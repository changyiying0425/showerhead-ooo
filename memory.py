"""
蓮蓬頭記憶系統

memories.json   — 精選聲音記憶庫（手動維護，scan_sounds.py 協助更新）
session_log.json — 展覽即時對話紀錄（自動寫入）
"""

import json
import os
from datetime import datetime

_BASE = os.path.dirname(__file__)
SOUND_LIB_FILE  = os.path.join(_BASE, "memories.json")
SESSION_LOG_FILE = os.path.join(_BASE, "session_log.json")
MAX_SESSION_CTX  = 5   # 帶進 Gemini 的最近對話筆數


# ─── 聲音記憶庫 ───────────────────────────────────────────

def load_sound_library() -> list[dict]:
    if not os.path.exists(SOUND_LIB_FILE):
        return []
    with open(SOUND_LIB_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("memories", [])


def save_sound_library(memories: list[dict]):
    existing = {}
    if os.path.exists(SOUND_LIB_FILE):
        with open(SOUND_LIB_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
    existing["memories"] = memories
    existing["version"] = existing.get("version", "1.0")
    with open(SOUND_LIB_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def add_or_update_sound(entry: dict):
    """新增或更新一筆聲音記憶（以 id 為鍵）。"""
    library = load_sound_library()
    ids = [m["id"] for m in library]
    if entry["id"] in ids:
        library[ids.index(entry["id"])] = entry
    else:
        library.append(entry)
    save_sound_library(library)


def match_sound(rms: float, centroid: float, zcr: float,
                freq_high_ratio: float = 0.5,
                has_melody: bool = False) -> dict | None:
    """
    根據 librosa 特徵找最接近的聲音記憶。
    回傳匹配的記憶 dict，或 None（差異太大）。
    """
    library = load_sound_library()
    if not library:
        return None

    best, best_score = None, float("inf")

    for mem in library:
        hint = mem.get("acoustic_hint", {})
        rms_t      = hint.get("rms_approx", 0.05)
        centroid_t = hint.get("spectral_centroid_hz_approx", 2000)

        rms_diff      = abs(rms - rms_t) / (rms_t + 1e-6)
        centroid_diff = abs(centroid - centroid_t) / (centroid_t + 1e-6)

        penalty = 0.0
        if hint.get("freq_high_ratio_min") and freq_high_ratio < hint["freq_high_ratio_min"] - 0.1:
            penalty += 0.5
        if hint.get("freq_mid_dominant") and freq_high_ratio > 0.65:
            penalty += 0.3
        if hint.get("zcr_high") and zcr < 0.10:
            penalty += 0.3
        if hint.get("zcr_low") and zcr > 0.15:
            penalty += 0.3
        if hint.get("has_melody") and not has_melody:
            penalty += 0.4
        if has_melody and not hint.get("has_melody"):
            penalty += 0.2
        # 偵測到旋律時，優先匹配唱歌記憶
        if has_melody and "唱歌" in mem.get("id", ""):
            penalty -= 0.4
        # 偵測到旋律但匹配到非人聲樂器，加懲罰
        if has_melody and hint.get("has_melody") and "唱歌" not in mem.get("id", ""):
            penalty += 0.3

        score = rms_diff * 0.55 + centroid_diff * 0.30 + penalty
        if score < best_score:
            best_score, best = score, mem

    return best if best_score < 1.5 else None


# ─── 即時對話紀錄 ─────────────────────────────────────────

def load_session_log() -> list[dict]:
    if not os.path.exists(SESSION_LOG_FILE):
        return []
    with open(SESSION_LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_session_entry(context: str, sound_desc: str,
                       matched_id: str | None, response: str,
                       singing_quality: float | None = None):
    log = load_session_log()
    entry = {
        "timestamp":         datetime.now().strftime("%Y-%m-%d %H:%M"),
        "context":           context,
        "sound_desc":        sound_desc,
        "matched_memory_id": matched_id,
        "response":          response,
    }
    if singing_quality is not None:
        entry["singing_quality"] = round(singing_quality, 4)
    log.append(entry)
    if len(log) > 200:
        log = log[-200:]
    with open(SESSION_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


# ─── 唱歌品質比較 ─────────────────────────────────────────

def score_singing(harmonic_ratio: float, zcr: float, rms: float) -> float:
    """
    0.0–1.0 的唱歌品質分數。
    諧波比（音準）權重最高，ZCR 穩定度其次，音量補充。
    """
    hr_score  = min(harmonic_ratio, 1.0)
    zcr_score = max(0.0, 1.0 - zcr * 4)   # ZCR 越低越穩（唱歌）
    rms_score = min(rms / 0.05, 1.0)
    return round(hr_score * 0.6 + zcr_score * 0.3 + rms_score * 0.1, 4)


def get_last_singing_quality() -> float | None:
    """回傳最近一次唱歌的品質分數，沒有則回傳 None。"""
    log = load_session_log()
    for entry in reversed(log):
        if (entry.get("matched_memory_id") or "").startswith("唱歌") and \
           entry.get("singing_quality") is not None:
            return entry["singing_quality"]
    return None


def singing_comparison_hint(current_score: float) -> str | None:
    """
    回傳比較提示字串，給 Gemini 作為上下文判斷依據。
    差距不夠大時回傳 None（不做比較）。
    """
    prev = get_last_singing_quality()
    if prev is None:
        return None
    diff = current_score - prev
    if diff > 0.08:
        return f"這次唱得比上次好（上次{prev:.2f}，這次{current_score:.2f}）"
    if diff < -0.08:
        return f"這次唱得比上次差（上次{prev:.2f}，這次{current_score:.2f}）"
    return None   # 差不多，不做比較


# ─── Gemini 上下文組裝 ────────────────────────────────────

def build_memory_context(matched_memory: dict | None = None,
                         singing_hint: str | None = None) -> str:
    parts = []

    if matched_memory:
        sid     = matched_memory.get("id", "")
        mem_txt = matched_memory.get("showerhead_memory", "")
        feeling = matched_memory.get("showerhead_feeling", "")
        samples = matched_memory.get("sample_responses", [])

        parts.append(f"你記得這種聲音（{sid}）：{mem_txt}")
        if feeling:
            parts.append(f"你當時的感受：{feeling}")
        if samples:
            parts.append(f"你曾對這種聲音說過：{'、'.join(samples[:3])}")

    if singing_hint:
        parts.append(f"\n【唱歌比較】{singing_hint}。你可以偶爾說出比較的感受，例如「上一個比較好。」「好聽。」「這次不一樣。」等，但不必每次都比較。")

    log = load_session_log()
    recent = log[-MAX_SESSION_CTX:]
    if recent:
        parts.append("\n你今天說過：")
        for e in recent:
            parts.append(f"- 聽到「{e['sound_desc']}」，你說：「{e['response']}」")

    return "\n".join(parts)
