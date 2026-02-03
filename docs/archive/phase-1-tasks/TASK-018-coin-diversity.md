# TASK-018: Coin Diversity Enforcement

## Overview
Prevent the trading bot from repeatedly trading the same coin. Enforce cooldown periods between trades on the same coin to ensure diverse portfolio exposure and generate varied learning data.

## Current State
- Bot can trade same coin repeatedly
- No cooldown between trades on same coin
- Risk of fixating on one "favorite" coin
- Learning data may be repetitive/narrow

## Target State
- Cooldown period enforced after trading each coin
- Trades distributed across multiple coins
- Diverse learnings from different market conditions
- No single-coin fixation

---

## Configuration

### Cooldown Settings
```python
# Default: 10 minutes cooldown after trading a coin
COIN_COOLDOWN_SECONDS = 600

# Can be adjusted via environment variable
COIN_COOLDOWN_SECONDS = int(os.environ.get("COIN_COOLDOWN", 600))
```

### Cooldown Behavior
| Scenario | Action |
|----------|--------|
| Coin traded < 10 min ago | Reject trade, suggest alternatives |
| Coin traded > 10 min ago | Allow trade, reset cooldown |
| Open position on coin | Coin remains tradeable (for closing) |
| Cooldown expired | Coin available for trading |

---

## Implementation

### 1. Risk Manager Updates (`risk_manager.py`)

Add cooldown tracking to RiskManager class:

```python
# Configuration
COIN_COOLDOWN_SECONDS = int(os.environ.get("COIN_COOLDOWN", 300))

class RiskManager:
    def __init__(self, db: Database = None):
        # ... existing init ...
        self.coin_cooldowns: Dict[str, float] = {}
        self.cooldown_seconds = COIN_COOLDOWN_SECONDS

    def is_coin_in_cooldown(self, coin_name: str) -> bool:
        """Check if coin is in cooldown period."""
        if coin_name not in self.coin_cooldowns:
            return False

        elapsed = time.time() - self.coin_cooldowns[coin_name]
        return elapsed < self.cooldown_seconds

    def get_cooldown_remaining(self, coin_name: str) -> int:
        """Get seconds remaining in cooldown."""
        if coin_name not in self.coin_cooldowns:
            return 0

        elapsed = time.time() - self.coin_cooldowns[coin_name]
        remaining = self.cooldown_seconds - elapsed
        return max(0, int(remaining))

    def record_trade(self, coin_name: str):
        """Record trade time for cooldown tracking."""
        self.coin_cooldowns[coin_name] = time.time()

    def get_coins_in_cooldown(self) -> List[str]:
        """Get list of coins currently in cooldown."""
        return [
            coin for coin in self.coin_cooldowns
            if self.is_coin_in_cooldown(coin)
        ]
```

### 2. Trade Validation Update

Update `validate_trade()` to check cooldown:

```python
def validate_trade(self, coin_name: str, size_usd: float, action: str) -> TradeValidation:
    """Validate a proposed trade against all risk rules."""

    # ... existing validations ...

    # Check coin cooldown (only for new BUY trades)
    if action == "BUY" and self.is_coin_in_cooldown(coin_name):
        remaining = self.get_cooldown_remaining(coin_name)
        return TradeValidation(
            valid=False,
            reason=f"Coin {coin_name} in cooldown ({remaining}s remaining). Trade different coins for diversity.",
            max_allowed_size=0
        )

    # ... rest of validation ...
```

### 3. Main Loop Integration (`main.py`)

Record trades after successful execution:

```python
# After opening a trade successfully
if trade_result:
    risk_manager.record_trade(coin_name)
    logger.info(f"Trade opened: {coin_name}, cooldown started ({COIN_COOLDOWN_SECONDS}s)")
```

### 4. LLM Prompt Update (`llm_interface.py`)

Add cooldown info to trading decision prompt:

```python
# In get_trading_decision(), add to prompt:
coins_in_cooldown = risk_manager.get_coins_in_cooldown()

prompt = f"""...
Coins Currently in Cooldown (avoid these):
{json.dumps(coins_in_cooldown)}

IMPORTANT: Trade DIFFERENT coins to generate diverse learnings.
Avoid coins in cooldown - they were traded recently.
..."""
```

---

## Dashboard Integration

### Show Cooldown Status
Add to dashboard data:
```python
def get_cooldown_status():
    return {
        'coins_in_cooldown': rm.get_coins_in_cooldown(),
        'cooldown_details': {
            coin: rm.get_cooldown_remaining(coin)
            for coin in rm.get_coins_in_cooldown()
        }
    }
```

---

## Verification

### Test Cooldown Enforcement
```bash
# Watch logs for cooldown rejections
tail -f logs/trading_bot.log | grep -i cooldown

# Expected output when coin is in cooldown:
# "Coin bitcoin in cooldown (180s remaining). Trade different coins for diversity."
```

### Test Trade Distribution
```bash
# After 30 minutes of trading, check coin distribution
sqlite3 data/trading_bot.db "
SELECT coin_name, COUNT(*) as trades
FROM closed_trades
WHERE closed_at > datetime('now', '-30 minutes')
GROUP BY coin_name
ORDER BY trades DESC;
"

# Should show trades across multiple coins, not concentrated on one
```

---

## Success Criteria

- [ ] Cooldown enforced after each trade (default 5 min)
- [ ] Validation rejects trades on coins in cooldown
- [ ] LLM informed about coins to avoid
- [ ] Trades distributed across multiple coins
- [ ] Cooldown status visible in logs
- [ ] Diverse learnings generated from different coins
