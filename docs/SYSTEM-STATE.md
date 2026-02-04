# System State - Ground Truth

**Last Updated:** 2026-02-03
**Updated By:** Claude Code

---

## Production Configuration

| Setting | Value |
|---------|-------|
| Entry Point | `src/main.py` (Phase 2 TradingSystem) |
| Process Manager | Supervisor |
| Config File | `config/supervisor.conf` |
| Dashboard | Built into main.py (FastAPI), port 8080 |
| Market Data | Bybit WebSocket (real-time) |
| LLM | Ollama qwen2.5:14b |
| Database | SQLite at data/trading_bot.db |

---

## Active Components

| Component | File | Purpose |
|-----------|------|---------|
| MarketFeed | market_feed.py | WebSocket price data |
| Sniper | sniper.py | Sub-ms trade execution |
| Strategist | strategist.py | LLM condition generation |
| Journal | journal.py | Trade recording |
| KnowledgeBrain | knowledge.py | Learned knowledge storage |
| CoinScorer | coin_scorer.py | Per-coin performance |
| PatternLibrary | pattern_library.py | Trading patterns |
| QuickUpdate | quick_update.py | Instant post-trade learning |
| ReflectionEngine | reflection.py | Hourly LLM analysis |
| AdaptationEngine | adaptation.py | Automatic behavior changes |
| ProfitabilityTracker | profitability.py | P&L tracking |
| EffectivenessMonitor | effectiveness.py | Adaptation validation |
| DashboardServer | dashboard_v2.py | Web UI |
| FearGreedFetcher | sentiment/fear_greed.py | Market sentiment index |
| CandleFetcher | technical/candle_fetcher.py | OHLCV candle data |
| RSICalculator | technical/rsi.py | Overbought/oversold detection |
| ATRCalculator | technical/atr.py | Volatility and position sizing |
| FundingRateFetcher | technical/funding.py | Crowded position detection |

---

## Deprecated Components (DO NOT USE)

| File | Replaced By | Remove After |
|------|-------------|--------------|
| main_legacy.py | main.py | 2026-03-05 |
| dashboard.py | dashboard_v2.py | 2026-03-05 |
| trading_engine.py | sniper.py | 2026-03-05 |
| learning_system.py | knowledge.py + reflection.py | 2026-03-05 |
| market_data.py | market_feed.py | 2026-03-05 |
| risk_manager.py | sniper.py | 2026-03-05 |

---

## Coin Universe

**Count:** 20 coins across 3 tiers
**Source:** config/settings.py TRADEABLE_COINS
**Exchange:** Bybit (default)

---

## LLM Input Data

The Strategist sends to qwen2.5:14b:
- Coin prices (real-time from WebSocket)
- 24h price change
- Coin performance (win rate, P&L, trend)
- Good/bad coin lists
- Active regime rules
- Winning patterns with confidence
- Account state

**NOT INCLUDED (Phase 3):** RSI, VWAP, ATR, Fear & Greed, funding rates, order book

---

## Learning Loop

```
Trade Executes → Sniper
       ↓
QuickUpdate (instant coin score update)
       ↓
Journal (full context logged)
       ↓
ReflectionEngine (hourly analysis)
       ↓
AdaptationEngine (behavior changes)
       ↓
KnowledgeBrain (updated)
       ↓
Strategist (reads knowledge for next decision)
```

---

## Phase 3: Intelligence Layer (Preview)

**Status:** In Progress (5/13 tasks complete)
**Prerequisite:** Phase 2 complete with proven learning loop

### Phase 3A: Sentiment Layer
| Component | File | Purpose | Status |
|-----------|------|---------|--------|
| FearGreedFetcher | sentiment/fear_greed.py | Alternative.me Fear & Greed Index | ✅ Complete |
| BTCCorrelationTracker | sentiment/btc_correlation.py | Detect BTC-driven moves | Backlog |
| NewsFeedFetcher | sentiment/news_feed.py | CryptoPanic news integration | Backlog |
| SocialSentimentFetcher | sentiment/social_sentiment.py | LunarCrush social metrics | Backlog |
| ContextManager | sentiment/context_manager.py | Aggregates all sentiment sources | Backlog |

### Phase 3B: Technical Indicators
| Component | File | Purpose | Status |
|-----------|------|---------|--------|
| CandleFetcher | technical/candle_fetcher.py | OHLCV data from Bybit | ✅ Complete |
| RSICalculator | technical/rsi.py | Overbought/oversold detection | ✅ Complete |
| VWAPCalculator | technical/vwap.py | Fair value and deviation | Backlog |
| ATRCalculator | technical/atr.py | Volatility and dynamic stops | ✅ Complete |
| FundingRateFetcher | technical/funding.py | Perpetual funding rates | ✅ Complete |
| SRLevelDetector | technical/support_resistance.py | Auto S/R detection | Backlog |
| VolumeProfileCalculator | technical/volume_profile.py | Volume distribution | Backlog |
| OrderBookAnalyzer | technical/orderbook.py | Bid/ask imbalance | Backlog |
| TechnicalManager | technical/manager.py | Aggregates all indicators | Backlog |

### LLM Input (Phase 3 Additions)
When Phase 3 is complete, Strategist will receive:
- Fear & Greed Index value and classification
- BTC correlation status for each coin
- Breaking news affecting coins
- RSI, VWAP deviation, ATR volatility
- Funding rates and market positioning
- Support/resistance levels and distances
- Trade setup quality score

---

## Update Rules

This file MUST be updated when:
- Entry point changes
- Component added/removed
- LLM input changes
- Architecture changes

Failure to update is a blocking issue.
