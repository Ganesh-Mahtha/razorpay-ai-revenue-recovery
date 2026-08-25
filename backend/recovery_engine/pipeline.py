from dataclasses import dataclass

from agent.diagnosis import PaymentDiagnosis, diagnose_payment
from razorpay_adapter import payment_to_recovery_context
from recommender import RecoveryRecommendation, generate_recommendation
from scorer import RecoveryContext, RecoveryScore, calculate_recovery_score


@dataclass
class RecoveryPipelineResult:
    diagnosis: PaymentDiagnosis
    score: RecoveryScore
    recommendation: RecoveryRecommendation


def process_payment(
    amount: float,
    customer_success_count: int,
    failure_type: str,
    hours_since_last_success: float,
) -> RecoveryPipelineResult:
    """
    Run a failed payment through the complete recovery pipeline.

    Flow:
        Payment context
            ↓
        Diagnosis
            ↓
        Recovery score
            ↓
        Recovery recommendation

    Diagnosis interprets the payment context.
    The deterministic scorer calculates recovery opportunity.
    The recommender converts the score into an actionable recommendation.
    """

    # 1. Diagnose the payment
    diagnosis = diagnose_payment(
        amount=amount,
        customer_success_count=customer_success_count,
        failure_type=failure_type,
        hours_since_last_success=int(hours_since_last_success),
    )

    # 2. Build deterministic scoring context
    context = RecoveryContext(
        amount=amount,
        customer_success_count=customer_success_count,
        failure_type=failure_type,
        hours_since_last_success=hours_since_last_success,
    )

    # 3. Calculate recovery opportunity
    score = calculate_recovery_score(context)

    # 4. Convert score into recommendation
    recommendation = generate_recommendation(score)

    # 5. Apply safety overrides
    #
    # A known permanent failure must never be recommended
    # for automated retry, even if other signals are strong.
    if (
        failure_type == "permanent_failure"
        and diagnosis.confidence == "HIGH"
    ):
        recommendation = RecoveryRecommendation(
            action="DO_NOT_RETRY",
            title="Do not retry",
            confidence="HIGH",
            reason=(
                "The payment failure appears permanent, so automated "
                "retry is not recommended despite other positive signals."
            ),
            guardrail_required=False,
        )

    return RecoveryPipelineResult(
        diagnosis=diagnosis,
        score=score,
        recommendation=recommendation,
    )

def process_razorpay_payment(
    payment: dict,
    customer_success_count: int = 0,
    hours_since_last_success: float | None = None,
) -> RecoveryPipelineResult:
    """
    Process a Razorpay payment through the recovery pipeline.

    The Razorpay payment is first converted into our internal
    RecoveryContext. The existing recovery pipeline then handles
    diagnosis, scoring, recommendation, and safety guardrails.
    """

    context = payment_to_recovery_context(
        payment=payment,
        customer_success_count=customer_success_count,
        hours_since_last_success=hours_since_last_success,
    )

    return process_payment(
        amount=context.amount,
        customer_success_count=context.customer_success_count,
        failure_type=context.failure_type,
        hours_since_last_success=context.hours_since_last_success,
    )