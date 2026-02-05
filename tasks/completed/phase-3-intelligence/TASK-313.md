# TASK-313: Funding Rates

**Status:** Complete
**Phase:** 3B - Technical Indicators
**Priority:** Medium
**Estimated Complexity:** Low

---

## Overview

Integrate perpetual futures funding rates to detect market positioning bias. Extreme funding rates often precede reversals.

---

## Requirements

### Core Functionality
- Fetch funding rates from Bybit API
- Track historical funding for trend detection
- Identify extreme funding (crowded trades)
- Calculate annualized funding cost

### API Integration
```python
# Bybit Funding Rate endpoint
GET /v5/market/funding/history
    ?category=linear
    &symbol=BTCUSDT
    &limit=200

# Response
{
  "result": {
    "list": [
      {
        "symbol": "BTCUSDT",
        "fundingRate": "0.0001",
        "fundingRateTimestamp": "1675209600000"
      }
    ]
  }
}
```

### Data Model
```python
@dataclass
class FundingData:
    coin: str
    current_rate: float       # Current funding rate (per 8h)
    predicted_rate: float     # Next predicted rate
    avg_24h: float            # 24h average
    annualized: float         # Annualized rate
    timestamp: datetime

    @property
    def is_extreme_long(self) -> bool:
        """Market is crowded long (pay to be long)."""
        return self.current_rate > 0.0005  # >0.05% per 8h

    @property
    def is_extreme_short(self) -> bool:
        """Market is crowded short (pay to be short)."""
        return self.current_rate < -0.0005

    @property
    def bias(self) -> str:
        if self.is_extreme_long:
            return "crowded_long"
        if self.is_extreme_short:
            return "crowded_short"
        if self.current_rate > 0:
            return "slight_long"
        return "slight_short"
```

---

## File Structure

```
src/
  technical/
    funding.py            # FundingRateFetcher class
```

---

## Implementation Notes

### Annualized Rate Calculation
```python
def annualized_funding(rate_per_8h: float) -> float:
    """
    3 funding payments per day * 365 days
    """
    return rate_per_8h * 3 * 365 * 100  # As percentage
```

### Trading Signals
- Extreme long funding + overbought RSI = potential short
- Extreme short funding + oversold RSI = potential long
- Funding flipping direction = trend change signal

### Strategist Usage
```
BTC Funding: +0.08% (annualized 87.6%)
- Market crowded long, expensive to hold longs
- Consider: Take profits on longs, look for short entries
```

---

## Testing Requirements

### Unit Tests
- [ ] Test funding rate parsing
- [ ] Test annualized calculation
- [ ] Test bias classification
- [ ] Test extreme detection thresholds

### Integration Tests
- [ ] Test real API call (can be skipped in CI)

---

## Acceptance Criteria

- [ ] FundingRateFetcher class implemented
- [ ] Current and predicted rates fetched
- [ ] Annualized rate calculated
- [ ] Extreme funding detected
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

---

## Implementation Summary

**Date:** 2026-02-03

**Files Created:**
- src/technical/funding.py (FundingRateFetcher class)
- tests/test_funding.py (23 tests)

**Features:**
- Bybit funding rate API integration
- Crowded position detection (extreme long/short)
- Contrarian signal generation
- Annualized rate calculation
- Direction avoidance recommendations

**Verification:** All 23 tests passing

