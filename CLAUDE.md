# 蓮蓬頭專題 — CLAUDE.md

## 專題概述
- **主題**：客體導向本體論（Object-Oriented Ontology，OOO）
- **物件**：蓮蓬頭
- **形式**：互動裝置，展覽展出
- **GitHub**：https://github.com/changyiying0425/showerhead-ooo
- **專案路徑**：`C:\Users\咦\Downloads\蓮蓬頭\`

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

### 互動模式

**模式一：環境音模式（預設）**
```
麥克風 → librosa 分析聲音特徵（音量、頻率）
→ 每10秒分析一次，有明顯變化才觸發
→ Gemini API（蓮蓬頭個性回應）
→ OLED 顯示文字 + ElevenLabs TTS → Voicemeeter → 喇叭
超過30秒安靜 → 自動自言自語
```

**模式二：對話模式（觀眾握住時）**
```
觀眾握住蓮蓬頭握把
→ FSR 壓力感測器 → Arduino Nano → Python
→ Chrome Web Speech API 收音
→ 語音轉文字 → Gemini API
→ OLED 顯示文字 + ElevenLabs TTS → Voicemeeter → 喇叭
→ 觀眾放開 → 回到環境音模式
```

### 各角色分工
| 角色 | 負責 |
|------|------|
| FSR 壓力感測器 | 偵測觀眾握住蓮蓬頭 |
| Arduino Nano | 讀取 FSR、驅動 OLED、傳訊號給 Python |
| 麥克風 | 收環境音及觀眾說話 |
| Chrome 網頁 | Web Speech API 語音轉文字 |
| Python（main.py） | 整個系統的大腦，串聯所有服務 |
| librosa | 分析環境音特徵 |
| Gemini API | 用蓮蓬頭個性思考、產生回應 |
| ElevenLabs | 文字轉語音 |
| Voicemeeter Banana | 所有播出聲音自動加悶聲混響 |
| OLED 螢幕 | 顯示文字，觀眾讀懂用 |
| USB 喇叭 | 播出處理後的聲音 |

### Serial 通訊協定
- Arduino → Python：`HOLD\n` / `RELEASE\n`
- Python → Arduino：`[0xFF 0xFE 0xFD]` + 1024 bytes 點陣圖（SH1106 U8g2 格式）

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
| Arduino IDE | ❌ 待安裝 |
| Voicemeeter Banana | ✅ 已安裝，EQ + A1 輸出設定完成（見下方音效設定章節） |
| VB-Cable | ✅ 已安裝（重新安裝 v2.1.5.8） |
| Chrome 瀏覽器 | ✅ |

---

## 硬體採購清單
| 元件 | 用途 | 狀態 |
|------|------|------|
| Arduino Nano | 讀取 FSR、驅動 OLED | ✅ 已有 |
| 1.3吋 OLED SPI 128×64（SH1106） | 顯示文字 | ✅ 已有 |
| FSR 壓力感測器 | 偵測握力 | ✅ 已有 |
| 10kΩ 電阻 | FSR 分壓電路 | ✅ 已有 |
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

OLED SH1106 SPI：
  OLED SCK  → D13
  OLED MOSI → D11
  OLED CS   → D10
  OLED DC   → D9
  OLED RST  → D8
  OLED VCC  → 3.3V
  OLED GND  → GND

Arduino Nano USB → 筆電（透過 USB 集線器）
```
Arduino IDE 需安裝 Library：**U8g2 by oliver**

---

## 蓮蓬頭 System Prompt（Gemini）
```
你是一個蓮蓬頭。

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
```

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
- `main.py` 靜音門檻：`rms < 0.022`
- 低於此值視為安靜，不觸發 Gemini 回應
- melody 偵測條件：`harmonic_ratio > 0.65 and zcr < 0.07`

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
- [x] 麥克風校準（靜音門檻 0.022，melody 偵測條件調校）
- [x] 環境音模式完整測試通過（唱歌、說話、環境音皆可正確匹配）
- [x] 聲音效果疊加完成（ring modulation + Voicemeeter EQ + VoiceSettings 活潑參數）
- [x] ElevenLabs 聲音確定（Bella premade，已批次測試所有免費可用聲音）
- [x] test_voices.py：多聲音試聽比較工具（含 ring modulation 效果）
- [ ] 瀏覽器 Web Speech API 介面設定與測試
- [ ] Arduino IDE 安裝 + U8g2 library
- [x] 硬體備齊（USB 喇叭暫以電腦替代，其餘全部到位）
- [ ] 燒錄 Arduino、測試 OLED 顯示 + FSR 壓力感測
- [ ] 展覽用 USB 麥克風（3.5mm TRRS 不相容，需更換）
- [ ] 全系統整合測試（含 Arduino）

## 技術備註
- Gemini SDK 已從 `google-generativeai`（已停止維護）升級至 `google-genai`
- 使用模型：`gemini-2.5-flash`
- ElevenLabs 免費方案只能使用 `premade` 聲音（不能用聲音庫社群聲音）
- API 金鑰存於 `key.env`（等同 .env），main.py 以 `load_dotenv("key.env", override=True)` 載入
- pygame 播放完畢後需呼叫 `pygame.mixer.music.unload()` 再刪除暫存檔，避免 Windows 檔案鎖定
- M4A 等非標準格式透過 ffmpeg 轉成臨時 WAV 再用 librosa 分析，FFMPEG_DIR 設定於 key.env
- memories.json v1.2：21 筆聲音記憶，含公園、捷運、雨聲、唱歌（中/英文）等
- 唱歌品質分數：hr×0.6 + zcr_stability×0.3 + rms×0.1，比較差距 > 0.08 才輸出比較語
- melody 偵測條件：`harmonic_ratio > 0.65 and zcr < 0.07`（說話不觸發，需真正唱歌）
- 唱歌記憶匹配優先：has_melody=True 時給唱歌記憶 −0.4 bonus，非人聲樂器 +0.3 懲罰
- 靜音門檻：`rms < 0.022`（依 2026-05-18 麥克風校準結果設定）
- 3.5mm TRRS 麥克風（JGL-119H）與筆電不相容，暫用內建 Microphone Array
- `session_log.json` 中 `matched_memory_id` 可能為 None，memory.py 已加入 `or ""` 防護
- **Ring modulation**：`_apply_robot_effect()` 在 main.py speak() 內執行，60Hz 載波、depth=0.55，pydub + numpy 實作
- ElevenLabs VoiceSettings：`stability=0.25, similarity_boost=0.5, style=0.4, use_speaker_boost=False`

*最後更新：2026-05-18（聲音效果完成：ring modulation + Voicemeeter EQ + Bella 聲音）*
