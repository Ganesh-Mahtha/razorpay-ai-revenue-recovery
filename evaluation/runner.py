from typing import Any, Dict, List, Tuple

from backend.recovery_engine.ai_pipeline import (
    process_payment_with_ai,
)

from evaluation.dataset import (
    EvaluationCase,
    build_evaluation_dataset,
)

from evaluation.metrics import (
    EvaluationMetrics,
    calculate_metrics,
    print_metrics,
)


def _case_key(case: EvaluationCase) -> tuple:
    """
    Return the complete payment context used by the AI pipeline.

    Cases with the same context produce the same evaluation input,
    so they can safely reuse the same pipeline result during
    synthetic batch evaluation.
    """

    return (
        case.amount,
        case.customer_success_count,
        case.customer_failed_count,
        case.failure_type,
        case.hours_since_last_success,
    )


def run_evaluation() -> Tuple[
    List[EvaluationCase],
    List[Any],
]:
    """
    Run the complete RecoverAI evaluation dataset.

    IMPORTANT:

    The synthetic dataset intentionally contains repeated scenarios.
    We therefore evaluate each UNIQUE payment context only once.

    This prevents unnecessary duplicate LLM API calls while still
    producing one result for every evaluation case.

    Example:

        100 cases
            ↓
        12 unique contexts
            ↓
        12 AI pipeline executions
            ↓
        results mapped back to all 100 cases
    """

    cases = build_evaluation_dataset()

    results: List[Any] = []

    print("=" * 60)
    print("RECOVERAI BATCH EVALUATION")
    print("=" * 60)

    print(f"Total cases: {len(cases)}")

    # ---------------------------------------------------------
    # Build unique evaluation contexts
    # ---------------------------------------------------------

    unique_cases: Dict[tuple, EvaluationCase] = {}

    for case in cases:
        key = _case_key(case)

        if key not in unique_cases:
            unique_cases[key] = case

    print(
        f"Unique contexts: {len(unique_cases)}"
    )

    print(
        f"AI pipeline calls required: {len(unique_cases)}"
    )

    print(
        f"Duplicate evaluations avoided: "
        f"{len(cases) - len(unique_cases)}"
    )

    print()
    print("Running unique evaluation contexts...")
    print()

    # ---------------------------------------------------------
    # Evaluate each unique context exactly once
    # ---------------------------------------------------------

    result_cache: Dict[tuple, Any] = {}

    for index, case in enumerate(
        unique_cases.values(),
        start=1,
    ):

        key = _case_key(case)

        print(
            f"[{index:02d}/{len(unique_cases)}] "
            f"{case.case_id} | "
            f"{case.failure_type} | "
            f"₹{case.amount:,.2f}"
        )

        try:

            result = process_payment_with_ai(
                amount=case.amount,
                customer_success_count=(
                    case.customer_success_count
                ),
                customer_failed_count=(
                    case.customer_failed_count
                ),
                failure_type=case.failure_type,
                hours_since_last_success=(
                    case.hours_since_last_success
                ),
            )

        except Exception as exc:

            raise RuntimeError(
                f"Evaluation failed for "
                f"{case.case_id}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        result_cache[key] = result

        print(
            f"       Expected: "
            f"{case.expected_action}"
        )

        print(
            f"       AI: "
            f"{result.ai_assessment.recommended_action}"
        )

        print(
            f"       Deterministic: "
            f"{result.recommendation.action}"
        )

        print(
            f"       Final: "
            f"{result.guardrail.action}"
        )

        print()

    # ---------------------------------------------------------
    # Map cached results back to all 100 cases
    # ---------------------------------------------------------

    for case in cases:

        key = _case_key(case)

        if key not in result_cache:
            raise RuntimeError(
                f"Missing cached evaluation result "
                f"for {case.case_id}."
            )

        results.append(
            result_cache[key]
        )

    print(
        f"Mapped {len(results)} results "
        f"back to {len(cases)} evaluation cases."
    )

    print()

    return cases, results


def print_evaluation_header() -> None:
    """
    Print the evaluation methodology.
    """

    print()
    print("=" * 60)
    print("RECOVERAI EVALUATION")
    print("=" * 60)

    print()
    print("Evaluation flow:")

    print("Payment context")
    print("    ↓")
    print("AI reasoning")
    print("    ↓")
    print("Deterministic scoring")
    print("    ↓")
    print("AI / policy reconciliation")
    print("    ↓")
    print("Safety guardrails")
    print("    ↓")
    print("Final bounded decision")

    print()


def main() -> None:
    """
    Run the complete evaluation and print metrics.
    """

    print_evaluation_header()

    cases, results = run_evaluation()

    metrics: EvaluationMetrics = calculate_metrics(
        cases,
        results,
    )

    print_metrics(metrics)


if __name__ == "__main__":
    main()