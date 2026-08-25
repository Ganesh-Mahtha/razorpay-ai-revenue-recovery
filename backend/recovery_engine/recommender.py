from dataclasses import dataclass

from scorer import RecoveryScore


@dataclass
class RecoveryRecommendation:
    action: str
    title: str
    confidence: str
    reason: str
    guardrail_required: bool


def generate_recommendation(
    score: RecoveryScore,
) -> RecoveryRecommendation:
    """
    Convert a recovery score into a bounded recovery recommendation.

    This layer does not calculate the recovery score.
    It translates the scorer's decision into an actionable,
    explainable recommendation.

    Decision priority:
    1. LOW recovery opportunity -> DO_NOT_RETRY
    2. LOW confidence -> HUMAN_REVIEW
    3. HIGH recovery opportunity -> RETRY
    4. MEDIUM recovery opportunity -> RETRY_WITH_CAUTION
    """

    # A low recovery opportunity should never be retried,
    # even if confidence is also low.
    if score.tier == "LOW":
        return RecoveryRecommendation(
            action="DO_NOT_RETRY",
            title="Do not retry",
            confidence=score.confidence,
            reason="The payment does not currently show enough evidence of a recoverable opportunity.",
            guardrail_required=False,
        )

    # If the opportunity is potentially recoverable but
    # the system is not confident enough, escalate to a human.
    if score.confidence == "LOW":
        return RecoveryRecommendation(
            action="HUMAN_REVIEW",
            title="Review payment manually",
            confidence="LOW",
            reason="RecoverAI is not confident enough to recommend an automated recovery action.",
            guardrail_required=True,
        )

    if score.tier == "HIGH":
        return RecoveryRecommendation(
            action="RETRY",
            title="Retry payment",
            confidence=score.confidence,
            reason="The payment has a strong recovery opportunity based on its value, history, and failure context.",
            guardrail_required=True,
        )

    if score.tier == "MEDIUM":
        return RecoveryRecommendation(
            action="RETRY_WITH_CAUTION",
            title="Retry with caution",
            confidence=score.confidence,
            reason="The payment shows some recovery potential, but the available signals are not strong enough for an aggressive retry.",
            guardrail_required=True,
        )

    return RecoveryRecommendation(
        action="DO_NOT_RETRY",
        title="Do not retry",
        confidence=score.confidence,
        reason="The payment does not currently show enough evidence of a recoverable opportunity.",
        guardrail_required=False,
    )