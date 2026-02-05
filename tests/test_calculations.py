"""
Tests for financial calculations module.

TASK-AUDIT: Financial Math Verification
"""

import math
import pytest
from src.calculations import (
    # Core P&L
    calculate_pnl,
    calculate_pnl_percentage,
    calculate_return_pct,
    # Performance Metrics
    calculate_win_rate,
    calculate_profit_factor,
    calculate_avg_win_loss_ratio,
    calculate_expectancy,
    calculate_return_on_balance,
    # Risk Metrics
    calculate_max_drawdown,
    build_equity_curve,
    calculate_sharpe_ratio,
    # Position Sizing
    calculate_position_size,
    apply_position_modifier,
    # Utilities
    safe_divide,
    clamp_percentage,
)


# =============================================================================
# Core P&L Tests
# =============================================================================

class TestCalculatePnl:
    """Tests for calculate_pnl function."""

    def test_long_profit(self):
        """LONG position with price increase = profit."""
        # Entry $100, current $105, size $1000
        # 5% increase on $1000 = $50 profit
        result = calculate_pnl(100, 105, 1000, "LONG")
        assert result == pytest.approx(50.0)

    def test_long_loss(self):
        """LONG position with price decrease = loss."""
        # Entry $100, current $95, size $1000
        # 5% decrease on $1000 = -$50 loss
        result = calculate_pnl(100, 95, 1000, "LONG")
        assert result == pytest.approx(-50.0)

    def test_short_profit(self):
        """SHORT position with price decrease = profit."""
        # Entry $100, current $95, size $1000
        # 5% decrease = profit for short
        result = calculate_pnl(100, 95, 1000, "SHORT")
        assert result == pytest.approx(50.0)

    def test_short_loss(self):
        """SHORT position with price increase = loss."""
        # Entry $100, current $105, size $1000
        result = calculate_pnl(100, 105, 1000, "SHORT")
        assert result == pytest.approx(-50.0)

    def test_real_sol_position(self):
        """Real-world SOL position from live trading."""
        # Entry $83.20, current $81.63, size $60, LONG
        result = calculate_pnl(83.20, 81.63, 60, "LONG")
        # Expected: ((81.63 - 83.20) / 83.20) * 60 = -1.133...
        assert result == pytest.approx(-1.13, abs=0.01)

    def test_zero_entry_price(self):
        """Zero entry price returns 0."""
        result = calculate_pnl(0, 100, 1000, "LONG")
        assert result == 0.0

    def test_zero_size(self):
        """Zero position size returns 0."""
        result = calculate_pnl(100, 105, 0, "LONG")
        assert result == 0.0

    def test_direction_case_insensitive(self):
        """Direction should be case-insensitive."""
        result1 = calculate_pnl(100, 95, 1000, "short")
        result2 = calculate_pnl(100, 95, 1000, "SHORT")
        result3 = calculate_pnl(100, 95, 1000, "Short")
        assert result1 == result2 == result3


class TestCalculatePnlPercentage:
    """Tests for calculate_pnl_percentage function."""

    def test_positive_pnl(self):
        """Positive P&L gives positive percentage."""
        result = calculate_pnl_percentage(50, 1000)
        assert result == pytest.approx(5.0)

    def test_negative_pnl(self):
        """Negative P&L gives negative percentage."""
        result = calculate_pnl_percentage(-50, 1000)
        assert result == pytest.approx(-5.0)

    def test_zero_size(self):
        """Zero size returns 0."""
        result = calculate_pnl_percentage(50, 0)
        assert result == 0.0

    def test_small_position(self):
        """Small position with fractional percentage."""
        result = calculate_pnl_percentage(-1.13, 60)
        assert result == pytest.approx(-1.88, abs=0.01)


class TestCalculateReturnPct:
    """Tests for calculate_return_pct function."""

    def test_long_profit(self):
        """LONG with price increase."""
        result = calculate_return_pct(100, 105, "LONG")
        assert result == pytest.approx(5.0)

    def test_short_profit(self):
        """SHORT with price decrease."""
        result = calculate_return_pct(100, 95, "SHORT")
        assert result == pytest.approx(5.0)

    def test_zero_entry(self):
        """Zero entry price returns 0."""
        result = calculate_return_pct(0, 100, "LONG")
        assert result == 0.0


# =============================================================================
# Performance Metrics Tests
# =============================================================================

class TestCalculateWinRate:
    """Tests for calculate_win_rate function."""

    def test_basic_win_rate(self):
        """Basic win rate calculation."""
        result = calculate_win_rate(6, 10)
        assert result == pytest.approx(60.0)

    def test_all_wins(self):
        """100% win rate."""
        result = calculate_win_rate(10, 10)
        assert result == pytest.approx(100.0)

    def test_no_wins(self):
        """0% win rate."""
        result = calculate_win_rate(0, 10)
        assert result == pytest.approx(0.0)

    def test_no_trades(self):
        """No trades returns 0."""
        result = calculate_win_rate(0, 0)
        assert result == 0.0


class TestCalculateProfitFactor:
    """Tests for calculate_profit_factor function."""

    def test_profitable(self):
        """Profit factor > 1 means profitable."""
        result = calculate_profit_factor(1000, 500)
        assert result == pytest.approx(2.0)

    def test_unprofitable(self):
        """Profit factor < 1 means unprofitable."""
        result = calculate_profit_factor(500, 1000)
        assert result == pytest.approx(0.5)

    def test_no_losses(self):
        """No losses returns infinity."""
        result = calculate_profit_factor(1000, 0)
        assert result == float('inf')

    def test_no_profit_no_loss(self):
        """No profit and no loss returns 0."""
        result = calculate_profit_factor(0, 0)
        assert result == 0.0


class TestCalculateExpectancy:
    """Tests for calculate_expectancy function."""

    def test_positive_expectancy(self):
        """Positive expectancy system."""
        # 60% win rate, $100 avg win, $50 avg loss
        # (0.6 * 100) - (0.4 * 50) = 60 - 20 = 40
        result = calculate_expectancy(60, 100, 50)
        assert result == pytest.approx(40.0)

    def test_negative_expectancy(self):
        """Negative expectancy system."""
        # 30% win rate, $100 avg win, $100 avg loss
        # (0.3 * 100) - (0.7 * 100) = 30 - 70 = -40
        result = calculate_expectancy(30, 100, 100)
        assert result == pytest.approx(-40.0)

    def test_breakeven(self):
        """Breakeven system."""
        # 50% win rate, $100 avg win, $100 avg loss
        result = calculate_expectancy(50, 100, 100)
        assert result == pytest.approx(0.0)


class TestCalculateReturnOnBalance:
    """Tests for calculate_return_on_balance function."""

    def test_profit(self):
        """Profit return percentage."""
        result = calculate_return_on_balance(1000, 10000)
        assert result == pytest.approx(10.0)

    def test_loss(self):
        """Loss return percentage."""
        result = calculate_return_on_balance(-500, 10000)
        assert result == pytest.approx(-5.0)

    def test_zero_balance(self):
        """Zero balance returns 0."""
        result = calculate_return_on_balance(100, 0)
        assert result == 0.0


# =============================================================================
# Risk Metrics Tests
# =============================================================================

class TestBuildEquityCurve:
    """Tests for build_equity_curve function."""

    def test_basic_curve(self):
        """Build equity curve from P&L values."""
        result = build_equity_curve([100, -50, 200], 1000)
        assert result == [1000, 1100, 1050, 1250]

    def test_empty_pnl(self):
        """Empty P&L returns starting balance only."""
        result = build_equity_curve([], 1000)
        assert result == [1000]


class TestCalculateMaxDrawdown:
    """Tests for calculate_max_drawdown function."""

    def test_basic_drawdown(self):
        """Calculate max drawdown from equity curve."""
        # Peak at 1100, trough at 900 = 200 drawdown (18.18%)
        curve = [1000, 1100, 900, 950, 1050]
        dd_amount, dd_pct = calculate_max_drawdown(curve)
        assert dd_amount == pytest.approx(200.0)
        assert dd_pct == pytest.approx(18.18, abs=0.01)

    def test_no_drawdown(self):
        """Monotonically increasing = no drawdown."""
        curve = [1000, 1100, 1200, 1300]
        dd_amount, dd_pct = calculate_max_drawdown(curve)
        assert dd_amount == 0.0
        assert dd_pct == 0.0

    def test_empty_curve(self):
        """Empty curve returns 0."""
        dd_amount, dd_pct = calculate_max_drawdown([])
        assert dd_amount == 0.0
        assert dd_pct == 0.0

    def test_single_point(self):
        """Single point curve returns 0."""
        dd_amount, dd_pct = calculate_max_drawdown([1000])
        assert dd_amount == 0.0
        assert dd_pct == 0.0


class TestCalculateSharpeRatio:
    """Tests for calculate_sharpe_ratio function."""

    def test_positive_sharpe(self):
        """Positive returns with variance = positive Sharpe."""
        # Returns averaging ~1% with some variance
        returns = [0.01, 0.02, 0.005, 0.015, 0.01, 0.008, 0.012, 0.018, 0.007, 0.013]
        result = calculate_sharpe_ratio(returns, periods_per_year=365)
        assert result > 0

    def test_zero_returns(self):
        """Zero returns = zero Sharpe."""
        returns = [0] * 30
        result = calculate_sharpe_ratio(returns)
        assert result == 0.0

    def test_insufficient_data(self):
        """Less than 2 data points returns 0."""
        result = calculate_sharpe_ratio([0.01])
        assert result == 0.0

    def test_empty_returns(self):
        """Empty returns list returns 0."""
        result = calculate_sharpe_ratio([])
        assert result == 0.0


# =============================================================================
# Position Sizing Tests
# =============================================================================

class TestCalculatePositionSize:
    """Tests for calculate_position_size function."""

    def test_basic_sizing(self):
        """Basic position sizing calculation."""
        # $10000 balance, 1% risk, 2% stop loss
        # Risk = $100, SL = 2%, Position = $100 / 0.02 = $5000
        result = calculate_position_size(10000, 1.0, 2.0)
        assert result == pytest.approx(5000.0)

    def test_tighter_stop(self):
        """Tighter stop = smaller position."""
        # Same risk but 1% stop
        result = calculate_position_size(10000, 1.0, 1.0)
        assert result == pytest.approx(10000.0)

    def test_zero_stop_loss(self):
        """Zero stop loss returns 0."""
        result = calculate_position_size(10000, 1.0, 0)
        assert result == 0.0


class TestApplyPositionModifier:
    """Tests for apply_position_modifier function."""

    def test_reduced(self):
        """Reduced modifier (0.5)."""
        result = apply_position_modifier(100, 0.5)
        assert result == pytest.approx(50.0)

    def test_normal(self):
        """Normal modifier (1.0)."""
        result = apply_position_modifier(100, 1.0)
        assert result == pytest.approx(100.0)

    def test_favored(self):
        """Favored modifier (1.5)."""
        result = apply_position_modifier(100, 1.5)
        assert result == pytest.approx(150.0)

    def test_with_max_size(self):
        """Max size cap is applied."""
        result = apply_position_modifier(100, 1.5, max_size=120)
        assert result == pytest.approx(120.0)


# =============================================================================
# Utility Tests
# =============================================================================

class TestSafeDivide:
    """Tests for safe_divide function."""

    def test_normal_division(self):
        """Normal division works."""
        result = safe_divide(10, 2)
        assert result == pytest.approx(5.0)

    def test_zero_denominator(self):
        """Zero denominator returns default."""
        result = safe_divide(10, 0)
        assert result == 0.0

    def test_custom_default(self):
        """Custom default on zero division."""
        result = safe_divide(10, 0, default=-1)
        assert result == -1


class TestClampPercentage:
    """Tests for clamp_percentage function."""

    def test_within_range(self):
        """Value within range unchanged."""
        result = clamp_percentage(50)
        assert result == 50.0

    def test_below_min(self):
        """Value below min clamped."""
        result = clamp_percentage(-10)
        assert result == 0.0

    def test_above_max(self):
        """Value above max clamped."""
        result = clamp_percentage(150)
        assert result == 100.0


# =============================================================================
# Integration Tests
# =============================================================================

class TestPnlConsistency:
    """Test that P&L calculations are consistent across methods."""

    def test_pnl_matches_return_pct(self):
        """P&L and return percentage should match."""
        entry = 100
        exit = 105
        size = 1000
        direction = "LONG"

        pnl = calculate_pnl(entry, exit, size, direction)
        pnl_pct = calculate_pnl_percentage(pnl, size)
        return_pct = calculate_return_pct(entry, exit, direction)

        assert pnl_pct == pytest.approx(return_pct)

    def test_short_pnl_matches_return_pct(self):
        """SHORT P&L and return percentage should match."""
        entry = 100
        exit = 95
        size = 1000
        direction = "SHORT"

        pnl = calculate_pnl(entry, exit, size, direction)
        pnl_pct = calculate_pnl_percentage(pnl, size)
        return_pct = calculate_return_pct(entry, exit, direction)

        assert pnl_pct == pytest.approx(return_pct)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_small_price_movement(self):
        """Very small price changes don't cause precision issues."""
        result = calculate_pnl(100.0001, 100.0002, 1000, "LONG")
        assert result == pytest.approx(0.001, abs=0.0001)

    def test_large_position(self):
        """Large positions calculate correctly."""
        result = calculate_pnl(50000, 51000, 1000000, "LONG")
        assert result == pytest.approx(20000.0)

    def test_fractional_shares(self):
        """Fractional calculations are accurate."""
        # $60 position at $83.20 entry = 0.7212 "coins"
        # Price drops to $81.63, loss = 0.7212 * (81.63 - 83.20) = -1.13
        result = calculate_pnl(83.20, 81.63, 60, "LONG")
        assert result == pytest.approx(-1.13, abs=0.01)
