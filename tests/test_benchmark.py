"""Tests for the track-1 benchmark harness (items, chance, metrics).

Run: python -m pytest tests/ -q
"""

import pytest

from precedent.benchmark import (
    build_items,
    chance_mrr,
    chance_recall_at_k,
    pull_rate,
    recall_at_k,
    reciprocal_rank,
)

# A hand-computable 5-trace store: q is the eligible query under test.
LABELS = [
    {"trajectory_id": "q", "task_type_name": "T1", "target_object": "apple",
     "goal_receptacle": "fridge"},
    {"trajectory_id": "a", "task_type_name": "T1", "target_object": "pear",
     "goal_receptacle": "bed"},          # gold: same type, diff object AND receptacle
    {"trajectory_id": "b", "task_type_name": "T1", "target_object": "apple",
     "goal_receptacle": "bed"},          # same type but same object: not gold, not dopp
    {"trajectory_id": "c", "task_type_name": "T2", "target_object": "apple",
     "goal_receptacle": "desk"},         # doppelganger: diff type, shares the object
    {"trajectory_id": "d", "task_type_name": "T2", "target_object": "egg",
     "goal_receptacle": None},           # incomplete labels: candidate only
]


@pytest.fixture
def items():
    return {i.query_id: i for i in build_items(LABELS)}


def test_incomplete_label_queries_excluded_but_counted_as_candidates(items):
    assert not items["d"].eligible
    assert items["d"].gold == [] and items["d"].chance == {}
    assert items["q"].eligible
    assert items["q"].n_candidates == 4  # d still in the haystack


def test_gold_and_doppelganger_sets(items):
    q = items["q"]
    assert q.gold == ["a"]
    assert q.doppelgangers == ["c"]
    assert "q" not in q.gold  # gold never contains the query
    assert not set(q.gold) & set(q.doppelgangers)  # disjoint by construction


def test_all_items_gold_dopp_disjoint_and_queryless(items):
    for item in items.values():
        assert item.query_id not in item.gold
        assert item.query_id not in item.doppelgangers
        assert not set(item.gold) & set(item.doppelgangers)


def test_hand_computed_hypergeometric_chance(items):
    q = items["q"]  # N=4 candidates, G=1 gold
    assert q.chance["recall@1"] == pytest.approx(1 / 4)
    assert q.chance["recall@5"] == pytest.approx(1.0)  # k capped at N
    # E[1/rank] with 1 gold uniform over 4 ranks: (1 + 1/2 + 1/3 + 1/4) / 4
    assert q.chance["mrr"] == pytest.approx((1 + 1 / 2 + 1 / 3 + 1 / 4) / 4)


def test_chance_functions_edge_cases():
    assert chance_recall_at_k(4, 2, 1) == pytest.approx(0.5)
    assert chance_recall_at_k(4, 2, 3) == pytest.approx(1.0)  # C(2,3)=0
    assert chance_mrr(2, 1) == pytest.approx(0.75)  # 1/2 * 1 + 1/2 * 1/2
    assert chance_mrr(5, 0) == 0.0


def test_metric_functions_worked_example():
    ranking, gold = ["x", "g1", "y", "g2"], {"g1", "g2"}
    assert recall_at_k(ranking, gold, 1) == 0.0
    assert recall_at_k(ranking, gold, 2) == 1.0
    assert reciprocal_rank(ranking, gold) == pytest.approx(0.5)
    assert reciprocal_rank(["z"], gold) == 0.0
    assert pull_rate(["d1", "x", "d2"], {"d1", "d2"}, k=3) == pytest.approx(2 / 3)
