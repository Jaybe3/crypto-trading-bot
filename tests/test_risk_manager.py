"""Tests for the risk manager module."""

import os
import tempfile
import pytest

from src.risk_manager import (
    RiskManager, TradeValidation, get_risk_summary,
    MAX_TRADE_PERCENT, MAX_EXPOSURE_PERCENT, MIN_BALANCE,
    STOP_LOSS_PERCENT, TAKE_PROFIT_USD
)
from src.database import Database


class TestRiskManagerConstants:
    """Test that risk constants are correctly defined."""

    def test_max_trade_percent(self):
        """Max trade should be 2%."""
        assert MAX_TRADE_PERCENT == 0.02

    def test_max_exposure_percent(self):
        """Max exposure should be 10%."""
        assert MAX_EXPOSURE_PERCENT == 0.10

    def test_min_balance(self):
        """Minimum balance should be $900."""
        assert MIN_BALANCE == 900.0

    def test_stop_loss_percent(self):
        """Stop loss should be 10%."""
        assert STOP_LOSS_PERCENT == 0.10

    def test_take_profit_usd(self):
        """Take profit should be $1."""
        assert TAKE_PROFIT_USD == 1.0


class TestRiskManager:
    """Test cases for the RiskManager class."""

    def setup_method(self):
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)
        self.rm = RiskManager(db=self.db)

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_get_risk_parameters(self):
        """Test that risk parameters are returned correctly."""
        params = self.rm.get_risk_parameters()
        assert params['max_trade_percent'] == 0.02
        assert params['max_exposure_percent'] == 0.10
        assert params['min_balance'] == 900.0
        assert params['stop_loss_percent'] == 0.10
        assert params['take_profit_usd'] == 1.0

    def test_get_account_state(self):
        """Test getting account state."""
        state = self.rm.get_account_state()
        assert state['balance'] == 1000.0
        assert state['available_balance'] == 1000.0

    def test_max_trade_size_fresh_account(self):
        """Test max trade size on fresh $1,000 account."""
        # $1,000 * 2% = $20 max per trade
        max_size = self.rm.calculate_max_trade_size()
        assert max_size == 20.0

    def test_available_for_trading_fresh_account(self):
        """Test available for trading on fresh account."""
        # Above minimum: $1,000 - $900 = $100
        # Max exposure: $1,000 * 10% = $100
        # Available is min($100, $100) = $100
        available = self.rm.get_available_for_trading()
        assert available == 100.0


class TestTradeValidation:
    """Test trade validation against risk rules."""

    def setup_method(self):
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)
        self.rm = RiskManager(db=self.db)

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_valid_trade(self):
        """Test that a valid $20 trade passes."""
        result = self.rm.validate_trade("bitcoin", 20.0)
        assert result.valid is True
        assert result.reason == "Trade passes all risk checks"
        assert result.max_allowed_size == 20.0

    def test_trade_exceeds_max_percent(self):
        """Test that $25 trade is rejected (exceeds 2%)."""
        result = self.rm.validate_trade("bitcoin", 25.0)
        assert result.valid is False
        assert "exceeds max per trade" in result.reason
        assert result.max_allowed_size == 20.0

    def test_trade_at_exact_limit(self):
        """Test that trade exactly at limit passes."""
        result = self.rm.validate_trade("bitcoin", 20.0)
        assert result.valid is True

    def test_small_trade_valid(self):
        """Test that small trades are valid."""
        result = self.rm.validate_trade("bitcoin", 5.0)
        assert result.valid is True

    def test_huge_trade_rejected(self):
        """Test that huge trades are rejected."""
        result = self.rm.validate_trade("bitcoin", 500.0)
        assert result.valid is False

    def test_validation_result_structure(self):
        """Test TradeValidation dataclass structure."""
        result = self.rm.validate_trade("bitcoin", 20.0)
        assert isinstance(result, TradeValidation)
        assert hasattr(result, 'valid')
        assert hasattr(result, 'reason')
        assert hasattr(result, 'max_allowed_size')


class TestStopLossCalculation:
    """Test stop loss price calculations."""

    def setup_method(self):
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)
        self.rm = RiskManager(db=self.db)

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_stop_loss_calculation(self):
        """Test stop loss is 10% below entry."""
        # Entry at $100, stop loss at $90
        stop_loss = self.rm.calculate_stop_loss(100.0)
        assert stop_loss == 90.0

    def test_stop_loss_bitcoin_price(self):
        """Test stop loss at realistic Bitcoin price."""
        # Entry at $95,000, stop loss at $85,500
        stop_loss = self.rm.calculate_stop_loss(95000.0)
        assert stop_loss == 85500.0

    def test_check_stop_loss_not_triggered(self):
        """Test stop loss not triggered when price is above."""
        # Entry $100, current $95 (only -5%, stop at -10%)
        triggered = self.rm.check_stop_loss(100.0, 95.0)
        assert triggered is False

    def test_check_stop_loss_triggered(self):
        """Test stop loss triggered when price drops 10%."""
        # Entry $100, current $90 (exactly -10%)
        triggered = self.rm.check_stop_loss(100.0, 90.0)
        assert triggered is True

    def test_check_stop_loss_triggered_below(self):
        """Test stop loss triggered when price drops more than 10%."""
        # Entry $100, current $85 (-15%)
        triggered = self.rm.check_stop_loss(100.0, 85.0)
        assert triggered is True


class TestTakeProfitCalculation:
    """Test take profit price calculations."""

    def setup_method(self):
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)
        self.rm = RiskManager(db=self.db)

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_take_profit_calculation(self):
        """Test take profit yields $1 profit."""
        # Entry at $100, size $20
        # $1 profit on $20 = 5% gain needed
        # Take profit = $100 * 1.05 = $105
        take_profit = self.rm.calculate_take_profit(100.0, 20.0)
        assert take_profit == 105.0

    def test_take_profit_larger_position(self):
        """Test take profit with different position size."""
        # Entry at $100, size $10
        # $1 profit on $10 = 10% gain needed
        # Take profit = $100 * 1.10 = $110
        take_profit = self.rm.calculate_take_profit(100.0, 10.0)
        assert take_profit == 110.0

    def test_check_take_profit_not_reached(self):
        """Test take profit not reached when price is below target."""
        # Entry $100, size $20, current $104 (below $105 target)
        reached = self.rm.check_take_profit(100.0, 104.0, 20.0)
        assert reached is False

    def test_check_take_profit_reached(self):
        """Test take profit reached when price hits target."""
        # Entry $100, size $20, current $105 (exactly $1 profit)
        reached = self.rm.check_take_profit(100.0, 105.0, 20.0)
        assert reached is True

    def test_check_take_profit_exceeded(self):
        """Test take profit reached when price exceeds target."""
        # Entry $100, size $20, current $110 (more than $1 profit)
        reached = self.rm.check_take_profit(100.0, 110.0, 20.0)
        assert reached is True


class TestShouldExitTrade:
    """Test the should_exit_trade decision logic."""

    def setup_method(self):
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)
        self.rm = RiskManager(db=self.db)

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_no_exit_in_range(self):
        """Test no exit when price is within range."""
        result = self.rm.should_exit_trade(100.0, 102.0, 20.0)
        assert result['should_exit'] is False
        assert result['reason'] == 'none'
        # 2% gain on $20 = $0.40
        assert abs(result['pnl_usd'] - 0.40) < 0.01

    def test_exit_on_stop_loss(self):
        """Test exit triggered on stop loss."""
        result = self.rm.should_exit_trade(100.0, 90.0, 20.0)
        assert result['should_exit'] is True
        assert result['reason'] == 'stop_loss'
        # -10% loss on $20 = -$2
        assert abs(result['pnl_usd'] - (-2.0)) < 0.01

    def test_exit_on_take_profit(self):
        """Test exit triggered on take profit."""
        result = self.rm.should_exit_trade(100.0, 105.0, 20.0)
        assert result['should_exit'] is True
        assert result['reason'] == 'take_profit'
        # 5% gain on $20 = $1
        assert abs(result['pnl_usd'] - 1.0) < 0.01

    def test_result_contains_pnl(self):
        """Test that result always contains P&L info."""
        result = self.rm.should_exit_trade(100.0, 100.0, 20.0)
        assert 'pnl_usd' in result
        assert 'pnl_pct' in result
        assert result['pnl_usd'] == 0.0
        assert result['pnl_pct'] == 0.0


class TestRiskSummary:
    """Test the get_risk_summary function."""

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

    def test_risk_summary_structure(self):
        """Test risk summary contains all expected fields."""
        summary = get_risk_summary(db=self.db)
        assert 'balance' in summary
        assert 'in_positions' in summary
        assert 'exposure_percent' in summary
        assert 'available_for_trading' in summary
        assert 'max_single_trade' in summary
        assert 'above_minimum' in summary
        assert 'risk_parameters' in summary

    def test_risk_summary_values(self):
        """Test risk summary has correct values for fresh account."""
        summary = get_risk_summary(db=self.db)
        assert summary['balance'] == 1000.0
        assert summary['in_positions'] == 0.0
        assert summary['exposure_percent'] == 0.0
        assert summary['available_for_trading'] == 100.0
        assert summary['max_single_trade'] == 20.0
        assert summary['above_minimum'] is True


class TestActivityLogging:
    """Test that risk checks are logged."""

    def setup_method(self):
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)
        self.rm = RiskManager(db=self.db)

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_log_passed_risk_check(self):
        """Test logging a passed risk check."""
        result = self.rm.validate_trade("bitcoin", 20.0)
        self.rm.log_risk_check("bitcoin", 20.0, result)

        activities = self.db.get_recent_activity(5)
        risk_activities = [a for a in activities if 'risk_check' in a['activity_type']]
        assert len(risk_activities) > 0
        assert risk_activities[0]['activity_type'] == 'risk_check_passed'

    def test_log_failed_risk_check(self):
        """Test logging a failed risk check."""
        result = self.rm.validate_trade("bitcoin", 500.0)
        self.rm.log_risk_check("bitcoin", 500.0, result)

        activities = self.db.get_recent_activity(5)
        risk_activities = [a for a in activities if 'risk_check' in a['activity_type']]
        assert len(risk_activities) > 0
        assert risk_activities[0]['activity_type'] == 'risk_check_failed'


def test_risk_manager_import():
    """Test that RiskManager can be imported."""
    from src.risk_manager import RiskManager, TradeValidation, get_risk_summary
    assert RiskManager is not None
    assert TradeValidation is not None
    assert get_risk_summary is not None
