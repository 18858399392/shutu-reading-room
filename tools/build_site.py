"""Rebuild the notebook site from committed content and UI templates.

Image generation is separate: tools/build_notebook_images.py and the renderer.
The original v1 generator is retained as build_legacy_site.py for reference.
"""
import argparse
import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path, PurePosixPath


AI_IMAGE_ROLES = ('cover', 'threeLines', 'blackboard')


def load_ai_overrides(data, book_ids, out=None):
    """Load optional, persistent image selections without modifying the base plan."""
    path = data / 'ai-image-overrides.json'
    raw = read(path) if path.is_file() else {}
    if not isinstance(raw, dict):
        raise ValueError('ai-image-overrides.json must be an object keyed by book ID')
    overrides = {}
    for key, roles in raw.items():
        if not str(key).isdigit() or int(key) not in book_ids:
            raise ValueError(f'Unknown AI image book ID: {key}')
        book_id = int(key)
        if book_id in overrides or not isinstance(roles, dict):
            raise ValueError(f'Invalid or duplicate AI image entry: {key}')
        overrides[book_id] = {}
        for role, value in roles.items():
            if role not in AI_IMAGE_ROLES or not isinstance(value, dict):
                raise ValueError(f'Invalid AI image role: {key}/{role}')
            image = deepcopy(value)
            image.setdefault('thumb', image.get('src'))
            for field in ('src', 'thumb'):
                relative = image.get(field)
                if not isinstance(relative, str) or any(c in relative for c in ('\\', '?', '#', '%')):
                    raise ValueError(f'Invalid AI image {field}: {key}/{role}')
                parts = PurePosixPath(relative).parts
                if parts[:2] != ('assets', 'ai-books') or len(parts) < 3 or '..' in parts:
                    raise ValueError(f'AI image must stay in assets/ai-books: {relative}')
                if out is not None:
                    asset = (out / relative).resolve()
                    try:
                        asset.relative_to((out / 'assets/ai-books').resolve())
                    except ValueError as error:
                        raise ValueError(f'AI image escapes its asset directory: {relative}') from error
                    if not asset.is_file():
                        raise ValueError(f'Missing AI image: {asset}')
                    if field == 'src' and image.get('assetSha256', image.get('sourceSha256')):
                        if hashlib.sha256(asset.read_bytes()).hexdigest() != image.get('assetSha256', image.get('sourceSha256')):
                            raise ValueError(f'AI image content hash changed: {relative}')
            for field in ('width', 'height'):
                if isinstance(image.get(field), bool) or not isinstance(image.get(field), int) or image[field] <= 0:
                    raise ValueError(f'AI image requires positive {field}: {key}/{role}')
            if not isinstance(image.get('label'), str) or not image['label'].strip():
                raise ValueError(f'AI image requires a label: {key}/{role}')
            image.update(generated=True, aiGenerated=True)
            overrides[book_id][role] = image
    return overrides


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
    ai_overrides = load_ai_overrides(data, expected, out)
    for rank in ranks.values():
        assert all(0 <= rank[key] <= 5 and rank[key] * 2 == int(rank[key] * 2) for key in ('impact', 'popularity', 'reach'))
    order = sorted(ranks.values(), key=lambda rank: (-round(rank['impact'] * 2) * 50 - round(rank['popularity'] * 2) * 35 - round(rank['reach'] * 2) * 15, -rank['impact'], -rank['popularity'], -rank['reach'], rank['id']))
    assert [rank['rank'] for rank in order] == list(range(1, 101)), 'Ranking disagrees with stated weighting and tie-break'
    generated = 0
    for book in books:
        rank, plan = ranks[book['id']], images[book['id']]
        book.update(rank=rank['rank'], rankReason=rank['reason'], ranking={k: rank[k] for k in ('impact', 'popularity', 'reach')})
        selected = ai_overrides.get(book['id'], {})
        book['images'] = [dict(selected.get(key, plan[key])) for key in AI_IMAGE_ROLES]
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
    for name in ('style.css', 'app.js', 'books.js', 'assets/icon.svg', 'assets/icon-192.png', 'assets/icon-512.png'):
        fingerprint = hashlib.sha256((out / name).read_bytes()).hexdigest()[:12]
        versioned = name + '?v=' + fingerprint
        html = html.replace('"' + name + '"', '"' + versioned + '"')
        versioned_assets.append('./' + versioned)
    (out / 'index.html').write_text(html, encoding='utf-8', newline='\n')
    shutil.copyfile(out / 'index.html', out / 'index.htm')
    manifest = read(out / 'manifest.webmanifest')
    manifest.update(name='一书三图 · 翻页阅读本', description='100本好书，大封面、三句话、黑板图解。按综合阅读榜翻阅，从目录直达每一本。', background_color='#f2eee5', theme_color='#294536')
    for icon in manifest['icons']:
        relative = icon['src'].split('?')[0]
        icon['src'] = relative + '?v=' + hashlib.sha256((out / relative).read_bytes()).hexdigest()[:12]
    write(out / 'manifest.webmanifest', manifest)
    ai_generated = sum(bool(image.get('aiGenerated')) for book in books for image in book['images'])
    write(out / 'release.json', dict(name='一书三图', version='2.2.0', theme='reading-journal', books=100, primaryImages=300, generatedNotebookCards=generated-ai_generated, aiGeneratedImages=ai_generated, canonicalUrl='https://shutu.kanglimin.com/', productionBranch='main', rankingDate=method.get('asOf', '2026-10-22')))
    digest = hashlib.sha256()
    for name in ('index.html', 'style.css', 'app.js', 'books.js', 'manifest.webmanifest'):
        digest.update((out / name).read_bytes())
    version = 'onebook-notebook-' + digest.hexdigest()[:12]
    sw = (root / 'tools/templates/sw.js').read_text(encoding='utf-8')
    (out / 'sw.js').write_text(sw.replace('__VERSION__', version).replace('__ASSET_FILES__', json.dumps(versioned_assets)), encoding='utf-8', newline='\n')
    print(json.dumps(dict(books=100, mainImages=300, extras=sum(len(b['extras']) for b in books), generated=generated, cacheVersion=version), ensure_ascii=False))


if __name__ == '__main__':
    main()
