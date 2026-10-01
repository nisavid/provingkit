"""Run the frozen eight-cell packet once, with an independent local watchdog."""
import time

STARTED = time.monotonic()

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess

ORDER = ['B10', 'C10', 'C20', 'B20', 'B30', 'C30', 'C40', 'B40']


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def supervise(command, out, deadline, *, started=None):
    began = time.monotonic()
    started = began if started is None else started
    out = out.resolve()
    out.mkdir(mode=0o700)
    save(out / 'launcher-start.json', {'started_unix': time.time(),
                                     'deadline_remaining_seconds': max(0, deadline - began)})
    status = 'not_launched'
    returncode = None
    child = None
    try:
        if time.monotonic() >= deadline:
            status = 'deadline_before_launch'
        else:
            with (out / 'stdout.txt').open('xb') as stdout, (out / 'stderr.txt').open('xb') as stderr:
                child = subprocess.Popen(command, cwd=out, stdout=stdout, stderr=stderr,
                                         start_new_session=True)
                try:
                    returncode = child.wait(timeout=max(0, deadline - time.monotonic()))
                    status = 'exited'
                except subprocess.TimeoutExpired:
                    status = 'deadline'
    except BaseException:
        status = 'controller_interrupted'
        raise
    finally:
        termination_began = time.monotonic()
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            returncode = child.wait()
        reconciliation_began = time.monotonic()
        cells = []
        for cell in ORDER:
            terminal = out / 'attempts' / f'{cell}-terminal.json'
            start = out / 'attempts' / f'{cell}-start.json'
            if terminal.exists():
                try:
                    row = json.loads(terminal.read_text())
                    cell_status = row['status'] if row['status'] in ('assessed', 'failed') else 'unknown_terminal'
                except (ValueError, KeyError):
                    cell_status = 'unknown_terminal'
            else:
                cell_status = 'unknown_after_start' if start.exists() else 'unattempted'
            cells.append({'id': cell, 'status': cell_status})
        reconciliation_ended = time.monotonic()
        result = {'status': status, 'returncode': returncode, 'cells': cells,
                  'timing': {
                      'initialization_seconds': began - started,
                      'supervision_seconds': termination_began - began,
                      'termination_seconds': reconciliation_began - termination_began,
                      'reconciliation_seconds': reconciliation_ended - reconciliation_began,
                      'elapsed_through_reconciliation_seconds': reconciliation_ended - started,
                      'excludes_final_launcher_record_write': True,
                  },
                  'remote_cancellation_confirmed': False,
                  'unknown_usage_is_zero': False}
        save(out / 'launcher.json', result)
    return result


def main():
    def interrupted(signum, frame):
        raise InterruptedError('launcher interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    parser = argparse.ArgumentParser()
    for name in ('packet', 'packet-sha256', 'runner', 'runner-sha256',
                 'launcher-sha256', 'sdk', 'out'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    for path, expected in ((args.packet, args.packet_sha256),
                           (args.runner, args.runner_sha256),
                           (__file__, args.launcher_sha256)):
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError('frozen input changed')
    command = ['node', str(Path(args.runner).resolve()), 'run',
               str(Path(args.packet).resolve()), args.packet_sha256,
               str(Path(args.sdk).resolve()), str(Path(args.out).resolve())]
    result = supervise(command, Path(args.out), STARTED + 75, started=STARTED)
    print(json.dumps(result))
    return 0 if result['status'] == 'exited' and result['returncode'] == 0 and all(
        c['status'] == 'assessed' for c in result['cells']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
