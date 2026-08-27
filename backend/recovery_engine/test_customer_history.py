from customer_history import (
    calculate_customer_history,
    payment_belongs_to_customer,
)


def test_payment_belongs_to_customer_by_email_and_contact():
    target = {
        "id": "pay_target",
        "email": "customer@example.com",
        "contact": "+919999999999",
    }

    historical = {
        "id": "pay_old",
        "email": "customer@example.com",
        "contact": "+919999999999",
    }

    assert payment_belongs_to_customer(
        historical,
        target,
    )


def test_payment_does_not_belong_to_customer():
    target = {
        "id": "pay_target",
        "email": "customer@example.com",
        "contact": "+919999999999",
    }

    historical = {
        "id": "pay_old",
        "email": "other@example.com",
        "contact": "+918888888888",
    }

    assert not payment_belongs_to_customer(
        historical,
        target,
    )


def test_customer_history_counts_success_and_failure():
    target = {
        "id": "pay_target",
        "email": "customer@example.com",
        "contact": "+919999999999",
    }

    payments = [
        {
            "id": "pay_old_1",
            "email": "customer@example.com",
            "contact": "+919999999999",
            "status": "captured",
            "created_at": 1000,
        },
        {
            "id": "pay_old_2",
            "email": "customer@example.com",
            "contact": "+919999999999",
            "status": "captured",
            "created_at": 2000,
        },
        {
            "id": "pay_old_3",
            "email": "customer@example.com",
            "contact": "+919999999999",
            "status": "failed",
            "created_at": 3000,
        },
    ]

    history = calculate_customer_history(
        target,
        payments,
    )

    assert history["customer_payment_count"] == 3
    assert history["customer_success_count"] == 2
    assert history["customer_failed_count"] == 1
    assert history["hours_since_last_success"] is not None