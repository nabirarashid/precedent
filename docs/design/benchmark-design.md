# Benchmark design v1 (working name: DoppelBench; name unpublished)

Evidence trail: docs/notes/nebius-audit.md (task-identity gold killed:
gold pairs out-word distractors), docs/notes/family-premise.md
(family gold killed: structure is blind to mutation family),
docs/notes/alfworld-premise.md (track 1 premise passed).

## Question

Given one agent run as a query, can a retriever find past runs that did
the same KIND of work, when lexically magnetic lookalikes are present?
After arXiv:2609.01556, whose hard case (same task type, different
object and receptacle) is track 1's gold rule. Methodological note: gold
is ecological (labels decide, wording uncontrolled); lexical overlap is
measured and split afterwards, never used to select gold.

## Track 1: ALFWorld/AgentInstruct (336 trajectories, paper corpus)

- QUERY: each trajectory with complete labels (task_type, target_object,
  goal_receptacle known).
- CANDIDATES: all other 335 trajectories. No constructed pools; the
  whole store is the haystack.
- GOLD: same task_type, different target_object AND different
  goal_receptacle (the paper's hard case).
- DOPPELGANGERS (measured, not gold): candidates sharing the query's
  target_object or goal_receptacle with a DIFFERENT task_type. Verb-level
  measurement put shared-object overlap at 0.650 Jaccard, the lexical
  magnet of this domain.
- Queries whose labels are incomplete (e.g. look_at_obj_in_light has no
  receptacle) are excluded as queries but remain as candidates.

## Systems (v0)

1. structural: find_similar, weighted n-gram motifs (as shipped).
2. lexical: BM25 over full trajectory text (states + actions).
3. embedding: all-MiniLM-L6-v2 over full trajectory text.
4. structure-then-lexical rerank: structural top-20, BM25 rerank within.
Later: a production embedder; one incumbent memory system (Mem0 or
LangMem). Honesty clause: results publish whichever system wins.

## Metrics

- Recall@k (k=1,5,10) and MRR over gold.
- Exact hypergeometric chance per query (gold count vs store size),
  aggregated for the chance row.
- Bootstrap 95% CIs over queries (1,000 resamples).
- Lexical-control split: queries bucketed by their gold set's mean
  full-text overlap with the query; headline is the lowest bucket.
- Doppelganger pull rate: fraction of each system's top-10 that are
  doppelgangers as defined above.

## Track 2: SWE (open)

Query-by-structural-pattern is the candidate (corpus memo, quote 016);
premise untested. Not in v0 of the harness.
