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
import sounddevice as sd
import pvporcupine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

# Window mode flag (set False for fullscreen)
WINDOW_MODE = True

# Global process reference
current_video = None

def get_mpv_command(video_path, loop=False):
    """Build mpv command based on mode"""
    cmd = [
        'mpv',
        '--vo=gpu',             # Use GPU video output
        '--hwdec=no',           # Disable hardware acceleration (more stable)
        '--really-quiet',
        '--no-osc',             # No on-screen controller
        '--no-input-default-bindings',  # Disable keyboard shortcuts
        '--vf=scale=800:480',   # Scale to smaller resolution
        '--no-correct-pts',     # Faster playback
        '--no-border',          # Remove window borders
        '--ontop',              # Keep on top of other windows
        '--no-keepaspect-window', # Don't maintain aspect ratio of window
    ]
    
    if loop:
        cmd.append('--loop-file=inf')
    
    if WINDOW_MODE:
        cmd.extend(['--geometry=800x480', '--title=VoiceBox'])
    else:
        cmd.extend(['--fullscreen', '--fs'])
    
    cmd.append(video_path)
    return cmd

def play_listening_video():
    """Start playing the listening animation in a loop"""
    global current_video
    stop_current_video()
    print("Starting listening animation...")
    current_video = subprocess.Popen(get_mpv_command(LISTENING_VIDEO, loop=True))
    return current_video

def stop_current_video():
    """Stop any currently playing video"""
    global current_video
    if current_video and current_video.poll() is None:
        current_video.terminate()
        try:
            current_video.wait(timeout=1)  # Reduced timeout for faster transitions
        except subprocess.TimeoutExpired:
            current_video.kill()
            current_video.wait()
        current_video = None
        # Removed sleep for faster transitions

def play_response_video(video_path):
    """Play a response video once, then return to listening"""
    global current_video
    stop_current_video()
    print(f"Playing response video: {os.path.basename(video_path)}")
    
    # Play response video and wait for completion
    process = subprocess.Popen(get_mpv_command(video_path, loop=False))
    process.wait()
    
    # Return to listening animation
    play_listening_video()

def cleanup(signum=None, frame=None):
    """Clean shutdown handler"""
    print("\nShutting down VoiceBox...")
    stop_current_video()
    sys.exit(0)

def main():
    # Set up signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    print("="*50)
    print("VoiceBox Starting Up")
    print(f"Mode: {'Window' if WINDOW_MODE else 'Fullscreen'}")
    print("="*50)
    
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
    
    # Start listening animation
    play_listening_video()
    
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
                
                # Auto-restart if video crashes
                if current_video and current_video.poll() is not None:
                    print("Video stopped unexpectedly, restarting...")
                    play_listening_video()
                    
    except Exception as e:
        print(f"Error: {e}")
    finally:
        porcupine.delete()
        cleanup()

if __name__ == "__main__":
    # Check if running in test mode
    if len(sys.argv) > 1 and sys.argv[1] == '--fullscreen':
        WINDOW_MODE = False
    
    main()