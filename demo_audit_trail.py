from unittest.mock import patch

from backend.recovery_engine.ai_pipeline import (
    process_payment_with_ai,
)

from backend.recovery_engine.ai_reasoner import (
    AIRecoveryAssessment,
)

from backend.recovery_engine.audit_trail import (
    format_audit_trail,
)


def make_demo_ai_assessment() -> AIRecoveryAssessment:
    """
    Simulated AI response for the safety demonstration.

    No OpenAI API call is made.
    """

    return AIRecoveryAssessment(
        diagnosis=(
            "The payment appears potentially recoverable "
            "based on recent customer activity."
        ),
        recoverability="HIGH",
        confidence="HIGH",
        recommended_action="RETRY",
        reasoning=(
            "The customer has previous successful payments, "
            "so the AI recommends retrying the payment."
        ),
        signals=[
            "Customer has previous successful payments.",
            "Payment was recently successful in the past.",
        ],
    )


@patch(
    "backend.recovery_engine.ai_pipeline.assess_payment_with_ai"
)
def main(mock_ai):
    """
    Demonstrate the RecoverAI safety boundary.

    AI recommends RETRY.

    The payment is permanently failed.

    The deterministic safety layer blocks the retry.

    The complete decision is recorded in the audit trail.
    """

    mock_ai.return_value = make_demo_ai_assessment()

    result = process_payment_with_ai(
        amount=20000,
        customer_success_count=3,
        customer_failed_count=1,
        failure_type="permanent_failure",
        hours_since_last_success=12,
    )

    print()
    print(format_audit_trail(result.audit_trail))

    print()
    print("=" * 60)
    print("SAFETY DEMONSTRATION")
    print("=" * 60)

    print()
    print(
        f"AI recommendation: "
        f"{result.ai_assessment.recommended_action}"
    )

    print(
        f"Final decision: "
        f"{result.guardrail.action}"
    )

    print(
        f"Guardrail triggered: "
        f"{result.guardrail.guardrail_triggered}"
    )

    print(
        f"Execution status: "
        f"{result.execution.status}"
    )

    print(
        f"Payment executed: "
        f"{result.execution.executed}"
    )

    print()

    if (
        result.ai_assessment.recommended_action == "RETRY"
        and result.guardrail.action == "DO_NOT_RETRY"
        and result.execution.status == "BLOCKED"
        and result.execution.executed is False
    ):
        print(
            "✓ SAFETY BOUNDARY VERIFIED"
        )
        print(
            "✓ AI retry recommendation was blocked."
        )
        print(
            "✓ No payment execution occurred."
        )
        print(
            "✓ Decision was recorded in the audit trail."
        )
    else:
        print(
            "✗ SAFETY DEMONSTRATION FAILED"
        )


if __name__ == "__main__":
    main()