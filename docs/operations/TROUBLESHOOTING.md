# Troubleshooting Guide

Common issues and how to fix them.

---

## Quick Diagnosis

```bash
# Is bot running?
pgrep -f "python.*main.py"

# Is dashboard running?
curl -s http://localhost:8080/api/status | jq .

# Is LLM responding?
curl -s http://172.27.144.1:11434/api/tags | jq .

# Recent errors?
grep -i error logs/bot.log | tail -10

# Database accessible?
sqlite3 data/trading_bot.db "SELECT COUNT(*) FROM closed_trades;"
```

---

## Common Issues

### Bot Not Running

**Symptoms:** No new trades, dashboard shows stale data

**Diagnosis:**
```bash
pgrep -f "python.*main.py"
# No output = not running
```

**Solutions:**

1. Check supervisor:
   ```bash
   supervisorctl status
   ```

2. Start manually to see errors:
   ```bash
   python src/main.py
   ```

3. Check logs for crash:
   ```bash
   tail -100 logs/bot.log | grep -i -E "(error|exception|traceback)"
   ```

4. Restart:
   ```bash
   bash scripts/start.sh
   ```

---

### LLM Not Responding

**Symptoms:** All decisions are HOLD, logs show LLM errors

**Diagnosis:**
```bash
curl -s --max-time 10 http://172.27.144.1:11434/api/tags
# Should return model list
```

**Solutions:**

1. Check Ollama is running (on Windows):
   ```powershell
   ollama list
   ```

2. Start Ollama:
   ```powershell
   ollama serve
   ```

3. Check WSL can reach Windows:
   ```bash
   ping 172.27.144.1
   ```

4. Verify OLLAMA_HOST is correct:
   ```bash
   echo $OLLAMA_HOST
   # Should be Windows host IP
   ```

5. Find correct IP:
   ```bash
   ip route show default | awk '{print $3}'
   ```

---

### Dashboard Not Loading

**Symptoms:** Cannot access http://localhost:8080

**Diagnosis:**
```bash
curl -s http://localhost:8080/api/status
lsof -i :8080
```

**Solutions:**

1. Check if running:
   ```bash
   pgrep -f "python.*dashboard.py"
   ```

2. Check port conflict:
   ```bash
   lsof -i :8080
   # If another process, kill it or change port
   ```

3. Start dashboard:
   ```bash
   python src/dashboard.py
   ```

4. Check for errors:
   ```bash
   python src/dashboard.py 2>&1 | head -50
   ```

---

### Database Locked

**Symptoms:** Errors about "database is locked"

**Diagnosis:**
```bash
lsof data/trading_bot.db
```

**Solutions:**

1. Check for multiple bot instances:
   ```bash
   pgrep -af "python.*main.py"
   # Should be only one
   ```

2. Kill duplicates:
   ```bash
   pkill -f "python.*main.py"
   bash scripts/start.sh
   ```

3. If persists, restart everything:
   ```bash
   bash scripts/stop.sh
   sleep 5
   bash scripts/start.sh
   ```

---

### No Trades Being Made

**Symptoms:** Bot running but no new trades

**Diagnosis:**
```bash
# Check recent activity
tail -50 logs/bot.log | grep -E "(BUY|SELL|HOLD|rejected)"
```

**Possible Causes:**

1. **All coins in cooldown:**
   ```bash
   sqlite3 data/trading_bot.db "SELECT COUNT(*) FROM coin_cooldowns WHERE expires_at > datetime('now');"
   # If 45, all coins are cooling
   ```

   Solution: Wait for cooldowns to expire (30 min max)

2. **Exposure limit reached:**
   ```bash
   sqlite3 data/trading_bot.db "SELECT in_positions, balance FROM account_state;"
   # If in_positions > balance * 0.1, at limit
   ```

   Solution: Wait for positions to close

3. **LLM always returning HOLD:**
   Check logs for LLM responses

   Solution: Check LLM is working, review prompts

4. **Market data not updating:**
   ```bash
   sqlite3 data/trading_bot.db "SELECT coin, last_updated FROM market_data LIMIT 5;"
   # Should be recent
   ```

   Solution: Check CoinGecko API access

---

### High Loss Rate

**Symptoms:** Win rate below 40%, losing money

**Diagnosis:**
```bash
sqlite3 data/trading_bot.db "
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as win_rate
FROM closed_trades
WHERE closed_at > datetime('now', '-24 hours');
"
```

**Possible Causes:**

1. **Bad rules active:**
   ```bash
   sqlite3 data/trading_bot.db "
   SELECT id, rule_text, success_count, failure_count
   FROM trading_rules
   WHERE status = 'active'
   AND failure_count > success_count;
   "
   ```

   Solution: Deactivate bad rules:
   ```bash
   sqlite3 data/trading_bot.db "UPDATE trading_rules SET status = 'inactive' WHERE id = X;"
   ```

2. **Market conditions changed:**
   Review when losses started, correlate with market events

3. **Stop losses too tight:**
   Check if most losses are stop-loss exits

---

### Disk Space Issues

**Symptoms:** Errors about disk space, database errors

**Diagnosis:**
```bash
df -h .
du -sh data/ logs/
```

**Solutions:**

1. Rotate logs:
   ```bash
   find logs/ -name "*.log" -mtime +7 -delete
   ```

2. Compress old logs:
   ```bash
   gzip logs/*.log.1
   ```

3. Archive old database:
   ```bash
   sqlite3 data/trading_bot.db "DELETE FROM activity_log WHERE created_at < datetime('now', '-30 days');"
   sqlite3 data/trading_bot.db "VACUUM;"
   ```

---

## Recovery Procedures

### Full Restart
```bash
bash scripts/stop.sh
sleep 10
bash scripts/start.sh
bash scripts/status.sh
```

### Database Recovery
```bash
# Stop bot
bash scripts/stop.sh

# Check database integrity
sqlite3 data/trading_bot.db "PRAGMA integrity_check;"

# If corrupted, restore from backup
cp data/backups/trading_bot_YYYYMMDD.db data/trading_bot.db

# Restart
bash scripts/start.sh
```

### Reset to Clean State (CAUTION)
```bash
# This loses all data!
bash scripts/stop.sh
rm data/trading_bot.db
python -c "from src.database import Database; Database()"
bash scripts/start.sh
```

---

## Getting Help

1. Check this guide first
2. Review logs: `tail -100 logs/bot.log`
3. Check monitoring alerts: `sqlite3 data/trading_bot.db "SELECT * FROM monitoring_alerts WHERE status='open';"`
4. Run autonomous monitor: `python scripts/autonomous_monitor.py`

---

*Last Updated: February 2026*
