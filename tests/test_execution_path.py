"""
Verify the complete trade execution path works.
This test confirms the system CAN execute trades.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.sniper import Sniper, Position
from src.market_feed import PriceTick
from src.models.trade_condition import TradeCondition


class TestExecutionPath:
    """Test that the full execution path works."""

    def setup_method(self):
        """Set up test Sniper with mocked journal."""
        self.mock_journal = MagicMock()
        self.mock_journal.record_entry = MagicMock()
        self.mock_journal.record_exit = MagicMock()

        self.sniper = Sniper(
            journal=self.mock_journal,
            initial_balance=10000.0,
            state_path="data/test_sniper_state.json",
        )

    def test_condition_triggers_trade_above(self):
        """Test: BTC ABOVE $70,000 triggers when BTC is $76,274."""
        # Create condition - ABOVE $70,000
        condition = TradeCondition(
            id="test_001",
            coin="BTC",
            direction="LONG",
            trigger_price=70000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=3.0,
            position_size_usd=50.0,
            reasoning="Test condition",
            strategy_id="test",
            created_at=datetime.now(),
            valid_until=datetime.now() + timedelta(minutes=10),
        )

        # Set condition
        self.sniper.set_conditions([condition])
        assert len(self.sniper.active_conditions) == 1

        # Send price tick - BTC at $76,274 (above $70,000)
        tick = PriceTick(
            coin="BTC",
            price=76274.0,
            timestamp=int(datetime.now().timestamp() * 1000),
            volume_24h=1000000.0,
            change_24h=2.0,
        )

        # Process tick
        self.sniper.on_price_tick(tick)

        # Verify trade executed
        assert len(self.sniper.open_positions) == 1, "Should have opened a position"
        assert self.sniper.trades_executed == 1, "Should have executed 1 trade"
        assert len(self.sniper.active_conditions) == 0, "Condition should be consumed"

        # Verify journal was called
        self.mock_journal.record_entry.assert_called_once()

        # Check position details
        position = list(self.sniper.open_positions.values())[0]
        assert position.coin == "BTC"
        assert position.direction == "LONG"
        assert position.entry_price == 76274.0
        assert position.size_usd == 50.0

        print("✅ ABOVE trigger works correctly")

    def test_condition_triggers_trade_below(self):
        """Test: BTC BELOW $80,000 triggers when BTC is $76,274."""
        condition = TradeCondition(
            id="test_002",
            coin="BTC",
            direction="SHORT",
            trigger_price=80000.0,
            trigger_condition="BELOW",
            stop_loss_pct=2.0,
            take_profit_pct=3.0,
            position_size_usd=50.0,
            reasoning="Test condition",
            strategy_id="test",
            created_at=datetime.now(),
            valid_until=datetime.now() + timedelta(minutes=10),
        )

        self.sniper.set_conditions([condition])

        tick = PriceTick(
            coin="BTC",
            price=76274.0,
            timestamp=int(datetime.now().timestamp() * 1000),
            volume_24h=1000000.0,
            change_24h=2.0,
        )

        self.sniper.on_price_tick(tick)

        assert len(self.sniper.open_positions) == 1
        assert self.sniper.trades_executed == 1

        position = list(self.sniper.open_positions.values())[0]
        assert position.direction == "SHORT"

        print("✅ BELOW trigger works correctly")

    def test_condition_does_not_trigger_when_not_met(self):
        """Test: BTC ABOVE $80,000 does NOT trigger when BTC is $76,274."""
        condition = TradeCondition(
            id="test_003",
            coin="BTC",
            direction="LONG",
            trigger_price=80000.0,  # Above current price
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=3.0,
            position_size_usd=50.0,
            reasoning="Test condition",
            strategy_id="test",
            created_at=datetime.now(),
            valid_until=datetime.now() + timedelta(minutes=10),
        )

        self.sniper.set_conditions([condition])

        tick = PriceTick(
            coin="BTC",
            price=76274.0,  # Below trigger
            timestamp=int(datetime.now().timestamp() * 1000),
            volume_24h=1000000.0,
            change_24h=2.0,
        )

        self.sniper.on_price_tick(tick)

        assert len(self.sniper.open_positions) == 0, "Should NOT open position"
        assert self.sniper.trades_executed == 0, "Should NOT execute trade"
        assert len(self.sniper.active_conditions) == 1, "Condition should remain"

        print("✅ Non-triggered condition correctly not executed")

    def test_stop_loss_exit(self):
        """Test that stop-loss exits work."""
        # First open a position
        condition = TradeCondition(
            id="test_004",
            coin="ETH",
            direction="LONG",
            trigger_price=2000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,  # Stop at $2244
            take_profit_pct=5.0,
            position_size_usd=100.0,
            reasoning="Test condition",
            strategy_id="test",
            created_at=datetime.now(),
            valid_until=datetime.now() + timedelta(minutes=10),
        )

        self.sniper.set_conditions([condition])

        # Entry tick at $2290
        entry_tick = PriceTick(
            coin="ETH",
            price=2290.0,
            timestamp=int(datetime.now().timestamp() * 1000),
            volume_24h=1000000.0,
            change_24h=2.0,
        )
        self.sniper.on_price_tick(entry_tick)

        assert len(self.sniper.open_positions) == 1
        position = list(self.sniper.open_positions.values())[0]
        stop_loss_price = position.stop_loss_price
        print(f"  Entry: $2290, Stop-loss at: ${stop_loss_price:.2f}")

        # Price drops below stop-loss
        exit_tick = PriceTick(
            coin="ETH",
            price=stop_loss_price - 10,  # Below stop
            timestamp=int(datetime.now().timestamp() * 1000) + 1000,
            volume_24h=1000000.0,
            change_24h=-3.0,
        )
        self.sniper.on_price_tick(exit_tick)

        assert len(self.sniper.open_positions) == 0, "Position should be closed"
        self.mock_journal.record_exit.assert_called_once()

        print("✅ Stop-loss exit works correctly")

    def test_take_profit_exit(self):
        """Test that take-profit exits work."""
        condition = TradeCondition(
            id="test_005",
            coin="SOL",
            direction="LONG",
            trigger_price=90.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=5.0,  # TP at $105
            position_size_usd=100.0,
            reasoning="Test condition",
            strategy_id="test",
            created_at=datetime.now(),
            valid_until=datetime.now() + timedelta(minutes=10),
        )

        self.sniper.set_conditions([condition])

        # Entry tick at $100
        entry_tick = PriceTick(
            coin="SOL",
            price=100.0,
            timestamp=int(datetime.now().timestamp() * 1000),
            volume_24h=1000000.0,
            change_24h=2.0,
        )
        self.sniper.on_price_tick(entry_tick)

        position = list(self.sniper.open_positions.values())[0]
        tp_price = position.take_profit_price
        print(f"  Entry: $100, Take-profit at: ${tp_price:.2f}")

        # Price rises above take-profit
        exit_tick = PriceTick(
            coin="SOL",
            price=tp_price + 5,  # Above TP
            timestamp=int(datetime.now().timestamp() * 1000) + 1000,
            volume_24h=1000000.0,
            change_24h=8.0,
        )
        self.sniper.on_price_tick(exit_tick)

        assert len(self.sniper.open_positions) == 0, "Position should be closed"
        self.mock_journal.record_exit.assert_called_once()

        print("✅ Take-profit exit works correctly")


if __name__ == "__main__":
    # Run tests directly
    test = TestExecutionPath()

    print("=" * 60)
    print("EXECUTION PATH VERIFICATION TEST")
    print("=" * 60)
    print()

    test.setup_method()
    test.test_condition_triggers_trade_above()

    test.setup_method()
    test.test_condition_triggers_trade_below()

    test.setup_method()
    test.test_condition_does_not_trigger_when_not_met()

    test.setup_method()
    test.test_stop_loss_exit()

    test.setup_method()
    test.test_take_profit_exit()

    print()
    print("=" * 60)
    print("ALL EXECUTION PATH TESTS PASSED ✅")
    print("=" * 60)
    print()
    print("CONCLUSION: The system CAN execute trades.")
    print("The issue is that trigger prices are set too far from")
    print("current prices (~2% gap) with a 5-minute TTL.")
