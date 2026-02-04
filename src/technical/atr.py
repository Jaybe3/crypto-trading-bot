"""ATR (Average True Range) calculator for volatility measurement."""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from .candle_fetcher import CandleFetcher, Candle

logger = logging.getLogger(__name__)


@dataclass
class ATRData:
    """ATR calculation result."""
    coin: str
    atr: float                # Absolute ATR value
    atr_pct: float            # ATR as percentage of price
    period: int
    current_price: float
    timeframe: str
    timestamp: datetime

    @property
    def volatility_level(self) -> str:
        """Classify volatility level based on ATR percentage."""
        if self.atr_pct > 5:
            return "extreme"
        if self.atr_pct > 3:
            return "high"
        if self.atr_pct > 1.5:
            return "moderate"
        return "low"

    def suggested_stop_loss(self, multiplier: float = 1.5) -> float:
        """Get suggested stop-loss distance based on ATR.

        Args:
            multiplier: ATR multiplier (1.5-2.0 typical)

        Returns:
            Stop-loss distance in price units
        """
        return self.atr * multiplier

    def suggested_stop_price(self, entry_price: float, direction: str, multiplier: float = 1.5) -> float:
        """Get suggested stop-loss price.

        Args:
            entry_price: Trade entry price
            direction: "LONG" or "SHORT"
            multiplier: ATR multiplier

        Returns:
            Stop-loss price
        """
        distance = self.suggested_stop_loss(multiplier)
        if direction.upper() == "LONG":
            return entry_price - distance
        return entry_price + distance


class ATRCalculator:
    """Calculates ATR (Average True Range) for volatility measurement.

    ATR measures market volatility by analyzing the range of price movement.
    Higher ATR = more volatile = wider stops needed.

    Usage:
        fetcher = CandleFetcher()
        atr = ATRCalculator(fetcher)
        data = atr.calculate("BTC", timeframe="1h")
        print(f"BTC ATR: ${data.atr:.2f} ({data.volatility_level})")
        print(f"Suggested SL: ${data.suggested_stop_loss():.2f}")
    """

    def __init__(self, candle_fetcher: CandleFetcher, default_period: int = 14):
        """Initialize ATR calculator.

        Args:
            candle_fetcher: CandleFetcher instance for getting price data
            default_period: Default ATR period (standard is 14)
        """
        self.candle_fetcher = candle_fetcher
        self.default_period = default_period

    def calculate(
        self,
        coin: str,
        timeframe: str = "1h",
        period: Optional[int] = None
    ) -> ATRData:
        """Calculate ATR for a coin.

        Args:
            coin: Coin symbol (e.g., "BTC", "ETH")
            timeframe: Candle timeframe (e.g., "15m", "1h", "4h")
            period: ATR period (default 14)

        Returns:
            ATRData with calculated ATR value
        """
        period = period or self.default_period

        # Need period + 1 candles for true range calculation
        candle_data = self.candle_fetcher.get_candles(coin, timeframe, limit=period + 50)
        candles = candle_data.candles

        if len(candles) < period + 1:
            logger.warning(f"Insufficient data for ATR: {len(candles)} candles, need {period + 1}")
            # Return a default based on current price
            current_price = candles[-1].close if candles else 0
            return ATRData(
                coin=coin,
                atr=current_price * 0.02,  # 2% default
                atr_pct=2.0,
                period=period,
                current_price=current_price,
                timeframe=timeframe,
                timestamp=datetime.now()
            )

        atr_value = self._calculate_atr(candles, period)
        current_price = candles[-1].close
        atr_pct = (atr_value / current_price * 100) if current_price > 0 else 0

        return ATRData(
            coin=coin,
            atr=atr_value,
            atr_pct=atr_pct,
            period=period,
            current_price=current_price,
            timeframe=timeframe,
            timestamp=datetime.now()
        )

    def calculate_from_candles(self, candles: List[Candle], period: int = 14) -> float:
        """Calculate ATR from a list of candles.

        Useful for testing or when you already have candle data.

        Args:
            candles: List of Candle objects (oldest first)
            period: ATR period

        Returns:
            ATR value
        """
        if len(candles) < period + 1:
            return 0.0
        return self._calculate_atr(candles, period)

    def _calculate_atr(self, candles: List[Candle], period: int) -> float:
        """Internal ATR calculation using Wilder's smoothing.

        True Range = max of:
        1. Current High - Current Low
        2. abs(Current High - Previous Close)
        3. abs(Current Low - Previous Close)

        ATR = Smoothed average of True Range
        """
        if len(candles) < period + 1:
            return 0.0

        # Calculate True Range for each candle
        true_ranges = []
        for i in range(1, len(candles)):
            tr = self._true_range(candles[i], candles[i - 1].close)
            true_ranges.append(tr)

        # Initial ATR (simple average for first period)
        atr = sum(true_ranges[:period]) / period

        # Apply Wilder's smoothing for remaining periods
        for i in range(period, len(true_ranges)):
            atr = (atr * (period - 1) + true_ranges[i]) / period

        return atr

    def _true_range(self, candle: Candle, prev_close: float) -> float:
        """Calculate True Range for a single candle.

        TR = max(H-L, |H-PC|, |L-PC|)
        """
        return max(
            candle.high - candle.low,
            abs(candle.high - prev_close),
            abs(candle.low - prev_close)
        )

    def get_position_size_modifier(self, coin: str, target_risk_pct: float = 2.0) -> float:
        """Get position size modifier based on volatility.

        Higher volatility = smaller position to maintain consistent risk.

        Args:
            coin: Coin symbol
            target_risk_pct: Target risk percentage (default 2%)

        Returns:
            Multiplier for position size (e.g., 0.5 = half size)
        """
        data = self.calculate(coin)

        # If ATR% matches target, modifier = 1.0
        # If ATR% is 2x target, modifier = 0.5
        if data.atr_pct <= 0:
            return 1.0

        modifier = target_risk_pct / data.atr_pct

        # Clamp between 0.25 and 2.0
        return max(0.25, min(2.0, modifier))

    def get_dynamic_stops(
        self,
        coin: str,
        direction: str,
        entry_price: float,
        sl_multiplier: float = 1.5,
        tp_multiplier: float = 2.0
    ) -> Tuple[float, float]:
        """Calculate dynamic stop-loss and take-profit based on ATR.

        Args:
            coin: Coin symbol
            direction: "LONG" or "SHORT"
            entry_price: Trade entry price
            sl_multiplier: ATR multiplier for stop-loss
            tp_multiplier: ATR multiplier for take-profit

        Returns:
            Tuple of (stop_loss_price, take_profit_price)
        """
        data = self.calculate(coin)

        sl_distance = data.atr * sl_multiplier
        tp_distance = data.atr * tp_multiplier

        if direction.upper() == "LONG":
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
        else:
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance

        return stop_loss, take_profit
