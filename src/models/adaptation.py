"""
Adaptation data models.

TASK-133: Data classes for tracking adaptations applied from insights.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class AdaptationAction(Enum):
    """Types of adaptations that can be applied."""

    BLACKLIST_COIN = "blacklist"
    FAVOR_COIN = "favor"
    REDUCE_COIN = "reduce"
    DEACTIVATE_PATTERN = "deactivate_pattern"
    BOOST_PATTERN = "boost_pattern"
    CREATE_TIME_RULE = "create_time_rule"
    CREATE_REGIME_RULE = "create_regime_rule"
    NO_ACTION = "no_action"


@dataclass
class AdaptationRecord:
    """Record of an adaptation applied from an insight.

    Tracks what was changed, when, why, and captures pre-metrics
    for later effectiveness measurement.
    """

    adaptation_id: str
    timestamp: datetime
    insight_type: str  # coin, pattern, time, regime
    insight_title: str

    # What was done
    action: str  # AdaptationAction value
    target: str  # Coin symbol, pattern_id, or rule_id
    description: str  # Human-readable description

    # Pre-adaptation metrics
    pre_metrics: Dict[str, Any] = field(default_factory=dict)

    # Insight details
    insight_confidence: float = 0.0
    insight_evidence: Dict[str, Any] = field(default_factory=dict)
    auto_applied: bool = True  # True if automatic, False if manual

    # Post-adaptation tracking (filled later)
    post_metrics: Optional[Dict[str, Any]] = None
    effectiveness: Optional[str] = None  # "improved", "no_change", "degraded"
    effectiveness_measured_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "adaptation_id": self.adaptation_id,
            "timestamp": self.timestamp.isoformat(),
            "insight_type": self.insight_type,
            "insight_title": self.insight_title,
            "action": self.action,
            "target": self.target,
            "description": self.description,
            "pre_metrics": self.pre_metrics,
            "insight_confidence": self.insight_confidence,
            "insight_evidence": self.insight_evidence,
            "auto_applied": self.auto_applied,
            "post_metrics": self.post_metrics,
            "effectiveness": self.effectiveness,
            "effectiveness_measured_at": (
                self.effectiveness_measured_at.isoformat()
                if self.effectiveness_measured_at
                else None
            ),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AdaptationRecord":
        """Create from dictionary."""
        return cls(
            adaptation_id=d["adaptation_id"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
            insight_type=d.get("insight_type", "unknown"),
            insight_title=d.get("insight_title", ""),
            action=d["action"],
            target=d["target"],
            description=d["description"],
            pre_metrics=d.get("pre_metrics", {}),
            insight_confidence=d.get("insight_confidence", 0.0),
            insight_evidence=d.get("insight_evidence", {}),
            auto_applied=d.get("auto_applied", True),
            post_metrics=d.get("post_metrics"),
            effectiveness=d.get("effectiveness"),
            effectiveness_measured_at=(
                datetime.fromisoformat(d["effectiveness_measured_at"])
                if d.get("effectiveness_measured_at")
                else None
            ),
        )

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"[{self.action}] {self.target}: {self.description}"
