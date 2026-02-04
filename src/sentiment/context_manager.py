"""Context Manager - Aggregates all sentiment sources for Strategist."""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from .fear_greed import FearGreedFetcher, FearGreedData
from .btc_correlation import BTCCorrelationTracker, BTCCorrelation
from .news_feed import NewsFeedFetcher, NewsItem, NewsFeed
from .social_sentiment import SocialSentimentFetcher, SocialMetrics

logger = logging.getLogger(__name__)


@dataclass
class MarketContext:
    """Overall market context from sentiment sources."""
    fear_greed: Optional[FearGreedData] = None
    btc_change_1h: float = 0.0
    btc_change_24h: float = 0.0
    breaking_news: List[NewsItem] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def fear_greed_value(self) -> int:
        """Fear & Greed value or 50 (neutral) if unavailable."""
        return self.fear_greed.value if self.fear_greed else 50

    @property
    def fear_greed_classification(self) -> str:
        """Fear & Greed classification or 'neutral' if unavailable."""
        return self.fear_greed.classification if self.fear_greed else "neutral"

    @property
    def is_extreme_fear(self) -> bool:
        """Market in extreme fear (value < 20)."""
        return self.fear_greed_value < 20

    @property
    def is_extreme_greed(self) -> bool:
        """Market in extreme greed (value > 80)."""
        return self.fear_greed_value > 80

    @property
    def has_breaking_news(self) -> bool:
        """Breaking news exists."""
        return len(self.breaking_news) > 0

    @property
    def btc_trend(self) -> str:
        """BTC trend based on 1h change."""
        if self.btc_change_1h > 1:
            return "bullish"
        if self.btc_change_1h < -1:
            return "bearish"
        return "neutral"

    def to_prompt(self) -> str:
        """Format market context for LLM prompt."""
        lines = [
            "=== MARKET CONTEXT ===",
            f"Fear & Greed: {self.fear_greed_value} ({self.fear_greed_classification})",
            f"BTC: {self.btc_change_1h:+.1f}% (1h), {self.btc_change_24h:+.1f}% (24h)",
        ]

        if self.is_extreme_fear:
            lines.append("⚠️ EXTREME FEAR - Market may be oversold")
        elif self.is_extreme_greed:
            lines.append("⚠️ EXTREME GREED - Market may be overbought")

        if self.breaking_news:
            lines.append(f"Breaking News: {len(self.breaking_news)} items")
            for news in self.breaking_news[:3]:  # Top 3
                sentiment = "🟢" if news.is_bullish else "🔴" if news.is_bearish else "⚪"
                lines.append(f"  {sentiment} {news.title[:50]}...")

        return "\n".join(lines)


@dataclass
class CoinContext:
    """Coin-specific context from sentiment sources."""
    coin: str
    btc_correlation: Optional[BTCCorrelation] = None
    recent_news: List[NewsItem] = field(default_factory=list)
    social_metrics: Optional[SocialMetrics] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_btc_driven(self) -> bool:
        """Coin is currently moving with BTC."""
        return self.btc_correlation.is_btc_driven if self.btc_correlation else False

    @property
    def correlation_strength(self) -> str:
        """BTC correlation strength."""
        return self.btc_correlation.correlation_strength if self.btc_correlation else "unknown"

    @property
    def is_trending(self) -> bool:
        """Coin is trending on social media."""
        return self.social_metrics.is_trending if self.social_metrics else False

    @property
    def social_sentiment(self) -> str:
        """Social sentiment label."""
        return self.social_metrics.sentiment_label if self.social_metrics else "unknown"

    @property
    def has_negative_news(self) -> bool:
        """Has recent bearish news."""
        return any(n.is_bearish for n in self.recent_news)

    @property
    def has_positive_news(self) -> bool:
        """Has recent bullish news."""
        return any(n.is_bullish for n in self.recent_news)

    def to_prompt(self) -> str:
        """Format coin context for LLM prompt."""
        lines = [f"=== {self.coin} CONTEXT ==="]

        if self.btc_correlation:
            corr = self.btc_correlation
            lines.append(f"BTC Correlation: {corr.correlation_24h:.2f} ({corr.correlation_strength})")
            if corr.is_btc_driven:
                lines.append(f"  ⚠️ Move is BTC-driven ({corr.move_type})")

        if self.social_metrics:
            sm = self.social_metrics
            lines.append(f"Social: Rank #{sm.alt_rank}, Sentiment {sm.sentiment:.0f}/100 ({sm.sentiment_label})")
            if sm.is_trending:
                lines.append("  🔥 TRENDING")
            if sm.has_social_spike:
                lines.append(f"  📈 Social spike: {sm.volume_multiplier:.1f}x normal")

        if self.recent_news:
            lines.append(f"Recent News: {len(self.recent_news)} items")
            for news in self.recent_news[:2]:
                sentiment = "🟢" if news.is_bullish else "🔴" if news.is_bearish else "⚪"
                lines.append(f"  {sentiment} {news.title[:40]}...")

        return "\n".join(lines)


class ContextManager:
    """Aggregates all sentiment sources for the Strategist.

    Provides unified access to:
    - Fear & Greed Index
    - BTC correlation
    - News sentiment
    - Social sentiment

    Graceful degradation: if any source fails, continues with available data.

    Usage:
        ctx_mgr = ContextManager()
        market = ctx_mgr.get_context()
        print(market.to_prompt())

        coin_ctx = ctx_mgr.get_coin_context("SOL")
        should_avoid, reason = ctx_mgr.should_avoid_trading("SOL")
    """

    def __init__(
        self,
        fear_greed_fetcher: Optional[FearGreedFetcher] = None,
        btc_tracker: Optional[BTCCorrelationTracker] = None,
        news_fetcher: Optional[NewsFeedFetcher] = None,
        social_fetcher: Optional[SocialSentimentFetcher] = None
    ):
        """Initialize with sentiment sources.

        Args:
            fear_greed_fetcher: FearGreedFetcher instance (created if None)
            btc_tracker: BTCCorrelationTracker instance
            news_fetcher: NewsFeedFetcher instance (created if None)
            social_fetcher: SocialSentimentFetcher instance (created if None)
        """
        self.fear_greed = fear_greed_fetcher or FearGreedFetcher()
        self.btc_tracker = btc_tracker
        self.news_fetcher = news_fetcher or NewsFeedFetcher()
        self.social_fetcher = social_fetcher or SocialSentimentFetcher()

    def get_context(self) -> MarketContext:
        """Get overall market context.

        Returns:
            MarketContext with available sentiment data
        """
        fear_greed = self._get_fear_greed()
        btc_changes = self._get_btc_changes()
        breaking_news = self._get_breaking_news()

        return MarketContext(
            fear_greed=fear_greed,
            btc_change_1h=btc_changes[0],
            btc_change_24h=btc_changes[1],
            breaking_news=breaking_news,
            timestamp=datetime.now(timezone.utc)
        )

    def get_coin_context(self, coin: str) -> CoinContext:
        """Get context for a specific coin.

        Args:
            coin: Coin symbol (e.g., "SOL")

        Returns:
            CoinContext with available data for the coin
        """
        btc_correlation = self._get_btc_correlation(coin)
        recent_news = self._get_coin_news(coin)
        social_metrics = self._get_social_metrics(coin)

        return CoinContext(
            coin=coin.upper(),
            btc_correlation=btc_correlation,
            recent_news=recent_news,
            social_metrics=social_metrics,
            timestamp=datetime.now(timezone.utc)
        )

    def should_avoid_trading(self, coin: str) -> tuple[bool, str]:
        """Determine if trading should be avoided.

        Args:
            coin: Coin symbol

        Returns:
            Tuple of (should_avoid, reason)
        """
        reasons = []

        # Check extreme fear/greed
        fg = self._get_fear_greed()
        if fg:
            if fg.value < 10:
                reasons.append(f"Extreme fear ({fg.value}) - high risk of capitulation")
            elif fg.value > 90:
                reasons.append(f"Extreme greed ({fg.value}) - high risk of correction")

        # Check for breaking negative news
        coin_news = self._get_coin_news(coin)
        breaking_negative = [n for n in coin_news if n.is_breaking and n.is_bearish]
        if breaking_negative:
            reasons.append(f"Breaking negative news: {breaking_negative[0].title[:50]}")

        if reasons:
            return True, "; ".join(reasons)

        return False, ""

    def get_all_coin_contexts(self, coins: List[str]) -> Dict[str, CoinContext]:
        """Get context for multiple coins.

        Args:
            coins: List of coin symbols

        Returns:
            Dict mapping coin to CoinContext
        """
        return {coin: self.get_coin_context(coin) for coin in coins}

    def _get_fear_greed(self) -> Optional[FearGreedData]:
        """Get Fear & Greed data with error handling."""
        try:
            return self.fear_greed.get_index()
        except Exception as e:
            logger.warning(f"Failed to get Fear & Greed: {e}")
            return None

    def _get_btc_changes(self) -> tuple[float, float]:
        """Get BTC price changes with error handling."""
        if not self.btc_tracker:
            return 0.0, 0.0

        try:
            corr = self.btc_tracker.get_correlation("BTC")
            return corr.btc_change_1h, 0.0  # 24h not always available
        except Exception as e:
            logger.warning(f"Failed to get BTC changes: {e}")
            return 0.0, 0.0

    def _get_breaking_news(self) -> List[NewsItem]:
        """Get breaking news with error handling."""
        try:
            return self.news_fetcher.get_breaking_news()
        except Exception as e:
            logger.warning(f"Failed to get breaking news: {e}")
            return []

    def _get_btc_correlation(self, coin: str) -> Optional[BTCCorrelation]:
        """Get BTC correlation for a coin with error handling."""
        if not self.btc_tracker:
            return None

        try:
            return self.btc_tracker.get_correlation(coin)
        except Exception as e:
            logger.warning(f"Failed to get BTC correlation for {coin}: {e}")
            return None

    def _get_coin_news(self, coin: str) -> List[NewsItem]:
        """Get news for a coin with error handling."""
        try:
            return self.news_fetcher.get_news_for_coin(coin)
        except Exception as e:
            logger.warning(f"Failed to get news for {coin}: {e}")
            return []

    def _get_social_metrics(self, coin: str) -> Optional[SocialMetrics]:
        """Get social metrics for a coin with error handling."""
        try:
            return self.social_fetcher.get_metrics(coin)
        except Exception as e:
            logger.warning(f"Failed to get social metrics for {coin}: {e}")
            return None
