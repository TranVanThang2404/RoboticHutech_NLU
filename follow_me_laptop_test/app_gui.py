"""GUI tkinter offline: chup, dang ky, va follow truc tiep tren man hinh."""

import io
import threading
import tkinter as tk

from PIL import Image, ImageTk

from state_manager import State, state_manager

BG = "#0a0a1a"
BG_PANEL = "#111118"
CYAN = "#00e5ff"
GREEN = "#00c853"
GREEN_D = "#0d3b1a"
RED = "#d50000"
RED_L = "#ff1744"
ORANGE = "#ffab00"
GRAY_L = "#888888"


class FollowMeGUI:
    """Giao dien chinh cho che do GUI."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Follow Me - GUI")
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._cam_photo: ImageTk.PhotoImage | None = None
        self._closed = False
        self._registering = False

        self._build_ui()
        self._poll_camera()
        self._poll_state()

    def _build_ui(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)
        self.root.grid_columnconfigure(0, weight=1)

        self.cam_label = tk.Label(self.root, bg="#000", bd=0, highlightthickness=0)
        self.cam_label.grid(row=0, column=0, sticky="nsew", padx=4, pady=(4, 2))

        panel = tk.Frame(self.root, bg=BG)
        panel.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 4))

        self.status_var = tk.StringVar(value="Dung truoc camera va nhan CHUP & THEO DOI")
        self.status_label = tk.Label(
            panel,
            textvariable=self.status_var,
            bg=BG_PANEL,
            fg=GRAY_L,
            font=("Segoe UI", 10, "bold"),
            padx=8,
            pady=4,
            relief=tk.FLAT,
            anchor="w",
        )
        self.status_label.pack(fill=tk.X, pady=(0, 4))

        self.btn_register = tk.Button(
            panel,
            text="CHUP & THEO DOI",
            bg=GREEN,
            fg="#000",
            font=("Segoe UI", 12, "bold"),
            activebackground="#00e676",
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=self._register_target,
        )
        self.btn_register.pack(fill=tk.X, ipady=8, pady=(0, 4))

        self.btn_reset_target = tk.Button(
            panel,
            text="DANG KY LAI",
            bg=CYAN,
            fg="#000",
            font=("Segoe UI", 10, "bold"),
            activebackground="#4dd0e1",
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=self._reset,
        )
        self.btn_reset_target.pack(fill=tk.X, ipady=6, pady=(0, 4))

        self.btn_emergency = tk.Button(
            panel,
            text="DUNG KHAN CAP",
            bg=RED,
            fg="#fff",
            font=("Segoe UI", 10, "bold"),
            activebackground=RED_L,
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=self._toggle_emergency,
        )
        self.btn_emergency.pack(fill=tk.X, ipady=6, pady=(0, 4))

        self.btn_resume = tk.Button(
            panel,
            text="TIEP TUC",
            bg=GREEN_D,
            fg="#00e676",
            font=("Segoe UI", 10, "bold"),
            activebackground="#1b5e20",
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=self._resume,
        )

        self.root.bind("<KeyPress-e>", lambda e: self._toggle_emergency())
        self.root.bind("<KeyPress-r>", lambda e: self._reset())

    def _poll_camera(self):
        if self._closed:
            return
        jpeg = state_manager.get_frame()
        if jpeg:
            try:
                img = Image.open(io.BytesIO(jpeg))
                self.root.update_idletasks()
                avail_w = max(self.cam_label.winfo_width(), 320)
                avail_h = max(self.cam_label.winfo_height(), 180)
                ratio = min(avail_w / max(img.width, 1), avail_h / max(img.height, 1))
                ratio = max(ratio, 0.1)
                new_w = max(1, int(img.width * ratio))
                new_h = max(1, int(img.height * ratio))
                img = img.resize((new_w, new_h), Image.LANCZOS)
                self._cam_photo = ImageTk.PhotoImage(img)
                self.cam_label.configure(image=self._cam_photo)
            except Exception:
                pass
        self.root.after(50, self._poll_camera)

    def _poll_state(self):
        if self._closed:
            return

        st = state_manager.state
        if state_manager.is_emergency:
            self._set_status("DUNG KHAN CAP", RED_L, "#3b0000")
            self.btn_resume.pack(fill=tk.X, ipady=6)
        else:
            self.btn_resume.pack_forget()
            if self._registering:
                self._set_status("Dang chup va dang ky muc tieu...", ORANGE, BG_PANEL)
            elif st == State.FOLLOWING:
                self._set_status("Dang follow nguoi da chup", "#69ff47", "#0d2b1a")
            elif st == State.TARGET_LOST:
                self._set_status("Mat muc tieu - dung vao giua khung hinh", "#ff5252", "#3b0d0d")
            elif st == State.OBSTACLE_STOP:
                self._set_status("Tam dung - co vat can phia truoc", ORANGE, BG_PANEL)
            elif st == State.READY_TO_CAPTURE:
                self._set_status("San sang chup muc tieu", GRAY_L, BG_PANEL)
            else:
                self._set_status("Dung truoc camera va nhan CHUP & THEO DOI", GRAY_L, BG_PANEL)

        self.root.after(500, self._poll_state)

    def _set_status(self, text: str, fg_color: str, bg_color: str):
        self.status_var.set(text)
        self.status_label.configure(fg=fg_color, bg=bg_color)

    def _register_target(self):
        if self._registering:
            return
        self._registering = True
        self.btn_register.configure(state=tk.DISABLED, text="DANG CHUP...")
        self._set_status("Dang chup va luu nguoi dang dung truoc camera...", ORANGE, BG_PANEL)

        def do_register():
            success, msg = state_manager.request_registration(timeout=5.0)
            if self._closed:
                return
            self.root.after(0, lambda: self._on_register_result(success, msg))

        threading.Thread(target=do_register, daemon=True).start()

    def _on_register_result(self, success: bool, msg: str):
        self._registering = False
        self.btn_register.configure(state=tk.NORMAL, text="CHUP & THEO DOI")
        if success:
            self._set_status(msg, "#00e676", GREEN_D)
        else:
            self._set_status(msg, "#ff5252", "#3b0d0d")

    def _toggle_emergency(self):
        if state_manager.is_emergency:
            self._resume()
        else:
            state_manager.set_emergency_stop()

    def _resume(self):
        if state_manager.is_emergency:
            state_manager.clear_emergency_stop()
            self._set_status("Da tiep tuc - san sang follow", GRAY_L, BG_PANEL)

    def _reset(self):
        self._registering = False
        state_manager.reset_pairing()
        self.btn_register.configure(state=tk.NORMAL, text="CHUP & THEO DOI")
        self._set_status("Da reset - nhan CHUP & THEO DOI de dang ky lai", GRAY_L, BG_PANEL)

    def _on_close(self):
        self._closed = True
        self.root.destroy()


def run_gui():
    """Chay tkinter mainloop."""
    root = tk.Tk()
    root.geometry("800x480")
    root.minsize(480, 320)
    app = FollowMeGUI(root)
    root.mainloop()
    return app._closed
