#!/bin/bash
# Set up USB auto-mounting for VoiceBox

echo "Setting up USB auto-mounting..."

# Create mount point
sudo mkdir -p /media/usb

# Add udev rule for auto-mounting
cat << 'EOF' | sudo tee /etc/udev/rules.d/99-usb-automount.rules
# Auto-mount USB drives for VoiceBox
KERNEL=="sd[a-z]*", SUBSYSTEM=="block", ENV{ID_FS_TYPE}!="", RUN+="/bin/mkdir -p /media/usb%n", RUN+="/bin/mount /dev/%k /media/usb%n"
EOF

# Reload udev rules
sudo udevadm control --reload-rules

echo "USB auto-mounting configured"
echo "USB drives will mount to /media/usb*"
echo ""
echo "To test:"
echo "1. Insert USB drive with video files" 
echo "2. Files should auto-mount and be discoverable by VoiceBox"
echo "3. Speak the filename (without extension) to play videos"