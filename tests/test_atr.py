"""Tests for ATR Calculator."""
import pytest
from datetime import datetime
from unittest.mock import Mock

from src.technical.atr import ATRCalculator, ATRData
from src.technical.candle_fetcher import CandleFetcher, Candle, CandleData


class TestATRData:
    """Tests for ATRData dataclass."""

    def test_volatility_level_extreme(self):
        data = ATRData(coin="BTC", atr=5000, atr_pct=6.0, period=14, current_price=50000, timeframe="1h", timestamp=datetime.now())
        assert data.volatility_level == "extreme"

    def test_volatility_level_high(self):
        data = ATRData(coin="BTC", atr=2000, atr_pct=4.0, period=14, current_price=50000, timeframe="1h", timestamp=datetime.now())
        assert data.volatility_level == "high"

    def test_volatility_level_moderate(self):
        data = ATRData(coin="BTC", atr=1000, atr_pct=2.0, period=14, current_price=50000, timeframe="1h", timestamp=datetime.now())
        assert data.volatility_level == "moderate"

    def test_volatility_level_low(self):
        data = ATRData(coin="BTC", atr=500, atr_pct=1.0, period=14, current_price=50000, timeframe="1h", timestamp=datetime.now())
        assert data.volatility_level == "low"

    def test_suggested_stop_loss(self):
        data = ATRData(coin="BTC", atr=1000, atr_pct=2.0, period=14, current_price=50000, timeframe="1h", timestamp=datetime.now())

        assert data.suggested_stop_loss(1.5) == 1500
        assert data.suggested_stop_loss(2.0) == 2000

    def test_suggested_stop_price_long(self):
        data = ATRData(coin="BTC", atr=1000, atr_pct=2.0, period=14, current_price=50000, timeframe="1h", timestamp=datetime.now())

        stop = data.suggested_stop_price(50000, "LONG", 1.5)
        assert stop == 48500  # 50000 - 1500

    def test_suggested_stop_price_short(self):
        data = ATRData(coin="BTC", atr=1000, atr_pct=2.0, period=14, current_price=50000, timeframe="1h", timestamp=datetime.now())

        stop = data.suggested_stop_price(50000, "SHORT", 1.5)
        assert stop == 51500  # 50000 + 1500


class TestATRCalculator:
    """Tests for ATRCalculator."""

    @pytest.fixture
    def mock_fetcher(self):
        return Mock(spec=CandleFetcher)

    def test_init_default_period(self, mock_fetcher):
        atr = ATRCalculator(mock_fetcher)
        assert atr.default_period == 14

    def test_init_custom_period(self, mock_fetcher):
        atr = ATRCalculator(mock_fetcher, default_period=21)
        assert atr.default_period == 21

    def test_true_range_normal_candle(self, mock_fetcher):
        """Test True Range for a normal candle."""
        atr = ATRCalculator(mock_fetcher)

        # Normal candle: H=105, L=95, C=100
        candle = Candle(1000, 100, 105, 95, 100, 1000)
        prev_close = 100

        tr = atr._true_range(candle, prev_close)

        # TR = max(H-L, |H-PC|, |L-PC|) = max(10, 5, 5) = 10
        assert tr == 10

    def test_true_range_gap_up(self, mock_fetcher):
        """Test True Range for a gap up candle."""
        atr = ATRCalculator(mock_fetcher)

        # Gap up: prev_close=100, today O=110, H=115, L=108, C=112
        candle = Candle(1000, 110, 115, 108, 112, 1000)
        prev_close = 100

        tr = atr._true_range(candle, prev_close)

        # TR = max(H-L, |H-PC|, |L-PC|) = max(7, 15, 8) = 15
        assert tr == 15

    def test_true_range_gap_down(self, mock_fetcher):
        """Test True Range for a gap down candle."""
        atr = ATRCalculator(mock_fetcher)

        # Gap down: prev_close=100, today O=90, H=92, L=85, C=88
        candle = Candle(1000, 90, 92, 85, 88, 1000)
        prev_close = 100

        tr = atr._true_range(candle, prev_close)

        # TR = max(H-L, |H-PC|, |L-PC|) = max(7, 8, 15) = 15
        assert tr == 15

    def test_calculate_from_candles(self, mock_fetcher):
        """Test ATR calculation from candle list."""
        atr = ATRCalculator(mock_fetcher)

        # Create candles with consistent $10 range
        candles = []
        for i in range(20):
            candles.append(Candle(
                timestamp=i * 1000,
                open=100,
                high=105,
                low=95,
                close=100,
                volume=1000
            ))

        result = atr.calculate_from_candles(candles, period=14)

        # With consistent $10 range, ATR should be ~10
        assert 9 < result < 11

    def test_calculate_uses_fetcher(self, mock_fetcher):
        """Test that calculate() uses the candle fetcher."""
        candles = [Candle(i * 1000, 100, 105, 95, 100, 1000) for i in range(50)]
        mock_fetcher.get_candles.return_value = CandleData(coin="BTC", interval="1h", candles=candles)

        atr = ATRCalculator(mock_fetcher)
        result = atr.calculate("BTC", "1h")

        assert mock_fetcher.get_candles.called
        assert result.coin == "BTC"
        assert result.timeframe == "1h"
        assert result.period == 14
        assert result.atr > 0

    def test_calculate_atr_percentage(self, mock_fetcher):
        """Test that ATR percentage is calculated correctly."""
        candles = [Candle(i * 1000, 1000, 1050, 950, 1000, 1000) for i in range(50)]
        mock_fetcher.get_candles.return_value = CandleData(coin="ETH", interval="1h", candles=candles)

        atr = ATRCalculator(mock_fetcher)
        result = atr.calculate("ETH", "1h")

        # ATR ~100, price 1000, so ATR% ~10%
        assert 5 < result.atr_pct < 15

    def test_calculate_insufficient_candles(self, mock_fetcher):
        """Test handling of insufficient candle data."""
        candles = [Candle(i * 1000, 100, 105, 95, 100, 1000) for i in range(5)]
        mock_fetcher.get_candles.return_value = CandleData(coin="BTC", interval="1h", candles=candles)

        atr = ATRCalculator(mock_fetcher)
        result = atr.calculate("BTC", "1h")

        # Should return default (2% of price)
        assert result.atr_pct == 2.0

    def test_get_position_size_modifier_high_vol(self, mock_fetcher):
        """Test position sizing for high volatility."""
        candles = [Candle(i * 1000, 100, 110, 90, 100, 1000) for i in range(50)]
        mock_fetcher.get_candles.return_value = CandleData(coin="BTC", interval="1h", candles=candles)

        atr = ATRCalculator(mock_fetcher)
        modifier = atr.get_position_size_modifier("BTC", target_risk_pct=2.0)

        # High vol should reduce position size
        assert modifier < 1.0

    def test_get_dynamic_stops_long(self, mock_fetcher):
        """Test dynamic stop calculation for long."""
        candles = [Candle(i * 1000, 100, 105, 95, 100, 1000) for i in range(50)]
        mock_fetcher.get_candles.return_value = CandleData(coin="BTC", interval="1h", candles=candles)

        atr = ATRCalculator(mock_fetcher)
        sl, tp = atr.get_dynamic_stops("BTC", "LONG", 100, sl_multiplier=1.5, tp_multiplier=2.0)

        # SL should be below entry, TP above
        assert sl < 100
        assert tp > 100

    def test_get_dynamic_stops_short(self, mock_fetcher):
        """Test dynamic stop calculation for short."""
        candles = [Candle(i * 1000, 100, 105, 95, 100, 1000) for i in range(50)]
        mock_fetcher.get_candles.return_value = CandleData(coin="BTC", interval="1h", candles=candles)

        atr = ATRCalculator(mock_fetcher)
        sl, tp = atr.get_dynamic_stops("BTC", "SHORT", 100, sl_multiplier=1.5, tp_multiplier=2.0)

        # SL should be above entry, TP below
        assert sl > 100
        assert tp < 100
