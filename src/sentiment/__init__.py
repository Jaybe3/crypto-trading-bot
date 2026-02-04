"""Sentiment analysis module for market context."""
from .fear_greed import FearGreedFetcher, FearGreedData
from .btc_correlation import BTCCorrelationTracker, BTCCorrelation
from .news_feed import NewsFeedFetcher, NewsItem, NewsFeed
from .social_sentiment import SocialSentimentFetcher, SocialMetrics
from .context_manager import ContextManager, MarketContext, CoinContext

__all__ = [
    "FearGreedFetcher",
    "FearGreedData",
    "BTCCorrelationTracker",
    "BTCCorrelation",
    "NewsFeedFetcher",
    "NewsItem",
    "NewsFeed",
    "SocialSentimentFetcher",
    "SocialMetrics",
    "ContextManager",
    "MarketContext",
    "CoinContext",
]
