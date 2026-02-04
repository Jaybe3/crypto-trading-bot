# Phase 3: Intelligence Layer

## Overview

Enhance the autonomous trader with market-wide context, sentiment data, and technical indicators to improve decision quality. The bot should understand *why* prices are moving, not just *that* they're moving.

**Prerequisite:** Phase 2 complete with proven learning loop

---

## Rationale

Phase 2 creates a bot that learns from its own trades. Phase 3 gives it external context to make better decisions *before* entering trades, rather than learning only through losses.

### Without Context (Phase 2)
1. SOL drops 5% → Bot enters short
2. SOL recovers (was just tracking BTC dip)
3. Bot loses money → Learns "SOL shorts risky"

### With Context (Phase 3)
1. SOL drops 5% → Bot checks: BTC also down 4%, Fear at 25, RSI oversold
2. Bot recognizes: "Market-wide dip, not SOL weakness, oversold bounce likely"
3. Bot skips short or goes long on oversold bounce
4. No loss required to learn

---

## Implementation Phases

### Phase 3A: Sentiment Layer
| Task | Description | Priority | Status |
|------|-------------|----------|--------|
| [TASK-301](tasks/backlog/phase-3-intelligence/TASK-301.md) | Fear & Greed Index Integration | High | ✅ Complete |
| [TASK-302](tasks/backlog/phase-3-intelligence/TASK-302.md) | BTC Correlation Tracking | High | ✅ Complete |
| [TASK-303](tasks/backlog/phase-3-intelligence/TASK-303.md) | News Feed Integration | Medium | ✅ Complete |
| [TASK-304](tasks/backlog/phase-3-intelligence/TASK-304.md) | Social Sentiment Integration | Low | ✅ Complete |
| [TASK-305](tasks/backlog/phase-3-intelligence/TASK-305.md) | ContextManager & Strategist Integration | High | ✅ Complete |

**Milestone:** Sentiment data flowing to Strategist for context-aware decisions

### Phase 3B: Technical Indicators
| Task | Description | Priority | Status |
|------|-------------|----------|--------|
| [TASK-309](tasks/backlog/phase-3-intelligence/TASK-309.md) | Candle Data Fetcher | High | ✅ Complete |
| [TASK-310](tasks/backlog/phase-3-intelligence/TASK-310.md) | RSI (Relative Strength Index) | High | ✅ Complete |
| [TASK-311](tasks/backlog/phase-3-intelligence/TASK-311.md) | VWAP (Volume-Weighted Average Price) | Medium | ✅ Complete |
| [TASK-312](tasks/backlog/phase-3-intelligence/TASK-312.md) | ATR (Average True Range) | High | ✅ Complete |
| [TASK-313](tasks/backlog/phase-3-intelligence/TASK-313.md) | Funding Rates | Medium | ✅ Complete |
| [TASK-314](tasks/backlog/phase-3-intelligence/TASK-314.md) | Support/Resistance Levels | Medium | ✅ Complete |
| [TASK-315](tasks/backlog/phase-3-intelligence/TASK-315.md) | Volume Profile | Low | ✅ Complete |
| [TASK-316](tasks/backlog/phase-3-intelligence/TASK-316.md) | Order Book Depth | Low | ✅ Complete |
| [TASK-317](tasks/backlog/phase-3-intelligence/TASK-317.md) | TechnicalManager & Strategist Integration | High | ✅ Complete |

**Milestone:** Technical analysis providing trade setup quality scoring

---

## Architecture

### New Directory Structure
```
src/
  sentiment/
    __init__.py
    fear_greed.py           # TASK-301
    btc_correlation.py      # TASK-302
    news_feed.py            # TASK-303
    social_sentiment.py     # TASK-304
    context_manager.py      # TASK-305
  technical/
    __init__.py
    candle_fetcher.py       # TASK-309
    rsi.py                  # TASK-310
    vwap.py                 # TASK-311
    atr.py                  # TASK-312
    funding.py              # TASK-313
    support_resistance.py   # TASK-314
    volume_profile.py       # TASK-315
    orderbook.py            # TASK-316
    manager.py              # TASK-317
```

### Data Flow
```
External APIs ──► Sentiment Layer ──► ContextManager ──┐
                                                       ├──► Strategist
Bybit API ──────► Technical Layer ──► TechnicalManager ┘
```

---

## Data Sources

| Data Type | Source | Cost | Priority |
|-----------|--------|------|----------|
| Fear & Greed | Alternative.me | Free | High |
| BTC Correlation | Internal (MarketFeed) | Free | High |
| News | CryptoPanic | Free (limited) | Medium |
| Social | LunarCrush | Free (limited) | Low |
| Candles/OHLCV | Bybit | Free | High |
| Funding Rates | Bybit | Free | Medium |
| Order Book | Bybit | Free | Low |

---

## Success Criteria

The intelligence layer is working when:

1. Trade decisions incorporate market-wide context
2. Bot avoids trades during obvious market-wide moves
3. Technical indicators provide trade setup quality scoring
4. Context and technicals are recorded with each trade
5. Win rate improves compared to Phase 2 baseline
6. Fewer "learned the hard way" losses

---

## Dependencies

- Phase 2.1 ✓ (Speed Infrastructure)
- Phase 2.2 ✓ (Strategist Integration)
- Phase 2.3 ✓ (Knowledge Brain)
- Phase 2.4 ✓ (Reflection Engine)
- Phase 2.5 ✓ (Closed Loop)
- Phase 2.6 ✓ (Validation - 7 day run)

---

*Last Updated: February 4, 2026*
