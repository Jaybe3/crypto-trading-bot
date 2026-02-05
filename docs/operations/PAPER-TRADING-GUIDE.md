# Paper Trading Guide

**Last Updated:** February 3, 2026
**Phase:** 2 Complete

---

## Overview

Paper trading mode simulates real trading without risking actual capital. The bot executes the full trading loop - market data, strategy generation, condition execution, learning - but all trades are simulated.

---

## Starting Paper Trading

### Quick Start

```bash
# Activate environment
source venv/bin/activate

# Start with dashboard
python src/main.py --mode paper --dashboard --port 8080
```

### Command Line Options

```bash
python src/main.py \
  --mode paper \           # Paper trading mode (required for validation)
  --dashboard \            # Enable web dashboard
  --port 8080 \           # Dashboard port
  --db data/trading_bot.db  # Database path
```

### Using the Start Script

```bash
./scripts/start_paper_trading.sh
```

This script:
1. Checks Ollama is running
2. Initializes database if needed
3. Starts the trading system
4. Opens dashboard in browser

---

## What Happens in Paper Trading

### Trading Loop

Every 5 minutes:
1. **MarketFeed** provides current prices via WebSocket
2. **Strategist** generates conditions using LLM + knowledge context
3. **Sniper** monitors prices against conditions
4. When triggered, **simulated orders** are created (no real exchange)
5. Positions monitored for exit (stop-loss, take-profit)
6. **QuickUpdate** processes closed trades instantly
7. **ReflectionEngine** performs hourly deep analysis

### Simulated vs Real

| Aspect | Paper Mode | Real Mode |
|--------|-----------|-----------|
| Market Data | Real (Bybit WebSocket) | Real |
| Order Execution | Simulated | Real exchange |
| Fills | Instant at market price | May slip |
| Position Tracking | Database | Exchange + Database |
| Learning | Active | Active |

---

## Monitoring Paper Trading

### Dashboard

Open http://localhost:8080 to view:

- **Overview**: Live prices, open positions, recent trades
- **Knowledge**: Coin scores, patterns, regime rules
- **Adaptations**: History of learning changes
- **Profitability**: P&L tracking, metrics

### Command Line Checks

```bash
# Recent trades
sqlite3 data/trading_bot.db "
SELECT coin, direction, pnl_usd, exit_reason
FROM trade_journal
ORDER BY exit_time DESC LIMIT 10;
"

# Win rate
sqlite3 data/trading_bot.db "
SELECT
    COUNT(*) as trades,
    SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as win_rate
FROM trade_journal;
"

# Coin performance
sqlite3 data/trading_bot.db "
SELECT coin, total_trades, win_rate, total_pnl, status
FROM coin_scores
WHERE total_trades > 0
ORDER BY total_pnl DESC;
"
```

---

## Daily Checkpoints

Run the daily checkpoint script to generate a summary:

```bash
python scripts/daily_checkpoint.py
```

This outputs:
- Trade count (24h)
- Win rate
- Total P&L
- Best/worst performers
- Active adaptations
- System health status

### Manual Review Checklist

1. **Is the bot running?**
   ```bash
   pgrep -f "main.py"
   ```

2. **Are trades happening?**
   ```bash
   sqlite3 data/trading_bot.db "SELECT COUNT(*) FROM trade_journal WHERE exit_time > datetime('now', '-24 hours');"
   ```

3. **Is learning active?**
   ```bash
   sqlite3 data/trading_bot.db "SELECT COUNT(*) FROM adaptations WHERE applied_at > datetime('now', '-24 hours');"
   ```

4. **Check for errors:**
   ```bash
   grep -i error logs/bot.log | tail -20
   ```

---

## 7-Day Validation Protocol

### Objectives

After 7 days of paper trading, validate:
- Profitability: Positive overall P&L
- Learning: Measurable improvement over time
- Reliability: Minimal downtime or errors
- Risk Management: Drawdown within limits

### Daily Tasks

| Day | Focus | Checks |
|-----|-------|--------|
| 1 | Baseline | System running, trades executing |
| 2 | Data Quality | Orders filling, prices accurate |
| 3 | Learning | Quick updates processing |
| 4 | Reflection | Hourly insights generating |
| 5 | Adaptation | Changes being applied |
| 6 | Metrics | Win rate, profit factor trends |
| 7 | Analysis | Full performance report |

### End-of-Week Analysis

```bash
python scripts/analyze_performance.py --days 7
```

This generates:
- Overall metrics (win rate, profit factor, Sharpe ratio)
- Breakdown by coin, hour, pattern
- Learning effectiveness analysis
- Comparison: first half vs second half

### Success Criteria

| Metric | Minimum | Target |
|--------|---------|--------|
| Win Rate | 50% | 55%+ |
| Profit Factor | 1.0 | 1.3+ |
| Max Drawdown | <20% | <10% |
| Trades | 50+ | 100+ |
| Adaptations Applied | 5+ | 10+ |

---

## Configuration

### Position Sizing (Paper Mode)

```python
# Default paper trading balance
PAPER_BALANCE = 10000  # $10,000 simulated

# Position size calculation
base_size = 100  # $100 per trade
modifier = coin_scorer.get_position_modifier(coin)  # 0.5 - 1.5
final_size = base_size * modifier
```

### Risk Parameters

| Parameter | Value |
|-----------|-------|
| Max Position Size | $200 |
| Max Open Positions | 5 |
| Default Stop Loss | 2% |
| Default Take Profit | 3% |

---

## Common Issues

### No Trades Happening

1. Check WebSocket connection:
   ```bash
   grep "WebSocket" logs/bot.log | tail -5
   ```

2. Check LLM is responding:
   ```bash
   curl -s http://localhost:11434/api/tags
   ```

3. Check for blacklisted coins:
   ```bash
   sqlite3 data/trading_bot.db "SELECT coin FROM coin_scores WHERE is_blacklisted = 1;"
   ```

### Learning Not Working

1. Check trades are being recorded:
   ```bash
   sqlite3 data/trading_bot.db "SELECT COUNT(*) FROM trade_journal;"
   ```

2. Check quick updates:
   ```bash
   sqlite3 data/trading_bot.db "SELECT * FROM adaptations ORDER BY applied_at DESC LIMIT 5;"
   ```

3. Check reflection is running:
   ```bash
   sqlite3 data/trading_bot.db "SELECT * FROM reflections ORDER BY completed_at DESC LIMIT 3;"
   ```

---

## Stopping Paper Trading

### Graceful Stop

```bash
# Ctrl+C in terminal, or:
pkill -f "main.py"
```

The system saves all state before exit:
- Open positions recorded
- Learning state persisted
- Can resume from same point

### Exporting Data

Before stopping a significant run:

```bash
# Export trades to CSV
python scripts/export_trades.py --output data/exports/trades_$(date +%Y%m%d).csv

# Generate report
python scripts/generate_report.py --output data/reports/report_$(date +%Y%m%d).md

# Backup database
cp data/trading_bot.db data/backups/trading_bot_$(date +%Y%m%d).db
```

---

## Related Documentation

- [DASHBOARD-GUIDE.md](./DASHBOARD-GUIDE.md) - Dashboard features
- [RUNBOOK.md](./RUNBOOK.md) - Day-to-day operations
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Problem solving
