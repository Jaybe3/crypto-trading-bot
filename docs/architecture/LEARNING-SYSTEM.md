# Learning System Architecture

**Last Updated:** February 3, 2026
**Phase:** 2 Complete

---

## Overview

The learning system enables the trading bot to improve its performance over time by:
1. Tracking outcomes of every trade
2. Updating knowledge immediately after each trade (Quick Update)
3. Performing deep analysis periodically (Reflection)
4. Applying changes based on accumulated evidence (Adaptation)

---

## Learning Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                      LEARNING LOOP                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Trade Closes                                                   │
│        │                                                         │
│        ▼                                                         │
│   ┌─────────────────┐                                           │
│   │   QUICK UPDATE  │  ← Instant (< 10ms)                       │
│   │   - Coin score  │                                           │
│   │   - Pattern     │                                           │
│   │     confidence  │                                           │
│   │   - Threshold   │                                           │
│   │     checks      │                                           │
│   └────────┬────────┘                                           │
│            │                                                     │
│            ▼                                                     │
│   ┌─────────────────┐                                           │
│   │ DEEP REFLECTION │  ← Hourly (LLM-powered)                   │
│   │   - Trade       │                                           │
│   │     analysis    │                                           │
│   │   - Pattern     │                                           │
│   │     detection   │                                           │
│   │   - Insight     │                                           │
│   │     generation  │                                           │
│   └────────┬────────┘                                           │
│            │                                                     │
│            ▼                                                     │
│   ┌─────────────────┐                                           │
│   │   ADAPTATION    │  ← Apply changes                          │
│   │   - Blacklist   │                                           │
│   │   - Favor       │                                           │
│   │   - Rules       │                                           │
│   │   - Patterns    │                                           │
│   └────────┬────────┘                                           │
│            │                                                     │
│            ▼                                                     │
│   ┌─────────────────┐                                           │
│   │ KNOWLEDGE BRAIN │  ← Updated knowledge                      │
│   │   used by       │                                           │
│   │   Strategist    │                                           │
│   └─────────────────┘                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tier 1: Quick Update

**File:** `src/quick_update.py`
**Trigger:** Every trade close
**Latency:** < 10ms (no LLM)

### Purpose
Provide immediate feedback to the knowledge system. Pure math calculations, no AI involved.

### What It Updates

#### 1. Coin Scores
```python
# After each trade:
coin_score.total_trades += 1
coin_score.wins += 1 if won else 0
coin_score.losses += 1 if not won else 0
coin_score.total_pnl += pnl_usd
coin_score.win_rate = wins / total_trades
coin_score.trend = calculate_trend(recent_results)
```

#### 2. Pattern Confidence
```python
# If trade used a pattern:
pattern.times_used += 1
pattern.wins += 1 if won else 0
pattern.total_pnl += pnl_usd
pattern.confidence = calculate_confidence(pattern)
```

#### 3. Threshold Checks
```python
# Automatic adaptations when thresholds crossed:
if coin.win_rate < 0.30 and coin.total_pnl < 0:
    trigger_adaptation("BLACKLIST", coin)
elif coin.win_rate < 0.45:
    trigger_adaptation("REDUCE", coin)
elif coin.win_rate > 0.60 and coin.total_pnl > 0:
    trigger_adaptation("FAVOR", coin)
```

### Coin Status Levels

| Status | Win Rate | P&L | Position Modifier |
|--------|----------|-----|-------------------|
| BLACKLISTED | < 30% | < 0 | 0% (no trading) |
| REDUCED | < 45% | any | 50% size |
| NORMAL | 45-60% | any | 100% size |
| FAVORED | > 60% | > 0 | 150% size |
| UNKNOWN | < 5 trades | - | 100% size |

---

## Tier 2: Deep Reflection

**File:** `src/reflection.py`
**Trigger:** Hourly (or after N trades)
**Latency:** 1-5 minutes (LLM analysis)

### Purpose
Use AI to identify patterns, problems, and opportunities that simple math can't detect.

### Process

```
1. Gather Data
   └── Recent trades (last hour/day)
   └── Current coin scores
   └── Pattern performance
   └── Market context

2. LLM Analysis
   └── Prompt with trade data
   └── Ask for patterns, problems, suggestions
   └── Parse structured response

3. Generate Insights
   └── Coin insights (good/bad performers)
   └── Pattern insights (what's working)
   └── Time insights (bad hours)
   └── Regime insights (market conditions)

4. Queue Adaptations
   └── Convert insights to actionable changes
   └── Pass to AdaptationEngine
```

### Insight Types

| Type | Example | Possible Action |
|------|---------|-----------------|
| `coin` | "DOGE has 25% win rate over 15 trades" | BLACKLIST |
| `pattern` | "Breakout pattern failing in low volatility" | DEACTIVATE |
| `time` | "Hour 3-4 UTC has 20% win rate" | CREATE_TIME_RULE |
| `regime` | "BTC volatility < 1% correlates with losses" | CREATE_REGIME_RULE |
| `exit` | "Stop losses too tight, getting stopped out" | ADJUST_PARAMETERS |

### LLM Prompt Structure

```
You are analyzing trading performance. Here is the recent data:

TRADES (last 24 hours):
- BTC LONG: +$45 (win)
- ETH SHORT: -$30 (loss)
...

COIN PERFORMANCE:
- SOL: 70% win rate, +$120 total
- DOGE: 25% win rate, -$80 total
...

PATTERNS:
- breakout_001: 60% win rate, confidence 0.7
- support_bounce: 35% win rate, confidence 0.4
...

Analyze this data and identify:
1. Coins that should be blacklisted or favored
2. Patterns that are working or failing
3. Time-based patterns (specific hours performing poorly)
4. Any other insights for improvement

Respond in JSON format...
```

---

## Tier 3: Adaptation Engine

**File:** `src/adaptation.py`
**Trigger:** After reflection, or threshold crossings
**Purpose:** Apply changes to the knowledge system

### Adaptation Types

| Action | Target | Effect |
|--------|--------|--------|
| `BLACKLIST` | Coin | Prevent trading this coin |
| `UNBLACKLIST` | Coin | Re-enable trading |
| `FAVOR` | Coin | Increase position size |
| `REDUCE` | Coin | Decrease position size |
| `CREATE_RULE` | Regime | Add time/condition rule |
| `DEACTIVATE_PATTERN` | Pattern | Stop using pattern |
| `ACTIVATE_PATTERN` | Pattern | Resume using pattern |
| `ADJUST_PARAMS` | Various | Modify thresholds |

### Adaptation Record

Every adaptation is logged with:
```python
AdaptationRecord(
    adaptation_id="adapt_001",
    action="BLACKLIST",
    target="DOGE",
    reason="25% win rate over 15 trades",
    confidence=0.85,

    # Before metrics (for measuring effectiveness)
    win_rate_before=0.25,
    pnl_before=-80.0,

    # After metrics (filled in later)
    win_rate_after=None,  # Measured after 10 trades
    pnl_after=None,
    effectiveness_rating=None,  # "effective", "neutral", "harmful"
)
```

### Effectiveness Measurement

After an adaptation is applied, we measure its impact:

```python
# 10 trades later:
def measure_effectiveness(adaptation):
    if adaptation.action == "BLACKLIST":
        # Did we avoid losses?
        hypothetical_loss = estimate_if_we_traded(coin)
        return "effective" if hypothetical_loss < 0 else "neutral"

    elif adaptation.action == "FAVOR":
        # Did the coin continue performing well?
        actual_pnl = get_pnl_since(adaptation)
        return "effective" if actual_pnl > 0 else "harmful"
```

---

## Knowledge Brain

**File:** `src/knowledge.py`
**Purpose:** Central repository for all learned knowledge

### Data Structures

```python
KnowledgeBrain:
    # Coin performance
    coin_scores: Dict[str, CoinScore]

    # Trading patterns
    patterns: Dict[str, TradingPattern]

    # Regime rules
    rules: Dict[str, RegimeRule]

    # Blacklist
    blacklisted_coins: Set[str]

    # Methods
    get_knowledge_context() -> dict  # For Strategist
    get_coin_score(coin) -> CoinScore
    get_active_patterns() -> List[TradingPattern]
    get_applicable_rules(market_state) -> List[RegimeRule]
```

### Knowledge Context (for Strategist)

```python
{
    "coin_summaries": {
        "SOL": "70% win rate, trending up, FAVORED",
        "DOGE": "BLACKLISTED - poor performance",
        ...
    },
    "blacklist": ["DOGE", "SHIB"],
    "good_coins": ["SOL", "BTC"],
    "patterns": [
        {"id": "breakout_001", "confidence": 0.8, "description": "..."},
        ...
    ],
    "regime_rules": [
        {"condition": "hour in [2,3,4]", "action": "REDUCE_SIZE"},
        ...
    ],
    "recent_performance": {
        "win_rate": 58.3,
        "profit_factor": 1.45,
        ...
    }
}
```

---

## Learning Metrics

### Tracked Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| Score Update Rate | Scores updated / Trades | 100% |
| Insight Rate | Insights / Reflections | > 0.5 |
| Adaptation Rate | Adaptations / Insights | > 0.3 |
| Effectiveness Rate | Effective adaptations / Total | > 50% |
| Harmful Rate | Harmful adaptations / Total | < 20% |

### Validation Approach

1. **Coin Score Accuracy**: Do high scores correlate with high win rates?
2. **Pattern Confidence**: Do high-confidence patterns win more?
3. **Adaptation Effectiveness**: Do adaptations improve performance?
4. **Improvement Over Time**: Is second half better than first half?

---

## Configuration

### Thresholds (coin_scorer.py)

```python
MIN_TRADES_FOR_ADAPTATION = 5
BLACKLIST_WIN_RATE = 0.30
REDUCED_WIN_RATE = 0.45
FAVORED_WIN_RATE = 0.60
RECOVERY_WIN_RATE = 0.50
```

### Reflection Settings

```python
REFLECTION_INTERVAL_HOURS = 1
MIN_TRADES_FOR_REFLECTION = 5
INSIGHT_CONFIDENCE_THRESHOLD = 0.6
```

### Adaptation Settings

```python
MIN_CONFIDENCE_TO_APPLY = 0.5
TRADES_BEFORE_EFFECTIVENESS_CHECK = 10
ROLLBACK_IF_HARMFUL = True
```

---

## Related Documentation

- [SYSTEM-OVERVIEW.md](./SYSTEM-OVERVIEW.md) - Overall architecture
- [DATA-MODEL.md](./DATA-MODEL.md) - Database schema
- [../development/COMPONENT-GUIDE.md](../development/COMPONENT-GUIDE.md) - Component details
