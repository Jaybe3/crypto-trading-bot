"""
Tests for Performance Analysis (TASK-152).

Tests for metrics calculation, performance breakdown, and learning analysis.
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta

from src.analysis.metrics import (
    TradingMetrics,
    calculate_metrics,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_profit_factor,
    build_equity_curve,
)
from src.analysis.performance import (
    analyze_by_hour,
    analyze_by_coin,
    analyze_by_pattern,
    compare_periods,
    get_best_worst_hours,
    get_best_worst_coins,
    calculate_consistency,
)
from src.database import Database


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_trades():
    """Sample trades for testing."""
    base_time = datetime.now() - timedelta(days=7)
    return [
        # Winning trades
        {"trade_id": "t1", "coin": "BTC", "pnl_usd": 50.0, "exit_time": (base_time + timedelta(hours=1)).isoformat(),
         "entry_time": (base_time + timedelta(hours=0, minutes=50)).isoformat(), "pattern_id": "breakout",
         "duration_seconds": 600},
        {"trade_id": "t2", "coin": "ETH", "pnl_usd": 30.0, "exit_time": (base_time + timedelta(hours=2)).isoformat(),
         "entry_time": (base_time + timedelta(hours=1, minutes=50)).isoformat(), "pattern_id": "support",
         "duration_seconds": 600},
        {"trade_id": "t3", "coin": "BTC", "pnl_usd": 25.0, "exit_time": (base_time + timedelta(hours=3)).isoformat(),
         "entry_time": (base_time + timedelta(hours=2, minutes=50)).isoformat(), "pattern_id": "breakout",
         "duration_seconds": 600},
        {"trade_id": "t4", "coin": "SOL", "pnl_usd": 40.0, "exit_time": (base_time + timedelta(hours=4)).isoformat(),
         "entry_time": (base_time + timedelta(hours=3, minutes=50)).isoformat(), "pattern_id": "momentum",
         "duration_seconds": 600},
        {"trade_id": "t5", "coin": "BTC", "pnl_usd": 15.0, "exit_time": (base_time + timedelta(hours=5)).isoformat(),
         "entry_time": (base_time + timedelta(hours=4, minutes=50)).isoformat(), "pattern_id": "breakout",
         "duration_seconds": 600},
        # Losing trades
        {"trade_id": "t6", "coin": "DOGE", "pnl_usd": -20.0, "exit_time": (base_time + timedelta(hours=6)).isoformat(),
         "entry_time": (base_time + timedelta(hours=5, minutes=50)).isoformat(), "pattern_id": "support",
         "duration_seconds": 600},
        {"trade_id": "t7", "coin": "ETH", "pnl_usd": -15.0, "exit_time": (base_time + timedelta(hours=7)).isoformat(),
         "entry_time": (base_time + timedelta(hours=6, minutes=50)).isoformat(), "pattern_id": "momentum",
         "duration_seconds": 600},
        {"trade_id": "t8", "coin": "BTC", "pnl_usd": -10.0, "exit_time": (base_time + timedelta(hours=8)).isoformat(),
         "entry_time": (base_time + timedelta(hours=7, minutes=50)).isoformat(), "pattern_id": "breakout",
         "duration_seconds": 600},
        # Breakeven
        {"trade_id": "t9", "coin": "SOL", "pnl_usd": 0.0, "exit_time": (base_time + timedelta(hours=9)).isoformat(),
         "entry_time": (base_time + timedelta(hours=8, minutes=50)).isoformat(), "pattern_id": "support",
         "duration_seconds": 600},
        {"trade_id": "t10", "coin": "ETH", "pnl_usd": 20.0, "exit_time": (base_time + timedelta(hours=10)).isoformat(),
         "entry_time": (base_time + timedelta(hours=9, minutes=50)).isoformat(), "pattern_id": "breakout",
         "duration_seconds": 600},
    ]


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_analysis.db")
    db = Database(db_path=db_path)
    yield db
    if os.path.exists(db_path):
        os.remove(db_path)
    os.rmdir(temp_dir)


# =============================================================================
# Metrics Tests
# =============================================================================

class TestTradingMetrics:
    """Tests for core trading metrics calculation."""

    def test_calculate_metrics_basic(self, sample_trades):
        """Calculate basic metrics from sample trades."""
        metrics = calculate_metrics(sample_trades)

        assert metrics.total_trades == 10
        assert metrics.wins == 6  # 5 wins + 1 more
        assert metrics.losses == 3
        assert metrics.breakeven == 1

    def test_calculate_win_rate(self, sample_trades):
        """Win rate is calculated correctly."""
        metrics = calculate_metrics(sample_trades)

        # 6 wins out of 10 = 60%
        assert 55 <= metrics.win_rate <= 65

    def test_calculate_total_pnl(self, sample_trades):
        """Total P&L is calculated correctly."""
        metrics = calculate_metrics(sample_trades)

        # Sum: 50+30+25+40+15-20-15-10+0+20 = 135
        expected = 50 + 30 + 25 + 40 + 15 - 20 - 15 - 10 + 0 + 20
        assert abs(metrics.total_pnl - expected) < 0.01

    def test_calculate_profit_factor(self, sample_trades):
        """Profit factor is calculated correctly."""
        metrics = calculate_metrics(sample_trades)

        # Gross profit: 50+30+25+40+15+20 = 180
        # Gross loss: 20+15+10 = 45
        # PF = 180/45 = 4.0
        assert metrics.profit_factor > 1.0
        assert 3.5 <= metrics.profit_factor <= 4.5

    def test_calculate_avg_win_loss(self, sample_trades):
        """Average win and loss are calculated correctly."""
        metrics = calculate_metrics(sample_trades)

        # Wins: 50, 30, 25, 40, 15, 20 = 180/6 = 30
        assert 25 <= metrics.avg_win <= 35

        # Losses: 20, 15, 10 = 45/3 = 15
        assert 10 <= metrics.avg_loss <= 20

    def test_calculate_largest_win_loss(self, sample_trades):
        """Largest win and loss are identified correctly."""
        metrics = calculate_metrics(sample_trades)

        assert metrics.largest_win == 50.0
        assert metrics.largest_loss == -20.0

    def test_empty_trades(self):
        """Handle empty trade list gracefully."""
        metrics = calculate_metrics([])

        assert metrics.total_trades == 0
        assert metrics.win_rate == 0
        assert metrics.total_pnl == 0


class TestSharpeRatio:
    """Tests for Sharpe ratio calculation."""

    def test_sharpe_positive_returns(self):
        """Sharpe ratio for positive returns."""
        returns = [0.02, 0.01, 0.03, 0.02, 0.01]
        sharpe = calculate_sharpe_ratio(returns, annualize=False)

        assert sharpe > 0

    def test_sharpe_negative_returns(self):
        """Sharpe ratio for negative returns."""
        returns = [-0.02, -0.01, -0.03, -0.02, -0.01]
        sharpe = calculate_sharpe_ratio(returns, annualize=False)

        assert sharpe < 0

    def test_sharpe_mixed_returns(self):
        """Sharpe ratio for mixed returns."""
        returns = [0.05, -0.02, 0.03, -0.01, 0.04]
        sharpe = calculate_sharpe_ratio(returns, annualize=False)

        # Should be positive since net return is positive
        assert sharpe > 0

    def test_sharpe_zero_std(self):
        """Sharpe ratio when all returns are the same."""
        returns = [0.01, 0.01, 0.01, 0.01]
        sharpe = calculate_sharpe_ratio(returns, annualize=False)

        assert sharpe == 0  # Zero std means zero Sharpe

    def test_sharpe_empty_returns(self):
        """Sharpe ratio for empty returns."""
        sharpe = calculate_sharpe_ratio([])
        assert sharpe == 0


class TestMaxDrawdown:
    """Tests for max drawdown calculation."""

    def test_drawdown_no_losses(self):
        """No drawdown when equity only goes up."""
        equity = [1000, 1050, 1100, 1150, 1200]
        dd_amount, dd_pct = calculate_max_drawdown(equity)

        assert dd_amount == 0
        assert dd_pct == 0

    def test_drawdown_simple(self):
        """Calculate drawdown with simple decline."""
        equity = [1000, 1100, 1050, 1000, 1150]  # Peak 1100, trough 1000
        dd_amount, dd_pct = calculate_max_drawdown(equity)

        assert abs(dd_amount - 100) < 0.01  # 1100 - 1000 = 100
        assert abs(dd_pct - 9.09) < 0.5  # 100/1100 * 100 = 9.09%

    def test_drawdown_multiple_dips(self):
        """Max drawdown with multiple dips finds the largest."""
        equity = [1000, 1100, 1050, 1200, 1000, 1300]
        # First dip: 1100->1050 = 50 (4.5%)
        # Second dip: 1200->1000 = 200 (16.7%)
        dd_amount, dd_pct = calculate_max_drawdown(equity)

        assert abs(dd_amount - 200) < 0.01
        assert abs(dd_pct - 16.67) < 1

    def test_drawdown_empty(self):
        """Handle empty equity curve."""
        dd_amount, dd_pct = calculate_max_drawdown([])
        assert dd_amount == 0
        assert dd_pct == 0


class TestProfitFactor:
    """Tests for profit factor calculation."""

    def test_profit_factor_profitable(self):
        """Profit factor for profitable trading."""
        pf = calculate_profit_factor(1000, 500)
        assert pf == 2.0

    def test_profit_factor_losing(self):
        """Profit factor for losing trading."""
        pf = calculate_profit_factor(500, 1000)
        assert pf == 0.5

    def test_profit_factor_no_losses(self):
        """Profit factor with no losses."""
        pf = calculate_profit_factor(1000, 0)
        assert pf == float("inf")

    def test_profit_factor_no_profits(self):
        """Profit factor with no profits."""
        pf = calculate_profit_factor(0, 1000)
        assert pf == 0


class TestEquityCurve:
    """Tests for equity curve building."""

    def test_build_equity_curve(self):
        """Build equity curve from P&L values."""
        pnl = [50, -20, 30, -10, 40]
        curve = build_equity_curve(pnl, starting_balance=1000)

        assert len(curve) == 6  # Starting + 5 trades
        assert curve[0] == 1000
        assert curve[1] == 1050
        assert curve[2] == 1030
        assert curve[-1] == 1090  # 1000 + 50 - 20 + 30 - 10 + 40


# =============================================================================
# Performance Breakdown Tests
# =============================================================================

class TestPerformanceBreakdown:
    """Tests for performance breakdown by dimension."""

    def test_analyze_by_coin(self, sample_trades):
        """Analyze performance by coin."""
        by_coin = analyze_by_coin(sample_trades)

        assert "BTC" in by_coin
        assert "ETH" in by_coin
        assert "SOL" in by_coin
        assert "DOGE" in by_coin

        # BTC should have 4 trades
        assert by_coin["BTC"].total_trades == 4

    def test_analyze_by_pattern(self, sample_trades):
        """Analyze performance by pattern."""
        by_pattern = analyze_by_pattern(sample_trades)

        assert "breakout" in by_pattern
        assert "support" in by_pattern
        assert "momentum" in by_pattern

    def test_analyze_by_hour(self, sample_trades):
        """Analyze performance by hour."""
        by_hour = analyze_by_hour(sample_trades)

        # Should have entries for hours with trades
        assert len(by_hour) > 0

    def test_compare_periods(self, sample_trades):
        """Compare first half vs second half."""
        comparison = compare_periods(sample_trades)

        assert "first_half" in comparison
        assert "second_half" in comparison
        assert "comparison" in comparison

        # Should have split the trades
        first = comparison["first_half"]
        second = comparison["second_half"]

        assert first["total_trades"] + second["total_trades"] == 10

    def test_get_best_worst_coins(self, sample_trades):
        """Identify best and worst coins."""
        by_coin = analyze_by_coin(sample_trades)
        best_worst = get_best_worst_coins(by_coin, min_trades=1)

        assert "best_coins" in best_worst
        assert "worst_coins" in best_worst

    def test_calculate_consistency(self, sample_trades):
        """Calculate trading consistency."""
        consistency = calculate_consistency(sample_trades)

        assert "profitable_periods" in consistency
        assert "total_periods" in consistency
        assert "consistency_rate" in consistency


# =============================================================================
# Learning Analysis Tests
# =============================================================================

class TestLearningAnalysis:
    """Tests for learning effectiveness analysis."""

    def test_analyze_coin_score_accuracy_no_data(self, temp_db):
        """Handle case with no coin score data."""
        from src.analysis.learning import analyze_coin_score_accuracy

        result = analyze_coin_score_accuracy(temp_db)

        assert "total_coins" in result
        assert result["total_coins"] == 0

    def test_analyze_adaptation_effectiveness_no_data(self, temp_db):
        """Handle case with no adaptation data."""
        from src.analysis.learning import analyze_adaptation_effectiveness

        result = analyze_adaptation_effectiveness(temp_db)

        assert "total_adaptations" in result
        assert result["total_adaptations"] == 0

    def test_analyze_pattern_confidence_no_data(self, temp_db):
        """Handle case with no pattern data."""
        from src.analysis.learning import analyze_pattern_confidence_accuracy

        result = analyze_pattern_confidence_accuracy(temp_db)

        assert "total_patterns" in result
        assert result["total_patterns"] == 0

    def test_analyze_knowledge_growth(self, temp_db):
        """Analyze knowledge growth over time."""
        from src.analysis.learning import analyze_knowledge_growth

        result = analyze_knowledge_growth(temp_db, days=7)

        assert "period_days" in result
        assert result["period_days"] == 7
        assert "total_patterns" in result
        assert "total_rules" in result

    def test_calculate_learning_score(self):
        """Calculate overall learning score."""
        from src.analysis.learning import calculate_learning_score

        coin_accuracy = {"correlation": 0.7}
        adapt_effectiveness = {"effectiveness_rate": 60, "harmful_rate": 10}
        pattern_accuracy = {"confidence_predicts_outcomes": True}
        knowledge_growth = {"new_patterns": 5, "new_rules": 3, "total_adaptations": 8}

        result = calculate_learning_score(
            coin_accuracy, adapt_effectiveness, pattern_accuracy, knowledge_growth
        )

        assert "total_score" in result
        assert "grade" in result
        assert "assessment" in result
        assert 0 <= result["total_score"] <= 100


# =============================================================================
# Integration Tests
# =============================================================================

class TestAnalysisIntegration:
    """Integration tests for the full analysis pipeline."""

    def test_full_metrics_calculation(self, sample_trades):
        """Test full metrics calculation pipeline."""
        metrics = calculate_metrics(sample_trades)

        # Verify all fields are populated
        assert metrics.total_trades > 0
        assert metrics.win_rate > 0
        assert metrics.total_pnl != 0
        assert metrics.profit_factor > 0

        # Verify summary generation
        summary = metrics.summary()
        assert "Total Trades" in summary
        assert "Win Rate" in summary

    def test_metrics_to_dict(self, sample_trades):
        """Test metrics serialization."""
        metrics = calculate_metrics(sample_trades)
        data = metrics.to_dict()

        assert isinstance(data, dict)
        assert "total_trades" in data
        assert "win_rate" in data
        assert "total_pnl" in data

    def test_all_breakdowns_consistent(self, sample_trades):
        """All breakdown analyses sum to total."""
        by_coin = analyze_by_coin(sample_trades)

        total_from_coins = sum(m.total_trades for m in by_coin.values())
        assert total_from_coins == len(sample_trades)

        by_pattern = analyze_by_pattern(sample_trades)
        total_from_patterns = sum(m.total_trades for m in by_pattern.values())
        assert total_from_patterns == len(sample_trades)
