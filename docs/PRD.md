# Product Requirements Document: Self-Learning Crypto Trading Bot

## Vision
An autonomous cryptocurrency trading bot that learns from every trade, continuously improving its decision-making through LLM-powered analysis and rule evolution.

## Core Principles
1. **Learn from every trade** - Win or lose, extract actionable insights
2. **Rules evolve from patterns** - High-confidence learnings become trading rules
3. **Risk-first approach** - Never risk more than we can afford to lose
4. **Transparency** - All decisions logged and explainable
5. **Incremental scaling** - Prove at small scale before expanding

---

## PHASE 1: Foundation (Paper Trading) - COMPLETE ✅

### Goals Achieved
- [x] Functional paper trading system with $1,000 virtual balance
- [x] Real market data from CoinGecko API
- [x] LLM-powered trading decisions (Claude)
- [x] Automatic learning extraction from closed trades
- [x] Rule creation from high-confidence patterns
- [x] Risk management with position limits, stop-loss, take-profit
- [x] Live web dashboard with real-time monitoring
- [x] Daily summary reports

### Components Built
| Component | File | Status |
|-----------|------|--------|
| Database Layer | `src/database.py` | ✅ Complete |
| Market Data | `src/market_data.py` | ✅ Complete |
| LLM Interface | `src/llm_interface.py` | ✅ Complete |
| Risk Manager | `src/risk_manager.py` | ✅ Complete |
| Trading Engine | `src/trading_engine.py` | ✅ Complete |
| Learning System | `src/learning_system.py` | ✅ Complete |
| Web Dashboard | `src/dashboard.py` | ✅ Complete |
| Daily Summary | `src/daily_summary.py` | ✅ Complete |
| Main Loop | `src/main.py` | ✅ Complete |

### Metrics from Phase 1
- Coins tracked: 5 (BTC, ETH, SOL, DOGE, XRP)
- Learning extraction: Automated after each trade
- Rule evolution: Testing → Active → Rejected lifecycle
- Dashboard: Real-time with 5-second refresh

---

## PHASE 1.5: Production Optimization (Current)

### Goals
1. **Scale coin universe** - Expand from 5 to 40-50 coins
2. **Multi-tier strategy** - Different approaches for different market caps
3. **24/7 deployment** - Continuous operation with monitoring
4. **Performance optimization** - Handle increased data volume efficiently

### New Capabilities

#### Multi-Tier Coin Universe
| Tier | Market Cap | Coins | Strategy |
|------|------------|-------|----------|
| Tier 1 | Top 10 | ~10 | Conservative, larger positions |
| Tier 2 | Top 11-30 | ~20 | Balanced risk/reward |
| Tier 3 | Top 31-50 | ~20 | Aggressive, smaller positions |

#### Volatility-Based Risk Adjustment
- Dynamic position sizing based on 24h volatility
- Automatic stop-loss/take-profit adjustment
- Reduced exposure during high-volatility periods

#### 24/7 Deployment
- Systemd service configuration
- Automatic restart on failure
- Health check endpoints
- Alert system for critical issues

#### Performance Monitoring
- API rate limit tracking
- Trade execution latency
- Learning system throughput
- Memory/CPU utilization

### Success Criteria
- [ ] 40+ coins tracked without API rate limit issues
- [ ] Tier-appropriate strategies executing correctly
- [ ] System runs 7+ days without manual intervention
- [ ] All metrics visible in dashboard

---

## PHASE 2: Real Money Trading (OUT OF SCOPE)

Phase 2 will only begin after:
1. Phase 1.5 runs successfully for 30+ days
2. Paper trading shows consistent positive returns
3. Full security audit of API key handling
4. Legal/tax implications reviewed

**Phase 2 is explicitly OUT OF SCOPE for current development.**

---

## Technical Constraints

### API Limits
- CoinGecko Free: 10-30 calls/minute
- Anthropic Claude: Based on subscription tier

### Risk Limits (Paper Trading)
- Max position size: 20% of balance
- Max concurrent positions: 5
- Daily loss limit: 10% of balance
- Stop-loss: Required on all trades

### Data Storage
- SQLite for simplicity and portability
- All trades, learnings, rules persisted
- Daily reports saved to `data/reports/`

---

## Mandatory Workflow

Every feature follows this process:

```
1. SPEC    → Write detailed specification
2. REVIEW  → User approves approach
3. BUILD   → Implement the feature
4. VERIFY  → Test and validate
5. APPROVE → User confirms completion
```

No code is written without a spec. No feature ships without verification.
