"""M2: family-gold premise test on SWE-smith.

Candidate redesign under test (measure only, no building): gold = same
mutation family across different repos; doppelganger = same repo across
different families. The family is SWE-smith's mutation operator embedded in
instance_id: `<repo>.<commit>.<family>__<suffix>`, e.g.
django-money__django-money.835c1ab8.func_pm_ctrl_shuffle__viqnyl9u.

Streams the first 1,000 rows of SWE-bench/SWE-smith-trajectories (tool
split) through the existing ingest path, samples pairs
  A. same family, different repo   (candidate GOLD)
  B. same repo, different family   (candidate DOPPELGANGER)
  C. different repo, different family (baseline)
and computes per pair: lexical Jaccard on raw trajectory text (same method
as the nebius audit) and the shipped weighted n-gram motif score over one
SignatureStore of all 1,000 records. Writes docs/notes/family-premise.md.

Run from the repo root (inside the venv):
    python scripts/premise_family_gold.py
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

from precedent.similarity import SignatureStore, motif_similarity

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_nebius_dataset import md_table  # noqa: E402
from audit_nebius_part2 import WORD, above_fraction, hist_label, jaccard  # noqa: E402
from load_sample_traces import get_messages, to_trace_record  # noqa: E402

DATASET = "SWE-bench/SWE-smith-trajectories"
N = 1_000
N_PAIRS = 200
SEED = 0
OUT = Path(__file__).resolve().parent.parent / "docs" / "notes" / "family-premise.md"

GROUPS = {
    "A": "same family, different repo (candidate gold)",
    "B": "same repo, different family (candidate doppelganger)",
    "C": "different repo, different family (baseline)",
}


MUTATION_RE = re.compile(
    r"^(?P<repo>.+)\.(?P<commit>[0-9a-f]{8})\.(?P<family>.+)__[A-Za-z0-9]+$"
)
PR_RE = re.compile(r"^(?P<repo>.+)\.(?P<commit>[0-9a-f]{8})\.pr_\d+$")


def parse_instance(instance_id: str) -> tuple[str, str | None] | None:
    """(repo, family) from `<repo>.<commit>.<family>__<suffix>`, or (repo, None)
    for the second instance class `<repo>.<commit>.pr_<number>` (PR-mirror
    tasks with no mutation operator); None if neither shape.

    Anchored on the 8-hex commit segment, not "before the first dot": repo
    names can contain dots (pdfminer__pdfminer.six)."""
    m = MUTATION_RE.fullmatch(instance_id)
    if m:
        return m.group("repo"), m.group("family")
    m = PR_RE.fullmatch(instance_id)
    if m:
        return m.group("repo"), None
    return None


def word_set(row: dict) -> set[str]:
    """Nebius-audit method: lowercased `\\w+` words >= 3 chars over the raw
    trajectory text. The system prompt is excluded there (it lives outside
    `text`); here that means skipping role=system messages."""
    out: set[str] = set()
    for m in get_messages(row):
        if not isinstance(m, dict) or (m.get("role") or m.get("from")) == "system":
            continue
        content = m.get("content") or m.get("value") or ""
        if not isinstance(content, str):
            content = str(content)
        out.update(w for w in WORD.findall(content.lower()) if len(w) >= 3)
    return out


def stats_row(label: str, vals: list[float]) -> list[str]:
    return [label, str(len(vals)), f"{statistics.mean(vals):.3f}",
            f"{statistics.median(vals):.3f}", f"{min(vals):.3f}", f"{max(vals):.3f}"]


def hist(scores: dict[str, list[float]]) -> list[str]:
    counts = {g: Counter(hist_label(x) for x in v) for g, v in scores.items()}
    labels = [hist_label(i / 10 + 0.05) for i in range(10)]
    rows = [[lab] + [counts[g].get(lab, 0) for g in scores] for lab in labels]
    return md_table(["score"] + [g for g in scores], [r for r in rows if any(r[1:])])


def main() -> None:
    print(f"Streaming first {N} rows of {DATASET} (tool split) ...")
    stream = load_dataset(DATASET, split="tool", streaming=True)
    rows = list(islice(stream, N))

    parsed = [parse_instance(r["instance_id"]) for r in rows]
    bad = [rows[i]["instance_id"] for i, p in enumerate(parsed) if p is None]
    if bad:
        print(f"FAMILY PARSING FAILED for {len(bad)} of {len(rows)} instance_ids. Examples:")
        for ex in bad[:10]:
            print(f"  {ex}")
        print("Stopping without writing the report, per the handoff.")
        return

    # rows with a mutation family; pr_<n> rows (family None) are a separate
    # instance class with no operator, kept in the store but not paired
    fam_idx = [i for i, p in enumerate(parsed) if p[1] is not None]
    pr_rows = [rows[i]["instance_id"] for i, p in enumerate(parsed) if p[1] is None]
    repos = {i: parsed[i][0] for i in fam_idx}
    families = {i: parsed[i][1] for i in fam_idx}
    fam_counts = Counter(families.values())
    print(f"Distinct families found ({len(fam_counts)}): "
          + ", ".join(sorted(fam_counts)))
    print(f"pr_<n> rows (no mutation family, excluded from pairing): {len(pr_rows)}")

    print("Ingesting records and building one SignatureStore ...")
    records = [to_trace_record(r, i) for i, r in enumerate(rows)]
    store = SignatureStore(records)
    weights = store.idf_weights()
    sigs = store.signatures  # same order as records
    print(f"Store: {len(store)} runs, {len(store.doc_freq)} distinct n-grams")

    print("Computing word sets ...")
    wsets = [word_set(r) for r in rows]

    # classify every unordered pair of family-bearing rows, then sample
    rng = random.Random(SEED)
    pools: dict[str, list[tuple[int, int]]] = {"A": [], "B": [], "C": []}
    same_repo_same_family = 0
    for i, j in combinations(fam_idx, 2):
        sr, sf = repos[i] == repos[j], families[i] == families[j]
        if sf and not sr:
            pools["A"].append((i, j))
        elif sr and not sf:
            pools["B"].append((i, j))
        elif not sr and not sf:
            pools["C"].append((i, j))
        else:
            same_repo_same_family += 1
    sampled = {g: rng.sample(p, min(N_PAIRS, len(p))) for g, p in pools.items()}

    lex = {g: [jaccard(wsets[a], wsets[b]) for a, b in pairs] for g, pairs in sampled.items()}
    struct = {g: [motif_similarity(sigs[a], sigs[b], weights) for a, b in pairs]
              for g, pairs in sampled.items()}

    # coverage: how many repos each family appears in
    fam_repos: dict[str, set] = defaultdict(set)
    repo_fams: dict[str, set] = defaultdict(set)
    for i in fam_idx:
        fam_repos[families[i]].add(repos[i])
        repo_fams[repos[i]].add(families[i])

    p_lex_b_gt_a = above_fraction(lex["B"], lex["A"])
    p_struct_a_gt_b = above_fraction(struct["A"], struct["B"])
    gap_lex_ab = statistics.mean(lex["A"]) - statistics.mean(lex["B"])
    gap_struct_ab = statistics.mean(struct["A"]) - statistics.mean(struct["B"])

    L: list = [
        "# Family-gold premise test (SWE-smith) — Nov 19, 2026",
        "",
        f"*Generated by scripts/premise_family_gold.py. First {len(rows):,} rows of "
        f"`{DATASET}` (tool split, streaming). Seed {SEED}. Measurements only; no design "
        "decisions.*",
        "",
        "Premise under test: gold = same mutation family across different repos, doppelganger = "
        "same repo across different families. Repo and family parsed from `instance_id` "
        "(`<repo>.<commit>.<family>__<suffix>`, anchored on the 8-hex commit segment, since repo "
        "names can contain dots: `pdfminer__pdfminer.six`). All "
        f"{len(rows):,} ids parsed; {len(fam_idx):,} carry a mutation family. The other "
        f"{len(pr_rows)} are a second instance class, `<repo>.<commit>.pr_<number>` (PR-mirror "
        "tasks, e.g. " + ", ".join(f"`{x}`" for x in pr_rows[:3]) + "): no mutation operator, each "
        "unique, so they cannot form same-family pairs. They stay in the SignatureStore (IDF "
        "background over all 1,000 runs) and are excluded from the pair pools.",
        "",
        "## 1. Coverage",
        "",
        f"Over the {len(fam_idx):,} family-bearing rows: {len(set(repos.values())):,} distinct "
        f"repos, {len(fam_counts)} distinct families, "
        f"{len(set(rows[i]['instance_id'] for i in fam_idx)):,} distinct instance_ids.",
        "",
        "Families by repos (the design needs families spanning many repos):",
        "",
        md_table(["family", "rows", "distinct repos"],
                 [[f"`{f}`", fam_counts[f], len(fam_repos[f])]
                  for f in sorted(fam_counts, key=lambda f: -fam_counts[f])]),
        "",
        f"Repos with 2+ families (eligible for B pairs): "
        f"{sum(len(v) >= 2 for v in repo_fams.values()):,} of {len(repo_fams):,}; "
        f"median families per repo: {statistics.median(sorted(len(v) for v in repo_fams.values()))}.",
        "",
        "## 2. Sampled pairs",
        "",
        md_table(["type", "", "possible pairs", "sampled"],
                 [[g, GROUPS[g], f"{len(pools[g]):,}", len(sampled[g])] for g in "ABC"]),
        "",
        f"(Same repo AND same family pairs, used by neither side: {same_repo_same_family:,}.)",
        "",
        "## 3. Lexical overlap (Jaccard, words >= 3 chars, nebius-audit method)",
        "",
        md_table(["type", "pairs", "mean", "median", "min", "max"],
                 [stats_row(g, lex[g]) for g in "ABC"]),
        "",
        hist(lex),
        "",
        "## 4. Structural similarity (weighted n-gram motif score, similarity.py as shipped)",
        "",
        f"One SignatureStore over all {len(store)} records; IDF weights from that store.",
        "",
        md_table(["type", "pairs", "mean", "median", "min", "max"],
                 [stats_row(g, struct[g]) for g in "ABC"]),
        "",
        hist(struct),
        "",
        "## 5. Separations",
        "",
        "P(x > y) over all sampled cross-pairs; ties count half. 0.5 = no separation.",
        "",
        md_table(["comparison", "P", "mean gap"], [
            ["**lexical: B > A** (trap works if > 0.5)", f"{p_lex_b_gt_a:.3f}",
             f"mean(A) − mean(B) = {gap_lex_ab:+.3f}"],
            ["**structural: A > B** (signal exists if > 0.5)", f"{p_struct_a_gt_b:.3f}",
             f"mean(A) − mean(B) = {gap_struct_ab:+.3f}"],
            ["lexical: A > C", f"{above_fraction(lex['A'], lex['C']):.3f}",
             f"{statistics.mean(lex['A']) - statistics.mean(lex['C']):+.3f}"],
            ["lexical: B > C", f"{above_fraction(lex['B'], lex['C']):.3f}",
             f"{statistics.mean(lex['B']) - statistics.mean(lex['C']):+.3f}"],
            ["structural: A > C", f"{above_fraction(struct['A'], struct['C']):.3f}",
             f"{statistics.mean(struct['A']) - statistics.mean(struct['C']):+.3f}"],
            ["structural: B > C", f"{above_fraction(struct['B'], struct['C']):.3f}",
             f"{statistics.mean(struct['B']) - statistics.mean(struct['C']):+.3f}"],
        ]),
        "",
        "## Verdict",
        "",
        f"**Lexical trap (same-repo pairs out-word same-family pairs): "
        f"{'holds' if p_lex_b_gt_a > 0.5 else 'does not hold'}.** "
        f"P(lexical: B > A) = {p_lex_b_gt_a:.3f}; mean Jaccard A = "
        f"{statistics.mean(lex['A']):.3f}, B = {statistics.mean(lex['B']):.3f} "
        f"(gap {gap_lex_ab:+.3f}). "
        f"**Structural signal (scorer rates same-family-cross-repo above "
        f"same-repo-cross-family): {'holds' if p_struct_a_gt_b > 0.5 else 'does not hold'}.** "
        f"P(structural: A > B) = {p_struct_a_gt_b:.3f}; mean motif score A = "
        f"{statistics.mean(struct['A']):.3f}, B = {statistics.mean(struct['B']):.3f} "
        f"(gap {gap_struct_ab:+.3f}). "
        f"Against baseline C: lexical A−C {statistics.mean(lex['A']) - statistics.mean(lex['C']):+.3f}, "
        f"B−C {statistics.mean(lex['B']) - statistics.mean(lex['C']):+.3f}; "
        f"structural A−C {statistics.mean(struct['A']) - statistics.mean(struct['C']):+.3f}, "
        f"B−C {statistics.mean(struct['B']) - statistics.mean(struct['C']):+.3f}.",
        "",
    ]
    lines: list[str] = []
    for x in L:
        lines.extend(x if isinstance(x, list) else [x])
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[lines.index("## 2. Sampled pairs"):]))
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
    sys.stdout.flush()  # os._exit skips buffer flushing when stdout is piped
    os._exit(0)  # datasets streaming can hang on connection cleanup
