// 蓮蓬頭 - Arduino Nano 程式
// 負責：FSR 壓力感測 + 微動開關 + SH1106 OLED ×2 顯示 + Serial 通訊
//
// 接線：
//   FSR  → A0（另一端接 3.3V，A0 與 GND 之間接 10kΩ）
//   OLED 1（文字）GND/VCC/SCK/SDA → GND/3.3V/A5/A4，I2C 位址 0x3C（SA0 接 GND）
//   OLED 2（波形）GND/VCC/SCK/SDA → GND/3.3V/A5/A4，I2C 位址 0x3D（SA0 接 VCC）
//   微動開關 COM → GND，NO → D2（INPUT_PULLUP）
//
// 需要安裝的 Library（Arduino IDE → Library Manager）：
//   - U8g2 by oliver
//
// 注意：loop() 絕對不能有 delay()，否則 64-byte serial buffer 會溢位
// Python 一次送 1027 bytes（header 3 + bitmap 1024），需即時消化

#include <Arduino.h>
#include <Wire.h>
#include <U8g2lib.h>

// OLED 1（文字回應）：I2C 預設位址 0x3C
U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);

// OLED 2（音訊波形）：0.96吋 SSD1306，I2C 位址 0x3D（背面焊橋切換）
U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2b(U8G2_R0, U8X8_PIN_NONE);

const int FSR_PIN       = A0;
const int FSR_THRESHOLD = 200;
const int SWITCH_PIN    = 2;     // 微動開關（INPUT_PULLUP）
const int BITMAP_SIZE   = 1024;

bool prevHolding     = false;
unsigned long lastFsrMs = 0;

// 微動開關去彈跳
bool prevSwitchState     = HIGH;
unsigned long lastSwitchMs = 0;
const unsigned long DEBOUNCE_MS = 80;

// ── 接收 bitmap 並顯示到指定 OLED ──────────────────────────
void receiveBitmapToOled(U8G2_SH1106_128X64_NONAME_F_HW_I2C& oled) {
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

  // OLED 1（0x3C，預設位址）
  u8g2.begin();
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_unifont_tf);
  u8g2.drawStr(50, 36, "...");
  u8g2.sendBuffer();

  // OLED 2（0x3D，SA0 接 VCC → setI2CAddress 0x3D<<1 = 0x7A）
  u8g2b.setI2CAddress(0x7A);
  u8g2b.begin();
  u8g2b.clearBuffer();
  u8g2b.sendBuffer();  // 初始全黑，等 Python 送波形

  // 微動開關
  pinMode(SWITCH_PIN, INPUT_PULLUP);
  prevSwitchState = digitalRead(SWITCH_PIN);
}

void loop() {
  // ── FSR 壓力偵測（每 50ms）────────────────────────────────
  if (millis() - lastFsrMs >= 50) {
    lastFsrMs = millis();
    int fsrValue = analogRead(FSR_PIN);
    bool holding = (fsrValue > FSR_THRESHOLD);
    if (holding != prevHolding) {
      prevHolding = holding;
      Serial.println(holding ? "HOLD" : "RELEASE");
    }
  }

  // ── 微動開關（去彈跳，偵測下降沿 → HANG）────────────────
  bool swState = digitalRead(SWITCH_PIN);
  if (swState != prevSwitchState && millis() - lastSwitchMs > DEBOUNCE_MS) {
    lastSwitchMs    = millis();
    prevSwitchState = swState;
    if (swState == LOW) {     // 蓮蓬頭剛掛回，開關被壓下
      Serial.println("HANG");
    }
  }

  // ── 接收 Python 傳來的點陣圖 ──────────────────────────────
  // Header:  [0xFF][0xFE][0xFD] → OLED 1（文字）
  //          [0xFF][0xFE][0xFC] → OLED 2（波形）
  if (Serial.available() > 0) {
    byte b0 = Serial.peek();
    if (b0 == 0xFF) {
      Serial.read();  // 消化 0xFF

      unsigned long tw = millis();
      while (Serial.available() < 2 && millis() - tw < 50);

      if (Serial.available() >= 2) {
        byte b1 = Serial.read();
        byte b2 = Serial.read();
        if (b1 == 0xFE) {
          if (b2 == 0xFD) {
            receiveBitmapToOled(u8g2);   // → OLED 1
          } else if (b2 == 0xFC) {
            receiveBitmapToOled(u8g2b);  // → OLED 2
          }
        }
      }
    } else {
      Serial.read();  // 丟掉雜訊
    }
  }

  // 不加 delay()
}
