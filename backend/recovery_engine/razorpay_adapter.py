from datetime import datetime, timezone

from .scorer import RecoveryContext


def map_failure_type(payment: dict) -> str:
    """
    Convert Razorpay payment failure information into
    RecoverAI's internal failure categories.

    Categories:

        temporary_failure
            Infrastructure / network / timeout type failures.

        permanent_failure
            Failures that should not be automatically retried.

        unknown_failure
            Failures that RecoverAI cannot safely classify.

    The adapter intentionally prefers safety over aggressive
    classification.
    """

    error_reason = (payment.get("error_reason") or "").lower()
    error_code = (payment.get("error_code") or "").lower()
    error_description = (payment.get("error_description") or "").lower()
    error_source = (payment.get("error_source") or "").lower()
    error_step = (payment.get("error_step") or "").lower()

    failure_text = " ".join(
        [
            error_reason,
            error_code,
            error_description,
            error_source,
            error_step,
        ]
    )

    # ---------------------------------------------------------
    # 1. Temporary / infrastructure-related failures
    # ---------------------------------------------------------

    temporary_keywords = [
        "timeout",
        "timed out",
        "network",
        "temporary",
        "gateway",
        "server",
        "technical",
        "connection",
        "unavailable",
        "service unavailable",
    ]

    if any(keyword in failure_text for keyword in temporary_keywords):
        return "temporary_failure"

    # ---------------------------------------------------------
    # 2. Clearly non-recoverable payment failures
    # ---------------------------------------------------------
    #
    # Keep this list deliberately conservative.
    # We should NOT automatically treat every OTP,
    # authentication or insufficient-funds issue as permanent.
    #

    permanent_keywords = [
    "card_declined",
    "card declined",
    "do_not_honor",
    "do not honor",
    "lost_card",
    "stolen_card",
    "expired_card",
    "invalid_card",
    "invalid card",
    "closed_account",
    "closed account",

    # Explicit OTP failure.
    # This represents an unsuccessful authentication attempt
    # and should not be automatically retried.
    "incorrect_otp",
    "incorrect otp",
    ]

    if any(keyword in failure_text for keyword in permanent_keywords):
        return "permanent_failure"

    # ---------------------------------------------------------
    # 3. Unknown / customer-action / ambiguous failures
    # ---------------------------------------------------------
    #
    # These should be handled conservatively by the
    # recovery engine rather than being treated as safe
    # automatic retry candidates.
    #

    return "unknown_failure"


def payment_to_recovery_context(
    payment: dict,
    customer_success_count: int = 0,
    customer_failed_count: int = 0,
    hours_since_last_success: float | None = None,
) -> RecoveryContext:
    """
    Convert a Razorpay payment into our internal RecoveryContext.

    Razorpay amounts are represented in the smallest currency unit.
    For INR, this means paise, so we convert to rupees here.

    If there is no previous successful payment, recency is represented
    as infinity rather than using the failed payment's timestamp.
    """

    amount = payment.get("amount")

    if amount is None:
        raise ValueError("Razorpay payment is missing amount")

    amount_in_rupees = amount / 100

    failure_type = map_failure_type(payment)

    # ---------------------------------------------------------
    # Important safety rule:
    #
    # If there is no previous successful payment, do NOT use
    # the failed payment timestamp as "last success".
    #
    # A customer with no successful history has no successful
    # payment recency signal.
    # ---------------------------------------------------------

    if hours_since_last_success is None:
        hours_since_last_success = float("inf")

    return RecoveryContext(
        amount=amount_in_rupees,
        customer_success_count=customer_success_count,
        customer_failed_count=customer_failed_count,
        failure_type=failure_type,
        hours_since_last_success=hours_since_last_success,
    )