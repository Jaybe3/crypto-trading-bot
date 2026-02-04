"""
Tests for MarketFeed WebSocket component.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import asdict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.market_feed import MarketFeed, PriceTick, TradeEvent, CoinConfig, FeedStatus


class TestDataClasses:
    """Test data class structures."""

    def test_price_tick_creation(self):
        tick = PriceTick(
            coin="BTC",
            price=42000.50,
            timestamp=1672515782136,
            volume_24h=1000000.0,
            change_24h=2.5
        )
        assert tick.coin == "BTC"
        assert tick.price == 42000.50
        assert tick.timestamp == 1672515782136
        assert tick.volume_24h == 1000000.0
        assert tick.change_24h == 2.5

    def test_trade_event_creation(self):
        trade = TradeEvent(
            coin="ETH",
            price=2500.00,
            quantity=1.5,
            is_buyer_maker=True,
            timestamp=1672515782136
        )
        assert trade.coin == "ETH"
        assert trade.price == 2500.00
        assert trade.quantity == 1.5
        assert trade.is_buyer_maker == True  # Sell
        assert trade.timestamp == 1672515782136

    def test_coin_config_creation(self):
        config = CoinConfig(
            symbol="SOL",
            binance="SOLUSDT",
            tier=1,
            name="Solana"
        )
        assert config.symbol == "SOL"
        assert config.binance == "SOLUSDT"
        assert config.tier == 1


class TestMarketFeedInitialization:
    """Test MarketFeed initialization."""

    def test_init_with_coins_list(self):
        feed = MarketFeed(['BTC', 'ETH'])
        assert len(feed.coin_configs) >= 2
        symbols = [c.symbol for c in feed.coin_configs]
        assert 'BTC' in symbols
        assert 'ETH' in symbols

    def test_init_with_lowercase_coins(self):
        feed = MarketFeed(['btc', 'eth'])
        symbols = [c.symbol for c in feed.coin_configs]
        assert 'BTC' in symbols
        assert 'ETH' in symbols

    def test_init_unknown_coin_gets_default(self):
        feed = MarketFeed(['BTC', 'UNKNOWN123'])
        symbols = [c.symbol for c in feed.coin_configs]
        assert 'UNKNOWN123' in symbols
        # Unknown coin should get default tier 3
        unknown_config = next(c for c in feed.coin_configs if c.symbol == 'UNKNOWN123')
        assert unknown_config.tier == 3
        assert unknown_config.binance == 'UNKNOWN123USDT'

    def test_symbol_mapping(self):
        feed = MarketFeed(['BTC', 'ETH'])
        assert 'BTCUSDT' in feed._symbol_to_coin
        assert feed._symbol_to_coin['BTCUSDT'] == 'BTC'

    def test_initial_status(self):
        feed = MarketFeed(['BTC'])
        assert feed.status.connected == False
        assert feed.status.messages_received == 0
        assert feed.status.reconnect_count == 0


class TestStreamUrlBuilding:
    """Test WebSocket URL construction."""

    def test_get_ws_url_bybit(self):
        feed = MarketFeed(['BTC', 'ETH'], exchange='bybit')
        url = feed._get_ws_url()
        assert 'wss://stream.bybit.com' in url

    def test_get_ws_url_binance(self):
        feed = MarketFeed(['BTC', 'ETH'], exchange='binance')
        url = feed._get_ws_url()
        assert 'wss://stream.binance.com' in url

    def test_exchange_config(self):
        # Test that multiple exchanges are available
        assert 'bybit' in MarketFeed.EXCHANGES
        assert 'binance' in MarketFeed.EXCHANGES
        assert 'binance_us' in MarketFeed.EXCHANGES


class TestMessageHandling:
    """Test WebSocket message parsing."""

    def test_handle_binance_trade(self):
        async def run_test():
            feed = MarketFeed(['BTC'], exchange='binance')
            received_trades = []
            received_prices = []

            feed.subscribe_trades(lambda t: received_trades.append(t))
            feed.subscribe_price(lambda p: received_prices.append(p))

            # Simulate Binance trade data
            trade_data = {
                's': 'BTCUSDT',
                'p': '42000.50',
                'q': '0.001',
                'T': 1672515782136,
                'm': True
            }

            await feed._handle_binance_trade(trade_data)

            # Should have received trade event
            assert len(received_trades) == 1
            assert received_trades[0].coin == 'BTC'
            assert received_trades[0].price == 42000.50
            assert received_trades[0].is_buyer_maker == True

            # Should have received price update
            assert len(received_prices) == 1
            assert received_prices[0].coin == 'BTC'
            assert received_prices[0].price == 42000.50

        asyncio.run(run_test())

    def test_handle_bybit_trade(self):
        async def run_test():
            feed = MarketFeed(['BTC'], exchange='bybit')
            received_trades = []
            received_prices = []

            feed.subscribe_trades(lambda t: received_trades.append(t))
            feed.subscribe_price(lambda p: received_prices.append(p))

            # Simulate Bybit trade data
            trade_data = {
                's': 'BTCUSDT',
                'p': '42000.50',
                'v': '0.001',
                'T': 1672515782136,
                'S': 'Sell'
            }

            await feed._handle_bybit_trade(trade_data)

            # Should have received trade event
            assert len(received_trades) == 1
            assert received_trades[0].coin == 'BTC'
            assert received_trades[0].price == 42000.50

            # Should have received price update
            assert len(received_prices) == 1
            assert received_prices[0].coin == 'BTC'
            assert received_prices[0].price == 42000.50

        asyncio.run(run_test())

    def test_ignore_unknown_symbol(self):
        async def run_test():
            feed = MarketFeed(['BTC'], exchange='binance')  # Only BTC
            received = []
            feed.subscribe_price(lambda p: received.append(p))

            # Send ETH trade (not subscribed)
            trade_data = {
                's': 'ETHUSDT',
                'p': '2500.00',
                'q': '1.0',
                'T': 1672515782136,
                'm': False
            }

            await feed._handle_binance_trade(trade_data)

            # Should not trigger callback
            assert len(received) == 0

        asyncio.run(run_test())


class TestCallbacks:
    """Test callback registration and invocation."""

    def test_subscribe_price(self):
        feed = MarketFeed(['BTC'])
        callback = MagicMock()

        feed.subscribe_price(callback)

        assert len(feed._price_callbacks) == 1
        assert callback in feed._price_callbacks

    def test_subscribe_trades(self):
        feed = MarketFeed(['BTC'])
        callback = MagicMock()

        feed.subscribe_trades(callback)

        assert len(feed._trade_callbacks) == 1

    def test_subscribe_status(self):
        feed = MarketFeed(['BTC'])
        callback = MagicMock()

        feed.subscribe_status(callback)

        assert len(feed._status_callbacks) == 1

    def test_multiple_callbacks(self):
        feed = MarketFeed(['BTC'])

        feed.subscribe_price(lambda x: None)
        feed.subscribe_price(lambda x: None)
        feed.subscribe_price(lambda x: None)

        assert len(feed._price_callbacks) == 3

    def test_callback_error_doesnt_break_feed(self):
        async def run_test():
            feed = MarketFeed(['BTC'], exchange='binance')
            good_received = []

            def bad_callback(tick):
                raise Exception("Callback error!")

            def good_callback(tick):
                good_received.append(tick)

            feed.subscribe_price(bad_callback)
            feed.subscribe_price(good_callback)

            # Simulate trade (using Binance handler)
            await feed._handle_binance_trade({
                's': 'BTCUSDT',
                'p': '42000.00',
                'q': '0.001',
                'T': 1672515782136,
                'm': False
            })

            # Good callback should still be called despite bad callback error
            assert len(good_received) == 1

        asyncio.run(run_test())


class TestPriceCache:
    """Test price caching functionality."""

    def test_get_price(self):
        async def run_test():
            feed = MarketFeed(['BTC', 'ETH'], exchange='binance')

            # Simulate price update
            await feed._handle_binance_trade({
                's': 'BTCUSDT',
                'p': '42000.00',
                'q': '0.001',
                'T': 1672515782136,
                'm': False
            })

            price = feed.get_price('BTC')
            assert price is not None
            assert price.price == 42000.00
            assert price.coin == 'BTC'

        asyncio.run(run_test())

    def test_get_price_not_found(self):
        feed = MarketFeed(['BTC'])
        price = feed.get_price('XYZ')
        assert price is None

    def test_get_price_case_insensitive(self):
        feed = MarketFeed(['BTC'])
        feed.current_prices['BTC'] = PriceTick(
            coin='BTC', price=42000, timestamp=0, volume_24h=0, change_24h=0
        )

        assert feed.get_price('btc') is not None
        assert feed.get_price('BTC') is not None

    def test_get_all_prices(self):
        async def run_test():
            feed = MarketFeed(['BTC', 'ETH'], exchange='binance')

            await feed._handle_binance_trade({'s': 'BTCUSDT', 'p': '42000', 'q': '0.001', 'T': 0, 'm': False})
            await feed._handle_binance_trade({'s': 'ETHUSDT', 'p': '2500', 'q': '0.1', 'T': 0, 'm': False})

            prices = feed.get_all_prices()
            assert 'BTC' in prices
            assert 'ETH' in prices
            assert prices['BTC'].price == 42000

        asyncio.run(run_test())


class TestStatus:
    """Test status reporting."""

    def test_get_status(self):
        feed = MarketFeed(['BTC', 'ETH', 'SOL'])
        status = feed.get_status()

        assert 'connected' in status
        assert 'coins' in status
        assert status['coins'] == 3
        assert status['connected'] == False
        assert status['messages_received'] == 0

    def test_status_emit(self):
        feed = MarketFeed(['BTC'])
        events = []

        feed.subscribe_status(lambda e, d: events.append((e, d)))
        feed._emit_status('test_event', {'key': 'value'})

        assert len(events) == 1
        assert events[0][0] == 'test_event'
        assert events[0][1]['key'] == 'value'


# Integration test (requires network - skip in CI)
@pytest.mark.skipif(True, reason="Integration test - requires network")
class TestIntegration:
    """Integration tests with real Binance WebSocket."""

    @pytest.mark.asyncio
    async def test_real_connection(self):
        """Test actual connection to Binance (manual run only)."""
        feed = MarketFeed(['BTC'])
        prices_received = []

        feed.subscribe_price(lambda p: prices_received.append(p))

        # Connect and wait briefly
        connect_task = asyncio.create_task(feed.connect())

        await asyncio.sleep(5)  # Wait for some prices
        await feed.disconnect()

        assert len(prices_received) > 0
        assert prices_received[0].coin == 'BTC'
        assert prices_received[0].price > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
