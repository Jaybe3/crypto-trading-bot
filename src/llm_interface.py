"""Interface to local LLM via Ollama.

This module connects to a local LLM (qwen2.5-coder:7b) running via Ollama
to make trading decisions and analyze trades.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

from src.database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Default configuration
DEFAULT_MODEL = "qwen2.5-coder:7b"
# Ollama direct API - can be overridden with OLLAMA_HOST env var
# For WSL2, use the gateway IP to reach Windows host
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "172.27.144.1")
DEFAULT_API_URL = f"http://{OLLAMA_HOST}:11434/api/chat"
DEFAULT_TIMEOUT = 120  # seconds (LLM can be slow, especially first load)
MAX_RETRIES = 3
INITIAL_BACKOFF = 2  # seconds


class LLMInterface:
    """Interface to local LLM via Ollama API.

    Connects to a locally running LLM to make trading decisions,
    analyze trades, and generate learnings.

    Attributes:
        api_url: Ollama API endpoint.
        model: LLM model name.
        timeout: Request timeout in seconds.
        db: Database instance for logging.

    Example:
        >>> llm = LLMInterface()
        >>> response = llm.query("What is 2+2?")
        >>> print(response)
        "Four."

    Verification:
        User can test LLM directly with:
        curl -X POST http://localhost:11434/api/chat -H "Content-Type: application/json" \\
          -d '{"model": "qwen2.5-coder:7b", "messages": [{"role": "user", "content": "Hello"}], "stream": false}'
    """

    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        model: str = DEFAULT_MODEL,
        timeout: int = DEFAULT_TIMEOUT,
        db: Optional[Database] = None
    ):
        """Initialize the LLM interface.

        Args:
            api_url: Ollama API endpoint (default: http://localhost:11434/api/chat).
            model: LLM model name (default: qwen2.5-coder:7b).
            timeout: Request timeout in seconds (default: 120).
            db: Database instance (creates new one if not provided).

        Environment Variables:
            OLLAMA_HOST: Override the default host (e.g., for WSL use gateway IP).
        """
        self.api_url = api_url
        self.model = model
        self.timeout = timeout
        self.db = db or Database()

        logger.info(f"LLMInterface initialized: model={model}, url={api_url}")

    def _make_request(
        self,
        messages: List[Dict[str, str]],
        retry_count: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Make a request to the LLM API with retry logic.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            retry_count: Current retry attempt (for exponential backoff).

        Returns:
            API response as dict, or None if all retries failed.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }

        try:
            start_time = time.time()

            response = requests.post(
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            response.raise_for_status()

            elapsed = time.time() - start_time
            logger.info(f"LLM response received in {elapsed:.2f}s")

            return response.json()

        except ConnectionError as e:
            logger.error(f"Cannot connect to LLM at {self.api_url}: {e}")
            logger.error("Is Ollama running? Try: ollama serve")
            self.db.log_activity(
                activity_type='error',
                description='LLM connection failed',
                details=f'Cannot connect to {self.api_url}: {str(e)}'
            )
            return None

        except Timeout as e:
            logger.warning(f"LLM request timed out after {self.timeout}s")

            if retry_count < MAX_RETRIES:
                backoff = INITIAL_BACKOFF * (2 ** retry_count)
                logger.info(f"Retrying in {backoff}s (attempt {retry_count + 1}/{MAX_RETRIES})")
                time.sleep(backoff)
                return self._make_request(messages, retry_count + 1)

            logger.error(f"LLM request failed after {MAX_RETRIES} retries")
            self.db.log_activity(
                activity_type='error',
                description='LLM timeout after retries',
                details=f'Timed out after {MAX_RETRIES} attempts'
            )
            return None

        except RequestException as e:
            logger.error(f"LLM request error: {e}")

            if retry_count < MAX_RETRIES:
                backoff = INITIAL_BACKOFF * (2 ** retry_count)
                logger.info(f"Retrying in {backoff}s (attempt {retry_count + 1}/{MAX_RETRIES})")
                time.sleep(backoff)
                return self._make_request(messages, retry_count + 1)

            self.db.log_activity(
                activity_type='error',
                description='LLM request failed',
                details=str(e)
            )
            return None

    def query(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Send a prompt to the LLM and get a text response.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system prompt for context.

        Returns:
            LLM response text, or None if request failed.
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        # Log the query
        logger.info(f"Sending prompt to LLM: {prompt[:100]}...")

        response = self._make_request(messages)

        if response is None:
            return None

        # Extract content from response
        try:
            content = response.get("message", {}).get("content", "")

            # Log successful interaction
            self.db.log_activity(
                activity_type='llm_query',
                description=f'Prompt: {prompt[:100]}...',
                details=json.dumps({
                    'prompt': prompt,
                    'response': content,
                    'model': self.model
                })
            )

            logger.info(f"LLM response: {content[:100]}...")
            return content

        except (KeyError, TypeError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Raw response: {response}")
            return None

    def query_json(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict]:
        """Send a prompt and parse the response as JSON.

        Args:
            prompt: The user prompt (should ask for JSON response).
            system_prompt: Optional system prompt.

        Returns:
            Parsed JSON dict, or None if parsing failed.
        """
        response = self.query(prompt, system_prompt)

        if response is None:
            return None

        try:
            # Try to extract JSON from response
            # Sometimes LLM wraps JSON in markdown code blocks
            clean_response = response.strip()

            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.startswith("```"):
                clean_response = clean_response[3:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]

            return json.loads(clean_response.strip())

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Raw response: {response}")
            return None

    def get_trading_decision(
        self,
        market_data: Dict[str, Any],
        account_state: Dict[str, Any],
        recent_learnings: Optional[List[str]] = None,
        active_rules: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a trading decision from the LLM.

        Args:
            market_data: Current market prices and changes.
            account_state: Current account balance and positions.
            recent_learnings: List of recent learning texts.
            active_rules: List of active trading rules.

        Returns:
            Dict with 'action' (BUY/SELL/HOLD), 'coin', 'reason', 'confidence'.
        """
        system_prompt = """You are a cryptocurrency trading bot assistant.
Analyze the market data and account state to make a trading decision.
Always respond with valid JSON in this exact format:
{
    "action": "BUY" or "SELL" or "HOLD",
    "coin": "bitcoin" or "ethereum" or "ripple" or null,
    "size_usd": number or null,
    "reason": "brief explanation",
    "confidence": 0.0 to 1.0
}"""

        prompt = f"""Current Market Data:
{json.dumps(market_data, indent=2)}

Account State:
{json.dumps(account_state, indent=2)}

Recent Learnings:
{json.dumps(recent_learnings or [], indent=2)}

Active Rules:
{json.dumps(active_rules or [], indent=2)}

Based on this data, what trading action should I take?
Respond with JSON only."""

        result = self.query_json(prompt, system_prompt)

        if result and 'action' in result:
            logger.info(f"Trading decision: {result['action']} (confidence: {result.get('confidence', 'N/A')})")
            return result

        # Return a safe default if parsing failed
        logger.warning("Failed to get valid trading decision, defaulting to HOLD")
        return {
            "action": "HOLD",
            "coin": None,
            "size_usd": None,
            "reason": "Failed to parse LLM response",
            "confidence": 0.0
        }

    def analyze_trade(self, trade_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze a completed trade and generate a learning.

        Args:
            trade_data: Dict with trade details (coin, entry/exit price, pnl, etc.)

        Returns:
            Dict with 'what_happened', 'why_outcome', 'pattern', 'lesson', 'confidence'.
        """
        system_prompt = """You are a cryptocurrency trading analyst.
Analyze the completed trade and extract learnings.
Always respond with valid JSON in this exact format:
{
    "what_happened": "brief description of the trade",
    "why_outcome": "why did it succeed or fail",
    "pattern": "any pattern observed",
    "lesson": "key lesson learned",
    "confidence": 0.0 to 1.0
}"""

        prompt = f"""Analyze this completed trade:

Trade Details:
- Coin: {trade_data.get('coin_name', 'unknown')}
- Entry Price: ${trade_data.get('entry_price', 0):,.2f}
- Exit Price: ${trade_data.get('exit_price', 0):,.2f}
- Size: ${trade_data.get('size_usd', 0):,.2f}
- P&L: ${trade_data.get('pnl_usd', 0):,.2f} ({trade_data.get('pnl_pct', 0):+.2f}%)
- Entry Reason: {trade_data.get('entry_reason', 'unknown')}
- Exit Reason: {trade_data.get('exit_reason', 'unknown')}
- Duration: {trade_data.get('duration_seconds', 0)} seconds

What can we learn from this trade?
Respond with JSON only."""

        result = self.query_json(prompt, system_prompt)

        if result:
            logger.info(f"Trade analysis complete: {result.get('lesson', 'N/A')[:50]}...")
            return result

        return None

    def test_connection(self) -> bool:
        """Test if the LLM is reachable and responding.

        Returns:
            True if LLM responds, False otherwise.
        """
        logger.info("Testing LLM connection...")

        response = self.query("What is 2+2? Answer with just the number.")

        if response:
            logger.info(f"LLM connection test successful: {response}")
            return True

        logger.error("LLM connection test failed")
        return False

    def get_model_info(self) -> Dict[str, str]:
        """Get information about the configured model.

        Returns:
            Dict with model name and API URL.
        """
        return {
            "model": self.model,
            "api_url": self.api_url,
            "timeout": self.timeout
        }


# Allow running directly for testing
if __name__ == "__main__":
    print("=" * 60)
    print("LLM Interface Test - Connecting to Ollama")
    print("=" * 60)

    llm = LLMInterface()

    print(f"\nModel: {llm.model}")
    print(f"API URL: {llm.api_url}")
    print()

    # Test connection
    print("Testing connection...")
    print("-" * 40)

    response = llm.query("What is 2+2? Answer in one word.")

    if response:
        print(f"LLM Response: {response}")
        print("\nConnection successful!")
    else:
        print("Failed to connect to LLM")
        print("\nMake sure Ollama is running: ollama serve")
        print("And model 'qwen2.5-coder:7b' is available: ollama pull qwen2.5-coder:7b")
        print("\nFor WSL, set OLLAMA_HOST to your Windows gateway IP:")
        print("  export OLLAMA_HOST=172.x.x.x")
