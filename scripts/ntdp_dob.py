import json,os,re,sys,urllib.parse,urllib.request
from concurrent.futures import ThreadPoolExecutor
SP=os.path.dirname(os.path.abspath(__file__))
API="https://api-v8.volleyballlife.com"
H={"User-Agent":("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
   "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"),"Accept":"application/json"}
def get(p,tries=3):
    for _ in range(tries):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(API+p,headers=H),timeout=30).read())
        except Exception: pass
    return None
rows=json.load(open(os.path.join(SP,'ntdp_rows.json')))
rows=[r for r in rows if not re.match(r"(boys|men)",(r['division'] or ''),re.I)]
names=sorted({(r['first'].strip(),r['last'].strip()) for r in rows})
CACHE=os.path.join(SP,'dob_cache.json')
cache=json.load(open(CACHE)) if os.path.exists(CACHE) else {}
todo=[n for n in names if f"{n[0]} {n[1]}" not in cache]
print(f"{len(names)} unique athletes, {len(todo)} to look up",flush=True)
def norm(s): return re.sub(r'[^a-z]','',(s or '').lower())
def one(n):
    first,last=n; key=f"{first} {last}"
    res=get("/playerprofile/search/"+urllib.parse.quote(key)) or []
    cands=[p for p in res if norm(p.get('firstName'))==norm(first) and norm(p.get('lastName'))==norm(last)]
    if not cands: cands=[p for p in res if norm(p.get('lastName'))==norm(last)]
    out={"n_search":len(res),"n_exact":len(cands)}
    if cands:
        # prefer the profile with a dob; tie-break on most matches played
        best=None
        for c in cands[:6]:
            pr=get(f"/playerprofile/{c['id']}") or {}
            tv=get(f"/playerprofile/{c['id']}/truvolley") or {}
            cand={"id":c['id'],"dob":(pr.get('dob') or '')[:10] or None,
                  "grad":pr.get('gradYear') or None,"city":pr.get('cityState'),
                  "m":tv.get('matchesPlayed') or 0}
            if best is None or (cand['dob'] and not best['dob']) or \
               (bool(cand['dob'])==bool(best['dob']) and cand['m']>best['m']): best=cand
        out.update(best or {})
    return key,out
with ThreadPoolExecutor(8) as ex:
    for i,(k,v) in enumerate(ex.map(one,todo),1):
        cache[k]=v
        if i%40==0:
            json.dump(cache,open(CACHE,'w'),indent=1); print(f"  {i}/{len(todo)}",flush=True)
json.dump(cache,open(CACHE,'w'),indent=1)
got=sum(1 for v in cache.values() if v.get('dob'))
print(f"done: {len(cache)} cached, {got} with a birthdate")
