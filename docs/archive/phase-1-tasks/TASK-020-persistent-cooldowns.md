# TASK-020: Persistent Coin Cooldowns

## Overview
Fix the coin cooldown system to properly enforce diversity. Currently cooldowns reset on bot restart, LLM ignores "avoid" suggestions, and 10-minute cooldown is too short.

## Current Issues

### Issue 1: Cooldowns Lost on Restart
- Cooldown dict is in-memory only
- Bot restart = all cooldowns cleared
- No persistence layer

### Issue 2: LLM Ignores Suggestion
- Current prompt: "Avoid coins in cooldown"
- LLM treats it as optional suggestion
- Keeps picking same coin anyway

### Issue 3: Cooldown Too Short
- 10 minutes expires quickly
- With 30-second cycles, that's only ~20 cycles
- Not enough time to explore other coins

---

## Fixes

### Fix 1: Database Persistence

**New table: `coin_cooldowns`**
```sql
CREATE TABLE IF NOT EXISTS coin_cooldowns (
    coin_name TEXT PRIMARY KEY,
    expires_at TIMESTAMP NOT NULL
);
```

**RiskManager changes:**
```python
class RiskManager:
    def __init__(self, db: Database = None):
        # ... existing init ...
        self._load_cooldowns_from_db()  # NEW: Load on startup

    def _load_cooldowns_from_db(self):
        """Load active cooldowns from database."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT coin_name, expires_at FROM coin_cooldowns
                WHERE expires_at > datetime('now')
            """)
            for row in cursor.fetchall():
                # Convert expires_at to timestamp
                expires_at = datetime.fromisoformat(row[1])
                self.coin_cooldowns[row[0]] = expires_at.timestamp()

    def record_trade(self, coin_name: str):
        """Record trade and persist cooldown to database."""
        expires_at = time.time() + self.cooldown_seconds
        self.coin_cooldowns[coin_name] = expires_at

        # Persist to database
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO coin_cooldowns (coin_name, expires_at)
                VALUES (?, datetime('now', '+' || ? || ' seconds'))
            """, (coin_name, self.cooldown_seconds))
            conn.commit()

    def _cleanup_expired_cooldowns(self):
        """Remove expired cooldowns from database."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM coin_cooldowns
                WHERE expires_at <= datetime('now')
            """)
            conn.commit()
```

### Fix 2: FORBIDDEN LLM Instruction

**Current (weak):**
```
Avoid coins listed in "Coins in Cooldown" - they were traded recently.
```

**New (strong):**
```
FORBIDDEN COINS (DO NOT TRADE - in cooldown):
{list}

You MUST NOT select any coin from the FORBIDDEN list above.
These coins were recently traded and are blocked for diversity.
Selecting a forbidden coin will cause your trade to be REJECTED.
Choose a different coin instead.
```

### Fix 3: Extend Cooldown to 30 Minutes

```python
# Old
COIN_COOLDOWN_SECONDS = int(os.environ.get("COIN_COOLDOWN", 600))  # 10 min

# New
COIN_COOLDOWN_SECONDS = int(os.environ.get("COIN_COOLDOWN", 1800))  # 30 min
```

---

## Implementation Plan

### Step 1: Database Table
Add `coin_cooldowns` table to database.py schema.

### Step 2: Update RiskManager
- Add `_load_cooldowns_from_db()` method
- Update `record_trade()` to persist to DB
- Add cleanup for expired cooldowns
- Change default to 1800 seconds (30 min)

### Step 3: Update LLM Prompt
Change `llm_interface.py` to use FORBIDDEN language.

### Step 4: Test
- Trade a coin
- Restart bot
- Verify cooldown persists
- Verify LLM avoids forbidden coins

---

## Files Changed

| File | Changes |
|------|---------|
| `database.py` | Add `coin_cooldowns` table |
| `risk_manager.py` | Add DB persistence, load on init, 30-min default |
| `llm_interface.py` | FORBIDDEN prompt language |

---

## Verification

### Test 1: Cooldown Persists Across Restart
```bash
# Trade a coin
# Note the coin name
# Restart bot: bash scripts/restart.sh
# Check cooldown still active:
python3 -c "
from src.risk_manager import RiskManager
rm = RiskManager()
print(f'Coins in cooldown: {rm.get_coins_in_cooldown()}')
"
```

### Test 2: LLM Avoids Forbidden Coins
```bash
# Watch LLM decisions - should not pick forbidden coins
tail -f logs/trading_bot.log | grep -E "BUY|FORBIDDEN"
```

### Test 3: Diverse Coin Selection
```bash
# After 30+ minutes, check trade distribution
python3 -c "
import sqlite3
conn = sqlite3.connect('data/trading_bot.db')
cursor = conn.cursor()
cursor.execute('''
SELECT coin_name, COUNT(*) FROM closed_trades
WHERE closed_at > datetime('now', '-1 hour')
GROUP BY coin_name ORDER BY 2 DESC
''')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]} trades')
"
```

---

## Success Criteria

- [ ] Cooldowns survive bot restart
- [ ] `coin_cooldowns` table created and populated
- [ ] LLM prompt uses FORBIDDEN language
- [ ] Cooldown extended to 30 minutes
- [ ] Bot trades multiple different coins over time
