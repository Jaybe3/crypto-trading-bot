"""SQLite database operations for the trading bot."""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Database:
    """SQLite database interface for the trading bot.

    Handles all database operations including table creation,
    CRUD operations for trades, learnings, rules, and account state.

    Attributes:
        db_path: Path to the SQLite database file.

    Example:
        >>> db = Database()
        >>> db.get_account_state()
        {'balance': 1000.0, 'available_balance': 1000.0, ...}
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection.

        Args:
            db_path: Optional path to database file.
                     Defaults to data/trading_bot.db in project root.
        """
        if db_path is None:
            # Default to data/trading_bot.db relative to project root
            project_root = Path(__file__).parent.parent
            self.db_path = project_root / "data" / "trading_bot.db"
        else:
            self.db_path = Path(db_path)

        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create tables on initialization
        self.create_tables()

        # Initialize account state if empty
        self._initialize_account_state()

        logger.info(f"Database initialized at {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory enabled.

        Returns:
            sqlite3.Connection configured for dict-like row access.
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def create_tables(self) -> None:
        """Create all required tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. open_trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS open_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coin_name TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    size_usd REAL NOT NULL,
                    current_price REAL,
                    unrealized_pnl REAL,
                    unrealized_pnl_pct REAL,
                    stop_loss_price REAL NOT NULL,
                    take_profit_price REAL NOT NULL,
                    entry_reason TEXT NOT NULL,
                    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. closed_trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS closed_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coin_name TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    size_usd REAL NOT NULL,
                    pnl_usd REAL NOT NULL,
                    pnl_pct REAL NOT NULL,
                    entry_reason TEXT NOT NULL,
                    exit_reason TEXT NOT NULL,
                    opened_at TIMESTAMP,
                    closed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    duration_seconds INTEGER
                )
            """)

            # 3. learnings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id INTEGER,
                    learning_text TEXT NOT NULL,
                    pattern_observed TEXT,
                    success_rate REAL,
                    confidence_level REAL,
                    trades_analyzed INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    validated BOOLEAN DEFAULT 0
                )
            """)

            # 4. trading_rules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_text TEXT NOT NULL,
                    rule_type TEXT NOT NULL,
                    created_by TEXT DEFAULT 'LLM',
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'testing',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP
                )
            """)

            # 5. activity_log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 6. account_state table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS account_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    balance REAL NOT NULL DEFAULT 1000.0,
                    available_balance REAL NOT NULL DEFAULT 1000.0,
                    in_positions REAL NOT NULL DEFAULT 0.0,
                    total_pnl REAL NOT NULL DEFAULT 0.0,
                    daily_pnl REAL NOT NULL DEFAULT 0.0,
                    trade_count_today INTEGER NOT NULL DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 7. market_data table (for TASK-003)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    coin TEXT PRIMARY KEY,
                    price_usd REAL NOT NULL,
                    change_24h REAL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 8. price_history table (for TASK-015 volatility)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coin TEXT NOT NULL,
                    price_usd REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 9. coin_cooldowns table (for TASK-020 persistent cooldowns)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS coin_cooldowns (
                    coin_name TEXT PRIMARY KEY,
                    expires_at TIMESTAMP NOT NULL
                )
            """)

            # 10. monitoring_alerts table (for TASK-021 autonomous monitoring)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    evidence TEXT,
                    recommendation TEXT,
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    acknowledged_at TIMESTAMP,
                    fixed_at TIMESTAMP
                )
            """)

            # 11. trade_journal table (for TASK-102 comprehensive trade journaling)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_journal (
                    id TEXT PRIMARY KEY,
                    position_id TEXT NOT NULL,

                    -- Entry details
                    entry_time TIMESTAMP NOT NULL,
                    entry_price REAL NOT NULL,
                    entry_reason TEXT,

                    -- Trade parameters
                    coin TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    position_size_usd REAL NOT NULL,
                    stop_loss_price REAL,
                    take_profit_price REAL,

                    -- Strategy context
                    strategy_id TEXT,
                    condition_id TEXT,
                    pattern_id TEXT,

                    -- Market context at entry
                    market_regime TEXT,
                    volatility REAL,
                    funding_rate REAL,
                    cvd REAL,
                    btc_trend TEXT,
                    btc_price REAL,

                    -- Timing context
                    hour_of_day INTEGER,
                    day_of_week INTEGER,

                    -- Exit details (filled when closed)
                    exit_time TIMESTAMP,
                    exit_price REAL,
                    exit_reason TEXT,

                    -- Outcome (filled when closed)
                    pnl_usd REAL,
                    pnl_pct REAL,
                    duration_seconds INTEGER,

                    -- Post-trade context (filled async after exit)
                    price_1min_after REAL,
                    price_5min_after REAL,
                    price_15min_after REAL,
                    missed_profit_usd REAL,

                    -- Metadata
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_open_trades_coin
                ON open_trades(coin_name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_open_trades_opened_at
                ON open_trades(opened_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_closed_trades_coin
                ON closed_trades(coin_name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_closed_trades_closed_at
                ON closed_trades(closed_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_learnings_created_at
                ON learnings(created_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trading_rules_status
                ON trading_rules(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_activity_log_created_at
                ON activity_log(created_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_activity_log_type
                ON activity_log(activity_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_severity
                ON monitoring_alerts(severity)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_status
                ON monitoring_alerts(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_created
                ON monitoring_alerts(created_at)
            """)

            # 12. active_conditions table (for TASK-110 Strategist)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_conditions (
                    id TEXT PRIMARY KEY,
                    coin TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    trigger_price REAL NOT NULL,
                    trigger_condition TEXT NOT NULL,
                    stop_loss_pct REAL NOT NULL,
                    take_profit_pct REAL NOT NULL,
                    position_size_usd REAL NOT NULL,
                    strategy_id TEXT,
                    reasoning TEXT,
                    created_at TIMESTAMP NOT NULL,
                    valid_until TIMESTAMP NOT NULL,
                    triggered BOOLEAN DEFAULT FALSE,
                    triggered_at TIMESTAMP,
                    additional_filters TEXT
                )
            """)

            # Trade journal indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_journal_coin
                ON trade_journal(coin)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_journal_strategy
                ON trade_journal(strategy_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_journal_status
                ON trade_journal(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_journal_entry_time
                ON trade_journal(entry_time)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_journal_exit_reason
                ON trade_journal(exit_reason)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_journal_pnl
                ON trade_journal(pnl_usd)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_journal_hour
                ON trade_journal(hour_of_day)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_journal_day
                ON trade_journal(day_of_week)
            """)

            # Active conditions indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conditions_coin
                ON active_conditions(coin)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conditions_valid_until
                ON active_conditions(valid_until)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conditions_triggered
                ON active_conditions(triggered)
            """)

            conn.commit()
            logger.info("All tables and indexes created successfully")

    def _initialize_account_state(self) -> None:
        """Initialize account state with $1,000 if not exists."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM account_state")
            count = cursor.fetchone()[0]

            if count == 0:
                cursor.execute("""
                    INSERT INTO account_state
                    (balance, available_balance, in_positions, total_pnl, daily_pnl, trade_count_today)
                    VALUES (1000.0, 1000.0, 0.0, 0.0, 0.0, 0)
                """)
                conn.commit()
                logger.info("Account state initialized with $1,000 balance")

    def get_account_state(self) -> Dict[str, Any]:
        """Get current account state.

        Returns:
            Dictionary with account balance and position information.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM account_state ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {}

    def update_account_state(self, **kwargs) -> None:
        """Update account state with provided values.

        Args:
            **kwargs: Fields to update (balance, available_balance, etc.)
        """
        if not kwargs:
            return

        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE account_state
                SET {set_clause}, last_updated = CURRENT_TIMESTAMP
                WHERE id = (SELECT MAX(id) FROM account_state)
            """, values)
            conn.commit()

    def log_activity(self, activity_type: str, description: str, details: Optional[str] = None) -> int:
        """Log an activity to the activity_log table.

        Args:
            activity_type: Type of activity (e.g., 'trade', 'learning', 'error')
            description: Human-readable description
            details: Optional JSON or additional details

        Returns:
            The ID of the inserted log entry.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO activity_log (activity_type, description, details)
                VALUES (?, ?, ?)
            """, (activity_type, description, details))
            conn.commit()
            return cursor.lastrowid

    def get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent activity log entries.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of activity log entries as dictionaries.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM activity_log
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # ========== Active Conditions (TASK-110 Strategist) ==========

    def save_condition(self, condition: Dict[str, Any]) -> None:
        """Save a trade condition to the database.

        Args:
            condition: Dictionary with condition fields from TradeCondition.to_dict()
        """
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO active_conditions
                (id, coin, direction, trigger_price, trigger_condition,
                 stop_loss_pct, take_profit_pct, position_size_usd,
                 strategy_id, reasoning, created_at, valid_until, additional_filters)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                condition["id"],
                condition["coin"],
                condition["direction"],
                condition["trigger_price"],
                condition["trigger_condition"],
                condition["stop_loss_pct"],
                condition["take_profit_pct"],
                condition["position_size_usd"],
                condition.get("strategy_id"),
                condition.get("reasoning"),
                condition["created_at"],
                condition["valid_until"],
                json.dumps(condition.get("additional_filters")) if condition.get("additional_filters") else None,
            ))
            conn.commit()
            logger.debug(f"Saved condition {condition['id']} for {condition['coin']}")

    def get_active_conditions(self) -> List[Dict[str, Any]]:
        """Get all non-expired, non-triggered conditions.

        Returns:
            List of active condition dictionaries.
        """
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM active_conditions
                WHERE triggered = FALSE
                AND valid_until > datetime('now')
                ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()
            conditions = []
            for row in rows:
                cond = dict(row)
                if cond.get("additional_filters"):
                    cond["additional_filters"] = json.loads(cond["additional_filters"])
                conditions.append(cond)
            return conditions

    def get_condition_by_id(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific condition by ID.

        Args:
            condition_id: The condition ID.

        Returns:
            Condition dictionary or None if not found.
        """
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM active_conditions WHERE id = ?
            """, (condition_id,))
            row = cursor.fetchone()
            if row:
                cond = dict(row)
                if cond.get("additional_filters"):
                    cond["additional_filters"] = json.loads(cond["additional_filters"])
                return cond
            return None

    def mark_condition_triggered(self, condition_id: str) -> None:
        """Mark a condition as triggered.

        Args:
            condition_id: The condition ID to mark as triggered.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE active_conditions
                SET triggered = TRUE, triggered_at = datetime('now')
                WHERE id = ?
            """, (condition_id,))
            conn.commit()
            logger.info(f"Marked condition {condition_id} as triggered")

    def delete_expired_conditions(self) -> int:
        """Delete all expired conditions.

        Returns:
            Number of conditions deleted.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM active_conditions
                WHERE valid_until < datetime('now')
            """)
            deleted = cursor.rowcount
            conn.commit()
            if deleted > 0:
                logger.info(f"Deleted {deleted} expired conditions")
            return deleted

    def clear_all_conditions(self) -> int:
        """Clear all active conditions (used when Strategist generates new set).

        Returns:
            Number of conditions deleted.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM active_conditions
                WHERE triggered = FALSE
            """)
            deleted = cursor.rowcount
            conn.commit()
            logger.debug(f"Cleared {deleted} untriggered conditions")
            return deleted

    def get_conditions_for_coin(self, coin: str) -> List[Dict[str, Any]]:
        """Get active conditions for a specific coin.

        Args:
            coin: Coin symbol (e.g., "SOL", "ETH").

        Returns:
            List of condition dictionaries for this coin.
        """
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM active_conditions
                WHERE coin = ?
                AND triggered = FALSE
                AND valid_until > datetime('now')
                ORDER BY created_at DESC
            """, (coin,))
            rows = cursor.fetchall()
            conditions = []
            for row in rows:
                cond = dict(row)
                if cond.get("additional_filters"):
                    cond["additional_filters"] = json.loads(cond["additional_filters"])
                conditions.append(cond)
            return conditions


# Allow running directly to initialize database
if __name__ == "__main__":
    db = Database()
    print(f"Database created at: {db.db_path}")
    print(f"Account state: {db.get_account_state()}")
