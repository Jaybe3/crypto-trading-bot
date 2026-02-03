"""
Tests for EffectivenessMonitor (TASK-142).

Tests effectiveness measurement, rating calculation, and rollback functionality.
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
from src.knowledge import KnowledgeBrain
from src.effectiveness import (
    EffectivenessMonitor,
    EffectivenessRating,
    EffectivenessResult,
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
    ):
        self.id = id
        self.coin = coin
        self.pnl_usd = pnl_usd
        self.position_size_usd = position_size_usd
        self.exit_time = exit_time or datetime.now()


class MockJournal:
    """Mock journal for testing."""

    def __init__(self, trades=None):
        self.trades = trades or []

    def get_recent(self, hours=24, status=None, limit=10000):
        return self.trades


class MockProfitability:
    """Mock profitability tracker for testing."""

    def __init__(self, metrics=None):
        self._metrics = metrics or {}

    def calculate_metrics(self, trades):
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "profit_factor": 0.0,
            }

        wins = sum(1 for t in trades if t.pnl_usd > 0)
        total = len(trades)
        pnl = sum(t.pnl_usd for t in trades)

        return {
            "total_trades": total,
            "winning_trades": wins,
            "win_rate": (wins / total * 100) if total > 0 else 0,
            "total_pnl": pnl,
            "profit_factor": 1.5 if pnl > 0 else 0.5,
        }


class TestEffectivenessRating(unittest.TestCase):
    """Test effectiveness rating calculation."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)
        self.knowledge = KnowledgeBrain(self.db)
        self.journal = MockJournal()
        self.profitability = MockProfitability()

        self.monitor = EffectivenessMonitor(
            db=self.db,
            journal=self.journal,
            profitability=self.profitability,
            adaptation_engine=MagicMock(),
            knowledge=self.knowledge,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_highly_effective_rating(self):
        """Test highly effective rating when win rate improves significantly."""
        pre_metrics = {"overall": {"win_rate": 40.0, "total_pnl": 0.0, "profit_factor": 1.0}}
        post_metrics = {"overall": {"win_rate": 55.0, "total_pnl": 100.0, "profit_factor": 2.0}}

        result = self.monitor._calculate_effectiveness(
            adaptation_id="test1",
            pre_metrics=pre_metrics,
            post_metrics=post_metrics,
            hours_elapsed=48,
            trades_measured=15,
        )

        self.assertEqual(result.rating, EffectivenessRating.HIGHLY_EFFECTIVE)
        self.assertEqual(result.win_rate_change, 15.0)
        self.assertFalse(result.should_rollback)

    def test_effective_rating(self):
        """Test effective rating for moderate improvement."""
        pre_metrics = {"overall": {"win_rate": 50.0, "total_pnl": 0.0, "profit_factor": 1.0}}
        post_metrics = {"overall": {"win_rate": 55.0, "total_pnl": 50.0, "profit_factor": 1.5}}

        result = self.monitor._calculate_effectiveness(
            adaptation_id="test2",
            pre_metrics=pre_metrics,
            post_metrics=post_metrics,
            hours_elapsed=48,
            trades_measured=15,
        )

        self.assertEqual(result.rating, EffectivenessRating.EFFECTIVE)
        self.assertEqual(result.win_rate_change, 5.0)

    def test_neutral_rating(self):
        """Test neutral rating when no significant change."""
        pre_metrics = {"overall": {"win_rate": 50.0, "total_pnl": 0.0, "profit_factor": 1.0}}
        post_metrics = {"overall": {"win_rate": 51.0, "total_pnl": 10.0, "profit_factor": 1.1}}

        result = self.monitor._calculate_effectiveness(
            adaptation_id="test3",
            pre_metrics=pre_metrics,
            post_metrics=post_metrics,
            hours_elapsed=48,
            trades_measured=15,
        )

        self.assertEqual(result.rating, EffectivenessRating.NEUTRAL)

    def test_ineffective_rating(self):
        """Test ineffective rating for moderate decline."""
        pre_metrics = {"overall": {"win_rate": 50.0, "total_pnl": 0.0, "profit_factor": 1.0}}
        post_metrics = {"overall": {"win_rate": 44.0, "total_pnl": -15.0, "profit_factor": 0.8}}

        result = self.monitor._calculate_effectiveness(
            adaptation_id="test4",
            pre_metrics=pre_metrics,
            post_metrics=post_metrics,
            hours_elapsed=48,
            trades_measured=15,
        )

        self.assertEqual(result.rating, EffectivenessRating.INEFFECTIVE)

    def test_harmful_rating(self):
        """Test harmful rating for significant decline."""
        pre_metrics = {"overall": {"win_rate": 50.0, "total_pnl": 0.0, "profit_factor": 1.0}}
        post_metrics = {"overall": {"win_rate": 35.0, "total_pnl": -50.0, "profit_factor": 0.5}}

        result = self.monitor._calculate_effectiveness(
            adaptation_id="test5",
            pre_metrics=pre_metrics,
            post_metrics=post_metrics,
            hours_elapsed=48,
            trades_measured=15,
        )

        self.assertEqual(result.rating, EffectivenessRating.HARMFUL)
        self.assertEqual(result.win_rate_change, -15.0)

    def test_harmful_triggers_rollback(self):
        """Test that harmful rating with significant loss triggers rollback."""
        pre_metrics = {"overall": {"win_rate": 50.0, "total_pnl": 0.0, "profit_factor": 1.0}}
        post_metrics = {"overall": {"win_rate": 35.0, "total_pnl": -50.0, "profit_factor": 0.5}}

        result = self.monitor._calculate_effectiveness(
            adaptation_id="test6",
            pre_metrics=pre_metrics,
            post_metrics=post_metrics,
            hours_elapsed=48,
            trades_measured=15,  # Enough trades
        )

        self.assertTrue(result.should_rollback)
        self.assertIsNotNone(result.rollback_reason)
        self.assertIn("15.0%", result.rollback_reason)

    def test_harmful_no_rollback_insufficient_trades(self):
        """Test that harmful rating doesn't trigger rollback with few trades."""
        pre_metrics = {"overall": {"win_rate": 50.0, "total_pnl": 0.0, "profit_factor": 1.0}}
        post_metrics = {"overall": {"win_rate": 35.0, "total_pnl": -50.0, "profit_factor": 0.5}}

        result = self.monitor._calculate_effectiveness(
            adaptation_id="test7",
            pre_metrics=pre_metrics,
            post_metrics=post_metrics,
            hours_elapsed=48,
            trades_measured=5,  # Not enough trades
        )

        self.assertEqual(result.rating, EffectivenessRating.HARMFUL)
        self.assertFalse(result.should_rollback)


class TestPostMetricsCapture(unittest.TestCase):
    """Test post-metrics capture."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)
        self.knowledge = KnowledgeBrain(self.db)

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_capture_post_metrics_filters_by_time(self):
        """Test that post-metrics only include trades after adaptation."""
        adaptation_time = datetime.now() - timedelta(hours=48)

        # Trades before adaptation (should be excluded)
        old_trades = [
            MockJournalEntry("t1", "BTC", pnl_usd=10.0, exit_time=adaptation_time - timedelta(hours=1)),
            MockJournalEntry("t2", "ETH", pnl_usd=-5.0, exit_time=adaptation_time - timedelta(hours=2)),
        ]

        # Trades after adaptation (should be included)
        new_trades = [
            MockJournalEntry("t3", "SOL", pnl_usd=20.0, exit_time=adaptation_time + timedelta(hours=1)),
            MockJournalEntry("t4", "DOGE", pnl_usd=15.0, exit_time=adaptation_time + timedelta(hours=2)),
        ]

        journal = MockJournal(old_trades + new_trades)
        profitability = MockProfitability()

        monitor = EffectivenessMonitor(
            db=self.db,
            journal=journal,
            profitability=profitability,
            adaptation_engine=MagicMock(),
            knowledge=self.knowledge,
        )

        post_metrics = monitor._capture_post_metrics(adaptation_time)

        # Should only count the 2 new trades
        self.assertEqual(post_metrics["trades_measured"], 2)


class TestRollbackFunctionality(unittest.TestCase):
    """Test rollback functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)
        self.knowledge = KnowledgeBrain(self.db)
        self.journal = MockJournal()
        self.profitability = MockProfitability()

        self.monitor = EffectivenessMonitor(
            db=self.db,
            journal=self.journal,
            profitability=self.profitability,
            adaptation_engine=MagicMock(),
            knowledge=self.knowledge,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_rollback_blacklist(self):
        """Test rollback of coin blacklist."""
        # Blacklist a coin
        self.knowledge.blacklist_coin("DOGE", "Testing")
        self.assertTrue(self.knowledge.is_blacklisted("DOGE"))

        # Log an adaptation
        self.db.log_adaptation(
            adaptation_id="test_blacklist",
            insight_type="coin",
            action="blacklist",
            target="DOGE",
            description="Blacklisted DOGE",
        )

        # Execute rollback
        success = self.monitor.execute_rollback("test_blacklist")

        self.assertTrue(success)
        self.assertFalse(self.knowledge.is_blacklisted("DOGE"))

    def test_rollback_time_rule(self):
        """Test rollback of time rule."""
        from src.models.knowledge import RegimeRule

        # Create a time rule
        rule = RegimeRule(
            rule_id="time_filter_test",
            description="Test time filter",
            condition={"hour_of_day": {"op": "in", "value": [2, 3, 4]}},
            action="REDUCE_SIZE",
        )
        self.knowledge.add_rule(rule)

        # Verify rule is active
        active_rules = self.knowledge.get_active_rules()
        self.assertTrue(any(r.rule_id == "time_filter_test" for r in active_rules))

        # Log an adaptation
        self.db.log_adaptation(
            adaptation_id="test_time_rule",
            insight_type="time",
            action="create_time_rule",
            target="time_filter_test",
            description="Created time filter",
        )

        # Execute rollback
        success = self.monitor.execute_rollback("test_time_rule")

        self.assertTrue(success)

        # Verify rule is deactivated
        active_rules = self.knowledge.get_active_rules()
        self.assertFalse(any(r.rule_id == "time_filter_test" for r in active_rules))

    def test_suggest_rollback(self):
        """Test rollback suggestion."""
        # Log an adaptation
        self.db.log_adaptation(
            adaptation_id="test_suggest",
            insight_type="coin",
            action="blacklist",
            target="XRP",
            description="Blacklisted XRP",
        )

        suggestion = self.monitor.suggest_rollback("test_suggest")

        self.assertEqual(suggestion["adaptation_id"], "test_suggest")
        self.assertEqual(suggestion["target"], "XRP")
        self.assertTrue(suggestion["can_rollback"])
        self.assertIn("Unblacklist", suggestion["rollback_action"])


class TestEffectivenessSummary(unittest.TestCase):
    """Test effectiveness summary."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)
        self.knowledge = KnowledgeBrain(self.db)
        self.journal = MockJournal()
        self.profitability = MockProfitability()

        self.monitor = EffectivenessMonitor(
            db=self.db,
            journal=self.journal,
            profitability=self.profitability,
            adaptation_engine=MagicMock(),
            knowledge=self.knowledge,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_empty_summary(self):
        """Test summary with no adaptations."""
        summary = self.monitor.get_effectiveness_summary()

        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["total_measured"], 0)
        self.assertEqual(summary["pending"], 0)

    def test_summary_counts(self):
        """Test summary counts adaptations correctly."""
        # Log some adaptations
        self.db.log_adaptation(
            adaptation_id="adapt1",
            insight_type="coin",
            action="blacklist",
            target="COIN1",
            description="Test 1",
        )
        self.db.log_adaptation(
            adaptation_id="adapt2",
            insight_type="coin",
            action="blacklist",
            target="COIN2",
            description="Test 2",
        )

        summary = self.monitor.get_effectiveness_summary()

        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["pending"], 2)  # Not measured yet


class TestHealthCheck(unittest.TestCase):
    """Test health check functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)
        self.knowledge = KnowledgeBrain(self.db)
        self.journal = MockJournal()
        self.profitability = MockProfitability()

        self.monitor = EffectivenessMonitor(
            db=self.db,
            journal=self.journal,
            profitability=self.profitability,
            adaptation_engine=MagicMock(),
            knowledge=self.knowledge,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_health_check_healthy(self):
        """Test health check returns healthy status."""
        health = self.monitor.get_health()

        self.assertEqual(health["status"], "healthy")
        self.assertIn("metrics", health)
        self.assertTrue(health["metrics"]["has_journal"])
        self.assertTrue(health["metrics"]["has_profitability"])

    def test_health_check_degraded(self):
        """Test health check returns degraded when dependencies missing."""
        monitor = EffectivenessMonitor(
            db=self.db,
            journal=None,  # Missing
            profitability=None,  # Missing
            adaptation_engine=MagicMock(),
            knowledge=self.knowledge,
        )

        health = monitor.get_health()

        self.assertEqual(health["status"], "degraded")


class TestEffectivenessResultSerialization(unittest.TestCase):
    """Test EffectivenessResult serialization."""

    def test_to_dict(self):
        """Test EffectivenessResult.to_dict()."""
        result = EffectivenessResult(
            adaptation_id="test123",
            rating=EffectivenessRating.EFFECTIVE,
            pre_metrics={"overall": {"win_rate": 50.0}},
            post_metrics={"overall": {"win_rate": 55.0}},
            win_rate_change=5.0,
            pnl_change=25.0,
            profit_factor_change=0.3,
            trades_measured=15,
            hours_elapsed=48.5,
            should_rollback=False,
            measured_at=datetime(2026, 2, 3, 12, 0, 0),
        )

        d = result.to_dict()

        self.assertEqual(d["adaptation_id"], "test123")
        self.assertEqual(d["rating"], "effective")
        self.assertEqual(d["win_rate_change"], 5.0)
        self.assertEqual(d["trades_measured"], 15)
        self.assertFalse(d["should_rollback"])


if __name__ == "__main__":
    unittest.main()
