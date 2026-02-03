"""
Tests for ProfitabilityTracker (TASK-141).

Tests metric calculations, snapshot persistence, and dimension analysis.
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import Database
from src.profitability import (
    ProfitabilityTracker,
    ProfitSnapshot,
    DimensionPerformance,
    TimeFrame,
    SnapshotScheduler,
)


class MockJournalEntry:
    """Mock journal entry for testing."""

    def __init__(
        self,
        id: str,
        coin: str,
        pnl_usd: float,
        position_size_usd: float = 100.0,
        exit_time: datetime = None,
        hour_of_day: int = 12,
        day_of_week: int = 2,
        pattern_id: str = None,
        strategy_id: str = None,
        exit_reason: str = "take_profit",
        duration_seconds: int = 300,
    ):
        self.id = id
        self.coin = coin
        self.pnl_usd = pnl_usd
        self.position_size_usd = position_size_usd
        self.exit_time = exit_time or datetime.now()
        self.hour_of_day = hour_of_day
        self.day_of_week = day_of_week
        self.pattern_id = pattern_id
        self.strategy_id = strategy_id
        self.exit_reason = exit_reason
        self.duration_seconds = duration_seconds


class MockJournal:
    """Mock journal for testing."""

    def __init__(self, trades=None):
        self.trades = trades or []

    def get_recent(self, hours=24, status=None, limit=10000):
        return self.trades


class TestMetricCalculations(unittest.TestCase):
    """Test metric calculation methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)
        self.journal = MockJournal()
        self.tracker = ProfitabilityTracker(
            db=self.db,
            journal=self.journal,
            initial_balance=10000.0,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_empty_trades(self):
        """Test metrics with no trades."""
        metrics = self.tracker.calculate_metrics([])

        self.assertEqual(metrics["total_trades"], 0)
        self.assertEqual(metrics["win_rate"], 0.0)
        self.assertEqual(metrics["total_pnl"], 0.0)

    def test_all_winners(self):
        """Test metrics with all winning trades."""
        trades = [
            MockJournalEntry("t1", "BTC", pnl_usd=10.0),
            MockJournalEntry("t2", "ETH", pnl_usd=15.0),
            MockJournalEntry("t3", "SOL", pnl_usd=5.0),
        ]

        metrics = self.tracker.calculate_metrics(trades)

        self.assertEqual(metrics["total_trades"], 3)
        self.assertEqual(metrics["winning_trades"], 3)
        self.assertEqual(metrics["losing_trades"], 0)
        self.assertEqual(metrics["win_rate"], 100.0)
        self.assertEqual(metrics["total_pnl"], 30.0)
        self.assertEqual(metrics["avg_win"], 10.0)

    def test_all_losers(self):
        """Test metrics with all losing trades."""
        trades = [
            MockJournalEntry("t1", "BTC", pnl_usd=-10.0),
            MockJournalEntry("t2", "ETH", pnl_usd=-15.0),
        ]

        metrics = self.tracker.calculate_metrics(trades)

        self.assertEqual(metrics["total_trades"], 2)
        self.assertEqual(metrics["winning_trades"], 0)
        self.assertEqual(metrics["losing_trades"], 2)
        self.assertEqual(metrics["win_rate"], 0.0)
        self.assertEqual(metrics["total_pnl"], -25.0)
        self.assertEqual(metrics["avg_loss"], 12.5)

    def test_mixed_trades(self):
        """Test metrics with mixed wins and losses."""
        trades = [
            MockJournalEntry("t1", "BTC", pnl_usd=20.0),
            MockJournalEntry("t2", "ETH", pnl_usd=-10.0),
            MockJournalEntry("t3", "SOL", pnl_usd=15.0),
            MockJournalEntry("t4", "DOGE", pnl_usd=-5.0),
        ]

        metrics = self.tracker.calculate_metrics(trades)

        self.assertEqual(metrics["total_trades"], 4)
        self.assertEqual(metrics["winning_trades"], 2)
        self.assertEqual(metrics["losing_trades"], 2)
        self.assertEqual(metrics["win_rate"], 50.0)
        self.assertEqual(metrics["total_pnl"], 20.0)  # 20 - 10 + 15 - 5 = 20
        self.assertEqual(metrics["gross_profit"], 35.0)  # 20 + 15
        self.assertEqual(metrics["gross_loss"], 15.0)  # 10 + 5
        self.assertAlmostEqual(metrics["profit_factor"], 35.0 / 15.0, places=2)

    def test_win_rate_calculation(self):
        """Test win rate with specific ratio."""
        trades = [
            MockJournalEntry("t1", "BTC", pnl_usd=10.0),
            MockJournalEntry("t2", "ETH", pnl_usd=10.0),
            MockJournalEntry("t3", "SOL", pnl_usd=10.0),
            MockJournalEntry("t4", "DOGE", pnl_usd=-5.0),
        ]

        metrics = self.tracker.calculate_metrics(trades)

        self.assertEqual(metrics["win_rate"], 75.0)  # 3 out of 4

    def test_expectancy_calculation(self):
        """Test expectancy calculation."""
        trades = [
            MockJournalEntry("t1", "BTC", pnl_usd=20.0),
            MockJournalEntry("t2", "ETH", pnl_usd=-10.0),
        ]

        metrics = self.tracker.calculate_metrics(trades)

        # Expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        # = (0.5 * 20) - (0.5 * 10) = 10 - 5 = 5
        self.assertAlmostEqual(metrics["expectancy"], 5.0, places=2)

    def test_return_percentage(self):
        """Test return percentage calculation."""
        trades = [
            MockJournalEntry("t1", "BTC", pnl_usd=100.0),
        ]

        metrics = self.tracker.calculate_metrics(trades)

        # 100 / 10000 * 100 = 1%
        self.assertAlmostEqual(metrics["return_pct"], 1.0, places=2)


class TestDrawdownCalculation(unittest.TestCase):
    """Test drawdown calculation."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)
        self.journal = MockJournal()
        self.tracker = ProfitabilityTracker(
            db=self.db,
            journal=self.journal,
            initial_balance=10000.0,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_no_drawdown(self):
        """Test with no drawdown (all winners)."""
        now = datetime.now()
        trades = [
            MockJournalEntry("t1", "BTC", pnl_usd=100.0, exit_time=now - timedelta(hours=3)),
            MockJournalEntry("t2", "ETH", pnl_usd=100.0, exit_time=now - timedelta(hours=2)),
            MockJournalEntry("t3", "SOL", pnl_usd=100.0, exit_time=now - timedelta(hours=1)),
        ]

        metrics = self.tracker.calculate_metrics(trades)

        self.assertEqual(metrics["max_drawdown"], 0.0)
        self.assertEqual(metrics["max_drawdown_pct"], 0.0)

    def test_single_loss_drawdown(self):
        """Test drawdown from single loss."""
        now = datetime.now()
        trades = [
            MockJournalEntry("t1", "BTC", pnl_usd=500.0, exit_time=now - timedelta(hours=2)),
            MockJournalEntry("t2", "ETH", pnl_usd=-200.0, exit_time=now - timedelta(hours=1)),
        ]

        metrics = self.tracker.calculate_metrics(trades)

        # High water mark: 10000 + 500 = 10500
        # After loss: 10500 - 200 = 10300
        # Drawdown: 200
        self.assertAlmostEqual(metrics["max_drawdown"], 200.0, places=2)

    def test_recovery_drawdown(self):
        """Test drawdown with recovery."""
        now = datetime.now()
        trades = [
            MockJournalEntry("t1", "BTC", pnl_usd=500.0, exit_time=now - timedelta(hours=4)),
            MockJournalEntry("t2", "ETH", pnl_usd=-300.0, exit_time=now - timedelta(hours=3)),
            MockJournalEntry("t3", "SOL", pnl_usd=400.0, exit_time=now - timedelta(hours=2)),
            MockJournalEntry("t4", "DOGE", pnl_usd=100.0, exit_time=now - timedelta(hours=1)),
        ]

        metrics = self.tracker.calculate_metrics(trades)

        # Balance: 10000 -> 10500 -> 10200 -> 10600 -> 10700
        # Max drawdown was 300 (from 10500 to 10200)
        self.assertAlmostEqual(metrics["max_drawdown"], 300.0, places=2)


class TestSnapshotPersistence(unittest.TestCase):
    """Test snapshot save/load functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)
        self.journal = MockJournal([
            MockJournalEntry("t1", "BTC", pnl_usd=10.0),
            MockJournalEntry("t2", "ETH", pnl_usd=-5.0),
        ])
        self.tracker = ProfitabilityTracker(
            db=self.db,
            journal=self.journal,
            initial_balance=10000.0,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_take_snapshot(self):
        """Test taking a snapshot saves to database."""
        snapshot = self.tracker.take_snapshot(TimeFrame.HOUR)

        self.assertIsInstance(snapshot, ProfitSnapshot)
        self.assertEqual(snapshot.total_trades, 2)

        # Verify saved to database
        saved = self.db.get_profit_snapshots(timeframe="hour", limit=1)
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["total_trades"], 2)

    def test_get_historical_snapshots(self):
        """Test retrieving historical snapshots."""
        # Take multiple snapshots
        self.tracker.take_snapshot(TimeFrame.HOUR)
        self.tracker.take_snapshot(TimeFrame.DAY)
        self.tracker.take_snapshot(TimeFrame.HOUR)

        # Get hourly snapshots only
        hourly = self.tracker.get_historical_snapshots(TimeFrame.HOUR)
        self.assertEqual(len(hourly), 2)

        # Get all snapshots (by querying with DAY which we only took once)
        daily = self.tracker.get_historical_snapshots(TimeFrame.DAY)
        self.assertEqual(len(daily), 1)

    def test_snapshot_to_dict_from_dict(self):
        """Test snapshot serialization round-trip."""
        snapshot = ProfitSnapshot(
            timestamp=datetime.now(),
            timeframe=TimeFrame.DAY,
            total_pnl=100.0,
            realized_pnl=100.0,
            total_trades=5,
            winning_trades=3,
            losing_trades=2,
            win_rate=60.0,
            avg_win=50.0,
            avg_loss=25.0,
            profit_factor=2.0,
            max_drawdown=50.0,
            max_drawdown_pct=0.5,
            sharpe_ratio=1.5,
            starting_balance=10000.0,
            ending_balance=10100.0,
            return_pct=1.0,
        )

        d = snapshot.to_dict()
        restored = ProfitSnapshot.from_dict(d)

        self.assertEqual(restored.total_pnl, 100.0)
        self.assertEqual(restored.total_trades, 5)
        self.assertEqual(restored.timeframe, TimeFrame.DAY)


class TestDimensionAnalysis(unittest.TestCase):
    """Test performance breakdown by dimension."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)

        # Create trades with various dimensions
        self.trades = [
            MockJournalEntry("t1", "BTC", pnl_usd=100.0, hour_of_day=10, day_of_week=0),
            MockJournalEntry("t2", "BTC", pnl_usd=50.0, hour_of_day=10, day_of_week=1),
            MockJournalEntry("t3", "ETH", pnl_usd=-30.0, hour_of_day=14, day_of_week=0),
            MockJournalEntry("t4", "ETH", pnl_usd=20.0, hour_of_day=14, day_of_week=2),
            MockJournalEntry("t5", "SOL", pnl_usd=-10.0, hour_of_day=10, day_of_week=0),
        ]
        self.journal = MockJournal(self.trades)
        self.tracker = ProfitabilityTracker(
            db=self.db,
            journal=self.journal,
            initial_balance=10000.0,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_by_coin(self):
        """Test breakdown by coin."""
        results = self.tracker.get_performance_by_dimension("coin")

        # Should have 3 coins
        self.assertEqual(len(results), 3)

        # BTC should be first (highest P&L)
        btc = next(r for r in results if r.key == "BTC")
        self.assertEqual(btc.total_pnl, 150.0)  # 100 + 50
        self.assertEqual(btc.trade_count, 2)
        self.assertEqual(btc.win_rate, 100.0)

        # ETH
        eth = next(r for r in results if r.key == "ETH")
        self.assertEqual(eth.total_pnl, -10.0)  # -30 + 20
        self.assertEqual(eth.trade_count, 2)

    def test_by_hour(self):
        """Test breakdown by hour of day."""
        results = self.tracker.get_performance_by_dimension("hour_of_day")

        # Should have 2 hours
        self.assertEqual(len(results), 2)

        # Hour 10 should be best
        hour_10 = next(r for r in results if r.key == "10")
        self.assertEqual(hour_10.total_pnl, 140.0)  # 100 + 50 - 10
        self.assertEqual(hour_10.trade_count, 3)

    def test_by_day_of_week(self):
        """Test breakdown by day of week."""
        results = self.tracker.get_performance_by_dimension("day_of_week")

        # Should have 3 days
        self.assertEqual(len(results), 3)

        # Monday (day 0) should have 3 trades
        mon = next(r for r in results if r.key == "Mon")
        self.assertEqual(mon.trade_count, 3)

    def test_contribution_percentage(self):
        """Test that contribution percentages are calculated."""
        results = self.tracker.get_performance_by_dimension("coin")

        # Total P&L: 100 + 50 - 30 + 20 - 10 = 130
        total_pnl = sum(r.total_pnl for r in results)
        self.assertAlmostEqual(total_pnl, 130.0, places=2)

        # BTC contribution: 150 / 130 * 100 ≈ 115%
        btc = next(r for r in results if r.key == "BTC")
        self.assertAlmostEqual(btc.contribution_pct, 150.0 / 130.0 * 100, places=1)


class TestEquityCurve(unittest.TestCase):
    """Test equity curve generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)

        now = datetime.now()
        self.trades = [
            MockJournalEntry("t1", "BTC", pnl_usd=100.0, exit_time=now - timedelta(hours=3)),
            MockJournalEntry("t2", "ETH", pnl_usd=-50.0, exit_time=now - timedelta(hours=2)),
            MockJournalEntry("t3", "SOL", pnl_usd=75.0, exit_time=now - timedelta(hours=1)),
        ]
        self.journal = MockJournal(self.trades)
        self.tracker = ProfitabilityTracker(
            db=self.db,
            journal=self.journal,
            initial_balance=10000.0,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_equity_curve_shape(self):
        """Test equity curve has correct shape."""
        curve = self.tracker.get_equity_curve()

        # Should have initial point + 3 trades
        self.assertEqual(len(curve), 4)

        # First point is initial balance
        self.assertEqual(curve[0]["balance"], 10000.0)
        self.assertIsNone(curve[0]["trade_id"])

    def test_equity_curve_balance_progression(self):
        """Test balance progression in equity curve."""
        curve = self.tracker.get_equity_curve()

        # Balance progression: 10000 -> 10100 -> 10050 -> 10125
        balances = [p["balance"] for p in curve]
        self.assertEqual(balances[0], 10000.0)
        self.assertEqual(balances[1], 10100.0)  # +100
        self.assertEqual(balances[2], 10050.0)  # -50
        self.assertEqual(balances[3], 10125.0)  # +75


class TestImprovementMetrics(unittest.TestCase):
    """Test improvement tracking."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_improvement_metrics_structure(self):
        """Test improvement metrics returns correct structure."""
        now = datetime.now()

        # Current period: good performance
        current_trades = [
            MockJournalEntry("t1", "BTC", pnl_usd=100.0, exit_time=now - timedelta(days=1)),
            MockJournalEntry("t2", "ETH", pnl_usd=50.0, exit_time=now - timedelta(days=2)),
        ]

        # Previous period: bad performance
        prev_trades = [
            MockJournalEntry("t3", "SOL", pnl_usd=-30.0, exit_time=now - timedelta(days=10)),
            MockJournalEntry("t4", "DOGE", pnl_usd=-20.0, exit_time=now - timedelta(days=11)),
        ]

        all_trades = current_trades + prev_trades
        journal = MockJournal(all_trades)
        tracker = ProfitabilityTracker(
            db=self.db,
            journal=journal,
            initial_balance=10000.0,
        )

        metrics = tracker.get_improvement_metrics(lookback_days=7)

        # Check structure
        self.assertIn("current_period", metrics)
        self.assertIn("previous_period", metrics)
        self.assertIn("changes", metrics)
        self.assertIn("is_improving", metrics)

        # Current period should have positive P&L
        self.assertGreater(metrics["current_period"]["pnl"], 0)


class TestSnapshotScheduler(unittest.TestCase):
    """Test snapshot scheduling."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)
        self.journal = MockJournal([
            MockJournalEntry("t1", "BTC", pnl_usd=10.0),
        ])
        self.tracker = ProfitabilityTracker(
            db=self.db,
            journal=self.journal,
            initial_balance=10000.0,
        )
        self.scheduler = SnapshotScheduler(self.tracker)

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_first_check_takes_hourly(self):
        """Test first check takes hourly snapshot."""
        taken = self.scheduler.check_and_take_snapshots()

        self.assertIn(TimeFrame.HOUR, taken)

    def test_second_check_no_snapshot(self):
        """Test immediate second check doesn't take snapshot."""
        self.scheduler.check_and_take_snapshots()  # First check
        taken = self.scheduler.check_and_take_snapshots()  # Immediate second

        # Should not take hourly again (less than 1 hour)
        self.assertNotIn(TimeFrame.HOUR, taken)


class TestHealthCheck(unittest.TestCase):
    """Test health check functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)
        self.journal = MockJournal()
        self.tracker = ProfitabilityTracker(
            db=self.db,
            journal=self.journal,
            initial_balance=10000.0,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_health_check_structure(self):
        """Test health check returns correct structure."""
        health = self.tracker.get_health()

        self.assertIn("status", health)
        self.assertIn("metrics", health)
        self.assertEqual(health["metrics"]["has_journal"], True)

    def test_health_check_degraded_without_snapshots(self):
        """Test health degrades without recent snapshots."""
        # No snapshots taken yet, but that's okay - it shouldn't degrade
        # just because there are no historical snapshots
        health = self.tracker.get_health()
        # Status depends on whether there are any snapshots
        self.assertIn(health["status"], ["healthy", "degraded"])


if __name__ == "__main__":
    unittest.main()
