"""One player's whole career, year by year: when did she get good?

  python3 scripts/history.py 64896
  python3 scripts/history.py "Thais Treumann"

The group reports run on a twelve-month window, which is the right frame for "who is
strong now" and useless for "how did she get here". This reads the entire tournament
history off the profile, joins the field size for each division, and prints the shape of
the career: results by year, the mix of junior against adult fields, every podium in an
18U-or-older draw, and the biggest fields ever won.

The adult-field share is the column worth reading. A junior who is climbing is usually one
who started entering older draws a year or two before she could win them, and that shows
up here as a rising adult share with a *worsening* median finish, ahead of the season
where the results arrive.
"""
import datetime, json, os, re, sys, time, urllib.parse, urllib.request
from collections import Counter, defaultdict

API = "https://api-v8.volleyballlife.com"
HDRS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
JSON = dict(HDRS, **{"Content-Type": "application/json"})
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
PAIRS = 1          # doubles only: a team entry's finish is not the individual's result


def get(path, body=None, tries=4):
    data = json.dumps(body).encode() if body is not None else None
    for a in range(tries):
        try:
            r = urllib.request.Request(API + path, data=data,
                                       headers=JSON if body is not None else HDRS)
            with urllib.request.urlopen(r, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            time.sleep(0.5 * (a + 1))
    return None


def resolve(who):
    if who.isdigit():
        return int(who)
    hits = get(f"/playerprofile/search/{urllib.parse.quote(who)}") or []
    if not hits:
        sys.exit(f"no player matching {who!r}")
    return hits[0]["id"]


def adult(div):
    """True for a division with no age ceiling -- women's, open, pro."""
    d = div.lower()
    if re.search(r"\d\d\s*u|u\s*\d\d|girls|boys", d):
        return False
    return any(k in d for k in ("women", "open", "pro", "adult", "coed"))


def ceiling(div):
    """The age ceiling of a division, 99 for an adult field, None if unreadable."""
    m = re.search(r"(\d\d)\s*u|u\s*(\d\d)", div.lower())
    if m:
        return int(m.group(1) or m.group(2))
    if adult(div):
        return 99
    return 18 if "class of" in div.lower() else None


def history(pid):
    pr = get(f"/playerprofile/{pid}")
    if not pr:
        sys.exit(f"no profile for {pid}")
    tours = pr.get("tournaments", [])
    counts = {}
    ids = sorted({t["id"] for t in tours})
    for i in range(0, len(ids), 40):
        res = get("/Tournament/CountsV3Bulk", {"tournamentIds": ids[i:i + 40]}) or {}
        counts.update(res)
        time.sleep(0.3)
    field = {d["id"]: d["teamCount"] for divs in counts.values() for d in (divs or [])}
    ev = [{"date": t["date"][:10], "name": t["tournament"].strip(),
           "div": (t.get("division") or "").strip(), "finish": t.get("finish"),
           "field": field.get(t.get("tdId")),
           "partners": [p["name"] for p in (t.get("partners") or [])],
           "pids": [p.get("id") for p in (t.get("partners") or [])]}
          for t in tours]
    return pr, [e for e in ev if len(e["partners"]) == PAIRS and e["finish"]]


def report(pr, ev):
    dob = datetime.date.fromisoformat(pr["dob"][:10]) if pr.get("dob") else None
    age = (lambda d: (datetime.date.fromisoformat(d) - dob).days / 365.25) if dob else \
        (lambda d: float("nan"))
    name = f'{pr.get("firstName")} {pr.get("lastName")}'
    tv = get(f"/playerprofile/{pr['id']}/truvolley") or {}
    print(f"{name}  id {pr['id']}  born {pr.get('dob', '?')[:10]}  grad {pr.get('gradYear')}  "
          f"{pr.get('height')}  {pr.get('city', '').strip()}, {pr.get('state')}")
    print(f"  club {pr.get('club')}   AVP points {pr.get('avpPoints')}   "
          f"committed {pr.get('committedSchool') or 'no'}")
    print(f"  TruVolley {tv.get('truVolley')} (peak {tv.get('peak')}), "
          f"{tv.get('wins')}-{(tv.get('matchesPlayed') or 0) - (tv.get('wins') or 0)}, "
          f"{len(ev)} doubles entries {min(e['date'] for e in ev)} .. "
          f"{max(e['date'] for e in ev)}\n")

    by = defaultdict(list)
    for e in ev:
        by[e["date"][:4]].append(e)
    print(f"{'YEAR':6}{'AGE':>5}{'N':>4}{'WINS':>6}{'POD':>5}{'MED':>5}{'ADULT':>7}")
    for y in sorted(by):
        g = by[y]
        fin = sorted(e["finish"] for e in g)
        ad = sum(1 for e in g if adult(e["div"]))
        print(f"{y:6}{sum(age(e['date']) for e in g) / len(g):5.1f}{len(g):>4}"
              f"{sum(1 for e in g if e['finish'] == 1):>6}"
              f"{sum(1 for e in g if e['finish'] <= 3):>5}"
              f"{fin[len(fin) // 2]:>5}{100 * ad // len(g):>6}%")

    print("\npodiums in an 18U-or-older field")
    for e in sorted(ev, key=lambda x: x["date"]):
        c = ceiling(e["div"])
        if c and c >= 18 and e["finish"] <= 3:
            print(f"  {e['date']}  age {age(e['date']):4.1f}  {e['finish']:>2}/"
                  f"{e['field'] or '?':<4} {e['div'][:22]:22s} {e['name'][:52]}")

    print("\nbiggest fields won")
    for e in sorted((e for e in ev if e["finish"] == 1 and (e["field"] or 0) >= 16),
                    key=lambda x: -x["field"])[:10]:
        print(f"  {e['date']}  {e['field']:>3} teams  {e['div'][:20]:20s} {e['name'][:50]}")

    print("\nmost frequent partners")
    for nm, c in Counter(p for e in ev for p in e["partners"]).most_common(8):
        d = [e["date"] for e in ev if nm in e["partners"]]
        print(f"  {c:>2}  {nm:26s} {min(d)} .. {max(d)}")


def placing(e):
    """Finish as a percentage of the field beaten: a win is 100, last is 0.

    Beach draws share finishes -- everyone knocked out in the same round gets the same
    number -- so a 5th in a draw of 20 is really 5th-8th and this reads a shade low.
    """
    f = e["field"]
    return None if not f or f < 2 else 100 * (1 - (e["finish"] - 1) / (f - 1))


def partners(ev, since=None):
    """Results grouped by partner. Field size is the column that matters: percentage
    placing flatters a good result in a small local draw, so it is shown next to the
    median field rather than on its own."""
    import statistics as st
    sel = [e for e in ev if not since or e["date"] >= since]
    tv = {}
    for pid in {e["pids"][0] for e in sel if e["pids"][0]}:
        r = get(f"/playerprofile/{pid}/truvolley") or {}
        p = get(f"/playerprofile/{pid}") or {}
        tv[pid] = (r.get("truVolley"), p.get("gradYear"), p.get("height"))
        time.sleep(0.1)

    groups = defaultdict(list)
    for e in sel:
        groups[e["partners"][0]].append(e)
    print(f"\nby partner{' since ' + since if since else ''}"
          f"  ({len(sel)} entries, {len(groups)} partners)")
    print(f"  {'PARTNER':24}{'N':>3}{'WIN':>4}{'POD':>4}{'MED':>5}{'FIELD':>6}{'PLACE':>7}"
          f"{'TV':>7}{'GRAD':>6}  RANGE")
    rank = lambda g: -st.median(x["field"] or 0 for x in g)
    for nm, g in sorted(groups.items(), key=lambda kv: (rank(kv[1]), -len(kv[1]))):
        pl = [placing(e) for e in g if placing(e) is not None]
        t, gr, _ = tv.get(g[0]["pids"][0], (None, None, None))
        print(f"  {nm[:23]:24}{len(g):>3}{sum(1 for e in g if e['finish'] == 1):>4}"
              f"{sum(1 for e in g if e['finish'] <= 3):>4}"
              f"{st.median(e['finish'] for e in g):>5.0f}"
              f"{st.median([e['field'] for e in g if e['field']] or [0]):>6.0f}"
              f"{(st.mean(pl) if pl else 0):>6.0f}%{str(t or '-'):>7}{str(gr or '-'):>6}  "
              f"{min(e['date'] for e in g)}..{max(e['date'] for e in g)}")


if __name__ == "__main__":
    pid = resolve(sys.argv[1] if len(sys.argv) > 1 else "64896")
    pr, ev = history(pid)
    json.dump(ev, open(os.path.join(DATA, f"history_{pid}.json"), "w"), indent=1)
    report(pr, ev)
    partners(ev)
    partners(ev, since=sys.argv[2] if len(sys.argv) > 2 else None)
