"""
config.py — Centralized configuration for Follow Me Laptop Test MVP.

Chỉnh sửa file này để thay đổi:
  - Camera index
  - Server port
  - Motor speed parameters
  - Person detection / Re-ID thresholds
"""

import socket

# ============================================================
#  DEPLOYMENT MODE
# ============================================================
# "laptop"  → dùng FakeMotorUART + MockUltrasonicArray (test trên laptop)
# "raspi"   → dùng RealMotorUART (pyserial UART) + RealUltrasonicArray (RPi.GPIO)
HARDWARE_MODE = "laptop"

# True  → không gọi cv2.imshow / cv2.waitKey (chạy không cần màn hình / SSH)
# False → hiển thị cửa sổ debug camera (cần display)
HEADLESS = False

# ============================================================
#  CHECKLIST KHI DEPLOY LÊN RASPBERRY PI
# ============================================================
#  1. HARDWARE_MODE = "raspi"      ← đổi "laptop" → "raspi"
#  2. HEADLESS      = True         ← True nếu chạy qua SSH / không có màn hình
#  3. CAMERA_INDEX  = 0            ← USB webcam giữ 0; CSI Pi Camera = cũng thử 0
#     Nếu CSI camera không nhận:
#       sudo modprobe bcm2835-v4l2  (load V4L2 driver cho Pi Camera)
#       rồi thử lại với CAMERA_INDEX = 0
#  4. UART port trong motor_raspi.py:
#       /dev/ttyAMA0  = UART phần cứng (cần tắt login shell trong raspi-config)
#       /dev/serial0  = alias tự động của RPi 4/5
#       /dev/ttyUSB0  = USB-Serial adapter
#  5. GPIO pins trong ultrasonic_raspi.py → SENSORS_PINS
#       Mặc định: LEFT TRIG=17 ECHO=27 | CENTER TRIG=23 ECHO=24 | RIGHT TRIG=5 ECHO=6
#       Đổi nếu nối dây khác.
#  6. pip install -r requirements.txt   (thêm RPi.GPIO + pyserial)
#  7. Thêm user vào group gpio nếu cần:
#       sudo usermod -aG gpio $USER && sudo reboot
# ============================================================

# ============================================================
#  CAMERA
# ============================================================
CAMERA_INDEX = 0          # 0 = webcam tích hợp | 1 = USB camera đầu tiên

# ============================================================
#  SERVER (Flask)
# ============================================================
SERVER_PORT = 5000

# ============================================================
#  PERSON DETECTION
# ============================================================
DETECTOR_BACKEND = "yolo"   # "yolo" (YOLOv8n, cần ultralytics) hoặc "hog" (OpenCV built-in, fallback)
YOLO_CONFIDENCE  = 0.40     # Ngưỡng confidence tối thiểu để nhận diện người

# ============================================================
#  FACE VERIFICATION (tùy chọn — cần cài face_recognition)
# ============================================================
# Cài đặt: pip install face_recognition
# Khoảng cách Euclidean tối đa giữa 2 face encoding:
#   Nhỏ hơn (0.45) = khó tit hơn, ít nhầm hơn, có thể bỏ qua chính chủ
#   Lớn hơn (0.60) = dễ tính hơn, nhận tốt khi góc nghịng, có thể nhầm
FACE_TOLERANCE   = 0.50     # Mặc định face_recognition là 0.60

# ============================================================
#  RE-ID / PERSON TRACKING
# ============================================================
# Cosine similarity tối thiểu để chấp nhận là đúng người đã đăng ký.
# Tăng lên nếu bị nhầm người, giảm xuống nếu bị mất theo quá sớm.
SIMILARITY_THRESHOLD = 0.40

# ---- Multi-template gallery ----
# Lưu N snapshot descriptor tại các thời điểm khác nhau để thích nghi
# khi người mặc thêm/cởi áo khoác, thay đổi góc nhìn, ánh sáng.
# Similarity cuối = max(sim với từng template trong gallery).
GALLERY_SIZE            = 6     # số snapshot tối đa (tăng = bộ nhớ nhiều hơn, thích nghi tốt hơn)
GALLERY_UPDATE_INTERVAL = 4.0   # giây tối thiểu giữa 2 lần thêm snapshot mới
GALLERY_MIN_SIM         = 0.55  # chỉ thêm snapshot khi similarity ≥ ngưỡng này
                                 # (tránh lưu frame nhiễu hoặc người khác vào gallery)

# Bbox area / frame area:
#   > BBOX_TOO_CLOSE_RATIO → người quá gần → giảm tốc
#   < BBOX_TOO_FAR_RATIO   → người quá xa  → tăng tốc
BBOX_TOO_CLOSE_RATIO = 0.55   # tăng lên để không bị coi là "quá gần" khi test trong phòng
BBOX_TOO_FAR_RATIO   = 0.03

# Dead zone: nếu |error| < ngưỡng này thì coi là đi thẳng (lọc nhiễu detection)
# 0.08 ≈ 8% chiều rộng frame — đủ để lọc flickering 1-2 pixel
STEERING_DEAD_ZONE = 0.08

# ============================================================
#  MOTOR CONTROL
# ============================================================
BASE_SPEED  = 60          # Tốc độ nền khi đi thẳng (0–100)
MAX_SPEED   = 100         # Giới hạn tốc độ tối đa
MIN_SPEED   = 0           # Giới hạn tốc độ tối thiểu

# ============================================================
#  PID — STEERING (lái trái/phải)
# ============================================================
# Error = (cx_người - cx_frame) / cx_frame  ∈ [-1, +1]
# Output = speed differential (đơn vị motor 0–100)
#   Tăng STEER_KP → phản ứng nhanh hơn, dễ dao động nếu quá cao
#   Tăng STEER_KI → xử lý lệch hệ thống (camera lắp lệch tâm)
#   Tăng STEER_KD → giảm vọt lố khi người chuyển hướng đột ngột
STEER_KP               = 80.0   # gain tỉ lệ
STEER_KI               =  5.0   # gain tích phân (nhỏ, tránh windup)
STEER_KD               = 20.0   # gain vi phân (lọc dao động)
STEER_INTEGRAL_LIMIT   = 20.0   # anti-windup: max |integral contribution| (speed units)
STEER_OUTPUT_LIMIT     = 90.0   # clamp đầu ra: max speed differential (0–100)
STEER_DERIV_ALPHA      =  0.20  # hệ số lọc low-pass đạo hàm (0.1=mượt – 1.0=raw)

# ============================================================
#  PID — SPEED (duy trì khoảng cách follow)
# ============================================================
# Error = BBOX_TARGET_RATIO - bbox_area_ratio
#   > 0: người quá xa  → tăng BASE_SPEED
#   < 0: người quá gần → giảm BASE_SPEED (hoặc lùi nếu MIN_SPEED < 0)
#
# BBOX_TARGET_RATIO: tỷ lệ bbox/frame tại khoảng cách follow lý tưởng
#   0.10 ≈ người ở ~1.5–2 m  (camera laptop góc rộng)
#   0.15 ≈ người ở ~1–1.5 m
BBOX_TARGET_RATIO      =  0.12  # tỷ lệ bbox/frame mục tiêu

SPEED_KP               = 100.0  # gain tỉ lệ (error 0.10 → +10 speed units)
SPEED_KI               =   5.0  # gain tích phân
SPEED_KD               =  15.0  # gain vi phân (giảm vọt lố khi người dừng đột ngột)
SPEED_INTEGRAL_LIMIT   =  25.0  # anti-windup (speed units)
SPEED_OUTPUT_LIMIT     =  40.0  # max |delta speed| cộng vào BASE_SPEED
SPEED_DERIV_ALPHA      =   0.15  # lọc mạnh hơn steering (bbox noisy hơn)

# Backward-compat alias (không xóa để không phá code cũ nếu có)
KP = STEER_KP / 100.0   # KP cũ ≈ steer_output/base ≈ 80/100 = 0.80

# ============================================================
#  TIMING
# ============================================================
TARGET_LOST_TIMEOUT  = 2.0   # Giây không thấy người → chuyển TARGET_LOST
MOTOR_SEND_INTERVAL  = 0.05  # Giây giữa hai lần gửi lệnh (~20 Hz)

# ============================================================
#  ULTRASONIC — 3 cảm biến (Trái / Giữa / Phải)
# ============================================================
# --- Cảm biến GIỮA (phía trước) ---
# Hai ngưỡng để phản ứng tuyến tính:
#   OBSTACLE_STOP_CM : xe DỪNG hoàn toàn (vùng nguy hiểm tức thời)
#   OBSTACLE_SLOW_CM : xe BẮT ĐẦU GIẢM TỐC (vùng cảnh báo sớm)
# Tốc độ scale tuyến tính từ 100% (tại SLOW) → 30% (sát STOP)
OBSTACLE_STOP_CM    = 20.0   # cm — dừng cứng (người đi ngang, tường gần)
OBSTACLE_SLOW_CM    = 60.0   # cm — bắt đầu giảm tốc

# --- Cảm biến TRÁI / PHẢI (hai bên sườn) ---
# Khi một bên < SIDE_SAFE_CM → lệch lái sang bên kia để thoát
SIDE_SAFE_CM        = 25.0   # cm — ngưỡng kích hoạt tránh tường/vật cản bên

# Mức lệch lái cưỡng bức khi một bên bị chặn (0.0–1.0 normalized error)
#   0.40 = lệch vừa (tránh tường nhẹ)
#   0.70 = lệch mạnh (hẻm hẹp, tường hai bên)
OBSTACLE_SIDE_BIAS  = 0.40

# Khoảng cách mặc định khi mock / không có vật cản
DEFAULT_DISTANCE_CM = 150.0

# Backward-compat alias
SAFE_DISTANCE_CM    = OBSTACLE_STOP_CM


# ============================================================
#  HELPER
# ============================================================
def get_local_ip() -> str:
    """Trả về địa chỉ IP LAN của máy tính hiện tại."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"
