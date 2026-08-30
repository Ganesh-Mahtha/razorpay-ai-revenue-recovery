from types import SimpleNamespace

from backend.recovery_engine.audit_trail import (
    create_audit_trail,
    audit_trail_to_dict,
    format_audit_trail,
)


def test_audit_trail_records_complete_decision():
    ai = SimpleNamespace(
        diagnosis="Temporary failure",
        recoverability="HIGH",
        confidence="LOW",
        recommended_action="RETRY_WITH_CAUTION",
        reasoning="Controlled retry is appropriate.",
        signals=["temporary failure", "recent success"],
    )

    score = SimpleNamespace(
        score=100,
        tier="HIGH",
        recommended_action="RETRY",
        confidence="HIGH",
        reasons=["Strong recovery evidence"],
    )

    recommendation = SimpleNamespace(
        action="RETRY",
        title="Retry payment",
        confidence="HIGH",
        reason="Strong recovery opportunity.",
        guardrail_required=True,
    )

    decision = SimpleNamespace(
        action="RETRY_WITH_CAUTION",
        title="Retry with caution",
        confidence="LOW",
        reason="Controlled retry is preferred.",
        guardrail_required=True,
    )

    guardrail = SimpleNamespace(
        action="RETRY_WITH_CAUTION",
        title="Retry with caution",
        guardrail_triggered=False,
        reason="No safety rule triggered.",
        reasons=[],
    )

    execution = SimpleNamespace(
        action="RETRY_WITH_CAUTION",
        status="SIMULATED",
        executed=False,
        message="A guarded retry would be initiated.",
    )

    audit = create_audit_trail(
        audit_id="rec_test_001",
        amount=20000,
        customer_success_count=3,
        customer_failed_count=1,
        failure_type="temporary_failure",
        hours_since_last_success=12,
        ai_assessment=ai,
        score=score,
        recommendation=recommendation,
        decision=decision,
        guardrail=guardrail,
        execution=execution,
    )

    assert audit.audit_id == "rec_test_001"

    assert audit.payment_context["amount"] == 20000

    assert (
        audit.ai_assessment["recommended_action"]
        == "RETRY_WITH_CAUTION"
    )

    assert audit.deterministic_score["score"] == 100

    assert (
        audit.deterministic_recommendation["action"]
        == "RETRY"
    )

    assert (
        audit.final_decision["action"]
        == "RETRY_WITH_CAUTION"
    )

    assert (
        audit.guardrail["guardrail_triggered"]
        is False
    )

    assert (
        audit.execution["status"]
        == "SIMULATED"
    )


def test_audit_trail_can_be_serialized():
    audit = create_audit_trail(
        audit_id="rec_test_002",
        amount=20000,
        customer_success_count=3,
        customer_failed_count=1,
        failure_type="permanent_failure",
        hours_since_last_success=12,
        ai_assessment=SimpleNamespace(
            recommended_action="RETRY",
            confidence="HIGH",
        ),
        score=SimpleNamespace(
            score=50,
            tier="MEDIUM",
        ),
        recommendation=SimpleNamespace(
            action="RETRY",
        ),
        decision=SimpleNamespace(
            action="RETRY",
        ),
        guardrail=SimpleNamespace(
            action="DO_NOT_RETRY",
            guardrail_triggered=True,
            reason="Permanent failure.",
        ),
        execution=SimpleNamespace(
            action="DO_NOT_RETRY",
            status="BLOCKED",
            executed=False,
            message="Retry blocked.",
        ),
    )

    data = audit_trail_to_dict(audit)

    assert isinstance(data, dict)
    assert data["audit_id"] == "rec_test_002"
    assert data["guardrail"]["guardrail_triggered"] is True


def test_audit_trail_format_contains_decision_chain():
    audit = create_audit_trail(
        audit_id="rec_test_003",
        amount=20000,
        customer_success_count=3,
        customer_failed_count=1,
        failure_type="permanent_failure",
        hours_since_last_success=12,
        ai_assessment=SimpleNamespace(
            diagnosis="Permanent failure",
            recoverability="LOW",
            confidence="HIGH",
            recommended_action="RETRY",
            reasoning="AI test recommendation.",
            signals=[],
        ),
        score=SimpleNamespace(
            score=50,
            tier="MEDIUM",
        ),
        recommendation=SimpleNamespace(
            action="RETRY",
        ),
        decision=SimpleNamespace(
            action="RETRY",
        ),
        guardrail=SimpleNamespace(
            action="DO_NOT_RETRY",
            guardrail_triggered=True,
            reason="Permanent failure blocked.",
        ),
        execution=SimpleNamespace(
            action="DO_NOT_RETRY",
            status="BLOCKED",
            executed=False,
            message="Retry was blocked.",
        ),
    )

    output = format_audit_trail(audit)

    assert "RECOVERAI AUDIT TRAIL" in output
    assert "AI ASSESSMENT" in output
    assert "DETERMINISTIC POLICY" in output
    assert "DECISION ENGINE" in output
    assert "GUARDRAIL" in output
    assert "EXECUTION" in output
    assert "DO_NOT_RETRY" in output