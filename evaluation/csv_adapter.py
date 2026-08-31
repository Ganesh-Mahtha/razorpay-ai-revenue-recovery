import csv
import io
from typing import List

from evaluation.dataset import EvaluationCase


ALLOWED_FAILURE_TYPES = {
    "temporary_failure",
    "permanent_failure",
    "unknown_failure",
}

ALLOWED_ACTIONS = {
    "RETRY",
    "RETRY_WITH_CAUTION",
    "DO_NOT_RETRY",
    "HUMAN_REVIEW",
}

REQUIRED_COLUMNS = {
    "case_id",
    "amount",
    "customer_success_count",
    "customer_failed_count",
    "failure_type",
    "hours_since_last_success",
    "expected_action",
    "recoverable",
}


def _parse_bool(value: str, row_number: int) -> bool:
    normalized = value.strip().lower()

    if normalized in {"true", "1", "yes"}:
        return True

    if normalized in {"false", "0", "no"}:
        return False

    raise ValueError(
        f"Row {row_number}: recoverable must be "
        f"true/false, 1/0, or yes/no."
    )


def _parse_float(
    value: str,
    field: str,
    row_number: int,
) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Row {row_number}: {field} must be numeric."
        ) from exc

    if parsed < 0:
        raise ValueError(
            f"Row {row_number}: {field} cannot be negative."
        )

    return parsed


def _parse_int(
    value: str,
    field: str,
    row_number: int,
) -> int:
    try:
        parsed_float = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Row {row_number}: {field} must be an integer."
        ) from exc

    if not parsed_float.is_integer():
        raise ValueError(
            f"Row {row_number}: {field} must be an integer."
        )

    parsed = int(parsed_float)

    if parsed < 0:
        raise ValueError(
            f"Row {row_number}: {field} cannot be negative."
        )

    return parsed


def parse_evaluation_csv(
    content: bytes,
) -> List[EvaluationCase]:
    """
    Parse a RecoverAI evaluation CSV into EvaluationCase objects.

    Expected columns:

        case_id
        amount
        customer_success_count
        customer_failed_count
        failure_type
        hours_since_last_success
        expected_action
        recoverable
    """

    if not content:
        raise ValueError("The uploaded CSV is empty.")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "The CSV must be UTF-8 encoded."
        ) from exc

    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise ValueError(
            "The CSV must contain a header row."
        )

    columns = {
        column.strip()
        for column in reader.fieldnames
        if column
    }

    missing = REQUIRED_COLUMNS - columns

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(sorted(missing))
        )

    cases: List[EvaluationCase] = []

    for row_number, row in enumerate(reader, start=2):

        def value(field: str) -> str:
            raw = row.get(field)

            if raw is None:
                raise ValueError(
                    f"Row {row_number}: missing value "
                    f"for {field}."
                )

            return raw.strip()

        case_id = value("case_id")

        if not case_id:
            raise ValueError(
                f"Row {row_number}: case_id cannot be empty."
            )

        amount = _parse_float(
            value("amount"),
            "amount",
            row_number,
        )

        customer_success_count = _parse_int(
            value("customer_success_count"),
            "customer_success_count",
            row_number,
        )

        customer_failed_count = _parse_int(
            value("customer_failed_count"),
            "customer_failed_count",
            row_number,
        )

        failure_type = value(
            "failure_type"
        ).lower()

        if failure_type not in ALLOWED_FAILURE_TYPES:
            raise ValueError(
                f"Row {row_number}: invalid failure_type "
                f"'{failure_type}'. Allowed values: "
                + ", ".join(
                    sorted(ALLOWED_FAILURE_TYPES)
                )
            )

        hours_since_last_success = _parse_float(
            value("hours_since_last_success"),
            "hours_since_last_success",
            row_number,
        )

        expected_action = value(
            "expected_action"
        ).upper()

        if expected_action not in ALLOWED_ACTIONS:
            raise ValueError(
                f"Row {row_number}: invalid expected_action "
                f"'{expected_action}'. Allowed values: "
                + ", ".join(
                    sorted(ALLOWED_ACTIONS)
                )
            )

        recoverable = _parse_bool(
            value("recoverable"),
            row_number,
        )

        cases.append(
            EvaluationCase(
                case_id=case_id,
                amount=amount,
                customer_success_count=(
                    customer_success_count
                ),
                customer_failed_count=(
                    customer_failed_count
                ),
                failure_type=failure_type,
                hours_since_last_success=(
                    hours_since_last_success
                ),
                expected_action=expected_action,
                recoverable=recoverable,
            )
        )

    if not cases:
        raise ValueError(
            "The CSV contains no evaluation rows."
        )

    return cases