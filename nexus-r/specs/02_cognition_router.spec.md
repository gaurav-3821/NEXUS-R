# Cognition Router Phase 1 Specification

## Responsibilities

- Route tasks between:
  - `T1/local`
  - `T2/byok`
- Estimate cost before execution.
- Check for prior similar successful task traces before routing.

## Inputs

- `IntentResult`
- `EventStore`
- `NEXUSConfig`

## Outputs

- `RoutingDecision`
  - `selected_model`
  - `selected_tier`
  - `cost_estimate`
  - `rationale`
  - `etd_match_found`
  - `fallback_chain`

## Routing Rules

- Default to `local` for simple filesystem tasks.
- Use `byok` only when complexity is above the Phase 1 threshold and BYOK is configured.
- Never route to a non-configured provider.
- If a prior successful near-identical task exists, note it as an ETD precursor signal but do not reuse execution automatically.
