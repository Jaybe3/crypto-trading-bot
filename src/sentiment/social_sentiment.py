"""Social sentiment tracking via LunarCrush."""
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import requests

logger = logging.getLogger(__name__)


@dataclass
class SocialMetrics:
    """Social media metrics for a coin."""
    coin: str
    social_volume: int              # Total social mentions
    social_score: float             # LunarCrush social score (0-100)
    sentiment: float                # Sentiment score (0-100)
    galaxy_score: float             # Overall LunarCrush score
    alt_rank: int                   # Rank among altcoins (1 = best)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Historical comparison
    avg_social_volume: Optional[float] = None

    @property
    def is_trending(self) -> bool:
        """Coin is trending (alt_rank <= 10)."""
        return self.alt_rank <= 10

    @property
    def is_bullish_sentiment(self) -> bool:
        """Social sentiment is bullish (>60)."""
        return self.sentiment > 60

    @property
    def is_bearish_sentiment(self) -> bool:
        """Social sentiment is bearish (<40)."""
        return self.sentiment < 40

    @property
    def is_neutral_sentiment(self) -> bool:
        """Social sentiment is neutral."""
        return not self.is_bullish_sentiment and not self.is_bearish_sentiment

    @property
    def sentiment_label(self) -> str:
        """Human-readable sentiment label."""
        if self.is_bullish_sentiment:
            return "bullish"
        if self.is_bearish_sentiment:
            return "bearish"
        return "neutral"

    @property
    def has_social_spike(self) -> bool:
        """Check if social volume is spiking (>2x average)."""
        if self.avg_social_volume is None or self.avg_social_volume == 0:
            return False
        return self.social_volume > (self.avg_social_volume * 2)

    @property
    def volume_multiplier(self) -> Optional[float]:
        """Social volume as multiple of average."""
        if self.avg_social_volume is None or self.avg_social_volume == 0:
            return None
        return self.social_volume / self.avg_social_volume


class SocialSentimentFetcher:
    """Fetches social sentiment data from LunarCrush.

    LunarCrush aggregates social media data across Twitter, Reddit,
    YouTube, and other platforms to measure crypto sentiment.

    Usage:
        fetcher = SocialSentimentFetcher(api_key="your_key")
        metrics = fetcher.get_metrics("BTC")
        if metrics.is_trending:
            print(f"{metrics.coin} is trending with {metrics.sentiment_label} sentiment")
    """

    BASE_URL = "https://lunarcrush.com/api3/coins"
    CACHE_TTL = 900  # 15 minutes

    def __init__(self, api_key: Optional[str] = None):
        """Initialize social sentiment fetcher.

        Args:
            api_key: LunarCrush API key
        """
        self.api_key = api_key
        self._cache: Dict[str, tuple[SocialMetrics, float]] = {}
        self._historical_volumes: Dict[str, List[int]] = {}

    def get_metrics(self, coin: str) -> SocialMetrics:
        """Get social metrics for a coin.

        Args:
            coin: Coin symbol (e.g., "BTC", "ETH")

        Returns:
            SocialMetrics for the coin
        """
        coin_upper = coin.upper()

        # Check cache
        if coin_upper in self._cache:
            cached_metrics, cache_time = self._cache[coin_upper]
            if (time.time() - cache_time) < self.CACHE_TTL:
                return cached_metrics

        try:
            params = {"key": self.api_key} if self.api_key else {}

            response = requests.get(
                f"{self.BASE_URL}/{coin_upper}",
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            metrics = self._parse_response(coin_upper, data)

            # Update cache
            self._cache[coin_upper] = (metrics, time.time())

            # Track historical volume
            self._update_historical_volume(coin_upper, metrics.social_volume)

            return metrics

        except requests.RequestException as e:
            logger.warning(f"Failed to fetch social metrics for {coin}: {e}")
            # Return cached data if available
            if coin_upper in self._cache:
                return self._cache[coin_upper][0]
            return self._empty_metrics(coin_upper)

    def get_all_metrics(self, coins: List[str]) -> Dict[str, SocialMetrics]:
        """Get social metrics for multiple coins.

        Args:
            coins: List of coin symbols

        Returns:
            Dict mapping coin to SocialMetrics
        """
        results = {}
        for coin in coins:
            results[coin.upper()] = self.get_metrics(coin)
        return results

    def detect_social_spike(self, coin: str) -> tuple[bool, Optional[float]]:
        """Detect if a coin has a social volume spike.

        Args:
            coin: Coin symbol

        Returns:
            Tuple of (is_spike, volume_multiplier)
        """
        metrics = self.get_metrics(coin)
        return metrics.has_social_spike, metrics.volume_multiplier

    def get_trending_coins(self, coins: List[str]) -> List[str]:
        """Get coins that are currently trending.

        Args:
            coins: List of coins to check

        Returns:
            List of trending coin symbols
        """
        trending = []
        for coin in coins:
            metrics = self.get_metrics(coin)
            if metrics.is_trending:
                trending.append(coin.upper())
        return trending

    def _parse_response(self, coin: str, data: Dict[str, Any]) -> SocialMetrics:
        """Parse API response into SocialMetrics."""
        # LunarCrush returns data in different formats
        coin_data = data.get("data", data)

        # Handle list response
        if isinstance(coin_data, list) and coin_data:
            coin_data = coin_data[0]

        social_volume = int(coin_data.get("social_volume", 0))
        social_score = float(coin_data.get("social_score", 50))
        sentiment = float(coin_data.get("sentiment", 50))
        galaxy_score = float(coin_data.get("galaxy_score", 50))
        alt_rank = int(coin_data.get("alt_rank", 100))

        # Get historical average
        avg_volume = self._get_average_volume(coin)

        return SocialMetrics(
            coin=coin,
            social_volume=social_volume,
            social_score=social_score,
            sentiment=sentiment,
            galaxy_score=galaxy_score,
            alt_rank=alt_rank,
            avg_social_volume=avg_volume,
            timestamp=datetime.now(timezone.utc)
        )

    def _empty_metrics(self, coin: str) -> SocialMetrics:
        """Return empty metrics when API fails."""
        return SocialMetrics(
            coin=coin,
            social_volume=0,
            social_score=50,
            sentiment=50,
            galaxy_score=50,
            alt_rank=100,
            timestamp=datetime.now(timezone.utc)
        )

    def _update_historical_volume(self, coin: str, volume: int) -> None:
        """Update historical volume tracking."""
        if coin not in self._historical_volumes:
            self._historical_volumes[coin] = []

        history = self._historical_volumes[coin]
        history.append(volume)

        # Keep last 24 data points (24 hours at 1 hour intervals)
        if len(history) > 24:
            self._historical_volumes[coin] = history[-24:]

    def _get_average_volume(self, coin: str) -> Optional[float]:
        """Get average historical volume for a coin."""
        if coin not in self._historical_volumes:
            return None

        history = self._historical_volumes[coin]
        if not history:
            return None

        return sum(history) / len(history)
