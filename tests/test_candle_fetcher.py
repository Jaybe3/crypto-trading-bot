"""Tests for Candle Data Fetcher."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

from src.technical.candle_fetcher import CandleFetcher, Candle, CandleData


class TestCandle:
    """Tests for Candle dataclass."""

    def test_is_bullish(self):
        bullish = Candle(1000, 100.0, 110.0, 95.0, 105.0, 1000.0)
        bearish = Candle(1000, 105.0, 110.0, 95.0, 100.0, 1000.0)

        assert bullish.is_bullish is True
        assert bearish.is_bullish is False

    def test_body_size(self):
        candle = Candle(1000, 100.0, 110.0, 95.0, 105.0, 1000.0)
        assert candle.body_size == 5.0

    def test_wick_ratio(self):
        # Candle: O=100, H=110, L=95, C=105
        # Total range = 15, body = 5, wicks = 10
        candle = Candle(1000, 100.0, 110.0, 95.0, 105.0, 1000.0)
        assert candle.wick_ratio == pytest.approx(10/15, rel=0.01)

    def test_wick_ratio_doji(self):
        # Doji: O=C, all wick
        candle = Candle(1000, 100.0, 105.0, 95.0, 100.0, 1000.0)
        assert candle.wick_ratio == 1.0

    def test_wick_ratio_zero_range(self):
        candle = Candle(1000, 100.0, 100.0, 100.0, 100.0, 1000.0)
        assert candle.wick_ratio == 0


class TestCandleData:
    """Tests for CandleData dataclass."""

    def test_closes(self):
        candles = [
            Candle(1000, 100.0, 105.0, 98.0, 103.0, 1000.0),
            Candle(2000, 103.0, 108.0, 102.0, 107.0, 1200.0)
        ]
        data = CandleData(coin="BTC", interval="1h", candles=candles)

        assert data.closes() == [103.0, 107.0]

    def test_volumes(self):
        candles = [
            Candle(1000, 100.0, 105.0, 98.0, 103.0, 1000.0),
            Candle(2000, 103.0, 108.0, 102.0, 107.0, 1200.0)
        ]
        data = CandleData(coin="BTC", interval="1h", candles=candles)

        assert data.volumes() == [1000.0, 1200.0]

    def test_highs_lows(self):
        candles = [
            Candle(1000, 100.0, 105.0, 98.0, 103.0, 1000.0),
            Candle(2000, 103.0, 108.0, 102.0, 107.0, 1200.0)
        ]
        data = CandleData(coin="BTC", interval="1h", candles=candles)

        assert data.highs() == [105.0, 108.0]
        assert data.lows() == [98.0, 102.0]


class TestCandleFetcher:
    """Tests for CandleFetcher."""

    def test_init_default(self):
        fetcher = CandleFetcher()
        assert fetcher.cache_duration == timedelta(seconds=60)

    def test_init_custom_cache(self):
        fetcher = CandleFetcher(cache_seconds=120)
        assert fetcher.cache_duration == timedelta(seconds=120)

    def test_get_symbol_known(self):
        fetcher = CandleFetcher()
        assert fetcher._get_symbol("BTC") == "BTCUSDT"
        assert fetcher._get_symbol("btc") == "BTCUSDT"
        assert fetcher._get_symbol("SOL") == "SOLUSDT"

    def test_get_symbol_unknown(self):
        fetcher = CandleFetcher()
        assert fetcher._get_symbol("NEWCOIN") == "NEWCOINUSDT"

    @patch('src.technical.candle_fetcher.requests.get')
    def test_get_candles_success(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "retCode": 0,
            "result": {
                "list": [
                    ["1706919300000", "103", "108", "102", "107", "1200", "128400"],
                    ["1706918400000", "100", "105", "98", "103", "1000", "103000"]
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = CandleFetcher()
        data = fetcher.get_candles("BTC", "1h", limit=2)

        assert data.coin == "BTC"
        assert data.interval == "1h"
        assert len(data.candles) == 2
        # Should be chronological (oldest first after reverse)
        assert data.candles[0].close == 103.0
        assert data.candles[1].close == 107.0

    @patch('src.technical.candle_fetcher.requests.get')
    def test_get_candles_uses_cache(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "retCode": 0,
            "result": {"list": [["1706918400000", "100", "105", "98", "103", "1000", "103000"]]}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = CandleFetcher()

        # First call hits API
        fetcher.get_candles("BTC", "1h")
        assert mock_get.call_count == 1

        # Second call uses cache
        fetcher.get_candles("BTC", "1h")
        assert mock_get.call_count == 1

    @patch('src.technical.candle_fetcher.requests.get')
    def test_get_candles_cache_expired(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "retCode": 0,
            "result": {"list": [["1706918400000", "100", "105", "98", "103", "1000", "103000"]]}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = CandleFetcher(cache_seconds=1)

        # First call
        fetcher.get_candles("BTC", "1h")

        # Expire cache
        fetcher._cache["BTC_1h"].last_updated = datetime.now() - timedelta(seconds=10)

        # Second call should hit API
        fetcher.get_candles("BTC", "1h")
        assert mock_get.call_count == 2

    @patch('src.technical.candle_fetcher.requests.get')
    def test_get_candles_api_error(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.RequestException("Network error")

        fetcher = CandleFetcher()
        data = fetcher.get_candles("BTC", "1h")

        assert data.coin == "BTC"
        assert data.candles == []

    def test_invalid_interval(self):
        fetcher = CandleFetcher()
        data = fetcher.get_candles("BTC", "invalid")
        assert data.candles == []

    @patch('src.technical.candle_fetcher.requests.get')
    def test_get_latest_candle(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "retCode": 0,
            "result": {"list": [
                ["1706919300000", "103", "108", "102", "107", "1200", "128400"],
                ["1706918400000", "100", "105", "98", "103", "1000", "103000"]
            ]}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = CandleFetcher()
        candle = fetcher.get_latest_candle("BTC", "1h")

        assert candle is not None
        assert candle.close == 107.0  # Latest after reverse

    @patch('src.technical.candle_fetcher.requests.get')
    def test_different_intervals_cached_separately(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "retCode": 0,
            "result": {"list": [["1706918400000", "100", "105", "98", "103", "1000", "103000"]]}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = CandleFetcher()

        fetcher.get_candles("BTC", "1h")
        fetcher.get_candles("BTC", "4h")

        # Should be 2 calls (different intervals)
        assert mock_get.call_count == 2
