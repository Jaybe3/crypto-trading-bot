# Development Environment Setup

**Last Updated:** February 3, 2026
**Phase:** 2 Complete

---

## Prerequisites

- Python 3.10+
- Ollama (for local LLM)
- Git
- SQLite 3

---

## Quick Start

```bash
# Clone repository
git clone <repository-url>
cd crypto-trading-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/WSL/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p data logs data/backups

# Initialize database
python -c "from src.database import Database; Database()"

# Run tests
pytest tests/ -v

# Start paper trading
python src/main_v2.py --mode paper --dashboard
```

---

## Detailed Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd crypto-trading-bot
```

### 2. Create Virtual Environment

**Linux/WSL/Mac:**
```bash
python -m venv venv
source venv/bin/activate
```

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**
- `aiohttp` - Async HTTP client
- `websockets` - WebSocket connections
- `fastapi` - Dashboard API
- `uvicorn` - ASGI server
- `jinja2` - Templates
- `pytest` - Testing
- `pytest-asyncio` - Async tests

### 4. Create Directories

```bash
mkdir -p data logs data/backups data/exports data/reports
```

### 5. Setup Ollama

**Install Ollama:**
- Download from https://ollama.ai/
- Or via package manager:
  ```bash
  curl -fsSL https://ollama.ai/install.sh | sh
  ```

**Pull the model:**
```bash
ollama pull qwen2.5:14b
```

**Start server:**
```bash
ollama serve
```

**Verify:**
```bash
curl http://localhost:11434/api/tags
```

### 6. WSL2 Configuration (if applicable)

If running the bot in WSL2 with Ollama on Windows:

**Find Windows host IP:**
```bash
ip route show default | awk '{print $3}'
```

**Set environment variable:**
```bash
export OLLAMA_HOST=172.27.144.1  # Use your actual IP
```

**Make permanent:**
```bash
echo 'export OLLAMA_HOST=172.27.144.1' >> ~/.bashrc
```

---

## Verification

### Check Python Environment

```bash
python -c "import aiohttp, websockets, fastapi; print('Dependencies OK')"
```

### Check Database

```bash
python -c "from src.database import Database; Database(); print('Database OK')"
```

### Check LLM Connection

```bash
python -c "
from src.llm_interface import LLMInterface
from src.database import Database
llm = LLMInterface()
print('LLM Available:', llm.is_available())
"
```

### Run Tests

```bash
pytest tests/ -v
```

Expected output: All tests pass

### Start System

```bash
python src/main_v2.py --mode paper --dashboard --port 8080
```

Open http://localhost:8080 to verify dashboard.

---

## Project Structure

```
crypto-trading-bot/
├── src/
│   ├── main_v2.py           # Entry point
│   ├── market_feed.py       # WebSocket data
│   ├── strategist.py        # LLM conditions
│   ├── sniper.py            # Execution
│   ├── journal.py           # Trade recording
│   ├── quick_update.py      # Instant learning
│   ├── coin_scorer.py       # Coin tracking
│   ├── pattern_library.py   # Pattern management
│   ├── reflection.py        # Deep analysis
│   ├── adaptation.py        # Apply changes
│   ├── knowledge.py         # Knowledge store
│   ├── database.py          # Persistence
│   ├── llm_interface.py     # LLM client
│   ├── dashboard_v2.py      # Web dashboard
│   ├── profitability.py     # P&L tracking
│   ├── models/              # Data models
│   │   ├── trade_condition.py
│   │   ├── quick_update.py
│   │   ├── knowledge.py
│   │   ├── reflection.py
│   │   └── adaptation.py
│   └── analysis/            # Analysis tools
│       ├── metrics.py
│       ├── performance.py
│       └── learning.py
├── tests/                   # Test suite
├── scripts/                 # Utility scripts
├── data/                    # Database and exports
├── logs/                    # Log files
├── docs/                    # Documentation
│   ├── architecture/        # System design
│   ├── development/         # Dev guides
│   ├── operations/          # Ops guides
│   └── business/            # Business docs
└── requirements.txt
```

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_HOST` | `localhost` | Ollama server address |
| `OLLAMA_MODEL` | `qwen2.5:14b` | LLM model to use |
| `DB_PATH` | `data/trading_bot.db` | Database file path |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

**Set variables:**
```bash
export OLLAMA_HOST=localhost
export OLLAMA_MODEL=qwen2.5:14b
export LOG_LEVEL=DEBUG
```

---

## IDE Setup

### VS Code

**Recommended extensions:**
- Python (Microsoft)
- Pylance
- Python Test Explorer

**settings.json:**
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "python.linting.enabled": true
}
```

### PyCharm

1. Open project folder
2. Configure interpreter: `venv/bin/python`
3. Set pytest as test runner
4. Mark `src/` as Sources Root

---

## Running the System

### Paper Trading Mode

```bash
python src/main_v2.py --mode paper --dashboard --port 8080
```

### Dashboard Only

```bash
python src/dashboard_v2.py --port 8080 --db data/trading_bot.db
```

### Background Mode

```bash
nohup python src/main_v2.py --mode paper --dashboard > logs/bot.log 2>&1 &
```

### Check Status

```bash
curl http://localhost:8080/api/status
```

---

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/my-feature
```

### 2. Make Changes

Edit code in `src/`

### 3. Run Tests

```bash
pytest tests/ -v
```

### 4. Test Manually

```bash
python src/main_v2.py --mode paper --dashboard
```

### 5. Commit

```bash
git add .
git commit -m "Add my feature"
```

### 6. Push

```bash
git push origin feature/my-feature
```

---

## Troubleshooting

### Ollama Connection Failed

```bash
# Check if running
curl http://localhost:11434/api/tags

# Start if not
ollama serve

# For WSL, check Windows IP
curl http://172.27.144.1:11434/api/tags
```

### Database Locked

```bash
# Find processes
lsof data/trading_bot.db

# Kill if needed
pkill -f "main_v2.py"
```

### Port 8080 in Use

```bash
# Check what's using it
lsof -i :8080

# Use different port
python src/main_v2.py --dashboard --port 9090
```

### Import Errors

```bash
# Ensure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Test Failures

```bash
# Run with verbose output
pytest tests/ -v --tb=long

# Run specific failing test
pytest tests/test_file.py::test_name -v
```

---

## Related Documentation

- [COMPONENT-GUIDE.md](./COMPONENT-GUIDE.md) - Component details
- [TESTING-GUIDE.md](./TESTING-GUIDE.md) - Testing practices
- [ADDING-FEATURES.md](./ADDING-FEATURES.md) - Adding features
- [../operations/RUNBOOK.md](../operations/RUNBOOK.md) - Operations
