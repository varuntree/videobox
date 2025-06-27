#!/bin/bash
# VoiceBox deployment script for development

set -e

PI_HOST="varun@192.168.50.45"
PI_PASSWORD="12345"
DEPLOY_DIR="/home/varun/voicebox"
LOCAL_DIR="$(dirname "$(dirname "$(realpath "$0")")")"

echo "==========================================="
echo "VoiceBox Deployment Script"
echo "==========================================="
echo "Local directory: ${LOCAL_DIR}"
echo "Target: ${PI_HOST}:${DEPLOY_DIR}"
echo

# 1. Test connection
echo "1. Testing connection to Raspberry Pi..."
if sshpass -p "${PI_PASSWORD}" ssh -o StrictHostKeyChecking=no ${PI_HOST} "whoami" > /dev/null 2>&1; then
    echo "   ✓ Connection successful"
else
    echo "   ✗ Cannot connect to Pi. Check IP address and credentials."
    exit 1
fi

# 2. Create directories on Pi
echo "2. Creating directories on Pi..."
sshpass -p "${PI_PASSWORD}" ssh -o StrictHostKeyChecking=no ${PI_HOST} "
    mkdir -p ${DEPLOY_DIR}/{src,config,scripts,models,videos}
    echo '   ✓ Directories created'
"

# 3. Transfer source code
echo "3. Transferring source code..."
sshpass -p "${PI_PASSWORD}" scp -o StrictHostKeyChecking=no -r \
    "${LOCAL_DIR}/src/"* \
    ${PI_HOST}:${DEPLOY_DIR}/src/
echo "   ✓ Source code transferred"

# 4. Transfer config files
echo "4. Transferring configuration files..."
sshpass -p "${PI_PASSWORD}" scp -o StrictHostKeyChecking=no -r \
    "${LOCAL_DIR}/config/"* \
    ${PI_HOST}:${DEPLOY_DIR}/config/

sshpass -p "${PI_PASSWORD}" scp -o StrictHostKeyChecking=no \
    "${LOCAL_DIR}/.env" \
    "${LOCAL_DIR}/requirements.txt" \
    ${PI_HOST}:${DEPLOY_DIR}/
echo "   ✓ Configuration files transferred"

# 5. Transfer scripts
echo "5. Transferring scripts..."
sshpass -p "${PI_PASSWORD}" scp -o StrictHostKeyChecking=no -r \
    "${LOCAL_DIR}/scripts/"* \
    ${PI_HOST}:${DEPLOY_DIR}/scripts/
echo "   ✓ Scripts transferred"

# 6. Transfer optimized videos
echo "6. Transferring optimized videos..."
if [ -d "${LOCAL_DIR}/videos_optimized" ]; then
    sshpass -p "${PI_PASSWORD}" scp -o StrictHostKeyChecking=no \
        "${LOCAL_DIR}/videos_optimized/"* \
        ${PI_HOST}:${DEPLOY_DIR}/videos/
    echo "   ✓ Optimized videos transferred"
else
    echo "   ⚠ videos_optimized directory not found"
fi

# 7. Set permissions
echo "7. Setting permissions on Pi..."
sshpass -p "${PI_PASSWORD}" ssh -o StrictHostKeyChecking=no ${PI_HOST} "
    chmod +x ${DEPLOY_DIR}/src/*.py
    chmod +x ${DEPLOY_DIR}/scripts/*.sh
    echo '   ✓ Permissions set'
"

# 8. Optional: Run installation
echo
echo "Deployment complete!"
echo
echo "To complete setup on Pi, run:"
echo "ssh ${PI_HOST}"
echo "cd ${DEPLOY_DIR}"
echo "./scripts/install.sh"
echo
echo "Or run installation remotely:"
read -p "Run installation script now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "8. Running installation on Pi..."
    sshpass -p "${PI_PASSWORD}" ssh -o StrictHostKeyChecking=no ${PI_HOST} "
        cd ${DEPLOY_DIR}
        ./scripts/install.sh
    "
    echo "   ✓ Installation complete"
    echo
    echo "VoiceBox is ready! Test with:"
    echo "ssh ${PI_HOST}"
    echo "cd ${DEPLOY_DIR}"
    echo "./venv/bin/python src/test_system.py"
else
    echo "Installation skipped. Run manually when ready."
fi