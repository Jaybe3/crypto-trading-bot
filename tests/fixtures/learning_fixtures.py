"""
Test fixtures for learning validation.

Provides helpers for creating trades, simulating outcomes,
and setting up test scenarios for learning validation.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class MockTrade:
    """Mock trade for testing learning components."""
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    coin: str = "BTC"
    direction: str = "long"
    entry_price: float = 50000.0
    exit_price: float = 50500.0
    size: float = 0.01
    pnl: float = 5.0
    pnl_pct: float = 1.0
    outcome: str = "win"  # "win" or "loss"
    pattern: Optional[str] = None
    strategy: Optional[str] = None
    entry_time: datetime = field(default_factory=datetime.now)
    exit_time: datetime = field(default_factory=datetime.now)
    exit_reason: str = "take_profit"
    duration_seconds: int = 300

    def to_dict(self) -> dict:
        """Convert to dictionary format expected by components."""
        return {
            "trade_id": self.trade_id,
            "coin": self.coin,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "size": self.size,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "outcome": self.outcome,
            "pattern": self.pattern,
            "strategy": self.strategy,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat(),
            "exit_reason": self.exit_reason,
            "duration_seconds": self.duration_seconds,
        }


def create_trade(
    coin: str = "BTC",
    pnl: float = 10.0,
    outcome: str = None,
    pattern: str = None,
    strategy: str = None,
    timestamp: datetime = None,
    direction: str = "long",
    exit_reason: str = None,
    entry_price: float = None,
    size: float = 0.01,
) -> MockTrade:
    """
    Create a mock trade for testing.

    Args:
        coin: Coin symbol
        pnl: Profit/loss in dollars
        outcome: "win" or "loss" (auto-determined from pnl if not specified)
        pattern: Pattern used for trade
        strategy: Strategy name
        timestamp: Trade timestamp (defaults to now)
        direction: "long" or "short"
        exit_reason: Reason for exit
        entry_price: Entry price (auto-generated if not specified)
        size: Position size

    Returns:
        MockTrade instance
    """
    if outcome is None:
        outcome = "win" if pnl >= 0 else "loss"

    if timestamp is None:
        timestamp = datetime.now()

    if entry_price is None:
        entry_price = {
            "BTC": 67000.0,
            "ETH": 3400.0,
            "SOL": 140.0,
            "AVAX": 35.0,
            "LINK": 15.0,
            "DOGE": 0.08,
            "XRP": 0.55,
            "ADA": 0.45,
            "DOT": 7.0,
            "MATIC": 0.85,
        }.get(coin, 100.0)

    if exit_reason is None:
        exit_reason = "take_profit" if outcome == "win" else "stop_loss"

    # Calculate exit price from pnl
    pnl_pct = (pnl / (entry_price * size)) * 100 if entry_price * size > 0 else 0
    if direction == "long":
        exit_price = entry_price * (1 + pnl_pct / 100)
    else:
        exit_price = entry_price * (1 - pnl_pct / 100)

    return MockTrade(
        coin=coin,
        direction=direction,
        entry_price=entry_price,
        exit_price=exit_price,
        size=size,
        pnl=pnl,
        pnl_pct=pnl_pct,
        outcome=outcome,
        pattern=pattern,
        strategy=strategy,
        entry_time=timestamp - timedelta(minutes=5),
        exit_time=timestamp,
        exit_reason=exit_reason,
    )


def make_timestamp(hour: int, days_ago: int = 0, minute: int = 0) -> datetime:
    """
    Create a timestamp at a specific hour.

    Args:
        hour: Hour of day (0-23)
        days_ago: Days in the past (0 = today)
        minute: Minute of hour (0-59)

    Returns:
        datetime at specified time
    """
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    target = target - timedelta(days=days_ago)
    return target


def create_winning_streak(
    coin: str,
    count: int,
    avg_pnl: float = 20.0,
    pattern: str = None,
) -> list[MockTrade]:
    """
    Create a streak of winning trades.

    Args:
        coin: Coin symbol
        count: Number of trades
        avg_pnl: Average P&L per trade
        pattern: Pattern to use

    Returns:
        List of winning MockTrade instances
    """
    trades = []
    for i in range(count):
        # Vary P&L slightly
        pnl = avg_pnl * (0.8 + 0.4 * (i % 3) / 2)
        timestamp = datetime.now() - timedelta(hours=count - i)
        trades.append(create_trade(
            coin=coin,
            pnl=pnl,
            outcome="win",
            pattern=pattern,
            timestamp=timestamp,
        ))
    return trades


def create_losing_streak(
    coin: str,
    count: int,
    avg_pnl: float = -15.0,
    pattern: str = None,
) -> list[MockTrade]:
    """
    Create a streak of losing trades.

    Args:
        coin: Coin symbol
        count: Number of trades
        avg_pnl: Average P&L per trade (negative)
        pattern: Pattern to use

    Returns:
        List of losing MockTrade instances
    """
    trades = []
    for i in range(count):
        # Vary P&L slightly
        pnl = avg_pnl * (0.8 + 0.4 * (i % 3) / 2)
        timestamp = datetime.now() - timedelta(hours=count - i)
        trades.append(create_trade(
            coin=coin,
            pnl=pnl,
            outcome="loss",
            pattern=pattern,
            timestamp=timestamp,
        ))
    return trades


def create_mixed_trades(
    coin: str,
    win_count: int,
    loss_count: int,
    win_pnl: float = 25.0,
    loss_pnl: float = -15.0,
    pattern: str = None,
) -> list[MockTrade]:
    """
    Create a mix of winning and losing trades.

    Args:
        coin: Coin symbol
        win_count: Number of winning trades
        loss_count: Number of losing trades
        win_pnl: Average winning P&L
        loss_pnl: Average losing P&L
        pattern: Pattern to use

    Returns:
        List of MockTrade instances (interleaved wins and losses)
    """
    trades = []
    total = win_count + loss_count
    wins_remaining = win_count
    losses_remaining = loss_count

    for i in range(total):
        timestamp = datetime.now() - timedelta(hours=total - i)

        # Distribute wins and losses roughly evenly
        if wins_remaining > 0 and (losses_remaining == 0 or i % 2 == 0):
            trades.append(create_trade(
                coin=coin,
                pnl=win_pnl,
                outcome="win",
                pattern=pattern,
                timestamp=timestamp,
            ))
            wins_remaining -= 1
        else:
            trades.append(create_trade(
                coin=coin,
                pnl=loss_pnl,
                outcome="loss",
                pattern=pattern,
                timestamp=timestamp,
            ))
            losses_remaining -= 1

    return trades


def create_hourly_trades(
    coin: str,
    hour: int,
    count: int,
    win_rate: float = 0.5,
    avg_win: float = 20.0,
    avg_loss: float = -15.0,
) -> list[MockTrade]:
    """
    Create trades at a specific hour for time-based testing.

    Args:
        coin: Coin symbol
        hour: Hour of day (0-23)
        count: Number of trades
        win_rate: Fraction of trades that win
        avg_win: Average winning P&L
        avg_loss: Average losing P&L

    Returns:
        List of MockTrade instances at specified hour
    """
    trades = []
    win_count = int(count * win_rate)

    for i in range(count):
        days_ago = i // 3  # Spread over multiple days
        timestamp = make_timestamp(hour=hour, days_ago=days_ago)

        if i < win_count:
            trades.append(create_trade(
                coin=coin,
                pnl=avg_win,
                outcome="win",
                timestamp=timestamp,
            ))
        else:
            trades.append(create_trade(
                coin=coin,
                pnl=avg_loss,
                outcome="loss",
                timestamp=timestamp,
            ))

    return trades


class LearningTestContext:
    """
    Context manager for learning validation tests.

    Sets up and tears down test state for isolated testing.
    """

    def __init__(self, db=None, knowledge=None, coin_scorer=None,
                 pattern_library=None, quick_update=None):
        self.db = db
        self.knowledge = knowledge
        self.coin_scorer = coin_scorer
        self.pattern_library = pattern_library
        self.quick_update = quick_update
        self._initial_state = {}

    def __enter__(self):
        """Save initial state."""
        if self.knowledge:
            self._initial_state["blacklist"] = list(self.knowledge.get_blacklist())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore initial state (optional cleanup)."""
        pass

    def process_trades(self, trades: list[MockTrade]) -> None:
        """Process a list of trades through the learning system."""
        if not self.quick_update:
            raise RuntimeError("quick_update not configured")

        for trade in trades:
            self.quick_update.process_trade(trade.to_dict())

    def get_coin_score(self, coin: str) -> float:
        """Get current score for a coin."""
        if self.coin_scorer:
            return self.coin_scorer.get_score(coin) or 50.0
        return 50.0

    def is_blacklisted(self, coin: str) -> bool:
        """Check if coin is blacklisted."""
        if self.knowledge:
            return self.knowledge.is_blacklisted(coin)
        return False
