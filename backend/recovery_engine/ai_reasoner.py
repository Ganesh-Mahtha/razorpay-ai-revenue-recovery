import json
import os
from dataclasses import dataclass
from typing import List

from openai import OpenAI


@dataclass
class AIRecoveryAssessment:
    diagnosis: str
    recoverability: str
    confidence: str
    recommended_action: str
    reasoning: str
    signals: List[str]


ALLOWED_ACTIONS = {
    "RETRY",
    "RETRY_WITH_CAUTION",
    "DO_NOT_RETRY",
    "HUMAN_REVIEW",
}


def _build_prompt(
    amount: float,
    customer_success_count: int,
    customer_failed_count: int,
    failure_type: str,
    hours_since_last_success: float,
) -> str:
    return f"""
You are RecoverAI, a revenue recovery decision-support agent
for Razorpay payment failures.

Your job is to reason about whether a failed payment appears
recoverable and recommend the safest next intervention.

You are NOT allowed to execute payments.
You are NOT the final authority.
Your recommendation will be passed through a deterministic
policy and guardrail layer before any action is allowed.

Payment context:

Amount: ₹{amount:,.2f}
Customer successful payments: {customer_success_count}
Customer failed payments: {customer_failed_count}
Failure type: {failure_type}
Hours since last successful payment: {hours_since_last_success}

Reason over the COMPLETE context rather than relying on a
single field.

Possible actions:

- RETRY
- RETRY_WITH_CAUTION
- DO_NOT_RETRY
- HUMAN_REVIEW

Possible recoverability levels:

- HIGH
- MEDIUM
- LOW

Return a structured assessment containing:

1. diagnosis
2. recoverability
3. confidence
4. recommended_action
5. reasoning
6. signals

The reasoning must explain which payment and customer signals
support the recommendation.

Be conservative when evidence is weak.
Permanent failures should normally not be recommended for retry.
Unknown failures should normally result in HUMAN_REVIEW or
DO_NOT_RETRY.

Never invent customer history or payment facts.
"""


def assess_payment_with_ai(
    amount: float,
    customer_success_count: int,
    customer_failed_count: int,
    failure_type: str,
    hours_since_last_success: float,
) -> AIRecoveryAssessment:
    """
    Use an LLM to reason about recovery potential.

    The result is advisory only. It must pass through the
    deterministic scorer and guardrail system before execution.
    """

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. "
            "Set it before using AI recovery assessment."
        )

    client = OpenAI(api_key=api_key)

    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        input=[
            {
                "role": "system",
                "content": (
                    "You are a conservative fintech revenue "
                    "recovery reasoning agent. "
                    "Return valid JSON only."
                ),
            },
            {
                "role": "user",
                "content": _build_prompt(
                    amount=amount,
                    customer_success_count=customer_success_count,
                    customer_failed_count=customer_failed_count,
                    failure_type=failure_type,
                    hours_since_last_success=hours_since_last_success,
                ),
            },
        ],
    )

    raw_output = response.output_text.strip()

    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "AI recovery assessment returned invalid JSON."
        ) from exc

    action = str(
        data.get("recommended_action", "HUMAN_REVIEW")
    ).upper()

    if action not in ALLOWED_ACTIONS:
        action = "HUMAN_REVIEW"

    recoverability = str(
        data.get("recoverability", "LOW")
    ).upper()

    if recoverability not in {"HIGH", "MEDIUM", "LOW"}:
        recoverability = "LOW"

    confidence = str(
        data.get("confidence", "LOW")
    ).upper()

    if confidence not in {"HIGH", "MEDIUM", "LOW"}:
        confidence = "LOW"

    signals = data.get("signals", [])

    if not isinstance(signals, list):
        signals = []

    return AIRecoveryAssessment(
        diagnosis=str(
            data.get(
                "diagnosis",
                "Insufficient AI evidence.",
            )
        ),
        recoverability=recoverability,
        confidence=confidence,
        recommended_action=action,
        reasoning=str(
            data.get(
                "reasoning",
                "No reasoning provided.",
            )
        ),
        signals=[str(signal) for signal in signals],
    )