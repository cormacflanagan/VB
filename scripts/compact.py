"""Fold a crawl's plain increment back into its gzipped archive.

  python3 scripts/compact.py                 # every corpus that has an increment
  python3 scripts/compact.py data/vb/teams.jsonl

The crawlers append new rows to `<name>` beside the committed `<name>.gz`, because they
cannot append to a gzip member as they go. Readers (scripts/jsonl.py) therefore take both
files, archive first. That is correct but it leaves two files where the repository should
carry one, and the plain half is not committed -- the raw Volleyball Life match file is
105 MB, over GitHub's single-file limit, which is why the archive is compressed in the
first place.

So this rewrites the archive as archive + increment and deletes the increment. The new
archive is written beside the old one and moved into place only once it has been written
and counted, so an interrupted run leaves the original intact.
"""
import gzip
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jsonl import read

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
# the corpora stored compressed, relative to the repo root
CORPORA = [
    "data/vb/matches.jsonl",
    "data/vb/teams.jsonl",
    "data/vb/players.jsonl",
    "data/all_matches.jsonl",
    "data/all_finishes.jsonl",
]


def compact(path):
    """Rewrite <path>.gz as archive + increment, then remove the increment.

    Rows carrying an `id` are deduplicated on it, keeping the first seen. A crawl that
    seeded its "already held" set from the increment alone re-emitted players that were
    in the archive all along, and folding the two together would otherwise keep both
    copies. Rows without an `id` -- team entries, which are identified by the tournament
    and division they belong to -- are kept as they are.
    """
    gz = path + ".gz"
    if not os.path.exists(path):
        return None
    if not os.path.exists(gz):
        # nothing to fold into: the corpus is stored plain
        return None
    tmp = gz + ".new"
    n, seen, dropped = 0, set(), 0
    with gzip.open(tmp, "wt") as out:
        for row in read(path):
            rid = row.get("id") if isinstance(row, dict) else None
            if rid is not None:
                if rid in seen:
                    dropped += 1
                    continue
                seen.add(rid)
            out.write(json.dumps(row) + "\n")
            n += 1
    if dropped:
        print(f"  {dropped} duplicate rows dropped")
    shutil.move(tmp, gz)
    os.remove(path)
    return n


def main(argv):
    targets = argv or CORPORA
    for t in targets:
        p = t if os.path.isabs(t) else os.path.join(ROOT, t)
        before = os.path.getsize(p) if os.path.exists(p) else 0
        n = compact(p)
        if n is None:
            print(f"{t}: nothing to fold")
            continue
        print(f"{t}: {n} rows now in the archive, {before:,} byte increment removed")


if __name__ == "__main__":
    main(sys.argv[1:])
