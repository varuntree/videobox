#!/usr/bin/env python3
"""
Video Discovery Module
Handles USB detection and video file scanning
"""

import os
import glob
import time
import re
from pathlib import Path
import pyudev

class VideoDiscovery:
    def __init__(self, usb_mount_point="/media/usb", local_video_dir="/home/varun/videobox/videos"):
        self.usb_mount_point = usb_mount_point
        self.local_video_dir = local_video_dir
        self.video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv']
        self.reserved_names = ['listening', 'welcome']  # System videos
        
    def clean_filename_to_command(self, filename):
        """Convert filename to voice command"""
        # Remove extension
        name = Path(filename).stem.lower()
        
        # Remove special characters and numbers
        name = re.sub(r'[^a-zA-Z\s]', '', name)
        
        # Replace multiple spaces with single space
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Convert to single word if possible
        if ' ' in name:
            # Try to use first meaningful word
            words = name.split()
            if len(words) > 0:
                return words[0] if len(words[0]) > 2 else name.replace(' ', '')
        
        return name

    def scan_directory(self, directory):
        """Scan directory for video files"""
        videos = {}
        
        if not os.path.exists(directory):
            return videos
            
        for ext in self.video_extensions:
            pattern = os.path.join(directory, f"*{ext}")
            for video_path in glob.glob(pattern, recursive=False):
                filename = os.path.basename(video_path)
                command = self.clean_filename_to_command(filename)
                
                # Skip reserved system videos
                if command not in self.reserved_names and command:
                    videos[command] = video_path
                    
        return videos

    def scan_usb_drives(self):
        """Scan all mounted USB drives for videos"""
        videos = {}
        
        # Common USB mount points
        usb_paths = [
            "/media/usb",
            "/media/usb0", 
            "/media/usb1",
            "/mnt/usb",
            "/media/pi",
            "/media/varun"
        ]
        
        # Also check /media/* for any mounted drives
        if os.path.exists("/media"):
            for item in os.listdir("/media"):
                full_path = os.path.join("/media", item)
                if os.path.isdir(full_path):
                    usb_paths.append(full_path)
        
        for usb_path in usb_paths:
            if os.path.exists(usb_path) and os.path.ismount(usb_path):
                print(f"Scanning USB drive: {usb_path}")
                usb_videos = self.scan_directory(usb_path)
                videos.update(usb_videos)
                
        return videos

    def get_all_videos(self):
        """Get all available videos (local + USB)"""
        all_videos = {}
        
        # Scan local videos directory
        local_videos = self.scan_directory(self.local_video_dir)
        all_videos.update(local_videos)
        
        # Scan USB drives (these override local if same command name)
        usb_videos = self.scan_usb_drives()
        all_videos.update(usb_videos)
        
        return all_videos

    def monitor_usb_changes(self):
        """Monitor for USB plug/unplug events (optional background task)"""
        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by(subsystem='block', device_type='partition')
        
        for device in iter(monitor.poll, None):
            if device.action in ['add', 'remove']:
                print(f"USB device {device.action}: {device.device_node}")
                # Could trigger video rescan here
                yield device.action