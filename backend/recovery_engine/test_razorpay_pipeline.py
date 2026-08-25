from pipeline import process_razorpay_payment


def test_razorpay_payment_flows_through_recovery_pipeline():
    payment = {
        "amount": 849900,
        "error_code": "GATEWAY_ERROR",
        "error_description": "Gateway timeout",
        "error_reason": "timeout",
        "created_at": 1756000000,
    }

    result = process_razorpay_payment(
        payment=payment,
        customer_success_count=6,
        hours_since_last_success=6,
    )

    assert result.diagnosis.recoverability == "HIGH"
    assert result.diagnosis.confidence == "HIGH"

    assert result.score.score == 100
    assert result.score.tier == "HIGH"

    assert result.recommendation.action == "RETRY"
    assert result.recommendation.guardrail_required is True