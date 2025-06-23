# Welcome Video Placeholder

Place your `welcome.mp4` file in this directory.

## Welcome Video Specifications:
- **Filename**: `welcome.mp4`
- **Duration**: 3-8 seconds recommended
- **Resolution**: 800x480 (same as other videos)
- **Content**: Welcome message, logo, branding, etc.
- **Audio**: Optional

## Creating Welcome Video:
If you don't have a welcome video yet, you can create one using ffmpeg:

```bash
# Create a simple black screen with text (example)
ffmpeg -f lavfi -i color=black:size=800x480:duration=5 -vf "drawtext=text='Welcome to VoiceBox':fontcolor=white:fontsize=36:x=(w-text_w)/2:y=(h-text_h)/2" welcome.mp4
```

## Note:
- If `welcome.mp4` is not found, VoiceBox will skip directly to the listening animation
- The welcome video plays once at startup, then transitions to listening mode