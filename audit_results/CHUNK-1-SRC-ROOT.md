# CHUNK 1: src/ Root Directory Audit

**Date:** 2026-02-04
**Auditor:** Claude Code
**Files Audited:** 27 of 27

---

## Summary

| Metric | Value |
|--------|-------|
| Total Files | 27 |
| Files Audited | 27 |
| Critical Issues | 2 |
| High Issues | 2 |
| Medium Issues | 4 |
| Low Issues | 3 |
| Deprecated Files | 3 |

---

## File Inventory

| # | File | Lines | Status | Issues |
|---|------|-------|--------|--------|
| 1 | __init__.py | ~10 | ✅ OK | None |
| 2 | adaptation.py | ~450 | ✅ OK | None |
| 3 | coin_config.py | ~200 | ✅ OK | None |
| 4 | coin_scorer.py | ~500 | ⚠️ BUG | CRIT-003: FAVORED demotion logic |
| 5 | daily_summary.py | ~300 | ✅ OK | None |
| 6 | dashboard.py | ~400 | ⚠️ DEPRECATED | Replaced by dashboard_v2.py |
| 7 | dashboard_v2.py | ~600 | ✅ OK | None |
| 8 | database.py | 1743 | ⚠️ WARN | MED-001: 20+ unused methods |
| 9 | effectiveness.py | 662 | ✅ OK | None |
| 10 | journal.py | 1114 | ✅ OK | None |
| 11 | knowledge.py | 539 | ✅ OK | None |
| 12 | learning_system.py | 975 | ✅ OK | None |
| 13 | llm_interface.py | 440 | ✅ OK | None |
| 14 | main.py | 1062 | ⚠️ CRITICAL | CRIT-001: Phase 3 not integrated |
| 15 | main_legacy.py | 456 | ⚠️ DEPRECATED | Replaced by main.py |
| 16 | market_data.py | 558 | ✅ OK | None |
| 17 | market_feed.py | 711 | ✅ OK | None |
| 18 | metrics.py | 548 | ✅ OK | None |
| 19 | pattern_library.py | 716 | ✅ OK | None |
| 20 | profitability.py | 907 | ✅ OK | None |
| 21 | quick_update.py | 373 | ✅ OK | None |
| 22 | reflection.py | 794 | ✅ OK | None |
| 23 | risk_manager.py | 841 | ✅ OK | None |
| 24 | sniper.py | 863 | ✅ OK | None |
| 25 | strategist.py | 922 | ⚠️ CRITICAL | CRIT-001, HIGH-001 |
| 26 | trading_engine.py | 395 | ⚠️ DEPRECATED | Replaced by Sniper |
| 27 | volatility.py | 469 | ✅ OK | None |

---

## Critical Issues

### CRIT-001: Phase 3 Intelligence Layer Not Integrated

**Files:** `main.py`, `strategist.py`
**Severity:** CRITICAL
**Category:** INTEGRATION

**Description:**
Phase 3 modules (`ContextManager`, `TechnicalManager`) are fully implemented with passing tests but are NOT imported or used in production code.

**Evidence:**
- `main.py` does not import `ContextManager` or `TechnicalManager`
- `TradingSystem.__init__()` does not initialize these managers
- `Strategist.__init__()` has no parameters for context/technical managers
- `Strategist._build_prompt()` does not include RSI, VWAP, ATR, funding rates, fear/greed index, or news sentiment

**Impact:**
- Bot runs "blind" without technical indicators
- All Phase 3 intelligence (RSI, VWAP, ATR, Fear & Greed, news sentiment) is dead code
- Trading decisions based only on price and 24h change

**Fix:**
1. Import in main.py:
   ```python
   from src.sentiment.context_manager import ContextManager
   from src.technical.manager import TechnicalManager
   ```
2. Initialize in `TradingSystem.__init__()`:
   ```python
   self.context_manager = ContextManager()
   self.technical_manager = TechnicalManager(self.db)
   ```
3. Pass to Strategist:
   ```python
   self.strategist = Strategist(
       ...,
       context_manager=self.context_manager,
       technical_manager=self.technical_manager,
   )
   ```
4. Update `Strategist._build_prompt()` to include Phase 3 data

---

### CRIT-003: FAVORED Demotion Logic Bug

**File:** `coin_scorer.py:211`
**Severity:** CRITICAL
**Category:** LOGIC

**Description:**
Asymmetric promotion/demotion criteria for FAVORED status:
- Promotion requires: `win_rate >= 60% AND total_pnl > 0`
- Demotion only checks: `win_rate < 60%`

**Impact:**
- Coin can stay FAVORED while losing money (high win rate, negative P&L)
- Coin can be demoted despite great P&L if win rate dips

**Fix:**
```python
# Line 211 - change from:
elif (score.win_rate < FAVORED_WIN_RATE and
      current_status == CoinStatus.FAVORED):

# To:
elif ((score.win_rate < FAVORED_WIN_RATE or score.total_pnl <= 0) and
      current_status == CoinStatus.FAVORED):
```

---

## High Issues

### HIGH-001: Strategist Missing Phase 3 Context

**File:** `strategist.py:548-636` (`_build_prompt()`)
**Severity:** HIGH
**Category:** INTEGRATION

**Description:**
The LLM prompt built by Strategist does not include any Phase 3 data:
- No RSI values
- No VWAP proximity
- No ATR/volatility metrics
- No funding rates
- No Fear & Greed index
- No news/social sentiment
- No BTC correlation signals

**Impact:**
LLM makes trading decisions without technical analysis or sentiment data.

**Fix:**
After CRIT-001 is fixed, update `_build_prompt()` to include:
```python
# Technical indicators section
TECHNICAL INDICATORS:
{technical_manager.get_snapshot_text()}

# Market context section
MARKET CONTEXT:
{context_manager.get_context_text()}
```

---

### HIGH-002: No Integration Tests for Phase 3

**Severity:** HIGH
**Category:** TEST

**Description:**
No integration tests exist for:
- ContextManager → Strategist flow
- TechnicalManager → Strategist flow
- Full pipeline with Phase 3 data

**Impact:**
Cannot verify Phase 3 integration works correctly.

**Fix:**
After CRIT-001 is fixed, add integration tests in `tests/test_integration.py`.

---

## Medium Issues

### MED-001: Unused Database Methods

**File:** `database.py`
**Severity:** MEDIUM
**Category:** DEAD

**Description:**
Vulture analysis found 20+ potentially unused database methods:
- `update_account_state()`
- `get_recent_activity()`
- `get_recent_reflections()`
- `get_active_conditions()`
- `mark_condition_triggered()`
- `clear_all_conditions()`
- And more

**Impact:**
Dead code increases maintenance burden.

**Recommendation:**
Review each method - either document as "reserved for future use" or remove.

---

### MED-002: CoinScorer Unused Methods

**File:** `coin_scorer.py`
**Severity:** MEDIUM
**Category:** DEAD

**Description:**
Methods flagged as potentially unused:
- `force_blacklist()`
- `force_unblacklist()`

**Recommendation:**
Verify if these are intentional admin functions or dead code.

---

### MED-003: Deprecated Files Still Present

**Files:** `main_legacy.py`, `trading_engine.py`, `dashboard.py`
**Severity:** MEDIUM
**Category:** DEAD

**Description:**
Three deprecated files are still in src/:
1. `main_legacy.py` - Old TradingBot class using CoinGecko polling
2. `trading_engine.py` - Old trade execution, replaced by Sniper
3. `dashboard.py` - Old dashboard, replaced by dashboard_v2.py

**Impact:**
Confusion about which files are active.

**Recommendation:**
Move to `src/deprecated/` or delete with deprecation comment in git history.

---

### MED-004: Risk Manager Tier 3 Coins

**File:** `risk_manager.py`
**Severity:** MEDIUM
**Category:** CONFIG

**Description:**
Risk manager tier configuration may not match settings.py Tier 3 coins. Needs verification that NEAR, APT, ARB, OP, INJ are properly categorized.

**Recommendation:**
Verify tier assignment for all tradeable coins matches settings.py.

---

## Low Issues

### LOW-001: Repeated Guard Patterns in main.py

**File:** `main.py:937-973`
**Severity:** LOW
**Category:** STYLE

**Description:**
Multiple repeated `if not self.X:` guard patterns that could be refactored.

**Recommendation:**
Create helper method for component initialization checks.

---

### LOW-002: F-String Logging

**Files:** Multiple
**Severity:** LOW
**Category:** STYLE

**Description:**
Many instances of f-string formatting in logging calls, e.g.:
```python
logger.info(f"Message {variable}")
```
Should use lazy formatting:
```python
logger.info("Message %s", variable)
```

**Impact:**
Minor performance - f-strings evaluate even when log level disabled.

---

### LOW-003: Missing Type Hints

**Files:** Various
**Severity:** LOW
**Category:** STYLE

**Description:**
Some functions lack complete type hints.

**Recommendation:**
Add type hints incrementally, especially for public APIs.

---

## File Details

### 1. __init__.py
- **Purpose:** Package marker
- **Imports:** None
- **Exports:** None
- **Issues:** None

### 2. adaptation.py (~450 lines)
- **Purpose:** AdaptationEngine converts insights to Knowledge Brain changes
- **Key Classes:** `AdaptationEngine`, `Adaptation`
- **Imports:** `database`, `models.adaptation`
- **Database Tables:** `adaptations`
- **Issues:** None

### 3. coin_config.py (~200 lines)
- **Purpose:** Tier-based coin configuration
- **Key Functions:** `get_tier()`, `get_tier_config()`
- **Constants:** `TIER_1_COINS`, `TIER_2_COINS`, `TIER_3_COINS`
- **Issues:** None

### 4. coin_scorer.py (~500 lines)
- **Purpose:** Track coin trading performance, manage status
- **Key Classes:** `CoinScorer`, `CoinStatus` enum
- **Status Values:** NORMAL, FAVORED, REDUCED, BLACKLISTED
- **Database Tables:** `knowledge_coin_scores`
- **Issues:** CRIT-003 (demotion logic bug)

### 5. daily_summary.py (~300 lines)
- **Purpose:** Generate daily trading summaries
- **Key Classes:** `DailySummaryGenerator`
- **Integrations:** Database, LLM for narrative
- **Issues:** None

### 6. dashboard.py (~400 lines)
- **Purpose:** Original Flask dashboard (DEPRECATED)
- **Status:** Replaced by dashboard_v2.py
- **Issues:** MED-003 (should remove)

### 7. dashboard_v2.py (~600 lines)
- **Purpose:** Current Flask dashboard with SSE
- **Routes:** `/`, `/trades`, `/knowledge`, `/adaptations`, `/profitability`
- **API:** `/api/stats`, `/api/prices`, `/api/coins`, `/api/patterns`, `/api/rules`, `/api/events`
- **Issues:** None

### 8. database.py (1743 lines)
- **Purpose:** SQLite database operations
- **Tables:** 21+ tables including:
  - `open_trades`, `closed_trades`, `account_state`
  - `trade_conditions`, `knowledge_coin_scores`
  - `knowledge_patterns`, `knowledge_rules`, `knowledge_insights`
  - `adaptations`, `profitability_snapshots`
  - `adaptation_measurements`, `high_water_marks`
  - `runtime_state`, `activity_log`, `trade_journal`
- **Issues:** MED-001 (unused methods)

### 9. effectiveness.py (662 lines)
- **Purpose:** Track adaptation effectiveness, enable rollback
- **Key Classes:** `EffectivenessMonitor`
- **Constants:** `MIN_TRADES=10`, `HARMFUL_THRESHOLD=-10%`
- **Database Tables:** `adaptation_measurements`, `high_water_marks`
- **Issues:** None

### 10. journal.py (1114 lines)
- **Purpose:** Trade journaling with post-trade analysis
- **Key Classes:** `TradeJournal`, `JournalEntry`
- **Features:** Async write queue, post-trade price capture
- **Database Tables:** `trade_journal`
- **Issues:** None

### 11. knowledge.py (539 lines)
- **Purpose:** KnowledgeBrain - central knowledge management
- **Key Classes:** `KnowledgeBrain`
- **Manages:** CoinScores, TradingPatterns, RegimeRules
- **Issues:** None

### 12. learning_system.py (975 lines)
- **Purpose:** LLM-powered trade analysis and rule creation
- **Key Classes:** `LearningSystem`, `RuleManager`
- **Features:** Rule lifecycle (testing → active/rejected)
- **Confidence Threshold:** 0.7 for rule creation
- **Issues:** None

### 13. llm_interface.py (440 lines)
- **Purpose:** Ollama API interface
- **Default Model:** `qwen2.5:14b`
- **Connection:** WSL gateway IP
- **Methods:** `query()`, `query_async()`
- **Issues:** None

### 14. main.py (1062 lines)
- **Purpose:** Main TradingSystem orchestration
- **Key Classes:** `TradingSystem`, `HealthMonitor`
- **Components Initialized:**
  - ✅ LLMInterface, MarketFeed, Database
  - ✅ KnowledgeBrain, CoinScorer, PatternLibrary
  - ✅ Sniper, ReflectionEngine, AdaptationEngine
  - ✅ ProfitabilityTracker, EffectivenessMonitor
  - ✅ DashboardServer
  - ❌ ContextManager (NOT IMPORTED)
  - ❌ TechnicalManager (NOT IMPORTED)
- **Issues:** CRIT-001 (Phase 3 not integrated)

### 15. main_legacy.py (456 lines)
- **Purpose:** Old TradingBot using CoinGecko polling (DEPRECATED)
- **Status:** Replaced by main.py
- **Issues:** MED-003 (should remove)

### 16. market_data.py (558 lines)
- **Purpose:** CoinGecko API data fetcher
- **Key Classes:** `MarketDataFetcher`
- **Features:** Batch fetching, volume filtering by tier
- **Universe:** 45 coins
- **Issues:** None

### 17. market_feed.py (711 lines)
- **Purpose:** WebSocket market feed (Bybit/Binance)
- **Key Classes:** `MarketFeed`, `PriceTick`, `TradeEvent`
- **Features:** Sub-second updates, reconnection logic
- **Primary Exchange:** Bybit
- **Fallback:** Binance
- **Issues:** None

### 18. metrics.py (548 lines)
- **Purpose:** Prometheus-compatible metrics collection
- **Key Classes:** `MetricsCollector`
- **Features:** Alert thresholds, metric export
- **Issues:** None

### 19. pattern_library.py (716 lines)
- **Purpose:** Trading pattern management
- **Key Classes:** `PatternLibrary`, `TradingPattern`
- **Features:** SEED_PATTERNS for initialization, confidence management
- **Database Tables:** `knowledge_patterns`
- **Issues:** None

### 20. profitability.py (907 lines)
- **Purpose:** P&L tracking, performance analysis
- **Key Classes:** `ProfitabilityTracker`, `ProfitSnapshot`, `DimensionPerformance`
- **Features:** Equity curve, Sharpe ratio calculation
- **Database Tables:** `profitability_snapshots`
- **Issues:** None

### 21. quick_update.py (373 lines)
- **Purpose:** Instant post-trade knowledge updates (<10ms)
- **Key Classes:** `QuickUpdate`
- **Updates:** Coin scores, pattern confidence
- **Called By:** Sniper on trade exit
- **Issues:** None

### 22. reflection.py (794 lines)
- **Purpose:** LLM-powered periodic analysis
- **Key Classes:** `ReflectionEngine`
- **Triggers:** Hourly OR every 10 trades
- **Analysis Dimensions:** Coin, pattern, time, regime
- **Issues:** None

### 23. risk_manager.py (841 lines)
- **Purpose:** Tier-based risk management
- **Key Classes:** `RiskManager`
- **Features:**
  - 3 tiers with different position limits
  - Volatility adjustment
  - Coin cooldowns (30 min default, persisted to DB)
- **Database Tables:** `runtime_state` (for cooldowns)
- **Issues:** MED-004 (verify tier assignment)

### 24. sniper.py (863 lines)
- **Purpose:** Fast execution engine (replaces trading_engine)
- **Key Classes:** `Sniper`, `Position`, `ExecutionEvent`
- **Constraint:** `on_price_tick` must complete in <1ms
- **Risk Limits:**
  - MAX_POSITIONS = 5
  - MAX_PER_COIN = 1
  - MAX_EXPOSURE_PCT = 10%
- **Features:** State persistence, stop-loss/take-profit management
- **Issues:** None

### 25. strategist.py (922 lines)
- **Purpose:** LLM-powered trade condition generator
- **Key Classes:** `Strategist`
- **Interval:** Default 3 minutes
- **Model:** qwen2.5:14b
- **Inputs Used:**
  - ✅ MarketFeed prices
  - ✅ Knowledge Brain (coin scores, patterns, rules)
  - ✅ CoinScorer (blacklist, position modifiers)
  - ✅ PatternLibrary (pattern context)
  - ❌ ContextManager (NOT IMPORTED)
  - ❌ TechnicalManager (NOT IMPORTED)
- **Issues:** CRIT-001, HIGH-001 (Phase 3 not in prompt)

### 26. trading_engine.py (395 lines)
- **Purpose:** Paper trading execution (DEPRECATED)
- **Status:** Replaced by Sniper
- **Issues:** MED-003 (should remove)

### 27. volatility.py (469 lines)
- **Purpose:** Volatility calculation for risk adjustment
- **Key Classes:** `VolatilityCalculator`
- **Features:**
  - Rolling 24h volatility
  - Volatility score (0-100)
  - Position size multipliers
  - Dynamic stop-loss (ATR-like)
  - 5-minute caching
- **Database Tables:** `price_history`
- **Issues:** None

---

## Cross-Reference Analysis

### Component Dependencies (main.py → others)

```
TradingSystem
├── LLMInterface (llm_interface.py)
├── MarketFeed (market_feed.py)
├── Database (database.py)
├── KnowledgeBrain (knowledge.py)
│   ├── CoinScorer (coin_scorer.py)
│   ├── PatternLibrary (pattern_library.py)
│   └── RegimeRules
├── Strategist (strategist.py)
│   ├── LLMInterface
│   ├── MarketFeed
│   ├── KnowledgeBrain
│   ├── CoinScorer
│   └── PatternLibrary
├── Sniper (sniper.py)
│   ├── TradeJournal (journal.py)
│   └── QuickUpdate (quick_update.py)
├── ReflectionEngine (reflection.py)
├── AdaptationEngine (adaptation.py)
├── ProfitabilityTracker (profitability.py)
├── EffectivenessMonitor (effectiveness.py)
├── DashboardServer (dashboard_v2.py)
├── ❌ ContextManager (NOT CONNECTED)
└── ❌ TechnicalManager (NOT CONNECTED)
```

### Data Flow

```
MarketFeed (WebSocket)
    → Sniper (price ticks)
    → Strategist (current prices)

Strategist (every 3 min)
    → reads: MarketFeed, KnowledgeBrain
    → generates: TradeConditions
    → sends to: Sniper

Sniper (real-time)
    → watches: TradeConditions
    → executes: entries/exits
    → calls: QuickUpdate, TradeJournal

QuickUpdate (instant)
    → updates: CoinScorer, PatternLibrary

ReflectionEngine (hourly or 10 trades)
    → reads: TradeJournal
    → generates: Insights
    → sends to: AdaptationEngine

AdaptationEngine
    → updates: KnowledgeBrain

EffectivenessMonitor
    → tracks: Adaptation outcomes
    → can rollback: harmful changes
```

---

## Recommendations

### Priority 1 (Fix Immediately)
1. **CRIT-001**: Integrate Phase 3 modules into main.py and strategist.py
2. **CRIT-003**: Fix FAVORED demotion logic in coin_scorer.py

### Priority 2 (Fix Soon)
3. **HIGH-001**: Update Strategist._build_prompt() to include Phase 3 data
4. **HIGH-002**: Add Phase 3 integration tests

### Priority 3 (Fix When Convenient)
5. **MED-003**: Remove deprecated files (main_legacy.py, trading_engine.py, dashboard.py)
6. **MED-001**: Review and clean up unused database methods
7. **MED-002**: Document or remove unused CoinScorer methods
8. **MED-004**: Verify risk manager tier assignments

### Priority 4 (Nice to Have)
9. **LOW-001**: Refactor repeated guard patterns
10. **LOW-002**: Convert f-string logging to lazy formatting
11. **LOW-003**: Add missing type hints

---

## Audit Completion

| Criteria | Status |
|----------|--------|
| All 27 files read | ✅ |
| Issues documented | ✅ 11 issues |
| Cross-references analyzed | ✅ |
| Recommendations provided | ✅ |

**Chunk 1 Complete: 27/27 files audited**

---

*Audit completed: 2026-02-04*
*Auditor: Claude Code*
