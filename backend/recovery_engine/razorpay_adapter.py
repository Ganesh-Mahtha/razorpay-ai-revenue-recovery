from datetime import datetime, timezone

from scorer import RecoveryContext


def map_failure_type(payment: dict) -> str:
    """
    Convert Razorpay payment failure information
    into our internal failure categories.
    """

    error_reason = (payment.get("error_reason") or "").lower()
    error_code = (payment.get("error_code") or "").lower()
    error_description = (payment.get("error_description") or "").lower()

    failure_text = " ".join(
        [error_reason, error_code, error_description]
    )

    if any(
        keyword in failure_text
        for keyword in [
            "timeout",
            "timed out",
            "network",
            "temporary",
            "server",
            "gateway",
        ]
    ):
        return "temporary_failure"

    if any(
        keyword in failure_text
        for keyword in [
            "incorrect_otp",
            "invalid",
            "declined",
            "authentication",
            "insufficient",
        ]
    ):
        return "permanent_failure"

    return "unknown_failure"


def hours_since_timestamp(timestamp: int) -> float:
    """
    Calculate hours elapsed since a UNIX timestamp.
    """

    created_at = datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    )

    now = datetime.now(timezone.utc)

    return (now - created_at).total_seconds() / 3600


def payment_to_recovery_context(
    payment: dict,
    customer_success_count: int = 0,
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
        failure_type=failure_type,
        hours_since_last_success=hours_since_last_success,
    )