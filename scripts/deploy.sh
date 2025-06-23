#!/bin/bash
# Deploy script to sync with Pi

PI_HOST="pi@raspberrypi.local"
PI_DIR="/home/pi/videobox"

echo "Deploying to Raspberry Pi..."

# Sync files
rsync -av --exclude='venv/' --exclude='.git/' --exclude='*.pyc' \
    ./ ${PI_HOST}:${PI_DIR}/

# Run setup on Pi
ssh ${PI_HOST} "cd ${PI_DIR} && bash scripts/setup_pi.sh"

echo "Deployment complete!"