"""Tests for Knowledge Brain data structures and operations."""

import pytest
from datetime import datetime, timedelta

from src.database import Database
from src.knowledge import KnowledgeBrain
from src.models.knowledge import CoinScore, TradingPattern, RegimeRule


class TestCoinScore:
    """Tests for CoinScore dataclass."""

    def test_create_coin_score(self):
        """Test basic CoinScore creation."""
        score = CoinScore(coin="SOL")
        assert score.coin == "SOL"
        assert score.total_trades == 0
        assert score.wins == 0
        assert score.losses == 0
        assert score.win_rate == 0.0
        assert score.is_blacklisted is False
        assert score.last_updated is not None

    def test_coin_score_to_dict(self):
        """Test CoinScore serialization."""
        score = CoinScore(coin="ETH", total_trades=10, wins=6, losses=4)
        data = score.to_dict()

        assert data["coin"] == "ETH"
        assert data["total_trades"] == 10
        assert data["wins"] == 6
        assert data["losses"] == 4
        assert "last_updated" in data

    def test_coin_score_from_dict(self):
        """Test CoinScore deserialization."""
        data = {
            "coin": "BTC",
            "total_trades": 15,
            "wins": 10,
            "losses": 5,
            "total_pnl": 50.0,
            "avg_pnl": 3.33,
            "win_rate": 0.67,
            "avg_winner": 8.0,
            "avg_loser": -4.0,
            "is_blacklisted": False,
            "blacklist_reason": "",
            "last_updated": "2026-02-03T10:00:00",
            "trend": "improving",
        }

        score = CoinScore.from_dict(data)
        assert score.coin == "BTC"
        assert score.total_trades == 15
        assert score.trend == "improving"
        assert isinstance(score.last_updated, datetime)

    def test_recalculate_stats(self):
        """Test statistics recalculation."""
        score = CoinScore(
            coin="SOL",
            total_trades=10,
            wins=6,
            losses=4,
            total_pnl=25.0,
        )
        score.recalculate_stats()

        assert score.win_rate == 0.6
        assert score.avg_pnl == 2.5


class TestTradingPattern:
    """Tests for TradingPattern dataclass."""

    def test_create_pattern(self):
        """Test basic pattern creation."""
        pattern = TradingPattern(
            pattern_id="pullback_support",
            description="Long on pullback to support in uptrend",
            entry_conditions={"trend": "up", "near_support": True},
            exit_conditions={"target_reached": True},
        )

        assert pattern.pattern_id == "pullback_support"
        assert pattern.times_used == 0
        assert pattern.confidence == 0.5
        assert pattern.is_active is True

    def test_pattern_win_rate_property(self):
        """Test win rate calculation."""
        pattern = TradingPattern(
            pattern_id="test",
            description="Test",
            entry_conditions={},
            exit_conditions={},
            times_used=10,
            wins=7,
            losses=3,
        )

        assert pattern.win_rate == 0.7

    def test_pattern_win_rate_zero_uses(self):
        """Test win rate with no uses."""
        pattern = TradingPattern(
            pattern_id="test",
            description="Test",
            entry_conditions={},
            exit_conditions={},
        )

        assert pattern.win_rate == 0.0

    def test_pattern_to_dict(self):
        """Test pattern serialization."""
        pattern = TradingPattern(
            pattern_id="breakout",
            description="Breakout pattern",
            entry_conditions={"breakout": True, "volume_surge": True},
            exit_conditions={"target": 0.02},
        )
        data = pattern.to_dict()

        assert data["pattern_id"] == "breakout"
        # Conditions should be JSON strings
        assert '"breakout": true' in data["entry_conditions"]

    def test_pattern_from_dict(self):
        """Test pattern deserialization."""
        data = {
            "pattern_id": "reversal",
            "description": "Reversal at support",
            "entry_conditions": '{"oversold": true}',
            "exit_conditions": '{"overbought": true}',
            "times_used": 5,
            "wins": 3,
            "losses": 2,
            "total_pnl": 10.0,
            "confidence": 0.6,
            "is_active": True,
            "created_at": "2026-02-01T08:00:00",
            "last_used": None,
        }

        pattern = TradingPattern.from_dict(data)
        assert pattern.pattern_id == "reversal"
        assert pattern.entry_conditions == {"oversold": True}
        assert isinstance(pattern.created_at, datetime)


class TestRegimeRule:
    """Tests for RegimeRule dataclass."""

    def test_create_rule(self):
        """Test basic rule creation."""
        rule = RegimeRule(
            rule_id="low_vol",
            description="Don't trade when BTC volatility < 1%",
            condition={"btc_volatility": {"op": "lt", "value": 1.0}},
            action="NO_TRADE",
        )

        assert rule.rule_id == "low_vol"
        assert rule.action == "NO_TRADE"
        assert rule.is_active is True
        assert rule.times_triggered == 0

    def test_invalid_action_raises(self):
        """Test that invalid action raises error."""
        with pytest.raises(ValueError):
            RegimeRule(
                rule_id="bad",
                description="Bad rule",
                condition={},
                action="INVALID_ACTION",
            )

    def test_rule_check_condition_lt(self):
        """Test condition checking with less-than operator."""
        rule = RegimeRule(
            rule_id="test",
            description="Test",
            condition={"volatility": {"op": "lt", "value": 2.0}},
            action="NO_TRADE",
        )

        assert rule.check_condition({"volatility": 1.5}) is True
        assert rule.check_condition({"volatility": 2.5}) is False

    def test_rule_check_condition_gt(self):
        """Test condition checking with greater-than operator."""
        rule = RegimeRule(
            rule_id="test",
            description="Test",
            condition={"volume": {"op": "gt", "value": 1000000}},
            action="INCREASE_SIZE",
        )

        assert rule.check_condition({"volume": 2000000}) is True
        assert rule.check_condition({"volume": 500000}) is False

    def test_rule_check_condition_eq(self):
        """Test condition checking with equality."""
        rule = RegimeRule(
            rule_id="test",
            description="Test",
            condition={"market_regime": "trending"},
            action="CAUTION",
        )

        assert rule.check_condition({"market_regime": "trending"}) is True
        assert rule.check_condition({"market_regime": "ranging"}) is False

    def test_rule_to_dict(self):
        """Test rule serialization."""
        rule = RegimeRule(
            rule_id="weekend",
            description="Reduce size on weekends",
            condition={"is_weekend": True},
            action="REDUCE_SIZE",
        )
        data = rule.to_dict()

        assert data["rule_id"] == "weekend"
        assert '"is_weekend": true' in data["condition"]

    def test_rule_from_dict(self):
        """Test rule deserialization."""
        data = {
            "rule_id": "funding",
            "description": "No trade when funding negative",
            "condition": '{"funding_rate": {"op": "lt", "value": 0}}',
            "action": "NO_TRADE",
            "times_triggered": 10,
            "estimated_saves": 50.0,
            "is_active": True,
            "created_at": "2026-02-02T12:00:00",
        }

        rule = RegimeRule.from_dict(data)
        assert rule.rule_id == "funding"
        assert rule.condition == {"funding_rate": {"op": "lt", "value": 0}}


class TestKnowledgeBrain:
    """Tests for KnowledgeBrain class."""

    @pytest.fixture
    def brain(self, tmp_path):
        """Create a fresh KnowledgeBrain with temp file database.

        Note: SQLite :memory: databases don't work with the Database class
        because each _get_connection() call creates a new empty database.
        """
        db_path = str(tmp_path / "test_brain.db")
        db = Database(db_path)
        return KnowledgeBrain(db)

    def test_initialization(self, brain):
        """Test KnowledgeBrain initializes empty."""
        assert len(brain.get_all_coin_scores()) == 0
        assert len(brain.get_active_patterns()) == 0
        assert len(brain.get_active_rules()) == 0

    # === Coin Score Tests ===

    def test_update_coin_score_first_trade(self, brain):
        """Test updating score for first trade."""
        score = brain.update_coin_score("SOL", {"won": True, "pnl": 5.0})

        assert score.coin == "SOL"
        assert score.total_trades == 1
        assert score.wins == 1
        assert score.losses == 0
        assert score.total_pnl == 5.0
        assert score.win_rate == 1.0
        assert score.avg_winner == 5.0

    def test_update_coin_score_multiple_trades(self, brain):
        """Test updating score across multiple trades."""
        brain.update_coin_score("SOL", {"won": True, "pnl": 5.0})
        brain.update_coin_score("SOL", {"won": True, "pnl": 3.0})
        brain.update_coin_score("SOL", {"won": False, "pnl": -2.0})

        score = brain.get_coin_score("SOL")
        assert score.total_trades == 3
        assert score.wins == 2
        assert score.losses == 1
        assert score.total_pnl == 6.0
        assert abs(score.win_rate - (2/3)) < 0.01
        assert score.avg_winner == 4.0  # (5+3)/2
        assert score.avg_loser == -2.0

    def test_get_good_coins(self, brain):
        """Test identifying good performing coins."""
        # Add coin with good performance
        for _ in range(6):
            brain.update_coin_score("SOL", {"won": True, "pnl": 2.0})
        for _ in range(2):
            brain.update_coin_score("SOL", {"won": False, "pnl": -1.0})

        # Add coin with bad performance
        for _ in range(6):
            brain.update_coin_score("DOGE", {"won": False, "pnl": -2.0})
        for _ in range(2):
            brain.update_coin_score("DOGE", {"won": True, "pnl": 1.0})

        good = brain.get_good_coins(min_trades=5, min_win_rate=0.5)
        assert "SOL" in good
        assert "DOGE" not in good

    def test_get_bad_coins(self, brain):
        """Test identifying poorly performing coins."""
        # Add coin with bad performance
        for _ in range(8):
            brain.update_coin_score("SHIB", {"won": False, "pnl": -1.0})
        for _ in range(2):
            brain.update_coin_score("SHIB", {"won": True, "pnl": 0.5})

        bad = brain.get_bad_coins(min_trades=5, max_win_rate=0.35)
        assert "SHIB" in bad

    # === Blacklist Tests ===

    def test_blacklist_coin(self, brain):
        """Test blacklisting a coin."""
        brain.blacklist_coin("AXS", "Lost 8 of 10 trades")

        assert brain.is_blacklisted("AXS")
        assert "AXS" in brain.get_blacklisted_coins()

        score = brain.get_coin_score("AXS")
        assert score.blacklist_reason == "Lost 8 of 10 trades"

    def test_unblacklist_coin(self, brain):
        """Test removing coin from blacklist."""
        brain.blacklist_coin("SAND", "Poor performance")
        assert brain.is_blacklisted("SAND")

        brain.unblacklist_coin("SAND")
        assert not brain.is_blacklisted("SAND")

    def test_blacklisted_excluded_from_good_coins(self, brain):
        """Test that blacklisted coins are excluded from good coins."""
        # Add good performance
        for _ in range(6):
            brain.update_coin_score("MANA", {"won": True, "pnl": 2.0})

        assert "MANA" in brain.get_good_coins()

        brain.blacklist_coin("MANA", "Manual blacklist")
        assert "MANA" not in brain.get_good_coins()

    # === Pattern Tests ===

    def test_add_pattern(self, brain):
        """Test adding a trading pattern."""
        pattern = TradingPattern(
            pattern_id="support_bounce",
            description="Long on bounce from support",
            entry_conditions={"near_support": True, "bouncing": True},
            exit_conditions={"at_resistance": True},
        )
        brain.add_pattern(pattern)

        retrieved = brain.get_pattern("support_bounce")
        assert retrieved is not None
        assert retrieved.description == "Long on bounce from support"

    def test_update_pattern_stats(self, brain):
        """Test updating pattern statistics."""
        pattern = TradingPattern(
            pattern_id="test_pattern",
            description="Test pattern",
            entry_conditions={},
            exit_conditions={},
        )
        brain.add_pattern(pattern)

        brain.update_pattern_stats("test_pattern", won=True, pnl=5.0)
        brain.update_pattern_stats("test_pattern", won=True, pnl=3.0)
        brain.update_pattern_stats("test_pattern", won=False, pnl=-2.0)

        updated = brain.get_pattern("test_pattern")
        assert updated.times_used == 3
        assert updated.wins == 2
        assert updated.losses == 1
        assert updated.total_pnl == 6.0

    def test_deactivate_pattern(self, brain):
        """Test deactivating a pattern."""
        pattern = TradingPattern(
            pattern_id="bad_pattern",
            description="Pattern to deactivate",
            entry_conditions={},
            exit_conditions={},
        )
        brain.add_pattern(pattern)
        assert len(brain.get_active_patterns()) == 1

        brain.deactivate_pattern("bad_pattern")
        assert len(brain.get_active_patterns()) == 0

    def test_get_winning_patterns(self, brain):
        """Test filtering for winning patterns."""
        # Add winning pattern
        winning = TradingPattern(
            pattern_id="winner",
            description="Winning pattern",
            entry_conditions={},
            exit_conditions={},
            times_used=10,
            wins=7,
            losses=3,
            confidence=0.7,
        )
        brain.add_pattern(winning)

        # Add losing pattern
        losing = TradingPattern(
            pattern_id="loser",
            description="Losing pattern",
            entry_conditions={},
            exit_conditions={},
            times_used=10,
            wins=3,
            losses=7,
            confidence=0.3,
        )
        brain.add_pattern(losing)

        winners = brain.get_winning_patterns(min_uses=5, min_win_rate=0.55)
        assert len(winners) == 1
        assert winners[0].pattern_id == "winner"

    # === Regime Rule Tests ===

    def test_add_rule(self, brain):
        """Test adding a regime rule."""
        rule = RegimeRule(
            rule_id="low_vol_rule",
            description="Don't trade when volatility is low",
            condition={"volatility": {"op": "lt", "value": 1.0}},
            action="NO_TRADE",
        )
        brain.add_rule(rule)

        assert len(brain.get_active_rules()) == 1

    def test_check_rules(self, brain):
        """Test checking rules against market state."""
        rule = RegimeRule(
            rule_id="vol_check",
            description="No trade when vol < 1%",
            condition={"volatility": {"op": "lt", "value": 1.0}},
            action="NO_TRADE",
        )
        brain.add_rule(rule)

        # Should trigger
        actions = brain.check_rules({"volatility": 0.5})
        assert "NO_TRADE" in actions

        # Should not trigger
        actions = brain.check_rules({"volatility": 2.0})
        assert len(actions) == 0

    def test_deactivate_rule(self, brain):
        """Test deactivating a rule."""
        rule = RegimeRule(
            rule_id="temp_rule",
            description="Temporary rule",
            condition={},
            action="CAUTION",
        )
        brain.add_rule(rule)
        assert len(brain.get_active_rules()) == 1

        brain.deactivate_rule("temp_rule")
        assert len(brain.get_active_rules()) == 0

    # === Strategist Interface Tests ===

    def test_get_knowledge_context(self, brain):
        """Test getting knowledge context for Strategist."""
        # Setup some data
        for _ in range(6):
            brain.update_coin_score("SOL", {"won": True, "pnl": 2.0})
        brain.blacklist_coin("SHIB", "Too volatile")

        rule = RegimeRule(
            rule_id="test_rule",
            description="Test rule description",
            condition={},
            action="CAUTION",
        )
        brain.add_rule(rule)

        pattern = TradingPattern(
            pattern_id="test_pattern",
            description="Test pattern description",
            entry_conditions={},
            exit_conditions={},
            times_used=10,
            wins=7,
        )
        brain.add_pattern(pattern)

        context = brain.get_knowledge_context()

        assert "SOL" in context["good_coins"]
        assert "SHIB" in context["avoid_coins"]
        assert "Test rule description" in context["active_rules"]
        assert "Test pattern description" in context["winning_patterns"]

    def test_get_coin_summary(self, brain):
        """Test getting human-readable coin summary."""
        brain.update_coin_score("ETH", {"won": True, "pnl": 10.0})
        brain.update_coin_score("ETH", {"won": False, "pnl": -3.0})

        summary = brain.get_coin_summary("ETH")
        assert summary is not None
        assert summary["coin"] == "ETH"
        assert summary["trades"] == 2
        assert summary["status"] == "ACTIVE"

    def test_get_coin_summary_not_found(self, brain):
        """Test getting summary for unknown coin."""
        summary = brain.get_coin_summary("UNKNOWN")
        assert summary is None

    def test_get_stats_summary(self, brain):
        """Test getting overall statistics."""
        brain.update_coin_score("SOL", {"won": True, "pnl": 5.0})
        brain.blacklist_coin("SHIB", "Bad")

        pattern = TradingPattern(
            pattern_id="p1",
            description="Pattern 1",
            entry_conditions={},
            exit_conditions={},
        )
        brain.add_pattern(pattern)

        rule = RegimeRule(
            rule_id="r1",
            description="Rule 1",
            condition={},
            action="NO_TRADE",
        )
        brain.add_rule(rule)

        stats = brain.get_stats_summary()
        assert stats["coins"]["total"] == 2  # SOL + SHIB
        assert stats["coins"]["blacklisted"] == 1
        assert stats["patterns"]["total"] == 1
        assert stats["rules"]["total"] == 1


class TestKnowledgeBrainPersistence:
    """Tests for Knowledge Brain persistence across restarts."""

    def test_persistence_across_restart(self, tmp_path):
        """Test that data persists across KnowledgeBrain instances."""
        db_path = str(tmp_path / "test_kb.db")

        # Create and populate
        db1 = Database(db_path)
        brain1 = KnowledgeBrain(db1)
        brain1.update_coin_score("ETH", {"won": True, "pnl": 10.0})
        brain1.blacklist_coin("SAND", "Terrible performance")

        pattern = TradingPattern(
            pattern_id="persist_test",
            description="Test persistence",
            entry_conditions={"test": True},
            exit_conditions={"done": True},
        )
        brain1.add_pattern(pattern)

        rule = RegimeRule(
            rule_id="persist_rule",
            description="Persist rule test",
            condition={"check": True},
            action="CAUTION",
        )
        brain1.add_rule(rule)

        # Simulate restart - create new instances
        db2 = Database(db_path)
        brain2 = KnowledgeBrain(db2)

        # Verify data persisted
        score = brain2.get_coin_score("ETH")
        assert score is not None
        assert score.wins == 1

        assert brain2.is_blacklisted("SAND")

        loaded_pattern = brain2.get_pattern("persist_test")
        assert loaded_pattern is not None
        assert loaded_pattern.description == "Test persistence"

        assert len(brain2.get_active_rules()) == 1
