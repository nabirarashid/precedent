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
2. **Canonicalize** each run into a *structural signature*: the tool-call dependency graph with arguments abstracted to types and roles, plus retry and backtrack markers. The signature deliberately excludes the surface features the paper showed retrieval wrongly anchors on. See [docs/trace-record-schema.md](docs/trace-record-schema.md) for the v0 record schema.
3. **Index and compare** on signatures: structural similarity first, with lexical features quarantined into an explicit diagnostic ("this match is structural" vs. "this match is token overlap").

Which capability leads v0.1, `find_similar(run)` or `cluster(failures)`, is an open question currently being settled by an evidence study of public builder demand signals (in progress). Both are planned; the evidence picks the headline.

## The eval ships with it

Precedent will not ask to be trusted. v0.1 ships with a side-by-side evaluation against embedding baselines on labeled trajectory data, reported the way the source paper reports: exact chance baselines, bootstrap confidence intervals, a mandatory lexical-control diagnostic, and a written list of what the eval does not measure. If a baseline beats Precedent on its own benchmark, that result gets published too.

## v0 scope

A library and CLI. Explicitly not: an observability platform, an agent framework, a memory-as-a-service product, or anything hosted. No UI in v0.1.

## Status

- [x] Problem measured (arXiv:2609.01556)
- [x] v0 trace record schema defined ([docs/trace-record-schema.md](docs/trace-record-schema.md))
- [ ] Evidence study: headline-feature decision (in progress)
- [ ] Structural signature spec
- [ ] Canonicalizer
- [ ] Retrieval + benchmark harness
- [ ] Demo notebook
- [ ] v0.1 release

## Author

Nabira Rashid ([nabira.rashidm@gmail.com](mailto:nabira.rashidm@gmail.com)). The underlying measurement was first-authored at the MIT CSAIL Kellis Lab (Mantis project).
