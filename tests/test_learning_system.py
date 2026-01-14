"""Tests for the learning system module."""

import os
import tempfile
import json
import pytest
from unittest.mock import MagicMock, patch

from src.learning_system import LearningSystem, Learning, get_learnings_as_text
from src.database import Database
from src.llm_interface import LLMInterface


class TestLearningDataclass:
    """Test the Learning dataclass."""

    def test_learning_creation(self):
        """Test creating a Learning object."""
        learning = Learning(
            id=1,
            trade_id=1,
            what_happened="Test trade",
            why_outcome="Test reason",
            pattern="Test pattern",
            lesson="Test lesson",
            confidence=0.8
        )
        assert learning.id == 1
        assert learning.confidence == 0.8

    def test_learning_to_dict(self):
        """Test converting Learning to dictionary."""
        learning = Learning(
            id=1,
            trade_id=1,
            what_happened="Test",
            why_outcome="Test",
            pattern="Test",
            lesson="Test lesson",
            confidence=0.8
        )
        d = learning.to_dict()
        assert d['lesson'] == "Test lesson"
        assert d['confidence'] == 0.8

    def test_learning_to_text(self):
        """Test converting Learning to text."""
        learning = Learning(
            id=1,
            trade_id=1,
            what_happened="Test",
            why_outcome="Test",
            pattern="Test",
            lesson="Always check momentum",
            confidence=0.85
        )
        text = learning.to_text()
        assert "85%" in text
        assert "Always check momentum" in text


class TestLearningSystemInit:
    """Test LearningSystem initialization."""

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

    def test_init_with_db(self):
        """Test initialization with database."""
        ls = LearningSystem(db=self.db)
        assert ls.db is not None

    def test_init_without_llm(self):
        """Test initialization without LLM."""
        ls = LearningSystem(db=self.db, llm=None)
        assert ls.llm is None


class TestGetClosedTrade:
    """Test getting closed trades."""

    def setup_method(self):
        """Create a temporary database with a closed trade."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)
        self.ls = LearningSystem(db=self.db, llm=None)

        # Add a closed trade
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO closed_trades (
                    coin_name, entry_price, exit_price, size_usd,
                    pnl_usd, pnl_pct, entry_reason, exit_reason,
                    opened_at, closed_at, duration_seconds
                ) VALUES (
                    'bitcoin', 95000.0, 95500.0, 20.0,
                    0.11, 0.53, 'test entry', 'take_profit',
                    datetime('now', '-1 hour'), datetime('now'), 3600
                )
            """)
            conn.commit()

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_get_existing_trade(self):
        """Test getting an existing closed trade."""
        trade = self.ls.get_closed_trade(1)
        assert trade is not None
        assert trade['coin_name'] == 'bitcoin'
        assert trade['pnl_usd'] == 0.11

    def test_get_nonexistent_trade(self):
        """Test getting a trade that doesn't exist."""
        trade = self.ls.get_closed_trade(999)
        assert trade is None


class TestBuildAnalysisPrompt:
    """Test prompt building."""

    def setup_method(self):
        """Create a temporary database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)
        self.ls = LearningSystem(db=self.db, llm=None)

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_build_prompt_contains_trade_info(self):
        """Test that prompt contains trade information."""
        trade = {
            'coin_name': 'bitcoin',
            'entry_price': 95000.0,
            'exit_price': 95500.0,
            'size_usd': 20.0,
            'pnl_usd': 0.11,
            'pnl_pct': 0.53,
            'entry_reason': 'test entry',
            'exit_reason': 'take_profit',
            'duration_seconds': 3600
        }
        prompt = self.ls.build_analysis_prompt(trade)

        assert 'BITCOIN' in prompt
        assert '95,000' in prompt
        assert '95,500' in prompt
        assert 'PROFIT' in prompt

    def test_build_prompt_contains_json_format(self):
        """Test that prompt asks for JSON format."""
        trade = {
            'coin_name': 'bitcoin',
            'entry_price': 95000.0,
            'exit_price': 94000.0,
            'size_usd': 20.0,
            'pnl_usd': -0.21,
            'pnl_pct': -1.05,
            'entry_reason': 'test',
            'exit_reason': 'stop_loss',
            'duration_seconds': 600
        }
        prompt = self.ls.build_analysis_prompt(trade)

        assert 'JSON' in prompt
        assert 'what_happened' in prompt
        assert 'lesson' in prompt


class TestAnalyzeTrade:
    """Test trade analysis with mocked LLM."""

    def setup_method(self):
        """Create a temporary database with a closed trade."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)

        # Add market data
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO market_data (coin, price_usd, change_24h, last_updated)
                VALUES ('bitcoin', 95500.0, 2.5, datetime('now'))
            """)

            # Add a closed trade
            cursor.execute("""
                INSERT INTO closed_trades (
                    coin_name, entry_price, exit_price, size_usd,
                    pnl_usd, pnl_pct, entry_reason, exit_reason,
                    opened_at, closed_at, duration_seconds
                ) VALUES (
                    'bitcoin', 95000.0, 95500.0, 20.0,
                    0.11, 0.53, 'test entry', 'take_profit',
                    datetime('now', '-1 hour'), datetime('now'), 3600
                )
            """)
            conn.commit()

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_analyze_without_llm_returns_none(self):
        """Test that analysis without LLM returns None."""
        ls = LearningSystem(db=self.db, llm=None)
        result = ls.analyze_trade(1)
        assert result is None

    def test_analyze_nonexistent_trade_returns_none(self):
        """Test that analyzing non-existent trade returns None."""
        mock_llm = MagicMock()
        ls = LearningSystem(db=self.db, llm=mock_llm)
        result = ls.analyze_trade(999)
        assert result is None

    def test_analyze_with_mocked_llm(self):
        """Test successful analysis with mocked LLM."""
        mock_llm = MagicMock()
        mock_llm.query_json.return_value = {
            'what_happened': 'Price rose 0.53%',
            'why_outcome': 'Market momentum was positive',
            'pattern': 'buying during uptrend',
            'lesson': 'Enter during positive 24h momentum',
            'confidence': 0.75
        }

        ls = LearningSystem(db=self.db, llm=mock_llm)
        result = ls.analyze_trade(1)

        assert result is not None
        assert result.lesson == 'Enter during positive 24h momentum'
        assert result.confidence == 0.75

    def test_analyze_stores_in_database(self):
        """Test that analysis is stored in database."""
        mock_llm = MagicMock()
        mock_llm.query_json.return_value = {
            'what_happened': 'Test',
            'why_outcome': 'Test',
            'pattern': 'test pattern',
            'lesson': 'Test lesson',
            'confidence': 0.8
        }

        ls = LearningSystem(db=self.db, llm=mock_llm)
        ls.analyze_trade(1)

        # Check database
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM learnings")
            count = cursor.fetchone()[0]
            assert count == 1

    def test_analyze_already_analyzed_returns_existing(self):
        """Test that re-analyzing returns existing learning."""
        mock_llm = MagicMock()
        mock_llm.query_json.return_value = {
            'what_happened': 'Test',
            'why_outcome': 'Test',
            'pattern': 'test',
            'lesson': 'First lesson',
            'confidence': 0.8
        }

        ls = LearningSystem(db=self.db, llm=mock_llm)

        # First analysis
        result1 = ls.analyze_trade(1)

        # Change mock return value
        mock_llm.query_json.return_value['lesson'] = 'Second lesson'

        # Second analysis should return existing
        result2 = ls.analyze_trade(1)

        assert result2.lesson == 'First lesson'


class TestGetLearnings:
    """Test learning retrieval methods."""

    def setup_method(self):
        """Create a temporary database with learnings."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)
        self.ls = LearningSystem(db=self.db, llm=None)

        # Add closed trades and learnings
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # Add closed trades
            cursor.execute("""
                INSERT INTO closed_trades (
                    coin_name, entry_price, exit_price, size_usd,
                    pnl_usd, pnl_pct, entry_reason, exit_reason,
                    opened_at, closed_at, duration_seconds
                ) VALUES
                ('bitcoin', 95000, 95500, 20, 0.11, 0.53, 'test', 'tp', datetime('now'), datetime('now'), 100),
                ('ethereum', 3300, 3250, 20, -0.30, -1.52, 'test', 'sl', datetime('now'), datetime('now'), 100)
            """)

            # Add learnings
            learning1 = json.dumps({
                'what_happened': 'BTC rose',
                'why_outcome': 'momentum',
                'pattern': 'uptrend entry',
                'lesson': 'Enter BTC during uptrends',
                'confidence': 0.8
            })
            learning2 = json.dumps({
                'what_happened': 'ETH fell',
                'why_outcome': 'weak market',
                'pattern': 'downtrend entry',
                'lesson': 'Avoid ETH during weak markets',
                'confidence': 0.6
            })

            cursor.execute("""
                INSERT INTO learnings (trade_id, learning_text, pattern_type, confidence_level, created_at)
                VALUES
                (1, ?, 'uptrend entry', 0.8, datetime('now')),
                (2, ?, 'downtrend entry', 0.6, datetime('now'))
            """, (learning1, learning2))
            conn.commit()

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_get_learnings_for_decision(self):
        """Test getting learnings for decision making."""
        learnings = self.ls.get_learnings_for_decision(limit=10)
        assert len(learnings) == 2
        # Should be sorted by confidence (highest first)
        assert learnings[0].confidence >= learnings[1].confidence

    def test_get_learnings_by_coin(self):
        """Test getting learnings for specific coin."""
        btc_learnings = self.ls.get_learnings_by_coin('bitcoin')
        assert len(btc_learnings) == 1
        assert 'BTC' in btc_learnings[0].lesson

    def test_get_all_learnings(self):
        """Test getting all learnings."""
        learnings = self.ls.get_all_learnings()
        assert len(learnings) == 2

    def test_get_learning_for_trade(self):
        """Test getting learning for specific trade."""
        learning = self.ls.get_learning_for_trade(1)
        assert learning is not None
        assert learning.trade_id == 1

    def test_get_unanalyzed_trades(self):
        """Test getting unanalyzed trades."""
        # Add a trade without learning
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO closed_trades (
                    coin_name, entry_price, exit_price, size_usd,
                    pnl_usd, pnl_pct, entry_reason, exit_reason,
                    opened_at, closed_at, duration_seconds
                ) VALUES ('ripple', 2.1, 2.2, 20, 0.95, 4.76, 'test', 'tp', datetime('now'), datetime('now'), 100)
            """)
            conn.commit()

        unanalyzed = self.ls.get_unanalyzed_trades()
        assert 3 in unanalyzed


class TestLearningSummary:
    """Test learning summary statistics."""

    def setup_method(self):
        """Create a temporary database with learnings."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)
        self.ls = LearningSystem(db=self.db, llm=None)

        # Add learnings directly
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO learnings (trade_id, learning_text, pattern_type, confidence_level, created_at)
                VALUES
                (1, '{"lesson": "test1"}', 'pattern1', 0.9, datetime('now')),
                (2, '{"lesson": "test2"}', 'pattern2', 0.7, datetime('now')),
                (3, '{"lesson": "test3"}', 'pattern3', 0.5, datetime('now'))
            """)
            conn.commit()

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_get_learning_summary(self):
        """Test getting learning summary."""
        summary = self.ls.get_learning_summary()
        assert summary['total_learnings'] == 3
        assert summary['high_confidence_count'] == 2  # 0.9 and 0.7 >= 0.7
        assert summary['average_confidence'] == pytest.approx(0.7, rel=0.01)


class TestGetLearningsAsText:
    """Test the convenience function."""

    def setup_method(self):
        """Create a temporary database with learnings."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)

        # Add a learning
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            learning = json.dumps({
                'what_happened': 'test',
                'why_outcome': 'test',
                'pattern': 'test',
                'lesson': 'Important lesson here',
                'confidence': 0.85
            })
            cursor.execute("""
                INSERT INTO learnings (trade_id, learning_text, pattern_type, confidence_level, created_at)
                VALUES (1, ?, 'test', 0.85, datetime('now'))
            """, (learning,))
            conn.commit()

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_get_learnings_as_text(self):
        """Test getting learnings as text strings."""
        texts = get_learnings_as_text(db=self.db, limit=10)
        assert len(texts) == 1
        assert 'Important lesson' in texts[0]
        assert '85%' in texts[0]


def test_learning_system_import():
    """Test that LearningSystem can be imported."""
    from src.learning_system import LearningSystem, Learning, get_learnings_as_text
    assert LearningSystem is not None
    assert Learning is not None
    assert get_learnings_as_text is not None
