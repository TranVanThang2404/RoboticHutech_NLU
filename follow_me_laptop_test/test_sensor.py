"""
test_sensor.py — Test nhanh cảm biến SEN0311 trên Raspberry Pi.

Chạy:
  source venv/bin/activate
  python test_sensor.py

Kết quả mong đợi:
  - Nếu nối đúng: hiện khoảng cách (cm) liên tục
  - Nếu nối sai/chưa nối: hiện "Timeout" hoặc lỗi mở cổng
"""

import time
import sys

# === 1. Kiểm tra cổng UART3 tồn tại ===
import os
port = "/dev/ttyAMA3"

print("=" * 50)
print("  TEST CẢM BIẾN SEN0311 (A02YYUW)")
print("=" * 50)
print()

if not os.path.exists(port):
    print(f"[FAIL] Không tìm thấy {port}")
    print()
    print("  Kiểm tra:")
    print("  1. cat /boot/config.txt | grep uart3")
    print("     -> Phải thấy: dtoverlay=uart3")
    print("  2. Nếu chưa có, chạy:")
    print("     sudo bash -c 'echo dtoverlay=uart3 >> /boot/config.txt'")
    print("     sudo reboot")
    print()
    sys.exit(1)

print(f"[OK] Cổng {port} tồn tại")

# === 2. Mở serial ===
try:
    import serial
except ImportError:
    print("[FAIL] Chưa cài pyserial:")
    print("  pip install pyserial")
    sys.exit(1)

try:
    ser = serial.Serial(port, 9600, timeout=0.15)
    print(f"[OK] Mở {port} @ 9600 baud thành công")
except serial.SerialException as e:
    print(f"[FAIL] Không mở được {port}: {e}")
    print()
    print("  Thử: sudo chmod 666 /dev/ttyAMA3")
    print("  Hoặc: sudo usermod -aG dialout $USER && sudo reboot")
    sys.exit(1)

# === 3. Đọc dữ liệu ===
print()
print("Đang đọc cảm biến... (Ctrl+C để dừng)")
print("-" * 50)

HEADER = 0xFF
read_count = 0
success_count = 0
fail_count = 0

try:
    while True:
        read_count += 1

        # Đọc buffer
        time.sleep(0.1)
        waiting = ser.in_waiting

        if waiting == 0:
            fail_count += 1
            print(f"  [{read_count:3d}] Không có dữ liệu (buffer trống) ❌")
            if fail_count >= 5 and success_count == 0:
                print()
                print("  ⚠️  5 lần liên tiếp không nhận được dữ liệu!")
                print("  Kiểm tra:")
                print("  - Dây TX (xanh lá) có nối vào Pin 29 (GPIO5)?")
                print("  - Dây VCC (đỏ) có nối vào Pin 2 (5V)?")
                print("  - Dây GND (đen) có nối vào Pin 9 (GND)?")
                print("  - LED trên sensor có sáng không?")
            if fail_count >= 10 and success_count == 0:
                print()
                print("  ❌ 10 lần thất bại — dừng test.")
                break
            continue

        buf = ser.read(waiting)

        # Tìm gói tin hợp lệ [0xFF, H, L, SUM]
        found = False
        idx = len(buf) - 4
        while idx >= 0:
            if buf[idx] == HEADER:
                h = buf[idx + 1]
                l = buf[idx + 2]
                chk = buf[idx + 3]

                if ((HEADER + h + l) & 0xFF) == chk:
                    dist_mm = h * 256 + l
                    dist_cm = dist_mm / 10.0

                    if 3.0 <= dist_cm <= 450.0:
                        success_count += 1
                        print(f"  [{read_count:3d}] Khoảng cách: {dist_cm:6.1f} cm  ✅")
                        found = True
                        break
                    else:
                        print(f"  [{read_count:3d}] Ngoài tầm đo: {dist_cm:.1f} cm (3-450cm)")
                        found = True
                        break
            idx -= 1

        if not found:
            fail_count += 1
            hex_str = buf[:20].hex(' ')
            print(f"  [{read_count:3d}] Dữ liệu lỗi checksum: {hex_str} ❌")

        # Sau 20 lần thành công thì tổng kết
        if success_count >= 20:
            print()
            print(f"  ✅ Sensor hoạt động tốt! ({success_count}/{read_count} lần OK)")
            break

except KeyboardInterrupt:
    print()
    print(f"\nDừng. Kết quả: {success_count} OK / {fail_count} lỗi / {read_count} tổng")

finally:
    ser.close()
    print()
    if success_count > 0:
        print("✅ CẢM BIẾN NỐI ĐÚNG — hoạt động bình thường!")
        print("   Đổi SENSOR_ENABLED = True trong config.py rồi chạy chương trình chính.")
    else:
        print("❌ CẢM BIẾN KHÔNG HOẠT ĐỘNG")
        print("   Kiểm tra lại:")
        print("   - Đỏ  → Pin 2 (5V)")
        print("   - Đen → Pin 9 (GND)")
        print("   - Xanh lá → Pin 29 (GPIO5)")
        print("   - Xanh lương → KHÔNG NỐI")
