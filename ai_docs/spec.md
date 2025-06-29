# Voice-Controlled Video Player - Complete Implementation

## Project Overview
Simple voice-controlled video player for Raspberry Pi 3B (1GB) that plays videos based on voice commands.

**Video Files:**
- `welcome.mp4` - Plays once on startup
- `listening.mp4` - Loops when waiting for commands
- `americano.mp4` - Plays when "americano" is spoken
- `bumblebee.mp4` - Plays when "bumblebee" is spoken  
- `grasshopper.mp4` - Plays when "grasshopper" is spoken

---

## Phase 1: Install Dependencies

SSH into your Raspberry Pi and run these commands:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python dependencies
sudo apt install -y python3-pip python3-pyaudio portaudio19-dev

# Install VLC for video playback
sudo apt install -y vlc

# Install VOSK for speech recognition
pip3 install vosk sounddevice

# Download small English model (50MB)
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 vosk-model
rm vosk-model-small-en-us-0.15.zip
```

---

## Phase 2: Create Main Application

Create the main Python script:

```bash
cd ~/videobox
nano voice_video_player.py
```

Copy this code:

```python
#!/usr/bin/env python3
import json
import queue
import sounddevice as sd
import vosk
import subprocess
import threading
import time
import os
import signal
import sys

class VoiceVideoPlayer:
    def __init__(self):
        # Initialize VOSK model
        model_path = "/home/pi/vosk-model"
        if not os.path.exists(model_path):
            print(f"Please download vosk model to {model_path}")
            sys.exit(1)
            
        self.model = vosk.Model(model_path)
        self.rec = vosk.KaldiRecognizer(self.model, 16000)
        
        # Audio queue
        self.q = queue.Queue()
        
        # Video player process
        self.video_process = None
        
        # State management
        self.current_state = "welcome"
        self.is_listening = False
        
        # Video paths (using optimized folder)
        self.video_dir = "/home/pi/videobox/videos_optimized"
        self.videos = {
            "welcome": f"{self.video_dir}/welcome.mp4",
            "listening": f"{self.video_dir}/listening.mp4",
            "americano": f"{self.video_dir}/americano.mp4",
            "bumblebee": f"{self.video_dir}/bumblebee.mp4",
            "grasshopper": f"{self.video_dir}/grasshopper.mp4"
        }
        
        # Command keywords
        self.commands = ["americano", "bumblebee", "grasshopper"]
        
        print("Voice Video Player initialized")

    def audio_callback(self, indata, frames, time, status):
        """Audio input callback"""
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def play_video(self, video_key, loop=False):
        """Play video using VLC"""
        if video_key not in self.videos:
            print(f"Video {video_key} not found")
            return
            
        # Stop current video
        self.stop_video()
        
        video_path = self.videos[video_key]
        if not os.path.exists(video_path):
            print(f"Video file not found: {video_path}")
            return
            
        # VLC command for fullscreen playback
        cmd = [
            "cvlc", 
            "--intf", "dummy",
            "--no-video-title-show",
            "--fullscreen",
            "--no-osd",
            video_path
        ]
        
        # Add loop option if needed
        if loop:
            cmd.insert(-1, "--loop")
            
        print(f"Playing: {video_key}")
        
        try:
            self.video_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print(f"Error playing video: {e}")

    def stop_video(self):
        """Stop current video"""
        if self.video_process:
            try:
                self.video_process.terminate()
                self.video_process.wait(timeout=2)
            except:
                try:
                    self.video_process.kill()
                except:
                    pass
            self.video_process = None
            
        # Backup: kill all VLC processes
        try:
            subprocess.run(["pkill", "-f", "vlc"], check=False)
        except:
            pass

    def wait_for_video_end(self, video_key):
        """Wait for video to finish playing"""
        if self.video_process and video_key != "listening":
            try:
                self.video_process.wait()
            except:
                pass

    def start_listening(self):
        """Start speech recognition"""
        print("Starting speech recognition...")
        self.is_listening = True
        
        try:
            with sd.RawInputStream(
                samplerate=16000, 
                blocksize=8000, 
                dtype="int16",
                channels=1, 
                callback=self.audio_callback
            ):
                while self.is_listening:
                    try:
                        data = self.q.get(timeout=1)
                        if self.rec.AcceptWaveform(data):
                            result = json.loads(self.rec.Result())
                            text = result.get('text', '').lower().strip()
                            
                            if text:
                                print(f"Recognized: '{text}'")
                                
                                # Check for commands
                                for command in self.commands:
                                    if command in text:
                                        print(f"Command detected: {command}")
                                        self.handle_command(command)
                                        return
                                        
                    except queue.Empty:
                        continue
                    except Exception as e:
                        print(f"Recognition error: {e}")
                        
        except Exception as e:
            print(f"Audio error: {e}")
            time.sleep(2)  # Wait before retrying

    def handle_command(self, command):
        """Handle recognized voice command"""
        self.is_listening = False
        self.current_state = command
        
        # Play command video
        self.play_video(command)
        
        # Wait for video to finish
        self.wait_for_video_end(command)
        
        # Return to listening state
        self.return_to_listening()

    def return_to_listening(self):
        """Return to listening state"""
        print("Returning to listening state")
        self.current_state = "listening"
        self.play_video("listening", loop=True)
        time.sleep(1)  # Give video time to start
        self.start_listening()

    def run(self):
        """Main application loop"""
        try:
            # Play welcome video once
            print("Playing welcome video...")
            self.play_video("welcome")
            self.wait_for_video_end("welcome")
            
            # Enter main listening loop
            self.return_to_listening()
            
        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        print("Cleaning up...")
        self.is_listening = False
        self.stop_video()

    def signal_handler(self, signum, frame):
        """Handle system signals"""
        print(f"\nReceived signal {signum}")
        self.cleanup()
        sys.exit(0)

def main():
    # Set up signal handlers
    player = VoiceVideoPlayer()
    signal.signal(signal.SIGINT, player.signal_handler)
    signal.signal(signal.SIGTERM, player.signal_handler)
    
    # Run the application
    player.run()

if __name__ == "__main__":
    main()
```

Make it executable:
```bash
chmod +x voice_video_player.py
```

---

## Phase 3: Test Video Playback

Test each video individually:

```bash
# Test welcome video
cvlc --intf dummy --fullscreen ~/videobox/videos_optimized/welcome.mp4

# Test listening video (press Ctrl+C to stop)
cvlc --intf dummy --fullscreen --loop ~/videobox/videos_optimized/listening.mp4

# Test command videos
cvlc --intf dummy --fullscreen ~/videobox/videos_optimized/americano.mp4
cvlc --intf dummy --fullscreen ~/videobox/videos_optimized/bumblebee.mp4
cvlc --intf dummy --fullscreen ~/videobox/videos_optimized/grasshopper.mp4
```

**Expected Results:**
- Videos play fullscreen
- No desktop/taskbar visible
- Good quality playback

---

## Phase 4: Test Speech Recognition

Test VOSK speech recognition:

```bash
# Test microphone and speech recognition
python3 -c "
import sounddevice as sd
import vosk
import json
import queue
import sys

# Check if microphone works
print('Testing microphone...')
try:
    devices = sd.query_devices()
    print('Available audio devices:')
    for i, device in enumerate(devices):
        print(f'{i}: {device[\"name\"]}')
    
    # Test recording
    print('Recording for 3 seconds... Say something!')
    recording = sd.rec(int(3 * 16000), samplerate=16000, channels=1, dtype='int16')
    sd.wait()
    print('Recording complete!')
    
    # Test VOSK
    print('Testing VOSK...')
    model = vosk.Model('/home/pi/vosk-model')
    rec = vosk.KaldiRecognizer(model, 16000)
    
    # Process the recording
    if rec.AcceptWaveform(recording.tobytes()):
        result = json.loads(rec.Result())
        print(f'Recognized: {result.get(\"text\", \"nothing\")}')
    else:
        print('No speech detected')
        
except Exception as e:
    print(f'Error: {e}')
"
```

---

## Phase 5: Test Complete Application

Run the main application:

```bash
cd ~/videobox
python3 voice_video_player.py
```

**Expected Behavior:**
1. Welcome video plays once
2. Listening video starts looping
3. Say "americano", "bumblebee", or "grasshopper"
4. Corresponding video plays
5. Returns to listening video
6. Press Ctrl+C to quit

**Troubleshooting:**
- If audio doesn't work: Check microphone connection
- If VOSK fails: Verify model download
- If videos don't play: Check file paths and VLC installation

---

## Phase 6: Auto-Start Setup (Final Phase)

Only do this after everything works perfectly in Phase 5!

### Option A: Simple Auto-Start (Recommended)

Edit the autostart file:
```bash
sudo mkdir -p /etc/xdg/autostart
sudo nano /etc/xdg/autostart/voice-video-player.desktop
```

Add this content:
```ini
[Desktop Entry]
Type=Application
Name=Voice Video Player
Exec=/usr/bin/python3 /home/pi/videobox/voice_video_player.py
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
```

### Option B: Boot Service (Alternative)

Create a systemd service:
```bash
sudo nano /etc/systemd/system/voice-video-player.service
```

Add this content:
```ini
[Unit]
Description=Voice Video Player
After=sound.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/videobox
ExecStart=/usr/bin/python3 /home/pi/videobox/voice_video_player.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable the service:
```bash
sudo systemctl enable voice-video-player.service
sudo systemctl start voice-video-player.service
```

### Configure Auto-Login (Optional)

Enable auto-login for immediate start:
```bash
sudo raspi-config
```
- Choose "System Options" → "Boot / Auto Login" → "Desktop Autologin"

---

## File Structure

Your final structure should look like:
```
/home/pi/videobox/
├── voice_video_player.py          # Main application
├── videos_optimized/
│   ├── welcome.mp4
│   ├── listening.mp4
│   ├── americano.mp4
│   ├── bumblebee.mp4
│   └── grasshopper.mp4
└── /home/pi/vosk-model/           # VOSK speech model
```

---

## Usage

**Normal Operation:**
1. Power on Raspberry Pi
2. Application starts automatically
3. Welcome video plays
4. Device enters listening mode
5. Say commands to trigger videos
6. Device returns to listening mode

**To Stop:**
- SSH in and run: `sudo pkill -f voice_video_player.py`
- Or disable auto-start: `sudo systemctl disable voice-video-player.service`

**Commands:**
- "americano" → plays americano.mp4
- "bumblebee" → plays bumblebee.mp4  
- "grasshopper" → plays grasshopper.mp4

---

## Technical Notes

- **Memory Usage:** ~300MB (VOSK model + VLC)
- **CPU Usage:** ~25% during speech recognition
- **Audio:** 16kHz mono input required
- **Video:** Any format VLC supports (MP4 recommended)
- **Boot Time:** ~30 seconds to full operation

**Optimization Tips:**
- Use smaller video files if possible
- Ensure videos are optimized for Pi hardware
- Keep VOSK model in fast storage
- Monitor system temperature under load