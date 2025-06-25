#!/bin/bash
# Updated setup script for Vosk version

set -e

echo "=== VoiceBox Pi Setup (Vosk Version) ==="
echo

# Update system
echo "1. Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install system dependencies
echo "2. Installing system dependencies..."
sudo apt install -y \
    mpv \
    python3-pip \
    python3-venv \
    portaudio19-dev \
    libatlas-base-dev \
    git \
    xserver-xorg \
    xinit \
    unclutter \
    wget \
    unzip \
    udev

# Set up Python virtual environment
echo "3. Setting up Python environment..."
cd /home/varun/videobox
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "4. Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Download Vosk model if not exists
echo "5. Setting up Vosk model..."
if [ ! -d "models/vosk-model-en-us-small" ]; then
    mkdir -p models
    cd models
    echo "   Downloading Vosk model (50MB)..."
    wget -q https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    unzip -q vosk-model-small-en-us-0.15.zip
    mv vosk-model-small-en-us-0.15 vosk-model-en-us-small
    rm vosk-model-small-en-us-0.15.zip
    cd ..
    echo "   ✓ Vosk model installed"
else
    echo "   ✓ Vosk model already exists"
fi

# Create .env file
echo "6. Setting up configuration..."
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
VOSK_MODEL_PATH=/home/varun/videobox/models/vosk-model-en-us-small
USB_MOUNT_POINT=/media/usb
MIN_CONFIDENCE=0.7
EOF
    echo "   ✓ Created .env file"
else
    echo "   ✓ .env file already exists"
fi

# Set permissions
echo "7. Setting permissions..."
chmod +x src/voicebox.py
chmod +x src/test_hardware.py

# Configure kiosk mode
echo "8. Configuring kiosk mode..."
# Disable LXDE autostart
sudo systemctl disable lightdm.service 2>/dev/null || true
rm -f ~/.config/autostart/voicebox.desktop 2>/dev/null || true
sudo systemctl disable voicebox.service 2>/dev/null || true

# Install kiosk configuration files
cp config/.xinitrc ~/.xinitrc
chmod +x ~/.xinitrc
sudo cp config/voicebox-kiosk.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable voicebox-kiosk.service

echo
echo "=== Setup Complete ==="
echo
echo "Next steps:"
echo "1. Add video files to videos/ directory or USB drive"
echo "2. Test: ./venv/bin/python src/test_hardware.py"
echo "3. Run: ./venv/bin/python src/voicebox.py"
echo "4. For production: sudo reboot (will auto-start kiosk mode)"
echo
echo "Now supports any spoken filename as a voice command!"