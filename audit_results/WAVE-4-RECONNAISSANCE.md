# Wave 4 Reconnaissance: Phase 3 Integration

**Date:** February 5, 2026
**Purpose:** Understand current system before Phase 3 integration
**Status:** READ-ONLY investigation complete

---

## 1. Trading Loop

### Architecture Overview

The system uses an **async architecture** with multiple concurrent components:

```
main.py::TradingSystem
    ├── MarketFeed (WebSocket, continuous)
    ├── Strategist (runs every 180s)
    ├── Sniper (reacts to price ticks)
    ├── ReflectionEngine (runs hourly)
    └── _main_loop (health checks every 30s)
```

### Main Loop Function (src/main.py:449-496)

```python
async def _main_loop(self) -> None:
    """Main system loop - status logging and health checks."""
    health_check_interval = 30  # Check health every 30 seconds
    last_health_check = 0
    last_snapshot_check = 0
    snapshot_check_interval = 300  # Check for snapshots every 5 minutes
    last_effectiveness_check = 0
    effectiveness_check_interval = 3600  # Check effectiveness every hour

    while self._running:
        await asyncio.sleep(1)
        now = time.time()

        # Periodic status log
        if now - self._last_status_log >= STATUS_LOG_INTERVAL:
            self._log_status()
            self._last_status_log = now

        # Periodic health check (TASK-140)
        if now - last_health_check >= health_check_interval:
            health = self.health_check()
            if health["overall"] != "healthy":
                logger.warning(f"System health degraded: {health['overall']}")
            last_health_check = now

        # Periodic snapshot check (TASK-141)
        if now - last_snapshot_check >= snapshot_check_interval:
            if self.snapshot_scheduler:
                taken = self.snapshot_scheduler.check_and_take_snapshots()
            last_snapshot_check = now

        # Periodic effectiveness check (TASK-142)
        if now - last_effectiveness_check >= effectiveness_check_interval:
            if self.effectiveness_monitor:
                results = self.effectiveness_monitor.check_pending_adaptations()
            last_effectiveness_check = now
```

**Key Finding:** The main loop is NOT the trading decision loop. It's a health monitoring loop that runs every 1 second and performs periodic checks.

### Strategist Loop (src/strategist.py:154-172)

The actual trading decisions happen in the Strategist, which runs independently:

```python
async def _run_loop(self) -> None:
    """Main loop that generates conditions periodically."""
    while self._running:
        try:
            # Generate new conditions
            conditions = await self.generate_conditions()

            # Notify callbacks
            self._notify_callbacks(conditions)

            # Wait for next cycle
            await asyncio.sleep(self.interval)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in strategist loop: {e}")
            # Wait before retrying on error
            await asyncio.sleep(30)
```

### Call Sequence

Every 180 seconds (3 minutes):
1. `generate_conditions()` called
2. `_remove_expired_conditions()` - cleanup
3. `_check_regime_rules()` - check if NO_TRADE rule active
4. `_build_context()` - gather market data + knowledge
5. `_build_prompt(context)` - format for LLM
6. `llm.query(prompt, system_prompt)` - call qwen2.5:14b
7. `_parse_response(response)` - extract conditions
8. `_validate_condition(condition)` - validate each condition
9. `db.save_condition()` - persist to database
10. `_notify_callbacks(conditions)` - send to Sniper

---

## 2. Current LLM Prompt

### System Prompt (src/strategist.py:491-545)

```python
"""You are the Strategist for an autonomous trading bot. Your job is to set up trade conditions for the Sniper to watch and execute.

IMPORTANT RULES:
1. Only suggest coins that are NOT in the avoid list
2. Position size MUST be between $20 and $100 (NEVER exceed $100)
3. Stop-loss should be 1-3%
4. Take-profit should be 1-2%
5. You can suggest 0-3 conditions (0 if no good setups)
6. Each condition must have a clear, specific trigger price
7. Only suggest LONG trades (we don't support SHORT yet)

CRITICAL - TRIGGER PRICE RULES:
- Conditions expire in 5 minutes, so trigger prices MUST be very close to current price
- For ABOVE triggers: set trigger_price 0.1-0.3% ABOVE current price
- For BELOW triggers: set trigger_price 0.1-0.3% BELOW current price
- DO NOT set triggers more than 0.5% from current price - they will expire before triggering

OUTPUT FORMAT:
You MUST respond with valid JSON in exactly this format:
{
    "conditions": [
        {
            "coin": "SOL",
            "direction": "LONG",
            "trigger_price": 143.50,
            "trigger_condition": "ABOVE",
            "stop_loss_pct": 2.0,
            "take_profit_pct": 1.5,
            "position_size_usd": 50,
            "reasoning": "Brief explanation of why this trade",
            "strategy_id": "pattern_name"
        }
    ],
    "market_assessment": "Brief assessment of overall market conditions",
    "no_trade_reason": null
}
"""
```

### User Prompt (_build_prompt) (src/strategist.py:548-636)

```python
def _build_prompt(self, context: Dict[str, Any]) -> str:
    # ... formatting code ...

    return f"""CURRENT MARKET STATE:
{prices_text}

COIN PERFORMANCE (your track record):
{coin_summary_text}

COINS TO FAVOR: {', '.join(knowledge['good_coins']) or 'None identified'}
COINS TO AVOID: {', '.join(knowledge['avoid_coins']) or 'None blacklisted'}

ACTIVE REGIME RULES:
{rules_text}

WINNING PATTERNS: {patterns_list}
{pattern_section}
ACCOUNT STATE:
- Balance: ${account['balance_usd']:,.2f}
- Available: ${account['available_balance']:,.2f}
- 24h P&L: ${account['recent_pnl_24h']:,.2f}

RECENT PERFORMANCE:
- Win rate (24h): {performance['win_rate_24h']*100:.0f}%
- Trades today: {performance['total_trades_24h']}

Based on this data, generate 0-3 specific trade conditions.
Set trigger prices that are realistic (near current prices).
If using a known pattern, include pattern_id in your response.
Respond with JSON only - no other text."""
```

### What the LLM Currently Sees

| Data Category | Source | Included |
|--------------|--------|----------|
| Prices (20 coins) | MarketFeed WebSocket | YES |
| 24h price changes | MarketFeed WebSocket | YES |
| Coin performance (top 5) | KnowledgeBrain.coin_scores | YES |
| Good/Avoid coin lists | KnowledgeBrain | YES |
| Active regime rules | KnowledgeBrain | YES |
| Winning patterns | PatternLibrary | YES |
| Account balance | Database | YES |
| 24h P&L | Database | YES |
| Recent win rate | Database | YES |
| **RSI** | TechnicalManager | **NO** |
| **VWAP** | TechnicalManager | **NO** |
| **ATR** | TechnicalManager | **NO** |
| **Funding rates** | TechnicalManager | **NO** |
| **Support/Resistance** | TechnicalManager | **NO** |
| **Order book** | TechnicalManager | **NO** |
| **Fear & Greed** | ContextManager | **NO** |
| **BTC correlation** | ContextManager | **NO** |
| **News** | ContextManager | **NO** |
| **Social sentiment** | ContextManager | **NO** |

### Estimated Token Count

Current prompt structure:
- System prompt: ~350 tokens
- Price data (20 coins): ~200 tokens
- Coin performance (5 coins): ~100 tokens
- Lists and rules: ~100 tokens
- Account state: ~50 tokens
- Instructions: ~100 tokens

**Estimated current prompt size: ~900 tokens**

---

## 3. Phase 3 Module Outputs

### TechnicalManager (src/technical/manager.py)

**Main method:** `get_technical_snapshot(coin: str) -> TechnicalSnapshot`

**TechnicalSnapshot dataclass fields:**
```python
@dataclass
class TechnicalSnapshot:
    coin: str
    rsi: Optional[RSIData] = None
    vwap: Optional[VWAPData] = None
    atr: Optional[ATRData] = None
    funding: Optional[FundingData] = None
    sr_levels: Optional[SRLevels] = None
    volume_profile: Optional[VolumeProfile] = None
    orderbook: Optional[OrderBookDepth] = None
    timestamp: datetime = field(default_factory=datetime.now)
```

**Has LLM-ready formatting:** `to_prompt() -> str`

```
=== SOL TECHNICAL ===
RSI: 45.2 (neutral)
VWAP: $143.50 (+0.5%, above)
ATR: $2.50 (1.7% volatility)
Funding: 0.0100% (neutral)
Support: $140.00 (2.5% below)
Resistance: $150.00 (4.3% above)
POC: $142.00 (below_poc)
Order Book: bullish (imbalance: +0.15)
```

**Additional methods:**
- `get_trade_setup_quality(coin, direction) -> Tuple[float, str]` - Returns score 0-100
- `get_dynamic_stops(coin, direction, entry_price) -> Tuple[float, float]` - ATR-based stops
- `get_position_size(coin, ...) -> float` - Volatility-adjusted sizing

### ContextManager (src/sentiment/context_manager.py)

**Main methods:**
- `get_context() -> MarketContext` - Overall market sentiment
- `get_coin_context(coin: str) -> CoinContext` - Coin-specific sentiment

**MarketContext dataclass fields:**
```python
@dataclass
class MarketContext:
    fear_greed: Optional[FearGreedData] = None
    btc_change_1h: float = 0.0
    btc_change_24h: float = 0.0
    breaking_news: List[NewsItem] = field(default_factory=list)
    timestamp: datetime
```

**Has LLM-ready formatting:** `to_prompt() -> str`

```
=== MARKET CONTEXT ===
Fear & Greed: 25 (extreme_fear)
BTC: -2.5% (1h), -5.2% (24h)
EXTREME FEAR - Market may be oversold
Breaking News: 2 items
  RED NEWS HEADLINE...
  GREEN NEWS HEADLINE...
```

**CoinContext dataclass fields:**
```python
@dataclass
class CoinContext:
    coin: str
    btc_correlation: Optional[BTCCorrelation] = None
    recent_news: List[NewsItem] = field(default_factory=list)
    social_metrics: Optional[SocialMetrics] = None
    timestamp: datetime
```

**Has LLM-ready formatting:** `to_prompt() -> str`

```
=== SOL CONTEXT ===
BTC Correlation: 0.85 (high)
  Move is BTC-driven (following)
Social: Rank #5, Sentiment 72/100 (bullish)
  TRENDING
  Social spike: 2.5x normal
Recent News: 2 items
  GREEN Solana upgrade announcement...
```

---

## 4. Data Dependencies

### HTTP Calls by Module

| Module | API | Can Block? | Timeout | Rate Limit |
|--------|-----|------------|---------|------------|
| CandleFetcher | Bybit REST | Yes | 10s | Unknown |
| FundingRateFetcher | Bybit REST | Yes | 10s | Unknown |
| OrderBookAnalyzer | Bybit REST | Yes | 10s | Unknown |
| FearGreedFetcher | Alternative.me | Yes | 10s | Unknown |
| NewsFeedFetcher | CryptoPanic | Yes | 10s | Free tier limits |
| SocialSentimentFetcher | LunarCrush | Yes | 10s | Free tier limits |

### Initialization Requirements

**TechnicalManager requires:**
```python
def __init__(
    self,
    candle_fetcher: CandleFetcher,  # REQUIRED
    rsi_calculator: Optional[RSICalculator] = None,  # Auto-created
    vwap_calculator: Optional[VWAPCalculator] = None,  # Auto-created
    atr_calculator: Optional[ATRCalculator] = None,  # Auto-created
    funding_fetcher: Optional[FundingRateFetcher] = None,  # Auto-created
    sr_detector: Optional[SRLevelDetector] = None,  # Auto-created
    volume_profile: Optional[VolumeProfileCalculator] = None,  # Auto-created
    orderbook_analyzer: Optional[OrderBookAnalyzer] = None  # Auto-created
):
```

**ContextManager requires:**
```python
def __init__(
    self,
    fear_greed_fetcher: Optional[FearGreedFetcher] = None,  # Auto-created
    btc_tracker: Optional[BTCCorrelationTracker] = None,  # Optional
    news_fetcher: Optional[NewsFeedFetcher] = None,  # Auto-created
    social_fetcher: Optional[SocialSentimentFetcher] = None  # Auto-created
):
```

### Data Flow

```
Bybit REST API
    └── CandleFetcher (OHLCV data)
            ├── RSICalculator
            ├── VWAPCalculator
            ├── ATRCalculator
            ├── SRLevelDetector
            └── VolumeProfileCalculator
    └── FundingRateFetcher (funding rates)
    └── OrderBookAnalyzer (order book depth)

External APIs
    ├── FearGreedFetcher (Alternative.me)
    ├── NewsFeedFetcher (CryptoPanic)
    └── SocialSentimentFetcher (LunarCrush)

MarketFeed (WebSocket)
    └── BTCCorrelationTracker (price stream)
```

---

## 5. LLM Context Budget

### Model Configuration

| Setting | Value | Source |
|---------|-------|--------|
| Model | qwen2.5:14b | src/llm_interface.py:28 |
| API URL | http://{OLLAMA_HOST}:11434/api/chat | src/llm_interface.py:32 |
| Timeout | 120 seconds | src/llm_interface.py:33 |
| num_ctx | NOT SET (model default) | - |

### Context Window Analysis

qwen2.5:14b default context window: **32,768 tokens**

| Component | Estimated Tokens |
|-----------|-----------------|
| Current system prompt | ~350 |
| Current user prompt | ~550 |
| **Current total** | **~900** |
| Phase 3 technical (1 coin) | ~150 |
| Phase 3 technical (20 coins) | ~3,000 |
| Phase 3 market context | ~100 |
| Phase 3 coin context (1 coin) | ~100 |
| Phase 3 coin context (20 coins) | ~2,000 |
| **Phase 3 total (all data)** | **~5,100** |
| **Combined total** | **~6,000** |

**Budget Analysis:**
- Current usage: ~900 tokens (2.7% of context)
- With full Phase 3: ~6,000 tokens (18.3% of context)
- Available headroom: ~26,000 tokens

**Conclusion:** Context window is NOT a constraint. We have significant headroom.

---

## 6. Error Handling

### Current Isolation Strategy

**Strategist loop (src/strategist.py:154-172):**
- Catches all exceptions except CancelledError
- Logs error and waits 30 seconds before retry
- Loop continues - single failure doesn't crash system

**Main loop (src/main.py:449-496):**
- Health checks have individual try/except (implied in component calls)
- Status logging is non-critical

**LLM interface (src/llm_interface.py:87-164):**
- Connection errors: logged, returns None
- Timeouts: retry with exponential backoff (max 3 retries)
- Request errors: retry with backoff
- All failures return None (Strategist handles this gracefully)

### What Happens When Components Fail

| Failure | System Behavior |
|---------|-----------------|
| LLM unavailable | Returns None, no conditions generated, loop continues |
| LLM timeout | Retries 3x with backoff, then returns None |
| Invalid LLM response | Logs warning, returns empty conditions |
| MarketFeed disconnected | Health check warns, continues with stale data |
| Database error | Logged, operation fails gracefully |

### Phase 3 Integration Risk

If Phase 3 modules make HTTP calls inside the Strategist cycle:
- Each call could timeout (10s each)
- Multiple calls could add up to significant latency
- Need to decide: fail fast or graceful degradation?

**Recommendation:** Both managers already implement graceful degradation (return partial data if some sources fail).

---

## 7. Timing

### Current Cycle Durations

| Component | Interval | Notes |
|-----------|----------|-------|
| Main loop tick | 1 second | Health check loop |
| Health check | 30 seconds | Status logging |
| Strategist cycle | **180 seconds (3 min)** | LLM decision generation |
| Snapshot check | 300 seconds | State snapshots |
| Effectiveness check | 3600 seconds | Adaptation review |
| Reflection | 3600 seconds | Deep analysis |

### Async Architecture

- System is fully async (asyncio)
- Components run concurrently via `asyncio.create_task()`
- Strategist runs in its own loop, doesn't block main loop
- MarketFeed runs continuously (WebSocket)

### Time Budget for Phase 3 Data Fetching

Within the 180-second Strategist cycle:
- Current LLM query: ~2-5 seconds
- Remaining budget: ~175 seconds

**If fetching Phase 3 data sequentially:**
- 8 HTTP calls (technical) @ 10s timeout each = 80s worst case
- 3 HTTP calls (sentiment) @ 10s timeout each = 30s worst case
- Total worst case: 110 seconds
- Still within budget, but tight

**Recommendation:** Parallel fetching or caching to reduce latency.

---

## Summary: Integration Readiness

### What's Ready

1. **TechnicalManager and ContextManager exist** with full implementations
2. **`to_prompt()` methods** already format data for LLM
3. **Graceful degradation** built into both managers
4. **Context window** has ample headroom (~26k tokens available)
5. **Error handling** in Strategist loop catches failures

### What Needs to Be Done

1. **Instantiate managers** in TradingSystem.__init__()
2. **Wire CandleFetcher** (required dependency for TechnicalManager)
3. **Call managers** in Strategist._build_context()
4. **Add Phase 3 data** to Strategist._build_prompt()
5. **Handle timing** (parallel fetch or caching)
6. **Update system prompt** to reference new data types

### Key Questions for Integration

1. **Fetch on every cycle or cache?** Technical data changes slowly; could fetch every N cycles
2. **All 20 coins or just candidates?** Full data for 20 coins is ~5k tokens; could fetch only for top candidates
3. **What if external APIs fail?** Both managers degrade gracefully, but should Strategist still generate conditions?
4. **Should LLM be told when data is missing?** "RSI: unavailable" vs just omitting

---

## Files Read (Evidence)

- src/main.py: lines 449-516 (main loop), 212-241 (start)
- src/strategist.py: lines 154-172 (run loop), 174-233 (generate), 268-304 (build_context), 306-358 (get_knowledge), 491-545 (system prompt), 548-636 (build_prompt)
- src/llm_interface.py: lines 1-50 (config), 87-164 (make_request), 166-212 (query)
- src/technical/manager.py: lines 20-156 (TechnicalSnapshot), 158-212 (TechnicalManager init), 214-233 (get_technical_snapshot), 235-308 (get_trade_setup_quality)
- src/sentiment/context_manager.py: lines 16-78 (MarketContext), 81-144 (CoinContext), 146-195 (ContextManager)
