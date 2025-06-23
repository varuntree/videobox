# VoiceBox Implementation Plan for Claude Code

## Project Overview
Voice-activated video display system that continuously plays a "listening" animation and responds to voice commands ("americano", "bumblebee", "grasshopper") by playing corresponding videos. Built for Raspberry Pi 3B with Pi OS 32-bit (with desktop).

**Simplified Approach**: Uses built-in Picovoice wake words (no .ppn files needed!).

## Phase 1: Local Project Setup

### 1.1 Create Project Repository Structure
```
videobox/
├── src/
│   ├── voicebox.py              # Main control script
│   └── test_hardware.py         # Hardware test script
├── config/
│   ├── voicebox.service         # Systemd service (for later)
│   └── voicebox.desktop         # Autostart file (for later)
├── scripts/
│   ├── setup_pi.sh              # Pi setup script
│   └── deploy.sh                # Deployment script
├── videos/
│   ├── listening.mp4            # Continuous mic animation
│   ├── americano.mp4            # Response to "americano"
│   ├── bumblebee.mp4            # Response to "bumblebee"
│   └── grasshopper.mp4          # Response to "grasshopper"
├── voice_files/                 # Optional: Custom wake word files
│   └── detective_en_raspberry-pi_v3_0_0.zip
├── ai_docs/                     # Project documentation
│   └── spec.md                  # This specification
├── .env.example                 # Example environment file
├── .gitignore
├── requirements.txt
└── README.md
```

### 1.2 Create voicebox.py
```python
#!/usr/bin/env python3
"""
VoiceBox - Voice-Activated Video Display
Continuously plays listening animation, responds to voice commands
"""

import subprocess
import sys
import time
import signal
import os
import sounddevice as sd
import pvporcupine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
ACCESS_KEY = os.getenv('PICOVOICE_ACCESS_KEY', '')
# Using built-in wake words - no .ppn files needed!
WAKE_WORDS = ['americano', 'bumblebee', 'grasshopper']
VIDEO_PATHS = {
    0: "/home/pi/videobox/videos/americano.mp4",    # americano keyword
    1: "/home/pi/videobox/videos/bumblebee.mp4",    # bumblebee keyword
    2: "/home/pi/videobox/videos/grasshopper.mp4"   # grasshopper keyword
}
LISTENING_VIDEO = "/home/pi/videobox/videos/listening.mp4"

# Window mode flag (set False for fullscreen)
WINDOW_MODE = True

# Global process reference
current_video = None

def get_mpv_command(video_path, loop=False):
    """Build mpv command based on mode"""
    cmd = [
        'mpv',
        '--hwdec=mmal',
        '--really-quiet',
        '--no-osc',              # No on-screen controller
        '--no-input-default-bindings',  # Disable keyboard shortcuts
    ]
    
    if loop:
        cmd.append('--loop-file=inf')
    
    if WINDOW_MODE:
        cmd.extend(['--geometry=800x480', '--title=VoiceBox'])
    else:
        cmd.extend(['--fullscreen', '--fs'])
    
    cmd.append(video_path)
    return cmd

def play_listening_video():
    """Start playing the listening animation in a loop"""
    global current_video
    stop_current_video()
    print("Starting listening animation...")
    current_video = subprocess.Popen(get_mpv_command(LISTENING_VIDEO, loop=True))
    return current_video

def stop_current_video():
    """Stop any currently playing video"""
    global current_video
    if current_video and current_video.poll() is None:
        current_video.terminate()
        try:
            current_video.wait(timeout=2)
        except subprocess.TimeoutExpired:
            current_video.kill()
            current_video.wait()
        current_video = None
        time.sleep(0.1)  # Small delay for smooth transition

def play_response_video(video_path):
    """Play a response video once, then return to listening"""
    global current_video
    stop_current_video()
    print(f"Playing response video: {os.path.basename(video_path)}")
    
    # Play response video and wait for completion
    process = subprocess.Popen(get_mpv_command(video_path, loop=False))
    process.wait()
    
    # Return to listening animation
    play_listening_video()

def cleanup(signum=None, frame=None):
    """Clean shutdown handler"""
    print("\nShutting down VoiceBox...")
    stop_current_video()
    sys.exit(0)

def main():
    # Set up signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    print("="*50)
    print("VoiceBox Starting Up")
    print(f"Mode: {'Window' if WINDOW_MODE else 'Fullscreen'}")
    print("="*50)
    
    # Verify access key
    if not ACCESS_KEY:
        print("ERROR: No Picovoice access key found!")
        print("Set PICOVOICE_ACCESS_KEY in .env file")
        sys.exit(1)
    
    # Initialize Porcupine with built-in keywords
    try:
        porcupine = pvporcupine.create(
            access_key=ACCESS_KEY,
            keywords=WAKE_WORDS  # Using built-in keywords!
        )
        print("✓ Porcupine initialized with built-in keywords")
    except Exception as e:
        print(f"✗ Failed to initialize Porcupine: {e}")
        sys.exit(1)
    
    # Start listening animation
    play_listening_video()
    
    # Audio callback for processing
    def audio_callback(indata, frames, time_info, status):
        if status:
            print(f"Audio error: {status}")
        
        # Convert to int16 for Porcupine
        audio_frame = (indata[:, 0] * 32767).astype('int16')
        
        # Process audio
        keyword_index = porcupine.process(audio_frame)
        
        if keyword_index >= 0:
            keyword_name = WAKE_WORDS[keyword_index]
            print(f"\n*** Detected: '{keyword_name}' ***")
            
            video_path = VIDEO_PATHS.get(keyword_index)
            if video_path and os.path.exists(video_path):
                play_response_video(video_path)
            else:
                print(f"Warning: Video not found: {video_path}")
    
    # Start audio stream
    try:
        print("✓ Starting audio stream")
        print(f"\nListening for: {', '.join([f\"'{word}'\" for word in WAKE_WORDS])}")
        print("Press Ctrl+C to stop\n")
        
        with sd.InputStream(
            samplerate=porcupine.sample_rate,
            blocksize=porcupine.frame_length,
            dtype='float32',
            channels=1,
            callback=audio_callback
        ):
            # Monitor loop
            while True:
                time.sleep(1)
                
                # Auto-restart if video crashes
                if current_video and current_video.poll() is not None:
                    print("Video stopped unexpectedly, restarting...")
                    play_listening_video()
                    
    except Exception as e:
        print(f"Error: {e}")
    finally:
        porcupine.delete()
        cleanup()

if __name__ == "__main__":
    # Check if running in test mode
    if len(sys.argv) > 1 and sys.argv[1] == '--fullscreen':
        WINDOW_MODE = False
    
    main()
```

### 1.3 Create test_hardware.py
```python
#!/usr/bin/env python3
"""Hardware test script for VoiceBox"""

import subprocess
import sounddevice as sd
import numpy as np
import time
import os
import sys

print("="*60)
print("VoiceBox Hardware Test")
print("="*60)

# Test 1: Check Python packages
print("\n1. Checking Python packages...")
packages = ['pvporcupine', 'sounddevice', 'python-dotenv', 'numpy']
for pkg in packages:
    try:
        __import__(pkg.replace('-', '_'))
        print(f"   ✓ {pkg}")
    except ImportError:
        print(f"   ✗ {pkg} - Run: pip3 install {pkg}")

# Test 2: Check video files
print("\n2. Checking video files...")
video_dir = "/home/pi/videobox/videos"
required_videos = ['listening.mp4', 'americano.mp4', 'bumblebee.mp4', 'grasshopper.mp4']

for video in required_videos:
    path = os.path.join(video_dir, video)
    if os.path.exists(path):
        size = os.path.getsize(path) / 1024 / 1024  # MB
        print(f"   ✓ {video} ({size:.1f} MB)")
    else:
        print(f"   ✗ {video} NOT FOUND")

# Test 3: Display test
print("\n3. Testing display...")
test_video = os.path.join(video_dir, 'listening.mp4')
if os.path.exists(test_video):
    print("   Playing listening video for 5 seconds...")
    proc = subprocess.Popen([
        'mpv', '--hwdec=mmal', '--really-quiet', 
        '--geometry=800x480', '--title=Display Test',
        test_video
    ])
    time.sleep(5)
    proc.terminate()
    proc.wait()
    print("   ✓ Display working")
else:
    print("   ✗ No video available for display test")

# Test 4: Audio test
print("\n4. Testing microphone...")
print("   Audio devices:")
devices = sd.query_devices()
input_devices = []
for i, device in enumerate(devices):
    if device['max_input_channels'] > 0:
        print(f"   [{i}] {device['name']} ({device['max_input_channels']} ch)")
        input_devices.append(i)

if input_devices:
    print("\n   Recording 3 seconds - SPEAK NOW!")
    duration = 3
    sample_rate = 16000
    recording = sd.rec(int(duration * sample_rate), 
                       samplerate=sample_rate, 
                       channels=1, 
                       dtype='float32')
    sd.wait()
    
    level = np.max(np.abs(recording))
    print(f"   Peak level: {level:.4f}")
    
    if level > 0.01:
        print("   ✓ Microphone working!")
    else:
        print("   ✗ No audio detected - check mic connection")
else:
    print("   ✗ No input devices found!")

# Test 5: Check built-in wake words
print("\n5. Checking built-in wake words...")
try:
    import pvporcupine
    wake_words = ['americano', 'bumblebee', 'grasshopper']
    print("   Available built-in keywords:")
    for word in pvporcupine.KEYWORDS:
        status = "✓" if word in wake_words else " "
        print(f"   {status} {word}")
except ImportError:
    print("   ✗ pvporcupine not available")

# Test 6: Environment check
print("\n6. Checking environment...")
if os.path.exists('/home/pi/videobox/.env'):
    from dotenv import load_dotenv
    load_dotenv('/home/pi/videobox/.env')
    if os.getenv('PICOVOICE_ACCESS_KEY'):
        print("   ✓ Picovoice access key found")
    else:
        print("   ✗ PICOVOICE_ACCESS_KEY not set in .env")
else:
    print("   ✗ .env file not found")

print("\n" + "="*60)
print("Test complete! Fix any ✗ items before running VoiceBox")
print("="*60)
```

### 1.4 Create setup_pi.sh
```bash
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
echo "2. Download wake word files from Picovoice Console"
echo "3. Add your video files to the videos/ directory"
echo "4. Run: ./venv/bin/python src/test_hardware.py"
echo "5. Run: ./venv/bin/python src/voicebox.py"
```

### 1.5 Create deploy.sh
```bash
#!/bin/bash
# Deploy script to sync with Pi

PI_HOST="pi@raspberrypi.local"
PI_DIR="/home/pi/videobox"

echo "Deploying to Raspberry Pi..."

# Sync files
rsync -av --exclude='venv/' --exclude='.git/' --exclude='*.pyc' \
    ./ ${PI_HOST}:${PI_DIR}/

# Run setup on Pi
ssh ${PI_HOST} "cd ${PI_DIR} && bash scripts/setup_pi.sh"

echo "Deployment complete!"
```

### 1.6 Create requirements.txt
```
pvporcupine==3.0.0
sounddevice==0.4.6
python-dotenv==1.0.0
numpy==1.24.3
```

### 1.7 Create .env.example
```
# Picovoice Access Key (get from https://console.picovoice.ai/)
PICOVOICE_ACCESS_KEY=your_access_key_here
```

### 1.8 Create .gitignore
```
# Python
__pycache__/
*.py[cod]
*$py.class
venv/
env/

# Environment
.env

# Wake word files (proprietary)
*.ppn

# Video files (large)
*.mp4
*.avi
*.mov

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

### 1.9 Create voicebox.desktop (for fullscreen autostart)
```ini
[Desktop Entry]
Type=Application
Name=VoiceBox
Comment=Voice-Activated Video Display
Exec=/home/pi/videobox/venv/bin/python /home/pi/videobox/src/voicebox.py --fullscreen
Terminal=false
Categories=AudioVideo;
StartupNotify=true
```

### 1.10 Create voicebox.service (alternative systemd approach)
```ini
[Unit]
Description=VoiceBox Voice-Activated Video Display
After=graphical.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/videobox
Environment="DISPLAY=:0"
Environment="XAUTHORITY=/home/pi/.Xauthority"
Environment="HOME=/home/pi"
Environment="PATH=/home/pi/videobox/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/pi/videobox/venv/bin/python /home/pi/videobox/src/voicebox.py --fullscreen
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical.target
```

## Phase 2: Claude Code Implementation Steps

### Step 1: Initialize Local Repository
```bash
# Create project directory
mkdir videobox
cd videobox

# Initialize git
git init

# Create directory structure
mkdir -p src config scripts videos wakewords

# Create all files as specified above
# (Create each file with content from Phase 1)

# Initial commit
git add .
git commit -m "Initial VoiceBox project structure"
```

### Step 2: Prepare Raspberry Pi
1. Flash Raspberry Pi OS 32-bit (with desktop) using Pi Imager
2. Enable SSH, set WiFi, hostname, and password
3. Boot Pi and ensure SSH access works

### Step 3: Deploy to Pi
```bash
# Make deploy script executable
chmod +x scripts/deploy.sh

# Deploy to Pi
./scripts/deploy.sh
```

### Step 4: Configure on Pi (via SSH)
```bash
ssh pi@raspberrypi.local

# Navigate to project
cd /home/pi/videobox

# Edit .env file
nano .env
# Add: PICOVOICE_ACCESS_KEY=your_actual_key_here

# No wake word files needed! Using built-in keywords:
# "americano", "bumblebee", "grasshopper"
# These are already included in the pvporcupine package
```

### Step 5: Add Video Files
```bash
# From local machine, copy video files:
scp videos/*.mp4 pi@raspberrypi.local:/home/pi/videobox/videos/

# Required videos:
# - listening.mp4: Continuous animation when waiting for commands
# - americano.mp4: Response to "americano" command
# - bumblebee.mp4: Response to "bumblebee" command  
# - grasshopper.mp4: Response to "grasshopper" command
```

### Step 6: Test in Window Mode
```bash
ssh -X pi@raspberrypi.local  # Enable X11 forwarding
cd /home/pi/videobox

# Run hardware test
./venv/bin/python src/test_hardware.py

# Run main program in window mode
./venv/bin/python src/voicebox.py
```

### Step 7: Test Fullscreen Mode
```bash
# Run in fullscreen mode
./venv/bin/python src/voicebox.py --fullscreen
```

### Step 8: Configure Autostart (After Testing)
```bash
# Option A: Desktop autostart (recommended for GUI)
mkdir -p /home/pi/.config/autostart
cp config/voicebox.desktop /home/pi/.config/autostart/

# Option B: Systemd service (alternative)
sudo cp config/voicebox.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable voicebox.service
sudo systemctl start voicebox.service

# Hide desktop elements for kiosk mode
# Edit /home/pi/.config/lxsession/LXDE-pi/autostart
nano /home/pi/.config/lxsession/LXDE-pi/autostart

# Add these lines to hide UI elements:
@xset s off
@xset -dpms
@xset s noblank
@unclutter -idle 0

# Disable screensaver
sudo apt install unclutter
```

### Step 9: Verify Full Setup
```bash
# Reboot and verify autostart
sudo reboot

# After reboot, should see:
# 1. Boot sequence
# 2. Brief desktop flash
# 3. VoiceBox fullscreen with listening animation
# 4. Voice commands working
```

## Testing Commands

### Manual Testing Steps
1. **Window Mode Test**: Say "americano" → americano.mp4 plays → returns to listening
2. **Fullscreen Test**: Same as above but fullscreen
3. **Multiple Commands**: Try all three commands ("americano", "bumblebee", "grasshopper") in sequence
4. **Audio Level**: Speak from different distances
5. **Recovery Test**: Kill process, verify auto-restart

### Debug Commands
```bash
# View logs (if using systemd)
sudo journalctl -u voicebox -f

# Check audio devices
arecord -l

# Test microphone
arecord -d 5 test.wav && aplay test.wav

# Monitor CPU/Memory
htop
```

## Video Specifications

### listening.mp4
- Duration: Any (will loop)
- Resolution: 800x480 or 720p
- Content: Animated microphone, pulsing wave, or listening indicator
- Audio: None (silent)

### Response Videos (americano.mp4, bumblebee.mp4, grasshopper.mp4)
- Duration: 2-10 seconds each
- Resolution: 800x480 or 720p
- Content: Your response content
- Audio: Optional

## Performance Targets
- Boot to operational: <20 seconds
- Keyword detection: <200ms response
- Video transition: <100ms (seamless)
- CPU usage: <20% when listening
- RAM usage: <100MB total

## Troubleshooting

### No Video Output
- Check HDMI connection
- Verify mpv installation: `mpv --version`
- Test video directly: `mpv --hwdec=mmal videos/listening.mp4`

### Microphone Not Working
- Check USB connection
- List devices: `arecord -l`
- Check permissions: `groups pi` (should include 'audio')

### Keywords Not Detected
- Verify .env has correct ACCESS_KEY
- No .ppn files needed - using built-in keywords
- Test audio levels with test_hardware.py
- Speak clearly, 1-2 feet from mic
- Use exact words: "americano", "bumblebee", "grasshopper"

### Video Transitions Not Smooth
- Ensure videos are same resolution
- Use hardware acceleration: `--hwdec=mmal`
- Consider reducing video resolution to 720p

## Final Notes

This implementation provides:
1. Initial window mode for testing
2. Fullscreen mode for production
3. Seamless video transitions
4. Automatic recovery from crashes
5. Easy deployment via Claude Code

The listening animation provides visual feedback that the system is ready, while instant video switching creates a responsive feel. The modular design allows easy addition of new commands or videos.