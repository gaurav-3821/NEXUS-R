# Workflow Engine Phase 1 Specification

## Responsibilities

- Record causal traces for every execution step.
- Support later ETD distillation by storing complete causal metadata.

## Phase 1 Scope

- Trace recording only
- Trace retrieval and lightweight summary
- No ETD extraction, generalization, or replay

## Required Metadata

- task id
- step index
- tool name
- action name
- input payload
- output payload
- verification result
- model used
- cost
- permission tier
