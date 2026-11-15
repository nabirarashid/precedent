"""Precedent similarity v0: structural scorers over Signatures, and find_similar.

Everything here reads Signatures only, never TraceRecords' SURFACE fields:
records are canonicalized on the way in (canonicalize.build_signature), so
the field quarantine is inherited, not re-implemented.

Structural stopwords (spec section 5): scaffold motifs such as the bash.find
opener and the submit → bash.rm → submit closer appear in nearly every run
and would otherwise dominate similarity. They are downweighted by IDF,
log(N / df), computed from the store's own runs, never from a hardcoded list.

Stage one only. The Oct 19 design (docs/notes/m1-spec-notes.md) reranks the
structurally-similar set lexically in a second stage; that is a later,
designed experiment and deliberately absent here.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Callable, Iterable, Mapping, Optional, Union

from .canonicalize import Signature, build_signature
from .records import TraceRecord

Weights = Mapping[str, float]


class SignatureStore:
    """Signatures for a set of runs, plus document frequencies over their tokens."""

    def __init__(self, records: Iterable[TraceRecord]):
        self.signatures: list[Signature] = [build_signature(r) for r in records]
        # df(token) = number of runs containing the token at least once
        self.doc_freq: Counter = Counter()
        for sig in self.signatures:
            self.doc_freq.update(set(sig.canonical_steps))

    def __len__(self) -> int:
        return len(self.signatures)

    def idf_weights(self) -> dict[str, float]:
        """weight(token) = log(N / df(token)). A token in every run weighs 0."""
        n = len(self.signatures)
        return {t: math.log(n / df) for t, df in self.doc_freq.items()}


def _w(weights: Optional[Weights], token: str) -> float:
    # Tokens absent from the weights (or no weights at all) count as 1.0.
    return 1.0 if weights is None else weights.get(token, 1.0)


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


def motif_similarity(a: Signature, b: Signature, weights: Optional[Weights] = None) -> float:
    """Cosine similarity of motif_counts() vectors, each count scaled by its
    token's weight. Returns 0.0 when either vector is zero."""
    va = {t: c * _w(weights, t) for t, c in a.motif_counts().items()}
    vb = {t: c * _w(weights, t) for t, c in b.motif_counts().items()}
    dot = sum(v * vb.get(t, 0.0) for t, v in va.items())
    norm = math.sqrt(sum(v * v for v in va.values())) * math.sqrt(sum(v * v for v in vb.values()))
    return dot / norm if norm > 0 else 0.0


SCORERS: dict[str, Callable[[Signature, Signature, Optional[Weights]], float]] = {
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
    token counts) or "seq" (normalized longest common subsequence). With
    `weighted=True`, tokens common to most runs in the store (harness
    scaffolding) count for less, by IDF. Returns (signature, score) pairs,
    best first, scores in [0, 1]. The query's own run is never returned.
    """
    if scorer not in SCORERS:
        raise ValueError(f"unknown scorer {scorer!r}; expected one of {sorted(SCORERS)}")
    score = SCORERS[scorer]
    sig = query if isinstance(query, Signature) else build_signature(query)

    weights = None
    if weighted:
        weights = store.idf_weights()
        # A query token the store has never seen is treated as maximally rare (df = 1).
        unseen = math.log(len(store)) if len(store) else 0.0
        weights.update({t: unseen for t in sig.canonical_steps if t not in weights})

    scored = [(s, score(sig, s, weights)) for s in store.signatures if s.run_id != sig.run_id]
    scored.sort(key=lambda pair: pair[1], reverse=True)  # stable: ties keep store order
    return scored[:k]
