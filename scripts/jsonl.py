"""Read a JSONL file whether or not it is gzipped.

The crawled corpora are large -- the Volleyball Life match file alone is 105 MB raw, which
is over GitHub's hard limit for a single file -- so the big ones are stored compressed.
Everything that reads them goes through here so the choice of compression is invisible to
the caller and reversible without touching the readers.

A corpus can be spread across two files. The archive `<name>.gz` is what the repository
carries; the crawlers append new rows to the plain `<name>` beside it, because appending
to a gzip member is not something they can do incrementally. So when both exist the plain
file is an *increment*, not a copy, and reading only one of them is silently wrong in one
of two directions: take the archive alone and every row crawled since it was written is
missing, take the plain file alone and 94% of the corpus is missing. That is not
hypothetical -- it is what happened between 17 and 24 October 2026, when a rating refit
read 45,682 of 705,605 team rows and an empty matches file, because an append had created
a plain sibling that then won the preference. `read` therefore yields both, archive first.

`compact.py` folds the increment back into the archive and removes it, which is what
should happen before the archive is committed.
"""
import gzip
import json
import os


def paths_of(path):
    """Every file holding part of this corpus, archive first. Never empty."""
    found = [p for p in (path + ".gz", path) if os.path.exists(p)]
    if not found:
        raise FileNotFoundError(f"neither {path} nor {path}.gz")
    return found


def path_of(path):
    """The single file to write to: the plain one, which is where appends go."""
    paths_of(path)
    return path


def open_jsonl(path):
    p = paths_of(path)[0]
    return gzip.open(p, "rt") if p.endswith(".gz") else open(p)


def read(path):
    """Yield each row of the corpus, archive then increment.

    A truncated final line is skipped: a crawl killed mid-write leaves one, and losing a
    row is better than failing to read the file at all.
    """
    for p in paths_of(path):
        op = gzip.open if p.endswith(".gz") else open
        with op(p, "rt") as fh:
            for line in fh:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
