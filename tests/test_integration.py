"""
Integration tests for the full autonomous learning loop (TASK-140).

Tests end-to-end flows through the system.
"""

import asyncio
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import Database
from src.knowledge import KnowledgeBrain
from src.coin_scorer import CoinScorer
from src.pattern_library import PatternLibrary
from src.adaptation import AdaptationEngine
from src.models.reflection import Insight


class TestComponentHealth(unittest.TestCase):
    """Test that all components expose health status."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)
        self.knowledge = KnowledgeBrain(self.db)
        self.coin_scorer = CoinScorer(self.knowledge, self.db)
        self.pattern_library = PatternLibrary(self.knowledge)

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_adaptation_engine_health(self):
        """Test AdaptationEngine.get_health()."""
        engine = AdaptationEngine(
            self.knowledge, self.coin_scorer, self.pattern_library, self.db
        )

        health = engine.get_health()

        self.assertIn("status", health)
        self.assertIn("metrics", health)
        self.assertEqual(health["status"], "healthy")
        self.assertTrue(health["metrics"]["has_knowledge_brain"])

    def test_adaptation_engine_health_degraded(self):
        """Test AdaptationEngine health when knowledge brain missing."""
        engine = AdaptationEngine(None, None, None, None)

        health = engine.get_health()

        self.assertEqual(health["status"], "degraded")
        self.assertFalse(health["metrics"]["has_knowledge_brain"])


class TestRuntimeStatePersistence(unittest.TestCase):
    """Test runtime state save/restore functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_save_and_restore_state(self):
        """Test that runtime state can be saved and restored."""
        state = {
            "shutdown_time": datetime.now().isoformat(),
            "last_reflection_time": "2026-02-03T10:00:00",
            "trades_since_reflection": 5,
            "uptime_seconds": 3600,
        }

        self.db.save_runtime_state(state)
        restored = self.db.get_runtime_state()

        self.assertEqual(restored["last_reflection_time"], "2026-02-03T10:00:00")
        self.assertEqual(restored["trades_since_reflection"], 5)
        self.assertEqual(restored["uptime_seconds"], 3600)

    def test_clear_state(self):
        """Test clearing runtime state."""
        self.db.save_runtime_state({"key": "value"})
        self.db.clear_runtime_state()
        restored = self.db.get_runtime_state()

        self.assertEqual(len(restored), 0)

    def test_overwrite_state(self):
        """Test that saving state overwrites previous values."""
        self.db.save_runtime_state({"key": "value1"})
        self.db.save_runtime_state({"key": "value2"})
        restored = self.db.get_runtime_state()

        self.assertEqual(restored["key"], "value2")


class TestLearningLoopIntegration(unittest.TestCase):
    """Test the complete learning loop integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)
        self.knowledge = KnowledgeBrain(self.db)
        self.coin_scorer = CoinScorer(self.knowledge, self.db)
        self.pattern_library = PatternLibrary(self.knowledge)
        self.adaptation_engine = AdaptationEngine(
            self.knowledge, self.coin_scorer, self.pattern_library, self.db
        )

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_insight_to_blacklist_flow(self):
        """Test: Insight -> AdaptationEngine -> KnowledgeBrain blacklist."""
        # Simulate an insight from ReflectionEngine
        insight = Insight(
            insight_type="coin",
            category="problem",
            title="DOGE underperforming",
            description="DOGE has 20% win rate over 10 trades",
            evidence={"coin": "DOGE", "win_rate": 0.20, "trades": 10, "pnl": -15.0},
            suggested_action="Blacklist DOGE",
            confidence=0.90,
        )

        # Before: DOGE not blacklisted
        self.assertFalse(self.knowledge.is_blacklisted("DOGE"))

        # Apply insight via AdaptationEngine
        adaptations = self.adaptation_engine.apply_insights([insight])

        # After: DOGE should be blacklisted
        self.assertEqual(len(adaptations), 1)
        self.assertTrue(self.knowledge.is_blacklisted("DOGE"))

        # Verify blacklist reason
        score = self.knowledge.get_coin_score("DOGE")
        self.assertIn("20%", score.blacklist_reason)

    def test_blacklisted_coin_excluded_from_good_coins(self):
        """Test: Blacklisted coins are excluded from good_coins list."""
        # First, add some trades for SOL to make it "good"
        for i in range(6):
            self.knowledge.update_coin_score("SOL", {"won": True, "pnl": 5.0})

        # Verify SOL is in good coins
        self.assertIn("SOL", self.knowledge.get_good_coins())

        # Now blacklist SOL
        self.knowledge.blacklist_coin("SOL", "Test blacklist")

        # SOL should no longer be in good coins
        self.assertNotIn("SOL", self.knowledge.get_good_coins())

    def test_adaptation_logged_to_database(self):
        """Test: Adaptations are logged to database for tracking."""
        insight = Insight(
            insight_type="coin",
            category="problem",
            title="XRP underperforming",
            description="XRP has 15% win rate",
            evidence={"coin": "XRP", "win_rate": 0.15, "trades": 10, "pnl": -20.0},
            suggested_action="Blacklist XRP",
            confidence=0.90,
        )

        self.adaptation_engine.apply_insights([insight])

        # Check database
        adaptations = self.db.get_adaptations(hours=1)
        self.assertEqual(len(adaptations), 1)
        self.assertEqual(adaptations[0]["target"], "XRP")
        self.assertEqual(adaptations[0]["action"], "blacklist")

    def test_time_rule_creation_flow(self):
        """Test: Time insight -> AdaptationEngine -> Regime rule created."""
        insight = Insight(
            insight_type="time",
            category="problem",
            title="Asia session losses",
            description="Hours 2-5 UTC have 25% win rate",
            evidence={"worst_hours": [2, 3, 4, 5], "win_rate": 0.25, "trades": 15},
            suggested_action="Add time filter",
            confidence=0.80,
        )

        # Before: No time rules
        rules_before = self.knowledge.get_active_rules()
        time_rules_before = [r for r in rules_before if "time_filter" in r.rule_id]
        self.assertEqual(len(time_rules_before), 0)

        # Apply insight
        adaptations = self.adaptation_engine.apply_insights([insight])

        # After: Time rule should exist
        rules_after = self.knowledge.get_active_rules()
        time_rules_after = [r for r in rules_after if "time_filter" in r.rule_id]
        self.assertEqual(len(time_rules_after), 1)
        self.assertEqual(len(adaptations), 1)

    def test_cooldown_prevents_duplicate_adaptations(self):
        """Test: Same adaptation cannot be applied twice within cooldown period."""
        insight = Insight(
            insight_type="coin",
            category="problem",
            title="SHIB underperforming",
            description="SHIB has 20% win rate",
            evidence={"coin": "SHIB", "win_rate": 0.20, "trades": 10, "pnl": -10.0},
            suggested_action="Blacklist SHIB",
            confidence=0.90,
        )

        # First application should succeed
        adaptations1 = self.adaptation_engine.apply_insights([insight])
        self.assertEqual(len(adaptations1), 1)

        # Second application should be skipped (cooldown)
        adaptations2 = self.adaptation_engine.apply_insights([insight])
        self.assertEqual(len(adaptations2), 0)


class TestSystemHealthAggregation(unittest.TestCase):
    """Test system-level health aggregation."""

    def test_health_aggregation_logic(self):
        """Test that overall health degrades when any component degrades."""
        # Simulate component health responses
        component_healths = {
            "market_feed": {"status": "healthy"},
            "sniper": {"status": "healthy"},
            "strategist": {"status": "degraded"},  # One degraded
            "reflection_engine": {"status": "healthy"},
        }

        # Aggregate
        overall = "healthy"
        for name, health in component_healths.items():
            status = health.get("status")
            if status == "failed":
                overall = "failed"
            elif status == "degraded" and overall == "healthy":
                overall = "degraded"

        self.assertEqual(overall, "degraded")

    def test_health_aggregation_failed(self):
        """Test that overall health fails when any component fails."""
        component_healths = {
            "market_feed": {"status": "failed"},  # One failed
            "sniper": {"status": "healthy"},
        }

        overall = "healthy"
        for name, health in component_healths.items():
            status = health.get("status")
            if status == "failed":
                overall = "failed"
            elif status == "degraded" and overall == "healthy":
                overall = "degraded"

        self.assertEqual(overall, "failed")


class TestKnowledgeBrainPersistence(unittest.TestCase):
    """Test that Knowledge Brain state persists across restarts."""

    def test_coin_scores_persist(self):
        """Test that coin scores survive restart."""
        db_fd, db_path = tempfile.mkstemp(suffix=".db")

        try:
            # Create first instance and add data
            db1 = Database(db_path)
            knowledge1 = KnowledgeBrain(db1)
            knowledge1.update_coin_score("ETH", {"won": True, "pnl": 10.0})
            knowledge1.blacklist_coin("BAD", "Testing")

            # Verify data exists
            score1 = knowledge1.get_coin_score("ETH")
            self.assertIsNotNone(score1)
            self.assertEqual(score1.wins, 1)
            self.assertTrue(knowledge1.is_blacklisted("BAD"))

            # Create second instance (simulating restart)
            db2 = Database(db_path)
            knowledge2 = KnowledgeBrain(db2)

            # Verify data persisted
            score2 = knowledge2.get_coin_score("ETH")
            self.assertIsNotNone(score2)
            self.assertEqual(score2.wins, 1)
            self.assertTrue(knowledge2.is_blacklisted("BAD"))

        finally:
            os.close(db_fd)
            os.unlink(db_path)

    def test_patterns_persist(self):
        """Test that trading patterns survive restart."""
        db_fd, db_path = tempfile.mkstemp(suffix=".db")

        try:
            # Create first instance
            db1 = Database(db_path)
            knowledge1 = KnowledgeBrain(db1)
            patterns1 = PatternLibrary(knowledge1)

            # Get initial pattern count
            initial_count = len(knowledge1.get_active_patterns())

            # Deactivate a pattern
            patterns = knowledge1.get_active_patterns()
            if patterns:
                knowledge1.deactivate_pattern(patterns[0].pattern_id)

            # Create second instance (simulating restart)
            db2 = Database(db_path)
            knowledge2 = KnowledgeBrain(db2)

            # Verify deactivation persisted
            new_count = len(knowledge2.get_active_patterns())
            self.assertEqual(new_count, initial_count - 1)

        finally:
            os.close(db_fd)
            os.unlink(db_path)

    def test_rules_persist(self):
        """Test that regime rules survive restart."""
        db_fd, db_path = tempfile.mkstemp(suffix=".db")

        try:
            # Create first instance
            db1 = Database(db_path)
            knowledge1 = KnowledgeBrain(db1)

            from src.models.knowledge import RegimeRule
            rule = RegimeRule(
                rule_id="test_rule_persist",
                description="Test rule for persistence",
                condition={"hour_of_day": {"op": "in", "value": [1, 2, 3]}},
                action="REDUCE_SIZE",
            )
            knowledge1.add_rule(rule)

            # Create second instance (simulating restart)
            db2 = Database(db_path)
            knowledge2 = KnowledgeBrain(db2)

            # Verify rule persisted
            rules = knowledge2.get_active_rules()
            rule_ids = [r.rule_id for r in rules]
            self.assertIn("test_rule_persist", rule_ids)

        finally:
            os.close(db_fd)
            os.unlink(db_path)


if __name__ == "__main__":
    unittest.main()
