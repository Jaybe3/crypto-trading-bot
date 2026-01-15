# Product Requirements Document: Self-Learning Crypto Trading Bot

**Version:** 1.0  
**Last Updated:** January 13, 2026  
**Status:** Phase 1 - Paper Trading

---

## 1. EXECUTIVE SUMMARY

### Vision
Build an autonomous, self-learning AI trading bot that trades cryptocurrency 24/7, learns from every trade, creates its own rules, and optimizes itself to consistently generate $1 profit per minute.

### Core Philosophy
This is NOT a fixed-strategy bot with pre-programmed indicators. This is a **learning system** that:
- Analyzes its own performance
- Identifies successful patterns
- Creates and tests new trading rules
- Evolves over time to become increasingly profitable

### Success Criteria (Phase 1)
- Bot runs autonomously 24/7 without human intervention
- Consistently generates $1/min profit ($1,440/day) for 7+ consecutive days
- Learns from every trade (wins AND losses)
- Creates and validates its own trading rules
- Respects all risk management constraints 100% of time
- ALL data and decisions are transparent and verifiable

---

## 2. SCOPE

### PHASE 1: PAPER TRADING (Current Scope)
This PRD covers paper trading ONLY. No real money, no wallet integration.

**Phase 1 Must Prove:**
- The learning loop works
- The bot can consistently profit
- Risk rules are respected
- The LLM makes good decisions
- The system is transparent and verifiable

### PHASE 2: REAL TRADING (Out of Scope Until Phase 1 Complete)
⚠️ **DO NOT BUILD PHASE 2 FEATURES YET** ⚠️

Phase 2 is OUT OF SCOPE until Phase 1 proves:
- Bot can consistently profit $1/min for 7+ days
- Learning mechanism demonstrably improves performance over time
- All risk rules are respected 100% of time
- Dashboard accurately shows all data
- User can verify everything is working

**Phase 2 Will Include (but DO NOT BUILD now):**
- Real wallet integration
- Actual trade execution on exchanges
- Admin hub for configuration
- Multi-wallet support
- Manual rule override interface

---

## 3. CORE REQUIREMENTS (NON-NEGOTIABLE)

### 3.1 The Learning System (HIGHEST PRIORITY)

**This is the entire point of the project.**

The bot MUST be a self-optimizing system that:

1. **Learns from Every Trade**
   - Records the LLM's reasoning for every buy decision
   - Records the outcome (profit/loss) and WHY it happened
   - Analyzes what made successful trades successful
   - Analyzes what made losing trades lose
   - Stores these learnings in retrievable format

2. **Creates Its Own Rules**
   - Identifies patterns from successful trades
   - Formulates new trading rules based on patterns
   - Tests new rules (via simulation or small live tests)
   - Adopts successful rules permanently
   - Discards or modifies unsuccessful rules

3. **Optimizes Over Time**
   - Performance should improve week over week
   - Win rate should increase
   - Loss severity should decrease
   - Time to $1 profit should decrease
   - The system should become more confident and precise

4. **Operates Autonomously**
   - No human intervention required after launch
   - Makes all decisions independently
   - Adapts to changing market conditions
   - Self-corrects when strategies stop working

**CRITICAL:** This is not optional. If the learning loop doesn't work, the project has failed.

### 3.2 Risk Management

These constraints are MANDATORY and enforced on EVERY trade:

- **Maximum Risk Per Trade:** 2% of account balance ($20 on $1,000)
- **Maximum Total Exposure:** 10% of account balance ($100 on $1,000)
- **Automatic Stop Loss:** -10% on every trade (exit immediately)
- **Automatic Take Profit:** +$1 on every trade (exit immediately)
- **Never trade if balance < $900** (90% of starting capital)

**Risk checks happen BEFORE every trade. No exceptions.**

### 3.3 Performance Target

- **Primary Goal:** $1 profit per minute
- **Daily Target:** $1,440 profit per day
- **Validation Period:** 7+ consecutive profitable days before Phase 2

**If target is not being met:**
- Bot continues trading (doesn't stop)
- LLM reviews performance and adjusts strategy
- Creates new learnings to improve performance
- Tests new approaches

### 3.4 Transparency & Verifiability

**Everything must be verifiable by the user:**

- ✅ Market data is REAL (not simulated)
- ✅ API calls are visible (can see actual requests/responses)
- ✅ Learnings are stored and retrievable
- ✅ LLM's reasoning is recorded for every decision
- ✅ All trades are logged with timestamps
- ✅ Database can be queried directly
- ✅ Dashboard shows live, accurate data

**NO BLACK BOXES.** User must be able to verify every component works.

### 3.5 Coin Diversity

**The bot must trade across multiple coins, not fixate on one.**

- **Cooldown Period:** 30 minutes after trading a coin before trading it again
- **Persistent Cooldowns:** Cooldowns stored in database, survive bot restarts
- **Hard Constraint:** LLM is FORBIDDEN from trading coins in cooldown
- **Portfolio Diversity:** Spread risk across different coins
- **Learning Diversity:** Generate learnings from different market conditions

**Cooldown Implementation:**
- Cooldowns stored in `coin_cooldowns` database table
- Loaded on bot startup (persist across restarts)
- Risk manager rejects trades on coins in cooldown
- LLM prompt explicitly forbids trading cooldown coins

**Why this matters:**
- Reduces concentration risk
- Generates more diverse learning data
- Prevents over-optimization on single coin patterns
- Better represents real market conditions
- Survives bot restarts (persistent state)

---

## 4. TECHNICAL SPECIFICATIONS

### 4.1 Technology Stack

**Local LLM:**
- Model: `qwen2.5-coder:7b` (already installed via OpenWebUI)
- Interface: OpenWebUI API at http://localhost:3000
- Why: Fast enough for real-time decisions, runs locally, no API costs

**Market Data:**
- CoinGecko API (free tier) - for BTC, ETH, XRP, major coins
- DexScreener API (free) - for DEX tokens
- Update frequency: Every 10-30 seconds

**Data Storage:**
- SQLite database (simple, verifiable, no setup required)
- Location: `/data/trading_bot.db`

**Dashboard:**
- Simple web server (Flask or FastAPI)
- Accessible at http://localhost:8080
- Auto-refreshes every 5 seconds
- Shows all bot activity in real-time

### 4.2 Paper Trading Simulation

**Starting Conditions:**
- Account Balance: $1,000 (paper money)
- Available for Trading: $1,000 initially

**Trade Execution:**
- Instant fill at current market price (no slippage in paper trading)
- No trading fees (add later if needed)
- Positions are tracked with entry price and size
- Exit when stop loss (-10%) OR take profit (+$1) is hit

---

## 5. DATA MODELS

### 5.1 Open Trades Table
```sql
CREATE TABLE open_trades (
    id INTEGER PRIMARY KEY,
    coin_name TEXT NOT NULL,
    entry_price REAL NOT NULL,
    size_usd REAL NOT NULL,
    current_price REAL,
    unrealized_pnl REAL,
    unrealized_pnl_pct REAL,
    stop_loss_price REAL,
    take_profit_price REAL,
    entry_reason TEXT NOT NULL,
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5.2 Closed Trades Table
```sql
CREATE TABLE closed_trades (
    id INTEGER PRIMARY KEY,
    coin_name TEXT NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL NOT NULL,
    size_usd REAL NOT NULL,
    pnl_usd REAL NOT NULL,
    pnl_pct REAL NOT NULL,
    entry_reason TEXT NOT NULL,
    exit_reason TEXT NOT NULL,
    opened_at TIMESTAMP,
    closed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_seconds INTEGER
);
```

### 5.3 Learnings Table
```sql
CREATE TABLE learnings (
    id INTEGER PRIMARY KEY,
    learning_text TEXT NOT NULL,
    pattern_observed TEXT,
    success_rate REAL,
    confidence_level TEXT,
    trades_analyzed INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated BOOLEAN DEFAULT 0
);
```

### 5.4 Trading Rules Table
```sql
CREATE TABLE trading_rules (
    id INTEGER PRIMARY KEY,
    rule_text TEXT NOT NULL,
    rule_type TEXT NOT NULL,
    created_by TEXT DEFAULT 'LLM',
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'testing',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP
);
```

---

## 6. THE LEARNING LOOP

### Main Trading Cycle (Every 10-30 seconds):
1. Fetch latest market data
2. Update open position P&L
3. Check if stop loss or take profit hit
4. Query LLM with:
   - Current market data
   - Account state
   - Past learnings
   - Active trading rules
5. LLM responds with: BUY/SELL/HOLD + reasoning + **rules_applied**
6. Execute decision (if valid per risk rules)
7. **Tag trade with rule IDs** for outcome tracking
8. Log everything

### Rule Tracking (CRITICAL)

**LLM must return which rules it applies to each decision.**

Every LLM trading decision MUST include:
```json
{
    "action": "BUY/SELL/HOLD",
    "coin": "...",
    "size_usd": ...,
    "reason": "...",
    "confidence": 0.0-1.0,
    "rules_applied": [1, 2, ...]  // REQUIRED - list of rule IDs
}
```

**Why this matters:**
- Rule success rates must match actual trade outcomes
- Without `rules_applied`, we can't track which rules work
- This enables the self-learning loop to evaluate and improve rules

### Learning Analysis (After Each Closed Trade):
1. Query LLM: "Analyze this trade"
2. LLM generates:
   - What happened
   - Why it worked/failed
   - Pattern observed
   - Lesson learned
3. Store learning in database
4. If pattern is strong, create new rule

### Daily Summary:
- Analyze all day's trades
- Identify what worked/didn't
- Update rule effectiveness
- Store as daily learning

---

## 7. DASHBOARD REQUIREMENTS

**Must Show:**
- Bot status (running/stopped)
- Last market data API call (with actual response)
- LLM's current thinking (full prompt and response)
- Open positions with live P&L
- Recent closed trades
- All learnings (searchable)
- All rules (with success rates)
- Account balance and daily P&L
- Performance metrics

**User must be able to:**
- Verify market data is real
- Read LLM's reasoning
- Query database directly
- See everything updating live

---

## 8. VALIDATION REQUIREMENTS

**Every component must be independently verifiable:**

1. Market data: User runs curl command to verify
2. Database: User queries SQLite directly
3. LLM: User can test LLM API directly
4. Dashboard: Shows real, live data
5. Learning loop: Learnings appear after trades

**No moving forward until user can verify current component works.**

---

## 9. SUCCESS METRICS

**Week 1:**
- Bot runs 24h without crashing
- 20+ trades executed
- 5+ learnings created
- 2+ rules formulated

**Week 2-3:**
- Win rate > 55%
- Avg hourly profit > $30
- 10+ active rules
- Performance improving

**Week 4+:**
- Consistent $1/min for 7+ days
- Win rate > 60%
- Ready for Phase 2
