# VoiceBox - Voice-Activated Video Display

Speak any video filename to play it instantly!

## Quick Start

1. **Add Your Videos**
   - Copy video files to USB drive
   - Plug USB drive into VoiceBox
   - System automatically detects your videos

2. **Voice Commands**
   - Speak the filename (without extension)
   - Example: For "my-demo.mp4" say "my demo" or "demo"
   - System responds within 1 second

3. **Supported Formats**
   - MP4, AVI, MKV, MOV, WMV
   - Best performance: MP4 files under 10MB
   - Recommended resolution: 800x480

## Example Usage

```
USB Drive Contents:          Voice Commands:
- product-demo.mp4          → Say "product demo"
- tutorial.mp4              → Say "tutorial" 
- introduction.mp4          → Say "introduction"
- customer-testimonial.mp4  → Say "customer"
```

## Tips for Best Results

- **Speak clearly** into the microphone
- **Use simple names** for video files
- **Avoid special characters** in filenames
- **Keep videos under 10MB** for best performance
- **Wait for current video to finish** before next command

## Installation

1. **Deploy to Raspberry Pi:**
   ```bash
   ./scripts/deploy.sh
   ```

2. **Or install manually on Pi:**
   ```bash
   scp -r . varun@192.168.50.45:/home/varun/voicebox/
   ssh varun@192.168.50.45
   cd /home/varun/voicebox
   ./scripts/install.sh
   ```

3. **Test the system:**
   ```bash
   ./venv/bin/python src/test_system.py
   ```

4. **Start the service:**
   ```bash
   sudo systemctl enable voicebox
   sudo systemctl start voicebox
   ```

## Troubleshooting

- **No response**: Check microphone connection
- **Video not found**: Ensure USB drive is properly connected
- **Poor quality**: Use MP4 format with 800x480 resolution
- **System restart**: Unplug power for 10 seconds, reconnect

## Development

- **Source code**: `src/` directory
- **Configuration**: `.env` file
- **Logs**: `journalctl -u voicebox -f`
- **Manual testing**: `./venv/bin/python src/voicebox.py`

## System Status

- Green light: Ready for voice commands
- Blue light: Processing voice
- Red light: Playing video
- No light: System error (restart needed)