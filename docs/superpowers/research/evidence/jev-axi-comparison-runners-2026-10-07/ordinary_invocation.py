"""Own the whole clock and outer accounting of an ordinary comparison invocation."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from uuid import uuid4
from ordinary_preflight import admit, checked, fingerprint, load_json

PHASES = {
    'acquisition_selection', 'source_resolution', 'extraction_hashing_rendering',
    'preparation', 'request_work', 'interpretation', 'required_review', 'correction',
    'fallback', 'source_refresh', 'grading', 'operator_recovery', 'handback',
    'setup_research', 'equipment_implementation', 'fixture_construction',
    'source_review', 'operator_effort', 'interruptions', 'billing', 'subscription_usage'}
STATUSES = {'observed', 'derived', 'estimated', 'unknown', 'not_applicable', 'invalid'}

def now():
    return datetime.now(timezone.utc).isoformat(), time.monotonic_ns()

def clock_identity():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()

def save(path, value):
    data = (json.dumps(value, ensure_ascii=True, indent=2) + '\n').encode()
    with Path(path).open('xb') as stream:
        stream.write(data)
    return dict(path=str(path), bytes=len(data), sha256=fingerprint(data))

def reference(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('evidence must be a regular file')
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=fingerprint(data))

class JobFailure(ValueError):
    def __init__(self, name, result, reason, failure_type):
        super().__init__(reason)
        self.name = name
        self.result = result
        self.failure_type = failure_type

def request_inventory(directory):
    evidence = []
    for path in sorted(directory.rglob('*')):
        if path.is_dir() and not path.is_symlink():
            continue
        evidence.append(reference(path))
    return evidence

def retain_request_evidence(state, directory, admission, prepared_ref):
    """Bind retained bytes before reconciling a possibly interrupted request phase."""
    evidence = request_inventory(directory)
    state['request_evidence_root'] = str(directory)
    state['artifacts']['request_evidence'] = save(
        directory.parent / 'request-evidence.json', evidence)
    identity_ref = reference(directory / 'run-identity.json')
    identity = json.loads(checked(identity_ref))
    identities = identity['slots']
    actual = [dict(case=slot['case'], condition=slot['condition']) for slot in identities]
    if (actual != admission['schedule']
            or identity['manifest_sha256'] != prepared_ref['sha256']):
        raise ValueError('partial run identity does not reconcile with admission')
    slots = {slot['slot_id']: slot for slot in identities}
    if len(slots) != len(identities):
        raise ValueError('duplicate partial run slot identity')
    for index, slot in enumerate(identities):
        if (slot['run_id'] != identity['run_id'] or slot['slot_index'] != index
                or slot['slot_id'] != f"{identity['run_id']}/slot-{index:04d}"):
            raise ValueError('invalid partial run slot identity')
    state['artifacts']['run_identity'] = identity_ref
    state['runner_run_id'] = identity['run_id']

    def record_identity(record):
        slot = slots[record['slot_id']]
        number = record['attempt_index']
        if (record['run_id'] != identity['run_id']
                or record['case'] != slot['case']
                or record['condition'] != slot['condition']
                or record['slot_index'] != slot['slot_index']
                or type(number) is not int
                or not 0 <= number < admission['spec']['limits']['requests_per_cell']
                or record['attempt_id'] != f"{slot['slot_id']}/attempt-{number:04d}"):
            raise ValueError('partial request identity differs')
        return record['attempt_id']

    def records(pattern):
        result = {}
        for path in sorted(directory.rglob(pattern)):
            item_ref = reference(path)
            item = json.loads(checked(item_ref))
            key = record_identity(item)
            if key in result:
                raise ValueError('duplicate partial request record')
            result[key] = (item, item_ref, path)
        return result

    reservations = records('request-*.json')
    attempts = records('attempt-*.json')
    boundaries = records('submission-*.json')
    not_submitted = records('not-submitted-*.json')
    if not (set(attempts) | set(boundaries) | set(not_submitted)) <= set(reservations):
        raise ValueError('request record has no reservation')
    maximum = len(identities) * admission['spec']['limits']['requests_per_cell']
    if len(reservations) > maximum:
        raise ValueError('reservation count exceeds admission')
    requests = []
    for key, (reservation, reservation_ref, path) in reservations.items():
        relative = Path(reservation['request_body'])
        if relative.is_absolute() or len(relative.parts) != 1:
            raise ValueError('invalid reserved request body path')
        body_ref = reference(path.parent / relative)
        if body_ref['sha256'] != reservation['payload_sha256']:
            raise ValueError('reserved request body changed')
        item = dict(
            attempt_id=key, slot_id=reservation['slot_id'],
            attempt_index=reservation['attempt_index'],
            reservation=reservation_ref, request_body=body_ref)
        if key in attempts:
            attempt, attempt_ref, _ = attempts[key]
            if (attempt['submission_started'] is not True
                    or attempt['payload_sha256'] != reservation['payload_sha256']
                    or key in not_submitted):
                raise ValueError('observed attempt differs from reservation')
            item.update(status=attempt['status'], submission_started=True,
                        attempt=attempt_ref,
                        usage_rule='runner attempt record remains authoritative',
                        residual_provider_work_unknown=attempt['residual_provider_work_unknown'])
        elif key in not_submitted:
            record, record_ref, _ = not_submitted[key]
            if record['submission_started'] is not False:
                raise ValueError('non-submission record differs')
            item.update(status='not_submitted', submission_started=False,
                        non_submission=record_ref, reason=record['reason'],
                        usage=None, residual_provider_work_unknown=False)
        elif (reservation.get('status') == 'started'
              and reservation.get('submission_started') is True):
            item.update(status='interrupted', submission_started=True,
                        usage=None, residual_provider_work_unknown=True)
        elif key in boundaries:
            record, record_ref, _ = boundaries[key]
            if (record['status'] != 'submission_uncertain'
                    or record['submission_started'] is not None):
                raise ValueError('submission boundary record differs')
            item.update(status='submission_uncertain', submission_started=None,
                        submission_boundary=record_ref,
                        usage=None, residual_provider_work_unknown=True)
        else:
            item.update(status='not_submitted', submission_started=False,
                        reason='request_phase_ended_before_transport_boundary',
                        usage=None, residual_provider_work_unknown=False)
        requests.append(item)
    requests.sort(key=lambda item: (
        slots[item['slot_id']]['slot_index'], item['attempt_index']))
    recovered_slots = []
    interruption = state.get('reason', 'request_phase_interrupted')
    for slot in identities:
        work = [item for item in requests if item['slot_id'] == slot['slot_id']]
        if not work or all(item['submission_started'] is False for item in work):
            reason = work[-1]['reason'] if work else interruption
            recovered_slots.append(dict(slot, status='unattempted', reason=reason))
        else:
            last = work[-1]
            status = last['status']
            if status in {'tool_calls', 'not_submitted'}:
                status = 'interrupted'
            recovered_slots.append(dict(slot, status=status, reason=interruption))
    summary_path = directory / 'summary.json'
    if summary_path.exists():
        summary_ref = reference(summary_path)
        summary = json.loads(checked(summary_ref))
        if (summary['run_id'] != identity['run_id']
                or summary['manifest_sha256'] != prepared_ref['sha256']
                or [dict(case=slot['case'], condition=slot['condition'])
                    for slot in summary['slots']] != admission['schedule']
                or len({slot['slot_id'] for slot in summary['slots']}) != len(identities)
                or any(slot['slot_id'] not in slots
                       or slot['run_id'] != identity['run_id']
                       or slot['slot_index'] != slots[slot['slot_id']]['slot_index']
                       for slot in summary['slots'])
                or summary['request_accounting']['attempts'] != len(attempts)):
            raise ValueError('retained summary differs from request evidence')
        recovered_slots = summary['slots']
        state['artifacts']['run_summary'] = summary_ref
    accounting = dict(
        reserved_requests=len(reservations), observed_attempts=len(attempts),
        observed_submissions_without_attempt=sum(
            item['submission_started'] is True and 'attempt' not in item for item in requests),
        submission_uncertain_reservations=sum(
            item['submission_started'] is None for item in requests),
        not_submitted_reservations=sum(
            item['submission_started'] is False for item in requests),
        rule=('Runner attempts retain authoritative usage and valuation. '
              'Uncertain reservations establish neither submission nor charges.'))
    state['artifacts']['request_recovery'] = save(directory.parent / 'run-recovery.json', dict(
        run_id=identity['run_id'], manifest_sha256=prepared_ref['sha256'],
        slots=recovered_slots, requests=requests, request_accounting=accounting,
        claim_limits=('A transport-boundary marker is not evidence of transmission. '
                      'Unobserved usage and residual provider work remain unknown.')))

def timed(state, phase, action):
    started_at, tick = now()
    try:
        result = action()
    except BaseException:
        state['intervals'].append(dict(phase=phase, outcome='failed',
            started_at=started_at, finished_at=now()[0],
            started_monotonic_ns=tick, finished_monotonic_ns=time.monotonic_ns()))
        raise
    state['intervals'].append(dict(phase=phase, outcome='completed',
        started_at=started_at, finished_at=now()[0],
        started_monotonic_ns=tick, finished_monotonic_ns=time.monotonic_ns()))
    return result

def job(command, directory, name, deadline):
    remaining = (deadline - time.monotonic_ns()) / 1_000_000_000
    if remaining <= 0:
        raise TimeoutError('whole-invocation deadline exhausted')
    stdout, stderr = directory / (name + '.stdout'), directory / (name + '.stderr')
    failure = None
    with stdout.open('xb') as out, stderr.open('xb') as err:
        child = subprocess.Popen(command, stdout=out, stderr=err, start_new_session=True)
        try:
            code = child.wait(timeout=remaining)
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
            code = child.returncode
            failure = (
                ('operator_interruption', 'KeyboardInterrupt')
                if isinstance(error, KeyboardInterrupt) else
                ('whole-invocation deadline exhausted during ' + name, 'TimeoutError'))
    result = dict(returncode=code, stdout=reference(stdout), stderr=reference(stderr))
    if failure:
        raise JobFailure(name, result, *failure)
    if code:
        raise JobFailure(name, result,
                         name + ' CLI refused; retained output: ' + str(stderr), 'ValueError')
    return result

def start(args):
    started_at, tick = now()
    output = Path(args.output)
    output.mkdir(exist_ok=False)
    state = dict(version=1, invocation_id=uuid4().hex, status='starting',
                 clock_identity=clock_identity(), started_at=started_at,
                 started_monotonic_ns=tick, intervals=[], artifacts={})
    save(output / 'started.json', state)
    admission, prepared_ref = None, None
    results = output / 'run'
    try:
        admission = timed(state, 'preflight', lambda: admit(
            args.spec, args.spec_sha256, args.bindings, args.bindings_sha256))
        state['invocation_seconds'] = admission['bindings']['invocation_seconds']
        deadline = tick + int(state['invocation_seconds'] * 1_000_000_000)
        state['deadline_monotonic_ns'] = deadline
        state['artifacts']['admission'] = save(output / 'admission.json', admission)
        runner = admission['runner']['path']
        prepared, results = output / 'prepared', output / 'run'
        state['artifacts']['prepare_cli'] = timed(state, 'preparation', lambda: job(
            [sys.executable, runner, 'prepare', '--spec', args.spec, '--output', str(prepared)],
            output, 'prepare', deadline))
        checked(admission['runner'])
        for dependency in admission['bindings']['dependencies']:
            checked(dependency)
        prepared_ref = reference(prepared / 'manifest.json')
        prepared_manifest = load_json(prepared_ref['path'], prepared_ref['sha256'])
        if (prepared_manifest['source_spec_sha256'] != args.spec_sha256
                or prepared_manifest['runner_sha256'] != admission['runner']['sha256']
                or prepared_manifest['schedule'] != admission['schedule']
                or prepared_manifest['limits'] != admission['spec']['limits']
                or prepared_manifest['conditions'] != admission['spec']['conditions']
                or prepared_manifest['kind'] != admission['spec']['kind']
                or [(item['id'], item['status'], item['input']['sha256'])
                    for item in prepared_manifest['cases']]
                   != [(item['id'], item['status'], item['input']['sha256'])
                       for item in admission['spec']['cases']]):
            raise ValueError('prepared manifest differs from admitted invocation')
        state['artifacts']['prepared_manifest'] = prepared_ref
        save(output / 'before-requests.json', state)
        command = [sys.executable, runner, 'run', '--prepared', str(prepared),
                   '--manifest-sha256', prepared_ref['sha256'], '--output', str(results),
                   '--deadline-monotonic-ns', str(deadline)]
        if args.local_http:
            command.append('--local-http')
        state['artifacts']['run_cli'] = timed(
            state, 'request_work', lambda: job(command, output, 'run', deadline))
        if reference(prepared / 'manifest.json') != prepared_ref:
            raise ValueError('prepared manifest changed')
        for dependency in admission['bindings']['dependencies']:
            checked(dependency)
        summary_ref = reference(results / 'summary.json')
        summary = load_json(summary_ref['path'], summary_ref['sha256'])
        actual = [dict(case=slot['case'], condition=slot['condition']) for slot in summary['slots']]
        if actual != admission['schedule'] or summary['manifest_sha256'] != prepared_ref['sha256']:
            raise ValueError('run slots do not reconcile with admission')
        slots = {slot['slot_id']: slot for slot in summary['slots']}
        if len(slots) != len(admission['schedule']):
            raise ValueError('duplicate run slot identity')
        attempt_ids = set()
        for path in sorted(results.rglob('attempt-*.json')):
            attempt = json.loads(checked(reference(path)))
            slot = slots[attempt['slot_id']]
            if (attempt['attempt_id'] in attempt_ids or attempt['run_id'] != summary['run_id']
                    or attempt['case'] != slot['case'] or attempt['condition'] != slot['condition']
                    or slot['status'] == 'unattempted' or attempt['submission_started'] is not True
                    or type(attempt['attempt_index']) is not int
                    or not 0 <= attempt['attempt_index'] < admission['spec']['limits']['requests_per_cell']):
                raise ValueError('attempt identity or submission differs')
            attempt_ids.add(attempt['attempt_id'])
        maximum = len(admission['schedule']) * admission['spec']['limits']['requests_per_cell']
        if (len(attempt_ids) > maximum
                or summary['request_accounting']['attempts'] != len(attempt_ids)):
            raise ValueError('attempt count does not reconcile')
        state['artifacts']['run_summary'] = summary_ref
        state['runner_run_id'] = summary['run_id']
        state['status'] = 'awaiting_closeout'
    except (OSError, ValueError, KeyError, TypeError, KeyboardInterrupt) as error:
        state['status'] = 'failed'
        state['failure_type'] = (error.failure_type if isinstance(error, JobFailure)
                                 else type(error).__name__)
        state['reason'] = 'operator_interruption' if isinstance(error, KeyboardInterrupt) else str(error)
        if isinstance(error, JobFailure):
            state['artifacts'][error.name + '_cli'] = error.result
    for name in ['prepare', 'run']:
        if name + '_cli' in state['artifacts']:
            continue
        streams = {stream: output / (name + '.' + stream) for stream in ['stdout', 'stderr']}
        if all(path.exists() for path in streams.values()):
            state['artifacts'][name + '_cli'] = dict(
                returncode=None, exit_status='unobserved',
                **{stream: reference(path) for stream, path in streams.items()})
    if results.exists():
        try:
            retain_request_evidence(state, results, admission, prepared_ref)
        except (OSError, ValueError, KeyError, TypeError) as error:
            state['request_evidence_failure'] = dict(
                failure_type=type(error).__name__, reason=str(error))
            if state['status'] != 'failed':
                state['failure_type'] = type(error).__name__
                state['reason'] = str(error)
            state['status'] = 'failed'
    state['checkpoint_at'], state['checkpoint_monotonic_ns'] = now()
    ref = save(output / 'state.json', state)
    print(json.dumps(dict(state=ref, status=state['status'])))
    return 0 if state['status'] == 'awaiting_closeout' else 2

def close(args):
    state = load_json(args.state, args.state_sha256)
    if state['clock_identity'] != clock_identity():
        raise ValueError('invocation clock changed')
    def verify_artifacts(value):
        if isinstance(value, dict):
            if {'path', 'sha256', 'bytes'} <= set(value):
                checked(value)
            else:
                for child in value.values():
                    verify_artifacts(child)
        elif isinstance(value, list):
            for child in value:
                verify_artifacts(child)
    verify_artifacts(state['artifacts'])
    if 'request_evidence' in state['artifacts']:
        ref = state['artifacts']['request_evidence']
        inventory = load_json(ref['path'], ref['sha256'])
        verify_artifacts(inventory)
        if request_inventory(Path(state['request_evidence_root'])) != inventory:
            raise ValueError('retained request evidence changed')
    document = load_json(args.events, args.events_sha256)
    if set(document) != {'version', 'events'} or document['version'] != 1:
        raise ValueError('invalid closeout events')
    events = document['events']
    if not isinstance(events, list):
        raise ValueError('events must be a list')
    identities = set()
    for event in events:
        if (set(event) != {'id', 'phase', 'purpose', 'recurrence', 'actor',
                          'evidence', 'measurements'}
                or event['id'] in identities or event['phase'] not in PHASES
                or event['purpose'] not in {'experiment_setup', 'experiment_evaluation',
                                            'ordinary_workflow'}
                or event['recurrence'] not in {'one_time', 'per_invocation', 'per_case',
                                               'per_attempt', 'on_change'}
                or not isinstance(event['actor'], str) or not event['actor']
                or not isinstance(event['evidence'], list)
                or not isinstance(event['measurements'], list) or not event['measurements']):
            raise ValueError('invalid ledger event')
        identities.add(event['id'])
        for evidence in event['evidence']:
            if set(evidence) != {'path', 'sha256', 'bytes', 'selector'} or not evidence['selector']:
                raise ValueError('evidence needs an unambiguous selector')
            checked(evidence)
        for measurement in event['measurements']:
            if (set(measurement) != {'name', 'value', 'unit', 'status', 'basis'}
                    or measurement['status'] not in STATUSES or not measurement['basis']
                    or not measurement['name'] or not measurement['unit']):
                raise ValueError('invalid ledger measurement')
            unknown = measurement['status'] in {'unknown', 'not_applicable', 'invalid'}
            if ((unknown and measurement['value'] is not None)
                    or (not unknown and (measurement['value'] is None or not event['evidence']))):
                raise ValueError('measurement value or evidence differs from status')
    finished_at, finished_tick = now()
    if finished_tick < state['started_monotonic_ns']:
        raise ValueError('invalid invocation clock order')
    covered = {event['phase'] for event in events}
    covered.update(interval['phase'] for interval in state['intervals'])
    missing = sorted(PHASES - covered)
    final = dict(state, closeout_events=events, missing_phase_measurements=missing,
                 closeout_events_identity=dict(path=args.events, sha256=args.events_sha256),
                 finished_at=finished_at, finished_monotonic_ns=finished_tick,
                 elapsed_ms=(finished_tick - state['started_monotonic_ns']) / 1_000_000,
                 timing_rule='elapsed span; overlapping intervals are not summed',
                 request_accounting_rule='runner records remain authoritative; not duplicated')
    expired = finished_tick > state.get('deadline_monotonic_ns', finished_tick)
    failed = state['status'] != 'awaiting_closeout'
    final['status'] = ('deadline_exceeded' if expired else
                       'closed_failed' if failed else 'closed_with_gaps')
    final['claim_limits'] = ('No completed grading, complete cost, or native-benefit claim is '
                            'established by ledger closure; use the bound evaluation evidence.')
    ref = save(args.output, final)
    print(json.dumps(dict(ledger=ref, status=final['status'])))
    return 2 if expired or failed else 0

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    starting = commands.add_parser('start')
    for name in ['spec', 'spec-sha256', 'bindings', 'bindings-sha256', 'output']:
        starting.add_argument('--' + name, required=True)
    starting.add_argument('--local-http', action='store_true')
    closing = commands.add_parser('close')
    for name in ['state', 'state-sha256', 'events', 'events-sha256', 'output']:
        closing.add_argument('--' + name, required=True)
    args = parser.parse_args()
    try:
        return start(args) if args.command == 'start' else close(args)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps(dict(status='refused', reason=str(error))))
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
