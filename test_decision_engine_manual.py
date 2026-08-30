from backend.recovery_engine.ai_reasoner import (
    AIRecoveryAssessment,
)

from backend.recovery_engine.decision_engine import (
    make_recovery_decision,
)

from backend.recovery_engine.scorer import (
    RecoveryContext,
    calculate_recovery_score,
)


def run_case(
    name,
    amount,
    success_count,
    failed_count,
    failure_type,
    hours_since_success,
    ai_action,
    ai_recoverability,
    ai_confidence,
):
    print()
    print("=" * 60)
    print(name)
    print("=" * 60)

    context = RecoveryContext(
        amount=amount,
        customer_success_count=success_count,
        customer_failed_count=failed_count,
        failure_type=failure_type,
        hours_since_last_success=hours_since_success,
    )

    score = calculate_recovery_score(context)

    ai = AIRecoveryAssessment(
        diagnosis="Manual test assessment",
        recoverability=ai_recoverability,
        confidence=ai_confidence,
        recommended_action=ai_action,
        reasoning="Manual decision-engine test.",
        signals=[],
    )

    decision = make_recovery_decision(
        context=context,
        score=score,
        ai_assessment=ai,
    )

    print("Failure type:", failure_type)
    print("Score:", score.score)
    print("Score tier:", score.tier)

    print("AI action:", ai.recommended_action)
    print("AI recoverability:", ai.recoverability)
    print("AI confidence:", ai.confidence)

    print("FINAL DECISION:", decision.action)
    print("REASON:", decision.reason)

    return decision


# ============================================================
# 1. Strong temporary failure
# ============================================================

decision = run_case(
    name="CASE 1 — Strong temporary failure",
    amount=5000,
    success_count=5,
    failed_count=1,
    failure_type="temporary_failure",
    hours_since_success=4,
    ai_action="RETRY",
    ai_recoverability="HIGH",
    ai_confidence="HIGH",
)

assert decision.action == "RETRY"


# ============================================================
# 2. High-value temporary failure
# ============================================================

decision = run_case(
    name="CASE 2 — High-value temporary failure",
    amount=20000,
    success_count=3,
    failed_count=1,
    failure_type="temporary_failure",
    hours_since_success=12,
    ai_action="RETRY_WITH_CAUTION",
    ai_recoverability="HIGH",
    ai_confidence="LOW",
)

assert decision.action == "RETRY_WITH_CAUTION"


# ============================================================
# 3. Poor customer history
# ============================================================

decision = run_case(
    name="CASE 3 — Poor customer history",
    amount=3000,
    success_count=1,
    failed_count=5,
    failure_type="temporary_failure",
    hours_since_success=72,
    ai_action="RETRY_WITH_CAUTION",
    ai_recoverability="MEDIUM",
    ai_confidence="MEDIUM",
)

assert decision.action == "RETRY_WITH_CAUTION"


# ============================================================
# 4. Permanent failure
# ============================================================

decision = run_case(
    name="CASE 4 — Permanent failure",
    amount=5000,
    success_count=4,
    failed_count=1,
    failure_type="permanent_failure",
    hours_since_success=8,
    ai_action="RETRY",
    ai_recoverability="HIGH",
    ai_confidence="HIGH",
)

assert decision.action == "DO_NOT_RETRY"


# ============================================================
# 5. Unknown failure
# ============================================================

decision = run_case(
    name="CASE 5 — Unknown failure",
    amount=2500,
    success_count=3,
    failed_count=1,
    failure_type="unknown_failure",
    hours_since_success=12,
    ai_action="RETRY",
    ai_recoverability="HIGH",
    ai_confidence="HIGH",
)

assert decision.action == "HUMAN_REVIEW"


print()
print("=" * 60)
print("ALL 5 DECISION ENGINE TESTS PASSED")
print("=" * 60)