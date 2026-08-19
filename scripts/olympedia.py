"""Scrape Olympic beach volleyball height and weight from Olympedia.

  python3 scripts/olympedia.py            ->  data/olympedia_bv.json

Olympedia has no bulk export, so the route is edition -> result page -> athlete page.
Every athlete page carries a `biodata` table whose Measurements row reads "180 cm / 70 kg";
either half can be missing, and for a good number of athletes the whole row is absent.

Two populations are collected and kept apart. The senior Olympic tournament (1996-2024)
is the adult reference. The Youth Olympic tournament (2010, 2014, 2018) is a field of
16- to 18-year-olds, which is the only Olympic-grade sample that is actually Haisley's
age -- comparing a 16-year-old against senior means is the wrong comparison, and having
both lets the page say so with data rather than with a caveat.

Measurements are self-reported to the NOC at the time of the Games and are never updated,
so treat them as a snapshot of that athlete at that edition, not as a current fact.
"""
import json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

SITE = "https://www.olympedia.org"
HDRS = {"User-Agent": "Mozilla/5.0 (compatible; height-weight research)"}
DATA = os.path.join(os.path.dirname(__file__) or ".", "..", "data")
WORKERS = 6

# edition id -> (year, host, senior?)
EDITIONS = {
    24: (1996, "Atlanta", True),      25: (2000, "Sydney", True),
    26: (2004, "Athina", True),       53: (2008, "Beijing", True),
    54: (2012, "London", True),       59: (2016, "Rio de Janeiro", True),
    61: (2020, "Tokyo", True),        63: (2024, "Paris", True),
    65: (2010, "Singapore", False),   67: (2014, "Nanjing", False),
    69: (2018, "Buenos Aires", False),
}

CM = re.compile(r"(\d+)\s*cm")
KG = re.compile(r"(\d+)\s*kg")
ROW = re.compile(r"<tr><th>([^<]+)</th><td>(.*?)</td></tr>", re.S)
TAG = re.compile(r"<[^>]+>")


def get(url, tries=4):
    for a in range(tries):
        try:
            r = urllib.request.Request(url, headers=HDRS)
            with urllib.request.urlopen(r, timeout=60) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(1.0 * (a + 1))
    return ""


def text(s):
    return re.sub(r"\s+", " ", TAG.sub(" ", s)).strip()


def athlete(pid):
    """Parse one athlete page. Returns None unless they actually played beach volleyball."""
    s = get(f"{SITE}/athletes/{pid}")
    if not s or "Beach Volleyball" not in s:
        return None
    bio = dict((k.strip(), v) for k, v in ROW.findall(s))
    meas = text(bio.get("Measurements", ""))
    cm, kg = CM.search(meas), KG.search(meas)
    born = text(bio.get("Born", ""))
    byear = re.search(r"\b(1[89]\d\d|20\d\d)\b", born)
    name = re.search(r"<h1>\s*(.*?)\s*</h1>", s, re.S)
    return {
        "id": int(pid),
        "name": text(name.group(1)) if name else "",
        "sex": text(bio.get("Sex", "")),
        "cm": int(cm.group(1)) if cm else None,
        "kg": int(kg.group(1)) if kg else None,
        "born": int(byear.group(1)) if byear else None,
        "noc": text(bio.get("NOC", "")),
    }


def main():
    people, seen = {}, set()
    try:                                    # resume: the athlete fetch is the slow half
        for rec in json.load(open(f"{DATA}/olympedia_bv.json"))["athletes"]:
            people[rec["id"]] = rec
        print(f"resuming with {len(people)} athletes already parsed")
    except (FileNotFoundError, KeyError):
        pass

    games = {}                              # athlete id -> list of (year, senior?)
    for eid, (year, host, senior) in sorted(EDITIONS.items(), key=lambda kv: kv[1][0]):
        page = get(f"{SITE}/editions/{eid}/sports/VBV")
        rids = sorted(set(re.findall(r"/results/(\d+)", page)), key=int)
        ids = set()
        for rid in rids:
            ids |= set(re.findall(r"/athletes/(\d+)", get(f"{SITE}/results/{rid}")))
        print(f"{year} {host}: {len(rids)} events, {len(ids)} athlete links")
        for pid in ids:
            games.setdefault(int(pid), []).append((year, senior))
        seen |= {int(p) for p in ids}

    todo = sorted(seen - set(people))
    print(f"{len(seen)} distinct athletes, {len(todo)} to fetch")
    for i in range(0, len(todo), 60):
        part = todo[i:i + 60]
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for rec in ex.map(athlete, part):
                if rec:
                    people[rec["id"]] = rec
        print(f"  {min(i + 60, len(todo))}/{len(todo)} fetched, {len(people)} kept",
              flush=True)
        save(people, games)

    save(people, games)
    fem = [p for p in people.values() if p["sex"] == "Female"]
    both = [p for p in fem if p["cm"] and p["kg"]]
    print(f"\n{len(people)} beach volleyball Olympians; {len(fem)} women, "
          f"{len(both)} with both height and weight")


def save(people, games):
    for pid, rec in people.items():
        g = games.get(pid, [])
        rec["years"] = sorted({y for y, _ in g})
        rec["senior"] = any(s for _, s in g)
        rec["youth"] = any(not s for _, s in g)
    json.dump({"source": SITE, "editions": {str(k): v for k, v in EDITIONS.items()},
               "athletes": sorted(people.values(), key=lambda p: p["id"])},
              open(f"{DATA}/olympedia_bv.json", "w"), indent=1)


if __name__ == "__main__":
    main()
