import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware

from backend.razorpay_client import RazorpayClient
from backend.recovery_engine.customer_history import (
    calculate_customer_history,
)
from backend.recovery_engine.pipeline import (
    process_razorpay_payment,
)

from evaluation.csv_adapter import (
    parse_evaluation_csv,
)
from evaluation.metrics import (
    metrics_to_dict,
)
from evaluation.runner import (
    run_evaluation_metrics,
)


# =========================================================
# PROJECT PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

EVALUATION_SUMMARY_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "summary.json"
)

EVALUATION_LATEST_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "latest.json"
)

EVALUATION_SNAPSHOTS_DIR = (
    PROJECT_ROOT
    / "evaluation"
    / "snapshots"
)


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="RecoverAI API",
    description=(
        "Revenue recovery intelligence "
        "for failed Razorpay payments."
    ),
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "service": "RecoverAI",
        "status": "running",
    }


# =========================================================
# RAZORPAY PAYMENTS
# =========================================================

@app.get("/payments")
def get_payments():
    client = RazorpayClient()

    return client.fetch_payments(
        count=100,
        skip=0,
    )


@app.get("/payments/{payment_id}")
def get_payment(payment_id: str):
    client = RazorpayClient()

    return client.fetch_payment(payment_id)


# =========================================================
# RAZORPAY PAYMENT ANALYSIS
# =========================================================

@app.get("/payments/{payment_id}/analyze")
def analyze_payment(payment_id: str):
    client = RazorpayClient()

    # -----------------------------------------------------
    # 1. Fetch real Razorpay payment
    # -----------------------------------------------------

    payment = client.fetch_payment(
        payment_id
    )

    # -----------------------------------------------------
    # 2. Fetch recent payment history
    # -----------------------------------------------------

    payment_collection = client.fetch_payments(
        count=100,
        skip=0,
    )

    payments = payment_collection.get(
        "items",
        [],
    )

    # -----------------------------------------------------
    # 3. Calculate customer history
    # -----------------------------------------------------

    history = calculate_customer_history(
        target_payment=payment,
        payments=payments,
    )

    # -----------------------------------------------------
    # 4. Run RecoverAI pipeline
    # -----------------------------------------------------

    result = process_razorpay_payment(
        payment=payment,
        customer_success_count=(
            history["customer_success_count"]
        ),
        customer_failed_count=(
            history["customer_failed_count"]
        ),
        hours_since_last_success=(
            history["hours_since_last_success"]
        ),
    )

    # -----------------------------------------------------
    # 5. Build complete decision response
    # -----------------------------------------------------

    response = {
        "payment_id": payment_id,
        "customer_history": history,

        "ai_assessment": result.ai_assessment,

        "score": result.score,

        "recommendation": result.recommendation,

        "reconciled_action": (
            result.reconciled_action
        ),

        "reconciliation_reason": (
            result.reconciliation_reason
        ),

        "guardrail": result.guardrail,

        "execution": result.execution,
    }

    # -----------------------------------------------------
    # 6. Include audit trail when available
    # -----------------------------------------------------

    audit_trail = getattr(
        result,
        "audit_trail",
        None,
    )

    if audit_trail is not None:
        response["audit_trail"] = audit_trail

    return response


# =========================================================
# EVALUATION — CURRENT SNAPSHOT
# =========================================================

@app.get("/evaluation/summary")
def get_evaluation_summary():
    """
    Return the latest saved RecoverAI evaluation snapshot.

    This endpoint does NOT execute the AI pipeline.
    """

    if not EVALUATION_SUMMARY_PATH.exists():
        return {
            "available": False,
            "message": (
                "Evaluation snapshot not found."
            ),
        }

    try:
        with EVALUATION_SUMMARY_PATH.open(
            "r",
            encoding="utf-8",
        ) as file:
            summary = json.load(file)

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        return {
            "available": False,
            "message": (
                "Evaluation snapshot "
                "could not be read."
            ),
            "error": str(exc),
        }

    return {
        "available": True,
        "summary": summary,
    }


# =========================================================
# EVALUATION — CSV UPLOAD
# =========================================================

@app.post("/evaluation/upload")
async def upload_evaluation(
    file: UploadFile = File(...),
):
    """
    Upload a RecoverAI evaluation CSV.

    The uploaded dataset is:

        CSV
          ↓
        Validation
          ↓
        EvaluationCase[]
          ↓
        RecoverAI AI pipeline
          ↓
        Deterministic policy
          ↓
        Safety guardrails
          ↓
        Metrics
          ↓
        Persisted snapshot
    """

    # -----------------------------------------------------
    # 1. Validate filename
    # -----------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected.",
        )

    if not file.filename.lower().endswith(
        ".csv"
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Please upload a CSV file."
            ),
        )

    # -----------------------------------------------------
    # 2. Read uploaded file
    # -----------------------------------------------------

    try:
        content = await file.read()

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to read uploaded file."
            ),
        ) from exc

    # -----------------------------------------------------
    # 3. Parse and validate CSV
    # -----------------------------------------------------

    try:
        cases = parse_evaluation_csv(
            content
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    # -----------------------------------------------------
    # 4. Run RecoverAI evaluation
    # -----------------------------------------------------

    try:
        metrics = run_evaluation_metrics(
            cases
        )

        summary = metrics_to_dict(
            metrics
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Evaluation failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc

    # -----------------------------------------------------
    # 5. Create snapshot metadata
    # -----------------------------------------------------

    timestamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    snapshot = {
        "source": "uploaded_csv",
        "filename": file.filename,
        "created_at": timestamp,
        "cases": len(cases),
        "summary": summary,
    }

    # -----------------------------------------------------
    # 6. Save timestamped snapshot
    # -----------------------------------------------------

    EVALUATION_SNAPSHOTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    snapshot_path = (
        EVALUATION_SNAPSHOTS_DIR
        / f"evaluation_{timestamp}.json"
    )

    try:
        snapshot_path.write_text(
            json.dumps(
                snapshot,
                indent=2,
            ),
            encoding="utf-8",
        )

    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Evaluation completed but "
                "snapshot could not be saved."
            ),
        ) from exc

    # -----------------------------------------------------
    # 7. Update latest evaluation
    # -----------------------------------------------------

    try:
        EVALUATION_LATEST_PATH.write_text(
            json.dumps(
                snapshot,
                indent=2,
            ),
            encoding="utf-8",
        )

    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Evaluation completed but "
                "latest snapshot could not be saved."
            ),
        ) from exc

    # -----------------------------------------------------
    # 8. Return fresh metrics to frontend
    # -----------------------------------------------------

    return {
        "available": True,
        "filename": file.filename,
        "cases": len(cases),
        "created_at": timestamp,
        "summary": summary,
    }