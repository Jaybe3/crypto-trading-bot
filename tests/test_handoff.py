"""
Integration tests for Strategist → Sniper handoff.

Tests that conditions flow correctly from LLM generation to Sniper execution.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.strategist import Strategist
from src.sniper import Sniper, Position
from src.models.trade_condition import TradeCondition
from src.market_feed import MarketFeed, PriceTick
from src.journal import TradeJournal


class TestHandoff:
    """Test Strategist → Sniper handoff."""

    def test_callback_wiring(self):
        """Test that callback wiring works."""
        # Create mocks
        mock_llm = Mock()
        mock_market = Mock()
        mock_market.get_all_prices.return_value = {}
        mock_market.get_price.return_value = None

        journal = TradeJournal()
        sniper = Sniper(journal)
        strategist = Strategist(mock_llm, mock_market)

        # Track received conditions
        received = []

        def on_conditions(conditions):
            received.extend(conditions)
            sniper.set_conditions(conditions)

        strategist.subscribe_conditions(on_conditions)

        # Simulate callback
        test_condition = TradeCondition(
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

        strategist._notify_callbacks([test_condition])

        assert len(received) == 1
        assert received[0].coin == "SOL"
        assert len(sniper.active_conditions) == 1

    def test_condition_format_compatibility(self):
        """Test that Strategist conditions work with Sniper."""
        journal = TradeJournal()
        sniper = Sniper(journal)

        # Create condition using models.trade_condition (Strategist format)
        condition = TradeCondition(
            coin="ETH",
            direction="LONG",
            trigger_price=2850.00,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=75.0,
            reasoning="Momentum breakout",
            strategy_id="momentum",
        )

        # Should work with Sniper
        result = sniper.add_condition(condition)
        assert result is True
        assert len(sniper.active_conditions) == 1
        assert "ETH" in [c.coin for c in sniper.active_conditions.values()]

    def test_trigger_condition_field(self):
        """Test that trigger_condition field works correctly."""
        journal = TradeJournal()
        sniper = Sniper(journal)

        # ABOVE condition
        above_condition = TradeCondition(
            coin="BTC",
            direction="LONG",
            trigger_price=50000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=100.0,
            reasoning="Breakout",
            strategy_id="test",
        )
        sniper.add_condition(above_condition)

        # Price below trigger - should not execute
        tick_below = PriceTick(coin="BTC", price=49000.0, timestamp=1000, volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick_below)
        assert len(sniper.open_positions) == 0

        # Price above trigger - should execute
        tick_above = PriceTick(coin="BTC", price=50100.0, timestamp=2000, volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick_above)
        assert len(sniper.open_positions) == 1

    def test_full_handoff_flow(self):
        """Test complete flow from Strategist generation to Sniper execution."""
        # Setup
        mock_llm = Mock()
        mock_llm.query.return_value = json.dumps({
            "conditions": [
                {
                    "coin": "SOL",
                    "direction": "LONG",
                    "trigger_price": 140.00,
                    "trigger_condition": "ABOVE",
                    "stop_loss_pct": 2.0,
                    "take_profit_pct": 1.5,
                    "position_size_usd": 50,
                    "reasoning": "Test breakout",
                    "strategy_id": "test_strategy",
                }
            ],
            "market_assessment": "Test",
            "no_trade_reason": None,
        })

        mock_tick = Mock()
        mock_tick.price = 138.00
        mock_tick.change_24h = 1.0

        mock_market = Mock()
        mock_market.get_all_prices.return_value = {"SOL": mock_tick}
        mock_market.get_price.return_value = mock_tick

        journal = TradeJournal()
        sniper = Sniper(journal)
        strategist = Strategist(mock_llm, mock_market)

        # Wire handoff
        def on_conditions(conditions):
            sniper.set_conditions(conditions)

        strategist.subscribe_conditions(on_conditions)

        # Run async test
        async def run_test():
            # Generate conditions
            conditions = await strategist.generate_conditions()

            # Verify conditions were generated
            assert len(conditions) == 1

            # Notify callbacks (mimics what _run_once does)
            strategist._notify_callbacks(conditions)

            # Verify conditions passed to sniper
            assert len(sniper.active_conditions) == 1

            # Simulate price tick below trigger
            tick_below = PriceTick(coin="SOL", price=139.00, timestamp=1000, volume_24h=0, change_24h=0)
            sniper.on_price_tick(tick_below)
            assert len(sniper.open_positions) == 0

            # Simulate price tick above trigger
            tick_above = PriceTick(coin="SOL", price=141.00, timestamp=2000, volume_24h=0, change_24h=0)
            sniper.on_price_tick(tick_above)
            assert len(sniper.open_positions) == 1

            # Verify position details
            position = list(sniper.open_positions.values())[0]
            assert position.coin == "SOL"
            assert position.direction == "LONG"
            assert position.entry_price == 141.00

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_test())
        finally:
            loop.close()

    def test_multiple_conditions(self):
        """Test handling multiple conditions from Strategist."""
        journal = TradeJournal()
        sniper = Sniper(journal)

        conditions = [
            TradeCondition(
                coin="BTC",
                direction="LONG",
                trigger_price=50000.0,
                trigger_condition="ABOVE",
                stop_loss_pct=2.0,
                take_profit_pct=1.5,
                position_size_usd=100.0,
                reasoning="BTC breakout",
                strategy_id="test",
            ),
            TradeCondition(
                coin="ETH",
                direction="LONG",
                trigger_price=2800.0,
                trigger_condition="ABOVE",
                stop_loss_pct=2.0,
                take_profit_pct=1.5,
                position_size_usd=75.0,
                reasoning="ETH breakout",
                strategy_id="test",
            ),
            TradeCondition(
                coin="SOL",
                direction="LONG",
                trigger_price=140.0,
                trigger_condition="BELOW",
                stop_loss_pct=2.0,
                take_profit_pct=1.5,
                position_size_usd=50.0,
                reasoning="SOL dip buy",
                strategy_id="test",
            ),
        ]

        count = sniper.set_conditions(conditions)
        assert count == 3
        assert len(sniper.active_conditions) == 3

    def test_condition_replacement(self):
        """Test that new conditions replace old ones."""
        journal = TradeJournal()
        sniper = Sniper(journal)

        # First set
        first_conditions = [
            TradeCondition(
                coin="BTC",
                direction="LONG",
                trigger_price=50000.0,
                trigger_condition="ABOVE",
                stop_loss_pct=2.0,
                take_profit_pct=1.5,
                position_size_usd=100.0,
                reasoning="Old",
                strategy_id="test",
            ),
        ]
        sniper.set_conditions(first_conditions)
        assert len(sniper.active_conditions) == 1

        # Second set (should replace)
        second_conditions = [
            TradeCondition(
                coin="ETH",
                direction="LONG",
                trigger_price=2800.0,
                trigger_condition="ABOVE",
                stop_loss_pct=2.0,
                take_profit_pct=1.5,
                position_size_usd=75.0,
                reasoning="New",
                strategy_id="test",
            ),
            TradeCondition(
                coin="SOL",
                direction="LONG",
                trigger_price=140.0,
                trigger_condition="ABOVE",
                stop_loss_pct=2.0,
                take_profit_pct=1.5,
                position_size_usd=50.0,
                reasoning="New",
                strategy_id="test",
            ),
        ]
        sniper.set_conditions(second_conditions)

        # Should have 2 new conditions, not 3
        assert len(sniper.active_conditions) == 2
        coins = [c.coin for c in sniper.active_conditions.values()]
        assert "BTC" not in coins
        assert "ETH" in coins
        assert "SOL" in coins

    def test_expired_conditions_filtered(self):
        """Test that expired conditions are filtered out."""
        journal = TradeJournal()
        sniper = Sniper(journal)

        conditions = [
            TradeCondition(
                coin="BTC",
                direction="LONG",
                trigger_price=50000.0,
                trigger_condition="ABOVE",
                stop_loss_pct=2.0,
                take_profit_pct=1.5,
                position_size_usd=100.0,
                reasoning="Active",
                strategy_id="test",
                valid_until=datetime.now() + timedelta(minutes=5),
            ),
            TradeCondition(
                coin="ETH",
                direction="LONG",
                trigger_price=2800.0,
                trigger_condition="ABOVE",
                stop_loss_pct=2.0,
                take_profit_pct=1.5,
                position_size_usd=75.0,
                reasoning="Expired",
                strategy_id="test",
                valid_until=datetime.now() - timedelta(minutes=1),  # Already expired
            ),
        ]

        count = sniper.set_conditions(conditions)
        assert count == 1
        assert len(sniper.active_conditions) == 1
        assert list(sniper.active_conditions.values())[0].coin == "BTC"


# Run tests directly
if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
