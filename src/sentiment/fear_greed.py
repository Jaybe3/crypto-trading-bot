"""Fear & Greed Index fetcher from Alternative.me API."""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List
import requests

logger = logging.getLogger(__name__)


@dataclass
class FearGreedData:
    """Fear & Greed Index data point."""
    value: int                    # 0-100
    classification: str           # "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
    timestamp: datetime

    @property
    def is_extreme_fear(self) -> bool:
        """Market in extreme fear (potential buying opportunity)."""
        return self.value < 25

    @property
    def is_extreme_greed(self) -> bool:
        """Market in extreme greed (potential selling opportunity)."""
        return self.value > 75


class FearGreedFetcher:
    """Fetches Crypto Fear & Greed Index from Alternative.me.

    The index measures market sentiment on a 0-100 scale:
    - 0-24: Extreme Fear
    - 25-44: Fear
    - 45-55: Neutral
    - 56-74: Greed
    - 75-100: Extreme Greed

    Usage:
        fetcher = FearGreedFetcher()
        data = fetcher.get_current()
        print(f"Fear & Greed: {data.value} ({data.classification})")
    """

    API_URL = "https://api.alternative.me/fng/"

    def __init__(self, cache_ttl_minutes: int = 60):
        """Initialize fetcher with cache TTL.

        Args:
            cache_ttl_minutes: Cache duration (default 60 min, index updates daily)
        """
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self._cached_data: Optional[FearGreedData] = None
        self._cache_time: Optional[datetime] = None
        self._retry_count = 3
        self._retry_delay = 1  # seconds

    def get_current(self) -> Optional[FearGreedData]:
        """Get current Fear & Greed value.

        Returns cached value if fresh, otherwise fetches from API.
        Returns None if API fails and no cached value available.
        """
        # Return cached if valid
        if self._is_cache_valid():
            return self._cached_data

        # Fetch with retries
        for attempt in range(self._retry_count):
            try:
                data = self._fetch_from_api()
                if data:
                    self._cached_data = data
                    self._cache_time = datetime.now()
                    return data
            except Exception as e:
                logger.warning(f"Fear & Greed API attempt {attempt + 1} failed: {e}")
                if attempt < self._retry_count - 1:
                    import time
                    time.sleep(self._retry_delay * (attempt + 1))

        # All retries failed - return cached if available
        if self._cached_data:
            logger.warning("Using stale Fear & Greed data after API failure")
            return self._cached_data

        logger.error("Failed to fetch Fear & Greed Index, no cached data available")
        return None

    def get_historical(self, days: int = 7) -> List[FearGreedData]:
        """Get historical Fear & Greed values.

        Args:
            days: Number of days of history (max ~30 on free tier)

        Returns:
            List of FearGreedData, newest first
        """
        try:
            response = requests.get(
                f"{self.API_URL}?limit={days}",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("data", []):
                results.append(FearGreedData(
                    value=int(item["value"]),
                    classification=item["value_classification"],
                    timestamp=datetime.fromtimestamp(int(item["timestamp"]))
                ))
            return results

        except Exception as e:
            logger.error(f"Failed to fetch historical Fear & Greed: {e}")
            return []

    def _fetch_from_api(self) -> Optional[FearGreedData]:
        """Fetch current value from API."""
        response = requests.get(self.API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "data" not in data or not data["data"]:
            raise ValueError("Invalid API response: missing data")

        current = data["data"][0]

        return FearGreedData(
            value=int(current["value"]),
            classification=current["value_classification"],
            timestamp=datetime.fromtimestamp(int(current["timestamp"]))
        )

    def _is_cache_valid(self) -> bool:
        """Check if cached data is still fresh."""
        if self._cached_data is None or self._cache_time is None:
            return False

        age = datetime.now() - self._cache_time
        if age > self.cache_ttl:
            return False

        # Warn if data is >24 hours old (stale)
        data_age = datetime.now() - self._cached_data.timestamp
        if data_age > timedelta(hours=24):
            logger.warning(f"Fear & Greed data is {data_age.total_seconds()/3600:.1f}h old")

        return True
