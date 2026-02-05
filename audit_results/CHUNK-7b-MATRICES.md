# CHUNK 7b - Cross-Reference Matrices (Part 2)

## Matrix 4: Coin Symbol Matrix

### Full Comparison Table

| Coin | settings.py | coins.json | technical/funding.py | technical/candle_fetcher.py |
|------|-------------|------------|---------------------|----------------------------|
| ADA | YES | YES | YES | YES |
| APT | YES | YES | **NO** | **NO** |
| ARB | YES | YES | **NO** | **NO** |
| ATOM | YES | YES | YES | YES |
| AVAX | YES | YES | YES | YES |
| BNB | YES | YES | YES | YES |
| BONK | **NO** | **NO** | YES | YES |
| BTC | YES | YES | YES | YES |
| DOGE | YES | YES | YES | YES |
| DOT | YES | YES | YES | YES |
| ETC | YES | YES | YES | YES |
| ETH | YES | YES | YES | YES |
| FLOKI | **NO** | **NO** | YES | YES |
| INJ | YES | YES | **NO** | **NO** |
| LINK | YES | YES | YES | YES |
| LTC | YES | YES | YES | YES |
| MATIC | YES | YES | YES | YES |
| NEAR | YES | YES | **NO** | **NO** |
| OP | YES | YES | **NO** | **NO** |
| PEPE | **NO** | **NO** | YES | YES |
| SHIB | **NO** | **NO** | YES | YES |
| SOL | YES | YES | YES | YES |
| UNI | YES | YES | YES | YES |
| WIF | **NO** | **NO** | YES | YES |
| XRP | YES | YES | YES | YES |

### Mismatch Summary

**In config but NOT in technical SYMBOL_MAP (5 coins):**
- APT, ARB, INJ, NEAR, OP

**In technical SYMBOL_MAP but NOT in config (5 coins):**
- BONK, FLOKI, PEPE, SHIB, WIF

**Impact:** Technical indicators (funding rate, candles) cannot be fetched for APT, ARB, INJ, NEAR, OP. Meme coins in SYMBOL_MAP (BONK, FLOKI, PEPE, SHIB, WIF) are not tradeable per config.

---

## Matrix 5: Database Query Matrix

### Defined Tables (21)

```
open_trades, closed_trades, learnings, trading_rules, activity_log,
account_state, market_data, price_history, coin_cooldowns, monitoring_alerts,
trade_journal, active_conditions, coin_scores, trading_patterns, regime_rules,
coin_adaptations, reflections, adaptations, runtime_state, profit_snapshots,
equity_points
```

### Query Analysis (513 SQL statements found)

| Operation | Count | Files |
|-----------|-------|-------|
| SELECT | ~200 | Most files |
| INSERT | ~50 | database.py, journal.py, learning_system.py, etc. |
| UPDATE | ~40 | database.py, journal.py, trading_engine.py, etc. |
| DELETE | ~15 | database.py, risk_manager.py |
| CREATE TABLE | 21 | database.py, journal.py, volatility.py |

### Schema Mismatches Found

| File | Line | Issue |
|------|------|-------|
| src/analysis/learning.py | 377 | `SELECT COUNT(*) FROM insights` - **TABLE NOT DEFINED** |
| src/analysis/learning.py | 398 | `SELECT COUNT(*) FROM insights` - **TABLE NOT DEFINED** |

**Critical Issue:** The `insights` table is queried but never created. This will cause runtime errors in `analyze_knowledge_growth()`.

### Table Usage Matrix

| Table | Files Using |
|-------|-------------|
| trade_journal | journal.py (primary), database.py |
| coin_scores | database.py, knowledge.py, analysis/learning.py |
| trading_patterns | database.py, knowledge.py, analysis/learning.py |
| active_conditions | database.py, strategist.py |
| market_data | market_data.py, dashboard.py, main_legacy.py, volatility.py |
| open_trades | trading_engine.py, risk_manager.py, metrics.py |
| closed_trades | trading_engine.py, metrics.py, daily_summary.py |

---

## Matrix 6: Win Rate Thresholds

### Threshold Definitions

| Location | Constant | Value | Purpose |
|----------|----------|-------|---------|
| coin_scorer.py:42 | BLACKLIST_WIN_RATE | 0.30 | Below this + negative P&L = blacklist |
| coin_scorer.py:43 | REDUCED_WIN_RATE | 0.45 | Below this = reduced position size |
| coin_scorer.py:44 | FAVORED_WIN_RATE | 0.60 | Above this + positive P&L = favored |
| coin_scorer.py:45 | RECOVERY_WIN_RATE | 0.50 | Above this to recover from reduced |
| adaptation.py:30 | blacklist.max_win_rate | 0.30 | Threshold for auto-blacklist |
| adaptation.py:31 | favor.min_win_rate | 0.60 | Threshold for auto-favor |
| adaptation.py:366 | pattern deactivation | 0.35 | Below this = deactivate pattern |
| knowledge.py:157 | good trend threshold | 0.60 | Win rate for "improving" trend |
| knowledge.py:159 | bad trend threshold | 0.35 | Win rate for "declining" trend |
| knowledge.py:163 | get_good_coins default | 0.50 | Default min_win_rate parameter |
| knowledge.py:180 | get_bad_coins default | 0.35 | Default max_win_rate parameter |

### Consistency Analysis

| Threshold | coin_scorer | adaptation | knowledge | strategist | Status |
|-----------|-------------|------------|-----------|------------|--------|
| Blacklist | 0.30 | 0.30 | N/A | N/A | CONSISTENT |
| Reduced | 0.45 | N/A | N/A | 0.45 | CONSISTENT |
| Favored | 0.60 | 0.60 | 0.60 | 0.60 | CONSISTENT |
| Bad coin | N/A | N/A | 0.35 | N/A | ISOLATED |
| Pattern deactivation | N/A | 0.35 | N/A | N/A | UNIQUE |

**Status:** Thresholds are CONSISTENT across modules. No conflicts detected.

---

## Matrix 7: Phase 3 Integration Check

### Integration Status

| Component | main.py | strategist.py | Status |
|-----------|---------|---------------|--------|
| ContextManager | NOT IMPORTED | NOT IMPORTED | DISCONNECTED |
| TechnicalManager | NOT IMPORTED | NOT IMPORTED | DISCONNECTED |
| FearGreedFetcher | NOT IMPORTED | NOT IMPORTED | DISCONNECTED |
| NewsFeed | NOT IMPORTED | NOT IMPORTED | DISCONNECTED |
| SocialSentiment | NOT IMPORTED | NOT IMPORTED | DISCONNECTED |
| BTCCorrelation | NOT IMPORTED | NOT IMPORTED | DISCONNECTED |
| CandleFetcher | NOT IMPORTED | NOT IMPORTED | DISCONNECTED |
| RSICalculator | NOT IMPORTED | NOT IMPORTED | DISCONNECTED |
| VWAPCalculator | NOT IMPORTED | NOT IMPORTED | DISCONNECTED |
| ATRCalculator | NOT IMPORTED | NOT IMPORTED | DISCONNECTED |
| OrderBookAnalyzer | NOT IMPORTED | NOT IMPORTED | DISCONNECTED |
| VolumeProfiler | NOT IMPORTED | NOT IMPORTED | DISCONNECTED |
| FundingRateFetcher | NOT IMPORTED | NOT IMPORTED | DISCONNECTED |

### to_prompt() Methods (for LLM integration)

| File | Line | Method |
|------|------|--------|
| src/sentiment/context_manager.py | 58 | MarketContext.to_prompt() |
| src/sentiment/context_manager.py | 119 | ContextManager.to_prompt() |
| src/technical/manager.py | 120 | TechnicalSnapshot.to_prompt() |

**These methods exist but are NEVER CALLED from the trading loop or strategist.**

### Phase 3 Module Status

```
src/sentiment/
├── context_manager.py    [HAS to_prompt(), NOT INTEGRATED]
├── fear_greed.py         [COMPLETE, NOT INTEGRATED]
├── news_feed.py          [COMPLETE, NOT INTEGRATED]
├── social_sentiment.py   [COMPLETE, NOT INTEGRATED]
└── btc_correlation.py    [COMPLETE, NOT INTEGRATED]

src/technical/
├── manager.py            [HAS to_prompt(), NOT INTEGRATED]
├── candle_fetcher.py     [COMPLETE, NOT INTEGRATED]
├── rsi.py                [COMPLETE, NOT INTEGRATED]
├── vwap.py               [COMPLETE, NOT INTEGRATED]
├── atr.py                [COMPLETE, NOT INTEGRATED]
├── orderbook.py          [COMPLETE, NOT INTEGRATED]
├── volume_profile.py     [COMPLETE, NOT INTEGRATED]
└── funding.py            [COMPLETE, NOT INTEGRATED]
```

**Conclusion:** All 13 Phase 3 modules are implemented but NONE are connected to the main trading loop. The Intelligence Layer is dormant.

---

## Summary

| Metric | Count | Status |
|--------|-------|--------|
| Coin mismatches (config vs technical) | 10 | WARNING |
| Query/schema mismatches | 2 | CRITICAL |
| Threshold inconsistencies | 0 | OK |
| Phase 3 modules connected | 0/13 | CRITICAL |

### Critical Issues

1. **MISSING TABLE:** `insights` table queried in `analysis/learning.py:377,398` but never created in database schema
2. **COIN SYMBOL MISMATCH:** 5 tradeable coins (APT, ARB, INJ, NEAR, OP) cannot get technical data
3. **PHASE 3 DISCONNECTED:** All 13 Intelligence Layer modules are built but not wired to trading

### Recommendations

1. Add `insights` table to database schema or fix queries to use correct table
2. Add APT, ARB, INJ, NEAR, OP to SYMBOL_MAP in technical files, OR remove from tradeable config
3. Wire Phase 3 modules into strategist.py prompt construction:
   - Import ContextManager and TechnicalManager
   - Call to_prompt() and include in LLM context

---

## Acceptance Criteria Checklist

- [x] extract_coins.py ran, coin_matrix_raw.txt created
- [x] extract_queries.py ran, query_matrix_raw.txt created (513 lines)
- [x] win_rate_raw.txt created (334 lines)
- [x] phase3_integration.txt created
- [x] CHUNK-7b-MATRICES.md summarizes all findings
