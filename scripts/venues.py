"""Resolve every venue the planning page names to the address its organiser published.

  python3 scripts/venues.py            ->  data/venues.json

A venue name is not a location. "2400 Ocean Front Walk" is in Santa Monica, "Gulf Shores"
is in Alabama, and "Arizona Athletic Grounds" is in Mesa rather than Phoenix -- none of
which the name tells you. Volleyball Life hangs a Google Maps embed off each division's
location, and the query string in it is the address the organiser typed. That is the only
authority on where an event is, so it is cached here and the page checks itself against it.

Takes the tournament ids the page links to, plus every edition it draws numbers from.
"""
import json, os, re, sys, urllib.parse
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vbcrawl import get

OUT = os.path.join(HERE, "..", "data", "venues.json")
ST = re.compile(r",\s*([A-Z]{2})\b")


def addresses(tid):
    """{venue name: address} for one tournament, from its divisions' map links."""
    d = get(f"/tournament/{tid}") or {}
    out = {}
    for x in (d.get("divisions") or []):
        loc = x.get("location") or {}
        name = loc.get("name")
        if not name:
            continue
        q = urllib.parse.unquote(loc.get("googleUrl") or "")
        m = re.search(r"[?&]q=([^&]*)", q)
        addr = (m.group(1).strip() if m else "") or None
        # A bare coordinate pair is not an address, and says nothing a reader can check.
        if addr and re.fullmatch(r"-?\d+\.\d+[,\s]+-?\d+\.\d+", addr):
            addr = None
        out.setdefault(name, addr)
    return out


def main(tids):
    have = json.load(open(OUT)) if os.path.exists(OUT) else {}
    todo = [t for t in tids if str(t) not in have]
    print(f"{len(tids)} tournaments, {len(todo)} to fetch", flush=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        for tid, got in zip(todo, ex.map(addresses, todo)):
            have[str(tid)] = got
    json.dump(have, open(OUT, "w"), indent=1, sort_keys=True)
    n = sum(1 for v in have.values() for a in v.values() if a)
    print(f"wrote {OUT}: {len(have)} tournaments, {n} venues with an address")


if __name__ == "__main__":
    args = [int(x) for x in sys.argv[1:] if x.isdigit()]
    main(args or [])
