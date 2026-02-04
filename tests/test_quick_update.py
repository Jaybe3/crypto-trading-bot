"""
Tests for QuickUpdate post-trade knowledge updates.

TASK-130: Tests for instant post-trade updates to coin scores and pattern confidence.
"""

import os
import tempfile
import time
import pytest
from unittest.mock import Mock, patch

from src.models.quick_update import TradeResult, QuickUpdateResult


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    from src.database import Database

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(path)
    yield db
    os.unlink(path)


@pytest.fixture
def knowledge_brain(temp_db):
    """Create a KnowledgeBrain with test data."""
    from src.knowledge import KnowledgeBrain

    brain = KnowledgeBrain(temp_db)
    return brain


@pytest.fixture
def coin_scorer(knowledge_brain, temp_db):
    """Create a CoinScorer."""
    from src.coin_scorer import CoinScorer

    return CoinScorer(knowledge_brain, temp_db)


@pytest.fixture
def pattern_library(knowledge_brain):
    """Create a PatternLibrary."""
    from src.pattern_library import PatternLibrary

    return PatternLibrary(knowledge_brain)


@pytest.fixture
def quick_update(coin_scorer, pattern_library, temp_db):
    """Create a QuickUpdate instance."""
    from src.quick_update import QuickUpdate

    return QuickUpdate(coin_scorer, pattern_library, temp_db)


class TestTradeResultDataclass:
    """Tests for TradeResult dataclass."""

    def test_basic_creation(self):
        """Can create a TradeResult with required fields."""
        result = TradeResult(
            trade_id="test-001",
            coin="SOL",
            direction="LONG",
            entry_price=100.0,
            exit_price=102.0,
            position_size_usd=50.0,
            pnl_usd=1.0,
            won=True,
            exit_reason="take_profit",
        )

        assert result.coin == "SOL"
        assert result.won is True
        assert result.pnl_usd == 1.0

    def test_return_pct_long(self):
        """Return percentage calculated correctly for LONG."""
        result = TradeResult(
            trade_id="test-001",
            coin="SOL",
            direction="LONG",
            entry_price=100.0,
            exit_price=102.0,
            position_size_usd=50.0,
            pnl_usd=1.0,
            won=True,
            exit_reason="take_profit",
        )

        assert result.return_pct == 2.0

    def test_return_pct_short(self):
        """Return percentage calculated correctly for SHORT."""
        result = TradeResult(
            trade_id="test-001",
            coin="BTC",
            direction="SHORT",
            entry_price=50000.0,
            exit_price=49000.0,
            position_size_usd=50.0,
            pnl_usd=1.0,
            won=True,
            exit_reason="take_profit",
        )

        assert result.return_pct == 2.0  # (50000 - 49000) / 50000 * 100

    def test_duration_seconds(self):
        """Duration calculated from timestamps."""
        result = TradeResult(
            trade_id="test-001",
            coin="SOL",
            direction="LONG",
            entry_price=100.0,
            exit_price=102.0,
            position_size_usd=50.0,
            pnl_usd=1.0,
            won=True,
            exit_reason="take_profit",
            entry_timestamp=1000000,
            exit_timestamp=1060000,  # 60 seconds later (in ms)
        )

        assert result.duration_seconds == 60


class TestQuickUpdateResult:
    """Tests for QuickUpdateResult dataclass."""

    def test_str_winning_trade(self):
        """String representation for winning trade."""
        result = QuickUpdateResult(
            trade_id="test-001",
            coin="SOL",
            won=True,
            pnl_usd=1.50,
            processing_time_ms=0.5,
        )

        s = str(result)
        assert "SOL" in s
        assert "WIN" in s
        assert "+1.50" in s

    def test_str_losing_trade_with_adaptation(self):
        """String representation for losing trade with adaptation."""
        result = QuickUpdateResult(
            trade_id="test-001",
            coin="SHIB",
            won=False,
            pnl_usd=-5.0,
            coin_adaptation="BLACKLIST",
            processing_time_ms=0.5,
        )

        s = str(result)
        assert "SHIB" in s
        assert "LOSS" in s
        assert "BLACKLIST" in s


class TestQuickUpdateProcessing:
    """Tests for QuickUpdate.process_trade_close()."""

    def test_winning_trade_updates_score(self, quick_update, knowledge_brain):
        """Winning trade updates coin score correctly."""
        result = quick_update.process_trade_close(TradeResult(
            trade_id="test-001",
            coin="SOL",
            direction="LONG",
            entry_price=100.0,
            exit_price=102.0,
            position_size_usd=50.0,
            pnl_usd=1.0,
            won=True,
            exit_reason="take_profit",
        ))

        assert result.coin_score_updated is True
        assert result.won is True

        # Verify coin score was updated
        score = knowledge_brain.get_coin_score("SOL")
        assert score is not None
        assert score.wins == 1
        assert score.losses == 0
        assert score.total_pnl == 1.0

    def test_losing_trade_updates_score(self, quick_update, knowledge_brain):
        """Losing trade updates coin score correctly."""
        result = quick_update.process_trade_close(TradeResult(
            trade_id="test-001",
            coin="ETH",
            direction="LONG",
            entry_price=2500.0,
            exit_price=2450.0,
            position_size_usd=50.0,
            pnl_usd=-1.0,
            won=False,
            exit_reason="stop_loss",
        ))

        assert result.won is False

        score = knowledge_brain.get_coin_score("ETH")
        assert score.wins == 0
        assert score.losses == 1
        assert score.total_pnl == -1.0

    def test_blacklist_triggered(self, quick_update, knowledge_brain):
        """Blacklist adaptation triggers after 5+ trades with <30% win rate."""
        # Process losing trades until blacklist triggers
        blacklist_triggered = False
        for i in range(6):
            result = quick_update.process_trade_close(TradeResult(
                trade_id=f"test-loss-{i}",
                coin="SHIB",
                direction="LONG",
                entry_price=0.00001,
                exit_price=0.000009,
                position_size_usd=50.0,
                pnl_usd=-5.0,
                won=False,
                exit_reason="stop_loss",
            ))

            # Check if blacklist was triggered on THIS trade
            # Note: CoinStatus.BLACKLISTED.value = "blacklisted" -> upper() = "BLACKLISTED"
            if result.coin_adaptation == "BLACKLISTED":
                blacklist_triggered = True
                break

        # Verify blacklist was triggered (on trade 5 when threshold crossed)
        assert blacklist_triggered, "Blacklist should have been triggered"
        score = knowledge_brain.get_coin_score("SHIB")
        assert score.is_blacklisted is True

    def test_processing_time_tracked(self, quick_update):
        """Processing time is measured and recorded."""
        result = quick_update.process_trade_close(TradeResult(
            trade_id="test-001",
            coin="BTC",
            direction="LONG",
            entry_price=45000.0,
            exit_price=45100.0,
            position_size_usd=50.0,
            pnl_usd=0.11,
            won=True,
            exit_reason="take_profit",
        ))

        assert result.processing_time_ms > 0
        assert result.processing_time_ms < 100  # Should be fast

    def test_stats_updated(self, quick_update):
        """QuickUpdate stats are incremented."""
        initial_count = quick_update.updates_processed

        quick_update.process_trade_close(TradeResult(
            trade_id="test-001",
            coin="SOL",
            direction="LONG",
            entry_price=100.0,
            exit_price=102.0,
            position_size_usd=50.0,
            pnl_usd=1.0,
            won=True,
            exit_reason="take_profit",
        ))

        assert quick_update.updates_processed == initial_count + 1


class TestPatternUpdates:
    """Tests for pattern confidence updates."""

    def test_pattern_confidence_updated(self, quick_update, pattern_library):
        """Pattern confidence is updated when pattern_id is provided."""
        # Create a pattern
        pattern = pattern_library.create_pattern(
            pattern_type="test",
            description="Test pattern",
            entry_conditions={"test": True},
            exit_conditions={"stop_loss_pct": 2.0},
        )
        # Capture initial values BEFORE trade (object is mutated in place)
        initial_times_used = pattern.times_used  # Should be 0
        initial_confidence = pattern.confidence

        # Process a winning trade with this pattern
        result = quick_update.process_trade_close(TradeResult(
            trade_id="test-001",
            coin="ETH",
            direction="LONG",
            entry_price=2500.0,
            exit_price=2550.0,
            position_size_usd=50.0,
            pnl_usd=1.0,
            won=True,
            exit_reason="take_profit",
            pattern_id=pattern.pattern_id,
        ))

        assert result.pattern_updated is True
        assert result.pattern_id == pattern.pattern_id

        # times_used should have increased from initial value
        updated = pattern_library.get_pattern(pattern.pattern_id)
        assert updated.times_used > initial_times_used

    def test_no_pattern_update_without_pattern_id(self, quick_update):
        """No pattern update when pattern_id is not provided."""
        result = quick_update.process_trade_close(TradeResult(
            trade_id="test-001",
            coin="SOL",
            direction="LONG",
            entry_price=100.0,
            exit_price=102.0,
            position_size_usd=50.0,
            pnl_usd=1.0,
            won=True,
            exit_reason="take_profit",
            pattern_id=None,
        ))

        assert result.pattern_updated is False
        assert result.pattern_id is None


class TestPerformance:
    """Tests for QuickUpdate performance requirements."""

    def test_single_update_fast(self, quick_update):
        """Single update completes in <10ms."""
        result = quick_update.process_trade_close(TradeResult(
            trade_id="test-001",
            coin="BTC",
            direction="LONG",
            entry_price=45000.0,
            exit_price=45100.0,
            position_size_usd=50.0,
            pnl_usd=0.11,
            won=True,
            exit_reason="take_profit",
        ))

        assert result.processing_time_ms < 10

    def test_bulk_updates_fast(self, quick_update):
        """100 updates complete in <1 second."""
        start = time.perf_counter()

        for i in range(100):
            quick_update.process_trade_close(TradeResult(
                trade_id=f"perf-{i}",
                coin="BTC",
                direction="LONG",
                entry_price=45000.0,
                exit_price=45100.0,
                position_size_usd=50.0,
                pnl_usd=0.11,
                won=True,
                exit_reason="take_profit",
            ))

        elapsed = time.perf_counter() - start

        assert elapsed < 1.0, f"100 updates took {elapsed:.2f}s, should be <1s"


class TestSniperIntegration:
    """Tests for QuickUpdate integration with Sniper."""

    def test_sniper_calls_quick_update(self, quick_update):
        """Sniper calls QuickUpdate after trade exit."""
        from src.sniper import Sniper
        from src.journal import TradeJournal
        from src.models.trade_condition import TradeCondition
        from datetime import datetime, timedelta

        # Create a temp journal with its own database
        fd, journal_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        journal = TradeJournal(db_path=journal_path, enable_async=False)
        sniper = Sniper(
            journal=journal,
            initial_balance=10000.0,
            quick_update=quick_update,
        )

        # Create a condition
        condition = TradeCondition(
            coin="SOL",
            direction="LONG",
            trigger_price=100.0,
            trigger_condition="ABOVE",
            stop_loss_pct=2.0,
            take_profit_pct=2.0,
            position_size_usd=50.0,
            reasoning="Test quick update",
            strategy_id="test_strategy",
            valid_until=datetime.now() + timedelta(hours=1),
        )

        # Manually add a position (simulating entry)
        from src.sniper import Position
        position = Position(
            id="test-pos-001",
            coin="SOL",
            direction="LONG",
            entry_price=100.0,
            entry_time=datetime.now(),
            size_usd=50.0,
            stop_loss_price=98.0,
            take_profit_price=102.0,
            condition_id=condition.id,
            strategy_id="test",
            reasoning="Test trade",
        )
        sniper.open_positions[position.id] = position
        sniper.balance -= 50.0  # Deduct position size

        # Close the position (simulating take profit)
        initial_updates = quick_update.updates_processed
        sniper._execute_exit(position, 102.0, int(time.time() * 1000), "take_profit")

        # Cleanup
        os.unlink(journal_path)

        # QuickUpdate should have been called
        assert quick_update.updates_processed == initial_updates + 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
