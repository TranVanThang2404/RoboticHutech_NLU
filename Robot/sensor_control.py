# ===== Ultrasonic Sensor Control Module =====
import RPi.GPIO as GPIO
import time
from config import *

class UltrasonicSensor:
    """Xử lý cảm biến siêu âm HC-SR04"""
    
    def __init__(self, trig_pin, echo_pin, name="Sensor"):
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        self.name = name
        self.distance = 0
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.trig_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        
        # Đặt trigger thấp ban đầu
        GPIO.output(self.trig_pin, GPIO.LOW)
        time.sleep(0.3)
        
        if DEBUG_MODE:
            print(f"[{self.name}] Khởi tạo thành công (TRIG: {trig_pin}, ECHO: {echo_pin})")
    
    def get_distance(self):
        """
        Tính khoảng cách từ cảm biến
        Trả về khoảng cách (cm)
        """
        try:
            # Gửi xung
            GPIO.output(self.trig_pin, GPIO.HIGH)
            time.sleep(0.00001)  # 10 µs
            GPIO.output(self.trig_pin, GPIO.LOW)
            
            # Đợi tín hiệu echo
            timeout = 0.04  # 40ms timeout
            start_time = time.time()
            
            while GPIO.input(self.echo_pin) == GPIO.LOW:
                start_pulse = time.time()
                if (start_pulse - start_time) > timeout:
                    return 999  # Out of range
            
            while GPIO.input(self.echo_pin) == GPIO.HIGH:
                end_pulse = time.time()
                if (end_pulse - start_time) > timeout:
                    return 999  # Out of range
            
            # Tính khoảng cách: distance = (time * speed_of_sound) / 2
            pulse_duration = end_pulse - start_pulse
            distance = (pulse_duration * 34300) / 2  # 34300 cm/s là tốc độ âm thanh
            distance = round(distance, 2)
            
            self.distance = distance
            return distance
            
        except Exception as e:
            if DEBUG_MODE:
                print(f"[{self.name}] Lỗi: {e}")
            return 999
    
    def is_obstacle_detected(self, threshold=SAFE_DISTANCE):
        """Kiểm tra có chướng ngại vật không"""
        return self.distance < threshold
    
    def cleanup(self):
        """Dọn dẹp"""
        GPIO.cleanup()


class SensorManager:
    """Quản lý cảm biến siêu âm"""
    
    def __init__(self):
        self.center_sensor = UltrasonicSensor(ULTRASONIC_CENTER_TRIG, ULTRASONIC_CENTER_ECHO, "Center Sensor")
        
        self.obstacles = {
            'center': False
        }
        
        if DEBUG_MODE:
            print("[SensorManager] Khởi tạo xong với 1 cảm biến")
    
    def update_sensors(self):
        """Cập nhật trạng thái cảm biến"""
        center_dist = self.center_sensor.get_distance()
        
        self.obstacles['center'] = center_dist < SAFE_DISTANCE
        
        if DEBUG_MODE:
            print(f"[Sensors] C: {center_dist}cm")
        
        return {
            'center': center_dist
        }
    
    def is_any_obstacle(self):
        """Kiểm tra có chướng ngại vật không"""
        return self.obstacles['center']
    
    def cleanup(self):
        """Dọn dẹp"""
        try:
            GPIO.cleanup()
        except:
            pass
