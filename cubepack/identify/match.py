import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
"""Step 3 - score a polycube against a photographed piece.

silhouette IoU  x  crease chamfer  x  three-face brightness model,
maximised over orientation, yaw, elevation, scale and a small offset.
"""
import pickle, math, sys, time
import numpy as np
from PIL import Image
from scipy import ndimage
from polycube import enumerate_polycubes, orientations
import render as shade2

DOWN=4.0; CANVAS=(150,150); TAU=2.5
SHAPES=[(f"T{i}",c) for i,c in enumerate(enumerate_polycubes(4))] + \
       [(f"P{i}",c) for i,c in enumerate(enumerate_polycubes(5))]
SHD=dict(SHAPES); ORIS={n:orientations(c) for n,c in SHAPES}

def centre(arr,canvas):
    H,W=canvas; ys,xs=np.nonzero(arr>0); cy,cx=ys.mean(),xs.mean()
    out=np.zeros((H,W),arr.dtype)
    oy=int(round(H/2-cy)); ox=int(round(W/2-cx)); h,w=arr.shape
    y0,y1=max(0,oy),min(H,oy+h); x0,x1=max(0,ox),min(W,ox+w)
    out[y0:y1,x0:x1]=arr[y0-oy:y1-oy, x0-ox:x1-ox]
    return out

def prep(p):
    h,w=p['mask'].shape
    nw,nh=int(w/DOWN),int(h/DOWN)
    m=np.array(Image.fromarray(p['mask']).resize((nw,nh),Image.NEAREST))
    g=np.array(Image.fromarray((p['gray']*255).astype(np.uint8)).resize((nw,nh),Image.BILINEAR)).astype(float)/255
    m=centre(m,CANVAS).astype(bool); g=centre(g*(m0:=1),CANVAS) if False else centre(g,CANVAS)
    g=g*m
    e=shade2.obs_edges(m,g)
    dt=ndimage.distance_transform_edt(~e)
    return dict(mask=m, gray=g, edges=e, dt=dt, area=int(m.sum()))

def score(o, lab):
    r=lab>0
    inter=o['mask']&r; ni=int(inter.sum())
    if ni<30: return 0,0,0,0
    iou=ni/int((o['mask']|r).sum())
    re=shade2.edges_of(lab)&ndimage.binary_dilation(r,np.ones((3,3)))
    d1=o['dt'][re].mean() if re.any() else 20
    dtr=ndimage.distance_transform_edt(~re)
    d2=dtr[o['edges']].mean() if o['edges'].any() else 20
    cham=math.exp(-(d1+d2)/(2*TAU))
    g=o['gray'][inter]; l=(lab//1000)[inter]
    tot=((g-g.mean())**2).sum(); res=0.0
    for c in (1,2,3):
        m=(l==c)
        if m.any(): gg=g[m]; res+=((gg-gg.mean())**2).sum()
    r2=max(0.0,1-res/tot) if tot>0 else 0
    return iou*cham*(0.4+0.6*r2), iou, cham, r2

def render(name,oi,alpha,phi,roll,s,shift=(0,0)):
    lab=shade2.render(ORIS[name][oi],math.radians(alpha),math.radians(phi),math.radians(roll),s,CANVAS)
    if lab is None: return None
    return np.roll(lab,shift,axis=(0,1)) if shift!=(0,0) else lab

def area_scale(name,oi,alpha,phi,roll,area):
    lab=shade2.render(ORIS[name][oi],math.radians(alpha),math.radians(phi),math.radians(roll),40.0,(300,300))
    if lab is None: return None
    return 40.0*math.sqrt(area/np.count_nonzero(lab))

def ev(o,name,oi,al,ph,ro,s,sh):
    lab=render(name,oi,al,ph,ro,s,sh)
    if lab is None: return (0,0,0,0)
    return score(o,lab)

def refine(o,name,oi,al,ph,ro,s,phi_lo=34,phi_hi=52):
    cur=dict(alpha=al,phi=ph,roll=ro,s=s,shift=(0,0))
    best=ev(o,name,oi,al,ph,ro,s,(0,0))[0]
    for _ in range(3):
        for key,vals in (('alpha',[cur['alpha']+d for d in (-4,-3,-2,-1,1,2,3,4)]),
                         ('phi',[v for v in (cur['phi']-4,cur['phi']-2,cur['phi']+2,cur['phi']+4) if phi_lo<=v<=phi_hi]),
                         ('roll',[cur['roll']+d for d in (-3,-1.5,1.5,3)]),
                         ('s',[cur['s']*f for f in (0.95,0.98,1.02,1.05)]),
                         ('shift',[(dy,dx) for dy in (-2,0,2) for dx in (-2,0,2) if (dy,dx)!=(0,0)])):
            for v in vals:
                t=dict(cur); t[key]=v
                sc=ev(o,name,oi,t['alpha'],t['phi'],t['roll'],t['s'],t['shift'])[0]
                if sc>best: best,cur=sc,t
    return best,cur

def identify(p, coarse_step=4, keep=20, phi0=42.0):
    o=prep(p); best={}
    for name,_ in SHAPES:
        for oi in range(len(ORIS[name])):
            for ad in range(0,90,coarse_step):
                s=area_scale(name,oi,ad,phi0,0,o['area'])
                if s is None: continue
                sc,iou,ch,r2=ev(o,name,oi,ad,phi0,0,s,(0,0))
                k=(name,oi)
                if sc>best.get(k,(-1,))[0]: best[k]=(sc,ad,s)
    top=sorted(((v[0],k[0],k[1],v[1],v[2]) for k,v in best.items()), reverse=True)[:keep]
    out=[]
    for sc0,name,oi,ad,s in top:
        b,cur=refine(o,name,oi,ad,phi0,0,s)
        sc,iou,ch,r2=ev(o,name,oi,cur['alpha'],cur['phi'],cur['roll'],cur['s'],cur['shift'])
        out.append(dict(score=sc,iou=iou,cham=ch,r2=r2,shape=name,ori=oi,n=len(SHD[name]),**cur))
    out.sort(key=lambda d:-d['score'])
    return out,o

if __name__=='__main__':
    pieces=pickle.load(open('pieces.pkl','rb'))
    idx=int(sys.argv[1]); t=time.time()
    res,_=identify(pieces[idx-1])
    print(f"piece {idx} {pieces[idx-1]['color']} ({time.time()-t:.0f}s)")
    for d in res[:8]:
        print(f"   {d['shape']:4}(n={d['n']}) score={d['score']:.3f} IoU={d['iou']:.3f} cham={d['cham']:.3f} R2={d['r2']:.3f} ori{d['ori']} a={d['alpha']:.0f} phi={d['phi']:.0f} s={d['s']:.1f}")
