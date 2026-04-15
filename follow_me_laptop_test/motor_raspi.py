"""
motor_raspi.py - Real UART motor controller cho Raspberry Pi.

Binary frame protocol (7 bytes):
  [0xAA] [speed_a] [dir_a] [speed_b] [dir_b] [CRC] [0x55]
  speed : 0=phanh, 1-255=chay
  dir   : 0=CW, 1=CCW
  ACK   : STM32 gui 0x06

API ngoai: send(left, right) voi -100 den +100
  Gia tri am = lui (dir=1 CCW), duong = tien (dir=0 CW)
"""

import time
import serial
import config

FRAME_SOF = 0xAA
FRAME_EOF = 0x55


def calc_crc(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= b
    return crc


def build_frame(speed_a, dir_a, speed_b, dir_b) -> bytes:
    speed_a = max(0, min(255, int(speed_a)))
    speed_b = max(0, min(255, int(speed_b)))
    dir_a   = 1 if dir_a else 0
    dir_b   = 1 if dir_b else 0
    payload = bytes([speed_a, dir_a, speed_b, dir_b])
    return bytes([FRAME_SOF]) + payload + bytes([calc_crc(payload), FRAME_EOF])


def _wheel_to_channel_dir(wheel: str, value: int) -> tuple[int, int]:
    """Map lenh banh trai/phai sang speed+dir phu hop voi cuc tinh tung kenh."""
    value = max(-100, min(100, int(value)))
    speed = round(abs(value) / 100 * 255)
    if wheel == "right":
        direction = 1 if value < 0 else 0
    else:
        direction = 0 if value < 0 else 1
    return speed, direction


def _apply_trim(value: int, trim: float) -> int:
    """Bù sai số cơ khí từng bánh, giữ nguyên dấu tiến/lùi."""
    if value == 0:
        return 0
    scaled = int(round(abs(value) * float(trim)))
    scaled = max(0, min(100, scaled))
    return scaled if value > 0 else -scaled


def _apply_min_effective_speed(value: int) -> int:
    """Đẩy lệnh nhỏ lên ngưỡng đủ thắng ma sát khởi động của motor."""
    if value == 0:
        return 0
    min_eff = int(getattr(config, "MOTOR_MIN_EFFECTIVE_SPEED", 0))
    if min_eff <= 0:
        return value
    mag = abs(value)
    if mag >= min_eff:
        return value
    return min_eff if value > 0 else -min_eff


def _apply_forward_boost(left: int, right: int) -> tuple[int, int]:
    """Bù lệch cơ khí khi xe đang chạy tiến."""
    if left > 0:
        left += int(getattr(config, "WHEEL_FORWARD_BOOST_LEFT", 0))
    if right > 0:
        right += int(getattr(config, "WHEEL_FORWARD_BOOST_RIGHT", 0))
    left = max(-100, min(100, left))
    right = max(-100, min(100, right))
    return left, right


def _apply_directional_steer_comp(left: int, right: int) -> tuple[int, int]:
    """Bù theo hướng rẽ để sửa hiện tượng mục tiêu bên phải nhưng xe vẫn kéo trái."""
    if left > right and left > 0:
        left += int(getattr(config, "STEER_RIGHT_LEFT_BOOST", 0))
    elif right > left and right > 0:
        right -= int(getattr(config, "STEER_LEFT_RIGHT_REDUCE", 0))
    left = max(-100, min(100, left))
    right = max(-100, min(100, right))
    return left, right


def _apply_start_boost(prev_left: int, prev_right: int, left: int, right: int) -> tuple[int, int]:
    """Khi vừa rời trạng thái đứng yên, đẩy lệnh lên cao hơn để thắng ma sát khởi động."""
    boost = int(getattr(config, "MOTOR_START_BOOST", 0))
    if boost <= 0:
        return left, right
    if prev_left == 0 and left > 0:
        left = max(left, boost)
    if prev_right == 0 and right > 0:
        right = max(right, boost)
    left = max(-100, min(100, left))
    right = max(-100, min(100, right))
    return left, right


class RealMotorUART:
    def __init__(self, port="/dev/ttyACM0", baudrate=115200, timeout=0.005):
        self._port     = port
        self._last_cmd = (-999, -999)
        self._ack_miss_count = 0
        self._ack_timeout = float(getattr(config, "MOTOR_ACK_TIMEOUT", 0.030))
        self._ack_retries = max(1, int(getattr(config, "MOTOR_ACK_RETRIES", 3)))
        try:
            self.ser = serial.Serial(port, baudrate=baudrate, timeout=timeout)
            self.ser.reset_input_buffer()
            print(f"[UART] RealMotorUART connected -> {port} @{baudrate} baud")
        except serial.SerialException as e:
            raise RuntimeError(f"[UART] Khong mo duoc cong {port}: {e}") from e

    def _wait_for_ack(self) -> bool:
        """Cho ACK 0x06 trong mot timeout ngan de dong bo tung frame."""
        deadline = time.time() + self._ack_timeout
        while time.time() < deadline:
            waiting = getattr(self.ser, "in_waiting", 0)
            if waiting > 0:
                ack = self.ser.read(waiting)
                if bytes([0x06]) in ack:
                    self._ack_miss_count = 0
                    return True
            time.sleep(0.001)
        self._ack_miss_count += 1
        return False

    def send(self, left: int, right: int) -> bool:
        left  = max(-100, min(100, int(left)))
        right = max(-100, min(100, int(right)))
        left  = _apply_trim(left, getattr(config, "WHEEL_TRIM_LEFT", 1.0))
        right = _apply_trim(right, getattr(config, "WHEEL_TRIM_RIGHT", 1.0))
        left, right = _apply_forward_boost(left, right)
        left, right = _apply_directional_steer_comp(left, right)
        left  = _apply_min_effective_speed(left)
        right = _apply_min_effective_speed(right)
        left, right = _apply_start_boost(
            self._last_cmd[0] if self._last_cmd != (-999, -999) else 0,
            self._last_cmd[1] if self._last_cmd != (-999, -999) else 0,
            left,
            right,
        )

        # Loại bỏ thay đổi rất nhỏ để xe bớt giật và STM32 không bị spam setpoint.
        if self._last_cmd != (-999, -999):
            force_send = (
                (left == 0 and right == 0) or
                (left > 0 > self._last_cmd[0]) or (left < 0 < self._last_cmd[0]) or
                (right > 0 > self._last_cmd[1]) or (right < 0 < self._last_cmd[1])
            )
            if (not force_send and
                    abs(left - self._last_cmd[0]) < config.MOTOR_CMD_DEADBAND and
                    abs(right - self._last_cmd[1]) < config.MOTOR_CMD_DEADBAND):
                return True

        if (left, right) == self._last_cmd:
            return True
        # Mapping kenh A/B co the dao neu phan cung dang noi nguoc trai/phai.
        if getattr(config, "MOTOR_SWAP_LEFT_RIGHT", False):
            speed_a, dir_a = _wheel_to_channel_dir("left", left)
            speed_b, dir_b = _wheel_to_channel_dir("right", right)
        else:
            speed_a, dir_a = _wheel_to_channel_dir("right", right)
            speed_b, dir_b = _wheel_to_channel_dir("left", left)
        frame = build_frame(speed_a, dir_a, speed_b, dir_b)
        try:
            hex_str = " ".join(f"{b:02x}" for b in frame)
            for attempt in range(1, self._ack_retries + 1):
                self.ser.reset_input_buffer()
                self.ser.write(frame)
                if self._wait_for_ack():
                    self._last_cmd = (left, right)
                    log_min = int(getattr(config, "MOTOR_LOG_MIN_ABS", 20))
                    if abs(left) >= log_min or abs(right) >= log_min or (left == 0 and right == 0):
                        print(
                            f"[UART] cmd L={left:>4} R={right:>4} -> "
                            f"A(speed={speed_a:>3},dir={dir_a}) "
                            f"B(speed={speed_b:>3},dir={dir_b}) | {hex_str} | ACK"
                        )
                    return True
                print(
                    f"[UART] ACK timeout attempt {attempt}/{self._ack_retries} "
                    f"for L={left} R={right} | {hex_str}"
                )
            return False
        except serial.SerialException as e:
            print(f"[UART] Loi ghi UART: {e}")
            return False

    def send_raw(self, speed_a, dir_a, speed_b, dir_b) -> bool:
        """Gui thang binary frame (speed 0-255, dir CW/CCW)."""
        frame = build_frame(speed_a, dir_a, speed_b, dir_b)
        try:
            for _ in range(self._ack_retries):
                self.ser.reset_input_buffer()
                self.ser.write(frame)
                if self._wait_for_ack():
                    return True
            return False
        except serial.SerialException as e:
            print(f"[UART] Loi ghi UART (raw): {e}")
            return False

    def stop(self):
        self.send(0, 0)
        self._last_cmd = (-999, -999)
        self._ack_miss_count = 0

    def close(self):
        try:
            self.stop()
            self.ser.close()
            print("[UART] Serial port closed")
        except Exception:
            pass
