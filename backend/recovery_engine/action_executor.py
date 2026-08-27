from dataclasses import dataclass

from .guardrails import GuardrailDecision


@dataclass
class RecoveryActionResult:
    action: str
    status: str
    executed: bool
    message: str


def execute_recovery_action(
    decision: GuardrailDecision,
) -> RecoveryActionResult:
    """
    Safely execute a recovery decision in simulation mode.

    This layer does not perform a real payment retry.

    Guardrails have already determined the final allowed action.
    The executor simply translates that final decision into a
    simulated recovery action.

    Supported actions:
        RETRY
        RETRY_WITH_CAUTION
        HUMAN_REVIEW
        DO_NOT_RETRY
    """

    # ---------------------------------------------------------
    # 1. Retry
    # ---------------------------------------------------------

    if decision.action == "RETRY":
        return RecoveryActionResult(
            action="RETRY",
            status="SIMULATED",
            executed=True,
            message="Payment retry would be initiated.",
        )

    # ---------------------------------------------------------
    # 2. Retry with caution
    # ---------------------------------------------------------

    if decision.action == "RETRY_WITH_CAUTION":
        return RecoveryActionResult(
            action="RETRY_WITH_CAUTION",
            status="SIMULATED",
            executed=True,
            message=(
                "A guarded payment retry would be initiated "
                "after applying recovery limits."
            ),
        )

    # ---------------------------------------------------------
    # 3. Human review
    # ---------------------------------------------------------

    if decision.action == "HUMAN_REVIEW":
        return RecoveryActionResult(
            action="HUMAN_REVIEW",
            status="PENDING_REVIEW",
            executed=False,
            message="Payment requires manual review before recovery.",
        )

    # ---------------------------------------------------------
    # 4. Do not retry
    # ---------------------------------------------------------

    if decision.action == "DO_NOT_RETRY":
        return RecoveryActionResult(
            action="DO_NOT_RETRY",
            status="BLOCKED",
            executed=False,
            message="Payment retry was blocked by the recovery policy.",
        )

    # ---------------------------------------------------------
    # 5. Unknown action
    # ---------------------------------------------------------

    return RecoveryActionResult(
        action=decision.action,
        status="REJECTED",
        executed=False,
        message="Unknown recovery action. No action was executed.",
    )