"""TradeCondition dataclass for Strategist output."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal, Optional
import uuid


@dataclass
class TradeCondition:
    """A specific condition for Sniper to watch and execute.

    The Strategist generates these conditions based on market analysis.
    The Sniper watches for the trigger conditions and executes when met.

    Attributes:
        coin: The coin symbol (e.g., "SOL", "ETH")
        direction: Trade direction - LONG (buy) or SHORT (sell)
        trigger_price: Price that triggers entry
        trigger_condition: ABOVE for breakout, BELOW for dip buy
        stop_loss_pct: Stop loss as percentage (e.g., 2.0 for 2%)
        take_profit_pct: Take profit as percentage (e.g., 1.5 for 1.5%)
        position_size_usd: Position size in USD (e.g., 50.0)
        reasoning: Why this trade was suggested (for logging/learning)
        strategy_id: Which strategy/pattern generated this condition
        id: Unique identifier (auto-generated)
        created_at: When the condition was created
        valid_until: When the condition expires (default: 5 minutes)
        additional_filters: Optional extra filters (e.g., volume, CVD)

    Example:
        >>> condition = TradeCondition(
        ...     coin="SOL",
        ...     direction="LONG",
        ...     trigger_price=143.50,
        ...     trigger_condition="ABOVE",
        ...     stop_loss_pct=2.0,
        ...     take_profit_pct=1.5,
        ...     position_size_usd=50.0,
        ...     reasoning="Momentum breakout above resistance",
        ...     strategy_id="momentum_breakout"
        ... )
        >>> condition.is_expired()
        False
    """

    coin: str
    direction: Literal["LONG", "SHORT"]
    trigger_price: float
    trigger_condition: Literal["ABOVE", "BELOW"]
    stop_loss_pct: float
    take_profit_pct: float
    position_size_usd: float
    reasoning: str
    strategy_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=datetime.now)
    valid_until: datetime = field(
        default_factory=lambda: datetime.now() + timedelta(minutes=5)
    )
    additional_filters: Optional[dict] = None

    def is_expired(self) -> bool:
        """Check if this condition has expired.

        Returns:
            True if current time is past valid_until.
        """
        return datetime.now() > self.valid_until

    def is_triggered(self, current_price: float) -> bool:
        """Check if the trigger condition is met.

        Args:
            current_price: Current market price for this coin.

        Returns:
            True if the condition is triggered.
        """
        if self.trigger_condition == "ABOVE":
            return current_price >= self.trigger_price
        else:  # BELOW
            return current_price <= self.trigger_price

    def calculate_stop_loss_price(self) -> float:
        """Calculate the stop loss price based on trigger price and percentage.

        Returns:
            Stop loss price in USD.
        """
        if self.direction == "LONG":
            return self.trigger_price * (1 - self.stop_loss_pct / 100)
        else:  # SHORT
            return self.trigger_price * (1 + self.stop_loss_pct / 100)

    def calculate_take_profit_price(self) -> float:
        """Calculate the take profit price based on trigger price and percentage.

        Returns:
            Take profit price in USD.
        """
        if self.direction == "LONG":
            return self.trigger_price * (1 + self.take_profit_pct / 100)
        else:  # SHORT
            return self.trigger_price * (1 - self.take_profit_pct / 100)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the condition.
        """
        return {
            "id": self.id,
            "coin": self.coin,
            "direction": self.direction,
            "trigger_price": self.trigger_price,
            "trigger_condition": self.trigger_condition,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "position_size_usd": self.position_size_usd,
            "reasoning": self.reasoning,
            "strategy_id": self.strategy_id,
            "created_at": self.created_at.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "additional_filters": self.additional_filters,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TradeCondition":
        """Create TradeCondition from dictionary.

        Args:
            data: Dictionary with condition fields.

        Returns:
            New TradeCondition instance.
        """
        # Parse datetime strings if present
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.now()

        valid_until = data.get("valid_until")
        if isinstance(valid_until, str):
            valid_until = datetime.fromisoformat(valid_until)
        else:
            valid_until = datetime.now() + timedelta(minutes=5)

        return cls(
            coin=data["coin"],
            direction=data["direction"],
            trigger_price=float(data["trigger_price"]),
            trigger_condition=data["trigger_condition"],
            stop_loss_pct=float(data["stop_loss_pct"]),
            take_profit_pct=float(data["take_profit_pct"]),
            position_size_usd=float(data["position_size_usd"]),
            reasoning=data.get("reasoning", ""),
            strategy_id=data.get("strategy_id", "unknown"),
            id=data.get("id", str(uuid.uuid4())[:8]),
            created_at=created_at,
            valid_until=valid_until,
            additional_filters=data.get("additional_filters"),
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"{self.direction} {self.coin} if {self.trigger_condition} "
            f"${self.trigger_price:,.2f} | SL: {self.stop_loss_pct}% | "
            f"TP: {self.take_profit_pct}% | Size: ${self.position_size_usd}"
        )
