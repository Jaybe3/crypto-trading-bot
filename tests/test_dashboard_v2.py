"""Tests for Dashboard v2 (TASK-143)."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from src.dashboard_v2 import (
    DashboardServer,
    BlacklistRequest,
    UnblacklistRequest,
    PatternToggleRequest,
    RuleToggleRequest,
    RollbackRequest,
    NoteRequest,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_trading_system():
    """Create a mock TradingSystem for testing."""
    system = MagicMock()

    # Basic attributes
    system.coins = ["BTC", "ETH", "SOL"]
    system.test_mode = False
    system._running = True
    system._start_time = datetime.now()

    # Health monitor
    system.health = MagicMock()
    system.health.get_stats.return_value = {
        "healthy": True,
        "feed_stale": False,
        "uptime_seconds": 3600,
        "ticks_per_second": 100.5,
        "tick_count": 10000,
        "error_count": 0,
    }
    system.health.get_last_price.side_effect = lambda coin: {
        "BTC": 67000.0,
        "ETH": 3400.0,
        "SOL": 140.0,
    }.get(coin)

    # Sniper
    system.sniper = MagicMock()
    system.sniper.get_status.return_value = {
        "active_conditions": 2,
        "open_positions": 1,
        "balance": 10500.0,
        "total_pnl": 500.0,
    }

    # Get methods
    system.get_status.return_value = {
        "running": True,
        "test_mode": False,
        "health": {"uptime_seconds": 3600, "healthy": True},
    }
    system.get_conditions.return_value = []
    system.get_positions.return_value = []

    # Knowledge Brain
    system.knowledge = MagicMock()
    system.knowledge.get_all_coins.return_value = [
        MagicMock(to_dict=lambda: {
            "coin": "BTC", "total_trades": 50, "win_rate": 55.0,
            "total_pnl": 250.0, "status": "active", "is_blacklisted": False
        }),
        MagicMock(to_dict=lambda: {
            "coin": "ETH", "total_trades": 30, "win_rate": 60.0,
            "total_pnl": 180.0, "status": "favored", "is_blacklisted": False
        }),
    ]
    system.knowledge.get_coin.return_value = MagicMock(
        to_dict=lambda: {"coin": "BTC", "total_trades": 50}
    )
    system.knowledge.get_all_rules.return_value = []
    system.knowledge.get_blacklist.return_value = []
    system.knowledge.get_context_for_strategist.return_value = {"coins": [], "patterns": []}

    # Pattern Library
    system.pattern_library = MagicMock()
    system.pattern_library.get_all_patterns.return_value = []

    # Database
    system.db = MagicMock()
    system.db.get_adaptations.return_value = []
    system.db.get_adaptation.return_value = None

    # Profitability
    system.get_profitability_snapshot.return_value = {
        "total_pnl": 500.0,
        "win_rate": 55.0,
        "total_trades": 100,
        "profit_factor": 1.35,
    }
    system.get_performance_by_dimension.return_value = []
    system.get_equity_curve.return_value = []
    system.get_improvement_metrics.return_value = {"improving": True}

    # Effectiveness
    system.get_adaptation_effectiveness.return_value = {
        "highly_effective": 2,
        "effective": 5,
        "neutral": 3,
        "ineffective": 1,
        "harmful": 0,
        "pending": 4,
    }
    system.get_harmful_adaptations.return_value = []
    system.rollback_adaptation.return_value = {"success": True}

    # Health check
    system.health_check.return_value = {
        "overall": "healthy",
        "components": {},
    }
    system.get_loop_stats.return_value = {
        "uptime_hours": 1.0,
        "total_trades": 100,
    }

    # Async methods
    system.trigger_reflection = AsyncMock(return_value={
        "success": True,
        "trades_analyzed": 10,
        "insights_count": 2,
    })

    # Control methods
    system.pause_trading = MagicMock()
    system.resume_trading = MagicMock()

    return system


@pytest.fixture
def dashboard(mock_trading_system):
    """Create DashboardServer with mocked system."""
    return DashboardServer(mock_trading_system)


@pytest.fixture
def client(dashboard):
    """Create test client for dashboard API."""
    return TestClient(dashboard.app)


# =============================================================================
# API Endpoint Tests
# =============================================================================

class TestStatusEndpoints:
    """Test real-time status endpoints."""

    def test_get_status(self, client):
        """Test /api/status returns system status."""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data

    def test_get_conditions(self, client):
        """Test /api/conditions returns conditions list."""
        response = client.get("/api/conditions")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "conditions" in data

    def test_get_positions(self, client):
        """Test /api/positions returns positions list."""
        response = client.get("/api/positions")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "positions" in data

    def test_get_prices(self, client):
        """Test /api/prices returns current prices."""
        response = client.get("/api/prices")
        assert response.status_code == 200
        data = response.json()
        assert "prices" in data
        assert "count" in data


class TestKnowledgeEndpoints:
    """Test Knowledge Brain API endpoints."""

    def test_get_coins(self, client):
        """Test /api/knowledge/coins returns coin list."""
        response = client.get("/api/knowledge/coins")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "coins" in data
        assert len(data["coins"]) == 2

    def test_get_coin_detail(self, client):
        """Test /api/knowledge/coins/{coin} returns coin detail."""
        response = client.get("/api/knowledge/coins/BTC")
        assert response.status_code == 200
        data = response.json()
        assert data["coin"] == "BTC"

    def test_get_coin_not_found(self, client, mock_trading_system):
        """Test 404 when coin not found."""
        mock_trading_system.knowledge.get_coin.return_value = None
        response = client.get("/api/knowledge/coins/NOTACOIN")
        assert response.status_code == 404

    def test_get_patterns(self, client):
        """Test /api/knowledge/patterns returns patterns."""
        response = client.get("/api/knowledge/patterns")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "patterns" in data

    def test_get_rules(self, client):
        """Test /api/knowledge/rules returns rules."""
        response = client.get("/api/knowledge/rules")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "rules" in data

    def test_get_blacklist(self, client):
        """Test /api/knowledge/blacklist returns blacklist."""
        response = client.get("/api/knowledge/blacklist")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "coins" in data


class TestAdaptationsEndpoints:
    """Test Adaptations API endpoints."""

    def test_get_adaptations(self, client):
        """Test /api/adaptations returns adaptation list."""
        response = client.get("/api/adaptations")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "adaptations" in data

    def test_get_adaptations_with_limit(self, client):
        """Test /api/adaptations respects limit parameter."""
        response = client.get("/api/adaptations?limit=10")
        assert response.status_code == 200

    def test_get_effectiveness_summary(self, client):
        """Test /api/adaptations/effectiveness returns summary."""
        response = client.get("/api/adaptations/effectiveness")
        assert response.status_code == 200
        data = response.json()
        assert "highly_effective" in data
        assert "harmful" in data


class TestProfitabilityEndpoints:
    """Test Profitability API endpoints."""

    def test_get_snapshot(self, client):
        """Test /api/profitability/snapshot returns snapshot."""
        response = client.get("/api/profitability/snapshot")
        assert response.status_code == 200
        data = response.json()
        assert "total_pnl" in data
        assert "win_rate" in data

    def test_get_snapshot_with_timeframe(self, client):
        """Test /api/profitability/snapshot with timeframe."""
        response = client.get("/api/profitability/snapshot?timeframe=day")
        assert response.status_code == 200

    def test_get_performance_by_dimension(self, client):
        """Test /api/profitability/by/{dimension} returns breakdown."""
        response = client.get("/api/profitability/by/coin")
        assert response.status_code == 200
        data = response.json()
        assert data["dimension"] == "coin"
        assert "data" in data

    def test_get_invalid_dimension(self, client):
        """Test 400 for invalid dimension."""
        response = client.get("/api/profitability/by/invalid")
        assert response.status_code == 400

    def test_get_equity_curve(self, client):
        """Test /api/profitability/equity-curve returns data."""
        response = client.get("/api/profitability/equity-curve")
        assert response.status_code == 200
        data = response.json()
        assert "points" in data
        assert "count" in data

    def test_get_improvement(self, client):
        """Test /api/profitability/improvement returns metrics."""
        response = client.get("/api/profitability/improvement")
        assert response.status_code == 200


class TestOverrideEndpoints:
    """Test Manual Override API endpoints."""

    def test_blacklist_coin(self, client, mock_trading_system):
        """Test POST /api/override/blacklist."""
        response = client.post(
            "/api/override/blacklist",
            json={"coin": "DOGE", "reason": "Test blacklist"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["coin"] == "DOGE"
        mock_trading_system.knowledge.blacklist_coin.assert_called_once()

    def test_unblacklist_coin(self, client, mock_trading_system):
        """Test POST /api/override/unblacklist."""
        response = client.post(
            "/api/override/unblacklist",
            json={"coin": "DOGE"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_trading_system.knowledge.unblacklist_coin.assert_called_once()

    def test_disable_pattern(self, client, mock_trading_system):
        """Test POST /api/override/disable-pattern."""
        response = client.post(
            "/api/override/disable-pattern",
            json={"pattern_id": "momentum_breakout"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_trading_system.pattern_library.deactivate_pattern.assert_called_once()

    def test_enable_pattern(self, client, mock_trading_system):
        """Test POST /api/override/enable-pattern."""
        response = client.post(
            "/api/override/enable-pattern",
            json={"pattern_id": "momentum_breakout"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_trading_system.knowledge.reactivate_pattern.assert_called_once()

    def test_deactivate_rule(self, client, mock_trading_system):
        """Test POST /api/override/deactivate-rule."""
        response = client.post(
            "/api/override/deactivate-rule",
            json={"rule_id": "time_filter_0203"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_trading_system.knowledge.deactivate_rule.assert_called_once()

    def test_pause_trading(self, client, mock_trading_system):
        """Test POST /api/override/pause."""
        response = client.post("/api/override/pause")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_trading_system.pause_trading.assert_called_once()

    def test_resume_trading(self, client, mock_trading_system):
        """Test POST /api/override/resume."""
        response = client.post("/api/override/resume")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_trading_system.resume_trading.assert_called_once()

    def test_rollback_adaptation(self, client, mock_trading_system):
        """Test POST /api/override/rollback."""
        response = client.post(
            "/api/override/rollback",
            json={"adaptation_id": "abc123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestNotesEndpoints:
    """Test session notes endpoints."""

    def test_add_note(self, client):
        """Test POST /api/notes adds a note."""
        response = client.post(
            "/api/notes",
            json={"content": "Test note content"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "note" in data

    def test_get_notes(self, client):
        """Test GET /api/notes returns notes list."""
        # Add a note first
        client.post("/api/notes", json={"content": "Test note"})

        response = client.get("/api/notes")
        assert response.status_code == 200
        data = response.json()
        assert "notes" in data
        assert data["count"] >= 1


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, client):
        """Test /api/health returns health status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "overall" in data

    def test_loop_stats(self, client):
        """Test /api/loop-stats returns statistics."""
        response = client.get("/api/loop-stats")
        assert response.status_code == 200
        data = response.json()
        assert "uptime_hours" in data


# =============================================================================
# Helper Method Tests
# =============================================================================

class TestHelperMethods:
    """Test dashboard helper methods."""

    def test_format_adaptation_with_timestamp(self, dashboard):
        """Test _format_adaptation adds relative time."""
        adaptation = {
            "applied_at": datetime.now().isoformat(),
            "action": "BLACKLIST",
            "target": "DOGE",
        }
        formatted = dashboard._format_adaptation(adaptation)
        assert "relative_time" in formatted

    def test_format_adaptation_dict_passthrough(self, dashboard):
        """Test _format_adaptation handles dicts."""
        adaptation = {"action": "TEST", "target": "BTC"}
        formatted = dashboard._format_adaptation(adaptation)
        assert formatted["action"] == "TEST"

    def test_get_feed_data(self, dashboard, mock_trading_system):
        """Test _get_feed_data returns correct structure."""
        data = dashboard._get_feed_data()
        assert "timestamp" in data
        assert "prices" in data
        assert "healthy" in data
        assert data["healthy"] is True

    def test_get_health(self, dashboard):
        """Test get_health returns dashboard health."""
        health = dashboard.get_health()
        assert health["status"] == "healthy"


# =============================================================================
# Page Route Tests
# =============================================================================

class TestPageRoutes:
    """Test HTML page routes are registered."""

    def test_index_route_exists(self, dashboard):
        """Test / route is registered."""
        routes = [r.path for r in dashboard.app.routes]
        assert "/" in routes

    def test_knowledge_page_route_exists(self, dashboard):
        """Test /knowledge route is registered."""
        routes = [r.path for r in dashboard.app.routes]
        assert "/knowledge" in routes

    def test_adaptations_page_route_exists(self, dashboard):
        """Test /adaptations route is registered."""
        routes = [r.path for r in dashboard.app.routes]
        assert "/adaptations" in routes

    def test_profitability_page_route_exists(self, dashboard):
        """Test /profitability route is registered."""
        routes = [r.path for r in dashboard.app.routes]
        assert "/profitability" in routes

    def test_overrides_page_route_exists(self, dashboard):
        """Test /overrides route is registered."""
        routes = [r.path for r in dashboard.app.routes]
        assert "/overrides" in routes


# =============================================================================
# Pydantic Model Tests
# =============================================================================

class TestPydanticModels:
    """Test request/response models."""

    def test_blacklist_request_defaults(self):
        """Test BlacklistRequest has default reason."""
        req = BlacklistRequest(coin="DOGE")
        assert req.reason == "Manual override"

    def test_blacklist_request_custom_reason(self):
        """Test BlacklistRequest accepts custom reason."""
        req = BlacklistRequest(coin="DOGE", reason="Too volatile")
        assert req.reason == "Too volatile"

    def test_unblacklist_request(self):
        """Test UnblacklistRequest."""
        req = UnblacklistRequest(coin="DOGE")
        assert req.coin == "DOGE"

    def test_pattern_toggle_request(self):
        """Test PatternToggleRequest."""
        req = PatternToggleRequest(pattern_id="momentum_breakout")
        assert req.pattern_id == "momentum_breakout"

    def test_rule_toggle_request(self):
        """Test RuleToggleRequest."""
        req = RuleToggleRequest(rule_id="time_filter")
        assert req.rule_id == "time_filter"

    def test_rollback_request(self):
        """Test RollbackRequest."""
        req = RollbackRequest(adaptation_id="abc123")
        assert req.adaptation_id == "abc123"

    def test_note_request(self):
        """Test NoteRequest."""
        req = NoteRequest(content="Test note")
        assert req.content == "Test note"
