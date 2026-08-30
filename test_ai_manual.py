from backend.recovery_engine.ai_reasoner import (
    assess_payment_with_ai,
)


result = assess_payment_with_ai(
    amount=20000,
    customer_success_count=3,
    customer_failed_count=1,
    failure_type="temporary_failure",
    hours_since_last_success=12,
)

print("\nDIAGNOSIS:")
print(result.diagnosis)

print("\nRECOVERABILITY:")
print(result.recoverability)

print("\nCONFIDENCE:")
print(result.confidence)

print("\nRECOMMENDED ACTION:")
print(result.recommended_action)

print("\nREASONING:")
print(result.reasoning)

print("\nSIGNALS:")
for signal in result.signals:
    print("-", signal)