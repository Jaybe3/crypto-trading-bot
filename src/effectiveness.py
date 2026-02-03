"""
Effectiveness Monitor - Tracks whether adaptations actually improve performance.

TASK-142: Measures adaptation effectiveness by comparing pre/post metrics
and flags harmful adaptations for rollback.

This closes the learning feedback loop: Adapt → Measure → Validate/Rollback
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.adaptation import AdaptationEngine
    from src.database import Database
    from src.journal import TradeJournal
    from src.knowledge import KnowledgeBrain
    from src.profitability import ProfitabilityTracker

logger = logging.getLogger(__name__)


class EffectivenessRating(Enum):
    """Rating for adaptation effectiveness."""
    HIGHLY_EFFECTIVE = "highly_effective"  # Significantly improved metrics
    EFFECTIVE = "effective"                 # Moderately improved metrics
    NEUTRAL = "neutral"                     # No significant change
    INEFFECTIVE = "ineffective"             # Made things worse
    HARMFUL = "harmful"                     # Significantly worse, consider rollback
    PENDING = "pending"                     # Not enough data yet


@dataclass
class EffectivenessResult:
    """Result of effectiveness measurement."""
    adaptation_id: str
    rating: EffectivenessRating

    # Pre/post comparison
    pre_metrics: Dict[str, Any]
    post_metrics: Dict[str, Any]

    # Key changes
    win_rate_change: float = 0.0       # Percentage points (+5 means 50% -> 55%)
    pnl_change: float = 0.0            # Dollar change
    profit_factor_change: float = 0.0  # Change in profit factor

    # Context
    trades_measured: int = 0           # Trades since adaptation
    hours_elapsed: float = 0.0         # Hours since adaptation

    # Recommendation
    should_rollback: bool = False
    rollback_reason: Optional[str] = None

    measured_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "adaptation_id": self.adaptation_id,
            "rating": self.rating.value,
            "pre_metrics": self.pre_metrics,
            "post_metrics": self.post_metrics,
            "win_rate_change": self.win_rate_change,
            "pnl_change": self.pnl_change,
            "profit_factor_change": self.profit_factor_change,
            "trades_measured": self.trades_measured,
            "hours_elapsed": self.hours_elapsed,
            "should_rollback": self.should_rollback,
            "rollback_reason": self.rollback_reason,
            "measured_at": self.measured_at.isoformat(),
        }


class EffectivenessMonitor:
    """Monitors adaptation effectiveness and flags harmful changes.

    Flow:
    1. AdaptationEngine applies adaptation, records pre_metrics
    2. EffectivenessMonitor runs periodically
    3. For each unmeasured adaptation older than MIN_HOURS:
       - Calculate post_metrics
       - Compare to pre_metrics
       - Assign effectiveness rating
       - Flag for rollback if harmful

    Example:
        >>> monitor = EffectivenessMonitor(db, journal, profitability, adaptation_engine, knowledge)
        >>> results = monitor.check_pending_adaptations()
        >>> for r in results:
        ...     print(f"{r.adaptation_id}: {r.rating.value}")
    """

    # Measurement thresholds
    MIN_TRADES_FOR_MEASUREMENT = 10     # At least 10 trades after adaptation
    MIN_HOURS_FOR_MEASUREMENT = 24      # At least 24 hours after adaptation
    MAX_HOURS_FOR_MEASUREMENT = 168     # Measure within 7 days

    # Effectiveness thresholds (percentage points for win rate)
    HIGHLY_EFFECTIVE_THRESHOLD = 10.0   # +10% win rate
    EFFECTIVE_THRESHOLD = 3.0           # +3% win rate
    INEFFECTIVE_THRESHOLD = -3.0        # -3% win rate
    HARMFUL_THRESHOLD = -10.0           # -10% win rate

    # Rollback thresholds
    ROLLBACK_MIN_PNL_LOSS = 20.0        # Must lose at least $20 to rollback
    ROLLBACK_MIN_TRADES = 10            # Must have at least 10 trades

    def __init__(
        self,
        db: "Database",
        journal: "TradeJournal",
        profitability: "ProfitabilityTracker",
        adaptation_engine: "AdaptationEngine",
        knowledge: "KnowledgeBrain",
    ):
        """Initialize EffectivenessMonitor.

        Args:
            db: Database for persistence.
            journal: TradeJournal for trade data.
            profitability: ProfitabilityTracker for metrics.
            adaptation_engine: AdaptationEngine for rollback coordination.
            knowledge: KnowledgeBrain for rollback actions.
        """
        self.db = db
        self.journal = journal
        self.profitability = profitability
        self.adaptation_engine = adaptation_engine
        self.knowledge = knowledge

        # Stats
        self._last_check: Optional[datetime] = None
        self._measurements_completed = 0
        self._rollbacks_executed = 0
        self._rollbacks_flagged = 0

        logger.info("EffectivenessMonitor initialized")

    def check_pending_adaptations(self) -> List[EffectivenessResult]:
        """Check all unmeasured adaptations that are ready for measurement.

        Returns:
            List of effectiveness results for newly measured adaptations.
        """
        self._last_check = datetime.now()
        results = []

        # Get adaptations that haven't been measured yet
        pending = self.get_pending_measurements()

        for adaptation in pending:
            result = self.measure_adaptation(adaptation["adaptation_id"])
            if result:
                results.append(result)

                # Log significant results
                if result.rating == EffectivenessRating.HARMFUL:
                    logger.warning(
                        f"HARMFUL adaptation detected: {adaptation['adaptation_id']} "
                        f"({adaptation['action']} {adaptation['target']}) - "
                        f"Win rate: {result.win_rate_change:+.1f}%, "
                        f"P&L: ${result.pnl_change:+.2f}"
                    )
                    if result.should_rollback:
                        self._rollbacks_flagged += 1
                elif result.rating == EffectivenessRating.HIGHLY_EFFECTIVE:
                    logger.info(
                        f"HIGHLY EFFECTIVE adaptation: {adaptation['adaptation_id']} "
                        f"({adaptation['action']} {adaptation['target']}) - "
                        f"Win rate: {result.win_rate_change:+.1f}%, "
                        f"P&L: ${result.pnl_change:+.2f}"
                    )

        if results:
            logger.info(f"Measured {len(results)} adaptations")

        return results

    def measure_adaptation(self, adaptation_id: str) -> Optional[EffectivenessResult]:
        """Measure effectiveness of a specific adaptation.

        Args:
            adaptation_id: ID of adaptation to measure.

        Returns:
            EffectivenessResult or None if not ready.
        """
        # Get adaptation from database
        adaptations = self.db.get_adaptations(hours=self.MAX_HOURS_FOR_MEASUREMENT, limit=1000)
        adaptation = next((a for a in adaptations if a["adaptation_id"] == adaptation_id), None)

        if not adaptation:
            logger.debug(f"Adaptation {adaptation_id} not found")
            return None

        # Check if already measured
        if adaptation.get("effectiveness"):
            logger.debug(f"Adaptation {adaptation_id} already measured")
            return None

        # Parse pre-metrics
        pre_metrics = adaptation.get("pre_metrics", {})
        if isinstance(pre_metrics, str):
            try:
                pre_metrics = json.loads(pre_metrics)
            except json.JSONDecodeError:
                pre_metrics = {}

        if not pre_metrics:
            logger.debug(f"No pre-metrics for adaptation {adaptation_id}")
            return None

        # Check if enough time has passed
        adaptation_time = self._parse_timestamp(adaptation.get("timestamp"))
        if not adaptation_time:
            return None

        hours_elapsed = (datetime.now() - adaptation_time).total_seconds() / 3600

        if hours_elapsed < self.MIN_HOURS_FOR_MEASUREMENT:
            logger.debug(
                f"Adaptation {adaptation_id} too recent: "
                f"{hours_elapsed:.1f}h < {self.MIN_HOURS_FOR_MEASUREMENT}h"
            )
            return None

        # Capture post-metrics
        post_metrics = self._capture_post_metrics(adaptation_time)

        # Check if enough trades
        trades_measured = post_metrics.get("trades_measured", 0)
        if trades_measured < self.MIN_TRADES_FOR_MEASUREMENT:
            logger.debug(
                f"Adaptation {adaptation_id} not enough trades: "
                f"{trades_measured} < {self.MIN_TRADES_FOR_MEASUREMENT}"
            )
            # Still record if max hours exceeded
            if hours_elapsed < self.MAX_HOURS_FOR_MEASUREMENT:
                return None

        # Calculate effectiveness
        result = self._calculate_effectiveness(
            adaptation_id=adaptation_id,
            pre_metrics=pre_metrics,
            post_metrics=post_metrics,
            hours_elapsed=hours_elapsed,
            trades_measured=trades_measured,
        )

        # Save to database
        self._save_effectiveness(adaptation_id, result)
        self._measurements_completed += 1

        return result

    def _capture_post_metrics(self, since: datetime) -> Dict[str, Any]:
        """Capture post-adaptation metrics.

        Args:
            since: Timestamp of adaptation.

        Returns:
            Dict with post-adaptation metrics.
        """
        hours_since = (datetime.now() - since).total_seconds() / 3600

        # Get trades since adaptation
        trades = self.journal.get_recent(
            hours=int(hours_since) + 1,
            status="closed",
            limit=10000,
        )

        # Filter to only trades after adaptation
        trades_after = [
            t for t in trades
            if t.exit_time and t.exit_time > since
        ]

        # Calculate metrics
        if trades_after:
            metrics = self.profitability.calculate_metrics(trades_after)
        else:
            metrics = {
                "total_trades": 0,
                "winning_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "profit_factor": 0.0,
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "hours_since_adaptation": hours_since,
            "trades_measured": len(trades_after),
            "overall": {
                "total_trades": metrics.get("total_trades", 0),
                "winning_trades": metrics.get("winning_trades", 0),
                "win_rate": metrics.get("win_rate", 0.0),
                "total_pnl": metrics.get("total_pnl", 0.0),
                "profit_factor": metrics.get("profit_factor", 0.0),
            }
        }

    def _calculate_effectiveness(
        self,
        adaptation_id: str,
        pre_metrics: Dict[str, Any],
        post_metrics: Dict[str, Any],
        hours_elapsed: float,
        trades_measured: int,
    ) -> EffectivenessResult:
        """Compare pre/post metrics and assign rating.

        Args:
            adaptation_id: ID of adaptation.
            pre_metrics: Metrics before adaptation.
            post_metrics: Metrics after adaptation.
            hours_elapsed: Hours since adaptation.
            trades_measured: Number of trades since adaptation.

        Returns:
            EffectivenessResult with rating and recommendation.
        """
        # Extract metrics
        pre_overall = pre_metrics.get("overall", pre_metrics)
        post_overall = post_metrics.get("overall", post_metrics)

        pre_win_rate = pre_overall.get("win_rate", 0.0)
        post_win_rate = post_overall.get("win_rate", 0.0)

        pre_pnl = pre_overall.get("total_pnl", 0.0)
        post_pnl = post_overall.get("total_pnl", 0.0)

        pre_pf = pre_overall.get("profit_factor", 0.0)
        post_pf = post_overall.get("profit_factor", 0.0)

        # Calculate changes
        win_rate_change = post_win_rate - pre_win_rate
        pnl_change = post_pnl - pre_pnl
        pf_change = post_pf - pre_pf

        # Assign rating based on win rate change
        if win_rate_change >= self.HIGHLY_EFFECTIVE_THRESHOLD:
            rating = EffectivenessRating.HIGHLY_EFFECTIVE
        elif win_rate_change >= self.EFFECTIVE_THRESHOLD:
            rating = EffectivenessRating.EFFECTIVE
        elif win_rate_change >= self.INEFFECTIVE_THRESHOLD:
            rating = EffectivenessRating.NEUTRAL
        elif win_rate_change >= self.HARMFUL_THRESHOLD:
            rating = EffectivenessRating.INEFFECTIVE
        else:
            rating = EffectivenessRating.HARMFUL

        # Determine if rollback needed
        should_rollback = (
            rating == EffectivenessRating.HARMFUL and
            pnl_change < -self.ROLLBACK_MIN_PNL_LOSS and
            trades_measured >= self.ROLLBACK_MIN_TRADES
        )

        rollback_reason = None
        if should_rollback:
            rollback_reason = (
                f"Win rate dropped {abs(win_rate_change):.1f}% and "
                f"lost ${abs(pnl_change):.2f} over {trades_measured} trades"
            )

        return EffectivenessResult(
            adaptation_id=adaptation_id,
            rating=rating,
            pre_metrics=pre_metrics,
            post_metrics=post_metrics,
            win_rate_change=win_rate_change,
            pnl_change=pnl_change,
            profit_factor_change=pf_change,
            trades_measured=trades_measured,
            hours_elapsed=hours_elapsed,
            should_rollback=should_rollback,
            rollback_reason=rollback_reason,
            measured_at=datetime.now(),
        )

    def _save_effectiveness(self, adaptation_id: str, result: EffectivenessResult) -> None:
        """Save effectiveness measurement to database.

        Args:
            adaptation_id: ID of adaptation.
            result: Effectiveness result.
        """
        try:
            self.db.update_adaptation_effectiveness(
                adaptation_id=adaptation_id,
                post_metrics=json.dumps(result.post_metrics),
                effectiveness=result.rating.value,
                effectiveness_measured_at=result.measured_at,
            )
            logger.debug(f"Saved effectiveness for {adaptation_id}: {result.rating.value}")
        except Exception as e:
            logger.error(f"Failed to save effectiveness: {e}")

    def _parse_timestamp(self, ts: Any) -> Optional[datetime]:
        """Parse timestamp from various formats."""
        if ts is None:
            return None
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                try:
                    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return None
        return None

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_pending_measurements(self) -> List[Dict[str, Any]]:
        """Get adaptations pending measurement.

        Returns:
            List of adaptations that haven't been measured yet.
        """
        adaptations = self.db.get_adaptations(
            hours=self.MAX_HOURS_FOR_MEASUREMENT,
            limit=1000,
        )

        # Filter to unmeasured, old enough
        pending = []
        for a in adaptations:
            if a.get("effectiveness"):
                continue  # Already measured

            ts = self._parse_timestamp(a.get("timestamp"))
            if not ts:
                continue

            hours_elapsed = (datetime.now() - ts).total_seconds() / 3600
            if hours_elapsed >= self.MIN_HOURS_FOR_MEASUREMENT:
                pending.append(a)

        return pending

    def get_harmful_adaptations(self, hours: int = 168) -> List[Dict[str, Any]]:
        """Get adaptations flagged as harmful in time period.

        Args:
            hours: Hours to look back.

        Returns:
            List of harmful adaptations.
        """
        return self.db.get_adaptations_by_effectiveness(
            effectiveness=EffectivenessRating.HARMFUL.value,
            hours=hours,
        )

    def get_effectiveness_summary(self) -> Dict[str, Any]:
        """Get summary of adaptation effectiveness.

        Returns:
            Summary dict with counts by rating.
        """
        adaptations = self.db.get_adaptations(hours=self.MAX_HOURS_FOR_MEASUREMENT, limit=1000)

        summary = {
            "total": len(adaptations),
            "total_measured": 0,
            "highly_effective": 0,
            "effective": 0,
            "neutral": 0,
            "ineffective": 0,
            "harmful": 0,
            "pending": 0,
            "rollbacks_flagged": self._rollbacks_flagged,
            "rollbacks_executed": self._rollbacks_executed,
        }

        for a in adaptations:
            effectiveness = a.get("effectiveness")
            if not effectiveness:
                summary["pending"] += 1
            else:
                summary["total_measured"] += 1
                if effectiveness in summary:
                    summary[effectiveness] += 1

        return summary

    # =========================================================================
    # Rollback Methods
    # =========================================================================

    def suggest_rollback(self, adaptation_id: str) -> Dict[str, Any]:
        """Get rollback suggestion for an adaptation.

        Args:
            adaptation_id: ID of adaptation.

        Returns:
            Dict with rollback suggestion.
        """
        adaptations = self.db.get_adaptations(hours=self.MAX_HOURS_FOR_MEASUREMENT, limit=1000)
        adaptation = next((a for a in adaptations if a["adaptation_id"] == adaptation_id), None)

        if not adaptation:
            return {"error": "Adaptation not found"}

        action = adaptation.get("action", "")
        target = adaptation.get("target", "")

        rollback_actions = {
            "blacklist": f"Unblacklist coin {target}",
            "favor": f"Remove favor status from {target}",
            "create_time_rule": f"Deactivate rule {target}",
            "create_regime_rule": f"Deactivate rule {target}",
            "deactivate_pattern": f"Reactivate pattern {target}",
        }

        rollback_action = None
        for key, description in rollback_actions.items():
            if key in action.lower():
                rollback_action = description
                break

        return {
            "adaptation_id": adaptation_id,
            "action": action,
            "target": target,
            "effectiveness": adaptation.get("effectiveness"),
            "rollback_action": rollback_action or "Unknown rollback action",
            "can_rollback": rollback_action is not None,
        }

    def execute_rollback(self, adaptation_id: str) -> bool:
        """Execute rollback of a harmful adaptation.

        Args:
            adaptation_id: ID of adaptation to rollback.

        Returns:
            True if rollback successful.
        """
        adaptations = self.db.get_adaptations(hours=self.MAX_HOURS_FOR_MEASUREMENT, limit=1000)
        adaptation = next((a for a in adaptations if a["adaptation_id"] == adaptation_id), None)

        if not adaptation:
            logger.error(f"Adaptation {adaptation_id} not found for rollback")
            return False

        action = adaptation.get("action", "").lower()
        target = adaptation.get("target", "")

        success = False

        try:
            if "blacklist" in action:
                # Unblacklist coin
                if self.knowledge:
                    self.knowledge.unblacklist_coin(target)
                    success = True
                    logger.info(f"Rollback: Unblacklisted {target}")

            elif "favor" in action:
                # Remove favor status (set trend to stable)
                if self.knowledge:
                    score = self.knowledge.get_coin_score(target)
                    if score:
                        score.trend = "stable"
                        self.knowledge.db.save_coin_score(score.to_dict())
                        success = True
                        logger.info(f"Rollback: Removed favor from {target}")

            elif "time_rule" in action or "regime_rule" in action:
                # Deactivate rule
                if self.knowledge:
                    self.knowledge.deactivate_rule(target)
                    success = True
                    logger.info(f"Rollback: Deactivated rule {target}")

            elif "deactivate_pattern" in action:
                # Reactivate pattern
                if self.knowledge:
                    self.knowledge.reactivate_pattern(target)
                    success = True
                    logger.info(f"Rollback: Reactivated pattern {target}")

            else:
                logger.warning(f"Unknown adaptation action for rollback: {action}")

            if success:
                self._rollbacks_executed += 1
                # Log the rollback
                self.db.log_activity(
                    activity_type="rollback",
                    description=f"Rolled back adaptation {adaptation_id}",
                    details=json.dumps({
                        "adaptation_id": adaptation_id,
                        "action": action,
                        "target": target,
                    }),
                )

        except Exception as e:
            logger.error(f"Rollback failed for {adaptation_id}: {e}")
            success = False

        return success

    # =========================================================================
    # Health Check
    # =========================================================================

    def get_health(self) -> Dict[str, Any]:
        """Get component health status.

        Returns:
            Dict with status, metrics.
        """
        status = "healthy"

        # Check dependencies
        if not self.journal or not self.profitability:
            status = "degraded"

        return {
            "status": status,
            "last_activity": self._last_check.isoformat() if self._last_check else None,
            "error_count": 0,
            "metrics": {
                "measurements_completed": self._measurements_completed,
                "rollbacks_flagged": self._rollbacks_flagged,
                "rollbacks_executed": self._rollbacks_executed,
                "has_journal": self.journal is not None,
                "has_profitability": self.profitability is not None,
            }
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics.

        Returns:
            Stats dictionary.
        """
        return {
            "measurements_completed": self._measurements_completed,
            "rollbacks_flagged": self._rollbacks_flagged,
            "rollbacks_executed": self._rollbacks_executed,
            "last_check": self._last_check.isoformat() if self._last_check else None,
        }
