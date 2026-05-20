// 蓮蓬頭 - Arduino Nano 程式
// 負責：FSR 壓力感測 + 微動開關重置 + SH1106 OLED 顯示 + Serial 通訊
//
// 接線：
//   FSR  → A0（另一端接 3.3V，A0 與 GND 之間接 10kΩ）
//   OLED GND → GND
//   OLED VCC → 3.3V
//   OLED SCK → A5 (SCL)
//   OLED SDA → A4 (SDA)
//   微動開關 COM → GND
//   微動開關 NO  → D2（INPUT_PULLUP，不需外接電阻）
//
// 需要安裝的 Library（Arduino IDE → Library Manager）：
//   - U8g2 by oliver
//
// 注意：loop() 絕對不能有 delay()，否則 64-byte serial buffer 會溢位

#include <Arduino.h>
#include <Wire.h>
#include <U8g2lib.h>

// SH1106 128x64 I2C（1.3吋 OLED，4 腳位 IIC 版本）
U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);

const int FSR_PIN        = A0;
const int SWITCH_PIN     = 2;    // 微動開關，D2，INPUT_PULLUP
const int FSR_THRESHOLD  = 200;
const int BITMAP_SIZE    = 1024;
const unsigned long DEBOUNCE_MS = 80;  // 微動開關去彈跳時間（ms）

bool prevHolding     = false;
unsigned long lastFsrMs = 0;

// 微動開關去彈跳狀態
bool prevSwitch      = HIGH;    // HIGH = 蓮蓬頭不在掛架上
bool switchPending   = false;
bool switchPendingVal = HIGH;
unsigned long switchDebounceMs = 0;

void setup() {
  Serial.begin(115200);

  pinMode(SWITCH_PIN, INPUT_PULLUP);

  u8g2.begin();
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_unifont_tf);
  u8g2.drawStr(50, 36, "...");
  u8g2.sendBuffer();
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
    // 狀態變化，重設去彈跳計時
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
          uint8_t* buf = u8g2.getBufferPtr();
          int received = 0;
          unsigned long t0 = millis();

          while (received < BITMAP_SIZE && millis() - t0 < 2000) {
            if (Serial.available()) {
              buf[received++] = Serial.read();
            }
          }

          if (received == BITMAP_SIZE) {
            u8g2.sendBuffer();
            Serial.println("BMAP_OK");
          } else {
            Serial.print("BMAP_TIMEOUT:");
            Serial.println(received);
          }
        }
      }
    } else {
      Serial.read();  // 丟掉雜訊
    }
  }

  // 不加 delay()
}
