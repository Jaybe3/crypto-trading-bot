"""Tests for News Feed Fetcher."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from src.sentiment.news_feed import NewsFeedFetcher, NewsItem, NewsFeed


class TestNewsItem:
    """Tests for NewsItem dataclass."""

    def test_is_bullish(self):
        item = NewsItem(
            title="BTC Surges",
            coins=["BTC"],
            published_at=datetime.now(timezone.utc),
            sentiment_score=0.5,
            is_breaking=False,
            source="CoinDesk"
        )
        assert item.is_bullish is True
        assert item.is_bearish is False

    def test_is_bearish(self):
        item = NewsItem(
            title="Market Crash",
            coins=["BTC"],
            published_at=datetime.now(timezone.utc),
            sentiment_score=-0.5,
            is_breaking=False,
            source="CoinDesk"
        )
        assert item.is_bullish is False
        assert item.is_bearish is True

    def test_is_neutral(self):
        item = NewsItem(
            title="Market Update",
            coins=["BTC"],
            published_at=datetime.now(timezone.utc),
            sentiment_score=0.1,
            is_breaking=False,
            source="CoinDesk"
        )
        assert item.is_neutral is True
        assert item.is_bullish is False
        assert item.is_bearish is False

    def test_sentiment_label_bullish(self):
        item = NewsItem(
            title="Test",
            coins=["BTC"],
            published_at=datetime.now(timezone.utc),
            sentiment_score=0.5,
            is_breaking=False,
            source="Test"
        )
        assert item.sentiment_label == "bullish"

    def test_sentiment_label_bearish(self):
        item = NewsItem(
            title="Test",
            coins=["BTC"],
            published_at=datetime.now(timezone.utc),
            sentiment_score=-0.5,
            is_breaking=False,
            source="Test"
        )
        assert item.sentiment_label == "bearish"

    def test_sentiment_label_neutral(self):
        item = NewsItem(
            title="Test",
            coins=["BTC"],
            published_at=datetime.now(timezone.utc),
            sentiment_score=0.0,
            is_breaking=False,
            source="Test"
        )
        assert item.sentiment_label == "neutral"


class TestNewsFeed:
    """Tests for NewsFeed dataclass."""

    def test_breaking_news(self):
        items = [
            NewsItem("Breaking", ["BTC"], datetime.now(timezone.utc), 0.5, True, "Source1"),
            NewsItem("Old News", ["ETH"], datetime.now(timezone.utc), 0.3, False, "Source2"),
            NewsItem("Breaking 2", ["SOL"], datetime.now(timezone.utc), 0.4, True, "Source3"),
        ]
        feed = NewsFeed(items=items)

        assert len(feed.breaking_news) == 2
        assert all(item.is_breaking for item in feed.breaking_news)

    def test_bullish_count(self):
        items = [
            NewsItem("Bull 1", ["BTC"], datetime.now(timezone.utc), 0.5, False, "Source"),
            NewsItem("Bull 2", ["ETH"], datetime.now(timezone.utc), 0.4, False, "Source"),
            NewsItem("Bear", ["SOL"], datetime.now(timezone.utc), -0.5, False, "Source"),
        ]
        feed = NewsFeed(items=items)

        assert feed.bullish_count == 2
        assert feed.bearish_count == 1

    def test_overall_sentiment(self):
        items = [
            NewsItem("Test1", ["BTC"], datetime.now(timezone.utc), 0.5, False, "Source"),
            NewsItem("Test2", ["ETH"], datetime.now(timezone.utc), -0.5, False, "Source"),
        ]
        feed = NewsFeed(items=items)

        # Average of 0.5 and -0.5 = 0
        assert feed.overall_sentiment == 0.0

    def test_overall_sentiment_empty(self):
        feed = NewsFeed(items=[])
        assert feed.overall_sentiment == 0.0

    def test_for_coin(self):
        items = [
            NewsItem("BTC News", ["BTC"], datetime.now(timezone.utc), 0.5, False, "Source"),
            NewsItem("ETH News", ["ETH"], datetime.now(timezone.utc), 0.3, False, "Source"),
            NewsItem("BTC ETH News", ["BTC", "ETH"], datetime.now(timezone.utc), 0.4, False, "Source"),
        ]
        feed = NewsFeed(items=items)

        btc_news = feed.for_coin("BTC")
        assert len(btc_news) == 2

        eth_news = feed.for_coin("eth")  # lowercase should work
        assert len(eth_news) == 2


class TestNewsFeedFetcher:
    """Tests for NewsFeedFetcher."""

    def test_init_defaults(self):
        fetcher = NewsFeedFetcher()
        assert fetcher.api_token is None
        assert fetcher.CACHE_TTL == 300

    def test_init_with_token(self):
        fetcher = NewsFeedFetcher(api_token="test_token")
        assert fetcher.api_token == "test_token"

    def test_calculate_sentiment_positive(self):
        fetcher = NewsFeedFetcher()
        sentiment = fetcher.calculate_sentiment(80, 20)
        # (80 - 20) / 100 = 0.6
        assert abs(sentiment - 0.6) < 0.01

    def test_calculate_sentiment_negative(self):
        fetcher = NewsFeedFetcher()
        sentiment = fetcher.calculate_sentiment(20, 80)
        # (20 - 80) / 100 = -0.6
        assert abs(sentiment - (-0.6)) < 0.01

    def test_calculate_sentiment_zero_votes(self):
        fetcher = NewsFeedFetcher()
        sentiment = fetcher.calculate_sentiment(0, 0)
        assert sentiment == 0.0

    def test_calculate_sentiment_equal_votes(self):
        fetcher = NewsFeedFetcher()
        sentiment = fetcher.calculate_sentiment(50, 50)
        assert sentiment == 0.0

    @patch('src.sentiment.news_feed.requests.get')
    def test_get_news_success(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Test News",
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "currencies": [{"code": "BTC"}],
                    "votes": {"positive": 10, "negative": 2},
                    "source": {"title": "TestSource"}
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = NewsFeedFetcher()
        fetcher._last_request_time = 0  # Skip rate limiting
        feed = fetcher.get_news()

        assert len(feed.items) == 1
        assert feed.items[0].title == "Test News"
        assert "BTC" in feed.items[0].coins

    @patch('src.sentiment.news_feed.requests.get')
    def test_get_news_uses_cache(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = NewsFeedFetcher()
        fetcher._last_request_time = 0

        # First call
        fetcher.get_news()
        # Second call should use cache
        fetcher.get_news()

        # Should only be called once
        assert mock_get.call_count == 1

    @patch('src.sentiment.news_feed.requests.get')
    def test_get_news_api_error_returns_cache(self, mock_get):
        import requests as req
        mock_get.side_effect = req.RequestException("API Error")

        fetcher = NewsFeedFetcher()
        fetcher._cache = NewsFeed(items=[
            NewsItem("Cached", ["BTC"], datetime.now(timezone.utc), 0.5, False, "Source")
        ])
        fetcher._cache_time = 0  # Expired cache

        feed = fetcher.get_news()

        # Should return cached data
        assert len(feed.items) == 1
        assert feed.items[0].title == "Cached"

    @patch('src.sentiment.news_feed.requests.get')
    def test_get_news_api_error_no_cache(self, mock_get):
        import requests as req
        mock_get.side_effect = req.RequestException("API Error")

        fetcher = NewsFeedFetcher()
        feed = fetcher.get_news()

        # Should return empty feed
        assert len(feed.items) == 0

    def test_build_params_no_token(self):
        fetcher = NewsFeedFetcher()
        params = fetcher._build_params("hot", None)

        assert "auth_token" not in params
        assert params["filter"] == "hot"
        assert params["public"] == "true"

    def test_build_params_with_token(self):
        fetcher = NewsFeedFetcher(api_token="test_token")
        params = fetcher._build_params("hot", None)

        assert params["auth_token"] == "test_token"

    def test_build_params_with_currencies(self):
        fetcher = NewsFeedFetcher()
        params = fetcher._build_params("hot", ["BTC", "ETH"])

        assert params["currencies"] == "BTC,ETH"

    def test_parse_response_breaking_news(self):
        fetcher = NewsFeedFetcher()
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(minutes=30)).isoformat()
        old = (now - timedelta(hours=2)).isoformat()

        data = {
            "results": [
                {
                    "title": "Breaking",
                    "published_at": recent,
                    "currencies": [{"code": "BTC"}],
                    "votes": {"positive": 10, "negative": 0},
                    "source": {"title": "Source"}
                },
                {
                    "title": "Old",
                    "published_at": old,
                    "currencies": [{"code": "ETH"}],
                    "votes": {"positive": 5, "negative": 5},
                    "source": {"title": "Source"}
                }
            ]
        }

        feed = fetcher._parse_response(data)

        breaking = [item for item in feed.items if item.is_breaking]
        assert len(breaking) == 1
        assert breaking[0].title == "Breaking"
