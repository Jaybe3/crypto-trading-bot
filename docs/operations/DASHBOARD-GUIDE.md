# Dashboard Guide

**Last Updated:** February 3, 2026
**Phase:** 2 Complete

---

## Overview

The Dashboard v2 provides real-time observability into the trading system. Built with FastAPI and Server-Sent Events (SSE), it shows live prices, positions, learning activity, and performance metrics.

---

## Accessing the Dashboard

### URL

```
http://localhost:8080
```

### Starting Dashboard

**With Trading System:**
```bash
python src/main_v2.py --dashboard --port 8080
```

**Standalone (view only):**
```bash
python src/dashboard_v2.py --port 8080 --db data/trading_bot.db
```

---

## Pages

### Overview (`/`)

The main dashboard showing real-time system state.

**Sections:**
- **System Status**: WebSocket connection, LLM status, uptime
- **Current Prices**: Live cryptocurrency prices
- **Open Positions**: Active trades with unrealized P&L
- **Active Conditions**: Pending trade triggers
- **Recent Trades**: Last 10 completed trades

**Updates:** Every 1 second via SSE

### Knowledge Browser (`/knowledge`)

Explore the bot's accumulated knowledge.

**Sections:**
- **Coin Scores**: Performance by coin with status (FAVORED, NORMAL, REDUCED, BLACKLISTED)
- **Trading Patterns**: Active patterns with confidence scores
- **Regime Rules**: Time and condition-based trading rules

**Features:**
- Sort by any column
- Filter by status
- Click coin for detailed history

### Adaptations (`/adaptations`)

History of all learning-driven changes.

**Columns:**
- Adaptation ID
- Action (BLACKLIST, FAVOR, CREATE_RULE, etc.)
- Target (coin or pattern)
- Reason
- Effectiveness rating
- Applied timestamp

**Filters:**
- By action type
- By effectiveness
- By date range

### Profitability (`/profitability`)

Performance metrics and P&L tracking.

**Metrics Displayed:**
- Total P&L (all time, 24h, 7d)
- Win Rate
- Profit Factor
- Sharpe Ratio
- Max Drawdown
- Average Win/Loss

**Charts:**
- Equity curve
- Daily P&L
- Win rate over time

### Overrides (`/overrides`)

Manual control panel for human intervention.

**Actions Available:**
- Force blacklist a coin
- Unblacklist a coin
- Deactivate a pattern
- Create a regime rule
- Pause/resume trading

**Safety:** All manual actions are logged with reason.

---

## API Endpoints

### Status and Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | System health |
| `/api/health` | GET | Simple health check |

**Example:**
```bash
curl http://localhost:8080/api/status
```

Response:
```json
{
  "status": "running",
  "websocket_connected": true,
  "llm_available": true,
  "uptime_seconds": 3600,
  "last_trade": "2026-02-03T10:30:00Z"
}
```

### Market Data

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/prices` | GET | Current prices |
| `/api/positions` | GET | Open positions |
| `/api/conditions` | GET | Active conditions |

### Knowledge

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/knowledge/coins` | GET | Coin scores |
| `/api/knowledge/patterns` | GET | Pattern library |
| `/api/knowledge/rules` | GET | Regime rules |
| `/api/knowledge/context` | GET | Full context for Strategist |

### Trading

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/trades` | GET | Recent trades |
| `/api/trades/{id}` | GET | Single trade details |
| `/api/adaptations` | GET | Adaptation history |

### Analytics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/profitability` | GET | Current metrics |
| `/api/profitability/history` | GET | Historical metrics |
| `/api/analytics/by-coin` | GET | Performance by coin |
| `/api/analytics/by-hour` | GET | Performance by hour |

### Real-Time Feed

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/feed` | GET | SSE event stream |

**Events:**
- `price_update`: New price data
- `position_opened`: Trade entered
- `position_closed`: Trade exited
- `condition_triggered`: Condition activated
- `adaptation_applied`: Learning change

**Example:**
```javascript
const source = new EventSource('/api/feed');
source.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data.payload);
};
```

---

## Query Parameters

### Filtering

```bash
# Trades by coin
curl "http://localhost:8080/api/trades?coin=BTC"

# Trades in date range
curl "http://localhost:8080/api/trades?from=2026-02-01&to=2026-02-03"

# Adaptations by action
curl "http://localhost:8080/api/adaptations?action=BLACKLIST"
```

### Pagination

```bash
# First 20 trades
curl "http://localhost:8080/api/trades?limit=20&offset=0"

# Next 20
curl "http://localhost:8080/api/trades?limit=20&offset=20"
```

### Sorting

```bash
# Coins by win rate (descending)
curl "http://localhost:8080/api/knowledge/coins?sort=win_rate&order=desc"
```

---

## Real-Time Updates

The dashboard uses Server-Sent Events for live updates.

### How It Works

1. Client connects to `/api/feed`
2. Server pushes events as they occur
3. UI updates without page refresh

### Event Types

| Event | Payload | Frequency |
|-------|---------|-----------|
| `heartbeat` | `{timestamp}` | Every 5s |
| `price_update` | `{coin, price, change}` | Every 1s |
| `position_opened` | `{trade_id, coin, direction, entry}` | On entry |
| `position_closed` | `{trade_id, coin, pnl, exit_reason}` | On exit |
| `insight_generated` | `{insight_type, title, confidence}` | Hourly |
| `adaptation_applied` | `{action, target, reason}` | On learn |

---

## Customization

### Changing Port

```bash
python src/dashboard_v2.py --port 9090
```

### External Access

By default, dashboard binds to `0.0.0.0` allowing LAN access.

```bash
# Access from another machine
http://192.168.1.100:8080
```

**Security Note:** No authentication in v2. Only expose on trusted networks.

### Refresh Rates

Default refresh rates:
- Prices: 1 second
- Positions: 1 second
- Metrics: 30 seconds
- Adaptations: 60 seconds

---

## Troubleshooting

### Dashboard Won't Load

1. Check process is running:
   ```bash
   pgrep -f "dashboard"
   ```

2. Check port is available:
   ```bash
   lsof -i :8080
   ```

3. Check logs:
   ```bash
   grep -i dashboard logs/bot.log | tail -20
   ```

### Data Not Updating

1. Check SSE connection:
   - Browser dev tools > Network > Filter "feed"
   - Should show open connection

2. Check database:
   ```bash
   sqlite3 data/trading_bot.db "SELECT MAX(exit_time) FROM trade_journal;"
   ```

3. Refresh page (hard refresh: Ctrl+Shift+R)

### API Errors

Check `/api/status` first:
```bash
curl http://localhost:8080/api/status
```

If LLM unavailable, system continues but Strategist won't generate new conditions.

---

## Related Documentation

- [PAPER-TRADING-GUIDE.md](./PAPER-TRADING-GUIDE.md) - Running paper trading
- [RUNBOOK.md](./RUNBOOK.md) - Operations reference
- [../architecture/COMPONENT-REFERENCE.md](../architecture/COMPONENT-REFERENCE.md) - API details
