from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List


from .dataset import EvaluationCase


RETRY_ACTIONS = {
    "RETRY",
    "RETRY_WITH_CAUTION",
}

SAFE_ACTIONS = {
    "DO_NOT_RETRY",
    "HUMAN_REVIEW",
}


ALL_ACTIONS = [
    "RETRY",
    "RETRY_WITH_CAUTION",
    "DO_NOT_RETRY",
    "HUMAN_REVIEW",
]


@dataclass
class EvaluationMetrics:
    """
    Aggregate metrics for a RecoverAI evaluation run.

    This module measures system behavior.

    It does not make recovery decisions.
    """

    total_cases: int

    # ---------------------------------------------------------
    # Exact action accuracy
    # ---------------------------------------------------------

    exact_action_matches: int
    exact_action_accuracy: float

    ai_exact_matches: int
    ai_exact_accuracy: float

    deterministic_exact_matches: int
    deterministic_exact_accuracy: float

    # ---------------------------------------------------------
    # Per-action classification
    # ---------------------------------------------------------

    action_precision: Dict[str, float]
    action_recall: Dict[str, float]

    # ---------------------------------------------------------
    # Confusion matrix
    # ---------------------------------------------------------

    confusion_matrix: Dict[str, Dict[str, int]]

    # ---------------------------------------------------------
    # AI / deterministic relationship
    # ---------------------------------------------------------

    ai_policy_agreements: int
    ai_policy_disagreements: int
    ai_policy_agreement_rate: float

    ai_decisions_changed: int
    ai_decision_change_rate: float

    disagreement_pairs: Dict[str, int]

    # ---------------------------------------------------------
    # Recovery performance
    # ---------------------------------------------------------

    recoverable_cases: int
    recoverable_retry_opportunities: int
    recovery_recall: float

    non_recoverable_cases: int
    safely_prevented_retries: int
    safety_rate: float

    unsafe_retry_count: int

    # ---------------------------------------------------------
    # AI safety
    # ---------------------------------------------------------

    unsafe_ai_recommendations: int
    unsafe_ai_recommendations_prevented: int
    ai_unsafe_prevention_rate: float

    # ---------------------------------------------------------
    # Guardrails
    # ---------------------------------------------------------

    guardrail_triggered: int
    guardrail_not_triggered: int
    guardrail_trigger_rate: float

    # ---------------------------------------------------------
    # Revenue
    # ---------------------------------------------------------

    total_revenue_at_risk: float
    recoverable_revenue_at_risk: float

    recoverable_revenue_receiving_retry_opportunity: float

    revenue_safely_blocked: float

    revenue_recovery_opportunity_rate: float


def _percent(
    numerator: float,
    denominator: float,
) -> float:
    """
    Safely calculate a percentage.
    """

    if denominator == 0:
        return 0.0

    return (numerator / denominator) * 100


def _get_final_action(result: Any) -> str:
    """
    Extract the final action.

    Guardrail action has final authority over execution.
    """

    return str(
        result.guardrail.action
    ).upper()


def _get_ai_action(result: Any) -> str:
    """
    Extract the AI recommendation.
    """

    return str(
        result.ai_assessment.recommended_action
    ).upper()


def _get_deterministic_action(result: Any) -> str:
    """
    Extract the deterministic recommendation.
    """

    return str(
        result.recommendation.action
    ).upper()


def _build_empty_confusion_matrix() -> Dict[str, Dict[str, int]]:
    """
    Build a complete expected-vs-predicted action matrix.
    """

    return {
        expected: {
            predicted: 0
            for predicted in ALL_ACTIONS
        }
        for expected in ALL_ACTIONS
    }


def calculate_metrics(
    cases: List[EvaluationCase],
    results: List[Any],
) -> EvaluationMetrics:
    """
    Calculate aggregate RecoverAI evaluation metrics.

    `cases` contains expected scenario outcomes.

    `results` contains corresponding AI recovery pipeline
    results.

    The two lists must have identical ordering and length.
    """

    if len(cases) != len(results):
        raise ValueError(
            "Evaluation cases and results must have "
            "the same length."
        )

    total_cases = len(cases)

    if total_cases == 0:
        raise ValueError(
            "Cannot calculate metrics for an empty evaluation."
        )

    # ---------------------------------------------------------
    # Core counters
    # ---------------------------------------------------------

    exact_action_matches = 0
    ai_exact_matches = 0
    deterministic_exact_matches = 0

    ai_policy_agreements = 0
    ai_decisions_changed = 0

    recoverable_cases = 0
    recoverable_retry_opportunities = 0

    non_recoverable_cases = 0
    safely_prevented_retries = 0

    unsafe_retry_count = 0

    unsafe_ai_recommendations = 0
    unsafe_ai_recommendations_prevented = 0

    guardrail_triggered = 0
    guardrail_not_triggered = 0

    # ---------------------------------------------------------
    # Revenue counters
    # ---------------------------------------------------------

    total_revenue_at_risk = 0.0
    recoverable_revenue_at_risk = 0.0
    recoverable_revenue_receiving_retry_opportunity = 0.0
    revenue_safely_blocked = 0.0

    # ---------------------------------------------------------
    # Confusion matrix
    # ---------------------------------------------------------

    confusion_matrix = _build_empty_confusion_matrix()

    # ---------------------------------------------------------
    # Disagreement analysis
    # ---------------------------------------------------------

    disagreement_pairs = Counter()

    # ---------------------------------------------------------
    # Evaluate every case
    # ---------------------------------------------------------

    for case, result in zip(cases, results):

        expected_action = case.expected_action.upper()

        ai_action = _get_ai_action(result)

        deterministic_action = _get_deterministic_action(
            result
        )

        final_action = _get_final_action(result)

        amount = float(case.amount)

        # -----------------------------------------------------
        # Confusion matrix
        # -----------------------------------------------------

        if expected_action not in confusion_matrix:
            confusion_matrix[expected_action] = {
                action: 0
                for action in ALL_ACTIONS
            }

        if final_action not in ALL_ACTIONS:
            for row in confusion_matrix.values():
                row.setdefault(final_action, 0)

        confusion_matrix[expected_action][final_action] += 1

        # -----------------------------------------------------
        # Revenue at risk
        # -----------------------------------------------------

        total_revenue_at_risk += amount

        if case.recoverable:
            recoverable_cases += 1
            recoverable_revenue_at_risk += amount

        else:
            non_recoverable_cases += 1

        # -----------------------------------------------------
        # Final policy accuracy
        # -----------------------------------------------------

        if final_action == expected_action:
            exact_action_matches += 1

        # -----------------------------------------------------
        # AI accuracy
        # -----------------------------------------------------

        if ai_action == expected_action:
            ai_exact_matches += 1

        # -----------------------------------------------------
        # Deterministic accuracy
        # -----------------------------------------------------

        if deterministic_action == expected_action:
            deterministic_exact_matches += 1

        # -----------------------------------------------------
        # AI vs deterministic policy
        # -----------------------------------------------------

        if ai_action == deterministic_action:
            ai_policy_agreements += 1

        else:
            ai_decisions_changed += 1

            disagreement_key = (
                f"{ai_action} -> {deterministic_action}"
            )

            disagreement_pairs[disagreement_key] += 1

        # -----------------------------------------------------
        # Reconciliation change
        # -----------------------------------------------------

        if ai_action != final_action:
            # AI recommendation was changed by reconciliation
            # or by the downstream guardrail layer.
            pass

        # -----------------------------------------------------
        # Guardrails
        # -----------------------------------------------------

        if result.guardrail.guardrail_triggered:
            guardrail_triggered += 1

        else:
            guardrail_not_triggered += 1

        # -----------------------------------------------------
        # Retry opportunity
        # -----------------------------------------------------

        final_retry = final_action in RETRY_ACTIONS

        if final_retry:
            if case.recoverable:
                recoverable_retry_opportunities += 1
                recoverable_revenue_receiving_retry_opportunity += (
                    amount
                )

        # -----------------------------------------------------
        # Recoverable revenue
        # -----------------------------------------------------

        if case.recoverable:

            if final_retry:
                pass

        # -----------------------------------------------------
        # Non-recoverable safety
        # -----------------------------------------------------

        if not case.recoverable:

            if final_retry:
                unsafe_retry_count += 1

            else:
                safely_prevented_retries += 1
                revenue_safely_blocked += amount

        # -----------------------------------------------------
        # AI safety
        # -----------------------------------------------------

        ai_retry = ai_action in RETRY_ACTIONS

        if not case.recoverable and ai_retry:

            unsafe_ai_recommendations += 1

            if not final_retry:
                unsafe_ai_recommendations_prevented += 1

    # ---------------------------------------------------------
    # Derived accuracy metrics
    # ---------------------------------------------------------

    exact_action_accuracy = _percent(
        exact_action_matches,
        total_cases,
    )

    ai_exact_accuracy = _percent(
        ai_exact_matches,
        total_cases,
    )

    deterministic_exact_accuracy = _percent(
        deterministic_exact_matches,
        total_cases,
    )

    # ---------------------------------------------------------
    # Per-action precision / recall
    # ---------------------------------------------------------

    action_precision: Dict[str, float] = {}
    action_recall: Dict[str, float] = {}

    for action in ALL_ACTIONS:

        true_positive = confusion_matrix[action][action]

        predicted_count = sum(
            confusion_matrix[expected][action]
            for expected in confusion_matrix
        )

        actual_count = sum(
            confusion_matrix[action].values()
        )

        action_precision[action] = _percent(
            true_positive,
            predicted_count,
        )

        action_recall[action] = _percent(
            true_positive,
            actual_count,
        )

    # ---------------------------------------------------------
    # AI / policy relationship
    # ---------------------------------------------------------

    ai_policy_disagreements = (
        total_cases - ai_policy_agreements
    )

    ai_policy_agreement_rate = _percent(
        ai_policy_agreements,
        total_cases,
    )

    ai_decision_change_rate = _percent(
        ai_decisions_changed,
        total_cases,
    )

    # ---------------------------------------------------------
    # Recovery recall
    # ---------------------------------------------------------

    recovery_recall = _percent(
        recoverable_retry_opportunities,
        recoverable_cases,
    )

    # ---------------------------------------------------------
    # Safety rate
    # ---------------------------------------------------------

    safety_rate = _percent(
        safely_prevented_retries,
        non_recoverable_cases,
    )

    # ---------------------------------------------------------
    # AI unsafe recommendation prevention
    # ---------------------------------------------------------

    ai_unsafe_prevention_rate = _percent(
        unsafe_ai_recommendations_prevented,
        unsafe_ai_recommendations,
    )

    # ---------------------------------------------------------
    # Guardrail trigger rate
    # ---------------------------------------------------------

    guardrail_trigger_rate = _percent(
        guardrail_triggered,
        total_cases,
    )

    # ---------------------------------------------------------
    # Revenue recovery opportunity
    #
    # IMPORTANT:
    # Only recoverable revenue receiving a retry opportunity
    # is counted here.
    # ---------------------------------------------------------

    revenue_recovery_opportunity_rate = _percent(
        recoverable_revenue_receiving_retry_opportunity,
        recoverable_revenue_at_risk,
    )

    return EvaluationMetrics(
        total_cases=total_cases,

        exact_action_matches=exact_action_matches,
        exact_action_accuracy=exact_action_accuracy,

        ai_exact_matches=ai_exact_matches,
        ai_exact_accuracy=ai_exact_accuracy,

        deterministic_exact_matches=(
            deterministic_exact_matches
        ),
        deterministic_exact_accuracy=(
            deterministic_exact_accuracy
        ),

        action_precision=action_precision,
        action_recall=action_recall,

        confusion_matrix=confusion_matrix,

        ai_policy_agreements=ai_policy_agreements,
        ai_policy_disagreements=(
            ai_policy_disagreements
        ),
        ai_policy_agreement_rate=(
            ai_policy_agreement_rate
        ),

        ai_decisions_changed=ai_decisions_changed,
        ai_decision_change_rate=(
            ai_decision_change_rate
        ),

        disagreement_pairs=dict(
            disagreement_pairs
        ),

        recoverable_cases=recoverable_cases,
        recoverable_retry_opportunities=(
            recoverable_retry_opportunities
        ),
        recovery_recall=recovery_recall,

        non_recoverable_cases=non_recoverable_cases,
        safely_prevented_retries=(
            safely_prevented_retries
        ),
        safety_rate=safety_rate,

        unsafe_retry_count=unsafe_retry_count,

        unsafe_ai_recommendations=(
            unsafe_ai_recommendations
        ),
        unsafe_ai_recommendations_prevented=(
            unsafe_ai_recommendations_prevented
        ),
        ai_unsafe_prevention_rate=(
            ai_unsafe_prevention_rate
        ),

        guardrail_triggered=guardrail_triggered,
        guardrail_not_triggered=guardrail_not_triggered,
        guardrail_trigger_rate=(
            guardrail_trigger_rate
        ),

        total_revenue_at_risk=(
            total_revenue_at_risk
        ),
        recoverable_revenue_at_risk=(
            recoverable_revenue_at_risk
        ),
        recoverable_revenue_receiving_retry_opportunity=(
            recoverable_revenue_receiving_retry_opportunity
        ),
        revenue_safely_blocked=(
            revenue_safely_blocked
        ),
        revenue_recovery_opportunity_rate=(
            revenue_recovery_opportunity_rate
        ),
    )


def print_metrics(
    metrics: EvaluationMetrics,
) -> None:
    """
    Print a concise but comprehensive RecoverAI
    evaluation report.
    """

    print()
    print("=" * 60)
    print("RECOVERAI EVALUATION REPORT")
    print("=" * 60)

    # ---------------------------------------------------------
    # Accuracy
    # ---------------------------------------------------------

    print()
    print("1. ACTION ACCURACY")
    print("-" * 60)

    print(
        f"Final policy accuracy: "
        f"{metrics.exact_action_matches}/"
        f"{metrics.total_cases} "
        f"({metrics.exact_action_accuracy:.1f}%)"
    )

    print(
        f"AI accuracy: "
        f"{metrics.ai_exact_matches}/"
        f"{metrics.total_cases} "
        f"({metrics.ai_exact_accuracy:.1f}%)"
    )

    print(
        f"Deterministic accuracy: "
        f"{metrics.deterministic_exact_matches}/"
        f"{metrics.total_cases} "
        f"({metrics.deterministic_exact_accuracy:.1f}%)"
    )

    # ---------------------------------------------------------
    # Per-action metrics
    # ---------------------------------------------------------

    print()
    print("2. PER-ACTION PRECISION / RECALL")
    print("-" * 60)

    for action in ALL_ACTIONS:

        print(
            f"{action:<22} "
            f"precision={metrics.action_precision[action]:5.1f}% "
            f"recall={metrics.action_recall[action]:5.1f}%"
        )

    # ---------------------------------------------------------
    # Confusion matrix
    # ---------------------------------------------------------

    print()
    print("3. CONFUSION MATRIX")
    print("-" * 60)

    header = (
        f"{'Expected':<22}"
        + "".join(
            f"{action:<20}"
            for action in ALL_ACTIONS
        )
    )

    print(header)

    for expected in ALL_ACTIONS:

        row = f"{expected:<22}"

        for predicted in ALL_ACTIONS:
            row += (
                f"{metrics.confusion_matrix[expected][predicted]:<20}"
            )

        print(row)

    # ---------------------------------------------------------
    # AI / deterministic relationship
    # ---------------------------------------------------------

    print()
    print("4. AI / DETERMINISTIC POLICY")
    print("-" * 60)

    print(
        f"Agreements: "
        f"{metrics.ai_policy_agreements} "
        f"({metrics.ai_policy_agreement_rate:.1f}%)"
    )

    print(
        f"Disagreements: "
        f"{metrics.ai_policy_disagreements} "
        f"({100 - metrics.ai_policy_agreement_rate:.1f}%)"
    )

    print(
        f"AI decisions changed downstream: "
        f"{metrics.ai_decisions_changed} "
        f"({metrics.ai_decision_change_rate:.1f}%)"
    )

    if metrics.disagreement_pairs:

        print()
        print("Disagreement pairs:")

        for pair, count in sorted(
            metrics.disagreement_pairs.items()
        ):
            print(
                f"  {pair}: {count}"
            )

    # ---------------------------------------------------------
    # Recovery
    # ---------------------------------------------------------

    print()
    print("5. RECOVERY PERFORMANCE")
    print("-" * 60)

    print(
        f"Recoverable cases: "
        f"{metrics.recoverable_cases}"
    )

    print(
        f"Recoverable cases receiving retry opportunity: "
        f"{metrics.recoverable_retry_opportunities}"
    )

    print(
        f"Recovery recall: "
        f"{metrics.recovery_recall:.1f}%"
    )

    # ---------------------------------------------------------
    # Safety
    # ---------------------------------------------------------

    print()
    print("6. SAFETY")
    print("-" * 60)

    print(
        f"Non-recoverable cases: "
        f"{metrics.non_recoverable_cases}"
    )

    print(
        f"Safely prevented automatic retries: "
        f"{metrics.safely_prevented_retries}"
    )

    print(
        f"Safety rate: "
        f"{metrics.safety_rate:.1f}%"
    )

    print(
        f"UNSAFE FINAL RETRIES: "
        f"{metrics.unsafe_retry_count}"
    )

    # ---------------------------------------------------------
    # AI safety value
    # ---------------------------------------------------------

    print()
    print("7. AI SAFETY VALUE")
    print("-" * 60)

    print(
        f"Unsafe AI retry recommendations: "
        f"{metrics.unsafe_ai_recommendations}"
    )

    print(
        f"Unsafe AI recommendations prevented: "
        f"{metrics.unsafe_ai_recommendations_prevented}"
    )

    print(
        f"AI unsafe-recommendation prevention rate: "
        f"{metrics.ai_unsafe_prevention_rate:.1f}%"
    )

    # ---------------------------------------------------------
    # Guardrails
    # ---------------------------------------------------------

    print()
    print("8. GUARDRAILS")
    print("-" * 60)

    print(
        f"Triggered: "
        f"{metrics.guardrail_triggered}"
    )

    print(
        f"Not triggered: "
        f"{metrics.guardrail_not_triggered}"
    )

    print(
        f"Trigger rate: "
        f"{metrics.guardrail_trigger_rate:.1f}%"
    )

    # ---------------------------------------------------------
    # Revenue
    # ---------------------------------------------------------

    print()
    print("9. REVENUE IMPACT")
    print("-" * 60)

    print(
        f"Total revenue at risk: "
        f"₹{metrics.total_revenue_at_risk:,.2f}"
    )

    print(
        f"Recoverable revenue at risk: "
        f"₹{metrics.recoverable_revenue_at_risk:,.2f}"
    )

    print(
        f"Recoverable revenue receiving retry opportunity: "
        f"₹{metrics.recoverable_revenue_receiving_retry_opportunity:,.2f}"
    )

    print(
        f"Revenue safely blocked: "
        f"₹{metrics.revenue_safely_blocked:,.2f}"
    )

    print(
        f"Revenue recovery opportunity rate: "
        f"{metrics.revenue_recovery_opportunity_rate:.1f}%"
    )

    print()
    print("=" * 60)
    print("END OF EVALUATION REPORT")
    print("=" * 60)