from datetime import datetime, timezone


def _normalize(value: str | None) -> str:
    """Normalize a customer identifier for comparison."""
    return (value or "").strip().lower()


def payment_belongs_to_customer(
    payment: dict,
    target_payment: dict,
) -> bool:
    """
    Determine whether a historical payment belongs
    to the same customer as the target payment.
    """

    target_email = _normalize(target_payment.get("email"))
    target_contact = _normalize(target_payment.get("contact"))

    payment_email = _normalize(payment.get("email"))
    payment_contact = _normalize(payment.get("contact"))

    # Strongest match: both identifiers agree.
    if target_email and target_contact:
        return (
            payment_email == target_email
            and payment_contact == target_contact
        )

    # Fall back to contact if email is unavailable.
    if target_contact:
        return payment_contact == target_contact

    # Fall back to email if contact is unavailable.
    if target_email:
        return payment_email == target_email

    # Never guess when there is no customer identifier.
    return False


def calculate_customer_history(
    target_payment: dict,
    payments: list[dict],
) -> dict:
    """
    Calculate basic customer payment history
    from a collection of Razorpay payments.
    """

    customer_payments = [
        payment
        for payment in payments
        if payment.get("id") != target_payment.get("id")
        and payment_belongs_to_customer(
            payment,
            target_payment,
        )
    ]

    successful_payments = [
        payment
        for payment in customer_payments
        if payment.get("status") == "captured"
    ]

    failed_payments = [
        payment
        for payment in customer_payments
        if payment.get("status") == "failed"
    ]

    last_success_at = None

    if successful_payments:
        latest_success = max(
            successful_payments,
            key=lambda payment: payment.get("created_at", 0),
        )

        created_at = latest_success.get("created_at")

        if created_at:
            created_at_dt = datetime.fromtimestamp(
                created_at,
                tz=timezone.utc,
            )

            last_success_at = created_at_dt

    hours_since_last_success = None

    if last_success_at:
        now = datetime.now(timezone.utc)

        hours_since_last_success = (
            now - last_success_at
        ).total_seconds() / 3600

    return {
        "customer_payment_count": len(customer_payments),
        "customer_success_count": len(successful_payments),
        "customer_failed_count": len(failed_payments),
        "hours_since_last_success": hours_since_last_success,
    }