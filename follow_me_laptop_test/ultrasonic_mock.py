"""
ultrasonic_mock.py — Mock mảng 3 cảm biến siêu âm (Trái / Giữa / Phải).

Sơ đồ lắp đặt trên xe:
                    [TRÁI]   [GIỮA]   [PHẢI]
                       \\       |       /
                        \\      |      /
                     ← bên trái  bên phải →
                            [XE]

Trên Raspberry Pi thật, thay MockUltrasonicArray bằng:

    import RPi.GPIO as GPIO
    import time

    # Khai báo chân GPIO cho từng cảm biến HC-SR04
    SENSORS_PINS = {
        "left":   {"trig": 17, "echo": 27},
        "center": {"trig": 23, "echo": 24},
        "right":  {"trig":  5, "echo":  6},
    }

    class RealUltrasonicArray:
        def __init__(self):
            GPIO.setmode(GPIO.BCM)
            for s in SENSORS_PINS.values():
                GPIO.setup(s["trig"], GPIO.OUT)
                GPIO.setup(s["echo"], GPIO.IN)

        def _measure_cm(self, trig: int, echo: int) -> float:
            GPIO.output(trig, True)
            time.sleep(0.00001)
            GPIO.output(trig, False)
            start = end = time.time()
            while GPIO.input(echo) == 0:
                start = time.time()
            while GPIO.input(echo) == 1:
                end = time.time()
            return (end - start) * 17150  # cm

        def read(self) -> "ObstacleReading":
            vals = {}
            for name, pins in SENSORS_PINS.items():
                vals[name] = self._measure_cm(pins["trig"], pins["echo"])
            return ObstacleReading(
                left_cm=vals["left"],
                center_cm=vals["center"],
                right_cm=vals["right"],
            )

        def is_obstacle_detected(self) -> bool:
            return self.read().center_stop
"""

from dataclasses import dataclass

import config


# ============================================================
#  ObstacleReading — kết quả đọc 3 cảm biến trong 1 chu kỳ
# ============================================================

@dataclass
class ObstacleReading:
    """
    Snapshot khoảng cách từ 3 cảm biến siêu âm.

    Thuộc tính:
        left_cm   : khoảng cách cảm biến trái (cm)
        center_cm : khoảng cách cảm biến giữa (cm)
        right_cm  : khoảng cách cảm biến phải (cm)

    Property logic:
        center_stop  : phía trước nguy hiểm → DỪNG
        center_slow  : phía trước vào vùng cảnh báo → GIẢM TỐC
        left_blocked : bên trái bị chặn → lệch sang phải
        right_blocked: bên phải bị chặn → lệch sang trái
    """
    left_cm:   float
    center_cm: float
    right_cm:  float

    @property
    def center_stop(self) -> bool:
        """Phía trước < OBSTACLE_STOP_CM → dừng hoàn toàn."""
        return self.center_cm < config.OBSTACLE_STOP_CM

    @property
    def center_slow(self) -> bool:
        """Phía trước vào vùng giảm tốc (chưa stop)."""
        return self.center_cm < config.OBSTACLE_SLOW_CM

    @property
    def left_blocked(self) -> bool:
        """Bên trái < SIDE_SAFE_CM → không rẽ trái, buộc sang phải."""
        return self.left_cm < config.SIDE_SAFE_CM

    @property
    def right_blocked(self) -> bool:
        """Bên phải < SIDE_SAFE_CM → không rẽ phải, buộc sang trái."""
        return self.right_cm < config.SIDE_SAFE_CM

    @property
    def slow_factor(self) -> float:
        """
        Hệ số giảm tốc tuyến tính dựa trên cảm biến giữa (0.30 – 1.0).
        1.0 = tốc độ bình thường (≥ OBSTACLE_SLOW_CM)
        0.30 = tốc độ tối thiểu (sát OBSTACLE_STOP_CM)
        """
        if not self.center_slow:
            return 1.0
        span = max(1.0, config.OBSTACLE_SLOW_CM - config.OBSTACLE_STOP_CM)
        return max(0.30, (self.center_cm - config.OBSTACLE_STOP_CM) / span)

    def summary(self) -> str:
        """Chuỗi mô tả ngắn trạng thái 3 cảm biến."""
        flags = []
        if self.center_stop:
            flags.append("STOP")
        elif self.center_slow:
            flags.append("SLOW")
        if self.left_blocked:
            flags.append("L-BLK")
        if self.right_blocked:
            flags.append("R-BLK")
        return " ".join(flags) if flags else "CLEAR"


# ============================================================
#  MockUltrasonicArray — giả lập 3 cảm biến cho laptop test
# ============================================================

class MockUltrasonicArray:
    """
    Giả lập mảng 3 cảm biến siêu âm: Trái / Giữa / Phải.

    Dùng trong laptop test; thay bằng RealUltrasonicArray trên Raspberry Pi.

    Phím tắt trong camera loop:
        O   → toggle vật cản GIỮA (phía trước)
        [   → toggle vật cản TRÁI
        ]   → toggle vật cản PHẢI
    """

    def __init__(self):
        self._fake_cm: dict[str, float] = {
            "left":   config.DEFAULT_DISTANCE_CM,
            "center": config.DEFAULT_DISTANCE_CM,
            "right":  config.DEFAULT_DISTANCE_CM,
        }
        self._obstacle_cm = 10.0   # khoảng cách giả lập khi fake bật
        print(
            f"[ULTRASONIC] MockUltrasonicArray (3 sensors) initialized  "
            f"| stop={config.OBSTACLE_STOP_CM:.0f}cm "
            f"slow={config.OBSTACLE_SLOW_CM:.0f}cm "
            f"side={config.SIDE_SAFE_CM:.0f}cm"
        )

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def read(self) -> ObstacleReading:
        """Đọc cả 3 cảm biến và trả về ObstacleReading."""
        return ObstacleReading(
            left_cm=self._fake_cm["left"],
            center_cm=self._fake_cm["center"],
            right_cm=self._fake_cm["right"],
        )

    def is_obstacle_detected(self) -> bool:
        """Backward-compat: True nếu cảm biến giữa kích hoạt stop."""
        return self.read().center_stop

    def get_distance_cm(self) -> float:
        """Backward-compat: chỉ trả khoảng cách cảm biến giữa (cm)."""
        return self._fake_cm["center"]

    @property
    def fake_obstacle(self) -> bool:
        """True nếu cảm biến giữa đang ở chế độ fake-obstacle."""
        return self._fake_cm["center"] < config.DEFAULT_DISTANCE_CM

    def set_fake_obstacle(
        self,
        active: bool,
        side: str = "center",
        distance_cm: float = None,
    ):
        """
        Bật / tắt giả lập vật cản cho một hoặc tất cả cảm biến.

        Args:
            active     : True = bật vật cản, False = xóa
            side       : "left" | "center" | "right" | "all"
            distance_cm: khoảng cách giả lập khi bật (mặc định 10 cm)
        """
        if distance_cm is not None:
            self._obstacle_cm = distance_cm

        targets = ["left", "center", "right"] if side == "all" else [side]
        for s in targets:
            if s in self._fake_cm:
                self._fake_cm[s] = (
                    self._obstacle_cm if active else config.DEFAULT_DISTANCE_CM
                )

        obs = self.read()
        print(
            f"[ULTRASONIC] Fake '{side}': {'ON' if active else 'OFF'}  "
            f"| L={obs.left_cm:.0f}  C={obs.center_cm:.0f}  R={obs.right_cm:.0f} cm"
            f"  [{obs.summary()}]"
        )

    def cleanup(self):
        """No-op cho mock — tương thích API với RealUltrasonicArray."""
        pass
