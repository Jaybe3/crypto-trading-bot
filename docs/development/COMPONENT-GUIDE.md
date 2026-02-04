# Component Development Guide

**Last Updated:** February 3, 2026
**Phase:** 2 Complete

Detailed guide for understanding and modifying trading bot components.

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                               │
│                      (Orchestration)                             │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│  MarketFeed  │  Strategist  │   Sniper     │    Dashboard      │
│  (Data)      │  (Strategy)  │  (Execution) │    (Observability)│
├──────────────┴──────────────┴──────────────┴───────────────────┤
│                        Learning Layer                           │
│  QuickUpdate │ CoinScorer │ PatternLibrary │ ReflectionEngine  │
├─────────────────────────────────────────────────────────────────┤
│                       Knowledge Layer                           │
│              KnowledgeBrain │ AdaptationEngine                  │
├─────────────────────────────────────────────────────────────────┤
│                       Persistence Layer                         │
│                          Database                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## MarketFeed

**File:** `src/market_feed.py`
**Purpose:** Real-time market data via WebSocket

### Key Concepts

- Maintains persistent WebSocket connection to Binance
- Subscribes to multiple trading pairs
- Caches latest prices for instant access
- Provides market state for Strategist

### Usage

```python
from market_feed import MarketFeed

feed = MarketFeed()
await feed.connect()
await feed.subscribe(["BTCUSDT", "ETHUSDT", "SOLUSDT"])

# Get current price
price = feed.get_price("BTC")  # Returns float

# Get klines (candlestick data)
klines = feed.get_klines("BTC", "1h", limit=24)

# Get full market state for Strategist
state = feed.get_market_state()
```

### Market State Structure

```python
{
    "prices": {"BTC": 45000.0, "ETH": 2500.0, ...},
    "changes_24h": {"BTC": 2.5, "ETH": -1.2, ...},
    "volatility": {"BTC": 1.8, "ETH": 2.1, ...},
    "volumes": {"BTC": 1500000000, ...},
    "btc_trend": "up",
    "market_sentiment": "bullish",
    "timestamp": 1707000000
}
```

### Extension Points

- Add new data sources: Implement in `connect()` and `subscribe()`
- Add new market metrics: Extend `get_market_state()`
- Add WebSocket reconnection logic: Modify `_on_disconnect()`

---

## Strategist

**File:** `src/strategist.py`
**Purpose:** LLM-powered trading condition generation

### Key Concepts

- Uses LLM to analyze market state and generate trading conditions
- Integrates knowledge context from KnowledgeBrain
- Respects blacklists, patterns, and regime rules
- Outputs structured TradeCondition objects

### Usage

```python
from strategist import Strategist
from llm_interface import LLMInterface
from knowledge import KnowledgeBrain

llm = LLMInterface()
brain = KnowledgeBrain(db)
strategist = Strategist(llm, brain)

# Generate conditions
conditions = await strategist.generate_conditions(market_state)
# Returns: List[TradeCondition]
```

### TradeCondition Structure

```python
@dataclass
class TradeCondition:
    condition_id: str
    coin: str
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size_usd: float
    expires_at: datetime
    pattern_id: Optional[str] = None
```

### LLM Prompt Flow

1. Build context from KnowledgeBrain
2. Format market state
3. Send to LLM with structured output request
4. Parse JSON response
5. Validate and create TradeCondition objects

### Extension Points

- Modify prompts: Edit `_build_prompt()` method
- Add new condition types: Extend TradeCondition dataclass
- Change LLM model: Configure in LLMInterface

---

## Sniper

**File:** `src/sniper.py`
**Purpose:** Sub-millisecond trade execution

### Key Concepts

- Monitors prices against active conditions
- Executes instantly when conditions trigger
- Manages open positions
- Handles stop-loss and take-profit exits

### Usage

```python
from sniper import Sniper

sniper = Sniper(exchange_client, journal)

# Set conditions from Strategist
sniper.set_conditions(conditions)

# Called on every price update (main loop)
sniper.check_and_execute(current_prices)

# Get open positions
positions = sniper.get_positions()

# Close a position manually
sniper.close_position(position_id, reason="manual")
```

### Execution Flow

```
Price Update → Check Entry Conditions → Execute if Matched
            → Check Exit Conditions  → Close if Stop/Take-Profit
```

### Position Structure

```python
@dataclass
class Position:
    position_id: str
    condition_id: str
    coin: str
    direction: str
    entry_price: float
    entry_time: datetime
    position_size_usd: float
    stop_loss: float
    take_profit: float
    current_pnl: float = 0.0
```

### Extension Points

- Add trailing stops: Modify `_check_exits()`
- Add partial exits: New method `partial_close()`
- Add slippage simulation: Modify `_execute_entry()`

---

## QuickUpdate

**File:** `src/quick_update.py`
**Purpose:** Instant post-trade learning (<10ms)

### Key Concepts

- Processes every closed trade immediately
- Updates coin scores via CoinScorer
- Updates pattern confidence via PatternLibrary
- Triggers threshold-based adaptations
- No LLM involvement (pure math)

### Usage

```python
from quick_update import QuickUpdate

quick = QuickUpdate(coin_scorer, pattern_library, db)

# Called when trade closes
result = quick.process_trade_close(trade_result)
# Returns: QuickUpdateResult
```

### TradeResult Input

```python
@dataclass
class TradeResult:
    trade_id: str
    coin: str
    direction: str
    entry_price: float
    exit_price: float
    position_size_usd: float
    pnl_usd: float
    won: bool
    exit_reason: str
    pattern_id: Optional[str] = None
```

### QuickUpdateResult Output

```python
@dataclass
class QuickUpdateResult:
    trade_id: str
    coin: str
    won: bool
    pnl_usd: float
    coin_adaptation: Optional[str] = None  # "BLACKLISTED", "REDUCED", "FAVORED"
    pattern_deactivated: bool = False
```

### Extension Points

- Add new metrics: Extend `process_trade_close()`
- Change thresholds: Modify constants in CoinScorer
- Add new adaptation types: Extend QuickUpdateResult

---

## CoinScorer

**File:** `src/coin_scorer.py`
**Purpose:** Per-coin performance tracking

### Key Concepts

- Maintains performance metrics for each coin
- Calculates win rate, P&L, trends
- Determines coin status (BLACKLISTED, REDUCED, NORMAL, FAVORED)
- Provides position size modifiers

### Usage

```python
from coin_scorer import CoinScorer

scorer = CoinScorer(knowledge_brain, db)

# Process trade result
adaptation = scorer.process_trade_result(trade)

# Get coin status
status = scorer.get_coin_status("SOL")  # CoinStatus enum

# Get position modifier
modifier = scorer.get_position_modifier("SOL")  # 0.0 - 1.5

# Force blacklist
scorer.force_blacklist("DOGE", "Manual blacklist")
```

### Coin Status Thresholds

```python
MIN_TRADES_FOR_ADAPTATION = 5
BLACKLIST_WIN_RATE = 0.30      # Below 30% → BLACKLISTED
REDUCED_WIN_RATE = 0.45        # Below 45% → REDUCED
FAVORED_WIN_RATE = 0.60        # Above 60% → FAVORED
RECOVERY_WIN_RATE = 0.50       # Above 50% → Can recover from REDUCED
```

### Position Modifiers

| Status | Modifier |
|--------|----------|
| BLACKLISTED | 0.0 (no trading) |
| REDUCED | 0.5 |
| NORMAL | 1.0 |
| FAVORED | 1.5 |
| UNKNOWN | 1.0 |

---

## PatternLibrary

**File:** `src/pattern_library.py`
**Purpose:** Trading pattern management

### Key Concepts

- Stores trading patterns with entry/exit conditions
- Tracks pattern performance (wins, losses, P&L)
- Manages confidence scores
- Activates/deactivates patterns based on performance

### Usage

```python
from pattern_library import PatternLibrary

library = PatternLibrary(knowledge_brain)

# Create pattern
pattern = library.create_pattern(
    name="breakout",
    description="Price breaks above resistance",
    entry_conditions={"..."},
    exit_conditions={"..."}
)

# Record outcome
library.record_pattern_outcome(pattern_id, won=True, pnl=50.0)

# Match patterns to market state
matches = library.match_conditions(market_state)

# Update confidence
library.update_confidence(pattern_id)
```

### Confidence Calculation

```python
def calculate_confidence(pattern):
    if pattern.times_used < 3:
        return 0.5  # Default for new patterns

    base = pattern.wins / pattern.times_used
    recency_factor = get_recent_performance(pattern)

    return (base * 0.7) + (recency_factor * 0.3)
```

### Auto-Deactivation

Patterns are deactivated when:
- Confidence drops below 0.2
- 5+ consecutive losses
- Total P&L below -$100

---

## ReflectionEngine

**File:** `src/reflection.py`
**Purpose:** Hourly deep analysis with LLM

### Key Concepts

- Runs hourly (or after N trades)
- Uses LLM to analyze trade history
- Generates insights (patterns, problems, opportunities)
- Queues insights for adaptation

### Usage

```python
from reflection import ReflectionEngine

engine = ReflectionEngine(llm, knowledge_brain, db)

# Queue trade for analysis
engine.add_trade(trade)

# Run reflection (called hourly)
result = await engine.reflect()
# Returns: ReflectionResult
```

### ReflectionResult Structure

```python
@dataclass
class ReflectionResult:
    reflection_id: str
    trades_analyzed: int
    insights: List[Insight]
    adaptations_triggered: int
```

### Insight Types

| Type | Description | Example Action |
|------|-------------|----------------|
| `coin` | Coin performance issue | BLACKLIST/FAVOR |
| `pattern` | Pattern effectiveness | DEACTIVATE |
| `time` | Time-based pattern | CREATE_TIME_RULE |
| `regime` | Market condition | CREATE_REGIME_RULE |
| `exit` | Exit strategy issue | ADJUST_PARAMS |

---

## AdaptationEngine

**File:** `src/adaptation.py`
**Purpose:** Apply learning changes

### Key Concepts

- Receives insights from Reflection
- Applies changes to KnowledgeBrain
- Records all adaptations with before/after metrics
- Measures effectiveness over time
- Can rollback harmful adaptations

### Usage

```python
from adaptation import AdaptationEngine

engine = AdaptationEngine(knowledge_brain, coin_scorer, pattern_library, db)

# Apply insights from reflection
results = engine.apply_insights(insights)
# Returns: List[AdaptationRecord]

# Measure effectiveness
engine.measure_effectiveness(adaptation_id)

# Rollback if harmful
engine.rollback_adaptation(adaptation_id)
```

### AdaptationRecord Structure

```python
@dataclass
class AdaptationRecord:
    adaptation_id: str
    action: str
    target: str
    reason: str
    confidence: float
    win_rate_before: float
    pnl_before: float
    win_rate_after: Optional[float]
    pnl_after: Optional[float]
    effectiveness_rating: str  # pending, effective, harmful, etc.
```

---

## KnowledgeBrain

**File:** `src/knowledge.py`
**Purpose:** Central knowledge repository

### Key Concepts

- Single source of truth for all learned knowledge
- Provides context for Strategist
- Stores coin scores, patterns, rules
- Persists to database

### Usage

```python
from knowledge import KnowledgeBrain

brain = KnowledgeBrain(db)

# Get context for Strategist
context = brain.get_knowledge_context()

# Coin operations
score = brain.get_coin_score("BTC")
brain.blacklist_coin("DOGE", "Poor performance")
brain.favor_coin("SOL", "High win rate")

# Pattern operations
brain.add_pattern(pattern)
brain.deactivate_pattern(pattern_id)

# Rule operations
brain.add_rule(rule)
```

### Knowledge Context Structure

```python
{
    "coin_summaries": {
        "SOL": "70% win rate, trending up, FAVORED",
        "DOGE": "BLACKLISTED - poor performance"
    },
    "blacklist": ["DOGE", "SHIB"],
    "good_coins": ["SOL", "BTC"],
    "patterns": [
        {"id": "breakout_001", "confidence": 0.8, "description": "..."}
    ],
    "regime_rules": [
        {"condition": "hour in [2,3,4]", "action": "REDUCE_SIZE"}
    ],
    "recent_performance": {
        "win_rate": 58.3,
        "profit_factor": 1.45
    }
}
```

---

## Database

**File:** `src/database.py`
**Purpose:** SQLite persistence layer

### Key Methods

```python
# Trades
db.save_trade(trade_dict)
db.get_recent_trades(hours=24)
db.get_trade(trade_id)

# Coin scores
db.get_coin_score(coin)
db.update_coin_score(coin, updates)
db.get_all_coin_scores()

# Patterns
db.save_pattern(pattern_dict)
db.get_pattern(pattern_id)
db.get_active_patterns()

# Adaptations
db.save_adaptation(adaptation_dict)
db.get_recent_adaptations(days=7)
db.update_adaptation_effectiveness(adaptation_id, rating)
```

### Tables

See [DATA-MODEL.md](../architecture/DATA-MODEL.md) for full schema.

---

## Testing Components

### Unit Test Pattern

```python
import pytest
from unittest.mock import Mock, AsyncMock

def test_coin_scorer_blacklist():
    # Setup
    mock_brain = Mock()
    mock_db = Mock()
    scorer = CoinScorer(mock_brain, mock_db)

    # Create losing trades
    for i in range(5):
        trade = TradeResult(
            trade_id=f"trade_{i}",
            coin="DOGE",
            won=False,
            pnl_usd=-10.0,
            ...
        )
        scorer.process_trade_result(trade)

    # Verify blacklisted
    assert scorer.get_coin_status("DOGE") == CoinStatus.BLACKLISTED
```

### Integration Test Pattern

```python
@pytest.mark.asyncio
async def test_full_learning_loop():
    # Setup real components
    db = Database(":memory:")
    brain = KnowledgeBrain(db)
    scorer = CoinScorer(brain, db)
    quick = QuickUpdate(scorer, library, db)

    # Process trade
    result = quick.process_trade_close(trade_result)

    # Verify learning
    score = brain.get_coin_score("BTC")
    assert score.total_trades == 1
```

---

## Related Documentation

- [TESTING-GUIDE.md](./TESTING-GUIDE.md) - Testing practices
- [ADDING-FEATURES.md](./ADDING-FEATURES.md) - Adding new features
- [../architecture/COMPONENT-REFERENCE.md](../architecture/COMPONENT-REFERENCE.md) - Quick reference
