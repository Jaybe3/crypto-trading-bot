#!/bin/bash
# Install dependencies for the crypto trading bot

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "  Crypto Trading Bot - Installation"
echo "=========================================="

# Check Python
echo ""
echo "Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 not found. Please install Python 3.8+${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo -e "  ${GREEN}$PYTHON_VERSION${NC}"

# Create directories
echo ""
echo "Creating directories..."
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/data"

# Try to create virtual environment
VENV_DIR="$PROJECT_DIR/venv"
USE_VENV=false

if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "Creating virtual environment..."
    if python3 -m venv "$VENV_DIR" 2>/dev/null; then
        USE_VENV=true
        echo -e "  ${GREEN}Virtual environment created${NC}"
    else
        echo -e "  ${YELLOW}Could not create venv (python3-venv may not be installed)${NC}"
        echo "  Will install packages globally..."
        echo ""
        echo "  To use a virtual environment instead, run:"
        echo "    sudo apt install python3.12-venv"
        echo "    rm -rf venv && bash scripts/install.sh"
    fi
else
    USE_VENV=true
    echo "Using existing virtual environment..."
fi

# Install pip packages
echo ""
echo "Installing Python dependencies..."

if [ "$USE_VENV" = true ]; then
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install flask requests anthropic supervisor
else
    # Install globally (for systems without venv)
    pip3 install --user --break-system-packages flask requests anthropic supervisor 2>/dev/null || \
    pip3 install --user flask requests anthropic supervisor 2>/dev/null || \
    pip3 install flask requests anthropic supervisor
fi

# Verify supervisor installed
echo ""
echo "Verifying installation..."

if [ "$USE_VENV" = true ]; then
    if command -v supervisord &> /dev/null; then
        echo -e "  ${GREEN}supervisor installed${NC}"
    else
        echo -e "  ${RED}supervisor not found in PATH${NC}"
    fi
else
    # Check in user local bin
    if [ -f "$HOME/.local/bin/supervisord" ]; then
        echo -e "  ${GREEN}supervisor installed in ~/.local/bin${NC}"
        export PATH="$HOME/.local/bin:$PATH"
    fi
fi

# Initialize database
echo ""
echo "Initializing database..."
cd "$PROJECT_DIR"
python3 -c "from src.database import Database; db = Database(); print(f'  Database ready at {db.db_path}')"

echo ""
echo -e "${GREEN}=========================================="
echo "  Installation Complete!"
echo "==========================================${NC}"
echo ""

if [ "$USE_VENV" = true ]; then
    echo "To run the bot:"
    echo ""
    echo "1. Activate virtual environment:"
    echo -e "   ${YELLOW}source venv/bin/activate${NC}"
    echo ""
else
    echo "Make sure ~/.local/bin is in your PATH:"
    echo -e "   ${YELLOW}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
    echo ""
fi

echo "2. Make sure Ollama is running (on Windows host):"
echo -e "   ${YELLOW}ollama serve${NC}"
echo ""
echo "3. Start the bot:"
echo -e "   ${YELLOW}bash scripts/start.sh${NC}"
echo ""
echo "4. Access dashboard:"
echo -e "   ${YELLOW}http://localhost:8080${NC}"
echo ""
echo "Note: Uses local LLM (qwen2.5:14b) via Ollama - no API key needed!"
echo ""
