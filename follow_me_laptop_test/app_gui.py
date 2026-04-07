"""
app_gui.py — Giao diện tkinter (offline, không cần mạng) cho hệ thống Follow Me.

Thay thế Flask + HTML khi không có internet / test trên Raspberry Pi.
Tất cả giao tiếp qua state_manager (shared memory, thread-safe).

Chạy:
  python camera_follow_laptop.py          # config.USE_GUI = True
"""

import base64
import io
import threading
import tkinter as tk

from PIL import Image, ImageTk

from state_manager import State, state_manager

# ============================================================
#  Màu sắc
# ============================================================
BG       = "#0a0a1a"
BG_PANEL = "#111118"
FG       = "#e0e0e0"
CYAN     = "#00e5ff"
GREEN    = "#00c853"
GREEN_D  = "#0d3b1a"
RED      = "#d50000"
RED_L    = "#ff1744"
ORANGE   = "#ffab00"
GRAY     = "#333333"
GRAY_L   = "#888888"


class FollowMeGUI:
    """Giao diện chính — chạy trong main thread."""

    # ---------------------------------------------------------- #
    #  Init
    # ---------------------------------------------------------- #
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Follow Me — Person Re-ID")
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Giữ reference để GC không xoá ảnh
        self._cam_photo: ImageTk.PhotoImage | None = None
        self._snap_photos: list[ImageTk.PhotoImage | None] = [None] * 6

        self._capture_polling = False
        self._closed = False

        self._build_ui()

        # Bắt đầu poll
        self._poll_camera()
        self._poll_state()

    # ---------------------------------------------------------- #
    #  Build UI
    # ---------------------------------------------------------- #
    def _build_ui(self):
        # ---- Camera feed (chiếm nhiều nhất có thể) ----
        self.cam_label = tk.Label(self.root, bg="#000", bd=0, highlightthickness=0)
        self.cam_label.pack(fill=tk.BOTH, expand=True, padx=4, pady=(4, 2))

        # ---- Status bar ----
        self.status_var = tk.StringVar(value="📷 Đứng trước camera → nhấn ĐĂNG KÝ")
        self.status_label = tk.Label(
            self.root,
            textvariable=self.status_var,
            bg=BG_PANEL, fg=GRAY_L,
            font=("Segoe UI", 9, "bold"),
            padx=6, pady=3,
            relief=tk.FLAT,
        )
        self.status_label.pack(fill=tk.X, padx=4, pady=1)

        # ---- State label ẩn (debug) ----
        self.state_var = tk.StringVar(value="")

        # ---- Controls frame ----
        ctrl = tk.Frame(self.root, bg=BG)
        ctrl.pack(fill=tk.X, padx=4, pady=2)

        # Nút ĐĂNG KÝ
        self.btn_register = tk.Button(
            ctrl, text="\U0001F4F8  ĐĂNG KÝ",
            bg=GREEN, fg="#000",
            font=("Segoe UI", 11, "bold"),
            activebackground="#00e676",
            relief=tk.FLAT, bd=0,
            cursor="hand2",
            command=self._start_capture,
        )
        self.btn_register.pack(fill=tk.X, ipady=5, pady=(0, 2))

        # ---- Snapshot carousel (ẩn ban đầu) ----
        self.snap_frame = tk.Frame(self.root, bg=BG)

        self.capture_label = tk.Label(
            self.snap_frame, text="Đang chụp… 0/6",
            bg=BG, fg=ORANGE, font=("Segoe UI", 9, "bold"),
        )
        self.capture_label.pack(pady=(0, 2))

        slots_frame = tk.Frame(self.snap_frame, bg=BG)
        slots_frame.pack()
        self.snap_labels: list[tk.Label] = []
        for i in range(6):
            lbl = tk.Label(
                slots_frame,
                width=56, height=70,
                bg="#111", fg=CYAN,
                text=str(i + 1),
                font=("Segoe UI", 8, "bold"),
                relief=tk.RIDGE,
                bd=1,
                highlightbackground=GRAY,
            )
            lbl.grid(row=0, column=i, padx=2, pady=2)
            self.snap_labels.append(lbl)

        # Nút XÁC NHẬN / HỦY
        btn_row = tk.Frame(self.snap_frame, bg=BG)
        btn_row.pack(fill=tk.X, pady=(2, 0))

        self.btn_confirm = tk.Button(
            btn_row, text="\u2705  XÁC NHẬN",
            bg=CYAN, fg="#000",
            font=("Segoe UI", 10, "bold"),
            activebackground="#4dd0e1",
            relief=tk.FLAT, bd=0,
            cursor="hand2",
            command=self._confirm,
        )

        self.btn_cancel = tk.Button(
            btn_row, text="\u274C  Hủy",
            bg=GRAY, fg="#aaa",
            font=("Segoe UI", 9),
            activebackground="#555",
            relief=tk.FLAT, bd=0,
            cursor="hand2",
            command=self._cancel,
        )

        # ---- Bottom: Emergency (compact) ----
        bottom = tk.Frame(self.root, bg=BG)
        bottom.pack(fill=tk.X, padx=4, pady=(2, 4))

        self.btn_emergency = tk.Button(
            bottom, text="\u26D4  DỪNG KHẨN CẤP",
            bg=RED, fg="#fff",
            font=("Segoe UI", 10, "bold"),
            activebackground=RED_L,
            relief=tk.FLAT, bd=0,
            cursor="hand2",
            command=self._toggle_emergency,
        )
        self.btn_emergency.pack(fill=tk.X, ipady=6, pady=(0, 2))

        self.btn_resume = tk.Button(
            bottom, text="\u25B6  TIẾP TỤC",
            bg=GREEN_D, fg="#00e676",
            font=("Segoe UI", 9, "bold"),
            activebackground="#1b5e20",
            relief=tk.FLAT, bd=0,
            cursor="hand2",
            command=self._resume,
        )
        # btn_resume ẩn ban đầu — chỉ hiện khi emergency

        # Keyboard shortcut
        self.root.bind("<KeyPress-e>", lambda e: self._toggle_emergency())
        self.root.bind("<KeyPress-r>", lambda e: self._reset())

    # ---------------------------------------------------------- #
    #  Camera feed polling
    # ---------------------------------------------------------- #
    def _poll_camera(self):
        if self._closed:
            return
        jpeg = state_manager.get_frame()
        if jpeg:
            try:
                img = Image.open(io.BytesIO(jpeg))
                # Resize to fit window width while keeping aspect ratio
                win_w = max(self.cam_label.winfo_width(), 320)
                ratio = win_w / img.width
                new_h = int(img.height * ratio)
                img = img.resize((win_w, new_h), Image.LANCZOS)
                self._cam_photo = ImageTk.PhotoImage(img)
                self.cam_label.configure(image=self._cam_photo)
            except Exception:
                pass
        self.root.after(50, self._poll_camera)

    # ---------------------------------------------------------- #
    #  State polling
    # ---------------------------------------------------------- #
    def _poll_state(self):
        if self._closed:
            return
        st = state_manager.state

        # Hiển thị trạng thái thân thiện thay vì tên hằng số
        _STATE_VI = {
            State.WAIT_FOR_PAIR:        "Sẵn sàng",
            State.PAIRED_BUT_NO_TARGET: "Chờ đăng ký",
            State.FOLLOWING:            "Đang follow",
            State.TARGET_LOST:          "Mất mục tiêu",
            State.OBSTACLE_STOP:        "Vật cản",
            State.EMERGENCY_STOP:       "DỪNG KHẨN CẤP",
        }
        self.state_var.set(_STATE_VI.get(st, st))

        if state_manager.is_emergency:
            self._set_status("⛔ DỪNG KHẨN CẤP", RED_L, "#3b0000")
            self.btn_resume.pack(fill=tk.X, ipady=6)
        else:
            self.btn_resume.pack_forget()
            if st == State.FOLLOWING:
                self._set_status("🏃 Đang follow bạn!", "#69ff47", "#0d2b1a")
            elif st == State.TARGET_LOST:
                self._set_status("⚠ Mất mục tiêu — đứng vào khung hình", "#ff5252", "#3b0d0d")
            elif st == State.OBSTACLE_STOP:
                self._set_status("🛑 Tạm dừng — vật cản phía trước", ORANGE, BG_PANEL)
            elif st in (State.WAIT_FOR_PAIR, State.PAIRED_BUT_NO_TARGET):
                if not self._capture_polling:
                    self._set_status("📷 Đứng trước camera → nhấn ĐĂNG KÝ", GRAY_L, BG_PANEL)

        self.root.after(1000, self._poll_state)

    def _set_status(self, text: str, fg_color: str, bg_color: str):
        self.status_var.set(text)
        self.status_label.configure(fg=fg_color, bg=bg_color)

    # ---------------------------------------------------------- #
    #  Multi-capture flow
    # ---------------------------------------------------------- #
    def _start_capture(self):
        # Ẩn nút đăng ký, hiện carousel
        self.btn_register.pack_forget()
        self.snap_frame.pack(fill=tk.X, padx=6, pady=3)

        # Reset slots
        for lbl in self.snap_labels:
            lbl.configure(image="", text="…", bg="#111",
                          highlightbackground=GRAY)
        self.btn_confirm.pack_forget()
        self.btn_cancel.pack_forget()
        self.capture_label.configure(text="Đang chụp… 0/6")

        self._set_status("⏳ Đứng yên trước camera…", ORANGE, BG_PANEL)
        state_manager.set_paired()          # auto-pair khi nhấn ĐĂNG KÝ
        state_manager.start_multi_capture()
        self._capture_polling = True
        self._poll_capture()

    def _poll_capture(self):
        if self._closed or not self._capture_polling:
            return

        data = state_manager.get_mc_snapshots()
        count = data["count"]

        # Fill completed slots
        for i, snap in enumerate(data["snapshots"]):
            if self._snap_photos[i] is not None:
                continue  # already filled
            try:
                jpeg_bytes = base64.b64decode(snap["jpeg_b64"])
                img = Image.open(io.BytesIO(jpeg_bytes))
                img = img.resize((56, 70), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self._snap_photos[i] = photo
                self.snap_labels[i].configure(
                    image=photo, text="",
                    highlightbackground=CYAN,
                )
            except Exception:
                pass

        self.capture_label.configure(text=f"Đang chụp… {count}/6")

        if data["done"]:
            self._capture_polling = False
            self.capture_label.configure(text="✅ Chụp xong! Kiểm tra và xác nhận")
            self._set_status("✅ Chụp xong 6 tấm — nhấn XÁC NHẬN", "#00e676", GREEN_D)
            self.btn_confirm.pack(fill=tk.X, ipady=6, pady=(4, 2))
            self.btn_cancel.pack(fill=tk.X, ipady=4)
        else:
            self.root.after(500, self._poll_capture)

    def _confirm(self):
        self.btn_confirm.configure(state=tk.DISABLED, text="⏳ Đang xác nhận…")
        self.btn_cancel.pack_forget()
        self._set_status("⏳ Đang xác nhận…", ORANGE, BG_PANEL)

        def do_confirm():
            success, msg = state_manager.confirm_multi_capture(timeout=5.0)
            if self._closed:
                return
            self.root.after(0, lambda: self._on_confirm_result(success, msg))

        threading.Thread(target=do_confirm, daemon=True).start()

    def _on_confirm_result(self, success: bool, msg: str):
        if success:
            self._set_status("✅ Đăng ký thành công! Xe đang follow bạn.",
                             "#00e676", GREEN_D)
            self.snap_frame.pack_forget()
            self.btn_register.configure(text="\U0001F504  Đăng ký lại")
            self.btn_register.pack(fill=tk.X, ipady=8, padx=6, pady=3)
        else:
            self._set_status(f"❌ {msg}", "#ff5252", "#3b0d0d")
            self.btn_confirm.configure(state=tk.NORMAL,
                                       text="\u2705  XÁC NHẬN — Bắt đầu follow")
            self.btn_cancel.pack(fill=tk.X, ipady=4)

        # Reset snap photos for next round
        self._snap_photos = [None] * 6

    def _cancel(self):
        self._capture_polling = False
        state_manager.cancel_multi_capture()
        state_manager.set_paired()          # re-pair để cho phép đăng ký lại
        self._snap_photos = [None] * 6

        self.snap_frame.pack_forget()
        self.btn_register.configure(text="\U0001F4F8  ĐĂNG KÝ")
        self.btn_register.pack(fill=tk.X, ipady=8, padx=6, pady=3)
        self._set_status("Đã hủy — nhấn ĐĂNG KÝ để thử lại", GRAY_L, BG_PANEL)

    # ---------------------------------------------------------- #
    #  Emergency
    # ---------------------------------------------------------- #
    def _toggle_emergency(self):
        if state_manager.is_emergency:
            self._resume()
        else:
            state_manager.set_emergency_stop()

    def _resume(self):
        if state_manager.is_emergency:
            state_manager.clear_emergency_stop()
            self._set_status("Xe đã mở — sẵn sàng", GRAY_L, BG_PANEL)

    def _reset(self):
        self._capture_polling = False
        state_manager.reset_pairing()
        self._snap_photos = [None] * 6
        self.snap_frame.pack_forget()
        self.btn_register.configure(text="\U0001F4F8  ĐĂNG KÝ")
        self.btn_register.pack(fill=tk.X, ipady=8, padx=6, pady=3)
        self._set_status("Đã reset — nhấn ĐĂNG KÝ", GRAY_L, BG_PANEL)

    # ---------------------------------------------------------- #
    #  Cleanup
    # ---------------------------------------------------------- #
    def _on_close(self):
        self._closed = True
        self.root.destroy()


# ============================================================
#  Entry point (gọi từ camera_follow_laptop.py)
# ============================================================

def run_gui():
    """Chạy tkinter mainloop — phải gọi từ main thread."""
    root = tk.Tk()
    root.geometry("800x480")
    root.minsize(480, 360)
    app = FollowMeGUI(root)
    root.mainloop()
    return app._closed  # signal camera thread to stop
