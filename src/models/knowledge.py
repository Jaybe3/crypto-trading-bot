"""Knowledge Brain data models for accumulated trading wisdom."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any
import json


@dataclass
class CoinScore:
    """Performance metrics for a specific coin.

    Tracks win/loss statistics, P&L, and trend to help the Strategist
    make informed decisions about which coins to trade.
    """
    coin: str                           # "SOL", "ETH", etc.
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    avg_pnl: float = 0.0
    win_rate: float = 0.0
    avg_winner: float = 0.0             # Average profit on winning trades
    avg_loser: float = 0.0              # Average loss on losing trades
    is_blacklisted: bool = False
    blacklist_reason: str = ""
    last_updated: Optional[datetime] = None
    trend: str = "stable"               # "improving", "degrading", "stable"

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        data = asdict(self)
        if isinstance(data["last_updated"], datetime):
            data["last_updated"] = data["last_updated"].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CoinScore":
        """Create from database row dictionary."""
        if data.get("last_updated") and isinstance(data["last_updated"], str):
            data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        return cls(**data)

    def recalculate_stats(self) -> None:
        """Recalculate derived statistics after trade updates."""
        if self.total_trades > 0:
            self.win_rate = self.wins / self.total_trades
            self.avg_pnl = self.total_pnl / self.total_trades


@dataclass
class TradingPattern:
    """A reusable trading pattern with effectiveness tracking.

    Patterns describe entry/exit conditions that can be identified
    and tracked across multiple trades.
    """
    pattern_id: str
    description: str                    # "Long on pullback to support in uptrend"
    entry_conditions: Dict[str, Any]    # JSON-serializable conditions
    exit_conditions: Dict[str, Any]     # JSON-serializable conditions
    times_used: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    confidence: float = 0.5             # 0-1, how much we trust this pattern
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_used: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    @property
    def win_rate(self) -> float:
        """Calculate win rate for this pattern."""
        if self.times_used == 0:
            return 0.0
        return self.wins / self.times_used

    @property
    def avg_pnl(self) -> float:
        """Calculate average P&L per use."""
        if self.times_used == 0:
            return 0.0
        return self.total_pnl / self.times_used

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "pattern_id": self.pattern_id,
            "description": self.description,
            "entry_conditions": json.dumps(self.entry_conditions),
            "exit_conditions": json.dumps(self.exit_conditions),
            "times_used": self.times_used,
            "wins": self.wins,
            "losses": self.losses,
            "total_pnl": self.total_pnl,
            "confidence": self.confidence,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TradingPattern":
        """Create from database row dictionary."""
        # Parse JSON strings
        if isinstance(data.get("entry_conditions"), str):
            data["entry_conditions"] = json.loads(data["entry_conditions"])
        if isinstance(data.get("exit_conditions"), str):
            data["exit_conditions"] = json.loads(data["exit_conditions"])
        # Parse timestamps
        if data.get("created_at") and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("last_used") and isinstance(data["last_used"], str):
            data["last_used"] = datetime.fromisoformat(data["last_used"])
        return cls(**data)


@dataclass
class RegimeRule:
    """A rule about when to trade or sit out.

    Regime rules capture learned market conditions that affect
    trading decisions (e.g., "Don't trade when BTC volatility < 1%").
    """
    rule_id: str
    description: str                    # "Don't trade when BTC volatility < 1%"
    condition: Dict[str, Any]           # JSON-serializable condition
    action: str                         # "NO_TRADE", "REDUCE_SIZE", "INCREASE_SIZE"
    times_triggered: int = 0
    estimated_saves: float = 0.0        # P&L saved by following this rule
    is_active: bool = True
    created_at: Optional[datetime] = None

    # Valid actions
    VALID_ACTIONS = ["NO_TRADE", "REDUCE_SIZE", "INCREASE_SIZE", "CAUTION"]

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.action not in self.VALID_ACTIONS:
            raise ValueError(f"Invalid action: {self.action}. Must be one of {self.VALID_ACTIONS}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "condition": json.dumps(self.condition),
            "action": self.action,
            "times_triggered": self.times_triggered,
            "estimated_saves": self.estimated_saves,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegimeRule":
        """Create from database row dictionary."""
        # Parse JSON string
        if isinstance(data.get("condition"), str):
            data["condition"] = json.loads(data["condition"])
        # Parse timestamp
        if data.get("created_at") and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)

    def check_condition(self, market_state: Dict[str, Any]) -> bool:
        """Check if this rule's condition is met by current market state.

        Args:
            market_state: Dictionary of current market conditions.

        Returns:
            True if the rule condition is satisfied.
        """
        # Simple condition checking - can be extended
        for key, requirement in self.condition.items():
            if key not in market_state:
                continue

            value = market_state[key]

            # Handle comparison operators in requirement
            if isinstance(requirement, dict):
                op = requirement.get("op", "eq")
                target = requirement.get("value")

                if op == "lt" and not (value < target):
                    return False
                elif op == "gt" and not (value > target):
                    return False
                elif op == "lte" and not (value <= target):
                    return False
                elif op == "gte" and not (value >= target):
                    return False
                elif op == "eq" and not (value == target):
                    return False
                elif op == "neq" and not (value != target):
                    return False
            else:
                # Direct equality check
                if value != requirement:
                    return False

        return True
