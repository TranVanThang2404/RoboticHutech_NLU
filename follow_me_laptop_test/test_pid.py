"""
test_pid.py â€” Kiá»ƒm tra vÃ  visualize logic PID cho Follow Me.

Cháº¡y:  python test_pid.py

CÃ¡c test:
  1. Khá»Ÿi táº¡o tá»« config
  2. Steering PID â€” ngÆ°á»i lá»‡ch pháº£i rá»“i vá» giá»¯a (step response)
  3. Speed PID â€” ngÆ°á»i quÃ¡ xa rá»“i tiáº¿n láº¡i gáº§n (distance control)
  4. Anti-windup â€” giá»¯ nguyÃªn error lÃ¢u dÃ i
  5. Derivative filter â€” error nháº£y Ä‘á»™t ngá»™t (noise spike)
  6. Reset â€” kiá»ƒm tra reset sáº¡ch tráº¡ng thÃ¡i
  7. compute_motor tÃ­ch há»£p â€” kiá»ƒm tra Ä‘áº§u ra motor cuá»‘i cÃ¹ng
  8. Obstacle override â€” cáº£m biáº¿n bÃªn cÆ°á»¡ng bá»©c steering
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from pid_controller import PIDController
from ultrasonic_mock import MockUltrasonicArray, ObstacleReading
import config

PASS = "PASS"
FAIL = "FAIL"

results = []

def check(name, condition, detail=""):
    tag = PASS if condition else FAIL
    results.append((tag, name))
    mark = "OK" if condition else "!!"
    print(f"  [{mark}] {name}" + (f"  ({detail})" if detail else ""))
    return condition


# ================================================================
print("=" * 60)
print("  TEST 1: Khoi tao PID tu config")
print("=" * 60)
# ================================================================
try:
    steer = PIDController(
        kp=config.STEER_KP, ki=config.STEER_KI, kd=config.STEER_KD,
        integral_limit=config.STEER_INTEGRAL_LIMIT,
        output_limit=config.STEER_OUTPUT_LIMIT,
        deriv_filter_alpha=config.STEER_DERIV_ALPHA,
    )
    speed = PIDController(
        kp=config.SPEED_KP, ki=config.SPEED_KI, kd=config.SPEED_KD,
        integral_limit=config.SPEED_INTEGRAL_LIMIT,
        output_limit=config.SPEED_OUTPUT_LIMIT,
        deriv_filter_alpha=config.SPEED_DERIV_ALPHA,
    )
    check("Steering gains khop config", steer.kp == config.STEER_KP and steer.ki == config.STEER_KI)
    check("Speed gains khop config", speed.kp == config.SPEED_KP and speed.ki == config.SPEED_KI)
    check("Steer output_limit khop config", steer.output_limit == config.STEER_OUTPUT_LIMIT)
    check("Speed output_limit khop config", speed.output_limit == config.SPEED_OUTPUT_LIMIT)
    check("BBOX_TARGET_RATIO trong config", hasattr(config, "BBOX_TARGET_RATIO"))
except Exception as e:
    check("Import + khoi tao", False, str(e))


# ================================================================
print()
print("=" * 60)
print("  TEST 2: Steering PID â€” Step response (nguoi lech phai)")
print("=" * 60)
print(f"  {'step':<5} {'error':>8} {'P':>8} {'I':>8} {'D':>8} {'output':>8}")
print(f"  {'-'*5} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
# ================================================================
pid_s = PIDController(kp=80.0, ki=5.0, kd=20.0,
                      integral_limit=20.0, output_limit=90.0,
                      deriv_filter_alpha=0.20)
dt = 0.05
# NgÆ°á»i lá»‡ch pháº£i (error > 0) rá»“i tiáº¿n dáº§n vá» giá»¯a
errors_right = [0.50, 0.45, 0.35, 0.22, 0.12, 0.04, 0.01, 0.00, 0.00, 0.00]
outputs = []
for i, e in enumerate(errors_right):
    out = pid_s.compute(e, dt)
    p, ii, d = pid_s.terms
    outputs.append(out)
    print(f"  {i:<5} {e:>8.3f} {p:>8.2f} {ii:>8.2f} {d:>8.2f} {out:>8.2f}")

check("Error > 0 â†’ output > 0 (re phai)", outputs[0] > 0,
      f"output[0]={outputs[0]:.2f}")
check("Output giam dan khi error giam", outputs[0] > outputs[4],
      f"{outputs[0]:.1f} > {outputs[4]:.1f}  (D-term brake la binh thuong)")
check("Output clamp <= 90.0", max(outputs) <= 90.0,
      f"max={max(outputs):.2f}")

# NgÆ°á»i lá»‡ch trÃ¡i (error < 0) â†’ output < 0
pid_s.reset()
out_left = pid_s.compute(-0.5, dt)
check("Error < 0 â†’ output < 0 (re trai)", out_left < 0,
      f"output={out_left:.2f}")


# ================================================================
print()
print("=" * 60)
print("  TEST 3: Speed PID â€” Distance control (nguoi qua xa)")
print("=" * 60)
print(f"  {'step':<5} {'bbox_ratio':>10} {'speed_err':>10} {'output':>10} {'base':>8}")
print(f"  {'-'*5} {'-'*10} {'-'*10} {'-'*10} {'-'*8}")
# ================================================================
pid_v = PIDController(kp=config.SPEED_KP, ki=config.SPEED_KI, kd=config.SPEED_KD,
                      integral_limit=config.SPEED_INTEGRAL_LIMIT,
                      output_limit=config.SPEED_OUTPUT_LIMIT,
                      deriv_filter_alpha=config.SPEED_DERIV_ALPHA)
target_ratio = config.BBOX_TARGET_RATIO   # 0.12
# NgÆ°á»i xa (bbox nhá» = 0.03) tiáº¿n dáº§n láº¡i vá»‹ trÃ­ target (0.12)
bbox_sequence = [0.03, 0.05, 0.08, 0.10, 0.11, 0.12, 0.12, 0.12]
speed_outputs = []
for i, bbox in enumerate(bbox_sequence):
    err = target_ratio - bbox
    out = pid_v.compute(err, dt)
    speed_outputs.append(out)
    base_adj = int(config.BASE_SPEED + out)
    print(f"  {i:<5} {bbox:>10.3f} {err:>10.3f} {out:>10.2f} {base_adj:>8d}")

check("Nguoi xa â†’ speed output > 0 (tang toc)", speed_outputs[0] > 0,
      f"output[0]={speed_outputs[0]:.2f}")
check("Speed output clamp <= output_limit", max(speed_outputs) <= config.SPEED_OUTPUT_LIMIT,
      f"max={max(speed_outputs):.2f}")
check("Speed output giam khi nguoi den gan", speed_outputs[0] > speed_outputs[4],
      f"{speed_outputs[0]:.1f} > {speed_outputs[4]:.1f}")

# NgÆ°á»i quÃ¡ gáº§n â†’ output Ã¢m (giáº£m tá»‘c)
pid_v.reset()
out_close = pid_v.compute(config.BBOX_TARGET_RATIO - 0.30, dt)  # bbox ráº¥t lá»›n
check("Nguoi qua gan â†’ output < 0 (giam toc)", out_close < 0,
      f"output={out_close:.2f}")


# ================================================================
print()
print("=" * 60)
print("  TEST 4: Anti-windup â€” Error khong doi trong 2 giay")
print("=" * 60)
# ================================================================
pid_aw = PIDController(kp=80.0, ki=5.0, kd=20.0,
                       integral_limit=20.0, output_limit=90.0,
                       deriv_filter_alpha=0.20)
for _ in range(40):   # 40 frames Ã— 0.05s = 2s
    pid_aw.compute(0.5, 0.05)

# Integral bá»‹ clamp táº¡i STEER_INTEGRAL_LIMIT = 20.0
# I component = ki * integral = 5.0 * 20.0 = 100 â†’ clamp output = 90
integral_contribution = pid_aw.ki * pid_aw.integral
check("Integral bi clamp <= STEER_INTEGRAL_LIMIT",
      abs(pid_aw.integral) <= config.STEER_INTEGRAL_LIMIT,
      f"integral={pid_aw.integral:.3f}")
check("Output van clamp <= 90.0 du integral lon",
      pid_aw.compute(0.5, 0.05) <= 90.0)


# ================================================================
print()
print("=" * 60)
print("  TEST 5: Derivative filter â€” Noise spike khong gay giat")
print("=" * 60)
# ================================================================
pid_df = PIDController(kp=80.0, ki=5.0, kd=20.0,
                       integral_limit=20.0, output_limit=90.0,
                       deriv_filter_alpha=0.20)
# Steady error = 0.3 rá»“i noise spike to 0.9 (detection glitch)
pid_df.compute(0.3, dt)
pid_df.compute(0.3, dt)
out_before_spike = pid_df.compute(0.3, dt)

# Spike Ä‘á»™t ngá»™t: bbox nháº£y sang 0.9 (lá»—i detect)
out_spike = pid_df.compute(0.9, dt)

# Náº¿u khÃ´ng cÃ³ filter, D = kd*(0.9-0.3)/0.05 = 20*12 = 240 â†’ clamp 90
# Vá»›i filter alpha=0.20, D bá»‹ giáº£m Ä‘Ã¡ng ká»ƒ
_, _, d_spike = pid_df.terms
print(f"  D-term sau spike (co filter alpha=0.20): {d_spike:.2f}")
print(f"  D-term khong filter se la: {20.0 * (0.9 - 0.3) / dt:.2f}")
check("Filter lam giam D-term spike > 50%",
      abs(d_spike) < abs(20.0 * (0.9 - 0.3) / dt) * 0.5,
      f"d_filtered={d_spike:.2f}  d_raw={20.0*(0.9-0.3)/dt:.2f}")
check("Output sau spike van clamp <= 90", abs(out_spike) <= 90.0)


# ================================================================
print()
print("=" * 60)
print("  TEST 6: Reset â€” Xoa sach trang thai noi bo")
print("=" * 60)
# ================================================================
pid_r = PIDController(kp=80.0, ki=5.0, kd=20.0,
                      integral_limit=20.0, output_limit=90.0)
for _ in range(20):
    pid_r.compute(0.5, 0.05)

integral_before = pid_r.integral
pid_r.reset()

check("Integral = 0 sau reset", pid_r.integral == 0.0,
      f"was {integral_before:.3f}")
check("prev_error = None sau reset", pid_r._prev_error is None)
check("deriv_filtered = 0 sau reset", pid_r._deriv_filtered == 0.0)
# Sau reset, D-term frame Ä‘áº§u = 0 (prev_error is None)
out_first = pid_r.compute(0.5, 0.05)
_, _, d_first = pid_r.terms
check("D-term = 0 o frame dau sau reset", d_first == 0.0,
      f"d={d_first:.3f}")


# ================================================================
print()
print("=" * 60)
print("  TEST 7: compute_motor tich hop â€” kiem tra dau ra motor")
print("=" * 60)
# ================================================================
# Import vÃ  táº¡o láº¡i PID nhÆ° camera_loop
from camera_follow_laptop import compute_motor
from ultrasonic_mock import ObstacleReading

obs_clear = ObstacleReading(left_cm=150.0, center_cm=150.0, right_cm=150.0)

pid_steer = PIDController(kp=80.0, ki=5.0, kd=20.0,
                          integral_limit=20.0, output_limit=90.0,
                          deriv_filter_alpha=0.20)
pid_speed = PIDController(kp=config.SPEED_KP, ki=config.SPEED_KI, kd=config.SPEED_KD,
                          integral_limit=config.SPEED_INTEGRAL_LIMIT,
                          output_limit=config.SPEED_OUTPUT_LIMIT,
                          deriv_filter_alpha=config.SPEED_DERIV_ALPHA)

frame_cx = 320   # 640/2
dt = 0.05

# NgÆ°á»i á»Ÿ giá»¯a, Ä‘Ãºng khoáº£ng cÃ¡ch
cx_center = 320
bbox_at_target = config.BBOX_TARGET_RATIO
L, R = compute_motor(cx_center, frame_cx, bbox_at_target, obs_clear,
                     pid_steer, pid_speed, dt)
print(f"  Nguoi giua, dung kc: L={L}  R={R}")
check("L == R khi nguoi giua (dead zone)", abs(L - R) <= 5,
      f"L={L} R={R}")
check("Dung khoang cach -> xe dung/rat cham", abs(L) <= 5 and abs(R) <= 5,
      f"L={L} R={R}")

# NgÆ°á»i lá»‡ch pháº£i máº¡nh
pid_steer.reset(); pid_speed.reset()
cx_right = 500  # lá»‡ch pháº£i (500-320)/320 â‰ˆ +0.56
bbox_far = 0.03
L, R = compute_motor(cx_right, frame_cx, bbox_far, obs_clear,
                     pid_steer, pid_speed, dt)
print(f"  Nguoi lech phai + dang tien: L={L}  R={R}")
check("Nguoi phai khi dang tien â†’ L > R (re phai)", L > R, f"L={L} R={R}")
check("Toc do trong gioi han motor", config.MIN_SPEED <= L <= config.MAX_SPEED and
      config.MIN_SPEED <= R <= config.MAX_SPEED, f"L={L} R={R}")

# NgÆ°á»i quÃ¡ xa â†’ tÄƒng tá»‘c
pid_steer.reset(); pid_speed.reset()
L, R = compute_motor(cx_center, frame_cx, bbox_far, obs_clear,
                     pid_steer, pid_speed, dt)
print(f"  Nguoi qua xa:        L={L}  R={R}")
check("Nguoi xa â†’ xe tien", L > 0 or R > 0,
      f"L={L} R={R}")


# ================================================================
print()
print("=" * 60)
print("  TEST 8: Obstacle override â€” cam bien ben cuong buc steering")
print("=" * 60)
# ================================================================
pid_steer.reset(); pid_speed.reset()

# BÃªn trÃ¡i bá»‹ cháº·n, ngÆ°á»i Ä‘ang á»Ÿ GIá»®A â†’ xe pháº£i ráº½ pháº£i (L > R)
obs_left_blocked = ObstacleReading(left_cm=10.0, center_cm=150.0, right_cm=150.0)
L, R = compute_motor(cx_center, frame_cx, bbox_at_target, obs_left_blocked,
                     pid_steer, pid_speed, dt)
print(f"  Ben trai bi chan:     L={L}  R={R}")
check("Trai bi chan â†’ khong re sai huong", L >= R, f"L={L} R={R}")

pid_steer.reset(); pid_speed.reset()

# BÃªn pháº£i bá»‹ cháº·n, ngÆ°á»i Ä‘ang á»Ÿ GIá»®A â†’ xe pháº£i ráº½ trÃ¡i (R > L)
obs_right_blocked = ObstacleReading(left_cm=150.0, center_cm=150.0, right_cm=10.0)
L, R = compute_motor(cx_center, frame_cx, bbox_at_target, obs_right_blocked,
                     pid_steer, pid_speed, dt)
print(f"  Ben phai bi chan:     L={L}  R={R}")
check("Phai bi chan â†’ khong re sai huong", R >= L, f"L={L} R={R}")

pid_steer.reset(); pid_speed.reset()

# Cáº£ hai bá»‹ cháº·n â†’ Ä‘i tháº³ng (cháº­m)
obs_both_blocked = ObstacleReading(left_cm=10.0, center_cm=150.0, right_cm=10.0)
L, R = compute_motor(cx_center, frame_cx, bbox_at_target, obs_both_blocked,
                     pid_steer, pid_speed, dt)
print(f"  Ca hai bi chan:       L={L}  R={R}")
check("Ca hai bi chan â†’ di thang (L == R)", abs(L - R) <= 3, f"L={L} R={R}")

# PhÃ­a trÆ°á»›c bá»‹ cháº·n (slow) â†’ tá»‘c Ä‘á»™ tháº¥p hÆ¡n
pid_steer.reset(); pid_speed.reset()
obs_front_slow = ObstacleReading(left_cm=150.0, center_cm=40.0, right_cm=150.0)
L_slow, R_slow = compute_motor(cx_center, frame_cx, bbox_at_target, obs_front_slow,
                                pid_steer, pid_speed, dt)
pid_steer.reset(); pid_speed.reset()
L_norm, R_norm = compute_motor(cx_center, frame_cx, bbox_at_target, obs_clear,
                                pid_steer, pid_speed, dt)
print(f"  Phia truoc slow:     L={L_slow}  R={R_slow}  (norm: L={L_norm} R={R_norm})")
check("Cam bien slow giam toc do", (L_slow + R_slow) <= (L_norm + R_norm),
      f"slow={L_slow+R_slow}  norm={L_norm+R_norm}")


# ================================================================
print()
print("=" * 60)
print("  KET QUA")
print("=" * 60)
passed = sum(1 for tag, _ in results if tag == PASS)
failed = sum(1 for tag, _ in results if tag == FAIL)
total  = len(results)
print(f"  PASS: {passed}/{total}")
if failed:
    print(f"  FAIL: {failed}/{total}")
    for tag, name in results:
        if tag == FAIL:
            print(f"    !! {name}")
else:
    print("  Tat ca test PASS!")
print("=" * 60)

