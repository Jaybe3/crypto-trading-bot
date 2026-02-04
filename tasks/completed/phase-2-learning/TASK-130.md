# TASK-130: Quick Update (Post-Trade)

**Status:** COMPLETED
**Created:** February 3, 2026
**Completed:** February 3, 2026
**Priority:** High
**Depends On:** TASK-101 (Sniper), TASK-102 (Journal), TASK-121 (CoinScorer), TASK-122 (PatternLibrary)
**Phase:** Phase 2.4 - Reflection Engine

---

## Objective

Implement the Quick Update system that runs instantly after every trade closes, updating coin scores, pattern confidence, and triggering automatic adaptations - all without LLM calls.

---

## Background

The Reflection Engine has two tiers:

| Tier | When | What It Does | Speed |
|------|------|--------------|-------|
| **Quick Update** | After every trade | Update coin score, pattern confidence, log outcome | Instant |
| **Deep Reflection** | Hourly OR after 10 trades | LLM analyzes patterns, generates insights | 30-60s |

This task implements the **Quick Update** tier. It coordinates calling:
- `CoinScorer.process_trade_result()` (already built in TASK-121)
- `PatternLibrary.record_pattern_outcome()` (already built in TASK-122)
- Activity logging for audit trail

**Key Principle:** Quick Update is pure math - no LLM calls, no delays. It must complete in milliseconds.

---

## Current State

What exists:
- `Sniper._execute_exit()` calls `journal.record_exit()` when a trade closes
- `CoinScorer.process_trade_result()` updates coin scores and triggers adaptations
- `PatternLibrary.record_pattern_outcome()` updates pattern confidence

What's missing:
- No connection between trade closure and Knowledge Brain updates
- Sniper doesn't know about CoinScorer or PatternLibrary
- No coordination of post-trade updates

---

## Specification

### QuickUpdate Class

```python
# src/quick_update.py

class QuickUpdate:
    """Instant post-trade updates - no LLM, pure math.

    Called immediately after every trade closes to update:
    - Coin score (wins, losses, P&L, trend)
    - Pattern confidence (if pattern was used)
    - Adaptation triggers (blacklist, reduce, favor)

    Must complete in <10ms.
    """

    def __init__(
        self,
        coin_scorer: CoinScorer,
        pattern_library: PatternLibrary,
        db: Database,
    ):
        self.coin_scorer = coin_scorer
        self.pattern_library = pattern_library
        self.db = db

        # Stats
        self.updates_processed = 0
        self.adaptations_triggered = 0

    def process_trade_close(self, trade_result: TradeResult) -> QuickUpdateResult:
        """Process a completed trade and update all knowledge.

        Args:
            trade_result: Trade outcome with coin, pnl, pattern_id, etc.

        Returns:
            QuickUpdateResult with any adaptations triggered.
        """

    def _update_coin_score(self, trade_result: TradeResult) -> Optional[CoinAdaptation]:
        """Update coin score and check thresholds."""

    def _update_pattern_confidence(self, trade_result: TradeResult) -> Optional[PatternUpdate]:
        """Update pattern confidence if a pattern was used."""

    def _log_quick_update(self, result: QuickUpdateResult) -> None:
        """Log the quick update for audit trail."""
```

### TradeResult Dataclass

```python
@dataclass
class TradeResult:
    """Outcome of a completed trade, passed to QuickUpdate."""

    trade_id: str
    coin: str
    direction: str                    # LONG or SHORT
    entry_price: float
    exit_price: float
    position_size_usd: float
    pnl_usd: float
    won: bool                         # pnl_usd > 0
    exit_reason: str                  # stop_loss, take_profit, manual

    # Optional context
    pattern_id: Optional[str] = None  # Pattern used, if any
    strategy_id: Optional[str] = None # Strategy that generated condition
    condition_id: Optional[str] = None

    # Timing
    entry_timestamp: int = 0
    exit_timestamp: int = 0
    duration_seconds: int = 0

    # Market context at exit
    btc_price: Optional[float] = None
    btc_trend: Optional[str] = None
```

### QuickUpdateResult Dataclass

```python
@dataclass
class QuickUpdateResult:
    """Result of a quick update, including any adaptations."""

    trade_id: str
    coin: str
    won: bool
    pnl_usd: float

    # What was updated
    coin_score_updated: bool = True
    pattern_updated: bool = False
    pattern_id: Optional[str] = None

    # Adaptations triggered
    coin_adaptation: Optional[CoinAdaptation] = None   # Blacklist, reduce, etc.
    pattern_deactivated: bool = False                   # Pattern confidence too low

    # New coin status after update
    new_coin_status: str = "normal"

    # Processing time
    processing_time_ms: float = 0.0
```

### Integration with Sniper

Update Sniper to call QuickUpdate after every exit:

```python
# In Sniper._execute_exit()

def _execute_exit(self, position, price, timestamp, reason):
    # ... existing exit logic ...

    # Calculate PnL
    pnl = self._calculate_pnl(position, price)

    # Record in journal
    self.journal.record_exit(position, price, timestamp, reason, pnl)

    # NEW: Quick update
    if self.quick_update:
        trade_result = TradeResult(
            trade_id=position.id,
            coin=position.coin,
            direction=position.direction,
            entry_price=position.entry_price,
            exit_price=price,
            position_size_usd=position.size_usd,
            pnl_usd=pnl,
            won=pnl > 0,
            exit_reason=reason,
            pattern_id=position.metadata.get("pattern_id"),
            strategy_id=position.metadata.get("strategy_id"),
            entry_timestamp=position.entry_timestamp,
            exit_timestamp=timestamp,
        )

        update_result = self.quick_update.process_trade_close(trade_result)

        # Log adaptation if triggered
        if update_result.coin_adaptation:
            logger.info(f"Quick update triggered: {update_result.coin_adaptation}")
```

### Process Flow

```
Trade Closes (Sniper._execute_exit)
    │
    ▼
QuickUpdate.process_trade_close(trade_result)
    │
    ├─► CoinScorer.process_trade_result()
    │       ├─► Update wins/losses/pnl
    │       ├─► Check thresholds
    │       └─► Return CoinAdaptation if triggered
    │
    ├─► PatternLibrary.record_pattern_outcome() (if pattern_id exists)
    │       ├─► Update pattern stats
    │       ├─► Recalculate confidence
    │       └─► Deactivate if confidence < 0.3
    │
    └─► Log activity for audit trail
```

---

## Technical Approach

### Step 1: Create Data Classes

Create `src/models/quick_update.py`:
- `TradeResult` dataclass
- `QuickUpdateResult` dataclass

### Step 2: Implement QuickUpdate Class

Create `src/quick_update.py`:
- Constructor takes CoinScorer, PatternLibrary, Database
- `process_trade_close()` coordinates all updates
- Must be synchronous and fast (<10ms)

### Step 3: Integrate with Sniper

Update `src/sniper.py`:
- Add `quick_update` parameter to constructor
- Call `quick_update.process_trade_close()` in `_execute_exit()`
- Build `TradeResult` from position and exit data

### Step 4: Wire in main.py

Update initialization to create and wire QuickUpdate:
- Create QuickUpdate instance
- Pass to Sniper

### Step 5: Create Unit Tests

Test:
- QuickUpdate processes winning trades
- QuickUpdate processes losing trades
- Coin adaptations trigger correctly
- Pattern confidence updates
- Processing completes in <10ms

---

## Files Created

| File | Purpose |
|------|---------|
| `src/models/quick_update.py` | TradeResult and QuickUpdateResult dataclasses |
| `src/quick_update.py` | QuickUpdate class |
| `tests/test_quick_update.py` | Unit tests |

---

## Files Modified

| File | Change |
|------|--------|
| `src/sniper.py` | Add quick_update parameter, call after exits |
| `src/main.py` | Create and wire QuickUpdate |

---

## Acceptance Criteria

- [x] QuickUpdate class processes trade outcomes
- [x] CoinScorer called for every trade close
- [x] PatternLibrary called when pattern_id present
- [x] Adaptations trigger correctly (blacklist at <30%, etc.)
- [x] Sniper calls QuickUpdate after every exit
- [x] Processing time <10ms per update (achieved ~4-8ms)
- [x] Activity logged for audit trail
- [x] Unit tests pass

---

## Verification

### Unit Test

```bash
python -m pytest tests/test_quick_update.py -v
```

### Integration Test

```python
from src.quick_update import QuickUpdate, TradeResult
from src.coin_scorer import CoinScorer
from src.pattern_library import PatternLibrary
from src.knowledge import KnowledgeBrain
from src.database import Database

# Setup
db = Database("data/test_quick_update.db")
brain = KnowledgeBrain(db)
scorer = CoinScorer(brain, db)
patterns = PatternLibrary(brain)

quick = QuickUpdate(scorer, patterns, db)

# Process a winning trade
result = quick.process_trade_close(TradeResult(
    trade_id="test-001",
    coin="SOL",
    direction="LONG",
    entry_price=100.0,
    exit_price=102.0,
    position_size_usd=50.0,
    pnl_usd=1.0,
    won=True,
    exit_reason="take_profit",
))

print(f"Processed in {result.processing_time_ms:.2f}ms")
print(f"Coin status: {result.new_coin_status}")
print(f"Adaptation: {result.coin_adaptation}")

# Verify coin score updated
score = brain.get_coin_score("SOL")
print(f"SOL score: {score.wins}W {score.losses}L, ${score.total_pnl:.2f}")
```

### Performance Test

```python
import time

# Process 100 trades
start = time.time()
for i in range(100):
    quick.process_trade_close(TradeResult(
        trade_id=f"perf-{i}",
        coin="ETH",
        direction="LONG",
        entry_price=2500.0,
        exit_price=2525.0,
        position_size_usd=50.0,
        pnl_usd=0.5,
        won=True,
        exit_reason="take_profit",
    ))
elapsed = time.time() - start

print(f"100 updates in {elapsed*1000:.1f}ms ({elapsed*10:.2f}ms per update)")
assert elapsed < 1.0, "Should process 100 updates in <1 second"
```

---

## Example Scenarios

### Scenario 1: Winning Trade Updates Score

```
Trade: SOL LONG, +$1.50, take_profit

Before: SOL score = 3W 2L, $4.50 P&L
After:  SOL score = 4W 2L, $6.00 P&L

No adaptation (win rate 67%, above thresholds)
```

### Scenario 2: Losing Trade Triggers Blacklist

```
Trade: SHIB LONG, -$2.00, stop_loss

Before: SHIB score = 1W 4L, -$8.00 P&L (20% win rate)
After:  SHIB score = 1W 5L, -$10.00 P&L (17% win rate)

Adaptation triggered: BLACKLIST
- 5+ trades ✓
- Win rate <30% ✓
- Total P&L <0 ✓
```

### Scenario 3: Pattern Confidence Update

```
Trade: ETH LONG using pattern "momentum_breakout_v1", +$2.00

Before: Pattern confidence = 0.65, 10 uses, 7 wins
After:  Pattern confidence = 0.68, 11 uses, 8 wins

Pattern still active (confidence > 0.3)
```

### Scenario 4: Pattern Deactivation

```
Trade: BTC LONG using pattern "fade_reversal_v1", -$3.00

Before: Pattern confidence = 0.32, 20 uses, 5 wins
After:  Pattern confidence = 0.28, 21 uses, 5 wins

Pattern DEACTIVATED (confidence < 0.3)
```

---

## Completion Notes

### Implementation Summary

**Date:** February 3, 2026

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/models/quick_update.py` | ~95 | TradeResult and QuickUpdateResult dataclasses |
| `src/quick_update.py` | ~300 | QuickUpdate class with post-trade processing |
| `tests/test_quick_update.py` | ~280 | Comprehensive unit tests |

### Files Modified

| File | Changes |
|------|---------|
| `src/sniper.py` | Added `quick_update` parameter, calls QuickUpdate in `_execute_exit()` |
| `src/main.py` | Creates QuickUpdate instance, wires to Sniper |

### Key Implementation Details

1. **TradeResult**: Dataclass with all trade outcome data:
   - trade_id, coin, direction, entry/exit prices
   - pnl_usd, won, exit_reason
   - Optional: pattern_id, strategy_id, timestamps
   - Computed: duration_seconds, return_pct

2. **QuickUpdateResult**: What changed after update:
   - coin_score_updated, pattern_updated
   - coin_adaptation (BLACKLIST, REDUCED, FAVORED, etc.)
   - new_coin_status, new_coin_win_rate
   - processing_time_ms

3. **QuickUpdate.process_trade_close()**: Main entry point:
   - Calls CoinScorer.process_trade_result()
   - Calls PatternLibrary.record_pattern_outcome() (if pattern_id)
   - Logs activity to database
   - Returns QuickUpdateResult

4. **Sniper Integration**: `_execute_exit()` builds TradeResult and calls QuickUpdate

### Performance

- Single update: ~4-8ms (target: <10ms) ✅
- 100 updates: ~430ms (4.3ms per update)
- No I/O blocking in hot path

### Verification

```bash
python3 -m src.quick_update
# Output: All QuickUpdate Tests PASSED!
```

---

## Related

- [TASK-121](./TASK-121.md) - Coin Scoring System (CoinScorer)
- [TASK-122](./TASK-122.md) - Pattern Library (PatternLibrary)
- [TASK-131](./TASK-131.md) - Deep Reflection (uses Quick Update data)
- [AUTONOMOUS-TRADER-SPEC.md](../AUTONOMOUS-TRADER-SPEC.md) - Section 6: Reflection Engine
