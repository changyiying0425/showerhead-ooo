"""
測試倒放效果：播放「大家好，我是蓮蓬頭」的正放與倒放
"""
import asyncio, io, time, tempfile, os
import numpy as np
import edge_tts
import pygame
from pydub import AudioSegment

VOICE = "zh-TW-HsiaoChenNeural"
TEXT  = "大家好，我是蓮蓬頭"

async def _gen_tts(text: str, path: str):
    await edge_tts.Communicate(text, voice=VOICE).save(path)

def tts_to_samples(text: str):
    """生成 TTS，回傳 (samples_float32, sample_rate, channels)"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        tmp = f.name
    loop = asyncio.new_event_loop()
    loop.run_until_complete(_gen_tts(text, tmp))
    loop.close()

    with open(tmp, "rb") as f:
        raw = f.read()
    os.unlink(tmp)

    seg = AudioSegment.from_mp3(io.BytesIO(raw))
    samples = np.frombuffer(seg.raw_data, dtype=np.int16).astype(np.float32) / 32768.0
    return samples, seg.frame_rate, seg.channels

def apply_ring_mod(samples, sr, ch):
    carrier_freq = 60.0
    depth        = 0.55
    t       = np.arange(len(samples)) / (sr * ch)
    carrier = 1.0 - depth + depth * np.sin(2 * np.pi * carrier_freq * t)
    return np.clip(samples * carrier, -1.0, 1.0)

def samples_to_mp3(samples, sr, ch) -> bytes:
    seg = AudioSegment(
        (samples * 32767).astype(np.int16).tobytes(),
        frame_rate=sr, sample_width=2, channels=ch,
    )
    buf = io.BytesIO()
    seg.export(buf, format="mp3", bitrate="128k")
    return buf.getvalue()

def play_bytes(audio_bytes: bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        f.write(audio_bytes)
        tmp = f.name
    pygame.mixer.music.load(tmp)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.05)
    pygame.mixer.music.unload()
    os.unlink(tmp)

if __name__ == "__main__":
    pygame.mixer.init(frequency=44100)

    print("生成 TTS 中...")
    samples, sr, ch = tts_to_samples(TEXT)

    # ── 正放 ──
    print("\n▶ 正放 + ring modulation")
    forward = apply_ring_mod(samples.copy(), sr, ch)
    play_bytes(samples_to_mp3(forward, sr, ch))
    time.sleep(0.8)

    # ── 倒放 ──
    print("◀ 倒放 + ring modulation")
    reversed_ = apply_ring_mod(samples[::-1].copy(), sr, ch)
    play_bytes(samples_to_mp3(reversed_, sr, ch))

    print("\n完成")
