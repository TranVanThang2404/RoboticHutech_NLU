# 📋 PROJECT STRUCTURE & FILE GUIDE

## Cây Thư Mục

```
RoboticHutech_NLU/
│
├── README.md               📄 Tài liệu chính (Introduction)
├── .git/                   📁 Git repository
│
└── Robot/                  🤖 THƯ MỤC CHÍNH
    │
    ├── 🔧 CÁC MODULE CHÍNH
    ├── config.py           ⚙️  Cấu hình - GPIO pins, tốc độ, ngưỡng
    ├── motor_control.py    🔌 Điều khiển 3 động cơ DC
    ├── sensor_control.py   📡 Xử lý 3 cảm biến Ultrasonic
    ├── camera_detection.py 📸 Phát hiện người từ camera USB (YOLO/HOG)
    │
    ├── 🚀 CHƯƠNG TRÌNH CHÍNH
    ├── main.py             🎬 Chương trình chính (Autonomy mode)
    ├── advanced_control.py 🎯 Mode nâng cao (PID Control + Threading)
    │
    ├── 🧪 CÁC CÔNG CỤ TEST/DEBUG
    ├── test_brain.py       ✔️  Test tất cả modules
    ├── calibration.py      🔧 Hiệu chỉnh cảm biến/motor/camera
    ├── examples.py         📚 6 ví dụ chức năng khác nhau
    │
    ├── 📖 TÀI LIỆU
    ├── README.md           📘 Tài liệu phần mềm chi tiết
    ├── QUICKSTART.md       ⚡ Hướng dẫn bắt đầu nhanh
    ├── HARDWARE_GUIDE.md   🔌 Sơ đồ kết nối phần cứng
    ├── COMMANDS.md         📝 Các lệnh & recipes hữu ích
    │
    ├── 📦 DEPENDENCIES & CONFIG
    ├── requirements.txt    📋 Python packages
    ├── install.sh          🔨 Script cài đặt tự động
    ├── .gitignore          🚫 Git ignore rules
    │
    └── 📁 THƯ MỤC TỰY CHỌN (Tạo nếu cần)
        ├── models/         🧠 YOLO weights, configs
        ├── logs/           📜 Log files
        ├── data/           📊 Dữ liệu thu thập
        └── examples/       📚 Thêm ví dụ
```

---

## 📄 MÌNH TIÊU CỤ CHI TIẾT

### 🔧 Core Modules

#### `config.py` - MAIN CONFIGURATION
- **Dòng 1-50**: Cấu hình GPIO pins
  - Motor pins & PWM
  - Sensor TRIG/ECHO pins
- **Dòng 51-75**: Motor parameters
  - Tốc độ max/min, tốc độ thường xuyên, etc
- **Dòng 76-100**: Camera settings
  - Frame size, FPS, confidence threshold
- **Dòng 101+**: Thông số điều khiển
  - Khoảng cách an toàn, PID tuning, etc

**Dùng cho**: Tất cả module khác import từ đây

---

#### `motor_control.py` - MOTOR CONTROL ENGINE
- **Class `MotorControl`**
  - `__init__()`: Khởi tạo GPIO PWM
  - `set_motor_speed(left, right)`: Đặt tốc độ
  - `move_forward(speed)`: Đi tiến
  - `move_backward(speed)`: Lùi
  - `turn_left(speed) / turn_right(speed)`: Quay
  - `stop()`: Dừng
  - `cleanup()`: Dọn dẹp GPIO

**Dùng cho**: Điều khiển tất cả động cơ

**Ví dụ**:
```python
motor = MotorControl()
motor.move_forward(70)
time.sleep(3)
motor.stop()
```

---

#### `sensor_control.py` - ULTRASONIC SENSORS
- **Class `UltrasonicSensor`** (1 cảm biến)
  - `get_distance()`: Đọc khoảng cách (cm)
  - `is_obstacle_detected(threshold)`: Kiểm tra chướng ngại
  
- **Class `SensorManager`** (3 cảm biến)
  - `update_sensors()`: Cập nhật tất cả 3 cảm biến
  - `is_any_obstacle()`: Có chướng ngại không

**Dùng cho**: Tránh chướng ngại, kiểm tra an toàn

**Ví dụ**:
```python
sensors = SensorManager()
data = sensors.update_sensors()
if data['center'] < 20:
    print("Obstacle ahead!")
```

---

#### `camera_detection.py` - PERSON DETECTION
- **Class `PersonDetector`**
  - `detect_person()`: Phát hiện người trong frame
  - `get_person_center()`: Tọa độ trung tâm người
  - `get_horizontal_offset()`: Độ lệch ngang (px)
  - `draw_detections(frame)`: Vẽ bounding box
  - Hỗ trợ 3 phương pháp: YOLO, MobileNet SSD, HOG

**Dùng cho**: Phát hiện & theo dõi người

---

### 🚀 Main Programs

#### `main.py` - AUTONOMOUS ROBOT
- **Class `Robot`**
  - `scan_mode()`: Quay tòn tìm người
  - `follow_person()`: Đi theo người
  - `obstacle_avoidance()`: Tránh chướng ngại
  - `run()`: Vòng lặp chính

**Chạy**: `sudo python3 main.py`

---

#### `advanced_control.py` - ENHANCED MODE
- **Class `AdvancedRobot`**
  - Multi-threading (sensor thread, camera thread)
  - PID control cho steering chính xác
  - Web control interface (Flask)

- **Class `WebRobotControl`**
  - REST API `/status`, `/control/<action>`
  - Access: `http://pi-ip:5000`

**Chạy**: `sudo python3 advanced_control.py`

---

### 🧪 Testing & Calibration

#### `test_brain.py` - MODULE TESTING
- Test 1: Motor control (Forward, Back, Turn)
- Test 2: Sensors (Read 10 seconds)
- Test 3: Camera (Detect person for 10s)

**Chạy**: `sudo python3 test_brain.py`

**Tùy chọn**: Chạy từng test riêng (edit script)

---

#### `calibration.py` - TUNING TOOL
Menu với 5 tùy chọn:
1. Calibrate Motors (test cân bằng)
2. Calibrate Sensors (test độ chính xác)
3. Calibrate Camera (test phát hiện)
4. Balance Motor Speed (đặt cùng tốc độ)
5. Find Confidence Threshold (threshold tối ưu)

**Chạy**: `sudo python3 calibration.py`

---

#### `examples.py` - FUNCTIONAL EXAMPLES
6 ví dụ:
1. Manual motor control
2. Sensor reading
3. Person detection
4. Obstacle avoidance
5. Motor speed adjustment
6. Combined operation

**Chạy**: `python3 examples.py` hoặc `python3 examples.py 3`

---

### 📖 Documentation

| File | Nội Dung | Mục Đích |
|------|---------|---------|
| README.md | Overview chính | Giới thiệu dự án |
| QUICKSTART.md | Cài đặt nhanh | Bắt đầu ngay |
| HARDWARE_GUIDE.md | Kết nối phần cứng | Wiring & pinout |
| COMMANDS.md | Lệnh & recipes | Reference nhanh |
| Robot/README.md | Chi tiết phần mềm | Hướng dẫn đầy đủ |

---

## 🔄 DATA FLOW

```
User Request
    ↓
main.py / advanced_control.py
    ↓
    ├── motor_control.py (Motor commands)
    ├── sensor_control.py (Read distances)
    └── camera_detection.py (Detect person)
    ↓
GPIO Pins on Raspberry Pi
    ↓
Hardware
    ├── Motors spin/stop
    ├── Sensors measure
    └── Camera captures
```

---

## 📊 MODULE DEPENDENCIES

```
main.py/advanced_control.py
    ├── config.py ← Tất cả import từ đây
    ├── motor_control.py
    ├── sensor_control.py
    └── camera_detection.py

test_brain.py
    ├── motor_control.py
    ├── sensor_control.py
    └── camera_detection.py

calibration.py
    ├── motor_control.py
    ├── sensor_control.py
    └── camera_detection.py

examples.py
    └── Các module riêng lẻ
```

---

## 🛠️ CUSTOMIZATION CHECKLIST

- [ ] Edit `config.py` với GPIO pins đúng
- [ ] Chạy `calibration.py` để hiệu chỉnh
- [ ] Chạy `test_brain.py` để verify
- [ ] Điều chỉnh `NORMAL_SPEED`, `TURN_SPEED`
- [ ] Điều chỉnh `CONFIDENCE_THRESHOLD` nếu cần
- [ ] Tối ưu hóa PID parameters nếu dùng advanced mode
- [ ] Backup cấu hình: `cp config.py config.py.bak`

---

## 📚 CODE STATISTICS

```
Total Lines: ~3000+
  - Core logic: ~1500
  - Config & commenting: ~500
  - Multiple examples & docs: ~1000+

Main modules:
  config.py: ~150 lines
  motor_control.py: ~200 lines
  sensor_control.py: ~200 lines
  camera_detection.py: ~400 lines
  main.py: ~300 lines
  advanced_control.py: ~400 lines
  test_brain.py: ~300 lines
  calibration.py: ~350 lines
  examples.py: ~600 lines
```

---

**Sẽn sàng! 🚀**
