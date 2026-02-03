# TASK-151: Learning Validation

**Status:** COMPLETE
**Created:** February 3, 2026
**Completed:** February 3, 2026
**Priority:** High
**Depends On:** TASK-150 (Paper Trading Run)
**Phase:** Phase 2.6 - Validation

---

## Objective

Validate that the autonomous learning loop actually works. Create automated tests and analysis tools that prove the system learns from trades, updates its knowledge, and adapts its behavior based on experience.

---

## Background

The system has components for learning:
- **QuickUpdate** - Updates coin scores after each trade
- **CoinScorer** - Tracks win rate, P&L, trends per coin
- **PatternLibrary** - Tracks pattern confidence and usage
- **ReflectionEngine** - Generates insights from trade analysis
- **AdaptationEngine** - Applies changes (blacklist, favor, rules)
- **Strategist** - Uses Knowledge Brain context for decisions

**What we need to prove:**
1. These components actually modify the Knowledge Brain
2. The modifications are based on real trade outcomes
3. The Strategist actually uses the updated knowledge
4. The adaptations improve (or at least don't hurt) performance

---

## Validation Areas

### 1. Coin Score Updates

**Hypothesis:** Coin scores change appropriately after trades.

| Trade Outcome | Expected Score Change |
|---------------|----------------------|
| Win (profit) | Score increases |
| Loss | Score decreases |
| Big win (>5%) | Larger score increase |
| Big loss (>5%) | Larger score decrease |
| Streak of wins | Trend becomes "improving" |
| Streak of losses | Trend becomes "declining" |

**Validation Tests:**

```python
def test_winning_trade_increases_score():
    """Coin score increases after a winning trade."""
    initial_score = coin_scorer.get_score("BTC")

    # Simulate winning trade
    trade = create_trade(coin="BTC", pnl=50.0, outcome="win")
    quick_update.process_trade(trade)

    final_score = coin_scorer.get_score("BTC")
    assert final_score > initial_score

def test_losing_trade_decreases_score():
    """Coin score decreases after a losing trade."""
    initial_score = coin_scorer.get_score("ETH")

    # Simulate losing trade
    trade = create_trade(coin="ETH", pnl=-30.0, outcome="loss")
    quick_update.process_trade(trade)

    final_score = coin_scorer.get_score("ETH")
    assert final_score < initial_score

def test_score_reflects_win_rate():
    """Coin with higher win rate has higher score."""
    # Simulate 10 trades for COIN_A: 8 wins, 2 losses (80%)
    # Simulate 10 trades for COIN_B: 3 wins, 7 losses (30%)

    score_a = coin_scorer.get_score("COIN_A")
    score_b = coin_scorer.get_score("COIN_B")

    assert score_a > score_b

def test_trend_updates_with_recent_performance():
    """Trend reflects recent trade outcomes."""
    # Simulate 5 consecutive wins
    for i in range(5):
        trade = create_trade(coin="SOL", pnl=20.0, outcome="win")
        quick_update.process_trade(trade)

    coin = knowledge.get_coin("SOL")
    assert coin.trend in ["improving", "up"]
```

### 2. Pattern Confidence Updates

**Hypothesis:** Pattern confidence changes based on usage outcomes.

| Pattern Outcome | Expected Confidence Change |
|-----------------|---------------------------|
| Trade using pattern wins | Confidence increases |
| Trade using pattern loses | Confidence decreases |
| Pattern unused for 7 days | Confidence decays slightly |
| Pattern consistently wins | Becomes "high confidence" |
| Pattern consistently loses | Gets deactivated |

**Validation Tests:**

```python
def test_pattern_confidence_increases_on_win():
    """Pattern confidence increases when trade wins."""
    pattern_id = "momentum_breakout"
    initial_conf = pattern_library.get_confidence(pattern_id)

    # Simulate winning trade using this pattern
    trade = create_trade(pattern=pattern_id, pnl=40.0, outcome="win")
    quick_update.process_trade(trade)

    final_conf = pattern_library.get_confidence(pattern_id)
    assert final_conf > initial_conf

def test_pattern_confidence_decreases_on_loss():
    """Pattern confidence decreases when trade loses."""
    pattern_id = "support_bounce"
    initial_conf = pattern_library.get_confidence(pattern_id)

    # Simulate losing trade using this pattern
    trade = create_trade(pattern=pattern_id, pnl=-25.0, outcome="loss")
    quick_update.process_trade(trade)

    final_conf = pattern_library.get_confidence(pattern_id)
    assert final_conf < initial_conf

def test_failing_pattern_gets_deactivated():
    """Pattern with consistently bad results gets deactivated."""
    pattern_id = "failed_pattern"

    # Simulate 10 losses in a row
    for i in range(10):
        trade = create_trade(pattern=pattern_id, pnl=-20.0, outcome="loss")
        quick_update.process_trade(trade)

    pattern = pattern_library.get_pattern(pattern_id)
    assert pattern.is_active is False or pattern.confidence < 0.3
```

### 3. Adaptation Triggers

**Hypothesis:** Adaptations are triggered based on accumulated evidence.

| Condition | Expected Adaptation |
|-----------|---------------------|
| Coin win rate < 35% over 10+ trades | BLACKLIST coin |
| Coin win rate > 65% over 10+ trades | FAVOR coin |
| Hour consistently loses (< 35% WR) | CREATE_TIME_RULE |
| Pattern win rate < 30% | DEACTIVATE_PATTERN |
| Coin P&L < -$50 | BLACKLIST coin |

**Validation Tests:**

```python
def test_poor_performer_gets_blacklisted():
    """Coin with consistently poor results gets blacklisted."""
    # Simulate 15 trades with 25% win rate
    for i in range(15):
        pnl = 30.0 if i < 4 else -20.0  # 4 wins, 11 losses
        trade = create_trade(coin="DOGE", pnl=pnl)
        quick_update.process_trade(trade)

    # Trigger reflection
    await reflection_engine.reflect()

    # Check blacklist
    assert knowledge.is_blacklisted("DOGE")

def test_good_performer_gets_favored():
    """Coin with consistently good results gets favored."""
    # Simulate 15 trades with 70% win rate
    for i in range(15):
        pnl = 40.0 if i < 11 else -25.0  # 11 wins, 4 losses
        trade = create_trade(coin="SOL", pnl=pnl)
        quick_update.process_trade(trade)

    # Trigger reflection
    await reflection_engine.reflect()

    # Check favor status
    coin = knowledge.get_coin("SOL")
    assert coin.status == "favored" or coin.score > 70

def test_bad_hour_creates_time_rule():
    """Hour with poor performance creates a time rule."""
    # Simulate 10 trades at hour 3 UTC, all losses
    for i in range(10):
        trade = create_trade(
            coin="BTC",
            pnl=-15.0,
            timestamp=make_timestamp(hour=3)
        )
        quick_update.process_trade(trade)

    # Trigger reflection
    await reflection_engine.reflect()

    # Check for time rule
    rules = knowledge.get_rules_for_hour(3)
    assert len(rules) > 0
    assert any(r.action in ["REDUCE_SIZE", "SKIP"] for r in rules)
```

### 4. Strategist Knowledge Usage

**Hypothesis:** Strategist uses Knowledge Brain context in its decisions.

| Knowledge State | Expected Strategist Behavior |
|-----------------|------------------------------|
| Coin blacklisted | Does NOT generate conditions for that coin |
| Coin favored | May prefer conditions for that coin |
| Pattern high confidence | More likely to use that pattern |
| Time rule active | Adjusts position size or skips |

**Validation Tests:**

```python
def test_strategist_avoids_blacklisted_coins():
    """Strategist does not generate conditions for blacklisted coins."""
    # Blacklist DOGE
    knowledge.blacklist_coin("DOGE", "Test blacklist")

    # Generate conditions multiple times
    all_coins = set()
    for _ in range(10):
        conditions = await strategist.generate_conditions()
        for c in conditions:
            all_coins.add(c.coin)

    assert "DOGE" not in all_coins

def test_strategist_includes_favored_coins():
    """Strategist context includes favored coins."""
    # Favor SOL
    coin = knowledge.get_coin("SOL")
    coin.status = "favored"
    knowledge.update_coin(coin)

    # Get context
    context = knowledge.get_context_for_strategist()

    assert "SOL" in context.get("good_coins", [])

def test_strategist_prompt_includes_patterns():
    """Strategist prompt includes active patterns."""
    # Create a pattern
    pattern_library.add_pattern(
        name="test_pattern",
        description="Buy on breakout",
        confidence=0.8
    )

    # Get context
    context = knowledge.get_context_for_strategist()

    assert any("test_pattern" in str(p) for p in context.get("patterns", []))

def test_strategist_respects_time_rules():
    """Strategist context includes active time rules."""
    # Create time rule for current hour
    current_hour = datetime.now().hour
    knowledge.add_rule(
        rule_id=f"time_rule_{current_hour}",
        condition=f"hour == {current_hour}",
        action="REDUCE_SIZE",
        reason="Test rule"
    )

    # Get context
    context = knowledge.get_context_for_strategist()

    assert any(
        str(current_hour) in str(r)
        for r in context.get("regime_rules", [])
    )
```

### 5. End-to-End Learning Loop

**Hypothesis:** The complete loop works: Trade → Learn → Adapt → Better Trade.

```python
async def test_complete_learning_loop():
    """
    Test the full learning loop end-to-end.

    1. Start with neutral knowledge
    2. Execute trades with known outcomes
    3. Verify knowledge updates
    4. Verify adaptations apply
    5. Verify Strategist uses updated knowledge
    """
    # Step 1: Record initial state
    initial_blacklist = set(knowledge.get_blacklist())
    initial_score = coin_scorer.get_score("TEST_COIN") or 50

    # Step 2: Simulate bad trades for TEST_COIN
    for i in range(12):
        trade = create_trade(
            coin="TEST_COIN",
            pnl=-20.0,
            outcome="loss"
        )
        quick_update.process_trade(trade)

    # Step 3: Trigger reflection
    result = await reflection_engine.reflect()

    # Step 4: Verify knowledge updated
    final_score = coin_scorer.get_score("TEST_COIN")
    assert final_score < initial_score, "Score should decrease"

    # Step 5: Verify adaptation applied
    final_blacklist = set(knowledge.get_blacklist())
    assert "TEST_COIN" in final_blacklist, "Should be blacklisted"

    # Step 6: Verify Strategist avoids it
    context = knowledge.get_context_for_strategist()
    assert "TEST_COIN" in context.get("blacklist", [])
```

---

## Metrics to Track

### Learning Velocity

| Metric | Definition | Target |
|--------|------------|--------|
| Score update rate | Scores updated / Trades executed | 100% |
| Pattern update rate | Patterns updated / Trades with pattern | 100% |
| Insight generation rate | Insights / Reflections | > 0.5 |
| Adaptation application rate | Adaptations applied / Insights | > 0.3 |

### Learning Accuracy

| Metric | Definition | Target |
|--------|------------|--------|
| Score correlation | Correlation(score, actual_performance) | > 0.5 |
| Blacklist accuracy | Bad coins blacklisted / Total bad coins | > 80% |
| False positive rate | Good coins wrongly blacklisted | < 10% |

### Knowledge Growth

| Metric | Definition | Target |
|--------|------------|--------|
| Coins with data | Coins with > 5 trades | Growing |
| Active patterns | Patterns with confidence > 0.5 | > 3 |
| Active rules | Regime rules applied > 0 times | > 1 |

---

## Validation Script

Create a script that runs all validation tests and reports results:

```python
# scripts/validate_learning.py

def validate_learning():
    """Run all learning validation tests."""
    results = {
        "coin_scores": validate_coin_scores(),
        "pattern_confidence": validate_patterns(),
        "adaptation_triggers": validate_adaptations(),
        "strategist_usage": validate_strategist(),
        "end_to_end": validate_full_loop(),
    }

    print("=" * 60)
    print("LEARNING VALIDATION RESULTS")
    print("=" * 60)

    all_passed = True
    for category, tests in results.items():
        passed = sum(1 for t in tests if t["passed"])
        total = len(tests)
        status = "PASS" if passed == total else "FAIL"
        print(f"\n{category}: {passed}/{total} {status}")

        for test in tests:
            icon = "✓" if test["passed"] else "✗"
            print(f"  {icon} {test['name']}")
            if not test["passed"]:
                print(f"    Reason: {test['reason']}")
                all_passed = False

    print("\n" + "=" * 60)
    print(f"OVERALL: {'PASS' if all_passed else 'FAIL'}")
    print("=" * 60)

    return all_passed
```

---

## Technical Approach

### Step 1: Create Test Fixtures

Create helper functions for simulating trades with controlled outcomes.

```python
# tests/fixtures/learning_fixtures.py

def create_trade(
    coin: str,
    pnl: float,
    outcome: str = None,
    pattern: str = None,
    timestamp: datetime = None
) -> dict:
    """Create a trade record for testing."""

def make_timestamp(hour: int, days_ago: int = 0) -> datetime:
    """Create a timestamp at specific hour."""
```

### Step 2: Create Unit Tests

Add tests to existing test files:
- `tests/test_coin_scorer.py` - Score update tests
- `tests/test_pattern_library.py` - Confidence update tests
- `tests/test_adaptation.py` - Adaptation trigger tests
- `tests/test_knowledge_integration.py` - Strategist usage tests

### Step 3: Create Integration Tests

Add to `tests/test_learning_validation.py`:
- End-to-end loop tests
- Multi-day simulation tests
- Regression tests

### Step 4: Create Validation Script

`scripts/validate_learning.py` - Runs against live system to verify learning.

### Step 5: Create Analysis Tools

`scripts/analyze_learning.py` - Analyzes historical data to measure learning effectiveness.

---

## Files to Create

| File | Purpose |
|------|---------|
| `tests/test_learning_validation.py` | Comprehensive learning validation tests |
| `tests/fixtures/learning_fixtures.py` | Test helpers for simulating trades |
| `scripts/validate_learning.py` | Live system learning validation |
| `scripts/analyze_learning.py` | Historical learning analysis |

---

## Files to Modify

| File | Change |
|------|--------|
| `tests/test_coin_scorer.py` | Add score update validation tests |
| `tests/test_pattern_library.py` | Add confidence update tests |
| `tests/test_adaptation.py` | Add trigger validation tests |

---

## Acceptance Criteria

- [x] All coin score update tests pass (5/5)
- [x] All pattern confidence update tests pass (4/4)
- [x] All adaptation trigger tests pass (4/4)
- [x] All Strategist knowledge usage tests pass (4/4)
- [x] End-to-end learning loop tests pass (4/4)
- [x] Learning metrics tests pass (3/3)
- [x] Validation script (`scripts/validate_learning.py`) runs successfully
- [x] Analysis script (`scripts/analyze_learning.py`) created
- [x] Test fixtures (`tests/fixtures/learning_fixtures.py`) created

---

## Verification

### Run Validation Tests

```bash
# Run all learning validation tests
python -m pytest tests/test_learning_validation.py -v

# Run with coverage
python -m pytest tests/test_learning_validation.py -v --cov=src
```

### Run Live Validation

```bash
# Against running system
python scripts/validate_learning.py

# Analyze historical data
python scripts/analyze_learning.py --days 7
```

### Expected Output

```
LEARNING VALIDATION RESULTS
============================================================

coin_scores: 5/5 PASS
  ✓ test_winning_trade_increases_score
  ✓ test_losing_trade_decreases_score
  ✓ test_score_reflects_win_rate
  ✓ test_trend_updates_with_recent_performance
  ✓ test_score_persists_across_restart

pattern_confidence: 4/4 PASS
  ✓ test_pattern_confidence_increases_on_win
  ✓ test_pattern_confidence_decreases_on_loss
  ✓ test_failing_pattern_gets_deactivated
  ✓ test_pattern_usage_tracked

adaptation_triggers: 3/3 PASS
  ✓ test_poor_performer_gets_blacklisted
  ✓ test_good_performer_gets_favored
  ✓ test_bad_hour_creates_time_rule

strategist_usage: 4/4 PASS
  ✓ test_strategist_avoids_blacklisted_coins
  ✓ test_strategist_includes_favored_coins
  ✓ test_strategist_prompt_includes_patterns
  ✓ test_strategist_respects_time_rules

end_to_end: 1/1 PASS
  ✓ test_complete_learning_loop

============================================================
OVERALL: PASS
============================================================
```

---

## Related

- [TASK-130](./TASK-130.md) - Quick Update (Post-Trade)
- [TASK-121](./TASK-121.md) - Coin Scoring System
- [TASK-122](./TASK-122.md) - Pattern Library
- [TASK-131](./TASK-131.md) - Deep Reflection
- [TASK-133](./TASK-133.md) - Adaptation Application
- [TASK-150](./TASK-150.md) - Paper Trading Run
- [TASK-152](./TASK-152.md) - Performance Analysis
