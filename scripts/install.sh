#!/bin/bash
# Complete VoiceBox system installation

set -e

echo "==========================================="
echo "VoiceBox Dynamic System Installation"
echo "==========================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "Don't run this script as root. Run as regular user (varun)."
   exit 1
fi

USER_NAME=$(whoami)
PROJECT_DIR="/home/${USER_NAME}/voicebox"

echo "Installing for user: ${USER_NAME}"
echo "Installation directory: ${PROJECT_DIR}"
echo


# 1. System packages
echo "1. Installing system packages..."
sudo apt update
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    mpv \
    portaudio19-dev \
    libatlas-base-dev \
    git \
    wget \
    unzip \
    udev \
    pulseaudio \
    alsa-utils

# 2. Create project directory
echo "2. Setting up project directory..."
mkdir -p "${PROJECT_DIR}"/{src,config,scripts,models,videos}

# 3. Python virtual environment
echo "3. Setting up Python environment..."
cd "${PROJECT_DIR}"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# 4. Install Python packages
echo "4. Installing Python packages..."
pip install vosk sounddevice numpy psutil python-dotenv watchdog

# 5. Download Vosk model
echo "5. Downloading Vosk speech model (50MB)..."
cd models
if [ ! -d "vosk-model-en-us-small" ]; then
    wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    unzip -q vosk-model-small-en-us-0.15.zip
    mv vosk-model-small-en-us-0.15 vosk-model-en-us-small
    rm vosk-model-small-en-us-0.15.zip
    echo "   ✓ Vosk model installed"
else
    echo "   ✓ Vosk model already exists"
fi

# 6. Create configuration files
echo "6. Creating configuration files..."
cd "${PROJECT_DIR}"

# Create .env file
cat > .env << EOF
VOSK_MODEL_PATH=${PROJECT_DIR}/models/vosk-model-en-us-small
MIN_CONFIDENCE=0.7
VIDEO_DIR=${PROJECT_DIR}/videos
USB_MOUNT_POINT=/media/usb
SAMPLE_RATE=16000
AUDIO_BLOCK_SIZE=1600
DISPLAY_WIDTH=800
DISPLAY_HEIGHT=480
FULLSCREEN=true
LOG_LEVEL=INFO
DEBUG_MODE=false
EOF

# 7. Set up USB auto-mounting
echo "7. Setting up USB auto-mounting..."
sudo tee /etc/udev/rules.d/99-usb-automount.rules > /dev/null << 'EOF'
# Auto-mount USB storage devices
KERNEL=="sd[a-z]*", SUBSYSTEM=="block", ENV{ID_FS_TYPE}!="", \
  RUN+="/bin/mkdir -p /media/usb%n", \
  RUN+="/bin/mount -o uid=1000,gid=1000 /dev/%k /media/usb%n"
EOF

sudo udevadm control --reload-rules

# 8. Create systemd service
echo "8. Creating systemd service..."
sudo tee /etc/systemd/system/voicebox.service > /dev/null << EOF
[Unit]
Description=VoiceBox Dynamic Voice Recognition System
After=graphical.target sound.service

[Service]
Type=simple
User=${USER_NAME}
Group=${USER_NAME}
WorkingDirectory=${PROJECT_DIR}
Environment="DISPLAY=:0"
Environment="PULSE_RUNTIME_PATH=/run/user/1000/pulse"
ExecStart=${PROJECT_DIR}/venv/bin/python ${PROJECT_DIR}/src/voicebox.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical.target
EOF

sudo systemctl daemon-reload

# 9. Set permissions
echo "9. Setting permissions..."
chmod +x src/*.py
chmod +x scripts/*.sh

echo
echo "==========================================="
echo "Installation Complete!"
echo "==========================================="
echo
echo "Next steps:"
echo "1. Copy your video files to: ${PROJECT_DIR}/videos/"
echo "2. Test the system: ${PROJECT_DIR}/venv/bin/python ${PROJECT_DIR}/src/test_system.py"
echo "3. Run manually: ${PROJECT_DIR}/venv/bin/python ${PROJECT_DIR}/src/voicebox.py"
echo "4. Enable autostart: sudo systemctl enable voicebox"
echo "5. Start service: sudo systemctl start voicebox"
echo
echo "To test with USB videos:"
echo "- Put video files on USB drive"
echo "- Plug into Raspberry Pi"
echo "- Speak the filename (without extension)"
echo
echo "System is ready for voice-activated video playback!"