"""Prepare and retain bounded ordinary comparison evidence."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import http.client
import json
import multiprocessing
import math
import re
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

QUESTION = ('Considering only the supplied sources, what relation does the designated assertion '
            'have to their evidence? Respect the assertion\'s scope and any explicit qualifications '
            'in the supplied evidence. Do not decide global truth or recommend an action.')
RELATIONS = {
    'supported': 'The supplied evidence warrants the complete assertion at its stated scope.',
    'contradicted': ('A supplied source explicitly states an incompatible fact, and the supplied '
                     'sources do not conflict about it.'),
    'unsupported_extension': ('The assertion claims more than the supplied evidence establishes, '
                              'without a demonstrated incompatible fact.'),
    'unresolved': ('Missing referents, conflicting sources, or insufficiently interpretable '
                   'context prevent choosing the other relations.')}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def http_child(endpoint, body, headers, response_path, byte_limit, deadline_ns, channel):
    """Stream directly to the reserved attempt; the parent owns the wall-clock limit."""
    url = urlsplit(endpoint)
    connection_type = http.client.HTTPSConnection if url.scheme == 'https' else http.client.HTTPConnection
    remaining = (deadline_ns - time.monotonic_ns()) / 1_000_000_000
    if remaining <= 0:
        channel.send({'transport_status': 'not_submitted'})
        channel.close()
        return
    connection = connection_type(url.hostname, url.port, timeout=remaining)
    try:
        if time.monotonic_ns() >= deadline_ns:
            channel.send({'transport_status': 'not_submitted'})
            return
        channel.send({'submission_started': True})
        connection.request('POST', url.path or '/', body=body, headers=headers)
        response = connection.getresponse()
        channel.send({'http_status': response.status,
                      'provider_request_id': response.getheader('x-request-id')})
        total = 0
        first = True
        with Path(response_path).open('xb', buffering=0) as stream:
            while True:
                chunk = response.read1(min(65536, byte_limit - total + 1))
                if not chunk:
                    break
                if first:
                    channel.send({'first_byte_monotonic_ns': time.monotonic_ns()})
                    first = False
                retained = chunk[:byte_limit - total]
                stream.write(retained)
                total += len(retained)
                if len(retained) != len(chunk):
                    channel.send({'transport_status': 'response_limit'})
                    return
        channel.send({'transport_status': 'received' if 200 <= response.status < 300 else 'http_error'})
    except (OSError, http.client.HTTPException) as error:
        channel.send({'transport_status': 'timeout' if isinstance(error, TimeoutError) else 'transport_error',
                      'error_type': type(error).__name__})
    finally:
        connection.close()
        channel.close()


def request_bounded(endpoint, body, headers, response_path, byte_limit, deadline_ns):
    if time.monotonic_ns() >= deadline_ns:
        return {'transport_status': 'not_submitted', 'submission_started': False}
    context = multiprocessing.get_context('spawn')
    reader, writer = context.Pipe(duplex=False)
    child = context.Process(target=http_child, args=(
        endpoint, body, headers, str(response_path), byte_limit, deadline_ns, writer))
    child.start()
    writer.close()
    child.join(max(0, (deadline_ns - time.monotonic_ns()) / 1_000_000_000))
    timed_out = child.is_alive()
    if timed_out:
        child.terminate()
        child.join(1)
        if child.is_alive():
            child.kill()
            child.join()
    metadata = {'transport_status': 'transport_error', 'http_status': None,
                'provider_request_id': None, 'first_byte_monotonic_ns': None,
                'submission_started': False}
    while reader.poll():
        try:
            metadata.update(reader.recv())
        except EOFError:
            break
    reader.close()
    if timed_out and metadata['submission_started']:
        metadata['transport_status'] = 'timeout'
    if not metadata['submission_started']:
        metadata['transport_status'] = 'not_submitted'
    if metadata['submission_started'] and not response_path.exists():
        response_path.open('xb').close()
    return metadata


def coverage_packet(state):
    packet = json.loads(state)
    exact_fields(packet, ['task', 'ordinary', 'deterministic', 'sources'], 'coverage packet')
    if any(not isinstance(packet[key], str) or not packet[key] for key in ['task', 'ordinary', 'deterministic']):
        raise ValueError('coverage text is required')
    if not isinstance(packet['sources'], list) or not packet['sources']:
        raise ValueError('coverage sources are required')
    seen = set()
    for source in packet['sources']:
        unavailable = isinstance(source, dict) and 'unavailable_reason' in source
        fields = ['id', 'path', 'unavailable_reason'] if unavailable else ['id', 'path', 'content', 'sha256']
        exact_fields(source, fields, 'coverage source')
        if (not isinstance(source['id'], str) or not re.fullmatch(r's[0-9]{2}', source['id']) or
                source['id'] in seen or not isinstance(source['path'], str)):
            raise ValueError('invalid coverage source identity')
        if unavailable:
            if not isinstance(source['unavailable_reason'], str) or not source['unavailable_reason'].strip():
                raise ValueError('an unavailable source requires its reason')
        elif not isinstance(source['content'], str) or digest(source['content'].encode()) != source['sha256']:
            raise ValueError('invalid coverage source identity')
        seen.add(source['id'])
    return packet


def payload_for(condition, state, kind='claim'):
    if kind == 'coverage':
        packet = coverage_packet(state)
        catalog = [{'id': source['id'], 'path': source['path']} for source in packet['sources']]
        initial = packet[condition['arm']] + '\n\nSources: ' + json.dumps(catalog)
        return {'model': condition['model'], 'instructions': packet['task'],
                'input': [{'role': 'user', 'content': [{'type': 'input_text', 'text': initial}]}],
                'reasoning': {'effort': condition['effort']}, 'stream': True, 'store': False,
                'include': ['reasoning.encrypted_content'],
                'tools': [{'type': 'namespace', 'name': 'evidence',
                           'description': 'Read the supplied evidence sources.',
                           'tools': [{'type': 'function', 'name': 'read_source',
                                      'description': ('Read one complete source by its catalog ID; '
                                                      'unavailable bytes return an explicit unavailable_reason.'),
                                      'strict': True, 'parameters': {'type': 'object',
                                          'properties': {'source': {'type': 'string'}},
                                          'required': ['source'], 'additionalProperties': False}}]}]}
    if condition['adapter'] == 'jev':
        return {'model': condition['model'], 'state': state, 'questions': {
            'claim_relation': {'type': 'choice', 'instructions': QUESTION, 'criteria': RELATIONS}}}
    if condition['adapter'] == 'decisions':
        return {'model': condition['model'], 'input': state, 'questions': [{
            'type': 'choice', 'name': 'claim_relation', 'instructions': QUESTION,
            'choices': [{'value': key, 'description': value} for key, value in RELATIONS.items()]}]}
    if condition['adapter'] == 'responses':
        return {'model': condition['model'], 'instructions': QUESTION + '\n' +
                '\n'.join(key + ': ' + value for key, value in RELATIONS.items()),
                'input': [{'role': 'user', 'content': [{'type': 'input_text', 'text': state}]}],
                'reasoning': {'effort': condition['effort']}, 'stream': True, 'store': False,
                'text': {'format': {'type': 'json_schema', 'name': 'claim_relation',
                    'strict': True, 'schema': {'type': 'object', 'properties': {
                        'relation': {'type': 'string', 'enum': list(RELATIONS)}},
                        'required': ['relation'], 'additionalProperties': False}}}}
    raise ValueError('unsupported adapter')


def response_evidence(adapter, body):
    """Acquire the response envelope before interpreting its answer."""
    events = []
    if adapter == 'responses':
        malformed = False
        for part in body.replace(b'\r\n', b'\n').split(b'\n\n')[:-1]:
            data = b'\n'.join(line[5:].lstrip(b' ') for line in part.splitlines()
                              if line.startswith(b'data:'))
            if data and data != b'[DONE]':
                try:
                    event = json.loads(data)
                except ValueError:
                    malformed = True
                    continue
                events.append(event)
                if not isinstance(event, dict) or not isinstance(event.get('type'), str):
                    malformed = True
        terminal = [event for event in events
                    if isinstance(event, dict) and isinstance(event.get('type'), str)
                    and event['type'] in {
            'response.completed', 'response.failed', 'response.incomplete', 'error'}]
        if not terminal:
            return None, events, 'invalid_response' if malformed else 'stream_incomplete'
        if len(terminal) != 1:
            return None, events, 'invalid_response'
        event = terminal[0]
        result = event.get('response')
        if event['type'] == 'error':
            return result, events, 'provider_error'
        if event['type'] != 'response.completed':
            status = {'response.failed': 'provider_failed',
                      'response.incomplete': 'provider_incomplete'}[event['type']]
            return result, events, status
        return result, events, 'invalid_response' if malformed else 'completed'
    return json.loads(body), events, 'completed'


def parse_result(adapter, result, events, envelope_status, kind='claim'):
    if envelope_status != 'completed':
        return result, events, None, envelope_status
    if adapter == 'responses':
        if not isinstance(result, dict) or result.get('status') != 'completed':
            return result, events, None, 'invalid_response'
        output = result.get('output')
        if not isinstance(output, list):
            return result, events, None, 'invalid_response'
        for item in output:
            if not isinstance(item, dict) or not isinstance(item.get('type'), str):
                return result, events, None, 'invalid_response'
            if item['type'] == 'message':
                content = item.get('content')
                if (not isinstance(content, list) or any(
                        not isinstance(part, dict) or not isinstance(part.get('type'), str)
                        for part in content)):
                    return result, events, None, 'invalid_response'
                if any(part['type'] == 'output_text' and not isinstance(part.get('text'), str)
                       for part in content):
                    return result, events, None, 'invalid_response'
        if any(content.get('type') == 'refusal' for item in output
               if item.get('type') == 'message' for content in item.get('content', [])):
            return result, events, None, 'refused'
        if any(item['type'] == 'function_call' for item in output):
            return result, events, None, 'tool_calls' if kind == 'coverage' else 'unexpected_tool_call'
        texts = [content.get('text') for item in output
                 if item.get('type') == 'message' and item.get('role') == 'assistant'
                 and (kind == 'claim' or item.get('phase') in {None, 'final_answer'})
                 for content in item.get('content', []) if content.get('type') == 'output_text']
        if any(not isinstance(value, str) for value in texts):
            return result, events, None, 'invalid_response'
        if kind == 'coverage':
            answer = ''.join(texts)
            return result, events, answer or None, 'completed' if answer.strip() else 'invalid_response'
        try:
            value = json.loads(''.join(texts))
            relation = value['relation'] if set(value) == {'relation'} and value['relation'] in RELATIONS else None
        except (ValueError, TypeError, KeyError):
            relation = None
    else:
        answers = result.get('answers')
        if adapter == 'jev' and isinstance(answers, dict) and set(answers) == {'claim_relation'}:
            answers = [dict(answers['claim_relation'], name='claim_relation')]
        if (isinstance(answers, list) and len(answers) == 1 and
                isinstance(answers[0], dict) and answers[0].get('type') == 'refusal'):
            return result, events, None, 'refused'
        valid = (isinstance(answers, list) and len(answers) == 1 and
                 isinstance(answers[0], dict) and answers[0].get('type') == 'choice' and
                 answers[0].get('name') == 'claim_relation' and answers[0].get('choice') in RELATIONS)
        relation = answers[0]['choice'] if valid and valid_probabilities(adapter, answers[0]) else None
    return result, events, relation, 'completed' if relation is not None else 'invalid_response'


def interpret_response(adapter, body, transport_status, kind='claim'):
    # Retained complete envelopes remain evidence even when transport fails.
    # Only a successful transport can supply an answer or tool continuation.
    try:
        result, events, envelope_status = response_evidence(adapter, body)
    except (ValueError, TypeError, KeyError, AttributeError, IndexError):
        result, events, envelope_status = None, [], 'invalid_response'
    if transport_status != 'received':
        return result, events, None, transport_status
    try:
        return parse_result(adapter, result, events, envelope_status, kind)
    except (ValueError, TypeError, KeyError, AttributeError, IndexError):
        return result, events, None, 'invalid_response'


def valid_probabilities(adapter, answer):
    def probability(value):
        return type(value) in {int, float} and math.isfinite(value) and 0 <= value <= 1
    if not probability(answer.get('confidence')):
        return False
    probabilities = answer.get('probabilities')
    if adapter == 'decisions':
        if not isinstance(probabilities, list) or len(probabilities) != len(RELATIONS):
            return False
        if any(not isinstance(item, dict) or set(item) != {'value', 'probability'}
               for item in probabilities):
            return False
        probabilities = {item['value']: item['probability'] for item in probabilities}
    return (isinstance(probabilities, dict) and set(probabilities) == set(RELATIONS) and
            all(probability(value) for value in probabilities.values()) and
            math.isclose(sum(probabilities.values()), 1.0, rel_tol=0, abs_tol=1e-6))


def value_usage(condition, usage):
    def validate_counts(value):
        for key, count in value.items():
            if key.endswith('_tokens') and count is not None and (type(count) is not int or count < 0):
                raise ValueError('invalid token counter')
            if isinstance(count, dict):
                validate_counts(count)
            elif key.endswith('_details') and count is not None:
                raise ValueError('token details must be an object')
    if usage is None:
        return None
    if not isinstance(usage, dict):
        raise ValueError('usage must be an object')
    validate_counts(usage)
    output = usage.get('output_tokens')
    reasoning = (usage.get('output_tokens_details') or {}).get('reasoning_tokens')
    if (condition['adapter'] == 'responses' and output is not None and
            reasoning is not None and reasoning > output):
        raise ValueError('reasoning tokens exceed output tokens')
    if usage.get('input_tokens') is None:
        return None
    rates = {key: Decimal(value) for key, value in condition['rates'].items()}
    total = Decimal(usage['input_tokens']) * rates['input']
    if condition['adapter'] == 'responses':
        details = usage.get('input_tokens_details') or {}
        counters = [details.get('cached_tokens'), details.get('cache_write_tokens'), usage.get('output_tokens')]
        if sum(value for value in counters[:2] if value is not None) > usage['input_tokens']:
            raise ValueError('cache partitions exceed total input')
        if any(value is None for value in counters):
            return None
        cached, written, output = map(Decimal, counters)
        total = ((Decimal(usage['input_tokens']) - cached - written) * rates['input'] +
                 cached * rates['cached'] + written * rates['write'] + output * rates['output'])
    return format(total / 1_000_000, 'f')


def finalize_response(condition, result, status):
    usage = result.get('usage') if isinstance(result, dict) else None
    returned_model = result.get('model') if isinstance(result, dict) else None
    condition_error = None
    try:
        value = value_usage(condition, usage)
    except (ValueError, TypeError):
        value = None
        condition_error = 'accounting_error'
    if returned_model is not None and returned_model != condition['model']:
        value = None
        condition_error = 'model_mismatch'
    if condition_error and status not in {'response_limit', 'http_error', 'timeout', 'transport_error'}:
        status = condition_error
    return status, condition_error, usage, returned_model, value


def exact_fields(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError('unsupported ' + label + ' fields')


def request_accounting(attempts):
    known_value = sum((Decimal(attempt['api_rate_equivalent_usd']) for attempt in attempts
                       if attempt['api_rate_equivalent_usd'] is not None), Decimal(0))
    unvalued = sum(attempt['api_rate_equivalent_usd'] is None for attempt in attempts)
    totals = {'attempts': len(attempts),
              'known_api_rate_equivalent_usd': format(known_value, 'f'),
              'unvalued_attempts': unvalued,
              'api_rate_equivalent_usd': format(known_value, 'f') if not unvalued else None,
              'confirmed_charge_usd': None, 'complete_workflow_costs_measured': False}
    for counter in ['input_tokens', 'output_tokens']:
        values = [(attempt.get('usage') or {}).get(counter) for attempt in attempts
                  if isinstance(attempt.get('usage'), dict)]
        reported = [value for value in values if type(value) is int and value >= 0]
        totals[counter] = {'reported_sum': sum(reported),
                           'unreported_attempts': len(attempts) - len(reported)}
    return totals


def validate_spec(spec):
    fields = ['version', 'kind', 'cases', 'conditions', 'limits']
    if isinstance(spec, dict) and spec.get('kind') == 'coverage' and 'mode' in spec:
        fields.append('mode')
    exact_fields(spec, fields, 'spec')
    if type(spec['version']) is not int or spec['version'] != 1 or spec['kind'] not in {'claim', 'coverage'}:
        raise ValueError('unsupported protocol')
    if spec['kind'] == 'coverage' and spec.get('mode', 'comparison') not in {'comparison', 'diagnostic'}:
        raise ValueError('unsupported coverage mode')
    limits = spec['limits']
    limit_fields = ['request_seconds', 'run_seconds', 'input_bytes', 'request_bytes',
                    'response_bytes', 'requests_per_cell']
    if spec['kind'] == 'coverage':
        limit_fields += ['cell_seconds', 'tool_operations', 'tool_result_bytes', 'tool_total_bytes']
    exact_fields(limits, limit_fields, 'limits')
    for key, value in limits.items():
        if type(value) not in {int, float} or not math.isfinite(value) or value <= 0:
            raise ValueError('limits must be positive finite numbers')
        if not key.endswith('_seconds') and type(value) is not int:
            raise ValueError('count and byte limits must be integers')
    if spec['kind'] == 'claim' and limits['requests_per_cell'] != 1:
        raise ValueError('claim cells have exactly one request')
    if spec['kind'] == 'coverage' and limits['requests_per_cell'] > 5:
        raise ValueError('coverage cells permit at most five requests')
    for collection in ['cases', 'conditions']:
        if not isinstance(spec[collection], list) or not spec[collection]:
            raise ValueError('nonempty ' + collection + ' required')
        seen = set()
        for item in spec[collection]:
            identity = item.get('id') if isinstance(item, dict) else None
            if not isinstance(identity, str) or not re.fullmatch(r'[a-z][a-z0-9_-]*', identity) or identity in seen:
                raise ValueError('invalid or duplicate identifier')
            seen.add(identity)
    for case in spec['cases']:
        exact_fields(case, ['id', 'status', 'input'], 'case')
        if not re.fullmatch(r'c[0-9]{2}', case['id']) or case['status'] not in {'ready', 'unavailable'}:
            raise ValueError('case must have a neutral identity and supported status')
        exact_fields(case['input'], ['path', 'sha256'], 'input')
        if not isinstance(case['input']['path'], str) or not re.fullmatch(r'[0-9a-f]{64}', case['input']['sha256']):
            raise ValueError('invalid input reference')
    for condition in spec['conditions']:
        fields = ['id', 'adapter', 'model', 'effort', 'endpoint', 'billing', 'auth_env', 'rates']
        if spec['kind'] == 'coverage':
            fields += ['arm']
        exact_fields(condition, fields, 'condition')
        if spec['kind'] == 'coverage' and (condition['adapter'] != 'responses' or
                                           condition['arm'] not in {'ordinary', 'deterministic'}):
            raise ValueError('coverage needs a Responses arm')
        if condition['adapter'] not in {'jev', 'decisions', 'responses'}:
            raise ValueError('unsupported adapter')
        if condition['adapter'] == 'responses':
            if condition['model'] not in {'gpt-6-luna', 'gpt-6.1-sol'} or condition['effort'] not in {'low', 'medium', 'high'}:
                raise ValueError('unsupported model or effort')
        elif condition['effort'] is not None:
            raise ValueError('effort is not supported by this endpoint')
        endpoint = condition['endpoint']
        if (not isinstance(endpoint, str) or
                any(ord(char) <= 32 or ord(char) == 127 for char in endpoint)):
            raise ValueError('invalid endpoint')
        url = urlsplit(endpoint)
        port = url.port
        if (url.scheme not in {'http', 'https'} or not url.hostname or url.username or url.password or
                url.query or url.fragment or port == 0 or not url.path.isascii()):
            raise ValueError('invalid endpoint')
        exact_fields(condition['rates'], ['input', 'cached', 'write', 'output'], 'rates')
        for value in condition['rates'].values():
            if not isinstance(value, str) or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', value):
                raise ValueError('rates require nonnegative decimal strings')
        if condition['adapter'] in {'jev', 'decisions'} and any(
                Decimal(condition['rates'][component]) != 0 for component in ['cached', 'write', 'output']):
            raise ValueError('Jev and Decisions require input-only rates')
    if spec['kind'] == 'coverage' and spec.get('mode', 'comparison') == 'comparison':
        profiles = {}
        for condition in spec['conditions']:
            profiles.setdefault((condition['model'], condition['effort']), []).append(condition)
        if any(sorted(item['arm'] for item in pair) != ['deterministic', 'ordinary']
               for pair in profiles.values()):
            raise ValueError('coverage comparisons require exactly one condition per arm in each profile')
        if any(pair[0]['endpoint'] != pair[1]['endpoint'] or pair[0]['rates'] != pair[1]['rates']
               for pair in profiles.values()):
            raise ValueError('coverage comparison arms require matching endpoint and rates')


def make_schedule(spec):
    schedule = []
    conditions = spec['conditions']
    ready = [case for case in spec['cases'] if case['status'] == 'ready']
    if spec['kind'] == 'coverage':
        profiles = {}
        for condition in conditions:
            profile = (condition['model'], condition['effort'])
            profiles.setdefault(profile, []).append(condition)
        for case in ready:
            ordinal = int(case['id'][1:]) - 1
            for profile_index, arms in enumerate(profiles.values()):
                first = 'ordinary' if (ordinal + profile_index) % 2 == 0 else 'deterministic'
                for condition in sorted(arms, key=lambda arm: arm['arm'] != first):
                    schedule.append({'case': case['id'], 'condition': condition['id']})
        return schedule
    for index, case in enumerate(ready):
        start = index % len(conditions)
        for condition in conditions[start:] + conditions[:start]:
            schedule.append({'case': case['id'], 'condition': condition['id']})
    return schedule


def prepare(spec_path, output):
    raw = spec_path.read_bytes()
    manifest = json.loads(raw)
    validate_spec(manifest)
    if manifest['kind'] == 'coverage':
        manifest.setdefault('mode', 'comparison')
    inputs = []
    for index, case in enumerate(manifest['cases']):
        source = Path(case['input']['path'])
        if source.is_symlink() or not source.is_file():
            raise ValueError('input must be a regular file')
        with source.open('rb') as stream:
            data = stream.read(manifest['limits']['input_bytes'] + 1)
        if len(data) > manifest['limits']['input_bytes']:
            raise ValueError('input exceeds byte limit')
        if digest(data) != case['input']['sha256']:
            raise ValueError('input identity changed')
        state = data.decode('utf-8')
        if case['status'] == 'ready':
            for condition in manifest['conditions']:
                if len(json.dumps(payload_for(condition, state, manifest['kind'])).encode()) > manifest['limits']['request_bytes']:
                    raise ValueError('request exceeds byte limit')
        inputs.append(data)
    output.mkdir(exist_ok=False)
    for index, (case, data) in enumerate(zip(manifest['cases'], inputs)):
        name = f'input-{index:03d}.txt'
        with (output / name).open('xb') as stream:
            stream.write(data)
        case['input']['path'] = name
    manifest['source_spec_sha256'] = digest(raw)
    manifest['runner_sha256'] = digest(Path(__file__).read_bytes())
    manifest['schedule'] = make_schedule(manifest)
    write_json(output / 'manifest.json', manifest)
    print(json.dumps({'manifest': str(output / 'manifest.json'),
                      'sha256': digest((output / 'manifest.json').read_bytes())}))


def run_coverage_cell(condition, state, output, limits, run_deadline_ns):
    output.mkdir(exist_ok=False)
    tick = time.monotonic_ns()
    cell_deadline_ns = min(run_deadline_ns, tick + int(limits['cell_seconds'] * 1_000_000_000))
    payload = payload_for(condition, state, 'coverage')
    sources = {source['id']: source for source in coverage_packet(state)['sources']}
    operations, prepared_bytes, submitted_bytes, requests = 0, 0, 0, 0
    pending_results = []
    unsubmitted_reason = None
    answer = None
    status = 'resource_incomplete'
    seen_calls = set()
    attempts = []
    for number in range(limits['requests_per_cell']):
        available = (cell_deadline_ns - time.monotonic_ns()) / 1_000_000_000
        body = json.dumps(payload).encode()
        tool_bytes = sum(len(item['output'].encode()) for item in payload['input']
                         if item.get('type') == 'function_call_output')
        if (available <= 0 or len(body) > limits['request_bytes'] or
                submitted_bytes + tool_bytes > limits['tool_total_bytes']):
            status = 'resource_incomplete'
            if available <= 0:
                unsubmitted_reason = 'cell_deadline'
            elif len(body) > limits['request_bytes']:
                unsubmitted_reason = 'request_bytes'
            else:
                unsubmitted_reason = 'tool_submission_bytes'
            break
        started = datetime.now(timezone.utc).isoformat()
        request_tick = time.monotonic_ns()
        request_file = f'request-{number:04d}.body'
        with (output / request_file).open('xb') as stream:
            stream.write(body)
        reservation_path = output / f'request-{number:04d}.json'
        reservation = {
            'status': 'reserved', 'started_at': started, 'request': payload,
            'payload_sha256': digest(body), 'request_body': request_file}
        write_json(reservation_path, reservation)
        response_file = f'response-{number:04d}.body'
        if time.monotonic_ns() >= cell_deadline_ns:
            unsubmitted_reason = 'cell_deadline'
            break
        request_deadline_ns = min(cell_deadline_ns, time.monotonic_ns() +
                                  int(limits['request_seconds'] * 1_000_000_000))
        metadata = request_bounded(condition['endpoint'], body, {'Content-Type': 'application/json'},
                                   output / response_file, limits['response_bytes'],
                                   request_deadline_ns)
        if not metadata['submission_started']:
            unsubmitted_reason = 'cell_deadline' if time.monotonic_ns() >= cell_deadline_ns else 'request_deadline'
            break
        reservation['status'] = 'started'
        reservation_path.write_text(json.dumps(reservation, ensure_ascii=False, indent=2) + '\n')
        submitted_bytes += tool_bytes
        pending_results = []
        unsubmitted_reason = None
        requests += 1
        raw = (output / response_file).read_bytes()
        result, events, answer, status = interpret_response(
            'responses', raw, metadata['transport_status'], 'coverage')
        status, condition_error, usage, returned_model, value = finalize_response(
            condition, result, status)
        attempt = {
            'status': status, 'condition_error': condition_error, 'started_at': started,
            'duration_ms': (time.monotonic_ns() - request_tick) / 1_000_000,
            'request': payload, 'payload_sha256': digest(body), 'request_body': request_file,
            'requested_model': condition['model'], 'returned_model': returned_model,
            'requested_effort': condition['effort'], 'response_body': response_file,
            'raw_response': result, 'raw_events': events, 'usage': usage,
            'api_rate_equivalent_usd': value, 'confirmed_charge_usd': None,
            'residual_provider_work_unknown': status in {'response_limit', 'timeout', 'transport_error'},
            **metadata}
        write_json(output / f'attempt-{number:04d}.json', attempt)
        attempts.append(attempt)
        if status != 'tool_calls':
            break
        history = payload['input'] + [{key: value for key, value in item.items() if key != 'status'}
                                     for item in result['output']]
        tool_results = []
        for call in result['output']:
            if call.get('type') != 'function_call':
                continue
            try:
                args = json.loads(call['arguments'])
                exact_fields(args, ['source'], 'read_source arguments')
                call_id = call['call_id']
                if (call.get('namespace') != 'evidence' or call.get('name') != 'read_source' or
                        not isinstance(call_id, str) or not call_id or call_id in seen_calls):
                    raise ValueError('unsupported or duplicate tool call')
                content = json.dumps(sources[args['source']], ensure_ascii=False)
            except (ValueError, KeyError, TypeError):
                status = 'tool_error'
                break
            size = len(content.encode())
            if (operations >= limits['tool_operations'] or size > limits['tool_result_bytes'] or
                    prepared_bytes + size > limits['tool_total_bytes']):
                status = 'resource_incomplete'
                break
            seen_calls.add(call_id)
            operations += 1
            prepared_bytes += size
            tool_results.append({'type': 'function_call_output', 'call_id': call_id, 'output': content})
        pending_results = [item['call_id'] for item in tool_results]
        write_json(output / f'tools-{number:04d}.json', {
            'results': tool_results, 'status': status, 'operations': operations,
            'prepared_bytes': prepared_bytes})
        if status != 'tool_calls':
            unsubmitted_reason = status
            break
        payload = dict(payload, input=history + tool_results)
        status = 'resource_incomplete'
        unsubmitted_reason = 'request_limit'
    write_json(output / 'summary.json', {
        'status': status, 'answer': answer if status == 'completed' else None,
        'requests': requests, 'tool_operations': operations,
        'tool_prepared_bytes': prepared_bytes,
        'tool_submission_attempted_bytes': submitted_bytes,
        'provider_consumed_tool_bytes': None,
        'unsubmitted_tool_results': pending_results,
        'unsubmitted_reason': unsubmitted_reason,
        'duration_ms': (time.monotonic_ns() - tick) / 1_000_000})
    return status, attempts


def run(prepared, expected_digest, output, local_http):
    run_tick = time.monotonic_ns()
    raw = (prepared / 'manifest.json').read_bytes()
    if digest(raw) != expected_digest:
        raise ValueError('manifest identity changed')
    manifest = json.loads(raw)
    spec = {key: value for key, value in manifest.items() if key not in {'source_spec_sha256', 'runner_sha256', 'schedule'}}
    validate_spec(spec)
    if manifest['schedule'] != make_schedule(spec):
        raise ValueError('schedule differs from the protocol')
    if not local_http:
        raise ValueError('live transport is not implemented')
    for condition in manifest['conditions']:
        endpoint = urlsplit(condition['endpoint'])
        if endpoint.scheme != 'http' or endpoint.hostname != '127.0.0.1':
            raise ValueError('local HTTP tests require a loopback endpoint')
    if manifest['runner_sha256'] != digest(Path(__file__).read_bytes()):
        raise ValueError('runner identity changed')
    states = {}
    for case in manifest['cases']:
        relative = Path(case['input']['path'])
        source = prepared / relative
        if relative.is_absolute() or len(relative.parts) != 1 or source.is_symlink():
            raise ValueError('invalid prepared input path')
        with source.open('rb') as stream:
            data = stream.read(manifest['limits']['input_bytes'] + 1)
        if len(data) > manifest['limits']['input_bytes']:
            raise ValueError('prepared input exceeds byte limit')
        if digest(data) != case['input']['sha256']:
            raise ValueError('prepared input identity changed')
        states[case['id']] = data.decode('utf-8')
    output.mkdir(exist_ok=False)
    cases = {case['id']: case for case in manifest['cases']}
    conditions = {condition['id']: condition for condition in manifest['conditions']}
    slots = []
    attempts = []
    stopped = set()
    run_deadline_ns = run_tick + int(manifest['limits']['run_seconds'] * 1_000_000_000)
    for index, slot in enumerate(manifest['schedule']):
        remaining = (run_deadline_ns - time.monotonic_ns()) / 1_000_000_000
        if remaining <= 0:
            slots.append(dict(slot, status='unattempted', reason='run_deadline'))
            continue
        if slot['condition'] in stopped:
            slots.append(dict(slot, status='unattempted', reason='condition_stopped'))
            continue
        case, condition = cases[slot['case']], conditions[slot['condition']]
        state = states[case['id']]
        if manifest['kind'] == 'coverage':
            status, cell_attempts = run_coverage_cell(condition, state, output / f'cell-{index:04d}',
                                                      manifest['limits'], run_deadline_ns)
            attempts.extend(cell_attempts)
            slots.append(dict(slot, status=status))
            if any(attempt['condition_error'] for attempt in cell_attempts) or status not in {'completed', 'refused', 'provider_incomplete',
                              'stream_incomplete', 'invalid_response', 'timeout',
                              'resource_incomplete', 'response_limit', 'tool_error'}:
                stopped.add(slot['condition'])
            continue
        payload = payload_for(condition, state)
        started = datetime.now(timezone.utc).isoformat()
        tick = time.monotonic_ns()
        body = json.dumps(payload).encode()
        request_file = f'request-{index:04d}.body'
        with (output / request_file).open('xb') as stream:
            stream.write(body)
        reservation_path = output / f'request-{index:04d}.json'
        reservation = dict(slot, status='reserved', started_at=started, request=payload,
                           payload_sha256=digest(body), request_body=request_file)
        write_json(reservation_path, reservation)
        if time.monotonic_ns() >= run_deadline_ns:
            slots.append(dict(slot, status='unattempted', reason='run_deadline'))
            continue
        response_file = f'response-{index:04d}.body'
        request_deadline_ns = min(run_deadline_ns, time.monotonic_ns() +
                                  int(manifest['limits']['request_seconds'] * 1_000_000_000))
        metadata = request_bounded(condition['endpoint'], body,
                                   {'Content-Type': 'application/json'}, output / response_file,
                                   manifest['limits']['response_bytes'],
                                   request_deadline_ns)
        if not metadata['submission_started']:
            slots.append(dict(slot, status='unattempted', reason='run_deadline' if
                              time.monotonic_ns() >= run_deadline_ns else 'request_deadline'))
            continue
        reservation['status'] = 'started'
        reservation_path.write_text(json.dumps(reservation, ensure_ascii=False, indent=2) + '\n')
        response_body = (output / response_file).read_bytes()
        result, events, relation, status = interpret_response(
            condition['adapter'], response_body, metadata['transport_status'])
        duration = (time.monotonic_ns() - tick) / 1_000_000
        status, condition_error, usage, returned_model, value = finalize_response(
            condition, result, status)
        attempt = dict(slot, started_at=started, duration_ms=duration, request=payload,
                       payload_sha256=digest(body), request_body=request_file,
                       requested_model=condition['model'], returned_model=returned_model,
                       requested_effort=condition['effort'],
                       status=status, condition_error=condition_error,
                       response_body=response_file, raw_response=result,
                       raw_events=events, relation=relation, usage=usage,
                       api_rate_equivalent_usd=value, confirmed_charge_usd=None,
                       response_truncated=status in {'response_limit', 'timeout', 'transport_error'},
                       residual_provider_work_unknown=status in {'response_limit', 'timeout', 'transport_error'},
                       **metadata)
        write_json(output / f'attempt-{index:04d}.json', attempt)
        attempts.append(attempt)
        slots.append(dict(slot, status=status))
        if status != 'completed':
            stopped.add(slot['condition'])
    write_json(output / 'summary.json', {'slots': slots,
               'coverage_mode': manifest.get('mode') if manifest['kind'] == 'coverage' else None,
               'cases': [{'case': case['id'], 'status': case['status']} for case in manifest['cases']],
               'request_accounting': request_accounting(attempts),
               'duration_ms': (time.monotonic_ns() - run_tick) / 1_000_000})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prep = commands.add_parser('prepare')
    prep.add_argument('--spec', type=Path, required=True)
    prep.add_argument('--output', type=Path, required=True)
    execution = commands.add_parser('run')
    execution.add_argument('--prepared', type=Path, required=True)
    execution.add_argument('--manifest-sha256', required=True)
    execution.add_argument('--output', type=Path, required=True)
    execution.add_argument('--local-http', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            prepare(args.spec, args.output)
        else:
            run(args.prepared, args.manifest_sha256, args.output, args.local_http)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(type(error).__name__ + ': ' + str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
