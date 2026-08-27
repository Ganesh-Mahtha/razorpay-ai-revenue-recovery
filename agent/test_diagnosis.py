from diagnosis import diagnose_payment


def test_high_recovery_payment():
    result = diagnose_payment(
        amount=8499,
        customer_success_count=6,
        customer_failed_count=0,
        failure_type="temporary_failure",
        hours_since_last_success=6,
    )

    assert result.recoverability == "HIGH"
    assert result.confidence == "HIGH"
    assert "High-value payment" in result.signals
    assert "Strong successful payment history" in result.signals
    assert "Failure appears temporary" in result.signals
    assert "Recent successful payment" in result.signals


def test_permanent_failure_is_low_recovery():
    result = diagnose_payment(
        amount=8499,
        customer_success_count=6,
        customer_failed_count=0,
        failure_type="permanent_failure",
        hours_since_last_success=6,
    )

    assert result.recoverability == "LOW"
    assert result.confidence == "HIGH"


def test_uncertain_payment_has_low_confidence():
    result = diagnose_payment(
        amount=500,
        customer_success_count=0,
        customer_failed_count=0,
        failure_type="unknown_failure",
        hours_since_last_success=72,
    )

    assert result.recoverability == "LOW"
    assert result.confidence == "LOW"