import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
"""Step 5 - photo next to shaded renders of the best-matching shapes, for eyeballing."""
import pickle, json, sys, math
import numpy as np
import os
from PIL import Image, ImageDraw
import match as I

pieces=pickle.load(open('pieces.pkl','rb'))
SRC=os.environ.get('PUZZLE_PHOTO','photo.jpg')  # the photograph of the 13 pieces
photo=Image.open(SRC).resize((5712//2,4284//2), Image.LANCZOS)
GREY={0:(255,255,255)}
def shade_rgb(lab):
    rgb=np.full(lab.shape+(3,),255,np.uint8)
    cls=lab//1000
    rgb[cls==1]=(245,245,245); rgb[cls==2]=(158,158,158); rgb[cls==3]=(88,88,88)
    # thin outline on creases
    e=np.zeros(lab.shape,bool)
    e[:-1,:]|=lab[:-1,:]!=lab[1:,:]; e[:,:-1]|=lab[:,:-1]!=lab[:,1:]
    rgb[e&(lab>0)]=(20,20,20)
    return rgb

def sheet(idx, names=None, ncand=8, out=None):
    p=pieces[idx-1]
    d=json.load(open(f'cand_{idx:02d}.json'))
    cands=sorted(d['cands'].items(), key=lambda kv:-kv[1]['score'])
    if names: cands=[(n,d['cands'][n]) for n in names]
    cands=cands[:ncand]
    pad=18
    crop=photo.crop((p['x0']-pad,p['y0']-pad,p['x0']+p['mask'].shape[1]+pad,p['y0']+p['mask'].shape[0]+pad))
    crop=crop.resize((300,int(300*crop.size[1]/crop.size[0])))
    panels=[(f"piece {idx} ({p['color']})",crop)]
    for name,c in cands:
        lab=I.render(name,c['ori'],c['alpha'],c['phi'],c['roll'],c['s'],tuple(c['shift']))
        img=Image.fromarray(shade_rgb(lab)).resize((260,260),Image.NEAREST)
        panels.append((f"{name} n={c['n']} {c['score']:.3f}/{c['iou']:.2f}",img))
    cols=min(5,len(panels)); rows=(len(panels)+cols-1)//cols
    W,H=cols*310+20, rows*330+20
    sh=Image.new('RGB',(W,H),(255,255,255)); dr=ImageDraw.Draw(sh)
    for i,(tag,img) in enumerate(panels):
        x=(i%cols)*310+15; y=(i//cols)*330+15
        sh.paste(img,(x,y)); dr.text((x,y+300),tag,fill=(0,0,0))
    sh.save(out or f'sheet_{idx:02d}.png')
    return [n for n,_ in cands]

if __name__=='__main__':
    idx=int(sys.argv[1]); names=sys.argv[2:] or None
    print(sheet(idx, names))
