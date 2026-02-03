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

            # 13. coin_scores table (for TASK-120 Knowledge Brain)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS coin_scores (
                    coin TEXT PRIMARY KEY,
                    total_trades INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    avg_pnl REAL DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    avg_winner REAL DEFAULT 0,
                    avg_loser REAL DEFAULT 0,
                    is_blacklisted BOOLEAN DEFAULT FALSE,
                    blacklist_reason TEXT,
                    trend TEXT DEFAULT 'stable',
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 14. trading_patterns table (for TASK-120 Knowledge Brain)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    entry_conditions TEXT NOT NULL,
                    exit_conditions TEXT NOT NULL,
                    times_used INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    confidence REAL DEFAULT 0.5,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP
                )
            """)

            # 15. regime_rules table (for TASK-120 Knowledge Brain)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS regime_rules (
                    rule_id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    action TEXT NOT NULL,
                    times_triggered INTEGER DEFAULT 0,
                    estimated_saves REAL DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 16. coin_adaptations table (for TASK-121 Coin Scoring)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS coin_adaptations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coin TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    old_status TEXT NOT NULL,
                    new_status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    trigger_stats TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 17. reflections table (for TASK-131 Deep Reflection)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reflections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP NOT NULL,
                    trades_analyzed INTEGER NOT NULL,
                    period_hours REAL,
                    insights TEXT NOT NULL,
                    summary TEXT,
                    total_time_ms REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 18. adaptations table (for TASK-133 Adaptation Application)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS adaptations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    adaptation_id TEXT NOT NULL UNIQUE,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    insight_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL,
                    description TEXT NOT NULL,
                    pre_metrics TEXT,
                    insight_confidence REAL,
                    insight_evidence TEXT,
                    post_metrics TEXT,
                    effectiveness TEXT,
                    effectiveness_measured_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 19. runtime_state table (for TASK-140 Full System Integration)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS runtime_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 20. profit_snapshots table (for TASK-141 Profitability Tracking)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profit_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP NOT NULL,
                    timeframe TEXT NOT NULL,

                    -- Core metrics
                    total_pnl REAL NOT NULL,
                    realized_pnl REAL NOT NULL,
                    unrealized_pnl REAL DEFAULT 0,

                    -- Trade counts
                    total_trades INTEGER NOT NULL,
                    winning_trades INTEGER NOT NULL,
                    losing_trades INTEGER NOT NULL,

                    -- Rates
                    win_rate REAL NOT NULL,
                    avg_win REAL,
                    avg_loss REAL,
                    profit_factor REAL,

                    -- Risk metrics
                    max_drawdown REAL,
                    max_drawdown_pct REAL,
                    sharpe_ratio REAL,

                    -- Balance
                    starting_balance REAL,
                    ending_balance REAL,
                    return_pct REAL,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 21. equity_points table (for TASK-141 Profitability Tracking)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS equity_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP NOT NULL,
                    balance REAL NOT NULL,
                    trade_id TEXT,
                    is_high_water_mark BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Knowledge Brain indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_coin_scores_blacklisted
                ON coin_scores(is_blacklisted)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_coin_scores_win_rate
                ON coin_scores(win_rate)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_patterns_active
                ON trading_patterns(is_active)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_patterns_confidence
                ON trading_patterns(confidence)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_rules_active
                ON regime_rules(is_active)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_adaptations_coin
                ON coin_adaptations(coin)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_adaptations_timestamp
                ON coin_adaptations(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reflections_timestamp
                ON reflections(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_adaptations_timestamp
                ON adaptations(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_adaptations_target
                ON adaptations(target)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_adaptations_action
                ON adaptations(action)
            """)

            # Profitability tracking indexes (TASK-141)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_timeframe
                ON profit_snapshots(timeframe, timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp
                ON profit_snapshots(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_equity_timestamp
                ON equity_points(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_equity_hwm
                ON equity_points(is_high_water_mark)
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

    # ========== Reflections (TASK-131 Deep Reflection) ==========

    def log_reflection(
        self,
        trades_analyzed: int,
        period_hours: float,
        insights: str,
        summary: str,
        total_time_ms: float,
    ) -> int:
        """Log a reflection result to the database.

        Args:
            trades_analyzed: Number of trades analyzed.
            period_hours: Time period covered in hours.
            insights: JSON string of insights.
            summary: LLM-generated summary.
            total_time_ms: Total reflection time in milliseconds.

        Returns:
            The ID of the inserted reflection.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reflections
                (timestamp, trades_analyzed, period_hours, insights, summary, total_time_ms)
                VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
            """, (trades_analyzed, period_hours, insights, summary, total_time_ms))
            conn.commit()
            return cursor.lastrowid

    def get_recent_reflections(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent reflection results.

        Args:
            limit: Maximum number of reflections to return.

        Returns:
            List of reflection records as dictionaries.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM reflections
                ORDER BY timestamp DESC
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

    # ========== Coin Scores (TASK-120 Knowledge Brain) ==========

    def save_coin_score(self, score_data: Dict[str, Any]) -> None:
        """Save or update a coin score.

        Args:
            score_data: Dictionary from CoinScore.to_dict()
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO coin_scores
                (coin, total_trades, wins, losses, total_pnl, avg_pnl, win_rate,
                 avg_winner, avg_loser, is_blacklisted, blacklist_reason, trend, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                score_data["coin"],
                score_data["total_trades"],
                score_data["wins"],
                score_data["losses"],
                score_data["total_pnl"],
                score_data["avg_pnl"],
                score_data["win_rate"],
                score_data["avg_winner"],
                score_data["avg_loser"],
                score_data["is_blacklisted"],
                score_data["blacklist_reason"],
                score_data["trend"],
                score_data["last_updated"],
            ))
            conn.commit()

    def get_coin_score(self, coin: str) -> Optional[Dict[str, Any]]:
        """Get score for a specific coin.

        Args:
            coin: Coin symbol.

        Returns:
            Coin score dictionary or None if not found.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM coin_scores WHERE coin = ?", (coin,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_coin_scores(self) -> List[Dict[str, Any]]:
        """Get all coin scores.

        Returns:
            List of all coin score dictionaries.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM coin_scores ORDER BY total_pnl DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_blacklisted_coins(self) -> List[str]:
        """Get list of blacklisted coin symbols.

        Returns:
            List of blacklisted coin symbols.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT coin FROM coin_scores WHERE is_blacklisted = TRUE")
            return [row[0] for row in cursor.fetchall()]

    def update_coin_blacklist(self, coin: str, is_blacklisted: bool, reason: str = "") -> None:
        """Update blacklist status for a coin.

        Args:
            coin: Coin symbol.
            is_blacklisted: Whether to blacklist.
            reason: Reason for blacklisting (if applicable).
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE coin_scores
                SET is_blacklisted = ?, blacklist_reason = ?, last_updated = CURRENT_TIMESTAMP
                WHERE coin = ?
            """, (is_blacklisted, reason, coin))
            conn.commit()

    # ========== Trading Patterns (TASK-120 Knowledge Brain) ==========

    def save_pattern(self, pattern_data: Dict[str, Any]) -> None:
        """Save or update a trading pattern.

        Args:
            pattern_data: Dictionary from TradingPattern.to_dict()
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO trading_patterns
                (pattern_id, description, entry_conditions, exit_conditions,
                 times_used, wins, losses, total_pnl, confidence, is_active,
                 created_at, last_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern_data["pattern_id"],
                pattern_data["description"],
                pattern_data["entry_conditions"],
                pattern_data["exit_conditions"],
                pattern_data["times_used"],
                pattern_data["wins"],
                pattern_data["losses"],
                pattern_data["total_pnl"],
                pattern_data["confidence"],
                pattern_data["is_active"],
                pattern_data["created_at"],
                pattern_data["last_used"],
            ))
            conn.commit()

    def get_pattern(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """Get a trading pattern by ID.

        Args:
            pattern_id: Pattern ID.

        Returns:
            Pattern dictionary or None if not found.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trading_patterns WHERE pattern_id = ?", (pattern_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_active_patterns(self) -> List[Dict[str, Any]]:
        """Get all active trading patterns.

        Returns:
            List of active pattern dictionaries.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trading_patterns
                WHERE is_active = TRUE
                ORDER BY confidence DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def update_pattern_stats(self, pattern_id: str, won: bool, pnl: float) -> None:
        """Update pattern statistics after a trade.

        Args:
            pattern_id: Pattern ID.
            won: Whether the trade was a winner.
            pnl: P&L from the trade.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trading_patterns
                SET times_used = times_used + 1,
                    wins = wins + ?,
                    losses = losses + ?,
                    total_pnl = total_pnl + ?,
                    last_used = CURRENT_TIMESTAMP
                WHERE pattern_id = ?
            """, (1 if won else 0, 0 if won else 1, pnl, pattern_id))
            conn.commit()

    def deactivate_pattern(self, pattern_id: str) -> None:
        """Deactivate a pattern.

        Args:
            pattern_id: Pattern ID.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trading_patterns
                SET is_active = FALSE
                WHERE pattern_id = ?
            """, (pattern_id,))
            conn.commit()

    # ========== Regime Rules (TASK-120 Knowledge Brain) ==========

    def save_rule(self, rule_data: Dict[str, Any]) -> None:
        """Save or update a regime rule.

        Args:
            rule_data: Dictionary from RegimeRule.to_dict()
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO regime_rules
                (rule_id, description, condition, action, times_triggered,
                 estimated_saves, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule_data["rule_id"],
                rule_data["description"],
                rule_data["condition"],
                rule_data["action"],
                rule_data["times_triggered"],
                rule_data["estimated_saves"],
                rule_data["is_active"],
                rule_data["created_at"],
            ))
            conn.commit()

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get a regime rule by ID.

        Args:
            rule_id: Rule ID.

        Returns:
            Rule dictionary or None if not found.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM regime_rules WHERE rule_id = ?", (rule_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_active_rules(self) -> List[Dict[str, Any]]:
        """Get all active regime rules.

        Returns:
            List of active rule dictionaries.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM regime_rules
                WHERE is_active = TRUE
                ORDER BY created_at ASC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def update_rule_stats(self, rule_id: str, estimated_save: float = 0.0) -> None:
        """Update rule statistics after it triggered.

        Args:
            rule_id: Rule ID.
            estimated_save: Estimated P&L saved by following this rule.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE regime_rules
                SET times_triggered = times_triggered + 1,
                    estimated_saves = estimated_saves + ?
                WHERE rule_id = ?
            """, (estimated_save, rule_id))
            conn.commit()

    def deactivate_rule(self, rule_id: str) -> None:
        """Deactivate a regime rule.

        Args:
            rule_id: Rule ID.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE regime_rules
                SET is_active = FALSE
                WHERE rule_id = ?
            """, (rule_id,))
            conn.commit()

    # ========== Coin Adaptations (TASK-121 Coin Scoring) ==========

    def save_coin_adaptation(self, adaptation_data: Dict[str, Any]) -> int:
        """Save a coin adaptation record.

        Args:
            adaptation_data: Dictionary from CoinAdaptation.to_dict()

        Returns:
            ID of the inserted record.
        """
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO coin_adaptations
                (coin, timestamp, old_status, new_status, reason, trigger_stats)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                adaptation_data["coin"],
                adaptation_data["timestamp"],
                adaptation_data["old_status"],
                adaptation_data["new_status"],
                adaptation_data["reason"],
                json.dumps(adaptation_data.get("trigger_stats", {})),
            ))
            conn.commit()
            return cursor.lastrowid

    def get_coin_adaptations(self, coin: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get coin adaptation history.

        Args:
            coin: Optional coin to filter by.
            limit: Maximum number of records.

        Returns:
            List of adaptation records.
        """
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if coin:
                cursor.execute("""
                    SELECT * FROM coin_adaptations
                    WHERE coin = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (coin, limit))
            else:
                cursor.execute("""
                    SELECT * FROM coin_adaptations
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))

            results = []
            for row in cursor.fetchall():
                record = dict(row)
                if record.get("trigger_stats"):
                    record["trigger_stats"] = json.loads(record["trigger_stats"])
                results.append(record)
            return results

    def get_recent_adaptations(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get adaptations from the last N hours.

        Args:
            hours: Number of hours to look back.

        Returns:
            List of recent adaptation records.
        """
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM coin_adaptations
                WHERE timestamp > datetime('now', ? || ' hours')
                ORDER BY timestamp DESC
            """, (f"-{hours}",))

            results = []
            for row in cursor.fetchall():
                record = dict(row)
                if record.get("trigger_stats"):
                    record["trigger_stats"] = json.loads(record["trigger_stats"])
                results.append(record)
            return results


    # ========== Adaptations (TASK-133 Adaptation Application) ==========

    def log_adaptation(
        self,
        adaptation_id: str,
        insight_type: str,
        action: str,
        target: str,
        description: str,
        pre_metrics: str = "{}",
        insight_confidence: float = 0.0,
        insight_evidence: str = "{}",
    ) -> int:
        """Log an adaptation applied from an insight.

        Args:
            adaptation_id: Unique ID for this adaptation.
            insight_type: Type of insight (coin, pattern, time, regime).
            action: Action taken (blacklist, favor, create_rule, etc.).
            target: Target of the action (coin symbol, rule_id, etc.).
            description: Human-readable description.
            pre_metrics: JSON string of pre-adaptation metrics.
            insight_confidence: Confidence level of the insight.
            insight_evidence: JSON string of insight evidence.

        Returns:
            The ID of the inserted adaptation.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO adaptations
                (adaptation_id, insight_type, action, target, description,
                 pre_metrics, insight_confidence, insight_evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                adaptation_id,
                insight_type,
                action,
                target,
                description,
                pre_metrics,
                insight_confidence,
                insight_evidence,
            ))
            conn.commit()
            logger.info(f"Logged adaptation: [{action}] {target}")
            return cursor.lastrowid

    def get_adaptations(self, hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent adaptations from the adaptations table.

        Args:
            hours: Number of hours to look back (default 24).
            limit: Maximum number of records to return.

        Returns:
            List of adaptation records as dictionaries.
        """
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM adaptations
                WHERE timestamp > datetime('now', ? || ' hours')
                ORDER BY timestamp DESC
                LIMIT ?
            """, (f"-{hours}", limit))

            results = []
            for row in cursor.fetchall():
                record = dict(row)
                # Parse JSON fields
                if record.get("pre_metrics"):
                    try:
                        record["pre_metrics"] = json.loads(record["pre_metrics"])
                    except json.JSONDecodeError:
                        pass
                if record.get("insight_evidence"):
                    try:
                        record["insight_evidence"] = json.loads(record["insight_evidence"])
                    except json.JSONDecodeError:
                        pass
                if record.get("post_metrics"):
                    try:
                        record["post_metrics"] = json.loads(record["post_metrics"])
                    except json.JSONDecodeError:
                        pass
                results.append(record)
            return results

    def get_adaptations_for_target(self, target: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent adaptations for a specific target.

        Args:
            target: The target (coin symbol, rule_id, etc.).
            hours: Number of hours to look back.

        Returns:
            List of adaptation records for this target.
        """
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM adaptations
                WHERE target = ?
                AND timestamp > datetime('now', ? || ' hours')
                ORDER BY timestamp DESC
            """, (target, f"-{hours}"))

            results = []
            for row in cursor.fetchall():
                record = dict(row)
                if record.get("pre_metrics"):
                    try:
                        record["pre_metrics"] = json.loads(record["pre_metrics"])
                    except json.JSONDecodeError:
                        pass
                results.append(record)
            return results

    def update_adaptation_effectiveness(
        self,
        adaptation_id: str,
        post_metrics: str,
        effectiveness: str,
        effectiveness_measured_at: datetime,
    ) -> None:
        """Update adaptation with effectiveness measurement.

        Args:
            adaptation_id: ID of the adaptation.
            post_metrics: JSON string of post-adaptation metrics.
            effectiveness: Effectiveness rating.
            effectiveness_measured_at: When effectiveness was measured.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE adaptations
                SET post_metrics = ?,
                    effectiveness = ?,
                    effectiveness_measured_at = ?
                WHERE adaptation_id = ?
            """, (
                post_metrics,
                effectiveness,
                effectiveness_measured_at.isoformat() if isinstance(effectiveness_measured_at, datetime) else effectiveness_measured_at,
                adaptation_id,
            ))
            conn.commit()
            logger.debug(f"Updated effectiveness for adaptation {adaptation_id}: {effectiveness}")

    def get_adaptations_by_effectiveness(
        self,
        effectiveness: str,
        hours: int = 168,
    ) -> List[Dict[str, Any]]:
        """Get adaptations by effectiveness rating.

        Args:
            effectiveness: Effectiveness rating to filter by.
            hours: Number of hours to look back.

        Returns:
            List of adaptation records with this effectiveness.
        """
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM adaptations
                WHERE effectiveness = ?
                AND timestamp > datetime('now', ? || ' hours')
                ORDER BY effectiveness_measured_at DESC
            """, (effectiveness, f"-{hours}"))

            results = []
            for row in cursor.fetchall():
                record = dict(row)
                # Parse JSON fields
                for field in ["pre_metrics", "post_metrics", "insight_evidence"]:
                    if record.get(field):
                        try:
                            record[field] = json.loads(record[field])
                        except json.JSONDecodeError:
                            pass
                results.append(record)
            return results

    def get_unmeasured_adaptations(self, min_hours: int = 24) -> List[Dict[str, Any]]:
        """Get adaptations that haven't been measured yet.

        Args:
            min_hours: Minimum hours since adaptation.

        Returns:
            List of unmeasured adaptation records.
        """
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM adaptations
                WHERE effectiveness IS NULL
                AND timestamp < datetime('now', ? || ' hours')
                ORDER BY timestamp ASC
            """, (f"-{min_hours}",))

            results = []
            for row in cursor.fetchall():
                record = dict(row)
                if record.get("pre_metrics"):
                    try:
                        record["pre_metrics"] = json.loads(record["pre_metrics"])
                    except json.JSONDecodeError:
                        pass
                results.append(record)
            return results

    # ========== Runtime State (TASK-140 Full System Integration) ==========

    def save_runtime_state(self, state: Dict[str, Any]) -> None:
        """Save runtime state for restart recovery.

        Args:
            state: Dictionary of state to persist.
        """
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for key, value in state.items():
                value_json = json.dumps(value) if not isinstance(value, str) else value
                cursor.execute("""
                    INSERT OR REPLACE INTO runtime_state (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, value_json))
            conn.commit()
            logger.debug(f"Saved runtime state: {len(state)} keys")

    def get_runtime_state(self) -> Dict[str, Any]:
        """Load runtime state after restart.

        Returns:
            Dictionary of saved state.
        """
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM runtime_state")
            rows = cursor.fetchall()

            state = {}
            for row in rows:
                key = row[0]
                value = row[1]
                # Try to parse as JSON
                try:
                    state[key] = json.loads(value)
                except json.JSONDecodeError:
                    state[key] = value
            return state

    def clear_runtime_state(self) -> None:
        """Clear all runtime state."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM runtime_state")
            conn.commit()
            logger.debug("Cleared runtime state")

    # ========== Profit Snapshots (TASK-141 Profitability Tracking) ==========

    def save_profit_snapshot(self, snapshot: Dict[str, Any]) -> int:
        """Save a profitability snapshot.

        Args:
            snapshot: Dictionary from ProfitSnapshot.to_dict()

        Returns:
            The ID of the inserted snapshot.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO profit_snapshots
                (timestamp, timeframe, total_pnl, realized_pnl, unrealized_pnl,
                 total_trades, winning_trades, losing_trades, win_rate,
                 avg_win, avg_loss, profit_factor, max_drawdown, max_drawdown_pct,
                 sharpe_ratio, starting_balance, ending_balance, return_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot["timestamp"],
                snapshot["timeframe"],
                snapshot["total_pnl"],
                snapshot["realized_pnl"],
                snapshot.get("unrealized_pnl", 0),
                snapshot["total_trades"],
                snapshot["winning_trades"],
                snapshot["losing_trades"],
                snapshot["win_rate"],
                snapshot.get("avg_win"),
                snapshot.get("avg_loss"),
                snapshot.get("profit_factor"),
                snapshot.get("max_drawdown"),
                snapshot.get("max_drawdown_pct"),
                snapshot.get("sharpe_ratio"),
                snapshot.get("starting_balance"),
                snapshot.get("ending_balance"),
                snapshot.get("return_pct"),
            ))
            conn.commit()
            logger.debug(f"Saved profit snapshot ({snapshot['timeframe']})")
            return cursor.lastrowid

    def get_profit_snapshots(
        self,
        timeframe: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get profitability snapshots.

        Args:
            timeframe: Filter by timeframe (hour, day, week, month, all_time).
            start: Start of date range.
            end: End of date range.
            limit: Maximum number of snapshots to return.

        Returns:
            List of snapshot dictionaries.
        """
        where_parts = ["1=1"]
        params = []

        if timeframe:
            where_parts.append("timeframe = ?")
            params.append(timeframe)

        if start:
            where_parts.append("timestamp >= ?")
            params.append(start.isoformat() if isinstance(start, datetime) else start)

        if end:
            where_parts.append("timestamp <= ?")
            params.append(end.isoformat() if isinstance(end, datetime) else end)

        where = " AND ".join(where_parts)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT * FROM profit_snapshots
                WHERE {where}
                ORDER BY timestamp DESC
                LIMIT ?
            """, params + [limit])
            return [dict(row) for row in cursor.fetchall()]

    def delete_old_snapshots(self, timeframe: str, cutoff: datetime) -> int:
        """Delete snapshots older than cutoff.

        Args:
            timeframe: Timeframe to delete from.
            cutoff: Delete snapshots before this time.

        Returns:
            Number of snapshots deleted.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM profit_snapshots
                WHERE timeframe = ?
                AND timestamp < ?
            """, (timeframe, cutoff.isoformat()))
            deleted = cursor.rowcount
            conn.commit()
            if deleted > 0:
                logger.debug(f"Deleted {deleted} old {timeframe} snapshots")
            return deleted

    # ========== Equity Points (TASK-141 Profitability Tracking) ==========

    def save_equity_point(self, point: Dict[str, Any]) -> int:
        """Save an equity point.

        Args:
            point: Dictionary with timestamp, balance, trade_id, is_high_water_mark.

        Returns:
            The ID of the inserted point.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO equity_points
                (timestamp, balance, trade_id, is_high_water_mark)
                VALUES (?, ?, ?, ?)
            """, (
                point["timestamp"],
                point["balance"],
                point.get("trade_id"),
                point.get("is_high_water_mark", False),
            ))
            conn.commit()
            return cursor.lastrowid

    def get_equity_curve(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Get equity curve data.

        Args:
            start: Start of date range.
            end: End of date range.
            limit: Maximum number of points to return.

        Returns:
            List of equity point dictionaries.
        """
        where_parts = ["1=1"]
        params = []

        if start:
            where_parts.append("timestamp >= ?")
            params.append(start.isoformat() if isinstance(start, datetime) else start)

        if end:
            where_parts.append("timestamp <= ?")
            params.append(end.isoformat() if isinstance(end, datetime) else end)

        where = " AND ".join(where_parts)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT * FROM equity_points
                WHERE {where}
                ORDER BY timestamp ASC
                LIMIT ?
            """, params + [limit])
            return [dict(row) for row in cursor.fetchall()]

    def get_high_water_marks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all high water mark points.

        Args:
            limit: Maximum number of points to return.

        Returns:
            List of high water mark equity points.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM equity_points
                WHERE is_high_water_mark = TRUE
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]


# Allow running directly to initialize database
if __name__ == "__main__":
    db = Database()
    print(f"Database created at: {db.db_path}")
    print(f"Account state: {db.get_account_state()}")
