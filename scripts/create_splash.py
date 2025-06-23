#!/usr/bin/env python3
"""Create a black splash screen to hide boot process"""

import tkinter as tk
import time
import threading
import sys

def create_splash():
    """Create fullscreen black window to hide desktop during startup"""
    root = tk.Tk()
    root.title("VoiceBox")
    root.configure(bg='black')
    root.attributes('-fullscreen', True)
    root.attributes('-topmost', True)
    
    # Add loading text
    label = tk.Label(root, text="VoiceBox Loading...", 
                     fg='white', bg='black', 
                     font=('Arial', 24))
    label.pack(expand=True)
    
    # Auto-close after 8 seconds (enough time for VoiceBox to start)
    def close_splash():
        time.sleep(8)
        root.quit()
        root.destroy()
    
    threading.Thread(target=close_splash, daemon=True).start()
    
    try:
        root.mainloop()
    except:
        pass

if __name__ == "__main__":
    create_splash()