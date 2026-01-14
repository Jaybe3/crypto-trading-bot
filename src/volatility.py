"""Volatility calculation and risk adjustment.

Calculates rolling volatility metrics and provides dynamic position
sizing and stop-loss recommendations based on market conditions.

Features:
- Rolling 24h volatility from price history
- Volatility score (0-100) for easy comparison
- Position size multipliers based on volatility
- Dynamic stop-loss using ATR-like calculation
- 5-minute caching to reduce computation
- Automatic cleanup of old data (>7 days)
"""

import math
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from src.database import Database
from src.coin_config import get_tier, get_tier_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Volatility multiplier thresholds (score -> multiplier)
VOLATILITY_MULTIPLIERS = [
    (20, 1.2),   # Very low volatility: +20% position
    (40, 1.0),   # Low volatility: no change
    (60, 0.9),   # Normal volatility: -10% position
    (80, 0.7),   # High volatility: -30% position
    (100, 0.5),  # Extreme volatility: -50% position
]

# ATR multipliers by tier (for stop-loss calculation)
ATR_MULTIPLIERS = {
    1: 1.5,  # Blue chips: tighter stops
    2: 2.0,  # Established: moderate
    3: 2.5,  # High volatility tier: wider stops
}

# Stop-loss bounds
MIN_STOP_LOSS_PCT = 0.02  # 2% minimum
MAX_STOP_LOSS_PCT = 0.15  # 15% maximum

# Cache settings
CACHE_DURATION_SECONDS = 300  # 5 minutes


class VolatilityCalculator:
    """Calculates volatility metrics for risk adjustment.

    Maintains price history, calculates rolling volatility,
    and provides position size and stop-loss recommendations.
    """

    def __init__(self, db: Database = None):
        """Initialize with database connection.

        Args:
            db: Database instance. Creates new one if not provided.
        """
        self.db = db or Database()
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._ensure_tables()
        logger.info("VolatilityCalculator initialized")

    def _ensure_tables(self):
        """Create price_history table if not exists."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coin TEXT NOT NULL,
                    price_usd REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_price_history_coin_time
                ON price_history(coin, timestamp DESC)
            """)
            conn.commit()

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.now() - timestamp < timedelta(seconds=CACHE_DURATION_SECONDS):
                return value
        return None

    def _set_cached(self, key: str, value: Any):
        """Set cached value with current timestamp."""
        self._cache[key] = (value, datetime.now())

    def record_price(self, coin: str, price: float) -> None:
        """Record a price snapshot for volatility calculation.

        Args:
            coin: Coin ID.
            price: Current price in USD.
        """
        if price <= 0:
            return

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO price_history (coin, price_usd)
                VALUES (?, ?)
            """, (coin, price))
            conn.commit()

    def record_all_prices(self, prices: Dict[str, float]) -> int:
        """Record prices for all coins in one transaction.

        Args:
            prices: Dict mapping coin ID to price.

        Returns:
            Number of prices recorded.
        """
        count = 0
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            for coin, price in prices.items():
                if price and price > 0:
                    cursor.execute("""
                        INSERT INTO price_history (coin, price_usd)
                        VALUES (?, ?)
                    """, (coin, price))
                    count += 1
            conn.commit()

        logger.debug(f"Recorded {count} price snapshots")
        return count

    def get_price_history(
        self, coin: str, hours: int = 24
    ) -> List[Tuple[float, str]]:
        """Get price history for a coin.

        Args:
            coin: Coin ID.
            hours: How many hours of history to retrieve.

        Returns:
            List of (price, timestamp) tuples, oldest first.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT price_usd, timestamp
                FROM price_history
                WHERE coin = ?
                AND timestamp > datetime('now', ?)
                ORDER BY timestamp ASC
            """, (coin, f'-{hours} hours'))
            return [(row[0], row[1]) for row in cursor.fetchall()]

    def get_history_count(self, coin: str) -> int:
        """Get number of price history records for a coin."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM price_history WHERE coin = ?",
                (coin,)
            )
            return cursor.fetchone()[0]

    def calculate_volatility(self, coin: str, hours: int = 24) -> float:
        """Calculate volatility as standard deviation of returns.

        Args:
            coin: Coin ID.
            hours: Hours of history to use.

        Returns:
            Volatility as a decimal (e.g., 0.05 = 5%).
            Returns tier default if insufficient data.
        """
        # Check cache first
        cache_key = f"vol_{coin}_{hours}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        history = self.get_price_history(coin, hours)

        if len(history) < 3:
            # Not enough data - return tier default
            config = get_tier_config(coin)
            return config.stop_loss_pct

        # Calculate returns
        prices = [h[0] for h in history]
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)

        if len(returns) < 2:
            config = get_tier_config(coin)
            return config.stop_loss_pct

        # Standard deviation of returns
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)

        # Cache and return
        self._set_cached(cache_key, std_dev)
        return std_dev

    def calculate_volatility_score(self, coin: str) -> int:
        """Calculate normalized volatility score (0-100).

        Combines historical volatility with 24h price change
        for a more responsive score.

        Score interpretation:
        - 0-30: Low volatility (calm market)
        - 30-70: Normal volatility
        - 70-100: High volatility (turbulent market)

        Args:
            coin: Coin ID.

        Returns:
            Volatility score from 0 to 100.
        """
        # Check cache
        cache_key = f"vol_score_{coin}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        vol = self.calculate_volatility(coin, hours=24)

        # Get 24h change as additional signal
        change_24h = 0
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT change_24h FROM market_data WHERE coin = ?",
                (coin,)
            )
            row = cursor.fetchone()
            if row and row[0]:
                change_24h = abs(row[0])

        # Combine volatility and 24h change
        # Scale volatility (0.01 = 1% std dev -> ~10 points)
        base_score = min(100, vol * 1000)

        # 24h change contribution (10% change = 50 points)
        change_score = min(50, change_24h * 5)

        # Weighted combination
        combined = int((base_score * 0.6) + (change_score * 0.4))
        score = min(100, max(0, combined))

        # Cache and return
        self._set_cached(cache_key, score)
        return score

    def get_volatility_multiplier(self, vol_score: int) -> float:
        """Get position size multiplier based on volatility score.

        Args:
            vol_score: Volatility score (0-100).

        Returns:
            Multiplier for position size (0.5 to 1.2).
        """
        for threshold, multiplier in VOLATILITY_MULTIPLIERS:
            if vol_score <= threshold:
                return multiplier
        return 0.5  # Most conservative for extreme volatility

    def calculate_dynamic_stop_loss(
        self, coin: str, entry_price: float
    ) -> Tuple[float, float]:
        """Calculate dynamic stop-loss based on volatility.

        Uses volatility as a proxy for ATR, scaled by tier multiplier.

        Args:
            coin: Coin ID.
            entry_price: Entry price in USD.

        Returns:
            Tuple of (stop_loss_price, stop_loss_percentage).
        """
        tier = get_tier(coin)
        tier_config = get_tier_config(coin)
        atr_mult = ATR_MULTIPLIERS.get(tier, 2.0)

        # Calculate volatility-based stop distance
        vol = self.calculate_volatility(coin, hours=24)
        stop_distance = vol * atr_mult

        # Apply bounds
        stop_pct = max(MIN_STOP_LOSS_PCT, min(MAX_STOP_LOSS_PCT, stop_distance))

        # Ensure at least half the tier default (safety floor)
        stop_pct = max(stop_pct, tier_config.stop_loss_pct * 0.5)

        stop_price = entry_price * (1 - stop_pct)
        return stop_price, stop_pct

    def get_adjusted_position_size(
        self, coin: str, base_position: float
    ) -> Tuple[float, Dict[str, Any]]:
        """Get volatility-adjusted position size.

        Args:
            coin: Coin ID.
            base_position: Base position size from tier config.

        Returns:
            Tuple of (adjusted_size, adjustment_info_dict).
        """
        vol_score = self.calculate_volatility_score(coin)
        multiplier = self.get_volatility_multiplier(vol_score)
        adjusted = base_position * multiplier

        return adjusted, {
            'volatility_score': vol_score,
            'multiplier': multiplier,
            'base_position': base_position,
            'adjusted_position': adjusted,
            'reduction_pct': (1 - multiplier) * 100
        }

    def cleanup_old_history(self, days: int = 7) -> int:
        """Remove price history older than specified days.

        Should be called periodically to prevent database bloat.

        Args:
            days: Remove records older than this many days.

        Returns:
            Number of records deleted.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM price_history
                WHERE timestamp < datetime('now', ?)
            """, (f'-{days} days',))
            deleted = cursor.rowcount
            conn.commit()

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old price history records")

        return deleted

    def get_volatility_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get volatility summary for all tracked coins.

        Returns:
            Dict mapping coin ID to volatility info.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT coin FROM market_data")
            coins = [row[0] for row in cursor.fetchall()]

        summary = {}
        for coin in coins:
            vol_score = self.calculate_volatility_score(coin)
            multiplier = self.get_volatility_multiplier(vol_score)
            history_count = self.get_history_count(coin)

            summary[coin] = {
                'volatility_score': vol_score,
                'multiplier': multiplier,
                'tier': get_tier(coin),
                'history_records': history_count,
                'has_enough_data': history_count >= 3
            }

        return summary

    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about price history storage.

        Returns:
            Dict with storage statistics.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # Total records
            cursor.execute("SELECT COUNT(*) FROM price_history")
            total_records = cursor.fetchone()[0]

            # Unique coins
            cursor.execute("SELECT COUNT(DISTINCT coin) FROM price_history")
            unique_coins = cursor.fetchone()[0]

            # Oldest record
            cursor.execute("SELECT MIN(timestamp) FROM price_history")
            oldest = cursor.fetchone()[0]

            # Records per coin (average)
            avg_per_coin = total_records / unique_coins if unique_coins > 0 else 0

        return {
            'total_records': total_records,
            'unique_coins': unique_coins,
            'avg_records_per_coin': avg_per_coin,
            'oldest_record': oldest,
            'estimated_size_kb': total_records * 50 / 1024  # ~50 bytes per record
        }


# Convenience functions for external use
def get_volatility_score(coin: str, db: Database = None) -> int:
    """Get volatility score for a coin."""
    vc = VolatilityCalculator(db=db)
    return vc.calculate_volatility_score(coin)


def get_position_multiplier(coin: str, db: Database = None) -> float:
    """Get position size multiplier for a coin."""
    vc = VolatilityCalculator(db=db)
    score = vc.calculate_volatility_score(coin)
    return vc.get_volatility_multiplier(score)


# Test when run directly
if __name__ == "__main__":
    print("=" * 60)
    print("Volatility Calculator Test")
    print("=" * 60)

    vc = VolatilityCalculator()

    # Show database stats
    stats = vc.get_database_stats()
    print(f"\nPrice History Stats:")
    print(f"  Total records: {stats['total_records']}")
    print(f"  Unique coins: {stats['unique_coins']}")
    print(f"  Estimated size: {stats['estimated_size_kb']:.1f} KB")

    # Show volatility for sample coins
    print(f"\nVolatility Scores (cached for 5 min):")
    for coin in ['bitcoin', 'ethereum', 'pepe']:
        score = vc.calculate_volatility_score(coin)
        mult = vc.get_volatility_multiplier(score)
        tier = get_tier(coin)
        print(f"  {coin}: Score={score}, Multiplier={mult}x, Tier={tier}")

    # Cleanup old data
    deleted = vc.cleanup_old_history(days=7)
    print(f"\nCleaned up {deleted} old records")
