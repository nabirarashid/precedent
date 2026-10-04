"""Sprint 2: load real SWE-agent trajectories into TraceRecords. (v2)

Learned from v1 against real data:
- splits are tool/xml/ticks (we use tool)
- row["messages"] is a JSON-encoded STRING, not a list -> json.loads it
- rows carry native outcome labels: 'resolved' -> OutcomeLabel

Run from the repo root (inside the venv):
    python scripts/load_sample_traces.py
"""

from __future__ import annotations

import json
import re
from itertools import islice

from datasets import load_dataset

from precedent.records import (
    OutcomeLabel,
    Source,
    Step,
    StepKind,
    TraceRecord,
)

N = 5

FENCE = re.compile(r"```(?:\w*)\n(.*?)```", re.DOTALL)


def classify_arg(token: str) -> str:
    """Abstract one command argument into a type/role label (very v0)."""
    token = str(token)
    if re.fullmatch(r"-?\d+(:\d+)?", token):
        return "number_or_range"
    if "/" in token or token.endswith((".py", ".md", ".txt", ".cfg", ".toml", ".json")):
        return "path"
    if token.startswith("-"):
        return "flag"
    return "text"

def canonical_tool(step: Step) -> str:
    """Spec notes #2 and #3, prototyped: lift sub-actions, split bash by program."""
    if step.tool_name == "bash":
        cmd = str(step.arg_values.get("command", ""))
        tokens = cmd.split()
        prog = tokens[0].rsplit("/", 1)[-1] if tokens else "?"
        if prog in ("python", "python3") and len(tokens) > 2 and tokens[1] == "-m":
            return f"bash.python -m {tokens[2]}"
        return f"bash.{prog}"
    if step.tool_name == "str_replace_editor":
        return f"editor.{step.arg_values.get('command', '?')}"
    return step.tool_name or "unknown"

def get_messages(row: dict) -> list:
    m = row.get("messages") or row.get("conversations") or []
    if isinstance(m, str):
        m = json.loads(m)
    return m


def steps_from_message(msg: dict, start_index: int) -> list[Step]:
    """One message -> zero or more Steps. Handles OpenAI-style tool_calls,
    legacy fenced command blocks, tool/observation results, and plain turns."""
    role = msg.get("role") or msg.get("from") or ""
    content = msg.get("content") or msg.get("value") or ""
    if isinstance(content, list):  # some formats: list of content blocks
        content = " ".join(str(c.get("text", c)) if isinstance(c, dict) else str(c) for c in content)

    if role == "system":
        return []

    if role in ("assistant", "gpt"):
        tool_calls = msg.get("tool_calls") or []
        if tool_calls:
            out = []
            for tc in tool_calls:
                fn = tc.get("function", tc) if isinstance(tc, dict) else {}
                name = fn.get("name", "unknown")
                raw_args = fn.get("arguments", "")
                if isinstance(raw_args, str):
                    try:
                        raw_args = json.loads(raw_args)
                    except (json.JSONDecodeError, TypeError):
                        raw_args = {"raw": raw_args}
                if not isinstance(raw_args, dict):
                    raw_args = {"raw": raw_args}
                out.append(Step(
                    step_index=start_index + len(out),
                    kind=StepKind.TOOL_CALL,
                    tool_name=name,
                    arg_types=[f"{k}:{classify_arg(v)}" for k, v in raw_args.items()],
                    arg_values=raw_args,          # surface
                    text=content or None,          # surface: reasoning around the call
                ))
            return out
        m = FENCE.search(content or "")
        if m:
            first_line = m.group(1).strip().splitlines()[0].strip() if m.group(1).strip() else ""
            tokens = first_line.split()
            return [Step(
                step_index=start_index,
                kind=StepKind.TOOL_CALL,
                tool_name=tokens[0] if tokens else "unknown",
                arg_types=[classify_arg(a) for a in tokens[1:]],
                arg_values={"command": first_line},
                text=content,
            )]
        return [Step(step_index=start_index, kind=StepKind.MODEL_TURN, text=content)]

    if role in ("tool", "user", "human", "observation"):
        if start_index == 0 and role in ("user", "human"):
            return []  # the task statement, captured as task_text, not a step
        return [Step(step_index=start_index, kind=StepKind.OBSERVATION, text=str(content))]

    return []


def to_trace_record(row: dict, i: int) -> TraceRecord:
    messages = get_messages(row)
    steps: list[Step] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        steps.extend(steps_from_message(msg, len(steps)))

    resolved = row.get("resolved")
    outcome = OutcomeLabel.UNKNOWN
    if resolved is True:
        outcome = OutcomeLabel.SUCCESS
    elif resolved is False:
        outcome = OutcomeLabel.FAILURE

    task_text = next((m.get("content") or m.get("value") for m in messages
                      if isinstance(m, dict) and (m.get("role") or m.get("from")) in ("user", "human")), None)

    return TraceRecord(
        run_id=str(row.get("traj_id", f"swe_smith_{i}")),
        source=Source.SWE_AGENT,
        source_ref=str(row.get("instance_id", f"row_{i}")),
        agent_label=str(row.get("model")) if row.get("model") else None,
        task_id=str(row.get("instance_id")) if row.get("instance_id") else None,
        task_text=task_text if isinstance(task_text, str) else None,
        steps=steps,
        outcome_label=outcome,
        outcome_source="swe_smith_resolved" if resolved is not None else None,
    )


def main() -> None:
    print(f"Streaming first {N} rows of SWE-bench/SWE-smith-trajectories (tool split) ...")
    stream = load_dataset("SWE-bench/SWE-smith-trajectories", split="tool", streaming=True)
    rows = list(islice(stream, N))

    print("\n=== RAW STRUCTURE (row 0) ===")
    row0 = rows[0]
    print("columns:", list(row0.keys()))
    print("resolved:", row0.get("resolved"), "| model:", row0.get("model"), "| instance:", row0.get("instance_id"))
    msgs = get_messages(row0)
    print(f"n messages: {len(msgs)}")
    for m in msgs[:6]:
        if not isinstance(m, dict):
            print("  [non-dict message]", str(m)[:100])
            continue
        role = m.get("role") or m.get("from")
        keys = [k for k in m.keys() if k not in ("role", "from")]
        content = str(m.get("content") or m.get("value") or "")[:150].replace("\n", " ")
        print(f"  [{role}] keys={keys} | {content}")

    print("\n=== CONVERTED TRACERECORDS ===")
    for i, row in enumerate(rows):
        rec = to_trace_record(row, i)
        tool_calls = [s for s in rec.steps if s.kind == StepKind.TOOL_CALL]
        print(f"\n--- {rec.run_id} (task {rec.task_id}, outcome={rec.outcome_label.value}) ---")
        print(f"steps: {len(rec.steps)} total, {len(tool_calls)} tool calls")
        sig = " → ".join(canonical_tool(s) for s in tool_calls)
        print(f"signature: {sig}")
        
    print("\nDone. The tool-call sequences above are proto-signatures: real runs")
    print("reduced to shape, surface text quarantined. Note what looks wrong.")


if __name__ == "__main__":
    main()
    import os
    os._exit(0)  # datasets streaming can hang on connection cleanup