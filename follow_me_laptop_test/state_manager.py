"""
state_manager.py — State machine cho hệ thống Follow Me.

Các trạng thái:
  WAIT_FOR_PAIR        : Chưa có điện thoại pair. Motor dừng.
  PAIRED_BUT_NO_TARGET : Đã pair nhưng chưa đăng ký / thấy người. Motor dừng.
  FOLLOWING            : Đang bám theo người đã đăng ký. Motor chạy.
  TARGET_LOST          : Mất người quá timeout. Motor dừng.
  OBSTACLE_STOP        : Vật cản quá gần (real hoặc mock). Motor dừng.
  EMERGENCY_STOP       : Dừng khẩn cấp do người dùng kích hoạt. Ưu tiên cao nhất.

Thêm so với phiên bản cũ:
  - Registration event: Flask báo camera thread cần chụp và đăng ký người
  - Registration result: camera thread trả kết quả về Flask qua shared dict
  - Emergency stop: Flask / bàn phím → camera thread dừng cứng tức thì
"""

import threading

class State:
    """Hằng số tên trạng thái."""
    WAIT_FOR_PAIR        = "WAIT_FOR_PAIR"
    PAIRED_BUT_NO_TARGET = "PAIRED_BUT_NO_TARGET"
    FOLLOWING            = "FOLLOWING"
    TARGET_LOST          = "TARGET_LOST"
    OBSTACLE_STOP        = "OBSTACLE_STOP"
    EMERGENCY_STOP       = "EMERGENCY_STOP"   # ưu tiên cao nhất — khoá motor cứng


class StateManager:
    """Thread-safe state machine + registration handshake."""

    def __init__(self):
        self._lock       = threading.Lock()
        self._state      = State.WAIT_FOR_PAIR
        self._paired     = False
        self._registered = False           # True sau khi đăng ký người thành công
        self._left_spd   = 0
        self._right_spd  = 0
        self._last_sim   = 0.0             # similarity score lần cuối tìm thấy người
        self._emergency  = False           # True = dừng khẩn cấp đang kích hoạt

        # ---- Registration handshake events ----
        # Flask  → sets  _reg_request_event  (yêu cầu capture + register)
        # Camera → sets  _reg_done_event     (hoàn thành, dù thành công hay không)
        self._reg_request_event = threading.Event()
        self._reg_done_event    = threading.Event()
        self._reg_result        = {}       # {"success": bool, "message": str}

    # ------------------------------------------------------------------ #
    #  State
    # ------------------------------------------------------------------ #
    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @state.setter
    def state(self, new_state: str):
        with self._lock:
            if self._state != new_state:
                print(f"[STATE] {self._state} --> {new_state}")
                self._state = new_state

    # ------------------------------------------------------------------ #
    #  Pairing
    # ------------------------------------------------------------------ #
    def set_paired(self):
        """Gọi khi điện thoại truy cập /pair. Chuyển sang PAIRED_BUT_NO_TARGET."""
        with self._lock:
            if not self._paired:
                self._paired = True
                if self._state == State.WAIT_FOR_PAIR:
                    print("[STATE] WAIT_FOR_PAIR --> PAIRED_BUT_NO_TARGET  (phone paired)")
                    self._state = State.PAIRED_BUT_NO_TARGET

    def reset_pairing(self):
        """Reset toàn bộ về trạng thái ban đầu (bao gồm xoá emergency stop)."""
        with self._lock:
            self._paired     = False
            self._registered = False
            self._emergency  = False
            self._state      = State.WAIT_FOR_PAIR
            self._left_spd   = 0
            self._right_spd  = 0
            self._last_sim   = 0.0
        self._reg_request_event.clear()
        self._reg_done_event.clear()
        self._reg_result = {}
        print("[STATE] Pairing reset --> WAIT_FOR_PAIR")

    # ------------------------------------------------------------------ #
    #  Emergency stop
    # ------------------------------------------------------------------ #
    def set_emergency_stop(self):
        """
        Kích hoạt dừng khẩn cấp — ưu tiên cao nhất, motor khoá cứng.
        Gọi được từ Flask thread hoặc camera thread (thread-safe).
        """
        with self._lock:
            if not self._emergency:
                self._emergency = True
                print("[STATE] *** EMERGENCY STOP ACTIVATED ***")
            self._state = State.EMERGENCY_STOP

    def clear_emergency_stop(self):
        """
        Giải phóng dừng khẩn cấp — xe tiếp tục hoạt động bình thường.
        Chỉ chuyển về PAIRED_BUT_NO_TARGET (an toàn) chứ không tự FOLLOWING.
        """
        with self._lock:
            if self._emergency:
                self._emergency = False
                print("[STATE] Emergency stop cleared --> PAIRED_BUT_NO_TARGET")
            # Chuyển về trạng thái chờ an toàn (camera loop tự cập nhật tiếp)
            if self._state == State.EMERGENCY_STOP:
                self._state = (
                    State.PAIRED_BUT_NO_TARGET if self._paired
                    else State.WAIT_FOR_PAIR
                )

    @property
    def is_emergency(self) -> bool:
        with self._lock:
            return self._emergency

    # ------------------------------------------------------------------ #
    #  Pairing
    # ------------------------------------------------------------------ #
    @property
    def is_paired(self) -> bool:
        with self._lock:
            return self._paired

    @property
    def is_registered(self) -> bool:
        with self._lock:
            return self._registered

    def set_registered(self, value: bool):
        with self._lock:
            self._registered = value

    # ------------------------------------------------------------------ #
    #  Registration handshake (Flask ↔ Camera thread)
    # ------------------------------------------------------------------ #
    def request_registration(self, timeout: float = 4.0):
        """
        Gọi từ Flask thread.
        Báo camera thread hãy chụp frame và đăng ký người.
        Block cho đến khi camera trả kết quả (hoặc timeout).

        Returns:
            (success: bool, message: str)
        """
        self._reg_result = {}
        self._reg_done_event.clear()
        self._reg_request_event.set()       # báo camera thread

        got = self._reg_done_event.wait(timeout=timeout)
        if not got:
            self._reg_request_event.clear()
            return False, "Timeout — camera không phản hồi"
        return (
            self._reg_result.get("success", False),
            self._reg_result.get("message", ""),
        )

    @property
    def registration_requested(self) -> bool:
        """Camera thread kiểm tra mỗi frame."""
        return self._reg_request_event.is_set()

    def complete_registration(self, success: bool, message: str):
        """
        Gọi từ camera thread sau khi đăng ký xong (thành công hay thất bại).
        """
        self._reg_result = {"success": success, "message": message}
        self._reg_request_event.clear()
        self._reg_done_event.set()
        with self._lock:
            self._registered = success
        print(f"[STATE] Registration complete — success={success}  msg={message}")

    # ------------------------------------------------------------------ #
    #  Motor speeds (dùng cho debug overlay)
    # ------------------------------------------------------------------ #
    def update_motor(self, left: int, right: int, similarity: float = 0.0):
        with self._lock:
            self._left_spd  = left
            self._right_spd = right
            self._last_sim  = similarity

    @property
    def motor_speeds(self):
        with self._lock:
            return self._left_spd, self._right_spd

    @property
    def last_similarity(self) -> float:
        with self._lock:
            return self._last_sim


# ------------------------------------------------------------------ #
#  Singleton
# ------------------------------------------------------------------ #
state_manager = StateManager()
