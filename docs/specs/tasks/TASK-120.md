# TASK-120: Knowledge Brain Data Structures

**Status:** COMPLETED
**Created:** February 3, 2026
**Completed:** N/A
**Priority:** High
**Depends On:** TASK-102 (Trade Journal)
**Phase:** Phase 2.3 - Knowledge Brain

---

## Objective

Create the Knowledge Brain component with data structures and persistence for storing the bot's accumulated trading wisdom. This is the foundation that enables the bot to learn from its trades.

---

## Background

The bot currently trades without memory - each session starts fresh. The Knowledge Brain provides:

1. **Coin Scores** - Track which coins are profitable/losing for us
2. **Trading Patterns** - Store entry/exit patterns with effectiveness scores
3. **Regime Rules** - Know when to trade vs sit out
4. **Blacklist** - Coins to avoid entirely
5. **Persistence** - Survive restarts, accumulate knowledge over time

The Strategist will read from Knowledge Brain to make informed decisions. The Reflection Engine (Phase 2.4) will write to it.

---

## Specification

### Data Classes

```python
@dataclass
class CoinScore:
    """Performance metrics for a specific coin."""
    coin: str                    # "SOL", "ETH", etc.
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    avg_pnl: float = 0.0
    win_rate: float = 0.0
    avg_winner: float = 0.0      # Average profit on winning trades
    avg_loser: float = 0.0       # Average loss on losing trades
    is_blacklisted: bool = False
    blacklist_reason: str = ""
    last_updated: datetime = None
    trend: str = "stable"        # "improving", "degrading", "stable"

@dataclass
class TradingPattern:
    """A reusable trading pattern with effectiveness tracking."""
    pattern_id: str
    description: str             # "Long on pullback to support in uptrend"
    entry_conditions: dict       # JSON-serializable conditions
    exit_conditions: dict        # JSON-serializable conditions
    times_used: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    confidence: float = 0.5      # 0-1, how much we trust this pattern
    is_active: bool = True
    created_at: datetime = None
    last_used: datetime = None

@dataclass
class RegimeRule:
    """A rule about when to trade or sit out."""
    rule_id: str
    description: str             # "Don't trade when BTC volatility < 1%"
    condition: dict              # JSON-serializable condition
    action: str                  # "NO_TRADE", "REDUCE_SIZE", "INCREASE_SIZE"
    times_triggered: int = 0
    estimated_saves: float = 0.0 # P&L saved by following this rule
    is_active: bool = True
    created_at: datetime = None
```

### KnowledgeBrain Class

```python
class KnowledgeBrain:
    """The bot's accumulated trading wisdom.

    Provides read/write access to learned knowledge:
    - Coin performance scores
    - Trading patterns
    - Regime rules
    - Blacklist

    All data persists to SQLite database.
    """

    def __init__(self, db: Database):
        self.db = db
        self._coin_scores: dict[str, CoinScore] = {}
        self._patterns: dict[str, TradingPattern] = {}
        self._regime_rules: dict[str, RegimeRule] = {}
        self._load_from_db()

    # === Coin Scores ===
    def get_coin_score(self, coin: str) -> Optional[CoinScore]
    def get_all_coin_scores(self) -> list[CoinScore]
    def update_coin_score(self, coin: str, trade_result: dict) -> CoinScore
    def get_good_coins(self, min_trades: int = 5, min_win_rate: float = 0.5) -> list[str]
    def get_bad_coins(self, min_trades: int = 5, max_win_rate: float = 0.35) -> list[str]

    # === Blacklist ===
    def blacklist_coin(self, coin: str, reason: str) -> None
    def unblacklist_coin(self, coin: str) -> None
    def get_blacklisted_coins(self) -> list[str]
    def is_blacklisted(self, coin: str) -> bool

    # === Patterns ===
    def get_pattern(self, pattern_id: str) -> Optional[TradingPattern]
    def get_active_patterns(self) -> list[TradingPattern]
    def add_pattern(self, pattern: TradingPattern) -> None
    def update_pattern_stats(self, pattern_id: str, won: bool, pnl: float) -> None
    def deactivate_pattern(self, pattern_id: str) -> None
    def get_winning_patterns(self, min_uses: int = 5, min_win_rate: float = 0.55) -> list[TradingPattern]

    # === Regime Rules ===
    def get_active_rules(self) -> list[RegimeRule]
    def add_rule(self, rule: RegimeRule) -> None
    def update_rule_stats(self, rule_id: str, triggered: bool, saved_pnl: float = 0) -> None
    def check_rules(self, market_state: dict) -> list[str]  # Returns actions

    # === Strategist Interface ===
    def get_knowledge_context(self) -> dict:
        """Get summarized knowledge for Strategist prompts."""
        return {
            "good_coins": self.get_good_coins(),
            "avoid_coins": self.get_blacklisted_coins() + self.get_bad_coins(),
            "active_rules": [r.description for r in self.get_active_rules()],
            "winning_patterns": [p.description for p in self.get_winning_patterns()],
        }
```

### Database Schema

Add tables to `src/database.py`:

```sql
-- Coin performance scores
CREATE TABLE IF NOT EXISTS coin_scores (
    coin TEXT PRIMARY KEY,
    total_trades INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    total_pnl REAL DEFAULT 0,
    avg_pnl REAL DEFAULT 0,
    win_rate REAL DEFAULT 0,
    avg_winner REAL DEFAULT 0,
    avg_loser REAL DEFAULT 0,
    is_blacklisted BOOLEAN DEFAULT FALSE,
    blacklist_reason TEXT,
    trend TEXT DEFAULT 'stable',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trading patterns
CREATE TABLE IF NOT EXISTS trading_patterns (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    entry_conditions TEXT NOT NULL,  -- JSON
    exit_conditions TEXT NOT NULL,   -- JSON
    times_used INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    total_pnl REAL DEFAULT 0,
    confidence REAL DEFAULT 0.5,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP
);

-- Regime rules
CREATE TABLE IF NOT EXISTS regime_rules (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    condition TEXT NOT NULL,  -- JSON
    action TEXT NOT NULL,
    times_triggered INTEGER DEFAULT 0,
    estimated_saves REAL DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Technical Approach

### Step 1: Create Data Classes

Create `src/models/knowledge.py`:
- `CoinScore` dataclass with serialization
- `TradingPattern` dataclass with serialization
- `RegimeRule` dataclass with serialization

### Step 2: Add Database Tables

Update `src/database.py`:
- Add table creation in `create_tables()`
- Add CRUD methods for each table

### Step 3: Create KnowledgeBrain Class

Create `src/knowledge.py`:
- Initialize with database
- Load existing data on startup
- Implement all read/write methods
- Cache in memory, persist on change

### Step 4: Update Models Export

Update `src/models/__init__.py`:
- Export new data classes

### Step 5: Create Unit Tests

Create `tests/test_knowledge.py`:
- Test each data class
- Test KnowledgeBrain CRUD operations
- Test persistence across restarts

---

## Files Created

| File | Purpose |
|------|---------|
| `src/models/knowledge.py` | CoinScore, TradingPattern, RegimeRule dataclasses |
| `src/knowledge.py` | KnowledgeBrain class |
| `tests/test_knowledge.py` | Unit tests |

---

## Files Modified

| File | Change |
|------|--------|
| `src/database.py` | Add knowledge tables and CRUD methods |
| `src/models/__init__.py` | Export knowledge dataclasses |

---

## Acceptance Criteria

- [x] CoinScore tracks wins/losses/PnL per coin
- [x] TradingPattern stores reusable patterns with effectiveness
- [x] RegimeRule stores market condition rules
- [x] Blacklist functionality works (add/remove/check)
- [x] All data persists to SQLite
- [x] Data loads correctly on restart
- [x] get_knowledge_context() returns data for Strategist
- [x] Unit tests pass

---

## Verification

### Unit Tests

```bash
python -m pytest tests/test_knowledge.py -v
```

### Integration Test

```python
from src.knowledge import KnowledgeBrain
from src.database import Database

# Create fresh brain
db = Database(":memory:")
brain = KnowledgeBrain(db)

# Test coin scoring
brain.update_coin_score("SOL", {"won": True, "pnl": 5.0})
brain.update_coin_score("SOL", {"won": True, "pnl": 3.0})
brain.update_coin_score("SOL", {"won": False, "pnl": -2.0})

score = brain.get_coin_score("SOL")
assert score.total_trades == 3
assert score.wins == 2
assert score.win_rate == 2/3

# Test blacklist
brain.blacklist_coin("AXS", "Lost 8 of 10 trades")
assert brain.is_blacklisted("AXS")
assert "AXS" in brain.get_blacklisted_coins()

# Test Strategist context
context = brain.get_knowledge_context()
assert "SOL" in context["good_coins"]
assert "AXS" in context["avoid_coins"]

print("Knowledge Brain working!")
```

### Persistence Test

```python
# Create and populate
db = Database("data/test_kb.db")
brain = KnowledgeBrain(db)
brain.update_coin_score("ETH", {"won": True, "pnl": 10.0})
brain.blacklist_coin("SAND", "Terrible performance")

# Simulate restart
brain2 = KnowledgeBrain(Database("data/test_kb.db"))
assert brain2.get_coin_score("ETH").wins == 1
assert brain2.is_blacklisted("SAND")

print("Persistence working!")
```

---

## Adaptation Thresholds

From spec - these will be used by Reflection Engine:

| Action | Condition |
|--------|-----------|
| **Blacklist** | min 5 trades AND win_rate < 30% AND total_pnl < 0 |
| **Reduce Size** | min 5 trades AND win_rate < 45% AND trending worse |
| **Unblacklist** | After 7 days, re-evaluate with 1 small test trade |

---

## Completion Notes

### Implementation Summary

**Date:** February 3, 2026

### Files Created

| File | Purpose |
|------|---------|
| `src/models/knowledge.py` | CoinScore, TradingPattern, RegimeRule dataclasses with serialization |
| `src/knowledge.py` | KnowledgeBrain class (389 lines) with full CRUD and Strategist interface |
| `tests/test_knowledge.py` | Comprehensive unit tests (42 test cases) |

### Files Modified

| File | Changes |
|------|---------|
| `src/database.py` | Added 3 tables (coin_scores, trading_patterns, regime_rules) + indexes + CRUD methods |
| `src/models/__init__.py` | Export CoinScore, TradingPattern, RegimeRule |

### Key Implementation Details

1. **CoinScore**: Tracks per-coin performance with running averages for winners/losers, trend detection, and blacklist support

2. **TradingPattern**: Stores entry/exit conditions as JSON, tracks times_used/wins/losses, calculates confidence based on win rate

3. **RegimeRule**: Condition-checking with operators (lt, gt, eq, etc.), supports NO_TRADE, REDUCE_SIZE, INCREASE_SIZE, CAUTION actions

4. **KnowledgeBrain**:
   - In-memory cache backed by SQLite for persistence
   - Loads all data on startup
   - Provides `get_knowledge_context()` for Strategist integration
   - `check_rules()` evaluates market state against all active rules

### Database Tables Added

```sql
-- coin_scores: Coin performance tracking
-- trading_patterns: Reusable pattern storage
-- regime_rules: Market condition rules
```

### Verification

```bash
# All tests pass
python3 -c "
from src.knowledge import KnowledgeBrain
from src.database import Database
# ... integration test ...
"
# Output: Knowledge Brain working! Persistence working!
```

---

## Related

- [AUTONOMOUS-TRADER-SPEC.md](../AUTONOMOUS-TRADER-SPEC.md) - Section 5: Knowledge Brain
- [TASK-121](./TASK-121.md) - Coin Scoring System (uses CoinScore)
- [TASK-122](./TASK-122.md) - Pattern Library (uses TradingPattern)
- [TASK-123](./TASK-123.md) - Strategist ← Knowledge Integration
- [TASK-130](./TASK-130.md) - Quick Update (writes to Knowledge Brain)
