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


class RealMotorUART:
    def __init__(self, port="/dev/ttyACM0", baudrate=115200, timeout=0.005):
        self._port     = port
        self._last_cmd = (-999, -999)
        self._ack_miss_count = 0
        try:
            self.ser = serial.Serial(port, baudrate=baudrate, timeout=timeout)
            self.ser.reset_input_buffer()
            print(f"[UART] RealMotorUART connected -> {port} @{baudrate} baud")
        except serial.SerialException as e:
            raise RuntimeError(f"[UART] Khong mo duoc cong {port}: {e}") from e

    def send(self, left: int, right: int) -> bool:
        left  = max(-100, min(100, int(left)))
        right = max(-100, min(100, int(right)))

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
        # Kênh A = bánh PHẢI,  Kênh B = bánh TRÁI
        # Forward: A dir=0 (CW), B dir=1 (CCW) — ngược nhau vì gắn đối xứng
        dir_a = 1 if right < 0 else 0           # bánh phải → kênh A
        dir_b = 0 if left  < 0 else 1           # bánh trái → kênh B (đảo dir)
        speed_a = round(abs(right) / 100 * 255)  # A = phải
        speed_b = round(abs(left)  / 100 * 255)  # B = trái
        frame = build_frame(speed_a, dir_a, speed_b, dir_b)
        try:
            self.ser.write(frame)
            self._last_cmd = (left, right)
            ok = True

            # Không block chờ ACK; chỉ đọc nếu STM32 đã trả dữ liệu.
            waiting = getattr(self.ser, "in_waiting", 0)
            if waiting > 0:
                ack = self.ser.read(waiting)
                ok = bytes([0x06]) in ack
                if ok:
                    self._ack_miss_count = 0
            else:
                self._ack_miss_count += 1
                if self._ack_miss_count % 50 == 0:
                    print(f"[UART] ACK miss x{self._ack_miss_count} (non-blocking)")
            return ok
        except serial.SerialException as e:
            print(f"[UART] Loi ghi UART: {e}")
            return False

    def send_raw(self, speed_a, dir_a, speed_b, dir_b) -> bool:
        """Gui thang binary frame (speed 0-255, dir CW/CCW)."""
        frame = build_frame(speed_a, dir_a, speed_b, dir_b)
        try:
            self.ser.write(frame)
            ack = self.ser.read(1)
            return ack == bytes([0x06])
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
