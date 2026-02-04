# TASK-112: Strategist → Sniper Handoff

**Status:** COMPLETED
**Created:** February 3, 2026
**Completed:** February 3, 2026
**Priority:** High
**Depends On:** TASK-110 (Strategist), TASK-101 (Sniper)
**Phase:** Phase 2.2 - Strategist Integration

---

## Objective

Wire the Strategist and Sniper components together so that LLM-generated trade conditions flow automatically to the execution engine.

---

## Background

We now have two independent components:

- **Strategist (TASK-110):** Generates `TradeCondition` objects every 2-5 minutes using qwen2.5:14b
- **Sniper (TASK-101):** Executes trades instantly when conditions are triggered

These need to be connected:
```
Strategist.generate_conditions() → [TradeCondition] → Sniper.set_conditions()
```

### Current Issue: Duplicate TradeCondition Classes

There are two `TradeCondition` definitions:
1. `src/models/trade_condition.py` - Created in TASK-110 (uses `trigger_condition`)
2. `src/sniper.py` - Created in TASK-101 (uses `trigger_type`)

This task unifies them and wires the handoff.

---

## Specification

### 1. Unify TradeCondition

Consolidate on the `src/models/trade_condition.py` version as the single source of truth.

**Changes to `src/sniper.py`:**
- Remove local `TradeCondition` class
- Import from `src/models.trade_condition`
- Map `trigger_condition` → `trigger_type` internally if needed (or rename consistently)

**Field Mapping:**
| Strategist (new) | Sniper (old) | Resolution |
|------------------|--------------|------------|
| `trigger_condition` | `trigger_type` | Rename to `trigger_condition` everywhere |
| `valid_until` | `valid_until` | Same |
| `additional_filters` | N/A | Sniper ignores for now |

### 2. Wire Callback

Connect Strategist output to Sniper input:

```python
# In orchestrator/main
strategist.subscribe_conditions(sniper.set_conditions)
```

The Sniper's `set_conditions()` method will receive the list of `TradeCondition` objects directly from the Strategist callback.

### 3. Update Orchestrator (main.py)

Extend `src/main.py` to include Strategist:

```python
class TradingSystem:
    def __init__(self):
        # Existing components
        self.market_feed = MarketFeed(TRADEABLE_COINS)
        self.journal = TradeJournal()
        self.sniper = Sniper(self.journal, initial_balance=INITIAL_BALANCE)

        # New: Add Strategist
        self.llm = LLMInterface()
        self.strategist = Strategist(
            llm=self.llm,
            market_feed=self.market_feed,
            db=Database(),
            interval_seconds=STRATEGIST_INTERVAL,
        )

        # Wire Strategist → Sniper
        self.strategist.subscribe_conditions(self._on_new_conditions)

    def _on_new_conditions(self, conditions: List[TradeCondition]):
        """Handle new conditions from Strategist."""
        logger.info(f"Received {len(conditions)} conditions from Strategist")
        self.sniper.set_conditions(conditions)

    async def start(self):
        # Start all components
        await self.market_feed.connect()
        await self.strategist.start()  # New
        # ... existing startup

    async def stop(self):
        await self.strategist.stop()  # New
        # ... existing shutdown
```

### 4. Configuration

Add to `config/settings.py`:

```python
# Strategist settings
STRATEGIST_INTERVAL = 180  # 3 minutes between generations
STRATEGIST_ENABLED = True  # Can disable for testing
STRATEGIST_MAX_CONDITIONS = 3
STRATEGIST_CONDITION_TTL = 300  # 5 minutes
```

### 5. Condition Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                  CONDITION LIFECYCLE                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Strategist                    Sniper                       │
│  ──────────                    ──────                       │
│                                                             │
│  1. Generate conditions        2. Receive via callback      │
│     every 3 minutes               └─→ set_conditions()      │
│     └─→ [TradeCondition]                                    │
│                                3. Store in active_conditions│
│                                                             │
│                                4. On each price tick:       │
│                                   - Check if triggered      │
│                                   - Execute if yes          │
│                                   - Remove triggered/expired│
│                                                             │
│  5. Next generation:           6. Old conditions replaced   │
│     └─→ [TradeCondition]          by new set               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6. Logging & Observability

Log the handoff for debugging:

```python
def _on_new_conditions(self, conditions: List[TradeCondition]):
    logger.info(f"=== STRATEGIST → SNIPER HANDOFF ===")
    logger.info(f"Conditions received: {len(conditions)}")
    for c in conditions:
        logger.info(f"  {c.direction} {c.coin} @ ${c.trigger_price:,.2f} "
                   f"({c.trigger_condition})")

    # Pass to Sniper
    active_count = self.sniper.set_conditions(conditions)
    logger.info(f"Sniper now watching {active_count} conditions")
```

---

## Technical Approach

### Step 1: Unify TradeCondition

1. Update `src/sniper.py`:
   - Remove `@dataclass class TradeCondition`
   - Add `from src.models.trade_condition import TradeCondition`
   - Rename `trigger_type` → `trigger_condition` in all usages

2. Update `tests/test_sniper.py`:
   - Import TradeCondition from models
   - Update test fixtures

### Step 2: Update Sniper Interface

Ensure `set_conditions()` handles the new TradeCondition format:

```python
def set_conditions(self, conditions: List[TradeCondition]) -> int:
    """Replace all active conditions with new ones from Strategist."""
    self._cleanup_expired_conditions()

    # Clear old, add new
    self.active_conditions.clear()
    for condition in conditions:
        if not condition.is_expired():
            self.active_conditions[condition.id] = condition

    return len(self.active_conditions)
```

### Step 3: Update Orchestrator

1. Import Strategist and LLMInterface
2. Initialize in `TradingSystem.__init__`
3. Wire callback
4. Add to start/stop lifecycle

### Step 4: Add Configuration

Add strategist settings to config with sensible defaults.

### Step 5: Test Integration

Create integration test that verifies end-to-end flow.

---

## Files Modified

| File | Change |
|------|--------|
| `src/sniper.py` | Remove local TradeCondition, import from models, rename trigger_type → trigger_condition |
| `src/main.py` | Add Strategist integration, wire callback, lifecycle management |
| `config/settings.py` | Add STRATEGIST_* settings |
| `tests/test_sniper.py` | Update imports, fix field names |

---

## Files Created

| File | Purpose |
|------|---------|
| `tests/test_handoff.py` | Integration tests for Strategist → Sniper flow |

---

## Acceptance Criteria

- [x] Single TradeCondition class used throughout codebase
- [x] Strategist conditions automatically flow to Sniper
- [x] Sniper executes when conditions trigger
- [x] Handoff logged for observability
- [x] System starts/stops cleanly with all components
- [x] Existing Sniper tests pass with updated imports
- [x] Integration test verifies full flow

---

## Verification

### Unit Test

```bash
# Run sniper tests with updated imports
pytest tests/test_sniper.py -v
```

### Integration Test

```python
# tests/test_handoff.py
import asyncio
from src.strategist import Strategist
from src.sniper import Sniper
from src.market_feed import MarketFeed
from src.journal import TradeJournal
from src.llm_interface import LLMInterface

async def test_handoff():
    """Test conditions flow from Strategist to Sniper."""
    # Setup
    llm = LLMInterface()
    market = MarketFeed(['BTC', 'ETH', 'SOL'])
    journal = TradeJournal()
    sniper = Sniper(journal)
    strategist = Strategist(llm, market)

    # Wire handoff
    received = []
    def track_conditions(conditions):
        received.extend(conditions)
        sniper.set_conditions(conditions)

    strategist.subscribe_conditions(track_conditions)

    # Start components
    await market.connect()
    await asyncio.sleep(3)  # Let prices populate

    # Generate conditions
    conditions = await strategist.generate_conditions()

    # Verify handoff
    assert len(received) == len(conditions)
    assert len(sniper.active_conditions) == len(conditions)

    print(f"Handoff successful: {len(conditions)} conditions")

asyncio.run(test_handoff())
```

### Manual Verification

```bash
# Start full system and watch logs
python src/main.py

# Should see logs like:
# [INFO] Strategist: Generated 2 conditions
# [INFO] === STRATEGIST → SNIPER HANDOFF ===
# [INFO] Conditions received: 2
# [INFO]   LONG SOL @ $143.50 (ABOVE)
# [INFO]   LONG ETH @ $2,855.00 (ABOVE)
# [INFO] Sniper now watching 2 conditions
```

---

## Completion Notes

### Implementation Summary

**Date:** February 3, 2026

### Files Modified

| File | Changes |
|------|---------|
| `src/sniper.py` | Removed local TradeCondition class, import from models, updated `trigger_type` → `trigger_condition`, fixed percentage calculations (2.0 = 2% not 0.02) |
| `src/main.py` | Added Strategist initialization, wired `_on_new_conditions` callback, added lifecycle management |
| `config/settings.py` | Added `STRATEGIST_ENABLED`, `STRATEGIST_INTERVAL`, `STRATEGIST_MAX_CONDITIONS`, `STRATEGIST_CONDITION_TTL` |
| `tests/test_sniper.py` | Updated imports, fixed field names and percentage format |

### Files Created

| File | Purpose |
|------|---------|
| `tests/test_handoff.py` | Integration tests for Strategist → Sniper flow (7 test cases) |

### Key Changes

1. **Unified TradeCondition**: Single class in `src/models/trade_condition.py` used everywhere
2. **Field Renamed**: `trigger_type` → `trigger_condition` for consistency
3. **Percentage Format**: Standardized on `2.0` = 2% (not `0.02`)
4. **Callback Wiring**: `strategist.subscribe_conditions(self._on_new_conditions)`
5. **Handoff Logging**: Clear log output showing conditions flowing to Sniper

### Verification

```bash
# Test handoff
python3 -c "
from src.sniper import Sniper
from src.models.trade_condition import TradeCondition
from src.journal import TradeJournal
from src.market_feed import PriceTick

journal = TradeJournal()
sniper = Sniper(journal)
condition = TradeCondition(
    coin='SOL', direction='LONG', trigger_price=140.00,
    trigger_condition='ABOVE', stop_loss_pct=2.0, take_profit_pct=1.5,
    position_size_usd=50.0, reasoning='Test', strategy_id='test'
)
sniper.add_condition(condition)
tick = PriceTick(coin='SOL', price=141.00, timestamp=1000, volume_24h=0, change_24h=0)
sniper.on_price_tick(tick)
print(f'Position opened: {len(sniper.open_positions) == 1}')
"
```

### Data Flow

```
Strategist (every 3 min)
    │ generate_conditions()
    ▼
[TradeCondition objects]
    │ _notify_callbacks()
    ▼
TradingSystem._on_new_conditions()
    │ logs handoff
    ▼
Sniper.set_conditions()
    │ stores conditions
    ▼
on_price_tick()
    │ checks triggers
    ▼
_execute_entry() when triggered
```

---

## Related

- [TASK-110](./TASK-110.md) - Strategist Component (generates conditions)
- [TASK-101](./TASK-101.md) - Sniper Execution Engine (receives conditions)
- [TASK-103](./TASK-103.md) - Feed → Sniper → Journal Integration
- [AUTONOMOUS-TRADER-SPEC.md](../AUTONOMOUS-TRADER-SPEC.md) - Full system spec
