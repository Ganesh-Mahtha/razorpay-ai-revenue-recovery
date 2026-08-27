from backend.recovery_engine.recommender import RecoveryRecommendation, generate_recommendation
from backend.recovery_engine.scorer import RecoveryScore


def test_high_score_recommends_retry():
    score = RecoveryScore(
        score=85,
        tier="HIGH",
        recommended_action="RETRY",
        confidence="HIGH",
        reasons=["High-value payment"],
    )

    result = generate_recommendation(score)

    assert isinstance(result, RecoveryRecommendation)
    assert result.action == "RETRY"
    assert result.title == "Retry payment"
    assert result.confidence == "HIGH"
    assert result.guardrail_required is True


def test_medium_score_recommends_cautious_retry():
    score = RecoveryScore(
        score=60,
        tier="MEDIUM",
        recommended_action="RETRY_WITH_CAUTION",
        confidence="MEDIUM",
        reasons=["Moderate recovery opportunity"],
    )

    result = generate_recommendation(score)

    assert result.action == "RETRY_WITH_CAUTION"
    assert result.title == "Retry with caution"
    assert result.confidence == "MEDIUM"
    assert result.guardrail_required is True


def test_low_score_does_not_retry():
    score = RecoveryScore(
        score=20,
        tier="LOW",
        recommended_action="DO_NOT_RETRY",
        confidence="LOW",
        reasons=["Weak recovery opportunity"],
    )

    result = generate_recommendation(score)

    assert result.action == "DO_NOT_RETRY"
    assert result.title == "Do not retry"
    assert result.guardrail_required is False


def test_low_confidence_goes_to_human_review():
    score = RecoveryScore(
        score=80,
        tier="HIGH",
        recommended_action="RETRY",
        confidence="LOW",
        reasons=["Conflicting signals"],
    )

    result = generate_recommendation(score)

    assert result.action == "HUMAN_REVIEW"
    assert result.title == "Review payment manually"
    assert result.confidence == "LOW"
    assert result.guardrail_required is True