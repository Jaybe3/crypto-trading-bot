# TASK-131: Deep Reflection (Hourly)

**Status:** COMPLETED
**Created:** February 3, 2026
**Completed:** February 3, 2026
**Priority:** High
**Depends On:** TASK-102 (Journal), TASK-120 (Knowledge Brain), TASK-130 (Quick Update)
**Phase:** Phase 2.4 - Reflection Engine

---

## Objective

Implement the Deep Reflection system that runs periodically (hourly or after 10 trades) to analyze recent trading performance, identify patterns, and generate LLM-powered insights for adaptation.

---

## Background

The Reflection Engine has two tiers:

| Tier | When | What It Does | Speed |
|------|------|--------------|-------|
| Quick Update | After every trade | Update coin score, pattern confidence | Instant |
| **Deep Reflection** | Hourly OR after 10 trades | LLM analyzes patterns, generates insights | 30-60s |

TASK-130 implemented Quick Update. This task implements **Deep Reflection** - the "thinking" layer where the bot reflects on its performance and identifies opportunities for improvement.

**Key Principle:** Deep Reflection must produce ACTIONABLE insights. Analysis without adaptation is just logging.

---

## Specification

### Trigger Conditions

Deep Reflection runs when EITHER:
1. **Time-based:** 1 hour has passed since last reflection
2. **Trade-based:** 10 trades have closed since last reflection

Whichever comes first triggers the reflection.

### ReflectionEngine Class

```python
# src/reflection.py

class ReflectionEngine:
    """Periodic LLM-powered analysis and insight generation.

    Runs hourly or after every 10 trades to:
    - Analyze recent trading performance
    - Identify patterns (winning/losing coins, times, regimes)
    - Generate LLM-powered insights
    - Produce adaptation recommendations

    Example:
        >>> engine = ReflectionEngine(journal, knowledge, llm, db)
        >>> await engine.start()  # Runs in background
        >>> # Or manually trigger
        >>> result = await engine.reflect()
    """

    # Trigger thresholds
    REFLECTION_INTERVAL_HOURS = 1
    REFLECTION_TRADE_COUNT = 10

    def __init__(
        self,
        journal: TradeJournal,
        knowledge: KnowledgeBrain,
        llm: LLMInterface,
        db: Database,
    ):
        self.journal = journal
        self.knowledge = knowledge
        self.llm = llm
        self.db = db

        # State
        self.last_reflection_time: Optional[datetime] = None
        self.trades_since_reflection: int = 0
        self._running: bool = False

        # Stats
        self.reflections_completed: int = 0
        self.insights_generated: int = 0
        self.adaptations_suggested: int = 0

    # === Lifecycle ===
    async def start(self) -> None:
        """Start background reflection loop."""

    async def stop(self) -> None:
        """Stop the reflection loop."""

    def on_trade_close(self) -> None:
        """Called by QuickUpdate to track trade count."""

    def should_reflect(self) -> bool:
        """Check if reflection should run now."""

    # === Core Reflection ===
    async def reflect(self) -> ReflectionResult:
        """Run a full reflection cycle."""

    # === Analysis (Quantitative) ===
    def _analyze_by_coin(self, trades: List[JournalEntry]) -> CoinAnalysis:
        """Performance metrics per coin."""

    def _analyze_by_pattern(self, trades: List[JournalEntry]) -> PatternAnalysis:
        """Performance metrics per pattern/strategy."""

    def _analyze_by_time(self, trades: List[JournalEntry]) -> TimeAnalysis:
        """Performance by hour of day and day of week."""

    def _analyze_by_regime(self, trades: List[JournalEntry]) -> RegimeAnalysis:
        """Performance by market regime (BTC trend, volatility)."""

    def _analyze_exits(self, trades: List[JournalEntry]) -> ExitAnalysis:
        """Stop-loss vs take-profit analysis, early exit detection."""

    # === Insight Generation (LLM) ===
    async def _generate_insights(
        self,
        trades: List[JournalEntry],
        coin_analysis: CoinAnalysis,
        pattern_analysis: PatternAnalysis,
        time_analysis: TimeAnalysis,
        regime_analysis: RegimeAnalysis,
        exit_analysis: ExitAnalysis,
    ) -> List[Insight]:
        """Use LLM to find patterns and generate insights."""

    def _build_reflection_prompt(self, analyses: Dict[str, Any]) -> str:
        """Build prompt for LLM insight generation."""

    def _parse_insights(self, llm_response: str) -> List[Insight]:
        """Parse LLM response into structured insights."""

    # === Persistence ===
    def _log_reflection(self, result: ReflectionResult) -> None:
        """Save reflection to database for history."""
```

### Data Classes

```python
@dataclass
class CoinAnalysis:
    """Performance analysis by coin."""
    coin: str
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    avg_winner: float
    avg_loser: float
    best_trade: float
    worst_trade: float
    trend: str  # "improving", "declining", "stable"

@dataclass
class PatternAnalysis:
    """Performance analysis by pattern/strategy."""
    pattern_id: str
    description: str
    total_trades: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    confidence: float

@dataclass
class TimeAnalysis:
    """Performance analysis by time."""
    # By hour (0-23)
    best_hours: List[int]
    worst_hours: List[int]
    hour_win_rates: Dict[int, float]

    # By day (0-6)
    best_days: List[int]
    worst_days: List[int]
    day_win_rates: Dict[int, float]

@dataclass
class RegimeAnalysis:
    """Performance analysis by market regime."""
    btc_up_win_rate: float
    btc_down_win_rate: float
    btc_sideways_win_rate: float
    high_vol_win_rate: float
    low_vol_win_rate: float
    best_regime: str
    worst_regime: str

@dataclass
class ExitAnalysis:
    """Analysis of exit performance."""
    stop_loss_count: int
    take_profit_count: int
    manual_count: int
    stop_loss_rate: float
    avg_stop_loss_pnl: float
    avg_take_profit_pnl: float
    early_exits: int  # Trades that would have been more profitable
    avg_missed_profit: float

@dataclass
class Insight:
    """A single insight from reflection."""
    insight_type: str  # "coin", "pattern", "time", "regime", "exit", "general"
    category: str      # "opportunity", "problem", "observation"
    title: str
    description: str
    evidence: Dict[str, Any]  # Supporting data
    suggested_action: Optional[str] = None
    confidence: float = 0.5  # How confident the LLM is

@dataclass
class ReflectionResult:
    """Complete result of a reflection cycle."""
    timestamp: datetime
    trades_analyzed: int
    period_hours: float

    # Analyses
    coin_analysis: List[CoinAnalysis]
    pattern_analysis: List[PatternAnalysis]
    time_analysis: TimeAnalysis
    regime_analysis: RegimeAnalysis
    exit_analysis: ExitAnalysis

    # LLM output
    insights: List[Insight]
    summary: str  # LLM-generated summary

    # Performance
    analysis_time_ms: float
    llm_time_ms: float
    total_time_ms: float
```

### Insight Types

| Type | Example | Potential Adaptation |
|------|---------|---------------------|
| **coin_underperforming** | "SHIB has 20% win rate over 10 trades" | Blacklist or reduce |
| **coin_overperforming** | "SOL has 75% win rate, $15 profit" | Favor, increase size |
| **pattern_winning** | "momentum_breakout has 70% win rate" | Increase confidence |
| **pattern_losing** | "fade_reversal has 25% win rate" | Deactivate pattern |
| **time_pattern** | "80% of losses occur before 8am UTC" | Add time filter |
| **regime_pattern** | "BTC downtrend = 30% win rate" | Add regime rule |
| **exit_issue** | "40% of stop-losses recover within 5min" | Widen stops |
| **opportunity** | "ETH performs well during US session" | Note for strategist |

### LLM Prompt Template

```python
REFLECTION_SYSTEM_PROMPT = """You are the Reflection Engine for an autonomous trading bot.
Your job is to analyze recent trading performance and generate actionable insights.

You will receive:
1. Performance data broken down by coin, pattern, time, and market regime
2. Raw trade data for the analysis period

Your output must be valid JSON with this structure:
{
    "summary": "Brief 2-3 sentence summary of overall performance",
    "insights": [
        {
            "insight_type": "coin|pattern|time|regime|exit|general",
            "category": "opportunity|problem|observation",
            "title": "Short title (under 50 chars)",
            "description": "Detailed explanation of the insight",
            "evidence": {"metric": value, ...},
            "suggested_action": "Specific action to take (or null)",
            "confidence": 0.0-1.0
        }
    ]
}

Focus on:
- Patterns that are statistically significant (5+ trades)
- Actionable insights that can improve performance
- Both problems (things to stop) and opportunities (things to do more)
- Be specific with numbers and evidence
"""

REFLECTION_USER_PROMPT = """Analyze this trading data and generate insights:

PERIOD: {period_start} to {period_end} ({hours:.1f} hours)
TRADES: {trade_count} total, {win_count} wins ({win_rate:.0%}), ${total_pnl:+.2f} P&L

PERFORMANCE BY COIN:
{coin_analysis_text}

PERFORMANCE BY PATTERN:
{pattern_analysis_text}

PERFORMANCE BY TIME:
Best hours: {best_hours}
Worst hours: {worst_hours}
Weekend win rate: {weekend_win_rate:.0%}

PERFORMANCE BY MARKET REGIME:
BTC Up: {btc_up_win_rate:.0%} win rate
BTC Down: {btc_down_win_rate:.0%} win rate
BTC Sideways: {btc_sideways_win_rate:.0%} win rate

EXIT ANALYSIS:
Stop-loss rate: {stop_loss_rate:.0%}
Early exits (missed profit): {early_exit_count}
Avg missed profit: ${avg_missed_profit:.2f}

Generate 3-7 specific, actionable insights based on this data.
Focus on patterns with 5+ trades for statistical significance.
Respond with JSON only - no other text."""
```

### Trigger Logic

```python
def should_reflect(self) -> bool:
    """Check if reflection should run."""
    # Time-based trigger
    if self.last_reflection_time:
        hours_since = (datetime.now() - self.last_reflection_time).total_seconds() / 3600
        if hours_since >= self.REFLECTION_INTERVAL_HOURS:
            return True

    # Trade count trigger
    if self.trades_since_reflection >= self.REFLECTION_TRADE_COUNT:
        return True

    # First reflection (no history)
    if self.last_reflection_time is None:
        # Need at least some trades
        return self.trades_since_reflection >= 5

    return False
```

### Integration with QuickUpdate

QuickUpdate should notify ReflectionEngine of each trade:

```python
# In QuickUpdate.process_trade_close()
if self.reflection_engine:
    self.reflection_engine.on_trade_close()

    # Check if reflection should run
    if self.reflection_engine.should_reflect():
        # Schedule async reflection (don't block)
        asyncio.create_task(self.reflection_engine.reflect())
```

---

## Technical Approach

### Step 1: Create Data Classes

Create `src/models/reflection.py`:
- CoinAnalysis, PatternAnalysis, TimeAnalysis, RegimeAnalysis, ExitAnalysis
- Insight, ReflectionResult

### Step 2: Implement ReflectionEngine

Create `src/reflection.py`:
- Quantitative analysis methods (_analyze_by_*)
- LLM prompt building and parsing
- Main reflect() method
- Background loop with start()/stop()

### Step 3: Integrate with QuickUpdate

Update `src/quick_update.py`:
- Add reflection_engine parameter
- Call on_trade_close() after each update
- Trigger reflection when conditions met

### Step 4: Wire in main_v2.py

Update initialization:
- Create ReflectionEngine
- Pass to QuickUpdate
- Start reflection loop

### Step 5: Add Database Table

Add `reflections` table to store history:
```sql
CREATE TABLE reflections (
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    trades_analyzed INTEGER,
    period_hours REAL,
    insights TEXT NOT NULL,     -- JSON
    summary TEXT,
    total_time_ms REAL
);
```

### Step 6: Create Unit Tests

Test:
- Analysis calculations are correct
- LLM prompt is well-formed
- Insights are parsed correctly
- Trigger conditions work
- Background loop starts/stops

---

## Files Created

| File | Purpose |
|------|---------|
| `src/models/reflection.py` | Analysis and insight data classes |
| `src/reflection.py` | ReflectionEngine class |
| `tests/test_reflection.py` | Unit tests |

---

## Files Modified

| File | Change |
|------|--------|
| `src/quick_update.py` | Add reflection_engine, trigger reflection |
| `src/main_v2.py` | Create and wire ReflectionEngine |
| `src/database.py` | Add reflections table |

---

## Acceptance Criteria

- [x] ReflectionEngine analyzes trades by coin, pattern, time, regime
- [x] LLM generates structured insights from analysis
- [x] Insights include type, category, evidence, and suggested action
- [x] Reflection triggers hourly OR after 10 trades
- [x] Results saved to database with full context
- [x] Background loop runs without blocking main operations
- [x] Analysis completes in <60 seconds
- [x] Unit tests pass

---

## Verification

### Unit Test

```bash
python -m pytest tests/test_reflection.py -v
```

### Integration Test

```python
from src.reflection import ReflectionEngine
from src.journal import TradeJournal
from src.knowledge import KnowledgeBrain
from src.llm_interface import LLMInterface
from src.database import Database

# Setup
db = Database("data/test_reflection.db")
journal = TradeJournal(db=db)
knowledge = KnowledgeBrain(db)
llm = LLMInterface()

engine = ReflectionEngine(journal, knowledge, llm, db)

# Add some test trades to journal
# ... (mock trades) ...

# Run reflection
result = await engine.reflect()

print(f"Analyzed {result.trades_analyzed} trades")
print(f"Generated {len(result.insights)} insights")
print(f"\nSummary: {result.summary}")

for insight in result.insights:
    print(f"\n[{insight.insight_type}] {insight.title}")
    print(f"  {insight.description}")
    if insight.suggested_action:
        print(f"  -> Action: {insight.suggested_action}")
```

### Manual Test

```bash
# Run with existing trade history
python -c "
import asyncio
from src.reflection import ReflectionEngine
# ... setup ...
result = asyncio.run(engine.reflect())
print(result.summary)
for i in result.insights:
    print(f'- {i.title}: {i.description}')
"
```

---

## Example Reflection Output

### Input: 24 trades over 6 hours

```
PERFORMANCE BY COIN:
  SOL: 8 trades, 75% win, +$12.50
  ETH: 6 trades, 50% win, +$2.00
  DOGE: 5 trades, 20% win, -$8.00
  BTC: 5 trades, 60% win, +$3.00

PERFORMANCE BY TIME:
  Best hours: 14, 15, 16 (US session)
  Worst hours: 3, 4, 5 (Asia session)
```

### Output: Insights

```json
{
  "summary": "Mixed performance with $9.50 profit. SOL is your best performer (75% win rate) while DOGE is significantly underperforming (20%). US session trading shows stronger results than Asia session.",

  "insights": [
    {
      "insight_type": "coin",
      "category": "opportunity",
      "title": "SOL is a strong performer",
      "description": "SOL has a 75% win rate over 8 trades with $12.50 profit. This is your best-performing coin by both win rate and total P&L.",
      "evidence": {"win_rate": 0.75, "trades": 8, "pnl": 12.50},
      "suggested_action": "Consider favoring SOL with increased position sizes",
      "confidence": 0.85
    },
    {
      "insight_type": "coin",
      "category": "problem",
      "title": "DOGE underperforming significantly",
      "description": "DOGE has only a 20% win rate over 5 trades with -$8.00 loss. This meets the threshold for blacklisting (5+ trades, <30% win rate, negative P&L).",
      "evidence": {"win_rate": 0.20, "trades": 5, "pnl": -8.00},
      "suggested_action": "Blacklist DOGE immediately",
      "confidence": 0.90
    },
    {
      "insight_type": "time",
      "category": "observation",
      "title": "US session outperforms Asia session",
      "description": "Trades during hours 14-16 UTC (US open) have significantly better outcomes than hours 3-5 UTC (Asia session).",
      "evidence": {"us_session_win_rate": 0.70, "asia_session_win_rate": 0.30},
      "suggested_action": "Consider adding regime rule to reduce size during Asia session",
      "confidence": 0.70
    }
  ]
}
```

---

## Process Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                      DEEP REFLECTION                                 │
│                                                                     │
│  Trigger: Hourly OR after 10 trades                                 │
│                                                                     │
│  1. Gather Data                                                     │
│     └─► journal.get_recent(hours=24)                               │
│                                                                     │
│  2. Quantitative Analysis                                           │
│     ├─► _analyze_by_coin() → CoinAnalysis[]                        │
│     ├─► _analyze_by_pattern() → PatternAnalysis[]                  │
│     ├─► _analyze_by_time() → TimeAnalysis                          │
│     ├─► _analyze_by_regime() → RegimeAnalysis                      │
│     └─► _analyze_exits() → ExitAnalysis                            │
│                                                                     │
│  3. LLM Insight Generation                                          │
│     ├─► Build prompt with all analyses                              │
│     ├─► Query qwen2.5:14b                                          │
│     └─► Parse JSON response → Insight[]                            │
│                                                                     │
│  4. Log & Return                                                    │
│     ├─► Save to reflections table                                  │
│     └─► Return ReflectionResult                                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    TASK-132: Insight Generation                      │
│                    TASK-133: Adaptation Application                  │
│                                                                     │
│  Takes insights and applies them to Knowledge Brain:                │
│  - Blacklist/favor coins                                            │
│  - Adjust pattern confidence                                        │
│  - Create regime rules                                              │
│  - Update position modifiers                                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Completion Notes

### Implementation Summary

**Date:** February 3, 2026

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/models/reflection.py` | ~250 | Data classes for analysis results and insights |
| `src/reflection.py` | ~500 | ReflectionEngine with analysis and LLM integration |
| `tests/test_reflection.py` | ~300 | Comprehensive unit tests |

### Files Modified

| File | Changes |
|------|---------|
| `src/database.py` | Added `reflections` table, `log_reflection()`, `get_recent_reflections()` |
| `src/quick_update.py` | Added `reflection_engine` parameter and `set_reflection_engine()` |
| `src/main_v2.py` | Creates ReflectionEngine, wires to QuickUpdate, starts/stops with system |

### Key Implementation Details

1. **Analysis Methods** (pure math, fast):
   - `_analyze_by_coin()` - Win rate, P&L, trend per coin
   - `_analyze_by_pattern()` - Performance per strategy/pattern
   - `_analyze_by_time()` - Best/worst hours and days
   - `_analyze_by_regime()` - BTC up/down/sideways performance
   - `_analyze_exits()` - Stop-loss vs take-profit analysis

2. **Trigger Conditions**:
   - Time-based: Every 1 hour since last reflection
   - Trade-based: After 10 trades since last reflection
   - Initial: After 5 trades (minimum for first reflection)

3. **LLM Integration**:
   - Builds structured prompt with all analysis data
   - Parses JSON response into Insight objects
   - Handles markdown-wrapped responses

4. **Insight Structure**:
   ```python
   Insight(
       insight_type="coin",           # coin, pattern, time, regime, exit
       category="problem",            # opportunity, problem, observation
       title="DOGE underperforming",
       description="DOGE has 20% win rate",
       evidence={"win_rate": 0.20},
       suggested_action="Blacklist",
       confidence=0.90
   )
   ```

5. **QuickUpdate Integration**:
   - `on_trade_close()` increments trade counter
   - Triggers reflection when threshold reached

### Database Schema

```sql
CREATE TABLE reflections (
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    trades_analyzed INTEGER NOT NULL,
    period_hours REAL,
    insights TEXT NOT NULL,  -- JSON
    summary TEXT,
    total_time_ms REAL
);
```

### Verification

```bash
python3 -c "
from src.reflection import ReflectionEngine
# ... test code ...
"
# Output: All ReflectionEngine Tests PASSED!
```

---

## Related

- [TASK-130](./TASK-130.md) - Quick Update (triggers reflection)
- [TASK-132](./TASK-132.md) - Insight Generation (advanced insights)
- [TASK-133](./TASK-133.md) - Adaptation Application (applies insights)
- [AUTONOMOUS-TRADER-SPEC.md](../AUTONOMOUS-TRADER-SPEC.md) - Section 6: Reflection Engine
