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
        
        # Video paths (using optimized folder)
        self.video_dir = "/home/varun/videobox/videos_optimized"
        self.videos = {
            "welcome": f"{self.video_dir}/welcome.mp4",
            "listening": f"{self.video_dir}/listening.mp4",
            "coffee": f"{self.video_dir}/coffee.mp4",
            "insect": f"{self.video_dir}/insect.mp4",
            "grasshopper": f"{self.video_dir}/grasshopper.mp4"
        }
        
        # Command keywords
        self.commands = ["coffee", "insect", "grasshopper"]
        
        # NEW: make the desktop background solid black so any
        # accidental exposure is invisible to the user.
        if shutil.which("xsetroot"):                 # only if X11 is running
            try:
                subprocess.Popen(["xsetroot", "-solid", "black"],
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
            except Exception:
                pass
        
        print("Voice Video Player initialized")

    def audio_callback(self, indata, frames, time, status):
        """Audio input callback"""
        if status:
            print(status, file=sys.stderr)

        # NEW: only enqueue audio when we are truly listening
        if self.is_listening and not self.command_playing:
            self.q.put(bytes(indata))

    def play_video(self, video_key, loop=False, with_audio=False):
        """Play video using VLC with double-buffered hand-off."""
        with self.video_lock:
            if video_key not in self.videos:
                print(f"Video {video_key} not found")
                return

            video_path = self.videos[video_key]
            if not os.path.exists(video_path):
                print(f"Video file not found: {video_path}")
                return

            # Build VLC command
            cmd = ["cvlc", "--intf", "dummy",
                   "--no-video-title-show",
                   "--fullscreen", "--no-osd",
                   "--no-video-deco",        # just in case
                   "--video-on-top"]         # makes sure new window is topmost

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
                            text = result.get('text', '').lower().strip()
                            
                            if text and len(text.split()) <= 3:
                                print(f"Recognized: '{text}'")
                                
                                for command in self.commands:
                                    if command in text or \
                                       (command == "coffee" and ("cafe" in text or "caffeine" in text or "coff" in text)) or \
                                       (command == "insect" and ("bug" in text or "beetle" in text or "insec" in text)) or \
                                       (command == "grasshopper" and ("grass" in text or "hopper" in text)):
                                        
                                        print(f"Command detected: {command}")
                                        self.handle_command(command)
                                        # No return needed; the loop continues after handling
                                        break # Exit the for loop once a command is handled
                                        
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

        # --- launch the command clip (unchanged) ---
        cmd = ["cvlc", "--intf", "dummy",
               "--no-video-title-show", "--fullscreen", "--no-osd",
               "--video-on-top", "--play-and-exit", self.videos[command]]
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
            self.play_video("listening", loop=True, with_audio=False)  # runs muted in the background
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
                           self.videos["welcome"]]

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