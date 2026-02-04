"""Order Book analysis for bid/ask imbalance and wall detection."""
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

import requests

logger = logging.getLogger(__name__)


@dataclass
class PriceWall:
    """A significant order at a price level."""
    price: float
    size: float
    side: str                       # "bid" or "ask"
    distance_pct: float             # Distance from current price

    @property
    def is_bid_wall(self) -> bool:
        """Wall is on bid side (support)."""
        return self.side == "bid"

    @property
    def is_ask_wall(self) -> bool:
        """Wall is on ask side (resistance)."""
        return self.side == "ask"


@dataclass
class OrderBookDepth:
    """Order book analysis result."""
    coin: str
    bid_volume: float               # Total bid volume
    ask_volume: float               # Total ask volume
    imbalance: float                # (bid - ask) / (bid + ask), -1 to +1
    bid_walls: List[PriceWall]      # Large bid orders
    ask_walls: List[PriceWall]      # Large ask orders
    spread_pct: float               # Bid-ask spread as percentage
    best_bid: float
    best_ask: float
    mid_price: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def bias(self) -> str:
        """Market bias based on order book imbalance."""
        if self.imbalance > 0.2:
            return "strong_bid"
        if self.imbalance < -0.2:
            return "strong_ask"
        return "balanced"

    @property
    def is_bullish(self) -> bool:
        """Order book shows bullish pressure."""
        return self.imbalance > 0.1

    @property
    def is_bearish(self) -> bool:
        """Order book shows bearish pressure."""
        return self.imbalance < -0.1

    @property
    def has_bid_walls(self) -> bool:
        """Significant bid walls detected."""
        return len(self.bid_walls) > 0

    @property
    def has_ask_walls(self) -> bool:
        """Significant ask walls detected."""
        return len(self.ask_walls) > 0

    @property
    def nearest_bid_wall(self) -> Optional[PriceWall]:
        """Nearest bid wall to mid price."""
        if not self.bid_walls:
            return None
        return min(self.bid_walls, key=lambda w: w.distance_pct)

    @property
    def nearest_ask_wall(self) -> Optional[PriceWall]:
        """Nearest ask wall to mid price."""
        if not self.ask_walls:
            return None
        return min(self.ask_walls, key=lambda w: w.distance_pct)


class OrderBookAnalyzer:
    """Analyzes order book depth for trading signals.

    Order book analysis reveals:
    - Imbalance: More bids vs asks indicates buying pressure
    - Walls: Large orders that may act as support/resistance
    - Spread: Liquidity indicator

    Usage:
        analyzer = OrderBookAnalyzer()
        depth = analyzer.analyze("BTC")
        print(f"Bias: {depth.bias}")
        print(f"Imbalance: {depth.imbalance:+.2f}")
    """

    BASE_URL = "https://api.bybit.com/v5/market/orderbook"
    CACHE_TTL = 5  # 5 seconds (order book changes fast)

    def __init__(self, wall_multiplier: float = 3.0):
        """Initialize order book analyzer.

        Args:
            wall_multiplier: Multiplier for detecting walls (default 3x average)
        """
        self.wall_multiplier = wall_multiplier
        self._cache: Dict[str, tuple[OrderBookDepth, float]] = {}

    def analyze(
        self,
        coin: str,
        depth: int = 50,
        use_cache: bool = True
    ) -> OrderBookDepth:
        """Analyze order book for a coin.

        Args:
            coin: Coin symbol (e.g., "BTC", "ETH")
            depth: Number of levels to fetch (max 200)
            use_cache: Whether to use cached data

        Returns:
            OrderBookDepth with analysis
        """
        coin_upper = coin.upper()
        symbol = f"{coin_upper}USDT"

        # Check cache
        if use_cache and symbol in self._cache:
            cached_depth, cache_time = self._cache[symbol]
            if (time.time() - cache_time) < self.CACHE_TTL:
                return cached_depth

        try:
            response = requests.get(
                self.BASE_URL,
                params={
                    "category": "linear",
                    "symbol": symbol,
                    "limit": min(depth, 200)
                },
                timeout=5
            )
            response.raise_for_status()

            data = response.json()
            result = self._parse_response(coin_upper, data)

            # Update cache
            self._cache[symbol] = (result, time.time())

            return result

        except requests.RequestException as e:
            logger.warning(f"Failed to fetch order book for {coin}: {e}")
            # Return cached data if available
            if symbol in self._cache:
                return self._cache[symbol][0]
            return self._empty_depth(coin_upper)

    def calculate_imbalance(self, bid_volume: float, ask_volume: float) -> float:
        """Calculate order book imbalance.

        Args:
            bid_volume: Total bid volume
            ask_volume: Total ask volume

        Returns:
            Imbalance from -1 (all asks) to +1 (all bids)
        """
        total = bid_volume + ask_volume
        if total == 0:
            return 0.0
        return (bid_volume - ask_volume) / total

    def detect_walls(
        self,
        orders: List[tuple[float, float]],
        side: str,
        mid_price: float
    ) -> List[PriceWall]:
        """Detect large orders (walls) in order book.

        Args:
            orders: List of (price, size) tuples
            side: "bid" or "ask"
            mid_price: Current mid price for distance calculation

        Returns:
            List of PriceWall objects
        """
        if not orders:
            return []

        # Calculate average order size
        sizes = [size for _, size in orders]
        avg_size = sum(sizes) / len(sizes) if sizes else 0
        threshold = avg_size * self.wall_multiplier

        walls = []
        for price, size in orders:
            if size > threshold:
                distance_pct = abs((price - mid_price) / mid_price * 100) if mid_price else 0
                walls.append(PriceWall(
                    price=price,
                    size=size,
                    side=side,
                    distance_pct=distance_pct
                ))

        return walls

    def get_spread(self, best_bid: float, best_ask: float) -> float:
        """Calculate spread as percentage.

        Args:
            best_bid: Best bid price
            best_ask: Best ask price

        Returns:
            Spread as percentage of mid price
        """
        if best_bid == 0 or best_ask == 0:
            return 0.0
        mid_price = (best_bid + best_ask) / 2
        return ((best_ask - best_bid) / mid_price) * 100

    def _parse_response(self, coin: str, data: Dict[str, Any]) -> OrderBookDepth:
        """Parse Bybit API response into OrderBookDepth."""
        result = data.get("result", {})

        # Parse bids and asks
        bids_raw = result.get("b", [])
        asks_raw = result.get("a", [])

        # Convert to (price, size) tuples
        bids = [(float(b[0]), float(b[1])) for b in bids_raw]
        asks = [(float(a[0]), float(a[1])) for a in asks_raw]

        # Calculate volumes
        bid_volume = sum(size for _, size in bids)
        ask_volume = sum(size for _, size in asks)

        # Get best prices
        best_bid = bids[0][0] if bids else 0.0
        best_ask = asks[0][0] if asks else 0.0
        mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else 0.0

        # Calculate metrics
        imbalance = self.calculate_imbalance(bid_volume, ask_volume)
        spread_pct = self.get_spread(best_bid, best_ask)

        # Detect walls
        bid_walls = self.detect_walls(bids, "bid", mid_price)
        ask_walls = self.detect_walls(asks, "ask", mid_price)

        return OrderBookDepth(
            coin=coin,
            bid_volume=bid_volume,
            ask_volume=ask_volume,
            imbalance=imbalance,
            bid_walls=bid_walls,
            ask_walls=ask_walls,
            spread_pct=spread_pct,
            best_bid=best_bid,
            best_ask=best_ask,
            mid_price=mid_price,
            timestamp=datetime.now(timezone.utc)
        )

    def _empty_depth(self, coin: str) -> OrderBookDepth:
        """Return empty depth when API fails."""
        return OrderBookDepth(
            coin=coin,
            bid_volume=0.0,
            ask_volume=0.0,
            imbalance=0.0,
            bid_walls=[],
            ask_walls=[],
            spread_pct=0.0,
            best_bid=0.0,
            best_ask=0.0,
            mid_price=0.0,
            timestamp=datetime.now(timezone.utc)
        )
