#!/usr/bin/env python3
"""Hardware test script for VoiceBox (Vosk Version)"""

import subprocess
import sounddevice as sd
import numpy as np
import time
import os
import sys
import json

print("="*60)
print("VoiceBox Hardware Test (Vosk Version)")
print("="*60)

# Test 1: Check Python packages
print("\n1. Checking Python packages...")
packages = ['vosk', 'sounddevice', 'python-dotenv', 'numpy', 'pyudev']
for pkg in packages:
    try:
        __import__(pkg.replace('-', '_'))
        print(f"   ✓ {pkg}")
    except ImportError:
        print(f"   ✗ {pkg} - Run: pip3 install {pkg}")

# Test 2: Check Vosk model
print("\n2. Checking Vosk model...")
model_path = "/home/varun/videobox/models/vosk-model-en-us-small"
if os.path.exists(model_path):
    try:
        import vosk
        vosk.SetLogLevel(-1)
        model = vosk.Model(model_path)
        print(f"   ✓ Vosk model loaded from {model_path}")
    except Exception as e:
        print(f"   ✗ Vosk model error: {e}")
else:
    print(f"   ✗ Vosk model not found at {model_path}")
    print("      Download with: wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")

# Test 3: Check video files
print("\n3. Checking video files...")
video_dir = "/home/varun/videobox/videos"
required_videos = ['listening.mp4']
optional_videos = ['welcome.mp4']

for video in required_videos:
    path = os.path.join(video_dir, video)
    if os.path.exists(path):
        size = os.path.getsize(path) / 1024 / 1024
        print(f"   ✓ {video} ({size:.1f} MB)")
    else:
        print(f"   ✗ {video} NOT FOUND")

for video in optional_videos:
    path = os.path.join(video_dir, video)
    if os.path.exists(path):
        size = os.path.getsize(path) / 1024 / 1024
        print(f"   ✓ {video} ({size:.1f} MB) - Optional")
    else:
        print(f"   ⚬ {video} not found (optional)")

# Test 4: Test video discovery
print("\n4. Testing video discovery...")
try:
    sys.path.append('/home/varun/videobox/src')
    from video_discovery import VideoDiscovery
    
    discovery = VideoDiscovery()
    videos = discovery.get_all_videos()
    
    print(f"   Found {len(videos)} command videos:")
    for command, path in videos.items():
        print(f"   - '{command}' -> {os.path.basename(path)}")
        
except Exception as e:
    print(f"   ✗ Video discovery error: {e}")

# Test 5: Test speech recognition
print("\n5. Testing speech recognition...")
if os.path.exists(model_path):
    try:
        import vosk
        vosk.SetLogLevel(-1)
        model = vosk.Model(model_path)
        rec = vosk.KaldiRecognizer(model, 16000)
        
        print("   Recording 5 seconds - SAY A VIDEO NAME!")
        duration = 5
        sample_rate = 16000
        recording = sd.rec(int(duration * sample_rate), 
                           samplerate=sample_rate, 
                           channels=1, 
                           dtype='float32')
        sd.wait()
        
        # Process with Vosk
        audio_data = (recording[:, 0] * 32767).astype(np.int16).tobytes()
        
        if rec.AcceptWaveform(audio_data):
            result = json.loads(rec.Result())
            text = result.get('text', '')
            confidence = result.get('confidence', 0)
            
            if text:
                print(f"   ✓ Recognized: '{text}' (confidence: {confidence:.2f})")
            else:
                print("   ⚬ No speech detected")
        else:
            partial = json.loads(rec.PartialResult())
            partial_text = partial.get('partial', '')
            if partial_text:
                print(f"   ⚬ Partial: '{partial_text}'")
            else:
                print("   ⚬ No speech recognized")
                
    except Exception as e:
        print(f"   ✗ Speech recognition error: {e}")

print("\n" + "="*60)
print("Test complete! Fix any ✗ items before running VoiceBox")
print("="*60)