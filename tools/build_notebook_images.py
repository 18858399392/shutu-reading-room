from __future__ import annotations
import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--repo-dir', default=str(SCRIPT_DIR.parent if SCRIPT_DIR.name == 'tools' else SCRIPT_DIR/'shutu-repo'))
parser.add_argument('--work-dir', default=None)
args = parser.parse_args()
REPO = Path(args.repo_dir).resolve()
BASE = Path(args.work_dir).resolve() if args.work_dir else SCRIPT_DIR if SCRIPT_DIR.name != 'tools' else REPO/'.notebook-build'
BASE.mkdir(parents=True, exist_ok=True)
SITE = REPO / 'site'
TARGET = SITE / 'assets' / 'notebook'
TARGET.mkdir(parents=True, exist_ok=True)
BOOKS_INPUT = REPO/'content'/'books-base.json'
if not BOOKS_INPUT.exists():
    BOOKS_INPUT = SITE/'data'/'books.json'
books = json.loads(BOOKS_INPUT.read_text(encoding='utf-8'))
inventory = json.loads((REPO / 'content' / 'inventory.json').read_text(encoding='utf-8'))
originals = {b['id']: b for b in inventory['books']}
CORRECTED = {16, 22, 37}
NEW_COVER = {15, 16, 22, 37, 50, 54, 57} | set(range(68, 101))
# Checked by visual content, not by filename. These originals contain exactly
# three explanatory content groups although many were named "cover.png".
THREE_FROM_COVER = {1,6,8,9,12,19,20,23,24,25,27,29,32,33,35,39,41,48,49,50,51,52,53,54,60,64,65,66,67}
THREE_SPECIAL = {21:'其他.png', 56:'黑板2.png'}
FONTS = {
    'body': ('Microsoft YaHei', 'C:/Windows/Fonts/msyh.ttc'),
    'display': ('KaiTi', 'C:/Windows/Fonts/simkai.ttf'),
    'chalk': ('KaiTi', 'C:/Windows/Fonts/simkai.ttf')
}
FONT_CACHE = {}

def measure(s, size, role='body'):
    key = (size, role)
    if key not in FONT_CACHE:
        FONT_CACHE[key] = ImageFont.truetype(FONTS[role][1], size)
    return FONT_CACHE[key].getlength(s)

def wrap(s, width, size, role='body'):
    result, current = [], ''
    for ch in str(s):
        if ch == '\n':
            result.append(current)
            current = ''
            continue
        if current and measure(current + ch, size, role) > width:
            closing = '，。！？；：、）》】〉」』’”％…·'
            opening = '（《【〈「『“‘'
            if ch in closing:
                carry = current[-1]
                current = current[:-1]
                while current and (carry[0] in closing or current[-1] in opening):
                    carry = current[-1]+carry
                    current = current[:-1]
                assert current, (s, 'cannot wrap punctuation')
                result.append(current)
                current = carry+ch
            elif current[-1] in opening:
                opener = current[-1]
                result.append(current[:-1])
                current = opener+ch
            else:
                result.append(current)
                current = ch
        else:
            current += ch
    if current:
        result.append(current)
    assert not any(line and line[0] in '，。！？；：、）》】〉」』’”％…·' for line in result), (s,result)
    assert not any(line and line[-1] in '（《【〈「『“‘' for line in result[:-1]), (s,result)
    return result or ['']

def line_text(content, x, y, size, fill, role='body', weight='400', anchor='start', zone='body', bounds=(65, 1135, 80, 1460)):
    left, right, top, bottom = bounds
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-family="{FONTS[role][0]}, Microsoft YaHei, sans-serif" font-weight="{weight}" text-anchor="{anchor}" data-zone="{zone}" data-left="{left}" data-right="{right}" data-top="{top}" data-bottom="{bottom}">{html.escape(str(content))}</text>'

def block(content, x, y, size, fill, width, lineheight, role='body', weight='400', zone='body', bounds=(65, 1135, 80, 1460)):
    ls = wrap(content, width, size, role)
    return ''.join(line_text(t, x, y+i*lineheight, size, fill, role, weight, zone=zone, bounds=bounds) for i,t in enumerate(ls)), len(ls)

def sentence(text):
    # Combine the two short, original explanatory sentences into one statement.
    # The semantic contents are unchanged, and the card does not turn into a prompt.
    t = re.sub(r'[。；;]+$', '', text.strip())
    t = t.replace('。', '；')
    if '？' in t or '?' in t:
        # Retain the explanatory statement after a rhetorical question.
        t = re.split(r'[？?]', t)[-1].strip()
    assert t and '？' not in t and '?' not in t, t
    return t + '。'

PALETTES = {
    '文学故事': ('#243e45', '#e7d8b5', '#8fb7b4'),
    '历史社会': ('#293e62', '#ecdec3', '#95b4d3'),
    '心理关系': ('#244d43', '#ede2bf', '#a2c8af'),
    '女性视角': ('#603f50', '#f2dfbb', '#d3acb5'),
    '成长方法': ('#4b4c69', '#eeebd0', '#c4c2de'),
    '商业认知': ('#303d50', '#eddaaa', '#b4c2d3'),
    '科学探索': ('#163e5b', '#dce7ed', '#8fbfd2')
}

def make_cover(b):
    bg, ink, soft = PALETTES[b['category']]
    out = [f'<rect width="1200" height="1600" fill="{bg}"/>', f'<path d="M74 70H1126V1530H74Z" fill="none" stroke="{soft}" stroke-opacity=".38" stroke-width="2"/>', f'<path d="M103 70V1530" stroke="{soft}" stroke-opacity=".18" stroke-width="2"/>']
    out.append(line_text(b['category'], 155, 190, 30, soft, zone='cover-category', bounds=(120,1100,120,240)))
    out.append(f'<path d="M155 250h150" stroke="{ink}" stroke-width="4"/>')
    units = measure(b['title'],100,'display')/100
    title_size = 190 if units <= 5.1 else 168 if units <= 9.1 else 148
    total_width = measure(b['title'], title_size, 'display')
    max_title_width = 960
    desired_rows = max(1, __import__('math').ceil(total_width/max_title_width))
    balanced_width = min(max_title_width, total_width/desired_rows+title_size*.20)
    title_lines = wrap(b['title'], balanced_width, title_size, 'display')
    while len(title_lines) > desired_rows and balanced_width < max_title_width:
        balanced_width = min(max_title_width, balanced_width+6)
        title_lines = wrap(b['title'], balanced_width, title_size, 'display')
    while len(title_lines) > 4 and title_size > 84:
        title_size -= 4
        title_lines = wrap(b['title'], 900, title_size, 'display')
    lh = title_size * 1.48
    top = 750 - (len(title_lines)-1)*lh/2
    for i, text in enumerate(title_lines):
        out.append(line_text(text, 600, top+i*lh, title_size, ink, 'display', anchor='middle', zone='cover-title', bounds=(115,1100,300,1150)))
    out.append(f'<path d="M155 1220h890" stroke="{soft}" stroke-opacity=".3" stroke-width="2"/>')
    author, count = block(b['author'], 155, 1322, 32, soft, 890, 56, zone='cover-author', bounds=(120,1110,1250,1445))
    assert count <= 3, (b['id'], 'author overflow', count)
    out.append(author)
    out.append(line_text('一书三图 · 原创阅读封面', 155, 1482, 23, soft, zone='footer', bounds=(120,1110,1440,1520)))
    return ''.join(out)

def make_three_lines(b):
    out = ['<rect width="1200" height="1600" fill="#f8f7f0"/>', '<path d="M75 72H1125V1528H75Z" fill="none" stroke="#d6ded4" stroke-width="2"/>', '<path d="M152 355V1435" stroke="#ded7bf" stroke-width="2"/>']
    out.append(line_text('三句话解读', 90, 140, 29, '#567561', zone='section', bounds=(65,1135,90,170)))
    title, count = block(b['title'], 90, 235, 58, '#263f36', 1010, 84, role='display', weight='600', zone='title', bounds=(65,1135,170,360))
    out.append(title)
    assert count <= 2, (b['id'], 'three title count', count)
    for i, idea in enumerate(b['ideas']):
        top = 405+i*350
        out.append(f'<circle cx="127" cy="{top+12}" r="35" fill="#e7ebe0"/>')
        out.append(line_text(f'{i+1:02d}', 127, top+22, 25, '#567561', anchor='middle', zone=f'number-{i+1}', bounds=(85,170,top-30,top+55)))
        if b['id'] == 22:
            desc = [
                '日常生活中对权威、成就和照护责任的不同期待，让性别规则不断被重复。',
                '从小接受的不同教育，会限制男孩和女孩对情绪、目标与责任的想象。',
                '改变性别不平等，需要所有人在工作、家庭和交往中共同调整习惯。'
            ][i]
        else:
            desc = sentence(idea['text'])
        text, count = block(desc, 196, top+25, 42, '#34483e', 890, 70, zone=f'body-{i+1}', bounds=(180,1110,top-22,top+292))
        assert count <= 4, (b['id'], 'three body count', i, count)
        out.append(text)
        if i < 2:
            out.append(f'<path d="M196 {top+281}H1090" stroke="#e0e3d9" stroke-width="2"/>')
    out.append(line_text('原创解读 · 非原书逐字摘录', 90, 1498, 24, '#6f7d6d', zone='footer', bounds=(65,1135,1450,1530)))
    return ''.join(out)

def make_blackboard(b):
    out = ['<rect width="1200" height="1600" fill="#6b573d"/>', '<rect x="31" y="31" width="1138" height="1538" rx="5" fill="#153b31" stroke="#a78e63" stroke-width="4"/>', '<rect x="49" y="49" width="1102" height="1502" fill="none" stroke="#cee0c4" stroke-opacity=".13" stroke-width="2"/>']
    for i in range(28):
        x = 75+(i*137)%1030
        y = 75+(i*83)%1420
        out.append(f'<path d="M{x} {y}l{45+(i*11)%90} {i%3-1}" stroke="#e4e9d5" stroke-opacity=".035" stroke-width="2"/>')
    title, count = block(b['title'], 90, 158, 59, '#f0ead3', 1010, 82, 'chalk', weight='600', zone='title', bounds=(65,1135,85,310))
    assert count <= 2, (b['id'], 'board title count', count)
    out.append(title)
    out.append(line_text('黑板图解 / 三条知识分支', 92, 158+count*82+18, 27, '#cbd0ac', 'chalk', zone='section', bounds=(65,1135,230,390)))
    out.append('<path d="M148 412V1398" fill="none" stroke="#d5c97c" stroke-width="4" stroke-linecap="round" opacity=".8"/>')
    colors = ['#edcf76', '#a9d6bb', '#d5c0e4']
    for i, idea in enumerate(b['ideas']):
        top = 470+i*340
        c = colors[i]
        out.append(f'<circle cx="148" cy="{top-13}" r="13" fill="{c}"/><path d="M161 {top-13}H198" stroke="{c}" stroke-width="4" stroke-linecap="round"/>')
        title, ntitle = block(idea['title'], 220, top, 45, c, 870, 63, 'chalk', weight='600', zone=f'branch-title-{i+1}', bounds=(205,1110,top-55,top+75))
        assert ntitle <= 1, (b['id'], 'board branch title wraps', i)
        out.append(title)
        out.append(f'<path d="M220 {top+22}Q600 {top+26}1080 {top+21}" stroke="{c}" stroke-opacity=".4" stroke-width="2" fill="none"/>')
        desc, ndesc = block(idea['text'], 220, top+94, 35, '#ecebd9', 865, 59, 'chalk', zone=f'branch-body-{i+1}', bounds=(205,1110,top+50,top+285))
        assert ndesc <= 4, (b['id'], 'board desc count', i, ndesc)
        out.append(desc)
    out.append(line_text('原创图解 · 依据简介与阅读线索整理', 90, 1504, 25, '#b9cbb6', 'chalk', zone='footer', bounds=(65,1135,1465,1535)))
    return ''.join(out)

MAKERS = {'cover':make_cover, 'three-lines':make_three_lines, 'blackboard':make_blackboard}
LABELS = {'cover':'大标题封面', 'three-lines':'三句话解读', 'blackboard':'黑板图解'}
generated_sources = []

def generated_item(b, kind):
    name = f'{b["id"]:02d}-{kind}'
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1600" viewBox="0 0 1200 1600"><title>{html.escape(b["title"])} · {LABELS[kind]}</title>'+MAKERS[kind](b)+'</svg>'
    (TARGET / (name+'.svg')).write_text(svg, encoding='utf-8')
    digest = hashlib.sha256(svg.encode('utf-8')).hexdigest()[:12]
    generated_sources.append({'id':b['id'],'kind':kind,'file':name+'.svg'})
    return {'src':f'assets/notebook/{name}.webp?v={digest}', 'thumb':f'assets/notebook/{name}-thumb.webp?v={digest}', 'label':LABELS[kind], 'generated':True, 'width':1200, 'height':1600}

def existing_item(bid, original, kind):
    path = SITE / original['webPath']
    with Image.open(path) as im:
        size = im.size
    digest = original['sha256'][:12]
    return {'src':original['webPath']+'?v='+digest, 'thumb':original['thumbPath']+'?v='+digest, 'label':LABELS[kind], 'generated':False, 'width':size[0], 'height':size[1]}

def normalized(item, label=None):
    return {k:(label if k=='label' and label else item[k]) for k in ('src','thumb','label','generated','width','height')}

plan = []
statistics = {'cover':{'reused':0,'new':0},'three-lines':{'reused':0,'new':0},'blackboard':{'reused':0,'new':0}}
for b in sorted(books, key=lambda x:x['id']):
    bid = b['id']
    original = originals.get(bid, {'images':[]})['images'] if bid not in CORRECTED else []
    by_name = {im['name']:im for im in original}
    selected = {}
    for kind in ('cover','three-lines','blackboard'):
        original_item = None
        if kind == 'cover' and bid not in NEW_COVER:
            if bid in (1,6,9):
                name = '封面3.png'
            elif bid == 43:
                name = '封面.png'
            else:
                name = '封面2.png' if '封面2.png' in by_name else '封面.png'
            if name != '封面.png' and '封面.png' in by_name and by_name[name]['sha256'] == by_name['封面.png']['sha256']:
                name = '封面.png'
            original_item = by_name.get(name)
            assert original_item is not None, (bid, kind, name)
        elif kind == 'three-lines':
            original_item = by_name.get('三句话.png')
            if original_item is None and bid in THREE_FROM_COVER:
                original_item = by_name.get('封面.png')
            if original_item is None and bid in THREE_SPECIAL:
                original_item = by_name.get(THREE_SPECIAL[bid])
        elif kind == 'blackboard':
            original_item = by_name.get('黑板.png')
        if original_item:
            selected[kind] = existing_item(bid, original_item, kind)
            statistics[kind]['reused'] += 1
        else:
            selected[kind] = generated_item(b, kind)
            statistics[kind]['new'] += 1
    used = {urlsplit(im['src']).path for im in selected.values()}
    extras, seen = [], set(used)
    for im in b['images']:
        p = urlsplit(im['src']).path
        if p in seen:
            continue
        seen.add(p)
        label = im['label']
        if im['generated']:
            label = '旧版原创导读 · '+label
        elif bid in CORRECTED and not label.startswith('原素材对照'):
            label = '原素材对照 · '+label
        extras.append(normalized(im, label))
    # The chosen large-title original may previously have been a hidden image;
    # keeping all other existing records preserves every independent old image.
    plan.append({'id':bid,'cover':selected['cover'],'threeLines':selected['three-lines'],'blackboard':selected['blackboard'],'extras':extras})

assert len(plan) == 100
assert sum(v['new'] for v in statistics.values()) == len(generated_sources)
report = {'statistics':statistics, 'generated_count':len(generated_sources), 'reused_count':300-len(generated_sources), 'generated_sources':generated_sources, 'extras_count':sum(len(x['extras']) for x in plan), 'input_books_sha256':hashlib.sha256(BOOKS_INPUT.read_bytes()).hexdigest(), 'cover_selection_notes':{'1':'封面3：标题比信息图封面更明确','6':'封面3：双行大标题，文字最少','9':'封面3：最大标题版本','43':'封面.png为少文字封面，封面2有四点信息，未当三句话复用','50':'唯一旧封面为三句信息图，新制标题封面，旧图作为三句话','54':'唯一旧封面为三句信息图，新制标题封面，旧图作为三句话'}, 'three_sentence_originals_visually_verified':sorted(THREE_FROM_COVER | set(THREE_SPECIAL)), 'source_png_directory_read_only':True}
(BASE/'notebook-image-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
(REPO/'content'/'notebook-images.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
(BASE/'notebook-image-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'statistics':statistics,'new':len(generated_sources),'reused':300-len(generated_sources),'extras':report['extras_count']},ensure_ascii=False))
