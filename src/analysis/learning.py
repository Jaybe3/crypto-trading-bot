"""
Learning Effectiveness Analysis (TASK-152).

Analyzes how well the learning system is working:
- Coin score accuracy
- Adaptation effectiveness
- Pattern confidence accuracy
- Knowledge growth over time
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from src.database import Database


def analyze_coin_score_accuracy(db: Database, min_trades: int = 5) -> dict:
    """
    Analyze how well coin scores predicted actual performance.

    Args:
        db: Database instance.
        min_trades: Minimum trades for a coin to be included.

    Returns:
        Dictionary with accuracy metrics and details.
    """
    results = {
        "total_coins": 0,
        "coins_with_enough_data": 0,
        "high_score_coins": [],  # Score > 60
        "low_score_coins": [],   # Score < 40
        "correlation": 0.0,
        "accuracy_assessment": "",
    }

    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()

            # Get coin scores with trade data
            cursor.execute("""
                SELECT coin, score, total_trades, win_rate, total_pnl
                FROM coin_scores
                WHERE total_trades >= ?
            """, (min_trades,))

            coins = cursor.fetchall()
            results["total_coins"] = len(coins)

            if not coins:
                results["accuracy_assessment"] = "No coins with enough data"
                return results

            # Separate by score level
            high_score_wins = []
            high_score_pnl = []
            low_score_wins = []
            low_score_pnl = []

            for coin, score, trades, win_rate, pnl in coins:
                results["coins_with_enough_data"] += 1
                score = score or 50

                coin_data = {
                    "coin": coin,
                    "score": score,
                    "win_rate": win_rate or 0,
                    "total_pnl": pnl or 0,
                    "trades": trades,
                }

                if score >= 60:
                    results["high_score_coins"].append(coin_data)
                    high_score_wins.append(win_rate or 0)
                    high_score_pnl.append(pnl or 0)
                elif score <= 40:
                    results["low_score_coins"].append(coin_data)
                    low_score_wins.append(win_rate or 0)
                    low_score_pnl.append(pnl or 0)

            # Calculate averages
            if high_score_wins:
                results["high_score_avg_win_rate"] = sum(high_score_wins) / len(high_score_wins)
                results["high_score_avg_pnl"] = sum(high_score_pnl) / len(high_score_pnl)
            else:
                results["high_score_avg_win_rate"] = 0
                results["high_score_avg_pnl"] = 0

            if low_score_wins:
                results["low_score_avg_win_rate"] = sum(low_score_wins) / len(low_score_wins)
                results["low_score_avg_pnl"] = sum(low_score_pnl) / len(low_score_pnl)
            else:
                results["low_score_avg_win_rate"] = 0
                results["low_score_avg_pnl"] = 0

            # Simple correlation check
            if high_score_wins and low_score_wins:
                # If high score coins have better win rate, scores are accurate
                if results["high_score_avg_win_rate"] > results["low_score_avg_win_rate"]:
                    diff = results["high_score_avg_win_rate"] - results["low_score_avg_win_rate"]
                    if diff > 20:
                        results["correlation"] = 0.8
                        results["accuracy_assessment"] = "STRONG - Scores accurately predict performance"
                    elif diff > 10:
                        results["correlation"] = 0.6
                        results["accuracy_assessment"] = "MODERATE - Scores somewhat predict performance"
                    else:
                        results["correlation"] = 0.4
                        results["accuracy_assessment"] = "WEAK - Scores slightly predict performance"
                else:
                    results["correlation"] = -0.2
                    results["accuracy_assessment"] = "INVERTED - Scores may be wrong"
            else:
                results["accuracy_assessment"] = "INSUFFICIENT DATA - Need more varied scores"

    except Exception as e:
        results["error"] = str(e)

    return results


def analyze_adaptation_effectiveness(db: Database) -> dict:
    """
    Analyze how effective adaptations were.

    Args:
        db: Database instance.

    Returns:
        Dictionary with effectiveness metrics.
    """
    results = {
        "total_adaptations": 0,
        "measured_adaptations": 0,
        "highly_effective": 0,
        "effective": 0,
        "neutral": 0,
        "ineffective": 0,
        "harmful": 0,
        "pending": 0,
        "effectiveness_rate": 0.0,
        "harmful_rate": 0.0,
        "by_type": {},
        "recent_adaptations": [],
    }

    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()

            # Get all adaptations
            cursor.execute("""
                SELECT adaptation_id, action, target, insight_confidence, effectiveness,
                       pre_metrics, post_metrics, timestamp
                FROM adaptations
                ORDER BY timestamp DESC
            """)

            adaptations = cursor.fetchall()
            results["total_adaptations"] = len(adaptations)

            by_type = defaultdict(lambda: {"count": 0, "effective": 0, "harmful": 0})

            for row in adaptations:
                (adapt_id, action, target, conf, effectiveness,
                 pre_metrics_json, post_metrics_json, applied_at) = row

                # Parse JSON metrics
                pre_metrics = json.loads(pre_metrics_json) if pre_metrics_json else {}
                post_metrics = json.loads(post_metrics_json) if post_metrics_json else {}

                wr_before = pre_metrics.get('win_rate', 0)
                wr_after = post_metrics.get('win_rate', 0)
                pnl_before = pre_metrics.get('pnl', 0)
                pnl_after = post_metrics.get('pnl', 0)
                rating = effectiveness or "pending"  # rest of code uses 'rating'

                action = action or "unknown"

                # Count by rating
                if rating == "highly_effective":
                    results["highly_effective"] += 1
                    results["measured_adaptations"] += 1
                    by_type[action]["effective"] += 1
                elif rating == "effective":
                    results["effective"] += 1
                    results["measured_adaptations"] += 1
                    by_type[action]["effective"] += 1
                elif rating == "neutral":
                    results["neutral"] += 1
                    results["measured_adaptations"] += 1
                elif rating == "ineffective":
                    results["ineffective"] += 1
                    results["measured_adaptations"] += 1
                elif rating == "harmful":
                    results["harmful"] += 1
                    results["measured_adaptations"] += 1
                    by_type[action]["harmful"] += 1
                else:
                    results["pending"] += 1

                by_type[action]["count"] += 1

                # Track recent adaptations
                if len(results["recent_adaptations"]) < 10:
                    results["recent_adaptations"].append({
                        "id": adapt_id,
                        "action": action,
                        "target": target,
                        "rating": rating,
                        "win_rate_change": (wr_after or 0) - (wr_before or 0) if wr_after and wr_before else None,
                        "pnl_change": (pnl_after or 0) - (pnl_before or 0) if pnl_after and pnl_before else None,
                    })

            # Calculate rates
            if results["measured_adaptations"] > 0:
                effective_count = results["highly_effective"] + results["effective"]
                results["effectiveness_rate"] = effective_count / results["measured_adaptations"] * 100
                results["harmful_rate"] = results["harmful"] / results["measured_adaptations"] * 100

            results["by_type"] = dict(by_type)

    except Exception as e:
        results["error"] = str(e)

    return results


def analyze_pattern_confidence_accuracy(db: Database, min_usage: int = 3) -> dict:
    """
    Analyze how well pattern confidence predicted outcomes.

    Args:
        db: Database instance.
        min_usage: Minimum usage count for pattern to be included.

    Returns:
        Dictionary with confidence accuracy metrics.
    """
    results = {
        "total_patterns": 0,
        "patterns_with_data": 0,
        "high_confidence_patterns": [],  # Confidence > 0.6
        "low_confidence_patterns": [],   # Confidence < 0.4
        "confidence_predicts_outcomes": False,
        "assessment": "",
    }

    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT pattern_id, name, confidence, usage_count, win_rate, total_pnl, is_active
                FROM trading_patterns
                WHERE usage_count >= ?
            """, (min_usage,))

            patterns = cursor.fetchall()
            results["total_patterns"] = len(patterns)

            high_conf_wins = []
            low_conf_wins = []

            for pattern_id, name, conf, usage, win_rate, pnl, active in patterns:
                results["patterns_with_data"] += 1
                conf = conf or 0.5

                pattern_data = {
                    "pattern_id": pattern_id,
                    "name": name,
                    "confidence": conf,
                    "win_rate": win_rate or 0,
                    "usage": usage,
                    "pnl": pnl or 0,
                    "is_active": active,
                }

                if conf >= 0.6:
                    results["high_confidence_patterns"].append(pattern_data)
                    high_conf_wins.append(win_rate or 0)
                elif conf <= 0.4:
                    results["low_confidence_patterns"].append(pattern_data)
                    low_conf_wins.append(win_rate or 0)

            # Calculate averages
            if high_conf_wins:
                results["high_conf_avg_win_rate"] = sum(high_conf_wins) / len(high_conf_wins)
            else:
                results["high_conf_avg_win_rate"] = 0

            if low_conf_wins:
                results["low_conf_avg_win_rate"] = sum(low_conf_wins) / len(low_conf_wins)
            else:
                results["low_conf_avg_win_rate"] = 0

            # Check if confidence predicts outcomes
            if high_conf_wins and low_conf_wins:
                if results["high_conf_avg_win_rate"] > results["low_conf_avg_win_rate"]:
                    results["confidence_predicts_outcomes"] = True
                    results["assessment"] = "YES - High confidence patterns win more often"
                else:
                    results["confidence_predicts_outcomes"] = False
                    results["assessment"] = "NO - Confidence does not predict outcomes"
            else:
                results["assessment"] = "INSUFFICIENT DATA - Need patterns at both confidence levels"

    except Exception as e:
        results["error"] = str(e)

    return results


def analyze_knowledge_growth(db: Database, days: int = 7) -> dict:
    """
    Analyze knowledge growth over time.

    Args:
        db: Database instance.
        days: Number of days to analyze.

    Returns:
        Dictionary with knowledge growth metrics.
    """
    results = {
        "period_days": days,
        "total_patterns": 0,
        "new_patterns": 0,
        "deactivated_patterns": 0,
        "total_rules": 0,
        "new_rules": 0,
        "coins_tracked": 0,
        "coins_blacklisted": 0,
        "coins_favored": 0,
        "total_insights": 0,
        "total_adaptations": 0,
        "daily_breakdown": [],
    }

    try:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        with db._get_connection() as conn:
            cursor = conn.cursor()

            # Pattern counts
            cursor.execute("SELECT COUNT(*) FROM trading_patterns")
            results["total_patterns"] = cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT COUNT(*) FROM trading_patterns
                WHERE created_at >= ?
            """, (cutoff,))
            results["new_patterns"] = cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT COUNT(*) FROM trading_patterns
                WHERE is_active = 0
            """)
            results["deactivated_patterns"] = cursor.fetchone()[0] or 0

            # Rule counts
            cursor.execute("SELECT COUNT(*) FROM regime_rules")
            results["total_rules"] = cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT COUNT(*) FROM regime_rules
                WHERE created_at >= ?
            """, (cutoff,))
            results["new_rules"] = cursor.fetchone()[0] or 0

            # Coin counts
            cursor.execute("SELECT COUNT(*) FROM coin_scores")
            results["coins_tracked"] = cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT COUNT(*) FROM coin_scores
                WHERE is_blacklisted = 1
            """)
            results["coins_blacklisted"] = cursor.fetchone()[0] or 0

            # Insight and adaptation counts
            cursor.execute("""
                SELECT COUNT(*) FROM insights
                WHERE created_at >= ?
            """, (cutoff,))
            results["total_insights"] = cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT COUNT(*) FROM adaptations
                WHERE applied_at >= ?
            """, (cutoff,))
            results["total_adaptations"] = cursor.fetchone()[0] or 0

            # Daily breakdown
            for d in range(days):
                day_start = (datetime.now() - timedelta(days=d+1)).replace(
                    hour=0, minute=0, second=0
                ).isoformat()
                day_end = (datetime.now() - timedelta(days=d)).replace(
                    hour=0, minute=0, second=0
                ).isoformat()

                cursor.execute("""
                    SELECT COUNT(*) FROM insights
                    WHERE created_at >= ? AND created_at < ?
                """, (day_start, day_end))
                day_insights = cursor.fetchone()[0] or 0

                cursor.execute("""
                    SELECT COUNT(*) FROM adaptations
                    WHERE applied_at >= ? AND applied_at < ?
                """, (day_start, day_end))
                day_adaptations = cursor.fetchone()[0] or 0

                cursor.execute("""
                    SELECT COUNT(*) FROM trading_patterns
                    WHERE created_at >= ? AND created_at < ?
                """, (day_start, day_end))
                day_patterns = cursor.fetchone()[0] or 0

                results["daily_breakdown"].append({
                    "day": d + 1,
                    "date": (datetime.now() - timedelta(days=d+1)).strftime("%Y-%m-%d"),
                    "insights": day_insights,
                    "adaptations": day_adaptations,
                    "new_patterns": day_patterns,
                })

    except Exception as e:
        results["error"] = str(e)

    return results


def calculate_learning_score(
    coin_accuracy: dict,
    adaptation_effectiveness: dict,
    pattern_accuracy: dict,
    knowledge_growth: dict
) -> dict:
    """
    Calculate an overall learning effectiveness score.

    Args:
        coin_accuracy: Results from analyze_coin_score_accuracy().
        adaptation_effectiveness: Results from analyze_adaptation_effectiveness().
        pattern_accuracy: Results from analyze_pattern_confidence_accuracy().
        knowledge_growth: Results from analyze_knowledge_growth().

    Returns:
        Dictionary with overall score and breakdown.
    """
    scores = {}
    weights = {
        "coin_accuracy": 0.25,
        "adaptation_effectiveness": 0.30,
        "pattern_accuracy": 0.25,
        "knowledge_growth": 0.20,
    }

    # Coin accuracy score (0-100)
    if coin_accuracy.get("correlation", 0) > 0.6:
        scores["coin_accuracy"] = 90
    elif coin_accuracy.get("correlation", 0) > 0.4:
        scores["coin_accuracy"] = 70
    elif coin_accuracy.get("correlation", 0) > 0.2:
        scores["coin_accuracy"] = 50
    else:
        scores["coin_accuracy"] = 30

    # Adaptation effectiveness score (0-100)
    eff_rate = adaptation_effectiveness.get("effectiveness_rate", 0)
    harm_rate = adaptation_effectiveness.get("harmful_rate", 100)
    if eff_rate > 60 and harm_rate < 20:
        scores["adaptation_effectiveness"] = 90
    elif eff_rate > 40 and harm_rate < 30:
        scores["adaptation_effectiveness"] = 70
    elif eff_rate > 20:
        scores["adaptation_effectiveness"] = 50
    else:
        scores["adaptation_effectiveness"] = 30

    # Pattern accuracy score (0-100)
    if pattern_accuracy.get("confidence_predicts_outcomes"):
        scores["pattern_accuracy"] = 80
    else:
        scores["pattern_accuracy"] = 40

    # Knowledge growth score (0-100)
    total_items = (
        knowledge_growth.get("new_patterns", 0) +
        knowledge_growth.get("new_rules", 0) +
        knowledge_growth.get("total_adaptations", 0)
    )
    if total_items >= 10:
        scores["knowledge_growth"] = 90
    elif total_items >= 5:
        scores["knowledge_growth"] = 70
    elif total_items >= 2:
        scores["knowledge_growth"] = 50
    else:
        scores["knowledge_growth"] = 30

    # Calculate weighted total
    total_score = sum(
        scores[key] * weights[key]
        for key in weights
    )

    # Determine grade
    if total_score >= 80:
        grade = "A"
        assessment = "EXCELLENT - Learning system is highly effective"
    elif total_score >= 65:
        grade = "B"
        assessment = "GOOD - Learning system is working well"
    elif total_score >= 50:
        grade = "C"
        assessment = "FAIR - Learning system needs improvement"
    else:
        grade = "D"
        assessment = "POOR - Learning system has issues"

    return {
        "total_score": total_score,
        "grade": grade,
        "assessment": assessment,
        "breakdown": scores,
        "weights": weights,
    }
