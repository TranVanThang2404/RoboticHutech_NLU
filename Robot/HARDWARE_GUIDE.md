# 🔌 HƯỚNG DẪN KẾT NỐI PHẦN CỨNG CHI TIẾT

## 📋 DANH SÁCH LINH KIỆN

### Bắt Buộc
- Raspberry Pi 4 Model B (4GB RAM)
- USB Camera hoặc Webcam USB
- Motor Driver (L298N hoặc tương tự) × 2
- DC Motor 12V × 3 (hoặc 2 motor + 1 bánh quay)
- Ultrasonic Sensor HC-SR04 × 3
- Pin Lithium 24V 20Ah
- Buck Converter 24V → 5V 5A
- Dây cáp, điện trở, tụ điện

### Tùy Chọn
- Màn hình LCD 3.5" TFT SPI
- Đèn LED
- Buzzer

---

## ⚡ SƠĐỒ KẾT NỐI TỪA NGUỒN

```
[24V Li-ion Battery]
        ↓
    [Fuse 25A]
        ├─→ [Motor Driver 1 VCC] → Motors (3-4 amps)
        ├─→ [Motor Driver 2 VCC] → Motors (3-4 amps)
        ├─→ [Buck Converter] → 5V 5A
                                ↓
                        [Raspberry Pi 5V + GND]
                        [Ultrasonic sensors (5V)]
                        [USB Camera (5V via USB)]
                        
[All GNDs Connected Together - STAR Configuration]
```

---

## 🎮 RASPBERRY PI GPIO PIN MAPPING

### GPIO Header Pinout (BCM Numbering)

```
Pi Pin  BCM#   Function        Connected To
─────────────────────────────────────────
 3      GPIO2  SDA             (I2C - Optional)
 5      GPIO3  SCL             (I2C - Optional)
 7      GPIO4  (Available)
 8      GPIO14 UART TX         (Debug)
10      GPIO15 UART RX         (Debug)
11      GPIO17 DO/ECHO3/IN2    Motor Right INput
12      GPIO18 PWM0            (CS LCD)
13      GPIO27 Motor Right IN1
15      GPIO22 (Available)
16      GPIO23 Motor Left IN1
18      GPIO24 Motor Left IN2
19      GPIO10 SPI MOSI        (LCD Data)
21      GPIO9  SPI MISO        (LCD Data)
23      GPIO11 SPI CLOCK       (LCD Clock)
24      GPIO8  SPI CE0         (LCD)
29      GPIO5  GPIO5           (Available)
31      GPIO6  GPIO6           (Available)
32      GPIO12 MPO0            Motor Left PWM
33      GPIO13 PWM1            Motor Right PWM
35      GPIO19 TRIG2/ECHO2     Ultrasonic Center
37      GPIO26 ECHO2           Ultrasonic Center
38      GPIO20 TRIG3           Ultrasonic Right
40      GPIO21 ECHO3           Ultrasonic Right
```

### Ultrasonic Sensor Connection

```
HC-SR04 Pin    Raspberry Pi
─────────────────────────────
VCC            5V (from buck converter)
GND            GND
TRIG           GPIO (see config)
ECHO           GPIO (see config through voltage divider)
```

#### ⚠️ IMPORTANT: ECHO Pin Voltage Divider
HC-SR04 ECHO outputs 5V, but Raspberry Pi GPIO accepts only 3.3V!

```
                    Raspberry Pi
                    (3.3V Input)
                         ↑
                         │
HC-SR04 ECHO ────┬────[1kΩ]────┤ GPIO
    (5V)         │
                [2.2kΩ]
                 │
                GND
```

---

## 🚗 MOTOR CONTROL WIRING

### Motor Driver L298N Connection

```
┌─────────────────────┐
│   L298N Module      │
├─────────────────────┤
│ IN1 ─→ GPIO23       │ Left Motor
│ IN2 ─→ GPIO24       │
│ PWM ─→ GPIO12 (PWM) │
│ OUT1,2 ─→ Motor L   │
├─────────────────────┤
│ IN1 ─→ GPIO27       │ Right Motor
│ IN2 ─→ GPIO17       │
│ PWM ─→ GPIO13 (PWM) │
│ OUT3,4 ─→ Motor R   │
├─────────────────────┤
│ +12V ← 24V Battery  │
│ GND ─ GND (Star)    │
└─────────────────────┘
```

---

## 📸 USB CAMERA CONNECTION

```
USB Port 2 or 3/4
    ↓
[USB Camera]
```

Check which USB port:
```bash
lsusb
ls /dev/video*
```

---

## 🖥️ OPTIONAL: LCD 3.5" SPI CONNECTION

```
LCD Pin     Raspberry Pi
───────────────────────
VCC (5V)    5V
GND         GND
DIN         GPIO10 (SPI MOSI)
CLK         GPIO11 (SPI CLK)
CS          GPIO8 (SPI CE0)
RST         GPIO25 (or connect to Pi 3.3V)
```

---

## 🔧 STEP-BY-STEP CONNECTION GUIDE

### Step 1: Power Distribution
1. Cắm pin 24V vào fuse 25A
2. Sau fuse, chia 2 đầu:
   - Đầu 1: L298N Module
   - Đầu 2: Buck Converter 24V input

### Step 2: Raspberry Pi Power
1. Buck Converter output (5V) → Raspberry Pi
2. GND wire từ tất cả module → GND của Pi (star connection)

### Step 3: Motor Connections
1. Motor 1 OUT1, OUT2 → L298N OUT1, OUT2
2. Motor 2 OUT1, OUT2 → L298N OUT3, OUT4
3. Motor 3 → có thể điều khiển bằng GPIO thêm hoặc relay

### Step 4: GPIO Connections (Motor Control)
Sử dụng dây jumper male-to-female từ L298N đến Pi GPIO:
- IN1, IN2, PWM từ driver → Pi GPIO theo config.py

### Step 5: Ultrasonic Sensors
1. Sensor 1 (Trái):
   - TRIG → GPIO17
   - ECHO → GPIO32 (với voltage divider)
2. Sensor 2 (Giữa):
   - TRIG → GPIO19
   - ECHO → GPIO26 (với voltage divider)
3. Sensor 3 (Phải):
   - TRIG → GPIO20
   - ECHO → GPIO21 (với voltage divider)

### Step 6: Camera
Cắm USB camera vào cổng USB 2/3/4 của Pi

### Step 7: Test Connections
```bash
# Kiểm tra GPIO
gpio readall

# Kiểm tra Camera
lsusb
ls /dev/video*

# Chạy test
sudo python3 test_brain.py
```

---

## 🚨 TROUBLESHOOTING

### GPIO Not Responding
```bash
# Check current user permissions
id

# Add to GPIO group
sudo usermod -aG gpio $USER

# Or run with sudo
sudo python3 main.py
```

### Ultrasonic Returns 999 (out of range)
- Kiểm tra voltage divider trên ECHO pins
- Verify TRIG/ECHO pins trên config.py
- Test each sensor individually

### Motor Not Spinning
- Kiểm tra Pin VCC/GND trên L298N
- Kiểm tra GPIO pins (sudo gpio readall)
- Test motor directly với 12V (không qua driver)

### Camera Not Detected
```bash
# List devices
ls /dev/video*

# Check USB device
lsusb

# Give permissions
sudo chmod 666 /dev/video0
```

---

## 📊 POWER CONSUMPTION TABLE

| Component | Voltage | Current | Notes |
|-----------|---------|---------|-------|
| Motor × 3 | 12V | ~3-4A each | Peak: 5A |
| Pi + Peripherals | 5V | ~2A | Stable |
| Sensors | 5V | ~100mA | Minimal |
| **Total** | - | ~**14-16A** | 20Ah battery → 1.2-1.4h |

---

## ✅ VERIFICATION CHECKLIST

- [ ] Tất cả GND kết nối với nhau (star configuration)
- [ ] 5V stable (sudo python -c "import RPi.GPIO as GPIO; GPIO.setup(...)") 
- [ ] Motor spinner sau khi cấp power
- [ ] Cảm biến siêu âm đếm xung từ
- [ ] Camera nhận dạng người (test_brain.py)
- [ ] LCD hiện thị (nếu có)

---

**Thành công! Xe đã sẵn sàng chạy 🚀**
