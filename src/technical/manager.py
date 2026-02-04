"""Technical Manager - Aggregates all technical indicators for Strategist."""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Tuple

from .candle_fetcher import CandleFetcher
from .rsi import RSICalculator, RSIData
from .vwap import VWAPCalculator, VWAPData
from .atr import ATRCalculator, ATRData
from .funding import FundingRateFetcher, FundingData
from .support_resistance import SRLevelDetector, SRLevels
from .volume_profile import VolumeProfileCalculator, VolumeProfile
from .orderbook import OrderBookAnalyzer, OrderBookDepth

logger = logging.getLogger(__name__)


@dataclass
class TechnicalSnapshot:
    """Complete technical analysis snapshot for a coin."""
    coin: str
    rsi: Optional[RSIData] = None
    vwap: Optional[VWAPData] = None
    atr: Optional[ATRData] = None
    funding: Optional[FundingData] = None
    sr_levels: Optional[SRLevels] = None
    volume_profile: Optional[VolumeProfile] = None
    orderbook: Optional[OrderBookDepth] = None
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def current_price(self) -> float:
        """Current price from available sources."""
        if self.vwap and self.vwap.current_price:
            return self.vwap.current_price
        if self.sr_levels and self.sr_levels.current_price:
            return self.sr_levels.current_price
        if self.orderbook and self.orderbook.mid_price:
            return self.orderbook.mid_price
        return 0.0

    @property
    def is_oversold(self) -> bool:
        """RSI indicates oversold condition."""
        return self.rsi.is_oversold if self.rsi else False

    @property
    def is_overbought(self) -> bool:
        """RSI indicates overbought condition."""
        return self.rsi.is_overbought if self.rsi else False

    @property
    def at_support(self) -> bool:
        """Price is at a support level."""
        return self.sr_levels.in_support_zone if self.sr_levels else False

    @property
    def at_resistance(self) -> bool:
        """Price is at a resistance level."""
        return self.sr_levels.in_resistance_zone if self.sr_levels else False

    @property
    def funding_bias(self) -> str:
        """Funding rate bias."""
        if not self.funding:
            return "neutral"
        if self.funding.is_extreme_long:
            return "extreme_long"
        if self.funding.is_extreme_short:
            return "extreme_short"
        return "neutral"

    @property
    def orderbook_bias(self) -> str:
        """Order book bias."""
        return self.orderbook.bias if self.orderbook else "balanced"

    def get_confluence_signals(self, direction: str) -> List[str]:
        """Get signals that align with the given direction.

        Args:
            direction: "LONG" or "SHORT"

        Returns:
            List of confluence signals
        """
        signals = []

        if direction == "LONG":
            if self.is_oversold:
                signals.append("RSI oversold")
            if self.at_support:
                signals.append("At support level")
            if self.funding and self.funding.is_extreme_short:
                signals.append("Extreme shorts (squeeze potential)")
            if self.vwap and self.vwap.is_below_vwap:
                signals.append("Below VWAP")
            if self.orderbook and self.orderbook.is_bullish:
                signals.append("Bullish order book")
            if self.volume_profile and self.volume_profile.position_vs_poc == "below_poc":
                signals.append("Below POC")

        elif direction == "SHORT":
            if self.is_overbought:
                signals.append("RSI overbought")
            if self.at_resistance:
                signals.append("At resistance level")
            if self.funding and self.funding.is_extreme_long:
                signals.append("Extreme longs (dump potential)")
            if self.vwap and self.vwap.is_above_vwap:
                signals.append("Above VWAP")
            if self.orderbook and self.orderbook.is_bearish:
                signals.append("Bearish order book")
            if self.volume_profile and self.volume_profile.position_vs_poc == "above_poc":
                signals.append("Above POC")

        return signals

    def to_prompt(self) -> str:
        """Format technical snapshot for LLM prompt."""
        lines = [f"=== {self.coin} TECHNICAL ==="]

        if self.rsi:
            condition = self.rsi.condition
            lines.append(f"RSI: {self.rsi.value:.1f} ({condition})")

        if self.vwap:
            pos = self.vwap.position
            lines.append(f"VWAP: ${self.vwap.vwap:.2f} ({self.vwap.deviation_pct:+.1f}%, {pos})")

        if self.atr:
            lines.append(f"ATR: ${self.atr.atr:.2f} ({self.atr.volatility_pct:.1f}% volatility)")

        if self.funding:
            bias = self.funding_bias
            lines.append(f"Funding: {self.funding.current_rate:.4%} ({bias})")

        if self.sr_levels:
            if self.sr_levels.nearest_support:
                dist = self.sr_levels.support_distance_pct
                lines.append(f"Support: ${self.sr_levels.nearest_support.price:.2f} ({dist:.1f}% below)")
            if self.sr_levels.nearest_resistance:
                dist = self.sr_levels.resistance_distance_pct
                lines.append(f"Resistance: ${self.sr_levels.nearest_resistance.price:.2f} ({dist:.1f}% above)")

        if self.volume_profile:
            vp = self.volume_profile
            lines.append(f"POC: ${vp.poc:.2f} ({vp.position_vs_poc})")

        if self.orderbook:
            ob = self.orderbook
            lines.append(f"Order Book: {ob.bias} (imbalance: {ob.imbalance:+.2f})")

        return "\n".join(lines)


class TechnicalManager:
    """Aggregates all technical indicators for the Strategist.

    Provides unified access to:
    - RSI (momentum)
    - VWAP (fair value)
    - ATR (volatility)
    - Funding rates (positioning)
    - Support/Resistance levels
    - Volume Profile
    - Order Book

    Graceful degradation: if any indicator fails, continues with available data.

    Usage:
        candle_fetcher = CandleFetcher()
        tech_mgr = TechnicalManager(candle_fetcher)
        snapshot = tech_mgr.get_technical_snapshot("SOL")
        print(snapshot.to_prompt())

        quality, reasons = tech_mgr.get_trade_setup_quality("SOL", "LONG")
        stop, tp = tech_mgr.get_dynamic_stops("SOL", "LONG", 100.0)
    """

    def __init__(
        self,
        candle_fetcher: CandleFetcher,
        rsi_calculator: Optional[RSICalculator] = None,
        vwap_calculator: Optional[VWAPCalculator] = None,
        atr_calculator: Optional[ATRCalculator] = None,
        funding_fetcher: Optional[FundingRateFetcher] = None,
        sr_detector: Optional[SRLevelDetector] = None,
        volume_profile: Optional[VolumeProfileCalculator] = None,
        orderbook_analyzer: Optional[OrderBookAnalyzer] = None
    ):
        """Initialize with technical indicator sources.

        Args:
            candle_fetcher: CandleFetcher instance (required)
            rsi_calculator: RSICalculator instance (created if None)
            vwap_calculator: VWAPCalculator instance (created if None)
            atr_calculator: ATRCalculator instance (created if None)
            funding_fetcher: FundingRateFetcher instance (created if None)
            sr_detector: SRLevelDetector instance (created if None)
            volume_profile: VolumeProfileCalculator instance (created if None)
            orderbook_analyzer: OrderBookAnalyzer instance (created if None)
        """
        self.candle_fetcher = candle_fetcher
        self.rsi = rsi_calculator or RSICalculator(candle_fetcher)
        self.vwap = vwap_calculator or VWAPCalculator(candle_fetcher)
        self.atr = atr_calculator or ATRCalculator(candle_fetcher)
        self.funding = funding_fetcher or FundingRateFetcher()
        self.sr_detector = sr_detector or SRLevelDetector(candle_fetcher)
        self.volume_profile = volume_profile or VolumeProfileCalculator(candle_fetcher)
        self.orderbook = orderbook_analyzer or OrderBookAnalyzer()

    def get_technical_snapshot(self, coin: str) -> TechnicalSnapshot:
        """Get complete technical snapshot for a coin.

        Args:
            coin: Coin symbol (e.g., "SOL")

        Returns:
            TechnicalSnapshot with all available indicators
        """
        return TechnicalSnapshot(
            coin=coin.upper(),
            rsi=self._get_rsi(coin),
            vwap=self._get_vwap(coin),
            atr=self._get_atr(coin),
            funding=self._get_funding(coin),
            sr_levels=self._get_sr_levels(coin),
            volume_profile=self._get_volume_profile(coin),
            orderbook=self._get_orderbook(coin),
            timestamp=datetime.now()
        )

    def get_trade_setup_quality(
        self,
        coin: str,
        direction: str
    ) -> Tuple[float, str]:
        """Calculate trade setup quality score.

        Args:
            coin: Coin symbol
            direction: "LONG" or "SHORT"

        Returns:
            Tuple of (score 0-100, reasons string)
        """
        snapshot = self.get_technical_snapshot(coin)
        score = 50  # Start neutral
        reasons = []

        if direction == "LONG":
            # Positive signals for LONG
            if snapshot.is_oversold:
                score += 15
                reasons.append("+15 RSI oversold")
            if snapshot.at_support:
                score += 15
                reasons.append("+15 at support")
            if snapshot.funding and snapshot.funding.is_extreme_short:
                score += 10
                reasons.append("+10 crowded shorts")
            if snapshot.orderbook and snapshot.orderbook.is_bullish:
                score += 10
                reasons.append("+10 bullish orderbook")

            # Negative signals for LONG
            if snapshot.is_overbought:
                score -= 20
                reasons.append("-20 RSI overbought")
            if snapshot.at_resistance:
                score -= 15
                reasons.append("-15 at resistance")
            if snapshot.funding and snapshot.funding.is_extreme_long:
                score -= 10
                reasons.append("-10 crowded longs")

        elif direction == "SHORT":
            # Positive signals for SHORT
            if snapshot.is_overbought:
                score += 15
                reasons.append("+15 RSI overbought")
            if snapshot.at_resistance:
                score += 15
                reasons.append("+15 at resistance")
            if snapshot.funding and snapshot.funding.is_extreme_long:
                score += 10
                reasons.append("+10 crowded longs")
            if snapshot.orderbook and snapshot.orderbook.is_bearish:
                score += 10
                reasons.append("+10 bearish orderbook")

            # Negative signals for SHORT
            if snapshot.is_oversold:
                score -= 20
                reasons.append("-20 RSI oversold")
            if snapshot.at_support:
                score -= 15
                reasons.append("-15 at support")
            if snapshot.funding and snapshot.funding.is_extreme_short:
                score -= 10
                reasons.append("-10 crowded shorts")

        # Clamp score
        score = max(0, min(100, score))

        return score, "; ".join(reasons) if reasons else "neutral setup"

    def get_dynamic_stops(
        self,
        coin: str,
        direction: str,
        entry_price: float
    ) -> Tuple[float, float]:
        """Calculate dynamic stop loss and take profit.

        Uses ATR and S/R levels for intelligent stop placement.

        Args:
            coin: Coin symbol
            direction: "LONG" or "SHORT"
            entry_price: Entry price

        Returns:
            Tuple of (stop_loss_price, take_profit_price)
        """
        atr_data = self._get_atr(coin)
        sr_data = self._get_sr_levels(coin)

        # Default multipliers
        stop_atr_mult = 1.5
        tp_atr_mult = 2.5

        # Get ATR value or fallback to 2% of price
        if atr_data and atr_data.atr > 0:
            atr_value = atr_data.atr
        else:
            atr_value = entry_price * 0.02

        if direction == "LONG":
            # Stop below entry
            stop_loss = entry_price - (atr_value * stop_atr_mult)

            # If we have support, use it if closer
            if sr_data and sr_data.nearest_support:
                support_stop = sr_data.nearest_support.zone_low * 0.995  # Just below zone
                if support_stop > stop_loss and support_stop < entry_price:
                    stop_loss = support_stop

            # Take profit above entry
            take_profit = entry_price + (atr_value * tp_atr_mult)

            # If we have resistance, use it if reasonable
            if sr_data and sr_data.nearest_resistance:
                resistance_tp = sr_data.nearest_resistance.zone_low * 0.995
                if resistance_tp < take_profit and resistance_tp > entry_price:
                    take_profit = resistance_tp

        else:  # SHORT
            # Stop above entry
            stop_loss = entry_price + (atr_value * stop_atr_mult)

            # If we have resistance, use it if closer
            if sr_data and sr_data.nearest_resistance:
                resistance_stop = sr_data.nearest_resistance.zone_high * 1.005
                if resistance_stop < stop_loss and resistance_stop > entry_price:
                    stop_loss = resistance_stop

            # Take profit below entry
            take_profit = entry_price - (atr_value * tp_atr_mult)

            # If we have support, use it if reasonable
            if sr_data and sr_data.nearest_support:
                support_tp = sr_data.nearest_support.zone_high * 1.005
                if support_tp > take_profit and support_tp < entry_price:
                    take_profit = support_tp

        return stop_loss, take_profit

    def get_position_size(
        self,
        coin: str,
        base_size: float,
        direction: str
    ) -> float:
        """Calculate position size based on volatility and setup quality.

        Args:
            coin: Coin symbol
            base_size: Base position size
            direction: "LONG" or "SHORT"

        Returns:
            Adjusted position size
        """
        # Get setup quality
        quality, _ = self.get_trade_setup_quality(coin, direction)

        # Get volatility
        atr_data = self._get_atr(coin)

        # Quality adjustment: scale 0.5x to 1.5x based on quality
        quality_mult = 0.5 + (quality / 100)  # 50 quality = 1.0x

        # Volatility adjustment: reduce size in high volatility
        vol_mult = 1.0
        if atr_data:
            if atr_data.atr_pct > 5:  # High volatility
                vol_mult = 0.7
            elif atr_data.atr_pct > 3:  # Medium volatility
                vol_mult = 0.85

        return base_size * quality_mult * vol_mult

    def _get_rsi(self, coin: str) -> Optional[RSIData]:
        """Get RSI with error handling."""
        try:
            return self.rsi.calculate(coin)
        except Exception as e:
            logger.warning(f"Failed to get RSI for {coin}: {e}")
            return None

    def _get_vwap(self, coin: str) -> Optional[VWAPData]:
        """Get VWAP with error handling."""
        try:
            return self.vwap.calculate(coin)
        except Exception as e:
            logger.warning(f"Failed to get VWAP for {coin}: {e}")
            return None

    def _get_atr(self, coin: str) -> Optional[ATRData]:
        """Get ATR with error handling."""
        try:
            return self.atr.calculate(coin)
        except Exception as e:
            logger.warning(f"Failed to get ATR for {coin}: {e}")
            return None

    def _get_funding(self, coin: str) -> Optional[FundingData]:
        """Get funding rate with error handling."""
        try:
            return self.funding.get_funding_rate(coin)
        except Exception as e:
            logger.warning(f"Failed to get funding for {coin}: {e}")
            return None

    def _get_sr_levels(self, coin: str) -> Optional[SRLevels]:
        """Get S/R levels with error handling."""
        try:
            return self.sr_detector.detect(coin)
        except Exception as e:
            logger.warning(f"Failed to get S/R levels for {coin}: {e}")
            return None

    def _get_volume_profile(self, coin: str) -> Optional[VolumeProfile]:
        """Get volume profile with error handling."""
        try:
            return self.volume_profile.calculate(coin)
        except Exception as e:
            logger.warning(f"Failed to get volume profile for {coin}: {e}")
            return None

    def _get_orderbook(self, coin: str) -> Optional[OrderBookDepth]:
        """Get orderbook with error handling."""
        try:
            return self.orderbook.analyze(coin)
        except Exception as e:
            logger.warning(f"Failed to get orderbook for {coin}: {e}")
            return None
