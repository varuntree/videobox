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
import shutil
import re
from pathlib import Path
from typing import Dict, List, Set, Optional

class VideoScanner:
    """Scans directories for video files and converts filenames to voice commands."""
    
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.mpg', '.mpeg', '.m4v', 
                       '.MP4', '.AVI', '.MOV', '.MKV', '.WMV', '.MPG', '.MPEG', '.M4V'}
    
    @staticmethod
    def find_video_files(directory: str) -> List[str]:
        """Find all video files in a directory recursively."""
        if not os.path.exists(directory):
            return []
            
        video_files = []
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if Path(file).suffix in VideoScanner.VIDEO_EXTENSIONS:
                        full_path = os.path.join(root, file)
                        video_files.append(full_path)
        except (PermissionError, OSError) as e:
            print(f"Error scanning {directory}: {e}")
            
        return video_files
    
    @staticmethod
    def filename_to_command(filepath: str) -> str:
        """Convert a video filename to a voice command."""
        # Get filename without extension
        filename = Path(filepath).stem
        
        # Replace common separators with spaces
        command = re.sub(r'[_\-\.]+', ' ', filename)
        
        # Remove special characters and normalize
        command = re.sub(r'[^\w\s]', '', command)
        
        # Convert to lowercase and clean up spaces
        command = ' '.join(command.lower().split())
        
        return command


class VideoRegistry:
    """Manages the dynamic registry of available videos and their commands."""
    
    def __init__(self):
        self.videos: Dict[str, str] = {}  # command -> filepath
        self.system_videos: Dict[str, str] = {}  # protected system videos
        self.usb_videos: Dict[str, str] = {}  # videos from USB drives
        self.lock = threading.Lock()
        
    def add_system_videos(self, video_dir: str, system_video_names: Dict[str, str]):
        """Add protected system videos that cannot be overridden."""
        with self.lock:
            self.system_videos.clear()
            for command, filename in system_video_names.items():
                filepath = os.path.join(video_dir, filename)
                if os.path.exists(filepath):
                    self.system_videos[command] = filepath
                    self.videos[command] = filepath
                    
    def scan_directory(self, directory: str, namespace: str = "usb") -> int:
        """Scan a directory for videos and add them to registry."""
        video_files = VideoScanner.find_video_files(directory)
        added_count = 0
        
        with self.lock:
            # Clear previous videos from this namespace
            if namespace == "usb":
                # Remove old USB videos from main registry
                for cmd in list(self.usb_videos.keys()):
                    if cmd in self.videos and cmd not in self.system_videos:
                        del self.videos[cmd]
                self.usb_videos.clear()
            
            # Add new videos
            for video_file in video_files:
                command = VideoScanner.filename_to_command(video_file)
                if command and len(command.split()) <= 4:  # Reasonable command length
                    
                    # Don't override system videos
                    if command in self.system_videos:
                        print(f"Skipping USB video '{command}' - conflicts with system video")
                        continue
                        
                    if namespace == "usb":
                        self.usb_videos[command] = video_file
                    
                    self.videos[command] = video_file
                    added_count += 1
                    print(f"Added video command: '{command}' -> {os.path.basename(video_file)}")
                    
        return added_count
    
    def get_video_path(self, command: str) -> Optional[str]:
        """Get video path for a command."""
        with self.lock:
            return self.videos.get(command)
            
    def get_all_commands(self) -> List[str]:
        """Get list of all available commands."""
        with self.lock:
            return list(self.videos.keys())
            
    def remove_usb_videos(self):
        """Remove all USB videos from registry."""
        with self.lock:
            for cmd in list(self.usb_videos.keys()):
                if cmd in self.videos:
                    del self.videos[cmd]
            self.usb_videos.clear()
            print("Removed all USB videos from registry")


class USBMonitor:
    """Monitors USB drive insertion/removal and manages video discovery."""
    
    def __init__(self, video_registry: VideoRegistry):
        self.video_registry = video_registry
        self.monitoring = False
        self.monitor_thread = None
        self.usb_mount_points: Set[str] = set()
        
        # Common USB mount locations on Raspberry Pi
        self.mount_base_paths = [
            "/media/pi",     # Desktop environment
            "/media/usb",    # pi-usb-automount
            "/media/usb0",   # Common alternative
            "/media/usb1",   # Multiple USB drives
            "/mnt/usb"       # Manual mount
        ]
    
    def start_monitoring(self):
        """Start USB monitoring in a background thread."""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("USB monitoring started")
        
    def stop_monitoring(self):
        """Stop USB monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("USB monitoring stopped")
        
    def _monitor_loop(self):
        """Main monitoring loop - polls for mount point changes."""
        while self.monitoring:
            try:
                current_mounts = self._find_current_usb_mounts()
                
                # Check for new mounts
                new_mounts = current_mounts - self.usb_mount_points
                if new_mounts:
                    for mount_point in new_mounts:
                        self._handle_usb_inserted(mount_point)
                
                # Check for removed mounts  
                removed_mounts = self.usb_mount_points - current_mounts
                if removed_mounts:
                    for mount_point in removed_mounts:
                        self._handle_usb_removed(mount_point)
                
                self.usb_mount_points = current_mounts
                
            except Exception as e:
                print(f"USB monitoring error: {e}")
                
            time.sleep(2)  # Check every 2 seconds
    
    def _find_current_usb_mounts(self) -> Set[str]:
        """Find currently mounted USB drives."""
        mounts = set()
        
        # Check each potential mount base path
        for base_path in self.mount_base_paths:
            if os.path.exists(base_path):
                try:
                    # For base directories like /media/pi, scan subdirectories
                    if base_path in ["/media/pi", "/media/usb"]:
                        for item in os.listdir(base_path):
                            mount_point = os.path.join(base_path, item)
                            if os.path.ismount(mount_point) and os.path.isdir(mount_point):
                                mounts.add(mount_point)
                    else:
                        # For specific mount points, check if mounted
                        if os.path.ismount(base_path):
                            mounts.add(base_path)
                except (PermissionError, OSError):
                    continue
                    
        return mounts
    
    def _handle_usb_inserted(self, mount_point: str):
        """Handle USB drive insertion."""
        print(f"USB drive detected: {mount_point}")
        video_count = self.video_registry.scan_directory(mount_point, "usb")
        print(f"Found {video_count} videos on USB drive")
        
    def _handle_usb_removed(self, mount_point: str):
        """Handle USB drive removal."""
        print(f"USB drive removed: {mount_point}")
        self.video_registry.remove_usb_videos()
        
    def force_rescan(self):
        """Force a rescan of all USB drives."""
        self.video_registry.remove_usb_videos()
        current_mounts = self._find_current_usb_mounts()
        
        total_videos = 0
        for mount_point in current_mounts:
            video_count = self.video_registry.scan_directory(mount_point, "usb")
            total_videos += video_count
            
        self.usb_mount_points = current_mounts
        print(f"USB rescan complete: {total_videos} videos found across {len(current_mounts)} drives")


class VoiceVideoPlayer:
    def __init__(self):
        # Initialize VOSK model
        model_path = "/home/varun/vosk-model"
        if not os.path.exists(model_path):
            print(f"Please download vosk model to {model_path}")
            sys.exit(1)
            
        self.model = vosk.Model(model_path)
        self.rec = vosk.KaldiRecognizer(self.model, 16000)
        self.rec.SetWords(True)
        self.rec.SetPartialWords(False)
        
        # Audio queue
        self.q = queue.Queue()
        
        # Video player process
        self.video_process = None
        
        ## FIX: Add a lock for thread-safe access to the video process
        self.video_lock = threading.Lock()
        
        # State management
        self.current_state = "welcome"
        self.is_listening = False
        self.command_playing = False
        
        # Initialize dynamic video system
        self.video_dir = "/home/varun/videobox/videos_optimized"
        self.video_registry = VideoRegistry()
        self.usb_monitor = USBMonitor(self.video_registry)
        
        # Add system videos (protected)
        system_videos = {
            "welcome": "welcome.mp4",
            "listening": "listening.mp4", 
            "coffee": "coffee.mp4",
            "insect": "insect.mp4",
            "grasshopper": "grasshopper.mp4"
        }
        self.video_registry.add_system_videos(self.video_dir, system_videos)
        
        # Legacy compatibility - maintain old interface
        self.videos = self.video_registry.videos
        self.commands = ["coffee", "insect", "grasshopper"]  # Will be dynamic
        
        # NEW: make the desktop background solid black so any
        # accidental exposure is invisible to the user.
        if shutil.which("xsetroot"):                 # only if X11 is running
            try:
                subprocess.Popen(["xsetroot", "-solid", "black"],
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
            except Exception:
                pass
        
        # Start USB monitoring
        self.usb_monitor.start_monitoring()
        
        # Initial USB scan
        self.usb_monitor.force_rescan()
        
        print("Voice Video Player initialized with dynamic video discovery")

    def _maybe_fire_command(self, text):
        """Helper to check if text contains a command and fire it."""
        text = text.lower().strip()
        if not text or len(text.split()) > 4:  # Allow slightly longer USB video commands
            return False
            
        # Get current available commands dynamically
        available_commands = self.video_registry.get_all_commands()
        
        for command in available_commands:
            # Skip system videos that aren't commands
            if command in ["welcome", "listening"]:
                continue
                
            if self._command_matches(command, text):
                print(f"Command detected (partial/full): '{command}'")
                self.handle_command(command)
                return True
        return False
        
    def _command_matches(self, command: str, text: str) -> bool:
        """Check if spoken text matches a command with fuzzy matching."""
        # Direct match
        if command in text:
            return True
            
        # Split command into words for partial matching
        command_words = command.split()
        text_words = text.split()
        
        # Check if all command words are present in text
        if len(command_words) > 1:
            matches = sum(1 for word in command_words if any(word in text_word for text_word in text_words))
            if matches >= len(command_words) // 2:  # At least half the words match
                return True
        
        # Legacy fuzzy matching for system commands
        if command == "coffee" and ("cafe" in text or "caffeine" in text or "coff" in text):
            return True
        if command == "insect" and ("bug" in text or "beetle" in text or "insec" in text):
            return True  
        if command == "grasshopper" and ("grass" in text or "hopper" in text):
            return True
            
        return False

    def audio_callback(self, indata, frames, time, status):
        """Audio input callback"""
        if status:
            print(status, file=sys.stderr)

        # NEW: only enqueue audio when we are truly listening
        if self.is_listening and not self.command_playing:
            self.q.put(bytes(indata))

    def play_video(self, video_key, loop=False, with_audio=False, on_top=True):
        """Play video using VLC with double-buffered hand-off."""
        with self.video_lock:
            # Use dynamic video registry
            video_path = self.video_registry.get_video_path(video_key)
            if not video_path:
                print(f"Video command '{video_key}' not found in registry")
                return

            if not os.path.exists(video_path):
                print(f"Video file not found: {video_path}")
                return

            # Build VLC command
            cmd = ["cvlc", "--intf", "dummy",
                   "--no-video-title-show",
                   "--fullscreen", "--no-osd",
                   "--no-video-deco"]        # just in case
            if on_top:
                cmd.append("--video-on-top")   # only add when requested

            if not with_audio:
                cmd.append("--no-audio")
            cmd.append("--loop" if loop else "--play-and-exit")
            cmd.append(video_path)

            print(f"Playing: {video_key} (audio: {with_audio}, loop: {loop})")

            try:
                # NEW: start the *next* video first
                next_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                # Give VLC a moment (100–200 ms is usually enough) to create
                # its window before we kill the old one.
                time.sleep(0.15)

                # NOW stop the previous video, if any
                if self.video_process and self.video_process.poll() is None:
                    try:
                        self.video_process.terminate()
                        self.video_process.wait(timeout=0.5)
                    except subprocess.TimeoutExpired:
                        self.video_process.kill()
                # Swap references
                self.video_process = next_process

            except Exception as e:
                print(f"Error playing video: {e}")

    def _stop_video_internal(self):
        """Internal stop video function, to be called within a lock"""
        if self.video_process:
            try:
                # Use SIGTERM for a graceful shutdown, which is better for VLC
                self.video_process.terminate()
                self.video_process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                print("VLC did not terminate gracefully, killing.")
                self.video_process.kill()
            except Exception:
                pass
            self.video_process = None

    def stop_video(self):
        """Stop current video (public method with lock)"""
        with self.video_lock:
            self._stop_video_internal()
        
        # Backup: kill all VLC processes if something goes wrong
        try:
            subprocess.run(["pkill", "-f", "vlc"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def start_listening(self):
        """Start speech recognition. This runs in a separate thread."""
        print("Starting speech recognition thread...")
        
        try:
            with sd.RawInputStream(
                samplerate=16000, 
                blocksize=2000,   # 2000 samples @16 kHz = 125 ms
                dtype="int16",
                channels=1, 
                callback=self.audio_callback
            ):
                # The 'with' block keeps the audio stream open.
                # The loop below will run as long as the main app is running.
                while True:
                    try:
                        # Wait for audio data
                        data = self.q.get()
                        
                        ## FIX: Only process audio if we are in a listening state
                        if not self.is_listening or self.command_playing:
                            continue
                            
                        if self.rec.AcceptWaveform(data):
                            result = json.loads(self.rec.Result())
                            self._maybe_fire_command(result.get('text', ''))
                        else:
                            # NEW: act on partials immediately
                            partial = json.loads(self.rec.PartialResult())
                            self._maybe_fire_command(partial.get('partial', ''))
                                        
                    except queue.Empty:
                        continue
                    except Exception as e:
                        print(f"Recognition error: {e}")
                        
        except Exception as e:
            # This error is critical, likely a problem with the audio device.
            print(f"CRITICAL Audio Error: {e}. The listener thread is stopping.")
            self.is_listening = False

    def handle_command(self, command):
        """Handle recognized voice command. This is called from the listener thread."""
        print(f"HANDLING COMMAND: {command}")

        # Pause recognition
        self.is_listening = False
        self.command_playing = True

        # NEW: purge any audio already captured so it can't be processed later
        while not self.q.empty():
            try:
                self.q.get_nowait()
            except queue.Empty:
                break
        self.rec.Reset()       # NEW: drop partial state inside Vosk

        # --- launch the command clip ---
        video_path = self.video_registry.get_video_path(command)
        if not video_path:
            print(f"Command video '{command}' not found")
            self.command_playing = False
            self.is_listening = True
            return
            
        cmd = ["cvlc", "--intf", "dummy",
               "--no-video-title-show", "--fullscreen", "--no-osd",
               "--video-on-top", "--play-and-exit", video_path]
        command_proc = subprocess.Popen(cmd,
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL)
        command_proc.wait()

        print("Command finished, returning to listening mode.")

        # NEW: make sure any mic noise during the clip isn't queued
        while not self.q.empty():
            try:
                self.q.get_nowait()
            except queue.Empty:
                break
        self.rec.Reset()       # fresh start

        # Resume recognition
        self.command_playing = False
        self.is_listening = True

    def run(self):
        """Main application loop"""
        try:
            # ---------------------------------------------------------
            # 1️⃣  Start the silent listening loop FIRST (stays forever)
            # ---------------------------------------------------------
            self.play_video("listening", loop=True, with_audio=False, on_top=False)  # runs muted in the background
            self.is_listening = False          # do not recognise speech yet

            # ---------------------------------------------------------
            # 2️⃣  Overlay the one‑shot welcome clip ON TOP of it
            #     (so the screen is always covered)
            # ---------------------------------------------------------
            welcome_cmd = ["cvlc", "--intf", "dummy",
                           "--no-video-title-show", "--fullscreen", "--no-osd",
                           "--video-on-top",           # <- forces welcome to sit above the listening loop
                           "--no-audio",               # or True if your file has sound
                           "--play-and-exit",
                           self.video_registry.get_video_path("welcome")]

            welcome_proc = subprocess.Popen(welcome_cmd,
                                            stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL)

            # Wait until the welcome clip finishes naturally
            welcome_proc.wait()
            print("Welcome finished, entering listening mode.")

            # ---------------------------------------------------------
            # 3️⃣  Now begin speech recognition; the listening video is
            #     already on screen, so no desktop flash can occur.
            # ---------------------------------------------------------
            self.is_listening = True
            listener_thread = threading.Thread(target=self.start_listening,
                                               daemon=True)
            listener_thread.start()

            # Keep the main thread alive
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"Error in main loop: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        print("Cleaning up...")
        self.is_listening = False
        self.stop_video()
        
        # Stop USB monitoring
        if hasattr(self, 'usb_monitor'):
            self.usb_monitor.stop_monitoring()

    def signal_handler(self, signum, frame):
        """Handle system signals"""
        print(f"\nReceived signal {signum}, shutting down.")
        self.cleanup()
        sys.exit(0)

def main():
    player = VoiceVideoPlayer()
    signal.signal(signal.SIGINT, player.signal_handler)
    signal.signal(signal.SIGTERM, player.signal_handler)
    player.run()

if __name__ == "__main__":
    main()