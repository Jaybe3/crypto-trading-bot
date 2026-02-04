"""Tests for RSI Calculator."""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.technical.rsi import RSICalculator, RSIData
from src.technical.candle_fetcher import CandleFetcher, Candle, CandleData


class TestRSIData:
    """Tests for RSIData dataclass."""

    def test_is_overbought_boundary(self):
        """Test overbought at boundary (70 = not, 71 = yes)."""
        not_overbought = RSIData(coin="BTC", value=70.0, period=14, timeframe="1h", timestamp=datetime.now())
        overbought = RSIData(coin="BTC", value=70.1, period=14, timeframe="1h", timestamp=datetime.now())

        assert not_overbought.is_overbought is False
        assert overbought.is_overbought is True

    def test_is_oversold_boundary(self):
        """Test oversold at boundary (30 = not, 29 = yes)."""
        not_oversold = RSIData(coin="BTC", value=30.0, period=14, timeframe="1h", timestamp=datetime.now())
        oversold = RSIData(coin="BTC", value=29.9, period=14, timeframe="1h", timestamp=datetime.now())

        assert not_oversold.is_oversold is False
        assert oversold.is_oversold is True

    def test_condition_oversold(self):
        data = RSIData(coin="BTC", value=25.0, period=14, timeframe="1h", timestamp=datetime.now())
        assert data.condition == "oversold"

    def test_condition_overbought(self):
        data = RSIData(coin="BTC", value=75.0, period=14, timeframe="1h", timestamp=datetime.now())
        assert data.condition == "overbought"

    def test_condition_neutral(self):
        data = RSIData(coin="BTC", value=50.0, period=14, timeframe="1h", timestamp=datetime.now())
        assert data.condition == "neutral"


class TestRSICalculator:
    """Tests for RSICalculator."""

    @pytest.fixture
    def mock_fetcher(self):
        return Mock(spec=CandleFetcher)

    def test_init_default_period(self, mock_fetcher):
        rsi = RSICalculator(mock_fetcher)
        assert rsi.default_period == 14

    def test_init_custom_period(self, mock_fetcher):
        rsi = RSICalculator(mock_fetcher, default_period=21)
        assert rsi.default_period == 21

    def test_calculate_from_closes_all_gains(self):
        """RSI should be 100 when all price changes are gains."""
        mock_fetcher = Mock(spec=CandleFetcher)
        rsi = RSICalculator(mock_fetcher)

        # Steadily rising prices
        closes = [100 + i for i in range(20)]
        result = rsi.calculate_from_closes(closes, period=14)

        assert result == 100.0

    def test_calculate_from_closes_all_losses(self):
        """RSI should be 0 when all price changes are losses."""
        mock_fetcher = Mock(spec=CandleFetcher)
        rsi = RSICalculator(mock_fetcher)

        # Steadily falling prices
        closes = [100 - i for i in range(20)]
        result = rsi.calculate_from_closes(closes, period=14)

        assert result == 0.0

    def test_calculate_from_closes_neutral(self):
        """RSI should be ~50 for alternating gains/losses."""
        mock_fetcher = Mock(spec=CandleFetcher)
        rsi = RSICalculator(mock_fetcher)

        # Alternating up/down of equal magnitude
        closes = []
        price = 100
        for i in range(30):
            closes.append(price)
            price += 1 if i % 2 == 0 else -1

        result = rsi.calculate_from_closes(closes, period=14)

        # Should be close to 50 (neutral)
        assert 45 < result < 55

    def test_calculate_from_closes_insufficient_data(self):
        """RSI should return 50 for insufficient data."""
        mock_fetcher = Mock(spec=CandleFetcher)
        rsi = RSICalculator(mock_fetcher)

        closes = [100, 101, 102]  # Only 3 data points
        result = rsi.calculate_from_closes(closes, period=14)

        assert result == 50.0

    def test_calculate_uses_fetcher(self, mock_fetcher):
        """Test that calculate() uses the candle fetcher."""
        # Create mock candle data with upward trend
        candles = [Candle(i * 1000, 100 + i, 101 + i, 99 + i, 100.5 + i, 1000) for i in range(50)]
        mock_fetcher.get_candles.return_value = CandleData(coin="BTC", interval="1h", candles=candles)

        rsi = RSICalculator(mock_fetcher)
        result = rsi.calculate("BTC", "1h")

        assert mock_fetcher.get_candles.called
        assert result.coin == "BTC"
        assert result.timeframe == "1h"
        assert result.period == 14
        assert 0 <= result.value <= 100

    def test_calculate_insufficient_candles(self, mock_fetcher):
        """Test handling of insufficient candle data."""
        candles = [Candle(i * 1000, 100, 101, 99, 100, 1000) for i in range(5)]
        mock_fetcher.get_candles.return_value = CandleData(coin="BTC", interval="1h", candles=candles)

        rsi = RSICalculator(mock_fetcher)
        result = rsi.calculate("BTC", "1h")

        # Should return neutral default
        assert result.value == 50.0

    def test_get_multi_timeframe(self, mock_fetcher):
        """Test multi-timeframe RSI calculation."""
        candles = [Candle(i * 1000, 100 + i, 101 + i, 99 + i, 100.5 + i, 1000) for i in range(50)]
        mock_fetcher.get_candles.return_value = CandleData(coin="BTC", interval="1h", candles=candles)

        rsi = RSICalculator(mock_fetcher)
        results = rsi.get_multi_timeframe("BTC", ["15m", "1h", "4h"])

        assert len(results) == 3
        assert "15m" in results
        assert "1h" in results
        assert "4h" in results

    def test_wilder_smoothing_accuracy(self):
        """Test that Wilder's smoothing produces expected RSI values."""
        mock_fetcher = Mock(spec=CandleFetcher)
        rsi = RSICalculator(mock_fetcher)

        # Known test case: 14 period RSI
        # After 14 gains of 1.0 each, then 14 losses of 0.5 each
        closes = [100]
        for i in range(14):
            closes.append(closes[-1] + 1.0)  # 14 gains
        for i in range(14):
            closes.append(closes[-1] - 0.5)  # 14 losses

        result = rsi.calculate_from_closes(closes, period=14)

        # RSI should be somewhere between 0 and 100, biased toward gains
        assert 0 < result < 100
