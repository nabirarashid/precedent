"""M2 demo: find_similar over 100 real SWE-smith runs.

Streams the first 100 SWE-smith trajectories (tool split), builds a
SignatureStore, and for the first 3 runs prints the query signature and its
top-3 structural neighbors (weighted n-gram motif scorer). Ends with the
store's 10 lowest-weight n-grams: the most scaffold-like motifs.

Run from the repo root (inside the venv):
    python scripts/demo_find_similar.py
"""

from __future__ import annotations

import os
import sys
from itertools import islice

from datasets import load_dataset

from precedent.similarity import SignatureStore, find_similar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load_sample_traces import to_trace_record  # noqa: E402  (reuse the ingest path)

N = 100
QUERIES = 3
K = 3


def main() -> None:
    print(f"Streaming first {N} rows of SWE-bench/SWE-smith-trajectories (tool split) ...")
    stream = load_dataset("SWE-bench/SWE-smith-trajectories", split="tool", streaming=True)
    records = [to_trace_record(row, i) for i, row in enumerate(islice(stream, N))]
    store = SignatureStore(records)
    print(f"Store: {len(store)} runs, {len(store.doc_freq)} distinct n-grams")

    for rec in records[:QUERIES]:
        query = next(s for s in store.signatures if s.run_id == rec.run_id)
        print(f"\n=== QUERY {query.run_id} ({query.outcome_label.value}, {query.tool_call_count} calls)")
        print(f"    {' → '.join(query.canonical_steps)}")
        for rank, (sig, score) in enumerate(find_similar(rec, store, k=K), 1):
            print(f"  #{rank}  {score:.3f}  {sig.run_id} ({sig.outcome_label.value}, {sig.tool_call_count} calls)")
            print(f"        {' → '.join(sig.canonical_steps)}")

    idf = store.idf_weights()
    lowest = sorted(idf.items(), key=lambda kv: (kv[1], kv[0]))[:10]
    print("\nLowest-weight (most scaffold-like) n-grams: "
          + ", ".join(f"{' → '.join(g)} ({w:.3f}, df={store.doc_freq[g]})" for g, w in lowest))


if __name__ == "__main__":
    main()
    sys.stdout.flush()  # os._exit skips buffer flushing when stdout is piped
    os._exit(0)  # datasets streaming can hang on connection cleanup
