"""Tests for Phase 3 integration - technical + sentiment data in LLM prompt."""

import pytest
from unittest.mock import MagicMock, patch
from src.strategist import Strategist


class TestPhase3Integration:
    """Test that Phase 3 data flows from managers to LLM prompt."""

    def _create_strategist(self, technical_manager=None, context_manager=None):
        """Create a Strategist with mocked dependencies."""
        # Mock market_feed
        market = MagicMock()
        market.get_all_prices.return_value = {
            "BTC": MagicMock(price=50000.0, change_24h=2.5),
            "ETH": MagicMock(price=3000.0, change_24h=-1.2),
        }

        # Mock llm
        llm = MagicMock()

        # Mock db
        db = MagicMock()
        db.get_account_state.return_value = {
            "balance": 10000, "available_balance": 9000, "daily_pnl": 50
        }

        return Strategist(
            llm=llm,
            market_feed=market,
            db=db,
            technical_manager=technical_manager,
            context_manager=context_manager,
        )

    def test_prompt_works_without_phase3(self):
        """Backward compatibility: no Phase 3 managers = no crash."""
        strat = self._create_strategist()
        context = strat._build_context()
        prompt = strat._build_prompt(context)
        assert "CURRENT MARKET STATE" in prompt
        assert "BTC" in prompt
        # No technical or sentiment sections
        assert "TECHNICAL ANALYSIS" not in prompt

    def test_prompt_includes_technical_data(self):
        """When TechnicalManager returns data, prompt contains it."""
        tech_mgr = MagicMock()
        snapshot = MagicMock()
        snapshot.to_prompt.return_value = "=== BTC TECHNICAL ===\nRSI: 45.2 (neutral)"
        tech_mgr.get_technical_snapshot.return_value = snapshot

        strat = self._create_strategist(technical_manager=tech_mgr)
        context = strat._build_context()
        prompt = strat._build_prompt(context)
        assert "TECHNICAL ANALYSIS" in prompt
        assert "RSI" in prompt

    def test_prompt_includes_sentiment_data(self):
        """When ContextManager returns data, prompt contains it."""
        ctx_mgr = MagicMock()
        market_ctx = MagicMock()
        market_ctx.to_prompt.return_value = "=== MARKET CONTEXT ===\nFear & Greed: 25 (Extreme Fear)"
        ctx_mgr.get_context.return_value = market_ctx
        ctx_mgr.get_coin_context.return_value = None

        strat = self._create_strategist(context_manager=ctx_mgr)
        context = strat._build_context()
        prompt = strat._build_prompt(context)
        assert "Fear & Greed" in prompt

    def test_technical_failure_doesnt_crash(self):
        """If TechnicalManager throws, _build_context still returns."""
        tech_mgr = MagicMock()
        tech_mgr.get_technical_snapshot.side_effect = Exception("API timeout")

        strat = self._create_strategist(technical_manager=tech_mgr)
        context = strat._build_context()  # Should not raise
        assert "technical" in context
        assert context["technical"] == {}  # Empty, not crashed

    def test_sentiment_failure_doesnt_crash(self):
        """If ContextManager throws, _build_context still returns."""
        ctx_mgr = MagicMock()
        ctx_mgr.get_context.side_effect = Exception("Rate limited")
        ctx_mgr.get_coin_context.side_effect = Exception("Rate limited")

        strat = self._create_strategist(context_manager=ctx_mgr)
        context = strat._build_context()  # Should not raise
        assert "sentiment" in context

    def test_prompt_token_budget(self):
        """Full prompt with Phase 3 data stays under budget."""
        # Create realistic mocks
        tech_mgr = MagicMock()
        snapshot = MagicMock()
        snapshot.to_prompt.return_value = (
            "=== BTC TECHNICAL ===\n"
            "RSI: 45.2 (neutral)\n"
            "VWAP: $50100.00 (+0.2%, above)\n"
            "ATR: $1200.00 (2.4% volatility)\n"
            "Funding: 0.0100% (bullish)\n"
            "Support: $48500.00 (3.0% below)\n"
            "Resistance: $52000.00 (4.0% above)\n"
            "POC: $49800.00 (above)\n"
            "Order Book: bullish (imbalance: +0.15)"
        )
        tech_mgr.get_technical_snapshot.return_value = snapshot

        ctx_mgr = MagicMock()
        market_ctx = MagicMock()
        market_ctx.to_prompt.return_value = (
            "=== MARKET CONTEXT ===\n"
            "Fear & Greed: 25 (Extreme Fear)\n"
            "BTC: +1.2% (1h), +2.5% (24h)\n"
            "⚠️ EXTREME FEAR - Market may be oversold"
        )
        ctx_mgr.get_context.return_value = market_ctx
        coin_ctx = MagicMock()
        coin_ctx.to_prompt.return_value = (
            "=== BTC CONTEXT ===\n"
            "Social: Rank #1, Sentiment 65/100 (Bullish)\n"
            "Recent News: 2 items\n"
            "  🟢 Bitcoin ETF inflows hit record..."
        )
        ctx_mgr.get_coin_context.return_value = coin_ctx

        strat = self._create_strategist(
            technical_manager=tech_mgr,
            context_manager=ctx_mgr,
        )
        context = strat._build_context()
        prompt = strat._build_prompt(context)

        # Rough token estimate: ~4 chars per token
        estimated_tokens = len(prompt) / 4
        assert estimated_tokens < 8000, f"Prompt too large: ~{estimated_tokens:.0f} tokens"
