from backend.recovery_engine.guardrails import (
    apply_guardrails,
)

from backend.recovery_engine.recommender import (
    RecoveryRecommendation,
)

from backend.recovery_engine.scorer import (
    RecoveryContext,
)


def test_retry_limit_requires_human_review():

    context = RecoveryContext(
        amount=5000,
        customer_success_count=5,
        customer_failed_count=0,
        failure_type="temporary_failure",
        hours_since_last_success=6,
        retry_count=1,
    )

    recommendation = RecoveryRecommendation(
        action="RETRY",
        title="Retry payment",
        confidence="HIGH",
        reason="AI recommends another retry.",
        guardrail_required=True,
    )

    decision = apply_guardrails(
        context=context,
        recommendation=recommendation,
    )

    assert decision.action == "HUMAN_REVIEW"

    assert decision.guardrail_triggered is True

    assert (
        "retry" in decision.guardrail_reasons[0].lower()
    )