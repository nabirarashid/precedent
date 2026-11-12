# Precedent

**Structural retrieval over agent traces.** Status: building. Nothing here is released yet.

Agent teams accumulate thousands of recorded runs and have no good way to use them. If you search your trace store for a run similar to the one in front of you, retrieval matches *wording*, not *what the agent did*. Precedent is a small Python library that indexes existing traces by structure, so you can find the run that solved a similar task, cluster failures that broke the same way, and diff two runs by path instead of text.

## The problem, measured

This project exists because its failure mode has been measured, not assumed. In *Retrieved but not ranked: surface-form bias in structural retrieval* (arXiv:2609.01556, under submission to ICLR 2027), embedding retrieval over agent trajectories was evaluated against exact hypergeometric chance with task-structure gold labels:

- When the correct match must involve a **different target object** than the query, production embedders score at or barely above random chance.
- When it must involve a **different object and receptacle**, all three tested embedders fall **below chance**: the ranking is actively steered away from structural matches by literal token overlap.
- A deliberately naive lexical reranker closed 26 to 36% of the recoverable gap on this data, confirming that the embedders' "semantic" rankings are substantially lexical.

Thousands of recorded runs, retrievable in principle, unusable in practice.

## The approach

Three stages, built on trace formats teams already emit (OpenTelemetry GenAI conventions; Langfuse export):

1. **Ingest** existing traces. No capture SDK, no agent framework, no migration.
2. **Canonicalize** each run into a *structural signature*. In v0 that is the ordered sequence of canonical action tokens, one per tool call (`editor.view`, `bash.grep`, `bash.python -m pytest`), per [docs/spec/signature-spec-v0.md](docs/spec/signature-spec-v0.md). The planned next layer is the tool-call dependency graph with retry and backtrack markers: schema-ready in [src/precedent/records.py](src/precedent/records.py) (`depends_on`, `retry_of`), not yet inferred from traces. Either way, the signature excludes the surface features the paper showed retrieval wrongly anchors on; see [docs/trace-record-schema.md](docs/trace-record-schema.md) for the v0 record schema.
3. **Index and compare** on signatures: structural similarity first, with lexical features quarantined into an explicit diagnostic ("this match is structural" vs. "this match is token overlap").

A 30-artifact evidence study ([docs/evidence/findings-memo.md](docs/evidence/findings-memo.md)) points to `find_similar(run)` leading v0.1, with `cluster(failures)` as the fast-follow; the verdict is provisional pending practitioner conversations.

## What a signature looks like

The schema is implemented and loading real traces. Here is an actual SWE-agent run (Claude 3.7 Sonnet fixing a GitHub issue, from the public SWE-smith trajectory release), reduced to its structural skeleton by the v0 canonicalizer ([src/precedent/canonicalize.py](src/precedent/canonicalize.py)):

```
bash.find → editor.view → bash.find → bash.find → editor.view → editor.view
→ bash.grep → editor.view → editor.view → editor.view → editor.create
→ bash.python → editor.str_replace → bash.python → … → editor.str_replace
→ bash.python → submit → bash.rm → submit
```

Locate, read, probe, edit, test, submit — the behavior is legible with every variable name, file path, and prompt token quarantined. The token rules are specified in [docs/spec/signature-spec-v0.md](docs/spec/signature-spec-v0.md); working notes from first contact with real traces, including five spec requirements this surfaced, live in [docs/notes/m1-spec-notes.md](docs/notes/m1-spec-notes.md).

## The eval ships with it

Precedent will not ask to be trusted. v0.1 ships with a side-by-side evaluation against embedding baselines on labeled trajectory data, reported the way the source paper reports: exact chance baselines, bootstrap confidence intervals, a mandatory lexical-control diagnostic, and a written list of what the eval does not measure. If a baseline beats Precedent on its own benchmark, that result gets published too.

## v0 scope

A library and CLI. Explicitly not: an observability platform, an agent framework, a memory-as-a-service product, or anything hosted. No UI in v0.1.

## Repository layout

```
src/precedent/records.py      # v0 schema as code: TraceRecord/Step with enforced
                              # structural / surface / metadata field quarantine
src/precedent/canonicalize.py # v0 canonicalizer: TraceRecord -> structural Signature
tests/                        # schema + canonicalizer guarantees as tests
scripts/load_sample_traces.py # stream real SWE-agent trajectories into
                              # TraceRecords, print their signatures
scripts/make_handcheck.py     # generate the 20-run hand-check review sheet
docs/trace-record-schema.md   # the v0 record schema (the ingest contract)
docs/spec/signature-spec-v0.md # the v0 signature spec (spec of record)
docs/notes/m1-spec-notes.md   # signature-spec requirements learned from real data
docs/notes/handcheck-20.md    # M1 hand-check: 20 runs, reviewed 20/20 faithful
docs/evidence/corpus-log.md   # M0 evidence study: demand-signal corpus + method
docs/evidence/findings-memo.md # M0 findings memo and headline-feature verdict
docs/journey.md               # dated session log
```

To run it yourself:

```
python3 -m venv .venv && source .venv/bin/activate
pip install -e . pytest
python -m pytest tests/ -q          # 30 tests: schema + canonicalizer
pip install datasets
python scripts/load_sample_traces.py  # streams 5 real traces, prints signatures
```

## Status

- [x] Problem measured (arXiv:2609.01556)
- [x] v0 trace record schema defined ([docs/trace-record-schema.md](docs/trace-record-schema.md)) and implemented ([src/precedent/records.py](src/precedent/records.py), tested)
- [x] Real coding-agent traces loading into the schema; first legible structural signatures ([docs/notes/m1-spec-notes.md](docs/notes/m1-spec-notes.md))
- [x] Evidence study: corpus complete (30 artifacts, closed Nov 8 — [docs/evidence/corpus-log.md](docs/evidence/corpus-log.md)); findings memo written ([docs/evidence/findings-memo.md](docs/evidence/findings-memo.md)), verdict provisional pending practitioner conversations
- [x] Structural signature spec v0, reviewed ([docs/spec/signature-spec-v0.md](docs/spec/signature-spec-v0.md))
- [x] Canonicalizer v0: implemented, tested, and hand-checked 20/20 ([docs/notes/handcheck-20.md](docs/notes/handcheck-20.md)) — M1 complete
- [ ] Retrieval + benchmark harness
- [ ] Demo notebook
- [ ] v0.1 release

## Author

Nabira Rashid ([nabira.rashidm@gmail.com](mailto:nabira.rashidm@gmail.com)). The underlying measurement was first-authored at the MIT CSAIL Kellis Lab (Mantis project).