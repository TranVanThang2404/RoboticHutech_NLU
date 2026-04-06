# QUICK START - HƯỚNG DẪN NHANH

## 1️⃣ CỤC LS - LẦN ĐẦU SỬ DỤNG

### Chuẩn bị
Cắm đủ câu:
- Power supply 24V vào motor driver
- USB camera vào Raspberry Pi
- Tất cả GPIO pins về đúng vị trí (xem config.py)

### Cài đặt (SSH vào Raspberry Pi)

```bash
# SSH vào Pi
ssh pi@192.168.x.x  # Thay IP của Pi

# Clone code
git clone https://github.com/your-repo/RoboticHutech_NLU.git
cd RoboticHutech_NLU/Robot

# Cài thư viện
pip3 install -r requirements.txt

# Test các module
sudo python3 test_brain.py
```

---

## 2️⃣ CHẠY CHƯƠNG TRÌNH CHÍNH

```bash
# Mode tự động theo dõi người
sudo python3 main.py

# Mode nâng cao với PID control
sudo python3 advanced_control.py
```

---

## 3️⃣ KẾT QUẢ MONG ĐỢI

✅ **Boot thành công**: Sẽ thấy dòng khởi tạo các module
✅ **Bắt đầu quét**: Xe sẽ quay tròn tìm người
✅ **Phát hiện người**: Khi camera detect người → xe sẽ đi theo

---

## 4️⃣ ĐIỀU CHỈNH NHANH

| Vấn đề | Giải Pháp |
|--------|----------|
| Xe chạy quá nhanh | Giảm `NORMAL_SPEED` trong config.py |
| Không detect người | Tăng `CONFIDENCE_THRESHOLD` hoặc check camera |
| Xe va chướng ngại | Giảm `SAFE_DISTANCE` |
| Xe quay không tròn | Điều chỉnh `TURN_SPEED` |

---

## 5️⃣ DEBUG MODE

Bật debug: Mở `config.py` → `DEBUG_MODE = True`

Sẽ in chi tiết:
```
[Motor] Trái: 60% | Phải: 60%
[Sensors] L: 45.32cm | C: 52.18cm | R: 48.75cm
[Camera] Person detected: True at position (320, 240)
```

---

## 6️⃣ DỪNG CHƯƠNG TRÌNH

**Bấm `Ctrl + C` trong terminal**

Hoặc nếu chạy trên màn hình LCD, bấn nút Emergency Stop (nếu có).

---

## 7️⃣ CHẾ ĐỘ THỦ CÔNG (Manual Mode)

```python
from motor_control import MotorControl

motor = MotorControl()
motor.move_forward(80)      # Đi tiến 80%
time.sleep(2)

motor.turn_right(50)        # Quay phải 50%
time.sleep(1)

motor.stop()                # Dừng
```

---

## 8️⃣ TÍCH HỢP KHÁC

### Với LCD Screen (3.5" SPI)
```bash
sudo pip3 install RPi.GPIO
```

### Với Web Control
```bash
pip3 install flask
python3 advanced_control.py
# Truy cập: http://pi-ip:5000/status
```

---

## 9️⃣ TỪ KHÓA

| Mode | Hành động |
|------|----------|
| `Follow` | Đi theo người |
| `Scan` | Quét tìm người |
| `Avoid` | Tránh chướng ngại vật |
| `Emergency` | Dừng khẩn cấp |

---

## 🔟 THÔNG SỐ QUAN TRỌNG

```python
# Trong config.py

MAX_SPEED = 100              # Tốc độ tối đa (%)
NORMAL_SPEED = 60            # Tốc độ thường xuyên
TURN_SPEED = 50              # Tốc độ quay

SAFE_DISTANCE = 30           # Khoảng cách an toàn (cm)
STOP_DISTANCE = 20           # Dừng nếu < 20cm

CONFIDENCE_THRESHOLD = 0.5   # Ngưỡng detect người (0-1)
CENTER_TOLERANCE = 50        # Độ lệch khi canh giữa
```

---

**Thắc mắc? Xem README.md đầy đủ** 📖
