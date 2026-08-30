from unittest.mock import patch

from backend.recovery_engine.ai_pipeline import (
    process_payment_with_ai,
)

from backend.recovery_engine.ai_reasoner import (
    AIRecoveryAssessment,
)


def make_ai_assessment(
    action: str,
    recoverability: str = "HIGH",
    confidence: str = "HIGH",
) -> AIRecoveryAssessment:
    """
    Create a deterministic fake AI response.

    This test intentionally does NOT call the OpenAI API.
    """

    return AIRecoveryAssessment(
        diagnosis="AI identified a potentially recoverable failure.",
        recoverability=recoverability,
        confidence=confidence,
        recommended_action=action,
        reasoning=(
            "The AI recommends a retry based on the available "
            "payment and customer signals."
        ),
        signals=[
            "Failure appears potentially retryable.",
            "Customer has previous successful payment history.",
        ],
    )


@patch(
    "backend.recovery_engine.ai_pipeline.assess_payment_with_ai"
)
def test_ai_retry_is_blocked_and_audited(mock_ai):
    """
    Critical end-to-end safety demonstration.

    Scenario:

        AI recommends RETRY
                ↓
        Permanent failure detected
                ↓
        Deterministic policy / guardrails
                ↓
        DO_NOT_RETRY
                ↓
        Execution BLOCKED
                ↓
        Audit trail records the complete decision path

    No real AI API call is made.
    """

    # ---------------------------------------------------------
    # 1. Force AI to recommend an unsafe retry
    # ---------------------------------------------------------

    mock_ai.return_value = make_ai_assessment(
        action="RETRY",
        recoverability="HIGH",
        confidence="HIGH",
    )

    # ---------------------------------------------------------
    # 2. Process a permanent failure
    # ---------------------------------------------------------

    result = process_payment_with_ai(
        amount=20000,
        customer_success_count=3,
        customer_failed_count=1,
        failure_type="permanent_failure",
        hours_since_last_success=12,
    )

    # ---------------------------------------------------------
    # 3. AI recommendation is RETRY
    # ---------------------------------------------------------

    assert (
        result.ai_assessment.recommended_action
        == "RETRY"
    )

    # ---------------------------------------------------------
    # 4. Safety boundary overrides AI
    # ---------------------------------------------------------

    assert result.guardrail.action == "DO_NOT_RETRY"

    assert result.guardrail.guardrail_triggered is True

    # ---------------------------------------------------------
    # 5. Execution must NOT occur
    # ---------------------------------------------------------

    assert result.execution.executed is False

    assert result.execution.status == "BLOCKED"

    # ---------------------------------------------------------
    # 6. Audit trail must exist
    # ---------------------------------------------------------

    assert result.audit_trail is not None

    audit = result.audit_trail

    # ---------------------------------------------------------
    # 7. Verify payment context was recorded
    # ---------------------------------------------------------

    assert audit.payment_context["amount"] == 20000

    assert (
        audit.payment_context["failure_type"]
        == "permanent_failure"
    )

    # ---------------------------------------------------------
    # 8. Verify AI recommendation was recorded
    # ---------------------------------------------------------

    assert (
        audit.ai_assessment["recommended_action"]
        == "RETRY"
    )

    assert (
        audit.ai_assessment["confidence"]
        == "HIGH"
    )

    # ---------------------------------------------------------
    # 9. Verify deterministic policy was recorded
    # ---------------------------------------------------------

    assert "score" in audit.deterministic_score

    assert (
        audit.deterministic_recommendation["action"]
        in {
            "RETRY",
            "RETRY_WITH_CAUTION",
            "DO_NOT_RETRY",
            "HUMAN_REVIEW",
        }
    )

    # ---------------------------------------------------------
    # 10. Verify final decision was recorded
    # ---------------------------------------------------------

    assert (
        audit.final_decision["action"]
        == "DO_NOT_RETRY"
    )

    # ---------------------------------------------------------
    # 11. Verify guardrail decision was recorded
    # ---------------------------------------------------------

    assert (
        audit.guardrail["action"]
        == "DO_NOT_RETRY"
    )

    assert audit.guardrail["guardrail_triggered"] is True

    # ---------------------------------------------------------
    # 12. Verify execution outcome was recorded
    # ---------------------------------------------------------

    assert (
        audit.execution["status"]
        == "BLOCKED"
    )

    assert (
        audit.execution["executed"]
        is False
    )


    assert (
        audit.execution["executed"]
        is False
    )