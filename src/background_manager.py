#!/usr/bin/env python3
"""
Background Manager - Maintains persistent black fullscreen window
This eliminates desktop flashes during video transitions
"""

import tkinter as tk
import threading
import time
import signal
import sys

class BackgroundManager:
    def __init__(self):
        self.root = None
        self.running = True
        
    def create_background(self):
        """Create persistent black fullscreen window"""
        self.root = tk.Tk()
        self.root.title("VoiceBox Background")
        self.root.configure(bg='black')
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)  # Stay on top of desktop
        self.root.overrideredirect(True)  # Remove window decorations
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.cleanup)
        
        # Resize after X is ready to fix black corner strip
        self.root.after(100, lambda: self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0"))
        
        # Keep window alive
        self.update_background()
        
    def update_background(self):
        """Keep background window alive and responsive"""
        if self.running and self.root:
            try:
                self.root.update()
                self.root.after(100, self.update_background)
            except tk.TclError:
                pass
                
    def cleanup(self):
        """Clean shutdown"""
        self.running = False
        if self.root:
            try:
                self.root.quit()
                self.root.destroy()
            except:
                pass
                
    def run(self):
        """Run the background manager"""
        try:
            self.create_background()
            self.root.mainloop()
        except KeyboardInterrupt:
            self.cleanup()
        except Exception as e:
            print(f"Background manager error: {e}")
            self.cleanup()

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    manager = BackgroundManager()
    manager.run()