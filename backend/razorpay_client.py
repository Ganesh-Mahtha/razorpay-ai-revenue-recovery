import os

import razorpay
from dotenv import load_dotenv


load_dotenv()


class RazorpayClient:
    def __init__(self):
        key_id = os.getenv("RAZORPAY_KEY_ID")
        key_secret = os.getenv("RAZORPAY_KEY_SECRET")

        if not key_id or not key_secret:
            raise RuntimeError(
                "Razorpay credentials are missing. "
                "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env"
            )

        self.client = razorpay.Client(
            auth=(key_id, key_secret)
        )

    def fetch_payment(self, payment_id: str):
        """Fetch a single Razorpay payment."""
        return self.client.payment.fetch(payment_id)

    def fetch_payments(self, count: int = 100, skip: int = 0):
        """Fetch recent Razorpay payments."""
        return self.client.payment.all(
            {
                "count": count,
                "skip": skip,
            }
        )

    def fetch_order(self, order_id: str):
        """Fetch a single Razorpay order."""
        return self.client.order.fetch(order_id)

    def fetch_order_payments(self, order_id: str):
        """Fetch payments associated with an order."""
        return self.client.order.payments(order_id)