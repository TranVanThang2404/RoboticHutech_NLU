# ===== Motor Control Module =====
import RPi.GPIO as GPIO
import time
from config import *

class MotorControl:
    """Điều khiển các động cơ của xe"""
    
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup pins
        GPIO.setup([MOTOR_LEFT_PIN1, MOTOR_LEFT_PIN2, 
                   MOTOR_RIGHT_PIN1, MOTOR_RIGHT_PIN2], GPIO.OUT)
        
        # Setup PWM
        self.left_pwm = GPIO.PWM(MOTOR_LEFT_PWM, PWM_FREQUENCY)
        self.right_pwm = GPIO.PWM(MOTOR_RIGHT_PWM, PWM_FREQUENCY)
        
        self.left_pwm.start(0)
        self.right_pwm.start(0)
        
        self.current_speed = 0
        self.is_moving = False
        
        if DEBUG_MODE:
            print("[Motor] Khởi tạo thành công")
    
    def set_motor_speed(self, left_speed, right_speed):
        """
        Đặt tốc độ cho động cơ trái và phải
        Speed: 0-100 (%)
        Âm = lùi, Dương = tiến
        """
        # Clamp values
        left_speed = max(-100, min(100, left_speed))
        right_speed = max(-100, min(100, right_speed))
        
        # Left motor
        if left_speed >= 0:
            GPIO.output(MOTOR_LEFT_PIN1, GPIO.HIGH)
            GPIO.output(MOTOR_LEFT_PIN2, GPIO.LOW)
        else:
            GPIO.output(MOTOR_LEFT_PIN1, GPIO.LOW)
            GPIO.output(MOTOR_LEFT_PIN2, GPIO.HIGH)
        self.left_pwm.ChangeDutyCycle(abs(left_speed))
        
        # Right motor
        if right_speed >= 0:
            GPIO.output(MOTOR_RIGHT_PIN1, GPIO.HIGH)
            GPIO.output(MOTOR_RIGHT_PIN2, GPIO.LOW)
        else:
            GPIO.output(MOTOR_RIGHT_PIN1, GPIO.LOW)
            GPIO.output(MOTOR_RIGHT_PIN2, GPIO.HIGH)
        self.right_pwm.ChangeDutyCycle(abs(right_speed))
        
        self.current_speed = (left_speed + right_speed) / 2
        self.is_moving = (left_speed != 0 or right_speed != 0)
        
        if DEBUG_MODE:
            print(f"[Motor] Trái: {left_speed}% | Phải: {right_speed}%")
    
    def move_forward(self, speed=NORMAL_SPEED):
        """Đi tiến"""
        self.set_motor_speed(speed, speed)
    
    def move_backward(self, speed=NORMAL_SPEED):
        """Lùi lại"""
        self.set_motor_speed(-speed, -speed)
    
    def turn_left(self, speed=TURN_SPEED):
        """Quay trái"""
        self.set_motor_speed(speed/2, speed)
    
    def turn_right(self, speed=TURN_SPEED):
        """Quay phải"""
        self.set_motor_speed(speed, speed/2)
    
    def turn_left_sharp(self, speed=TURN_SPEED):
        """Quay trái mạnh (quay tại chỗ)"""
        self.set_motor_speed(-speed, speed)
    
    def turn_right_sharp(self, speed=TURN_SPEED):
        """Quay phải mạnh (quay tại chỗ)"""
        self.set_motor_speed(speed, -speed)
    
    def stop(self):
        """Dừng lại"""
        self.set_motor_speed(0, 0)
        self.is_moving = False
    
    def increase_speed(self, increment=10):
        """Tăng tốc"""
        new_speed = min(self.current_speed + increment, MAX_SPEED)
        self.set_motor_speed(new_speed, new_speed)
    
    def decrease_speed(self, decrement=10):
        """Giảm tốc"""
        new_speed = max(self.current_speed - decrement, 0)
        self.set_motor_speed(new_speed, new_speed)
    
    def cleanup(self):
        """Dọn dẹp GPIO"""
        self.stop()
        self.left_pwm.stop()
        self.right_pwm.stop()
        GPIO.cleanup()
        print("[Motor] Dọn dẹp GPIO xong")
