# TASK-311: VWAP (Volume-Weighted Average Price)

**Status:** Complete
**Phase:** 3B - Technical Indicators
**Priority:** Medium
**Estimated Complexity:** Low

---

## Implementation Summary

**Completed:** February 4, 2026

### Files Created
- `src/technical/vwap.py` - VWAPCalculator class with daily reset support
- `tests/test_vwap.py` - 19 unit tests

### Key Components
- **VWAPData** dataclass with position and mean_reversion_signal properties
- **VWAPCalculator** class with VWAP formula: Cumulative(TP*Vol) / Cumulative(Vol)
- Daily reset at UTC midnight via `_filter_to_today()`
- Standard deviation bands via `get_bands()`
- Mean reversion signals at ±3% deviation

### Test Results
- 19/19 tests passing
- Tests cover VWAP calculation, deviation, bands, daily reset

---

## Overview

Implement VWAP calculation to identify fair value and potential support/resistance. VWAP is widely used by institutional traders.

---

## Requirements

### Core Functionality
- Calculate VWAP from candle data (price * volume weighted)
- Reset daily (standard VWAP behavior)
- Calculate deviation bands (optional)
- Detect price relative to VWAP

### Calculation
```python
def calculate_vwap(candles: List[Candle]) -> float:
    """
    VWAP = Cumulative(Typical Price * Volume) / Cumulative(Volume)
    Typical Price = (High + Low + Close) / 3
    """
    if not candles:
        return 0.0

    cumulative_tpv = 0.0  # Typical Price * Volume
    cumulative_vol = 0.0

    for c in candles:
        typical_price = (c.high + c.low + c.close) / 3
        cumulative_tpv += typical_price * c.volume
        cumulative_vol += c.volume

    if cumulative_vol == 0:
        return candles[-1].close

    return cumulative_tpv / cumulative_vol
```

### Data Model
```python
@dataclass
class VWAPData:
    coin: str
    vwap: float
    current_price: float
    deviation_pct: float      # % above/below VWAP
    timestamp: datetime

    @property
    def is_above_vwap(self) -> bool:
        return self.current_price > self.vwap

    @property
    def is_below_vwap(self) -> bool:
        return self.current_price < self.vwap

    @property
    def position(self) -> str:
        if self.deviation_pct > 2:
            return "extended_above"
        if self.deviation_pct < -2:
            return "extended_below"
        if self.is_above_vwap:
            return "above"
        return "below"
```

---

## File Structure

```
src/
  technical/
    vwap.py               # VWAPCalculator class
```

---

## Implementation Notes

### Daily Reset
- VWAP resets at UTC midnight
- Filter candles to current day only
- Handle timezone correctly

### Deviation Bands
```python
def calculate_vwap_bands(candles: List[Candle],
                         std_multiplier: float = 2.0) -> tuple[float, float, float]:
    """
    Returns (vwap, upper_band, lower_band)
    Bands are +/- N standard deviations
    """
    vwap = calculate_vwap(candles)
    # Calculate standard deviation of price from VWAP
    # ... implementation
    return vwap, upper, lower
```

### Strategist Usage
```
SOL: $102.50 (VWAP: $100.00, +2.5% above)
- Price extended above VWAP, potential pullback target
```

---

## Testing Requirements

### Unit Tests
- [ ] Test VWAP calculation accuracy
- [ ] Test daily reset behavior
- [ ] Test deviation calculation
- [ ] Test position classification

### Validation
- Compare calculated VWAP against TradingView

---

## Acceptance Criteria

- [ ] VWAPCalculator class implemented
- [ ] Daily reset working correctly
- [ ] Deviation calculation accurate
- [ ] Position relative to VWAP detected
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
