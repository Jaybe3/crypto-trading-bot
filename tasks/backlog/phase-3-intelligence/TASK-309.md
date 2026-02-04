# TASK-309: Candle Data Fetcher

**Status:** Complete
**Phase:** 3B - Technical Indicators
**Priority:** High
**Estimated Complexity:** Medium

---

## Overview

Create a robust candle data fetcher to provide OHLCV data for technical indicator calculations. This is the foundation for all Phase 3B indicators.

---

## Requirements

### Core Functionality
- Fetch historical candles from Bybit API
- Support multiple timeframes (1m, 5m, 15m, 1h, 4h)
- Cache candles to reduce API calls
- Provide streaming updates from WebSocket

### API Integration
```python
# Bybit Kline endpoint
GET /v5/market/kline
    ?category=linear
    &symbol=BTCUSDT
    &interval=60        # 1h
    &limit=200

# Response
{
  "result": {
    "list": [
      ["1675209600000", "23000", "23100", "22900", "23050", "1234.5", "28000000"]
      # [timestamp, open, high, low, close, volume, turnover]
    ]
  }
}
```

### Data Model
```python
@dataclass
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)

    @property
    def wick_ratio(self) -> float:
        body = self.body_size
        total = self.high - self.low
        return (total - body) / total if total > 0 else 0

@dataclass
class CandleData:
    coin: str
    interval: str
    candles: List[Candle]

    def closes(self) -> List[float]:
        return [c.close for c in self.candles]

    def volumes(self) -> List[float]:
        return [c.volume for c in self.candles]
```

---

## File Structure

```
src/
  technical/
    __init__.py
    candle_fetcher.py     # CandleFetcher class
```

---

## Implementation Notes

### Caching Strategy
- Cache candles by (coin, interval)
- Update cache incrementally as new candles close
- Keep 200 candles per timeframe (enough for indicators)

### WebSocket Integration
- Subscribe to kline updates for live data
- Merge WebSocket updates with cached data
- Handle partial candles (current candle not closed)

### Rate Limiting
- Batch initial fetches on startup
- Use cached data during operation
- Only fetch on cache miss

---

## Testing Requirements

### Unit Tests
- [ ] Test candle parsing
- [ ] Test cache management
- [ ] Test property calculations (bullish, wick_ratio)

### Integration Tests
- [ ] Test real API call (can be skipped in CI)
- [ ] Test WebSocket updates

---

## Acceptance Criteria

- [ ] CandleFetcher class implemented
- [ ] Multiple timeframes supported
- [ ] Caching working correctly
- [ ] WebSocket updates integrated
- [ ] All tests passing

---

## Dependencies

- Bybit API (existing)
- MarketFeed WebSocket (existing)

## Blocked By

- None (foundational task)

## Blocks

- TASK-310 (RSI)
- TASK-311 (VWAP)
- TASK-312 (ATR)
- All other technical indicators

---

*Created: February 3, 2026*

---

## Implementation Summary

**Date:** 2026-02-03

**Files Created:**
- src/technical/__init__.py
- src/technical/candle_fetcher.py (CandleFetcher class)
- tests/test_candle_fetcher.py (19 tests)

**Verification:** All tests passing. Bybit API geo-blocked in CI but mocks verify functionality.

