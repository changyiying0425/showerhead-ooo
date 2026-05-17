"""
試聽各聲音 — 每個聲音說同一句話，加上 ring modulation 效果
"""

import os
import sys
import io
import time
import tempfile

import numpy as np
import pygame
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from pydub import AudioSegment

load_dotenv()
load_dotenv("key.env", override=True)

el_key = os.getenv("ELEVENLABS_API_KEY", "")
if not el_key:
    print("缺少 ELEVENLABS_API_KEY")
    sys.exit(1)

client = ElevenLabs(api_key=el_key)
pygame.mixer.init()

VOICES = [
    ("Antoni （男，活潑自然）", "ErXwobaYiN019PkySvjV"),
    ("Rachel （女，清晰溫和）", "21m00Tcm4TlvDq8ikWAM"),
    ("Bella  （女，年輕感）",   "EXAVITQu4vr4xnSDxMaL"),
    ("Arnold （男，低沉粗獷）", "VR6AewLTigWG4xSOukaG"),
    ("Adam   （男，沉穩，目前）","pNInz6obpgDQGcFmaJgB"),
]

TEST_TEXT = "你來了。上一個人說話比你小聲。"


def apply_robot_effect(audio_bytes: bytes) -> bytes:
    seg = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
    sr = seg.frame_rate
    ch = seg.channels
    samples = np.frombuffer(seg.raw_data, dtype=np.int16).astype(np.float32) / 32768.0
    carrier_freq = 60.0
    depth = 0.55
    t = np.arange(len(samples)) / (sr * ch)
    carrier = 1.0 - depth + depth * np.sin(2 * np.pi * carrier_freq * t)
    samples = np.clip(samples * carrier, -1.0, 1.0)
    result = AudioSegment(
        (samples * 32767).astype(np.int16).tobytes(),
        frame_rate=sr, sample_width=2, channels=ch,
    )
    buf = io.BytesIO()
    result.export(buf, format="mp3", bitrate="128k")
    return buf.getvalue()


def play(audio_bytes: bytes):
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(audio_bytes)
        tmp = f.name
    try:
        pygame.mixer.music.load(tmp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        pygame.mixer.music.unload()
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass


print("=" * 50)
print("  蓮蓬頭 聲音試聽")
print(f"  測試句：「{TEST_TEXT}」")
print("  （含 ring modulation 效果）")
print("=" * 50)
print()

for name, vid in VOICES:
    print(f"▶ {name}", end="  ", flush=True)
    try:
        gen = client.text_to_speech.convert(
            voice_id=vid,
            text=TEST_TEXT,
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(
                stability=0.25,
                similarity_boost=0.5,
                style=0.4,
                use_speaker_boost=False,
            ),
        )
        raw = b"".join(gen)
        processed = apply_robot_effect(raw)
        play(processed)
        print("✓")
    except Exception as e:
        print(f"✗  {e}")
    time.sleep(0.5)

print()
print("試聽完成。請告訴我要用哪個聲音。")
