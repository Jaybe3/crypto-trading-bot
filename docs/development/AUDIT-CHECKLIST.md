# Runtime Integration Audit Checklist

Reusable checklist for verifying crypto trading bot runtime integrity.

## Quick Audit

```bash
# Run quick shell audit
./scripts/audit.sh

# Run comprehensive Python audit
python scripts/audit_runtime.py

# Run with API verification (if bot is running)
python scripts/audit_runtime.py --api http://localhost:8000
```

## Manual Verification Steps

### 1. Database Layer

Check that database tables exist and contain expected data:

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('data/trading_bot.db')
cur = conn.cursor()
cur.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
print('Tables:', [r[0] for r in cur.fetchall()])
conn.close()
"
```

Verify account_state is being updated:
```sql
SELECT balance, total_pnl, updated_at FROM account_state;
-- If balance = 1000.00, RT-001 is present
```

Verify trade_journal vs open/closed_trades:
```sql
SELECT
  (SELECT COUNT(*) FROM trade_journal) as journal,
  (SELECT COUNT(*) FROM open_trades) as open_t,
  (SELECT COUNT(*) FROM closed_trades) as closed_t;
-- If open_t and closed_t are 0 but journal > 0, RT-002 is present
```

### 2. JSON State Layer

```bash
# Check sniper state file
cat data/sniper_state.json | python -m json.tool | head -20
```

Key fields to verify:
- `balance` - Should match trading activity
- `positions` - Current open positions
- `closed_positions` - History of closed trades
- `total_pnl` - Cumulative profit/loss

### 3. API Layer (if running)

```bash
# Status endpoint
curl -s http://localhost:8000/api/status | python -m json.tool

# Profitability endpoint
curl -s http://localhost:8000/api/profitability/snapshot | python -m json.tool

# Positions
curl -s http://localhost:8000/api/positions | python -m json.tool
```

### 4. Cross-Layer Consistency

Compare these values across all layers:

| Metric | Database | JSON State | API /status | API /profitability |
|--------|----------|------------|-------------|-------------------|
| Balance | `account_state.balance` | `sniper_state.balance` | `account.balance` | `account_balance` |
| Total P&L | `account_state.total_pnl` | `sniper_state.total_pnl` | `account.total_pnl` | `total_pnl` |
| Closed Trades | `trade_journal WHERE exit IS NOT NULL` | `closed_positions[]` | N/A | `total_trades` |

**Expected behavior**: All values should match within acceptable tolerance ($0.01 for balances).

## Known Bugs Reference

### RT-001: update_account_state() Never Called

**Symptom**: `account_state.balance` stuck at initial $1000.00

**Location**: `src/database.py:648` - `update_account_state()` exists but is never called

**Impact**: Database doesn't reflect actual account state

**Verification**:
```sql
SELECT balance FROM account_state;  -- Returns 1000.00
```

### RT-002: open_trades/closed_trades Tables Empty

**Symptom**: Both tables have 0 rows despite trading activity

**Location**: Tables not populated by any code path

**Impact**: Dashboard endpoints reading these tables show stale/no data

**Verification**:
```sql
SELECT COUNT(*) FROM open_trades;   -- Returns 0
SELECT COUNT(*) FROM closed_trades; -- Returns 0
SELECT COUNT(*) FROM trade_journal; -- Returns > 0
```

### RT-003: Database vs JSON Balance Mismatch

**Symptom**: Different balance values in database vs JSON state file

**Root Cause**: RT-001 - database never updated

**Verification**:
```bash
python scripts/audit_runtime.py  # Shows mismatch in report
```

### RT-004: API Endpoint Data Disagreement

**Symptom**: Different API endpoints return different values for same metrics

**Root Cause**: Endpoints read from different data sources (in-memory vs database)

**Verification**:
```bash
# Compare these two:
curl http://localhost:8000/api/status
curl http://localhost:8000/api/profitability/snapshot
```

### RT-005: Three Disconnected Data Stores

**Symptom**: System maintains three data stores that drift out of sync:
1. Sniper in-memory state
2. Sniper JSON persistence (sniper_state.json)
3. Database tables

**Impact**: Different parts of system show different data

## Integration Flow Verification

### Flow 1: Strategist → Sniper

```
Strategist.generate_conditions()
  → main.py:452 sniper.set_conditions(conditions)
  → Sniper stores conditions in memory
```

**Test**: Check that conditions from Strategist appear in Sniper:
```python
# In running bot
print(len(trading_system.sniper.conditions))  # Should match strategist output
```

### Flow 2: Sniper → Journal

```
Sniper._close_position()
  → sniper.py:548 self.journal.record_exit(...)
  → Journal writes to trade_journal table
```

**Test**: After trade close, check trade_journal has new entry:
```sql
SELECT * FROM trade_journal ORDER BY exit_timestamp DESC LIMIT 1;
```

### Flow 3: Journal → QuickUpdate → Learning

```
Sniper._close_position()
  → sniper.py:570 self.quick_update.process_trade_close(...)
  → QuickUpdate updates coin_scorer
  → quick_update.py:146 self.reflection_engine.on_trade_close()
  → ReflectionEngine increments trade counter
```

**Test**: Check reflection engine trade counter increments:
```python
print(trading_system.reflection_engine.trades_since_reflection)
```

## Automated Tests

Run integration tests:
```bash
pytest tests/test_integration.py -v
pytest tests/test_phase3_integration.py -v
```

## Audit Schedule

- **Pre-deployment**: Full checklist
- **Weekly**: Quick audit (`./scripts/audit.sh`)
- **After major changes**: Full checklist + test suite
- **On anomalous behavior**: Full checklist with API verification
