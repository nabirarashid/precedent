"""Precedent similarity v0: structural scorers over Signatures, and find_similar.

Everything here reads Signatures only, never TraceRecords' SURFACE fields:
records are canonicalized on the way in (canonicalize.build_signature), so
the field quarantine is inherited, not re-implemented.

The unit of structure is the n-gram (1- to 3-grams of canonical tokens), not
the single token. Unigrams alone degenerate on SWE-smith: a ~26-token vocab
where the core actions appear in every run, so almost nothing distinguishes
runs. Order-bearing grams (editor.view → bash.grep) carry the behavior.

Structural stopwords (spec section 5): scaffold motifs such as the bash.find
opener and the submit → bash.rm → submit closer appear in nearly every run
and would otherwise dominate similarity. They are downweighted by smoothed
IDF, log((1 + N) / (1 + df)) + 1, computed from the store's own runs, never
from a hardcoded list. Ubiquitous grams floor at 1.0: de-emphasized, not erased.

Stage one only. The Oct 19 design (docs/notes/m1-spec-notes.md) reranks the
structurally-similar set lexically in a second stage; that is a later,
designed experiment and deliberately absent here.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Callable, Hashable, Iterable, Mapping, Optional, Union

from .canonicalize import Signature, build_signature
from .records import TraceRecord

Weights = Mapping[Hashable, float]
Gram = tuple[str, ...]

N_MAX = 3


def ngram_counts(signature: Signature, n_max: int = N_MAX) -> Counter:
    """Counts of every 1- to n_max-gram of the canonical token sequence, keyed by tuple."""
    steps = signature.canonical_steps
    return Counter(
        tuple(steps[i:i + n]) for n in range(1, n_max + 1) for i in range(len(steps) - n + 1)
    )


def _smoothed_idf(n_runs: int, df: int) -> float:
    return math.log((1 + n_runs) / (1 + df)) + 1


class SignatureStore:
    """Signatures for a set of runs, plus document frequencies over their n-grams."""

    def __init__(self, records: Iterable[TraceRecord], n_max: int = N_MAX):
        self.n_max = n_max
        self.signatures: list[Signature] = [build_signature(r) for r in records]
        # df(gram) = number of runs containing the gram at least once
        self.doc_freq: Counter = Counter()
        for sig in self.signatures:
            self.doc_freq.update(set(ngram_counts(sig, n_max)))

    def __len__(self) -> int:
        return len(self.signatures)

    def idf_weights(self) -> dict[Gram, float]:
        """weight(gram) = log((1 + N) / (1 + df(gram))) + 1. A gram in every run weighs 1.0."""
        n = len(self.signatures)
        return {g: _smoothed_idf(n, df) for g, df in self.doc_freq.items()}

    def unseen_weight(self) -> float:
        """Weight for a gram no run in the store contains (df = 0): the maximum."""
        return _smoothed_idf(len(self.signatures), 0)


def _w(weights: Optional[Weights], key: Hashable) -> float:
    # Keys absent from the weights (or no weights at all) count as 1.0.
    return 1.0 if weights is None else weights.get(key, 1.0)


def seq_similarity(a: Signature, b: Signature, weights: Optional[Weights] = None) -> float:
    """Normalized longest common subsequence: LCS length / max sequence length.

    With weights, matched tokens contribute their weight and each sequence's
    length is its total weight. Returns 0.0 when either side has no weight."""
    x, y = a.canonical_steps, b.canonical_steps
    prev = [0.0] * (len(y) + 1)
    for tx in x:
        cur = [0.0]
        for j, ty in enumerate(y, 1):
            if tx == ty:
                cur.append(prev[j - 1] + _w(weights, tx))
            else:
                cur.append(max(prev[j], cur[j - 1]))
        prev = cur
    denom = max(sum(_w(weights, t) for t in x), sum(_w(weights, t) for t in y))
    return prev[-1] / denom if denom > 0 else 0.0


def motif_similarity(a: Signature, b: Signature, weights: Optional[Weights] = None,
                     n_max: int = N_MAX) -> float:
    """Cosine similarity of 1- to n_max-gram count vectors, each count scaled
    by its gram's weight. Returns 0.0 when either vector is zero."""
    va = {g: c * _w(weights, g) for g, c in ngram_counts(a, n_max).items()}
    vb = {g: c * _w(weights, g) for g, c in ngram_counts(b, n_max).items()}
    dot = sum(v * vb.get(g, 0.0) for g, v in va.items())
    norm = math.sqrt(sum(v * v for v in va.values())) * math.sqrt(sum(v * v for v in vb.values()))
    return dot / norm if norm > 0 else 0.0


SCORERS: dict[str, Callable[..., float]] = {
    "motif": motif_similarity,
    "seq": seq_similarity,
}


def find_similar(
    query: Union[TraceRecord, Signature],
    store: SignatureStore,
    k: int = 5,
    scorer: str = "motif",
    weighted: bool = True,
) -> list[tuple[Signature, float]]:
    """Find the k runs in `store` most structurally similar to `query`.

    `query` is a TraceRecord or a Signature. `scorer` is "motif" (cosine over
    counts of short action sequences: single steps, pairs, triples) or "seq"
    (normalized longest common subsequence). With `weighted=True`, patterns
    common to most runs in the store (harness scaffolding) count for less, by
    IDF. Returns (signature, score) pairs, best first, scores in [0, 1]. The
    query's own run is never returned.
    """
    if scorer not in SCORERS:
        raise ValueError(f"unknown scorer {scorer!r}; expected one of {sorted(SCORERS)}")
    sig = query if isinstance(query, Signature) else build_signature(query)

    weights: Optional[dict] = None
    if weighted:
        weights = store.idf_weights()
        # A query gram the store has never seen is treated as maximally rare (df = 0).
        unseen = store.unseen_weight()
        weights.update({g: unseen for g in ngram_counts(sig, store.n_max) if g not in weights})
        if scorer == "seq":  # seq aligns single tokens: use the unigram weights
            weights = {g[0]: w for g, w in weights.items() if len(g) == 1}

    if scorer == "motif":
        score = lambda s: motif_similarity(sig, s, weights, store.n_max)  # noqa: E731
    else:
        score = lambda s: seq_similarity(sig, s, weights)  # noqa: E731

    scored = [(s, score(s)) for s in store.signatures if s.run_id != sig.run_id]
    scored.sort(key=lambda pair: pair[1], reverse=True)  # stable: ties keep store order
    return scored[:k]
