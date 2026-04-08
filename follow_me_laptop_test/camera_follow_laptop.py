"""
camera_follow_laptop.py — Main entry point cho Follow Me Laptop Test MVP.

Luồng hoạt động:
  1. Flask server chạy trong daemon thread
  2. Vòng lặp camera OpenCV trong main thread

Quy trình người dùng:
  a. Mở browser laptop → http://<ip>:5000/
  b. Điện thoại quét QR → mở /pair
  c. Trang /pair yêu cầu người đứng trước camera và nhấn ĐĂNG KÝ
  d. POST /capture_target → camera chụp frame, detect người gần tâm nhất → đăng ký
  e. Hệ thống bắt đầu follow đúng người đó dù xung quanh có nhiều người khác

Phím tắt trong cửa sổ OpenCV:
  Q / ESC  — Thoát
  E        — Toggle Emergency Stop
  O        — Bật/tắt fake obstacle phía TRƯỚC
  [  / ]   — Bật/tắt fake obstacle bên TRÁI / PHẢI
  R        — Reset pairing + đăng ký
"""

import base64
import os
import sys
import threading
import time
from datetime import datetime

# Tắt cảnh báo Qt font (chỉ là warning, không ảnh hưởng)
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")

import config
import cv2
import numpy as np

from person_tracker import TargetTracker, create_detector
from pid_controller import PIDController
from state_manager import State, state_manager
from ultrasonic_mock import ObstacleReading

# ============================================================
#  Dynamic hardware — đổi HARDWARE_MODE trong config.py
#  "raspi"  → RealMotorUART (UART pyserial) + RealUltrasonicArray / MockUltrasonicArray
# ============================================================
if config.HARDWARE_MODE == "raspi":
    from motor_raspi import RealMotorUART as _MotorClass
    if config.SENSOR_ENABLED:
        from ultrasonic_raspi import RealUltrasonicArray as _UltrasonicClass
    else:
        from ultrasonic_mock import MockUltrasonicArray as _UltrasonicClass  # type: ignore
        print("[WARN] SENSOR_ENABLED=False -> dùng MockSensor")
else:
    raise RuntimeError("HARDWARE_MODE chi ho tro 'raspi' sau khi da bo fake motor")

motor      = _MotorClass()
ultrasonic = _UltrasonicClass()


# ============================================================
#  Motor control — Dual PID (Steering + Speed)
# ============================================================

def compute_motor(
    cx: int,
    frame_cx: int,
    bbox_area_ratio: float,
    obs: "ObstacleReading",
    steer_pid: PIDController,
    speed_pid: PIDController,
    dt: float,
):
    """
    Tính tốc độ hai bánh dùng hai PID độc lập + tránh vật cản 3 chiều.

    PID Steering:
      Error  = (cx_người - cx_frame) / cx_frame  ∈ [-1, +1]
      Output = speed differential  (left - right) ∈ [-100, +100]
      left   = base + output
      right  = base - output

    PID Speed (duy trì khoảng cách follow):
      Error  = BBOX_TARGET_RATIO - bbox_area_ratio
      > 0: người quá xa  → tăng tốc
      < 0: người quá gần → giảm tốc
      Output = điều chỉnh thêm vào BASE_SPEED

    Kết hợp với 3 cảm biến siêu âm:
      - Cảm biến giữa: giảm tốc tuyến tính (slow_factor)
      - Cảm biến bên: cưỡng bức steering output tránh tường

    Returns:
        (left_speed, right_speed)
    """
    # ============ PID Speed: tính vận tốc tiến/lùi ============
    speed_err = config.BBOX_TARGET_RATIO - bbox_area_ratio
    if abs(speed_err) < config.BBOX_HOLD_ZONE:
        speed_err = 0.0
    speed_out = speed_pid.compute(speed_err, dt)       # speed units điều chỉnh
    base = int(config.BASE_SPEED + speed_out)
    base = max(config.MIN_SPEED, min(config.MAX_SPEED, base))

    # Giảm tốc theo cảm biến GIỮA (slow_factor: 1.0 → 0.30)
    base = max(config.MIN_SPEED, int(base * obs.slow_factor))

    # ============ PID Steering: tính speed differential ============
    steer_err = (cx - frame_cx) / max(frame_cx, 1)

    # Dead zone: loại bỏ noise nhỏ do detection flickering
    if abs(steer_err) < config.STEERING_DEAD_ZONE:
        steer_err = 0.0
        # Không reset PID, chỉ đưa error = 0 để integral dần về 0

    steer_out = steer_pid.compute(steer_err, dt)       # speed differential

    # Ưu tiên cua mượt: khi xe đang gần như đứng yên/tiến rất chậm thì
    # không cho steering đủ lớn để biến thành quay tại chỗ liên tục.
    if abs(base) < config.STEER_LOW_SPEED_CUTOFF:
        if abs(steer_err) < config.STEER_LOW_SPEED_ERR:
            steer_out = 0.0
        else:
            steer_out *= 0.35

    # ============ Tránh vật cản HAI BÊN (override steering) ============
    abs_base = max(abs(base), 1)
    if obs.left_blocked and not obs.right_blocked:
        # Bên trái bị chặn → buộc rẽ phải (steer_out ≥ SIDE_BIAS)
        steer_out = max(steer_out, config.OBSTACLE_SIDE_BIAS * abs_base)
    elif obs.right_blocked and not obs.left_blocked:
        # Bên phải bị chặn → buộc rẽ trái (steer_out ≤ -SIDE_BIAS)
        steer_out = min(steer_out, -config.OBSTACLE_SIDE_BIAS * abs_base)
    elif obs.left_blocked and obs.right_blocked:
        # Cả hai bị chặn (hẻm hẹp) → đi thẳng + giảm tốc thêm
        steer_out = 0.0
        base = max(config.MIN_SPEED, int(base * 0.50))

    # Khi đang FOLLOWING bình thường, giới hạn chênh lệch hai bánh theo base speed
    # để ưu tiên cua vòng cung thay vì một bánh tiến một bánh lùi.
    if base >= 0:
        steer_out = max(-abs(base), min(abs(base), steer_out))

    # ============ Tổng hợp đầu ra ============
    left_speed  = max(config.MIN_SPEED, min(config.MAX_SPEED,
                      int(base + steer_out)))
    right_speed = max(config.MIN_SPEED, min(config.MAX_SPEED,
                      int(base - steer_out)))
    return left_speed, right_speed


def _ramp_motor_command(prev_left: int, prev_right: int,
                        target_left: int, target_right: int) -> tuple[int, int]:
    """Giới hạn độ thay đổi tốc độ mỗi chu kỳ gửi để xe thật bớt giật."""
    step = max(1, int(config.MOTOR_MAX_DELTA_PER_SEND))
    reverse_brake = max(0, int(getattr(config, "MOTOR_REVERSE_BRAKE_THRESHOLD", 0)))

    def _clamp_delta(prev: int, target: int) -> int:
        # Với xe thật, nếu đang chạy đủ nhanh mà bị đảo chiều ngay thì
        # buộc hãm về 0 trước một nhịp để giảm sốc cơ khí/hộp số.
        if reverse_brake > 0 and prev * target < 0 and abs(prev) >= reverse_brake:
            return 0
        delta = target - prev
        if delta > step:
            return prev + step
        if delta < -step:
            return prev - step
        return target

    return _clamp_delta(prev_left, target_left), _clamp_delta(prev_right, target_right)


# ============================================================
#  Debug overlay
# ============================================================

_STATE_COLORS = {
    State.WAIT_FOR_PAIR:        (90,  90,  90),   # xám
    State.PAIRED_BUT_NO_TARGET: (0,  140, 255),   # cam
    State.FOLLOWING:            (0,  210,  0),    # xanh lá
    State.TARGET_LOST:          (0,   50, 220),   # đỏ
    State.OBSTACLE_STOP:        (30,  30, 200),   # đỏ đậm
    State.EMERGENCY_STOP:       (0,   0, 255),    # đỏ thuần — nhấp nháy
}


def _sensor_bar_color(dist_cm: float) -> tuple:
    """Màu thanh cảm biến: đỏ=stop, cam=slow, vàng=chú ý, xanh=an toàn."""
    if dist_cm < config.OBSTACLE_STOP_CM:
        return (0, 0, 220)     # đỏ
    if dist_cm < config.OBSTACLE_SLOW_CM:
        return (0, 140, 255)   # cam
    if dist_cm < config.SIDE_SAFE_CM * 3:
        return (0, 220, 220)   # vàng
    return (0, 200, 80)        # xanh


def _draw_sensor_bars(frame: np.ndarray, obs: "ObstacleReading"):
    """
    Vẽ 3 thanh cảm biến siêu âm ở góc dưới-phải frame.
    Màu: xanh=an toàn | vàng=chú ý | cam=slow | đỏ=stop
    """
    h, w   = frame.shape[:2]
    bw, bh = 56, 16
    gap    = 6
    base_x = w - (bw * 3 + gap * 2) - 10
    base_y = h - bh - 8
    for i, (label, d) in enumerate([
        ("L", obs.left_cm),
        ("C", obs.center_cm),
        ("R", obs.right_cm),
    ]):
        x     = base_x + i * (bw + gap)
        color = _sensor_bar_color(d)
        cv2.rectangle(frame, (x, base_y), (x + bw, base_y + bh), (20, 20, 20), -1)
        cv2.rectangle(frame, (x, base_y), (x + bw, base_y + bh), color, 2)
        cv2.putText(
            frame, f"{label}:{d:.0f}cm",
            (x + 4, base_y + bh - 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1,
        )


def draw_overlay_lite(frame: np.ndarray, target_bbox, all_bboxes: list,
                     state: str, sim: float):
    """Overlay nhẹ cho GUI mode (7-inch screen) — chỉ bbox + crosshair + 1 dòng state."""
    h, w = frame.shape[:2]

    # Crosshair
    cv2.line(frame, (w // 2 - 20, h // 2), (w // 2 + 20, h // 2), (0, 255, 255), 1)
    cv2.line(frame, (w // 2, h // 2 - 20), (w // 2, h // 2 + 20), (0, 255, 255), 1)

    # Tất cả người
    for bbox in all_bboxes:
        x1, y1, x2, y2 = bbox
        cv2.rectangle(frame, (x1, y1), (x2, y2), (200, 140, 50), 1)

    # Mục tiêu
    if target_bbox is not None:
        x1, y1, x2, y2 = target_bbox
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 0), 2)
        cv2.circle(frame, (cx, cy), 6, (0, 0, 255), -1)
        cv2.putText(frame, f"{sim:.2f}", (x1, max(y1 - 6, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 0), 1)

    # 1 dòng state nhỏ ở góc trên trái
    _STATE_VI = {
        State.WAIT_FOR_PAIR: "San sang",
        State.PAIRED_BUT_NO_TARGET: "Cho dang ky",
        State.FOLLOWING: "FOLLOWING",
        State.TARGET_LOST: "MAT MUC TIEU",
        State.OBSTACLE_STOP: "VAT CAN",
        State.EMERGENCY_STOP: "DUNG KHAN CAP",
    }
    sc = _STATE_COLORS.get(state, (200, 200, 200))
    label = _STATE_VI.get(state, state)
    cv2.putText(frame, label, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, sc, 2)

    if state == State.EMERGENCY_STOP:
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 255), -1)
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

    return frame


def _save_gui_registration_snapshot(frame: np.ndarray, bbox: tuple | None) -> str | None:
    """Lưu ảnh người vừa đăng ký trong GUI mode để tiện kiểm tra lại."""
    if bbox is None:
        return None

    x1, y1, x2, y2 = bbox
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(frame.shape[1], x2)
    y2 = min(frame.shape[0], y2)
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captures")
    os.makedirs(save_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = os.path.join(save_dir, f"target_{ts}.jpg")
    ok = cv2.imwrite(save_path, crop)
    return save_path if ok else None


def draw_overlay(
    frame: np.ndarray,
    target_bbox,
    all_bboxes: list,
    state: str,
    sim: float,
    left: int,
    right: int,
    obs: "ObstacleReading",
    registering: bool,
    gallery_count: int = 0,
    gallery_size: int = 6,
    pid_steer: tuple = (0.0, 0.0, 0.0),   # (P, I, D) steering PID
    pid_speed: tuple = (0.0, 0.0, 0.0),   # (P, I, D) speed PID
):
    """
    Vẽ debug overlay lên frame:
      - Crosshair tâm frame
      - Tất cả bbox người phát hiện (xanh lam nhạt)
      - Bbox mục tiêu (xanh lá đậm + đường nối tâm)
      - Thanh similarity
      - Panel thông tin
      - Flash "REGISTERING..." khi đang đăng ký
    """
    h, w = frame.shape[:2]

    # --- Crosshair ---
    cv2.line(frame, (w // 2 - 30, h // 2), (w // 2 + 30, h // 2), (0, 255, 255), 1)
    cv2.line(frame, (w // 2, h // 2 - 30), (w // 2, h // 2 + 30), (0, 255, 255), 1)

    # --- Tất cả người (bounding box xanh lam nhạt) ---
    for bbox in all_bboxes:
        x1, y1, x2, y2 = bbox
        cv2.rectangle(frame, (x1, y1), (x2, y2), (200, 140, 50), 1)

    # --- Mục tiêu (bounding box xanh lá đậm) ---
    if target_bbox is not None:
        x1, y1, x2, y2 = target_bbox
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        # Viền dày hơn + màu nổi bật
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 0), 3)
        cv2.circle(frame, (cx, cy), 8, (0, 0, 255), -1)
        cv2.line(frame, (w // 2, h // 2), (cx, cy), (50, 50, 255), 2)

        # Label similarity
        cv2.putText(
            frame, f"SIM:{sim:.2f}",
            (x1, max(y1 - 8, 12)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 220, 0), 2,
        )

        # Thanh similarity (dưới bbox)
        bar_w  = x2 - x1
        bar_fill = int(bar_w * min(sim, 1.0))
        cv2.rectangle(frame, (x1, y2 + 4), (x2, y2 + 12), (50, 50, 50), -1)
        cv2.rectangle(frame, (x1, y2 + 4), (x1 + bar_fill, y2 + 12), (0, 220, 0), -1)

    # --- Flash đỏ khi đang đăng ký ---
    if registering:
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 200), -1)
        cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
        cv2.putText(
            frame, "REGISTERING...",
            (w // 2 - 140, h // 2),
            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 100, 255), 3,
        )

    # --- Flash đỏ thuần khi EMERGENCY STOP ---
    if state == State.EMERGENCY_STOP:
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 255), -1)
        cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)
        cv2.putText(
            frame, "!! EMERGENCY STOP !!",
            (w // 2 - 220, h // 2 - 20),
            cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 255), 4,
        )
        cv2.putText(
            frame, "Nhan [E] de tiep tuc",
            (w // 2 - 160, h // 2 + 28),
            cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2,
        )

    # --- Info panel ---
    sc = _STATE_COLORS.get(state, (200, 200, 200))
    panel_h = 220   # 8 dòng x 26px + padding
    cv2.rectangle(frame, (0, 0), (460, panel_h), (10, 10, 10), -1)
    cv2.rectangle(frame, (0, 0), (460, panel_h), sc, 2)

    n_persons = len(all_bboxes)

    # Chú thích hướng di chuyển từ lệnh UART
    if left < 0 and right < 0:
        direction = "LUI      v"     # cả hai bánh lùi
    elif left > 0 and right < 0:
        direction = "XOAY PHAI >>"   # xoay tại chỗ
    elif left < 0 and right > 0:
        direction = "<< XOAY TRAI"   # xoay tại chỗ
    elif left > right:
        direction = "QUEO PHAI ->"   # bánh trái nhanh hơn → xe rẽ phải
    elif left < right:
        direction = "<- QUEO TRAI"   # bánh phải nhanh hơn → xe rẽ trái
    elif left == 0 and right == 0:
        direction = "DUNG     ="
    else:
        direction = "DI THANG  ^"    # hai bánh bằng nhau → đi thẳng

    lines = [
        (f"STATE  : {state}",                              sc,              0.62, 2),
        (f"MOTOR  : L={left:3d}   R={right:3d}  [{direction}]", (240, 240, 240), 0.55, 1),
        (f"[{'FAKE ' if config.HARDWARE_MODE != 'raspi' else ''}UART]  M,{left},{right}  ({direction})",
                                                     (140, 200, 140), 0.52, 1),
        (f"PERSONS: {n_persons}  |  SIM: {sim:.3f}  GALLERY: {gallery_count}/{gallery_size}",
                                                     (180, 210, 255), 0.52, 1),
        (f"DIST  L:{obs.left_cm:5.1f}  C:{obs.center_cm:5.1f}  R:{obs.right_cm:5.1f} cm  [{obs.summary()}]",
                                                     (100, 200, 255), 0.48, 1),
        (f"PID-S: P={pid_steer[0]:+5.1f} I={pid_steer[1]:+5.1f} D={pid_steer[2]:+5.1f}",
                                                     (200, 255, 180), 0.46, 1),
        (f"PID-V: P={pid_speed[0]:+5.1f} I={pid_speed[1]:+5.1f} D={pid_speed[2]:+5.1f}",
                                                     (180, 220, 255), 0.46, 1),
        (f"[Q]Quit [E]Emg [O]Front [[]/]]Side [R]Reset", (120, 120, 120), 0.43, 1),
    ]
    y = 24
    for text, color, scale, thick in lines:
        cv2.putText(frame, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick)
        y += 26

    # --- Thanh cảm biến 3 chiều (góc dưới-phải) ---
    _draw_sensor_bars(frame, obs)

    return frame


# ============================================================
#  Main camera loop
# ============================================================

def camera_loop():
    """
    Vòng lặp camera chính.

    Ba nhiệm vụ:
      1. Kiểm tra registration_requested từ Flask thread
         → gọi tracker.register_from_frame() nếu được yêu cầu
      2. Follow người đã đăng ký (tracker.find_target)
      3. Tính lệnh motor + gửi fake UART
    """
    print(f"\n[CAMERA] Opening camera index {config.CAMERA_INDEX} …")
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        print(f"[CAMERA] ERROR: Không mở được camera index {config.CAMERA_INDEX}")
        print("         Hãy thử thay đổi CAMERA_INDEX trong config.py (0, 1, 2 …)")
        motor.stop()
        motor.close()
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
    try:
        # Giảm frame tồn trong buffer để vòng lặp bám frame mới hơn.
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:
        pass
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[CAMERA] Camera sẵn sàng  {actual_w}x{actual_h}")
    print("[CAMERA] Đang tải person detector…")

    detector = create_detector(config.DETECTOR_BACKEND, config.YOLO_CONFIDENCE)
    tracker  = TargetTracker(
        similarity_threshold=config.SIMILARITY_THRESHOLD,
        face_tolerance=config.FACE_TOLERANCE,
        gallery_size=config.GALLERY_SIZE,
        gallery_update_interval=config.GALLERY_UPDATE_INTERVAL,
        gallery_min_sim=config.GALLERY_MIN_SIM,
    )

    # ---- Hai bộ PID ----
    steer_pid = PIDController(
        kp=config.STEER_KP,
        ki=config.STEER_KI,
        kd=config.STEER_KD,
        integral_limit=config.STEER_INTEGRAL_LIMIT,
        output_limit=config.STEER_OUTPUT_LIMIT,
        deriv_filter_alpha=config.STEER_DERIV_ALPHA,
    )
    speed_pid = PIDController(
        kp=config.SPEED_KP,
        ki=config.SPEED_KI,
        kd=config.SPEED_KD,
        integral_limit=config.SPEED_INTEGRAL_LIMIT,
        output_limit=config.SPEED_OUTPUT_LIMIT,
        deriv_filter_alpha=config.SPEED_DERIV_ALPHA,
    )
    print(f"[PID] Steering: Kp={config.STEER_KP}  Ki={config.STEER_KI}  Kd={config.STEER_KD}")
    print(f"[PID] Speed   : Kp={config.SPEED_KP}  Ki={config.SPEED_KI}  Kd={config.SPEED_KD}")
    print(f"[PID] Bbox target ratio        : {config.BBOX_TARGET_RATIO}")

    print("[CAMERA] Sẵn sàng! Phím: Q=Thoát  E=Emergency  O=Vật cản  R=Reset\n")

    last_seen     = None
    lost_since    = None          # thời điểm bắt đầu TARGET_LOST (cho spin-search)
    last_tx       = 0.0
    prev_t      = time.time()   # thời điểm frame trước (tính dt cho PID)
    left, right = 0, 0
    cmd_left, cmd_right = 0, 0
    last_sim    = 0.0
    all_bboxes  = []
    target_bbox = None
    registering = False

    # ---- EMA smoothing cho bbox (chống jitter trên RPi chậm) ----
    _ema_alpha  = 0.4            # 0.0=giữ cũ, 1.0=dùng raw (0.4 = cân bằng)
    _smooth_cx  = None           # tâm X đã làm mượt
    _smooth_ratio = None         # bbox_area_ratio đã làm mượt

    # ---- Skip-frame detection: chạy detector mỗi N frame ----
    _frame_count     = 0
    _detect_every    = max(1, config.DETECT_EVERY_N)
    _cached_result   = None      # kết quả find_target lần detect gần nhất
    _cached_bboxes   = []
    print(f"[CAMERA] Detect mỗi {_detect_every} frame (skip-frame)")

    read_fail_count = 0
    stall_count = 0
    registration_deadline = None

    while True:
        ret, frame = cap.read()
        if not ret:
            read_fail_count += 1
            print(f"[CAMERA] Đọc frame thất bại ({read_fail_count}/{config.CAMERA_READ_FAIL_LIMIT})")
            if read_fail_count >= config.CAMERA_READ_FAIL_LIMIT:
                print("[SAFETY] Camera read failed too many times -> motor stop")
                cmd_left = cmd_right = 0
                motor.send(0, 0)
                state_manager.update_motor(0, 0, last_sim)
                break
            time.sleep(0.02)
            continue
        read_fail_count = 0

        t_now = time.time()
        loop_gap = t_now - prev_t
        dt    = min(loop_gap, 0.50)   # clamp dt ≤ 500ms (RPi ONNX chậm ~300-500ms/frame)
        prev_t = t_now
        h, w  = frame.shape[:2]
        fx    = w // 2

        obs = ultrasonic.read()

        # Watchdog: nếu camera/detector khựng quá lâu thì dừng fail-safe.
        if loop_gap > config.CAMERA_STALL_TIMEOUT:
            stall_count += 1
            print(
                f"[SAFETY] Camera loop slow {loop_gap:.3f}s "
                f"({stall_count}/{config.CAMERA_STALL_MAX_CONSECUTIVE})"
            )
            if stall_count < config.CAMERA_STALL_MAX_CONSECUTIVE:
                continue
            print(f"[SAFETY] Camera loop stalled {loop_gap:.3f}s -> motor stop")
            left = right = 0
            cmd_left = cmd_right = 0
            motor.send(0, 0)
            state_manager.update_motor(0, 0, last_sim)
            steer_pid.reset()
            speed_pid.reset()
            continue
        stall_count = 0

        # ====================================================
        #  EMERGENCY STOP — ưu tiên tuyệt đối, kiểm tra TRƯỚC HẾT
        # ====================================================
        if state_manager.is_emergency:
            state_manager.state = State.EMERGENCY_STOP
            left, right = 0, 0
            cmd_left, cmd_right = 0, 0
            motor.send(0, 0)
            state_manager.update_motor(0, 0, last_sim)
            steer_pid.reset()
            speed_pid.reset()
            # Vẽ overlay + encode JPEG (cho cả GUI và web stream)
            if config.USE_GUI:
                frame = draw_overlay_lite(
                    frame, target_bbox, all_bboxes,
                    state_manager.state, last_sim,
                )
            else:
                frame = draw_overlay(
                    frame, target_bbox, all_bboxes,
                    state_manager.state, last_sim, left, right,
                    obs, registering,
                    gallery_count=tracker.gallery_count,
                    gallery_size=config.GALLERY_SIZE,
                )
            _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            state_manager.update_frame(jpeg.tobytes())
            if not config.HEADLESS:
                cv2.imshow("Follow Me -- Debug (Q=Quit O=Obstacle R=Reset)", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                elif key == ord("e"):
                    state_manager.clear_emergency_stop()
                    steer_pid.reset()   # reset sau emergency
                    speed_pid.reset()
            continue   # bỏ qua toàn bộ logic phía dưới

        # ====================================================
        #  Xử lý yêu cầu đăng ký từ Flask thread
        # ====================================================
        if state_manager.registration_requested:
            if not registering:
                registering = True
                registration_deadline = t_now + (4.5 if config.USE_GUI else 1.5)

            if config.USE_GUI:
                reg_bbox = tracker.select_registration_target(
                    frame, detector, center_weight=0.80, area_weight=0.20
                )
                if reg_bbox is not None:
                    ok, msg = tracker.register_bbox(frame, reg_bbox)
                    if ok:
                        saved_path = _save_gui_registration_snapshot(frame, reg_bbox)
                        if saved_path:
                            msg = f"{msg} | Da luu: {saved_path}"
                        registering = False
                        registration_deadline = None
                        state_manager.complete_registration(ok, msg)
                    else:
                        if t_now >= (registration_deadline or t_now):
                            registering = False
                            registration_deadline = None
                            state_manager.complete_registration(False, msg)
                elif t_now >= (registration_deadline or t_now):
                    registering = False
                    registration_deadline = None
                    state_manager.complete_registration(
                        False,
                        "Khong thay nguoi phu hop. Dung vao giua khung hinh, cach camera 1-2m roi bam lai.",
                    )
            else:
                ok, msg = tracker.register_from_frame(frame, detector)
                registering = False
                registration_deadline = None
                state_manager.complete_registration(ok, msg)

            if not state_manager.registration_requested and state_manager.is_registered:
                last_seen   = None
                lost_since  = None
                left, right = 0, 0
                last_sim    = 0.0
                target_bbox = None
                steer_pid.reset()   # reset PID khi đăng ký mới
                speed_pid.reset()
                _smooth_cx = None   # reset EMA
                _smooth_ratio = None

        # ====================================================
        #  Multi-capture: chụp 6 tấm → chờ xác nhận → đăng ký
        # ====================================================
        if state_manager.mc_active and state_manager.mc_count < 6:
            if t_now - state_manager.mc_last_time >= 0.8:
                mc_bboxes = detector.detect(frame)
                if mc_bboxes:
                    # Chọn người gần tâm + lớn nhất
                    mc_best = None
                    mc_best_score = -1.0
                    for bb in mc_bboxes:
                        bx1, by1, bx2, by2 = bb
                        bcx  = (bx1 + bx2) / 2.0
                        bcy  = (by1 + by2) / 2.0
                        barea = (bx2 - bx1) * (by2 - by1)
                        dist_n = (((bcx - fx) / max(fx, 1)) ** 2 +
                                  ((bcy - h / 2) / max(h / 2, 1)) ** 2) ** 0.5 / 1.414
                        sc = 0.55 * (1.0 - dist_n) + 0.45 * (barea / max(w * h, 1))
                        if sc > mc_best_score:
                            mc_best_score = sc
                            mc_best = bb
                    if mc_best:
                        from person_tracker import extract_appearance
                        mc_desc = extract_appearance(frame, mc_best)
                        # Crop thumbnail
                        mx1, my1, mx2, my2 = mc_best
                        crop = frame[my1:my2, mx1:mx2]
                        _, mc_jpg = cv2.imencode(
                            ".jpg", crop,
                            [cv2.IMWRITE_JPEG_QUALITY, config.MC_SNAPSHOT_JPEG_QUALITY]
                        )
                        mc_b64 = base64.b64encode(mc_jpg.tobytes()).decode()
                        # Face encoding là tác vụ khá nặng; tắt mặc định trên RPi.
                        mc_face = None
                        if config.MC_ENABLE_FACE_ENCODING and state_manager.mc_count == 0:
                            mc_face = tracker._face_verifier.encode(frame, mc_best)
                        state_manager.add_mc_snapshot(mc_b64, mc_desc, mc_face, mc_best)
                        state_manager.mc_last_time = t_now

        # Multi-capture: user xác nhận → đăng ký
        if state_manager.mc_confirmed:
            mc_descs, mc_face_enc, mc_bbs = state_manager.get_mc_data()
            ok, msg = tracker.register_from_gallery(mc_descs, mc_face_enc, mc_bbs)
            state_manager.complete_multi_capture(ok, msg)
            if ok:
                last_seen   = None
                lost_since  = None
                left, right = 0, 0
                last_sim    = 0.0
                target_bbox = None
                steer_pid.reset()
                speed_pid.reset()
                _smooth_cx = None   # reset EMA
                _smooth_ratio = None
        # ====================================================
        all_bboxes  = []
        target_bbox = None

        if not state_manager.is_paired:
            state_manager.state = State.WAIT_FOR_PAIR
            left, right = 0, 0

        elif not state_manager.is_registered:
            state_manager.state = State.PAIRED_BUT_NO_TARGET
            left, right = 0, 0
            # GUI cũng cần hiển thị bbox ứng viên để người dùng đứng đúng vị trí.
            if not config.HEADLESS or config.USE_GUI:
                all_bboxes = detector.detect(frame)

        else:
            # --- Đã đăng ký → tìm và follow ---

            # Obstacle check chỉ khi đã đăng ký (tránh flap khi chưa follow)
            if obs.center_stop:
                state_manager.state = State.OBSTACLE_STOP
                left, right = 0, 0
                steer_pid.reset()
                speed_pid.reset()
            else:
                # find_target trả về (result, all_bboxes) — detector chỉ gọi 1 lần
                _frame_count += 1
                if _frame_count >= _detect_every:
                    # ---- Frame detect: chạy ONNX inference ----
                    _frame_count = 0
                    result, all_bboxes = tracker.find_target(frame, detector)
                    _cached_result = result
                    _cached_bboxes = all_bboxes
                else:
                    # ---- Frame skip: dùng lại kết quả cũ ----
                    result     = _cached_result
                    all_bboxes = _cached_bboxes

                if result is not None:
                    target_bbox, (tcx, _tcy), last_sim = result
                    frame_area   = w * h
                    x1, y1, x2, y2 = target_bbox
                    bbox_area    = (x2 - x1) * (y2 - y1)
                    bbox_ratio   = bbox_area / max(frame_area, 1)

                    # ---- EMA smoothing: loại bỏ jitter bbox ----
                    if _smooth_cx is None:
                        _smooth_cx    = float(tcx)
                        _smooth_ratio = bbox_ratio
                    else:
                        _smooth_cx    = _ema_alpha * tcx + (1 - _ema_alpha) * _smooth_cx
                        _smooth_ratio = _ema_alpha * bbox_ratio + (1 - _ema_alpha) * _smooth_ratio

                    left, right  = compute_motor(
                        int(_smooth_cx), fx, _smooth_ratio, obs,
                        steer_pid, speed_pid, dt,
                    )
                    last_seen    = t_now
                    lost_since   = None
                    state_manager.state = State.FOLLOWING

                else:
                    # Không tìm thấy trong frame này
                    if last_seen is None:
                        state_manager.state = State.PAIRED_BUT_NO_TARGET
                        left, right = 0, 0
                        steer_pid.reset(); speed_pid.reset()
                        _smooth_cx = None; _smooth_ratio = None
                    elif t_now - last_seen > config.TARGET_LOST_TIMEOUT:
                        state_manager.state = State.TARGET_LOST
                        last_sim    = 0.0
                        target_bbox = None
                        steer_pid.reset(); speed_pid.reset()
                        _smooth_cx = None; _smooth_ratio = None
                        # --- Spin-search: xoay tại chỗ tìm người ---
                        if lost_since is None:
                            lost_since = t_now
                        spin_elapsed = t_now - lost_since
                        if spin_elapsed < config.SEARCH_SPIN_DURATION:
                            spd = config.SEARCH_SPIN_SPEED
                            d   = config.SEARCH_SPIN_DIR
                            left  =  spd * d    # +spd = bánh trái tiến
                            right = -spd * d    # -spd = bánh phải lùi → xoay tại chỗ
                        else:
                            left, right = 0, 0  # hết thời gian xoay → dừng hẳn
                    # else: còn trong grace period → giữ lệnh cuối

        # ====================================================
        #  Gửi lệnh motor (rate-limited)
        # ====================================================
        if t_now - last_tx >= config.MOTOR_SEND_INTERVAL:
            cmd_left, cmd_right = _ramp_motor_command(cmd_left, cmd_right, left, right)
            motor.send(cmd_left, cmd_right)
            state_manager.update_motor(cmd_left, cmd_right, last_sim)
            last_tx = t_now

        # ====================================================
        #  Debug overlay + hiển thị
        # ====================================================
        if not config.HEADLESS:
            frame = draw_overlay(
                frame,
                target_bbox,
                all_bboxes,
                state_manager.state,
                last_sim,
                left, right,
                obs,
                registering,
                gallery_count=tracker.gallery_count,
                gallery_size=config.GALLERY_SIZE,
                pid_steer=steer_pid.terms,
                pid_speed=speed_pid.terms,
            )
            cv2.imshow("Follow Me -- Debug (Q=Quit O=Obstacle R=Reset)", frame)
        else:
            # HEADLESS hoặc GUI mode — overlay nhẹ khi GUI, đầy đủ khi web
            if config.USE_GUI:
                frame = draw_overlay_lite(
                    frame, target_bbox, all_bboxes,
                    state_manager.state, last_sim,
                )
            else:
                frame = draw_overlay(
                    frame,
                    target_bbox,
                    all_bboxes,
                    state_manager.state,
                    last_sim,
                    left, right,
                    obs,
                    registering,
                    gallery_count=tracker.gallery_count,
                    gallery_size=config.GALLERY_SIZE,
                    pid_steer=steer_pid.terms,
                    pid_speed=speed_pid.terms,
                )

        # Encode frame → JPEG cho web streaming
        _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        state_manager.update_frame(jpeg.tobytes())

        # ====================================================
        #  Phím tắt (chỉ khi không headless)
        # ====================================================
        key = cv2.waitKey(1) & 0xFF if not config.HEADLESS else 0xFF
        if key in (ord("q"), 27):
            break
        elif key == ord("e"):
            # Toggle Emergency Stop
            if state_manager.is_emergency:
                state_manager.clear_emergency_stop()
            else:
                state_manager.set_emergency_stop()
        elif key == ord("o"):
            # Toggle vật cản phía TRƯỚC (chỉ có hiệu lực khi HARDWARE_MODE=laptop)
            if config.HARDWARE_MODE != "raspi":
                ultrasonic.set_fake_obstacle(not ultrasonic.fake_obstacle, side="center")
        elif key == ord("["):
            # Toggle vật cản bên TRÁI
            if config.HARDWARE_MODE != "raspi":
                _l_on = ultrasonic._fake_cm["left"] < config.DEFAULT_DISTANCE_CM
                ultrasonic.set_fake_obstacle(not _l_on, side="left")
        elif key == ord("]"):
            # Toggle vật cản bên PHẢI
            if config.HARDWARE_MODE != "raspi":
                _r_on = ultrasonic._fake_cm["right"] < config.DEFAULT_DISTANCE_CM
                ultrasonic.set_fake_obstacle(not _r_on, side="right")
        elif key == ord("r"):
            state_manager.reset_pairing()
            tracker.reset()
            steer_pid.reset()
            speed_pid.reset()
            last_seen   = None
            lost_since  = None
            left, right = 0, 0
            last_sim    = 0.0
            target_bbox = None
            _smooth_cx = None; _smooth_ratio = None

    # --- Dọn dẹp ---
    cap.release()
    if not config.HEADLESS:
        cv2.destroyAllWindows()
    motor.stop()
    motor.close()
    ultrasonic.cleanup()
    print("\n[CAMERA] Đã thoát.")


# ============================================================
#  Entry point
# ============================================================

def main():
    print("=" * 60)
    print("   Follow Me — Laptop Test MVP  (Person Re-ID)")
    print("=" * 60)
    print(f"  Camera index   : {config.CAMERA_INDEX}")
    print(f"  Detector       : {config.DETECTOR_BACKEND.upper()}")
    print(f"  Sim threshold  : {config.SIMILARITY_THRESHOLD}")
    print("=" * 60)

    # ---- Menu chọn chế độ ----
    print("\n  Chọn chế độ giao diện:")
    print("    [1] APP  — Giao diện tkinter (không cần mạng)")
    print("    [2] WEB  — Giao diện web Flask (cần mạng, quét QR)")
    print()

    choice = ""
    while choice not in ("1", "2"):
        choice = input("  Nhập 1 hoặc 2 (mặc định=1): ").strip()
        if choice == "":
            choice = "1"

    use_gui = (choice == "1")
    config.USE_GUI = use_gui   # cập nhật runtime cho overlay selection
    print()

    if use_gui:
        # GUI mode: camera loop trong background thread, tkinter trong main thread
        from app_gui import run_gui

        print("  → Chế độ APP (tkinter) — không cần mạng")
        print("  Phím: E=Emergency  R=Reset")
        print("=" * 60 + "\n")

        cam_thread = threading.Thread(target=camera_loop, name="CameraLoop", daemon=True)
        cam_thread.start()
        time.sleep(0.5)  # chờ camera mở xong
        run_gui()        # tkinter mainloop (block main thread)

    else:
        # Web mode: Flask trong daemon thread, camera loop trong main thread
        from app_server import run_server

        ip = config.get_local_ip()
        print(f"  → Chế độ WEB (Flask)")
        print(f"  LAN IP         : {ip}")
        print(f"  QR page        : http://{ip}:{config.SERVER_PORT}/")
        print(f"  Pair URL       : http://{ip}:{config.SERVER_PORT}/pair")
        print("=" * 60)
        print("  FLOW:")
        print("  1. Mở browser laptop → QR page")
        print("  2. Điện thoại quét QR → trang /pair")
        print("  3. Đứng trước camera, nhấn ĐĂNG KÝ trên điện thoại")
        print("  4. Xe follow đúng bạn dù xung quanh có nhiều người")
        print("=" * 60 + "\n")

        srv = threading.Thread(target=run_server, name="FlaskServer", daemon=True)
        srv.start()
        time.sleep(0.9)   # chờ Flask bind xong
        camera_loop()     # main thread (yêu cầu của OpenCV trên Windows)


if __name__ == "__main__":
    main()
