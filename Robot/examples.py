# ===== EXAMPLE PROGRAMS - CÁC VÍ DỤ CHỰC NĂNG =====

# ===== EXAMPLE 1: Simple Manual Control =====
"""
Ví dụ 1: Điều khiển thủ công đơn giản
"""
from motor_control import MotorControl
import time

def example_manual_control():
    motor = MotorControl()
    
    print("🎮 Manual Motor Control Example")
    
    # Đi tiến
    print("→ Forward 3 seconds")
    motor.move_forward(70)
    time.sleep(3)
    
    # Quay trái
    print("← Turn left 2 seconds")
    motor.turn_left(60)
    time.sleep(2)
    
    # Quay phải
    print("→ Turn right 2 seconds")
    motor.turn_right(60)
    time.sleep(2)
    
    # Lùi
    print("← Backward 2 seconds")
    motor.move_backward(70)
    time.sleep(2)
    
    # Dừng
    motor.stop()
    motor.cleanup()
    
    print("✅ Complete!")


# ===== EXAMPLE 2: Sensor Reading =====
"""
Ví dụ 2: Đọc dữ liệu từ cảm biến
"""
from sensor_control import SensorManager
import time

def example_sensor_reading():
    sensors = SensorManager()
    
    print("📡 Ultrasonic Sensor Reading Example")
    print("Reading for 10 seconds...\n")
    
    for i in range(10):
        data = sensors.update_sensors()
        print(f"[{i+1}s] Left: {data['left']:6.2f}cm | Center: {data['center']:6.2f}cm | Right: {data['right']:6.2f}cm")
        time.sleep(1)
    
    sensors.cleanup()
    print("\n✅ Complete!")


# ===== EXAMPLE 3: Person Detection =====
"""
Ví dụ 3: Phát hiện người từ camera
"""
from camera_detection import PersonDetector
import cv2
import time

def example_person_detection():
    camera = PersonDetector()
    
    print("👤 Person Detection Example")
    print("Running for 10 seconds... Press 'q' to quit\n")
    
    start_time = time.time()
    
    while time.time() - start_time < 10:
        camera.detect_person()
        frame = camera.get_frame()
        
        if frame is not None:
            frame_display = camera.draw_detections(frame)
            
            # Add info
            text = f"Detected: {'YES' if camera.person_detected else 'NO'} | Offset: {camera.get_horizontal_offset() or 0:.0f}px"
            cv2.putText(frame_display, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.imshow('Person Detection', frame_display)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    cv2.destroyAllWindows()
    camera.release()
    print("\n✅ Complete!")


# ===== EXAMPLE 4: Obstacle Avoidance =====
"""
Ví dụ 4: Tránh chướng ngại vật
"""
from motor_control import MotorControl
from sensor_control import SensorManager
import time

def example_obstacle_avoidance():
    motor = MotorControl()
    sensors = SensorManager()
    
    print("🛣️ Obstacle Avoidance Example")
    print("Robot will move forward and avoid obstacles for 30 seconds\n")
    
    start_time = time.time()
    
    while time.time() - start_time < 30:
        # Đi tiến
        motor.move_forward(60)
        
        # Kiểm tra cảm biến
        data = sensors.update_sensors()
        
        # Nếu có chướng ngại ở giữa, lùi và quay
        if data['center'] < 20:
            print(f"⚠️ Obstacle at center ({data['center']:.1f}cm) - Reversing...")
            motor.move_backward(50)
            time.sleep(1)
            
            # Quay trái nếu phía phải trống hơn
            if data['right'] > data['left']:
                motor.turn_left(50)
                time.sleep(1)
            else:
                motor.turn_right(50)
                time.sleep(1)
        
        # Nếu có chướng ngại ở trái, quay phải
        elif data['left'] < 25 and data['right'] > 25:
            print(f"⚠️ Obstacle at left ({data['left']:.1f}cm) - Turning right...")
            motor.turn_right(50)
            time.sleep(0.5)
        
        # Nếu có chướng ngại ở phải, quay trái
        elif data['right'] < 25 and data['left'] > 25:
            print(f"⚠️ Obstacle at right ({data['right']:.1f}cm) - Turning left...")
            motor.turn_left(50)
            time.sleep(0.5)
        
        print(f"L: {data['left']:5.1f}cm | C: {data['center']:5.1f}cm | R: {data['right']:5.1f}cm")
        time.sleep(0.5)
    
    motor.stop()
    motor.cleanup()
    sensors.cleanup()
    print("\n✅ Complete!")


# ===== EXAMPLE 5: Motor Speed Adjustment =====
"""
Ví dụ 5: Điều chỉnh tốc độ động cơ
"""
from motor_control import MotorControl
import time

def example_speed_adjustment():
    motor = MotorControl()
    
    print("⚡ Motor Speed Adjustment Example")
    print("Testing different speed levels...\n")
    
    speeds = [30, 50, 70, 90, 100]
    
    for speed in speeds:
        print(f"→ Moving forward at {speed}%")
        motor.move_forward(speed)
        time.sleep(2)
    
    print("\nDecreasing speed...")
    for speed in speeds[::-1]:
        print(f"→ Moving forward at {speed}%")
        motor.move_forward(speed)
        time.sleep(1)
    
    motor.stop()
    motor.cleanup()
    print("\n✅ Complete!")


# ===== EXAMPLE 6: Combined Operation =====
"""
Ví dụ 6: Vận hành kết hợp - Di chuyển theo cảm biến + Camera
"""
from motor_control import MotorControl
from sensor_control import SensorManager
from camera_detection import PersonDetector
import time
import cv2

def example_combined():
    motor = MotorControl()
    sensors = SensorManager()
    camera = PersonDetector()
    
    print("🤖 Combined Operation Example")
    print("Robot will move while checking for person and obstacles\n")
    
    runtime = 0
    
    try:
        while runtime < 30:
            # Check for obstacles
            sensor_data = sensors.update_sensors()
            
            if sensor_data['center'] < 20:
                print("⚠️ Obstacle! Stopping...")
                motor.stop()
                time.sleep(1)
                motor.turn_right(50)
                time.sleep(1)
                continue
            
            # Check for person
            camera.detect_person()
            
            if camera.person_detected:
                print("👤 Person detected! Following...")
                offset = camera.get_horizontal_offset()
                
                if offset < -50:
                    motor.turn_left(60)
                elif offset > 50:
                    motor.turn_right(60)
                else:
                    motor.move_forward(60)
            else:
                print("🔍 Scanning for person...")
                motor.turn_right(40)
            
            time.sleep(1)
            runtime += 1
    
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    
    finally:
        motor.stop()
        motor.cleanup()
        sensors.cleanup()
        camera.release()
        cv2.destroyAllWindows()
        print("✅ Complete!")


# ===== MENU =====
def main():
    print("\n" + "="*50)
    print("  ROBOTIC HUTECH - EXAMPLE PROGRAMS")
    print("="*50 + "\n")
    
    examples = {
        '1': ('Manual Motor Control', example_manual_control),
        '2': ('Sensor Reading', example_sensor_reading),
        '3': ('Person Detection', example_person_detection),
        '4': ('Obstacle Avoidance', example_obstacle_avoidance),
        '5': ('Speed Adjustment', example_speed_adjustment),
        '6': ('Combined Operation', example_combined),
    }
    
    for key, (name, _) in examples.items():
        print(f"{key}. {name}")
    
    print("0. Exit\n")
    
    choice = input("Select example (0-6): ").strip()
    
    if choice in examples:
        name, func = examples[choice]
        print(f"\n▶️  Running: {name}\n")
        print("-" * 50 + "\n")
        
        try:
            func()
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        print("\n" + "-" * 50)
    
    elif choice == '0':
        print("👋 Goodbye!")
    
    else:
        print("❌ Invalid choice")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Run specific example by number
        example_num = sys.argv[1]
        examples = {
            '1': example_manual_control,
            '2': example_sensor_reading,
            '3': example_person_detection,
            '4': example_obstacle_avoidance,
            '5': example_speed_adjustment,
            '6': example_combined,
        }
        
        if example_num in examples:
            print(f"\n▶️  Running example {example_num}\n")
            examples[example_num]()
        else:
            print(f"❌ Example {example_num} not found")
    else:
        main()
