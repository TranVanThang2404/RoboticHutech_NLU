#!/bin/bash
# setup_raspi.sh  Cai dat tu dong cho Follow Me tren Raspberry Pi 4B
# Chay mot lan duy nhat sau khi git clone:
#   chmod +x setup_raspi.sh && sudo bash setup_raspi.sh

set -e
echo "=================================================="
echo "  Follow Me RPi Setup"
echo "=================================================="

# ---------- 1. /boot/config.txt ----------
CONFIG="/boot/config.txt"
echo ""
echo "[1/4] Cap nhat $CONFIG ..."

add_if_missing() {
    local line="$1"
    if ! grep -qxF "$line" "$CONFIG"; then
        echo "$line" >> "$CONFIG"
        echo "  THEM: $line"
    else
        echo "  DA CO: $line"
    fi
}

add_if_missing "dtoverlay=disable-bt"
add_if_missing "dtoverlay=uart3"

echo "  => Xong $CONFIG"

# ---------- 2. Tat login shell tren serial ----------
echo ""
echo "[2/4] Tat login shell tren serial (UART0 cho motor) ..."
# Xoa console=serial0 khoi cmdline.txt neu co
CMDLINE="/boot/cmdline.txt"
if grep -q "console=serial0" "$CMDLINE"; then
    sed -i 's/console=serial0,[0-9]* //g' "$CMDLINE"
    echo "  DA XOA console=serial0 khoi $CMDLINE"
else
    echo "  OK (khong co console=serial0)"
fi

# Tat serial getty service
systemctl disable serial-getty@ttyAMA0.service 2>/dev/null || true
echo "  Da tat serial-getty service"

# ---------- 3. Cai pip packages ----------
echo ""
echo "[3/4] Cai Python packages ..."
pip3 install pyserial RPi.GPIO flask opencv-python numpy "qrcode[pil]" Pillow ultralytics --break-system-packages 2>/dev/null \
  || pip3 install pyserial RPi.GPIO flask opencv-python numpy "qrcode[pil]" Pillow ultralytics
echo "  => Xong cai packages"

# ---------- 4. Them user vao group gpio/dialout ----------
echo ""
echo "[4/4] Them user '$SUDO_USER' vao group gpio + dialout ..."
if [ -n "$SUDO_USER" ]; then
    usermod -aG gpio,dialout "$SUDO_USER"
    echo "  => Da them $SUDO_USER vao gpio + dialout"
else
    echo "  CANH BAO: Chay bang sudo, khong xac dinh duoc user goc"
    echo "  Chay them: sudo usermod -aG gpio,dialout \$USER"
fi

echo ""
echo "=================================================="
echo "  Hoan tat! Vui long REBOOT de ap dung:"
echo "    sudo reboot"
echo ""
echo "  Sau khi reboot, kiem tra:"
echo "    ls /dev/ttyAMA*"
echo "    # Phai thay: /dev/ttyAMA0  /dev/ttyAMA3"
echo ""
echo "  Test cam bien SEN0311:"
echo "    python3 ultrasonic_raspi.py"
echo ""
echo "  Chay chinh:"
echo "    python3 camera_follow_laptop.py"
echo "=================================================="