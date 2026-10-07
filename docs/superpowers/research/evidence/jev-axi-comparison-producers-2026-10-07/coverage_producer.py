"""Relate an explicit commit candidate to supplied records, without judging review sufficiency."""
import argparse
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def require(value, reason):
    if not value: raise ValueError(reason)


def digest_valid(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value)


def relative_path(value):
    require(isinstance(value, str) and value and '\\' not in value and
            all(ord(c) >= 32 and ord(c) != 127 for c in value) and
            all(p not in ('', '.', '..') for p in value.split('/')), 'invalid relative path')
    return value


def prepare(repository, case_spec, output):
    started = time.monotonic_ns()
    output.mkdir(exist_ok=False)
    packet = {'version': 1, 'ready': False, 'sources': [], 'entries': [],
              'outside_difference': [], 'errors': [], 'review': {'relationship': 'unavailable'}}
    count, case_bytes, trees = 0, b'', {}

    def store(name, data):
        with (output / name).open('xb') as stream: stream.write(data)
        return name

    def git(*args):
        nonlocal count
        run = subprocess.run(['git', '--no-replace-objects', '-C', str(repository), *args],
                             capture_output=True, env={k: v for k, v in os.environ.items() if not k.startswith('GIT_')})
        count += len(run.stdout)
        require(run.returncode == 0, 'unavailable Git object or repository')
        return run.stdout

    def tree(revision):
        require(isinstance(revision, str) and re.fullmatch(r'[0-9a-f]{40}', revision), 'immutable SHA-1 commit required')
        if revision in trees: return dict(trees[revision])
        require(git('cat-file', '-t', revision).strip() == b'commit', 'non-commit identity')
        result = {}
        for row in git('ls-tree', '-rz', '--full-tree', revision).split(b'\0'):
            if row:
                head, path = row.split(b'\t', 1)
                result[relative_path(path.decode())] = head.decode().split()
        trees[revision] = result
        return dict(result)

    def acquire(ref, index):
        item, data = {'id': f's{index:03d}', 'status': 'malformed'}, None
        try:
            require(isinstance(ref, dict) and set(ref) == {'commit', 'path', 'sha256'}, 'source fields')
            relative_path(ref['path'])
            require(digest_valid(ref['sha256']), 'expected digest')
            require(isinstance(ref['commit'], str) and re.fullmatch(r'[0-9a-f]{40}', ref['commit']),
                    'immutable SHA-1 commit required')
            item.update(ref)
            item['status'] = 'unavailable'
            inventory = tree(ref['commit'])
            entry = inventory.get(ref['path'])
            require(entry is not None, 'missing source')
            item['mode'], item['kind'], item['blob'] = entry
            item['status'] = 'unsupported'
            require(entry[0] in ('100644', '100755') and entry[1] == 'blob', 'source kind')
            item['status'] = 'unavailable'
            data = git('cat-file', 'blob', entry[2])
            item.update(artifact=store(f's{index:03d}.bin', data), actual_sha256=sha(data))
            item['status'] = 'available' if sha(data) == ref['sha256'] else 'changed'
        except (ValueError, TypeError, KeyError, OSError):
            pass
        packet['sources'].append(item)
        if item['status'] != 'available': packet['errors'].append(f"{item['id']}: {item['status']}")
        return data if item['status'] == 'available' else None

    try:
        case_bytes = case_spec.read_bytes()
        count += len(case_bytes)
        spec = json.loads(case_bytes)
        required = {'version', 'parent', 'child', 'sources', 'verification', 'review'}
        require(isinstance(spec, dict) and required <= set(spec) <= required | {'overlays'}
                and type(spec['version']) is int and spec['version'] == 1, 'case specification')
        require(isinstance(spec['sources'], list) and bool(spec['sources']), 'ordered sources')
        for key in ('verification', 'review'):
            require(type(spec[key]) is int and 0 <= spec[key] < len(spec['sources']), 'source index')
        parent, child = spec['parent'], spec['child']
        before, after = tree(parent), tree(child)
        require(parent in git('rev-list', '--parents', '-n', '1', child).decode().split()[1:], 'direct parent required')
        packet.update(parent=parent, candidate={'kind': 'commit', 'commit': child},
                      comparison='commit candidate; actual push not established')
        overlays, overlay_bytes = spec.get('overlays', []), {}
        require(isinstance(overlays, list), 'overlays')
        for overlay in overlays:
            require(isinstance(overlay, dict) and set(overlay) == {'path', 'mode', 'base64'}, 'overlay fields')
            path = relative_path(overlay['path'])
            require(path not in overlay_bytes and overlay['mode'] in ('100644', '100755')
                    and isinstance(overlay['base64'], str), 'overlay identity')
            data = base64.b64decode(overlay['base64'], validate=True)
            overlay_bytes[path] = data
            oid = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            after[path] = [overlay['mode'], 'blob', oid]
        for path in after:
            pieces = path.split('/')
            require(not any('/'.join(pieces[:i]) in after for i in range(1, len(pieces))),
                    'file and directory collision in derived snapshot')
        if overlays:
            packet['candidate'] = {'kind': 'snapshot', 'base_commit': child,
                                   'identity_sha256': sha(encoded(sorted(after.items())))}
            packet['comparison'] = 'derived snapshot compared with parent; not a historical commit or observed push'
        sources = [acquire(ref, i) for i, ref in enumerate(spec['sources'])]
        files = None
        try:
            record = json.loads(sources[spec['verification']])
            files = record['reviewed_public_inputs']
            require(isinstance(files, dict) and all(relative_path(p) and digest_valid(h) for p, h in files.items())
                    and digest_valid(record['review_sha256']), 'verification record')
            review = sources[spec['review']]
            packet['review'] = {'source': f"s{spec['review']:03d}", 'recorded_sha256': record['review_sha256'],
                                'relationship': 'unavailable' if review is None else
                                'equal' if sha(review) == record['review_sha256'] else 'different'}
        except (ValueError, TypeError, KeyError):
            files = None
            packet['errors'].append('unavailable or malformed verification record')
        changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
        packet['entries'] = [{'path': path, 'before': before.get(path), 'after': after.get(path),
                              'relationship': 'unavailable'} for path in changed]
        for i, row in enumerate(packet['entries']):
            path, new = row['path'], row['after']
            if new is None or new[0] not in ('100644', '100755') or new[1] != 'blob':
                row['reason'] = 'unsupported deletion or entry kind'
                packet['errors'].append(row['reason'])
                continue
            try:
                data = overlay_bytes[path] if path in overlay_bytes else git('cat-file', 'blob', new[2])
            except ValueError:
                row['reason'] = 'unavailable candidate blob'
                packet['errors'].append(path + ': ' + row['reason'])
                continue
            row.update(sha256=sha(data), artifact=store(f'c{i:03d}.bin', data))
            if files is not None:
                row['recorded_sha256'] = files.get(path)
                row['relationship'] = 'absent' if path not in files else 'equal' if files[path] == sha(data) else 'different'
        if files is not None:
            packet['outside_difference'] = [{'path': p, 'recorded_sha256': h} for p, h in files.items() if p not in changed]
    except (ValueError, TypeError, KeyError, UnicodeError, OSError):
        packet['errors'].append('malformed, unsupported, or unavailable input')
    packet['ready'] = not packet['errors']
    store('packet.json', encoded(packet))
    display = lambda value: html.escape(str(value)).replace('|', '&#124;')
    lines = ['# Candidate identity comparison', '',
             'Identity relationships do not determine review completeness or publication authority.', '',
             f"Package ready: {packet['ready']}", '', '| Path | Before | After | Relationship | Bytes |',
             '| --- | --- | --- | --- | --- |']
    for row in packet['entries']:
        link = f"[file]({row['artifact']})" if 'artifact' in row else 'Unavailable'
        lines.append('| ' + ' | '.join(display(row.get(k)) for k in ('path', 'before', 'after', 'relationship')) + f' | {link} |')
    lines += ['', f"Separate review digest: {packet['review']['relationship']}", '', 'Sources, in supplied order:']
    lines += [f"- {s['id']}: {s['status']}" + (f" ([complete bytes]({s['artifact']}))" if 'artifact' in s else '') for s in packet['sources']]
    lines += ['', 'Content-map entries outside the difference:']
    lines += [f"- {display(s['path'])}: {s['recorded_sha256']}" for s in packet['outside_difference']]
    lines += ['', *[f'- {display(e)}' for e in packet['errors']], '']
    store('packet.md', '\n'.join(lines).encode())
    receipt = {'case_spec_sha256': sha(case_bytes), 'producer_sha256': sha(Path(__file__).read_bytes()),
               'runtime_repository': str(repository.resolve()), 'bytes_read': count,
               'bytes_read_scope': 'case bytes plus returned Git stdout; excludes physical I/O and receipt hashing',
               'duration_monotonic_ms': (time.monotonic_ns()-started)/1_000_000,
               'artifacts': {p.name: sha(p.read_bytes()) for p in output.iterdir()}, 'ready': packet['ready']}
    store('receipt.json', encoded(receipt))
    return 0 if packet['ready'] else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare-coverage'])
    for name in ('repository', 'case-spec', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    try:
        return prepare(args.repository, args.case_spec, args.output)
    except OSError:
        print('Output allocation or write failed; no existing result is overwritten.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
