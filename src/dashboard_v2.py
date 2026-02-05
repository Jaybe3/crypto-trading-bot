"""
Dashboard v2 - Trading System Observability UI.

Provides real-time visibility into system state, knowledge brain,
adaptations, and manual override controls for paper trading.

Usage:
    from src.dashboard_v2 import DashboardServer

    server = DashboardServer(trading_system)
    await server.start(port=8080)
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

if TYPE_CHECKING:
    from src.main import TradingSystem

logger = logging.getLogger("Dashboard")


# =============================================================================
# Pydantic Models for API
# =============================================================================

class BlacklistRequest(BaseModel):
    coin: str
    reason: str = "Manual override"


class UnblacklistRequest(BaseModel):
    coin: str


class PatternToggleRequest(BaseModel):
    pattern_id: str


class RuleToggleRequest(BaseModel):
    rule_id: str


class RollbackRequest(BaseModel):
    adaptation_id: str


class NoteRequest(BaseModel):
    content: str


# =============================================================================
# Dashboard Server
# =============================================================================

class DashboardServer:
    """
    FastAPI server for the trading dashboard.

    Provides API endpoints and serves the web UI for observing
    and controlling the trading system.
    """

    def __init__(self, trading_system: "TradingSystem"):
        """
        Initialize dashboard server.

        Args:
            trading_system: The TradingSystem instance to observe/control.
        """
        self.system = trading_system
        self.app = FastAPI(
            title="Trading Dashboard v2",
            description="Observability UI for autonomous trading system",
            version="2.0.0",
        )

        # Template directory
        self.template_dir = Path(__file__).parent.parent / "dashboard" / "templates"
        self.static_dir = Path(__file__).parent.parent / "dashboard" / "static"

        # Jinja2 templates
        self.templates = Jinja2Templates(directory=str(self.template_dir))

        # Session notes (in-memory for now)
        self._notes: list[dict] = []

        # Setup routes
        self._setup_routes()
        self._setup_static()

    def _setup_static(self) -> None:
        """Mount static files directory."""
        if self.static_dir.exists():
            self.app.mount(
                "/static",
                StaticFiles(directory=str(self.static_dir)),
                name="static"
            )

    def _setup_routes(self) -> None:
        """Set up all API and page routes."""

        # =====================================================================
        # Page Routes (HTML)
        # =====================================================================

        @self.app.get("/", response_class=HTMLResponse)
        async def index(request: Request):
            """Real-time view - home page."""
            return self.templates.TemplateResponse(
                "index.html",
                {"request": request, "page": "realtime"}
            )

        @self.app.get("/knowledge", response_class=HTMLResponse)
        async def knowledge_page(request: Request):
            """Knowledge brain browser."""
            return self.templates.TemplateResponse(
                "knowledge.html",
                {"request": request, "page": "knowledge"}
            )

        @self.app.get("/adaptations", response_class=HTMLResponse)
        async def adaptations_page(request: Request):
            """Adaptations log."""
            return self.templates.TemplateResponse(
                "adaptations.html",
                {"request": request, "page": "adaptations"}
            )

        @self.app.get("/profitability", response_class=HTMLResponse)
        async def profitability_page(request: Request):
            """Profitability stats."""
            return self.templates.TemplateResponse(
                "profitability.html",
                {"request": request, "page": "profitability"}
            )

        @self.app.get("/overrides", response_class=HTMLResponse)
        async def overrides_page(request: Request):
            """Manual overrides (paper trading)."""
            return self.templates.TemplateResponse(
                "overrides.html",
                {"request": request, "page": "overrides"}
            )

        # =====================================================================
        # Real-Time API
        # =====================================================================

        @self.app.get("/api/status")
        async def get_status():
            """Get system status, health, uptime."""
            status = self.system.get_status()

            # Add formatted uptime
            if status.get("health"):
                uptime = status["health"].get("uptime_seconds", 0)
                hours = int(uptime // 3600)
                minutes = int((uptime % 3600) // 60)
                status["uptime_formatted"] = f"{hours}h {minutes}m"

            return status

        @self.app.get("/api/conditions")
        async def get_conditions():
            """Get active conditions Sniper is watching."""
            conditions = self.system.get_conditions()
            return {
                "count": len(conditions),
                "conditions": [self._format_condition(c) for c in conditions],
            }

        @self.app.get("/api/positions")
        async def get_positions():
            """Get open positions with unrealized P&L."""
            positions = self.system.get_positions()

            # Add current prices for unrealized P&L
            formatted = []
            for pos in positions:
                current_price = None
                if self.system.health:
                    current_price = self.system.health.get_last_price(pos.get("coin", ""))

                pos_data = {
                    **pos,
                    "current_price": current_price,
                }

                # Calculate unrealized P&L if we have current price
                if current_price and pos.get("entry_price"):
                    entry = pos["entry_price"]
                    size = pos.get("size", 0)
                    direction = pos.get("direction", "long")

                    if direction == "long":
                        pos_data["unrealized_pnl"] = (current_price - entry) * size
                    else:
                        pos_data["unrealized_pnl"] = (entry - current_price) * size

                    pos_data["unrealized_pnl_pct"] = (
                        (pos_data["unrealized_pnl"] / (entry * size)) * 100
                        if entry * size > 0 else 0
                    )

                formatted.append(pos_data)

            return {"count": len(formatted), "positions": formatted}

        @self.app.get("/api/prices")
        async def get_prices():
            """Get current prices for watched coins."""
            prices = {}
            if self.system.health:
                for coin in self.system.coins:
                    price = self.system.health.get_last_price(coin)
                    if price:
                        prices[coin] = price

            return {"prices": prices, "count": len(prices)}

        @self.app.get("/api/feed")
        async def event_stream():
            """SSE endpoint for real-time updates."""
            async def generate():
                while True:
                    try:
                        data = self._get_feed_data()
                        yield f"data: {json.dumps(data)}\n\n"
                        await asyncio.sleep(1)
                    except Exception as e:
                        logger.error(f"SSE error: {e}")
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
                        await asyncio.sleep(5)

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        # =====================================================================
        # Knowledge Brain API
        # =====================================================================

        @self.app.get("/api/knowledge/coins")
        async def get_coins():
            """Get all coin scores with status."""
            if not self.system.knowledge:
                raise HTTPException(500, "Knowledge Brain not initialized")

            coins = self.system.knowledge.get_all_coins()
            return {
                "count": len(coins),
                "coins": [self._format_coin(c) for c in coins],
            }

        @self.app.get("/api/knowledge/coins/{coin}")
        async def get_coin_detail(coin: str):
            """Get detailed info for a specific coin."""
            if not self.system.knowledge:
                raise HTTPException(500, "Knowledge Brain not initialized")

            coin_data = self.system.knowledge.get_coin(coin.upper())
            if not coin_data:
                raise HTTPException(404, f"Coin {coin} not found")

            return self._format_coin(coin_data)

        @self.app.get("/api/knowledge/patterns")
        async def get_patterns():
            """Get all patterns with stats."""
            if not self.system.pattern_library:
                raise HTTPException(500, "Pattern Library not initialized")

            patterns = self.system.pattern_library.get_all_patterns()
            return {
                "count": len(patterns),
                "patterns": [self._format_pattern(p) for p in patterns],
            }

        @self.app.get("/api/knowledge/rules")
        async def get_rules():
            """Get all regime rules."""
            if not self.system.knowledge:
                raise HTTPException(500, "Knowledge Brain not initialized")

            rules = self.system.knowledge.get_all_rules()
            return {
                "count": len(rules),
                "rules": [self._format_rule(r) for r in rules],
            }

        @self.app.get("/api/knowledge/blacklist")
        async def get_blacklist():
            """Get blacklisted coins with reasons."""
            if not self.system.knowledge:
                raise HTTPException(500, "Knowledge Brain not initialized")

            blacklist = self.system.knowledge.get_blacklist()
            return {
                "count": len(blacklist),
                "coins": blacklist,
            }

        @self.app.get("/api/knowledge/context")
        async def get_knowledge_context():
            """Get full knowledge context (for Strategist)."""
            if not self.system.knowledge:
                raise HTTPException(500, "Knowledge Brain not initialized")

            return self.system.knowledge.get_context_for_strategist()

        # =====================================================================
        # Adaptations API
        # =====================================================================

        @self.app.get("/api/adaptations")
        async def get_adaptations(limit: int = 50):
            """Get recent adaptations with effectiveness."""
            if not self.system.db:
                raise HTTPException(500, "Database not initialized")

            adaptations = self.system.db.get_adaptations(limit=limit)
            return {
                "count": len(adaptations),
                "adaptations": [self._format_adaptation(a) for a in adaptations],
            }

        @self.app.get("/api/adaptations/effectiveness")
        async def get_effectiveness_summary():
            """Get effectiveness summary by rating."""
            summary = self.system.get_adaptation_effectiveness()
            if "error" in summary:
                raise HTTPException(500, summary["error"])
            return summary

        @self.app.get("/api/adaptations/{adaptation_id}")
        async def get_adaptation_detail(adaptation_id: str):
            """Get single adaptation detail."""
            if not self.system.db:
                raise HTTPException(500, "Database not initialized")

            adaptation = self.system.db.get_adaptation(adaptation_id)
            if not adaptation:
                raise HTTPException(404, f"Adaptation {adaptation_id} not found")

            return self._format_adaptation(adaptation)

        # =====================================================================
        # Profitability API
        # =====================================================================

        @self.app.get("/api/profitability/snapshot")
        async def get_profitability_snapshot(timeframe: str = "all_time"):
            """Get current profitability snapshot."""
            result = self.system.get_profitability_snapshot(timeframe)
            if "error" in result:
                raise HTTPException(500, result["error"])
            return result

        @self.app.get("/api/profitability/by/{dimension}")
        async def get_performance_by_dimension(dimension: str):
            """Get performance by coin/hour/day/pattern."""
            valid_dimensions = [
                "coin", "pattern", "hour_of_day", "day_of_week",
                "exit_reason", "position_size", "hold_duration"
            ]
            if dimension not in valid_dimensions:
                raise HTTPException(400, f"Invalid dimension. Use: {valid_dimensions}")

            result = self.system.get_performance_by_dimension(dimension)
            return {"dimension": dimension, "data": result}

        @self.app.get("/api/profitability/equity-curve")
        async def get_equity_curve():
            """Get equity curve data for charting."""
            data = self.system.get_equity_curve()
            return {"points": data, "count": len(data)}

        @self.app.get("/api/profitability/improvement")
        async def get_improvement(days: int = 7):
            """Is the system improving?"""
            result = self.system.get_improvement_metrics(days)
            if "error" in result:
                raise HTTPException(500, result["error"])
            return result

        # =====================================================================
        # Manual Overrides API (Paper Trading Only)
        # =====================================================================

        @self.app.post("/api/override/blacklist")
        async def blacklist_coin(request: BlacklistRequest):
            """Add coin to blacklist."""
            if not self.system.knowledge:
                raise HTTPException(500, "Knowledge Brain not initialized")

            coin = request.coin.upper()
            reason = f"Manual: {request.reason}"

            try:
                self.system.knowledge.blacklist_coin(coin, reason)
                logger.info(f"Manual blacklist: {coin} - {reason}")
                return {"success": True, "coin": coin, "reason": reason}
            except Exception as e:
                raise HTTPException(500, str(e))

        @self.app.post("/api/override/unblacklist")
        async def unblacklist_coin(request: UnblacklistRequest):
            """Remove coin from blacklist."""
            if not self.system.knowledge:
                raise HTTPException(500, "Knowledge Brain not initialized")

            coin = request.coin.upper()

            try:
                self.system.knowledge.unblacklist_coin(coin)
                logger.info(f"Manual unblacklist: {coin}")
                return {"success": True, "coin": coin}
            except Exception as e:
                raise HTTPException(500, str(e))

        @self.app.post("/api/override/disable-pattern")
        async def disable_pattern(request: PatternToggleRequest):
            """Disable a pattern."""
            if not self.system.pattern_library:
                raise HTTPException(500, "Pattern Library not initialized")

            try:
                self.system.pattern_library.deactivate_pattern(request.pattern_id)
                logger.info(f"Manual pattern disable: {request.pattern_id}")
                return {"success": True, "pattern_id": request.pattern_id}
            except Exception as e:
                raise HTTPException(500, str(e))

        @self.app.post("/api/override/enable-pattern")
        async def enable_pattern(request: PatternToggleRequest):
            """Enable a pattern."""
            if not self.system.knowledge:
                raise HTTPException(500, "Knowledge Brain not initialized")

            try:
                self.system.knowledge.reactivate_pattern(request.pattern_id)
                logger.info(f"Manual pattern enable: {request.pattern_id}")
                return {"success": True, "pattern_id": request.pattern_id}
            except Exception as e:
                raise HTTPException(500, str(e))

        @self.app.post("/api/override/deactivate-rule")
        async def deactivate_rule(request: RuleToggleRequest):
            """Deactivate a regime rule."""
            if not self.system.knowledge:
                raise HTTPException(500, "Knowledge Brain not initialized")

            try:
                self.system.knowledge.deactivate_rule(request.rule_id)
                logger.info(f"Manual rule deactivate: {request.rule_id}")
                return {"success": True, "rule_id": request.rule_id}
            except Exception as e:
                raise HTTPException(500, str(e))

        @self.app.post("/api/override/trigger-reflection")
        async def trigger_reflection():
            """Manually trigger a reflection cycle."""
            result = await self.system.trigger_reflection()
            if not result.get("success"):
                raise HTTPException(500, result.get("error", "Unknown error"))
            return result

        @self.app.post("/api/override/rollback")
        async def rollback_adaptation(request: RollbackRequest):
            """Rollback a harmful adaptation."""
            result = self.system.rollback_adaptation(request.adaptation_id)
            if not result.get("success"):
                raise HTTPException(500, result.get("error", "Unknown error"))
            return result

        @self.app.post("/api/override/pause")
        async def pause_trading():
            """Pause all trading."""
            self.system.pause_trading("Dashboard pause")
            return {"success": True, "message": "Trading paused"}

        @self.app.post("/api/override/resume")
        async def resume_trading():
            """Resume trading."""
            self.system.resume_trading()
            return {"success": True, "message": "Trading resumed"}

        @self.app.post("/api/notes")
        async def add_note(request: NoteRequest):
            """Add a session note."""
            note = {
                "timestamp": datetime.now().isoformat(),
                "content": request.content,
            }
            self._notes.append(note)
            logger.info(f"Note added: {request.content[:50]}...")
            return {"success": True, "note": note}

        @self.app.get("/api/notes")
        async def get_notes():
            """Get all session notes."""
            return {"notes": self._notes, "count": len(self._notes)}

        # =====================================================================
        # Health Check
        # =====================================================================

        @self.app.get("/api/health")
        async def health_check():
            """Full system health check."""
            return self.system.health_check()

        @self.app.get("/api/loop-stats")
        async def loop_stats():
            """Get learning loop statistics."""
            return self.system.get_loop_stats()

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_feed_data(self) -> dict:
        """Get data for SSE feed."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "prices": {},
            "conditions_count": 0,
            "positions_count": 0,
            "healthy": False,
        }

        if self.system.health:
            stats = self.system.health.get_stats()
            data["healthy"] = stats.get("healthy", False)
            data["ticks_per_second"] = stats.get("ticks_per_second", 0)

            # Get prices for all coins
            for coin in self.system.coins:
                price = self.system.health.get_last_price(coin)
                if price:
                    data["prices"][coin] = price

        if self.system.sniper:
            status = self.system.sniper.get_status()
            data["conditions_count"] = status.get("active_conditions", 0)
            data["positions_count"] = status.get("open_positions", 0)
            data["balance"] = status.get("balance", 0)
            data["total_pnl"] = status.get("total_pnl", 0)

        return data

    def _format_condition(self, cond) -> dict:
        """Format a condition for API response."""
        if hasattr(cond, "to_dict"):
            return cond.to_dict()
        return dict(cond) if cond else {}

    def _format_coin(self, coin) -> dict:
        """Format a coin for API response."""
        if hasattr(coin, "to_dict"):
            return coin.to_dict()
        return dict(coin) if coin else {}

    def _format_pattern(self, pattern) -> dict:
        """Format a pattern for API response."""
        if hasattr(pattern, "to_dict"):
            return pattern.to_dict()
        return dict(pattern) if pattern else {}

    def _format_rule(self, rule) -> dict:
        """Format a rule for API response."""
        if hasattr(rule, "to_dict"):
            return rule.to_dict()
        return dict(rule) if rule else {}

    def _format_adaptation(self, adaptation) -> dict:
        """Format an adaptation for API response."""
        if isinstance(adaptation, dict):
            # Add relative time
            if "applied_at" in adaptation:
                try:
                    applied = datetime.fromisoformat(adaptation["applied_at"])
                    delta = datetime.now() - applied
                    hours = delta.total_seconds() / 3600
                    if hours < 1:
                        adaptation["relative_time"] = f"{int(delta.total_seconds() / 60)}m ago"
                    elif hours < 24:
                        adaptation["relative_time"] = f"{int(hours)}h ago"
                    else:
                        adaptation["relative_time"] = f"{int(hours / 24)}d ago"
                except (ValueError, TypeError):
                    adaptation["relative_time"] = "unknown"
            return adaptation

        if hasattr(adaptation, "to_dict"):
            return adaptation.to_dict()
        return dict(adaptation) if adaptation else {}

    def get_health(self) -> dict:
        """Get dashboard health status."""
        return {
            "status": "healthy",
            "template_dir_exists": self.template_dir.exists(),
            "static_dir_exists": self.static_dir.exists(),
        }

    async def start(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        """
        Start the dashboard server.

        Args:
            host: Host to bind to.
            port: Port to listen on.
        """
        import uvicorn

        logger.info(f"Starting dashboard on http://{host}:{port}")

        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_level="info",
            access_log=False,
        )
        server = uvicorn.Server(config)
        await server.serve()
