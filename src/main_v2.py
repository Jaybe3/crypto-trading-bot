"""
Trading System v2 - Main Entry Point.

Wires together MarketFeed, Sniper, and TradeJournal into a unified
trading system with health monitoring and clean lifecycle management.

Usage:
    # Run live
    python src/main_v2.py

    # Run with specific exchange
    TRADING_EXCHANGE=binance_us python src/main_v2.py
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.market_feed import MarketFeed, PriceTick
from src.sniper import Sniper
from src.journal import TradeJournal, MarketContext
from src.models.trade_condition import TradeCondition
from src.strategist import Strategist
from src.llm_interface import LLMInterface
from src.database import Database

# Import settings
try:
    from config.settings import (
        TRADEABLE_COINS, DEFAULT_EXCHANGE, INITIAL_BALANCE,
        STALE_DATA_THRESHOLD, STATUS_LOG_INTERVAL, SNIPER_STATE_PATH,
        STRATEGIST_INTERVAL, STRATEGIST_ENABLED
    )
except ImportError:
    # Defaults if config not available
    TRADEABLE_COINS = ["BTC", "ETH", "SOL"]
    DEFAULT_EXCHANGE = "bybit"
    INITIAL_BALANCE = 10000.0
    STALE_DATA_THRESHOLD = 5
    STATUS_LOG_INTERVAL = 60
    SNIPER_STATE_PATH = "data/sniper_state.json"
    STRATEGIST_INTERVAL = 180  # 3 minutes
    STRATEGIST_ENABLED = True

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("TradingSystem")


class HealthMonitor:
    """
    Monitors system health and detects issues.

    Tracks tick throughput, detects stale data, and reports system status.
    """

    def __init__(self, stale_threshold: float = STALE_DATA_THRESHOLD):
        self.stale_threshold = stale_threshold
        self.last_tick_time: Optional[float] = None
        self.tick_count: int = 0
        self.error_count: int = 0
        self.start_time: float = time.time()
        self._last_prices: dict[str, float] = {}

    def on_tick(self, tick: PriceTick) -> None:
        """Called on each price tick."""
        self.last_tick_time = time.time()
        self.tick_count += 1
        self._last_prices[tick.coin] = tick.price

    def on_error(self, error: Exception) -> None:
        """Called when an error occurs."""
        self.error_count += 1
        logger.error(f"System error: {error}")

    @property
    def is_healthy(self) -> bool:
        """Check if system is healthy (receiving data)."""
        if self.last_tick_time is None:
            return False
        return time.time() - self.last_tick_time < self.stale_threshold

    @property
    def is_feed_stale(self) -> bool:
        """Check if feed data is stale."""
        if self.last_tick_time is None:
            return True
        return time.time() - self.last_tick_time >= self.stale_threshold

    @property
    def uptime_seconds(self) -> float:
        """Get system uptime in seconds."""
        return time.time() - self.start_time

    @property
    def ticks_per_second(self) -> float:
        """Calculate average ticks per second."""
        uptime = self.uptime_seconds
        if uptime <= 0:
            return 0
        return self.tick_count / uptime

    def get_stats(self) -> dict:
        """Get health statistics."""
        return {
            "healthy": self.is_healthy,
            "feed_stale": self.is_feed_stale,
            "last_tick_time": self.last_tick_time,
            "tick_count": self.tick_count,
            "ticks_per_second": round(self.ticks_per_second, 2),
            "error_count": self.error_count,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "coins_with_prices": len(self._last_prices),
        }

    def get_last_price(self, coin: str) -> Optional[float]:
        """Get last known price for a coin."""
        return self._last_prices.get(coin.upper())


class TradingSystem:
    """
    Main trading system orchestrator.

    Wires together MarketFeed, Sniper, and TradeJournal into a unified
    system with proper lifecycle management.

    Usage:
        system = TradingSystem()
        await system.start()  # Blocks until shutdown

    Test mode:
        system = TradingSystem(test_mode=True)
        await system.start_components()  # Initialize without main loop
        system.inject_condition(condition)
        system.inject_price("BTC", 50000.0)
        await system.stop()
    """

    def __init__(self,
                 exchange: str = DEFAULT_EXCHANGE,
                 coins: list[str] = None,
                 initial_balance: float = INITIAL_BALANCE,
                 test_mode: bool = False,
                 db_path: Optional[str] = None,
                 state_path: Optional[str] = None):
        """
        Initialize the trading system.

        Args:
            exchange: Exchange to connect to (bybit, binance, binance_us)
            coins: List of coins to monitor (default: TRADEABLE_COINS)
            initial_balance: Starting paper balance
            test_mode: If True, don't connect to real exchange
            db_path: Path to journal database (default: data/trading_bot.db)
            state_path: Path to sniper state file (default: data/sniper_state.json)
        """
        self.exchange = exchange
        self.coins = coins or TRADEABLE_COINS
        self.initial_balance = initial_balance
        self.test_mode = test_mode
        self._db_path = db_path
        self._state_path = state_path or SNIPER_STATE_PATH

        # Components (initialized in start_components)
        self.market_feed: Optional[MarketFeed] = None
        self.sniper: Optional[Sniper] = None
        self.journal: Optional[TradeJournal] = None
        self.health: Optional[HealthMonitor] = None
        self.strategist: Optional[Strategist] = None
        self.llm: Optional[LLMInterface] = None
        self.db: Optional[Database] = None

        # State
        self._running = False
        self._start_time: Optional[datetime] = None
        self._last_status_log = 0

        logger.info(f"TradingSystem initialized (exchange={exchange}, coins={len(self.coins)}, test_mode={test_mode})")

    async def start(self) -> None:
        """
        Start the trading system and enter main loop.

        This method blocks until shutdown is triggered.
        """
        await self.start_components()

        if not self.test_mode:
            await self._connect_feed()

            # Start Strategist after feed is connected
            if self.strategist:
                logger.info("Starting Strategist...")
                await self.strategist.start()

        self._running = True
        logger.info("Trading system started - entering main loop")

        try:
            await self._main_loop()
        except asyncio.CancelledError:
            logger.info("Main loop cancelled")
        finally:
            await self.stop()

    async def start_components(self) -> None:
        """
        Initialize all components without entering main loop.

        Useful for test mode or manual control.
        """
        self._start_time = datetime.now()

        # Initialize Journal
        logger.info("Initializing TradeJournal...")
        self.journal = TradeJournal(db_path=self._db_path, enable_async=True)

        # Initialize Sniper
        logger.info("Initializing Sniper...")
        self.sniper = Sniper(
            self.journal,
            initial_balance=self.initial_balance,
            state_path=self._state_path
        )

        # Try to load persisted state
        if self.sniper.load_state():
            logger.info(f"Restored state: balance=${self.sniper.balance:.2f}, "
                       f"positions={len(self.sniper.open_positions)}")

        # Initialize MarketFeed
        logger.info(f"Initializing MarketFeed ({self.exchange}, {len(self.coins)} coins)...")
        self.market_feed = MarketFeed(self.coins, exchange=self.exchange)

        # Pass market feed to journal for post-trade capture
        self.journal.market_feed = self.market_feed

        # Initialize Health Monitor
        self.health = HealthMonitor()

        # Initialize Strategist (if enabled)
        if STRATEGIST_ENABLED:
            logger.info("Initializing Strategist...")
            self.db = Database()
            self.llm = LLMInterface()
            self.strategist = Strategist(
                llm=self.llm,
                market_feed=self.market_feed,
                db=self.db,
                interval_seconds=STRATEGIST_INTERVAL,
            )
            logger.info(f"Strategist ready (interval={STRATEGIST_INTERVAL}s)")
        else:
            logger.info("Strategist disabled")

        # Wire callbacks
        self._wire_callbacks()

        logger.info("All components initialized")

    def _wire_callbacks(self) -> None:
        """Wire up component callbacks."""
        # Feed → Sniper
        self.market_feed.subscribe_price(self._on_price_tick)

        # Feed → Health
        self.market_feed.subscribe_price(self.health.on_tick)

        # Feed status changes
        self.market_feed.subscribe_status(self._on_feed_status)

        # Sniper execution events
        self.sniper.subscribe(self._on_execution)

        # Strategist → Sniper (handoff)
        if self.strategist:
            self.strategist.subscribe_conditions(self._on_new_conditions)

        logger.debug("Callbacks wired")

    def _on_price_tick(self, tick: PriceTick) -> None:
        """Handle price tick from feed."""
        try:
            self.sniper.on_price_tick(tick)
        except Exception as e:
            logger.error(f"Sniper tick error: {e}")
            if self.health:
                self.health.on_error(e)

    def _on_feed_status(self, event: str, data: dict) -> None:
        """Handle feed status changes."""
        if event == "connected":
            logger.info(f"Feed connected to {data.get('exchange', 'unknown')}")
        elif event == "disconnected":
            logger.warning("Feed disconnected")
        elif event == "reconnecting":
            logger.info(f"Feed reconnecting (attempt {data.get('attempt', '?')})")
        elif event == "error":
            logger.error(f"Feed error: {data.get('error', 'unknown')}")

    def _on_execution(self, event) -> None:
        """Handle sniper execution events."""
        if event.event_type == "entry":
            logger.info(f"TRADE ENTRY: {event.direction} {event.coin} @ ${event.price:,.2f}")
        elif event.event_type == "exit":
            pnl_str = f"+${event.pnl:.2f}" if event.pnl >= 0 else f"-${abs(event.pnl):.2f}"
            logger.info(f"TRADE EXIT: {event.coin} @ ${event.price:,.2f} [{event.reason}] {pnl_str}")

    def _on_new_conditions(self, conditions: list[TradeCondition]) -> None:
        """Handle new conditions from Strategist (handoff to Sniper)."""
        logger.info("=" * 50)
        logger.info("STRATEGIST → SNIPER HANDOFF")
        logger.info(f"Conditions received: {len(conditions)}")
        for c in conditions:
            logger.info(f"  {c.direction} {c.coin} @ ${c.trigger_price:,.2f} ({c.trigger_condition})")

        # Pass to Sniper
        active_count = self.sniper.set_conditions(conditions)
        logger.info(f"Sniper now watching {active_count} conditions")
        logger.info("=" * 50)

    async def _connect_feed(self) -> None:
        """Connect to exchange WebSocket."""
        logger.info(f"Connecting to {self.exchange}...")

        # Start connection (runs in background)
        asyncio.create_task(self.market_feed.connect())

        # Wait for connection
        for _ in range(30):  # 30 second timeout
            await asyncio.sleep(1)
            if self.market_feed.status.connected:
                logger.info("Feed connected successfully")
                return

        logger.warning("Feed connection timeout - will keep trying in background")

    async def _main_loop(self) -> None:
        """Main system loop - status logging and health checks."""
        while self._running:
            await asyncio.sleep(1)

            # Periodic status log
            now = time.time()
            if now - self._last_status_log >= STATUS_LOG_INTERVAL:
                self._log_status()
                self._last_status_log = now

    def _log_status(self) -> None:
        """Log current system status."""
        if not self.health or not self.sniper:
            return

        health = self.health.get_stats()
        sniper_status = self.sniper.get_status()

        feed_status = "OK" if health["healthy"] else "STALE"
        strategist_status = "ON" if self.strategist else "OFF"

        logger.info(
            f"STATUS: Feed={feed_status} | Strategist={strategist_status} | "
            f"Ticks={health['tick_count']} ({health['ticks_per_second']}/s) | "
            f"Conditions={sniper_status['active_conditions']} | "
            f"Positions={sniper_status['open_positions']} | "
            f"Balance=${sniper_status['balance']:,.2f} | "
            f"PnL=${sniper_status['total_pnl']:+,.2f}"
        )

    async def stop(self) -> None:
        """
        Gracefully stop the trading system.

        Saves state, disconnects feed, and flushes journal.
        """
        logger.info("Stopping trading system...")
        self._running = False

        # Stop strategist first
        if self.strategist:
            logger.info("Stopping Strategist...")
            await self.strategist.stop()

        # Save sniper state
        if self.sniper:
            logger.info("Saving sniper state...")
            self.sniper.save_state()

        # Disconnect feed
        if self.market_feed:
            logger.info("Disconnecting feed...")
            await self.market_feed.disconnect()

        # Stop journal
        if self.journal:
            logger.info("Stopping journal...")
            self.journal.stop()

        # Final stats
        if self.health:
            stats = self.health.get_stats()
            logger.info(f"Final stats: {stats['tick_count']} ticks, "
                       f"{stats['error_count']} errors, "
                       f"{stats['uptime_seconds']:.1f}s uptime")

        logger.info("Trading system stopped")

    # =========================================================================
    # Test Mode Methods
    # =========================================================================

    def inject_condition(self, condition: TradeCondition) -> bool:
        """
        Inject a test condition (test mode).

        Args:
            condition: TradeCondition to add

        Returns:
            True if added successfully
        """
        if not self.sniper:
            raise RuntimeError("System not started - call start_components() first")
        return self.sniper.add_condition(condition)

    def inject_price(self, coin: str, price: float, timestamp: int = None) -> None:
        """
        Inject a test price tick (test mode).

        Args:
            coin: Coin symbol
            price: Price value
            timestamp: Optional timestamp (default: now)
        """
        if not self.sniper:
            raise RuntimeError("System not started - call start_components() first")

        ts = timestamp or int(time.time() * 1000)
        tick = PriceTick(
            coin=coin.upper(),
            price=price,
            timestamp=ts,
            volume_24h=0,
            change_24h=0
        )
        self._on_price_tick(tick)
        if self.health:
            self.health.on_tick(tick)

    # =========================================================================
    # Status Methods
    # =========================================================================

    def get_status(self) -> dict:
        """Get complete system status."""
        result = {
            "running": self._running,
            "test_mode": self.test_mode,
            "exchange": self.exchange,
            "start_time": self._start_time.isoformat() if self._start_time else None,
        }

        if self.health:
            result["health"] = self.health.get_stats()

        if self.sniper:
            result["sniper"] = self.sniper.get_status()

        if self.market_feed:
            result["feed"] = self.market_feed.get_status()

        if self.journal:
            result["journal"] = {
                "entry_count": self.journal.entry_count(),
                "pending_entries": len(self.journal.pending_entries),
            }

        if self.strategist:
            result["strategist"] = self.strategist.get_stats()

        return result

    def get_positions(self) -> list:
        """Get current open positions."""
        if not self.sniper:
            return []
        return self.sniper.get_positions()

    def get_conditions(self) -> list:
        """Get active conditions."""
        if not self.sniper:
            return []
        return self.sniper.get_conditions()


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    """Main entry point."""
    system = TradingSystem()

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Shutdown signal received")
        asyncio.create_task(system.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    try:
        await system.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt")
        await system.stop()


if __name__ == "__main__":
    asyncio.run(main())
