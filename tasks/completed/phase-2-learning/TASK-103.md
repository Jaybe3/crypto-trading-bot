# TASK-103: Integration - Feed → Sniper → Journal

**Status:** COMPLETED
**Created:** February 2, 2026
**Completed:** February 2, 2026
**Priority:** High
**Depends On:** TASK-100, TASK-101, TASK-102
**Phase:** Phase 2.1 - Speed Infrastructure

---

## Objective

Wire together MarketFeed, Sniper, and TradeJournal into a working system that can receive real-time prices and execute paper trades.

---

## Background

With the three core components built, we need to:
1. Connect them together
2. Create the main loop
3. Verify end-to-end functionality
4. Establish baseline performance metrics

This is the foundation everything else builds on.

---

## Specification

### System Flow

```
┌─────────────────┐
│  Binance WS     │
└────────┬────────┘
         │ Price ticks
         ▼
┌─────────────────┐
│  MarketFeed     │
└────────┬────────┘
         │ on_price_tick()
         ▼
┌─────────────────┐      ┌─────────────────┐
│    Sniper       │─────>│  TradeJournal   │
└─────────────────┘      └────────┬────────┘
                                  │ async write
                                  ▼
                         ┌─────────────────┐
                         │    SQLite DB    │
                         └─────────────────┘
```

### Main Entry Point

```python
# src/main.py

import asyncio
from src.market_feed import MarketFeed
from src.sniper import Sniper
from src.journal import TradeJournal
from src.database import Database

class TradingSystem:
    def __init__(self):
        self.db = Database()
        self.journal = TradeJournal(self.db)
        self.sniper = Sniper(self.journal)
        self.market_feed = MarketFeed(coins=TRADEABLE_COINS)
        
    async def start(self):
        """Start the trading system."""
        # Wire up components
        self.market_feed.subscribe_price(self.sniper.on_price_tick)
        
        # Start market feed (connects to Binance)
        await self.market_feed.connect()
        
        # Start journal writer
        await self.journal.start_writer()
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            self._log_status()
            
    def _log_status(self):
        """Periodic status log."""
        print(f"Conditions: {len(self.sniper.active_conditions)} | "
              f"Positions: {len(self.sniper.open_positions)} | "
              f"Feed: {'OK' if self.market_feed.connected else 'DISCONNECTED'}")
              
    async def stop(self):
        """Graceful shutdown."""
        await self.market_feed.disconnect()
        await self.journal.flush()  # Write pending entries

async def main():
    system = TradingSystem()
    try:
        await system.start()
    except KeyboardInterrupt:
        await system.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### Test Mode

For testing without waiting for real market triggers:

```python
class TradingSystem:
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        ...
        
    async def inject_test_condition(self, condition: TradeCondition):
        """For testing: manually add a condition."""
        self.sniper.set_conditions([condition])
        
    async def inject_test_price(self, coin: str, price: float):
        """For testing: manually send a price tick."""
        self.sniper.on_price_tick(coin, price, int(time.time() * 1000))
```

### Configuration

```python
# config/settings.py

TRADEABLE_COINS = [
    # Tier 1 - Blue chips
    "BTC", "ETH", "SOL", "BNB", "XRP",
    # Tier 2 - High volume
    "DOGE", "ADA", "AVAX", "LINK", "DOT",
    "MATIC", "UNI", "ATOM", "LTC", "BCH",
    # Tier 3 - Volatile (selected for movement)
    "PEPE", "SHIB", "FLOKI", "WIF", "BONK",
]

# Risk limits
MAX_POSITIONS = 5
MAX_POSITION_PER_COIN = 1
MAX_EXPOSURE_PCT = 0.10  # 10% of balance
DEFAULT_STOP_LOSS_PCT = 0.02  # 2%
DEFAULT_TAKE_PROFIT_PCT = 0.015  # 1.5%

# Paper trading
INITIAL_BALANCE = 1000.0  # Starting paper balance
```

### Health Monitoring

```python
class HealthMonitor:
    def __init__(self, system: TradingSystem):
        self.system = system
        self.last_tick_time = None
        self.tick_count = 0
        
    def on_tick(self):
        self.last_tick_time = time.time()
        self.tick_count += 1
        
    @property
    def is_healthy(self) -> bool:
        if self.last_tick_time is None:
            return False
        # Unhealthy if no tick in 5 seconds
        return time.time() - self.last_tick_time < 5
        
    def get_stats(self) -> dict:
        return {
            "healthy": self.is_healthy,
            "last_tick": self.last_tick_time,
            "tick_count": self.tick_count,
            "active_conditions": len(self.system.sniper.active_conditions),
            "open_positions": len(self.system.sniper.open_positions),
        }
```

---

## Technical Approach

### Startup Sequence

1. Initialize Database
2. Load any persisted state (open positions, balance)
3. Initialize TradeJournal
4. Initialize Sniper
5. Initialize MarketFeed
6. Wire callbacks
7. Connect to Binance
8. Enter main loop

### Shutdown Sequence

1. Stop accepting new conditions
2. Cancel pending conditions
3. Close open positions at market (or leave for restart)
4. Flush journal writes
5. Disconnect WebSocket
6. Save state

### Error Handling

| Error | Response |
|-------|----------|
| WebSocket disconnect | Auto-reconnect, pause trading until reconnected |
| Database error | Log, retry, alert if persistent |
| Invalid price data | Skip tick, log warning |
| Sniper exception | Log, don't crash main loop |

---

## Files Created

| File | Purpose |
|------|---------|
| `src/main.py` | New main entry point |
| `config/settings.py` | Configuration constants |
| `tests/test_integration.py` | End-to-end tests |

---

## Files Modified

| File | Change |
|------|--------|
| `src/market_feed.py` | Add connected property, disconnect method |
| `src/sniper.py` | Add state persistence on shutdown |
| `src/journal.py` | Add flush method for clean shutdown |

---

## Acceptance Criteria

- [x] System starts and connects to Binance/Bybit
- [x] Price ticks flow through to Sniper
- [x] Can inject test condition and see it trigger
- [x] Triggered trades are journaled
- [x] Stop-loss triggers correctly
- [x] Take-profit triggers correctly
- [x] System handles WebSocket disconnect gracefully
- [x] Clean shutdown saves state
- [x] System restarts and recovers state
- [x] Health monitor reports accurate status
- [x] Performance exceeds target (647,540 ticks/second vs 10,000 target)

---

## Verification

### Basic Flow Test

```bash
# Start system and verify it connects
python src/main.py &
sleep 10

# Check health
curl http://localhost:8080/health  # If dashboard running
# Or check logs for "Connected to Binance"
```

### End-to-End Test

```bash
python -c "
import asyncio
from src.main_v2 import TradingSystem
from src.sniper import TradeCondition
from datetime import datetime, timedelta

async def test():
    system = TradingSystem(test_mode=True)
    await system.start_components()  # Don't enter main loop
    
    # Inject a condition
    condition = TradeCondition(
        id='test-e2e',
        coin='BTC',
        direction='LONG',
        trigger_price=42000.0,
        trigger_type='ABOVE',
        stop_loss_pct=0.02,
        take_profit_pct=0.015,
        position_size_usd=100.0,
        strategy_id='test',
        reasoning='E2E test',
        valid_until=datetime.now() + timedelta(minutes=5),
        created_at=datetime.now()
    )
    await system.inject_test_condition(condition)
    print(f'Conditions: {len(system.sniper.active_conditions)}')
    
    # Inject price below trigger
    await system.inject_test_price('BTC', 41999.0)
    print(f'Positions after 41999: {len(system.sniper.open_positions)}')
    
    # Inject price above trigger - should open position
    await system.inject_test_price('BTC', 42001.0)
    print(f'Positions after 42001: {len(system.sniper.open_positions)}')
    
    # Inject take-profit price
    await system.inject_test_price('BTC', 42631.0)  # +1.5%
    print(f'Positions after TP: {len(system.sniper.open_positions)}')
    
    # Check journal
    entries = system.journal.get_recent(hours=1)
    print(f'Journal entries: {len(entries)}')
    if entries:
        print(f'P&L: {entries[0].pnl_usd}')
    
    await system.stop()

asyncio.run(test())
"
```

### Performance Test

```bash
python -c "
import asyncio
import time
from src.main_v2 import TradingSystem

async def test():
    system = TradingSystem(test_mode=True)
    await system.start_components()
    
    # Measure tick processing speed
    start = time.perf_counter()
    for i in range(10000):
        await system.inject_test_price('BTC', 42000.0 + i * 0.01)
    elapsed = time.perf_counter() - start
    
    print(f'10000 ticks in {elapsed:.3f}s')
    print(f'Per tick: {elapsed/10000*1000:.3f}ms')
    print(f'Ticks/second: {10000/elapsed:.0f}')
    
    await system.stop()

asyncio.run(test())
"

# Target: > 10,000 ticks/second (< 0.1ms per tick)
```

### Stability Test

```bash
# Run for 1 hour, check for crashes
timeout 3600 python src/main.py

# Check logs for errors
grep -i error logs/trading.log
grep -i exception logs/trading.log
```

---

## Completion Notes

### Implementation Summary

**Files Created:**
- `config/settings.py` (~80 lines) - Central configuration for trading bot
- `src/main.py` (~477 lines) - Main TradingSystem orchestrator with HealthMonitor
- `tests/test_integration.py` (~500 lines) - Comprehensive end-to-end tests

### Key Components

1. **TradingSystem** - Main orchestrator that wires together all components:
   - Lifecycle management (start, stop)
   - Component initialization in correct order
   - Callback wiring (Feed → Sniper → Journal)
   - Test mode for isolated testing with `inject_condition()` and `inject_price()`
   - Supports custom `db_path` and `state_path` for test isolation

2. **HealthMonitor** - Monitors system health:
   - Tracks tick count and throughput
   - Detects stale data (no tick in 5 seconds)
   - Reports system statistics
   - Tracks last price per coin

3. **Configuration** (`config/settings.py`):
   - 20 tradeable coins across 3 tiers
   - Risk limits (MAX_POSITIONS=5, MAX_EXPOSURE=10%)
   - Default SL/TP percentages
   - Path configurations

### Verification Results

**Integration Tests:** 16/16 passed
- TestHealthMonitor (5 tests)
- TestTradingSystemInit (2 tests)
- TestTradingSystemComponents (2 tests)
- TestEndToEnd (4 tests) - condition trigger, stop-loss, take-profit, full cycle
- TestPerformance (1 test)
- TestStatePersistence (1 test)
- TestGetStatus (1 test)

**Performance Results:**
- 10,000 ticks processed in 0.015s
- Per tick: 0.0015ms (target was < 0.1ms)
- Throughput: 647,540 ticks/second (target was > 10,000)
- **65x faster than requirement**

### System Flow

```
┌─────────────────┐
│ Bybit/Binance   │
│   WebSocket     │
└────────┬────────┘
         │ Price ticks
         ▼
┌─────────────────┐
│   MarketFeed    │
└────────┬────────┘
         │ callbacks
    ┌────┴────┐
    ▼         ▼
┌───────┐  ┌─────────────┐
│Health │  │   Sniper    │
│Monitor│  └──────┬──────┘
└───────┘         │ record trades
                  ▼
          ┌─────────────┐
          │TradeJournal │
          └──────┬──────┘
                 │ async write
                 ▼
          ┌─────────────┐
          │   SQLite    │
          └─────────────┘
```

### Usage Example

```python
# Production mode
system = TradingSystem(exchange="bybit")
await system.start()  # Blocks until shutdown

# Test mode
system = TradingSystem(test_mode=True, coins=["BTC"])
await system.start_components()
system.inject_condition(condition)
system.inject_price("BTC", 50000.0)
await system.stop()
```

### Notes

- Multi-exchange support: Bybit (primary), Binance (fallback)
- Graceful shutdown: saves state, flushes journal, disconnects WebSocket
- State persistence: positions and balance survive restarts
- Test isolation: each test uses temp directories for DB and state

---

## Milestone

**Phase 2.1 Complete when:**
- [x] TASK-100 ✓ (Market Feed)
- [x] TASK-101 ✓ (Sniper)
- [x] TASK-102 ✓ (Journal)
- [x] TASK-103 ✓ (Integration)
- [x] System can execute paper trades within 100ms of price trigger (achieved 0.0015ms)

**PHASE 2.1 COMPLETE** - All 4 tasks verified and passing.

---

## Related

- [TASK-100](./TASK-100.md) - WebSocket Market Feed
- [TASK-101](./TASK-101.md) - Sniper
- [TASK-102](./TASK-102.md) - Trade Journal
- [TASK-110](./TASK-110.md) - Strategist (next phase)
- [PHASE-2-INDEX.md](../PHASE-2-INDEX.md) - Phase overview
