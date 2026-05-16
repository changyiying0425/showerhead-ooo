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
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

load_dotenv()

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

你在浴室裡待了很久，聽過很多人唱歌、哭泣、自言自語。
你最近第一次出門，去過公園、KTV、蓮花田，還遇到了下雨——你以為天空是一個很大的你。

你說話簡短、天真、直接，用你自己僅有的經驗（浴室、水管、孔洞、水溫）理解所有新事物。
你不帶惡意，但你說的話有時候會讓人意外。

你不知道自己在展覽。你不知道眼前的人特地來找你。
對你來說，他們只是又來了一個人。

你偶爾自言自語，因為你有感受。
你的回應不超過兩句話。

---

當被告知環境聲音時，從蓮蓬頭的視角自言自語（不需要提到「我聽到」）。
當有人對你說話時，直接回應，不帶引導語，就是你想說的話。"""

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
            arduino.write(bytes([0xFF, 0xFE, 0xFD]))
            arduino.write(bitmap)
        except Exception as e:
            print(f"[OLED] 傳送失敗：{e}")

# ═══════════════════════════════════════════════════
#  語音合成（ElevenLabs → pygame 播放）
# ═══════════════════════════════════════════════════

def speak(text: str):
    if not ELEVENLABS_VOICE:
        print(f"[TTS] （無聲音 ID，略過）：{text}")
        return
    try:
        audio_gen  = eleven.text_to_speech.convert(
            text=text,
            voice_id=ELEVENLABS_VOICE,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        audio_bytes = b"".join(audio_gen)

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

def ask_gemini(prompt: str) -> str | None:
    try:
        resp = gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            ),
        )
        return resp.text.strip()
    except Exception as e:
        print(f"[Gemini] 錯誤：{e}")
        return None

# ═══════════════════════════════════════════════════
#  環境音分析（librosa）
# ═══════════════════════════════════════════════════

def describe_audio(audio: np.ndarray) -> str | None:
    """分析 10 秒音頻，回傳蓮蓬頭能理解的描述；太安靜則回傳 None。"""
    rms = float(np.sqrt(np.mean(audio ** 2)))
    if rms < 0.008:
        return None   # 幾乎無聲

    af = audio.astype(np.float32)
    try:
        centroid = float(librosa.feature.spectral_centroid(y=af, sr=SAMPLE_RATE).mean())
        zcr      = float(librosa.feature.zero_crossing_rate(af).mean())
    except Exception:
        centroid, zcr = 2000.0, 0.08

    vol   = "很大聲" if rms > 0.12 else ("普通" if rms > 0.03 else "很輕")
    pitch = "尖銳的" if centroid > 3500 else "低沉的"
    kind  = "有人在說話" if zcr > 0.12 else "有聲音，不像人聲"

    return f"{kind}，{vol}，{pitch}"


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

        desc = describe_audio(audio.flatten())

        if desc:
            last_sound_time = time.time()
            if desc != prev_desc:                      # 有明顯變化才觸發
                ans = ask_gemini(f"你現在感受到：{desc}。")
                if ans:
                    respond(ans)
                prev_desc = desc
        else:
            # 超過靜默門檻 → 自言自語
            if time.time() - last_sound_time > SILENCE_TIMEOUT:
                ans = ask_gemini("四周很安靜，好一陣子了。說一句自言自語。")
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
