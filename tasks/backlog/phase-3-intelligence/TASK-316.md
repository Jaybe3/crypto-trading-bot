# TASK-316: Order Book Depth

**Status:** Not Started
**Phase:** 3B - Technical Indicators
**Priority:** Low
**Estimated Complexity:** Medium

---

## Overview

Analyze order book depth to detect large support/resistance walls and imbalances. Order book data reveals trader positioning.

---

## Requirements

### Core Functionality
- Fetch order book snapshot from Bybit
- Calculate bid/ask imbalance
- Detect large walls (significant orders)
- Track depth at key price levels

### API Integration
```python
# Bybit Order Book endpoint
GET /v5/market/orderbook
    ?category=linear
    &symbol=BTCUSDT
    &limit=50

# Response
{
  "result": {
    "b": [["22950.00", "1.5"], ...],   # Bids [price, size]
    "a": [["22951.00", "0.8"], ...],   # Asks [price, size]
    "ts": 1675209600000
  }
}
```

### Data Model
```python
@dataclass
class OrderBookDepth:
    coin: str
    bid_volume: float         # Total bid volume
    ask_volume: float         # Total ask volume
    imbalance: float          # (bid - ask) / (bid + ask), -1 to +1
    bid_walls: List[PriceWall]  # Large bid orders
    ask_walls: List[PriceWall]  # Large ask orders
    spread_pct: float         # Bid-ask spread as %
    timestamp: datetime

    @property
    def bias(self) -> str:
        if self.imbalance > 0.2:
            return "strong_bid"  # Buying pressure
        if self.imbalance < -0.2:
            return "strong_ask"  # Selling pressure
        return "balanced"

@dataclass
class PriceWall:
    price: float
    size: float
    side: str                 # "bid" or "ask"
    distance_pct: float       # Distance from current price

    @property
    def is_significant(self) -> bool:
        # Wall > 3x average order size
        return self.size > self.avg_size * 3
```

---

## File Structure

```
src/
  technical/
    orderbook.py          # OrderBookAnalyzer class
```

---

## Implementation Notes

### Wall Detection
```python
def detect_walls(orders: List[tuple], avg_size: float,
                 multiplier: float = 3.0) -> List[PriceWall]:
    """
    Detect orders significantly larger than average.
    """
    walls = []
    for price, size in orders:
        if size > avg_size * multiplier:
            walls.append(PriceWall(
                price=float(price),
                size=float(size),
                ...
            ))
    return walls
```

### Imbalance Calculation
```python
def calculate_imbalance(bids: List, asks: List,
                        depth_pct: float = 1.0) -> float:
    """
    Calculate bid/ask imbalance within depth_pct of mid price.
    """
    mid = (float(bids[0][0]) + float(asks[0][0])) / 2
    upper = mid * (1 + depth_pct / 100)
    lower = mid * (1 - depth_pct / 100)

    bid_vol = sum(float(s) for p, s in bids if float(p) >= lower)
    ask_vol = sum(float(s) for p, s in asks if float(p) <= upper)

    total = bid_vol + ask_vol
    if total == 0:
        return 0

    return (bid_vol - ask_vol) / total
```

### Strategist Usage
```
SOL Order Book:
- Imbalance: +0.35 (strong bid bias - buyers stacking)
- Bid Wall: 50,000 SOL at $98.00 (2% below)
- Ask Wall: 30,000 SOL at $105.00 (3% above)
- Interpretation: Stronger support than resistance
```

### Limitations
- Order book can be spoofed
- Walls can be pulled before hit
- Use as supporting data, not primary signal

---

## Testing Requirements

### Unit Tests
- [ ] Test order book parsing
- [ ] Test imbalance calculation
- [ ] Test wall detection
- [ ] Test depth analysis

### Integration Tests
- [ ] Test real API call (can be skipped in CI)

---

## Acceptance Criteria

- [ ] OrderBookAnalyzer class implemented
- [ ] Bid/ask imbalance calculated
- [ ] Walls detected at threshold
- [ ] Spread calculated
- [ ] All tests passing

---

## Dependencies

- Bybit API (existing)

## Blocked By

- None

## Blocks

- TASK-317 (TechnicalManager Integration)

---

*Created: February 3, 2026*
