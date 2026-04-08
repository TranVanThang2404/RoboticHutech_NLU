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
# "raspi"   → dùng RealMotorUART (pyserial UART) + RealUltrasonicArray / MockUltrasonicArray
HARDWARE_MODE = "raspi"

# True  → dùng cảm biến siêu âm thật (SEN0311 qua UART)
# False → dùng sensor giả (test camera mà chưa nối sensor / chưa bật UART3)
SENSOR_ENABLED = False

# True  → không gọi cv2.imshow / cv2.waitKey (chạy không cần màn hình / SSH)
# False → hiển thị cửa sổ debug camera (cần display)
HEADLESS = True

# True  → giao diện tkinter (app_gui.py), không cần mạng / Flask
# False → giao diện web Flask + HTML (cần mạng, điện thoại quét QR)
USE_GUI = True

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
CAMERA_WIDTH  = 320       # độ phân giải capture (320 để RPi nhanh hơn, 640 nếu laptop mạnh)
CAMERA_HEIGHT = 240
DETECT_EVERY_N = 3        # chạy detector mỗi N frame (1=mọi frame, 3=nhanh 3x, giữ lại bbox cũ)

# ============================================================
#  SERVER (Flask)
# ============================================================
SERVER_PORT = 5000

# ============================================================
#  PERSON DETECTION
# ============================================================
# "onnx"  → ONNX Runtime (nhẹ ~15MB, không cần torch — ưu tiên RPi)
# "yolo"  → ultralytics YOLO (cần torch ~2GB — nặng trên RPi)
# "hog"   → OpenCV HOG (fallback, kém chính xác nhất)
# Thứ tự fallback tự động: onnx → yolo → hog (hoặc yolo → onnx → hog)
DETECTOR_BACKEND = "onnx"
YOLO_CONFIDENCE  = 0.40     # Ngưỡng confidence tối thiểu để nhận diện người
DETECTOR_INPUT_SIZE = 640   # model ONNX hiện tại fixed 640; RPi có thể override thấp hơn nếu export lại

# Multi-capture trên Raspberry Pi: tắt face encoding để tránh tụt FPS mạnh.
MC_ENABLE_FACE_ENCODING = True
MC_SNAPSHOT_JPEG_QUALITY = 85

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
MIN_SPEED   = -60         # Giới hạn tốc độ tối thiểu (âm = lùi)

# ============================================================
#  PID — STEERING (lái trái/phải)
# ============================================================
# Error = (cx_người - cx_frame) / cx_frame  ∈ [-1, +1]
# Output = speed differential (đơn vị motor 0–100)
#   Tăng STEER_KP → phản ứng nhanh hơn, dễ dao động nếu quá cao
#   Tăng STEER_KI → xử lý lệch hệ thống (camera lắp lệch tâm)
#   Tăng STEER_KD → giảm vọt lố khi người chuyển hướng đột ngột
STEER_KP               = 50.0   # gain tỉ lệ (hạ từ 80 → 50 cho RPi chậm)
STEER_KI               =  3.0   # gain tích phân (hạ từ 5 → 3, tránh windup trên RPi)
STEER_KD               = 12.0   # gain vi phân (hạ từ 20 → 12, tránh dao động)
STEER_INTEGRAL_LIMIT   = 15.0   # anti-windup: max |integral contribution| (speed units)
STEER_OUTPUT_LIMIT     = 70.0   # clamp đầu ra: max speed differential (0–100)
STEER_DERIV_ALPHA      =  0.15  # hệ số lọc low-pass đạo hàm (0.1=mượt – 1.0=raw)

# Giảm quay tại chỗ trong lúc FOLLOWING.
# Nếu base speed quá nhỏ thì chỉ cho đánh lái nhẹ; muốn quay tìm người dùng SEARCH_SPIN riêng.
STEER_LOW_SPEED_CUTOFF = 0      # generic/laptop: tắt chế độ hạn chế quay tại chỗ
STEER_LOW_SPEED_ERR    = 0.0

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
BBOX_HOLD_ZONE         =  0.000 # generic/laptop: không hold, raspi sẽ override

SPEED_KP               =  60.0  # gain tỉ lệ (hạ từ 100 → 60, bớt giật tiến/lùi)
SPEED_KI               =   2.0  # gain tích phân (hạ từ 5 → 2, tránh tích lũy sai)
SPEED_KD               =   8.0  # gain vi phân (hạ từ 15 → 8)
SPEED_INTEGRAL_LIMIT   =  15.0  # anti-windup (speed units)
SPEED_OUTPUT_LIMIT     =  30.0  # max |delta speed| cộng vào BASE_SPEED (hạ từ 40)
SPEED_DERIV_ALPHA      =   0.10  # lọc mạnh hơn (0.10 = rất mượt, bớt noise bbox)

# Backward-compat alias (không xóa để không phá code cũ nếu có)
KP = STEER_KP / 100.0   # KP cũ ≈ steer_output/base ≈ 80/100 = 0.80

# ============================================================
#  TIMING
# ============================================================
TARGET_LOST_TIMEOUT  = 2.0   # Giây không thấy người → chuyển TARGET_LOST
MOTOR_SEND_INTERVAL  = 0.05  # Giây giữa hai lần gửi lệnh (~20 Hz)

# Giảm số lệnh UART không cần thiết xuống STM32.
# Nếu chênh lệch lệnh giữa 2 lần gửi quá nhỏ thì giữ lệnh cũ để bánh xe đỡ giật.
MOTOR_CMD_DEADBAND   = 0     # generic/laptop: không deadband
MOTOR_MAX_DELTA_PER_SEND = 100  # generic/laptop: gần như không giới hạn ramp
CAMERA_STALL_TIMEOUT = 1.0      # generic/laptop: watchdog lỏng
CAMERA_STALL_MAX_CONSECUTIVE = 2  # chỉ fail-safe khi bị chậm liên tiếp nhiều vòng
CAMERA_READ_FAIL_LIMIT = 1      # generic/laptop: lỗi là dừng luôn như hiện tại
MOTOR_REVERSE_BRAKE_THRESHOLD = 0  # generic/laptop: không chèn pha hãm trước khi đảo chiều

# ============================================================
#  SEARCH SPIN — Xoay tìm người khi TARGET_LOST
# ============================================================
SEARCH_SPIN_SPEED    = 45    # Tốc độ xoay tại chỗ khi tìm người (0–100)
SEARCH_SPIN_DURATION = 6.0   # Xoay tối đa bao lâu (giây) rồi dừng hẳn
SEARCH_SPIN_DIR      = 1     # 1 = xoay phải (CW), -1 = xoay trái (CCW)

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
#  RASPI OVERRIDES
# ============================================================
# Chỉ áp dụng các tinh chỉnh "xe thật" khi chạy trên Raspberry Pi.
if HARDWARE_MODE == "raspi":
    DETECT_EVERY_N = 4
    DETECTOR_INPUT_SIZE = 320
    MC_ENABLE_FACE_ENCODING = False
    MC_SNAPSHOT_JPEG_QUALITY = 60

    BASE_SPEED = 0
    BBOX_HOLD_ZONE = 0.015
    STEERING_DEAD_ZONE = 0.12
    STEER_KP = 38.0
    STEER_KI = 2.0
    STEER_KD = 8.0
    STEER_OUTPUT_LIMIT = 55.0
    STEER_DERIV_ALPHA = 0.10
    STEER_LOW_SPEED_CUTOFF = 8
    STEER_LOW_SPEED_ERR = 0.20

    MOTOR_SEND_INTERVAL = 0.08
    MOTOR_CMD_DEADBAND = 6
    MOTOR_MAX_DELTA_PER_SEND = 12
    # ONNX trên Raspberry Pi thường dao động ~0.3-0.6s/frame.
    # Nếu để watchdog quá thấp sẽ báo giả "camera loop stalled" dù camera vẫn hoạt động.
    CAMERA_STALL_TIMEOUT = 0.80
    CAMERA_STALL_MAX_CONSECUTIVE = 3
    CAMERA_READ_FAIL_LIMIT = 3
    MOTOR_REVERSE_BRAKE_THRESHOLD = 10


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
