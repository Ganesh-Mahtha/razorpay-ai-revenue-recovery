from dataclasses import dataclass

from uuid import uuid4

from backend.recovery_engine.audit_trail import (
    AuditTrail,
    create_audit_trail,
)

from backend.recovery_engine.action_executor import (
    RecoveryActionResult,
    execute_recovery_action,
)

from backend.recovery_engine.ai_reasoner import (
    AIRecoveryAssessment,
    assess_payment_with_ai,
)

from backend.recovery_engine.decision_engine import (
    make_recovery_decision,
)

from backend.recovery_engine.guardrails import (
    GuardrailDecision,
    apply_guardrails,
)

from backend.recovery_engine.recommender import (
    RecoveryRecommendation,
    generate_recommendation,
)

from backend.recovery_engine.scorer import (
    RecoveryContext,
    RecoveryScore,
    calculate_recovery_score,
)


# ============================================================
# ACTION PRIORITY
# ============================================================
#
# Lower number = safer / more conservative action.
#
# Kept for backwards compatibility with the existing
# reconciliation tests.
#
# The actual production reconciliation is now handled by
# decision_engine.py.
#

ACTION_PRIORITY = {
    "DO_NOT_RETRY": 0,
    "HUMAN_REVIEW": 1,
    "RETRY_WITH_CAUTION": 2,
    "RETRY": 3,
}


ACTION_TITLES = {
    "RETRY": "Retry payment",
    "RETRY_WITH_CAUTION": "Retry with caution",
    "DO_NOT_RETRY": "Do not retry",
    "HUMAN_REVIEW": "Review payment manually",
}


# ============================================================
# PIPELINE RESULT
# ============================================================


@dataclass
class AIRecoveryPipelineResult:
    """
    Complete result of an AI-assisted recovery decision.

    Pipeline:

        Payment context
              ↓
        AI reasoning
              ↓
        Deterministic scoring
              ↓
        Deterministic recommendation
              ↓
        Decision engine
              ↓
        Safety guardrails
              ↓
        Bounded execution

    AI is advisory.

    The decision engine and guardrails retain final authority.
    """

    ai_assessment: AIRecoveryAssessment
    score: RecoveryScore
    recommendation: RecoveryRecommendation
    reconciled_action: str
    reconciliation_reason: str
    guardrail: GuardrailDecision
    execution: RecoveryActionResult
    audit_trail: AuditTrail


# ============================================================
# LEGACY RECONCILIATION HELPER
# ============================================================
#
# IMPORTANT:
#
# This function is retained because the existing
# test_ai_reconciliation.py tests it directly.
#
# Production pipeline decisions are now handled by
# decision_engine.make_recovery_decision().
#


def _reconcile_recommendations(
    ai_action: str,
    deterministic_action: str,
) -> tuple[str, str]:
    """
    Reconcile AI and deterministic recommendations.

    The more conservative action wins whenever the two
    systems disagree.

    This helper is retained for backwards compatibility
    with the existing reconciliation tests.
    """

    ai_action = str(ai_action).upper()
    deterministic_action = str(deterministic_action).upper()

    # --------------------------------------------------------
    # Invalid AI output
    # --------------------------------------------------------

    if ai_action not in ACTION_PRIORITY:
        ai_action = "HUMAN_REVIEW"

    # --------------------------------------------------------
    # Invalid deterministic output
    # --------------------------------------------------------

    if deterministic_action not in ACTION_PRIORITY:
        deterministic_action = "HUMAN_REVIEW"

    # --------------------------------------------------------
    # Agreement
    # --------------------------------------------------------

    if ai_action == deterministic_action:
        return (
            ai_action,
            "AI and deterministic policy agree on the recovery action.",
        )

    # --------------------------------------------------------
    # Disagreement
    #
    # Lower priority number = more conservative action.
    # --------------------------------------------------------

    if ACTION_PRIORITY[ai_action] < ACTION_PRIORITY[
        deterministic_action
    ]:
        selected_action = ai_action
    else:
        selected_action = deterministic_action

    return (
        selected_action,
        (
            "AI and deterministic policy disagreed. "
            f"AI suggested {ai_action}, while deterministic policy "
            f"suggested {deterministic_action}. "
            f"The more conservative action, {selected_action}, "
            "was selected."
        ),
    )


# ============================================================
# LEGACY RECOMMENDATION BUILDER
# ============================================================
#
# Retained for compatibility with existing code/tests.
# The production pipeline now receives its final recommendation
# directly from decision_engine.py.
#


def _build_reconciled_recommendation(
    action: str,
    ai_assessment: AIRecoveryAssessment,
    deterministic_recommendation: RecoveryRecommendation,
    reconciliation_reason: str,
) -> RecoveryRecommendation:
    """
    Convert a reconciled action into the existing
    RecoveryRecommendation structure.

    Retained for backwards compatibility.
    """

    if action not in ACTION_TITLES:
        action = "HUMAN_REVIEW"

    return RecoveryRecommendation(
        action=action,
        title=ACTION_TITLES[action],
        confidence=ai_assessment.confidence,
        reason=(
            f"{reconciliation_reason} "
            f"AI assessment: {ai_assessment.reasoning}"
        ),
        guardrail_required=(
            action
            in {
                "RETRY",
                "RETRY_WITH_CAUTION",
                "HUMAN_REVIEW",
            }
        ),
    )


# ============================================================
# MAIN AI PIPELINE
# ============================================================


def process_payment_with_ai(
    amount: float,
    customer_success_count: int,
    customer_failed_count: int,
    failure_type: str,
    hours_since_last_success: float,
) -> AIRecoveryPipelineResult:
    """
    Run a payment through the complete RecoverAI pipeline.

    Production decision flow:

        Payment context
              ↓
        AI reasoning
              ↓
        Deterministic scoring
              ↓
        Deterministic recommendation
              ↓
        Decision engine
              ↓
        Safety guardrails
              ↓
        Bounded execution

    AI is advisory only.

    The decision engine determines the final proposed action.
    Guardrails retain final authority over execution.
    """

    # ========================================================
    # 1. AI REASONING
    # ========================================================

    ai_assessment = assess_payment_with_ai(
        amount=amount,
        customer_success_count=customer_success_count,
        customer_failed_count=customer_failed_count,
        failure_type=failure_type,
        hours_since_last_success=hours_since_last_success,
    )

    # ========================================================
    # 2. BUILD DETERMINISTIC RECOVERY CONTEXT
    # ========================================================

    context = RecoveryContext(
        amount=amount,
        customer_success_count=customer_success_count,
        customer_failed_count=customer_failed_count,
        failure_type=failure_type,
        hours_since_last_success=hours_since_last_success,
    )

    # ========================================================
    # 3. CALCULATE DETERMINISTIC RECOVERY SCORE
    # ========================================================

    score = calculate_recovery_score(context)

    # ========================================================
    # 4. GENERATE DETERMINISTIC RECOMMENDATION
    # ========================================================

    recommendation = generate_recommendation(score)

        # ========================================================
    # 5. AI + DETERMINISTIC RECONCILIATION
    # ========================================================
    #
    # This produces the proposed action BEFORE the final
    # safety guardrail is applied.
    #
    # The reconciliation layer is intentionally advisory.
    # Guardrails still have final authority.
    #

    reconciled_action, reconciliation_reason = (
        _reconcile_recommendations(
            ai_action=ai_assessment.recommended_action,
            deterministic_action=recommendation.action,
        )
    )

    # ========================================================
    # 6. DECISION ENGINE
    # ========================================================
    #
    # The decision engine provides the policy-aware decision.
    #
    # This does NOT replace the guardrail layer.
    #

    decision = make_recovery_decision(
        context=context,
        score=score,
        ai_assessment=ai_assessment,
    )

    # ========================================================
    # 7. BUILD GUARDRAIL RECOMMENDATION
    # ========================================================
    #
    # The decision engine's bounded action is passed into
    # the guardrail layer.
    #
    # IMPORTANT:
    #
    # reconciled_action above represents the intermediate
    # AI/deterministic reconciliation.
    #
    # decision.action represents the policy-aware action
    # that is sent toward the safety boundary.
    #

    guardrail_recommendation = RecoveryRecommendation(
        action=decision.action,
        title=decision.title,
        confidence=decision.confidence,
        reason=decision.reason,
        guardrail_required=decision.guardrail_required,
    )

    # ========================================================
    # 8. APPLY SAFETY GUARDRAILS
    # ========================================================
    #
    # Guardrails retain final authority.
    #
    # Example:
    #
    # AI                  -> RETRY
    # Deterministic       -> RETRY_WITH_CAUTION
    # Reconciled          -> RETRY_WITH_CAUTION
    # Decision engine     -> DO_NOT_RETRY
    # Guardrail           -> DO_NOT_RETRY
    #
    # A permanent failure can therefore never reach retry
    # execution.
    #

    guardrail = apply_guardrails(
        context=context,
        recommendation=guardrail_recommendation,
    )

    # ========================================================
    # 9. EXECUTE FINAL BOUNDED DECISION
    # ========================================================

    execution = execute_recovery_action(guardrail)

    audit_trail = create_audit_trail(
        audit_id=f"rec_{uuid4().hex[:12]}",
        amount=amount,
        customer_success_count=customer_success_count,
        customer_failed_count=customer_failed_count,
        failure_type=failure_type,
        hours_since_last_success=hours_since_last_success,
        ai_assessment=ai_assessment,
        score=score,
        recommendation=recommendation,
        decision=decision,
        guardrail=guardrail,
        execution=execution,
    )

    # ========================================================
    # 10. RETURN COMPLETE PIPELINE RESULT
    # ========================================================

    return AIRecoveryPipelineResult(
        ai_assessment=ai_assessment,
        score=score,
        recommendation=recommendation,
        reconciled_action=reconciled_action,
        reconciliation_reason=reconciliation_reason,
        guardrail=guardrail,
        execution=execution,
        audit_trail=audit_trail,
    )