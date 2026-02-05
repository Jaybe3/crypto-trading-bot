# Phase 3: Cross-Reference Matrices

**Date:** 2026-02-04
**Auditor:** Claude Code

---

## 3.1 Import Matrix (Critical Modules)

### Phase 3 Modules - Integration Status

| Consumer | Import | Name | Exists | Used |
|----------|--------|------|--------|------|
| main.py | ❌ NOT imported | ContextManager | ✅ | ❌ NO |
| main.py | ❌ NOT imported | TechnicalManager | ✅ | ❌ NO |
| main.py | ❌ NOT imported | MarketContext | ✅ | ❌ NO |
| main.py | ❌ NOT imported | TechnicalSnapshot | ✅ | ❌ NO |
| strategist.py | ❌ NOT imported | ContextManager | ✅ | ❌ NO |
| strategist.py | ❌ NOT imported | TechnicalManager | ✅ | ❌ NO |

**CRITICAL ISSUE:** All Phase 3 modules are implemented but never imported or used in production code.

---

## 3.2 Config Matrix

| Config Key | settings.py | coins.json | Consistent? |
|------------|-------------|------------|-------------|
| DEFAULT_EXCHANGE | "bybit" | "binance_us" | ❌ MISMATCH |
| TRADEABLE_COINS | 20 coins | 20 coins | ✅ |
| Tier 3 coins | NEAR,APT,ARB,OP,INJ | NEAR,APT,ARB,OP,INJ | ✅ |
| WebSocket URL | (uses pybit) | binance URLs | ❌ MISMATCH |

---

## 3.3 Coin Symbol Matrix

| Symbol | settings.py | coins.json | funding.py SYMBOL_MAP | candle_fetcher.py SYMBOL_MAP | market_feed.py |
|--------|-------------|------------|----------------------|------------------------------|----------------|
| **Tier 1** |
| BTC | ✅ | ✅ | ✅ | ✅ | ✅ |
| ETH | ✅ | ✅ | ✅ | ✅ | ✅ |
| SOL | ✅ | ✅ | ✅ | ✅ | ✅ |
| BNB | ✅ | ✅ | ✅ | ✅ | ✅ |
| XRP | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Tier 2** |
| DOGE | ✅ | ✅ | ✅ | ✅ | ✅ |
| ADA | ✅ | ✅ | ✅ | ✅ | ✅ |
| AVAX | ✅ | ✅ | ✅ | ✅ | ✅ |
| LINK | ✅ | ✅ | ✅ | ✅ | ✅ |
| DOT | ✅ | ✅ | ✅ | ✅ | ✅ |
| MATIC | ✅ | ✅ | ✅ | ✅ | ✅ |
| UNI | ✅ | ✅ | ✅ | ✅ | ✅ |
| ATOM | ✅ | ✅ | ✅ | ✅ | ✅ |
| LTC | ✅ | ✅ | ✅ | ✅ | ✅ |
| ETC | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Tier 3 - MISMATCH** |
| NEAR | ✅ | ✅ | ❌ MISSING | ❌ MISSING | ✅ |
| APT | ✅ | ✅ | ❌ MISSING | ❌ MISSING | ✅ |
| ARB | ✅ | ✅ | ❌ MISSING | ❌ MISSING | ✅ |
| OP | ✅ | ✅ | ❌ MISSING | ❌ MISSING | ✅ |
| INJ | ✅ | ✅ | ❌ MISSING | ❌ MISSING | ✅ |
| **Not in settings.py** |
| PEPE | ❌ | ❌ | ✅ EXTRA | ✅ EXTRA | ❌ |
| FLOKI | ❌ | ❌ | ✅ EXTRA | ✅ EXTRA | ❌ |
| BONK | ❌ | ❌ | ✅ EXTRA | ✅ EXTRA | ❌ |
| WIF | ❌ | ❌ | ✅ EXTRA | ✅ EXTRA | ❌ |
| SHIB | ❌ | ❌ | ✅ EXTRA | ✅ EXTRA | ❌ |

**CRITICAL ISSUE:** Tier 3 coins (NEAR, APT, ARB, OP, INJ) are in settings but NOT in technical module SYMBOL_MAPs. Meme coins (PEPE, FLOKI, etc.) are in SYMBOL_MAPs but NOT in settings.

---

## 3.4 Database Matrix

| File | Query Type | Table | Schema Match |
|------|-----------|-------|--------------|
| database.py | CREATE | open_trades | ✅ |
| database.py | CREATE | closed_trades | ✅ |
| database.py | CREATE | account_state | ✅ |
| database.py | CREATE | trade_conditions | ✅ |
| database.py | CREATE | knowledge_coin_scores | ✅ |
| database.py | CREATE | knowledge_patterns | ✅ |
| database.py | CREATE | knowledge_rules | ✅ |
| database.py | CREATE | knowledge_insights | ✅ |
| database.py | CREATE | adaptations | ✅ |
| database.py | CREATE | profitability_snapshots | ✅ |
| database.py | CREATE | adaptation_measurements | ✅ |
| database.py | CREATE | high_water_marks | ✅ |
| database.py | CREATE | runtime_state | ✅ |
| database.py | CREATE | activity_log | ✅ |

All database tables defined in schema and created properly.

---

## 3.5 API Endpoint Matrix

### Dashboard v2 API Routes

| Route | Method | Handler | Exists |
|-------|--------|---------|--------|
| / | GET | dashboard_page | ✅ |
| /trades | GET | trades_page | ✅ |
| /knowledge | GET | knowledge_page | ✅ |
| /adaptations | GET | adaptations_page | ✅ |
| /profitability | GET | profitability_page | ✅ |
| /api/stats | GET | get_stats | ✅ |
| /api/prices | GET | get_prices | ✅ |
| /api/coins | GET | get_coins | ✅ |
| /api/patterns | GET | get_patterns | ✅ |
| /api/rules | GET | get_rules | ✅ |
| /api/events | GET | event_stream (SSE) | ✅ |

All API endpoints have corresponding handlers.

---

## 3.6 Component Initialization Matrix

| Component | Initialized in main.py | Passed to Strategist | Used |
|-----------|----------------------|---------------------|------|
| LLMInterface | ✅ | ✅ | ✅ |
| MarketFeed | ✅ | ✅ | ✅ |
| Database | ✅ | ✅ | ✅ |
| KnowledgeBrain | ✅ | ✅ | ✅ |
| CoinScorer | ✅ | ✅ | ✅ |
| PatternLibrary | ✅ | ✅ | ✅ |
| Sniper | ✅ | ❌ N/A | ✅ |
| ReflectionEngine | ✅ | ❌ N/A | ✅ |
| AdaptationEngine | ✅ | ❌ N/A | ✅ |
| ProfitabilityTracker | ✅ | ❌ N/A | ✅ |
| EffectivenessMonitor | ✅ | ❌ N/A | ✅ |
| DashboardServer | ✅ | ❌ N/A | ✅ |
| **ContextManager** | ❌ NOT init | ❌ | ❌ |
| **TechnicalManager** | ❌ NOT init | ❌ | ❌ |

**CRITICAL:** Phase 3 managers are not initialized or used.

---

## 3.7 Documentation vs Reality Matrix

| Doc Claim | File | Reality | Match |
|-----------|------|---------|-------|
| "NOT INCLUDED: RSI, VWAP..." | SYSTEM-STATE.md:88 | RSI, VWAP implemented | ❌ DOC OUTDATED |
| "Phase 3 Complete (14/14)" | SYSTEM-STATE.md:114 | Code exists, not integrated | ⚠️ PARTIAL |
| "bybit exchange" | settings.py | Code uses Bybit | ✅ |
| "binance_us exchange" | coins.json | Deprecated/unused | ❌ STALE |

---

## Summary

| Category | Issues Found |
|----------|-------------|
| Phase 3 Integration | CRITICAL - modules not used |
| Coin Symbol Sync | CRITICAL - 10 mismatches |
| Config Consistency | MEDIUM - exchange mismatch |
| Database Schema | OK |
| API Endpoints | OK |
| Documentation | MEDIUM - outdated |

**Total Critical Issues:** 2
**Total Medium Issues:** 2
