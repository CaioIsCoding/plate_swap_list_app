#!/bin/bash
set -e

echo "🚀 Starting Update..."

# 1. Update Code
echo "📥 Pulling latest code..."
git pull

# 2. Backend Dependencies
echo "🐍 Updating Backend (uv)..."
# Ensure we are in the root where pyproject.toml would be, or just sync the env
# Assuming this script is run from /opt/swaplist
export UV_PYTHON_INSTALL_DIR="/opt/swaplist/.python"
/root/.local/bin/uv sync

# 3. Frontend Build
echo "⚛️ Building Frontend..."
cd frontend
npm install
npm run build
cd ..

# 4. Restart Service
echo "🔄 Restarting Service..."
sudo systemctl restart swaplist

echo "✅ Update Complete!"
