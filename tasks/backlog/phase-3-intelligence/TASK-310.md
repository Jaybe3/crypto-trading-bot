# TASK-310: RSI (Relative Strength Index)

**Status:** Complete
**Phase:** 3B - Technical Indicators
**Priority:** High
**Estimated Complexity:** Low

---

## Overview

Implement RSI calculation to identify overbought/oversold conditions. RSI is a momentum oscillator that measures speed and magnitude of price changes.

---

## Requirements

### Core Functionality
- Calculate RSI from candle close prices
- Support configurable period (default 14)
- Detect overbought (>70) and oversold (<30) conditions
- Support multiple timeframes

### Calculation
```python
def calculate_rsi(closes: List[float], period: int = 14) -> float:
    """
    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss over period
    """
    if len(closes) < period + 1:
        return 50.0  # Neutral if insufficient data

    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]

    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
```

### Data Model
```python
@dataclass
class RSIData:
    coin: str
    value: float              # 0-100
    period: int
    timeframe: str
    timestamp: datetime

    @property
    def is_overbought(self) -> bool:
        return self.value > 70

    @property
    def is_oversold(self) -> bool:
        return self.value < 30

    @property
    def condition(self) -> str:
        if self.is_oversold:
            return "oversold"
        if self.is_overbought:
            return "overbought"
        return "neutral"
```

---

## File Structure

```
src/
  technical/
    rsi.py                # RSICalculator class
```

---

## Implementation Notes

### Multi-Timeframe RSI
```python
class RSICalculator:
    def __init__(self, candle_fetcher: CandleFetcher):
        self.candle_fetcher = candle_fetcher

    def get_rsi(self, coin: str, timeframe: str = "1h",
                period: int = 14) -> RSIData:
        candles = self.candle_fetcher.get_candles(coin, timeframe)
        closes = candles.closes()
        value = calculate_rsi(closes, period)
        return RSIData(
            coin=coin,
            value=value,
            period=period,
            timeframe=timeframe,
            timestamp=datetime.now()
        )
```

### Strategist Usage
```
SOL RSI(1h): 28 - OVERSOLD - potential bounce opportunity
BTC RSI(1h): 72 - OVERBOUGHT - consider taking profits
```

---

## Testing Requirements

### Unit Tests
- [ ] Test RSI calculation accuracy
- [ ] Test edge cases (all gains, all losses)
- [ ] Test insufficient data handling
- [ ] Test boundary conditions (exactly 30, exactly 70)

### Validation
- Compare calculated RSI against TradingView for same data

---

## Acceptance Criteria

- [ ] RSICalculator class implemented
- [ ] Calculation matches standard RSI formula
- [ ] Multi-timeframe support working
- [ ] Overbought/oversold detection accurate
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
- src/technical/rsi.py (RSICalculator class)
- tests/test_rsi.py (15 tests)

**Features:**
- Wilder's smoothing for accurate RSI
- Overbought/oversold detection (70/30 thresholds)
- Multi-timeframe support
- Works with CandleFetcher

**Verification:** All 15 tests passing

