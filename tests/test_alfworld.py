"""Tests for the AgentInstruct/ALFWorld adapter.

Run: python -m pytest tests/ -q
"""

from pathlib import Path

import pytest

from precedent.alfworld import (
    load_corpus,
    parse_action,
    to_trace_record,
    unrecognized_verbs,
)
from precedent.canonicalize import TOOL_ARG_ROLES, build_signature

DATA = Path(__file__).resolve().parent.parent / "data" / "alfworld"
CORPUS = DATA / "agentinstruct_trajectories.json"
LABELS = DATA / "agentinstruct_task_type_labels.json"


def traj(run_id: str, *actions: str, task: str = "do the thing.") -> dict:
    return {
        "task_instance_id": run_id,
        "task_description": task,
        "state_action_pairs": [
            {"step_id": i + 1, "state": f"obs {i}", "action": a}
            for i, a in enumerate(actions)
        ],
        "total_steps": len(actions),
        "source": "agentinstruct",
    }


def test_parse_action_grammar():
    assert parse_action("go to diningtable 1") == ("go", {"receptacle": "diningtable 1"}, True)
    assert parse_action("take laptop 1 from diningtable 1") == \
        ("take", {"object": "laptop 1", "receptacle": "diningtable 1"}, True)
    assert parse_action("put laptop 1 in/on bed 1") == \
        ("put", {"object": "laptop 1", "receptacle": "bed 1"}, True)
    assert parse_action("heat apple 1 with microwave 1") == \
        ("heat", {"object": "apple 1", "receptacle": "microwave 1"}, True)
    assert parse_action("use desklamp 1") == ("use", {"object": "desklamp 1"}, True)
    assert parse_action("look") == ("look", {}, True)
    verb, args, ok = parse_action("Task succeeded.")
    assert (verb, ok) == ("Task", False) and args == {"raw": "Task succeeded."}


def test_take_put_pair_different_objects_identical_steps():
    """The design's core property: different objects AND receptacles, same signature."""
    a = to_trace_record(traj("a",
                             "go to diningtable 1",
                             "take laptop 1 from diningtable 1",
                             "go to bed 1",
                             "put laptop 1 in/on bed 1"))
    b = to_trace_record(traj("b",
                             "go to shelf 2",
                             "take candle 3 from shelf 2",
                             "go to fridge 1",
                             "put candle 3 in/on fridge 1"))
    sa, sb = build_signature(a), build_signature(b)
    assert sa.canonical_steps == sb.canonical_steps == ["go", "take", "go", "put"]


def test_signature_unchanged_when_objects_renamed():
    actions = [
        "go to countertop 1",
        "take egg 2 from countertop 1",
        "heat egg 2 with microwave 1",
        "put egg 2 in/on fridge 1",
        "examine egg 2",
    ]
    renamed = [a.replace("egg 2", "soapbar 9").replace("countertop", "drawer")
               .replace("microwave", "sinkbasin").replace("fridge", "cabinet")
               for a in actions]
    s1 = build_signature(to_trace_record(traj("x", *actions)))
    s2 = build_signature(to_trace_record(traj("x", *renamed)))
    assert s1.canonical_steps == s2.canonical_steps


def test_object_and_receptacle_roles_declared():
    rec = to_trace_record(traj("r", "take laptop 1 from diningtable 1"))
    assert rec.steps[0].arg_types == ["object:object", "receptacle:receptacle"]
    assert rec.steps[0].arg_values == {"object": "laptop 1", "receptacle": "diningtable 1"}


def test_label_join_sets_task_type_and_task_text():
    rec = to_trace_record(traj("alfworld_0", "look", task="find two laptop and put them in bed."),
                          {"trajectory_id": "alfworld_0", "task_type_name": "pick_two_obj_and_place"})
    assert rec.task_type == "pick_two_obj_and_place"
    assert rec.task_text == "find two laptop and put them in bed."


@pytest.mark.skipif(not (CORPUS.exists() and LABELS.exists()),
                    reason="data/alfworld/ not fetched (scripts/fetch_alfworld_corpus.py)")
def test_verb_table_covers_the_real_corpus():
    import json
    records = load_corpus(CORPUS, LABELS)
    assert len(records) == 336
    assert all(r.task_type for r in records)
    total = sum(len(r.steps) for r in records)
    trajs = json.loads(CORPUS.read_text())["trajectories"]
    unrec = unrecognized_verbs(trajs)
    # every unrecognized action is a free-text termination line, not a command
    assert sum(unrec.values()) / total < 0.01, unrec
    # every recognized verb is declared in the role table (no silent unknowns)
    recognized = {s.tool_name for r in records for s in r.steps} - set(unrec)
    assert recognized <= set(TOOL_ARG_ROLES), recognized - set(TOOL_ARG_ROLES)
