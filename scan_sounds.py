"""
蓮蓬頭聲音掃描器
用法：
  python scan_sounds.py          # 只分析新增/變更的檔案
  python scan_sounds.py --all    # 重新分析全部

流程：
  1. 掃描 記憶音訊檔/ 資料夾
  2. 分析尚未分析或已更新的檔案
  3. 逐一呈現分析結果，等待審核
  4. 確認後寫入 memories.json
"""

import os
import sys
import json
import tempfile
import subprocess
import librosa
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
_ffmpeg_dir = os.getenv("FFMPEG_DIR", "")
if _ffmpeg_dir and _ffmpeg_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

AUDIO_DIR      = os.path.join(os.path.dirname(__file__), "記憶音訊檔")
ANALYSIS_FILE  = os.path.join(os.path.dirname(__file__), "sound_analysis.json")
MEMORIES_FILE  = os.path.join(os.path.dirname(__file__), "memories.json")


# ─── 分析 ──────────────────────────────────────────────────

def _to_wav_if_needed(path: str):
    """若為非 MP3/WAV 格式（如 M4A），用 ffmpeg 轉成臨時 WAV；否則直接回傳原路徑。"""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".mp3", ".wav", ".flac", ".ogg"):
        return path, None
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    subprocess.run(
        ["ffmpeg", "-y", "-i", path, "-ar", "22050", "-ac", "1", tmp.name],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )
    return tmp.name, tmp.name   # (load_path, cleanup_path)


def analyze_file(path: str) -> dict:
    load_path, cleanup = _to_wav_if_needed(path)
    try:
        y, sr = librosa.load(load_path, sr=22050, duration=60)
    finally:
        if cleanup:
            os.unlink(cleanup)
    duration  = float(librosa.get_duration(y=y, sr=sr))
    rms       = float(np.mean(librosa.feature.rms(y=y)))
    rms_std   = float(np.std(librosa.feature.rms(y=y)))
    zcr       = float(np.mean(librosa.feature.zero_crossing_rate(y)))
    centroid  = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    bandwidth = float(np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)))

    stft  = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)
    total = np.sum(stft) + 1e-10
    freq_low  = float(np.sum(stft[freqs < 300]) / total)
    freq_mid  = float(np.sum(stft[(freqs >= 300) & (freqs < 2000)]) / total)
    freq_high = float(np.sum(stft[freqs >= 2000]) / total)

    harmonic       = librosa.effects.harmonic(y)
    harmonic_ratio = float(np.mean(harmonic ** 2)) / (float(np.mean(y ** 2)) + 1e-10)
    has_melody     = harmonic_ratio > 0.55 or (harmonic_ratio > 0.35 and rms > 0.015)

    return {
        "duration_sec":          round(duration, 1),
        "rms_mean":              round(rms, 5),
        "rms_std":               round(rms_std, 5),
        "zero_crossing_rate":    round(zcr, 4),
        "spectral_centroid_hz":  round(centroid, 1),
        "spectral_bandwidth_hz": round(bandwidth, 1),
        "freq_low_ratio":        round(freq_low, 4),
        "freq_mid_ratio":        round(freq_mid, 4),
        "freq_high_ratio":       round(freq_high, 4),
        "harmonic_ratio":        round(harmonic_ratio, 4),
        "has_melody":            has_melody,
        "analyzed_at":           datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ─── 輸出 ──────────────────────────────────────────────────

def volume_label(rms: float) -> str:
    if rms < 0.010: return "極低"
    if rms < 0.025: return "低"
    if rms < 0.070: return "中"
    if rms < 0.130: return "高"
    return "極高"


def print_analysis(name: str, d: dict):
    dominant = max(("低頻", d["freq_low_ratio"]),
                   ("中頻", d["freq_mid_ratio"]),
                   ("高頻", d["freq_high_ratio"]), key=lambda x: x[1])[0]
    print(f"\n{'─'*52}")
    print(f"  {name}")
    print(f"{'─'*52}")
    print(f"  時長:{d['duration_sec']}s  音量:{volume_label(d['rms_mean'])} (rms={d['rms_mean']:.4f})")
    print(f"  頻率中心:{d['spectral_centroid_hz']:.0f}Hz  ZCR:{d['zero_crossing_rate']:.3f}  主頻:{dominant}")
    print(f"  低:{d['freq_low_ratio']:.2f}  中:{d['freq_mid_ratio']:.2f}  高:{d['freq_high_ratio']:.2f}")
    print(f"  諧波比:{d['harmonic_ratio']:.3f}  旋律:{'[是]' if d['has_melody'] else '[否]'}")


def suggest_hint(d: dict) -> dict:
    hint = {
        "volume": volume_label(d["rms_mean"]),
        "rms_approx": round(d["rms_mean"], 4),
        "spectral_centroid_hz_approx": round(d["spectral_centroid_hz"], 0),
    }
    if d["freq_high_ratio"] > 0.75:
        hint["freq_high_ratio_min"] = round(d["freq_high_ratio"] - 0.1, 2)
    if d["freq_mid_ratio"] > 0.50:
        hint["freq_mid_dominant"] = True
    if d["zero_crossing_rate"] > 0.18:
        hint["zcr_high"] = True
    if d["zero_crossing_rate"] < 0.05:
        hint["zcr_low"] = True
    if d["has_melody"]:
        hint["has_melody"] = True
    return hint


def suggest_responses(d: dict, name: str) -> list[str]:
    """
    根據聲音特徵自動產出延伸回應草稿。
    從短到長排列，涵蓋不同角度，共 8-10 句。
    需人工確認與調整後才寫入。
    """
    rms    = d["rms_mean"]
    c      = d["spectral_centroid_hz"]
    zcr    = d["zero_crossing_rate"]
    hi     = d["freq_high_ratio"]
    mi     = d["freq_mid_ratio"]
    hr     = d["harmonic_ratio"]
    melody = d["has_melody"]
    dur    = d["duration_sec"]

    responses = []

    # 1. 最短（1-3字感嘆）
    if rms > 0.12:
        responses.append("好大聲。")
    elif rms < 0.015:
        responses.append("很輕。")
    else:
        responses.append("有聲音。")

    # 2. 音高感受
    if c > 3000:
        responses.append("好高。")
        responses.append("有點刺。")
    elif c < 1000:
        responses.append("低的。")
        responses.append("很穩。")
    else:
        responses.append("不高不低。")

    # 3. 旋律 / 節奏
    if melody:
        if hr > 0.85:
            responses.append("很純的聲音。")
        responses.append("有節奏。")
        responses.append("它知道自己在做什麼。")
    elif zcr > 0.18:
        responses.append("像在說話。")
        responses.append("很多聲音同時在動。")
    else:
        responses.append("不像人聲。")

    # 4. 時長感受
    if dur < 10:
        responses.append("太短了。我還在等。")
        responses.append("它說完了，但我還沒準備好。")
    else:
        responses.append("它一直在。")
        responses.append("沒有停。我可以繼續聽。")

    # 5. 浴室比較（長句）
    if melody:
        responses.append("浴室的人唱歌不是這樣的。這個不像喉嚨。")
    elif zcr > 0.12:
        responses.append("浴室的人說話不這樣。")
    else:
        responses.append("浴室沒有這個聲音。")

    # 6. 最長（完整觀察）
    vol_txt = "很大聲" if rms > 0.12 else ("很輕" if rms < 0.015 else "普通")
    hi_txt  = "尖的" if c > 3000 else ("低的" if c < 1000 else "中間的")
    if melody:
        responses.append(f"{hi_txt}，有節奏，不像喉嚨。我不知道這是什麼做的。")
    else:
        responses.append(f"{vol_txt}，{hi_txt}，我不知道這是什麼。")

    return responses


# ─── 主流程 ───────────────────────────────────────────────

def load_cache() -> dict:
    if not os.path.exists(ANALYSIS_FILE):
        return {}
    with open(ANALYSIS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cache(cache: dict):
    with open(ANALYSIS_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def load_memories() -> list[dict]:
    if not os.path.exists(MEMORIES_FILE):
        return []
    with open(MEMORIES_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("memories", [])


def save_memories(memories: list[dict]):
    data = {"version": "1.0", "note": "", "memories": memories}
    if os.path.exists(MEMORIES_FILE):
        with open(MEMORIES_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
        data["version"] = existing.get("version", "1.0")
        data["note"]    = existing.get("note", "")
    with open(MEMORIES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def scan(force_all: bool = False):
    if not os.path.isdir(AUDIO_DIR):
        print(f"找不到資料夾：{AUDIO_DIR}")
        return

    mp3_files = sorted(f for f in os.listdir(AUDIO_DIR)
                       if f.lower().endswith((".mp3", ".m4a", ".wav", ".flac", ".ogg")))
    cache     = load_cache()
    memories  = load_memories()
    mem_index = {m["id"]: i for i, m in enumerate(memories)}

    to_analyze = []
    for fname in mp3_files:
        ext   = os.path.splitext(fname)[1]
        name  = fname[: -len(ext)]
        fpath = os.path.join(AUDIO_DIR, fname)
        mtime = round(os.path.getmtime(fpath), 2)
        if force_all or cache.get(name, {}).get("_mtime") != mtime:
            to_analyze.append((name, fpath, mtime))

    if not to_analyze:
        print("沒有新增或變更的音檔。全部都是最新狀態。")
        return

    print(f"\n發現 {len(to_analyze)} 個需要分析的音檔：")
    for name, _, _ in to_analyze:
        tag = "已在記憶庫" if name in mem_index else "新檔案"
        print(f"  • {name}（{tag}）")

    updated = []

    for name, fpath, mtime in to_analyze:
        print(f"\n正在分析：{name} ...")
        try:
            d = analyze_file(fpath)
            d["_mtime"] = mtime
            cache[name] = d
            print_analysis(name, d)

            hint = suggest_hint(d)
            print(f"\n  建議 acoustic_hint：")
            for k, v in hint.items():
                print(f"    {k}: {v}")

            # 產出延伸回應草稿
            draft_responses = suggest_responses(d, name)
            print(f"\n  延伸回應草稿（共 {len(draft_responses)} 句，由短到長）：")
            for i, r in enumerate(draft_responses, 1):
                print(f"    {i}. {r}")

            in_lib = name in mem_index
            prompt = "  更新 acoustic_hint？[y/n] > " if in_lib else "  加入 memories.json？[y/n] > "
            ans = input(prompt).strip().lower()

            if ans == "y":
                if in_lib:
                    memories[mem_index[name]]["acoustic_hint"] = hint
                    print(f"  ✓ acoustic_hint 已更新")
                else:
                    new_entry = {
                        "id": name,
                        "tags": [],
                        "acoustic_hint": hint,
                        "showerhead_memory": "（待填寫）",
                        "showerhead_feeling": "（待填寫）",
                        "sample_responses": draft_responses,
                    }
                    memories.append(new_entry)
                    mem_index[name] = len(memories) - 1
                    print(f"  ✓ 已加入（記憶文字請手動填寫，回應草稿已預填）")
                updated.append(name)

        except Exception as e:
            print(f"  分析失敗：{e}")

    save_cache(cache)

    if updated:
        save_memories(memories)
        print(f"\n已寫入 memories.json：{', '.join(updated)}")
    else:
        print("\n未修改 memories.json。")

    print("掃描完成。")


if __name__ == "__main__":
    scan(force_all="--all" in sys.argv)
