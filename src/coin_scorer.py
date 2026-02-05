"""Coin Scoring System - Tracks coin performance and triggers adaptations.

This module implements the "Quick Update" tier of reflection:
- Updates coin scores after each trade close
- Automatically triggers adaptations when thresholds are crossed
- Provides position size modifiers based on coin performance
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from src.knowledge import KnowledgeBrain

logger = logging.getLogger(__name__)


class CoinStatus(Enum):
    """Current trading status for a coin."""
    BLACKLISTED = "blacklisted"    # Do not trade
    REDUCED = "reduced"            # Trade with reduced size (50%)
    NORMAL = "normal"              # Trade normally (100%)
    FAVORED = "favored"            # Can trade with increased size (150%)
    UNKNOWN = "unknown"            # Not enough data yet


# Position size multipliers for each status
POSITION_MODIFIERS = {
    CoinStatus.BLACKLISTED: 0.0,
    CoinStatus.REDUCED: 0.5,
    CoinStatus.NORMAL: 1.0,
    CoinStatus.FAVORED: 1.5,
    CoinStatus.UNKNOWN: 1.0,  # Treat unknown as normal
}

# Minimum trades required before making adaptation decisions
MIN_TRADES_FOR_ADAPTATION = 5

# Thresholds
BLACKLIST_WIN_RATE = 0.30      # Below this + negative P&L = blacklist
REDUCED_WIN_RATE = 0.45        # Below this = reduced size
FAVORED_WIN_RATE = 0.60        # Above this + positive P&L = favored
RECOVERY_WIN_RATE = 0.50       # Above this to recover from reduced


@dataclass
class CoinAdaptation:
    """Record of a coin status change."""
    coin: str
    timestamp: datetime
    old_status: CoinStatus
    new_status: CoinStatus
    reason: str
    trigger_stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "coin": self.coin,
            "timestamp": self.timestamp.isoformat(),
            "old_status": self.old_status.value,
            "new_status": self.new_status.value,
            "reason": self.reason,
            "trigger_stats": self.trigger_stats,
        }


class CoinScorer:
    """Manages coin performance scoring and adaptations.

    Called after every trade close to update scores and check thresholds.
    Provides position size modifiers for the Strategist.

    Example:
        >>> scorer = CoinScorer(brain)
        >>> adaptation = scorer.process_trade_result(trade_entry)
        >>> if adaptation:
        ...     print(f"{adaptation.coin} -> {adaptation.new_status.value}")
        >>> modifier = scorer.get_position_modifier("SOL")
        >>> position_size = base_size * modifier
    """

    def __init__(self, brain: KnowledgeBrain, db=None):
        """Initialize CoinScorer.

        Args:
            brain: KnowledgeBrain instance for reading/writing coin data.
            db: Optional database for logging adaptations.
        """
        self.brain = brain
        self.db = db
        self._status_cache: Dict[str, CoinStatus] = {}
        self._load_statuses()
        logger.info("CoinScorer initialized")

    def _load_statuses(self) -> None:
        """Load current statuses from brain."""
        for score in self.brain.get_all_coin_scores():
            self._status_cache[score.coin] = self._calculate_status(score)

    def _calculate_status(self, score) -> CoinStatus:
        """Calculate status from a CoinScore."""
        if score.is_blacklisted:
            return CoinStatus.BLACKLISTED

        if score.total_trades < MIN_TRADES_FOR_ADAPTATION:
            return CoinStatus.UNKNOWN

        if score.win_rate < BLACKLIST_WIN_RATE and score.total_pnl < 0:
            return CoinStatus.BLACKLISTED

        if score.win_rate < REDUCED_WIN_RATE:
            return CoinStatus.REDUCED

        if score.win_rate >= FAVORED_WIN_RATE and score.total_pnl > 0:
            return CoinStatus.FAVORED

        return CoinStatus.NORMAL

    def process_trade_result(self, trade: Dict[str, Any]) -> Optional[CoinAdaptation]:
        """Process a completed trade and return any adaptation triggered.

        This is the main entry point, called after every trade close.

        Args:
            trade: Trade data with at least: coin, pnl_usd (or pnl)

        Returns:
            CoinAdaptation if status changed, None otherwise.
        """
        coin = trade.get("coin")
        pnl = trade.get("pnl_usd") or trade.get("pnl", 0)

        if not coin:
            logger.warning("process_trade_result called without coin")
            return None

        # Determine if trade was a win
        won = pnl > 0

        # Update score in brain
        self.brain.update_coin_score(coin, {"won": won, "pnl": pnl})

        # Check for threshold crossings
        adaptation = self.check_thresholds(coin)

        if adaptation:
            self._log_adaptation(adaptation)

        return adaptation

    def check_thresholds(self, coin: str) -> Optional[CoinAdaptation]:
        """Check if coin crosses any adaptation thresholds.

        Args:
            coin: Coin symbol to check.

        Returns:
            CoinAdaptation if status changed, None otherwise.
        """
        score = self.brain.get_coin_score(coin)
        if not score:
            return None

        if score.total_trades < MIN_TRADES_FOR_ADAPTATION:
            # Not enough data yet
            self._status_cache[coin] = CoinStatus.UNKNOWN
            return None

        current_status = self._status_cache.get(coin, CoinStatus.UNKNOWN)
        new_status = current_status
        reason = ""

        # Check BLACKLIST threshold (most severe)
        if (score.win_rate < BLACKLIST_WIN_RATE and
            score.total_pnl < 0 and
            not score.is_blacklisted):

            new_status = CoinStatus.BLACKLISTED
            reason = (f"Win rate {score.win_rate:.0%} < {BLACKLIST_WIN_RATE:.0%} "
                     f"with ${score.total_pnl:.2f} loss over {score.total_trades} trades")
            self.brain.blacklist_coin(coin, reason)

        # Check REDUCED threshold (not blacklisted, but underperforming)
        elif (score.win_rate < REDUCED_WIN_RATE and
              current_status not in [CoinStatus.BLACKLISTED, CoinStatus.REDUCED]):

            new_status = CoinStatus.REDUCED
            reason = (f"Win rate {score.win_rate:.0%} < {REDUCED_WIN_RATE:.0%} "
                     f"over {score.total_trades} trades")

        # Check FAVORED threshold (performing well)
        elif (score.win_rate >= FAVORED_WIN_RATE and
              score.total_pnl > 0 and
              current_status not in [CoinStatus.BLACKLISTED, CoinStatus.FAVORED]):

            new_status = CoinStatus.FAVORED
            reason = (f"Win rate {score.win_rate:.0%} >= {FAVORED_WIN_RATE:.0%} "
                     f"with ${score.total_pnl:.2f} profit over {score.total_trades} trades")

        # Check if coin recovered from REDUCED status
        elif (score.win_rate >= RECOVERY_WIN_RATE and
              current_status == CoinStatus.REDUCED):

            new_status = CoinStatus.NORMAL
            reason = f"Win rate recovered to {score.win_rate:.0%} (>= {RECOVERY_WIN_RATE:.0%})"

        # Check if coin dropped from FAVORED status
        elif ((score.win_rate < FAVORED_WIN_RATE or score.total_pnl <= 0) and
              current_status == CoinStatus.FAVORED):

            new_status = CoinStatus.NORMAL
            if score.total_pnl <= 0:
                reason = f"P&L went negative (${score.total_pnl:.2f})"
            else:
                reason = f"Win rate dropped to {score.win_rate:.0%} (< {FAVORED_WIN_RATE:.0%})"

        # Update cache and return adaptation if changed
        if new_status != current_status:
            self._status_cache[coin] = new_status

            adaptation = CoinAdaptation(
                coin=coin,
                timestamp=datetime.now(),
                old_status=current_status,
                new_status=new_status,
                reason=reason,
                trigger_stats={
                    "total_trades": score.total_trades,
                    "wins": score.wins,
                    "losses": score.losses,
                    "win_rate": score.win_rate,
                    "total_pnl": score.total_pnl,
                    "avg_pnl": score.avg_pnl,
                }
            )

            logger.info(f"COIN ADAPTATION: {coin} {current_status.value} -> {new_status.value}")
            logger.info(f"  Reason: {reason}")

            return adaptation

        return None

    def get_position_modifier(self, coin: str) -> float:
        """Get position size modifier for a coin.

        Args:
            coin: Coin symbol.

        Returns:
            Multiplier: 0.0 (blacklisted), 0.5 (reduced), 1.0 (normal), 1.5 (favored)
        """
        status = self.get_coin_status(coin)
        return POSITION_MODIFIERS[status]

    def get_coin_status(self, coin: str) -> CoinStatus:
        """Get current status for a coin.

        Args:
            coin: Coin symbol.

        Returns:
            CoinStatus enum value.
        """
        # Check cache first
        if coin in self._status_cache:
            return self._status_cache[coin]

        # Check brain for blacklist
        if self.brain.is_blacklisted(coin):
            self._status_cache[coin] = CoinStatus.BLACKLISTED
            return CoinStatus.BLACKLISTED

        # Calculate from score
        score = self.brain.get_coin_score(coin)
        if score:
            status = self._calculate_status(score)
            self._status_cache[coin] = status
            return status

        return CoinStatus.UNKNOWN

    def force_blacklist(self, coin: str, reason: str) -> CoinAdaptation:
        """Manually blacklist a coin (for dashboard override).

        Args:
            coin: Coin symbol to blacklist.
            reason: Reason for manual blacklist.

        Returns:
            CoinAdaptation record.
        """
        old_status = self.get_coin_status(coin)

        self.brain.blacklist_coin(coin, f"MANUAL: {reason}")
        self._status_cache[coin] = CoinStatus.BLACKLISTED

        adaptation = CoinAdaptation(
            coin=coin,
            timestamp=datetime.now(),
            old_status=old_status,
            new_status=CoinStatus.BLACKLISTED,
            reason=f"Manual blacklist: {reason}",
            trigger_stats={"manual": True}
        )

        self._log_adaptation(adaptation)
        logger.info(f"MANUAL BLACKLIST: {coin} - {reason}")

        return adaptation

    def force_unblacklist(self, coin: str) -> CoinAdaptation:
        """Manually remove a coin from blacklist.

        Args:
            coin: Coin symbol to unblacklist.

        Returns:
            CoinAdaptation record.
        """
        old_status = self.get_coin_status(coin)

        self.brain.unblacklist_coin(coin)

        # Recalculate status based on current score
        score = self.brain.get_coin_score(coin)
        if score:
            new_status = self._calculate_status(score)
        else:
            new_status = CoinStatus.UNKNOWN

        self._status_cache[coin] = new_status

        adaptation = CoinAdaptation(
            coin=coin,
            timestamp=datetime.now(),
            old_status=old_status,
            new_status=new_status,
            reason="Manual unblacklist",
            trigger_stats={"manual": True}
        )

        self._log_adaptation(adaptation)
        logger.info(f"MANUAL UNBLACKLIST: {coin} -> {new_status.value}")

        return adaptation

    def _log_adaptation(self, adaptation: CoinAdaptation) -> None:
        """Log adaptation to database if available."""
        if self.db:
            try:
                self.db.save_coin_adaptation(adaptation.to_dict())
            except Exception as e:
                logger.error(f"Failed to log adaptation: {e}")

    def get_all_statuses(self) -> Dict[str, CoinStatus]:
        """Get status for all known coins.

        Returns:
            Dictionary mapping coin symbols to their status.
        """
        result = {}
        for score in self.brain.get_all_coin_scores():
            result[score.coin] = self.get_coin_status(score.coin)
        return result

    def get_status_summary(self) -> Dict[str, Any]:
        """Get summary of coin statuses for dashboard.

        Returns:
            Dictionary with counts and lists by status.
        """
        statuses = self.get_all_statuses()

        summary = {
            "blacklisted": [],
            "reduced": [],
            "normal": [],
            "favored": [],
            "unknown": [],
        }

        for coin, status in statuses.items():
            summary[status.value].append(coin)

        return {
            "counts": {k: len(v) for k, v in summary.items()},
            "coins": summary,
        }
