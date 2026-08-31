from backend.recovery_engine.guardrails import apply_guardrails
from backend.recovery_engine.recommender import (
    RecoveryRecommendation,
)
from backend.recovery_engine.scorer import RecoveryContext


def test_permanent_failure_blocks_retry():
    context = RecoveryContext(
        amount=10000,
        customer_success_count=5,
        customer_failed_count=0,
        failure_type="permanent_failure",
        hours_since_last_success=6,
    )

    recommendation = RecoveryRecommendation(
        action="RETRY",
        title="Retry payment",
        confidence="HIGH",
        reason="Test recommendation",
        guardrail_required=True,
    )

    decision = apply_guardrails(
        context,
        recommendation,
    )

    assert decision.action == "DO_NOT_RETRY"
    assert decision.guardrail_triggered is True


def test_unknown_failure_requires_human_review():
    context = RecoveryContext(
        amount=10000,
        customer_success_count=5,
        customer_failed_count=0,
        failure_type="unknown_failure",
        hours_since_last_success=6,
    )

    recommendation = RecoveryRecommendation(
        action="RETRY",
        title="Retry payment",
        confidence="HIGH",
        reason="Test recommendation",
        guardrail_required=True,
    )

    decision = apply_guardrails(
        context,
        recommendation,
    )

    assert decision.action == "HUMAN_REVIEW"
    assert decision.guardrail_triggered is True


def test_poor_customer_history_downgrades_retry():
    context = RecoveryContext(
        amount=10000,
        customer_success_count=1,
        customer_failed_count=4,
        failure_type="temporary_failure",
        hours_since_last_success=8,
    )

    recommendation = RecoveryRecommendation(
        action="RETRY",
        title="Retry payment",
        confidence="HIGH",
        reason="Test recommendation",
        guardrail_required=True,
    )

    decision = apply_guardrails(
        context,
        recommendation,
    )

    assert decision.action == "RETRY_WITH_CAUTION"
    assert decision.guardrail_triggered is True


def test_safe_recommendation_passes_through():
    context = RecoveryContext(
        amount=10000,
        customer_success_count=5,
        customer_failed_count=0,
        failure_type="temporary_failure",
        hours_since_last_success=6,
    )

    recommendation = RecoveryRecommendation(
        action="RETRY",
        title="Retry payment",
        confidence="HIGH",
        reason="Strong recovery opportunity",
        guardrail_required=True,
    )

    decision = apply_guardrails(
        context,
        recommendation,
    )

    assert decision.action == "RETRY"
    assert decision.guardrail_triggered is False


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
        context,
        recommendation,
    )

    assert decision.action == "HUMAN_REVIEW"
    assert decision.guardrail_triggered is True

    assert (
        "retry" in decision.guardrail_reasons[0].lower()
    )