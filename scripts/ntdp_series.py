"""Collect the Beach NTDP training-series rosters from USA Volleyball.

The programme runs four residential training series a year and publishes a roster for each.
They are not competitions, so nothing about them can be derived from Volleyball Life — this
reads USA Volleyball's own roster pages, where each age group is one `tableizer-table` of
FIRST / LAST / REGION preceded by a heading naming the group.

  python3 scripts/ntdp_series.py           ->  data/ntdp_series.json
  python3 scripts/ntdp_series.py --match   ->  also resolve the girls to Volleyball Life ids
"""
import html as _html, json, os, re, ssl, sys, time, urllib.parse, urllib.request

USAV = "https://usavolleyball.org"
TS = USAV + "/play/national-team-development-program"
DATA = os.path.join(os.path.dirname(__file__) or ".", "..", "data")
API = "https://api-v8.volleyballlife.com"

SERIES = [
    {"key": "fall2025", "season": "Fall", "year": 2025,
     "date": "2025-09-27", "endDate": "2025-09-28",
     "location": "Virginia Beach, Virginia", "note": "alongside the 51st Neptune Festival",
     "story": USAV + "/story/2025-beach-ntdp-fall-training-series-rosters-announced/",
     "rosters": TS + "/indoor-ntdp/indoor-ntdp-training-series/"
                     "2025-boys-and-girls-beach-ntdp-fall-training-series-rosters/"},
    {"key": "winter2025", "season": "Winter", "year": 2025,
     "date": "2025-12-27", "endDate": "2025-12-29",
     "location": "Manhattan Beach, California", "note": "",
     "story": USAV + "/story/usa-volleyball-announces-2025-beach-ntdp-winter-training-"
                     "series-rosters/",
     "rosters": TS + "/indoor-ntdp/indoor-ntdp-training-series/"
                     "2025-boys-and-girls-beach-ntdp-winter-training-series-rosters/"},
    {"key": "spring2026", "season": "Spring", "year": 2026,
     "date": "2026-05-15", "endDate": "2026-05-17",
     "location": "Manhattan Beach, California", "note": "athletes convened from the 14th",
     "story": USAV + "/story/usa-volleyball-announces-2026-beach-ntdp-spring-training-"
                     "series-rosters/",
     "rosters": TS + "/beach-ntdp/beach-ntdp-training-series/"
                     "2026-beach-ntdp-spring-training-series-rosters/"},
    {"key": "summer2026", "season": "Summer", "year": 2026,
     "date": "2026-07-26", "endDate": "2026-07-30",
     "location": "Chula Vista Elite Athlete Training Center, California",
     "note": "the girls' block; the boys followed 30 July-3 August",
     "story": USAV + "/story/usa-volleyball-announces-2026-beach-ntdp-summer-training-"
                     "series-rosters/",
     "rosters": TS + "/beach-ntdp/beach-ntdp-training-series/"
                     "2026-beach-ntdp-summer-training-series-rosters/"},
]

TABLE = re.compile(r'<table class="tableizer-table">(.*?)</table>', re.S)
ROW = re.compile(r"<tr>\s*<td>([^<]*)</td>\s*<td>([^<]*)</td>(?:\s*<td>([^<]*)</td>)?", re.S)
# the heading immediately above each table names the age group
GROUP = re.compile(r">\s*((?:Girls|Boys|Women's|Men's)[^<>]{0,14})\s*<")


def ctx():
    for p in (os.environ.get("SSL_CERT_FILE"), "/root/.ccr/ca-bundle.crt"):
        if p and os.path.exists(p):
            return ssl.create_default_context(cafile=p)
    return ssl.create_default_context()


def get(url, body=None):
    req = urllib.request.Request(url, data=body, headers={
        "User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60, context=ctx()) as r:
        return r.read().decode("utf-8", "replace")


def txt(s):
    return _html.unescape(re.sub(r"\s+", " ", s)).strip()


def girls_only(name):
    return name.lower().startswith(("girls", "women"))


def scrape(url):
    """Return {group: [(first, last, region)]} for the girls' groups on a roster page."""
    page = get(url)
    out, pos = {}, 0
    for m in TABLE.finditer(page):
        heads = GROUP.findall(page[pos:m.start()])
        pos = m.end()
        group = txt(heads[-1]) if heads else "?"
        if not girls_only(group):
            continue
        out[group] = [tuple(txt(x or "") for x in r) for r in ROW.findall(m.group(1))]
    return out


def main(match=False):
    out = []
    for s in SERIES:
        rosters = scrape(s["rosters"])
        out.append(dict(s, groups={g: [{"first": a, "last": b, "region": c}
                                       for a, b, c in v] for g, v in rosters.items()}))
        print(f"{s['key']:>11}  " + ", ".join(f"{g} {len(v)}" for g, v in rosters.items()))

    # who keeps getting invited back
    seen = {}
    for s in out:
        for g, v in s["groups"].items():
            for a in v:
                seen.setdefault(f"{a['first']} {a['last']}", []).append(s["key"])
    every = [n for n, k in seen.items() if len(k) == len(out)]
    print(f"\n{len(seen)} distinct girls across {len(out)} series; "
          f"{len(every)} in all four: {', '.join(sorted(every))}")

    if match:
        ids = resolve(sorted(seen))
        for s in out:
            for v in s["groups"].values():
                for a in v:
                    a["id"] = ids.get(f"{a['first']} {a['last']}")
        got = sum(1 for v in ids.values() if v)
        print(f"resolved {got} of {len(ids)} to Volleyball Life ids")

    json.dump({"series": out, "appearances": seen},
              open(f"{DATA}/ntdp_series.json", "w"), indent=1)


def resolve(names):
    """Name -> Volleyball Life player id, taking the best female match on the search feed."""
    ids = {}
    for n in names:
        try:
            res = json.loads(get(f"{API}/playerprofile/search/{urllib.parse.quote(n)}"))
        except Exception:
            res = []
        cand = [p for p in (res or []) if not p.get("male")
                and (p.get("fullName") or "").strip().lower() == n.lower()]
        ids[n] = cand[0]["id"] if cand else None
        time.sleep(0.05)
    return ids


if __name__ == "__main__":
    main(match="--match" in sys.argv)
