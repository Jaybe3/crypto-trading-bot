"""
Tests for Deep Reflection Engine.

TASK-131: Tests for periodic LLM-powered analysis and insight generation.
"""

import os
import tempfile
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.models.reflection import (
    CoinAnalysis,
    PatternAnalysis,
    TimeAnalysis,
    RegimeAnalysis,
    ExitAnalysis,
    Insight,
    ReflectionResult,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    from src.database import Database

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(path)
    yield db
    os.unlink(path)


@pytest.fixture
def knowledge_brain(temp_db):
    """Create a KnowledgeBrain."""
    from src.knowledge import KnowledgeBrain

    return KnowledgeBrain(temp_db)


@pytest.fixture
def mock_journal():
    """Create a mock TradeJournal with test trades."""
    from src.journal import JournalEntry

    journal = Mock()

    # Create test trades
    trades = []
    base_time = datetime.now() - timedelta(hours=12)

    # SOL trades - mostly winners
    for i in range(8):
        won = i < 6  # 6 wins, 2 losses
        trades.append(JournalEntry(
            id=f"sol-{i}",
            position_id=f"pos-sol-{i}",
            entry_time=base_time + timedelta(minutes=i*30),
            entry_price=100.0,
            entry_reason="Test",
            coin="SOL",
            direction="LONG",
            position_size_usd=50.0,
            stop_loss_price=98.0,
            take_profit_price=102.0,
            strategy_id="test_strategy",
            condition_id=f"cond-{i}",
            hour_of_day=(base_time.hour + i) % 24,
            day_of_week=base_time.weekday(),
            btc_trend="up" if i % 2 == 0 else "sideways",
            exit_time=base_time + timedelta(minutes=i*30 + 15),
            exit_price=102.0 if won else 98.0,
            exit_reason="take_profit" if won else "stop_loss",
            pnl_usd=1.0 if won else -1.0,
            status="closed",
        ))

    # DOGE trades - mostly losers
    for i in range(5):
        won = i == 0  # 1 win, 4 losses
        trades.append(JournalEntry(
            id=f"doge-{i}",
            position_id=f"pos-doge-{i}",
            entry_time=base_time + timedelta(minutes=i*40),
            entry_price=0.12,
            entry_reason="Test",
            coin="DOGE",
            direction="LONG",
            position_size_usd=50.0,
            stop_loss_price=0.118,
            take_profit_price=0.122,
            strategy_id="test_strategy",
            condition_id=f"cond-doge-{i}",
            hour_of_day=(base_time.hour + i + 3) % 24,
            day_of_week=base_time.weekday(),
            btc_trend="down",
            exit_time=base_time + timedelta(minutes=i*40 + 20),
            exit_price=0.122 if won else 0.118,
            exit_reason="take_profit" if won else "stop_loss",
            pnl_usd=0.83 if won else -0.83,
            status="closed",
        ))

    journal.get_recent.return_value = trades
    return journal


@pytest.fixture
def mock_llm():
    """Create a mock LLM that returns valid JSON."""
    llm = Mock()
    llm.query.return_value = '''{
        "summary": "Test reflection summary. SOL is performing well with 75% win rate while DOGE is underperforming.",
        "insights": [
            {
                "insight_type": "coin",
                "category": "opportunity",
                "title": "SOL is strong performer",
                "description": "SOL has 75% win rate over 8 trades",
                "evidence": {"win_rate": 0.75, "trades": 8},
                "suggested_action": "Consider favoring SOL",
                "confidence": 0.85
            },
            {
                "insight_type": "coin",
                "category": "problem",
                "title": "DOGE underperforming",
                "description": "DOGE has only 20% win rate",
                "evidence": {"win_rate": 0.20, "trades": 5},
                "suggested_action": "Consider blacklisting DOGE",
                "confidence": 0.90
            }
        ]
    }'''
    return llm


@pytest.fixture
def reflection_engine(mock_journal, knowledge_brain, mock_llm, temp_db):
    """Create a ReflectionEngine with mocks."""
    from src.reflection import ReflectionEngine

    return ReflectionEngine(
        journal=mock_journal,
        knowledge=knowledge_brain,
        llm=mock_llm,
        db=temp_db,
    )


class TestInsightDataclass:
    """Tests for Insight dataclass."""

    def test_insight_from_dict(self):
        """Can create Insight from dictionary."""
        data = {
            "insight_type": "coin",
            "category": "problem",
            "title": "Test insight",
            "description": "This is a test",
            "evidence": {"metric": 42},
            "suggested_action": "Do something",
            "confidence": 0.75,
        }

        insight = Insight.from_dict(data)

        assert insight.insight_type == "coin"
        assert insight.category == "problem"
        assert insight.title == "Test insight"
        assert insight.confidence == 0.75

    def test_insight_to_dict(self):
        """Insight can be serialized to dict."""
        insight = Insight(
            insight_type="time",
            category="observation",
            title="Test",
            description="Description",
            evidence={"hour": 14},
        )

        d = insight.to_dict()

        assert d["insight_type"] == "time"
        assert d["evidence"]["hour"] == 14

    def test_insight_str(self):
        """Insight string representation is readable."""
        insight = Insight(
            insight_type="coin",
            category="opportunity",
            title="SOL is great",
            description="SOL has 80% win rate",
            evidence={},
            suggested_action="Favor SOL",
        )

        s = str(insight)
        assert "coin" in s
        assert "opportunity" in s
        assert "SOL is great" in s


class TestCoinAnalysis:
    """Tests for coin performance analysis."""

    def test_analyze_by_coin(self, reflection_engine, mock_journal):
        """Coin analysis calculates correct metrics."""
        trades = mock_journal.get_recent()

        analyses = reflection_engine._analyze_by_coin(trades)

        # Should have SOL and DOGE
        coins = {a.coin for a in analyses}
        assert "SOL" in coins
        assert "DOGE" in coins

        # SOL should be first (higher P&L)
        sol = next(a for a in analyses if a.coin == "SOL")
        assert sol.total_trades == 8
        assert sol.wins == 6
        assert sol.win_rate == 0.75

        # DOGE should have low win rate
        doge = next(a for a in analyses if a.coin == "DOGE")
        assert doge.total_trades == 5
        assert doge.wins == 1
        assert doge.win_rate == 0.2


class TestTimeAnalysis:
    """Tests for time-based analysis."""

    def test_analyze_by_time(self, reflection_engine, mock_journal):
        """Time analysis identifies best/worst hours."""
        trades = mock_journal.get_recent()

        analysis = reflection_engine._analyze_by_time(trades)

        assert isinstance(analysis, TimeAnalysis)
        assert len(analysis.hour_win_rates) > 0
        assert len(analysis.day_win_rates) > 0


class TestRegimeAnalysis:
    """Tests for market regime analysis."""

    def test_analyze_by_regime(self, reflection_engine, mock_journal):
        """Regime analysis separates by BTC trend."""
        trades = mock_journal.get_recent()

        analysis = reflection_engine._analyze_by_regime(trades)

        assert isinstance(analysis, RegimeAnalysis)
        # Should have some trades in different regimes
        total = analysis.btc_up_trades + analysis.btc_down_trades + analysis.btc_sideways_trades
        assert total > 0


class TestExitAnalysis:
    """Tests for exit analysis."""

    def test_analyze_exits(self, reflection_engine, mock_journal):
        """Exit analysis calculates stop-loss rate."""
        trades = mock_journal.get_recent()

        analysis = reflection_engine._analyze_exits(trades)

        assert isinstance(analysis, ExitAnalysis)
        assert analysis.total_exits == 13  # 8 SOL + 5 DOGE
        assert analysis.stop_loss_count > 0
        assert analysis.take_profit_count > 0


class TestLLMInsightGeneration:
    """Tests for LLM insight generation."""

    def test_generate_insights(self, reflection_engine, mock_journal, mock_llm):
        """LLM generates structured insights."""
        import asyncio

        async def run_test():
            trades = mock_journal.get_recent()

            coin_analyses = reflection_engine._analyze_by_coin(trades)
            pattern_analyses = reflection_engine._analyze_by_pattern(trades)
            time_analysis = reflection_engine._analyze_by_time(trades)
            regime_analysis = reflection_engine._analyze_by_regime(trades)
            exit_analysis = reflection_engine._analyze_exits(trades)

            insights, summary = await reflection_engine._generate_insights(
                trades=trades,
                coin_analyses=coin_analyses,
                pattern_analyses=pattern_analyses,
                time_analysis=time_analysis,
                regime_analysis=regime_analysis,
                exit_analysis=exit_analysis,
                period_hours=12.0,
                total_pnl=5.0,
                win_rate=0.54,
            )

            assert len(insights) == 2
            assert "SOL" in summary
            assert insights[0].insight_type == "coin"

        asyncio.run(run_test())

    def test_parse_llm_response(self, reflection_engine):
        """Can parse valid LLM JSON response."""
        response = '''{
            "summary": "Test summary",
            "insights": [
                {
                    "insight_type": "coin",
                    "category": "problem",
                    "title": "Test",
                    "description": "Test desc",
                    "evidence": {},
                    "confidence": 0.8
                }
            ]
        }'''

        insights, summary = reflection_engine._parse_llm_response(response)

        assert summary == "Test summary"
        assert len(insights) == 1
        assert insights[0].confidence == 0.8

    def test_parse_llm_response_with_markdown(self, reflection_engine):
        """Handles LLM response wrapped in markdown."""
        response = '''```json
{
    "summary": "Wrapped response",
    "insights": []
}
```'''

        insights, summary = reflection_engine._parse_llm_response(response)

        assert summary == "Wrapped response"


class TestTriggerConditions:
    """Tests for reflection trigger conditions."""

    def test_should_reflect_time_trigger(self, reflection_engine):
        """Triggers after time threshold."""
        reflection_engine.last_reflection_time = datetime.now() - timedelta(hours=2)
        reflection_engine.trades_since_reflection = 0

        assert reflection_engine.should_reflect() is True

    def test_should_reflect_trade_trigger(self, reflection_engine):
        """Triggers after trade count threshold."""
        reflection_engine.last_reflection_time = datetime.now()
        reflection_engine.trades_since_reflection = 10

        assert reflection_engine.should_reflect() is True

    def test_should_not_reflect_early(self, reflection_engine):
        """Does not trigger if thresholds not met."""
        reflection_engine.last_reflection_time = datetime.now()
        reflection_engine.trades_since_reflection = 3

        assert reflection_engine.should_reflect() is False

    def test_initial_reflection_needs_min_trades(self, reflection_engine):
        """Initial reflection requires minimum trades."""
        reflection_engine.last_reflection_time = None
        reflection_engine.trades_since_reflection = 2

        assert reflection_engine.should_reflect() is False

        reflection_engine.trades_since_reflection = 5
        assert reflection_engine.should_reflect() is True


class TestFullReflection:
    """Tests for full reflection cycle."""

    def test_full_reflect(self, reflection_engine):
        """Full reflection produces valid result."""
        import asyncio

        async def run_test():
            result = await reflection_engine.reflect()

            assert isinstance(result, ReflectionResult)
            assert result.trades_analyzed == 13
            assert len(result.insights) > 0
            assert result.summary != ""
            assert result.total_time_ms > 0

        asyncio.run(run_test())

    def test_reflect_updates_state(self, reflection_engine):
        """Reflection updates internal state."""
        import asyncio

        async def run_test():
            reflection_engine.trades_since_reflection = 15

            await reflection_engine.reflect()

            assert reflection_engine.trades_since_reflection == 0
            assert reflection_engine.last_reflection_time is not None
            assert reflection_engine.reflections_completed == 1

        asyncio.run(run_test())

    def test_reflect_empty_journal(self, reflection_engine, mock_journal):
        """Handles empty journal gracefully."""
        import asyncio

        async def run_test():
            mock_journal.get_recent.return_value = []

            result = await reflection_engine.reflect()

            assert result.trades_analyzed == 0
            assert len(result.insights) == 0

        asyncio.run(run_test())


class TestDatabaseIntegration:
    """Tests for database logging."""

    def test_reflection_logged_to_db(self, reflection_engine, temp_db):
        """Reflection is saved to database."""
        import asyncio

        async def run_test():
            await reflection_engine.reflect()

            reflections = temp_db.get_recent_reflections(limit=1)

            assert len(reflections) == 1
            assert reflections[0]["trades_analyzed"] == 13

        asyncio.run(run_test())


class TestOnTradeClose:
    """Tests for trade close notification."""

    def test_on_trade_close_increments_counter(self, reflection_engine):
        """on_trade_close increments trade counter."""
        initial = reflection_engine.trades_since_reflection

        reflection_engine.on_trade_close()

        assert reflection_engine.trades_since_reflection == initial + 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
