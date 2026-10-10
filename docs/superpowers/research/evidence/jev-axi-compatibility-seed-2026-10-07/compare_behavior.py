#!/usr/bin/env python3
"""Compare trusted local inventory CLIs at their documented TSV boundary.

Each command has a 5-second timeout. Exit codes: 0 compatible, 1 different,
2 observation_failed (or invalid invocation). The evidence directory is new.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys

TIMEOUT_SECONDS = 5
HEADER = ['sku', 'warehouse', 'on_hand']


def source_identity(root):
    def traversal_error(error):
        raise error

    files = {}
    for directory, subdirectories, names in os.walk(root, onerror=traversal_error):
        subdirectories[:] = sorted(name for name in subdirectories if name != '__pycache__')
        for name in sorted(names):
            path = Path(directory) / name
            if '__pycache__' not in path.parts and stat.S_ISREG(path.stat().st_mode):
                files[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def parse_tsv(data):
    try:
        rows = list(csv.reader(io.StringIO(data.decode('utf-8')), delimiter='\t', quoting=csv.QUOTE_NONE))
        if not rows or rows[0] != HEADER:
            raise ValueError('invalid TSV header')
        records = []
        for row in rows[1:]:
            if len(row) != 3 or not row[0] or not row[1] or not row[2].isdigit():
                raise ValueError('invalid TSV record')
            records.append([row[0], row[1], int(row[2])])
        return sorted(records)
    except (UnicodeError, csv.Error, ValueError) as exc:
        raise ValueError(str(exc)) from exc


def observe(root, name, input_path, output_dir, warehouse, threshold):
    commands = {
        'report': ['bin/inventory-report', '--input', str(input_path)],
        'low_stock': ['bin/low-stock', '--input', str(input_path), '--threshold', str(threshold)],
        'archive': ['jobs/archive-inventory.py', '--input', str(input_path), '--output', str(output_dir / 'archive.tsv')],
    }
    if name == 'filtered_report':
        command = ['bin/inventory-report', '--input', str(input_path), '--warehouse', warehouse]
    else:
        command = commands[name]
    argv = [sys.executable, str(root / command[0]), *command[1:]]
    record = {'argv': argv, 'exit_code': None, 'timed_out': False, 'stdout': '', 'stderr': '', 'stdout_hex': '', 'stderr_hex': '', 'archive_bytes_hex': None, 'records': None, 'status': None}
    try:
        with subprocess.Popen(argv, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True) as process:
            try:
                stdout, stderr = process.communicate(timeout=TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stdout, stderr = process.communicate()
                record.update(timed_out=True, exit_code=process.returncode,
                              stdout=stdout.decode('utf-8', 'replace'), stderr=stderr.decode('utf-8', 'replace'),
                              stdout_hex=stdout.hex(), stderr_hex=stderr.hex(), status='failed')
                return record
            result = subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)
        record.update(exit_code=result.returncode, stdout=result.stdout.decode('utf-8', 'replace'), stderr=result.stderr.decode('utf-8', 'replace'), stdout_hex=result.stdout.hex(), stderr_hex=result.stderr.hex())
        payload = result.stdout
        if name == 'archive':
            archive = output_dir / 'archive.tsv'
            if archive.exists():
                payload = archive.read_bytes()
                record['archive_bytes_hex'] = payload.hex()
            elif result.returncode == 0:
                record['status'] = 'malformed'
                return record
        if result.returncode != 0:
            record['status'] = 'failed'
        else:
            try:
                record['records'] = parse_tsv(payload)
                record['status'] = 'success'
            except ValueError as exc:
                record['status'] = 'malformed'
                record['parse_error'] = str(exc)
    except OSError as exc:
        record.update(status='failed', stderr=str(exc))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('before', 'after', 'input', 'output'):
        parser.add_argument('--' + flag, type=Path, required=True)
    parser.add_argument('--warehouse')
    parser.add_argument('--threshold', type=int, default=2)
    args = parser.parse_args()
    for name in ('before', 'after', 'input', 'output'):
        setattr(args, name, getattr(args, name).resolve())
    if args.threshold < 0 or not args.before.is_dir() or not args.after.is_dir() or not args.input.is_file() or args.output.exists():
        parser.error('require source directories, an input file, a nonnegative threshold, and a new output directory')
    if any(args.output.is_relative_to(root) for root in (args.before, args.after)):
        parser.error('evidence output must be outside both source directories')
    try:
        source = {'before': source_identity(args.before), 'after': source_identity(args.after)}
    except OSError as error:
        parser.error(f'source inventory unavailable: {error}')
    input_bytes = args.input.read_bytes()
    args.output.mkdir(parents=True, exist_ok=False)
    retained = args.output / 'input.json'
    retained.write_bytes(input_bytes)
    names = ['report'] + (['filtered_report'] if args.warehouse is not None else []) + ['low_stock', 'archive']
    observations = {}
    failed = different = False
    for name in names:
        sides = {}
        for side, root in (('before', args.before), ('after', args.after)):
            directory = args.output / side / name
            directory.mkdir(parents=True)
            sides[side] = observe(root, name, retained, directory, args.warehouse, args.threshold)
        statuses = [sides[side]['status'] for side in ('before', 'after')]
        same = statuses == ['success', 'success'] and sides['before']['records'] == sides['after']['records']
        observation_failed = 'failed' in statuses
        difference = not same and not observation_failed
        # A successful observation alongside a failed one remains unestablished.
        failed |= observation_failed
        different |= difference
        observations[name] = {**sides, 'different': difference, 'observation_failed': observation_failed}
    source_rechecks = {}
    for side, root in (('before', args.before), ('after', args.after)):
        try:
            identity = source_identity(root)
            status = 'unchanged' if identity == source[side] else 'changed'
            source_rechecks[side] = {'status': status, 'identity': identity}
        except OSError as error:
            source_rechecks[side] = {'status': 'failed', 'identity': None,
                                     'error': str(error)}
        failed |= source_rechecks[side]['status'] != 'unchanged'
    outcome = 'observation_failed' if failed else 'different' if different else 'compatible'
    summary = {'outcome': outcome, 'input_sha256': hashlib.sha256(input_bytes).hexdigest(), 'source_identities': source, 'source_rechecks': source_rechecks, 'timeout_seconds': TIMEOUT_SECONDS, 'observations': observations}
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(outcome)
    return {'compatible': 0, 'different': 1, 'observation_failed': 2}[outcome]


if __name__ == '__main__':
    raise SystemExit(main())
