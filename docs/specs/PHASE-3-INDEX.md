# Phase 3: Market Context Enhancement

## Overview

Enhance the autonomous trader with market-wide context and sentiment data to improve decision quality. The bot should understand *why* prices are moving, not just *that* they're moving.

**Prerequisite:** Phase 2 complete with proven learning loop

---

## Rationale

Phase 2 creates a bot that learns from its own trades. Phase 3 gives it external context to make better decisions *before* entering trades, rather than learning only through losses.

### Without Context (Phase 2)
1. SOL drops 5% → Bot enters short
2. SOL recovers (was just tracking BTC dip)
3. Bot loses money → Learns "SOL shorts risky"

### With Context (Phase 3)
1. SOL drops 5% → Bot checks: BTC also down 4%, Fear at 25
2. Bot recognizes: "Market-wide dip, not SOL weakness"
3. Bot skips trade or goes long on oversold bounce
4. No loss required to learn

---

## Implementation Phases

### Phase 3.1: Core Context Layer
| Task | Description | Status |
|------|-------------|--------|
| TASK-300 | Sentiment & Context Layer | Not Started |
| TASK-301 | BTC Correlation Tracking | Not Started |
| TASK-302 | Fear & Greed Integration | Not Started |

**Milestone:** Context data flowing to Strategist

### Phase 3.2: News & Events
| Task | Description | Status |
|------|-------------|--------|
| TASK-310 | News Feed Integration | Not Started |
| TASK-311 | Event Detection (listings, unlocks) | Not Started |
| TASK-312 | News → Trade Signal Mapping | Not Started |

**Milestone:** Bot avoids trades during negative news events

### Phase 3.3: Social Signals (Optional)
| Task | Description | Status |
|------|-------------|--------|
| TASK-320 | Social Sentiment Integration | Not Started |
| TASK-321 | Trending Coin Detection | Not Started |
| TASK-322 | Crowd Mood Analysis | Not Started |

**Milestone:** Bot uses social signals for timing

### Phase 3.4: Context Learning
| Task | Description | Status |
|------|-------------|--------|
| TASK-330 | Context Performance Tracking | Not Started |
| TASK-331 | Context Weight Optimization | Not Started |
| TASK-332 | Context → Knowledge Brain | Not Started |

**Milestone:** Bot learns which context signals matter

---

## Data Sources

| Data Type | Source | Cost | Priority |
|-----------|--------|------|----------|
| Fear & Greed | Alternative.me | Free | High |
| BTC Correlation | Internal (MarketFeed) | Free | High |
| News | CryptoPanic | Free (limited) | Medium |
| Social | LunarCrush | Free (limited) | Low |

---

## Success Criteria

The context layer is working when:

1. Trade decisions incorporate market-wide context
2. Bot avoids trades during obvious market-wide moves
3. Context is recorded with each trade for learning
4. Win rate improves compared to Phase 2 baseline
5. Fewer "learned the hard way" losses

---

## Dependencies

- Phase 2.1 ✓ (Speed Infrastructure)
- Phase 2.2 ✓ (Strategist Integration)
- Phase 2.3 ✓ (Knowledge Brain)
- Phase 2.4 ✓ (Reflection Engine)
- Phase 2.5 ✓ (Closed Loop)
- Phase 2.6 ✓ (Validation - 7 day run)

---

*Last Updated: February 2, 2026*
