"""
Trade Journal - Comprehensive trade recording for the learning system.

Captures full context for every trade:
- Entry: price, time, reasoning, market conditions
- Exit: price, time, reason, P&L
- Post-trade: what happened after (did we exit too early?)

This is the raw data that feeds the Reflection Engine.
"""

import asyncio
import logging
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field, asdict, fields
from datetime import datetime, timedelta
from pathlib import Path
from queue import Queue, Empty
from typing import Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.sniper import Position
    from src.market_feed import MarketFeed

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class MarketContext:
    """
    Market conditions at time of trade.

    Captured at entry to understand what environment the trade was made in.
    The Reflection Engine uses this to find patterns like:
    - "We lose money in volatile markets"
    - "Trending BTC helps altcoin longs"
    """
    regime: Optional[str] = None           # "trending", "ranging", "volatile"
    volatility: Optional[float] = None     # ATR or similar measure
    funding_rate: Optional[float] = None   # Exchange funding rate
    cvd: Optional[float] = None            # Cumulative volume delta
    btc_trend: Optional[str] = None        # "up", "down", "sideways"
    btc_price: Optional[float] = None      # BTC price at time

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> 'MarketContext':
        if d is None:
            return cls()
        valid_keys = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid_keys})


@dataclass
class JournalEntry:
    """
    Complete trade record from entry through post-exit.

    This captures everything needed to learn from the trade:
    - Why we entered (conditions, reasoning, market state)
    - What happened (entry price, exit price, duration)
    - The outcome (P&L, exit reason)
    - What happened next (did we exit too early?)
    """
    # Identity
    id: str
    position_id: str                       # Links to Sniper position

    # Entry details
    entry_time: datetime
    entry_price: float
    entry_reason: str                      # Human-readable reasoning

    # Trade parameters
    coin: str
    direction: str                         # "LONG" or "SHORT"
    position_size_usd: float
    stop_loss_price: float
    take_profit_price: float

    # Strategy context
    strategy_id: str
    condition_id: str
    pattern_id: Optional[str] = None       # If pattern-based entry

    # Market context at entry
    market_regime: Optional[str] = None
    volatility: Optional[float] = None
    funding_rate: Optional[float] = None
    cvd: Optional[float] = None
    btc_trend: Optional[str] = None
    btc_price: Optional[float] = None

    # Timing context
    hour_of_day: int = 0                   # 0-23 UTC
    day_of_week: int = 0                   # 0-6 (Mon-Sun)

    # Exit details (filled when closed)
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None      # "stop_loss", "take_profit", "manual"

    # Outcome (filled when closed)
    pnl_usd: Optional[float] = None
    pnl_pct: Optional[float] = None
    duration_seconds: Optional[int] = None

    # Post-trade prices (filled async after exit)
    price_1min_after: Optional[float] = None
    price_5min_after: Optional[float] = None
    price_15min_after: Optional[float] = None
    missed_profit_usd: Optional[float] = None

    # Metadata
    status: str = "open"                   # "open", "closed", "post_tracked"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        d = asdict(self)
        # Convert datetimes to ISO strings
        for key in ['entry_time', 'exit_time', 'created_at', 'updated_at']:
            if d.get(key) and isinstance(d[key], datetime):
                d[key] = d[key].isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'JournalEntry':
        """Create from dictionary (database row)."""
        # Convert ISO strings back to datetimes
        for key in ['entry_time', 'exit_time', 'created_at', 'updated_at']:
            if d.get(key) and isinstance(d[key], str):
                try:
                    d[key] = datetime.fromisoformat(d[key])
                except (ValueError, TypeError):
                    d[key] = None

        # Filter to only valid fields
        valid_fields = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in d.items() if k in valid_fields}
        return cls(**filtered)

    def is_winner(self) -> bool:
        """Check if this trade was profitable."""
        return self.pnl_usd is not None and self.pnl_usd > 0

    def is_loser(self) -> bool:
        """Check if this trade lost money."""
        return self.pnl_usd is not None and self.pnl_usd < 0


# =============================================================================
# Database Operations
# =============================================================================

class JournalDatabase:
    """
    SQLite database operations for the trade journal.

    Handles persistence with proper connection management.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            project_root = Path(__file__).parent.parent
            self.db_path = project_root / "data" / "trading_bot.db"
        else:
            self.db_path = Path(db_path)

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize table
        self._create_table()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _create_table(self) -> None:
        """Create trade_journal table if not exists."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_journal (
                    id TEXT PRIMARY KEY,
                    position_id TEXT NOT NULL,
                    entry_time TIMESTAMP NOT NULL,
                    entry_price REAL NOT NULL,
                    entry_reason TEXT,
                    coin TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    position_size_usd REAL NOT NULL,
                    stop_loss_price REAL,
                    take_profit_price REAL,
                    strategy_id TEXT,
                    condition_id TEXT,
                    pattern_id TEXT,
                    market_regime TEXT,
                    volatility REAL,
                    funding_rate REAL,
                    cvd REAL,
                    btc_trend TEXT,
                    btc_price REAL,
                    hour_of_day INTEGER,
                    day_of_week INTEGER,
                    exit_time TIMESTAMP,
                    exit_price REAL,
                    exit_reason TEXT,
                    pnl_usd REAL,
                    pnl_pct REAL,
                    duration_seconds INTEGER,
                    price_1min_after REAL,
                    price_5min_after REAL,
                    price_15min_after REAL,
                    missed_profit_usd REAL,
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def insert(self, entry: JournalEntry) -> None:
        """Insert a new journal entry."""
        d = entry.to_dict()
        columns = ', '.join(d.keys())
        placeholders = ', '.join(['?' for _ in d])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"INSERT OR REPLACE INTO trade_journal ({columns}) VALUES ({placeholders})",
                list(d.values())
            )
            conn.commit()

    def update(self, entry_id: str, updates: dict) -> None:
        """Update an existing entry."""
        updates['updated_at'] = datetime.now().isoformat()
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE trade_journal SET {set_clause} WHERE id = ?",
                list(updates.values()) + [entry_id]
            )
            conn.commit()

    def get(self, entry_id: str) -> Optional[JournalEntry]:
        """Get a single entry by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trade_journal WHERE id = ?", (entry_id,))
            row = cursor.fetchone()
            if row:
                return JournalEntry.from_dict(dict(row))
            return None

    def get_by_position(self, position_id: str) -> Optional[JournalEntry]:
        """Get entry by position ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM trade_journal WHERE position_id = ?",
                (position_id,)
            )
            row = cursor.fetchone()
            if row:
                return JournalEntry.from_dict(dict(row))
            return None

    def query(self,
              where: str = "1=1",
              params: tuple = (),
              order_by: str = "entry_time DESC",
              limit: int = 100) -> list[JournalEntry]:
        """Execute a query with WHERE clause."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM trade_journal WHERE {where} ORDER BY {order_by} LIMIT ?",
                params + (limit,)
            )
            return [JournalEntry.from_dict(dict(row)) for row in cursor.fetchall()]

    def count(self, where: str = "1=1", params: tuple = ()) -> int:
        """Count entries matching criteria."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT COUNT(*) FROM trade_journal WHERE {where}",
                params
            )
            return cursor.fetchone()[0]

    def aggregate(self,
                  select: str,
                  where: str = "1=1",
                  params: tuple = (),
                  group_by: str = None) -> list[dict]:
        """Run aggregate query."""
        query = f"SELECT {select} FROM trade_journal WHERE {where}"
        if group_by:
            query += f" GROUP BY {group_by}"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


# =============================================================================
# Async Write Queue
# =============================================================================

class AsyncWriteQueue:
    """
    Background write queue to avoid blocking the Sniper.

    Writes are queued and processed in a background thread.
    """

    def __init__(self, db: JournalDatabase):
        self.db = db
        self.queue: Queue = Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the background writer thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._process_queue, daemon=True)
        self._thread.start()
        logger.debug("Async write queue started")

    def stop(self) -> None:
        """Stop the background writer and flush remaining writes."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)

        # Flush remaining items
        while not self.queue.empty():
            try:
                operation, args = self.queue.get_nowait()
                self._execute(operation, args)
            except Empty:
                break

        logger.debug("Async write queue stopped")

    def enqueue_insert(self, entry: JournalEntry) -> None:
        """Queue an insert operation."""
        self.queue.put(('insert', entry))

    def enqueue_update(self, entry_id: str, updates: dict) -> None:
        """Queue an update operation."""
        self.queue.put(('update', (entry_id, updates)))

    def _process_queue(self) -> None:
        """Process queued writes in background thread."""
        while self._running:
            try:
                operation, args = self.queue.get(timeout=0.5)
                self._execute(operation, args)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Write queue error: {e}")

    def _execute(self, operation: str, args: Any) -> None:
        """Execute a queued operation."""
        try:
            if operation == 'insert':
                self.db.insert(args)
            elif operation == 'update':
                entry_id, updates = args
                self.db.update(entry_id, updates)
        except Exception as e:
            logger.error(f"Database write error: {e}")


# =============================================================================
# Trade Journal
# =============================================================================

class TradeJournal:
    """
    Comprehensive trade journaling system.

    Records full context for every trade - the raw data that feeds the learning system.

    Features:
    - Non-blocking writes (queue-based)
    - Full market context capture
    - Post-trade price tracking
    - Rich query interface for Reflection Engine

    Usage:
        journal = TradeJournal()

        # Record entry (called by Sniper)
        entry_id = journal.record_entry(position, market_context)

        # Record exit (called by Sniper)
        journal.record_exit(position, exit_price, timestamp, reason, pnl, pnl_pct)

        # Query for analysis (called by Reflection Engine)
        recent = journal.get_recent(hours=24)
        losers = journal.get_losers(limit=10)
        by_hour = journal.get_performance_by_hour()
    """

    def __init__(self,
                 db_path: Optional[str] = None,
                 market_feed: Optional['MarketFeed'] = None,
                 enable_async: bool = True):
        """
        Initialize the Trade Journal.

        Args:
            db_path: Path to SQLite database (default: data/trading_bot.db)
            market_feed: MarketFeed for post-trade price capture
            enable_async: Use async write queue (default True)
        """
        self.db = JournalDatabase(db_path)
        self.market_feed = market_feed

        # In-memory cache for open trades
        self.pending_entries: dict[str, JournalEntry] = {}

        # Async write queue
        self._write_queue: Optional[AsyncWriteQueue] = None
        if enable_async:
            self._write_queue = AsyncWriteQueue(self.db)
            self._write_queue.start()

        # Post-trade capture tasks
        self._post_trade_tasks: dict[str, asyncio.Task] = {}

        # Load any open entries from database
        self._load_pending_entries()

        # Track entry count for ID generation
        self._entry_count = 0

        logger.info("Trade Journal initialized")

    def _load_pending_entries(self) -> None:
        """Load open entries from database into memory."""
        open_entries = self.db.query(where="status = 'open'")
        for entry in open_entries:
            self.pending_entries[entry.position_id] = entry

        if open_entries:
            logger.info(f"Loaded {len(open_entries)} open journal entries")

    def _generate_id(self) -> str:
        """Generate unique entry ID."""
        self._entry_count += 1
        return f"j-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

    # =========================================================================
    # Entry Recording (called by Sniper)
    # =========================================================================

    def record_entry(self,
                     position: 'Position',
                     timestamp: int,
                     market_context: Optional[MarketContext] = None) -> str:
        """
        Record a new trade entry.

        Args:
            position: The opened position from Sniper
            timestamp: Entry timestamp in milliseconds
            market_context: Optional market conditions at entry

        Returns:
            The journal entry ID
        """
        entry_time = datetime.fromtimestamp(timestamp / 1000)

        # Extract market context fields
        ctx = market_context or MarketContext()

        entry = JournalEntry(
            id=self._generate_id(),
            position_id=position.id,
            entry_time=entry_time,
            entry_price=position.entry_price,
            entry_reason=position.reasoning,
            coin=position.coin,
            direction=position.direction,
            position_size_usd=position.size_usd,
            stop_loss_price=position.stop_loss_price,
            take_profit_price=position.take_profit_price,
            strategy_id=position.strategy_id,
            condition_id=position.condition_id,
            # Market context
            market_regime=ctx.regime,
            volatility=ctx.volatility,
            funding_rate=ctx.funding_rate,
            cvd=ctx.cvd,
            btc_trend=ctx.btc_trend,
            btc_price=ctx.btc_price,
            # Timing
            hour_of_day=entry_time.hour,
            day_of_week=entry_time.weekday(),
            # Metadata
            status="open",
        )

        # Store in pending
        self.pending_entries[position.id] = entry

        # Queue async write
        if self._write_queue:
            self._write_queue.enqueue_insert(entry)
        else:
            self.db.insert(entry)

        logger.info(
            f"JOURNAL ENTRY: {position.direction} {position.coin} @ ${position.entry_price:.2f} "
            f"[{entry.id}]"
        )

        return entry.id

    # =========================================================================
    # Exit Recording (called by Sniper)
    # =========================================================================

    def record_exit(self,
                    position: 'Position',
                    exit_price: float,
                    timestamp: int,
                    reason: str,
                    pnl: float) -> Optional[str]:
        """
        Record a trade exit.

        Args:
            position: The position being closed
            exit_price: Exit price
            timestamp: Exit timestamp in milliseconds
            reason: Exit reason ("stop_loss", "take_profit", "manual")
            pnl: Realized P&L in USD

        Returns:
            The journal entry ID, or None if not found
        """
        # Find the pending entry
        entry = self.pending_entries.pop(position.id, None)

        if entry is None:
            # Try to find in database
            entry = self.db.get_by_position(position.id)
            if entry is None:
                logger.warning(f"No journal entry found for position {position.id}")
                return None

        exit_time = datetime.fromtimestamp(timestamp / 1000)

        # Calculate metrics
        pnl_pct = (pnl / position.size_usd) * 100 if position.size_usd > 0 else 0
        duration = int((exit_time - entry.entry_time).total_seconds())

        # Update entry
        updates = {
            'exit_time': exit_time.isoformat(),
            'exit_price': exit_price,
            'exit_reason': reason,
            'pnl_usd': pnl,
            'pnl_pct': pnl_pct,
            'duration_seconds': duration,
            'status': 'closed',
        }

        # Apply updates to entry object
        for key, value in updates.items():
            if key == 'exit_time':
                entry.exit_time = exit_time
            else:
                setattr(entry, key, value)

        # Queue async write
        if self._write_queue:
            self._write_queue.enqueue_update(entry.id, updates)
        else:
            self.db.update(entry.id, updates)

        pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
        logger.info(
            f"JOURNAL EXIT: {position.coin} @ ${exit_price:.2f} [{reason}] "
            f"{pnl_str} ({pnl_pct:+.2f}%) [{entry.id}]"
        )

        # Schedule post-trade price capture
        self._schedule_post_trade_capture(entry)

        return entry.id

    # =========================================================================
    # Post-Trade Price Capture
    # =========================================================================

    def _schedule_post_trade_capture(self, entry: JournalEntry) -> None:
        """Schedule async capture of post-trade prices."""
        if self.market_feed is None:
            logger.debug("No market feed - skipping post-trade capture")
            return

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                task = asyncio.create_task(
                    self._capture_post_trade_prices(entry.id, entry.coin, entry.direction, entry.exit_price)
                )
                self._post_trade_tasks[entry.id] = task
            else:
                # Run in thread if no event loop
                threading.Thread(
                    target=self._capture_post_trade_sync,
                    args=(entry.id, entry.coin, entry.direction, entry.exit_price),
                    daemon=True
                ).start()
        except RuntimeError:
            # No event loop
            threading.Thread(
                target=self._capture_post_trade_sync,
                args=(entry.id, entry.coin, entry.direction, entry.exit_price),
                daemon=True
            ).start()

    async def _capture_post_trade_prices(self,
                                          entry_id: str,
                                          coin: str,
                                          direction: str,
                                          exit_price: float) -> None:
        """
        Capture prices at 1, 5, and 15 minutes after exit.

        This answers: "Did we exit too early?"
        """
        prices = {}

        try:
            # Wait 1 minute, capture
            await asyncio.sleep(60)
            tick = self.market_feed.get_price(coin)
            if tick:
                prices['price_1min_after'] = tick.price

            # Wait 4 more minutes (total 5), capture
            await asyncio.sleep(240)
            tick = self.market_feed.get_price(coin)
            if tick:
                prices['price_5min_after'] = tick.price

            # Wait 10 more minutes (total 15), capture
            await asyncio.sleep(600)
            tick = self.market_feed.get_price(coin)
            if tick:
                prices['price_15min_after'] = tick.price

            # Calculate missed profit
            if prices.get('price_15min_after'):
                missed = self._calculate_missed_profit(
                    direction, exit_price, prices['price_15min_after']
                )
                prices['missed_profit_usd'] = missed

            prices['status'] = 'post_tracked'

            # Update database
            if self._write_queue:
                self._write_queue.enqueue_update(entry_id, prices)
            else:
                self.db.update(entry_id, prices)

            logger.debug(f"Post-trade capture complete for {entry_id}: {prices}")

        except asyncio.CancelledError:
            logger.debug(f"Post-trade capture cancelled for {entry_id}")
        except Exception as e:
            logger.error(f"Post-trade capture error for {entry_id}: {e}")
        finally:
            self._post_trade_tasks.pop(entry_id, None)

    def _capture_post_trade_sync(self,
                                  entry_id: str,
                                  coin: str,
                                  direction: str,
                                  exit_price: float) -> None:
        """Synchronous version for when no event loop is available."""
        import time

        prices = {}

        try:
            # Wait 1 minute
            time.sleep(60)
            tick = self.market_feed.get_price(coin)
            if tick:
                prices['price_1min_after'] = tick.price

            # Wait 4 more minutes
            time.sleep(240)
            tick = self.market_feed.get_price(coin)
            if tick:
                prices['price_5min_after'] = tick.price

            # Wait 10 more minutes
            time.sleep(600)
            tick = self.market_feed.get_price(coin)
            if tick:
                prices['price_15min_after'] = tick.price

            if prices.get('price_15min_after'):
                missed = self._calculate_missed_profit(
                    direction, exit_price, prices['price_15min_after']
                )
                prices['missed_profit_usd'] = missed

            prices['status'] = 'post_tracked'
            self.db.update(entry_id, prices)

        except Exception as e:
            logger.error(f"Post-trade capture error: {e}")

    def _calculate_missed_profit(self,
                                  direction: str,
                                  exit_price: float,
                                  later_price: float) -> float:
        """
        Calculate profit missed by exiting when we did.

        For LONG: if price went higher, we missed profit
        For SHORT: if price went lower, we missed profit

        Returns positive number if we missed profit, negative if we dodged a bullet.
        """
        price_change_pct = (later_price - exit_price) / exit_price

        if direction == "SHORT":
            price_change_pct = -price_change_pct

        # Missed profit as percentage (positive = left money on table)
        return price_change_pct * 100

    # =========================================================================
    # Query Methods (for Reflection Engine)
    # =========================================================================

    def get_entry(self, entry_id: str) -> Optional[JournalEntry]:
        """Get a single entry by ID."""
        return self.db.get(entry_id)

    def get_by_position(self, position_id: str) -> Optional[JournalEntry]:
        """Get entry by position ID."""
        # Check pending first
        if position_id in self.pending_entries:
            return self.pending_entries[position_id]
        return self.db.get_by_position(position_id)

    def get_recent(self,
                   hours: int = 24,
                   status: Optional[str] = None,
                   limit: int = 100) -> list[JournalEntry]:
        """
        Get recent journal entries.

        Args:
            hours: How far back to look
            status: Filter by status ("open", "closed", "post_tracked")
            limit: Maximum entries to return
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        where = "entry_time >= ?"
        params = (cutoff.isoformat(),)

        if status:
            where += " AND status = ?"
            params += (status,)

        return self.db.query(where=where, params=params, limit=limit)

    def get_by_coin(self, coin: str, limit: int = 100) -> list[JournalEntry]:
        """Get entries for a specific coin."""
        return self.db.query(
            where="coin = ?",
            params=(coin.upper(),),
            limit=limit
        )

    def get_by_strategy(self, strategy_id: str, limit: int = 100) -> list[JournalEntry]:
        """Get entries for a specific strategy."""
        return self.db.query(
            where="strategy_id = ?",
            params=(strategy_id,),
            limit=limit
        )

    def get_by_exit_reason(self, reason: str, limit: int = 100) -> list[JournalEntry]:
        """Get entries by exit reason."""
        return self.db.query(
            where="exit_reason = ?",
            params=(reason,),
            limit=limit
        )

    def get_by_time_of_day(self, hour: int, limit: int = 100) -> list[JournalEntry]:
        """Get entries that occurred at a specific hour (0-23 UTC)."""
        return self.db.query(
            where="hour_of_day = ?",
            params=(hour,),
            limit=limit
        )

    def get_by_day_of_week(self, day: int, limit: int = 100) -> list[JournalEntry]:
        """Get entries that occurred on a specific day (0=Mon, 6=Sun)."""
        return self.db.query(
            where="day_of_week = ?",
            params=(day,),
            limit=limit
        )

    def get_winners(self, limit: int = 100) -> list[JournalEntry]:
        """Get profitable trades."""
        return self.db.query(
            where="pnl_usd > 0 AND status != 'open'",
            params=(),
            order_by="pnl_usd DESC",
            limit=limit
        )

    def get_losers(self, limit: int = 100) -> list[JournalEntry]:
        """Get losing trades."""
        return self.db.query(
            where="pnl_usd < 0 AND status != 'open'",
            params=(),
            order_by="pnl_usd ASC",
            limit=limit
        )

    def get_by_market_regime(self, regime: str, limit: int = 100) -> list[JournalEntry]:
        """Get entries that occurred in a specific market regime."""
        return self.db.query(
            where="market_regime = ?",
            params=(regime,),
            limit=limit
        )

    def get_early_exits(self, min_missed_profit: float = 1.0, limit: int = 100) -> list[JournalEntry]:
        """Get trades where we exited too early (missed significant profit)."""
        return self.db.query(
            where="missed_profit_usd > ? AND status = 'post_tracked'",
            params=(min_missed_profit,),
            order_by="missed_profit_usd DESC",
            limit=limit
        )

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self,
                  coin: Optional[str] = None,
                  strategy_id: Optional[str] = None,
                  hours: Optional[int] = None) -> dict:
        """
        Get performance statistics.

        Args:
            coin: Filter by coin
            strategy_id: Filter by strategy
            hours: Only include trades from last N hours

        Returns:
            Dict with trade counts, win rate, P&L stats, etc.
        """
        where_parts = ["status != 'open'"]
        params = []

        if coin:
            where_parts.append("coin = ?")
            params.append(coin.upper())

        if strategy_id:
            where_parts.append("strategy_id = ?")
            params.append(strategy_id)

        if hours:
            cutoff = datetime.now() - timedelta(hours=hours)
            where_parts.append("entry_time >= ?")
            params.append(cutoff.isoformat())

        where = " AND ".join(where_parts)

        # Get aggregate stats
        result = self.db.aggregate(
            select="""
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN pnl_usd <= 0 THEN 1 ELSE 0 END) as losses,
                SUM(pnl_usd) as total_pnl,
                AVG(pnl_usd) as avg_pnl,
                MAX(pnl_usd) as best_trade,
                MIN(pnl_usd) as worst_trade,
                AVG(duration_seconds) as avg_duration,
                AVG(ABS(pnl_pct)) as avg_move_pct
            """,
            where=where,
            params=tuple(params)
        )

        if not result:
            return self._empty_stats()

        stats = result[0]
        total = stats['total_trades'] or 0
        wins = stats['wins'] or 0

        return {
            'total_trades': total,
            'wins': wins,
            'losses': stats['losses'] or 0,
            'win_rate': (wins / total * 100) if total > 0 else 0,
            'total_pnl': stats['total_pnl'] or 0,
            'avg_pnl': stats['avg_pnl'] or 0,
            'best_trade': stats['best_trade'] or 0,
            'worst_trade': stats['worst_trade'] or 0,
            'avg_duration_seconds': stats['avg_duration'] or 0,
            'avg_move_pct': stats['avg_move_pct'] or 0,
        }

    def _empty_stats(self) -> dict:
        """Return empty stats dict."""
        return {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'avg_pnl': 0,
            'best_trade': 0,
            'worst_trade': 0,
            'avg_duration_seconds': 0,
            'avg_move_pct': 0,
        }

    def get_performance_by_hour(self) -> dict[int, dict]:
        """
        Get performance broken down by hour of day.

        Returns:
            Dict mapping hour (0-23) to stats dict
        """
        results = self.db.aggregate(
            select="""
                hour_of_day,
                COUNT(*) as trades,
                SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
                SUM(pnl_usd) as total_pnl,
                AVG(pnl_usd) as avg_pnl
            """,
            where="status != 'open'",
            group_by="hour_of_day"
        )

        return {
            r['hour_of_day']: {
                'trades': r['trades'],
                'wins': r['wins'],
                'win_rate': (r['wins'] / r['trades'] * 100) if r['trades'] > 0 else 0,
                'total_pnl': r['total_pnl'] or 0,
                'avg_pnl': r['avg_pnl'] or 0,
            }
            for r in results if r['hour_of_day'] is not None
        }

    def get_performance_by_day(self) -> dict[int, dict]:
        """
        Get performance broken down by day of week.

        Returns:
            Dict mapping day (0=Mon, 6=Sun) to stats dict
        """
        results = self.db.aggregate(
            select="""
                day_of_week,
                COUNT(*) as trades,
                SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
                SUM(pnl_usd) as total_pnl,
                AVG(pnl_usd) as avg_pnl
            """,
            where="status != 'open'",
            group_by="day_of_week"
        )

        return {
            r['day_of_week']: {
                'trades': r['trades'],
                'wins': r['wins'],
                'win_rate': (r['wins'] / r['trades'] * 100) if r['trades'] > 0 else 0,
                'total_pnl': r['total_pnl'] or 0,
                'avg_pnl': r['avg_pnl'] or 0,
            }
            for r in results if r['day_of_week'] is not None
        }

    def get_performance_by_coin(self) -> dict[str, dict]:
        """
        Get performance broken down by coin.

        Returns:
            Dict mapping coin symbol to stats dict
        """
        results = self.db.aggregate(
            select="""
                coin,
                COUNT(*) as trades,
                SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
                SUM(pnl_usd) as total_pnl,
                AVG(pnl_usd) as avg_pnl
            """,
            where="status != 'open'",
            group_by="coin"
        )

        return {
            r['coin']: {
                'trades': r['trades'],
                'wins': r['wins'],
                'win_rate': (r['wins'] / r['trades'] * 100) if r['trades'] > 0 else 0,
                'total_pnl': r['total_pnl'] or 0,
                'avg_pnl': r['avg_pnl'] or 0,
            }
            for r in results if r['coin'] is not None
        }

    def get_performance_by_exit_reason(self) -> dict[str, dict]:
        """
        Get performance broken down by exit reason.

        Returns:
            Dict mapping exit reason to stats dict
        """
        results = self.db.aggregate(
            select="""
                exit_reason,
                COUNT(*) as trades,
                SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
                SUM(pnl_usd) as total_pnl,
                AVG(pnl_usd) as avg_pnl
            """,
            where="status != 'open' AND exit_reason IS NOT NULL",
            group_by="exit_reason"
        )

        return {
            r['exit_reason']: {
                'trades': r['trades'],
                'wins': r['wins'],
                'win_rate': (r['wins'] / r['trades'] * 100) if r['trades'] > 0 else 0,
                'total_pnl': r['total_pnl'] or 0,
                'avg_pnl': r['avg_pnl'] or 0,
            }
            for r in results if r['exit_reason'] is not None
        }

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def stop(self) -> None:
        """Stop async operations and flush writes."""
        # Cancel post-trade tasks
        for task in self._post_trade_tasks.values():
            task.cancel()
        self._post_trade_tasks.clear()

        # Stop write queue
        if self._write_queue:
            self._write_queue.stop()

        logger.info("Trade Journal stopped")

    def get_open_entries(self) -> list[JournalEntry]:
        """Get all open (pending) entries."""
        return list(self.pending_entries.values())

    def entry_count(self) -> int:
        """Get total number of journal entries."""
        return self.db.count()
