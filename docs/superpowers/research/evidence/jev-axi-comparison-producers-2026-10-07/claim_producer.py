"""Prepare complete, pinned claim evidence without semantic assessment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def sha(data):
    return hashlib.sha256(data).hexdigest()


def normalize(text):
    return text.replace('\r\n', '\n').replace('\r', '\n')


def read_blob(repository, entry):
    def git(*args):
        return subprocess.run(['git', '--no-replace-objects', '--literal-pathspecs', '-C',
                               str(repository), *args], capture_output=True,
                              env={k: v for k, v in os.environ.items() if not k.startswith('GIT_')})
    kind = git('cat-file', '-t', entry['commit'])
    if kind.returncode: return 'missing', None
    if kind.stdout.strip() != b'commit': return 'unsupported', None
    tree = git('ls-tree', '-z', entry['commit'], '--', entry['path'])
    rows = [r for r in tree.stdout.split(b'\0') if r]
    if tree.returncode or not rows: return 'missing', None
    if len(rows) != 1: return 'unsupported', None
    header, path = rows[0].split(b'\t', 1)
    mode, kind, oid = header.split()
    if path != entry['path'].encode() or mode not in (b'100644', b'100755') or kind != b'blob':
        return 'unsupported', None
    blob = git('cat-file', 'blob', oid.decode())
    if blob.returncode: return 'missing', None
    return ('ready' if sha(blob.stdout) == entry['sha256'] else 'changed'), blob.stdout


def validate(case):
    required = {'version', 'case_id', 'assertion', 'draft', 'sources'}
    if not isinstance(case, dict) or not required <= set(case) <= required | {'quotation'}:
        raise ValueError('case fields')
    if type(case['version']) is not int or case['version'] != 1:
        raise ValueError('version')
    if not isinstance(case['case_id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,32}', case['case_id']):
        raise ValueError('case id')
    if not isinstance(case['assertion'], str) or not case['assertion'].strip():
        raise ValueError('assertion')
    quote = case.get('quotation')
    if quote is not None and (not isinstance(quote, str) or not quote or
                              normalize(quote) not in normalize(case['assertion'])):
        raise ValueError('quotation')
    if not isinstance(case['sources'], list) or not 1 <= len(case['sources']) <= 2:
        raise ValueError('sources')
    for index, entry in enumerate([case['draft']] + case['sources']):
        keys = {'commit', 'path', 'sha256'}
        extra = {'start_line', 'end_line', 'assertion_line'} if index == 0 else {'availability'}
        if not isinstance(entry, dict) or not keys <= set(entry) <= keys | extra:
            raise ValueError('source fields')
        for key, pattern in [('commit', r'[0-9a-f]{40}'), ('sha256', r'[0-9a-f]{64}')]:
            if not isinstance(entry[key], str) or not re.fullmatch(pattern, entry[key]):
                raise ValueError('identity')
        path = entry['path']
        if not isinstance(path, str) or not path or any(c in path for c in '\\:*?[]') or any(ord(c)<32 for c in path) or any(part in ('', '.', '..') for part in path.split('/')):
            raise ValueError('path')
        if index == 0:
            if any(type(entry.get(k)) is not int for k in extra):
                raise ValueError('coordinates')
            if not 1 <= entry['start_line'] <= entry['assertion_line'] <= entry['end_line']:
                raise ValueError('coordinates')
        elif entry.get('availability', 'fetch') not in ('fetch', 'controlled_unavailable'):
            raise ValueError('availability')


def prepare(repository, case_spec, output):
    started = time.monotonic_ns()
    output.mkdir(exist_ok=False)
    raw, case = b'', None
    artifacts, texts, blob_bytes = {}, [], 0

    def write(name, data):
        with (output / name).open('xb') as stream:
            stream.write(data)
        artifacts[name] = {'sha256': sha(data), 'bytes': len(data)}

    try:
        raw = case_spec.read_bytes()
        case = json.loads(raw)
        validate(case)
    except (ValueError, TypeError, KeyError, UnicodeError, OSError):
        packet = {'status': 'non_ready', 'reason': 'malformed_or_unavailable_case_spec'}
        write('packet.json', (json.dumps(packet) + '\n').encode())
        write('packet.md', b'# Claim evidence\n\nStatus: non_ready\n')
        write('receipt.json', (json.dumps({'case_spec_sha256': sha(raw), 'artifacts': dict(artifacts),
              'producer_sha256': sha(Path(__file__).read_bytes()), 'case_spec_bytes': len(raw),
              'git_blob_bytes_read': 0, 'duration_monotonic_ms': (time.monotonic_ns()-started)/1_000_000})+'\n').encode())
        return 2
    packet = {'status': 'ready', 'case_id': case['case_id'],
              'assertion': case['assertion'], 'sources': []}

    for name, entry in [('draft', case['draft'])] + [
            (f'source-{i}', value) for i, value in enumerate(case['sources'], 1)]:
        data, text, status = None, '', 'controlled_unavailable'
        if entry.get('availability') != 'controlled_unavailable':
            status, data = read_blob(repository, entry)
        if data is not None:
            blob_bytes += len(data)
            write(name + '.source', data)
            try:
                text = data.decode('utf-8')
            except UnicodeError:
                status = 'unsupported'
        if status != 'ready':
            packet['status'] = 'non_ready'
        record = entry | {'status': status, 'observed_sha256': sha(data) if data is not None else None,
                          'file': name + '.source' if data is not None else None}
        if name == 'draft':
            packet['draft'] = record
            draft_lines = text.splitlines(keepends=True)
            a, b, n = entry['start_line'], entry['end_line'], entry['assertion_line']
            packet['context'] = ''.join(draft_lines[a-1:b])
            if status == 'ready' and (b > len(draft_lines) or case['assertion'] not in draft_lines[n-1]):
                record['status'] = 'malformed_context'
                packet['status'] = 'non_ready'
        else:
            packet['sources'].append(record)
            texts.append(text)
    quote = case.get('quotation')
    packet['quotation_status'] = ('none' if quote is None else
                                  'matched' if any(normalize(quote) in normalize(t) for t in texts)
                                  else 'unmatched')
    if packet['status'] != 'ready':
        packet['quotation_status'] = 'unavailable'
    lines = ['# Claim evidence', '', 'Status: ' + packet['status'], '', packet['assertion'],
             '', '## Draft context', '', packet['context']]
    for index, text in enumerate(texts, 1):
        record = packet['sources'][index-1]
        lines += ['', f'## Source {index}', '', 'Status: ' + record['status'],
                  'Revision: ' + record['commit'], 'Path: ' + record['path'], '']
        lines += [f'{n:04d} | {line}' for n, line in enumerate(text.splitlines(), 1)]
    write('packet.json', (json.dumps(packet, ensure_ascii=False, indent=2) + '\n').encode())
    write('packet.md', ('\n'.join(lines) + '\n').encode())
    receipt = {'producer_sha256': sha(Path(__file__).read_bytes()), 'case_spec_sha256': sha(raw),
               'git_blob_bytes_read': blob_bytes, 'case_spec_bytes': len(raw), 'artifacts': dict(artifacts),
               'duration_monotonic_ms': (time.monotonic_ns()-started)/1_000_000}
    write('receipt.json', (json.dumps(receipt, indent=2) + '\n').encode())
    return 0 if packet['status'] == 'ready' else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare-claim'])
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--case-spec', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        return prepare(args.repository, args.case_spec, args.output)
    except FileExistsError:
        print('Output already exists; no files changed.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
