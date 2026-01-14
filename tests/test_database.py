"""Tests for the database module."""

import os
import tempfile
import pytest
from src.database import Database


class TestDatabase:
    """Test cases for the Database class."""

    def setup_method(self):
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_database_creation(self):
        """Test that database file is created."""
        assert os.path.exists(self.db_path)

    def test_tables_exist(self):
        """Test that all required tables are created."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        expected_tables = {
            'open_trades',
            'closed_trades',
            'learnings',
            'trading_rules',
            'activity_log',
            'account_state',
            'market_data'
        }
        assert expected_tables.issubset(tables)

    def test_account_state_initialized(self):
        """Test that account state is initialized with $1,000."""
        state = self.db.get_account_state()
        assert state['balance'] == 1000.0
        assert state['available_balance'] == 1000.0
        assert state['in_positions'] == 0.0
        assert state['total_pnl'] == 0.0
        assert state['daily_pnl'] == 0.0
        assert state['trade_count_today'] == 0

    def test_update_account_state(self):
        """Test updating account state."""
        self.db.update_account_state(balance=950.0, in_positions=50.0)
        state = self.db.get_account_state()
        assert state['balance'] == 950.0
        assert state['in_positions'] == 50.0

    def test_log_activity(self):
        """Test logging activity."""
        log_id = self.db.log_activity(
            activity_type='test',
            description='Test activity',
            details='{"key": "value"}'
        )
        assert log_id is not None
        assert log_id > 0

    def test_get_recent_activity(self):
        """Test retrieving recent activity."""
        # Log some activities
        self.db.log_activity('trade', 'Opened BTC position')
        self.db.log_activity('learning', 'Created new learning')
        self.db.log_activity('trade', 'Closed BTC position')

        activities = self.db.get_recent_activity(limit=2)
        assert len(activities) == 2
        # Most recent first
        assert activities[0]['activity_type'] == 'trade'
        assert 'Closed' in activities[0]['description']

    def test_indexes_created(self):
        """Test that indexes are created for performance."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}
        conn.close()

        expected_indexes = {
            'idx_open_trades_coin',
            'idx_open_trades_opened_at',
            'idx_closed_trades_coin',
            'idx_closed_trades_closed_at',
            'idx_learnings_created_at',
            'idx_trading_rules_status',
            'idx_activity_log_created_at',
            'idx_activity_log_type'
        }
        assert expected_indexes.issubset(indexes)


def test_database_import():
    """Test that Database can be imported."""
    from src.database import Database
    assert Database is not None
