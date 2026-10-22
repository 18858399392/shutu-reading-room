"""Rebuild the notebook site from committed content and UI templates.

Image generation is separate: tools/build_notebook_images.py and the renderer.
The original v1 generator is retained as build_legacy_site.py for reference.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser()
    root = Path(__file__).resolve().parent.parent
    parser.add_argument('--data-dir', type=Path, default=root / 'content')
    parser.add_argument('--out-dir', type=Path, default=root / 'site')
    args = parser.parse_args()
    data, out = args.data_dir, args.out_dir
    books = read(data / 'books-base.json')
    ranks = {x['id']: x for x in read(data / 'notebook-ranking.json')}
    images = {x['id']: x for x in read(data / 'notebook-images.json')}
    method = read(data / 'notebook-ranking-method.json')
    expected = set(range(1, 101))
    assert {x['id'] for x in books} == set(ranks) == set(images) == expected
    assert {x['rank'] for x in ranks.values()} == expected
    for rank in ranks.values():
        assert all(0 <= rank[key] <= 5 and rank[key] * 2 == int(rank[key] * 2) for key in ('impact', 'popularity', 'reach'))
    order = sorted(ranks.values(), key=lambda rank: (-round(rank['impact'] * 2) * 50 - round(rank['popularity'] * 2) * 35 - round(rank['reach'] * 2) * 15, -rank['impact'], -rank['popularity'], -rank['reach'], rank['id']))
    assert [rank['rank'] for rank in order] == list(range(1, 101)), 'Ranking disagrees with stated weighting and tie-break'
    generated = 0
    for book in books:
        rank, plan = ranks[book['id']], images[book['id']]
        book.update(rank=rank['rank'], rankReason=rank['reason'], ranking={k: rank[k] for k in ('impact', 'popularity', 'reach')})
        book['images'] = [dict(plan[key]) for key in ('cover', 'threeLines', 'blackboard')]
        book['extras'] = [dict(image) for image in plan['extras']]
        assert len(book['images']) == 3
        generated += sum(image['generated'] for image in book['images'])
        for image in book['images'] + book['extras']:
            for field in ('src', 'thumb'):
                relative = image[field].split('?')[0]
                file = out / relative
                assert file.is_file(), str(file)
                fingerprint = hashlib.sha256(file.read_bytes()).hexdigest()[:12]
                image[field] = relative + '?v=' + fingerprint
    books.sort(key=lambda book: book['rank'])
    write(out / 'data/books.json', books)
    write(out / 'data/ranking-method.json', method)
    (out / 'books.js').write_text('window.BOOKS=' + json.dumps(books, ensure_ascii=False, separators=(',', ':')) + ';\nwindow.RANKING_METHOD=' + json.dumps(method, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8', newline='\n')
    for name in ('index.html', 'style.css', 'app.js'):
        source = (root / 'tools/templates' / name).read_text(encoding='utf-8')
        (out / name).write_text(source, encoding='utf-8', newline='\n')
    html = (out / 'index.html').read_text(encoding='utf-8')
    versioned_assets = []
    for name in ('style.css', 'app.js', 'books.js'):
        fingerprint = hashlib.sha256((out / name).read_bytes()).hexdigest()[:12]
        versioned = name + '?v=' + fingerprint
        html = html.replace('"' + name + '"', '"' + versioned + '"')
        versioned_assets.append('./' + versioned)
    (out / 'index.html').write_text(html, encoding='utf-8', newline='\n')
    shutil.copyfile(out / 'index.html', out / 'index.htm')
    manifest = read(out / 'manifest.webmanifest')
    manifest.update(name='一书三图 · 翻页阅读本', description='100本好书，大封面、三句话、黑板图解。按综合阅读榜翻阅，从目录直达每一本。', background_color='#f3f0f6')
    write(out / 'manifest.webmanifest', manifest)
    write(out / 'release.json', dict(name='一书三图', version='2.0.0', books=100, primaryImages=300, generatedNotebookCards=generated, canonicalUrl='https://shutu.kanglimin.com/', productionBranch='main', rankingDate=method.get('asOf', '2026-10-22')))
    digest = hashlib.sha256()
    for name in ('index.html', 'style.css', 'app.js', 'books.js', 'manifest.webmanifest'):
        digest.update((out / name).read_bytes())
    version = 'onebook-notebook-' + digest.hexdigest()[:12]
    sw = (root / 'tools/templates/sw.js').read_text(encoding='utf-8')
    (out / 'sw.js').write_text(sw.replace('__VERSION__', version).replace('__ASSET_FILES__', json.dumps(versioned_assets)), encoding='utf-8', newline='\n')
    print(json.dumps(dict(books=100, mainImages=300, extras=sum(len(b['extras']) for b in books), generated=generated, cacheVersion=version), ensure_ascii=False))


if __name__ == '__main__':
    main()
