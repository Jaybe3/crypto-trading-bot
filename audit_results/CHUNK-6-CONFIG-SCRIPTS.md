# CHUNK 6: Config, Scripts, Dashboard & Root Files Audit

**Date:** 2026-02-04
**Auditor:** Claude Code
**Scope:** 33 config, scripts, dashboard, and root files

---

## Executive Summary

The audit revealed **4 CRITICAL issues** and **9 MEDIUM issues**:

1. **Exchange configuration conflict**: coins.json says "binance_us" but settings.py uses "bybit"
2. **LLM model mismatch**: Different files reference different models (qwen2.5:14b vs qwen2.5-coder:7b)
3. **health.sh PID path mismatch**: Uses wrong PID file location
4. **README.md Tier 3 coin mismatch**: Lists wrong coins (PEPE, FLOKI vs NEAR, APT)

---

## File Inventory

| Category | Files | Issues Found |
|----------|-------|--------------|
| config/ | 3 | 2 CRITICAL |
| scripts/ (Shell) | 8 | 2 HIGH |
| scripts/ (Python) | 7 | 0 |
| dashboard/templates/ | 6 | 0 |
| dashboard/static/ | 2 | 0 |
| Root files | 7 | 4 MEDIUM |
| **TOTAL** | **33** | **8 ISSUES** |

---

## Issues by Severity

### CRITICAL Issues

| ID | File | Line | Issue | Fix |
|----|------|------|-------|-----|
| C001 | config/coins.json | 2 | `"exchange": "binance_us"` | System uses Bybit (settings.py:26) - DELETE file or update |
| C002 | config/coins.json | 27-31 | WebSocket URLs point to Binance | System uses Bybit - DELETE file |
| C003 | health.sh | 11 | Uses `$LOG_DIR/supervisord.pid` | Should use `/tmp/cryptobot-supervisord.pid` |
| C004 | health.sh | 24 | Checks `dashboard` status | supervisor.conf only has `trading_bot` program |

### HIGH Issues

| ID | File | Line | Issue | Fix |
|----|------|------|-------|-----|
| H001 | README.md | 171 | Tier 3 says "PEPE, FLOKI, BONK..." | Should be "NEAR, APT, ARB, OP, INJ" |
| H002 | .clinerules | 82 | Says `qwen2.5-coder:7b` | System uses `qwen2.5:14b` |

### MEDIUM Issues

| ID | File | Line | Issue | Fix |
|----|------|------|-------|-----|
| M001 | install.sh | 124 | References `qwen2.5-coder:7b` | Should be `qwen2.5:14b` |
| M002 | .clinerules | 70-78 | Risk limits reference deprecated `risk_manager.py`, `trading_engine.py`, `coin_config.py` | Update to Phase 2 locations |
| M003 | .clinerules | 127-141 | File organization lists deprecated modules | Update to Phase 2 structure |
| M004 | requirements.txt | - | Missing `pybit` for Bybit WebSocket | Add `pybit>=5.0.0` |
| M005 | requirements.txt | - | Missing `pytest-asyncio` for async tests | Add `pytest-asyncio>=0.23.0` |
| M006 | README.md | 189 | "Phase 3: Market Context Enhancement - Planned" | Phase 3 is COMPLETE (14/14 tasks) |
| M007 | README.md | 93 | `ollama pull qwen2.5:14b` in Quick Start | Matches code (OK), but install.sh says 7b |
| M008 | config/supervisor.conf | 33-34 | Comment says "dashboard.py removed" | Accurate (good) |
| M009 | pytest.ini | - | No test path or exclusions configured | Add `testpaths = tests` and ignore deprecated |

---

## File-by-File Analysis

### config/coins.json (CRITICAL - DEPRECATED)

**Status:** Should be DELETED

```json
{
  "exchange": "binance_us",    // WRONG - system uses Bybit
  "websocket": {
    "base_url": "wss://stream.binance.us:9443/stream"  // WRONG
  }
}
```

**Issues:**
- Line 2: `"exchange": "binance_us"` - System actually uses Bybit
- Lines 27-31: All WebSocket URLs point to Binance
- Lines 3-24: Coin list is correct (matches settings.py)

**Recommendation:** DELETE this file - settings.py is the authoritative source

---

### config/settings.py (OK)

**Status:** Authoritative configuration - CORRECT

```python
DEFAULT_EXCHANGE = os.getenv("TRADING_EXCHANGE", "bybit")  # Line 26 - CORRECT

TRADEABLE_COINS = [
    # Tier 1 - Blue chips
    "BTC", "ETH", "SOL", "BNB", "XRP",
    # Tier 2 - High volume
    "DOGE", "ADA", "AVAX", "LINK", "DOT",
    "MATIC", "UNI", "ATOM", "LTC", "ETC",
    # Tier 3 - More volatile
    "NEAR", "APT", "ARB", "OP", "INJ",
]  # 20 coins total - CORRECT
```

**Verified:**
- Exchange: Bybit ✅
- Coins: 20 total (5+10+5) ✅
- Paths: Correct ✅
- Risk settings: Present ✅

---

### config/supervisor.conf (OK)

**Status:** Correct configuration

```ini
[program:trading_bot]
command=python3 -u src/main.py --dashboard --port 8080  # Line 20 - CORRECT
```

**Verified:**
- Uses `src/main.py` (not deprecated main_legacy.py) ✅
- Dashboard built into main.py ✅
- Comment notes dashboard.py removed ✅
- PID file: `/tmp/cryptobot-supervisord.pid` ✅

---

### scripts/start.sh (OK)

**Status:** Correct

**Verified:**
- PID file path: `/tmp/cryptobot-supervisord.pid` ✅
- Ollama check at correct host ✅
- Uses supervisor.conf ✅

---

### scripts/stop.sh (OK)

**Status:** Correct - matches start.sh paths

---

### scripts/restart.sh (OK)

**Status:** Correct - calls stop.sh then start.sh

---

### scripts/status.sh (OK)

**Status:** Correct

**Verified:**
- PID file path matches start.sh ✅
- Database query uses correct module ✅

---

### scripts/health.sh (CRITICAL ISSUES)

**Status:** Has path mismatches

**Issues:**
- Line 11: `$LOG_DIR/supervisord.pid` - Should be `/tmp/cryptobot-supervisord.pid`
- Line 24: Checks `dashboard` program status - supervisor.conf only has `trading_bot`

**Fix:**
```bash
# Line 11 - Change:
if [ ! -f "/tmp/cryptobot-supervisord.pid" ]; then

# Line 16 - Change:
PID=$(cat "/tmp/cryptobot-supervisord.pid")

# Line 24 - Remove or comment out dashboard check
```

---

### scripts/install.sh (MEDIUM - Model Mismatch)

**Status:** Model reference incorrect

**Issues:**
- Line 124: "qwen2.5-coder:7b" should be "qwen2.5:14b"

**Fix:**
```bash
echo "Note: Uses local LLM (qwen2.5:14b) via Ollama - no API key needed!"
```

---

### scripts/performance.sh (OK)

**Status:** Correct

---

### scripts/start_paper_trading.sh (OK)

**Status:** Correct

**Verified:**
- Line 50: Checks for `qwen2.5:14b` ✅
- Line 158: Uses `python3 src/main.py` ✅

---

### scripts/autonomous_monitor.py (OK)

**Status:** Well-structured monitoring script

**Verified:**
- Uses correct imports ✅
- Database queries use proper tables ✅
- LLM interface usage correct ✅

---

### scripts/daily_checkpoint.py (OK)

**Status:** Correct API endpoints

**Verified API Calls:**
- `/api/health` ✅
- `/api/loop-stats` ✅
- `/api/profitability/snapshot` ✅
- `/api/adaptations/effectiveness` ✅
- `/api/conditions` ✅
- `/api/positions` ✅
- `/api/knowledge/*` ✅

---

### scripts/validate_learning.py (OK)

**Status:** Correct validation checks

---

### scripts/analyze_learning.py (OK)

**Status:** Correct database queries

---

### scripts/export_trades.py (OK)

**Status:** Correct export functionality

---

### scripts/generate_report.py (OK)

**Status:** Uses correct analysis modules

---

### scripts/analyze_performance.py (OK)

**Status:** Correct imports and functionality

---

### dashboard/templates/base.html (OK)

**Status:** Well-structured base template

**Verified:**
- Nav links: /, /knowledge, /adaptations, /profitability, /overrides ✅
- SSE connection to `/api/feed` ✅
- Balance and P&L updates ✅

---

### dashboard/templates/index.html (OK)

**Status:** Real-time view template correct

**Verified API Calls:**
- `/api/feed` (SSE) ✅
- `/api/conditions` ✅
- `/api/positions` ✅
- `/api/loop-stats` ✅

---

### dashboard/templates/knowledge.html (OK)

**Status:** Knowledge brain view correct

**Verified API Calls:**
- `/api/knowledge/coins` ✅
- `/api/knowledge/patterns` ✅
- `/api/knowledge/rules` ✅
- `/api/knowledge/blacklist` ✅

---

### dashboard/templates/adaptations.html (OK)

**Status:** Adaptations view correct

**Verified API Calls:**
- `/api/adaptations/effectiveness` ✅
- `/api/adaptations` ✅
- `/api/override/rollback` (POST) ✅

---

### dashboard/templates/profitability.html (OK)

**Status:** Profitability view correct

**Verified API Calls:**
- `/api/profitability/snapshot` ✅
- `/api/profitability/equity-curve` ✅
- `/api/profitability/by/{dimension}` ✅
- `/api/profitability/improvement` ✅

---

### dashboard/templates/overrides.html (OK)

**Status:** Manual overrides view correct

**Verified API Calls:**
- `/api/override/blacklist` (POST) ✅
- `/api/override/unblacklist` (POST) ✅
- `/api/override/disable-pattern` (POST) ✅
- `/api/override/enable-pattern` (POST) ✅
- `/api/override/deactivate-rule` (POST) ✅
- `/api/override/trigger-reflection` (POST) ✅
- `/api/override/pause` (POST) ✅
- `/api/override/resume` (POST) ✅
- `/api/notes` (GET/POST) ✅

---

### dashboard/static/js/dashboard.js (OK)

**Status:** Utility functions correct

**Functions:**
- `formatPrice()` - Price formatting ✅
- `formatCurrency()` - Currency formatting ✅
- `formatPercent()` - Percentage formatting ✅
- `formatRelativeTime()` - Relative time ✅
- `apiCall()` - API wrapper ✅
- `Toast` - Notifications ✅
- `Storage` - localStorage wrapper ✅

---

### dashboard/static/css/styles.css (OK)

**Status:** Custom styles correct

---

### pytest.ini (NEEDS UPDATE)

**Status:** Minimal configuration

**Current:**
```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
```

**Recommended:**
```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
testpaths = tests
ignore = tests/deprecated
```

---

### requirements.txt (MISSING DEPENDENCIES)

**Current (9 packages):**
```
requests>=2.28.0
flask>=2.3.0
pytest>=7.0.0
python-dateutil>=2.8.0
websockets>=12.0
fastapi>=0.109.0
uvicorn>=0.27.0
jinja2>=3.1.0
pydantic>=2.5.0
```

**Missing:**
```
pybit>=5.0.0           # Bybit WebSocket
pytest-asyncio>=0.23.0 # Async test support
httpx>=0.26.0          # For testing FastAPI
aiosqlite>=0.19.0      # Async SQLite (if used)
```

---

### .gitignore (OK)

**Status:** Comprehensive and correct

**Verified:**
- data/ ✅
- logs/ ✅
- __pycache__/ ✅
- .env ✅
- credentials ✅

---

### .clinerules (OUTDATED)

**Status:** References Phase 1 architecture

**Issues:**
- Line 70-78: Risk limits reference deprecated files (`risk_manager.py`, `trading_engine.py`, `coin_config.py`)
- Line 82: LLM model is `qwen2.5-coder:7b` (should be `qwen2.5:14b`)
- Line 127-141: File organization lists deprecated modules

**Fix:** Update to reflect Phase 2 architecture:
- `risk_manager.py` → Risk checks in `sniper.py`
- `trading_engine.py` → `sniper.py`
- `coin_config.py` → `config/settings.py`
- `learning_system.py` → `knowledge.py`, `reflection.py`, `adaptation.py`
- `dashboard.py` → `dashboard_v2.py`

---

### README.md (MULTIPLE ISSUES)

**Status:** Partially outdated

**Issues:**
| Line | Current | Should Be |
|------|---------|-----------|
| 171 | "Tier 3: PEPE, FLOKI, BONK..." | "Tier 3: NEAR, APT, ARB, OP, INJ" |
| 189 | "Phase 3: Planned" | "Phase 3: Complete (14/14 tasks)" |

**Correct Information:**
- Line 10: "Bybit" ✅
- Line 12: "20-Coin Universe" ✅
- Line 71: `qwen2.5:14b` ✅
- Architecture diagram: Accurate ✅

---

## Verification Against Code

### Exchange Configuration

| Source | Value | Correct? |
|--------|-------|----------|
| settings.py:26 | `"bybit"` | ✅ Authoritative |
| coins.json:2 | `"binance_us"` | ❌ WRONG |
| README.md:10 | "Bybit" | ✅ |

### LLM Model

| Source | Value | Correct? |
|--------|-------|----------|
| README.md:71 | `qwen2.5:14b` | ✅ Authoritative |
| start_paper_trading.sh:50 | `qwen2.5:14b` | ✅ |
| .clinerules:82 | `qwen2.5-coder:7b` | ❌ WRONG |
| install.sh:124 | `qwen2.5-coder:7b` | ❌ WRONG |

### Coin Configuration

| Source | Tier 3 Coins | Correct? |
|--------|--------------|----------|
| settings.py:39 | NEAR, APT, ARB, OP, INJ | ✅ Authoritative |
| coins.json:19-23 | NEAR, APT, ARB, OP, INJ | ✅ |
| README.md:171 | PEPE, FLOKI, BONK... | ❌ WRONG |

### PID File Path

| Source | Path | Correct? |
|--------|------|----------|
| start.sh:35 | `/tmp/cryptobot-supervisord.pid` | ✅ Authoritative |
| stop.sh:27 | `/tmp/cryptobot-supervisord.pid` | ✅ |
| status.sh:28 | `/tmp/cryptobot-supervisord.pid` | ✅ |
| health.sh:11 | `$LOG_DIR/supervisord.pid` | ❌ WRONG |

---

## API Endpoint Inventory

### Dashboard Templates → Backend

| Template | Endpoints Used |
|----------|---------------|
| base.html | `/api/feed` (SSE) |
| index.html | `/api/feed`, `/api/conditions`, `/api/positions`, `/api/loop-stats` |
| knowledge.html | `/api/knowledge/coins`, `/api/knowledge/patterns`, `/api/knowledge/rules`, `/api/knowledge/blacklist` |
| adaptations.html | `/api/adaptations`, `/api/adaptations/effectiveness`, `/api/override/rollback` |
| profitability.html | `/api/profitability/snapshot`, `/api/profitability/equity-curve`, `/api/profitability/by/{dim}`, `/api/profitability/improvement` |
| overrides.html | `/api/override/*`, `/api/notes`, `/api/knowledge/*` |

### Scripts → Backend

| Script | Endpoints Used |
|--------|---------------|
| daily_checkpoint.py | `/api/health`, `/api/loop-stats`, `/api/profitability/snapshot`, `/api/adaptations/effectiveness`, `/api/conditions`, `/api/positions`, `/api/knowledge/*` |
| validate_learning.py | `/api/knowledge/*`, `/api/adaptations`, `/api/loop-stats` |

---

## Recommendations

### P0 - Fix Immediately

1. **DELETE config/coins.json**
   - Settings.py is authoritative
   - coins.json references wrong exchange

2. **Fix health.sh PID path**
   ```bash
   # Change line 11:
   if [ ! -f "/tmp/cryptobot-supervisord.pid" ]; then
   # Change line 16:
   PID=$(cat "/tmp/cryptobot-supervisord.pid")
   # Remove lines 24-28 (dashboard check)
   ```

### P1 - Fix Soon

3. **Update .clinerules**
   - Update LLM model to qwen2.5:14b
   - Update file organization to Phase 2 structure
   - Update risk limit locations

4. **Update README.md**
   - Fix Tier 3 coin list (line 171)
   - Update Phase 3 status to "Complete" (line 189)

5. **Update install.sh**
   - Fix LLM model reference (line 124)

### P2 - Fix When Convenient

6. **Update requirements.txt**
   - Add missing dependencies

7. **Update pytest.ini**
   - Add testpaths and ignore deprecated

---

## Acceptance Criteria Status

| Criteria | Status |
|----------|--------|
| All 33 files documented | ✅ 33/33 |
| Config conflicts identified | ✅ coins.json vs settings.py |
| Shell script paths verified | ✅ health.sh has issues |
| API endpoints matched | ✅ All endpoints verified |
| LLM model consistency checked | ✅ Mismatches found |
| Exchange configuration verified | ✅ Conflict found |
| CHUNK-6-CONFIG-SCRIPTS.md created | ✅ |

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Files Audited | 33 |
| Critical Issues | 4 |
| High Issues | 2 |
| Medium Issues | 9 |
| Files OK | 24 |

---

## Conclusion

The configuration and scripts layer has several inconsistencies stemming from the Phase 1 → Phase 2 transition:

1. **config/coins.json** should be deleted - it's a Phase 1 artifact that references Binance instead of Bybit

2. **health.sh** has critical bugs - wrong PID path and references non-existent dashboard program

3. **LLM model references** are inconsistent - some files say `qwen2.5-coder:7b`, others say `qwen2.5:14b`

4. **.clinerules** is severely outdated - still describes Phase 1 architecture

5. **Dashboard templates and scripts** are well-maintained and consistent with the API

**Recommended action:** Prioritize fixing health.sh and deleting coins.json before next deployment.

---

*Audit completed: 2026-02-04*
*Auditor: Claude Code*
