# Monitoring Guide

What to watch, how to interpret it, and when to act.

---

## Key Metrics

### Health Indicators

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| Bot process | Running | - | Not running |
| Dashboard | Running | - | Not running |
| Cycle time | <10s | 10-30s | >30s |
| LLM response | <5s | 5-30s | >30s or failing |
| Win rate (24h) | >50% | 40-50% | <40% |
| Daily P&L | Positive | Small loss | Large loss |

### Check Commands

**Bot running:**
```bash
pgrep -f "python.*main.py" && echo "OK" || echo "NOT RUNNING"
```

**Dashboard running:**
```bash
curl -s http://localhost:8080/api/status > /dev/null && echo "OK" || echo "NOT RUNNING"
```

**LLM responding:**
```bash
curl -s --max-time 10 http://172.27.144.1:11434/api/tags > /dev/null && echo "OK" || echo "FAILED"
```

---

## Dashboard Monitoring

### Key Sections to Watch

1. **Account Overview**
   - Balance trending up = good
   - Large sudden drops = investigate

2. **Open Positions**
   - Should be 0-3 typically
   - Many positions = check exposure limits

3. **Recent Trades**
   - Mix of wins/losses normal
   - All losses = investigate
   - Same coin repeatedly = cooldown may be broken

4. **Learning System**
   - New learnings appearing = good
   - Rules being created = learning system working

---

## Prometheus Metrics

Endpoint: `http://localhost:8080/metrics`

### Key Metrics

```
# Trade metrics
trading_bot_trades_total{outcome="win"}
trading_bot_trades_total{outcome="loss"}
trading_bot_pnl_total

# System metrics
trading_bot_cycle_duration_seconds
trading_bot_llm_response_seconds
trading_bot_open_positions

# Learning metrics
trading_bot_learnings_total
trading_bot_rules_active
```

### Example Prometheus Query
```
rate(trading_bot_trades_total[1h])  # Trades per hour
```

---

## Log Analysis

### Log Location
```
logs/bot.log
```

### Key Patterns to Watch

**Normal operation:**
```
INFO - Cycle #1234 complete | HOLD (65%) | Balance: $1050.00 | 2.3s
```

**Trade executed:**
```
INFO - Trade opened: BITCOIN $20.00 (momentum breakout)
INFO - Trade closed: BITCOIN +$1.00 (take_profit)
```

**Warnings to investigate:**
```
WARNING - LLM returned no decision, defaulting to HOLD
WARNING - Trade rejected: exposure limit exceeded
WARNING - API rate limit approaching
```

**Errors requiring action:**
```
ERROR - Failed to fetch market data: ConnectionError
ERROR - LLM error: timeout
ERROR - Database error: database is locked
```

### Log Analysis Commands

**Recent errors:**
```bash
grep -i error logs/bot.log | tail -20
```

**Trade activity:**
```bash
grep -E "(Trade opened|Trade closed)" logs/bot.log | tail -20
```

**LLM issues:**
```bash
grep -i llm logs/bot.log | grep -i -E "(error|timeout|failed)" | tail -10
```

---

## Alerts

### Autonomous Monitor

The bot includes a self-monitoring system. Run manually:
```bash
python scripts/autonomous_monitor.py
```

Or schedule via cron:
```bash
0 * * * * cd /path/to/bot && python scripts/autonomous_monitor.py
```

### Check Alerts
```bash
sqlite3 data/trading_bot.db "
SELECT severity, title, created_at
FROM monitoring_alerts
WHERE status = 'open'
ORDER BY created_at DESC;
"
```

### Acknowledge Alert
```bash
sqlite3 data/trading_bot.db "
UPDATE monitoring_alerts
SET status = 'acknowledged'
WHERE id = X;
"
```

---

## Performance Analysis

### Daily Summary
```bash
python src/daily_summary.py
```

### Win Rate by Period
```bash
sqlite3 data/trading_bot.db "
SELECT
    date(closed_at) as day,
    COUNT(*) as trades,
    SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as win_rate,
    ROUND(SUM(pnl_usd), 2) as pnl
FROM closed_trades
WHERE closed_at > datetime('now', '-7 days')
GROUP BY date(closed_at)
ORDER BY day DESC;
"
```

### Performance by Tier
```bash
bash scripts/performance.sh
```

---

## Capacity Planning

### Current Limits

| Resource | Limit | Current Usage |
|----------|-------|---------------|
| Coins monitored | 45 | 45 |
| Database size | ~10GB practical | Check with `du -sh data/` |
| API rate limit | 50 calls/min | ~2 calls/min |
| Disk for logs | Depends on rotation | Check with `du -sh logs/` |

### Growth Projections

At current rate:
- ~2,880 cycles/day
- ~100-200 trades/day typical
- ~10-20 learnings/day
- Database grows ~1-5 MB/day

---

*Last Updated: February 2026*
