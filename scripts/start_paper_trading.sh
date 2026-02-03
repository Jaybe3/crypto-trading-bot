#!/bin/bash
# Paper Trading Startup Script
# Usage: ./scripts/start_paper_trading.sh [--fresh]
#
# Options:
#   --fresh    Start with fresh database (backup current first)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
VALIDATION_DIR="$LOG_DIR/validation"
DATA_DIR="$PROJECT_DIR/data"
DASHBOARD_PORT=8080

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Paper Trading Validation Run${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Check for --fresh flag
FRESH_START=false
if [[ "$1" == "--fresh" ]]; then
    FRESH_START=true
    echo -e "${YELLOW}Fresh start requested - will backup and reset database${NC}"
fi

# Pre-flight checks
echo -e "${CYAN}Running pre-flight checks...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: python3 not found${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Python3 found"

# Check Ollama
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}WARNING: ollama not found in PATH${NC}"
else
    if ollama list 2>/dev/null | grep -q "qwen2.5:14b"; then
        echo -e "  ${GREEN}✓${NC} Ollama with qwen2.5:14b available"
    else
        echo -e "${YELLOW}WARNING: qwen2.5:14b model not found${NC}"
    fi
fi

# Check directories
mkdir -p "$LOG_DIR" "$VALIDATION_DIR" "$DATA_DIR"
echo -e "  ${GREEN}✓${NC} Directories exist"

# Check disk space (need at least 1GB free)
AVAILABLE_KB=$(df "$PROJECT_DIR" | awk 'NR==2 {print $4}')
if [[ $AVAILABLE_KB -lt 1000000 ]]; then
    echo -e "${RED}ERROR: Less than 1GB disk space available${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Disk space OK ($(($AVAILABLE_KB / 1024))MB free)"

# Fresh start - backup and reset
if [[ "$FRESH_START" == true ]]; then
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    if [[ -f "$DATA_DIR/trading_bot.db" ]]; then
        echo -e "${YELLOW}Backing up database to trading_bot.db.backup_$TIMESTAMP${NC}"
        cp "$DATA_DIR/trading_bot.db" "$DATA_DIR/trading_bot.db.backup_$TIMESTAMP"
        rm "$DATA_DIR/trading_bot.db"
        echo -e "  ${GREEN}✓${NC} Database reset"
    fi
    if [[ -f "$DATA_DIR/sniper_state.json" ]]; then
        cp "$DATA_DIR/sniper_state.json" "$DATA_DIR/sniper_state.json.backup_$TIMESTAMP"
        rm "$DATA_DIR/sniper_state.json"
        echo -e "  ${GREEN}✓${NC} Sniper state reset"
    fi
fi

# Create today's validation log
TODAY=$(date +%Y-%m-%d)
DAY_NUM=0
if [[ -f "$VALIDATION_DIR/.run_start" ]]; then
    START_DATE=$(cat "$VALIDATION_DIR/.run_start")
    DAY_NUM=$(( ($(date +%s) - $(date -d "$START_DATE" +%s)) / 86400 ))
else
    echo "$TODAY" > "$VALIDATION_DIR/.run_start"
fi

LOG_FILE="$VALIDATION_DIR/day-$DAY_NUM.md"
if [[ ! -f "$LOG_FILE" ]]; then
    echo -e "${CYAN}Creating validation log: day-$DAY_NUM.md${NC}"
    cat > "$LOG_FILE" << EOF
# Day $DAY_NUM Validation Log

**Date:** $TODAY
**Reviewer:** [Name]
**Decision:** CONTINUE / INVESTIGATE / PAUSE / ABORT

## System Health
- Uptime: ___h ___m
- Crashes: ___
- Feed reconnects: ___
- Errors: ___

## Trading Activity
- Trades (24h): ___
- Trades (total): ___
- Conditions generated: ___

## Performance
- Win rate (24h): ___%
- Win rate (total): ___%
- P&L (24h): \$___
- P&L (total): \$___
- Balance: \$___

## Learning
- Reflections: ___
- Insights: ___
- Adaptations: ___
- Blacklisted coins: ___

## Effectiveness
- Highly Effective: ___
- Effective: ___
- Neutral: ___
- Ineffective: ___
- Harmful: ___

## Notes
[Any observations, anomalies, or concerns]

## Actions Taken
[Any interventions or overrides]
EOF
fi

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}Starting Paper Trading System${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "Dashboard: ${CYAN}http://localhost:$DASHBOARD_PORT${NC}"
echo -e "Validation Day: ${CYAN}$DAY_NUM${NC}"
echo -e "Log File: ${CYAN}$LOG_FILE${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Start the system
cd "$PROJECT_DIR"
python3 src/main_v2.py --dashboard --port $DASHBOARD_PORT
