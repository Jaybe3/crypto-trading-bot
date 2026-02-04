# INCONSISTENCIES LOG

**Generated:** February 3, 2026
**Auditor:** Claude Code (Automated)

This document lists all inconsistencies found during the comprehensive audit.

---

## CRITICAL INCONSISTENCIES

### I-001: Documentation References Wrong Entry Point

| Field | Value |
|-------|-------|
| **Severity** | CRITICAL |
| **Category** | Documentation |
| **Description** | 23 files reference `main.py` which was renamed to `main.py` |
| **Impact** | Users following documentation will get "file not found" errors |
| **Affected Files** | See table below |

**Files with `main.py` references:**

| # | File | Count | Context |
|---|------|-------|---------|
| 1 | docs/operations/RUNBOOK.md | 12 | Commands, start/stop procedures |
| 2 | docs/development/SETUP.md | 8 | Installation, running instructions |
| 3 | docs/architecture/SYSTEM-OVERVIEW.md | 4 | Entry point documentation |
| 4 | docs/development/COMPONENT-GUIDE.md | Multiple | Component references |
| 5 | docs/operations/TROUBLESHOOTING.md | Multiple | Troubleshooting commands |
| 6 | docs/operations/DASHBOARD-GUIDE.md | Multiple | Dashboard startup |
| 7 | docs/operations/PAPER-TRADING-GUIDE.md | Multiple | Paper trading commands |
| 8 | docs/architecture/COMPONENT-REFERENCE.md | Multiple | Component docs |
| 9 | docs/PRE-RUN-CHECKLIST.md | Multiple | Checklist items |
| 10 | AUDIT-REPORT.md | Multiple | Prior audit |
| 11 | tasks/completed/phase-2-learning/TASK-103.md | 1 | Task reference |
| 12 | tasks/completed/phase-2-learning/TASK-112.md | 1 | Task reference |
| 13 | tasks/completed/phase-2-learning/TASK-121.md | 1 | Task reference |
| 14 | tasks/completed/phase-2-learning/TASK-122.md | 1 | Task reference |
| 15 | tasks/completed/phase-2-learning/TASK-130.md | 1 | Task reference |
| 16 | tasks/completed/phase-2-learning/TASK-131.md | 1 | Task reference |
| 17 | tasks/completed/phase-2-learning/TASK-133.md | 1 | Task reference |
| 18 | tasks/completed/phase-2-learning/TASK-140.md | 1 | Task reference |
| 19 | tasks/completed/phase-2-learning/TASK-141.md | 1 | Task reference |
| 20 | tasks/completed/phase-2-learning/TASK-142.md | 1 | Task reference |
| 21 | tasks/completed/phase-2-learning/TASK-143.md | 1 | Task reference |
| 22 | tasks/completed/phase-2-learning/TASK-150.md | 1 | Task reference |
| 23 | src/main.py | 1 | Internal docstring |

---

### I-002: Test Suite Has 92 Failures/Errors

| Field | Value |
|-------|-------|
| **Severity** | CRITICAL |
| **Category** | Testing |
| **Description** | 56 failures + 36 errors out of 600 tests |
| **Impact** | Cannot verify system correctness; CI/CD would fail |
| **Root Causes** | Mixed - deprecated tests + interface changes |

**Failure Breakdown:**

| Category | Tests | Reason |
|----------|-------|--------|
| Deprecated: trading_engine | 13 fail + 23 err | Tests deprecated component |
| Deprecated: learning_system | 7 err | Tests deprecated component |
| Strategist | 13 fail | Interface/mock changes |
| Knowledge Integration | 20 err | Integration errors |

---

## HIGH SEVERITY INCONSISTENCIES

### I-003: Deprecated Files Still Present

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Category** | Code Organization |
| **Description** | 8 deprecated files remain in src/ |
| **Impact** | Confusion about which files are active; maintenance burden |

**Deprecated Files:**

| File | Replaced By | Lines |
|------|-------------|-------|
| main_legacy.py | main.py | ~400 |
| dashboard.py | dashboard_v2.py | ~400 |
| trading_engine.py | sniper.py | ~350 |
| learning_system.py | knowledge.py, reflection.py, adaptation.py | ~300 |
| market_data.py | market_feed.py | ~250 |
| risk_manager.py | sniper.py (partial) | ~200 |
| metrics.py | profitability.py | ~150 |
| volatility.py | (integrated) | ~100 |

**Total deprecated code:** ~2,150 lines

---

### I-004: Analysis Module Not Integrated

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Category** | Code Organization |
| **Description** | src/analysis/ has 4 files not called by any component |
| **Impact** | Dead code; potential useful functionality not available |

**Unused Files:**

| File | Purpose | Lines |
|------|---------|-------|
| analysis/__init__.py | Module init | ~10 |
| analysis/learning.py | Learning analysis | ~150 |
| analysis/metrics.py | Metrics analysis | ~100 |
| analysis/performance.py | Performance analysis | ~200 |

---

### I-005: Tests for Deprecated Components

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Category** | Testing |
| **Description** | Test files exist for deprecated components |
| **Impact** | Test suite failures; wasted CI time |

**Deprecated Test Files:**

| Test File | Tests For | Status |
|-----------|-----------|--------|
| test_trading_engine.py | trading_engine.py | 36 errors |
| test_learning_system.py | learning_system.py | 7 errors |
| test_dashboard.py | dashboard.py | May be deprecated |
| test_risk_manager.py | risk_manager.py | May be deprecated |
| test_market_data.py | market_data.py | Mixed |

---

## MEDIUM SEVERITY INCONSISTENCIES

### I-006: Coin Symbols Use Binance Format

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **Category** | Configuration |
| **Description** | coins.json uses BTCUSDT format but Bybit is primary exchange |
| **Impact** | Potential symbol mapping issues |

**Example:**
```json
// coins.json
"symbol": "BTCUSDT"

// But market_feed.py default exchange is Bybit
DEFAULT_EXCHANGE = "bybit"
```

---

### I-007: daily_summary.py Not Integrated

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **Category** | Code Organization |
| **Description** | daily_summary.py exists but not called by main system |
| **Impact** | Feature exists but unavailable |

---

### I-008: README Says 45 Coins, Config Has 20

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **Category** | Documentation |
| **Description** | README.md mentions "45-Coin Universe" but coins.json has 20 |
| **Impact** | Misleading documentation |

**README.md line 12:**
> 45-Coin Universe across 3 risk tiers (Blue Chips, Established, High Volatility)

**Actual:** 20 coins in config/coins.json

---

### I-009: SYSTEM-OVERVIEW Says Binance, System Uses Bybit

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **Category** | Documentation |
| **Description** | Documentation references Binance but default is Bybit |
| **Impact** | Misleading documentation |

**docs/architecture/SYSTEM-OVERVIEW.md line 60:**
> WebSocket connection to Binance, real-time price/kline data

**Actual:** market_feed.py defaults to Bybit

---

### I-010: Strategist Test Failures

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **Category** | Testing |
| **Description** | 13 strategist tests failing |
| **Impact** | Cannot verify Strategist behavior |

**Failing Tests:**
- test_calculate_take_profit_long
- test_generate_conditions
- test_generate_no_conditions
- test_generate_conditions_llm_error
- test_generate_conditions_invalid_json
- test_callback_notification
- (and 7 more)

---

## LOW SEVERITY INCONSISTENCIES

### I-011: Knowledge Integration Test Errors

| Field | Value |
|-------|-------|
| **Severity** | LOW |
| **Category** | Testing |
| **Description** | 20 errors in knowledge integration tests |
| **Impact** | Cannot verify knowledge integration |

**Note:** These may be import/mock errors rather than actual bugs.

---

### I-012: PHASE-2-INDEX.md File Missing

| Field | Value |
|-------|-------|
| **Severity** | LOW |
| **Category** | Documentation |
| **Description** | docs/specs/PHASE-2-INDEX.md does not exist |
| **Impact** | Broken link from other docs |

**Actual location:** docs/architecture/PHASE-2-INDEX.md

---

### I-013: Mixed Date Formats in Docs

| Field | Value |
|-------|-------|
| **Severity** | LOW |
| **Category** | Documentation |
| **Description** | Some docs use "February 3, 2026", others use "2026-02-03" |
| **Impact** | Inconsistent style |

---

### I-014: Sniper State File Path

| Field | Value |
|-------|-------|
| **Severity** | LOW |
| **Category** | Configuration |
| **Description** | docs mention sniper_state.json but path may vary |
| **Impact** | Minor confusion |

---

## SUMMARY TABLE

| ID | Severity | Category | Description |
|----|----------|----------|-------------|
| I-001 | CRITICAL | Documentation | 23 files reference main.py |
| I-002 | CRITICAL | Testing | 92 test failures/errors |
| I-003 | HIGH | Code | 8 deprecated files (~2150 lines) |
| I-004 | HIGH | Code | Analysis module unused |
| I-005 | HIGH | Testing | Tests for deprecated components |
| I-006 | MEDIUM | Configuration | Binance symbols with Bybit |
| I-007 | MEDIUM | Code | daily_summary.py unused |
| I-008 | MEDIUM | Documentation | 45 coins vs 20 coins |
| I-009 | MEDIUM | Documentation | Binance vs Bybit |
| I-010 | MEDIUM | Testing | 13 Strategist test failures |
| I-011 | LOW | Testing | 20 knowledge integration errors |
| I-012 | LOW | Documentation | Missing PHASE-2-INDEX.md |
| I-013 | LOW | Documentation | Mixed date formats |
| I-014 | LOW | Configuration | Sniper state path |

**Total Inconsistencies:** 14
- Critical: 2
- High: 3
- Medium: 5
- Low: 4

---

*See RECOMMENDATIONS.md for prioritized fixes.*
