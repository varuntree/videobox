#!/usr/bin/env python3
"""
VoiceBox - Dynamic Voice-Activated Video Display
Recognizes any spoken filename and plays corresponding videos
"""

import signal
import sys
import time
import threading
from pathlib import Path
from dotenv import load_dotenv

from video_discovery import VideoDiscovery
from voice_processor import VoiceProcessor
from display_manager import DisplayManager

class VoiceBox:
    def __init__(self):
        load_dotenv()
        
        # Initialize components
        self.video_discovery = VideoDiscovery()
        self.voice_processor = VoiceProcessor()
        self.display_manager = DisplayManager()
        
        # State management
        self.available_videos = {}
        self.is_running = True
        self.current_state = "startup"
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
    
    def startup_sequence(self):
        """System startup and initialization"""
        print("="*50)
        print("VoiceBox Dynamic System Starting")
        print("="*50)
        
        # Initialize display
        self.display_manager.initialize()
        
        # Play welcome video
        if self.display_manager.has_welcome_video():
            print("Playing welcome message...")
            self.display_manager.play_welcome()
            time.sleep(3)  # Welcome video duration
        
        # Initialize voice recognition
        self.voice_processor.initialize()
        
        # Scan for videos
        self.refresh_video_library()
        
        # Start listening mode
        self.enter_listening_mode()
    
    def refresh_video_library(self):
        """Scan and update available video library"""
        print("Scanning for videos...")
        self.available_videos = self.video_discovery.get_all_videos()
        
        video_count = len(self.available_videos)
        print(f"Found {video_count} voice commands:")
        
        for command, video_path in self.available_videos.items():
            video_name = Path(video_path).name
            source = "USB" if "/media/" in video_path else "Local"
            print(f"  '{command}' -> {video_name} ({source})")
        
        return self.available_videos
    
    def enter_listening_mode(self):
        """Enter continuous listening state"""
        print("\nEntering listening mode...")
        self.current_state = "listening"
        self.display_manager.play_listening_animation()
        
        # Start voice processing
        self.voice_processor.start_listening(self.on_voice_command)
        
        print("Ready! Speak any video filename to play it.")
        if self.available_videos:
            commands = list(self.available_videos.keys())[:5]  # Show first 5
            print(f"Try saying: {', '.join(commands)}")
    
    def on_voice_command(self, recognized_text, confidence):
        """Handle recognized voice command"""
        if not recognized_text or confidence < 0.7:
            return
        
        print(f"\nRecognized: '{recognized_text}' (confidence: {confidence:.2f})")
        
        # Find matching video
        video_path = self.find_matching_video(recognized_text)
        
        if video_path:
            self.play_response_video(video_path)
        else:
            print(f"No video found for: '{recognized_text}'")
            # Could play "not found" audio here
    
    def find_matching_video(self, spoken_text):
        """Find best matching video for spoken command"""
        spoken_lower = spoken_text.lower().strip()
        
        # Exact match first
        if spoken_lower in self.available_videos:
            return self.available_videos[spoken_lower]
        
        # Partial matches
        for command, video_path in self.available_videos.items():
            if command in spoken_lower or spoken_lower in command:
                print(f"Partial match: '{spoken_text}' -> '{command}'")
                return video_path
        
        # Fuzzy matching (optional enhancement)
        return self.fuzzy_match(spoken_lower)
    
    def fuzzy_match(self, spoken_text, threshold=0.6):
        """Fuzzy string matching for better recognition"""
        import difflib
        
        commands = list(self.available_videos.keys())
        matches = difflib.get_close_matches(
            spoken_text, commands, n=1, cutoff=threshold
        )
        
        if matches:
            matched_command = matches[0]
            print(f"Fuzzy match: '{spoken_text}' -> '{matched_command}'")
            return self.available_videos[matched_command]
        
        return None
    
    def play_response_video(self, video_path):
        """Play customer video, then return to listening"""
        self.current_state = "playing_response"
        
        video_name = Path(video_path).name
        print(f"Playing: {video_name}")
        
        # Play the video
        self.display_manager.play_video(video_path)
        
        # Monitor for completion
        self.monitor_video_completion()
    
    def monitor_video_completion(self):
        """Monitor video playback and return to listening when done"""
        def check_completion():
            while self.current_state == "playing_response":
                if self.display_manager.is_video_finished():
                    print("Video finished, returning to listening...")
                    self.enter_listening_mode()
                    break
                time.sleep(0.5)
        
        # Run in background thread
        threading.Thread(target=check_completion, daemon=True).start()
    
    def run(self):
        """Main application loop"""
        try:
            self.startup_sequence()
            
            # Background video library refresh
            def periodic_refresh():
                while self.is_running:
                    time.sleep(30)  # Check every 30 seconds
                    if self.current_state == "listening":
                        old_count = len(self.available_videos)
                        self.refresh_video_library()
                        new_count = len(self.available_videos)
                        if new_count != old_count:
                            print(f"Video library updated: {new_count} videos available")
            
            refresh_thread = threading.Thread(target=periodic_refresh, daemon=True)
            refresh_thread.start()
            
            # Main loop
            while self.is_running:
                time.sleep(1)
                
                # Health checks
                if not self.display_manager.is_healthy():
                    print("Display manager unhealthy, restarting...")
                    self.display_manager.restart()
        
        except KeyboardInterrupt:
            self.shutdown()
        except Exception as e:
            print(f"System error: {e}")
            self.shutdown(1)
    
    def shutdown(self, exit_code=0):
        """Clean system shutdown"""
        print("\nShutting down VoiceBox...")
        self.is_running = False
        
        # Stop components
        self.voice_processor.stop()
        self.display_manager.stop()
        
        print("Shutdown complete.")
        sys.exit(exit_code)

def main():
    """Application entry point"""
    voicebox = VoiceBox()
    voicebox.run()

if __name__ == "__main__":
    main()