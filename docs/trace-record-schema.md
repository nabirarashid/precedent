# Trace Record Schema, v0

*Draft, Sept 30, 2026. This is the normalized record Precedent builds from an ingested trace. It is not the structural signature spec (that is milestone M1); it is the contract between ingestion and everything downstream, and it encodes the project's one non-negotiable design rule up front.*

## Design rule: surface features are quarantined, never indexed

The source measurement (arXiv:2609.01556) found that embedding retrieval over trajectories anchors on literal tokens: in the trajectory domain, retrieval fell below exact chance precisely when the correct match had to involve different object and receptacle tokens, and in the mathematics domain, 95 to 99.8% of ranking failures chose the candidate that was more lexically similar to the query than the correct answer. The design consequence for this schema: every field is classified at definition time as **structural** (matching may key on it), **surface** (kept for display and diagnostics, never scored by default), or **metadata** (identity and outcomes). A field's class is part of its definition. Nothing moves from surface to structural without a measured justification.

## Record layout

### Identity (metadata)

| Field | Type | Notes |
|---|---|---|
| `run_id` | str | Stable unique id, from the source store where available |
| `source` | enum | `otel_genai` \| `langfuse` \| `alfworld` \| `swe_agent` \| `openhands` |
| `source_ref` | str | Trace id / file path in the originating system |
| `started_at`, `ended_at` | timestamp, optional | As recorded |
| `agent_label` | str, optional | Scaffold or agent name as the store reports it |

### Task (mixed)

| Field | Class | Type | Notes |
|---|---|---|---|
| `task_id` | metadata | str, optional | Per-run task identifier where the source has one (e.g. a SWE-bench instance id). Required by the planned downstream experiment; captured from day one. |
| `task_text` | **surface** | str | The instruction or goal as written. Displayed, never indexed. |
| `task_type` | structural | str, optional | A label from the source's own taxonomy when one exists (e.g. ALFWorld task types). Not inferred in v0. |

### Steps (the structural core)

`steps` is an ordered list. Each step:

| Field | Class | Type | Notes |
|---|---|---|---|
| `step_index` | structural | int | Position in the run |
| `kind` | structural | enum | `tool_call` \| `model_turn` \| `observation` \| `control` |
| `tool_name` | structural | str, optional | Canonical tool identifier for `tool_call` steps |
| `arg_types` | structural | list | Argument *shapes*: types and roles only (e.g. `path`, `query_string`, `numeric_id`). Derived at ingest. |
| `arg_values` | **surface** | dict | Raw arguments. Kept for display and for the lexical diagnostic; never scored by default. |
| `depends_on` | structural | list[int] | Step indices whose outputs this step consumes, where derivable; empty list means "unknown", which is distinct from "independent" and recorded as such |
| `status` | structural | enum | `ok` \| `error` \| `retry_of:<index>` \| `abandoned` |
| `text` | **surface** | str, optional | Model text / observation text. Displayed, never indexed. |

Retry and backtrack markers live in `status` and `depends_on`; they are structural because *that a step was retried* is part of what the run did, while *what the retry said* is surface.

### Outcome (metadata, captured from day one)

| Field | Type | Notes |
|---|---|---|
| `outcome_label` | enum, optional | `success` \| `failure` \| `partial` \| `unknown`, from source ground truth only (e.g. test results). Never inferred by an LLM in v0. |
| `outcome_source` | str, optional | What produced the label (e.g. `swe_bench_tests`) |

## Explicitly deferred to the M1 signature spec

How `steps` becomes a comparable signature: graph construction, abstraction levels for `arg_types`, hashing, similarity scoring, and the structural-vs-token-luck diagnostic. This document only guarantees the signature will have honest inputs.

## Format commitments checked against real data

- SWE-agent trajectories (`.traj`, e.g. the nebius/SWE-agent-trajectories release, CC BY 4.0): outcome labels available from linked tests; maps onto `outcome_label` directly.
- OpenHands trajectories (e.g. nebius/SWE-rebench-openhands-trajectories): tool-call `arguments` arrive serialized as strings and must be deserialized before `arg_types` derivation. Known ingest step, noted here so it is not rediscovered.
- ALFWorld-derived set (336 traces, from the source paper): `task_type` comes from the exhaustive labels already built and audited for the paper.
