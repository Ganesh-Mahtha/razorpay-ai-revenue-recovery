from datetime import datetime, timezone

from .scorer import RecoveryContext


def map_failure_type(payment: dict) -> str:
    """
    Convert Razorpay payment failure information
    into our internal failure categories.
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

    # Temporary / infrastructure-related failures
    if any(
        keyword in failure_text
        for keyword in [
            "timeout",
            "timed out",
            "network",
            "temporary",
            "gateway",
            "server",
            "technical",
            "connection",
        ]
    ):
        return "temporary_failure"

    # Customer/payment-method related failures
    if any(
        keyword in failure_text
        for keyword in [
            "incorrect_otp",
            "invalid_otp",
            "otp",
            "authentication",
            "insufficient",
            "declined",
            "card_declined",
            "invalid",
        ]
    ):
        return "permanent_failure"

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
    """

    amount = payment.get("amount")

    if amount is None:
        raise ValueError("Razorpay payment is missing amount")

    amount_in_rupees = amount / 100

    failure_type = map_failure_type(payment)

    if hours_since_last_success is None:
        hours_since_last_success = hours_since_timestamp(
            payment["created_at"]
        )

    return RecoveryContext(
    amount=amount_in_rupees,
    customer_success_count=customer_success_count,
    customer_failed_count=customer_failed_count,
    failure_type=failure_type,
    hours_since_last_success=hours_since_last_success,
    )