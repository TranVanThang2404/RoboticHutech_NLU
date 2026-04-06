# ===== ROBOT SCAN & FOLLOW TEST =====
# Simulate robot behavior: Scan → Detect → Follow

import cv2
import sys
import time
sys.path.insert(0, '.')

from camera_detection import PersonDetector

class RobotSimulator:
    """Simulate robot behavior"""

    def __init__(self):
        self.mode = "SCAN"  # SCAN or FOLLOW
        self.scan_direction = "RIGHT"  # LEFT or RIGHT
        self.scan_count = 0
        self.follow_count = 0
        self.person_lost_time = 0

    def scan_behavior(self):
        """Simulate scanning behavior"""
        self.scan_count += 1

        # Simulate turning right to scan
        if self.scan_count % 10 == 0:
            self.scan_direction = "LEFT" if self.scan_direction == "RIGHT" else "RIGHT"

        return f"🔍 SCANNING - Turning {self.scan_direction}"

    def follow_behavior(self, offset):
        """Simulate following behavior"""
        self.follow_count += 1

        if abs(offset) < 50:
            return "➡️ ĐI THẲNG (GO STRAIGHT)"
        elif offset < -50:
            return "⬅️ QUẸO TRÁI (TURN LEFT)"
        else:
            return "➡️ QUẸO PHẢI (TURN RIGHT)"

def main():
    print("╔" + "="*60 + "╗")
    print("║" + " "*15 + "ROBOT SCAN & FOLLOW TEST" + " "*15 + "║")
    print("╚" + "="*60 + "╝\n")

    print("🤖 Simulate robot behavior:")
    print("   🔍 SCAN MODE: Quay tròn tìm người")
    print("   👤 FOLLOW MODE: Theo dõi và điều khiển")
    print("   ⬅️ QUẸO TRÁI: Khi bạn sang trái")
    print("   ➡️ QUẸO PHẢI: Khi bạn sang phải")
    print("   ➡️ ĐI THẲNG: Khi bạn ở giữa\n")

    print("📸 Khởi tạo camera...")
    camera = PersonDetector()
    robot = RobotSimulator()

    print("✅ Sẵn sàng! Đứng trước camera và di chuyển...\n")
    print("-" * 60 + "\n")

    frame_count = 0

    try:
        while frame_count < 100:  # Run for 100 frames
            frame_count += 1

            # Detect person
            detected = camera.detect_person()
            offset = camera.get_horizontal_offset() or 0

            # Robot logic
            if detected:
                robot.person_lost_time = 0

                if robot.mode == "SCAN":
                    print(f"[{frame_count:2d}] 🎯 PHÁT HIỆN NGƯỜI! Chuyển sang FOLLOW MODE")
                    robot.mode = "FOLLOW"

                # Follow behavior
                action = robot.follow_behavior(offset)
                print(f"[{frame_count:2d}] 👤 FOLLOW: {action} (Offset: {offset:6.1f}px)")

            else:
                robot.person_lost_time += 1

                if robot.mode == "FOLLOW" and robot.person_lost_time > 10:
                    print(f"[{frame_count:2d}] ❌ MẤT NGƯỜI! Chuyển sang SCAN MODE")
                    robot.mode = "SCAN"
                    robot.person_lost_time = 0

                if robot.mode == "SCAN":
                    action = robot.scan_behavior()
                    print(f"[{frame_count:2d}] 🔍 SCAN: {action}")

            time.sleep(0.3)  # Slow down for readability

    except KeyboardInterrupt:
        print("\n\n⏹️  Dừng test")

    except Exception as e:
        print(f"\n❌ Lỗi: {e}")

    finally:
        print("\n" + "-" * 60)
        print("\n📊 THỐNG KÊ:")
        print(f"   - Tổng frame: {frame_count}")
        print(f"   - Scan count: {robot.scan_count}")
        print(f"   - Follow count: {robot.follow_count}")
        print(f"   - Mode cuối: {robot.mode}")

        print("\n🔌 Đóng camera...")
        camera.release()
        print("✅ Xong!")


if __name__ == "__main__":
    main()
