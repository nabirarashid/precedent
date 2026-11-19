"""AgentInstruct/ALFWorld ingest adapter.

Each corpus trajectory (state_action_pairs of {step_id, state, action})
becomes a TraceRecord; each action a TOOL_CALL Step. The canonical token for
this domain is the ACTION VERB ONLY: "take laptop 1 from diningtable 1" →
`take`. Object and receptacle names are SURFACE arg_values with roles
`object` / `receptacle` declared in canonicalize.TOOL_ARG_ROLES — the spec's
R1 applied to this domain: the whole design depends on object/receptacle
being invisible to the signature.

Action grammar (the AgentInstruct corpus's observed command set):
    go to R | take O from R | put O in/on R | heat/cool/clean O with R
    open/close R | toggle/examine/use O | look | inventory
An action matching none of these keeps its first word as the token (and no
args); callers can collect those via `unrecognized_verbs` to extend the table.

Task metadata comes from the paper repo's labels file: task_type_name →
TraceRecord.task_type (STRUCTURAL, source taxonomy only); task_description →
task_text (SURFACE).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, Optional

from .canonicalize import arg_roles
from .records import OutcomeLabel, Source, Step, StepKind, TraceRecord

# Patterns are anchored and tried in order; group names become arg_values keys.
ACTION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^go to (?P<receptacle>.+)$"), "go"),
    (re.compile(r"^take (?P<object>.+?) from (?P<receptacle>.+)$"), "take"),
    (re.compile(r"^put (?P<object>.+?) (?:in/on|in|on) (?P<receptacle>.+)$"), "put"),
    (re.compile(r"^heat (?P<object>.+?) with (?P<receptacle>.+)$"), "heat"),
    (re.compile(r"^cool (?P<object>.+?) with (?P<receptacle>.+)$"), "cool"),
    (re.compile(r"^clean (?P<object>.+?) with (?P<receptacle>.+)$"), "clean"),
    (re.compile(r"^open (?P<receptacle>.+)$"), "open"),
    (re.compile(r"^close (?P<receptacle>.+)$"), "close"),
    (re.compile(r"^toggle (?P<object>.+)$"), "toggle"),
    (re.compile(r"^examine (?P<object>.+)$"), "examine"),
    (re.compile(r"^use (?P<object>.+)$"), "use"),
    (re.compile(r"^look$"), "look"),
    (re.compile(r"^inventory$"), "inventory"),
]


def parse_action(action: str) -> tuple[str, dict[str, str], bool]:
    """(verb token, arg_values, recognized). Unrecognized actions keep their
    first word as the token, with the raw text as a SURFACE arg."""
    text = action.strip()
    for pattern, verb in ACTION_PATTERNS:
        m = pattern.match(text)
        if m:
            return verb, {k: v for k, v in m.groupdict().items() if v}, True
    first = text.split()[0] if text.split() else "unknown"
    return first, {"raw": text}, False


def to_trace_record(traj: dict, label: Optional[dict] = None) -> TraceRecord:
    steps: list[Step] = []
    for pair in traj.get("state_action_pairs", []):
        verb, args, _ = parse_action(pair.get("action") or "")
        steps.append(Step(
            step_index=len(steps),
            kind=StepKind.TOOL_CALL,
            tool_name=verb,
            arg_types=[f"{k}:{r}" for k, r in arg_roles(verb, args).items()],
            arg_values=args,
        ))
    run_id = str(traj.get("task_instance_id"))
    return TraceRecord(
        run_id=run_id,
        source=Source.ALFWORLD,
        source_ref=run_id,
        task_id=run_id,
        task_text=traj.get("task_description"),
        task_type=str(label["task_type_name"]) if label and label.get("task_type_name") else None,
        steps=steps,
        outcome_label=OutcomeLabel.UNKNOWN,  # the corpus carries no eval verdict
    )


def unrecognized_verbs(trajs: Iterable[dict]) -> dict[str, int]:
    """Distinct unrecognized action verbs -> count, so the table can be extended."""
    out: dict[str, int] = {}
    for traj in trajs:
        for pair in traj.get("state_action_pairs", []):
            verb, _, ok = parse_action(pair.get("action") or "")
            if not ok:
                out[verb] = out.get(verb, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def load_corpus(corpus_path: str | Path,
                labels_path: str | Path | None = None) -> list[TraceRecord]:
    """READ-ONLY ingest of the fetched corpus (+ labels, joined on trajectory id)."""
    data = json.loads(Path(corpus_path).read_text())
    trajs = data["trajectories"] if isinstance(data, dict) else data
    labels_by_id: dict[str, dict] = {}
    if labels_path is not None:
        for lab in json.loads(Path(labels_path).read_text()):
            labels_by_id[str(lab.get("trajectory_id"))] = lab
    return [to_trace_record(t, labels_by_id.get(str(t.get("task_instance_id"))))
            for t in trajs]
