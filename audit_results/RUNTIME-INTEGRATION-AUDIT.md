# Runtime Integration Audit Report

**Date**: 2026-02-05
**Auditor**: Automated audit during Phase B remediation
**Scope**: Full system data integrity verification

## Executive Summary

The audit identified **4 confirmed runtime bugs** causing significant data disagreement across system layers. The three data stores (database, JSON state, in-memory) have drifted completely out of sync.

| Bug ID | Severity | Status | Description |
|--------|----------|--------|-------------|
| RT-001 | HIGH | CONFIRMED | `update_account_state()` never called |
| RT-002 | MEDIUM | CONFIRMED | `open_trades`/`closed_trades` tables empty |
| RT-003 | HIGH | CONFIRMED | Database vs JSON balance mismatch |
| RT-004 | MEDIUM | CONFIRMED | API endpoints show different data |
| RT-005 | HIGH | CONFIRMED | Three disconnected data stores |

## Data Store Comparison

### Current State (as of audit)

| Metric | Database | JSON State | Gap |
|--------|----------|------------|-----|
| Balance | $1,000.00 | $9,930.27 | $8,930.27 |
| Total P&L | $0.00 (account_state) | -$9.73 | N/A |
| Total P&L | $744.27 (trade_journal sum) | -$9.73 | $754.00 |
| Closed Trades | 175 (trade_journal) | 0 (closed_positions) | 175 |
| Open Trades | 0 (open_trades table) | 1 (positions) | 1 |
| Activity Log | 851 entries | N/A | - |
| Adaptations | 0 | N/A | - |

### Key Observations

1. **Database account_state is stale**: Still shows initial $1,000 balance, never updated
2. **JSON state reset**: `closed_positions` array is empty (0 trades) but trade_journal has 175 closed trades
3. **P&L disagreement**: Database shows +$744 profit, JSON shows -$9 loss
4. **open_trades/closed_trades unused**: Both tables have 0 rows despite trading activity

## Bug Evidence

### RT-001: update_account_state() Never Called

**Location**: `src/database.py:648`

```python
def update_account_state(self, balance: float, total_pnl: float, ...):
    # This function EXISTS but is NEVER CALLED
```

**Evidence**:
```sql
SELECT balance, total_pnl FROM account_state;
-- Returns: 1000.0, 0.0 (initial values)
```

**Grep for callers**:
```bash
$ grep -r "update_account_state" src/
src/database.py:648:    def update_account_state(...)  # Definition only
# No callers found
```

**Impact**: Database doesn't reflect actual account state. Any code reading from `account_state` gets stale data.

### RT-002: open_trades/closed_trades Tables Empty

**Evidence**:
```sql
SELECT COUNT(*) FROM open_trades;   -- 0
SELECT COUNT(*) FROM closed_trades; -- 0
SELECT COUNT(*) FROM trade_journal; -- 644 (175 closed)
```

**Root Cause**: Code writes to `trade_journal` but not to `open_trades`/`closed_trades`.

**Impact**: Dashboard or other code reading from these tables shows no data.

### RT-003: Database vs JSON Balance Mismatch

**Database (account_state)**:
- Balance: $1,000.00
- Total P&L: $0.00

**JSON (sniper_state.json)**:
- Balance: $9,930.27
- Total P&L: -$9.73
- Open Positions: 1
- Closed Positions: 0

**Discrepancy**: $8,930.27 balance difference

**Root Cause**: RT-001 (database never updated) plus potential JSON state resets.

### RT-004: API Endpoint Data Disagreement

Different endpoints return different values for the same metrics:

| Endpoint | Data Source | Balance | P&L |
|----------|-------------|---------|-----|
| `/api/status` | Sniper in-memory | ~$9,906 | ~-$13 |
| `/api/profitability/snapshot` | Profitability class (DB) | ~$10,758 | ~+$758 |
| Database account_state | Direct query | $1,000 | $0 |
| JSON state file | File read | $9,930 | -$9 |

**Root Cause**: Endpoints read from different data sources without synchronization.

### RT-005: Three Disconnected Data Stores

The system maintains three data stores that have completely drifted:

1. **Sniper In-Memory State**
   - Authoritative for current trading
   - Lost on restart (unless persisted to JSON)
   - Read by `/api/status`, `/api/positions`

2. **Sniper JSON File** (`data/sniper_state.json`)
   - Persistence layer for Sniper
   - Updated on trades
   - Can be reset/corrupted

3. **Database Tables** (`data/trading_bot.db`)
   - `account_state`: Never updated (RT-001)
   - `trade_journal`: Receives trade records
   - `open_trades`/`closed_trades`: Never populated (RT-002)
   - Read by `/api/profitability/*` endpoints

## Integration Flow Verification

### Flow 1: Strategist → Sniper (WORKING)

```
Strategist.generate_conditions()
  → main.py:452 sniper.set_conditions(conditions)
  → Sniper stores conditions
```

**Status**: Verified working. Conditions flow correctly.

### Flow 2: Sniper → Journal (WORKING)

```
Sniper._close_position()
  → sniper.py:548 journal.record_exit(...)
  → trade_journal table updated
```

**Status**: Verified working. 175 closed trades in trade_journal.

### Flow 3: Sniper → QuickUpdate → Learning (WORKING)

```
Sniper._close_position()
  → sniper.py:570 quick_update.process_trade_close(...)
  → QuickUpdate updates coin_scorer
  → quick_update.py:146 reflection_engine.on_trade_close()
```

**Status**: Verified working. Integration code is properly wired.

### Flow 4: Trade → Account State (BROKEN)

```
Sniper._close_position()
  → ??? (no call to update_account_state)
  → account_state table NEVER UPDATED
```

**Status**: BROKEN. Missing integration.

## Recommendations

### Immediate Actions

1. **Fix RT-001**: Add call to `update_account_state()` after trades complete
   - Location: After `journal.record_exit()` in `sniper.py:548`
   - Or in `QuickUpdate.process_trade_close()`

2. **Fix RT-002**: Either populate `open_trades`/`closed_trades` or deprecate them
   - If kept: Add write calls to Sniper position management
   - If deprecated: Remove tables and update code that reads them

3. **Fix RT-003/RT-004**: Establish single source of truth
   - Option A: Make database authoritative, sync others to it
   - Option B: Make Sniper in-memory authoritative, database is just for history

### Long-term Actions

1. **Unify data stores**: Consider single authoritative source
2. **Add data integrity checks**: Regular comparison between stores
3. **Add alerts**: Notify when stores drift beyond threshold
4. **Add recovery mechanism**: Auto-sync or manual reconciliation

## Audit Infrastructure Created

This audit created reusable infrastructure:

| File | Purpose |
|------|---------|
| `scripts/audit.sh` | Quick shell-based runtime check |
| `scripts/audit_runtime.py` | Comprehensive Python audit with JSON output |
| `docs/development/AUDIT-CHECKLIST.md` | Reusable manual checklist |
| `audit_results/RUNTIME-INTEGRATION-AUDIT.md` | This document |

### Usage

```bash
# Quick audit
./scripts/audit.sh

# Comprehensive audit
python scripts/audit_runtime.py

# With API verification
python scripts/audit_runtime.py --api http://localhost:8000

# JSON output for automation
python scripts/audit_runtime.py --json
```

## Appendix: Raw Data

### Database Tables

```
account_state, adaptations, activity_log, backtest_results,
closed_trades, coin_scores, learning_cycles, llm_cache,
market_context, market_snapshots, meta_strategy, news_items,
open_trades, parameter_history, pattern_stats, reflection_insights,
session_snapshots, signal_history, social_sentiment, strategy_config,
technical_levels, trade_journal, trade_learning
```

### JSON State Structure

```json
{
  "balance": 9930.27,
  "total_pnl": -9.73,
  "positions": { "1": {...} },
  "closed_positions": [],
  "conditions": [...]
}
```

## Conclusion

The audit confirms significant data integrity issues across the system. The core trading flows (Strategist → Sniper → Journal → Learning) are working correctly, but the account state synchronization is broken. This results in different parts of the system showing different data, which is confusing for users and could lead to incorrect decisions.

Priority should be given to fixing RT-001 (account state updates) as it is the root cause of most discrepancies.
