from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.razorpay_client import RazorpayClient
from backend.recovery_engine.pipeline import process_razorpay_payment
from backend.recovery_engine.customer_history import (
    calculate_customer_history,
)


app = FastAPI(
    title="RecoverAI API",
    description="Revenue recovery intelligence for failed Razorpay payments.",
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

@app.get("/")
def root():
    return {
        "service": "RecoverAI",
        "status": "running",
    }


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


@app.get("/payments/{payment_id}/analyze")
def analyze_payment(payment_id: str):
    client = RazorpayClient()

    # =========================================================
    # 1. Fetch the real Razorpay payment
    # =========================================================

    payment = client.fetch_payment(payment_id)

    # =========================================================
    # 2. Fetch recent payment history
    # =========================================================

    payment_collection = client.fetch_payments(
        count=100,
        skip=0,
    )

    payments = payment_collection.get("items", [])

    # =========================================================
    # 3. Calculate real customer history
    # =========================================================

    history = calculate_customer_history(
        target_payment=payment,
        payments=payments,
    )

    # =========================================================
    # 4. Run the complete RecoverAI pipeline
    # =========================================================

    result = process_razorpay_payment(
        payment=payment,
        customer_success_count=history["customer_success_count"],
        customer_failed_count=history["customer_failed_count"],
        hours_since_last_success=history["hours_since_last_success"],
    )

    # =========================================================
    # 5. Return the COMPLETE decision path
    # =========================================================
    #
    # Important:
    #
    # AI assessment
    #       ↓
    # deterministic score
    #       ↓
    # recommendation
    #       ↓
    # decision engine
    #       ↓
    # guardrail
    #       ↓
    # execution
    #       ↓
    # audit trail
    #
    # The frontend receives the complete chain so that
    # judges can see WHY RecoverAI made its decision.
    #

    response = {
        "payment_id": payment_id,
        "customer_history": history,

        # -----------------------------------------------------
        # AI reasoning
        # -----------------------------------------------------

        "ai_assessment": result.ai_assessment,

        # -----------------------------------------------------
        # Deterministic scoring
        # -----------------------------------------------------

        "score": result.score,

        # -----------------------------------------------------
        # Deterministic recommendation
        # -----------------------------------------------------

        "recommendation": result.recommendation,

        # -----------------------------------------------------
        # AI + policy reconciliation
        # -----------------------------------------------------

        "reconciled_action": result.reconciled_action,
        "reconciliation_reason": (
            result.reconciliation_reason
        ),

        # -----------------------------------------------------
        # Safety guardrail
        # -----------------------------------------------------

        "guardrail": result.guardrail,

        # -----------------------------------------------------
        # Bounded execution
        # -----------------------------------------------------

        "execution": result.execution,
    }

    # ---------------------------------------------------------
    # Audit trail
    # ---------------------------------------------------------
    #
    # Only expose this if the current pipeline already attaches
    # an audit trail to the result.
    #
    # getattr keeps this API backward-compatible while we finish
    # wiring the audit layer into the pipeline.
    #

    audit_trail = getattr(
        result,
        "audit_trail",
        None,
    )

    if audit_trail is not None:
        response["audit_trail"] = audit_trail

    return response