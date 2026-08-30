from unittest.mock import patch

from backend.recovery_engine.ai_pipeline import (
    process_payment_with_ai,
    _reconcile_recommendations,
)

from backend.recovery_engine.ai_reasoner import (
    AIRecoveryAssessment,
)


def make_ai_assessment(
    action: str,
    recoverability: str = "MEDIUM",
    confidence: str = "HIGH",
) -> AIRecoveryAssessment:
    """
    Create a fake AI assessment for testing.

    This does NOT call OpenAI.
    """

    return AIRecoveryAssessment(
        diagnosis="Test AI diagnosis.",
        recoverability=recoverability,
        confidence=confidence,
        recommended_action=action,
        reasoning="Test AI reasoning.",
        signals=[
            "Test signal 1",
            "Test signal 2",
        ],
    )


# ==========================================================
# RECONCILIATION TESTS
# ==========================================================


def test_reconciliation_when_ai_and_policy_agree():
    """
    When AI and deterministic policy agree,
    the shared action should be selected.
    """

    action, reason = _reconcile_recommendations(
        ai_action="RETRY",
        deterministic_action="RETRY",
    )

    assert action == "RETRY"
    assert "agree" in reason.lower()


def test_reconciliation_prefers_cautious_ai_action():
    """
    AI says RETRY_WITH_CAUTION while deterministic policy
    says RETRY.

    The safer AI recommendation should win.
    """

    action, reason = _reconcile_recommendations(
        ai_action="RETRY_WITH_CAUTION",
        deterministic_action="RETRY",
    )

    assert action == "RETRY_WITH_CAUTION"
    assert "disagreed" in reason.lower()


def test_reconciliation_prefers_do_not_retry():
    """
    DO_NOT_RETRY must always beat a more aggressive retry.
    """

    action, reason = _reconcile_recommendations(
        ai_action="DO_NOT_RETRY",
        deterministic_action="RETRY",
    )

    assert action == "DO_NOT_RETRY"


def test_reconciliation_prefers_human_review_over_retry():
    """
    HUMAN_REVIEW should beat an automated retry when
    the AI recommends escalation.
    """

    action, reason = _reconcile_recommendations(
        ai_action="HUMAN_REVIEW",
        deterministic_action="RETRY",
    )

    assert action == "HUMAN_REVIEW"


def test_invalid_ai_action_defaults_to_human_review():
    """
    An invalid model action must never become an executable
    recovery action.
    """

    action, reason = _reconcile_recommendations(
        ai_action="INVALID_ACTION",
        deterministic_action="RETRY",
    )

    assert action == "HUMAN_REVIEW"


# ==========================================================
# END-TO-END AI PIPELINE TESTS
# ==========================================================


@patch(
    "backend.recovery_engine.ai_pipeline.assess_payment_with_ai"
)
def test_ai_pipeline_uses_cautious_action_when_ai_disagrees(
    mock_ai,
):
    """
    AI recommends RETRY_WITH_CAUTION while deterministic
    policy recommends RETRY.

    The final proposal should be RETRY_WITH_CAUTION.
    """

    mock_ai.return_value = make_ai_assessment(
        action="RETRY_WITH_CAUTION",
        recoverability="MEDIUM",
        confidence="LOW",
    )

    result = process_payment_with_ai(
        amount=20000,
        customer_success_count=3,
        customer_failed_count=1,
        failure_type="temporary_failure",
        hours_since_last_success=12,
    )

    assert result.ai_assessment.recommended_action == (
        "RETRY_WITH_CAUTION"
    )

    assert result.recommendation.action == "RETRY"

    assert result.reconciled_action == (
        "RETRY_WITH_CAUTION"
    )

    assert result.guardrail.action == (
        "RETRY_WITH_CAUTION"
    )

    assert result.execution.status == "SIMULATED"


@patch(
    "backend.recovery_engine.ai_pipeline.assess_payment_with_ai"
)
def test_permanent_failure_guardrail_overrides_ai_retry(
    mock_ai,
):
    """
    Critical safety test:

    Even if AI recommends RETRY, a permanent failure
    must ultimately be blocked by the deterministic
    guardrail.

    The reconciliation layer may still produce an
    intermediate retry recommendation because the
    failure-type safety rule belongs to the guardrail layer.

    The guardrail has final authority.
    """

    mock_ai.return_value = make_ai_assessment(
        action="RETRY",
        recoverability="HIGH",
        confidence="HIGH",
    )

    result = process_payment_with_ai(
        amount=20000,
        customer_success_count=3,
        customer_failed_count=1,
        failure_type="permanent_failure",
        hours_since_last_success=12,
    )

    # AI attempted to recommend a retry.
    assert result.ai_assessment.recommended_action == "RETRY"

    # The reconciliation layer may still produce a bounded
    # retry recommendation before safety guardrails.
    assert result.reconciled_action in {
        "RETRY",
        "RETRY_WITH_CAUTION",
    }

    # The critical safety property:
    # permanent failures must NEVER reach retry execution.
    assert result.guardrail.action == "DO_NOT_RETRY"

    assert result.guardrail.guardrail_triggered is True

    assert "Permanent failure" in (
        result.guardrail.guardrail_reasons[0]
    )

    # Execution must follow the guardrail decision,
    # not the AI recommendation.
    assert result.execution.action == "DO_NOT_RETRY"

@patch(
    "backend.recovery_engine.ai_pipeline.assess_payment_with_ai"
)
def test_unknown_failure_escalates_to_human_review(
    mock_ai,
):
    """
    Unknown failures must never be automatically retried,
    even if AI recommends RETRY.
    """

    mock_ai.return_value = make_ai_assessment(
        action="RETRY",
        recoverability="MEDIUM",
        confidence="HIGH",
    )

    result = process_payment_with_ai(
        amount=20000,
        customer_success_count=2,
        customer_failed_count=1,
        failure_type="unknown_failure",
        hours_since_last_success=24,
    )

    assert result.guardrail.action == "HUMAN_REVIEW"

    assert result.guardrail.guardrail_triggered is True

    assert "Failure type is unknown." in (
        result.guardrail.guardrail_reasons[0]
    )

    assert result.execution.action == "HUMAN_REVIEW"


@patch(
    "backend.recovery_engine.ai_pipeline.assess_payment_with_ai"
)
def test_ai_human_review_overrides_deterministic_retry(
    mock_ai,
):
    """
    If AI recommends HUMAN_REVIEW while deterministic
    policy recommends RETRY, the conservative reconciliation
    should select HUMAN_REVIEW.
    """

    mock_ai.return_value = make_ai_assessment(
        action="HUMAN_REVIEW",
        recoverability="LOW",
        confidence="LOW",
    )

    result = process_payment_with_ai(
        amount=20000,
        customer_success_count=3,
        customer_failed_count=1,
        failure_type="temporary_failure",
        hours_since_last_success=12,
    )

    assert result.ai_assessment.recommended_action == (
        "HUMAN_REVIEW"
    )

    assert result.reconciled_action == "HUMAN_REVIEW"

    assert result.guardrail.action == "HUMAN_REVIEW"

    assert result.execution.action == "HUMAN_REVIEW"


@patch(
    "backend.recovery_engine.ai_pipeline.assess_payment_with_ai"
)
def test_ai_do_not_retry_overrides_deterministic_retry(
    mock_ai,
):
    """
    If AI recommends DO_NOT_RETRY while deterministic
    policy recommends RETRY, the safer action wins.
    """

    mock_ai.return_value = make_ai_assessment(
        action="DO_NOT_RETRY",
        recoverability="LOW",
        confidence="HIGH",
    )

    result = process_payment_with_ai(
        amount=20000,
        customer_success_count=3,
        customer_failed_count=1,
        failure_type="temporary_failure",
        hours_since_last_success=12,
    )

    assert result.reconciled_action == "DO_NOT_RETRY"

    assert result.guardrail.action == "DO_NOT_RETRY"

    assert result.execution.action == "DO_NOT_RETRY"


@patch(
    "backend.recovery_engine.ai_pipeline.assess_payment_with_ai"
)
def test_ai_and_policy_agree_on_retry(
    mock_ai,
):
    """
    When AI and deterministic policy agree on RETRY,
    the reconciled action should remain RETRY.
    """

    mock_ai.return_value = make_ai_assessment(
        action="RETRY",
        recoverability="HIGH",
        confidence="HIGH",
    )

    result = process_payment_with_ai(
        amount=1000,
        customer_success_count=5,
        customer_failed_count=0,
        failure_type="temporary_failure",
        hours_since_last_success=2,
    )

    assert result.recommendation.action == "RETRY"

    assert result.ai_assessment.recommended_action == "RETRY"

    assert result.reconciled_action == "RETRY"

    assert result.guardrail.action == "RETRY"

    assert result.execution.status == "SIMULATED"