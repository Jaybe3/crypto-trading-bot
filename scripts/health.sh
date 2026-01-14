#!/bin/bash
# Health check for monitoring systems
# Returns exit codes: 0=OK, 1=WARNING, 2=CRITICAL

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
CONFIG_FILE="$PROJECT_DIR/config/supervisor.conf"

# Check supervisor is running
if [ ! -f "$LOG_DIR/supervisord.pid" ]; then
    echo "CRITICAL: Supervisor not running"
    exit 2
fi

PID=$(cat "$LOG_DIR/supervisord.pid")
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "CRITICAL: Supervisor not running (stale PID)"
    exit 2
fi

# Check individual processes
TRADING_STATUS=$(supervisorctl -c "$CONFIG_FILE" status trading_bot 2>/dev/null | awk '{print $2}')
DASHBOARD_STATUS=$(supervisorctl -c "$CONFIG_FILE" status dashboard 2>/dev/null | awk '{print $2}')

if [ "$TRADING_STATUS" != "RUNNING" ]; then
    echo "WARNING: Trading bot status: $TRADING_STATUS"
    exit 1
fi

if [ "$DASHBOARD_STATUS" != "RUNNING" ]; then
    echo "WARNING: Dashboard status: $DASHBOARD_STATUS"
    exit 1
fi

# Check dashboard is responding
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 2>/dev/null || echo "000")
if [ "$HTTP_CODE" != "200" ]; then
    echo "WARNING: Dashboard not responding (HTTP $HTTP_CODE)"
    exit 1
fi

# Check log file is being updated (within last 5 minutes)
if [ -f "$LOG_DIR/trading_bot.log" ]; then
    LOG_AGE=$(( $(date +%s) - $(stat -c %Y "$LOG_DIR/trading_bot.log" 2>/dev/null || echo 0) ))
    if [ "$LOG_AGE" -gt 300 ]; then
        echo "WARNING: No log activity for ${LOG_AGE}s"
        exit 1
    fi
fi

echo "OK: All services running"
exit 0
