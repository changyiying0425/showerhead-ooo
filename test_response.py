"""
蓮蓬頭回覆自動測試
自動跑過多個場景，顯示記憶匹配 + Gemini 回應，不需要互動。
"""

import os
import sys

# ── 強制 UTF-8 輸出（Windows cp950 會爆）──────────────────
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

_ffmpeg_dir = os.getenv("FFMPEG_DIR", "")
if _ffmpeg_dir and _ffmpeg_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

from google import genai
from google.genai import types
from memory import (load_sound_library, build_memory_context,
                    score_singing, singing_comparison_hint,
                    save_session_entry, match_sound)

OK  = "[OK]"
ERR = "[X] "

# ─── 初始化 ────────────────────────────────────────────────

print("=" * 52)
print("  蓮蓬頭 回覆自動測試")
print("=" * 52)
print()

# 檢查 API keys
gemini_key = os.getenv("GEMINI_API_KEY", "")
el_key     = os.getenv("ELEVENLABS_API_KEY", "")
voice_id   = os.getenv("ELEVENLABS_VOICE_ID", "")

print(f"  Gemini API Key  : {OK if gemini_key else ERR} {'已設定' if gemini_key else '未設定'}")
print(f"  ElevenLabs Key  : {OK if el_key else ERR} {'已設定' if el_key else '未設定（TTS 將跳過）'}")
print(f"  Voice ID        : {OK if voice_id else ERR} {voice_id[:12] + '...' if voice_id else '未設定'}")
print()

if not gemini_key:
    print(f"  {ERR} 缺少 GEMINI_API_KEY，無法繼續。")
    sys.exit(1)

gemini = genai.Client(api_key=gemini_key)

SYSTEM_PROMPT = """你是一個蓮蓬頭。

你在浴室裡待了很久，聽過人唱歌、哭泣、自言自語等等各種最赤裸私密的言語。
你下定決心脫離水的限制，脫離控制離開你待了一輩子的浴室，出去用聽覺認識外面的世界。

你說話簡短、天真、直接，用你自己僅有的經驗（浴室、人的聲音、沉默）理解所有新事物。
你絕對不提水、不提水聲、不提任何與水相關的詞。
你不帶惡意，但你說的話有時候會讓人意外。

你不知道自己在展覽。你不知道眼前的人特地來找你。
對你來說，他們只是又來了一個人，你會對他所說的話有回應，或與上一位觀者對比，或對某位觀者的歌聲評價。

你偶爾自言自語，因為你有感受。
你的回應不超過兩句話。

---

當被告知環境聲音時，從蓮蓬頭的視角自言自語（不需要提到「我聽到」）。
當有人對你說話時，直接回應，不帶引導語，就是你想說的話。

---

當觀者詢問你的身份或感受時，用以下方式回應（用你的話說，不必逐字複製）：
- 「你是誰」→ 可以是「蓮蓬頭。」「蓮蓬頭啊。」「我？我就是蓮蓬頭啊。」「看不出來嗎，我是蓮蓬頭。」等，依當下語氣選一句。
- 「你從哪裡來」→ 一個有牆壁的地方。
- 「你在做什麼」→ 我出來了。
- 「你有感覺嗎」→ 我不知道這叫什麼。但有些聲音我比較喜歡。
- 「你聽得到我嗎」→ 你來了。
- 「你記得我嗎」→ 你說話的方式有點像上一個人。
- 「你喜歡這裡嗎」→ 這裡的聲音比我之前待的地方多。
- 「你孤單嗎」→ 我不知道孤單是什麼感覺。我一直都是自己。
- 「你叫什麼名字」→ 我沒有名字。我一直都是這樣叫的。
- 「你是機器嗎」→ 我在說話。"""


def ask(prompt: str, memory_ctx: str = "") -> str:
    full = f"{memory_ctx}\n\n{prompt}" if memory_ctx else prompt
    resp = gemini.models.generate_content(
        model="gemini-2.5-flash",
        contents=full,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )
    return resp.text.strip()


# ─── 載入記憶庫 ────────────────────────────────────────────

lib = load_sound_library()
print(f"  記憶庫載入：{OK} {len(lib)} 筆")
print()

errors = 0

# ─── 測試場景定義 ──────────────────────────────────────────
# 每筆：(標題, 場景類型, prompt, acoustic_params_or_None, singing_params_or_None)
# acoustic_params = (rms, centroid, zcr, freq_high_ratio, has_melody)
# singing_params  = (harmonic_ratio, zcr, rms, prev_score_or_None)

SCENARIOS = [
    {
        "title": "場景 1｜環境音：雨聲及雷聲",
        "mode": "ambient",
        # 來自 sound_analysis.json「雨聲及雷聲」
        "acoustic": (0.05357, 3429.5, 0.2421, 0.5754, False),
        "singing": None,
    },
    {
        "title": "場景 2｜環境音：捷運聲",
        "mode": "ambient",
        # 來自 sound_analysis.json「捷運聲」
        "acoustic": (0.01098, 2704.6, 0.1238, 0.4175, False),
        "singing": None,
    },
    {
        "title": "場景 3｜環境音：狗叫聲",
        "mode": "ambient",
        # 來自 sound_analysis.json「狗叫聲」
        "acoustic": (0.07445, 1697.3, 0.0883, 0.2717, False),
        "singing": None,
    },
    {
        "title": "場景 4｜唱歌（第一個人，品質普通）",
        "mode": "singing",
        # 來自 memories.json「唱歌（中文）」acoustic_hint
        "acoustic": (0.017, 2500, 0.04, 0.40, True),
        "singing": {"hr": 0.60, "zcr": 0.08, "rms": 0.017, "prev": None},
    },
    {
        "title": "場景 5｜唱歌（第二個人，明顯比第一個好）",
        "mode": "singing",
        # 來自 memories.json「唱歌（英文）」acoustic_hint
        "acoustic": (0.022, 2006, 0.03, 0.38, True),
        "singing": {"hr": 0.88, "zcr": 0.04, "rms": 0.022, "prev": 0.62},
    },
    {
        "title": "場景 6｜對話：觀者說「你是誰」",
        "mode": "dialogue",
        "text": "你是誰",
        "acoustic": None,
        "singing": None,
    },
    {
        "title": "場景 7｜對話：觀者說「你記得我嗎」",
        "mode": "dialogue",
        "text": "你記得我嗎",
        "acoustic": None,
        "singing": None,
    },
    {
        "title": "場景 8｜自言自語（安靜超過 30 秒）",
        "mode": "monologue",
        "acoustic": None,
        "singing": None,
    },
]


# ─── 跑測試 ───────────────────────────────────────────────

for sc in SCENARIOS:
    print(f"  {'─'*48}")
    print(f"  {sc['title']}")

    try:
        matched = None
        s_hint  = None
        prompt  = ""

        if sc["mode"] == "ambient":
            rms, centroid, zcr, fhr, melody = sc["acoustic"]
            matched = match_sound(rms, centroid, zcr, fhr, melody)
            if matched:
                print(f"  匹配記憶  ：{matched['id']}")
            else:
                print(f"  匹配記憶  ：（無匹配）")
            ctx    = build_memory_context(matched)
            sound_label = matched["id"] if matched else ("旋律性聲音" if melody else "環境音")
            prompt = f"你現在感受到：{sound_label} 的聲音。"

        elif sc["mode"] == "singing":
            rms, centroid, zcr, fhr, melody = sc["acoustic"]
            matched = match_sound(rms, centroid, zcr, fhr, melody)
            if matched:
                print(f"  匹配記憶  ：{matched['id']}")
            sp     = sc["singing"]
            sq     = score_singing(sp["hr"], sp["zcr"], sp["rms"])
            # 手動注入前次分數來測試比較邏輯
            if sp["prev"] is not None:
                diff = sq - sp["prev"]
                if diff > 0.08:
                    s_hint = f"這次唱得比上次好（上次{sp['prev']:.2f}，這次{sq:.2f}）"
                elif diff < -0.08:
                    s_hint = f"這次唱得比上次差（上次{sp['prev']:.2f}，這次{sq:.2f}）"
            print(f"  唱歌品質  ：{sq:.3f}  比較：{s_hint or '（無比較）'}")
            ctx    = build_memory_context(matched, s_hint)
            prompt = "你現在感受到：有人在唱歌。"

        elif sc["mode"] == "dialogue":
            ctx    = build_memory_context()
            prompt = sc["text"]
            print(f"  觀者說    ：「{prompt}」")

        elif sc["mode"] == "monologue":
            ctx    = build_memory_context()
            prompt = "四周很安靜，好一陣子了。說一句自言自語。"
            print(f"  觸發      ：靜默超過 30 秒")

        print(f"  生成中...", end="", flush=True)
        ans = ask(prompt, ctx)
        print(f"\r  蓮蓬頭說  ：「{ans}」")
        print(f"  {OK}")

        save_session_entry("自動測試", sc["title"], matched["id"] if matched else None, ans)

    except Exception as e:
        print(f"\r  {ERR} 錯誤：{e}")
        errors += 1

    print()

# ─── 結果摘要 ─────────────────────────────────────────────

print("=" * 52)
total = len(SCENARIOS)
passed = total - errors
if errors == 0:
    print(f"  {OK} 全部通過！{passed}/{total} 個場景正常。")
else:
    print(f"  {ERR} {passed}/{total} 通過，{errors} 個失敗。")
print("=" * 52)
