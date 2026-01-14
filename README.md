# Self-Learning Crypto Trading Bot

An autonomous cryptocurrency paper trading bot that learns from every trade and continuously improves its decision-making through LLM-powered analysis.

## Features

- **45-Coin Universe** across 3 risk tiers (Blue Chips, Established, High Volatility)
- **LLM-Powered Decisions** using Claude for market analysis
- **Self-Learning System** - extracts lessons from every trade
- **Rule Evolution** - high-confidence patterns become trading rules
- **Real-Time Dashboard** with live market data
- **Risk Management** - tier-specific position limits and stop-losses
- **Volume Filtering** - automatically skips illiquid coins

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
- Anthropic API key (Claude)

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/crypto-trading-bot.git
cd crypto-trading-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install flask requests anthropic

# Create required directories
mkdir -p data logs
```

### Configuration

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY="your-api-key-here"

# Optional: customize settings
export LOOP_INTERVAL=30        # Trading cycle interval (seconds)
export MIN_CONFIDENCE=0.6      # Minimum confidence for trades
```

### Running

```bash
# Start the trading bot
python3 src/main.py

# In a separate terminal, start the dashboard
python3 src/dashboard.py

# Access dashboard at http://localhost:8080
```

## Project Structure

```
crypto-trading-bot/
├── src/
│   ├── main.py              # Main trading loop
│   ├── database.py          # SQLite operations
│   ├── market_data.py       # CoinGecko API integration
│   ├── llm_interface.py     # Claude API integration
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
| `ANTHROPIC_API_KEY` | Claude API key | Required |
| `LOOP_INTERVAL` | Cycle interval (seconds) | 30 |
| `MIN_CONFIDENCE` | Min trade confidence | 0.6 |

## Development Status

- **Phase 1**: Foundation ✅ Complete
- **Phase 1.5**: Production Scaling 🔄 In Progress
  - [x] TASK-014: Multi-Tier Coin Universe (45 coins)
  - [ ] TASK-015: Volatility-Based Risk Adjustment
  - [ ] TASK-016: 24/7 Deployment Setup
  - [ ] TASK-017: Performance Monitoring
- **Phase 2**: Real Money Trading (Out of Scope)

## Disclaimer

⚠️ **This is a paper trading bot for educational purposes only.**

- No real money is involved
- Past performance does not guarantee future results
- Cryptocurrency trading involves significant risk
- Always do your own research

## License

Private repository - All rights reserved.
