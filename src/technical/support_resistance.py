"""Support and Resistance level detection."""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from collections import defaultdict

from .candle_fetcher import CandleFetcher, Candle

logger = logging.getLogger(__name__)


@dataclass
class PriceLevel:
    """A support or resistance price level."""
    price: float
    level_type: str               # "support" or "resistance"
    strength: int                 # Number of touches
    last_touch: datetime
    zone_low: float               # Level is actually a zone
    zone_high: float

    def price_in_zone(self, price: float) -> bool:
        """Check if a price is within this level's zone."""
        return self.zone_low <= price <= self.zone_high


@dataclass
class SRLevels:
    """Support and resistance levels for a coin."""
    coin: str
    support_levels: List[PriceLevel] = field(default_factory=list)
    resistance_levels: List[PriceLevel] = field(default_factory=list)
    current_price: float = 0.0
    nearest_support: Optional[PriceLevel] = None
    nearest_resistance: Optional[PriceLevel] = None
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def support_distance_pct(self) -> Optional[float]:
        """Distance to nearest support as percentage."""
        if not self.nearest_support or self.current_price == 0:
            return None
        return ((self.current_price - self.nearest_support.price)
                / self.current_price * 100)

    @property
    def resistance_distance_pct(self) -> Optional[float]:
        """Distance to nearest resistance as percentage."""
        if not self.nearest_resistance or self.current_price == 0:
            return None
        return ((self.nearest_resistance.price - self.current_price)
                / self.current_price * 100)

    @property
    def in_support_zone(self) -> bool:
        """Check if price is in a support zone."""
        if not self.nearest_support:
            return False
        return self.nearest_support.price_in_zone(self.current_price)

    @property
    def in_resistance_zone(self) -> bool:
        """Check if price is in a resistance zone."""
        if not self.nearest_resistance:
            return False
        return self.nearest_resistance.price_in_zone(self.current_price)


class SRLevelDetector:
    """Detects support and resistance levels from price history.

    Support: Price levels where buying pressure has historically emerged
    Resistance: Price levels where selling pressure has historically emerged

    Usage:
        fetcher = CandleFetcher()
        detector = SRLevelDetector(fetcher)
        levels = detector.detect("BTC")
        print(f"Nearest support: ${levels.nearest_support.price:.2f}")
        print(f"Distance: {levels.support_distance_pct:.1f}% below")
    """

    def __init__(
        self,
        candle_fetcher: CandleFetcher,
        lookback: int = 5,
        tolerance_pct: float = 0.5
    ):
        """Initialize S/R detector.

        Args:
            candle_fetcher: CandleFetcher instance for getting price data
            lookback: Candles on each side to confirm swing point (default 5)
            tolerance_pct: % tolerance for clustering levels (default 0.5%)
        """
        self.candle_fetcher = candle_fetcher
        self.lookback = lookback
        self.tolerance_pct = tolerance_pct

    def detect(
        self,
        coin: str,
        timeframe: str = "4h",
        limit: int = 200
    ) -> SRLevels:
        """Detect support and resistance levels for a coin.

        Args:
            coin: Coin symbol (e.g., "BTC", "ETH")
            timeframe: Candle timeframe (default "4h" for meaningful levels)
            limit: Number of candles to analyze

        Returns:
            SRLevels with detected levels
        """
        candle_data = self.candle_fetcher.get_candles(coin, timeframe, limit=limit)
        candles = candle_data.candles

        if len(candles) < self.lookback * 2 + 1:
            return SRLevels(coin=coin)

        current_price = candles[-1].close

        # Find swing points
        swing_points = self._find_swing_points(candles)

        # Separate into support and resistance
        support_points = [p for p, t in swing_points if t == "support"]
        resistance_points = [p for p, t in swing_points if t == "resistance"]

        # Cluster into levels
        support_levels = self._cluster_levels(support_points, "support")
        resistance_levels = self._cluster_levels(resistance_points, "resistance")

        # Filter levels relative to current price
        # Support should be below current price
        support_levels = [l for l in support_levels if l.price < current_price]
        # Resistance should be above current price
        resistance_levels = [l for l in resistance_levels if l.price > current_price]

        # Sort by proximity to current price
        support_levels.sort(key=lambda l: current_price - l.price)
        resistance_levels.sort(key=lambda l: l.price - current_price)

        # Get nearest levels
        nearest_support = support_levels[0] if support_levels else None
        nearest_resistance = resistance_levels[0] if resistance_levels else None

        return SRLevels(
            coin=coin,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            current_price=current_price,
            nearest_support=nearest_support,
            nearest_resistance=nearest_resistance,
            timestamp=datetime.now()
        )

    def find_swing_points(self, candles: List[Candle]) -> List[tuple[float, str]]:
        """Find swing highs and lows in candle data.

        Public method for testing.

        Args:
            candles: List of candles

        Returns:
            List of (price, type) tuples
        """
        return self._find_swing_points(candles)

    def cluster_levels(
        self,
        points: List[float],
        level_type: str
    ) -> List[PriceLevel]:
        """Cluster price points into levels.

        Public method for testing.

        Args:
            points: List of prices
            level_type: "support" or "resistance"

        Returns:
            List of PriceLevel objects
        """
        return self._cluster_levels(points, level_type)

    def _find_swing_points(self, candles: List[Candle]) -> List[tuple[float, str]]:
        """Find swing highs and lows.

        A swing high: high > all highs in lookback on both sides
        A swing low: low < all lows in lookback on both sides
        """
        points = []
        lookback = self.lookback

        for i in range(lookback, len(candles) - lookback):
            candle = candles[i]

            # Get surrounding candles
            left_candles = candles[i - lookback:i]
            right_candles = candles[i + 1:i + lookback + 1]

            # Check for swing high
            left_highs = [c.high for c in left_candles]
            right_highs = [c.high for c in right_candles]

            if candle.high > max(left_highs) and candle.high > max(right_highs):
                points.append((candle.high, "resistance"))

            # Check for swing low
            left_lows = [c.low for c in left_candles]
            right_lows = [c.low for c in right_candles]

            if candle.low < min(left_lows) and candle.low < min(right_lows):
                points.append((candle.low, "support"))

        return points

    def _cluster_levels(
        self,
        points: List[float],
        level_type: str
    ) -> List[PriceLevel]:
        """Cluster nearby price points into zones.

        Points within tolerance_pct are merged.
        Strength = number of points in cluster.
        """
        if not points:
            return []

        # Sort points
        sorted_points = sorted(points)

        # Cluster points within tolerance
        clusters = []
        current_cluster = [sorted_points[0]]

        for price in sorted_points[1:]:
            # Check if within tolerance of cluster average
            cluster_avg = sum(current_cluster) / len(current_cluster)
            tolerance = cluster_avg * (self.tolerance_pct / 100)

            if abs(price - cluster_avg) <= tolerance:
                current_cluster.append(price)
            else:
                # Save current cluster and start new one
                clusters.append(current_cluster)
                current_cluster = [price]

        # Don't forget the last cluster
        clusters.append(current_cluster)

        # Convert clusters to PriceLevel objects
        levels = []
        for cluster in clusters:
            avg_price = sum(cluster) / len(cluster)
            zone_low = min(cluster)
            zone_high = max(cluster)

            # Expand zone slightly
            zone_range = avg_price * (self.tolerance_pct / 100)
            zone_low = min(zone_low, avg_price - zone_range)
            zone_high = max(zone_high, avg_price + zone_range)

            levels.append(PriceLevel(
                price=avg_price,
                level_type=level_type,
                strength=len(cluster),
                last_touch=datetime.now(),
                zone_low=zone_low,
                zone_high=zone_high
            ))

        # Sort by strength (most touches first)
        levels.sort(key=lambda l: l.strength, reverse=True)

        return levels
