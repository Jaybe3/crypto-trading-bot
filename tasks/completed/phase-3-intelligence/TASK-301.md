# TASK-301: Fear & Greed Index Integration

**Status:** Complete
**Phase:** 3A - Sentiment Layer
**Priority:** High
**Estimated Complexity:** Low

---

## Overview

Integrate the Alternative.me Fear & Greed Index to provide market-wide sentiment context to the Strategist. This single number (0-100) captures overall crypto market sentiment.

---

## Requirements

### Core Functionality
- Fetch Fear & Greed Index from Alternative.me API
- Cache value with 1-hour TTL (index updates daily)
- Provide sentiment classification (Extreme Fear/Fear/Neutral/Greed/Extreme Greed)
- Store historical values for pattern analysis

### API Integration
```python
# Endpoint
GET https://api.alternative.me/fng/

# Response
{
  "data": [{
    "value": "25",
    "value_classification": "Extreme Fear",
    "timestamp": "1234567890"
  }]
}
```

### Data Model
```python
@dataclass
class FearGreedData:
    value: int              # 0-100
    classification: str     # "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
    timestamp: datetime

    @property
    def is_extreme_fear(self) -> bool:
        return self.value < 25

    @property
    def is_extreme_greed(self) -> bool:
        return self.value > 75
```

---

## File Structure

```
src/
  sentiment/
    __init__.py
    fear_greed.py         # FearGreedFetcher class
```

---

## Implementation Notes

### Caching Strategy
- Cache for 1 hour (API updates daily but we want freshness)
- Fallback to last known value if API fails
- Log staleness warnings if >24 hours old

### Error Handling
- Retry 3x with exponential backoff on API failure
- Return None with warning if all retries fail
- Never block trading on sentiment fetch failure

---

## Testing Requirements

### Unit Tests
- [ ] Test API response parsing
- [ ] Test classification boundaries (24/25, 45/46, 54/55, 74/75)
- [ ] Test caching behavior
- [ ] Test error handling

### Integration Tests
- [ ] Test real API call (can be skipped in CI)
- [ ] Test staleness detection

---

## Acceptance Criteria

- [ ] FearGreedFetcher class implemented
- [ ] Caching with 1-hour TTL working
- [ ] Classification accurate at boundaries
- [ ] Graceful degradation on API failure
- [ ] All tests passing
- [ ] Historical values stored in database

---

## Dependencies

- None (foundational task)

## Blocked By

- None

## Blocks

- TASK-305 (ContextManager Integration)

---

*Created: February 3, 2026*

---

## Implementation Summary

**Date:** 2026-02-03

**Files Created:**
- src/sentiment/__init__.py
- src/sentiment/fear_greed.py (FearGreedFetcher class)
- tests/test_fear_greed.py (11 tests)

**Verification:** All tests passing, live API returns data (Fear & Greed: 14)

