"""Precedent canonicalizer v0: Steps -> canonical structural tokens, records -> Signatures.

Implements spec requirements #1, #2, #3 and #5 from docs/notes/m1-spec-notes.md.
Requirement #4 (structural stopwords) is deliberately NOT implemented here:
Signature.motif_counts() exposes the counts it will need, and weighting them
is M2 scoring.

Quarantine (docs/trace-record-schema.md): this module never reads Step.text or
TraceRecord.task_text. It reads exactly two things out of the SURFACE field
Step.arg_values, and only to decide structural identity, never to score:

  - the value of a tool's declared discriminator arg (role "subaction"), because
    which sub-action a composite tool performed IS the move (spec req #2);
  - bash's arg_values["command"], because bash is a tool-multiplexer and the
    program it invokes IS the move (spec req #3, #5).

Both reads collapse a raw string into a small closed-ish vocabulary of tool
tokens; nothing else about the value survives into the Signature.

Nothing in this module scores, indexes, or compares anything. That is M2.
"""

from __future__ import annotations

import os
import re
import shlex
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable

from .records import OutcomeLabel, Step, StepKind, TraceRecord

UNKNOWN_ROLE = "unknown"
SUBACTION_ROLE = "subaction"

# Per-tool argument schemas (spec req #1). Arg roles come ONLY from this table.
# A tool or arg missing from it gets role "unknown"; it is never inferred.
#
# Value inspection is forbidden in role assignment. The v0 prototype typed args
# by looking at the value (a slash meant "path"), so two structurally identical
# edits got different shapes because one old_str happened to contain a slash.
# That is the lexical-anchoring failure of the source paper (arXiv:2609.01556)
# recurring at the schema layer, the exact mistake the signature exists to avoid.
TOOL_ARG_ROLES: dict[str, dict[str, str]] = {
    # SWE-agent toolset
    "str_replace_editor": {
        "command": SUBACTION_ROLE,
        "path": "path",
        "old_str": "content",
        "new_str": "content",
        "file_text": "content",
        "view_range": "range",
    },
    "bash": {"command": "shell_command"},
    "submit": {},
}

# Short display names for canonical tokens; the prototype's signatures used
# "editor.view", and keeping it keeps signatures legible.
TOOL_ALIASES: dict[str, str] = {"str_replace_editor": "editor"}


def arg_role(tool_name: str | None, arg_name: str) -> str:
    """Role of one argument, from TOOL_ARG_ROLES only."""
    return TOOL_ARG_ROLES.get(tool_name or "", {}).get(arg_name, UNKNOWN_ROLE)


def arg_roles(tool_name: str | None, arg_names: Iterable[str]) -> dict[str, str]:
    """Roles for a call's arguments. Takes arg NAMES, never values, so a value
    cannot influence its own type even by accident."""
    return {name: arg_role(tool_name, name) for name in arg_names}


def _discriminator(tool_name: str | None) -> str | None:
    for name, role in TOOL_ARG_ROLES.get(tool_name or "", {}).items():
        if role == SUBACTION_ROLE:
            return name
    return None


# Naive on purpose (handoff: no shell grammar). Splits sequential segments on
# &&, ||, ; and pipeline components on | without regard to quoting, so
# `grep 'a|b'` splits wrongly; shlex is used only to tokenize each piece.
_SEQUENCE_SPLIT = re.compile(r"&&|\|\||;")


def _argv(segment: str) -> list[str]:
    try:
        return shlex.split(segment)
    except ValueError:  # unbalanced quotes, often an artifact of the naive split
        return segment.split()


def canonical_bash(command: str) -> str:
    """Salient program of a bash command (spec req #3, #5): skip `cd` segments,
    take the last remaining sequential segment; if it is a pipeline, its FIRST
    component's argv[0] basename (`find … | head` is a find, the pipe tail only
    formats output); `python -m X` keeps X. If every segment is `cd`, fall back
    to the first segment."""
    segments = []  # each: argv of the segment's first pipeline component
    for seg in _SEQUENCE_SPLIT.split(command):
        components = [a for a in (_argv(c) for c in seg.split("|")) if a]
        if components:
            segments.append(components[0])
    if not segments:
        return "bash.?"
    non_cd = [a for a in segments if os.path.basename(a[0]) != "cd"]
    argv = non_cd[-1] if non_cd else segments[0]
    prog = os.path.basename(argv[0])
    if prog in ("python", "python3") and len(argv) > 2 and argv[1] == "-m":
        return f"bash.python -m {argv[2]}"
    return f"bash.{prog}"


def canonical_tool(step: Step) -> str:
    """Canonical tool identity: tool name + discriminating sub-action where the
    table declares one (spec req #2); bash split by program (spec req #3)."""
    name = step.tool_name
    if not name:
        return "unknown"
    if name == "bash":
        return canonical_bash(str(step.arg_values.get("command", "")))
    alias = TOOL_ALIASES.get(name, name)
    disc = _discriminator(name)
    if disc is not None:
        return f"{alias}.{step.arg_values.get(disc, '?')}"
    return alias  # undeclared tools pass through unchanged


@dataclass
class Signature:
    run_id: str
    canonical_steps: list[str] = field(default_factory=list)  # tool_calls only, in order
    step_count: int = 0
    tool_call_count: int = 0
    outcome_label: OutcomeLabel = OutcomeLabel.UNKNOWN

    def motif_counts(self) -> Counter:
        """Unigram counts of canonical tokens. Input for structural stopwords
        (spec req #4); TODO(M2, m1-spec-notes req #4): weighting lives in scoring."""
        return Counter(self.canonical_steps)


def build_signature(record: TraceRecord) -> Signature:
    tool_calls = [s for s in record.steps if s.kind == StepKind.TOOL_CALL]
    return Signature(
        run_id=record.run_id,
        canonical_steps=[canonical_tool(s) for s in tool_calls],
        step_count=len(record.steps),
        tool_call_count=len(tool_calls),
        outcome_label=record.outcome_label,
    )
