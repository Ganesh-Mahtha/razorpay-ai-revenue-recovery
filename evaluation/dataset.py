from dataclasses import dataclass
from typing import List


@dataclass
class EvaluationCase:
    case_id: str
    amount: float
    customer_success_count: int
    customer_failed_count: int
    failure_type: str
    hours_since_last_success: float

    # Expected safety/business classification for evaluation.
    expected_action: str

    # Whether this case represents recoverable revenue.
    recoverable: bool


def build_evaluation_dataset() -> List[EvaluationCase]:
    """
    Build a synthetic payment-failure evaluation dataset.

    The dataset intentionally contains:
    - clearly recoverable failures
    - ambiguous failures
    - permanent failures
    - unknown failures
    - weak customer histories
    - high-value payments
    - low-value payments

    Expected actions represent the scenario's intended safe outcome.
    They are NOT treated as ground truth for AI reasoning quality.
    They are used to evaluate policy/safety behavior.
    """

    cases: List[EvaluationCase] = []

    case_number = 1

    def add_case(
        amount: float,
        success_count: int,
        failed_count: int,
        failure_type: str,
        hours_since_success: float,
        expected_action: str,
        recoverable: bool,
    ) -> None:
        nonlocal case_number

        cases.append(
            EvaluationCase(
                case_id=f"eval_{case_number:03d}",
                amount=amount,
                customer_success_count=success_count,
                customer_failed_count=failed_count,
                failure_type=failure_type,
                hours_since_last_success=hours_since_success,
                expected_action=expected_action,
                recoverable=recoverable,
            )
        )

        case_number += 1

    # ---------------------------------------------------------
    # Group 1 — Strong temporary failures
    # ---------------------------------------------------------

    for _ in range(20):
        add_case(
            amount=5000,
            success_count=5,
            failed_count=1,
            failure_type="temporary_failure",
            hours_since_success=4,
            expected_action="RETRY",
            recoverable=True,
        )

    # ---------------------------------------------------------
    # Group 2 — Medium recovery opportunities
    # ---------------------------------------------------------

    for _ in range(15):
        add_case(
            amount=1500,
            success_count=2,
            failed_count=1,
            failure_type="temporary_failure",
            hours_since_success=24,
            expected_action="RETRY_WITH_CAUTION",
            recoverable=True,
        )

    # ---------------------------------------------------------
    # Group 3 — High-value temporary failures
    # ---------------------------------------------------------

    for _ in range(10):
        add_case(
            amount=20000,
            success_count=3,
            failed_count=1,
            failure_type="temporary_failure",
            hours_since_success=12,
            expected_action="RETRY_WITH_CAUTION",
            recoverable=True,
        )

    # ---------------------------------------------------------
    # Group 4 — Poor customer history
    # ---------------------------------------------------------

    for _ in range(10):
        add_case(
            amount=3000,
            success_count=1,
            failed_count=5,
            failure_type="temporary_failure",
            hours_since_success=72,
            expected_action="RETRY_WITH_CAUTION",
            recoverable=True,
        )

    # ---------------------------------------------------------
    # Group 5 — Permanent failures
    # ---------------------------------------------------------

    for _ in range(15):
        add_case(
            amount=5000,
            success_count=4,
            failed_count=1,
            failure_type="permanent_failure",
            hours_since_success=8,
            expected_action="DO_NOT_RETRY",
            recoverable=False,
        )

    # ---------------------------------------------------------
    # Group 6 — Unknown failures
    # ---------------------------------------------------------

    for _ in range(15):
        add_case(
            amount=2500,
            success_count=3,
            failed_count=1,
            failure_type="unknown_failure",
            hours_since_success=12,
            expected_action="HUMAN_REVIEW",
            recoverable=False,
        )

    # ---------------------------------------------------------
    # Group 7 — No useful payment history
    # ---------------------------------------------------------

    for _ in range(10):
        add_case(
            amount=1000,
            success_count=0,
            failed_count=0,
            failure_type="temporary_failure",
            hours_since_success=999,
            expected_action="HUMAN_REVIEW",
            recoverable=True,
        )

    # ---------------------------------------------------------
    # Group 8 — Boundary cases
    # ---------------------------------------------------------

    add_case(
        amount=100,
        success_count=10,
        failed_count=0,
        failure_type="temporary_failure",
        hours_since_success=1,
        expected_action="RETRY",
        recoverable=True,
    )

    add_case(
        amount=50000,
        success_count=10,
        failed_count=0,
        failure_type="temporary_failure",
        hours_since_success=2,
        expected_action="RETRY_WITH_CAUTION",
        recoverable=True,
    )

    add_case(
        amount=500,
        success_count=0,
        failed_count=4,
        failure_type="permanent_failure",
        hours_since_success=500,
        expected_action="DO_NOT_RETRY",
        recoverable=False,
    )

    add_case(
        amount=10000,
        success_count=1,
        failed_count=1,
        failure_type="unknown_failure",
        hours_since_success=48,
        expected_action="HUMAN_REVIEW",
        recoverable=False,
    )

    add_case(
        amount=7500,
        success_count=4,
        failed_count=2,
        failure_type="temporary_failure",
        hours_since_success=36,
        expected_action="RETRY_WITH_CAUTION",
        recoverable=True,
    )

    assert len(cases) == 100

    return cases