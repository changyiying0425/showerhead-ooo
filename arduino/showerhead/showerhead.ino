// 蓮蓬頭 - Arduino Nano 程式
// 負責：FSR 壓力感測 + SH1106 OLED 顯示 + Serial 通訊
//
// 接線：
//   FSR  → A0（另一端接 3.3V，A0 與 GND 之間接 10kΩ）
//   OLED GND → GND
//   OLED VCC → 3.3V
//   OLED SCK → A5 (SCL)
//   OLED SDA → A4 (SDA)
//
// 需要安裝的 Library（Arduino IDE → Library Manager）：
//   - U8g2 by oliver
//
// 注意：loop() 絕對不能有 delay()，否則 64-byte serial buffer 會溢位
// Python 一次送 1027 bytes（header 3 + bitmap 1024），需即時消化

#include <Arduino.h>
#include <Wire.h>
#include <U8g2lib.h>

// SH1106 128x64 I2C（1.3吋 OLED，4 腳位 IIC 版本）
U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);

const int FSR_PIN       = A0;
const int FSR_THRESHOLD = 200;
const int BITMAP_SIZE   = 1024;

bool prevHolding = false;
unsigned long lastFsrMs = 0;

void setup() {
  Serial.begin(115200);
  u8g2.begin();

  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_unifont_tf);
  u8g2.drawStr(50, 36, "...");
  u8g2.sendBuffer();
}

void loop() {
  // ── FSR 壓力偵測（每 50ms 取樣一次，不用 delay）────────
  if (millis() - lastFsrMs >= 50) {
    lastFsrMs = millis();
    int fsrValue = analogRead(FSR_PIN);
    bool holding = (fsrValue > FSR_THRESHOLD);
    if (holding != prevHolding) {
      prevHolding = holding;
      Serial.println(holding ? "HOLD" : "RELEASE");
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
