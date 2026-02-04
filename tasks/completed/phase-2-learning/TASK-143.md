# TASK-143: Dashboard v2

**Status:** COMPLETE
**Created:** February 3, 2026
**Completed:** February 3, 2026
**Priority:** Medium
**Depends On:** TASK-140 (Full System Integration), TASK-141 (Profitability Tracking), TASK-142 (Effectiveness Monitoring)
**Phase:** Phase 2.5 - Closed Loop

---

## Objective

Create an observability dashboard for monitoring the autonomous trading system. Provides real-time visibility into conditions, knowledge state, adaptations, and allows manual overrides during paper trading.

---

## Background

The autonomous trading system now has:
- Sniper watching conditions from Strategist
- Knowledge Brain with coin scores, patterns, rules
- Reflection Engine generating insights
- Adaptation Engine applying changes
- Effectiveness Monitor tracking results

**Missing:** A unified view to observe and interact with all these components. Currently, we rely on logs which are hard to parse in real-time.

### Requirements

1. **Real-Time View** - See what the bot is doing right now
2. **Knowledge Browser** - Explore accumulated knowledge
3. **Adaptation History** - Track what changed and whether it helped
4. **Manual Control** - Override decisions during paper trading

---

## Specification

### 1. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Dashboard v2                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Real-Time   │  │  Knowledge   │  │  Adaptations │          │
│  │    View      │  │   Browser    │  │     Log      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Manual     │  │ Profitability│  │   System     │          │
│  │  Overrides   │  │    Stats     │  │   Health     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│                    FastAPI Backend                               │
│  /api/conditions  /api/knowledge  /api/adaptations  /api/health │
├─────────────────────────────────────────────────────────────────┤
│                    TradingSystem                                 │
│  Sniper | Strategist | Knowledge | Reflection | Adaptation      │
└─────────────────────────────────────────────────────────────────┘
```

**Technology:**
- **Backend:** FastAPI (async-native, OpenAPI docs)
- **Frontend:** Simple HTML/JS with htmx for dynamic updates (no build step)
- **Styling:** Tailwind CSS via CDN

### 2. API Endpoints

#### Real-Time

```python
GET /api/status
# Returns: System status, health, uptime

GET /api/conditions
# Returns: Active conditions Sniper is watching

GET /api/positions
# Returns: Open positions with unrealized P&L

GET /api/prices
# Returns: Current prices for watched coins

GET /api/feed
# SSE endpoint for real-time updates
```

#### Knowledge Brain

```python
GET /api/knowledge/coins
# Returns: All coin scores with status

GET /api/knowledge/coins/{coin}
# Returns: Detailed coin info

GET /api/knowledge/patterns
# Returns: All patterns with stats

GET /api/knowledge/rules
# Returns: All regime rules

GET /api/knowledge/blacklist
# Returns: Blacklisted coins with reasons

GET /api/knowledge/context
# Returns: Full knowledge context (for Strategist)
```

#### Adaptations

```python
GET /api/adaptations
# Returns: Recent adaptations with effectiveness

GET /api/adaptations/{id}
# Returns: Single adaptation detail

GET /api/adaptations/effectiveness
# Returns: Effectiveness summary by rating
```

#### Profitability

```python
GET /api/profitability/snapshot
# Returns: Current profitability snapshot

GET /api/profitability/by/{dimension}
# Returns: Performance by coin/hour/day/pattern

GET /api/profitability/equity-curve
# Returns: Equity curve data for charting

GET /api/profitability/improvement
# Returns: Is the system improving?
```

#### Manual Overrides (Paper Trading Only)

```python
POST /api/override/blacklist
# Body: {"coin": "DOGE", "reason": "Manual override"}

POST /api/override/unblacklist
# Body: {"coin": "DOGE"}

POST /api/override/disable-pattern
# Body: {"pattern_id": "momentum_breakout"}

POST /api/override/enable-pattern
# Body: {"pattern_id": "momentum_breakout"}

POST /api/override/deactivate-rule
# Body: {"rule_id": "time_filter_xxx"}

POST /api/override/trigger-reflection
# Manually trigger a reflection cycle

POST /api/override/rollback
# Body: {"adaptation_id": "abc123"}
```

### 3. Dashboard Pages

#### 3.1 Real-Time View (Home)

```
┌─────────────────────────────────────────────────────────────────┐
│  🟢 System Running | Uptime: 4h 23m | Feed: OK | Strategist: ON │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ACTIVE CONDITIONS (3)                                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ LONG SOL @ $142.50 (price >= trigger)                     │  │
│  │ Strategy: momentum_breakout | Valid: 2h 15m               │  │
│  │ Reasoning: "SOL showing breakout pattern above $142..."   │  │
│  ├───────────────────────────────────────────────────────────┤  │
│  │ SHORT DOGE @ $0.0825 (price <= trigger)                   │  │
│  │ Strategy: mean_reversion | Valid: 1h 45m                  │  │
│  │ Reasoning: "DOGE overextended after 15% pump..."          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  WATCHED PRICES                                                  │
│  ┌─────────┬──────────┬──────────┬──────────┐                  │
│  │  Coin   │  Price   │  24h %   │  Status  │                  │
│  ├─────────┼──────────┼──────────┼──────────┤                  │
│  │  BTC    │ $67,234  │  +2.3%   │  Active  │                  │
│  │  ETH    │ $3,456   │  +1.8%   │  Active  │                  │
│  │  SOL    │ $141.82  │  +5.2%   │  Active  │                  │
│  │  DOGE   │ $0.0831  │  +15.1%  │ Watching │                  │
│  └─────────┴──────────┴──────────┴──────────┘                  │
│                                                                  │
│  OPEN POSITIONS (1)                                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ LONG ETH | Entry: $3,420 | Current: $3,456 | +$36 (+1.1%) │  │
│  │ SL: $3,350 | TP: $3,550 | Duration: 45m                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2 Knowledge Brain

```
┌─────────────────────────────────────────────────────────────────┐
│  KNOWLEDGE BRAIN                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  COIN SCORES                            [Filter: All ▼]         │
│  ┌─────────┬────────┬─────────┬─────────┬──────────┬─────────┐ │
│  │  Coin   │ Trades │ Win Rate│  P&L    │  Trend   │ Status  │ │
│  ├─────────┼────────┼─────────┼─────────┼──────────┼─────────┤ │
│  │  SOL    │   23   │  65.2%  │ +$127   │    ↑     │ Favored │ │
│  │  ETH    │   45   │  55.6%  │ +$89    │    →     │ Active  │ │
│  │  BTC    │   38   │  52.6%  │ +$42    │    →     │ Active  │ │
│  │  AVAX   │   12   │  41.7%  │ -$18    │    ↓     │ Reduced │ │
│  │  DOGE   │   15   │  26.7%  │ -$52    │    ↓     │ 🚫 BL   │ │
│  └─────────┴────────┴─────────┴─────────┴──────────┴─────────┘ │
│                                                                  │
│  ACTIVE PATTERNS (4)                                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ momentum_breakout    | Conf: 0.72 | Uses: 34 | Win: 62%   │  │
│  │ mean_reversion       | Conf: 0.68 | Uses: 28 | Win: 57%   │  │
│  │ support_bounce       | Conf: 0.65 | Uses: 19 | Win: 53%   │  │
│  │ funding_arb          | Conf: 0.58 | Uses: 12 | Win: 50%   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  REGIME RULES (2 active)                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ ⚠️ time_filter_0203 | REDUCE_SIZE during hours [2,3,4,5]  │  │
│  │    Triggered: 15 times | Saves: ~$45                      │  │
│  ├───────────────────────────────────────────────────────────┤  │
│  │ ✓ regime_btc_down   | REDUCE_SIZE when BTC trending down  │  │
│  │    Triggered: 8 times | Saves: ~$32                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  BLACKLIST (3 coins)                                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ DOGE - 26.7% win rate over 15 trades, -$52 P&L            │  │
│  │ SHIB - 20.0% win rate over 10 trades, -$38 P&L            │  │
│  │ PEPE - Manual blacklist: "Too volatile for current strategy"│ │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.3 Adaptations Log

```
┌─────────────────────────────────────────────────────────────────┐
│  ADAPTATIONS                                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  EFFECTIVENESS SUMMARY                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ●●●● Highly Effective: 3                                 │   │
│  │ ●●● Effective: 5                                         │   │
│  │ ●● Neutral: 8                                            │   │
│  │ ● Ineffective: 2                                         │   │
│  │ ⚠️ Harmful: 1 (rollback available)                       │   │
│  │ ⏳ Pending: 4                                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  RECENT ADAPTATIONS                                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 2h ago | BLACKLIST DOGE                                   │  │
│  │ Insight: "DOGE has 26.7% win rate over 15 trades"         │  │
│  │ Confidence: 0.90 | Effectiveness: ✅ Effective (+8% WR)   │  │
│  ├───────────────────────────────────────────────────────────┤  │
│  │ 5h ago | CREATE_TIME_RULE time_filter_0203                │  │
│  │ Insight: "Hours 2-5 UTC have 25% win rate"                │  │
│  │ Confidence: 0.85 | Effectiveness: ⏳ Pending (12 trades)  │  │
│  ├───────────────────────────────────────────────────────────┤  │
│  │ 1d ago | DEACTIVATE_PATTERN failed_breakout               │  │
│  │ Insight: "Pattern has 28% win rate, -$45 P&L"             │  │
│  │ Confidence: 0.88 | Effectiveness: ⚠️ Harmful (-12% WR)    │  │
│  │ [Rollback Available]                                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.4 Profitability

```
┌─────────────────────────────────────────────────────────────────┐
│  PROFITABILITY                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CURRENT SNAPSHOT                                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Total P&L: +$287.50    Win Rate: 54.2%   Trades: 120     │   │
│  │ Profit Factor: 1.42    Sharpe: 1.28      Drawdown: 4.2%  │   │
│  │ Starting: $10,000      Current: $10,287  Return: +2.9%   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  EQUITY CURVE                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │     $10,300 ┤                              ╭─────        │   │
│  │     $10,200 ┤                    ╭────────╯              │   │
│  │     $10,100 ┤          ╭────────╯                        │   │
│  │     $10,000 ┼─────────╯                                  │   │
│  │      $9,900 ┤                                            │   │
│  │             └────────────────────────────────────────    │   │
│  │              Day 1    Day 2    Day 3    Day 4    Day 5   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  PERFORMANCE BY COIN                                            │
│  ┌─────────┬─────────┬──────────┬───────────┐                  │
│  │  Coin   │  P&L    │ Win Rate │ Contrib % │                  │
│  ├─────────┼─────────┼──────────┼───────────┤                  │
│  │  SOL    │ +$127   │   65%    │   44.2%   │                  │
│  │  ETH    │ +$89    │   56%    │   31.0%   │                  │
│  │  BTC    │ +$42    │   53%    │   14.6%   │                  │
│  └─────────┴─────────┴──────────┴───────────┘                  │
│                                                                  │
│  IMPROVEMENT (7 day)                                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Win Rate: 54.2% → was 48.5% (+5.7%)     ✅ Improving     │   │
│  │ P&L: +$287 → was +$142 (+$145)          ✅ Improving     │   │
│  │ Profit Factor: 1.42 → was 1.18 (+0.24)  ✅ Improving     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.5 Manual Overrides

```
┌─────────────────────────────────────────────────────────────────┐
│  MANUAL OVERRIDES (Paper Trading Mode)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  COIN CONTROLS                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Coin: [DOGE    ▼]                                         │  │
│  │                                                           │  │
│  │ [🚫 Blacklist]  [✅ Unblacklist]  [⭐ Favor]              │  │
│  │                                                           │  │
│  │ Reason: [_________________________________]               │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  PATTERN CONTROLS                                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Pattern: [momentum_breakout ▼]  Status: Active            │  │
│  │                                                           │  │
│  │ [Disable Pattern]  [Enable Pattern]                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  RULE CONTROLS                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Rule: [time_filter_0203 ▼]  Status: Active                │  │
│  │                                                           │  │
│  │ [Deactivate Rule]                                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  SYSTEM CONTROLS                                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ [🔄 Trigger Reflection]  [⏸️ Pause Trading]  [▶️ Resume]  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ADAPTATION ROLLBACK                                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Harmful adaptations available for rollback:               │  │
│  │                                                           │  │
│  │ • DEACTIVATE_PATTERN failed_breakout (1d ago)            │  │
│  │   Effect: -12% win rate                                   │  │
│  │   [Rollback]                                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  NOTES                                                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ [Add note about current session...]                       │  │
│  │ [Save Note]                                               │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4. Implementation

#### 4.1 Dashboard Server

```python
# src/dashboard.py

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncio

class DashboardServer:
    """FastAPI server for the trading dashboard."""

    def __init__(self, trading_system: TradingSystem):
        self.system = trading_system
        self.app = FastAPI(title="Trading Dashboard v2")

        self._setup_routes()
        self._setup_static()

    def _setup_routes(self):
        """Set up API routes."""

        @self.app.get("/api/status")
        async def get_status():
            return self.system.get_status()

        @self.app.get("/api/conditions")
        async def get_conditions():
            return self.system.get_conditions()

        # ... more routes

    def _setup_static(self):
        """Serve static files."""
        self.app.mount(
            "/static",
            StaticFiles(directory="dashboard/static"),
            name="static"
        )

    async def start(self, host="0.0.0.0", port=8080):
        """Start the dashboard server."""
        import uvicorn
        config = uvicorn.Config(self.app, host=host, port=port)
        server = uvicorn.Server(config)
        await server.serve()
```

#### 4.2 Frontend Structure

```
dashboard/
├── static/
│   ├── css/
│   │   └── styles.css
│   └── js/
│       └── dashboard.js
└── templates/
    ├── base.html
    ├── index.html          # Real-time view
    ├── knowledge.html      # Knowledge browser
    ├── adaptations.html    # Adaptation log
    ├── profitability.html  # Profitability stats
    └── overrides.html      # Manual controls
```

### 5. Real-Time Updates

Use Server-Sent Events (SSE) for real-time updates:

```python
@self.app.get("/api/feed")
async def event_stream():
    async def generate():
        while True:
            # Emit updates every second
            data = {
                "prices": self.system.health.get_last_prices(),
                "conditions": len(self.system.get_conditions()),
                "positions": len(self.system.get_positions()),
            }
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

Frontend connection:

```javascript
const eventSource = new EventSource('/api/feed');
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    updatePrices(data.prices);
    updateConditionCount(data.conditions);
};
```

---

## Technical Approach

### Step 1: Create API Layer
- Create `src/dashboard.py` with FastAPI app
- Implement all API endpoints
- Add to TradingSystem as optional component

### Step 2: Create Templates
- Create base HTML template with navigation
- Create page templates for each section
- Use htmx for dynamic updates

### Step 3: Add Real-Time Feed
- Implement SSE endpoint
- Connect frontend to feed
- Update UI reactively

### Step 4: Implement Overrides
- Add POST endpoints for manual actions
- Validate paper trading mode
- Log all manual overrides

### Step 5: Create Startup Integration
- Add --dashboard flag to main.py
- Start dashboard server alongside trading system

### Step 6: Create Tests
- Test API endpoints
- Test override actions

---

## Files to Create

| File | Purpose |
|------|---------|
| `src/dashboard.py` | DashboardServer class with FastAPI |
| `dashboard/templates/base.html` | Base template with nav |
| `dashboard/templates/index.html` | Real-time view |
| `dashboard/templates/knowledge.html` | Knowledge browser |
| `dashboard/templates/adaptations.html` | Adaptation log |
| `dashboard/templates/profitability.html` | Profitability stats |
| `dashboard/templates/overrides.html` | Manual controls |
| `dashboard/static/js/dashboard.js` | Frontend JS |
| `dashboard/static/css/styles.css` | Custom styles |
| `tests/test_dashboard.py` | API tests |

---

## Files to Modify

| File | Change |
|------|--------|
| `src/main.py` | Add dashboard integration, --dashboard flag |
| `requirements.txt` | Add fastapi, uvicorn, jinja2 |

---

## Acceptance Criteria

- [x] Dashboard starts with `--dashboard` flag
- [x] Real-time view shows active conditions and prices
- [x] Knowledge browser shows all coin scores, patterns, rules
- [x] Adaptation log shows recent changes with effectiveness
- [x] Profitability page shows metrics and charts
- [x] Manual overrides work (blacklist, pattern toggle, etc.)
- [x] SSE feed provides real-time updates
- [x] All API endpoints return correct data
- [x] Tests pass (47 tests)

---

## Verification

### Start Dashboard

```bash
python src/main.py --dashboard --port 8080
```

Then open: http://localhost:8080

### API Test

```bash
# Get system status
curl http://localhost:8080/api/status

# Get conditions
curl http://localhost:8080/api/conditions

# Get knowledge
curl http://localhost:8080/api/knowledge/coins

# Manual blacklist
curl -X POST http://localhost:8080/api/override/blacklist \
  -H "Content-Type: application/json" \
  -d '{"coin": "DOGE", "reason": "Manual test"}'
```

### Real-Time Feed Test

```bash
curl -N http://localhost:8080/api/feed
```

---

## Related

- [TASK-140](./TASK-140.md) - Full System Integration
- [TASK-141](./TASK-141.md) - Profitability Tracking
- [TASK-142](./TASK-142.md) - Adaptation Effectiveness Monitoring
- [AUTONOMOUS-TRADER-SPEC.md](../AUTONOMOUS-TRADER-SPEC.md) - Full system architecture
