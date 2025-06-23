# VoiceBox - Voice-Activated Video Display

A voice-activated video display system for Raspberry Pi that continuously plays a listening animation and responds to voice commands by playing corresponding videos.

## Features

- Continuous listening animation when idle
- Responds to built-in wake words: "americano", "bumblebee", "grasshopper"
- Seamless video transitions
- Auto-recovery from crashes
- Window and fullscreen modes
- No custom wake word files needed!

## Hardware Requirements

- Raspberry Pi 3B (or newer)
- Raspberry Pi OS 32-bit (with desktop)
- USB microphone
- HDMI display
- SD card (8GB minimum)

## Quick Start

### 1. Prepare Your Raspberry Pi

Flash Raspberry Pi OS (32-bit with desktop) using Raspberry Pi Imager with:
- SSH enabled
- WiFi configured
- Hostname: `raspberrypi`
- Username: `pi`

### 2. Get Picovoice Access Key

1. Go to [Picovoice Console](https://console.picovoice.ai/)
2. Create a free account
3. Copy your access key

### 3. Deploy to Pi

From your local machine:

```bash
# Clone this repository
git clone [your-repo-url] videobox
cd videobox

# Make scripts executable
chmod +x scripts/deploy.sh

# Deploy to Pi
./scripts/deploy.sh
```

### 4. Configure on Pi

SSH into your Pi:
```bash
ssh pi@raspberrypi.local
cd /home/pi/videobox

# Add your Picovoice access key
nano .env
# Add: PICOVOICE_ACCESS_KEY=your_actual_key_here
```

### 5. Add Video Files

Create these video files and copy them to the Pi:
- `listening.mp4` - Looping animation while waiting for commands
- `americano.mp4` - Plays when "americano" is detected
- `bumblebee.mp4` - Plays when "bumblebee" is detected
- `grasshopper.mp4` - Plays when "grasshopper" is detected

Copy videos from your local machine:
```bash
scp videos/*.mp4 pi@raspberrypi.local:/home/pi/videobox/videos/
```

### 6. Test the System

```bash
# Run hardware test
./venv/bin/python src/test_hardware.py

# Run in window mode
./venv/bin/python src/voicebox.py

# Run in fullscreen mode
./venv/bin/python src/voicebox.py --fullscreen
```

## Auto-Start Configuration

### Option A: Desktop Autostart (Recommended)
```bash
mkdir -p /home/pi/.config/autostart
cp config/voicebox.desktop /home/pi/.config/autostart/
```

### Option B: Systemd Service
```bash
sudo cp config/voicebox.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable voicebox.service
sudo systemctl start voicebox.service
```

## Project Structure

```
videobox/
├── src/
│   ├── voicebox.py          # Main control script
│   └── test_hardware.py     # Hardware test script
├── config/
│   ├── voicebox.service     # Systemd service file
│   └── voicebox.desktop     # Desktop autostart file
├── scripts/
│   ├── setup_pi.sh          # Pi setup script
│   └── deploy.sh            # Deployment script
├── videos/                  # Video files (user-provided)
├── .env                     # Environment variables (create from .env.example)
├── .env.example             # Example environment file
├── .gitignore
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Wake Words

The system uses Picovoice's built-in wake words:
- **"americano"** → plays `americano.mp4`
- **"bumblebee"** → plays `bumblebee.mp4`
- **"grasshopper"** → plays `grasshopper.mp4`

No custom .ppn files needed!

## Video Specifications

- **Format**: MP4 recommended
- **Resolution**: 800x480 or 720p
- **listening.mp4**: Should loop seamlessly
- **Response videos**: 2-10 seconds each

## Troubleshooting

### No Video Output
- Check HDMI connection
- Test video directly: `mpv --hwdec=mmal videos/listening.mp4`

### Keywords Not Detected
- Verify .env has correct ACCESS_KEY
- Speak clearly, 1-2 feet from mic
- Use exact words: "americano", "bumblebee", "grasshopper"

### View Logs (if using systemd)
```bash
sudo journalctl -u voicebox -f
```

## Performance

- Boot to operational: <20 seconds
- Keyword detection: <200ms response
- CPU usage: <20% when listening
- RAM usage: <100MB total

## License

This project is provided as-is for educational and personal use.