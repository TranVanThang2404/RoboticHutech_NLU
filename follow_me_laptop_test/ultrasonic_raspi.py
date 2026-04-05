"""
ultrasonic_raspi.py — Real HC-SR04 ultrasonic sensor array cho Raspberry Pi.

Sơ đồ lắp đặt:
                    [TRÁI]   [GIỮA]   [PHẢI]
                       \\       |       /
                        \\      |      /
                     ← bên trái  bên phải →
                            [XE]

Kết nối HC-SR04 (mỗi cảm biến cần 4 dây: VCC 5V, GND, TRIG, ECHO):
  QUAN TRỌNG: HC-SR04 Echo xuất 5V — phải qua voltage divider hoặc level shifter
              trước khi nối vào chân GPIO RPi (chịu tối đa 3.3V)!

  Voltage divider đơn giản cho ECHO:
    Echo → R1(1kΩ) → GPIO → R2(2kΩ) → GND
    (ra ~3.33V = an toàn cho RPi)

Cổng GPIO mặc định (BCM numbering):
  Cảm biến TRÁI  : TRIG=17, ECHO=27
  Cảm biến GIỮA  : TRIG=23, ECHO=24
  Cảm biến PHẢI  : TRIG= 5, ECHO= 6

Cài thư viện:
  pip install RPi.GPIO

Lưu ý:
  - Chạy script với sudo hoặc thêm user vào group gpio:
      sudo usermod -aG gpio $USER && reboot
  - Mỗi HC-SR04 cần timeout nhỏ để tránh treo khi echo không về
    → đã tích hợp timeout 0.03s per measurement
"""

import time
import config
from ultrasonic_mock import ObstacleReading   # tái dùng dataclass

try:
    import RPi.GPIO as GPIO
    _GPIO_AVAILABLE = True
except ImportError:
    _GPIO_AVAILABLE = False
    print("[ULTRASONIC] CẢNH BÁO: RPi.GPIO chưa cài hoặc không chạy trên Raspberry Pi")


# ============================================================
#  Cấu hình chân GPIO (BCM numbering)
# ============================================================
SENSORS_PINS = {
    "left":   {"trig": 17, "echo": 27},
    "center": {"trig": 23, "echo": 24},
    "right":  {"trig":  5, "echo":  6},
}

_MEASURE_TIMEOUT = 0.03   # giây — timeout mỗi lần đo (tránh treo khi không có echo)
_PULSE_US        = 0.00001  # 10µs pulse kích hoạt TRIG


class RealUltrasonicArray:
    """
    Đọc 3 cảm biến HC-SR04 qua GPIO.

    API giống hệt MockUltrasonicArray để drop-in replace.
    """

    def __init__(self):
        if not _GPIO_AVAILABLE:
            raise RuntimeError(
                "[ULTRASONIC] RPi.GPIO không khả dụng. "
                "Cài bằng: pip install RPi.GPIO"
            )
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for name, pins in SENSORS_PINS.items():
            GPIO.setup(pins["trig"], GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(pins["echo"], GPIO.IN)

        print(
            f"[ULTRASONIC] RealUltrasonicArray (3 sensors) initialized  "
            f"| stop={config.OBSTACLE_STOP_CM:.0f}cm "
            f"slow={config.OBSTACLE_SLOW_CM:.0f}cm "
            f"side={config.SIDE_SAFE_CM:.0f}cm  "
            f"GPIO(BCM): L={SENSORS_PINS['left']}  "
            f"C={SENSORS_PINS['center']}  "
            f"R={SENSORS_PINS['right']}"
        )

    # ------------------------------------------------------------------ #
    #  Public API (giống MockUltrasonicArray)
    # ------------------------------------------------------------------ #

    def read(self) -> ObstacleReading:
        """Đọc cả 3 cảm biến và trả về ObstacleReading."""
        return ObstacleReading(
            left_cm=self._measure_cm("left"),
            center_cm=self._measure_cm("center"),
            right_cm=self._measure_cm("right"),
        )

    def is_obstacle_detected(self) -> bool:
        """True nếu cảm biến giữa kích hoạt stop."""
        return self.read().center_stop

    def get_distance_cm(self) -> float:
        """Chỉ trả khoảng cách cảm biến giữa (cm)."""
        return self._measure_cm("center")

    def cleanup(self):
        """Giải phóng GPIO. Gọi khi thoát chương trình."""
        GPIO.cleanup()
        print("[ULTRASONIC] GPIO cleanup done")

    # ------------------------------------------------------------------ #
    #  Private
    # ------------------------------------------------------------------ #

    def _measure_cm(self, sensor: str) -> float:
        """
        Đo khoảng cách từ 1 cảm biến HC-SR04.

        Returns:
            float: khoảng cách (cm). Trả config.DEFAULT_DISTANCE_CM nếu timeout.
        """
        trig = SENSORS_PINS[sensor]["trig"]
        echo = SENSORS_PINS[sensor]["echo"]

        # Gửi xung TRIG 10µs
        GPIO.output(trig, GPIO.HIGH)
        time.sleep(_PULSE_US)
        GPIO.output(trig, GPIO.LOW)

        deadline = time.time() + _MEASURE_TIMEOUT

        # Chờ echo lên HIGH
        start = time.time()
        while GPIO.input(echo) == GPIO.LOW:
            start = time.time()
            if start > deadline:
                return config.DEFAULT_DISTANCE_CM   # timeout — không có vật cản

        # Chờ echo xuống LOW
        end = time.time()
        while GPIO.input(echo) == GPIO.HIGH:
            end = time.time()
            if end > deadline:
                return config.DEFAULT_DISTANCE_CM   # timeout — vật cản quá xa

        # distance = (time * speed_of_sound) / 2
        # speed_of_sound ≈ 34300 cm/s
        dist_cm = (end - start) * 17150.0
        return max(0.0, dist_cm)
