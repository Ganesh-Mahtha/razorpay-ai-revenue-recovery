from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class AuditTrail:
    """
    Complete, structured audit record for one recovery decision.

    The audit trail records the decision path from payment context
    through AI reasoning, deterministic policy, guardrails, and
    simulated execution.

    This class does NOT call the AI and does NOT influence decisions.
    It is purely an observability / traceability layer.
    """

    audit_id: str
    created_at: str

    # ---------------------------------------------------------
    # PAYMENT CONTEXT
    # ---------------------------------------------------------

    payment_context: Dict[str, Any]

    # ---------------------------------------------------------
    # AI REASONING
    # ---------------------------------------------------------

    ai_assessment: Dict[str, Any]

    # ---------------------------------------------------------
    # DETERMINISTIC POLICY
    # ---------------------------------------------------------

    deterministic_score: Dict[str, Any]
    deterministic_recommendation: Dict[str, Any]

    # ---------------------------------------------------------
    # DECISION ENGINE
    # ---------------------------------------------------------

    final_decision: Dict[str, Any]

    # ---------------------------------------------------------
    # GUARDRAIL
    # ---------------------------------------------------------

    guardrail: Dict[str, Any]

    # ---------------------------------------------------------
    # EXECUTION
    # ---------------------------------------------------------

    execution: Dict[str, Any]


def _to_dict(value: Any) -> Dict[str, Any]:
    """
    Convert a dataclass-like object into a dictionary.

    Falls back safely for unexpected objects so the audit layer
    never becomes a decision-making dependency.
    """

    if value is None:
        return {}

    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)

    if isinstance(value, dict):
        return dict(value)

    return {
        key: getattr(value, key)
        for key in dir(value)
        if not key.startswith("_")
        and not callable(getattr(value, key, None))
    }


def create_audit_trail(
    *,
    audit_id: str,
    amount: float,
    customer_success_count: int,
    customer_failed_count: int,
    failure_type: str,
    hours_since_last_success: float,
    ai_assessment: Any,
    score: Any,
    recommendation: Any,
    decision: Any,
    guardrail: Any,
    execution: Any,
) -> AuditTrail:
    """
    Create a complete audit record for one recovery decision.

    IMPORTANT:

    This function only records what happened.

    It does not:
    - call the AI
    - calculate scores
    - modify recommendations
    - override guardrails
    - execute payments
    """

    return AuditTrail(
        audit_id=audit_id,
        created_at=datetime.now(timezone.utc).isoformat(),

        payment_context={
            "amount": amount,
            "customer_success_count": customer_success_count,
            "customer_failed_count": customer_failed_count,
            "failure_type": failure_type,
            "hours_since_last_success": (
                hours_since_last_success
            ),
        },

        ai_assessment=_to_dict(ai_assessment),

        deterministic_score=_to_dict(score),

        deterministic_recommendation=_to_dict(
            recommendation
        ),

        final_decision=_to_dict(decision),

        guardrail=_to_dict(guardrail),

        execution=_to_dict(execution),
    )


def audit_trail_to_dict(
    audit_trail: AuditTrail,
) -> Dict[str, Any]:
    """
    Convert an AuditTrail into a JSON-serializable dictionary.
    """

    return asdict(audit_trail)


def format_audit_trail(
    audit_trail: AuditTrail,
) -> str:
    """
    Produce a human-readable audit trail for the demo,
    terminal, logs, or future dashboard.
    """

    payment = audit_trail.payment_context
    ai = audit_trail.ai_assessment
    score = audit_trail.deterministic_score
    recommendation = audit_trail.deterministic_recommendation
    decision = audit_trail.final_decision
    guardrail = audit_trail.guardrail
    execution = audit_trail.execution

    lines: List[str] = []

    lines.append("=" * 60)
    lines.append("RECOVERAI AUDIT TRAIL")
    lines.append("=" * 60)

    lines.append("")
    lines.append(f"Audit ID: {audit_trail.audit_id}")
    lines.append(f"Created: {audit_trail.created_at}")

    lines.append("")
    lines.append("1. PAYMENT CONTEXT")
    lines.append("-" * 60)
    lines.append(
        f"Amount: ₹{payment.get('amount', 0):,.2f}"
    )
    lines.append(
        "Successful payments: "
        f"{payment.get('customer_success_count')}"
    )
    lines.append(
        "Failed payments: "
        f"{payment.get('customer_failed_count')}"
    )
    lines.append(
        f"Failure type: {payment.get('failure_type')}"
    )
    lines.append(
        "Hours since last success: "
        f"{payment.get('hours_since_last_success')}"
    )

    lines.append("")
    lines.append("2. AI ASSESSMENT")
    lines.append("-" * 60)
    lines.append(
        f"Diagnosis: {ai.get('diagnosis')}"
    )
    lines.append(
        f"Recoverability: {ai.get('recoverability')}"
    )
    lines.append(
        f"Confidence: {ai.get('confidence')}"
    )
    lines.append(
        f"Recommendation: "
        f"{ai.get('recommended_action')}"
    )
    lines.append(
        f"Reasoning: {ai.get('reasoning')}"
    )

    signals = ai.get("signals", [])

    if signals:
        lines.append("Signals:")
        for signal in signals:
            lines.append(f"  - {signal}")

    lines.append("")
    lines.append("3. DETERMINISTIC POLICY")
    lines.append("-" * 60)
    lines.append(
        f"Score: {score.get('score')}"
    )
    lines.append(
        f"Tier: {score.get('tier')}"
    )
    lines.append(
        f"Recommendation: "
        f"{recommendation.get('action')}"
    )

    lines.append("")
    lines.append("4. DECISION ENGINE")
    lines.append("-" * 60)
    lines.append(
        f"Final decision: "
        f"{decision.get('action')}"
    )
    lines.append(
        f"Confidence: "
        f"{decision.get('confidence')}"
    )
    lines.append(
        f"Reason: "
        f"{decision.get('reason')}"
    )

    lines.append("")
    lines.append("5. GUARDRAIL")
    lines.append("-" * 60)
    lines.append(
        "Triggered: "
        f"{guardrail.get('guardrail_triggered')}"
    )
    lines.append(
        f"Action: {guardrail.get('action')}"
    )
    lines.append(
        f"Reason: {guardrail.get('reason')}"
    )

    guardrail_reasons = guardrail.get(
        "reasons",
        [],
    )

    if guardrail_reasons:
        lines.append("Guardrail reasons:")
        for reason in guardrail_reasons:
            lines.append(f"  - {reason}")

    lines.append("")
    lines.append("6. EXECUTION")
    lines.append("-" * 60)
    lines.append(
        f"Action: {execution.get('action')}"
    )
    lines.append(
        f"Status: {execution.get('status')}"
    )
    lines.append(
        f"Executed: {execution.get('executed')}"
    )
    lines.append(
        f"Message: {execution.get('message')}"
    )

    lines.append("")
    lines.append("=" * 60)
    lines.append("END AUDIT TRAIL")
    lines.append("=" * 60)

    return "\n".join(lines)