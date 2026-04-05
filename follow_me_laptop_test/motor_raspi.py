"""
motor_raspi.py — Real UART motor controller cho Raspberry Pi.

Giao tiếp với board điều khiển động cơ (STM32 / Arduino) qua cổng UART.

Sơ đồ kết nối (Raspberry Pi 4):
  Pi TX  (GPIO 14, pin 8)  →  Board RX
  Pi RX  (GPIO 15, pin 10) ←  Board TX
  GND    (pin 6)           ↔  Board GND

Cổng mặc định: /dev/ttyAMA0  (UART hardware — cần tắt console serial trong raspi-config)
Nếu dùng USB-Serial: /dev/ttyUSB0

Format lệnh gửi: "M,left,right\n"
  left, right: tốc độ bánh (0–100 hoặc -100–100 nếu hỗ trợ lùi)

Cài thư viện:
  pip install pyserial

Bật UART trên RPi:
  sudo raspi-config → Interface Options → Serial Port
    - "Would you like a login shell to be accessible over serial?" → No
    - "Would you like the serial port hardware to be enabled?" → Yes
  sudo reboot
"""

import serial
import config


class RealMotorUART:
    """
    Gửi lệnh điều khiển motor qua UART đến board STM32 / Arduino.

    Format lệnh: "M,left,right\\n"
      left  : tốc độ bánh trái  (0–100)
      right : tốc độ bánh phải  (0–100)
    """

    def __init__(
        self,
        port: str = "/dev/ttyAMA0",
        baudrate: int = 115200,
    ):
        self._port     = port
        self._baudrate = baudrate
        self._last_cmd = (-999, -999)
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            print(f"[UART] RealMotorUART connected → {port}  @{baudrate} baud")
        except serial.SerialException as e:
            raise RuntimeError(
                f"[UART] Không mở được cổng {port}: {e}\n"
                f"       Kiểm tra: ls /dev/tty* | raspi-config serial port"
            ) from e

    def send(self, left: int, right: int):
        """
        Gửi lệnh tốc độ motor.
        Chỉ gửi khi lệnh thay đổi để tránh spam UART.
        """
        left  = max(-100, min(100, int(left)))
        right = max(-100, min(100, int(right)))
        if (left, right) == self._last_cmd:
            return
        cmd = f"M,{left},{right}\n"
        try:
            self.ser.write(cmd.encode("ascii"))
            self._last_cmd = (left, right)
        except serial.SerialException as e:
            print(f"[UART] Lỗi ghi UART: {e}")

    def stop(self):
        """Dừng tất cả động cơ ngay lập tức."""
        self.send(0, 0)

    def close(self):
        """Đóng kết nối serial."""
        try:
            self.stop()
            self.ser.close()
            print("[UART] Serial port closed")
        except Exception:
            pass
