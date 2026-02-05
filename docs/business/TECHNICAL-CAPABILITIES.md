# Technical Capabilities

**Last Updated:** February 3, 2026
**Phase:** 2 Complete

Summary of technical capabilities for the autonomous trading bot.

---

## System Architecture

### Core Loop
```
MarketFeed → Strategist → Sniper → Journal → Learning → Knowledge → Strategist
    ↓            ↓           ↓         ↓          ↓           ↓
WebSocket     LLM      Execution   Record   Update+     Context
  Data      Conditions   Engine    Trades   Reflect    for LLM
```

### Component Count
- Core trading: 4 components
- Learning: 6 components
- Analysis: 3 modules
- Total: 13 major components

---

## Performance Characteristics

| Metric | Target | Achieved |
|--------|--------|----------|
| Price update latency | <10ms | <1ms |
| Condition check | <1ms | 0.0015ms |
| Trade execution | <100ms | <50ms |
| Quick update | <10ms | <5ms |
| Reflection cycle | <5min | ~2min |
| Dashboard update | <1s | 100ms |

---

## Market Data

### WebSocket Connection
- **Source**: Bybit WebSocket API
- **Data Types**: Real-time prices, 24h changes, klines
- **Pairs**: Configurable (default: 20 coins in 3 tiers)
- **Reconnection**: Automatic with backoff

### Market State
```python
{
    "prices": {"BTC": 45000.0, "ETH": 2500.0, ...},
    "changes_24h": {"BTC": 2.5, "ETH": -1.2, ...},
    "volatility": {"BTC": 1.8, "ETH": 2.1, ...},
    "btc_trend": "up",
    "market_sentiment": "bullish"
}
```

---

## Trading Execution

### Condition-Based Trading
- Strategist generates conditions (not direct trades)
- Sniper monitors and executes when triggered
- Sub-millisecond execution latency
- No LLM in critical path

### Trade Condition Structure
```python
TradeCondition:
    coin: str
    direction: "LONG" | "SHORT"
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size_usd: float
    expires_at: datetime
```

### Position Management
- Multiple concurrent positions (configurable max)
- Automatic stop-loss and take-profit
- Position size based on coin status

---

## Learning System

### Two-Tier Architecture

**Tier 1: Quick Update (<10ms)**
- Triggered on every trade close
- Pure math, no LLM
- Updates coin scores
- Updates pattern confidence
- Threshold-based adaptations

**Tier 2: Deep Reflection (~2min)**
- Runs hourly
- LLM-powered analysis
- Pattern detection
- Insight generation
- Strategic adaptations

### Learning Outputs
- Coin status changes (BLACKLIST, FAVOR, REDUCE)
- Pattern confidence updates
- New regime rules
- Trading parameter adjustments

---

## Knowledge Management

### Coin Scoring
| Status | Win Rate | Position Modifier |
|--------|----------|-------------------|
| BLACKLISTED | <30% | 0% (no trading) |
| REDUCED | <45% | 50% |
| NORMAL | 45-60% | 100% |
| FAVORED | >60% | 150% |

### Pattern Library
- Stores trading patterns
- Tracks usage and outcomes
- Confidence scoring (0-1)
- Auto-deactivation at low confidence

### Regime Rules
- Time-based rules (avoid certain hours)
- Volatility-based rules
- Market condition rules
- Automatic trigger tracking

---

## Adaptation System

### Adaptation Types
| Action | Effect |
|--------|--------|
| BLACKLIST | Prevent trading coin |
| FAVOR | Increase position size |
| REDUCE | Decrease position size |
| CREATE_RULE | Add trading rule |
| DEACTIVATE_PATTERN | Stop using pattern |

### Effectiveness Tracking
- Before/after metrics for every adaptation
- Automatic effectiveness rating
- Rollback capability for harmful changes

### Effectiveness Ratings
- `highly_effective`: >20% improvement
- `effective`: 5-20% improvement
- `neutral`: No significant change
- `ineffective`: 0-10% worse
- `harmful`: >10% worse

---

## Database

### Technology
- SQLite for Phase 1-2
- Single file persistence
- ACID compliance
- Easy backup (single file copy)

### Tables
| Table | Purpose | Retention |
|-------|---------|-----------|
| trade_journal | All completed trades | Forever |
| coin_scores | Per-coin performance | Forever |
| trading_patterns | Pattern library | Forever |
| regime_rules | Trading rules | Forever |
| adaptations | Change history | Forever |
| insights | Generated insights | 30 days |
| reflections | Reflection sessions | 30 days |

---

## LLM Integration

### Model
- **Provider**: Ollama (local)
- **Model**: qwen2.5:14b
- **Hosting**: Local machine
- **Cost**: $0 (no API fees)

### Usage
- Condition generation (Strategist)
- Deep reflection (hourly)
- Insight generation

### Fallback
- System continues if LLM unavailable
- Uses existing conditions
- Logs warning

---

## Dashboard

### Technology
- FastAPI backend
- Server-Sent Events (SSE) for real-time
- Jinja2 templates
- No JavaScript framework (vanilla JS)

### Pages
| Page | Purpose |
|------|---------|
| Overview | Real-time status, positions, trades |
| Knowledge | Coin scores, patterns, rules |
| Adaptations | Change history |
| Profitability | Metrics and P&L |
| Overrides | Manual controls |

### API
- RESTful endpoints
- JSON responses
- SSE for real-time updates

---

## Analysis Tools

### Metrics
- Win rate
- Profit factor
- Sharpe ratio
- Max drawdown
- Average win/loss

### Breakdowns
- By coin
- By hour of day
- By pattern
- By time period

### Learning Analysis
- Coin score accuracy
- Pattern confidence correlation
- Adaptation effectiveness
- Improvement over time

---

## Monitoring

### Health Checks
- WebSocket connection status
- LLM availability
- Database accessibility
- Trade activity

### Alerts (via Dashboard)
- High loss rate
- No trades in period
- Learning inactive
- System errors

---

## Security

### Current State (Paper Trading)
- No authentication on dashboard
- Local network only recommended
- No sensitive data exposure

### Real Money Requirements
- Dashboard authentication
- API key encryption
- Network isolation
- Audit logging

---

## Scalability

### Current Limits
- Single instance
- SQLite (single writer)
- Local LLM

### Future Scale Path
- PostgreSQL for multi-writer
- Multiple bot instances
- Cloud deployment
- Distributed LLM

---

## Test Coverage

### Tests
- Unit tests: Per component
- Integration tests: Cross-component
- Analysis tests: Metrics and breakdowns
- Total: 59 tests

### Categories
| Category | Tests |
|----------|-------|
| Coin Scorer | 8 |
| Pattern Library | 6 |
| Quick Update | 7 |
| Reflection | 5 |
| Knowledge Integration | 4 |
| Analysis | 35 |

---

## Related Documentation

- [SYSTEM-OVERVIEW.md](../architecture/SYSTEM-OVERVIEW.md) - Architecture details
- [LEARNING-SYSTEM.md](../architecture/LEARNING-SYSTEM.md) - Learning mechanics
- [DATA-MODEL.md](../architecture/DATA-MODEL.md) - Database schema
- [COMPONENT-REFERENCE.md](../architecture/COMPONENT-REFERENCE.md) - API reference
