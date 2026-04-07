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

import sys
import threading
import time

import cv2
import numpy as np

import config
from app_server import run_server
from person_tracker import TargetTracker, create_detector
from pid_controller import PIDController
from state_manager import State, state_manager
from ultrasonic_mock import ObstacleReading

# ============================================================
#  Dynamic hardware — đổi HARDWARE_MODE trong config.py
#  "laptop" → FakeMotorUART + MockUltrasonicArray (test không cần phần cứng)
#  "raspi"  → RealMotorUART (UART pyserial) + RealUltrasonicArray (RPi.GPIO HC-SR04)
# ============================================================
if config.HARDWARE_MODE == "raspi":
    from motor_raspi import RealMotorUART as _MotorClass
    from ultrasonic_raspi import RealUltrasonicArray as _UltrasonicClass
else:
    from motor_fake import FakeMotorUART as _MotorClass         # type: ignore
    from ultrasonic_mock import MockUltrasonicArray as _UltrasonicClass  # type: ignore

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
    # ============ PID Speed: tính base speed ============
    speed_err = config.BBOX_TARGET_RATIO - bbox_area_ratio
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

    # ============ Tổng hợp đầu ra ============
    left_speed  = max(config.MIN_SPEED, min(config.MAX_SPEED,
                      int(base + steer_out)))
    right_speed = max(config.MIN_SPEED, min(config.MAX_SPEED,
                      int(base - steer_out)))
    return left_speed, right_speed


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

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    print("[CAMERA] Camera sẵn sàng  640x480")
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
    last_sim    = 0.0
    all_bboxes  = []
    target_bbox = None
    registering = False

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[CAMERA] Đọc frame thất bại — camera bị ngắt?")
            break

        t_now = time.time()
        dt    = min(t_now - prev_t, 0.20)   # clamp dt ≤ 200ms (tráng thái sau pause)
        prev_t = t_now
        h, w  = frame.shape[:2]
        fx    = w // 2

        obs = ultrasonic.read()

        # ====================================================
        #  EMERGENCY STOP — ưu tiên tuyệt đối, kiểm tra TRƯỚC HẾT
        # ====================================================
        if state_manager.is_emergency:
            state_manager.state = State.EMERGENCY_STOP
            left, right = 0, 0
            motor.send(0, 0)
            state_manager.update_motor(0, 0, last_sim)
            steer_pid.reset()
            speed_pid.reset()
            if not config.HEADLESS:
                frame = draw_overlay(
                    frame, target_bbox, all_bboxes,
                    state_manager.state, last_sim, left, right,
                    obs, registering,
                    gallery_count=tracker.gallery_count,
                    gallery_size=config.GALLERY_SIZE,
                )
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
            registering = True
            ok, msg     = tracker.register_from_frame(frame, detector)
            registering = False
            state_manager.complete_registration(ok, msg)
            if ok:
                last_seen   = None
                lost_since  = None
                left, right = 0, 0
                last_sim    = 0.0
                target_bbox = None
                steer_pid.reset()   # reset PID khi đăng ký mới
                speed_pid.reset()

        # ====================================================
        #  State machine + follow logic
        # ====================================================
        all_bboxes  = []
        target_bbox = None

        if obs.center_stop:
            state_manager.state = State.OBSTACLE_STOP
            left, right = 0, 0
            steer_pid.reset()
            speed_pid.reset()

        elif not state_manager.is_paired:
            state_manager.state = State.WAIT_FOR_PAIR
            left, right = 0, 0

        elif not state_manager.is_registered:
            state_manager.state = State.PAIRED_BUT_NO_TARGET
            left, right = 0, 0
            # Phát hiện người để hiển thị hướng dẫn vị trí đứng (chỉ khi có màn hình)
            if not config.HEADLESS:
                all_bboxes = detector.detect(frame)

        else:
            # --- Đã đăng ký → tìm và follow ---
            # find_target trả về (result, all_bboxes) — detector chỉ gọi 1 lần
            result, all_bboxes = tracker.find_target(frame, detector)

            if result is not None:
                target_bbox, (tcx, _tcy), last_sim = result
                frame_area   = w * h
                x1, y1, x2, y2 = target_bbox
                bbox_area    = (x2 - x1) * (y2 - y1)
                bbox_ratio   = bbox_area / max(frame_area, 1)

                left, right  = compute_motor(
                    tcx, fx, bbox_ratio, obs,
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
                elif t_now - last_seen > config.TARGET_LOST_TIMEOUT:
                    state_manager.state = State.TARGET_LOST
                    last_sim    = 0.0
                    target_bbox = None
                    steer_pid.reset(); speed_pid.reset()
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
            motor.send(left, right)
            state_manager.update_motor(left, right, last_sim)
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
    ip = config.get_local_ip()
    print("=" * 60)
    print("   Follow Me — Laptop Test MVP  (Person Re-ID)")
    print("=" * 60)
    print(f"  LAN IP         : {ip}")
    print(f"  QR page        : http://{ip}:{config.SERVER_PORT}/")
    print(f"  Pair URL       : http://{ip}:{config.SERVER_PORT}/pair")
    print(f"  Camera index   : {config.CAMERA_INDEX}")
    print(f"  Detector       : {config.DETECTOR_BACKEND.upper()}")
    print(f"  Sim threshold  : {config.SIMILARITY_THRESHOLD}")
    print("=" * 60)
    print("  FLOW:")
    print("  1. Mở browser laptop → QR page")
    print("  2. Điện thoại quét QR → trang /pair")
    print("  3. Đứng trước camera, nhấn ĐĂNG KÝ trên điện thoại")
    print("  4. Xe follow đúng bạn dù xung quanh có nhiều người")
    print("=" * 60 + "\n")

    # Khởi động Flask trong daemon thread
    srv = threading.Thread(target=run_server, name="FlaskServer", daemon=True)
    srv.start()
    time.sleep(0.9)   # chờ Flask bind xong

    # Camera loop trong main thread (yêu cầu của OpenCV trên Windows)
    camera_loop()


if __name__ == "__main__":
    main()
