"""State machine cho Follow Me."""

import threading


class State:
    """Hang so ten trang thai."""

    IDLE = "IDLE"
    READY_TO_CAPTURE = "READY_TO_CAPTURE"
    FOLLOWING = "FOLLOWING"
    TARGET_LOST = "TARGET_LOST"
    OBSTACLE_STOP = "OBSTACLE_STOP"
    EMERGENCY_STOP = "EMERGENCY_STOP"

    # Backward-compat aliases cho code cu/web mode.
    WAIT_FOR_PAIR = IDLE
    PAIRED_BUT_NO_TARGET = READY_TO_CAPTURE


class StateManager:
    """Thread-safe state machine + registration handshake."""

    def __init__(self):
        self._lock = threading.Lock()
        self._state = State.IDLE
        self._paired = False
        self._registered = False
        self._left_spd = 0
        self._right_spd = 0
        self._last_sim = 0.0
        self._emergency = False

        self._reg_request_event = threading.Event()
        self._reg_done_event = threading.Event()
        self._reg_result = {}

        self._mc_active = False
        self._mc_snapshots = []
        self._mc_descriptors = []
        self._mc_face_enc = None
        self._mc_bboxes = []
        self._mc_last_time = 0.0
        self._mc_max = 6
        self._mc_confirmed = threading.Event()
        self._mc_done_event = threading.Event()
        self._mc_result = {}

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

    def set_paired(self):
        """Backward-compat: danh dau he thong da san sang dang ky muc tieu."""
        with self._lock:
            if not self._paired:
                self._paired = True
            if self._state == State.IDLE:
                print("[STATE] IDLE --> READY_TO_CAPTURE")
                self._state = State.READY_TO_CAPTURE

    def reset_pairing(self):
        """Backward-compat: reset toan bo session ve trang thai dau."""
        with self._lock:
            self._paired = False
            self._registered = False
            self._emergency = False
            self._state = State.IDLE
            self._left_spd = 0
            self._right_spd = 0
            self._last_sim = 0.0
        self._reg_request_event.clear()
        self._reg_done_event.clear()
        self._reg_result = {}
        self._mc_confirmed.clear()
        self._mc_done_event.clear()
        self.cancel_multi_capture()
        print("[STATE] Reset --> IDLE")

    def set_emergency_stop(self):
        with self._lock:
            if not self._emergency:
                self._emergency = True
                print("[STATE] *** EMERGENCY STOP ACTIVATED ***")
            self._state = State.EMERGENCY_STOP

    def clear_emergency_stop(self):
        with self._lock:
            if self._emergency:
                self._emergency = False
                print("[STATE] Emergency stop cleared")
            if self._state == State.EMERGENCY_STOP:
                self._state = State.READY_TO_CAPTURE if self._paired else State.IDLE

    @property
    def is_emergency(self) -> bool:
        with self._lock:
            return self._emergency

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

    def request_registration(self, timeout: float = 4.0):
        self._reg_result = {}
        self._reg_done_event.clear()
        self._reg_request_event.set()

        got = self._reg_done_event.wait(timeout=timeout)
        if not got:
            self._reg_request_event.clear()
            return False, "Timeout - camera khong phan hoi"
        return (
            self._reg_result.get("success", False),
            self._reg_result.get("message", ""),
        )

    @property
    def registration_requested(self) -> bool:
        return self._reg_request_event.is_set()

    def complete_registration(self, success: bool, message: str):
        self._reg_result = {"success": success, "message": message}
        self._reg_request_event.clear()
        self._reg_done_event.set()
        with self._lock:
            self._registered = success
            self._state = State.FOLLOWING if success else State.READY_TO_CAPTURE
        print(f"[STATE] Registration complete - success={success}  msg={message}")

    def start_multi_capture(self):
        with self._lock:
            self._mc_active = True
            self._mc_snapshots = []
            self._mc_descriptors = []
            self._mc_face_enc = None
            self._mc_bboxes = []
            self._mc_last_time = 0.0
            self._mc_confirmed.clear()
            self._mc_done_event.clear()
            self._mc_result = {}
        print("[STATE] Multi-capture started (6 snapshots)")

    @property
    def mc_active(self) -> bool:
        with self._lock:
            return self._mc_active

    @property
    def mc_count(self) -> int:
        with self._lock:
            return len(self._mc_snapshots)

    @property
    def mc_last_time(self) -> float:
        with self._lock:
            return self._mc_last_time

    @mc_last_time.setter
    def mc_last_time(self, val: float):
        with self._lock:
            self._mc_last_time = val

    def add_mc_snapshot(self, jpeg_b64: str, descriptor, face_enc=None, bbox=None):
        with self._lock:
            if len(self._mc_snapshots) >= self._mc_max:
                return
            self._mc_snapshots.append({"jpeg_b64": jpeg_b64})
            self._mc_descriptors.append(descriptor)
            self._mc_bboxes.append(bbox)
            if face_enc is not None and self._mc_face_enc is None:
                self._mc_face_enc = face_enc
            count = len(self._mc_snapshots)
        print(f"[STATE] Multi-capture snapshot {count}/{self._mc_max}")

    def get_mc_snapshots(self) -> dict:
        with self._lock:
            return {
                "active": self._mc_active,
                "count": len(self._mc_snapshots),
                "max": self._mc_max,
                "done": len(self._mc_snapshots) >= self._mc_max,
                "snapshots": list(self._mc_snapshots),
            }

    def get_mc_data(self) -> tuple:
        with self._lock:
            return list(self._mc_descriptors), self._mc_face_enc, list(self._mc_bboxes)

    def confirm_multi_capture(self, timeout: float = 4.0):
        self._mc_confirmed.set()
        got = self._mc_done_event.wait(timeout=timeout)
        if not got:
            self._mc_confirmed.clear()
            return False, "Timeout - camera khong phan hoi"
        return (
            self._mc_result.get("success", False),
            self._mc_result.get("message", ""),
        )

    @property
    def mc_confirmed(self) -> bool:
        return self._mc_confirmed.is_set()

    def complete_multi_capture(self, success: bool, message: str):
        self._mc_result = {"success": success, "message": message}
        with self._lock:
            self._mc_active = False
            self._registered = success
            self._state = State.FOLLOWING if success else State.READY_TO_CAPTURE
        self._mc_confirmed.clear()
        self._mc_done_event.set()
        print(f"[STATE] Multi-capture confirm - success={success}  msg={message}")

    def cancel_multi_capture(self):
        with self._lock:
            self._mc_active = False
            self._mc_snapshots = []
            self._mc_descriptors = []
            self._mc_face_enc = None
            self._mc_bboxes = []
        self._mc_confirmed.clear()
        self._mc_done_event.clear()
        print("[STATE] Multi-capture cancelled")

    def update_motor(self, left: int, right: int, similarity: float = 0.0):
        with self._lock:
            self._left_spd = left
            self._right_spd = right
            self._last_sim = similarity

    @property
    def motor_speeds(self):
        with self._lock:
            return self._left_spd, self._right_spd

    @property
    def last_similarity(self) -> float:
        with self._lock:
            return self._last_sim

    def update_frame(self, jpeg_bytes: bytes):
        with self._lock:
            self._latest_jpeg = jpeg_bytes

    def get_frame(self) -> bytes:
        with self._lock:
            return getattr(self, "_latest_jpeg", b"")


state_manager = StateManager()
