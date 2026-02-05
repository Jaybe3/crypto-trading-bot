# AUDIT-FINAL-COMPLETE.md

## Crypto Trading Bot - Complete Code Audit Report

**Audit Date:** 2026-02-04
**Auditor:** Claude Code
**Repository:** crypto-trading-bot
**Total Files:** 191
**Files Audited:** 191 (100%)

---

## Chunk Completion Status

| Chunk | File | Complete | Issues Found |
|-------|------|----------|--------------|
| 1 | CHUNK-1-SRC-ROOT.md | ✅ | 11 |
| 2 | CHUNK-2-SRC-SUBDIRS.md | ✅ | 5 |
| 3 | CHUNK-3-TESTS.md | ✅ | 4 |
| 4 | CHUNK-4-DOCS.md | ✅ | 22 |
| 5 | CHUNK-5-TASKS.md | ✅ | 29 |
| 6 | CHUNK-6-CONFIG-SCRIPTS.md | ✅ | 15 |
| 7 | CHUNK-7a/7b-MATRICES.md | ✅ | 17 |
| 8 | CHUNK-8-TOOL-ANALYSIS.md | ✅ | 19 |
| 9 | CHUNK-9-DATABASE.md | ✅ | 10 |

**ALL CHUNKS COMPLETE**

---

## Complete Issue List (Deduplicated)

### CRITICAL Issues (8)

| ID | Chunk | File | Line | Category | Description |
|----|-------|------|------|----------|-------------|
| 001 | 1,2,7 | main.py, strategist.py | - | INTEGRATION | Phase 3 Intelligence Layer not integrated (13 modules dormant) |
| 002 | 1 | coin_scorer.py | 211 | LOGIC | FAVORED demotion bug - doesn't check P&L, only win_rate |
| 003 | 2 | technical/funding.py, candle_fetcher.py | 73-94 | CONFIG | SYMBOL_MAP missing 5 Tier 3 coins (APT, ARB, INJ, NEAR, OP) |
| 004 | 7,9 | analysis/learning.py | 377,398 | SCHEMA | Queries non-existent `insights` table |
| 005 | 9 | analysis/learning.py | 155-158 | SCHEMA | Queries 7 non-existent columns in adaptations table |
| 006 | 8 | quick_update.py | 46,69 | CODE | Undefined name 'ReflectionEngine' |
| 007 | 7 | dashboard_v2.py | - | INTEGRATION | Imports from non-existent main_v2.py |
| 008 | 6 | config/coins.json | 2 | CONFIG | Wrong exchange "binance_us" (system uses Bybit) |

### HIGH Issues (8)

| ID | Chunk | File | Line | Category | Description |
|----|-------|------|------|----------|-------------|
| 009 | 1 | strategist.py | 548-636 | INTEGRATION | _build_prompt() missing Phase 3 data |
| 010 | 2 | technical/manager.py | 443 | LOGIC | _get_funding calls non-existent method get_funding_rate() |
| 011 | 3 | - | - | TEST | No Phase 3 integration tests |
| 012 | 4 | SYSTEM-STATE.md | 88 | DOC | Contradicts itself about Phase 3 status |
| 013 | 4 | 8+ files | various | DOC | Exchange references say "Binance" (should be Bybit) |
| 014 | 4 | 6+ files | various | DOC | Coin count says "45" (actual: 20) |
| 015 | 6 | health.sh | 11,24 | CONFIG | Wrong PID path and checks non-existent dashboard program |
| 016 | 8 | 8 functions | various | COMPLEXITY | 8 functions with D-grade complexity (>20) |

### MEDIUM Issues (21)

| ID | Chunk | File | Category | Description |
|----|-------|------|----------|-------------|
| 017 | 1 | database.py | DEAD | 20+ potentially unused methods |
| 018 | 1 | main_legacy.py, trading_engine.py, dashboard.py | DEAD | 3 deprecated files still present |
| 019 | 2 | funding.py, candle_fetcher.py | STYLE | Duplicate SYMBOL_MAP definitions |
| 020 | 4 | DEVELOPMENT.md | DOC | Severely outdated - references Phase 1 |
| 021 | 4 | TASKS.md | DOC | Shows Phase 1.5 as current (Phase 2 complete) |
| 022 | 5 | backlog/phase-3-intelligence/ | ORG | 14 completed tasks in wrong directory |
| 023 | 5 | completed/TASK-150.md | ORG | Status "READY" but in completed/ |
| 024 | 5 | INDEX.md | ORG | References 3 non-existent directories |
| 025 | 5 | 24 task files | STYLE | 7 different status formats used |
| 026 | 6 | .clinerules | CONFIG | LLM model wrong (7b vs 14b) |
| 027 | 6 | install.sh | CONFIG | LLM model wrong (7b vs 14b) |
| 028 | 6 | README.md | DOC | Tier 3 coins wrong (PEPE vs NEAR) |
| 029 | 6 | requirements.txt | CONFIG | Missing pybit, pytest-asyncio dependencies |
| 030 | 7 | settings.py | CONFIG | 11 dead config constants never used |
| 031 | 7 | sniper.py, coin_scorer.py | CONFIG | Hardcoded values that should be config |
| 032 | 8 | quick_update.py | CODE | Redefinition of 'time' variable |
| 033 | 8 | volatility.py | CODE | f-strings missing placeholders |
| 034 | 8 | journal.py | TYPE | no '__dataclass_fields__' member access |
| 035 | 8 | 15 files | STYLE | Unused imports to remove |
| 036 | 9 | database.py | SCHEMA | No foreign key constraints (4 relationships) |
| 037 | 9 | database.py | SCHEMA | No schema versioning |

### LOW Issues (25)

| ID | Chunk | Category | Description |
|----|-------|----------|-------------|
| 038 | 1 | STYLE | Repeated guard patterns in main.py |
| 039 | 1 | STYLE | F-string logging (~200 instances) |
| 040 | 1 | STYLE | Missing type hints in various files |
| 041 | 3 | TEST | Deprecated test files (35+ failing) |
| 042 | 3 | DOC | Some test files missing docstrings |
| 043 | 4 | DOC | Multiple minor documentation inaccuracies |
| 044 | 6 | CONFIG | pytest.ini missing testpaths config |
| 045 | 8 | SECURITY | SQL f-string construction (low actual risk) |
| 046 | 8 | SECURITY | Bind to 0.0.0.0 (intentional) |
| 047 | 8 | STYLE | ~40 line-too-long violations |
| 048 | 8 | STYLE | ~30 wrong-import-position violations |
| 049 | 8 | STYLE | ~25 broad-exception-caught warnings |
| 050 | 8 | STYLE | 8 ambiguous variable names ('l') |
| 051 | 8 | TYPE | 10 missing type stubs for requests |
| 052-062 | Various | Various | Additional style/doc issues |

---

## Issues by Category

### INTEGRATION (4 issues)
| ID | File | Description |
|----|------|-------------|
| 001 | main.py, strategist.py | Phase 3 not integrated (13 modules) |
| 007 | dashboard_v2.py | Imports non-existent main_v2.py |
| 009 | strategist.py | _build_prompt() missing Phase 3 data |
| 011 | tests/ | No Phase 3 integration tests |

### CONFIG (8 issues)
| ID | File | Description |
|----|------|-------------|
| 003 | technical/*.py | SYMBOL_MAP missing 5 coins |
| 008 | coins.json | Wrong exchange |
| 015 | health.sh | Wrong PID path |
| 026 | .clinerules | LLM model wrong |
| 027 | install.sh | LLM model wrong |
| 029 | requirements.txt | Missing dependencies |
| 030 | settings.py | 11 dead config constants |
| 031 | sniper.py, coin_scorer.py | Hardcoded values |

### LOGIC (2 issues)
| ID | File | Description |
|----|------|-------------|
| 002 | coin_scorer.py:211 | FAVORED demotion bug |
| 010 | technical/manager.py:443 | Wrong method call |

### SCHEMA (4 issues)
| ID | File | Description |
|----|------|-------------|
| 004 | analysis/learning.py | Missing insights table |
| 005 | analysis/learning.py | Missing 7 columns |
| 036 | database.py | No FK constraints |
| 037 | database.py | No schema versioning |

### DOC (7 issues)
| ID | File | Description |
|----|------|-------------|
| 012 | SYSTEM-STATE.md | Phase 3 contradiction |
| 013 | 8+ files | Exchange says Binance |
| 014 | 6+ files | Coin count says 45 |
| 020 | DEVELOPMENT.md | Severely outdated |
| 021 | TASKS.md | Phase status wrong |
| 028 | README.md | Tier 3 coins wrong |
| 043 | Various | Minor inaccuracies |

### CODE (3 issues)
| ID | File | Description |
|----|------|-------------|
| 006 | quick_update.py | Undefined ReflectionEngine |
| 032 | quick_update.py | Redefinition of time |
| 033 | volatility.py | f-string placeholders |

### DEAD (2 issues)
| ID | File | Description |
|----|------|-------------|
| 017 | database.py | 20+ unused methods |
| 018 | 3 files | Deprecated files present |

### TEST (2 issues)
| ID | File | Description |
|----|------|-------------|
| 011 | tests/ | No Phase 3 integration tests |
| 041 | tests/deprecated/ | 35+ failing tests |

### COMPLEXITY (1 issue)
| ID | File | Description |
|----|------|-------------|
| 016 | 8 functions | D-grade complexity (>20) |

### STYLE (10+ issues)
Various formatting, import, and naming issues.

### TYPE (2 issues)
| ID | File | Description |
|----|------|-------------|
| 034 | journal.py | dataclass_fields access |
| 051 | 10 files | Missing type stubs |

### ORG (4 issues)
| ID | File | Description |
|----|------|-------------|
| 022 | backlog/ | 14 tasks in wrong directory |
| 023 | TASK-150.md | Wrong location |
| 024 | INDEX.md | Non-existent directory refs |
| 025 | 24 task files | Status format drift |

---

## Issues by Severity

### CRITICAL (Fix immediately) - 8 issues

| ID | File | Description | Fix |
|----|------|-------------|-----|
| 001 | main.py, strategist.py | Phase 3 not integrated | Import ContextManager, TechnicalManager; call to_prompt() |
| 002 | coin_scorer.py:211 | FAVORED demotion bug | Add `or score.total_pnl <= 0` condition |
| 003 | technical/*.py | SYMBOL_MAP missing coins | Add NEAR, APT, ARB, OP, INJ to SYMBOL_MAP |
| 004 | analysis/learning.py | Missing insights table | Change to reflections table or add insights table |
| 005 | analysis/learning.py | Missing 7 columns | Update queries to use actual column names |
| 006 | quick_update.py | Undefined ReflectionEngine | Add missing import |
| 007 | dashboard_v2.py | Missing main_v2.py | Remove import or create module |
| 008 | config/coins.json | Wrong exchange | DELETE file (settings.py is authoritative) |

### HIGH (Fix before deployment) - 8 issues

| ID | File | Description | Fix |
|----|------|-------------|-----|
| 009 | strategist.py | Missing Phase 3 in prompt | Add context_manager.to_prompt() after #001 fixed |
| 010 | technical/manager.py:443 | Wrong method call | Change get_funding_rate() to get_current() |
| 011 | tests/ | No Phase 3 integration tests | Add tests after #001 fixed |
| 012 | SYSTEM-STATE.md:88 | Phase 3 contradiction | Update to "IMPLEMENTED BUT NOT INTEGRATED" |
| 013 | 8+ docs | Exchange says Binance | Global find/replace Binance → Bybit |
| 014 | 6+ docs | Coin count says 45 | Global find/replace 45 → 20 |
| 015 | health.sh | Wrong paths | Fix PID path and remove dashboard check |
| 016 | 8 functions | High complexity | Refactor calculate_metrics, _analyze_by_time, etc. |

### MEDIUM (Fix within 1 week) - 21 issues

| ID | File | Description | Fix |
|----|------|-------------|-----|
| 017 | database.py | Unused methods | Document as API surface or remove |
| 018 | 3 deprecated files | Still present | Move to deprecated/ or delete |
| 019 | technical/*.py | Duplicate SYMBOL_MAP | Centralize to one location |
| 020-037 | Various | Various | See individual chunk reports |

### LOW (Fix when convenient) - 25+ issues

Style, documentation, and minor issues. See CHUNK reports for details.

---

## Fix Plan

### Issue #001: Phase 3 Not Integrated

**File:** src/main.py, src/strategist.py
**Category:** INTEGRATION
**Impact:** 13 fully-built modules are dormant

**Current Code (main.py):**
```python
# Missing imports and initialization
self.strategist = Strategist(
    llm=self.llm,
    market_feed=self.market_feed,
    # ... no context_manager or technical_manager
)
```

**Fixed Code:**
```python
# Add imports at top
from src.sentiment.context_manager import ContextManager
from src.technical.manager import TechnicalManager

# In TradingSystem.__init__():
self.context_manager = ContextManager()
self.technical_manager = TechnicalManager(CandleFetcher())

# Pass to Strategist
self.strategist = Strategist(
    llm=self.llm,
    market_feed=self.market_feed,
    context_manager=self.context_manager,
    technical_manager=self.technical_manager,
    # ...
)
```

**Why:** The Intelligence Layer (Phase 3) represents significant development effort that's completely unused. The LLM makes trading decisions without RSI, VWAP, ATR, funding rates, fear/greed index, or news sentiment.

---

### Issue #002: FAVORED Demotion Logic Bug

**File:** src/coin_scorer.py
**Line:** 211
**Category:** LOGIC

**Current Code:**
```python
elif (score.win_rate < FAVORED_WIN_RATE and
      current_status == CoinStatus.FAVORED):
    return CoinStatus.NORMAL
```

**Fixed Code:**
```python
elif ((score.win_rate < FAVORED_WIN_RATE or score.total_pnl <= 0) and
      current_status == CoinStatus.FAVORED):
    return CoinStatus.NORMAL
```

**Why:** A coin can stay FAVORED while losing money if win rate stays above 60%. Promotion requires both high win rate AND positive P&L, but demotion only checks win rate.

---

### Issue #003: SYMBOL_MAP Missing Tier 3 Coins

**Files:** src/technical/funding.py, src/technical/candle_fetcher.py
**Lines:** 73-94 in both files
**Category:** CONFIG

**Current Code:**
```python
SYMBOL_MAP = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", # ...
    "PEPE": "PEPEUSDT", "FLOKI": "FLOKIUSDT",  # Extra meme coins
    # Missing: NEAR, APT, ARB, OP, INJ
}
```

**Fixed Code:**
```python
SYMBOL_MAP = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT",
    "BNB": "BNBUSDT", "XRP": "XRPUSDT",
    "DOGE": "DOGEUSDT", "ADA": "ADAUSDT", "AVAX": "AVAXUSDT",
    "LINK": "LINKUSDT", "DOT": "DOTUSDT", "MATIC": "MATICUSDT",
    "UNI": "UNIUSDT", "ATOM": "ATOMUSDT", "LTC": "LTCUSDT", "ETC": "ETCUSDT",
    # Tier 3
    "NEAR": "NEARUSDT", "APT": "APTUSDT", "ARB": "ARBUSDT",
    "OP": "OPUSDT", "INJ": "INJUSDT",
}
```

**Why:** 5 tradeable coins (Tier 3) cannot get technical indicators because they're not in SYMBOL_MAP.

---

### Issue #004: Missing `insights` Table

**File:** src/analysis/learning.py
**Lines:** 377, 383, 398
**Category:** SCHEMA

**Current Code:**
```python
cursor.execute("SELECT COUNT(*) FROM insights WHERE created_at >= ?", (cutoff,))
```

**Fixed Code (Option 1 - Use reflections table):**
```python
cursor.execute("SELECT COUNT(*) FROM reflections WHERE created_at >= ?", (cutoff,))
```

**Fixed Code (Option 2 - Add insights table to database.py):**
```python
cursor.execute("""
    CREATE TABLE IF NOT EXISTS insights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        insight_type TEXT NOT NULL,
        content TEXT NOT NULL,
        confidence REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
```

**Why:** Runtime crash when analyze_knowledge_growth() is called.

---

### Issue #005: Missing Columns in adaptations Query

**File:** src/analysis/learning.py
**Lines:** 155-158
**Category:** SCHEMA

**Current Code:**
```python
cursor.execute("""
    SELECT adaptation_id, action, target, confidence, effectiveness_rating,
           win_rate_before, win_rate_after, pnl_before, pnl_after, applied_at
    FROM adaptations
    ORDER BY applied_at DESC
""")
```

**Fixed Code:**
```python
cursor.execute("""
    SELECT adaptation_id, action, target, insight_confidence, effectiveness,
           pre_metrics, post_metrics, timestamp
    FROM adaptations
    ORDER BY timestamp DESC
""")
# Then parse pre_metrics/post_metrics JSON for win_rate and pnl values
```

**Why:** Query uses 7 column names that don't exist in schema, causing runtime crash.

---

### Issue #006: Undefined ReflectionEngine

**File:** src/quick_update.py
**Lines:** 46, 69
**Category:** CODE

**Current Code:**
```python
# Line 46, 69 - uses ReflectionEngine without import
```

**Fixed Code:**
```python
# Add at top of file
from src.reflection import ReflectionEngine
```

**Why:** Flake8 F821 undefined name error.

---

### Issue #007: Missing main_v2.py

**File:** src/dashboard_v2.py
**Category:** INTEGRATION

**Current Code:**
```python
from src.main_v2 import TradingSystem
```

**Fixed Code (Option 1 - Remove import):**
```python
# Remove the import line if not needed
```

**Fixed Code (Option 2 - Use main.py):**
```python
from src.main import TradingSystem
```

**Why:** dashboard_v2.py imports from non-existent module.

---

### Issue #008: Wrong Exchange in coins.json

**File:** config/coins.json
**Category:** CONFIG

**Fix:**
```bash
rm config/coins.json
```

**Why:** File says "binance_us" but system uses Bybit. settings.py is authoritative. DELETE the file.

---

### Issue #010: Wrong Method Call in TechnicalManager

**File:** src/technical/manager.py
**Line:** 443
**Category:** LOGIC

**Current Code:**
```python
return self.funding.get_funding_rate(coin)
```

**Fixed Code:**
```python
return self.funding.get_current(coin)
```

**Why:** Method doesn't exist; will cause AttributeError when Phase 3 is integrated.

---

### Issue #015: health.sh Path Mismatch

**File:** scripts/health.sh
**Lines:** 11, 16, 24
**Category:** CONFIG

**Current Code:**
```bash
if [ ! -f "$LOG_DIR/supervisord.pid" ]; then
PID=$(cat "$LOG_DIR/supervisord.pid")
# Line 24: checks dashboard program
```

**Fixed Code:**
```bash
if [ ! -f "/tmp/cryptobot-supervisord.pid" ]; then
PID=$(cat "/tmp/cryptobot-supervisord.pid")
# Remove dashboard check (program doesn't exist in supervisor.conf)
```

**Why:** Path doesn't match start.sh; dashboard program removed from supervisor.conf.

---

## Final Statistics

### Files
| Metric | Value |
|--------|-------|
| Total files in repository | 191 |
| Files audited | 191 |
| Files with issues | 67 |
| Files with no issues | 124 |

### Issues
| Severity | Count |
|----------|-------|
| Critical | 8 |
| High | 8 |
| Medium | 21 |
| Low | 25+ |
| **Total** | **62+** |

### By Category
| Category | Count |
|----------|-------|
| INTEGRATION | 4 |
| CONFIG | 8 |
| LOGIC | 2 |
| SCHEMA | 4 |
| DOC | 7 |
| CODE | 3 |
| DEAD | 2 |
| TEST | 2 |
| COMPLEXITY | 1 |
| STYLE | 10+ |
| TYPE | 2 |
| ORG | 4 |

### Code Quality Metrics
| Metric | Value |
|--------|-------|
| Test coverage | 64% (line) / 96.4% (docstring) |
| Average complexity | A (3.6) |
| D-grade functions | 8 |
| Dead code items | ~15-20 definite, ~80 false positives |
| Unused imports | 15 |
| Security issues | 0 High/Critical, 12 Medium (all low risk) |

### Automated Tool Summary
| Tool | Findings | Critical |
|------|----------|----------|
| Vulture | 206 | 2 |
| Pylint | ~700 | 2 |
| Mypy | 11 | 0 |
| Bandit | 22 | 0 |
| Radon | 12 D-grade | 8 |
| Flake8 | 397 | 4 |

---

## Audit Sign-Off

### Verification
- [x] All 191 files reviewed
- [x] All automated tools run (vulture, pylint, mypy, bandit, radon, flake8, coverage, interrogate)
- [x] All matrices complete (imports, calls, config, coins, queries, thresholds, Phase 3)
- [x] All issues documented (62+)
- [x] All critical/high issues have fix plans (16 fix plans)
- [x] No sections marked TODO

### Auditor Statement
I confirm this audit reviewed 100% of the repository files.
Every file was read in full. Every issue was documented.

**Completed:** 2026-02-04
**Auditor:** Claude Code

---

## Appendix: File Counts by Directory

| Directory | Files | Issues |
|-----------|-------|--------|
| src/ (root) | 27 | 11 |
| src/models/ | 6 | 0 |
| src/analysis/ | 4 | 2 |
| src/sentiment/ | 6 | 0 |
| src/technical/ | 10 | 2 |
| tests/ | 45 | 4 |
| docs/ | ~45 | 22 |
| tasks/ | 40 | 29 |
| config/ | 3 | 2 |
| scripts/ | 15 | 2 |
| dashboard/ | 8 | 0 |
| root files | 7 | 4 |

---

## Quick Reference: Most Critical Files

| File | Issues | Severity |
|------|--------|----------|
| src/main.py | 1 | CRITICAL |
| src/strategist.py | 2 | CRITICAL + HIGH |
| src/coin_scorer.py | 1 | CRITICAL |
| src/analysis/learning.py | 2 | CRITICAL |
| src/quick_update.py | 2 | CRITICAL + MEDIUM |
| src/dashboard_v2.py | 1 | CRITICAL |
| config/coins.json | 1 | CRITICAL (delete) |
| src/technical/manager.py | 1 | HIGH |
| scripts/health.sh | 1 | HIGH |

---

*Audit Report Complete*
*Generated: 2026-02-04*
*Auditor: Claude Code*
