# Learning System Architecture

The learning system is the core intellectual property of this trading bot. It transforms raw trade outcomes into actionable knowledge.

---

## Overview

```
Trade Outcome ──> LLM Analysis ──> Structured Learning ──> Rule Candidate ──> Active Rule
```

Unlike traditional trading systems with static rules, this system:
1. Learns from every trade (wins AND losses)
2. Extracts patterns autonomously
3. Creates and validates its own rules
4. Continuously improves decision quality

---

## Learning Extraction

### Input: Closed Trade

When a trade closes (stop-loss, take-profit, or manual), the system captures:

```python
{
    "trade_id": 1234,
    "coin_name": "bitcoin",
    "entry_price": 45000.00,
    "exit_price": 45500.00,
    "size_usd": 20.00,
    "pnl_usd": 1.00,
    "pnl_pct": 1.11,
    "entry_reason": "Momentum breakout with volume confirmation",
    "exit_reason": "take_profit",
    "duration_seconds": 180,
    "opened_at": "2026-01-15 10:30:00",
    "closed_at": "2026-01-15 10:33:00"
}
```

### Process: LLM Analysis

The trade is sent to the LLM with a structured prompt:

```
Analyze this cryptocurrency trade:

TRADE DETAILS:
- Coin: bitcoin (Tier 1 - Blue Chip)
- Entry: $45,000.00 at 2026-01-15 10:30:00
- Exit: $45,500.00 at 2026-01-15 10:33:00
- Size: $20.00
- P&L: +$1.00 (+1.11%)
- Duration: 3 minutes
- Entry Reason: Momentum breakout with volume confirmation
- Exit Reason: take_profit

MARKET CONTEXT:
- 24h Change at Entry: +2.3%
- Current Price: $45,520.00

Please analyze and provide:
1. what_happened: Brief factual summary
2. why_outcome: Why did this trade succeed/fail?
3. pattern: What recognizable pattern occurred?
4. lesson: What should be learned for future trades?
5. confidence: Your confidence in this lesson (0.0 to 1.0)

Respond in JSON format.
```

### Output: Structured Learning

```python
{
    "trade_id": 1234,
    "what_happened": "BTC momentum trade captured quick profit during uptrend",
    "why_outcome": "Entry caught continuation of existing trend, tight take-profit executed before reversal",
    "pattern": "Trend continuation on blue chip during low volatility",
    "lesson": "Blue chip momentum trades in established uptrends have high probability of quick small gains",
    "confidence": 0.75,
    "created_at": "2026-01-15 10:33:05"
}
```

---

## Rule Creation

### Promotion Criteria

A learning becomes a rule candidate when:
- Confidence ≥ 70%
- Pattern is specific enough to be actionable
- Not a duplicate of existing rule

### Rule Structure

```python
{
    "id": 42,
    "rule_text": "In established uptrends, blue chip momentum trades should use tight take-profits ($1) to capture quick gains before reversal",
    "source_learning_id": 1234,
    "status": "testing",  # testing → active → inactive
    "success_count": 0,
    "failure_count": 0,
    "created_at": "2026-01-15 10:33:10"
}
```

### Testing Phase

Rules enter testing status and are tracked for 10 trades:
- Each trade where rule was applied is recorded
- Win = success_count++
- Loss = failure_count++
- After 10 trades, success rate determines promotion

### Promotion/Rejection

```python
if success_count >= 6:  # 60% success rate
    status = "active"
else:
    status = "rejected"
```

---

## Rule Application

### Context Building

When making a trade decision, active rules are included in the LLM prompt:

```
ACTIVE TRADING RULES:
[Rule #42] In established uptrends, blue chip momentum trades should use tight take-profits ($1) to capture quick gains before reversal
[Rule #38] Avoid Tier 3 coins when BTC is declining more than 2% in 24h
[Rule #45] Volume spikes on Tier 2 coins often precede 2-3% moves

Consider these rules when making your decision. If you apply a rule, include its ID in your response.
```

### Rule Tracking

When a trade is executed, the LLM indicates which rules influenced the decision:

```python
{
    "action": "BUY",
    "coin": "ethereum",
    "confidence": 0.72,
    "reason": "Momentum breakout with volume confirmation",
    "rules_applied": [42, 45]
}
```

The trade is tagged with these rule IDs, enabling rule performance tracking.

---

## Database Schema

### learnings table
```sql
CREATE TABLE learnings (
    id INTEGER PRIMARY KEY,
    trade_id INTEGER NOT NULL,
    what_happened TEXT NOT NULL,
    why_outcome TEXT NOT NULL,
    pattern TEXT NOT NULL,
    lesson TEXT NOT NULL,
    confidence REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trade_id) REFERENCES closed_trades(id)
);
```

### trading_rules table
```sql
CREATE TABLE trading_rules (
    id INTEGER PRIMARY KEY,
    rule_text TEXT NOT NULL,
    source_learning_id INTEGER,
    status TEXT DEFAULT 'testing',
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_learning_id) REFERENCES learnings(id)
);
```

---

## Quality Safeguards

### Preventing Bad Learning

| Risk | Mitigation |
|------|------------|
| Learning from noise | Confidence threshold filters low-quality learnings |
| Overfitting | Rules require validation across multiple trades |
| Conflicting rules | LLM considers all rules together, weighs relevance |
| Stale rules | Inactive rules excluded from context |

### Monitoring Learning Quality

Key metrics to track:
- Learning creation rate (should correlate with trade volume)
- Average confidence of learnings (trending up = good)
- Rule promotion rate (too high = threshold too low)
- Active rule performance (should beat baseline)

---

## Future Enhancements

Potential improvements for Phase 2+:
- Rule expiration (demote rules unused for N days)
- Rule versioning (evolve rules over time)
- Rule clustering (identify related rules)
- Meta-learning (learn what makes good rules)

---

*Last Updated: February 2026*
