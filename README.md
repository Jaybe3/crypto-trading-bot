# Self-Learning Crypto Trading Bot

An autonomous cryptocurrency paper trading bot that learns from every trade and continuously improves its decision-making through LLM-powered analysis.

## Features

- **45-Coin Universe** across 3 risk tiers (Blue Chips, Established, High Volatility)
- **LLM-Powered Decisions** using local Ollama (qwen2.5-coder:7b) - no API key needed!
- **Self-Learning System** - extracts lessons from every trade
- **Rule Evolution** - high-confidence patterns become trading rules
- **Real-Time Dashboard** with live market data
- **Risk Management** - tier-specific position limits and stop-losses
- **Volatility Adjustment** - dynamic position sizing based on market conditions
- **Volume Filtering** - automatically skips illiquid coins
- **24/7 Deployment** - supervisor-managed with auto-restart
- **Performance Monitoring** - metrics, alerts, and Prometheus endpoint

## Documentation

| Audience | Start Here |
|----------|------------|
| Investors/Advisors | [docs/business/EXECUTIVE-SUMMARY.md](docs/business/EXECUTIVE-SUMMARY.md) |
| Technical Leaders | [docs/architecture/SYSTEM-OVERVIEW.md](docs/architecture/SYSTEM-OVERVIEW.md) |
| Developers | [docs/development/WORKFLOW.md](docs/development/WORKFLOW.md) |
| Operators | [docs/operations/RUNBOOK.md](docs/operations/RUNBOOK.md) |

For Claude Code: Start with [.clinerules](.clinerules)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      TRADING BOT                            │
├─────────────────────────────────────────────────────────────┤
│  Market Data (CoinGecko) → LLM Decision → Trade Execution   │
│            ↓                    ↑              ↓            │
│      Risk Manager ←───── Learnings ←──── Trade Analysis     │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) with qwen2.5-coder:7b model (runs locally, no API key needed)

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/crypto-trading-bot.git
cd crypto-trading-bot

# Run the install script (creates venv, installs dependencies)
bash scripts/install.sh

# Or manually:
pip install flask requests supervisor
mkdir -p data logs
```

### Setup Ollama (One-time)

```bash
# Install Ollama from https://ollama.ai/
# Then pull the model:
ollama pull qwen2.5-coder:7b

# Start Ollama server (keep running)
ollama serve
```

### Running

```bash
# Start everything (trading bot + dashboard)
bash scripts/start.sh

# Access dashboard at http://localhost:8080

# Check status
bash scripts/status.sh

# View performance metrics
bash scripts/performance.sh

# Stop
bash scripts/stop.sh
```

### Configuration (Optional)

```bash
# For WSL2: set Ollama host to Windows gateway IP
export OLLAMA_HOST=$(ip route show default | awk '{print $3}')

# Trading settings
export LOOP_INTERVAL=30        # Trading cycle interval (seconds)
export MIN_CONFIDENCE=0.6      # Minimum confidence for trades
```

## Project Structure

```
crypto-trading-bot/
├── src/
│   ├── main.py              # Main trading loop
│   ├── database.py          # SQLite operations
│   ├── market_data.py       # CoinGecko API integration
│   ├── llm_interface.py     # Ollama LLM integration
│   ├── risk_manager.py      # Position sizing & limits
│   ├── trading_engine.py    # Trade execution
│   ├── learning_system.py   # Learning & rule creation
│   ├── coin_config.py       # 45-coin tier configuration
│   ├── dashboard.py         # Web dashboard (Flask)
│   └── daily_summary.py     # Report generation
├── docs/
│   ├── PRD.md               # Product requirements
│   ├── TASKS.md             # Task tracking
│   └── DEVELOPMENT.md       # Development guide
├── tests/                   # Unit tests
├── data/                    # Database & reports (gitignored)
└── logs/                    # Log files (gitignored)
```

## Coin Tiers

| Tier | Name | Coins | Max Position | Stop-Loss |
|------|------|-------|--------------|-----------|
| 1 | Blue Chips | 5 (BTC, ETH, BNB, XRP, SOL) | 25% | 3% |
| 2 | Established | 15 (ADA, DOGE, AVAX, DOT...) | 15% | 5% |
| 3 | High Volatility | 25 (PEPE, FLOKI, BONK...) | 10% | 7% |

## Risk Management

- **Position Limits**: Tier-specific maximum position sizes
- **Stop-Loss**: Automatic exit on tier-specific loss threshold
- **Take-Profit**: $1 profit target per trade (consistent)
- **Volume Filter**: Skips coins below minimum 24h volume
- **Exposure Limit**: Maximum 10% of balance in positions

## Learning System

1. **Trade Closes** → LLM analyzes outcome
2. **Learning Created** → Pattern and lesson extracted
3. **High Confidence** → Learning becomes a rule
4. **Rule Testing** → Validated over 10 trades
5. **Promotion/Rejection** → Rule becomes active or rejected

## Dashboard

Access at `http://localhost:8080` after starting:

- Live market data for all 44 coins with tier badges
- Account balance and P&L tracking
- Open and closed trades
- Learnings with confidence levels
- Active and testing rules

## Commands

```bash
# Run trading bot
python3 src/main.py

# Run dashboard only
python3 src/dashboard.py

# Generate daily summary
python3 src/daily_summary.py

# Test coin configuration
python3 src/coin_config.py

# Fetch market data once
python3 src/market_data.py
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_HOST` | Ollama server host (for WSL2) | 172.27.144.1 |
| `LOOP_INTERVAL` | Cycle interval (seconds) | 30 |
| `MIN_CONFIDENCE` | Min trade confidence | 0.6 |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Main dashboard |
| `GET /api/status` | Account and trade status |
| `GET /api/metrics` | Performance metrics (JSON) |
| `GET /metrics` | Prometheus-compatible metrics |
| `GET /api/alerts` | Active monitoring alerts |

## Development Status

- **Phase 1**: Foundation ✅ Complete
- **Phase 1.5**: Production Scaling ✅ Complete
  - [x] TASK-014: Multi-Tier Coin Universe (45 coins)
  - [x] TASK-015: Volatility-Based Risk Adjustment
  - [x] TASK-016: 24/7 Deployment Setup
  - [x] TASK-017: Performance Monitoring
- **Phase 2**: Real Money Trading (Out of Scope)

## Disclaimer

⚠️ **This is a paper trading bot for educational purposes only.**

- No real money is involved
- Past performance does not guarantee future results
- Cryptocurrency trading involves significant risk
- Always do your own research

## License

Private repository - All rights reserved.
