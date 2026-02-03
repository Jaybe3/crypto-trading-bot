"""
Tests for Sniper Execution Engine.
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sniper import Sniper, Position, ExecutionEvent
from src.models.trade_condition import TradeCondition
from src.journal import TradeJournal
from src.market_feed import PriceTick


class TestTradeCondition:
    """Test TradeCondition data class."""

    def test_creation(self):
        condition = TradeCondition(
            id="test-1",
            coin="BTC",
            direction="LONG",
            trigger_price=42000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=100.0,
            strategy_id="test-strategy",
            reasoning="Test condition",
            valid_until=datetime.now() + timedelta(minutes=5),
        )
        assert condition.coin == "BTC"
        assert condition.direction == "LONG"
        assert condition.trigger_price == 42000.0

    def test_is_expired(self):
        # Not expired
        condition = TradeCondition(
            id="test-1",
            coin="BTC",
            direction="LONG",
            trigger_price=42000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=100.0,
            strategy_id="test",
            reasoning="Test",
            valid_until=datetime.now() + timedelta(minutes=5),
        )
        assert not condition.is_expired()

        # Expired
        condition_expired = TradeCondition(
            id="test-2",
            coin="BTC",
            direction="LONG",
            trigger_price=42000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=100.0,
            strategy_id="test",
            reasoning="Test",
            valid_until=datetime.now() - timedelta(minutes=5),
        )
        assert condition_expired.is_expired()

    def test_serialization(self):
        condition = TradeCondition(
            id="test-1",
            coin="BTC",
            direction="LONG",
            trigger_price=42000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=100.0,
            strategy_id="test",
            reasoning="Test",
            valid_until=datetime.now() + timedelta(minutes=5),
        )
        d = condition.to_dict()
        restored = TradeCondition.from_dict(d)
        assert restored.id == condition.id
        assert restored.coin == condition.coin
        assert restored.trigger_price == condition.trigger_price


class TestSniperInitialization:
    """Test Sniper initialization."""

    def test_init_defaults(self):
        journal = TradeJournal()
        sniper = Sniper(journal)
        assert sniper.balance == 10000.0
        assert sniper.initial_balance == 10000.0
        assert len(sniper.open_positions) == 0
        assert len(sniper.active_conditions) == 0

    def test_init_custom_balance(self):
        journal = TradeJournal()
        sniper = Sniper(journal, initial_balance=50000.0)
        assert sniper.balance == 50000.0

    def test_init_status(self):
        journal = TradeJournal()
        sniper = Sniper(journal)
        status = sniper.get_status()
        assert status["balance"] == 10000.0
        assert status["open_positions"] == 0
        assert status["active_conditions"] == 0
        assert status["trades_executed"] == 0


class TestConditionManagement:
    """Test condition management."""

    def test_set_conditions(self):
        journal = TradeJournal()
        sniper = Sniper(journal)

        conditions = [
            TradeCondition(
                id="cond-1",
                coin="BTC",
                direction="LONG",
                trigger_price=42000.0,
                trigger_condition="ABOVE",
                stop_loss_pct=2.0,
                take_profit_pct=1.5,
                position_size_usd=100.0,
                strategy_id="test",
                reasoning="Test",
                valid_until=datetime.now() + timedelta(minutes=5),
            ),
            TradeCondition(
                id="cond-2",
                coin="ETH",
                direction="LONG",
                trigger_price=2500.0,
                trigger_condition="ABOVE",
                stop_loss_pct=2.0,
                take_profit_pct=1.5,
                position_size_usd=100.0,
                strategy_id="test",
                reasoning="Test",
                valid_until=datetime.now() + timedelta(minutes=5),
            ),
        ]

        count = sniper.set_conditions(conditions)
        assert count == 2
        assert len(sniper.active_conditions) == 2

    def test_set_conditions_filters_expired(self):
        journal = TradeJournal()
        sniper = Sniper(journal)

        conditions = [
            TradeCondition(
                id="cond-1",
                coin="BTC",
                direction="LONG",
                trigger_price=42000.0,
                trigger_condition="ABOVE",
                stop_loss_pct=2.0,
                take_profit_pct=1.5,
                position_size_usd=100.0,
                strategy_id="test",
                reasoning="Test",
                valid_until=datetime.now() + timedelta(minutes=5),  # Valid
            ),
            TradeCondition(
                id="cond-2",
                coin="ETH",
                direction="LONG",
                trigger_price=2500.0,
                trigger_condition="ABOVE",
                stop_loss_pct=2.0,
                take_profit_pct=1.5,
                position_size_usd=100.0,
                strategy_id="test",
                reasoning="Test",
                valid_until=datetime.now() - timedelta(minutes=5),  # Expired
            ),
        ]

        count = sniper.set_conditions(conditions)
        assert count == 1  # Only valid one

    def test_add_condition(self):
        journal = TradeJournal()
        sniper = Sniper(journal)

        condition = TradeCondition(
            id="cond-1",
            coin="BTC",
            direction="LONG",
            trigger_price=42000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=100.0,
            strategy_id="test",
            reasoning="Test",
            valid_until=datetime.now() + timedelta(minutes=5),
        )

        result = sniper.add_condition(condition)
        assert result == True
        assert len(sniper.active_conditions) == 1

    def test_add_expired_condition_rejected(self):
        journal = TradeJournal()
        sniper = Sniper(journal)

        condition = TradeCondition(
            id="cond-1",
            coin="BTC",
            direction="LONG",
            trigger_price=42000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=100.0,
            strategy_id="test",
            reasoning="Test",
            valid_until=datetime.now() - timedelta(minutes=5),  # Expired
        )

        result = sniper.add_condition(condition)
        assert result == False
        assert len(sniper.active_conditions) == 0

    def test_clear_conditions(self):
        journal = TradeJournal()
        sniper = Sniper(journal)

        conditions = [
            TradeCondition(
                id=f"cond-{i}",
                coin="BTC" if i % 2 == 0 else "ETH",
                direction="LONG",
                trigger_price=42000.0,
                trigger_condition="ABOVE",
                stop_loss_pct=2.0,
                take_profit_pct=1.5,
                position_size_usd=100.0,
                strategy_id="test",
                reasoning="Test",
                valid_until=datetime.now() + timedelta(minutes=5),
            )
            for i in range(4)
        ]

        sniper.set_conditions(conditions)
        assert len(sniper.active_conditions) == 4

        # Clear only BTC
        cleared = sniper.clear_conditions("BTC")
        assert cleared == 2
        assert len(sniper.active_conditions) == 2

        # Clear all
        cleared = sniper.clear_conditions()
        assert cleared == 2
        assert len(sniper.active_conditions) == 0


class TestEntryTriggering:
    """Test entry condition triggering."""

    def test_trigger_above(self):
        journal = TradeJournal()
        sniper = Sniper(journal)

        condition = TradeCondition(
            id="cond-1",
            coin="BTC",
            direction="LONG",
            trigger_price=42000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=100.0,
            strategy_id="test",
            reasoning="Test buy on breakout",
            valid_until=datetime.now() + timedelta(minutes=5),
        )
        sniper.add_condition(condition)

        # Price below trigger - should not execute
        tick = PriceTick(coin="BTC", price=41999.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)
        assert len(sniper.open_positions) == 0

        # Price at trigger - should execute
        tick = PriceTick(coin="BTC", price=42001.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)
        assert len(sniper.open_positions) == 1
        assert len(sniper.active_conditions) == 0  # Condition consumed

    def test_trigger_below(self):
        journal = TradeJournal()
        sniper = Sniper(journal)

        condition = TradeCondition(
            id="cond-1",
            coin="BTC",
            direction="LONG",
            trigger_price=40000.0,
            trigger_condition="BELOW",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=100.0,
            strategy_id="test",
            reasoning="Test buy on dip",
            valid_until=datetime.now() + timedelta(minutes=5),
        )
        sniper.add_condition(condition)

        # Price above trigger - should not execute
        tick = PriceTick(coin="BTC", price=40001.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)
        assert len(sniper.open_positions) == 0

        # Price below trigger - should execute
        tick = PriceTick(coin="BTC", price=39999.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)
        assert len(sniper.open_positions) == 1

    def test_position_created_correctly(self):
        journal = TradeJournal()
        sniper = Sniper(journal)

        condition = TradeCondition(
            id="cond-1",
            coin="BTC",
            direction="LONG",
            trigger_price=42000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,       # 2% stop loss
            take_profit_pct=1.5,    # 1.5% take profit
            position_size_usd=100.0,
            strategy_id="test",
            reasoning="Test",
            valid_until=datetime.now() + timedelta(minutes=5),
        )
        sniper.add_condition(condition)

        tick = PriceTick(coin="BTC", price=42100.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)

        position = sniper.get_position("BTC")
        assert position is not None
        assert position.coin == "BTC"
        assert position.direction == "LONG"
        assert position.entry_price == 42100.0
        assert position.size_usd == 100.0
        # Stop loss: 42100 * (1 - 0.02) = 41258
        assert abs(position.stop_loss_price - 41258.0) < 1
        # Take profit: 42100 * (1 + 0.015) = 42731.5
        assert abs(position.take_profit_price - 42731.5) < 1


class TestExitLogic:
    """Test exit condition triggering (stop-loss and take-profit)."""

    def _setup_position(self, sniper: Sniper, direction: str = "LONG") -> None:
        """Helper to create a position at $42000."""
        condition = TradeCondition(
            id="cond-1",
            coin="BTC",
            direction=direction,
            trigger_price=42000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,       # 2% stop loss
            take_profit_pct=1.5,    # 1.5% take profit
            position_size_usd=100.0,
            strategy_id="test",
            reasoning="Test",
            valid_until=datetime.now() + timedelta(minutes=5),
        )
        sniper.add_condition(condition)
        tick = PriceTick(coin="BTC", price=42000.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)

    def test_stop_loss_long(self):
        journal = TradeJournal()
        sniper = Sniper(journal)
        self._setup_position(sniper, "LONG")

        assert len(sniper.open_positions) == 1
        # Stop loss at 42000 * 0.98 = 41160

        # Price above stop - should stay open
        tick = PriceTick(coin="BTC", price=41200.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)
        assert len(sniper.open_positions) == 1

        # Price at stop loss - should close
        tick = PriceTick(coin="BTC", price=41100.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)
        assert len(sniper.open_positions) == 0

        # Check journal recorded exit
        exits = [e for e in journal.entries if e.event_type == "exit"]
        assert len(exits) == 1
        assert exits[0].exit_reason == "stop_loss"
        assert exits[0].pnl < 0  # Loss

    def test_take_profit_long(self):
        journal = TradeJournal()
        sniper = Sniper(journal)
        self._setup_position(sniper, "LONG")

        assert len(sniper.open_positions) == 1
        # Take profit at 42000 * 1.015 = 42630

        # Price below TP - should stay open
        tick = PriceTick(coin="BTC", price=42500.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)
        assert len(sniper.open_positions) == 1

        # Price at take profit - should close
        tick = PriceTick(coin="BTC", price=42700.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)
        assert len(sniper.open_positions) == 0

        # Check journal recorded exit
        exits = [e for e in journal.entries if e.event_type == "exit"]
        assert len(exits) == 1
        assert exits[0].exit_reason == "take_profit"
        assert exits[0].pnl > 0  # Profit

    def test_stop_loss_short(self):
        journal = TradeJournal()
        sniper = Sniper(journal)
        self._setup_position(sniper, "SHORT")

        # For SHORT: stop loss at 42000 * 1.02 = 42840
        tick = PriceTick(coin="BTC", price=42900.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)
        assert len(sniper.open_positions) == 0

        exits = [e for e in journal.entries if e.event_type == "exit"]
        assert exits[0].exit_reason == "stop_loss"

    def test_take_profit_short(self):
        journal = TradeJournal()
        sniper = Sniper(journal)
        self._setup_position(sniper, "SHORT")

        # For SHORT: take profit at 42000 * 0.985 = 41370
        tick = PriceTick(coin="BTC", price=41300.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)
        assert len(sniper.open_positions) == 0

        exits = [e for e in journal.entries if e.event_type == "exit"]
        assert exits[0].exit_reason == "take_profit"


class TestPnLCalculation:
    """Test P&L calculations."""

    def test_pnl_long_profit(self):
        journal = TradeJournal()
        sniper = Sniper(journal, initial_balance=10000.0)

        condition = TradeCondition(
            id="cond-1",
            coin="BTC",
            direction="LONG",
            trigger_price=42000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=10.0,       # Wide stop
            take_profit_pct=0.02,     # 2% take profit
            position_size_usd=1000.0,
            strategy_id="test",
            reasoning="Test",
            valid_until=datetime.now() + timedelta(minutes=5),
        )
        sniper.add_condition(condition)

        # Entry at 42000
        tick = PriceTick(coin="BTC", price=42000.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)
        assert sniper.balance == 9000.0  # 10000 - 1000

        # Exit at 42840 (2% profit)
        tick = PriceTick(coin="BTC", price=42840.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)

        # Should get back: 1000 + (1000 * 0.02) = 1020
        assert abs(sniper.balance - 10020.0) < 1
        assert sniper.total_pnl > 0

    def test_pnl_long_loss(self):
        journal = TradeJournal()
        sniper = Sniper(journal, initial_balance=10000.0)

        condition = TradeCondition(
            id="cond-1",
            coin="BTC",
            direction="LONG",
            trigger_price=42000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,       # 2% stop loss
            take_profit_pct=0.10,     # Wide TP
            position_size_usd=1000.0,
            strategy_id="test",
            reasoning="Test",
            valid_until=datetime.now() + timedelta(minutes=5),
        )
        sniper.add_condition(condition)

        # Entry at 42000
        tick = PriceTick(coin="BTC", price=42000.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)

        # Exit at 41160 (2% loss)
        tick = PriceTick(coin="BTC", price=41160.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)

        # Should get back: 1000 + (1000 * -0.02) = 980
        assert abs(sniper.balance - 9980.0) < 1
        assert sniper.total_pnl < 0

    def test_pnl_short_profit(self):
        journal = TradeJournal()
        sniper = Sniper(journal, initial_balance=10000.0)

        condition = TradeCondition(
            id="cond-1",
            coin="BTC",
            direction="SHORT",
            trigger_price=42000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=10.0,       # Wide stop
            take_profit_pct=0.02,     # 2% take profit (price drops)
            position_size_usd=1000.0,
            strategy_id="test",
            reasoning="Test",
            valid_until=datetime.now() + timedelta(minutes=5),
        )
        sniper.add_condition(condition)

        # Entry at 42000
        tick = PriceTick(coin="BTC", price=42000.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)

        # Exit at 41160 (2% profit for SHORT)
        tick = PriceTick(coin="BTC", price=41160.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)

        # Should profit ~2%
        assert sniper.total_pnl > 0


class TestRiskLimits:
    """Test risk limit enforcement."""

    def test_max_positions_limit(self):
        journal = TradeJournal()
        sniper = Sniper(journal, initial_balance=100000.0)

        # Add 6 conditions (MAX_POSITIONS = 5)
        coins = ["BTC", "ETH", "SOL", "XRP", "DOGE", "ADA"]
        for i, coin in enumerate(coins):
            condition = TradeCondition(
                id=f"cond-{i}",
                coin=coin,
                direction="LONG",
                trigger_price=100.0,
                trigger_condition="ABOVE",
                stop_loss_pct=2.0,
                take_profit_pct=1.5,
                position_size_usd=100.0,
                strategy_id="test",
                reasoning="Test",
                valid_until=datetime.now() + timedelta(minutes=5),
            )
            sniper.add_condition(condition)

        # Trigger all 6
        for coin in coins:
            tick = PriceTick(coin=coin, price=101.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
            sniper.on_price_tick(tick)

        # Should only have 5 positions
        assert len(sniper.open_positions) == 5

    def test_max_per_coin_limit(self):
        journal = TradeJournal()
        sniper = Sniper(journal)

        # Add 2 conditions for same coin
        for i in range(2):
            condition = TradeCondition(
                id=f"cond-{i}",
                coin="BTC",
                direction="LONG",
                trigger_price=42000.0 + i * 100,  # Different trigger prices
                trigger_condition="ABOVE",
                stop_loss_pct=2.0,
                take_profit_pct=0.15,  # Wide TP
                position_size_usd=100.0,
                strategy_id="test",
                reasoning="Test",
                valid_until=datetime.now() + timedelta(minutes=5),
            )
            sniper.add_condition(condition)

        # Trigger both
        tick = PriceTick(coin="BTC", price=42200.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)

        # Should only have 1 position (MAX_PER_COIN = 1)
        assert len(sniper.open_positions) == 1

    def test_exposure_limit(self):
        journal = TradeJournal()
        sniper = Sniper(journal, initial_balance=1000.0)

        # MAX_EXPOSURE_PCT = 0.10, so max exposure = $100
        # Try to open position of $200
        condition = TradeCondition(
            id="cond-1",
            coin="BTC",
            direction="LONG",
            trigger_price=42000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=200.0,  # Over limit
            strategy_id="test",
            reasoning="Test",
            valid_until=datetime.now() + timedelta(minutes=5),
        )
        sniper.add_condition(condition)

        tick = PriceTick(coin="BTC", price=42100.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)

        # Should not open position
        assert len(sniper.open_positions) == 0


class TestPerformance:
    """Test tick processing performance."""

    def test_tick_processing_speed(self):
        journal = TradeJournal()
        sniper = Sniper(journal)

        # Add some conditions
        for i in range(5):
            condition = TradeCondition(
                id=f"cond-{i}",
                coin=["BTC", "ETH", "SOL", "XRP", "DOGE"][i],
                direction="LONG",
                trigger_price=50000.0,  # Won't trigger
                trigger_condition="ABOVE",
                stop_loss_pct=2.0,
                take_profit_pct=1.5,
                position_size_usd=100.0,
                strategy_id="test",
                reasoning="Test",
                valid_until=datetime.now() + timedelta(hours=1),
            )
            sniper.add_condition(condition)

        # Process 10000 ticks
        start = time.perf_counter()
        for _ in range(10000):
            tick = PriceTick(
                coin="BTC",
                price=42000.0,
                timestamp=int(time.time() * 1000),
                volume_24h=0,
                change_24h=0
            )
            sniper.on_price_tick(tick)
        elapsed = time.perf_counter() - start

        per_tick_ms = (elapsed / 10000) * 1000

        print(f"\n10000 ticks in {elapsed:.3f}s")
        print(f"Per tick: {per_tick_ms:.4f}ms")

        # Should be < 1ms per tick
        assert per_tick_ms < 1.0, f"Tick processing too slow: {per_tick_ms:.4f}ms"


class TestStatePersistence:
    """Test state save/load."""

    def test_save_and_load_state(self, tmp_path):
        journal = TradeJournal()
        sniper = Sniper(journal, initial_balance=10000.0)

        # Add a condition
        condition = TradeCondition(
            id="cond-1",
            coin="BTC",
            direction="LONG",
            trigger_price=42000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=100.0,
            strategy_id="test",
            reasoning="Test",
            valid_until=datetime.now() + timedelta(hours=1),
        )
        sniper.add_condition(condition)

        # Open a position
        tick = PriceTick(coin="BTC", price=42100.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)

        # Save state
        state_file = tmp_path / "test_state.json"
        sniper.save_state(str(state_file))

        # Create new sniper and load state
        sniper2 = Sniper(TradeJournal(), initial_balance=5000.0)  # Different initial
        sniper2.load_state(str(state_file))

        # Verify state restored
        assert len(sniper2.open_positions) == 1
        position = list(sniper2.open_positions.values())[0]
        assert position.coin == "BTC"
        assert position.entry_price == 42100.0


class TestCallbacks:
    """Test execution event callbacks."""

    def test_entry_callback(self):
        journal = TradeJournal()
        sniper = Sniper(journal)

        events = []
        sniper.subscribe(lambda e: events.append(e))

        condition = TradeCondition(
            id="cond-1",
            coin="BTC",
            direction="LONG",
            trigger_price=42000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=1.5,
            position_size_usd=100.0,
            strategy_id="test",
            reasoning="Test",
            valid_until=datetime.now() + timedelta(minutes=5),
        )
        sniper.add_condition(condition)

        tick = PriceTick(coin="BTC", price=42100.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)

        assert len(events) == 1
        assert events[0].event_type == "entry"
        assert events[0].coin == "BTC"

    def test_exit_callback(self):
        journal = TradeJournal()
        sniper = Sniper(journal)

        events = []
        sniper.subscribe(lambda e: events.append(e))

        condition = TradeCondition(
            id="cond-1",
            coin="BTC",
            direction="LONG",
            trigger_price=42000.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=0.01,  # Tight TP
            position_size_usd=100.0,
            strategy_id="test",
            reasoning="Test",
            valid_until=datetime.now() + timedelta(minutes=5),
        )
        sniper.add_condition(condition)

        # Entry
        tick = PriceTick(coin="BTC", price=42000.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)

        # Exit (take profit at 42420)
        tick = PriceTick(coin="BTC", price=42500.0, timestamp=int(time.time() * 1000), volume_24h=0, change_24h=0)
        sniper.on_price_tick(tick)

        assert len(events) == 2
        assert events[0].event_type == "entry"
        assert events[1].event_type == "exit"
        assert events[1].reason == "take_profit"


def run_tests():
    """Run all tests manually (no pytest)."""
    import traceback

    test_classes = [
        TestTradeCondition,
        TestSniperInitialization,
        TestConditionManagement,
        TestEntryTriggering,
        TestExitLogic,
        TestPnLCalculation,
        TestRiskLimits,
        TestPerformance,
        TestCallbacks,
    ]

    passed = 0
    failed = 0

    for test_class in test_classes:
        print(f"\n=== {test_class.__name__} ===")
        instance = test_class()

        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    method = getattr(instance, method_name)
                    # Handle tmp_path for persistence test
                    if "tmp_path" in method.__code__.co_varnames:
                        import tempfile
                        with tempfile.TemporaryDirectory() as tmp:
                            method(Path(tmp))
                    else:
                        method()
                    print(f"  ✓ {method_name}")
                    passed += 1
                except Exception as e:
                    print(f"  ✗ {method_name}: {e}")
                    traceback.print_exc()
                    failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*40}")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
