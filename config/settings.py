"""
Trading System Configuration.

Central configuration for the autonomous trading bot.
"""

import os
from pathlib import Path

# =============================================================================
# Project Paths
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)

# =============================================================================
# Exchange Configuration
# =============================================================================

DEFAULT_EXCHANGE = os.getenv("TRADING_EXCHANGE", "bybit")

# =============================================================================
# Tradeable Coins
# =============================================================================

TRADEABLE_COINS = [
    # Tier 1 - Blue chips (high liquidity)
    "BTC", "ETH", "SOL", "BNB", "XRP",
    # Tier 2 - High volume
    "DOGE", "ADA", "AVAX", "LINK", "DOT",
    "MATIC", "UNI", "ATOM", "LTC", "ETC",
    # Tier 3 - More volatile
    "NEAR", "APT", "ARB", "OP", "INJ",
]

COIN_TIERS = {
    1: ["BTC", "ETH", "SOL", "BNB", "XRP"],
    2: ["DOGE", "ADA", "AVAX", "LINK", "DOT", "MATIC", "UNI", "ATOM", "LTC", "ETC"],
    3: ["NEAR", "APT", "ARB", "OP", "INJ"],
}

# Maps coin symbols to exchange trading pair format (Bybit uses COINUSDT)
SYMBOL_MAP = {
    # Tier 1
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "BNB": "BNBUSDT",
    "XRP": "XRPUSDT",
    # Tier 2
    "DOGE": "DOGEUSDT",
    "ADA": "ADAUSDT",
    "AVAX": "AVAXUSDT",
    "LINK": "LINKUSDT",
    "DOT": "DOTUSDT",
    "MATIC": "MATICUSDT",
    "UNI": "UNIUSDT",
    "ATOM": "ATOMUSDT",
    "LTC": "LTCUSDT",
    "ETC": "ETCUSDT",
    # Tier 3
    "NEAR": "NEARUSDT",
    "APT": "APTUSDT",
    "ARB": "ARBUSDT",
    "OP": "OPUSDT",
    "INJ": "INJUSDT",
}

# =============================================================================
# Risk Management
# =============================================================================

MAX_POSITIONS = 5
MAX_EXPOSURE_PCT = 0.10  # 10% of balance

# =============================================================================
# Paper Trading
# =============================================================================

INITIAL_BALANCE = 10000.0

# =============================================================================
# Health Monitoring
# =============================================================================

STALE_DATA_THRESHOLD = 5  # seconds without tick = unhealthy
STATUS_LOG_INTERVAL = 60  # seconds between status logs

# =============================================================================
# Strategist Configuration
# =============================================================================

STRATEGIST_ENABLED = True  # Set to False to disable LLM condition generation
STRATEGIST_INTERVAL = 180  # Seconds between condition generation (3 minutes)

# =============================================================================
# Paths
# =============================================================================

SNIPER_STATE_PATH = str(DATA_DIR / "sniper_state.json")
