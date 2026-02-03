"""
Integration Tests - End-to-end testing of the trading system.

Tests the complete flow: Feed → Sniper → Journal
"""

import asyncio
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main_v2 import TradingSystem, HealthMonitor
from src.sniper import TradeCondition
from src.market_feed import PriceTick


class TestHealthMonitor:
    """Test HealthMonitor class."""

    def test_init(self):
        health = HealthMonitor()
        assert health.tick_count == 0
        assert health.last_tick_time is None
        assert not health.is_healthy

    def test_on_tick(self):
        health = HealthMonitor()
        tick = PriceTick(coin="BTC", price=50000.0, timestamp=int(time.time()*1000), volume_24h=0, change_24h=0)

        health.on_tick(tick)

        assert health.tick_count == 1
        assert health.last_tick_time is not None
        assert health.is_healthy

    def test_stale_detection(self):
        health = HealthMonitor(stale_threshold=0.1)  # 100ms threshold
        tick = PriceTick(coin="BTC", price=50000.0, timestamp=int(time.time()*1000), volume_24h=0, change_24h=0)

        health.on_tick(tick)
        assert health.is_healthy

        time.sleep(0.2)  # Wait past threshold
        assert not health.is_healthy
        assert health.is_feed_stale

    def test_get_stats(self):
        health = HealthMonitor()
        tick = PriceTick(coin="BTC", price=50000.0, timestamp=int(time.time()*1000), volume_24h=0, change_24h=0)
        health.on_tick(tick)

        stats = health.get_stats()

        assert "healthy" in stats
        assert "tick_count" in stats
        assert stats["tick_count"] == 1
        assert "ticks_per_second" in stats

    def test_last_price_tracking(self):
        health = HealthMonitor()

        tick1 = PriceTick(coin="BTC", price=50000.0, timestamp=int(time.time()*1000), volume_24h=0, change_24h=0)
        tick2 = PriceTick(coin="ETH", price=3000.0, timestamp=int(time.time()*1000), volume_24h=0, change_24h=0)

        health.on_tick(tick1)
        health.on_tick(tick2)

        assert health.get_last_price("BTC") == 50000.0
        assert health.get_last_price("ETH") == 3000.0
        assert health.get_last_price("SOL") is None


class TestTradingSystemInit:
    """Test TradingSystem initialization."""

    def test_init_defaults(self):
        system = TradingSystem(test_mode=True)

        assert system.test_mode == True
        assert system.exchange == "bybit"
        assert len(system.coins) > 0
        assert system._running == False

    def test_init_custom(self):
        system = TradingSystem(
            exchange="binance",
            coins=["BTC", "ETH"],
            initial_balance=5000.0,
            test_mode=True
        )

        assert system.exchange == "binance"
        assert system.coins == ["BTC", "ETH"]
        assert system.initial_balance == 5000.0


class TestTradingSystemComponents:
    """Test component initialization."""

    def test_start_components(self):
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                system = TradingSystem(
                    test_mode=True,
                    coins=["BTC", "ETH"],
                    db_path=f"{tmp}/test.db",
                    state_path=f"{tmp}/state.json"
                )
                await system.start_components()

                assert system.journal is not None
                assert system.sniper is not None
                assert system.market_feed is not None
                assert system.health is not None

                await system.stop()

        asyncio.run(run())

    def test_callbacks_wired(self):
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                system = TradingSystem(
                    test_mode=True,
                    coins=["BTC"],
                    db_path=f"{tmp}/test.db",
                    state_path=f"{tmp}/state.json"
                )
                await system.start_components()

                # Verify sniper receives ticks
                initial_tick_count = system.sniper._tick_count
                system.inject_price("BTC", 50000.0)

                assert system.sniper._tick_count == initial_tick_count + 1
                assert system.health.tick_count == 1

                await system.stop()

        asyncio.run(run())


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_condition_trigger(self):
        """Test that a condition triggers when price crosses threshold."""
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                system = TradingSystem(
                    test_mode=True,
                    coins=["BTC"],
                    db_path=f"{tmp}/test.db",
                    state_path=f"{tmp}/state.json"
                )
                await system.start_components()

                # Create condition: BUY if price > 50000
                condition = TradeCondition(
                    id="test-e2e-1",
                    coin="BTC",
                    direction="LONG",
                    trigger_price=50000.0,
                    trigger_type="ABOVE",
                    stop_loss_pct=0.02,
                    take_profit_pct=0.015,
                    position_size_usd=100.0,
                    strategy_id="e2e-test",
                    reasoning="E2E test condition",
                    valid_until=datetime.now() + timedelta(minutes=5),
                )
                system.inject_condition(condition)

                assert len(system.sniper.active_conditions) == 1

                # Price below trigger - no position
                system.inject_price("BTC", 49999.0)
                assert len(system.sniper.open_positions) == 0

                # Price above trigger - should open position
                system.inject_price("BTC", 50001.0)
                assert len(system.sniper.open_positions) == 1
                assert len(system.sniper.active_conditions) == 0  # Consumed

                await system.stop()

        asyncio.run(run())

    def test_stop_loss(self):
        """Test that stop-loss triggers correctly."""
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                system = TradingSystem(
                    test_mode=True,
                    coins=["BTC"],
                    db_path=f"{tmp}/test.db",
                    state_path=f"{tmp}/state.json"
                )
                await system.start_components()

                # Create condition with 2% stop loss
                condition = TradeCondition(
                    id="test-sl-1",
                    coin="BTC",
                    direction="LONG",
                    trigger_price=50000.0,
                    trigger_type="ABOVE",
                    stop_loss_pct=0.02,      # 2% = $49000 stop
                    take_profit_pct=0.10,    # Wide TP
                    position_size_usd=100.0,
                    strategy_id="e2e-test",
                    reasoning="Stop loss test",
                    valid_until=datetime.now() + timedelta(minutes=5),
                )
                system.inject_condition(condition)

                # Trigger entry at 50000
                system.inject_price("BTC", 50000.0)
                assert len(system.sniper.open_positions) == 1

                # Price drops to stop loss (50000 * 0.98 = 49000)
                system.inject_price("BTC", 48900.0)
                assert len(system.sniper.open_positions) == 0  # Closed

                # Check journal recorded exit
                entries = system.journal.get_recent(hours=1)
                exit_entry = next((e for e in entries if e.exit_reason == "stop_loss"), None)
                assert exit_entry is not None
                assert exit_entry.pnl_usd < 0  # Loss

                await system.stop()

        asyncio.run(run())

    def test_take_profit(self):
        """Test that take-profit triggers correctly."""
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                system = TradingSystem(
                    test_mode=True,
                    coins=["BTC"],
                    db_path=f"{tmp}/test.db",
                    state_path=f"{tmp}/state.json"
                )
                await system.start_components()

                # Create condition with 1.5% take profit
                condition = TradeCondition(
                    id="test-tp-1",
                    coin="BTC",
                    direction="LONG",
                    trigger_price=50000.0,
                    trigger_type="ABOVE",
                    stop_loss_pct=0.10,      # Wide stop
                    take_profit_pct=0.015,   # 1.5% = $50750 TP
                    position_size_usd=100.0,
                    strategy_id="e2e-test",
                    reasoning="Take profit test",
                    valid_until=datetime.now() + timedelta(minutes=5),
                )
                system.inject_condition(condition)

                # Trigger entry at 50000
                system.inject_price("BTC", 50000.0)
                assert len(system.sniper.open_positions) == 1

                # Price rises to take profit (50000 * 1.015 = 50750)
                system.inject_price("BTC", 50800.0)
                assert len(system.sniper.open_positions) == 0  # Closed

                # Check journal recorded profit
                entries = system.journal.get_recent(hours=1)
                exit_entry = next((e for e in entries if e.exit_reason == "take_profit"), None)
                assert exit_entry is not None
                assert exit_entry.pnl_usd > 0  # Profit

                await system.stop()

        asyncio.run(run())

    def test_full_trade_cycle_journaled(self):
        """Test complete trade cycle is recorded in journal."""
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                system = TradingSystem(
                    test_mode=True,
                    coins=["BTC"],
                    db_path=f"{tmp}/test.db",
                    state_path=f"{tmp}/state.json"
                )
                await system.start_components()

                initial_balance = system.sniper.balance

                # Create and trigger condition
                condition = TradeCondition(
                    id="test-journal-1",
                    coin="BTC",
                    direction="LONG",
                    trigger_price=50000.0,
                    trigger_type="ABOVE",
                    stop_loss_pct=0.02,
                    take_profit_pct=0.01,  # 1% TP for quick exit
                    position_size_usd=100.0,
                    strategy_id="journal-test",
                    reasoning="Journal integration test",
                    valid_until=datetime.now() + timedelta(minutes=5),
                )
                system.inject_condition(condition)

                # Entry
                system.inject_price("BTC", 50100.0)
                assert len(system.sniper.open_positions) == 1

                # Give async write time
                time.sleep(0.5)

                # Exit (TP at 50100 * 1.01 = 50601)
                system.inject_price("BTC", 50700.0)
                assert len(system.sniper.open_positions) == 0

                # Give async write time
                time.sleep(0.5)

                # Verify journal
                stats = system.journal.get_stats()
                assert stats["total_trades"] >= 1

                # Verify balance updated
                assert system.sniper.balance != initial_balance

                await system.stop()

        asyncio.run(run())


class TestPerformance:
    """Performance tests."""

    def test_tick_processing_speed(self):
        """Test that tick processing is fast enough."""
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                system = TradingSystem(
                    test_mode=True,
                    coins=["BTC"],
                    db_path=f"{tmp}/test.db",
                    state_path=f"{tmp}/state.json"
                )
                await system.start_components()

                # Add some conditions to make it realistic
                for i in range(5):
                    condition = TradeCondition(
                        id=f"perf-{i}",
                        coin="BTC",
                        direction="LONG",
                        trigger_price=100000.0,  # Won't trigger
                        trigger_type="ABOVE",
                        stop_loss_pct=0.02,
                        take_profit_pct=0.015,
                        position_size_usd=100.0,
                        strategy_id="perf-test",
                        reasoning="Performance test",
                        valid_until=datetime.now() + timedelta(hours=1),
                    )
                    system.inject_condition(condition)

                # Process 10000 ticks
                start = time.perf_counter()
                for i in range(10000):
                    system.inject_price("BTC", 50000.0 + i * 0.01)
                elapsed = time.perf_counter() - start

                per_tick_ms = (elapsed / 10000) * 1000
                ticks_per_second = 10000 / elapsed

                print(f"\nPerformance: {10000} ticks in {elapsed:.3f}s")
                print(f"Per tick: {per_tick_ms:.4f}ms")
                print(f"Ticks/second: {ticks_per_second:.0f}")

                # Target: < 0.1ms per tick (> 10000 ticks/second)
                assert per_tick_ms < 0.1, f"Tick processing too slow: {per_tick_ms:.4f}ms"

                await system.stop()

        asyncio.run(run())


class TestStatePersistence:
    """Test state persistence and recovery."""

    def test_state_save_and_load(self):
        """Test that state survives restart."""
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                state_path = f"{tmp}/sniper_state.json"
                db_path = f"{tmp}/test.db"

                # First run - create position
                system1 = TradingSystem(
                    test_mode=True,
                    coins=["BTC"],
                    db_path=db_path,
                    state_path=state_path
                )
                await system1.start_components()

                condition = TradeCondition(
                    id="persist-1",
                    coin="BTC",
                    direction="LONG",
                    trigger_price=50000.0,
                    trigger_type="ABOVE",
                    stop_loss_pct=0.02,
                    take_profit_pct=0.10,  # Wide TP
                    position_size_usd=100.0,
                    strategy_id="persist-test",
                    reasoning="Persistence test",
                    valid_until=datetime.now() + timedelta(hours=1),
                )
                system1.inject_condition(condition)
                system1.inject_price("BTC", 50100.0)

                assert len(system1.sniper.open_positions) == 1
                original_balance = system1.sniper.balance

                # Save and stop
                system1.sniper.save_state()
                await system1.stop()

                # Second run - load state
                system2 = TradingSystem(
                    test_mode=True,
                    coins=["BTC"],
                    db_path=db_path,
                    state_path=state_path
                )
                await system2.start_components()

                # Verify state restored
                assert len(system2.sniper.open_positions) == 1
                assert system2.sniper.balance == original_balance

                await system2.stop()

        asyncio.run(run())


class TestGetStatus:
    """Test status reporting."""

    def test_get_status(self):
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                system = TradingSystem(
                    test_mode=True,
                    coins=["BTC", "ETH"],
                    db_path=f"{tmp}/test.db",
                    state_path=f"{tmp}/state.json"
                )
                await system.start_components()

                # Inject some activity
                system.inject_price("BTC", 50000.0)
                system.inject_price("ETH", 3000.0)

                status = system.get_status()

                assert "running" in status
                assert "health" in status
                assert "sniper" in status
                assert "feed" in status
                assert "journal" in status

                assert status["health"]["tick_count"] == 2

                await system.stop()

        asyncio.run(run())


def run_tests():
    """Run all integration tests."""
    import traceback

    test_classes = [
        TestHealthMonitor,
        TestTradingSystemInit,
        TestTradingSystemComponents,
        TestEndToEnd,
        TestPerformance,
        TestStatePersistence,
        TestGetStatus,
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
                    method()
                    print(f"  ✓ {method_name}")
                    passed += 1
                except Exception as e:
                    print(f"  ✗ {method_name}: {e}")
                    traceback.print_exc()
                    failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*50}")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
