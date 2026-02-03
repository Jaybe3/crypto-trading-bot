# Testing Guide

**Last Updated:** February 3, 2026
**Phase:** 2 Complete

Guide for testing the trading bot codebase.

---

## Test Structure

```
tests/
├── test_integration.py      # Full system integration tests
├── test_coin_scorer.py      # CoinScorer unit tests
├── test_pattern_library.py  # PatternLibrary unit tests
├── test_knowledge.py        # KnowledgeBrain unit tests
├── test_quick_update.py     # QuickUpdate unit tests
├── test_reflection.py       # ReflectionEngine unit tests
├── test_adaptation.py       # AdaptationEngine unit tests
├── test_analysis.py         # Analysis module tests
└── test_knowledge_integration.py  # Learning system integration
```

---

## Running Tests

### All Tests

```bash
pytest tests/ -v
```

### Specific Test File

```bash
pytest tests/test_coin_scorer.py -v
```

### Specific Test

```bash
pytest tests/test_coin_scorer.py::test_blacklist_threshold -v
```

### With Coverage

```bash
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

### Watch Mode (during development)

```bash
pip install pytest-watch
ptw tests/
```

---

## Test Categories

### Unit Tests

Test individual components in isolation.

**Characteristics:**
- Mock all dependencies
- Fast execution (<1 second each)
- Test one behavior per test

**Example:**

```python
# tests/test_coin_scorer.py
import pytest
from unittest.mock import Mock
from src.coin_scorer import CoinScorer, CoinStatus
from src.models.quick_update import TradeResult

class TestCoinScorer:

    def setup_method(self):
        """Setup for each test"""
        self.mock_brain = Mock()
        self.mock_db = Mock()
        self.scorer = CoinScorer(self.mock_brain, self.mock_db)

    def test_new_coin_is_unknown(self):
        """New coins should have UNKNOWN status"""
        status = self.scorer.get_coin_status("NEW_COIN")
        assert status == CoinStatus.UNKNOWN

    def test_blacklist_after_losses(self):
        """Coin should be blacklisted after 5 losses with < 30% win rate"""
        # Create 5 losing trades
        for i in range(5):
            trade = TradeResult(
                trade_id=f"trade_{i}",
                coin="DOGE",
                direction="LONG",
                entry_price=0.10,
                exit_price=0.09,
                position_size_usd=100.0,
                pnl_usd=-10.0,
                won=False,
                exit_reason="stop_loss"
            )
            self.scorer.process_trade_result(trade)

        status = self.scorer.get_coin_status("DOGE")
        assert status == CoinStatus.BLACKLISTED
```

### Integration Tests

Test multiple components working together.

**Characteristics:**
- Use real components (not mocks)
- May use in-memory database
- Test data flow across components

**Example:**

```python
# tests/test_knowledge_integration.py
import pytest
from src.database import Database
from src.knowledge import KnowledgeBrain
from src.coin_scorer import CoinScorer
from src.quick_update import QuickUpdate
from src.pattern_library import PatternLibrary

class TestLearningIntegration:

    def setup_method(self):
        """Setup real components with in-memory DB"""
        self.db = Database(":memory:")
        self.brain = KnowledgeBrain(self.db)
        self.scorer = CoinScorer(self.brain, self.db)
        self.library = PatternLibrary(self.brain)
        self.quick = QuickUpdate(self.scorer, self.library, self.db)

    def test_trade_updates_coin_score(self):
        """Trade close should update coin score in knowledge"""
        # Process winning trade
        trade = create_trade_result(coin="BTC", won=True, pnl=50.0)
        self.quick.process_trade_close(trade)

        # Verify coin score updated
        score = self.brain.get_coin_score("BTC")
        assert score.total_trades == 1
        assert score.wins == 1
        assert score.total_pnl == 50.0
```

### Async Tests

For components that use async/await.

```python
import pytest

@pytest.mark.asyncio
async def test_strategist_generates_conditions():
    """Strategist should generate valid conditions"""
    mock_llm = AsyncMock()
    mock_llm.generate_json.return_value = {
        "conditions": [
            {"coin": "BTC", "direction": "LONG", "entry": 45000, ...}
        ]
    }

    brain = Mock()
    brain.get_knowledge_context.return_value = {...}

    strategist = Strategist(mock_llm, brain)
    conditions = await strategist.generate_conditions(market_state)

    assert len(conditions) >= 1
    assert conditions[0].coin == "BTC"
```

---

## Test Fixtures

### Common Fixtures

```python
# tests/conftest.py
import pytest
from src.database import Database
from src.knowledge import KnowledgeBrain

@pytest.fixture
def db():
    """In-memory database for tests"""
    return Database(":memory:")

@pytest.fixture
def brain(db):
    """KnowledgeBrain with fresh database"""
    return KnowledgeBrain(db)

@pytest.fixture
def sample_trade():
    """Sample TradeResult for testing"""
    return TradeResult(
        trade_id="test_001",
        coin="BTC",
        direction="LONG",
        entry_price=45000.0,
        exit_price=45500.0,
        position_size_usd=100.0,
        pnl_usd=1.11,
        won=True,
        exit_reason="take_profit"
    )
```

### Factory Functions

```python
# tests/factories.py
def create_trade_result(
    trade_id: str = None,
    coin: str = "BTC",
    won: bool = True,
    pnl: float = 10.0,
    **kwargs
) -> TradeResult:
    """Factory for creating TradeResult objects"""
    return TradeResult(
        trade_id=trade_id or f"trade_{uuid.uuid4().hex[:8]}",
        coin=coin,
        direction=kwargs.get("direction", "LONG"),
        entry_price=kwargs.get("entry_price", 100.0),
        exit_price=kwargs.get("exit_price", 110.0 if won else 90.0),
        position_size_usd=kwargs.get("position_size_usd", 100.0),
        pnl_usd=pnl,
        won=won,
        exit_reason=kwargs.get("exit_reason", "take_profit" if won else "stop_loss"),
        pattern_id=kwargs.get("pattern_id")
    )

def create_mock_trade(
    coin: str = "BTC",
    won: bool = True,
    pnl: float = 10.0
) -> Mock:
    """Create mock trade object for testing"""
    trade = Mock()
    trade.coin = coin
    trade.won = won
    trade.pnl_usd = pnl
    trade.direction = "LONG"
    trade.exit_reason = "take_profit" if won else "stop_loss"
    return trade
```

---

## Mocking Strategies

### Mock LLM Interface

```python
from unittest.mock import Mock, AsyncMock

def create_mock_llm():
    """Create mock LLM that returns predictable responses"""
    llm = Mock()
    llm.generate_json = AsyncMock(return_value={
        "conditions": [
            {
                "coin": "BTC",
                "direction": "LONG",
                "entry_price": 45000,
                "stop_loss": 44000,
                "take_profit": 46000,
                "position_size_usd": 100
            }
        ]
    })
    llm.is_available.return_value = True
    return llm
```

### Mock Database

```python
def create_mock_db():
    """Create mock database with in-memory state"""
    db = Mock()
    db._trades = []
    db._coin_scores = {}

    def save_trade(trade_dict):
        db._trades.append(trade_dict)

    def get_coin_score(coin):
        return db._coin_scores.get(coin)

    db.save_trade = save_trade
    db.get_coin_score = get_coin_score
    return db
```

### Mock Market Feed

```python
def create_mock_feed(prices: dict = None):
    """Create mock market feed with preset prices"""
    feed = Mock()
    feed._prices = prices or {"BTC": 45000, "ETH": 2500}

    feed.get_price = lambda coin: feed._prices.get(coin)
    feed.get_market_state = lambda: {
        "prices": feed._prices,
        "changes_24h": {k: 0.0 for k in feed._prices},
        "btc_trend": "up"
    }
    return feed
```

---

## Testing Patterns

### Test Coin Status Transitions

```python
class TestCoinStatusTransitions:
    """Test all possible coin status transitions"""

    def test_unknown_to_normal(self, scorer):
        """After trades, unknown becomes normal"""
        for i in range(5):
            trade = create_trade_result(coin="NEW", won=i % 2 == 0)
            scorer.process_trade_result(trade)

        status = scorer.get_coin_status("NEW")
        assert status in [CoinStatus.NORMAL, CoinStatus.REDUCED]

    def test_normal_to_blacklisted(self, scorer):
        """Heavy losses should blacklist"""
        for i in range(5):
            trade = create_trade_result(coin="BAD", won=False, pnl=-20)
            scorer.process_trade_result(trade)

        assert scorer.get_coin_status("BAD") == CoinStatus.BLACKLISTED

    def test_normal_to_favored(self, scorer):
        """Consistent wins should favor"""
        for i in range(5):
            trade = create_trade_result(coin="GOOD", won=True, pnl=20)
            scorer.process_trade_result(trade)

        assert scorer.get_coin_status("GOOD") == CoinStatus.FAVORED
```

### Test Pattern Confidence

```python
class TestPatternConfidence:
    """Test pattern confidence calculations"""

    def test_confidence_increases_on_win(self, library):
        pattern_id = library.create_pattern("test", "desc", {}, {})
        initial = library.get_pattern(pattern_id).confidence

        library.record_pattern_outcome(pattern_id, won=True, pnl=10)

        assert library.get_pattern(pattern_id).confidence > initial

    def test_confidence_decreases_on_loss(self, library):
        pattern_id = library.create_pattern("test", "desc", {}, {})

        # First give it some wins to have confidence > 0.5
        for _ in range(3):
            library.record_pattern_outcome(pattern_id, won=True, pnl=10)

        initial = library.get_pattern(pattern_id).confidence
        library.record_pattern_outcome(pattern_id, won=False, pnl=-10)

        assert library.get_pattern(pattern_id).confidence < initial

    def test_pattern_deactivates_at_low_confidence(self, library):
        pattern_id = library.create_pattern("test", "desc", {}, {})

        # Many losses
        for _ in range(10):
            library.record_pattern_outcome(pattern_id, won=False, pnl=-10)

        assert not library.get_pattern(pattern_id).is_active
```

### Test Adaptation Effectiveness

```python
class TestAdaptationEffectiveness:
    """Test adaptation tracking"""

    def test_blacklist_prevents_trading(self, engine, scorer):
        # Blacklist coin
        engine.apply_adaptation(Adaptation(
            action="BLACKLIST",
            target="DOGE",
            reason="test"
        ))

        # Verify modifier is 0
        modifier = scorer.get_position_modifier("DOGE")
        assert modifier == 0.0

    def test_effectiveness_measured(self, engine, db):
        # Apply adaptation
        adaptation = engine.apply_adaptation(...)

        # Simulate trades
        for _ in range(10):
            db.save_trade(create_trade())

        # Measure effectiveness
        engine.measure_effectiveness(adaptation.adaptation_id)

        record = db.get_adaptation(adaptation.adaptation_id)
        assert record.effectiveness_rating != "pending"
```

---

## Analysis Module Tests

```python
# tests/test_analysis.py
from src.analysis.metrics import calculate_metrics, calculate_sharpe_ratio
from src.analysis.performance import analyze_by_coin, analyze_by_hour
from src.analysis.learning import analyze_coin_score_accuracy

class TestMetrics:

    def test_win_rate_calculation(self):
        trades = [
            {"pnl_usd": 10, "won": True},
            {"pnl_usd": -5, "won": False},
            {"pnl_usd": 15, "won": True},
        ]
        metrics = calculate_metrics(trades)
        assert metrics.win_rate == pytest.approx(0.667, rel=0.01)

    def test_profit_factor(self):
        trades = [
            {"pnl_usd": 100, "won": True},
            {"pnl_usd": -50, "won": False},
        ]
        metrics = calculate_metrics(trades)
        assert metrics.profit_factor == 2.0

class TestPerformanceAnalysis:

    def test_analyze_by_coin(self):
        trades = [
            {"coin": "BTC", "pnl_usd": 10},
            {"coin": "BTC", "pnl_usd": 20},
            {"coin": "ETH", "pnl_usd": -5},
        ]
        by_coin = analyze_by_coin(trades)
        assert by_coin["BTC"].total_pnl == 30
        assert by_coin["ETH"].total_pnl == -5
```

---

## Test Data

### Sample Trade Data

```python
SAMPLE_TRADES = [
    {
        "trade_id": "t001",
        "coin": "BTC",
        "direction": "LONG",
        "entry_price": 45000,
        "exit_price": 45500,
        "position_size_usd": 100,
        "pnl_usd": 1.11,
        "won": True,
        "exit_reason": "take_profit"
    },
    # ... more trades
]
```

### Test Database Seed

```python
def seed_test_db(db):
    """Seed database with test data"""
    # Add coin scores
    for coin in ["BTC", "ETH", "SOL"]:
        db.update_coin_score(coin, {
            "total_trades": 10,
            "wins": 6,
            "win_rate": 0.6,
            "total_pnl": 100
        })

    # Add patterns
    db.save_pattern({
        "pattern_id": "pattern_001",
        "description": "Test pattern",
        "confidence": 0.7,
        "is_active": True
    })
```

---

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov=src
```

---

## Related Documentation

- [COMPONENT-GUIDE.md](./COMPONENT-GUIDE.md) - Component details
- [ADDING-FEATURES.md](./ADDING-FEATURES.md) - Adding new features
- [../architecture/DATA-MODEL.md](../architecture/DATA-MODEL.md) - Database schema
