"""
Quick Update data models.

TASK-130: Data classes for post-trade quick updates.
"""

from dataclasses import dataclass, field
from typing import Optional

from src.calculations import calculate_return_pct


@dataclass
class TradeResult:
    """Outcome of a completed trade, passed to QuickUpdate.

    Contains all information needed to update coin scores and pattern confidence.
    """

    trade_id: str
    coin: str
    direction: str  # LONG or SHORT
    entry_price: float
    exit_price: float
    position_size_usd: float
    pnl_usd: float
    won: bool  # pnl_usd > 0
    exit_reason: str  # stop_loss, take_profit, manual

    # Optional context
    pattern_id: Optional[str] = None  # Pattern used, if any
    strategy_id: Optional[str] = None  # Strategy that generated condition
    condition_id: Optional[str] = None

    # Timing
    entry_timestamp: int = 0
    exit_timestamp: int = 0

    # Market context at exit
    btc_price: Optional[float] = None
    btc_trend: Optional[str] = None

    @property
    def duration_seconds(self) -> int:
        """Calculate trade duration in seconds."""
        if self.exit_timestamp and self.entry_timestamp:
            return (self.exit_timestamp - self.entry_timestamp) // 1000
        return 0

    @property
    def return_pct(self) -> float:
        """Calculate return percentage."""
        return calculate_return_pct(self.entry_price, self.exit_price, self.direction)


@dataclass
class QuickUpdateResult:
    """Result of a quick update, including any adaptations triggered.

    Returned by QuickUpdate.process_trade_close() to inform caller
    of what changed.
    """

    trade_id: str
    coin: str
    won: bool
    pnl_usd: float

    # What was updated
    coin_score_updated: bool = True
    pattern_updated: bool = False
    pattern_id: Optional[str] = None

    # Adaptations triggered
    coin_adaptation: Optional[str] = None  # "BLACKLIST", "REDUCE", "FAVOR", None
    coin_adaptation_reason: Optional[str] = None
    pattern_deactivated: bool = False

    # New coin status after update
    new_coin_status: str = "normal"
    new_coin_win_rate: float = 0.0
    new_coin_total_trades: int = 0

    # Pattern stats after update (if applicable)
    new_pattern_confidence: Optional[float] = None

    # Processing time
    processing_time_ms: float = 0.0

    def __str__(self) -> str:
        """Human-readable summary."""
        result = "WIN" if self.won else "LOSS"
        parts = [f"{self.coin} {result} ${self.pnl_usd:+.2f}"]

        if self.coin_adaptation:
            parts.append(f"-> {self.coin_adaptation}")

        if self.pattern_deactivated:
            parts.append(f"[pattern {self.pattern_id} deactivated]")

        parts.append(f"({self.processing_time_ms:.1f}ms)")

        return " ".join(parts)
