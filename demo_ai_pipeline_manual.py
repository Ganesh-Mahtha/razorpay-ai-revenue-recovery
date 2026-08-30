from backend.recovery_engine.ai_pipeline import (
    process_payment_with_ai,
)


result = process_payment_with_ai(
    amount=20000,
    customer_success_count=3,
    customer_failed_count=1,
    failure_type="temporary_failure",
    hours_since_last_success=12,
)


print("\n==============================")
print("AI RECOVERY PIPELINE")
print("==============================")

print("\nAI DIAGNOSIS:")
print(result.ai_assessment.diagnosis)

print("\nAI RECOVERABILITY:")
print(result.ai_assessment.recoverability)

print("\nAI CONFIDENCE:")
print(result.ai_assessment.confidence)

print("\nAI RECOMMENDED ACTION:")
print(result.ai_assessment.recommended_action)

print("\nAI REASONING:")
print(result.ai_assessment.reasoning)

print("\nAI SIGNALS:")
for signal in result.ai_assessment.signals:
    print("-", signal)

print("\n==============================")
print("DETERMINISTIC SCORE")
print("==============================")

print("Score:", result.score.score)
print("Tier:", result.score.tier)

print("\nDETERMINISTIC RECOMMENDATION:")
print(result.recommendation.action)

print("\n==============================")
print("RECONCILIATION")
print("==============================")

print("Final proposed action:")
print(result.reconciled_action)

print("\nReason:")
print(result.reconciliation_reason)

print("\n==============================")
print("GUARDRAIL")
print("==============================")

print("Action:", result.guardrail.action)
print("Title:", result.guardrail.title)
print("Confidence:", result.guardrail.confidence)
print("Triggered:", result.guardrail.guardrail_triggered)

print("\nReason:")
print(result.guardrail.reason)

print("\nGuardrail reasons:")
for reason in result.guardrail.guardrail_reasons:
    print("-", reason)

print("\n==============================")
print("EXECUTION")
print("==============================")

print("Action:", result.execution.action)
print("Status:", result.execution.status)
print("Message:", result.execution.message)