# Architecture Decision Records (ADRs)

This document captures significant technical decisions made during development, including context, alternatives considered, and rationale.

---

## ADR-001: Local LLM via Ollama

**Date:** January 2026
**Status:** Accepted
**Context:** Need LLM for trading decisions and trade analysis. Options are cloud APIs (OpenAI, Anthropic) or local inference.

**Decision:** Use Ollama with qwen2.5:14b model running locally on Windows host.

**Alternatives Considered:**
| Option | Pros | Cons |
|--------|------|------|
| OpenAI API | Best quality, easy setup | Cost per call, rate limits, latency |
| Anthropic API | High quality | Cost per call, rate limits |
| Local LLM (Ollama) | Free, no limits, low latency | Requires GPU, quality varies |

**Rationale:**
- Trading bot makes decisions every 30 seconds, 24/7
- At ~2,880 calls/day, API costs would be significant
- Local inference has ~1-2s latency vs 3-5s for API
- qwen2.5:14b provides sufficient quality for trading decisions
- No external dependency for core functionality

**Consequences:**
- Must maintain Ollama installation
- Limited to models that fit in VRAM
- Quality ceiling lower than frontier models

---

## ADR-002: SQLite for Data Persistence

**Date:** January 2026
**Status:** Accepted (revisit for Phase 2)
**Context:** Need database for trades, learnings, rules, and account state.

**Decision:** Use SQLite with single database file.

**Alternatives Considered:**
| Option | Pros | Cons |
|--------|------|------|
| PostgreSQL | Scalable, concurrent, robust | Setup complexity, overkill for Phase 1 |
| SQLite | Simple, single-file, zero config | Limited concurrency, no network access |
| JSON files | Simplest | No querying, corruption risk |

**Rationale:**
- Phase 1 is single-process paper trading
- SQLite is ACID compliant for data integrity
- Single file makes backup trivial
- Dashboard reads don't conflict with bot writes
- Can migrate to Postgres later if needed

**Consequences:**
- Cannot have multiple bot instances
- Must consider migration for Phase 2
- Dashboard and bot share same file (works for now)

---

## ADR-003: Three-Tier Coin Universe

**Date:** January 2026
**Status:** Accepted
**Context:** Need to decide which coins to trade and how to manage risk across different volatility levels.

**Decision:** 20 coins in 3 tiers with tier-specific risk parameters.

**Tiers:**
| Tier | Coins | Max Position | Stop-Loss |
|------|-------|--------------|-----------|
| 1 (Blue Chip) | 5 | 25% of balance | 3% |
| 2 (Established) | 10 | 15% of balance | 5% |
| 3 (High Volatility) | 5 | 10% of balance | 7% |

**Rationale:**
- Blue chips (BTC, ETH) are more predictable → larger positions, tighter stops
- High volatility coins need room to move → smaller positions, wider stops
- 20 coins provides diversity for learning without overwhelming
- Tier structure allows risk-appropriate behavior

**Consequences:**
- Must maintain coin tier assignments
- Adding/removing coins requires config change
- Different strategies may emerge per tier

---

## ADR-004: Conservative Take-Profit Target

**Date:** January 2026
**Status:** Accepted
**Context:** Need to decide when to close winning trades.

**Decision:** Fixed $1 take-profit target across all trades.

**Alternatives Considered:**
| Option | Pros | Cons |
|--------|------|------|
| Percentage-based (2%) | Scales with position | Small positions = tiny profits |
| Fixed dollar ($1) | Consistent, predictable | May leave money on table |
| Trailing stop | Captures trends | Complex, can whipsaw |
| LLM-decided | Adaptive | Unpredictable, hard to test |

**Rationale:**
- Consistent $1 target generates steady learning data
- Small wins compound with high frequency
- Easier to measure system performance
- Reduces complexity in early phase
- Can be revisited once learning system is validated

**Consequences:**
- May exit winning trades too early
- In strong trends, leaves significant gains unrealized
- Works best with high trade frequency

---

## ADR-005: Coin Cooldown for Diversity

**Date:** January 2026
**Status:** Accepted
**Context:** Bot was repeatedly trading the same coin, limiting learning diversity.

**Decision:** 30-minute cooldown after trading a coin. Coin is forbidden during cooldown.

**Alternatives Considered:**
| Option | Pros | Cons |
|--------|------|------|
| No cooldown | Maximum opportunity | Concentration risk, repetitive learnings |
| 5-minute cooldown | Quick recovery | Didn't solve the problem |
| 30-minute cooldown | Forces diversity | May miss good re-entries |
| LLM preference | Adaptive | LLM ignored "prefer diversity" hints |

**Rationale:**
- LLM would not honor soft suggestions to diversify
- Hard constraint (FORBIDDEN) was necessary
- 30 minutes balances diversity with opportunity
- Persistent cooldowns survive bot restarts
- Diverse trades generate diverse learnings

**Consequences:**
- Cannot re-enter strong trends quickly
- Cooldown state must be persisted to database
- Dashboard should show cooldown status (TODO)

---

## ADR-006: Paper Trading First

**Date:** January 2026
**Status:** Accepted
**Context:** Starting point for the trading system.

**Decision:** Build and validate entirely with paper trading before any real money.

**Rationale:**
- Prove learning system works without financial risk
- Catch bugs and edge cases safely
- Build confidence in risk management
- Generate track record for Phase 2 decision
- Learning is the same whether paper or real

**Consequences:**
- No revenue during Phase 1
- Phase 2 requires exchange integration work
- Slippage and fees not modeled (will differ in real trading)

---

## ADR-007: Supervisor for Process Management

**Date:** January 2026
**Status:** Accepted
**Context:** Need 24/7 operation with automatic recovery from crashes.

**Decision:** Use Supervisor to manage bot and dashboard processes.

**Alternatives Considered:**
| Option | Pros | Cons |
|--------|------|------|
| Systemd | Native Linux, robust | Complex for development |
| Supervisor | Python ecosystem, simple | Another dependency |
| PM2 | Popular, good UI | Node.js oriented |
| Manual | Simplest | No auto-restart |

**Rationale:**
- Supervisor is lightweight and Python-native
- Auto-restart on crash
- Easy log management
- Simple configuration
- Works well in WSL2 environment

**Consequences:**
- Must install and configure Supervisor
- Logs managed by Supervisor
- Status checks via supervisorctl

---

## ADR-008: WSL2 Development Environment

**Date:** January 2026
**Status:** Accepted
**Context:** Development machine is Windows with WSL2.

**Decision:** Run bot in WSL2 (Ubuntu), Ollama on Windows host.

**Architecture:**
```
Windows Host                    WSL2 (Ubuntu)
┌─────────────┐                ┌─────────────┐
│   Ollama    │ <───────────── │  Trading    │
│   :11434    │   HTTP API     │    Bot      │
└─────────────┘                └─────────────┘
     GPU                         CPU-bound
```

**Rationale:**
- Ollama needs GPU access (Windows native)
- Bot runs fine on CPU in WSL2
- Network bridge works reliably
- Familiar Linux environment for development

**Consequences:**
- Must use gateway IP (172.27.144.1) for Ollama
- WSL2 IP can change (handled via env var)
- Deployment to Linux server will need adjustment

---

*Last Updated: February 2026*
