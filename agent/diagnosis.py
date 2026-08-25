from dataclasses import dataclass
from typing import List


@dataclass
class PaymentDiagnosis:
    diagnosis: str
    recoverability: str
    confidence: str
    signals: List[str]


def diagnose_payment(
    amount: float,
    customer_success_count: int,
    failure_type: str,
    hours_since_last_success: int,
) -> PaymentDiagnosis:
    """
    Diagnose a failed payment using payment context.

    This is the AI-facing diagnosis contract.
    It interprets payment signals but does not authorize
    a recovery action.

    Recovery authorization remains the responsibility
    of the deterministic recovery engine and guardrails.
    """

    signals = []

    # Payment value
    if amount >= 5000:
        signals.append("High-value payment")
    elif amount >= 1000:
        signals.append("Meaningful payment value")

    # Customer history
    if customer_success_count >= 5:
        signals.append("Strong successful payment history")
    elif customer_success_count >= 2:
        signals.append("Some successful payment history")

    # Failure type
    if failure_type == "temporary_failure":
        signals.append("Failure appears temporary")
    elif failure_type == "permanent_failure":
        signals.append("Failure appears permanent")
    else:
        signals.append("Failure type requires further review")

    # Recency
    if hours_since_last_success <= 24:
        signals.append("Recent successful payment")

    # Determine recoverability
    if (
        failure_type == "temporary_failure"
        and customer_success_count >= 5
        and hours_since_last_success <= 24
    ):
        recoverability = "HIGH"
        confidence = "HIGH"
        diagnosis = (
            "The payment appears highly recoverable based on "
            "the temporary failure and strong recent payment history."
        )

    elif failure_type == "permanent_failure":
        recoverability = "LOW"
        confidence = "HIGH"
        diagnosis = (
            "The payment does not appear suitable for automated "
            "recovery because the failure indicates a permanent issue."
        )

    elif customer_success_count >= 2:
        recoverability = "MEDIUM"
        confidence = "MEDIUM"
        diagnosis = (
            "The payment shows some recovery potential, "
            "but the available signals are not strong enough "
            "for a high-confidence diagnosis."
        )

    else:
        recoverability = "LOW"
        confidence = "LOW"
        diagnosis = (
            "There is insufficient evidence to determine that "
            "the payment is a strong recovery opportunity."
        )

    return PaymentDiagnosis(
        diagnosis=diagnosis,
        recoverability=recoverability,
        confidence=confidence,
        signals=signals,
    )