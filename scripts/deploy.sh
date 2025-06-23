#!/bin/bash
# Deploy script to sync with Pi

PI_HOST="varun@192.168.50.45"
PI_DIR="/home/varun/videobox"

echo "Deploying to Raspberry Pi..."

# Sync files
sshpass -p '12345' rsync -av --exclude='venv/' --exclude='.git/' --exclude='*.pyc' \
    ./ ${PI_HOST}:${PI_DIR}/

# Run setup on Pi
sshpass -p '12345' ssh -o StrictHostKeyChecking=no ${PI_HOST} "cd ${PI_DIR} && bash scripts/setup_pi.sh"

echo "Deployment complete!"