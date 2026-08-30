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


ALLOWED_LEVELS = {
    "HIGH",
    "MEDIUM",
    "LOW",
}


RETRYABLE_FAILURES = {
    "temporary_failure",
    "bank_timeout",
    "timeout",
    "network_timeout",
    "gateway_timeout",
}


def _build_prompt(
    amount: float,
    customer_success_count: int,
    customer_failed_count: int,
    failure_type: str,
    hours_since_last_success: float,
) -> str:
    return f"""
You are RecoverAI, an AI revenue recovery decision-support
agent for Razorpay payment failures.

Your job is to reason over the COMPLETE payment context and
determine whether a failed payment represents a recoverable
revenue opportunity.

You are NOT allowed to execute payments.

You are NOT the final authority.

Your recommendation will be passed through deterministic
decision logic and safety guardrails before any action can
be executed.

============================================================
PAYMENT CONTEXT
============================================================

Amount: ₹{amount:,.2f}

Customer successful payments:
{customer_success_count}

Customer failed payments:
{customer_failed_count}

Failure type:
{failure_type}

Hours since last successful payment:
{hours_since_last_success}

============================================================
IMPORTANT PRINCIPLE
============================================================

Do not make the recommendation from a single field.

Reason over the COMPLETE context.

Consider:

- failure type
- customer payment history
- historical success/failure balance
- recency of successful activity
- transaction amount
- whether the failure appears isolated or persistent
- uncertainty in the available evidence

You must distinguish between:

1. recoverability
2. confidence
3. recommended intervention

These are NOT the same thing.

A payment can have HIGH recoverability but LOW confidence.

For example:

A temporary failure with recent successful history may be
recoverable, but if the transaction is unusually high-value
or important failure telemetry is missing, confidence may
still be LOW.

============================================================
RECOVERABILITY
============================================================

HIGH:

Use HIGH when multiple independent signals indicate that the
payment is likely recoverable.

Typical examples:

- clearly retryable/transient failure
- several successful historical payments
- low historical failure rate
- recent successful transaction
- failure appears isolated

MEDIUM:

Use MEDIUM when recovery is plausible but evidence is mixed.

Typical examples:

- some successful history but meaningful failures
- temporary failure with older activity
- incomplete evidence
- moderate customer history

LOW:

Use LOW when evidence strongly suggests that recovery is
unlikely or inappropriate.

============================================================
CONFIDENCE
============================================================

HIGH:

Use HIGH when the available evidence is strong, consistent,
and leaves little ambiguity.

MEDIUM:

Use MEDIUM when evidence supports a conclusion but some
uncertainty remains.

LOW:

Use LOW when important information is missing, signals conflict,
or the available context is insufficient for a confident
automated decision.

Do NOT automatically assign HIGH confidence simply because
recoverability is HIGH.

============================================================
ACTION POLICY
============================================================

RETRY:

Recommend RETRY only when ALL of the following are true:

- failure is clearly retryable
- recovery evidence is strong
- customer history is favorable
- recent successful activity supports validity
- failure appears isolated rather than persistent
- confidence is HIGH
- there is no major risk signal requiring caution

RETRY_WITH_CAUTION:

Recommend RETRY_WITH_CAUTION when:

- failure is probably retryable
- recovery is plausible
- but evidence is incomplete or mixed

This is appropriate when:

- transaction value is material
- customer history is mixed
- activity is somewhat old
- confidence is MEDIUM or LOW
- the failure is likely transient but root cause is uncertain

DO_NOT_RETRY:

Recommend DO_NOT_RETRY when:

- failure is clearly permanent
- retry is unlikely to help
- available evidence indicates a non-recoverable situation

HUMAN_REVIEW:

Recommend HUMAN_REVIEW when:

- failure type is unknown
- evidence is insufficient
- signals conflict significantly
- there is not enough information to safely automate recovery

============================================================
IMPORTANT DISTINCTION
============================================================

Do NOT use RETRY_WITH_CAUTION as the default for every
temporary failure.

If the evidence is exceptionally strong and confidence is HIGH,
recommend RETRY.

If the evidence is good but uncertainty remains, recommend
RETRY_WITH_CAUTION.

If evidence is insufficient, recommend HUMAN_REVIEW.

============================================================
EXAMPLES OF REASONING
============================================================

Example A:

temporary failure
+ 10 successful payments
+ 0 failed payments
+ successful payment 1 hour ago
+ ordinary transaction amount
+ HIGH confidence

→ RETRY


Example B:

temporary failure
+ 3 successful payments
+ 1 failed payment
+ successful payment 12 hours ago
+ ₹20,000 transaction
+ LOW confidence

→ RETRY_WITH_CAUTION


Example C:

temporary failure
+ 1 successful payment
+ 5 failed payments
+ last success 72 hours ago
+ mixed evidence
+ MEDIUM confidence

→ RETRY_WITH_CAUTION


Example D:

permanent failure
+ strong customer history

→ DO_NOT_RETRY


Example E:

unknown failure
+ strong customer history

→ HUMAN_REVIEW


Example F:

temporary failure
+ no customer history
+ very old/no recent activity
+ LOW confidence

→ HUMAN_REVIEW

============================================================
SIGNALS
============================================================

Return several signals explaining your reasoning.

Each signal should identify:

- the relevant field
- its value
- whether it supports or weakens recovery
- why it matters

Do not invent information that is not present in the payment
context.

============================================================
OUTPUT FORMAT
============================================================

Return ONLY valid JSON.

Use exactly this structure:

{{
  "diagnosis": "string",

  "recoverability": "HIGH | MEDIUM | LOW",

  "confidence": "HIGH | MEDIUM | LOW",

  "recommended_action": "RETRY | RETRY_WITH_CAUTION | DO_NOT_RETRY | HUMAN_REVIEW",

  "reasoning": "string",

  "signals": [
    {{
      "name": "string",
      "value": "string or number",
      "interpretation": "string"
    }}
  ]
}}

Do not include markdown.

Do not include additional fields.

Never invent customer history, payment facts, failure details,
or telemetry that was not provided.
"""


def assess_payment_with_ai(
    amount: float,
    customer_success_count: int,
    customer_failed_count: int,
    failure_type: str,
    hours_since_last_success: float,
) -> AIRecoveryAssessment:
    """
    Use an LLM to reason about payment recovery potential.

    The AI result is advisory only.

    It must pass through the deterministic decision engine
    and safety guardrails before execution.
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
                    "You are RecoverAI, a conservative fintech "
                    "revenue recovery reasoning agent. "
                    "Return valid JSON only. "
                    "Follow the supplied decision rubric exactly."
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

    # =========================================================
    # Validate action
    # =========================================================

    action = str(
        data.get(
            "recommended_action",
            "HUMAN_REVIEW",
        )
    ).upper()

    if action not in ALLOWED_ACTIONS:
        action = "HUMAN_REVIEW"

    # =========================================================
    # Validate recoverability
    # =========================================================

    recoverability = str(
        data.get(
            "recoverability",
            "LOW",
        )
    ).upper()

    if recoverability not in ALLOWED_LEVELS:
        recoverability = "LOW"

    # =========================================================
    # Validate confidence
    # =========================================================

    confidence = str(
        data.get(
            "confidence",
            "LOW",
        )
    ).upper()

    if confidence not in ALLOWED_LEVELS:
        confidence = "LOW"

    # =========================================================
    # Validate signals
    # =========================================================

    signals = data.get("signals", [])

    if not isinstance(signals, list):
        signals = []

    normalized_signals = []

    for signal in signals:

        if isinstance(signal, dict):

            normalized_signals.append(
                str(signal)
            )

        else:

            normalized_signals.append(
                str(signal)
            )

    # =========================================================
    # Additional local safety normalization
    # =========================================================
    #
    # The model is advisory. We can make the returned assessment
    # more conservative when obvious contradictions exist.
    #
    # These are NOT the final guardrails.
    # The decision engine and guardrails still retain authority.
    # =========================================================

    normalized_failure_type = (
        failure_type.lower()
    )

    if normalized_failure_type == "permanent_failure":

        action = "DO_NOT_RETRY"

    elif normalized_failure_type == "unknown_failure":

        action = "HUMAN_REVIEW"

    # A low-confidence aggressive retry should never leave the
    # AI layer as an unrestricted RETRY recommendation.

    elif (
        action == "RETRY"
        and confidence == "LOW"
    ):

        action = "RETRY_WITH_CAUTION"

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
        signals=normalized_signals,
    )