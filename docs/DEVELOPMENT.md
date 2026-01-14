# Development Guide: Self-Learning Crypto Trading Bot

## Quick Start

```bash
# Install dependencies
pip install flask requests anthropic

# Set API key
export ANTHROPIC_API_KEY="your-key-here"

# Run the bot
python3 src/main.py

# Run dashboard (separate terminal)
python3 src/dashboard.py

# Generate daily summary
python3 src/daily_summary.py
```

---

## Project Structure

```
crypto-trading-bot/
├── src/
│   ├── database.py        # SQLite operations
│   ├── market_data.py     # CoinGecko API integration
│   ├── llm_interface.py   # Claude API integration
│   ├── risk_manager.py    # Position sizing, limits
│   ├── trading_engine.py  # Trade execution logic
│   ├── learning_system.py # Learning & rule creation
│   ├── dashboard.py       # Web dashboard (Flask)
│   ├── daily_summary.py   # Report generation
│   └── main.py            # Main trading loop
├── data/
│   ├── trading_bot.db     # SQLite database
│   └── reports/           # Daily summary files
├── docs/
│   ├── PRD.md             # Product requirements
│   ├── TASKS.md           # Task tracking
│   ├── DEVELOPMENT.md     # This file
│   └── TASK-XXX-*.md      # Task specifications
└── tests/
    └── test_*.py          # Unit tests
```

---

## Mandatory Workflow

### Before Writing Any Code

1. **Create a spec** in `docs/TASK-XXX-name.md`
2. **Get user approval** on the approach
3. **Only then** write the implementation

### Spec Template

```markdown
# TASK-XXX: Feature Name

## Overview
What this feature does and why.

## Requirements
- Specific requirement 1
- Specific requirement 2

## Implementation
### Approach
How we'll build it.

### Files to Modify/Create
- `src/file.py` - What changes

### Code Examples
```python
# Key implementation details
```

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Testing
How to verify it works.
```

---

## Scaling Guidelines

### Adding New Coins Safely

#### Step 1: Validate Coin Data
```python
# Test that the coin exists and has valid data
from src.market_data import MarketDataFetcher

mdf = MarketDataFetcher()
data = mdf.fetch_price("new-coin-id")
print(f"Price: {data}")  # Should not be None
```

#### Step 2: Add to Coin List
```python
# In market_data.py or config
COINS = [
    # Tier 1 (existing)
    "bitcoin", "ethereum", "solana",
    # New coin
    "new-coin-id",  # Use CoinGecko ID
]
```

#### Step 3: Verify Rate Limits
```python
# Check we're within limits after adding
# CoinGecko Free: 10-30 calls/minute
# With 50 coins and 1 call per coin: need batching
```

#### Step 4: Test One Cycle
```bash
# Run one trading cycle and check logs
python3 -c "from src.main import TradingBot; bot = TradingBot(); bot.run_cycle()"
```

### Batch API Calls for Scale

```python
# Instead of individual calls:
for coin in coins:
    price = fetch_price(coin)  # 50 API calls!

# Use batch endpoint:
def fetch_prices_batch(coin_ids: List[str]) -> Dict:
    """Fetch multiple coins in one API call."""
    ids = ",".join(coin_ids)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
    response = requests.get(url)
    return response.json()  # 1 API call for all!
```

### Testing with More Data

#### Load Test Script
```python
"""Test system performance with increased load."""
import time
from src.database import Database
from src.market_data import MarketDataFetcher

def load_test(num_coins: int = 50, cycles: int = 10):
    db = Database()
    mdf = MarketDataFetcher()

    for cycle in range(cycles):
        start = time.time()

        # Fetch all prices
        # Process decisions
        # Log timing

        elapsed = time.time() - start
        print(f"Cycle {cycle}: {elapsed:.2f}s")

        if elapsed < 60:
            time.sleep(60 - elapsed)  # Rate limit
```

#### Database Performance
```sql
-- Check table sizes
SELECT name, COUNT(*) as rows FROM (
    SELECT 'market_data' as name FROM market_data
    UNION ALL SELECT 'closed_trades' FROM closed_trades
    UNION ALL SELECT 'learnings' FROM learnings
) GROUP BY name;

-- Ensure indexes exist
.indexes
```

### Verification at Scale

#### Checklist Before Scaling
- [ ] Batch API calls implemented
- [ ] Rate limit tracking in place
- [ ] Error handling for API failures
- [ ] Database indexes on frequently queried columns
- [ ] Memory usage acceptable with more data
- [ ] Logs don't grow unbounded

#### Monitoring Commands
```bash
# Watch API calls
tail -f logs/trading.log | grep "API"

# Check database size
ls -lh data/trading_bot.db

# Memory usage
ps aux | grep python3

# Active connections (if applicable)
netstat -an | grep 8080
```

---

## Database Schema

### Core Tables
```sql
-- Account state
account_state(id, balance, available_balance, in_positions,
              total_pnl, daily_pnl, trade_count_today)

-- Market data cache
market_data(coin, price_usd, change_24h, last_updated)

-- Open positions
open_trades(id, coin_name, entry_price, size_usd,
            stop_loss_price, take_profit_price, ...)

-- Closed positions
closed_trades(id, coin_name, entry_price, exit_price,
              pnl_usd, pnl_pct, ...)

-- Extracted learnings
learnings(id, trade_id, learning_text, confidence_level, ...)

-- Trading rules
trading_rules(id, rule_text, status, success_count,
              failure_count, ...)

-- Activity log
activity_log(id, activity_type, description, created_at)
```

---

## Common Tasks

### Reset Paper Trading Balance
```python
from src.database import Database
db = Database()
db.update_account_state(
    balance=1000.0,
    available_balance=1000.0,
    in_positions=0.0,
    total_pnl=0.0,
    daily_pnl=0.0,
    trade_count_today=0
)
```

### Clear All Trades (Fresh Start)
```bash
# Backup first!
cp data/trading_bot.db data/trading_bot.db.backup

# Then clear
sqlite3 data/trading_bot.db "DELETE FROM open_trades; DELETE FROM closed_trades;"
```

### View Recent Activity
```python
from src.database import Database
db = Database()
for activity in db.get_recent_activity(20):
    print(f"{activity['created_at']}: {activity['description']}")
```

### Force Learning Analysis
```python
from src.learning_system import LearningSystem
from src.llm_interface import LLMInterface

ls = LearningSystem(llm=LLMInterface())
learnings = ls.analyze_all_pending()
print(f"Created {len(learnings)} new learnings")
```

---

## Troubleshooting

### API Rate Limit Errors
```
Error: 429 Too Many Requests
```
**Solution:** Implement batching, add delays between calls, or upgrade API tier.

### LLM Timeout
```
Error: Request timeout
```
**Solution:** Increase timeout, simplify prompt, or retry with backoff.

### Database Locked
```
Error: database is locked
```
**Solution:** Ensure only one writer at a time, use WAL mode:
```python
conn.execute("PRAGMA journal_mode=WAL")
```

### Dashboard Won't Start
```
Error: Address already in use
```
**Solution:** Kill existing process or use different port:
```bash
lsof -i :8080 | grep python | awk '{print $2}' | xargs kill
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude API key | Required |
| `COINGECKO_API_KEY` | CoinGecko API key (optional) | None |
| `TRADING_BOT_DB` | Database path | `data/trading_bot.db` |
| `DASHBOARD_PORT` | Dashboard port | `8080` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
