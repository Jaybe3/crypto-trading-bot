"""Volume Profile analysis for identifying key price levels."""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from collections import defaultdict

from .candle_fetcher import CandleFetcher, Candle

logger = logging.getLogger(__name__)


@dataclass
class VolumeLevel:
    """A price level with associated volume."""
    price: float
    volume: float
    pct_of_total: float             # Percentage of total volume


@dataclass
class VolumeProfile:
    """Volume profile analysis result."""
    coin: str
    poc: float                      # Point of Control (highest volume price)
    value_area_high: float          # Top of Value Area (70% of volume)
    value_area_low: float           # Bottom of Value Area
    hvn_levels: List[float]         # High Volume Nodes
    lvn_levels: List[float]         # Low Volume Nodes
    current_price: float
    total_volume: float
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_in_value_area(self) -> bool:
        """Check if current price is within value area."""
        return self.value_area_low <= self.current_price <= self.value_area_high

    @property
    def position_vs_poc(self) -> str:
        """Position relative to Point of Control."""
        if self.current_price > self.poc * 1.001:  # 0.1% tolerance
            return "above_poc"
        if self.current_price < self.poc * 0.999:
            return "below_poc"
        return "at_poc"

    @property
    def distance_to_poc_pct(self) -> float:
        """Distance to POC as percentage."""
        if self.poc == 0:
            return 0.0
        return ((self.current_price - self.poc) / self.poc) * 100

    @property
    def value_area_width_pct(self) -> float:
        """Width of value area as percentage."""
        if self.value_area_low == 0:
            return 0.0
        return ((self.value_area_high - self.value_area_low) / self.value_area_low) * 100

    @property
    def nearest_hvn(self) -> Optional[float]:
        """Nearest high volume node to current price."""
        if not self.hvn_levels:
            return None
        return min(self.hvn_levels, key=lambda x: abs(x - self.current_price))

    @property
    def nearest_lvn(self) -> Optional[float]:
        """Nearest low volume node to current price."""
        if not self.lvn_levels:
            return None
        return min(self.lvn_levels, key=lambda x: abs(x - self.current_price))


class VolumeProfileCalculator:
    """Calculates Volume Profile from candle data.

    Volume Profile shows where trading activity occurred at each price level.
    Key levels:
    - POC (Point of Control): Price with highest volume - strong S/R
    - Value Area: Price range containing 70% of volume
    - HVN (High Volume Nodes): Prices with significant volume - support/resistance
    - LVN (Low Volume Nodes): Prices with low volume - price moves quickly through

    Usage:
        fetcher = CandleFetcher()
        calculator = VolumeProfileCalculator(fetcher)
        profile = calculator.calculate("BTC")
        print(f"POC: ${profile.poc:.2f}")
        print(f"Value Area: ${profile.value_area_low:.2f} - ${profile.value_area_high:.2f}")
    """

    def __init__(
        self,
        candle_fetcher: CandleFetcher,
        num_levels: int = 50,
        value_area_pct: float = 0.70
    ):
        """Initialize Volume Profile calculator.

        Args:
            candle_fetcher: CandleFetcher instance for getting price data
            num_levels: Number of price levels to divide range into
            value_area_pct: Percentage of volume for value area (default 70%)
        """
        self.candle_fetcher = candle_fetcher
        self.num_levels = num_levels
        self.value_area_pct = value_area_pct

    def calculate(
        self,
        coin: str,
        timeframe: str = "1h",
        limit: int = 200
    ) -> VolumeProfile:
        """Calculate volume profile for a coin.

        Args:
            coin: Coin symbol (e.g., "BTC", "ETH")
            timeframe: Candle timeframe (default "1h")
            limit: Number of candles to analyze

        Returns:
            VolumeProfile with POC, Value Area, and volume nodes
        """
        candle_data = self.candle_fetcher.get_candles(coin, timeframe, limit=limit)
        candles = candle_data.candles

        if not candles:
            return self._empty_profile(coin)

        current_price = candles[-1].close

        # Build volume distribution
        volume_dist = self._build_volume_distribution(candles)

        if not volume_dist:
            return self._empty_profile(coin, current_price)

        # Calculate POC
        poc = self._calculate_poc(volume_dist)

        # Calculate Value Area
        value_area_low, value_area_high = self._calculate_value_area(volume_dist)

        # Find HVN and LVN levels
        hvn_levels = self._find_hvn_levels(volume_dist)
        lvn_levels = self._find_lvn_levels(volume_dist)

        total_volume = sum(v for v in volume_dist.values())

        return VolumeProfile(
            coin=coin,
            poc=poc,
            value_area_high=value_area_high,
            value_area_low=value_area_low,
            hvn_levels=hvn_levels,
            lvn_levels=lvn_levels,
            current_price=current_price,
            total_volume=total_volume,
            timestamp=datetime.now()
        )

    def calculate_from_candles(self, candles: List[Candle], coin: str = "UNKNOWN") -> VolumeProfile:
        """Calculate volume profile from a list of candles.

        Useful for testing or when you already have candle data.

        Args:
            candles: List of Candle objects
            coin: Coin symbol for the result

        Returns:
            VolumeProfile
        """
        if not candles:
            return self._empty_profile(coin)

        current_price = candles[-1].close
        volume_dist = self._build_volume_distribution(candles)

        if not volume_dist:
            return self._empty_profile(coin, current_price)

        poc = self._calculate_poc(volume_dist)
        value_area_low, value_area_high = self._calculate_value_area(volume_dist)
        hvn_levels = self._find_hvn_levels(volume_dist)
        lvn_levels = self._find_lvn_levels(volume_dist)
        total_volume = sum(v for v in volume_dist.values())

        return VolumeProfile(
            coin=coin,
            poc=poc,
            value_area_high=value_area_high,
            value_area_low=value_area_low,
            hvn_levels=hvn_levels,
            lvn_levels=lvn_levels,
            current_price=current_price,
            total_volume=total_volume,
            timestamp=datetime.now()
        )

    def _build_volume_distribution(self, candles: List[Candle]) -> dict[float, float]:
        """Build volume distribution across price levels."""
        if not candles:
            return {}

        # Find price range
        all_highs = [c.high for c in candles]
        all_lows = [c.low for c in candles]
        price_high = max(all_highs)
        price_low = min(all_lows)

        if price_high == price_low:
            return {price_high: sum(c.volume for c in candles)}

        # Calculate level size
        level_size = (price_high - price_low) / self.num_levels

        # Distribute volume across levels
        volume_dist: dict[float, float] = defaultdict(float)

        for candle in candles:
            # Distribute candle volume across its price range
            candle_levels = self._get_candle_levels(
                candle, price_low, level_size
            )
            vol_per_level = candle.volume / len(candle_levels) if candle_levels else 0

            for level in candle_levels:
                volume_dist[level] += vol_per_level

        return dict(volume_dist)

    def _get_candle_levels(
        self,
        candle: Candle,
        price_low: float,
        level_size: float
    ) -> List[float]:
        """Get price levels that a candle spans."""
        if level_size == 0:
            return [candle.close]

        start_level = int((candle.low - price_low) / level_size)
        end_level = int((candle.high - price_low) / level_size)

        levels = []
        for i in range(start_level, end_level + 1):
            level_price = price_low + (i + 0.5) * level_size
            levels.append(round(level_price, 8))

        return levels if levels else [candle.close]

    def _calculate_poc(self, volume_dist: dict[float, float]) -> float:
        """Calculate Point of Control (highest volume price)."""
        if not volume_dist:
            return 0.0
        return max(volume_dist.keys(), key=lambda x: volume_dist[x])

    def _calculate_value_area(
        self,
        volume_dist: dict[float, float]
    ) -> tuple[float, float]:
        """Calculate Value Area (70% of volume centered on POC)."""
        if not volume_dist:
            return 0.0, 0.0

        total_volume = sum(volume_dist.values())
        target_volume = total_volume * self.value_area_pct

        # Sort levels by price
        sorted_levels = sorted(volume_dist.keys())
        poc = self._calculate_poc(volume_dist)
        poc_idx = sorted_levels.index(poc) if poc in sorted_levels else len(sorted_levels) // 2

        # Expand from POC until we have 70% of volume
        accumulated_volume = volume_dist.get(poc, 0)
        low_idx = poc_idx
        high_idx = poc_idx

        while accumulated_volume < target_volume:
            # Check which direction to expand
            can_go_lower = low_idx > 0
            can_go_higher = high_idx < len(sorted_levels) - 1

            if not can_go_lower and not can_go_higher:
                break

            lower_vol = volume_dist.get(sorted_levels[low_idx - 1], 0) if can_go_lower else 0
            higher_vol = volume_dist.get(sorted_levels[high_idx + 1], 0) if can_go_higher else 0

            if lower_vol >= higher_vol and can_go_lower:
                low_idx -= 1
                accumulated_volume += lower_vol
            elif can_go_higher:
                high_idx += 1
                accumulated_volume += higher_vol
            elif can_go_lower:
                low_idx -= 1
                accumulated_volume += lower_vol
            else:
                break

        return sorted_levels[low_idx], sorted_levels[high_idx]

    def _find_hvn_levels(self, volume_dist: dict[float, float]) -> List[float]:
        """Find High Volume Nodes (above average volume)."""
        if not volume_dist:
            return []

        avg_volume = sum(volume_dist.values()) / len(volume_dist)
        threshold = avg_volume * 1.5  # 50% above average

        hvn = [price for price, vol in volume_dist.items() if vol > threshold]
        return sorted(hvn)

    def _find_lvn_levels(self, volume_dist: dict[float, float]) -> List[float]:
        """Find Low Volume Nodes (below average volume)."""
        if not volume_dist:
            return []

        avg_volume = sum(volume_dist.values()) / len(volume_dist)
        threshold = avg_volume * 0.5  # 50% below average

        lvn = [price for price, vol in volume_dist.items() if vol < threshold]
        return sorted(lvn)

    def _empty_profile(self, coin: str, current_price: float = 0.0) -> VolumeProfile:
        """Return empty profile when no data available."""
        return VolumeProfile(
            coin=coin,
            poc=current_price,
            value_area_high=current_price,
            value_area_low=current_price,
            hvn_levels=[],
            lvn_levels=[],
            current_price=current_price,
            total_volume=0.0,
            timestamp=datetime.now()
        )
