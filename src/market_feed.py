"""
WebSocket Market Data Feed for Crypto Exchanges.

Provides real-time price updates via WebSocket, replacing 30-second polling.
Supports Bybit (primary) and Binance (fallback).
Designed for speed - no LLM calls, no database writes in hot path.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Literal

try:
    import websockets
    from websockets.exceptions import ConnectionClosed, WebSocketException
except ImportError:
    raise ImportError("websockets library required. Install with: pip install websockets")

logger = logging.getLogger(__name__)


@dataclass
class PriceTick:
    """Real-time price update."""
    coin: str           # "BTC", "ETH", etc.
    price: float        # Current price in USDT
    timestamp: int      # Unix timestamp in milliseconds
    volume_24h: float   # 24h volume (updated periodically)
    change_24h: float   # 24h % change (updated periodically)


@dataclass
class TradeEvent:
    """Individual trade event for order flow analysis."""
    coin: str
    price: float
    quantity: float
    is_buyer_maker: bool  # True = sell (taker sold), False = buy (taker bought)
    timestamp: int


@dataclass
class CoinConfig:
    """Configuration for a monitored coin."""
    symbol: str         # "BTC"
    binance: str        # "BTCUSDT"
    tier: int           # 1, 2, or 3
    name: str           # "Bitcoin"


@dataclass
class FeedStatus:
    """Current status of the market feed."""
    connected: bool = False
    exchange: str = ""
    last_message_time: Optional[float] = None
    reconnect_count: int = 0
    messages_received: int = 0
    errors: int = 0


class MarketFeed:
    """
    Real-time WebSocket market data feed.

    Supports:
    - Bybit (primary, works globally)
    - Binance / Binance US (fallback)

    Features:
    - Sub-second price updates
    - Auto-reconnect with exponential backoff
    - Callback system for price and trade events
    - Connection health monitoring

    Usage:
        feed = MarketFeed(['BTC', 'ETH', 'SOL'])
        feed.subscribe_price(lambda tick: print(f"{tick.coin}: ${tick.price}"))
        await feed.connect()
    """

    EXCHANGES = {
        'bybit': {
            'url': 'wss://stream.bybit.com/v5/public/spot',
            'type': 'bybit'
        },
        'bybit_linear': {
            'url': 'wss://stream.bybit.com/v5/public/linear',
            'type': 'bybit'
        },
        'binance': {
            'url': 'wss://stream.binance.com:9443/stream',
            'type': 'binance'
        },
        'binance_us': {
            'url': 'wss://stream.binance.us:9443/stream',
            'type': 'binance'
        },
    }

    def __init__(
        self,
        coins: Optional[list[str]] = None,
        exchange: str = 'bybit',
        config_path: Optional[str] = None
    ):
        """
        Initialize MarketFeed.

        Args:
            coins: List of coin symbols to monitor (e.g., ['BTC', 'ETH']).
                   If None, loads from config/coins.json.
            exchange: Exchange to use ('bybit', 'binance', 'binance_us').
            config_path: Path to coins.json config file.
        """
        self.config = self._load_config(config_path)
        self.exchange = exchange or self.config.get('exchange', 'bybit')
        self.coin_configs = self._parse_coin_configs(coins)

        # Validate exchange
        if self.exchange not in self.EXCHANGES:
            logger.warning(f"Unknown exchange '{self.exchange}', defaulting to 'bybit'")
            self.exchange = 'bybit'

        # WebSocket state
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._listen_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None

        # Callbacks
        self._price_callbacks: list[Callable[[PriceTick], None]] = []
        self._trade_callbacks: list[Callable[[TradeEvent], None]] = []
        self._status_callbacks: list[Callable[[str, dict], None]] = []

        # Price cache (latest price per coin)
        self.current_prices: dict[str, PriceTick] = {}

        # 24h data cache (updated less frequently)
        self._ticker_data: dict[str, dict] = {}

        # Status tracking
        self.status = FeedStatus(exchange=self.exchange)

        # Reconnection settings
        ws_config = self.config.get('websocket', {})
        self._reconnect_delay = ws_config.get('reconnect_delay_initial', 1.0)
        self._reconnect_delay_max = ws_config.get('reconnect_delay_max', 30.0)
        self._ping_interval = ws_config.get('ping_interval', 20)
        self._stale_threshold = ws_config.get('stale_threshold_seconds', 5)

        # Symbol mapping
        self._symbol_to_coin: dict[str, str] = {}
        self._setup_symbol_mapping()

        logger.info(f"MarketFeed initialized: {self.exchange}, {len(self.coin_configs)} coins")

    def _load_config(self, config_path: Optional[str] = None) -> dict:
        """Load configuration from coins.json."""
        if config_path is None:
            possible_paths = [
                Path(__file__).parent.parent / 'config' / 'coins.json',
                Path('config/coins.json'),
                Path('/mnt/c/documents/crypto-trading-bot/config/coins.json'),
            ]
            for path in possible_paths:
                if path.exists():
                    config_path = str(path)
                    break
            else:
                logger.warning("coins.json not found, using defaults")
                return self._default_config()

        with open(config_path, 'r') as f:
            return json.load(f)

    def _default_config(self) -> dict:
        return {
            'exchange': 'bybit',
            'monitored_coins': [],
            'websocket': {
                'reconnect_delay_initial': 1.0,
                'reconnect_delay_max': 30.0,
                'ping_interval': 20,
                'stale_threshold_seconds': 5
            }
        }

    def _parse_coin_configs(self, coins: Optional[list[str]] = None) -> list[CoinConfig]:
        """Parse coin configurations."""
        all_configs = [
            CoinConfig(
                symbol=c['symbol'],
                binance=c['binance'],
                tier=c['tier'],
                name=c['name']
            )
            for c in self.config.get('monitored_coins', [])
        ]

        if coins is None:
            return all_configs

        coins_upper = [c.upper() for c in coins]
        filtered = [c for c in all_configs if c.symbol in coins_upper]

        # Add unknown coins with defaults
        existing = {c.symbol for c in filtered}
        for coin in coins_upper:
            if coin not in existing:
                filtered.append(CoinConfig(
                    symbol=coin,
                    binance=f"{coin}USDT",
                    tier=3,
                    name=coin
                ))

        return filtered

    def _setup_symbol_mapping(self):
        """Set up symbol to coin mapping based on exchange."""
        exchange_type = self.EXCHANGES[self.exchange]['type']

        for coin in self.coin_configs:
            if exchange_type == 'bybit':
                # Bybit uses BTCUSDT format
                symbol = f"{coin.symbol}USDT"
                self._symbol_to_coin[symbol] = coin.symbol
            else:
                # Binance uses btcusdt lowercase
                symbol = coin.binance.lower()
                self._symbol_to_coin[symbol] = coin.symbol

    def _get_ws_url(self) -> str:
        """Get WebSocket URL for the configured exchange."""
        return self.EXCHANGES[self.exchange]['url']

    async def connect(self):
        """
        Connect to exchange WebSocket and start receiving data.

        Auto-reconnects on disconnect.
        """
        if self._running:
            logger.warning("MarketFeed already running")
            return

        self._running = True
        await self._connect()

    async def _connect(self):
        """Internal connection method with reconnection logic."""
        url = self._get_ws_url()
        exchange_type = self.EXCHANGES[self.exchange]['type']

        while self._running:
            try:
                logger.info(f"Connecting to {self.exchange} WebSocket...")
                self.ws = await websockets.connect(
                    url,
                    ping_interval=None,
                    ping_timeout=None,
                    close_timeout=10,
                )

                self.status.connected = True
                self.status.last_message_time = time.time()
                self._reconnect_delay = self.config.get('websocket', {}).get('reconnect_delay_initial', 1.0)

                # Subscribe to streams based on exchange type
                if exchange_type == 'bybit':
                    await self._subscribe_bybit()
                else:
                    # Binance uses URL-based subscription
                    pass

                logger.info(f"Connected to {self.exchange} ({len(self.coin_configs)} coins)")
                self._emit_status('connected', {'exchange': self.exchange, 'coins': len(self.coin_configs)})

                # Start background tasks
                self._listen_task = asyncio.create_task(self._listen(exchange_type))
                self._ping_task = asyncio.create_task(self._ping_loop(exchange_type))
                self._monitor_task = asyncio.create_task(self._monitor_connection())

                await self._listen_task

            except (ConnectionClosed, WebSocketException, OSError) as e:
                self.status.connected = False
                self.status.errors += 1
                logger.error(f"WebSocket error: {e}")
                self._emit_status('disconnected', {'error': str(e)})

            except Exception as e:
                self.status.connected = False
                self.status.errors += 1
                logger.exception(f"Unexpected error: {e}")
                self._emit_status('error', {'error': str(e)})

            # Cancel background tasks
            for task in [self._ping_task, self._monitor_task]:
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            # Reconnect if still running
            if self._running:
                self.status.reconnect_count += 1
                logger.info(f"Reconnecting in {self._reconnect_delay:.1f}s (attempt {self.status.reconnect_count})")
                self._emit_status('reconnecting', {'delay': self._reconnect_delay})

                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, self._reconnect_delay_max)

    async def _subscribe_bybit(self):
        """Subscribe to Bybit streams in batches (Bybit limits to 10 args per request)."""
        # Build all subscription args
        args = []
        for coin in self.coin_configs:
            args.append(f"publicTrade.{coin.symbol}USDT")
            args.append(f"tickers.{coin.symbol}USDT")

        # Batch into groups of 10 (Bybit limit)
        batch_size = 10
        for i in range(0, len(args), batch_size):
            batch = args[i:i + batch_size]
            subscribe_msg = {
                "op": "subscribe",
                "args": batch
            }
            await self.ws.send(json.dumps(subscribe_msg))
            logger.debug(f"Subscribed to batch {i//batch_size + 1}: {len(batch)} streams")
            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(args):
                await asyncio.sleep(0.1)

        logger.info(f"Subscribed to {len(args)} Bybit streams in {(len(args) + batch_size - 1) // batch_size} batches")

    async def _listen(self, exchange_type: str):
        """Listen for WebSocket messages."""
        try:
            async for message in self.ws:
                self.status.messages_received += 1
                self.status.last_message_time = time.time()

                try:
                    data = json.loads(message)
                    if exchange_type == 'bybit':
                        await self._handle_bybit_message(data)
                    else:
                        await self._handle_binance_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON: {message[:100]}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")

        except ConnectionClosed:
            logger.info("WebSocket connection closed")
            raise

    async def _handle_bybit_message(self, data: dict):
        """
        Handle Bybit WebSocket message.

        Trade format:
        {
            "topic": "publicTrade.BTCUSDT",
            "data": [{
                "s": "BTCUSDT",
                "p": "42000.00",
                "v": "0.001",
                "S": "Buy",  # Buy or Sell
                "T": 1672515782136
            }]
        }

        Ticker format:
        {
            "topic": "tickers.BTCUSDT",
            "data": {
                "symbol": "BTCUSDT",
                "lastPrice": "42000.00",
                "price24hPcnt": "0.0234",
                "turnover24h": "1000000"
            }
        }
        """
        topic = data.get('topic', '')

        if topic.startswith('publicTrade.'):
            for trade in data.get('data', []):
                await self._handle_bybit_trade(trade)
        elif topic.startswith('tickers.'):
            await self._handle_bybit_ticker(data.get('data', {}))
        elif data.get('op') == 'subscribe':
            # Subscription confirmation
            if data.get('success'):
                logger.debug("Bybit subscription confirmed")
            else:
                logger.warning(f"Bybit subscription failed: {data}")

    async def _handle_bybit_trade(self, trade: dict):
        """Handle Bybit trade event."""
        symbol = trade.get('s', '')
        coin = self._symbol_to_coin.get(symbol)

        if not coin:
            return

        price = float(trade.get('p', 0))
        quantity = float(trade.get('v', 0))
        side = trade.get('S', '')
        timestamp = int(trade.get('T', 0))

        # is_buyer_maker = True means the maker was a buyer (so taker sold)
        is_buyer_maker = side == 'Sell'

        trade_event = TradeEvent(
            coin=coin,
            price=price,
            quantity=quantity,
            is_buyer_maker=is_buyer_maker,
            timestamp=timestamp
        )

        # Update price cache
        ticker = self._ticker_data.get(coin, {})
        self.current_prices[coin] = PriceTick(
            coin=coin,
            price=price,
            timestamp=timestamp,
            volume_24h=ticker.get('volume_24h', 0),
            change_24h=ticker.get('change_24h', 0)
        )

        # Fire callbacks
        for callback in self._trade_callbacks:
            try:
                callback(trade_event)
            except Exception as e:
                logger.error(f"Trade callback error: {e}")

        for callback in self._price_callbacks:
            try:
                callback(self.current_prices[coin])
            except Exception as e:
                logger.error(f"Price callback error: {e}")

    async def _handle_bybit_ticker(self, data: dict):
        """Handle Bybit ticker update."""
        symbol = data.get('symbol', '')
        coin = self._symbol_to_coin.get(symbol)

        if not coin:
            return

        change_pct = float(data.get('price24hPcnt', 0)) * 100  # Convert to percentage
        volume = float(data.get('turnover24h', 0))

        self._ticker_data[coin] = {
            'volume_24h': volume,
            'change_24h': change_pct
        }

    async def _handle_binance_message(self, data: dict):
        """Handle Binance WebSocket message."""
        stream = data.get('stream', '')
        payload = data.get('data', {})

        if '@trade' in stream:
            await self._handle_binance_trade(payload)
        elif '@miniTicker' in stream:
            await self._handle_binance_ticker(payload)

    async def _handle_binance_trade(self, data: dict):
        """Handle Binance trade event."""
        symbol = data.get('s', '').lower()
        coin = self._symbol_to_coin.get(symbol)

        if not coin:
            return

        price = float(data.get('p', 0))
        quantity = float(data.get('q', 0))
        timestamp = int(data.get('T', 0))
        is_buyer_maker = data.get('m', False)

        trade = TradeEvent(
            coin=coin,
            price=price,
            quantity=quantity,
            is_buyer_maker=is_buyer_maker,
            timestamp=timestamp
        )

        ticker = self._ticker_data.get(coin, {})
        self.current_prices[coin] = PriceTick(
            coin=coin,
            price=price,
            timestamp=timestamp,
            volume_24h=ticker.get('volume_24h', 0),
            change_24h=ticker.get('change_24h', 0)
        )

        for callback in self._trade_callbacks:
            try:
                callback(trade)
            except Exception as e:
                logger.error(f"Trade callback error: {e}")

        for callback in self._price_callbacks:
            try:
                callback(self.current_prices[coin])
            except Exception as e:
                logger.error(f"Price callback error: {e}")

    async def _handle_binance_ticker(self, data: dict):
        """Handle Binance mini ticker."""
        symbol = data.get('s', '').lower()
        coin = self._symbol_to_coin.get(symbol)

        if not coin:
            return

        close = float(data.get('c', 0))
        open_price = float(data.get('o', 0))
        volume = float(data.get('q', 0))

        change_24h = ((close - open_price) / open_price * 100) if open_price > 0 else 0

        self._ticker_data[coin] = {
            'volume_24h': volume,
            'change_24h': change_24h
        }

    async def _ping_loop(self, exchange_type: str):
        """Send periodic pings to keep connection alive."""
        while self._running and self.ws:
            try:
                await asyncio.sleep(self._ping_interval)
                if self.ws and self.ws.open:
                    if exchange_type == 'bybit':
                        # Bybit uses JSON ping
                        await self.ws.send(json.dumps({"op": "ping"}))
                    else:
                        await self.ws.ping()
            except Exception as e:
                logger.debug(f"Ping error: {e}")
                break

    async def _monitor_connection(self):
        """Monitor connection health."""
        while self._running:
            await asyncio.sleep(1)

            if self.status.last_message_time:
                elapsed = time.time() - self.status.last_message_time
                if elapsed > self._stale_threshold:
                    logger.warning(f"Feed stale: no data for {elapsed:.1f}s")
                    self._emit_status('stale', {'seconds': elapsed})

    def subscribe_price(self, callback: Callable[[PriceTick], None]):
        """Subscribe to price updates."""
        self._price_callbacks.append(callback)
        logger.debug(f"Price callback registered (total: {len(self._price_callbacks)})")

    def subscribe_trades(self, callback: Callable[[TradeEvent], None]):
        """Subscribe to individual trade events."""
        self._trade_callbacks.append(callback)
        logger.debug(f"Trade callback registered (total: {len(self._trade_callbacks)})")

    def subscribe_status(self, callback: Callable[[str, dict], None]):
        """Subscribe to connection status events."""
        self._status_callbacks.append(callback)

    def _emit_status(self, event: str, details: dict):
        """Emit status event to subscribers."""
        for callback in self._status_callbacks:
            try:
                callback(event, details)
            except Exception as e:
                logger.error(f"Status callback error: {e}")

    def get_price(self, coin: str) -> Optional[PriceTick]:
        """Get the latest cached price for a coin."""
        return self.current_prices.get(coin.upper())

    def get_all_prices(self) -> dict[str, PriceTick]:
        """Get all cached prices."""
        return self.current_prices.copy()

    async def disconnect(self):
        """Gracefully disconnect from WebSocket."""
        logger.info("Disconnecting MarketFeed...")
        self._running = False

        if self.ws:
            await self.ws.close()

        for task in [self._listen_task, self._ping_task, self._monitor_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self.status.connected = False
        logger.info("MarketFeed disconnected")

    def get_status(self) -> dict:
        """Get current feed status."""
        return {
            'connected': self.status.connected,
            'exchange': self.status.exchange,
            'coins': len(self.coin_configs),
            'messages_received': self.status.messages_received,
            'reconnect_count': self.status.reconnect_count,
            'errors': self.status.errors,
            'prices_cached': len(self.current_prices),
            'last_message_age': (
                time.time() - self.status.last_message_time
                if self.status.last_message_time else None
            )
        }

    def get_health(self) -> dict:
        """Get component health status for monitoring.

        Returns:
            Dict with status (healthy/degraded/failed), last_activity, error_count, metrics.
        """
        now = time.time()
        last_msg_age = (
            now - self.status.last_message_time
            if self.status.last_message_time else None
        )

        # Determine health status
        if not self.status.connected:
            status = "failed"
        elif last_msg_age is None or last_msg_age > 10:
            status = "degraded"
        elif last_msg_age > 5:
            status = "degraded"
        else:
            status = "healthy"

        return {
            "status": status,
            "last_activity": datetime.fromtimestamp(
                self.status.last_message_time
            ).isoformat() if self.status.last_message_time else None,
            "error_count": self.status.errors,
            "metrics": {
                "connected": self.status.connected,
                "exchange": self.status.exchange,
                "messages_received": self.status.messages_received,
                "reconnect_count": self.status.reconnect_count,
                "last_message_age_seconds": round(last_msg_age, 2) if last_msg_age else None,
                "coins_with_prices": len(self.current_prices),
            }
        }


async def test_feed(coins: list[str] = ['BTC', 'ETH', 'SOL'], duration: int = 30, exchange: str = 'bybit'):
    """Test the market feed."""
    feed = MarketFeed(coins, exchange=exchange)
    count = {'trades': 0}

    def on_price(tick: PriceTick):
        count['trades'] += 1
        if count['trades'] % 5 == 0:
            print(f"{tick.coin}: ${tick.price:,.2f} ({tick.change_24h:+.2f}%)")

    def on_status(event: str, details: dict):
        print(f"[STATUS] {event}: {details}")

    feed.subscribe_price(on_price)
    feed.subscribe_status(on_status)

    print(f"Starting {exchange} feed for {coins} ({duration}s test)...")

    async def run():
        await feed.connect()

    async def stop():
        await asyncio.sleep(duration)
        await feed.disconnect()
        print(f"\nTest complete: {count['trades']} price updates received")
        for coin, price in feed.get_all_prices().items():
            print(f"  {coin}: ${price.price:,.2f}")

    await asyncio.gather(run(), stop())


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(test_feed())
