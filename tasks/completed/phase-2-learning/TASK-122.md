# TASK-122: Pattern Library

**Status:** COMPLETED
**Created:** February 3, 2026
**Completed:** N/A
**Priority:** High
**Depends On:** TASK-120 (Knowledge Brain Data Structures)
**Phase:** Phase 2.3 - Knowledge Brain

---

## Objective

Create a Pattern Library system that manages reusable trading patterns - identifying them from winning trades, tracking their effectiveness, and providing them to the Strategist for informed decision-making.

---

## Background

TASK-120 created the `TradingPattern` dataclass and basic CRUD operations in `KnowledgeBrain`. This task adds:

1. **Pattern Identification** - Extract patterns from successful trades
2. **Pattern Matching** - Check if current market conditions match known patterns
3. **Confidence Management** - Adjust pattern confidence based on track record
4. **Strategist Integration** - Provide high-confidence patterns for condition generation

A pattern is a set of conditions that, when present, suggest a trade is likely to succeed.

---

## Specification

### Pattern Types

| Pattern Type | Description | Example Entry Conditions |
|--------------|-------------|-------------------------|
| **momentum_breakout** | Price breaks key level with momentum | `{"breakout": true, "volume_surge": true, "trend": "up"}` |
| **support_bounce** | Price bounces from support level | `{"near_support": true, "rsi_oversold": true}` |
| **trend_continuation** | Pullback in established trend | `{"trend": "up", "pullback_pct": 2.0, "macd_positive": true}` |
| **reversal** | Trend exhaustion signals | `{"divergence": true, "volume_declining": true}` |
| **range_trade** | Trade within defined range | `{"in_range": true, "near_boundary": true}` |

### PatternLibrary Class

```python
class PatternLibrary:
    """Manages trading patterns and their effectiveness.

    Responsibilities:
    - Store and retrieve patterns
    - Extract patterns from winning trades
    - Match current conditions to known patterns
    - Update pattern confidence based on outcomes
    - Provide high-confidence patterns to Strategist
    """

    def __init__(self, brain: KnowledgeBrain):
        self.brain = brain

    # === Pattern Retrieval ===
    def get_pattern(self, pattern_id: str) -> Optional[TradingPattern]
    def get_active_patterns(self) -> List[TradingPattern]
    def get_high_confidence_patterns(self, min_confidence: float = 0.6) -> List[TradingPattern]
    def get_patterns_for_coin(self, coin: str) -> List[TradingPattern]

    # === Pattern Creation ===
    def create_pattern_from_trade(self, trade: JournalEntry) -> Optional[TradingPattern]
    def create_pattern(
        self,
        pattern_type: str,
        description: str,
        entry_conditions: dict,
        exit_conditions: dict,
        source_trade_id: Optional[str] = None
    ) -> TradingPattern

    # === Pattern Matching ===
    def match_conditions(self, market_state: dict) -> List[PatternMatch]
    def find_similar_patterns(self, conditions: dict) -> List[TradingPattern]

    # === Pattern Updates ===
    def record_pattern_outcome(self, pattern_id: str, won: bool, pnl: float) -> None
    def update_confidence(self, pattern_id: str) -> float
    def deactivate_pattern(self, pattern_id: str, reason: str) -> None
    def reactivate_pattern(self, pattern_id: str) -> None

    # === Strategist Interface ===
    def get_pattern_context(self) -> dict
    def get_suggested_patterns(self, coin: str, market_state: dict) -> List[PatternSuggestion]
```

### PatternMatch and PatternSuggestion

```python
@dataclass
class PatternMatch:
    """Result of matching market conditions to a pattern."""
    pattern: TradingPattern
    match_score: float          # 0-1, how well conditions match
    matched_conditions: dict    # Which conditions were satisfied
    missing_conditions: dict    # Which conditions were not satisfied

@dataclass
class PatternSuggestion:
    """A pattern suggestion for the Strategist."""
    pattern: TradingPattern
    suggested_direction: str    # "LONG" or "SHORT"
    suggested_entry: dict       # Entry parameters
    suggested_exit: dict        # Exit parameters
    confidence: float           # Overall confidence
    reasoning: str              # Why this pattern applies
```

### Confidence Algorithm

Pattern confidence is calculated dynamically based on track record:

```python
def calculate_confidence(self, pattern: TradingPattern) -> float:
    """Calculate confidence score for a pattern.

    Factors:
    - Base: 0.5 (neutral)
    - Win rate contribution: (win_rate - 0.5) * 0.5
    - Usage penalty: Lower confidence if rarely used
    - Recency bonus: Higher confidence if recently successful

    Returns:
        Confidence score between 0.1 and 0.9
    """
    if pattern.times_used < 3:
        return 0.5  # Not enough data

    # Base from win rate
    win_rate_contrib = (pattern.win_rate - 0.5) * 0.5
    base_confidence = 0.5 + win_rate_contrib

    # Usage factor (more usage = more reliable)
    usage_factor = min(1.0, pattern.times_used / 20)

    # Combine
    confidence = base_confidence * (0.7 + 0.3 * usage_factor)

    # Clamp to valid range
    return max(0.1, min(0.9, confidence))
```

### Confidence Thresholds

| Confidence | Status | Position Modifier |
|------------|--------|-------------------|
| >= 0.7 | HIGH | 1.25x position size |
| 0.5 - 0.7 | MEDIUM | 1.0x position size |
| 0.3 - 0.5 | LOW | 0.75x position size |
| < 0.3 | VERY_LOW | Deactivate pattern |

### Pattern Extraction from Trades

When the Reflection Engine finds a winning trade, it can extract a pattern:

```python
def create_pattern_from_trade(self, trade: JournalEntry) -> Optional[TradingPattern]:
    """Extract a pattern from a successful trade.

    Only creates patterns from:
    - Winning trades (pnl > 0)
    - Trades with sufficient context

    Returns:
        New TradingPattern or None if trade unsuitable.
    """
    if trade.pnl_usd <= 0:
        return None

    # Extract entry conditions from trade context
    entry_conditions = {
        "direction": trade.direction,
        "market_regime": trade.market_regime,
        "hour_range": self._get_hour_range(trade.hour_of_day),
    }

    # Add volatility context if available
    if trade.volatility:
        entry_conditions["volatility_range"] = self._get_volatility_range(trade.volatility)

    # Add trend context
    if trade.btc_trend:
        entry_conditions["btc_trend"] = trade.btc_trend

    # Create pattern
    pattern = TradingPattern(
        pattern_id=f"auto_{trade.id[:8]}",
        description=self._generate_description(trade),
        entry_conditions=entry_conditions,
        exit_conditions={
            "stop_loss_pct": self._extract_stop_pct(trade),
            "take_profit_pct": self._extract_tp_pct(trade),
        },
        times_used=1,
        wins=1,
        total_pnl=trade.pnl_usd,
        confidence=0.5,  # Start neutral
    )

    self.brain.add_pattern(pattern)
    return pattern
```

---

## Technical Approach

### Step 1: Create PatternLibrary Class

Create `src/pattern_library.py`:
- PatternMatch dataclass
- PatternSuggestion dataclass
- PatternLibrary class with all methods

### Step 2: Implement Pattern Matching

Create condition matching logic:
- Compare market state to pattern entry_conditions
- Calculate match score based on satisfied conditions
- Handle partial matches

### Step 3: Implement Confidence Management

Add confidence calculation and updates:
- Dynamic confidence based on track record
- Automatic deactivation for poor performers
- Confidence-based position modifiers

### Step 4: Integrate with Strategist

Update Strategist to use pattern library:
- Query high-confidence patterns
- Include pattern reasoning in LLM prompt
- Tag conditions with pattern_id when applicable

### Step 5: Create Unit Tests

Create `tests/test_pattern_library.py`:
- Test pattern CRUD operations
- Test confidence calculations
- Test pattern matching
- Test pattern extraction from trades

---

## Files Created

| File | Purpose |
|------|---------|
| `src/pattern_library.py` | PatternLibrary class with matching and confidence logic |
| `tests/test_pattern_library.py` | Unit tests |

---

## Files Modified

| File | Change |
|------|--------|
| `src/strategist.py` | Query pattern library, include in prompts |
| `src/main.py` | Initialize PatternLibrary, wire to components |

---

## Acceptance Criteria

- [x] PatternLibrary stores and retrieves patterns
- [x] Patterns can be created from winning trades
- [x] Pattern matching returns scored matches
- [x] Confidence updates based on outcomes
- [x] Low-confidence patterns auto-deactivate (<0.3)
- [x] Strategist receives high-confidence patterns
- [x] Pattern suggestions include reasoning
- [x] Unit tests pass

---

## Verification

### Unit Test

```bash
python -m pytest tests/test_pattern_library.py -v
```

### Integration Test

```python
from src.pattern_library import PatternLibrary, PatternMatch
from src.knowledge import KnowledgeBrain
from src.database import Database

# Setup
db = Database("data/test_patterns.db")
brain = KnowledgeBrain(db)
library = PatternLibrary(brain)

# Create a pattern
pattern = library.create_pattern(
    pattern_type="momentum_breakout",
    description="Long on breakout above resistance with volume",
    entry_conditions={"breakout": True, "volume_surge": True, "trend": "up"},
    exit_conditions={"stop_loss_pct": 2.0, "take_profit_pct": 3.0},
)
print(f"Created: {pattern.pattern_id}")

# Record outcomes
library.record_pattern_outcome(pattern.pattern_id, won=True, pnl=5.0)
library.record_pattern_outcome(pattern.pattern_id, won=True, pnl=3.0)
library.record_pattern_outcome(pattern.pattern_id, won=False, pnl=-2.0)

# Check confidence
updated = library.get_pattern(pattern.pattern_id)
print(f"Confidence: {updated.confidence:.2f} (win rate: {updated.win_rate:.1%})")

# Match against market state
market_state = {"breakout": True, "volume_surge": True, "trend": "up"}
matches = library.match_conditions(market_state)
print(f"Matches: {len(matches)}")
for m in matches:
    print(f"  {m.pattern.description}: {m.match_score:.0%}")

# Get pattern context for Strategist
context = library.get_pattern_context()
print(f"High-confidence patterns: {len(context['high_confidence'])}")

print("Pattern Library working!")
```

---

## Example Patterns

### Seed Patterns (Initial Library)

```python
SEED_PATTERNS = [
    {
        "pattern_id": "momentum_breakout_v1",
        "description": "Long on price breakout with volume confirmation",
        "entry_conditions": {
            "price_vs_24h_high": {"op": "gte", "value": 0.98},
            "volume_vs_avg": {"op": "gte", "value": 1.5},
            "btc_trend": "up",
        },
        "exit_conditions": {
            "stop_loss_pct": 2.0,
            "take_profit_pct": 3.0,
        },
    },
    {
        "pattern_id": "support_bounce_v1",
        "description": "Long on bounce from support with oversold RSI",
        "entry_conditions": {
            "near_support": True,
            "rsi": {"op": "lte", "value": 35},
            "btc_trend": {"op": "neq", "value": "down"},
        },
        "exit_conditions": {
            "stop_loss_pct": 1.5,
            "take_profit_pct": 2.5,
        },
    },
    {
        "pattern_id": "trend_pullback_v1",
        "description": "Long on pullback in uptrend",
        "entry_conditions": {
            "trend": "up",
            "pullback_from_high_pct": {"op": "gte", "value": 2.0},
            "pullback_from_high_pct": {"op": "lte", "value": 5.0},
        },
        "exit_conditions": {
            "stop_loss_pct": 2.5,
            "take_profit_pct": 2.0,
        },
    },
]
```

---

## Strategist Prompt Integration

```python
# In Strategist._build_prompt()
pattern_context = self.pattern_library.get_pattern_context()

prompt += f"""
WINNING PATTERNS (use these if conditions match):
{self._format_patterns(pattern_context['high_confidence'])}

PATTERN SUGGESTIONS FOR CURRENT MARKET:
{self._format_suggestions(pattern_context['suggestions'])}

When generating conditions, reference pattern_id if using a known pattern.
"""
```

---

## Completion Notes

### Implementation Summary

**Date:** February 3, 2026

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/pattern_library.py` | 480 | PatternLibrary class with matching and confidence logic |
| `tests/test_pattern_library.py` | 380 | Comprehensive unit tests |

### Files Modified

| File | Changes |
|------|---------|
| `src/strategist.py` | Added `pattern_library` parameter, includes pattern context in prompts |
| `src/main.py` | Initializes PatternLibrary, wires to Strategist |

### Key Implementation Details

1. **PatternMatch**: Scores how well market conditions match a pattern (0-1)

2. **PatternSuggestion**: Provides direction, entry/exit, confidence, and reasoning

3. **Confidence Algorithm**:
   - Base: win_rate contribution (50% +/- 25%)
   - Usage factor: more uses = more reliable
   - Range: 0.1 to 0.9
   - Auto-deactivate below 0.3

4. **Seed Patterns**: 3 initial patterns (momentum_breakout, support_bounce, trend_pullback)

5. **Pattern Extraction**: Creates patterns from winning trades using market context

6. **Integration Flow**:
   ```
   PatternLibrary
       → get_pattern_context() → Strategist prompt
       → match_conditions() → find applicable patterns
       → record_pattern_outcome() → update confidence
   ```

### Position Modifiers

| Confidence | Modifier |
|------------|----------|
| >= 0.7 | 1.25x |
| 0.5 - 0.7 | 1.0x |
| 0.3 - 0.5 | 0.75x |
| < 0.3 | Deactivate |

### Verification

```bash
python3 -c "
from src.pattern_library import PatternLibrary
# ... integration tests ...
"
# Output: All Tests Passed!
```

---

## Related

- [TASK-120](./TASK-120.md) - Knowledge Brain Data Structures (provides TradingPattern)
- [TASK-123](./TASK-123.md) - Strategist ← Knowledge Integration (uses PatternLibrary)
- [TASK-131](./TASK-131.md) - Deep Reflection (creates patterns from trades)
- [AUTONOMOUS-TRADER-SPEC.md](../AUTONOMOUS-TRADER-SPEC.md) - Section 5: Knowledge Brain
