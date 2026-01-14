"""Coin universe configuration with tier-based risk profiles.

Defines the 45-coin trading universe organized into three tiers:
- Tier 1: Blue Chips (5 coins) - Conservative, large positions
- Tier 2: Established Altcoins (15 coins) - Balanced approach
- Tier 3: High Volatility (25 coins) - Aggressive, small positions

Each tier has different risk parameters and volume requirements.
"""

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
TIERS: Dict[int, TierConfig] = {
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


# Coin to tier mapping (CoinGecko IDs)
COINS: Dict[str, int] = {
    # ===================
    # Tier 1: Blue Chips (5)
    # ===================
    "bitcoin": 1,
    "ethereum": 1,
    "binancecoin": 1,
    "ripple": 1,
    "solana": 1,

    # ===================
    # Tier 2: Established Altcoins (15)
    # ===================
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

    # ===================
    # Tier 3: High Volatility (25)
    # ===================
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
    """Get all coin IDs in the trading universe.

    Returns:
        List of CoinGecko coin IDs.
    """
    return list(COINS.keys())


def get_tier(coin_id: str) -> int:
    """Get tier number for a coin.

    Args:
        coin_id: CoinGecko coin ID.

    Returns:
        Tier number (1, 2, or 3). Defaults to 3 for unknown coins.
    """
    return COINS.get(coin_id, 3)


def get_tier_config(coin_id: str) -> TierConfig:
    """Get tier configuration for a coin.

    Args:
        coin_id: CoinGecko coin ID.

    Returns:
        TierConfig with risk parameters for the coin's tier.
    """
    tier = get_tier(coin_id)
    return TIERS[tier]


def get_coins_by_tier(tier: int) -> List[str]:
    """Get all coins in a specific tier.

    Args:
        tier: Tier number (1, 2, or 3).

    Returns:
        List of coin IDs in that tier.
    """
    return [coin for coin, t in COINS.items() if t == tier]


def get_tier_summary() -> Dict[int, Dict]:
    """Get summary of each tier.

    Returns:
        Dict with tier stats.
    """
    return {
        tier: {
            "name": config.name,
            "coin_count": len(get_coins_by_tier(tier)),
            "max_position_pct": config.max_position_pct,
            "stop_loss_pct": config.stop_loss_pct,
            "min_volume": config.min_volume_24h
        }
        for tier, config in TIERS.items()
    }


# Quick verification when run directly
if __name__ == "__main__":
    print("=" * 50)
    print("Coin Universe Configuration")
    print("=" * 50)

    total = len(COINS)
    print(f"\nTotal coins: {total}")

    for tier, config in TIERS.items():
        coins = get_coins_by_tier(tier)
        print(f"\nTier {tier}: {config.name}")
        print(f"  Coins: {len(coins)}")
        print(f"  Max position: {config.max_position_pct:.0%}")
        print(f"  Stop-loss: {config.stop_loss_pct:.0%}")
        print(f"  Take-profit: ${config.take_profit_usd:.2f}")
        print(f"  Min volume: ${config.min_volume_24h:,.0f}")
        print(f"  Coins: {', '.join(coins[:5])}{'...' if len(coins) > 5 else ''}")
