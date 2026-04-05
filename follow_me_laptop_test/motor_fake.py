"""
motor_fake.py — Fake UART motor controller.

Thay thế class này bằng FakeMotorUART thật khi chạy trên Raspberry Pi:

    import serial
    class RealMotorUART:
        def __init__(self, port="/dev/ttyAMA0", baudrate=115200):
            self.ser = serial.Serial(port, baudrate, timeout=1)

        def send(self, left: int, right: int):
            cmd = f"M,{left},{right}\\n"
            self.ser.write(cmd.encode())

        def stop(self):
            self.send(0, 0)

        def close(self):
            self.ser.close()
"""


class FakeMotorUART:
    """
    Giả lập UART gửi lệnh điều khiển động cơ tới STM32.

    Format lệnh thật: "M,left,right\\n"
    Ở đây chỉ in ra console.

    - left  : tốc độ bánh trái  (0–100)
    - right : tốc độ bánh phải  (0–100)
    """

    def __init__(self):
        self._last_command = (-999, -999)   # tracker để chỉ print khi thay đổi
        print("[FAKE UART] FakeMotorUART initialized  (no real serial port)")

    def send(self, left: int, right: int):
        """
        Gửi lệnh tốc độ motor.

        Chỉ in ra console khi lệnh thay đổi để tránh spam log.
        Format: [FAKE UART] M,left,right
        """
        left  = max(-100, min(100, int(left)))
        right = max(-100, min(100, int(right)))

        if (left, right) != self._last_command:
            # Chú thích hướng di chuyển
            if left > right:
                direction = "QUEO PHAI ->"   # bánh trái nhanh hơn → xe rẽ phải
            elif left < right:
                direction = "<- QUEO TRAI"   # bánh phải nhanh hơn → xe rẽ trái
            else:
                direction = "DI THANG  ^"    # hai bánh bằng nhau → đi thẳng
            print(f"[FAKE UART] M,{left},{right}  ({direction})")
            self._last_command = (left, right)

    def stop(self):
        """Dừng tất cả động cơ."""
        self.send(0, 0)

    def close(self):
        """
        Đóng kết nối.
        Trong bản thật: self.ser.close()
        """
        print("[FAKE UART] Connection closed  (no-op for fake)")
