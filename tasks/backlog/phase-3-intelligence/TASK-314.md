# TASK-314: Support/Resistance Levels

**Status:** Not Started
**Phase:** 3B - Technical Indicators
**Priority:** Medium
**Estimated Complexity:** Medium

---

## Overview

Implement automatic support/resistance level detection from historical price data. These levels are key for entry/exit decisions.

---

## Requirements

### Core Functionality
- Detect swing highs and lows from candle data
- Cluster nearby levels into zones
- Rank levels by strength (touches)
- Track level proximity for current price

### Level Detection Algorithm
```python
def find_swing_points(candles: List[Candle],
                      lookback: int = 5) -> List[tuple[float, str]]:
    """
    Find swing highs and lows.
    A swing high: high > all highs in lookback on both sides
    A swing low: low < all lows in lookback on both sides
    """
    points = []
    for i in range(lookback, len(candles) - lookback):
        candle = candles[i]

        # Check for swing high
        is_swing_high = all(
            candle.high > candles[j].high
            for j in range(i - lookback, i + lookback + 1)
            if j != i
        )
        if is_swing_high:
            points.append((candle.high, "resistance"))

        # Check for swing low
        is_swing_low = all(
            candle.low < candles[j].low
            for j in range(i - lookback, i + lookback + 1)
            if j != i
        )
        if is_swing_low:
            points.append((candle.low, "support"))

    return points
```

### Data Model
```python
@dataclass
class PriceLevel:
    price: float
    level_type: str           # "support" or "resistance"
    strength: int             # Number of touches
    last_touch: datetime
    zone_low: float           # Level is actually a zone
    zone_high: float

    def price_in_zone(self, price: float) -> bool:
        return self.zone_low <= price <= self.zone_high

@dataclass
class SRLevels:
    coin: str
    support_levels: List[PriceLevel]   # Sorted by proximity
    resistance_levels: List[PriceLevel]
    current_price: float
    nearest_support: Optional[PriceLevel]
    nearest_resistance: Optional[PriceLevel]

    @property
    def support_distance_pct(self) -> Optional[float]:
        if not self.nearest_support:
            return None
        return ((self.current_price - self.nearest_support.price)
                / self.current_price * 100)

    @property
    def resistance_distance_pct(self) -> Optional[float]:
        if not self.nearest_resistance:
            return None
        return ((self.nearest_resistance.price - self.current_price)
                / self.current_price * 100)
```

---

## File Structure

```
src/
  technical/
    support_resistance.py # SRLevelDetector class
```

---

## Implementation Notes

### Level Clustering
```python
def cluster_levels(points: List[float],
                   tolerance_pct: float = 0.5) -> List[PriceLevel]:
    """
    Cluster nearby price points into zones.
    Points within tolerance_pct are merged.
    Strength = number of points in cluster.
    """
    # Sort points
    # Merge points within tolerance
    # Return zones with strength
    ...
```

### Timeframe Selection
- Use 4h or 1h candles for meaningful levels
- Higher timeframe = stronger levels
- Track multiple timeframes

### Strategist Usage
```
SOL S/R Levels:
- Nearest Support: $98.50 (3 touches, 2.5% below)
- Nearest Resistance: $105.00 (5 touches, 2.4% above)
- Trade idea: Long at support with stop below
```

---

## Testing Requirements

### Unit Tests
- [ ] Test swing point detection
- [ ] Test level clustering
- [ ] Test proximity calculation
- [ ] Test strength counting

### Visual Validation
- Plot detected levels on chart to verify accuracy

---

## Acceptance Criteria

- [ ] SRLevelDetector class implemented
- [ ] Swing points detected accurately
- [ ] Levels clustered into zones
- [ ] Strength (touches) counted
- [ ] Proximity to current price calculated
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
