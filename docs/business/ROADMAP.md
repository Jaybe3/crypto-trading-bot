# Product Roadmap

## Vision

A fully autonomous trading system that consistently generates returns through self-improving strategy, requiring minimal human intervention.

---

## Phase 1: Foundation ✅ COMPLETE

**Timeline:** Completed January 2026
**Objective:** Prove the core concept works

### Delivered
- [x] Real-time market data integration (CoinGecko)
- [x] LLM-powered trading decisions (Ollama/qwen2.5-coder:7b)
- [x] Paper trading execution engine
- [x] Learning extraction from closed trades
- [x] Rule creation and promotion system
- [x] Risk management (position limits, stop-loss, exposure caps)
- [x] Web dashboard for monitoring
- [x] SQLite database for all state

### Key Decisions Made
- Local LLM over cloud API (cost, latency, no limits)
- SQLite over Postgres (simplicity for Phase 1)
- Paper trading first (prove before risking capital)

---

## Phase 1.5: Production Scaling ✅ COMPLETE

**Timeline:** Completed January 2026
**Objective:** Scale to production-ready 24/7 operation

### Delivered
- [x] Expanded to 45 coins across 3 risk tiers
- [x] Tier-specific risk parameters
- [x] Volatility-based position sizing
- [x] Volume filtering for liquidity
- [x] 24/7 deployment with Supervisor
- [x] Performance monitoring and metrics
- [x] Prometheus endpoint for external monitoring
- [x] Autonomous monitoring agent (self-diagnosis)
- [x] Persistent cooldowns (survive restarts)
- [x] Coin diversity enforcement

### Coin Tiers Implemented
| Tier | Risk Level | Coins | Max Position | Stop-Loss |
|------|------------|-------|--------------|-----------|
| 1 | Low | 5 (BTC, ETH, BNB, XRP, SOL) | 25% | 3% |
| 2 | Medium | 15 (ADA, DOGE, AVAX...) | 15% | 5% |
| 3 | High | 25 (PEPE, FLOKI, BONK...) | 10% | 7% |

---

## Phase 2: Real Money Trading ⬜ NOT STARTED

**Timeline:** TBD - Requires profitability proof
**Objective:** Trade with real capital

### Prerequisites
- [ ] Sustained paper trading profitability (target: 7+ days positive)
- [ ] Win rate >55% over 100+ trades
- [ ] Learning system demonstrably improving decisions
- [ ] At least 5 active rules with positive track records

### Planned Work
- [ ] Exchange API integration (Binance or Coinbase)
- [ ] Real order execution with confirmation
- [ ] Enhanced error handling for real money
- [ ] Withdrawal limits and circuit breakers
- [ ] Tax reporting data export
- [ ] Upgraded monitoring and alerting

### Risk Mitigations
- Start with small capital ($1,000)
- Tighter stop-losses initially
- Manual approval for first N trades
- Kill switch for immediate halt

---

## Phase 3: Optimization (Future)

**Objective:** Maximize returns with proven system

### Potential Enhancements
- Multiple exchange support
- Advanced order types (limit, stop-limit)
- Portfolio rebalancing
- Correlation analysis between coins
- Sentiment integration (news, social)
- GPU-accelerated local LLM for faster decisions

---

## Phase 4: Scale (Future)

**Objective:** Production system for larger capital

### Potential Enhancements
- PostgreSQL migration for scale
- Multi-instance deployment
- Cloud infrastructure (AWS/GCP)
- Real-time P&L dashboard
- Mobile alerts
- Multi-user support

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| Jan 2026 | Local LLM (Ollama) | No API costs, no rate limits, lower latency |
| Jan 2026 | SQLite for Phase 1 | Simplicity, single-file backup, sufficient for paper trading |
| Jan 2026 | 45 coins in 3 tiers | Balance between learning diversity and risk management |
| Jan 2026 | $1 take-profit | Conservative target generates consistent learning data |
| Jan 2026 | 30-min coin cooldown | Enforces diversity, prevents fixation on single coin |

---

*Last Updated: February 2026*
