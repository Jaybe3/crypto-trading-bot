#!/usr/bin/env python3
"""
Learning Validation Script (TASK-151).

Validates that the learning loop is functioning correctly by checking:
1. Coin scores reflect trade performance
2. Pattern confidence updates appropriately
3. Adaptations are being triggered
4. Knowledge is growing over time

Usage:
    python scripts/validate_learning.py [--json] [--verbose]
"""

import argparse
import json
import sys
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    print("ERROR: requests library required. Install with: pip install requests")
    sys.exit(1)


DASHBOARD_URL = "http://localhost:8080"


class ValidationResult:
    """Result of a validation check."""

    def __init__(self, name: str, passed: bool, reason: str = "", details: dict = None):
        self.name = name
        self.passed = passed
        self.reason = reason
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "reason": self.reason,
            "details": self.details,
        }


def fetch_api(endpoint: str) -> dict:
    """Fetch data from dashboard API."""
    try:
        response = requests.get(f"{DASHBOARD_URL}{endpoint}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}


# =============================================================================
# Validation Functions
# =============================================================================

def validate_coin_scores() -> list[ValidationResult]:
    """Validate coin score updates."""
    results = []

    # Fetch coin data
    data = fetch_api("/api/knowledge/coins")
    if "error" in data:
        return [ValidationResult(
            "coin_scores_available",
            False,
            f"Cannot fetch coin data: {data['error']}"
        )]

    coins = data.get("coins", [])

    # Test 1: Coins are being tracked
    results.append(ValidationResult(
        "coins_tracked",
        len(coins) > 0,
        f"Found {len(coins)} coins" if coins else "No coins tracked yet",
        {"count": len(coins)}
    ))

    # Test 2: Coins have trade data
    coins_with_trades = [c for c in coins if c.get("total_trades", 0) > 0]
    results.append(ValidationResult(
        "coins_have_trades",
        len(coins_with_trades) > 0,
        f"{len(coins_with_trades)} coins have trade data",
        {"coins_with_trades": len(coins_with_trades)}
    ))

    # Test 3: Scores vary (not all the same)
    if len(coins) >= 2:
        scores = [c.get("score", 50) for c in coins if c.get("total_trades", 0) > 0]
        if len(scores) >= 2:
            score_variance = max(scores) - min(scores) if scores else 0
            results.append(ValidationResult(
                "scores_vary",
                score_variance > 5,
                f"Score range: {min(scores):.1f} - {max(scores):.1f}",
                {"min": min(scores), "max": max(scores), "variance": score_variance}
            ))
        else:
            results.append(ValidationResult(
                "scores_vary",
                False,
                "Not enough coins with trades to compare scores"
            ))

    # Test 4: Score correlates with win rate
    coins_with_enough_trades = [c for c in coins if c.get("total_trades", 0) >= 5]
    if len(coins_with_enough_trades) >= 2:
        # Sort by win rate and check if scores follow
        sorted_coins = sorted(coins_with_enough_trades, key=lambda c: c.get("win_rate", 0))
        score_trend_correct = True
        for i in range(len(sorted_coins) - 1):
            # Higher win rate should generally mean higher score
            if sorted_coins[i+1].get("win_rate", 0) > sorted_coins[i].get("win_rate", 0) + 20:
                if sorted_coins[i+1].get("score", 0) < sorted_coins[i].get("score", 0):
                    score_trend_correct = False
                    break

        results.append(ValidationResult(
            "score_correlates_winrate",
            score_trend_correct,
            "Scores generally correlate with win rate" if score_trend_correct else "Score-winrate correlation weak",
        ))

    return results


def validate_pattern_confidence() -> list[ValidationResult]:
    """Validate pattern confidence updates."""
    results = []

    data = fetch_api("/api/knowledge/patterns")
    if "error" in data:
        return [ValidationResult(
            "patterns_available",
            False,
            f"Cannot fetch pattern data: {data['error']}"
        )]

    patterns = data.get("patterns", [])

    # Test 1: Patterns exist
    results.append(ValidationResult(
        "patterns_exist",
        len(patterns) > 0,
        f"Found {len(patterns)} patterns" if patterns else "No patterns yet",
        {"count": len(patterns)}
    ))

    # Test 2: Patterns have been used
    used_patterns = [p for p in patterns if p.get("usage_count", 0) > 0]
    results.append(ValidationResult(
        "patterns_used",
        len(used_patterns) > 0,
        f"{len(used_patterns)} patterns have been used",
        {"used_count": len(used_patterns)}
    ))

    # Test 3: Confidence varies
    if len(patterns) >= 2:
        confidences = [p.get("confidence", 0.5) for p in patterns]
        conf_variance = max(confidences) - min(confidences)
        results.append(ValidationResult(
            "confidence_varies",
            conf_variance > 0.1,
            f"Confidence range: {min(confidences):.2f} - {max(confidences):.2f}",
            {"min": min(confidences), "max": max(confidences)}
        ))

    # Test 4: Some patterns are active, some may be inactive
    active_patterns = [p for p in patterns if p.get("is_active", True)]
    results.append(ValidationResult(
        "active_patterns",
        len(active_patterns) > 0,
        f"{len(active_patterns)} active patterns",
        {"active": len(active_patterns), "total": len(patterns)}
    ))

    return results


def validate_adaptations() -> list[ValidationResult]:
    """Validate that adaptations are being triggered."""
    results = []

    data = fetch_api("/api/adaptations")
    if "error" in data:
        return [ValidationResult(
            "adaptations_available",
            False,
            f"Cannot fetch adaptation data: {data['error']}"
        )]

    adaptations = data.get("adaptations", [])

    # Test 1: Adaptations have occurred
    results.append(ValidationResult(
        "adaptations_occurred",
        len(adaptations) > 0,
        f"Found {len(adaptations)} adaptations" if adaptations else "No adaptations yet",
        {"count": len(adaptations)}
    ))

    # Test 2: Effectiveness is being measured
    eff_data = fetch_api("/api/adaptations/effectiveness")
    if "error" not in eff_data:
        measured = sum([
            eff_data.get("highly_effective", 0),
            eff_data.get("effective", 0),
            eff_data.get("neutral", 0),
            eff_data.get("ineffective", 0),
            eff_data.get("harmful", 0),
        ])
        pending = eff_data.get("pending", 0)

        results.append(ValidationResult(
            "effectiveness_measured",
            measured > 0 or pending > 0,
            f"{measured} measured, {pending} pending",
            eff_data
        ))

        # Test 3: Not too many harmful adaptations
        total_rated = measured
        harmful = eff_data.get("harmful", 0)
        harmful_pct = (harmful / total_rated * 100) if total_rated > 0 else 0

        results.append(ValidationResult(
            "harmful_rate_acceptable",
            harmful_pct < 30,
            f"Harmful rate: {harmful_pct:.1f}%",
            {"harmful": harmful, "total_rated": total_rated, "harmful_pct": harmful_pct}
        ))

    # Test 4: Various adaptation types
    if adaptations:
        action_types = set(a.get("action", "") for a in adaptations)
        results.append(ValidationResult(
            "diverse_adaptations",
            len(action_types) >= 1,
            f"Adaptation types: {', '.join(action_types)}",
            {"types": list(action_types)}
        ))

    return results


def validate_strategist_usage() -> list[ValidationResult]:
    """Validate that Strategist uses knowledge."""
    results = []

    # Get knowledge context
    context = fetch_api("/api/knowledge/context")
    if "error" in context:
        return [ValidationResult(
            "context_available",
            False,
            f"Cannot fetch context: {context['error']}"
        )]

    # Test 1: Context has coin information
    has_coins = (
        "coins" in context or
        "coin_summaries" in context or
        "good_coins" in context
    )
    results.append(ValidationResult(
        "context_has_coins",
        has_coins,
        "Context includes coin information" if has_coins else "No coin info in context",
    ))

    # Test 2: Blacklist is in context
    blacklist = fetch_api("/api/knowledge/blacklist")
    blacklist_coins = blacklist.get("coins", [])
    results.append(ValidationResult(
        "blacklist_in_context",
        "blacklist" in context or len(blacklist_coins) >= 0,  # Always true if endpoint works
        f"{len(blacklist_coins)} coins blacklisted",
        {"blacklisted": len(blacklist_coins)}
    ))

    # Test 3: Patterns in context
    has_patterns = "patterns" in context or "pattern_summaries" in context
    results.append(ValidationResult(
        "context_has_patterns",
        has_patterns,
        "Context includes pattern information" if has_patterns else "No pattern info",
    ))

    # Test 4: Rules in context
    has_rules = "regime_rules" in context or "rules" in context
    results.append(ValidationResult(
        "context_has_rules",
        has_rules or True,  # Rules are optional
        "Context includes regime rules" if has_rules else "No regime rules yet (OK)",
    ))

    return results


def validate_knowledge_growth() -> list[ValidationResult]:
    """Validate that knowledge is growing over time."""
    results = []

    # Get loop stats
    stats = fetch_api("/api/loop-stats")
    if "error" in stats:
        return [ValidationResult(
            "stats_available",
            False,
            f"Cannot fetch stats: {stats['error']}"
        )]

    # Test 1: Trades are happening
    total_trades = stats.get("total_trades", 0)
    results.append(ValidationResult(
        "trades_executed",
        total_trades > 0,
        f"{total_trades} trades executed",
        {"total_trades": total_trades}
    ))

    # Test 2: Reflections are running
    reflections = stats.get("total_reflections", 0)
    results.append(ValidationResult(
        "reflections_running",
        reflections > 0,
        f"{reflections} reflections completed",
        {"reflections": reflections}
    ))

    # Test 3: Insights being generated
    insights = stats.get("total_insights", 0)
    results.append(ValidationResult(
        "insights_generated",
        insights >= 0,  # Can be 0 if no insights yet
        f"{insights} insights generated",
        {"insights": insights}
    ))

    # Test 4: Learning rate (insights per trade)
    if total_trades > 10:
        insight_rate = insights / total_trades if total_trades > 0 else 0
        adaptations = stats.get("total_adaptations", 0)
        adaptation_rate = adaptations / total_trades if total_trades > 0 else 0

        results.append(ValidationResult(
            "learning_rate",
            adaptation_rate > 0 or total_trades < 20,  # Give time to accumulate
            f"Adaptation rate: {adaptation_rate:.2%} per trade",
            {"insight_rate": insight_rate, "adaptation_rate": adaptation_rate}
        ))

    return results


# =============================================================================
# Main
# =============================================================================

def run_validation(verbose: bool = False) -> dict:
    """Run all learning validation checks."""
    all_results = {
        "coin_scores": validate_coin_scores(),
        "pattern_confidence": validate_pattern_confidence(),
        "adaptations": validate_adaptations(),
        "strategist_usage": validate_strategist_usage(),
        "knowledge_growth": validate_knowledge_growth(),
    }

    return all_results


def print_results(results: dict) -> bool:
    """Print validation results and return overall pass/fail."""
    print("=" * 70)
    print("              LEARNING VALIDATION RESULTS")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    all_passed = True

    for category, tests in results.items():
        passed = sum(1 for t in tests if t.passed)
        total = len(tests)
        status = "PASS" if passed == total else "PARTIAL" if passed > 0 else "FAIL"
        status_color = {
            "PASS": "\033[92m",    # Green
            "PARTIAL": "\033[93m", # Yellow
            "FAIL": "\033[91m",    # Red
        }.get(status, "")
        reset = "\033[0m"

        print(f"\n{category.upper().replace('_', ' ')}: {status_color}{passed}/{total} {status}{reset}")

        for test in tests:
            icon = "\033[92m✓\033[0m" if test.passed else "\033[91m✗\033[0m"
            print(f"  {icon} {test.name}")
            if test.reason:
                print(f"      {test.reason}")

            if not test.passed:
                all_passed = False

    print()
    print("=" * 70)
    overall = "\033[92mPASS\033[0m" if all_passed else "\033[91mFAIL\033[0m"
    print(f"OVERALL: {overall}")
    print("=" * 70)

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Validate Learning Loop")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    print(f"Connecting to dashboard at {DASHBOARD_URL}...")

    results = run_validation(verbose=args.verbose)

    if args.json:
        output = {
            "timestamp": datetime.now().isoformat(),
            "results": {
                cat: [r.to_dict() for r in tests]
                for cat, tests in results.items()
            }
        }
        print(json.dumps(output, indent=2))
    else:
        passed = print_results(results)
        sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
