# Paper Trading Pre-Run Checklist

Complete this checklist before starting a 7-day validation run.

## Environment

- [ ] **Python 3.10+** installed and working
  ```bash
  python3 --version
  ```

- [ ] **Dependencies** installed
  ```bash
  pip install -r requirements.txt
  ```

- [ ] **Ollama** running with qwen2.5:14b
  ```bash
  ollama list | grep qwen2.5:14b
  ```

- [ ] **Disk space** > 10GB free
  ```bash
  df -h .
  ```

## Configuration

- [ ] **Paper trading mode** enabled in settings
  ```python
  # config/settings.py
  PAPER_TRADING = True
  INITIAL_BALANCE = 10000.0
  ```

- [ ] **Risk limits** configured
  ```python
  MAX_POSITION_SIZE = 500.0
  MAX_OPEN_POSITIONS = 3
  DAILY_LOSS_LIMIT = 500.0
  ```

- [ ] **Coins** configured
  ```python
  TRADEABLE_COINS = ["BTC", "ETH", "SOL", ...]
  ```

## Data Decision

Choose one:

- [ ] **Fresh start** - Reset database for clean validation
  ```bash
  ./scripts/start_paper_trading.sh --fresh
  ```

- [ ] **Continue** - Keep existing Knowledge Brain
  ```bash
  ./scripts/start_paper_trading.sh
  ```

## Directories

- [ ] **Logs directory** exists
  ```bash
  mkdir -p logs/validation
  ```

- [ ] **Data directory** exists
  ```bash
  mkdir -p data
  ```

## Network

- [ ] **Exchange API** accessible (for price feed)
  ```bash
  curl -s "https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT" | head -c 100
  ```

- [ ] **Dashboard port** available (8080)
  ```bash
  lsof -i :8080 || echo "Port available"
  ```

## Final Checks

- [ ] **System time** synchronized
  ```bash
  date
  ```

- [ ] **No other trading instances** running
  ```bash
  ps aux | grep main.py
  ```

- [ ] **Terminal/screen** ready for long-running process
  - Consider using `screen` or `tmux` for persistence

## Ready to Start

Once all boxes are checked:

```bash
# Make script executable (first time only)
chmod +x scripts/start_paper_trading.sh

# Start paper trading
./scripts/start_paper_trading.sh

# Or with fresh database
./scripts/start_paper_trading.sh --fresh
```

## Daily Checkpoints

Run the checkpoint script daily at a consistent time:

```bash
python scripts/daily_checkpoint.py
```

Or save to file:

```bash
python scripts/daily_checkpoint.py -o logs/validation/checkpoint-$(date +%Y%m%d).txt
```

## Emergency Stop

If needed, stop gracefully with Ctrl+C. The system will:
1. Save runtime state
2. Close open positions at current prices (paper)
3. Flush journal to database

For immediate stop (not recommended):
```bash
pkill -f main.py
```
