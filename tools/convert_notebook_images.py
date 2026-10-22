import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image

SCRIPT_DIR=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--repo-dir',default=str(SCRIPT_DIR.parent if SCRIPT_DIR.name=='tools' else SCRIPT_DIR/'shutu-repo'))
parser.add_argument('--work-dir',default=None)
args=parser.parse_args()
REPO=Path(args.repo_dir).resolve()
BASE=Path(args.work_dir).resolve() if args.work_dir else SCRIPT_DIR if SCRIPT_DIR.name!='tools' else REPO/'.notebook-build'
SITE=REPO/'site'
TARGET=SITE/'assets'/'notebook'
SCRATCH=BASE/'notebook-render'
REPORT=BASE/'notebook-image-report.json'
report=json.loads(REPORT.read_text(encoding='utf-8'))
plan=json.loads((BASE/'notebook-image-plan.json').read_text(encoding='utf-8'))

def convert(item):
    stem=Path(item['file']).stem
    source=SCRATCH/(stem+'.png')
    full=TARGET/(stem+'.webp')
    thumb=TARGET/(stem+'-thumb.webp')
    with Image.open(source) as im:
        im.load()
        assert im.size==(1200,1600)
        rgb=im.convert('RGB')
        rgb.save(full,format='WEBP',quality=91,method=4)
        rgb.resize((420,560),Image.Resampling.LANCZOS).save(thumb,format='WEBP',quality=91,method=4)
    for p,size in ((full,(1200,1600)),(thumb,(420,560))):
        with Image.open(p) as im:
            im.load()
            assert im.size==size and im.format=='WEBP',p
    return {'file':item['file'],'fullBytes':full.stat().st_size,'thumbBytes':thumb.stat().st_size,'fullSha256':hashlib.sha256(full.read_bytes()).hexdigest()}

with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    items=list(pool.map(convert,report['generated_sources']))

path_checks=[]
for b in plan:
    for kind in ('cover','threeLines','blackboard'):
        im=b[kind]
        for field in ('src','thumb'):
            p=SITE/urlsplit(im[field]).path
            assert p.resolve().is_relative_to(SITE.resolve()) and p.is_file(),(b['id'],kind,field,p)
            with Image.open(p) as loaded:
                loaded.load()
                expected=(im['width'],im['height']) if field=='src' else (420,560) if im['generated'] else None
                if expected:assert loaded.size==expected,(p,loaded.size,expected)
        path_checks.append({'id':b['id'],'kind':kind,'label':im['label'],'generated':im['generated']})
    for im in b['extras']:
        assert (SITE/urlsplit(im['src']).path).is_file()
        assert (SITE/urlsplit(im['thumb']).path).is_file()
report['conversion']={'generated_full_and_thumb_decoded':len(items)*2,'primary_full_and_thumb_decoded':len(path_checks)*2,'all_primary_300_semantics_and_paths_verified':len(path_checks)==300,'fullBytes':sum(x['fullBytes'] for x in items),'thumbBytes':sum(x['thumbBytes'] for x in items),'items':items}
report['complete']=True
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'generated':len(items),'primary':len(path_checks),'text_bbox_issues':len(report['text_bbox_checks']['issues']),'fullBytes':report['conversion']['fullBytes'],'thumbBytes':report['conversion']['thumbBytes']},ensure_ascii=False))
