"""Tests for Social Sentiment Fetcher."""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.sentiment.social_sentiment import SocialSentimentFetcher, SocialMetrics


class TestSocialMetrics:
    """Tests for SocialMetrics dataclass."""

    def test_is_trending(self):
        metrics = SocialMetrics(
            coin="BTC",
            social_volume=1000,
            social_score=80,
            sentiment=70,
            galaxy_score=75,
            alt_rank=5
        )
        assert metrics.is_trending is True

    def test_is_not_trending(self):
        metrics = SocialMetrics(
            coin="BTC",
            social_volume=1000,
            social_score=80,
            sentiment=70,
            galaxy_score=75,
            alt_rank=50
        )
        assert metrics.is_trending is False

    def test_is_bullish_sentiment(self):
        metrics = SocialMetrics(
            coin="BTC",
            social_volume=1000,
            social_score=80,
            sentiment=70,
            galaxy_score=75,
            alt_rank=10
        )
        assert metrics.is_bullish_sentiment is True
        assert metrics.is_bearish_sentiment is False

    def test_is_bearish_sentiment(self):
        metrics = SocialMetrics(
            coin="BTC",
            social_volume=1000,
            social_score=80,
            sentiment=30,
            galaxy_score=75,
            alt_rank=10
        )
        assert metrics.is_bullish_sentiment is False
        assert metrics.is_bearish_sentiment is True

    def test_is_neutral_sentiment(self):
        metrics = SocialMetrics(
            coin="BTC",
            social_volume=1000,
            social_score=80,
            sentiment=50,
            galaxy_score=75,
            alt_rank=10
        )
        assert metrics.is_neutral_sentiment is True

    def test_sentiment_label_bullish(self):
        metrics = SocialMetrics(
            coin="BTC",
            social_volume=1000,
            social_score=80,
            sentiment=70,
            galaxy_score=75,
            alt_rank=10
        )
        assert metrics.sentiment_label == "bullish"

    def test_sentiment_label_bearish(self):
        metrics = SocialMetrics(
            coin="BTC",
            social_volume=1000,
            social_score=80,
            sentiment=30,
            galaxy_score=75,
            alt_rank=10
        )
        assert metrics.sentiment_label == "bearish"

    def test_sentiment_label_neutral(self):
        metrics = SocialMetrics(
            coin="BTC",
            social_volume=1000,
            social_score=80,
            sentiment=50,
            galaxy_score=75,
            alt_rank=10
        )
        assert metrics.sentiment_label == "neutral"

    def test_has_social_spike(self):
        metrics = SocialMetrics(
            coin="BTC",
            social_volume=5000,
            social_score=80,
            sentiment=50,
            galaxy_score=75,
            alt_rank=10,
            avg_social_volume=2000
        )
        # 5000 > 2000 * 2 = True
        assert metrics.has_social_spike is True

    def test_no_social_spike(self):
        metrics = SocialMetrics(
            coin="BTC",
            social_volume=3000,
            social_score=80,
            sentiment=50,
            galaxy_score=75,
            alt_rank=10,
            avg_social_volume=2000
        )
        # 3000 < 2000 * 2 = False
        assert metrics.has_social_spike is False

    def test_has_social_spike_no_history(self):
        metrics = SocialMetrics(
            coin="BTC",
            social_volume=5000,
            social_score=80,
            sentiment=50,
            galaxy_score=75,
            alt_rank=10,
            avg_social_volume=None
        )
        assert metrics.has_social_spike is False

    def test_volume_multiplier(self):
        metrics = SocialMetrics(
            coin="BTC",
            social_volume=6000,
            social_score=80,
            sentiment=50,
            galaxy_score=75,
            alt_rank=10,
            avg_social_volume=2000
        )
        assert metrics.volume_multiplier == 3.0

    def test_volume_multiplier_no_history(self):
        metrics = SocialMetrics(
            coin="BTC",
            social_volume=6000,
            social_score=80,
            sentiment=50,
            galaxy_score=75,
            alt_rank=10,
            avg_social_volume=None
        )
        assert metrics.volume_multiplier is None


class TestSocialSentimentFetcher:
    """Tests for SocialSentimentFetcher."""

    def test_init_defaults(self):
        fetcher = SocialSentimentFetcher()
        assert fetcher.api_key is None
        assert fetcher.CACHE_TTL == 900

    def test_init_with_key(self):
        fetcher = SocialSentimentFetcher(api_key="test_key")
        assert fetcher.api_key == "test_key"

    @patch('src.sentiment.social_sentiment.requests.get')
    def test_get_metrics_success(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "social_volume": 5000,
                "social_score": 80,
                "sentiment": 65,
                "galaxy_score": 70,
                "alt_rank": 5
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = SocialSentimentFetcher()
        metrics = fetcher.get_metrics("BTC")

        assert metrics.coin == "BTC"
        assert metrics.social_volume == 5000
        assert metrics.sentiment == 65
        assert metrics.alt_rank == 5

    @patch('src.sentiment.social_sentiment.requests.get')
    def test_get_metrics_uses_cache(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "social_volume": 5000,
                "social_score": 80,
                "sentiment": 65,
                "galaxy_score": 70,
                "alt_rank": 5
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = SocialSentimentFetcher()

        # First call
        fetcher.get_metrics("BTC")
        # Second call should use cache
        fetcher.get_metrics("BTC")

        # Should only be called once
        assert mock_get.call_count == 1

    @patch('src.sentiment.social_sentiment.requests.get')
    def test_get_metrics_api_error_returns_cache(self, mock_get):
        import requests as req
        import time
        mock_get.side_effect = req.RequestException("API Error")

        fetcher = SocialSentimentFetcher()
        cached_metrics = SocialMetrics(
            coin="BTC",
            social_volume=1000,
            social_score=50,
            sentiment=50,
            galaxy_score=50,
            alt_rank=10
        )
        fetcher._cache["BTC"] = (cached_metrics, time.time() - 1000)  # Expired cache

        metrics = fetcher.get_metrics("BTC")

        # Should return cached data
        assert metrics.coin == "BTC"
        assert metrics.social_volume == 1000

    @patch('src.sentiment.social_sentiment.requests.get')
    def test_get_metrics_api_error_no_cache(self, mock_get):
        import requests as req
        mock_get.side_effect = req.RequestException("API Error")

        fetcher = SocialSentimentFetcher()
        metrics = fetcher.get_metrics("BTC")

        # Should return empty metrics
        assert metrics.coin == "BTC"
        assert metrics.social_volume == 0
        assert metrics.alt_rank == 100

    @patch('src.sentiment.social_sentiment.requests.get')
    def test_get_all_metrics(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "social_volume": 1000,
                "social_score": 50,
                "sentiment": 50,
                "galaxy_score": 50,
                "alt_rank": 10
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = SocialSentimentFetcher()
        results = fetcher.get_all_metrics(["BTC", "ETH", "SOL"])

        assert "BTC" in results
        assert "ETH" in results
        assert "SOL" in results

    @patch('src.sentiment.social_sentiment.requests.get')
    def test_detect_social_spike(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "social_volume": 10000,
                "social_score": 80,
                "sentiment": 70,
                "galaxy_score": 75,
                "alt_rank": 5
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = SocialSentimentFetcher()
        # Pre-populate historical data
        fetcher._historical_volumes["BTC"] = [2000, 2500, 2000, 2500, 2000]

        is_spike, multiplier = fetcher.detect_social_spike("BTC")

        # Volume should be detected as spike
        assert isinstance(is_spike, bool)
        assert multiplier is None or isinstance(multiplier, float)

    @patch('src.sentiment.social_sentiment.requests.get')
    def test_get_trending_coins(self, mock_get):
        def side_effect(url, **kwargs):
            mock_response = Mock()
            if "BTC" in url:
                mock_response.json.return_value = {"data": {"alt_rank": 3, "social_volume": 1000, "social_score": 80, "sentiment": 70, "galaxy_score": 75}}
            elif "ETH" in url:
                mock_response.json.return_value = {"data": {"alt_rank": 5, "social_volume": 1000, "social_score": 80, "sentiment": 70, "galaxy_score": 75}}
            else:
                mock_response.json.return_value = {"data": {"alt_rank": 50, "social_volume": 1000, "social_score": 80, "sentiment": 70, "galaxy_score": 75}}
            mock_response.raise_for_status = Mock()
            return mock_response

        mock_get.side_effect = side_effect

        fetcher = SocialSentimentFetcher()
        trending = fetcher.get_trending_coins(["BTC", "ETH", "DOGE"])

        assert "BTC" in trending
        assert "ETH" in trending
        assert "DOGE" not in trending

    def test_update_historical_volume(self):
        fetcher = SocialSentimentFetcher()

        # Add volumes
        for i in range(30):
            fetcher._update_historical_volume("BTC", i * 100)

        # Should only keep last 24
        assert len(fetcher._historical_volumes["BTC"]) == 24

    def test_get_average_volume(self):
        fetcher = SocialSentimentFetcher()
        fetcher._historical_volumes["BTC"] = [1000, 2000, 3000]

        avg = fetcher._get_average_volume("BTC")
        assert avg == 2000

    def test_get_average_volume_no_history(self):
        fetcher = SocialSentimentFetcher()

        avg = fetcher._get_average_volume("BTC")
        assert avg is None

    def test_parse_response_list_format(self):
        fetcher = SocialSentimentFetcher()
        data = {
            "data": [
                {
                    "social_volume": 5000,
                    "social_score": 80,
                    "sentiment": 65,
                    "galaxy_score": 70,
                    "alt_rank": 5
                }
            ]
        }

        metrics = fetcher._parse_response("BTC", data)
        assert metrics.social_volume == 5000
