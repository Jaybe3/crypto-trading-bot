#!/bin/bash
# Quick runtime audit script for crypto trading bot
# Usage: ./scripts/audit.sh
# Verifies data integrity across all storage layers

set -e

DB_PATH="${1:-data/trading_bot.db}"
SNIPER_STATE="${2:-data/sniper_state.json}"

echo "=============================================="
echo "         CRYPTO BOT RUNTIME AUDIT"
echo "=============================================="
echo "Time: $(date)"
echo "DB: $DB_PATH"
echo "State: $SNIPER_STATE"
echo ""

# Check if files exist
if [ ! -f "$DB_PATH" ]; then
    echo "ERROR: Database not found at $DB_PATH"
    exit 1
fi

echo "=== 1. DATABASE STATE ==="
python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
cur = conn.cursor()

# Account state
cur.execute('SELECT balance, total_pnl FROM account_state LIMIT 1')
row = cur.fetchone()
if row:
    print(f'  account_state: balance=\${row[0]:.2f}, total_pnl=\${row[1]:.2f}')
else:
    print('  account_state: NO DATA')

# Trade counts
cur.execute('SELECT COUNT(*) FROM trade_journal')
journal_count = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM trade_journal WHERE exit_timestamp IS NOT NULL')
closed_count = cur.fetchone()[0]
print(f'  trade_journal: {journal_count} total, {closed_count} closed')

# Activity log
cur.execute('SELECT COUNT(*) FROM activity_log')
activity_count = cur.fetchone()[0]
print(f'  activity_log: {activity_count} entries')

# Adaptations
cur.execute('SELECT COUNT(*) FROM adaptations')
adaptation_count = cur.fetchone()[0]
print(f'  adaptations: {adaptation_count}')

# Recent activity
cur.execute('SELECT activity_type, COUNT(*) FROM activity_log GROUP BY activity_type ORDER BY COUNT(*) DESC LIMIT 5')
print('  Top activity types:')
for row in cur.fetchall():
    print(f'    - {row[0]}: {row[1]}')

conn.close()
"
echo ""

echo "=== 2. SNIPER STATE (JSON) ==="
if [ -f "$SNIPER_STATE" ]; then
    python3 -c "
import json
with open('$SNIPER_STATE') as f:
    state = json.load(f)

balance = state.get('balance', 'N/A')
positions = state.get('positions', {})
closed = state.get('closed_positions', [])
total_pnl = state.get('total_pnl', 0)

print(f'  balance: \${balance}')
print(f'  open_positions: {len(positions)}')
print(f'  closed_positions: {len(closed)}')
print(f'  total_pnl: \${total_pnl:.2f}' if isinstance(total_pnl, (int, float)) else f'  total_pnl: {total_pnl}')
"
else
    echo "  WARNING: Sniper state file not found"
fi
echo ""

echo "=== 3. DATA CONSISTENCY CHECK ==="
python3 -c "
import sqlite3
import json
import os

errors = []
warnings = []

# Load database state
conn = sqlite3.connect('$DB_PATH')
cur = conn.cursor()

cur.execute('SELECT balance FROM account_state LIMIT 1')
row = cur.fetchone()
db_balance = row[0] if row else None

cur.execute('SELECT COUNT(*) FROM trade_journal WHERE exit_timestamp IS NOT NULL')
db_closed_trades = cur.fetchone()[0]

cur.execute('SELECT COALESCE(SUM(pnl), 0) FROM trade_journal WHERE exit_timestamp IS NOT NULL')
db_total_pnl = cur.fetchone()[0]

conn.close()

# Load JSON state
json_balance = None
json_closed_trades = 0
json_total_pnl = 0
if os.path.exists('$SNIPER_STATE'):
    with open('$SNIPER_STATE') as f:
        state = json.load(f)
        json_balance = state.get('balance')
        json_closed_trades = len(state.get('closed_positions', []))
        json_total_pnl = state.get('total_pnl', 0)

# Compare
if db_balance is not None and json_balance is not None:
    if abs(db_balance - json_balance) > 0.01:
        errors.append(f'Balance mismatch: DB=\${db_balance:.2f}, JSON=\${json_balance:.2f}')
elif db_balance == 1000.0:  # Initial value never updated
    warnings.append('RT-001: account_state has initial value (\$1000) - update_account_state() never called')

if db_closed_trades != json_closed_trades:
    warnings.append(f'Closed trade count differs: DB={db_closed_trades}, JSON={json_closed_trades}')

if abs(db_total_pnl - json_total_pnl) > 1.0:
    warnings.append(f'Total P&L differs: DB=\${db_total_pnl:.2f}, JSON=\${json_total_pnl:.2f}')

# Report
if errors:
    print('  ERRORS:')
    for e in errors:
        print(f'    ❌ {e}')
if warnings:
    print('  WARNINGS:')
    for w in warnings:
        print(f'    ⚠️  {w}')
if not errors and not warnings:
    print('  ✅ All consistency checks passed')
"
echo ""

echo "=== 4. KNOWN BUG CHECK ==="
python3 -c "
import sqlite3

conn = sqlite3.connect('$DB_PATH')
cur = conn.cursor()

print('  RT-001: update_account_state() never called')
cur.execute('SELECT balance FROM account_state LIMIT 1')
row = cur.fetchone()
if row and row[0] == 1000.0:
    print('    Status: CONFIRMED (balance stuck at initial \$1000)')
else:
    print('    Status: FIXED or N/A')

print()
print('  RT-002: open_trades/closed_trades tables empty')
cur.execute('SELECT COUNT(*) FROM open_trades')
open_count = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM closed_trades')
closed_count = cur.fetchone()[0]
if open_count == 0 and closed_count == 0:
    cur.execute('SELECT COUNT(*) FROM trade_journal')
    journal_count = cur.fetchone()[0]
    print(f'    Status: CONFIRMED (0 rows in both tables, but {journal_count} in trade_journal)')
else:
    print(f'    Status: Tables have data (open={open_count}, closed={closed_count})')

conn.close()
"
echo ""

echo "=== AUDIT COMPLETE ==="
echo "Run 'python scripts/audit_runtime.py' for comprehensive verification"
