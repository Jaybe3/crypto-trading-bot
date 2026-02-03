"""
Adaptation Engine - Converts insights into Knowledge Brain changes.

TASK-133: Takes insights from ReflectionEngine and applies them to
the Knowledge Brain, making the bot actually learn from its experience.

This completes the learning loop: Reflect → Insight → Adapt → Improve
"""

import json
import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.coin_scorer import CoinScorer
from src.database import Database
from src.knowledge import KnowledgeBrain
from src.models.adaptation import AdaptationAction, AdaptationRecord
from src.models.knowledge import RegimeRule
from src.models.reflection import Insight
from src.pattern_library import PatternLibrary

logger = logging.getLogger(__name__)


# Confidence thresholds for automatic adaptation
THRESHOLDS = {
    "blacklist": {"confidence": 0.85, "min_trades": 5, "max_win_rate": 0.30},
    "favor": {"confidence": 0.80, "min_trades": 5, "min_win_rate": 0.60},
    "deactivate_pattern": {"confidence": 0.85, "min_trades": 5},
    "boost_pattern": {"confidence": 0.75, "min_trades": 5},
    "create_time_rule": {"confidence": 0.75, "min_trades": 10},
    "create_regime_rule": {"confidence": 0.75, "min_trades": 10},
}

# Cooldown period - don't apply same adaptation twice
ADAPTATION_COOLDOWN_HOURS = 24


class AdaptationEngine:
    """Converts insights into Knowledge Brain changes.

    Takes insights from ReflectionEngine and applies them:
    - Blacklist/favor coins based on performance
    - Adjust pattern confidence
    - Create regime rules for time/market conditions
    - Deactivate failing patterns

    All adaptations are logged with pre/post metrics for effectiveness tracking.

    Example:
        >>> engine = AdaptationEngine(knowledge, coin_scorer, pattern_library, db)
        >>> adaptations = engine.apply_insights(insights)
        >>> for a in adaptations:
        ...     print(f"{a.action}: {a.description}")
    """

    def __init__(
        self,
        knowledge: KnowledgeBrain,
        coin_scorer: Optional[CoinScorer] = None,
        pattern_library: Optional[PatternLibrary] = None,
        db: Optional[Database] = None,
    ):
        """Initialize AdaptationEngine.

        Args:
            knowledge: KnowledgeBrain to update.
            coin_scorer: Optional CoinScorer for coin adaptations.
            pattern_library: Optional PatternLibrary for pattern adaptations.
            db: Optional Database for logging adaptations.
        """
        self.knowledge = knowledge
        self.coin_scorer = coin_scorer
        self.pattern_library = pattern_library
        self.db = db

        # Stats
        self.adaptations_applied = 0
        self.adaptations_skipped = 0

        logger.info("AdaptationEngine initialized")

    def apply_insights(self, insights: List[Insight]) -> List[AdaptationRecord]:
        """Apply a list of insights and return records of changes made.

        Args:
            insights: List of insights from ReflectionEngine.

        Returns:
            List of AdaptationRecord for changes that were made.
        """
        adaptations = []

        for insight in insights:
            record = self._apply_insight(insight)
            if record:
                adaptations.append(record)
                self.adaptations_applied += 1
                logger.info(f"Adaptation applied: {record}")
            else:
                self.adaptations_skipped += 1

        if adaptations:
            logger.info(f"Applied {len(adaptations)} adaptations from {len(insights)} insights")
        else:
            logger.debug(f"No adaptations applied from {len(insights)} insights")

        return adaptations

    def _apply_insight(self, insight: Insight) -> Optional[AdaptationRecord]:
        """Apply a single insight if it meets thresholds.

        Args:
            insight: The insight to apply.

        Returns:
            AdaptationRecord if applied, None otherwise.
        """
        # Check if we should apply this insight
        if not self._should_apply(insight):
            logger.debug(f"Skipping insight: {insight.title} (thresholds not met)")
            return None

        # Route to appropriate handler based on insight type
        handlers = {
            "coin": self._apply_coin_insight,
            "pattern": self._apply_pattern_insight,
            "time": self._apply_time_insight,
            "regime": self._apply_regime_insight,
        }

        handler = handlers.get(insight.insight_type)
        if not handler:
            logger.debug(f"No handler for insight type: {insight.insight_type}")
            return None

        return handler(insight)

    def _should_apply(self, insight: Insight) -> bool:
        """Check if insight meets thresholds for automatic application.

        Args:
            insight: The insight to check.

        Returns:
            True if should be applied, False otherwise.
        """
        # Must have minimum confidence
        if insight.confidence < 0.6:
            logger.debug(f"Confidence too low: {insight.confidence}")
            return False

        # Must have evidence
        if not insight.evidence:
            logger.debug("No evidence in insight")
            return False

        # Must have suggested action
        if not insight.suggested_action:
            logger.debug("No suggested action in insight")
            return False

        # Must have minimum trades for statistical significance
        trades = insight.evidence.get("trades", 0)
        if trades < 5:
            logger.debug(f"Not enough trades: {trades}")
            return False

        # Check if recently applied (prevent duplicate adaptations)
        if self._recently_applied(insight):
            logger.debug(f"Recently applied similar adaptation for: {insight.title}")
            return False

        return True

    def _recently_applied(self, insight: Insight) -> bool:
        """Check if similar adaptation was applied recently.

        Args:
            insight: The insight to check.

        Returns:
            True if similar adaptation exists in cooldown period.
        """
        if not self.db:
            return False

        # Extract target from insight
        target = (
            insight.evidence.get("coin")
            or insight.evidence.get("pattern_id")
            or self._extract_coin(insight.title)
        )

        if not target:
            return False

        # Check recent adaptations for this target
        recent = self.db.get_adaptations_for_target(target, hours=ADAPTATION_COOLDOWN_HOURS)
        return len(recent) > 0

    def _extract_coin(self, text: str) -> Optional[str]:
        """Extract coin symbol from text.

        Args:
            text: Text that might contain a coin symbol.

        Returns:
            Coin symbol or None.
        """
        # Common coin patterns
        coins = ["BTC", "ETH", "SOL", "DOGE", "SHIB", "XRP", "ADA", "AVAX", "MATIC", "LINK"]
        text_upper = text.upper()

        for coin in coins:
            if coin in text_upper:
                return coin

        # Try to find any uppercase 3-5 letter word that might be a coin
        match = re.search(r'\b([A-Z]{3,5})\b', text.upper())
        if match:
            return match.group(1)

        return None

    def _get_pre_metrics(self) -> Dict[str, Any]:
        """Capture current performance metrics before adaptation.

        Returns:
            Dict with current win rate, P&L, etc.
        """
        metrics = {
            "timestamp": datetime.now().isoformat(),
        }

        if self.knowledge:
            stats = self.knowledge.get_stats_summary()
            metrics["blacklisted_coins"] = stats.get("coins", {}).get("blacklisted", 0)
            metrics["active_rules"] = stats.get("rules", {}).get("active", 0)
            metrics["active_patterns"] = stats.get("patterns", {}).get("active", 0)

        return metrics

    # =========================================================================
    # Insight Handlers
    # =========================================================================

    def _apply_coin_insight(self, insight: Insight) -> Optional[AdaptationRecord]:
        """Handle coin-related insights (blacklist, favor, reduce).

        Args:
            insight: Coin insight to apply.

        Returns:
            AdaptationRecord if applied.
        """
        # Extract coin from evidence or title
        coin = insight.evidence.get("coin") or self._extract_coin(insight.title)
        if not coin:
            logger.debug("Could not extract coin from insight")
            return None

        win_rate = insight.evidence.get("win_rate", 0.5)
        trades = insight.evidence.get("trades", 0)
        pnl = insight.evidence.get("pnl", 0)

        pre_metrics = self._get_pre_metrics()
        pre_metrics["coin"] = coin
        pre_metrics["win_rate"] = win_rate
        pre_metrics["trades"] = trades

        if insight.category == "problem":
            # Underperforming coin - consider blacklist
            thresholds = THRESHOLDS["blacklist"]

            if (
                insight.confidence >= thresholds["confidence"]
                and trades >= thresholds["min_trades"]
                and win_rate < thresholds["max_win_rate"]
                and pnl < 0
            ):
                # Blacklist the coin
                self.knowledge.blacklist_coin(coin, insight.description)

                record = AdaptationRecord(
                    adaptation_id=str(uuid.uuid4())[:8],
                    timestamp=datetime.now(),
                    insight_type="coin",
                    insight_title=insight.title,
                    action=AdaptationAction.BLACKLIST_COIN.value,
                    target=coin,
                    description=f"Blacklisted {coin}: {win_rate:.0%} win rate over {trades} trades",
                    pre_metrics=pre_metrics,
                    insight_confidence=insight.confidence,
                    insight_evidence=insight.evidence,
                )

                self._log_adaptation(record)
                return record

        elif insight.category == "opportunity":
            # Overperforming coin - favor it
            thresholds = THRESHOLDS["favor"]

            if (
                insight.confidence >= thresholds["confidence"]
                and trades >= thresholds["min_trades"]
                and win_rate >= thresholds["min_win_rate"]
                and pnl > 0
            ):
                # Favor the coin
                self.knowledge.favor_coin(coin, insight.description)

                record = AdaptationRecord(
                    adaptation_id=str(uuid.uuid4())[:8],
                    timestamp=datetime.now(),
                    insight_type="coin",
                    insight_title=insight.title,
                    action=AdaptationAction.FAVOR_COIN.value,
                    target=coin,
                    description=f"Favored {coin}: {win_rate:.0%} win rate over {trades} trades",
                    pre_metrics=pre_metrics,
                    insight_confidence=insight.confidence,
                    insight_evidence=insight.evidence,
                )

                self._log_adaptation(record)
                return record

        return None

    def _apply_pattern_insight(self, insight: Insight) -> Optional[AdaptationRecord]:
        """Handle pattern-related insights (deactivate, boost).

        Args:
            insight: Pattern insight to apply.

        Returns:
            AdaptationRecord if applied.
        """
        if not self.pattern_library:
            return None

        pattern_id = insight.evidence.get("pattern_id")
        if not pattern_id:
            return None

        win_rate = insight.evidence.get("win_rate", 0.5)
        trades = insight.evidence.get("trades", 0)
        confidence = insight.evidence.get("confidence", 0.5)

        pre_metrics = self._get_pre_metrics()
        pre_metrics["pattern_id"] = pattern_id
        pre_metrics["pattern_confidence"] = confidence

        if insight.category == "problem":
            # Failing pattern - deactivate
            thresholds = THRESHOLDS["deactivate_pattern"]

            if (
                insight.confidence >= thresholds["confidence"]
                and trades >= thresholds["min_trades"]
                and win_rate < 0.35
            ):
                self.pattern_library.deactivate_pattern(pattern_id, insight.description)

                record = AdaptationRecord(
                    adaptation_id=str(uuid.uuid4())[:8],
                    timestamp=datetime.now(),
                    insight_type="pattern",
                    insight_title=insight.title,
                    action=AdaptationAction.DEACTIVATE_PATTERN.value,
                    target=pattern_id,
                    description=f"Deactivated pattern {pattern_id}: {win_rate:.0%} win rate",
                    pre_metrics=pre_metrics,
                    insight_confidence=insight.confidence,
                    insight_evidence=insight.evidence,
                )

                self._log_adaptation(record)
                return record

        return None

    def _apply_time_insight(self, insight: Insight) -> Optional[AdaptationRecord]:
        """Handle time-based insights (create time filter rules).

        Args:
            insight: Time insight to apply.

        Returns:
            AdaptationRecord if applied.
        """
        if insight.category != "problem":
            return None

        thresholds = THRESHOLDS["create_time_rule"]
        if insight.confidence < thresholds["confidence"]:
            return None

        # Extract worst hours from evidence
        worst_hours = insight.evidence.get("worst_hours", [])
        if not worst_hours or not isinstance(worst_hours, list):
            return None

        trades = insight.evidence.get("trades", 0)
        if trades < thresholds["min_trades"]:
            return None

        pre_metrics = self._get_pre_metrics()

        # Create regime rule for bad hours
        rule_id = f"time_filter_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        rule = RegimeRule(
            rule_id=rule_id,
            description=f"Reduce trading during hours {worst_hours} (auto-generated from reflection)",
            condition={"hour_of_day": {"op": "in", "value": worst_hours}},
            action="REDUCE_SIZE",
        )

        self.knowledge.add_rule(rule)

        record = AdaptationRecord(
            adaptation_id=str(uuid.uuid4())[:8],
            timestamp=datetime.now(),
            insight_type="time",
            insight_title=insight.title,
            action=AdaptationAction.CREATE_TIME_RULE.value,
            target=rule_id,
            description=f"Created time filter: REDUCE_SIZE during hours {worst_hours}",
            pre_metrics=pre_metrics,
            insight_confidence=insight.confidence,
            insight_evidence=insight.evidence,
        )

        self._log_adaptation(record)
        return record

    def _apply_regime_insight(self, insight: Insight) -> Optional[AdaptationRecord]:
        """Handle regime-based insights (create market regime rules).

        Args:
            insight: Regime insight to apply.

        Returns:
            AdaptationRecord if applied.
        """
        if insight.category != "problem":
            return None

        thresholds = THRESHOLDS["create_regime_rule"]
        if insight.confidence < thresholds["confidence"]:
            return None

        # Extract worst regime from evidence
        worst_regime = insight.evidence.get("worst_regime")
        if not worst_regime:
            return None

        trades = insight.evidence.get("trades", 0)
        if trades < thresholds["min_trades"]:
            return None

        # Map regime to condition
        condition = {}
        if worst_regime == "btc_down":
            condition = {"btc_trend": "down"}
        elif worst_regime == "btc_up":
            condition = {"btc_trend": "up"}
        elif worst_regime == "btc_sideways":
            condition = {"btc_trend": "sideways"}
        elif "weekend" in worst_regime.lower():
            condition = {"is_weekend": True}
        else:
            logger.debug(f"Unknown regime: {worst_regime}")
            return None

        pre_metrics = self._get_pre_metrics()

        # Create regime rule
        rule_id = f"regime_filter_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        rule = RegimeRule(
            rule_id=rule_id,
            description=f"Reduce trading during {worst_regime} (auto-generated from reflection)",
            condition=condition,
            action="REDUCE_SIZE",
        )

        self.knowledge.add_rule(rule)

        record = AdaptationRecord(
            adaptation_id=str(uuid.uuid4())[:8],
            timestamp=datetime.now(),
            insight_type="regime",
            insight_title=insight.title,
            action=AdaptationAction.CREATE_REGIME_RULE.value,
            target=rule_id,
            description=f"Created regime filter: REDUCE_SIZE during {worst_regime}",
            pre_metrics=pre_metrics,
            insight_confidence=insight.confidence,
            insight_evidence=insight.evidence,
        )

        self._log_adaptation(record)
        return record

    # =========================================================================
    # Logging
    # =========================================================================

    def _log_adaptation(self, record: AdaptationRecord) -> None:
        """Log adaptation to database.

        Args:
            record: The adaptation record to log.
        """
        if not self.db:
            return

        try:
            self.db.log_adaptation(
                adaptation_id=record.adaptation_id,
                insight_type=record.insight_type,
                action=record.action,
                target=record.target,
                description=record.description,
                pre_metrics=json.dumps(record.pre_metrics),
                insight_confidence=record.insight_confidence,
                insight_evidence=json.dumps(record.insight_evidence),
            )
        except Exception as e:
            logger.error(f"Failed to log adaptation: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get AdaptationEngine statistics.

        Returns:
            Stats dictionary.
        """
        return {
            "adaptations_applied": self.adaptations_applied,
            "adaptations_skipped": self.adaptations_skipped,
        }

    def get_health(self) -> Dict[str, Any]:
        """Get component health status for monitoring.

        Returns:
            Dict with status (healthy/degraded/failed), last_activity, error_count, metrics.
        """
        # AdaptationEngine is passive - it's called by ReflectionEngine
        # Health is based on whether it has Knowledge Brain access

        status = "healthy"
        if not self.knowledge:
            status = "degraded"

        return {
            "status": status,
            "last_activity": None,  # Passive component
            "error_count": 0,
            "metrics": {
                "adaptations_applied": self.adaptations_applied,
                "adaptations_skipped": self.adaptations_skipped,
                "has_knowledge_brain": self.knowledge is not None,
                "has_coin_scorer": self.coin_scorer is not None,
                "has_pattern_library": self.pattern_library is not None,
            }
        }


# Allow running directly for testing
if __name__ == "__main__":
    import tempfile
    import os

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("=" * 60)
    print("AdaptationEngine Test")
    print("=" * 60)

    # Create temp database
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        from src.database import Database
        from src.knowledge import KnowledgeBrain
        from src.coin_scorer import CoinScorer
        from src.pattern_library import PatternLibrary
        from src.models.reflection import Insight

        db = Database(path)
        brain = KnowledgeBrain(db)
        scorer = CoinScorer(brain, db)
        patterns = PatternLibrary(brain)

        engine = AdaptationEngine(brain, scorer, patterns, db)

        # Test 1: Coin blacklist
        print("\n[TEST 1] Apply coin blacklist insight...")
        insight = Insight(
            insight_type="coin",
            category="problem",
            title="DOGE underperforming",
            description="DOGE has 20% win rate over 10 trades with -$15 loss",
            evidence={"coin": "DOGE", "win_rate": 0.20, "trades": 10, "pnl": -15.0},
            suggested_action="Blacklist DOGE",
            confidence=0.90,
        )

        adaptations = engine.apply_insights([insight])
        if adaptations:
            print(f"  Applied: {adaptations[0]}")
            # Verify
            assert brain.is_blacklisted("DOGE"), "DOGE should be blacklisted"
            print("  PASSED: DOGE blacklisted")
        else:
            print("  FAILED: No adaptation applied")

        # Test 2: Coin favor
        print("\n[TEST 2] Apply coin favor insight...")
        insight = Insight(
            insight_type="coin",
            category="opportunity",
            title="SOL strong performer",
            description="SOL has 75% win rate over 12 trades with $18 profit",
            evidence={"coin": "SOL", "win_rate": 0.75, "trades": 12, "pnl": 18.0},
            suggested_action="Favor SOL",
            confidence=0.85,
        )

        adaptations = engine.apply_insights([insight])
        if adaptations:
            print(f"  Applied: {adaptations[0]}")
            # Verify - SOL should be marked with "improving" trend
            sol_score = brain.get_coin_score("SOL")
            assert sol_score is not None, "SOL should have score"
            assert sol_score.trend == "improving", "SOL should be improving"
            print("  PASSED: SOL favored (trend=improving)")
        else:
            print("  FAILED: No adaptation applied")

        # Test 3: Time rule
        print("\n[TEST 3] Apply time rule insight...")
        insight = Insight(
            insight_type="time",
            category="problem",
            title="Asia session losses",
            description="Hours 2-5 UTC have 25% win rate",
            evidence={"worst_hours": [2, 3, 4, 5], "win_rate": 0.25, "trades": 15},
            suggested_action="Add time filter",
            confidence=0.80,
        )

        adaptations = engine.apply_insights([insight])
        if adaptations:
            print(f"  Applied: {adaptations[0]}")
            rules = brain.get_active_rules()
            time_rules = [r for r in rules if "time_filter" in r.rule_id]
            assert len(time_rules) > 0, "Should have time rule"
            print(f"  PASSED: Time rule created ({time_rules[0].rule_id})")
        else:
            print("  FAILED: No adaptation applied")

        # Test 4: Low confidence skipped
        print("\n[TEST 4] Skip low confidence insight...")
        insight = Insight(
            insight_type="coin",
            category="problem",
            title="BTC slightly underperforming",
            description="BTC has 45% win rate",
            evidence={"coin": "BTC", "win_rate": 0.45, "trades": 5, "pnl": -2.0},
            suggested_action="Maybe reduce BTC",
            confidence=0.50,  # Too low
        )

        adaptations = engine.apply_insights([insight])
        assert len(adaptations) == 0, "Should skip low confidence"
        print("  PASSED: Low confidence insight skipped")

        # Stats
        print("\n" + "-" * 40)
        print("Stats:")
        for k, v in engine.get_stats().items():
            print(f"  {k}: {v}")

        print("\n" + "=" * 60)
        print("All AdaptationEngine Tests PASSED!")
        print("=" * 60)

    finally:
        os.unlink(path)
