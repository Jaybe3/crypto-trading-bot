# Phase 2: Manual File-by-File Audit

**Date:** 2026-02-04
**Auditor:** Claude Code

---

## Pre-Audit: Known Issues Verified

| # | Issue | Location | Verified |
|---|-------|----------|----------|
| 1 | SYMBOL_MAP mismatch | funding.py, candle_fetcher.py vs settings.py | ✅ CONFIRMED |
| 2 | Phase 3 not imported | main.py, strategist.py | ✅ CONFIRMED |
| 3 | FAVORED demotion asymmetry | coin_scorer.py:211 | ✅ CONFIRMED |
| 4 | Exchange config mismatch | coins.json vs settings.py | ✅ CONFIRMED |
| 5 | SYSTEM-STATE contradiction | docs/SYSTEM-STATE.md:88 vs :114 | ✅ CONFIRMED |
| 6 | "Duplicate code" main.py | Lines 937-973 | ⚠️ PARTIAL - repeated patterns |

---

## Critical Issues Found

### CRIT-001: SYMBOL_MAP Mismatch
**Severity:** HIGH
**Files:** `src/technical/funding.py`, `src/technical/candle_fetcher.py`, `config/settings.py`

**Description:**
- `settings.py` Tier 3 coins: `NEAR, APT, ARB, OP, INJ`
- `funding.py` SYMBOL_MAP: `PEPE, FLOKI, BONK, WIF, SHIB`
- `candle_fetcher.py` SYMBOL_MAP: `PEPE, FLOKI, BONK, WIF, SHIB`

**Impact:** Technical indicators will fail for Tier 3 coins (NEAR, APT, ARB, OP, INJ) because they're not in SYMBOL_MAP. API calls will construct wrong symbols.

**Fix:** Synchronize SYMBOL_MAP with settings.py TRADEABLE_COINS.

---

### CRIT-002: Phase 3 Modules Not Integrated
**Severity:** CRITICAL
**Files:** `src/main.py`, `src/strategist.py`

**Description:**
Phase 3 modules (`src/sentiment/*`, `src/technical/*`) are fully implemented with tests passing, but they are NOT imported or used anywhere in the production code.

**Impact:** All Phase 3 functionality (RSI, VWAP, ATR, funding rates, fear/greed, news, etc.) is dead code. The bot runs without any of this intelligence.

**Fix:**
1. Import ContextManager and TechnicalManager in main.py
2. Initialize them in TradingSystem.__init__
3. Pass to Strategist
4. Use in Strategist.generate_conditions() prompt

---

### CRIT-003: Exchange Configuration Conflict
**Severity:** MEDIUM
**Files:** `config/coins.json`, `config/settings.py`

**Description:**
- `coins.json`: `"exchange": "binance_us"`
- `settings.py`: `DEFAULT_EXCHANGE = "bybit"`

**Impact:** Confusion about which exchange the bot uses. Could cause API failures if wrong exchange is targeted.

**Fix:** Remove deprecated coins.json or update to match settings.py.

---

### CRIT-004: FAVORED Demotion Logic Bug
**Severity:** MEDIUM
**Files:** `src/coin_scorer.py`

**Description:**
- Promotion to FAVORED requires: `win_rate >= 60% AND total_pnl > 0`
- Demotion from FAVORED only checks: `win_rate < 60%`

**Impact:** A coin can stay FAVORED while losing money as long as win rate stays high. Or get demoted with great P&L if win rate dips.

**Fix:** Add P&L check to demotion condition:
```python
elif (score.win_rate < FAVORED_WIN_RATE or score.total_pnl <= 0) and
      current_status == CoinStatus.FAVORED:
```

---

### CRIT-005: Documentation Out of Sync
**Severity:** LOW
**Files:** `docs/SYSTEM-STATE.md`

**Description:**
Line 88 says "NOT INCLUDED (Phase 3): RSI, VWAP, ATR, Fear & Greed..."
Line 114 says "Status: Complete (14/14 tasks complete)"

**Impact:** Misleading documentation for anyone reading system state.

**Fix:** Update line 88 to remove "NOT INCLUDED" text or reword the section.

---

## File-by-File Audit Progress

### src/ Directory

| File | Status | Issues Found |
|------|--------|--------------|
| adaptation.py | ⬜ TODO | |
| coin_config.py | ⬜ TODO | |
| coin_scorer.py | ✅ DONE | CRIT-004 |
| daily_summary.py | ⬜ TODO | |
| dashboard.py | ⬜ TODO | |
| dashboard_v2.py | ⬜ TODO | |
| database.py | ⬜ TODO | |
| effectiveness.py | ⬜ TODO | |
| journal.py | ⬜ TODO | |
| knowledge.py | ⬜ TODO | |
| learning_system.py | ⬜ TODO | |
| llm_interface.py | ⬜ TODO | |
| main.py | ✅ DONE | CRIT-002 |
| main_legacy.py | ⬜ TODO | |
| market_data.py | ⬜ TODO | |
| market_feed.py | ⬜ TODO | |
| metrics.py | ⬜ TODO | |
| pattern_library.py | ⬜ TODO | |
| profitability.py | ⬜ TODO | |
| quick_update.py | ⬜ TODO | |
| reflection.py | ⬜ TODO | |
| risk_manager.py | ⬜ TODO | |
| sniper.py | ⬜ TODO | |
| strategist.py | ✅ DONE | CRIT-002 |
| trading_engine.py | ⬜ TODO | |
| volatility.py | ⬜ TODO | |

### src/technical/

| File | Status | Issues Found |
|------|--------|--------------|
| __init__.py | ✅ DONE | - |
| atr.py | ⬜ TODO | |
| candle_fetcher.py | ✅ DONE | CRIT-001 |
| funding.py | ✅ DONE | CRIT-001 |
| manager.py | ⬜ TODO | |
| orderbook.py | ⬜ TODO | |
| rsi.py | ⬜ TODO | |
| support_resistance.py | ⬜ TODO | |
| volume_profile.py | ⬜ TODO | |
| vwap.py | ⬜ TODO | |

### src/sentiment/

| File | Status | Issues Found |
|------|--------|--------------|
| __init__.py | ✅ DONE | - |
| btc_correlation.py | ⬜ TODO | |
| context_manager.py | ⬜ TODO | |
| fear_greed.py | ⬜ TODO | |
| news_feed.py | ⬜ TODO | |
| social_sentiment.py | ⬜ TODO | |

### config/

| File | Status | Issues Found |
|------|--------|--------------|
| coins.json | ✅ DONE | CRIT-003 |
| settings.py | ✅ DONE | CRIT-001, CRIT-003 |

---

## Continuation Note

This audit is in progress. Due to the comprehensive nature (191+ files), this document will be updated as files are reviewed.

Current Progress: ~15/191 files audited
