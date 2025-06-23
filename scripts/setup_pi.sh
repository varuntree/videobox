#!/bin/bash
# Setup script for Raspberry Pi

set -e

echo "=== VoiceBox Pi Setup ==="
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
    git

# Create project directory
echo "3. Setting up project directory..."
cd /home/pi
if [ ! -d "videobox" ]; then
    echo "   Creating videobox directory..."
    mkdir -p videobox
fi

# Set up Python virtual environment
echo "4. Setting up Python environment..."
cd /home/pi/videobox
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "5. Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if not exists
if [ ! -f ".env" ]; then
    echo "6. Creating .env file..."
    cp .env.example .env
    echo "   ⚠️  Add your PICOVOICE_ACCESS_KEY to .env file!"
fi

# Set permissions
echo "7. Setting permissions..."
chmod +x src/voicebox.py
chmod +x src/test_hardware.py

echo
echo "=== Setup Complete ==="
echo
echo "Next steps:"
echo "1. Edit .env and add your PICOVOICE_ACCESS_KEY"
echo "2. Add your video files to the videos/ directory"
echo "3. Run: ./venv/bin/python src/test_hardware.py"
echo "4. Run: ./venv/bin/python src/voicebox.py"