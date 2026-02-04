# TASK-312: ATR (Average True Range)

**Status:** Complete
**Phase:** 3B - Technical Indicators
**Priority:** High
**Estimated Complexity:** Low

---

## Overview

Implement ATR calculation to measure volatility. ATR is essential for dynamic stop-loss/take-profit sizing.

---

## Requirements

### Core Functionality
- Calculate ATR from candle data
- Support configurable period (default 14)
- Express ATR as both absolute and percentage
- Use for position sizing and stop-loss calculation

### Calculation
```python
def calculate_true_range(candle: Candle, prev_close: float) -> float:
    """
    True Range = max of:
    1. Current High - Current Low
    2. abs(Current High - Previous Close)
    3. abs(Current Low - Previous Close)
    """
    return max(
        candle.high - candle.low,
        abs(candle.high - prev_close),
        abs(candle.low - prev_close)
    )

def calculate_atr(candles: List[Candle], period: int = 14) -> float:
    """
    ATR = SMA of True Range over period
    """
    if len(candles) < period + 1:
        return candles[-1].high - candles[-1].low  # Fallback

    true_ranges = []
    for i in range(1, len(candles)):
        tr = calculate_true_range(candles[i], candles[i-1].close)
        true_ranges.append(tr)

    return sum(true_ranges[-period:]) / period
```

### Data Model
```python
@dataclass
class ATRData:
    coin: str
    atr: float                # Absolute ATR
    atr_pct: float            # ATR as % of price
    period: int
    current_price: float
    timestamp: datetime

    @property
    def volatility_level(self) -> str:
        if self.atr_pct > 5:
            return "extreme"
        if self.atr_pct > 3:
            return "high"
        if self.atr_pct > 1.5:
            return "moderate"
        return "low"

    def suggested_stop_loss(self, multiplier: float = 1.5) -> float:
        """Suggested stop-loss distance based on ATR."""
        return self.atr * multiplier
```

---

## File Structure

```
src/
  technical/
    atr.py                # ATRCalculator class
```

---

## Implementation Notes

### ATR-Based Stops
```python
class ATRCalculator:
    def get_dynamic_stop(self, coin: str, direction: str,
                         entry_price: float,
                         atr_multiplier: float = 1.5) -> float:
        """
        Calculate stop-loss using ATR.
        LONG: entry - (ATR * multiplier)
        SHORT: entry + (ATR * multiplier)
        """
        atr_data = self.get_atr(coin)

        if direction == "LONG":
            return entry_price - (atr_data.atr * atr_multiplier)
        else:
            return entry_price + (atr_data.atr * atr_multiplier)
```

### Strategist Usage
```
SOL ATR(14): $2.50 (2.5% of price)
- Volatility: moderate
- Suggested SL: 1.5 ATR = $3.75 from entry
```

### Position Sizing Integration
- Higher ATR = smaller position (inverse relationship)
- Can be used to normalize risk across different coins

---

## Testing Requirements

### Unit Tests
- [ ] Test True Range calculation
- [ ] Test ATR calculation accuracy
- [ ] Test volatility classification
- [ ] Test stop-loss suggestions

### Validation
- Compare calculated ATR against TradingView

---

## Acceptance Criteria

- [ ] ATRCalculator class implemented
- [ ] True Range calculation accurate
- [ ] ATR percentage calculated
- [ ] Volatility level classification working
- [ ] Dynamic stop-loss calculation working
- [ ] All tests passing

---

## Dependencies

- TASK-309 (Candle Data Fetcher)

## Blocked By

- TASK-309

## Blocks

- TASK-317 (TechnicalManager Integration)

---

*Created: February 3, 2026*

---

## Implementation Summary

**Date:** 2026-02-03

**Files Created:**
- src/technical/atr.py (ATRCalculator class)
- tests/test_atr.py (19 tests)

**Features:**
- True Range calculation with gap handling
- Wilder's smoothing for ATR
- Volatility level classification
- Dynamic stop-loss/take-profit calculation
- Position size modifier based on volatility

**Verification:** All 19 tests passing

