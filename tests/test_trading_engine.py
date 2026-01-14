"""Tests for the trading engine module."""

import os
import tempfile
import pytest

from src.trading_engine import TradingEngine, TradeResult
from src.database import Database
from src.risk_manager import RiskManager


class TestTradingEngineInit:
    """Test TradingEngine initialization."""

    def setup_method(self):
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_init_default(self):
        """Test default initialization."""
        engine = TradingEngine(db=self.db)
        assert engine.db is not None
        assert engine.risk_manager is not None

    def test_init_with_risk_manager(self):
        """Test initialization with custom risk manager."""
        rm = RiskManager(db=self.db)
        engine = TradingEngine(db=self.db, risk_manager=rm)
        assert engine.risk_manager is rm


class TestExecuteBuy:
    """Test execute_buy functionality."""

    def setup_method(self):
        """Create a temporary database with market data."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)
        self.engine = TradingEngine(db=self.db)

        # Add market data for bitcoin
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO market_data (coin, price_usd, change_24h, last_updated)
                VALUES ('bitcoin', 95000.0, 2.5, datetime('now'))
            """)
            conn.commit()

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_execute_buy_success(self):
        """Test successful buy execution."""
        result = self.engine.execute_buy('bitcoin', 20.0, 'Test trade')

        assert result.success is True
        assert result.trade_id is not None
        assert 'Opened trade' in result.message

    def test_execute_buy_creates_open_trade(self):
        """Test that buy creates entry in open_trades."""
        result = self.engine.execute_buy('bitcoin', 20.0, 'Test trade')

        trades = self.engine.get_open_trades()
        assert len(trades) == 1
        assert trades[0]['coin_name'] == 'bitcoin'
        assert trades[0]['size_usd'] == 20.0
        assert trades[0]['entry_price'] == 95000.0

    def test_execute_buy_updates_account(self):
        """Test that buy updates account state."""
        initial_state = self.db.get_account_state()
        initial_available = initial_state['available_balance']

        self.engine.execute_buy('bitcoin', 20.0, 'Test trade')

        new_state = self.db.get_account_state()
        assert new_state['available_balance'] == initial_available - 20.0
        assert new_state['in_positions'] == 20.0

    def test_execute_buy_calculates_stop_loss(self):
        """Test that stop loss is calculated correctly."""
        self.engine.execute_buy('bitcoin', 20.0, 'Test trade')

        trades = self.engine.get_open_trades()
        # Stop loss should be 10% below entry (95000 * 0.9 = 85500)
        assert trades[0]['stop_loss_price'] == 85500.0

    def test_execute_buy_calculates_take_profit(self):
        """Test that take profit is calculated correctly."""
        self.engine.execute_buy('bitcoin', 20.0, 'Test trade')

        trades = self.engine.get_open_trades()
        # Take profit should yield $1 profit on $20 = 5% gain
        # 95000 * 1.05 = 99750
        assert trades[0]['take_profit_price'] == 99750.0

    def test_execute_buy_no_market_data_fails(self):
        """Test that buy fails without market data."""
        result = self.engine.execute_buy('dogecoin', 20.0, 'Test trade')

        assert result.success is False
        assert 'No market data' in result.message

    def test_execute_buy_exceeds_limit_fails(self):
        """Test that buy fails if it exceeds risk limits."""
        result = self.engine.execute_buy('bitcoin', 50.0, 'Too large trade')

        assert result.success is False
        assert 'exceeds max per trade' in result.message

    def test_execute_buy_logs_activity(self):
        """Test that buy is logged to activity_log."""
        self.engine.execute_buy('bitcoin', 20.0, 'Test trade')

        activities = self.db.get_recent_activity(5)
        trade_activities = [a for a in activities if a['activity_type'] == 'trade_opened']
        assert len(trade_activities) > 0


class TestCloseTrade:
    """Test close_trade functionality."""

    def setup_method(self):
        """Create a temporary database with an open trade."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)
        self.engine = TradingEngine(db=self.db)

        # Add market data
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO market_data (coin, price_usd, change_24h, last_updated)
                VALUES ('bitcoin', 95000.0, 2.5, datetime('now'))
            """)
            conn.commit()

        # Open a trade
        self.engine.execute_buy('bitcoin', 20.0, 'Test trade')

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_close_trade_success(self):
        """Test successful trade close."""
        trades = self.engine.get_open_trades()
        trade_id = trades[0]['id']

        result = self.engine.close_trade(trade_id, 'manual_close')

        assert result.success is True
        assert result.trade_id == trade_id

    def test_close_trade_removes_from_open(self):
        """Test that close removes trade from open_trades."""
        trades = self.engine.get_open_trades()
        trade_id = trades[0]['id']

        self.engine.close_trade(trade_id, 'manual_close')

        open_trades = self.engine.get_open_trades()
        assert len(open_trades) == 0

    def test_close_trade_adds_to_closed(self):
        """Test that close adds trade to closed_trades."""
        trades = self.engine.get_open_trades()
        trade_id = trades[0]['id']

        self.engine.close_trade(trade_id, 'manual_close')

        closed_trades = self.engine.get_closed_trades()
        assert len(closed_trades) == 1
        assert closed_trades[0]['coin_name'] == 'bitcoin'
        assert closed_trades[0]['exit_reason'] == 'manual_close'

    def test_close_trade_calculates_pnl(self):
        """Test that P&L is calculated correctly."""
        trades = self.engine.get_open_trades()
        trade_id = trades[0]['id']

        # Update price to show profit
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE market_data SET price_usd = 96000.0 WHERE coin = 'bitcoin'
            """)
            conn.commit()

        self.engine.close_trade(trade_id, 'take_profit')

        closed_trades = self.engine.get_closed_trades()
        # 1.05% gain on $20 = ~$0.21
        assert closed_trades[0]['pnl_usd'] > 0
        assert closed_trades[0]['exit_price'] == 96000.0

    def test_close_trade_updates_account(self):
        """Test that account is updated correctly."""
        trades = self.engine.get_open_trades()
        trade_id = trades[0]['id']

        self.engine.close_trade(trade_id, 'manual_close')

        state = self.db.get_account_state()
        # Position should be closed, in_positions back to 0
        assert state['in_positions'] == 0
        # Trade count should increment
        assert state['trade_count_today'] == 1

    def test_close_nonexistent_trade_fails(self):
        """Test that closing non-existent trade fails."""
        result = self.engine.close_trade(9999, 'manual_close')

        assert result.success is False
        assert 'not found' in result.message


class TestUpdatePositions:
    """Test update_positions functionality."""

    def setup_method(self):
        """Create a temporary database with an open trade."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)
        self.engine = TradingEngine(db=self.db)

        # Add market data
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO market_data (coin, price_usd, change_24h, last_updated)
                VALUES ('bitcoin', 95000.0, 2.5, datetime('now'))
            """)
            conn.commit()

        # Open a trade
        self.engine.execute_buy('bitcoin', 20.0, 'Test trade')

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_update_positions_updates_price(self):
        """Test that position prices are updated."""
        # Change price
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE market_data SET price_usd = 96000.0 WHERE coin = 'bitcoin'
            """)
            conn.commit()

        self.engine.update_positions()

        trades = self.engine.get_open_trades()
        assert trades[0]['current_price'] == 96000.0

    def test_update_positions_calculates_unrealized_pnl(self):
        """Test that unrealized P&L is calculated."""
        # Change price to +1%
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE market_data SET price_usd = 95950.0 WHERE coin = 'bitcoin'
            """)
            conn.commit()

        self.engine.update_positions()

        trades = self.engine.get_open_trades()
        assert trades[0]['unrealized_pnl'] > 0
        assert trades[0]['unrealized_pnl_pct'] > 0

    def test_update_positions_triggers_stop_loss(self):
        """Test that stop loss is triggered."""
        # Drop price by 10%
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE market_data SET price_usd = 85500.0 WHERE coin = 'bitcoin'
            """)
            conn.commit()

        closed = self.engine.update_positions()

        assert len(closed) == 1
        assert closed[0]['reason'] == 'stop_loss'
        assert closed[0]['pnl_usd'] < 0

    def test_update_positions_triggers_take_profit(self):
        """Test that take profit is triggered."""
        # Raise price by 5% to hit $1 profit target
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE market_data SET price_usd = 99750.0 WHERE coin = 'bitcoin'
            """)
            conn.commit()

        closed = self.engine.update_positions()

        assert len(closed) == 1
        assert closed[0]['reason'] == 'take_profit'
        assert closed[0]['pnl_usd'] >= 1.0

    def test_update_positions_no_trigger_in_range(self):
        """Test that positions stay open when price is in range."""
        # Small price change
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE market_data SET price_usd = 95500.0 WHERE coin = 'bitcoin'
            """)
            conn.commit()

        closed = self.engine.update_positions()

        assert len(closed) == 0
        assert len(self.engine.get_open_trades()) == 1


class TestGetCurrentPrice:
    """Test get_current_price functionality."""

    def setup_method(self):
        """Create a temporary database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)
        self.engine = TradingEngine(db=self.db)

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_get_price_exists(self):
        """Test getting price that exists."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO market_data (coin, price_usd, change_24h, last_updated)
                VALUES ('bitcoin', 95000.0, 2.5, datetime('now'))
            """)
            conn.commit()

        price = self.engine.get_current_price('bitcoin')
        assert price == 95000.0

    def test_get_price_not_exists(self):
        """Test getting price that doesn't exist."""
        price = self.engine.get_current_price('nonexistent')
        assert price is None


class TestTradeResult:
    """Test TradeResult dataclass."""

    def test_trade_result_success(self):
        """Test successful trade result."""
        result = TradeResult(success=True, trade_id=1, message="Trade opened")
        assert result.success is True
        assert result.trade_id == 1
        assert result.message == "Trade opened"

    def test_trade_result_failure(self):
        """Test failed trade result."""
        result = TradeResult(success=False, trade_id=None, message="No market data")
        assert result.success is False
        assert result.trade_id is None


def test_trading_engine_import():
    """Test that TradingEngine can be imported."""
    from src.trading_engine import TradingEngine, TradeResult
    assert TradingEngine is not None
    assert TradeResult is not None
