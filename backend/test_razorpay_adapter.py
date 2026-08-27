from backend.recovery_engine.razorpay_adapter import (
    map_failure_type,
    payment_to_recovery_context,
)


def test_temporary_failure_is_detected():
    payment = {
        "amount": 849900,
        "error_code": "GATEWAY_ERROR",
        "error_description": "Gateway timeout",
        "error_reason": "timeout",
        "created_at": 1756000000,
    }

    assert map_failure_type(payment) == "temporary_failure"


def test_permanent_failure_is_detected():
    payment = {
        "amount": 50000,
        "error_code": "BAD_REQUEST_ERROR",
        "error_description": "Incorrect OTP",
        "error_reason": "incorrect_otp",
        "created_at": 1756000000,
    }

    assert map_failure_type(payment) == "permanent_failure"


def test_unknown_failure_is_detected():
    payment = {
        "amount": 50000,
        "error_code": "SOME_UNKNOWN_ERROR",
        "error_description": "Something unexpected happened",
        "error_reason": "unknown_reason",
        "created_at": 1756000000,
    }

    assert map_failure_type(payment) == "unknown_failure"


def test_payment_is_converted_to_recovery_context():
    payment = {
        "amount": 849900,
        "error_code": "GATEWAY_ERROR",
        "error_description": "Gateway timeout",
        "error_reason": "timeout",
        "created_at": 1756000000,
    }

    context = payment_to_recovery_context(
        payment,
        customer_success_count=6,
        customer_failed_count=0,
        hours_since_last_success=6,
    )

    assert context.amount == 8499
    assert context.customer_success_count == 6
    assert context.failure_type == "temporary_failure"
    assert context.hours_since_last_success == 6