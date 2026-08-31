from dataclasses import dataclass
from typing import List


@dataclass
class RecoveryContext:
    amount: float
    customer_success_count: int
    customer_failed_count: int
    failure_type: str
    hours_since_last_success: float
    retry_count: int = 0


@dataclass
class RecoveryScore:
    score: int
    tier: str
    recommended_action: str
    confidence: str
    reasons: List[str]


def calculate_recovery_score(
    context: RecoveryContext,
) -> RecoveryScore:
    """
    Calculate an explainable recovery opportunity score.

    This is deterministic by design.

    The scorer provides:
    - recovery score
    - recovery tier
    - deterministic recommended action
    - confidence
    - explainable reasons

    AI reasoning happens in a separate layer.
    """

    score = 0
    reasons = []

    total_customer_payments = (
        context.customer_success_count
        + context.customer_failed_count
    )

    # ---------------------------------------------------------
    # Customer historical success rate
    # ---------------------------------------------------------

    if total_customer_payments > 0:
        success_rate = (
            context.customer_success_count
            / total_customer_payments
        )
    else:
        success_rate = 0.0

    # ---------------------------------------------------------
    # 1. Payment value — max 20
    # ---------------------------------------------------------

    if context.amount >= 5000:
        score += 20
        reasons.append("High-value payment")

    elif context.amount >= 1000:
        score += 12
        reasons.append("Medium-value payment")

    else:
        score += 5
        reasons.append("Low-value payment")

    # ---------------------------------------------------------
    # 2. Customer history — max 30
    # ---------------------------------------------------------

    if total_customer_payments == 0:
        reasons.append(
            "No previous customer payment history"
        )

    elif (
        success_rate >= 0.75
        and context.customer_success_count >= 3
    ):
        score += 30
        reasons.append(
            "Strong successful payment history"
        )

    elif success_rate >= 0.50:
        score += 20
        reasons.append(
            "Moderate successful payment history"
        )

    elif context.customer_success_count >= 1:
        score += 8
        reasons.append(
            "Limited successful payment history"
        )

    else:
        reasons.append(
            "No successful payment history"
        )

    # ---------------------------------------------------------
    # Historical failure-rate penalty
    # ---------------------------------------------------------

    if total_customer_payments >= 3:

        if success_rate < 0.25:
            score -= 15
            reasons.append(
                "High historical payment failure rate"
            )

        elif success_rate < 0.50:
            score -= 8
            reasons.append(
                "Elevated historical payment failure rate"
            )

    # Keep score within bounds.
    score = max(0, min(score, 100))

    # ---------------------------------------------------------
    # 3. Failure recoverability — max 30
    # ---------------------------------------------------------

    retryable_failures = {
        "temporary_failure",
        "bank_timeout",
        "timeout",
        "network_timeout",
        "gateway_timeout",
    }

    if context.failure_type in retryable_failures:
        score += 30
        reasons.append(
            "Failure appears retryable"
        )

    elif context.failure_type == "permanent_failure":
        score -= 20
        reasons.append(
            "Failure appears permanent"
        )

    else:
        reasons.append(
            "Failure may require alternative recovery"
        )

    # ---------------------------------------------------------
    # 4. Recency — max 20
    # ---------------------------------------------------------

    if context.hours_since_last_success <= 24:
        score += 20
        reasons.append(
            "Recent successful payment"
        )

    elif context.hours_since_last_success <= 72:
        score += 12
        reasons.append(
            "Recent customer activity"
        )

    elif context.hours_since_last_success != float("inf"):
        score += 5

    # Final score bounds.
    score = max(0, min(score, 100))

    # ---------------------------------------------------------
    # 5. Determine tier, action and confidence
    # ---------------------------------------------------------

    if score >= 75:
        tier = "HIGH"
        recommended_action = "RETRY"
        confidence = "HIGH"

    elif score >= 50:
        tier = "MEDIUM"
        recommended_action = "RETRY_WITH_CAUTION"
        confidence = "MEDIUM"

    else:
        tier = "LOW"
        recommended_action = "DO_NOT_RETRY"
        confidence = "LOW"

    # ---------------------------------------------------------
    # 6. Return complete deterministic score
    # ---------------------------------------------------------

    return RecoveryScore(
        score=score,
        tier=tier,
        recommended_action=recommended_action,
        confidence=confidence,
        reasons=reasons,
    )