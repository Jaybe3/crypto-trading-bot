"""
Reflection data models.

TASK-131: Data classes for Deep Reflection analysis and insights.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.adaptation import AdaptationRecord


@dataclass
class CoinAnalysis:
    """Performance analysis for a single coin."""

    coin: str
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    avg_winner: float
    avg_loser: float
    best_trade: float
    worst_trade: float
    trend: str  # "improving", "declining", "stable"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coin": self.coin,
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": self.win_rate,
            "total_pnl": self.total_pnl,
            "avg_pnl": self.avg_pnl,
            "avg_winner": self.avg_winner,
            "avg_loser": self.avg_loser,
            "best_trade": self.best_trade,
            "worst_trade": self.worst_trade,
            "trend": self.trend,
        }


@dataclass
class PatternAnalysis:
    """Performance analysis for a pattern/strategy."""

    pattern_id: str
    description: str
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "description": self.description,
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": self.win_rate,
            "total_pnl": self.total_pnl,
            "avg_pnl": self.avg_pnl,
            "confidence": self.confidence,
        }


@dataclass
class TimeAnalysis:
    """Performance analysis by time of day and day of week."""

    # By hour (0-23)
    best_hours: List[int]
    worst_hours: List[int]
    hour_win_rates: Dict[int, float]
    hour_trade_counts: Dict[int, int]

    # By day (0-6, Mon-Sun)
    best_days: List[int]
    worst_days: List[int]
    day_win_rates: Dict[int, float]
    day_trade_counts: Dict[int, int]

    # Weekend performance
    weekend_trades: int
    weekend_win_rate: float
    weekday_win_rate: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "best_hours": self.best_hours,
            "worst_hours": self.worst_hours,
            "hour_win_rates": self.hour_win_rates,
            "hour_trade_counts": self.hour_trade_counts,
            "best_days": self.best_days,
            "worst_days": self.worst_days,
            "day_win_rates": self.day_win_rates,
            "day_trade_counts": self.day_trade_counts,
            "weekend_trades": self.weekend_trades,
            "weekend_win_rate": self.weekend_win_rate,
            "weekday_win_rate": self.weekday_win_rate,
        }


@dataclass
class RegimeAnalysis:
    """Performance analysis by market regime."""

    # BTC trend performance
    btc_up_trades: int
    btc_up_win_rate: float
    btc_up_pnl: float

    btc_down_trades: int
    btc_down_win_rate: float
    btc_down_pnl: float

    btc_sideways_trades: int
    btc_sideways_win_rate: float
    btc_sideways_pnl: float

    # Best/worst
    best_regime: str
    worst_regime: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "btc_up_trades": self.btc_up_trades,
            "btc_up_win_rate": self.btc_up_win_rate,
            "btc_up_pnl": self.btc_up_pnl,
            "btc_down_trades": self.btc_down_trades,
            "btc_down_win_rate": self.btc_down_win_rate,
            "btc_down_pnl": self.btc_down_pnl,
            "btc_sideways_trades": self.btc_sideways_trades,
            "btc_sideways_win_rate": self.btc_sideways_win_rate,
            "btc_sideways_pnl": self.btc_sideways_pnl,
            "best_regime": self.best_regime,
            "worst_regime": self.worst_regime,
        }


@dataclass
class ExitAnalysis:
    """Analysis of exit performance."""

    stop_loss_count: int
    take_profit_count: int
    manual_count: int
    total_exits: int

    stop_loss_rate: float
    take_profit_rate: float

    avg_stop_loss_pnl: float
    avg_take_profit_pnl: float

    # Early exit detection
    early_exits: int  # Trades that would have been more profitable
    avg_missed_profit: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stop_loss_count": self.stop_loss_count,
            "take_profit_count": self.take_profit_count,
            "manual_count": self.manual_count,
            "total_exits": self.total_exits,
            "stop_loss_rate": self.stop_loss_rate,
            "take_profit_rate": self.take_profit_rate,
            "avg_stop_loss_pnl": self.avg_stop_loss_pnl,
            "avg_take_profit_pnl": self.avg_take_profit_pnl,
            "early_exits": self.early_exits,
            "avg_missed_profit": self.avg_missed_profit,
        }


@dataclass
class Insight:
    """A single insight from reflection."""

    insight_type: str  # "coin", "pattern", "time", "regime", "exit", "general"
    category: str  # "opportunity", "problem", "observation"
    title: str
    description: str
    evidence: Dict[str, Any]
    suggested_action: Optional[str] = None
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "insight_type": self.insight_type,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
            "suggested_action": self.suggested_action,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Insight":
        return cls(
            insight_type=d.get("insight_type", "general"),
            category=d.get("category", "observation"),
            title=d.get("title", ""),
            description=d.get("description", ""),
            evidence=d.get("evidence", {}),
            suggested_action=d.get("suggested_action"),
            confidence=d.get("confidence", 0.5),
        )

    def __str__(self) -> str:
        action = f" -> {self.suggested_action}" if self.suggested_action else ""
        return f"[{self.insight_type}:{self.category}] {self.title}{action}"


@dataclass
class ReflectionResult:
    """Complete result of a reflection cycle."""

    timestamp: datetime
    trades_analyzed: int
    period_hours: float

    # Overall performance
    total_pnl: float
    win_rate: float
    wins: int
    losses: int

    # Analyses
    coin_analyses: List[CoinAnalysis]
    pattern_analyses: List[PatternAnalysis]
    time_analysis: Optional[TimeAnalysis]
    regime_analysis: Optional[RegimeAnalysis]
    exit_analysis: Optional[ExitAnalysis]

    # LLM output
    insights: List[Insight]
    summary: str

    # Performance metrics
    analysis_time_ms: float = 0.0
    llm_time_ms: float = 0.0
    total_time_ms: float = 0.0

    # Adaptations applied (TASK-133)
    adaptations: List["AdaptationRecord"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "trades_analyzed": self.trades_analyzed,
            "period_hours": self.period_hours,
            "total_pnl": self.total_pnl,
            "win_rate": self.win_rate,
            "wins": self.wins,
            "losses": self.losses,
            "coin_analyses": [c.to_dict() for c in self.coin_analyses],
            "pattern_analyses": [p.to_dict() for p in self.pattern_analyses],
            "time_analysis": self.time_analysis.to_dict() if self.time_analysis else None,
            "regime_analysis": self.regime_analysis.to_dict() if self.regime_analysis else None,
            "exit_analysis": self.exit_analysis.to_dict() if self.exit_analysis else None,
            "insights": [i.to_dict() for i in self.insights],
            "summary": self.summary,
            "analysis_time_ms": self.analysis_time_ms,
            "llm_time_ms": self.llm_time_ms,
            "total_time_ms": self.total_time_ms,
            "adaptations": [a.to_dict() for a in self.adaptations],
        }

    def __str__(self) -> str:
        adapt_str = f", {len(self.adaptations)} adaptations" if self.adaptations else ""
        return (
            f"Reflection: {self.trades_analyzed} trades, "
            f"{self.win_rate:.0%} win rate, ${self.total_pnl:+.2f} P&L, "
            f"{len(self.insights)} insights{adapt_str} ({self.total_time_ms:.0f}ms)"
        )
