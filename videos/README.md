# VoiceBox Videos Directory

This directory contains system videos for the VoiceBox application.

## Required Videos

- **welcome.mp4** - Played once at startup
- **listening.mp4** - Looped when waiting for voice commands

## Video Requirements

- **Format**: H.264 encoded MP4
- **Resolution**: 800×480 (matches Pi display)
- **Size**: ≤ 3 MB each for optimal performance
- **Frame Rate**: 30 FPS recommended
- **Audio**: Optional (will be ignored during playback)

## Supported Video Formats

The system supports these video file extensions:
- .mp4 (recommended)
- .mov
- .mkv
- .avi

## Adding Custom Videos

1. Place video files in this directory
2. Use descriptive filenames (e.g., "movie_trailer.mp4")
3. The system will clean filenames for voice recognition:
   - "Movie_Trailer.mp4" → voice command: "movie trailer"
   - "Funny-Cat-Video.mp4" → voice command: "funny cat video"

## Video Optimization

To optimize videos for the Raspberry Pi, use ffmpeg:

```bash
ffmpeg -i input.mp4 -vf scale=800:480 -c:v libx264 -crf 23 -preset medium -an output.mp4
```

This command:
- Scales to 800×480 resolution
- Uses H.264 encoding with CRF 23 (good quality/size balance)
- Removes audio (-an flag)
- Uses medium preset for reasonable encoding speed