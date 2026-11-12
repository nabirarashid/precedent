# Precedent signature spec v0

Status: REVIEWED. Hand-checked against 20 SWE-smith runs on Nov 12, 2026
(docs/notes/handcheck-20.md, 20/20 faithful). This is the spec of record
for the v0 canonicalizer.

## 1. What a signature is

A signature is the structural fingerprint of one agent run: the ordered list
of canonical action tokens, derived only from what the agent *did*, never
from what anyone *wrote*. Two runs that took the same actions in the same
order get the same signature even if their task text, file contents, and
model chatter are completely different. This is the design answer to the
paper's finding (arXiv:2609.01556): retrieval that reads surface text gets
anchored by it and falls below chance exactly when structure should dominate.

## 2. Inputs: the field quarantine

Signatures are computed only from fields classified STRUCTURAL in
`records.FIELD_CLASSES`. SURFACE fields (task_text, arg_values beyond the
discriminator role, Step.text) are forbidden inputs; METADATA fields
(timestamps, model name, run ids) are ignored. Any field not in the registry
is not scorable: unknown fails closed. This is enforced by tests, not
convention (`test_every_record_and_step_field_is_classified`).

Invariant: changing any SURFACE field of a record must not change its
signature. (Covered by the Step.text regression test.)

## 3. Canonical token grammar

One token per tool call, in run order:

    <tool>[.<subaction_or_program>]

Rules, in the order they were earned:

R1. Role-driven arg typing. An argument's type comes from the
    TOOL_ARG_ROLES table (tool name + arg name decide the role), never from
    inspecting the argument's value. Value inspection is how the slash bug
    happened: identical edits got different types because one old_str
    contained a "/". The paper's lexical-anchoring failure, reproduced in
    our own abstraction, in one afternoon.

R2. Sub-action lifting. Multiplexed tools are split by their discriminator
    arg: str_replace_editor becomes editor.view, editor.str_replace,
    editor.create. A tool's identity is what it did, not what it's called.

R3. Bash salient program. A bash call is tokenized by the program that
    carries the step's meaning, not literally "bash".

R4. Compound-command rule. Bash commands are split on &&, ;, ||.
    Across sequential segments: take the LAST non-cd segment.
    Within a pipeline: take the FIRST pipe component's program.
    Example: `cd x && find . | head` → bash.find.
    Rationale: cd and head are plumbing; find is the decision.

    Decision (hand-check review, Nov 12): `find … | xargs grep -l X`
    pipelines stay bash.find. A repo-wide hunt for files mentioning X is a
    different move from a targeted grep inside a known file, and the
    first-program rule happens to preserve that distinction. No special
    case for xargs. Revisit at M2 if similarity data argues otherwise.

R5. Quote-aware splitting. Separators inside single or double quotes, or
    escaped with a backslash, do not split. An unbalanced quote treats the
    remainder as quoted. Earned from run 10 of the hand-check, where
    `python -c "…; print_doc('x')"` produced garbage tokens until fixed.

R6. Python invocations split by what they run. `python -m X` lifts the
    module: bash.python -m pytest, bash.python -m unittest. Running a test
    suite is structurally different from running a script. `python -c` and
    `python script.py` both collapse to bash.python: the payload is
    surface, the action is "ran python".

## 4. Signature object

`Signature` carries: run_id, canonical_steps (the token list), step_count,
tool_call_count, outcome_label, and motif_counts() for frequency analysis.
Outcome rides along because v0.2 needs outcome-conditioned retrieval; it is
never an input to the signature itself.

## 5. Structural stopwords (measured, deferred to M2)

The hand-check's frequency table (434 calls, 14 distinct tokens after the
R5 fix) confirms scaffold motifs empirically: all 20 runs open with
bash.find, 15 of 20 close with submit → bash.rm → submit, and the top five
tokens (bash.python, editor.view, editor.str_replace, editor.create,
submit) cover 78% of calls. These are the harness speaking, not the agent.
Similarity scoring in M2 must downweight scaffold-common motifs or every
run will look like every other run. This spec only records the evidence;
the weighting scheme is an M2 decision.

## 6. Known limits (v0, accepted)

- One token per tool call: non-salient segments of a compound command are
  discarded entirely. In `cd … && rm -f *.png && python rerun.py` the rm
  is invisible in the signature. Found in hand-check review (run 08).
- No parsing of subshells, heredocs, or process substitution; those
  commands resolve by the same scanner rules, imperfectly.
- depends_on is Optional: None means unknown, [] means independent. SWE
  ingestion currently leaves it unknown; dependency-graph signatures are
  future work, token sequences are v0.
- Retry/backtrack detection (retry_of) is schema-ready but not inferred.
- Observation truncation is not modeled; observations are SURFACE anyway.

## 7. Done-definition for M1 (met)

(a) This spec is reviewed and committed. (b) The canonicalizer passes its
test suite (30 tests as of ca45e31). (c) The 20-run hand-check was
completed by a human reviewer on Nov 12, 2026: 20/20 signatures faithful,
with one limitation (dropped non-salient segments) recorded in section 6
and one design decision (xargs-grep pipelines) recorded in section 3.
