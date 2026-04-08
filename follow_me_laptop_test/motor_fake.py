"""
motor_fake.py — Fake UART motor controller (chạy trên laptop, không cần phần cứng).

Protocol thật (motor_raspi.py) dùng binary frame:
  [0xAA] [speed_a] [dir_a] [speed_b] [dir_b] [CRC] [0x55]
  speed : 0 = phanh, 1–255
  dir   : 0 = CW,    1 = CCW
  CRC   : XOR của 4 payload bytes
  ACK   : STM32 gửi lại 0x06

Class này mô phỏng cùng API send(left, right) và cũng hiển thị frame sẽ gửi
thực tế để dễ debug.
"""

# ---- Frame helpers (giống motor_raspi.py) ----
FRAME_SOF = 0xAA
FRAME_EOF = 0x55


def _calc_crc(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= b
    return crc


def _build_frame(speed_a: int, dir_a: int,
                 speed_b: int, dir_b: int) -> bytes:
    speed_a = max(0, min(255, int(speed_a)))
    speed_b = max(0, min(255, int(speed_b)))
    dir_a   = 1 if dir_a else 0
    dir_b   = 1 if dir_b else 0
    payload = bytes([speed_a, dir_a, speed_b, dir_b])
    crc     = _calc_crc(payload)
    return bytes([FRAME_SOF]) + payload + bytes([crc, FRAME_EOF])


class FakeMotorUART:
    """
    Giả lập UART gửi lệnh điều khiển động cơ tới STM32.

    Binary frame protocol (7 bytes):
        [0xAA][speed_a][dir_a][speed_b][dir_b][CRC][0x55]
        CRC = XOR(speed_a, dir_a, speed_b, dir_b)
        ACK từ STM32: 0x06

    - left  : tốc độ bánh trái  (-100–100) → |speed| scale → speed_a (0–255)
      Âm = lùi (dir=1 CCW), dương = tiến (dir=0 CW)
    - right : tốc độ bánh phải  (-100–100) → |speed| scale → speed_b (0–255)
      Âm = lùi (dir=1 CCW), dương = tiến (dir=0 CW)
    """

    def __init__(self):
        self._last_command = (-999, -999)   # tracker để chỉ print khi thay đổi
        print("[FAKE UART] FakeMotorUART initialized  (no real serial port)")

    def send(self, left: int, right: int):
        """
        Gửi lệnh tốc độ motor (-100–100). Âm = lùi.

        Chỉ in ra console khi lệnh thay đổi để tránh spam log.
        Hiển thị binary frame hex để debug parity với motor_raspi.py.
        """
        left  = max(-100, min(100, int(left)))
        right = max(-100, min(100, int(right)))

        if (left, right) != self._last_command:
            # Đồng bộ 100% với motor_raspi.py:
            # Kênh A = bánh phải, kênh B = bánh trái, và bánh trái đảo dir vì gắn đối xứng.
            dir_a   = 1 if right < 0 else 0
            dir_b   = 0 if left  < 0 else 1
            speed_a = round(abs(right) / 100 * 255)
            speed_b = round(abs(left)  / 100 * 255)
            frame   = _build_frame(speed_a, dir_a, speed_b, dir_b)
            hex_str = " ".join(f"{b:02x}" for b in frame)

            if left < 0 and right < 0:
                direction = "LUI      v"
            elif left > right:
                direction = "QUEO PHAI ->"
            elif left < right:
                direction = "<- QUEO TRAI"
            elif left == 0 and right == 0:
                direction = "DUNG     ="
            else:
                direction = "DI THANG  ^"

            print(f"[FAKE UART] frame={hex_str}  ({direction})")
            self._last_command = (left, right)
        return True

    def stop(self):
        """Dừng tất cả động cơ và reset cache."""
        self.send(0, 0)
        self._last_command = (-999, -999)

    def close(self):
        """
        Đóng kết nối.
        Trong bản thật: self.ser.close()
        """
        print("[FAKE UART] Connection closed  (no-op for fake)")
