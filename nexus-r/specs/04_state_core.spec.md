# State Core Phase 1 Specification

## Responsibilities

- Maintain append-only event log in SQLite.
- Maintain working state for the active task.
- Expose history and cost queries.

## Event Store Requirements

- SQLite with WAL mode.
- Indexes on timestamp, event type, and parent event id.
- Methods:
  - `append`
  - `query`
  - `get_chain`
  - `get_by_time_range`
  - `get_by_type`
  - `create_projected_view`
  - `compact`

## Working State Requirements

- Track active task id
- Track lifecycle status
- Track last routing decision
- Track latest execution result
