"""
Tests for Knowledge Brain integration with Strategist.

TASK-123: Verifies that accumulated knowledge flows correctly
from KnowledgeBrain, CoinScorer, and PatternLibrary into Strategist
prompts and trade condition generation.
"""

import os
import tempfile
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from src.database import Database
from src.knowledge import KnowledgeBrain
from src.coin_scorer import CoinScorer, CoinStatus
from src.pattern_library import PatternLibrary
from src.models.knowledge import CoinScore, TradingPattern, RegimeRule


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(path)
    yield db
    # Database uses connection pooling, no close() needed
    os.unlink(path)


@pytest.fixture
def knowledge_brain(temp_db):
    """Create a KnowledgeBrain with test data."""
    brain = KnowledgeBrain(temp_db)
    return brain


@pytest.fixture
def coin_scorer(knowledge_brain, temp_db):
    """Create a CoinScorer."""
    return CoinScorer(knowledge_brain, temp_db)


@pytest.fixture
def pattern_library(knowledge_brain):
    """Create a PatternLibrary."""
    return PatternLibrary(knowledge_brain)


@pytest.fixture
def mock_market_feed():
    """Create a mock MarketFeed."""
    mock_feed = Mock()

    # Mock tick class
    class MockTick:
        def __init__(self, price, change_24h):
            self.price = price
            self.change_24h = change_24h

    # Set up price data
    prices = {
        "BTC": MockTick(45000.0, 2.5),
        "ETH": MockTick(2500.0, 1.8),
        "SOL": MockTick(100.0, 5.2),
        "DOGE": MockTick(0.12, -3.1),
        "SHIB": MockTick(0.00001, -5.0),
    }

    mock_feed.get_all_prices.return_value = prices
    mock_feed.get_price.side_effect = lambda coin: prices.get(coin)
    mock_feed.get_latest_tick.side_effect = lambda coin: prices.get(coin)

    return mock_feed


@pytest.fixture
def mock_llm():
    """Create a mock LLM interface."""
    mock = Mock()
    mock.query.return_value = '{"conditions": [], "market_assessment": "Test", "no_trade_reason": "Testing"}'
    return mock


class TestKnowledgeToPrompt:
    """Test knowledge flows correctly into Strategist prompts."""

    def test_coin_summaries_in_knowledge(self, knowledge_brain, temp_db):
        """Coin summaries include status, trades, win rate, PnL, trend."""
        # Add coin data
        for _ in range(6):
            knowledge_brain.update_coin_score("SOL", {"won": True, "pnl": 5.0})
        for _ in range(4):
            knowledge_brain.update_coin_score("SOL", {"won": False, "pnl": -2.0})

        # Get the score
        score = knowledge_brain.get_coin_score("SOL")

        assert score is not None
        assert score.coin == "SOL"
        assert score.total_trades == 10
        assert score.wins == 6
        assert score.win_rate == 0.6
        assert score.total_pnl == 22.0  # (6*5) - (4*2)

    def test_good_coins_in_context(self, knowledge_brain, coin_scorer, pattern_library, mock_market_feed, mock_llm, temp_db):
        """Good coins appear in knowledge context."""
        from src.strategist import Strategist

        # Create a favored coin (>=60% win rate, profitable)
        for _ in range(7):
            knowledge_brain.update_coin_score("SOL", {"won": True, "pnl": 5.0})
        for _ in range(3):
            knowledge_brain.update_coin_score("SOL", {"won": False, "pnl": -2.0})

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market_feed,
            knowledge=knowledge_brain,
            coin_scorer=coin_scorer,
            pattern_library=pattern_library,
            db=temp_db,
        )

        context = strategist._build_context()

        assert "SOL" in context["knowledge"]["good_coins"]

    def test_blacklisted_coins_in_avoid(self, knowledge_brain, coin_scorer, pattern_library, mock_market_feed, mock_llm, temp_db):
        """Blacklisted coins appear in avoid list."""
        from src.strategist import Strategist

        # Blacklist a coin
        knowledge_brain.blacklist_coin("SHIB", "Poor performance in testing")

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market_feed,
            knowledge=knowledge_brain,
            coin_scorer=coin_scorer,
            pattern_library=pattern_library,
            db=temp_db,
        )

        context = strategist._build_context()

        assert "SHIB" in context["knowledge"]["avoid_coins"]
        assert "SHIB" in context["knowledge"]["blacklisted"]

    def test_prompt_includes_coin_performance(self, knowledge_brain, coin_scorer, pattern_library, mock_market_feed, mock_llm, temp_db):
        """Prompt includes formatted coin performance section."""
        from src.strategist import Strategist

        # Add some coin history
        for _ in range(5):
            knowledge_brain.update_coin_score("ETH", {"won": True, "pnl": 3.0})

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market_feed,
            knowledge=knowledge_brain,
            coin_scorer=coin_scorer,
            pattern_library=pattern_library,
            db=temp_db,
        )

        context = strategist._build_context()
        prompt = strategist._build_prompt(context)

        assert "COIN PERFORMANCE" in prompt
        assert "ETH" in prompt

    def test_prompt_includes_regime_rules(self, knowledge_brain, coin_scorer, pattern_library, mock_market_feed, mock_llm, temp_db):
        """Prompt includes active regime rules."""
        from src.strategist import Strategist

        # Add a regime rule
        rule = RegimeRule(
            rule_id="test_rule",
            description="No trading on weekends",
            condition={"is_weekend": True},
            action="NO_TRADE",
        )
        knowledge_brain.add_rule(rule)

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market_feed,
            knowledge=knowledge_brain,
            coin_scorer=coin_scorer,
            pattern_library=pattern_library,
            db=temp_db,
        )

        context = strategist._build_context()

        assert len(context["knowledge"]["active_rules"]) > 0
        assert context["knowledge"]["active_rules"][0]["description"] == "No trading on weekends"


class TestRegimeRuleEnforcement:
    """Test regime rules are enforced before condition generation."""

    def test_no_trade_rule_skips_generation(self, knowledge_brain, coin_scorer, pattern_library, mock_market_feed, mock_llm, temp_db):
        """NO_TRADE rule prevents condition generation."""
        import asyncio
        from src.strategist import Strategist

        # Add a rule that always triggers
        rule = RegimeRule(
            rule_id="always_no_trade",
            description="Always block trades for testing",
            condition={"btc_price": {"op": "gt", "value": 0}},  # Always true
            action="NO_TRADE",
        )
        knowledge_brain.add_rule(rule)

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market_feed,
            knowledge=knowledge_brain,
            coin_scorer=coin_scorer,
            pattern_library=pattern_library,
            db=temp_db,
        )

        async def run_test():
            conditions = await strategist.generate_conditions()
            # Should return empty list without calling LLM
            assert conditions == []
            mock_llm.query.assert_not_called()

        asyncio.run(run_test())

    def test_reduce_size_rule_halves_positions(self, knowledge_brain, coin_scorer, pattern_library, mock_market_feed, mock_llm, temp_db):
        """REDUCE_SIZE rule halves position sizes."""
        from src.strategist import Strategist

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market_feed,
            knowledge=knowledge_brain,
            coin_scorer=coin_scorer,
            pattern_library=pattern_library,
            db=temp_db,
        )

        # Simulate REDUCE_SIZE being active
        strategist._active_rule_actions = ["REDUCE_SIZE"]

        # Calculate position size with regime modifier
        base_size = 100.0
        final_size = strategist._calculate_final_position_size(base_size, "BTC")

        assert final_size == 50.0  # Halved due to REDUCE_SIZE


class TestCombinedPositionModifiers:
    """Test position size combines multiple modifiers correctly."""

    def test_blacklisted_coin_returns_zero(self, knowledge_brain, coin_scorer, pattern_library, mock_market_feed, mock_llm, temp_db):
        """Blacklisted coin modifier returns 0."""
        from src.strategist import Strategist

        knowledge_brain.blacklist_coin("SHIB", "Testing")

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market_feed,
            knowledge=knowledge_brain,
            coin_scorer=coin_scorer,
            pattern_library=pattern_library,
            db=temp_db,
        )

        final_size = strategist._calculate_final_position_size(100.0, "SHIB")

        assert final_size == 0.0

    def test_favored_coin_gets_boost(self, knowledge_brain, coin_scorer, pattern_library, mock_market_feed, mock_llm, temp_db):
        """Favored coin gets 1.5x modifier."""
        from src.strategist import Strategist

        # Create a favored coin
        for _ in range(10):
            knowledge_brain.update_coin_score("SOL", {"won": True, "pnl": 5.0})

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market_feed,
            knowledge=knowledge_brain,
            coin_scorer=coin_scorer,
            pattern_library=pattern_library,
            db=temp_db,
        )
        strategist._active_rule_actions = []  # No regime modifiers

        # Base $50, favored coin gets 1.5x = $75
        final_size = strategist._calculate_final_position_size(50.0, "SOL")

        assert final_size == 75.0

    def test_reduced_coin_gets_penalty(self, knowledge_brain, coin_scorer, pattern_library, mock_market_feed, mock_llm, temp_db):
        """Reduced status coin gets 0.5x modifier."""
        from src.strategist import Strategist

        # Create a poor performer (under 45% but not blacklisted)
        for _ in range(4):
            knowledge_brain.update_coin_score("DOGE", {"won": True, "pnl": 2.0})
        for _ in range(6):
            knowledge_brain.update_coin_score("DOGE", {"won": False, "pnl": -3.0})

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market_feed,
            knowledge=knowledge_brain,
            coin_scorer=coin_scorer,
            pattern_library=pattern_library,
            db=temp_db,
        )
        strategist._active_rule_actions = []

        # Base $50, reduced coin gets 0.5x = $25
        final_size = strategist._calculate_final_position_size(50.0, "DOGE")

        assert final_size == 25.0

    def test_combined_modifiers_multiply(self, knowledge_brain, coin_scorer, pattern_library, mock_market_feed, mock_llm, temp_db):
        """Multiple modifiers multiply together."""
        from src.strategist import Strategist

        # Create a favored coin
        for _ in range(10):
            knowledge_brain.update_coin_score("SOL", {"won": True, "pnl": 5.0})

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market_feed,
            knowledge=knowledge_brain,
            coin_scorer=coin_scorer,
            pattern_library=pattern_library,
            db=temp_db,
        )

        # Simulate REDUCE_SIZE active
        strategist._active_rule_actions = ["REDUCE_SIZE"]

        # Base $50 * 1.5 (favored) * 0.5 (regime) = $37.50
        final_size = strategist._calculate_final_position_size(50.0, "SOL")

        assert final_size == 37.50

    def test_enforces_min_position_size(self, knowledge_brain, coin_scorer, pattern_library, mock_market_feed, mock_llm, temp_db):
        """Position size cannot go below minimum."""
        from src.strategist import Strategist, DEFAULT_MIN_POSITION_SIZE

        # Create a REDUCED coin (30-45% win rate, NOT blacklisted)
        # 4 wins out of 10 = 40% win rate, with positive P&L to avoid blacklist
        for _ in range(4):
            knowledge_brain.update_coin_score("DOGE", {"won": True, "pnl": 3.0})
        for _ in range(6):
            knowledge_brain.update_coin_score("DOGE", {"won": False, "pnl": -1.0})
        # Total: 4*3 - 6*1 = +$6 P&L, 40% win rate -> REDUCED (not blacklisted)

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market_feed,
            knowledge=knowledge_brain,
            coin_scorer=coin_scorer,
            pattern_library=pattern_library,
            db=temp_db,
        )
        strategist._active_rule_actions = []  # No regime modifiers

        # Very small base would be below minimum
        # 10 * 0.5 (reduced modifier) = 5, but min is 20
        final_size = strategist._calculate_final_position_size(10.0, "DOGE")

        # Should clamp to minimum
        assert final_size == DEFAULT_MIN_POSITION_SIZE

    def test_enforces_max_position_size(self, knowledge_brain, coin_scorer, pattern_library, mock_market_feed, mock_llm, temp_db):
        """Position size cannot exceed maximum."""
        from src.strategist import Strategist, DEFAULT_MAX_POSITION_SIZE

        # Create a favored coin
        for _ in range(10):
            knowledge_brain.update_coin_score("SOL", {"won": True, "pnl": 5.0})

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market_feed,
            knowledge=knowledge_brain,
            coin_scorer=coin_scorer,
            pattern_library=pattern_library,
            db=temp_db,
        )
        strategist._active_rule_actions = []

        # Large base would exceed max
        final_size = strategist._calculate_final_position_size(100.0, "SOL")

        # 100 * 1.5 = 150, but max is 100
        assert final_size == DEFAULT_MAX_POSITION_SIZE


class TestValidationWithKnowledge:
    """Test condition validation uses knowledge correctly."""

    def test_blacklisted_coin_rejected(self, knowledge_brain, coin_scorer, pattern_library, mock_market_feed, mock_llm, temp_db):
        """Conditions for blacklisted coins are rejected."""
        from src.strategist import Strategist
        from src.models.trade_condition import TradeCondition

        knowledge_brain.blacklist_coin("SHIB", "Testing")

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market_feed,
            knowledge=knowledge_brain,
            coin_scorer=coin_scorer,
            pattern_library=pattern_library,
            db=temp_db,
        )

        condition = TradeCondition(
            coin="SHIB",
            direction="LONG",
            trigger_price=0.000011,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=50.0,
            reasoning="Test blacklist validation",
            strategy_id="test_strategy",
        )

        is_valid = strategist._validate_condition(condition)

        assert is_valid is False


class TestMarketStateForRules:
    """Test market state is built correctly for rule checking."""

    def test_btc_trend_detection(self, knowledge_brain, coin_scorer, pattern_library, mock_market_feed, mock_llm, temp_db):
        """BTC trend is detected from 24h change."""
        from src.strategist import Strategist

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market_feed,
            knowledge=knowledge_brain,
            coin_scorer=coin_scorer,
            pattern_library=pattern_library,
            db=temp_db,
        )

        state = strategist._get_market_state_for_rules()

        assert state["btc_price"] == 45000.0
        assert state["btc_change_24h"] == 2.5
        assert state["btc_trend"] == "up"  # >2% change

    def test_time_context_included(self, knowledge_brain, coin_scorer, pattern_library, mock_market_feed, mock_llm, temp_db):
        """Time context is included in market state."""
        from src.strategist import Strategist

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market_feed,
            knowledge=knowledge_brain,
            coin_scorer=coin_scorer,
            pattern_library=pattern_library,
            db=temp_db,
        )

        state = strategist._get_market_state_for_rules()

        assert "hour_of_day" in state
        assert "day_of_week" in state
        assert "is_weekend" in state
        assert "session" in state


class TestFullIntegrationFlow:
    """Test the complete knowledge integration flow."""

    def test_full_knowledge_flow(self, knowledge_brain, coin_scorer, pattern_library, mock_market_feed, mock_llm, temp_db):
        """Knowledge flows from Brain → Strategist → Conditions."""
        from src.strategist import Strategist

        # Setup: Add coin data
        for _ in range(6):
            knowledge_brain.update_coin_score("SOL", {"won": True, "pnl": 5.0})
        for _ in range(4):
            knowledge_brain.update_coin_score("SOL", {"won": False, "pnl": -2.0})

        knowledge_brain.blacklist_coin("SHIB", "Poor performance")

        # Create strategist
        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market_feed,
            knowledge=knowledge_brain,
            coin_scorer=coin_scorer,
            pattern_library=pattern_library,
            db=temp_db,
        )

        # Verify knowledge flows to context
        context = strategist._build_context()

        assert "SOL" not in context["knowledge"]["avoid_coins"]
        assert "SHIB" in context["knowledge"]["avoid_coins"]

        # Verify prompt includes knowledge
        prompt = strategist._build_prompt(context)

        assert "SHIB" in prompt  # In avoid list
        assert "COIN PERFORMANCE" in prompt
        assert "ACTIVE REGIME RULES" in prompt

    def test_pattern_context_flows_to_prompt(self, knowledge_brain, coin_scorer, pattern_library, mock_market_feed, mock_llm, temp_db):
        """Pattern library context appears in prompts."""
        from src.strategist import Strategist

        # Create a high-confidence pattern
        pattern = pattern_library.create_pattern(
            pattern_type="momentum_breakout",
            description="Long on breakout with volume",
            entry_conditions={"breakout": True, "volume_surge": True},
            exit_conditions={"stop_loss_pct": 2.0, "take_profit_pct": 3.0},
        )

        # Record wins to increase confidence
        for _ in range(10):
            pattern_library.record_pattern_outcome(pattern.pattern_id, won=True, pnl=5.0)

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market_feed,
            knowledge=knowledge_brain,
            coin_scorer=coin_scorer,
            pattern_library=pattern_library,
            db=temp_db,
        )

        context = strategist._build_context()
        prompt = strategist._build_prompt(context)

        # High-confidence pattern should appear
        assert "HIGH-CONFIDENCE PATTERNS" in prompt or "breakout" in prompt.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
