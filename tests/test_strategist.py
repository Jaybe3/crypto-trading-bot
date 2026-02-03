"""Unit tests for the Strategist component."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import json

from src.models.trade_condition import TradeCondition
from src.strategist import Strategist, DEFAULT_MAX_POSITION_SIZE, DEFAULT_MIN_POSITION_SIZE


class TestTradeCondition:
    """Tests for TradeCondition dataclass."""

    def test_create_condition(self):
        """Test basic condition creation."""
        condition = TradeCondition(
            coin="SOL",
            direction="LONG",
            trigger_price=143.50,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=50.0,
            reasoning="Test reason",
            strategy_id="test_strategy",
        )

        assert condition.coin == "SOL"
        assert condition.direction == "LONG"
        assert condition.trigger_price == 143.50
        assert condition.trigger_condition == "ABOVE"
        assert condition.stop_loss_pct == 2.0
        assert condition.take_profit_pct == 1.5
        assert condition.position_size_usd == 50.0
        assert condition.reasoning == "Test reason"
        assert condition.strategy_id == "test_strategy"
        assert condition.id is not None
        assert condition.created_at is not None
        assert condition.valid_until is not None

    def test_is_expired(self):
        """Test expiration detection."""
        # Not expired
        condition = TradeCondition(
            coin="SOL",
            direction="LONG",
            trigger_price=143.50,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=50.0,
            reasoning="Test",
            strategy_id="test",
            valid_until=datetime.now() + timedelta(minutes=5),
        )
        assert not condition.is_expired()

        # Expired
        expired_condition = TradeCondition(
            coin="SOL",
            direction="LONG",
            trigger_price=143.50,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=50.0,
            reasoning="Test",
            strategy_id="test",
            valid_until=datetime.now() - timedelta(minutes=1),
        )
        assert expired_condition.is_expired()

    def test_is_triggered_above(self):
        """Test trigger detection for ABOVE condition."""
        condition = TradeCondition(
            coin="SOL",
            direction="LONG",
            trigger_price=143.50,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=50.0,
            reasoning="Test",
            strategy_id="test",
        )

        assert not condition.is_triggered(143.00)  # Below trigger
        assert condition.is_triggered(143.50)  # At trigger
        assert condition.is_triggered(144.00)  # Above trigger

    def test_is_triggered_below(self):
        """Test trigger detection for BELOW condition."""
        condition = TradeCondition(
            coin="SOL",
            direction="LONG",
            trigger_price=140.00,
            trigger_condition="BELOW",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=50.0,
            reasoning="Test",
            strategy_id="test",
        )

        assert condition.is_triggered(139.00)  # Below trigger
        assert condition.is_triggered(140.00)  # At trigger
        assert not condition.is_triggered(141.00)  # Above trigger

    def test_calculate_stop_loss_long(self):
        """Test stop loss calculation for LONG position."""
        condition = TradeCondition(
            coin="SOL",
            direction="LONG",
            trigger_price=100.00,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=50.0,
            reasoning="Test",
            strategy_id="test",
        )

        # Long: stop loss is below entry
        assert condition.calculate_stop_loss_price() == 98.00

    def test_calculate_take_profit_long(self):
        """Test take profit calculation for LONG position."""
        condition = TradeCondition(
            coin="SOL",
            direction="LONG",
            trigger_price=100.00,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=50.0,
            reasoning="Test",
            strategy_id="test",
        )

        # Long: take profit is above entry
        assert condition.calculate_take_profit_price() == 101.50

    def test_to_dict(self):
        """Test dictionary serialization."""
        condition = TradeCondition(
            coin="ETH",
            direction="LONG",
            trigger_price=2850.00,
            trigger_condition="ABOVE",
            stop_loss_pct=1.5,
            take_profit_pct=1.0,
            position_size_usd=75.0,
            reasoning="Breakout setup",
            strategy_id="momentum",
        )

        data = condition.to_dict()

        assert data["coin"] == "ETH"
        assert data["direction"] == "LONG"
        assert data["trigger_price"] == 2850.00
        assert data["trigger_condition"] == "ABOVE"
        assert data["stop_loss_pct"] == 1.5
        assert data["take_profit_pct"] == 1.0
        assert data["position_size_usd"] == 75.0
        assert data["reasoning"] == "Breakout setup"
        assert data["strategy_id"] == "momentum"
        assert "id" in data
        assert "created_at" in data
        assert "valid_until" in data

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "coin": "BTC",
            "direction": "LONG",
            "trigger_price": 42500.00,
            "trigger_condition": "ABOVE",
            "stop_loss_pct": 2.0,
            "take_profit_pct": 1.5,
            "position_size_usd": 100.0,
            "reasoning": "Momentum breakout",
            "strategy_id": "breakout",
        }

        condition = TradeCondition.from_dict(data)

        assert condition.coin == "BTC"
        assert condition.direction == "LONG"
        assert condition.trigger_price == 42500.00
        assert condition.trigger_condition == "ABOVE"
        assert condition.position_size_usd == 100.0

    def test_str_representation(self):
        """Test string representation."""
        condition = TradeCondition(
            coin="SOL",
            direction="LONG",
            trigger_price=143.50,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=50.0,
            reasoning="Test",
            strategy_id="test",
        )

        s = str(condition)
        assert "LONG" in s
        assert "SOL" in s
        assert "ABOVE" in s
        assert "143.50" in s


class TestStrategist:
    """Tests for Strategist class."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM interface."""
        llm = Mock()
        llm.query.return_value = json.dumps({
            "conditions": [
                {
                    "coin": "SOL",
                    "direction": "LONG",
                    "trigger_price": 143.50,
                    "trigger_condition": "ABOVE",
                    "stop_loss_pct": 2.0,
                    "take_profit_pct": 1.5,
                    "position_size_usd": 50,
                    "reasoning": "Momentum breakout",
                    "strategy_id": "momentum_breakout",
                }
            ],
            "market_assessment": "Bullish momentum",
            "no_trade_reason": None,
        })
        return llm

    @pytest.fixture
    def mock_market(self):
        """Create mock market feed."""
        market = Mock()

        # Create mock PriceTick
        mock_tick = Mock()
        mock_tick.price = 142.00
        mock_tick.change_24h = 2.5

        market.get_all_prices.return_value = {
            "SOL": mock_tick,
            "ETH": Mock(price=2800.0, change_24h=-0.5),
            "BTC": Mock(price=42000.0, change_24h=1.0),
        }
        market.get_price.return_value = mock_tick

        return market

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.get_account_state.return_value = {
            "balance": 1000.0,
            "available_balance": 1000.0,
            "daily_pnl": 0.0,
        }
        db.delete_expired_conditions.return_value = 0
        return db

    def test_strategist_initialization(self, mock_llm, mock_market, mock_db):
        """Test strategist initialization."""
        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market,
            db=mock_db,
            interval_seconds=120,
        )

        assert strategist.interval == 120
        assert strategist.active_conditions == []
        assert strategist.generation_count == 0

    def test_subscribe_conditions(self, mock_llm, mock_market, mock_db):
        """Test condition callback subscription."""
        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market,
            db=mock_db,
        )

        callback = Mock()
        strategist.subscribe_conditions(callback)

        assert len(strategist._condition_callbacks) == 1

    @pytest.mark.asyncio
    async def test_generate_conditions(self, mock_llm, mock_market, mock_db):
        """Test condition generation."""
        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market,
            db=mock_db,
        )

        conditions = await strategist.generate_conditions()

        assert len(conditions) == 1
        assert conditions[0].coin == "SOL"
        assert conditions[0].direction == "LONG"
        assert conditions[0].trigger_price == 143.50
        assert mock_llm.query.called
        assert mock_db.save_condition.called

    @pytest.mark.asyncio
    async def test_generate_no_conditions(self, mock_llm, mock_market, mock_db):
        """Test when LLM returns no conditions."""
        mock_llm.query.return_value = json.dumps({
            "conditions": [],
            "market_assessment": "Low volatility",
            "no_trade_reason": "No clear setups",
        })

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market,
            db=mock_db,
        )

        conditions = await strategist.generate_conditions()

        assert len(conditions) == 0

    @pytest.mark.asyncio
    async def test_generate_conditions_llm_error(self, mock_llm, mock_market, mock_db):
        """Test handling of LLM errors."""
        mock_llm.query.return_value = None

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market,
            db=mock_db,
        )

        conditions = await strategist.generate_conditions()

        assert len(conditions) == 0

    @pytest.mark.asyncio
    async def test_generate_conditions_invalid_json(self, mock_llm, mock_market, mock_db):
        """Test handling of invalid JSON response."""
        mock_llm.query.return_value = "not valid json"

        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market,
            db=mock_db,
        )

        conditions = await strategist.generate_conditions()

        assert len(conditions) == 0

    def test_validate_condition_position_size(self, mock_llm, mock_market, mock_db):
        """Test position size validation."""
        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market,
            db=mock_db,
        )

        # Valid position size
        valid_condition = TradeCondition(
            coin="SOL",
            direction="LONG",
            trigger_price=142.50,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=50.0,
            reasoning="Test",
            strategy_id="test",
        )
        assert strategist._validate_condition(valid_condition)

        # Position too small
        small_condition = TradeCondition(
            coin="SOL",
            direction="LONG",
            trigger_price=142.50,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=10.0,  # Below minimum
            reasoning="Test",
            strategy_id="test",
        )
        assert not strategist._validate_condition(small_condition)

        # Position too large
        large_condition = TradeCondition(
            coin="SOL",
            direction="LONG",
            trigger_price=142.50,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=150.0,  # Above maximum
            reasoning="Test",
            strategy_id="test",
        )
        assert not strategist._validate_condition(large_condition)

    def test_validate_condition_trigger_price(self, mock_llm, mock_market, mock_db):
        """Test trigger price validation."""
        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market,
            db=mock_db,
        )

        # Trigger price too far from current (>10%)
        far_condition = TradeCondition(
            coin="SOL",
            direction="LONG",
            trigger_price=200.00,  # Way above current ~142
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=50.0,
            reasoning="Test",
            strategy_id="test",
        )
        assert not strategist._validate_condition(far_condition)

    def test_build_context(self, mock_llm, mock_market, mock_db):
        """Test context building."""
        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market,
            db=mock_db,
        )

        context = strategist._build_context()

        assert "market_state" in context
        assert "knowledge" in context
        assert "account" in context
        assert "recent_performance" in context

        assert "SOL" in context["market_state"]["prices"]
        assert context["account"]["balance_usd"] == 1000.0

    def test_parse_response_with_code_block(self, mock_llm, mock_market, mock_db):
        """Test parsing response wrapped in code block."""
        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market,
            db=mock_db,
        )

        response = '''```json
{
    "conditions": [
        {
            "coin": "ETH",
            "direction": "LONG",
            "trigger_price": 2850.00,
            "trigger_condition": "ABOVE",
            "stop_loss_pct": 2.0,
            "take_profit_pct": 1.5,
            "position_size_usd": 75,
            "reasoning": "Test",
            "strategy_id": "test"
        }
    ],
    "market_assessment": "Test",
    "no_trade_reason": null
}
```'''

        conditions = strategist._parse_response(response)

        assert len(conditions) == 1
        assert conditions[0].coin == "ETH"
        assert conditions[0].trigger_price == 2850.00

    def test_get_stats(self, mock_llm, mock_market, mock_db):
        """Test stats retrieval."""
        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market,
            db=mock_db,
        )

        stats = strategist.get_stats()

        assert "generation_count" in stats
        assert "conditions_generated" in stats
        assert "active_conditions" in stats
        assert "interval_seconds" in stats
        assert "is_running" in stats
        assert stats["is_running"] is False

    def test_remove_expired_conditions(self, mock_llm, mock_market, mock_db):
        """Test expired condition removal."""
        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market,
            db=mock_db,
        )

        # Add active and expired conditions
        active = TradeCondition(
            coin="SOL",
            direction="LONG",
            trigger_price=143.50,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=50.0,
            reasoning="Active",
            strategy_id="test",
            valid_until=datetime.now() + timedelta(minutes=5),
        )

        expired = TradeCondition(
            coin="ETH",
            direction="LONG",
            trigger_price=2850.00,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=50.0,
            reasoning="Expired",
            strategy_id="test",
            valid_until=datetime.now() - timedelta(minutes=1),
        )

        strategist.active_conditions = [active, expired]
        strategist._remove_expired_conditions()

        assert len(strategist.active_conditions) == 1
        assert strategist.active_conditions[0].coin == "SOL"

    @pytest.mark.asyncio
    async def test_callback_notification(self, mock_llm, mock_market, mock_db):
        """Test that callbacks are notified."""
        strategist = Strategist(
            llm=mock_llm,
            market_feed=mock_market,
            db=mock_db,
        )

        callback = Mock()
        strategist.subscribe_conditions(callback)

        await strategist.generate_conditions()

        callback.assert_called_once()
        args = callback.call_args[0]
        assert len(args[0]) == 1  # One condition
        assert args[0][0].coin == "SOL"
