from razorpay_client import RazorpayClient


def test_razorpay_credentials():
    client = RazorpayClient()

    result = client.fetch_payments()

    assert "items" in result