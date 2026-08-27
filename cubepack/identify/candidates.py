import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
"""Step 4 - write cand_NN.json: the ranked candidate shapes for one piece."""
import pickle, sys, json, math
import numpy as np
import match as I

pieces=pickle.load(open('pieces.pkl','rb'))
idx=int(sys.argv[1]); p=pieces[idx-1]
o=I.prep(p)
best={}     # shape -> best (fullscore, iou, params) over orientations/yaw
for name,_ in I.SHAPES:
    for oi in range(len(I.ORIS[name])):
        for ad in range(0,90,4):
            s=I.area_scale(name,oi,ad,42.0,0,o['area'])
            if s is None: continue
            sc,iou,ch,r2=I.ev(o,name,oi,ad,42.0,0,s,(0,0))
            k=(name,oi)
            if sc>best.get(k,(-1,))[0]: best[k]=(sc,iou,ad,s)
# refine the best 30 (shape,orientation) pairs
top=sorted(((v[0],v[1],k[0],k[1],v[2],v[3]) for k,v in best.items()), reverse=True)[:18]
topi=sorted(((v[1],v[0],k[0],k[1],v[2],v[3]) for k,v in best.items()), reverse=True)[:18]
pool={}
for sc,iou,name,oi,ad,s in top: pool[(name,oi)]=(ad,s)
for iou,sc,name,oi,ad,s in topi: pool.setdefault((name,oi),(ad,s))
res={}
for (name,oi),(ad,s) in pool.items():
    b,cur=I.refine(o,name,oi,ad,42.0,0,s)
    sc,iou,ch,r2=I.ev(o,name,oi,cur['alpha'],cur['phi'],cur['roll'],cur['s'],cur['shift'])
    rec=dict(score=float(sc),iou=float(iou),cham=float(ch),r2=float(r2),ori=oi,
             alpha=float(cur['alpha']),phi=float(cur['phi']),roll=float(cur['roll']),
             s=float(cur['s']),shift=list(cur['shift']),n=len(I.SHD[name]))
    if name not in res or sc>res[name]['score']: res[name]=rec
json.dump(dict(piece=idx,color=p['color'],cands=res), open(f'cand_{idx:02d}.json','w'), indent=1)
r=sorted(res.items(), key=lambda kv:-kv[1]['score'])
print(f"piece {idx} {p['color']}: " + ", ".join(f"{k}({v['n']}) {v['score']:.3f}/{v['iou']:.2f}" for k,v in r[:6]))
