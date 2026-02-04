# TASK-302: BTC Correlation Tracking

**Status:** Not Started
**Phase:** 3A - Sentiment Layer
**Priority:** High
**Estimated Complexity:** Medium

---

## Overview

Track Bitcoin's price movement to detect market-wide moves vs coin-specific moves. When BTC moves significantly, altcoin moves in the same direction are likely correlation, not independent signals.

---

## Requirements

### Core Functionality
- Track BTC price from existing MarketFeed
- Calculate rolling correlation for each altcoin vs BTC
- Detect "BTC-driven" moves (altcoin moving with BTC)
- Provide correlation context to Strategist

### Correlation Detection
```python
@dataclass
class BTCCorrelation:
    coin: str
    btc_change_1h: float      # BTC % change in last hour
    coin_change_1h: float     # Coin % change in last hour
    correlation_24h: float    # Rolling 24h correlation coefficient
    is_btc_driven: bool       # True if move appears BTC-correlated

    @classmethod
    def calculate(cls, coin: str, btc_prices: List[float],
                  coin_prices: List[float]) -> "BTCCorrelation":
        # Pearson correlation over 24h of hourly candles
        ...
```

### Move Classification
```python
def is_btc_driven_move(btc_change: float, coin_change: float,
                       correlation: float) -> bool:
    """
    A move is BTC-driven if:
    1. BTC moved significantly (>1%)
    2. Coin moved in same direction
    3. Historical correlation is >0.5
    """
    if abs(btc_change) < 1.0:
        return False
    if (btc_change > 0) != (coin_change > 0):
        return False
    return correlation > 0.5
```

---

## File Structure

```
src/
  sentiment/
    btc_correlation.py    # BTCCorrelationTracker class
```

---

## Implementation Notes

### Data Source
- Use existing MarketFeed WebSocket data for BTC
- Store hourly snapshots for correlation calculation
- 24 hours of data needed for meaningful correlation

### Strategist Integration
When a coin shows a significant move:
- Calculate if move is BTC-driven
- If BTC-driven: "SOL down 3% (tracking BTC down 2.5%)"
- If independent: "SOL down 3% (BTC flat - coin-specific)"

---

## Testing Requirements

### Unit Tests
- [ ] Test correlation calculation accuracy
- [ ] Test BTC-driven detection logic
- [ ] Test edge cases (BTC flat, opposite moves)

### Integration Tests
- [ ] Test with real MarketFeed data
- [ ] Test rolling window updates

---

## Acceptance Criteria

- [ ] BTCCorrelationTracker class implemented
- [ ] Rolling 24h correlation calculated
- [ ] BTC-driven move detection working
- [ ] Integrates with existing MarketFeed
- [ ] All tests passing

---

## Dependencies

- MarketFeed (existing)

## Blocked By

- None

## Blocks

- TASK-305 (ContextManager Integration)

---

*Created: February 3, 2026*
