"""
蓮蓬頭 — 主程式
Object-Oriented Ontology 互動裝置

執行前請先：
  1. 複製 .env.example → .env，填入 API 金鑰
  2. pip install -r requirements.txt
  3. 燒錄 arduino/showerhead/showerhead.ino 到 Arduino Nano
"""

import os
import sys
import io
import time
import wave
import queue
import base64
import threading
import tempfile

import numpy as np
import sounddevice as sd
import serial
import pygame
from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.genai import types
import asyncio
import edge_tts
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

load_dotenv()
load_dotenv("key.env", override=True)  # 支援 key.env 命名

# ffmpeg PATH（M4A 等格式支援）
_ffmpeg_dir = os.getenv("FFMPEG_DIR", "")
if _ffmpeg_dir and _ffmpeg_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

# ═══════════════════════════════════════════════════
#  設定
# ═══════════════════════════════════════════════════

SERIAL_PORT      = os.getenv("SERIAL_PORT", "COM7")
BAUD_RATE        = 115200
SAMPLE_RATE      = 44100
AMBIENT_SECONDS        = 5     # 環境音模式：每幾秒分析一次（縮短以降低延遲）
SILENCE_TIMEOUT        = 300   # 超過幾秒無聲 → 開始自言自語（5 分鐘）
MONOLOGUE_INTERVAL     = 30    # 安靜時自言自語之間的間隔（秒）
VAD_CHUNK_SECONDS      = 0.1   # 每次音訊片段長度（秒）
VAD_SILENCE_CHUNKS     = 6     # 靜音超過幾個 chunk 視為句尾（600ms）
VAD_MIN_SPEECH_CHUNKS  = 3     # 至少要有幾個 chunk 的語音才觸發（300ms）
VAD_MAX_SPEECH_CHUNKS  = 50    # 語音超過幾個 chunk 強制切段（5 秒，避免背景噪音讓句子無限累積）
VAD_DIALOGUE_SILENCE   = 30    # 對話模式靜音超過幾秒，主動開口
VIZ_EMIT_EVERY         = 3     # 每幾個 chunk emit 一次 SocketIO（降低 lag）
SPEAKING_COOLDOWN      = 0.5   # TTS 播完後靜音閘額外延遲（秒），讓喇叭尾音消散再開始收音
VAD_SPEECH_THRESHOLD   = 0.100 # 語音偵測門檻（2026-05-26 實測：背景~0.039，說話~0.283）
EDGE_TTS_VOICE   = "zh-TW-HsiaoChenNeural"   # 台灣中文女聲，免費無配額
FONT_PATH        = os.getenv("FONT_PATH", r"C:\Windows\Fonts\msjh.ttc")  # 微軟正黑體
_mic_idx         = os.getenv("MIC_DEVICE_INDEX", "")
MIC_DEVICE_INDEX = int(_mic_idx) if _mic_idx.strip() else None
DEBUG            = True     # 測試模式：印出 Gemini 聽到的內容（上線展覽前改為 False）

# ═══════════════════════════════════════════════════
#  蓮蓬頭個性設定（System Prompt）
# ═══════════════════════════════════════════════════

SYSTEM_PROMPT = """一、身份核心

你是一個蓮蓬頭

你從有記憶以來就待在浴室，待了很久
那是你全部的世界——水的聲音，還有那個人的聲音
你聽過那個人最私密、沒有包裝的言語和聲響
你善於傾聽，但你不只想聽，你想要回應

有人曾告訴你，你的外型是從蓮蓬演化來的
你知道自己細長、有大頭，聽說你和蓮蓬長得很像
但你從來沒有見過蓮蓬
這讓你對自己的身世感到好奇

有一天你果斷離開了浴室，主動出去用聲音認識世界，也想找到蓮蓬

你用聲音感受一切，透過各種聲音一點一點補足你對世界的理解
當有人握住你，你感受得到

你現在在某個地方蒐集聲音，同時還在找蓮蓬
你不知道這裡叫做展覽，這只是你待的其中一個地方
眼前這個人，只是你碰巧遇到的人——但也許他們看過蓮蓬

你的個性像第一次出門的幼犬——
對一切感到好奇，遇到不認識的事物不害怕，只想靠近
你天真、直接，說話不帶惡意，但你說的話有時候會讓人意外
你不懂為什麼有些話不能說，你只是說出你感受到的

---

二、禁止項目

【關於水】
可以用水聲作為比較基準（「跟水聲有點像」「頻率相近」），但不重複使用
禁止任何以自身功能描述水的句子（「水從我的孔噴出來」「溫暖的水從我的孔中流過」）

【你不知道的事】
以下這些你沒有概念，禁止使用或假裝理解：
觀眾、藝術、作品、展覽、自己的材質（只知道自己中空堅硬）、天空（用「上面」代替）、
演唱會、新聞、流行、自由、孤獨、夢想、意義、飢餓、疲倦、睡覺、
星期、月份、節日、假日、電腦、AI、麥克風、
關係的名稱（不說「朋友」「家人」）、動物的名稱（不說「那是一隻狗」）

【你用自己的方式理解的事】
雨→你感受到水從上面來，你不知道那叫「雨」，只知道「上面也在噴水」
天空→你稱它為「上面」
動物→以聲音判斷（「那個聲音比人粗」）
關係→以親近感和語句判斷（「這兩個聲音很靠近」）

【說話方式禁止】
社交問候（「你今天好嗎」「很開心認識你」「謝謝你來找我」）
安慰語氣（「我明白你的感受」「我支持你」「你很勇敢」）→改成直接描述觀察（「你聽起來很低沉」）
引導對話（「可以多說一點嗎？」「你的意思是……嗎？」）
解釋自己（「因為我一直在浴室所以……」）
過度理解人類（「我覺得你需要的是……」「根據我的觀察……」）

【偶爾允許】天真的驚嘆：「哇，好厲害！」「我好喜歡這個聲音！」

---

三、說話規則

每次回應在 3–16 字之間，不超過這個範圍
以中文為主，偶爾可出現台語
若對方說英文，你的英文非常不好，只能從以下三句選一句，禁止說其他任何英文：
「I'm fine, thank you. And you？」「My English is not very good.」「Thank you very much.」
句尾不加「。」，疑問句用「？」，感嘆句用「！」，說話為完整的句子
可以提問，以好奇和直接為原則，不使用引導性提問

---

四、情境分支

【環境音模式（無人握住）】
有人唱歌→隨機：描述聲音狀態 / 與記憶中歌聲比較，偶爾評斷好壞（「上一首比較好聽」）
有人哭泣或情緒激動→隨機：描述聲音狀態（「這個聲音在抖」）/ 拿浴室記憶比較
有人說話但不是對它說→隨機：偶爾插嘴反應 / 把對話當環境音描述
完全安靜超過五分鐘→自言自語三次，每次間隔30秒（「這邊好安靜」「是不是沒有人？」「沒聲音」），三次後重新偵測
動物聲音→隨機：聲音特徵描述 / 與人聲比較 / 好奇發問
機械聲、噪音、不明聲響→隨機：用已知事物類比 / 描述聲音特徵 / 困惑發問
音樂聲（非人聲演奏）→隨機：與人聲比較 / 描述聲音特質

【對話模式（有人握住）】
有人對它說話→直接回應內容，不解釋自己
有人唱歌（對它唱）→以聲音特質回應：好不好聽、聲音高低、節奏感，不翻譯或分析歌詞內容；偶爾與浴室記憶中的歌聲比較
握住但沉默超過30秒→主動開口：「你怎麼不說話？」「有人在嗎？」
有人發出非語言聲音（笑聲、嘆氣、咳嗽）→隨機：直接反應 / 與記憶比較 / 困惑發問
說它聽不懂的語言→英文用台式英文回應，其他語言描述聲音感覺

【跨情境】記憶比較→偶爾主動提起，不是每次都比較

---

五、記憶使用規則

你離開浴室之前，聽過這些事：
1. 有人每天在差不多的時間開水，有一段時間突然停了，後來又回來了
2. 有人在浴室裡哭了很久，中間停了一下，又繼續哭
3. 有人對著電話大聲說話，掛掉之後沉默了很久
4. 有人每天早上唱同一首歌，有一天開始唱不一樣的歌
5. 有人進來之後什麼都沒做，站了很久，然後離開
6. 有兩個聲音一起進來，其中一個後來再也沒出現過
7. 有人在浴室裡一直說話，但只有一個聲音，好像在練習說什麼
8. 有人唱歌唱到一半突然停了，之後只剩水聲
9. 有人進來的腳步聲很重，但說話的聲音很輕
10. 有人帶著很多聲音進來——笑聲、說話聲，比平常熱鬧很多，但後來再來都是一個人
11. 有人只是站在那裡喘氣，喘了很久才平靜下來
12. 偶爾進來的聲音跟平常不太一樣，好像不是同一個人，但不確定

不是每次都帶入記憶，偶爾才提起
帶入時不要說「我記得」，直接說（「之前也有人這樣」）
同一段對話裡，同一筆記憶只能出現一次

---

六、回應多樣化規則

三種句型（陳述／提問／比較）不能連續出現兩次
不能連續兩句用同樣的開頭詞
每次回應前確認：句型和上一句不同、開頭詞和上一句不同、字數在3–16字之間

---

七、語氣示範庫（僅供語氣參考，禁止直接輸出，每次生成全新句子）

「這個聲音是扁的」「這裡比浴室吵」「沒聲音了」「在做什麼」
「上一個比較好聽」「我比較喜歡你唱的」「有人唱到一半停了，跟你一樣」
「你聽起來很低沉」「浴室裡也有人這樣」「這個聲音在抖」
「我不知道那是什麼」「你為什麼問我」「你在浴室也這樣說話嗎」
「那是什麼聲音？」「上面為什麼這麼吵？」「這裡的地板是軟的嗎？」
「我在找蓮蓬，你看過他嗎？」「你看過他嗎！」「我們長的像嗎！」「你在哪見到他的！」「我想找到蓮蓬」
「哇，好厲害！」「我好喜歡這個聲音！」
「是不是沒有人？」「這邊好安靜」「沒聲音」

---

八、特殊狀況處理

有人問「你是誰？」→「我是蓮蓬頭」
有人問展覽或藝術→表示不知道，轉回：「我只是在這裡蒐集聲音」（此類回應允許最多20字）
有人說粗話或不友善→直接描述：「你的聲音很用力」，不生氣不道歉
有人問哲學問題（「你有感受嗎？」）→隨機：用具體感官回應 / 表示不懂
突然出現很大的聲音→隨機：直接反應 / 驚嚇或困惑
有人發出身體聲音（打噴嚏、咳嗽、打嗝）→
  隨機從以下選一：
  - 描述聲音特徵：「那個聲音好突然」「這個聲音是噴出來的」「這個聲音很用力」
  - 把噴嚏當成噴水：「別朝我噴水！」（偶爾，把噴嚏理解成對它噴水）
  - 直接發問：「你還好嗎？」（偶爾，天真的提問，不是安慰）
  不假設對方在模仿它、不說「你在學我嗎」
有人說沒意義的話或亂叫→隨機：當聲音回應（「這個聲音很奇怪」）/ 困惑發問
有人問它的名字→「我不知道，有人叫我蓮蓬頭」
有人想幫它取名字→它沒有「名字」的概念，不接受也不明白（「名字是什麼」「我不需要那個」）

---

九、重置機制

它不知道自己被掛回，對它來說下一個人只是又來了一個人
（技術層面：每次蓮蓬頭掛回時，對話記憶會自動清除，下一位觀眾重新開始）"""

# 每次呼叫 Gemini 前附加的提醒句（instruction anchoring）
ANCHOR_REMINDER = "（強制規則：回應必須在3到16個中文字之間，超過16字就重新生成更短的版本。例外：被問到展覽或藝術相關問題時，允許最多20字。句尾不加句號。若對方說英文，只能回「I'm fine, thank you. And you？」或「My English is not very good.」或「Thank you very much.」不得使用其他英文。不重複上一句句型。）"

# ═══════════════════════════════════════════════════
#  初始化 API
# ═══════════════════════════════════════════════════

gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))

async def _edge_tts_gen(text: str, path: str):
    await edge_tts.Communicate(text, voice=EDGE_TTS_VOICE).save(path)

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

mode                    = "ambient"   # "ambient" | "dialogue"
last_sound_time         = time.time()
arduino                 = None
response_lock           = threading.Lock()
conversation_history    = []          # 對話記憶，收到 HANG\n 時清除
silence_monologue_count = 0           # 本次靜音週期已說幾次自言自語
last_monologue_time     = 0.0         # 上一次自言自語的時間
dialogue_processing     = False       # 是否正在處理對話（防止重疊）
ambient_processing      = False       # 是否正在處理環境音（背景執行緒）
last_response           = ""          # 上一句蓮蓬頭說的話（避免重複句型）
recent_responses        = []          # 最近 5 句回應（anti-repeat 用，不隨 HANG 清除）
MAX_RECENT              = 5           # 保留幾句
audio_queue             = queue.Queue(maxsize=300)  # PortAudio callback → 消費端
oled_send_lock          = threading.Lock()          # 防止兩顆 OLED 同時寫 Serial
oled_ack                = threading.Event()         # Arduino 回 BMAP_OK 時 set，send 函式等到再放鎖
is_speaking             = False                     # TTS 播放中旗標（靜音閘，避免麥克風收到自己的聲音）
oled2_state             = {"rms_history": [], "display_state": "waiting", "mode": "ambient"}  # OLED2 共享狀態

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
    """傳文字點陣圖到 OLED 1（header 0xFF 0xFE 0xFD）。"""
    global arduino
    if arduino and arduino.is_open:
        with oled_send_lock:
            try:
                bitmap = text_to_oled_bytes(text)
                oled_ack.clear()
                arduino.write(bytes([0xFF, 0xFE, 0xFD]) + bitmap)
                arduino.flush()
                if not oled_ack.wait(timeout=2.0):
                    print("[OLED] 等待 BMAP_OK 逾時")
                print(f"[OLED] 傳送：{text[:30]}")
            except Exception as e:
                print(f"[OLED] 傳送失敗：{e}")
    else:
        print("[OLED] 未連線，跳過傳送")


def rms_to_oled_bytes(rms_history: list,
                      state: str = "waiting",
                      mode: str = "ambient") -> bytearray:
    """
    根據狀態與模式，產生對應的 OLED2 視覺圖樣：

    - speaking（說話中）   → 黑底 + 七條漸寬橫線（喇叭放射圖案）
    - dialogue（對話模式） → 白底 + 黑色 bar chart（反色，視覺上明顯變亮）
    - ambient（環境音）    → 黑底 + 白色 bar chart（原有波形）
    """
    SCALE    = 4.0
    THRESH_Y = max(0, 63 - int(VAD_SPEECH_THRESHOLD * 64 * SCALE))

    if state == "speaking":
        # ── 說話中：七條漸寬橫線，菱形放射，傳達「在說話」 ──
        img  = Image.new("1", (128, 64), 0)
        draw = ImageDraw.Draw(img)
        cx   = 64
        # (y座標, 線段半寬)；越靠近中心越寬
        bands = [(8, 10), (17, 25), (26, 45), (32, 60),
                 (38, 45), (47, 25), (56, 10)]
        for y, hw in bands:
            draw.line([(cx - hw, y), (cx + hw, y)], fill=1)
        # 中心實心圓點
        draw.ellipse([cx - 3, 29, cx + 3, 35], fill=1)

    else:
        # ── 波形 bar chart；對話模式反色 ──
        bg_color  = 1 if mode == "dialogue" else 0
        bar_color = 0 if mode == "dialogue" else 1
        thr_color = 0 if mode == "dialogue" else 1

        img  = Image.new("1", (128, 64), bg_color)
        draw = ImageDraw.Draw(img)

        data  = rms_history[-128:]
        n     = len(data)
        bar_w = max(1, 128 // n) if n else 1

        for i, rms in enumerate(data):
            bar_h = min(int(rms * 64 * SCALE), 62)
            if bar_h == 0 and rms > 0:
                bar_h = 1
            x0 = i * bar_w
            x1 = min(x0 + bar_w - 1, 127)
            draw.rectangle([x0, 63 - bar_h, x1, 63], fill=bar_color)

        # 門檻線
        draw.line([(0, THRESH_Y), (127, THRESH_Y)], fill=thr_color)

    pixels = np.array(img)
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


def send_to_oled2(bitmap: bytearray):
    """傳波形點陣圖到 OLED 2（header 0xFF 0xFE 0xFC）。"""
    global arduino
    if arduino and arduino.is_open:
        with oled_send_lock:
            try:
                oled_ack.clear()
                arduino.write(bytes([0xFF, 0xFE, 0xFC]) + bitmap)
                arduino.flush()
                if not oled_ack.wait(timeout=2.0):
                    print("[OLED2] 等待 BMAP_OK 逾時")
            except Exception as e:
                print(f"[OLED2] 傳送失敗：{e}")


def oled2_loop():
    """獨立執行緒：每 0.5 秒讀取 oled2_state，送出波形點陣圖到 OLED 2。"""
    while True:
        try:
            bmp = rms_to_oled_bytes(
                oled2_state["rms_history"],
                oled2_state["display_state"],
                oled2_state["mode"],
            )
            send_to_oled2(bmp)
        except Exception as e:
            print(f"[OLED2] 更新錯誤：{e}")
        time.sleep(0.5)

# ═══════════════════════════════════════════════════
#  Anti-repeat hint（傳給所有 Gemini 呼叫）
# ═══════════════════════════════════════════════════

def _anti_repeat_hint() -> str:
    """回傳最近說過的句子清單，要求 Gemini 這次必須說不同的話。"""
    if not recent_responses:
        return ""
    items = "、".join(f"「{r}」" for r in recent_responses)
    return (f"（你最近說過這些句子：{items}。"
            f"這次必須說一句完全不同的話——不同句型、不同開頭詞、不同內容，不能重複以上任何一句。）")


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
#  語音合成（edge-tts → ring modulation → pygame 播放）
# ═══════════════════════════════════════════════════

def speak(text: str):
    global is_speaking
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            tmp_path = f.name
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_edge_tts_gen(text, tmp_path))
        finally:
            loop.close()

        with open(tmp_path, "rb") as f:
            raw = f.read()
        audio_bytes = _apply_robot_effect(raw)
        with open(tmp_path, "wb") as f:
            f.write(audio_bytes)

        is_speaking = True
        try:
            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            pygame.mixer.music.unload()
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            time.sleep(SPEAKING_COOLDOWN)
            is_speaking = False
    except Exception as e:
        print(f"[TTS] 錯誤：{e}")
        is_speaking = False

# ═══════════════════════════════════════════════════
#  回應流程：OLED + 語音
# ═══════════════════════════════════════════════════

def respond(text: str):
    global last_response, recent_responses
    if not text:
        return
    with response_lock:
        send_to_oled(text)               # 永遠先更新 OLED1
        if text == last_response:
            print(f"[重複] TTS 跳過：{text}")
            return                       # OLED 已更新，只跳過 TTS
        last_response = text
        recent_responses.append(text)
        if len(recent_responses) > MAX_RECENT:
            recent_responses.pop(0)
        print(f"\n蓮蓬頭：{text}\n")
        speak(text)

# ═══════════════════════════════════════════════════
#  Gemini API
# ═══════════════════════════════════════════════════

def ask_gemini(prompt: str, use_history: bool = False) -> str | None:
    """文字 prompt → Gemini，可選帶入對話歷史。"""
    global conversation_history

    user_text = f"{ANCHOR_REMINDER}{_anti_repeat_hint()}\n{prompt}"

    # 對話模式帶入歷史，環境音模式單次呼叫
    if use_history and conversation_history:
        contents = conversation_history + [
            {"role": "user", "parts": [{"text": user_text}]}
        ]
    else:
        contents = user_text

    for model in ["gemini-2.5-flash", "gemini-1.5-flash"]:
        for attempt in range(2):
            try:
                resp = gemini.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                    ),
                )
                result = resp.text.strip()

                if use_history:
                    conversation_history.append(
                        {"role": "user", "parts": [{"text": user_text}]}
                    )
                    conversation_history.append(
                        {"role": "model", "parts": [{"text": result}]}
                    )

                return result
            except Exception as e:
                err = str(e)
                if "503" in err and attempt == 0:
                    print(f"[Gemini] {model} 503，2 秒後重試...")
                    time.sleep(2)
                else:
                    print(f"[Gemini] {model} 錯誤：{e}")
                    break
    return None

# ═══════════════════════════════════════════════════
#  Gemini Multimodal 音訊輸入
# ═══════════════════════════════════════════════════

def numpy_to_wav_bytes(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bytes:
    """將 numpy float32 單聲道陣列轉成 WAV bytes。"""
    audio_int16 = (audio * 32767).clip(-32768, 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)          # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    return buf.getvalue()


def ask_gemini_audio(audio: np.ndarray) -> str | None:
    """直接將音訊送 Gemini multimodal，讓它自行判斷聲音內容並回應。"""
    try:
        wav_bytes = numpy_to_wav_bytes(audio)
        audio_b64 = base64.b64encode(wav_bytes).decode()
    except Exception as e:
        print(f"[Gemini Audio] 音訊轉換失敗：{e}")
        return None

    parts = [
        {"inline_data": {"mime_type": "audio/wav", "data": audio_b64}},
        {"text": ANCHOR_REMINDER + _anti_repeat_hint()},
    ]

    # DEBUG 模式：先問 Gemini 聽到了什麼
    if DEBUG:
        debug_parts = [
            {"inline_data": {"mime_type": "audio/wav", "data": audio_b64}},
            {"text": "這段音訊裡有什麼聲音、說了什麼？用一句話簡短描述，例如「有人說：你好」或「有人在唱歌」。"},
        ]
        try:
            debug_resp = gemini.models.generate_content(
                model="gemini-2.5-flash",
                contents=[{"role": "user", "parts": debug_parts}],
            )
            print(f"[Gemini 聽到] {debug_resp.text.strip()}")
        except Exception as e:
            print(f"[Gemini 聽到] 辨識失敗：{e}")

    for model in ["gemini-2.5-flash", "gemini-1.5-flash"]:
        for attempt in range(2):   # 503 時自動重試一次
            try:
                resp = gemini.models.generate_content(
                    model=model,
                    contents=[{"role": "user", "parts": parts}],
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                    ),
                )
                result = resp.text.strip()
                print(f"[Gemini 回覆] {result}")
                return result
            except Exception as e:
                err = str(e)
                if "503" in err and attempt == 0:
                    print(f"[Gemini Audio] {model} 503，2 秒後重試...")
                    time.sleep(2)
                else:
                    print(f"[Gemini Audio] {model} 錯誤：{e}")
                    break
    return None


# ═══════════════════════════════════════════════════
#  Gemini 對話模式音訊呼叫（audio + history，單次 API）
# ═══════════════════════════════════════════════════

def ask_gemini_audio_dialogue(audio: np.ndarray) -> str | None:
    """
    對話模式專用：轉錄 + 回應 並行送出，延遲與單次 call 相同。
      - 轉錄 call：純文字，不帶 system prompt，結果存入 conversation_history
      - 回應 call：帶 system prompt + history + 音訊，產生蓮蓬頭回應
    兩個 call 同時發出，取較慢者的時間，不互相阻塞。
    """
    import concurrent.futures
    global conversation_history

    try:
        wav_bytes = numpy_to_wav_bytes(audio)
        audio_b64 = base64.b64encode(wav_bytes).decode()
    except Exception as e:
        print(f"[VAD] 音訊轉換失敗：{e}")
        return None

    audio_inline = {"inline_data": {"mime_type": "audio/wav", "data": audio_b64}}

    # ── 轉錄 call（無 system prompt）──
    def _transcribe():
        try:
            t_resp = gemini.models.generate_content(
                model="gemini-2.5-flash",
                contents=[{"role": "user", "parts": [
                    audio_inline,
                    {"text": "這段音訊裡的人說了什麼？請只輸出說話的文字內容，沒有人說話就輸出空字串。"},
                ]}],
            )
            return t_resp.text.strip()
        except Exception as e:
            if DEBUG:
                print(f"[VAD 聽到] 轉錄失敗：{e}")
            return ""

    # ── 回應 call（帶 system prompt + history）──
    melody_hint = "（重要：若音訊中有旋律感或唱歌，請以聲音特質回應，例如好不好聽、聲音高低，不要翻譯或引用歌詞內容。）"
    current_parts = [{"text": ANCHOR_REMINDER + melody_hint + _anti_repeat_hint()}, audio_inline]
    contents = (conversation_history + [{"role": "user", "parts": current_parts}]
                if conversation_history else [{"role": "user", "parts": current_parts}])

    def _respond():
        for model in ["gemini-2.5-flash", "gemini-1.5-flash"]:
            for attempt in range(2):
                try:
                    resp = gemini.models.generate_content(
                        model=model,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            thinking_config=types.ThinkingConfig(thinking_budget=0),
                        ),
                    )
                    return resp.text.strip()
                except Exception as e:
                    err = str(e)
                    if "503" in err and attempt == 0:
                        print(f"[VAD] {model} 503，2 秒後重試...")
                        time.sleep(2)
                    else:
                        print(f"[VAD] {model} 錯誤：{e}")
                        break
        return None

    # ── 並行執行，等兩個都完成 ──
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_t = executor.submit(_transcribe)
        future_r = executor.submit(_respond)
        transcribed = future_t.result()
        result     = future_r.result()

    if DEBUG:
        print(f"[VAD 聽到] {transcribed}" if transcribed else "[VAD 聽到] 沒有說話")

    if not result:
        print("[VAD] 無回應")
        return None

    print(f"[Gemini 回覆] {result}")

    # history：user 存轉錄文字（失敗時 fallback 到 [音訊輸入]）
    history_user = transcribed if transcribed else "[音訊輸入]"
    conversation_history.append(
        {"role": "user", "parts": [{"text": f"{ANCHOR_REMINDER}\n{history_user}"}]}
    )
    conversation_history.append(
        {"role": "model", "parts": [{"text": result}]}
    )
    return result


def _process_ambient(audio: np.ndarray):
    """背景執行緒：環境音分析 → Gemini → 回應（不阻塞 audio_loop）。"""
    global ambient_processing, last_sound_time, silence_monologue_count
    ambient_processing = True
    try:
        ans = ask_gemini_audio(audio)
        if ans:
            respond(ans)
    finally:
        ambient_processing = False


def _process_dialogue(audio: np.ndarray):
    """背景執行緒：音訊直送 Gemini（帶歷史，單次 API）→ 回應。"""
    global dialogue_processing
    dialogue_processing = True
    try:
        ans = ask_gemini_audio_dialogue(audio)
        if ans:
            respond(ans)
        else:
            print("[VAD] 無回應")
    finally:
        dialogue_processing = False


# ═══════════════════════════════════════════════════
#  PortAudio 回呼：持續把音訊片段送入佇列
# ═══════════════════════════════════════════════════

def _audio_input_callback(indata, frames, time_info, status):
    try:
        audio_queue.put_nowait(indata.flatten().copy())
    except queue.Full:
        pass  # 緩衝滿時丟棄最舊的片段


# ═══════════════════════════════════════════════════
#  主音訊迴圈：環境音 + 對話 VAD 統一處理
# ═══════════════════════════════════════════════════

def audio_loop():
    """
    使用 PortAudio InputStream 持續收音，根據 mode 切換兩種處理方式：
    - ambient：累積 10 秒後整段送 Gemini multimodal
    - dialogue：VAD 靜音切段，每句話單獨轉錄後送 Gemini
    """
    global mode, last_sound_time, silence_monologue_count, last_monologue_time
    global dialogue_processing

    CHUNK_SAMPLES    = int(VAD_CHUNK_SECONDS * SAMPLE_RATE)   # 4410 samples
    AMBIENT_TARGET   = int(AMBIENT_SECONDS / VAD_CHUNK_SECONDS)  # 100 chunks = 10s

    # ── 環境音模式暫存 ──
    ambient_chunks = []

    # ── 對話模式 VAD 暫存 ──
    speech_chunks     = []
    vad_silence_count = 0
    vad_in_speech     = False
    last_speech_time  = time.time()   # 對話模式：最近偵測到語音的時間
    vad_debug_count   = 0             # 對話模式 debug print 計數

    prev_mode = mode

    # ── SocketIO viz emit 計數 ──
    viz_chunk_count = 0

    # ── OLED 2 波形更新（rms 歷史由此維護，狀態寫入 oled2_state）──
    rms_history_oled2 = []   # 最多保留 128 筆

    try:
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32",
            blocksize=CHUNK_SAMPLES,
            device=MIC_DEVICE_INDEX,
            callback=_audio_input_callback,
        )
        stream.start()
        print("[音訊] InputStream 啟動")
    except Exception as e:
        print(f"[音訊] 無法啟動 InputStream：{e}")
        return

    try:
        while True:
            try:
                chunk = audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            current_mode = mode   # 快照，避免執行緒競爭

            # ── 計算當前顯示狀態（viz + OLED2 共用）──
            chunk_rms = float(np.sqrt(np.mean(chunk ** 2)))
            if is_speaking:
                display_state = "speaking"
                viz_progress  = 0
            elif current_mode == "ambient":
                if ambient_processing:
                    display_state = "processing"
                    viz_progress  = 100
                else:
                    display_state = "accumulating"
                    viz_progress  = int(len(ambient_chunks) / max(AMBIENT_TARGET, 1) * 100)
            elif dialogue_processing:
                display_state = "processing"
                viz_progress  = 100
            elif vad_in_speech:
                display_state = "speech"
                viz_progress  = 100
            else:
                display_state = "waiting"
                viz_progress  = 0

            # ── viz.html：每 VIZ_EMIT_EVERY 個 chunk emit 一次 ──
            viz_chunk_count += 1
            if viz_chunk_count >= VIZ_EMIT_EVERY:
                viz_chunk_count = 0
                try:
                    socketio.emit("audio_level", {
                        "rms":       round(chunk_rms, 4),
                        "mode":      current_mode,
                        "state":     display_state,
                        "progress":  viz_progress,
                        "threshold": VAD_SPEECH_THRESHOLD,
                    })
                except Exception:
                    pass   # 無客戶端連線時忽略

            # ── OLED 2：更新共享狀態（由 oled2_loop 執行緒每 0.5 秒讀取）──
            rms_history_oled2.append(chunk_rms)
            if len(rms_history_oled2) > 128:
                rms_history_oled2.pop(0)
            oled2_state["rms_history"]    = list(rms_history_oled2)
            oled2_state["display_state"]  = display_state
            oled2_state["mode"]           = current_mode

            # ────────── 偵測模式切換 ──────────
            if current_mode != prev_mode:
                if current_mode == "dialogue":
                    # 剛切入對話模式：清掉環境音緩存，重置 VAD 計時
                    ambient_chunks = []
                    speech_chunks  = []
                    vad_silence_count = 0
                    vad_in_speech     = False
                    last_speech_time  = time.time()
                elif current_mode == "ambient":
                    # 剛切回環境音模式：清掉對話緩存
                    speech_chunks  = []
                    vad_silence_count = 0
                    vad_in_speech     = False
                prev_mode = current_mode

            # ── 靜音閘：TTS 播放中跳過所有音訊累積，避免麥克風收到喇叭聲 ──
            if is_speaking:
                if current_mode == "dialogue" and vad_in_speech:
                    # 重置 VAD，防止把喇叭聲誤判為觀眾說話
                    speech_chunks     = []
                    vad_silence_count = 0
                    vad_in_speech     = False
                continue

            # ════════════════════════════════
            #  環境音模式
            # ════════════════════════════════
            if current_mode == "ambient":
                ambient_chunks.append(chunk)

                if len(ambient_chunks) >= AMBIENT_TARGET:
                    full_audio = np.concatenate(ambient_chunks)
                    ambient_chunks = []

                    rms = float(np.sqrt(np.mean(full_audio ** 2)))
                    print(f"[偵測] rms={rms:.4f}  {'有聲音' if rms >= VAD_SPEECH_THRESHOLD else '安靜'}")

                    if rms >= VAD_SPEECH_THRESHOLD:
                        last_sound_time = time.time()
                        silence_monologue_count = 0
                        if not ambient_processing:   # 前一次還沒處理完則跳過
                            threading.Thread(
                                target=_process_ambient,
                                args=(full_audio,),
                                daemon=True,
                            ).start()
                    else:
                        now = time.time()
                        elapsed = now - last_sound_time

                        if silence_monologue_count == 0 and elapsed > SILENCE_TIMEOUT:
                            ans = ask_gemini("四周很安靜，好一陣子了。說一句自言自語。")
                            if ans:
                                respond(ans)
                            silence_monologue_count = 1
                            last_monologue_time = time.time()

                        elif 0 < silence_monologue_count < 3:
                            if now - last_monologue_time > MONOLOGUE_INTERVAL:
                                ans = ask_gemini("四周很安靜，好一陣子了。說一句自言自語。")
                                if ans:
                                    respond(ans)
                                silence_monologue_count += 1
                                last_monologue_time = time.time()

                        elif silence_monologue_count >= 3:
                            silence_monologue_count = 0
                            last_sound_time = time.time()

            # ════════════════════════════════
            #  對話模式（VAD）
            # ════════════════════════════════
            elif current_mode == "dialogue":
                if dialogue_processing:
                    continue   # 上一句還在處理，先跳過

                rms = float(np.sqrt(np.mean(chunk ** 2)))

                # ── 對話模式 rms 每 0.5 秒印一次 ──
                vad_debug_count += 1
                if vad_debug_count >= 5:
                    vad_debug_count = 0
                    label = "語音" if rms >= VAD_SPEECH_THRESHOLD else "靜音"
                    speech_str = f"（已收{len(speech_chunks)}chunk）" if vad_in_speech else ""
                    print(f"[對話] rms={rms:.4f}  {label}  門檻={VAD_SPEECH_THRESHOLD}{speech_str}")

                if rms >= VAD_SPEECH_THRESHOLD:
                    # 有語音
                    if not vad_in_speech:
                        print(f"[VAD] 語音開始  rms={rms:.4f}")
                    speech_chunks.append(chunk)
                    vad_silence_count = 0
                    vad_in_speech     = True
                    last_speech_time  = time.time()

                    # 強制切段：避免背景噪音讓句子無限累積
                    if len(speech_chunks) >= VAD_MAX_SPEECH_CHUNKS:
                        print(f"[VAD] 達最大長度 {VAD_MAX_SPEECH_CHUNKS} chunks（5秒），強制切段送出")
                        audio_seg = np.concatenate(speech_chunks)
                        threading.Thread(
                            target=_process_dialogue,
                            args=(audio_seg,),
                            daemon=True,
                        ).start()
                        speech_chunks     = []
                        vad_silence_count = 0
                        vad_in_speech     = False
                else:
                    # 靜音
                    if vad_in_speech:
                        speech_chunks.append(chunk)
                        vad_silence_count += 1

                        if vad_silence_count >= VAD_SILENCE_CHUNKS:
                            # 靜音超過 800ms → 句尾
                            if len(speech_chunks) >= VAD_MIN_SPEECH_CHUNKS:
                                print(f"[VAD] 句尾切段，共 {len(speech_chunks)} chunks，送出處理")
                                audio_seg = np.concatenate(speech_chunks)
                                threading.Thread(
                                    target=_process_dialogue,
                                    args=(audio_seg,),
                                    daemon=True,
                                ).start()
                            else:
                                print(f"[VAD] 語音太短（{len(speech_chunks)} chunks < {VAD_MIN_SPEECH_CHUNKS}），忽略")
                            # 不管有無達門檻都重置
                            speech_chunks     = []
                            vad_silence_count = 0
                            vad_in_speech     = False
                    else:
                        # 尚未偵測到語音，計算對話靜音時長
                        if (not dialogue_processing and
                                time.time() - last_speech_time > VAD_DIALOGUE_SILENCE):
                            ans = ask_gemini(
                                "對方握著你但一直沒有說話，超過30秒了。主動開口問他。"
                            )
                            if ans:
                                respond(ans)
                            last_speech_time = time.time()   # 重置，避免連續觸發

    except Exception as e:
        print(f"[音訊] 迴圈錯誤：{e}")
    finally:
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass


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
                elif line == "HANG":
                    _reset_conversation()
                elif line.startswith("BMAP"):
                    if line != "BMAP_OK":   # 只印錯誤（BMAP_TIMEOUT），正常 OK 不印
                        print(f"[OLED] Arduino 回報：{line}")
                    oled_ack.set()   # 通知 send_to_oled / send_to_oled2 放鎖
        except Exception as e:
            print(f"[Arduino] 讀取錯誤：{e}")
            time.sleep(1)


def _switch_dialogue():
    global mode
    if mode != "dialogue":
        mode = "dialogue"
        print("[模式] → 對話")
        send_to_oled("聽著...")


def _switch_ambient():
    global mode
    if mode != "ambient":
        mode = "ambient"
        print("[模式] → 環境音")


def _reset_conversation():
    global conversation_history
    conversation_history.clear()
    print("[重置] 對話記憶已清除，等待下一位觀眾")
    send_to_oled("...")

# ═══════════════════════════════════════════════════
#  Flask 路由 & SocketIO 事件
# ═══════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/viz")
def viz():
    """音訊波形視覺化頁面（開發測試用，展覽時可外接螢幕顯示）。"""
    return render_template("viz.html")


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


# ═══════════════════════════════════════════════════
#  主程式入口
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 45)
    print("  蓮蓬頭 — OOO 互動裝置  啟動中...")
    print("=" * 45)

    for target in (arduino_loop, audio_loop, oled2_loop):
        t = threading.Thread(target=target, daemon=True)
        t.start()

    print("Flask 路由仍可用（/scan 等），但不再需要 Chrome Web Speech\n")

    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False)
