# Self-Learning Crypto Trading Bot

An autonomous cryptocurrency paper trading bot with a complete learning loop that automatically improves its trading through LLM-powered analysis and adaptation.

**Current Status:** Phase 2 Deployed (February 3, 2026)

## Features

### Trading Infrastructure
- **Real-Time WebSocket Feed** - Sub-millisecond price updates from Bybit
- **Condition-Based Execution** - LLM generates conditions, Sniper executes instantly
- **20-Coin Universe** across 3 risk tiers (Blue Chips, Established, High Volatility)
- **24/7 Deployment** - supervisor-managed with auto-restart

### Learning System
- **Knowledge Brain** - Tracks per-coin performance, patterns, and rules
- **Quick Update** - Instant learning after every trade (<10ms)
- **Deep Reflection** - Hourly LLM analysis of trading patterns
- **Automatic Adaptation** - Blacklists losers, favors winners, creates rules
- **Effectiveness Monitoring** - Tracks if adaptations actually help

### Dashboard
- **Live Market Data** - Real-time prices for all 20 coins
- **Position Monitoring** - Open positions with P&L
- **Knowledge View** - Coin scores, patterns, rules
- **Performance Metrics** - Win rate, profit factor, Sharpe ratio

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AUTONOMOUS TRADING LOOP                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │  MarketFeed  │───►│  Strategist  │───►│    Sniper    │                   │
│  │  (WebSocket) │    │    (LLM)     │    │  (Executor)  │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
│         │                   ▲                    │                           │
│         │                   │                    ▼                           │
│         │           ┌──────────────┐    ┌──────────────┐                    │
│         │           │  Knowledge   │◄───│   Journal    │                    │
│         │           │    Brain     │    │  (Records)   │                    │
│         │           └──────────────┘    └──────────────┘                    │
│         │                   ▲                    │                           │
│         │                   │                    ▼                           │
│         │           ┌──────────────┐    ┌──────────────┐                    │
│         └──────────►│  Reflection  │◄───│ Quick Update │                    │
│                     │   (Hourly)   │    │  (Instant)   │                    │
│                     └──────────────┘    └──────────────┘                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Documentation

| Audience | Start Here |
|----------|------------|
| Investors/Advisors | [docs/business/EXECUTIVE-SUMMARY.md](docs/business/EXECUTIVE-SUMMARY.md) |
| Technical Leaders | [docs/architecture/SYSTEM-OVERVIEW.md](docs/architecture/SYSTEM-OVERVIEW.md) |
| Developers | [docs/development/SETUP.md](docs/development/SETUP.md) |
| Operators | [docs/operations/RUNBOOK.md](docs/operations/RUNBOOK.md) |

For Claude Code: Start with [.clinerules](.clinerules)

## Quick Start

### Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) with qwen2.5:14b model

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/crypto-trading-bot.git
cd crypto-trading-bot

# Run the install script
bash scripts/install.sh

# Or manually:
pip install -r requirements.txt
mkdir -p data logs
```

### Setup Ollama

```bash
# Install Ollama from https://ollama.ai/
# Then pull the model:
ollama pull qwen2.5:14b

# Start Ollama server (keep running)
ollama serve
```

### Running

```bash
# Start the trading system (includes dashboard)
bash scripts/start.sh

# Access dashboard at http://localhost:8080

# Check status
bash scripts/status.sh

# Stop
bash scripts/stop.sh
```

For paper trading validation runs:
```bash
bash scripts/start_paper_trading.sh
```

### Configuration

```bash
# For WSL2: set Ollama host to Windows gateway IP
export OLLAMA_HOST=$(ip route show default | awk '{print $3}')
```

## Project Structure

```
crypto-trading-bot/
├── src/
│   ├── main.py              # Main entry point (Phase 2 system)
│   ├── market_feed.py       # WebSocket market data
│   ├── strategist.py        # LLM condition generation
│   ├── sniper.py            # Sub-ms trade execution
│   ├── journal.py           # Trade journaling
│   ├── knowledge.py         # Knowledge Brain
│   ├── coin_scorer.py       # Per-coin tracking
│   ├── pattern_library.py   # Trading patterns
│   ├── quick_update.py      # Instant learning
│   ├── reflection.py        # Hourly analysis
│   ├── adaptation.py        # Apply learnings
│   ├── profitability.py     # P&L tracking
│   ├── effectiveness.py     # Adaptation monitoring
│   ├── dashboard_v2.py      # Web dashboard
│   ├── database.py          # SQLite persistence
│   ├── llm_interface.py     # Ollama connection
│   └── main_legacy.py       # Old Phase 1 system (deprecated)
├── docs/                    # Documentation
├── tests/                   # Unit tests
├── data/                    # Database & state (gitignored)
└── logs/                    # Log files (gitignored)
```

## Learning Loop

The system learns automatically:

1. **Trade Executes** - Sniper opens/closes position
2. **Quick Update** (<10ms) - Updates coin score and pattern confidence
3. **Journal Records** - Full trade context saved
4. **Reflection** (hourly) - LLM analyzes patterns, generates insights
5. **Adaptation** - Blacklists losing coins, favors winners, creates rules
6. **Strategist Uses Knowledge** - Next conditions informed by learnings

## Coin Tiers

| Tier | Name | Coins | Max Position |
|------|------|-------|--------------|
| 1 | Blue Chips | BTC, ETH, BNB, XRP, SOL | 25% |
| 2 | Established | ADA, DOGE, AVAX, DOT... | 15% |
| 3 | High Volatility | PEPE, FLOKI, BONK... | 10% |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Main dashboard |
| `GET /api/health` | System health status |
| `GET /api/conditions` | Active trade conditions |
| `GET /api/positions` | Open positions |
| `GET /api/prices` | Current prices |
| `GET /api/knowledge` | Knowledge Brain summary |

## Development Status

- **Phase 1**: Foundation - Complete
- **Phase 1.5**: Production Hardening - Complete
- **Phase 2**: Autonomous Learning - **Deployed**
- **Phase 3**: Market Context Enhancement - Planned

## Disclaimer

This is a paper trading bot for educational purposes only.

- No real money is involved
- Past performance does not guarantee future results
- Cryptocurrency trading involves significant risk
- Always do your own research

## License

Private repository - All rights reserved.
