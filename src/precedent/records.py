"""Precedent v0 trace records.

Implements docs/trace-record-schema.md. The schema's one non-negotiable rule
is encoded here as data, not convention: every field is classified as
STRUCTURAL (matching may key on it), SURFACE (display and diagnostics only,
never scored by default), or METADATA (identity and outcomes). Downstream
code must consult FIELD_CLASSES rather than hard-coding field names, so the
quarantine survives refactors.

Nothing in this module scores, indexes, or compares anything. That is M1+.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FieldClass(str, Enum):
    STRUCTURAL = "structural"
    SURFACE = "surface"
    METADATA = "metadata"


class Source(str, Enum):
    OTEL_GENAI = "otel_genai"
    LANGFUSE = "langfuse"
    ALFWORLD = "alfworld"
    SWE_AGENT = "swe_agent"
    OPENHANDS = "openhands"


class StepKind(str, Enum):
    TOOL_CALL = "tool_call"
    MODEL_TURN = "model_turn"
    OBSERVATION = "observation"
    CONTROL = "control"


class StepStatus(str, Enum):
    OK = "ok"
    ERROR = "error"
    RETRY = "retry"  # pair with retry_of index on the Step
    ABANDONED = "abandoned"


class OutcomeLabel(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


@dataclass
class Step:
    """One step of a run.

    depends_on semantics (per schema): None means "unknown", which is
    deliberately distinct from [] meaning "known independent".
    """

    step_index: int                                  # structural
    kind: StepKind                                   # structural
    tool_name: Optional[str] = None                  # structural
    arg_types: list[str] = field(default_factory=list)   # structural
    arg_values: dict = field(default_factory=dict)   # SURFACE — never scored
    depends_on: Optional[list[int]] = None           # structural
    status: StepStatus = StepStatus.OK               # structural
    retry_of: Optional[int] = None                   # structural
    text: Optional[str] = None                       # SURFACE — never scored


@dataclass
class TraceRecord:
    """A normalized recorded run. The contract between ingest and everything else."""

    # identity (metadata)
    run_id: str
    source: Source
    source_ref: str
    started_at: Optional[str] = None   # ISO 8601 when available
    ended_at: Optional[str] = None
    agent_label: Optional[str] = None

    # task
    task_id: Optional[str] = None      # metadata — required by the v0.2 experiment
    task_text: Optional[str] = None    # SURFACE — displayed, never indexed
    task_type: Optional[str] = None    # structural — source taxonomy only, never inferred in v0

    # the structural core
    steps: list[Step] = field(default_factory=list)

    # outcome (metadata) — ground truth only, never LLM-inferred in v0
    outcome_label: OutcomeLabel = OutcomeLabel.UNKNOWN
    outcome_source: Optional[str] = None


# The quarantine, as a queryable registry. Downstream matching code must use
# structural_fields() / is_scorable(); touching a SURFACE field in scoring is a bug.
FIELD_CLASSES: dict[str, FieldClass] = {
    # TraceRecord
    "run_id": FieldClass.METADATA,
    "source": FieldClass.METADATA,
    "source_ref": FieldClass.METADATA,
    "started_at": FieldClass.METADATA,
    "ended_at": FieldClass.METADATA,
    "agent_label": FieldClass.METADATA,
    "task_id": FieldClass.METADATA,
    "task_text": FieldClass.SURFACE,
    "task_type": FieldClass.STRUCTURAL,
    "outcome_label": FieldClass.METADATA,
    "outcome_source": FieldClass.METADATA,
    # Step
    "step_index": FieldClass.STRUCTURAL,
    "kind": FieldClass.STRUCTURAL,
    "tool_name": FieldClass.STRUCTURAL,
    "arg_types": FieldClass.STRUCTURAL,
    "arg_values": FieldClass.SURFACE,
    "depends_on": FieldClass.STRUCTURAL,
    "status": FieldClass.STRUCTURAL,
    "retry_of": FieldClass.STRUCTURAL,
    "text": FieldClass.SURFACE,
}


def structural_fields() -> set[str]:
    return {k for k, v in FIELD_CLASSES.items() if v is FieldClass.STRUCTURAL}


def surface_fields() -> set[str]:
    return {k for k, v in FIELD_CLASSES.items() if v is FieldClass.SURFACE}


def is_scorable(field_name: str) -> bool:
    """May matching/scoring code read this field? Unknown fields are NOT scorable."""
    return FIELD_CLASSES.get(field_name) is FieldClass.STRUCTURAL
