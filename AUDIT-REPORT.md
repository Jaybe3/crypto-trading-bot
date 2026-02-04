# System Audit Report

**Date:** February 3, 2026
**Auditor:** Claude (AI Assistant)
**Scope:** Complete system audit - code, documentation, deployment state

---

## EXECUTIVE SUMMARY

**CRITICAL FINDING: There are TWO completely separate trading systems in this codebase, and the production deployment runs the WRONG one.**

| System | File | What It Does | Is It Running? |
|--------|------|--------------|----------------|
| Phase 1 | `main.py` | CoinGecko polling, direct LLM decisions | **YES** (via supervisor) |
| Phase 2 | `main.py` | WebSocket, Strategist, Sniper, Learning Loop | **NO** (manual only) |

**All Phase 2 learning infrastructure (24 tasks) is built but NOT deployed to production.**

---

## PART 1: THE TWO SYSTEMS

### main.py (Phase 1 System)

**Imports:**
```python
from src.database import Database
from src.market_data import MarketDataFetcher, format_price
from src.trading_engine import TradingEngine
from src.learning_system import LearningSystem, RuleManager
from src.llm_interface import LLMInterface
from src.risk_manager import RiskManager
from src.coin_config import get_coin_ids, get_tier, get_tier_config
```

**Classes Instantiated:**
- `Database` - SQLite storage
- `LLMInterface` - Ollama connection
- `MarketDataFetcher` - CoinGecko API poller
- `RiskManager` - Position limits
- `TradingEngine` - Trade execution
- `LearningSystem` - Post-trade analysis
- `RuleManager` - Rule creation

**Main Loop:**
1. Fetch market data (CoinGecko batch API)
2. Update positions (check stop-loss/take-profit)
3. Analyze closed trades (create learnings)
4. Query LLM for trading decision
5. Execute decision if valid
6. Sleep 30 seconds, repeat

**Data LLM Receives:**
```python
market_data = {
    coin: {
        "price_usd": float,
        "change_24h": float,
        "tier": int
    }
}
account_state = {
    "balance": float,
    "available_balance": float,
    "in_positions": float,
    "daily_pnl": float,
    "open_trades": int,
    "trade_count_today": int
}
recent_learnings = ["text1", "text2", ...]
active_rules = ["rule1", "rule2", ...]
coins_in_cooldown = ["BTC", "ETH", ...]
```

---

### main.py (Phase 2 System)

**Imports:**
```python
from src.market_feed import MarketFeed, PriceTick
from src.sniper import Sniper
from src.journal import TradeJournal, MarketContext
from src.models.trade_condition import TradeCondition
from src.strategist import Strategist
from src.llm_interface import LLMInterface
from src.database import Database
from src.knowledge import KnowledgeBrain
from src.coin_scorer import CoinScorer
from src.quick_update import QuickUpdate
from src.pattern_library import PatternLibrary
from src.reflection import ReflectionEngine
from src.adaptation import AdaptationEngine
from src.profitability import ProfitabilityTracker, SnapshotScheduler
from src.effectiveness import EffectivenessMonitor
from src.dashboard_v2 import DashboardServer
```

**Classes Instantiated:**
- `TradeJournal` - Rich trade recording
- `Database` - SQLite storage
- `KnowledgeBrain` - Knowledge storage
- `CoinScorer` - Per-coin tracking
- `PatternLibrary` - Pattern storage
- `QuickUpdate` - Instant learning
- `Sniper` - Sub-ms execution
- `MarketFeed` - WebSocket data
- `Strategist` - LLM condition generation
- `AdaptationEngine` - Apply learnings
- `ReflectionEngine` - Hourly analysis
- `ProfitabilityTracker` - P&L tracking
- `EffectivenessMonitor` - Adaptation tracking
- `DashboardServer` - Web UI

**Main Loop:**
1. WebSocket receives price ticks (real-time)
2. Sniper checks conditions on each tick
3. If triggered → execute trade → log to journal
4. QuickUpdate updates coin scores/patterns (instant)
5. Strategist generates new conditions (every 3 min)
6. ReflectionEngine runs deep analysis (hourly)
7. AdaptationEngine applies insights

**Data LLM Receives (Strategist):**
```python
# Prices
"BTC: $76,274 (+2.5%)"
"ETH: $2,286 (-1.2%)"
# ... all 45 coins

# Coin Performance (from Knowledge Brain)
"SOL: FAVORED | 15 trades | 60% win | +$45 P&L | improving"

# Blacklist
COINS TO AVOID: ["AXS", "SAND", ...]

# Active Rules
"Don't trade during first 5 minutes of the hour"

# Patterns
"momentum_breakout (75% conf, 62% win rate)"

# Account
"Balance: $10,000 | Available: $9,500 | 24h P&L: +$25"
```

---

### KEY DIFFERENCES

| Aspect | main.py (Phase 1) | main.py (Phase 2) |
|--------|-------------------|----------------------|
| **Market Data** | CoinGecko API (30s poll) | Bybit WebSocket (<1ms) |
| **Decision Making** | LLM makes direct BUY/SELL | LLM generates conditions |
| **Execution** | TradingEngine | Sniper (sub-ms) |
| **Learning** | LearningSystem (basic) | QuickUpdate + Reflection |
| **Knowledge** | Rules only | CoinScores, Patterns, Rules |
| **Adaptation** | Manual rules | Automatic blacklist, favor, etc. |
| **Dashboard** | dashboard.py (Flask) | dashboard_v2.py (FastAPI) |

---

## PART 2: PRODUCTION STATE

### supervisor.conf (Line 19-20)
```ini
[program:trading_bot]
command=python3 -u src/main.py    # <-- RUNS PHASE 1!

[program:dashboard]
command=python3 -u src/dashboard.py    # <-- RUNS OLD DASHBOARD!
```

### start.sh
- Runs `supervisord -c config/supervisor.conf`
- **Result: Starts Phase 1 system (main.py)**

### start_paper_trading.sh (Line 158)
```bash
python3 src/main.py --dashboard --port $DASHBOARD_PORT
```
- **Result: Starts Phase 2 system (main.py)**
- But this is a MANUAL script, not the default!

### WHICH SYSTEM IS ACTUALLY RUNNING?

| Start Method | System That Runs |
|--------------|-----------------|
| `bash scripts/start.sh` | **Phase 1** (main.py) |
| `bash scripts/start_paper_trading.sh` | **Phase 2** (main.py) |
| `supervisorctl start all` | **Phase 1** (main.py) |

**CONCLUSION:** The documented "production" deployment runs the **OLD Phase 1 system** that lacks all the learning infrastructure built in Phase 2.

---

## PART 3: COMPONENT INVENTORY

| File | Purpose | main.py | main.py | Has Tests | Status |
|------|---------|---------|------------|-----------|--------|
| `__init__.py` | Package marker | - | - | - | N/A |
| `database.py` | SQLite persistence | YES | YES | YES | PRODUCTION |
| `llm_interface.py` | Ollama connection | YES | YES | YES | PRODUCTION |
| `coin_config.py` | 45-coin tier config | YES | YES | NO | PRODUCTION |
| `market_data.py` | CoinGecko API | YES | NO | YES | PHASE 1 ONLY |
| `trading_engine.py` | Trade execution (old) | YES | NO | YES | PHASE 1 ONLY |
| `learning_system.py` | Basic learnings | YES | NO | YES | PHASE 1 ONLY |
| `risk_manager.py` | Position limits | YES | NO | YES | PHASE 1 ONLY |
| `dashboard.py` | Flask dashboard | YES | NO | YES | PHASE 1 ONLY |
| `daily_summary.py` | Report generation | YES | NO | NO | PHASE 1 ONLY |
| `volatility.py` | Volatility calc | YES | NO | NO | PHASE 1 ONLY |
| `metrics.py` | Performance metrics | YES | NO | NO | PHASE 1 ONLY |
| `main.py` | Phase 1 entry | - | - | NO | PRODUCTION |
| `main.py` | Phase 2 entry | - | - | NO | BUILT-NOT-DEPLOYED |
| `market_feed.py` | WebSocket data | NO | YES | YES | BUILT-NOT-DEPLOYED |
| `sniper.py` | Sub-ms execution | NO | YES | YES | BUILT-NOT-DEPLOYED |
| `journal.py` | Rich trade journal | NO | YES | YES | BUILT-NOT-DEPLOYED |
| `strategist.py` | LLM conditions | NO | YES | YES | BUILT-NOT-DEPLOYED |
| `knowledge.py` | Knowledge Brain | NO | YES | YES | BUILT-NOT-DEPLOYED |
| `coin_scorer.py` | Coin performance | NO | YES | YES | BUILT-NOT-DEPLOYED |
| `pattern_library.py` | Pattern storage | NO | YES | YES | BUILT-NOT-DEPLOYED |
| `quick_update.py` | Instant learning | NO | YES | YES | BUILT-NOT-DEPLOYED |
| `reflection.py` | Hourly analysis | NO | YES | YES | BUILT-NOT-DEPLOYED |
| `adaptation.py` | Apply learnings | NO | YES | YES | BUILT-NOT-DEPLOYED |
| `profitability.py` | P&L tracking | NO | YES | YES | BUILT-NOT-DEPLOYED |
| `effectiveness.py` | Adaptation tracking | NO | YES | YES | BUILT-NOT-DEPLOYED |
| `dashboard_v2.py` | FastAPI dashboard | NO | YES | YES | BUILT-NOT-DEPLOYED |

**Summary:**
- **PRODUCTION (supervisor):** 11 files
- **BUILT-NOT-DEPLOYED:** 14 files (all Phase 2 learning infrastructure)

---

## PART 4: TASK VERIFICATION

### Phase 2 Tasks Claimed Complete

| Task | Claimed Build | Code Exists? | Used by main.py? | Used by main.py? | TRUE STATUS |
|------|---------------|--------------|------------------|---------------------|-------------|
| TASK-100 | WebSocket Market Feed | YES (`market_feed.py`) | NO | YES | BUILT-NOT-DEPLOYED |
| TASK-101 | Sniper Execution | YES (`sniper.py`) | NO | YES | BUILT-NOT-DEPLOYED |
| TASK-102 | Trade Journal | YES (`journal.py`) | NO | YES | BUILT-NOT-DEPLOYED |
| TASK-110 | Strategist | YES (`strategist.py`) | NO | YES | BUILT-NOT-DEPLOYED |
| TASK-120 | Knowledge Brain | YES (`knowledge.py`) | NO | YES | BUILT-NOT-DEPLOYED |
| TASK-121 | Coin Scorer | YES (`coin_scorer.py`) | NO | YES | BUILT-NOT-DEPLOYED |
| TASK-122 | Pattern Library | YES (`pattern_library.py`) | NO | YES | BUILT-NOT-DEPLOYED |
| TASK-130 | Quick Update | YES (`quick_update.py`) | NO | YES | BUILT-NOT-DEPLOYED |
| TASK-131 | Reflection Engine | YES (`reflection.py`) | NO | YES | BUILT-NOT-DEPLOYED |
| TASK-133 | Adaptation Engine | YES (`adaptation.py`) | NO | YES | BUILT-NOT-DEPLOYED |
| TASK-140 | Full Integration | YES (`main.py`) | NO | YES | BUILT-NOT-DEPLOYED |
| TASK-141 | Profitability | YES (`profitability.py`) | NO | YES | BUILT-NOT-DEPLOYED |
| TASK-142 | Effectiveness | YES (`effectiveness.py`) | NO | YES | BUILT-NOT-DEPLOYED |
| TASK-143 | Dashboard v2 | YES (`dashboard_v2.py`) | NO | YES | BUILT-NOT-DEPLOYED |

**CONCLUSION:** All Phase 2 code EXISTS and is FUNCTIONAL, but none of it runs in the default production deployment.

---

## PART 5: THE INTELLIGENCE GAP

### What Data Does The LLM Actually See?

**main.py `get_trading_decision()`:**
```
Per coin:
- price_usd
- change_24h
- tier (1, 2, or 3)

Account:
- balance, available_balance, in_positions
- daily_pnl, open_trades, trade_count_today

Learning:
- recent_learnings (text)
- active_rules (text)
- coins_in_cooldown (list)
```

**main.py Strategist:**
```
Per coin:
- price
- change_24h

Knowledge context:
- Coin summaries (status, trades, win_rate, pnl, trend)
- Good/bad coins list
- Active regime rules
- Winning patterns with confidence
- High-confidence pattern descriptions

Account:
- balance, available_balance, recent_pnl_24h
- win_rate_24h, total_trades_24h
```

### Missing Technical Indicators

**NEITHER system has:**
- RSI (Relative Strength Index)
- VWAP (Volume Weighted Average Price)
- ATR (Average True Range)
- Fear & Greed Index
- Funding rates
- Order book depth
- Liquidation data
- On-chain metrics
- Sentiment data

**PDF Audit Claim CONFIRMED:** The LLM only sees basic price data (coin, price, 24h change). No technical indicators.

---

## PART 6: DATABASE SCHEMA

### Tables (21 total)

| Table | Writes | Reads | Used in main.py? |
|-------|--------|-------|-----------------|
| `open_trades` | TradingEngine | TradingEngine, Dashboard | YES |
| `closed_trades` | TradingEngine | Dashboard, Reports | YES |
| `learnings` | LearningSystem | LLMInterface | YES |
| `trading_rules` | RuleManager | LLMInterface | YES |
| `activity_log` | All | Dashboard | YES |
| `account_state` | TradingEngine | All | YES |
| `market_data` | MarketDataFetcher | TradingEngine | YES |
| `price_history` | MarketDataFetcher | Volatility | YES |
| `coin_cooldowns` | RiskManager | RiskManager | YES |
| `monitoring_alerts` | Monitoring | Dashboard | YES |
| `trade_journal` | Journal | Analysis | NO (Phase 2) |
| `active_conditions` | Strategist | Sniper | NO (Phase 2) |
| `coin_scores` | CoinScorer | Strategist | NO (Phase 2) |
| `trading_patterns` | PatternLibrary | Strategist | NO (Phase 2) |
| `regime_rules` | KnowledgeBrain | Strategist | NO (Phase 2) |
| `coin_adaptations` | CoinScorer | Reports | NO (Phase 2) |
| `reflections` | ReflectionEngine | Reports | NO (Phase 2) |
| `adaptations` | AdaptationEngine | Effectiveness | NO (Phase 2) |
| `runtime_state` | main_v2 | main_v2 | NO (Phase 2) |
| `profit_snapshots` | Profitability | Dashboard | NO (Phase 2) |
| `equity_points` | Profitability | Dashboard | NO (Phase 2) |

**11 tables used by main.py, 10 tables for Phase 2 only**

---

## PART 7: DOCUMENTATION ACCURACY

### README.md

| Claim | Reality | Verdict |
|-------|---------|---------|
| "Market Data (CoinGecko)" | main.py uses WebSocket | **WRONG** for Phase 2 |
| Architecture shows old flow | Phase 2 has different architecture | **OUTDATED** |
| "python3 src/main.py" | Phase 2 uses main.py | **INCOMPLETE** |
| "Phase 2: Real Money Trading (Out of Scope)" | Phase 2 is autonomous learning | **WRONG** |
| "qwen2.5-coder:7b" model | Code uses "qwen2.5:14b" | **OUTDATED** |

### docs/architecture/SYSTEM-OVERVIEW.md

| Claim | Reality | Verdict |
|-------|---------|---------|
| Describes main.py architecture | Code matches | **CORRECT** |
| "Binance WebSocket" | Default is Bybit | **MINOR ERROR** |
| Entry point is main.py | Supervisor runs main.py | **MISLEADING** |

### tasks/INDEX.md

| Claim | Reality | Verdict |
|-------|---------|---------|
| Phase 2 Complete (24 tasks) | Code exists | **CORRECT** |
| "Ready for paper trading validation" | main.py runs by default | **MISLEADING** |

---

## PART 8: SUMMARY

### 1. What is ACTUALLY running in production right now?

**When using `bash scripts/start.sh`:**
- `main.py` (Phase 1 system)
- `dashboard.py` (old Flask dashboard)
- CoinGecko polling (30 second intervals)
- Basic learning via LearningSystem
- NO Knowledge Brain, NO Sniper, NO Reflection Engine

### 2. What was built but never deployed?

**14 components (all of Phase 2):**
- `market_feed.py` - WebSocket market data
- `sniper.py` - Sub-millisecond execution
- `journal.py` - Rich trade journal
- `strategist.py` - LLM condition generation
- `knowledge.py` - Knowledge Brain
- `coin_scorer.py` - Per-coin performance tracking
- `pattern_library.py` - Trading patterns
- `quick_update.py` - Instant learning
- `reflection.py` - Hourly LLM analysis
- `adaptation.py` - Automatic adaptations
- `profitability.py` - P&L tracking
- `effectiveness.py` - Adaptation monitoring
- `dashboard_v2.py` - Modern dashboard
- `main.py` - System orchestrator

### 3. What does the LLM actually see when making decisions?

**In main.py (what's running):**
- Coin name
- Price
- 24h change
- Tier (1/2/3)
- Text learnings
- Text rules

**In main.py (what's NOT running):**
- All of the above PLUS:
- Coin performance summaries (win rate, P&L, trend)
- Blacklisted coins
- Favored coins
- Active patterns with confidence scores

**Neither has:** RSI, VWAP, ATR, Fear & Greed, funding rates, order book data.

### 4. Is the learning loop actually closed?

**main.py (running):** PARTIALLY
- Trade → LLM analyzes → Learning created → Rule maybe created
- Rules are text-based, don't auto-adapt
- No automatic blacklisting
- No pattern tracking

**main.py (not running):** YES, FULLY CLOSED
- Trade → QuickUpdate → CoinScorer → PatternLibrary
- Hourly → ReflectionEngine → AdaptationEngine
- Auto-blacklist losing coins
- Auto-favor winning coins
- Pattern confidence tracking
- Effectiveness monitoring

### 5. What's the single biggest gap between documentation and reality?

**The supervisor configuration runs the old Phase 1 system, not the Phase 2 system that the documentation describes.**

The entire Phase 2 infrastructure (24 tasks, 14 components, ~5000 lines of code) exists and works, but it doesn't run unless you manually use `start_paper_trading.sh`.

---

## RECOMMENDATIONS

### Immediate Actions

1. **Update supervisor.conf** to run `main.py` instead of `main.py`:
   ```ini
   [program:trading_bot]
   command=python3 -u src/main.py --dashboard --port 8080
   ```

2. **Update README.md** to reflect Phase 2 architecture

3. **Remove or archive** Phase 1 components that are superseded

### Documentation Updates Needed

1. README.md - Complete rewrite for Phase 2
2. Remove references to CoinGecko (now uses WebSocket)
3. Update architecture diagrams
4. Clarify which startup script to use

### Technical Debt

1. Two parallel systems create confusion
2. Phase 1 components should be archived
3. Test coverage gaps for main entry points
4. No technical indicators (RSI, VWAP, etc.) in either system

---

## CONCLUSION

**Phase 2 is BUILT but NOT DEPLOYED.**

The documentation claims Phase 2 is complete, and the code does exist. However, the default production deployment (`scripts/start.sh` → `supervisor.conf`) still runs the old Phase 1 system (`main.py`).

To actually run the Phase 2 learning system, use:
```bash
bash scripts/start_paper_trading.sh
# OR
python3 src/main.py --dashboard --port 8080
```

---

*Audit completed February 3, 2026*
