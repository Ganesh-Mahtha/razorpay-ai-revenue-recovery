from dataclasses import dataclass

from backend.recovery_engine.action_executor import (
    RecoveryActionResult,
    execute_recovery_action,
)

from backend.recovery_engine.ai_reasoner import (
    AIRecoveryAssessment,
    assess_payment_with_ai,
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


@dataclass
class AIRecoveryPipelineResult:
    """
    Complete result of an AI-assisted recovery decision.

    AI provides contextual reasoning.

    The deterministic scorer provides an independent
    recovery opportunity assessment.

    The reconciliation layer resolves disagreements
    conservatively.

    Guardrails retain final authority over execution.
    """

    ai_assessment: AIRecoveryAssessment
    score: RecoveryScore
    recommendation: RecoveryRecommendation
    reconciled_action: str
    reconciliation_reason: str
    guardrail: GuardrailDecision
    execution: RecoveryActionResult


def _reconcile_recommendations(
    ai_action: str,
    deterministic_action: str,
) -> tuple[str, str]:
    """
    Reconcile AI and deterministic recommendations.

    The safer action wins whenever the two systems disagree.
    """

    ai_action = ai_action.upper()
    deterministic_action = deterministic_action.upper()

    if ai_action not in ACTION_PRIORITY:
        ai_action = "HUMAN_REVIEW"

    if deterministic_action not in ACTION_PRIORITY:
        deterministic_action = "HUMAN_REVIEW"

    if ai_action == deterministic_action:
        return (
            ai_action,
            "AI and deterministic policy agree on the recovery action.",
        )

    if ACTION_PRIORITY[ai_action] < ACTION_PRIORITY[deterministic_action]:
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


def _build_reconciled_recommendation(
    action: str,
    ai_assessment: AIRecoveryAssessment,
    deterministic_recommendation: RecoveryRecommendation,
    reconciliation_reason: str,
) -> RecoveryRecommendation:
    """
    Convert the reconciled action into the existing
    RecoveryRecommendation structure.
    """

    return RecoveryRecommendation(
        action=action,
        title=ACTION_TITLES[action],
        confidence=ai_assessment.confidence,
        reason=(
            f"{reconciliation_reason} "
            f"AI assessment: {ai_assessment.reasoning}"
        ),
        guardrail_required=(
            action in {
                "RETRY",
                "RETRY_WITH_CAUTION",
                "HUMAN_REVIEW",
            }
        ),
    )


def process_payment_with_ai(
    amount: float,
    customer_success_count: int,
    customer_failed_count: int,
    failure_type: str,
    hours_since_last_success: float,
) -> AIRecoveryPipelineResult:
    """
    Run a payment through the complete AI-assisted
    RecoverAI recovery pipeline.

    Flow:

        Payment context
            ↓
        AI reasoning
            ↓
        Deterministic scoring
            ↓
        Deterministic recommendation
            ↓
        AI/policy reconciliation
            ↓
        Safety guardrails
            ↓
        Simulated execution

    AI is advisory.

    Guardrails retain final authority.
    """

    # ---------------------------------------------------------
    # 1. AI reasoning
    # ---------------------------------------------------------

    ai_assessment = assess_payment_with_ai(
        amount=amount,
        customer_success_count=customer_success_count,
        customer_failed_count=customer_failed_count,
        failure_type=failure_type,
        hours_since_last_success=hours_since_last_success,
    )

    # ---------------------------------------------------------
    # 2. Build deterministic recovery context
    # ---------------------------------------------------------

    context = RecoveryContext(
        amount=amount,
        customer_success_count=customer_success_count,
        customer_failed_count=customer_failed_count,
        failure_type=failure_type,
        hours_since_last_success=hours_since_last_success,
    )

    # ---------------------------------------------------------
    # 3. Calculate deterministic recovery score
    # ---------------------------------------------------------

    score = calculate_recovery_score(context)

    # ---------------------------------------------------------
    # 4. Generate deterministic recommendation
    # ---------------------------------------------------------

    recommendation = generate_recommendation(score)

    # ---------------------------------------------------------
    # 5. Reconcile AI and deterministic recommendations
    # ---------------------------------------------------------

    reconciled_action, reconciliation_reason = (
        _reconcile_recommendations(
            ai_action=ai_assessment.recommended_action,
            deterministic_action=recommendation.action,
        )
    )

    # ---------------------------------------------------------
    # 6. Convert reconciliation into existing recommendation
    #    structure
    # ---------------------------------------------------------

    guardrail_recommendation = _build_reconciled_recommendation(
        action=reconciled_action,
        ai_assessment=ai_assessment,
        deterministic_recommendation=recommendation,
        reconciliation_reason=reconciliation_reason,
    )

    # ---------------------------------------------------------
    # 7. Apply deterministic safety guardrails
    # ---------------------------------------------------------

    guardrail = apply_guardrails(
        context=context,
        recommendation=guardrail_recommendation,
    )

    # ---------------------------------------------------------
    # 8. Execute final bounded decision
    # ---------------------------------------------------------

    execution = execute_recovery_action(guardrail)

    return AIRecoveryPipelineResult(
        ai_assessment=ai_assessment,
        score=score,
        recommendation=recommendation,
        reconciled_action=reconciled_action,
        reconciliation_reason=reconciliation_reason,
        guardrail=guardrail,
        execution=execution,
    )