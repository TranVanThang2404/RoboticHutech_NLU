# ===== Test Script - Kiểm tra từng module =====
import time
import sys

def test_motor():
    """Kiểm tra điều khiển động cơ"""
    print("\n" + "="*50)
    print("TEST: MOTOR CONTROL")
    print("="*50)
    
    try:
        from motor_control import MotorControl
        motor = MotorControl()
        
        print("→ Đi tiến 3 giây...")
        motor.move_forward(60)
        time.sleep(3)
        
        print("→ Quay trái 2 giây...")
        motor.turn_left(50)
        time.sleep(2)
        
        print("→ Quay phải 2 giây...")
        motor.turn_right(50)
        time.sleep(2)
        
        print("→ Lùi 2 giây...")
        motor.move_backward(50)
        time.sleep(2)
        
        print("→ Dừng lại")
        motor.stop()
        
        motor.cleanup()
        print("✅ Test Motor PASS")
        return True
    
    except Exception as e:
        print(f"❌ Test Motor FAIL: {e}")
        return False


def test_sensors():
    """Kiểm tra cảm biến"""
    print("\n" + "="*50)
    print("TEST: ULTRASONIC SENSORS")
    print("="*50)
    
    try:
        from sensor_control import SensorManager
        sensors = SensorManager()
        
        print("→ Đọc cảm biến trong 10 giây...")
        for i in range(10):
            data = sensors.update_sensors()
            print(f"  [{i+1}] L: {data['left']:6.2f}cm | C: {data['center']:6.2f}cm | R: {data['right']:6.2f}cm")
            time.sleep(1)
        
        sensors.cleanup()
        print("✅ Test Sensors PASS")
        return True
    
    except Exception as e:
        print(f"❌ Test Sensors FAIL: {e}")
        return False


def test_camera():
    """Kiểm tra camera"""
    print("\n" + "="*50)
    print("TEST: CAMERA DETECTION")
    print("="*50)
    
    try:
        from camera_detection import PersonDetector
        import cv2
        
        camera = PersonDetector()
        
        print("→ Chạy detect person trong 10 giây...")
        print("  (Nếu window camera xuất hiện, nhấn 'q' để thoát)")
        
        for i in range(10 * 30):  # 10 giây @ 30 FPS
            camera.detect_person()
            frame = camera.get_frame()
            
            if frame is not None:
                frame_display = camera.draw_detections(frame)
                cv2.imshow('Robot Camera', frame_display)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            if (i + 1) % 30 == 0:
                print(f"  [{i+1}] Person detected: {camera.person_detected}")
        
        cv2.destroyAllWindows()
        camera.release()
        print("✅ Test Camera PASS")
        return True
    
    except Exception as e:
        print(f"❌ Test Camera FAIL: {e}")
        return False


def test_all():
    """Chạy tất cả test"""
    print("\n")
    print("╔" + "="*48 + "╗")
    print("║" + " "*10 + "ROBOTIC HUTECH NLU - TEST SUITE" + " "*7 + "║")
    print("╚" + "="*48 + "╝")
    
    results = {}
    
    # Test motor
    results['Motor'] = test_motor()
    input("\n→ Nhấn Enter để test Sensors...")
    
    # Test sensors
    results['Sensors'] = test_sensors()
    input("\n→ Nhấn Enter để test Camera...")
    
    # Test camera
    results['Camera'] = test_camera()
    
    # Tóm tắt kết quả
    print("\n" + "="*50)
    print("KẾT QUẢ TEST")
    print("="*50)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:20} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*50)
    if all_passed:
        print("🎉 TẤT CẢ TEST ĐỀU PASS - SẲN SÀNG CHẠY!")
    else:
        print("⚠️ CÓ SỰ CỐ - KIỂM TRA LẠI CẤU HÌNH")
    print("="*50)


if __name__ == "__main__":
    try:
        test_all()
    except KeyboardInterrupt:
        print("\n\n❌ Test bị hủy bởi người dùng")
