"""Import reviewed imagegen results; preserve originals and optionally encode web assets."""
import argparse
import io
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from PIL import Image

from build_site import AI_IMAGE_ROLES, load_ai_overrides, read

ROLE_LABELS = {'cover': '视觉封面', 'threeLines': '三句话解读', 'blackboard': '黑板图解'}
ROLE_FILENAMES = {'cover': 'cover', 'threeLines': 'three-lines', 'blackboard': 'blackboard'}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def prepare(manifest, data, site, encode_webp=False, originals_dir=None):
    raw = read(manifest)
    entries = raw.get('images') if isinstance(raw, dict) else raw
    if not isinstance(entries, list) or not entries:
        raise ValueError('Manifest must be a nonempty array or {"images": [...]}')
    book_ids = {book['id'] for book in read(data / 'books-base.json')}
    existing = load_ai_overrides(data, book_ids, site)
    provenance_path = data / 'ai-image-provenance.json'
    provenance = read(provenance_path) if provenance_path.is_file() else []
    if not isinstance(provenance, list):
        raise ValueError('ai-image-provenance.json must contain an array')
    plans = []
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError('Every manifest image must be an object')
        book_id = entry.get('id')
        if isinstance(book_id, bool) or not isinstance(book_id, int) or book_id not in book_ids:
            raise ValueError(f'Unknown manifest book ID: {book_id}')
        role = entry.get('role', entry.get('slot'))
        if role not in AI_IMAGE_ROLES:
            raise ValueError(f'Invalid role/slot for book {book_id}: {role}')
        if entry.get('role') and entry.get('slot') and entry['role'] != entry['slot']:
            raise ValueError(f'Conflicting role and slot for book {book_id}')
        if (book_id, role) in seen:
            raise ValueError(f'Duplicate manifest target: {book_id}/{role}')
        seen.add((book_id, role))
        if entry.get('reviewed') is not True:
            raise ValueError(f'Image must be reviewed before import: {book_id}/{role}')
        value = entry.get('path')
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'Missing local image path: {book_id}/{role}')
        source = Path(value).expanduser()
        if not source.is_absolute():
            source = manifest.parent / source
        source = source.resolve(strict=True)
        if not source.is_file():
            raise ValueError(f'Image path is not a file: {source}')
        with Image.open(source) as image:
            image.load()
            width, height, fmt = image.width, image.height, image.format
            if abs(width / height - .75) > .015:
                raise ValueError(f'Image must be portrait 3:4: {book_id}/{role} ({width}x{height})')
            web_bytes = thumb_bytes = None
            if encode_webp:
                web_buffer, thumb_buffer = io.BytesIO(), io.BytesIO()
                image.save(web_buffer, format='WEBP', quality=92, method=6)
                thumbnail = image.copy()
                thumbnail.thumbnail((420, 560), Image.Resampling.LANCZOS)
                thumbnail.save(thumb_buffer, format='WEBP', quality=88, method=6)
                web_bytes, thumb_bytes = web_buffer.getvalue(), thumb_buffer.getvalue()
        if fmt not in ('PNG', 'JPEG'):
            raise ValueError(f'Only original PNG/JPEG results are accepted: {source} ({fmt})')
        checksum = sha256(source)
        suffix = '.png' if fmt == 'PNG' else '.jpg'
        stem = f'{book_id:03}-{ROLE_FILENAMES[role]}-{checksum[:12]}'
        relative = f'assets/ai-books/{stem}' + ('.webp' if encode_webp else suffix)
        target = (site / relative).resolve()
        thumb_relative = f'assets/ai-books/{stem}-thumb.webp' if encode_webp else relative
        thumb_target = (site / thumb_relative).resolve()
        asset_checksum = hashlib.sha256(web_bytes).hexdigest() if encode_webp else checksum
        try:
            target.relative_to((site / 'assets/ai-books').resolve())
        except ValueError as error:
            raise ValueError('AI asset destination escapes its directory') from error
        if target.exists() and sha256(target) != asset_checksum:
            raise ValueError(f'Existing content-addressed image differs; refusing overwrite: {target}')
        if encode_webp and thumb_target.exists() and sha256(thumb_target) != hashlib.sha256(thumb_bytes).hexdigest():
            raise ValueError(f'Existing thumbnail differs; refusing overwrite: {thumb_target}')
        original_target = originals_dir / (stem + suffix) if originals_dir else None
        if original_target and original_target.exists() and sha256(original_target) != checksum:
            raise ValueError(f'Existing original differs; refusing overwrite: {original_target}')
        label = entry.get('label', ROLE_LABELS[role])
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f'Invalid label for {book_id}/{role}')
        selected = dict(src=relative, thumb=thumb_relative, label=label, generated=True, aiGenerated=True,
                        width=width, height=height, sourceSha256=checksum, assetSha256=asset_checksum)
        details = {key: deepcopy(value) for key, value in entry.items()
                   if key not in ('id', 'role', 'slot') and not key.lower().endswith('path')}
        record = dict(id=book_id, role=role, asset=relative, sourceSha256=checksum,
                      sourceFileName=source.name, manifestFile=manifest.name,
                      importedAt=datetime.now(timezone.utc).isoformat(), **details)
        record.update(assetSha256=asset_checksum, encoding='webp-q92' if encode_webp else 'original',
                      width=width, height=height)
        # The full original absolute path remains in the local manifest; do not publish it.
        plans.append(dict(id=book_id, role=role, source=source, target=target,
                          checksum=checksum, asset_checksum=asset_checksum, web_bytes=web_bytes,
                          thumb_bytes=thumb_bytes, thumb_target=thumb_target, original_target=original_target,
                          selected=selected, provenance=record))
    return plans, existing, provenance


def main():
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--data-dir', type=Path, default=root / 'content')
    parser.add_argument('--site-dir', type=Path, default=root / 'site')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--encode-webp', action='store_true', help='Encode full-size WebP and a 420px thumbnail; no cropping or layout changes')
    parser.add_argument('--originals-dir', type=Path, help='Also preserve byte-identical source PNG/JPEG files in this directory')
    args = parser.parse_args()
    manifest = args.manifest.resolve(strict=True)
    data, site = args.data_dir.resolve(strict=True), args.site_dir.resolve(strict=True)
    originals_dir = args.originals_dir.resolve() if args.originals_dir else None
    plans, overrides, provenance = prepare(manifest, data, site, args.encode_webp, originals_dir)
    report = dict(dryRun=args.dry_run, images=len(plans), copied=0, reused=0,
                  assets=[dict(id=p['id'], role=p['role'], asset=p['selected']['src'],
                               width=p['selected']['width'], height=p['selected']['height']) for p in plans])
    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    for plan in plans:
        if plan['target'].exists():
            report['reused'] += 1
        else:
            plan['target'].parent.mkdir(parents=True, exist_ok=True)
            if plan['web_bytes'] is None:
                shutil.copyfile(plan['source'], plan['target'])
            else:
                plan['target'].write_bytes(plan['web_bytes'])
            report['copied'] += 1
        if plan['thumb_bytes'] is not None and not plan['thumb_target'].exists():
            plan['thumb_target'].write_bytes(plan['thumb_bytes'])
        if sha256(plan['target']) != plan['asset_checksum']:
            raise ValueError(f'Imported image bytes differ: {plan["target"]}')
        if plan['original_target']:
            plan['original_target'].parent.mkdir(parents=True, exist_ok=True)
            if not plan['original_target'].exists():
                shutil.copyfile(plan['source'], plan['original_target'])
            if sha256(plan['original_target']) != plan['checksum']:
                raise ValueError(f'Original image bytes differ: {plan["original_target"]}')
        overrides.setdefault(plan['id'], {})[plan['role']] = plan['selected']
        # Repeat imports are idempotent; new content/prompts retain their own records.
        record = plan['provenance']
        identity = (record['id'], record['role'], record['sourceSha256'], record.get('prompt'))
        if not any((p.get('id'), p.get('role'), p.get('sourceSha256'), p.get('prompt')) == identity for p in provenance):
            provenance.append(record)
    serializable = {str(key): overrides[key] for key in sorted(overrides)}
    atomic_json(data / 'ai-image-provenance.json', provenance)
    atomic_json(data / 'ai-image-overrides.json', serializable)
    report.update(overridesFile=str(data / 'ai-image-overrides.json'), provenanceFile=str(data / 'ai-image-provenance.json'))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
