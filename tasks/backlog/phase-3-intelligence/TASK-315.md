# TASK-315: Volume Profile

**Status:** Not Started
**Phase:** 3B - Technical Indicators
**Priority:** Low
**Estimated Complexity:** Medium

---

## Overview

Implement volume profile analysis to identify high-volume price zones. These zones act as magnets and support/resistance.

---

## Requirements

### Core Functionality
- Calculate volume distribution across price levels
- Identify Point of Control (POC) - highest volume level
- Identify Value Area (VA) - 70% of volume
- Detect High Volume Nodes (HVN) and Low Volume Nodes (LVN)

### Volume Profile Calculation
```python
def calculate_volume_profile(candles: List[Candle],
                             num_bins: int = 50) -> VolumeProfile:
    """
    Distribute volume across price bins.
    """
    # Find price range
    all_highs = [c.high for c in candles]
    all_lows = [c.low for c in candles]
    price_range = max(all_highs) - min(all_lows)
    bin_size = price_range / num_bins

    # Allocate volume to bins
    bins = defaultdict(float)
    for candle in candles:
        # Distribute candle volume across its price range
        candle_bins = int((candle.high - candle.low) / bin_size) + 1
        vol_per_bin = candle.volume / candle_bins

        current_price = candle.low
        while current_price <= candle.high:
            bin_idx = int((current_price - min(all_lows)) / bin_size)
            bins[bin_idx] += vol_per_bin
            current_price += bin_size

    return bins
```

### Data Model
```python
@dataclass
class VolumeProfile:
    coin: str
    poc: float                # Point of Control price
    value_area_high: float    # Upper bound of 70% volume
    value_area_low: float     # Lower bound of 70% volume
    hvn_levels: List[float]   # High Volume Nodes
    lvn_levels: List[float]   # Low Volume Nodes
    current_price: float
    timestamp: datetime

    @property
    def is_in_value_area(self) -> bool:
        return self.value_area_low <= self.current_price <= self.value_area_high

    @property
    def position_vs_poc(self) -> str:
        if self.current_price > self.poc * 1.01:
            return "above_poc"
        if self.current_price < self.poc * 0.99:
            return "below_poc"
        return "at_poc"
```

---

## File Structure

```
src/
  technical/
    volume_profile.py     # VolumeProfileCalculator class
```

---

## Implementation Notes

### POC and Value Area
```python
def find_poc_and_va(bins: dict, total_volume: float) -> tuple:
    """
    POC = bin with highest volume
    VA = bins containing 70% of total volume, centered on POC
    """
    poc_bin = max(bins, key=bins.get)

    # Expand from POC until 70% captured
    va_bins = {poc_bin}
    va_volume = bins[poc_bin]

    while va_volume < total_volume * 0.7:
        # Add adjacent bin with higher volume
        ...

    return poc_price, va_high, va_low
```

### Trading Implications
- Price tends to return to POC
- LVN = fast moves through these areas
- HVN = slow, choppy trading
- Outside VA = trending or reversal imminent

### Strategist Usage
```
SOL Volume Profile (24h):
- POC: $100.50 (price magnet)
- Value Area: $98.00 - $103.00
- Current: $105.00 (above VA - extended)
- Expectation: Mean reversion to POC likely
```

---

## Testing Requirements

### Unit Tests
- [ ] Test volume distribution
- [ ] Test POC identification
- [ ] Test Value Area calculation
- [ ] Test HVN/LVN detection

### Visual Validation
- Plot volume profile to verify accuracy

---

## Acceptance Criteria

- [ ] VolumeProfileCalculator class implemented
- [ ] POC calculated correctly
- [ ] Value Area (70%) identified
- [ ] HVN and LVN detected
- [ ] Position vs profile analyzed
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
