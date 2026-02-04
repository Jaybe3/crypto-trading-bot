"""Tests for Volume Profile Calculator."""
import pytest
from datetime import datetime
from unittest.mock import Mock

from src.technical.volume_profile import VolumeProfileCalculator, VolumeProfile
from src.technical.candle_fetcher import CandleFetcher, Candle, CandleData


class TestVolumeProfile:
    """Tests for VolumeProfile dataclass."""

    def test_is_in_value_area_true(self):
        profile = VolumeProfile(
            coin="BTC",
            poc=100.0,
            value_area_high=105.0,
            value_area_low=95.0,
            hvn_levels=[100.0],
            lvn_levels=[90.0],
            current_price=102.0,
            total_volume=10000
        )
        assert profile.is_in_value_area is True

    def test_is_in_value_area_false(self):
        profile = VolumeProfile(
            coin="BTC",
            poc=100.0,
            value_area_high=105.0,
            value_area_low=95.0,
            hvn_levels=[100.0],
            lvn_levels=[90.0],
            current_price=110.0,
            total_volume=10000
        )
        assert profile.is_in_value_area is False

    def test_position_vs_poc_above(self):
        profile = VolumeProfile(
            coin="BTC",
            poc=100.0,
            value_area_high=105.0,
            value_area_low=95.0,
            hvn_levels=[],
            lvn_levels=[],
            current_price=102.0,
            total_volume=10000
        )
        assert profile.position_vs_poc == "above_poc"

    def test_position_vs_poc_below(self):
        profile = VolumeProfile(
            coin="BTC",
            poc=100.0,
            value_area_high=105.0,
            value_area_low=95.0,
            hvn_levels=[],
            lvn_levels=[],
            current_price=98.0,
            total_volume=10000
        )
        assert profile.position_vs_poc == "below_poc"

    def test_position_vs_poc_at(self):
        profile = VolumeProfile(
            coin="BTC",
            poc=100.0,
            value_area_high=105.0,
            value_area_low=95.0,
            hvn_levels=[],
            lvn_levels=[],
            current_price=100.0,
            total_volume=10000
        )
        assert profile.position_vs_poc == "at_poc"

    def test_distance_to_poc_pct(self):
        profile = VolumeProfile(
            coin="BTC",
            poc=100.0,
            value_area_high=105.0,
            value_area_low=95.0,
            hvn_levels=[],
            lvn_levels=[],
            current_price=105.0,
            total_volume=10000
        )
        assert profile.distance_to_poc_pct == 5.0

    def test_value_area_width_pct(self):
        profile = VolumeProfile(
            coin="BTC",
            poc=100.0,
            value_area_high=110.0,
            value_area_low=100.0,
            hvn_levels=[],
            lvn_levels=[],
            current_price=105.0,
            total_volume=10000
        )
        # (110 - 100) / 100 * 100 = 10%
        assert profile.value_area_width_pct == 10.0

    def test_nearest_hvn(self):
        profile = VolumeProfile(
            coin="BTC",
            poc=100.0,
            value_area_high=110.0,
            value_area_low=90.0,
            hvn_levels=[95.0, 100.0, 108.0],
            lvn_levels=[],
            current_price=102.0,
            total_volume=10000
        )
        assert profile.nearest_hvn == 100.0

    def test_nearest_hvn_empty(self):
        profile = VolumeProfile(
            coin="BTC",
            poc=100.0,
            value_area_high=110.0,
            value_area_low=90.0,
            hvn_levels=[],
            lvn_levels=[],
            current_price=102.0,
            total_volume=10000
        )
        assert profile.nearest_hvn is None

    def test_nearest_lvn(self):
        profile = VolumeProfile(
            coin="BTC",
            poc=100.0,
            value_area_high=110.0,
            value_area_low=90.0,
            hvn_levels=[],
            lvn_levels=[92.0, 97.0, 107.0],
            current_price=99.0,
            total_volume=10000
        )
        assert profile.nearest_lvn == 97.0


class TestVolumeProfileCalculator:
    """Tests for VolumeProfileCalculator."""

    @pytest.fixture
    def mock_fetcher(self):
        return Mock(spec=CandleFetcher)

    def test_init_defaults(self, mock_fetcher):
        calculator = VolumeProfileCalculator(mock_fetcher)
        assert calculator.num_levels == 50
        assert calculator.value_area_pct == 0.70

    def test_init_custom(self, mock_fetcher):
        calculator = VolumeProfileCalculator(mock_fetcher, num_levels=100, value_area_pct=0.80)
        assert calculator.num_levels == 100
        assert calculator.value_area_pct == 0.80

    def test_calculate_poc(self, mock_fetcher):
        calculator = VolumeProfileCalculator(mock_fetcher)

        volume_dist = {
            90.0: 100,
            95.0: 200,
            100.0: 500,  # Highest volume
            105.0: 300,
            110.0: 100
        }

        poc = calculator._calculate_poc(volume_dist)
        assert poc == 100.0

    def test_calculate_poc_empty(self, mock_fetcher):
        calculator = VolumeProfileCalculator(mock_fetcher)
        poc = calculator._calculate_poc({})
        assert poc == 0.0

    def test_calculate_value_area(self, mock_fetcher):
        calculator = VolumeProfileCalculator(mock_fetcher, value_area_pct=0.70)

        # Create distribution where 70% is centered around 100
        volume_dist = {
            90.0: 50,
            95.0: 100,
            100.0: 500,  # POC
            105.0: 150,
            110.0: 50
        }

        va_low, va_high = calculator._calculate_value_area(volume_dist)

        # Value area should include POC
        assert va_low <= 100.0
        assert va_high >= 100.0

    def test_find_hvn_levels(self, mock_fetcher):
        calculator = VolumeProfileCalculator(mock_fetcher)

        # Average = 200, threshold = 300
        volume_dist = {
            90.0: 100,
            95.0: 100,
            100.0: 500,  # HVN
            105.0: 400,  # HVN
            110.0: 100
        }

        hvn = calculator._find_hvn_levels(volume_dist)

        assert 100.0 in hvn
        assert 105.0 in hvn

    def test_find_lvn_levels(self, mock_fetcher):
        calculator = VolumeProfileCalculator(mock_fetcher)

        # Average = 200, threshold = 100
        volume_dist = {
            90.0: 50,   # LVN
            95.0: 200,
            100.0: 500,
            105.0: 200,
            110.0: 50   # LVN
        }

        lvn = calculator._find_lvn_levels(volume_dist)

        assert 90.0 in lvn
        assert 110.0 in lvn

    def test_build_volume_distribution(self, mock_fetcher):
        calculator = VolumeProfileCalculator(mock_fetcher, num_levels=10)

        candles = [
            Candle(1000, 100, 105, 95, 100, 1000),
            Candle(2000, 100, 110, 100, 105, 2000),
            Candle(3000, 105, 108, 102, 106, 1500),
        ]

        volume_dist = calculator._build_volume_distribution(candles)

        assert len(volume_dist) > 0
        assert sum(volume_dist.values()) > 0

    def test_build_volume_distribution_empty(self, mock_fetcher):
        calculator = VolumeProfileCalculator(mock_fetcher)
        volume_dist = calculator._build_volume_distribution([])
        assert volume_dist == {}

    def test_calculate_from_candles(self, mock_fetcher):
        calculator = VolumeProfileCalculator(mock_fetcher, num_levels=20)

        # Create candles with volume concentrated at certain levels
        candles = []
        for i in range(50):
            # More volume around price 100
            base_price = 100 + (i % 10) - 5
            vol = 2000 if abs(base_price - 100) < 2 else 500
            candles.append(Candle(
                i * 1000, base_price, base_price + 2, base_price - 2, base_price, vol
            ))

        profile = calculator.calculate_from_candles(candles, "TEST")

        assert profile.coin == "TEST"
        assert profile.poc > 0
        assert profile.total_volume > 0

    def test_calculate_uses_fetcher(self, mock_fetcher):
        candles = [
            Candle(i * 1000, 100, 105, 95, 100, 1000)
            for i in range(50)
        ]
        mock_fetcher.get_candles.return_value = CandleData(
            coin="BTC", interval="1h", candles=candles
        )

        calculator = VolumeProfileCalculator(mock_fetcher)
        profile = calculator.calculate("BTC")

        assert mock_fetcher.get_candles.called
        assert profile.coin == "BTC"

    def test_calculate_empty_candles(self, mock_fetcher):
        mock_fetcher.get_candles.return_value = CandleData(
            coin="BTC", interval="1h", candles=[]
        )

        calculator = VolumeProfileCalculator(mock_fetcher)
        profile = calculator.calculate("BTC")

        assert profile.coin == "BTC"
        assert profile.poc == 0.0
        assert profile.total_volume == 0.0

    def test_get_candle_levels(self, mock_fetcher):
        calculator = VolumeProfileCalculator(mock_fetcher)

        candle = Candle(1000, 100, 110, 90, 100, 1000)
        levels = calculator._get_candle_levels(candle, 80, 5)

        # Should have multiple levels for a candle spanning 90-110
        assert len(levels) > 1

    def test_empty_profile(self, mock_fetcher):
        calculator = VolumeProfileCalculator(mock_fetcher)

        profile = calculator._empty_profile("TEST", 100.0)

        assert profile.coin == "TEST"
        assert profile.poc == 100.0
        assert profile.hvn_levels == []
        assert profile.lvn_levels == []
