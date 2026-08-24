"""Read a JSONL file whether or not it is gzipped.

The crawled corpora are large -- the Volleyball Life match file alone is 105 MB raw, which
is over GitHub's hard limit for a single file -- so the big ones are stored compressed.
Everything that reads them goes through here so the choice of compression is invisible to
the caller and reversible without touching the readers.
"""
import gzip
import json
import os


def path_of(path):
    """Prefer the plain file if present, fall back to the .gz beside it."""
    if os.path.exists(path):
        return path
    if os.path.exists(path + ".gz"):
        return path + ".gz"
    raise FileNotFoundError(f"neither {path} nor {path}.gz")


def open_jsonl(path):
    p = path_of(path)
    return gzip.open(p, "rt") if p.endswith(".gz") else open(p)


def read(path):
    """Yield each row. A truncated final line is skipped: a crawl killed mid-write leaves
    one, and losing a row is better than failing to read the file at all."""
    with open_jsonl(path) as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue
