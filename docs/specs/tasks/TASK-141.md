# TASK-141: Profitability Tracking

**Status:** COMPLETE
**Created:** February 3, 2026
**Completed:** February 3, 2026
**Priority:** High
**Depends On:** TASK-140 (Full System Integration)
**Phase:** Phase 2.5 - Closed Loop

---

## Objective

Implement comprehensive profitability tracking to measure system performance over time. Track P&L, win rates, and key metrics across multiple dimensions (overall, by coin, by pattern, by time period) to validate the learning loop is improving performance.

---

## Background

The autonomous trading system now has:
- Trade execution with full journaling (TASK-102)
- Knowledge Brain tracking coin performance (TASK-121)
- Reflection Engine analyzing trades (TASK-131)
- Adaptation Engine making adjustments (TASK-133)

**Missing:** Holistic profitability tracking that answers:
- Is the system profitable overall?
- Are we becoming more profitable over time?
- Which strategies/patterns contribute most to P&L?
- What's our risk-adjusted return?

### Current State

Trade data exists in `trade_journal` table with:
- Entry/exit prices, PnL per trade
- Coin, position size, hold duration
- Pattern/strategy used

**Not yet tracked:**
- Running P&L totals
- Periodic snapshots (daily, weekly)
- Performance metrics (Sharpe, drawdown, etc.)
- Before/after comparison for adaptations

---

## Specification

### 1. ProfitabilityTracker Class

```python
# src/profitability.py

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum


class TimeFrame(Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    ALL_TIME = "all_time"


@dataclass
class ProfitSnapshot:
    """Point-in-time profitability snapshot."""
    timestamp: datetime
    timeframe: TimeFrame

    # Core metrics
    total_pnl: float
    realized_pnl: float
    unrealized_pnl: float

    # Trade counts
    total_trades: int
    winning_trades: int
    losing_trades: int

    # Rates
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float  # gross_profit / gross_loss

    # Risk metrics
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: Optional[float]

    # Balance
    starting_balance: float
    ending_balance: float
    return_pct: float


@dataclass
class DimensionPerformance:
    """Performance breakdown by dimension (coin, pattern, hour, etc.)."""
    dimension: str  # "coin", "pattern", "hour_of_day", "day_of_week"
    key: str  # "BTC", "momentum_breakout", "14", "Monday"

    total_pnl: float
    trade_count: int
    win_rate: float
    avg_pnl: float
    contribution_pct: float  # % of total P&L


class ProfitabilityTracker:
    """Tracks and analyzes trading profitability."""

    def __init__(self, db: Database, journal: TradeJournal):
        self.db = db
        self.journal = journal
        self._snapshots: List[ProfitSnapshot] = []
        self._last_snapshot_time: Dict[TimeFrame, datetime] = {}

    def get_current_snapshot(self, timeframe: TimeFrame = TimeFrame.ALL_TIME) -> ProfitSnapshot:
        """Get current profitability snapshot for timeframe."""

    def get_historical_snapshots(
        self,
        timeframe: TimeFrame,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> List[ProfitSnapshot]:
        """Get historical snapshots for trend analysis."""

    def get_performance_by_dimension(
        self,
        dimension: str,
        timeframe: TimeFrame = TimeFrame.ALL_TIME
    ) -> List[DimensionPerformance]:
        """Get performance breakdown by dimension."""

    def calculate_metrics(self, trades: List[Trade]) -> Dict[str, float]:
        """Calculate performance metrics from trade list."""

    def take_snapshot(self, timeframe: TimeFrame) -> ProfitSnapshot:
        """Record a point-in-time snapshot."""

    def get_equity_curve(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get equity curve data for charting."""
```

### 2. Key Metrics

| Metric | Formula | Purpose |
|--------|---------|---------|
| Win Rate | wins / total_trades | Basic success rate |
| Profit Factor | gross_profit / gross_loss | Risk/reward efficiency |
| Sharpe Ratio | (avg_return - risk_free) / std_return | Risk-adjusted return |
| Max Drawdown | max(peak - trough) | Worst decline |
| Avg Win/Loss Ratio | avg_win / avg_loss | Quality of wins vs losses |
| Expectancy | (win_rate * avg_win) - (loss_rate * avg_loss) | Expected value per trade |

### 3. Database Schema

```sql
-- Periodic snapshots for trend tracking
CREATE TABLE IF NOT EXISTS profit_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL,
    timeframe TEXT NOT NULL,

    -- Core metrics
    total_pnl REAL NOT NULL,
    realized_pnl REAL NOT NULL,
    unrealized_pnl REAL DEFAULT 0,

    -- Trade counts
    total_trades INTEGER NOT NULL,
    winning_trades INTEGER NOT NULL,
    losing_trades INTEGER NOT NULL,

    -- Rates
    win_rate REAL NOT NULL,
    avg_win REAL,
    avg_loss REAL,
    profit_factor REAL,

    -- Risk metrics
    max_drawdown REAL,
    max_drawdown_pct REAL,
    sharpe_ratio REAL,

    -- Balance
    starting_balance REAL,
    ending_balance REAL,
    return_pct REAL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_snapshots_timeframe ON profit_snapshots(timeframe, timestamp);

-- High-water mark tracking for drawdown calculation
CREATE TABLE IF NOT EXISTS equity_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL,
    balance REAL NOT NULL,
    trade_id INTEGER,
    is_high_water_mark BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (trade_id) REFERENCES trade_journal(id)
);

CREATE INDEX idx_equity_timestamp ON equity_points(timestamp);
```

### 4. Snapshot Schedule

| Timeframe | Frequency | Retention |
|-----------|-----------|-----------|
| Hour | Every hour | 7 days |
| Day | End of day (00:00 UTC) | 90 days |
| Week | End of week (Sunday) | 1 year |
| Month | End of month | Forever |

### 5. Performance Dimensions

Track performance breakdown by:

```python
DIMENSIONS = {
    "coin": "Which coins are most/least profitable?",
    "pattern": "Which trading patterns work best?",
    "hour_of_day": "What hours are most profitable?",
    "day_of_week": "What days are most profitable?",
    "position_size": "Does size affect performance?",
    "hold_duration": "Short vs long holds?",
}
```

### 6. Learning Loop Integration

The ProfitabilityTracker feeds back to the learning system:

```python
def get_improvement_metrics(self, lookback_days: int = 7) -> Dict[str, Any]:
    """Get metrics showing if system is improving."""
    current = self.get_current_snapshot(TimeFrame.WEEK)
    previous = self.get_snapshot_at(datetime.now() - timedelta(days=lookback_days))

    return {
        "win_rate_change": current.win_rate - previous.win_rate,
        "pnl_change": current.total_pnl - previous.total_pnl,
        "profit_factor_change": current.profit_factor - previous.profit_factor,
        "is_improving": current.total_pnl > previous.total_pnl,
    }
```

---

## Technical Approach

### Step 1: Create ProfitabilityTracker Class

- Create `src/profitability.py`
- Implement core metrics calculations
- Add snapshot creation logic

### Step 2: Add Database Schema

- Add `profit_snapshots` table
- Add `equity_points` table
- Add database methods for saving/loading snapshots

### Step 3: Implement Snapshot Scheduling

- Add periodic snapshot task to main loop
- Implement retention cleanup

### Step 4: Add Dimension Analysis

- Query trade journal for dimension breakdowns
- Calculate contribution percentages

### Step 5: Integrate with System

- Add ProfitabilityTracker to TradingSystem
- Expose metrics via operational commands
- Add to health check (degraded if metrics stale)

### Step 6: Create Tests

- Unit tests for metric calculations
- Integration tests for snapshot persistence

---

## Files to Create

| File | Purpose |
|------|---------|
| `src/profitability.py` | ProfitabilityTracker class |
| `tests/test_profitability.py` | Unit tests |

---

## Files to Modify

| File | Change |
|------|--------|
| `src/database.py` | Add snapshot tables and methods |
| `src/main_v2.py` | Integrate ProfitabilityTracker |

---

## Acceptance Criteria

- [x] ProfitabilityTracker calculates all key metrics correctly
- [x] Snapshots save to database at scheduled intervals
- [x] Historical snapshots queryable for trend analysis
- [x] Performance breakdown by coin, pattern, time available
- [x] Equity curve data available for charting
- [x] Integrated with TradingSystem
- [x] Improvement metrics show learning progress
- [x] All tests pass (24 tests)

---

## Verification

### Metric Calculation Test

```python
# Create tracker
tracker = ProfitabilityTracker(db, journal)

# Get current snapshot
snapshot = tracker.get_current_snapshot()
print(f"Win Rate: {snapshot.win_rate:.1%}")
print(f"Profit Factor: {snapshot.profit_factor:.2f}")
print(f"Sharpe Ratio: {snapshot.sharpe_ratio:.2f}")
print(f"Max Drawdown: {snapshot.max_drawdown_pct:.1%}")
```

### Dimension Analysis Test

```python
# Best performing coins
by_coin = tracker.get_performance_by_dimension("coin")
for perf in sorted(by_coin, key=lambda x: x.total_pnl, reverse=True)[:5]:
    print(f"{perf.key}: ${perf.total_pnl:.2f} ({perf.win_rate:.0%} win)")
```

### Improvement Tracking Test

```python
# Is the system improving?
improvement = tracker.get_improvement_metrics(lookback_days=7)
print(f"Win rate change: {improvement['win_rate_change']:+.1%}")
print(f"P&L change: ${improvement['pnl_change']:+.2f}")
print(f"Improving: {improvement['is_improving']}")
```

---

## Related

- [TASK-140](./TASK-140.md) - Full System Integration
- [TASK-142](./TASK-142.md) - Adaptation Effectiveness Monitoring
- [TASK-102](./TASK-102.md) - Trade Journal
- [TASK-121](./TASK-121.md) - Coin Scoring System

---

## Completion Notes

**Completed February 3, 2026**

### Implementation Summary

1. **ProfitabilityTracker Class** (`src/profitability.py`):
   - Calculates all key metrics: win rate, profit factor, Sharpe ratio, max drawdown, expectancy
   - Generates ProfitSnapshot objects with comprehensive performance data
   - Takes periodic snapshots (hourly, daily, weekly, monthly)
   - Tracks equity curve for charting

2. **Dimension Analysis**:
   - Performance breakdown by: coin, pattern, hour_of_day, day_of_week, exit_reason, position_size, hold_duration
   - Contribution percentage calculation for each dimension
   - Sorted by P&L for easy identification of best/worst performers

3. **Learning Loop Integration**:
   - `get_improvement_metrics()` compares current vs previous period
   - Tracks if system is improving over time
   - Used to validate the autonomous learning loop

4. **Database Schema** (`src/database.py`):
   - `profit_snapshots` table for periodic snapshots
   - `equity_points` table for high-water mark tracking
   - Methods: `save_profit_snapshot()`, `get_profit_snapshots()`, `delete_old_snapshots()`
   - Methods: `save_equity_point()`, `get_equity_curve()`, `get_high_water_marks()`

5. **TradingSystem Integration** (`src/main_v2.py`):
   - ProfitabilityTracker initialized on startup
   - SnapshotScheduler checks for due snapshots every 5 minutes
   - Added to health check components
   - New operational commands:
     - `get_profitability_snapshot(timeframe)`
     - `get_performance_by_dimension(dimension)`
     - `get_improvement_metrics(lookback_days)`
     - `get_equity_curve()`

6. **Tests** (`tests/test_profitability.py`):
   - 24 unit tests covering all functionality
   - TestMetricCalculations: win rate, expectancy, profit factor
   - TestDrawdownCalculation: max drawdown scenarios
   - TestSnapshotPersistence: save/load round-trip
   - TestDimensionAnalysis: by coin, hour, day
   - TestEquityCurve: balance progression
   - TestImprovementMetrics: learning validation
   - TestSnapshotScheduler: scheduling logic
   - TestHealthCheck: component health

### Key Metrics Tracked

| Metric | Formula | Purpose |
|--------|---------|---------|
| Win Rate | wins / total_trades | Basic success rate |
| Profit Factor | gross_profit / gross_loss | Risk/reward efficiency |
| Sharpe Ratio | (mean_return - rf) / std_return | Risk-adjusted return |
| Max Drawdown | max(peak - trough) | Worst decline |
| Avg Win/Loss Ratio | avg_win / avg_loss | Quality of wins vs losses |
| Expectancy | (win_rate * avg_win) - (loss_rate * avg_loss) | Expected value per trade |

### Files Created

| File | Purpose |
|------|---------|
| `src/profitability.py` | ProfitabilityTracker, SnapshotScheduler, TimeFrame |
| `tests/test_profitability.py` | 24 unit tests |

### Files Modified

| File | Changes |
|------|---------|
| `src/database.py` | Added profit_snapshots and equity_points tables |
| `src/main_v2.py` | Integrated ProfitabilityTracker, added operational commands |

