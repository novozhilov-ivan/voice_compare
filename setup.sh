#!/bin/bash

echo "================================================"
echo "Voice Speaker Recognition - Setup Script"
echo "================================================"
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Check if FFmpeg is installed
if command -v ffmpeg &> /dev/null; then
    echo "✓ FFmpeg is installed"
else
    echo "✗ FFmpeg is not installed"
    echo "  Please install FFmpeg:"
    echo "    Ubuntu/Debian: sudo apt-get install ffmpeg"
    echo "    macOS: brew install ffmpeg"
    echo "    Windows: Download from https://ffmpeg.org/download.html"
    exit 1
fi

# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    echo ""
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
else
    echo "✓ uv is installed"
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo ""
    echo "Creating virtual environment with uv..."
    uv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Install dependencies
echo ""
echo "Installing Python dependencies with uv..."
echo "This may take several minutes..."
uv sync

# Create necessary directories
echo ""
echo "Creating data directories..."
mkdir -p data/videos data/audio data/models

# Make run script executable
chmod +x run.py

echo ""
echo "================================================"
echo "✓ Setup completed successfully!"
echo "================================================"
echo ""
echo "To start the application:"
echo "  1. Activate virtual environment: source .venv/bin/activate"
echo "  2. Run the application: python run.py"
echo ""
echo "Or simply run: uv run python run.py"
echo ""
echo "Web interface will be available at:"
echo "  http://localhost:8000/static/index.html"
echo ""
