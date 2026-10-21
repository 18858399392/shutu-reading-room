from pathlib import Path
import json, html, textwrap, collections, re, hashlib, argparse
from PIL import Image, ImageDraw

BASE=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser()
parser.add_argument('--data-dir',default=str(BASE/'work'))
parser.add_argument('--out-dir',default=str(BASE/'outputs'/'一书三图'))
args=parser.parse_args()
DATA=Path(args.data_dir).resolve()
OUT=Path(args.out_dir).resolve()
E=lambda v:html.escape(str(v),quote=True)
categories=['文学故事','历史社会','心理关系','女性视角','成长方法','商业认知','科学探索']
content=[]
for name in ['content-a.json','content-b.json','content-c1.json','content-c2.json','content-c3.json']:
    content+=json.loads((DATA/name).read_text(encoding='utf-8-sig'))
inventory=json.loads((DATA/'inventory.json').read_text(encoding='utf-8-sig'))
lookup={b['id']:b for b in content}
assert len(lookup)==100
corrections_path=DATA/'content-corrections.json'
if corrections_path.exists():
    for id,correction in json.loads(corrections_path.read_text(encoding='utf-8-sig')).items():lookup[int(id)].update(correction)
supp=OUT/'assets/supplements';supp.mkdir(parents=True,exist_ok=True)

def lines(s,n):
    return textwrap.wrap(str(s),n,break_long_words=True,break_on_hyphens=False) or ['']

def text_svg(s,x,y,size=30,fill='#29243f',width=24,lineheight=None,weight='400'):
    lh=lineheight or size*1.7
    return ''.join(f'<text x="{x}" y="{y+i*lh}" fill="{fill}" font-size="{size}" font-weight="{weight}">{E(line)}</text>' for i,line in enumerate(lines(s,width)))

def make_card(b,mode):
    id=b['id']; filename=f'{id:02d}-{mode}.svg'
    title={'overview':'从这里读起','ideas':'三个阅读线索','questions':'把问题带进书里','reflections':'把问题带进书里'}[mode]
    s=f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1600" viewBox="0 0 1200 1600"><rect width="1200" height="1600" fill="{dict(overview="#ded8ee",ideas="#e6e1f0",questions="#e5edf0",reflections="#e2eaf1")[mode]}"/><rect x="48" y="48" width="1104" height="1504" rx="14" fill="#ffffff"/><path d="M96 118h96" stroke="#6554a4" stroke-width="6"/><g font-family="Microsoft YaHei, PingFang SC, sans-serif">'
    s+=text_svg('一书三图  /  原创导读',96,170,24,'#6554a4',35)
    s+=text_svg(b['title'],96,285,58,'#29243f',15,85,'600')
    title_rows=len(lines(b['title'],15)); y=285+title_rows*85+8
    s+=text_svg(b['author'],96,y,26,'#716c80',33,45)
    y+=len(lines(b['author'],33))*45+70
    s+=text_svg(title,96,y,34,'#6554a4',28,52,'600');y+=85
    if mode=='overview':
        s+=text_svg(b['tagline'],96,y,37,'#29243f',24,63,'500');y+=len(lines(b['tagline'],24))*63+45
        s+=text_svg(b['intro'],96,y,30,'#625c70',29,54)
    else:
        for i,idea in enumerate(b['ideas'][:3]):
            heading=idea.get('title','阅读线索')
            desc=idea.get('text','')
            if mode in ['questions','reflections']:
                heading=['回到书里的细节','换一个角度看','联系自己的生活'][i]
                desc=[f'作者如何展开“{idea.get("title", "这个问题")}”？选一个具体的人物、证据或情境，说明你读到的意思。',f'如果换一种立场或处境，你会怎样理解“{idea.get("title", "这一观点")}”？找出仍然需要追问的地方。',f'关于“{idea.get("title", "这个主题")}”，你的经历能补充什么？把认同与疑问记下，留待下一次翻阅。'][i]
            s+=f'<circle cx="111" cy="{y-10}" r="8" fill="#b3a4cf"/>'
            s+=text_svg(heading,158,y,32,'#29243f',27,52,'600');y+=63
            s+=text_svg(desc,158,y,27,'#625c70',31,47);y+=len(lines(desc,31))*47+62
    s+='<path d="M96 1443h1008" stroke="#dfdce9"/>'
    s+=text_svg('本站补充整理 · 非书中原文或引语',96,1490,21,'#8b819d',42)
    s+='</g></svg>'
    (supp/filename).write_text(s,encoding='utf-8')
    rev='?v='+hashlib.sha256(s.encode('utf-8')).hexdigest()[:12]
    return {'src':'assets/supplements/'+filename.replace('.svg','.webp')+rev,'thumb':'assets/supplements/'+filename.replace('.svg','-thumb.webp')+rev,'vector':'assets/supplements/'+filename,'label':title,'generated':True,'width':1200,'height':1600}

books=[];duplicates=[];supp_count=0
rank={'封面.png':0,'黑板.png':1,'三句话.png':2,'其他.png':3,'黑板2.png':4,'封面2.png':5,'封面3.png':6}
for asset in inventory['books']:
    b=dict(lookup[asset['id']]);b['originalTitle']=asset['title'];b['category']=b['category'] if b['category'] in categories else '文学故事'
    images=[];hashes=set()
    for im in sorted(asset['images'],key=lambda x:rank.get(x['name'],99)):
        if im['sha256'] in hashes:
            duplicates.append({'id':b['id'],'file':im['name'],'sha256':im['sha256']});continue
        hashes.add(im['sha256'])
        label={'封面.png':'封面印象','黑板.png':'黑板图解','三句话.png':'三句话读懂','其他.png':'延伸图解','黑板2.png':'黑板图解 · 二','封面2.png':'另一种封面','封面3.png':'另一种封面 · 三'}.get(im['name'],im['name'])
        rev='?v='+im['sha256'][:12]
        images.append({'src':im['webPath']+rev,'thumb':im['thumbPath']+rev,'label':label,'generated':False,'width':im['width'],'height':im['height'],'sourceName':im['name']})
    if b.get('archiveOriginals'):
        for im in images:im['label']='原素材对照 · '+im['label']
        images=[make_card(b,m) for m in ['overview','ideas','reflections']]+images
        supp_count+=3
    modes=['overview','ideas'] if len(images)==1 and images[0]['sourceName'].startswith('黑板') else ['ideas','questions']
    while len(images)<3:
        images.append(make_card(b,modes.pop(0)));supp_count+=1
    b['images']=images;books.append(b)
for id in range(68,101):
    b=dict(lookup[id]);b['images']=[make_card(b,m) for m in ['overview','ideas','reflections']];supp_count+=3;books.append(b)
books.sort(key=lambda b:b['id'])
(OUT/'data').mkdir(exist_ok=True)
(OUT/'data/books.json').write_text(json.dumps(books,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'books.js').write_text('window.BOOKS='+json.dumps(books,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')

bookmark='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M6 3h12v18l-6-4-6 4z"/></svg>'
cards=[]
for b in books:
    extra=len(b['images'])-3
    figs=[]
    for j,im in enumerate(b['images'][:3]):
        figs.append(f'<figure class="figure"><button class="image-open" data-book="{b["id"]}" data-view="{j}" aria-label="放大《{E(b["title"])}》的{E(im["label"])}"><img src="{im["thumb"]}" width="{im["width"]}" height="{im["height"]}" alt="{E(b["title"])} · {E(im["label"])}" loading="lazy" decoding="async"></button><figcaption><span>{E(im["label"])}</span>{"<small>原创补充</small>" if im["generated"] else ""}</figcaption></figure>')
    note=f'<p class="note">{E(b["correctionNote"])}</p>' if b.get('correctionNote') else ''
    sources=b.get('sources') or ([{'url':b.get('sourceUrl',''),'label':b.get('sourceLabel','资料来源')}] if b.get('sourceUrl') else [])
    sourcehtml=' · '.join(f'<a href="{E(x.get("url",""))}" target="_blank" rel="noopener noreferrer">{E(x.get("label","资料来源"))}</a>' for x in sources if x.get('url'))
    reference='<p>书目信息参考：'+sourcehtml+'</p>' if sourcehtml else ''
    hint='<p>核对提示：'+E(b.get('suggestedTitle',''))+'</p>' if b.get('suggestedTitle') else ''
    detail=f'<details class="meta-details"><summary>关于这本书</summary><p>简介与补充卡为本站原创整理，帮助选择与阅读。图中的归纳保留原样，阅读时可与原书对照。</p>{reference}{hint}</details>'
    extras=f'<div class="extras"><span>另有 {extra} 张图片</span><button data-book="{b["id"]}" data-view="3">查看其余图片 →</button></div>' if extra else ''
    cards.append(f'<article class="book" id="book-{b["id"]}" data-id="{b["id"]}"><div class="book-info"><div class="book-top"><div><span class="book-id">{b["id"]:02d}</span><span class="category">{E(b["category"])}</span></div><button class="save" data-id="{b["id"]}" aria-label="收藏《{E(b["title"])}》" aria-pressed="false">{bookmark}</button></div><h3>{E(b["title"])}</h3><p class="author">{E(b["author"])}</p><p class="tagline">{E(b["tagline"])}</p><p class="intro">{E(b["intro"])}</p>{note}{detail}</div><div class="book-gallery">{"".join(figs)}</div>{extras}</article>')
counts=collections.Counter(b['category'] for b in books)
filters='<button class="filter" data-category="全部" aria-pressed="true">全部书目 <span>100</span></button>'+''.join(f'<button class="filter" data-category="{c}" aria-pressed="false">{c} <span>{counts[c]}</span></button>' for c in categories)
page=f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#6554a4"><title>一书三图 · 私人阅读室</title><meta name="description" content="100本书，一本简介，三张图解。用文字与图片，把每本书慢慢读懂。"><meta property="og:title" content="一书三图 · 私人阅读室"><meta property="og:description" content="100本书的简介、图解与阅读笔记。"><link rel="canonical" href="https://shutu.kanglimin.com/"><link rel="icon" href="assets/icon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="assets/icon-192.png"><link rel="manifest" href="manifest.webmanifest"><link rel="stylesheet" href="style.css"><script src="books.js" defer></script><script src="app.js" defer></script></head><body>
<a class="skip" href="#library">跳到书目</a><header class="topbar"><a class="brand" href="./" aria-label="一书三图首页"><span class="logo" aria-hidden="true"><i></i><i></i><i></i></span><span><strong>一书三图</strong><small>A LITTLE ROOM FOR READING</small></span></a><nav class="top-actions" aria-label="页面导航"><a class="about-link" href="#about">关于阅读室</a><button id="install" hidden>添加到主屏幕</button><a href="https://kanglimin.com/" target="_blank" rel="noopener noreferrer">康利民的书房 ↗</a></nav></header>
<section class="hero" aria-labelledby="page-title"><div><p class="eyebrow">私人阅读室 · 图文藏书</p><h1 id="page-title">一本好书，<em>慢慢读懂。</em></h1><p>先读一段简介，再翻三张图。让每一次翻阅，都有新的发现。</p></div><div class="hero-aside"><div><strong>100</strong> 本书，七个阅读方向</div><div>文学 · 历史 · 心理 · 成长 · 科学</div><div>点开图片，放大看每一个细节。</div></div></section>
<section class="controls-wrap" aria-label="查找书籍"><div class="controls"><div class="control-row"><label class="search"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></svg><input id="search" type="search" placeholder="搜索书名、作者，或一个想了解的话题…" aria-label="搜索书名、作者或主题" autocomplete="off"></label><button class="filter-saved" id="filter-saved" aria-pressed="false">{bookmark}收藏 <span id="saved-count">0</span></button><label class="select-wrap" for="jump">书目索引 <select id="jump" aria-label="跳转到一本书"><option value="">跳转到一本书</option></select></label></div><div class="filters" aria-label="按类别筛选">{filters}</div></div></section>
<main class="library" id="library"><div class="library-heading"><h2 id="section-title">全部书目</h2><span aria-live="polite"><span id="result-count">100</span> 本 · 三图一览 <button id="reset-view" hidden>清除筛选 ↺</button></span></div>{''.join(cards)}<div class="empty" id="empty" hidden><h3>换个词，再找找。</h3><p>可以试试作者、书名，或清除当前分类与收藏筛选。</p><button id="empty-reset">查看全部书目</button></div></main>
<footer class="footer" id="about"><div><strong>一书三图 · 私人阅读室</strong><p>图片来自已有读书图文收藏；{supp_count} 张标有“原创补充”的导读卡用于补齐缺图。简介、线索和问题为本站整理，非书中原文；原图中的概括与书名疑点在对应书目中提示。此处是阅读索引，适合带着兴趣继续翻开原书。</p></div><div>本地版可直接打开 index.htm<br>收藏保存在当前浏览器<br><a href="https://kanglimin.com/" target="_blank" rel="noopener noreferrer">kanglimin.com ↗</a></div></footer>
<button class="back-top" id="back-top" aria-label="返回页面顶部">↑</button><div id="toast" class="toast" role="status" hidden></div>
<dialog class="viewer" id="viewer" aria-labelledby="viewer-title"><header class="viewer-head"><div><h2 id="viewer-title" class="viewer-title"></h2><div id="viewer-meta" class="viewer-meta"></div></div><button class="viewer-close" id="viewer-close" aria-label="关闭图片">×</button></header><div id="viewer-canvas" class="viewer-canvas"><img id="full-image" alt=""></div><footer class="viewer-bottom"><div class="viewer-nav"><button id="prev" aria-label="上一张图片">← 上一张</button><button id="next" aria-label="下一张图片">下一张 →</button></div><span class="viewer-help">← → 切换 · Esc 关闭 · 点击图片放大</span><div class="viewer-tools"><button id="zoom">放大细读</button><a id="image-original" href="#" download>保存图片</a></div></footer></dialog>
<noscript><div class="noscript">此浏览器关闭了 JavaScript。书目简介和三图仍可阅读；搜索、收藏和放大功能需要允许 JavaScript。</div></noscript></body></html>'''
(OUT/'index.html').write_text(page,encoding='utf-8');(OUT/'index.htm').write_text(page,encoding='utf-8')

for size in [192,512]:
    im=Image.new('RGB',(size,size),'#6554a4');d=ImageDraw.Draw(im)
    for box,fill in [((.25,.25,.61,.74),'#8c7aba'),((.34,.22,.70,.71),'#c8bde1'),((.43,.29,.79,.78),'#f5f5fa')]:
        d.rounded_rectangle(tuple(int(v*size) for v in box),radius=int(.018*size),fill=fill,outline='white',width=max(1,int(.014*size)))
    for y in [.44,.51,.58]:d.line([(int(.50*size),int(y*size)),(int(.71*size),int(y*size))],fill='#6554a4',width=max(2,int(.014*size)))
    im.save(OUT/f'assets/icon-{size}.png')
report={'books':len(books),'sourceImages':sum(len(b['images']) for b in inventory['books']),'uniqueSourceImages':sum(sum(not i['generated'] for i in b['images']) for b in books),'generatedCards':supp_count,'duplicatesExcludedFromDisplay':duplicates,'primaryImages':sum(len(b['images'][:3]) for b in books),'allDisplayImages':sum(len(b['images']) for b in books),'extraImages':sum(len(b['images'])-3 for b in books),'correctionNotes':[{'id':b['id'],'title':b['title'],'note':b['correctionNote']} for b in books if b.get('correctionNote')]}
(DATA/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
