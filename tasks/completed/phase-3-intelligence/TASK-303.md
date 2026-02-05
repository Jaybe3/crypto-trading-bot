# TASK-303: News Feed Integration

**Status:** Complete
**Phase:** 3A - Sentiment Layer
**Priority:** Medium
**Estimated Complexity:** Medium

---

## Implementation Summary

**Completed:** February 4, 2026

### Files Created
- `src/sentiment/news_feed.py` - NewsFeedFetcher with CryptoPanic integration
- `tests/test_news_feed.py` - 25 unit tests

### Key Components
- **NewsItem** dataclass with sentiment_score, is_bullish, is_bearish properties
- **NewsFeed** dataclass aggregating items with overall_sentiment, breaking_news
- **NewsFeedFetcher** class with 5-minute cache, rate limiting (5 req/min)
- Sentiment calculation from positive/negative votes
- Breaking news detection (< 1 hour old)

### Test Results
- 25/25 tests passing
- Tests cover API parsing, sentiment calculation, breaking news detection

---

## Overview

Integrate CryptoPanic news feed to detect market-moving news events. The bot should be aware of major news before entering trades.

---

## Requirements

### Core Functionality
- Fetch recent news from CryptoPanic API
- Filter news relevant to tradeable coins
- Classify news sentiment (bullish/bearish/neutral)
- Detect breaking news that might affect trades

### API Integration
```python
# Endpoint (free tier)
GET https://cryptopanic.com/api/v1/posts/
    ?auth_token={TOKEN}
    &filter=hot
    &currencies=BTC,ETH,SOL

# Response
{
  "results": [{
    "title": "SOL Foundation announces major upgrade",
    "currencies": [{"code": "SOL"}],
    "published_at": "2026-02-03T12:00:00Z",
    "votes": {"positive": 45, "negative": 5},
    "kind": "news"
  }]
}
```

### Data Model
```python
@dataclass
class NewsItem:
    title: str
    coins: List[str]
    published_at: datetime
    sentiment_score: float  # -1 to +1 based on votes
    is_breaking: bool       # Published < 1 hour ago
    source: str

    @property
    def is_bullish(self) -> bool:
        return self.sentiment_score > 0.3

    @property
    def is_bearish(self) -> bool:
        return self.sentiment_score < -0.3
```

---

## File Structure

```
src/
  sentiment/
    news_feed.py          # NewsFeedFetcher class
```

---

## Implementation Notes

### Rate Limiting
- Free tier: 5 requests/minute
- Cache for 5 minutes
- Batch fetch all coins in one request

### Sentiment Calculation
```python
def calculate_sentiment(positive_votes: int, negative_votes: int) -> float:
    total = positive_votes + negative_votes
    if total == 0:
        return 0.0
    return (positive_votes - negative_votes) / total
```

### Breaking News Detection
- News < 1 hour old with high vote count
- Should trigger immediate context refresh

---

## Testing Requirements

### Unit Tests
- [ ] Test API response parsing
- [ ] Test sentiment calculation
- [ ] Test coin filtering
- [ ] Test breaking news detection

### Integration Tests
- [ ] Test real API call (can be skipped in CI)
- [ ] Test rate limiting behavior

---

## Acceptance Criteria

- [ ] NewsFeedFetcher class implemented
- [ ] News filtered to tradeable coins
- [ ] Sentiment score calculated correctly
- [ ] Breaking news detected
- [ ] Rate limiting respected
- [ ] All tests passing

---

## Dependencies

- CryptoPanic API token (free tier)

## Blocked By

- None

## Blocks

- TASK-305 (ContextManager Integration)

---

*Created: February 3, 2026*
