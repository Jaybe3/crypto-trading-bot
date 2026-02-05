"""Candle data fetcher for technical indicator calculations."""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import requests

from config.settings import SYMBOL_MAP

logger = logging.getLogger(__name__)


@dataclass
class Candle:
    """Single OHLCV candle."""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float = 0.0

    @property
    def is_bullish(self) -> bool:
        """True if close > open (green candle)."""
        return self.close > self.open

    @property
    def body_size(self) -> float:
        """Absolute size of candle body."""
        return abs(self.close - self.open)

    @property
    def wick_ratio(self) -> float:
        """Ratio of wicks to total candle range."""
        body = self.body_size
        total = self.high - self.low
        if total == 0:
            return 0
        return (total - body) / total


@dataclass
class CandleData:
    """Collection of candles for a coin/interval."""
    coin: str
    interval: str
    candles: List[Candle] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

    def closes(self) -> List[float]:
        """Get list of close prices."""
        return [c.close for c in self.candles]

    def volumes(self) -> List[float]:
        """Get list of volumes."""
        return [c.volume for c in self.candles]

    def highs(self) -> List[float]:
        """Get list of high prices."""
        return [c.high for c in self.candles]

    def lows(self) -> List[float]:
        """Get list of low prices."""
        return [c.low for c in self.candles]


class CandleFetcher:
    """Fetches OHLCV candle data from Bybit.

    Provides the foundation for all technical indicators:
    - RSI needs close prices
    - ATR needs high/low/close
    - VWAP needs OHLCV
    - Support/Resistance needs historical OHLC

    Usage:
        fetcher = CandleFetcher()
        data = fetcher.get_candles("BTC", "1h", limit=100)
        closes = data.closes()  # For RSI
    """

    API_URL = "https://api.bybit.com/v5/market/kline"

    # Interval mapping (our format -> Bybit format)
    INTERVALS = {
        "1m": "1",
        "3m": "3",
        "5m": "5",
        "15m": "15",
        "30m": "30",
        "1h": "60",
        "2h": "120",
        "4h": "240",
        "6h": "360",
        "12h": "720",
        "1d": "D",
        "1w": "W",
    }

    # Symbol mapping (imported from config.settings)

    def __init__(self, cache_seconds: int = 60):
        """Initialize fetcher with cache duration.

        Args:
            cache_seconds: How long to cache candle data (default 60s)
        """
        self.cache_duration = timedelta(seconds=cache_seconds)
        self._cache: Dict[str, CandleData] = {}

    def get_candles(
        self,
        coin: str,
        interval: str = "1h",
        limit: int = 200
    ) -> CandleData:
        """Get candles for a coin.

        Args:
            coin: Coin symbol (e.g., "BTC", "ETH", "SOL")
            interval: Candle interval (e.g., "1m", "15m", "1h", "4h", "1d")
            limit: Number of candles (max 200)

        Returns:
            CandleData with list of candles in chronological order (oldest first)
        """
        cache_key = f"{coin}_{interval}"

        # Check cache
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if datetime.now() - cached.last_updated < self.cache_duration:
                return cached

        # Fetch from API
        try:
            symbol = self._get_symbol(coin)
            bybit_interval = self.INTERVALS.get(interval)

            if not bybit_interval:
                logger.error(f"Invalid interval: {interval}. Valid: {list(self.INTERVALS.keys())}")
                return self._get_cached_or_empty(coin, interval)

            params = {
                "category": "linear",  # Perpetual futures for more liquidity
                "symbol": symbol,
                "interval": bybit_interval,
                "limit": min(limit, 200)
            }

            response = requests.get(self.API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("retCode") != 0:
                logger.error(f"Bybit API error: {data.get('retMsg')}")
                return self._get_cached_or_empty(coin, interval)

            candles = []
            for item in data.get("result", {}).get("list", []):
                # Bybit returns: [timestamp, open, high, low, close, volume, turnover]
                candles.append(Candle(
                    timestamp=int(item[0]),
                    open=float(item[1]),
                    high=float(item[2]),
                    low=float(item[3]),
                    close=float(item[4]),
                    volume=float(item[5]),
                    turnover=float(item[6]) if len(item) > 6 else 0.0
                ))

            # Bybit returns newest first, reverse to chronological order
            candles.reverse()

            result = CandleData(
                coin=coin,
                interval=interval,
                candles=candles,
                last_updated=datetime.now()
            )

            self._cache[cache_key] = result
            logger.debug(f"Fetched {len(candles)} {interval} candles for {coin}")
            return result

        except requests.RequestException as e:
            logger.error(f"Failed to fetch candles for {coin}: {e}")
            return self._get_cached_or_empty(coin, interval)
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse candle response for {coin}: {e}")
            return self._get_cached_or_empty(coin, interval)

    def get_latest_candle(self, coin: str, interval: str = "1h") -> Optional[Candle]:
        """Get most recent closed candle."""
        data = self.get_candles(coin, interval, limit=2)
        if data.candles:
            return data.candles[-1]
        return None

    def _get_symbol(self, coin: str) -> str:
        """Convert coin symbol to Bybit trading pair."""
        coin_upper = coin.upper()
        if coin_upper in SYMBOL_MAP:
            return SYMBOL_MAP[coin_upper]
        return f"{coin_upper}USDT"

    def _get_cached_or_empty(self, coin: str, interval: str) -> CandleData:
        """Return cached data or empty result on error."""
        cache_key = f"{coin}_{interval}"
        if cache_key in self._cache:
            logger.info(f"Using cached candles for {coin} {interval}")
            return self._cache[cache_key]
        return CandleData(coin=coin, interval=interval)
