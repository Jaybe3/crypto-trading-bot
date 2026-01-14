#!/bin/bash
# Start the crypto trading bot

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_DIR/config/supervisor.conf"
LOG_DIR="$PROJECT_DIR/logs"
VENV_DIR="$PROJECT_DIR/venv"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "  Crypto Trading Bot - Starting"
echo "=========================================="

# Create logs directory
mkdir -p "$LOG_DIR"

# Add user local bin to PATH (for pip --user installs)
export PATH="$HOME/.local/bin:$PATH"

# Activate virtual environment if it exists
if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
    echo "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
fi

# Check if already running
if [ -f "$LOG_DIR/supervisord.pid" ]; then
    PID=$(cat "$LOG_DIR/supervisord.pid")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}Bot is already running (PID: $PID)${NC}"
        echo ""
        echo "Use 'bash scripts/status.sh' to check status"
        echo "Use 'bash scripts/restart.sh' to restart"
        exit 0
    else
        # Stale PID file
        rm -f "$LOG_DIR/supervisord.pid" "$LOG_DIR/supervisor.sock"
    fi
fi

# Check Ollama is reachable
OLLAMA_HOST="${OLLAMA_HOST:-172.27.144.1}"
echo "Checking Ollama at $OLLAMA_HOST:11434..."
if curl -s --connect-timeout 3 "http://$OLLAMA_HOST:11434/api/tags" > /dev/null 2>&1; then
    echo -e "  ${GREEN}Ollama reachable${NC}"
else
    echo -e "${YELLOW}WARNING: Cannot reach Ollama at $OLLAMA_HOST:11434${NC}"
    echo ""
    echo "Make sure Ollama is running on your Windows host:"
    echo "  ollama serve"
    echo ""
    echo "If using WSL2, you may need to set OLLAMA_HOST:"
    echo "  export OLLAMA_HOST=\$(ip route show default | awk '{print \$3}')"
    echo ""
    echo "Continuing anyway - bot will retry connections..."
fi

# Check supervisor is installed
if ! command -v supervisord &> /dev/null; then
    echo -e "${RED}ERROR: supervisor not installed${NC}"
    echo "Run: bash scripts/install.sh"
    exit 1
fi

# Start supervisor
echo ""
echo "Starting supervisor..."
cd "$PROJECT_DIR"
supervisord -c "$CONFIG_FILE"

# Wait for startup
sleep 3

# Check status
if [ -f "$LOG_DIR/supervisord.pid" ]; then
    PID=$(cat "$LOG_DIR/supervisord.pid")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}=========================================="
        echo "  Bot Started Successfully!"
        echo "==========================================${NC}"
        echo ""
        echo "Dashboard: http://localhost:8080"
        echo "Logs:      $LOG_DIR/"
        echo ""
        echo "Commands:"
        echo "  bash scripts/status.sh    - Check status"
        echo "  bash scripts/stop.sh      - Stop bot"
        echo "  bash scripts/restart.sh   - Restart bot"
        echo "  tail -f logs/trading_bot.log - Watch logs"
        echo ""

        # Show initial status
        supervisorctl -c "$CONFIG_FILE" status
    else
        echo -e "${RED}Failed to start bot${NC}"
        echo "Check logs: tail -50 $LOG_DIR/supervisor.log"
        exit 1
    fi
else
    echo -e "${RED}Failed to start bot${NC}"
    exit 1
fi
