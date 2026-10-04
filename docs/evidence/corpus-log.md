# M0 Evidence Study — Corpus Log

*Public demand signals for structural search over agent traces. Inclusion rule: the artifact must be a builder describing their own workflow or need, first person. Vendor marketing, docs, and listicles are excluded. Artifacts showing templated/AI-drafted style are admitted only if they describe a concrete own-workflow detail, and flagged for second look.*

**Tags:** `retrieval-pain` (wants to find/reuse past runs) · `debugging-pain` (wants to group/compare failures across runs) · `neither-adjacent` (real trace-workflow pain Precedent doesn't address) · `neither`

**Target N:** 40–60 admitted artifacts. **Pre-registered kill criterion:** if fewer than ~15% of a good-faith 50-artifact corpus shows either pain AND practitioner conversations agree, the negative result gets written up and published.

| ID | URL | Post date | Source | Near-verbatim quote | First-person? | Tag | 2nd-look |
|----|-----|-----------|--------|---------------------|---------------|-----|----------|
| 001 | https://github.com/langfuse/langfuse/issues/9179 | 2025-09-17 | langfuse-gh | "my use case is to check if my executed tool calls are really the ones I expected... Visually if the order is not preserved it is more difficult to see the differences. It somehow fits into understanding why the evaluation run actually failed." (fhoering) | Y | debugging-pain | ? |
| 002 | https://github.com/langfuse/langfuse/issues/9179 (gschnaub comment) | 2025-10-23 | langfuse-gh | "I want to calculate a meteor score for each dataset item when I run an experiment. Since the order is not preserved (and my output is fairly large json) the score ends up being quite low." | Y | neither-adjacent | |
| 003 | https://github.com/mem0ai/mem0/issues/6010 | 2026-06-30 | mem0-gh | "A planner-executor agent may need memories useful for... avoiding previously observed failure modes... reusing procedural experience from similar tasks; revising a failed plan based on past successful or failed trajectories." (DLA-learn) | Y | retrieval-pain | ? |
| 004 | https://github.com/mem0ai/mem0/issues/6010 (hegu-1 comment) | 2026-07-12 | mem0-gh | "A planner can then ask a more typed question: 'what playbooks or prior failures apply to this step?' rather than only 'what text is similar?'" | Y | retrieval-pain | |
| 005 | https://github.com/mem0ai/mem0/issues/4573 | 2026-03-27 | mem0-gh | "After noticing the agent kept 'remembering' things it had never been told... We pulled the entire collection. 10,134 entries... 97.8% junk. 2,943 entries (37.6%) flagged as near-duplicates." (jamebobob, 32 days in production) | Y | neither-adjacent | ? |
| 006 | https://github.com/mem0ai/mem0/issues/4573 (farrrr comment) | 2026-03-29 | mem0-gh | "All embedding models scored P@1 ≤ 33% on temporal queries. This isn't an embedding quality problem — it's a fundamental limitation of vector similarity. Graph Memory is needed to break through." (production, 7,500+ node graph) | Y | retrieval-pain | ? |
| 007 | https://github.com/mem0ai/mem0/issues/5235 | 2026-05-22 | mem0-gh | "subtle failures that are hard to debug: the agent should remember a preference but silently retrieves stale or conflicting information instead... Regressions in memory behavior go undetected until they affect user experience." (Ruthwik-Data) | Y | debugging-pain | ? |
| 008 | https://hn.algolia.com (pauliusztin, "A year building agent memory on knowledge graphs: 5 mistakes") | 2026-06 | HN | "I only built short-term and long-term memory. The agent repeated failed strategies because I skipped reasoning memory. This is a trace per run including the strategy, tools used, and the success or failure... Even semantic search over history can't traverse the relationships." | Y | retrieval-pain | |
| 009 | https://hn.algolia.com (Launch HN: Martin, darweenist) | 2024 | HN | "most of our reliability issues are soft errors which are very hard to programmatically catch... The best we can do is rudimentary checks based on behavior patterns which we know historically indicate errors (e.g. making many similar API calls in quick succession, implying rapid failure and retry of function calls)" | Y | debugging-pain | |
| 010 | https://hn.algolia.com (Show HN: Telem, yurikoif) | 2026-09 | HN | "I stopped just checking the final answer and started reading the actual trajectories: what did the agent search for? What came back? At what point were agents off the rail?... A run jeopardized at minute 1 but still ran for another 10 before returning nonsense... nothing reveals it." | Y | debugging-pain | ? |
| 011 | https://hn.algolia.com (Ask HN: knowledge graphs for LLM agent memory, mbbah) | 2025 | HN | "One core challenge I keep hitting: managing evolving memory and context... once agents need to maintain structured knowledge, track state, or coordinate multi-step tasks, things get messy fast." | Y | retrieval-pain | ? |
| 012 | https://hn.algolia.com (Launch HN: Airbyte Agents, mtricot) | 2026-05 | HN | "What got us working on this was an insane trace from an agent we were migrating... The trace had 47 steps... when the Agent finally responded, the answer sounded ok, but was wrong." | Y | debugging-pain | ? |

| 013 | https://hn.algolia.com (Launch HN: Sentrial YC W26, anayrshukla) | 2026-03 | HN | "debugging agents was often harder than actually building them... When agents fail, choose wrong tools, or blow cost budgets, there's no way to know why - usually just logs and guesswork." (pain lived at SenseHQ/Accenture before founding) | Y | debugging-pain | ? |
| 014 | https://hn.algolia.com (Show HN: WatchLLM, Kaadz) | 2026-01 | HN | "When your agent makes 20 tool calls and fails, good luck figuring out which decision was wrong... Agents love getting stuck in loops... 'loop detected - same action repeated 3x'" | Y | debugging-pain | ? |
| 015 | https://hn.algolia.com (Show HN: plomp, michaelgiba) | 2024 | HN | "programs which are prompting LLMs many times or using complicated contexts... I had noticed that having this layer for debugging would be useful for some of my other side projects so I decided to pull it out" (personal OSS tool, no product) | Y | neither-adjacent | |

## Running tally

| Tag | Count |
|-----|-------|
| retrieval-pain | 5 |
| debugging-pain | 7 |
| neither-but-adjacent | 3 |
| neither | 0 |
| **Total admitted** | **15** |

**Interim read (Oct 4):** 12 of 15 artifacts show one of the two pains — far above the ~15% kill line. Debugging leads the raw count, but the carrier pattern differs: most debugging-pain artifacts are founders describing the pain they then commercialized (Sentrial, WatchLLM, Telem, Cortexa), while retrieval-pain artifacts are builders describing unserved needs. Working hypothesis to test against the remaining corpus + conversations: debugging-pain is real and already being commercialized (hosted monitors); retrieval-pain is real and unserved (open wedge for a library). Verdict stays open.

## Memo notes (context, not corpus data)

- Langfuse founder-authored "compare metrics across versions/releases" (#3259) sat 10 months, closed as not planned — incumbent declined cross-run comparison.
- mem0 maintainers route eval demand to their own benchmark suite (BEAM: contradiction resolution, knowledge update, temporal reasoning). Letta runs a memory leaderboard. Incumbents benchmark *memory behavior*; nobody in any opened thread benchmarks *retrieval over execution traces*.
- Letta #3115 locked by maintainer (cpacker) as "AI slopfest" — maintainer-confirmed slop contamination in these trackers; validates the strict inclusion rule.
- Hosted agent-failure monitoring is an emerging commercial category: Sentrial (YC W26) and WatchLLM both detect loop/repeated-action patterns — signature-shaped failure detection as a hosted monitor. Nobody observed so far ships library-over-existing-trace-store.
- Closest commercial neighbor observed: Cortexa (HN, Mar 2026) — "agent decision forensics," memory write governance, hosted. Same thesis (traces underused), different wedge (platform vs. library).
- alibaizhanov (mem0 #4573 comment, vendor, excluded): extraction abstraction loss — "loyalty number LR-11560 became 'has a loyalty number'" — surface-form information loss in the wild.
- Lexical pollution meta-finding: GitHub search for "similar trace" in langfuse matched support-bot boilerplate ("I found a similar discussion..."); letta "past" matched MemGPT's own system prompt. Token-level search failing on exactly the corpus about token-level search failing.

## Search log (terms × sources tried, so coverage is auditable)

| Date | Source | Term | Results scanned | Admitted |
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

## Still to search (next sessions)

- GitHub: langgraph, arize-phoenix, agentops, zep, langsmith-sdk (term list per runbook)
- HN Algolia: "learn from previous runs", "agent memory" (comments), "debug agent failures"
- Reddit: r/LangChain, r/AI_Agents, r/LocalLLaMA
- langfuse/mem0 **Discussions** tabs (only Issues searched so far)