"""Match our Volleyball Life events to CBVA's own tournament pages.

Volleyball Life carries CBVA's Southern California juniors circuit but sanctions it as
"AVPA", so the sanction field cannot identify a CBVA event. CBVA's own site does: it
publishes the same tournaments at /tournaments/{id}, filterable by date, and the two
agree on venue and date. So the match is made against CBVA rather than guessed from a
name, and an event links out to CBVA only when CBVA itself lists it.

  python3 scripts/cbva.py            ->  data/cbva.json   (the CBVA listing, cached)
  python3 scripts/cbva.py --link     ->  data/cbva_links.json  (our tid -> CBVA url)
"""
import datetime, html as _html, json, os, re, ssl, sys, urllib.request

BASE = "https://cbva.com"
LIST = BASE + "/tournaments?page=1&pageSize=100&name=null&divisions=%5B%5D&venues=%5B%5D" \
              "&genders=%5B%5D&past={p}&startDate={a}&endDate={b}"
DATA = os.path.join(os.path.dirname(__file__) or ".", "..", "data")

# a tournament block: the header anchor (venue + date), then its division anchors
BLOCK = re.compile(r'href="/tournaments/(\d+)"[^>]*>(.*?)(?=href="/tournaments/\d+"|\Z)', re.S)
DIV = re.compile(r'href="/tournaments/\d+/(\d+)"[^>]*>(.*?)</a>', re.S)
DATE = re.compile(r">(\d{1,2}/\d{1,2}/\d{4})<")


def txt(s):
    return _html.unescape(re.sub(r"<[^>]+>|<!--.*?-->", "", s)).strip()


def _ctx():
    """Outbound HTTPS goes through an agent proxy, whose CA has to be trusted explicitly."""
    for p in (os.environ.get("SSL_CERT_FILE"), os.environ.get("REQUESTS_CA_BUNDLE"),
              "/root/.ccr/ca-bundle.crt"):
        if p and os.path.exists(p):
            return ssl.create_default_context(cafile=p)
    return ssl.create_default_context()


def fetch(a, b, past=True):
    url = LIST.format(a=a, b=b, p="true" if past else "false")
    with urllib.request.urlopen(urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60, context=_ctx()) as r:
        return r.read().decode("utf-8", "replace")


def parse(page):
    out = {}
    for tid, body in BLOCK.findall(page):
        head = body.split("</a>", 1)[0]
        d = DATE.search(body)
        if not d:
            continue
        m, day, y = (int(x) for x in d.group(1).split("/"))
        out[int(tid)] = {
            "id": int(tid),
            "venue": txt(re.sub(r"<span[^>]*>\s*\d{1,2}/\d{1,2}/\d{4}\s*</span>", "", head)),
            "date": f"{y:04d}-{m:02d}-{day:02d}",
            "divisions": [{"id": int(i), "name": txt(n)} for i, n in DIV.findall(body)],
        }
    return out


def crawl(start, end, past=True):
    """One request per month; CBVA returns well under a page of 100 per month."""
    all_t, a = {}, datetime.date.fromisoformat(start)
    stop = datetime.date.fromisoformat(end)
    while a <= stop:
        nxt = (a.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        b = min(nxt - datetime.timedelta(days=1), stop)
        got = parse(fetch(a.isoformat(), b.isoformat(), past))
        print(f"  {a:%Y-%m}  {len(got):>3} tournaments")
        all_t.update(got)
        a = nxt
    return all_t


def norm_venue(s):
    """CBVA writes 'Newland, Huntington Beach'; Volleyball Life writes it a dozen ways."""
    s = s.lower()
    s = re.sub(r"\b(beach|pier|park|courts?|complex|sand|volleyball|state|city|the|at|north|"
               r"south|of|street|st|ave|avenue)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return set(s.split())


def link(window):
    cb = {int(k): v for k, v in json.load(open(f"{DATA}/cbva.json"))["tournaments"].items()}
    by_date = {}
    for t in cb.values():
        by_date.setdefault(t["date"], []).append(t)

    # our events: name, date and whatever location the summaries feed carried
    loc = {}
    for f in ("past.json", "upcoming.json"):
        for path in (f, os.path.join(DATA, f)):
            try:
                for t in json.load(open(path)):
                    loc[t["id"]] = ", ".join(x for x in (t.get("locations") or []) if x)
                break
            except FileNotFoundError:
                pass

    out, seen = {}, set()
    for f in sorted(os.listdir(DATA)):
        if not f.endswith("_clean.json"):
            continue
        for tid, t in json.load(open(f"{DATA}/{f}"))["tour_info"].items():
            if tid in seen:
                continue
            seen.add(tid)
            # Volleyball Life names CBVA events "<division> <gender+age> at <venue>", but
            # just as often "6/13/26, Main Beach, Santa Cruz" with no location recorded at
            # all, so the whole name is offered to the venue match. Only CBVA's own venue
            # tokens are scored, so the extra words in the name cost nothing.
            ours = norm_venue(loc.get(int(tid), "") + " " + t["name"])
            best = None
            for c in by_date.get(t["date"], []):
                theirs = norm_venue(c["venue"])
                score = len(ours & theirs)
                if score and score >= len(theirs) - 1 and (best is None or score > best[0]):
                    best = (score, c)
            if not best:
                continue
            c = best[1]
            # prefer the division whose name Volleyball Life reused verbatim
            head = t["name"].rsplit(" at ", 1)[0]
            div = next((d for d in c["divisions"]
                        if d["name"] and d["name"].lower() in head.lower()), None)
            out[tid] = {
                "url": f"{BASE}/tournaments/{c['id']}" + (f"/{div['id']}" if div else ""),
                "cbvaId": c["id"], "divisionId": div["id"] if div else None,
                "venue": c["venue"], "name": t["name"], "date": t["date"],
            }
    json.dump(out, open(f"{DATA}/cbva_links.json", "w"), indent=1)
    named = sum(1 for v in out.values() if "cbva" in v["name"].lower())
    print(f"{len(out)} of {len(seen)} events matched to CBVA "
          f"({sum(1 for v in out.values() if v['divisionId'])} to a specific division; "
          f"{named} carry 'CBVA' in the Volleyball Life name)")


if __name__ == "__main__":
    win = ("2025-08-20", "2026-08-20")
    ahead = ("2026-08-12", "2027-08-11")
    if "--link" in sys.argv:
        link(win)
    elif "--upcoming" in sys.argv:
        print(f"crawling CBVA {ahead[0]} to {ahead[1]} (not yet played)")
        t = crawl(*ahead, past=False)
        json.dump({"window": ahead, "tournaments": t},
                  open(f"{DATA}/cbva_upcoming.json", "w"), indent=1)
        print(f"{len(t)} CBVA tournaments scheduled")
    else:
        print(f"crawling CBVA {win[0]} to {win[1]}")
        t = crawl(*win)
        json.dump({"window": win, "tournaments": t}, open(f"{DATA}/cbva.json", "w"), indent=1)
        print(f"{len(t)} CBVA tournaments cached")
