# TASK-014: Multi-Tier Coin Universe

## Overview
Expand the trading bot from 3 coins to 40-50 coins organized into three tiers with different risk profiles and trading strategies.

## Current State
- 3 coins: bitcoin, ethereum, ripple
- Single risk profile for all coins
- Individual API calls per coin
- No tier-based strategy differentiation

## Target State
- 45 coins across 3 tiers
- Tier-specific position sizing and risk limits
- Batched API calls (1 call for all coins)
- Tier metadata stored for decision-making

---

## Tier Definitions

### Tier 1: Blue Chips (5 coins)
Large cap, high liquidity, lower volatility. Conservative approach.

| CoinGecko ID | Symbol | Notes |
|--------------|--------|-------|
| bitcoin | BTC | Market leader |
| ethereum | ETH | DeFi backbone |
| binancecoin | BNB | Exchange token |
| ripple | XRP | Payments focus |
| solana | SOL | High-performance L1 |

**Risk Profile:**
- Max position size: 25% of balance
- Stop-loss: 3%
- Take-profit: 5%
- Max concurrent: 2 positions

### Tier 2: Established Altcoins (15 coins)
Mid-cap, proven projects, moderate volatility. Balanced approach.

| CoinGecko ID | Symbol | Notes |
|--------------|--------|-------|
| cardano | ADA | Smart contracts |
| dogecoin | DOGE | Meme origin, large cap |
| avalanche-2 | AVAX | L1 competitor |
| polkadot | DOT | Interoperability |
| chainlink | LINK | Oracle network |
| polygon-ecosystem-token | POL | L2 scaling |
| tron | TRX | High throughput |
| the-open-network | TON | Telegram ecosystem |
| shiba-inu | SHIB | Meme, large community |
| litecoin | LTC | Bitcoin fork |
| uniswap | UNI | DEX governance |
| bitcoin-cash | BCH | Bitcoin fork |
| stellar | XLM | Payments |
| near | NEAR | L1 platform |
| aptos | APT | New L1 |

**Risk Profile:**
- Max position size: 15% of balance
- Stop-loss: 5%
- Take-profit: 8%
- Max concurrent: 3 positions

### Tier 3: High Volatility / Emerging (25 coins)
Smaller cap, higher risk/reward, meme coins. Aggressive approach.

| CoinGecko ID | Symbol | Notes |
|--------------|--------|-------|
| pepe | PEPE | Meme coin |
| floki | FLOKI | Meme coin |
| bonk | BONK | Solana meme |
| dogwifcoin | WIF | Solana meme |
| brett | BRETT | Base meme |
| render-token | RNDR | AI/GPU |
| injective-protocol | INJ | DeFi |
| sei-network | SEI | Trading L1 |
| sui | SUI | New L1 |
| celestia | TIA | Modular blockchain |
| jupiter-exchange-solana | JUP | Solana DEX |
| starknet | STRK | L2 |
| worldcoin-wld | WLD | Identity |
| arbitrum | ARB | L2 |
| optimism | OP | L2 |
| immutable-x | IMX | Gaming |
| gala | GALA | Gaming |
| the-sandbox | SAND | Metaverse |
| axie-infinity | AXS | Gaming |
| ondo-finance | ONDO | RWA |
| fetch-ai | FET | AI |
| kaspa | KAS | PoW |
| cosmos | ATOM | Interchain |
| algorand | ALGO | L1 |
| hedera-hashgraph | HBAR | Enterprise |

**Risk Profile:**
- Max position size: 10% of balance
- Stop-loss: 7%
- Take-profit: ~$1 (same as other tiers)
- Max concurrent: 3 positions

---

## Liquidity & Volume Filters

### Minimum 24h Volume Requirements
To avoid illiquid or dead coins, we filter by 24-hour trading volume:

| Tier | Minimum 24h Volume | Rationale |
|------|-------------------|-----------|
| Tier 1 | $100,000,000 | Blue chips always liquid |
| Tier 2 | $10,000,000 | Established projects |
| Tier 3 | $1,000,000 | Filters dead meme coins |

### Implementation
- Fetch volume data in batch API call
- Skip coins below volume threshold
- Log skipped coins for visibility
- Re-check volume each cycle (can change rapidly for memes)

### Take-Profit Strategy (Updated)
Instead of percentage-based take-profit that varies by tier, we use **consistent $1 profit target** across all tiers:
- Easier to hit on smaller positions
- Accumulates small wins consistently
- Stop-loss still varies by tier (accounts for volatility)

---

## Implementation

### 1. Create Coin Configuration Module

**New file: `src/coin_config.py`**

```python
"""Coin universe configuration with tier-based risk profiles."""

from dataclasses import dataclass
from typing import Dict, List

@dataclass
class TierConfig:
    """Configuration for a coin tier."""
    name: str
    max_position_pct: float      # Max % of balance per position
    stop_loss_pct: float         # Stop loss percentage
    take_profit_usd: float       # Take profit in USD (consistent $1)
    max_concurrent: int          # Max positions in this tier
    min_volume_24h: float        # Minimum 24h volume to trade

# Tier definitions
TIERS = {
    1: TierConfig(
        name="Blue Chips",
        max_position_pct=0.25,
        stop_loss_pct=0.03,
        take_profit_usd=1.00,
        max_concurrent=2,
        min_volume_24h=100_000_000  # $100M
    ),
    2: TierConfig(
        name="Established Altcoins",
        max_position_pct=0.15,
        stop_loss_pct=0.05,
        take_profit_usd=1.00,
        max_concurrent=3,
        min_volume_24h=10_000_000   # $10M
    ),
    3: TierConfig(
        name="High Volatility",
        max_position_pct=0.10,
        stop_loss_pct=0.07,
        take_profit_usd=1.00,
        max_concurrent=3,
        min_volume_24h=1_000_000    # $1M
    )
}

# Coin to tier mapping
COINS = {
    # Tier 1: Blue Chips
    "bitcoin": 1,
    "ethereum": 1,
    "binancecoin": 1,
    "ripple": 1,
    "solana": 1,

    # Tier 2: Established Altcoins
    "cardano": 2,
    "dogecoin": 2,
    "avalanche-2": 2,
    "polkadot": 2,
    "chainlink": 2,
    "polygon-ecosystem-token": 2,
    "tron": 2,
    "the-open-network": 2,
    "shiba-inu": 2,
    "litecoin": 2,
    "uniswap": 2,
    "bitcoin-cash": 2,
    "stellar": 2,
    "near": 2,
    "aptos": 2,

    # Tier 3: High Volatility
    "pepe": 3,
    "floki": 3,
    "bonk": 3,
    "dogwifcoin": 3,
    "brett": 3,
    "render-token": 3,
    "injective-protocol": 3,
    "sei-network": 3,
    "sui": 3,
    "celestia": 3,
    "jupiter-exchange-solana": 3,
    "starknet": 3,
    "worldcoin-wld": 3,
    "arbitrum": 3,
    "optimism": 3,
    "immutable-x": 3,
    "gala": 3,
    "the-sandbox": 3,
    "axie-infinity": 3,
    "ondo-finance": 3,
    "fetch-ai": 3,
    "kaspa": 3,
    "cosmos": 3,
    "algorand": 3,
    "hedera-hashgraph": 3,
}

def get_coin_ids() -> List[str]:
    """Get all coin IDs."""
    return list(COINS.keys())

def get_tier(coin_id: str) -> int:
    """Get tier for a coin."""
    return COINS.get(coin_id, 3)  # Default to tier 3

def get_tier_config(coin_id: str) -> TierConfig:
    """Get tier configuration for a coin."""
    tier = get_tier(coin_id)
    return TIERS[tier]

def get_coins_by_tier(tier: int) -> List[str]:
    """Get all coins in a specific tier."""
    return [coin for coin, t in COINS.items() if t == tier]
```

### 2. Update Market Data for Batch Fetching

**Modify: `src/market_data.py`**

```python
def fetch_all_prices(self) -> Dict[str, Dict]:
    """Fetch prices for ALL coins in one API call.

    Returns:
        Dict mapping coin_id to {price_usd, change_24h}
    """
    from src.coin_config import get_coin_ids

    coin_ids = get_coin_ids()
    ids_param = ",".join(coin_ids)

    url = f"{self.base_url}/simple/price"
    params = {
        "ids": ids_param,
        "vs_currencies": "usd",
        "include_24hr_change": "true"
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    result = {}
    for coin_id in coin_ids:
        if coin_id in data:
            result[coin_id] = {
                "price_usd": data[coin_id].get("usd", 0),
                "change_24h": data[coin_id].get("usd_24h_change", 0)
            }

    return result

def update_all_prices(self) -> int:
    """Update all coin prices in database.

    Returns:
        Number of coins updated.
    """
    prices = self.fetch_all_prices()

    with self.db._get_connection() as conn:
        cursor = conn.cursor()
        for coin_id, data in prices.items():
            cursor.execute("""
                INSERT OR REPLACE INTO market_data (coin, price_usd, change_24h, last_updated)
                VALUES (?, ?, ?, datetime('now'))
            """, (coin_id, data["price_usd"], data["change_24h"]))
        conn.commit()

    logger.info(f"Updated prices for {len(prices)} coins")
    return len(prices)
```

### 3. Update Risk Manager for Tier-Based Limits

**Modify: `src/risk_manager.py`**

```python
from src.coin_config import get_tier_config, get_tier, TIERS

def get_position_limits(self, coin: str) -> Dict[str, float]:
    """Get tier-specific position limits for a coin."""
    config = get_tier_config(coin)
    balance = self.get_available_balance()

    return {
        "max_position_usd": balance * config.max_position_pct,
        "stop_loss_pct": config.stop_loss_pct,
        "take_profit_pct": config.take_profit_pct,
        "tier": get_tier(coin),
        "tier_name": config.name
    }

def can_open_position(self, coin: str, size_usd: float) -> Tuple[bool, str]:
    """Check if a position can be opened, considering tier limits."""
    config = get_tier_config(coin)
    tier = get_tier(coin)

    # Check tier-specific concurrent position limit
    current_tier_positions = self._count_positions_in_tier(tier)
    if current_tier_positions >= config.max_concurrent:
        return False, f"Max {config.max_concurrent} positions in {config.name} tier"

    # Check position size limit
    limits = self.get_position_limits(coin)
    if size_usd > limits["max_position_usd"]:
        return False, f"Position ${size_usd:.2f} exceeds tier max ${limits['max_position_usd']:.2f}"

    # Existing checks (total positions, daily loss, etc.)
    ...

    return True, "OK"

def _count_positions_in_tier(self, tier: int) -> int:
    """Count open positions in a specific tier."""
    from src.coin_config import get_tier

    with self.db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT coin_name FROM open_trades")
        open_coins = [row[0] for row in cursor.fetchall()]

    return sum(1 for coin in open_coins if get_tier(coin) == tier)
```

### 4. Update Dashboard to Show Tier Information

**Modify: `src/dashboard.py`**

Add tier badge to market data display:
```html
<span class="tier-badge tier-{{ tier }}">T{{ tier }}</span>
```

CSS:
```css
.tier-badge {
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 0.75em;
    margin-left: 8px;
}
.tier-badge.tier-1 { background: #ffd700; color: #000; }
.tier-badge.tier-2 { background: #c0c0c0; color: #000; }
.tier-badge.tier-3 { background: #cd7f32; color: #fff; }
```

### 5. Update Main Loop

**Modify: `src/main.py`**

```python
def run_cycle(self):
    """Run one trading cycle for all coins."""
    # Batch fetch all prices (1 API call)
    updated = self.market_data.update_all_prices()
    logger.info(f"Updated {updated} coin prices")

    # Get all coins with prices
    coins = self.get_tradeable_coins()

    # Process each coin
    for coin in coins:
        self.process_coin(coin)

    # Existing: check open positions, learning analysis, etc.
    ...
```

---

## API Rate Limit Strategy

### CoinGecko Free Tier
- Limit: ~10-30 calls/minute
- Our approach: **1 call per cycle** (batch endpoint)

### Calculation
```
45 coins × 1 price = 1 API call (batch)
+ 1 call for market stats (optional)
= 2 calls per minute max

Well within 10-30 limit!
```

### Fallback
If batch call fails, fall back to individual calls with 2-second delays.

---

## Database Changes

### Add tier column to market_data (optional)
```sql
ALTER TABLE market_data ADD COLUMN tier INTEGER DEFAULT 3;
```

### Add index for tier queries
```sql
CREATE INDEX IF NOT EXISTS idx_market_data_tier ON market_data(tier);
```

---

## Files to Modify/Create

| File | Action | Changes |
|------|--------|---------|
| `src/coin_config.py` | CREATE | Tier definitions, coin mapping |
| `src/market_data.py` | MODIFY | Add batch fetch methods |
| `src/risk_manager.py` | MODIFY | Tier-based position limits |
| `src/dashboard.py` | MODIFY | Show tier badges, all coins |
| `src/main.py` | MODIFY | Use batch fetching |

---

## Acceptance Criteria

- [ ] All 45 coins fetching prices successfully
- [ ] Single API call fetches all coin prices
- [ ] Tier-specific risk limits enforced
- [ ] Dashboard shows all coins with tier badges
- [ ] No API rate limit errors
- [ ] Position limits respect tier configuration
- [ ] Existing functionality unchanged for current coins

---

## Testing Plan

### Step 1: Verify Batch API
```python
from src.market_data import MarketDataFetcher
mdf = MarketDataFetcher()
prices = mdf.fetch_all_prices()
print(f"Fetched {len(prices)} coins")
assert len(prices) >= 40
```

### Step 2: Verify Tier Config
```python
from src.coin_config import get_tier_config, get_coins_by_tier
assert get_tier_config("bitcoin").max_position_pct == 0.25
assert get_tier_config("pepe").max_position_pct == 0.10
assert len(get_coins_by_tier(1)) == 5
assert len(get_coins_by_tier(3)) == 25
```

### Step 3: Verify Risk Limits
```python
from src.risk_manager import RiskManager
rm = RiskManager()
btc_limits = rm.get_position_limits("bitcoin")
pepe_limits = rm.get_position_limits("pepe")
assert btc_limits["stop_loss_pct"] < pepe_limits["stop_loss_pct"]
```

### Step 4: End-to-End Test
```bash
# Run one cycle and verify
python3 -c "from src.main import TradingBot; TradingBot().run_cycle()"
# Check dashboard shows all coins
curl http://localhost:8080 | grep -c "tier-badge"  # Should be 45
```

---

## Rollback Plan

If issues arise:
1. Revert `coin_config.py` to only include original 3 coins
2. Keep batch API (still works for 3 coins)
3. No database schema changes required to rollback
