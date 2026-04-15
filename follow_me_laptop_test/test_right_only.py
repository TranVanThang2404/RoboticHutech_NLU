"""Test chi chay banh phai de kiem tra huong quay va do manh cua banh phai.

Mac dinh:
  - Dem nguoc 3 giay
  - Chi gui lenh tien cho banh phai
  - Tu dong dung sau mot khoang thoi gian
"""

from __future__ import annotations

import argparse
import time

from motor_raspi import RealMotorUART


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test chi chay banh phai."
    )
    parser.add_argument("--speed", type=int, default=30, help="Toc do 0-100. Mac dinh: 30")
    parser.add_argument("--duration", type=float, default=2.0, help="So giay chay. Mac dinh: 2.0")
    parser.add_argument("--countdown", type=int, default=3, help="So giay dem nguoc. Mac dinh: 3")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    speed = max(0, min(100, int(args.speed)))
    duration = max(0.1, float(args.duration))
    countdown = max(0, int(args.countdown))

    motor = RealMotorUART()
    print("[TEST] Right wheel only")
    print(f"[TEST] speed={speed}, duration={duration:.1f}s, countdown={countdown}s")
    print("[TEST] Dat xe ke chan hoac nhac banh len neu can an toan.")

    try:
        for sec in range(countdown, 0, -1):
            print(f"[TEST] Chay sau {sec}...")
            time.sleep(1.0)

        print(f"[TEST] Gui lenh: L=0, R=+{speed}")
        if not motor.send(0, speed, apply_compensation=False):
            print("[TEST] Khong nhan duoc ACK tu STM32, huy test.")
            return 1

        time.sleep(duration)
        print("[TEST] Het thoi gian, dang dung xe.")
        return 0
    except KeyboardInterrupt:
        print("[TEST] Nguoi dung da dung test.")
        return 130
    finally:
        try:
            motor.stop()
        finally:
            motor.close()
        print("[TEST] Da gui lenh dung.")


if __name__ == "__main__":
    raise SystemExit(main())
