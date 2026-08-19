"""August temperature at Santa Cruz: one datapoint per year, back to 1893.

The tournament calendar is a beach calendar, so the question behind this is what an August
day on the Santa Cruz sand is actually like. Two answers, because they are two different
questions and they do not agree:

  tmax   the mean of the daily maximum over the 31 days of August -- the afternoon peak
  tmin   the mean of the daily minimum -- the pre-dawn low, which is what an evening on
         the sand and a 7am first serve are played in

  Station USC00047916, SANTA CRUZ, CA -- a US Historical Climatology Network site with
  daily observations from 1893. It is the only long record inside the town: every other
  Santa Cruz station in GHCN is a modern CoCoRaHS rain gauge with no thermometer. The
  station stopped reporting in April 2022, which is where the observed series ends.

For each element two series are built, because the raw one cannot be read on its own:

  observed   the mean of the daily values as the observer wrote them down, which is
             literally what was asked for. Days carrying a GHCN quality-control flag are
             dropped, and a year needs 28 of its 31 days to count.
  adjusted   NOAA's homogenised monthly value for the same station (USHCN v2.5, the
             "FLs.52j" product), which corrects the record for the things that move a
             thermometer's reading without the weather moving: a change in the hour of
             observation, a shift of the instrument, a new screen. It also carries
             2022-2025, infilled from neighbouring stations after the station closed.

How far apart those two run is not a matter of opinion, so the pipeline measures it: every
August is also differenced against Watsonville, 21 km down the coast, and the difference is
reported decade by decade. A pair of stations 21 km apart should hold a roughly constant
offset. For the daily minima they do, within about 1.5 degF for a century. For the maxima
they do not -- the offset wanders across a 6 degF range -- which is the whole reason the
homogenised line is drawn beside the observed one, and the reason the daytime series
carries a caveat the nighttime series does not.

  python3 scripts/august_temps.py                    ->  both elements, JSON + page each
  python3 scripts/august_temps.py tmin               ->  just the nights
  python3 scripts/august_temps.py --refresh          ->  re-download the sources first
"""
import csv, json, os, ssl, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
DOCS = os.path.join(HERE, "..", "docs")
CACHE = os.path.join(DATA, "ghcn")

STATION = "USC00047916"
USHCN_ID = "USH00047916"
NAME = "Santa Cruz, California"
# the yardstick: the nearest station with a record long enough to difference against, and
# still reporting. Watsonville Water Works, 21 km down the coast, daily since 1908.
NEIGHBOUR = "USC00049473"
NEIGHBOUR_NAME = "Watsonville"
NEIGHBOUR_KM = 21

DAILY = ("https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily"
         "/access/{}.csv")
USHCN = "https://www.ncei.noaa.gov/pub/data/ushcn/v2.5/ushcn.{1}.latest.{0}.tar.gz"
# NOAA publishes its own working: the station as reported, the same series after the
# time-of-observation correction, and the same again after pairwise homogenisation. The
# difference between consecutive stages is the adjustment, per station and per month.
STAGES = ("raw", "tob", "FLs.52j")

MIN_DAYS = 28      # of 31; below this the month's mean is a different question
SMOOTH = 11        # centred running mean, the usual window for a climate series
AUG = 8

ELEMENTS = {
    "tmax": {
        "ghcn": "TMAX", "slug": "august-temps", "data": "august_temps",
        # where this station reads warm against Watsonville and the difference has to be
        # treated as the instrument. Shaded on the daytime chart; there is no nighttime
        # equivalent, because the nighttime offset never opens up like this.
        "drift": (2009, 2015),
    },
    "tmin": {
        "ghcn": "TMIN", "slug": "august-nights", "data": "august_nights",
        "drift": None,
    },
}


def _ctx():
    """Outbound HTTPS goes through an agent proxy, whose CA has to be trusted explicitly."""
    for p in (os.environ.get("SSL_CERT_FILE"), os.environ.get("REQUESTS_CA_BUNDLE"),
              "/root/.ccr/ca-bundle.crt"):
        if p and os.path.exists(p):
            return ssl.create_default_context(cafile=p)
    return ssl.create_default_context()


def refresh():
    """Pull the source files into data/ghcn/. They are the inputs, not the output."""
    import io, tarfile
    os.makedirs(CACHE, exist_ok=True)
    for sid in (STATION, NEIGHBOUR):
        with urllib.request.urlopen(DAILY.format(sid), context=_ctx(), timeout=300) as r:
            open(os.path.join(CACHE, sid + ".csv"), "wb").write(r.read())
    for el in ELEMENTS:
        for stage in STAGES:
            with urllib.request.urlopen(USHCN.format(stage, el), context=_ctx(),
                                        timeout=600) as r:
                blob = r.read()
            with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as t:
                member = next(m for m in t.getmembers() if USHCN_ID in m.name)
                open(os.path.join(CACHE, f"{USHCN_ID}.{stage}.{el}"), "wb").write(
                    t.extractfile(member).read())


def f(tenths_c):
    return tenths_c / 10.0 * 9 / 5 + 32


def daily(station, key):
    """{year: [degF, ...]} for August, quality-flagged days dropped."""
    out, rejected = {}, 0
    with open(os.path.join(CACHE, station + ".csv")) as fh:
        for row in csv.DictReader(fh):
            date = row["DATE"]
            if int(date[5:7]) != AUG:
                continue
            v = row[key].strip()
            if not v:
                continue
            # attributes are measurement,quality,source,time -- a non-blank quality flag
            # means NCEI's own checks caught the value, so it is not ours to average
            flags = row[key + "_ATTRIBUTES"].split(",")
            if len(flags) > 1 and flags[1].strip():
                rejected += 1
                continue
            out.setdefault(int(date[:4]), []).append(f(int(v)))
    return out, rejected


def observed(station, key):
    """{year: (mean degF, days used)} from the daily record, August only."""
    days, rejected = daily(station, key)
    return {y: (sum(v) / len(v), len(v)) for y, v in days.items()}, rejected


def stage(element, which="FLs.52j"):
    """{year: (mean degF, estimated?)} from one USHCN stage. Fixed-width: value 6, 3 flags."""
    out = {}
    for line in open(os.path.join(CACHE, f"{USHCN_ID}.{which}.{element}")):
        year, off = int(line[12:16]), 16 + (AUG - 1) * 9
        v = line[off:off + 6].strip()
        if v == "-9999":
            continue
        # dmflag E: the month was estimated from surrounding stations, or the pairwise
        # homogenisation dropped it. Either way it is not this station's own reading.
        out[year] = (int(v) / 100.0 * 9 / 5 + 32, line[off + 6] == "E")
    return out


def adjusted(element):
    return stage(element, "FLs.52j")


def ladder(element):
    """What each stage of NOAA's pipeline did to this station's Augusts.

    tob is the time-of-observation correction, which follows from the observer's recorded
    reading hour; pha is what the pairwise homogenisation algorithm did on top of it,
    comparing this station against its neighbours. Reported per year, and collapsed into
    the segments the algorithm actually works in.
    """
    raw, tob, fin = (stage(element, s) for s in STAGES)
    years = [y for y in sorted(fin) if y in raw and y in tob]
    per = {y: (round(tob[y][0] - raw[y][0], 2), round(fin[y][0] - tob[y][0], 2))
           for y in years}
    segs = []
    for y in years:
        a = per[y][1]
        # one segment per constant adjustment; near-equal adjacent steps are the same
        # break seen through slightly different months, so they are merged
        if segs and y == segs[-1]["to"] + 1 and abs(segs[-1]["adj"] - a) < 0.75:
            segs[-1]["to"] = y
            segs[-1]["_v"].append(a)
        else:
            segs.append({"from": y, "to": y, "adj": a, "_v": [a]})
    for s_ in segs:
        s_["adj"] = round(sum(s_["_v"]) / len(s_["_v"]), 2)
        s_["years"] = s_["to"] - s_["from"] + 1
        del s_["_v"]
    return {
        "per_year": {str(y): {"tob": per[y][0], "pha": per[y][1]} for y in years},
        "tob_mean": round(sum(v[0] for v in per.values()) / len(per), 2),
        "pha_mean": round(sum(v[1] for v in per.values()) / len(per), 2),
        # the breaks worth naming: a sustained correction of at least a degree
        "segments": [s_ for s_ in segs if s_["years"] >= 3 and abs(s_["adj"]) >= 1.0],
    }


def against_neighbour(key):
    """Santa Cruz minus Watsonville, decade by decade.

    Two stations 21 km apart share their weather, so the difference between them should be
    a constant. Where it is not, the station moved and the record says so.
    """
    here, _ = observed(STATION, key)
    there, _ = observed(NEIGHBOUR, key)
    both = {y: here[y][0] - there[y][0] for y in here
            if y in there and here[y][1] >= MIN_DAYS and there[y][1] >= MIN_DAYS}
    out = []
    for dec in sorted({y // 10 * 10 for y in both}):
        d = [v for y, v in both.items() if dec <= y < dec + 10]
        # a decade holding one or two Augusts is noise, not an offset
        if len(d) >= 3:
            out.append({"decade": dec, "diff": round(sum(d) / len(d), 2), "years": len(d)})
    return out


def running(series, window=SMOOTH):
    """Centred mean over `window` years. Two absences inside the window are tolerated --
    the record has a handful of gaps, and demanding a full window would erase eleven years
    of trend line around each of them -- but a third leaves the line broken, which is what
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


def diurnal():
    """{year: mean degF between the day's high and its low}, on days that have both."""
    hi, _ = daily(STATION, "TMAX")
    lo, _ = daily(STATION, "TMIN")
    out = {}
    for y in hi:
        # only Augusts where both elements survived quality control on the same count of
        # days; a high from one day and a low from another is not a daily range
        if y in lo and len(hi[y]) == len(lo[y]) >= MIN_DAYS:
            out[y] = sum(a - b for a, b in zip(hi[y], lo[y])) / len(hi[y])
    return out


def build(element):
    spec = ELEMENTS[element]
    obs, rejected = observed(STATION, spec["ghcn"])
    adj = adjusted(element)
    rows = []
    for y in sorted(set(obs) | set(adj)):
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
    off = against_neighbour(spec["ghcn"])
    rng = diurnal()
    ry = sorted(rng)
    rb, _ = fit(ry, [rng[y] for y in ry])
    return {
        "element": element,
        "ghcn_element": spec["ghcn"],
        "drift": list(spec["drift"]) if spec["drift"] else None,
        "station": {"id": STATION, "ushcn": USHCN_ID, "name": NAME,
                    "lat": 36.9878, "lon": -121.9994, "elevation_m": 21.3},
        "min_days": MIN_DAYS, "smooth": SMOOTH,
        "qc_rejected_days": rejected,
        "observed_years": len(kept),
        "observed_span": [min(kept), max(kept)],
        "observed_mean_f": round(sum(kept.values()) / len(kept), 2),
        "observed_trend_f_per_decade": round(ob * 10, 3),
        "first30_f": round(sum(kept[y] for y in sorted(kept)[:30]) / 30, 2),
        "last30_f": round(sum(kept[y] for y in sorted(kept)[-30:]) / 30, 2),
        "adjusted_span": [min(adjs), max(adjs)],
        "adjusted_trend_f_per_decade": round(ab * 10, 3),
        "neighbour": {
            "id": NEIGHBOUR, "name": NEIGHBOUR_NAME, "km": NEIGHBOUR_KM,
            "decades": off,
            "spread_f": round(max(o["diff"] for o in off) - min(o["diff"] for o in off), 2),
        },
        "ladder": ladder(element),
        "diurnal": {
            "span": [ry[0], ry[-1]], "years": len(ry),
            "mean_f": round(sum(rng.values()) / len(rng), 2),
            "trend_f_per_decade": round(rb * 10, 3),
            "first30_f": round(sum(rng[y] for y in ry[:30]) / 30, 2),
            "last30_f": round(sum(rng[y] for y in ry[-30:]) / 30, 2),
        },
        "years": rows,
    }


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if "--refresh" in sys.argv:
        refresh()
    sys.path.insert(0, HERE)
    from august_page import page
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(DOCS, exist_ok=True)
    for element in (args or list(ELEMENTS)):
        series = build(element)
        spec = ELEMENTS[element]
        with open(os.path.join(DATA, spec["data"] + ".json"), "w") as fh:
            json.dump(series, fh, indent=1)
        open(os.path.join(DOCS, spec["slug"] + ".html"), "w").write(page(series))
        print(f"{element}: {series['observed_years']} Augusts, "
              f"{series['observed_span'][0]}-{series['observed_span'][1]}; "
              f"mean {series['observed_mean_f']} degF, "
              f"trend {series['observed_trend_f_per_decade']:+} degF/decade")
