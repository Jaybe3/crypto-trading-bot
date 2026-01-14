"""Tests for the market data module."""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from src.market_data import MarketDataFetcher, get_verification_url, DEFAULT_COINS
from src.database import Database


class TestMarketDataFetcher:
    """Test cases for the MarketDataFetcher class."""

    def setup_method(self):
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading_bot.db")
        self.db = Database(db_path=self.db_path)
        self.fetcher = MarketDataFetcher(db=self.db)

    def teardown_method(self):
        """Clean up temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_default_coins(self):
        """Test that default coins are bitcoin, ethereum, ripple."""
        assert self.fetcher.coins == ['bitcoin', 'ethereum', 'ripple']

    def test_custom_coins(self):
        """Test that custom coins can be specified."""
        fetcher = MarketDataFetcher(coins=['solana', 'cardano'], db=self.db)
        assert fetcher.coins == ['solana', 'cardano']

    def test_add_coin(self):
        """Test adding a coin to the fetch list."""
        self.fetcher.add_coin('solana')
        assert 'solana' in self.fetcher.coins

    def test_add_coin_duplicate(self):
        """Test that duplicate coins are not added."""
        self.fetcher.add_coin('bitcoin')
        assert self.fetcher.coins.count('bitcoin') == 1

    def test_remove_coin(self):
        """Test removing a coin from the fetch list."""
        self.fetcher.remove_coin('ripple')
        assert 'ripple' not in self.fetcher.coins

    def test_update_interval_default(self):
        """Test default update interval is 30 seconds."""
        assert self.fetcher.update_interval == 30

    def test_update_interval_custom(self):
        """Test custom update interval."""
        fetcher = MarketDataFetcher(update_interval=60, db=self.db)
        assert fetcher.update_interval == 60

    def test_get_current_prices_empty(self):
        """Test getting prices when database is empty."""
        prices = self.fetcher.get_current_prices()
        assert prices == {}

    def test_get_price_not_found(self):
        """Test getting price for non-existent coin."""
        price = self.fetcher.get_price('nonexistent')
        assert price is None

    @patch('src.market_data.requests.get')
    def test_fetch_prices_mocked(self, mock_get):
        """Test fetch_prices with mocked API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'bitcoin': {'usd': 94000.0, 'usd_24h_change': 2.5}
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        prices = self.fetcher.fetch_prices(['bitcoin'])

        assert 'bitcoin' in prices
        assert prices['bitcoin']['usd'] == 94000.0
        assert prices['bitcoin']['usd_24h_change'] == 2.5

    @patch('src.market_data.requests.get')
    def test_update_database_mocked(self, mock_get):
        """Test that prices are stored in database."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'bitcoin': {'usd': 94000.0, 'usd_24h_change': 2.5},
            'ethereum': {'usd': 3200.0, 'usd_24h_change': 1.2}
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Fetch and store
        self.fetcher.fetch_and_store()

        # Check database
        btc_price = self.fetcher.get_price('bitcoin')
        eth_price = self.fetcher.get_price('ethereum')

        assert btc_price == 94000.0
        assert eth_price == 3200.0


class TestGetVerificationUrl:
    """Test cases for the get_verification_url function."""

    def test_single_coin(self):
        """Test URL generation for single coin."""
        url = get_verification_url(['bitcoin'])
        assert 'ids=bitcoin' in url
        assert 'vs_currencies=usd' in url

    def test_multiple_coins(self):
        """Test URL generation for multiple coins."""
        url = get_verification_url(['bitcoin', 'ethereum'])
        assert 'ids=bitcoin,ethereum' in url

    def test_default_coin(self):
        """Test URL generation with default (bitcoin)."""
        url = get_verification_url()
        assert 'ids=bitcoin' in url


class TestRealAPIIntegration:
    """Integration tests that call the real CoinGecko API.

    These tests verify that we can actually fetch REAL data.
    They may fail if there are network issues or API rate limits.
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
    def test_fetch_real_bitcoin_price(self):
        """Test fetching REAL bitcoin price from CoinGecko.

        This test calls the actual API to verify integration works.
        """
        fetcher = MarketDataFetcher(coins=['bitcoin'], db=self.db)
        prices = fetcher.fetch_prices()

        # Bitcoin should be in response
        assert 'bitcoin' in prices

        # Price should be a positive number
        btc_price = prices['bitcoin']['usd']
        assert isinstance(btc_price, (int, float))
        assert btc_price > 0

        # Price should be reasonable (between $1,000 and $1,000,000)
        assert 1000 < btc_price < 1000000

    @pytest.mark.integration
    def test_fetch_and_store_real_data(self):
        """Test fetching and storing REAL data."""
        fetcher = MarketDataFetcher(coins=['bitcoin'], db=self.db)
        fetcher.fetch_and_store()

        # Check database has the price
        db_price = fetcher.get_price('bitcoin')
        assert db_price is not None
        assert db_price > 0


def test_market_data_import():
    """Test that MarketDataFetcher can be imported."""
    from src.market_data import MarketDataFetcher
    assert MarketDataFetcher is not None
