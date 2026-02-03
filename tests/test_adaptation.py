"""
Tests for AdaptationEngine (TASK-133).

Tests the insight-to-action conversion system.
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import Database
from src.knowledge import KnowledgeBrain
from src.coin_scorer import CoinScorer
from src.pattern_library import PatternLibrary
from src.adaptation import AdaptationEngine, THRESHOLDS
from src.models.adaptation import AdaptationAction, AdaptationRecord
from src.models.reflection import Insight


class TestAdaptationEngine(unittest.TestCase):
    """Tests for AdaptationEngine."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temp database
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

        self.db = Database(self.db_path)
        self.knowledge = KnowledgeBrain(self.db)
        self.coin_scorer = CoinScorer(self.knowledge, self.db)
        self.pattern_library = PatternLibrary(self.knowledge)
        self.engine = AdaptationEngine(
            self.knowledge, self.coin_scorer, self.pattern_library, self.db
        )

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_blacklist_coin_insight(self):
        """Test that underperforming coin insights trigger blacklist."""
        insight = Insight(
            insight_type="coin",
            category="problem",
            title="DOGE underperforming",
            description="DOGE has 20% win rate over 10 trades with -$15 loss",
            evidence={"coin": "DOGE", "win_rate": 0.20, "trades": 10, "pnl": -15.0},
            suggested_action="Blacklist DOGE",
            confidence=0.90,
        )

        adaptations = self.engine.apply_insights([insight])

        self.assertEqual(len(adaptations), 1)
        self.assertEqual(adaptations[0].action, AdaptationAction.BLACKLIST_COIN.value)
        self.assertEqual(adaptations[0].target, "DOGE")
        self.assertTrue(self.knowledge.is_blacklisted("DOGE"))

    def test_favor_coin_insight(self):
        """Test that overperforming coin insights trigger favor."""
        insight = Insight(
            insight_type="coin",
            category="opportunity",
            title="SOL strong performer",
            description="SOL has 75% win rate over 12 trades with $18 profit",
            evidence={"coin": "SOL", "win_rate": 0.75, "trades": 12, "pnl": 18.0},
            suggested_action="Favor SOL",
            confidence=0.85,
        )

        adaptations = self.engine.apply_insights([insight])

        self.assertEqual(len(adaptations), 1)
        self.assertEqual(adaptations[0].action, AdaptationAction.FAVOR_COIN.value)
        self.assertEqual(adaptations[0].target, "SOL")

        # Check SOL is now marked as "improving"
        score = self.knowledge.get_coin_score("SOL")
        self.assertIsNotNone(score)
        self.assertEqual(score.trend, "improving")

    def test_time_rule_creation(self):
        """Test that time insights create regime rules."""
        insight = Insight(
            insight_type="time",
            category="problem",
            title="Asia session losses",
            description="Hours 2-5 UTC have 25% win rate",
            evidence={"worst_hours": [2, 3, 4, 5], "win_rate": 0.25, "trades": 15},
            suggested_action="Add time filter",
            confidence=0.80,
        )

        adaptations = self.engine.apply_insights([insight])

        self.assertEqual(len(adaptations), 1)
        self.assertEqual(adaptations[0].action, AdaptationAction.CREATE_TIME_RULE.value)
        self.assertIn("time_filter", adaptations[0].target)

        # Verify rule was created
        rules = self.knowledge.get_active_rules()
        time_rules = [r for r in rules if "time_filter" in r.rule_id]
        self.assertEqual(len(time_rules), 1)

    def test_regime_rule_creation(self):
        """Test that regime insights create regime rules."""
        insight = Insight(
            insight_type="regime",
            category="problem",
            title="BTC down losses",
            description="Losing trades when BTC is trending down",
            evidence={"worst_regime": "btc_down", "win_rate": 0.30, "trades": 12},
            suggested_action="Add regime filter",
            confidence=0.80,
        )

        adaptations = self.engine.apply_insights([insight])

        self.assertEqual(len(adaptations), 1)
        self.assertEqual(adaptations[0].action, AdaptationAction.CREATE_REGIME_RULE.value)
        self.assertIn("regime_filter", adaptations[0].target)

        # Verify rule was created
        rules = self.knowledge.get_active_rules()
        regime_rules = [r for r in rules if "regime_filter" in r.rule_id]
        self.assertEqual(len(regime_rules), 1)

    def test_low_confidence_skipped(self):
        """Test that low confidence insights are skipped."""
        insight = Insight(
            insight_type="coin",
            category="problem",
            title="BTC slightly underperforming",
            description="BTC has 45% win rate",
            evidence={"coin": "BTC", "win_rate": 0.45, "trades": 5, "pnl": -2.0},
            suggested_action="Maybe reduce BTC",
            confidence=0.50,  # Too low
        )

        adaptations = self.engine.apply_insights([insight])

        self.assertEqual(len(adaptations), 0)
        self.assertEqual(self.engine.adaptations_skipped, 1)

    def test_insufficient_trades_skipped(self):
        """Test that insights with few trades are skipped."""
        insight = Insight(
            insight_type="coin",
            category="problem",
            title="XRP underperforming",
            description="XRP has 10% win rate",
            evidence={"coin": "XRP", "win_rate": 0.10, "trades": 3, "pnl": -5.0},
            suggested_action="Blacklist XRP",
            confidence=0.90,
        )

        adaptations = self.engine.apply_insights([insight])

        self.assertEqual(len(adaptations), 0)

    def test_no_suggested_action_skipped(self):
        """Test that insights without suggested actions are skipped."""
        insight = Insight(
            insight_type="coin",
            category="observation",
            title="ETH performance noted",
            description="ETH has consistent performance",
            evidence={"coin": "ETH", "win_rate": 0.50, "trades": 10, "pnl": 0.0},
            suggested_action=None,  # No action
            confidence=0.80,
        )

        adaptations = self.engine.apply_insights([insight])

        self.assertEqual(len(adaptations), 0)

    def test_cooldown_prevents_duplicate(self):
        """Test that cooldown prevents duplicate adaptations."""
        insight = Insight(
            insight_type="coin",
            category="problem",
            title="DOGE underperforming",
            description="DOGE has 20% win rate",
            evidence={"coin": "DOGE", "win_rate": 0.20, "trades": 10, "pnl": -15.0},
            suggested_action="Blacklist DOGE",
            confidence=0.90,
        )

        # First application should succeed
        adaptations1 = self.engine.apply_insights([insight])
        self.assertEqual(len(adaptations1), 1)

        # Second application should be skipped (cooldown)
        adaptations2 = self.engine.apply_insights([insight])
        self.assertEqual(len(adaptations2), 0)

    def test_multiple_insights_processed(self):
        """Test that multiple insights are processed correctly."""
        insights = [
            Insight(
                insight_type="coin",
                category="problem",
                title="DOGE underperforming",
                description="DOGE has 20% win rate",
                evidence={"coin": "DOGE", "win_rate": 0.20, "trades": 10, "pnl": -15.0},
                suggested_action="Blacklist DOGE",
                confidence=0.90,
            ),
            Insight(
                insight_type="coin",
                category="opportunity",
                title="SOL strong performer",
                description="SOL has 75% win rate",
                evidence={"coin": "SOL", "win_rate": 0.75, "trades": 12, "pnl": 18.0},
                suggested_action="Favor SOL",
                confidence=0.85,
            ),
            Insight(
                insight_type="coin",
                category="observation",
                title="BTC stable",
                description="BTC has 50% win rate",
                evidence={"coin": "BTC", "win_rate": 0.50, "trades": 20, "pnl": 0.0},
                suggested_action=None,  # Will be skipped
                confidence=0.80,
            ),
        ]

        adaptations = self.engine.apply_insights(insights)

        # Should have 2 adaptations (BTC insight skipped due to no action)
        self.assertEqual(len(adaptations), 2)
        self.assertEqual(self.engine.adaptations_applied, 2)
        self.assertEqual(self.engine.adaptations_skipped, 1)

    def test_adaptation_record_logged_to_db(self):
        """Test that adaptations are logged to database."""
        insight = Insight(
            insight_type="coin",
            category="problem",
            title="DOGE underperforming",
            description="DOGE has 20% win rate",
            evidence={"coin": "DOGE", "win_rate": 0.20, "trades": 10, "pnl": -15.0},
            suggested_action="Blacklist DOGE",
            confidence=0.90,
        )

        self.engine.apply_insights([insight])

        # Check database
        adaptations = self.db.get_adaptations(hours=1)
        self.assertEqual(len(adaptations), 1)
        self.assertEqual(adaptations[0]["target"], "DOGE")
        self.assertEqual(adaptations[0]["action"], "blacklist")

    def test_coin_extraction_from_title(self):
        """Test that coin symbol is extracted from title when not in evidence."""
        insight = Insight(
            insight_type="coin",
            category="problem",
            title="SHIB is losing money",
            description="Poor performance on SHIB trades",
            evidence={"win_rate": 0.15, "trades": 10, "pnl": -20.0},
            suggested_action="Blacklist SHIB",
            confidence=0.90,
        )

        adaptations = self.engine.apply_insights([insight])

        self.assertEqual(len(adaptations), 1)
        self.assertEqual(adaptations[0].target, "SHIB")

    def test_win_rate_threshold_for_blacklist(self):
        """Test that win rate threshold is respected for blacklist."""
        # Win rate too high for blacklist (40% vs 30% threshold)
        insight = Insight(
            insight_type="coin",
            category="problem",
            title="LINK slightly under",
            description="LINK has 40% win rate",
            evidence={"coin": "LINK", "win_rate": 0.40, "trades": 10, "pnl": -5.0},
            suggested_action="Consider reducing LINK",
            confidence=0.90,
        )

        adaptations = self.engine.apply_insights([insight])

        # Should not blacklist because win rate > 30%
        self.assertEqual(len(adaptations), 0)

    def test_win_rate_threshold_for_favor(self):
        """Test that win rate threshold is respected for favor."""
        # Win rate too low for favor (55% vs 60% threshold)
        insight = Insight(
            insight_type="coin",
            category="opportunity",
            title="AVAX decent",
            description="AVAX has 55% win rate",
            evidence={"coin": "AVAX", "win_rate": 0.55, "trades": 10, "pnl": 5.0},
            suggested_action="Favor AVAX",
            confidence=0.85,
        )

        adaptations = self.engine.apply_insights([insight])

        # Should not favor because win rate < 60%
        self.assertEqual(len(adaptations), 0)

    def test_stats_tracking(self):
        """Test that stats are tracked correctly."""
        insights = [
            Insight(
                insight_type="coin",
                category="problem",
                title="DOGE underperforming",
                description="DOGE has 20% win rate",
                evidence={"coin": "DOGE", "win_rate": 0.20, "trades": 10, "pnl": -15.0},
                suggested_action="Blacklist DOGE",
                confidence=0.90,
            ),
            Insight(
                insight_type="coin",
                category="observation",
                title="ETH stable",
                description="ETH is stable",
                evidence={"coin": "ETH", "win_rate": 0.50, "trades": 10},
                suggested_action=None,  # Will be skipped
                confidence=0.80,
            ),
        ]

        self.engine.apply_insights(insights)

        stats = self.engine.get_stats()
        self.assertEqual(stats["adaptations_applied"], 1)
        self.assertEqual(stats["adaptations_skipped"], 1)


class TestAdaptationRecord(unittest.TestCase):
    """Tests for AdaptationRecord dataclass."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        record = AdaptationRecord(
            adaptation_id="test123",
            timestamp=datetime(2026, 2, 3, 12, 0, 0),
            insight_type="coin",
            insight_title="Test insight",
            action="blacklist",
            target="DOGE",
            description="Blacklisted DOGE for testing",
            pre_metrics={"win_rate": 0.20},
            insight_confidence=0.90,
            insight_evidence={"trades": 10},
        )

        d = record.to_dict()

        self.assertEqual(d["adaptation_id"], "test123")
        self.assertEqual(d["insight_type"], "coin")
        self.assertEqual(d["action"], "blacklist")
        self.assertEqual(d["target"], "DOGE")

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        d = {
            "adaptation_id": "test456",
            "timestamp": "2026-02-03T12:00:00",
            "insight_type": "time",
            "insight_title": "Time rule",
            "action": "create_time_rule",
            "target": "time_filter_123",
            "description": "Created time filter",
            "pre_metrics": {},
            "insight_confidence": 0.85,
            "insight_evidence": {},
            "auto_applied": True,
            "post_metrics": None,
            "effectiveness": None,
            "effectiveness_measured_at": None,
        }

        record = AdaptationRecord.from_dict(d)

        self.assertEqual(record.adaptation_id, "test456")
        self.assertEqual(record.action, "create_time_rule")
        self.assertEqual(record.target, "time_filter_123")

    def test_str_representation(self):
        """Test string representation."""
        record = AdaptationRecord(
            adaptation_id="test789",
            timestamp=datetime.now(),
            insight_type="coin",
            insight_title="Test",
            action="blacklist",
            target="DOGE",
            description="Blacklisted DOGE",
            pre_metrics={},
            insight_confidence=0.90,
            insight_evidence={},
        )

        s = str(record)

        self.assertIn("blacklist", s)
        self.assertIn("DOGE", s)


if __name__ == "__main__":
    unittest.main()
