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


context = RecoveryContext(
    amount=1000,
    customer_success_count=0,
    customer_failed_count=0,
    failure_type="temporary_failure",
    hours_since_last_success=999,
)

score = calculate_recovery_score(context)

ai = AIRecoveryAssessment(
    diagnosis="Temporary failure with insufficient customer history.",
    recoverability="MEDIUM",
    confidence="LOW",
    recommended_action="RETRY_WITH_CAUTION",
    reasoning="There is insufficient customer history to justify automated recovery.",
    signals=[],
)

decision = make_recovery_decision(
    context=context,
    score=score,
    ai_assessment=ai,
)

print("Score:", score.score)
print("Tier:", score.tier)
print("AI:", ai.recommended_action)
print("AI confidence:", ai.confidence)
print("Final decision:", decision.action)
print("Reason:", decision.reason)

assert decision.action == "HUMAN_REVIEW"

print()
print("NO-HISTORY TEST PASSED")