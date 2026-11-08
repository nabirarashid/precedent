# M0 Findings Memo — Do agent builders need structural search over their traces?

*Precedent evidence study, Sept 18 - Nov 8, 2026. Method and full corpus: [corpus-log.md](corpus-log.md). Status: DRAFT v1 — verdict provisional pending 3-5 warm practitioner conversations (in scheduling).*

## The question, pre-registered

Before building Precedent v0.1, decide from evidence which capability leads: `find_similar(run)` (retrieval-pain: builders want agents/teams to reuse past runs) or `cluster(failures)` (debugging-pain: builders want to group and compare failing runs). Kill criterion, written in advance: if fewer than ~15% of a good-faith corpus showed either pain and conversations agreed, publish the negative result and stop.

## Method, briefly

30 artifacts admitted from public demand signals (GitHub issues and discussions across langfuse, mem0, letta, langgraph, arize-phoenix; Hacker News; Reddit r/LangChain and r/AI_Agents) under a strict rule: a builder describing their own workflow or need, first person. Vendor marketing and AI-generated filler excluded; founder testimony admitted but flagged and discounted; one row per author across all venues. Every search logged, including the 20+ that admitted nothing, so coverage is auditable. Target N was 40-60; closed at 30 on saturation (final threads repeated held themes).

## Result

**26 of 30 artifacts (87%) exhibit one of the two pains. The kill criterion is decisively not triggered.**

| Tag | Raw | Conservative (flags excluded) |
|---|---|---|
| retrieval-pain | 11 | 6 |
| debugging-pain | 15 | 5 |
| adjacent | 4 | 2 |

Debugging-pain leads the raw count; the lead disappears under the conservative tally because it is carried largely by founder-origin testimony. The decisive finding is not the tally but the carrier pattern:

**Debugging-pain is real and already being commercialized.** Nine commercial entrants were observed attacking it during the study window (Sentrial YC W26, WatchLLM, Cortexa, Telem, rootline, TAQ, thinkhive, octomind, LangGraphics) — nearly every debugging-pain artifact is written by someone monetizing it.

**Retrieval-pain is real and unserved.** Its artifacts repeatedly end the same way: the builder hand-rolls a solution because nothing exists. "Is there a library or tool to do that?" — "I don't know of any, I've always built it myself" (022). A two-year effort ends in a homemade Git-based system (028). A measured 23-session self-audit finds the agent relearning the same four workflows from zero (029). No library over existing trace stores offering structural retrieval was found anywhere in the study.

## The five quotes that carry the finding

1. "A planner can then ask a more typed question: 'what playbooks or prior failures apply to this step?' rather than only 'what text is similar?'" (004, mem0 tracker)
2. "Your agent repeats mistakes because its memory retrieves what sounds related, not what worked... similarity tells you what looks related, recency tells you what is still current, and neither tells you what actually worked." (030, r/AI_Agents — the paper's Domain-2 finding, restated as a complaint by a stranger)
3. "Today every filter matches a single observation. That makes it impossible to answer a common agent question: 'show me the runs in which tool X was called somewhere below the root.'" (016, langfuse discussions — structural trace query requested in the incumbent's own forum)
4. OP: "is there a library or tool to do that?" Reply: "I don't know of any, I've always built it myself." (022, r/LangChain)
5. "Nobody has a good way to find the earliest point where a good run and a bad run diverge... compare decisions rather than states: which tool, and the arguments that are load-bearing rather than incidental." (024, r/AI_Agents — a practitioner independently specifying structural signatures)

## Secondary findings

- **The benchmark gap is itself demanded:** "The challenge I'm facing is a decent benchmark, there seems to be very little for quantifying gains" (028). Incumbents benchmark conversational-memory behavior (mem0 BEAM, Letta leaderboard); nobody benchmarks retrieval over traces. Precedent's benchmark fills a stated need.
- **Outcome-blind memory is a recognized hole:** "Every agent-memory tool stores the steps and nothing about the outcome" (029 and an entire thread titled the same). Validates the schema's day-one outcome labels.
- **Method meta-finding:** token-based search was defeated three separate ways during collection (support-bot boilerplate, system-prompt text, issue templates — 694/694 false positives in one repo). The study of lexical retrieval failure was itself obstructed by lexical retrieval failure.

## Verdict (provisional)

**`find_similar` leads v0.1; `cluster(failures)` is the fast-follow.** Rationale: both pains clear the bar, but retrieval-pain is the unserved wedge — building the ninth hosted failure-monitor competes with funded teams; building the first structural retrieval library over existing trace stores competes with nobody and is what the retrieval-pain artifacts are asking for by name. Clustering remains in v0.1's architecture (same signatures) and is commercially validated by the debugging-pain entrants, so it headlines the follow-up release rather than being cut.

Confirmation check before this verdict is final: 3-5 warm practitioner conversations (scheduled; same ten-question script, question 9 tags). Trigger to revisit: if conversations contradict the corpus — practitioners reporting debugging-pain as blocking and retrieval-pain as hypothetical — the headline flips, per the plan's pre-decided cut.

## What this study does not claim

That demand guarantees adoption; that N=30 of public complainers represents all agent teams (selection favors people who post); that the raw tag tally is unbiased (Nov 8 search terms skewed debugging-phrased; see tag-by-channel in the corpus log); or that absence of a competitor in our searches proves absence of a competitor.
