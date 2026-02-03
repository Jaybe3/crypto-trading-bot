# TASK-150: Paper Trading Run (7 days)

**Status:** NOT STARTED
**Created:** February 3, 2026
**Priority:** Critical
**Depends On:** TASK-140 (Full Integration), TASK-141 (Profitability), TASK-142 (Effectiveness), TASK-143 (Dashboard)
**Phase:** Phase 2.6 - Validation

---

## Objective

Execute a 7-day paper trading run to validate that the autonomous learning system works correctly in practice. This task defines the operational procedures, success criteria, monitoring requirements, and daily checkpoint process.

---

## Background

The system has been built and all components are integrated:
- Speed infrastructure (0.0015ms execution)
- LLM-driven strategy generation
- Knowledge Brain accumulating coin scores, patterns, rules
- Reflection Engine generating insights
- Adaptation Engine applying changes
- Effectiveness Monitor tracking results
- Dashboard for observability

**What we need to prove:**
1. The system runs autonomously without crashes
2. The learning loop actually improves performance
3. Adaptations help rather than hurt
4. The bot makes reasonable trading decisions

---

## Paper Trading Configuration

### Starting Conditions

```python
# config/settings.py (paper trading)

# Account
INITIAL_BALANCE = 10000.0        # $10,000 paper money
PAPER_TRADING = True             # No real money at risk

# Risk Management
MAX_POSITION_SIZE = 500.0        # $500 max per trade
MAX_OPEN_POSITIONS = 3           # Max 3 concurrent positions
DAILY_LOSS_LIMIT = 500.0         # Stop trading if down $500/day

# Coins
TRADEABLE_COINS = [
    "BTC", "ETH", "SOL", "AVAX", "LINK",
    "DOGE", "XRP", "ADA", "DOT", "MATIC"
]

# Strategist
STRATEGIST_INTERVAL = 180        # Generate conditions every 3 minutes
STRATEGIST_ENABLED = True

# Reflection
REFLECTION_INTERVAL_HOURS = 1    # Reflect every hour
REFLECTION_MIN_TRADES = 5        # Or after 5 trades

# Effectiveness
MIN_TRADES_FOR_MEASUREMENT = 10  # Measure after 10 trades
MIN_HOURS_FOR_MEASUREMENT = 24   # Or after 24 hours
```

### System Startup

```bash
# Start the system with dashboard
python src/main_v2.py --dashboard --port 8080

# In another terminal, watch logs
tail -f logs/trading.log
```

---

## Success Criteria

The 7-day run is successful if **ALL** of the following are met:

### Tier 1: Stability (Must Pass)

| Criteria | Threshold | Measurement |
|----------|-----------|-------------|
| **Uptime** | ≥ 99% | Total uptime / 168 hours |
| **No crashes** | 0 unrecoverable crashes | Manual count |
| **Feed stability** | < 5 reconnects/day | Log count |
| **Health status** | Healthy or Degraded | Never "Failed" for > 5 min |

### Tier 2: Activity (Must Pass)

| Criteria | Threshold | Measurement |
|----------|-----------|-------------|
| **Trades executed** | ≥ 50 total | `total_trades` |
| **Conditions generated** | ≥ 100 total | Strategist stats |
| **Reflections completed** | ≥ 100 total | Reflection count |
| **Adaptations applied** | ≥ 5 total | Adaptation count |

### Tier 3: Learning (Target)

| Criteria | Target | Acceptable |
|----------|--------|------------|
| **Win rate trend** | Improving week over week | Stable (not declining) |
| **P&L trend** | Positive over 7 days | Not worse than -5% |
| **Harmful adaptations** | < 10% of total | < 20% of total |
| **Effective adaptations** | > 30% of total | > 20% of total |

### Tier 4: Performance (Aspirational)

| Criteria | Aspirational | Notes |
|----------|--------------|-------|
| **Final win rate** | > 50% | Indicates learning works |
| **Profit factor** | > 1.0 | Making money overall |
| **Sharpe ratio** | > 0.5 | Risk-adjusted returns |

---

## Monitoring Procedures

### Real-Time Monitoring (Dashboard)

Access: `http://localhost:8080`

| Page | What to Check | Frequency |
|------|---------------|-----------|
| **Real-Time** | System status, active conditions, prices | Continuous |
| **Knowledge** | Coin scores, patterns, blacklist | 2x daily |
| **Adaptations** | Recent changes, effectiveness | 2x daily |
| **Profitability** | Win rate, P&L, equity curve | Daily |
| **Overrides** | Only if intervention needed | As needed |

### Log Monitoring

```bash
# Watch for errors
grep -i "error\|exception\|failed" logs/trading.log | tail -20

# Watch trading activity
grep "TRADE ENTRY\|TRADE EXIT" logs/trading.log | tail -20

# Watch adaptations
grep "Adaptation applied" logs/trading.log | tail -10
```

### Health Check (Every 4 Hours)

```python
# Via API
curl http://localhost:8080/api/health

# Expected: all components "healthy"
{
  "overall": "healthy",
  "components": {
    "market_feed": {"status": "healthy"},
    "sniper": {"status": "healthy"},
    "strategist": {"status": "healthy"},
    "reflection_engine": {"status": "healthy"},
    "adaptation_engine": {"status": "healthy"}
  }
}
```

---

## Daily Checkpoint Process

### Daily Review Checklist

Perform this review at the same time each day (recommend: 9am local).

#### 1. System Health (5 min)

- [ ] System uptime since last check: _____ hours
- [ ] Any crashes or restarts? Yes / No
- [ ] Current health status: Healthy / Degraded / Failed
- [ ] Feed reconnects in last 24h: _____
- [ ] Error count in last 24h: _____

#### 2. Trading Activity (5 min)

- [ ] Trades executed (24h): _____
- [ ] Trades executed (cumulative): _____
- [ ] Conditions generated (24h): _____
- [ ] Open positions: _____

#### 3. Performance Metrics (5 min)

- [ ] Win rate (24h): _____%
- [ ] Win rate (cumulative): _____%
- [ ] P&L (24h): $______
- [ ] P&L (cumulative): $______
- [ ] Current balance: $______

#### 4. Learning Activity (5 min)

- [ ] Reflections completed (24h): _____
- [ ] Insights generated (24h): _____
- [ ] Adaptations applied (24h): _____
- [ ] Coins blacklisted (total): _____
- [ ] Patterns active (total): _____

#### 5. Effectiveness Check (5 min)

- [ ] Harmful adaptations flagged: _____
- [ ] Rollbacks executed: _____
- [ ] Effectiveness distribution:
  - Highly Effective: _____
  - Effective: _____
  - Neutral: _____
  - Ineffective: _____
  - Harmful: _____
  - Pending: _____

#### 6. Go/No-Go Decision

Based on the above, decide:

- [ ] **CONTINUE** - System healthy, no issues
- [ ] **INVESTIGATE** - Minor issues, continue with monitoring
- [ ] **PAUSE** - Significant issues, pause and fix
- [ ] **ABORT** - Critical failure, stop the run

### Decision Criteria

| Condition | Action |
|-----------|--------|
| System crashed and didn't recover | ABORT |
| Cumulative P&L < -$1,000 (-10%) | PAUSE |
| Win rate dropped > 20% from peak | INVESTIGATE |
| > 50% of adaptations harmful | PAUSE |
| No trades in 24 hours | INVESTIGATE |
| No reflections in 24 hours | INVESTIGATE |
| All systems healthy | CONTINUE |

---

## Intervention Guidelines

### When NOT to Intervene

- Win rate temporarily dips (< 3 days)
- A single bad trade
- Blacklist seems overly aggressive
- Pattern confidence seems low
- P&L is slightly negative

**Trust the system to learn.** Premature intervention defeats the purpose of validation.

### When to Intervene

| Situation | Action |
|-----------|--------|
| System crash | Restart, check logs |
| Feed disconnected > 1 hour | Check exchange status |
| LLM not responding | Check Ollama service |
| Database errors | Check disk space |
| Runaway losses (> $500/day) | Daily loss limit should trigger |

### Override Actions (Use Sparingly)

```bash
# Pause trading
curl -X POST http://localhost:8080/api/override/pause

# Resume trading
curl -X POST http://localhost:8080/api/override/resume

# Force reflection
curl -X POST http://localhost:8080/api/override/trigger-reflection

# Blacklist a coin manually (only if clearly broken)
curl -X POST http://localhost:8080/api/override/blacklist \
  -H "Content-Type: application/json" \
  -d '{"coin": "DOGE", "reason": "Manual: Suspected data issue"}'
```

---

## Daily Log Template

Create a daily log file: `logs/validation/day-N.md`

```markdown
# Day N Validation Log

**Date:** YYYY-MM-DD
**Reviewer:** [Name]
**Decision:** CONTINUE / INVESTIGATE / PAUSE / ABORT

## System Health
- Uptime: ___h ___m
- Crashes: ___
- Feed reconnects: ___
- Errors: ___

## Trading Activity
- Trades (24h): ___
- Trades (total): ___
- Conditions generated: ___

## Performance
- Win rate (24h): ___%
- Win rate (total): ___%
- P&L (24h): $___
- P&L (total): $___
- Balance: $___

## Learning
- Reflections: ___
- Insights: ___
- Adaptations: ___
- Blacklisted coins: ___

## Effectiveness
- Highly Effective: ___
- Effective: ___
- Neutral: ___
- Ineffective: ___
- Harmful: ___

## Notes
[Any observations, anomalies, or concerns]

## Actions Taken
[Any interventions or overrides]
```

---

## End-of-Run Analysis

After 7 days, compile final report (see TASK-152).

### Data to Collect

1. **Full trade history** - Export from journal
2. **All adaptations** - Export with effectiveness
3. **Equity curve** - Daily snapshots
4. **Knowledge state** - Final coin scores, patterns, rules
5. **System logs** - For debugging if needed

### Questions to Answer

1. Did the system run autonomously for 7 days?
2. Did win rate improve over time?
3. Did adaptations help or hurt?
4. Which coins performed best/worst?
5. Which patterns were most reliable?
6. What regime rules proved useful?

---

## Schedule

| Day | Date | Checkpoint Time | Reviewer |
|-----|------|-----------------|----------|
| 0 | Start | 09:00 | [Name] |
| 1 | Day 1 | 09:00 | [Name] |
| 2 | Day 2 | 09:00 | [Name] |
| 3 | Day 3 | 09:00 | [Name] |
| 4 | Day 4 | 09:00 | [Name] |
| 5 | Day 5 | 09:00 | [Name] |
| 6 | Day 6 | 09:00 | [Name] |
| 7 | End | 09:00 | [Name] |

---

## Acceptance Criteria

- [ ] System runs for 7 consecutive days
- [ ] All Tier 1 (Stability) criteria met
- [ ] All Tier 2 (Activity) criteria met
- [ ] At least 50% of Tier 3 (Learning) targets met
- [ ] Daily checkpoints completed and logged
- [ ] Final report compiled (TASK-152)

---

## Pre-Run Checklist

Before starting the 7-day run:

- [ ] Fresh database (or backup current)
- [ ] Knowledge Brain reset or preserved (decide which)
- [ ] Config settings verified (see above)
- [ ] Dashboard accessible
- [ ] Logs directory exists (`logs/validation/`)
- [ ] Ollama running with qwen2.5:14b
- [ ] Exchange API accessible (for price feed)
- [ ] Disk space > 10GB free
- [ ] System time synchronized

---

## Related

- [TASK-140](./TASK-140.md) - Full System Integration
- [TASK-141](./TASK-141.md) - Profitability Tracking
- [TASK-142](./TASK-142.md) - Adaptation Effectiveness
- [TASK-143](./TASK-143.md) - Dashboard v2
- [TASK-151](./TASK-151.md) - Learning Validation
- [TASK-152](./TASK-152.md) - Performance Analysis
- [AUTONOMOUS-TRADER-SPEC.md](../AUTONOMOUS-TRADER-SPEC.md) - Full system architecture
