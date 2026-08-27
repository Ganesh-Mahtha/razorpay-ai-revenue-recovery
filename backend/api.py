from fastapi import FastAPI

from backend.razorpay_client import RazorpayClient
from backend.recovery_engine.pipeline import process_payment
from backend.recovery_engine.razorpay_adapter import (
    payment_to_recovery_context,
)
from backend.recovery_engine.customer_history import (
    calculate_customer_history,
)


app = FastAPI(
    title="RecoverAI API",
    description="Revenue recovery intelligence for failed Razorpay payments.",
    version="0.1.0",
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
    return client.fetch_payments()


@app.get("/payments/{payment_id}")
def get_payment(payment_id: str):
    client = RazorpayClient()
    return client.fetch_payment(payment_id)


@app.get("/payments/{payment_id}/analyze")
def analyze_payment(payment_id: str):
    client = RazorpayClient()

    # 1. Fetch the real Razorpay payment
    payment = client.fetch_payment(payment_id)

    # 2. Fetch recent Razorpay payment history
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

    # 4. Convert Razorpay data into our internal context
    context = payment_to_recovery_context(
        payment,
        customer_success_count=history["customer_success_count"],
        hours_since_last_success=history["hours_since_last_success"],
    )

    # 5. Run the recovery engine
    result = process_payment(
        amount=context.amount,
        customer_success_count=context.customer_success_count,
        failure_type=context.failure_type,
        hours_since_last_success=context.hours_since_last_success,
    )

    # 6. Return a clean RecoverAI response
    return {
        "payment_id": payment_id,
        "customer_history": history,
        "diagnosis": result.diagnosis,
        "score": result.score,
        "recommendation": result.recommendation,
    }