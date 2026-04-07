"""
app_server.py — Flask web server cho hệ thống Follow Me (Person Re-ID).

Routes:
  GET  /               → Trang chủ với QR code để pair
  GET  /qr_image       → Ảnh QR code (PNG)
  GET  /pair           → Điện thoại đến đây sau khi quét QR, hiển thị trang đăng ký
  POST /capture_target → Điện thoại gửi lên → camera thread chụp và đăng ký người
  GET  /pair_status    → JSON {"paired", "registered", "state", "emergency"}
  POST /emergency_stop → Kích hoạt dừng khẩn cấp (motor khoá cứng)
  POST /resume         → Giải phóng dừng khẩn cấp, xe tiếp tục
  POST /reset          → Reset pairing về trạng thái ban đầu
"""

import io
import logging
import time

import qrcode
from flask import Flask, Response, jsonify, render_template, request, send_file

import config
from state_manager import State, state_manager

logging.getLogger("werkzeug").setLevel(logging.WARNING)

app = Flask(__name__)


# ============================================================
#  Routes
# ============================================================

@app.route("/")
def index():
    """Trang chủ: hiển thị QR code và hướng dẫn pair."""
    ip       = config.get_local_ip()
    pair_url = f"http://{ip}:{config.SERVER_PORT}/pair"
    return render_template("index.html", pair_url=pair_url, ip=ip, port=config.SERVER_PORT)


@app.route("/qr_image")
def qr_image():
    """Tạo và trả về QR code trỏ tới /pair (PNG)."""
    ip       = config.get_local_ip()
    pair_url = f"http://{ip}:{config.SERVER_PORT}/pair"

    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=4,
    )
    qr.add_data(pair_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", max_age=0, as_attachment=False)


@app.route("/pair")
def pair():
    """
    Điện thoại vào đây sau khi quét QR.
    Đánh dấu paired và hiển thị trang đăng ký người.
    """
    state_manager.set_paired()
    client_ip = request.remote_addr
    print(f"[SERVER] /pair  <-- {client_ip}  → paired!")
    return render_template("marker.html")   # marker.html giờ là trang pair/register


@app.route("/capture_target", methods=["POST"])
def capture_target():
    """
    Điện thoại POST endpoint này khi người dùng nhấn nút ĐĂNG KÝ.

    Flow:
      1. Flask set registration_requested event trong state_manager
      2. Camera thread phát hiện, chụp frame ngay, đăng ký người gần tâm nhất
      3. Camera thread trả kết quả qua complete_registration()
      4. Flask chờ tối đa 4 giây rồi trả JSON về điện thoại

    Returns:
        JSON {"success": bool, "message": str}
    """
    if not state_manager.is_paired:
        return jsonify({"success": False, "message": "Chưa pair — quét QR trước"}), 400

    print(f"[SERVER] /capture_target  <-- {request.remote_addr}  → registration requested")

    # Block Flask thread, chờ camera thread xử lý (timeout 4s)
    success, message = state_manager.request_registration(timeout=4.0)

    print(f"[SERVER] Registration result: success={success}  msg={message}")
    return jsonify({"success": success, "message": message})


@app.route("/pair_status")
def pair_status():
    """
    JSON API — điện thoại poll để cập nhật trạng thái.
    Response: {"paired", "registered", "state", "emergency"}
    """
    return jsonify({
        "paired":     state_manager.is_paired,
        "registered": state_manager.is_registered,
        "state":      state_manager.state,
        "emergency":  state_manager.is_emergency,
    })


@app.route("/emergency_stop", methods=["POST"])
def emergency_stop():
    """
    Kích hoạt dừng khẩn cấp tức thì.
    Motor khoá cứng 0,0 cho đến khi /resume được gọi.
    """
    print(f"[SERVER] /emergency_stop  <-- {request.remote_addr}")
    state_manager.set_emergency_stop()
    return jsonify({"status": "ok", "message": "Emergency stop activated"})


@app.route("/resume", methods=["POST"])
def resume():
    """
    Giải phóng dừng khẩn cấp.
    Chỉ hoạt động khi đang ở trạng thái EMERGENCY_STOP.
    """
    if not state_manager.is_emergency:
        return jsonify({"status": "noop", "message": "Không ở trạng thái emergency"})
    print(f"[SERVER] /resume  <-- {request.remote_addr}")
    state_manager.clear_emergency_stop()
    return jsonify({"status": "ok", "message": "Resumed"})


@app.route("/reset", methods=["POST"])
def reset():
    """Reset pairing + đăng ký (dùng khi test lại mà không restart server)."""
    state_manager.reset_pairing()
    return jsonify({"status": "ok", "message": "Pairing + registration reset"})


# ============================================================
#  Multi-capture (chụp 6 tấm → xác nhận)
# ============================================================

@app.route("/start_capture", methods=["POST"])
def start_capture():
    """Điện thoại nhấn ĐĂNG KÝ → bắt đầu chụp 6 tấm."""
    if not state_manager.is_paired:
        return jsonify({"success": False, "message": "Chưa pair — quét QR trước"}), 400
    state_manager.start_multi_capture()
    return jsonify({"success": True, "message": "Bắt đầu chụp"})


@app.route("/capture_progress")
def capture_progress():
    """Điện thoại poll để lấy thumbnails đang chụp."""
    return jsonify(state_manager.get_mc_snapshots())


@app.route("/confirm_target", methods=["POST"])
def confirm_target():
    """Điện thoại xác nhận 6 tấm → camera thread đăng ký."""
    if not state_manager.mc_active and state_manager.mc_count < 6:
        return jsonify({"success": False, "message": "Chưa chụp đủ"}), 400
    success, message = state_manager.confirm_multi_capture(timeout=4.0)
    return jsonify({"success": success, "message": message})


@app.route("/cancel_capture", methods=["POST"])
def cancel_capture():
    """Điện thoại hủy capture."""
    state_manager.cancel_multi_capture()
    return jsonify({"status": "ok"})


# ============================================================
#  Video feed (MJPEG stream cho web)
# ============================================================

def _gen_mjpeg():
    """Generator: yield JPEG frames liên tục cho MJPEG stream."""
    while True:
        jpeg = state_manager.get_frame()
        if jpeg:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
            )
        time.sleep(0.05)   # ~20 FPS max


@app.route("/video_feed")
def video_feed():
    """MJPEG stream — dùng trong <img src="/video_feed">."""
    return Response(
        _gen_mjpeg(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


# ============================================================
#  Entry point
# ============================================================

def run_server():
    """Khởi động Flask. Gọi trong daemon thread từ camera_follow_laptop.py."""
    ip = config.get_local_ip()
    print(f"[SERVER] Flask starting on http://0.0.0.0:{config.SERVER_PORT}")
    print(f"[SERVER] LAN URL : http://{ip}:{config.SERVER_PORT}/")
    app.run(
        host="0.0.0.0",
        port=config.SERVER_PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


if __name__ == "__main__":
    run_server()
