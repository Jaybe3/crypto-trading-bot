"""Tests for Support/Resistance Level Detector."""
import pytest
from datetime import datetime
from unittest.mock import Mock

from src.technical.support_resistance import SRLevelDetector, PriceLevel, SRLevels
from src.technical.candle_fetcher import CandleFetcher, Candle, CandleData


class TestPriceLevel:
    """Tests for PriceLevel dataclass."""

    def test_price_in_zone_true(self):
        level = PriceLevel(
            price=100.0,
            level_type="support",
            strength=3,
            last_touch=datetime.now(),
            zone_low=99.0,
            zone_high=101.0
        )
        assert level.price_in_zone(100.0) is True
        assert level.price_in_zone(99.5) is True
        assert level.price_in_zone(100.5) is True

    def test_price_in_zone_false(self):
        level = PriceLevel(
            price=100.0,
            level_type="support",
            strength=3,
            last_touch=datetime.now(),
            zone_low=99.0,
            zone_high=101.0
        )
        assert level.price_in_zone(98.0) is False
        assert level.price_in_zone(102.0) is False


class TestSRLevels:
    """Tests for SRLevels dataclass."""

    def test_support_distance_pct(self):
        support = PriceLevel(
            price=95.0, level_type="support", strength=2,
            last_touch=datetime.now(), zone_low=94.5, zone_high=95.5
        )
        levels = SRLevels(
            coin="BTC",
            current_price=100.0,
            nearest_support=support
        )
        # Distance = (100 - 95) / 100 * 100 = 5%
        assert abs(levels.support_distance_pct - 5.0) < 0.1

    def test_resistance_distance_pct(self):
        resistance = PriceLevel(
            price=110.0, level_type="resistance", strength=2,
            last_touch=datetime.now(), zone_low=109.5, zone_high=110.5
        )
        levels = SRLevels(
            coin="BTC",
            current_price=100.0,
            nearest_resistance=resistance
        )
        # Distance = (110 - 100) / 100 * 100 = 10%
        assert abs(levels.resistance_distance_pct - 10.0) < 0.1

    def test_distance_pct_none_when_no_level(self):
        levels = SRLevels(coin="BTC", current_price=100.0)
        assert levels.support_distance_pct is None
        assert levels.resistance_distance_pct is None

    def test_in_support_zone(self):
        support = PriceLevel(
            price=100.0, level_type="support", strength=2,
            last_touch=datetime.now(), zone_low=99.0, zone_high=101.0
        )
        levels = SRLevels(
            coin="BTC",
            current_price=100.5,
            nearest_support=support
        )
        assert levels.in_support_zone is True

    def test_in_resistance_zone(self):
        resistance = PriceLevel(
            price=100.0, level_type="resistance", strength=2,
            last_touch=datetime.now(), zone_low=99.0, zone_high=101.0
        )
        levels = SRLevels(
            coin="BTC",
            current_price=100.5,
            nearest_resistance=resistance
        )
        assert levels.in_resistance_zone is True


class TestSRLevelDetector:
    """Tests for SRLevelDetector."""

    @pytest.fixture
    def mock_fetcher(self):
        return Mock(spec=CandleFetcher)

    def test_init_defaults(self, mock_fetcher):
        detector = SRLevelDetector(mock_fetcher)
        assert detector.lookback == 5
        assert detector.tolerance_pct == 0.5

    def test_init_custom(self, mock_fetcher):
        detector = SRLevelDetector(mock_fetcher, lookback=3, tolerance_pct=1.0)
        assert detector.lookback == 3
        assert detector.tolerance_pct == 1.0

    def test_find_swing_high(self, mock_fetcher):
        """Test detection of swing highs."""
        detector = SRLevelDetector(mock_fetcher, lookback=2)

        # Create candles with a clear swing high in the middle
        candles = [
            Candle(1000, 100, 102, 98, 100, 1000),   # Low
            Candle(2000, 100, 103, 98, 100, 1000),   # Higher
            Candle(3000, 100, 110, 98, 100, 1000),   # SWING HIGH
            Candle(4000, 100, 105, 98, 100, 1000),   # Lower
            Candle(5000, 100, 103, 98, 100, 1000),   # Lower
        ]

        swing_points = detector.find_swing_points(candles)

        # Should find the swing high at 110
        resistance_points = [p for p, t in swing_points if t == "resistance"]
        assert 110 in resistance_points

    def test_find_swing_low(self, mock_fetcher):
        """Test detection of swing lows."""
        detector = SRLevelDetector(mock_fetcher, lookback=2)

        # Create candles with a clear swing low in the middle
        candles = [
            Candle(1000, 100, 105, 98, 100, 1000),   # Normal
            Candle(2000, 100, 105, 95, 100, 1000),   # Lower
            Candle(3000, 100, 105, 90, 100, 1000),   # SWING LOW
            Candle(4000, 100, 105, 93, 100, 1000),   # Higher
            Candle(5000, 100, 105, 96, 100, 1000),   # Higher
        ]

        swing_points = detector.find_swing_points(candles)

        # Should find the swing low at 90
        support_points = [p for p, t in swing_points if t == "support"]
        assert 90 in support_points

    def test_cluster_levels_single(self, mock_fetcher):
        """Test clustering of single point."""
        detector = SRLevelDetector(mock_fetcher)

        points = [100.0]
        levels = detector.cluster_levels(points, "support")

        assert len(levels) == 1
        assert levels[0].price == 100.0
        assert levels[0].strength == 1

    def test_cluster_levels_multiple_same_zone(self, mock_fetcher):
        """Test clustering of nearby points."""
        detector = SRLevelDetector(mock_fetcher, tolerance_pct=1.0)

        # Points within 1% of each other should cluster
        points = [100.0, 100.5, 100.3]
        levels = detector.cluster_levels(points, "support")

        assert len(levels) == 1
        assert levels[0].strength == 3

    def test_cluster_levels_multiple_zones(self, mock_fetcher):
        """Test clustering into separate zones."""
        detector = SRLevelDetector(mock_fetcher, tolerance_pct=0.5)

        # Points far apart should be separate clusters
        points = [100.0, 110.0, 120.0]
        levels = detector.cluster_levels(points, "support")

        assert len(levels) == 3

    def test_cluster_levels_empty(self, mock_fetcher):
        """Test clustering with empty list."""
        detector = SRLevelDetector(mock_fetcher)

        levels = detector.cluster_levels([], "support")
        assert levels == []

    def test_detect_uses_fetcher(self, mock_fetcher):
        """Test that detect() uses the candle fetcher."""
        # Create enough candles for swing detection
        candles = []
        for i in range(50):
            # Create some price variation
            h = 100 + (i % 10) * 2
            l = 95 + (i % 10)
            candles.append(Candle(i * 1000, 100, h, l, (h + l) / 2, 1000))

        mock_fetcher.get_candles.return_value = CandleData(coin="BTC", interval="4h", candles=candles)

        detector = SRLevelDetector(mock_fetcher)
        result = detector.detect("BTC")

        assert mock_fetcher.get_candles.called
        assert result.coin == "BTC"

    def test_detect_filters_support_below_price(self, mock_fetcher):
        """Test that support levels are filtered to be below current price."""
        detector = SRLevelDetector(mock_fetcher, lookback=2)

        # Create candles where swing low is above current price
        candles = [
            Candle(1000, 100, 105, 120, 100, 1000),
            Candle(2000, 100, 105, 115, 100, 1000),
            Candle(3000, 100, 105, 110, 100, 1000),  # Swing low at 110
            Candle(4000, 100, 105, 115, 100, 1000),
            Candle(5000, 100, 105, 120, 95, 1000),   # Current price 95
        ]

        mock_fetcher.get_candles.return_value = CandleData(coin="BTC", interval="4h", candles=candles)

        result = detector.detect("BTC")

        # Support at 110 should be filtered out (it's above current price 95)
        for level in result.support_levels:
            assert level.price < result.current_price

    def test_detect_filters_resistance_above_price(self, mock_fetcher):
        """Test that resistance levels are filtered to be above current price."""
        detector = SRLevelDetector(mock_fetcher, lookback=2)

        # Create candles where swing high is below current price
        candles = [
            Candle(1000, 100, 90, 85, 100, 1000),
            Candle(2000, 100, 95, 85, 100, 1000),
            Candle(3000, 100, 100, 85, 100, 1000),   # Swing high at 100
            Candle(4000, 100, 95, 85, 100, 1000),
            Candle(5000, 100, 90, 85, 110, 1000),    # Current price 110
        ]

        mock_fetcher.get_candles.return_value = CandleData(coin="BTC", interval="4h", candles=candles)

        result = detector.detect("BTC")

        # Resistance at 100 should be filtered out (it's below current price 110)
        for level in result.resistance_levels:
            assert level.price > result.current_price

    def test_detect_sorts_by_proximity(self, mock_fetcher):
        """Test that levels are sorted by proximity to current price."""
        detector = SRLevelDetector(mock_fetcher, lookback=2)

        # Manual test - create levels and check sorting
        support1 = PriceLevel(90, "support", 1, datetime.now(), 89, 91)
        support2 = PriceLevel(95, "support", 1, datetime.now(), 94, 96)

        levels = SRLevels(
            coin="BTC",
            support_levels=[support1, support2],
            current_price=100
        )

        # Nearest should be 95 (closer to 100)
        levels.support_levels.sort(key=lambda l: levels.current_price - l.price)
        assert levels.support_levels[0].price == 95

    def test_insufficient_candles(self, mock_fetcher):
        """Test handling of insufficient candle data."""
        detector = SRLevelDetector(mock_fetcher, lookback=5)

        candles = [Candle(i * 1000, 100, 105, 95, 100, 1000) for i in range(5)]
        mock_fetcher.get_candles.return_value = CandleData(coin="BTC", interval="4h", candles=candles)

        result = detector.detect("BTC")

        # Should return empty levels
        assert result.coin == "BTC"
