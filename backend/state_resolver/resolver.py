from dataclasses import dataclass
from typing import List


@dataclass
class PaymentEvent:
    event_id: str
    payment_id: str
    event_type: str
    timestamp: int


@dataclass
class PaymentState:
    payment_id: str
    state: str
    certainty: str


def resolve_payment_state(events: List[PaymentEvent]) -> PaymentState:
    """
    Reconstruct the latest reliable payment state from payment events.

    This is deterministic and does not use AI.
    """

    if not events:
        raise ValueError("At least one payment event is required.")

    # Remove duplicate events.
    unique_events = {
        event.event_id: event
        for event in events
    }.values()

    # Process events chronologically.
    ordered_events = sorted(
        unique_events,
        key=lambda event: event.timestamp
    )

    payment_id = ordered_events[0].payment_id
    event_types = [event.event_type for event in ordered_events]

    # A captured payment is the strongest terminal signal.
    if "payment.captured" in event_types:
        return PaymentState(
            payment_id=payment_id,
            state="CAPTURED",
            certainty="HIGH"
        )

    # A refund after capture means the payment is no longer recoverable.
    if "payment.refunded" in event_types:
        return PaymentState(
            payment_id=payment_id,
            state="REFUNDED",
            certainty="HIGH"
        )

    # A confirmed failure with no later success.
    if "payment.failed" in event_types:
        return PaymentState(
            payment_id=payment_id,
            state="FAILED",
            certainty="HIGH"
        )

    # We don't have enough evidence.
    return PaymentState(
        payment_id=payment_id,
        state="UNCERTAIN",
        certainty="LOW"
    )