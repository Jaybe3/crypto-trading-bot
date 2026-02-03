# Data Model Reference

**Last Updated:** February 3, 2026
**Phase:** 2 Complete

---

## Overview

The trading bot uses SQLite for persistence. All knowledge, trades, adaptations, and metrics are stored in a single database file: `data/trading_bot.db`.

---

## Database Schema

### Core Tables

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  trade_journal  │     │   coin_scores   │     │trading_patterns │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ trade_id (PK)   │     │ coin (PK)       │     │ pattern_id (PK) │
│ coin            │────►│ total_trades    │     │ description     │
│ pnl_usd         │     │ wins, losses    │     │ entry_conditions│
│ pattern_id      │────►│ win_rate        │     │ exit_conditions │
│ ...             │     │ total_pnl       │     │ confidence      │
└─────────────────┘     │ trend           │     │ times_used      │
                        │ is_blacklisted  │     │ wins, losses    │
                        └─────────────────┘     └─────────────────┘
                                │
                                │
┌─────────────────┐     ┌───────▼─────────┐     ┌─────────────────┐
│   adaptations   │     │  regime_rules   │     │    insights     │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ adaptation_id   │     │ rule_id (PK)    │     │ insight_id (PK) │
│ action          │     │ description     │     │ insight_type    │
│ target          │     │ condition       │     │ title           │
│ effectiveness   │     │ action          │     │ description     │
│ win_rate_before │     │ times_triggered │     │ suggested_action│
│ win_rate_after  │     │ is_active       │     │ confidence      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## Table Definitions

### trade_journal

Records every completed trade with full context.

```sql
CREATE TABLE trade_journal (
    -- Identity
    trade_id TEXT PRIMARY KEY,
    journal_id INTEGER AUTOINCREMENT,

    -- Trade details
    coin TEXT NOT NULL,
    direction TEXT NOT NULL,  -- 'LONG' or 'SHORT'
    entry_price REAL NOT NULL,
    exit_price REAL NOT NULL,
    position_size_usd REAL NOT NULL,

    -- Results
    pnl_usd REAL NOT NULL,
    pnl_pct REAL,

    -- Timing
    entry_time TEXT NOT NULL,  -- ISO format
    exit_time TEXT NOT NULL,
    duration_seconds INTEGER,

    -- Context
    exit_reason TEXT,  -- 'take_profit', 'stop_loss', 'manual'
    pattern_id TEXT,
    strategy_id TEXT,
    condition_id TEXT,

    -- Market context at entry
    btc_price_at_entry REAL,
    btc_trend_at_entry TEXT,
    volatility_at_entry REAL,

    -- Indexes
    INDEX idx_coin (coin),
    INDEX idx_exit_time (exit_time),
    INDEX idx_pattern (pattern_id)
);
```

**Key Queries:**
```sql
-- Recent trades
SELECT * FROM trade_journal ORDER BY exit_time DESC LIMIT 50;

-- Trades by coin
SELECT * FROM trade_journal WHERE coin = 'BTC' ORDER BY exit_time DESC;

-- Win rate calculation
SELECT
    coin,
    COUNT(*) as trades,
    SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
    SUM(pnl_usd) as total_pnl
FROM trade_journal
GROUP BY coin;
```

---

### coin_scores

Tracks performance metrics for each traded coin.

```sql
CREATE TABLE coin_scores (
    -- Identity
    coin TEXT PRIMARY KEY,

    -- Trade counts
    total_trades INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,

    -- P&L
    total_pnl REAL DEFAULT 0,
    avg_pnl REAL DEFAULT 0,
    avg_winner REAL DEFAULT 0,
    avg_loser REAL DEFAULT 0,

    -- Rates
    win_rate REAL DEFAULT 0,
    score REAL DEFAULT 50,  -- 0-100 scale

    -- Status
    is_blacklisted BOOLEAN DEFAULT FALSE,
    blacklist_reason TEXT,
    status TEXT DEFAULT 'unknown',  -- 'blacklisted', 'reduced', 'normal', 'favored'

    -- Trend
    trend TEXT DEFAULT 'stable',  -- 'improving', 'degrading', 'stable'
    recent_results TEXT,  -- JSON array of recent win/loss

    -- Timestamps
    first_trade_at TEXT,
    last_trade_at TEXT,
    last_updated TEXT
);
```

**Key Queries:**
```sql
-- Good performers
SELECT coin, win_rate, total_pnl
FROM coin_scores
WHERE total_trades >= 5 AND win_rate > 0.6 AND total_pnl > 0
ORDER BY win_rate DESC;

-- Blacklisted coins
SELECT coin, blacklist_reason FROM coin_scores WHERE is_blacklisted = 1;

-- Score ranking
SELECT coin, score, win_rate, total_trades
FROM coin_scores
ORDER BY score DESC;
```

---

### trading_patterns

Stores trading patterns with effectiveness tracking.

```sql
CREATE TABLE trading_patterns (
    -- Identity
    pattern_id TEXT PRIMARY KEY,
    name TEXT,
    description TEXT NOT NULL,

    -- Conditions (JSON)
    entry_conditions TEXT NOT NULL,  -- JSON
    exit_conditions TEXT NOT NULL,   -- JSON

    -- Performance
    times_used INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    total_pnl REAL DEFAULT 0,
    win_rate REAL DEFAULT 0,

    -- Confidence
    confidence REAL DEFAULT 0.5,  -- 0-1 scale

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    deactivation_reason TEXT,

    -- Timestamps
    created_at TEXT,
    last_used_at TEXT,
    last_updated TEXT
);
```

**Entry Conditions Example:**
```json
{
    "coin": "BTC",
    "timeframe": "1h",
    "trend": "up",
    "volatility_range": [1.5, 3.0],
    "hour_range": [8, 16],
    "btc_trend": "up"
}
```

**Exit Conditions Example:**
```json
{
    "take_profit_pct": 2.0,
    "stop_loss_pct": 1.0,
    "trailing_stop": false,
    "max_duration_minutes": 60
}
```

---

### regime_rules

Time-based and condition-based trading rules.

```sql
CREATE TABLE regime_rules (
    -- Identity
    rule_id TEXT PRIMARY KEY,
    description TEXT NOT NULL,

    -- Condition (JSON)
    condition TEXT NOT NULL,  -- JSON condition specification

    -- Action
    action TEXT NOT NULL,  -- 'NO_TRADE', 'REDUCE_SIZE', 'INCREASE_SIZE'

    -- Performance
    times_triggered INTEGER DEFAULT 0,
    estimated_saves REAL DEFAULT 0,  -- P&L saved by following rule

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TEXT,
    last_triggered_at TEXT
);
```

**Condition Examples:**
```json
// Time-based rule
{
    "type": "time",
    "hour_range": [2, 4]
}

// Volatility-based rule
{
    "type": "volatility",
    "btc_volatility_below": 1.0
}

// Combined rule
{
    "type": "combined",
    "conditions": [
        {"hour_range": [0, 4]},
        {"btc_volatility_below": 0.8}
    ]
}
```

---

### adaptations

Records every change made to the knowledge system.

```sql
CREATE TABLE adaptations (
    -- Identity
    adaptation_id TEXT PRIMARY KEY,

    -- Action
    action TEXT NOT NULL,  -- 'BLACKLIST', 'FAVOR', 'CREATE_RULE', etc.
    target TEXT NOT NULL,  -- Coin symbol, pattern_id, or rule_id
    reason TEXT,

    -- Source
    source TEXT,  -- 'quick_update', 'reflection', 'manual'
    insight_id TEXT,  -- Link to triggering insight
    confidence REAL,

    -- Before metrics
    win_rate_before REAL,
    pnl_before REAL,
    trades_before INTEGER,

    -- After metrics (filled later)
    win_rate_after REAL,
    pnl_after REAL,
    trades_after INTEGER,

    -- Effectiveness
    effectiveness_rating TEXT,  -- 'highly_effective', 'effective', 'neutral', 'ineffective', 'harmful', 'pending'
    effectiveness_measured_at TEXT,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    rolled_back BOOLEAN DEFAULT FALSE,
    rollback_reason TEXT,

    -- Timestamps
    applied_at TEXT NOT NULL,

    FOREIGN KEY (insight_id) REFERENCES insights(insight_id)
);
```

**Effectiveness Ratings:**
- `highly_effective`: Significant improvement (>20% better)
- `effective`: Noticeable improvement (5-20% better)
- `neutral`: No significant change
- `ineffective`: Slight negative impact (0-10% worse)
- `harmful`: Significant negative impact (>10% worse)
- `pending`: Not yet measured

---

### insights

Stores insights generated by the reflection engine.

```sql
CREATE TABLE insights (
    -- Identity
    insight_id TEXT PRIMARY KEY,

    -- Classification
    insight_type TEXT NOT NULL,  -- 'coin', 'pattern', 'time', 'regime', 'exit', 'general'
    category TEXT,  -- 'opportunity', 'problem', 'observation'

    -- Content
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    evidence TEXT,  -- JSON with supporting data

    -- Action
    suggested_action TEXT,
    confidence REAL,

    -- Status
    status TEXT DEFAULT 'pending',  -- 'pending', 'applied', 'rejected', 'expired'
    applied_adaptation_id TEXT,

    -- Timestamps
    created_at TEXT NOT NULL,
    applied_at TEXT,

    FOREIGN KEY (applied_adaptation_id) REFERENCES adaptations(adaptation_id)
);
```

---

### reflections

Records each reflection session.

```sql
CREATE TABLE reflections (
    -- Identity
    reflection_id TEXT PRIMARY KEY,

    -- Input
    trades_analyzed INTEGER,
    time_period_hours REAL,

    -- Output
    insights_generated INTEGER,
    adaptations_triggered INTEGER,

    -- Content
    summary TEXT,  -- LLM-generated summary
    raw_response TEXT,  -- Full LLM response

    -- Timing
    started_at TEXT,
    completed_at TEXT,
    duration_seconds REAL,

    -- Status
    status TEXT  -- 'completed', 'failed', 'partial'
);
```

---

## Data Models (Python)

### CoinScore

```python
@dataclass
class CoinScore:
    coin: str
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    avg_pnl: float = 0.0
    win_rate: float = 0.0
    avg_winner: float = 0.0
    avg_loser: float = 0.0
    is_blacklisted: bool = False
    blacklist_reason: str = ""
    last_updated: datetime = None
    trend: str = "stable"
```

### TradingPattern

```python
@dataclass
class TradingPattern:
    pattern_id: str
    description: str
    entry_conditions: Dict[str, Any]
    exit_conditions: Dict[str, Any]
    times_used: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    confidence: float = 0.5
    is_active: bool = True
```

### TradeResult

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
    entry_timestamp: int = 0
    exit_timestamp: int = 0
```

### Insight

```python
@dataclass
class Insight:
    insight_type: str
    category: str
    title: str
    description: str
    evidence: Dict[str, Any]
    suggested_action: Optional[str] = None
    confidence: float = 0.5
```

---

## Database Operations

### Connection Management

```python
# src/database.py
class Database:
    def __init__(self, db_path: str = "data/trading_bot.db"):
        self.db_path = db_path
        self._init_tables()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)
```

### Common Operations

```python
# Save trade
db.save_trade(trade_result.to_dict())

# Get coin score
score = db.get_coin_score("BTC")

# Update coin score
db.update_coin_score("BTC", {"win_rate": 0.65, "total_pnl": 150.0})

# Save adaptation
db.save_adaptation(adaptation.to_dict())

# Get recent trades
trades = db.get_recent_trades(hours=24)
```

---

## Data Retention

| Table | Retention | Cleanup |
|-------|-----------|---------|
| trade_journal | Forever | None |
| coin_scores | Forever | None |
| trading_patterns | Forever | Deactivate, don't delete |
| regime_rules | Forever | Deactivate, don't delete |
| adaptations | Forever | Historical record |
| insights | 30 days | Auto-cleanup |
| reflections | 30 days | Auto-cleanup |

---

## Indexes

```sql
-- Performance-critical indexes
CREATE INDEX idx_trade_exit_time ON trade_journal(exit_time);
CREATE INDEX idx_trade_coin ON trade_journal(coin);
CREATE INDEX idx_adaptation_applied ON adaptations(applied_at);
CREATE INDEX idx_insight_created ON insights(created_at);
```

---

## Related Documentation

- [SYSTEM-OVERVIEW.md](./SYSTEM-OVERVIEW.md) - System architecture
- [LEARNING-SYSTEM.md](./LEARNING-SYSTEM.md) - How data is used for learning
- [../development/COMPONENT-GUIDE.md](../development/COMPONENT-GUIDE.md) - Database usage in code
