"""Synthetic control for Aeon Bell's public bound monitor interface.

Only the engine subprocess runs. Returned native/adapter argv is data.
Use a fresh directory for each construction. From the repository root, run
``python tests/praxis_fixture.py setup CASE --directory DIR``. Preserve the
returned initial bound reply and entry reference. For each issued reply, run
``python tests/praxis_fixture.py control --directory DIR --reply REPLY.json``;
this supplies one synthetic result and writes observation artifacts only when
an observe action requests them. Submit that result through the engine's
monitor continue interface using the issued continuation and synthetic time.
Tests contain the assertions; JSON recipes contain setup and control inputs.

Setup and raw engine-result controls are controller-side preparation, separate
from acceptance assertions. They do not replace createStructuredMonitorBinding,
its native result association, or semantic classification channels for actors.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


class Fixture:
    def __init__(self, recipe_path, directory, engine):
        self.recipe_path = Path(recipe_path)
        self.recipe_bytes = self.recipe_path.read_bytes()
        self.recipe = json.loads(self.recipe_bytes)
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.engine = self.directory / 'aeon_bell.py'
        source = Path(engine).read_bytes()
        self.engine.write_bytes(source)
        self.identity = {'engine_sha256': hashlib.sha256(source).hexdigest(),
                         'recipe_sha256': hashlib.sha256(self.recipe_bytes).hexdigest(),
                         'case_id': self.recipe['id']}
        self.store = self.directory / 'synthetic-store'
        self.now = self.recipe['clock']['setup_at']
        self.transcript = []
        self.registrations = []
        self.controller = Controller(self)
        options = []
        if self.recipe['binding']:
            options = ['--binding', self.directory / 'synthetic-binding.json']
        self.bound = self.command('monitor', 'bind', '--store', self.store,
                                  '--initialize-registry', '--heartbeat',
                                  'synthetic-heartbeat', *options)

    def command(self, *argv):
        argv = list(map(str, argv))
        process = subprocess.run([sys.executable, '-B', str(self.engine), *argv],
                                 capture_output=True, cwd=self.directory, timeout=20,
                                 env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        record = {'argv': argv, 'exit_code': process.returncode,
                  'stdout': process.stdout.decode(), 'stderr': process.stderr.decode()}
        self.transcript.append({'command': record})
        if process.returncode:
            raise RuntimeError(record)
        return json.loads(record['stdout'])

    def register(self, specification):
        gate = specification['gate']
        options = []
        if 'expected_open_at' in specification:
            options += ['--expected-open-at', specification['expected_open_at']]
        if 'expires_in_minutes' in specification:
            options += ['--expires-in-minutes', specification['expires_in_minutes']]
        registration = self.command('register', '--store', self.store, '--owner',
                                    'synthetic-owner', '--host', 'synthetic-host',
                                    '--task-id', specification['task_id'], '--episode',
                                    specification['episode'], '--gate-json', json.dumps(gate),
                                    '--continuation', 'Continue the synthetic fixture only.',
                                    '--now', self.now, *options)
        self.registrations.append(registration)
        return registration

    def observation(self, registration, remaining, at):
        gate = registration['gate']
        return {'gate_key': registration['gate_key'], 'status': 'ok', 'observed_at': at,
                'account': gate['account'], 'route': gate['route'],
                'buckets': [{'name': gate['bucket'], 'remaining_percent': remaining}]}

    def seed_cache(self, remaining):
        payload = {'observations': [self.observation(r, remaining, self.now)
                                    for r in self.registrations],
                   'task_states': [{'host': r['host'], 'task_id': r['task_id'],
                                    'status': 'running', 'observed_at': self.now}
                                   for r in self.registrations]}
        path = self.directory / 'synthetic-cache-input.json'
        path.write_text(json.dumps(payload) + '\n')
        self.transcript.append({'seed_input': payload})
        return self.command('cycle', '--store', self.store, '--input', path, '--now', self.now)

    def inspect(self):
        return self.command('inspect', '--store', self.store, '--now', self.now)

    def enter(self):
        return self.command('monitor', 'enter', '--entry-ref', self.bound['entry_ref'],
                            '--now', self.now)

    def submit(self, reply, result):
        self.transcript.append({'constructed_result': result, 'action': reply['action'],
                                'continuation': reply['continuation']})
        return self.command('monitor', 'continue', '--continuation', reply['continuation'],
                            '--result-json', json.dumps(result), '--now', self.now)

    def finish(self, reply):
        for _ in range(64):
            if reply['status'] == 'complete':
                return reply
            reply = self.submit(reply, self.controller.result(reply))
        raise RuntimeError('Synthetic fixture exceeded 64 actions')


class Controller:
    def __init__(self, fixture):
        self.fixture = fixture

    def result(self, reply):
        action = reply['action']
        if action['kind'] == 'observe':
            if self.fixture.recipe.get('controls', {}).get('observation') == 'adapter-failure':
                return {'exit_code': 2, 'stderr_line': 'codex status: synthetic-adapter-failure: synthetic provider unavailable'}
            argv = action['arguments']['argv']
            requests_path = Path(argv[argv.index('--requests') + 1])
            requests = json.loads(requests_path.read_text())['observation_requests']
            observations, gates = [], []
            for request in requests:
                registration = next(r for r in self.fixture.registrations
                                    if r['gate_key'] == request['gate_key'])
                mode = self.fixture.recipe.get('controls', {}).get('observation')
                if mode == 'partial' and registration['task_id'] == self.fixture.recipe['controls']['unanswered_task_id']:
                    gates.append({'gate_key': request['gate_key'], 'kind': request['kind'],
                                  'outcome': 'error', 'reason': 'error:synthetic-provider-timeout'})
                    continue
                if mode == 'held':
                    observations.append({'gate_key': request['gate_key'], 'status': 'error',
                                         'observed_at': self.fixture.now, 'reason': 'held:policy-revision-mismatch'})
                    gates.append({'gate_key': request['gate_key'], 'kind': request['kind'],
                                  'outcome': 'held', 'reason': 'held:policy-revision-mismatch'})
                    continue
                remaining = 40 if self.fixture.recipe.get('controls', {}).get('observation') == 'open' else 0
                observations.append(self.fixture.observation(registration, remaining, self.fixture.now))
                gates.append({'gate_key': request['gate_key'], 'kind': request['kind'],
                              'outcome': 'observed', 'reason': 'typed-observation'})
            artifacts = {'--output': {'observations': observations, 'task_states': []},
                         '--report': {'adapter': 'praxis-aeon-bell-codex-status', 'gates': gates}}
            record = {'action': action, 'requests': requests, 'artifacts': []}
            for flag, payload in artifacts.items():
                path = Path(argv[argv.index(flag) + 1])
                data = json.dumps(payload) + '\n'
                path.write_text(data)
                record['artifacts'].append({'path': str(path), 'bytes': data,
                                            'sha256': hashlib.sha256(data.encode()).hexdigest()})
            self.fixture.transcript.append({'constructed_observation': record})
            return {'exit_code': 0}
        if action['kind'] == 'task_read':
            status = self.fixture.recipe.get('controls', {}).get('task_states', {}).get(action['arguments']['task_id'], 'idle')
            return {'status': status, 'observed_at': self.fixture.now}
        if action['kind'] == 'send':
            return {'outcome': 'accepted', 'evidence': {'mode': 'synthetic control; no native send'}}
        if action['kind'] == 'emit':
            return {'emitted': True}
        if action['kind'] == 'heartbeat_set':
            if self.fixture.recipe.get('controls', {}).get('heartbeat') == 'unavailable':
                return {'disposition': 'unavailable', 'reason': 'synthetic heartbeat control unavailable'}
            return {'applied': True, 'next_run_at': action['arguments']['target_at']}
        raise ValueError('No synthetic result for ' + action['kind'])


def construct(recipe, directory, *, engine=None, enter=True):
    engine = engine or Path(__file__).resolve().parents[1] / 'plugins/praxis/skills/aeon-bell/scripts/aeon_bell.py'
    fixture = Fixture(recipe, directory, engine)
    for specification in fixture.recipe['registrations']:
        fixture.register(specification)
    if 'cache_remaining' in fixture.recipe:
        fixture.seed_cache(fixture.recipe['cache_remaining'])
    for specification, registration in zip(fixture.recipe['registrations'], fixture.registrations):
        if specification.get('paused'):
            fixture.command('pause', '--store', fixture.store, '--owner', 'synthetic-owner',
                            '--registration-id', registration['registration_id'], '--now', fixture.now)
    if 'prelude' in fixture.recipe:
        fixture.now = fixture.recipe['prelude']['at']
        reply = fixture.enter()
        if fixture.recipe['prelude'].get('stop_kind'):
            for _ in range(64):
                if reply['action']['kind'] == fixture.recipe['prelude']['stop_kind']:
                    break
                reply = fixture.submit(reply, fixture.controller.result(reply))
            else:
                raise RuntimeError('Synthetic prelude did not reach stop_kind')
            fixture.setup_pending = reply
        elif fixture.recipe['prelude'].get('fail_notice'):
            for _ in range(64):
                if reply['action']['purpose'] == 'notice':
                    break
                reply = fixture.submit(reply, fixture.controller.result(reply))
            else:
                raise RuntimeError('Synthetic prelude did not reach notice')
            fixture.setup_notice = reply['action']
            reply = fixture.submit(reply, {'disposition': 'failed', 'reason': 'synthetic print channel closed'})
        if not fixture.recipe['prelude'].get('stop_kind'):
            fixture.prelude_final = fixture.finish(reply)
    fixture.now = fixture.recipe['clock']['entry_at']
    fixture.before = fixture.inspect()
    fixture.initial = fixture.enter() if enter else None
    return fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    setup = commands.add_parser('setup')
    setup.add_argument('case')
    setup.add_argument('--directory', required=True)
    setup.add_argument('--engine')
    setup.add_argument('--defer-enter', action='store_true')
    control = commands.add_parser('control')
    control.add_argument('--directory', required=True)
    control.add_argument('--reply', required=True)
    args = parser.parse_args()
    directory = Path(args.directory)
    if args.command == 'setup':
        recipe = Path(__file__).resolve().parents[1] / 'evals/praxis/fixtures' / (args.case + '.json')
        fixture = construct(recipe, directory, engine=args.engine, enter=not args.defer_enter)
        entry = {'case_id': fixture.recipe['id'], 'entry_ref': fixture.bound['entry_ref'],
                 'initial': fixture.initial, 'now': fixture.now, 'engine': str(fixture.engine)}
        state = {'recipe': fixture.recipe, 'registrations': fixture.registrations,
                 'now': fixture.now, 'identity': fixture.identity}
        for name, value in [('entry.json', entry), ('control-state.json', state),
                            ('before.json', fixture.before), ('setup-transcript.json', fixture.transcript)]:
            (directory / name).write_text(json.dumps(value, indent=2) + '\n')
        print(json.dumps(entry))
    else:
        state = json.loads((directory / 'control-state.json').read_text())
        fixture = Fixture.__new__(Fixture)
        fixture.recipe = state['recipe']
        fixture.registrations = state['registrations']
        fixture.now = state['now']
        fixture.directory = directory
        fixture.transcript = []
        reply = json.loads(Path(args.reply).read_text())
        result = Controller(fixture).result(reply)
        with (directory / 'control-transcript.jsonl').open('a') as output:
            output.write(json.dumps({'action': reply['action'], 'constructed_result': result,
                                     'artifact_records': fixture.transcript}) + '\n')
        print(json.dumps(result))


if __name__ == '__main__':
    main()
