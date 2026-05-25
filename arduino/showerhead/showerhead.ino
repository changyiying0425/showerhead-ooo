// 蓮蓬頭 - Arduino Nano 程式
// 負責：FSR 壓力感測 + 微動開關重置 + SH1106 OLED 顯示 × 2 + Serial 通訊
//
// 接線：
//   FSR  → A0（另一端接 3.3V，A0 與 GND 之間接 10kΩ）
//   微動開關 COM → GND
//   微動開關 NO  → D2（INPUT_PULLUP，不需外接電阻）
//
//   OLED 1（文字顯示）— 硬體 I2C，地址 0x3C
//     GND → GND
//     VCC → 3.3V
//     SCK → A5 (SCL)
//     SDA → A4 (SDA)
//
//   OLED 2（波形顯示）— 軟體 I2C，地址 0x3C（與 OLED 1 相同但不衝突）
//     GND → GND
//     VCC → 3.3V
//     SCK → D6
//     SDA → D7
//
// 需要安裝的 Library（Arduino IDE → Library Manager）：
//   - U8g2 by oliver
//
// 注意：loop() 絕對不能有 delay()，否則 64-byte serial buffer 會溢位

#include <Arduino.h>
#include <Wire.h>
#include <U8g2lib.h>

// OLED 1：硬體 I2C（A4=SDA, A5=SCL），4 腳位 SH1106，地址 0x3C
U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);

// OLED 2：軟體 I2C（D6=SCK, D7=SDA），地址同為 0x3C 但不衝突
U8G2_SH1106_128X64_NONAME_F_SW_I2C u8g2_2(U8G2_R0, /*SCL=*/6, /*SDA=*/7, U8X8_PIN_NONE);

const int FSR_PIN        = A0;
const int SWITCH_PIN     = 2;    // 微動開關，D2，INPUT_PULLUP
const int FSR_THRESHOLD  = 200;
const int BITMAP_SIZE    = 1024;
const unsigned long DEBOUNCE_MS = 80;  // 微動開關去彈跳時間（ms）

bool prevHolding        = false;
unsigned long lastFsrMs = 0;

// 微動開關去彈跳狀態
bool prevSwitch         = HIGH;   // HIGH = 蓮蓬頭不在掛架上
bool switchPending      = false;
bool switchPendingVal   = HIGH;
unsigned long switchDebounceMs = 0;

// ── 共用：接收點陣圖並顯示到指定 OLED ──────────────────────
void receiveBitmapToOled(U8G2 &oled) {
  uint8_t* buf = oled.getBufferPtr();
  int received = 0;
  unsigned long t0 = millis();

  while (received < BITMAP_SIZE && millis() - t0 < 2000) {
    if (Serial.available()) {
      buf[received++] = Serial.read();
    }
  }

  if (received == BITMAP_SIZE) {
    oled.sendBuffer();
    Serial.println("BMAP_OK");
  } else {
    Serial.print("BMAP_TIMEOUT:");
    Serial.println(received);
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(SWITCH_PIN, INPUT_PULLUP);

  // 初始化 OLED 1
  u8g2.begin();
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_unifont_tf);
  u8g2.drawStr(50, 36, "...");
  u8g2.sendBuffer();

  // 初始化 OLED 2（波形，待 Python 送資料）
  u8g2_2.begin();
  u8g2_2.clearBuffer();
  u8g2_2.sendBuffer();
}

void loop() {
  // ── FSR 壓力偵測（每 50ms 取樣一次）────────────────────
  if (millis() - lastFsrMs >= 50) {
    lastFsrMs = millis();
    int fsrValue = analogRead(FSR_PIN);
    bool holding = (fsrValue > FSR_THRESHOLD);
    if (holding != prevHolding) {
      prevHolding = holding;
      Serial.println(holding ? "HOLD" : "RELEASE");
    }
  }

  // ── 微動開關偵測（去彈跳，偵測下降沿 = 掛回）───────────
  bool curSwitch = digitalRead(SWITCH_PIN);
  if (curSwitch != switchPendingVal) {
    switchPendingVal = curSwitch;
    switchDebounceMs = millis();
    switchPending = true;
  }
  if (switchPending && millis() - switchDebounceMs >= DEBOUNCE_MS) {
    switchPending = false;
    if (switchPendingVal != prevSwitch) {
      prevSwitch = switchPendingVal;
      if (switchPendingVal == LOW) {
        // 下降沿：HIGH → LOW = 蓮蓬頭剛掛回
        Serial.println("HANG");
      }
      // 上升沿（LOW → HIGH）= 蓮蓬頭被取下，目前不送訊號
    }
  }

  // ── 接收 Python 傳來的點陣圖 ──────────────────────────
  // Header：0xFF 0xFE 0xFD → OLED 1（文字）
  //         0xFF 0xFE 0xFC → OLED 2（波形）
  if (Serial.available() > 0) {
    byte b0 = Serial.peek();
    if (b0 == 0xFF) {
      Serial.read();  // 消化 0xFF

      // 等待後續 2 個 header bytes
      unsigned long tw = millis();
      while (Serial.available() < 2 && millis() - tw < 50);

      if (Serial.available() >= 2) {
        byte b1 = Serial.read();
        byte b2 = Serial.read();
        if (b1 == 0xFE && b2 == 0xFD) {
          receiveBitmapToOled(u8g2);    // → OLED 1
        } else if (b1 == 0xFE && b2 == 0xFC) {
          receiveBitmapToOled(u8g2_2);  // → OLED 2
        }
      }
    } else {
      Serial.read();  // 丟掉雜訊
    }
  }

  // 不加 delay()
}
