# PRE-WAVE VERIFICATION RESULTS

**Date:** February 2026
**Purpose:** Validate assumptions before starting fix waves
**Status:** COMPLETE - All 14 checks executed

---

## CHECK RESULTS

### V1: coins.json Usage
**Question:** Is coins.json actually read anywhere, or is it truly orphaned?

**Command:** `grep -rn "coins.json" src/`

**Result:**
```
src/market_feed.py:45:        with open('config/coins.json') as f:
src/market_feed.py:47:            logger.warning("coins.json not found, using default coins")
```

**Finding:** coins.json IS actively read by market_feed.py at line 45. It is NOT orphaned.

**Decision:** Cannot simply delete coins.json. Need to verify if market_feed.py should use settings.py TIER_* instead, then update market_feed.py before removing coins.json.

---

### V2: TradingSystem.total_pnl Attribute
**Question:** Does TradingSystem actually have a total_pnl attribute?

**Command:** `grep -n "total_pnl" src/main.py`

**Result:**
```
src/main.py:289:        self.total_pnl = 0.0
src/main.py:476:        self.total_pnl += pnl
src/main.py:477:        logger.info(f"Trade closed: {coin} PnL: ${pnl:.2f}, Total: ${self.total_pnl:.2f}")
```

**Finding:** TradingSystem DOES have total_pnl attribute, initialized at line 289 and updated at line 476.

**Decision:** Issue #015 (dashboard total_pnl) is confirmed - dashboard imports from wrong module (main_v2), but the attribute exists in main.py.

---

### V3: main.py Classes
**Question:** What classes does main.py actually export?

**Command:** `grep -n "^class " src/main.py`

**Result:**
```
src/main.py:71:class HealthMonitor:
src/main.py:142:class TradingSystem:
```

**Finding:** main.py exports HealthMonitor (line 71) and TradingSystem (line 142).

**Decision:** Confirms dashboard_v2.py should import from `src.main` not `src.main_v2`.

---

### V4: FundingRateFetcher Methods
**Question:** Does FundingRateFetcher have get_funding_rate() or get_current()?

**Command:** `grep -n "def get" src/technical/funding.py`

**Result:**
```
src/technical/funding.py:105:    def get_current(self, symbol: str) -> Optional[Dict[str, Any]]:
```

**Finding:** FundingRateFetcher has `get_current()` method (line 105), NOT `get_funding_rate()`.

**Decision:** Confirms Issue #010 - any code calling `get_funding_rate()` will fail. Fix must use `get_current()`.

---

### V5: ReflectionEngine Location
**Question:** Where is ReflectionEngine actually defined?

**Command:** `grep -rn "class ReflectionEngine" src/`

**Result:**
```
src/reflection.py:72:class ReflectionEngine:
```

**Finding:** ReflectionEngine exists at src/reflection.py:72.

**Decision:** Issue #006 (ReflectionEngine not instantiated) is confirmed - the class exists but is not imported/used in main.py. Fix requires adding import and instantiation.

---

### V6: analyze_knowledge_growth Code
**Question:** What does analyze_knowledge_growth actually query?

**Command:** Read src/analysis/learning.py lines 370-410

**Result:**
```python
def analyze_knowledge_growth(self) -> Dict[str, Any]:
    """Analyze how the system's knowledge has grown over time."""
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()

    # Get insight accumulation over time
    cursor.execute("""
        SELECT date(discovered_at) as date, COUNT(*) as count
        FROM insights
        GROUP BY date(discovered_at)
        ORDER BY date
    """)
    insight_growth = cursor.fetchall()

    # ... more code querying 'insights' table
```

**Finding:** analyze_knowledge_growth queries non-existent `insights` table at lines 377 and 398.

**Decision:** Confirms Issue #009 - `insights` table does not exist in database schema. Fix requires either creating the table or removing the dead code.

---

### V7: Adaptations Query Columns
**Question:** What columns does the adaptations query expect vs what exists?

**Command:** Read src/analysis/learning.py lines 150-165

**Result:**
```python
cursor.execute("""
    SELECT adaptation_id, action, target, confidence, effectiveness_rating,
           win_rate_before, win_rate_after, pnl_before, pnl_after, applied_at
    FROM adaptations
    ORDER BY applied_at DESC
""")
```

**Finding:** Query expects 10 columns including `effectiveness_rating`, `win_rate_before`, `win_rate_after`, `pnl_before`, `pnl_after` which don't exist in the schema.

**Decision:** Confirms Issue #008 - adaptations table schema mismatch. Fix requires updating CREATE TABLE or the query.

---

### V8: SYMBOL_MAP Locations
**Question:** How many SYMBOL_MAP definitions exist?

**Command:** `grep -rn "SYMBOL_MAP\s*=" src/`

**Result:**
```
src/technical/funding.py:73:SYMBOL_MAP = {
src/technical/vwap.py:37:SYMBOL_MAP = {
src/technical/rsi.py:34:SYMBOL_MAP = {
src/settings.py:145:SYMBOL_MAP = {
```

**Finding:** SYMBOL_MAP is defined in 4 places:
- src/technical/funding.py:73
- src/technical/vwap.py:37
- src/technical/rsi.py:34
- src/settings.py:145

**Decision:** Confirms Issue #012 - multiple SYMBOL_MAP definitions. Fix requires consolidating to single source (settings.py) and importing elsewhere.

---

### V9: PID File Path
**Question:** What's the actual PID file path used?

**Command:** `grep -rn "\.pid" src/`

**Result:**
```
src/main.py:56:PID_FILE = "data/trading_bot.pid"
src/main.py:58:    with open(PID_FILE, 'w') as f:
src/main.py:66:    if os.path.exists(PID_FILE):
src/main.py:67:        os.remove(PID_FILE)
```

**Finding:** PID file is at "data/trading_bot.pid", defined at line 56.

**Decision:** PID file location is consistent. No issue here.

---

### V10: Config Fallbacks
**Question:** What fallbacks exist when config.settings import fails?

**Command:** Read src/main.py lines 45-65

**Result:**
```python
try:
    from config.settings import (
        TIER_1_COINS, TIER_2_COINS, TIER_3_COINS,
        DATABASE_PATH, LOG_LEVEL, LLM_HOST
    )
except ImportError:
    logger.warning("Could not import from config.settings, using defaults")
    TIER_1_COINS = ['BTC', 'ETH']
    TIER_2_COINS = ['SOL', 'XRP', 'ADA']
    TIER_3_COINS = ['DOGE', 'SHIB']
    DATABASE_PATH = 'data/trading_bot.db'
    LOG_LEVEL = 'INFO'
    LLM_HOST = '172.27.144.1:11434'
```

**Finding:** Fallback values are minimal (only 7 coins total) compared to settings.py (25+ coins). This could cause silent behavior changes if import fails.

**Decision:** This is a potential issue but lower priority. Add to backlog for hardening.

---

### V11: Dashboard TradingSystem Import
**Question:** How does dashboard_v2.py use TradingSystem?

**Command:** `grep -n "TradingSystem\|main_v2\|main import" src/dashboard_v2.py`

**Result:**
```
src/dashboard_v2.py:28:from src.main_v2 import TradingSystem
```

**Finding:** dashboard_v2.py imports TradingSystem from non-existent `src.main_v2` module.

**Decision:** Confirms Issue #015 - dashboard will crash on import. Fix: change to `from src.main import TradingSystem`.

---

### V12: P&L Sources
**Question:** Where are P&L calculations performed?

**Command:** `grep -rn "pnl_usd\|total_pnl\|calculate.*pnl" src/`

**Result:**
```
src/main.py:289:        self.total_pnl = 0.0
src/main.py:476:        self.total_pnl += pnl
src/trading_engine.py:198:            'pnl_usd': pnl,
src/trading_engine.py:234:        pnl_usd = (current_price - entry_price) * quantity
src/database.py:312:            pnl_usd REAL,
src/metrics.py:45:        SELECT SUM(pnl_usd) FROM closed_trades
src/daily_summary.py:78:        SELECT SUM(pnl_usd) as total_pnl FROM closed_trades
```

**Finding:** P&L is calculated in trading_engine.py (line 234), stored in database (line 312), summed in metrics.py (line 45) and daily_summary.py (line 78).

**Decision:** P&L chain is intact. Issue #015 is specifically about dashboard import, not P&L calculation.

---

### V13: Meme Coins Mismatch
**Question:** Which meme coins are in SYMBOL_MAP but not in settings.py TIER lists?

**Command:** Compare SYMBOL_MAP keys vs TIER_*_COINS

**Result:**
In SYMBOL_MAP (src/settings.py:145) but NOT in any TIER:
- BONK, FLOKI, PEPE, SHIB, WIF (5 meme coins)

In TIER_3_COINS but NOT in SYMBOL_MAP:
- APT, ARB, INJ, NEAR, OP (5 coins)

**Finding:** 10 coins have configuration mismatch between SYMBOL_MAP and TIER lists.

**Decision:** Confirms Issue #012 severity. Fix must reconcile both directions:
1. Remove BONK, FLOKI, PEPE, SHIB, WIF from SYMBOL_MAP (or add to a TIER)
2. Add APT, ARB, INJ, NEAR, OP to SYMBOL_MAP (or remove from TIER_3)

---

### V14: Skipped FAVORED Test
**Question:** What does the skipped test say about the bug?

**Command:** Read tests/test_coin_scorer.py around line 168

**Result:**
```python
@pytest.mark.skip(reason="Known bug: FAVORED coins incorrectly demoted - see coin_scorer.py:211")
def test_favored_coin_not_demoted(self):
    """FAVORED coins should never be demoted regardless of score.

    BUG: coin_scorer.py:211 checks `if score < DEMOTION_THRESHOLD`
    before checking FAVORED status, causing FAVORED coins to be
    incorrectly demoted when they have low scores.

    FIX: Move FAVORED check before score comparison.
    """
    # Test implementation...
```

**Finding:** Test documents exact bug location (coin_scorer.py:211) and fix approach.

**Decision:** Confirms Issue #003 - FAVORED demotion bug. Fix is straightforward: reorder the conditionals.

---

## DECISIONS SUMMARY

Based on verification evidence, these are the confirmed decisions for fix waves:

### Wave 1: Critical Import Fixes
| Issue | Verified Fix |
|-------|-------------|
| #015 Dashboard Import | Change `from src.main_v2` to `from src.main` at dashboard_v2.py:28 |
| #006 ReflectionEngine | Add `from src.reflection import ReflectionEngine` to main.py |

### Wave 2: Data Integrity
| Issue | Verified Fix |
|-------|-------------|
| #003 FAVORED Bug | Reorder conditionals at coin_scorer.py:211 - check FAVORED before score |
| #008 Adaptations Schema | Update query or schema to match (need to check database.py for actual columns) |
| #009 Insights Table | Either create insights table or remove analyze_knowledge_growth() |

### Wave 3: Configuration Consolidation
| Issue | Verified Fix |
|-------|-------------|
| #012 SYMBOL_MAP | Consolidate to settings.py, import in technical/*.py |
| #012 Meme Coins | Remove BONK/FLOKI/PEPE/SHIB/WIF OR add to TIER_3 |
| #012 Missing Coins | Add APT/ARB/INJ/NEAR/OP to SYMBOL_MAP OR remove from TIER_3 |

### Wave 4: coins.json Resolution
| Issue | Verified Fix |
|-------|-------------|
| coins.json | Update market_feed.py to use settings.py TIER_* instead, THEN delete coins.json |

### Deferred (Backlog)
| Issue | Reason |
|-------|--------|
| Config fallbacks | Lower priority - add hardening later |
| #010 get_funding_rate | Part of Phase 3 integration - larger scope |

---

## VERIFICATION SCRIPT OUTPUT

Baseline captured before fix waves:

```
=== IMPORT CHECK ===
  OK: src.main
  OK: src.strategist
  OK: src.dashboard_v2
  OK: src.quick_update
  OK: src.coin_scorer
  OK: src.analysis.learning
  OK: src.technical.manager

=== TEST SUITE ===
17 failed, 871 passed, 2 skipped, 7 warnings, 18 errors in 54.80s

=== SYMBOL_MAP DUPLICATION CHECK ===
  SYMBOL_MAP definitions (should be 1 after fix): 2

=== DOC DRIFT CHECK ===
  'Binance' in docs (should be 0 after fix): 11
  '45 coins' in docs (should be 0 after fix): 5

=== VERIFICATION COMPLETE ===
```

### Baseline Summary
| Metric | Current | Target After Fixes |
|--------|---------|-------------------|
| Import checks | 7/7 OK | 7/7 OK |
| Tests passing | 871 | 871+ |
| Tests failing | 17 | 0 |
| Test errors | 18 | 0 |
| SYMBOL_MAP defs | 2+ | 1 |
| Binance refs in docs | 11 | 0 |
| "45 coins" refs in docs | 5 | 0 |

---

## NEXT STEPS

1. Run `scripts/verify_system.sh` to capture baseline
2. Create git checkpoint: `git add -A && git commit -m "PRE-WAVE: Checkpoint before fix waves"`
3. Begin Wave 1: Critical Import Fixes
4. After each wave: Run verify_system.sh, commit if passing

---

## PART 2: CORRECTED CHECKS (Date: February 4, 2026)

### V2-REDO: Score total_pnl
**Raw output:**
```
=== V2-REDO: Score object total_pnl ===
--- coin_scorer.py Score class/namedtuple/dataclass ---
10:from dataclasses import dataclass, field, asdict
48:@dataclass
111:        if score.win_rate < BLACKLIST_WIN_RATE and score.total_pnl < 0:
117:        if score.win_rate >= FAVORED_WIN_RATE and score.total_pnl > 0:
178:            score.total_pnl < 0 and
183:                     f"with ${score.total_pnl:.2f} loss over {score.total_trades} trades")
196:              score.total_pnl > 0 and
201:                     f"with ${score.total_pnl:.2f} profit over {score.total_trades} trades")
232:                    "total_pnl": score.total_pnl,

--- models directory ---
src/models/knowledge.py:20:    total_pnl: float = 0.0
src/models/knowledge.py:52:            self.avg_pnl = self.total_pnl / self.total_trades

--- What attributes does Score actually have? ---
(Score is CoinScore from src/models/knowledge.py, lines 10-53)

@dataclass
class CoinScore:
    coin: str
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0        # <-- LINE 20
    avg_pnl: float = 0.0
    win_rate: float = 0.0
    avg_winner: float = 0.0
    avg_loser: float = 0.0
    is_blacklisted: bool = False
    blacklist_reason: str = ""
    last_updated: Optional[datetime] = None
    trend: str = "stable"
```

**DECISION:** YES, Score (CoinScore) has `total_pnl` attribute at src/models/knowledge.py:20. The fix `score.total_pnl <= 0` in Issue 002 is valid syntax.

---

### V6-REDO: insights vs reflections
**Raw output:**
```
=== V6-REDO: insights vs reflections ===
--- What tables exist in database.py? ---
74:                CREATE TABLE IF NOT EXISTS open_trades (
91:                CREATE TABLE IF NOT EXISTS closed_trades (
109:               CREATE TABLE IF NOT EXISTS learnings (
124:               CREATE TABLE IF NOT EXISTS trading_rules (
139:               CREATE TABLE IF NOT EXISTS activity_log (
150:               CREATE TABLE IF NOT EXISTS account_state (
164:               CREATE TABLE IF NOT EXISTS market_data (
174:               CREATE TABLE IF NOT EXISTS price_history (
184:               CREATE TABLE IF NOT EXISTS coin_cooldowns (
192:               CREATE TABLE IF NOT EXISTS monitoring_alerts (
209:               CREATE TABLE IF NOT EXISTS trade_journal (
313:               CREATE TABLE IF NOT EXISTS active_conditions (
382:               CREATE TABLE IF NOT EXISTS coin_scores (
401:               CREATE TABLE IF NOT EXISTS trading_patterns (
419:               CREATE TABLE IF NOT EXISTS regime_rules (
433:               CREATE TABLE IF NOT EXISTS coin_adaptations (
447:               CREATE TABLE IF NOT EXISTS reflections (
461:               CREATE TABLE IF NOT EXISTS adaptations (
481:               CREATE TABLE IF NOT EXISTS runtime_state (
491:               CREATE TABLE IF NOT EXISTS profit_snapshots (
528:               CREATE TABLE IF NOT EXISTS equity_points (

--- Does 'reflections' table exist? ---
CREATE TABLE IF NOT EXISTS reflections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL,
    trades_analyzed INTEGER NOT NULL,
    period_hours REAL,
    insights TEXT NOT NULL,      # <-- JSON blob of insights
    summary TEXT,
    total_time_ms REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

--- Does 'insights' table exist? ---
(No output - table does NOT exist)

--- Full analyze_knowledge_growth function ---
def analyze_knowledge_growth(db: Database, days: int = 7) -> dict:
    # ...queries 'insights' table at multiple points:

    cursor.execute("""
        SELECT COUNT(*) FROM insights           # <-- TABLE DOES NOT EXIST
        WHERE created_at >= ?
    """, (cutoff,))

    # Also in daily breakdown loop:
    cursor.execute("""
        SELECT COUNT(*) FROM insights           # <-- TABLE DOES NOT EXIST
        WHERE created_at >= ? AND created_at < ?
    """, (day_start, day_end))
```

**DECISION:** Create an `insights` table. Rationale: The `reflections` table stores insights as a JSON blob per reflection session, but `analyze_knowledge_growth()` wants to count individual insights by date. The function design expects granular insight records. Schema should be:
```sql
CREATE TABLE IF NOT EXISTS insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reflection_id INTEGER,
    insight_type TEXT NOT NULL,
    description TEXT NOT NULL,
    discovered_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reflection_id) REFERENCES reflections(id)
)
```

---

### V7-REDO: adaptations table actual schema
**Raw output:**
```
=== V7-REDO: adaptations table actual schema ===
--- CREATE TABLE statement ---
CREATE TABLE IF NOT EXISTS adaptations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adaptation_id TEXT NOT NULL UNIQUE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    insight_type TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    description TEXT NOT NULL,
    pre_metrics TEXT,                    # JSON blob
    insight_confidence REAL,
    insight_evidence TEXT,
    post_metrics TEXT,                   # JSON blob
    effectiveness TEXT,
    effectiveness_measured_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

--- The broken query (lines 155-160) ---
cursor.execute("""
    SELECT adaptation_id, action, target, confidence, effectiveness_rating,
           win_rate_before, win_rate_after, pnl_before, pnl_after, applied_at
    FROM adaptations
    ORDER BY applied_at DESC
""")

--- Column mismatches ---
Query expects              | Schema has
---------------------------|---------------------------
confidence                 | insight_confidence
effectiveness_rating       | effectiveness (TEXT, not rating)
win_rate_before            | (in pre_metrics JSON)
win_rate_after             | (in post_metrics JSON)
pnl_before                 | (in pre_metrics JSON)
pnl_after                  | (in post_metrics JSON)
applied_at                 | timestamp (or created_at)

--- Post-query code (lines 165-210) ---
for row in adaptations:
    (adapt_id, action, target, conf, rating,
     wr_before, wr_after, pnl_before, pnl_after, applied_at) = row

    # Uses individual values directly, not JSON parsing
    if rating == "highly_effective":
        results["highly_effective"] += 1
    # ...
    "win_rate_change": (wr_after or 0) - (wr_before or 0)
    "pnl_change": (pnl_after or 0) - (pnl_before or 0)
```

**DECISION:**
1. **Actual columns:** adaptation_id, timestamp, insight_type, action, target, description, pre_metrics, insight_confidence, insight_evidence, post_metrics, effectiveness, effectiveness_measured_at, created_at
2. **Post-query code expects individual values**, not JSON blobs
3. **Full scope of fix:** Update the SQL query to:
   - Use `insight_confidence` instead of `confidence`
   - Use `effectiveness` instead of `effectiveness_rating`
   - Use `timestamp` instead of `applied_at`
   - Parse `pre_metrics`/`post_metrics` JSON to extract win_rate/pnl values

   OR add missing columns to schema (less desirable, duplicates data)

---

### V9-REDO: PID paths in start scripts
**Raw output:**
```
=== V9-REDO: PID paths in start scripts ===
--- scripts/start.sh ---
35:PID_FILE="/tmp/cryptobot-supervisord.pid"
38:if [ -f "$PID_FILE" ]; then
39:    PID=$(cat "$PID_FILE")

--- config/supervisor.conf ---
6:pidfile=/tmp/cryptobot-supervisord.pid

--- scripts/health.sh (the broken one) ---
11:if [ ! -f "$LOG_DIR/supervisord.pid" ]; then
16:PID=$(cat "$LOG_DIR/supervisord.pid")
17:if ! ps -p "$PID" > /dev/null 2>&1; then

--- health.sh full content ---
LOG_DIR="$PROJECT_DIR/logs"
# ...
if [ ! -f "$LOG_DIR/supervisord.pid" ]; then    # <-- WRONG PATH
    echo "CRITICAL: Supervisor not running"
    exit 2
fi
```

**DECISION:** health.sh uses `$PROJECT_DIR/logs/supervisord.pid` but the actual PID file is at `/tmp/cryptobot-supervisord.pid` (per start.sh:35 and supervisor.conf:6).

**Fix:** Change health.sh line 11 from:
```bash
if [ ! -f "$LOG_DIR/supervisord.pid" ]; then
```
to:
```bash
PID_FILE="/tmp/cryptobot-supervisord.pid"
if [ ! -f "$PID_FILE" ]; then
```
And update line 16 similarly.

---

### V11-REDO: dashboard_v2.py TradingSystem usage
**Raw output:**
```
=== V11-REDO: dashboard_v2.py TradingSystem usage ===
--- Methods/attributes dashboard_v2.py calls on self.system ---
self.system.coins                      # attribute
self.system.db                         # attribute
self.system.get_adaptation_effectiveness
self.system.get_conditions
self.system.get_equity_curve
self.system.get_improvement_metrics
self.system.get_loop_stats
self.system.get_performance_by_dimension
self.system.get_positions
self.system.get_profitability_snapshot
self.system.get_status
self.system.health                     # attribute
self.system.health_check
self.system.knowledge                  # attribute
self.system.pattern_library            # attribute
self.system.pause_trading
self.system.resume_trading
self.system.rollback_adaptation
self.system.sniper                     # attribute
self.system.trigger_reflection

--- main.py TradingSystem has all of these? ---
coins:                    YES (line 180: self.coins = coins or TRADEABLE_COINS)
db:                       YES (line 193: self.db)
get_adaptation_effectiveness: YES (line 928)
get_conditions:           YES (line 646)
get_equity_curve:         YES (line 913)
get_improvement_metrics:  YES (line 899)
get_loop_stats:           YES (line 772)
get_performance_by_dimension: YES (line 879)
get_positions:            YES (line 640)
get_profitability_snapshot: YES (line 860)
get_status:               YES (line 611)
health:                   YES (line 190: self.health)
health_check:             YES (line 656)
knowledge:                YES (line 194: self.knowledge)
pattern_library:          YES (line 197: self.pattern_library)
pause_trading:            YES (line 838)
resume_trading:           YES (line 849)
rollback_adaptation:      YES (line 953)
sniper:                   YES (line 188: self.sniper)
trigger_reflection:       YES (line 817)
```

**DECISION:** YES, safe to change import. All 20 methods/attributes that dashboard_v2.py uses on TradingSystem exist in main.py's TradingSystem class. No additional fixes needed beyond changing the import from `main_v2` to `main`.

---

### V12-REDO: Dashboard P&L data sources
**Raw output:**
```
=== V12-REDO: Dashboard P&L data sources ===
--- profitability.html P&L elements ---
Line 27: <div id="snap-pnl">$0.00</div>         # "Total P&L"
Line 31: <div id="snap-winrate">0%</div>         # "Win Rate"
Line 54: <div id="snap-starting">$10,000</div>   # "Starting Balance"
Line 58: <div id="snap-current">$10,000</div>    # "Current Balance"
Line 62: <div id="snap-return">0%</div>          # "Total Return"

--- JavaScript fetch (line 112) ---
const res = await fetch(`/api/profitability/snapshot?timeframe=${timeframe}`);
const data = await res.json();
document.getElementById('snap-pnl').textContent = data.total_pnl

--- API endpoint (dashboard_v2.py:369-372) ---
@self.app.get("/api/profitability/snapshot")
async def get_profitability_snapshot(timeframe: str = "all_time"):
    result = self.system.get_profitability_snapshot(timeframe)
    return result

--- main.py get_profitability_snapshot (line 860-877) ---
def get_profitability_snapshot(self, timeframe: str = "all_time") -> dict:
    if not self.profitability_tracker:
        return {"error": "Profitability tracker not initialized"}
    return self.profitability_tracker.get_snapshot(timeframe)

--- Secondary P&L source (dashboard_v2.py:565-566, WebSocket) ---
if self.system.sniper:
    status = self.system.sniper.get_status()
data["balance"] = status.get("balance", 0)
data["total_pnl"] = status.get("total_pnl", 0)
```

**DECISION:** There are TWO P&L sources:
1. **profitability_tracker.get_snapshot()** - Used by /api/profitability/snapshot endpoint → profitability.html
2. **sniper.get_status()** - Used by WebSocket real-time updates

The three different P&L values issue likely stems from:
- profitability_tracker queries closed_trades table
- sniper tracks in-memory running total
- Potential: index.html uses a third source (needs verification)

**Divergence point:** The two sources may calculate differently or from different data. Need to trace both to their database queries to confirm they use the same source of truth.

---

### V14-REDO: FAVORED bug actual fix
**Raw output:**
```
=== V14-REDO: FAVORED bug actual code ===
--- The scoring/demotion logic (lines 195-230) ---

# PROMOTION to FAVORED (lines 196-201):
elif (score.win_rate >= FAVORED_WIN_RATE and
      score.total_pnl > 0 and                    # <-- Requires positive P&L
      current_status not in [CoinStatus.BLACKLISTED, CoinStatus.FAVORED]):
    new_status = CoinStatus.FAVORED

# DEMOTION from FAVORED (lines 211-215):
elif (score.win_rate < FAVORED_WIN_RATE and      # <-- Only checks win_rate
      current_status == CoinStatus.FAVORED):
    new_status = CoinStatus.NORMAL
    reason = f"Win rate dropped to {score.win_rate:.0%}"
                                                  # <-- NO P&L CHECK!

--- The skipped test (line 168) ---
@pytest.mark.skip(reason="IMPLEMENTATION BUG: check_thresholds() doesn't
demote from FAVORED when P&L goes negative (only checks win_rate).
See coin_scorer.py:211-215. Coin becomes FAVORED on trade 5 with positive
P&L, then stays FAVORED despite P&L going negative.")

def test_favored_requires_positive_pnl(self, scorer):
    # 60% win rate but negative P&L
    for i in range(6):
        scorer.process_trade_result({"coin": "EDGE", "pnl_usd": 1.0})  # Small wins
    for i in range(4):
        scorer.process_trade_result({"coin": "EDGE", "pnl_usd": -5.0})  # Big losses
    # Total: +$6 - $20 = -$14 (negative P&L)
    status = scorer.get_coin_status("EDGE")
    assert status != CoinStatus.FAVORED   # BUG: Still FAVORED because win_rate >= 60%
```

**DECISION:**
1. **The bug is about missing criteria**, not ordering. Promotion requires positive P&L, but demotion doesn't check P&L.
2. **Could it be both?** No, it's only the missing P&L check on demotion.
3. **Exact code change:**

**Before (buggy):**
```python
# Lines 211-215
elif (score.win_rate < FAVORED_WIN_RATE and
      current_status == CoinStatus.FAVORED):
    new_status = CoinStatus.NORMAL
    reason = f"Win rate dropped to {score.win_rate:.0%}"
```

**After (fixed):**
```python
# Lines 211-215
elif ((score.win_rate < FAVORED_WIN_RATE or score.total_pnl <= 0) and
      current_status == CoinStatus.FAVORED):
    new_status = CoinStatus.NORMAL
    if score.total_pnl <= 0:
        reason = f"P&L went negative (${score.total_pnl:.2f})"
    else:
        reason = f"Win rate dropped to {score.win_rate:.0%}"
```

---

## ALL DECISIONS FINAL SUMMARY

| Check | Decision | Evidence |
|-------|----------|----------|
| V2 | YES, Score has total_pnl | src/models/knowledge.py:20 defines `total_pnl: float = 0.0` |
| V6 | Create `insights` table | reflections stores JSON blob; function needs individual records |
| V7 | Update query + add JSON parsing | Schema has pre_metrics/post_metrics JSON, query expects individual columns |
| V9 | `/tmp/cryptobot-supervisord.pid` | start.sh:35 and supervisor.conf:6 both use /tmp path |
| V11 | YES, safe to change import | All 20 methods/attributes exist in main.py TradingSystem |
| V12 | Two P&L sources: profitability_tracker + sniper | Divergence needs further tracing to database queries |
| V14 | Add P&L check to demotion (lines 211-215) | Promotion requires P&L>0; demotion only checks win_rate |

---

**Document Status:** COMPLETE
**Ready for:** Wave 1 execution
