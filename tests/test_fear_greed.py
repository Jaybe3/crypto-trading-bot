"""Tests for Fear & Greed Index fetcher."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

from src.sentiment.fear_greed import FearGreedFetcher, FearGreedData


class TestFearGreedData:
    """Tests for FearGreedData dataclass."""

    def test_extreme_fear_boundary(self):
        """Test extreme fear at boundary (24 = extreme, 25 = not)."""
        extreme = FearGreedData(value=24, classification="Extreme Fear", timestamp=datetime.now())
        not_extreme = FearGreedData(value=25, classification="Fear", timestamp=datetime.now())

        assert extreme.is_extreme_fear is True
        assert not_extreme.is_extreme_fear is False

    def test_extreme_greed_boundary(self):
        """Test extreme greed at boundary (75 = not extreme, 76 = extreme)."""
        not_extreme = FearGreedData(value=75, classification="Greed", timestamp=datetime.now())
        extreme = FearGreedData(value=76, classification="Extreme Greed", timestamp=datetime.now())

        assert not_extreme.is_extreme_greed is False
        assert extreme.is_extreme_greed is True

    def test_neutral_values(self):
        """Test neutral values are neither extreme."""
        neutral = FearGreedData(value=50, classification="Neutral", timestamp=datetime.now())

        assert neutral.is_extreme_fear is False
        assert neutral.is_extreme_greed is False


class TestFearGreedFetcher:
    """Tests for FearGreedFetcher."""

    def test_init_default_ttl(self):
        fetcher = FearGreedFetcher()
        assert fetcher.cache_ttl == timedelta(minutes=60)

    def test_init_custom_ttl(self):
        fetcher = FearGreedFetcher(cache_ttl_minutes=30)
        assert fetcher.cache_ttl == timedelta(minutes=30)

    @patch('src.sentiment.fear_greed.requests.get')
    def test_get_current_success(self, mock_get):
        """Test successful API fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{
                "value": "25",
                "value_classification": "Fear",
                "timestamp": "1706918400"
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = FearGreedFetcher()
        data = fetcher.get_current()

        assert data is not None
        assert data.value == 25
        assert data.classification == "Fear"

    @patch('src.sentiment.fear_greed.requests.get')
    def test_get_current_uses_cache(self, mock_get):
        """Test that second call uses cache."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"value": "50", "value_classification": "Neutral", "timestamp": "1706918400"}]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = FearGreedFetcher()

        # First call hits API
        data1 = fetcher.get_current()
        assert mock_get.call_count == 1

        # Second call uses cache
        data2 = fetcher.get_current()
        assert mock_get.call_count == 1
        assert data1.value == data2.value

    @patch('src.sentiment.fear_greed.requests.get')
    def test_get_current_cache_expired(self, mock_get):
        """Test that expired cache triggers new fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"value": "50", "value_classification": "Neutral", "timestamp": "1706918400"}]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = FearGreedFetcher(cache_ttl_minutes=1)

        # First call
        fetcher.get_current()
        assert mock_get.call_count == 1

        # Expire cache
        fetcher._cache_time = datetime.now() - timedelta(minutes=5)

        # Second call should hit API
        fetcher.get_current()
        assert mock_get.call_count == 2

    @patch('src.sentiment.fear_greed.requests.get')
    def test_get_current_api_failure_returns_cached(self, mock_get):
        """Test fallback to cached data on API failure."""
        # First call succeeds
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"value": "30", "value_classification": "Fear", "timestamp": "1706918400"}]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = FearGreedFetcher()
        fetcher._retry_count = 1  # Speed up test
        data1 = fetcher.get_current()
        assert data1.value == 30

        # Expire cache
        fetcher._cache_time = datetime.now() - timedelta(hours=2)

        # API fails
        mock_get.side_effect = Exception("Network error")

        # Should return cached data
        data2 = fetcher.get_current()
        assert data2.value == 30

    @patch('src.sentiment.fear_greed.requests.get')
    def test_get_current_api_failure_no_cache(self, mock_get):
        """Test returns None when API fails and no cache."""
        mock_get.side_effect = Exception("Network error")

        fetcher = FearGreedFetcher()
        fetcher._retry_count = 1  # Speed up test
        data = fetcher.get_current()

        assert data is None

    @patch('src.sentiment.fear_greed.requests.get')
    def test_get_historical(self, mock_get):
        """Test fetching historical data."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"value": "50", "value_classification": "Neutral", "timestamp": "1706918400"},
                {"value": "45", "value_classification": "Fear", "timestamp": "1706832000"},
                {"value": "40", "value_classification": "Fear", "timestamp": "1706745600"}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = FearGreedFetcher()
        history = fetcher.get_historical(days=3)

        assert len(history) == 3
        assert history[0].value == 50
        assert history[2].value == 40
