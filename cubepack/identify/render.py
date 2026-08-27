"""Step 2 - orthographic renderer for a polycube resting on the table.

Faces are labelled 1000*class + plane so that coplanar neighbours merge and the
remaining label boundaries are exactly the creases a camera would see.
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

def axes(alpha, phi, roll, s):
    ca,sa=math.cos(alpha),math.sin(alpha)
    sp,cp=math.sin(phi),math.cos(phi)
    ex=(-sa, ca*sp); ey=(ca, sa*sp); ez=(0.0,-cp)
    cr,sr=math.cos(roll),math.sin(roll)
    def rot(v): return (s*(v[0]*cr - v[1]*sr), s*(v[0]*sr + v[1]*cr))
    return rot(ex),rot(ey),rot(ez)

def render(cells, alpha, phi, roll, s, canvas):
    """label image: 0 = background, else 1000*class + plane index.
       class 1 = top (+z), 2 = +x face, 3 = +y face."""
    H,W=canvas
    ex,ey,ez=axes(alpha,phi,roll,s)
    def pr(p,ox=0.,oy=0.):
        X,Y,Z=p
        return (ox+X*ex[0]+Y*ey[0]+Z*ez[0], oy+X*ex[1]+Y*ey[1]+Z*ez[1])
    pts=[pr((x+i,y+j,z+k)) for (x,y,z) in cells for i in (0,1) for j in (0,1) for k in (0,1)]
    mnx=min(p[0] for p in pts); mxx=max(p[0] for p in pts)
    mny=min(p[1] for p in pts); mxy=max(p[1] for p in pts)
    if mxx-mnx>=W-2 or mxy-mny>=H-2: return None
    ox=(W-(mxx+mnx))/2; oy=(H-(mxy+mny))/2
    img=Image.new('I',(W,H),0); dr=ImageDraw.Draw(img)
    n=(math.cos(alpha)*math.cos(phi), math.sin(alpha)*math.cos(phi), math.sin(phi))
    for (x,y,z) in sorted(cells, key=lambda c: c[0]*n[0]+c[1]*n[1]+c[2]*n[2]):
        for lab,q in ((1000+z+1,[(x,y,z+1),(x+1,y,z+1),(x+1,y+1,z+1),(x,y+1,z+1)]),
                      (2000+x+1,[(x+1,y,z),(x+1,y+1,z),(x+1,y+1,z+1),(x+1,y,z+1)]),
                      (3000+y+1,[(x,y+1,z),(x+1,y+1,z),(x+1,y+1,z+1),(x,y+1,z+1)])):
            dr.polygon([pr(p,ox,oy) for p in q], fill=lab)
    arr=np.array(img)
    if not arr.any(): return None
    ys,xs=np.nonzero(arr); cy,cx=ys.mean(),xs.mean()
    out=np.zeros((H,W),arr.dtype)
    oy2=int(round(H/2-cy)); ox2=int(round(W/2-cx))
    y0,y1=max(0,oy2),min(H,oy2+H); x0,x1=max(0,ox2),min(W,ox2+W)
    out[y0:y1,x0:x1]=arr[y0-oy2:y1-oy2, x0-ox2:x1-ox2]
    return out

def edges_of(lab):
    e=np.zeros(lab.shape,bool)
    e[:-1,:] |= lab[:-1,:]!=lab[1:,:]
    e[:,:-1] |= lab[:,:-1]!=lab[:,1:]
    return e

def obs_edges(mask, gray, thresh=0.06):
    gy,gx=np.gradient(ndimage.gaussian_filter(gray,1.0))
    mag=np.hypot(gx,gy)
    inner=ndimage.binary_erosion(mask,np.ones((3,3)))
    e=(mag>thresh)&inner
    e |= mask & ~ndimage.binary_erosion(mask,np.ones((3,3)))   # silhouette
    return e
