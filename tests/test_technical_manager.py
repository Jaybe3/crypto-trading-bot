"""Tests for Technical Manager."""
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from src.technical.manager import TechnicalManager, TechnicalSnapshot
from src.technical.candle_fetcher import CandleFetcher, Candle, CandleData
from src.technical.rsi import RSIData
from src.technical.vwap import VWAPData
from src.technical.atr import ATRData
from src.technical.funding import FundingData
from src.technical.support_resistance import SRLevels, PriceLevel
from src.technical.volume_profile import VolumeProfile
from src.technical.orderbook import OrderBookDepth


class TestTechnicalSnapshot:
    """Tests for TechnicalSnapshot dataclass."""

    def test_current_price_from_vwap(self):
        vwap = VWAPData(coin="SOL", vwap=100.0, current_price=102.0, deviation_pct=2.0, timestamp=datetime.now())
        snapshot = TechnicalSnapshot(coin="SOL", vwap=vwap)
        assert snapshot.current_price == 102.0

    def test_current_price_from_sr_levels(self):
        sr = SRLevels(coin="SOL", current_price=103.0)
        snapshot = TechnicalSnapshot(coin="SOL", sr_levels=sr)
        assert snapshot.current_price == 103.0

    def test_current_price_default(self):
        snapshot = TechnicalSnapshot(coin="SOL")
        assert snapshot.current_price == 0.0

    def test_is_oversold(self):
        rsi = RSIData(coin="SOL", value=25.0, period=14, timeframe="1h", timestamp=datetime.now())
        snapshot = TechnicalSnapshot(coin="SOL", rsi=rsi)
        assert snapshot.is_oversold is True
        assert snapshot.is_overbought is False

    def test_is_overbought(self):
        rsi = RSIData(coin="SOL", value=75.0, period=14, timeframe="1h", timestamp=datetime.now())
        snapshot = TechnicalSnapshot(coin="SOL", rsi=rsi)
        assert snapshot.is_oversold is False
        assert snapshot.is_overbought is True

    def test_at_support(self):
        support = PriceLevel(price=100.0, level_type="support", strength=3, last_touch=datetime.now(), zone_low=99.0, zone_high=101.0)
        sr = SRLevels(coin="SOL", current_price=100.5, nearest_support=support)
        snapshot = TechnicalSnapshot(coin="SOL", sr_levels=sr)
        assert snapshot.at_support is True

    def test_at_resistance(self):
        resistance = PriceLevel(price=100.0, level_type="resistance", strength=3, last_touch=datetime.now(), zone_low=99.0, zone_high=101.0)
        sr = SRLevels(coin="SOL", current_price=100.5, nearest_resistance=resistance)
        snapshot = TechnicalSnapshot(coin="SOL", sr_levels=sr)
        assert snapshot.at_resistance is True

    def test_funding_bias_extreme_long(self):
        funding = FundingData(coin="SOL", current_rate=0.001, predicted_rate=0.001, annualized=10.0, timestamp=datetime.now())
        snapshot = TechnicalSnapshot(coin="SOL", funding=funding)
        assert snapshot.funding_bias == "extreme_long"

    def test_funding_bias_extreme_short(self):
        funding = FundingData(coin="SOL", current_rate=-0.001, predicted_rate=-0.001, annualized=-10.0, timestamp=datetime.now())
        snapshot = TechnicalSnapshot(coin="SOL", funding=funding)
        assert snapshot.funding_bias == "extreme_short"

    def test_funding_bias_neutral(self):
        funding = FundingData(coin="SOL", current_rate=0.0001, predicted_rate=0.0001, annualized=1.0, timestamp=datetime.now())
        snapshot = TechnicalSnapshot(coin="SOL", funding=funding)
        assert snapshot.funding_bias == "neutral"

    def test_get_confluence_signals_long(self):
        rsi = RSIData(coin="SOL", value=25.0, period=14, timeframe="1h", timestamp=datetime.now())
        support = PriceLevel(price=100.0, level_type="support", strength=3, last_touch=datetime.now(), zone_low=99.0, zone_high=101.0)
        sr = SRLevels(coin="SOL", current_price=100.5, nearest_support=support)
        funding = FundingData(coin="SOL", current_rate=-0.001, predicted_rate=-0.001, annualized=-10.0, timestamp=datetime.now())

        snapshot = TechnicalSnapshot(coin="SOL", rsi=rsi, sr_levels=sr, funding=funding)
        signals = snapshot.get_confluence_signals("LONG")

        assert "RSI oversold" in signals
        assert "At support level" in signals
        assert any("Extreme shorts" in s for s in signals)

    def test_get_confluence_signals_short(self):
        rsi = RSIData(coin="SOL", value=75.0, period=14, timeframe="1h", timestamp=datetime.now())
        resistance = PriceLevel(price=100.0, level_type="resistance", strength=3, last_touch=datetime.now(), zone_low=99.0, zone_high=101.0)
        sr = SRLevels(coin="SOL", current_price=100.5, nearest_resistance=resistance)
        funding = FundingData(coin="SOL", current_rate=0.001, predicted_rate=0.001, annualized=10.0, timestamp=datetime.now())

        snapshot = TechnicalSnapshot(coin="SOL", rsi=rsi, sr_levels=sr, funding=funding)
        signals = snapshot.get_confluence_signals("SHORT")

        assert "RSI overbought" in signals
        assert "At resistance level" in signals
        assert any("Extreme longs" in s for s in signals)

    def test_to_prompt(self):
        rsi = RSIData(coin="SOL", value=50.0, period=14, timeframe="1h", timestamp=datetime.now())
        vwap = VWAPData(coin="SOL", vwap=100.0, current_price=102.0, deviation_pct=2.0, timestamp=datetime.now())

        snapshot = TechnicalSnapshot(coin="SOL", rsi=rsi, vwap=vwap)
        prompt = snapshot.to_prompt()

        assert "SOL TECHNICAL" in prompt
        assert "RSI:" in prompt
        assert "VWAP:" in prompt


class TestTechnicalManager:
    """Tests for TechnicalManager."""

    @pytest.fixture
    def mock_candle_fetcher(self):
        mock = Mock(spec=CandleFetcher)
        candles = [Candle(i * 1000, 100, 105, 95, 100, 1000) for i in range(50)]
        mock.get_candles.return_value = CandleData(coin="SOL", interval="1h", candles=candles)
        return mock

    @pytest.fixture
    def mock_rsi(self):
        mock = Mock()
        mock.calculate.return_value = RSIData(coin="SOL", value=50.0, period=14, timeframe="1h", timestamp=datetime.now())
        return mock

    @pytest.fixture
    def mock_vwap(self):
        mock = Mock()
        mock.calculate.return_value = VWAPData(coin="SOL", vwap=100.0, current_price=102.0, deviation_pct=2.0, timestamp=datetime.now())
        return mock

    @pytest.fixture
    def mock_atr(self):
        mock = Mock()
        mock.calculate.return_value = ATRData(coin="SOL", atr=2.5, atr_pct=2.5, period=14, current_price=100.0, timeframe="1h", timestamp=datetime.now())
        return mock

    @pytest.fixture
    def mock_funding(self):
        mock = Mock()
        mock.get_funding_rate.return_value = FundingData(coin="SOL", current_rate=0.0001, predicted_rate=0.0001, annualized=1.0, timestamp=datetime.now())
        return mock

    def test_init_creates_defaults(self, mock_candle_fetcher):
        mgr = TechnicalManager(mock_candle_fetcher)
        assert mgr.rsi is not None
        assert mgr.vwap is not None
        assert mgr.atr is not None
        assert mgr.funding is not None
        assert mgr.sr_detector is not None
        assert mgr.volume_profile is not None
        assert mgr.orderbook is not None

    def test_get_technical_snapshot(self, mock_candle_fetcher, mock_rsi, mock_vwap):
        mgr = TechnicalManager(
            mock_candle_fetcher,
            rsi_calculator=mock_rsi,
            vwap_calculator=mock_vwap
        )
        snapshot = mgr.get_technical_snapshot("SOL")

        assert isinstance(snapshot, TechnicalSnapshot)
        assert snapshot.coin == "SOL"
        assert snapshot.rsi is not None
        assert snapshot.vwap is not None

    def test_get_trade_setup_quality_long_oversold(self, mock_candle_fetcher):
        mock_rsi = Mock()
        mock_rsi.calculate.return_value = RSIData(coin="SOL", value=25.0, period=14, timeframe="1h", timestamp=datetime.now())

        mgr = TechnicalManager(mock_candle_fetcher, rsi_calculator=mock_rsi)
        quality, reasons = mgr.get_trade_setup_quality("SOL", "LONG")

        # Should be above 50 due to oversold
        assert quality > 50
        assert "RSI oversold" in reasons

    def test_get_trade_setup_quality_long_overbought(self, mock_candle_fetcher):
        mock_rsi = Mock()
        mock_rsi.calculate.return_value = RSIData(coin="SOL", value=75.0, period=14, timeframe="1h", timestamp=datetime.now())

        mgr = TechnicalManager(mock_candle_fetcher, rsi_calculator=mock_rsi)
        quality, reasons = mgr.get_trade_setup_quality("SOL", "LONG")

        # Should be below 50 due to overbought penalty
        assert quality < 50
        assert "RSI overbought" in reasons

    def test_get_trade_setup_quality_short_overbought(self, mock_candle_fetcher):
        mock_rsi = Mock()
        mock_rsi.calculate.return_value = RSIData(coin="SOL", value=75.0, period=14, timeframe="1h", timestamp=datetime.now())

        mgr = TechnicalManager(mock_candle_fetcher, rsi_calculator=mock_rsi)
        quality, reasons = mgr.get_trade_setup_quality("SOL", "SHORT")

        # Should be above 50 due to overbought (good for short)
        assert quality > 50
        assert "RSI overbought" in reasons

    def test_get_trade_setup_quality_neutral(self, mock_candle_fetcher, mock_rsi):
        mgr = TechnicalManager(mock_candle_fetcher, rsi_calculator=mock_rsi)
        quality, reasons = mgr.get_trade_setup_quality("SOL", "LONG")

        # Neutral RSI should give ~50
        assert 40 <= quality <= 60

    def test_get_trade_setup_quality_clamped(self, mock_candle_fetcher):
        # Create extreme scenario
        mock_rsi = Mock()
        mock_rsi.calculate.return_value = RSIData(coin="SOL", value=15.0, period=14, timeframe="1h", timestamp=datetime.now())

        support = PriceLevel(price=100.0, level_type="support", strength=3, last_touch=datetime.now(), zone_low=99.0, zone_high=101.0)
        mock_sr = Mock()
        mock_sr.detect.return_value = SRLevels(coin="SOL", current_price=100.5, nearest_support=support)

        mock_funding = Mock()
        mock_funding.get_funding_rate.return_value = FundingData(coin="SOL", current_rate=-0.001, predicted_rate=-0.001, annualized=-10.0, timestamp=datetime.now())

        mgr = TechnicalManager(
            mock_candle_fetcher,
            rsi_calculator=mock_rsi,
            sr_detector=mock_sr,
            funding_fetcher=mock_funding
        )
        quality, _ = mgr.get_trade_setup_quality("SOL", "LONG")

        # Should be clamped to 100 max
        assert quality <= 100

    def test_get_dynamic_stops_long(self, mock_candle_fetcher, mock_atr):
        mgr = TechnicalManager(mock_candle_fetcher, atr_calculator=mock_atr)
        stop, tp = mgr.get_dynamic_stops("SOL", "LONG", 100.0)

        # Stop should be below entry
        assert stop < 100.0
        # Take profit should be above entry
        assert tp > 100.0

    def test_get_dynamic_stops_short(self, mock_candle_fetcher, mock_atr):
        mgr = TechnicalManager(mock_candle_fetcher, atr_calculator=mock_atr)
        stop, tp = mgr.get_dynamic_stops("SOL", "SHORT", 100.0)

        # Stop should be above entry
        assert stop > 100.0
        # Take profit should be below entry
        assert tp < 100.0

    def test_get_dynamic_stops_uses_sr_levels(self, mock_candle_fetcher, mock_atr):
        support = PriceLevel(price=97.0, level_type="support", strength=3, last_touch=datetime.now(), zone_low=96.5, zone_high=97.5)
        mock_sr = Mock()
        mock_sr.detect.return_value = SRLevels(coin="SOL", current_price=100.0, nearest_support=support)

        mgr = TechnicalManager(
            mock_candle_fetcher,
            atr_calculator=mock_atr,
            sr_detector=mock_sr
        )
        stop, tp = mgr.get_dynamic_stops("SOL", "LONG", 100.0)

        # Stop should consider support level
        assert stop < 100.0

    def test_get_position_size_high_quality(self, mock_candle_fetcher, mock_atr):
        # High quality setup
        mock_rsi = Mock()
        mock_rsi.calculate.return_value = RSIData(coin="SOL", value=25.0, period=14, timeframe="1h", timestamp=datetime.now())

        mgr = TechnicalManager(
            mock_candle_fetcher,
            rsi_calculator=mock_rsi,
            atr_calculator=mock_atr
        )
        size = mgr.get_position_size("SOL", 100.0, "LONG")

        # High quality should increase size
        assert size > 100.0

    def test_get_position_size_low_quality(self, mock_candle_fetcher, mock_atr):
        # Low quality setup
        mock_rsi = Mock()
        mock_rsi.calculate.return_value = RSIData(coin="SOL", value=75.0, period=14, timeframe="1h", timestamp=datetime.now())

        mgr = TechnicalManager(
            mock_candle_fetcher,
            rsi_calculator=mock_rsi,
            atr_calculator=mock_atr
        )
        size = mgr.get_position_size("SOL", 100.0, "LONG")

        # Low quality should decrease size
        assert size < 100.0

    def test_get_position_size_high_volatility(self, mock_candle_fetcher, mock_rsi):
        mock_atr = Mock()
        mock_atr.calculate.return_value = ATRData(coin="SOL", atr=6.0, atr_pct=6.0, period=14, current_price=100.0, timeframe="1h", timestamp=datetime.now())

        mgr = TechnicalManager(
            mock_candle_fetcher,
            rsi_calculator=mock_rsi,
            atr_calculator=mock_atr
        )
        size = mgr.get_position_size("SOL", 100.0, "LONG")

        # High volatility should reduce size
        assert size < 100.0

    def test_graceful_degradation_rsi_fails(self, mock_candle_fetcher):
        mock_rsi = Mock()
        mock_rsi.calculate.side_effect = Exception("API Error")

        mgr = TechnicalManager(mock_candle_fetcher, rsi_calculator=mock_rsi)
        snapshot = mgr.get_technical_snapshot("SOL")

        # Should still return snapshot with None for RSI
        assert snapshot.rsi is None

    def test_graceful_degradation_vwap_fails(self, mock_candle_fetcher):
        mock_vwap = Mock()
        mock_vwap.calculate.side_effect = Exception("API Error")

        mgr = TechnicalManager(mock_candle_fetcher, vwap_calculator=mock_vwap)
        snapshot = mgr.get_technical_snapshot("SOL")

        # Should still return snapshot with None for VWAP
        assert snapshot.vwap is None

    def test_graceful_degradation_all_fail(self, mock_candle_fetcher):
        mock_rsi = Mock()
        mock_rsi.calculate.side_effect = Exception("API Error")
        mock_vwap = Mock()
        mock_vwap.calculate.side_effect = Exception("API Error")
        mock_atr = Mock()
        mock_atr.calculate.side_effect = Exception("API Error")

        mgr = TechnicalManager(
            mock_candle_fetcher,
            rsi_calculator=mock_rsi,
            vwap_calculator=mock_vwap,
            atr_calculator=mock_atr
        )
        snapshot = mgr.get_technical_snapshot("SOL")

        # Should still return snapshot
        assert snapshot.coin == "SOL"
        assert snapshot.rsi is None
        assert snapshot.vwap is None
        assert snapshot.atr is None
