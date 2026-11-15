#!/usr/bin/env python3
"""Prepare canonical archive aliases from already verified release payloads."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit


DOWNLOADS = 'https://github.com/nisavid/provingkit/releases/download'


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON field')
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError('JSON numbers must be finite')


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_object,
                      parse_constant=invalid_constant)


def filename(value):
    if not isinstance(value, str) or not value or Path(value).name != value or value in {'.', '..'}:
        raise ValueError('archive names must be plain filenames')
    return value


def verify_release(release, inventory, aliases, expected_files):
    if not isinstance(release, dict) or type(release.get('id')) is not int:
        raise ValueError('release snapshot must contain an integer id')
    if release['id'] != inventory['release_id'] or release.get('tag_name') != inventory['tag']:
        raise ValueError('release snapshot identity differs from the inventory')
    assets = release.get('assets')
    if not isinstance(assets, list):
        raise ValueError('release snapshot must contain an assets array')
    by_name = {}
    ids = set()
    for asset in assets:
        if not isinstance(asset, dict):
            raise ValueError('release assets must be objects')
        name = filename(asset.get('name'))
        identity = asset.get('id')
        if type(identity) is not int or identity <= 0 or identity in ids or name in by_name:
            raise ValueError('release asset names and positive ids must be unique')
        by_name[name] = asset
        ids.add(identity)
    original_count = inventory.get('original_asset_count')
    if type(original_count) is not int or original_count < 0 or len(assets) < original_count:
        raise ValueError('release snapshot has fewer assets than the original inventory')
    for alias in aliases:
        for key in ('old_zip', 'old_sidecar', 'new_zip', 'new_sidecar'):
            name = alias[key]
            asset = by_name.get(name)
            if asset is None:
                raise ValueError('release snapshot is missing a required alias or original')
            identity_key = {'old_zip': 'old_asset_id', 'old_sidecar': 'old_sidecar_id'}.get(key)
            if identity_key and asset['id'] != alias[identity_key]:
                raise ValueError('release snapshot changed an original asset id')
            data = expected_files[name]
            if type(asset.get('size')) is not int or asset['size'] != len(data):
                raise ValueError('release asset size differs from the verified payload')
            if asset.get('digest') != 'sha256:' + hashlib.sha256(data).hexdigest():
                raise ValueError('release asset digest differs from the verified payload')
            url = asset.get('browser_download_url')
            if not isinstance(url, str):
                raise ValueError('release asset URL must be a string')
            actual_url = urlsplit(url)
            expected_url = urlsplit(alias[key + '_url'])
            if (actual_url.scheme != expected_url.scheme or actual_url.netloc != expected_url.netloc
                    or unquote(actual_url.path) != unquote(expected_url.path)
                    or actual_url.query or actual_url.fragment):
                raise ValueError('release asset URL differs from the canonical or legacy link')


def prepare(inventory, source, output, release=None):
    if not isinstance(inventory, dict) or not isinstance(inventory.get('aliases'), list) or not inventory['aliases']:
        raise ValueError('inventory must contain a nonempty aliases array')
    if inventory.get('preserve_original_assets') is not True:
        raise ValueError('inventory must preserve all original assets')
    if type(inventory.get('release_id')) is not int or inventory['release_id'] <= 0:
        raise ValueError('release_id must be a positive integer')
    if type(inventory.get('original_asset_count')) is not int or inventory['original_asset_count'] < 2 * len(inventory['aliases']):
        raise ValueError('original_asset_count must cover the original ZIP and sidecar rows')
    tag = filename(inventory['tag'])
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.+-]+)?', tag):
        raise ValueError('inventory tag must name a versioned release')
    version = tag[1:]
    base_url = DOWNLOADS + '/' + quote(tag, safe='')
    aliases = []
    files = []
    originals = {}
    for entry in inventory['aliases']:
        if not isinstance(entry, dict):
            raise ValueError('each alias must be an object')
        plugin = entry.get('plugin')
        if not isinstance(plugin, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', plugin):
            raise ValueError('alias plugin must be a lowercase plugin name')
        stem = 'provingkit-' + plugin + '-' + version
        old_zip = filename(entry['old_zip'])
        old_sidecar = filename(entry['old_sidecar'])
        new_zip = stem + '.zip'
        new_sidecar = new_zip + '.sha256'
        if entry.get('new_zip', new_zip) != new_zip or entry.get('new_sidecar', new_sidecar) != new_sidecar:
            raise ValueError('alias destination disagrees with the canonical naming rule')
        if old_zip != stem + '-agent-plugins.zip' or old_sidecar != old_zip + '.sha256':
            raise ValueError('alias source must name the legacy standard archive and sidecar')
        expected_digest = entry.get('zip_sha256')
        if not isinstance(expected_digest, str) or not re.fullmatch('[0-9a-f]{64}', expected_digest):
            raise ValueError('ZIP digest must be a full lowercase SHA-256')
        if type(entry.get('zip_size')) is not int or entry['zip_size'] < 0:
            raise ValueError('ZIP size must be a nonnegative integer')
        if (source / old_zip).is_symlink() or (source / old_sidecar).is_symlink():
            raise ValueError('source archives and checksums must not be symlinks')
        data = (source / old_zip).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected_digest:
            raise ValueError('ZIP digest differs from the verified inventory')
        if len(data) != entry['zip_size']:
            raise ValueError('ZIP size differs from the verified inventory')
        old_checksum = (source / old_sidecar).read_bytes()
        if old_checksum != (digest + '  ' + old_zip + '\n').encode('utf-8'):
            raise ValueError('source checksum must match the ZIP digest and exact legacy basename')
        sidecar = (digest + '  ' + new_zip + '\n').encode('utf-8')
        sidecar_digest = hashlib.sha256(sidecar).hexdigest()
        if entry.get('new_sidecar_sha256', sidecar_digest) != sidecar_digest:
            raise ValueError('canonical checksum digest disagrees with the inventory')
        if entry.get('new_sidecar_size', len(sidecar)) != len(sidecar):
            raise ValueError('canonical checksum size disagrees with the inventory')
        files.extend([(new_zip, data), (new_sidecar, sidecar)])
        originals.update({old_zip: data, old_sidecar: old_checksum})
        for field in ('old_asset_id', 'old_sidecar_id'):
            if type(entry.get(field)) is not int or entry[field] <= 0:
                raise ValueError(field + ' must be a positive integer')
        row = {
            'plugin': plugin, 'old_zip': old_zip, 'old_sidecar': old_sidecar,
            'old_asset_id': entry['old_asset_id'], 'old_sidecar_id': entry['old_sidecar_id'],
            'new_zip': new_zip, 'new_sidecar': new_sidecar,
            'zip_sha256': digest, 'zip_size': len(data),
            'new_sidecar_sha256': sidecar_digest, 'new_sidecar_size': len(sidecar),
        }
        for key, name in [('old_zip_url', old_zip), ('old_sidecar_url', old_sidecar),
                          ('new_zip_url', new_zip), ('new_sidecar_url', new_sidecar)]:
            row[key] = base_url + '/' + quote(name, safe='')
        aliases.append(row)
    if len({name for name, _ in files}) != len(files):
        raise ValueError('alias destinations must be unique')
    old_ids = [row[key] for row in aliases for key in ('old_asset_id', 'old_sidecar_id')]
    if len(set(old_ids)) != len(old_ids):
        raise ValueError('original asset ids must be unique')
    if release is not None:
        verify_release(release, inventory, aliases, {**originals, **dict(files)})
    if output.is_symlink() or (output.exists() and not output.is_dir()):
        raise ValueError('output must be an owned directory, not a symlink or file')
    pending = []
    reused = []
    for name, data in files:
        target = output / name
        if target.is_symlink():
            raise ValueError('output contains a conflicting symlink')
        if target.exists():
            if not target.is_file() or target.read_bytes() != data:
                raise ValueError('output contains a conflicting file')
            reused.append(name)
        else:
            pending.append((name, data))
    output.mkdir(parents=True, exist_ok=True)
    for name, data in pending:
        with (output / name).open('xb') as target:
            target.write(data)
    return {
        'release_id': inventory['release_id'], 'tag': tag,
        'original_asset_count': inventory['original_asset_count'],
        'preserve_original_assets': True, 'aliases': aliases,
        'created_files': [name for name, _ in pending], 'reused_files': reused,
        'release_snapshot_verified': release is not None, 'public_downloads_verified': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', required=True, type=Path)
    parser.add_argument('--source-dir', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--release', type=Path)
    args = parser.parse_args()
    try:
        inventory = load_json(args.inventory)
        release = load_json(args.release) if args.release else None
        if args.release is not None and not isinstance(release, dict):
            raise ValueError('release snapshot must be an object')
        result = prepare(inventory, args.source_dir, args.output_dir, release)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print('error: ' + str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
