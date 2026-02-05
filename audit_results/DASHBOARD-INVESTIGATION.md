# Dashboard Investigation Results

**Date:** 2026-02-05
**Symptom:** Dashboard shows impossible data (45h uptime, $9,920.75 balance with +$0.75 P&L)

---

## 1. Database State

### Raw Output
```
=== Database file info ===
-rwxrwxrwx 1 jblac jblac  2105344 Feb  5 11:33 data/trading_bot.db
-rwxrwxrwx 1 jblac jblac 47497216 Feb  3 13:23 data/trading_bot.db.backup_20260203_132358
-rwxrwxrwx 1 jblac jblac   299008 Feb  3 13:33 data/trading_bot.db.backup_20260203_133311

=== Tables in database ===
23 tables including: account_state, closed_trades, open_trades, active_conditions,
profit_snapshots, equity_points, runtime_state, etc.

=== Account state ===
Columns: ['id', 'balance', 'available_balance', 'in_positions', 'total_pnl', 'daily_pnl', 'trade_count_today', 'last_updated']
(1, 1000.0, 1000.0, 0.0, 0.0, 0.0, 0, '2026-02-03 20:33:12')

=== Trade counts ===
closed_trades: 0
open_trades: 0
active_conditions: 84 (all expired, from earlier today)

=== Runtime state ===
(96, 'shutdown_time', '2026-02-05T11:29:33.270501', '2026-02-05 18:29:33')
(99, 'uptime_seconds', '63.6', '2026-02-05 18:29:33')
(100, 'tick_count', '7298', '2026-02-05 18:29:33')
```

### Analysis
- Database was NOT properly reset — account_state shows $1,000 balance from Feb 3
- 0 closed trades, 0 open trades
- 84 stale conditions from earlier testing
- Runtime state shows 63.6s uptime (from fresh test run), NOT 45 hours

---

## 2. Dashboard Data Sources

### Raw Output
```
=== Balance source in dashboard_v2.py ===
565:            data["balance"] = status.get("balance", 0)

=== P&L source in dashboard_v2.py ===
566:            data["total_pnl"] = status.get("total_pnl", 0)

=== Status source ===
562:            status = self.system.sniper.get_status()

=== Uptime source ===
src/dashboard_v2.py:169:                uptime = status["health"].get("uptime_seconds", 0)
src/main.py:117-119:    def uptime_seconds(self) -> float:
                            return time.time() - self.start_time
```

### Analysis
- Dashboard gets balance/P&L from `self.system.sniper.get_status()`
- Uptime comes from `status["health"].get("uptime_seconds", 0)`
- **The dashboard serves data from its parent process's in-memory state, NOT from the database**

---

## 3. Sniper State

### Raw Output
```
=== Sniper state file (data/sniper_state.json) ===
{
  "balance": 10000.0,
  "initial_balance": 10000.0,
  "total_pnl": 0.0,
  "trades_executed": 0,
  "conditions": [],
  "positions": [],
  "saved_at": "2026-02-05T11:29:33.278545"
}

=== Sniper get_status() returns ===
{
    "balance": self.balance,
    "initial_balance": self.initial_balance,
    "total_pnl": self.total_pnl,
    ...
}
```

### Analysis
- Sniper state file shows FRESH state: $10,000 balance, $0 P&L
- But dashboard is NOT reading from this file
- Dashboard reads from the running process's in-memory Sniper instance

---

## 4. Running Processes

### Raw Output
```
=== Python processes ===
jblac  15720  0.3  0.4 306692 75988 pts/3  Sl+  Feb04  4:19 /usr/bin/python3 src/main_v2.py --dashboard --port 8080

=== Process uptime ===
18:42:13 (18 hours, 42 minutes)

=== What's listening on port 8080? ===
LISTEN  0  2048  0.0.0.0:8080  0.0.0.0:*  users:(("python3",pid=15720,fd=7))

=== Does main_v2.py exist? ===
ls: cannot access 'src/main_v2.py': No such file or directory
```

### Analysis
**CRITICAL FINDING: ZOMBIE PROCESS**
- Process 15720 has been running since Feb04 (~18.7 hours)
- It's running `src/main_v2.py` — a file that NO LONGER EXISTS
- This zombie is holding port 8080, blocking new processes
- When new `main.py` tries to start, it crashes because port 8080 is taken
- **The dashboard is being served by this zombie with its stale in-memory state**

---

## 5. Log Evidence

### Raw Output
```
=== Last lines of trading_bot.log ===
[06:38:19] ✓ Cycle #2991 complete | BUY (95%) | Balance: $990.83 | 2.0s
[Shutdown signal received]

=== Phase 3 activity ===
No Phase 3 logs (grep found nothing relevant)

=== When did bot start ===
[12:42:30] Cycle #1 starting...
```

### Analysis
- Logs are OLD — from the previous system
- No Phase 3 initialization logs visible
- Balance in logs ($990.83) differs from dashboard ($9,920.75)
- The log format is from old Phase 1 system, not Phase 2

---

## 6. P&L Source Comparison

### Raw Output
```
=== Database closed_trades P&L ===
SUM(pnl_usd): None (no trades)

=== account_state ===
balance: 1000.0
total_pnl: 0.0

=== profit_snapshots (recent) ===
id=31: ending_balance=$10,084.76, total_pnl=$84.76 (hour snapshot)
id=30: ending_balance=$10,339.05, total_pnl=$339.05 (day snapshot)

=== sniper_state.json ===
balance: 10000.0
total_pnl: 0.0
```

### Analysis
**Four different data sources show four different states:**
| Source | Balance | Total P&L |
|--------|---------|-----------|
| Dashboard (live) | $9,920.75 | +$0.75 |
| Database account_state | $1,000.00 | $0.00 |
| Database profit_snapshots | $10,339.05 | +$339.05 |
| sniper_state.json | $10,000.00 | $0.00 |

The sources are completely inconsistent because they're from different sessions and different code versions.

---

## ROOT CAUSE HYPOTHESIS

Based on evidence above, the dashboard shows wrong data because:

1. **A ZOMBIE PROCESS (PID 15720) is running `src/main_v2.py`** — a file that was deleted/renamed during the Phase 2 transition
   - Evidence: `ps aux` shows process running main_v2.py
   - Evidence: `ls src/main_v2.py` returns "No such file or directory"
   - Evidence: Process started Feb04, running 18+ hours

2. **The zombie holds port 8080**, blocking new bot startups
   - Evidence: `ss -tlnp | grep 8080` shows PID 15720 listening
   - Evidence: New `main.py` process exits with status 1 (port conflict)

3. **The dashboard serves the zombie's stale in-memory state**
   - Evidence: Dashboard gets data from `self.system.sniper.get_status()`
   - Evidence: This returns whatever the parent process's Sniper has in memory
   - Evidence: The zombie's Sniper has old state from yesterday's trading

4. **The $9,920.75 balance with +$0.75 P&L is the zombie's stale data**
   - The math doesn't add up because it's accumulated from old trades that are no longer in the database
   - The database was reset but the zombie wasn't restarted

---

## WHAT NEEDS TO BE FIXED

### Immediate (must do before anything else works):
1. **Kill the zombie process:** `kill 15720`
2. **Verify port 8080 is free:** `ss -tlnp | grep 8080`

### Root cause prevention:
1. **Add PID file check to start.sh** — Don't start if old process running
2. **Add port check to start.sh** — Fail fast if 8080 is occupied
3. **Consider port conflict detection in main.py** — Warn clearly on startup

### Data consistency:
1. **Database account_state is stale** — Shows $1,000 from Feb 3
2. **profit_snapshots has data** — From a different session with different balance
3. **Need to reset database** OR reconcile with sniper_state.json

### Not broken (for reference):
- `sniper_state.json` — Correctly shows $10,000 fresh state
- `src/main.py` — Correctly initializes Phase 3 (confirmed from test run)
- `src/dashboard_v2.py` — Correctly reads from Sniper (just reading from wrong process)

---

## VERIFICATION STEPS BEFORE ANY FIX

1. `kill 15720` — Kill the zombie
2. `ss -tlnp | grep 8080` — Confirm port is free
3. `./scripts/start.sh` — Start fresh
4. `curl localhost:8080/api/status` — Check dashboard shows fresh data
5. Verify balance = $10,000, P&L = $0, uptime = seconds (not hours)
