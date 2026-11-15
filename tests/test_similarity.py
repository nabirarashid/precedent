"""Tests for structural similarity v0 and find_similar.

Run: python -m pytest tests/ -q
"""

import pytest

from precedent.canonicalize import build_signature
from precedent.records import Source, Step, StepKind, TraceRecord
from precedent.similarity import SignatureStore, find_similar, motif_similarity, seq_similarity


def step_for(token: str, i: int) -> Step:
    """A real tool call that canonicalizes back to `token` (round-trips the canonicalizer)."""
    if token.startswith("bash."):
        args, name = {"command": token[len("bash."):]}, "bash"
    elif token.startswith("editor."):
        args, name = {"command": token[len("editor."):]}, "str_replace_editor"
    else:
        args, name = {}, token
    return Step(step_index=i, kind=StepKind.TOOL_CALL, tool_name=name, arg_values=args)


def run(run_id: str, *tokens: str) -> TraceRecord:
    return TraceRecord(run_id=run_id, source=Source.SWE_AGENT, source_ref=run_id,
                       steps=[step_for(t, i) for i, t in enumerate(tokens)])


OPEN = ("bash.find",)
CLOSE = ("submit", "bash.rm", "submit")
PYTEST = "bash.python -m pytest"

# Every run carries the scaffold; middles differ. N=6, so scaffold tokens get IDF 0.
STORE_RUNS = [
    run("A", *OPEN, "editor.view", "editor.view", "editor.create", *CLOSE),
    run("B", *OPEN, "editor.str_replace", "bash.grep", *CLOSE),
    run("C", *OPEN, PYTEST, "editor.view", *CLOSE),
    run("D", *OPEN, PYTEST, "bash.grep", *CLOSE),
    run("F", *OPEN, "editor.view", "editor.str_replace", *CLOSE),
    run("G", *OPEN, "editor.view", "bash.grep", *CLOSE),
]


@pytest.fixture
def store():
    return SignatureStore(STORE_RUNS)


def sig(run_id, store):
    return next(s for s in store.signatures if s.run_id == run_id)


def test_round_trip_helper():
    assert build_signature(run("x", *OPEN, PYTEST, *CLOSE)).canonical_steps == \
        ["bash.find", PYTEST, "submit", "bash.rm", "submit"]


@pytest.mark.parametrize("scorer", [motif_similarity, seq_similarity])
def test_identical_signatures_score_one(scorer):
    a = build_signature(run("a", *OPEN, "editor.view", PYTEST, *CLOSE))
    b = build_signature(run("b", *OPEN, "editor.view", PYTEST, *CLOSE))
    assert scorer(a, b) == pytest.approx(1.0)


@pytest.mark.parametrize("scorer", [motif_similarity, seq_similarity])
def test_disjoint_signatures_score_zero(scorer):
    a = build_signature(run("a", "editor.view", "editor.create"))
    b = build_signature(run("b", "bash.grep", PYTEST))
    assert scorer(a, b) == 0.0


def test_store_doc_freq_and_idf(store):
    assert store.doc_freq["bash.find"] == 6
    assert store.doc_freq["submit"] == 6          # counted once per run, not per occurrence
    assert store.doc_freq[PYTEST] == 2
    idf = store.idf_weights()
    assert idf["bash.find"] == idf["submit"] == idf["bash.rm"] == 0.0
    assert idf[PYTEST] > idf["editor.view"] > 0.0


@pytest.mark.parametrize("scorer", [motif_similarity, seq_similarity])
def test_scaffold_only_pair_scores_lower_weighted(store, scorer):
    """A and B share only the bash.find opener and submit/rm/submit closer."""
    a, b = sig("A", store), sig("B", store)
    w = store.idf_weights()
    assert scorer(a, b, w) < scorer(a, b)


def test_rare_shared_token_beats_common_shared_token_weighted(store):
    """C/D share the rare bash.python -m pytest; F/G share only the common
    editor.view. Unweighted they tie; IDF separates them."""
    w = store.idf_weights()
    c, d, f, g = (sig(r, store) for r in "CDFG")
    assert motif_similarity(c, d) == pytest.approx(motif_similarity(f, g))
    assert motif_similarity(c, d, w) > motif_similarity(f, g, w)


def test_find_similar_excludes_query_and_ranks_all_when_k_large(store):
    query = STORE_RUNS[0]
    results = find_similar(query, store, k=100)
    assert [s.run_id for s, _ in results if s.run_id == "A"] == []
    assert len(results) == len(store) - 1
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)


def test_find_similar_accepts_signature_and_respects_k(store):
    results = find_similar(sig("C", store), store, k=2, scorer="seq")
    assert len(results) == 2
    assert results[0][0].run_id == "D"   # the only other run sharing the rare PYTEST
    assert results[0][1] > results[1][1]


def test_unknown_scorer_raises(store):
    with pytest.raises(ValueError):
        find_similar(STORE_RUNS[0], store, scorer="embedding")
