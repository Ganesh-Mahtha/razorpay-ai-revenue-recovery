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

    # 1. Fetch the real Razorpay payment
    payment = client.fetch_payment(payment_id)

    # 2. Fetch recent payment history
    payment_collection = client.fetch_payments(
        count=100,
        skip=0,
    )

    payments = payment_collection.get("items", [])

    # 3. Calculate real customer history
    history = calculate_customer_history(
        target_payment=payment,
        payments=payments,
    )

    # 4. Run the complete RecoverAI pipeline
    result = process_razorpay_payment(
        payment=payment,
        customer_success_count=history["customer_success_count"],
        customer_failed_count=history["customer_failed_count"],
        hours_since_last_success=history["hours_since_last_success"],
    )

    # 5. Return a clean dashboard/API response
    return {
        "payment_id": payment_id,
        "customer_history": history,
        "diagnosis": result.diagnosis,
        "score": result.score,
        "recommendation": result.recommendation,
        "guardrail": result.guardrail,
        "execution": result.execution,
    }