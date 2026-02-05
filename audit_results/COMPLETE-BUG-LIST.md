# Complete Bug List - Comprehensive System Audit

**Date**: 2026-02-05
**Auditor**: Systematic audit with evidence
**Scope**: All components, all data flows, all tables

## Executive Summary

| Severity | Count | Description |
|----------|-------|-------------|
| CRITICAL | 3 | System doesn't work as intended |
| HIGH | 6 | Major functionality broken |
| MEDIUM | 5 | Functionality impaired |
| LOW | 2 | Tech debt / cosmetic |

**Total: 16 bugs identified with evidence**

---

## CRITICAL (System doesn't work as intended)

### RT-006: Learning Loop Produces 0 Adaptations from 168 Trades

**Evidence**:
```
trade_journal: 168 closed trades
reflections: 2 (with insights JSON embedded)
insights table: 0 rows
adaptations table: 0 rows
```

**Root Cause**: Multiple failures:
1. Insights are stored as JSON in `reflections.insights` column but never extracted to `insights` table
2. `_should_apply()` in AdaptationEngine requires `insight.evidence.get("trades", 0) >= 5`, but generated insights have `evidence: {"metric": "win_rate", "value": 0.74}` with no `trades` field
3. All adaptations skipped due to threshold not being met

**Impact**: Bot cannot learn from its mistakes. Core value proposition is broken.

### RT-009: 5 Knowledge API Endpoints Broken (HTTP 500)

**Evidence**:
```
✗ /api/knowledge/coins (HTTP 500)
✗ /api/knowledge/patterns (HTTP 500)
✗ /api/knowledge/rules (HTTP 500)
✗ /api/knowledge/blacklist (HTTP 500)
✗ /api/knowledge/context (HTTP 500)
```

**Root Cause**: Dashboard calls methods that don't exist in KnowledgeBrain:
- Dashboard calls `get_all_coins()` - doesn't exist
- KnowledgeBrain has `get_all_coin_scores()`
- Dashboard calls `get_coin(coin)` - doesn't exist
- KnowledgeBrain has `get_coin_score(coin)`

**Impact**: Knowledge dashboard pages are completely non-functional.

### RT-010: Coin Scores Not Tracking Most Trades

**Evidence**:
```
coin_scores total: 12 trades (BTC: 3, SOL: 9)
trade_journal closed: 168 trades (BTC: 166, SOL: 2)
Discrepancy: 156 trades NOT tracked (93%)
```

**Root Cause**: QuickUpdate only processes trades that go through Sniper's `_close_position()`. Historical trades and trades created via other paths don't get processed.

**Impact**: Coin performance tracking is 93% incomplete. Blacklist/favor decisions based on wrong data.

---

## HIGH (Major functionality broken)

### RT-001: update_account_state() Never Called

**Evidence**:
```sql
SELECT balance, total_pnl FROM account_state;
-- Returns: 1000.0, 0.0 (initial values from 2026-02-03)
```

**Root Cause**: Function exists at `database.py:648` but no code calls it.

**Impact**: Database account state is stale. Any code reading from it gets wrong data.

### RT-003: Massive Data Disagreement Across Sources

**Evidence**:
| Source | Balance | P&L | Closed Trades |
|--------|---------|-----|---------------|
| account_state (DB) | $1,000 | $0 | N/A |
| trade_journal (DB) | N/A | $757 | 168 |
| sniper_state (JSON) | $9,930 | -$10 | 0 |
| /api/status | $9,935 | -$15 | N/A |
| /api/profitability | $10,757 | $757 | 168 |

**Impact**: Users see different data depending on which endpoint they call. Impossible to know what's real.

### RT-007: Phase 3 Technical Data Not In Logs

**Evidence**:
```bash
grep -i "RSI\|VWAP\|ATR\|fear\|greed" logs/trading_bot.log
# Returns: 1 unrelated line
```

**Root Cause**: Bot was restarted today (2026-02-05T12:59:36) with Phase 3 code, but no technical indicators appear in logs. Either:
1. Technical data fetch is failing silently
2. Technical data is empty
3. Data isn't being logged even when present

**Impact**: Cannot verify if LLM is receiving technical context for decisions.

### RT-008: 60 Trades Have Corrupted Timestamps

**Evidence**:
```sql
SELECT COUNT(*) FROM trade_journal WHERE entry_time < '2000-01-01';
-- Returns: 60 (all have entry_time = '1969-12-31T17:00:02')
```

**Root Cause**: Unix timestamp (milliseconds) being stored directly instead of converted to datetime.

**Impact**: Historical analysis and trade timeline queries are corrupted.

### RT-011: Reflection Endpoints Don't Exist

**Evidence**:
```
? /api/reflection/status (HTTP 404)
? /api/reflection/history (HTTP 404)
```

**Impact**: No way to monitor reflection engine status via API.

### RT-012: 12 Empty Database Tables (52%)

**Evidence**:
```
Empty tables (0 rows):
- adaptations
- closed_trades
- coin_cooldowns
- equity_points
- insights
- learnings
- market_data
- monitoring_alerts
- open_trades
- price_history
- regime_rules
- trading_rules
```

**Impact**: Half the database schema is unused. Code may be reading from these expecting data.

---

## MEDIUM (Functionality impaired)

### RT-002: open_trades/closed_trades Tables Empty

**Evidence**:
```sql
SELECT COUNT(*) FROM open_trades;  -- 0
SELECT COUNT(*) FROM closed_trades; -- 0
SELECT COUNT(*) FROM trade_journal; -- 645
```

**Impact**: Redundant tables causing confusion. Code reading them gets no data.

### RT-004: API Endpoints Read from Different Sources

**Evidence**:
- `/api/status` reads from Sniper in-memory
- `/api/profitability/snapshot` reads from Profitability class (uses trade_journal)
- Results differ by $800+ in balance

**Impact**: Inconsistent API responses depending on endpoint called.

### RT-005: Three Disconnected Data Stores

**Evidence**:
1. Sniper in-memory: balance=$9,935, pnl=-$15
2. sniper_state.json: balance=$9,930, pnl=-$10, closed_positions=0
3. Database tables: balance=$1,000, pnl=$0 (account_state) or $757 (trade_journal)

**Impact**: System has no single source of truth.

### RT-013: Instant Trades (entry_time == exit_time)

**Evidence**:
```
j-20260205142249-aa7 BTC entry=2026-02-05T14:22:49 exit=2026-02-05T14:22:49 pnl=$20.00
j-20260205142249-3f5 BTC entry=2026-02-05T14:22:49 exit=2026-02-05T14:22:49 pnl=$-20.00
```

Multiple trades with identical entry and exit timestamps (same second).

**Impact**: Data quality issue. May indicate test trades or bugs in trade execution.

### RT-014: JSON closed_positions Empty Despite 168 Closed Trades

**Evidence**:
```json
{
  "balance": 9930.27,
  "closed_positions": []  // Empty!
}
```

But trade_journal has 168 closed trades.

**Impact**: JSON state doesn't track trade history. Lost on restart.

---

## LOW (Tech debt / cosmetic)

### RT-015: Sniper trades_executed (12) != Journal Closed (168)

**Evidence**:
- Sniper reports: trades_executed=12
- trade_journal shows: 168 closed trades

**Root Cause**: Journal tracks all trades ever, Sniper only tracks current session.

**Impact**: Confusing metrics. Not a bug per se, but needs documentation.

### RT-016: Adaptation Threshold Logs at DEBUG Level

**Evidence**: `_should_apply()` uses `logger.debug()` for skip reasons, not visible in production logs.

**Impact**: Can't diagnose why adaptations aren't being applied without enabling debug logging.

---

## Dashboard Gaps (Features needed)

| ID | Description | Priority |
|----|-------------|----------|
| DASH-001 | No trade history view | HIGH |
| DASH-002 | No LLM prompt viewer | HIGH |
| DASH-003 | No Phase 3 data panel (technical indicators, sentiment) | HIGH |
| DASH-004 | No trade audit trail | HIGH |
| DASH-005 | Knowledge pages broken (HTTP 500) | CRITICAL |
| DASH-006 | No reflection status endpoint | MEDIUM |
| DASH-007 | No way to see what data LLM received | HIGH |

---

## Integration Flow Status

| Flow | Status | Evidence |
|------|--------|----------|
| Strategist → Sniper | WORKING | Conditions being set |
| Sniper → Journal | WORKING | 645 journal entries |
| Trade → QuickUpdate | PARTIAL | Only 12/168 trades (7%) |
| QuickUpdate → coin_scores | PARTIAL | 12 trades tracked |
| Reflection → insights table | BROKEN | 0 insights saved |
| Insights → Adaptations | BROKEN | Thresholds never met |
| Trade → account_state | BROKEN | Never updated |
| Phase 3 → LLM prompt | UNVERIFIED | No log evidence |

---

## Summary Table

| Bug ID | Severity | Category | Status |
|--------|----------|----------|--------|
| RT-001 | HIGH | Database | Never called |
| RT-002 | MEDIUM | Database | Empty tables |
| RT-003 | HIGH | Data | 5-way disagreement |
| RT-004 | MEDIUM | API | Different sources |
| RT-005 | MEDIUM | Architecture | 3 data stores |
| RT-006 | CRITICAL | Learning | 0 adaptations |
| RT-007 | HIGH | Phase 3 | Not in logs |
| RT-008 | HIGH | Data | 60 corrupted |
| RT-009 | CRITICAL | API | 5 endpoints 500 |
| RT-010 | CRITICAL | Learning | 93% not tracked |
| RT-011 | HIGH | API | Endpoints missing |
| RT-012 | HIGH | Database | 12 empty tables |
| RT-013 | MEDIUM | Data | Instant trades |
| RT-014 | MEDIUM | Data | JSON empty |
| RT-015 | LOW | Metrics | Count mismatch |
| RT-016 | LOW | Logging | Debug level |

---

## Recommended Priority Order

1. **RT-009**: Fix knowledge API methods (blocks dashboard)
2. **RT-006**: Fix insight extraction and adaptation thresholds (blocks learning)
3. **RT-010**: Ensure all trades go through QuickUpdate (blocks learning)
4. **RT-003**: Establish single source of truth (blocks trust in data)
5. **RT-001**: Add account_state updates (blocks accurate display)
6. **RT-007**: Verify Phase 3 data reaches LLM (blocks technical analysis)
7. **RT-008**: Fix timestamp handling (blocks historical analysis)
