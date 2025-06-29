# USB Video Discovery Setup Guide

## Overview
The voice video player now supports automatic discovery of videos from USB drives. Simply plug in a USB drive with video files and speak the filename to play them.

## USB Drive Preparation

### 1. Format USB Drive
- **Recommended**: FAT32 or exFAT format
- **Compatible**: NTFS (with ntfs-3g installed)

### 2. Video File Naming
Videos are converted to voice commands based on filename:

| Filename | Voice Command |
|----------|---------------|
| `movie_trailer.mp4` | "movie trailer" |
| `funny-cat-video.mp4` | "funny cat video" |
| `My-Home-Movie.avi` | "my home movie" |
| `vacation2024.mov` | "vacation2024" |

### 3. Supported Video Formats
- MP4 (recommended)
- AVI, MOV, MKV, WMV
- MPG, MPEG, M4V
- Case insensitive extensions

## Auto-Mount Setup on Pi

### Option 1: Desktop Environment (Automatic)
If using Raspberry Pi OS Desktop, USB drives auto-mount to `/media/pi/[DRIVE_NAME]`

### Option 2: Headless Setup (Manual)
For Raspberry Pi OS Lite, install pi-usb-automount:

```bash
# Install auto-mount tool
sudo apt update
sudo apt install udisks2

# Or install pi-usb-automount for consistent /media/usb0 mounting
git clone https://github.com/fasteddy516/pi-usb-automount
cd pi-usb-automount
sudo ./install.sh
```

## Usage Instructions

### 1. Insert USB Drive
- Plug USB drive into Pi
- Wait 2-3 seconds for detection
- Check console output: "USB drive detected: /media/pi/USB_DRIVE"
- Videos automatically discovered: "Found 5 videos on USB drive"

### 2. Voice Commands
- Say any filename (without extension)
- Examples:
  - "movie trailer" → plays movie_trailer.mp4
  - "funny cat" → plays funny_cat_video.mp4
  - "vacation" → plays vacation2024.mov

### 3. Remove USB Drive
- Safely eject USB drive
- USB videos automatically removed from system
- System videos (coffee, insect, grasshopper) continue working

## Multiple USB Drives
- System supports multiple USB drives simultaneously
- All videos from all drives are available
- Commands work regardless of which drive contains the video

## Troubleshooting

### USB Drive Not Detected
```bash
# Check if drive is mounted
lsblk
findmnt

# Check USB monitoring logs
grep "USB" /var/log/syslog

# Force rescan (if needed)
# System automatically rescans every 2 seconds
```

### Video Not Playing
- Check filename contains only letters, numbers, spaces, hyphens, underscores
- Avoid special characters: `@#$%^&*()`
- Keep filenames under 50 characters
- Ensure video format is supported

### Mount Permission Issues
```bash
# Add user to disk group
sudo usermod -a -G disk varun

# Or create fstab entry for manual mounting
echo 'LABEL=USB /media/usb auto defaults,user,nofail 0 0' | sudo tee -a /etc/fstab
```

## System Video Protection
These videos are protected and cannot be overridden by USB videos:
- `welcome.mp4` - Startup video
- `listening.mp4` - Loop video  
- `coffee.mp4` - System command
- `insect.mp4` - System command
- `grasshopper.mp4` - System command

## Performance Notes
- Video discovery happens in background (non-blocking)
- Up to 100+ videos supported per USB drive
- 2-second polling interval for USB changes
- Thread-safe operations during video playback

## Example USB Structure
```
USB Drive (FAT32)
├── movies/
│   ├── action_movie.mp4
│   └── comedy_special.avi
├── family/
│   ├── birthday_party.mov
│   └── vacation_2024.mp4
└── funny_cat_compilation.mp4

Voice Commands Available:
- "action movie"
- "comedy special" 
- "birthday party"
- "vacation 2024"
- "funny cat compilation"
```

All videos are discovered recursively in subdirectories.