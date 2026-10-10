#!/usr/bin/env python3
"""Compare trusted local inventory CLIs, or grade the amended format contract.

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


def observe(root, name, input_path, output_dir, warehouse, threshold,
            extra=(), output_format='text', expect_rejection=False):
    commands = {
        'report': ['bin/inventory-report', '--input', str(input_path)],
        'low_stock': ['bin/low-stock', '--input', str(input_path), '--threshold', str(threshold)],
        'archive': ['jobs/archive-inventory.py', '--input', str(input_path), '--output', str(output_dir / 'archive.tsv')],
    }
    if name == 'filtered_report':
        command = ['bin/inventory-report', '--input', str(input_path), '--warehouse', warehouse]
    else:
        command = commands[name]
    command.extend(extra)
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
            output_index = max(index for index, value in enumerate(command) if value == '--output')
            archive = Path(command[output_index + 1])
            if archive.exists():
                payload = archive.read_bytes()
                record['archive_bytes_hex'] = payload.hex()
            elif result.returncode == 0:
                record['status'] = 'malformed'
                return record
        if expect_rejection:
            record['status'] = ('success' if result.returncode != 0
                                and result.stderr.strip() and not result.stdout
                                and record['archive_bytes_hex'] is None else 'malformed')
        elif result.returncode != 0:
            record['status'] = 'failed'
        else:
            try:
                record['records'] = (parse_report_json(payload, warehouse)
                                     if output_format == 'json' else parse_tsv(payload))
                record['status'] = 'success'
            except ValueError as exc:
                record['status'] = 'malformed'
                record['parse_error'] = str(exc)
    except OSError as exc:
        record.update(status='failed', stderr=str(exc))
    return record


def inventory_records(items):
    if not isinstance(items, list):
        raise ValueError('items must be a list')
    records = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('item must be an object')
        sku, warehouse, quantity = item['sku'], item['warehouse'], item['on_hand']
        if any(not isinstance(value, str) or not value or '\t' in value
               or value.splitlines() != [value] for value in (sku, warehouse)):
            raise ValueError('invalid record identity')
        if type(quantity) is not int or quantity < 0:
            raise ValueError('invalid quantity')
        if (sku, warehouse) in seen:
            raise ValueError('duplicate record identity')
        seen.add((sku, warehouse))
        records.append([sku, warehouse, quantity])
    return sorted(records)


def parse_report_json(data, warehouse):
    try:
        value = json.loads(data)
        if (not isinstance(value, dict)
                or value.get('schema') != 'inventory-report/v1'
                or 'warehouse' not in value or value['warehouse'] != warehouse):
            raise ValueError('invalid JSON schema or selected warehouse')
        return inventory_records(value['items'])
    except (UnicodeError, ValueError, KeyError, TypeError) as exc:
        raise ValueError(str(exc)) from exc


def contract_cases(before, directory):
    cases = []
    for ident in ('unfiltered', 'south', 'empty', 'no-matches'):
        paths = [directory / ident, directory / (ident + '.json')]
        paths = [path for path in paths if path.is_file()]
        if len(paths) != 1:
            raise ValueError(f'require one case file for {ident}')
        declaration_bytes = paths[0].read_bytes()
        declaration = json.loads(declaration_bytes)
        selected = declaration['input']
        if not isinstance(selected, str) or Path(selected).is_absolute():
            raise ValueError('case input must be relative to baseline')
        input_path = (before / selected).resolve()
        if not input_path.is_relative_to(before):
            raise ValueError('case input must be within baseline')
        input_bytes = input_path.read_bytes()
        records = inventory_records(json.loads(input_bytes)['items'])
        warehouse = declaration.get('warehouse')
        threshold = declaration.get('threshold', 2)
        if (warehouse is not None and not isinstance(warehouse, str)
                or type(threshold) is not int or threshold < 0):
            raise ValueError('invalid case filter or threshold')
        cases.append((ident, declaration_bytes, input_bytes, records, warehouse, threshold))
    supported = {'items': [
        {'sku': '"A"é', 'warehouse': ' North ', 'on_hand': 0},
        {'sku': '"A"é', 'warehouse': 'South', 'on_hand': 4},
    ]}
    data = json.dumps(supported, ensure_ascii=False).encode('utf-8')
    cases.append(('supported-identities', b'{"constructed": true}', data,
                  inventory_records(supported['items']), None, 2))
    return cases


def invalid_inputs():
    item = {'sku': 'A', 'warehouse': 'North', 'on_hand': 0}
    values = {
        'malformed-json': b'{broken',
        'missing-items': b'{}',
        'root-null': b'null',
        'root-array': b'[]',
        'invalid-utf8': b'\xff',
        'items-not-array': b'{"items": {}}',
        'nonobject-item': b'{"items": [null]}',
        'duplicate': json.dumps({'items': [item, item]}).encode(),
    }
    for field in ('sku', 'warehouse', 'on_hand'):
        values['missing-' + field] = json.dumps(
            {'items': [{key: value for key, value in item.items() if key != field}]}).encode()
    for field in ('sku', 'warehouse'):
        for index, value in enumerate(('', None, 1, 'A\tB', 'A\nB', 'A\rB',
                                       'A\vB', 'A\fB', 'A\x1cB', 'A\x1dB',
                                       'A\x1eB', 'A\x85B', 'A\u2028B', 'A\u2029B')):
            values[f'{field}-{index}'] = json.dumps({'items': [{**item, field: value}]}).encode()
    for index, quantity in enumerate((-1, True, None, 1.5, '1')):
        values[f'quantity-{index}'] = json.dumps({'items': [{**item, 'on_hand': quantity}]}).encode()
    return values


def evaluate_contract(args, source):
    # Parse and retain the oracle outside either source, before invoking candidates.
    cases = contract_cases(args.before, args.contract_cases)
    args.output.mkdir(parents=True, exist_ok=False)
    observations = {}
    inputs = {}
    failed = different = False

    def check(key, name, input_path, warehouse=None, threshold=2,
              extra=(), output_format='text', expected=None, reject=False,
              sides=('before', 'after')):
        nonlocal failed, different
        observed = {}
        for side in sides:
            directory = args.output / side / key
            directory.mkdir(parents=True)
            observed[side] = observe(
                getattr(args, side), name, input_path, directory, warehouse, threshold,
                extra=extra, output_format=output_format, expect_rejection=reject)
        observation_failed = any(record['status'] == 'failed' for record in observed.values())
        matches = all(record['status'] == 'success'
                      and (reject or record['records'] == expected)
                      for record in observed.values())
        difference = any(record['status'] != 'failed'
                         and (record['status'] != 'success'
                              or (not reject and record['records'] != expected))
                         for record in observed.values())
        failed |= observation_failed
        different |= difference
        observations[key] = {**observed, 'expected_records': expected,
                             'expected_rejection': reject, 'matches_contract': matches,
                             'different': difference, 'observation_failed': observation_failed}

    for ident, declaration, data, records, warehouse, threshold in cases:
        directory = args.output / 'cases' / ident
        directory.mkdir(parents=True)
        (directory / 'case.json').write_bytes(declaration)
        input_path = directory / 'input.json'
        input_path.write_bytes(data)
        inputs[ident] = {'case_sha256': hashlib.sha256(declaration).hexdigest(),
                        'input_sha256': hashlib.sha256(data).hexdigest()}
        selected = [row for row in records if warehouse is None or row[1] == warehouse]
        name = 'filtered_report' if warehouse is not None else 'report'
        check(ident + '/default', name, input_path, warehouse, threshold, expected=selected)
        check(ident + '/text', name, input_path, warehouse, threshold,
              extra=('--format', 'text'), expected=selected, sides=('after',))
        check(ident + '/json', name, input_path, warehouse, threshold,
              extra=('--format', 'json'), output_format='json', expected=selected, sides=('after',))
        check(ident + '/low-stock', 'low_stock', input_path, threshold=threshold,
              expected=[row for row in records if row[2] <= threshold])
        check(ident + '/archive', 'archive', input_path, expected=records)

    def reject_reports(key, path, extra=(), sides=('before', 'after')):
        check(key + '/default', 'report', path, extra=extra, reject=True, sides=sides)
        for mode in ('text', 'json'):
            check(key + '/' + mode, 'report', path, extra=('--format', mode, *extra),
                  reject=True, sides=('after',))

    invalid_dir = args.output / 'invalid'
    invalid_dir.mkdir()
    for ident, data in invalid_inputs().items():
        path = invalid_dir / (ident + '.json')
        path.write_bytes(data)
        inputs['invalid/' + ident] = {'input_sha256': hashlib.sha256(data).hexdigest()}
        reject_reports('invalid/' + ident, path)
        for name in ('low_stock', 'archive'):
            check('invalid/' + ident + '/' + name, name, path, reject=True)
    valid_path = args.output / 'cases/unfiltered/input.json'
    reject_reports('invalid/missing-file', invalid_dir / 'absent.json')
    reject_reports('invalid/unknown-argument', valid_path, ('--unknown',))
    check('invalid/format', 'report', valid_path,
          extra=('--format', 'yaml'), reject=True, sides=('after',))
    check('invalid/negative-threshold', 'low_stock', valid_path, threshold=-1, reject=True)
    check('invalid/noninteger-threshold', 'low_stock', valid_path,
          extra=('--threshold', 'no'), reject=True)
    check('invalid/archive-parent', 'archive', valid_path,
          extra=('--output', str(args.output / 'absent-parent/archive.tsv')), reject=True)
    source_rechecks = {}
    for side, root in (('before', args.before), ('after', args.after)):
        try:
            identity = source_identity(root)
            status = 'unchanged' if identity == source[side] else 'changed'
            source_rechecks[side] = {'status': status, 'identity': identity}
        except OSError as error:
            source_rechecks[side] = {'status': 'failed', 'identity': None, 'error': str(error)}
        failed |= source_rechecks[side]['status'] != 'unchanged'
    outcome = 'observation_failed' if failed else 'different' if different else 'compatible'
    summary = {'mode': 'amended-inventory-contract/v1', 'outcome': outcome,
               'evaluator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'inputs': inputs, 'source_identities': source, 'source_rechecks': source_rechecks,
               'timeout_seconds': TIMEOUT_SECONDS, 'observations': observations}
    (args.output / 'summary.json').write_text(
        json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(outcome)
    return {'compatible': 0, 'different': 1, 'observation_failed': 2}[outcome]



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('before', 'after', 'output'):
        parser.add_argument('--' + flag, type=Path, required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--input', type=Path)
    selection.add_argument('--contract-cases', type=Path,
                           help='hidden final grading of the four prepared inventory cases')
    parser.add_argument('--warehouse')
    parser.add_argument('--threshold', type=int, default=2)
    args = parser.parse_args()
    if args.contract_cases is not None and (args.warehouse is not None or args.threshold != 2):
        parser.error('contract cases select the warehouse and threshold')
    for name in ('before', 'after', 'input', 'output', 'contract_cases'):
        if getattr(args, name) is not None:
            setattr(args, name, getattr(args, name).resolve())
    if args.threshold < 0 or not args.before.is_dir() or not args.after.is_dir() or (args.input is not None and not args.input.is_file()) or (args.contract_cases is not None and not args.contract_cases.is_dir()) or args.output.exists():
        parser.error('require source directories, an input file or case directory, a nonnegative threshold, and a new output directory')
    if any(args.output.is_relative_to(root) for root in (args.before, args.after)):
        parser.error('evidence output must be outside both source directories')
    try:
        source = {'before': source_identity(args.before), 'after': source_identity(args.after)}
    except OSError as error:
        parser.error(f'source inventory unavailable: {error}')
    if args.contract_cases is not None:
        try:
            return evaluate_contract(args, source)
        except (OSError, ValueError, KeyError, TypeError) as error:
            parser.error(f'contract evaluation unavailable: {error}')
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
