# TASK-300: Sentiment & Context Layer

**Status:** NOT STARTED
**Created:** February 2, 2026
**Completed:** N/A
**Priority:** Medium
**Depends On:** Phase 2 complete (core learning loop proven)
**Phase:** Phase 3 - Market Context Enhancement

---

## Objective

Add market-wide context and sentiment data to improve decision quality by enabling the bot to understand *why* prices are moving, not just *that* they're moving.

---

## Background

### The Problem

Currently, the bot can only learn from its own trades:
- "BTC dumped and I lost money" → learns "don't trade when BTC dumps"
- But it has to lose money first to learn this

With sentiment and context data, the bot can:
- See BTC dumping before entering an altcoin trade
- Check if fear is extreme (likely bottom, not time to short)
- Know if there's negative news driving the move
- Understand if this is coin-specific or market-wide

### Example Scenario

Without context:
1. SOL drops 5%
2. Bot sees momentum, enters short
3. SOL recovers because the drop was just tracking BTC
4. Bot loses money, learns "SOL shorts don't work"

With context:
1. SOL drops 5%
2. Bot checks: BTC also down 4%, Fear & Greed at 25 (fear)
3. Bot recognizes: "This is a market-wide dip, not SOL weakness"
4. Bot skips the trade or goes long on the oversold bounce

---

## Specification

### Component 1: BTC Correlation Check

**Purpose:** Determine if a coin's move is independent or market-correlated

```python
@dataclass
class MarketCorrelation:
    coin: str
    coin_change_1h: float      # e.g., -5%
    btc_change_1h: float       # e.g., -4%
    correlation: str           # "correlated", "decoupled", "leading"
    independent_move: float    # coin_change - (btc_change * beta)
```

**Data Source:** Already have BTC price from MarketFeed

**Implementation:**
- Track BTC 1h change alongside each coin
- Calculate if coin is moving with or against BTC
- Flag moves that are coin-specific vs market-wide

### Component 2: Fear & Greed Index

**Purpose:** Overall market sentiment gauge

```python
@dataclass
class FearGreedData:
    value: int                 # 0-100
    classification: str        # "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
    timestamp: datetime
```

**Data Source:** [Alternative.me Crypto Fear & Greed API](https://alternative.me/crypto/fear-and-greed-index/)

```bash
curl "https://api.alternative.me/fng/"
# Returns: {"data":[{"value":"25","value_classification":"Fear",...}]}
```

**Update Frequency:** Once per hour (index updates daily, but cache hourly)

**Usage Rules:**
- Extreme Fear (0-25): Avoid shorts, look for bounce longs
- Fear (25-45): Cautious, smaller positions
- Neutral (45-55): Normal operation
- Greed (55-75): Cautious on longs
- Extreme Greed (75-100): Avoid longs, look for short setups

### Component 3: News API Integration

**Purpose:** Event-driven context for sudden moves

```python
@dataclass
class NewsItem:
    title: str
    source: str
    coins: list[str]           # Mentioned coins
    sentiment: str             # "positive", "negative", "neutral"
    importance: str            # "high", "medium", "low"
    timestamp: datetime
```

**Data Source Options:**

1. **CryptoPanic API** (recommended)
   - Free tier: 50 requests/hour
   - Coin filtering, sentiment included
   - `https://cryptopanic.com/api/v1/posts/`

2. **Messari News API**
   - Requires API key
   - Higher quality, curated

3. **RSS Feeds** (fallback)
   - CoinDesk, CoinTelegraph RSS
   - Free, but requires sentiment analysis

**Update Frequency:** Every 5 minutes

**Usage:**
- Check for negative news before entering long
- Check for positive news before entering short
- Flag coins with recent high-importance news

### Component 4: Social Sentiment (Optional/Future)

**Purpose:** Crowd mood and attention metrics

```python
@dataclass
class SocialSentiment:
    coin: str
    sentiment_score: float     # -1 to 1
    social_volume: int         # Tweet/post count
    trending: bool
    timestamp: datetime
```

**Data Source Options:**

1. **LunarCrush** (recommended)
   - Social metrics for crypto
   - Galaxy Score, AltRank
   - Free tier available

2. **Santiment**
   - Social volume, sentiment
   - More expensive

**Update Frequency:** Every 15 minutes

---

## Technical Approach

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ContextManager                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   BTC        │  │  Fear/Greed  │  │    News      │       │
│  │ Correlation  │  │    Index     │  │    Feed      │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │                │
│         └────────────┬────┴────────────────┘                │
│                      ▼                                       │
│              ┌──────────────┐                                │
│              │   Context    │                                │
│              │   Summary    │                                │
│              └──────────────┘                                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Strategist  │
                    └──────────────┘
```

### Context Summary

```python
@dataclass
class MarketContext:
    # BTC correlation
    btc_trend: str              # "up", "down", "sideways"
    btc_change_1h: float
    btc_change_24h: float

    # Sentiment
    fear_greed_value: int
    fear_greed_class: str

    # News
    recent_news_count: int
    negative_news_coins: list[str]
    positive_news_coins: list[str]

    # Social (if available)
    trending_coins: list[str]

    # Computed
    market_condition: str       # "risk_on", "risk_off", "neutral", "uncertain"
    avoid_longs: bool
    avoid_shorts: bool
    caution_level: int          # 0-10

def get_context_for_trade(self, coin: str, direction: str) -> dict:
    """Get relevant context for a potential trade."""
    return {
        "proceed": True/False,
        "caution_level": 0-10,
        "reasons": ["BTC dumping", "Extreme fear", ...],
        "suggestions": ["Wait for BTC stabilization", ...]
    }
```

### Integration with Strategist

```python
class Strategist:
    def __init__(self, ..., context_manager: ContextManager):
        self.context = context_manager

    def analyze_opportunity(self, coin: str, signal: str) -> TradeCondition:
        # Get market context
        ctx = self.context.get_context_for_trade(coin, signal)

        if not ctx["proceed"]:
            logger.info(f"Skipping {coin} {signal}: {ctx['reasons']}")
            return None

        # Adjust position size based on caution level
        size_multiplier = 1.0 - (ctx["caution_level"] * 0.1)

        # Include context in reasoning
        reasoning = f"Signal: {signal}. Context: {ctx['suggestions']}"

        return TradeCondition(...)
```

---

## Files Created

| File | Purpose |
|------|---------|
| `src/context/manager.py` | ContextManager orchestrator |
| `src/context/btc_correlation.py` | BTC correlation tracking |
| `src/context/fear_greed.py` | Fear & Greed Index client |
| `src/context/news_feed.py` | News API integration |
| `src/context/social.py` | Social sentiment (optional) |
| `tests/test_context.py` | Unit tests |

---

## Files Modified

| File | Change |
|------|--------|
| `src/strategist.py` | Inject ContextManager, use in analysis |
| `src/journal.py` | Record context with each trade |
| `config/settings.py` | Add API keys and update intervals |

---

## Acceptance Criteria

- [ ] BTC correlation calculated for each coin
- [ ] Fear & Greed Index fetched and cached
- [ ] News feed integrated (at least one source)
- [ ] Context summary generated
- [ ] Strategist uses context to filter/adjust trades
- [ ] Context recorded in trade journal
- [ ] System degrades gracefully if APIs unavailable

---

## Verification

```bash
# Test context gathering
python -c "
from src.context.manager import ContextManager

ctx = ContextManager()
ctx.update()

summary = ctx.get_summary()
print(f'Fear/Greed: {summary.fear_greed_value} ({summary.fear_greed_class})')
print(f'BTC 1h: {summary.btc_change_1h:+.2f}%')
print(f'Market condition: {summary.market_condition}')
print(f'Avoid longs: {summary.avoid_longs}')
print(f'Avoid shorts: {summary.avoid_shorts}')

# Test trade context
trade_ctx = ctx.get_context_for_trade('SOL', 'LONG')
print(f'Proceed with SOL LONG: {trade_ctx[\"proceed\"]}')
print(f'Reasons: {trade_ctx[\"reasons\"]}')
"
```

---

## Completion Notes

*To be filled after implementation*

---

## API Rate Limits & Costs

| API | Free Tier | Rate Limit | Notes |
|-----|-----------|------------|-------|
| Alternative.me F&G | Yes | Unlimited | Updates daily |
| CryptoPanic | Yes | 50/hour | Good for news |
| LunarCrush | Yes (limited) | 10/min | Social metrics |

---

## Related

- [TASK-110](./TASK-110.md) - Strategist (consumes context)
- [TASK-102](./TASK-102.md) - Trade Journal (records context)
- [PHASE-3-INDEX.md](../PHASE-3-INDEX.md) - Phase overview
