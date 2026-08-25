# RecoverAI — AI Revenue Recovery

AI-powered revenue recovery system for merchants — Razorpay AI Buildathon 2026.

## Product

RecoverAI detects revenue at risk, reconstructs payment state, diagnoses the failure context, scores recovery opportunities, recommends a bounded recovery action, applies guardrails, executes the action, and records the outcome.

## Core loop

`Payment events → State resolution → Context → AI diagnosis → Recovery score → Recommendation → Guardrail → Action → Outcome → Audit`

## MVP scope

- Payment-failure recovery
- Payment state verification
- AI-assisted diagnosis and recovery recommendation
- Bounded actions with stopping rules
- Human-review escalation for low-confidence/uncertain cases
- Recovery outcome and audit trail
- Batch evaluation on synthetic payment scenarios
- Merchant recovery dashboard

## Repository structure

```text
frontend/      Merchant dashboard
backend/       API, payment state and recovery services
agent/         AI diagnosis and recommendation logic
data/          Synthetic scenarios and processed evaluation data
evaluation/    Batch evaluation and metrics
docs/          Architecture and product documentation
```

## Status

🚧 MVP in development.

## Important

All development and demonstrations use synthetic/test data and Razorpay test mode where applicable. No live payment credentials or secrets belong in this repository.
