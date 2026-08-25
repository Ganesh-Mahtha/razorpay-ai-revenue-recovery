from pipeline import process_payment


def test_high_recovery_payment_flows_through_pipeline():
    result = process_payment(
        amount=8499,
        customer_success_count=6,
        failure_type="temporary_failure",
        hours_since_last_success=6,
    )

    assert result.diagnosis.recoverability == "HIGH"
    assert result.diagnosis.confidence == "HIGH"

    assert result.score.score == 100
    assert result.score.tier == "HIGH"

    assert result.recommendation.action == "RETRY"
    assert result.recommendation.confidence == "HIGH"
    assert result.recommendation.guardrail_required is True


def test_permanent_failure_is_not_recommended_for_retry():
    result = process_payment(
        amount=8499,
        customer_success_count=6,
        failure_type="permanent_failure",
        hours_since_last_success=6,
    )

    assert result.diagnosis.recoverability == "LOW"
    assert result.diagnosis.confidence == "HIGH"

    assert result.recommendation.action == "DO_NOT_RETRY"
    assert result.recommendation.guardrail_required is False


def test_uncertain_payment_requires_caution():
    result = process_payment(
        amount=500,
        customer_success_count=0,
        failure_type="unknown_failure",
        hours_since_last_success=72,
    )

    assert result.diagnosis.recoverability == "LOW"
    assert result.diagnosis.confidence == "LOW"

    assert result.recommendation.action == "DO_NOT_RETRY"
    assert result.recommendation.confidence == "LOW"