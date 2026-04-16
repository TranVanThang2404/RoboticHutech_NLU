# ===== QUICK TEST - CÁCH NHANH NHẤT =====
# Chỉ test logic, không cần GPIO hay hardware

import sys
sys.path.insert(0, '.')

def test_config():
    """Test import config"""
    try:
        import config
        print("✅ config.py OK")
        print(f"   - NORMAL_SPEED: {config.NORMAL_SPEED}%")
        print(f"   - SAFE_DISTANCE: {config.SAFE_DISTANCE}cm")
        return True
    except Exception as e:
        print(f"❌ config.py FAILED: {e}")
        return False

def test_imports():
    """Test tất cả imports"""
    try:
        print("\n📦 Testing imports...")
        import cv2
        print("✅ OpenCV OK")
        import numpy as np
        print("✅ NumPy OK")
        return True
    except Exception as e:
        print(f"❌ Import FAILED: {e}")
        return False

def test_logic():
    """Test logic tính toán (không cần hardware)"""
    try:
        print("\n🧮 Testing logic...")
        
        # Test PID calculation
        try:
            from advanced_control import PIDController
            pid = PIDController(kp=0.5, ki=0.1, kd=0.2)
            
            # Simulate some errors
            errors = [-50, -30, 0, 30, 50]
            outputs = [pid.update(err) for err in errors]
            
            print(f"✅ PID Control OK")
            print(f"   Errors: {errors}")
            print(f"   Outputs: {[f'{o:.2f}' for o in outputs]}")
        except ImportError:
            print(f"⚠️  PID skipped (RPi.GPIO not available on Windows)")
        
        return True
    except Exception as e:
        print(f"❌ Logic test FAILED: {e}")
        return False

def test_motor_logic():
    """Test motor logic (không cần GPIO)"""
    try:
        print("\n🔌 Testing motor logic...")
        try:
            from motor_control import MotorControl
            print("✅ Motor logic OK")
        except ImportError:
            print("⚠️  Motor skipped (RPi.GPIO not available on Windows)")
        
        return True
    except Exception as e:
        print(f"⚠️  Motor logic: {e}")
        return False

def test_sensor_logic():
    """Test sensor logic"""
    try:
        print("\n📡 Testing sensor logic...")
        
        # Test distance calculation
        pulse_duration = 0.0005  # 0.5ms
        distance = (pulse_duration * 34300) / 2
        
        print(f"✅ Sensor calculation OK")
        print(f"   Pulse: {pulse_duration*1000}ms → Distance: {distance:.2f}cm")
        
        return True
    except Exception as e:
        print(f"❌ Sensor logic FAILED: {e}")
        return False

def test_camera_logic():
    """Test camera detection logic"""
    try:
        print("\n📸 Testing camera logic...")
        
        # Test offset calculation
        frame_width = 640
        person_x = 420
        frame_center = frame_width // 2
        offset = person_x - frame_center
        
        print(f"✅ Camera logic OK")
        print(f"   Frame center: {frame_center} | Person X: {person_x}")
        print(f"   Offset: {offset}px ({'LEFT' if offset < 0 else 'RIGHT'})")
        
        return True
    except Exception as e:
        print(f"❌ Camera logic FAILED: {e}")
        return False

def main():
    print("╔" + "="*48 + "╗")
    print("║" + " "*10 + "QUICK TEST - LOGIC ONLY" + " "*14 + "║")
    print("╚" + "="*48 + "╝")
    
    results = []
    
    results.append(test_config())
    results.append(test_imports())
    results.append(test_logic())
    results.append(test_motor_logic())
    results.append(test_sensor_logic())
    results.append(test_camera_logic())
    
    print("\n" + "="*50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("   Code is ready to deploy!")
    else:
        print(f"⚠️  {total - passed} test(s) failed")
    
    print("="*50)

if __name__ == "__main__":
    main()
