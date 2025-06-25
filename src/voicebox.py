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
import json
import socket
import sounddevice as sd
import pvporcupine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MPVController:
    def __init__(self, socket_path="/tmp/mpvsocket"):
        self.socket_path = socket_path

    def _cmd(self, *args):
        if not args:
            return
        msg = json.dumps({"command": list(args)}).encode("utf-8") + b"\n"
        try:
            with socket.socket(socket.AF_UNIX) as s:
                s.connect(self.socket_path)
                s.sendall(msg)
        except Exception as e:
            print(f"MPV command failed: {e}")

    def load(self, path, loop=False):
        self._cmd("loadfile", path, "replace")
        self._cmd("set", "loop-file", "inf" if loop else "no")
    
    def get_property(self, prop):
        try:
            msg = json.dumps({"command": ["get_property", prop]}).encode("utf-8") + b"\n"
            with socket.socket(socket.AF_UNIX) as s:
                s.connect(self.socket_path)
                s.sendall(msg)
                response = s.recv(1024).decode("utf-8")
                data = json.loads(response)
                return data.get("data")
        except Exception:
            return None

# Configuration
ACCESS_KEY = os.getenv('PICOVOICE_ACCESS_KEY', '')
# Using built-in wake words - no .ppn files needed!
WAKE_WORDS = ['americano', 'bumblebee', 'grasshopper']
VIDEO_PATHS = {
    0: "/home/varun/videobox/videos/americano.mp4",    # americano keyword
    1: "/home/varun/videobox/videos/bumblebee.mp4",    # bumblebee keyword
    2: "/home/varun/videobox/videos/grasshopper.mp4"   # grasshopper keyword
}
LISTENING_VIDEO = "/home/varun/videobox/videos/listening.mp4"
WELCOME_VIDEO = "/home/varun/videobox/videos/welcome.mp4"

# Global process references
mpv_process = None
mpv_controller = None

def start_mpv():
    """Start a single persistent mpv window with IPC."""
    socket_path = "/tmp/mpvsocket"
    if os.path.exists(socket_path):
        os.remove(socket_path)

    cmd = [
        "mpv",
        "--force-window=yes",
        "--idle=yes",
        "--ontop",
        "--no-border",
        "--geometry=800x480+0+0",
        "--no-osc",
        "--no-input-default-bindings",
        "--input-ipc-server=" + socket_path,
        "--vo=gpu",
        "--no-keepaspect-window",
        "--no-keepaspect",
        "--fullscreen",
        "--really-quiet"
    ]
    return subprocess.Popen(cmd), MPVController(socket_path)

def play_listening_video():
    """Start playing the listening animation in a loop"""
    global mpv_controller
    print("Starting listening animation...")
    mpv_controller.load(LISTENING_VIDEO, loop=True)

def play_welcome_video():
    """Play welcome video once, then start listening"""
    global mpv_controller
    if not os.path.exists(WELCOME_VIDEO):
        print("No welcome video found, starting listening directly...")
        return play_listening_video()
        
    print("Playing welcome video...")
    mpv_controller.load(WELCOME_VIDEO, loop=False)
    
    # Will transition to listening in main loop when video ends
    return True

def play_response_video(video_path):
    """Play a response video once, then return to listening"""
    global mpv_controller
    print(f"Playing response video: {os.path.basename(video_path)}")
    mpv_controller.load(video_path, loop=False)
    # Will transition back to listening in main loop when video ends

def cleanup(signum=None, frame=None):
    """Clean shutdown handler"""
    global mpv_process
    print("\nShutting down VoiceBox...")
    
    # Stop mpv process
    if mpv_process and mpv_process.poll() is None:
        mpv_process.terminate()
        try:
            mpv_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            mpv_process.kill()
            mpv_process.wait()
    
    sys.exit(0)

def main():
    global mpv_process, mpv_controller
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    print("="*50)
    print("VoiceBox Starting Up (Kiosk Mode)")
    print("="*50)
    
    # Start persistent mpv with IPC
    mpv_process, mpv_controller = start_mpv()
    time.sleep(1)  # Give mpv time to initialize
    
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
    
    # Start with welcome video, then listening animation
    play_welcome_video()
    
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
        wake_words_list = ', '.join([f"'{word}'" for word in WAKE_WORDS])
        print(f"\nListening for: {wake_words_list}")
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
                
                # Check if response video finished, return to listening
                eof = mpv_controller.get_property("eof-reached")
                if eof:
                    play_listening_video()
                
                # Auto-restart mpv if it crashes
                if mpv_process and mpv_process.poll() is not None:
                    print("MPV stopped unexpectedly, restarting...")
                    mpv_process, mpv_controller = start_mpv()
                    time.sleep(1)
                    play_listening_video()
                    
    except Exception as e:
        print(f"Error: {e}")
    finally:
        porcupine.delete()
        cleanup()

if __name__ == "__main__":
    main()