# TASK-110: Strategist Component

**Status:** COMPLETED
**Created:** February 3, 2026
**Completed:** February 3, 2026
**Priority:** High
**Depends On:** TASK-100 (MarketFeed), TASK-200 (LLM Config)
**Phase:** Phase 2.2 - Strategist Integration

---

## Objective

Create the Strategist component that periodically analyzes market conditions using `qwen2.5:14b` and generates trade conditions for the Sniper to watch. The Strategist does NOT execute trades - it only sets the conditions.

---

## Background

The current bot has the LLM making trade decisions on every cycle (30 seconds). This creates problems:
- LLM latency (5-20 seconds) delays execution
- Can't capture fast market moves
- Decisions based on stale data by execution time

The new architecture separates concerns:
- **Strategist** (this task): Thinks slow, generates conditions every 2-5 minutes
- **Sniper** (TASK-101): Acts fast, executes instantly when conditions are met

This allows the system to capture sub-second price moves while still using LLM intelligence for strategy.

---

## Specification

### Core Behavior

1. **Periodic Execution**: Runs every 2-5 minutes (configurable via `STRATEGIST_INTERVAL_SECONDS`)
2. **Reads Market State**: Gets current prices, volatility, and trends from MarketFeed
3. **Reads Knowledge**: Gets active rules, coin scores, patterns from Knowledge Brain (or simplified version initially)
4. **Generates Conditions**: Uses LLM to create specific trade conditions
5. **Outputs to Sniper**: Passes `TradeCondition` objects for Sniper to watch
6. **Logs Everything**: Records reasoning for each condition (for reflection later)

### TradeCondition Output Format

```python
@dataclass
class TradeCondition:
    """A specific condition for Sniper to watch and execute."""
    id: str                          # Unique ID (uuid)
    coin: str                        # e.g., "SOL", "ETH"
    direction: Literal["LONG", "SHORT"]
    trigger_price: float             # Price that triggers entry
    trigger_condition: Literal["ABOVE", "BELOW"]  # ABOVE for breakout, BELOW for dip
    stop_loss_pct: float             # e.g., 2.0 for 2%
    take_profit_pct: float           # e.g., 1.5 for 1.5%
    position_size_usd: float         # e.g., 50.0
    reasoning: str                   # Why this trade (logged)
    strategy_id: str                 # Which strategy/pattern this came from
    created_at: datetime
    valid_until: datetime            # Condition expires (default: 5 minutes)
    additional_filters: Optional[dict] = None  # Future: CVD, volume filters
```

### Input Context for LLM

The Strategist gathers this context before querying the LLM:

```python
context = {
    "market_state": {
        "prices": {"BTC": 42500.0, "ETH": 2850.0, "SOL": 142.30, ...},
        "changes_1h": {"BTC": 0.5, "ETH": -0.2, "SOL": 2.1, ...},
        "changes_24h": {"BTC": 1.2, "ETH": -1.5, "SOL": 5.3, ...},
        "volatility": {"BTC": "low", "ETH": "medium", "SOL": "high"},
    },
    "knowledge": {
        "good_coins": ["SOL", "ETH"],      # High win rate coins
        "avoid_coins": ["AXS", "SAND"],    # Blacklisted or poor performers
        "active_rules": [                   # From Knowledge Brain
            {"id": 1, "rule": "Don't trade low volatility"},
            {"id": 2, "rule": "SOL works well on momentum breakouts"},
        ],
        "winning_patterns": [
            "Momentum breakout with volume",
            "Support bounce after pullback",
        ],
    },
    "account": {
        "balance_usd": 500.0,
        "open_positions": [],
        "recent_pnl_24h": 12.50,
    },
    "recent_performance": {
        "win_rate_24h": 0.58,
        "total_trades_24h": 12,
    },
}
```

### LLM Prompt Structure

```
You are the Strategist for an autonomous trading bot. Your job is to set up trade conditions for the Sniper to watch.

CURRENT MARKET STATE:
{market_state}

YOUR LEARNED KNOWLEDGE:
- Coins that work for us: {good_coins}
- Coins to AVOID: {avoid_coins}
- Active rules: {active_rules}
- Winning patterns: {winning_patterns}

ACCOUNT STATE:
- Balance: ${balance}
- Open positions: {positions}
- 24h P&L: ${pnl_24h}

RECENT PERFORMANCE:
- Win rate (24h): {win_rate}%
- Total trades: {trade_count}

YOUR TASK:
Generate 0-3 trade conditions for the Sniper to watch. Each condition should be a specific, actionable setup.

RULES:
1. Only suggest coins NOT in the avoid list
2. Position size must be $20-$100 (max $100)
3. Stop-loss should be 1-3%
4. Take-profit should be 1-2%
5. If market conditions are unfavorable, output NO_TRADES

OUTPUT FORMAT (JSON):
{
    "conditions": [
        {
            "coin": "SOL",
            "direction": "LONG",
            "trigger_price": 143.50,
            "trigger_condition": "ABOVE",
            "stop_loss_pct": 2.0,
            "take_profit_pct": 1.5,
            "position_size_usd": 50,
            "reasoning": "Momentum breakout setup - SOL showing strength, looking for break above resistance",
            "strategy_id": "momentum_breakout"
        }
    ],
    "market_assessment": "Moderate volatility, SOL showing relative strength",
    "no_trade_reason": null
}

If no good setups, return:
{
    "conditions": [],
    "market_assessment": "Low volatility across all coins",
    "no_trade_reason": "No clear setups - market choppy"
}
```

### Strategist Class Interface

```python
class Strategist:
    """LLM-powered strategy generator. Runs periodically, not on every tick."""

    def __init__(
        self,
        llm: LLMInterface,
        market_feed: MarketFeed,
        knowledge: Optional[KnowledgeBrain] = None,  # Optional initially
        db: Optional[Database] = None,
        interval_seconds: int = 180,  # 3 minutes default
    ):
        self.llm = llm
        self.market = market_feed
        self.knowledge = knowledge
        self.db = db or Database()
        self.interval = interval_seconds
        self.active_conditions: List[TradeCondition] = []
        self.condition_callbacks: List[Callable] = []

    async def start(self):
        """Start the periodic strategist loop."""

    async def stop(self):
        """Stop the strategist loop."""

    async def generate_conditions(self) -> List[TradeCondition]:
        """Generate trade conditions based on current state. Called periodically."""

    def subscribe_conditions(self, callback: Callable[[List[TradeCondition]], None]):
        """Register callback for when new conditions are generated."""

    def get_active_conditions(self) -> List[TradeCondition]:
        """Get currently active (non-expired) conditions."""

    def _build_context(self) -> dict:
        """Build context dict for LLM prompt."""

    def _build_prompt(self, context: dict) -> str:
        """Build the full LLM prompt."""

    def _parse_response(self, response: str) -> List[TradeCondition]:
        """Parse LLM JSON response into TradeCondition objects."""

    def _log_conditions(self, conditions: List[TradeCondition]):
        """Log generated conditions to database."""
```

---

## Technical Approach

### Step 1: Create TradeCondition Dataclass

Create `src/models/trade_condition.py`:

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal, Optional
import uuid

@dataclass
class TradeCondition:
    coin: str
    direction: Literal["LONG", "SHORT"]
    trigger_price: float
    trigger_condition: Literal["ABOVE", "BELOW"]
    stop_loss_pct: float
    take_profit_pct: float
    position_size_usd: float
    reasoning: str
    strategy_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=datetime.now)
    valid_until: datetime = field(default_factory=lambda: datetime.now() + timedelta(minutes=5))
    additional_filters: Optional[dict] = None

    def is_expired(self) -> bool:
        return datetime.now() > self.valid_until

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "coin": self.coin,
            "direction": self.direction,
            "trigger_price": self.trigger_price,
            "trigger_condition": self.trigger_condition,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "position_size_usd": self.position_size_usd,
            "reasoning": self.reasoning,
            "strategy_id": self.strategy_id,
            "created_at": self.created_at.isoformat(),
            "valid_until": self.valid_until.isoformat(),
        }
```

### Step 2: Create Strategist Class

Create `src/strategist.py`:

1. **Initialization**: Take LLM, MarketFeed, optional Knowledge Brain
2. **Context Building**: Gather market state, knowledge, account info
3. **Prompt Building**: Format the LLM prompt with context
4. **Response Parsing**: Parse JSON response, validate, create TradeCondition objects
5. **Periodic Loop**: Run generation every N seconds
6. **Callback System**: Notify listeners (Sniper) when new conditions are generated
7. **Logging**: Log all conditions and reasoning to database

### Step 3: Initial Simplified Knowledge

For initial implementation (before full Knowledge Brain):

```python
def _get_simplified_knowledge(self) -> dict:
    """Get simplified knowledge until full Knowledge Brain is ready."""
    return {
        "good_coins": ["SOL", "ETH", "BTC"],  # Start with top 3
        "avoid_coins": [],  # No blacklist initially
        "active_rules": [],  # No rules initially
        "winning_patterns": [
            "Momentum breakout - enter when price breaks above recent high",
            "Support bounce - enter on pullback to support level",
        ],
    }
```

### Step 4: Database Schema

Add to `active_conditions` table (already in spec):

```sql
CREATE TABLE IF NOT EXISTS active_conditions (
    id TEXT PRIMARY KEY,
    coin TEXT NOT NULL,
    direction TEXT NOT NULL,
    trigger_price REAL NOT NULL,
    trigger_condition TEXT NOT NULL,
    stop_loss_pct REAL NOT NULL,
    take_profit_pct REAL NOT NULL,
    position_size_usd REAL NOT NULL,
    strategy_id TEXT,
    reasoning TEXT,
    created_at TIMESTAMP NOT NULL,
    valid_until TIMESTAMP NOT NULL,
    triggered BOOLEAN DEFAULT FALSE,
    triggered_at TIMESTAMP
);
```

### Step 5: Integration with Sniper

The Strategist notifies Sniper via callback:

```python
# In main orchestration:
strategist = Strategist(llm, market_feed)
sniper = Sniper(market_feed, journal)

# Wire them up:
strategist.subscribe_conditions(sniper.set_conditions)

# Start both:
await strategist.start()
await sniper.start()
```

---

## Files Created

| File | Purpose |
|------|---------|
| `src/strategist.py` | Main Strategist class |
| `src/models/trade_condition.py` | TradeCondition dataclass |
| `tests/test_strategist.py` | Unit tests |

---

## Files Modified

| File | Change |
|------|--------|
| `src/database.py` | Add `active_conditions` table and methods |
| `src/models/__init__.py` | Export TradeCondition |

---

## Acceptance Criteria

- [x] Strategist initializes with LLM and MarketFeed
- [x] Generates conditions every N seconds (configurable)
- [x] LLM returns valid JSON with 0-3 conditions
- [x] Conditions are parsed into TradeCondition objects
- [x] Expired conditions are automatically removed
- [x] Callbacks fire when new conditions are generated
- [x] All conditions logged to database with reasoning
- [x] Gracefully handles LLM errors (retries, continues)
- [x] Works without Knowledge Brain (simplified fallback)

---

## Verification

### Unit Test

```bash
pytest tests/test_strategist.py -v
```

### Integration Test

```python
# Test strategist generates conditions
import asyncio
from src.strategist import Strategist
from src.llm_interface import LLMInterface
from src.market_feed import MarketFeed

async def test_strategist():
    # Setup
    llm = LLMInterface()
    market = MarketFeed(['BTC', 'ETH', 'SOL'])
    strategist = Strategist(llm, market, interval_seconds=60)

    # Track conditions
    received_conditions = []
    def on_conditions(conditions):
        received_conditions.extend(conditions)
        print(f"Received {len(conditions)} conditions:")
        for c in conditions:
            print(f"  {c.direction} {c.coin} if {c.trigger_condition} ${c.trigger_price}")

    strategist.subscribe_conditions(on_conditions)

    # Start
    await market.connect()
    await asyncio.sleep(5)  # Let prices populate

    # Generate once manually
    conditions = await strategist.generate_conditions()
    print(f"\nGenerated {len(conditions)} conditions")

    for c in conditions:
        print(f"\n{c.direction} {c.coin}:")
        print(f"  Trigger: {c.trigger_condition} ${c.trigger_price:,.2f}")
        print(f"  Stop: {c.stop_loss_pct}% | Target: {c.take_profit_pct}%")
        print(f"  Size: ${c.position_size_usd}")
        print(f"  Reason: {c.reasoning}")

asyncio.run(test_strategist())
```

### Manual Verification

```bash
# Start strategist and watch output for 10 minutes
python -c "
import asyncio
from src.strategist import Strategist
from src.llm_interface import LLMInterface
from src.market_feed import MarketFeed

async def main():
    llm = LLMInterface()
    market = MarketFeed(['BTC', 'ETH', 'SOL', 'XRP', 'DOGE'])
    strategist = Strategist(llm, market, interval_seconds=120)  # 2 min

    def on_conditions(conditions):
        print(f'\n[{len(conditions)} new conditions]')
        for c in conditions:
            print(f'  {c.direction} {c.coin} @ \${c.trigger_price:,.2f}')

    strategist.subscribe_conditions(on_conditions)

    await market.connect()
    await strategist.start()

    # Run for 10 minutes
    await asyncio.sleep(600)

asyncio.run(main())
"
```

---

## Error Handling

| Error | Handling |
|-------|----------|
| LLM timeout | Retry with backoff, log warning, continue next cycle |
| Invalid JSON | Log error, continue next cycle |
| MarketFeed not ready | Skip generation, log warning |
| Missing price data | Exclude coin from context |

---

## Configuration

```python
# Environment variables or config
STRATEGIST_INTERVAL_SECONDS = 180  # 3 minutes (range: 120-300)
STRATEGIST_CONDITION_TTL_MINUTES = 5  # Conditions expire after 5 min
STRATEGIST_MAX_CONDITIONS = 3  # Max conditions per cycle
STRATEGIST_MIN_CONFIDENCE = 0.5  # Skip low-confidence suggestions
```

---

## Completion Notes

### Implementation Summary

**Date:** February 3, 2026

**Files Created:**
| File | Lines | Purpose |
|------|-------|---------|
| `src/models/__init__.py` | 5 | Model exports |
| `src/models/trade_condition.py` | 174 | TradeCondition dataclass |
| `src/strategist.py` | 653 | Main Strategist class |
| `tests/test_strategist.py` | 565 | Unit tests |

**Files Modified:**
| File | Change |
|------|--------|
| `src/database.py` | Added `active_conditions` table + 7 CRUD methods |

### Key Features Implemented

1. **Periodic Generation**: Runs every 3 minutes (configurable via `interval_seconds`)
2. **Context Building**: Gathers market prices, knowledge, account state
3. **LLM Prompting**: Structured prompt requesting JSON conditions
4. **Response Parsing**: Handles JSON with/without markdown code blocks
5. **Validation**: Enforces $20-$100 position size, 1-3% stop loss, trigger price within 10% of current
6. **Callback System**: `subscribe_conditions()` for Sniper integration
7. **Logging**: All conditions saved to database with reasoning
8. **Error Handling**: Graceful degradation on LLM errors

### TradeCondition Model

```python
@dataclass
class TradeCondition:
    coin: str                    # "SOL", "ETH"
    direction: "LONG"|"SHORT"
    trigger_price: float
    trigger_condition: "ABOVE"|"BELOW"
    stop_loss_pct: float         # e.g., 2.0 for 2%
    take_profit_pct: float
    position_size_usd: float
    reasoning: str
    strategy_id: str
    id: str                      # Auto-generated UUID
    created_at: datetime
    valid_until: datetime        # Default: 5 minutes
```

### Verification

```bash
# Test imports and basic functionality
python3 -c "
from src.models.trade_condition import TradeCondition
from src.strategist import Strategist
condition = TradeCondition(
    coin='SOL', direction='LONG', trigger_price=143.50,
    trigger_condition='ABOVE', stop_loss_pct=2.0, take_profit_pct=1.5,
    position_size_usd=50.0, reasoning='Test', strategy_id='test'
)
print(f'Created: {condition}')
print('All imports working!')
"
```

### Notes

- TASK-111 (Condition Generation & Parsing) was incorporated into this task
- Condition parsing handles markdown code blocks from LLM responses
- Simplified knowledge fallback until Knowledge Brain (TASK-300) is ready

---

## Related

- [AUTONOMOUS-TRADER-SPEC.md](../AUTONOMOUS-TRADER-SPEC.md) - Full system spec (Section 4: Strategist)
- [TASK-100](./TASK-100.md) - MarketFeed (provides price data)
- [TASK-101](./TASK-101.md) - Sniper (consumes conditions)
- [TASK-200](./TASK-200.md) - LLM Configuration (qwen2.5:14b)
- [TASK-300](./TASK-300.md) - Knowledge Brain (future integration)
