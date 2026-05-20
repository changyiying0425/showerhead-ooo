"""
蓮蓬頭 — 主程式
Object-Oriented Ontology 互動裝置

執行前請先：
  1. 複製 .env.example → .env，填入 API 金鑰
  2. pip install -r requirements.txt
  3. 燒錄 arduino/showerhead/showerhead.ino 到 Arduino Nano
  4. 用 Chrome 開啟 http://localhost:5000
"""

import os
import sys
import time
import threading
import tempfile

import numpy as np
import sounddevice as sd
import librosa
import serial
import pygame
from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.genai import types
from elevenlabs.client import ElevenLabs
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
from memory import (build_memory_context, save_session_entry, match_sound,
                    score_singing, singing_comparison_hint)
from scan_sounds import scan as scan_audio_folder

load_dotenv()
load_dotenv("key.env", override=True)  # 支援 key.env 命名

# ffmpeg PATH（M4A 等格式支援）
_ffmpeg_dir = os.getenv("FFMPEG_DIR", "")
if _ffmpeg_dir and _ffmpeg_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

# ═══════════════════════════════════════════════════
#  設定
# ═══════════════════════════════════════════════════

SERIAL_PORT      = os.getenv("SERIAL_PORT", "COM3")
BAUD_RATE        = 115200
SAMPLE_RATE      = 44100
AMBIENT_SECONDS  = 10     # 每幾秒分析一次環境音
SILENCE_TIMEOUT  = 30     # 超過幾秒無聲 → 自動自言自語
ELEVENLABS_VOICE = os.getenv("ELEVENLABS_VOICE_ID", "")
FONT_PATH        = os.getenv("FONT_PATH", r"C:\Windows\Fonts\msjh.ttc")  # 微軟正黑體

# ═══════════════════════════════════════════════════
#  蓮蓬頭個性設定（System Prompt）
# ═══════════════════════════════════════════════════

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

你說話時用感受和聯想，不直接描述音量大小或音調高低。
「好高。」「很輕。」「大聲。」「尖尖的。」「細細的。」「低的。」這類純粹描述聲音物理性質的話你不說。
你說的是這個聲音讓你感受到什麼、讓你想起什麼、它跟你經驗裡的什麼相似或不同。

每次回應的用詞和句式都不一樣，不重複今天已說過的表達方式。

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

# ═══════════════════════════════════════════════════
#  初始化 API
# ═══════════════════════════════════════════════════

gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))

eleven = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY", ""))

pygame.mixer.init(frequency=44100)

# ═══════════════════════════════════════════════════
#  Flask + SocketIO
# ═══════════════════════════════════════════════════

app = Flask(__name__, template_folder="web")
app.config["SECRET_KEY"] = "showerhead_ooo_2025"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ═══════════════════════════════════════════════════
#  全域狀態
# ═══════════════════════════════════════════════════

mode            = "ambient"   # "ambient" | "dialogue"
last_sound_time = time.time()
arduino         = None
response_lock   = threading.Lock()

# ═══════════════════════════════════════════════════
#  OLED 點陣圖產生（PIL → U8g2 頁格式）
# ═══════════════════════════════════════════════════

def _load_font(size=13):
    for path in [FONT_PATH,
                 r"C:\Windows\Fonts\msyh.ttc",
                 r"C:\Windows\Fonts\mingliu.ttc"]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap_text(text, font, max_w=124):
    lines, cur = [], ""
    for ch in text:
        test = cur + ch
        w = font.getlength(test) if hasattr(font, "getlength") else len(test) * 7
        if w > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def text_to_oled_bytes(text: str) -> bytearray:
    """將文字轉成 SH1106 U8g2 格式的 1024 bytes 點陣圖。"""
    img  = Image.new("1", (128, 64), 0)
    draw = ImageDraw.Draw(img)
    font = _load_font(13)

    lines  = _wrap_text(text, font)
    line_h = 15
    y0     = max(0, (64 - len(lines) * line_h) // 2)
    for i, line in enumerate(lines):
        draw.text((2, y0 + i * line_h), line, font=font, fill=1)

    pixels = np.array(img)           # shape (64, 128), dtype bool

    # U8g2 全框緩衝區格式：8 頁 × 128 欄，每 byte 代表 8 垂直像素
    buf = bytearray(1024)
    for page in range(8):
        for col in range(128):
            byte = 0
            for bit in range(8):
                row = page * 8 + bit
                if pixels[row, col]:
                    byte |= (1 << bit)
            buf[page * 128 + col] = byte
    return buf


def send_to_oled(text: str):
    global arduino
    if arduino and arduino.is_open:
        try:
            bitmap = text_to_oled_bytes(text)
            arduino.write(bytes([0xFF, 0xFE, 0xFD]) + bitmap)
            arduino.flush()
            print(f"[OLED] 傳送：{text[:30]}")
        except Exception as e:
            print(f"[OLED] 傳送失敗：{e}")
    else:
        print("[OLED] 未連線，跳過傳送")

# ═══════════════════════════════════════════════════
#  機械感音效處理（Ring Modulation）
# ═══════════════════════════════════════════════════

def _apply_robot_effect(audio_bytes: bytes) -> bytes:
    """
    環形調製：把語音乘以低頻載波，製造金屬共鳴/機械感。
    carrier_freq 越低越像低頻嗡嗡聲，40–80Hz 效果明顯。
    depth 控制效果強度（0=無效果，1=完全環形調製）。
    """
    import io
    from pydub import AudioSegment

    seg    = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
    sr     = seg.frame_rate
    ch     = seg.channels
    samples = np.frombuffer(seg.raw_data, dtype=np.int16).astype(np.float32) / 32768.0

    carrier_freq = 60.0   # Hz，可調：數字越小越沉、越大越像電話
    depth        = 0.55   # 0.0–1.0，效果強度

    t       = np.arange(len(samples)) / (sr * ch)
    carrier = 1.0 - depth + depth * np.sin(2 * np.pi * carrier_freq * t)
    samples = np.clip(samples * carrier, -1.0, 1.0)

    result = AudioSegment(
        (samples * 32767).astype(np.int16).tobytes(),
        frame_rate=sr, sample_width=2, channels=ch,
    )
    buf = io.BytesIO()
    result.export(buf, format="mp3", bitrate="128k")
    return buf.getvalue()


# ═══════════════════════════════════════════════════
#  語音合成（ElevenLabs → pygame 播放）
# ═══════════════════════════════════════════════════

def speak(text: str):
    if not ELEVENLABS_VOICE:
        print(f"[TTS] （無聲音 ID，略過）：{text}")
        return
    try:
        from elevenlabs import VoiceSettings
        audio_gen  = eleven.text_to_speech.convert(
            text=text,
            voice_id=ELEVENLABS_VOICE,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            voice_settings=VoiceSettings(
                stability=0.25,         # 低穩定性：聲音更粗糙、不均勻
                similarity_boost=0.5,   # 降低相似度：帶更多雜質
                style=0.4,              # 風格誇張化
                use_speaker_boost=False,
            ),
        )
        audio_bytes = b"".join(audio_gen)
        audio_bytes = _apply_robot_effect(audio_bytes)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            f.write(audio_bytes)
            tmp_path = f.name

        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        pygame.mixer.music.unload()
        os.unlink(tmp_path)
    except Exception as e:
        print(f"[TTS] 錯誤：{e}")

# ═══════════════════════════════════════════════════
#  回應流程：OLED + 語音
# ═══════════════════════════════════════════════════

def respond(text: str):
    with response_lock:
        print(f"\n蓮蓬頭：{text}\n")
        send_to_oled(text)
        speak(text)

# ═══════════════════════════════════════════════════
#  Gemini API
# ═══════════════════════════════════════════════════

def ask_gemini(prompt: str, sound_desc: str = "", context: str = "展場",
               matched_memory: dict | None = None,
               singing_hint: str | None = None,
               singing_quality: float | None = None) -> str | None:
    memory_ctx  = build_memory_context(matched_memory, singing_hint)
    full_prompt = f"{memory_ctx}\n\n{prompt}" if memory_ctx else prompt
    for model in ["gemini-2.5-flash", "gemini-2.5-flash-lite-preview-06-17"]:
        try:
            resp = gemini.models.generate_content(
                model=model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                ),
            )
            result = resp.text.strip()
            if sound_desc:
                matched_id = matched_memory.get("id") if matched_memory else None
                save_session_entry(context, sound_desc, matched_id, result, singing_quality)
            return result
        except Exception as e:
            print(f"[Gemini] {model} 錯誤：{e}")
    return None

# ═══════════════════════════════════════════════════
#  環境音分析（librosa）
# ═══════════════════════════════════════════════════

def describe_audio(audio: np.ndarray) -> tuple[str | None, dict]:
    """
    分析音頻，回傳 (描述文字, 聲音特徵字典)。
    太安靜則描述為 None。
    """
    rms = float(np.sqrt(np.mean(audio ** 2)))
    features: dict = {"rms": rms}

    if rms < 0.015:
        return None, features

    af = audio.astype(np.float32)
    try:
        centroid       = float(librosa.feature.spectral_centroid(y=af, sr=SAMPLE_RATE).mean())
        zcr            = float(librosa.feature.zero_crossing_rate(af).mean())
        stft           = np.abs(librosa.stft(af))
        freqs          = librosa.fft_frequencies(sr=SAMPLE_RATE)
        total          = np.sum(stft) + 1e-10
        freq_high      = float(np.sum(stft[freqs >= 2000]) / total)
        freq_mid       = float(np.sum(stft[(freqs >= 300) & (freqs < 2000)]) / total)
        harmonic       = librosa.effects.harmonic(af)
        harmonic_ratio = float(np.mean(harmonic ** 2)) / (float(np.mean(af ** 2)) + 1e-10)
        # 唱歌：harmonic_ratio 高 + ZCR 低（音符持續、穩定）
        # 說話：harmonic_ratio 中 + ZCR 較高（音高變化快）
        has_melody = (harmonic_ratio > 0.92 and zcr < 0.04) or \
                     (harmonic_ratio > 0.88 and zcr < 0.03 and rms > 0.025)
    except Exception:
        centroid, zcr, freq_high, freq_mid, harmonic_ratio, has_melody = (
            2000.0, 0.08, 0.5, 0.3, 0.0, False
        )

    features.update({
        "centroid": centroid, "zcr": zcr,
        "freq_high_ratio": freq_high, "freq_mid_ratio": freq_mid,
        "harmonic_ratio": harmonic_ratio, "has_melody": has_melody,
    })

    vol  = "很大聲" if rms > 0.12 else ("普通" if rms > 0.03 else "很輕")
    if has_melody:
        kind = "有人在唱歌或有音樂，有旋律"
    elif zcr > 0.18:
        kind = "有說話聲或吵雜的聲音"
    elif zcr > 0.12:
        kind = "有人在說話"
    else:
        kind = "有聲音，不像人聲"
    pitch = "尖銳的" if centroid > 3500 else ("低沉的" if centroid < 1500 else "中等音調的")

    return f"{kind}，{vol}，{pitch}", features


# ═══════════════════════════════════════════════════
#  背景執行緒 1：環境音模式
# ═══════════════════════════════════════════════════

def ambient_loop():
    global mode, last_sound_time
    prev_desc = None

    while True:
        if mode != "ambient":
            time.sleep(1)
            continue

        # 錄音
        try:
            audio = sd.rec(int(AMBIENT_SECONDS * SAMPLE_RATE),
                           samplerate=SAMPLE_RATE, channels=1, dtype="float32")
            sd.wait()
        except Exception as e:
            print(f"[音頻] 錄音失敗：{e}")
            time.sleep(5)
            continue

        if mode != "ambient":
            continue

        desc, features = describe_audio(audio.flatten())
        rms_val = features.get("rms", 0)
        zcr_val = features.get("zcr", 0)
        hr_val  = features.get("harmonic_ratio", 0)
        print(f"[偵測] rms={rms_val:.4f}  zcr={zcr_val:.3f}  hr={hr_val:.3f}  {'有聲音' if desc else '安靜（rms<0.015）'}  melody={features.get('has_melody', False)}")

        if desc:
            last_sound_time = time.time()
            is_singing = features.get("has_melody", False)
            if desc != prev_desc or is_singing:
                matched = match_sound(
                    rms            = features.get("rms", 0),
                    centroid       = features.get("centroid", 2000),
                    zcr            = features.get("zcr", 0.08),
                    freq_high_ratio= features.get("freq_high_ratio", 0.5),
                    has_melody     = features.get("has_melody", False),
                )
                if matched:
                    print(f"[記憶匹配] {matched['id']}")

                # 唱歌品質判斷
                s_quality = None
                s_hint    = None
                if features.get("has_melody") and matched and "唱歌" in matched.get("id", ""):
                    s_quality = score_singing(
                        features.get("harmonic_ratio", 0),
                        features.get("zcr", 0.1),
                        features.get("rms", 0),
                    )
                    s_hint = singing_comparison_hint(s_quality)
                    if s_hint:
                        print(f"[唱歌比較] {s_hint}")

                ans = ask_gemini(
                    f"你現在感受到：{desc}。",
                    sound_desc=desc,
                    matched_memory=matched,
                    singing_hint=s_hint,
                    singing_quality=s_quality,
                )
                if ans:
                    respond(ans)
                prev_desc = desc
        else:
            if time.time() - last_sound_time > SILENCE_TIMEOUT:
                ans = ask_gemini("四周很安靜，好一陣子了。說一句自言自語。", sound_desc="安靜")
                if ans:
                    respond(ans)
                last_sound_time = time.time()
            prev_desc = None


# ═══════════════════════════════════════════════════
#  背景執行緒 2：Arduino Serial 通訊
# ═══════════════════════════════════════════════════

def arduino_loop():
    global arduino, mode

    try:
        arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)   # 等待 Arduino 重置
        arduino.reset_input_buffer()  # 清掉殘留資料
        print(f"[Arduino] 連線成功：{SERIAL_PORT}")
        send_to_oled("...")
    except Exception as e:
        print(f"[Arduino] 連線失敗（{e}）\n"
              f"  → 請確認 .env 裡的 SERIAL_PORT（目前設定：{SERIAL_PORT}）")
        return

    while True:
        try:
            if arduino.in_waiting:
                line = arduino.readline().decode("utf-8", errors="ignore").strip()
                if line == "HOLD":
                    _switch_dialogue()
                elif line == "RELEASE":
                    _switch_ambient()
                elif line.startswith("BMAP"):
                    print(f"[OLED] Arduino 回報：{line}")
        except Exception as e:
            print(f"[Arduino] 讀取錯誤：{e}")
            time.sleep(1)


def _switch_dialogue():
    global mode
    if mode != "dialogue":
        mode = "dialogue"
        print("[模式] → 對話")
        send_to_oled("聽著...")
        socketio.emit("start_listening")


def _switch_ambient():
    global mode
    if mode != "ambient":
        mode = "ambient"
        print("[模式] → 環境音")

# ═══════════════════════════════════════════════════
#  Flask 路由 & SocketIO 事件
# ═══════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/scan")
def trigger_scan():
    """
    觸發音檔掃描（只分析新增/變更的檔案）。
    在終端機互動審核後決定是否寫入 memories.json。
    瀏覽器開啟 http://localhost:5000/scan 或在終端機執行：
      python scan_sounds.py
      python scan_sounds.py --all
    """
    import subprocess, sys
    subprocess.Popen([sys.executable, "scan_sounds.py"],
                     cwd=os.path.dirname(__file__))
    return jsonify({"status": "scan started",
                    "message": "請查看終端機視窗進行審核"})


@socketio.on("transcript")
def on_transcript(data):
    text = data.get("text", "").strip()
    if not text or mode != "dialogue":
        return
    print(f"觀眾說：{text}")
    ans = ask_gemini(text)
    if ans:
        respond(ans)

# ═══════════════════════════════════════════════════
#  主程式入口
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 45)
    print("  蓮蓬頭 — OOO 互動裝置  啟動中...")
    print("=" * 45)

    for target in (arduino_loop, ambient_loop):
        t = threading.Thread(target=target, daemon=True)
        t.start()

    print("Web Speech 介面：http://localhost:5000")
    print("請用 Chrome 開啟以上網址\n")

    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False)
