"""Test motor chi di thang toi de kiem tra huong quay hai banh.

Mac dinh:
  - Dem nguoc 3 giay
  - Chay tien thang 2 banh cung toc do
  - Tu dong dung sau mot khoang thoi gian

Vi du:
  python test_forward_only.py
  python test_forward_only.py --speed 25 --duration 2.5
"""

from __future__ import annotations

import argparse
import time

from motor_raspi import RealMotorUART


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test xe chi di thang toi de kiem tra co bi nguoc banh hay khong."
    )
    parser.add_argument(
        "--speed",
        type=int,
        default=25,
        help="Toc do gui cho ca 2 banh, 0-100. Mac dinh: 25",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=2.0,
        help="So giay chay thang truoc khi dung. Mac dinh: 2.0",
    )
    parser.add_argument(
        "--countdown",
        type=int,
        default=3,
        help="So giay dem nguoc truoc khi xe chay. Mac dinh: 3",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    speed = max(0, min(100, int(args.speed)))
    duration = max(0.1, float(args.duration))
    countdown = max(0, int(args.countdown))

    motor = RealMotorUART()
    print("[TEST] Forward-only motor test")
    print(f"[TEST] speed={speed}, duration={duration:.1f}s, countdown={countdown}s")
    print("[TEST] Dat xe ke chan hoac nhac banh len neu can an toan.")

    try:
        for sec in range(countdown, 0, -1):
            print(f"[TEST] Chay sau {sec}...")
            time.sleep(1.0)

        print("[TEST] Gui lenh di thang toi: L=+{0}, R=+{0}".format(speed))
        if not motor.send(speed, speed):
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
