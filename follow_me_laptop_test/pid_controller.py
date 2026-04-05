"""
pid_controller.py — Generic PID Controller dùng cho Follow Me.

Hệ thống dùng 2 PID độc lập:

  ┌─────────────────────────────────────────────────────────────┐
  │  Steering PID (lái trái/phải)                               │
  │    Error  = (cx_người - cx_frame) / cx_frame  ∈ [-1, +1]   │
  │    Output = speed differential (cùng đơn vị với motor 0-100)│
  │    left  = base + output                                    │
  │    right = base - output                                    │
  ├─────────────────────────────────────────────────────────────┤
  │  Speed PID (tiến/lùi — duy trì khoảng cách follow)         │
  │    Error  = BBOX_TARGET_RATIO - bbox_area_ratio             │
  │    > 0: người quá xa  → tăng tốc                           │
  │    < 0: người quá gần → giảm tốc / lùi                     │
  │    Output = delta speed cộng thêm vào BASE_SPEED            │
  └─────────────────────────────────────────────────────────────┘

Đặc điểm kỹ thuật:
  - Anti-windup: tích phân bị clamp theo integral_limit
  - Derivative low-pass filter: lọc nhiễu từ detection (d_filtered = α·raw + (1-α)·prev)
  - Output clamping qua output_limit
  - Thread-safe reset() để gọi khi mất người hoặc emergency stop
"""


class PIDController:
    """
    Bộ điều khiển PID 1 chiều với anti-windup và lọc nhiễu đạo hàm.

    Args:
        kp                 : Hệ số tỉ lệ (Proportional gain)
        ki                 : Hệ số tích phân (Integral gain)
        kd                 : Hệ số vi phân (Derivative gain)
        integral_limit     : Giới hạn tích lũy tích phân (anti-windup)
        output_limit       : Giới hạn giá trị đầu ra (None = không giới hạn)
        deriv_filter_alpha : Hệ số lọc low-pass cho đạo hàm
                             0.0 = giữ nguyên giá trị trước (không cập nhật)
                             1.0 = không lọc (dùng raw derivative)
                             0.15–0.25 = cân bằng tốt cho camera 15-30fps
    """

    def __init__(
        self,
        kp: float,
        ki: float,
        kd: float,
        integral_limit: float = 1.0,
        output_limit: float = None,
        deriv_filter_alpha: float = 0.20,
    ):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral_limit    = integral_limit
        self.output_limit      = output_limit
        self.alpha             = deriv_filter_alpha

        self._integral         = 0.0
        self._prev_error       = None   # None cho đến lần gọi đầu tiên
        self._deriv_filtered   = 0.0   # đạo hàm đã qua lọc thấp
        self._last_p           = 0.0
        self._last_i           = 0.0
        self._last_d           = 0.0

    # ------------------------------------------------------------------ #
    #  Core compute
    # ------------------------------------------------------------------ #

    def compute(self, error: float, dt: float) -> float:
        """
        Tính output PID cho bước thời gian dt.

        Args:
            error : sai số hiện tại (setpoint - measured)
            dt    : thời gian từ lần gọi trước (giây), > 0

        Returns:
            float: giá trị điều khiển đầu ra
        """
        dt = max(dt, 1e-6)   # tránh chia cho 0

        # ── Proportional ──────────────────────────────────────────────
        p = self.kp * error

        # ── Integral với anti-windup ───────────────────────────────────
        self._integral += error * dt
        self._integral = max(
            -self.integral_limit,
            min(self.integral_limit, self._integral),
        )
        i = self.ki * self._integral

        # ── Derivative với low-pass filter ────────────────────────────
        # Tránh derivative kick khi error nhảy đột ngột do detection noise
        if self._prev_error is None:
            raw_d = 0.0
        else:
            raw_d = (error - self._prev_error) / dt

        # Lọc low-pass: giảm nhiễu tần số cao từ vision pipeline
        self._deriv_filtered = (
            self.alpha * raw_d
            + (1.0 - self.alpha) * self._deriv_filtered
        )
        d = self.kd * self._deriv_filtered

        self._prev_error = error

        # ── Tổng hợp + clamp ──────────────────────────────────────────
        output = p + i + d
        if self.output_limit is not None:
            output = max(-self.output_limit, min(self.output_limit, output))

        # Lưu các thành phần để debug overlay
        self._last_p, self._last_i, self._last_d = p, i, d

        return output

    # ------------------------------------------------------------------ #
    #  Debug / introspection
    # ------------------------------------------------------------------ #

    @property
    def terms(self) -> tuple:
        """Trả về (P, I, D) của lần compute() gần nhất (cho debug overlay)."""
        return self._last_p, self._last_i, self._last_d

    @property
    def integral(self) -> float:
        """Giá trị tích phân hiện tại."""
        return self._integral

    # ------------------------------------------------------------------ #
    #  Reset
    # ------------------------------------------------------------------ #

    def reset(self):
        """
        Xóa toàn bộ trạng thái nội bộ.
        Gọi khi: mất target, emergency stop, đăng ký lại.
        """
        self._integral       = 0.0
        self._prev_error     = None
        self._deriv_filtered = 0.0
        self._last_p = self._last_i = self._last_d = 0.0
