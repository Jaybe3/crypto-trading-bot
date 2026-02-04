# TASK-317: TechnicalManager & Strategist Integration

**Status:** ✅ Complete
**Phase:** 3B - Technical Indicators
**Priority:** High
**Estimated Complexity:** High
**Completed:** February 4, 2026

---

## Implementation Summary

### Files Created
- `src/technical/manager.py` - TechnicalManager, TechnicalSnapshot classes
- `tests/test_technical_manager.py` - 29 comprehensive tests

### Key Features
- **TechnicalSnapshot**: Aggregates RSI, VWAP, ATR, Funding, S/R, Volume Profile, Orderbook
  - `to_prompt()` for LLM formatting
  - `get_confluence_signals(direction)` for signal alignment
  - Properties: `current_price`, `is_oversold`, `is_overbought`, `at_support`, `at_resistance`, `funding_bias`
- **TechnicalManager**: Aggregates all technical indicators with graceful degradation
  - `get_technical_snapshot(coin)` - Complete technical analysis
  - `get_trade_setup_quality(coin, direction)` - Quality score 0-100 with reasons
  - `get_dynamic_stops(coin, direction, entry_price)` - ATR-based stops with S/R consideration
  - `get_position_size(coin, base_size, direction)` - Volatility and quality adjusted sizing

### Exports Added
- `TechnicalManager`, `TechnicalSnapshot` exported from `src/technical/__init__.py`

---

## Overview

Create a TechnicalManager that aggregates all technical indicators and integrates with the Strategist to provide technical analysis context for trade decisions.

---

## Requirements

### Core Functionality
- Aggregate all technical indicators
- Provide technical snapshot for Strategist
- Log technicals with each trade for learning
- Support indicator-based trade filtering

### TechnicalManager Class
```python
class TechnicalManager:
    def __init__(self,
                 candle_fetcher: CandleFetcher,
                 rsi: RSICalculator,
                 vwap: VWAPCalculator,
                 atr: ATRCalculator,
                 funding: FundingRateFetcher,
                 sr_levels: SRLevelDetector,
                 volume_profile: VolumeProfileCalculator,
                 orderbook: OrderBookAnalyzer):
        ...

    async def get_technical_snapshot(self, coin: str) -> TechnicalSnapshot:
        """Get all technical data for a coin."""
        ...

    def get_trade_setup_quality(self, coin: str,
                                direction: str) -> tuple[float, str]:
        """
        Score trade setup quality based on technicals.
        Returns (score 0-100, reasoning)
        """
        ...

    def get_dynamic_stops(self, coin: str, direction: str,
                          entry: float) -> tuple[float, float]:
        """
        Calculate ATR-based stop-loss and take-profit.
        """
        ...
```

### Data Models
```python
@dataclass
class TechnicalSnapshot:
    coin: str
    rsi: RSIData
    vwap: VWAPData
    atr: ATRData
    funding: FundingData
    sr_levels: SRLevels
    volume_profile: VolumeProfile
    orderbook: OrderBookDepth
    timestamp: datetime

    def to_prompt(self) -> str:
        """Format technicals for LLM prompt."""
        return f"""
Technical Analysis for {self.coin}:
- RSI(14): {self.rsi.value:.1f} ({self.rsi.condition})
- VWAP: ${self.vwap.vwap:.2f} (price {self.vwap.deviation_pct:+.1f}%)
- ATR(14): ${self.atr.atr:.2f} ({self.atr.volatility_level} volatility)
- Funding: {self.funding.current_rate*100:.3f}% ({self.funding.bias})
- Support: ${self.sr_levels.nearest_support.price:.2f} ({self.sr_levels.support_distance_pct:.1f}% below)
- Resistance: ${self.sr_levels.nearest_resistance.price:.2f} ({self.sr_levels.resistance_distance_pct:.1f}% above)
- Order Book: {self.orderbook.bias}
"""

    def get_confluence_signals(self, direction: str) -> List[str]:
        """Get list of signals supporting/opposing a direction."""
        ...
```

---

## File Structure

```
src/
  technical/
    manager.py            # TechnicalManager class
    __init__.py           # Export all technical classes
```

---

## Strategist Integration

### Prompt Enhancement
```python
# In Strategist.generate_conditions()
technical = await self.technical_manager.get_technical_snapshot(coin)

prompt = f"""
{context.to_prompt()}  # Sentiment context

{technical.to_prompt()}  # Technical analysis

Trade Setup Quality Considerations:
- Oversold RSI with support nearby = high quality long setup
- Overbought RSI with resistance nearby = high quality short setup
- Price extended from VWAP with crowded funding = reversal likely

Generate trading conditions using both sentiment and technical context.
"""
```

### Trade Quality Scoring
```python
def get_trade_setup_quality(self, coin: str,
                            direction: str) -> tuple[float, str]:
    """
    Score: 0-100
    - 80+: Excellent setup (multiple confirmations)
    - 60-79: Good setup (some confirmation)
    - 40-59: Neutral
    - <40: Poor setup (against technicals)
    """
    snapshot = self.get_technical_snapshot(coin)
    score = 50  # Base score
    reasons = []

    if direction == "LONG":
        # RSI oversold = bullish
        if snapshot.rsi.is_oversold:
            score += 15
            reasons.append("RSI oversold")

        # Price at support = bullish
        if snapshot.sr_levels.support_distance_pct < 1:
            score += 15
            reasons.append("At support level")

        # Crowded short funding = bullish
        if snapshot.funding.is_extreme_short:
            score += 10
            reasons.append("Crowded shorts (funding)")

        # RSI overbought = bearish for longs
        if snapshot.rsi.is_overbought:
            score -= 20
            reasons.append("RSI overbought (caution)")

    # Similar logic for SHORT...

    return score, ", ".join(reasons)
```

### Dynamic Position Sizing
```python
def get_position_size(self, coin: str, base_size: float,
                      direction: str) -> float:
    """
    Adjust position size based on:
    - ATR (volatility)
    - Setup quality
    """
    atr = self.atr.get_atr(coin)
    quality, _ = self.get_trade_setup_quality(coin, direction)

    # Reduce size for high volatility
    vol_factor = 1.0 / max(atr.atr_pct / 2, 1)  # 2% ATR = 1x, 4% ATR = 0.5x

    # Increase size for high quality setups
    quality_factor = quality / 60  # 80 quality = 1.33x, 40 quality = 0.67x

    return base_size * vol_factor * quality_factor
```

---

## Implementation Notes

### Refresh Strategy
- Candles: Real-time via WebSocket
- RSI/VWAP/ATR: On demand (from cached candles)
- Funding: Every 8 hours (or on demand)
- S/R Levels: Hourly
- Volume Profile: Hourly
- Order Book: On demand (not cached - changes rapidly)

### Graceful Degradation
- If any indicator fails, continue with available data
- Log warnings for missing technicals
- Never block trading due to technical fetch failure

### Trade Logging
```python
# When trade executes, log technicals
trade_record = {
    "trade_id": trade.id,
    "technicals": {
        "rsi": snapshot.rsi.value,
        "vwap_deviation": snapshot.vwap.deviation_pct,
        "atr_pct": snapshot.atr.atr_pct,
        "funding": snapshot.funding.current_rate,
        "support_distance": snapshot.sr_levels.support_distance_pct,
        "setup_quality": quality_score,
    }
}
```

---

## Testing Requirements

### Unit Tests
- [ ] Test snapshot aggregation
- [ ] Test prompt formatting
- [ ] Test quality scoring logic
- [ ] Test dynamic stop calculation
- [ ] Test position sizing

### Integration Tests
- [ ] Test with mock indicator sources
- [ ] Test Strategist integration
- [ ] Test technical logging

---

## Acceptance Criteria

- [ ] TechnicalManager aggregates all indicators
- [ ] Strategist receives technicals in prompts
- [ ] Trade setup quality scoring working
- [ ] Dynamic stops calculated correctly
- [ ] Technicals logged with each trade
- [ ] Graceful degradation on source failures
- [ ] All tests passing

---

## Dependencies

- TASK-309 (Candle Data Fetcher)
- TASK-310 (RSI)
- TASK-311 (VWAP)
- TASK-312 (ATR)
- TASK-313 (Funding Rates)
- TASK-314 (Support/Resistance)
- TASK-315 (Volume Profile)
- TASK-316 (Order Book Depth)

## Blocked By

- All TASK-309 through TASK-316

## Blocks

- Phase 4 (Advanced Learning)

---

*Created: February 3, 2026*
