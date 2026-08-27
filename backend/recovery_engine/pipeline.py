from dataclasses import dataclass

from agent.diagnosis import PaymentDiagnosis, diagnose_payment

from backend.recovery_engine.action_executor import (
    RecoveryActionResult,
    execute_recovery_action,
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
    Run a payment through the complete RecoverAI pipeline.

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

    The action executor never performs a real payment retry.
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
) -> RecoveryPipelineResult:
    """
    Process a real Razorpay payment through the complete
    RecoverAI recovery pipeline.

    Razorpay-specific fields are first converted into the
    internal RecoveryContext. The rest of the system then
    operates independently of the Razorpay API.
    """

    context = payment_to_recovery_context(
        payment=payment,
        customer_success_count=customer_success_count,
        customer_failed_count=customer_failed_count,
        hours_since_last_success=hours_since_last_success,
    )

    return process_payment(
        amount=context.amount,
        customer_success_count=context.customer_success_count,
        customer_failed_count=context.customer_failed_count,
        failure_type=context.failure_type,
        hours_since_last_success=context.hours_since_last_success,
    )