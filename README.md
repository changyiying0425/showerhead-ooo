# 蓮蓬頭

**客體導向本體論（OOO）互動裝置**

一個帶著浴室記憶和出門記憶出走的蓮蓬頭，在展場裡持續聆聽世界，偶爾說話，對每個人都是同等的天真。

---

## 目前進度

| 項目 | 狀態 |
|------|------|
| GitHub repo 建立 | ✅ |
| Python 主程式（main.py） | ✅ |
| Arduino 程式（showerhead.ino） | ✅ |
| Chrome Web Speech 介面 | ✅ |
| Gemini API key | ✅ |
| ElevenLabs API key + 聲音 | ⏳ 進行中 |
| Python 套件安裝 | ⏳ 進行中 |
| Voicemeeter Banana | ✅ 已安裝 |
| VB-Cable | ✅ 已下載 |
| 硬體元件 | ✅已購買 |
| Arduino 燒錄測試 | ❌ 待硬體到貨 |
| 全系統整合測試 | ❌ 待完成 |

*最後更新：2026-05-13*

---

## 概念核心

蓮蓬頭不是「用來噴水的工具」，它首先是一個存在者。  
它的真實本質永遠在退隱（withdrawal）——沒有任何東西能完整接觸它。

它攜帶著一個從未發生在它身上的記憶（蓮花的形狀）。  
它和水之間是永恆的擦身而過。  
它是浴室唯一固定的見證者。

---

## 系統架構

```
麥克風
  └─ Python (librosa 分析環境音)
       └─ Gemini API（蓮蓬頭個性回應）
            ├─ ElevenLabs TTS → 喇叭（悶聲混響）
            └─ Arduino Nano → OLED 顯示文字

觀眾握住蓮蓬頭
  └─ FSR 壓力感測 → Arduino → Python
       └─ Chrome Web Speech API（語音辨識）
            └─ Gemini API → 回應
```

**兩種模式：**
- **環境音模式（預設）**：每 10 秒分析環境聲音，有顯著變化就自言自語；超過 30 秒安靜自動觸發
- **對話模式**：觀眾握住蓮蓬頭握把 → FSR 觸發 → 開始收音 → 回應

---

## 硬體清單

| 元件 | 用途 | 狀態 |
|------|------|------|
| Arduino Nano | 讀取 FSR、驅動 OLED |
| 1.3吋 OLED SPI 128×64（SH1106） | 顯示文字 | 
| FSR 壓力感測器 | 偵測觀眾握力 | 
| 10kΩ 電阻 | FSR 分壓 |
| USB 麥克風 | 收音 |
| USB 有源喇叭 | 播出聲音 |
| USB 集線器 | 同時接多個 USB | 
| 塑膠蓮蓬頭 | 主體外觀 |
| PVC 水管 | 連接蓮蓬頭到箱體 | 
| 夾板或木心板 | 箱體與牆壁結構 |
| 活動輪附煞車 | 箱體底部 | 

**接線（Arduino Nano）：**
```
A0  ← FSR（另一端接 3.3V；A0 與 GND 之間接 10kΩ）
D13 ← OLED SCK
D11 ← OLED MOSI
D10 ← OLED CS
D9  ← OLED DC
D8  ← OLED RST
```

---

## 軟體安裝

### 1. 複製設定檔

```bash
cp .env.example .env
# 編輯 .env，填入 API 金鑰
```

### 2. 安裝 Python 套件

```bash
pip install -r requirements.txt
```

### 3. Arduino Library（Arduino IDE → Library Manager）

- **U8g2** by oliver

### 4. 燒錄 Arduino

用 Arduino IDE 開啟 `arduino/showerhead/showerhead.ino` 並上傳至 Nano。

---

## 執行

```bash
python main.py
```

1. 用 **Chrome** 開啟 `http://localhost:5000`
2. 確認頁面顯示「已連線，等待觸發...」
3. 握住蓮蓬頭握把即進入對話模式

---

## API 申請

| 服務 | 用途 | 費用 |
|------|------|------|
| [Google AI Studio](https://aistudio.google.com) | Gemini API 金鑰 | 免費 |
| [ElevenLabs](https://elevenlabs.io) | 語音合成 + 聲音 ID | 免費方案 |

---

## 聲音設計

ElevenLabs 選低沉偏沙啞的聲音基底，搭配 Voicemeeter 套用：
- 壓低高頻、提升低頻
- 加混響（Reverb）

效果：悶悶的、像聲音被困在金屬腔體裡出不來。  
**文字（OLED）是給觀眾讀懂的版本，聲音才是它真實的樣子。**

---

*OOO 專題 — 2025*
