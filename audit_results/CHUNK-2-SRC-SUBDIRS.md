# CHUNK 2: src/ Subdirectories Audit

**Date:** 2026-02-04
**Auditor:** Claude Code
**Files Audited:** 26 of 26

---

## Summary

| Metric | Value |
|--------|-------|
| Total Files | 26 |
| Files Audited | 26 |
| Critical Issues | 2 |
| High Issues | 1 |
| Medium Issues | 2 |
| Low Issues | 0 |

---

## Directory Overview

| Directory | Files | Status |
|-----------|-------|--------|
| src/models/ | 6 | ✅ OK |
| src/analysis/ | 4 | ✅ OK |
| src/sentiment/ | 6 | ⚠️ NOT INTEGRATED |
| src/technical/ | 10 | ⚠️ NOT INTEGRATED + SYMBOL_MAP MISMATCH |

---

## src/models/ (6 files)

### 1. src/models/__init__.py

**Lines:** 12
**Read completely:** YES

**Imports:**
- `src.models.trade_condition.TradeCondition`
- `src.models.knowledge.CoinScore`
- `src.models.knowledge.TradingPattern`
- `src.models.knowledge.RegimeRule`

**Exports:** TradeCondition, CoinScore, TradingPattern, RegimeRule

**Issues:** None

---

### 2. src/models/adaptation.py

**Lines:** 107
**Read completely:** YES

**Imports:**
- `dataclasses.dataclass, field`
- `datetime.datetime`
- `enum.Enum`
- `typing.Any, Dict, Optional`

**Classes:**
- `AdaptationAction(Enum)` - Adaptation types (BLACKLIST_COIN, FAVOR_COIN, REDUCE_COIN, etc.)
- `AdaptationRecord` - Record of an applied adaptation with pre/post metrics

**Methods:**
- `AdaptationRecord.to_dict()` → Dict[str, Any]
- `AdaptationRecord.from_dict(d)` → AdaptationRecord
- `AdaptationRecord.__str__()` → str

**Issues:** None

---

### 3. src/models/knowledge.py

**Lines:** 214
**Read completely:** YES

**Imports:**
- `dataclasses.dataclass, field, asdict`
- `datetime.datetime`
- `typing.Optional, Dict, Any`
- `json`

**Classes:**
- `CoinScore` - Performance metrics for a coin (trades, wins, losses, P&L, win_rate, trend)
- `TradingPattern` - Reusable trading pattern with effectiveness tracking
- `RegimeRule` - Rule about when to trade or sit out

**Key Methods:**
- `CoinScore.recalculate_stats()` - Updates win_rate and avg_pnl
- `TradingPattern.win_rate` (property) - Calculated from times_used
- `RegimeRule.check_condition(market_state)` - Evaluates rule against market state

**Issues:** None

---

### 4. src/models/quick_update.py

**Lines:** 107
**Read completely:** YES

**Imports:**
- `dataclasses.dataclass, field`
- `typing.Optional`

**Classes:**
- `TradeResult` - Outcome of a completed trade, passed to QuickUpdate
- `QuickUpdateResult` - Result of a quick update, including adaptations triggered

**Key Properties:**
- `TradeResult.duration_seconds` - Calculated from timestamps
- `TradeResult.return_pct` - Calculated return percentage
- `QuickUpdateResult.__str__()` - Human-readable summary

**Issues:** None

---

### 5. src/models/reflection.py

**Lines:** 287
**Read completely:** YES

**Imports:**
- `dataclasses.dataclass, field`
- `datetime.datetime`
- `typing.Any, Dict, List, Optional, TYPE_CHECKING`
- `src.models.adaptation.AdaptationRecord` (TYPE_CHECKING)

**Classes:**
- `CoinAnalysis` - Performance analysis for a single coin
- `PatternAnalysis` - Performance analysis for a pattern
- `TimeAnalysis` - Performance by time of day/day of week
- `RegimeAnalysis` - Performance by market regime (BTC up/down/sideways)
- `ExitAnalysis` - Exit performance analysis
- `Insight` - A single insight from reflection
- `ReflectionResult` - Complete result of a reflection cycle

**Issues:** None

---

### 6. src/models/trade_condition.py

**Lines:** 175
**Read completely:** YES

**Imports:**
- `dataclasses.dataclass, field`
- `datetime.datetime, timedelta`
- `typing.Literal, Optional`
- `uuid`

**Classes:**
- `TradeCondition` - A specific condition for Sniper to watch and execute

**Key Methods:**
- `is_expired()` - Check if condition has expired
- `is_triggered(current_price)` - Check if trigger condition is met
- `calculate_stop_loss_price()` - Calculate stop-loss based on direction
- `calculate_take_profit_price()` - Calculate take-profit based on direction
- `to_dict()` / `from_dict()` - Serialization

**Issues:** None

---

## src/analysis/ (4 files)

### 7. src/analysis/__init__.py

**Lines:** 52
**Read completely:** YES

**Imports:**
- `src.analysis.metrics.*`
- `src.analysis.performance.*`
- `src.analysis.learning.*`

**Exports:** TradingMetrics, calculate_metrics, calculate_sharpe_ratio, calculate_max_drawdown, calculate_profit_factor, analyze_by_hour, analyze_by_coin, analyze_by_pattern, compare_periods, build_equity_curve, analyze_coin_score_accuracy, analyze_adaptation_effectiveness, analyze_pattern_confidence_accuracy, analyze_knowledge_growth

**Issues:** None

---

### 8. src/analysis/learning.py

**Lines:** 525
**Read completely:** YES

**Imports:**
- `collections.defaultdict`
- `datetime.datetime, timedelta`
- `typing.Dict, List, Optional, Any`
- `src.database.Database`

**Functions:**
- `analyze_coin_score_accuracy(db, min_trades)` - Analyze coin score prediction accuracy
- `analyze_adaptation_effectiveness(db)` - Analyze how effective adaptations were
- `analyze_pattern_confidence_accuracy(db, min_usage)` - Analyze pattern confidence accuracy
- `analyze_knowledge_growth(db, days)` - Analyze knowledge growth over time
- `calculate_learning_score(...)` - Calculate overall learning effectiveness score

**Issues:** None

---

### 9. src/analysis/metrics.py

**Lines:** 362
**Read completely:** YES

**Imports:**
- `math`
- `dataclasses.dataclass, field`
- `datetime.datetime`
- `typing.List, Tuple, Optional`

**Classes:**
- `TradingMetrics` - Complete trading performance metrics

**Functions:**
- `calculate_metrics(trades, starting_balance)` → TradingMetrics
- `calculate_profit_factor(gross_profit, gross_loss)` → float
- `calculate_sharpe_ratio(returns, risk_free_rate, annualize, periods_per_year)` → float
- `calculate_max_drawdown(equity_curve)` → Tuple[float, float]
- `build_equity_curve(pnl_values, starting_balance)` → List[float]
- `calculate_daily_returns(trades)` → List[float]

**Issues:** None

---

### 10. src/analysis/performance.py

**Lines:** 341
**Read completely:** YES

**Imports:**
- `collections.defaultdict`
- `datetime.datetime, timedelta`
- `typing.Dict, List, Optional, Tuple`
- `src.analysis.metrics.TradingMetrics, calculate_metrics, build_equity_curve`

**Functions:**
- `analyze_by_hour(trades)` → Dict[int, TradingMetrics]
- `analyze_by_coin(trades)` → Dict[str, TradingMetrics]
- `analyze_by_pattern(trades)` → Dict[str, TradingMetrics]
- `analyze_by_day(trades)` → Dict[str, TradingMetrics]
- `analyze_by_session(trades)` → Dict[str, TradingMetrics]
- `compare_periods(trades, split_point)` → Dict[str, dict]
- `get_best_worst_hours(hour_metrics, min_trades)` → dict
- `get_best_worst_coins(coin_metrics, min_trades)` → dict
- `calculate_consistency(trades, period_days)` → dict

**Issues:** None

---

## src/sentiment/ (6 files) - PHASE 3

### 11. src/sentiment/__init__.py

**Lines:** 22
**Read completely:** YES

**Exports:** FearGreedFetcher, FearGreedData, BTCCorrelationTracker, BTCCorrelation, NewsFeedFetcher, NewsItem, NewsFeed, SocialSentimentFetcher, SocialMetrics, ContextManager, MarketContext, CoinContext

**Integration Status:**
- Imported in main.py: ❌ NO
- Imported in strategist.py: ❌ NO
- Used in production: ❌ NO

**Issues:** CRIT-001 - Not integrated

---

### 12. src/sentiment/btc_correlation.py

**Lines:** 252
**Read completely:** YES

**Imports:**
- `logging`
- `dataclasses.dataclass`
- `datetime.datetime`
- `typing.Optional, List`
- `statistics`
- `src.technical.candle_fetcher.CandleFetcher`

**Classes:**
- `BTCCorrelation` - BTC correlation data for a coin
- `BTCCorrelationTracker` - Tracks correlation between altcoins and BTC

**Key Methods:**
- `get_correlation(coin, timeframe)` → BTCCorrelation
- `is_btc_driven_move(coin, btc_threshold, correlation_threshold)` → tuple[bool, str]
- `get_all_correlations(coins)` → dict[str, BTCCorrelation]
- `_calculate_correlation(btc_closes, coin_closes)` → float (Pearson)

**Integration Status:**
- Imported in main.py: ❌ NO
- Used in production: ❌ NO

**Issues:** None (module is correctly implemented)

---

### 13. src/sentiment/context_manager.py

**Lines:** 320
**Read completely:** YES

**Imports:**
- `logging`
- `dataclasses.dataclass, field`
- `datetime.datetime, timezone`
- `typing.List, Optional, Dict, Any`
- `.fear_greed.FearGreedFetcher, FearGreedData`
- `.btc_correlation.BTCCorrelationTracker, BTCCorrelation`
- `.news_feed.NewsFeedFetcher, NewsItem, NewsFeed`
- `.social_sentiment.SocialSentimentFetcher, SocialMetrics`

**Classes:**
- `MarketContext` - Overall market context from sentiment sources
- `CoinContext` - Coin-specific context from sentiment sources
- `ContextManager` - Aggregates all sentiment sources for Strategist

**Key Methods:**
- `ContextManager.get_context()` → MarketContext
- `ContextManager.get_coin_context(coin)` → CoinContext
- `ContextManager.should_avoid_trading(coin)` → tuple[bool, str]
- `MarketContext.to_prompt()` → str (formatted for LLM)
- `CoinContext.to_prompt()` → str (formatted for LLM)

**Integration with Strategist:**
To integrate, Strategist would need:
1. Import: `from src.sentiment.context_manager import ContextManager`
2. Initialize in `__init__`: `self.context_manager = context_manager or ContextManager()`
3. In `_build_prompt()`, add: `context.get_context().to_prompt()`

**Integration Status:**
- Imported in main.py: ❌ NO
- Imported in strategist.py: ❌ NO
- Used in production: ❌ NO

**Issues:** CRIT-001 - Ready for integration but not connected

---

### 14. src/sentiment/fear_greed.py

**Lines:** 153
**Read completely:** YES

**Imports:**
- `logging`
- `dataclasses.dataclass`
- `datetime.datetime, timedelta`
- `typing.Optional, List`
- `requests`

**Classes:**
- `FearGreedData` - Fear & Greed Index data point (0-100 scale)
- `FearGreedFetcher` - Fetches from Alternative.me API

**Key Methods:**
- `get_current()` → Optional[FearGreedData]
- `get_historical(days)` → List[FearGreedData]

**API:** `https://api.alternative.me/fng/`
**Cache TTL:** 60 minutes (index updates daily)

**Issues:** None

---

### 15. src/sentiment/news_feed.py

**Lines:** 271
**Read completely:** YES

**Imports:**
- `logging`
- `time`
- `dataclasses.dataclass, field`
- `datetime.datetime, timezone`
- `typing.List, Optional, Dict, Any`
- `requests`

**Classes:**
- `NewsItem` - A single news item with sentiment
- `NewsFeed` - Collection of news items
- `NewsFeedFetcher` - Fetches from CryptoPanic API

**Key Methods:**
- `get_news(filter_type, currencies)` → NewsFeed
- `get_news_for_coin(coin)` → List[NewsItem]
- `get_breaking_news()` → List[NewsItem]

**API:** `https://cryptopanic.com/api/v1/posts/`
**Cache TTL:** 5 minutes
**Rate Limit:** 1 request per 12 seconds

**Issues:** None

---

### 16. src/sentiment/social_sentiment.py

**Lines:** 247
**Read completely:** YES

**Imports:**
- `logging`
- `time`
- `dataclasses.dataclass, field`
- `datetime.datetime, timezone`
- `typing.Optional, Dict, Any, List`
- `requests`

**Classes:**
- `SocialMetrics` - Social media metrics for a coin
- `SocialSentimentFetcher` - Fetches from LunarCrush API

**Key Methods:**
- `get_metrics(coin)` → SocialMetrics
- `get_all_metrics(coins)` → Dict[str, SocialMetrics]
- `detect_social_spike(coin)` → tuple[bool, Optional[float]]
- `get_trending_coins(coins)` → List[str]

**API:** `https://lunarcrush.com/api3/coins`
**Cache TTL:** 15 minutes

**Issues:** None

---

## src/technical/ (10 files) - PHASE 3

### 17. src/technical/__init__.py

**Lines:** 35
**Read completely:** YES

**Exports:** CandleFetcher, Candle, CandleData, RSICalculator, RSIData, ATRCalculator, ATRData, FundingRateFetcher, FundingData, VWAPCalculator, VWAPData, SRLevelDetector, PriceLevel, SRLevels, VolumeProfileCalculator, VolumeProfile, OrderBookAnalyzer, OrderBookDepth, PriceWall, TechnicalManager, TechnicalSnapshot

**Integration Status:**
- Imported in main.py: ❌ NO
- Imported in strategist.py: ❌ NO
- Used in production: ❌ NO

**Issues:** CRIT-001 - Not integrated

---

### 18. src/technical/atr.py

**Lines:** 248
**Read completely:** YES

**Imports:**
- `logging`
- `dataclasses.dataclass`
- `datetime.datetime`
- `typing.List, Optional, Tuple`
- `.candle_fetcher.CandleFetcher, Candle`

**Classes:**
- `ATRData` - ATR calculation result
- `ATRCalculator` - Calculates ATR using Wilder's smoothing

**Key Methods:**
- `calculate(coin, timeframe, period)` → ATRData
- `calculate_from_candles(candles, period)` → float
- `get_position_size_modifier(coin, target_risk_pct)` → float
- `get_dynamic_stops(coin, direction, entry_price, sl_mult, tp_mult)` → Tuple[float, float]

**Properties:**
- `ATRData.volatility_level` - "extreme", "high", "moderate", "low"
- `ATRData.suggested_stop_loss(multiplier)` - Stop-loss distance
- `ATRData.suggested_stop_price(entry, direction, mult)` - Absolute stop price

**Issues:** None

---

### 19. src/technical/candle_fetcher.py

**Lines:** 236
**Read completely:** YES

**Imports:**
- `logging`
- `dataclasses.dataclass, field`
- `datetime.datetime, timedelta`
- `typing.Optional, List, Dict`
- `requests`

**Classes:**
- `Candle` - Single OHLCV candle
- `CandleData` - Collection of candles
- `CandleFetcher` - Fetches from Bybit API

**API:** `https://api.bybit.com/v5/market/kline`
**Cache:** 60 seconds

**SYMBOL_MAP:**
```python
SYMBOL_MAP = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "XRP": "XRPUSDT",
    "BNB": "BNBUSDT",
    "ADA": "ADAUSDT",
    "DOGE": "DOGEUSDT",
    "AVAX": "AVAXUSDT",
    "DOT": "DOTUSDT",
    "LINK": "LINKUSDT",
    "MATIC": "MATICUSDT",
    "UNI": "UNIUSDT",
    "ATOM": "ATOMUSDT",
    "LTC": "LTCUSDT",
    "ETC": "ETCUSDT",
    "PEPE": "PEPEUSDT",      # ❌ NOT IN settings.py
    "FLOKI": "FLOKIUSDT",    # ❌ NOT IN settings.py
    "BONK": "BONKUSDT",      # ❌ NOT IN settings.py
    "WIF": "WIFUSDT",        # ❌ NOT IN settings.py
    "SHIB": "SHIBUSDT",      # ❌ NOT IN settings.py
}
# MISSING: NEAR, APT, ARB, OP, INJ (Tier 3 coins from settings.py)
```

**Issues:** CRIT-002 - SYMBOL_MAP mismatch with settings.py

---

### 20. src/technical/funding.py

**Lines:** 263
**Read completely:** YES

**Imports:**
- `logging`
- `dataclasses.dataclass`
- `datetime.datetime, timedelta`
- `typing.Optional, List, Dict`
- `requests`

**Classes:**
- `FundingData` - Funding rate data for a coin
- `FundingRateFetcher` - Fetches from Bybit API

**API:**
- `https://api.bybit.com/v5/market/funding/history`
- `https://api.bybit.com/v5/market/tickers`
**Cache:** 5 minutes

**SYMBOL_MAP:**
```python
SYMBOL_MAP = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "XRP": "XRPUSDT",
    "BNB": "BNBUSDT",
    "ADA": "ADAUSDT",
    "DOGE": "DOGEUSDT",
    "AVAX": "AVAXUSDT",
    "DOT": "DOTUSDT",
    "LINK": "LINKUSDT",
    "MATIC": "MATICUSDT",
    "UNI": "UNIUSDT",
    "ATOM": "ATOMUSDT",
    "LTC": "LTCUSDT",
    "ETC": "ETCUSDT",
    "PEPE": "PEPEUSDT",      # ❌ NOT IN settings.py
    "FLOKI": "FLOKIUSDT",    # ❌ NOT IN settings.py
    "BONK": "BONKUSDT",      # ❌ NOT IN settings.py
    "WIF": "WIFUSDT",        # ❌ NOT IN settings.py
    "SHIB": "SHIBUSDT",      # ❌ NOT IN settings.py
}
# MISSING: NEAR, APT, ARB, OP, INJ (Tier 3 coins from settings.py)
```

**Key Methods:**
- `get_current(coin)` → FundingData
- `get_historical(coin, limit)` → List[dict]
- `get_all_extreme()` → Dict[str, FundingData]
- `should_avoid_direction(coin, direction)` → tuple[bool, str]

**Properties:**
- `FundingData.is_extreme_long` - >0.05% per 8h
- `FundingData.is_extreme_short` - <-0.05% per 8h
- `FundingData.bias` - "crowded_long", "crowded_short", "neutral"
- `FundingData.contrarian_signal` - "LONG", "SHORT", or None

**Issues:** CRIT-002 - SYMBOL_MAP mismatch with settings.py

---

### 21. src/technical/manager.py

**Lines:** 471
**Read completely:** YES

**Imports:**
- `logging`
- `dataclasses.dataclass, field`
- `datetime.datetime`
- `typing.List, Optional, Dict, Tuple`
- `.candle_fetcher.CandleFetcher`
- `.rsi.RSICalculator, RSIData`
- `.vwap.VWAPCalculator, VWAPData`
- `.atr.ATRCalculator, ATRData`
- `.funding.FundingRateFetcher, FundingData`
- `.support_resistance.SRLevelDetector, SRLevels`
- `.volume_profile.VolumeProfileCalculator, VolumeProfile`
- `.orderbook.OrderBookAnalyzer, OrderBookDepth`

**Classes:**
- `TechnicalSnapshot` - Complete technical analysis snapshot
- `TechnicalManager` - Aggregates all technical indicators

**Key Methods:**
- `get_technical_snapshot(coin)` → TechnicalSnapshot
- `get_trade_setup_quality(coin, direction)` → Tuple[float, str]
- `get_dynamic_stops(coin, direction, entry_price)` → Tuple[float, float]
- `get_position_size(coin, base_size, direction)` → float
- `TechnicalSnapshot.to_prompt()` → str (formatted for LLM)
- `TechnicalSnapshot.get_confluence_signals(direction)` → List[str]

**Integration with Strategist:**
To integrate, Strategist would need:
1. Import: `from src.technical.manager import TechnicalManager`
2. Initialize in `__init__`: `self.technical_manager = technical_manager or TechnicalManager(CandleFetcher())`
3. In `_build_prompt()`, add: `self.technical_manager.get_technical_snapshot(coin).to_prompt()`

**Integration Status:**
- Imported in main.py: ❌ NO
- Imported in strategist.py: ❌ NO
- Used in production: ❌ NO

**Issues:** CRIT-001 - Ready for integration but not connected

---

### 22. src/technical/orderbook.py

**Lines:** 295
**Read completely:** YES

**Imports:**
- `logging`
- `time`
- `dataclasses.dataclass, field`
- `datetime.datetime, timezone`
- `typing.List, Optional, Dict, Any`
- `requests`

**Classes:**
- `PriceWall` - A significant order at a price level
- `OrderBookDepth` - Order book analysis result
- `OrderBookAnalyzer` - Analyzes order book depth

**API:** `https://api.bybit.com/v5/market/orderbook`
**Cache:** 5 seconds

**Key Methods:**
- `analyze(coin, depth, use_cache)` → OrderBookDepth
- `calculate_imbalance(bid_volume, ask_volume)` → float
- `detect_walls(orders, side, mid_price)` → List[PriceWall]

**Issues:** None

---

### 23. src/technical/rsi.py

**Lines:** 183
**Read completely:** YES

**Imports:**
- `logging`
- `dataclasses.dataclass`
- `datetime.datetime`
- `typing.List, Optional`
- `.candle_fetcher.CandleFetcher`

**Classes:**
- `RSIData` - RSI calculation result
- `RSICalculator` - Calculates RSI using Wilder's smoothing

**Key Methods:**
- `calculate(coin, timeframe, period)` → RSIData
- `calculate_from_closes(closes, period)` → float
- `get_multi_timeframe(coin, timeframes)` → dict[str, RSIData]

**Properties:**
- `RSIData.is_overbought` - RSI > 70
- `RSIData.is_oversold` - RSI < 30
- `RSIData.condition` - "overbought", "oversold", "neutral"

**Issues:** None

---

### 24. src/technical/support_resistance.py

**Lines:** 283
**Read completely:** YES

**Imports:**
- `logging`
- `dataclasses.dataclass, field`
- `datetime.datetime`
- `typing.List, Optional`
- `collections.defaultdict`
- `.candle_fetcher.CandleFetcher, Candle`

**Classes:**
- `PriceLevel` - A support or resistance price level
- `SRLevels` - Support and resistance levels for a coin
- `SRLevelDetector` - Detects S/R levels from price history

**Key Methods:**
- `detect(coin, timeframe, limit)` → SRLevels
- `find_swing_points(candles)` → List[tuple[float, str]]
- `cluster_levels(points, level_type)` → List[PriceLevel]

**Properties:**
- `SRLevels.support_distance_pct` - Distance to nearest support
- `SRLevels.resistance_distance_pct` - Distance to nearest resistance
- `SRLevels.in_support_zone` - Is price in support zone
- `SRLevels.in_resistance_zone` - Is price in resistance zone

**Issues:** None

---

### 25. src/technical/volume_profile.py

**Lines:** 344
**Read completely:** YES

**Imports:**
- `logging`
- `dataclasses.dataclass, field`
- `datetime.datetime`
- `typing.List, Optional`
- `collections.defaultdict`
- `.candle_fetcher.CandleFetcher, Candle`

**Classes:**
- `VolumeLevel` - A price level with associated volume
- `VolumeProfile` - Volume profile analysis result
- `VolumeProfileCalculator` - Calculates Volume Profile

**Key Methods:**
- `calculate(coin, timeframe, limit)` → VolumeProfile
- `calculate_from_candles(candles, coin)` → VolumeProfile

**Properties:**
- `VolumeProfile.poc` - Point of Control (highest volume price)
- `VolumeProfile.value_area_high/low` - Value Area (70% of volume)
- `VolumeProfile.position_vs_poc` - "above_poc", "below_poc", "at_poc"
- `VolumeProfile.is_in_value_area` - Is current price in value area

**Issues:** None

---

### 26. src/technical/vwap.py

**Lines:** 214
**Read completely:** YES

**Imports:**
- `logging`
- `dataclasses.dataclass`
- `datetime.datetime, timezone`
- `typing.List, Optional`
- `.candle_fetcher.CandleFetcher, Candle`

**Classes:**
- `VWAPData` - VWAP calculation result
- `VWAPCalculator` - Calculates VWAP

**Key Methods:**
- `calculate(coin, timeframe, use_daily_reset)` → VWAPData
- `calculate_from_candles(candles)` → float
- `get_bands(coin, std_multiplier)` → tuple[float, float, float]

**Properties:**
- `VWAPData.is_above_vwap` / `is_below_vwap`
- `VWAPData.position` - "extended_above", "extended_below", "above", "below"
- `VWAPData.mean_reversion_signal` - "LONG", "SHORT", or None

**Issues:** None

---

## Critical Issues

### CRIT-001: Phase 3 Modules Not Integrated (CONFIRMED)

**Severity:** CRITICAL
**Category:** INTEGRATION

**Files Affected:**
- `src/sentiment/context_manager.py` - NOT imported in main.py or strategist.py
- `src/technical/manager.py` - NOT imported in main.py or strategist.py

**Description:**
All Phase 3 sentiment and technical modules are fully implemented with:
- Proper dataclasses for all data types
- `to_prompt()` methods designed for LLM integration
- Error handling and graceful degradation
- Caching for API calls

But they are NOT connected to the production code.

**Impact:**
- Bot trades without RSI, VWAP, ATR, funding rates
- Bot trades without Fear & Greed, news sentiment, social metrics
- Bot trades without support/resistance levels, volume profile, orderbook analysis
- All Phase 3 development effort is wasted until integrated

**Fix:**
See CHUNK-1 audit for detailed integration steps.

---

### CRIT-002: SYMBOL_MAP Mismatch

**Severity:** CRITICAL
**Category:** CONFIG

**Files Affected:**
- `src/technical/funding.py` (lines 73-94)
- `src/technical/candle_fetcher.py` (lines 101-122)

**Description:**
SYMBOL_MAP in technical modules does not match settings.py TRADEABLE_COINS.

**Comparison:**

| Coin | settings.py | funding.py | candle_fetcher.py |
|------|-------------|------------|-------------------|
| **Tier 1** |
| BTC | ✅ | ✅ | ✅ |
| ETH | ✅ | ✅ | ✅ |
| SOL | ✅ | ✅ | ✅ |
| BNB | ✅ | ✅ | ✅ |
| XRP | ✅ | ✅ | ✅ |
| **Tier 2** |
| DOGE | ✅ | ✅ | ✅ |
| ADA | ✅ | ✅ | ✅ |
| AVAX | ✅ | ✅ | ✅ |
| LINK | ✅ | ✅ | ✅ |
| DOT | ✅ | ✅ | ✅ |
| MATIC | ✅ | ✅ | ✅ |
| UNI | ✅ | ✅ | ✅ |
| ATOM | ✅ | ✅ | ✅ |
| LTC | ✅ | ✅ | ✅ |
| ETC | ✅ | ✅ | ✅ |
| **Tier 3** |
| NEAR | ✅ | ❌ MISSING | ❌ MISSING |
| APT | ✅ | ❌ MISSING | ❌ MISSING |
| ARB | ✅ | ❌ MISSING | ❌ MISSING |
| OP | ✅ | ❌ MISSING | ❌ MISSING |
| INJ | ✅ | ❌ MISSING | ❌ MISSING |
| **Meme Coins** |
| PEPE | ❌ | ✅ EXTRA | ✅ EXTRA |
| FLOKI | ❌ | ✅ EXTRA | ✅ EXTRA |
| BONK | ❌ | ✅ EXTRA | ✅ EXTRA |
| WIF | ❌ | ✅ EXTRA | ✅ EXTRA |
| SHIB | ❌ | ✅ EXTRA | ✅ EXTRA |

**Impact:**
- Technical indicators will fail for Tier 3 coins (NEAR, APT, ARB, OP, INJ)
- Funding rates unavailable for Tier 3 coins
- Meme coins (PEPE, FLOKI, etc.) have technical data but aren't tradeable

**Fix:**
Update SYMBOL_MAP in both files:
```python
SYMBOL_MAP = {
    # Tier 1
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT",
    "BNB": "BNBUSDT", "XRP": "XRPUSDT",
    # Tier 2
    "DOGE": "DOGEUSDT", "ADA": "ADAUSDT", "AVAX": "AVAXUSDT",
    "LINK": "LINKUSDT", "DOT": "DOTUSDT", "MATIC": "MATICUSDT",
    "UNI": "UNIUSDT", "ATOM": "ATOMUSDT", "LTC": "LTCUSDT", "ETC": "ETCUSDT",
    # Tier 3 - ADD THESE
    "NEAR": "NEARUSDT", "APT": "APTUSDT", "ARB": "ARBUSDT",
    "OP": "OPUSDT", "INJ": "INJUSDT",
}
# REMOVE: PEPE, FLOKI, BONK, WIF, SHIB
```

---

## High Issues

### HIGH-001: TechnicalManager._get_funding Method Bug

**File:** `src/technical/manager.py:440-446`
**Severity:** HIGH
**Category:** LOGIC

**Description:**
The `_get_funding` method calls `self.funding.get_funding_rate(coin)` but the actual method is `self.funding.get_current(coin)`.

```python
# Line 443 - INCORRECT
return self.funding.get_funding_rate(coin)

# Should be:
return self.funding.get_current(coin)
```

**Impact:**
When Phase 3 is integrated, funding rate data will fail to load with AttributeError.

**Fix:**
Change `get_funding_rate` to `get_current` on line 443.

---

## Medium Issues

### MED-001: Duplicate SYMBOL_MAP Definitions

**Files:** `funding.py`, `candle_fetcher.py`
**Severity:** MEDIUM
**Category:** STYLE

**Description:**
SYMBOL_MAP is defined twice in separate files with identical content. This violates DRY principle and makes updates error-prone.

**Fix:**
Move SYMBOL_MAP to a central location (e.g., `config/settings.py` or `src/technical/__init__.py`) and import from there.

---

### MED-002: Missing Error Handling in Fetchers

**Files:** Multiple in sentiment/technical
**Severity:** MEDIUM
**Category:** ERROR

**Description:**
Some API fetchers may not handle all error cases gracefully. The managers (ContextManager, TechnicalManager) handle errors well, but individual fetchers could be improved.

**Examples:**
- `btc_correlation.py` - No explicit timeout handling
- API key validation not explicit

**Fix:**
Add explicit timeout and error handling in each fetcher.

---

## CHUNK 2 SUMMARY

- Files in chunk: 26
- Files completed: 26
- Issues found: 5 (2 Critical, 1 High, 2 Medium)

### SYMBOL_MAP Status

**Coins in settings.py TRADEABLE_COINS (20):**
BTC, ETH, SOL, BNB, XRP, DOGE, ADA, AVAX, LINK, DOT, MATIC, UNI, ATOM, LTC, ETC, NEAR, APT, ARB, OP, INJ

**Coins in funding.py SYMBOL_MAP (20):**
BTC, ETH, SOL, XRP, BNB, ADA, DOGE, AVAX, DOT, LINK, MATIC, UNI, ATOM, LTC, ETC, PEPE, FLOKI, BONK, WIF, SHIB

**Coins in candle_fetcher.py SYMBOL_MAP (20):**
BTC, ETH, SOL, XRP, BNB, ADA, DOGE, AVAX, DOT, LINK, MATIC, UNI, ATOM, LTC, ETC, PEPE, FLOKI, BONK, WIF, SHIB

**Mismatches:**
- MISSING from SYMBOL_MAP: NEAR, APT, ARB, OP, INJ
- EXTRA in SYMBOL_MAP (not in settings): PEPE, FLOKI, BONK, WIF, SHIB

### Phase 3 Integration Status

| Module | Imported in main.py | Imported in strategist.py | Ready |
|--------|---------------------|---------------------------|-------|
| ContextManager | ❌ NO | ❌ NO | ✅ YES |
| TechnicalManager | ❌ NO | ❌ NO | ✅ YES* |
| FearGreedFetcher | ❌ NO | ❌ NO | ✅ YES |
| BTCCorrelationTracker | ❌ NO | ❌ NO | ✅ YES |
| NewsFeedFetcher | ❌ NO | ❌ NO | ✅ YES |
| SocialSentimentFetcher | ❌ NO | ❌ NO | ✅ YES |
| RSICalculator | ❌ NO | ❌ NO | ✅ YES |
| VWAPCalculator | ❌ NO | ❌ NO | ✅ YES |
| ATRCalculator | ❌ NO | ❌ NO | ✅ YES |
| FundingRateFetcher | ❌ NO | ❌ NO | ✅ YES |
| SRLevelDetector | ❌ NO | ❌ NO | ✅ YES |
| VolumeProfileCalculator | ❌ NO | ❌ NO | ✅ YES |
| OrderBookAnalyzer | ❌ NO | ❌ NO | ✅ YES |

*TechnicalManager has a minor bug (HIGH-001) that needs fixing before integration.

**Modules ready for integration:** 13
**ContextManager imported in production:** ❌ NO
**TechnicalManager imported in production:** ❌ NO

---

## Verification Checklist

- [x] All 26 files documented
- [x] SYMBOL_MAP fully documented
- [x] Phase 3 integration status clear
- [x] CHUNK-2-SRC-SUBDIRS.md created

---

*Audit completed: 2026-02-04*
*Auditor: Claude Code*
