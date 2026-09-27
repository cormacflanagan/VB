import json,os,re,html
SP=os.path.dirname(os.path.abspath(__file__))
def txt(x): return ' '.join(html.unescape(re.sub(r'<[^>]+>',' ',x)).split())
rows=[]
for fn in sorted(os.listdir(os.path.join(SP,'ntdp'))):
    label=fn[:-5].replace('_',' ')
    s=open(os.path.join(SP,'ntdp',fn),encoding='utf8',errors='replace').read()
    # headings and tables in document order
    marks=[(m.start(),'h',txt(m.group(1))) for m in re.finditer(r'<h2[^>]*class="[^"]*white[^"]*"[^>]*>(.*?)</h2>',s,re.S)]
    marks+=[(m.start(),'t',m.group(0)) for m in re.finditer(r'<table[\s\S]*?</table>',s)]
    marks.sort()
    div=None; per={}
    for _,kind,val in marks:
        if kind=='h': div=val; continue
        trs=re.findall(r'<tr[\s\S]*?</tr>',val)
        hdr=None
        for tr in trs:
            cells=[txt(c) for c in re.findall(r'<t[dh][^>]*>([\s\S]*?)</t[dh]>',tr)]
            if not cells or not any(cells): continue
            up=[c.upper() for c in cells]
            if 'FIRST' in up and 'LAST' in up:
                hdr={c.upper():i for i,c in enumerate(cells)}; continue
            if hdr is None: continue
            fi,li=hdr.get('FIRST',0),hdr.get('LAST',1); ri=hdr.get('REGION')
            if max(fi,li)>=len(cells): continue
            f,l=cells[fi],cells[li]
            if not f or not l: continue
            rows.append({"series":label,"division":div,"first":f,"last":l,
                         "region":cells[ri] if ri is not None and ri<len(cells) else None})
            per[div]=per.get(div,0)+1
    print(f"{label:13s} " + "  ".join(f"{k}:{v}" for k,v in per.items()))
json.dump(rows,open(os.path.join(SP,'ntdp_rows.json'),'w'),indent=1)
g=[r for r in rows if not re.match(r"(boys|men)",(r['division'] or ''),re.I)]
print(f"\ntotal {len(rows)}; non-boys {len(g)}; unique non-boys names {len({(r['first'],r['last']) for r in g})}")
