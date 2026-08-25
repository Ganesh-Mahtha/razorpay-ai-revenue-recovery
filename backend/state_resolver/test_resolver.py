from resolver import PaymentEvent, resolve_payment_state


def test_confirmed_failure():
    events = [
        PaymentEvent(
            event_id="evt_001",
            payment_id="pay_001",
            event_type="payment.created",
            timestamp=1,
        ),
        PaymentEvent(
            event_id="evt_002",
            payment_id="pay_001",
            event_type="payment.failed",
            timestamp=2,
        ),
    ]

    result = resolve_payment_state(events)

    assert result.state == "FAILED"
    assert result.certainty == "HIGH"


def test_captured_payment_overrides_failure():
    events = [
        PaymentEvent(
            event_id="evt_001",
            payment_id="pay_002",
            event_type="payment.failed",
            timestamp=1,
        ),
        PaymentEvent(
            event_id="evt_002",
            payment_id="pay_002",
            event_type="payment.captured",
            timestamp=2,
        ),
    ]

    result = resolve_payment_state(events)

    assert result.state == "CAPTURED"
    assert result.certainty == "HIGH"


def test_uncertain_payment():
    events = [
        PaymentEvent(
            event_id="evt_001",
            payment_id="pay_003",
            event_type="payment.created",
            timestamp=1,
        ),
    ]

    result = resolve_payment_state(events)

    assert result.state == "UNCERTAIN"
    assert result.certainty == "LOW"


def test_duplicate_events_are_ignored():
    events = [
        PaymentEvent(
            event_id="evt_001",
            payment_id="pay_004",
            event_type="payment.failed",
            timestamp=1,
        ),
        PaymentEvent(
            event_id="evt_001",
            payment_id="pay_004",
            event_type="payment.failed",
            timestamp=1,
        ),
    ]

    result = resolve_payment_state(events)

    assert result.state == "FAILED"