"""VWAP (Volume-Weighted Average Price) calculator."""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from .candle_fetcher import CandleFetcher, Candle

logger = logging.getLogger(__name__)


@dataclass
class VWAPData:
    """VWAP calculation result."""
    coin: str
    vwap: float                   # Volume-weighted average price
    current_price: float          # Current price
    deviation_pct: float          # % above/below VWAP
    timestamp: datetime

    @property
    def is_above_vwap(self) -> bool:
        """Price is above VWAP."""
        return self.current_price > self.vwap

    @property
    def is_below_vwap(self) -> bool:
        """Price is below VWAP."""
        return self.current_price < self.vwap

    @property
    def position(self) -> str:
        """Position relative to VWAP."""
        if self.deviation_pct > 2:
            return "extended_above"
        if self.deviation_pct < -2:
            return "extended_below"
        if self.is_above_vwap:
            return "above"
        return "below"

    @property
    def mean_reversion_signal(self) -> Optional[str]:
        """Mean reversion signal based on deviation."""
        if self.deviation_pct > 3:
            return "SHORT"  # Extended above, likely to revert
        if self.deviation_pct < -3:
            return "LONG"   # Extended below, likely to revert
        return None


class VWAPCalculator:
    """Calculates VWAP (Volume-Weighted Average Price).

    VWAP is used by institutional traders as a benchmark for fair value.
    Price extended from VWAP often reverts back.

    Usage:
        fetcher = CandleFetcher()
        vwap = VWAPCalculator(fetcher)
        data = vwap.calculate("BTC")
        print(f"BTC VWAP: ${data.vwap:.2f}, deviation: {data.deviation_pct:+.1f}%")
    """

    def __init__(self, candle_fetcher: CandleFetcher):
        """Initialize VWAP calculator.

        Args:
            candle_fetcher: CandleFetcher instance for getting price data
        """
        self.candle_fetcher = candle_fetcher

    def calculate(
        self,
        coin: str,
        timeframe: str = "1h",
        use_daily_reset: bool = True
    ) -> VWAPData:
        """Calculate VWAP for a coin.

        Args:
            coin: Coin symbol (e.g., "BTC", "ETH")
            timeframe: Candle timeframe (default "1h")
            use_daily_reset: Reset VWAP at UTC midnight (default True)

        Returns:
            VWAPData with VWAP and deviation
        """
        # Get candles
        candle_data = self.candle_fetcher.get_candles(coin, timeframe, limit=200)
        candles = candle_data.candles

        if not candles:
            return VWAPData(
                coin=coin,
                vwap=0.0,
                current_price=0.0,
                deviation_pct=0.0,
                timestamp=datetime.now()
            )

        # Filter to current day if using daily reset
        if use_daily_reset:
            candles = self._filter_to_today(candles)

        if not candles:
            # No candles for today yet, use last candle as reference
            candles = candle_data.candles[-1:]

        # Calculate VWAP
        vwap = self._calculate_vwap(candles)
        current_price = candles[-1].close

        # Calculate deviation
        deviation_pct = 0.0
        if vwap > 0:
            deviation_pct = ((current_price - vwap) / vwap) * 100

        return VWAPData(
            coin=coin,
            vwap=vwap,
            current_price=current_price,
            deviation_pct=deviation_pct,
            timestamp=datetime.now()
        )

    def calculate_from_candles(self, candles: List[Candle]) -> float:
        """Calculate VWAP from a list of candles.

        Useful for testing or when you already have candle data.

        Args:
            candles: List of Candle objects

        Returns:
            VWAP value
        """
        return self._calculate_vwap(candles)

    def get_bands(
        self,
        coin: str,
        std_multiplier: float = 2.0
    ) -> tuple[float, float, float]:
        """Calculate VWAP with standard deviation bands.

        Args:
            coin: Coin symbol
            std_multiplier: Multiplier for bands (default 2.0)

        Returns:
            Tuple of (vwap, upper_band, lower_band)
        """
        candle_data = self.candle_fetcher.get_candles(coin, "1h", limit=200)
        candles = self._filter_to_today(candle_data.candles)

        if not candles:
            return 0.0, 0.0, 0.0

        vwap = self._calculate_vwap(candles)

        # Calculate standard deviation of typical price from VWAP
        typical_prices = [(c.high + c.low + c.close) / 3 for c in candles]
        squared_deviations = [(tp - vwap) ** 2 for tp in typical_prices]

        if not squared_deviations:
            return vwap, vwap, vwap

        variance = sum(squared_deviations) / len(squared_deviations)
        std_dev = variance ** 0.5

        upper_band = vwap + (std_dev * std_multiplier)
        lower_band = vwap - (std_dev * std_multiplier)

        return vwap, upper_band, lower_band

    def _calculate_vwap(self, candles: List[Candle]) -> float:
        """Calculate VWAP from candles.

        VWAP = Cumulative(Typical Price * Volume) / Cumulative(Volume)
        Typical Price = (High + Low + Close) / 3
        """
        if not candles:
            return 0.0

        cumulative_tpv = 0.0  # Typical Price * Volume
        cumulative_vol = 0.0

        for candle in candles:
            typical_price = (candle.high + candle.low + candle.close) / 3
            cumulative_tpv += typical_price * candle.volume
            cumulative_vol += candle.volume

        if cumulative_vol == 0:
            # No volume, return simple average of closes
            return sum(c.close for c in candles) / len(candles)

        return cumulative_tpv / cumulative_vol

    def _filter_to_today(self, candles: List[Candle]) -> List[Candle]:
        """Filter candles to current UTC day only."""
        if not candles:
            return []

        # Get start of current UTC day
        now_utc = datetime.now(timezone.utc)
        day_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        day_start_ms = int(day_start.timestamp() * 1000)

        # Filter candles
        today_candles = [c for c in candles if c.timestamp >= day_start_ms]

        return today_candles
