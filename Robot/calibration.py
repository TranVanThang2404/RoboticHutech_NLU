# ===== Calibration Tools =====
# Công cụ hiệu chỉnh cảm biến, motor, và camera

import time
import cv2
from motor_control import MotorControl
from sensor_control import SensorManager, UltrasonicSensor
from camera_detection import PersonDetector
from config import *

class CalibrationTool:
    """Công cụ hiệu chỉnh robot"""
    
    @staticmethod
    def calibrate_motors():
        """Hiệu chỉnh motor - kiểm tra cả hai quay đều"""
        print("\n" + "="*50)
        print("HIỆU CHỈNH MOTOR")
        print("="*50)
        
        motor = MotorControl()
        
        print("\nTest Motor Trái...")
        print("  → Đi tiến 5 giây")
        motor.set_motor_speed(60, 0)
        time.sleep(5)
        motor.stop()
        
        input("  ✓ Bấm Enter nếu bánh trái quay tốt...")
        
        print("\nTest Motor Phải...")
        print("  → Đi tiến 5 giây")
        motor.set_motor_speed(0, 60)
        time.sleep(5)
        motor.stop()
        
        input("  ✓ Bấm Enter nếu bánh phải quay tốt...")
        
        print("\nTest cả 2 motor (nên đi thẳng)")
        print("  → Đi tiến 3 giây")
        motor.move_forward(60)
        time.sleep(3)
        motor.stop()
        
        print("\n✅ Hoàn thành hiệu chỉnh motor")
        motor.cleanup()
    
    @staticmethod
    def calibrate_sensors():
        """Hiệu chỉnh cảm biến siêu âm"""
        print("\n" + "="*50)
        print("HIỆU CHỈNH CẢM BIẾN SIÊU ÂM")
        print("="*50)
        
        sensors = SensorManager()
        
        print("\n⚠️ Cảm biến sẽ đọc trong 30 giây")
        print("   Di chuyển tay bạn ở các khoảng cách khác nhau")
        print("   để kiểm tra độ chính xác\n")
        
        time.sleep(2)
        
        readings = {
            'left': [],
            'center': [],
            'right': []
        }
        
        for i in range(30):
            data = sensors.update_sensors()
            readings['left'].append(data['left'])
            readings['center'].append(data['center'])
            readings['right'].append(data['right'])
            
            print(f"[{i+1:2d}s] L: {data['left']:6.2f}cm | C: {data['center']:6.2f}cm | R: {data['right']:6.2f}cm")
            time.sleep(1)
        
        # Tính toán thống kê
        print("\n📊 THỐNG KÊ:")
        for name, values in readings.items():
            avg = sum(values) / len(values)
            min_val = min(values)
            max_val = max(values)
            print(f"  {name.upper():6} - Avg: {avg:6.2f}cm | Min: {min_val:6.2f}cm | Max: {max_val:6.2f}cm")
        
        print("\n✅ Hoàn thành hiệu chỉnh cảm biến")
        sensors.cleanup()
    
    @staticmethod
    def calibrate_camera():
        """Hiệu chỉnh camera - test phát hiện người"""
        print("\n" + "="*50)
        print("HIỆU CHỈNH CAMERA")
        print("="*50)
        
        camera = PersonDetector()
        
        print("\n📷 Camera sẽ chạy trong 30 giây")
        print("   Thử nghiệm phát hiện người")
        print("   Nhấn 'q' để dừng\n")
        
        detected_frames = 0
        total_frames = 0
        
        start_time = time.time()
        
        while time.time() - start_time < 30:
            camera.detect_person()
            frame = camera.get_frame()
            total_frames += 1
            
            if camera.person_detected:
                detected_frames += 1
            
            if frame is not None:
                frame_display = camera.draw_detections(frame)
                
                # Thêm thông tin lên frame
                text = f"Detected: {camera.person_detected} | Offset: {camera.get_horizontal_offset() or 0:.0f}px"
                cv2.putText(frame_display, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Vẽ đường trung tâm
                h, w = frame.shape[:2]
                cv2.line(frame_display, (w//2, 0), (w//2, h), (255, 0, 0), 2)
                
                cv2.imshow('Camera Calibration', frame_display)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        
        cv2.destroyAllWindows()
        
        detection_rate = (detected_frames / total_frames * 100) if total_frames > 0 else 0
        print(f"\n📊 THỐNG KÊ:")
        print(f"  Tổng frame: {total_frames}")
        print(f"  Frame phát hiện: {detected_frames}")
        print(f"  Tỷ lệ phát hiện: {detection_rate:.1f}%")
        
        if detection_rate > 80:
            print("\n✅ Camera hoạt động TỐT")
        elif detection_rate > 50:
            print("\n⚠️ Camera hoạt động TRUNG BÌNH - Cân nhắc điều chỉnh CONFIDENCE_THRESHOLD")
        else:
            print("\n❌ Camera hoạt động TỪ TỪ - Kiểm tra ánh sáng hoặc model")
        
        camera.release()
    
    @staticmethod
    def calibrate_motor_speed():
        """Hiệu chỉnh cân bằng tốc độ giữa 2 motor"""
        print("\n" + "="*50)
        print("CÂN BẰNG TỐC ĐỘ MOTOR")
        print("="*50)
        
        motor = MotorControl()
        
        print("\n📏 Đo khoảng cách đi thẳng của xe")
        print("   Xe sẽ đi tiến 10 giây, bạn đo xem lệch bao nhiêu\n")
        
        input("  Bấm Enter khi sẵn sàng (đặt xe xa tường)...")
        
        print("  → Đi tiến 10 giây...")
        motor.move_forward(60)
        time.sleep(10)
        motor.stop()
        
        print("\n  Nếu lệch sang trái:")
        print("    → Giảm MOTOR_LEFT_PWM hoặc tăng MOTOR_RIGHT_PWM")
        print("  Nếu lệch sang phải:")
        print("    → Tăng MOTOR_LEFT_PWM hoặc giảm MOTOR_RIGHT_PWM")
        print("\n  (Điều chỉnh trong config.py hoặc motor_control.py)\n")
        
        motor.cleanup()
    
    @staticmethod
    def calibrate_confidence():
        """Tìm ngưỡng confidence tối ưu"""
        print("\n" + "="*50)
        print("TÌMÔI NGƯỠNG DETECT TỐI ƯU")
        print("="*50)
        
        camera = PersonDetector()
        
        thresholds_to_test = [0.3, 0.4, 0.5, 0.6, 0.7]
        
        print("\nKiểm tra các ngưỡng confidence khác nhau:")
        print("(Bạn sẽ thay đổi ngưỡng thủ công trong config.py)\n")
        
        for threshold in thresholds_to_test:
            print(f"\n📊 Threshold = {threshold}")
            print(f"  Hiện tại: CONFIDENCE_THRESHOLD = {CONFIDENCE_THRESHOLD}")
            print(f"  Thay đổi thành: CONFIDENCE_THRESHOLD = {threshold}")
            
            input("  → Bấn Enter khi đã thay đổi...")
            
            detected = 0
            total = 0
            
            for _ in range(100):
                camera.detect_person()
                total += 1
                if camera.person_detected:
                    detected += 1
            
            print(f"  → Detection rate: {detected}%")
        
        camera.release()
        print("\n✅ Chọn ngưỡng có detection rate phù hợp")


def main():
    """Menu hiệu chỉnh"""
    while True:
        print("\n" + "="*50)
        print("  CÔNG CỤ HIỆU CHỈNH ROBOT")
        print("="*50)
        print("1. Hiệu chỉnh Motor")
        print("2. Hiệu chỉnh Cảm biến")
        print("3. Hiệu chỉnh Camera")
        print("4. Cân bằng tốc độ Motor")
        print("5. Tìm ngưỡng Confidence tối ưu")
        print("0. Thoát")
        print("-"*50)
        
        choice = input("Chọn (0-5): ").strip()
        
        try:
            if choice == '1':
                CalibrationTool.calibrate_motors()
            elif choice == '2':
                CalibrationTool.calibrate_sensors()
            elif choice == '3':
                CalibrationTool.calibrate_camera()
            elif choice == '4':
                CalibrationTool.calibrate_motor_speed()
            elif choice == '5':
                CalibrationTool.calibrate_confidence()
            elif choice == '0':
                print("\n👋 Tạm biệt!")
                break
            else:
                print("❌ Lựa chọn không hợp lệ")
        
        except KeyboardInterrupt:
            print("\n\n❌ Bị dừng")
        
        except Exception as e:
            print(f"\n❌ Lỗi: {e}")
        
        input("\n← Bấm Enter để tiếp tục...")


if __name__ == "__main__":
    main()
