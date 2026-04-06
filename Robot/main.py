# ===== Main Robot Control Program =====
import time
import threading
from motor_control import MotorControl
from sensor_control import SensorManager
from camera_detection import PersonDetector
from config import *

class Robot:
    """Lớp chính điều khiển xe tự động"""
    
    def __init__(self):
        print("=" * 50)
        print("  KHỞI ĐỘNG XE TỰ ĐỘNG QUÉT NGƯỜI")
        print("=" * 50)
        
        # Khởi tạo các module
        self.motor = MotorControl()
        self.sensors = SensorManager()
        self.camera = PersonDetector()
        
        # Trạng thái
        self.is_running = False
        self.person_lost_time = 0
        self.follow_mode = False
        self.current_speed = NORMAL_SPEED
        
        print("\n[Robot] Tất cả module đã khởi tạo thành công!")
        print("[Robot] Sẵn sàng bắt đầu quét người\n")
    
    def obstacle_avoidance(self, sensor_data):
        """Tránh chướng ngại vật"""
        left_dist = sensor_data['left']
        center_dist = sensor_data['center']
        right_dist = sensor_data['right']
        
        # Kiểm tra chướng ngại vật ở giữa
        if center_dist < STOP_DISTANCE:
            if DEBUG_MODE:
                print("[Robot] ⚠️ Chướng ngại vật ở giữa - DỪNG!")
            self.motor.stop()
            return True
        
        # Kiểm tra chướng ngại vật ở trái
        if left_dist < SAFE_DISTANCE and right_dist > SAFE_DISTANCE:
            if DEBUG_MODE:
                print("[Robot] ⚠️ Chướng ngại vật bên trái - Quay phải")
            self.motor.turn_right(TURN_SPEED)
            return True
        
        # Kiểm tra chướng ngại vật ở phải
        if right_dist < SAFE_DISTANCE and left_dist > SAFE_DISTANCE:
            if DEBUG_MODE:
                print("[Robot] ⚠️ Chướng ngại vật bên phải - Quay trái")
            self.motor.turn_left(TURN_SPEED)
            return True
        
        return False
    
    def follow_person(self):
        """Theo dõi và đi theo người"""
        # Phát hiện người
        if not self.camera.detect_person():
            self.person_lost_time += 1
            
            # Nếu mất người quá lâu, dừng lại
            if self.person_lost_time > CAMERA_FPS * 3:  # 3 giây
                if DEBUG_MODE:
                    print("[Robot] ❌ Mất tín hiệu người - Dừng lại")
                self.motor.stop()
                self.follow_mode = False
            return
        
        # Tìm thấy người
        self.person_lost_time = 0
        self.follow_mode = True
        
        # Lấy vị trí người
        offset = self.camera.get_horizontal_offset()
        
        if offset is None:
            return
        
        # Cập nhật cảm biến
        sensor_data = self.sensors.update_sensors()
        
        # Tránh chướng ngại vật
        if self.obstacle_avoidance(sensor_data):
            return
        
        # Điều khiển dựa trên vị trí người
        if abs(offset) < CENTER_TOLERANCE:
            # Người ở giữa - đi thẳng
            if DEBUG_MODE:
                print(f"[Robot] ➡️ Theo người thẳng (Speed: {self.current_speed}%)")
            self.motor.move_forward(self.current_speed)
        
        elif offset < -CENTER_TOLERANCE:
            # Người ở bên trái - quay trái
            if DEBUG_MODE:
                print(f"[Robot] ⬅️ Người ở trái - Quay trái (Offset: {offset})")
            self.motor.turn_left(self.current_speed)
        
        else:
            # Người ở bên phải - quay phải
            if DEBUG_MODE:
                print(f"[Robot] ➡️ Người ở phải - Quay phải (Offset: {offset})")
            self.motor.turn_right(self.current_speed)
    
    def scan_mode(self):
        """Chế độ quét: quay tròn tìm người"""
        if DEBUG_MODE:
            print("[Robot] 🔍 Chế độ quét - Tìm kiếm người...")
        
        # Quay tròn tìm người
        self.motor.turn_right(TURN_SPEED)
        
        # Nếu phát hiện người, chuyển sang chế độ follow
        if self.camera.detect_person():
            if DEBUG_MODE:
                print("[Robot] ✅ Phát hiện người - Chuyển sang chế độ theo dõi")
            self.follow_mode = True
    
    def emergency_stop(self):
        """Dừng khẩn cấp"""
        print("[Robot] 🛑 DỪNG KHẨN CẤP!")
        self.motor.stop()
        self.is_running = False
    
    def handle_keyboard_input(self):
        """Xử lý lệnh từ bàn phím nếu cần"""
        try:
            import sys
            key = sys.stdin.read(1)
            
            if key.lower() == 'w':  # Forward
                self.motor.move_forward(self.current_speed)
            elif key.lower() == 's':  # Backward
                self.motor.move_backward(self.current_speed)
            elif key.lower() == 'a':  # Left
                self.motor.turn_left(self.current_speed)
            elif key.lower() == 'd':  # Right
                self.motor.turn_right(self.current_speed)
            elif key.lower() == ' ':  # Stop
                self.motor.stop()
            elif key == '+':  # Increase speed
                self.current_speed = min(self.current_speed + 10, MAX_SPEED)
                print(f"[Robot] Tốc độ: {self.current_speed}%")
            elif key == '-':  # Decrease speed
                self.current_speed = max(self.current_speed - 10, MIN_SPEED)
                print(f"[Robot] Tốc độ: {self.current_speed}%")
            elif key.lower() == 'q':  # Quit
                self.emergency_stop()
        except:
            pass
    
    def run(self):
        """Vòng lặp chính"""
        self.is_running = True
        frame_count = 0
        
        print("[Robot] Bắt đầu chạy!\n")
        print("Các phím điều khiển:")
        print("  W: Tiến, S: Lùi, A: Quay trái, D: Quay phải, Space: Dừng")
        print("  +: Tăng tốc, -: Giảm tốc, Q: Thoát\n")
        
        try:
            while self.is_running:
                frame_count += 1
                
                # Chuyển đổi giữa chế độ quét và theo dõi
                if not self.follow_mode:
                    self.scan_mode()
                else:
                    self.follow_person()
                
                # Kiểm tra cảm biến mỗi 10 frame
                if frame_count % 10 == 0:
                    sensor_data = self.sensors.update_sensors()
                
                time.sleep(1 / CAMERA_FPS)
        
        except KeyboardInterrupt:
            print("\n[Robot] Dừng bởi người dùng")
            self.emergency_stop()
        
        except Exception as e:
            print(f"[Robot] Lỗi: {e}")
            self.emergency_stop()
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Dọn dẹp toàn bộ"""
        print("\n[Robot] Đang dọn dẹp...")
        self.motor.stop()
        self.motor.cleanup()
        self.sensors.cleanup()
        self.camera.release()
        print("[Robot] Dọn dẹp xong. Tạm biệt!")


def main():
    """Hàm chính"""
    robot = Robot()
    
    try:
        robot.run()
    except Exception as e:
        print(f"Lỗi: {e}")
        robot.cleanup()


if __name__ == "__main__":
    main()
