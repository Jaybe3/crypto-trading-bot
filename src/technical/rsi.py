"""RSI (Relative Strength Index) calculator for overbought/oversold detection."""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from .candle_fetcher import CandleFetcher

logger = logging.getLogger(__name__)


@dataclass
class RSIData:
    """RSI calculation result."""
    coin: str
    value: float              # 0-100
    period: int
    timeframe: str
    timestamp: datetime

    @property
    def is_overbought(self) -> bool:
        """RSI > 70 indicates overbought condition."""
        return self.value > 70

    @property
    def is_oversold(self) -> bool:
        """RSI < 30 indicates oversold condition."""
        return self.value < 30

    @property
    def condition(self) -> str:
        """Human-readable condition."""
        if self.is_oversold:
            return "oversold"
        if self.is_overbought:
            return "overbought"
        return "neutral"


class RSICalculator:
    """Calculates RSI (Relative Strength Index) for coins.

    RSI measures momentum on a 0-100 scale:
    - 0-30: Oversold (potential buying opportunity)
    - 30-70: Neutral
    - 70-100: Overbought (potential selling opportunity)

    Usage:
        fetcher = CandleFetcher()
        rsi = RSICalculator(fetcher)
        data = rsi.calculate("BTC", timeframe="1h")
        print(f"BTC RSI: {data.value:.1f} ({data.condition})")
    """

    def __init__(self, candle_fetcher: CandleFetcher, default_period: int = 14):
        """Initialize RSI calculator.

        Args:
            candle_fetcher: CandleFetcher instance for getting price data
            default_period: Default RSI period (standard is 14)
        """
        self.candle_fetcher = candle_fetcher
        self.default_period = default_period

    def calculate(
        self,
        coin: str,
        timeframe: str = "1h",
        period: Optional[int] = None
    ) -> RSIData:
        """Calculate RSI for a coin.

        Args:
            coin: Coin symbol (e.g., "BTC", "ETH")
            timeframe: Candle timeframe (e.g., "15m", "1h", "4h")
            period: RSI period (default 14)

        Returns:
            RSIData with calculated RSI value
        """
        period = period or self.default_period

        # Need period + 1 candles to calculate period price changes
        candle_data = self.candle_fetcher.get_candles(coin, timeframe, limit=period + 50)
        closes = candle_data.closes()

        if len(closes) < period + 1:
            logger.warning(f"Insufficient data for RSI: {len(closes)} candles, need {period + 1}")
            return RSIData(
                coin=coin,
                value=50.0,  # Neutral default
                period=period,
                timeframe=timeframe,
                timestamp=datetime.now()
            )

        rsi_value = self._calculate_rsi(closes, period)

        return RSIData(
            coin=coin,
            value=rsi_value,
            period=period,
            timeframe=timeframe,
            timestamp=datetime.now()
        )

    def calculate_from_closes(self, closes: List[float], period: int = 14) -> float:
        """Calculate RSI from a list of close prices.

        Useful for testing or when you already have price data.

        Args:
            closes: List of close prices (oldest first)
            period: RSI period

        Returns:
            RSI value (0-100)
        """
        if len(closes) < period + 1:
            return 50.0
        return self._calculate_rsi(closes, period)

    def _calculate_rsi(self, closes: List[float], period: int) -> float:
        """Internal RSI calculation using Wilder's smoothing method.

        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss

        Uses exponential moving average (Wilder's smoothing) for accuracy.
        """
        if len(closes) < period + 1:
            return 50.0

        # Calculate price changes
        deltas = []
        for i in range(1, len(closes)):
            deltas.append(closes[i] - closes[i - 1])

        # Separate gains and losses
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        # Initial averages (simple average for first period)
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        # Apply Wilder's smoothing for remaining periods
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        # Calculate RSI
        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def get_multi_timeframe(
        self,
        coin: str,
        timeframes: List[str] = None
    ) -> dict[str, RSIData]:
        """Get RSI across multiple timeframes.

        Args:
            coin: Coin symbol
            timeframes: List of timeframes (default: ["15m", "1h", "4h"])

        Returns:
            Dict mapping timeframe to RSIData
        """
        timeframes = timeframes or ["15m", "1h", "4h"]
        results = {}

        for tf in timeframes:
            results[tf] = self.calculate(coin, tf)

        return results
