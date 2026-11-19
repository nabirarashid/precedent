# Precedent journey log

## Nov 12 — M1 closed
DONE: hand-check harness built and run (20 SWE-smith runs, 434 calls); quote-blind splitting bug found in real data and fixed same day (ca45e31, 30 tests); 20/20 signatures reviewed faithful by me; signature spec v0 written, reviewed, committed.
DECIDED: find | xargs grep stays bash.find (keeps repo hunts distinct from targeted greps); python -m lifts the module, python -c doesn't; dropped non-salient segments recorded as a known limit.
BLOCKED: nothing.
NEXT: M2 kickoff — find_similar + benchmark harness (name collision check first).
SCOPE FLAG: none.

## Nov 15 — M2 opened: find_similar works
DONE: benchmark name collision checks run (SigBench taken, StareBench confusable, DisguiseBench wrong neighborhood); working name DoppelBench chosen, clean across web/GitHub/PyPI/HF/arXiv. Sprint 1: SignatureStore, seq + motif scorers, IDF weighting, find_similar v0 (4226da7). Demo exposed unigram degeneracy (26-token vocab, top-3 ties at 0.999). Sprint 2 same day: 1-3-gram motifs + smoothed IDF (7c57628, 46 tests); ties broken, neighbors visibly share structure (edit-test loops match edit-test loops, grep-heavy explorers match each other).
DECIDED: unit of structure is the n-gram, not the token; smoothed IDF floors common grams at 1.0 instead of erasing them; benchmark name DoppelBench (neutral ground for the publish-even-if-we-lose clause); project-internal decisions are made in the Precedent chat, with loud flags on anything that changes shape, spends money, or adds a lane.
BLOCKED: nothing.
NEXT: scoring design note + benchmark harness design (the three-way: structure-only vs lexical-only vs structure-then-lexical), then baselines.
SCOPE FLAG: none. WATCHING: retrieval is outcome-blind by design right now; revisit when failures enter the store.

## Nov 19 — benchmark design: two premises tested, two killed
DONE: DoppelBench design note v0 drafted (gold by task identity, same-repo doppelgangers). Nebius audit parts 1+2 (babb04e, 9e76135): full 80k characterized (3,591 instances, 578 mixed-model, 42 repos with 10+ instances); BUT same-instance gold pairs are MORE word-similar than same-repo distractors (0.59 vs 0.36, holds even without issue text), so task-identity gold defeats the lexical trap. Family-gold premise test (0b016da): same-repo pairs do out-word same-family pairs (P=0.843, trap real), but structural score is blind to mutation family (P(A>B)=0.44; family vs random a wash), so family-gold dies too.
DECIDED: gold is never filtered by wording (ecological gold, observational overlap split; methodological upgrade over the paper's constructed gold). Benchmark gold is outcome-agnostic (same task, any grade); outcome-matched reported as secondary. Failures stay retrievable by design.
LEARNED: structure tracks workflow style, words track repo; relevance must be defined on an axis structure lives on.
BLOCKED: SWE-track gold definition is open again, by evidence.
NEXT: ALFWorld track premise test (paper's object/receptacle construction, 336 traces), and evaluate query-by-pattern as the SWE track (corpus quote 016's ask; programmatically checkable gold).
SCOPE FLAG: none.
