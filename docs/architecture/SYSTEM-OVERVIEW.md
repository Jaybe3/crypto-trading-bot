# System Architecture Overview

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TRADING BOT SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────────┐  │
│   │  CoinGecko  │────>│ Market Data │────>│                             │  │
│   │    API      │     │  Fetcher    │     │                             │  │
│   └─────────────┘     └─────────────┘     │                             │  │
│                              │            │      LLM Interface          │  │
│                              ▼            │      (Ollama)               │  │
│   ┌─────────────┐     ┌─────────────┐     │                             │  │
│   │   SQLite    │<───>│  Database   │<───>│  - Trading Decisions       │  │
│   │  Database   │     │   Layer     │     │  - Trade Analysis          │  │
│   └─────────────┘     └─────────────┘     │  - Learning Extraction     │  │
│                              │            │                             │  │
│                              ▼            └─────────────────────────────┘  │
│                       ┌─────────────┐                   │                  │
│                       │    Risk     │                   │                  │
│                       │  Manager    │<──────────────────┘                  │
│                       └─────────────┘                                      │
│                              │                                             │
│                              ▼                                             │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────────┐  │
│   │  Learning   │<────│  Trading    │────>│      Flask Dashboard        │  │
│   │   System    │     │   Engine    │     │      (Port 8080)            │  │
│   └─────────────┘     └─────────────┘     └─────────────────────────────┘  │
│          │                                                                 │
│          ▼                                                                 │
│   ┌─────────────┐                                                          │
│   │    Rule     │                                                          │
│   │  Manager    │                                                          │
│   └─────────────┘                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

External:
┌─────────────┐     ┌─────────────┐
│   Ollama    │     │ Supervisor  │
│  (Windows)  │     │  (Process)  │
└─────────────┘     └─────────────┘
```

## Component Descriptions

### Core Components

| Component | File | Responsibility |
|-----------|------|----------------|
| **Main Loop** | `src/main.py` | Orchestrates 30-second trading cycle |
| **Market Data** | `src/market_data.py` | Fetches prices from CoinGecko API |
| **LLM Interface** | `src/llm_interface.py` | Communicates with Ollama for decisions |
| **Trading Engine** | `src/trading_engine.py` | Executes paper trades |
| **Risk Manager** | `src/risk_manager.py` | Enforces position limits and stop-losses |
| **Learning System** | `src/learning_system.py` | Analyzes trades, extracts learnings |
| **Rule Manager** | `src/learning_system.py` | Promotes learnings to rules |
| **Database** | `src/database.py` | SQLite operations |
| **Dashboard** | `src/dashboard.py` | Flask web UI |
| **Coin Config** | `src/coin_config.py` | 45-coin tier configuration |

### Supporting Components

| Component | File | Responsibility |
|-----------|------|----------------|
| **Daily Summary** | `src/daily_summary.py` | Generates daily performance reports |
| **Metrics** | `src/metrics.py` | Performance metrics and Prometheus endpoint |
| **Volatility** | `src/volatility.py` | Volatility calculations for position sizing |
| **Autonomous Monitor** | `scripts/autonomous_monitor.py` | Self-diagnosing agent |

## Data Flow

### Trading Cycle (Every 30 Seconds)

```
1. FETCH      Market Data Fetcher gets prices for 45 coins from CoinGecko
                    │
                    ▼
2. UPDATE     Trading Engine checks open positions against current prices
              - Triggers stop-loss if threshold breached
              - Triggers take-profit if $1 gain reached
                    │
                    ▼
3. ANALYZE    If trades closed, Learning System analyzes each:
              - Sends trade details to LLM
              - Extracts what happened, why, pattern, lesson
              - Stores learning in database
                    │
                    ▼
4. PROMOTE    Rule Manager checks high-confidence learnings
              - Learnings ≥70% confidence become candidate rules
              - Rules enter testing phase
              - Validated rules become active
                    │
                    ▼
5. DECIDE     LLM Interface builds context and queries LLM:
              - Current market data (prices, 24h changes)
              - Account state (balance, exposure)
              - Recent learnings
              - Active rules
              - Coins in cooldown (forbidden)
                    │
                    ▼
6. VALIDATE   Risk Manager validates proposed trade:
              - Size within 2% of balance?
              - Total exposure under 10%?
              - Coin not in cooldown?
              - Tier-specific limits respected?
                    │
                    ▼
7. EXECUTE    Trading Engine executes if valid:
              - Records trade in database
              - Updates account state
              - Starts cooldown timer for coin
```

### Learning Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                       LEARNING LOOP                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Trade Closes ──> LLM Analysis ──> Learning Created            │
│        │                                    │                   │
│        │                                    ▼                   │
│        │                           Confidence ≥ 70%?            │
│        │                              │          │              │
│        │                             Yes         No             │
│        │                              │          │              │
│        │                              ▼          ▼              │
│        │                        Create Rule   Store Only        │
│        │                              │                         │
│        │                              ▼                         │
│        │                        Testing Phase                   │
│        │                        (10 trades)                     │
│        │                              │                         │
│        │                              ▼                         │
│        │                      Success Rate OK?                  │
│        │                        │          │                    │
│        │                       Yes         No                   │
│        │                        │          │                    │
│        │                        ▼          ▼                    │
│        │                   Promote to   Reject Rule             │
│        │                   Active                               │
│        │                        │                               │
│        └────────────────────────┴───────────────────────────────│
│                                 │                               │
│                    Active Rules Inform Future Decisions         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| CoinGecko API | Market data | Bot skips cycle, retries next interval |
| Ollama (Windows) | LLM inference | Bot defaults to HOLD |
| Supervisor | Process management | Manual restart required |
| SQLite | Data persistence | Bot cannot function |

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_HOST` | `172.27.144.1` | Ollama server address (WSL2 gateway) |
| `LOOP_INTERVAL` | `30` | Seconds between trading cycles |
| `MIN_CONFIDENCE` | `0.3` | Minimum confidence for trade execution |

### Hardcoded Limits (Non-Configurable)

| Limit | Value | Rationale |
|-------|-------|-----------|
| Max per trade | 2% | Prevent single-trade blowup |
| Max exposure | 10% | Preserve capital |
| Take profit | $1 | Consistent, conservative target |
| Tier 1 stop-loss | 3% | Tight stops for blue chips |
| Tier 2 stop-loss | 5% | Medium stops for established coins |
| Tier 3 stop-loss | 7% | Wider stops for volatile coins |
| Coin cooldown | 30 min | Enforce diversity |

---

*Last Updated: February 2026*
