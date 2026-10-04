"""Smoke tests for the v0 record schema.

Run: python -m pytest tests/ -q   (pip install pytest if needed)
"""

from precedent.records import (
    FIELD_CLASSES,
    FieldClass,
    OutcomeLabel,
    Source,
    Step,
    StepKind,
    StepStatus,
    TraceRecord,
    is_scorable,
    structural_fields,
    surface_fields,
)


def make_minimal_record() -> TraceRecord:
    return TraceRecord(
        run_id="r1",
        source=Source.ALFWORLD,
        source_ref="trial_001",
        task_type="pick_heat_then_place",
        steps=[
            Step(step_index=0, kind=StepKind.TOOL_CALL, tool_name="goto",
                 arg_types=["receptacle"], arg_values={"target": "fridge 1"},
                 depends_on=[]),
            Step(step_index=1, kind=StepKind.TOOL_CALL, tool_name="take",
                 arg_types=["object", "receptacle"],
                 arg_values={"obj": "potato 2", "from": "fridge 1"},
                 depends_on=[0]),
            Step(step_index=2, kind=StepKind.TOOL_CALL, tool_name="heat",
                 arg_types=["object", "appliance"],
                 arg_values={"obj": "potato 2", "with": "microwave 1"},
                 depends_on=[1], status=StepStatus.ERROR),
            Step(step_index=3, kind=StepKind.TOOL_CALL, tool_name="heat",
                 arg_types=["object", "appliance"],
                 arg_values={"obj": "potato 2", "with": "microwave 1"},
                 depends_on=[1], status=StepStatus.RETRY, retry_of=2),
        ],
        outcome_label=OutcomeLabel.SUCCESS,
        outcome_source="alfworld_env",
    )


def test_record_constructs():
    r = make_minimal_record()
    assert r.run_id == "r1"
    assert len(r.steps) == 4
    assert r.steps[3].retry_of == 2


def test_unknown_vs_independent_dependencies():
    known_independent = Step(step_index=0, kind=StepKind.MODEL_TURN, depends_on=[])
    unknown = Step(step_index=1, kind=StepKind.MODEL_TURN)  # depends_on defaults to None
    assert known_independent.depends_on == []
    assert unknown.depends_on is None
    assert known_independent.depends_on != unknown.depends_on


def test_every_record_and_step_field_is_classified():
    """No field exists without a declared class. New fields must be classified."""
    import dataclasses
    declared = set(FIELD_CLASSES)
    actual = {f.name for f in dataclasses.fields(TraceRecord) if f.name != "steps"}
    actual |= {f.name for f in dataclasses.fields(Step)}
    assert actual == declared, f"unclassified or stale fields: {actual ^ declared}"


def test_surface_fields_are_not_scorable():
    for name in surface_fields():
        assert not is_scorable(name), f"surface field {name} leaked into scoring"
    assert not is_scorable("task_text")
    assert not is_scorable("arg_values")
    assert not is_scorable("text")


def test_structural_fields_are_scorable():
    for name in structural_fields():
        assert is_scorable(name)
    assert is_scorable("tool_name")
    assert is_scorable("arg_types")


def test_unknown_field_is_not_scorable():
    """Fail closed: a field nobody classified must not be scored."""
    assert not is_scorable("embedding_of_task_text")
    assert not is_scorable("nonexistent")


def test_field_classes_are_exactly_three():
    assert set(FieldClass) == {FieldClass.STRUCTURAL, FieldClass.SURFACE, FieldClass.METADATA}
