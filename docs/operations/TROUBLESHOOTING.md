# Troubleshooting Guide

**Last Updated:** February 3, 2026
**Phase:** 2 Complete

Common issues and how to fix them.

---

## Quick Diagnosis

```bash
# Is bot running?
pgrep -f "main_v2.py"

# Is dashboard running?
curl -s http://localhost:8080/api/status | jq .

# Is LLM responding?
curl -s http://localhost:11434/api/tags | jq .

# Is WebSocket connected?
grep "WebSocket" logs/bot.log | tail -5

# Recent errors?
grep -i error logs/bot.log | tail -10

# Database accessible?
sqlite3 data/trading_bot.db "SELECT COUNT(*) FROM trade_journal;"
```

---

## Common Issues

### Bot Not Running

**Symptoms:** No new trades, dashboard shows stale data

**Diagnosis:**
```bash
pgrep -f "main_v2.py"
# No output = not running
```

**Solutions:**

1. Start manually to see errors:
   ```bash
   python src/main_v2.py --mode paper
   ```

2. Check logs for crash:
   ```bash
   tail -100 logs/bot.log | grep -i -E "(error|exception|traceback)"
   ```

3. Restart:
   ```bash
   python src/main_v2.py --mode paper --dashboard
   ```

---

### WebSocket Not Connecting

**Symptoms:** No price updates, "WebSocket disconnected" in logs

**Diagnosis:**
```bash
grep "WebSocket" logs/bot.log | tail -10
```

**Solutions:**

1. Check internet connectivity:
   ```bash
   ping -c 3 stream.binance.com
   ```

2. Check if Binance is accessible:
   ```bash
   curl -s "https://api.binance.com/api/v3/ping"
   ```

3. Restart the bot (WebSocket reconnects automatically):
   ```bash
   pkill -f "main_v2.py"
   python src/main_v2.py --mode paper --dashboard
   ```

4. If persistent, check firewall/proxy settings

---

### LLM Not Responding

**Symptoms:** No new conditions generated, logs show LLM errors

**Diagnosis:**
```bash
curl -s --max-time 10 http://localhost:11434/api/tags
# Should return model list
```

**Solutions:**

1. Check Ollama is running:
   ```bash
   ollama list
   ```

2. Start Ollama:
   ```bash
   ollama serve
   ```

3. For WSL, check Windows host:
   ```bash
   curl -s http://172.27.144.1:11434/api/tags
   ```

4. Verify correct model is available:
   ```bash
   ollama pull qwen2.5:14b
   ```

5. Test generation:
   ```bash
   curl -X POST http://localhost:11434/api/generate \
     -d '{"model":"qwen2.5:14b","prompt":"Hello"}'
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
   pgrep -f "dashboard"
   ```

2. Check port conflict:
   ```bash
   lsof -i :8080
   # If another process, kill it or change port
   ```

3. Start with different port:
   ```bash
   python src/main_v2.py --dashboard --port 9090
   ```

4. Check for startup errors:
   ```bash
   python src/dashboard_v2.py 2>&1 | head -50
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
   pgrep -af "main_v2.py"
   # Should be only one
   ```

2. Kill duplicates:
   ```bash
   pkill -f "main_v2.py"
   ```

3. Wait and restart:
   ```bash
   sleep 5
   python src/main_v2.py --mode paper --dashboard
   ```

---

### No Trades Being Made

**Symptoms:** Bot running but no new trades

**Diagnosis:**
```bash
# Check recent activity
tail -50 logs/bot.log | grep -E "(condition|triggered|executed)"

# Check conditions
sqlite3 data/trading_bot.db "SELECT COUNT(*) FROM trade_conditions WHERE expires_at > datetime('now');"
```

**Possible Causes:**

1. **No conditions generated:**
   - Check Strategist is running
   - Check LLM is responding
   - Check market_state is populated

2. **All coins blacklisted:**
   ```bash
   sqlite3 data/trading_bot.db "SELECT coin FROM coin_scores WHERE is_blacklisted = 1;"
   ```

   Solution: Unblacklist via dashboard or:
   ```bash
   sqlite3 data/trading_bot.db "UPDATE coin_scores SET is_blacklisted = 0 WHERE coin = 'BTC';"
   ```

3. **Conditions not triggering:**
   - Prices may not be reaching entry levels
   - This is normal market behavior

4. **WebSocket not providing prices:**
   ```bash
   grep "price" logs/bot.log | tail -5
   ```

---

### Learning Not Working

**Symptoms:** No adaptations, coin scores not updating

**Diagnosis:**
```bash
# Recent adaptations
sqlite3 data/trading_bot.db "SELECT * FROM adaptations ORDER BY applied_at DESC LIMIT 5;"

# Coin score updates
sqlite3 data/trading_bot.db "SELECT coin, last_updated FROM coin_scores ORDER BY last_updated DESC LIMIT 5;"

# Reflection activity
sqlite3 data/trading_bot.db "SELECT * FROM reflections ORDER BY completed_at DESC LIMIT 3;"
```

**Solutions:**

1. **QuickUpdate not processing:**
   - Trades must close for learning to trigger
   - Check trades are actually closing:
     ```bash
     sqlite3 data/trading_bot.db "SELECT COUNT(*) FROM trade_journal WHERE exit_time > datetime('now', '-1 hour');"
     ```

2. **Reflection not running:**
   - Runs hourly by default
   - Check last reflection time:
     ```bash
     sqlite3 data/trading_bot.db "SELECT MAX(completed_at) FROM reflections;"
     ```

3. **LLM not generating insights:**
   - Check LLM is available
   - Check reflection logs:
     ```bash
     grep "reflection" logs/bot.log | tail -20
     ```

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
FROM trade_journal
WHERE exit_time > datetime('now', '-24 hours');
"
```

**Possible Causes:**

1. **Bad patterns active:**
   ```bash
   sqlite3 data/trading_bot.db "
   SELECT pattern_id, description, win_rate, confidence
   FROM trading_patterns
   WHERE is_active = 1 AND win_rate < 0.4;
   "
   ```

   Solution: Deactivate via dashboard or:
   ```bash
   sqlite3 data/trading_bot.db "UPDATE trading_patterns SET is_active = 0 WHERE pattern_id = 'xxx';"
   ```

2. **Poor performing coins:**
   ```bash
   sqlite3 data/trading_bot.db "
   SELECT coin, win_rate, total_pnl, status
   FROM coin_scores
   WHERE total_pnl < 0
   ORDER BY total_pnl ASC LIMIT 10;
   "
   ```

   Solution: Let the system blacklist them naturally, or force blacklist via dashboard

3. **Market conditions changed:**
   - Review when losses started
   - Consider pausing and analyzing

---

### Pattern Library Issues

**Symptoms:** Patterns not being used, low confidence scores

**Diagnosis:**
```bash
sqlite3 data/trading_bot.db "
SELECT pattern_id, times_used, wins, losses, confidence, is_active
FROM trading_patterns
ORDER BY times_used DESC LIMIT 10;
"
```

**Solutions:**

1. **Patterns not matching:**
   - Check pattern conditions vs current market
   - Patterns may be too specific

2. **Low confidence:**
   - Confidence drops after losses
   - This is expected behavior
   - Patterns auto-deactivate at confidence < 0.2

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

2. Clean old insights:
   ```bash
   sqlite3 data/trading_bot.db "DELETE FROM insights WHERE created_at < datetime('now', '-30 days');"
   sqlite3 data/trading_bot.db "DELETE FROM reflections WHERE completed_at < datetime('now', '-30 days');"
   sqlite3 data/trading_bot.db "VACUUM;"
   ```

---

## Recovery Procedures

### Full Restart
```bash
pkill -f "main_v2.py"
sleep 5
python src/main_v2.py --mode paper --dashboard
```

### Database Recovery
```bash
# Stop bot
pkill -f "main_v2.py"

# Check integrity
sqlite3 data/trading_bot.db "PRAGMA integrity_check;"

# If corrupted, restore from backup
cp data/backups/trading_bot_YYYYMMDD.db data/trading_bot.db

# Restart
python src/main_v2.py --mode paper --dashboard
```

### Reset Learning (CAUTION)
```bash
# This resets all learning - use only if learning is badly corrupted
pkill -f "main_v2.py"

sqlite3 data/trading_bot.db "
DELETE FROM coin_scores;
DELETE FROM trading_patterns;
DELETE FROM regime_rules;
DELETE FROM adaptations;
DELETE FROM insights;
DELETE FROM reflections;
"

python src/main_v2.py --mode paper --dashboard
```

---

## Getting Help

1. Check this guide first
2. Review logs: `tail -100 logs/bot.log`
3. Check system status: `curl http://localhost:8080/api/status`
4. Run analysis: `python scripts/analyze_performance.py --days 1`

---

## Related Documentation

- [RUNBOOK.md](./RUNBOOK.md) - Day-to-day operations
- [PAPER-TRADING-GUIDE.md](./PAPER-TRADING-GUIDE.md) - Paper trading setup
- [DASHBOARD-GUIDE.md](./DASHBOARD-GUIDE.md) - Dashboard usage
