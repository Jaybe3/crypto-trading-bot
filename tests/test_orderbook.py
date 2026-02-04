"""Tests for Order Book Analyzer."""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.technical.orderbook import OrderBookAnalyzer, OrderBookDepth, PriceWall


class TestPriceWall:
    """Tests for PriceWall dataclass."""

    def test_is_bid_wall(self):
        wall = PriceWall(price=100.0, size=10000, side="bid", distance_pct=1.0)
        assert wall.is_bid_wall is True
        assert wall.is_ask_wall is False

    def test_is_ask_wall(self):
        wall = PriceWall(price=102.0, size=10000, side="ask", distance_pct=1.0)
        assert wall.is_bid_wall is False
        assert wall.is_ask_wall is True


class TestOrderBookDepth:
    """Tests for OrderBookDepth dataclass."""

    def test_bias_strong_bid(self):
        depth = OrderBookDepth(
            coin="BTC",
            bid_volume=10000,
            ask_volume=5000,
            imbalance=0.33,  # (10000-5000)/(10000+5000) = 0.33
            bid_walls=[],
            ask_walls=[],
            spread_pct=0.01,
            best_bid=100.0,
            best_ask=100.01,
            mid_price=100.005
        )
        assert depth.bias == "strong_bid"

    def test_bias_strong_ask(self):
        depth = OrderBookDepth(
            coin="BTC",
            bid_volume=5000,
            ask_volume=10000,
            imbalance=-0.33,
            bid_walls=[],
            ask_walls=[],
            spread_pct=0.01,
            best_bid=100.0,
            best_ask=100.01,
            mid_price=100.005
        )
        assert depth.bias == "strong_ask"

    def test_bias_balanced(self):
        depth = OrderBookDepth(
            coin="BTC",
            bid_volume=10000,
            ask_volume=9000,
            imbalance=0.05,
            bid_walls=[],
            ask_walls=[],
            spread_pct=0.01,
            best_bid=100.0,
            best_ask=100.01,
            mid_price=100.005
        )
        assert depth.bias == "balanced"

    def test_is_bullish(self):
        depth = OrderBookDepth(
            coin="BTC",
            bid_volume=10000,
            ask_volume=8000,
            imbalance=0.11,
            bid_walls=[],
            ask_walls=[],
            spread_pct=0.01,
            best_bid=100.0,
            best_ask=100.01,
            mid_price=100.005
        )
        assert depth.is_bullish is True
        assert depth.is_bearish is False

    def test_is_bearish(self):
        depth = OrderBookDepth(
            coin="BTC",
            bid_volume=8000,
            ask_volume=10000,
            imbalance=-0.11,
            bid_walls=[],
            ask_walls=[],
            spread_pct=0.01,
            best_bid=100.0,
            best_ask=100.01,
            mid_price=100.005
        )
        assert depth.is_bullish is False
        assert depth.is_bearish is True

    def test_has_bid_walls(self):
        depth = OrderBookDepth(
            coin="BTC",
            bid_volume=10000,
            ask_volume=10000,
            imbalance=0.0,
            bid_walls=[PriceWall(99.0, 5000, "bid", 1.0)],
            ask_walls=[],
            spread_pct=0.01,
            best_bid=100.0,
            best_ask=100.01,
            mid_price=100.005
        )
        assert depth.has_bid_walls is True
        assert depth.has_ask_walls is False

    def test_has_ask_walls(self):
        depth = OrderBookDepth(
            coin="BTC",
            bid_volume=10000,
            ask_volume=10000,
            imbalance=0.0,
            bid_walls=[],
            ask_walls=[PriceWall(101.0, 5000, "ask", 1.0)],
            spread_pct=0.01,
            best_bid=100.0,
            best_ask=100.01,
            mid_price=100.005
        )
        assert depth.has_bid_walls is False
        assert depth.has_ask_walls is True

    def test_nearest_bid_wall(self):
        walls = [
            PriceWall(98.0, 5000, "bid", 2.0),
            PriceWall(99.0, 5000, "bid", 1.0),
            PriceWall(97.0, 5000, "bid", 3.0),
        ]
        depth = OrderBookDepth(
            coin="BTC",
            bid_volume=10000,
            ask_volume=10000,
            imbalance=0.0,
            bid_walls=walls,
            ask_walls=[],
            spread_pct=0.01,
            best_bid=100.0,
            best_ask=100.01,
            mid_price=100.005
        )
        assert depth.nearest_bid_wall.price == 99.0

    def test_nearest_bid_wall_none(self):
        depth = OrderBookDepth(
            coin="BTC",
            bid_volume=10000,
            ask_volume=10000,
            imbalance=0.0,
            bid_walls=[],
            ask_walls=[],
            spread_pct=0.01,
            best_bid=100.0,
            best_ask=100.01,
            mid_price=100.005
        )
        assert depth.nearest_bid_wall is None

    def test_nearest_ask_wall(self):
        walls = [
            PriceWall(102.0, 5000, "ask", 2.0),
            PriceWall(101.0, 5000, "ask", 1.0),
            PriceWall(103.0, 5000, "ask", 3.0),
        ]
        depth = OrderBookDepth(
            coin="BTC",
            bid_volume=10000,
            ask_volume=10000,
            imbalance=0.0,
            bid_walls=[],
            ask_walls=walls,
            spread_pct=0.01,
            best_bid=100.0,
            best_ask=100.01,
            mid_price=100.005
        )
        assert depth.nearest_ask_wall.price == 101.0


class TestOrderBookAnalyzer:
    """Tests for OrderBookAnalyzer."""

    def test_init_defaults(self):
        analyzer = OrderBookAnalyzer()
        assert analyzer.wall_multiplier == 3.0
        assert analyzer.CACHE_TTL == 5

    def test_init_custom(self):
        analyzer = OrderBookAnalyzer(wall_multiplier=5.0)
        assert analyzer.wall_multiplier == 5.0

    def test_calculate_imbalance_positive(self):
        analyzer = OrderBookAnalyzer()
        imbalance = analyzer.calculate_imbalance(10000, 5000)
        # (10000 - 5000) / (10000 + 5000) = 0.333
        assert abs(imbalance - 0.333) < 0.01

    def test_calculate_imbalance_negative(self):
        analyzer = OrderBookAnalyzer()
        imbalance = analyzer.calculate_imbalance(5000, 10000)
        # (5000 - 10000) / (5000 + 10000) = -0.333
        assert abs(imbalance - (-0.333)) < 0.01

    def test_calculate_imbalance_zero(self):
        analyzer = OrderBookAnalyzer()
        imbalance = analyzer.calculate_imbalance(0, 0)
        assert imbalance == 0.0

    def test_calculate_imbalance_balanced(self):
        analyzer = OrderBookAnalyzer()
        imbalance = analyzer.calculate_imbalance(10000, 10000)
        assert imbalance == 0.0

    def test_detect_walls_finds_large_orders(self):
        analyzer = OrderBookAnalyzer(wall_multiplier=3.0)

        # Average = (100+100+100+100+1000)/5 = 280, threshold = 840
        orders = [
            (99.0, 100),
            (98.0, 100),
            (97.0, 1000),  # Wall - well above 3x average
            (96.0, 100),
            (95.0, 100),
        ]

        walls = analyzer.detect_walls(orders, "bid", 100.0)

        assert len(walls) == 1
        assert walls[0].price == 97.0
        assert walls[0].side == "bid"

    def test_detect_walls_empty_orders(self):
        analyzer = OrderBookAnalyzer()
        walls = analyzer.detect_walls([], "bid", 100.0)
        assert walls == []

    def test_detect_walls_no_walls(self):
        analyzer = OrderBookAnalyzer(wall_multiplier=3.0)

        # All similar sizes
        orders = [
            (99.0, 100),
            (98.0, 100),
            (97.0, 100),
        ]

        walls = analyzer.detect_walls(orders, "bid", 100.0)
        assert len(walls) == 0

    def test_get_spread(self):
        analyzer = OrderBookAnalyzer()
        spread = analyzer.get_spread(100.0, 100.1)
        # (100.1 - 100.0) / 100.05 * 100 = 0.0999%
        assert abs(spread - 0.0999) < 0.01

    def test_get_spread_zero(self):
        analyzer = OrderBookAnalyzer()
        spread = analyzer.get_spread(0.0, 100.0)
        assert spread == 0.0

    @patch('src.technical.orderbook.requests.get')
    def test_analyze_success(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {
                "b": [
                    ["100.0", "1000"],
                    ["99.0", "500"],
                ],
                "a": [
                    ["100.1", "800"],
                    ["100.2", "600"],
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        analyzer = OrderBookAnalyzer()
        depth = analyzer.analyze("BTC", use_cache=False)

        assert depth.coin == "BTC"
        assert depth.bid_volume == 1500
        assert depth.ask_volume == 1400
        assert depth.best_bid == 100.0
        assert depth.best_ask == 100.1

    @patch('src.technical.orderbook.requests.get')
    def test_analyze_uses_cache(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {
                "b": [["100.0", "1000"]],
                "a": [["100.1", "1000"]]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        analyzer = OrderBookAnalyzer()

        # First call
        analyzer.analyze("BTC")
        # Second call should use cache
        analyzer.analyze("BTC")

        # Should only be called once
        assert mock_get.call_count == 1

    @patch('src.technical.orderbook.requests.get')
    def test_analyze_api_error_returns_cache(self, mock_get):
        import requests as req
        import time
        mock_get.side_effect = req.RequestException("API Error")

        analyzer = OrderBookAnalyzer()
        cached_depth = OrderBookDepth(
            coin="BTC",
            bid_volume=1000,
            ask_volume=1000,
            imbalance=0.0,
            bid_walls=[],
            ask_walls=[],
            spread_pct=0.01,
            best_bid=100.0,
            best_ask=100.01,
            mid_price=100.005
        )
        analyzer._cache["BTCUSDT"] = (cached_depth, time.time() - 10)  # Expired

        depth = analyzer.analyze("BTC")

        assert depth.coin == "BTC"
        assert depth.bid_volume == 1000

    @patch('src.technical.orderbook.requests.get')
    def test_analyze_api_error_no_cache(self, mock_get):
        import requests as req
        mock_get.side_effect = req.RequestException("API Error")

        analyzer = OrderBookAnalyzer()
        depth = analyzer.analyze("BTC")

        assert depth.coin == "BTC"
        assert depth.bid_volume == 0.0
        assert depth.ask_volume == 0.0

    def test_parse_response_with_walls(self):
        analyzer = OrderBookAnalyzer(wall_multiplier=2.0)

        data = {
            "result": {
                "b": [
                    ["100.0", "100"],
                    ["99.0", "100"],
                    ["98.0", "500"],  # Wall
                ],
                "a": [
                    ["100.1", "100"],
                    ["100.2", "100"],
                    ["100.3", "500"],  # Wall
                ]
            }
        }

        depth = analyzer._parse_response("BTC", data)

        assert depth.has_bid_walls is True
        assert depth.has_ask_walls is True

    def test_empty_depth(self):
        analyzer = OrderBookAnalyzer()
        depth = analyzer._empty_depth("TEST")

        assert depth.coin == "TEST"
        assert depth.bid_volume == 0.0
        assert depth.ask_volume == 0.0
        assert depth.imbalance == 0.0
        assert depth.bid_walls == []
        assert depth.ask_walls == []
