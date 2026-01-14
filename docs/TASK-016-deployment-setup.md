# TASK-016: 24/7 Deployment Setup

## Overview
Configure the trading bot for continuous 24/7 operation with automatic restart on crash, log management, and easy monitoring. Supports both WSL2 and native Linux environments.

## Current State
- Bot runs manually via `python3 src/main.py`
- Dashboard runs manually via `python3 src/dashboard.py`
- No automatic restart on crash
- Logs go to console only
- No unified start/stop mechanism

## Target State
- Single command to start/stop entire system
- Automatic restart on crash (within seconds)
- Log files with rotation (prevent disk fill)
- Health monitoring
- Clean shutdown handling
- Works in WSL2 environment

---

## Deployment Options

### Option A: Supervisor (Recommended for WSL2)
Supervisor is a process manager that works well in WSL2 without requiring systemd.

### Option B: systemd (Native Linux / WSL2 with systemd)
For systems with systemd enabled.

### Option C: Screen/tmux (Simple)
For quick deployments or testing.

---

## Implementation

### 1. Directory Structure

```
crypto-trading-bot/
├── scripts/
│   ├── start.sh          # Start all services
│   ├── stop.sh           # Stop all services
│   ├── status.sh         # Check status
│   ├── restart.sh        # Restart all services
│   └── install.sh        # Install dependencies
├── config/
│   ├── supervisor.conf   # Supervisor configuration
│   └── logrotate.conf    # Log rotation config
├── logs/                 # Log files (gitignored)
│   ├── trading_bot.log
│   ├── dashboard.log
│   └── supervisor.log
└── ...
```

### 2. Supervisor Configuration

**`config/supervisor.conf`**
```ini
[supervisord]
logfile=%(here)s/../logs/supervisor.log
logfile_maxbytes=10MB
logfile_backups=3
loglevel=info
pidfile=%(here)s/../logs/supervisord.pid
nodaemon=false
directory=%(here)s/..

[unix_http_server]
file=%(here)s/../logs/supervisor.sock

[supervisorctl]
serverurl=unix://%(here)s/../logs/supervisor.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[program:trading_bot]
command=python3 -u src/main.py
directory=%(here)s/..
autostart=true
autorestart=true
startretries=10
startsecs=5
stopwaitsecs=10
stdout_logfile=%(here)s/../logs/trading_bot.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
stderr_redirect=true
environment=PYTHONUNBUFFERED="1"

[program:dashboard]
command=python3 -u src/dashboard.py
directory=%(here)s/..
autostart=true
autorestart=true
startretries=5
startsecs=3
stopwaitsecs=5
stdout_logfile=%(here)s/../logs/dashboard.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=3
stderr_redirect=true
environment=PYTHONUNBUFFERED="1"

[group:cryptobot]
programs=trading_bot,dashboard
priority=999
```

### 3. Management Scripts

**`scripts/start.sh`**
```bash
#!/bin/bash
# Start the crypto trading bot

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_DIR/config/supervisor.conf"
LOG_DIR="$PROJECT_DIR/logs"

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

# Check if already running
if [ -f "$LOG_DIR/supervisord.pid" ]; then
    PID=$(cat "$LOG_DIR/supervisord.pid")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}Bot is already running (PID: $PID)${NC}"
        echo "Use './scripts/status.sh' to check status"
        echo "Use './scripts/restart.sh' to restart"
        exit 0
    fi
fi

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}ERROR: ANTHROPIC_API_KEY not set${NC}"
    echo "Run: export ANTHROPIC_API_KEY='your-key-here'"
    exit 1
fi

# Start supervisor
echo "Starting supervisor..."
cd "$PROJECT_DIR"
supervisord -c "$CONFIG_FILE"

# Wait for startup
sleep 2

# Check status
if [ -f "$LOG_DIR/supervisord.pid" ]; then
    echo -e "${GREEN}Bot started successfully!${NC}"
    echo ""
    echo "Dashboard: http://localhost:8080"
    echo "Logs: $LOG_DIR/"
    echo ""
    echo "Commands:"
    echo "  ./scripts/status.sh   - Check status"
    echo "  ./scripts/stop.sh     - Stop bot"
    echo "  ./scripts/restart.sh  - Restart bot"
    echo "  tail -f logs/trading_bot.log - Watch logs"
else
    echo -e "${RED}Failed to start bot${NC}"
    exit 1
fi
```

**`scripts/stop.sh`**
```bash
#!/bin/bash
# Stop the crypto trading bot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_DIR/config/supervisor.conf"
LOG_DIR="$PROJECT_DIR/logs"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "  Crypto Trading Bot - Stopping"
echo "=========================================="

if [ ! -f "$LOG_DIR/supervisord.pid" ]; then
    echo -e "${YELLOW}Bot is not running${NC}"
    exit 0
fi

PID=$(cat "$LOG_DIR/supervisord.pid")
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${YELLOW}Bot is not running (stale PID file)${NC}"
    rm -f "$LOG_DIR/supervisord.pid"
    exit 0
fi

echo "Stopping supervisor (PID: $PID)..."
supervisorctl -c "$CONFIG_FILE" stop all
supervisorctl -c "$CONFIG_FILE" shutdown

# Wait for shutdown
sleep 2

if ps -p "$PID" > /dev/null 2>&1; then
    echo "Force killing..."
    kill -9 "$PID" 2>/dev/null
fi

rm -f "$LOG_DIR/supervisord.pid" "$LOG_DIR/supervisor.sock"

echo -e "${GREEN}Bot stopped${NC}"
```

**`scripts/status.sh`**
```bash
#!/bin/bash
# Check status of the crypto trading bot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_DIR/config/supervisor.conf"
LOG_DIR="$PROJECT_DIR/logs"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "  Crypto Trading Bot - Status"
echo "=========================================="

# Check if supervisor is running
if [ ! -f "$LOG_DIR/supervisord.pid" ]; then
    echo -e "${RED}Status: NOT RUNNING${NC}"
    exit 1
fi

PID=$(cat "$LOG_DIR/supervisord.pid")
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${RED}Status: NOT RUNNING (stale PID)${NC}"
    exit 1
fi

echo -e "${GREEN}Supervisor running (PID: $PID)${NC}"
echo ""

# Get detailed status
supervisorctl -c "$CONFIG_FILE" status

echo ""
echo "Dashboard: http://localhost:8080"
echo ""

# Show recent activity
echo "Recent log entries (last 5):"
echo "---"
tail -5 "$LOG_DIR/trading_bot.log" 2>/dev/null || echo "No logs yet"
```

**`scripts/restart.sh`**
```bash
#!/bin/bash
# Restart the crypto trading bot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Restarting crypto trading bot..."
"$SCRIPT_DIR/stop.sh"
sleep 2
"$SCRIPT_DIR/start.sh"
```

**`scripts/install.sh`**
```bash
#!/bin/bash
# Install dependencies for the crypto trading bot

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "  Crypto Trading Bot - Installation"
echo "=========================================="

# Check Python
echo "Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found. Please install Python 3.8+"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "  $PYTHON_VERSION"

# Install pip packages
echo ""
echo "Installing Python dependencies..."
pip3 install --user flask requests anthropic supervisor

# Create directories
echo ""
echo "Creating directories..."
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/config"
mkdir -p "$PROJECT_DIR/scripts"

# Make scripts executable
echo "Setting permissions..."
chmod +x "$PROJECT_DIR/scripts/"*.sh 2>/dev/null || true

# Initialize database
echo ""
echo "Initializing database..."
cd "$PROJECT_DIR"
python3 -c "from src.database import Database; db = Database(); print(f'Database ready at {db.db_path}')"

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Set your API key:"
echo "   export ANTHROPIC_API_KEY='your-key-here'"
echo ""
echo "2. Start the bot:"
echo "   ./scripts/start.sh"
echo ""
echo "3. Access dashboard:"
echo "   http://localhost:8080"
```

### 4. Log Rotation Configuration

**`config/logrotate.conf`** (optional, for systems with logrotate)
```
/path/to/crypto-trading-bot/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    maxsize 50M
}
```

### 5. Health Check Script

**`scripts/health.sh`**
```bash
#!/bin/bash
# Health check for monitoring systems

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
CONFIG_FILE="$PROJECT_DIR/config/supervisor.conf"

# Check supervisor
if [ ! -f "$LOG_DIR/supervisord.pid" ]; then
    echo "CRITICAL: Supervisor not running"
    exit 2
fi

PID=$(cat "$LOG_DIR/supervisord.pid")
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "CRITICAL: Supervisor not running"
    exit 2
fi

# Check individual processes
TRADING_STATUS=$(supervisorctl -c "$CONFIG_FILE" status trading_bot 2>/dev/null | awk '{print $2}')
DASHBOARD_STATUS=$(supervisorctl -c "$CONFIG_FILE" status dashboard 2>/dev/null | awk '{print $2}')

if [ "$TRADING_STATUS" != "RUNNING" ]; then
    echo "WARNING: Trading bot not running ($TRADING_STATUS)"
    exit 1
fi

if [ "$DASHBOARD_STATUS" != "RUNNING" ]; then
    echo "WARNING: Dashboard not running ($DASHBOARD_STATUS)"
    exit 1
fi

# Check dashboard is responding
if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 | grep -q "200"; then
    echo "WARNING: Dashboard not responding"
    exit 1
fi

echo "OK: All services running"
exit 0
```

---

## Usage Guide

### Starting the Bot
```bash
# First time setup
./scripts/install.sh

# Set API key (add to ~/.bashrc for persistence)
export ANTHROPIC_API_KEY="your-key-here"

# Start
./scripts/start.sh
```

### Monitoring
```bash
# Check status
./scripts/status.sh

# Watch live logs
tail -f logs/trading_bot.log

# Watch specific events
grep "TRADE" logs/trading_bot.log | tail -20
```

### Stopping
```bash
./scripts/stop.sh
```

### Restarting
```bash
./scripts/restart.sh
```

### Viewing Logs
```bash
# Trading bot logs
tail -100 logs/trading_bot.log

# Dashboard logs
tail -100 logs/dashboard.log

# Supervisor logs
tail -50 logs/supervisor.log

# Follow logs in real-time
tail -f logs/trading_bot.log
```

---

## Auto-Start on Boot (Optional)

### For WSL2
Add to `~/.bashrc` or `~/.profile`:
```bash
# Auto-start trading bot
if [ -z "$(pgrep -f 'supervisord.*crypto')" ]; then
    cd /mnt/c/documents/crypto-trading-bot
    ./scripts/start.sh > /dev/null 2>&1
fi
```

### For Native Linux with systemd
Create `/etc/systemd/system/cryptobot.service`:
```ini
[Unit]
Description=Crypto Trading Bot
After=network.target

[Service]
Type=forking
User=your_username
WorkingDirectory=/path/to/crypto-trading-bot
Environment="ANTHROPIC_API_KEY=your-key-here"
ExecStart=/path/to/crypto-trading-bot/scripts/start.sh
ExecStop=/path/to/crypto-trading-bot/scripts/stop.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cryptobot
sudo systemctl start cryptobot
```

---

## Crash Recovery

Supervisor automatically restarts crashed processes:
- **Trading Bot**: Restarts within 5 seconds, up to 10 retries
- **Dashboard**: Restarts within 3 seconds, up to 5 retries

If a process keeps crashing, check logs:
```bash
tail -100 logs/trading_bot.log
```

Manual restart:
```bash
supervisorctl -c config/supervisor.conf restart trading_bot
```

---

## Acceptance Criteria

- [ ] `./scripts/install.sh` installs all dependencies
- [ ] `./scripts/start.sh` starts bot and dashboard
- [ ] `./scripts/stop.sh` cleanly stops everything
- [ ] `./scripts/status.sh` shows running status
- [ ] Automatic restart on crash (test with `kill -9`)
- [ ] Logs written to files with rotation
- [ ] Dashboard accessible at http://localhost:8080
- [ ] Works in WSL2 environment

---

## Files to Create

| File | Description |
|------|-------------|
| `config/supervisor.conf` | Supervisor configuration |
| `scripts/install.sh` | Install dependencies |
| `scripts/start.sh` | Start all services |
| `scripts/stop.sh` | Stop all services |
| `scripts/status.sh` | Check status |
| `scripts/restart.sh` | Restart services |
| `scripts/health.sh` | Health check for monitoring |

---

## Testing Plan

1. **Install**: Run `./scripts/install.sh`
2. **Start**: Run `./scripts/start.sh` - verify dashboard accessible
3. **Status**: Run `./scripts/status.sh` - verify shows running
4. **Crash Recovery**: Kill trading bot, verify auto-restart
5. **Stop**: Run `./scripts/stop.sh` - verify clean shutdown
6. **Logs**: Verify logs are being written to files
