"""Tests for the dashboard module."""

import os
import tempfile
import pytest

from src.dashboard import app, DashboardData
from src.database import Database


class TestDashboardData:
    """Test cases for the DashboardData class."""

    def setup_method(self):
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)
        self.dashboard_data = DashboardData(db=self.db)

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_get_account_state(self):
        """Test getting account state."""
        state = self.dashboard_data.get_account_state()
        assert state['balance'] == 1000.0
        assert state['available_balance'] == 1000.0
        assert state['in_positions'] == 0.0

    def test_get_market_data_empty(self):
        """Test getting market data when empty."""
        data = self.dashboard_data.get_market_data()
        assert data == {}

    def test_get_open_trades_empty(self):
        """Test getting open trades when empty."""
        trades = self.dashboard_data.get_open_trades()
        assert trades == []

    def test_get_closed_trades_empty(self):
        """Test getting closed trades when empty."""
        trades = self.dashboard_data.get_closed_trades()
        assert trades == []


class TestDashboardRoutes:
    """Test cases for dashboard Flask routes."""

    def setup_method(self):
        """Set up Flask test client."""
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_index_route(self):
        """Test main dashboard route returns 200."""
        response = self.client.get('/')
        assert response.status_code == 200
        assert b'Crypto Trading Bot' in response.data

    def test_index_contains_market_data_section(self):
        """Test dashboard contains market data section."""
        response = self.client.get('/')
        assert b'Market Data' in response.data

    def test_index_contains_account_state_section(self):
        """Test dashboard contains account state section."""
        response = self.client.get('/')
        assert b'Account State' in response.data

    def test_index_contains_open_trades_section(self):
        """Test dashboard contains open trades section."""
        response = self.client.get('/')
        assert b'Open Trades' in response.data

    def test_index_contains_closed_trades_section(self):
        """Test dashboard contains closed trades section."""
        response = self.client.get('/')
        assert b'Closed Trades' in response.data

    def test_api_status_route(self):
        """Test API status endpoint returns JSON."""
        response = self.client.get('/api/status')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_api_status_contains_required_fields(self):
        """Test API status contains required fields."""
        response = self.client.get('/api/status')
        data = response.get_json()

        assert 'status' in data
        assert 'market_data' in data
        assert 'account' in data
        assert 'open_trades' in data
        assert 'closed_trades' in data
        assert 'timestamp' in data

    def test_api_status_account_balance(self):
        """Test API returns correct account balance."""
        response = self.client.get('/api/status')
        data = response.get_json()

        assert data['account']['balance'] == 1000.0


def test_dashboard_import():
    """Test that dashboard can be imported."""
    from src.dashboard import app, DashboardData, run_dashboard
    assert app is not None
    assert DashboardData is not None
    assert run_dashboard is not None
