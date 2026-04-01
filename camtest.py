import cv2

def main():
    # Khởi tạo camera qua backend GStreamer hoặc V4L2
    # Với Raspberry Pi 4, index 0 thường là camera mặc định
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Lỗi: Không thể mở camera. Kiểm tra kết nối!")
        return

    print("Đang hiển thị camera. Nhấn 'q' để thoát.")

    while True:
        # Đọc từng khung hình (frame) từ camera
        ret, frame = cap.read()

        if not ret:
            print("Lỗi: Không thể nhận dữ liệu hình ảnh.")
            break

        # Hiển thị khung hình lên một cửa sổ có tên 'Arducam Live'
        cv2.imshow('Arducam Live', frame)

        # Đợi 1ms và kiểm tra nếu người dùng nhấn phím 'q' thì thoát
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Giải phóng tài nguyên
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()