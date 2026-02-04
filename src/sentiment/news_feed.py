"""News feed integration for market-moving news detection."""
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

import requests

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """A single news item."""
    title: str
    coins: List[str]
    published_at: datetime
    sentiment_score: float          # -1 to +1
    is_breaking: bool               # Published < 1 hour ago
    source: str
    url: Optional[str] = None

    @property
    def is_bullish(self) -> bool:
        """News sentiment is bullish (>0.3)."""
        return self.sentiment_score > 0.3

    @property
    def is_bearish(self) -> bool:
        """News sentiment is bearish (<-0.3)."""
        return self.sentiment_score < -0.3

    @property
    def is_neutral(self) -> bool:
        """News sentiment is neutral."""
        return not self.is_bullish and not self.is_bearish

    @property
    def sentiment_label(self) -> str:
        """Human-readable sentiment label."""
        if self.is_bullish:
            return "bullish"
        if self.is_bearish:
            return "bearish"
        return "neutral"


@dataclass
class NewsFeed:
    """Collection of news items for analysis."""
    items: List[NewsItem] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def breaking_news(self) -> List[NewsItem]:
        """Get only breaking news items."""
        return [item for item in self.items if item.is_breaking]

    @property
    def bullish_count(self) -> int:
        """Count of bullish news items."""
        return sum(1 for item in self.items if item.is_bullish)

    @property
    def bearish_count(self) -> int:
        """Count of bearish news items."""
        return sum(1 for item in self.items if item.is_bearish)

    @property
    def overall_sentiment(self) -> float:
        """Average sentiment across all items."""
        if not self.items:
            return 0.0
        return sum(item.sentiment_score for item in self.items) / len(self.items)

    def for_coin(self, coin: str) -> List[NewsItem]:
        """Get news items mentioning a specific coin."""
        coin_upper = coin.upper()
        return [item for item in self.items if coin_upper in item.coins]


class NewsFeedFetcher:
    """Fetches and analyzes crypto news from CryptoPanic.

    CryptoPanic aggregates news from multiple sources and provides
    community voting for sentiment analysis.

    Usage:
        fetcher = NewsFeedFetcher(api_token="your_token")
        feed = fetcher.get_news()
        for item in feed.breaking_news:
            print(f"{item.title} - {item.sentiment_label}")
    """

    BASE_URL = "https://cryptopanic.com/api/v1/posts/"
    CACHE_TTL = 300  # 5 minutes
    RATE_LIMIT_INTERVAL = 12  # 5 requests per minute = 1 per 12 seconds

    def __init__(self, api_token: Optional[str] = None):
        """Initialize news fetcher.

        Args:
            api_token: CryptoPanic API token (optional for public endpoints)
        """
        self.api_token = api_token
        self._cache: Optional[NewsFeed] = None
        self._cache_time: float = 0
        self._last_request_time: float = 0

    def get_news(
        self,
        filter_type: str = "hot",
        currencies: Optional[List[str]] = None
    ) -> NewsFeed:
        """Get news feed from CryptoPanic.

        Args:
            filter_type: Filter type (hot, rising, bullish, bearish, important)
            currencies: List of currencies to filter (e.g., ["BTC", "ETH"])

        Returns:
            NewsFeed with news items
        """
        # Check cache
        if self._cache and (time.time() - self._cache_time) < self.CACHE_TTL:
            return self._cache

        # Rate limiting
        self._wait_for_rate_limit()

        try:
            params = self._build_params(filter_type, currencies)
            response = requests.get(
                self.BASE_URL,
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            feed = self._parse_response(data)

            # Update cache
            self._cache = feed
            self._cache_time = time.time()

            return feed

        except requests.RequestException as e:
            logger.warning(f"Failed to fetch news: {e}")
            # Return cached data if available
            if self._cache:
                return self._cache
            return NewsFeed()

    def get_news_for_coin(self, coin: str) -> List[NewsItem]:
        """Get news specifically for a coin.

        Args:
            coin: Coin symbol (e.g., "BTC")

        Returns:
            List of NewsItem for the coin
        """
        feed = self.get_news(currencies=[coin])
        return feed.for_coin(coin)

    def get_breaking_news(self) -> List[NewsItem]:
        """Get only breaking news (< 1 hour old).

        Returns:
            List of breaking NewsItem
        """
        feed = self.get_news(filter_type="important")
        return feed.breaking_news

    def calculate_sentiment(
        self,
        positive_votes: int,
        negative_votes: int
    ) -> float:
        """Calculate sentiment score from votes.

        Args:
            positive_votes: Number of positive votes
            negative_votes: Number of negative votes

        Returns:
            Sentiment score from -1 to +1
        """
        total = positive_votes + negative_votes
        if total == 0:
            return 0.0
        return (positive_votes - negative_votes) / total

    def _build_params(
        self,
        filter_type: str,
        currencies: Optional[List[str]]
    ) -> Dict[str, str]:
        """Build API request parameters."""
        params: Dict[str, str] = {
            "filter": filter_type,
            "public": "true"
        }

        if self.api_token:
            params["auth_token"] = self.api_token

        if currencies:
            params["currencies"] = ",".join(currencies)

        return params

    def _parse_response(self, data: Dict[str, Any]) -> NewsFeed:
        """Parse API response into NewsFeed."""
        items = []
        now = datetime.now(timezone.utc)

        for post in data.get("results", []):
            try:
                # Parse published time
                published_str = post.get("published_at", "")
                try:
                    published_at = datetime.fromisoformat(
                        published_str.replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    published_at = now

                # Check if breaking (< 1 hour old)
                age_hours = (now - published_at).total_seconds() / 3600
                is_breaking = age_hours < 1

                # Extract coins mentioned
                currencies = post.get("currencies", [])
                coins = [c.get("code", "") for c in currencies if c.get("code")]

                # Calculate sentiment from votes
                votes = post.get("votes", {})
                positive = votes.get("positive", 0)
                negative = votes.get("negative", 0)
                sentiment_score = self.calculate_sentiment(positive, negative)

                # Get source
                source = post.get("source", {}).get("title", "Unknown")

                items.append(NewsItem(
                    title=post.get("title", ""),
                    coins=coins,
                    published_at=published_at,
                    sentiment_score=sentiment_score,
                    is_breaking=is_breaking,
                    source=source,
                    url=post.get("url")
                ))

            except Exception as e:
                logger.debug(f"Failed to parse news item: {e}")
                continue

        return NewsFeed(items=items, timestamp=now)

    def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.RATE_LIMIT_INTERVAL:
            time.sleep(self.RATE_LIMIT_INTERVAL - elapsed)
        self._last_request_time = time.time()
