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
    def __init__(self, port="/dev/ttyACM0", baudrate=115200, timeout=0.1):
        self._port     = port
        self._last_cmd = (-999, -999)
        try:
            self.ser = serial.Serial(port, baudrate=baudrate, timeout=timeout)
            print(f"[UART] RealMotorUART connected -> {port} @{baudrate} baud")
        except serial.SerialException as e:
            raise RuntimeError(f"[UART] Khong mo duoc cong {port}: {e}") from e

    def send(self, left: int, right: int) -> bool:
        left  = max(-100, min(100, int(left)))
        right = max(-100, min(100, int(right)))
        # Đảo chiều: code tính tiến=dương, nhưng motor thực tế lắp ngược
        left  = -left
        right = -right
        if (left, right) == self._last_cmd:
            return True
        dir_a = 1 if left < 0 else 0
        dir_b = 1 if right < 0 else 0
        frame = build_frame(round(abs(left)/100*255), dir_a, round(abs(right)/100*255), dir_b)
        try:
            self.ser.write(frame)
            ack = self.ser.read(1)
            ok  = (ack == bytes([0x06]))
            if ok:
                self._last_cmd = (left, right)
            else:
                print(f"[UART] ACK khong hop le: {ack.hex() if ack else 'timeout'}")
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

    def close(self):
        try:
            self.stop()
            self.ser.close()
            print("[UART] Serial port closed")
        except Exception:
            pass
