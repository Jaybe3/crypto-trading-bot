#!/bin/bash
# =============================================================================
# COMPREHENSIVE SYSTEM AUDIT
# Run this BEFORE and AFTER any code changes
# =============================================================================

set -e
cd "$(dirname "$0")/.."

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="audit_results/audit_${TIMESTAMP}.txt"
mkdir -p audit_results

echo "========================================"
echo "CRYPTO TRADING BOT - SYSTEM AUDIT"
echo "========================================"
echo "Timestamp: $(date)"
echo "Report: $REPORT_FILE"
echo ""

# Tee output to both console and file
exec > >(tee -a "$REPORT_FILE") 2>&1

FAILURES=0
WARNINGS=0

# -----------------------------------------------------------------------------
# 1. CODE AUDIT
# -----------------------------------------------------------------------------
echo "=== 1. CODE AUDIT ==="

echo -n "  1.1 Import checks: "
if python3 -c "
import sys
sys.path.insert(0, '.')
modules = ['src.main', 'src.strategist', 'src.sniper', 'src.dashboard_v2',
           'src.journal', 'src.reflection', 'src.calculations', 'src.knowledge',
           'src.profitability', 'src.database', 'src.quick_update']
for mod in modules:
    __import__(mod)
" 2>/dev/null; then
    echo "PASS"
else
    echo "FAIL"
    FAILURES=$((FAILURES + 1))
fi

echo -n "  1.2 Duplicate calculations: "
DUPES=$(grep -rn "current.*-.*entry.*\*.*size\|entry.*-.*current.*\*.*size" src/ --include="*.py" 2>/dev/null | grep -v __pycache__ | grep -v calculations.py | grep -v test | wc -l)
if [ "$DUPES" -eq 0 ]; then
    echo "PASS (0 duplicates)"
else
    echo "FAIL ($DUPES duplicates found)"
    FAILURES=$((FAILURES + 1))
fi

echo -n "  1.3 Test suite: "
TEST_RESULT=$(python3 -m pytest tests/ -q --tb=no 2>&1 | tail -1)
if echo "$TEST_RESULT" | grep -q "passed"; then
    echo "PASS - $TEST_RESULT"
else
    echo "FAIL - $TEST_RESULT"
    FAILURES=$((FAILURES + 1))
fi

# -----------------------------------------------------------------------------
# 2. DATABASE AUDIT
# -----------------------------------------------------------------------------
echo ""
echo "=== 2. DATABASE AUDIT ==="

DB_FILE="data/trading_bot.db"
if [ ! -f "$DB_FILE" ]; then
    DB_FILE="data/trading.db"
fi

echo -n "  2.1 Database exists: "
if [ -f "$DB_FILE" ]; then
    echo "PASS ($DB_FILE)"
else
    echo "FAIL - No database found"
    FAILURES=$((FAILURES + 1))
fi

if [ -f "$DB_FILE" ]; then
    echo -n "  2.2 Corrupted timestamps: "
    CORRUPTED=$(python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_FILE')
cur = conn.cursor()
cur.execute(\"SELECT COUNT(*) FROM trade_journal WHERE entry_time < '2000-01-01'\")
print(cur.fetchone()[0])
conn.close()
" 2>/dev/null || echo "ERROR")
    if [ "$CORRUPTED" = "0" ]; then
        echo "PASS (0 corrupted)"
    elif [ "$CORRUPTED" = "ERROR" ]; then
        echo "SKIP (query failed)"
    else
        echo "WARN ($CORRUPTED corrupted records)"
        WARNINGS=$((WARNINGS + 1))
    fi

    echo -n "  2.3 Account state fresh: "
    ACCT_BAL=$(python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_FILE')
cur = conn.cursor()
cur.execute('SELECT balance FROM account_state LIMIT 1')
row = cur.fetchone()
print(row[0] if row else 'NONE')
conn.close()
" 2>/dev/null || echo "ERROR")
    if [ "$ACCT_BAL" != "1000" ] && [ "$ACCT_BAL" != "1000.0" ] && [ "$ACCT_BAL" != "NONE" ]; then
        echo "PASS (balance=$ACCT_BAL)"
    else
        echo "WARN (balance=$ACCT_BAL - RT-001: may be stale)"
        WARNINGS=$((WARNINGS + 1))
    fi

    echo -n "  2.4 Empty tables: "
    EMPTY_COUNT=$(python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_FILE')
cur = conn.cursor()
cur.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
tables = [r[0] for r in cur.fetchall()]
empty = 0
for t in tables:
    cur.execute(f'SELECT COUNT(*) FROM {t}')
    if cur.fetchone()[0] == 0:
        empty += 1
print(empty)
conn.close()
" 2>/dev/null || echo "ERROR")
    if [ "$EMPTY_COUNT" = "0" ]; then
        echo "PASS (0 empty)"
    else
        echo "INFO ($EMPTY_COUNT empty tables)"
    fi
fi

# -----------------------------------------------------------------------------
# 3. RUNTIME AUDIT (if bot is running)
# -----------------------------------------------------------------------------
echo ""
echo "=== 3. RUNTIME AUDIT ==="

echo -n "  3.1 Bot API reachable: "
if curl -s http://localhost:8080/api/status > /dev/null 2>&1; then
    echo "PASS"

    echo -n "  3.2 Knowledge endpoints: "
    KNOWLEDGE_FAIL=0
    for endpoint in /api/knowledge/coins /api/knowledge/patterns /api/knowledge/rules; do
        CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080$endpoint" 2>/dev/null)
        if [ "$CODE" != "200" ]; then
            KNOWLEDGE_FAIL=$((KNOWLEDGE_FAIL + 1))
        fi
    done
    if [ "$KNOWLEDGE_FAIL" -eq 0 ]; then
        echo "PASS (3/3 endpoints OK)"
    else
        echo "FAIL ($KNOWLEDGE_FAIL/3 endpoints broken - RT-009)"
        FAILURES=$((FAILURES + 1))
    fi

    echo -n "  3.3 Profitability endpoint: "
    CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080/api/profitability/snapshot" 2>/dev/null)
    if [ "$CODE" = "200" ]; then
        echo "PASS"
    else
        echo "FAIL (HTTP $CODE)"
        FAILURES=$((FAILURES + 1))
    fi
else
    echo "NOT RUNNING - skipping runtime checks"
fi

# -----------------------------------------------------------------------------
# 4. LEARNING SYSTEM AUDIT
# -----------------------------------------------------------------------------
echo ""
echo "=== 4. LEARNING SYSTEM AUDIT ==="

if [ -f "$DB_FILE" ]; then
    echo -n "  4.1 Reflections exist: "
    REFLECTIONS=$(python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_FILE')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM reflections')
print(cur.fetchone()[0])
conn.close()
" 2>/dev/null || echo "0")
    echo "$REFLECTIONS reflections"

    echo -n "  4.2 Insights saved: "
    INSIGHTS=$(python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_FILE')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM insights')
print(cur.fetchone()[0])
conn.close()
" 2>/dev/null || echo "0")
    if [ "$INSIGHTS" = "0" ]; then
        echo "WARN (0 insights - RT-006: learning broken)"
        WARNINGS=$((WARNINGS + 1))
    else
        echo "PASS ($INSIGHTS insights)"
    fi

    echo -n "  4.3 Adaptations applied: "
    ADAPTATIONS=$(python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_FILE')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM adaptations')
print(cur.fetchone()[0])
conn.close()
" 2>/dev/null || echo "0")
    if [ "$ADAPTATIONS" = "0" ]; then
        echo "WARN (0 adaptations - RT-006: learning broken)"
        WARNINGS=$((WARNINGS + 1))
    else
        echo "PASS ($ADAPTATIONS adaptations)"
    fi

    echo -n "  4.4 Coin score tracking: "
    SCORES=$(python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_FILE')
cur = conn.cursor()
cur.execute('SELECT COALESCE(SUM(total_trades), 0) FROM coin_scores')
scores = cur.fetchone()[0]
cur.execute(\"SELECT COUNT(*) FROM trade_journal WHERE status='closed'\")
journal = cur.fetchone()[0]
print(f'{scores}/{journal}')
conn.close()
" 2>/dev/null || echo "ERROR")
    IFS='/' read -r SCORE_COUNT JOURNAL_COUNT <<< "$SCORES"
    if [ "$SCORE_COUNT" = "$JOURNAL_COUNT" ]; then
        echo "PASS ($SCORES trades tracked)"
    else
        GAP=$((JOURNAL_COUNT - SCORE_COUNT))
        echo "WARN ($SCORES - gap of $GAP, RT-010)"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# -----------------------------------------------------------------------------
# 5. DATA CONSISTENCY AUDIT
# -----------------------------------------------------------------------------
echo ""
echo "=== 5. DATA CONSISTENCY AUDIT ==="

if [ -f "$DB_FILE" ]; then
    echo "  5.1 Data source comparison:"
    python3 -c "
import sqlite3
import json
import os

conn = sqlite3.connect('$DB_FILE')
cur = conn.cursor()

# Database
cur.execute('SELECT balance FROM account_state LIMIT 1')
row = cur.fetchone()
db_balance = row[0] if row else 0

cur.execute(\"SELECT COALESCE(SUM(pnl_usd), 0) FROM trade_journal WHERE status='closed'\")
db_pnl = cur.fetchone()[0]

# JSON
json_balance = 0
json_pnl = 0
if os.path.exists('data/sniper_state.json'):
    try:
        with open('data/sniper_state.json') as f:
            state = json.load(f)
            json_balance = state.get('balance', 0)
            json_pnl = state.get('total_pnl', 0)
    except:
        pass

print(f'    DB account_state balance: \${db_balance:.2f}')
print(f'    DB trade_journal P&L sum: \${db_pnl:.2f}')
print(f'    JSON sniper_state balance: \${json_balance:.2f}')
print(f'    JSON sniper_state P&L: \${json_pnl:.2f}')

# Check for disagreement
if abs(db_balance - json_balance) > 1:
    print(f'    WARNING: Balance mismatch (RT-003)')
if abs(db_pnl - json_pnl) > 1:
    print(f'    WARNING: P&L mismatch (RT-003)')

conn.close()
" 2>/dev/null || echo "    (comparison failed)"
fi

# -----------------------------------------------------------------------------
# SUMMARY
# -----------------------------------------------------------------------------
echo ""
echo "========================================"
echo "SUMMARY"
echo "========================================"
echo "Failures: $FAILURES"
echo "Warnings: $WARNINGS"
echo ""

if [ "$FAILURES" -eq 0 ]; then
    if [ "$WARNINGS" -eq 0 ]; then
        echo "AUDIT PASSED"
    else
        echo "AUDIT PASSED WITH WARNINGS"
    fi
else
    echo "AUDIT FAILED ($FAILURES critical issues)"
fi
echo "========================================"
echo "Report saved to: $REPORT_FILE"

exit $FAILURES
