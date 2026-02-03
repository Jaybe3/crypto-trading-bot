# System Overview - Autonomous Trading Bot v2

**Last Updated:** February 3, 2026
**Phase:** 2 Complete

---

## Executive Summary

The Autonomous Trading Bot is a self-learning cryptocurrency trading system that:
- Monitors real-time market data via WebSocket
- Uses an LLM (Strategist) to generate trading conditions
- Executes trades with sub-millisecond latency (Sniper)
- Learns from every trade outcome
- Automatically adapts its behavior based on accumulated knowledge

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AUTONOMOUS TRADING LOOP                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │  MarketFeed  │───►│  Strategist  │───►│    Sniper    │                   │
│  │  (WebSocket) │    │    (LLM)     │    │  (Executor)  │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
│         │                   ▲                    │                           │
│         │                   │                    ▼                           │
│         │           ┌──────────────┐    ┌──────────────┐                    │
│         │           │  Knowledge   │◄───│   Journal    │                    │
│         │           │    Brain     │    │  (Records)   │                    │
│         │           └──────────────┘    └──────────────┘                    │
│         │                   ▲                    │                           │
│         │                   │                    ▼                           │
│         │           ┌──────────────┐    ┌──────────────┐                    │
│         │           │  Adaptation  │◄───│ Quick Update │                    │
│         │           │   Engine     │    │  (Instant)   │                    │
│         │           └──────────────┘    └──────────────┘                    │
│         │                   ▲                    │                           │
│         │                   │                    ▼                           │
│         │           ┌──────────────┐    ┌──────────────┐                    │
│         └──────────►│  Reflection  │◄───│   Insights   │                    │
│                     │   (Hourly)   │    │ (Generated)  │                    │
│                     └──────────────┘    └──────────────┘                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Overview

### Data Flow Components

| Component | File | Purpose | Latency |
|-----------|------|---------|---------|
| **MarketFeed** | `market_feed.py` | WebSocket connection to Binance, real-time price/kline data | <1ms |
| **Strategist** | `strategist.py` | LLM-powered condition generation using market context | 2-10s |
| **Sniper** | `sniper.py` | Monitors conditions, executes trades instantly | <0.01ms |
| **Journal** | `journal.py` | Records all trades with full context | <5ms |

### Learning Components

| Component | File | Purpose | Frequency |
|-----------|------|---------|-----------|
| **QuickUpdate** | `quick_update.py` | Updates coin scores and pattern confidence | Every trade |
| **CoinScorer** | `coin_scorer.py` | Tracks per-coin win rate, P&L, trends | Every trade |
| **PatternLibrary** | `pattern_library.py` | Manages trading patterns and confidence | Every trade |
| **ReflectionEngine** | `reflection.py` | Deep analysis, insight generation | Hourly |
| **AdaptationEngine** | `adaptation.py` | Applies changes based on insights | After reflection |

### Knowledge Storage

| Component | File | Purpose |
|-----------|------|---------|
| **KnowledgeBrain** | `knowledge.py` | Central knowledge repository |
| **Database** | `database.py` | SQLite persistence layer |

---

## Data Flow Sequence

### 1. Market Data Ingestion
```
Binance WebSocket → MarketFeed → Price Cache → Strategist Context
                                            → Sniper Monitoring
```

### 2. Condition Generation (Every 5 minutes)
```
MarketFeed.get_market_state()
    → Strategist.generate_conditions(market_state, knowledge_context)
    → TradeCondition[] (coin, direction, entry, stop_loss, take_profit)
    → Sniper.set_conditions(conditions)
```

### 3. Trade Execution (Sub-millisecond)
```
MarketFeed.on_price_update(price)
    → Sniper.check_conditions(price)
    → If triggered: Sniper.execute_trade()
    → Position opened → Monitor for exit
    → Exit triggered → Trade closed
    → Journal.record_trade(trade_result)
```

### 4. Instant Learning (Every trade close)
```
Journal.on_trade_close(trade)
    → QuickUpdate.process_trade_close(trade_result)
        → CoinScorer.process_trade_result() → Update coin score
        → PatternLibrary.record_pattern_outcome() → Update confidence
        → Check thresholds → Trigger adaptations if needed
    → ReflectionEngine.add_trade() → Queue for hourly analysis
```

### 5. Deep Learning (Hourly)
```
ReflectionEngine.reflect()
    → Analyze recent trades with LLM
    → Generate insights (patterns, problems, opportunities)
    → AdaptationEngine.apply_insights()
        → Blacklist/favor coins
        → Activate/deactivate patterns
        → Create/modify rules
    → KnowledgeBrain updated
```

### 6. Knowledge Usage (Next cycle)
```
Strategist.generate_conditions()
    → KnowledgeBrain.get_knowledge_context()
        → Coin scores and recommendations
        → Active patterns with confidence
        → Regime rules (time-based, volatility-based)
        → Blacklisted coins to avoid
    → LLM uses context to make better decisions
```

---

## Key Design Decisions

### 1. Two-Tier Learning
- **Quick Update**: Pure math, no LLM, <10ms. Updates scores after every trade.
- **Deep Reflection**: LLM-powered, hourly. Generates insights and complex adaptations.

**Rationale**: Fast feedback loop for immediate adjustments, deep analysis for strategic changes.

### 2. Condition-Based Execution
- Strategist generates conditions (entry price, stop loss, take profit)
- Sniper monitors and executes without LLM involvement

**Rationale**: Sub-millisecond execution, no LLM latency during critical moments.

### 3. Persistent Knowledge
- All knowledge stored in SQLite database
- Survives restarts, accumulates over time

**Rationale**: Continuous learning across sessions.

### 4. Observable Adaptations
- Every adaptation logged with before/after metrics
- Effectiveness tracked and measured

**Rationale**: Verify learning is actually helping, roll back harmful changes.

---

## Component Dependencies

```
                    ┌─────────────┐
                    │  Database   │
                    └─────────────┘
                          ▲
          ┌───────────────┼───────────────┐
          │               │               │
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │  Knowledge  │ │   Journal   │ │ Adaptation  │
    │    Brain    │ │             │ │   Engine    │
    └─────────────┘ └─────────────┘ └─────────────┘
          ▲               ▲               ▲
          │               │               │
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ CoinScorer  │ │ QuickUpdate │ │ Reflection  │
    │ PatternLib  │ │             │ │   Engine    │
    └─────────────┘ └─────────────┘ └─────────────┘
          ▲               ▲               ▲
          │               │               │
          └───────────────┼───────────────┘
                          │
                    ┌─────────────┐
                    │   Sniper    │
                    └─────────────┘
                          ▲
                          │
          ┌───────────────┼───────────────┐
          │               │               │
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ MarketFeed  │ │ Strategist  │ │    LLM      │
    │             │ │             │ │  Interface  │
    └─────────────┘ └─────────────┘ └─────────────┘
```

---

## Performance Characteristics

| Metric | Target | Achieved |
|--------|--------|----------|
| Price update latency | <10ms | <1ms |
| Condition check latency | <1ms | 0.0015ms |
| Trade execution | <100ms | <50ms |
| Quick update processing | <10ms | <5ms |
| Reflection cycle | <5min | ~2min |
| Dashboard update | <1s | 100ms |

---

## Entry Points

| Script | Purpose | Usage |
|--------|---------|-------|
| `main_v2.py` | Full autonomous system | `python src/main_v2.py --dashboard` |
| `dashboard_v2.py` | Dashboard only | `python src/dashboard_v2.py` |
| `market_feed.py` | Market data only | Testing/debugging |

---

## Configuration

### Environment Variables
- `BINANCE_API_KEY`, `BINANCE_API_SECRET`: Exchange credentials
- `OLLAMA_HOST`: LLM server (default: localhost:11434)

### Command Line Arguments
```bash
python src/main_v2.py \
  --mode paper \
  --dashboard \
  --port 8080 \
  --db data/trading_bot.db
```

---

## Related Documentation

- [LEARNING-SYSTEM.md](./LEARNING-SYSTEM.md) - Deep dive into learning mechanics
- [DATA-MODEL.md](./DATA-MODEL.md) - Database schema and relationships
- [COMPONENT-REFERENCE.md](./COMPONENT-REFERENCE.md) - Detailed component documentation
- [../operations/PAPER-TRADING-GUIDE.md](../operations/PAPER-TRADING-GUIDE.md) - Running the system
