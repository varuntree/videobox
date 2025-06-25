#!/usr/bin/env python3
"""
VoiceBox - Voice-Activated Video Display (Vosk Version)
Continuously plays listening animation, responds to any spoken video filename
"""

import subprocess
import sys
import time
import signal
import os
import json
import socket
import threading
import sounddevice as sd
import vosk
import numpy as np
from dotenv import load_dotenv
from video_discovery import VideoDiscovery

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
VOSK_MODEL_PATH = os.getenv('VOSK_MODEL_PATH', '/home/varun/videobox/models/vosk-model-en-us-small')
MIN_CONFIDENCE = float(os.getenv('MIN_CONFIDENCE', '0.7'))

# Video paths
LISTENING_VIDEO = "/home/varun/videobox/videos/listening.mp4"
WELCOME_VIDEO = "/home/varun/videobox/videos/welcome.mp4"

# Global variables
mpv_process = None
mpv_controller = None
available_videos = {}
video_discovery = None
last_video_scan = 0
is_listening = True

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

def rescan_videos():
    """Rescan for available videos"""
    global available_videos, last_video_scan
    
    print("Rescanning for videos...")
    available_videos = video_discovery.get_all_videos()
    last_video_scan = time.time()
    
    print(f"Found {len(available_videos)} command videos:")
    for command, path in available_videos.items():
        print(f"  '{command}' -> {os.path.basename(path)}")
    
    return available_videos

def play_listening_video():
    """Start playing the listening animation in a loop"""
    global mpv_controller, is_listening
    print("Starting listening animation...")
    mpv_controller.load(LISTENING_VIDEO, loop=True)
    is_listening = True

def play_welcome_video():
    """Play welcome video once, then start listening"""
    global mpv_controller, is_listening
    if not os.path.exists(WELCOME_VIDEO):
        print("No welcome video found, starting listening directly...")
        return play_listening_video()
        
    print("Playing welcome video...")
    mpv_controller.load(WELCOME_VIDEO, loop=False)
    is_listening = False
    return True

def play_response_video(video_path):
    """Play a response video once, then return to listening"""
    global mpv_controller, is_listening
    print(f"Playing response video: {os.path.basename(video_path)}")
    mpv_controller.load(video_path, loop=False)
    is_listening = False

def process_speech_result(result_text):
    """Process recognized speech and find matching video"""
    global available_videos
    
    if not result_text or not result_text.strip():
        return
        
    # Convert to lowercase for matching
    spoken_text = result_text.lower().strip()
    print(f"Recognized: '{spoken_text}'")
    
    # Check for exact matches first
    if spoken_text in available_videos:
        video_path = available_videos[spoken_text]
        if os.path.exists(video_path):
            play_response_video(video_path)
            return True
    
    # Check for partial matches
    for command, video_path in available_videos.items():
        if command in spoken_text or spoken_text in command:
            print(f"Partial match: '{spoken_text}' -> '{command}'")
            if os.path.exists(video_path):
                play_response_video(video_path)
                return True
    
    print(f"No video found for: '{spoken_text}'")
    return False

def cleanup(signum=None, frame=None):
    """Clean shutdown handler"""
    global mpv_process
    print("\nShutting down VoiceBox...")
    
    if mpv_process and mpv_process.poll() is None:
        mpv_process.terminate()
        try:
            mpv_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            mpv_process.kill()
            mpv_process.wait()
    
    sys.exit(0)

def periodic_video_scan():
    """Periodically rescan for new videos (runs in background)"""
    global last_video_scan
    
    while True:
        try:
            time.sleep(30)  # Check every 30 seconds
            
            # Only rescan if it's been a while
            if time.time() - last_video_scan > 30:
                rescan_videos()
                
        except Exception as e:
            print(f"Error in periodic scan: {e}")
            time.sleep(60)

def main():
    global mpv_process, mpv_controller, video_discovery
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    print("="*50)
    print("VoiceBox Starting Up (Vosk Version)")
    print("="*50)
    
    # Initialize video discovery
    video_discovery = VideoDiscovery()
    
    # Start persistent mpv with IPC
    mpv_process, mpv_controller = start_mpv()
    time.sleep(1)
    
    # Initialize Vosk
    if not os.path.exists(VOSK_MODEL_PATH):
        print(f"ERROR: Vosk model not found at {VOSK_MODEL_PATH}")
        print("Run the model download step from the migration guide")
        sys.exit(1)
    
    try:
        print("Loading Vosk model...")
        vosk.SetLogLevel(-1)  # Reduce Vosk logging
        model = vosk.Model(VOSK_MODEL_PATH)
        rec = vosk.KaldiRecognizer(model, 16000)
        rec.SetMaxAlternatives(3)  # Get multiple possibilities
        print("✓ Vosk model loaded successfully")
    except Exception as e:
        print(f"✗ Failed to initialize Vosk: {e}")
        sys.exit(1)
    
    # Initial video scan
    rescan_videos()
    
    # Start background video scanning
    scan_thread = threading.Thread(target=periodic_video_scan, daemon=True)
    scan_thread.start()
    
    # Start with welcome video
    play_welcome_video()
    
    # Audio callback for Vosk processing
    def audio_callback(indata, frames, time_info, status):
        if status:
            print(f"Audio error: {status}")
        
        # Convert to int16 for Vosk
        audio_data = (indata[:, 0] * 32767).astype(np.int16).tobytes()
        
        # Process with Vosk
        if rec.AcceptWaveform(audio_data):
            # Final result
            result = json.loads(rec.Result())
            text = result.get('text', '')
            confidence = result.get('confidence', 0)
            
            if text and confidence >= MIN_CONFIDENCE:
                process_speech_result(text)
        else:
            # Partial result (optional - for debugging)
            partial = json.loads(rec.PartialResult())
            partial_text = partial.get('partial', '')
            if partial_text and len(partial_text) > 10:  # Only show longer partial results
                print(f"Listening: {partial_text}")
    
    # Start audio stream
    try:
        print("✓ Starting audio stream")
        print(f"Available commands: {list(available_videos.keys())}")
        print("Speak any video filename to play it!")
        print("Press Ctrl+C to stop\n")
        
        with sd.InputStream(
            samplerate=16000,
            blocksize=1600,  # 0.1 second blocks
            dtype='float32',
            channels=1,
            callback=audio_callback
        ):
            # Main monitoring loop
            while True:
                time.sleep(1)
                
                # Check if response video finished, return to listening
                if not is_listening:
                    eof = mpv_controller.get_property("eof-reached")
                    if eof:
                        play_listening_video()
                
                # Auto-restart mpv if it crashes
                if mpv_process and mpv_process.poll() is not None:
                    print("MPV stopped unexpectedly, restarting...")
                    mpv_process, mpv_controller = start_mpv()
                    time.sleep(1)
                    if is_listening:
                        play_listening_video()
                    
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cleanup()

if __name__ == "__main__":
    main()