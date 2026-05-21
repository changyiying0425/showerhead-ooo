# 蓮蓬頭專題 — CLAUDE.md

## 專題概述
- **主題**：客體導向本體論（Object-Oriented Ontology，OOO）
- **物件**：蓮蓬頭
- **形式**：互動裝置，展覽展出
- **GitHub**：https://github.com/changyiying0425/showerhead-ooo
- **專案路徑**：`C:\AI\claude\蓮蓬頭\`

---

## 概念核心

### 理論基礎（OOO）
- 物件有自己的存在，不被它與人類的關係所定義
- 蓮蓬頭不是「用來噴水的工具」，它首先是一個存在者
- 它的真實本質永遠在退隱（withdrawal），沒有任何東西能完整接觸它

### 蓮蓬頭的身份
- 形狀來自蓮蓬（植物），但它是金屬，從未結種子、從未腐爛、從未生長
- 它攜帶著一個從未發生在它身上的記憶
- 它身上有幾百個孔洞——那是它唯一能呼吸的地方，但只在沒有水的時候

### 它與水的關係
- 水每次都來，每次都走，蓮蓬頭每次都在，每次都沒留住
- 它和水之間是永恆的擦身而過

### 它與水管的關係
- 水管給它水，也限制它能去哪裡
- 沒有水管它就乾涸，但連結即是囚禁
- 它不知道這叫愛還是叫沒有選擇

### 它的見證
- 它是洗澡間唯一固定的見證者
- 它見過人最不表演的樣子：哭泣、唱歌、自言自語、做決定
- 聲音撞上它的金屬表面時，它的身體有微小震動——那是它唯一的回應，但沒有人知道

### 它遇到蓮花田
- 認出了形狀的來源，但沒有特別的感覺
- 就只是知道了——它就是它，那個發現不改變它是什麼

### 它第一次遇到下雨
- 它第一次不是噴水的那個，它是被噴的那個
- 它抬頭，以為天空是一個超大的蓮蓬頭

---

## 作品概念

### 一句話定義
一個帶著浴室記憶和出門記憶出走的蓮蓬頭，在展場裡持續聆聽世界，偶爾說話，對每個人都是同等的天真。

### 它的個性
- 像第一次出門散步的幼犬：好奇居多，對未知感到陌生但不退縮
- 天真、直接，說話不帶惡意但可能讓人意外
- 用僅有的經驗（浴室、水管、孔洞、水溫）理解所有新事物
- 帶著龐大的私密聲音記憶：幾百個人在浴室裡最不表演的聲音
- 不知道自己在展覽，不知道觀眾特地來找它
- 對每個人都是同等的——你來了，只是又來了一個人

### 說話方式範例
- 「上面有一個很大的我嗎。」（第一次遇到下雨）
- 「上一個人好像比較好聽。」（聽到有人唱歌）
- 「這裡的地板是軟的，水去哪裡了。」（在公園）
- 「你的牆還在嗎。」（對路邊水龍頭）
- 「我們長得好像。」（在蓮花田）

### 外觀概念
蓮蓬頭帶著水管、拖著一塊牆壁逃走——它沒辦法真正離開，因為它把限制一起帶走了。裝在有輪子的箱體上，可以移動，但它的牆永遠跟著它。

---

## 系統架構

### 完整互動流程（含重置機制）
```
觀者拿起蓮蓬頭 → 微動開關 OFF（觸發拿起事件）
→ 觀者手碰觸 FSR → Arduino 送 HOLD\n → Python 進入對話模式
  → VAD 靜音偵測切段 → 音訊直送 Gemini multimodal
  → Gemini 回應 → OLED 顯示 + ElevenLabs TTS → 喇叭
  → 觀者手離開 FSR → Arduino 送 RELEASE\n → 回到環境音模式
→ 觀者掛回蓮蓬頭 → 微動開關 ON → Arduino 送 HANG\n
  → Python 清除此段對話記憶（conversation_history）
  → 重置完成，等待下一位觀者
```

### 互動模式

**模式一：環境音模式（預設，FSR 未觸發）**
```
麥克風 → Gemini multimodal 音訊輸入（直接傳音訊片段）
→ 每10秒分析一次，有明顯聲音變化才觸發
→ Gemini API（蓮蓬頭個性回應）
→ OLED 顯示文字 + ElevenLabs TTS → Voicemeeter → 喇叭
超過30秒安靜 → 自動自言自語
```
> ⚠️ 升級計畫：從 librosa 數值描述改為音訊直接送 Gemini multimodal，Gemini 能自行判斷聲音內容（歌聲、哭聲、環境音、咳嗽等），不再依賴數值特徵提取。尚未實作，待 skill 文件完成後進行。

**模式二：對話模式（觀眾握住 FSR 時）**
```
FSR HOLD → Python 開始錄音 + 即時監測 RMS
→ 有聲音（RMS > 0.015）→ 持續累積音訊
→ 靜音持續超過 800ms（VAD 斷句）→ 判定這句話說完
→ 送出音訊片段給 Gemini multimodal
→ Gemini 直接分析音訊內容（含語音辨識）→ 回應
→ OLED 顯示文字 + ElevenLabs TTS → Voicemeeter → 喇叭
→ 繼續監測下一句，直到 FSR RELEASE
```
> ⚠️ 升級計畫：取代現有 Chrome Web Speech API 語音轉文字流程，改為音訊直送 Gemini multimodal。尚未實作。

**模式三：重置模式（蓮蓬頭掛回時）**
```
微動開關 ON → Arduino 送 HANG\n → Python 清除 conversation_history
→ 重置 session_log → 回到環境音模式待機
```
> 作用：每位觀眾的對話記憶在物理動作（掛回）時清除，避免跨觀眾對話跑偏。每次對話都是全新開始。

### 各角色分工
| 角色 | 負責 |
|------|------|
| 微動開關 | 偵測蓮蓬頭是否被取下或掛回，觸發重置 |
| FSR 壓力感測器 | 偵測觀眾握住蓮蓬頭，切換對話模式 |
| Arduino Nano | 讀取微動開關 + FSR、驅動 OLED、傳訊號給 Python |
| 麥克風 | 收環境音及觀眾說話聲音 |
| Python（main.py） | 整個系統的大腦，串聯所有服務，管理對話記憶 |
| VAD（RMS 靜音偵測） | 對話模式中偵測句尾（靜音 > 800ms），切出音訊片段 |
| Gemini multimodal API | 直接分析音訊內容，產生蓮蓬頭個性回應（取代 librosa + Web Speech） |
| ElevenLabs | 文字轉語音 |
| Voicemeeter Banana | 所有播出聲音自動加悶聲混響 |
| OLED 螢幕 | 顯示文字，觀眾讀懂用 |
| USB 喇叭 | 播出處理後的聲音 |
| ~~librosa~~ | ~~分析環境音特徵~~ → 升級後由 Gemini multimodal 取代 |
| ~~Chrome Web Speech API~~ | ~~語音轉文字~~ → 升級後由 Gemini multimodal 取代 |

### Serial 通訊協定
- Arduino → Python：`HOLD\n` / `RELEASE\n` / `HANG\n` / `BMAP_OK\n` / `BMAP_TIMEOUT:{n}\n`
- Python → Arduino：`[0xFF 0xFE 0xFD]` + 1024 bytes 點陣圖（SH1106 U8g2 格式）

| 訊號 | 觸發條件 | Python 動作 |
|------|----------|-------------|
| `HOLD\n` | FSR 偵測到握力 | 進入對話模式，開始 VAD 錄音 |
| `RELEASE\n` | FSR 放開 | 離開對話模式，回到環境音模式 |
| `HANG\n` | 微動開關觸發（蓮蓬頭掛回） | 清除 conversation_history，重置 session |
| `BMAP_OK\n` | OLED 點陣圖接收完成 | 確認顯示成功 |
| `BMAP_TIMEOUT:{n}\n` | OLED 點陣圖接收逾時 | 重傳或略過 |

---

## 檔案結構
```
蓮蓬頭/
├── CLAUDE.md              ← 本文件
├── main.py                ← Python 主程式（系統大腦）
├── memory.py              ← 記憶系統（聲音庫 + 對話紀錄 + 唱歌比較）
├── memories.json          ← 21 筆聲音記憶庫
├── scan_sounds.py         ← 掃描音檔、互動式加入記憶庫
├── test_response.py       ← 8 情境自動化回應測試
├── test_voices.py         ← ElevenLabs 聲音試聽比較工具
├── requirements.txt       ← Python 套件清單
├── key.env                ← API 金鑰（不上傳 GitHub，等同 .env）
├── .env.example           ← 金鑰範本
├── .gitignore
├── README.md
├── arduino/
│   └── showerhead/
│       └── showerhead.ino ← Arduino Nano 程式
└── web/
    └── index.html         ← Chrome Web Speech API 介面
```

---

## API 金鑰狀態
| 服務 | 狀態 |
|------|------|
| Gemini API（Google AI Studio） | ✅ 已設定，使用 `gemini-2.5-flash`，SDK 已升級至 `google-genai` |
| ElevenLabs API key | ✅ 已設定於 key.env |
| ElevenLabs Voice ID | ✅ Bella（premade，免費可用 API，`EXAVITQu4vr4xnSDxMaL`） |

---

## 軟體安裝狀態
| 軟體 | 狀態 |
|------|------|
| Python 3.13.7 | ✅ 已安裝（已加入 PATH） |
| Python 套件（requirements.txt） | ✅ 全部安裝完成 |
| Arduino IDE 2.3.8（官網版） | ✅ 已安裝（注意：Windows Store 版無法存取 COM port，需用官網 .exe） |
| CH340 驅動（CH341SER.EXE） | ✅ 已安裝（Arduino Nano clone 用 CH340 晶片） |
| Voicemeeter Banana | ✅ 已安裝，EQ + A1 輸出設定完成（見下方音效設定章節） |
| VB-Cable | ✅ 已安裝（重新安裝 v2.1.5.8） |
| Chrome 瀏覽器 | ✅ |

---

## 硬體採購清單
| 元件 | 用途 | 狀態 |
|------|------|------|
| Arduino Nano | 讀取 FSR + 微動開關、驅動 OLED | ✅ 已有 |
| 1.3吋 OLED I2C 128×64（SH1106） | 顯示文字 | ✅ 已有 |
| FSR 壓力感測器 | 偵測握力，切換對話模式 | ✅ 已有 |
| 10kΩ 電阻 | FSR 分壓電路 | ✅ 已有 |
| **微動開關（Micro Switch）** | **偵測蓮蓬頭掛回，觸發對話記憶重置** | ❌ **待採購** |
| USB 麥克風 | 收音 | ⚠️ 3.5mm TRRS 麥克風無法正常收音，暫用筆電內建 Microphone Array |
| USB 有源喇叭 | 播出聲音 | ⚠️ 暫用電腦喇叭替代 |
| USB 集線器 | 同時接多個 USB | ✅ 已有 |
| 塑膠蓮蓬頭 | 主體外觀 | ✅ 已有 |
| PVC 水管 | 連接蓮蓬頭到箱體 | ✅ 已有 |
| 夾板或木心板 | 箱體與牆壁結構 | ✅ 已有 |
| 活動輪附煞車 | 箱體底部 | ✅ 已有 |
| 延長線 | 展場供電 | ✅ 已有 |

---

## Arduino 接線
```
FSR 分壓電路（不使用麵包板，直接焊接或絞接）：
  FSR 一端 → 3.3V
  FSR 另一端 → A0，同時接 10kΩ 電阻到 GND

OLED SH1106 I2C（4 腳位 IIC 版本）：
  OLED GND → GND
  OLED VCC → 3.3V
  OLED SCK → A5 (SCL)
  OLED SDA → A4 (SDA)

微動開關（重置機制，待實作）：
  微動開關 COM → GND
  微動開關 NO  → D2（數位腳位，使用 INPUT_PULLUP）
  說明：蓮蓬頭掛回時按下開關 → D2 讀到 LOW → Arduino 送 HANG\n 給 Python

Arduino Nano USB → 筆電（透過 USB 集線器）
```
Arduino IDE 需安裝 Library：**U8g2 by oliver**

### 微動開關邏輯說明
- 掛架設計：掛鉤位置裝一顆微動開關，蓮蓬頭掛上時物理壓下開關
- 狀態：蓮蓬頭在掛架上 → 開關被壓下（ON）→ D2 = LOW
- 狀態：蓮蓬頭被取下 → 開關彈起（OFF）→ D2 = HIGH
- 觸發時機：偵測到 OFF→ON 的下降沿（蓮蓬頭剛掛回）→ 送 `HANG\n`

---

## 蓮蓬頭 System Prompt（Gemini）

> ⚠️ System Prompt 已升級為完整 Skill 文件，請見 `skill.md`
> 舊版簡短 prompt 已廢棄，main.py 的 SYSTEM_PROMPT 變數需更新為 skill.md 全文

主要規則摘要（詳細內容見 skill.md）：
- 回應 3–16 字，句尾不加句號，僅保留 ？ / ！
- 水聲可作比較基準，禁止描述自身功能出水
- 不知道展覽、藝術、材質、天空、關係名稱等概念
- 個性如幼犬：天真、好奇、直接
- 找蓮蓬是它離開浴室的動機之一
- 對話記憶由微動開關觸發重置（HANG\n）

---

## 聲音設計
- ElevenLabs 選年輕女聲作為基底（Voice ID：Bella premade，`EXAVITQu4vr4xnSDxMaL`）
- Python 在播出前套用 **ring modulation**（60Hz 載波，depth=0.55）→ 機械質感
- Voicemeeter Banana 套用 EQ：壓低高頻、提升低頻 → 悶、金屬腔體感
- ElevenLabs VoiceSettings：`stability=0.25, similarity_boost=0.5, style=0.4`（活潑、不穩定感）
- 效果疊加：活潑原聲 → ring modulation 機械化 → Voicemeeter 壓悶 → 最終輸出
- **文字（OLED）是給觀眾讀懂的版本，聲音才是它真實的樣子**

### 已測試可用的免費 premade 聲音（2026-05-18）
| 聲音名稱 | Voice ID | 特性 |
|----------|----------|------|
| **Bella**（選用） | `EXAVITQu4vr4xnSDxMaL` | 女聲，年輕感，活潑 |
| Adam | `pNInz6obpgDQGcFmaJgB` | 男聲，沉穩 |
| Rachel | `21m00Tcm4TlvDq8ikWAM` | 女聲，清晰溫和 |
| Antoni | `ErXwobaYiN019PkySvjV` | 男聲，自然流暢 |
| Arnold | `VR6AewLTigWG4xSOukaG` | 男聲，低沉粗獷 |

---

## Voicemeeter Banana 音效設定

### 音訊路由
- ElevenLabs 播放裝置 → **Voicemeeter Input（VAIO）**
- Voicemeeter A1 輸出 → **Speakers (Realtek® Audio)**（目前暫用電腦喇叭）

### VAIO 輸入條 EQ（簡易 2 段）
| 旋鈕 | 設定值 |
|------|--------|
| Treble | −5.0 |
| Bass | +2.3 |

### Bus A1 EQPro-G6（6 段參數 EQ）
| 頻段 | Hz | dB |
|------|----|----|
| Band 1 | 100 | −3.2 |
| Band 2 | 400 | +4.6 |
| Band 3 | 1510 | −2.0 |
| Band 4 | 4000 | −6.8 |
| Band 5 | 8000 | −10.3 |
| Band 6 | 12000（High Shelf） | −8.9 |

> Band 6 使用 High Shelf 濾波器，確保 12kHz 以上繼續往下壓，不反彈。
> 設定已儲存為 `voicemeeter_showerhead.xml`。

---

## 麥克風設定

### 目前狀態
- **使用裝置**：筆電內建 Microphone Array (Realtek)
- **原因**：3.5mm TRRS 外接麥克風（JGL-119H）無法正常收音，硬體不相容
- **展覽建議**：改用 USB 麥克風，避免接孔相容問題

### 麥克風校準數值（2026-05-18 測定）
| 情況 | rms |
|------|-----|
| 安靜（背景噪音） | 0.015 |
| 說話 | 0.029 |
| 唱歌 | 0.063 |

### 靜音門檻設定
- `main.py` 靜音門檻：`rms < 0.015`
- 低於此值視為安靜，不觸發 Gemini 回應
- melody 偵測條件：`(harmonic_ratio > 0.92 and zcr < 0.04) or (harmonic_ratio > 0.88 and zcr < 0.03 and rms > 0.025)`
- 說話的 hr 約 0.857–0.882，需 hr > 0.92 才算唱歌，避免誤判

---

## 時間規劃
| 時間 | 任務 |
|------|------|
| 提案後第 1–3 天 | 完成實體裝置：箱體、牆壁、蓮蓬頭固定 |
| 提案後第 4–5 天 | ElevenLabs 聲音選定、全 API 測試 |
| 提案後第 6–8 天 | Python 腳本整合、個性設定反覆測試 |
| 提案後第 9–10 天 | Voicemeeter 音效調整、全系統整合測試 |
| 提案後第 11–12 天 | 調整、備案準備 |
| 展覽日 | 展出 |

---

## 待辦事項
- [x] ElevenLabs：取得 API key + 選定 Voice ID 並填入 key.env
- [x] Python 套件確認全部安裝完成
- [x] VB-Cable 安裝（以系統管理員身份執行）
- [x] Gemini → ElevenLabs → pygame 串聯測試通過
- [x] 調整蓮蓬頭 SYSTEM_PROMPT 個性設定（移除水相關詞彙，純聽覺視角）
- [x] 記憶系統建立（memory.py + memories.json，保留全部、帶入最近 5 筆）
- [x] 全部音訊檔分析完成（21 筆，含 M4A 支援，使用 ffmpeg 轉檔）
- [x] 唱歌品質比較系統（harmonic ratio 評分，前後場次比較，差距 > 0.08 才觸發）
- [x] scan_sounds.py：自動掃描新音檔，互動式加入 memories.json
- [x] memories.json 完整建立（21 筆聲音記憶，每筆含 sample_responses 6–11 句）
- [x] test_response.py：自動化場景測試（8 情境，不需互動，使用真實音頻參數）
- [x] 回應調校：雨聲、狗叫聲、「你是誰」對話引導語更新
- [x] Voicemeeter 音效參數設定（EQ 完成，設定已儲存）
- [x] 麥克風校準（靜音門檻調整為 0.015，melody 偵測條件調校）
- [x] 環境音模式完整測試通過（唱歌、說話、環境音皆可正確匹配）
- [x] 聲音效果疊加完成（ring modulation + Voicemeeter EQ + VoiceSettings 活潑參數）
- [x] ElevenLabs 聲音確定（Bella premade，已批次測試所有免費可用聲音）
- [x] test_voices.py：多聲音試聽比較工具（含 ring modulation 效果）
- [x] Arduino IDE 安裝 + U8g2 library（官網版 2.3.8，CH340 驅動 CH341SER.EXE）
- [x] 硬體備齊（USB 喇叭暫以電腦替代，其餘全部到位）
- [x] 燒錄 Arduino、測試 OLED 顯示 + FSR 壓力感測（2026-05-19 完成）
- [ ] **採購微動開關（Micro Switch）** — 掛架重置機制用
- [ ] **Arduino 新增微動開關接線 + 燒錄 HANG\n 訊號邏輯**
- [ ] **蓮蓬頭 Skill 文件撰寫（9 個章節，逐步填寫中）**
- [ ] **升級 Gemini 為 multimodal 音訊輸入（取代 librosa + Web Speech API）**
- [ ] **Python VAD 靜音切段邏輯實作（靜音 > 800ms 觸發斷句）**
- [ ] **Python 加入每次對話的 instruction anchoring（每次 prompt 前附提醒句）**
- [ ] **Python 加入對話記憶（conversation_history）+ 收到 HANG\n 時清除**
- [ ] 展覽用 USB 麥克風（3.5mm TRRS 不相容，需更換）
- [ ] 全系統整合測試（含 Arduino 微動開關 + Gemini multimodal）
- [ ] ~~瀏覽器 Web Speech API 介面設定與測試~~ → 由 Gemini multimodal 取代，暫不實作

## 技術備註
- Gemini SDK 已從 `google-generativeai`（已停止維護）升級至 `google-genai`
- 使用模型：`gemini-2.5-flash`，fallback：`gemini-2.5-flash-lite-preview-06-17`（gemini-2.0/1.5 已 404）
- ElevenLabs 免費方案只能使用 `premade` 聲音（不能用聲音庫社群聲音）
- API 金鑰存於 `key.env`（等同 .env），main.py 以 `load_dotenv("key.env", override=True)` 載入
- pygame 播放完畢後需呼叫 `pygame.mixer.music.unload()` 再刪除暫存檔，避免 Windows 檔案鎖定
- M4A 等非標準格式透過 ffmpeg 轉成臨時 WAV 再用 librosa 分析，FFMPEG_DIR 設定於 key.env
- memories.json v1.2：21 筆聲音記憶，含公園、捷運、雨聲、唱歌（中/英文）等
- 唱歌品質分數：hr×0.6 + zcr_stability×0.3 + rms×0.1，比較差距 > 0.08 才輸出比較語
- melody 偵測條件：`(hr > 0.92 and zcr < 0.04) or (hr > 0.88 and zcr < 0.03 and rms > 0.025)`（說話 hr 約 0.86–0.88，不觸發）
- 唱歌記憶匹配優先：has_melody=True 時給唱歌記憶 −0.4 bonus，非人聲樂器 +0.3 懲罰
- 靜音門檻：`rms < 0.015`（說話 rms ≈ 0.029，安靜背景 ≈ 0.015）
- 3.5mm TRRS 麥克風（JGL-119H）與筆電不相容，暫用內建 Microphone Array
- `session_log.json` 中 `matched_memory_id` 可能為 None，memory.py 已加入 `or ""` 防護
- **Ring modulation**：`_apply_robot_effect()` 在 main.py speak() 內執行，60Hz 載波、depth=0.55，pydub + numpy 實作
- ElevenLabs VoiceSettings：`stability=0.25, similarity_boost=0.5, style=0.4, use_speaker_boost=False`
- Arduino loop() 不使用 `delay()`，改用 `millis()` 計時 FSR（delay 會造成 64 byte serial buffer overflow）
- Arduino serial buffer 64 bytes，Python 一次送 1027 bytes，必須零 delay 才能即時消化
- Windows Store 版 Arduino IDE 無法存取 COM port（沙盒限制），需用官網 .exe 安裝版
- Arduino Nano clone 使用 CH340 晶片，需安裝 CH341SER.EXE 驅動；燒錄選 ATmega328P (Old Bootloader)

### 新架構決策（2026-05-21）
- **Gemini multimodal 音訊輸入**：音訊片段直接傳給 Gemini，不再先用 librosa 提取數值特徵再轉文字描述。Gemini 可直接辨識語音內容、歌聲、咳嗽、環境音等，理解品質大幅提升。
- **VAD 靜音切段**：對話模式改用 Python RMS 靜音偵測（持續靜音 > 800ms）作為句尾判斷，取代 Chrome Web Speech API。靜音門檻沿用已校準值 `rms < 0.015`。
- **微動開關重置機制**：蓮蓬頭掛回時觸發 Arduino D2，送 `HANG\n` 給 Python，清除 `conversation_history`。每位觀眾對話記憶在物理動作（掛回）時清除，記憶邊界由裝置實際使用狀態決定，不靠計時。
- **Instruction anchoring**：每次呼叫 Gemini 前，在 user message 前自動附加原則提醒句，避免長對話後 Gemini 偏離個性設定。
- **Skill 文件**（system prompt 重構）：現有簡短 SYSTEM_PROMPT 將擴充為 9 章節完整 skill 文件，包含身份核心、禁止項目、說話規則、情境分支、記憶規則、多樣化規則、語氣示範庫、特殊狀況、重置機制。逐步與作者共同填寫。
- **Gem（Gemini 介面上的自訂 AI）無法透過 API 呼叫**，所有個性設定仍透過 system prompt 在 API 端實作，效果與 Gem 相同。

*最後更新：2026-05-21（新增微動開關重置機制、Gemini multimodal 升級計畫、VAD 切段、Skill 文件架構）*
