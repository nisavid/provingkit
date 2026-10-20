"""Prepare complete, pinned claim evidence without semantic assessment."""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
import posixpath
from pathlib import Path
import re
import subprocess
import stat
import sys
import time


def sha(data):
    return hashlib.sha256(data).hexdigest()


def normalize(text):
    return text.replace('\r\n', '\n').replace('\r', '\n')


def read_blob(repository, entry, counters):
    def git(*args):
        counters['git_commands'] += 1
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
    if not isinstance(case, dict) or not required <= set(case) <= required | ({'quotation', 'source_link'} if case.get('version') == 2 else {'quotation'}):
        raise ValueError('case fields')
    if type(case['version']) is not int or case['version'] not in (1, 2):
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
        snapshot = case['version'] == 2 and entry.get('kind') == 'snapshot' if isinstance(entry, dict) else False
        keys = {'kind', 'snapshot', 'checkpoint', 'path', 'sha256'} if snapshot else {'commit', 'path', 'sha256'}
        extra = {'start_line', 'end_line', 'assertion_line'} if index == 0 else {'availability'}
        if snapshot:
            extra = extra | {'supersedes'}
        if not isinstance(entry, dict) or not keys <= set(entry) <= keys | extra:
            raise ValueError('source fields')
        for key, pattern in [('sha256', r'[0-9a-f]{64}')] + ([] if snapshot else [('commit', r'[0-9a-f]{40}')]):
            if not isinstance(entry[key], str) or not re.fullmatch(pattern, entry[key]):
                raise ValueError('identity')
        path = entry['path']
        if not isinstance(path, str) or not path or any(c in path for c in '\\:*?[]') or any(ord(c)<32 for c in path) or any(part in ('', '.', '..') for part in path.split('/')):
            raise ValueError('path')
        if snapshot:
            if not isinstance(entry['checkpoint'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', entry['checkpoint']):
                raise ValueError('checkpoint')
            previous = entry.get('supersedes')
            if previous is not None:
                if (not isinstance(previous, dict) or set(previous) != {'checkpoint', 'sha256'}
                        or not isinstance(previous['checkpoint'], str)
                        or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', previous['checkpoint'])
                        or previous['checkpoint'] == entry['checkpoint']
                        or not isinstance(previous['sha256'], str)
                        or not re.fullmatch(r'[0-9a-f]{64}', previous['sha256'])
                        or previous['sha256'] == entry['sha256']):
                    raise ValueError('supersedes')
            stored = entry['snapshot']
            if not isinstance(stored, str) or not stored or any(c in stored for c in '\\:*?[]') or any(ord(c) < 32 for c in stored) or any(part in ('', '.', '..') for part in stored.split('/')):
                raise ValueError('snapshot path')
        if index == 0:
            if any(type(entry.get(k)) is not int for k in ('start_line', 'end_line', 'assertion_line')):
                raise ValueError('coordinates')
            if not 1 <= entry['start_line'] <= entry['assertion_line'] <= entry['end_line']:
                raise ValueError('coordinates')
        elif entry.get('availability', 'fetch') not in ('fetch', 'controlled_unavailable'):
            raise ValueError('availability')

    if case['version'] == 2:
        link = case.get('source_link')
        if len(case['sources']) != 1 or case['draft'].get('kind') != 'snapshot':
            raise ValueError('snapshot case')
        if not isinstance(link, dict) or set(link) != {'line', 'target'}:
            raise ValueError('source link')
        if type(link['line']) is not int or not case['draft']['start_line'] <= link['line'] <= case['draft']['end_line']:
            raise ValueError('source link line')
        if not isinstance(link['target'], str) or not re.fullmatch(r'[A-Za-z0-9_./-]+', link['target']) or link['target'].startswith('/'):
            raise ValueError('source link target')


def read_snapshot(base, entry, counters):
    counters['snapshot_read_attempts'] += 1
    try:
        with ExitStack() as stack:
            directory = os.open(base, os.O_RDONLY | os.O_DIRECTORY)
            stack.callback(os.close, directory)
            parts = entry['snapshot'].split('/')
            for part in parts[:-1]:
                directory = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                    dir_fd=directory)
                stack.callback(os.close, directory)
            fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=directory)
            stream = stack.enter_context(os.fdopen(fd, 'rb'))
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                return 'unsupported', None
            data = stream.read()
    except FileNotFoundError:
        return 'missing', None
    except OSError:
        return 'unsupported', None
    return ('ready' if sha(data) == entry['sha256'] else 'changed'), data


def line_in_code_span(lines, number):
    if not 1 <= number <= len(lines):
        return False
    start, end = number - 1, number
    while start > 0 and lines[start - 1].strip():
        start -= 1
    while end < len(lines) and lines[end].strip():
        end += 1
    text = ''.join(lines[start:end])
    offset = sum(map(len, lines[start:number - 1]))
    runs = list(re.finditer(r'`+', text))
    next_run, next_width = {}, {}
    for index in range(len(runs) - 1, -1, -1):
        width = len(runs[index].group())
        next_run[index] = next_width.get(width)
        next_width[width] = index
    index = 0
    while index < len(runs):
        opening = runs[index]
        before = text[:opening.start()]
        escaped = (len(before) - len(before.rstrip('\\'))) % 2
        closing = None if escaped else next_run[index]
        if closing is None:
            index += 1
        else:
            if opening.end() <= offset < runs[closing].start():
                return True
            index = closing + 1
    return False


def prepare(repository, case_spec, output):
    started = time.monotonic_ns()
    output.mkdir(exist_ok=False)
    raw, case = b'', None
    artifacts, texts, blob_bytes = {}, [], 0
    counters = {'snapshot_bytes_read': 0, 'snapshot_read_attempts': 0, 'git_commands': 0}

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
              **counters, 'git_blob_bytes_read': 0, 'duration_monotonic_ms': (time.monotonic_ns()-started)/1_000_000})+'\n').encode())
        return 2
    packet = {'status': 'ready', 'case_id': case['case_id'],
              'assertion': case['assertion'], 'sources': []}

    for name, entry in [('draft', case['draft'])] + [
            (f'source-{i}', value) for i, value in enumerate(case['sources'], 1)]:
        data, text, status = None, '', 'controlled_unavailable'
        if entry.get('availability') != 'controlled_unavailable':
            status, data = (read_snapshot(case_spec.parent, entry, counters) if entry.get('kind') == 'snapshot'
                            else read_blob(repository, entry, counters))
        if data is not None:
            if entry.get('kind') == 'snapshot':
                counters['snapshot_bytes_read'] += len(data)
            else:
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
            if status == 'ready' and (b > len(draft_lines) or
                                      case['assertion'] not in draft_lines[n-1] or
                                      packet['context'].count(case['assertion']) != 1):
                record['status'] = 'malformed_context'
                packet['status'] = 'non_ready'
        else:
            packet['sources'].append(record)
            texts.append(text)
    if case['version'] == 2:
        link = case['source_link']
        target = posixpath.normpath(posixpath.join(posixpath.dirname(case['draft']['path']), link['target']))
        line = draft_lines[link['line']-1] if link['line'] <= len(draft_lines) else ''
        matches = re.findall(r'\[[^\[\]\n]+\]\(([^()\s]+)\)', line)
        prefix = ''.join(draft_lines[:link['line']])
        simple_prose = (not line.expandtabs(4).startswith('    ')
                        and not line.lstrip(' \t').startswith('>')
                        and not line_in_code_span(draft_lines, link['line'])
                        and not any(c in line for c in ('`', '\\', '!['))
                        and not any(c in prefix for c in ('```', '~~~', '<'))
                        and line.count('[') == line.count(']') == 1)
        file_target = link['target'].rsplit('/', 1)[-1] not in ('', '.', '..')
        matched = (simple_prose and file_target and matches == [link['target']]
                   and target == case['sources'][0]['path'])
        packet['source_link'] = link | {'status': 'matched' if matched else 'unresolved', 'source_id': 'source-1'}
        if not matched:
            packet['status'] = 'non_ready'
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
                  'Revision: ' + record.get('commit', 'snapshot ' + record.get('checkpoint', '')), 'Path: ' + record['path'], '']
        lines += [f'{n:04d} | {line}' for n, line in enumerate(text.splitlines(), 1)]
    write('packet.json', (json.dumps(packet, ensure_ascii=False, indent=2) + '\n').encode())
    write('packet.md', ('\n'.join(lines) + '\n').encode())
    if packet['status'] == 'ready':
        inference = {'assertion': case['assertion'], 'draft_context': packet['context'],
                     'sources': [{'id': f'source-{index}', 'text': text}
                                 for index, text in enumerate(texts, 1)]}
        write('inference.json', (json.dumps(inference, ensure_ascii=False, indent=2) + '\n').encode())
    receipt = {'producer_sha256': sha(Path(__file__).read_bytes()), 'case_spec_sha256': sha(raw),
               **counters, 'git_blob_bytes_read': blob_bytes, 'case_spec_bytes': len(raw), 'artifacts': dict(artifacts),
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
