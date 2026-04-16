# 🤖 ROBOTIC HUTECH - NLU FOLLOW ME ROBOT

## Mô Tả Dự Án
Chiếc xe tự động thông minh có khả năng:
- 🎯 **Phát hiện người** từ camera USB sử dụng AI (YOLO/HOG)
- 👤 **Theo dõi và đi theo** người được phát hiện
- 🚗 **Quay trái/phải** khi cần
- 🛑 **Dừng lại** khi phát hiện chướng ngại vật
- ⚡ **Tăng/giảm tốc** động
- 📡 **Tránh chướng ngại vật** bằng cảm biến siêu âm 3 chiều

---

## Phần Cứng (Hardware)

### Th Chính
- **Raspberry Pi 4 Model B** (4GB RAM)
- **Màn hình LCD 3.5"** (SPI)
- **Camera USB OutdoorUSB** hoặc **camera ngoài USB**
- **Pin Lithium 24V 20Ah** (Li-ion)

### Module Điều Khiển
- **Buckconverter 24V → 5V 5A** (điều chỉnh áp cho Raspberry Pi)
- **Motor Driver** (L298N hoặc tương tự) × 2 chiếc
- **Cáp chủy lỏng 25A** có công tắc ON/OFF

### Cảm Biến
- **Ultrasonic HC-SR04** × 3 cái
  - Cảm biến Trái: TRIG=GPIO17, ECHO=GPIO32
  - Cảm biến Giữa: TRIG=GPIO19, ECHO=GPIO26
  - Cảm biến Phải: TRIG=GPIO20, ECHO=GPIO21

### Động Cơ
- **DC Motor 12V** × 3 chiếc (hoặc 2 chiếc + 1 bánh quay)
- **Bánh xe** PU 100mm × 3 chiếc

---

## Kết Nối Điện (Wiring)

### Motor Control (L298N Module)
```
Motor Trái:
  - IN1 = GPIO23
  - IN2 = GPIO24
  - PWM = GPIO12 (BCM 12)
  
Motor Phải:
  - IN1 = GPIO27
  - IN2 = GPIO17
  - PWM = GPIO13 (BCM 13)
```

### Ultrasonic Sensors (HC-SR04)
```
Sensor Trái:
  - TRIG = GPIO17
  - ECHO = GPIO32
  - VCC = 5V
  - GND = GND

Sensor Giữa:
  - TRIG = GPIO19
  - ECHO = GPIO26
  
Sensor Phải:
  - TRIG = GPIO20
  - ECHO = GPIO21
```

### Power Distribution
```
Pin 24V: Motor + → L298N VCC
Pin GND: Motor - → L298N GND → Raspberry Pi GND
Convert 24V → 5V: Raspberry Pi Power
USB Camera: USB Port
```

---

## Cài Đặt Phần Mềm

### 1. Chuẩn Bị Raspberry Pi

```bash
# Update hệ thống
sudo apt-get update
sudo apt-get upgrade -y

# Cài đặt Python 3 và pip
sudo apt-get install python3 python3-pip -y

# Cài đặt thư viện GPIO
sudo apt-get install python3-rpi.gpio -y

# Cài đặt OpenCV
sudo apt-get install python3-opencv -y
```

### 2. Clone Repository

```bash
cd ~
git clone https://github.com/your-repo/RoboticHutech_NLU.git
cd RoboticHutech_NLU/Robot
```

### 3. Cài Đặt Dependencies

```bash
# Cài đặt từ requirements.txt
pip3 install -r requirements.txt

# Hoặc cài thủ công
pip3 install opencv-python numpy RPi.GPIO
```

### 4. Tải Mô Hình YOLO (Tùy Chọn)

Nếu muốn sử dụng YOLO cho phát hiện người:

```bash
cd ~/RoboticHutech_NLU/Robot

# Tải YOLOv3-tiny weights (235 MB)
wget https://pjreddie.com/media/files/yolov3-tiny.weights

# Tải cấu hình YOLO
wget https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3-tiny.cfg

# Tải file label COCO
wget https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names
```

---

## Chạy Chương Trình

### 1. Test Từng Module

```bash
python3 test_brain.py
```

Điều này sẽ test:
- ✅ Motor control (Tiến, Lùi, Quay)
- ✅ Ultrasonic sensors (Đọc khoảng cách 3 cảm biến)
- ✅ Camera detection (Phát hiện người)

### 2. Chạy Chương Trình Chính

```bash
sudo python3 main.py
```

**Lưu ý:** Cần `sudo` để truy cập GPIO pins

### 3. Phím Điều Khiển (Manual Mode)

```
W: Đi tiến
S: Lùi
A: Quay trái
D: Quay phải
Space: Dừng lại
+: Tăng tốc độ
-: Giảm tốc độ
Q: Thoát
```

---

## Cấu Trúc Thư Mục

```
Robot/
├── config.py              # Cấu hình chung (GPIO pins, tốc độ, etc)
├── motor_control.py       # Điều khiển động cơ
├── sensor_control.py      # Xử lý cảm biến siêu âm
├── camera_detection.py    # Phát hiện người từ camera
├── main.py               # Chương trình chính
├── test_brain.py         # Script test từng module
├── requirements.txt      # Danh sách thư viện Python
└── README.md            # Tài liệu này
```

---

## Luồng Hoạt Động (Workflow)

```
1. Khởi động
   ↓
2. Chế Độ Quét (Scan Mode)
   - Quay tròn tìm người
   ↓
3. Phát Hiện Người
   - Nếu detect người → Chuyển sang Follow Mode
   - Nếu không → Tiếp tục quét
   ↓
4. Chế Độ Theo Dõi (Follow Mode)
   - Cập nhật vị trí người từ camera
   - Kiểm tra chướng ngại vật bằng ultrasonic
   - Điều khiển động cơ để đi theo:
     * Người ở trái → Quay trái
     * Người ở phải → Quay phải
     * Người ở giữa → Đi thẳng
   ↓
5. Tránh Chướng Ngại Vật
   - Trái < SAFE_DISTANCE → Quay phải
   - Phải < SAFE_DISTANCE → Quay trái
   - Giữa < STOP_DISTANCE → DỪNG
```

---

## Điều Chỉnh Thông Số

Mở file `config.py` để điều chỉnh:

```python
# Tốc độ động cơ (0-100%)
MAX_SPEED = 100
NORMAL_SPEED = 60
TURN_SPEED = 50

# Khoảng cách cảm biến (cm)
SAFE_DISTANCE = 30      # Khoảng cách an toàn
STOP_DISTANCE = 20      # Khoảng cách dừng

# Camera
CONFIDENCE_THRESHOLD = 0.5  # Ngưỡng detect: 0-1
CENTER_TOLERANCE = 50       # Độ sai lệch tối đa khi canh giữa
```

---

## Khắc Phục Sự Cố

### Camera không được nhận diện
```bash
# Kiểm tra camera
lsusb
ls /dev/video*

# Cấp quyền truy cập
sudo chmod 666 /dev/video0
```

### Không thể truy cập GPIO pins
```bash
# Chạy với quyền sudo
sudo python3 main.py
```

### Cảm biến siêu âm không hoạt động
```bash
# Kiểm tra GPIO pins có đúng không
# Xem file config.py và kiểm tra lại kết nối
```

### Motor không quay
```bash
# Kiểm tra pin PWM có được cấp điện không
# Kiểm tra kết nối động cơ
# Chạy test_brain.py để test từng module
```

---

## Cải Tiến Trong Tương Lai

- [ ] Thêm LCD display hiển thị thông tin
- [ ] Lưu logs vào file
- [ ] Web interface điều khiển từ xa
- [ ] Machine learning để học cách điều hướng
- [ ] Tích hợp LiDAR cho tránh chướng ngại vật tốt hơn
- [ ] Nội bộ từng động cơ để cân bằng tốc độ
- [ ] Voice control để nhận lệnh bằng giọng nói

---

## Tác Giả
**Robotic Hutech NLU Team**

## Giấy Phép
MIT License

---

**Chúc Vui! 🚗💨**
