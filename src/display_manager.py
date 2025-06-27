#!/usr/bin/env python3
"""
Display Manager for MPV Video Control
Handles seamless video playback with IPC
"""

import subprocess
import json
import socket
import time
import os
from pathlib import Path

class DisplayManager:
    def __init__(self):
        self.socket_path = "/tmp/mpvsocket"
        self.mpv_process = None
        self.current_video = None
        self.video_dir = "/home/varun/voicebox/videos"
        
        # System video paths
        self.listening_video = os.path.join(self.video_dir, "listening.mp4")
        self.welcome_video = os.path.join(self.video_dir, "welcome.mp4")
    
    def initialize(self):
        """Initialize MPV with IPC control"""
        print("Initializing display manager...")
        
        # Clean up any existing socket
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
        
        # MPV command with optimal settings for Pi
        mpv_cmd = [
            "mpv",
            "--force-window=yes",
            "--idle=yes",
            "--ontop",
            "--no-border",
            "--geometry=800x480+0+0",
            "--no-osc",
            "--no-input-default-bindings",
            f"--input-ipc-server={self.socket_path}",
            "--vo=gpu",
            "--hwdec=no",  # Software decoding for stability
            "--no-keepaspect-window",
            "--no-keepaspect",
            "--fullscreen",
            "--really-quiet",
            "--vf=scale=800:480",  # Scale to Pi display
            "--no-correct-pts"     # Faster playback
        ]
        
        try:
            self.mpv_process = subprocess.Popen(mpv_cmd)
            time.sleep(2)  # Give MPV time to start and create socket
            
            # Test IPC connection
            if self.test_ipc():
                print("✓ Display manager initialized")
                return True
            else:
                print("✗ MPV IPC connection failed")
                return False
                
        except Exception as e:
            print(f"✗ Failed to start MPV: {e}")
            return False
    
    def test_ipc(self):
        """Test MPV IPC connection"""
        try:
            self.send_command("get_property", "idle-active")
            return True
        except:
            return False
    
    def send_command(self, *args):
        """Send command to MPV via IPC"""
        if not args:
            return None
        
        message = json.dumps({"command": list(args)}).encode("utf-8") + b"\n"
        
        try:
            with socket.socket(socket.AF_UNIX) as sock:
                sock.connect(self.socket_path)
                sock.sendall(message)
                
                # Get response for property queries
                if args[0] == "get_property":
                    response = sock.recv(1024).decode("utf-8")
                    data = json.loads(response)
                    return data.get("data")
                    
        except Exception as e:
            print(f"MPV command failed: {e}")
            return None
    
    def load_video(self, video_path, loop=False):
        """Load and play video"""
        if not os.path.exists(video_path):
            print(f"Video not found: {video_path}")
            return False
        
        self.current_video = video_path
        
        # Load video
        self.send_command("loadfile", video_path, "replace")
        
        # Set loop mode
        loop_mode = "inf" if loop else "no"
        self.send_command("set", "loop-file", loop_mode)
        
        print(f"Loading video: {Path(video_path).name}")
        return True
    
    def play_listening_animation(self):
        """Play continuous listening animation"""
        if os.path.exists(self.listening_video):
            self.load_video(self.listening_video, loop=True)
            return True
        else:
            print("Warning: Listening animation not found")
            return False
    
    def play_welcome(self):
        """Play welcome video once"""
        if os.path.exists(self.welcome_video):
            self.load_video(self.welcome_video, loop=False)
            return True
        else:
            print("Welcome video not found")
            return False
    
    def play_video(self, video_path):
        """Play any video once"""
        return self.load_video(video_path, loop=False)
    
    def has_welcome_video(self):
        """Check if welcome video exists"""
        return os.path.exists(self.welcome_video)
    
    def is_video_finished(self):
        """Check if current video has finished playing"""
        try:
            eof = self.send_command("get_property", "eof-reached")
            return eof is True
        except:
            return False
    
    def is_healthy(self):
        """Check if MPV process is running and responsive"""
        if not self.mpv_process or self.mpv_process.poll() is not None:
            return False
        
        # Test IPC responsiveness
        return self.test_ipc()
    
    def restart(self):
        """Restart MPV process"""
        print("Restarting display manager...")
        self.stop()
        time.sleep(1)
        return self.initialize()
    
    def stop(self):
        """Stop MPV and clean up"""
        print("Stopping display manager...")
        
        if self.mpv_process:
            self.mpv_process.terminate()
            try:
                self.mpv_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.mpv_process.kill()
                self.mpv_process.wait()
            
            self.mpv_process = None
        
        # Clean up socket
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
        
        print("✓ Display manager stopped")