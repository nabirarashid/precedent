"""M2: fetch the ALFWorld/AgentInstruct corpus and task-type labels.

Nothing is vendored: the corpus is cloned from the upstream benchmark repo at
a pinned commit, sha256-verified, and copied into data/alfworld/, which is
gitignored (Apache 2.0 upstream; we follow the paper repo's no-vendoring
pattern). The task-type labels come from the paper repo.

Run from the repo root (inside the venv, with git and gh available):
    python scripts/fetch_alfworld_corpus.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

UPSTREAM_REPO = "https://github.com/qpiai/Proced_mem_bench"
PINNED_COMMIT = "0804875216391ae98aae8b8109657fd404faf61f"
CORPUS_REL = "procedural_memory_benchmark/data/corpus/agentinstruct_trajectories.json"
CORPUS_SHA256 = "4aee80a266220cd8b7a17bc6341345589536182f263c56b86e27008d1876243c"

PAPER_REPO = "nabirarashid/structural-retrieval"
LABELS_REL = "results/agentinstruct_task_type_labels.json"

DEST = Path(__file__).resolve().parent.parent / "data" / "alfworld"


def run(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def fetch_corpus() -> Path:
    tmp = tempfile.mkdtemp(prefix="alfworld_corpus_")
    print(f"Cloning {UPSTREAM_REPO} @ {PINNED_COMMIT[:12]} (shallow, into temp) ...")
    for cmd in (
        ["git", "init", "-q"],
        ["git", "remote", "add", "origin", UPSTREAM_REPO],
        ["git", "fetch", "-q", "--depth", "1", "origin", PINNED_COMMIT],
        ["git", "checkout", "-q", PINNED_COMMIT],
    ):
        p = run(cmd, cwd=tmp)
        if p.returncode != 0:
            sys.exit(f"STOP: `{' '.join(cmd)}` failed:\n{p.stderr.strip()}")
    src = Path(tmp) / CORPUS_REL
    if not src.exists():
        sys.exit(f"STOP: {CORPUS_REL} not found at the pinned commit.")
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    if digest != CORPUS_SHA256:
        sys.exit(f"STOP: sha256 mismatch for {CORPUS_REL}:\n"
                 f"  expected {CORPUS_SHA256}\n  got      {digest}\n"
                 "Not copying the file.")
    print(f"sha256 verified: {digest}")
    DEST.mkdir(parents=True, exist_ok=True)
    out = DEST / src.name
    shutil.copyfile(src, out)
    shutil.rmtree(tmp, ignore_errors=True)
    return out


def fetch_labels() -> Path:
    """Labels from the paper repo's default branch: gh handles auth if private."""
    out = DEST / Path(LABELS_REL).name
    p = run(["gh", "api", "-H", "Accept: application/vnd.github.raw",
             f"repos/{PAPER_REPO}/contents/{LABELS_REL}"])
    if p.returncode != 0:
        sys.exit(f"STOP: could not fetch {LABELS_REL} from {PAPER_REPO} via gh:\n"
                 f"{p.stderr.strip() or p.stdout.strip()}\n"
                 "Per the handoff: not guessing alternative sources.")
    out.write_text(p.stdout)
    return out


def main() -> None:
    corpus = fetch_corpus()
    labels = fetch_labels()

    data = json.loads(corpus.read_text())
    lab = json.loads(labels.read_text())
    n_traj = len(data["trajectories"]) if isinstance(data, dict) else len(data)
    n_lab = len(lab)
    print(f"\n{corpus}: {corpus.stat().st_size:,} bytes, {n_traj} trajectories")
    print(f"{labels}: {labels.stat().st_size:,} bytes, {n_lab} label entries")
    if n_traj != 336 or n_lab != 336:
        print("NOTE: expected 336 of each.")


if __name__ == "__main__":
    main()
