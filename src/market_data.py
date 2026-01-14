"""Fetches real market data from CoinGecko API.

This module fetches REAL cryptocurrency prices from CoinGecko's public API.
All data can be independently verified by the user.
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

import requests
from requests.exceptions import RequestException, Timeout, HTTPError

from src.database import Database
from src.coin_config import get_coin_ids, get_tier, get_tier_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Default configuration
DEFAULT_COINS = ['bitcoin', 'ethereum', 'ripple']
DEFAULT_UPDATE_INTERVAL = 30  # seconds
API_TIMEOUT = 10  # seconds


def format_price(price: float) -> str:
    """Format price with appropriate decimal places based on magnitude.

    - Prices >= $1: 2 decimals (e.g., $95,437.12)
    - Prices >= $0.01: 4 decimals (e.g., $0.1234)
    - Prices >= $0.0001: 6 decimals (e.g., $0.001234)
    - Prices < $0.0001: 8 decimals (e.g., $0.00001234)

    Args:
        price: The price to format.

    Returns:
        Formatted price string with $ prefix.
    """
    if price is None:
        return "$N/A"

    abs_price = abs(price)

    if abs_price >= 1:
        return f"${price:,.2f}"
    elif abs_price >= 0.01:
        return f"${price:.4f}"
    elif abs_price >= 0.0001:
        return f"${price:.6f}"
    else:
        return f"${price:.8f}"


class MarketDataFetcher:
    """Fetches real-time cryptocurrency prices from CoinGecko API.

    This class fetches REAL market data that can be independently verified
    by comparing to CoinGecko's website or running curl commands.

    Attributes:
        base_url: CoinGecko API base URL.
        coins: List of coin IDs to fetch.
        update_interval: Seconds between updates.
        db: Database instance for storing prices.

    Example:
        >>> fetcher = MarketDataFetcher()
        >>> prices = fetcher.fetch_prices()
        >>> print(prices['bitcoin']['usd'])
        94235.50

    Verification:
        User can verify prices match by running:
        curl "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    """

    def __init__(
        self,
        coins: Optional[List[str]] = None,
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
        db: Optional[Database] = None
    ):
        """Initialize the market data fetcher.

        Args:
            coins: List of coin IDs to fetch (default: bitcoin, ethereum, ripple).
            update_interval: Seconds between updates (default: 30).
            db: Database instance (creates new one if not provided).
        """
        self.base_url = "https://api.coingecko.com/api/v3"
        self.coins = coins or DEFAULT_COINS.copy()
        self.update_interval = update_interval
        self.db = db or Database()

        logger.info(f"MarketDataFetcher initialized for coins: {self.coins}")

    def fetch_prices(self, coins: Optional[List[str]] = None) -> Dict[str, Dict[str, float]]:
        """Fetch current prices from CoinGecko API.

        This fetches REAL prices from the CoinGecko API. The response can be
        verified by running the equivalent curl command.

        Args:
            coins: Optional list of coin IDs. Uses self.coins if not provided.

        Returns:
            Dictionary mapping coin IDs to price data.
            Example: {'bitcoin': {'usd': 94235.50, 'usd_24h_change': 2.35}}

        Raises:
            RequestException: If API call fails after retries.

        Verification:
            Run this curl command to verify:
            curl "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        """
        coins_to_fetch = coins or self.coins

        if not coins_to_fetch:
            logger.warning("No coins specified to fetch")
            return {}

        # Build API URL
        coin_ids = ",".join(coins_to_fetch)
        url = f"{self.base_url}/simple/price"
        params = {
            "ids": coin_ids,
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }

        # Log the request for transparency
        full_url = f"{url}?ids={coin_ids}&vs_currencies=usd&include_24hr_change=true"
        logger.info(f"Fetching prices from: {full_url}")

        try:
            response = requests.get(url, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()

            data = response.json()

            # Log successful fetch
            logger.info(f"Successfully fetched prices for {len(data)} coins")
            for coin, price_data in data.items():
                logger.debug(f"  {coin}: ${price_data.get('usd', 'N/A')}")

            # Log to activity log
            self.db.log_activity(
                activity_type='market_data',
                description=f'Fetched prices for {len(data)} coins',
                details=str(data)
            )

            return data

        except Timeout:
            logger.error(f"Timeout fetching prices from CoinGecko (>{API_TIMEOUT}s)")
            self.db.log_activity(
                activity_type='error',
                description='CoinGecko API timeout',
                details=f'Timeout after {API_TIMEOUT} seconds'
            )
            raise

        except HTTPError as e:
            if e.response.status_code == 429:
                logger.warning("Rate limited by CoinGecko API")
                self.db.log_activity(
                    activity_type='warning',
                    description='CoinGecko rate limit hit',
                    details=str(e)
                )
            else:
                logger.error(f"HTTP error from CoinGecko: {e}")
                self.db.log_activity(
                    activity_type='error',
                    description=f'CoinGecko HTTP error: {e.response.status_code}',
                    details=str(e)
                )
            raise

        except RequestException as e:
            logger.error(f"Error fetching prices: {e}")
            self.db.log_activity(
                activity_type='error',
                description='Failed to fetch market data',
                details=str(e)
            )
            raise

    def update_database(self, price_data: Optional[Dict[str, Dict[str, float]]] = None) -> int:
        """Store fetched prices in database.

        Args:
            price_data: Price data from fetch_prices(). If None, fetches fresh data.

        Returns:
            Number of coins updated.
        """
        if price_data is None:
            price_data = self.fetch_prices()

        if not price_data:
            logger.warning("No price data to store")
            return 0

        updated_count = 0

        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            for coin, data in price_data.items():
                price_usd = data.get('usd')
                change_24h = data.get('usd_24h_change')

                if price_usd is None:
                    logger.warning(f"No USD price for {coin}, skipping")
                    continue

                # Insert or replace (upsert)
                cursor.execute("""
                    INSERT OR REPLACE INTO market_data
                    (coin, price_usd, change_24h, last_updated)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (coin, price_usd, change_24h))

                updated_count += 1
                logger.debug(f"Updated {coin}: {format_price(price_usd)} ({change_24h:+.2f}%)")

            conn.commit()

        logger.info(f"Updated {updated_count} coins in database")
        return updated_count

    def get_current_prices(self) -> Dict[str, Dict[str, Any]]:
        """Get current prices from database.

        Returns:
            Dictionary mapping coin IDs to price data from database.
            Example: {'bitcoin': {'price_usd': 94235.50, 'change_24h': 2.35, 'last_updated': '...'}}
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT coin, price_usd, change_24h, last_updated FROM market_data")

            prices = {}
            for row in cursor.fetchall():
                prices[row[0]] = {
                    'price_usd': row[1],
                    'change_24h': row[2],
                    'last_updated': row[3]
                }

            return prices

    def get_price(self, coin: str) -> Optional[float]:
        """Get current price for a specific coin from database.

        Args:
            coin: Coin ID (e.g., 'bitcoin').

        Returns:
            Current USD price, or None if not found.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT price_usd FROM market_data WHERE coin = ?",
                (coin,)
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def fetch_and_store(self) -> Dict[str, Dict[str, float]]:
        """Fetch prices from API and store in database.

        Convenience method that combines fetch_prices() and update_database().

        Returns:
            The fetched price data.
        """
        price_data = self.fetch_prices()
        self.update_database(price_data)
        return price_data

    def add_coin(self, coin: str) -> None:
        """Add a coin to the fetch list.

        Args:
            coin: Coin ID to add (e.g., 'solana').
        """
        if coin not in self.coins:
            self.coins.append(coin)
            logger.info(f"Added {coin} to fetch list")

    def remove_coin(self, coin: str) -> None:
        """Remove a coin from the fetch list.

        Args:
            coin: Coin ID to remove.
        """
        if coin in self.coins:
            self.coins.remove(coin)
            logger.info(f"Removed {coin} from fetch list")

    def run_continuous(self, max_iterations: Optional[int] = None) -> None:
        """Run continuous price updates.

        Args:
            max_iterations: Maximum number of updates (None for infinite).
        """
        logger.info(f"Starting continuous updates every {self.update_interval} seconds")
        logger.info(f"Fetching: {', '.join(self.coins)}")

        iteration = 0
        while max_iterations is None or iteration < max_iterations:
            try:
                self.fetch_and_store()
                iteration += 1

                if max_iterations:
                    logger.info(f"Update {iteration}/{max_iterations} complete")

                time.sleep(self.update_interval)

            except KeyboardInterrupt:
                logger.info("Stopped by user")
                break
            except RequestException as e:
                logger.error(f"Fetch failed: {e}, retrying in {self.update_interval}s")
                time.sleep(self.update_interval)

    # =========================================================================
    # BATCH FETCHING FOR MULTI-TIER COIN UNIVERSE
    # =========================================================================

    def fetch_all_prices_with_volume(self) -> Dict[str, Dict[str, Any]]:
        """Fetch prices AND volume for ALL coins in one API call.

        Uses the /coins/markets endpoint which provides volume data.
        This is essential for filtering out illiquid coins.

        Returns:
            Dict mapping coin_id to {price_usd, change_24h, volume_24h, tier}
        """
        coin_ids = get_coin_ids()
        ids_param = ",".join(coin_ids)

        url = f"{self.base_url}/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": ids_param,
            "order": "market_cap_desc",
            "per_page": 100,  # Max allowed
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h"
        }

        logger.info(f"Batch fetching {len(coin_ids)} coins with volume data...")

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            result = {}
            for coin_data in data:
                coin_id = coin_data.get("id")
                if coin_id:
                    result[coin_id] = {
                        "price_usd": coin_data.get("current_price", 0),
                        "change_24h": coin_data.get("price_change_percentage_24h", 0),
                        "volume_24h": coin_data.get("total_volume", 0),
                        "market_cap": coin_data.get("market_cap", 0),
                        "tier": get_tier(coin_id)
                    }

            logger.info(f"Fetched {len(result)} coins with volume data")

            # Log to activity
            self.db.log_activity(
                activity_type='market_data',
                description=f'Batch fetched {len(result)} coins with volume',
                details=f'coins={len(result)}'
            )

            return result

        except Timeout:
            logger.error("Timeout fetching batch prices")
            raise
        except HTTPError as e:
            if e.response.status_code == 429:
                logger.warning("Rate limited - falling back to simple endpoint")
                return self._fallback_simple_fetch(coin_ids)
            raise
        except RequestException as e:
            logger.error(f"Error fetching batch prices: {e}")
            raise

    def _fallback_simple_fetch(self, coin_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fallback to simple price endpoint without volume."""
        logger.info("Using fallback simple price endpoint")
        price_data = self.fetch_prices(coin_ids)

        result = {}
        for coin_id, data in price_data.items():
            result[coin_id] = {
                "price_usd": data.get("usd", 0),
                "change_24h": data.get("usd_24h_change", 0),
                "volume_24h": 0,  # Not available in simple endpoint
                "market_cap": 0,
                "tier": get_tier(coin_id)
            }
        return result

    def update_all_prices(self) -> Dict[str, Any]:
        """Update all coin prices in database with volume filtering.

        Fetches all coins, filters by volume requirements, stores in DB.

        Returns:
            Dict with stats: {updated, skipped_low_volume, failed}
        """
        prices = self.fetch_all_prices_with_volume()

        stats = {"updated": 0, "skipped_low_volume": 0, "skipped_coins": []}

        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            for coin_id, data in prices.items():
                tier_config = get_tier_config(coin_id)
                volume = data.get("volume_24h", 0)

                # Check minimum volume requirement
                if volume < tier_config.min_volume_24h:
                    stats["skipped_low_volume"] += 1
                    stats["skipped_coins"].append(coin_id)
                    logger.debug(
                        f"Skipping {coin_id}: volume ${volume:,.0f} < "
                        f"${tier_config.min_volume_24h:,.0f} required"
                    )
                    continue

                # Store in database
                cursor.execute("""
                    INSERT OR REPLACE INTO market_data
                    (coin, price_usd, change_24h, last_updated)
                    VALUES (?, ?, ?, datetime('now'))
                """, (coin_id, data["price_usd"], data["change_24h"]))

                stats["updated"] += 1

            conn.commit()

        logger.info(
            f"Updated {stats['updated']} coins, "
            f"skipped {stats['skipped_low_volume']} (low volume)"
        )

        if stats["skipped_coins"]:
            logger.info(f"Skipped coins: {', '.join(stats['skipped_coins'][:5])}...")

        return stats

    def get_tradeable_coins(self) -> List[str]:
        """Get list of coins that meet volume requirements.

        Returns:
            List of coin IDs that are tradeable (have recent price data).
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            # Get coins updated in the last 5 minutes
            cursor.execute("""
                SELECT coin FROM market_data
                WHERE last_updated > datetime('now', '-5 minutes')
                ORDER BY coin
            """)
            return [row[0] for row in cursor.fetchall()]


def get_verification_url(coins: List[str] = None) -> str:
    """Get the curl command URL for verifying prices.

    Args:
        coins: List of coins to include (default: bitcoin).

    Returns:
        Full URL that can be used with curl for verification.
    """
    coins = coins or ['bitcoin']
    coin_ids = ",".join(coins)
    return f"https://api.coingecko.com/api/v3/simple/price?ids={coin_ids}&vs_currencies=usd&include_24hr_change=true"


# Allow running directly for testing
if __name__ == "__main__":
    print("=" * 60)
    print("Market Data Fetcher - REAL DATA from CoinGecko")
    print("=" * 60)

    # Show verification URL
    print("\nVerification URL (run with curl):")
    print(f"  curl \"{get_verification_url(['bitcoin', 'ethereum', 'ripple'])}\"")
    print()

    # Fetch and display
    fetcher = MarketDataFetcher()
    print("Fetching prices from CoinGecko API...")

    try:
        prices = fetcher.fetch_and_store()

        print("\nPrices fetched and stored:")
        print("-" * 40)
        for coin, data in prices.items():
            price = data.get('usd', 0)
            change = data.get('usd_24h_change', 0)
            print(f"  {coin.upper():10} {format_price(price):>14}  ({change:+.2f}%)")

        print("-" * 40)
        print("\nDatabase contents (full precision):")
        db_prices = fetcher.get_current_prices()
        for coin, data in db_prices.items():
            print(f"  {coin}: {format_price(data['price_usd'])} (updated: {data['last_updated']})")

        print("\n✅ Prices are REAL and can be verified at:")
        print("   https://www.coingecko.com/")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("   Check your internet connection and try again.")
