# Input Gateway Phase 1 Specification

## Responsibilities

- Normalize raw user text.
- Classify task type and execution complexity.
- Extract filesystem paths, patterns, content payloads, and terminal intent.
- Produce a stable `IntentResult`.

## Inputs

- `user_input: str`

## Outputs

- `IntentResult`
  - `raw_input`
  - `normalized_input`
  - `task_type`
  - `complexity`
  - `confidence`
  - `parameters`
  - `suggested_tier`
  - `warnings`

## Supported Task Types

- `list_files`
- `read_file`
- `write_file`
- `append_file`
- `search_text`
- `run_terminal`
- `unknown`

## Constraints

- Must never raise on malformed input.
- Must preserve raw input for audit.
- Must mark unsupported or ambiguous tasks as `unknown`.
- Must not invoke any model in Phase 1.
