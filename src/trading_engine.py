"""Paper trading execution logic.

Simulates buying and selling crypto, recording all trades in the database.
All prices come from real market data - no simulated prices allowed.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.database import Database
from src.risk_manager import RiskManager
from src.learning_system import RuleManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TradeResult:
    """Result of a trade execution attempt."""
    success: bool
    trade_id: Optional[int]
    message: str


class TradingEngine:
    """Executes paper trades and manages positions.

    All trades use REAL prices from the market_data table.
    No simulated or manual prices are allowed.
    """

    def __init__(self, db: Database = None, risk_manager: RiskManager = None):
        """Initialize with database and risk manager.

        Args:
            db: Database instance. If None, creates new connection.
            risk_manager: RiskManager instance. If None, creates new one.
        """
        self.db = db or Database()
        self.risk_manager = risk_manager or RiskManager(db=self.db)
        self.rule_manager = RuleManager(db=self.db, llm=None)
        logger.info("TradingEngine initialized")

    def get_current_price(self, coin: str) -> Optional[float]:
        """Get current price for a coin from market_data table.

        Args:
            coin: Cryptocurrency name (e.g., 'bitcoin').

        Returns:
            Current price in USD, or None if no data exists.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT price_usd FROM market_data WHERE coin = ?",
                (coin,)
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def execute_buy(
        self,
        coin: str,
        size_usd: float,
        reason: str,
        rule_ids: Optional[List[int]] = None
    ) -> TradeResult:
        """Execute a paper BUY order.

        Args:
            coin: Cryptocurrency to buy (e.g., 'bitcoin').
            size_usd: Size of trade in USD.
            reason: Reason for entering the trade.
            rule_ids: List of rule IDs that influenced this trade (for tracking).

        Returns:
            TradeResult with success status, trade_id, and message.
        """
        logger.info(f"Attempting BUY: {coin} ${size_usd:.2f} - {reason}")

        # Step 1: Get current price from market_data (MUST exist)
        current_price = self.get_current_price(coin)
        if current_price is None:
            message = f"No market data for {coin}. Cannot execute trade without real price."
            logger.warning(message)
            self.db.log_activity("trade_rejected", message)
            return TradeResult(success=False, trade_id=None, message=message)

        # Step 2: Validate with RiskManager (REJECT if invalid, don't auto-reduce)
        validation = self.risk_manager.validate_trade(coin, size_usd, "BUY")
        if not validation.valid:
            logger.warning(f"Trade rejected: {validation.reason}")
            self.db.log_activity("trade_rejected", f"BUY {coin} ${size_usd:.2f}: {validation.reason}")
            return TradeResult(success=False, trade_id=None, message=validation.reason)

        # Step 3: Calculate stop loss and take profit
        stop_loss_price = self.risk_manager.calculate_stop_loss(current_price)
        take_profit_price = self.risk_manager.calculate_take_profit(current_price, size_usd)

        # Step 4: Insert into open_trades
        rule_ids_str = ','.join(str(r) for r in rule_ids) if rule_ids else None

        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO open_trades (
                    coin_name, entry_price, size_usd, current_price,
                    unrealized_pnl, unrealized_pnl_pct, stop_loss_price,
                    take_profit_price, entry_reason, opened_at, rule_ids_used
                ) VALUES (?, ?, ?, ?, 0, 0, ?, ?, ?, datetime('now'), ?)
            """, (
                coin, current_price, size_usd, current_price,
                stop_loss_price, take_profit_price, reason, rule_ids_str
            ))

            trade_id = cursor.lastrowid

            # Step 5: Update account_state
            cursor.execute("""
                UPDATE account_state SET
                    available_balance = available_balance - ?,
                    in_positions = in_positions + ?
                WHERE id = 1
            """, (size_usd, size_usd))

            conn.commit()

        # Step 6: Log activity
        self.db.log_activity(
            "trade_opened",
            f"BUY {coin} ${size_usd:.2f} @ ${current_price:.2f}",
            f"trade_id={trade_id}, stop_loss=${stop_loss_price:.2f}, take_profit=${take_profit_price:.2f}"
        )

        message = f"Opened trade #{trade_id}: BUY {coin} ${size_usd:.2f} @ ${current_price:.2f}"
        logger.info(message)

        return TradeResult(success=True, trade_id=trade_id, message=message)

    def close_trade(self, trade_id: int, exit_reason: str) -> TradeResult:
        """Close an open trade.

        Args:
            trade_id: ID of the trade to close.
            exit_reason: Reason for closing (e.g., 'stop_loss', 'take_profit', 'manual').

        Returns:
            TradeResult with success status and message.
        """
        logger.info(f"Attempting to close trade #{trade_id}: {exit_reason}")

        # Step 1: Get trade from open_trades
        trade = self.get_trade_by_id(trade_id)
        if trade is None:
            message = f"Trade #{trade_id} not found in open_trades"
            logger.warning(message)
            return TradeResult(success=False, trade_id=trade_id, message=message)

        # Step 2: Get current price
        current_price = self.get_current_price(trade['coin_name'])
        if current_price is None:
            # Use the last known current_price from the trade record
            current_price = trade['current_price']
            logger.warning(f"No market data for {trade['coin_name']}, using last known price ${current_price:.2f}")

        # Step 3: Calculate final P&L
        entry_price = trade['entry_price']
        size_usd = trade['size_usd']
        price_change_pct = (current_price - entry_price) / entry_price
        pnl_usd = size_usd * price_change_pct
        pnl_pct = price_change_pct * 100

        # Step 4: Calculate duration
        opened_at = datetime.fromisoformat(trade['opened_at'].replace(' ', 'T'))
        closed_at = datetime.now()
        duration_seconds = int((closed_at - opened_at).total_seconds())

        # Step 5: Move from open_trades to closed_trades
        rule_ids_used = trade.get('rule_ids_used')

        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # Insert into closed_trades (including rule_ids_used)
            cursor.execute("""
                INSERT INTO closed_trades (
                    coin_name, entry_price, exit_price, size_usd,
                    pnl_usd, pnl_pct, entry_reason, exit_reason,
                    opened_at, closed_at, duration_seconds, rule_ids_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?)
            """, (
                trade['coin_name'], entry_price, current_price, size_usd,
                pnl_usd, pnl_pct, trade['entry_reason'], exit_reason,
                trade['opened_at'], duration_seconds, rule_ids_used
            ))

            # Delete from open_trades
            cursor.execute("DELETE FROM open_trades WHERE id = ?", (trade_id,))

            # Update account_state
            # Balance changes by P&L, available_balance gets size back + P&L
            cursor.execute("""
                UPDATE account_state SET
                    balance = balance + ?,
                    available_balance = available_balance + ? + ?,
                    in_positions = in_positions - ?,
                    total_pnl = total_pnl + ?,
                    daily_pnl = daily_pnl + ?,
                    trade_count_today = trade_count_today + 1
                WHERE id = 1
            """, (pnl_usd, size_usd, pnl_usd, size_usd, pnl_usd, pnl_usd))

            conn.commit()

        # Step 6: Record rule outcomes (if any rules were used)
        if rule_ids_used:
            trade_success = pnl_usd >= 0
            rule_ids = [int(r) for r in rule_ids_used.split(',') if r.strip()]
            for rule_id in rule_ids:
                self.rule_manager.record_rule_outcome(rule_id, success=trade_success)
            logger.info(f"Recorded {len(rule_ids)} rule outcomes (success={trade_success})")

        # Step 7: Log activity
        pnl_sign = "+" if pnl_usd >= 0 else ""
        self.db.log_activity(
            "trade_closed",
            f"CLOSED {trade['coin_name']} @ ${current_price:.2f} P&L: {pnl_sign}${pnl_usd:.2f} ({exit_reason})",
            f"trade_id={trade_id}, entry=${entry_price:.2f}, duration={duration_seconds}s"
        )

        message = f"Closed trade #{trade_id}: {trade['coin_name']} P&L: {pnl_sign}${pnl_usd:.2f} ({pnl_pct:+.2f}%)"
        logger.info(message)

        return TradeResult(success=True, trade_id=trade_id, message=message)

    def update_positions(self) -> List[Dict[str, Any]]:
        """Update all open positions with current prices.

        Checks stop loss and take profit triggers, closing trades as needed.

        Returns:
            List of trades that were closed due to stop loss or take profit.
        """
        logger.info("Updating open positions...")

        closed_trades = []
        open_trades = self.get_open_trades()

        for trade in open_trades:
            coin = trade['coin_name']
            trade_id = trade['id']

            # Get current price
            current_price = self.get_current_price(coin)
            if current_price is None:
                logger.warning(f"No market data for {coin}, skipping position update")
                continue

            # Update current price and unrealized P&L
            entry_price = trade['entry_price']
            size_usd = trade['size_usd']
            price_change_pct = (current_price - entry_price) / entry_price
            unrealized_pnl = size_usd * price_change_pct
            unrealized_pnl_pct = price_change_pct * 100

            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE open_trades SET
                        current_price = ?,
                        unrealized_pnl = ?,
                        unrealized_pnl_pct = ?
                    WHERE id = ?
                """, (current_price, unrealized_pnl, unrealized_pnl_pct, trade_id))
                conn.commit()

            # Check stop loss / take profit
            exit_check = self.risk_manager.should_exit_trade(
                entry_price, current_price, size_usd
            )

            if exit_check['should_exit']:
                result = self.close_trade(trade_id, exit_check['reason'])
                if result.success:
                    closed_trades.append({
                        'trade_id': trade_id,
                        'coin': coin,
                        'reason': exit_check['reason'],
                        'pnl_usd': exit_check['pnl_usd'],
                        'pnl_pct': exit_check['pnl_pct']
                    })

        logger.info(f"Position update complete. Closed {len(closed_trades)} trades.")
        return closed_trades

    def get_open_trades(self) -> List[Dict[str, Any]]:
        """Get all open trades.

        Returns:
            List of open trade dictionaries.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, coin_name, entry_price, size_usd, current_price,
                       unrealized_pnl, unrealized_pnl_pct, stop_loss_price,
                       take_profit_price, entry_reason, opened_at
                FROM open_trades
                ORDER BY opened_at DESC
            """)

            columns = ['id', 'coin_name', 'entry_price', 'size_usd', 'current_price',
                      'unrealized_pnl', 'unrealized_pnl_pct', 'stop_loss_price',
                      'take_profit_price', 'entry_reason', 'opened_at']

            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_trade_by_id(self, trade_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific open trade by ID.

        Args:
            trade_id: The trade ID to look up.

        Returns:
            Trade dictionary or None if not found.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, coin_name, entry_price, size_usd, current_price,
                       unrealized_pnl, unrealized_pnl_pct, stop_loss_price,
                       take_profit_price, entry_reason, opened_at, rule_ids_used
                FROM open_trades
                WHERE id = ?
            """, (trade_id,))

            row = cursor.fetchone()
            if row is None:
                return None

            columns = ['id', 'coin_name', 'entry_price', 'size_usd', 'current_price',
                      'unrealized_pnl', 'unrealized_pnl_pct', 'stop_loss_price',
                      'take_profit_price', 'entry_reason', 'opened_at', 'rule_ids_used']

            return dict(zip(columns, row))

    def get_closed_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent closed trades.

        Args:
            limit: Maximum number of trades to return.

        Returns:
            List of closed trade dictionaries.
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, coin_name, entry_price, exit_price, size_usd,
                       pnl_usd, pnl_pct, entry_reason, exit_reason,
                       opened_at, closed_at, duration_seconds
                FROM closed_trades
                ORDER BY closed_at DESC
                LIMIT ?
            """, (limit,))

            columns = ['id', 'coin_name', 'entry_price', 'exit_price', 'size_usd',
                      'pnl_usd', 'pnl_pct', 'entry_reason', 'exit_reason',
                      'opened_at', 'closed_at', 'duration_seconds']

            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_account_summary(self) -> Dict[str, Any]:
        """Get current account summary.

        Returns:
            Account state with trade counts.
        """
        state = self.db.get_account_state()
        open_count = len(self.get_open_trades())

        return {
            **state,
            'open_trade_count': open_count
        }
