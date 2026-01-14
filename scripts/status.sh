#!/bin/bash
# Check status of the crypto trading bot

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

# Add user local bin to PATH
export PATH="$HOME/.local/bin:$PATH"

# Activate virtual environment if it exists
if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
fi

echo "=========================================="
echo "  Crypto Trading Bot - Status"
echo "=========================================="

PID_FILE="/tmp/cryptobot-supervisord.pid"
SOCK_FILE="/tmp/cryptobot-supervisor.sock"

# Check if supervisor is running
if [ ! -f "$PID_FILE" ]; then
    echo ""
    echo -e "Status: ${RED}NOT RUNNING${NC}"
    echo ""
    echo "Start with: bash scripts/start.sh"
    exit 1
fi

PID=$(cat "$PID_FILE")
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo ""
    echo -e "Status: ${RED}NOT RUNNING${NC} (stale PID file)"
    echo ""
    echo "Start with: bash scripts/start.sh"
    rm -f "$PID_FILE" "$SOCK_FILE"
    exit 1
fi

echo ""
echo -e "Supervisor: ${GREEN}RUNNING${NC} (PID: $PID)"
echo ""

# Get detailed status
echo "Services:"
echo "---------"
supervisorctl -c "$CONFIG_FILE" status

echo ""
echo "Dashboard: http://localhost:8080"
echo ""

# Show account state
echo "Account State:"
echo "--------------"
cd "$PROJECT_DIR"
python3 -c "
from src.database import Database
db = Database()
state = db.get_account_state()
print(f\"  Balance: \${state.get('balance', 0):.2f}\")
print(f\"  In Positions: \${state.get('in_positions', 0):.2f}\")
print(f\"  Total P&L: \${state.get('total_pnl', 0):.2f}\")
print(f\"  Trades Today: {state.get('trade_count_today', 0)}\")
" 2>/dev/null || echo "  (unable to read database)"

echo ""

# Show recent log entries
echo "Recent Activity (last 5 lines):"
echo "--------------------------------"
tail -5 "$LOG_DIR/trading_bot.log" 2>/dev/null || echo "No logs yet"
