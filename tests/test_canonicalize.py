"""Tests for the canonicalizer v0 (spec requirements in docs/notes/m1-spec-notes.md).

Run: python -m pytest tests/ -q
"""

import pytest

from precedent.canonicalize import (
    UNKNOWN_ROLE,
    Signature,
    _split_command,
    arg_role,
    arg_roles,
    build_signature,
    canonical_tool,
)
from precedent.records import OutcomeLabel, Source, Step, StepKind, TraceRecord


def call(tool_name, i=0, **args) -> Step:
    return Step(step_index=i, kind=StepKind.TOOL_CALL, tool_name=tool_name, arg_values=args)


@pytest.mark.parametrize("step, expected", [
    # sub-action lifting (spec req #2)
    (call("str_replace_editor", command="view", path="/testbed/a.py"), "editor.view"),
    (call("str_replace_editor", command="create", path="/testbed/r.py", file_text="x"), "editor.create"),
    (call("str_replace_editor", command="str_replace", path="/testbed/a.py",
          old_str="a", new_str="b"), "editor.str_replace"),
    # bash split by program (spec req #3)
    (call("bash", command="find /testbed -name x"), "bash.find"),
    # compound commands (spec req #5)
    (call("bash", command="cd /testbed && python repro.py"), "bash.python"),
    (call("bash", command="cd a && python -m pytest tests/"), "bash.python -m pytest"),
    (call("bash", command="cd /testbed; cd src"), "bash.cd"),  # all-cd fallback
    # pipelines: the first component is the salient program, not the tail
    (call("bash", command="cd x && find . -name y | head"), "bash.find"),
    (call("bash", command="find /testbed -name x | sort"), "bash.find"),
    (call("bash", command="pytest -x || cat log | tail"), "bash.cat"),
    # separators inside quotes are not separators (handcheck-20 run 10, steps 9/11/12)
    (call("bash", command="""cd /testbed && python -c "from faker.cli import print_doc; print_doc('x')" """),
     "bash.python"),
    (call("bash", command="""grep -n "dump_only\\|load_only" schema.py"""), "bash.grep"),
    (call("bash", command="""echo 'a && b' && sort f"""), "bash.sort"),
    (call("bash", command="""cd /testbed && python -c "print(1); unbalanced"""), "bash.python"),
    (call("bash", command="/usr/bin/grep -rn foo ."), "bash.grep"),
    # undeclared tool passes through unchanged
    (call("goto", target="fridge 1"), "goto"),
    (call("submit"), "submit"),
])
def test_canonical_tool(step, expected):
    assert canonical_tool(step) == expected


def test_quoted_pipe_is_not_a_pipeline():
    """handcheck-20 run 04, steps 11/12: `\\|` inside a quoted grep pattern was
    split as a pipe; the token was right only because grep came first."""
    cmd = r'grep -n "dump_only\|load_only" /testbed/src/marshmallow/schema.py'
    assert _split_command(cmd) == [[cmd]]
    piped = cmd + " | head -20"
    assert len(_split_command(piped)) == 1 and len(_split_command(piped)[0]) == 2


def test_unbalanced_quote_quotes_the_rest():
    assert _split_command("echo 'a; b && c") == [["echo 'a; b && c"]]


def test_role_assignment_ignores_values():
    """The slash bug (spec req #1): v0 typed old_str as "path" when its value
    contained a slash. Roles come from the table, never from the value."""
    with_slash = call("str_replace_editor", command="str_replace", path="x.py",
                      old_str="import a/b/c.py", new_str="y")
    without_slash = call("str_replace_editor", command="str_replace", path="x.py",
                         old_str="plain text", new_str="y")
    assert arg_role("str_replace_editor", "old_str") == "content"
    assert arg_roles("str_replace_editor", with_slash.arg_values) == \
        arg_roles("str_replace_editor", without_slash.arg_values)
    assert arg_roles("str_replace_editor", with_slash.arg_values)["old_str"] == "content"


def test_undeclared_tool_args_are_unknown_not_guessed():
    roles = arg_roles("goto", ["target", "path"])
    assert roles == {"target": UNKNOWN_ROLE, "path": UNKNOWN_ROLE}
    assert arg_role("bash", "timeout") == UNKNOWN_ROLE   # undeclared arg on a declared tool
    assert arg_role(None, "command") == UNKNOWN_ROLE


def test_signature_and_motif_counts():
    rec = TraceRecord(
        run_id="r1",
        source=Source.SWE_AGENT,
        source_ref="row_0",
        steps=[
            call("bash", 0, command="find /testbed -name x"),
            Step(step_index=1, kind=StepKind.OBSERVATION, text="./x"),
            call("str_replace_editor", 2, command="view", path="/testbed/x"),
            call("str_replace_editor", 3, command="view", path="/testbed/y"),
            Step(step_index=4, kind=StepKind.MODEL_TURN, text="thinking"),
            call("bash", 5, command="cd /testbed && python -m pytest"),
        ],
        outcome_label=OutcomeLabel.SUCCESS,
    )
    sig = build_signature(rec)
    assert isinstance(sig, Signature)
    assert sig.canonical_steps == ["bash.find", "editor.view", "editor.view", "bash.python -m pytest"]
    assert sig.step_count == 6
    assert sig.tool_call_count == 4
    assert sig.outcome_label is OutcomeLabel.SUCCESS
    assert sig.motif_counts() == {"bash.find": 1, "editor.view": 2, "bash.python -m pytest": 1}


def test_signature_never_reads_text():
    """Quarantine: changing SURFACE text must not change the signature."""
    a = TraceRecord(run_id="r", source=Source.SWE_AGENT, source_ref="x",
                    steps=[Step(step_index=0, kind=StepKind.TOOL_CALL, tool_name="submit", text="one")])
    b = TraceRecord(run_id="r", source=Source.SWE_AGENT, source_ref="x",
                    steps=[Step(step_index=0, kind=StepKind.TOOL_CALL, tool_name="submit", text="two")])
    assert build_signature(a) == build_signature(b)
