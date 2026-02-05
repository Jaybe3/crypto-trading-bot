"""
Trading System - Main Entry Point (Phase 2).

Wires together MarketFeed, Sniper, and TradeJournal into a unified
trading system with health monitoring and clean lifecycle management.

Usage:
    # Run live
    python src/main.py

    # Run with specific exchange
    TRADING_EXCHANGE=binance_us python src/main.py
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
from src.knowledge import KnowledgeBrain
from src.coin_scorer import CoinScorer
from src.quick_update import QuickUpdate
from src.pattern_library import PatternLibrary
from src.reflection import ReflectionEngine
from src.adaptation import AdaptationEngine
from src.profitability import ProfitabilityTracker, SnapshotScheduler, TimeFrame
from src.effectiveness import EffectivenessMonitor, EffectivenessRating
from src.dashboard_v2 import DashboardServer

# Phase 3: Technical Analysis + Market Sentiment
from src.technical.candle_fetcher import CandleFetcher
from src.technical.manager import TechnicalManager
from src.sentiment.context_manager import ContextManager

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
        self.knowledge: Optional[KnowledgeBrain] = None
        self.coin_scorer: Optional[CoinScorer] = None
        self.quick_update: Optional[QuickUpdate] = None
        self.pattern_library: Optional[PatternLibrary] = None
        self.reflection_engine: Optional[ReflectionEngine] = None
        self.adaptation_engine: Optional[AdaptationEngine] = None
        self.profitability_tracker: Optional[ProfitabilityTracker] = None
        self.snapshot_scheduler: Optional[SnapshotScheduler] = None
        self.effectiveness_monitor: Optional[EffectivenessMonitor] = None
        self.dashboard: Optional[DashboardServer] = None

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

            # Start ReflectionEngine (TASK-131)
            if self.reflection_engine:
                logger.info("Starting ReflectionEngine...")
                await self.reflection_engine.start()

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

        # Initialize Database (shared by multiple components)
        logger.info("Initializing Database...")
        self.db = Database()

        # Initialize Knowledge Brain, Coin Scorer, and Pattern Library
        logger.info("Initializing Knowledge Brain...")
        self.knowledge = KnowledgeBrain(self.db)
        self.coin_scorer = CoinScorer(self.knowledge, self.db)
        self.pattern_library = PatternLibrary(self.knowledge)
        kb_stats = self.knowledge.get_stats_summary()
        pl_stats = self.pattern_library.get_stats_summary()
        logger.info(f"Knowledge Brain: {kb_stats['coins']['total']} coins, "
                   f"{kb_stats['coins']['blacklisted']} blacklisted")
        logger.info(f"Pattern Library: {pl_stats['total_patterns']} patterns, "
                   f"{pl_stats['high_confidence']} high-confidence")

        # Initialize QuickUpdate (TASK-130: post-trade knowledge updates)
        logger.info("Initializing QuickUpdate...")
        self.quick_update = QuickUpdate(
            coin_scorer=self.coin_scorer,
            pattern_library=self.pattern_library,
            db=self.db,
        )

        # Initialize Sniper (with quick_update for TASK-130)
        logger.info("Initializing Sniper...")
        self.sniper = Sniper(
            self.journal,
            initial_balance=self.initial_balance,
            state_path=self._state_path,
            quick_update=self.quick_update,
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

        # Phase 3: Technical Analysis + Market Sentiment
        try:
            candle_fetcher = CandleFetcher(cache_seconds=60)
            self.technical_manager = TechnicalManager(candle_fetcher)
            logger.info("Phase 3: TechnicalManager initialized")
        except Exception as e:
            logger.warning(f"Phase 3: TechnicalManager init failed, continuing without: {e}")
            self.technical_manager = None

        try:
            self.context_manager = ContextManager()
            logger.info("Phase 3: ContextManager initialized")
        except Exception as e:
            logger.warning(f"Phase 3: ContextManager init failed, continuing without: {e}")
            self.context_manager = None

        # Initialize Strategist (if enabled)
        if STRATEGIST_ENABLED:
            logger.info("Initializing Strategist...")
            self.llm = LLMInterface()
            self.strategist = Strategist(
                llm=self.llm,
                market_feed=self.market_feed,
                knowledge=self.knowledge,
                coin_scorer=self.coin_scorer,
                pattern_library=self.pattern_library,
                db=self.db,
                interval_seconds=STRATEGIST_INTERVAL,
                technical_manager=self.technical_manager,
                context_manager=self.context_manager,
            )
            logger.info(f"Strategist ready (interval={STRATEGIST_INTERVAL}s)")

            # Initialize AdaptationEngine (TASK-133: Adaptation Application)
            logger.info("Initializing AdaptationEngine...")
            self.adaptation_engine = AdaptationEngine(
                knowledge=self.knowledge,
                coin_scorer=self.coin_scorer,
                pattern_library=self.pattern_library,
                db=self.db,
            )

            # Initialize ReflectionEngine (TASK-131: Deep Reflection)
            logger.info("Initializing ReflectionEngine...")
            self.reflection_engine = ReflectionEngine(
                journal=self.journal,
                knowledge=self.knowledge,
                llm=self.llm,
                db=self.db,
                adaptation_engine=self.adaptation_engine,
            )
            # Wire reflection engine to quick update
            self.quick_update.set_reflection_engine(self.reflection_engine)
            logger.info("ReflectionEngine ready (triggers: 1h or 10 trades, with adaptations)")
        else:
            logger.info("Strategist disabled")

        # Initialize ProfitabilityTracker (TASK-141)
        logger.info("Initializing ProfitabilityTracker...")
        self.profitability_tracker = ProfitabilityTracker(
            db=self.db,
            journal=self.journal,
            initial_balance=self.initial_balance,
        )
        self.snapshot_scheduler = SnapshotScheduler(self.profitability_tracker)
        logger.info("ProfitabilityTracker ready")

        # Initialize EffectivenessMonitor (TASK-142)
        if self.adaptation_engine:
            logger.info("Initializing EffectivenessMonitor...")
            self.effectiveness_monitor = EffectivenessMonitor(
                db=self.db,
                journal=self.journal,
                profitability=self.profitability_tracker,
                adaptation_engine=self.adaptation_engine,
                knowledge=self.knowledge,
            )
            logger.info("EffectivenessMonitor ready")

        # Wire callbacks
        self._wire_callbacks()

        # Restore runtime state (TASK-140)
        self._restore_runtime_state()

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
        health_check_interval = 30  # Check health every 30 seconds
        last_health_check = 0
        last_snapshot_check = 0
        snapshot_check_interval = 300  # Check for snapshots every 5 minutes
        last_effectiveness_check = 0
        effectiveness_check_interval = 3600  # Check effectiveness every hour

        while self._running:
            await asyncio.sleep(1)

            now = time.time()

            # Periodic status log
            if now - self._last_status_log >= STATUS_LOG_INTERVAL:
                self._log_status()
                self._last_status_log = now

            # Periodic health check (TASK-140)
            if now - last_health_check >= health_check_interval:
                health = self.health_check()
                if health["overall"] != "healthy":
                    logger.warning(f"System health degraded: {health['overall']}")
                    for name, status in health["components"].items():
                        if status.get("status") != "healthy":
                            logger.warning(f"  {name}: {status.get('status')}")
                last_health_check = now

            # Periodic snapshot check (TASK-141)
            if now - last_snapshot_check >= snapshot_check_interval:
                if self.snapshot_scheduler:
                    taken = self.snapshot_scheduler.check_and_take_snapshots()
                    if taken:
                        logger.info(f"Snapshots taken: {[t.value for t in taken]}")
                last_snapshot_check = now

            # Periodic effectiveness check (TASK-142)
            if now - last_effectiveness_check >= effectiveness_check_interval:
                if self.effectiveness_monitor:
                    results = self.effectiveness_monitor.check_pending_adaptations()
                    for r in results:
                        if r.should_rollback:
                            logger.warning(
                                f"Adaptation {r.adaptation_id} flagged for rollback: "
                                f"{r.rollback_reason}"
                            )
                last_effectiveness_check = now

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

        # Stop reflection engine (TASK-131)
        if self.reflection_engine:
            logger.info("Stopping ReflectionEngine...")
            await self.reflection_engine.stop()

        # Save runtime state (TASK-140)
        logger.info("Saving runtime state...")
        self._save_runtime_state()

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

    # =========================================================================
    # Health Monitoring (TASK-140)
    # =========================================================================

    def health_check(self) -> dict:
        """Check health of all components.

        Returns:
            Dict with overall status and per-component health.
        """
        health = {
            "timestamp": datetime.now().isoformat(),
            "overall": "healthy",
            "components": {},
        }

        # Check each component
        components = [
            ("market_feed", self.market_feed),
            ("sniper", self.sniper),
            ("strategist", self.strategist),
            ("reflection_engine", self.reflection_engine),
            ("adaptation_engine", self.adaptation_engine),
            ("profitability_tracker", self.profitability_tracker),
            ("effectiveness_monitor", self.effectiveness_monitor),
        ]

        for name, component in components:
            if component is None:
                health["components"][name] = {"status": "not_initialized"}
                continue

            try:
                component_health = component.get_health()
                health["components"][name] = component_health

                # Aggregate overall status
                status = component_health.get("status", "unknown")
                if status == "failed":
                    health["overall"] = "failed"
                elif status == "degraded" and health["overall"] == "healthy":
                    health["overall"] = "degraded"
            except Exception as e:
                health["components"][name] = {
                    "status": "error",
                    "error": str(e),
                }
                health["overall"] = "degraded"

        return health

    # =========================================================================
    # Runtime State Persistence (TASK-140)
    # =========================================================================

    def _save_runtime_state(self) -> None:
        """Save runtime state for restart recovery."""
        if not self.db:
            return

        state = {
            "shutdown_time": datetime.now().isoformat(),
        }

        # Save reflection state
        if self.reflection_engine:
            state["last_reflection_time"] = (
                self.reflection_engine.last_reflection_time.isoformat()
                if self.reflection_engine.last_reflection_time
                else None
            )
            state["trades_since_reflection"] = self.reflection_engine.trades_since_reflection

        # Save system stats
        if self.health:
            stats = self.health.get_stats()
            state["uptime_seconds"] = stats.get("uptime_seconds", 0)
            state["tick_count"] = stats.get("tick_count", 0)

        try:
            self.db.save_runtime_state(state)
            logger.info("Runtime state saved")
        except Exception as e:
            logger.error(f"Failed to save runtime state: {e}")

    def _restore_runtime_state(self) -> None:
        """Restore runtime state after restart."""
        if not self.db:
            return

        try:
            state = self.db.get_runtime_state()
            if not state:
                logger.info("No runtime state to restore")
                return

            # Restore reflection state
            if self.reflection_engine and state.get("last_reflection_time"):
                try:
                    self.reflection_engine.last_reflection_time = datetime.fromisoformat(
                        state["last_reflection_time"]
                    )
                    self.reflection_engine.trades_since_reflection = state.get(
                        "trades_since_reflection", 0
                    )
                    logger.info(
                        f"Restored reflection state: last={state['last_reflection_time']}, "
                        f"trades_since={state.get('trades_since_reflection', 0)}"
                    )
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to restore reflection state: {e}")

            logger.info(f"Runtime state restored (shutdown: {state.get('shutdown_time', 'unknown')})")
        except Exception as e:
            logger.error(f"Failed to restore runtime state: {e}")

    # =========================================================================
    # Operational Commands (TASK-140)
    # =========================================================================

    def get_loop_stats(self) -> dict:
        """Get statistics about the learning loop.

        Returns:
            Dict with loop statistics.
        """
        stats = {
            "uptime_hours": (
                (datetime.now() - self._start_time).total_seconds() / 3600
                if self._start_time else 0
            ),
        }

        if self.sniper:
            sniper_status = self.sniper.get_status()
            stats["total_trades"] = sniper_status.get("trades_executed", 0)
            stats["total_pnl"] = sniper_status.get("total_pnl", 0)

        if self.reflection_engine:
            ref_stats = self.reflection_engine.get_stats()
            stats["total_reflections"] = ref_stats.get("reflections_completed", 0)
            stats["total_insights"] = ref_stats.get("insights_generated", 0)

        if self.adaptation_engine:
            adapt_stats = self.adaptation_engine.get_stats()
            stats["total_adaptations"] = adapt_stats.get("adaptations_applied", 0)

        if self.knowledge:
            kb_stats = self.knowledge.get_stats_summary()
            stats["blacklisted_coins"] = kb_stats.get("coins", {}).get("blacklisted", 0)
            stats["active_patterns"] = kb_stats.get("patterns", {}).get("active", 0)
            stats["active_rules"] = kb_stats.get("rules", {}).get("active", 0)

        if self.profitability_tracker:
            try:
                snapshot = self.profitability_tracker.get_current_snapshot()
                stats["win_rate"] = snapshot.win_rate
                stats["profit_factor"] = snapshot.profit_factor
                stats["max_drawdown_pct"] = snapshot.max_drawdown_pct
                stats["sharpe_ratio"] = snapshot.sharpe_ratio
            except Exception:
                pass

        return stats

    async def trigger_reflection(self) -> dict:
        """Manually trigger a reflection cycle.

        Returns:
            Dict with reflection result summary.
        """
        if not self.reflection_engine:
            return {"error": "ReflectionEngine not initialized"}

        try:
            result = await self.reflection_engine.reflect()
            return {
                "success": True,
                "trades_analyzed": result.trades_analyzed,
                "insights_count": len(result.insights),
                "adaptations_count": len(result.adaptations),
                "summary": result.summary,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def pause_trading(self, reason: str = "Manual pause") -> None:
        """Pause all trading (conditions stop triggering).

        Args:
            reason: Reason for pausing.
        """
        if self.sniper:
            # Clear all active conditions
            self.sniper.set_conditions([])
            logger.warning(f"Trading paused: {reason}")

    def resume_trading(self) -> None:
        """Resume trading by triggering new condition generation."""
        if self.strategist:
            # Force immediate condition generation
            logger.info("Trading resumed - triggering condition generation")
            # Note: Conditions will be generated on next Strategist cycle

    # =========================================================================
    # Profitability Tracking (TASK-141)
    # =========================================================================

    def get_profitability_snapshot(self, timeframe: str = "all_time") -> dict:
        """Get current profitability snapshot.

        Args:
            timeframe: "hour", "day", "week", "month", or "all_time"

        Returns:
            Dict with profitability metrics.
        """
        if not self.profitability_tracker:
            return {"error": "ProfitabilityTracker not initialized"}

        try:
            tf = TimeFrame(timeframe)
            snapshot = self.profitability_tracker.get_current_snapshot(tf)
            return snapshot.to_dict()
        except Exception as e:
            return {"error": str(e)}

    def get_performance_by_dimension(self, dimension: str) -> list:
        """Get performance breakdown by dimension.

        Args:
            dimension: "coin", "pattern", "hour_of_day", "day_of_week",
                      "exit_reason", "position_size", "hold_duration"

        Returns:
            List of performance dicts sorted by P&L.
        """
        if not self.profitability_tracker:
            return []

        try:
            results = self.profitability_tracker.get_performance_by_dimension(dimension)
            return [r.to_dict() for r in results]
        except Exception as e:
            logger.error(f"Error getting dimension performance: {e}")
            return []

    def get_improvement_metrics(self, lookback_days: int = 7) -> dict:
        """Get metrics showing if system is improving.

        Args:
            lookback_days: Days to compare against.

        Returns:
            Dict with improvement metrics.
        """
        if not self.profitability_tracker:
            return {"error": "ProfitabilityTracker not initialized"}

        return self.profitability_tracker.get_improvement_metrics(lookback_days)

    def get_equity_curve(self) -> list:
        """Get equity curve data for charting.

        Returns:
            List of {timestamp, balance, trade_id, pnl} dicts.
        """
        if not self.profitability_tracker:
            return []

        return self.profitability_tracker.get_equity_curve()

    # =========================================================================
    # Effectiveness Monitoring (TASK-142)
    # =========================================================================

    def get_adaptation_effectiveness(self) -> dict:
        """Get effectiveness summary for all adaptations.

        Returns:
            Dict with effectiveness counts by rating.
        """
        if not self.effectiveness_monitor:
            return {"error": "EffectivenessMonitor not initialized"}

        return self.effectiveness_monitor.get_effectiveness_summary()

    def get_harmful_adaptations(self, hours: int = 168) -> list:
        """Get adaptations flagged as harmful.

        Args:
            hours: Hours to look back.

        Returns:
            List of harmful adaptation dicts.
        """
        if not self.effectiveness_monitor:
            return []

        return self.effectiveness_monitor.get_harmful_adaptations(hours)

    def rollback_adaptation(self, adaptation_id: str) -> dict:
        """Execute rollback of a harmful adaptation.

        Args:
            adaptation_id: ID of adaptation to rollback.

        Returns:
            Dict with rollback result.
        """
        if not self.effectiveness_monitor:
            return {"error": "EffectivenessMonitor not initialized"}

        # Get rollback suggestion first
        suggestion = self.effectiveness_monitor.suggest_rollback(adaptation_id)
        if not suggestion.get("can_rollback"):
            return {
                "success": False,
                "error": suggestion.get("rollback_action", "Cannot rollback"),
            }

        # Execute rollback
        success = self.effectiveness_monitor.execute_rollback(adaptation_id)

        return {
            "success": success,
            "adaptation_id": adaptation_id,
            "action": suggestion.get("action"),
            "target": suggestion.get("target"),
            "rollback_action": suggestion.get("rollback_action"),
        }


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Trading System v2")
    parser.add_argument(
        "--dashboard", action="store_true",
        help="Start the dashboard web server"
    )
    parser.add_argument(
        "--port", type=int, default=8080,
        help="Dashboard port (default: 8080)"
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0",
        help="Dashboard host (default: 0.0.0.0)"
    )
    args = parser.parse_args()

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
        # Initialize components first
        await system.start_components()

        # Start dashboard if requested
        if args.dashboard:
            logger.info(f"Starting dashboard on http://{args.host}:{args.port}")
            system.dashboard = DashboardServer(system)
            # Run dashboard in background task
            asyncio.create_task(system.dashboard.start(host=args.host, port=args.port))

        if not system.test_mode:
            await system._connect_feed()

            # Start Strategist after feed is connected
            if system.strategist:
                logger.info("Starting Strategist...")
                await system.strategist.start()

            # Start ReflectionEngine (TASK-131)
            if system.reflection_engine:
                logger.info("Starting ReflectionEngine...")
                await system.reflection_engine.start()

        system._running = True
        logger.info("Trading system started - entering main loop")

        await system._main_loop()
    except asyncio.CancelledError:
        logger.info("Main loop cancelled")
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt")
    finally:
        await system.stop()


if __name__ == "__main__":
    asyncio.run(main())
