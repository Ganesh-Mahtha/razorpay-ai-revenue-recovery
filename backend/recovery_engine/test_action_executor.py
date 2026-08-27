from backend.recovery_engine.action_executor import execute_recovery_action
from backend.recovery_engine.guardrails import GuardrailDecision


def make_decision(action: str) -> GuardrailDecision:
    return GuardrailDecision(
        action=action,
        title="Test decision",
        confidence="HIGH",
        reason="Test reason",
        guardrail_triggered=False,
        guardrail_reasons=[],
    )


def test_retry_action_is_simulated():
    decision = make_decision("RETRY")

    result = execute_recovery_action(decision)

    assert result.action == "RETRY"
    assert result.status == "SIMULATED"
    assert result.executed is True


def test_retry_with_caution_action_is_simulated():
    decision = make_decision("RETRY_WITH_CAUTION")

    result = execute_recovery_action(decision)

    assert result.action == "RETRY_WITH_CAUTION"
    assert result.status == "SIMULATED"
    assert result.executed is True


def test_human_review_is_not_executed():
    decision = make_decision("HUMAN_REVIEW")

    result = execute_recovery_action(decision)

    assert result.action == "HUMAN_REVIEW"
    assert result.status == "PENDING_REVIEW"
    assert result.executed is False


def test_do_not_retry_is_blocked():
    decision = make_decision("DO_NOT_RETRY")

    result = execute_recovery_action(decision)

    assert result.action == "DO_NOT_RETRY"
    assert result.status == "BLOCKED"
    assert result.executed is False


def test_unknown_action_is_rejected():
    decision = make_decision("UNKNOWN_ACTION")

    result = execute_recovery_action(decision)

    assert result.action == "UNKNOWN_ACTION"
    assert result.status == "REJECTED"
    assert result.executed is False