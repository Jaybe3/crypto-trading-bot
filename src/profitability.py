"""
Profitability Tracking - Comprehensive performance metrics for the trading system.

Tracks P&L, win rates, and key metrics across multiple dimensions
(overall, by coin, by pattern, by time period) to validate the learning
loop is improving performance.

TASK-141: Profitability Tracking
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from src.calculations import (
    calculate_win_rate,
    calculate_profit_factor,
    calculate_avg_win_loss_ratio,
    calculate_expectancy,
    calculate_return_on_balance,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    build_equity_curve,
)

if TYPE_CHECKING:
    from src.database import Database
    from src.journal import TradeJournal

logger = logging.getLogger(__name__)


class TimeFrame(Enum):
    """Time frames for snapshot aggregation."""
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
    total_pnl: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

    # Trade counts
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0

    # Rates
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0  # gross_profit / gross_loss

    # Risk metrics
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: Optional[float] = None

    # Balance
    starting_balance: float = 0.0
    ending_balance: float = 0.0
    return_pct: float = 0.0

    # Additional metrics
    expectancy: float = 0.0  # Expected value per trade
    avg_win_loss_ratio: float = 0.0  # avg_win / avg_loss

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "timeframe": self.timeframe.value,
            "total_pnl": self.total_pnl,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "profit_factor": self.profit_factor,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "starting_balance": self.starting_balance,
            "ending_balance": self.ending_balance,
            "return_pct": self.return_pct,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ProfitSnapshot":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(d["timestamp"]) if isinstance(d["timestamp"], str) else d["timestamp"],
            timeframe=TimeFrame(d["timeframe"]) if isinstance(d["timeframe"], str) else d["timeframe"],
            total_pnl=d.get("total_pnl", 0.0),
            realized_pnl=d.get("realized_pnl", 0.0),
            unrealized_pnl=d.get("unrealized_pnl", 0.0),
            total_trades=d.get("total_trades", 0),
            winning_trades=d.get("winning_trades", 0),
            losing_trades=d.get("losing_trades", 0),
            win_rate=d.get("win_rate", 0.0),
            avg_win=d.get("avg_win", 0.0),
            avg_loss=d.get("avg_loss", 0.0),
            profit_factor=d.get("profit_factor", 0.0),
            max_drawdown=d.get("max_drawdown", 0.0),
            max_drawdown_pct=d.get("max_drawdown_pct", 0.0),
            sharpe_ratio=d.get("sharpe_ratio"),
            starting_balance=d.get("starting_balance", 0.0),
            ending_balance=d.get("ending_balance", 0.0),
            return_pct=d.get("return_pct", 0.0),
        )


@dataclass
class DimensionPerformance:
    """Performance breakdown by dimension (coin, pattern, hour, etc.)."""
    dimension: str  # "coin", "pattern", "hour_of_day", "day_of_week"
    key: str  # "BTC", "momentum_breakout", "14", "Monday"

    total_pnl: float = 0.0
    trade_count: int = 0
    win_rate: float = 0.0
    avg_pnl: float = 0.0
    contribution_pct: float = 0.0  # % of total P&L

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dimension": self.dimension,
            "key": self.key,
            "total_pnl": self.total_pnl,
            "trade_count": self.trade_count,
            "win_rate": self.win_rate,
            "avg_pnl": self.avg_pnl,
            "contribution_pct": self.contribution_pct,
        }


class ProfitabilityTracker:
    """
    Tracks and analyzes trading profitability.

    Provides:
    - Current snapshot of performance metrics
    - Historical snapshots for trend analysis
    - Performance breakdown by dimensions (coin, pattern, time)
    - Equity curve data for charting
    - Improvement metrics for learning validation
    """

    # Snapshot retention policy (in days)
    RETENTION = {
        TimeFrame.HOUR: 7,
        TimeFrame.DAY: 90,
        TimeFrame.WEEK: 365,
        TimeFrame.MONTH: None,  # Forever
    }

    def __init__(
        self,
        db: "Database",
        journal: "TradeJournal",
        initial_balance: float = 10000.0,
    ):
        """
        Initialize the ProfitabilityTracker.

        Args:
            db: Database instance for persistence
            journal: TradeJournal for trade data
            initial_balance: Starting balance for return calculations
        """
        self.db = db
        self.journal = journal
        self.initial_balance = initial_balance

        # Cache for recent snapshots
        self._snapshot_cache: Dict[TimeFrame, ProfitSnapshot] = {}
        self._last_snapshot_time: Dict[TimeFrame, datetime] = {}

        # High-water mark for drawdown calculation
        self._high_water_mark = initial_balance
        self._current_balance = initial_balance

        logger.info(f"ProfitabilityTracker initialized (initial_balance=${initial_balance:,.2f})")

    # =========================================================================
    # Core Snapshot Methods
    # =========================================================================

    def get_current_snapshot(
        self,
        timeframe: TimeFrame = TimeFrame.ALL_TIME,
    ) -> ProfitSnapshot:
        """
        Get current profitability snapshot for timeframe.

        Args:
            timeframe: Time period to calculate metrics for

        Returns:
            ProfitSnapshot with current metrics
        """
        # Determine time range
        now = datetime.now()
        start_time = self._get_start_time(timeframe, now)

        # Get trades from journal
        if timeframe == TimeFrame.ALL_TIME:
            trades = self.journal.get_recent(hours=24 * 365, status="closed", limit=10000)
        else:
            hours = int((now - start_time).total_seconds() / 3600)
            trades = self.journal.get_recent(hours=max(hours, 1), status="closed", limit=10000)

        # Calculate metrics
        metrics = self.calculate_metrics(trades)

        # Build snapshot
        snapshot = ProfitSnapshot(
            timestamp=now,
            timeframe=timeframe,
            total_pnl=metrics["total_pnl"],
            realized_pnl=metrics["total_pnl"],
            unrealized_pnl=0.0,  # TODO: Calculate from open positions
            total_trades=metrics["total_trades"],
            winning_trades=metrics["winning_trades"],
            losing_trades=metrics["losing_trades"],
            win_rate=metrics["win_rate"],
            avg_win=metrics["avg_win"],
            avg_loss=metrics["avg_loss"],
            profit_factor=metrics["profit_factor"],
            max_drawdown=metrics["max_drawdown"],
            max_drawdown_pct=metrics["max_drawdown_pct"],
            sharpe_ratio=metrics["sharpe_ratio"],
            starting_balance=self.initial_balance,
            ending_balance=self.initial_balance + metrics["total_pnl"],
            return_pct=metrics["return_pct"],
            expectancy=metrics["expectancy"],
            avg_win_loss_ratio=metrics["avg_win_loss_ratio"],
        )

        # Cache it
        self._snapshot_cache[timeframe] = snapshot

        return snapshot

    def calculate_metrics(self, trades: List[Any]) -> Dict[str, float]:
        """
        Calculate performance metrics from trade list.

        Args:
            trades: List of JournalEntry objects

        Returns:
            Dictionary of calculated metrics
        """
        if not trades:
            return self._empty_metrics()

        # Basic counts
        total_trades = len(trades)
        winners = [t for t in trades if t.pnl_usd and t.pnl_usd > 0]
        losers = [t for t in trades if t.pnl_usd and t.pnl_usd < 0]

        winning_trades = len(winners)
        losing_trades = len(losers)

        # P&L calculations
        total_pnl = sum(t.pnl_usd or 0 for t in trades)
        gross_profit = sum(t.pnl_usd for t in winners)
        gross_loss = abs(sum(t.pnl_usd for t in losers))

        # Averages
        avg_win = gross_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = gross_loss / losing_trades if losing_trades > 0 else 0

        # Use canonical calculations from src.calculations
        win_rate = calculate_win_rate(winning_trades, total_trades)
        profit_factor = calculate_profit_factor(gross_profit, gross_loss)
        avg_win_loss_ratio = calculate_avg_win_loss_ratio(avg_win, avg_loss)
        expectancy = calculate_expectancy(win_rate, avg_win, avg_loss)

        # Drawdown calculation
        max_drawdown, max_drawdown_pct = self._calculate_drawdown(trades)

        # Sharpe ratio (simplified: assume risk-free rate = 0)
        sharpe_ratio = self._calculate_sharpe_ratio(trades)

        # Return percentage
        return_pct = calculate_return_on_balance(total_pnl, self.initial_balance)

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "total_pnl": total_pnl,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "win_rate": win_rate,
            "profit_factor": profit_factor if profit_factor != float('inf') else 999.99,
            "avg_win_loss_ratio": avg_win_loss_ratio if avg_win_loss_ratio != float('inf') else 999.99,
            "expectancy": expectancy,
            "max_drawdown": max_drawdown,
            "max_drawdown_pct": max_drawdown_pct,
            "sharpe_ratio": sharpe_ratio,
            "return_pct": return_pct,
        }

    def _empty_metrics(self) -> Dict[str, float]:
        """Return empty metrics dictionary."""
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "avg_win_loss_ratio": 0.0,
            "expectancy": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_ratio": None,
            "return_pct": 0.0,
        }

    def _calculate_drawdown(self, trades: List[Any]) -> tuple[float, float]:
        """
        Calculate maximum drawdown from trade sequence.

        Returns:
            Tuple of (max_drawdown_usd, max_drawdown_pct)
        """
        if not trades:
            return 0.0, 0.0

        # Sort trades by exit time
        sorted_trades = sorted(
            [t for t in trades if t.exit_time],
            key=lambda t: t.exit_time
        )

        if not sorted_trades:
            return 0.0, 0.0

        # Extract P&L values and use canonical functions
        pnl_values = [t.pnl_usd for t in sorted_trades if t.pnl_usd is not None]
        equity_curve = build_equity_curve(pnl_values, self.initial_balance)
        return calculate_max_drawdown(equity_curve)

    def _calculate_sharpe_ratio(
        self,
        trades: List[Any],
        risk_free_rate: float = 0.0,
        periods_per_year: int = 252,
    ) -> Optional[float]:
        """
        Calculate Sharpe ratio from trade returns.

        Args:
            trades: List of trades
            risk_free_rate: Annual risk-free rate (default 0)
            periods_per_year: Trading periods per year (252 for daily)

        Returns:
            Sharpe ratio or None if insufficient data
        """
        if len(trades) < 2:
            return None

        # Get trade returns as decimal fractions (not percentages)
        returns = [
            (t.pnl_usd / t.position_size_usd)
            for t in trades
            if t.pnl_usd is not None and t.position_size_usd and t.position_size_usd > 0
        ]

        if len(returns) < 2:
            return None

        # Use canonical Sharpe ratio calculation
        sharpe = calculate_sharpe_ratio(
            returns,
            risk_free_rate=risk_free_rate,
            annualize=True,
            periods_per_year=periods_per_year
        )

        return round(sharpe, 2) if sharpe != 0.0 else None

    def _trading_days_in_sample(self, trades: List[Any]) -> int:
        """Estimate trading days in sample."""
        if not trades:
            return 1

        sorted_trades = sorted(
            [t for t in trades if t.exit_time],
            key=lambda t: t.exit_time
        )

        if len(sorted_trades) < 2:
            return 1

        first = sorted_trades[0].exit_time
        last = sorted_trades[-1].exit_time

        return max(1, (last - first).days)

    def _get_start_time(self, timeframe: TimeFrame, now: datetime) -> datetime:
        """Get start time for a timeframe."""
        if timeframe == TimeFrame.HOUR:
            return now - timedelta(hours=1)
        elif timeframe == TimeFrame.DAY:
            return now - timedelta(days=1)
        elif timeframe == TimeFrame.WEEK:
            return now - timedelta(weeks=1)
        elif timeframe == TimeFrame.MONTH:
            return now - timedelta(days=30)
        else:  # ALL_TIME
            return datetime(2020, 1, 1)

    # =========================================================================
    # Snapshot Persistence
    # =========================================================================

    def take_snapshot(self, timeframe: TimeFrame) -> ProfitSnapshot:
        """
        Record a point-in-time snapshot to database.

        Args:
            timeframe: Timeframe for this snapshot

        Returns:
            The recorded snapshot
        """
        snapshot = self.get_current_snapshot(timeframe)

        # Save to database
        self.db.save_profit_snapshot(snapshot.to_dict())

        # Update last snapshot time
        self._last_snapshot_time[timeframe] = snapshot.timestamp

        logger.info(
            f"Snapshot taken ({timeframe.value}): "
            f"P&L=${snapshot.total_pnl:+,.2f}, "
            f"Win Rate={snapshot.win_rate:.1f}%, "
            f"Trades={snapshot.total_trades}"
        )

        return snapshot

    def get_historical_snapshots(
        self,
        timeframe: TimeFrame,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[ProfitSnapshot]:
        """
        Get historical snapshots for trend analysis.

        Args:
            timeframe: Timeframe to query
            start: Start of range (optional)
            end: End of range (optional)
            limit: Maximum snapshots to return

        Returns:
            List of ProfitSnapshot objects
        """
        rows = self.db.get_profit_snapshots(
            timeframe=timeframe.value,
            start=start,
            end=end,
            limit=limit,
        )

        return [ProfitSnapshot.from_dict(row) for row in rows]

    def cleanup_old_snapshots(self) -> int:
        """
        Remove snapshots older than retention policy.

        Returns:
            Number of snapshots deleted
        """
        total_deleted = 0

        for timeframe, retention_days in self.RETENTION.items():
            if retention_days is None:
                continue

            cutoff = datetime.now() - timedelta(days=retention_days)
            deleted = self.db.delete_old_snapshots(timeframe.value, cutoff)
            total_deleted += deleted

        if total_deleted > 0:
            logger.info(f"Cleaned up {total_deleted} old snapshots")

        return total_deleted

    # =========================================================================
    # Dimension Analysis
    # =========================================================================

    def get_performance_by_dimension(
        self,
        dimension: str,
        timeframe: TimeFrame = TimeFrame.ALL_TIME,
    ) -> List[DimensionPerformance]:
        """
        Get performance breakdown by dimension.

        Args:
            dimension: "coin", "pattern", "hour_of_day", "day_of_week",
                      "position_size", "hold_duration"
            timeframe: Time period to analyze

        Returns:
            List of DimensionPerformance objects sorted by P&L
        """
        # Get trades for timeframe
        now = datetime.now()
        start_time = self._get_start_time(timeframe, now)

        if timeframe == TimeFrame.ALL_TIME:
            hours = 24 * 365
        else:
            hours = int((now - start_time).total_seconds() / 3600)

        trades = self.journal.get_recent(hours=max(hours, 1), status="closed", limit=10000)

        if not trades:
            return []

        # Calculate total P&L for contribution %
        total_pnl = sum(t.pnl_usd or 0 for t in trades)

        # Group by dimension
        groups: Dict[str, List[Any]] = {}

        for trade in trades:
            key = self._get_dimension_key(trade, dimension)
            if key is not None:
                if key not in groups:
                    groups[key] = []
                groups[key].append(trade)

        # Calculate performance for each group
        results = []
        for key, group_trades in groups.items():
            pnl = sum(t.pnl_usd or 0 for t in group_trades)
            wins = sum(1 for t in group_trades if t.pnl_usd and t.pnl_usd > 0)
            count = len(group_trades)

            results.append(DimensionPerformance(
                dimension=dimension,
                key=str(key),
                total_pnl=pnl,
                trade_count=count,
                win_rate=(wins / count * 100) if count > 0 else 0,
                avg_pnl=(pnl / count) if count > 0 else 0,
                contribution_pct=(pnl / total_pnl * 100) if total_pnl != 0 else 0,
            ))

        # Sort by P&L descending
        results.sort(key=lambda x: x.total_pnl, reverse=True)

        return results

    def _get_dimension_key(self, trade: Any, dimension: str) -> Optional[str]:
        """Extract dimension key from trade."""
        if dimension == "coin":
            return trade.coin
        elif dimension == "pattern":
            return trade.pattern_id or "none"
        elif dimension == "strategy":
            return trade.strategy_id or "none"
        elif dimension == "hour_of_day":
            return str(trade.hour_of_day)
        elif dimension == "day_of_week":
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            return days[trade.day_of_week] if 0 <= trade.day_of_week < 7 else str(trade.day_of_week)
        elif dimension == "exit_reason":
            return trade.exit_reason or "unknown"
        elif dimension == "position_size":
            # Bucket into size categories
            size = trade.position_size_usd or 0
            if size < 50:
                return "<$50"
            elif size < 100:
                return "$50-100"
            elif size < 200:
                return "$100-200"
            else:
                return ">$200"
        elif dimension == "hold_duration":
            # Bucket into duration categories
            duration = trade.duration_seconds or 0
            if duration < 60:
                return "<1min"
            elif duration < 300:
                return "1-5min"
            elif duration < 900:
                return "5-15min"
            elif duration < 3600:
                return "15-60min"
            else:
                return ">1hr"
        else:
            return None

    # =========================================================================
    # Equity Curve
    # =========================================================================

    def get_equity_curve(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get equity curve data for charting.

        Args:
            start: Start of range (optional)
            end: End of range (optional)

        Returns:
            List of {timestamp, balance, trade_id, pnl} dicts
        """
        # Get closed trades in time range
        if start is None:
            hours = 24 * 365
        else:
            hours = int((datetime.now() - start).total_seconds() / 3600)

        trades = self.journal.get_recent(hours=max(hours, 1), status="closed", limit=10000)

        # Sort by exit time
        sorted_trades = sorted(
            [t for t in trades if t.exit_time],
            key=lambda t: t.exit_time
        )

        # Filter by end time if specified
        if end:
            sorted_trades = [t for t in sorted_trades if t.exit_time <= end]

        # Build equity curve
        curve = [{
            "timestamp": self._get_start_time(TimeFrame.ALL_TIME, datetime.now()).isoformat(),
            "balance": self.initial_balance,
            "trade_id": None,
            "pnl": 0,
        }]

        balance = self.initial_balance
        for trade in sorted_trades:
            if trade.pnl_usd is not None:
                balance += trade.pnl_usd
                curve.append({
                    "timestamp": trade.exit_time.isoformat() if trade.exit_time else None,
                    "balance": balance,
                    "trade_id": trade.id,
                    "pnl": trade.pnl_usd,
                })

        return curve

    def record_equity_point(self, balance: float, trade_id: Optional[str] = None) -> None:
        """
        Record an equity point after a trade.

        Args:
            balance: Current balance
            trade_id: Associated trade ID
        """
        is_hwm = balance > self._high_water_mark

        if is_hwm:
            self._high_water_mark = balance

        self._current_balance = balance

        # Save to database
        self.db.save_equity_point({
            "timestamp": datetime.now().isoformat(),
            "balance": balance,
            "trade_id": trade_id,
            "is_high_water_mark": is_hwm,
        })

    # =========================================================================
    # Learning Loop Integration
    # =========================================================================

    def get_improvement_metrics(self, lookback_days: int = 7) -> Dict[str, Any]:
        """
        Get metrics showing if system is improving.

        Args:
            lookback_days: Days to compare against

        Returns:
            Dict with improvement metrics
        """
        now = datetime.now()
        cutoff = now - timedelta(days=lookback_days)

        # Get current period metrics
        current_trades = self.journal.get_recent(hours=lookback_days * 24, status="closed", limit=10000)
        current_metrics = self.calculate_metrics(current_trades)

        # Get previous period metrics
        prev_start = cutoff - timedelta(days=lookback_days)
        prev_hours = lookback_days * 24
        all_trades = self.journal.get_recent(hours=lookback_days * 24 * 2, status="closed", limit=10000)

        # Filter to previous period
        prev_trades = [
            t for t in all_trades
            if t.exit_time and prev_start <= t.exit_time < cutoff
        ]
        prev_metrics = self.calculate_metrics(prev_trades)

        # Calculate changes
        win_rate_change = current_metrics["win_rate"] - prev_metrics["win_rate"]
        pnl_change = current_metrics["total_pnl"] - prev_metrics["total_pnl"]
        profit_factor_change = current_metrics["profit_factor"] - prev_metrics["profit_factor"]
        expectancy_change = current_metrics["expectancy"] - prev_metrics["expectancy"]

        # Determine if improving
        is_improving = (
            current_metrics["total_pnl"] > prev_metrics["total_pnl"] and
            current_metrics["win_rate"] >= prev_metrics["win_rate"] - 5  # Allow 5% variance
        )

        return {
            "lookback_days": lookback_days,
            "current_period": {
                "trades": current_metrics["total_trades"],
                "pnl": current_metrics["total_pnl"],
                "win_rate": current_metrics["win_rate"],
                "profit_factor": current_metrics["profit_factor"],
                "expectancy": current_metrics["expectancy"],
            },
            "previous_period": {
                "trades": prev_metrics["total_trades"],
                "pnl": prev_metrics["total_pnl"],
                "win_rate": prev_metrics["win_rate"],
                "profit_factor": prev_metrics["profit_factor"],
                "expectancy": prev_metrics["expectancy"],
            },
            "changes": {
                "win_rate_change": win_rate_change,
                "pnl_change": pnl_change,
                "profit_factor_change": profit_factor_change,
                "expectancy_change": expectancy_change,
            },
            "is_improving": is_improving,
        }

    # =========================================================================
    # Health Check
    # =========================================================================

    def get_health(self) -> Dict[str, Any]:
        """Get component health status."""
        status = "healthy"
        metrics = {}

        # Check if we have recent snapshots
        try:
            latest = self.db.get_profit_snapshots(limit=1)
            if latest:
                last_snapshot = datetime.fromisoformat(latest[0]["timestamp"])
                hours_since = (datetime.now() - last_snapshot).total_seconds() / 3600
                metrics["hours_since_snapshot"] = hours_since
                if hours_since > 2:  # More than 2 hours without snapshot
                    status = "degraded"
            else:
                metrics["hours_since_snapshot"] = None
        except Exception as e:
            status = "degraded"
            metrics["error"] = str(e)

        metrics["has_journal"] = self.journal is not None
        metrics["initial_balance"] = self.initial_balance

        return {
            "status": status,
            "last_activity": None,
            "error_count": 0,
            "metrics": metrics,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics."""
        return {
            "initial_balance": self.initial_balance,
            "high_water_mark": self._high_water_mark,
            "current_balance": self._current_balance,
            "cached_snapshots": len(self._snapshot_cache),
        }


# =============================================================================
# Snapshot Scheduler
# =============================================================================

class SnapshotScheduler:
    """
    Schedules periodic snapshot creation.

    Manages hourly, daily, weekly, and monthly snapshots according to schedule.
    """

    def __init__(self, tracker: ProfitabilityTracker):
        self.tracker = tracker
        self._last_snapshots: Dict[TimeFrame, datetime] = {}

    def check_and_take_snapshots(self) -> List[TimeFrame]:
        """
        Check if any snapshots are due and take them.

        Returns:
            List of timeframes that were snapshotted
        """
        now = datetime.now()
        taken = []

        # Hourly: every hour
        if self._should_take(TimeFrame.HOUR, now, hours=1):
            self.tracker.take_snapshot(TimeFrame.HOUR)
            self._last_snapshots[TimeFrame.HOUR] = now
            taken.append(TimeFrame.HOUR)

        # Daily: at midnight UTC
        if self._should_take(TimeFrame.DAY, now, hours=24):
            self.tracker.take_snapshot(TimeFrame.DAY)
            self._last_snapshots[TimeFrame.DAY] = now
            taken.append(TimeFrame.DAY)

        # Weekly: Sunday midnight
        if now.weekday() == 6 and self._should_take(TimeFrame.WEEK, now, hours=24 * 7):
            self.tracker.take_snapshot(TimeFrame.WEEK)
            self._last_snapshots[TimeFrame.WEEK] = now
            taken.append(TimeFrame.WEEK)

        # Monthly: last day of month
        tomorrow = now + timedelta(days=1)
        if tomorrow.month != now.month and self._should_take(TimeFrame.MONTH, now, hours=24 * 28):
            self.tracker.take_snapshot(TimeFrame.MONTH)
            self._last_snapshots[TimeFrame.MONTH] = now
            taken.append(TimeFrame.MONTH)

        return taken

    def _should_take(self, timeframe: TimeFrame, now: datetime, hours: int) -> bool:
        """Check if a snapshot should be taken."""
        last = self._last_snapshots.get(timeframe)
        if last is None:
            return True
        return (now - last).total_seconds() >= hours * 3600
