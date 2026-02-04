# TASK-142: Adaptation Effectiveness Monitoring

**Status:** COMPLETE
**Created:** February 3, 2026
**Completed:** February 3, 2026
**Priority:** High
**Depends On:** TASK-133 (Adaptation Application), TASK-141 (Profitability Tracking)
**Phase:** Phase 2.5 - Closed Loop

---

## Objective

Track whether adaptations actually improve performance. Record pre-metrics when an adaptation is made, measure post-metrics after sufficient trades or time, and flag adaptations that hurt performance for potential rollback.

---

## Background

The AdaptationEngine (TASK-133) now applies insights from the ReflectionEngine:
- Blacklists underperforming coins
- Favors high-performing coins
- Creates time/regime filter rules
- Deactivates failing patterns

**The problem:** We don't know if these adaptations actually help. Did blacklisting DOGE improve win rate? Did the time filter rule save money? Without measurement, we're flying blind.

### Current State

The `adaptations` table already has fields for effectiveness tracking:
```sql
pre_metrics TEXT,          -- Captured when adaptation applied ✅
post_metrics TEXT,         -- NOT YET POPULATED
effectiveness TEXT,        -- NOT YET POPULATED
effectiveness_measured_at TIMESTAMP  -- NOT YET POPULATED
```

**Missing:**
- Mechanism to measure post-metrics after N trades or X hours
- Comparison logic to determine if adaptation helped
- Flagging of harmful adaptations
- Rollback suggestions or automatic rollback

---

## Specification

### 1. EffectivenessMonitor Class

```python
# src/effectiveness.py

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

class EffectivenessRating(Enum):
    """Rating for adaptation effectiveness."""
    HIGHLY_EFFECTIVE = "highly_effective"  # Significantly improved metrics
    EFFECTIVE = "effective"                 # Moderately improved metrics
    NEUTRAL = "neutral"                     # No significant change
    INEFFECTIVE = "ineffective"             # Made things worse
    HARMFUL = "harmful"                     # Significantly worse, consider rollback
    PENDING = "pending"                     # Not enough data yet


@dataclass
class EffectivenessResult:
    """Result of effectiveness measurement."""
    adaptation_id: str
    rating: EffectivenessRating

    # Pre/post comparison
    pre_metrics: Dict[str, Any]
    post_metrics: Dict[str, Any]

    # Key changes
    win_rate_change: float        # Percentage points (+5 means 50% -> 55%)
    pnl_change: float             # Dollar change
    profit_factor_change: float   # Change in profit factor

    # Context
    trades_measured: int          # Trades since adaptation
    hours_elapsed: float          # Hours since adaptation

    # Recommendation
    should_rollback: bool
    rollback_reason: Optional[str] = None

    measured_at: datetime = None


class EffectivenessMonitor:
    """Monitors adaptation effectiveness and flags harmful changes.

    Flow:
    1. AdaptationEngine applies adaptation, records pre_metrics
    2. EffectivenessMonitor runs periodically
    3. For each unmeasured adaptation older than MIN_HOURS:
       - Calculate post_metrics
       - Compare to pre_metrics
       - Assign effectiveness rating
       - Flag for rollback if harmful
    """

    # Measurement thresholds
    MIN_TRADES_FOR_MEASUREMENT = 10     # At least 10 trades after adaptation
    MIN_HOURS_FOR_MEASUREMENT = 24      # At least 24 hours after adaptation
    MAX_HOURS_FOR_MEASUREMENT = 168     # Measure within 7 days

    # Effectiveness thresholds (percentage points)
    HIGHLY_EFFECTIVE_THRESHOLD = 10.0   # +10% win rate
    EFFECTIVE_THRESHOLD = 3.0           # +3% win rate
    INEFFECTIVE_THRESHOLD = -3.0        # -3% win rate
    HARMFUL_THRESHOLD = -10.0           # -10% win rate

    def __init__(
        self,
        db: Database,
        journal: TradeJournal,
        profitability_tracker: ProfitabilityTracker,
        adaptation_engine: AdaptationEngine,
    ):
        self.db = db
        self.journal = journal
        self.profitability = profitability_tracker
        self.adaptation_engine = adaptation_engine

        self._last_check = None
        self._measurements_completed = 0
        self._rollbacks_flagged = 0

    def check_pending_adaptations(self) -> List[EffectivenessResult]:
        """Check all unmeasured adaptations that are ready for measurement.

        Returns:
            List of effectiveness results for newly measured adaptations.
        """

    def measure_adaptation(self, adaptation_id: str) -> Optional[EffectivenessResult]:
        """Measure effectiveness of a specific adaptation.

        Args:
            adaptation_id: ID of adaptation to measure.

        Returns:
            EffectivenessResult or None if not ready.
        """

    def get_pending_measurements(self) -> List[Dict[str, Any]]:
        """Get adaptations pending measurement."""

    def get_harmful_adaptations(self, hours: int = 168) -> List[Dict[str, Any]]:
        """Get adaptations flagged as harmful in time period."""

    def suggest_rollback(self, adaptation_id: str) -> Dict[str, Any]:
        """Get rollback suggestion for an adaptation."""

    def execute_rollback(self, adaptation_id: str) -> bool:
        """Execute rollback of a harmful adaptation.

        - Unblacklist coins
        - Reactivate patterns
        - Deactivate rules
        """
```

### 2. Measurement Logic

For each adaptation type, measure relevant metrics:

| Adaptation Type | Pre-Metrics | Post-Metrics | Comparison |
|-----------------|-------------|--------------|------------|
| Blacklist Coin | Overall win rate, P&L | Overall win rate, P&L (excluding blacklisted coin) | Did removing this coin help? |
| Favor Coin | Coin's win rate, P&L | Coin's win rate, P&L | Is favored coin still performing? |
| Time Rule | Win rate during filtered hours | Win rate outside filtered hours | Did avoiding bad hours help? |
| Regime Rule | Win rate in filtered regime | Win rate in other regimes | Did regime filter help? |
| Deactivate Pattern | Pattern's win rate | Overall win rate | Did removing pattern help? |

### 3. Pre-Metrics Capture (Enhanced)

When adaptation is applied, capture comprehensive metrics:

```python
def capture_pre_metrics(self, adaptation_type: str, target: str) -> Dict[str, Any]:
    """Capture pre-adaptation metrics for comparison."""

    # Get current snapshot
    snapshot = self.profitability.get_current_snapshot()

    metrics = {
        "timestamp": datetime.now().isoformat(),
        "overall": {
            "total_trades": snapshot.total_trades,
            "win_rate": snapshot.win_rate,
            "total_pnl": snapshot.total_pnl,
            "profit_factor": snapshot.profit_factor,
            "sharpe_ratio": snapshot.sharpe_ratio,
        }
    }

    # Add target-specific metrics
    if adaptation_type == "blacklist_coin":
        coin_perf = self.profitability.get_performance_by_dimension("coin")
        coin_data = next((c for c in coin_perf if c.key == target), None)
        if coin_data:
            metrics["target"] = {
                "coin": target,
                "trades": coin_data.trade_count,
                "win_rate": coin_data.win_rate,
                "pnl": coin_data.total_pnl,
            }

    elif adaptation_type == "create_time_rule":
        # Capture performance during filtered hours
        hour_perf = self.profitability.get_performance_by_dimension("hour_of_day")
        # ... filter to affected hours

    return metrics
```

### 4. Post-Metrics Capture

```python
def capture_post_metrics(
    self,
    adaptation_id: str,
    adaptation_type: str,
    target: str,
    pre_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    """Capture post-adaptation metrics for comparison.

    Only includes trades AFTER the adaptation was applied.
    """
    adaptation_time = datetime.fromisoformat(pre_metrics["timestamp"])
    hours_since = (datetime.now() - adaptation_time).total_seconds() / 3600

    # Get trades since adaptation
    trades_since = self.journal.get_recent(
        hours=int(hours_since),
        status="closed",
    )

    # Filter to only trades after adaptation
    trades_after = [
        t for t in trades_since
        if t.exit_time and t.exit_time > adaptation_time
    ]

    # Calculate metrics from these trades
    metrics = self.profitability.calculate_metrics(trades_after)

    return {
        "timestamp": datetime.now().isoformat(),
        "hours_since_adaptation": hours_since,
        "trades_measured": len(trades_after),
        "overall": {
            "total_trades": metrics["total_trades"],
            "win_rate": metrics["win_rate"],
            "total_pnl": metrics["total_pnl"],
            "profit_factor": metrics["profit_factor"],
        }
    }
```

### 5. Effectiveness Rating

```python
def calculate_effectiveness(
    self,
    pre_metrics: Dict[str, Any],
    post_metrics: Dict[str, Any],
) -> EffectivenessResult:
    """Compare pre/post metrics and assign rating."""

    # Calculate changes
    win_rate_change = (
        post_metrics["overall"]["win_rate"] -
        pre_metrics["overall"]["win_rate"]
    )

    pnl_change = (
        post_metrics["overall"]["total_pnl"] -
        pre_metrics["overall"]["total_pnl"]
    )

    # Assign rating
    if win_rate_change >= self.HIGHLY_EFFECTIVE_THRESHOLD:
        rating = EffectivenessRating.HIGHLY_EFFECTIVE
    elif win_rate_change >= self.EFFECTIVE_THRESHOLD:
        rating = EffectivenessRating.EFFECTIVE
    elif win_rate_change >= self.INEFFECTIVE_THRESHOLD:
        rating = EffectivenessRating.NEUTRAL
    elif win_rate_change >= self.HARMFUL_THRESHOLD:
        rating = EffectivenessRating.INEFFECTIVE
    else:
        rating = EffectivenessRating.HARMFUL

    # Determine if rollback needed
    should_rollback = (
        rating == EffectivenessRating.HARMFUL and
        pnl_change < -20.0 and  # Lost more than $20
        post_metrics["trades_measured"] >= 10  # Statistically significant
    )

    rollback_reason = None
    if should_rollback:
        rollback_reason = (
            f"Win rate dropped {abs(win_rate_change):.1f}% and "
            f"lost ${abs(pnl_change):.2f} since adaptation"
        )

    return EffectivenessResult(...)
```

### 6. Rollback Actions

| Adaptation | Rollback Action |
|------------|-----------------|
| Blacklist Coin | Unblacklist coin (remove from blacklist) |
| Favor Coin | Remove "improving" trend marker |
| Time Rule | Deactivate the rule |
| Regime Rule | Deactivate the rule |
| Deactivate Pattern | Reactivate the pattern |

### 7. Database Methods

```python
# In src/database.py

def update_adaptation_effectiveness(
    self,
    adaptation_id: str,
    post_metrics: str,
    effectiveness: str,
    effectiveness_measured_at: datetime,
) -> None:
    """Update adaptation with effectiveness measurement."""

def get_unmeasured_adaptations(self, min_hours: int = 24) -> List[Dict]:
    """Get adaptations that haven't been measured yet."""

def get_adaptations_by_effectiveness(
    self,
    effectiveness: str,
    hours: int = 168,
) -> List[Dict]:
    """Get adaptations by effectiveness rating."""

def get_adaptation_effectiveness_summary(self) -> Dict[str, Any]:
    """Get summary of adaptation effectiveness."""
```

### 8. Integration with TradingSystem

```python
# In src/main.py

# Add to __init__
self.effectiveness_monitor: Optional[EffectivenessMonitor] = None

# Add to start_components()
self.effectiveness_monitor = EffectivenessMonitor(
    db=self.db,
    journal=self.journal,
    profitability_tracker=self.profitability_tracker,
    adaptation_engine=self.adaptation_engine,
)

# Add to main loop (check every hour)
if now - last_effectiveness_check >= 3600:  # 1 hour
    if self.effectiveness_monitor:
        results = self.effectiveness_monitor.check_pending_adaptations()
        for r in results:
            if r.should_rollback:
                logger.warning(f"Adaptation {r.adaptation_id} flagged for rollback: {r.rollback_reason}")
    last_effectiveness_check = now

# Add operational command
def get_adaptation_effectiveness(self) -> dict:
    """Get effectiveness summary for all adaptations."""
```

---

## Technical Approach

### Step 1: Enhance Pre-Metrics Capture
- Update AdaptationEngine to capture comprehensive pre-metrics
- Include overall stats AND target-specific stats

### Step 2: Create EffectivenessMonitor Class
- Create `src/effectiveness.py`
- Implement measurement logic
- Implement rating calculation

### Step 3: Add Database Methods
- Add methods to update effectiveness
- Add methods to query by effectiveness

### Step 4: Implement Rollback
- Add rollback methods for each adaptation type
- Log rollback actions

### Step 5: Integrate with TradingSystem
- Initialize EffectivenessMonitor
- Add periodic check to main loop
- Add operational commands

### Step 6: Create Tests
- Test measurement timing logic
- Test effectiveness calculation
- Test rollback execution

---

## Files to Create

| File | Purpose |
|------|---------|
| `src/effectiveness.py` | EffectivenessMonitor class |
| `tests/test_effectiveness.py` | Unit tests |

---

## Files to Modify

| File | Change |
|------|--------|
| `src/database.py` | Add effectiveness query methods |
| `src/adaptation.py` | Enhance pre-metrics capture |
| `src/main.py` | Integrate EffectivenessMonitor |
| `src/knowledge.py` | Add unblacklist method for rollback |

---

## Acceptance Criteria

- [x] Pre-metrics captured comprehensively when adaptation applied
- [x] Post-metrics captured after MIN_TRADES or MIN_HOURS
- [x] Effectiveness rating assigned (highly_effective → harmful)
- [x] Harmful adaptations flagged for rollback
- [x] Rollback actions implemented for each adaptation type
- [x] Effectiveness summary available via operational command
- [x] Periodic checking integrated into main loop
- [x] All tests pass (16 tests)

---

## Verification

### Effectiveness Measurement Test

```python
# Apply an adaptation
insight = Insight(
    insight_type="coin",
    category="problem",
    title="DOGE underperforming",
    description="DOGE has 20% win rate",
    evidence={"coin": "DOGE", "win_rate": 0.20, "trades": 10, "pnl": -15.0},
    suggested_action="Blacklist DOGE",
    confidence=0.90,
)
adaptation_engine.apply_insights([insight])

# ... wait for trades ...

# Check effectiveness
results = effectiveness_monitor.check_pending_adaptations()
for r in results:
    print(f"Adaptation: {r.adaptation_id}")
    print(f"  Rating: {r.rating.value}")
    print(f"  Win rate change: {r.win_rate_change:+.1f}%")
    print(f"  P&L change: ${r.pnl_change:+.2f}")
    print(f"  Should rollback: {r.should_rollback}")
```

### Rollback Test

```python
# Get harmful adaptations
harmful = effectiveness_monitor.get_harmful_adaptations()
for h in harmful:
    print(f"Harmful: {h['target']} - {h['effectiveness']}")

    # Execute rollback
    success = effectiveness_monitor.execute_rollback(h['adaptation_id'])
    print(f"  Rollback: {'SUCCESS' if success else 'FAILED'}")
```

### Effectiveness Summary

```python
summary = effectiveness_monitor.get_effectiveness_summary()
print(f"Total measured: {summary['total_measured']}")
print(f"Highly effective: {summary['highly_effective']}")
print(f"Effective: {summary['effective']}")
print(f"Neutral: {summary['neutral']}")
print(f"Ineffective: {summary['ineffective']}")
print(f"Harmful: {summary['harmful']}")
print(f"Pending: {summary['pending']}")
print(f"Rollbacks executed: {summary['rollbacks_executed']}")
```

---

## Related

- [TASK-133](./TASK-133.md) - Adaptation Application
- [TASK-141](./TASK-141.md) - Profitability Tracking
- [TASK-131](./TASK-131.md) - Deep Reflection
- [AUTONOMOUS-TRADER-SPEC.md](../AUTONOMOUS-TRADER-SPEC.md) - Full system architecture

---

## Completion Notes

**Completed February 3, 2026**

### Implementation Summary

1. **EffectivenessMonitor Class** (`src/effectiveness.py`):
   - Tracks pending adaptations and measures effectiveness after MIN_TRADES (10) or MIN_HOURS (24)
   - Calculates effectiveness rating based on win rate change
   - Flags harmful adaptations for rollback (win rate drop > 10%, P&L loss > $20)
   - Provides rollback execution for all adaptation types

2. **Effectiveness Ratings:**
   | Rating | Win Rate Change | Description |
   |--------|-----------------|-------------|
   | `highly_effective` | ≥ +10% | Significantly improved |
   | `effective` | ≥ +3% | Moderately improved |
   | `neutral` | -3% to +3% | No significant change |
   | `ineffective` | -3% to -10% | Made things worse |
   | `harmful` | < -10% | Significantly worse |

3. **Rollback Actions:**
   - Blacklist coin → Unblacklist
   - Favor coin → Remove improving trend
   - Time/Regime rule → Deactivate rule
   - Deactivate pattern → Reactivate pattern

4. **Database Methods** (`src/database.py`):
   - `update_adaptation_effectiveness()` - Save measurement results
   - `get_adaptations_by_effectiveness()` - Query by rating
   - `get_unmeasured_adaptations()` - Find pending measurements

5. **Knowledge Brain Updates** (`src/knowledge.py`):
   - `reactivate_pattern()` - For rollback of pattern deactivations

6. **TradingSystem Integration** (`src/main.py`):
   - EffectivenessMonitor initialized with other components
   - Periodic check every hour in main loop
   - Warnings logged for harmful adaptations
   - Operational commands:
     - `get_adaptation_effectiveness()` - Summary by rating
     - `get_harmful_adaptations()` - List harmful ones
     - `rollback_adaptation(id)` - Execute rollback

### Test Results

- **16** effectiveness tests passing
- **24** profitability tests passing
- **15** integration tests passing
- **Total: 55 tests passing**

### Files Created

| File | Purpose |
|------|---------|
| `src/effectiveness.py` | EffectivenessMonitor class |
| `tests/test_effectiveness.py` | 16 unit tests |

### Files Modified

| File | Changes |
|------|---------|
| `src/database.py` | Added effectiveness query methods |
| `src/knowledge.py` | Added `reactivate_pattern()` for rollback |
| `src/main.py` | Integrated EffectivenessMonitor, added operational commands |
