# ===== RoboticHutech - Robot Configuration =====
# Cấu hình chung cho xe tự động quét người

# ===== GPIO PINS =====
# Motor control pins (Motor Driver)
MOTOR_LEFT_PIN1 = 23
MOTOR_LEFT_PIN2 = 24
MOTOR_LEFT_PWM = 12  # BCM 12 (PWM)

MOTOR_RIGHT_PIN1 = 27
MOTOR_RIGHT_PIN2 = 17
MOTOR_RIGHT_PWM = 13  # BCM 13 (PWM)

# Ultrasonic Sensor 1 (TRÁI)
ULTRASONIC_LEFT_TRIG = 17
ULTRASONIC_LEFT_ECHO = 32

# Ultrasonic Sensor 2 (GIỮA)
ULTRASONIC_CENTER_TRIG = 19
ULTRASONIC_CENTER_ECHO = 26

# Ultrasonic Sensor 3 (PHẢI)
ULTRASONIC_RIGHT_TRIG = 20
ULTRASONIC_RIGHT_ECHO = 21

# ===== MOTOR PARAMETERS =====
PWM_FREQUENCY = 100  # Hz
MAX_SPEED = 100  # Tốc độ tối đa (0-100%)
MIN_SPEED = 30   # Tốc độ tối thiểu
NORMAL_SPEED = 60  # Tốc độ thường xuyên
TURN_SPEED = 50    # Tốc độ khi quay

# ===== CAMERA SETTINGS =====
CAMERA_INDEX = 0  # USB camera index
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
CAMERA_FPS = 30
CONFIDENCE_THRESHOLD = 0.5  # Ngưỡng confidence để detect người

# ===== DISTANCE SETTINGS (cm) =====
SAFE_DISTANCE = 30  # Khoảng cách an toàn (cm)
FOLLOW_DISTANCE = 60  # Khoảng cách để bắt đầu theo (cm)
STOP_DISTANCE = 20  # Khoảng cách dừng lại (cm)

# ===== DETECTION PARAMETERS =====
PERSON_DETECTION_MODEL = "yolov3-tiny"  # hoặc "mobilenet"
PERSON_CLASS_ID = 0  # Class ID cho "person" trong YOLO
MIN_DETECTION_WIDTH = 50
MIN_DETECTION_HEIGHT = 50

# ===== CONTROL PARAMETERS =====
CENTER_TOLERANCE = 50  # Độ chênh lệch cho phép khi canh giữa
MAX_TURN_ANGLE = 30  # Độ quay tối đa

# ===== LOGGING =====
DEBUG_MODE = True
LOG_FILE = "robot_log.txt"
