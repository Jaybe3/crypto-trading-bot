"""Tests for BTC Correlation Tracker."""
import pytest
from datetime import datetime
from unittest.mock import Mock

from src.sentiment.btc_correlation import BTCCorrelationTracker, BTCCorrelation
from src.technical.candle_fetcher import CandleFetcher, Candle, CandleData


class TestBTCCorrelation:
    """Tests for BTCCorrelation dataclass."""

    def test_move_type_btc_correlated(self):
        corr = BTCCorrelation(
            coin="SOL",
            btc_change_1h=2.0,
            coin_change_1h=3.0,
            correlation_24h=0.8,
            is_btc_driven=True,
            timestamp=datetime.now()
        )
        assert corr.move_type == "btc_correlated"

    def test_move_type_coin_specific(self):
        corr = BTCCorrelation(
            coin="SOL",
            btc_change_1h=0.5,
            coin_change_1h=5.0,
            correlation_24h=0.3,
            is_btc_driven=False,
            timestamp=datetime.now()
        )
        assert corr.move_type == "coin_specific"

    def test_move_type_normal(self):
        corr = BTCCorrelation(
            coin="SOL",
            btc_change_1h=0.2,
            coin_change_1h=0.3,
            correlation_24h=0.4,
            is_btc_driven=False,
            timestamp=datetime.now()
        )
        assert corr.move_type == "normal"

    def test_correlation_strength_very_strong(self):
        corr = BTCCorrelation(
            coin="ETH", btc_change_1h=1.0, coin_change_1h=1.2,
            correlation_24h=0.85, is_btc_driven=True, timestamp=datetime.now()
        )
        assert corr.correlation_strength == "very_strong"

    def test_correlation_strength_strong(self):
        corr = BTCCorrelation(
            coin="ETH", btc_change_1h=1.0, coin_change_1h=1.2,
            correlation_24h=0.65, is_btc_driven=True, timestamp=datetime.now()
        )
        assert corr.correlation_strength == "strong"

    def test_correlation_strength_moderate(self):
        corr = BTCCorrelation(
            coin="ETH", btc_change_1h=1.0, coin_change_1h=1.2,
            correlation_24h=0.45, is_btc_driven=False, timestamp=datetime.now()
        )
        assert corr.correlation_strength == "moderate"

    def test_correlation_strength_weak(self):
        corr = BTCCorrelation(
            coin="ETH", btc_change_1h=1.0, coin_change_1h=1.2,
            correlation_24h=0.25, is_btc_driven=False, timestamp=datetime.now()
        )
        assert corr.correlation_strength == "weak"

    def test_correlation_strength_none(self):
        corr = BTCCorrelation(
            coin="ETH", btc_change_1h=1.0, coin_change_1h=1.2,
            correlation_24h=0.1, is_btc_driven=False, timestamp=datetime.now()
        )
        assert corr.correlation_strength == "none"


class TestBTCCorrelationTracker:
    """Tests for BTCCorrelationTracker."""

    @pytest.fixture
    def mock_fetcher(self):
        return Mock(spec=CandleFetcher)

    def test_calculate_change_positive(self, mock_fetcher):
        tracker = BTCCorrelationTracker(mock_fetcher)
        closes = [100, 102, 105, 110]  # +10% over 3 periods
        change = tracker._calculate_change(closes, 1)
        # Change from 105 to 110 = 4.76%
        assert abs(change - 4.76) < 0.1

    def test_calculate_change_negative(self, mock_fetcher):
        tracker = BTCCorrelationTracker(mock_fetcher)
        closes = [100, 98, 95, 90]  # Declining
        change = tracker._calculate_change(closes, 1)
        # Change from 95 to 90 = -5.26%
        assert change < 0

    def test_calculate_change_insufficient_data(self, mock_fetcher):
        tracker = BTCCorrelationTracker(mock_fetcher)
        closes = [100]  # Only 1 data point
        change = tracker._calculate_change(closes, 1)
        assert change == 0.0

    def test_pearson_correlation_perfect_positive(self, mock_fetcher):
        tracker = BTCCorrelationTracker(mock_fetcher)
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]  # Perfect positive correlation
        corr = tracker._pearson_correlation(x, y)
        assert abs(corr - 1.0) < 0.01

    def test_pearson_correlation_perfect_negative(self, mock_fetcher):
        tracker = BTCCorrelationTracker(mock_fetcher)
        x = [1, 2, 3, 4, 5]
        y = [10, 8, 6, 4, 2]  # Perfect negative correlation
        corr = tracker._pearson_correlation(x, y)
        assert abs(corr - (-1.0)) < 0.01

    def test_pearson_correlation_no_correlation(self, mock_fetcher):
        tracker = BTCCorrelationTracker(mock_fetcher)
        x = [1, 2, 3, 4, 5]
        y = [5, 2, 4, 1, 3]  # Random
        corr = tracker._pearson_correlation(x, y)
        # Should be close to 0
        assert abs(corr) < 0.5

    def test_is_btc_driven_move_true(self, mock_fetcher):
        tracker = BTCCorrelationTracker(mock_fetcher)
        result = tracker._is_btc_driven_move(
            btc_change=2.0,    # >1%
            coin_change=2.5,   # Same direction
            correlation=0.7    # >0.5
        )
        assert result is True

    def test_is_btc_driven_move_btc_too_small(self, mock_fetcher):
        tracker = BTCCorrelationTracker(mock_fetcher)
        result = tracker._is_btc_driven_move(
            btc_change=0.5,    # <1%
            coin_change=2.5,
            correlation=0.7
        )
        assert result is False

    def test_is_btc_driven_move_opposite_direction(self, mock_fetcher):
        tracker = BTCCorrelationTracker(mock_fetcher)
        result = tracker._is_btc_driven_move(
            btc_change=2.0,
            coin_change=-1.5,  # Opposite direction
            correlation=0.7
        )
        assert result is False

    def test_is_btc_driven_move_low_correlation(self, mock_fetcher):
        tracker = BTCCorrelationTracker(mock_fetcher)
        result = tracker._is_btc_driven_move(
            btc_change=2.0,
            coin_change=2.5,
            correlation=0.3    # <0.5
        )
        assert result is False

    def test_get_correlation_uses_fetcher(self, mock_fetcher):
        # Create correlated price data
        btc_candles = [Candle(i * 1000, 100 + i, 101 + i, 99 + i, 100.5 + i, 1000) for i in range(25)]
        sol_candles = [Candle(i * 1000, 50 + i * 0.5, 51 + i * 0.5, 49 + i * 0.5, 50.25 + i * 0.5, 500) for i in range(25)]

        mock_fetcher.get_candles.side_effect = [
            CandleData(coin="BTC", interval="1h", candles=btc_candles),
            CandleData(coin="SOL", interval="1h", candles=sol_candles)
        ]

        tracker = BTCCorrelationTracker(mock_fetcher)
        result = tracker.get_correlation("SOL")

        assert result.coin == "SOL"
        assert mock_fetcher.get_candles.call_count == 2

    def test_get_all_correlations(self, mock_fetcher):
        btc_candles = [Candle(i * 1000, 100 + i, 101 + i, 99 + i, 100.5 + i, 1000) for i in range(25)]
        alt_candles = [Candle(i * 1000, 50 + i, 51 + i, 49 + i, 50.5 + i, 500) for i in range(25)]

        mock_fetcher.get_candles.return_value = CandleData(coin="BTC", interval="1h", candles=btc_candles)
        mock_fetcher.get_candles.side_effect = lambda coin, *args, **kwargs: (
            CandleData(coin=coin, interval="1h", candles=btc_candles if coin == "BTC" else alt_candles)
        )

        tracker = BTCCorrelationTracker(mock_fetcher)
        results = tracker.get_all_correlations(["SOL", "ETH", "BTC"])

        # BTC should be excluded
        assert "BTC" not in results
        assert "SOL" in results
        assert "ETH" in results

    def test_is_btc_driven_move_method(self, mock_fetcher):
        btc_candles = [Candle(i * 1000, 100, 105, 95, 100 + i * 2, 1000) for i in range(25)]
        sol_candles = [Candle(i * 1000, 50, 52, 48, 50 + i, 500) for i in range(25)]

        mock_fetcher.get_candles.side_effect = [
            CandleData(coin="BTC", interval="1h", candles=btc_candles),
            CandleData(coin="SOL", interval="1h", candles=sol_candles)
        ]

        tracker = BTCCorrelationTracker(mock_fetcher)
        is_driven, reason = tracker.is_btc_driven_move("SOL")

        # Result depends on calculated values
        assert isinstance(is_driven, bool)
        assert isinstance(reason, str)
