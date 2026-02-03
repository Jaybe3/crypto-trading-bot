# TASK-121: Coin Scoring System

**Status:** COMPLETED
**Created:** February 3, 2026
**Completed:** N/A
**Priority:** High
**Depends On:** TASK-120 (Knowledge Brain Data Structures), TASK-102 (Trade Journal)
**Phase:** Phase 2.3 - Knowledge Brain

---

## Objective

Implement the coin scoring logic that updates performance metrics after each trade and automatically triggers adaptations (blacklist, size reduction) when thresholds are met.

---

## Background

TASK-120 created the data structures (`CoinScore`, `KnowledgeBrain`). This task adds the intelligence:

1. **Quick Update** - After every trade close, update that coin's score
2. **Threshold Checks** - Automatically trigger adaptations when coins cross thresholds
3. **Position Size Modifiers** - Provide size recommendations based on coin performance

This is part of the "Quick Update" tier of reflection - instant math after each trade, no LLM needed.

---

## Specification

### Adaptation Thresholds (from spec)

| Action | Condition | Effect |
|--------|-----------|--------|
| **BLACKLIST** | 5+ trades AND win_rate < 30% AND total_pnl < 0 | Stop trading this coin |
| **REDUCE_SIZE** | 5+ trades AND win_rate < 45% | Use 50% normal position size |
| **FAVOR** | 5+ trades AND win_rate >= 60% AND total_pnl > 0 | Can use 150% position size |
| **NORMAL** | Default | Use 100% position size |

### CoinScorer Class

```python
class CoinScorer:
    """Manages coin performance scoring and adaptations.

    Called after every trade close to update scores and check thresholds.
    """

    def __init__(self, brain: KnowledgeBrain):
        self.brain = brain

    def process_trade_result(self, trade: JournalEntry) -> CoinAdaptation:
        """Process a completed trade and return any adaptation triggered.

        Args:
            trade: Completed trade from journal with pnl_usd populated.

        Returns:
            CoinAdaptation describing any status change, or None.
        """

    def get_position_modifier(self, coin: str) -> float:
        """Get position size modifier for a coin.

        Returns:
            Multiplier: 0.0 (blacklisted), 0.5 (reduced), 1.0 (normal), 1.5 (favored)
        """

    def get_coin_status(self, coin: str) -> CoinStatus:
        """Get current status for a coin.

        Returns:
            CoinStatus enum: BLACKLISTED, REDUCED, NORMAL, FAVORED, UNKNOWN
        """

    def check_thresholds(self, coin: str) -> Optional[CoinAdaptation]:
        """Check if coin crosses any adaptation thresholds.

        Called automatically by process_trade_result().
        """

    def force_blacklist(self, coin: str, reason: str) -> CoinAdaptation:
        """Manually blacklist a coin (for dashboard override)."""

    def force_unblacklist(self, coin: str) -> CoinAdaptation:
        """Manually remove a coin from blacklist."""
```

### Data Classes

```python
class CoinStatus(Enum):
    """Current trading status for a coin."""
    BLACKLISTED = "blacklisted"    # Do not trade
    REDUCED = "reduced"            # Trade with reduced size
    NORMAL = "normal"              # Trade normally
    FAVORED = "favored"            # Can trade with increased size
    UNKNOWN = "unknown"            # Not enough data

@dataclass
class CoinAdaptation:
    """Record of a coin status change."""
    coin: str
    timestamp: datetime
    old_status: CoinStatus
    new_status: CoinStatus
    reason: str
    trigger_stats: dict  # Stats at time of trigger
```

### Integration Points

**1. Called by Sniper on trade close:**
```python
# In Sniper._close_position()
async def _close_position(self, position, exit_reason, exit_price):
    # ... existing close logic ...

    # Journal the trade
    entry = self.journal.record_exit(position, exit_price, exit_reason, pnl)

    # Update coin score (NEW)
    adaptation = self.coin_scorer.process_trade_result(entry)
    if adaptation:
        logger.info(f"ADAPTATION: {adaptation.coin} -> {adaptation.new_status.value}")
```

**2. Queried by Strategist for position sizing:**
```python
# In Strategist condition generation
base_size = 50.0  # USD
modifier = self.coin_scorer.get_position_modifier(coin)
actual_size = base_size * modifier  # 0, 25, 50, or 75 USD
```

**3. Queried for blacklist check:**
```python
# In Strategist before generating conditions for a coin
if self.coin_scorer.get_coin_status(coin) == CoinStatus.BLACKLISTED:
    # Skip this coin
    continue
```

### Threshold Logic

```python
def check_thresholds(self, coin: str) -> Optional[CoinAdaptation]:
    score = self.brain.get_coin_score(coin)
    if not score or score.total_trades < 5:
        return None  # Not enough data

    current_status = self.get_coin_status(coin)
    new_status = current_status
    reason = ""

    # Check BLACKLIST threshold (most severe)
    if (score.win_rate < 0.30 and
        score.total_pnl < 0 and
        not score.is_blacklisted):
        new_status = CoinStatus.BLACKLISTED
        reason = f"Win rate {score.win_rate:.0%} < 30% with ${score.total_pnl:.2f} loss over {score.total_trades} trades"
        self.brain.blacklist_coin(coin, reason)

    # Check REDUCED threshold
    elif (score.win_rate < 0.45 and
          current_status not in [CoinStatus.BLACKLISTED, CoinStatus.REDUCED]):
        new_status = CoinStatus.REDUCED
        reason = f"Win rate {score.win_rate:.0%} < 45% over {score.total_trades} trades"

    # Check FAVORED threshold
    elif (score.win_rate >= 0.60 and
          score.total_pnl > 0 and
          current_status not in [CoinStatus.BLACKLISTED]):
        new_status = CoinStatus.FAVORED
        reason = f"Win rate {score.win_rate:.0%} >= 60% with ${score.total_pnl:.2f} profit"

    # Check if coin recovered (was reduced but improved)
    elif (score.win_rate >= 0.50 and
          current_status == CoinStatus.REDUCED):
        new_status = CoinStatus.NORMAL
        reason = f"Win rate recovered to {score.win_rate:.0%}"

    if new_status != current_status:
        return CoinAdaptation(
            coin=coin,
            timestamp=datetime.now(),
            old_status=current_status,
            new_status=new_status,
            reason=reason,
            trigger_stats={
                "total_trades": score.total_trades,
                "win_rate": score.win_rate,
                "total_pnl": score.total_pnl,
            }
        )
    return None
```

---

## Technical Approach

### Step 1: Create CoinScorer Class

Create `src/coin_scorer.py`:
- CoinStatus enum
- CoinAdaptation dataclass
- CoinScorer class with all methods

### Step 2: Add Adaptation Logging

Update `src/database.py`:
- Add `coin_adaptations` table to track status changes
- Add CRUD methods for adaptations

### Step 3: Integrate with Sniper

Update `src/sniper.py`:
- Accept CoinScorer in constructor
- Call `process_trade_result()` after trade close

### Step 4: Integrate with Strategist

Update `src/strategist.py`:
- Query `get_position_modifier()` when generating conditions
- Skip blacklisted coins

### Step 5: Create Unit Tests

Create `tests/test_coin_scorer.py`:
- Test threshold detection
- Test position modifiers
- Test status transitions
- Test edge cases (not enough trades, etc.)

---

## Files Created

| File | Purpose |
|------|---------|
| `src/coin_scorer.py` | CoinScorer class with threshold logic |
| `tests/test_coin_scorer.py` | Unit tests |

---

## Files Modified

| File | Change |
|------|--------|
| `src/database.py` | Add coin_adaptations table |
| `src/sniper.py` | Call CoinScorer on trade close |
| `src/strategist.py` | Query position modifiers, skip blacklisted |
| `src/main_v2.py` | Initialize CoinScorer, wire components |

---

## Acceptance Criteria

- [x] CoinScorer updates scores after each trade close
- [x] Coins auto-blacklisted when: 5+ trades AND <30% win rate AND negative P&L
- [x] Position size reduced when: 5+ trades AND <45% win rate
- [x] Position size increased when: 5+ trades AND >=60% win rate AND positive P&L
- [x] Blacklisted coins skipped by Strategist
- [x] Reduced coins get 50% position size
- [x] Adaptations logged to database with full context
- [x] Status can recover (reduced → normal when improved)
- [x] Unit tests pass

---

## Verification

### Unit Test

```bash
python -m pytest tests/test_coin_scorer.py -v
```

### Integration Test

```python
from src.coin_scorer import CoinScorer, CoinStatus
from src.knowledge import KnowledgeBrain
from src.database import Database

# Setup
db = Database("data/test_scorer.db")
brain = KnowledgeBrain(db)
scorer = CoinScorer(brain)

# Simulate losing coin
for i in range(6):
    brain.update_coin_score("SHIB", {"won": False, "pnl": -2.0})

# Check status
status = scorer.get_coin_status("SHIB")
assert status == CoinStatus.BLACKLISTED
assert scorer.get_position_modifier("SHIB") == 0.0

# Simulate winning coin
for i in range(6):
    brain.update_coin_score("SOL", {"won": True, "pnl": 3.0})

status = scorer.get_coin_status("SOL")
assert status == CoinStatus.FAVORED
assert scorer.get_position_modifier("SOL") == 1.5

print("Coin Scorer working!")
```

### Manual Verification

```bash
# Watch logs during trading
python src/main_v2.py

# Should see:
# [INFO] Trade closed: SHIB -$2.00
# [INFO] Updated SHIB score: 6 trades, 16.7% win rate
# [INFO] ADAPTATION: SHIB -> blacklisted (Win rate 17% < 30% with -$12.00 loss)
```

---

## Edge Cases

| Case | Handling |
|------|----------|
| < 5 trades | Return UNKNOWN status, no adaptation |
| Coin not in brain | Create new score entry |
| Already blacklisted | Don't re-blacklist |
| Manual override | Respect force_blacklist/force_unblacklist |
| Win rate exactly at threshold | Use < not <= for safety |

---

## Position Size Modifiers

| Status | Modifier | Example (base $50) |
|--------|----------|-------------------|
| BLACKLISTED | 0.0 | $0 (don't trade) |
| REDUCED | 0.5 | $25 |
| NORMAL | 1.0 | $50 |
| FAVORED | 1.5 | $75 |
| UNKNOWN | 1.0 | $50 (treat as normal) |

---

## Completion Notes

### Implementation Summary

**Date:** February 3, 2026

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/coin_scorer.py` | 290 | CoinScorer class, CoinStatus enum, CoinAdaptation dataclass |
| `tests/test_coin_scorer.py` | 320 | Comprehensive unit tests |

### Files Modified

| File | Changes |
|------|---------|
| `src/database.py` | Added `coin_adaptations` table + indexes + CRUD methods |
| `src/sniper.py` | Added `coin_scorer` parameter, calls `process_trade_result()` on exit |
| `src/strategist.py` | Added `coin_scorer` parameter, applies position modifiers, skips blacklisted |
| `src/main_v2.py` | Initializes KnowledgeBrain + CoinScorer, wires to Sniper and Strategist |

### Key Implementation Details

1. **CoinStatus Enum**: BLACKLISTED, REDUCED, NORMAL, FAVORED, UNKNOWN

2. **Position Modifiers**:
   - BLACKLISTED: 0.0 (don't trade)
   - REDUCED: 0.5 (half size)
   - NORMAL: 1.0
   - FAVORED: 1.5 (increased size)

3. **Threshold Logic**:
   - Min 5 trades required for any adaptation
   - Blacklist: <30% win rate AND negative P&L
   - Reduce: <45% win rate
   - Favor: >=60% win rate AND positive P&L
   - Recovery: REDUCED → NORMAL when win rate >= 50%

4. **Integration Flow**:
   ```
   Sniper._execute_exit()
       → coin_scorer.process_trade_result()
           → brain.update_coin_score()
           → check_thresholds()
               → log adaptation if status changed

   Strategist._validate_condition()
       → coin_scorer.get_coin_status()
           → skip if BLACKLISTED
       → coin_scorer.get_position_modifier()
           → adjust position_size_usd
   ```

### Verification

```bash
python3 -c "
from src.coin_scorer import CoinScorer, CoinStatus
# ... integration tests ...
"
# Output: All Tests Passed!
```

---

## Related

- [TASK-120](./TASK-120.md) - Knowledge Brain Data Structures (provides CoinScore)
- [TASK-130](./TASK-130.md) - Quick Update (calls CoinScorer)
- [TASK-123](./TASK-123.md) - Strategist ← Knowledge Integration (uses position modifiers)
- [AUTONOMOUS-TRADER-SPEC.md](../AUTONOMOUS-TRADER-SPEC.md) - Section 7: Adaptation Thresholds
