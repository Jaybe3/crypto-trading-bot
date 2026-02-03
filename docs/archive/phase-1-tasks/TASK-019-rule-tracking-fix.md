# TASK-019: Fix Rule Tracking Bug

## Overview
Fix critical bug where rule success rates don't match actual trade outcomes. Rule showed 73% success rate but actual win rate was 7.1% (1 winner out of 14 trades).

## Root Cause Analysis

### Problem 1: LLM prompt missing `rules_applied` field
- **Location:** `src/llm_interface.py:277-289`
- **Issue:** JSON format doesn't include `rules_applied`
- **Result:** LLM never returns which rules it's using

### Problem 2: Trades not tagged with rule IDs
- **Location:** `src/main.py:337` and `src/trading_engine.py:74`
- **Issue:** `rules_applied` from LLM decision not passed to trade execution
- **Result:** `rule_ids_used` column always NULL

### Problem 3: Rule outcomes never recorded
- **Location:** `src/trading_engine.py:225-230`
- **Issue:** Only records outcomes when `rule_ids_used` is not NULL
- **Result:** No real trade outcomes linked to rules

### Problem 4: Phantom rule counts
- **Evidence:** Rule #1 has 8 success/3 failure, but only 1 trade has `rule_ids_used`
- **Likely cause:** Test/development code ran against production database
- **Solution:** Reset counts to zero for fresh start

---

## Fixes

### Fix 1: Update LLM Prompt (DONE)
```python
# src/llm_interface.py - Updated JSON format
{
    "action": "BUY" or "SELL" or "HOLD",
    "coin": "...",
    "size_usd": number,
    "reason": "...",
    "confidence": 0.0 to 1.0,
    "rules_applied": [1, 2] or []  # NEW - REQUIRED
}
```

### Fix 2: Reset Rule Counts
```sql
UPDATE trading_rules
SET success_count = 0,
    failure_count = 0,
    status = 'testing';
```

### Fix 3: Verify Trading Engine
Check that `src/trading_engine.py` properly:
1. Receives `rule_ids` from main.py
2. Stores them in `open_trades.rule_ids_used`
3. Transfers them to `closed_trades.rule_ids_used` on close
4. Calls `record_rule_outcome()` for each rule

---

## Verification

### Test 1: LLM returns rules_applied
```bash
# Watch for rules_applied in decisions
tail -f logs/trading_bot.log | grep "rules_applied"
```

### Test 2: Trades linked to rules
```python
# Check recent trades have rule_ids
import sqlite3
conn = sqlite3.connect('data/trading_bot.db')
cursor = conn.cursor()
cursor.execute('SELECT id, coin_name, rule_ids_used FROM closed_trades ORDER BY id DESC LIMIT 5')
for row in cursor.fetchall():
    print(f'Trade #{row[0]}: {row[1]} rules={row[2]}')
```

### Test 3: Rule counts match trades
```python
# Compare rule stats to actual trade outcomes
cursor.execute('''
SELECT tr.id, tr.success_count, tr.failure_count,
       (SELECT COUNT(*) FROM closed_trades WHERE rule_ids_used LIKE '%' || tr.id || '%' AND pnl_usd > 0) as actual_wins,
       (SELECT COUNT(*) FROM closed_trades WHERE rule_ids_used LIKE '%' || tr.id || '%' AND pnl_usd <= 0) as actual_losses
FROM trading_rules tr
''')
for row in cursor.fetchall():
    print(f'Rule #{row[0]}: claims {row[1]}W/{row[2]}L, actual {row[3]}W/{row[4]}L')
```

---

## Success Criteria

- [ ] LLM returns `rules_applied` in every decision
- [ ] Trades stored with `rule_ids_used` populated
- [ ] Rule success/failure counts match actual trade P&L
- [ ] Dashboard shows accurate rule success rates
