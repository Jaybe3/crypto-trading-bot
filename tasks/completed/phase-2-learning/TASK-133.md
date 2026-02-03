# TASK-133: Adaptation Application

**Status:** COMPLETE
**Created:** February 3, 2026
**Completed:** February 3, 2026
**Priority:** Critical
**Depends On:** TASK-131 (Deep Reflection), TASK-120 (Knowledge Brain), TASK-121 (CoinScorer), TASK-122 (PatternLibrary)
**Phase:** Phase 2.4 - Reflection Engine

---

## Objective

Implement the Adaptation Application system that converts insights from Deep Reflection into actual behavioral changes in the Knowledge Brain. This completes the learning loop: **Reflect → Insight → Adapt → Improve**.

---

## Background

TASK-131 generates insights like:
- "DOGE has 20% win rate over 10 trades" (suggested action: blacklist)
- "SOL has 75% win rate, $15 profit" (suggested action: favor)
- "Asia session (0-8 UTC) has 30% win rate" (suggested action: add time filter)

But these insights are **never acted upon**. The bot logs them but doesn't change its behavior.

**This task closes the loop** by automatically applying insights to the Knowledge Brain, making the bot actually learn from its experience.

**Key Principle:** Insights without adaptation is just logging. Adaptation is what makes the bot autonomous.

---

## Specification

### AdaptationEngine Class

```python
# src/adaptation.py

class AdaptationEngine:
    """Converts insights into Knowledge Brain changes.

    Takes insights from ReflectionEngine and applies them:
    - Blacklist/favor coins
    - Adjust pattern confidence
    - Create regime rules
    - Deactivate failing patterns

    All adaptations are logged with pre/post metrics for effectiveness tracking.

    Example:
        >>> engine = AdaptationEngine(knowledge, coin_scorer, pattern_library, db)
        >>> adaptations = engine.apply_insights(insights)
        >>> for a in adaptations:
        ...     print(f"{a.action}: {a.description}")
    """

    def __init__(
        self,
        knowledge: KnowledgeBrain,
        coin_scorer: CoinScorer,
        pattern_library: PatternLibrary,
        db: Database,
    ):
        self.knowledge = knowledge
        self.coin_scorer = coin_scorer
        self.pattern_library = pattern_library
        self.db = db

    def apply_insights(self, insights: List[Insight]) -> List[AdaptationRecord]:
        """Apply a list of insights and return records of changes made."""

    def _apply_coin_insight(self, insight: Insight) -> Optional[AdaptationRecord]:
        """Handle coin-related insights (blacklist, favor, reduce)."""

    def _apply_pattern_insight(self, insight: Insight) -> Optional[AdaptationRecord]:
        """Handle pattern-related insights (deactivate, boost confidence)."""

    def _apply_time_insight(self, insight: Insight) -> Optional[AdaptationRecord]:
        """Handle time-based insights (create time filter rules)."""

    def _apply_regime_insight(self, insight: Insight) -> Optional[AdaptationRecord]:
        """Handle regime-based insights (create regime rules)."""

    def _should_apply(self, insight: Insight) -> bool:
        """Check if insight meets threshold for automatic application."""

    def _get_pre_metrics(self) -> Dict[str, Any]:
        """Capture current performance metrics before adaptation."""

    def _log_adaptation(self, record: AdaptationRecord) -> None:
        """Log adaptation to database for effectiveness tracking."""
```

### AdaptationRecord Dataclass

```python
@dataclass
class AdaptationRecord:
    """Record of an adaptation applied."""

    adaptation_id: str
    timestamp: datetime
    insight_id: str          # Which insight triggered this
    insight_type: str        # coin, pattern, time, regime

    # What was done
    action: str              # "blacklist", "favor", "create_rule", "deactivate_pattern"
    target: str              # Coin symbol, pattern_id, or rule_id
    description: str         # Human-readable description

    # Pre-adaptation state
    pre_metrics: Dict[str, Any]  # Win rate, P&L before

    # Confidence
    insight_confidence: float
    auto_applied: bool       # True if auto-applied, False if manual

    # Post-adaptation (filled later by effectiveness tracking)
    post_metrics: Optional[Dict[str, Any]] = None
    effectiveness: Optional[str] = None  # "improved", "no_change", "degraded"
```

### Insight-to-Action Mapping

| Insight Type | Category | Confidence Threshold | Action |
|--------------|----------|---------------------|--------|
| coin | problem | >= 0.8 | `blacklist_coin()` |
| coin | problem | >= 0.6 | `reduce_coin()` (log only) |
| coin | opportunity | >= 0.8 | `favor_coin()` |
| pattern | problem | >= 0.8 | `deactivate_pattern()` |
| pattern | opportunity | >= 0.7 | `boost_pattern_confidence()` |
| time | problem | >= 0.7 | `create_time_rule()` |
| regime | problem | >= 0.7 | `create_regime_rule()` |

### Action Implementations

```python
def _apply_coin_insight(self, insight: Insight) -> Optional[AdaptationRecord]:
    """Handle coin-related insights."""
    coin = insight.evidence.get("coin") or self._extract_coin(insight.title)
    if not coin:
        return None

    if insight.category == "problem":
        # Underperforming coin
        if insight.confidence >= 0.8:
            # High confidence - blacklist
            win_rate = insight.evidence.get("win_rate", 0)
            trades = insight.evidence.get("trades", 0)

            if win_rate < 0.30 and trades >= 5:
                self.knowledge.blacklist_coin(coin, insight.description)
                return AdaptationRecord(
                    action="blacklist",
                    target=coin,
                    description=f"Blacklisted {coin}: {insight.description}",
                    ...
                )

    elif insight.category == "opportunity":
        # Overperforming coin
        if insight.confidence >= 0.8:
            win_rate = insight.evidence.get("win_rate", 0)
            if win_rate >= 0.60:
                # Mark as favored (CoinScorer will pick this up)
                self.knowledge.favor_coin(coin, insight.description)
                return AdaptationRecord(
                    action="favor",
                    target=coin,
                    description=f"Favored {coin}: {insight.description}",
                    ...
                )

    return None


def _apply_time_insight(self, insight: Insight) -> Optional[AdaptationRecord]:
    """Create time-based regime rules."""
    if insight.category != "problem" or insight.confidence < 0.7:
        return None

    # Extract hours from evidence or parse from description
    worst_hours = insight.evidence.get("worst_hours", [])
    if not worst_hours:
        return None

    # Create a NO_TRADE or REDUCE_SIZE rule for bad hours
    rule = RegimeRule(
        rule_id=f"time_filter_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        description=f"Reduce trading during hours {worst_hours} (from reflection)",
        condition={"hour_of_day": {"op": "in", "value": worst_hours}},
        action="REDUCE_SIZE",  # Be conservative - reduce, don't block
    )
    self.knowledge.add_rule(rule)

    return AdaptationRecord(
        action="create_rule",
        target=rule.rule_id,
        description=f"Created time filter: reduce size during hours {worst_hours}",
        ...
    )


def _apply_regime_insight(self, insight: Insight) -> Optional[AdaptationRecord]:
    """Create market regime rules."""
    if insight.category != "problem" or insight.confidence < 0.7:
        return None

    # Extract regime from evidence
    worst_regime = insight.evidence.get("worst_regime")
    if not worst_regime:
        return None

    # Map regime to condition
    condition = {}
    if worst_regime == "btc_down":
        condition = {"btc_trend": "down"}
    elif worst_regime == "btc_up":
        condition = {"btc_trend": "up"}
    elif "weekend" in worst_regime.lower():
        condition = {"is_weekend": True}

    if not condition:
        return None

    rule = RegimeRule(
        rule_id=f"regime_filter_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        description=f"Reduce trading during {worst_regime} (from reflection)",
        condition=condition,
        action="REDUCE_SIZE",
    )
    self.knowledge.add_rule(rule)

    return AdaptationRecord(
        action="create_rule",
        target=rule.rule_id,
        description=f"Created regime filter: reduce size during {worst_regime}",
        ...
    )
```

### Integration with ReflectionEngine

Update `ReflectionEngine.reflect()` to apply adaptations:

```python
async def reflect(self) -> ReflectionResult:
    # ... existing analysis code ...

    # Generate insights
    insights, summary = await self._generate_insights(...)

    # NEW: Apply adaptations
    adaptations = []
    if self.adaptation_engine:
        adaptations = self.adaptation_engine.apply_insights(insights)

    # Log reflection with adaptations
    self._log_reflection(result, adaptations)

    return result
```

### Confidence Thresholds

Adaptations are only applied when confidence meets threshold:

| Action | Min Confidence | Min Trades | Additional Conditions |
|--------|---------------|------------|----------------------|
| Blacklist coin | 0.85 | 5 | win_rate < 30%, pnl < 0 |
| Favor coin | 0.80 | 5 | win_rate >= 60%, pnl > 0 |
| Deactivate pattern | 0.85 | 5 | confidence < 0.3 |
| Create time rule | 0.75 | 10 | clear time correlation |
| Create regime rule | 0.75 | 10 | clear regime correlation |

### Safety Guards

```python
def _should_apply(self, insight: Insight) -> bool:
    """Conservative checks before applying adaptation."""

    # Must have minimum confidence
    if insight.confidence < 0.6:
        return False

    # Must have evidence
    if not insight.evidence:
        return False

    # Must have minimum trades for statistical significance
    trades = insight.evidence.get("trades", 0)
    if trades < 5:
        return False

    # Don't apply same adaptation twice in 24h
    if self._recently_applied(insight):
        return False

    return True


def _recently_applied(self, insight: Insight) -> bool:
    """Check if similar adaptation was applied recently."""
    # Check database for recent adaptations with same target
    recent = self.db.get_recent_adaptations(hours=24)
    target = insight.evidence.get("coin") or insight.evidence.get("pattern_id")

    for adaptation in recent:
        if adaptation["target"] == target:
            return True

    return False
```

---

## Technical Approach

### Step 1: Create Data Classes

Create `src/models/adaptation.py`:
- `AdaptationRecord` dataclass
- Action enum

### Step 2: Implement AdaptationEngine

Create `src/adaptation.py`:
- Insight-to-action mapping
- Safety guards
- Pre-metrics capture
- Logging

### Step 3: Add Database Support

Update `src/database.py`:
- `adaptations` table
- `log_adaptation()`
- `get_recent_adaptations()`

### Step 4: Add Knowledge Brain Methods

Update `src/knowledge.py` (if needed):
- `favor_coin()` method
- Ensure all action methods exist

### Step 5: Integrate with ReflectionEngine

Update `src/reflection.py`:
- Add `adaptation_engine` parameter
- Call `apply_insights()` after generating insights
- Include adaptations in result

### Step 6: Wire in main_v2.py

- Create AdaptationEngine
- Pass to ReflectionEngine

### Step 7: Create Tests

Test:
- Each insight type triggers correct action
- Confidence thresholds are respected
- Safety guards prevent duplicate adaptations
- Adaptations are logged correctly

---

## Files Created

| File | Purpose |
|------|---------|
| `src/models/adaptation.py` | AdaptationRecord dataclass |
| `src/adaptation.py` | AdaptationEngine class |
| `tests/test_adaptation.py` | Unit tests |

---

## Files Modified

| File | Change |
|------|--------|
| `src/reflection.py` | Add adaptation_engine, call apply_insights() |
| `src/knowledge.py` | Add favor_coin() if missing |
| `src/database.py` | Add adaptations table and methods |
| `src/main_v2.py` | Create and wire AdaptationEngine |

---

## Acceptance Criteria

- [x] AdaptationEngine converts insights to Knowledge Brain changes
- [x] Coin insights trigger blacklist/favor appropriately
- [x] Pattern insights can deactivate failing patterns
- [x] Time insights create time-based regime rules
- [x] Regime insights create market-based regime rules
- [x] Confidence thresholds prevent low-confidence adaptations
- [x] Safety guards prevent duplicate adaptations
- [x] All adaptations logged with pre-metrics
- [x] ReflectionEngine automatically applies adaptations
- [x] Unit tests pass (17 tests)

---

## Verification

### Unit Test

```bash
python -m pytest tests/test_adaptation.py -v
```

### Integration Test

```python
from src.adaptation import AdaptationEngine
from src.models.reflection import Insight

# Create engine
engine = AdaptationEngine(knowledge, coin_scorer, pattern_library, db)

# Test coin blacklist
insight = Insight(
    insight_type="coin",
    category="problem",
    title="DOGE underperforming",
    description="DOGE has 20% win rate over 10 trades",
    evidence={"coin": "DOGE", "win_rate": 0.20, "trades": 10, "pnl": -15.0},
    suggested_action="Blacklist DOGE",
    confidence=0.90,
)

adaptations = engine.apply_insights([insight])

assert len(adaptations) == 1
assert adaptations[0].action == "blacklist"
assert adaptations[0].target == "DOGE"

# Verify coin is actually blacklisted
assert knowledge.is_blacklisted("DOGE")
```

### Full Flow Test

```python
# Run reflection and verify adaptations applied
result = await reflection_engine.reflect()

print(f"Insights: {len(result.insights)}")
print(f"Adaptations applied: {len(result.adaptations)}")

for a in result.adaptations:
    print(f"  {a.action}: {a.description}")

# Check Knowledge Brain state changed
stats = knowledge.get_stats_summary()
print(f"Blacklisted coins: {stats['coins']['blacklisted']}")
print(f"Active rules: {stats['rules']['active']}")
```

---

## Example Adaptation Flow

### Input: Insights from Reflection

```python
insights = [
    Insight(
        insight_type="coin",
        category="problem",
        title="DOGE underperforming",
        evidence={"coin": "DOGE", "win_rate": 0.20, "trades": 10},
        confidence=0.90,
    ),
    Insight(
        insight_type="coin",
        category="opportunity",
        title="SOL strong performer",
        evidence={"coin": "SOL", "win_rate": 0.75, "trades": 12},
        confidence=0.85,
    ),
    Insight(
        insight_type="time",
        category="problem",
        title="Asia session losses",
        evidence={"worst_hours": [2, 3, 4, 5], "win_rate": 0.25},
        confidence=0.75,
    ),
]
```

### Output: Adaptations Applied

```
[blacklist] DOGE: Blacklisted due to 20% win rate over 10 trades
[favor] SOL: Marked as favored due to 75% win rate over 12 trades
[create_rule] time_filter_20260203_1430: Reduce size during hours [2, 3, 4, 5]
```

### Knowledge Brain State After

```
Coins:
  DOGE: BLACKLISTED
  SOL: FAVORED

Regime Rules:
  - time_filter_20260203_1430: REDUCE_SIZE when hour in [2,3,4,5]
```

---

## Process Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    REFLECTION ENGINE                                 │
│                                                                     │
│  analyze() → _generate_insights() → insights[]                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ADAPTATION ENGINE                                 │
│                                                                     │
│  For each insight:                                                  │
│    1. Check confidence threshold                                    │
│    2. Check safety guards (min trades, not recently applied)        │
│    3. Capture pre-metrics                                           │
│    4. Apply action to Knowledge Brain:                              │
│       - blacklist_coin() / favor_coin()                            │
│       - deactivate_pattern()                                        │
│       - add_rule()                                                  │
│    5. Log AdaptationRecord                                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE BRAIN                                   │
│                                                                     │
│  State Changed:                                                     │
│  - coin_scores updated                                              │
│  - patterns adjusted                                                │
│  - regime_rules added                                               │
│                                                                     │
│  Next Strategist cycle uses new knowledge!                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Completion Notes

**Completed February 3, 2026**

### Implementation Summary

1. **Created `src/models/adaptation.py`**:
   - `AdaptationAction` enum with all action types
   - `AdaptationRecord` dataclass with to_dict/from_dict methods

2. **Created `src/adaptation.py`**:
   - `AdaptationEngine` class with insight-to-action mapping
   - Handlers for coin, pattern, time, and regime insights
   - Confidence thresholds and safety guards
   - 24-hour cooldown to prevent duplicate adaptations

3. **Updated `src/knowledge.py`**:
   - Added `favor_coin()` method

4. **Updated `src/database.py`**:
   - Added `adaptations` table
   - Added `log_adaptation()` method
   - Added `get_adaptations()` and `get_adaptations_for_target()` methods

5. **Updated `src/reflection.py`**:
   - Added `adaptation_engine` parameter to constructor
   - Call `apply_insights()` after generating insights
   - Track `adaptations_applied` in stats

6. **Updated `src/models/reflection.py`**:
   - Added `adaptations` field to `ReflectionResult`

7. **Updated `src/main_v2.py`**:
   - Create and wire `AdaptationEngine`
   - Pass to `ReflectionEngine`

8. **Created `tests/test_adaptation.py`**:
   - 17 unit tests covering all adaptation scenarios
   - All tests passing

### Key Thresholds

| Action | Min Confidence | Min Trades | Additional |
|--------|---------------|------------|------------|
| Blacklist | 0.85 | 5 | win_rate < 30%, pnl < 0 |
| Favor | 0.80 | 5 | win_rate >= 60%, pnl > 0 |
| Deactivate | 0.85 | 5 | win_rate < 35% |
| Time rule | 0.75 | 10 | - |
| Regime rule | 0.75 | 10 | - |

### Learning Loop Complete

With TASK-133, the bot now has a complete autonomous learning loop:

```
Trade Execution → Quick Update → Knowledge Brain
         ↓                              ↑
  Reflection Engine → Insights → Adaptation Engine
```

The bot can now:
1. Execute trades and record outcomes
2. Analyze performance periodically via LLM
3. Generate actionable insights
4. Automatically apply adaptations to Knowledge Brain
5. Use updated knowledge in next trading cycle

---

## Related

- [TASK-131](./TASK-131.md) - Deep Reflection (generates insights)
- [TASK-120](./TASK-120.md) - Knowledge Brain (receives adaptations)
- [TASK-121](./TASK-121.md) - CoinScorer (blacklist/favor)
- [TASK-122](./TASK-122.md) - PatternLibrary (pattern confidence)
- [AUTONOMOUS-TRADER-SPEC.md](../AUTONOMOUS-TRADER-SPEC.md) - Section 6: Reflection Engine
