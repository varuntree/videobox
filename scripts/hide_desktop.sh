#!/bin/bash
# Hide desktop elements for kiosk mode

# Start splash screen immediately to cover desktop
python3 /home/varun/videobox/scripts/create_splash.py &
SPLASH_PID=$!

# Disable screensaver and power management
xset s off 2>/dev/null
xset -dpms 2>/dev/null
xset s noblank 2>/dev/null

# Hide mouse cursor immediately
unclutter -idle 0 -root &

# Hide taskbar (lxpanel)
pkill lxpanel 2>/dev/null

# Set desktop background to black
xsetroot -solid black 2>/dev/null

# Wait for system to stabilize, then start VoiceBox
sleep 5
cd /home/varun/videobox

# Kill splash screen and start VoiceBox
kill $SPLASH_PID 2>/dev/null
./venv/bin/python src/voicebox.py --fullscreen