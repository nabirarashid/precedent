"""Benchmark harness, track 1 (ALFWorld). Consumes the library as shipped.

Design of record: docs/design/benchmark-design.md. This module holds the
items builder (query/gold/doppelganger sets + exact hypergeometric chance),
the v0 retrieval systems as pluggable callables, and the metric functions.
The runner lives in scripts/run_track1.py.

Definitions implemented here:
- recall@k: fraction of queries with at least one gold id in the top k.
- MRR: mean over queries of 1 / rank of the first gold id.
- chance rows: exact expectations under a uniformly random ranking of the
  candidate store (hypergeometric: gold count G vs store size N).
    recall@k: 1 - C(N-G, k) / C(N, k)
    MRR: sum over ranks r of (1/r) * P(first gold lands at rank r)
- doppelganger pull rate: mean fraction of the top 10 that are
  doppelgangers; chance row is mean(D / N).
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

from .alfworld import load_corpus
from .records import TraceRecord
from .similarity import SignatureStore, find_similar

WORD = re.compile(r"\w+")
K_VALUES = (1, 5, 10)
TOP_POOL = 20  # structural pool size for the rerank system


# ---------------------------------------------------------------- items

@dataclass
class TrackItem:
    query_id: str
    eligible: bool
    gold: list[str] = field(default_factory=list)
    doppelgangers: list[str] = field(default_factory=list)
    n_candidates: int = 0
    chance: dict[str, float] = field(default_factory=dict)  # recall@k + mrr


def chance_recall_at_k(n: int, g: int, k: int) -> float:
    """P(>=1 of g golds in k uniform draws from n candidates), exact."""
    if g <= 0 or n <= 0:
        return 0.0
    k = min(k, n)
    return 1.0 - math.comb(n - g, k) / math.comb(n, k) if n - g >= k else 1.0


def chance_mrr(n: int, g: int) -> float:
    """E[1 / rank of first gold] under a uniformly random ranking, exact."""
    if g <= 0 or n <= 0:
        return 0.0
    expected, p_no_gold_so_far = 0.0, 1.0
    for r in range(1, n - g + 2):
        p_first_here = p_no_gold_so_far * g / (n - r + 1)
        expected += p_first_here / r
        p_no_gold_so_far *= (n - g - r + 1) / (n - r + 1)
    return expected


def build_items(labels: Sequence[Mapping]) -> list[TrackItem]:
    """Track-1 item records from label entries (pure; testable on synthetic
    labels). A query is eligible iff task_type, target_object and
    goal_receptacle are all known. Everything stays a candidate."""
    items = []
    for lab in labels:
        qid = str(lab["trajectory_id"])
        tt, to, gr = lab.get("task_type_name"), lab.get("target_object"), lab.get("goal_receptacle")
        eligible = bool(tt and to and gr)
        gold, dopp = [], []
        if eligible:
            for other in labels:
                oid = str(other["trajectory_id"])
                if oid == qid:
                    continue
                ott, oto, ogr = (other.get("task_type_name"), other.get("target_object"),
                                 other.get("goal_receptacle"))
                if ott == tt and oto != to and ogr and ogr != gr:
                    gold.append(oid)
                elif ott != tt and (oto == to or (ogr and ogr == gr)):
                    dopp.append(oid)
        n = len(labels) - 1
        item = TrackItem(query_id=qid, eligible=eligible, gold=gold,
                         doppelgangers=dopp, n_candidates=n)
        if eligible:
            item.chance = {f"recall@{k}": chance_recall_at_k(n, len(gold), k) for k in K_VALUES}
            item.chance["mrr"] = chance_mrr(n, len(gold))
        items.append(item)
    return items


def build_track1_items(corpus_path: str | Path, labels_path: str | Path,
                       out_path: str | Path | None = None) -> list[TrackItem]:
    labels = json.loads(Path(labels_path).read_text())
    items = build_items(labels)
    if out_path is not None:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps([asdict(i) for i in items], indent=1))
    return items


# ---------------------------------------------------------------- systems

def trajectory_text(traj: Mapping) -> str:
    """Full trajectory text: states + actions, in order."""
    parts = []
    for pair in traj.get("state_action_pairs", []):
        parts.append(pair.get("state") or "")
        parts.append(pair.get("action") or "")
    return "\n".join(parts)


def _tokens(text: str) -> list[str]:
    return WORD.findall(text.lower())


System = Callable[[str], list[str]]  # query_id -> candidate ids, best first


def make_structural(records: Sequence[TraceRecord], store: SignatureStore) -> System:
    by_id = {r.run_id: r for r in records}

    def rank(query_id: str) -> list[str]:
        ranked = find_similar(by_id[query_id], store, k=len(records))
        return [sig.run_id for sig, _ in ranked]
    return rank


def make_bm25(ids: Sequence[str], texts: Mapping[str, str]) -> System:
    from rank_bm25 import BM25Okapi
    corpus_ids = list(ids)
    bm25 = BM25Okapi([_tokens(texts[i]) for i in corpus_ids])

    def rank(query_id: str) -> list[str]:
        scores = bm25.get_scores(_tokens(texts[query_id]))
        order = sorted((i for i in range(len(corpus_ids)) if corpus_ids[i] != query_id),
                       key=lambda i: (-scores[i], corpus_ids[i]))
        return [corpus_ids[i] for i in order]
    return rank


def make_minilm(ids: Sequence[str], texts: Mapping[str, str]) -> System:
    """all-MiniLM-L6-v2 cosine ranking; raises on missing install/model, the
    caller decides whether to continue without it."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    corpus_ids = list(ids)
    emb = model.encode([texts[i] for i in corpus_ids], normalize_embeddings=True,
                       show_progress_bar=False)
    by_id = {i: e for i, e in zip(corpus_ids, emb)}

    def rank(query_id: str) -> list[str]:
        q = by_id[query_id]
        scored = [(float(q @ by_id[i]), i) for i in corpus_ids if i != query_id]
        scored.sort(key=lambda s: (-s[0], s[1]))
        return [i for _, i in scored]
    return rank


def make_rerank(structural: System, texts: Mapping[str, str], top: int = TOP_POOL) -> System:
    """Structural top-`top` reranked by BM25 against the query text; the rest
    keep structural order below them."""
    from rank_bm25 import BM25Okapi

    def rank(query_id: str) -> list[str]:
        base = structural(query_id)
        pool, rest = base[:top], base[top:]
        bm25 = BM25Okapi([_tokens(texts[i]) for i in pool])
        scores = bm25.get_scores(_tokens(texts[query_id]))
        reranked = [pool[i] for i in sorted(range(len(pool)),
                                            key=lambda i: (-scores[i], pool[i]))]
        return reranked + rest
    return rank


# ---------------------------------------------------------------- metrics

def recall_at_k(ranking: Sequence[str], gold: Iterable[str], k: int) -> float:
    gold = set(gold)
    return 1.0 if any(c in gold for c in ranking[:k]) else 0.0


def reciprocal_rank(ranking: Sequence[str], gold: Iterable[str]) -> float:
    gold = set(gold)
    for r, c in enumerate(ranking, 1):
        if c in gold:
            return 1.0 / r
    return 0.0


def pull_rate(ranking: Sequence[str], doppelgangers: Iterable[str], k: int = 10) -> float:
    top = ranking[:k]
    if not top:
        return 0.0
    dopp = set(doppelgangers)
    return sum(c in dopp for c in top) / len(top)


def bootstrap_ci(values: Sequence[float], n_resamples: int = 1000,
                 seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:
    """Percentile bootstrap CI for the mean, over queries."""
    import random
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(n_resamples))
    lo = means[int((alpha / 2) * n_resamples)]
    hi = means[min(int((1 - alpha / 2) * n_resamples), n_resamples - 1)]
    return lo, hi


def mean_word_overlap(query_text: str, gold_texts: Sequence[str]) -> float:
    """Query's mean full-text Jaccard with its gold set (lowercased word sets,
    words >= 3 chars: the audits' method), for the lexical-control split."""
    q = {w for w in _tokens(query_text) if len(w) >= 3}
    if not gold_texts:
        return 0.0
    out = 0.0
    for t in gold_texts:
        g = {w for w in _tokens(t) if len(w) >= 3}
        out += len(q & g) / len(q | g) if q or g else 0.0
    return out / len(gold_texts)
