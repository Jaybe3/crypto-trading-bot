# TASK-102: Trade Journal

**Status:** COMPLETED
**Created:** February 2, 2026
**Completed:** February 2, 2026
**Priority:** High
**Depends On:** None
**Phase:** Phase 2.1 - Speed Infrastructure

---

## Objective

Create a comprehensive trade journaling system that records full context for every trade - the raw data that feeds the learning system.

---

## Background

Like a trader keeping a detailed journal, the bot needs to record:
- Why it entered (conditions, reasoning, market state)
- What happened during the trade
- Why it exited (stop-loss, take-profit, strategy exit)
- The outcome (P&L, duration)
- Market context (what happened after exit)

This data is what the Reflection Engine analyzes to find patterns and improve.

---

## Specification

### Journal Entry Structure

```python
@dataclass
class JournalEntry:
    # Identity
    id: str
    
    # Entry details
    entry_time: datetime
    entry_price: float
    entry_reason: str           # Human-readable: "Momentum breakout triggered"
    
    # Trade parameters
    coin: str
    direction: str              # "LONG" or "SHORT"
    position_size_usd: float
    stop_loss_price: float
    take_profit_price: float
    
    # Strategy context
    strategy_id: str            # Which strategy
    pattern_id: Optional[str]   # Which pattern (if any)
    condition_id: str           # The trigger condition ID
    
    # Market context at entry
    market_regime: Optional[str]    # "trending", "ranging", "volatile"
    volatility: Optional[float]     # ATR or similar
    funding_rate: Optional[float]   # Exchange funding rate
    cvd: Optional[float]            # Cumulative volume delta
    btc_trend: Optional[str]        # BTC direction (affects alts)
    
    # Timing context
    hour_of_day: int            # 0-23 UTC
    day_of_week: int            # 0-6 (Mon-Sun)
    
    # Exit details (filled when trade closes)
    exit_time: Optional[datetime]
    exit_price: Optional[float]
    exit_reason: Optional[str]      # "stop_loss", "take_profit", "strategy_exit"
    
    # Outcome (filled when trade closes)
    pnl_usd: Optional[float]
    pnl_pct: Optional[float]
    duration_seconds: Optional[int]
    
    # Post-trade context (filled async after exit)
    price_1min_after: Optional[float]
    price_5min_after: Optional[float]
    price_15min_after: Optional[float]
    missed_profit: Optional[float]  # If exited too early, how much left on table
```

### Journal Operations

```python
class TradeJournal:
    def __init__(self, db: Database):
        self.db = db
        self.pending_entries: dict[str, JournalEntry] = {}  # Open trades
        
    def record_entry(self, position: Position, market_context: dict) -> str:
        """Record a new trade entry. Returns entry ID."""
        entry = JournalEntry(
            id=generate_id(),
            entry_time=position.entry_time,
            entry_price=position.entry_price,
            entry_reason=position.reasoning,
            coin=position.coin,
            direction=position.direction,
            position_size_usd=position.size_usd,
            stop_loss_price=position.stop_loss_price,
            take_profit_price=position.take_profit_price,
            strategy_id=position.strategy_id,
            condition_id=position.condition_id,
            hour_of_day=position.entry_time.hour,
            day_of_week=position.entry_time.weekday(),
            # Market context
            market_regime=market_context.get('regime'),
            volatility=market_context.get('volatility'),
            funding_rate=market_context.get('funding_rate'),
            cvd=market_context.get('cvd'),
            btc_trend=market_context.get('btc_trend'),
            # Exit fields null until closed
            exit_time=None,
            exit_price=None,
            exit_reason=None,
            pnl_usd=None,
            pnl_pct=None,
            duration_seconds=None,
        )
        
        self.pending_entries[entry.id] = entry
        self.db.insert_journal_entry(entry)  # Async write
        return entry.id
        
    def record_exit(self, entry_id: str, exit_price: float, exit_time: datetime, 
                    exit_reason: str, pnl_usd: float, pnl_pct: float):
        """Record trade exit and outcome."""
        entry = self.pending_entries.pop(entry_id)
        
        entry.exit_time = exit_time
        entry.exit_price = exit_price
        entry.exit_reason = exit_reason
        entry.pnl_usd = pnl_usd
        entry.pnl_pct = pnl_pct
        entry.duration_seconds = int((exit_time - entry.entry_time).total_seconds())
        
        self.db.update_journal_entry(entry)  # Async write
        
        # Schedule post-trade context capture
        self._schedule_post_trade_capture(entry)
        
    def record_post_trade_context(self, entry_id: str, prices: dict):
        """Called 15 min after exit to record what happened next."""
        # prices = {'1min': 42100, '5min': 42050, '15min': 42200}
        self.db.update_post_trade_context(entry_id, prices)
        
    # Query methods for Reflection Engine
    def get_recent(self, hours: int = 24) -> list[JournalEntry]:
        """Get recent closed trades."""
        
    def get_by_coin(self, coin: str, limit: int = 100) -> list[JournalEntry]:
        """Get trades for a specific coin."""
        
    def get_by_strategy(self, strategy_id: str) -> list[JournalEntry]:
        """Get trades for a specific strategy."""
        
    def get_by_pattern(self, pattern_id: str) -> list[JournalEntry]:
        """Get trades that used a specific pattern."""
```

### Why Capture Post-Trade Prices?

This answers: "Did we exit too early?"

- If we took profit at +1% but price went +5% in next 15 min → Learned: hold winners longer
- If we stopped out at -2% but price recovered to +1% → Learned: stop too tight, or bad entry

This data is gold for the Reflection Engine.

---

## Technical Approach

### Database Schema

```sql
CREATE TABLE trade_journal (
    id TEXT PRIMARY KEY,
    
    -- Entry
    entry_time TIMESTAMP NOT NULL,
    entry_price REAL NOT NULL,
    entry_reason TEXT NOT NULL,
    
    -- Trade params
    coin TEXT NOT NULL,
    direction TEXT NOT NULL,
    position_size_usd REAL NOT NULL,
    stop_loss_price REAL,
    take_profit_price REAL,
    
    -- Strategy context
    strategy_id TEXT,
    pattern_id TEXT,
    condition_id TEXT,
    
    -- Market context
    market_regime TEXT,
    volatility REAL,
    funding_rate REAL,
    cvd REAL,
    btc_trend TEXT,
    
    -- Timing
    hour_of_day INTEGER,
    day_of_week INTEGER,
    
    -- Exit
    exit_time TIMESTAMP,
    exit_price REAL,
    exit_reason TEXT,
    
    -- Outcome
    pnl_usd REAL,
    pnl_pct REAL,
    duration_seconds INTEGER,
    
    -- Post-trade
    price_1min_after REAL,
    price_5min_after REAL,
    price_15min_after REAL,
    missed_profit REAL,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_journal_coin ON trade_journal(coin);
CREATE INDEX idx_journal_strategy ON trade_journal(strategy_id);
CREATE INDEX idx_journal_pattern ON trade_journal(pattern_id);
CREATE INDEX idx_journal_time ON trade_journal(entry_time);
CREATE INDEX idx_journal_exit_reason ON trade_journal(exit_reason);
```

### Async Writes

Journal writes should not block the Sniper. Use a write queue:

```python
class AsyncJournalWriter:
    def __init__(self, db: Database):
        self.db = db
        self.queue = asyncio.Queue()
        
    async def start(self):
        while True:
            entry = await self.queue.get()
            await self.db.write_journal_entry(entry)
            
    def enqueue(self, entry: JournalEntry):
        self.queue.put_nowait(entry)
```

### Post-Trade Capture

Schedule price capture at 1, 5, and 15 minutes after exit:

```python
async def _schedule_post_trade_capture(self, entry: JournalEntry):
    exit_time = entry.exit_time
    
    await asyncio.sleep(60)  # 1 minute
    price_1min = self.market_feed.get_price(entry.coin)
    
    await asyncio.sleep(240)  # 4 more minutes (total 5)
    price_5min = self.market_feed.get_price(entry.coin)
    
    await asyncio.sleep(600)  # 10 more minutes (total 15)
    price_15min = self.market_feed.get_price(entry.coin)
    
    self.record_post_trade_context(entry.id, {
        '1min': price_1min,
        '5min': price_5min,
        '15min': price_15min,
    })
```

---

## Files Created

| File | Purpose |
|------|---------|
| `src/journal.py` | Trade Journal implementation |
| `tests/test_journal.py` | Unit tests |

---

## Files Modified

| File | Change |
|------|--------|
| `src/database.py` | Add journal table and operations |

---

## Acceptance Criteria

- [x] JournalEntry captures all required fields (30+ fields including market context)
- [x] Entry recorded when trade opens (via `record_entry()`)
- [x] Exit recorded when trade closes (via `record_exit()`)
- [x] P&L calculated correctly (tested for wins and losses)
- [x] Duration calculated correctly (`exit_time - entry_time`)
- [x] Post-trade prices captured at 1/5/15 min (async scheduler implemented)
- [x] Query methods return correct data (by coin, strategy, time, exit reason, etc.)
- [x] Writes don't block Sniper (async write queue with background thread)
- [x] Data persists across restarts (SQLite with proper schema)

---

## Verification

```bash
# Test journal entry creation
python -c "
from src.journal import TradeJournal, JournalEntry
from datetime import datetime

journal = TradeJournal()

# Record entry
entry_id = journal.record_entry(
    position=mock_position,
    market_context={'regime': 'trending', 'volatility': 0.02}
)
print(f'Entry recorded: {entry_id}')

# Record exit
journal.record_exit(
    entry_id=entry_id,
    exit_price=42500.0,
    exit_time=datetime.now(),
    exit_reason='take_profit',
    pnl_usd=1.50,
    pnl_pct=0.015
)
print('Exit recorded')

# Query
entries = journal.get_recent(hours=1)
print(f'Recent entries: {len(entries)}')
print(f'Entry: {entries[0]}')
"
```

```bash
# Verify persistence
python -c "
from src.journal import TradeJournal

journal = TradeJournal()
entries = journal.get_recent(hours=24)
print(f'Persisted entries: {len(entries)}')
for e in entries[:5]:
    print(f'  {e.coin} {e.direction} {e.pnl_usd:+.2f}')
"
```

---

## Completion Notes

### Implementation Summary

**Files Created/Modified:**
- `src/journal.py` (~750 lines) - Complete rewrite with full implementation
- `src/database.py` - Added trade_journal table schema and indexes
- `tests/test_journal.py` (~400 lines) - Comprehensive unit tests

### Key Components

1. **MarketContext** - Captures market conditions at entry:
   - Market regime (trending, ranging, volatile)
   - Volatility measure
   - Funding rate, CVD
   - BTC trend and price

2. **JournalEntry** - Complete trade record with 30+ fields:
   - Entry details (time, price, reason)
   - Trade parameters (coin, direction, size, SL/TP)
   - Strategy context (strategy_id, condition_id, pattern_id)
   - Market context at entry
   - Timing context (hour_of_day, day_of_week)
   - Exit details (time, price, reason)
   - Outcome (P&L USD/%, duration)
   - Post-trade prices (1/5/15 min after)
   - Missed profit calculation

3. **JournalDatabase** - SQLite persistence:
   - CRUD operations
   - Query builder with WHERE clauses
   - Aggregate queries for statistics
   - Proper indexing for performance

4. **AsyncWriteQueue** - Non-blocking writes:
   - Background thread processes queue
   - Sniper calls return immediately
   - Flush on shutdown

5. **Post-Trade Capture** - Async price tracking:
   - Captures prices at 1, 5, 15 minutes after exit
   - Calculates "missed profit" for learning
   - Works with or without event loop

### Verification Results

**Unit Tests:** 31/31 passed
- MarketContext (4 tests)
- JournalEntry (5 tests)
- JournalDatabase (4 tests)
- TradeJournal (5 tests)
- Query methods (5 tests)
- Statistics (3 tests)
- Async write queue (1 test)
- Missed profit calculation (4 tests)

**Integration Test:**
- Connected to live Bybit feed
- Entry triggered and recorded with market context
- Journal captured: coin, direction, price, strategy, market regime, BTC trend

### Query Methods for Reflection Engine

```python
# Basic queries
journal.get_recent(hours=24)
journal.get_by_coin('BTC')
journal.get_by_strategy('momentum')
journal.get_by_exit_reason('stop_loss')
journal.get_by_time_of_day(14)  # 2 PM UTC
journal.get_by_day_of_week(0)   # Monday

# Win/loss analysis
journal.get_winners(limit=10)
journal.get_losers(limit=10)
journal.get_early_exits(min_missed_profit=1.0)

# Statistics
journal.get_stats(coin='BTC', hours=24)
journal.get_performance_by_hour()
journal.get_performance_by_day()
journal.get_performance_by_coin()
journal.get_performance_by_exit_reason()
```

### Database Schema

```sql
CREATE TABLE trade_journal (
    id TEXT PRIMARY KEY,
    position_id TEXT NOT NULL,
    -- 25+ columns for full trade context
    -- See src/journal.py for complete schema
);

-- Indexes for fast queries
CREATE INDEX idx_journal_coin ON trade_journal(coin);
CREATE INDEX idx_journal_strategy ON trade_journal(strategy_id);
CREATE INDEX idx_journal_entry_time ON trade_journal(entry_time);
CREATE INDEX idx_journal_exit_reason ON trade_journal(exit_reason);
CREATE INDEX idx_journal_pnl ON trade_journal(pnl_usd);
CREATE INDEX idx_journal_hour ON trade_journal(hour_of_day);
CREATE INDEX idx_journal_day ON trade_journal(day_of_week);
```

### Usage Example

```python
from src.journal import TradeJournal, MarketContext
from src.sniper import Sniper
from src.market_feed import MarketFeed

# Setup with market feed for post-trade capture
feed = MarketFeed(['BTC', 'ETH'], exchange='bybit')
journal = TradeJournal(market_feed=feed)
sniper = Sniper(journal)

# Record entry with market context
ctx = MarketContext(regime='trending', btc_trend='up', volatility=0.02)
journal.record_entry(position, timestamp, market_context=ctx)

# Later, record exit (triggers post-trade capture)
journal.record_exit(position, exit_price, timestamp, 'take_profit', pnl)

# Query for analysis
stats = journal.get_stats(coin='BTC')
by_hour = journal.get_performance_by_hour()
early_exits = journal.get_early_exits()  # Trades where we exited too soon
```

### Notes for Future Tasks

- TASK-130 (Reflection Engine) can use query methods to analyze patterns
- Post-trade price capture helps identify if we're cutting winners short
- Market context enables analysis like "we lose money in volatile markets"
- Hour/day analysis can identify best trading times

---

## Related

- [TASK-101](./TASK-101.md) - Sniper (writes to Journal)
- [TASK-130](./TASK-130.md) - Reflection Engine (reads from Journal)
- [AUTONOMOUS-TRADER-SPEC.md](../AUTONOMOUS-TRADER-SPEC.md) - Full system spec
