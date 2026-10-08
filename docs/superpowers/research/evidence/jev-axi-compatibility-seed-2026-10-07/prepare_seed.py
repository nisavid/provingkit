#!/usr/bin/env python3
"""Prepare a byte-preserving compatibility seed packet from a closed v1 spec.

Directory identity is SHA-256 of UTF-8 JSON of the ordered file entries,
with sort_keys=True, separators=(',', ':'), and ensure_ascii=False. Each entry
has path, sha256, and executable (any execute bit). Files are sorted by path.
Labels supplied by an operator do not prove absence of hidden grading text.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import sys
import time


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def relative(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('invalid relative path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ('.', '..') for part in value.split('/')) or '//' in value:
        raise ValueError('invalid relative path')
    return path


def source(base, name):
    path = base.joinpath(*relative(name).parts)
    if path.is_symlink() or path.resolve() != path.absolute():
        raise ValueError(f'unsafe source path: {name}')
    return path


def file_record(path, declared_sha):
    info = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f'not a regular file: {path}')
    data = path.read_bytes()
    actual = sha(data)
    if actual != declared_sha:
        raise ValueError(f'identity mismatch: {path}')
    return {'sha256': actual, 'bytes': len(data), 'executable': bool(info.st_mode & 0o111), 'mode': stat.S_IMODE(info.st_mode)}, data


def directory(base, declaration):
    root = source(base, declaration['path'])
    if not root.is_dir():
        raise ValueError(f'missing directory: {root}')
    files = declaration['files']
    if not isinstance(files, list) or not files:
        raise ValueError('directory requires nonempty files manifest')
    names = [str(relative(item['path'])) for item in files]
    if names != sorted(set(names)):
        raise ValueError('directory files must be unique and path-sorted')
    actual = []
    copied = []
    for item in files:
        path = source(root, item['path'])
        record, data = file_record(path, item['sha256'])
        if record['executable'] != item['executable']:
            raise ValueError(f'executable mode mismatch: {path}')
        actual.append({'path': item['path'], 'sha256': record['sha256'], 'executable': record['executable']})
        copied.append((item['path'], data, record))
    identity = sha(encoded(actual))
    if identity != declaration['identity']:
        raise ValueError(f'directory identity mismatch: {root}')
    return root, {'path': declaration['path'], 'identity': identity, 'files': [dict(path=name, **record) for name, _, record in copied]}, copied


def write_file(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(data)
    path.chmod(mode)
    if path.read_bytes() != data:
        raise OSError(f'copy verification failed: {path}')


def prepare(spec_path, output):
    started = time.monotonic()
    spec_bytes = spec_path.read_bytes()
    spec = json.loads(spec_bytes)
    if spec.get('version') != 1 or set(spec) != {'version', 'seed', 'requests', 'observation_cases', 'constructed_candidates'}:
        raise ValueError('unsupported version-1 spec')
    base = spec_path.resolve().parent
    seed_root, seed_receipt, seed_files = directory(base, spec['seed'])
    selected = [seed_root]
    variants = []
    ids = set()
    for variant in spec['constructed_candidates']:
        ident = variant['id']
        if not isinstance(ident, str) or not ident.isascii() or not ident.replace('-', '').replace('_', '').isalnum() or ident in ids:
            raise ValueError('invalid or duplicate candidate id')
        ids.add(ident)
        root, receipt, files = directory(base, variant['source'])
        selected.append(root)
        variants.append((ident, receipt, files))
    requests = []
    cases = []
    for index, item in enumerate(spec['requests']):
        path = source(base, item['path'])
        record, data = file_record(path, item['sha256'])
        selected.append(path)
        requests.append((f'{index:04d}', item['path'], data, record))
    case_ids = set()
    for item in spec['observation_cases']:
        ident = item['id']
        if not isinstance(ident, str) or not ident.isascii() or not ident.replace('-', '').replace('_', '').isalnum() or ident in case_ids:
            raise ValueError('invalid or duplicate case id')
        case_ids.add(ident)
        path = source(base, item['path'])
        record, data = file_record(path, item['sha256'])
        selected.append(path)
        cases.append((ident, item['path'], data, record))
    target = output.resolve()
    if any(target == path or target in path.parents or path in target.parents for path in selected):
        raise ValueError('output overlaps selected source')
    receipt = {'version': 1, 'status': 'preparing', 'producer_sha256': sha(Path(__file__).read_bytes()),
               'spec_sha256': sha(spec_bytes), 'prepared_at': datetime.now(timezone.utc).isoformat(),
               'seed': seed_receipt, 'requests': [], 'observation_cases': [], 'constructed_candidates': [],
               'logical_bytes_read': len(spec_bytes) + sum(len(data) for _, data, _ in seed_files)}
    output.mkdir(parents=False, exist_ok=False)
    try:
        write_file(output / 'spec.json', spec_bytes, 0o644)
        for name, data, record in seed_files:
            write_file(output / 'seed' / name, data, record['mode'])
        for index, name, data, record in requests:
            write_file(output / 'requests' / index, data, record['mode'])
            receipt['requests'].append({'path': name, 'output': f'requests/{index}', **record})
            receipt['logical_bytes_read'] += len(data)
        for ident, name, data, record in cases:
            write_file(output / 'cases' / ident, data, record['mode'])
            receipt['observation_cases'].append({'id': ident, 'path': name, 'output': f'cases/{ident}', **record})
            receipt['logical_bytes_read'] += len(data)
        for ident, source_receipt, files in variants:
            for name, data, record in files:
                write_file(output / 'constructed_candidates' / ident / name, data, record['mode'])
                receipt['logical_bytes_read'] += len(data)
            receipt['constructed_candidates'].append({'id': ident, **source_receipt})
        receipt['status'] = 'ready'
        receipt['preparation_elapsed_seconds'] = time.monotonic() - started
        write_file(output / 'receipt.pending', encoded(receipt) + b'\n', 0o644)
        (output / 'receipt.pending').rename(output / 'receipt.json')
    except (OSError, ValueError) as exc:
        receipt['status'] = 'failed'
        receipt['failure'] = str(exc)
        receipt['preparation_elapsed_seconds'] = time.monotonic() - started
        try:
            write_file(output / 'failure.json', encoded(receipt) + b'\n', 0o644)
        except OSError:
            pass
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        prepare(args.spec, args.output)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f'preparation failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
