# TASK-123: Strategist ← Knowledge Integration

**Status:** COMPLETED
**Created:** February 3, 2026
**Completed:** February 3, 2026
**Priority:** High
**Depends On:** TASK-120, TASK-121, TASK-122
**Phase:** Phase 2.3 - Knowledge Brain

---

## Objective

Complete the integration between Knowledge Brain components and Strategist, ensuring all accumulated knowledge informs trade condition generation.

---

## Background

Previous tasks created the components:
- **TASK-120**: KnowledgeBrain, CoinScore, TradingPattern, RegimeRule
- **TASK-121**: CoinScorer with position modifiers (integrated)
- **TASK-122**: PatternLibrary with confidence scoring (integrated)

This task completes the integration by:
1. Enhancing prompt context with detailed knowledge
2. Enforcing regime rules before condition generation
3. Combining position modifiers from multiple sources
4. Adding coin performance summaries to prompts
5. Testing the full knowledge flow

---

## Current State

What's already integrated:
- `knowledge.get_good_coins()` → prompt
- `knowledge.get_blacklisted_coins()` → prompt + validation
- `coin_scorer.get_position_modifier()` → validation
- `pattern_library.get_pattern_context()` → prompt

What's missing:
- Regime rules enforcement (rules listed but not enforced)
- Coin performance details in prompts
- Combined position modifiers (coin score + pattern confidence)
- Pattern-specific position adjustments
- Full integration test

---

## Specification

### 1. Enhanced Knowledge Context

Update `_get_knowledge()` to return richer context:

```python
def _get_knowledge(self) -> Dict[str, Any]:
    """Get comprehensive trading knowledge for prompt.

    Returns:
        Knowledge dict with full context for LLM.
    """
    if not self.knowledge:
        return self._get_default_knowledge()

    # Coin performance summaries
    coin_summaries = []
    for score in self.knowledge.get_all_coin_scores()[:10]:
        summary = {
            "coin": score.coin,
            "status": self._get_coin_status_label(score),
            "trades": score.total_trades,
            "win_rate": f"{score.win_rate:.0%}",
            "pnl": f"${score.total_pnl:.2f}",
            "trend": score.trend,
        }
        coin_summaries.append(summary)

    # Active regime rules with descriptions
    active_rules = []
    for rule in self.knowledge.get_active_rules():
        active_rules.append({
            "description": rule.description,
            "action": rule.action,
            "times_triggered": rule.times_triggered,
        })

    return {
        "good_coins": self.knowledge.get_good_coins(),
        "avoid_coins": self.knowledge.get_blacklisted_coins() + self.knowledge.get_bad_coins(),
        "coin_summaries": coin_summaries,
        "active_rules": active_rules,
        "winning_patterns": [p.description for p in self.knowledge.get_winning_patterns()],
        "blacklist_count": len(self.knowledge.get_blacklisted_coins()),
    }
```

### 2. Regime Rules Enforcement

Check regime rules BEFORE generating conditions:

```python
async def generate_conditions(self) -> List[TradeCondition]:
    # ... existing setup ...

    # Check regime rules first
    if self.knowledge:
        market_state = self._get_market_state_for_rules()
        actions = self.knowledge.check_rules(market_state)

        if "NO_TRADE" in actions:
            logger.info("NO_TRADE regime rule triggered - skipping generation")
            self.db.log_activity(
                "strategist",
                "Skipped generation due to regime rule",
                json.dumps({"triggered_rules": actions})
            )
            return []

        # Store active rule actions for position sizing
        self._active_rule_actions = actions
```

### 3. Combined Position Modifiers

Calculate final position size using multiple factors:

```python
def _calculate_final_position_size(
    self,
    base_size: float,
    coin: str,
    pattern_id: Optional[str] = None
) -> float:
    """Calculate final position size with all modifiers.

    Factors:
    - Coin score modifier (0.0 - 1.5)
    - Pattern confidence modifier (0.75 - 1.25)
    - Regime rule modifier (0.5 for REDUCE_SIZE)

    Returns:
        Final position size in USD.
    """
    size = base_size

    # 1. Coin score modifier
    if self.coin_scorer:
        coin_modifier = self.coin_scorer.get_position_modifier(coin)
        if coin_modifier == 0.0:
            return 0.0  # Blacklisted
        size *= coin_modifier

    # 2. Pattern confidence modifier
    if pattern_id and self.pattern_library:
        pattern_modifier = self.pattern_library.get_position_modifier(pattern_id)
        size *= pattern_modifier

    # 3. Regime rule modifier
    if hasattr(self, '_active_rule_actions'):
        if "REDUCE_SIZE" in self._active_rule_actions:
            size *= 0.5

    # Enforce limits
    size = max(DEFAULT_MIN_POSITION_SIZE, min(DEFAULT_MAX_POSITION_SIZE, size))

    return size
```

### 4. Enhanced Prompt Building

Update `_build_prompt()` with detailed knowledge:

```python
def _build_prompt(self, context: Dict[str, Any]) -> str:
    # ... existing code ...

    # Format coin summaries
    coin_summary_text = ""
    if context["knowledge"].get("coin_summaries"):
        lines = []
        for cs in context["knowledge"]["coin_summaries"][:5]:
            lines.append(f"  {cs['coin']}: {cs['status']} | {cs['trades']} trades | "
                        f"{cs['win_rate']} win | {cs['pnl']} P&L | {cs['trend']}")
        coin_summary_text = "\n".join(lines)

    # Format regime rules
    rules_text = "None active"
    if context["knowledge"].get("active_rules"):
        rules = context["knowledge"]["active_rules"]
        rules_text = "\n".join(f"  - {r['description']} → {r['action']}" for r in rules)

    return f"""CURRENT MARKET STATE:
{prices_text}

COIN PERFORMANCE (your track record):
{coin_summary_text if coin_summary_text else "  No history yet"}

COINS TO FAVOR: {', '.join(context['knowledge']['good_coins']) or 'None identified'}
COINS TO AVOID: {', '.join(context['knowledge']['avoid_coins']) or 'None blacklisted'}

ACTIVE REGIME RULES:
{rules_text}
{pattern_section}
ACCOUNT STATE:
...
"""
```

### 5. Market State for Rule Checking

```python
def _get_market_state_for_rules(self) -> Dict[str, Any]:
    """Build market state dict for regime rule checking.

    Returns:
        Dict with conditions that rules can check against.
    """
    state = {}

    # BTC trend and price
    btc_tick = self.market.get_latest_tick("BTC")
    if btc_tick:
        state["btc_price"] = btc_tick.price
        state["btc_change_24h"] = btc_tick.change_24h
        # Determine trend
        if btc_tick.change_24h > 2:
            state["btc_trend"] = "up"
        elif btc_tick.change_24h < -2:
            state["btc_trend"] = "down"
        else:
            state["btc_trend"] = "sideways"

    # Time of day
    from datetime import datetime
    now = datetime.now()
    state["hour_of_day"] = now.hour
    state["day_of_week"] = now.weekday()
    state["is_weekend"] = now.weekday() >= 5

    # Could add: volatility, volume, etc.

    return state
```

---

## Technical Approach

### Step 1: Enhance _get_knowledge()

Update Strategist to return detailed coin summaries and formatted rules.

### Step 2: Add Regime Rule Enforcement

Check rules at start of `generate_conditions()`, skip if NO_TRADE.

### Step 3: Implement Combined Modifiers

Create `_calculate_final_position_size()` method combining all factors.

### Step 4: Update Prompt Format

Enhance prompt with coin performance table and rule status.

### Step 5: Add Market State Builder

Create `_get_market_state_for_rules()` for rule condition checking.

### Step 6: Integration Test

Test full flow: Knowledge → Strategist → Conditions with all modifiers applied.

---

## Files Modified

| File | Change |
|------|--------|
| `src/strategist.py` | Enhanced knowledge context, regime enforcement, combined modifiers |

---

## Files Created

| File | Purpose |
|------|---------|
| `tests/test_knowledge_integration.py` | Full integration tests |

---

## Acceptance Criteria

- [x] Coin summaries (trades, win rate, P&L) in Strategist prompts
- [x] Regime rules checked before generation
- [x] NO_TRADE rule skips condition generation
- [x] REDUCE_SIZE rule halves position sizes
- [x] Position size combines: coin score × pattern confidence × regime
- [x] Blacklisted coins never generate conditions
- [x] Good coins appear in prompt as "favored"
- [x] Full integration test passes

---

## Verification

### Integration Test

```python
from src.strategist import Strategist
from src.knowledge import KnowledgeBrain
from src.coin_scorer import CoinScorer
from src.pattern_library import PatternLibrary
from src.database import Database
from src.market_feed import MarketFeed
from src.llm_interface import LLMInterface

# Setup full stack
db = Database("data/test_integration.db")
brain = KnowledgeBrain(db)
scorer = CoinScorer(brain, db)
patterns = PatternLibrary(brain)

# Add test data
brain.update_coin_score("SOL", {"won": True, "pnl": 5.0})
brain.update_coin_score("SOL", {"won": True, "pnl": 3.0})
brain.blacklist_coin("SHIB", "Poor performance")

# Create strategist
market = MarketFeed(["BTC", "ETH", "SOL"])
llm = LLMInterface()
strategist = Strategist(
    llm=llm,
    market_feed=market,
    knowledge=brain,
    coin_scorer=scorer,
    pattern_library=patterns,
    db=db,
)

# Verify knowledge flows to context
context = strategist._build_context()
assert "SOL" not in context["knowledge"]["avoid_coins"]
assert "SHIB" in context["knowledge"]["avoid_coins"]

# Verify prompt includes knowledge
prompt = strategist._build_prompt(context)
assert "SHIB" in prompt  # In avoid list
assert "COIN PERFORMANCE" in prompt

print("Knowledge integration working!")
```

### Regime Rule Test

```python
# Add NO_TRADE rule
from src.models.knowledge import RegimeRule
rule = RegimeRule(
    rule_id="no_weekend",
    description="No trading on weekends",
    condition={"is_weekend": True},
    action="NO_TRADE",
)
brain.add_rule(rule)

# On weekend, should skip generation
# (Would need to mock datetime for full test)
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         KNOWLEDGE BRAIN                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Coin Scores  │  │  Patterns    │  │ Regime Rules │              │
│  │ (CoinScorer) │  │ (Library)    │  │              │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
└─────────┼─────────────────┼─────────────────┼───────────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          STRATEGIST                                  │
│                                                                     │
│  1. Check regime rules → NO_TRADE? Skip generation                  │
│                                                                     │
│  2. Build context:                                                  │
│     - Coin summaries (trades, win rate, trend)                      │
│     - Good coins / Avoid coins                                      │
│     - Active regime rules                                           │
│     - High-confidence patterns                                      │
│                                                                     │
│  3. Generate conditions via LLM                                     │
│                                                                     │
│  4. Validate & apply modifiers:                                     │
│     - Skip blacklisted coins                                        │
│     - Coin score modifier (0.5x for REDUCED)                        │
│     - Pattern confidence modifier (0.75x - 1.25x)                   │
│     - Regime modifier (0.5x for REDUCE_SIZE)                        │
│                                                                     │
│  5. Emit conditions to Sniper                                       │
└─────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           SNIPER                                     │
│  - Receives conditions with final position sizes                     │
│  - Executes when triggered                                          │
│  - Reports outcomes → CoinScorer → Knowledge Brain                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Position Size Calculation Example

```
Base size: $50

Coin: SOL (FAVORED status, 1.5x modifier)
Pattern: momentum_breakout (0.72 confidence, 1.0x modifier)
Regime: REDUCE_SIZE active (0.5x modifier)

Final = $50 × 1.5 × 1.0 × 0.5 = $37.50

Coin: BTC (REDUCED status, 0.5x modifier)
Pattern: none
Regime: normal

Final = $50 × 0.5 × 1.0 × 1.0 = $25.00
```

---

## Completion Notes

### Implementation Summary

**Date:** February 3, 2026

### Files Modified

| File | Changes |
|------|---------|
| `src/strategist.py` | Enhanced `_get_knowledge()`, added `_get_coin_status_label()`, `_get_market_state_for_rules()`, `_check_regime_rules()`, `_calculate_final_position_size()`, updated `_build_prompt()` and `generate_conditions()` |

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `tests/test_knowledge_integration.py` | ~380 | Full integration tests for knowledge flow |

### Key Implementation Details

1. **Enhanced `_get_knowledge()`**: Now returns comprehensive context including:
   - Coin summaries with status, trades, win rate, P&L, trend
   - Active regime rules with descriptions and actions
   - Good coins, avoid coins, blacklisted coins
   - Winning patterns

2. **Regime Rule Enforcement**: `generate_conditions()` now checks regime rules first:
   - Builds market state with BTC trend, time context
   - Checks rules via `knowledge.check_rules()`
   - Returns empty list if `NO_TRADE` triggered
   - Stores active rule actions for position sizing

3. **Combined Position Modifiers**: `_calculate_final_position_size()` multiplies:
   - Coin score modifier (0.0 for blacklisted, 0.5 for reduced, 1.0 normal, 1.5 favored)
   - Pattern confidence modifier (0.75 - 1.25)
   - Regime rule modifier (0.5 for REDUCE_SIZE)
   - Enforces min ($20) and max ($100) limits

4. **Enhanced Prompt Format**: Now includes:
   - Formatted coin performance table
   - Clear "COINS TO FAVOR" and "COINS TO AVOID" sections
   - Active regime rules with actions
   - High-confidence patterns from PatternLibrary

### Data Flow

```
KnowledgeBrain
├── get_all_coin_scores() → coin_summaries in prompt
├── get_good_coins() → COINS TO FAVOR
├── get_blacklisted_coins() → COINS TO AVOID
├── get_bad_coins() → COINS TO AVOID
├── get_active_rules() → ACTIVE REGIME RULES
├── get_winning_patterns() → WINNING PATTERNS
└── check_rules() → NO_TRADE / REDUCE_SIZE actions

CoinScorer
└── get_position_modifier() → position size adjustment

PatternLibrary
├── get_pattern_context() → HIGH-CONFIDENCE PATTERNS in prompt
└── get_position_modifier() → position size adjustment
```

### Verification

```bash
python3 -c "
# Full integration test
from src.strategist import Strategist
from src.knowledge import KnowledgeBrain
# ... (see tests/test_knowledge_integration.py)
"
# Output: All Knowledge Integration Tests PASSED!
```

---

## Related

- [TASK-120](./TASK-120.md) - Knowledge Brain Data Structures
- [TASK-121](./TASK-121.md) - Coin Scoring System
- [TASK-122](./TASK-122.md) - Pattern Library
- [TASK-130](./TASK-130.md) - Quick Update (writes to Knowledge Brain)
- [AUTONOMOUS-TRADER-SPEC.md](../AUTONOMOUS-TRADER-SPEC.md) - Full system architecture
