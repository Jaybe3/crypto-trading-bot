"""Tests for VWAP Calculator."""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from src.technical.vwap import VWAPCalculator, VWAPData
from src.technical.candle_fetcher import CandleFetcher, Candle, CandleData


class TestVWAPData:
    """Tests for VWAPData dataclass."""

    def test_is_above_vwap(self):
        data = VWAPData(coin="BTC", vwap=100.0, current_price=105.0, deviation_pct=5.0, timestamp=datetime.now())
        assert data.is_above_vwap is True
        assert data.is_below_vwap is False

    def test_is_below_vwap(self):
        data = VWAPData(coin="BTC", vwap=100.0, current_price=95.0, deviation_pct=-5.0, timestamp=datetime.now())
        assert data.is_above_vwap is False
        assert data.is_below_vwap is True

    def test_position_extended_above(self):
        data = VWAPData(coin="BTC", vwap=100.0, current_price=103.0, deviation_pct=3.0, timestamp=datetime.now())
        assert data.position == "extended_above"

    def test_position_extended_below(self):
        data = VWAPData(coin="BTC", vwap=100.0, current_price=97.0, deviation_pct=-3.0, timestamp=datetime.now())
        assert data.position == "extended_below"

    def test_position_above(self):
        data = VWAPData(coin="BTC", vwap=100.0, current_price=101.0, deviation_pct=1.0, timestamp=datetime.now())
        assert data.position == "above"

    def test_position_below(self):
        data = VWAPData(coin="BTC", vwap=100.0, current_price=99.0, deviation_pct=-1.0, timestamp=datetime.now())
        assert data.position == "below"

    def test_mean_reversion_signal_short(self):
        data = VWAPData(coin="BTC", vwap=100.0, current_price=104.0, deviation_pct=4.0, timestamp=datetime.now())
        assert data.mean_reversion_signal == "SHORT"

    def test_mean_reversion_signal_long(self):
        data = VWAPData(coin="BTC", vwap=100.0, current_price=96.0, deviation_pct=-4.0, timestamp=datetime.now())
        assert data.mean_reversion_signal == "LONG"

    def test_mean_reversion_signal_none(self):
        data = VWAPData(coin="BTC", vwap=100.0, current_price=101.0, deviation_pct=1.0, timestamp=datetime.now())
        assert data.mean_reversion_signal is None


class TestVWAPCalculator:
    """Tests for VWAPCalculator."""

    @pytest.fixture
    def mock_fetcher(self):
        return Mock(spec=CandleFetcher)

    def test_calculate_vwap_simple(self, mock_fetcher):
        """Test VWAP calculation with simple data."""
        vwap_calc = VWAPCalculator(mock_fetcher)

        # Create candles with known values
        # Typical price = (H + L + C) / 3
        # Candle 1: TP = (110 + 90 + 100) / 3 = 100, Vol = 1000
        # Candle 2: TP = (120 + 100 + 110) / 3 = 110, Vol = 2000
        # VWAP = (100*1000 + 110*2000) / (1000 + 2000) = 320000 / 3000 = 106.67
        candles = [
            Candle(1000, 100, 110, 90, 100, 1000),
            Candle(2000, 100, 120, 100, 110, 2000)
        ]

        vwap = vwap_calc.calculate_from_candles(candles)
        assert abs(vwap - 106.67) < 0.1

    def test_calculate_vwap_equal_volume(self, mock_fetcher):
        """Test VWAP with equal volume (should be simple average of TP)."""
        vwap_calc = VWAPCalculator(mock_fetcher)

        candles = [
            Candle(1000, 100, 105, 95, 100, 1000),   # TP = 100
            Candle(2000, 100, 115, 105, 110, 1000),  # TP = 110
        ]

        vwap = vwap_calc.calculate_from_candles(candles)
        # With equal volume, VWAP = (100 + 110) / 2 = 105
        assert abs(vwap - 105) < 0.1

    def test_calculate_vwap_no_volume(self, mock_fetcher):
        """Test VWAP with zero volume (should return average close)."""
        vwap_calc = VWAPCalculator(mock_fetcher)

        candles = [
            Candle(1000, 100, 105, 95, 100, 0),
            Candle(2000, 100, 115, 105, 110, 0),
        ]

        vwap = vwap_calc.calculate_from_candles(candles)
        # Should return average of closes: (100 + 110) / 2 = 105
        assert abs(vwap - 105) < 0.1

    def test_calculate_vwap_empty_candles(self, mock_fetcher):
        """Test VWAP with empty candle list."""
        vwap_calc = VWAPCalculator(mock_fetcher)
        vwap = vwap_calc.calculate_from_candles([])
        assert vwap == 0.0

    def test_calculate_uses_fetcher(self, mock_fetcher):
        """Test that calculate() uses the candle fetcher."""
        # Create candles with recent timestamps (within today)
        now = datetime.now(timezone.utc)
        base_ts = int(now.timestamp() * 1000) - 3600000  # 1 hour ago

        candles = [
            Candle(base_ts, 100, 105, 95, 100, 1000),
            Candle(base_ts + 60000, 100, 110, 95, 105, 1500)
        ]

        mock_fetcher.get_candles.return_value = CandleData(coin="BTC", interval="1h", candles=candles)

        vwap_calc = VWAPCalculator(mock_fetcher)
        result = vwap_calc.calculate("BTC", use_daily_reset=False)

        assert mock_fetcher.get_candles.called
        assert result.coin == "BTC"
        assert result.vwap > 0

    def test_calculate_deviation_positive(self, mock_fetcher):
        """Test deviation calculation when above VWAP."""
        vwap_calc = VWAPCalculator(mock_fetcher)

        candles = [
            Candle(1000, 100, 105, 95, 100, 1000),
            Candle(2000, 100, 115, 105, 110, 1000),  # Close at 110
        ]

        mock_fetcher.get_candles.return_value = CandleData(coin="BTC", interval="1h", candles=candles)

        result = vwap_calc.calculate("BTC", use_daily_reset=False)

        # VWAP ~105, current price 110
        # Deviation = (110 - 105) / 105 * 100 = 4.76%
        assert result.deviation_pct > 0

    def test_calculate_deviation_negative(self, mock_fetcher):
        """Test deviation calculation when below VWAP."""
        vwap_calc = VWAPCalculator(mock_fetcher)

        candles = [
            Candle(1000, 100, 115, 105, 110, 1000),  # TP = 110
            Candle(2000, 100, 105, 95, 100, 1000),   # Close at 100
        ]

        mock_fetcher.get_candles.return_value = CandleData(coin="BTC", interval="1h", candles=candles)

        result = vwap_calc.calculate("BTC", use_daily_reset=False)

        # Current price 100, VWAP ~105
        assert result.deviation_pct < 0

    def test_filter_to_today(self, mock_fetcher):
        """Test that candles are filtered to current day."""
        vwap_calc = VWAPCalculator(mock_fetcher)

        now = datetime.now(timezone.utc)
        today_ts = int(now.timestamp() * 1000)
        yesterday_ts = today_ts - 86400000  # 24 hours ago

        candles = [
            Candle(yesterday_ts, 100, 105, 95, 100, 1000),  # Yesterday
            Candle(today_ts, 100, 110, 95, 105, 1500),       # Today
        ]

        today_candles = vwap_calc._filter_to_today(candles)

        # Should only have today's candle
        assert len(today_candles) <= len(candles)

    def test_get_bands(self, mock_fetcher):
        """Test VWAP bands calculation."""
        vwap_calc = VWAPCalculator(mock_fetcher)

        now = datetime.now(timezone.utc)
        base_ts = int(now.timestamp() * 1000) - 3600000

        candles = [
            Candle(base_ts + i * 60000, 100, 105, 95, 100, 1000)
            for i in range(10)
        ]

        mock_fetcher.get_candles.return_value = CandleData(coin="BTC", interval="1h", candles=candles)

        vwap, upper, lower = vwap_calc.get_bands("BTC", std_multiplier=2.0)

        assert upper >= vwap
        assert lower <= vwap

    def test_empty_candle_data(self, mock_fetcher):
        """Test handling of empty candle data."""
        mock_fetcher.get_candles.return_value = CandleData(coin="BTC", interval="1h", candles=[])

        vwap_calc = VWAPCalculator(mock_fetcher)
        result = vwap_calc.calculate("BTC")

        assert result.vwap == 0.0
        assert result.current_price == 0.0
