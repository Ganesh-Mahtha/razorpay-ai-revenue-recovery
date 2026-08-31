from dataclasses import dataclass

from .recommender import RecoveryRecommendation
from .scorer import RecoveryContext


@dataclass
class GuardrailDecision:
    action: str
    title: str
    confidence: str
    reason: str
    guardrail_triggered: bool
    guardrail_reasons: list[str]


def apply_guardrails(
    context: RecoveryContext,
    recommendation: RecoveryRecommendation,
) -> GuardrailDecision:
    """
    Apply safety and policy rules to a recovery recommendation.

    Guardrails have final authority over the recommended action.

    The scorer estimates opportunity.
    The recommender suggests an action.
    Guardrails determine whether that action is allowed.
    """

    guardrail_reasons = []

    # ---------------------------------------------------------
    # Guardrail 0 — Retry stopping rule
    # ---------------------------------------------------------

    if context.retry_count >= 1:
        guardrail_reasons.append(
            "Automatic retry limit has already been reached."
        )

        return GuardrailDecision(
            action="HUMAN_REVIEW",
            title="Review payment manually",
            confidence="HIGH",
            reason=(
                "The payment has already received an automated "
                "retry attempt. Another automatic retry is blocked "
                "by the retry stopping rule."
            ),
            guardrail_triggered=True,
            guardrail_reasons=guardrail_reasons,
        )

    total_customer_payments = (
        context.customer_success_count
        + context.customer_failed_count
    )

    if total_customer_payments > 0:
        success_rate = (
            context.customer_success_count
            / total_customer_payments
        )
    else:
        success_rate = 0.0

    # ---------------------------------------------------------
    # Guardrail 1 — Permanent failure
    # ---------------------------------------------------------

    if context.failure_type == "permanent_failure":
        guardrail_reasons.append(
            "Permanent failure must not be automatically retried."
        )

        return GuardrailDecision(
            action="DO_NOT_RETRY",
            title="Do not retry",
            confidence="HIGH",
            reason=(
                "The failure appears permanent, so the recovery "
                "action is blocked by a safety guardrail."
            ),
            guardrail_triggered=True,
            guardrail_reasons=guardrail_reasons,
        )

    # ---------------------------------------------------------
    # Guardrail 2 — Unknown failure
    # ---------------------------------------------------------

    if context.failure_type == "unknown_failure":
        guardrail_reasons.append(
            "Failure type is unknown."
        )

        return GuardrailDecision(
            action="HUMAN_REVIEW",
            title="Review payment manually",
            confidence="LOW",
            reason=(
                "RecoverAI cannot safely determine the appropriate "
                "automated recovery action."
            ),
            guardrail_triggered=True,
            guardrail_reasons=guardrail_reasons,
        )

    # ---------------------------------------------------------
    # Guardrail 3 — Very poor customer history
    # ---------------------------------------------------------

    if (
        total_customer_payments >= 3
        and success_rate < 0.25
        and recommendation.action == "RETRY"
    ):
        guardrail_reasons.append(
            "Customer has a high historical payment failure rate."
        )

        return GuardrailDecision(
            action="RETRY_WITH_CAUTION",
            title="Retry with caution",
            confidence="MEDIUM",
            reason=(
                "The payment may be recoverable, but the customer's "
                "historical payment success rate is low."
            ),
            guardrail_triggered=True,
            guardrail_reasons=guardrail_reasons,
        )

    # ---------------------------------------------------------
    # No guardrail triggered
    # ---------------------------------------------------------

    return GuardrailDecision(
        action=recommendation.action,
        title=recommendation.title,
        confidence=recommendation.confidence,
        reason=recommendation.reason,
        guardrail_triggered=False,
        guardrail_reasons=[],
    )