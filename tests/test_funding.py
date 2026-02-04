"""Tests for Funding Rate Fetcher."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

from src.technical.funding import FundingRateFetcher, FundingData


class TestFundingData:
    """Tests for FundingData dataclass."""

    def test_is_extreme_long_boundary(self):
        """Test extreme long at boundary (0.0005 = yes, 0.0004 = no)."""
        extreme = FundingData(coin="BTC", current_rate=0.0006, predicted_rate=0.0006, annualized=65.7, timestamp=datetime.now())
        not_extreme = FundingData(coin="BTC", current_rate=0.0004, predicted_rate=0.0004, annualized=43.8, timestamp=datetime.now())

        assert extreme.is_extreme_long is True
        assert not_extreme.is_extreme_long is False

    def test_is_extreme_short_boundary(self):
        """Test extreme short at boundary (-0.0005 = yes, -0.0004 = no)."""
        extreme = FundingData(coin="BTC", current_rate=-0.0006, predicted_rate=-0.0006, annualized=-65.7, timestamp=datetime.now())
        not_extreme = FundingData(coin="BTC", current_rate=-0.0004, predicted_rate=-0.0004, annualized=-43.8, timestamp=datetime.now())

        assert extreme.is_extreme_short is True
        assert not_extreme.is_extreme_short is False

    def test_bias_crowded_long(self):
        data = FundingData(coin="BTC", current_rate=0.001, predicted_rate=0.001, annualized=109.5, timestamp=datetime.now())
        assert data.bias == "crowded_long"

    def test_bias_crowded_short(self):
        data = FundingData(coin="BTC", current_rate=-0.001, predicted_rate=-0.001, annualized=-109.5, timestamp=datetime.now())
        assert data.bias == "crowded_short"

    def test_bias_slight_long(self):
        data = FundingData(coin="BTC", current_rate=0.0002, predicted_rate=0.0002, annualized=21.9, timestamp=datetime.now())
        assert data.bias == "slight_long"

    def test_bias_slight_short(self):
        data = FundingData(coin="BTC", current_rate=-0.0002, predicted_rate=-0.0002, annualized=-21.9, timestamp=datetime.now())
        assert data.bias == "slight_short"

    def test_bias_neutral(self):
        data = FundingData(coin="BTC", current_rate=0.00005, predicted_rate=0.00005, annualized=5.5, timestamp=datetime.now())
        assert data.bias == "neutral"

    def test_contrarian_signal_extreme_long(self):
        data = FundingData(coin="BTC", current_rate=0.001, predicted_rate=0.001, annualized=109.5, timestamp=datetime.now())
        assert data.contrarian_signal == "SHORT"

    def test_contrarian_signal_extreme_short(self):
        data = FundingData(coin="BTC", current_rate=-0.001, predicted_rate=-0.001, annualized=-109.5, timestamp=datetime.now())
        assert data.contrarian_signal == "LONG"

    def test_contrarian_signal_neutral(self):
        data = FundingData(coin="BTC", current_rate=0.0001, predicted_rate=0.0001, annualized=10.95, timestamp=datetime.now())
        assert data.contrarian_signal is None


class TestFundingRateFetcher:
    """Tests for FundingRateFetcher."""

    def test_init_default_cache(self):
        fetcher = FundingRateFetcher()
        assert fetcher.cache_duration == timedelta(seconds=300)

    def test_init_custom_cache(self):
        fetcher = FundingRateFetcher(cache_seconds=600)
        assert fetcher.cache_duration == timedelta(seconds=600)

    def test_get_symbol_known(self):
        fetcher = FundingRateFetcher()
        assert fetcher._get_symbol("BTC") == "BTCUSDT"
        assert fetcher._get_symbol("btc") == "BTCUSDT"
        assert fetcher._get_symbol("ETH") == "ETHUSDT"

    def test_get_symbol_unknown(self):
        fetcher = FundingRateFetcher()
        assert fetcher._get_symbol("NEWCOIN") == "NEWCOINUSDT"

    @patch.object(FundingRateFetcher, '_fetch_ticker')
    @patch.object(FundingRateFetcher, '_fetch_history')
    def test_get_current_success(self, mock_history, mock_ticker):
        """Test successful funding rate fetch."""
        mock_ticker.return_value = {"fundingRate": "0.0001"}
        mock_history.return_value = []

        fetcher = FundingRateFetcher()
        data = fetcher.get_current("BTC")

        assert data.coin == "BTC"
        assert data.current_rate == 0.0001
        # Annualized: 0.0001 * 3 * 365 * 100 = 10.95%
        assert abs(data.annualized - 10.95) < 0.01

    @patch.object(FundingRateFetcher, '_fetch_ticker')
    @patch.object(FundingRateFetcher, '_fetch_history')
    def test_get_current_uses_cache(self, mock_history, mock_ticker):
        """Test that second call uses cache."""
        mock_ticker.return_value = {"fundingRate": "0.0002"}
        mock_history.return_value = []

        fetcher = FundingRateFetcher()

        # First call
        data1 = fetcher.get_current("BTC")
        assert mock_ticker.call_count == 1

        # Second call uses cache
        data2 = fetcher.get_current("BTC")
        assert mock_ticker.call_count == 1
        assert data1.current_rate == data2.current_rate

    @patch.object(FundingRateFetcher, '_fetch_ticker')
    @patch.object(FundingRateFetcher, '_fetch_history')
    def test_get_current_cache_expired(self, mock_history, mock_ticker):
        """Test that expired cache triggers new fetch."""
        mock_ticker.return_value = {"fundingRate": "0.0001"}
        mock_history.return_value = []

        fetcher = FundingRateFetcher(cache_seconds=1)

        # First call
        fetcher.get_current("BTC")

        # Expire cache
        fetcher._cache["BTC"] = (fetcher._cache["BTC"][0], datetime.now() - timedelta(seconds=10))

        # Second call should fetch again
        fetcher.get_current("BTC")
        assert mock_ticker.call_count == 2

    @patch.object(FundingRateFetcher, '_fetch_ticker')
    @patch.object(FundingRateFetcher, '_fetch_history')
    def test_get_current_api_error_returns_cached(self, mock_history, mock_ticker):
        """Test fallback to cached data on API error."""
        mock_ticker.return_value = {"fundingRate": "0.0003"}
        mock_history.return_value = []

        fetcher = FundingRateFetcher()
        data1 = fetcher.get_current("BTC")
        assert data1.current_rate == 0.0003

        # Expire cache
        fetcher._cache["BTC"] = (fetcher._cache["BTC"][0], datetime.now() - timedelta(seconds=600))

        # API fails
        mock_ticker.side_effect = Exception("Network error")

        # Should return cached
        data2 = fetcher.get_current("BTC")
        assert data2.current_rate == 0.0003

    @patch.object(FundingRateFetcher, '_fetch_ticker')
    @patch.object(FundingRateFetcher, '_fetch_history')
    def test_get_current_api_error_no_cache(self, mock_history, mock_ticker):
        """Test returns neutral when API fails and no cache."""
        mock_ticker.side_effect = Exception("Network error")

        fetcher = FundingRateFetcher()
        data = fetcher.get_current("BTC")

        assert data.current_rate == 0.0
        assert data.bias == "neutral"

    @patch.object(FundingRateFetcher, '_fetch_ticker')
    @patch.object(FundingRateFetcher, '_fetch_history')
    def test_should_avoid_direction_long(self, mock_history, mock_ticker):
        """Test avoiding longs when crowded long."""
        mock_ticker.return_value = {"fundingRate": "0.001"}
        mock_history.return_value = []

        fetcher = FundingRateFetcher()
        should_avoid, reason = fetcher.should_avoid_direction("BTC", "LONG")

        assert should_avoid is True
        assert "Crowded longs" in reason

    @patch.object(FundingRateFetcher, '_fetch_ticker')
    @patch.object(FundingRateFetcher, '_fetch_history')
    def test_should_avoid_direction_short(self, mock_history, mock_ticker):
        """Test avoiding shorts when crowded short."""
        mock_ticker.return_value = {"fundingRate": "-0.001"}
        mock_history.return_value = []

        fetcher = FundingRateFetcher()
        should_avoid, reason = fetcher.should_avoid_direction("BTC", "SHORT")

        assert should_avoid is True
        assert "Crowded shorts" in reason

    @patch.object(FundingRateFetcher, '_fetch_ticker')
    @patch.object(FundingRateFetcher, '_fetch_history')
    def test_should_avoid_direction_neutral(self, mock_history, mock_ticker):
        """Test no avoidance when neutral funding."""
        mock_ticker.return_value = {"fundingRate": "0.0001"}
        mock_history.return_value = []

        fetcher = FundingRateFetcher()

        should_avoid_long, _ = fetcher.should_avoid_direction("BTC", "LONG")
        should_avoid_short, _ = fetcher.should_avoid_direction("BTC", "SHORT")

        assert should_avoid_long is False
        assert should_avoid_short is False

    @patch.object(FundingRateFetcher, '_fetch_ticker')
    @patch.object(FundingRateFetcher, '_fetch_history')
    def test_annualized_calculation(self, mock_history, mock_ticker):
        """Test annualized rate calculation."""
        mock_ticker.return_value = {"fundingRate": "0.01"}  # 1% per 8h
        mock_history.return_value = []

        fetcher = FundingRateFetcher()
        data = fetcher.get_current("BTC")

        # 1% * 3 funding periods/day * 365 days = 1095%
        expected = 0.01 * 3 * 365 * 100
        assert abs(data.annualized - expected) < 0.1
