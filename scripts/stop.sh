#!/bin/bash
# Stop the crypto trading bot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_DIR/config/supervisor.conf"
LOG_DIR="$PROJECT_DIR/logs"
VENV_DIR="$PROJECT_DIR/venv"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Add user local bin to PATH
export PATH="$HOME/.local/bin:$PATH"

# Activate virtual environment if it exists
if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
fi

echo "=========================================="
echo "  Crypto Trading Bot - Stopping"
echo "=========================================="

PID_FILE="/tmp/cryptobot-supervisord.pid"
SOCK_FILE="/tmp/cryptobot-supervisor.sock"

if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}Bot is not running${NC}"
    exit 0
fi

PID=$(cat "$PID_FILE")
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${YELLOW}Bot is not running (stale PID file)${NC}"
    rm -f "$PID_FILE" "$SOCK_FILE"
    exit 0
fi

echo ""
echo "Stopping services (PID: $PID)..."

# Stop all programs first
supervisorctl -c "$CONFIG_FILE" stop all 2>/dev/null || true

# Shutdown supervisor
supervisorctl -c "$CONFIG_FILE" shutdown 2>/dev/null || true

# Wait for shutdown
sleep 2

# Force kill if still running
if ps -p "$PID" > /dev/null 2>&1; then
    echo "Force killing supervisor..."
    kill -9 "$PID" 2>/dev/null || true
    sleep 1
fi

# Cleanup
rm -f "$PID_FILE" "$SOCK_FILE"

echo ""
echo -e "${GREEN}Bot stopped${NC}"
