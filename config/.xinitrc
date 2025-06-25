#!/bin/sh
xset s off            # no screensaver
xset -dpms            # no power-down
xset s noblank
unclutter -idle 0 -root &

# one black window that always covers the root
python3 /home/varun/videobox/src/background_manager.py &

# give background a moment to size correctly
sleep 1

# hand over to VoiceBox (fullscreen flag no longer needed)
exec /home/varun/videobox/venv/bin/python /home/varun/videobox/src/voicebox.py