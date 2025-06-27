#!/usr/bin/env python3
"""
Video Discovery Engine
Handles USB detection and video file scanning
"""

import os
import glob
import re
from pathlib import Path
import psutil

class VideoDiscovery:
    def __init__(self):
        self.video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.m4v']
        self.reserved_names = ['listening', 'welcome', 'help']
        self.local_video_dir = "/home/varun/voicebox/videos"
        
    def clean_filename_to_command(self, filename):
        """Convert filename to voice command word"""
        # Remove extension and convert to lowercase
        name = Path(filename).stem.lower()
        
        # Remove common video file prefixes/suffixes
        prefixes_to_remove = ['video_', 'vid_', 'movie_', 'clip_']
        suffixes_to_remove = ['_video', '_vid', '_movie', '_clip', '_final', '_hd']
        
        for prefix in prefixes_to_remove:
            if name.startswith(prefix):
                name = name[len(prefix):]
        
        for suffix in suffixes_to_remove:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        
        # Remove special characters and numbers at start/end
        name = re.sub(r'^[^a-z]+|[^a-z]+$', '', name)
        
        # Replace internal special chars with spaces, then remove extra spaces
        name = re.sub(r'[^a-z0-9]+', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Convert multi-word to single word if reasonable
        if ' ' in name:
            words = name.split()
            # Use first significant word if it's long enough
            if len(words) > 0 and len(words[0]) >= 3:
                return words[0]
            # Otherwise combine first two words
            elif len(words) >= 2:
                return words[0] + words[1]
        
        return name if len(name) >= 2 else None
    
    def scan_directory(self, directory_path):
        """Scan directory for video files and create command mapping"""
        videos = {}
        
        if not os.path.exists(directory_path):
            return videos
        
        print(f"Scanning: {directory_path}")
        
        for ext in self.video_extensions:
            pattern = os.path.join(directory_path, f"*{ext}")
            for video_path in glob.glob(pattern):
                filename = os.path.basename(video_path)
                command = self.clean_filename_to_command(filename)
                
                # Skip reserved system videos and invalid commands
                if command and command not in self.reserved_names:
                    if command in videos:
                        print(f"  Warning: Duplicate command '{command}' - keeping first found")
                    else:
                        videos[command] = video_path
                        print(f"  Added: '{command}' -> {filename}")
        
        return videos
    
    def get_usb_drives(self):
        """Get list of mounted USB drives"""
        usb_drives = []
        
        # Get all mounted partitions
        for partition in psutil.disk_partitions():
            # Check if it's a removable device (USB)
            if 'removable' in partition.opts or '/media/' in partition.mountpoint:
                if os.path.exists(partition.mountpoint):
                    usb_drives.append(partition.mountpoint)
        
        # Also check common USB mount points
        common_usb_paths = [
            '/media/usb', '/media/usb0', '/media/usb1',
            '/mnt/usb', '/media/pi', '/media/varun'
        ]
        
        for path in common_usb_paths:
            if os.path.exists(path) and os.path.ismount(path):
                if path not in usb_drives:
                    usb_drives.append(path)
        
        return usb_drives
    
    def scan_usb_drives(self):
        """Scan all USB drives for videos"""
        all_usb_videos = {}
        usb_drives = self.get_usb_drives()
        
        print(f"Found {len(usb_drives)} USB drive(s)")
        
        for usb_path in usb_drives:
            try:
                usb_videos = self.scan_directory(usb_path)
                
                # Add source info for debugging
                for command, video_path in usb_videos.items():
                    all_usb_videos[command] = video_path
                
                if usb_videos:
                    print(f"USB {usb_path}: {len(usb_videos)} videos found")
                
            except Exception as e:
                print(f"Error scanning USB {usb_path}: {e}")
        
        return all_usb_videos
    
    def scan_local_videos(self):
        """Scan local videos directory"""
        return self.scan_directory(self.local_video_dir)
    
    def get_all_videos(self):
        """Get complete video library (local + USB)"""
        all_videos = {}
        
        # Start with local videos
        local_videos = self.scan_local_videos()
        all_videos.update(local_videos)
        
        # Add USB videos (these override local if same command)
        usb_videos = self.scan_usb_drives()
        if usb_videos:
            print(f"USB videos will override local videos for duplicate commands")
            all_videos.update(usb_videos)
        
        # Remove system videos from commands
        for reserved in self.reserved_names:
            all_videos.pop(reserved, None)
        
        return all_videos
    
    def get_video_info(self, video_path):
        """Get video file information"""
        try:
            stat = os.stat(video_path)
            size_mb = stat.st_size / (1024 * 1024)
            
            return {
                'path': video_path,
                'filename': os.path.basename(video_path),
                'size_mb': round(size_mb, 1),
                'source': 'USB' if '/media/' in video_path else 'Local'
            }
        except Exception as e:
            return {'error': str(e)}