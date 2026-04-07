"""
Export YOLOv8n sang ONNX input 320x320 de giam tai cho Raspberry Pi 4B.

Chay tren may da cai ultralytics:
    pip install ultralytics
    python export_onnx_320.py

Ket qua:
    tao file yolov8n_320.onnx trong cung thu muc voi script.
Sau do doi ten/noi dung file ONNX tren Raspberry Pi theo nhu cau.
"""

from pathlib import Path


def main():
    from ultralytics import YOLO

    root = Path(__file__).resolve().parent
    src = root / "yolov8n.pt"
    if not src.exists():
        raise FileNotFoundError(f"Khong tim thay model: {src}")

    model = YOLO(str(src))
    out = model.export(format="onnx", imgsz=320, opset=12, simplify=True)
    print(f"Export xong: {out}")


if __name__ == "__main__":
    main()
