"""Tests for Context Manager."""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.sentiment.context_manager import ContextManager, MarketContext, CoinContext
from src.sentiment.fear_greed import FearGreedData
from src.sentiment.btc_correlation import BTCCorrelation
from src.sentiment.news_feed import NewsItem
from src.sentiment.social_sentiment import SocialMetrics


class TestMarketContext:
    """Tests for MarketContext dataclass."""

    def test_fear_greed_value_with_data(self):
        fg = FearGreedData(value=25, classification="fear", timestamp=datetime.now())
        ctx = MarketContext(fear_greed=fg)
        assert ctx.fear_greed_value == 25

    def test_fear_greed_value_without_data(self):
        ctx = MarketContext()
        assert ctx.fear_greed_value == 50  # Default neutral

    def test_is_extreme_fear(self):
        fg = FearGreedData(value=15, classification="extreme_fear", timestamp=datetime.now())
        ctx = MarketContext(fear_greed=fg)
        assert ctx.is_extreme_fear is True
        assert ctx.is_extreme_greed is False

    def test_is_extreme_greed(self):
        fg = FearGreedData(value=85, classification="extreme_greed", timestamp=datetime.now())
        ctx = MarketContext(fear_greed=fg)
        assert ctx.is_extreme_fear is False
        assert ctx.is_extreme_greed is True

    def test_has_breaking_news(self):
        news = [NewsItem("Test", ["BTC"], datetime.now(timezone.utc), 0.5, True, "Source")]
        ctx = MarketContext(breaking_news=news)
        assert ctx.has_breaking_news is True

    def test_no_breaking_news(self):
        ctx = MarketContext()
        assert ctx.has_breaking_news is False

    def test_btc_trend_bullish(self):
        ctx = MarketContext(btc_change_1h=2.5)
        assert ctx.btc_trend == "bullish"

    def test_btc_trend_bearish(self):
        ctx = MarketContext(btc_change_1h=-1.5)
        assert ctx.btc_trend == "bearish"

    def test_btc_trend_neutral(self):
        ctx = MarketContext(btc_change_1h=0.5)
        assert ctx.btc_trend == "neutral"

    def test_to_prompt(self):
        fg = FearGreedData(value=35, classification="fear", timestamp=datetime.now())
        ctx = MarketContext(fear_greed=fg, btc_change_1h=1.5, btc_change_24h=3.0)
        prompt = ctx.to_prompt()

        assert "MARKET CONTEXT" in prompt
        assert "Fear & Greed: 35" in prompt
        assert "BTC:" in prompt


class TestCoinContext:
    """Tests for CoinContext dataclass."""

    def test_is_btc_driven_true(self):
        corr = BTCCorrelation(
            coin="SOL", btc_change_1h=2.0, coin_change_1h=3.0,
            correlation_24h=0.8, is_btc_driven=True, timestamp=datetime.now()
        )
        ctx = CoinContext(coin="SOL", btc_correlation=corr)
        assert ctx.is_btc_driven is True

    def test_is_btc_driven_false(self):
        ctx = CoinContext(coin="SOL")
        assert ctx.is_btc_driven is False

    def test_is_trending(self):
        metrics = SocialMetrics(
            coin="SOL", social_volume=5000, social_score=80,
            sentiment=70, galaxy_score=75, alt_rank=5
        )
        ctx = CoinContext(coin="SOL", social_metrics=metrics)
        assert ctx.is_trending is True

    def test_not_trending(self):
        metrics = SocialMetrics(
            coin="SOL", social_volume=1000, social_score=50,
            sentiment=50, galaxy_score=50, alt_rank=50
        )
        ctx = CoinContext(coin="SOL", social_metrics=metrics)
        assert ctx.is_trending is False

    def test_has_negative_news(self):
        news = [NewsItem("Bad news", ["SOL"], datetime.now(timezone.utc), -0.5, True, "Source")]
        ctx = CoinContext(coin="SOL", recent_news=news)
        assert ctx.has_negative_news is True

    def test_has_positive_news(self):
        news = [NewsItem("Good news", ["SOL"], datetime.now(timezone.utc), 0.5, True, "Source")]
        ctx = CoinContext(coin="SOL", recent_news=news)
        assert ctx.has_positive_news is True

    def test_to_prompt(self):
        corr = BTCCorrelation(
            coin="SOL", btc_change_1h=2.0, coin_change_1h=3.0,
            correlation_24h=0.75, is_btc_driven=True, timestamp=datetime.now()
        )
        ctx = CoinContext(coin="SOL", btc_correlation=corr)
        prompt = ctx.to_prompt()

        assert "SOL CONTEXT" in prompt
        assert "BTC Correlation" in prompt


class TestContextManager:
    """Tests for ContextManager."""

    @pytest.fixture
    def mock_fear_greed(self):
        mock = Mock()
        mock.get_index.return_value = FearGreedData(
            value=45, classification="fear", timestamp=datetime.now()
        )
        return mock

    @pytest.fixture
    def mock_news_fetcher(self):
        mock = Mock()
        mock.get_breaking_news.return_value = []
        mock.get_news_for_coin.return_value = []
        return mock

    @pytest.fixture
    def mock_social_fetcher(self):
        mock = Mock()
        mock.get_metrics.return_value = SocialMetrics(
            coin="SOL", social_volume=1000, social_score=50,
            sentiment=50, galaxy_score=50, alt_rank=20
        )
        return mock

    def test_init_creates_defaults(self):
        mgr = ContextManager()
        assert mgr.fear_greed is not None
        assert mgr.news_fetcher is not None
        assert mgr.social_fetcher is not None

    def test_get_context(self, mock_fear_greed, mock_news_fetcher):
        mgr = ContextManager(
            fear_greed_fetcher=mock_fear_greed,
            news_fetcher=mock_news_fetcher
        )
        ctx = mgr.get_context()

        assert isinstance(ctx, MarketContext)
        assert ctx.fear_greed_value == 45

    def test_get_coin_context(self, mock_news_fetcher, mock_social_fetcher):
        mgr = ContextManager(
            news_fetcher=mock_news_fetcher,
            social_fetcher=mock_social_fetcher
        )
        ctx = mgr.get_coin_context("SOL")

        assert isinstance(ctx, CoinContext)
        assert ctx.coin == "SOL"

    def test_should_avoid_trading_extreme_fear(self, mock_news_fetcher):
        mock_fg = Mock()
        mock_fg.get_index.return_value = FearGreedData(
            value=5, classification="extreme_fear", timestamp=datetime.now()
        )

        mgr = ContextManager(
            fear_greed_fetcher=mock_fg,
            news_fetcher=mock_news_fetcher
        )
        should_avoid, reason = mgr.should_avoid_trading("SOL")

        assert should_avoid is True
        assert "Extreme fear" in reason

    def test_should_avoid_trading_extreme_greed(self, mock_news_fetcher):
        mock_fg = Mock()
        mock_fg.get_index.return_value = FearGreedData(
            value=95, classification="extreme_greed", timestamp=datetime.now()
        )

        mgr = ContextManager(
            fear_greed_fetcher=mock_fg,
            news_fetcher=mock_news_fetcher
        )
        should_avoid, reason = mgr.should_avoid_trading("SOL")

        assert should_avoid is True
        assert "Extreme greed" in reason

    def test_should_avoid_trading_breaking_negative_news(self, mock_fear_greed):
        mock_news = Mock()
        mock_news.get_breaking_news.return_value = []
        mock_news.get_news_for_coin.return_value = [
            NewsItem("SOL crash", ["SOL"], datetime.now(timezone.utc), -0.5, True, "Source")
        ]

        mgr = ContextManager(
            fear_greed_fetcher=mock_fear_greed,
            news_fetcher=mock_news
        )
        should_avoid, reason = mgr.should_avoid_trading("SOL")

        assert should_avoid is True
        assert "Breaking negative news" in reason

    def test_should_not_avoid_trading_normal(self, mock_fear_greed, mock_news_fetcher):
        mgr = ContextManager(
            fear_greed_fetcher=mock_fear_greed,
            news_fetcher=mock_news_fetcher
        )
        should_avoid, reason = mgr.should_avoid_trading("SOL")

        assert should_avoid is False
        assert reason == ""

    def test_get_all_coin_contexts(self, mock_news_fetcher, mock_social_fetcher):
        mgr = ContextManager(
            news_fetcher=mock_news_fetcher,
            social_fetcher=mock_social_fetcher
        )
        contexts = mgr.get_all_coin_contexts(["SOL", "ETH", "BTC"])

        assert len(contexts) == 3
        assert "SOL" in contexts
        assert "ETH" in contexts
        assert "BTC" in contexts

    def test_graceful_degradation_fear_greed_fails(self, mock_news_fetcher):
        mock_fg = Mock()
        mock_fg.get_index.side_effect = Exception("API Error")

        mgr = ContextManager(
            fear_greed_fetcher=mock_fg,
            news_fetcher=mock_news_fetcher
        )
        ctx = mgr.get_context()

        # Should still return context with None for fear_greed
        assert ctx.fear_greed is None
        assert ctx.fear_greed_value == 50  # Default neutral

    def test_graceful_degradation_news_fails(self, mock_fear_greed):
        mock_news = Mock()
        mock_news.get_breaking_news.side_effect = Exception("API Error")
        mock_news.get_news_for_coin.side_effect = Exception("API Error")

        mgr = ContextManager(
            fear_greed_fetcher=mock_fear_greed,
            news_fetcher=mock_news
        )
        ctx = mgr.get_context()

        # Should still return context with empty breaking_news
        assert ctx.breaking_news == []

    def test_graceful_degradation_social_fails(self, mock_news_fetcher):
        mock_social = Mock()
        mock_social.get_metrics.side_effect = Exception("API Error")

        mgr = ContextManager(
            news_fetcher=mock_news_fetcher,
            social_fetcher=mock_social
        )
        coin_ctx = mgr.get_coin_context("SOL")

        # Should still return context with None for social_metrics
        assert coin_ctx.social_metrics is None
