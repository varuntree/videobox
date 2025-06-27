#!/usr/bin/env python3
"""
Voice Processing Engine using Vosk
Handles real-time speech recognition
"""

import json
import threading
import queue
import time
import os
import sounddevice as sd
import vosk
import numpy as np

class VoiceProcessor:
    def __init__(self):
        self.model_path = os.getenv('VOSK_MODEL_PATH', '/home/varun/voicebox/models/vosk-model-en-us-small')
        self.sample_rate = 16000
        self.block_size = 1600  # 0.1 second blocks
        
        self.model = None
        self.recognizer = None
        self.audio_stream = None
        self.is_listening = False
        self.callback_function = None
        
        # Audio processing queue
        self.audio_queue = queue.Queue()
        self.processing_thread = None
    
    def initialize(self):
        """Initialize Vosk model and recognizer"""
        print("Initializing voice recognition...")
        
        # Check model exists
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Vosk model not found at: {self.model_path}")
        
        try:
            # Reduce Vosk logging
            vosk.SetLogLevel(-1)
            
            # Load model
            print(f"Loading Vosk model from: {self.model_path}")
            self.model = vosk.Model(self.model_path)
            
            # Create recognizer
            self.recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.SetMaxAlternatives(3)
            self.recognizer.SetWords(True)
            
            print("✓ Voice recognition initialized")
            return True
            
        except Exception as e:
            print(f"✗ Failed to initialize voice recognition: {e}")
            return False
    
    def audio_callback(self, indata, frames, time, status):
        """Audio stream callback"""
        if status:
            print(f"Audio warning: {status}")
        
        # Convert to int16 and queue for processing
        audio_data = (indata[:, 0] * 32767).astype(np.int16).tobytes()
        self.audio_queue.put(audio_data)
    
    def process_audio_queue(self):
        """Process audio data from queue in separate thread"""
        while self.is_listening:
            try:
                # Get audio data with timeout
                audio_data = self.audio_queue.get(timeout=1.0)
                
                # Process with Vosk
                if self.recognizer.AcceptWaveform(audio_data):
                    # Final result
                    result = json.loads(self.recognizer.Result())
                    self.handle_recognition_result(result)
                else:
                    # Partial result (optional for debugging)
                    partial = json.loads(self.recognizer.PartialResult())
                    self.handle_partial_result(partial)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Audio processing error: {e}")
                time.sleep(0.1)
    
    def handle_recognition_result(self, result):
        """Handle final recognition result"""
        text = result.get('text', '').strip()
        confidence = result.get('confidence', 0)
        
        if text and self.callback_function:
            # Call the registered callback
            self.callback_function(text, confidence)
    
    def handle_partial_result(self, partial):
        """Handle partial recognition result (optional)"""
        partial_text = partial.get('partial', '').strip()
        
        # Only show longer partial results to avoid spam
        if len(partial_text) > 8:
            print(f"Listening: {partial_text}...")
    
    def start_listening(self, callback_function):
        """Start continuous speech recognition"""
        if not self.model or not self.recognizer:
            print("Voice processor not initialized!")
            return False
        
        self.callback_function = callback_function
        self.is_listening = True
        
        # Start audio processing thread
        self.processing_thread = threading.Thread(
            target=self.process_audio_queue, 
            daemon=True
        )
        self.processing_thread.start()
        
        # Start audio stream
        try:
            self.audio_stream = sd.InputStream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                dtype='float32',
                channels=1,
                callback=self.audio_callback
            )
            self.audio_stream.start()
            
            print("✓ Voice recognition active")
            return True
            
        except Exception as e:
            print(f"✗ Failed to start audio stream: {e}")
            self.is_listening = False
            return False
    
    def stop(self):
        """Stop voice recognition"""
        print("Stopping voice recognition...")
        self.is_listening = False
        
        # Stop audio stream
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.audio_stream = None
        
        # Wait for processing thread to finish
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2)
        
        print("✓ Voice recognition stopped")
    
    def test_microphone(self):
        """Test microphone input levels"""
        print("Testing microphone (3 seconds)...")
        
        def test_callback(indata, frames, time, status):
            volume = np.sqrt(np.mean(indata**2))
            if volume > 0.01:
                print(f"Microphone level: {volume:.3f}")
        
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                callback=test_callback,
                dtype='float32'
            ):
                time.sleep(3)
            print("✓ Microphone test complete")
            return True
        except Exception as e:
            print(f"✗ Microphone test failed: {e}")
            return False