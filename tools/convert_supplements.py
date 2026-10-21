import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

root = Path(sys.argv[1]).resolve()
scratch = Path(sys.argv[2]).resolve()
items=[]
issues=[]
modes=sys.argv[3].split(',') if len(sys.argv)>3 and sys.argv[3] else []
sources=sorted(root.glob('*.svg'))
for source in sources:
    if modes and not any(source.stem.endswith('-'+mode) for mode in modes):continue
    name=source.stem
    png=scratch/(name+'.png')
    if not png.is_file():
        raise RuntimeError(f'Missing screenshot: {png}')
    xml=ET.parse(source).getroot()
    for el in xml.iter():
        if el.tag.rsplit('}',1)[-1]!='text':continue
        y=float(el.attrib.get('y','0'))
        text=''.join(el.itertext())
        footer=abs(y-1490)<0.1 and any(t in text for t in ('本站','原创','补充','整理','非书中','导读'))
        if y>=1430 and not footer:
            issues.append({'file':source.name,'y':y,'text':text})
    with Image.open(png) as original:
        assert original.size==(1200,1600),(source.name,original.size)
        rgb=original.convert('RGB')
        full=root/(name+'.webp')
        thumb=root/(name+'-thumb.webp')
        rgb.save(full,format='WEBP',quality=90,method=6)
        preview=rgb.copy()
        preview.thumbnail((420,560),Image.Resampling.LANCZOS)
        preview.save(thumb,format='WEBP',quality=90,method=6)
    items.append({'file':source.name,'fullBytes':full.stat().st_size,'thumbBytes':thumb.stat().st_size})
totals={'fullBytes':0,'thumbBytes':0}
for source in sources:
    name=source.stem
    full=root/(name+'.webp')
    thumb=root/(name+'-thumb.webp')
    for target,size in ((full,(1200,1600)),(thumb,(420,560))):
        with Image.open(target) as check:
            check.load()
            assert check.size==size,(target.name,check.size)
            assert check.format=='WEBP',target.name
    totals['fullBytes']+=full.stat().st_size
    totals['thumbBytes']+=thumb.stat().st_size
    xml=ET.parse(source).getroot()
    for el in xml.iter():
        if el.tag.rsplit('}',1)[-1]!='text':continue
        y=float(el.attrib.get('y','0'))
        text=''.join(el.itertext())
        footer=abs(y-1490)<0.1 and any(t in text for t in ('本站','原创','补充','整理','非书中','导读'))
        if y>=1430 and not footer:
            issue={'file':source.name,'y':y,'text':text}
            if issue not in issues:issues.append(issue)
print(json.dumps({'count':len(sources),'convertedThisRun':len(items),'verifiedDecoded':len(sources)*2,'xmlTextIssues':issues,**totals},ensure_ascii=False))
