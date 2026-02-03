"""
Sniper Execution Engine - Fast trade execution without LLM in the path.

Receives conditions from Strategist, watches real-time prices from MarketFeed,
executes instantly when conditions trigger, manages stop-loss and take-profit.

Key constraint: on_price_tick must complete in < 1ms. No I/O in the hot path.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal, Optional

from src.journal import TradeJournal
from src.market_feed import PriceTick
from src.models.trade_condition import TradeCondition

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """
    An open position being managed by the Sniper.

    Tracks entry, current state, and exit targets (stop-loss, take-profit).
    """
    id: str
    coin: str
    direction: Literal["LONG", "SHORT"]
    entry_price: float
    entry_time: datetime
    size_usd: float
    stop_loss_price: float                          # Absolute price for stop
    take_profit_price: float                        # Absolute price for TP
    condition_id: str                               # Which condition triggered this
    strategy_id: str
    reasoning: str
    current_price: float = 0.0                      # Updated on each tick
    unrealized_pnl: float = 0.0                     # Updated on each tick

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        d = asdict(self)
        d['entry_time'] = self.entry_time.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'Position':
        """Create from dictionary."""
        d['entry_time'] = datetime.fromisoformat(d['entry_time'])
        return cls(**d)


@dataclass
class ExecutionEvent:
    """Event emitted when a trade is executed."""
    event_type: Literal["entry", "exit"]
    position_id: str
    coin: str
    direction: str
    price: float
    size_usd: float
    timestamp: int
    reason: Optional[str] = None                    # For exits: stop_loss, take_profit, manual
    pnl: Optional[float] = None                     # For exits


class Sniper:
    """
    Fast execution engine for paper trading.

    Receives conditions from Strategist, monitors prices from MarketFeed,
    executes trades instantly when conditions trigger.

    Key Features:
    - No LLM in the execution path
    - Sub-millisecond tick processing
    - Automatic stop-loss and take-profit management
    - Risk limits enforcement
    - State persistence for restart recovery

    Usage:
        journal = TradeJournal()
        sniper = Sniper(journal, initial_balance=10000.0)

        # Connect to market feed
        feed.subscribe_price(sniper.on_price_tick)

        # Set conditions (from Strategist)
        sniper.set_conditions([condition1, condition2])

        # Sniper automatically executes when conditions trigger
    """

    # Risk Limits
    MAX_POSITIONS = 5           # Maximum concurrent positions
    MAX_PER_COIN = 1            # Maximum positions per coin
    MAX_EXPOSURE_PCT = 0.10     # Maximum % of balance at risk

    # State persistence
    DEFAULT_STATE_PATH = "data/sniper_state.json"

    def __init__(
        self,
        journal: TradeJournal,
        initial_balance: float = 10000.0,
        state_path: Optional[str] = None,
        coin_scorer=None,
        quick_update=None,
    ):
        """
        Initialize the Sniper.

        Args:
            journal: TradeJournal for recording executions
            initial_balance: Starting paper trading balance in USD
            state_path: Path for state persistence (None = default)
            coin_scorer: Optional CoinScorer for tracking coin performance (deprecated, use quick_update)
            quick_update: Optional QuickUpdate for post-trade knowledge updates
        """
        self.journal = journal
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.state_path = Path(state_path) if state_path else Path(self.DEFAULT_STATE_PATH)
        self.coin_scorer = coin_scorer  # Deprecated: use quick_update instead
        self.quick_update = quick_update  # TASK-130: for post-trade updates

        # Core state
        self.active_conditions: dict[str, TradeCondition] = {}
        self.open_positions: dict[str, Position] = {}

        # Tracking
        self.total_pnl = 0.0
        self.trades_executed = 0
        self.last_tick_time: Optional[int] = None

        # Callbacks for execution events
        self._callbacks: list[Callable[[ExecutionEvent], None]] = []

        # Performance tracking
        self._tick_count = 0
        self._total_tick_time = 0.0

    # =========================================================================
    # Condition Management
    # =========================================================================

    def set_conditions(self, conditions: list[TradeCondition]) -> int:
        """
        Replace all active conditions with new ones.

        Called by Strategist to update the active condition set.
        Expired conditions are automatically filtered out.

        Args:
            conditions: New conditions to set

        Returns:
            Number of active conditions after setting
        """
        now = datetime.now()
        self.active_conditions = {
            c.id: c for c in conditions
            if c.valid_until > now
        }

        logger.info(f"Set {len(self.active_conditions)} active conditions")
        return len(self.active_conditions)

    def add_condition(self, condition: TradeCondition) -> bool:
        """
        Add a single condition.

        Args:
            condition: Condition to add

        Returns:
            True if added, False if expired or duplicate
        """
        if condition.is_expired():
            logger.debug(f"Condition {condition.id} already expired, not adding")
            return False

        if condition.id in self.active_conditions:
            logger.debug(f"Condition {condition.id} already exists, updating")

        self.active_conditions[condition.id] = condition
        logger.info(
            f"Added condition: {condition.direction} {condition.coin} "
            f"{'>' if condition.trigger_condition == 'ABOVE' else '<'} "
            f"${condition.trigger_price:.2f}"
        )
        return True

    def remove_condition(self, condition_id: str) -> bool:
        """
        Remove a condition by ID.

        Args:
            condition_id: ID of condition to remove

        Returns:
            True if removed, False if not found
        """
        if condition_id in self.active_conditions:
            del self.active_conditions[condition_id]
            return True
        return False

    def clear_conditions(self, coin: Optional[str] = None) -> int:
        """
        Clear conditions, optionally filtered by coin.

        Args:
            coin: If provided, only clear conditions for this coin

        Returns:
            Number of conditions cleared
        """
        if coin is None:
            count = len(self.active_conditions)
            self.active_conditions.clear()
            return count

        coin = coin.upper()
        to_remove = [cid for cid, c in self.active_conditions.items() if c.coin == coin]
        for cid in to_remove:
            del self.active_conditions[cid]
        return len(to_remove)

    def get_conditions(self, coin: Optional[str] = None) -> list[TradeCondition]:
        """
        Get active conditions, optionally filtered by coin.

        Args:
            coin: If provided, only return conditions for this coin

        Returns:
            List of active conditions
        """
        conditions = list(self.active_conditions.values())
        if coin:
            coin = coin.upper()
            conditions = [c for c in conditions if c.coin == coin]
        return conditions

    # =========================================================================
    # Price Tick Handler (HOT PATH - must be < 1ms)
    # =========================================================================

    def on_price_tick(self, tick: PriceTick) -> None:
        """
        Handle a price tick from MarketFeed.

        THIS IS THE HOT PATH - MUST BE FAST (< 1ms).
        No I/O, no async operations, no heavy computations.

        Args:
            tick: Price tick from MarketFeed
        """
        start = time.perf_counter()

        coin = tick.coin.upper()
        price = tick.price
        timestamp = tick.timestamp

        self.last_tick_time = timestamp

        # Clean up expired conditions (cheap operation)
        self._cleanup_expired_conditions()

        # Check entry conditions for this coin
        self._check_entry_conditions(coin, price, timestamp)

        # Check exit conditions for open positions
        self._check_exit_conditions(coin, price, timestamp)

        # Track performance
        elapsed = time.perf_counter() - start
        self._tick_count += 1
        self._total_tick_time += elapsed

    def _cleanup_expired_conditions(self) -> None:
        """Remove expired conditions. Called on each tick."""
        now = datetime.now()
        expired = [
            cid for cid, c in self.active_conditions.items()
            if c.valid_until <= now
        ]
        for cid in expired:
            logger.debug(f"Condition {cid} expired")
            del self.active_conditions[cid]

    # =========================================================================
    # Entry Logic
    # =========================================================================

    def _check_entry_conditions(self, coin: str, price: float, timestamp: int) -> None:
        """
        Check if any condition triggers an entry for this coin.

        Args:
            coin: Coin symbol
            price: Current price
            timestamp: Tick timestamp
        """
        # Get conditions for this coin
        conditions = [c for c in self.active_conditions.values() if c.coin == coin]

        for condition in conditions:
            if self._is_triggered(condition, price):
                if self._can_open_position(condition):
                    self._execute_entry(condition, price, timestamp)

    def _is_triggered(self, condition: TradeCondition, price: float) -> bool:
        """
        Check if a condition is triggered by the current price.

        Args:
            condition: The condition to check
            price: Current price

        Returns:
            True if triggered
        """
        if condition.trigger_condition == "ABOVE":
            return price >= condition.trigger_price
        else:  # BELOW
            return price <= condition.trigger_price

    def _can_open_position(self, condition: TradeCondition) -> bool:
        """
        Check if we can open a new position (risk limits).

        Args:
            condition: The condition that would open the position

        Returns:
            True if allowed, False if risk limit hit
        """
        # Check max positions
        if len(self.open_positions) >= self.MAX_POSITIONS:
            logger.warning(f"Max positions ({self.MAX_POSITIONS}) reached, skipping entry")
            return False

        # Check max per coin
        coin_positions = [p for p in self.open_positions.values() if p.coin == condition.coin]
        if len(coin_positions) >= self.MAX_PER_COIN:
            logger.warning(f"Max positions for {condition.coin} reached, skipping entry")
            return False

        # Check max exposure
        current_exposure = sum(p.size_usd for p in self.open_positions.values())
        new_exposure = current_exposure + condition.position_size_usd
        max_exposure = self.balance * self.MAX_EXPOSURE_PCT

        if new_exposure > max_exposure:
            logger.warning(
                f"Exposure limit exceeded: ${new_exposure:.2f} > ${max_exposure:.2f}"
            )
            return False

        # Check sufficient balance
        if condition.position_size_usd > self.balance:
            logger.warning(
                f"Insufficient balance: ${condition.position_size_usd:.2f} > ${self.balance:.2f}"
            )
            return False

        return True

    def _execute_entry(self, condition: TradeCondition, price: float, timestamp: int) -> None:
        """
        Execute an entry (open a position).

        Args:
            condition: The triggered condition
            price: Entry price
            timestamp: Entry timestamp
        """
        # Calculate stop-loss and take-profit prices
        stop_loss_price = self._calc_stop_loss_price(price, condition)
        take_profit_price = self._calc_take_profit_price(price, condition)

        # Create position
        position = Position(
            id=self._generate_id("pos"),
            coin=condition.coin,
            direction=condition.direction,
            entry_price=price,
            entry_time=datetime.fromtimestamp(timestamp / 1000),
            size_usd=condition.position_size_usd,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            condition_id=condition.id,
            strategy_id=condition.strategy_id,
            reasoning=condition.reasoning,
            current_price=price,
            unrealized_pnl=0.0,
        )

        # Add to open positions
        self.open_positions[position.id] = position

        # Remove consumed condition
        del self.active_conditions[condition.id]

        # Update balance (reserve funds)
        self.balance -= condition.position_size_usd

        # Increment trade counter
        self.trades_executed += 1

        # Log to journal
        self.journal.record_entry(position, timestamp)

        # Emit event
        self._emit_event(ExecutionEvent(
            event_type="entry",
            position_id=position.id,
            coin=position.coin,
            direction=position.direction,
            price=price,
            size_usd=position.size_usd,
            timestamp=timestamp,
        ))

        logger.info(
            f"ENTRY: {position.direction} {position.coin} @ ${price:.2f} "
            f"(SL: ${stop_loss_price:.2f}, TP: ${take_profit_price:.2f})"
        )

    def _calc_stop_loss_price(self, entry_price: float, condition: TradeCondition) -> float:
        """Calculate absolute stop-loss price.

        Note: stop_loss_pct is in percentage form (e.g., 2.0 = 2%), not decimal.
        """
        if condition.direction == "LONG":
            return entry_price * (1 - condition.stop_loss_pct / 100)
        else:  # SHORT
            return entry_price * (1 + condition.stop_loss_pct / 100)

    def _calc_take_profit_price(self, entry_price: float, condition: TradeCondition) -> float:
        """Calculate absolute take-profit price.

        Note: take_profit_pct is in percentage form (e.g., 1.5 = 1.5%), not decimal.
        """
        if condition.direction == "LONG":
            return entry_price * (1 + condition.take_profit_pct / 100)
        else:  # SHORT
            return entry_price * (1 - condition.take_profit_pct / 100)

    # =========================================================================
    # Exit Logic
    # =========================================================================

    def _check_exit_conditions(self, coin: str, price: float, timestamp: int) -> None:
        """
        Check if any open position should be closed.

        Args:
            coin: Coin symbol
            price: Current price
            timestamp: Tick timestamp
        """
        # Get positions for this coin (use list() to allow modification during iteration)
        positions = [p for p in list(self.open_positions.values()) if p.coin == coin]

        for position in positions:
            # Update current price and unrealized PnL
            position.current_price = price
            position.unrealized_pnl = self._calc_pnl(position, price)

            # Check exit conditions
            if self._hit_stop_loss(position, price):
                self._execute_exit(position, price, timestamp, "stop_loss")
            elif self._hit_take_profit(position, price):
                self._execute_exit(position, price, timestamp, "take_profit")

    def _hit_stop_loss(self, position: Position, price: float) -> bool:
        """Check if stop-loss is hit."""
        if position.direction == "LONG":
            return price <= position.stop_loss_price
        else:  # SHORT
            return price >= position.stop_loss_price

    def _hit_take_profit(self, position: Position, price: float) -> bool:
        """Check if take-profit is hit."""
        if position.direction == "LONG":
            return price >= position.take_profit_price
        else:  # SHORT
            return price <= position.take_profit_price

    def _calc_pnl(self, position: Position, current_price: float) -> float:
        """
        Calculate P&L for a position at current price.

        Args:
            position: The position
            current_price: Current market price

        Returns:
            P&L in USD (positive = profit, negative = loss)
        """
        price_change_pct = (current_price - position.entry_price) / position.entry_price

        if position.direction == "SHORT":
            price_change_pct = -price_change_pct

        return position.size_usd * price_change_pct

    def _execute_exit(
        self,
        position: Position,
        price: float,
        timestamp: int,
        reason: str
    ) -> None:
        """
        Execute an exit (close a position).

        Args:
            position: The position to close
            price: Exit price
            timestamp: Exit timestamp
            reason: Why exiting ("stop_loss", "take_profit", "manual")
        """
        # Calculate final PnL
        pnl = self._calc_pnl(position, price)

        # Update balance (return funds + PnL)
        self.balance += position.size_usd + pnl

        # Update total PnL
        self.total_pnl += pnl

        # Remove from open positions
        del self.open_positions[position.id]

        # Log to journal
        self.journal.record_exit(position, price, timestamp, reason, pnl)

        # TASK-130: Quick update for post-trade knowledge updates
        if self.quick_update:
            from src.models.quick_update import TradeResult

            trade_result = TradeResult(
                trade_id=position.id,
                coin=position.coin,
                direction=position.direction,
                entry_price=position.entry_price,
                exit_price=price,
                position_size_usd=position.size_usd,
                pnl_usd=pnl,
                won=pnl > 0,
                exit_reason=reason,
                strategy_id=position.strategy_id,
                condition_id=position.condition_id,
                entry_timestamp=int(position.entry_time.timestamp() * 1000),
                exit_timestamp=timestamp,
            )

            update_result = self.quick_update.process_trade_close(trade_result)

            if update_result.coin_adaptation:
                logger.info(
                    f"ADAPTATION: {position.coin} -> {update_result.coin_adaptation} "
                    f"({update_result.coin_adaptation_reason})"
                )
            if update_result.pattern_deactivated:
                logger.info(f"PATTERN DEACTIVATED: {update_result.pattern_id}")

        # Fallback: Update coin score directly (deprecated, for backward compatibility)
        elif self.coin_scorer:
            trade_data = {
                "coin": position.coin,
                "pnl_usd": pnl,
                "direction": position.direction,
                "exit_reason": reason,
            }
            adaptation = self.coin_scorer.process_trade_result(trade_data)
            if adaptation:
                logger.info(f"ADAPTATION: {adaptation.coin} -> {adaptation.new_status.value}")

        # Emit event
        self._emit_event(ExecutionEvent(
            event_type="exit",
            position_id=position.id,
            coin=position.coin,
            direction=position.direction,
            price=price,
            size_usd=position.size_usd,
            timestamp=timestamp,
            reason=reason,
            pnl=pnl,
        ))

        pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
        logger.info(f"EXIT: {position.coin} @ ${price:.2f} [{reason}] {pnl_str}")

    # =========================================================================
    # Position Management
    # =========================================================================

    def get_positions(self) -> list[Position]:
        """Get all open positions."""
        return list(self.open_positions.values())

    def get_position(self, coin: str) -> Optional[Position]:
        """
        Get open position for a coin (if any).

        Args:
            coin: Coin symbol

        Returns:
            Position or None
        """
        coin = coin.upper()
        for position in self.open_positions.values():
            if position.coin == coin:
                return position
        return None

    def close_position(self, position_id: str, price: float, timestamp: Optional[int] = None) -> bool:
        """
        Manually close a position.

        Args:
            position_id: ID of position to close
            price: Exit price
            timestamp: Optional timestamp (defaults to now)

        Returns:
            True if closed, False if not found
        """
        if position_id not in self.open_positions:
            return False

        position = self.open_positions[position_id]
        ts = timestamp or int(time.time() * 1000)

        self._execute_exit(position, price, ts, "manual")
        return True

    def close_all_positions(self, prices: dict[str, float]) -> int:
        """
        Close all open positions.

        Args:
            prices: Dict of coin -> current price

        Returns:
            Number of positions closed
        """
        closed = 0
        timestamp = int(time.time() * 1000)

        for position in list(self.open_positions.values()):
            price = prices.get(position.coin)
            if price:
                self._execute_exit(position, price, timestamp, "manual")
                closed += 1

        return closed

    # =========================================================================
    # State & Stats
    # =========================================================================

    def get_status(self) -> dict:
        """Get current Sniper status."""
        avg_tick_time = (
            self._total_tick_time / self._tick_count * 1000
            if self._tick_count > 0 else 0
        )

        return {
            "balance": self.balance,
            "initial_balance": self.initial_balance,
            "total_pnl": self.total_pnl,
            "total_pnl_pct": (self.total_pnl / self.initial_balance) * 100,
            "trades_executed": self.trades_executed,
            "open_positions": len(self.open_positions),
            "active_conditions": len(self.active_conditions),
            "tick_count": self._tick_count,
            "avg_tick_time_ms": avg_tick_time,
            "last_tick_time": self.last_tick_time,
        }

    def get_exposure(self) -> dict:
        """Get current exposure information."""
        position_exposure = sum(p.size_usd for p in self.open_positions.values())
        max_exposure = self.balance * self.MAX_EXPOSURE_PCT

        return {
            "current_exposure_usd": position_exposure,
            "max_exposure_usd": max_exposure,
            "exposure_pct": (position_exposure / self.balance) * 100 if self.balance > 0 else 0,
            "available_usd": max_exposure - position_exposure,
        }

    def get_health(self) -> dict:
        """Get component health status for monitoring.

        Returns:
            Dict with status (healthy/degraded/failed), last_activity, error_count, metrics.
        """
        now = time.time()

        # Check if processing ticks
        tick_age = now - self.last_tick_time if self.last_tick_time else None

        # Determine health status
        if tick_age is None:
            status = "degraded"  # Never received a tick
        elif tick_age > 10:
            status = "degraded"  # Haven't processed ticks recently
        else:
            status = "healthy"

        # Check for stuck positions (positions with extreme unrealized loss)
        stuck_positions = [
            p for p in self.open_positions.values()
            if p.unrealized_pnl < -p.size_usd * 0.1  # >10% loss
        ]
        if stuck_positions:
            status = "degraded"

        avg_tick_time = (
            self._total_tick_time / self._tick_count * 1000
            if self._tick_count > 0 else 0
        )

        return {
            "status": status,
            "last_activity": datetime.fromtimestamp(
                self.last_tick_time
            ).isoformat() if self.last_tick_time else None,
            "error_count": 0,  # No explicit error tracking yet
            "metrics": {
                "balance": self.balance,
                "total_pnl": self.total_pnl,
                "trades_executed": self.trades_executed,
                "open_positions": len(self.open_positions),
                "active_conditions": len(self.active_conditions),
                "tick_count": self._tick_count,
                "avg_tick_time_ms": round(avg_tick_time, 4),
                "tick_age_seconds": round(tick_age, 2) if tick_age else None,
            }
        }

    # =========================================================================
    # Persistence
    # =========================================================================

    def save_state(self, path: Optional[str] = None) -> None:
        """
        Save current state to file for restart recovery.

        Args:
            path: Optional path override
        """
        save_path = Path(path if path else self.state_path)

        # Ensure directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "balance": self.balance,
            "initial_balance": self.initial_balance,
            "total_pnl": self.total_pnl,
            "trades_executed": self.trades_executed,
            "conditions": [c.to_dict() for c in self.active_conditions.values()],
            "positions": [p.to_dict() for p in self.open_positions.values()],
            "saved_at": datetime.now().isoformat(),
        }

        save_path.write_text(json.dumps(state, indent=2))
        logger.info(f"Saved state to {save_path}")

    def load_state(self, path: Optional[str] = None) -> bool:
        """
        Load state from file.

        Args:
            path: Optional path override

        Returns:
            True if loaded successfully, False if file not found
        """
        load_path = Path(path if path else self.state_path)

        if not load_path.exists():
            logger.info(f"No state file found at {load_path}")
            return False

        try:
            state = json.loads(load_path.read_text())

            self.balance = state["balance"]
            self.initial_balance = state["initial_balance"]
            self.total_pnl = state["total_pnl"]
            self.trades_executed = state["trades_executed"]

            # Load conditions (filter expired)
            self.active_conditions = {}
            for c_dict in state.get("conditions", []):
                condition = TradeCondition.from_dict(c_dict)
                if not condition.is_expired():
                    self.active_conditions[condition.id] = condition

            # Load positions
            self.open_positions = {}
            for p_dict in state.get("positions", []):
                position = Position.from_dict(p_dict)
                self.open_positions[position.id] = position

            logger.info(
                f"Loaded state: {len(self.active_conditions)} conditions, "
                f"{len(self.open_positions)} positions"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return False

    # =========================================================================
    # Callbacks
    # =========================================================================

    def subscribe(self, callback: Callable[[ExecutionEvent], None]) -> None:
        """
        Subscribe to execution events.

        Args:
            callback: Function called on each entry/exit
        """
        self._callbacks.append(callback)

    def _emit_event(self, event: ExecutionEvent) -> None:
        """Emit an execution event to all subscribers."""
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    # =========================================================================
    # Utilities
    # =========================================================================

    def _generate_id(self, prefix: str = "id") -> str:
        """Generate a unique ID."""
        return f"{prefix}-{uuid.uuid4().hex[:8]}"
