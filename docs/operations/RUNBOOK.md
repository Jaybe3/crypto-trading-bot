# Operations Runbook

Day-to-day operations guide for running the crypto trading bot.

---

## Quick Reference

### Start Everything
```bash
cd ~/crypto-trading-bot
bash scripts/start.sh
```

### Stop Everything
```bash
bash scripts/stop.sh
```

### Check Status
```bash
bash scripts/status.sh
```

### View Logs
```bash
tail -f logs/bot.log
```

### Emergency Stop
```bash
pkill -f "python.*main.py"
pkill -f "python.*dashboard.py"
```

---

## Daily Operations

### Morning Check

1. **Verify bot is running:**
   ```bash
   bash scripts/status.sh
   ```
   Should show both bot and dashboard running.

2. **Check overnight performance:**
   ```bash
   sqlite3 data/trading_bot.db "
   SELECT COUNT(*) as trades,
          SUM(pnl_usd) as total_pnl,
          SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins
   FROM closed_trades
   WHERE closed_at > datetime('now', '-24 hours');
   "
   ```

3. **Review dashboard:**
   Open http://localhost:8080 and check:
   - Current balance
   - Open positions
   - Recent trades
   - Any alerts

### Weekly Tasks

1. **Backup database:**
   ```bash
   cp data/trading_bot.db data/backups/trading_bot_$(date +%Y%m%d).db
   ```

2. **Review rule performance:**
   ```bash
   sqlite3 data/trading_bot.db "
   SELECT id, rule_text, success_count, failure_count,
          ROUND(success_count * 100.0 / (success_count + failure_count), 1) as rate
   FROM trading_rules
   WHERE status = 'active'
   ORDER BY rate DESC;
   "
   ```

3. **Check disk space:**
   ```bash
   du -sh data/ logs/
   ```

4. **Rotate logs if needed:**
   ```bash
   # Keep last 7 days
   find logs/ -name "*.log" -mtime +7 -delete
   ```

---

## Starting and Stopping

### Normal Start
```bash
bash scripts/start.sh
```

This starts:
- Trading bot (main.py)
- Dashboard (dashboard.py)
- Supervisor manages both

### Normal Stop
```bash
bash scripts/stop.sh
```

Gracefully stops both processes.

### Restart
```bash
bash scripts/restart.sh
```

### Start Individual Components

**Bot only:**
```bash
python src/main.py
```

**Dashboard only:**
```bash
python src/dashboard.py
```

---

## Monitoring

### Real-Time Logs
```bash
tail -f logs/bot.log
```

### Dashboard
- URL: http://localhost:8080
- Shows: balance, positions, trades, learnings, rules

### Prometheus Metrics
- URL: http://localhost:8080/metrics
- For external monitoring systems

### Health Check
```bash
bash scripts/health.sh
```

---

## Common Operations

### Check Current Positions
```bash
sqlite3 data/trading_bot.db "SELECT * FROM open_trades;"
```

### Check Recent Trades
```bash
sqlite3 data/trading_bot.db "
SELECT coin_name, pnl_usd, exit_reason, closed_at
FROM closed_trades
ORDER BY closed_at DESC
LIMIT 10;
"
```

### Check Active Rules
```bash
sqlite3 data/trading_bot.db "
SELECT id, status, success_count, failure_count
FROM trading_rules
WHERE status IN ('active', 'testing');
"
```

### Check Cooldowns
```bash
sqlite3 data/trading_bot.db "
SELECT coin_name, expires_at
FROM coin_cooldowns
WHERE expires_at > datetime('now');
"
```

### Manually Clear a Cooldown
```bash
sqlite3 data/trading_bot.db "
DELETE FROM coin_cooldowns WHERE coin_name = 'bitcoin';
"
```

### Reset Daily P&L Counter
```bash
sqlite3 data/trading_bot.db "
UPDATE account_state SET daily_pnl = 0, trade_count_today = 0;
"
```

---

## Database Management

### Backup
```bash
cp data/trading_bot.db data/backups/trading_bot_$(date +%Y%m%d_%H%M%S).db
```

### Restore from Backup
```bash
# Stop bot first!
bash scripts/stop.sh
cp data/backups/trading_bot_YYYYMMDD.db data/trading_bot.db
bash scripts/start.sh
```

### Query with SQLite
```bash
sqlite3 data/trading_bot.db
```

Useful commands:
- `.tables` - List all tables
- `.schema TABLE` - Show table structure
- `.mode column` - Pretty print
- `.headers on` - Show column names

---

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| OLLAMA_HOST | 172.27.144.1 | Ollama server address |
| LOOP_INTERVAL | 30 | Seconds between cycles |
| MIN_CONFIDENCE | 0.3 | Minimum trade confidence |

### Changing Configuration

Edit environment in start script or export before running:
```bash
export LOOP_INTERVAL=60
python src/main.py
```

---

## Supervisor Management

### Check Status
```bash
supervisorctl status
```

### Restart Bot
```bash
supervisorctl restart trading_bot
```

### Restart Dashboard
```bash
supervisorctl restart dashboard
```

### View Supervisor Logs
```bash
tail -f /var/log/supervisor/supervisord.log
```

---

*Last Updated: February 2026*
