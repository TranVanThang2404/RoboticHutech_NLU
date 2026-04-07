"""
test_motor_direction.py — Test motor từng hướng để xác định đúng/sai.

Chạy trên RPi khi đã cắm STM32:
    python test_motor_direction.py

Mỗi bước chạy 2 giây rồi dừng 1 giây.
Quan sát xe thực tế và ghi lại kết quả.
"""

import time
import sys

# === Dùng send_raw để bypass mọi logic đảo chiều ===
from motor_raspi import RealMotorUART

SPEED = 120          # 0-255, tốc độ vừa phải để test
DURATION = 2.0       # giây mỗi bước
PAUSE = 1.5          # giây nghỉ giữa các bước

def run_test():
    print("=" * 55)
    print("  TEST MOTOR DIRECTION — Quan sát xe thực tế")
    print("=" * 55)

    try:
        motor = RealMotorUART()
    except RuntimeError as e:
        print(f"\n[LỖI] {e}")
        print("Hãy chắc chắn STM32 đã cắm USB và port /dev/ttyACM0 đúng.")
        sys.exit(1)

    tests = [
        # (tên, speed_a, dir_a, speed_b, dir_b, mô tả kỳ vọng)
        ("TEST 1: A=CW  B=CW",   SPEED, 0, SPEED, 0,
         "Cả 2 bánh quay CW (dir=0)"),
        ("TEST 2: A=CCW B=CCW",  SPEED, 1, SPEED, 1,
         "Cả 2 bánh quay CCW (dir=1)"),
        ("TEST 3: A=CW  B=CCW",  SPEED, 0, SPEED, 1,
         "Bánh A quay CW, Bánh B quay CCW"),
        ("TEST 4: A=CCW B=CW",   SPEED, 1, SPEED, 0,
         "Bánh A quay CCW, Bánh B quay CW"),
        ("TEST 5: Chỉ A chạy",   SPEED, 0, 0,     0,
         "Chỉ motor A chạy CW, B dừng"),
        ("TEST 6: Chỉ B chạy",   0,     0, SPEED,  0,
         "Chỉ motor B chạy CW, A dừng"),
    ]

    print(f"\n  Tốc độ test: {SPEED}/255")
    print(f"  Mỗi bước chạy {DURATION}s, nghỉ {PAUSE}s")
    print(f"  Tổng cộng {len(tests)} bước test")
    print()

    input("  Nhấn ENTER để bắt đầu (đặt xe lên cao hoặc xuống đất)...")
    print()

    for i, (name, sa, da, sb, db, desc) in enumerate(tests, 1):
        print(f"  [{i}/{len(tests)}] {name}")
        print(f"    Frame gửi: speed_a={sa} dir_a={da} speed_b={sb} dir_b={db}")
        print(f"    Kỳ vọng: {desc}")
        print(f"    >> Đang chạy {DURATION}s ...", end="", flush=True)

        motor.send_raw(sa, da, sb, db)
        time.sleep(DURATION)
        motor.send_raw(0, 0, 0, 0)  # dừng

        print(" XONG")
        print(f"    → Xe thực tế làm gì? (ghi nhớ lại)")
        print()

        if i < len(tests):
            time.sleep(PAUSE)

    # Dừng hẳn
    motor.stop()
    motor.close()

    print("=" * 55)
    print("  TEST XONG — Hãy cho tôi biết kết quả:")
    print("=" * 55)
    print("""
    Với mỗi test, hãy cho biết xe thực tế:
      - Đi tới hay lùi?
      - Quẹo trái hay phải?
      - Bánh nào quay, hướng nào?

    Ví dụ:
      TEST 1 (A=CW B=CW):   xe đi tới / xe đi lùi
      TEST 2 (A=CCW B=CCW): xe đi lùi / xe đi tới
      TEST 3 (A=CW B=CCW):  xe quẹo trái / xe quẹo phải
      TEST 5 (Chỉ A):       bánh trái quay / bánh phải quay
      TEST 6 (Chỉ B):       bánh trái quay / bánh phải quay
    """)


if __name__ == "__main__":
    run_test()
