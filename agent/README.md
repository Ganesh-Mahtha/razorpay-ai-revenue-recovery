# Agent

RecoverAI decision layer.

Pipeline:

Payment context → diagnosis → recoverability score → recommended action → confidence → guardrail input

The agent recommends bounded actions. It does not bypass state verification or guardrails.
