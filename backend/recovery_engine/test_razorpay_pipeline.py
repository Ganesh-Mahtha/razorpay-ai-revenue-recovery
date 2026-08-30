from unittest.mock import patch

from backend.recovery_engine.ai_reasoner import (
    AIRecoveryAssessment,
)
from backend.recovery_engine.pipeline import (
    process_razorpay_payment,
)


@patch(
    "backend.recovery_engine.ai_pipeline.assess_payment_with_ai"
)
def test_razorpay_payment_flows_through_recovery_pipeline(
    mock_ai,
):
    """
    Verify that a Razorpay payment flows through the complete
    recovery pipeline without making a real AI API call.

    Pipeline:

        Razorpay payment
              ↓
        Razorpay adapter
              ↓
        AI assessment
              ↓
        Deterministic scoring
              ↓
        Decision engine
              ↓
        Guardrails
              ↓
        Simulated execution
    """

    # ---------------------------------------------------------
    # 1. Mock AI assessment
    # ---------------------------------------------------------
    #
    # This prevents the automated test suite from making an
    # actual OpenAI request or requiring OPENAI_API_KEY.
    #

    mock_ai.return_value = AIRecoveryAssessment(
        diagnosis=(
            "Gateway timeout appears temporary and "
            "potentially recoverable."
        ),
        recoverability="HIGH",
        confidence="HIGH",
        recommended_action="RETRY",
        reasoning=(
            "The payment has a temporary failure classification, "
            "six previous successful payments, no previous "
            "failures, and recent successful activity."
        ),
        signals=[
            "temporary_failure",
            "6 successful payments",
            "0 failed payments",
            "last success 6 hours ago",
        ],
    )

    # ---------------------------------------------------------
    # 2. Simulated Razorpay payment
    # ---------------------------------------------------------

    payment = {
        "amount": 849900,
        "error_code": "GATEWAY_ERROR",
        "error_description": "Gateway timeout",
        "error_reason": "timeout",
        "created_at": 1756000000,
    }

    # ---------------------------------------------------------
    # 3. Run complete Razorpay recovery pipeline
    # ---------------------------------------------------------

    result = process_razorpay_payment(
        payment=payment,
        customer_success_count=6,
        customer_failed_count=0,
        hours_since_last_success=6,
    )

    # ---------------------------------------------------------
    # 4. Verify AI assessment
    # ---------------------------------------------------------

    assert result.ai_assessment.recoverability == "HIGH"
    assert result.ai_assessment.confidence == "HIGH"
    assert (
        result.ai_assessment.recommended_action
        == "RETRY"
    )

    # Backwards-compatible diagnosis alias.
    assert result.diagnosis.recoverability == "HIGH"
    assert result.diagnosis.confidence == "HIGH"

    # ---------------------------------------------------------
    # 5. Verify deterministic scoring
    # ---------------------------------------------------------

    assert result.score.score == 100
    assert result.score.tier == "HIGH"

    # ---------------------------------------------------------
    # 6. Verify deterministic recommendation
    # ---------------------------------------------------------

    assert result.recommendation.action == "RETRY"
    assert result.recommendation.guardrail_required is True

    # ---------------------------------------------------------
    # 7. Verify reconciled decision
    # ---------------------------------------------------------

    assert result.reconciled_action == "RETRY"

    # ---------------------------------------------------------
    # 8. Verify guardrails
    # ---------------------------------------------------------

    assert result.guardrail.action == "RETRY"

    # The temporary failure should not trigger the
    # permanent/unknown failure safety boundary.
    assert result.guardrail.guardrail_triggered is False

    # ---------------------------------------------------------
    # 9. Verify simulated execution
    # ---------------------------------------------------------

    assert result.execution.action == "RETRY"
    assert result.execution.status == "SIMULATED"

    # ---------------------------------------------------------
    # 10. Verify audit trail exists
    # ---------------------------------------------------------

    assert result.audit_trail is not None
    assert result.audit_trail.audit_id
    assert result.audit_trail.payment_context["amount"] == 8499.0

    # ---------------------------------------------------------
    # 11. Critical test isolation check
    # ---------------------------------------------------------
    #
    # Exactly one AI assessment should have been requested
    # by the pipeline, but it was completely mocked.
    #

    mock_ai.assert_called_once()