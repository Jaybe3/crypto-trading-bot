# CHUNK 7a - Cross-Reference Matrices (Part 1)

## Matrix 1: Import Matrix

**Total internal imports analyzed:** 146

### Missing Imports (1 found)

| File | Import | Status |
|------|--------|--------|
| src/dashboard_v2.py | from src.main_v2 import TradingSystem | **MISSING** |

**Issue:** `src/main_v2.py` does not exist. The dashboard_v2 module references a non-existent main_v2 module.

### Duplicate Import Patterns

The following files have duplicate imports (same module imported multiple times):
- `src/adaptation.py`: Duplicates `Database`, `KnowledgeBrain`, `CoinScorer`, `PatternLibrary`, `Insight`
- `src/quick_update.py`: Duplicates `Database`, `CoinScorer`, `PatternLibrary`

### Import Verification Summary
- Valid imports: **145**
- Missing imports: **1**
- Files with syntax errors: **0**

---

## Matrix 2: Call Chain Analysis

### Chain 1: Main Loop (main.py → strategist.py → llm_interface.py)

| Step | File | Line | Method Call |
|------|------|------|-------------|
| 1 | main.py | 226 | `await self.strategist.start()` |
| 2 | main.py | 388 | `self.strategist.subscribe_conditions(self._on_new_conditions)` |
| 3 | main.py | 530 | `await self.strategist.stop()` |
| 4 | strategist.py | 174 | `async def generate_conditions()` - **DEFINED** |
| 5 | strategist.py | 210 | `response = self.llm.query(prompt, system_prompt)` |

**Status:** COMPLETE - Chain flows from main → strategist → LLM interface

---

### Chain 2: Trade Execution (main.py → sniper.py → journal.py → database)

| Step | File | Lines | Operations |
|------|------|-------|------------|
| 1 | main.py | 289-395 | sniper.load_state(), subscribe(), on_price_tick() |
| 2 | main.py | 429 | `active_count = self.sniper.set_conditions(conditions)` |
| 3 | sniper.py | 421 | `self.journal.record_entry(position, timestamp)` |
| 4 | sniper.py | 547 | `self.journal.record_exit(position, price, timestamp, reason, pnl)` |
| 5 | journal.py | 392-608 | `self.db.insert()`, `self.db.update()`, `self.db.query()` |

**Status:** COMPLETE - Full chain: entry signal → sniper execution → journal recording → database persistence

---

### Chain 3: Learning Loop (main.py → reflection.py → knowledge.py → adaptation.py → strategist.py)

| Step | File | Lines | Operations |
|------|------|-------|------------|
| 1 | main.py | 198-791 | reflection_engine initialization, start(), stop(), reflect() |
| 2 | reflection.py | 117-268 | Uses `self.adaptation_engine.apply_insights(insights)` |
| 3 | reflection.py | 114 | `self.knowledge = knowledge` |
| 4 | strategist.py | 315-421 | Uses knowledge for coin scores, rules, patterns |

**Status:** COMPLETE - Learning loop closes: trades → reflection → insights → adaptation → knowledge → strategist

---

### Chain 4: Coin Scoring (coin_scorer.py ↔ main.py)

| Step | File | Lines | Operations |
|------|------|-------|------------|
| 1 | coin_scorer.py | 22-25 | Status definitions: BLACKLISTED, REDUCED, NORMAL, FAVORED |
| 2 | coin_scorer.py | 42-44 | Thresholds: BLACKLIST_WIN_RATE=0.30, REDUCED=0.45, FAVORED=0.60 |
| 3 | coin_scorer.py | 154 | `def check_thresholds(self, coin)` - threshold checking |
| 4 | coin_scorer.py | 106-118 | Status determination logic |
| 5 | main.py | 262-322 | CoinScorer instantiation and injection into strategist, quick_update, adaptation |

**Status:** COMPLETE - Scoring flows back into trading decisions

---

## Matrix 3: Config Value Matrix

### Unused Config Values (Dead Config)

| Config Constant | Status |
|-----------------|--------|
| PROJECT_ROOT | NOT USED in src/ |
| DATA_DIR | NOT USED in src/ |
| LOGS_DIR | NOT USED in src/ |
| COIN_TIERS | NOT USED in src/ |
| MAX_POSITION_PER_COIN | NOT USED in src/ |
| DEFAULT_STOP_LOSS_PCT | NOT USED in src/ |
| DEFAULT_TAKE_PROFIT_PCT | NOT USED in src/ |
| DEFAULT_POSITION_SIZE_USD | NOT USED in src/ |
| STRATEGIST_MAX_CONDITIONS | NOT USED in src/ |
| STRATEGIST_CONDITION_TTL | NOT USED in src/ |
| DATABASE_PATH | NOT USED in src/ |

**Total dead config:** 11 constants

### Config with Local Fallbacks

Several configs are imported but have local fallback definitions in `main.py`:

| Config | main.py Fallback | Line |
|--------|------------------|------|
| TRADEABLE_COINS | ["BTC", "ETH", "SOL"] | 53 |
| DEFAULT_EXCHANGE | "bybit" | 54 |
| INITIAL_BALANCE | 10000.0 | 55 |
| STALE_DATA_THRESHOLD | 5 | 56 |
| STATUS_LOG_INTERVAL | 60 | 57 |
| SNIPER_STATE_PATH | "data/sniper_state.json" | 58 |
| STRATEGIST_INTERVAL | 180 | 59 |
| STRATEGIST_ENABLED | True | 60 |

### Hardcoded Values That Should Be Config

| File | Line | Hardcoded Value | Recommended Config |
|------|------|-----------------|-------------------|
| sniper.py | 102 | MAX_POSITIONS = 5 | Should use MAX_POSITIONS from config |
| sniper.py | 104 | MAX_EXPOSURE_PCT = 0.10 | Should use MAX_EXPOSURE_PCT from config |
| coin_scorer.py | 42 | BLACKLIST_WIN_RATE = 0.30 | Should be in config |
| coin_scorer.py | 43 | REDUCED_WIN_RATE = 0.45 | Should be in config |
| coin_scorer.py | 44 | FAVORED_WIN_RATE = 0.60 | Should be in config |

---

## Summary

| Category | Count |
|----------|-------|
| Internal imports verified | 146 |
| Missing imports | 1 |
| Duplicate imports (redundant) | 8 |
| Call chain breaks | 0 |
| Call chains verified complete | 4 |
| Dead config constants | 11 |
| Hardcoded values needing config | 5 |
| Config with local fallbacks | 8 |

### Critical Issues

1. **MISSING IMPORT:** `src/dashboard_v2.py` imports from non-existent `src/main_v2.py`
2. **11 DEAD CONFIG VALUES** in config/settings.py that are never used

### Recommendations

1. Either create `src/main_v2.py` or remove the import from `dashboard_v2.py`
2. Remove or document the 11 unused config constants
3. Move hardcoded thresholds in `sniper.py` and `coin_scorer.py` to config
4. Clean up duplicate imports in `adaptation.py` and `quick_update.py`

---

## Acceptance Criteria Checklist

- [x] extract_imports.py ran successfully
- [x] import_matrix_raw.txt created (146 lines)
- [x] call_chains.txt created
- [x] config_usage.txt created
- [x] CHUNK-7a-MATRICES.md summarizes findings
