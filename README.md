# 🤖 RoboticHutech - NLU Robot Project

![Robot Follow Me](https://img.shields.io/badge/Status-Complete-brightgreen)
![Python](https://img.shields.io/badge/Python-3.7%2B-blue)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-4%20Model%20B-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

Chiếc xe tự động thông minh có khả năng **phát hiện người, theo dõi, tránh chướng ngại vật** bằng AI, Ultrasonic sensor, và OpenCV.

## 🎯 Tính Năng Chính

✅ **Phát hiện người** từ camera USB (YOLO/HOG)
✅ **Theo dõi động** người được phát hiện
✅ **Điều khiển hướng** (quay trái/phải, đi tròn)
✅ **Tránh chướng ngại vật** bằng cảm biến siêu âm 3 chiều
✅ **Điều chỉnh tốc độ** động
✅ **PID Control** cho steering chính xác
✅ **Web Interface** tùy chọn (Flask)
✅ **Chế độ test** từng module

## 📂 Cấu Trúc Thư Mục

```
RoboticHutech_NLU/
├── README.md                 # Tài liệu chính (bạn đang đọc)
└── Robot/
    ├── config.py            # Cấu hình GPIO, tốc độ, ngưỡng
    ├── motor_control.py     # Điều khiển 3 động cơ
    ├── sensor_control.py    # Xử lý 3 cảm biến siêu âm
    ├── camera_detection.py  # Phát hiện người từ camera
    ├── main.py             # Chương trình chính autonomy
    ├── advanced_control.py # Chế độ nâng cao (PID + Threading)
    ├── test_brain.py       # Test từng module
    ├── calibration.py      # Công cụ hiệu chỉnh
    ├── examples.py         # 6 ví dụ chức năng
    ├── requirements.txt    # Python dependencies
    ├── install.sh          # Script cài đặt tự động
    ├── README.md           # Tài liệu chi tiết phần mềm
    ├── QUICKSTART.md       # Hướng dẫn nhanh
    ├── HARDWARE_GUIDE.md   # Hướng dẫn kết nối phần cứng
    └── examples/           # Thư mục ví dụ (tạo nếu cần)
```

## ⚡ Bắt Đầu Nhanh (Quick Start)

### 1. Yêu cầu Phần Cứng
- Raspberry Pi 4 Model B (4GB RAM)
- USB Camera
- 3x Motor + Motor Driver
- 3x Ultrasonic Sensor HC-SR04
- Pin 24V + Buck Converter 5V

### 2. Cài Đặt
```bash
cd Robot
chmod +x install.sh
./install.sh
```

### 3. Cấu Hình
```bash
# Sửa GPIO pins theo phần cứng của bạn
nano config.py
```

### 4. Test Từng Module
```bash
sudo python3 test_brain.py
```

### 5. Chạy Chương Trình Chính
```bash
sudo python3 main.py
```

## 📚 Tài Liệu

| Tệp | Nội Dung |
|-----|---------|
| [Robot/README.md](Robot/README.md) | Tài liệu phần mềm chi tiết, calibration, troubleshooting |
| [Robot/QUICKSTART.md](Robot/QUICKSTART.md) | Hướng dẫn cài đặt nhanh & điều chỉnh nhanh |
| [Robot/HARDWARE_GUIDE.md](Robot/HARDWARE_GUIDE.md) | Sơ đồ kết nối phần cứng, pin mapping, danh sách linh kiện |

## 💻 Mã Nguồn Chi Tiết

### config.py
Cấu hình tất cả thông số: GPIO pins, tốc độ motor, ngưỡng detect cảm biến, etc.

```python
# GPIO Pins
MOTOR_LEFT_PIN1 = 23
MOTOR_LEFT_PWM = 12
ULTRASONIC_LEFT_TRIG = 17

# Tốc độ
MAX_SPEED = 100
NORMAL_SPEED = 60
TURN_SPEED = 50

# Khoảng cách (cm)
SAFE_DISTANCE = 30
STOP_DISTANCE = 20
```

### motor_control.py
```python
motor = MotorControl()
motor.move_forward(60)      # Đi tiến 60%
motor.turn_left(50)         # Quay trái 50%
motor.increase_speed(10)    # Tăng tốc 10%
motor.stop()                # Dừng lại
```

### sensor_control.py
```python
sensors = SensorManager()
data = sensors.update_sensors()
print(f"L: {data['left']}cm | C: {data['center']}cm | R: {data['right']}cm")
```

### camera_detection.py
```python
camera = PersonDetector()
if camera.detect_person():
    offset = camera.get_horizontal_offset()
    print(f"Person at offset: {offset}px")
```

### main.py
Chương trình chính với 2 chế độ:
- **Scan Mode**: Quay tròn tìm người
- **Follow Mode**: Theo dõi người được phát hiện

### advanced_control.py
Chế độ nâng cao:
- PID Steering Control cho điều khiển chính xác
- Multi-threading cho xử lý song song
- Web Control Interface (Flask optional)

## 🔧 Các Công Cụ Đi Kèm

### test_brain.py
Test các module riêng lẻ:
```bash
sudo python3 test_brain.py
```

### calibration.py
Hiệu chỉnh các thông số:
```bash
sudo python3 calibration.py
```

Menu:
1. Hiệu chỉnh Motor
2. Hiệu chỉnh Cảm biến
3. Hiệu chỉnh Camera
4. Cân bằng tốc độ
5. Tìm ngưỡng Confidence tối ưu

### examples.py
6 ví dụ chức năng (chạy từng cái):
```bash
python3 examples.py 1      # Manual Control
python3 examples.py 2      # Sensor Reading
python3 examples.py 3      # Person Detection
python3 examples.py 4      # Obstacle Avoidance
python3 examples.py 5      # Speed Adjustment
python3 examples.py 6      # Combined Operation
```

## 🎮 Phím Điều Khiển

Khi chạy `main.py`, có thể sử dụng:

```
W: Tiến        ↑
S: Lùi         ↓
A: Quay trái   ←
D: Quay phải   →
Space: Dừng
+: Tăng tốc
-: Giảm tốc
Q: Thoát
```

## 📊 Luồng Hoạt Động

```
1. Khởi động → Khởi tạo tất cả module
   ↓
2. Scan Mode → Quay tròn tìm người
   ↓
3. Phát hiện người → Chuyển sang Follow Mode
   ↓
4. Follow Mode → 
   ├─ Cập nhật vị trí người từ camera
   ├─ Kiểm tra chướng ngại vật
   ├─ Điều khiển motor:
   │   ├─ Người trái → Quay trái
   │   ├─ Người phải → Quay phải
   │   └─ Người giữa → Đi thẳng
   └─ Nếu mất người > 3s → Quay lại Scan Mode
   ↓
5. Tránh chướng ngại vật → Dừng/Quay
```

## 🛠️ Cải Tiến Trong Tương Lai

- [ ] Tích hợp LiDAR tạo bản đồ
- [ ] Machine Learning tối ưu hóa hành vi
- [ ] Điều khiển giọng nói
- [ ] LCD display hiển thị thông tin thời gian thực
- [ ] Lưu logs cho phân tích
- [ ] Web dashboard quản lý từ xa
- [ ] Các cảm biến bổ sung (GPS, IMU)

## 🐕 Video Demo

*[Thêm link YouTube hoặc video demo nếu có]*

## 👥 Đóng Góp

Nếu bạn muốn cải tiến, vui lòng:
1. Fork repository
2. Tạo branch cho feature (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Tạo Pull Request

## 📜 Giấy Phép

MIT License - Xem file LICENSE để chi tiết

## 📧 Liên Hệ

**Robotic Hutech NLU Team**
- Email: robothutech@hust.edu.vn
- GitHub: https://github.com/your-org/RoboticHutech_NLU

## 🙏 Cảm Ơn

- OpenCV community
- Raspberry Pi Foundation
- YOLOv3 authors
- Tất cả những người/tổ chức góp phần vào dự án

---

**Made with ❤️ by Robotic Hutech Team**

*Happy coding! 🚀*