# TASK-305: ContextManager & Strategist Integration

**Status:** Not Started
**Phase:** 3A - Sentiment Layer
**Priority:** High
**Estimated Complexity:** High

---

## Overview

Create a ContextManager that aggregates all sentiment sources and integrates with the Strategist to provide market context for trade decisions.

---

## Requirements

### Core Functionality
- Aggregate all sentiment sources into unified context
- Provide context snapshot for Strategist
- Log context with each trade for learning
- Support context-based trade filtering

### ContextManager Class
```python
class ContextManager:
    def __init__(self,
                 fear_greed: FearGreedFetcher,
                 btc_correlation: BTCCorrelationTracker,
                 news_feed: NewsFeedFetcher,
                 social: SocialSentimentFetcher):
        ...

    async def get_context(self) -> MarketContext:
        """Get current market context snapshot."""
        ...

    def get_coin_context(self, coin: str) -> CoinContext:
        """Get context specific to a coin."""
        ...

    def should_avoid_trading(self, coin: str) -> tuple[bool, str]:
        """Check if context suggests avoiding this trade."""
        ...
```

### Data Models
```python
@dataclass
class MarketContext:
    fear_greed: FearGreedData
    btc_change_1h: float
    btc_change_24h: float
    breaking_news: List[NewsItem]
    timestamp: datetime

    def to_prompt(self) -> str:
        """Format context for LLM prompt."""
        return f"""
Market Context:
- Fear & Greed: {self.fear_greed.value} ({self.fear_greed.classification})
- BTC 1h: {self.btc_change_1h:+.2f}%
- BTC 24h: {self.btc_change_24h:+.2f}%
- Breaking News: {len(self.breaking_news)} items
"""

@dataclass
class CoinContext:
    coin: str
    btc_correlation: BTCCorrelation
    recent_news: List[NewsItem]
    social_metrics: Optional[SocialMetrics]

    def to_prompt(self) -> str:
        """Format coin context for LLM prompt."""
        ...
```

---

## File Structure

```
src/
  sentiment/
    context_manager.py    # ContextManager class
    __init__.py           # Export all sentiment classes
```

---

## Strategist Integration

### Prompt Enhancement
```python
# In Strategist.generate_conditions()
context = await self.context_manager.get_context()

prompt = f"""
{context.to_prompt()}

Coin-specific context:
{self._format_coin_contexts(coins)}

Current prices:
{self._format_prices(prices)}

Generate trading conditions considering the market context.
If Fear & Greed is Extreme Fear, consider oversold bounces.
If a coin is moving with BTC, note it's a correlated move.
"""
```

### Trade Filtering
```python
# Before entering a trade
should_avoid, reason = context_manager.should_avoid_trading(coin)
if should_avoid:
    logger.info(f"Skipping {coin} trade: {reason}")
    return None
```

### Context Logging
```python
# When trade executes, log context
trade_record = {
    "trade_id": trade.id,
    "context": {
        "fear_greed": context.fear_greed.value,
        "btc_change_1h": context.btc_change_1h,
        "btc_driven": coin_context.btc_correlation.is_btc_driven,
        "breaking_news": len(coin_context.recent_news),
    }
}
```

---

## Implementation Notes

### Refresh Strategy
- Fear & Greed: Every hour
- BTC correlation: Every minute (uses MarketFeed data)
- News: Every 5 minutes
- Social: Every 15 minutes

### Graceful Degradation
- If any source fails, continue with available data
- Log warnings for missing context
- Never block trading due to context fetch failure

### Avoidance Rules
```python
def should_avoid_trading(self, coin: str) -> tuple[bool, str]:
    # Don't trade during extreme events
    if self.fear_greed.value < 10:
        return True, "Extreme Fear - market panic"
    if self.fear_greed.value > 90:
        return True, "Extreme Greed - likely top"

    # Don't trade coin with very negative breaking news
    news = self.get_coin_news(coin)
    if any(n.is_breaking and n.is_bearish for n in news):
        return True, f"Breaking negative news: {news[0].title}"

    return False, ""
```

---

## Testing Requirements

### Unit Tests
- [ ] Test context aggregation
- [ ] Test prompt formatting
- [ ] Test avoidance rules
- [ ] Test graceful degradation

### Integration Tests
- [ ] Test with mock sentiment sources
- [ ] Test Strategist integration
- [ ] Test context logging

---

## Acceptance Criteria

- [ ] ContextManager aggregates all sentiment sources
- [ ] Strategist receives context in prompts
- [ ] Trade avoidance rules working
- [ ] Context logged with each trade
- [ ] Graceful degradation on source failures
- [ ] All tests passing

---

## Dependencies

- TASK-301 (Fear & Greed)
- TASK-302 (BTC Correlation)
- TASK-303 (News Feed)
- TASK-304 (Social Sentiment)

## Blocked By

- TASK-301, TASK-302, TASK-303, TASK-304

## Blocks

- Phase 3B (Technical Indicators can use ContextManager pattern)

---

*Created: February 3, 2026*
