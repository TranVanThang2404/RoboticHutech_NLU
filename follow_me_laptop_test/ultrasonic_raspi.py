"""
ultrasonic_raspi.py  DFRobot SEN0311 (A02YYUW) ultrasonic sensor cho Raspberry Pi.

Cảm biến: DFRobot SEN0311 / A02YYUW
  Giao tiếp : UART 9600 baud (không phải GPIO TRIG/ECHO như HC-SR04)
  Đo được   : 3  450 cm (30  4500 mm)
  Gói tin   : 4 byte  [0xFF, H, L, SUM]
                distance_mm = H * 256 + L
                SUM = (0xFF + H + L) & 0xFF

Sơ đồ lắp đặt xe (nhìn từ trên):
                [TRÁI]   [GIỮA]   [PHẢI]
                   \       |       /
                    \      |      /
                 <- bên trái   bên phải ->
                          [XE]

  PHASE 1 (hiện tại): Chỉ cảm biến GIỮA
  PHASE 2:            Thêm TRÁI + PHẢI (xem hướng dẫn bên dưới)

--------------------------------------------------------------
  ĐẤU DÂY  PHASE 1 (cảm biến GIỮA)
--------------------------------------------------------------
  SEN0311   |  RPi 4B pin   |  Ghi chú
  ----------+---------------+--------------------------------
  VCC (đỏ)  |  Pin 2 (5V)   |  Nguồn 5V
  GND (đen) |  Pin 6 (GND)  |  Mass chung
  TX  (xanh)|  Pin 29       |  GPIO5 = UART3-RX <- nhận dữ liệu
  RX  (trắng|  Không nối    |  Cảm biến không cần lệnh
  ----------+---------------+--------------------------------
  KHÔNG cần voltage divider  SEN0311 dùng UART 3.3V logic

  Cổng UART: /dev/ttyAMA3
  Bật trong /boot/config.txt:
    dtoverlay=disable-bt     <- giải phóng ttyAMA0 cho motor
    dtoverlay=uart3          <- bật UART3 (GPIO4=TX, GPIO5=RX)
  Rồi: sudo reboot

--------------------------------------------------------------
  ĐẤU DÂY  PHASE 2 (thêm TRÁI + PHẢI)
--------------------------------------------------------------
  Cảm biến  |  Cổng    |  RPi TX pin   |  RPi RX pin
  ----------+----------+---------------+-------------------
  TRÁI      | ttyAMA4  |  Pin 24 GPIO8 |  Pin 21 GPIO9
  PHẢI      | ttyAMA5  |  Pin 32 GPIO12|  Pin 33 GPIO13
  ----------+----------+---------------+-------------------
  Thêm vào /boot/config.txt:
    dtoverlay=uart4
    dtoverlay=uart5
  Rồi bỏ comment 3 dòng PHASE 2 ở cuối file này.

--------------------------------------------------------------
  Cài thư viện:
    pip install pyserial
--------------------------------------------------------------
"""

import time

import serial

import config
from ultrasonic_mock import ObstacleReading   # tai dung dataclass

# ============================================================
#  Cau hinh cong UART cho tung cam bien
# ============================================================
UART_CENTER = "/dev/ttyAMA3"   # PHASE 1  cam bien GIUA
UART_LEFT   = "/dev/ttyAMA4"   # PHASE 2  cam bien TRAI  (chua dung)
UART_RIGHT  = "/dev/ttyAMA5"   # PHASE 2  cam bien PHAI (chua dung)

_BAUD         = 9600
_HEADER       = 0xFF
_READ_TIMEOUT = 0.15   # giay  timeout moi lan doc goi


# ============================================================
#  Low-level: doc 1 goi tu SEN0311
# ============================================================

def _read_packet(ser: serial.Serial) -> float:
    """
    Doc 1 goi tin 4-byte tu cam bien SEN0311 / A02YYUW.

    Goi tin: [0xFF, H, L, SUM]
      distance_mm = H * 256 + L
      SUM = (0xFF + H + L) & 0xFF

    Returns:
        float: khoang cach (cm). Tra config.DEFAULT_DISTANCE_CM neu loi/timeout.
    """
    deadline = time.time() + _READ_TIMEOUT

    while time.time() < deadline:
        waiting = ser.in_waiting
        if waiting < 4:
            time.sleep(0.005)
            continue

        buf = ser.read(ser.in_waiting)   # doc het buffer

        # Tim byte 0xFF tu cuoi ve (lay goi moi nhat)
        idx = len(buf) - 4
        while idx >= 0:
            if buf[idx] == _HEADER:
                h   = buf[idx + 1]
                l   = buf[idx + 2]
                chk = buf[idx + 3]

                # Kiem tra checksum
                if ((_HEADER + h + l) & 0xFF) == chk:
                    dist_mm = h * 256 + l
                    dist_cm = dist_mm / 10.0
                    # Loc gia tri ngoai tam do hop le
                    if 3.0 <= dist_cm <= 450.0:
                        return dist_cm
            idx -= 1

    # Timeout hoac khong co goi hop le
    return config.DEFAULT_DISTANCE_CM


# ============================================================
#  _SEN0311Sensor  wrapper cho 1 cam bien
# ============================================================

class _SEN0311Sensor:
    """Wrapper doc 1 cam bien SEN0311 qua UART."""

    def __init__(self, port: str, name: str):
        self._name = name
        try:
            self._ser = serial.Serial(port, _BAUD, timeout=_READ_TIMEOUT)
            print(f"[ULTRASONIC] {name} sensor open -> {port}  @{_BAUD} baud")
        except serial.SerialException as e:
            raise RuntimeError(
                f"[ULTRASONIC] Khong mo duoc {port} cho cam bien {name}: {e}\n"
                f"  Kiem tra:\n"
                f"  1. /boot/config.txt co dtoverlay=uart3 (hoac uart4/uart5)\n"
                f"  2. sudo reboot sau khi chinh\n"
                f"  3. ls /dev/ttyAMA*"
            ) from e

    def read_cm(self) -> float:
        return _read_packet(self._ser)

    def close(self):
        try:
            self._ser.close()
        except Exception:
            pass


# ============================================================
#  RealUltrasonicArray  API giong MockUltrasonicArray
# ============================================================

class RealUltrasonicArray:
    """
    Doc cam bien SEN0311 / A02YYUW qua UART.

    PHASE 1: Chi cam bien GIUA (/dev/ttyAMA3).
             TRAI va PHAI tra ve DEFAULT_DISTANCE_CM (an toan, khong co vat can).

    API giong het MockUltrasonicArray  drop-in replace, khong doi camera_follow_laptop.py.

    Khi them cam bien TRAI/PHAI (PHASE 2):
      Bo comment 3 dong o cuoi __init__ va cleanup.
    """

    def __init__(self):
        # PHASE 1: chi cam bien giua
        self._center = _SEN0311Sensor(UART_CENTER, "CENTER")

        # PHASE 2: bo comment 2 dong duoi khi lap them
        # self._left  = _SEN0311Sensor(UART_LEFT,   "LEFT")
        # self._right = _SEN0311Sensor(UART_RIGHT,  "RIGHT")

        print(
            f"[ULTRASONIC] RealUltrasonicArray (SEN0311) ready  "
            f"| stop={config.OBSTACLE_STOP_CM:.0f}cm "
            f"slow={config.OBSTACLE_SLOW_CM:.0f}cm "
            f"side={config.SIDE_SAFE_CM:.0f}cm  "
            f"[CENTER={UART_CENTER} | LEFT/RIGHT=disabled]"
        )

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def read(self) -> ObstacleReading:
        """
        Doc ca 3 kenh va tra ve ObstacleReading.

        PHASE 1: LEFT va RIGHT = DEFAULT_DISTANCE_CM (khong trigger tranh vat can ben).
        """
        center_cm = self._center.read_cm()

        # PHASE 2: thay 2 dong duoi bang:
        #   left_cm  = self._left.read_cm()
        #   right_cm = self._right.read_cm()
        left_cm  = config.DEFAULT_DISTANCE_CM
        right_cm = config.DEFAULT_DISTANCE_CM

        return ObstacleReading(
            left_cm=left_cm,
            center_cm=center_cm,
            right_cm=right_cm,
        )

    def is_obstacle_detected(self) -> bool:
        """True neu cam bien giua kich hoat stop."""
        return self.read().center_stop

    def get_distance_cm(self) -> float:
        """Chi tra khoang cach cam bien giua (cm)."""
        return self._center.read_cm()

    def cleanup(self):
        """Dong tat ca cong serial. Goi khi thoat chuong trinh."""
        self._center.close()
        # PHASE 2: bo comment 2 dong duoi
        # self._left.close()
        # self._right.close()
        print("[ULTRASONIC] Serial ports closed")


# ============================================================
#  Test doc lap  chay: python ultrasonic_raspi.py
# ============================================================

if __name__ == "__main__":
    print("=== SEN0311 Test  Cam bien GIUA ===")
    print(f"Port: {UART_CENTER}  Baud: {_BAUD}")
    print("Ctrl+C de thoat\n")

    try:
        sensor = _SEN0311Sensor(UART_CENTER, "CENTER")
        while True:
            d = sensor.read_cm()
            bar = "#" * min(int(d / 5), 40)
            print(f"  {d:6.1f} cm  |{bar}")
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\nDung test.")
    except RuntimeError as e:
        print(e)
