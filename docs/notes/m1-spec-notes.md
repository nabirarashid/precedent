# M1 Signature Spec — notes from first contact with real traces

*Oct 4, Socratica Sprint 2. Source: 5 trajectories from SWE-bench/SWE-smith-trajectories (tool split, SWE-agent + claude-3-7-sonnet), streamed and converted to TraceRecords by scripts/load_sample_traces.py. All findings below are requirements for the M1 spec, discovered empirically.*

## What worked

- End-to-end: real rows -> json.loads(messages) -> OpenAI-style tool_calls -> Steps -> TraceRecord, with native outcome labels (`resolved`), run ids (`traj_id`), and agent label (`model`).
- Observations interleave correctly (47 steps / 24 tool calls: tool results captured as OBSERVATION steps).
- Shape is already visible at proto-signature level: all 5 runs open with a locate -> view -> edit -> test motif; exploration-heavy runs (32 calls, long bash streaks) visually distinct from tight edit-test loops.

## Spec requirements discovered (the bugs are the findings)

1. **Argument classification must be role-driven, not value-driven.** v0 classifies by inspecting the value string, which produces nonsense: `old_str:text` vs `old_str:path` differ only because one edited string happened to contain a slash. Two structurally identical edits get different abstract shapes. M1 rule: per-tool argument schemas assign each argument a role; the value's surface form never decides its type. (This is the paper's lexical-anchoring failure recurring at the schema layer — the exact mistake the signature exists to avoid.)
2. **Composite tools need sub-action lifting.** `str_replace_editor` carries its real action in the `command` argument (view / create / str_replace). Structurally, viewing a file and editing a file are different moves and must not share a node label. M1 rule: canonical tool identity = tool name + discriminating sub-action (`str_replace_editor.view`, `str_replace_editor.str_replace`), with a per-source table of which argument discriminates.
3. **`bash` is a tool-multiplexer and must be split by program.** Classifying the whole command string as one "path" arg is doubly wrong. The structural identity of a bash step is the program invoked (`find`, `cat`, `python`, `pytest`, `grep`), i.e. `bash.find`, `bash.pytest`. M1 rule: parse argv[0] (and maybe subcommand for `python -m`); everything after is role-typed args.

## Dataset notes for M2 (benchmark)

- SWE-smith tool split: all 5 sampled rows have `resolved: True` — likely success-only (SFT set). Fine for retrieval gold; useless for failure clustering. For failures, use nebius/SWE-agent-trajectories (80k runs, test-evaluated outcomes, includes failures).
- Splits in SWE-smith are tool / xml / ticks: same tasks, different action formats. A canonicalizer that maps tool-split and xml-split runs of the same task to similar signatures would be a strong internal robustness test for the spec (same behavior, different serialization).
- `datasets` streaming mode works and avoids the 2.3 GB download; cache deletion: `rm -rf ~/.cache/huggingface/hub/datasets--SWE-bench--SWE-smith-trajectories`.

## Open questions parked for M1 design

- Where do retries live in this format? No explicit retry marker observed in 5 runs; likely visible as repeated near-identical tool_calls after an error observation. Need a detection rule, not a field read.
- `depends_on`: not derivable from the flat message stream without inspecting tool_call_ids links (tool messages carry `tool_call_ids`). The linkage exists in the data — use it in M1 rather than leaving depends_on unknown.
- Observation truncation: tool results can be huge (cat of whole files). Surface anyway, but M1 may want a length cap at ingest with a "truncated" marker.

## First legible signatures (same session)

canonical_tool prototype (sub-action lifting + bash argv split) applied to the 5 runs:

- Universal scaffold motifs found: all runs open `bash.find → editor.view`; all close `editor.create → … → submit → bash.rm → submit`. Spec requirement #4: signatures must downweight scaffold-common motifs (structural stopwords) or cross-run similarity is dominated by the harness, not the behavior. Direct analog of the paper's lexical-overlap quarantine, one level up.
- Spec requirement #5: bash canonicalization must handle compound commands — `bash.cd` is masking the true program in `cd X && python Y` patterns; split on `&&`/`;`/`|` and select the salient program.
- Strategy differences are visible at signature level: the python-pinyin run shows a grep-heavy exploration phase and a `bash.python → editor.str_replace` test-fix loop, vs. cd-chained testing in the other four. Structure separates behaviors that share vocabulary.
