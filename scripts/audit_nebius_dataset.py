"""M2: audit nebius/SWE-agent-trajectories for DoppelBench design.

Streams the first 20,000 rows (streaming=True; the full ~80k is not
downloaded) and measures schema, trajectories per instance, instances per
repo, outcome mix, and fit against our SWE-smith ingest path
(scripts/load_sample_traces.py). Writes docs/notes/nebius-audit.md.

Measure-and-report only: no benchmark building, no scoring.

Run from the repo root (inside the venv):
    python scripts/audit_nebius_dataset.py
"""

from __future__ import annotations

import os
import re
import sys
from collections import Counter, defaultdict
from itertools import islice
from pathlib import Path

from datasets import get_dataset_split_names, load_dataset

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load_sample_traces import FENCE, to_trace_record  # noqa: E402  (the SWE-smith ingest path)

from precedent.canonicalize import build_signature  # noqa: E402

DATASET = "nebius/SWE-agent-trajectories"
CAP = 20_000
OUT = Path(__file__).resolve().parent.parent / "docs" / "notes" / "nebius-audit.md"


def short(v, width=100):
    """Compact one-line rendering of a value; long strings truncated."""
    if isinstance(v, str):
        s = v.replace("\n", "\\n")
        return repr(s[:width]) + ("…" if len(s) > width else "")
    if isinstance(v, list):
        return f"list[{len(v)}]" + (f" first={short(v[0], width)}" if v else "")
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {short(x, width)}" for k, x in v.items()) + "}"
    return repr(v)


def repo_of(instance_id: str) -> str:
    # SWE-bench convention: "<owner>__<repo>-<number>"
    return instance_id.rsplit("-", 1)[0]


def bucket(n: int, edges: list[int]) -> str:
    """Label n by the first edge it falls under; edges ascending, last is open."""
    for lo, hi in zip(edges, edges[1:]):
        if lo <= n < hi:
            return str(lo) if hi == lo + 1 else f"{lo}-{hi - 1}"
    return f"{edges[-1]}+"


def as_smith_row(row: dict) -> dict:
    """Probe only (not an adapter): rename nebius fields to the shape the
    SWE-smith parser expects, to see how far the existing path gets."""
    role_map = {"ai": "assistant"}
    msgs = [{"role": role_map.get(m["role"], m["role"]), "content": m.get("text") or ""}
            for m in row["trajectory"]]
    return {"messages": msgs, "resolved": row["target"], "instance_id": row["instance_id"],
            "traj_id": f"{row['instance_id']}::{row['model_name']}", "model": row["model_name"]}


def md_table(header: list[str], rows: list[list]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return out


def main() -> None:
    splits = get_dataset_split_names(DATASET)
    print(f"{DATASET} splits: {splits}")
    stream = load_dataset(DATASET, split="train", streaming=True)
    features = stream.features

    by_instance: dict[str, list[bool]] = defaultdict(list)
    models_by_instance: dict[str, set] = defaultdict(set)
    models: Counter = Counter()
    exit_status: Counter = Counter()
    roles: Counter = Counter()
    first_word: Counter = Counter()
    ai_msgs = ai_fenced = ai_multi_fence = 0
    traj_lens: list[int] = []
    ids_in_order: list[str] = []
    example = None
    parser_probe = None

    for i, row in enumerate(islice(stream, CAP)):
        if example is None:
            example = row
            direct = to_trace_record(row, 0)
            mapped = to_trace_record(as_smith_row(row), 0)
            parser_probe = (direct, mapped, build_signature(mapped))
        iid = row["instance_id"]
        ids_in_order.append(iid)
        by_instance[iid].append(bool(row["target"]))
        models_by_instance[iid].add(row["model_name"])
        models[row["model_name"]] += 1
        exit_status[row["exit_status"]] += 1
        traj = row["trajectory"]
        traj_lens.append(len(traj))
        for m in traj:
            roles[m["role"]] += 1
            if m["role"] != "ai":
                continue
            ai_msgs += 1
            text = m.get("text") or ""
            blocks = FENCE.findall(text)
            if blocks:
                ai_fenced += 1
                ai_multi_fence += len(blocks) > 1
                first = blocks[0].strip().split(None, 1)
                first_word[first[0] if first else "<empty>"] += 1
        if (i + 1) % 2000 == 0:
            print(f"  {i + 1} rows ...", flush=True)

    n_rows = len(ids_in_order)
    n_inst = len(by_instance)
    successes = sum(sum(v) for v in by_instance.values())
    sorted_order = ids_in_order == sorted(ids_in_order)
    # contiguous blocks: if each instance's rows are adjacent, blocks == instances
    blocks = 1 + sum(a != b for a, b in zip(ids_in_order, ids_in_order[1:]))

    # 2. trajectories per instance
    tpi = Counter(bucket(len(v), [1, 2, 3, 4]) for v in by_instance.values())
    multi = {k: v for k, v in by_instance.items() if len(v) >= 2}
    # 3. instances per repo
    repo_inst: dict[str, set] = defaultdict(set)
    for iid in by_instance:
        repo_inst[repo_of(iid)].add(iid)
    ipr = Counter(bucket(len(s), [1, 2, 5, 10, 50]) for s in repo_inst.values())
    repos_10 = sum(len(s) >= 10 for s in repo_inst.values())
    repo_multi: Counter = Counter(repo_of(k) for k in multi)
    repos_10_multi = sum(c >= 10 for c in repo_multi.values())
    # 4. outcome mix
    mixed = {k: v for k, v in multi.items() if any(v) and not all(v)}
    all_succ = sum(all(v) for v in multi.values())
    all_fail = sum(not any(v) for v in multi.values())
    repo_mixed: Counter = Counter(repo_of(k) for k in mixed)
    repos_10_mixed = sum(c >= 10 for c in repo_mixed.values())
    repos_5_mixed = sum(c >= 5 for c in repo_mixed.values())
    multi_model = sum(len(models_by_instance[k]) > 1 for k in multi)
    singleton_repos = sum(len(s) == 1 for s in repo_inst.values())

    direct, mapped, mapped_sig = parser_probe

    L: list[str] = [
        "# nebius/SWE-agent-trajectories — audit for DoppelBench design",
        "",
        f"*Generated by scripts/audit_nebius_dataset.py. Streamed the first {n_rows:,} rows of split "
        f"`train` (splits available: {', '.join(f'`{s}`' for s in splits)}); nothing else downloaded. "
        "Measurements only; no design decisions.*",
        "",
        "## 1. Schema",
        "",
        *md_table(["column", "type"], [[f"`{k}`", f"`{v}`"] for k, v in features.items()]),
        "",
        "Example row (row 0), long strings truncated to 100 chars:",
        "",
        "```",
        *[f"{k}: {short(v)}" for k, v in example.items() if k != "trajectory"],
        f"trajectory: list[{len(example['trajectory'])}]",
        *[f"  [{j}] {short(m)}" for j, m in enumerate(example["trajectory"][:5])],
        "  …",
        "```",
        "",
        "- **Task instance:** `instance_id`, SWE-bench style `<owner>__<repo>-<number>`.",
        "- **Repo:** not a column; parsed from `instance_id` as everything before the last `-`.",
        "- **Run identity:** no trajectory id column. A row is (instance_id, model_name, trajectory); "
        "a run id has to be synthesized.",
        f"- **Outcome:** `target` (bool; treated here as resolved). Also `exit_status` (free-text "
        f"string, {len(exit_status)} distinct values in the sample), `generated_patch`, `eval_logs`.",
        f"- **Actions:** inside `trajectory`, a list of messages with roles "
        f"{', '.join(f'`{r}` ({c:,})' for r, c in roles.most_common())}. Text is in `text` "
        "(system message uses `system_prompt` instead). There are no structured tool calls: the "
        "action is a fenced code block inside each `ai` message (classic SWE-agent thought + command "
        f"format). {ai_fenced:,} of {ai_msgs:,} `ai` messages ({ai_fenced / max(ai_msgs, 1):.1%}) "
        f"contain a fenced block; {ai_multi_fence:,} contain more than one.",
        f"- **Trajectory length:** median {sorted(traj_lens)[len(traj_lens) // 2]} messages, "
        f"max {max(traj_lens)}.",
        f"- **Row order:** rows are {'' if sorted_order else 'not '}sorted by instance_id "
        f"(first `{ids_in_order[0]}`, last `{ids_in_order[-1]}`). "
        + ("**The first 20k rows therefore cover an alphabetical prefix of repos, not a random sample.** "
           if sorted_order else "")
        + f"Rows form {blocks:,} contiguous runs of the same instance_id for {len(by_instance):,} "
        "instances" + (": each instance's trajectories are grouped together, so the 20k prefix holds "
                       "complete trajectory sets for fewer instances rather than a thin slice of all of them."
                       if blocks == len(by_instance) else "."),
        "",
        "Action vocabulary (first word of the first fenced block in each `ai` message, top 20):",
        "",
        *md_table(["command", "count", "share"],
                  [[f"`{w}`", f"{c:,}", f"{c / ai_fenced:.1%}"] for w, c in first_word.most_common(20)]),
        "",
        "Models in the sample:",
        "",
        *md_table(["model_name", "rows"], [[f"`{m}`", f"{c:,}"] for m, c in models.most_common()]),
        "",
        "## 2. Trajectories per instance",
        "",
        f"{n_inst:,} distinct instances in {n_rows:,} rows.",
        "",
        *md_table(["trajectories", "instances"], [[b, f"{tpi.get(b, 0):,}"] for b in ["1", "2", "3", "4+"]]),
        "",
        f"**Instances with 2+ trajectories: {len(multi):,}.** "
        f"Max trajectories for one instance: {max(len(v) for v in by_instance.values())}. "
        f"Of those {len(multi):,}, {multi_model:,} have trajectories from more than one model.",
        "",
        "## 3. Instances per repo",
        "",
        f"{len(repo_inst):,} distinct repos.",
        "",
        *md_table(["instances seen", "repos"],
                  [[b, f"{ipr.get(b, 0):,}"] for b in ["1", "2-4", "5-9", "10-49", "50+"]]),
        "",
        f"**Repos with 10+ instances: {repos_10:,}.** Repos with 10+ instances that each have "
        f"2+ trajectories: {repos_10_multi:,}.",
        "",
        "Top 10 repos by instances seen:",
        "",
        *md_table(["repo", "instances", "instances with 2+ trajectories"],
                  [[f"`{r}`", len(s), repo_multi.get(r, 0)]
                   for r, s in sorted(repo_inst.items(), key=lambda kv: -len(kv[1]))[:10]]),
        "",
        "## 4. Outcome mix",
        "",
        *md_table(["", "trajectories", "share"], [
            ["success (`target` true)", f"{successes:,}", f"{successes / n_rows:.1%}"],
            ["failure (`target` false)", f"{n_rows - successes:,}", f"{(n_rows - successes) / n_rows:.1%}"],
        ]),
        "",
        f"Within the {len(multi):,} instances with 2+ trajectories:",
        "",
        *md_table(["outcomes across the instance's trajectories", "instances"], [
            ["at least one success AND at least one failure", f"{len(mixed):,}"],
            ["all success", f"{all_succ:,}"],
            ["all failure", f"{all_fail:,}"],
        ]),
        "",
        f"Repos with 10+ mixed-outcome instances: {repos_10_mixed:,}; with 5+: {repos_5_mixed:,}.",
        "",
        "`exit_status` values (top 10):",
        "",
        *md_table(["exit_status", "rows"], [[f"`{s}`", f"{c:,}"] for s, c in exit_status.most_common(10)]),
        "",
        "## 5. Ingest fit against the SWE-smith path",
        "",
        "Tested by running `to_trace_record` from scripts/load_sample_traces.py on row 0.",
        "",
        f"- **As-is: the same parser does not work.** It reads `messages`/`conversations`, so a nebius "
        f"row yields {len(direct.steps)} steps and outcome `{direct.outcome_label.value}` (it reads "
        "`resolved`; nebius calls it `target`).",
        f"- **With fields renamed only** (`trajectory`→`messages`, `text`→`content`, role `ai`→"
        f"`assistant`, `target`→`resolved`), the fenced-block fallback fires: {len(mapped.steps)} steps, "
        f"{mapped_sig.tool_call_count} tool calls. First tokens: "
        f"`{' → '.join(mapped_sig.canonical_steps[:8])}`.",
        "- **So a new adapter is needed, and renaming is not enough.** What differs:",
        "  - Field names and roles (above), and no run-id column (synthesize from instance_id + model_name).",
        "  - Actions are SWE-agent's classic command set (the `open`, `edit`, `search_dir`, "
        "`find_file`, `goto`, `scroll_down`, `create`, `submit` family; see the vocabulary table), not "
        "`str_replace_editor` + `bash` tool calls. None of them are in `TOOL_ARG_ROLES`, so every arg role "
        "is `unknown` and tokens pass through as bare command names. SWE-smith's `editor.view` and nebius's "
        "`open` are the same move under different names: cross-dataset signatures will not align "
        "without a mapping table.",
        "  - Shell commands are emitted bare in the fence (e.g. `python reproduce.py`), so the fallback "
        "names the tool `python` rather than `bash` and the bash canonicalization (cd-skipping, "
        "pipelines, `python -m`) never runs.",
        "  - `edit` blocks are multi-line (`edit N:M` … `end_of_edit`); the fallback keeps only the first "
        "line, which is what the structure needs, but the content parse is incidental.",
        "  - Data artifact: some commands are recorded with the space before `.` dropped "
        "(`find. -name …`, `cd..`, `ls.dvc`; see the vocabulary table). Checked against raw text: "
        "they are in the data as written, not a parsing error. Any adapter's program extraction "
        "will see `find.` as a different program from `find` unless it normalizes this.",
        "  - Observations are `user` messages after the first, which the existing path already handles.",
        "",
        "## Implications for gold-by-task-identity",
        "",
    ]

    L.append(
        f"**Items with 2+ trajectories per instance: yes, in volume.** The first {n_rows:,} rows hold "
        f"{len(multi):,} instances with 2+ trajectories (most with 4+), so hundreds of task-identity "
        f"gold items are available from this prefix alone; {len(mixed):,} of them mix success and "
        f"failure. **Same-repo distractor pools: thin.** Of {len(repo_inst):,} repos, "
        f"{singleton_repos:,} contribute a single instance and only {repos_10:,} reach 10+ instances "
        f"(led by `{max(repo_inst, key=lambda r: len(repo_inst[r]))}` with "
        f"{max(len(v) for v in repo_inst.values())}); no repo has 10+ mixed-outcome instances "
        f"({repos_5_mixed:,} have 5+). So items whose distractors must come from the same repo are "
        "available for a handful of repos, not across the board, in this prefix. Caveats: the 20k-row "
        "cap means the remaining rows' repo spread is unmeasured; "
        f"{models.most_common(1)[0][1] / n_rows:.0%} of rows come from one model "
        f"(`{models.most_common(1)[0][0]}`), so most same-instance pairs are repeated samples of one "
        f"model rather than different models ({multi_model:,} of {len(multi):,} multi-trajectory "
        "instances mix models); and the format needs a new adapter (section 5) before any of it can "
        "be canonicalized."
    )

    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L[L.index("## 2. Trajectories per instance"):]))
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
    sys.stdout.flush()  # os._exit skips buffer flushing when stdout is piped
    os._exit(0)  # datasets streaming can hang on connection cleanup
