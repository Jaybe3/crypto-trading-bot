"""Knowledge Brain - The bot's accumulated trading wisdom.

Provides read/write access to learned knowledge:
- Coin performance scores
- Trading patterns
- Regime rules
- Blacklist

All data persists to SQLite database.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from src.database import Database
from src.models.knowledge import CoinScore, TradingPattern, RegimeRule

logger = logging.getLogger(__name__)


class KnowledgeBrain:
    """The bot's accumulated trading wisdom.

    Manages coin scores, trading patterns, and regime rules.
    The Strategist reads from this to make informed decisions.
    The Reflection Engine writes to update knowledge based on trade outcomes.

    Example:
        >>> db = Database(":memory:")
        >>> brain = KnowledgeBrain(db)
        >>> brain.update_coin_score("SOL", {"won": True, "pnl": 5.0})
        >>> score = brain.get_coin_score("SOL")
        >>> print(f"SOL win rate: {score.win_rate:.1%}")
    """

    def __init__(self, db: Database):
        """Initialize Knowledge Brain with database connection.

        Args:
            db: Database instance for persistence.
        """
        self.db = db
        self._coin_scores: Dict[str, CoinScore] = {}
        self._patterns: Dict[str, TradingPattern] = {}
        self._regime_rules: Dict[str, RegimeRule] = {}
        self._load_from_db()
        logger.info(f"KnowledgeBrain initialized: {len(self._coin_scores)} coins, "
                   f"{len(self._patterns)} patterns, {len(self._regime_rules)} rules")

    def _load_from_db(self) -> None:
        """Load all knowledge data from database."""
        # Load coin scores
        for row in self.db.get_all_coin_scores():
            score = CoinScore.from_dict(row)
            self._coin_scores[score.coin] = score

        # Load patterns
        for row in self.db.get_active_patterns():
            pattern = TradingPattern.from_dict(row)
            self._patterns[pattern.pattern_id] = pattern

        # Load rules
        for row in self.db.get_active_rules():
            rule = RegimeRule.from_dict(row)
            self._regime_rules[rule.rule_id] = rule

    # ========== Coin Scores ==========

    def get_coin_score(self, coin: str) -> Optional[CoinScore]:
        """Get performance score for a specific coin.

        Args:
            coin: Coin symbol (e.g., "SOL").

        Returns:
            CoinScore or None if no data exists for this coin.
        """
        return self._coin_scores.get(coin)

    def get_all_coin_scores(self) -> List[CoinScore]:
        """Get all coin scores sorted by total P&L.

        Returns:
            List of CoinScore objects.
        """
        return sorted(
            self._coin_scores.values(),
            key=lambda s: s.total_pnl,
            reverse=True
        )

    def update_coin_score(self, coin: str, trade_result: Dict[str, Any]) -> CoinScore:
        """Update coin score with a new trade result.

        Args:
            coin: Coin symbol.
            trade_result: Dictionary with "won" (bool) and "pnl" (float) keys.

        Returns:
            Updated CoinScore.
        """
        won = trade_result["won"]
        pnl = trade_result["pnl"]

        if coin not in self._coin_scores:
            self._coin_scores[coin] = CoinScore(coin=coin)

        score = self._coin_scores[coin]
        score.total_trades += 1
        score.total_pnl += pnl

        if won:
            score.wins += 1
            # Update running average for winners
            if score.wins == 1:
                score.avg_winner = pnl
            else:
                score.avg_winner = ((score.avg_winner * (score.wins - 1)) + pnl) / score.wins
        else:
            score.losses += 1
            # Update running average for losers
            if score.losses == 1:
                score.avg_loser = pnl
            else:
                score.avg_loser = ((score.avg_loser * (score.losses - 1)) + pnl) / score.losses

        score.recalculate_stats()
        score.last_updated = datetime.now()

        # Update trend based on recent performance
        score.trend = self._calculate_trend(score)

        # Persist to database
        self.db.save_coin_score(score.to_dict())

        logger.debug(f"Updated {coin} score: {score.total_trades} trades, "
                    f"{score.win_rate:.1%} win rate, ${score.total_pnl:.2f} total P&L")

        return score

    def _calculate_trend(self, score: CoinScore) -> str:
        """Calculate trend for a coin based on recent performance.

        Args:
            score: The coin score to analyze.

        Returns:
            "improving", "degrading", or "stable"
        """
        # Simple heuristic: compare recent performance to overall
        # This will be enhanced when we have more historical data
        if score.total_trades < 5:
            return "stable"

        # For now, base it on win rate thresholds
        if score.win_rate >= 0.6:
            return "improving"
        elif score.win_rate <= 0.35:
            return "degrading"
        return "stable"

    def get_good_coins(self, min_trades: int = 5, min_win_rate: float = 0.5) -> List[str]:
        """Get coins with good performance.

        Args:
            min_trades: Minimum trades required for evaluation.
            min_win_rate: Minimum win rate to be considered "good".

        Returns:
            List of coin symbols meeting criteria.
        """
        return [
            score.coin for score in self._coin_scores.values()
            if score.total_trades >= min_trades
            and score.win_rate >= min_win_rate
            and not score.is_blacklisted
        ]

    def get_bad_coins(self, min_trades: int = 5, max_win_rate: float = 0.35) -> List[str]:
        """Get coins with poor performance.

        Args:
            min_trades: Minimum trades required for evaluation.
            max_win_rate: Maximum win rate to be considered "bad".

        Returns:
            List of coin symbols meeting criteria.
        """
        return [
            score.coin for score in self._coin_scores.values()
            if score.total_trades >= min_trades
            and score.win_rate <= max_win_rate
            and not score.is_blacklisted  # Already blacklisted coins separate
        ]

    # ========== Blacklist ==========

    def blacklist_coin(self, coin: str, reason: str) -> None:
        """Blacklist a coin to prevent trading.

        Args:
            coin: Coin symbol to blacklist.
            reason: Reason for blacklisting.
        """
        if coin not in self._coin_scores:
            self._coin_scores[coin] = CoinScore(coin=coin)

        score = self._coin_scores[coin]
        score.is_blacklisted = True
        score.blacklist_reason = reason
        score.last_updated = datetime.now()

        self.db.save_coin_score(score.to_dict())
        logger.info(f"Blacklisted {coin}: {reason}")

    def unblacklist_coin(self, coin: str) -> None:
        """Remove a coin from the blacklist.

        Args:
            coin: Coin symbol to unblacklist.
        """
        if coin in self._coin_scores:
            score = self._coin_scores[coin]
            score.is_blacklisted = False
            score.blacklist_reason = ""
            score.last_updated = datetime.now()

            self.db.save_coin_score(score.to_dict())
            logger.info(f"Unblacklisted {coin}")

    def favor_coin(self, coin: str, reason: str) -> None:
        """Mark a coin as favored (high performer).

        Favored coins get priority from the Strategist when generating conditions.
        This is the opposite of blacklisting - we want to trade these more.

        Args:
            coin: Coin symbol to favor.
            reason: Reason for favoring (from insight).
        """
        if coin not in self._coin_scores:
            self._coin_scores[coin] = CoinScore(coin=coin)

        score = self._coin_scores[coin]
        # Mark as improving trend (the closest we have to "favored" status)
        score.trend = "improving"
        score.last_updated = datetime.now()

        self.db.save_coin_score(score.to_dict())
        logger.info(f"Favored {coin}: {reason}")

    def get_blacklisted_coins(self) -> List[str]:
        """Get list of blacklisted coin symbols.

        Returns:
            List of blacklisted coin symbols.
        """
        return [
            score.coin for score in self._coin_scores.values()
            if score.is_blacklisted
        ]

    def is_blacklisted(self, coin: str) -> bool:
        """Check if a coin is blacklisted.

        Args:
            coin: Coin symbol to check.

        Returns:
            True if coin is blacklisted.
        """
        score = self._coin_scores.get(coin)
        return score.is_blacklisted if score else False

    # ========== Trading Patterns ==========

    def get_pattern(self, pattern_id: str) -> Optional[TradingPattern]:
        """Get a trading pattern by ID.

        Args:
            pattern_id: Pattern identifier.

        Returns:
            TradingPattern or None if not found.
        """
        return self._patterns.get(pattern_id)

    def get_active_patterns(self) -> List[TradingPattern]:
        """Get all active trading patterns.

        Returns:
            List of active TradingPattern objects.
        """
        return [p for p in self._patterns.values() if p.is_active]

    def add_pattern(self, pattern: TradingPattern) -> None:
        """Add a new trading pattern.

        Args:
            pattern: TradingPattern to add.
        """
        self._patterns[pattern.pattern_id] = pattern
        self.db.save_pattern(pattern.to_dict())
        logger.info(f"Added pattern: {pattern.pattern_id} - {pattern.description}")

    def update_pattern_stats(self, pattern_id: str, won: bool, pnl: float) -> None:
        """Update pattern statistics after a trade.

        Args:
            pattern_id: Pattern identifier.
            won: Whether the trade was a winner.
            pnl: P&L from the trade.
        """
        if pattern_id not in self._patterns:
            logger.warning(f"Pattern {pattern_id} not found for stats update")
            return

        pattern = self._patterns[pattern_id]
        pattern.times_used += 1
        pattern.total_pnl += pnl
        if won:
            pattern.wins += 1
        else:
            pattern.losses += 1
        pattern.last_used = datetime.now()

        # Update confidence based on performance
        if pattern.times_used >= 5:
            pattern.confidence = min(0.9, max(0.1, pattern.win_rate))

        self.db.save_pattern(pattern.to_dict())
        logger.debug(f"Updated pattern {pattern_id}: {pattern.times_used} uses, "
                    f"{pattern.win_rate:.1%} win rate")

    def deactivate_pattern(self, pattern_id: str) -> None:
        """Deactivate a pattern (stop using it).

        Args:
            pattern_id: Pattern identifier.
        """
        if pattern_id in self._patterns:
            self._patterns[pattern_id].is_active = False
            self.db.deactivate_pattern(pattern_id)
            logger.info(f"Deactivated pattern: {pattern_id}")

    def reactivate_pattern(self, pattern_id: str) -> None:
        """Reactivate a previously deactivated pattern.

        Used for rollback of harmful deactivation adaptations.

        Args:
            pattern_id: Pattern identifier.
        """
        if pattern_id in self._patterns:
            self._patterns[pattern_id].is_active = True
            # Save to database
            self.db.save_pattern(self._patterns[pattern_id].to_dict())
            logger.info(f"Reactivated pattern: {pattern_id}")
        else:
            # Try to load from database
            pattern_data = self.db.get_pattern(pattern_id)
            if pattern_data:
                pattern = TradingPattern.from_dict(pattern_data)
                pattern.is_active = True
                self._patterns[pattern_id] = pattern
                self.db.save_pattern(pattern.to_dict())
                logger.info(f"Reactivated pattern from database: {pattern_id}")
            else:
                logger.warning(f"Pattern {pattern_id} not found for reactivation")

    def get_winning_patterns(
        self,
        min_uses: int = 5,
        min_win_rate: float = 0.55
    ) -> List[TradingPattern]:
        """Get patterns with proven track records.

        Args:
            min_uses: Minimum times used for evaluation.
            min_win_rate: Minimum win rate to be considered "winning".

        Returns:
            List of winning patterns sorted by confidence.
        """
        winning = [
            p for p in self._patterns.values()
            if p.is_active
            and p.times_used >= min_uses
            and p.win_rate >= min_win_rate
        ]
        return sorted(winning, key=lambda p: p.confidence, reverse=True)

    # ========== Regime Rules ==========

    def get_active_rules(self) -> List[RegimeRule]:
        """Get all active regime rules.

        Returns:
            List of active RegimeRule objects.
        """
        return [r for r in self._regime_rules.values() if r.is_active]

    def add_rule(self, rule: RegimeRule) -> None:
        """Add a new regime rule.

        Args:
            rule: RegimeRule to add.
        """
        self._regime_rules[rule.rule_id] = rule
        self.db.save_rule(rule.to_dict())
        logger.info(f"Added rule: {rule.rule_id} - {rule.description}")

    def update_rule_stats(
        self,
        rule_id: str,
        triggered: bool,
        saved_pnl: float = 0.0
    ) -> None:
        """Update rule statistics after evaluation.

        Args:
            rule_id: Rule identifier.
            triggered: Whether the rule was triggered.
            saved_pnl: Estimated P&L saved by following this rule.
        """
        if rule_id not in self._regime_rules:
            logger.warning(f"Rule {rule_id} not found for stats update")
            return

        if triggered:
            rule = self._regime_rules[rule_id]
            rule.times_triggered += 1
            rule.estimated_saves += saved_pnl
            self.db.update_rule_stats(rule_id, saved_pnl)
            logger.debug(f"Rule {rule_id} triggered, estimated save: ${saved_pnl:.2f}")

    def deactivate_rule(self, rule_id: str) -> None:
        """Deactivate a regime rule.

        Args:
            rule_id: Rule identifier.
        """
        if rule_id in self._regime_rules:
            self._regime_rules[rule_id].is_active = False
            self.db.deactivate_rule(rule_id)
            logger.info(f"Deactivated rule: {rule_id}")

    def check_rules(self, market_state: Dict[str, Any]) -> List[str]:
        """Check all active rules against current market state.

        Args:
            market_state: Dictionary of current market conditions.

        Returns:
            List of actions from triggered rules (e.g., ["NO_TRADE", "REDUCE_SIZE"]).
        """
        actions = []
        for rule in self.get_active_rules():
            if rule.check_condition(market_state):
                actions.append(rule.action)
                logger.info(f"Rule triggered: {rule.description} -> {rule.action}")
        return actions

    # ========== Strategist Interface ==========

    def get_knowledge_context(self) -> Dict[str, Any]:
        """Get summarized knowledge for Strategist prompts.

        Returns:
            Dictionary with categorized knowledge for LLM context.
        """
        return {
            "good_coins": self.get_good_coins(),
            "avoid_coins": self.get_blacklisted_coins() + self.get_bad_coins(),
            "active_rules": [r.description for r in self.get_active_rules()],
            "winning_patterns": [p.description for p in self.get_winning_patterns()],
        }

    def get_coin_summary(self, coin: str) -> Optional[Dict[str, Any]]:
        """Get human-readable summary for a coin.

        Args:
            coin: Coin symbol.

        Returns:
            Summary dictionary or None if no data.
        """
        score = self.get_coin_score(coin)
        if not score:
            return None

        return {
            "coin": score.coin,
            "trades": score.total_trades,
            "win_rate": f"{score.win_rate:.1%}",
            "total_pnl": f"${score.total_pnl:.2f}",
            "avg_winner": f"${score.avg_winner:.2f}",
            "avg_loser": f"${score.avg_loser:.2f}",
            "trend": score.trend,
            "status": "BLACKLISTED" if score.is_blacklisted else "ACTIVE",
        }

    def get_stats_summary(self) -> Dict[str, Any]:
        """Get overall knowledge brain statistics.

        Returns:
            Dictionary with summary statistics.
        """
        total_coins = len(self._coin_scores)
        blacklisted = len(self.get_blacklisted_coins())
        good = len(self.get_good_coins())
        bad = len(self.get_bad_coins())

        total_patterns = len(self._patterns)
        active_patterns = len(self.get_active_patterns())
        winning_patterns = len(self.get_winning_patterns())

        total_rules = len(self._regime_rules)
        active_rules = len(self.get_active_rules())

        return {
            "coins": {
                "total": total_coins,
                "good": good,
                "bad": bad,
                "blacklisted": blacklisted,
            },
            "patterns": {
                "total": total_patterns,
                "active": active_patterns,
                "winning": winning_patterns,
            },
            "rules": {
                "total": total_rules,
                "active": active_rules,
            },
        }
