"""
person_tracker.py — Person detection + Re-ID tracking cho Follow Me.

Kiến trúc:
  PersonDetector  — phát hiện tất cả người trong frame
                    Backend ưu tiên: YOLOv8n (ultralytics)
                    Fallback tự động: OpenCV HOG

  TargetTracker   — đăng ký một người dùng bộ descriptor đa đặc trưng
                    rồi theo dõi họ frame-by-frame đúng người
                    dù xung quanh có nhiều người khác.

Descriptor Re-ID (tối ưu cho góc nhìn sau lưng — follow-me):
  Nhóm 1 — Màu sắc (HSV Hue 16 + Sat 8 bins × 5 vùng = 120 dims)
  Nhóm 2 — Texture lưng (gradient orientation 8 bins × 5 vùng = 40 dims)
            → phân biệt logo, vân áo, sọc, kẻ ô phía sau
  Nhóm 3 — Vóc dáng (aspect ratio height/width → 8 soft bins = 8 dims)
            → phân biệt người cao/thấp, mập/gầy
  Tổng: 168 chiều, cosine similarity

  5 vùng dọc ưu tiên đặc trưng lưng:
    đầu/tóc (0.10) | vai/lưng-trên (0.35) | lưng-dưới/eo (0.25)
    đùi (0.20)     | cẳng chân (0.10)

Multi-template gallery:
  - Lưu tối đa GALLERY_SIZE snapshot descriptor tại các thời điểm khác nhau
  - Similarity = max(cosine_sim(gallery_i, candidate)) qua toàn bộ gallery
  - Snapshot mới được thêm mỗi GALLERY_UPDATE_INTERVAL giây
    chỉ khi sim ≥ GALLERY_MIN_SIM (tránh lưu frame nhiễu)
  - Khi đầy gallery, snapshot cũ nhất bị thay thế (FIFO)
  → Hệ thống dần thích nghi khi người mặc áo khoác, đổi áo,
    hay bước qua vùng ánh sáng khác không bị mất theo.

  Đăng ký: có thêm xác minh khuôn mặt (nếu cài face_recognition)
            để đảm bảo đăng ký đúng người ngay từ đầu.
  Theo dõi: không dùng face (robot luôn thấy lưng), chỉ dùng descriptor.
"""

import time
import cv2
import numpy as np

# ---- Descriptor shape ----
_N_HUE   = 16   # hue bins / region           (màu sắc chính)
_N_SAT   = 8    # saturation bins / region    (độ bão hòa màu)
_N_GRAD  = 8    # gradient orientation bins   (texture lưng)
_N_REG   = 5    # số vùng dọc
_N_SHAPE = 8    # bins cho aspect ratio       (vóc dáng)

# Chiều descriptor: (16+8+8)*5 + 8 = 168
_DESC_COLOR_TEX = (_N_HUE + _N_SAT + _N_GRAD) * _N_REG   # 160
_DESC_DIM       = _DESC_COLOR_TEX + _N_SHAPE              # 168

# Trọng số 5 vùng dọc — ưu tiên vai/lưng-trên (đặc trưng nhất khi follow)
# đầu/tóc | vai/lưng-trên | lưng-dưới/eo | đùi | cẳng chân
_REGION_WEIGHTS = [0.10, 0.35, 0.25, 0.20, 0.10]


# ============================================================
#  Detection backends
# ============================================================

class _YOLODetector:
    """YOLOv8n person detector (ultralytics)."""

    def __init__(self, confidence: float = 0.40):
        import os
        import logging
        logging.getLogger("ultralytics").setLevel(logging.WARNING)
        os.environ["YOLO_VERBOSE"] = "False"
        from ultralytics import YOLO
        _model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yolov8n.pt")
        self.model = YOLO(_model_path)
        self.conf  = confidence
        print("[DETECTOR] YOLOv8n ready  (YOLO backend)")

    def detect(self, frame: np.ndarray) -> list:
        """Trả về list (x1, y1, x2, y2) của mọi người phát hiện được."""
        h, w    = frame.shape[:2]
        results = self.model(frame, classes=[0], conf=self.conf, verbose=False)[0]
        bboxes  = []
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            x1 = max(0, x1);  y1 = max(0, y1)
            x2 = min(w, x2);  y2 = min(h, y2)
            if (x2 - x1) > 10 and (y2 - y1) > 20:
                bboxes.append((x1, y1, x2, y2))
        return bboxes


class _ONNXDetector:
    """YOLOv8n person detector dùng ONNX Runtime — nhẹ, không cần torch."""

    def __init__(self, confidence: float = 0.40):
        import os
        import onnxruntime as ort
        _model_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "yolov8n.onnx"
        )
        if not os.path.isfile(_model_path):
            raise FileNotFoundError(f"Không tìm thấy {_model_path}")
        self.session = ort.InferenceSession(
            _model_path,
            providers=["CPUExecutionProvider"],
        )
        self.conf       = confidence
        self._input_name = self.session.get_inputs()[0].name
        # YOLOv8n ONNX input: (1, 3, 640, 640)
        self._imgsz     = 640
        print(f"[DETECTOR] YOLOv8n ONNX ready  (onnxruntime CPU)")

    def _preprocess(self, frame: np.ndarray):
        """Letterbox resize + normalize → (1,3,640,640) float32."""
        h, w = frame.shape[:2]
        sz   = self._imgsz
        scale = min(sz / h, sz / w)
        nh, nw = int(h * scale), int(w * scale)
        img = cv2.resize(frame, (nw, nh))

        pad_h = sz - nh
        pad_w = sz - nw
        top    = pad_h // 2
        left   = pad_w // 2
        img = cv2.copyMakeBorder(
            img, top, pad_h - top, left, pad_w - left,
            cv2.BORDER_CONSTANT, value=(114, 114, 114),
        )
        img = img[:, :, ::-1].transpose(2, 0, 1).astype(np.float32) / 255.0
        return img[np.newaxis], scale, top, left

    def detect(self, frame: np.ndarray) -> list:
        h, w = frame.shape[:2]
        blob, scale, pad_top, pad_left = self._preprocess(frame)
        outputs = self.session.run(None, {self._input_name: blob})
        # output shape: (1, 84, 8400) — 84 = 4 bbox + 80 classes
        preds = outputs[0][0]          # (84, 8400)
        preds = preds.T               # (8400, 84)

        # Class 0 = person
        scores = preds[:, 4:]          # (8400, 80)
        person_scores = scores[:, 0]   # class 0 = person
        mask = person_scores >= self.conf
        preds  = preds[mask]
        person_scores = person_scores[mask]

        if len(preds) == 0:
            return []

        # cx, cy, bw, bh → x1, y1, x2, y2 (trong ảnh 640×640 letterboxed)
        cx = preds[:, 0]
        cy = preds[:, 1]
        bw = preds[:, 2]
        bh = preds[:, 3]
        x1 = cx - bw / 2
        y1 = cy - bh / 2
        x2 = cx + bw / 2
        y2 = cy + bh / 2

        # Chuyển về tọa độ ảnh gốc
        x1 = ((x1 - pad_left) / scale).astype(int)
        y1 = ((y1 - pad_top)  / scale).astype(int)
        x2 = ((x2 - pad_left) / scale).astype(int)
        y2 = ((y2 - pad_top)  / scale).astype(int)

        # NMS đơn giản
        bboxes = []
        for i in range(len(x1)):
            bx1 = max(0, int(x1[i]));  by1 = max(0, int(y1[i]))
            bx2 = min(w, int(x2[i]));  by2 = min(h, int(y2[i]))
            if (bx2 - bx1) > 10 and (by2 - by1) > 20:
                bboxes.append((bx1, by1, bx2, by2))
        return _nms(bboxes)


def _nms(bboxes: list, thresh: float = 0.60) -> list:
    """IoU-based Non-Maximum Suppression (dùng cho HOG)."""
    if not bboxes:
        return []
    boxes  = np.array(bboxes, dtype=float)
    x1, y1, x2, y2 = boxes[:,0], boxes[:,1], boxes[:,2], boxes[:,3]
    areas  = (x2 - x1 + 1) * (y2 - y1 + 1)
    order  = areas.argsort()[::-1]
    keep   = []
    while order.size > 0:
        i = order[0]; keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w_  = np.maximum(0.0, xx2 - xx1 + 1)
        h_  = np.maximum(0.0, yy2 - yy1 + 1)
        iou = (w_ * h_) / (areas[i] + areas[order[1:]] - w_ * h_ + 1e-9)
        order = order[np.where(iou <= thresh)[0] + 1]
    return [bboxes[i] for i in keep]


class _HOGDetector:
    """OpenCV HOG person detector — fallback không cần cài thêm gói."""

    def __init__(self):
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        print("[DETECTOR] OpenCV HOG ready  (fallback backend — kém chính xác hơn YOLO)")

    def detect(self, frame: np.ndarray) -> list:
        h, w   = frame.shape[:2]
        scale  = 480.0 / max(h, w)
        small  = cv2.resize(frame, (max(1, int(w * scale)), max(1, int(h * scale))))
        rects, _ = self.hog.detectMultiScale(
            small, winStride=(8, 8), padding=(4, 4), scale=1.05
        )
        bboxes = []
        for (x, y, rw, rh) in (rects if len(rects) else []):
            x1 = int(x / scale);          y1 = int(y / scale)
            x2 = int((x + rw) / scale);   y2 = int((y + rh) / scale)
            bboxes.append((x1, y1, x2, y2))
        return _nms(bboxes)


def create_detector(backend: str = "yolo", confidence: float = 0.40):
    """
    Factory: tạo detector tốt nhất có thể.

    backend:
      "onnx" → ONNX Runtime (nhẹ, không cần torch — ưu tiên cho RPi)
      "yolo" → ultralytics YOLO (cần torch)
      "hog"  → OpenCV HOG (fallback)

    Thứ tự fallback: onnx → yolo → hog
    """
    if backend.lower() == "onnx":
        try:
            return _ONNXDetector(confidence)
        except (ImportError, FileNotFoundError, Exception) as e:
            print(f"[DETECTOR] ONNX không khả dụng ({e}), thử YOLO...")
            try:
                return _YOLODetector(confidence)
            except (ImportError, Exception):
                print("[DETECTOR] YOLO cũng không khả dụng, dùng HOG")
                return _HOGDetector()
    if backend.lower() == "yolo":
        try:
            return _YOLODetector(confidence)
        except (ImportError, Exception) as e:
            print(f"[DETECTOR] YOLO không khả dụng ({e}), thử ONNX...")
            try:
                return _ONNXDetector(confidence)
            except (ImportError, FileNotFoundError, Exception):
                print("[DETECTOR] ONNX cũng không khả dụng, dùng HOG")
                return _HOGDetector()
    return _HOGDetector()


# ============================================================
#  Appearance descriptor (Re-ID features)
# ============================================================

def extract_appearance(frame: np.ndarray, bbox: tuple) -> np.ndarray:
    """
    Trích xuất descriptor Re-ID đa đặc trưng tối ưu cho góc nhìn sau lưng.

    3 nhóm đặc trưng:
      1. Màu sắc     — HSV Hue (16 bins) + Saturation (8 bins) × 5 vùng = 120 dims
      2. Texture lưng— gradient orientation (8 bins) × 5 vùng            =  40 dims
                       phân biệt logo, vân áo, sọc, kẻ ô phía sau
      3. Vóc dáng    — aspect ratio height/width → 8 soft bins            =   8 dims
                       phân biệt người cao/thấp, mập/gầy
    Tổng: 168 chiều, cosine similarity.

    5 vùng dọc với trọng số ưu tiên lưng trên (đặc trưng nhất khi follow):
      đầu/tóc (0.10) | vai/lưng-trên (0.35) | lưng-dưới/eo (0.25)
      đùi (0.20)     | cẳng chân (0.10)

    Returns:
        np.ndarray shape (168,), normalized float32
    """
    x1, y1, x2, y2 = bbox
    x1 = max(0, x1);  y1 = max(0, y1)
    x2 = min(frame.shape[1] - 1, max(x1 + 1, x2))
    y2 = min(frame.shape[0] - 1, max(y1 + 1, y2))

    roi_bgr = frame[y1:y2, x1:x2]
    if roi_bgr.size == 0:
        return np.zeros(_DESC_DIM, dtype=np.float32)

    rh, rw   = roi_bgr.shape[:2]
    roi_hsv  = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    roi_gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)

    # --- Gradient orientation map (tính 1 lần cho toàn ROI) ---
    sx       = cv2.Sobel(roi_gray, cv2.CV_32F, 1, 0, ksize=3)
    sy       = cv2.Sobel(roi_gray, cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = np.sqrt(sx * sx + sy * sy)
    grad_ang = np.arctan2(sy, sx) + np.pi   # [0, 2π]

    # --- Ranh giới 5 vùng dọc ---
    cuts = [
        0,
        int(rh * 0.12),   # đầu/tóc
        int(rh * 0.40),   # vai/lưng trên
        int(rh * 0.62),   # lưng dưới/eo
        int(rh * 0.82),   # đùi
        rh,               # cẳng chân
    ]

    parts = []
    for i, w_reg in enumerate(_REGION_WEIGHTS):
        r0, r1 = cuts[i], cuts[i + 1]
        zero_feat = np.zeros(_N_HUE + _N_SAT + _N_GRAD, dtype=np.float32)
        if r1 <= r0:
            parts.append(zero_feat)
            continue

        seg_hsv = roi_hsv[r0:r1, :]
        seg_mag = grad_mag[r0:r1, :]
        seg_ang = grad_ang[r0:r1, :]

        # Màu sắc: Hue + Saturation
        h_hist = cv2.calcHist([seg_hsv], [0], None, [_N_HUE], [0, 180]).flatten().astype(np.float32)
        s_hist = cv2.calcHist([seg_hsv], [1], None, [_N_SAT], [0, 256]).flatten().astype(np.float32)
        h_n = np.linalg.norm(h_hist); h_hist /= (h_n + 1e-9)
        s_n = np.linalg.norm(s_hist); s_hist /= (s_n + 1e-9)

        # Texture: histogram hướng gradient có trọng số theo cường độ
        # → vùng có cạnh rõ (logo, sọc, viền) đóng góp nhiều hơn vùng phẳng
        g_hist = np.histogram(
            seg_ang.flatten(), bins=_N_GRAD, range=(0.0, 2 * np.pi),
            weights=seg_mag.flatten()
        )[0].astype(np.float32)
        g_n = np.linalg.norm(g_hist); g_hist /= (g_n + 1e-9)

        parts.append(np.concatenate([h_hist, s_hist, g_hist]) * w_reg)

    # --- Vóc dáng: aspect ratio height/width → soft binning ---
    # Người đứng thường có height/width ≈ 2.0–5.0
    aspect  = rh / max(rw, 1)
    asp_n   = np.clip((aspect - 1.5) / 3.5, 0.0, 1.0)   # normalize về [0, 1]
    shape_feat = np.zeros(_N_SHAPE, dtype=np.float32)
    idx = min(int(asp_n * _N_SHAPE), _N_SHAPE - 1)
    shape_feat[idx] = 1.0
    if idx + 1 < _N_SHAPE:
        frac = asp_n * _N_SHAPE - idx
        shape_feat[idx]     *= (1.0 - frac * 0.5)
        shape_feat[idx + 1]  = frac * 0.5

    desc = np.concatenate(parts + [shape_feat])
    n = np.linalg.norm(desc)
    if n > 1e-9:
        desc /= n
    return desc.astype(np.float32)


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity trong [0, 1] (0=khác hoàn toàn, 1=giống nhau)."""
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return float(np.clip(np.dot(a, b) / (na * nb), 0.0, 1.0))


# ============================================================
#  Face Verifier (tùy chọn — cần cài face_recognition)
# ============================================================

class FaceVerifier:
    """
    Xác minh khuôn mặt tại bước đăng ký người dùng.

    Cài đặt: pip install face_recognition
    Nếu chưa cài → tự động bỏ qua.

    Mục đích:
      - Lúc đăng ký: hệ thống yêu cầu người dùng quay mặt vào camera
        để có thể lưu face encoding — xác nhận đúng người bước đầu.
      - Lúc follow: không dùng face (robot luôn thấy lưng), chỉ dùng descriptor.
    """

    def __init__(self):
        self._available = False
        try:
            import face_recognition as _fr
            self._fr = _fr
            self._available = True
            print("[FACE] face_recognition sẵn sàng — xác minh khuôn mặt BẬT")
        except ImportError:
            print("[FACE] face_recognition chưa cài — chỉ dùng Re-ID màu sắc")

    @property
    def available(self) -> bool:
        return self._available

    def encode(self, frame: np.ndarray, bbox: tuple):
        """
        Trích xuất face encoding (128-dim) từ vùng bbox người.

        Returns:
            np.ndarray shape (128,) hoặc None nếu không tìm thấy khuôn mặt.
        """
        if not self._available:
            return None
        x1, y1, x2, y2 = bbox
        x1 = max(0, x1);  y1 = max(0, y1)
        x2 = min(frame.shape[1], x2);  y2 = min(frame.shape[0], y2)
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return None
        rgb  = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        locs = self._fr.face_locations(rgb, model="hog")
        if not locs:
            return None
        encs = self._fr.face_encodings(rgb, locs)
        return encs[0] if encs else None

    def verify(self,
               frame: np.ndarray,
               bbox: tuple,
               registered_enc: np.ndarray,
               tolerance: float = 0.50) -> tuple:
        """
        So sánh khuôn mặt trong bbox với encoding đã đăng ký.

        Args:
            tolerance: khoảng cách tối đa để chấp nhận (0–1; nhỏ = khó tính hơn).
                       face_recognition mặc định 0.60; dùng 0.50 để chính xác hơn.
        Returns:
            (face_found: bool, is_match: bool)
              face_found=False → không thấy mặt  → không chặn
              face_found=True, is_match=True  → đúng người
              face_found=True, is_match=False → người khác → chặn
        """
        if not self._available or registered_enc is None:
            return False, True   # không xác minh được → không chặn
        enc = self.encode(frame, bbox)
        if enc is None:
            return False, True   # không tìm thấy mặt → không chặn
        match = self._fr.compare_faces(
            [registered_enc], enc, tolerance=tolerance
        )[0]
        return True, bool(match)


# ============================================================
#  Target Tracker
# ============================================================

class TargetTracker:
    """
    Theo dõi một người đã đăng ký trong môi trường nhiều người,
    có khả năng thích nghi khi người thay đổi trang phục dần dần.

    Chiến lược tránh nhầm người:
      1. Multi-template gallery: lưu N snapshot tại các thời điểm khác nhau
         Similarity = max(sim với từng template) → thích nghi áo khoác/đổi áo
      2. Bonus vị trí (+12%) cho bbox gần vị trí cuối biết
      3. Gallery chỉ cập nhật khi similarity ≥ GALLERY_MIN_SIM
         → tránh lưu frame nhiễu hoặc người khác vào gallery
      4. Đăng ký: lưu face encoding (xác nhận đúng người đầu phiên)
         Theo dõi: không dùng face — robot luôn thấy lưng

    Cach dùng:
        tracker = TargetTracker()
        ok, msg = tracker.register_from_frame(frame, detector)
        result  = tracker.find_target(frame, detector)
        if result:
            bbox, (cx, cy), similarity = result
    """

    def __init__(self,
                 similarity_threshold: float = 0.40,
                 face_tolerance: float = 0.50,
                 gallery_size: int = 6,
                 gallery_update_interval: float = 4.0,
                 gallery_min_sim: float = 0.55):
        self._threshold               = similarity_threshold
        self._face_tolerance          = face_tolerance
        self._gallery_size            = gallery_size
        self._gallery_update_interval = gallery_update_interval
        self._gallery_min_sim         = gallery_min_sim

        self._gallery             = []     # list[np.ndarray] — tối đa gallery_size entries
        self._registered          = False
        self._last_bbox           = None
        self._last_center         = None
        self._last_gallery_update = 0.0   # timestamp lần cuối thêm snapshot
        self._face_verifier       = FaceVerifier()
        self._face_encoding       = None

    # ---- Public API -------------------------------------------------

    @property
    def is_registered(self) -> bool:
        return self._registered

    @property
    def gallery_count(self) -> int:
        """Số snapshot hiện có trong gallery."""
        return len(self._gallery)

    def register_from_frame(self, frame: np.ndarray, detector) -> tuple:
        """
        Tự động phát hiện và đăng ký người nổi bật nhất trong frame.

        Tiêu chí chọn: kết hợp gần tâm frame (55%) và diện tích lớn (45%).

        Returns:
            (success: bool, message: str)
        """
        bboxes = detector.detect(frame)
        if not bboxes:
            return False, "Không phát hiện người nào trong khung hình"

        h, w = frame.shape[:2]
        frame_area = w * h
        best_score = -1.0
        best_bbox  = None

        for bbox in bboxes:
            x1, y1, x2, y2 = bbox
            cx   = (x1 + x2) / 2.0
            cy   = (y1 + y2) / 2.0
            area = (x2 - x1) * (y2 - y1)

            dist_n   = (
                ((cx - w / 2) / (w / 2)) ** 2 +
                ((cy - h / 2) / (h / 2)) ** 2
            ) ** 0.5 / (2 ** 0.5)
            center_s = 1.0 - dist_n
            area_s   = area / frame_area

            score = 0.55 * center_s + 0.45 * area_s
            if score > best_score:
                best_score = score
                best_bbox  = bbox

        if best_bbox is None:
            return False, "Không chọn được mục tiêu"

        self._do_register(frame, best_bbox)
        x1, y1, x2, y2 = best_bbox
        area_pct = int(((x2 - x1) * (y2 - y1)) / frame_area * 100)
        return True, f"Đã đăng ký mục tiêu (diện tích ≈ {area_pct}% khung hình)"

    def register_from_gallery(self, descriptors: list, face_enc=None, bboxes: list = None):
        """
        Đăng ký người từ gallery đã chụp trước (multi-capture).

        Args:
            descriptors: list[np.ndarray] — 6 descriptor đã extract sẵn
            face_enc: face encoding (nếu có) từ snapshot đầu tiên
            bboxes: list[tuple] — bbox gốc (dùng lấy last_center)

        Returns:
            (success: bool, message: str)
        """
        if not descriptors:
            return False, "Không có descriptor nào"

        self._gallery     = [d.copy() for d in descriptors]
        self._registered  = True
        self._face_encoding = face_enc
        self._last_gallery_update = time.time()

        if bboxes and bboxes[-1]:
            x1, y1, x2, y2 = bboxes[-1]
            self._last_bbox   = bboxes[-1]
            self._last_center = ((x1 + x2) // 2, (y1 + y2) // 2)

        if face_enc is not None:
            print("[TRACKER] Đã đăng ký khuôn mặt từ multi-capture")
        print(f"[TRACKER] Multi-capture register — gallery={len(self._gallery)}/{self._gallery_size}")
        return True, f"Đăng ký thành công ({len(self._gallery)} mẫu)"

    def find_target(self, frame: np.ndarray, detector):
        """
        Tìm người đã đăng ký trong frame hiện tại.

        Thuật toán:
          1. Phát hiện tất cả người (1 lần duy nhất)
          2. Mỗi candidate: sim = max(cosine_sim(gallery_i, desc))
             + position bonus
          3. Chọn candidate có tổng điểm cao nhất
          4. Nếu sim thuần ≥ threshold → xác nhận
          5. Cập nhật gallery nếu đủ điều kiện

        Returns:
            (result, all_bboxes) — luôn trả tuple 2 phần tử
              result    : (bbox, (cx, cy), best_sim) nếu tìm thấy, None nếu không
              all_bboxes: list tất cả bbox phát hiện trong frame (để vẽ overlay,
                          tái sử dụng — tránh gọi detector 2 lần)
        """
        if not self._registered or not self._gallery:
            return None, []

        bboxes = detector.detect(frame)
        if not bboxes:
            return None, []

        best_total = -1.0
        best_bbox  = None
        best_desc  = None   # descriptor của winner — tránh tính lại lần 2
        best_sim   = 0.0    # gallery_sim thuần của winner (không có pos_bonus)

        for bbox in bboxes:
            desc = extract_appearance(frame, bbox)

            # Similarity = max qua toàn bộ gallery
            gallery_sim = max(cosine_sim(t, desc) for t in self._gallery)

            # Position bonus
            pos_bonus = 0.0
            if self._last_center is not None:
                x1, y1, x2, y2 = bbox
                cx   = (x1 + x2) / 2.0
                cy   = (y1 + y2) / 2.0
                dist = ((cx - self._last_center[0]) ** 2 +
                        (cy - self._last_center[1]) ** 2) ** 0.5
                pos_bonus = max(0.0, (1.0 - dist / 250.0)) * 0.12

            total = gallery_sim + pos_bonus
            if total > best_total:
                best_total = total
                best_bbox  = bbox
                best_desc  = desc        # cache — không cần tính lại sau vòng lặp
                best_sim   = gallery_sim # similarity thuần (không có bonus)

        if best_bbox is None:
            return None, bboxes

        # Kiểm tra similarity thuần (không có bonus) — dùng lại descriptor đã tính
        raw_desc = best_desc
        raw_sim  = best_sim
        if raw_sim < self._threshold:
            return None, bboxes

        # ---- Cập nhật tracker state ----
        x1, y1, x2, y2   = best_bbox
        cx, cy            = (x1 + x2) // 2, (y1 + y2) // 2
        self._last_bbox   = best_bbox
        self._last_center = (cx, cy)

        # ---- Cập nhật gallery (nếu đủ thời gian và đủ tự tin) ----
        now = time.time()
        if (raw_sim >= self._gallery_min_sim and
                now - self._last_gallery_update >= self._gallery_update_interval):
            self._add_to_gallery(raw_desc)
            self._last_gallery_update = now
            print(f"[GALLERY] Snapshot thêm — gallery={len(self._gallery)}/{self._gallery_size}  "
                  f"sim={raw_sim:.3f}")

        return (best_bbox, (cx, cy), raw_sim), bboxes

    def reset(self):
        """Xóa đăng ký, quay về trạng thái ban đầu."""
        self._gallery             = []
        self._registered          = False
        self._last_bbox           = None
        self._last_center         = None
        self._last_gallery_update = 0.0
        self._face_encoding       = None
        print("[TRACKER] Target registration cleared")

    # ---- Private -------------------------------------------------------

    def _add_to_gallery(self, desc: np.ndarray):
        """Thêm descriptor vào gallery; nếu đầy thì xóa entry cũ nhất (FIFO)."""
        if len(self._gallery) >= self._gallery_size:
            self._gallery.pop(0)
        self._gallery.append(desc.copy())

    def _do_register(self, frame: np.ndarray, bbox: tuple):
        desc              = extract_appearance(frame, bbox)
        self._gallery     = [desc]
        self._registered  = True
        x1, y1, x2, y2   = bbox
        self._last_bbox   = bbox
        self._last_center = ((x1 + x2) // 2, (y1 + y2) // 2)
        self._last_gallery_update = time.time()
        # --- Đăng ký khuôn mặt ---
        self._face_encoding = self._face_verifier.encode(frame, bbox)
        if self._face_encoding is not None:
            print("[TRACKER] Đã đăng ký khuôn mặt  (face verification BẬT)")
        else:
            print("[TRACKER] Không phát hiện khuôn mặt khi đăng ký — chỉ dùng Re-ID")
        print(f"[TRACKER] Đăng ký xong — gallery=1/{self._gallery_size}  "
              f"bbox={bbox}  center={self._last_center}")
