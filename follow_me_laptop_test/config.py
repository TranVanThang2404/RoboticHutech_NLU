"""
config.py — Centralized configuration for Follow Me Laptop Test MVP.

Chỉnh sửa file này để thay đổi:
  - Camera index
  - Server port
  - Motor speed parameters
  - Person detection / Re-ID thresholds
"""

# ============================================================
#  DEPLOYMENT MODE
# ============================================================
# "raspi"   → dùng RealMotorUART (pyserial UART) + RealUltrasonicArray / MockUltrasonicArray
HARDWARE_MODE = "raspi"

# True  → dùng cảm biến siêu âm thật (SEN0311 qua UART)
# False → dùng sensor giả (test camera mà chưa nối sensor / chưa bật UART3)
SENSOR_ENABLED = True

# True  → không gọi cv2.imshow / cv2.waitKey (chạy không cần màn hình / SSH)
# False → hiển thị cửa sổ debug camera (cần display)
HEADLESS = True

# GUI tkinter trực tiếp trên màn hình.
USE_GUI = True

# ============================================================
#  CHECKLIST KHI DEPLOY LÊN RASPBERRY PI
# ============================================================
#  1. HEADLESS      = True         ← True nếu chạy qua SSH / không có màn hình
#  2. CAMERA_INDEX  = 0            ← USB webcam giữ 0; CSI Pi Camera = cũng thử 0
#     Nếu CSI camera không nhận:
#       sudo modprobe bcm2835-v4l2  (load V4L2 driver cho Pi Camera)
#       rồi thử lại với CAMERA_INDEX = 0
#  3. UART port trong motor_raspi.py:
#       /dev/ttyAMA0  = UART phần cứng (cần tắt login shell trong raspi-config)
#       /dev/serial0  = alias tự động của RPi 4/5
#       /dev/ttyUSB0  = USB-Serial adapter
#  4. GPIO pins trong ultrasonic_raspi.py → SENSORS_PINS
#       Mặc định: LEFT TRIG=17 ECHO=27 | CENTER TRIG=23 ECHO=24 | RIGHT TRIG=5 ECHO=6
#       Đổi nếu nối dây khác.
#  5. pip install -r requirements.txt   (thêm RPi.GPIO + pyserial)
#  6. Thêm user vào group gpio nếu cần:
#       sudo usermod -aG gpio $USER && sudo reboot
# ============================================================

# ============================================================
#  CAMERA
# ============================================================
CAMERA_INDEX = 0          # 0 = webcam tích hợp | 1 = USB camera đầu tiên
CAMERA_WIDTH  = 720
CAMERA_HEIGHT = 480
DETECT_EVERY_N = 1        # 3→2: detect thường xuyên hơn, bớt dùng bbox cũ

#  PERSON DETECTION
# ============================================================
# "onnx"  → ONNX Runtime (nhẹ ~15MB, không cần torch — ưu tiên RPi)
# "yolo"  → ultralytics YOLO (cần torch ~2GB — nặng trên RPi)
# "hog"   → OpenCV HOG (fallback, kém chính xác nhất)
# Thứ tự fallback tự động: onnx → yolo → hog (hoặc yolo → onnx → hog)
DETECTOR_BACKEND = "onnx"
YOLO_CONFIDENCE  = 0.40     # Ngưỡng confidence tối thiểu để nhận diện người
DETECTOR_INPUT_SIZE = 320   # 320 cho RPi (nhẹ hơn 640)

# Multi-capture: face encoding giúp Re-ID chính xác hơn.
MC_ENABLE_FACE_ENCODING = True
MC_SNAPSHOT_JPEG_QUALITY = 60

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
SIMILARITY_THRESHOLD = 0.45

# ---- Multi-template gallery ----
# Lưu N snapshot descriptor tại các thời điểm khác nhau để thích nghi
# khi người mặc thêm/cởi áo khoác, thay đổi góc nhìn, ánh sáng.
# Similarity cuối = max(sim với từng template trong gallery).
GALLERY_SIZE            = 6     # số snapshot tối đa (tăng = bộ nhớ nhiều hơn, thích nghi tốt hơn)
GALLERY_UPDATE_INTERVAL = 4.0   # giây tối thiểu giữa 2 lần thêm snapshot mới
GALLERY_MIN_SIM         = 0.58  # chỉ thêm snapshot khi similarity ≥ ngưỡng này
                                 # (tránh lưu frame nhiễu hoặc người khác vào gallery)
TRACK_POS_BONUS_MAX     = 0.08  # bonus vị trí nhỏ để bám mượt nhưng không lấn át nhận diện
TRACK_AMBIGUOUS_MARGIN  = 0.00  # đứng gần màn hình dễ đổi pose nhanh; không bỏ frame vì mơ hồ nhẹ

# Bbox area / frame area:
#   > BBOX_TOO_CLOSE_RATIO → người quá gần → giảm tốc
#   < BBOX_TOO_FAR_RATIO   → người quá xa  → tăng tốc
BBOX_TOO_CLOSE_RATIO = 0.55   # tăng lên để không bị coi là "quá gần" khi test trong phòng
BBOX_TOO_FAR_RATIO   = 0.03

# Dead zone: nếu |error| < ngưỡng này thì coi là đi thẳng (lọc nhiễu detection)
STEERING_DEAD_ZONE = 0.10       # 0.14→0.10: giảm vùng chết, EMA đã lọc jitter
STEER_STRAIGHT_LOCK_ERR = 0.06  # nếu mục tiêu gần tâm hơn mức này thì ép đi thẳng
STEER_MAX_DIFF_RATIO = 0.75     # buộc 2 bánh cùng tiến, cua vòng cung thay vì xoay
STEER_APPROACH_SCALE = 0.60     # khi còn đang tiến tới thì giảm độ bẻ lái để ưu tiên đi thẳng
STEER_CENTER_PRIORITY_ERR = 0.15  # nếu lệch tâm chưa quá lớn thì vẫn ưu tiên 2 bánh gần bằng nhau
WHEEL_TRIM_LEFT = 1.45          # bánh trái yếu hơn → bù 45%
WHEEL_TRIM_RIGHT = 1.00         # giữ nguyên bánh phải
WHEEL_FORWARD_BOOST_LEFT = 0    # bỏ boost cố định, ưu tiên bù theo tỉ lệ 25%
WHEEL_FORWARD_BOOST_RIGHT = 0   # bánh phải giữ nguyên
STEER_RIGHT_LEFT_BOOST = 0      # tắt bù theo hướng rẽ để tránh làm lệch thêm
STEER_LEFT_RIGHT_REDUCE = 0     # tắt giảm bánh phải
MOTOR_SWAP_LEFT_RIGHT = True    # phần cứng thực tế đang phản ứng như bị đảo trái/phải

# ============================================================
#  MOTOR CONTROL
# ============================================================
BASE_SPEED  = 0           # PID speed controller tự tính, không cần base cố định
MAX_SPEED   = 100         # Giới hạn tốc độ tối đa
MIN_SPEED   = -60         # Giới hạn tốc độ tối thiểu (âm = lùi)
ONLY_FORWARD_MODE = True  # True -> chặn mọi lệnh lùi, xe chỉ được đi tới hoặc dừng

# ============================================================
#  PID — STEERING (lái trái/phải)
# ============================================================
# Error = (cx_người - cx_frame) / cx_frame  ∈ [-1, +1]
# Output = speed differential (đơn vị motor 0–100)
#   Tăng STEER_KP → phản ứng nhanh hơn, dễ dao động nếu quá cao
#   Tăng STEER_KI → xử lý lệch hệ thống (camera lắp lệch tâm)
#   Tăng STEER_KD → giảm vọt lố khi người chuyển hướng đột ngột
STEER_KP               = 22.0   # gain tỉ lệ — giảm dao động
STEER_KI               =  1.5   # gain tích phân — giảm tích lũy sai
STEER_KD               =  6.0   # gain vi phân — tăng độ dập dao động
STEER_INTEGRAL_LIMIT   = 15.0   # anti-windup: max |integral contribution| (speed units)
STEER_OUTPUT_LIMIT     = 40.0   # clamp đầu ra: max speed differential
STEER_DERIV_ALPHA      =  0.10  # hệ số lọc low-pass đạo hàm (0.1=mượt – 1.0=raw)

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
BBOX_TARGET_RATIO      =  0.42  # PID ước lượng là chính; sensor trước chỉ chặn ở mốc 15 cm
BBOX_HOLD_ZONE         =  0.03  # vùng giữ nhỏ để phản ứng nhanh hơn

SPEED_KP               =  60.0  # gain tỉ lệ (hạ từ 100 → 60, bớt giật tiến/lùi)
SPEED_KI               =   2.0  # gain tích phân (hạ từ 5 → 2, tránh tích lũy sai)
SPEED_KD               =   8.0  # gain vi phân (hạ từ 15 → 8)
SPEED_INTEGRAL_LIMIT   =  15.0  # anti-windup (speed units)
SPEED_OUTPUT_LIMIT     =  18.0  # trần tốc độ follow
SPEED_DERIV_ALPHA      =   0.10  # lọc mạnh (0.10 = rất mượt, bớt noise bbox)
FOLLOW_MIN_SPEED       =  24     # base cao hơn → max_diff=18 → quẹo rõ mà vẫn cua cung
FOLLOW_MIN_ERR         =  0.02   # thiếu nhẹ khoảng cách là đã bắt đầu bò tới
FOLLOW_FORCE_APPROACH_RATIO = 0.50  # nếu bbox vẫn dưới mức này thì cho phép tiến dựa trên sensor
MOTOR_MIN_EFFECTIVE_SPEED = 12   # không ép bánh yếu lên cao, giữ chênh lệch quẹo
MOTOR_LOG_MIN_ABS = 8            # in log cả các lệnh nhỏ để dễ debug
MOTOR_START_BOOST = 30           # cú hích khởi động để thắng ma sát

# Backward-compat alias (không xóa để không phá code cũ nếu có)
KP = STEER_KP / 100.0   # backward-compat alias

# ============================================================
#  TIMING
# ============================================================
TARGET_LOST_TIMEOUT  = 3.5   # Giây không thấy người → chuyển TARGET_LOST
MOTOR_SEND_INTERVAL  = 0.10  # ~10 Hz, bớt spam STM32

# Giảm số lệnh UART không cần thiết xuống STM32.
# Nếu chênh lệch lệnh giữa 2 lần gửi quá nhỏ thì giữ lệnh cũ để bánh xe đỡ giật.
MOTOR_CMD_DEADBAND   = 5        # 8→5: lọc giật nhẹ, không nuốt lệnh nhỏ
MOTOR_MAX_DELTA_PER_SEND = 22   # 15→22: tăng tốc nhanh hơn, vẫn mượt
# ONNX trên Raspberry Pi thường dao động ~0.3-0.6s/frame.
# Nếu để watchdog quá thấp sẽ báo giả "camera loop stalled" dù camera vẫn hoạt động.
CAMERA_STALL_TIMEOUT = 1.20     # watchdog cho ONNX trên RPi
CAMERA_STALL_MAX_CONSECUTIVE = 3  # fail-safe khi bị chậm liên tiếp
CAMERA_READ_FAIL_LIMIT = 3      # cho phép retry vài lần trước khi dừng
MOTOR_REVERSE_BRAKE_THRESHOLD = 10  # chèn pha hãm trước khi đảo chiều

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
OBSTACLE_STOP_CM    = 15.0   # cm — dừng ở khoảng cách mục tiêu an toàn
OBSTACLE_SLOW_CM    = 25.0   # cm — giảm tốc trước khi vào vùng 15 cm

# --- Cảm biến TRÁI / PHẢI (hai bên sườn) ---
# Khi một bên < SIDE_SAFE_CM → lệch lái sang bên kia để thoát
SIDE_SAFE_CM        = 15.0   # cm — bớt quẹt cạnh khi đứng gần vật xung quanh

# Mức lệch lái cưỡng bức khi một bên bị chặn (0.0–1.0 normalized error)
#   0.40 = lệch vừa (tránh tường nhẹ)
#   0.70 = lệch mạnh (hẻm hẹp, tường hai bên)
OBSTACLE_SIDE_BIAS  = 0.40

# Khoảng cách mặc định khi mock / không có vật cản
DEFAULT_DISTANCE_CM = 150.0

# Backward-compat alias
SAFE_DISTANCE_CM    = OBSTACLE_STOP_CM
