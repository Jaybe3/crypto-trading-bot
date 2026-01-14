"""Tests for the LLM interface module."""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from src.llm_interface import LLMInterface, DEFAULT_MODEL, DEFAULT_API_URL
from src.database import Database


class TestLLMInterface:
    """Test cases for the LLMInterface class."""

    def setup_method(self):
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)
        self.llm = LLMInterface(db=self.db)

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_default_configuration(self):
        """Test default model and API URL."""
        assert self.llm.model == DEFAULT_MODEL
        assert self.llm.api_url == DEFAULT_API_URL

    def test_custom_configuration(self):
        """Test custom model and API URL."""
        llm = LLMInterface(
            model="custom-model",
            api_url="http://custom:8080/api",
            db=self.db
        )
        assert llm.model == "custom-model"
        assert llm.api_url == "http://custom:8080/api"

    def test_get_model_info(self):
        """Test get_model_info returns correct data."""
        info = self.llm.get_model_info()
        assert info['model'] == DEFAULT_MODEL
        assert info['api_url'] == DEFAULT_API_URL
        assert 'timeout' in info

    @patch('src.llm_interface.requests.post')
    def test_query_mocked(self, mock_post):
        """Test query with mocked API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "Four."}
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.llm.query("What is 2+2?")

        assert result == "Four."
        mock_post.assert_called_once()

    @patch('src.llm_interface.requests.post')
    def test_query_json_mocked(self, mock_post):
        """Test query_json parses JSON response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": '{"action": "HOLD", "confidence": 0.5}'}
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.llm.query_json("Get trading decision")

        assert result['action'] == "HOLD"
        assert result['confidence'] == 0.5

    @patch('src.llm_interface.requests.post')
    def test_query_json_with_markdown(self, mock_post):
        """Test query_json handles markdown-wrapped JSON."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": '```json\n{"action": "BUY"}\n```'}
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.llm.query_json("Get decision")

        assert result['action'] == "BUY"

    @patch('src.llm_interface.requests.post')
    def test_get_trading_decision_mocked(self, mock_post):
        """Test get_trading_decision returns valid structure."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": '{"action": "BUY", "coin": "bitcoin", "size_usd": 20, "reason": "test", "confidence": 0.8}'}
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.llm.get_trading_decision(
            market_data={"bitcoin": {"usd": 95000}},
            account_state={"balance": 1000}
        )

        assert result['action'] == "BUY"
        assert result['coin'] == "bitcoin"
        assert result['confidence'] == 0.8

    @patch('src.llm_interface.requests.post')
    def test_get_trading_decision_fallback(self, mock_post):
        """Test get_trading_decision returns HOLD on error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "invalid json"}
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.llm.get_trading_decision(
            market_data={},
            account_state={}
        )

        assert result['action'] == "HOLD"
        assert result['confidence'] == 0.0

    @patch('src.llm_interface.requests.post')
    def test_analyze_trade_mocked(self, mock_post):
        """Test analyze_trade returns learning structure."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": '{"what_happened": "test", "why_outcome": "test", "pattern": "test", "lesson": "test lesson", "confidence": 0.9}'}
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.llm.analyze_trade({
            "coin_name": "bitcoin",
            "entry_price": 95000,
            "exit_price": 95100,
            "size_usd": 20,
            "pnl_usd": 2.0,
            "pnl_pct": 0.1
        })

        assert result['lesson'] == "test lesson"
        assert result['confidence'] == 0.9

    @patch('src.llm_interface.requests.post')
    def test_connection_error_handling(self, mock_post):
        """Test handling of connection errors."""
        from requests.exceptions import ConnectionError
        mock_post.side_effect = ConnectionError("Connection refused")

        result = self.llm.query("Test")

        assert result is None

    @patch('src.llm_interface.requests.post')
    def test_activity_logging(self, mock_post):
        """Test that LLM queries are logged to activity_log."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "Test response"}
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        self.llm.query("Test prompt")

        # Check activity log
        activities = self.db.get_recent_activity(5)
        llm_activities = [a for a in activities if a['activity_type'] == 'llm_query']
        assert len(llm_activities) > 0


class TestRealLLMIntegration:
    """Integration tests that call the real LLM.

    These tests verify that we can actually communicate with the LLM.
    They require OpenWebUI to be running at localhost:3000.
    """

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

    @pytest.mark.integration
    def test_real_llm_query(self):
        """Test sending a real query to the LLM.

        This test calls the actual LLM to verify integration works.
        Requires OpenWebUI running at localhost:3000.
        """
        llm = LLMInterface(db=self.db)
        response = llm.query("What is 2+2? Answer with just the number.")

        # Should get some response
        assert response is not None
        # Response should contain "4" somewhere
        assert "4" in response or "four" in response.lower()

    @pytest.mark.integration
    def test_real_llm_connection_test(self):
        """Test the connection test method."""
        llm = LLMInterface(db=self.db)
        result = llm.test_connection()

        assert result is True


def test_llm_interface_import():
    """Test that LLMInterface can be imported."""
    from src.llm_interface import LLMInterface
    assert LLMInterface is not None
