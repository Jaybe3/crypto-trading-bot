# Data Model

## Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  account_state  │       │   open_trades   │       │  closed_trades  │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id              │       │ id              │       │ id              │
│ balance         │       │ coin_name       │       │ coin_name       │
│ available_bal   │       │ entry_price     │       │ entry_price     │
│ in_positions    │       │ size_usd        │       │ exit_price      │
│ total_pnl       │       │ entry_reason    │       │ size_usd        │
│ daily_pnl       │       │ opened_at       │       │ pnl_usd         │
│ trade_count     │       │ rule_ids_used   │       │ pnl_pct         │
│ updated_at      │       └─────────────────┘       │ entry_reason    │
└─────────────────┘                                 │ exit_reason     │
                                                    │ opened_at       │
                                                    │ closed_at       │
                                                    │ duration_secs   │
┌─────────────────┐       ┌─────────────────┐       │ rule_ids_used   │
│   learnings     │       │ trading_rules   │       └────────┬────────┘
├─────────────────┤       ├─────────────────┤                │
│ id              │──────>│ id              │                │
│ trade_id        │───────│ rule_text       │                │
│ what_happened   │       │ source_learn_id │<───────────────┘
│ why_outcome     │       │ status          │
│ pattern         │       │ success_count   │
│ lesson          │       │ failure_count   │
│ confidence      │       │ created_at      │
│ created_at      │       └─────────────────┘
└─────────────────┘

┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  market_data    │       │  activity_log   │       │ coin_cooldowns  │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ coin (PK)       │       │ id              │       │ coin_name (PK)  │
│ price_usd       │       │ action          │       │ expires_at      │
│ change_24h      │       │ description     │       └─────────────────┘
│ volume_24h      │       │ details         │
│ last_updated    │       │ created_at      │       ┌─────────────────┐
└─────────────────┘       └─────────────────┘       │monitoring_alerts│
                                                    ├─────────────────┤
                                                    │ id              │
                                                    │ alert_type      │
                                                    │ severity        │
                                                    │ title           │
                                                    │ description     │
                                                    │ evidence        │
                                                    │ recommendation  │
                                                    │ status          │
                                                    │ created_at      │
                                                    └─────────────────┘
```

## Table Definitions

### account_state
Single row tracking overall account status.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Always 1 |
| balance | REAL | Total account value |
| available_balance | REAL | Balance minus open positions |
| in_positions | REAL | Value tied up in open trades |
| total_pnl | REAL | Lifetime profit/loss |
| daily_pnl | REAL | Today's profit/loss |
| trade_count_today | INTEGER | Trades executed today |
| updated_at | TIMESTAMP | Last update time |

### open_trades
Currently active positions.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Trade ID |
| coin_name | TEXT | Coin identifier (e.g., "bitcoin") |
| entry_price | REAL | Price at entry |
| size_usd | REAL | Position size in USD |
| entry_reason | TEXT | LLM's reason for trade |
| opened_at | TIMESTAMP | When trade was opened |
| rule_ids_used | TEXT | JSON array of rule IDs applied |

### closed_trades
Historical completed trades.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Trade ID |
| coin_name | TEXT | Coin identifier |
| entry_price | REAL | Price at entry |
| exit_price | REAL | Price at exit |
| size_usd | REAL | Position size in USD |
| pnl_usd | REAL | Profit/loss in USD |
| pnl_pct | REAL | Profit/loss percentage |
| entry_reason | TEXT | Why trade was entered |
| exit_reason | TEXT | Why trade was closed |
| opened_at | TIMESTAMP | Entry time |
| closed_at | TIMESTAMP | Exit time |
| duration_seconds | INTEGER | How long position was held |
| rule_ids_used | TEXT | JSON array of rule IDs applied |

### learnings
Lessons extracted from closed trades.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Learning ID |
| trade_id | INTEGER FK | Source trade |
| what_happened | TEXT | Factual summary |
| why_outcome | TEXT | Analysis of cause |
| pattern | TEXT | Identified pattern |
| lesson | TEXT | Actionable takeaway |
| confidence | REAL | LLM's confidence (0-1) |
| created_at | TIMESTAMP | When created |

### trading_rules
Rules evolved from high-confidence learnings.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Rule ID |
| rule_text | TEXT | The rule statement |
| source_learning_id | INTEGER FK | Learning that spawned this |
| status | TEXT | 'testing', 'active', 'rejected', 'inactive' |
| success_count | INTEGER | Wins when rule was applied |
| failure_count | INTEGER | Losses when rule was applied |
| created_at | TIMESTAMP | When created |

### market_data
Latest price data for each coin.

| Column | Type | Description |
|--------|------|-------------|
| coin | TEXT PK | Coin identifier |
| price_usd | REAL | Current price |
| change_24h | REAL | 24-hour change percentage |
| volume_24h | REAL | 24-hour trading volume |
| last_updated | TIMESTAMP | When price was fetched |

### activity_log
Audit trail of all significant events.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Log ID |
| action | TEXT | Event type |
| description | TEXT | Human-readable description |
| details | TEXT | JSON with additional data |
| created_at | TIMESTAMP | When event occurred |

### coin_cooldowns
Tracks when coins can be traded again.

| Column | Type | Description |
|--------|------|-------------|
| coin_name | TEXT PK | Coin identifier |
| expires_at | TIMESTAMP | When cooldown ends |

### monitoring_alerts
Issues detected by autonomous monitor.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Alert ID |
| alert_type | TEXT | 'bug', 'inefficiency', 'pattern', etc. |
| severity | TEXT | 'critical', 'high', 'medium', 'low', 'info' |
| title | TEXT | Short description |
| description | TEXT | Full explanation |
| evidence | TEXT | Supporting data |
| recommendation | TEXT | Suggested fix |
| status | TEXT | 'open', 'acknowledged', 'fixed', 'wontfix' |
| created_at | TIMESTAMP | When detected |

## Indexes

```sql
CREATE INDEX idx_closed_trades_coin ON closed_trades(coin_name);
CREATE INDEX idx_closed_trades_time ON closed_trades(closed_at);
CREATE INDEX idx_learnings_trade ON learnings(trade_id);
CREATE INDEX idx_learnings_confidence ON learnings(confidence);
CREATE INDEX idx_rules_status ON trading_rules(status);
CREATE INDEX idx_activity_action ON activity_log(action);
CREATE INDEX idx_activity_time ON activity_log(created_at);
CREATE INDEX idx_alerts_severity ON monitoring_alerts(severity);
CREATE INDEX idx_alerts_status ON monitoring_alerts(status);
```

## Common Queries

### Get Recent Trades with P&L
```sql
SELECT coin_name, pnl_usd, pnl_pct, exit_reason, closed_at
FROM closed_trades
ORDER BY closed_at DESC
LIMIT 20;
```

### Get Active Rules Performance
```sql
SELECT id, rule_text,
       success_count, failure_count,
       ROUND(success_count * 100.0 / (success_count + failure_count), 1) as success_rate
FROM trading_rules
WHERE status = 'active'
AND (success_count + failure_count) > 0
ORDER BY success_rate DESC;
```

### Get High-Confidence Learnings
```sql
SELECT l.lesson, l.confidence, ct.coin_name, ct.pnl_usd
FROM learnings l
JOIN closed_trades ct ON l.trade_id = ct.id
WHERE l.confidence >= 0.7
ORDER BY l.created_at DESC
LIMIT 10;
```

### Get Win Rate by Tier
```sql
SELECT
    CASE
        WHEN coin_name IN ('bitcoin','ethereum','binancecoin','ripple','solana') THEN 'Tier 1'
        WHEN coin_name IN ('cardano','dogecoin','avalanche-2',...) THEN 'Tier 2'
        ELSE 'Tier 3'
    END as tier,
    COUNT(*) as trades,
    SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as win_rate
FROM closed_trades
GROUP BY tier;
```

---

*Last Updated: February 2026*
