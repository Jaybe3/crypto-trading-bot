# Deprecation Log

This document tracks deprecated components and planned removals.

---

## main_legacy.py (Deprecated February 3, 2026)

**File:** `src/main_legacy.py`
**Status:** DEPRECATED
**Removal Date:** March 5, 2026 (30 days after deprecation)

### What It Was

The original Phase 1 trading system (`main.py`) that was renamed to `main_legacy.py` when Phase 2 was deployed.

### Why It Was Replaced

Phase 1 (`main_legacy.py`) had significant limitations:

| Aspect | Phase 1 (Legacy) | Phase 2 (Current) |
|--------|------------------|-------------------|
| Market Data | CoinGecko API (30s polling) | WebSocket (<1ms real-time) |
| Decision Making | LLM makes direct BUY/SELL decisions | LLM generates conditions, Sniper executes |
| Execution Speed | ~seconds | <1 millisecond |
| Learning | Basic text learnings | Knowledge Brain with coin scores, patterns, rules |
| Adaptation | Manual rules only | Automatic blacklisting, favoring, rule creation |
| Dashboard | Flask (dashboard.py) | FastAPI (built into main.py) |

### Components Made Obsolete

These Phase 1 components are no longer used by the main system:

| File | Purpose | Status |
|------|---------|--------|
| `src/main_legacy.py` | Old main entry point | DEPRECATED |
| `src/market_data.py` | CoinGecko polling | Superseded by `market_feed.py` |
| `src/trading_engine.py` | Old trade execution | Superseded by `sniper.py` |
| `src/learning_system.py` | Basic learnings | Superseded by Knowledge Brain |
| `src/dashboard.py` | Flask dashboard | Superseded by `dashboard_v2.py` |

### Migration Notes

1. **Configuration:** `supervisor.conf` was updated to run `main.py` (Phase 2) with built-in dashboard
2. **Database:** Phase 2 uses the same database file but adds new tables for Knowledge Brain
3. **State:** The Sniper state file (`data/sniper_state.json`) is new in Phase 2

### Keeping Legacy Code

The legacy code is kept for 30 days for:
- Reference during debugging
- Rollback capability if critical issues arise
- Comparison of behavior between systems

### Removal Checklist

Before removing `main_legacy.py` on March 5, 2026:

- [ ] Confirm Phase 2 has been running stable for 30 days
- [ ] Confirm no critical bugs require legacy comparison
- [ ] Archive the file to `archive/phase1/` if desired
- [ ] Remove the file
- [ ] Update this deprecation log

---

## Related Phase 1 Components

These files are still present but not used by the production system:

### market_data.py
- **Purpose:** CoinGecko API integration
- **Status:** Unused by Phase 2 (uses `market_feed.py` instead)
- **Keep for:** Fallback if WebSocket has issues
- **Review date:** March 5, 2026

### trading_engine.py
- **Purpose:** Trade execution with stop-loss/take-profit
- **Status:** Unused by Phase 2 (uses `sniper.py` instead)
- **Keep for:** Reference
- **Review date:** March 5, 2026

### learning_system.py
- **Purpose:** Basic learning and rule creation
- **Status:** Unused by Phase 2 (uses Knowledge Brain instead)
- **Keep for:** Reference
- **Review date:** March 5, 2026

### dashboard.py
- **Purpose:** Flask web dashboard
- **Status:** Unused by Phase 2 (uses `dashboard_v2.py` instead)
- **Keep for:** Reference
- **Review date:** March 5, 2026

---

## Deprecation Process

When deprecating a component:

1. Rename with `_legacy` suffix or move to `archive/`
2. Add entry to this log with:
   - Deprecation date
   - Planned removal date (usually 30 days)
   - Reason for deprecation
   - What replaces it
3. Update any documentation that references the old component
4. After removal date, verify no issues and delete

---

*Last Updated: February 3, 2026*
