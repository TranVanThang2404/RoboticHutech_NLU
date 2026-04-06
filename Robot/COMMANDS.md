# 📖 COMMON COMMANDS & RECIPES

Các lệnh và mã hữu ích khi làm việc với RoboticHutech Robot

---

## 🔧 LỆNH THIẾT LẬP BAN ĐẦU

### Kết nối SSH đến Raspberry Pi
```bash
# Tìm IP của Pi
arp-scan -l

# Kết nối
ssh pi@192.168.1.100  # Thay IP của Pi
# Mật khẩu mặc định: raspberry (nên đổi!)
```

### Clone Project
```bash
cd ~
git clone https://github.com/your-repo/RoboticHutech_NLU.git
cd RoboticHutech_NLU/Robot

# Hoặc tải về dạng ZIP
wget https://github.com/your-repo/RoboticHutech_NLU/archive/main.zip
unzip main.zip
```

### Cấp quyền thực thi cho script
```bash
chmod +x install.sh
chmod +x *.py

# Hoặc cấp quyền toàn bộ
chmod -R 755 ~/RoboticHutech_NLU
```

---

## 📦 CÀI ĐẶT

### Cài tự động
```bash
cd ~/RoboticHutech_NLU/Robot
chmod +x install.sh
./install.sh
```

### Cài thủ công từng bước
```bash
# Update hệ thống
sudo apt-get update && sudo apt-get upgrade -y

# Python + pip
sudo apt-get install python3 python3-pip -y

# GPIO library
pip3 install RPi.GPIO

# OpenCV
pip3 install opencv-python

# Từ requirements.txt
pip3 install -r requirements.txt
```

---

## 🚀 CHẠY CHƯƠNG TRÌNH

### Chạy chương trình chính
```bash
sudo python3 main.py
```

### Chạy chế độ nâng cao (PID + Threading)
```bash
sudo python3 advanced_control.py
```

### Chạy test modules
```bash
sudo python3 test_brain.py
```

### Chạy công cụ calibration
```bash
sudo python3 calibration.py
```

### Chạy ví dụ cụ thể
```bash
# Menu chọn
python3 examples.py

# Hoặc chạy trực tiếp
python3 examples.py 1      # Manual Control
python3 examples.py 4      # Obstacle Avoidance
```

---

##🐛 DEBUGGING & TROUBLESHOOTING

### Kiểm tra GPIO pins
```bash
# Cài đặt gpio command
sudo apt-get install wiringpi

# Xem trạng thái
gpio readall

# Kiểm tra GPIO mode
gpio mode 17 input
gpio read 17
```

### Kiểm tra Camera
```bash
# Liệt kê USB devices
lsusb

# Xem video devices
ls -la /dev/video*

# Cấp quyền
sudo chmod 666 /dev/video0

# Test camera (nếu có fswebcam)
sudo apt-get install fswebcam
fswebcam test.jpg
```

### Kiểm tra Python
```bash
# Version
python3 --version

# Interpreter path
which python3

# Test import
python3 -c "import RPi.GPIO as GPIO; print('GPIO OK')"
python3 -c "import cv2; print(cv2.__version__)"
```

### Xem logs
```bash
# Real-time log
sudo python3 main.py 2>&1 | tee robot.log

# Xem file log
tail -f robot.log
```

---

## 💾 BACKUP & RESTORE

### Backup toàn bộ project
```bash
cd ~/RoboticHutech_NLU
git add .
git commit -m "Backup $(date +%Y-%m-%d)"
git push origin main

# Hoặc zip
tar -czf ../RoboticHutech_backup_$(date +%Y%m%d).tar.gz .
```

### Restore từ backup
```bash
tar -xzf RoboticHutech_backup_20230101.tar.gz
```

---

## 📊 MONITOR & LOG

### Chạy với output log
```bash
sudo python3 main.py > /tmp/robot_$(date +%s).log 2>&1 &
```

### Xem process đang chạy
```bash
ps aux | grep python

# Xem memory usage
free -m

# Xem CPU temperature (Raspberry Pi)
vcgencmd measure_temp
```

### Kill process
```bash
# Tìm PID
ps aux | grep main.py

# Kill
sudo kill -9 <PID>

# Hoặc kill all python
sudo pkill -f python3
```

---

## 🔧 CONFIG & CUSTOMIZATION

### Sửa cấu hình nhanh
```bash
# Mở config
nano config.py

# Thay đổi tốc độ
NORMAL_SPEED = 70  # từ 60

# Thay đổi GPIO pins
MOTOR_LEFT_PIN1 = 23

# Lưu: Ctrl+X → Y → Enter
```

### Backup config gốc
```bash
cp config.py config.py.bak
```

### Restore config gốc
```bash
cp config.py.bak config.py
```

---

## 🎨 CODE MONITORING

### Kiểm tra syntax
```bash
python3 -m py_compile *.py
```

### Chạy linter (nếu cài)
```bash
pip3 install pylint
pylint main.py
```

### Format code
```bash
pip3 install black
black *.py
```

---

## 🌐 NETWORK

### SSH từ Local Machine tới Pi
```bash
# Copy file từ Pi
scp pi@192.168.1.100:/home/pi/file.txt ./

# Copy file tới Pi
scp ./file.txt pi@192.168.1.100:/home/pi/

# Entire folder
scp -r ./Robot pi@192.168.1.100:/home/pi/
```

### Chạy qua SSH terminal
```bash
ssh pi@192.168.1.100 "sudo python3 ~/RoboticHutech_NLU/Robot/main.py"
```

### Access qua IP tĩnh
```bash
# Set static IP
sudo nano /etc/dhcpcd.conf

# Add:
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
```

---

## 💡 USEFUL PYTHON SNIPPETS

### Đọc một GPIO pin
```python
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN)
state = GPIO.input(17)
GPIO.cleanup()
```

### Ghi GPIO pin
```python
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)
GPIO.output(17, GPIO.HIGH)  # Cao
GPIO.output(17, GPIO.LOW)   # Thấp
GPIO.cleanup()
```

### PWM (Pulse Width Modulation)
```python
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)

pwm = GPIO.PWM(17, 100)  # 100 Hz
pwm.start(50)   # 50% duty cycle
pwm.ChangeDutyCycle(75)
pwm.stop()
GPIO.cleanup()
```

### Đọc cảm biến siêu âm
```python
import time
GPIO.setup(23, GPIO.OUT)  # TRIG
GPIO.setup(24, GPIO.IN)   # ECHO

GPIO.output(23, GPIO.HIGH)
time.sleep(0.00001)
GPIO.output(23, GPIO.LOW)

while GPIO.input(24) == GPIO.LOW:
    pass
start = time.time()

while GPIO.input(24) == GPIO.HIGH:
    pass
end = time.time()

distance = ((end - start) * 34300) / 2
```

### Capture từ camera
```python
import cv2

cap = cv2.VideoCapture(0)
ret, frame = cap.read()

if ret:
    cv2.imshow('Camera', frame)
    cv2.imwrite('photo.jpg', frame)
    cv2.waitKey(1)

cap.release()
cv2.destroyAllWindows()
```

---

## 🚨 EMERGENCY COMMANDS

### Dừng tất cả process
```bash
sudo killall -9 python3
```

### Reboot Pi
```bash
sudo reboot
```

### Shutdown Pi
```bash
sudo shutdown -h now
```

### Reset GPIO
```bash
gpio reset
```

---

## 📝 CHEAT SHEET

| Task | Command |
|------|---------|
| SSH vào Pi | `ssh pi@192.168.1.100` |
| Edit config | `nano config.py` |
| Chạy chương trình | `sudo python3 main.py` |
| Test module | `sudo python3 test_brain.py` |
| Hiệu chỉnh | `sudo python3 calibration.py` |
| Xem GPIO | `gpio readall` |
| Kill process | `sudo pkill -f python3` |
| Xem temp | `vcgencmd measure_temp` |
| Copy tệp | `scp file.txt pi@IP:~/` |
| View log | `tail -f robot.log` |

---

## 📚 RESOURCE LINKS

- [Raspberry Pi Documentation](https://www.raspberrypi.com/documentation/)
- [Python RPi.GPIO Docs](https://sourceforge.net/p/raspberry-gpio-python/wiki/Home/)
- [OpenCV Documentation](https://docs.opencv.org/)
- [YOLO Documentation](https://pjreddie.com/darknet/yolo/)
- [HC-SR04 Ultrasonic Sensor Guide](https://tutorials-raspberrypi.com/raspberry-pi-ultrasonic-sensor-hc-sr04/)

---

**Chúc vui! 🚀**
