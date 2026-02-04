"""Funding Rate fetcher for perpetual futures market positioning."""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import requests

logger = logging.getLogger(__name__)


@dataclass
class FundingData:
    """Funding rate data for a coin."""
    coin: str
    current_rate: float       # Current funding rate (per 8h)
    predicted_rate: float     # Next predicted rate
    annualized: float         # Annualized rate percentage
    timestamp: datetime

    @property
    def is_extreme_long(self) -> bool:
        """Market is crowded long (expensive to hold longs)."""
        return self.current_rate > 0.0005  # >0.05% per 8h

    @property
    def is_extreme_short(self) -> bool:
        """Market is crowded short (expensive to hold shorts)."""
        return self.current_rate < -0.0005  # <-0.05% per 8h

    @property
    def bias(self) -> str:
        """Market positioning bias."""
        if self.is_extreme_long:
            return "crowded_long"
        if self.is_extreme_short:
            return "crowded_short"
        if self.current_rate > 0.0001:
            return "slight_long"
        if self.current_rate < -0.0001:
            return "slight_short"
        return "neutral"

    @property
    def contrarian_signal(self) -> Optional[str]:
        """Contrarian trading signal based on extreme funding."""
        if self.is_extreme_long:
            return "SHORT"  # Crowded longs often get squeezed
        if self.is_extreme_short:
            return "LONG"   # Crowded shorts often get squeezed
        return None


class FundingRateFetcher:
    """Fetches funding rates from Bybit for perpetual futures.

    Funding rates indicate market positioning:
    - Positive rate: Longs pay shorts (market bullish, crowded long)
    - Negative rate: Shorts pay longs (market bearish, crowded short)
    - Extreme rates often precede reversals

    Usage:
        funding = FundingRateFetcher()
        data = funding.get_current("BTC")
        print(f"BTC Funding: {data.current_rate*100:.4f}% ({data.bias})")
        if data.contrarian_signal:
            print(f"Contrarian signal: {data.contrarian_signal}")
    """

    API_URL = "https://api.bybit.com/v5/market/funding/history"
    TICKERS_URL = "https://api.bybit.com/v5/market/tickers"

    # Symbol mapping
    SYMBOL_MAP = {
        "BTC": "BTCUSDT",
        "ETH": "ETHUSDT",
        "SOL": "SOLUSDT",
        "XRP": "XRPUSDT",
        "BNB": "BNBUSDT",
        "ADA": "ADAUSDT",
        "DOGE": "DOGEUSDT",
        "AVAX": "AVAXUSDT",
        "DOT": "DOTUSDT",
        "LINK": "LINKUSDT",
        "MATIC": "MATICUSDT",
        "UNI": "UNIUSDT",
        "ATOM": "ATOMUSDT",
        "LTC": "LTCUSDT",
        "ETC": "ETCUSDT",
        "PEPE": "PEPEUSDT",
        "FLOKI": "FLOKIUSDT",
        "BONK": "BONKUSDT",
        "WIF": "WIFUSDT",
        "SHIB": "SHIBUSDT",
    }

    def __init__(self, cache_seconds: int = 300):
        """Initialize funding rate fetcher.

        Args:
            cache_seconds: Cache duration (default 5 minutes)
        """
        self.cache_duration = timedelta(seconds=cache_seconds)
        self._cache: Dict[str, tuple[FundingData, datetime]] = {}

    def get_current(self, coin: str) -> FundingData:
        """Get current funding rate for a coin.

        Args:
            coin: Coin symbol (e.g., "BTC", "ETH")

        Returns:
            FundingData with current and predicted rates
        """
        # Check cache
        if coin in self._cache:
            data, cache_time = self._cache[coin]
            if datetime.now() - cache_time < self.cache_duration:
                return data

        try:
            symbol = self._get_symbol(coin)

            # Get current funding rate from tickers
            ticker_data = self._fetch_ticker(symbol)

            # Get historical rates for context
            history = self._fetch_history(symbol, limit=1)

            current_rate = ticker_data.get("fundingRate", 0)
            if isinstance(current_rate, str):
                current_rate = float(current_rate)

            # Predicted rate (next funding)
            predicted_rate = current_rate  # Default to current if not available

            # Calculate annualized rate
            # Funding is paid 3x per day (every 8 hours)
            annualized = current_rate * 3 * 365 * 100  # As percentage

            result = FundingData(
                coin=coin,
                current_rate=current_rate,
                predicted_rate=predicted_rate,
                annualized=annualized,
                timestamp=datetime.now()
            )

            self._cache[coin] = (result, datetime.now())
            logger.debug(f"{coin} funding: {current_rate*100:.4f}% ({result.bias})")

            return result

        except Exception as e:
            logger.error(f"Failed to fetch funding for {coin}: {e}")
            # Return cached if available
            if coin in self._cache:
                return self._cache[coin][0]
            # Return neutral default
            return FundingData(
                coin=coin,
                current_rate=0.0,
                predicted_rate=0.0,
                annualized=0.0,
                timestamp=datetime.now()
            )

    def get_historical(self, coin: str, limit: int = 10) -> List[dict]:
        """Get historical funding rates.

        Args:
            coin: Coin symbol
            limit: Number of historical rates to fetch

        Returns:
            List of funding rate records
        """
        try:
            symbol = self._get_symbol(coin)
            return self._fetch_history(symbol, limit)
        except Exception as e:
            logger.error(f"Failed to fetch funding history for {coin}: {e}")
            return []

    def get_all_extreme(self) -> Dict[str, FundingData]:
        """Get all coins with extreme funding rates.

        Returns:
            Dict mapping coin to FundingData for coins with extreme rates
        """
        extreme = {}
        for coin in self.SYMBOL_MAP.keys():
            try:
                data = self.get_current(coin)
                if data.is_extreme_long or data.is_extreme_short:
                    extreme[coin] = data
            except Exception:
                continue
        return extreme

    def should_avoid_direction(self, coin: str, direction: str) -> tuple[bool, str]:
        """Check if funding suggests avoiding a direction.

        Args:
            coin: Coin symbol
            direction: "LONG" or "SHORT"

        Returns:
            Tuple of (should_avoid, reason)
        """
        data = self.get_current(coin)

        if direction.upper() == "LONG" and data.is_extreme_long:
            return True, f"Crowded longs (funding {data.current_rate*100:.3f}%)"

        if direction.upper() == "SHORT" and data.is_extreme_short:
            return True, f"Crowded shorts (funding {data.current_rate*100:.3f}%)"

        return False, ""

    def _get_symbol(self, coin: str) -> str:
        """Convert coin symbol to Bybit trading pair."""
        coin_upper = coin.upper()
        if coin_upper in self.SYMBOL_MAP:
            return self.SYMBOL_MAP[coin_upper]
        return f"{coin_upper}USDT"

    def _fetch_ticker(self, symbol: str) -> dict:
        """Fetch ticker data including funding rate."""
        params = {
            "category": "linear",
            "symbol": symbol
        }

        response = requests.get(self.TICKERS_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("retCode") != 0:
            raise ValueError(f"API error: {data.get('retMsg')}")

        tickers = data.get("result", {}).get("list", [])
        if not tickers:
            raise ValueError(f"No ticker data for {symbol}")

        return tickers[0]

    def _fetch_history(self, symbol: str, limit: int = 10) -> List[dict]:
        """Fetch historical funding rates."""
        params = {
            "category": "linear",
            "symbol": symbol,
            "limit": limit
        }

        response = requests.get(self.API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("retCode") != 0:
            raise ValueError(f"API error: {data.get('retMsg')}")

        return data.get("result", {}).get("list", [])
