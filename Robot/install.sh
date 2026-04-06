#!/bin/bash
# ===== INSTALLATION SCRIPT FOR RASPBERRY PI =====
# Cài đặt tự động các dependencies cho RoboticHutech Robot

echo "╔════════════════════════════════════════════════════╗"
echo "║     ROBOTIC HUTECH - INSTALLATION SCRIPT          ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Warning: This script is optimized for Raspberry Pi${NC}"
    echo "   Proceeding anyway..."
fi

echo ""
echo "📦 Step 1: Update system packages"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

sudo apt-get update -y
sudo apt-get upgrade -y

echo -e "${GREEN}✓ System updated${NC}\n"

echo "📦 Step 2: Install Python dependencies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

sudo apt-get install -y python3 python3-pip python3-dev

echo -e "${GREEN}✓ Python installed${NC}\n"

echo "📦 Step 3: Install RPi.GPIO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

sudo apt-get install -y python3-rpi.gpio

echo -e "${GREEN}✓ RPi.GPIO installed${NC}\n"

echo "📦 Step 4: Install OpenCV"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

sudo apt-get install -y libatlas-base-dev libjasper-dev libtiff5 libjasper1 libharfbuzz0b libwebp6 libtiff5 libharfbuzz0b libwebp6

pip3 install opencv-python --no-cache-dir

echo -e "${GREEN}✓ OpenCV installed${NC}\n"

echo "📦 Step 5: Install Python packages"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

pip3 install numpy==1.19.5 --no-cache-dir

echo -e "${GREEN}✓ Python packages installed${NC}\n"

echo "📦 Step 6: Optional packages"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "Cài thêm Flask cho web control? (y/n)"
read -r install_flask

if [ "$install_flask" = "y" ]; then
    pip3 install flask
    echo -e "${GREEN}✓ Flask installed${NC}"
fi

echo ""
echo "📦 Step 7: Download YOLO models (Optional)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

read -p "Download YOLOv3-tiny? (235MB, y/n): " install_yolo

if [ "$install_yolo" = "y" ]; then
    cd "$(dirname "$0")"
    
    echo "Downloading YOLO weights..."
    wget https://pjreddie.com/media/files/yolov3-tiny.weights -q --show-progress
    
    echo "Downloading YOLO config..."
    wget https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3-tiny.cfg -q --show-progress
    
    echo "Downloading COCO names..."
    wget https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names -q --show-progress
    
    echo -e "${GREEN}✓ YOLO files downloaded${NC}"
fi

echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║          ✅ INSTALLATION COMPLETE!                ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""
echo "📝 Next steps:"
echo "   1. Edit config.py to set GPIO pins correctly"
echo "   2. Run: sudo python3 calibration.py (for calibration)"
echo "   3. Run: sudo python3 test_brain.py (to test modules)"
echo "   4. Run: sudo python3 main.py (to start the robot)"
echo ""
echo "📖 For more info, see README.md"
echo ""
