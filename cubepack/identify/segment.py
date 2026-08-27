"""Step 1 - segment the 13 pieces out of the photograph by colour.

Writes pieces.pkl: for each piece a binary silhouette, the value channel of the
crop, and its position in the photo.
"""
import os
from PIL import Image
import numpy as np
from scipy import ndimage
import pickle

SRC=os.environ.get('PUZZLE_PHOTO','photo.jpg')  # the photograph of the 13 pieces
im=Image.open(SRC)
im2=im.resize((im.size[0]//2, im.size[1]//2), Image.LANCZOS)
a=np.asarray(im2).astype(float)/255.0
r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
mx=a.max(2); mn=a.min(2); v=mx; s=np.where(mx>0,(mx-mn)/np.maximum(mx,1e-6),0)
d=mx-mn+1e-9
hue=np.zeros_like(mx)
c=(mx==r); hue[c]=((g-b)[c]/d[c])%6
c=(mx==g)&(mx!=r); hue[c]=((b-r)[c]/d[c])+2
c=(mx==b)&(mx!=r)&(mx!=g); hue[c]=((r-g)[c]/d[c])+4
hue*=60
masks={
 'red':    (((hue<24)|(hue>335))&(s>0.45)&(v>0.33)),
 'yellow': ((hue>=34)&(hue<74)&(s>0.38)&(v>0.35)),
 'green':  ((hue>=90)&(hue<178)&(s>0.25)&(v>0.15)),
 'blue':   ((hue>=182)&(hue<252)&(s>0.30)&(v>0.15)),
}
pieces=[]
for col,m in masks.items():
    m=ndimage.binary_opening(m, np.ones((7,7)))
    m=ndimage.binary_closing(m, np.ones((15,15)))
    m=ndimage.binary_fill_holes(m)
    lab,n=ndimage.label(m)
    for i in range(1,n+1):
        sel=(lab==i)
        if sel.sum()<12000: continue
        ys,xs=np.nonzero(sel)
        gray=mx  # value channel: best face-shading contrast on saturated plastic
        pieces.append(dict(color=col, mask=sel[ys.min():ys.max()+1, xs.min():xs.max()+1].copy(),
                           gray=gray[ys.min():ys.max()+1, xs.min():xs.max()+1].copy(),
                           x0=int(xs.min()), y0=int(ys.min()), area=int(sel.sum()),
                           cx=float(xs.mean()), cy=float(ys.mean())))
pieces.sort(key=lambda p:(p['cy'],p['cx']))
for i,p in enumerate(pieces,1):
    p['id']=i
    h,w=p['mask'].shape
    print(f"{i:2d} {p['color']:6} area={p['area']:6d} bbox={w}x{h} at ({p['x0']},{p['y0']}) centre=({p['cx']:.0f},{p['cy']:.0f})")
pickle.dump(pieces, open('pieces.pkl','wb'))
# save a contact sheet of masks
sheet=Image.new('RGB',(1600,900),(255,255,255))
from PIL import ImageDraw
dr=ImageDraw.Draw(sheet)
for i,p in enumerate(pieces):
    m=(p['mask']*255).astype(np.uint8)
    img=Image.fromarray(m).convert('RGB')
    img.thumbnail((280,280))
    sheet.paste(img,(i%5*320+10,(i//5)*300+10))
    dr.text((i%5*320+10,(i//5)*300+290), f"{i+1} {p['color']}", fill=(0,0,0))
sheet.save('masks_sheet.png')
