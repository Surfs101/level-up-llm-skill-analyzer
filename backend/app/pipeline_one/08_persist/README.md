# Step 08 — Persist

**Purpose.** Save the finished analysis and mark the run complete.

**Inputs (from state).** The fully populated state — gap, selected courses,
generated projects — plus `is_guest`.

**Outputs.** For signed-in users, an immutable `Plan` row (a denormalized snapshot)
plus the run marked `completed` — both in one transaction. Returns the state
unchanged (terminal step).

**Guests.** Their result lives only in Redis with a short TTL — **not built yet**;
`run()` raises `NotImplementedError` for guests as a Phase-6 TODO. The authenticated
path is complete.

**Failure modes.** A write failure propagates; the orchestrator marks the run
`failed` and the user retries from the UI.
