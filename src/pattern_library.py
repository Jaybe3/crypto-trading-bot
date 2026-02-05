"""Pattern Library - Manages trading patterns and their effectiveness.

This module provides pattern storage, matching, and confidence management:
- Store and retrieve trading patterns
- Extract patterns from winning trades
- Match current market conditions to known patterns
- Update pattern confidence based on outcomes
- Provide high-confidence patterns to Strategist
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from src.knowledge import KnowledgeBrain
from src.models.knowledge import TradingPattern

logger = logging.getLogger(__name__)


# Confidence thresholds
HIGH_CONFIDENCE = 0.7
MEDIUM_CONFIDENCE = 0.5
LOW_CONFIDENCE = 0.3
DEACTIVATE_THRESHOLD = 0.3

# Minimum uses before confidence is meaningful
MIN_USES_FOR_CONFIDENCE = 3

# Position modifiers based on confidence
CONFIDENCE_MODIFIERS = {
    "high": 1.25,      # >= 0.7
    "medium": 1.0,     # 0.5 - 0.7
    "low": 0.75,       # 0.3 - 0.5
    "very_low": 0.0,   # < 0.3 (deactivated)
}


@dataclass
class PatternMatch:
    """Result of matching market conditions to a pattern."""
    pattern: TradingPattern
    match_score: float              # 0-1, how well conditions match
    matched_conditions: Dict[str, Any]   # Which conditions were satisfied
    missing_conditions: Dict[str, Any]   # Which conditions were not satisfied

    @property
    def is_full_match(self) -> bool:
        """Check if all conditions matched."""
        return len(self.missing_conditions) == 0


@dataclass
class PatternSuggestion:
    """A pattern suggestion for the Strategist."""
    pattern: TradingPattern
    suggested_direction: str        # "LONG" or "SHORT"
    suggested_entry: Dict[str, Any]  # Entry parameters
    suggested_exit: Dict[str, Any]   # Exit parameters
    confidence: float               # Overall confidence
    reasoning: str                  # Why this pattern applies


# Seed patterns for initial library
SEED_PATTERNS = [
    {
        "pattern_id": "momentum_breakout_v1",
        "description": "Long on price breakout with volume confirmation",
        "entry_conditions": {
            "near_24h_high": True,
            "volume_above_avg": True,
            "btc_trend": "up",
        },
        "exit_conditions": {
            "stop_loss_pct": 2.0,
            "take_profit_pct": 3.0,
        },
    },
    {
        "pattern_id": "support_bounce_v1",
        "description": "Long on bounce from support with oversold conditions",
        "entry_conditions": {
            "near_support": True,
            "oversold": True,
            "btc_trend_not_down": True,
        },
        "exit_conditions": {
            "stop_loss_pct": 1.5,
            "take_profit_pct": 2.5,
        },
    },
    {
        "pattern_id": "trend_pullback_v1",
        "description": "Long on pullback in established uptrend",
        "entry_conditions": {
            "trend": "up",
            "pullback_active": True,
            "not_oversold": True,
        },
        "exit_conditions": {
            "stop_loss_pct": 2.5,
            "take_profit_pct": 2.0,
        },
    },
]


class PatternLibrary:
    """Manages trading patterns and their effectiveness.

    Provides pattern storage, matching, confidence management, and
    integration with the Strategist for informed decision-making.

    Example:
        >>> library = PatternLibrary(brain)
        >>> pattern = library.create_pattern(
        ...     "breakout", "Breakout pattern",
        ...     {"breakout": True}, {"stop_loss_pct": 2.0}
        ... )
        >>> matches = library.match_conditions({"breakout": True})
        >>> for m in matches:
        ...     print(f"{m.pattern.description}: {m.match_score:.0%}")
    """

    def __init__(self, brain: KnowledgeBrain, seed_patterns: bool = True):
        """Initialize PatternLibrary.

        Args:
            brain: KnowledgeBrain instance for pattern storage.
            seed_patterns: Whether to add seed patterns if library is empty.
        """
        self.brain = brain

        # Seed patterns if empty
        if seed_patterns and len(brain.get_active_patterns()) == 0:
            self._seed_patterns()

        logger.info(f"PatternLibrary initialized: {len(self.brain.get_active_patterns())} active patterns")

    def _seed_patterns(self) -> None:
        """Add seed patterns to empty library."""
        for seed in SEED_PATTERNS:
            pattern = TradingPattern(
                pattern_id=seed["pattern_id"],
                description=seed["description"],
                entry_conditions=seed["entry_conditions"],
                exit_conditions=seed["exit_conditions"],
                confidence=0.5,  # Start neutral
            )
            self.brain.add_pattern(pattern)
        logger.info(f"Seeded {len(SEED_PATTERNS)} initial patterns")

    # =========================================================================
    # Pattern Retrieval
    # =========================================================================

    def get_pattern(self, pattern_id: str) -> Optional[TradingPattern]:
        """Get a pattern by ID.

        Args:
            pattern_id: Pattern identifier.

        Returns:
            TradingPattern or None if not found.
        """
        return self.brain.get_pattern(pattern_id)

    def get_active_patterns(self) -> List[TradingPattern]:
        """Get all active patterns.

        Returns:
            List of active TradingPattern objects.
        """
        return self.brain.get_active_patterns()

    def get_high_confidence_patterns(self, min_confidence: float = HIGH_CONFIDENCE) -> List[TradingPattern]:
        """Get patterns with high confidence.

        Args:
            min_confidence: Minimum confidence threshold (default: 0.7).

        Returns:
            List of high-confidence patterns sorted by confidence.
        """
        patterns = [
            p for p in self.brain.get_active_patterns()
            if p.confidence >= min_confidence
        ]
        return sorted(patterns, key=lambda p: p.confidence, reverse=True)

    def get_patterns_by_type(self, pattern_type: str) -> List[TradingPattern]:
        """Get patterns of a specific type.

        Args:
            pattern_type: Pattern type (e.g., "momentum_breakout").

        Returns:
            List of matching patterns.
        """
        return [
            p for p in self.brain.get_active_patterns()
            if pattern_type in p.pattern_id
        ]

    # =========================================================================
    # Pattern Creation
    # =========================================================================

    def create_pattern(
        self,
        pattern_type: str,
        description: str,
        entry_conditions: Dict[str, Any],
        exit_conditions: Dict[str, Any],
        source_trade_id: Optional[str] = None
    ) -> TradingPattern:
        """Create a new pattern.

        Args:
            pattern_type: Type of pattern (e.g., "breakout", "support_bounce").
            description: Human-readable description.
            entry_conditions: Conditions that must be met to enter.
            exit_conditions: Exit parameters (stop_loss_pct, take_profit_pct).
            source_trade_id: Optional ID of trade that inspired this pattern.

        Returns:
            Created TradingPattern.
        """
        # Generate unique ID
        suffix = str(uuid.uuid4())[:8]
        pattern_id = f"{pattern_type}_{suffix}"

        pattern = TradingPattern(
            pattern_id=pattern_id,
            description=description,
            entry_conditions=entry_conditions,
            exit_conditions=exit_conditions,
            confidence=0.5,  # Start neutral
        )

        self.brain.add_pattern(pattern)
        logger.info(f"Created pattern: {pattern_id} - {description}")

        return pattern

    def create_pattern_from_trade(self, trade: Dict[str, Any]) -> Optional[TradingPattern]:
        """Extract a pattern from a successful trade.

        Only creates patterns from winning trades with sufficient context.

        Args:
            trade: Trade data (typically from JournalEntry).

        Returns:
            New TradingPattern or None if trade unsuitable.
        """
        pnl = trade.get("pnl_usd") or trade.get("pnl", 0)
        if pnl <= 0:
            logger.debug("Skipping pattern extraction: trade was not profitable")
            return None

        # Extract entry conditions from trade context
        entry_conditions = {}

        # Direction
        direction = trade.get("direction", "LONG")
        entry_conditions["direction"] = direction

        # Market regime
        if trade.get("market_regime"):
            entry_conditions["market_regime"] = trade["market_regime"]

        # Time of day
        hour = trade.get("hour_of_day")
        if hour is not None:
            entry_conditions["hour_range"] = self._get_hour_range(hour)

        # BTC trend context
        if trade.get("btc_trend"):
            entry_conditions["btc_trend"] = trade["btc_trend"]

        # Volatility context
        if trade.get("volatility"):
            entry_conditions["volatility_level"] = self._get_volatility_level(trade["volatility"])

        # Exit conditions from trade
        exit_conditions = {}
        if trade.get("stop_loss_price") and trade.get("entry_price"):
            stop_pct = abs(trade["stop_loss_price"] - trade["entry_price"]) / trade["entry_price"] * 100
            exit_conditions["stop_loss_pct"] = round(stop_pct, 1)
        else:
            exit_conditions["stop_loss_pct"] = 2.0  # Default

        if trade.get("take_profit_price") and trade.get("entry_price"):
            tp_pct = abs(trade["take_profit_price"] - trade["entry_price"]) / trade["entry_price"] * 100
            exit_conditions["take_profit_pct"] = round(tp_pct, 1)
        else:
            exit_conditions["take_profit_pct"] = 2.0  # Default

        # Generate description
        description = self._generate_description(trade, entry_conditions)

        # Create pattern
        trade_id = trade.get("id", str(uuid.uuid4())[:8])
        pattern = TradingPattern(
            pattern_id=f"auto_{trade_id[:8]}",
            description=description,
            entry_conditions=entry_conditions,
            exit_conditions=exit_conditions,
            times_used=1,
            wins=1,
            total_pnl=pnl,
            confidence=0.5,  # Start neutral
        )

        self.brain.add_pattern(pattern)
        logger.info(f"Extracted pattern from trade: {pattern.pattern_id}")

        return pattern

    def _get_hour_range(self, hour: int) -> str:
        """Convert hour to trading session."""
        if 0 <= hour < 8:
            return "asia"
        elif 8 <= hour < 14:
            return "europe"
        elif 14 <= hour < 21:
            return "us"
        else:
            return "late_us"

    def _get_volatility_level(self, volatility: float) -> str:
        """Convert volatility to level."""
        if volatility < 1.0:
            return "low"
        elif volatility < 3.0:
            return "medium"
        else:
            return "high"

    def _generate_description(self, trade: Dict[str, Any], conditions: Dict[str, Any]) -> str:
        """Generate human-readable pattern description."""
        direction = conditions.get("direction", "LONG")
        coin = trade.get("coin", "unknown")
        regime = conditions.get("market_regime", "")
        hour_range = conditions.get("hour_range", "")

        parts = [direction, coin]
        if regime:
            parts.append(f"in {regime} regime")
        if hour_range:
            parts.append(f"during {hour_range} session")

        return " ".join(parts)

    # =========================================================================
    # Pattern Matching
    # =========================================================================

    def match_conditions(self, market_state: Dict[str, Any]) -> List[PatternMatch]:
        """Match current market conditions against all active patterns.

        Args:
            market_state: Current market conditions.

        Returns:
            List of PatternMatch objects, sorted by match score.
        """
        matches = []

        for pattern in self.brain.get_active_patterns():
            match = self._match_single_pattern(pattern, market_state)
            if match.match_score > 0:
                matches.append(match)

        # Sort by match score descending
        return sorted(matches, key=lambda m: m.match_score, reverse=True)

    def _match_single_pattern(self, pattern: TradingPattern, market_state: Dict[str, Any]) -> PatternMatch:
        """Match market state against a single pattern.

        Args:
            pattern: Pattern to match against.
            market_state: Current market conditions.

        Returns:
            PatternMatch with score and condition details.
        """
        matched = {}
        missing = {}

        for key, required_value in pattern.entry_conditions.items():
            actual_value = market_state.get(key)

            if actual_value is None:
                missing[key] = required_value
                continue

            if self._condition_matches(actual_value, required_value):
                matched[key] = actual_value
            else:
                missing[key] = required_value

        # Calculate match score
        total_conditions = len(pattern.entry_conditions)
        if total_conditions == 0:
            score = 0.0
        else:
            score = len(matched) / total_conditions

        return PatternMatch(
            pattern=pattern,
            match_score=score,
            matched_conditions=matched,
            missing_conditions=missing,
        )

    def _condition_matches(self, actual: Any, required: Any) -> bool:
        """Check if an actual value matches a required condition.

        Handles various condition formats:
        - Direct equality: "up" == "up"
        - Boolean: True == True
        - Operators: {"op": "gte", "value": 0.5}
        """
        # Handle operator dict
        if isinstance(required, dict) and "op" in required:
            op = required["op"]
            target = required["value"]

            if op == "eq":
                return actual == target
            elif op == "neq":
                return actual != target
            elif op == "gt":
                return actual > target
            elif op == "gte":
                return actual >= target
            elif op == "lt":
                return actual < target
            elif op == "lte":
                return actual <= target
            elif op == "in":
                return actual in target
            elif op == "not_in":
                return actual not in target
            else:
                return False

        # Direct equality
        return actual == required

    def find_similar_patterns(self, conditions: Dict[str, Any], min_similarity: float = 0.5) -> List[TradingPattern]:
        """Find patterns with similar entry conditions.

        Args:
            conditions: Conditions to compare.
            min_similarity: Minimum similarity score (0-1).

        Returns:
            List of similar patterns.
        """
        similar = []

        for pattern in self.brain.get_active_patterns():
            similarity = self._calculate_similarity(pattern.entry_conditions, conditions)
            if similarity >= min_similarity:
                similar.append(pattern)

        return similar

    def _calculate_similarity(self, conditions1: Dict[str, Any], conditions2: Dict[str, Any]) -> float:
        """Calculate similarity between two condition sets."""
        all_keys = set(conditions1.keys()) | set(conditions2.keys())
        if not all_keys:
            return 0.0

        matching = 0
        for key in all_keys:
            val1 = conditions1.get(key)
            val2 = conditions2.get(key)
            if val1 == val2:
                matching += 1

        return matching / len(all_keys)

    # =========================================================================
    # Pattern Updates
    # =========================================================================

    def record_pattern_outcome(self, pattern_id: str, won: bool, pnl: float) -> None:
        """Record the outcome of a trade that used a pattern.

        Args:
            pattern_id: Pattern identifier.
            won: Whether the trade was profitable.
            pnl: P&L from the trade.
        """
        self.brain.update_pattern_stats(pattern_id, won, pnl)

        # Update confidence
        new_confidence = self.update_confidence(pattern_id)

        # Check for deactivation
        if new_confidence < DEACTIVATE_THRESHOLD:
            pattern = self.brain.get_pattern(pattern_id)
            if pattern and pattern.times_used >= MIN_USES_FOR_CONFIDENCE:
                self.deactivate_pattern(pattern_id, f"Confidence dropped to {new_confidence:.2f}")

    def update_confidence(self, pattern_id: str) -> float:
        """Recalculate and update confidence for a pattern.

        Args:
            pattern_id: Pattern identifier.

        Returns:
            Updated confidence score.
        """
        pattern = self.brain.get_pattern(pattern_id)
        if not pattern:
            return 0.0

        confidence = self.calculate_confidence(pattern)

        # Update in brain (need to save full pattern)
        pattern.confidence = confidence
        self.brain.add_pattern(pattern)  # This does INSERT OR REPLACE

        return confidence

    def calculate_confidence(self, pattern: TradingPattern) -> float:
        """Calculate confidence score for a pattern.

        Factors:
        - Base from win rate: (win_rate - 0.5) * 0.5 + 0.5
        - Usage factor: More uses = more reliable data
        - Recency factor: Could be added later

        Returns:
            Confidence score between 0.1 and 0.9.
        """
        if pattern.times_used < MIN_USES_FOR_CONFIDENCE:
            return 0.5  # Not enough data

        # Base from win rate (ranges 0.25 to 0.75 for 0% to 100% win rate)
        win_rate_contrib = (pattern.win_rate - 0.5) * 0.5
        base_confidence = 0.5 + win_rate_contrib

        # Usage factor (more usage = more reliable, caps at 20 uses)
        usage_factor = min(1.0, pattern.times_used / 20)

        # Combine: base confidence weighted by reliability
        confidence = base_confidence * (0.7 + 0.3 * usage_factor)

        # Clamp to valid range
        return max(0.1, min(0.9, confidence))

    def deactivate_pattern(self, pattern_id: str, reason: str = "") -> None:
        """Deactivate a pattern.

        Args:
            pattern_id: Pattern identifier.
            reason: Reason for deactivation.
        """
        self.brain.deactivate_pattern(pattern_id)
        logger.info(f"Deactivated pattern {pattern_id}: {reason}")

    def reactivate_pattern(self, pattern_id: str) -> None:
        """Reactivate a previously deactivated pattern.

        Args:
            pattern_id: Pattern identifier.
        """
        pattern = self.brain.get_pattern(pattern_id)
        if pattern:
            pattern.is_active = True
            pattern.confidence = 0.5  # Reset to neutral
            self.brain.add_pattern(pattern)
            logger.info(f"Reactivated pattern {pattern_id}")

    # =========================================================================
    # Strategist Interface
    # =========================================================================

    def get_pattern_context(self) -> Dict[str, Any]:
        """Get pattern context for Strategist prompts.

        Returns:
            Dictionary with categorized patterns and suggestions.
        """
        active = self.brain.get_active_patterns()

        high_confidence = [p for p in active if p.confidence >= HIGH_CONFIDENCE]
        medium_confidence = [p for p in active if MEDIUM_CONFIDENCE <= p.confidence < HIGH_CONFIDENCE]

        return {
            "high_confidence": high_confidence,
            "medium_confidence": medium_confidence,
            "total_active": len(active),
            "pattern_summaries": [
                {
                    "id": p.pattern_id,
                    "description": p.description,
                    "confidence": p.confidence,
                    "win_rate": p.win_rate,
                    "times_used": p.times_used,
                }
                for p in sorted(active, key=lambda x: x.confidence, reverse=True)[:10]
            ],
        }

    def get_suggested_patterns(self, coin: str, market_state: Dict[str, Any]) -> List[PatternSuggestion]:
        """Get pattern suggestions for current market conditions.

        Args:
            coin: Coin being considered.
            market_state: Current market conditions.

        Returns:
            List of PatternSuggestion objects.
        """
        suggestions = []
        matches = self.match_conditions(market_state)

        for match in matches:
            if match.match_score >= 0.7:  # Only suggest high matches
                pattern = match.pattern

                # Determine direction from pattern
                direction = pattern.entry_conditions.get("direction", "LONG")

                suggestion = PatternSuggestion(
                    pattern=pattern,
                    suggested_direction=direction,
                    suggested_entry=pattern.entry_conditions,
                    suggested_exit=pattern.exit_conditions,
                    confidence=pattern.confidence * match.match_score,
                    reasoning=self._generate_suggestion_reasoning(match),
                )
                suggestions.append(suggestion)

        return sorted(suggestions, key=lambda s: s.confidence, reverse=True)

    def _generate_suggestion_reasoning(self, match: PatternMatch) -> str:
        """Generate reasoning for a pattern suggestion."""
        matched_keys = list(match.matched_conditions.keys())
        pattern = match.pattern

        return (
            f"Pattern '{pattern.description}' matches {match.match_score:.0%} "
            f"({len(matched_keys)} of {len(pattern.entry_conditions)} conditions). "
            f"Pattern has {pattern.win_rate:.0%} win rate over {pattern.times_used} uses."
        )

    def get_position_modifier(self, pattern_id: str) -> float:
        """Get position size modifier based on pattern confidence.

        Args:
            pattern_id: Pattern identifier.

        Returns:
            Position size multiplier (0.75 to 1.25).
        """
        pattern = self.brain.get_pattern(pattern_id)
        if not pattern:
            return 1.0

        if pattern.confidence >= HIGH_CONFIDENCE:
            return CONFIDENCE_MODIFIERS["high"]
        elif pattern.confidence >= MEDIUM_CONFIDENCE:
            return CONFIDENCE_MODIFIERS["medium"]
        elif pattern.confidence >= LOW_CONFIDENCE:
            return CONFIDENCE_MODIFIERS["low"]
        else:
            return CONFIDENCE_MODIFIERS["very_low"]

    def get_stats_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the pattern library.

        Returns:
            Dictionary with pattern statistics.
        """
        active = self.brain.get_active_patterns()

        if not active:
            return {
                "total_patterns": 0,
                "high_confidence": 0,
                "medium_confidence": 0,
                "low_confidence": 0,
                "avg_win_rate": 0.0,
                "total_uses": 0,
            }

        high = sum(1 for p in active if p.confidence >= HIGH_CONFIDENCE)
        medium = sum(1 for p in active if MEDIUM_CONFIDENCE <= p.confidence < HIGH_CONFIDENCE)
        low = sum(1 for p in active if p.confidence < MEDIUM_CONFIDENCE)

        total_uses = sum(p.times_used for p in active)
        patterns_with_data = [p for p in active if p.times_used > 0]
        avg_win_rate = (
            sum(p.win_rate for p in patterns_with_data) / len(patterns_with_data)
            if patterns_with_data else 0.0
        )

        return {
            "total_patterns": len(active),
            "high_confidence": high,
            "medium_confidence": medium,
            "low_confidence": low,
            "avg_win_rate": avg_win_rate,
            "total_uses": total_uses,
        }
