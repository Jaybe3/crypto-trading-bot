# TASK-304: Social Sentiment Integration

**Status:** Not Started
**Phase:** 3A - Sentiment Layer
**Priority:** Low
**Estimated Complexity:** Medium

---

## Overview

Integrate LunarCrush social metrics to detect trending coins and social sentiment shifts. Social activity often precedes price moves.

---

## Requirements

### Core Functionality
- Fetch social metrics from LunarCrush API
- Track social volume and sentiment per coin
- Detect unusual social activity spikes
- Identify trending coins before price moves

### API Integration
```python
# Endpoint (free tier)
GET https://lunarcrush.com/api3/coins/{symbol}
    ?key={API_KEY}

# Response
{
  "data": {
    "symbol": "SOL",
    "social_volume": 12500,
    "social_score": 78,
    "social_contributors": 3400,
    "sentiment": 65,          # 0-100, 50 = neutral
    "galaxy_score": 72,       # Overall health score
    "alt_rank": 5             # Rank among alts
  }
}
```

### Data Model
```python
@dataclass
class SocialMetrics:
    coin: str
    social_volume: int        # Total mentions
    social_score: int         # 0-100 engagement score
    sentiment: int            # 0-100, 50 = neutral
    galaxy_score: int         # Overall health
    alt_rank: int             # Rank among alts
    timestamp: datetime

    @property
    def is_trending(self) -> bool:
        return self.alt_rank <= 10

    @property
    def is_bullish_sentiment(self) -> bool:
        return self.sentiment > 60

    @property
    def is_bearish_sentiment(self) -> bool:
        return self.sentiment < 40
```

---

## File Structure

```
src/
  sentiment/
    social_sentiment.py   # SocialSentimentFetcher class
```

---

## Implementation Notes

### Rate Limiting
- Free tier: Limited requests
- Cache for 15 minutes
- Prioritize top coins

### Spike Detection
```python
def detect_social_spike(current_volume: int,
                        historical_avg: float) -> bool:
    """
    Social spike if volume > 2x historical average
    """
    return current_volume > (historical_avg * 2)
```

### Usage in Strategist
- Trending coin with bullish sentiment = opportunity signal
- Sudden social spike = potential volatility ahead
- Low social activity = likely to follow BTC

---

## Testing Requirements

### Unit Tests
- [ ] Test API response parsing
- [ ] Test sentiment classification
- [ ] Test trending detection
- [ ] Test spike detection

### Integration Tests
- [ ] Test real API call (can be skipped in CI)
- [ ] Test rate limiting behavior

---

## Acceptance Criteria

- [ ] SocialSentimentFetcher class implemented
- [ ] Social metrics tracked per coin
- [ ] Trending coins identified
- [ ] Social spikes detected
- [ ] Rate limiting respected
- [ ] All tests passing

---

## Dependencies

- LunarCrush API key (free tier)

## Blocked By

- None

## Blocks

- TASK-305 (ContextManager Integration)

---

*Created: February 3, 2026*
