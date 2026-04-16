# ===== Camera Detection Module =====
import cv2
import numpy as np
from config import *
import os

class PersonDetector:
    """Phát hiện người từ camera USB"""
    
    def __init__(self):
        # Khởi tạo camera
        self.cap = cv2.VideoCapture(CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
        
        # Tải mô hình YOLOv3-tiny cho phát hiện người
        self._load_yolo_model()
        
        self.person_detected = False
        self.person_position = None
        self.person_bbox = None
        self.frame = None
        
        if DEBUG_MODE:
            print("[Camera] Khởi tạo camera thành công")
    
    def _load_yolo_model(self):
        """Tải mô hình YOLO"""
        try:
            # Đường dẫn đến các file YOLO
            weights_path = "yolov3-tiny.weights"
            config_path = "yolov3-tiny.cfg"
            names_path = "coco.names"
            
            # Nếu chưa có file, sử dụng phương pháp thay thế đơn giản
            if not os.path.exists(weights_path):
                if DEBUG_MODE:
                    print("[Camera] Không tìm thấy YOLO weights, sử dụng MobileNet SSD thay thế")
                self._use_mobilenet_ssd()
                return
            
            self.net = cv2.dnn.readNet(weights_path, config_path)
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            
            # Tải tên classes
            with open(names_path, 'r') as f:
                self.classes = [line.strip() for line in f.readlines()]
            
            self.layer_names = self.net.getLayerNames()
            self.output_layers = [self.layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
            
            self.use_yolo = True
            if DEBUG_MODE:
                print("[Camera] YOLO model loaded successfully")
                
        except Exception as e:
            if DEBUG_MODE:
                print(f"[Camera] Lỗi load YOLO: {e}")
            self._use_mobilenet_ssd()
    
    def _use_mobilenet_ssd(self):
        """Sử dụng MobileNet SSD nếu YOLO không có"""
        try:
            # Tải MobileNet SSD từ OpenCV
            proto_path = "MobileNetSSD_deploy.prototxt.txt"
            model_path = "MobileNetSSD_deploy.caffemodel"
            
            if os.path.exists(proto_path) and os.path.exists(model_path):
                self.net = cv2.dnn.readNetFromCaffe(proto_path, model_path)
                self.use_yolo = False
                if DEBUG_MODE:
                    print("[Camera] MobileNet SSD loaded")
            else:
                # Dùng haar cascade để detect người nếu không có model
                self.use_yolo = False
                self.use_hog = True
                self.hog = cv2.HOGDescriptor()
                self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
                if DEBUG_MODE:
                    print("[Camera] Sử dụng HOG + SVM để detect người")
        except Exception as e:
            if DEBUG_MODE:
                print(f"[Camera] Lỗi: {e}, sử dụng HOG detector")
            self.use_hog = True
            self.hog = cv2.HOGDescriptor()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    
    def detect_person(self):
        """Phát hiện người trong frame hiện tại"""
        ret, frame = self.cap.read()
        
        if not ret:
            if DEBUG_MODE:
                print("[Camera] Lỗi: không đọc được frame")
            return False
        
        self.frame = frame
        h, w = frame.shape[:2]
        
        # Nếu sử dụng YOLO
        if hasattr(self, 'use_yolo') and self.use_yolo:
            return self._detect_yolo(frame, h, w)
        
        # Nếu sử dụng HOG
        elif hasattr(self, 'use_hog') and self.use_hog:
            return self._detect_hog(frame, h, w)
        
        else:
            return False
    
    def _detect_yolo(self, frame, h, w):
        """Phát hiện bằng YOLO"""
        # Tạo blob
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        self.net.setInput(blob)
        outs = self.net.forward(self.output_layers)
        
        class_ids = []
        confidences = []
        boxes = []
        
        # Xử lý output
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                # Chỉ quan tâm đến "person" (class_id = 0 trong COCO)
                if class_id == 0 and confidence > CONFIDENCE_THRESHOLD:
                    center_x = int(detection[0] * w)
                    center_y = int(detection[1] * h)
                    width = int(detection[2] * w)
                    height = int(detection[3] * h)
                    x = center_x - width // 2
                    y = center_y - height // 2
                    
                    boxes.append([x, y, width, height])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
        
        # Non-maxima suppression
        indexes = cv2.dnn.NMSBoxes(boxes, confidences, CONFIDENCE_THRESHOLD, 0.4)
        
        if len(indexes) > 0:
            # Lấy detection đầu tiên (gần nhất)
            idx = indexes[0][0]
            x, y, w, h = boxes[idx]
            self.person_bbox = (x, y, w, h)
            self.person_position = (x + w // 2, y + h // 2)
            self.person_detected = True
            return True
        
        self.person_detected = False
        return False
    
    def _detect_hog(self, frame, h, w):
        """Phát hiện bằng HOG"""
        (rects, weights) = self.hog.detectMultiScale(frame, winStride=(4, 4), padding=(8, 8), scale=1.05)
        
        if len(rects) > 0:
            # Lấy detection với weight cao nhất
            idx = np.argmax(weights)
            (x, y, w, h) = rects[idx]
            self.person_bbox = (x, y, w, h)
            self.person_position = (x + w // 2, y + h // 2)
            self.person_detected = True
            return True
        
        self.person_detected = False
        return False
    
    def get_person_center(self):
        """Lấy tọa độ trung tâm của người (pixels)"""
        if self.person_detected and self.person_position:
            return self.person_position
        return None
    
    def get_frame_center(self):
        """Lấy tọa độ trung tâm của frame"""
        if self.frame is not None:
            h, w = self.frame.shape[:2]
            return (w // 2, h // 2)
        return None
    
    def get_horizontal_offset(self):
        """
        Tính offset ngang của người từ trung tâm frame
        Âm = bên trái, Dương = bên phải
        """
        person_pos = self.get_person_center()
        frame_center = self.get_frame_center()
        
        if person_pos and frame_center:
            return person_pos[0] - frame_center[0]
        return None
    
    def get_frame(self):
        """Lấy frame hiện tại"""
        return self.frame
    
    def draw_detections(self, frame=None):
        """Vẽ bounding box lên frame (cho debugging)"""
        if frame is None:
            frame = self.frame.copy()
        else:
            frame = frame.copy()
        
        if self.person_detected and self.person_bbox:
            x, y, w, h = self.person_bbox
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(frame, self.person_position, 5, (0, 255, 0), -1)
            
            # Vẽ đường trung tâm
            h_frame = frame.shape[0]
            w_frame = frame.shape[1]
            cv2.line(frame, (w_frame // 2, 0), (w_frame // 2, h_frame), (255, 0, 0), 1)
        
        return frame
    
    def release(self):
        """Đóng camera"""
        self.cap.release()
        if DEBUG_MODE:
            print("[Camera] Camera đã được đóng")


if __name__ == "__main__":
    """Test camera detection"""
    print("Testing camera detection...")
    
    detector = PersonDetector()
    
    try:
        for i in range(10):  # Test 10 frames
            detected = detector.detect_person()
            if detected:
                offset = detector.get_horizontal_offset()
                print(f"Frame {i+1}: Person detected at offset {offset}")
            else:
                print(f"Frame {i+1}: No person detected")
            
            # Wait a bit
            import time
            time.sleep(0.8)
    
    except KeyboardInterrupt:
        print("Test interrupted")
    
    finally:
        detector.release()
        print("Test completed")
