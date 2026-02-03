# Autonomous Self-Learning Trading Bot v2

## Architecture Specification

**Version:** 2.0
**Date:** February 2, 2026
**Status:** DRAFT - Pending Review

---

## Vision

An autonomous trading system that teaches itself to become consistently profitable through its own experience. No human tuning. It trades, journals, reflects, adapts, and improves - continuously and indefinitely.

**Success Criteria:** The bot becomes a profitable trader on its own, measured by sustained positive P&L over time.

---

## Core Principles

1. **Speed enables learning** - Can't learn from wins if you can't capture them
2. **Everything is journaled** - Full context for every decision and outcome
3. **Reflection drives insight** - Pattern recognition across trade history
4. **Adaptation changes behavior** - Insights must become action
5. **Profitability is the measure** - Adaptations that don't improve results are failures
6. **No human in the loop** - System improves autonomously

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AUTONOMOUS TRADER                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         KNOWLEDGE BRAIN                                  │   │
│  │                                                                         │   │
│  │  Persistent, evolving knowledge:                                        │   │
│  │  • Coin performance scores (which coins win/lose for us)                │   │
│  │  • Pattern library (entry/exit conditions that work)                    │   │
│  │  • Market regime rules (when to trade vs sit out)                       │   │
│  │  • Risk parameters (position sizing by confidence)                      │   │
│  │  • Blacklist (what to avoid entirely)                                   │   │
│  │  • Strategy effectiveness scores                                        │   │
│  │                                                                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                          ▲                           │                          │
│                          │ Updates                   │ Informs                  │
│                          │                           ▼                          │
│  ┌──────────────────────────────────┐    ┌──────────────────────────────────┐  │
│  │       REFLECTION ENGINE          │    │          STRATEGIST              │  │
│  │       (Periodic - hourly)        │    │       (Periodic - 2-5 min)       │  │
│  │                                  │    │                                  │  │
│  │  • Analyzes trade journal        │    │  • Reads Knowledge Brain         │  │
│  │  • Finds winning patterns        │    │  • Reads real-time market data   │  │
│  │  • Finds losing patterns         │    │  • Sets trade conditions:        │  │
│  │  • Updates Knowledge Brain       │    │    "LONG SOL if X, Y, Z"         │  │
│  │  • Measures adaptation impact    │    │    "AVOID AXS - blacklisted"     │  │
│  │                                  │    │    "NO TRADES - regime bad"      │  │
│  └──────────────────────────────────┘    └──────────────────────────────────┘  │
│                          ▲                           │                          │
│                          │                           │ Conditions               │
│                          │                           ▼                          │
│  ┌──────────────────────────────────┐    ┌──────────────────────────────────┐  │
│  │        TRADE JOURNAL             │    │           SNIPER                 │  │
│  │     (Every trade - instant)      │    │    (Real-time - milliseconds)    │  │
│  │                                  │    │                                  │  │
│  │  Records:                        │    │  • Monitors WebSocket feed       │  │
│  │  • Entry: price, time, reason    │    │  • Watches for trigger prices    │  │
│  │  • Conditions at entry           │    │  • Executes INSTANTLY            │  │
│  │  • Exit: price, time, reason     │    │  • No LLM in execution path      │  │
│  │  • P&L, duration                 │    │  • Manages open positions        │  │
│  │  • What strategy was used        │    │  • Enforces stop-loss/take-profit│  │
│  │  • Market context                │    │                                  │  │
│  └──────────────────────────────────┘    └──────────────────────────────────┘  │
│                          ▲                           │                          │
│                          │ Logs                      │ Executes                 │
│                          │                           ▼                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         MARKET DATA FEED                                │   │
│  │                     (WebSocket - real-time)                             │   │
│  │                                                                         │   │
│  │  • Price ticks (sub-second)                                             │   │
│  │  • Order flow / CVD (who's buying vs selling)                           │   │
│  │  • Funding rates (leverage positioning)                                 │   │
│  │  • Open interest (money in the market)                                  │   │
│  │  • Volume (real activity)                                               │   │
│  │                                                                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

External:
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Exchange   │     │   Ollama    │     │  Dashboard  │
│  WebSocket  │     │    LLM      │     │  (Monitor)  │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## Component Specifications

### 1. Market Data Feed

**Purpose:** Provide real-time market data fast enough to capture short-term moves.

**Data Sources (via WebSocket):**

| Data | Source | Update Frequency | Use |
|------|--------|------------------|-----|
| Price | Binance/ByBit | Real-time (ms) | Trigger entries/exits |
| Trades | Binance/ByBit | Real-time | Order flow analysis |
| Order book | Binance/ByBit | 100ms | Liquidity/walls |
| Funding rate | Binance/ByBit | 8 hours | Leverage sentiment |
| Open interest | Binance/ByBit | Periodic | Money flow |

**Implementation:**

```python
# src/market_feed.py

class MarketFeed:
    """Real-time WebSocket market data."""
    
    def __init__(self, coins: list[str]):
        self.connections = {}  # WebSocket connections per coin
        self.current_prices = {}  # Latest price per coin
        self.callbacks = []  # Functions to call on price update
        
    async def connect(self):
        """Establish WebSocket connections."""
        
    async def on_price_update(self, coin: str, price: float, timestamp: int):
        """Called on every price tick - must be FAST."""
        
    def subscribe(self, callback: Callable):
        """Register callback for price updates."""
        
    def get_order_flow(self, coin: str, window_seconds: int) -> dict:
        """Get buy vs sell volume over recent window."""
```

**Key Requirement:** This component must be non-blocking and fast. No LLM calls. No database writes in the hot path.

---

### 2. Sniper (Execution Engine)

**Purpose:** Execute trades instantly when conditions are met. No thinking - just action.

**Behavior:**

1. Receives conditions from Strategist: `"BUY SOL if price > 142.50 AND cvd_positive"`
2. Monitors real-time feed for those conditions
3. When triggered: execute immediately
4. Manage position: enforce stop-loss and take-profit
5. Log everything to Trade Journal

**Implementation:**

```python
# src/sniper.py

@dataclass
class TradeCondition:
    coin: str
    direction: Literal["LONG", "SHORT"]
    trigger_price: float
    trigger_condition: Literal["ABOVE", "BELOW"]
    stop_loss_pct: float
    take_profit_pct: float
    position_size_usd: float
    strategy_id: str  # Which strategy generated this
    valid_until: datetime  # Condition expires
    additional_filters: dict  # e.g., {"cvd": "positive", "volume_min": 1000}

class Sniper:
    """Real-time execution engine. No LLM. Pure speed."""
    
    def __init__(self, market_feed: MarketFeed, journal: TradeJournal):
        self.active_conditions: list[TradeCondition] = []
        self.open_positions: dict[str, Position] = {}
        
    def set_conditions(self, conditions: list[TradeCondition]):
        """Called by Strategist with new conditions to watch."""
        
    async def on_price_tick(self, coin: str, price: float, market_data: dict):
        """Called on every price update. MUST BE FAST."""
        # Check if any condition is triggered
        # Check if any position hits stop-loss or take-profit
        # Execute if needed
        
    def execute_entry(self, condition: TradeCondition, price: float):
        """Open a position. Log to journal."""
        
    def execute_exit(self, position: Position, price: float, reason: str):
        """Close a position. Log to journal."""
```

**Key Requirement:** No LLM calls. No complex logic. Pure conditional execution.

---

### 3. Trade Journal

**Purpose:** Record complete context for every trade. This is the raw data for learning.

**What Gets Recorded:**

```python
# src/journal.py

@dataclass
class JournalEntry:
    # Identity
    trade_id: str
    
    # Entry
    entry_time: datetime
    entry_price: float
    entry_reason: str  # "Strategy X triggered: price broke 142.50"
    
    # Context at entry
    coin: str
    direction: str  # LONG or SHORT
    position_size_usd: float
    strategy_id: str  # Which strategy
    market_regime: str  # "trending", "ranging", "volatile"
    funding_rate: float
    open_interest_change: float
    cvd_at_entry: float  # Cumulative volume delta
    volatility_at_entry: float
    hour_of_day: int
    day_of_week: int
    
    # Exit
    exit_time: datetime
    exit_price: float
    exit_reason: str  # "take_profit", "stop_loss", "strategy_exit"
    
    # Outcome
    pnl_usd: float
    pnl_pct: float
    duration_seconds: int
    
    # Post-trade context
    price_5min_after: float  # Did we exit too early?
    price_15min_after: float
```

**Key Requirement:** Capture EVERYTHING. More data = better reflection.

---

### 4. Strategist (LLM Decision Layer)

**Purpose:** Periodically analyze market conditions and set trade conditions for the Sniper.

**Runs:** Every 2-5 minutes (configurable)

**Input:**
- Current market data (prices, funding, OI, volatility)
- Knowledge Brain (what the bot has learned)
- Recent trade performance

**Output:**
- List of `TradeCondition` objects for Sniper to watch
- Reasoning for each (logged but not blocking)

**Implementation:**

```python
# src/strategist.py

class Strategist:
    """LLM-powered strategy generator. Runs periodically, not on every tick."""
    
    def __init__(self, llm: LLMInterface, knowledge: KnowledgeBrain, market: MarketFeed):
        self.llm = llm
        self.knowledge = knowledge
        self.market = market
        
    async def generate_conditions(self) -> list[TradeCondition]:
        """Generate trade conditions based on current state."""
        
        # Build context for LLM
        context = {
            "market_state": self.market.get_summary(),
            "knowledge": self.knowledge.get_active_rules(),
            "blacklist": self.knowledge.get_blacklisted_coins(),
            "recent_performance": self.knowledge.get_recent_performance(),
            "winning_patterns": self.knowledge.get_winning_patterns(),
        }
        
        # Ask LLM for conditions
        prompt = self._build_prompt(context)
        response = await self.llm.query(prompt)
        
        # Parse into TradeCondition objects
        conditions = self._parse_response(response)
        
        return conditions
```

**Prompt Structure:**

```
You are the Strategist for an autonomous trading bot.

CURRENT MARKET STATE:
{market_summary}

YOUR LEARNED KNOWLEDGE:
- Coins that work for us: {good_coins}
- Coins to avoid: {blacklist}
- Patterns that win: {winning_patterns}
- Current regime: {regime}

RECENT PERFORMANCE:
- Last 24h: {win_rate}% win rate, ${pnl} P&L
- Current streak: {streak}

YOUR TASK:
Generate specific trade conditions for the Sniper to watch.
Each condition must include:
- Coin
- Direction (LONG/SHORT)
- Trigger price and condition
- Stop-loss %
- Take-profit %
- Position size as % of balance
- Why this trade (for journaling)

If market conditions are unfavorable, output NO_TRADES with reasoning.

Output format: JSON
```

**Key Requirement:** Strategist USES learned knowledge. It doesn't trade blind.

---

### 5. Knowledge Brain

**Purpose:** Persistent, evolving knowledge about what works and what doesn't.

**What It Tracks:**

```python
# src/knowledge.py

class KnowledgeBrain:
    """The bot's accumulated trading wisdom."""
    
    # Coin performance
    coin_scores: dict[str, CoinScore]  # Win rate, avg P&L, trade count per coin
    
    # Pattern library
    patterns: list[TradingPattern]  # Entry/exit patterns with effectiveness scores
    
    # Blacklist
    blacklist: set[str]  # Coins to never trade
    
    # Strategy effectiveness
    strategy_scores: dict[str, StrategyScore]  # Which strategies are winning
    
    # Regime rules
    regime_rules: list[RegimeRule]  # When to trade vs when to sit out
    
    # Risk parameters
    position_sizing: PositionSizingRules  # How much to bet based on confidence

@dataclass
class CoinScore:
    coin: str
    total_trades: int
    wins: int
    losses: int
    total_pnl: float
    avg_pnl: float
    win_rate: float
    avg_winner: float
    avg_loser: float
    last_updated: datetime
    trend: str  # "improving", "degrading", "stable"

@dataclass
class TradingPattern:
    pattern_id: str
    description: str  # "Long on pullback to support in uptrend"
    entry_conditions: dict
    exit_conditions: dict
    times_used: int
    wins: int
    losses: int
    total_pnl: float
    confidence: float  # 0-1, how much we trust this pattern
    
@dataclass
class RegimeRule:
    rule_id: str
    description: str  # "Don't trade when BTC volatility < 1%"
    condition: dict
    times_followed: int
    times_would_have_lost: int  # Trades we avoided that would have lost
    effectiveness: float
```

**Key Requirement:** Knowledge persists across restarts. It's the bot's memory.

---

### 6. Reflection Engine

**Purpose:** Analyze trade history, find patterns, update Knowledge Brain.

**Runs:** Hourly (or after N trades)

**Process:**

```
1. ANALYZE recent trades (last 24h, last 100 trades)
   - Win rate by coin → Update coin_scores
   - Win rate by pattern → Update patterns
   - Win rate by time of day → Update time_rules
   - Win rate by market regime → Update regime_rules
   
2. IDENTIFY insights
   - "Coin X has lost money on 8 of 10 trades" → Blacklist consideration
   - "Pattern Y has 70% win rate over 20 trades" → Increase confidence
   - "Trades during low volatility lose 80% of time" → Add regime rule
   
3. ADAPT Knowledge Brain
   - Add/remove from blacklist
   - Adjust pattern confidence scores
   - Update position sizing rules
   - Create new patterns from winning trades
   
4. MEASURE adaptation impact
   - Compare performance before vs after last adaptation
   - If adaptation hurt performance, consider rollback
   
5. LOG everything
   - What was analyzed
   - What insights were found
   - What changes were made
   - Why
```

**Implementation:**

```python
# src/reflection.py

class ReflectionEngine:
    """Periodic analysis and adaptation."""
    
    def __init__(self, journal: TradeJournal, knowledge: KnowledgeBrain, llm: LLMInterface):
        self.journal = journal
        self.knowledge = knowledge
        self.llm = llm
        
    async def reflect(self):
        """Run full reflection cycle."""
        
        # Get recent trades
        trades = self.journal.get_recent(hours=24)
        
        # Quantitative analysis
        coin_analysis = self._analyze_by_coin(trades)
        pattern_analysis = self._analyze_by_pattern(trades)
        time_analysis = self._analyze_by_time(trades)
        regime_analysis = self._analyze_by_regime(trades)
        
        # LLM-powered insight generation
        insights = await self._generate_insights(
            trades, coin_analysis, pattern_analysis, time_analysis, regime_analysis
        )
        
        # Apply adaptations
        adaptations = await self._apply_adaptations(insights)
        
        # Log reflection
        self._log_reflection(trades, insights, adaptations)
        
        return adaptations
    
    def _analyze_by_coin(self, trades: list[JournalEntry]) -> dict:
        """Calculate performance metrics per coin."""
        
    async def _generate_insights(self, ...) -> list[Insight]:
        """Use LLM to find patterns humans might miss."""
        
    async def _apply_adaptations(self, insights: list[Insight]) -> list[Adaptation]:
        """Convert insights into Knowledge Brain updates."""
```

**Insight Types:**

| Insight Type | Example | Adaptation |
|--------------|---------|------------|
| Coin Underperforming | "AXS has -$7.86 over 15 trades" | Add to blacklist |
| Coin Overperforming | "SOL has 65% win rate" | Increase position size |
| Pattern Winning | "Breakout + high CVD = 70% win" | Increase pattern confidence |
| Pattern Losing | "Fade the move = 30% win" | Decrease confidence or remove |
| Time Pattern | "Asia session has 80% losses" | Add time-based filter |
| Regime Pattern | "Low volatility = losses" | Add volatility filter |

**Key Requirement:** Reflection must result in BEHAVIORAL CHANGE. Otherwise it's just logging.

---

### 7. Profitability Tracking

**Purpose:** Measure if the bot is actually getting better.

**Metrics:**

```python
# src/metrics.py

@dataclass
class PerformanceSnapshot:
    timestamp: datetime
    period: str  # "hourly", "daily", "weekly"
    
    # Core metrics
    total_trades: int
    win_rate: float
    total_pnl: float
    avg_pnl_per_trade: float
    
    # Risk metrics
    max_drawdown: float
    sharpe_ratio: float
    profit_factor: float  # gross profit / gross loss
    
    # Learning metrics
    knowledge_version: int  # Increments on each adaptation
    active_patterns: int
    blacklisted_coins: int
    
    # Comparison
    vs_previous_period: float  # % change in P&L
    vs_baseline: float  # % improvement since start
```

**Tracking Adaptation Effectiveness:**

```python
@dataclass
class AdaptationRecord:
    adaptation_id: str
    timestamp: datetime
    description: str  # "Blacklisted AXS"
    
    # Performance before
    pre_win_rate: float
    pre_pnl_24h: float
    
    # Performance after (updated over time)
    post_win_rate: float
    post_pnl_24h: float
    
    # Verdict
    impact: str  # "positive", "negative", "neutral"
    should_keep: bool
```

**Key Requirement:** If an adaptation makes things worse, the bot should notice and potentially reverse it.

---

## The Learning Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                     THE LEARNING LOOP                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────┐                                                   │
│   │  START  │                                                   │
│   └────┬────┘                                                   │
│        │                                                        │
│        ▼                                                        │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 1. STRATEGIST generates conditions based on knowledge   │   │
│   └────────────────────────┬────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 2. SNIPER watches market, executes when triggered       │   │
│   └────────────────────────┬────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 3. JOURNAL records everything about the trade           │   │
│   └────────────────────────┬────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 4. REFLECTION analyzes trades, finds patterns           │   │
│   └────────────────────────┬────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 5. ADAPTATION updates Knowledge Brain                   │   │
│   └────────────────────────┬────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 6. MEASURE: Did we get better? Track profitability.     │   │
│   └────────────────────────┬────────────────────────────────┘   │
│                            │                                    │
│                            │ Loop back                          │
│                            │                                    │
│        ┌───────────────────┘                                    │
│        │                                                        │
│        ▼                                                        │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 1. STRATEGIST now has BETTER knowledge                  │   │
│   │    - Knows which coins to avoid                         │   │
│   │    - Knows which patterns work                          │   │
│   │    - Knows when to sit out                              │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   REPEAT FOREVER → System continuously improves                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema (New)

```sql
-- Real-time market data cache
CREATE TABLE market_ticks (
    id INTEGER PRIMARY KEY,
    coin TEXT NOT NULL,
    price REAL NOT NULL,
    volume REAL,
    timestamp INTEGER NOT NULL,
    INDEX idx_coin_time (coin, timestamp)
);

-- Trade journal (replaces closed_trades)
CREATE TABLE trade_journal (
    id TEXT PRIMARY KEY,
    
    -- Entry
    entry_time TIMESTAMP NOT NULL,
    entry_price REAL NOT NULL,
    entry_reason TEXT NOT NULL,
    
    -- Context
    coin TEXT NOT NULL,
    direction TEXT NOT NULL,
    position_size_usd REAL NOT NULL,
    strategy_id TEXT,
    pattern_id TEXT,
    market_regime TEXT,
    funding_rate REAL,
    open_interest_change REAL,
    cvd_at_entry REAL,
    volatility REAL,
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
    price_5min_after REAL,
    price_15min_after REAL,
    
    INDEX idx_coin (coin),
    INDEX idx_strategy (strategy_id),
    INDEX idx_pattern (pattern_id),
    INDEX idx_time (entry_time)
);

-- Knowledge: Coin scores
CREATE TABLE coin_scores (
    coin TEXT PRIMARY KEY,
    total_trades INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    total_pnl REAL DEFAULT 0,
    win_rate REAL DEFAULT 0,
    avg_winner REAL DEFAULT 0,
    avg_loser REAL DEFAULT 0,
    is_blacklisted BOOLEAN DEFAULT FALSE,
    blacklist_reason TEXT,
    last_updated TIMESTAMP
);

-- Knowledge: Trading patterns
CREATE TABLE trading_patterns (
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
    created_at TIMESTAMP,
    last_used TIMESTAMP
);

-- Knowledge: Regime rules
CREATE TABLE regime_rules (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    condition TEXT NOT NULL,  -- JSON
    action TEXT NOT NULL,     -- "NO_TRADE", "REDUCE_SIZE", etc.
    times_triggered INTEGER DEFAULT 0,
    estimated_saves REAL DEFAULT 0,  -- P&L saved by following rule
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP
);

-- Reflection log
CREATE TABLE reflections (
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    trades_analyzed INTEGER,
    insights TEXT NOT NULL,     -- JSON array of insights
    adaptations TEXT NOT NULL,  -- JSON array of changes made
    pre_metrics TEXT,           -- JSON snapshot before
    post_metrics TEXT           -- JSON snapshot after (updated later)
);

-- Adaptation tracking
CREATE TABLE adaptations (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    type TEXT NOT NULL,         -- "blacklist", "pattern_update", "regime_rule", etc.
    description TEXT NOT NULL,
    details TEXT,               -- JSON
    pre_win_rate REAL,
    pre_pnl_24h REAL,
    post_win_rate REAL,
    post_pnl_24h REAL,
    impact TEXT,                -- "positive", "negative", "neutral"
    is_active BOOLEAN DEFAULT TRUE
);

-- Performance snapshots
CREATE TABLE performance_snapshots (
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    period TEXT NOT NULL,       -- "hourly", "daily"
    total_trades INTEGER,
    win_rate REAL,
    total_pnl REAL,
    avg_pnl REAL,
    max_drawdown REAL,
    sharpe_ratio REAL,
    profit_factor REAL,
    knowledge_version INTEGER,
    active_patterns INTEGER,
    blacklisted_coins INTEGER
);

-- Strategist conditions (active)
CREATE TABLE active_conditions (
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

---

## File Structure

```
src/
├── main.py                 # Orchestration - starts all components
├── market_feed.py          # WebSocket real-time data
├── sniper.py               # Fast execution engine
├── journal.py              # Trade journaling
├── strategist.py           # LLM strategy generation
├── knowledge.py            # Knowledge Brain
├── reflection.py           # Reflection engine
├── metrics.py              # Performance tracking
├── database.py             # Database operations
├── llm_interface.py        # Ollama communication (existing, modified)
└── dashboard.py            # Monitoring UI (existing, modified)

config/
├── coins.json              # Tradeable coins list
└── settings.py             # Configuration

tests/
├── test_sniper.py
├── test_reflection.py
├── test_knowledge.py
└── test_integration.py
```

---

## Implementation Phases

### Phase 1: Speed Infrastructure (Week 1)
- [ ] WebSocket market data feed (Binance)
- [ ] Sniper execution engine
- [ ] Basic trade journal
- [ ] Wire up: prices flow, sniper can execute
- **Milestone:** Can execute a trade within 100ms of condition trigger

### Phase 2: Strategist Integration (Week 1-2)
- [ ] Strategist component with LLM
- [ ] Condition generation and parsing
- [ ] Strategist → Sniper handoff
- **Milestone:** LLM sets conditions, Sniper executes them

### Phase 3: Knowledge Brain (Week 2)
- [ ] Knowledge Brain data structures
- [ ] Coin scoring
- [ ] Pattern library
- [ ] Strategist reads from Knowledge Brain
- **Milestone:** Strategist decisions informed by knowledge

### Phase 4: Reflection Engine (Week 2-3)
- [ ] Trade analysis functions
- [ ] Pattern recognition
- [ ] Insight generation (LLM-assisted)
- [ ] Adaptation application
- **Milestone:** Reflection runs, updates Knowledge Brain

### Phase 5: Closed Loop (Week 3)
- [ ] Wire everything together
- [ ] Profitability tracking
- [ ] Adaptation effectiveness monitoring
- [ ] Dashboard updates
- **Milestone:** Full loop running autonomously

### Phase 6: Tuning & Validation (Week 3-4)
- [ ] Run in paper trading mode
- [ ] Validate learning is occurring
- [ ] Validate adaptations improve performance
- [ ] Fix issues
- **Milestone:** Bot demonstrably improving over time

---

## Success Criteria

The system is working when:

1. **Speed:** Trades execute within 100ms of trigger
2. **Journaling:** Every trade has full context recorded
3. **Learning:** New patterns/rules created from trade data
4. **Adaptation:** Knowledge Brain changes based on performance
5. **Improvement:** Win rate and P&L trend upward over time
6. **Autonomy:** No human intervention required for 7+ days

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| WebSocket disconnection | Auto-reconnect, halt trading if feed stale |
| Bad adaptation hurts performance | Track adaptation impact, allow rollback |
| LLM generates bad conditions | Validate conditions, enforce risk limits |
| Overfitting to recent data | Require minimum trade count before adaptation |
| Knowledge Brain corruption | Regular backups, versioning |
| Exchange API issues | Circuit breaker, manual intervention alerts |

---

## Decisions (Finalized)

| Question | Decision | Rationale |
|----------|----------|-----------|
| Exchange | Binance | Higher volume, more pairs |
| Paper trading | Simulate locally | Full control until ready for real money |
| Initial knowledge | Blank | Bot learns from scratch, no assumptions |
| Reflection frequency | Two-tier (see below) | Balance speed with depth |
| Adaptation aggressiveness | Statistical thresholds (see below) | Data-driven, not arbitrary |

### Two-Tier Reflection

| Tier | When | What It Does | Speed |
|------|------|--------------|-------|
| **Quick Update** | After every trade | Update coin score, log outcome, simple math | Instant |
| **Deep Reflection** | Hourly OR after 10 trades | LLM analyzes patterns, generates insights, updates strategies | 30-60s |

### Adaptation Thresholds

**BLACKLIST when ALL true:**
- Minimum 5 trades (enough data)
- Win rate < 30% (consistently losing)
- Net P&L negative (actually costing money)

**REDUCE POSITION SIZE when:**
- Minimum 5 trades
- Win rate < 45%
- Trending worse (last 5 trades worse than previous 5)

**REMOVE FROM BLACKLIST:**
- After 7 days, re-evaluate with 1 small test trade
- Or when market conditions change significantly

---

## Observability & Dashboard

### Purpose
During paper trading, the operator needs to observe what the bot is learning and course-correct bad habits before they're ingrained.

### Real-Time View

```
┌─────────────────────────────────────────────────────────────────────────┐
│ AUTONOMOUS TRADER - Paper Trading Mode                    [LEARNING]   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ ACTIVE CONDITIONS (Sniper watching)                                     │
│ ┌─────────────────────────────────────────────────────────────────────┐│
│ │ LONG SOL if price > $142.50                    [expires in 3:42]   ││
│ │   Reason: Momentum breakout, 68% confidence pattern                ││
│ │   Stop: 2% | Target: 1.5% | Size: $25                              ││
│ ├─────────────────────────────────────────────────────────────────────┤│
│ │ LONG ETH if price > $2,850                     [expires in 3:42]   ││
│ │   Reason: Support bounce, funding negative (shorts crowded)        ││
│ │   Stop: 1.5% | Target: 1% | Size: $30                              ││
│ └─────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│ KNOWLEDGE BRAIN                                                         │
│ ┌──────────────────────────────────────────────────────────────────────┐│
│ │ Coin Scores (Top/Bottom)                                            ││
│ │ ✅ SOL:  12 trades | 67% win | +$4.20    [FAVORED]                  ││
│ │ ✅ ETH:   8 trades | 62% win | +$2.10    [ACTIVE]                   ││
│ │ ⚠️ BTC:  16 trades | 44% win | +$0.07    [REDUCED SIZE]             ││
│ │ 🚫 AXS:  15 trades | 27% win | -$7.86    [BLACKLISTED]              ││
│ └──────────────────────────────────────────────────────────────────────┘│
│ ┌──────────────────────────────────────────────────────────────────────┐│
│ │ Active Patterns                                                     ││
│ │ • Momentum breakout (68% conf) - 22 uses, 15 wins                   ││
│ │ • Support bounce (61% conf) - 14 uses, 9 wins                       ││
│ │ • Funding squeeze (55% conf) - 8 uses, 5 wins [TESTING]             ││
│ └──────────────────────────────────────────────────────────────────────┘│
│ ┌──────────────────────────────────────────────────────────────────────┐│
│ │ Active Rules                                                        ││
│ │ • "No trades when BTC 1h volatility < 0.5%" - ACTIVE                ││
│ │ • "Reduce size during Asia session" - ACTIVE                        ││
│ └──────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│ RECENT ADAPTATIONS                                                      │
│ ┌──────────────────────────────────────────────────────────────────────┐│
│ │ [2 hours ago] Blacklisted AXS: 27% win rate over 15 trades          ││
│ │ [5 hours ago] Increased SOL size: 67% win rate, trending up         ││
│ │ [Yesterday] Added rule: "No trades during low volatility"           ││
│ └──────────────────────────────────────────────────────────────────────┘│
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Dashboard Sections

| Section | What It Shows |
|---------|---------------|
| **Active Conditions** | What Sniper is watching for, with reasoning |
| **Coin Scores** | Performance by coin with status (Active/Reduced/Blacklisted) |
| **Active Patterns** | Entry/exit patterns with confidence and stats |
| **Regime Rules** | Current rules and whether they're triggered |
| **Adaptation Log** | What changed, when, and why |
| **Trade Feed** | Recent trades with full context |

### Manual Overrides (Paper Trading Only)

| Override | Purpose |
|----------|---------|
| Force blacklist coin | Stop trading something you see failing |
| Remove from blacklist | Give a coin another chance |
| Disable pattern | Turn off a pattern that's not working |
| Disable rule | Turn off a regime rule |
| Add note | Document why you made an override |

Overrides are logged so the bot can potentially learn from your corrections.

---

## Next Steps

1. ✅ Spec reviewed and finalized
2. Create implementation task files
3. Begin Phase 1: Speed Infrastructure

---

*Created: February 2, 2026*
*Status: APPROVED - Ready for implementation*
