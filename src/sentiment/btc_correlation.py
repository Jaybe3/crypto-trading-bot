"""BTC Correlation Tracker for detecting market-wide vs coin-specific moves."""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
import statistics

from src.technical.candle_fetcher import CandleFetcher

logger = logging.getLogger(__name__)


@dataclass
class BTCCorrelation:
    """BTC correlation data for a coin."""
    coin: str
    btc_change_1h: float          # BTC % change in last hour
    coin_change_1h: float         # Coin % change in last hour
    correlation_24h: float        # Rolling 24h correlation coefficient (-1 to 1)
    is_btc_driven: bool           # True if move appears BTC-correlated
    timestamp: datetime

    @property
    def move_type(self) -> str:
        """Classify the type of move."""
        if self.is_btc_driven:
            return "btc_correlated"
        if abs(self.coin_change_1h) > 2:
            return "coin_specific"
        return "normal"

    @property
    def correlation_strength(self) -> str:
        """Classify correlation strength."""
        abs_corr = abs(self.correlation_24h)
        if abs_corr > 0.8:
            return "very_strong"
        if abs_corr > 0.6:
            return "strong"
        if abs_corr > 0.4:
            return "moderate"
        if abs_corr > 0.2:
            return "weak"
        return "none"


class BTCCorrelationTracker:
    """Tracks correlation between altcoins and BTC.

    When BTC moves significantly, altcoin moves in the same direction
    are likely correlation, not independent signals.

    Usage:
        fetcher = CandleFetcher()
        tracker = BTCCorrelationTracker(fetcher)
        corr = tracker.get_correlation("SOL")
        if corr.is_btc_driven:
            print(f"SOL move is tracking BTC ({corr.btc_change_1h:+.1f}%)")
    """

    def __init__(self, candle_fetcher: CandleFetcher):
        """Initialize tracker with candle fetcher.

        Args:
            candle_fetcher: CandleFetcher instance for getting price data
        """
        self.candle_fetcher = candle_fetcher

    def get_correlation(self, coin: str, timeframe: str = "1h") -> BTCCorrelation:
        """Get BTC correlation data for a coin.

        Args:
            coin: Coin symbol (e.g., "SOL", "ETH")
            timeframe: Timeframe for analysis (default "1h")

        Returns:
            BTCCorrelation with correlation data
        """
        # Get BTC and coin candles
        btc_data = self.candle_fetcher.get_candles("BTC", timeframe, limit=25)
        coin_data = self.candle_fetcher.get_candles(coin, timeframe, limit=25)

        btc_closes = btc_data.closes()
        coin_closes = coin_data.closes()

        # Calculate 1h changes
        btc_change_1h = self._calculate_change(btc_closes, 1)
        coin_change_1h = self._calculate_change(coin_closes, 1)

        # Calculate 24h correlation
        correlation_24h = self._calculate_correlation(btc_closes, coin_closes)

        # Determine if move is BTC-driven
        is_btc_driven = self._is_btc_driven_move(
            btc_change_1h, coin_change_1h, correlation_24h
        )

        return BTCCorrelation(
            coin=coin,
            btc_change_1h=btc_change_1h,
            coin_change_1h=coin_change_1h,
            correlation_24h=correlation_24h,
            is_btc_driven=is_btc_driven,
            timestamp=datetime.now()
        )

    def is_btc_driven_move(
        self,
        coin: str,
        btc_threshold: float = 1.0,
        correlation_threshold: float = 0.5
    ) -> tuple[bool, str]:
        """Check if a coin's current move is BTC-driven.

        Args:
            coin: Coin symbol
            btc_threshold: Minimum BTC move % to consider (default 1%)
            correlation_threshold: Minimum correlation to consider (default 0.5)

        Returns:
            Tuple of (is_btc_driven, reason)
        """
        corr = self.get_correlation(coin)

        if abs(corr.btc_change_1h) < btc_threshold:
            return False, "BTC move too small"

        if corr.correlation_24h < correlation_threshold:
            return False, f"Low correlation ({corr.correlation_24h:.2f})"

        # Check same direction
        same_direction = (corr.btc_change_1h > 0) == (corr.coin_change_1h > 0)
        if not same_direction:
            return False, "Opposite direction"

        return True, f"BTC {corr.btc_change_1h:+.1f}%, correlation {corr.correlation_24h:.2f}"

    def get_all_correlations(self, coins: List[str]) -> dict[str, BTCCorrelation]:
        """Get correlations for multiple coins.

        Args:
            coins: List of coin symbols

        Returns:
            Dict mapping coin to BTCCorrelation
        """
        results = {}
        for coin in coins:
            if coin.upper() != "BTC":
                try:
                    results[coin] = self.get_correlation(coin)
                except Exception as e:
                    logger.warning(f"Failed to get correlation for {coin}: {e}")
        return results

    def _calculate_change(self, closes: List[float], periods: int) -> float:
        """Calculate percentage change over N periods."""
        if len(closes) < periods + 1:
            return 0.0

        old_price = closes[-(periods + 1)]
        new_price = closes[-1]

        if old_price == 0:
            return 0.0

        return ((new_price - old_price) / old_price) * 100

    def _calculate_correlation(
        self,
        btc_closes: List[float],
        coin_closes: List[float]
    ) -> float:
        """Calculate Pearson correlation coefficient.

        Uses price returns (% changes) rather than absolute prices.
        """
        # Need at least 3 data points for meaningful correlation
        min_len = min(len(btc_closes), len(coin_closes))
        if min_len < 3:
            return 0.0

        # Use the same length for both
        btc_closes = btc_closes[-min_len:]
        coin_closes = coin_closes[-min_len:]

        # Calculate returns (% changes)
        btc_returns = []
        coin_returns = []

        for i in range(1, len(btc_closes)):
            if btc_closes[i - 1] != 0 and coin_closes[i - 1] != 0:
                btc_returns.append(
                    (btc_closes[i] - btc_closes[i - 1]) / btc_closes[i - 1]
                )
                coin_returns.append(
                    (coin_closes[i] - coin_closes[i - 1]) / coin_closes[i - 1]
                )

        if len(btc_returns) < 2:
            return 0.0

        # Calculate Pearson correlation
        try:
            return self._pearson_correlation(btc_returns, coin_returns)
        except Exception:
            return 0.0

    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient between two lists."""
        n = len(x)
        if n < 2:
            return 0.0

        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)

        # Calculate covariance and standard deviations
        covariance = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n

        std_x = statistics.pstdev(x)
        std_y = statistics.pstdev(y)

        if std_x == 0 or std_y == 0:
            return 0.0

        return covariance / (std_x * std_y)

    def _is_btc_driven_move(
        self,
        btc_change: float,
        coin_change: float,
        correlation: float
    ) -> bool:
        """Determine if a move is BTC-driven.

        A move is BTC-driven if:
        1. BTC moved significantly (>1%)
        2. Coin moved in same direction
        3. Historical correlation is >0.5
        """
        # BTC must have moved significantly
        if abs(btc_change) < 1.0:
            return False

        # Must be same direction
        if (btc_change > 0) != (coin_change > 0):
            return False

        # Must have meaningful correlation
        return correlation > 0.5
