#!/bin/bash
# Restart the crypto trading bot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "  Crypto Trading Bot - Restarting"
echo "=========================================="

"$SCRIPT_DIR/stop.sh"
echo ""
sleep 2
"$SCRIPT_DIR/start.sh"
