# Component Reference

**Last Updated:** February 3, 2026
**Phase:** 2 Complete

Quick reference for all source files in the trading bot.

---

## Core Trading Components

### market_feed.py
**Purpose:** Real-time market data via WebSocket

| Class | Key Methods |
|-------|-------------|
| `MarketFeed` | `connect()`, `subscribe()`, `get_price()`, `get_klines()`, `get_market_state()` |

```python
# Usage
feed = MarketFeed()
await feed.connect()
await feed.subscribe(["BTCUSDT", "ETHUSDT"])
price = feed.get_price("BTC")
state = feed.get_market_state()
```

---

### strategist.py
**Purpose:** LLM-powered trading condition generation

| Class | Key Methods |
|-------|-------------|
| `Strategist` | `generate_conditions()`, `set_knowledge_context()` |

```python
# Usage
strategist = Strategist(llm, knowledge_brain)
conditions = await strategist.generate_conditions(market_state)
# Returns: List[TradeCondition]
```

---

### sniper.py
**Purpose:** Sub-millisecond trade execution

| Class | Key Methods |
|-------|-------------|
| `Sniper` | `set_conditions()`, `check_and_execute()`, `close_position()`, `get_positions()` |

```python
# Usage
sniper = Sniper(exchange_client, journal)
sniper.set_conditions(conditions)
# Called on every price update:
sniper.check_and_execute(current_prices)
```

---

### journal.py
**Purpose:** Trade recording and history

| Class | Key Methods |
|-------|-------------|
| `TradeJournal` | `record_trade()`, `get_recent_trades()`, `get_trade()`, `get_stats()` |

```python
# Usage
journal = TradeJournal(db)
journal.record_trade(trade_result)
recent = journal.get_recent_trades(hours=24)
```

---

## Learning Components

### quick_update.py
**Purpose:** Instant post-trade updates (<10ms)

| Class | Key Methods |
|-------|-------------|
| `QuickUpdate` | `process_trade_close()`, `get_stats()` |

```python
# Usage
quick = QuickUpdate(coin_scorer, pattern_library, db)
result = quick.process_trade_close(trade_result)
# Returns: QuickUpdateResult with any adaptations triggered
```

---

### coin_scorer.py
**Purpose:** Per-coin performance tracking

| Class | Key Methods |
|-------|-------------|
| `CoinScorer` | `process_trade_result()`, `get_coin_status()`, `get_position_modifier()`, `force_blacklist()` |

```python
# Usage
scorer = CoinScorer(knowledge_brain, db)
adaptation = scorer.process_trade_result(trade)
status = scorer.get_coin_status("SOL")  # CoinStatus enum
modifier = scorer.get_position_modifier("SOL")  # 0.0-1.5
```

---

### pattern_library.py
**Purpose:** Trading pattern management

| Class | Key Methods |
|-------|-------------|
| `PatternLibrary` | `create_pattern()`, `get_pattern()`, `record_pattern_outcome()`, `update_confidence()`, `match_conditions()` |

```python
# Usage
library = PatternLibrary(knowledge_brain)
pattern = library.create_pattern("breakout", "desc", entry_cond, exit_cond)
library.record_pattern_outcome(pattern_id, won=True, pnl=50.0)
matches = library.match_conditions(market_state)
```

---

### reflection.py
**Purpose:** Hourly deep analysis with LLM

| Class | Key Methods |
|-------|-------------|
| `ReflectionEngine` | `reflect()`, `add_trade()`, `get_pending_trades()` |

```python
# Usage
engine = ReflectionEngine(llm, knowledge_brain, db)
engine.add_trade(trade)  # Queue for analysis
result = await engine.reflect()  # Hourly call
# Returns: ReflectionResult with insights
```

---

### adaptation.py
**Purpose:** Apply learning changes

| Class | Key Methods |
|-------|-------------|
| `AdaptationEngine` | `apply_insights()`, `apply_adaptation()`, `rollback_adaptation()`, `measure_effectiveness()` |

```python
# Usage
engine = AdaptationEngine(knowledge_brain, coin_scorer, pattern_library, db)
results = engine.apply_insights(insights)
# Returns: List[AdaptationRecord]
```

---

### knowledge.py
**Purpose:** Central knowledge repository

| Class | Key Methods |
|-------|-------------|
| `KnowledgeBrain` | `get_knowledge_context()`, `get_coin_score()`, `blacklist_coin()`, `add_pattern()`, `add_rule()` |

```python
# Usage
brain = KnowledgeBrain(db)
context = brain.get_knowledge_context()  # For Strategist
score = brain.get_coin_score("BTC")
brain.blacklist_coin("DOGE", "Poor performance")
```

---

## Analysis Components

### src/analysis/metrics.py
**Purpose:** Trading metrics calculation

| Function | Purpose |
|----------|---------|
| `calculate_metrics(trades)` | Full TradingMetrics from trade list |
| `calculate_sharpe_ratio(returns)` | Risk-adjusted return |
| `calculate_max_drawdown(equity)` | Peak-to-trough decline |
| `calculate_profit_factor(profit, loss)` | Gross profit / gross loss |

---

### src/analysis/performance.py
**Purpose:** Performance breakdown analysis

| Function | Purpose |
|----------|---------|
| `analyze_by_hour(trades)` | Metrics by hour of day |
| `analyze_by_coin(trades)` | Metrics by coin |
| `analyze_by_pattern(trades)` | Metrics by pattern |
| `compare_periods(trades)` | First half vs second half |

---

### src/analysis/learning.py
**Purpose:** Learning effectiveness analysis

| Function | Purpose |
|----------|---------|
| `analyze_coin_score_accuracy(db)` | Score vs actual performance |
| `analyze_adaptation_effectiveness(db)` | Adaptation impact |
| `analyze_pattern_confidence_accuracy(db)` | Confidence vs outcomes |
| `calculate_learning_score(...)` | Overall learning grade |

---

## Dashboard Components

### dashboard_v2.py
**Purpose:** FastAPI observability dashboard

| Class | Key Routes |
|-------|------------|
| `DashboardServer` | See routes below |

**API Routes:**
| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Real-time overview page |
| `/knowledge` | GET | Knowledge browser page |
| `/adaptations` | GET | Adaptation history page |
| `/profitability` | GET | Performance metrics page |
| `/overrides` | GET | Manual controls page |
| `/api/status` | GET | System health |
| `/api/prices` | GET | Current prices |
| `/api/positions` | GET | Open positions |
| `/api/conditions` | GET | Active conditions |
| `/api/knowledge/coins` | GET | Coin scores |
| `/api/knowledge/patterns` | GET | Pattern library |
| `/api/adaptations` | GET | Adaptation list |
| `/api/profitability` | GET | Current metrics |
| `/api/feed` | GET | SSE real-time updates |

---

## Data Models

### src/models/trade_condition.py

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

---

### src/models/quick_update.py

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

@dataclass
class QuickUpdateResult:
    trade_id: str
    coin: str
    won: bool
    pnl_usd: float
    coin_adaptation: Optional[str] = None
    pattern_deactivated: bool = False
```

---

### src/models/knowledge.py

```python
@dataclass
class CoinScore:
    coin: str
    total_trades: int
    wins: int
    losses: int
    total_pnl: float
    win_rate: float
    trend: str
    is_blacklisted: bool

@dataclass
class TradingPattern:
    pattern_id: str
    description: str
    entry_conditions: Dict
    exit_conditions: Dict
    confidence: float
    is_active: bool

@dataclass
class RegimeRule:
    rule_id: str
    description: str
    condition: Dict
    action: str
    is_active: bool
```

---

### src/models/reflection.py

```python
@dataclass
class Insight:
    insight_type: str
    category: str
    title: str
    description: str
    evidence: Dict
    suggested_action: Optional[str]
    confidence: float

@dataclass
class ReflectionResult:
    reflection_id: str
    trades_analyzed: int
    insights: List[Insight]
    adaptations_triggered: int
```

---

## Support Components

### database.py
**Purpose:** SQLite persistence

| Class | Key Methods |
|-------|-------------|
| `Database` | `save_trade()`, `get_coin_score()`, `save_adaptation()`, `get_recent_trades()` |

---

### llm_interface.py
**Purpose:** Ollama LLM communication

| Class | Key Methods |
|-------|-------------|
| `LLMInterface` | `generate()`, `generate_json()`, `is_available()` |

---

### profitability.py
**Purpose:** Real-time P&L tracking

| Class | Key Methods |
|-------|-------------|
| `ProfitabilityTracker` | `get_current_snapshot()`, `get_equity_curve()`, `record_trade()` |

---

### effectiveness.py
**Purpose:** Adaptation effectiveness tracking

| Class | Key Methods |
|-------|-------------|
| `EffectivenessTracker` | `measure_adaptation()`, `get_summary()`, `should_rollback()` |

---

## Entry Points

### main_v2.py
**Purpose:** Full autonomous trading system

```bash
python src/main_v2.py --mode paper --dashboard --port 8080
```

| Class | Key Methods |
|-------|-------------|
| `TradingSystem` | `start()`, `stop()`, `run_trading_loop()` |

---

## File Organization

```
src/
├── __init__.py
├── main_v2.py              # Entry point
├── market_feed.py          # WebSocket data
├── strategist.py           # LLM conditions
├── sniper.py               # Execution
├── journal.py              # Trade recording
├── quick_update.py         # Instant learning
├── coin_scorer.py          # Coin tracking
├── pattern_library.py      # Pattern management
├── reflection.py           # Deep analysis
├── adaptation.py           # Apply changes
├── knowledge.py            # Knowledge store
├── database.py             # Persistence
├── llm_interface.py        # LLM client
├── dashboard_v2.py         # FastAPI dashboard
├── profitability.py        # P&L tracking
├── effectiveness.py        # Adaptation tracking
├── models/
│   ├── trade_condition.py
│   ├── quick_update.py
│   ├── knowledge.py
│   ├── reflection.py
│   └── adaptation.py
└── analysis/
    ├── metrics.py          # Trading metrics
    ├── performance.py      # Breakdowns
    └── learning.py         # Learning analysis
```

---

## Related Documentation

- [SYSTEM-OVERVIEW.md](./SYSTEM-OVERVIEW.md) - Architecture overview
- [DATA-MODEL.md](./DATA-MODEL.md) - Database schema
- [../development/COMPONENT-GUIDE.md](../development/COMPONENT-GUIDE.md) - Detailed component docs
