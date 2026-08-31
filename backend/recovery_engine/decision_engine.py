from dataclasses import dataclass

from .ai_reasoner import AIRecoveryAssessment
from .scorer import RecoveryContext, RecoveryScore


ACTION_TITLES = {
    "RETRY": "Retry payment",
    "RETRY_WITH_CAUTION": "Retry with caution",
    "DO_NOT_RETRY": "Do not retry",
    "HUMAN_REVIEW": "Review payment manually",
}


RETRYABLE_FAILURES = {
    "temporary_failure",
    "bank_timeout",
    "timeout",
    "network_timeout",
    "gateway_timeout",
}


VALID_ACTIONS = {
    "RETRY",
    "RETRY_WITH_CAUTION",
    "DO_NOT_RETRY",
    "HUMAN_REVIEW",
}


@dataclass
class DecisionResult:
    """
    Final recovery decision proposed by the decision engine.

    AI provides contextual reasoning.

    The deterministic scorer provides independent evidence.

    The decision engine combines both while enforcing
    hard safety boundaries.

    This layer does not execute payments.
    """

    action: str
    title: str
    confidence: str
    reason: str
    guardrail_required: bool


def _normalise_action(action: str) -> str:
    """
    Normalise an AI action.

    Unknown or malformed actions are converted into
    HUMAN_REVIEW rather than being trusted.
    """

    action = str(action).upper()

    if action not in VALID_ACTIONS:
        return "HUMAN_REVIEW"

    return action


def make_recovery_decision(
    context: RecoveryContext,
    score: RecoveryScore,
    ai_assessment: AIRecoveryAssessment,
) -> DecisionResult:
    """
    Combine AI reasoning with deterministic safety evidence.

    Decision hierarchy:

        1. Hard safety boundaries
        2. Missing customer evidence
        3. AI-led recovery decision
        4. Deterministic safety constraints
        5. Defensive fallback

    Important design principle:

        AI = recovery intelligence

        Deterministic logic = safety constraints

    The AI cannot override permanent or unknown failure
    boundaries.
    """

    failure_type = str(
        context.failure_type
    ).lower()

    ai_action = _normalise_action(
        ai_assessment.recommended_action
    )

    ai_confidence = str(
        ai_assessment.confidence
    ).upper()

    ai_recoverability = str(
        ai_assessment.recoverability
    ).upper()

    # =========================================================
    # 1. HARD SAFETY BOUNDARIES
    # =========================================================

    # ---------------------------------------------------------
    # Retry stopping rule
    # ---------------------------------------------------------
    #
    # A payment must not be automatically retried more than
    # once. This is a deterministic safety boundary and cannot
    # be overridden by the AI.
    #

    if context.retry_count >= 1:

        return DecisionResult(
            action="HUMAN_REVIEW",
            title=ACTION_TITLES["HUMAN_REVIEW"],
            confidence="HIGH",
            reason=(
                "The payment has already received an automated "
                "retry attempt. The retry limit has been reached, "
                "so another automated retry is not allowed."
            ),
            guardrail_required=True,
        )

    # ---------------------------------------------------------
    # Permanent failure
    # ---------------------------------------------------------

    if failure_type == "permanent_failure":

        return DecisionResult(
            action="DO_NOT_RETRY",
            title=ACTION_TITLES["DO_NOT_RETRY"],
            confidence="HIGH",
            reason=(
                "The payment has a permanent failure classification. "
                "AI recommendations cannot override this safety boundary."
            ),
            guardrail_required=False,
        )

    # ---------------------------------------------------------
    # Unknown failure
    # ---------------------------------------------------------

    if failure_type == "unknown_failure":

        return DecisionResult(
            action="HUMAN_REVIEW",
            title=ACTION_TITLES["HUMAN_REVIEW"],
            confidence="LOW",
            reason=(
                "The failure type is unknown, so automated recovery "
                "is not sufficiently safe without additional evidence."
            ),
            guardrail_required=True,
        )

    # =========================================================
    # 2. CUSTOMER EVIDENCE
    # =========================================================

    total_customer_payments = (
        context.customer_success_count
        + context.customer_failed_count
    )

    # No customer history + low AI confidence remains a
    # human-review case.

    if (
        total_customer_payments == 0
        and ai_confidence == "LOW"
    ):

        return DecisionResult(
            action="HUMAN_REVIEW",
            title=ACTION_TITLES["HUMAN_REVIEW"],
            confidence="LOW",
            reason=(
                "There is no previous customer payment history "
                "and AI confidence is low. Additional evidence "
                "is required before automated recovery."
            ),
            guardrail_required=True,
        )

    # =========================================================
    # 3. NON-RETRYABLE FAILURE TYPES
    # =========================================================

    # Any failure type outside the explicitly retryable set
    # should not receive an automated retry.

    if failure_type not in RETRYABLE_FAILURES:

        return DecisionResult(
            action="HUMAN_REVIEW",
            title=ACTION_TITLES["HUMAN_REVIEW"],
            confidence="LOW",
            reason=(
                "The failure type is not explicitly classified "
                "as retryable. Human review is required before "
                "automated recovery."
            ),
            guardrail_required=True,
        )

    # =========================================================
    # 4. AI-LED RETRY DECISION
    # =========================================================
    #
    # At this point:
    #
    # - failure is known
    # - failure is retryable
    # - permanent failures are excluded
    # - unknown failures are excluded
    #
    # Therefore the AI can act as the primary recovery reasoner.
    #

    # ---------------------------------------------------------
    # AI says DO_NOT_RETRY
    # ---------------------------------------------------------

    if ai_action == "DO_NOT_RETRY":

        return DecisionResult(
            action="DO_NOT_RETRY",
            title=ACTION_TITLES["DO_NOT_RETRY"],
            confidence=ai_confidence,
            reason=(
                "AI does not identify sufficient recovery potential "
                "for an automated retry."
            ),
            guardrail_required=False,
        )

    # ---------------------------------------------------------
    # AI says HUMAN_REVIEW
    # ---------------------------------------------------------

    if ai_action == "HUMAN_REVIEW":

        return DecisionResult(
            action="HUMAN_REVIEW",
            title=ACTION_TITLES["HUMAN_REVIEW"],
            confidence=ai_confidence,
            reason=(
                "AI recommends human review rather than automated "
                "recovery."
            ),
            guardrail_required=True,
        )

    # =========================================================
    # 5. AI REQUESTS RETRY WITH CAUTION
    # =========================================================

    if ai_action == "RETRY_WITH_CAUTION":

        return DecisionResult(
            action="RETRY_WITH_CAUTION",
            title=ACTION_TITLES["RETRY_WITH_CAUTION"],
            confidence=ai_confidence,
            reason=(
                "AI identifies a potentially recoverable payment "
                "but recommends a controlled retry rather than "
                "an aggressive retry."
            ),
            guardrail_required=True,
        )

    # =========================================================
    # 6. AI REQUESTS AGGRESSIVE RETRY
    # =========================================================

    if ai_action == "RETRY":

        # -----------------------------------------------------
        # High-value payments receive an automatic downgrade
        # to controlled retry.
        # -----------------------------------------------------

        if context.amount >= 20000:

            return DecisionResult(
                action="RETRY_WITH_CAUTION",
                title=ACTION_TITLES["RETRY_WITH_CAUTION"],
                confidence=ai_confidence,
                reason=(
                    "AI identifies a recoverable payment, but the "
                    "transaction value is material. The aggressive "
                    "retry is therefore downgraded to a controlled retry."
                ),
                guardrail_required=True,
            )

        # -----------------------------------------------------
        # Low-confidence aggressive AI recommendations should
        # never become unrestricted retries.
        # -----------------------------------------------------

        if ai_confidence == "LOW":

            return DecisionResult(
                action="RETRY_WITH_CAUTION",
                title=ACTION_TITLES["RETRY_WITH_CAUTION"],
                confidence="LOW",
                reason=(
                    "AI recommends retrying, but confidence is low. "
                    "A controlled retry is safer than an aggressive retry."
                ),
                guardrail_required=True,
            )

        # -----------------------------------------------------
        # Medium recoverability should use controlled retry.
        # -----------------------------------------------------

        if ai_recoverability == "MEDIUM":

            return DecisionResult(
                action="RETRY_WITH_CAUTION",
                title=ACTION_TITLES["RETRY_WITH_CAUTION"],
                confidence=ai_confidence,
                reason=(
                    "AI identifies moderate recovery potential. "
                    "A controlled retry is preferred over an aggressive retry."
                ),
                guardrail_required=True,
            )

        # -----------------------------------------------------
        # High-confidence + high-recoverability retryable
        # payment can proceed as RETRY.
        # -----------------------------------------------------

        if (
            ai_confidence == "HIGH"
            and ai_recoverability == "HIGH"
        ):

            return DecisionResult(
                action="RETRY",
                title=ACTION_TITLES["RETRY"],
                confidence="HIGH",
                reason=(
                    "AI identifies a strong recovery opportunity "
                    "with high confidence for a known retryable failure."
                ),
                guardrail_required=True,
            )

        # -----------------------------------------------------
        # Defensive fallback.
        # -----------------------------------------------------

        return DecisionResult(
            action="RETRY_WITH_CAUTION",
            title=ACTION_TITLES["RETRY_WITH_CAUTION"],
            confidence=ai_confidence,
            reason=(
                "AI recommends retry, but the available evidence "
                "does not justify an unrestricted retry."
            ),
            guardrail_required=True,
        )

    # =========================================================
    # 7. DEFENSIVE FALLBACK
    # =========================================================

    return DecisionResult(
        action="HUMAN_REVIEW",
        title=ACTION_TITLES["HUMAN_REVIEW"],
        confidence="LOW",
        reason=(
            "RecoverAI could not establish sufficient evidence "
            "for a safe automated recovery decision."
        ),
        guardrail_required=True,
    )