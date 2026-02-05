"""
Quick Update - Instant post-trade knowledge updates.

TASK-130: Updates coin scores and pattern confidence immediately
after every trade closes. No LLM calls - pure math, must complete in <10ms.

Part of the two-tier Reflection Engine:
- Quick Update (this): After every trade, instant math
- Deep Reflection: Hourly, LLM-powered analysis
"""

import logging
import time
from typing import Optional

from src.coin_scorer import CoinScorer, CoinStatus
from src.database import Database
from src.models.quick_update import QuickUpdateResult, TradeResult
from src.pattern_library import PatternLibrary
from src.reflection import ReflectionEngine

logger = logging.getLogger(__name__)


class QuickUpdate:
    """Instant post-trade updates - no LLM, pure math.

    Called immediately after every trade closes to update:
    - Coin score (wins, losses, P&L, trend)
    - Pattern confidence (if pattern was used)
    - Adaptation triggers (blacklist, reduce, favor)

    Must complete in <10ms.

    Example:
        >>> quick = QuickUpdate(coin_scorer, pattern_library, db)
        >>> result = quick.process_trade_close(trade_result)
        >>> if result.coin_adaptation:
        ...     print(f"Adaptation triggered: {result.coin_adaptation}")
    """

    def __init__(
        self,
        coin_scorer: CoinScorer,
        pattern_library: Optional[PatternLibrary] = None,
        db: Optional[Database] = None,
        reflection_engine: Optional["ReflectionEngine"] = None,
    ):
        """Initialize QuickUpdate.

        Args:
            coin_scorer: CoinScorer for updating coin performance.
            pattern_library: Optional PatternLibrary for pattern confidence updates.
            db: Optional Database for activity logging.
            reflection_engine: Optional ReflectionEngine to notify of trades.
        """
        self.coin_scorer = coin_scorer
        self.pattern_library = pattern_library
        self.db = db
        self.reflection_engine = reflection_engine

        # Stats
        self.updates_processed = 0
        self.adaptations_triggered = 0
        self.patterns_updated = 0
        self.patterns_deactivated = 0

        logger.info("QuickUpdate initialized")

    def set_reflection_engine(self, engine: "ReflectionEngine") -> None:
        """Set the reflection engine (for late binding).

        Args:
            engine: ReflectionEngine to notify of trades.
        """
        self.reflection_engine = engine

    def process_trade_close(self, trade_result: TradeResult) -> QuickUpdateResult:
        """Process a completed trade and update all knowledge.

        This is the main entry point, called by Sniper after every trade closes.

        Args:
            trade_result: Trade outcome with coin, pnl, pattern_id, etc.

        Returns:
            QuickUpdateResult with any adaptations triggered.
        """
        start_time = time.perf_counter()

        # Initialize result
        result = QuickUpdateResult(
            trade_id=trade_result.trade_id,
            coin=trade_result.coin,
            won=trade_result.won,
            pnl_usd=trade_result.pnl_usd,
        )

        # 1. Update coin score
        coin_adaptation = self._update_coin_score(trade_result)
        if coin_adaptation:
            result.coin_adaptation = coin_adaptation.new_status.value.upper()
            result.coin_adaptation_reason = coin_adaptation.reason
            self.adaptations_triggered += 1

        # Get updated coin status
        status = self.coin_scorer.get_coin_status(trade_result.coin)
        result.new_coin_status = status.value

        # Get updated coin stats
        if self.coin_scorer.brain:
            score = self.coin_scorer.brain.get_coin_score(trade_result.coin)
            if score:
                result.new_coin_win_rate = score.win_rate
                result.new_coin_total_trades = score.total_trades

        # 2. Update pattern confidence (if pattern was used)
        if trade_result.pattern_id:
            pattern_update = self._update_pattern_confidence(trade_result)
            result.pattern_updated = True
            result.pattern_id = trade_result.pattern_id
            self.patterns_updated += 1

            if pattern_update and pattern_update.get("deactivated"):
                result.pattern_deactivated = True
                self.patterns_deactivated += 1

            if pattern_update and "new_confidence" in pattern_update:
                result.new_pattern_confidence = pattern_update["new_confidence"]

        # 3. Log activity
        self._log_quick_update(trade_result, result)

        # Calculate processing time
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        result.processing_time_ms = elapsed_ms

        self.updates_processed += 1

        # Log summary
        log_level = logging.INFO if coin_adaptation or result.pattern_deactivated else logging.DEBUG
        logger.log(log_level, f"Quick update: {result}")

        # 4. Notify reflection engine (TASK-131)
        if self.reflection_engine:
            self.reflection_engine.on_trade_close()

        return result

    def _update_coin_score(self, trade_result: TradeResult):
        """Update coin score and check thresholds.

        Args:
            trade_result: The completed trade.

        Returns:
            CoinAdaptation if threshold was crossed, else None.
        """
        # Build trade data for CoinScorer
        # CoinScorer expects dict with: coin, pnl_usd (or pnl), won (optional)
        trade_data = {
            "coin": trade_result.coin,
            "pnl_usd": trade_result.pnl_usd,
            "won": trade_result.won,
        }

        # Process through CoinScorer
        adaptation = self.coin_scorer.process_trade_result(trade_data)

        return adaptation

    def _update_pattern_confidence(self, trade_result: TradeResult) -> Optional[dict]:
        """Update pattern confidence if a pattern was used.

        Args:
            trade_result: The completed trade with pattern_id.

        Returns:
            Dict with update info, or None if no pattern library.
        """
        if not self.pattern_library or not trade_result.pattern_id:
            return None

        # Record the outcome
        self.pattern_library.record_pattern_outcome(
            pattern_id=trade_result.pattern_id,
            won=trade_result.won,
            pnl=trade_result.pnl_usd,
        )

        # Get updated pattern
        pattern = self.pattern_library.get_pattern(trade_result.pattern_id)
        if pattern:
            return {
                "new_confidence": pattern.confidence,
                "deactivated": not pattern.is_active,
            }

        return None

    def _log_quick_update(self, trade_result: TradeResult, result: QuickUpdateResult) -> None:
        """Log the quick update for audit trail.

        Args:
            trade_result: The original trade.
            result: The update result.
        """
        if not self.db:
            return

        import json

        details = {
            "trade_id": trade_result.trade_id,
            "coin": trade_result.coin,
            "won": trade_result.won,
            "pnl_usd": trade_result.pnl_usd,
            "exit_reason": trade_result.exit_reason,
            "pattern_id": trade_result.pattern_id,
            "coin_adaptation": result.coin_adaptation,
            "new_coin_status": result.new_coin_status,
            "new_coin_win_rate": result.new_coin_win_rate,
            "pattern_deactivated": result.pattern_deactivated,
            "processing_time_ms": result.processing_time_ms,
        }

        self.db.log_activity(
            activity_type="quick_update",
            description=f"Trade close: {trade_result.coin} {'WIN' if trade_result.won else 'LOSS'} ${trade_result.pnl_usd:+.2f}",
            details=json.dumps(details),
        )

    def get_stats(self) -> dict:
        """Get QuickUpdate statistics.

        Returns:
            Stats dictionary.
        """
        return {
            "updates_processed": self.updates_processed,
            "adaptations_triggered": self.adaptations_triggered,
            "patterns_updated": self.patterns_updated,
            "patterns_deactivated": self.patterns_deactivated,
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
    print("QuickUpdate Test")
    print("=" * 60)

    # Create temp database
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        from src.database import Database
        from src.knowledge import KnowledgeBrain
        from src.coin_scorer import CoinScorer
        from src.pattern_library import PatternLibrary

        db = Database(path)
        brain = KnowledgeBrain(db)
        scorer = CoinScorer(brain, db)
        patterns = PatternLibrary(brain)

        quick = QuickUpdate(scorer, patterns, db)

        # Test 1: Winning trade
        print("\n[TEST 1] Processing winning trade...")
        result = quick.process_trade_close(TradeResult(
            trade_id="test-001",
            coin="SOL",
            direction="LONG",
            entry_price=100.0,
            exit_price=102.0,
            position_size_usd=50.0,
            pnl_usd=1.0,
            won=True,
            exit_reason="take_profit",
        ))
        print(f"  Result: {result}")
        print(f"  Processing time: {result.processing_time_ms:.2f}ms")

        # Test 2: Multiple losing trades to trigger blacklist
        print("\n[TEST 2] Processing losing trades (triggering blacklist)...")
        for i in range(6):
            result = quick.process_trade_close(TradeResult(
                trade_id=f"test-loss-{i}",
                coin="SHIB",
                direction="LONG",
                entry_price=0.00001,
                exit_price=0.000009,
                position_size_usd=50.0,
                pnl_usd=-5.0,
                won=False,
                exit_reason="stop_loss",
            ))
            if result.coin_adaptation:
                print(f"  Trade {i+1}: {result}")
                break
            else:
                print(f"  Trade {i+1}: SHIB status = {result.new_coin_status}")

        # Verify blacklist
        status = scorer.get_coin_status("SHIB")
        print(f"  Final SHIB status: {status.value}")

        # Test 3: Trade with pattern
        print("\n[TEST 3] Processing trade with pattern...")
        # First create a pattern
        pattern = patterns.create_pattern(
            pattern_type="test_pattern",
            description="Test pattern for quick update",
            entry_conditions={"test": True},
            exit_conditions={"stop_loss_pct": 2.0},
        )

        result = quick.process_trade_close(TradeResult(
            trade_id="test-pattern-001",
            coin="ETH",
            direction="LONG",
            entry_price=2500.0,
            exit_price=2550.0,
            position_size_usd=50.0,
            pnl_usd=1.0,
            won=True,
            exit_reason="take_profit",
            pattern_id=pattern.pattern_id,
        ))
        print(f"  Result: {result}")
        print(f"  Pattern confidence: {result.new_pattern_confidence:.2f}")

        # Test 4: Performance test
        print("\n[TEST 4] Performance test (100 trades)...")
        start = time.perf_counter()
        for i in range(100):
            quick.process_trade_close(TradeResult(
                trade_id=f"perf-{i}",
                coin="BTC",
                direction="LONG",
                entry_price=45000.0,
                exit_price=45100.0,
                position_size_usd=50.0,
                pnl_usd=0.11,
                won=True,
                exit_reason="take_profit",
            ))
        elapsed = time.perf_counter() - start
        print(f"  100 updates in {elapsed*1000:.1f}ms ({elapsed*10:.2f}ms per update)")

        # Print stats
        print("\n" + "-" * 40)
        print("Stats:")
        for k, v in quick.get_stats().items():
            print(f"  {k}: {v}")

        print("\n" + "=" * 60)
        print("All QuickUpdate Tests PASSED!")
        print("=" * 60)

    finally:
        os.unlink(path)
