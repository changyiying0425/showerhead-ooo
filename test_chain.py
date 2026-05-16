"""
軟體串聯測試腳本
逐步確認：.env → Gemini → ElevenLabs → pygame 播音
"""

import os
import sys
import tempfile
import time

# ── 1. 載入 .env ──────────────────────────────────────
print("=" * 45)
print("  蓮蓬頭 串聯測試")
print("=" * 45)

from dotenv import load_dotenv
load_dotenv()

GEMINI_KEY    = os.getenv("GEMINI_API_KEY", "")
ELEVEN_KEY    = os.getenv("ELEVENLABS_API_KEY", "")
ELEVEN_VOICE  = os.getenv("ELEVENLABS_VOICE_ID", "")

print("\n[1] .env 載入")
print(f"    Gemini API Key : {'✅ 已設定' if GEMINI_KEY else '❌ 空白'}")
print(f"    ElevenLabs Key : {'✅ 已設定' if ELEVEN_KEY else '❌ 空白'}")
print(f"    Voice ID       : {'✅ ' + ELEVEN_VOICE[:8] + '...' if ELEVEN_VOICE else '❌ 空白'}")

if not all([GEMINI_KEY, ELEVEN_KEY, ELEVEN_VOICE]):
    print("\n❌ .env 有缺漏，請先補齊再執行。")
    sys.exit(1)

# ── 2. 測試 Gemini API ────────────────────────────────
print("\n[2] 測試 Gemini API...")
try:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_KEY)
    available = [m.name for m in client.models.list() if "generateContent" in (m.supported_actions or [])]
    model_name = available[0] if available else "gemini-2.5-flash"
    print(f"    → 使用：{model_name}")

    resp = client.models.generate_content(
        model=model_name,
        contents="說一句話。",
        config=types.GenerateContentConfig(
            system_instruction="你是一個蓮蓬頭。回應不超過一句話。"
        ),
    )
    gemini_text = resp.text.strip()
    print(f"    ✅ Gemini 回應：{gemini_text}")
except Exception as e:
    print(f"    ❌ Gemini 錯誤：{e}")
    sys.exit(1)

# ── 3. 測試 ElevenLabs TTS ────────────────────────────
print("\n[3] 測試 ElevenLabs TTS...")
try:
    from elevenlabs.client import ElevenLabs
    eleven = ElevenLabs(api_key=ELEVEN_KEY)

    audio_gen = eleven.text_to_speech.convert(
        text=gemini_text,
        voice_id=ELEVEN_VOICE,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    audio_bytes = b"".join(audio_gen)
    print(f"    ✅ 語音合成完成（{len(audio_bytes):,} bytes）")
except Exception as e:
    print(f"    ❌ ElevenLabs 錯誤：{e}")
    sys.exit(1)

# ── 4. 播放音訊（pygame → Voicemeeter） ───────────────
print("\n[4] 播放音訊（請確認喇叭有聲音）...")
try:
    import pygame
    pygame.mixer.init(frequency=44100)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        f.write(audio_bytes)
        tmp_path = f.name

    pygame.mixer.music.load(tmp_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.05)
    pygame.mixer.music.unload()
    os.unlink(tmp_path)
    print("    ✅ 播放完成")
except Exception as e:
    print(f"    ❌ 播放錯誤：{e}")
    sys.exit(1)

# ── 完成 ──────────────────────────────────────────────
print("\n" + "=" * 45)
print("  ✅ 全部通過！軟體串聯正常。")
print("=" * 45)
