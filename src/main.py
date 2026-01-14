#!/usr/bin/env python3
"""Main trading bot - the 24/7 autonomous trading loop.

This is the heart of the self-learning trading bot. It connects ALL components:
- Market data fetching (CoinGecko)
- Position management (stop loss / take profit)
- LLM decision making (with learnings and rules)
- Trade execution (paper trading)
- Post-trade learning (analysis and rule creation)

The bot runs continuously, making decisions every 30 seconds.
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import Database
from src.market_data import MarketDataFetcher, format_price
from src.trading_engine import TradingEngine
from src.learning_system import LearningSystem, RuleManager, get_learnings_as_text, get_rules_as_text
from src.llm_interface import LLMInterface
from src.risk_manager import RiskManager
from src.coin_config import get_coin_ids, get_tier, get_tier_config

# =============================================================================
# CONFIGURATION - All configurable parameters in one place
# =============================================================================

LOOP_INTERVAL = int(os.environ.get("LOOP_INTERVAL", 30))  # seconds
MIN_CONFIDENCE = float(os.environ.get("MIN_CONFIDENCE", 0.3))  # 30% minimum for aggressive learning
MAX_TRADES_PER_CYCLE = 5  # Allow multiple trades per cycle for faster learning
# Coins are now loaded from coin_config (45 coins across 3 tiers)

# Configure logging - summary to console, details to file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Suppress verbose logging from other modules in console
logging.getLogger('src.database').setLevel(logging.WARNING)
logging.getLogger('src.market_data').setLevel(logging.WARNING)
logging.getLogger('src.trading_engine').setLevel(logging.WARNING)
logging.getLogger('src.learning_system').setLevel(logging.WARNING)
logging.getLogger('src.llm_interface').setLevel(logging.WARNING)
logging.getLogger('src.risk_manager').setLevel(logging.WARNING)


class TradingBot:
    """Main trading bot that runs the 24/7 autonomous loop.

    This class integrates all components and runs the main trading cycle:
    1. Fetch market data
    2. Update open positions (check stop loss / take profit)
    3. Analyze any closed trades (create learnings)
    4. Query LLM for trading decision
    5. Execute trades if valid
    6. Log everything
    """

    def __init__(self):
        """Initialize all bot components."""
        print("\n" + "=" * 64)
        print("  INITIALIZING TRADING BOT")
        print("=" * 64)

        # Core components
        self.db = Database()
        self.llm = LLMInterface(db=self.db)
        self.market_data = MarketDataFetcher(db=self.db)
        self.risk_manager = RiskManager(db=self.db)
        self.trading_engine = TradingEngine(db=self.db, risk_manager=self.risk_manager)
        self.learning_system = LearningSystem(db=self.db, llm=self.llm)
        self.rule_manager = RuleManager(db=self.db, llm=self.llm)

        # State
        self.running = False
        self.cycle_count = 0
        self.trades_opened = 0
        self.trades_closed = 0
        self.start_time = None

        # Test LLM connection
        print("\n  Testing LLM connection...")
        if self.llm.test_connection():
            print("  ✓ LLM connected successfully")
        else:
            print("  ⚠ LLM not available - bot will default to HOLD")

        # Get coin counts by tier
        all_coins = get_coin_ids()
        tier_counts = {1: 0, 2: 0, 3: 0}
        for coin in all_coins:
            tier_counts[get_tier(coin)] += 1

        print("\n  Configuration:")
        print(f"    Loop interval: {LOOP_INTERVAL}s")
        print(f"    Min confidence: {MIN_CONFIDENCE:.0%}")
        print(f"    Max trades/cycle: {MAX_TRADES_PER_CYCLE}")
        print(f"    Coins: {len(all_coins)} total (T1:{tier_counts[1]} T2:{tier_counts[2]} T3:{tier_counts[3]})")

        # Log initialization
        self.db.log_activity(
            "bot_initialized",
            "Trading bot initialized",
            f"interval={LOOP_INTERVAL}s, min_confidence={MIN_CONFIDENCE}"
        )

    def run(self):
        """Main loop - runs until stopped."""
        self.running = True
        self.start_time = datetime.now()

        # Get initial account state
        account = self.db.get_account_state()

        print("\n" + "=" * 64)
        print(f"  TRADING BOT STARTED - {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Balance: ${account['balance']:.2f} | Model: {self.llm.model}")
        print("=" * 64 + "\n")

        self.db.log_activity("bot_started", f"Bot started with balance ${account['balance']:.2f}")

        try:
            while self.running:
                self.run_cycle()

                if self.running:  # Check again in case stopped during cycle
                    time.sleep(LOOP_INTERVAL)

        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}")
            self.db.log_activity("bot_error", f"Fatal error: {str(e)}")
            raise
        finally:
            self._print_summary()

    def run_cycle(self):
        """Execute a single trading cycle."""
        self.cycle_count += 1
        cycle_start = datetime.now()

        print(f"[{cycle_start.strftime('%H:%M:%S')}] Cycle #{self.cycle_count} starting...")

        try:
            # Step 1: Fetch market data
            prices = self._fetch_market_data()
            if not prices:
                print(f"[{cycle_start.strftime('%H:%M:%S')}] ⚠ Market data fetch failed, skipping cycle")
                return

            # Step 2: Update positions (may close trades)
            closed_trades = self._update_positions()

            # Step 3: Analyze any closed trades
            if closed_trades:
                self._analyze_closed_trades(closed_trades)

            # Step 4: Get LLM decision
            decision = self._get_trading_decision(prices)

            # Step 5: Execute if valid
            if decision:
                self._execute_decision(decision)

            # Step 6: Log cycle completion
            elapsed = (datetime.now() - cycle_start).total_seconds()
            account = self.db.get_account_state()

            # Summary line for console
            action_str = decision.get('action', 'HOLD') if decision else 'HOLD'
            confidence_str = f"{decision.get('confidence', 0):.0%}" if decision else "N/A"

            print(f"[{cycle_start.strftime('%H:%M:%S')}] ✓ Cycle #{self.cycle_count} complete "
                  f"| {action_str} ({confidence_str}) "
                  f"| Balance: ${account['balance']:.2f} "
                  f"| {elapsed:.1f}s")

        except Exception as e:
            logger.error(f"Error in cycle #{self.cycle_count}: {e}")
            self.db.log_activity("cycle_error", f"Cycle #{self.cycle_count} error: {str(e)}")
            print(f"[{cycle_start.strftime('%H:%M:%S')}] ✗ Cycle #{self.cycle_count} error: {e}")

    def _fetch_market_data(self) -> Optional[Dict[str, float]]:
        """Fetch latest market data from CoinGecko using batch API."""
        try:
            # Batch fetch all coins with volume filtering
            stats = self.market_data.update_all_prices()

            if stats['updated'] == 0:
                logger.warning("No coins updated")
                return None

            # Get tradeable coins (those that passed volume filter)
            tradeable = self.market_data.get_tradeable_coins()

            # Get prices from database
            prices = {}
            for coin in tradeable:
                price = self.trading_engine.get_current_price(coin)
                if price:
                    prices[coin] = price

            if prices:
                # Show top movers (sorted by absolute 24h change)
                with self.db._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT coin, change_24h FROM market_data
                        ORDER BY ABS(change_24h) DESC LIMIT 3
                    """)
                    top_movers = cursor.fetchall()

                mover_str = " | ".join([f"{c[:4].upper()}: {ch:+.1f}%" for c, ch in top_movers])
                logger.info(f"Updated {len(prices)} coins | Top movers: {mover_str}")
                return prices

            return None

        except Exception as e:
            logger.warning(f"Market data fetch failed: {e}")
            return None

    def _update_positions(self) -> List[Dict[str, Any]]:
        """Update open positions and check stop loss / take profit."""
        closed = self.trading_engine.update_positions()

        open_trades = self.trading_engine.get_open_trades()

        if closed:
            self.trades_closed += len(closed)
            for trade in closed:
                pnl_sign = "+" if trade['pnl_usd'] >= 0 else ""
                print(f"         ⚡ Trade closed: {trade['coin']} {pnl_sign}${trade['pnl_usd']:.2f} ({trade['reason']})")

        logger.info(f"Positions: {len(open_trades)} open, {len(closed)} closed this cycle")
        return closed

    def _analyze_closed_trades(self, closed_trades: List[Dict[str, Any]]):
        """Analyze closed trades to create learnings and rules."""
        for trade in closed_trades:
            trade_id = trade['trade_id']

            # Analyze trade with LLM
            learning = self.learning_system.analyze_trade(trade_id)

            if learning:
                print(f"         📚 Learning created: {learning.lesson[:50]}... ({learning.confidence:.0%})")

                # Try to create rule from high-confidence learning
                if learning.confidence >= 0.7:
                    rule = self.rule_manager.create_rule_from_learning(learning)
                    if rule:
                        print(f"         📋 Rule created: {rule.rule_text[:50]}...")

    def _get_trading_decision(self, prices: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """Query LLM for a trading decision."""
        # Build context for LLM
        account = self.db.get_account_state()
        open_trades = self.trading_engine.get_open_trades()
        learnings = get_learnings_as_text(db=self.db, limit=5)
        active_rules = get_rules_as_text(db=self.db)

        # Build market data dict from all tradeable coins
        market_data = {}
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT coin, price_usd, change_24h
                FROM market_data
                WHERE last_updated > datetime('now', '-5 minutes')
            """)
            for row in cursor.fetchall():
                coin, price, change = row
                market_data[coin] = {
                    "price_usd": price,
                    "change_24h": change or 0,
                    "tier": get_tier(coin)
                }

        # Build account state dict
        account_state = {
            "balance": account['balance'],
            "available_balance": account['available_balance'],
            "in_positions": account['in_positions'],
            "daily_pnl": account['daily_pnl'],
            "open_trades": len(open_trades),
            "trade_count_today": account['trade_count_today']
        }

        # Get decision from LLM
        decision = self.llm.get_trading_decision(
            market_data=market_data,
            account_state=account_state,
            recent_learnings=learnings,
            active_rules=active_rules
        )

        if decision is None:
            logger.warning("LLM returned no decision, defaulting to HOLD")
            return {"action": "HOLD", "confidence": 0, "reason": "LLM unavailable"}

        # Log the decision details to activity_log (detailed logging)
        self.db.log_activity(
            "llm_decision",
            f"{decision.get('action', 'HOLD')} (confidence: {decision.get('confidence', 0):.2f})",
            json.dumps(decision)
        )

        return decision

    def _execute_decision(self, decision: Dict[str, Any]):
        """Execute a trading decision if valid."""
        action = decision.get('action', 'HOLD')
        confidence = decision.get('confidence', 0)
        coin = decision.get('coin')
        size_usd = decision.get('size_usd')
        reason = decision.get('reason', 'No reason provided')
        rules_applied = decision.get('rules_applied', [])

        # Check confidence threshold
        if confidence < MIN_CONFIDENCE:
            logger.info(f"Decision {action} rejected: confidence {confidence:.0%} < {MIN_CONFIDENCE:.0%}")
            self.db.log_activity(
                "decision_rejected",
                f"{action} rejected: low confidence ({confidence:.0%})",
                reason
            )
            return

        # Only execute BUY orders for now (no shorting in Phase 1)
        if action == "BUY" and coin and size_usd:
            # Ensure we don't exceed max trades per cycle
            # (In practice, we only make one decision per cycle anyway)

            # Convert rules_applied to list of ints
            rule_ids = None
            if rules_applied:
                try:
                    rule_ids = [int(r) for r in rules_applied if r]
                except (ValueError, TypeError):
                    rule_ids = None

            result = self.trading_engine.execute_buy(
                coin=coin,
                size_usd=size_usd,
                reason=reason,
                rule_ids=rule_ids
            )

            if result.success:
                self.trades_opened += 1
                print(f"         💰 Trade opened: {coin.upper()} ${size_usd:.2f} ({reason[:30]}...)")
            else:
                print(f"         ⚠ Trade rejected: {result.message}")

        elif action == "SELL":
            # For Phase 1, SELL means close an existing position
            open_trades = self.trading_engine.get_open_trades()
            if coin:
                # Find trade for this coin
                for trade in open_trades:
                    if trade['coin_name'] == coin:
                        result = self.trading_engine.close_trade(trade['id'], f"llm_sell: {reason}")
                        if result.success:
                            self.trades_closed += 1
                            print(f"         💰 Trade closed: {coin.upper()} ({reason[:30]}...)")
                        break

        # HOLD - do nothing
        elif action == "HOLD":
            logger.info(f"HOLD decision: {reason}")

    def stop(self):
        """Graceful shutdown."""
        print("\n\n[Shutdown signal received]")
        self.running = False
        self.db.log_activity("bot_stopping", "Bot received shutdown signal")

    def _print_summary(self):
        """Print final summary when bot stops."""
        if self.start_time is None:
            return

        runtime = datetime.now() - self.start_time
        account = self.db.get_account_state()

        print("\n" + "=" * 64)
        print("  BOT STOPPED")
        print("=" * 64)
        print(f"  Runtime: {runtime}")
        print(f"  Total cycles: {self.cycle_count}")
        print(f"  Trades opened: {self.trades_opened}")
        print(f"  Trades closed: {self.trades_closed}")
        print(f"  Final balance: ${account['balance']:.2f}")
        print(f"  Total P&L: ${account['total_pnl']:.2f}")
        print("=" * 64 + "\n")

        self.db.log_activity(
            "bot_stopped",
            f"Bot stopped after {self.cycle_count} cycles",
            f"runtime={runtime}, trades_opened={self.trades_opened}, trades_closed={self.trades_closed}"
        )


def main():
    """Main entry point."""
    print("\n" + "=" * 64)
    print("  CRYPTO TRADING BOT")
    print("  Self-Learning Autonomous Trading System")
    print("=" * 64)

    # Create bot
    bot = TradingBot()

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        bot.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the bot
    try:
        bot.run()
    except KeyboardInterrupt:
        pass  # Already handled by signal handler
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise


if __name__ == "__main__":
    main()
