#!/bin/bash
# Setup boot splash to hide boot messages

echo "Setting up boot splash screen..."

# Backup original cmdline.txt
sudo cp /boot/firmware/cmdline.txt /boot/firmware/cmdline.txt.backup 2>/dev/null || sudo cp /boot/cmdline.txt /boot/cmdline.txt.backup

# Add quiet boot parameters
CMDLINE_FILE="/boot/firmware/cmdline.txt"
if [ ! -f "$CMDLINE_FILE" ]; then
    CMDLINE_FILE="/boot/cmdline.txt"
fi

# Check if quiet parameters are already added
if ! grep -q "quiet splash" "$CMDLINE_FILE"; then
    echo "Adding quiet boot parameters..."
    sudo sed -i 's/$/ quiet splash loglevel=3 rd.systemd.show_status=false rd.udev.log_priority=3 vt.global_cursor_default=0/' "$CMDLINE_FILE"
fi

# Create custom splash screen service (optional)
cat << 'EOF' | sudo tee /etc/systemd/system/voicebox-splash.service >/dev/null
[Unit]
Description=VoiceBox Splash Screen
DefaultDependencies=false
After=local-fs.target
Before=display-manager.service

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'echo 0 > /sys/class/graphics/fbcon/cursor_blink'
ExecStart=/bin/bash -c 'setterm -blank 0 -powersave off -powerdown 0'
RemainAfterExit=true

[Install]
WantedBy=sysinit.target
EOF

sudo systemctl enable voicebox-splash.service

echo "Boot splash setup complete!"
echo "Reboot to see changes: sudo reboot"