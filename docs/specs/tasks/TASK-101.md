# TASK-101: Sniper Execution Engine

**Status:** COMPLETED
**Created:** February 2, 2026
**Completed:** February 2, 2026
**Priority:** High
**Depends On:** TASK-100 (WebSocket Market Data Feed)
**Phase:** Phase 2.1 - Speed Infrastructure

---

## Objective

Create a fast execution engine that watches for trigger conditions and executes trades instantly - no LLM in the execution path.

---

## Background

Current bot has LLM make decisions on every cycle (30s). By the time it decides, the opportunity is gone.

The Sniper separates decision from execution:
- **Strategist (LLM):** Sets conditions periodically ("Buy SOL if > $142.50")
- **Sniper (Python):** Watches prices, executes instantly when condition triggers

This removes LLM latency from the critical path.

---

## Specification

### Trade Conditions

```python
@dataclass
class TradeCondition:
    id: str                                    # Unique identifier
    coin: str                                  # "SOL", "BTC", etc.
    direction: Literal["LONG", "SHORT"]        # Trade direction
    trigger_price: float                       # Price that triggers entry
    trigger_type: Literal["ABOVE", "BELOW"]    # Trigger when price goes above/below
    stop_loss_pct: float                       # Stop loss as % (e.g., 0.02 = 2%)
    take_profit_pct: float                     # Take profit as % (e.g., 0.015 = 1.5%)
    position_size_usd: float                   # How much to trade
    strategy_id: str                           # Which strategy created this
    reasoning: str                             # Why (for journaling)
    valid_until: datetime                      # Expiration time
    created_at: datetime                       # When condition was set
```

### Open Positions

```python
@dataclass
class Position:
    id: str
    coin: str
    direction: str
    entry_price: float
    entry_time: datetime
    size_usd: float
    stop_loss_price: float
    take_profit_price: float
    condition_id: str         # Which condition triggered this
    strategy_id: str
    reasoning: str
    current_price: float      # Updated on each tick
    unrealized_pnl: float     # Updated on each tick
```

### Sniper Behavior

**On each price tick:**
1. Check active conditions → Execute if triggered
2. Check open positions → Exit if stop-loss or take-profit hit

**Key constraint:** No async operations in the hot path. Must be synchronous and fast.

```python
class Sniper:
    def __init__(self, journal: TradeJournal):
        self.active_conditions: dict[str, TradeCondition] = {}
        self.open_positions: dict[str, Position] = {}
        self.journal = journal
        
    def set_conditions(self, conditions: list[TradeCondition]):
        """Called by Strategist with new conditions."""
        # Clear expired, add new
        self.active_conditions = {c.id: c for c in conditions if c.valid_until > now()}
        
    def on_price_tick(self, coin: str, price: float, timestamp: int):
        """Called by MarketFeed on every price update. MUST BE FAST."""
        # Check conditions
        self._check_entry_conditions(coin, price, timestamp)
        # Check positions
        self._check_exit_conditions(coin, price, timestamp)
        
    def _check_entry_conditions(self, coin: str, price: float, timestamp: int):
        """Check if any condition triggers entry."""
        for cond in self.active_conditions.values():
            if cond.coin != coin:
                continue
            if self._is_triggered(cond, price):
                self._execute_entry(cond, price, timestamp)
                
    def _check_exit_conditions(self, coin: str, price: float, timestamp: int):
        """Check if any position hits stop-loss or take-profit."""
        for pos in list(self.open_positions.values()):
            if pos.coin != coin:
                continue
            pos.current_price = price
            pos.unrealized_pnl = self._calc_pnl(pos, price)
            
            if self._hit_stop_loss(pos, price):
                self._execute_exit(pos, price, timestamp, "stop_loss")
            elif self._hit_take_profit(pos, price):
                self._execute_exit(pos, price, timestamp, "take_profit")
```

### Paper Trading Execution

For paper trading, "execution" means:
1. Record the trade in local state
2. Log to Trade Journal
3. Update simulated balance

```python
def _execute_entry(self, condition: TradeCondition, price: float, timestamp: int):
    """Open a paper position."""
    position = Position(
        id=generate_id(),
        coin=condition.coin,
        direction=condition.direction,
        entry_price=price,
        entry_time=datetime.fromtimestamp(timestamp / 1000),
        size_usd=condition.position_size_usd,
        stop_loss_price=self._calc_stop_loss(price, condition),
        take_profit_price=self._calc_take_profit(price, condition),
        condition_id=condition.id,
        strategy_id=condition.strategy_id,
        reasoning=condition.reasoning,
        current_price=price,
        unrealized_pnl=0,
    )
    
    self.open_positions[position.id] = position
    del self.active_conditions[condition.id]  # Condition consumed
    
    # Journal the entry
    self.journal.record_entry(position, timestamp)
    
def _execute_exit(self, position: Position, price: float, timestamp: int, reason: str):
    """Close a paper position."""
    pnl = self._calc_pnl(position, price)
    
    # Journal the exit
    self.journal.record_exit(position, price, timestamp, reason, pnl)
    
    del self.open_positions[position.id]
```

---

## Technical Approach

### Performance Requirements

- `on_price_tick` must complete in < 1ms
- No database writes in the hot path
- No network calls in the hot path
- Journal writes are queued for async processing

### Risk Limits (Enforced by Sniper)

| Limit | Value | Enforcement |
|-------|-------|-------------|
| Max positions | 5 | Reject new entries if at limit |
| Max per coin | 1 | Only one position per coin |
| Max exposure | 10% of balance | Check before entry |

### State Management

Sniper maintains in-memory state:
- Active conditions (set by Strategist)
- Open positions (entries pending exit)
- Simulated balance (for paper trading)

State is persisted to database periodically (every 10s) and on shutdown.

---

## Files Created

| File | Purpose |
|------|---------|
| `src/sniper.py` | Sniper execution engine |
| `tests/test_sniper.py` | Unit tests |

---

## Files Modified

| File | Change |
|------|--------|
| `src/market_feed.py` | Wire up Sniper as price callback |

---

## Acceptance Criteria

- [x] Sniper receives price ticks from MarketFeed (via `subscribe_price` callback)
- [x] Executes entry when condition triggers (ABOVE/BELOW logic)
- [x] Executes exit on stop-loss (tested for LONG and SHORT)
- [x] Executes exit on take-profit (tested for LONG and SHORT)
- [x] Respects position limits (MAX_POSITIONS=5, MAX_PER_COIN=1, MAX_EXPOSURE=10%)
- [x] Logs all executions to Journal (`record_entry`/`record_exit`)
- [x] `on_price_tick` completes in < 1ms (measured: 0.0045ms average)
- [x] Handles condition expiration (`_cleanup_expired_conditions`)
- [x] State survives restart (persistence via `save_state`/`load_state`)

---

## Verification

```bash
# Test condition triggering
python -c "
from src.sniper import Sniper, TradeCondition
from src.journal import TradeJournal
from datetime import datetime, timedelta

journal = TradeJournal()
sniper = Sniper(journal)

# Set a condition
condition = TradeCondition(
    id='test-1',
    coin='BTC',
    direction='LONG',
    trigger_price=42000.0,
    trigger_type='ABOVE',
    stop_loss_pct=0.02,
    take_profit_pct=0.015,
    position_size_usd=100.0,
    strategy_id='test',
    reasoning='Test condition',
    valid_until=datetime.now() + timedelta(minutes=5),
    created_at=datetime.now()
)
sniper.set_conditions([condition])

# Simulate price tick below trigger - should not execute
sniper.on_price_tick('BTC', 41999.0, int(datetime.now().timestamp() * 1000))
print(f'Positions after 41999: {len(sniper.open_positions)}')  # Should be 0

# Simulate price tick above trigger - should execute
sniper.on_price_tick('BTC', 42001.0, int(datetime.now().timestamp() * 1000))
print(f'Positions after 42001: {len(sniper.open_positions)}')  # Should be 1
"
```

```bash
# Test stop-loss
python -c "
from src.sniper import Sniper
from src.journal import TradeJournal
# ... setup position at 42000 with 2% stop loss (stop at 41160)

# Simulate price drop to stop
sniper.on_price_tick('BTC', 41100.0, timestamp)
print(f'Positions after stop: {len(sniper.open_positions)}')  # Should be 0
print(f'Journal entries: {len(journal.entries)}')  # Should show exit
"
```

```bash
# Benchmark tick processing speed
python -c "
import time
from src.sniper import Sniper
from src.journal import TradeJournal

sniper = Sniper(TradeJournal())
# Add 5 conditions, 3 positions

start = time.perf_counter()
for _ in range(10000):
    sniper.on_price_tick('BTC', 42000.0, int(time.time() * 1000))
elapsed = time.perf_counter() - start

print(f'10000 ticks in {elapsed:.3f}s')
print(f'Per tick: {elapsed/10000*1000:.3f}ms')  # Should be < 1ms
"
```

---

## Completion Notes

### Implementation Summary

**Files Created:**
- `src/sniper.py` (~500 lines) - Sniper execution engine
- `src/journal.py` (~200 lines) - TradeJournal stub (full implementation in TASK-102)
- `tests/test_sniper.py` (~500 lines) - Comprehensive unit tests

### Key Design Decisions

1. **No I/O in Hot Path**: `on_price_tick()` performs no disk or network operations. State persistence is done separately via `save_state()`.

2. **Risk Limits Enforced at Entry**:
   - MAX_POSITIONS = 5
   - MAX_PER_COIN = 1
   - MAX_EXPOSURE_PCT = 10%
   Checked in `_can_open_position()` before every entry.

3. **Callback System**: Execution events emitted via `subscribe()` for UI/monitoring integration.

4. **LONG/SHORT Support**: Full support for both directions with correct P&L, stop-loss, and take-profit calculations.

5. **State Persistence**: JSON-based save/load for restart recovery. Conditions and positions serializable.

### Verification Results

**Unit Tests:** 27/27 passed
- TradeCondition creation, expiration, serialization
- Sniper initialization
- Condition management (add, set, clear)
- Entry triggering (ABOVE, BELOW)
- Exit logic (stop-loss, take-profit for LONG/SHORT)
- P&L calculations
- Risk limit enforcement
- Callbacks

**Performance Test:**
```
10000 ticks in 0.012s
Per tick: 0.0012ms  (833x faster than 1ms requirement)
```

**Integration Test (15 seconds with live Bybit feed):**
- Ticks processed: 428
- Avg tick time: 0.0045ms
- Entry triggered successfully
- Position tracked with real-time unrealized P&L
- Journal recorded entry

### Data Classes

```python
@dataclass
class TradeCondition:
    id: str                    # Unique identifier
    coin: str                  # "SOL", "BTC", etc.
    direction: "LONG"|"SHORT"  # Trade direction
    trigger_price: float       # Entry trigger
    trigger_type: "ABOVE"|"BELOW"
    stop_loss_pct: float       # e.g., 0.02 = 2%
    take_profit_pct: float     # e.g., 0.015 = 1.5%
    position_size_usd: float
    strategy_id: str
    reasoning: str
    valid_until: datetime
    created_at: datetime

@dataclass
class Position:
    id: str
    coin: str
    direction: str
    entry_price: float
    entry_time: datetime
    size_usd: float
    stop_loss_price: float     # Absolute price
    take_profit_price: float   # Absolute price
    condition_id: str
    strategy_id: str
    reasoning: str
    current_price: float       # Updated each tick
    unrealized_pnl: float      # Updated each tick
```

### Usage Example

```python
from src.market_feed import MarketFeed
from src.sniper import Sniper, TradeCondition
from src.journal import TradeJournal
from datetime import datetime, timedelta

# Setup
journal = TradeJournal()
sniper = Sniper(journal, initial_balance=10000.0)
feed = MarketFeed(['BTC', 'ETH', 'SOL'], exchange='bybit')

# Wire sniper to feed
feed.subscribe_price(sniper.on_price_tick)

# Set condition (from Strategist)
condition = TradeCondition(
    id='btc-breakout',
    coin='BTC',
    direction='LONG',
    trigger_price=80000.0,
    trigger_type='ABOVE',
    stop_loss_pct=0.02,
    take_profit_pct=0.015,
    position_size_usd=500.0,
    strategy_id='momentum',
    reasoning='Breakout above resistance',
    valid_until=datetime.now() + timedelta(hours=1),
)
sniper.add_condition(condition)

# Start feed - sniper executes automatically
await feed.connect()
```

### Notes for Future Tasks

- TASK-102 (Trade Journal) will expand the stub `src/journal.py` with database persistence and query capabilities
- TASK-110 (Strategist) will call `sniper.set_conditions()` to manage active conditions
- Dashboard can subscribe to execution events via `sniper.subscribe()`

---

## Related

- [TASK-100](./TASK-100.md) - WebSocket Feed (dependency)
- [TASK-102](./TASK-102.md) - Trade Journal (used by Sniper)
- [TASK-110](./TASK-110.md) - Strategist (sets conditions)
- [AUTONOMOUS-TRADER-SPEC.md](../AUTONOMOUS-TRADER-SPEC.md) - Full system spec
