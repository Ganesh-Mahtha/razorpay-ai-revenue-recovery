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
    customer_failed_count: int,
    failure_type: str,
    hours_since_last_success: float,
) -> PaymentDiagnosis:
    """
    Diagnose a failed payment using payment context.

    This layer interprets payment signals.
    It does not authorize a recovery action.

    Failure categories are aligned with the recovery scorer:

        temporary_failure
        permanent_failure
        unknown_failure
    """

    signals = []

    total_customer_payments = (
        customer_success_count
        + customer_failed_count
    )

    if total_customer_payments > 0:
        success_rate = (
            customer_success_count
            / total_customer_payments
        )
    else:
        success_rate = 0.0

    # ---------------------------------------------------------
    # 1. Payment value
    # ---------------------------------------------------------

    if amount >= 5000:
        signals.append("High-value payment")
    elif amount >= 1000:
        signals.append("Meaningful payment value")

    # ---------------------------------------------------------
    # 2. Customer history
    # ---------------------------------------------------------

    if total_customer_payments == 0:
        signals.append("No previous customer payment history")

    elif success_rate >= 0.75 and customer_success_count >= 3:
        signals.append("Strong successful payment history")

    elif success_rate >= 0.50:
        signals.append("Moderate successful payment history")

    elif customer_success_count >= 1:
        signals.append("Limited successful payment history")

    else:
        signals.append("No successful payment history")

    if total_customer_payments >= 3:
        if success_rate < 0.25:
            signals.append("High historical payment failure rate")

        elif success_rate < 0.50:
            signals.append(
                "Elevated historical payment failure rate"
            )

    # ---------------------------------------------------------
    # 3. Failure type
    # ---------------------------------------------------------

    if failure_type == "temporary_failure":
        signals.append("Failure appears temporary")

    elif failure_type == "permanent_failure":
        signals.append("Failure appears permanent")

    else:
        signals.append(
            "Failure type requires further review"
        )

    # ---------------------------------------------------------
    # 4. Recency
    # ---------------------------------------------------------

    if hours_since_last_success <= 24:
        signals.append("Recent successful payment")

    elif hours_since_last_success <= 72:
        signals.append("Recent customer activity")

    # Do not add a recency signal when the value is infinity.
    #
    # This represents a customer with no known previous
    # successful payment.

    # ---------------------------------------------------------
    # 5. Determine recoverability
    # ---------------------------------------------------------

    # ---------------------------------------------------------
    # Permanent failure
    # ---------------------------------------------------------

    if failure_type == "permanent_failure":

        recoverability = "LOW"
        confidence = "HIGH"

        diagnosis = (
            "The payment does not appear suitable for "
            "automated recovery because the failure indicates "
            "a permanent issue."
        )

    # ---------------------------------------------------------
    # Strong temporary recovery opportunity
    # ---------------------------------------------------------

    elif (
        failure_type == "temporary_failure"
        and success_rate >= 0.75
        and customer_success_count >= 3
        and hours_since_last_success <= 24
    ):

        recoverability = "HIGH"
        confidence = "HIGH"

        diagnosis = (
            "The payment appears highly recoverable based on "
            "the temporary failure, strong customer history, "
            "and recent successful activity."
        )

    # ---------------------------------------------------------
    # Moderate temporary recovery opportunity
    # ---------------------------------------------------------

    elif (
        failure_type == "temporary_failure"
        and success_rate >= 0.50
    ):

        recoverability = "MEDIUM"
        confidence = "MEDIUM"

        diagnosis = (
            "The payment shows reasonable recovery potential "
            "based on the temporary failure and customer history, "
            "but caution is appropriate."
        )

    # ---------------------------------------------------------
    # Some positive history but not enough evidence
    # ---------------------------------------------------------

    elif (
        failure_type == "temporary_failure"
        and customer_success_count >= 1
    ):

        recoverability = "LOW"
        confidence = "MEDIUM"

        diagnosis = (
            "The payment has some positive recovery signals, "
            "but the customer's historical success rate is too "
            "weak to support a high-confidence recovery decision."
        )

    # ---------------------------------------------------------
    # Unknown failure
    # ---------------------------------------------------------

    elif failure_type == "unknown_failure":

        recoverability = "LOW"
        confidence = "LOW"

        diagnosis = (
            "The failure type could not be classified with "
            "enough confidence to support automated recovery."
        )

    # ---------------------------------------------------------
    # Fallback
    # ---------------------------------------------------------

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