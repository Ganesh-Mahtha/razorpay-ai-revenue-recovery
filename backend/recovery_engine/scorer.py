from dataclasses import dataclass
from typing import List


@dataclass
class RecoveryContext:
    amount: float
    customer_success_count: int
    failure_type: str
    hours_since_last_success: float


@dataclass
class RecoveryScore:
    score: int
    tier: str
    recommended_action: str
    confidence: str
    reasons: List[str]


def calculate_recovery_score(context: RecoveryContext) -> RecoveryScore:
    """
    Calculate an explainable recovery opportunity score.

    This is deterministic by design.
    AI will sit above this layer later.
    """

    score = 0
    reasons = []

    # 1. Payment value — max 20
    if context.amount >= 5000:
        score += 20
        reasons.append("High-value payment")
    elif context.amount >= 1000:
        score += 12
        reasons.append("Medium-value payment")
    else:
        score += 5
        reasons.append("Low-value payment")

    # 2. Customer history — max 30
    if context.customer_success_count >= 5:
        score += 30
        reasons.append("Strong successful payment history")
    elif context.customer_success_count >= 2:
        score += 20
        reasons.append("Returning successful customer")
    elif context.customer_success_count == 1:
        score += 10
        reasons.append("Previous successful payment")
    else:
        reasons.append("No successful payment history")

    # 3. Failure recoverability — max 30
    retryable_failures = {
        "temporary_failure",
        "network_error",
        "bank_timeout",
        "technical_error",
    }

    if context.failure_type in retryable_failures:
        score += 30
        reasons.append("Failure appears retryable")
    else:
        reasons.append("Failure may require alternative recovery")

    # 4. Recency — max 20
    if context.hours_since_last_success <= 24:
        score += 20
        reasons.append("Recent successful payment")
    elif context.hours_since_last_success <= 72:
        score += 12
        reasons.append("Recent customer activity")
    else:
        score += 5

    # Determine tier and action
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

    return RecoveryScore(
        score=score,
        tier=tier,
        recommended_action=recommended_action,
        confidence=confidence,
        reasons=reasons,
    )