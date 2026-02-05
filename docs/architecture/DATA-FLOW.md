# Data Flow Architecture

## Overview

The trading bot has three data stores that must stay synchronized:

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA STORES                               │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ Sniper Memory   │ sniper_state.json│ Database                   │
│ (runtime)       │ (persistence)    │ (source of truth)          │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ balance         │ balance          │ account_state.balance      │
│ positions       │ positions        │ open_trades (unused)       │
│ total_pnl       │ total_pnl        │ trade_journal SUM(pnl)     │
│ trades_executed │ trades_executed  │ trade_journal COUNT        │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

## Current State (As of 2026-02-05)

**BROKEN:** Three stores are disconnected. See RT-001 through RT-005.

| Source | Balance | P&L | Closed Trades |
|--------|---------|-----|---------------|
| account_state (DB) | $1,000 | $0 | N/A |
| trade_journal (DB) | N/A | $757 | 168 |
| sniper_state (JSON) | $9,930 | -$10 | 0 |
| /api/status | $9,935 | -$15 | N/A |
| /api/profitability | $10,757 | $757 | 168 |

## Target State

**Database is authoritative.** All components read from and write to database.

## Component Responsibilities

### Sniper (`src/sniper.py`)
- Executes trades based on conditions
- MUST update: trade_journal, account_state
- READS: active_conditions, account_state

### Strategist (`src/strategist.py`)
- Generates trade conditions using LLM
- WRITES: active_conditions
- READS: coin_scores, trading_patterns, regime_rules, market context

### Journal (`src/journal.py`)
- Records all trade entries and exits
- WRITES: trade_journal
- READS: trade_journal (for analysis)

### Learning System
- QuickUpdate (`src/quick_update.py`): Immediate post-trade updates
- Reflection (`src/reflection.py`): Periodic deep analysis
- WRITES: coin_scores, insights, adaptations, reflections
- READS: trade_journal, coin_scores

### Dashboard (`src/dashboard_v2.py`)
- READS ONLY: All tables for display
- WRITES: Nothing (except manual overrides)

## API Endpoint Data Sources

| Endpoint | Reads From | Should Read From |
|----------|------------|------------------|
| /api/status | Sniper memory | Database |
| /api/profitability | trade_journal | trade_journal (correct) |
| /api/knowledge/* | KnowledgeBrain | Database via KB (correct) |
| /api/positions | Sniper memory | Database |

## Trade Lifecycle

```
1. SIGNAL GENERATION
   Strategist → LLM → TradeCondition

2. CONDITION STORAGE
   TradeCondition → active_conditions table
   TradeCondition → Sniper.conditions (memory)

3. TRADE EXECUTION
   Sniper monitors prices → Condition triggered
   → Position opened → trade_journal (entry)
   → account_state updated (CURRENTLY BROKEN)

4. POSITION MONITORING
   Sniper monitors price vs SL/TP
   → Unrealized P&L calculated

5. TRADE EXIT
   SL/TP hit or manual close
   → trade_journal (exit)
   → account_state updated (CURRENTLY BROKEN)
   → QuickUpdate.process_trade_close()

6. LEARNING
   QuickUpdate → coin_scores update
   QuickUpdate → reflection_engine.on_trade_close()
   ReflectionEngine (periodic) → insights → adaptations
```

## Database Tables by Category

### Core Trading
- `account_state` - Current account balance and P&L
- `trade_journal` - All trade entries and exits
- `active_conditions` - Pending trade conditions

### Learning
- `coin_scores` - Per-coin performance tracking
- `reflections` - Periodic analysis results
- `insights` - Extracted insights (CURRENTLY EMPTY)
- `adaptations` - Applied adaptations (CURRENTLY EMPTY)
- `trading_patterns` - Learned patterns

### Unused (Legacy)
- `open_trades` - 0 rows, never populated
- `closed_trades` - 0 rows, never populated
- `learnings` - 0 rows
- `regime_rules` - 0 rows
- `trading_rules` - 0 rows

## Known Issues

See `audit_results/COMPLETE-BUG-LIST.md` for full details.

Key data flow issues:
- RT-001: account_state never updated
- RT-003: Data disagreement across sources
- RT-006: Learning loop not producing adaptations
- RT-010: 93% of trades not tracked in coin_scores
