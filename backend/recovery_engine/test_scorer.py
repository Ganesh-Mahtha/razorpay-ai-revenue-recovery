from scorer import RecoveryContext, calculate_recovery_score


def test_high_value_retryable_payment():
    context = RecoveryContext(
        amount=8499,
        customer_success_count=6,
        customer_failed_count=0,
        failure_type="temporary_failure",
        hours_since_last_success=6,
    )

    result = calculate_recovery_score(context)

    assert result.score == 100
    assert result.tier == "HIGH"
    assert result.recommended_action == "RETRY"
    assert result.confidence == "HIGH"


def test_medium_recovery_opportunity():
    context = RecoveryContext(
        amount=1500,
        customer_success_count=2,
        customer_failed_count=0,
        failure_type="bank_timeout",
        hours_since_last_success=48,
    )

    result = calculate_recovery_score(context)

    assert result.score == 74
    assert result.tier == "MEDIUM"
    assert result.recommended_action == "RETRY_WITH_CAUTION"


def test_low_recovery_opportunity():
    context = RecoveryContext(
        amount=500,
        customer_success_count=0,
        customer_failed_count=0,
        failure_type="permanent_failure",
        hours_since_last_success=120,
    )

    result = calculate_recovery_score(context)

    assert result.score == 0
    assert result.tier == "LOW"
    assert result.recommended_action == "DO_NOT_RETRY"


def test_reasons_are_generated():
    context = RecoveryContext(
        amount=8499,
        customer_success_count=6,
        customer_failed_count=0,
        failure_type="temporary_failure",
        hours_since_last_success=6,
    )

    result = calculate_recovery_score(context)

    assert "High-value payment" in result.reasons
    assert "Strong successful payment history" in result.reasons
    assert "Failure appears retryable" in result.reasons
    assert "Recent successful payment" in result.reasons