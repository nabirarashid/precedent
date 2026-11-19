"""M2: nebius audit part 2 — full-dataset counts + lexical overlap check.

Part 1: streams ALL rows of nebius/SWE-agent-trajectories (train split,
streaming=True) with column projection, so only instance_id, model_name and
target are read; trajectories are never downloaded or stored.

Part 2: within the first 20,000 rows (the prefix characterized in part 1 of
the audit), samples up to 200 gold pairs (two trajectories, same instance),
up to 200 doppelganger pairs (same repo, different instance) and up to 200
mixed-model gold pairs (same instance, different models), then re-streams the
prefix to compute word-set Jaccard on raw trajectory text for just those rows.

Appends (or replaces) a dated "Part 2" section in docs/notes/nebius-audit.md.
Measure-and-report only.

Run from the repo root (inside the venv):
    python scripts/audit_nebius_part2.py
"""

from __future__ import annotations

import os
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from itertools import combinations, islice
from pathlib import Path

from datasets import load_dataset

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_nebius_dataset import bucket, md_table, repo_of  # noqa: E402

DATASET = "nebius/SWE-agent-trajectories"
PREFIX = 20_000
N_PAIRS = 200
SEED = 0
DATE = "Nov 19, 2026"
OUT = Path(__file__).resolve().parent.parent / "docs" / "notes" / "nebius-audit.md"
MARKER = "## Part 2"
WORD = re.compile(r"\w+")
HIST_EDGES = [i / 10 for i in range(11)]


# ---------------------------------------------------------------- part 1: full counts

def full_counts():
    stream = load_dataset(DATASET, split="train", streaming=True,
                          columns=["instance_id", "model_name", "target"])
    rows: list[tuple[str, str, bool]] = []
    error = None
    try:
        for row in stream:
            rows.append((row["instance_id"], row["model_name"], bool(row["target"])))
            if len(rows) % 10_000 == 0:
                print(f"  {len(rows):,} rows ...", flush=True)
    except Exception as e:  # report how far we got rather than crash
        error = f"{type(e).__name__}: {e}"
    return rows, error


def summarize(rows):
    by_inst: dict[str, list[tuple[str, bool]]] = defaultdict(list)
    for iid, model, tgt in rows:
        by_inst[iid].append((model, tgt))
    multi = {k: v for k, v in by_inst.items() if len(v) >= 2}
    repo_inst: dict[str, set] = defaultdict(set)
    for iid in by_inst:
        repo_inst[repo_of(iid)].add(iid)
    mixed = {k for k, v in multi.items() if len({t for _, t in v}) == 2}
    multi_model = {k for k, v in multi.items() if len({m for m, _ in v}) >= 2}
    repo_mixed = Counter(repo_of(k) for k in mixed)
    return dict(
        by_inst=by_inst, multi=multi, repo_inst=repo_inst, mixed=mixed,
        multi_model=multi_model, repo_mixed=repo_mixed,
        successes=sum(t for _, _, t in rows),
        models=Counter(m for _, m, _ in rows),
    )


# ---------------------------------------------------------------- part 2: overlap

def words(traj) -> set[str]:
    """Lowercased word set over the trajectory's message `text` fields, words < 3 chars dropped."""
    out: set[str] = set()
    for m in traj:
        out.update(w for w in WORD.findall((m.get("text") or "").lower()) if len(w) >= 3)
    return out


def words_no_issue(traj) -> set[str]:
    """Same, but skipping the first user message (the issue statement)."""
    seen_user = False
    kept = []
    for m in traj:
        if m["role"] == "user" and not seen_user:
            seen_user = True
            continue
        kept.append(m)
    return words(kept)


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a or b else 0.0


def sample_pairs(prefix_rows):
    """Row-index pairs from the prefix. One pair per instance (gold) or per
    instance pair (doppelganger) so heavy instances do not dominate."""
    rng = random.Random(SEED)
    rows_by_inst: dict[str, list[int]] = defaultdict(list)
    for i, (iid, _, _) in enumerate(prefix_rows):
        rows_by_inst[iid].append(i)

    gold_inst = sorted(k for k, v in rows_by_inst.items() if len(v) >= 2)
    gold = [tuple(rng.sample(rows_by_inst[k], 2))
            for k in rng.sample(gold_inst, min(N_PAIRS, len(gold_inst)))]

    mm = []
    for k in sorted(rows_by_inst):
        cands = [(a, b) for a, b in combinations(rows_by_inst[k], 2)
                 if prefix_rows[a][1] != prefix_rows[b][1]]
        if cands:
            mm.append(rng.choice(cands))
    mm = rng.sample(mm, min(N_PAIRS, len(mm)))

    repo_inst: dict[str, list[str]] = defaultdict(list)
    for k in sorted(rows_by_inst):
        repo_inst[repo_of(k)].append(k)
    inst_pairs = [(a, b) for insts in repo_inst.values() for a, b in combinations(insts, 2)]
    eligible_repos = sorted(r for r, v in repo_inst.items() if len(v) >= 2)
    dopp, seen = [], set()
    # uniform over eligible repos, then over instance pairs within the repo
    attempts = 0
    while len(dopp) < min(N_PAIRS, len(inst_pairs)) and attempts < 100_000:
        attempts += 1
        r = rng.choice(eligible_repos)
        a, b = sorted(rng.sample(repo_inst[r], 2))
        if (a, b) in seen:
            continue
        seen.add((a, b))
        dopp.append((rng.choice(rows_by_inst[a]), rng.choice(rows_by_inst[b])))
    return gold, dopp, mm, eligible_repos, len(inst_pairs)


def overlap(prefix_rows, groups: dict[str, list[tuple[int, int]]]):
    needed = {i for pairs in groups.values() for p in pairs for i in p}
    ws: dict[int, set] = {}
    wn: dict[int, set] = {}
    stream = load_dataset(DATASET, split="train", streaming=True,
                          columns=["instance_id", "trajectory"])
    for i, row in enumerate(islice(stream, PREFIX)):
        assert row["instance_id"] == prefix_rows[i][0], f"row order changed at {i}"
        if i in needed:
            ws[i] = words(row["trajectory"])
            wn[i] = words_no_issue(row["trajectory"])
        if (i + 1) % 5000 == 0:
            print(f"  overlap pass: {i + 1:,} rows ...", flush=True)
    return ({g: [jaccard(ws[a], ws[b]) for a, b in p] for g, p in groups.items()},
            {g: [jaccard(wn[a], wn[b]) for a, b in p] for g, p in groups.items()},
            statistics.median(len(ws[i]) for i in needed))


def hist_label(x: float) -> str:
    lo = min(int(x * 10), 9) / 10
    return f"{lo:.1f}-{lo + 0.1:.1f}"


def stats_table(scores: dict[str, list[float]]) -> list[str]:
    return md_table(["group", "pairs", "mean", "median", "min", "max"], [
        [g, len(v), f"{statistics.mean(v):.3f}", f"{statistics.median(v):.3f}",
         f"{min(v):.3f}", f"{max(v):.3f}"] for g, v in scores.items() if v])


def hist_table(scores: dict[str, list[float]]) -> list[str]:
    labels = [hist_label(e + 0.05) for e in HIST_EDGES[:-1]]
    counts = {g: Counter(hist_label(x) for x in v) for g, v in scores.items()}
    rows = [[f"{lab}"] + [counts[g].get(lab, 0) for g in scores] for lab in labels]
    rows = [r for r in rows if any(r[1:])]
    return md_table(["Jaccard"] + list(scores), rows)


def above_fraction(a: list[float], b: list[float]) -> float:
    """P(random gold score > random doppelganger score), ties count half."""
    wins = sum((x > y) + 0.5 * (x == y) for x in a for y in b)
    return wins / (len(a) * len(b))


# ---------------------------------------------------------------- main

def main() -> None:
    print(f"Part 1: streaming all rows of {DATASET} (3 columns) ...")
    rows, error = full_counts()
    S = summarize(rows)
    n_rows, n_inst = len(rows), len(S["by_inst"])
    print(f"  done: {n_rows:,} rows, {n_inst:,} instances, error={error}")

    print(f"Part 2: sampling pairs from the first {PREFIX:,} rows ...")
    prefix = rows[:PREFIX]
    gold, dopp, mm, eligible_repos, n_inst_pairs = sample_pairs(prefix)
    groups = {"gold (same instance)": gold,
              "gold, mixed-model only": mm,
              "doppelganger (same repo, diff instance)": dopp}
    full, no_issue, median_vocab = overlap(prefix, groups)
    G, M, D = full.values()

    def pair_models(pairs):
        return Counter("same model" if prefix[a][1] == prefix[b][1] else "different models"
                       for a, b in pairs)

    def pair_outcomes(pairs):
        return Counter("same outcome" if prefix[a][2] == prefix[b][2] else "different outcomes"
                       for a, b in pairs)

    tpi = Counter(bucket(len(v), [1, 2, 3, 4, 10, 50]) for v in S["by_inst"].values())
    ipr = Counter(bucket(len(s), [1, 2, 5, 10, 50]) for s in S["repo_inst"].values())
    repos_5 = sum(len(s) >= 5 for s in S["repo_inst"].values())
    repos_10 = sum(len(s) >= 10 for s in S["repo_inst"].values())
    repos_5_mixed = sum(c >= 5 for c in S["repo_mixed"].values())
    repos_10_mixed = sum(c >= 10 for c in S["repo_mixed"].values())
    top_model, top_model_rows = S["models"].most_common(1)[0]
    complete = error is None

    L = [
        f"{MARKER} ({DATE}): full-dataset counts + lexical overlap",
        "",
        "*Generated by scripts/audit_nebius_part2.py. Measurements only; no design decisions.*",
        "",
        "### Part 2.1: full-dataset distributions",
        "",
        (f"Streamed **all {n_rows:,} rows** of split `train` (streaming=True, column projection: only "
         "`instance_id`, `model_name`, `target` were read; no trajectories downloaded or stored)."
         if complete else
         f"**Streaming stopped after {n_rows:,} rows** with `{error}`; numbers below cover that prefix."),
        "",
        md_table(["", "first 20k rows (part 1)", "full dataset"], [
            ["rows", "20,000", f"{n_rows:,}"],
            ["instances", "916", f"{n_inst:,}"],
            ["instances with 2+ trajectories", "914", f"{len(S['multi']):,}"],
            ["instances with 2+ different models", "135", f"{len(S['multi_model']):,}"],
            ["repos", "517", f"{len(S['repo_inst']):,}"],
            ["repos with 5+ instances", "22", f"{repos_5:,}"],
            ["repos with 10+ instances", "8", f"{repos_10:,}"],
            ["success share", "16.5%", f"{S['successes'] / n_rows:.1%}"],
            ["mixed-outcome instances", "211", f"{len(S['mixed']):,}"],
            ["repos with 5+ / 10+ mixed-outcome instances", "3 / 0",
             f"{repos_5_mixed:,} / {repos_10_mixed:,}"],
        ]),
        "",
        "Trajectories per instance:",
        "",
        md_table(["trajectories", "instances"],
                 [[b, f"{tpi.get(b, 0):,}"] for b in ["1", "2", "3", "4-9", "10-49", "50+"]]),
        "",
        f"Max trajectories for one instance: {max(len(v) for v in S['by_inst'].values())}.",
        "",
        "Instances per repo:",
        "",
        md_table(["instances", "repos"],
                 [[b, f"{ipr.get(b, 0):,}"] for b in ["1", "2-4", "5-9", "10-49", "50+"]]),
        "",
        "Top 10 repos by instance count:",
        "",
        md_table(["repo", "instances", "with 2+ trajectories", "mixed-outcome", "with 2+ models"],
                 [[f"`{r}`", len(s), sum(k in S["multi"] for k in s), S["repo_mixed"].get(r, 0),
                   sum(k in S["multi_model"] for k in s)]
                  for r, s in sorted(S["repo_inst"].items(), key=lambda kv: (-len(kv[1]), kv[0]))[:10]]),
        "",
        "Outcome mix:",
        "",
        md_table(["", "trajectories", "share"], [
            ["success (`target` true)", f"{S['successes']:,}", f"{S['successes'] / n_rows:.1%}"],
            ["failure (`target` false)", f"{n_rows - S['successes']:,}",
             f"{(n_rows - S['successes']) / n_rows:.1%}"],
        ]),
        "",
        f"Of {len(S['multi']):,} instances with 2+ trajectories: {len(S['mixed']):,} mixed-outcome, "
        f"{sum(all(t for _, t in v) for v in S['multi'].values()):,} all success, "
        f"{sum(not any(t for _, t in v) for v in S['multi'].values()):,} all failure. "
        f"Mixed-model and mixed-outcome: {len(S['mixed'] & S['multi_model']):,}.",
        "",
        "Models:",
        "",
        md_table(["model_name", "rows", "share"],
                 [[f"`{m}`", f"{c:,}", f"{c / n_rows:.1%}"] for m, c in S["models"].most_common()]),
        "",
        "### Part 2.2: lexical overlap, gold vs doppelgangers (first 20k rows)",
        "",
        f"Pairs sampled with seed {SEED}. Gold: one random pair of trajectories from each of "
        f"{len(gold)} randomly chosen instances with 2+ trajectories. Mixed-model gold: one random "
        f"different-model pair from each of {len(mm)} instances (all such instances in the prefix"
        f"{'' if len(mm) < N_PAIRS else ', capped'}). Doppelganger: {len(dopp)} distinct same-repo "
        f"instance pairs, repo drawn uniformly from the {len(eligible_repos)} repos with 2+ instances "
        f"({n_inst_pairs:,} possible instance pairs), one random trajectory per instance.",
        "",
        "Score: Jaccard over lowercased word sets (`\\w+`, words shorter than 3 chars dropped) of the "
        "trajectory's message `text` fields: issue statement, every `ai` message, every observation. "
        "The system prompt lives in `system_prompt`, not `text`, so it is not included. "
        f"Median word-set size per trajectory: {median_vocab:,.0f}.",
        "",
        "Composition of the sampled pairs:",
        "",
        md_table(["group", "same model", "different models", "same outcome", "different outcomes"],
                 [[g, pair_models(p)["same model"], pair_models(p)["different models"],
                   pair_outcomes(p)["same outcome"], pair_outcomes(p)["different outcomes"]]
                  for g, p in groups.items()]),
        "",
        "**Full trajectory text (as specified):**",
        "",
        stats_table(full),
        "",
        hist_table(full),
        "",
        "**Sensitivity check: same, excluding the first user message (the issue statement).** Gold "
        "pairs share the issue text by construction, so this shows how much of the gap is the shared "
        "task description versus what the agents wrote and saw:",
        "",
        stats_table(no_issue),
        "",
        hist_table(no_issue),
        "",
        "Separation (probability a random gold pair scores higher than a random doppelganger pair; "
        "0.5 = no separation, 1.0 = every gold pair above every doppelganger pair):",
        "",
        md_table(["comparison", "full text", "excluding issue"], [
            ["gold vs doppelganger", f"{above_fraction(G, D):.3f}",
             f"{above_fraction(list(no_issue.values())[0], list(no_issue.values())[2]):.3f}"],
            ["mixed-model gold vs doppelganger", f"{above_fraction(M, D):.3f}",
             f"{above_fraction(list(no_issue.values())[1], list(no_issue.values())[2]):.3f}"],
            ["gold vs mixed-model gold", f"{above_fraction(G, M):.3f}",
             f"{above_fraction(list(no_issue.values())[0], list(no_issue.values())[1]):.3f}"],
        ]),
        "",
        "### Part 2 readings (where the numbers cut against earlier assumptions)",
        "",
        f"- **Same-repo pools are less thin than part 1 suggested.** Part 1 measured a prefix of "
        f"{PREFIX:,} rows and found 8 repos with 10+ instances and none with 10+ mixed-outcome "
        f"instances. Over all {n_rows:,} rows: {repos_10:,} repos with 10+ instances, {repos_5:,} "
        f"with 5+, and {repos_10_mixed:,} with 10+ mixed-outcome instances. Part 1's \"thin\" verdict "
        "was a prefix artifact in degree, though the distribution is still long-tailed "
        f"({ipr.get('1', 0):,} of {len(S['repo_inst']):,} repos contribute one instance).",
        f"- **Mixed-model gold stays a minority:** {len(S['multi_model']):,} of "
        f"{len(S['multi']):,} multi-trajectory instances; {top_model_rows / n_rows:.1%} of rows "
        f"are `{top_model}`. Several large repos (`iterative__dvc`, `pvlib__pvlib-python`, "
        "`sqlfluff__sqlfluff`, `pydicom__pydicom`) have no mixed-model instances at all.",
        f"- **Gold pairs are systematically more word-similar than same-repo doppelgangers, and "
        f"by a wide margin.** Mean Jaccard {statistics.mean(G):.3f} vs {statistics.mean(D):.3f}; a "
        f"random gold pair outscores a random doppelganger pair {above_fraction(G, D):.0%} of the "
        f"time. This holds for mixed-model gold ({above_fraction(M, D):.0%}) and with the issue "
        f"statement removed ({above_fraction(list(no_issue.values())[0], list(no_issue.values())[2]):.0%}), "
        "so it is neither a same-model resampling effect nor only the shared task text. Mixed-model "
        f"gold is barely less word-similar than all gold ({above_fraction(G, M):.0%} separation). "
        "If the benchmark assumes same-repo doppelgangers are lexical traps (word-similar to the "
        "query but wrong), this measurement contradicts it at the raw-text level: under task-identity "
        "gold, a plain word-overlap baseline already has a strong signal. Not separated here: how much "
        "of the remaining gap comes from observations of the same files (same instance means same "
        "code on screen) versus the agents' own actions.",
        "",
    ]
    lines = []
    for x in L:
        lines.extend(x if isinstance(x, list) else [x])
    section = "\n".join(lines) + "\n"

    text = OUT.read_text()
    if MARKER in text:  # replace an earlier part 2, keep part 1 intact
        text = text[:text.index(MARKER)].rstrip("\n") + "\n"
    OUT.write_text(text + "\n" + section)
    print(section)
    print(f"Appended part 2 to {OUT}")


if __name__ == "__main__":
    main()
    sys.stdout.flush()  # os._exit skips buffer flushing when stdout is piped
    os._exit(0)  # datasets streaming can hang on connection cleanup
