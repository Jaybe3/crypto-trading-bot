"""
Tests for Trade Journal.
"""

import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.journal import (
    TradeJournal, JournalEntry, JournalDatabase, MarketContext, AsyncWriteQueue
)


# =============================================================================
# Mock Position for testing
# =============================================================================

class MockPosition:
    """Mock Position object for testing."""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 'pos-123')
        self.coin = kwargs.get('coin', 'BTC')
        self.direction = kwargs.get('direction', 'LONG')
        self.entry_price = kwargs.get('entry_price', 42000.0)
        self.entry_time = kwargs.get('entry_time', datetime.now())
        self.size_usd = kwargs.get('size_usd', 100.0)
        self.stop_loss_price = kwargs.get('stop_loss_price', 41160.0)
        self.take_profit_price = kwargs.get('take_profit_price', 42630.0)
        self.condition_id = kwargs.get('condition_id', 'cond-123')
        self.strategy_id = kwargs.get('strategy_id', 'test-strategy')
        self.reasoning = kwargs.get('reasoning', 'Test trade')


# =============================================================================
# Test Data Classes
# =============================================================================

class TestMarketContext:
    """Test MarketContext data class."""

    def test_creation(self):
        ctx = MarketContext(
            regime="trending",
            volatility=0.02,
            btc_trend="up",
            btc_price=78000.0
        )
        assert ctx.regime == "trending"
        assert ctx.volatility == 0.02
        assert ctx.btc_trend == "up"

    def test_defaults(self):
        ctx = MarketContext()
        assert ctx.regime is None
        assert ctx.volatility is None

    def test_to_dict(self):
        ctx = MarketContext(regime="volatile", volatility=0.05)
        d = ctx.to_dict()
        assert d['regime'] == "volatile"
        assert d['volatility'] == 0.05

    def test_from_dict(self):
        d = {'regime': 'ranging', 'btc_price': 80000.0}
        ctx = MarketContext.from_dict(d)
        assert ctx.regime == "ranging"
        assert ctx.btc_price == 80000.0


class TestJournalEntry:
    """Test JournalEntry data class."""

    def test_creation(self):
        entry = JournalEntry(
            id="j-123",
            position_id="pos-456",
            entry_time=datetime.now(),
            entry_price=42000.0,
            entry_reason="Test entry",
            coin="BTC",
            direction="LONG",
            position_size_usd=100.0,
            stop_loss_price=41160.0,
            take_profit_price=42630.0,
            strategy_id="test",
            condition_id="cond-1",
        )
        assert entry.id == "j-123"
        assert entry.coin == "BTC"
        assert entry.status == "open"

    def test_to_dict(self):
        entry = JournalEntry(
            id="j-123",
            position_id="pos-456",
            entry_time=datetime(2024, 1, 15, 10, 30, 0),
            entry_price=42000.0,
            entry_reason="Test",
            coin="BTC",
            direction="LONG",
            position_size_usd=100.0,
            stop_loss_price=41160.0,
            take_profit_price=42630.0,
            strategy_id="test",
            condition_id="cond-1",
        )
        d = entry.to_dict()
        assert d['id'] == "j-123"
        assert isinstance(d['entry_time'], str)  # Converted to ISO string

    def test_from_dict(self):
        d = {
            'id': "j-789",
            'position_id': "pos-111",
            'entry_time': "2024-01-15T10:30:00",
            'entry_price': 50000.0,
            'entry_reason': "Test",
            'coin': "ETH",
            'direction': "SHORT",
            'position_size_usd': 200.0,
            'stop_loss_price': 51000.0,
            'take_profit_price': 49000.0,
            'strategy_id': "test",
            'condition_id': "cond-2",
        }
        entry = JournalEntry.from_dict(d)
        assert entry.id == "j-789"
        assert entry.coin == "ETH"
        assert isinstance(entry.entry_time, datetime)

    def test_is_winner(self):
        entry = JournalEntry(
            id="j-1", position_id="p-1", entry_time=datetime.now(),
            entry_price=100, entry_reason="", coin="BTC", direction="LONG",
            position_size_usd=100, stop_loss_price=90, take_profit_price=110,
            strategy_id="s", condition_id="c",
            pnl_usd=5.0
        )
        assert entry.is_winner()
        assert not entry.is_loser()

    def test_is_loser(self):
        entry = JournalEntry(
            id="j-1", position_id="p-1", entry_time=datetime.now(),
            entry_price=100, entry_reason="", coin="BTC", direction="LONG",
            position_size_usd=100, stop_loss_price=90, take_profit_price=110,
            strategy_id="s", condition_id="c",
            pnl_usd=-3.0
        )
        assert entry.is_loser()
        assert not entry.is_winner()


# =============================================================================
# Test Database
# =============================================================================

class TestJournalDatabase:
    """Test JournalDatabase operations."""

    def test_create_and_insert(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            db = JournalDatabase(str(db_path))

            entry = JournalEntry(
                id="j-test-1",
                position_id="pos-1",
                entry_time=datetime.now(),
                entry_price=42000.0,
                entry_reason="Test",
                coin="BTC",
                direction="LONG",
                position_size_usd=100.0,
                stop_loss_price=41000.0,
                take_profit_price=43000.0,
                strategy_id="test",
                condition_id="c-1",
            )

            db.insert(entry)

            # Verify it was inserted
            result = db.get("j-test-1")
            assert result is not None
            assert result.coin == "BTC"

    def test_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            db = JournalDatabase(str(db_path))

            entry = JournalEntry(
                id="j-test-2",
                position_id="pos-2",
                entry_time=datetime.now(),
                entry_price=42000.0,
                entry_reason="Test",
                coin="BTC",
                direction="LONG",
                position_size_usd=100.0,
                stop_loss_price=41000.0,
                take_profit_price=43000.0,
                strategy_id="test",
                condition_id="c-1",
            )
            db.insert(entry)

            # Update with exit info
            db.update("j-test-2", {
                'exit_price': 42500.0,
                'exit_reason': 'take_profit',
                'pnl_usd': 1.19,
                'status': 'closed',
            })

            result = db.get("j-test-2")
            assert result.exit_price == 42500.0
            assert result.exit_reason == "take_profit"
            assert result.status == "closed"

    def test_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            db = JournalDatabase(str(db_path))

            # Insert multiple entries
            for i, coin in enumerate(['BTC', 'ETH', 'BTC', 'SOL']):
                entry = JournalEntry(
                    id=f"j-{i}",
                    position_id=f"pos-{i}",
                    entry_time=datetime.now(),
                    entry_price=42000.0,
                    entry_reason="Test",
                    coin=coin,
                    direction="LONG",
                    position_size_usd=100.0,
                    stop_loss_price=41000.0,
                    take_profit_price=43000.0,
                    strategy_id="test",
                    condition_id="c-1",
                )
                db.insert(entry)

            # Query BTC only
            btc_entries = db.query(where="coin = ?", params=("BTC",))
            assert len(btc_entries) == 2

    def test_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            db = JournalDatabase(str(db_path))

            for i in range(5):
                entry = JournalEntry(
                    id=f"j-{i}",
                    position_id=f"pos-{i}",
                    entry_time=datetime.now(),
                    entry_price=42000.0,
                    entry_reason="Test",
                    coin="BTC",
                    direction="LONG",
                    position_size_usd=100.0,
                    stop_loss_price=41000.0,
                    take_profit_price=43000.0,
                    strategy_id="test",
                    condition_id="c-1",
                )
                db.insert(entry)

            assert db.count() == 5


# =============================================================================
# Test Trade Journal
# =============================================================================

class TestTradeJournal:
    """Test TradeJournal main class."""

    def test_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            journal = TradeJournal(db_path=str(db_path), enable_async=False)

            assert journal.entry_count() == 0
            assert len(journal.pending_entries) == 0

    def test_record_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            journal = TradeJournal(db_path=str(db_path), enable_async=False)

            position = MockPosition(
                id="pos-test-1",
                coin="BTC",
                entry_price=42000.0,
                direction="LONG",
            )

            timestamp = int(datetime.now().timestamp() * 1000)
            entry_id = journal.record_entry(position, timestamp)

            assert entry_id is not None
            assert "pos-test-1" in journal.pending_entries
            assert journal.entry_count() == 1

    def test_record_entry_with_market_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            journal = TradeJournal(db_path=str(db_path), enable_async=False)

            position = MockPosition(id="pos-ctx-1")
            ctx = MarketContext(
                regime="trending",
                volatility=0.02,
                btc_trend="up",
                btc_price=78000.0
            )

            timestamp = int(datetime.now().timestamp() * 1000)
            entry_id = journal.record_entry(position, timestamp, market_context=ctx)

            entry = journal.get_entry(entry_id)
            assert entry.market_regime == "trending"
            assert entry.volatility == 0.02
            assert entry.btc_trend == "up"

    def test_record_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            journal = TradeJournal(db_path=str(db_path), enable_async=False)

            # Record entry
            position = MockPosition(
                id="pos-exit-1",
                coin="BTC",
                entry_price=42000.0,
                size_usd=100.0,
            )
            entry_timestamp = int(datetime.now().timestamp() * 1000)
            entry_id = journal.record_entry(position, entry_timestamp)

            # Wait a moment
            time.sleep(0.1)

            # Record exit
            exit_timestamp = int(datetime.now().timestamp() * 1000)
            exit_id = journal.record_exit(
                position=position,
                exit_price=42500.0,
                timestamp=exit_timestamp,
                reason="take_profit",
                pnl=1.19
            )

            assert exit_id == entry_id

            # Verify exit recorded
            entry = journal.get_entry(entry_id)
            assert entry.exit_price == 42500.0
            assert entry.exit_reason == "take_profit"
            assert entry.pnl_usd == 1.19
            assert entry.status == "closed"
            assert entry.duration_seconds >= 0

    def test_timing_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            journal = TradeJournal(db_path=str(db_path), enable_async=False)

            position = MockPosition(id="pos-time-1")
            now = datetime.now()
            timestamp = int(now.timestamp() * 1000)

            entry_id = journal.record_entry(position, timestamp)
            entry = journal.get_entry(entry_id)

            assert entry.hour_of_day == now.hour
            assert entry.day_of_week == now.weekday()


class TestJournalQueries:
    """Test journal query methods."""

    def _setup_journal_with_data(self, tmp_dir) -> TradeJournal:
        """Create a journal with test data."""
        db_path = Path(tmp_dir) / "test.db"
        journal = TradeJournal(db_path=str(db_path), enable_async=False)

        # Insert several trades
        trades = [
            {'coin': 'BTC', 'pnl': 5.0, 'reason': 'take_profit', 'strategy': 's1'},
            {'coin': 'BTC', 'pnl': -2.0, 'reason': 'stop_loss', 'strategy': 's1'},
            {'coin': 'ETH', 'pnl': 3.0, 'reason': 'take_profit', 'strategy': 's2'},
            {'coin': 'ETH', 'pnl': -1.0, 'reason': 'stop_loss', 'strategy': 's2'},
            {'coin': 'SOL', 'pnl': 10.0, 'reason': 'take_profit', 'strategy': 's1'},
        ]

        for i, trade in enumerate(trades):
            position = MockPosition(
                id=f"pos-q-{i}",
                coin=trade['coin'],
                entry_price=100.0,
                size_usd=100.0,
                strategy_id=trade['strategy'],
            )

            entry_ts = int(datetime.now().timestamp() * 1000)
            journal.record_entry(position, entry_ts)

            exit_ts = int(datetime.now().timestamp() * 1000)
            journal.record_exit(
                position=position,
                exit_price=100.0 + trade['pnl'],
                timestamp=exit_ts,
                reason=trade['reason'],
                pnl=trade['pnl']
            )

        return journal

    def test_get_by_coin(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self._setup_journal_with_data(tmp)

            btc = journal.get_by_coin('BTC')
            assert len(btc) == 2

            eth = journal.get_by_coin('ETH')
            assert len(eth) == 2

            sol = journal.get_by_coin('SOL')
            assert len(sol) == 1

    def test_get_by_strategy(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self._setup_journal_with_data(tmp)

            s1 = journal.get_by_strategy('s1')
            assert len(s1) == 3

            s2 = journal.get_by_strategy('s2')
            assert len(s2) == 2

    def test_get_by_exit_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self._setup_journal_with_data(tmp)

            tp = journal.get_by_exit_reason('take_profit')
            assert len(tp) == 3

            sl = journal.get_by_exit_reason('stop_loss')
            assert len(sl) == 2

    def test_get_winners(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self._setup_journal_with_data(tmp)

            winners = journal.get_winners()
            assert len(winners) == 3
            # Should be ordered by pnl DESC
            assert winners[0].pnl_usd >= winners[1].pnl_usd

    def test_get_losers(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self._setup_journal_with_data(tmp)

            losers = journal.get_losers()
            assert len(losers) == 2
            # Should be ordered by pnl ASC (most negative first)
            assert losers[0].pnl_usd <= losers[1].pnl_usd


class TestJournalStatistics:
    """Test journal statistics methods."""

    def _setup_journal(self, tmp_dir) -> TradeJournal:
        """Create a journal with predictable data."""
        db_path = Path(tmp_dir) / "test.db"
        journal = TradeJournal(db_path=str(db_path), enable_async=False)

        # 3 wins, 2 losses
        trades = [
            {'coin': 'BTC', 'pnl': 10.0},
            {'coin': 'BTC', 'pnl': 5.0},
            {'coin': 'ETH', 'pnl': -3.0},
            {'coin': 'ETH', 'pnl': 8.0},
            {'coin': 'SOL', 'pnl': -2.0},
        ]

        for i, trade in enumerate(trades):
            position = MockPosition(
                id=f"pos-s-{i}",
                coin=trade['coin'],
                size_usd=100.0,
            )

            entry_ts = int(datetime.now().timestamp() * 1000)
            journal.record_entry(position, entry_ts)

            exit_ts = int(datetime.now().timestamp() * 1000)
            journal.record_exit(
                position=position,
                exit_price=100.0,
                timestamp=exit_ts,
                reason='test',
                pnl=trade['pnl']
            )

        return journal

    def test_get_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self._setup_journal(tmp)

            stats = journal.get_stats()

            assert stats['total_trades'] == 5
            assert stats['wins'] == 3
            assert stats['losses'] == 2
            assert stats['win_rate'] == 60.0
            assert stats['total_pnl'] == 18.0  # 10+5-3+8-2
            assert stats['best_trade'] == 10.0
            assert stats['worst_trade'] == -3.0

    def test_get_stats_filtered_by_coin(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self._setup_journal(tmp)

            btc_stats = journal.get_stats(coin='BTC')

            assert btc_stats['total_trades'] == 2
            assert btc_stats['wins'] == 2
            assert btc_stats['total_pnl'] == 15.0  # 10+5

    def test_get_performance_by_coin(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self._setup_journal(tmp)

            by_coin = journal.get_performance_by_coin()

            assert 'BTC' in by_coin
            assert 'ETH' in by_coin
            assert 'SOL' in by_coin

            assert by_coin['BTC']['trades'] == 2
            assert by_coin['BTC']['win_rate'] == 100.0


class TestAsyncWriteQueue:
    """Test async write queue."""

    def test_queue_operations(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            db = JournalDatabase(str(db_path))
            queue = AsyncWriteQueue(db)

            queue.start()

            # Queue an insert
            entry = JournalEntry(
                id="j-async-1",
                position_id="pos-async-1",
                entry_time=datetime.now(),
                entry_price=42000.0,
                entry_reason="Test",
                coin="BTC",
                direction="LONG",
                position_size_usd=100.0,
                stop_loss_price=41000.0,
                take_profit_price=43000.0,
                strategy_id="test",
                condition_id="c-1",
            )
            queue.enqueue_insert(entry)

            # Wait for processing
            time.sleep(1)

            queue.stop()

            # Verify it was written
            result = db.get("j-async-1")
            assert result is not None
            assert result.coin == "BTC"


class TestMissedProfitCalculation:
    """Test missed profit calculation logic."""

    def test_missed_profit_long_price_went_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            journal = TradeJournal(db_path=str(db_path), enable_async=False)

            # LONG exit at 100, price went to 105 = missed 5%
            missed = journal._calculate_missed_profit("LONG", 100.0, 105.0)
            assert abs(missed - 5.0) < 0.01

    def test_missed_profit_long_price_went_down(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            journal = TradeJournal(db_path=str(db_path), enable_async=False)

            # LONG exit at 100, price went to 95 = dodged -5%
            missed = journal._calculate_missed_profit("LONG", 100.0, 95.0)
            assert abs(missed - (-5.0)) < 0.01

    def test_missed_profit_short_price_went_down(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            journal = TradeJournal(db_path=str(db_path), enable_async=False)

            # SHORT exit at 100, price went to 95 = missed 5% profit
            missed = journal._calculate_missed_profit("SHORT", 100.0, 95.0)
            assert abs(missed - 5.0) < 0.01

    def test_missed_profit_short_price_went_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            journal = TradeJournal(db_path=str(db_path), enable_async=False)

            # SHORT exit at 100, price went to 105 = dodged -5% loss
            missed = journal._calculate_missed_profit("SHORT", 100.0, 105.0)
            assert abs(missed - (-5.0)) < 0.01


def run_tests():
    """Run all tests manually."""
    import traceback

    test_classes = [
        TestMarketContext,
        TestJournalEntry,
        TestJournalDatabase,
        TestTradeJournal,
        TestJournalQueries,
        TestJournalStatistics,
        TestAsyncWriteQueue,
        TestMissedProfitCalculation,
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

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*40}")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
