"""August daytime warmth at Santa Cruz: one datapoint per year, back to 1893.

The tournament calendar is a beach calendar, so the question behind this is how hot an
August day on the Santa Cruz sand actually gets, and whether that has moved. The answer
is the mean of the daily maximum temperature over the 31 days of August, one number per
year, from the longest reliable record the town has.

  Station USC00047916, SANTA CRUZ, CA -- a US Historical Climatology Network site with
  daily observations from 1893. It is the only long record inside the town: every other
  Santa Cruz station in GHCN is a modern CoCoRaHS rain gauge with no thermometer. The
  station stopped reporting in April 2022, which is where the observed series ends.

Two series are built, because the raw one cannot be read on its own:

  observed   the mean of the daily TMAX values as the observer wrote them down, which is
             literally what was asked for. Days carrying a GHCN quality-control flag are
             dropped, and a year needs 28 of its 31 days to count.
  adjusted   NOAA's homogenised monthly TMAX for the same station (USHCN v2.5, the
             "FLs.52j" product), which corrects the record for the things that move a
             thermometer's reading without the weather moving: a change in the hour of
             observation, a shift of the instrument, a new screen. It also carries
             2022-2025, infilled from neighbouring stations after the station closed.

They disagree, and the disagreement is the point. Against Watsonville -- 21 km away and
still reporting -- Santa Cruz reads about 1.3 degF warmer through the 1990s and 2000s,
then 4 to 6 degF warmer from 2009 to 2015, then falls back. A gap that opens and closes
against a neighbour is the station moving, not the climate, so the observed line is
shown as observed and the homogenised line beside it.

  python3 scripts/august_temps.py             ->  data/august_temps.json, docs/august-temps.html
  python3 scripts/august_temps.py --refresh   ->  re-download both sources from NCEI first
"""
import csv, json, os, ssl, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
DOCS = os.path.join(HERE, "..", "docs")
CACHE = os.path.join(DATA, "ghcn")

STATION = "USC00047916"
USHCN_ID = "USH00047916"
NAME = "Santa Cruz, California"
DAILY = ("https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily"
         "/access/{}.csv")
USHCN = "https://www.ncei.noaa.gov/pub/data/ushcn/v2.5/ushcn.tmax.latest.FLs.52j.tar.gz"

MIN_DAYS = 28      # of 31; below this the month's mean is a different question
SMOOTH = 11        # centred running mean, the usual window for a climate series
AUG = 8


def _ctx():
    """Outbound HTTPS goes through an agent proxy, whose CA has to be trusted explicitly."""
    for p in (os.environ.get("SSL_CERT_FILE"), os.environ.get("REQUESTS_CA_BUNDLE"),
              "/root/.ccr/ca-bundle.crt"):
        if p and os.path.exists(p):
            return ssl.create_default_context(cafile=p)
    return ssl.create_default_context()


def refresh():
    """Pull both source files into data/ghcn/. They are the inputs, not the output."""
    import io, tarfile
    os.makedirs(CACHE, exist_ok=True)
    url = DAILY.format(STATION)
    with urllib.request.urlopen(url, context=_ctx(), timeout=300) as r:
        open(os.path.join(CACHE, STATION + ".csv"), "wb").write(r.read())
    with urllib.request.urlopen(USHCN, context=_ctx(), timeout=600) as r:
        blob = r.read()
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as t:
        member = next(m for m in t.getmembers() if USHCN_ID in m.name)
        open(os.path.join(CACHE, USHCN_ID + ".FLs.52j.tmax"), "wb").write(
            t.extractfile(member).read())


def f(tenths_c):
    return tenths_c / 10.0 * 9 / 5 + 32


def observed():
    """{year: (mean degF, days used)} from the daily record, August only."""
    days = {}
    rejected = 0
    with open(os.path.join(CACHE, STATION + ".csv")) as fh:
        for row in csv.DictReader(fh):
            date = row["DATE"]
            if int(date[5:7]) != AUG:
                continue
            v = row["TMAX"].strip()
            if not v:
                continue
            # attributes are measurement,quality,source,time -- a non-blank quality flag
            # means NCEI's own checks caught the value, so it is not ours to average
            flags = row["TMAX_ATTRIBUTES"].split(",")
            if len(flags) > 1 and flags[1].strip():
                rejected += 1
                continue
            days.setdefault(int(date[:4]), []).append(f(int(v)))
    return {y: (sum(v) / len(v), len(v)) for y, v in days.items()}, rejected


def adjusted():
    """{year: (mean degF, estimated?)} from USHCN. Fixed-width: value 6, then 3 flags."""
    out = {}
    path = os.path.join(CACHE, USHCN_ID + ".FLs.52j.tmax")
    for line in open(path):
        year, off = int(line[12:16]), 16 + (AUG - 1) * 9
        v = line[off:off + 6].strip()
        if v == "-9999":
            continue
        # dmflag E: the month was estimated from surrounding stations, or the pairwise
        # homogenisation dropped it. Either way it is not this station's own reading.
        out[year] = (int(v) / 100.0 * 9 / 5 + 32, line[off + 6] == "E")
    return out


def running(series, window=SMOOTH):
    """Centred mean over `window` years. Two absences inside the window are tolerated --
    the record has five gaps, and demanding a full window would erase eleven years of
    trend line around each of them -- but a third leaves the line broken, which is what
    a hole in the record should look like."""
    half, out = window // 2, {}
    for y in series:
        span = [series[k] for k in range(y - half, y + half + 1) if k in series]
        if len(span) >= window - 2:
            out[y] = sum(span) / len(span)
    return out


def fit(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return (sxy / sxx if sxx else 0.0), my


def build():
    obs, rejected = observed()
    adj = adjusted()
    years = sorted(set(obs) | set(adj))
    rows = []
    for y in years:
        mean, days = obs.get(y, (None, 0))
        a, est = adj.get(y, (None, False))
        rows.append({
            "year": y,
            "mean_f": round(mean, 2) if mean is not None else None,
            "days": days,
            "short": bool(mean is not None and days < MIN_DAYS),
            "adj_f": round(a, 2) if a is not None else None,
            "adj_estimated": est,
        })
    kept = {r["year"]: r["mean_f"] for r in rows if r["mean_f"] is not None and not r["short"]}
    adjs = {r["year"]: r["adj_f"] for r in rows if r["adj_f"] is not None}
    ob, _ = fit(sorted(kept), [kept[y] for y in sorted(kept)])
    ab, _ = fit(sorted(adjs), [adjs[y] for y in sorted(adjs)])
    return {
        "station": {"id": STATION, "ushcn": USHCN_ID, "name": NAME,
                    "lat": 36.9878, "lon": -121.9994, "elevation_m": 21.3},
        "min_days": MIN_DAYS, "smooth": SMOOTH,
        "qc_rejected_days": rejected,
        "observed_years": len(kept),
        "observed_span": [min(kept), max(kept)],
        "observed_mean_f": round(sum(kept.values()) / len(kept), 2),
        "observed_trend_f_per_decade": round(ob * 10, 3),
        "adjusted_span": [min(adjs), max(adjs)],
        "adjusted_trend_f_per_decade": round(ab * 10, 3),
        "years": rows,
    }


if __name__ == "__main__":
    if "--refresh" in sys.argv:
        refresh()
    series = build()
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "august_temps.json"), "w") as fh:
        json.dump(series, fh, indent=1)
    sys.path.insert(0, HERE)
    from august_page import page
    os.makedirs(DOCS, exist_ok=True)
    open(os.path.join(DOCS, "august-temps.html"), "w").write(page(series))
    print(f"{series['observed_years']} Augusts, "
          f"{series['observed_span'][0]}-{series['observed_span'][1]}; "
          f"mean {series['observed_mean_f']} degF")
