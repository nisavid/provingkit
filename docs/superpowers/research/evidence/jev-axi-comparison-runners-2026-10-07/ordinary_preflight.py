"""Validate a frozen ordinary-comparison invocation before any runner launch."""
import argparse
import hashlib
import json
import math
from pathlib import Path

PROFILES = [('gpt-6-luna', 'low'), ('gpt-6-luna', 'medium'),
            ('gpt-6-luna', 'high'), ('gpt-6.1-sol', 'low')]
CLAIMS = ['c01', 'c04', 'c03', 'c06', 'c05', 'c07', 'c02', 'c08', 'c09', 'c10', 'c11']
CEILINGS = {
    'claim': dict(request_seconds=120, run_seconds=9000, input_bytes=65536,
                  request_bytes=131072, response_bytes=1048576, requests_per_cell=1),
    'coverage': dict(request_seconds=120, run_seconds=9000, input_bytes=262144,
                     request_bytes=393216, response_bytes=1048576, requests_per_cell=5,
                     cell_seconds=480, tool_operations=32, tool_result_bytes=131072,
                     tool_total_bytes=2097152)}
ROLES = {'runner', 'contract', 'procedure', 'corpus', 'route', 'price', 'evaluator', 'inference'}

def fingerprint(data):
    return hashlib.sha256(data).hexdigest()

def checked(reference):
    path = Path(reference['path'])
    size = reference['bytes']
    if type(size) is not int or size < 0 or path.is_symlink() or not path.is_file():
        raise ValueError('invalid frozen file reference')
    with path.open('rb') as stream:
        data = stream.read(size + 1)
    if len(data) != size or fingerprint(data) != reference['sha256']:
        raise ValueError('frozen file identity changed')
    return data

def load_json(path, expected):
    path = Path(path)
    size = path.stat().st_size
    if size > 1048576:
        raise ValueError('metadata exceeds one MiB')
    data = checked(dict(path=str(path), bytes=size, sha256=expected))
    def unique(pairs):
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValueError('duplicate JSON key')
        return result
    def constant(_):
        raise ValueError('nonstandard JSON constant')
    return json.loads(data, object_pairs_hook=unique, parse_constant=constant)

def matrix(spec):
    kind = spec.get('kind')
    if type(spec.get('version')) is not int or spec['version'] != 1 or kind not in CEILINGS:
        raise ValueError('unsupported ordinary protocol')
    cases, conditions = spec['cases'], spec['conditions']
    expected = CLAIMS if kind == 'claim' else ['c01', 'c04']
    if [case['id'] for case in cases] != expected:
        raise ValueError(kind + ' case matrix differs')
    if any(case['status'] != ('unavailable' if case['id'] == 'c11' else 'ready')
           for case in cases):
        raise ValueError('case status differs')
    identities = [condition['id'] for condition in conditions]
    if len(set(identities)) != len(identities):
        raise ValueError('duplicate condition identity')
    if kind == 'claim':
        if (len(conditions) != 6 or conditions[0]['adapter'] != 'jev'
                or not isinstance(conditions[0]['model'], str) or not conditions[0]['model']
                or conditions[0]['effort'] is not None
                or (conditions[1]['adapter'], conditions[1]['model'], conditions[1]['effort'])
                   != ('decisions', 'gpt-6-luna', None)
                or [(item['adapter'], item['model'], item['effort']) for item in conditions[2:]]
                   != [('responses', model, effort) for model, effort in PROFILES]):
            raise ValueError('claim condition matrix differs')
    else:
        if spec.get('mode') != 'comparison':
            raise ValueError('coverage requires comparison mode')
        actual = [(item['adapter'], item['model'], item['effort'], item['arm'])
                  for item in conditions]
        wanted = [('responses', model, effort, arm) for model, effort in PROFILES
                  for arm in ['ordinary', 'deterministic']]
        if actual != wanted:
            raise ValueError('coverage condition matrix differs')
        for index in range(0, 8, 2):
            a, b = conditions[index:index + 2]
            if any(a[key] != b[key] for key in ['endpoint', 'billing', 'auth_env', 'rates']):
                raise ValueError('coverage routes differ between arms')
    limits = spec['limits']
    if set(limits) != set(CEILINGS[kind]):
        raise ValueError('limit fields differ')
    for key, ceiling in CEILINGS[kind].items():
        value = limits[key]
        if (type(value) not in {int, float} or not math.isfinite(value)
                or value <= 0 or value > ceiling
                or (not key.endswith('_seconds') and type(value) is not int)):
            raise ValueError('limit exceeds ordinary allowance')
    if limits['requests_per_cell'] != CEILINGS[kind]['requests_per_cell']:
        raise ValueError('request allowance differs')
    schedule = []
    for position, case in enumerate(cases):
        if case['status'] != 'ready':
            continue
        if kind == 'claim':
            start = position % 6
            ordered = conditions[start:] + conditions[:start]
        else:
            ordered = []
            for profile in range(4):
                pair = conditions[profile * 2:profile * 2 + 2]
                ordered += pair if (int(case['id'][1:]) - 1 + profile) % 2 == 0 else pair[::-1]
        schedule.extend(dict(case=case['id'], condition=item['id']) for item in ordered)
    return schedule

def admit(spec_path, spec_sha256, bindings_path, bindings_sha256):
    spec = load_json(spec_path, spec_sha256)
    schedule = matrix(spec)
    bindings = load_json(bindings_path, bindings_sha256)
    if (set(bindings) != {'version', 'kind', 'invocation_seconds', 'dependencies'}
            or type(bindings['version']) is not int or bindings['version'] != 1
            or bindings['kind'] != spec['kind']
            or type(bindings['invocation_seconds']) not in {int, float}
            or not math.isfinite(bindings['invocation_seconds'])
            or not 0 < bindings['invocation_seconds'] <= 9000):
        raise ValueError('invalid invocation bindings')
    dependencies = bindings['dependencies']
    if (not isinstance(dependencies, list) or not dependencies
            or any(set(item) != {'role', 'id', 'path', 'sha256', 'bytes'}
                   or item['role'] not in ROLES for item in dependencies)
            or len({(item['role'], item['id']) for item in dependencies}) != len(dependencies)
            or {item['role'] for item in dependencies} != ROLES):
        raise ValueError('incomplete frozen dependencies')
    runners = [item for item in dependencies if item['role'] == 'runner']
    if len(runners) != 1:
        raise ValueError('one runner binding required')
    inference = {item['id']: item for item in dependencies if item['role'] == 'inference'}
    if set(inference) != {case['id'] for case in spec['cases']}:
        raise ValueError('inference bindings differ')
    evaluator = {item['sha256'] for item in dependencies if item['role'] == 'evaluator'}
    for item in dependencies:
        checked(item)
    if spec['kind'] == 'claim':
        corpus = {item['id']: item for item in dependencies if item['role'] == 'corpus'}
        manifest = json.loads(checked(corpus['manifest']))
        records = {item['case']: item for item in manifest['preparations']}
        if (set(records) != set(CLAIMS)
                or any(records[case]['status'] != ('non_ready' if case == 'c11' else 'ready')
                       or records[case]['exit_code'] != (2 if case == 'c11' else 0)
                       for case in CLAIMS)):
            raise ValueError('claim producer outcomes differ')
        control = json.loads(checked(corpus['c11-packet']))
        if (control['case_id'] != 'c11' or control['status'] != 'non_ready'
                or control['quotation_status'] != 'unavailable'
                or len(control['sources']) != 1
                or control['sources'][0]['status'] != 'controlled_unavailable'
                or control['sources'][0]['availability'] != 'controlled_unavailable'
                or control['sources'][0]['observed_sha256'] is not None
                or control['sources'][0]['file'] is not None):
            raise ValueError('claim fallback control differs')
    for case in spec['cases']:
        reference = inference[case['id']]
        if (Path(reference['path']).resolve() != Path(case['input']['path']).resolve()
                or reference['sha256'] != case['input']['sha256']
                or reference['sha256'] in evaluator
                or reference['bytes'] > spec['limits']['input_bytes']):
            raise ValueError('inference identity or evaluator separation differs')
        if spec['kind'] == 'coverage':
            packet = json.loads(checked(reference))
            if (set(packet) != {'version', 'task', 'common_context', 'relationship_summary',
                               'sources', 'comparisons'} or packet['version'] != 2):
                raise ValueError('coverage requires the reviewed packet shape')
    return dict(spec=spec, bindings=bindings, schedule=schedule, runner=runners[0],
                spec_sha256=spec_sha256, bindings_sha256=bindings_sha256)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['spec', 'spec-sha256', 'bindings', 'bindings-sha256']:
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    try:
        result = admit(args.spec, args.spec_sha256, args.bindings, args.bindings_sha256)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps(dict(status='refused', reason=str(error), requests_submitted=0)))
        return 2
    print(json.dumps(dict(status='admitted', requests_submitted=0, admission=result)))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
