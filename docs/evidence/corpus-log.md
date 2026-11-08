# M0 Evidence Study — Corpus Log (FINAL, closed Nov 8 2026 at N=30)

*Public demand signals for structural search over agent traces. Inclusion rule: the artifact must be a builder describing their own workflow or need, first person. Vendor marketing, docs, and listicles are excluded. Artifacts showing templated/AI-drafted style are admitted only if they describe a concrete own-workflow detail, and flagged. One row per distinct author across all venues.*

**Tags:** `retrieval-pain` (wants to find/reuse past runs) · `debugging-pain` (wants to group/compare failures across runs) · `neither-adjacent` (real trace-workflow pain Precedent doesn't address) · `neither`

**Pre-registered kill criterion:** fewer than ~15% of a good-faith corpus showing either pain AND conversations agreeing → write up the negative result and stop. **Result: 26/30 on-pain (87%). Criterion decisively not triggered.**

**Closure note:** target N was 40-60; closed at 30 on saturation — the final three threads produced only themes already held (embeddings-fail/structure-wins, outcome-blind memory, DIY-over-vendor). 30 strictly-admitted artifacts with an auditable search log were judged stronger evidence than a padded 50.

| ID | URL | Post date | Source | Near-verbatim quote | First-person? | Tag | 2nd-look |
|----|-----|-----------|--------|---------------------|---------------|-----|----------|
| 001 | https://github.com/langfuse/langfuse/issues/9179 | 2025-09-17 | langfuse-gh | "my use case is to check if my executed tool calls are really the ones I expected... Visually if the order is not preserved it is more difficult to see the differences. It somehow fits into understanding why the evaluation run actually failed." (fhoering) | Y | debugging-pain | resolved: keep |
| 002 | https://github.com/langfuse/langfuse/issues/9179 (gschnaub comment) | 2025-10-23 | langfuse-gh | "I want to calculate a meteor score for each dataset item when I run an experiment. Since the order is not preserved (and my output is fairly large json) the score ends up being quite low." | Y | neither-adjacent | |
| 003 | https://github.com/mem0ai/mem0/issues/6010 | 2026-06-30 | mem0-gh | "A planner-executor agent may need memories useful for... avoiding previously observed failure modes... reusing procedural experience from similar tasks; revising a failed plan based on past successful or failed trajectories." (DLA-learn) | Y | retrieval-pain | style flag |
| 004 | https://github.com/mem0ai/mem0/issues/6010 (hegu-1 comment) | 2026-07-12 | mem0-gh | "A planner can then ask a more typed question: 'what playbooks or prior failures apply to this step?' rather than only 'what text is similar?'" | Y | retrieval-pain | |
| 005 | https://github.com/mem0ai/mem0/issues/4573 | 2026-03-27 | mem0-gh | "After noticing the agent kept 'remembering' things it had never been told... We pulled the entire collection. 10,134 entries... 97.8% junk. 2,943 entries (37.6%) flagged as near-duplicates." (jamebobob, 32 days in production) | Y | neither-adjacent | resolved: keep |
| 006 | https://github.com/mem0ai/mem0/issues/4573 (farrrr comment) | 2026-03-29 | mem0-gh | "All embedding models scored P@1 ≤ 33% on temporal queries. This isn't an embedding quality problem — it's a fundamental limitation of vector similarity. Graph Memory is needed to break through." (production, 7,500+ node graph) | Y | retrieval-pain | resolved: keep |
| 007 | https://github.com/mem0ai/mem0/issues/5235 | 2026-05-22 | mem0-gh | "subtle failures that are hard to debug: the agent should remember a preference but silently retrieves stale or conflicting information instead... Regressions in memory behavior go undetected until they affect user experience." (Ruthwik-Data) | Y | debugging-pain | resolved: keep |
| 008 | HN: pauliusztin, "A year building agent memory on knowledge graphs: 5 mistakes" | 2026-06 | HN | "I only built short-term and long-term memory. The agent repeated failed strategies because I skipped reasoning memory. This is a trace per run including the strategy, tools used, and the success or failure... Even semantic search over history can't traverse the relationships." | Y | retrieval-pain | |
| 009 | HN: Launch HN Martin (darweenist) | 2024 | HN | "most of our reliability issues are soft errors which are very hard to programmatically catch... The best we can do is rudimentary checks based on behavior patterns which we know historically indicate errors (e.g. making many similar API calls in quick succession, implying rapid failure and retry of function calls)" | Y | debugging-pain | |
| 010 | HN: Show HN Telem (yurikoif) | 2026-09 | HN | "I stopped just checking the final answer and started reading the actual trajectories: what did the agent search for? What came back? At what point were agents off the rail?... A run jeopardized at minute 1 but still ran for another 10 before returning nonsense... nothing reveals it." | Y | debugging-pain | founder-origin |
| 011 | HN: Ask HN knowledge graphs for agent memory (mbbah) | 2025 | HN | "One core challenge I keep hitting: managing evolving memory and context... once agents need to maintain structured knowledge, track state, or coordinate multi-step tasks, things get messy fast." | Y | retrieval-pain | resolved: keep |
| 012 | HN: Launch HN Airbyte Agents (mtricot) | 2026-05 | HN | "What got us working on this was an insane trace from an agent we were migrating... The trace had 47 steps... when the Agent finally responded, the answer sounded ok, but was wrong." | Y | debugging-pain | founder-origin |
| 013 | HN: Launch HN Sentrial YC W26 (anayrshukla) | 2026-03 | HN | "debugging agents was often harder than actually building them... When agents fail, choose wrong tools, or blow cost budgets, there's no way to know why - usually just logs and guesswork." (pain lived at SenseHQ/Accenture before founding) | Y | debugging-pain | founder-origin |
| 014 | HN: Show HN WatchLLM (Kaadz) | 2026-01 | HN | "When your agent makes 20 tool calls and fails, good luck figuring out which decision was wrong... Agents love getting stuck in loops... 'loop detected - same action repeated 3x'" | Y | debugging-pain | founder-origin |
| 015 | HN: Show HN plomp (michaelgiba) | 2024 | HN | "programs which are prompting LLMs many times or using complicated contexts... I had noticed that having this layer for debugging would be useful for some of my other side projects so I decided to pull it out" (personal OSS tool, no product) | Y | neither-adjacent | |
| 016 | https://github.com/orgs/langfuse/discussions/19251 | 2026-10 | langfuse-disc | "Today every filter matches a single observation. That makes it impossible to answer a common agent question: 'show me the runs in which tool X was called somewhere below the root.'... Write the called tool names onto the root span's metadata at the end of each run — needs an instrumentation change and doesn't apply to historical traces." (pratimapatel2008) | Y | retrieval-pain | |
| 017 | https://github.com/orgs/langfuse/discussions/18374 | 2026-10-07 | langfuse-disc | "I cannot open two runs' outputs together to compare A vs B without switching peek / remembering content... No readable diff between outputs when runs differ." (Tkgmuuuu) | Y | debugging-pain | resolved: keep |
| 018 | https://github.com/orgs/langfuse/discussions/17967 | 2026-09-26 | langfuse-disc | "when a long run goes wrong, the trace shows you every LLM call in perfect detail and nothing about the moment the run actually went wrong... Debugging this today means reading the whole trace and guessing where the requirement disappeared." (behrnt-slatgng, disclosed founder, Grunz) | Y | neither-adjacent | founder-origin |
| 019 | https://github.com/Arize-ai/phoenix/issues/17511 | 2026-11 | phoenix-gh | "Phoenix experiments support repetitions, but evaluators score each run independently. Nothing compares runs of the same input against each other, so a system that gives different answers... on each run can still score well on average." (krishna-gogineni-765) | Y | debugging-pain | resolved: keep (OSS contribution, not marketing) |
| 020 | https://github.com/Arize-ai/phoenix/issues/17511 (coindef comment) | 2026-11 | phoenix-gh | "We run the same simulated customer conversations several times per scenario, and a run that passes 3 of 5 averages out fine but is a real problem." | Y | debugging-pain | |
| 021 | r/LangChain "How do you prevent AI agents from repeating the same mistakes?" (OneTurnover3432, OP) | 2025-09 | reddit | "the agent keeps making the same mistakes over and over. Right now, the only way I'm catching these is by reading the transcripts every day and manually spotting what went wrong... Do you have monitoring or feedback loops that surface recurring issues automatically?" | Y | retrieval-pain | |
| 022 | same thread ([deleted] commenter + OP exchange) | 2025-09 | reddit | "I give them episodic memory and at each step show them positive/negative experiences: 'In the past, for a similar goal and in a similar state, when I did X, it led to a negative outcome.'" OP: "is there a library or tool to do that?" Reply: "I don't know of any, I've always built it myself." | Y | retrieval-pain | |
| 023 | r/LangChain "How do you actually debug a failed agent run?" (ComprehensiveMonth70, OP) | 2026-08 | reddit | "Say a LangGraph agent fails after 10-15 steps. You have the trace, tool calls and outputs, but the real cause is not obvious." | Y | debugging-pain | pre-product discovery |
| 024 | same thread (donk8r) | 2026-08 | reddit | "Nobody has a good way to find the earliest point where a good run and a bad run diverge. That's a bisect over the trace... compare decisions rather than states: (context the model saw) to (action it chose): which tool, and the arguments that are load-bearing rather than incidental." (disclosed: builds octomind; describes this as upstream of their product) | Y | debugging-pain | resolved: keep (strongest debugging artifact) |
| 025 | same thread (Worth_Wealth_6811) | 2026-08 | reddit | "take the wrong value in the final output and grep the raw trace for its first appearance... you're tracing data lineage instead of judging step correctness." | Y | debugging-pain | |
| 026 | same thread (SpecialChance8662) | 2026-08 | reddit | "most of those 10 steps fail quietly: a tool returns an empty result, the agent shrugs and keeps going, the run reports success, and the trace looks clean. We had this issue on a ReAct RAG system." | Y | debugging-pain | |
| 027 | r/LangChain "old agent failures come back after a prompt or model change" (More-Honeydew-2838) | 2026-06 | reddit | "What actually fixes it: treating every real failure as a permanent regression case. Capture failures straight from production traces, not from memory. Tag the bad ones... Track which old failures come back when." (consultant, firsthand across teams) | Y | debugging-pain | |
| 028 | r/AI_Agents "2 years building agent memory systems, ended up just using Git" (alexmrv) | 2025 | reddit | "Vector DBs, knowledge graphs, embeddings, the whole circus. They all suck at showing HOW knowledge evolved... The challenge I'm facing is a decent benchmark, there seems to be very little for quantifying gains." (2 years, built DiffMem, 200 upvotes) | Y | retrieval-pain | |
| 029 | r/AI_Agents "I scanned 23 of my own agent sessions..." (No_Advertising2536 = Mengram founder, disclosed; ONE row for this author across all venues) | 2026-09 | reddit | "'debug from logs' in 16 of 23 sessions means I walked an agent through the same sequence sixteen times and it began from nothing each time... Every memory tool I've looked at stores the steps and nothing about the outcome." | Y | retrieval-pain | founder-origin |
| 030 | r/AI_Agents "Your agent repeats mistakes because its memory retrieves what sounds related, not what worked" (Technical_Plant_6109) | 2026-07 | reddit | "closest means sounds related, which has nothing to do with whether acting on it ever worked... similarity tells you what looks related, recency tells you what is still current, and neither tells you what actually worked." | Y | retrieval-pain | style flag |

## Final tally

| Tag | Count | Excluding all flagged rows |
|-----|-------|---------------------------|
| retrieval-pain | 11 | 6 |
| debugging-pain | 15 | 5 |
| neither-but-adjacent | 4 | 2 |
| neither | 0 | 0 |
| **Total admitted** | **30** | **13** |

**Reading (Nov 8):** 26/30 on-pain; kill criterion decisively not triggered. Debugging-pain leads the raw count, but its lead is carried largely by founder-origin testimony (people who monetized the pain); on the conservative tally (flagged rows excluded) the two pains are near-even (6 vs 5). The carrier pattern is the sharper finding: debugging-pain arrives with a crowd of commercial entrants (Sentrial YC W26, WatchLLM, Telem, Cortexa, rootline, TAQ, thinkhive, octomind, LangGraphics), while retrieval-pain repeatedly arrives as "I built it myself because no library exists" (022, 028, 008, 029) — unserved. Selection caveat: Nov 8 Reddit searches were debugging-phrased; report tags by search channel in the memo. Headline-feature verdict: formally decided in the findings memo, with the warm conversations (still 0 of 3-5 held) as the remaining check.

## Memo notes (context, not corpus data)

- Market-gap dialogue (022): practitioner hand-builds precedent retrieval; "is there a library or tool to do that?" — "I don't know of any, I've always built it myself." Corroborated by 028 (built DiffMem after 2 years), the "why not Mem0" thread ("memory systems are shit and actively harm performance"; "it can keep wrong, outdated memories just as well as right"), and the Git-for-memory genre (DiffMem, Memoir, "I stopped building a database and just used git") — people reaching for versioned, inspectable, structural storage with their feet.
- Benchmark gap stated by builders: 028 ("can't seem to find a good eval framework... very little for quantifying gains"). Incumbents benchmark memory behavior (mem0 BEAM, Letta leaderboard); nobody benchmarks retrieval over traces. M2's reason to exist, as demand.
- Outcome-blind memory theme: 029/030 and thread titles ("Every agent-memory tool stores the steps. None of them store whether the steps worked") — validates schema's day-one outcome_label.
- Incumbent "clustering" is embeddings-of-text (Phoenix UMAP/HDBSCAN roadmap), not runs-by-structure. Langfuse founder-authored cross-run comparison ask (#3259) closed as not planned. Phoenix maintainers now building side-by-side experiment compare UI (#17239) — incumbent momentum in output-diff, none in structural run search.
- Commercial neighbors map: hosted monitors (Sentrial, WatchLLM, Cortexa, Telem); failure-replay/regression (TAQ, thinkhive); store-side narrow wedge (rootline: reads Langfuse traces, flags 3x-identical-tool-call loops — closest entrant to our lane, loop detection only, as of Nov 2026); cross-team trace reuse as a feature (Grov); memory-poisoning gates (Nomos, AgentUQ, NativePort essay). Library-over-existing-store with structural retrieval + public benchmark: still unoccupied.
- Lexical-pollution trilogy (method finding): GitHub search defeated by support-bot boilerplate (langfuse), system-prompt text (letta), and issue templates (langgraph "similar": 694/694 false positives) — token search failing three ways in a study about token search failing.
- Slop/marketing contamination: Letta maintainer locked a thread as "AI slopfest"; one vendor (alibaizhanov/No_Advertising2536/Mengram) posted across 4+ venues; polished AI-assisted pattern essays (NativePort) are the genre's new face. Strict first-person-with-concrete-detail rule + author dedup held the line.

## Search log (terms × sources, auditable coverage)

| Date | Source | Term/thread | Scanned | Admitted |
|------|--------|------|-----------------|----------|
| Oct 4 | langfuse-gh issues | "similar trace" | ~60 of 76 | 2 |
| Oct 4 | langfuse-gh issues | "deduplicate" | 22 | 0 |
| Oct 4 | langfuse-gh issues | "group traces" | 28 | 0 |
| Oct 4 | mem0-gh issues | "past runs" | 0 | 0 |
| Oct 4 | mem0-gh issues | "previous" | ~70 | 5 |
| Oct 4 | letta-gh issues | "past" | ~87 | 0 (system-prompt pollution) |
| Oct 4 | letta-gh #3115 | thread-mine | 14 comments | 0 (locked as slop by maintainer) |
| Oct 4 | HN Algolia | "trace retrieval" | 52 | 5 |
| Oct 4 | HN Algolia | "debugging agents" | 6 | 3 |
| Nov 8 | langfuse-discussions | "similar" | ~14 | 1 |
| Nov 8 | langfuse-discussions | "find traces" | ~10 | 0 |
| Nov 8 | langfuse-discussions | "compare runs" | ~7 | 2 |
| Nov 8 | mem0-discussions | "past runs" | 0 | 0 |
| Nov 8 | mem0-discussions | "failures" | 3 | 0 (1 vendor-pattern essay noted) |
| Nov 8 | langgraph-gh | "past runs" | 4 | 0 |
| Nov 8 | langgraph-gh | "learn from" | 3 | 0 |
| Nov 8 | langgraph-gh | "similar" | 694 | 0 (issue-template pollution; abandoned) |
| Nov 8 | phoenix-gh | "similar traces" | 7 | 0 |
| Nov 8 | phoenix-gh | "cluster" | 83 | 0 (incumbent clusters embeddings, not structure) |
| Nov 8 | phoenix-gh | "compare runs" + #17511 thread | 13 + 2 comments | 2 |
| Nov 8 | HN Algolia | "agent learns from" | 4 | 0 |
| Nov 8 | HN Algolia | "failed runs" | 6 | 0 (3 competitive notes) |
| Nov 8 | reddit r/LangChain | "repeating same mistakes" thread | 42 comments | 2 |
| Nov 8 | reddit r/LangChain | "debug a failed agent run" thread | 16 comments | 4 |
| Nov 8 | reddit r/LangChain | "old failures come back" thread | 14 comments | 1 |
| Nov 8 | reddit r/LangChain | "most painful part" thread | 20 comments | 0 (context noted) |
| Nov 8 | reddit r/AI_Agents | "Git memory" thread (80 comments) | OP+comments | 1 |
| Nov 8 | reddit r/AI_Agents | "23 sessions scan" thread | 15 comments | 1 |
| Nov 8 | reddit r/AI_Agents | "steps worked" thread | 21 comments | 0 (same author as 029) |
| Nov 8 | reddit r/AI_Agents | "sounds related not what worked" thread | 11 comments | 1 |
| Nov 8 | reddit r/AI_Agents | "why build own vs Mem0" thread | 25 comments | 0 (market notes) |

## Status

Corpus CLOSED Nov 8 at N=30. Next: findings memo (docs/evidence/findings-memo.md) — tally, tag-by-channel breakdown, five most vivid quotes (candidates: 004, 022, 016, 024, 030), competitive map, headline-feature verdict. Warm conversations (3-5) remain open as the memo's confirmation check.
