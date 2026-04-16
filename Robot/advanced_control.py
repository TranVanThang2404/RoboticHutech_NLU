# ===== Advanced Robot Control =====
# Các tính năng nâng cao: PID Control, Multi-threading, Web Control

import time
import threading
from motor_control import MotorControl
from sensor_control import SensorManager
from camera_detection import PersonDetector
from config import *

class PIDController:
    """PID Controller để điều chỉnh tốc độ động cơ chính xác"""
    
    def __init__(self, kp=1.0, ki=0.5, kd=0.1):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
        self.prev_error = 0
        self.integral = 0
        self.last_time = time.time()
    
    def update(self, error):
        """
        Tính toán PID output
        error: sai số hiện tại
        return: PID output
        """
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time
        
        # Proportional
        p_term = self.kp * error
        
        # Integral
        self.integral += error * dt
        i_term = self.ki * self.integral
        
        # Derivative
        if dt > 0:
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0
        d_term = self.kd * derivative
        
        self.prev_error = error
        
        output = p_term + i_term + d_term
        return output


class AdvancedRobot:
    """Robot nâng cao với PID control"""
    
    def __init__(self):
        print("=" * 60)
        print("  KHỞI ĐỘNG XE NÂNG CAO - PID CONTROL")
        print("=" * 60)
        
        self.motor = MotorControl()
        self.sensors = SensorManager()
        self.camera = PersonDetector()
        
        # PID cho điều khiển ngang
        self.pid_steering = PIDController(kp=0.5, ki=0.1, kd=0.2)
        
        self.is_running = False
        self.person_lost_time = 0
        self.follow_mode = False
        self.current_speed = NORMAL_SPEED
        
        # Threading
        self.sensor_thread = None
        self.camera_thread = None
        self.lock = threading.Lock()
        
        self.sensor_data = {
            'left': 0,
            'center': 0,
            'right': 0
        }
        
        self.camera_data = {
            'person_detected': False,
            'offset': 0
        }
        
        print("[Robot] Khởi tạo xong!")
    
    def sensor_worker(self):
        """Thread cập nhật cảm biến"""
        while self.is_running:
            data = self.sensors.update_sensors()
            with self.lock:
                self.sensor_data = data
            time.sleep(0.1)
    
    def camera_worker(self):
        """Thread xử lý camera"""
        while self.is_running:
            detected = self.camera.detect_person()
            offset = self.camera.get_horizontal_offset() or 0
            
            with self.lock:
                self.camera_data['person_detected'] = detected
                self.camera_data['offset'] = offset
            
            time.sleep(1 / CAMERA_FPS)
    
    def pid_steering_control(self):
        """Điều khiển bánh lái bằng PID"""
        with self.lock:
            offset = self.camera_data['offset']
            person_detected = self.camera_data['person_detected']
        
        if not person_detected:
            return
        
        # Tính PID output từ offset
        pid_output = self.pid_steering.update(offset)
        
        # Giới hạn output
        pid_output = max(-50, min(50, pid_output))
        
        # Điều khiển motor
        left_speed = self.current_speed - pid_output
        right_speed = self.current_speed + pid_output
        
        self.motor.set_motor_speed(left_speed, right_speed)
        
        if DEBUG_MODE and int(time.time() * 10) % 10 == 0:
            print(f"[PID] Offset: {offset:6.1f} | Output: {pid_output:6.1f}")
    
    def obstacle_detection_worker(self):
        """Phát hiện chướng ngại vật"""
        with self.lock:
            data = self.sensor_data.copy()
        
        left_dist = data['left']
        center_dist = data['center']
        right_dist = data['right']
        
        # Kiểm tra chướng ngại vật ở giữa
        if center_dist < STOP_DISTANCE:
            if DEBUG_MODE:
                print(f"[OBSTACLE] Chướng ngại vật phía trước! ({center_dist}cm)")
            self.motor.stop()
            time.sleep(0.5)
            # Lùi một chút
            self.motor.move_backward(TURN_SPEED)
            time.sleep(1)
            # Quay trái
            self.motor.turn_left(TURN_SPEED)
            time.sleep(1)
            return True
        
        return False
    
    def run_advanced(self):
        """Vòng lặp chính nâng cao"""
        self.is_running = True
        
        # Khởi động threads
        self.sensor_thread = threading.Thread(target=self.sensor_worker, daemon=True)
        self.camera_thread = threading.Thread(target=self.camera_worker, daemon=True)
        
        self.sensor_thread.start()
        self.camera_thread.start()
        
        print("[Robot] Threads khởi động")
        print("[Robot] Bắt đầu chạy (Chế độ nâng cao)!\n")
        
        try:
            while self.is_running:
                # Kiểm tra chướng ngại vật
                if self.obstacle_detection_worker():
                    continue
                
                # Nếu chưa phát hiện người
                with self.lock:
                    if not self.camera_data['person_detected']:
                        if DEBUG_MODE:
                            print("🔍 Quét tìm người...")
                        self.motor.turn_right(TURN_SPEED)
                    else:
                        # PID steering control
                        self.pid_steering_control()
                
                time.sleep(1 / CAMERA_FPS)
        
        except KeyboardInterrupt:
            print("\n[Robot] Dừng bởi người dùng")
            self.is_running = False
        
        except Exception as e:
            print(f"[Robot] Lỗi: {e}")
            self.is_running = False
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Dọn dẹp"""
        print("\n[Robot] Đang dọn dẹp...")
        self.is_running = False
        self.motor.stop()
        self.motor.cleanup()
        self.sensors.cleanup()
        self.camera.release()
        print("[Robot] Dọn dẹp xong!")


# ===== Web Control Interface (Optional) =====

class WebRobotControl:
    """Điều khiển robot qua web (Flask)"""
    
    def __init__(self, robot):
        self.robot = robot
        try:
            from flask import Flask, jsonify, request
            
            self.app = Flask(__name__)
            
            @self.app.route('/status')
            def status():
                return jsonify({
                    'is_running': self.robot.is_running,
                    'current_speed': self.robot.current_speed,
                    'person_detected': self.robot.camera_data['person_detected'],
                    'sensor_data': self.robot.sensor_data
                })
            
            @self.app.route('/control/<action>')
            def control(action):
                if action == 'forward':
                    self.robot.motor.move_forward(self.robot.current_speed)
                elif action == 'backward':
                    self.robot.motor.move_backward(self.robot.current_speed)
                elif action == 'left':
                    self.robot.motor.turn_left(self.robot.current_speed)
                elif action == 'right':
                    self.robot.motor.turn_right(self.robot.current_speed)
                elif action == 'stop':
                    self.robot.motor.stop()
                elif action == 'speed_up':
                    self.robot.current_speed = min(self.robot.current_speed + 10, MAX_SPEED)
                elif action == 'speed_down':
                    self.robot.current_speed = max(self.robot.current_speed - 10, MIN_SPEED)
                
                return jsonify({'status': 'ok', 'action': action})
            
            print("[Web] Flask app initialized")
        
        except ImportError:
            print("[Web] Flask not installed. Web control disabled.")
            self.app = None
    
    def run(self, host='0.0.0.0', port=5000):
        """Chạy web server"""
        if self.app:
            print(f"[Web] Server chạy tại http://{host}:{port}")
            self.app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    robot = AdvancedRobot()
    
    try:
        robot.run_advanced()
    except Exception as e:
        print(f"Lỗi: {e}")
        robot.cleanup()
