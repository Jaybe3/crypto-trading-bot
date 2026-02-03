# Operations Runbook

**Last Updated:** February 3, 2026
**Phase:** 2 Complete

Day-to-day operations guide for running the crypto trading bot.

---

## Quick Reference

### Start Everything
```bash
python src/main_v2.py --mode paper --dashboard --port 8080
```

### Stop Everything
```bash
pkill -f "main_v2.py"
```

### Check Status
```bash
curl -s http://localhost:8080/api/status | jq .
```

### View Logs
```bash
tail -f logs/bot.log
```

---

## Daily Operations

### Morning Check

1. **Verify bot is running:**
   ```bash
   pgrep -f "main_v2.py"
   curl -s http://localhost:8080/api/status
   ```

2. **Check overnight performance:**
   ```bash
   sqlite3 data/trading_bot.db "
   SELECT COUNT(*) as trades,
          SUM(pnl_usd) as total_pnl,
          SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins
   FROM trade_journal
   WHERE exit_time > datetime('now', '-24 hours');
   "
   ```

3. **Review dashboard:**
   Open http://localhost:8080 and check:
   - WebSocket connected (green indicator)
   - Open positions
   - Recent trades
   - Any adaptations applied

4. **Check for errors:**
   ```bash
   grep -i error logs/bot.log | tail -10
   ```

### Evening Check

1. **Daily summary:**
   ```bash
   python scripts/daily_checkpoint.py
   ```

2. **Verify learning is active:**
   ```bash
   sqlite3 data/trading_bot.db "
   SELECT COUNT(*) FROM adaptations WHERE applied_at > datetime('now', '-24 hours');
   "
   ```

### Weekly Tasks

1. **Backup database:**
   ```bash
   cp data/trading_bot.db data/backups/trading_bot_$(date +%Y%m%d).db
   ```

2. **Review coin performance:**
   ```bash
   sqlite3 data/trading_bot.db "
   SELECT coin, total_trades, win_rate, total_pnl, status
   FROM coin_scores
   WHERE total_trades > 0
   ORDER BY total_pnl DESC;
   "
   ```

3. **Review pattern performance:**
   ```bash
   sqlite3 data/trading_bot.db "
   SELECT pattern_id, times_used, win_rate, confidence, is_active
   FROM trading_patterns
   WHERE times_used > 0
   ORDER BY win_rate DESC;
   "
   ```

4. **Check disk space:**
   ```bash
   du -sh data/ logs/
   ```

5. **Rotate logs if needed:**
   ```bash
   find logs/ -name "*.log" -mtime +7 -delete
   ```

6. **Generate weekly report:**
   ```bash
   python scripts/analyze_performance.py --days 7
   ```

---

## Starting and Stopping

### Normal Start
```bash
# Ensure Ollama is running first
ollama serve &

# Start trading system
python src/main_v2.py --mode paper --dashboard --port 8080
```

This starts:
- MarketFeed (WebSocket connection)
- Strategist (LLM condition generation)
- Sniper (Trade execution)
- QuickUpdate (Instant learning)
- ReflectionEngine (Hourly analysis)
- Dashboard (Web interface)

### Normal Stop
```bash
# Ctrl+C in terminal, or:
pkill -f "main_v2.py"
```

The system gracefully:
- Closes WebSocket connection
- Saves all state to database
- Records any open positions

### Background Mode
```bash
nohup python src/main_v2.py --mode paper --dashboard > logs/bot.log 2>&1 &
```

Check it's running:
```bash
pgrep -f "main_v2.py"
tail -f logs/bot.log
```

---

## Monitoring

### Real-Time Logs
```bash
tail -f logs/bot.log
```

### Dashboard
- URL: http://localhost:8080
- Pages: Overview, Knowledge, Adaptations, Profitability

### API Health Check
```bash
curl -s http://localhost:8080/api/status | jq .
```

Expected response:
```json
{
  "status": "running",
  "websocket_connected": true,
  "llm_available": true,
  "uptime_seconds": 3600
}
```

### Key Metrics to Watch

| Metric | Check Command | Concern If |
|--------|--------------|------------|
| Win Rate | `curl /api/profitability` | < 45% |
| WebSocket | `curl /api/status` | disconnected |
| Trade Count | DB query | 0 in 6 hours |
| Adaptations | DB query | 0 in 24 hours |

---

## Common Operations

### Check Current Positions
```bash
curl -s http://localhost:8080/api/positions | jq .
```
Or:
```bash
sqlite3 data/trading_bot.db "SELECT * FROM open_positions;"
```

### Check Recent Trades
```bash
curl -s "http://localhost:8080/api/trades?limit=10" | jq .
```
Or:
```bash
sqlite3 data/trading_bot.db "
SELECT coin, direction, pnl_usd, exit_reason, exit_time
FROM trade_journal
ORDER BY exit_time DESC
LIMIT 10;
"
```

### Check Coin Scores
```bash
curl -s http://localhost:8080/api/knowledge/coins | jq .
```

### Check Active Patterns
```bash
sqlite3 data/trading_bot.db "
SELECT pattern_id, description, confidence, is_active
FROM trading_patterns
WHERE is_active = 1
ORDER BY confidence DESC;
"
```

### Force Blacklist a Coin
Via dashboard `/overrides` page, or:
```bash
sqlite3 data/trading_bot.db "
UPDATE coin_scores
SET is_blacklisted = 1, blacklist_reason = 'Manual blacklist', status = 'blacklisted'
WHERE coin = 'DOGE';
"
```

### Unblacklist a Coin
```bash
sqlite3 data/trading_bot.db "
UPDATE coin_scores
SET is_blacklisted = 0, blacklist_reason = NULL, status = 'normal'
WHERE coin = 'DOGE';
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
pkill -f "main_v2.py"
cp data/backups/trading_bot_YYYYMMDD.db data/trading_bot.db
python src/main_v2.py --mode paper --dashboard
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

### Clean Old Data
```bash
# Keep insights/reflections for 30 days
sqlite3 data/trading_bot.db "
DELETE FROM insights WHERE created_at < datetime('now', '-30 days');
DELETE FROM reflections WHERE completed_at < datetime('now', '-30 days');
VACUUM;
"
```

---

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| OLLAMA_HOST | localhost | Ollama server address |
| OLLAMA_MODEL | qwen2.5:14b | LLM model to use |
| DB_PATH | data/trading_bot.db | Database location |

### Command Line Arguments

```bash
python src/main_v2.py \
  --mode paper \           # paper or live
  --dashboard \            # Enable dashboard
  --port 8080 \           # Dashboard port
  --db data/trading_bot.db # Database path
```

---

## Emergency Procedures

### Emergency Stop
```bash
pkill -f "main_v2.py"
```

### If Bot Won't Stop
```bash
pkill -9 -f "main_v2.py"
```

### If Database Corrupted
```bash
# Check integrity
sqlite3 data/trading_bot.db "PRAGMA integrity_check;"

# If failed, restore backup
pkill -f "main_v2.py"
cp data/backups/trading_bot_latest.db data/trading_bot.db
```

### If LLM Down
Bot continues with existing conditions but won't generate new ones.
- Fix LLM issue
- Bot auto-reconnects

### If WebSocket Down
Bot auto-reconnects. If persistent:
- Check internet connectivity
- Check Binance status
- Restart bot

---

## Performance Analysis

### Quick Stats
```bash
python scripts/analyze_performance.py --days 1
```

### Weekly Report
```bash
python scripts/analyze_performance.py --days 7
```

### Export Data
```bash
python scripts/export_trades.py --output trades.csv
```

---

## Related Documentation

- [PAPER-TRADING-GUIDE.md](./PAPER-TRADING-GUIDE.md) - Paper trading setup
- [DASHBOARD-GUIDE.md](./DASHBOARD-GUIDE.md) - Dashboard usage
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Problem solving
- [../architecture/SYSTEM-OVERVIEW.md](../architecture/SYSTEM-OVERVIEW.md) - Architecture
