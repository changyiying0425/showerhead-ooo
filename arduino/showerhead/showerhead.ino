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

#include <Arduino.h>
#include <Wire.h>
#include <U8g2lib.h>

// SH1106 128x64 I2C（1.3吋 OLED，4 腳位 IIC 版本）
U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);

const int FSR_PIN       = A0;
const int FSR_THRESHOLD = 200;   // 0~1023，調大 = 需要更大力才觸發
const int BITMAP_SIZE   = 1024;  // 128×64÷8 bytes

bool prevHolding = false;

void setup() {
  Serial.begin(115200);
  u8g2.begin();

  // 顯示啟動符號
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_unifont_tf);
  u8g2.drawStr(50, 36, "...");
  u8g2.sendBuffer();
}

void loop() {
  // ── FSR 壓力偵測 ──────────────────────────────
  int fsrValue = analogRead(FSR_PIN);
  bool holding = (fsrValue > FSR_THRESHOLD);

  if (holding != prevHolding) {
    prevHolding = holding;
    Serial.println(holding ? "HOLD" : "RELEASE");
  }

  // ── 接收 Python 傳來的點陣圖 ──────────────────
  // 協定：3 個魔術 byte [0xFF 0xFE 0xFD] + 1024 bytes 點陣圖資料
  if (Serial.available() >= 3) {
    byte b0 = Serial.read();
    if (b0 == 0xFF) {
      byte b1 = Serial.read();
      byte b2 = Serial.read();
      if (b1 == 0xFE && b2 == 0xFD) {
        // 讀取點陣圖，直接寫入 u8g2 全框緩衝區
        uint8_t* buf     = u8g2.getBufferPtr();
        int      received = 0;
        unsigned long t0  = millis();

        while (received < BITMAP_SIZE) {
          if (Serial.available()) {
            buf[received++] = Serial.read();
          }
          if (millis() - t0 > 600) break;  // 逾時保護
        }

        if (received == BITMAP_SIZE) {
          u8g2.sendBuffer();
        }
      }
    }
  }

  delay(50);
}
