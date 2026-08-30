from dataclasses import dataclass

from agent.diagnosis import PaymentDiagnosis, diagnose_payment

from backend.recovery_engine.action_executor import (
    RecoveryActionResult,
    execute_recovery_action,
)

from backend.recovery_engine.ai_pipeline import (
    AIRecoveryPipelineResult,
    process_payment_with_ai,
)

from backend.recovery_engine.guardrails import (
    GuardrailDecision,
    apply_guardrails,
)

from backend.recovery_engine.razorpay_adapter import (
    payment_to_recovery_context,
)

from backend.recovery_engine.recommender import (
    RecoveryRecommendation,
    generate_recommendation,
)

from backend.recovery_engine.scorer import (
    RecoveryContext,
    RecoveryScore,
    calculate_recovery_score,
)


@dataclass
class RecoveryPipelineResult:
    """
    Result returned by the legacy deterministic pipeline.

    This structure is retained for backwards compatibility
    with the existing deterministic tests.

    The real Razorpay integration now uses the AI-assisted
    pipeline through process_razorpay_payment().
    """

    diagnosis: PaymentDiagnosis
    score: RecoveryScore
    recommendation: RecoveryRecommendation
    guardrail: GuardrailDecision
    execution: RecoveryActionResult


def process_payment(
    amount: float,
    customer_success_count: int,
    customer_failed_count: int,
    failure_type: str,
    hours_since_last_success: float,
) -> RecoveryPipelineResult:
    """
    Run a payment through the legacy deterministic pipeline.

    This function is intentionally preserved for backwards
    compatibility with the existing test suite.

    Flow:

        Payment context
            ↓
        Diagnosis
            ↓
        Deterministic scoring
            ↓
        Recommendation
            ↓
        Safety guardrails
            ↓
        Simulated action execution
    """

    # ---------------------------------------------------------
    # 1. Diagnose payment
    # ---------------------------------------------------------

    diagnosis = diagnose_payment(
        amount=amount,
        customer_success_count=customer_success_count,
        customer_failed_count=customer_failed_count,
        failure_type=failure_type,
        hours_since_last_success=hours_since_last_success,
    )

    # ---------------------------------------------------------
    # 2. Build deterministic scoring context
    # ---------------------------------------------------------

    context = RecoveryContext(
        amount=amount,
        customer_success_count=customer_success_count,
        customer_failed_count=customer_failed_count,
        failure_type=failure_type,
        hours_since_last_success=hours_since_last_success,
    )

    # ---------------------------------------------------------
    # 3. Calculate recovery opportunity
    # ---------------------------------------------------------

    score = calculate_recovery_score(context)

    # ---------------------------------------------------------
    # 4. Generate recommendation
    # ---------------------------------------------------------

    recommendation = generate_recommendation(score)

    # ---------------------------------------------------------
    # 5. Apply safety guardrails
    # ---------------------------------------------------------

    guardrail = apply_guardrails(
        context=context,
        recommendation=recommendation,
    )

    # ---------------------------------------------------------
    # 6. Execute final decision in simulation mode
    # ---------------------------------------------------------

    execution = execute_recovery_action(guardrail)

    return RecoveryPipelineResult(
        diagnosis=diagnosis,
        score=score,
        recommendation=recommendation,
        guardrail=guardrail,
        execution=execution,
    )


def process_razorpay_payment(
    payment: dict,
    customer_success_count: int = 0,
    customer_failed_count: int = 0,
    hours_since_last_success: float | None = None,
) -> AIRecoveryPipelineResult:
    """
    Process a real Razorpay payment through the complete
    AI-assisted RecoverAI pipeline.

    Razorpay-specific fields are first converted into the
    internal RecoveryContext.

    The payment is then passed through:

        Razorpay payment
              ↓
        Recovery context
              ↓
        AI reasoning
              ↓
        Deterministic scoring
              ↓
        Decision engine
              ↓
        Safety guardrails
              ↓
        Bounded execution
              ↓
        Audit trail

    AI remains advisory.

    The decision engine and guardrails retain final authority.
    """

    # =========================================================
    # 1. Convert Razorpay payment into internal context
    # =========================================================

    context = payment_to_recovery_context(
        payment=payment,
        customer_success_count=customer_success_count,
        customer_failed_count=customer_failed_count,
        hours_since_last_success=hours_since_last_success,
    )

    # =========================================================
    # 2. Run the production AI-assisted pipeline
    # =========================================================

    return process_payment_with_ai(
        amount=context.amount,
        customer_success_count=context.customer_success_count,
        customer_failed_count=context.customer_failed_count,
        failure_type=context.failure_type,
        hours_since_last_success=context.hours_since_last_success,
    )