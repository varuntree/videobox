#!/usr/bin/env python3
"""Hardware test script for VoiceBox"""

import subprocess
import sounddevice as sd
import numpy as np
import time
import os
import sys

print("="*60)
print("VoiceBox Hardware Test")
print("="*60)

# Test 1: Check Python packages
print("\n1. Checking Python packages...")
packages = ['pvporcupine', 'sounddevice', 'python-dotenv', 'numpy']
for pkg in packages:
    try:
        __import__(pkg.replace('-', '_'))
        print(f"   ✓ {pkg}")
    except ImportError:
        print(f"   ✗ {pkg} - Run: pip3 install {pkg}")

# Test 2: Check video files
print("\n2. Checking video files...")
video_dir = "/home/varun/videobox/videos"
required_videos = ['listening.mp4', 'americano.mp4', 'bumblebee.mp4', 'grasshopper.mp4']

for video in required_videos:
    path = os.path.join(video_dir, video)
    if os.path.exists(path):
        size = os.path.getsize(path) / 1024 / 1024  # MB
        print(f"   ✓ {video} ({size:.1f} MB)")
    else:
        print(f"   ✗ {video} NOT FOUND")

# Test 3: Display test
print("\n3. Testing display...")
test_video = os.path.join(video_dir, 'listening.mp4')
if os.path.exists(test_video):
    print("   Playing listening video for 5 seconds...")
    proc = subprocess.Popen([
        'mpv', '--vo=gpu', '--hwdec=no', '--really-quiet', 
        '--geometry=800x480', '--title=Display Test',
        '--vf=scale=800:480', '--no-correct-pts',
        test_video
    ])
    time.sleep(5)
    proc.terminate()
    proc.wait()
    print("   ✓ Display working")
else:
    print("   ✗ No video available for display test")

# Test 4: Audio test
print("\n4. Testing microphone...")
print("   Audio devices:")
devices = sd.query_devices()
input_devices = []
for i, device in enumerate(devices):
    if device['max_input_channels'] > 0:
        print(f"   [{i}] {device['name']} ({device['max_input_channels']} ch)")
        input_devices.append(i)

if input_devices:
    print("\n   Recording 3 seconds - SPEAK NOW!")
    duration = 3
    sample_rate = 16000
    recording = sd.rec(int(duration * sample_rate), 
                       samplerate=sample_rate, 
                       channels=1, 
                       dtype='float32')
    sd.wait()
    
    level = np.max(np.abs(recording))
    print(f"   Peak level: {level:.4f}")
    
    if level > 0.01:
        print("   ✓ Microphone working!")
    else:
        print("   ✗ No audio detected - check mic connection")
else:
    print("   ✗ No input devices found!")

# Test 5: Check built-in wake words
print("\n5. Checking built-in wake words...")
try:
    import pvporcupine
    wake_words = ['americano', 'bumblebee', 'grasshopper']
    print("   Available built-in keywords:")
    for word in pvporcupine.KEYWORDS:
        status = "✓" if word in wake_words else " "
        print(f"   {status} {word}")
except ImportError:
    print("   ✗ pvporcupine not available")

# Test 6: Environment check
print("\n6. Checking environment...")
if os.path.exists('/home/varun/videobox/.env'):
    from dotenv import load_dotenv
    load_dotenv('/home/varun/videobox/.env')
    if os.getenv('PICOVOICE_ACCESS_KEY'):
        print("   ✓ Picovoice access key found")
    else:
        print("   ✗ PICOVOICE_ACCESS_KEY not set in .env")
else:
    print("   ✗ .env file not found")

print("\n" + "="*60)
print("Test complete! Fix any ✗ items before running VoiceBox")
print("="*60)