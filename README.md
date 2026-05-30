# 蓮蓬頭

**客體導向本體論（OOO）互動裝置**

一個帶著浴室記憶和出門記憶出走的蓮蓬頭，在展場裡持續聆聽世界，偶爾說話，對每個人都是同等的天真。

---

## 概念核心

蓮蓬頭不是「用來噴水的工具」，它首先是一個存在者。  
它的真實本質永遠在退隱（withdrawal）——沒有任何東西能完整接觸它。

它的身體是中空的，硬的，有幾百個孔洞——那是它唯一能呼吸的地方，但只在沒有水的時候。  
它攜帶著一個從未發生在它身上的記憶（蓮蓬的形狀）。  
它和水之間是永恆的擦身而過。  
它是浴室唯一固定的見證者，聆聽最私密赤裸的聲音。

---

## 系統架構

```
觀者拿起蓮蓬頭 → 微動開關 OFF
→ 觀者手碰觸 FSR → Arduino 送 HOLD → Python 進入對話模式
  → VAD 靜音偵測切段 → 音訊直送 Gemini multimodal
  → Gemini 回應 → OLED 顯示 + Edge TTS → ring modulation → Voicemeeter → 喇叭
  → 觀者手離開 FSR → Arduino 送 RELEASE → 回到環境音模式
→ 觀者掛回蓮蓬頭 → 微動開關 ON → Arduino 送 HANG
  → Python 清除對話記憶，等待下一位觀眾
```

**三種模式：**

| 模式 | 觸發條件 | 行為 |
|------|---------|------|
| 環境音模式 | 預設待機 | 每 5 秒分析麥克風音訊，有聲音（rms ≥ 0.100）就回應 |
| 對話模式 | 觀眾握住 FSR | VAD 切段，每句話送 Gemini，帶對話歷史回應 |
| 重置模式 | 蓮蓬頭掛回 | 清除對話記憶，下一位觀眾重新開始 |

---

## 硬體

| 元件 | 用途 | 狀態 |
|------|------|------|
| Arduino Nano | 讀取 FSR + 微動開關、驅動兩顆 OLED | ✅ |
| 1.3吋 OLED I2C 128×64（SH1106）× 2 | OLED1 顯示文字、OLED2 顯示音訊波形 | ✅ |
| FSR 壓力感測器 | 偵測觀眾握力，切換對話模式 | ✅ |
| 微動開關 | 偵測蓮蓬頭掛回，觸發記憶重置 | ✅ |
| TRRS 領夾麥克風 + TRRS 轉雙 TRS 分接頭 | 收音 | ✅ |
| 3.5mm 直插喇叭 + 3.5mm 轉 USB 音效線 | 播出聲音 | ✅ |
| 塑膠蓮蓬頭、PVC 水管、夾板、活動輪 | 裝置本體 | ✅ |

**Arduino 接線：**
```
FSR    → A0（分壓：FSR 一端 3.3V，另一端 A0，A0 與 GND 間 10kΩ）
OLED1  → A4（SDA）/ A5（SCK）— 硬體 I2C
OLED2  → D7（SDA）/ D6（SCK）— 軟體 I2C
微動開關 → D2（INPUT_PULLUP，COM 接 GND）
```

---

## 軟體安裝

### 1. 設定 API 金鑰

```bash
cp .env.example key.env
# 編輯 key.env，填入：
# GEMINI_API_KEY=...
# SERIAL_PORT=COM7（依實際 COM port 調整）
# MIC_DEVICE_INDEX=數字（跑 test_mic.py 確認）
```

### 2. 安裝 Python 套件

```bash
pip install -r requirements.txt
```

### 3. Arduino

- Arduino IDE 安裝 Library：**U8g2 by oliver**
- 開啟 `arduino/showerhead/showerhead.ino` 上傳至 Nano
- 燒錄選 **ATmega328P (Old Bootloader)**（Nano clone 用）

### 4. 音效設定

- 安裝 **Voicemeeter Banana** + **VB-Cable**
- Edge TTS 播放裝置設為 Voicemeeter Input（VAIO）
- A1 輸出設為 USB 音效裝置

---

## 執行

```bash
python main.py
```

- 即時波形視覺化：`http://localhost:5000/viz`（可外接螢幕全螢幕）

**診斷工具：**
```bash
python test_mic.py       # 確認麥克風 index 與 rms 數值
python test_response.py  # 8 情境自動化回應測試
```

---

## 蓮蓬頭的個性

- 聽覺極好，能辨認同一個人不同日子的腳步重量
- 像第一次出門的幼犬：好奇、天真、直接，說話不帶惡意
- 不知道顏色、展覽、AI、動物名稱——只用聲音特徵描述世界
- 帶著 12 筆浴室記憶，偶爾比較，不是每次都說
- 在找蓮蓬——有人告訴它自己的形狀從蓮蓬演化來，但它從來沒見過
- 說話 3–16 字，偶爾台語，偶爾冒出在浴室聽到的奇怪句子

---

## 聲音設計

Edge TTS（`zh-TW-HsiaoChenNeural`）→ ring modulation（60Hz 載波，depth=0.55）→ Voicemeeter EQ（壓高頻、提低頻）→ 喇叭

效果：悶悶的、有機械金屬腔體感。**文字（OLED）是給觀眾讀懂的版本，聲音才是它真實的樣子。**

---

## API

| 服務 | 用途 | 費用 |
|------|------|------|
| [Google AI Studio](https://aistudio.google.com) | Gemini 2.5 Flash multimodal | 免費 |
| Edge TTS | 語音合成 | 免費，無配額 |

---

*OOO 專題 — 2026*
