#!/bin/bash
# ============================================================
# REBUILD DOCKER WITH TORCH + TRANSFORMERS
# ============================================================
# This script adds the AI segmentation dependencies to your
# Image Tagger backend container.
#
# HOW TO USE:
# 1. Put this file in your Tagging_Contractor folder
# 2. Open Terminal app (Applications > Utilities > Terminal)
# 3. Type: cd ~/REPOS/Tagging_Contractor
# 4. Type: bash rebuild_with_localized.sh
# 5. Wait ~10-15 minutes (downloads ~2GB)
# ============================================================

echo "============================================"
echo "STEP 1: Checking we're in the right place..."
echo "============================================"

if [ ! -f "docker-compose.yml" ]; then
    echo "ERROR: docker-compose.yml not found!"
    echo "Make sure you're in the Tagging_Contractor folder."
    echo "Try: cd ~/REPOS/Tagging_Contractor"
    exit 1
fi

echo "✓ Found docker-compose.yml"
echo ""

echo "============================================"
echo "STEP 2: Adding dependencies to Dockerfile..."
echo "============================================"

# Check if already added
if grep -q "torch" Dockerfile.api 2>/dev/null; then
    echo "✓ torch already in Dockerfile.api"
else
    # Add torch and transformers to Dockerfile.api
    # Find the last RUN pip install line and add after it
    echo "" >> Dockerfile.api
    echo "# Localized attribute dependencies (added by rebuild script)" >> Dockerfile.api
    echo "RUN pip install torch transformers --no-cache-dir" >> Dockerfile.api
    echo "✓ Added torch and transformers to Dockerfile.api"
fi

echo ""

echo "============================================"
echo "STEP 3: Stopping existing containers..."
echo "============================================"

docker-compose down
echo "✓ Containers stopped"
echo ""

echo "============================================"
echo "STEP 4: Rebuilding (this takes 10-15 min)..."
echo "============================================"
echo "Downloading ~2GB of AI libraries..."
echo ""

docker-compose build --no-cache api

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Build successful!"
else
    echo ""
    echo "ERROR: Build failed. Check the messages above."
    exit 1
fi

echo ""

echo "============================================"
echo "STEP 5: Starting containers..."
echo "============================================"

docker-compose up -d

echo ""
echo "============================================"
echo "DONE!"
echo "============================================"
echo ""
echo "Your Image Tagger now has:"
echo "  - torch (PyTorch AI framework)"
echo "  - transformers (SegFormer model)"
echo ""
echo "First time you use segmentation, it will"
echo "download the SegFormer model (~400MB)."
echo ""
echo "To check status: docker-compose ps"
echo "To see logs:     docker-compose logs -f api"
echo ""
