from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import selectors
import signal
import subprocess
import tempfile
import time
import uuid
def put(path, data):
    with path.open('xb') as stream:
        stream.write(data)

def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()

def collect(command, project, attempt, label, deadline, on_line=None, begin=None):
    """Retain bounded byte chunks before parsing; terminate the child process group."""
    buffers = {'out': bytearray(), 'err': bytearray()}
    size = 0
    process = None
    exit_code = None
    delivered_stdout_bytes = 0
    terminal_callback_stdout_offset = None
    with (attempt / (label + '-stdout.log')).open('xb') as out, (attempt / (label + '-stderr.log')).open('xb') as err, (attempt / (label + '-sent.jsonl')).open('xb') as sent, (attempt / (label + '-undelivered-stdout.log')).open('xb') as undelivered, selectors.DefaultSelector() as selector:
        def send(value):
            raw = (json.dumps(value) + '\n').encode()
            sent.write(raw); sent.flush()
            process.stdin.write(raw); process.stdin.flush()
        try:
            process = subprocess.Popen(command, cwd=project, stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       start_new_session=True)
            selector.register(process.stdout, selectors.EVENT_READ, 'out')
            selector.register(process.stderr, selectors.EVENT_READ, 'err')
            if begin:
                begin(send)
            else:
                process.stdin.close()
            done = False
            while selector.get_map() and not done:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(label + ' deadline exceeded')
                for key, _ in selector.select(min(remaining, 1)):
                    raw = os.read(key.fileobj.fileno(), 4096)
                    if not raw:
                        selector.unregister(key.fileobj)
                        continue
                    kind = key.data
                    retained = raw[:max(0, 2097152 - size)]
                    target = out if kind == 'out' else err
                    target.write(retained); target.flush()
                    size += len(raw)
                    if size > 2097152:
                        raise RuntimeError(label + ' output bound exceeded; retained prefix only')
                    buffers[kind].extend(raw)
                    if kind == 'out' and on_line:
                        while b'\n' in buffers['out']:
                            line, _, tail = buffers['out'].partition(b'\n')
                            buffers['out'] = bytearray(tail)
                            delivered_stdout_bytes += len(line) + 1
                            if on_line(json.loads(line), send):
                                done = True
                                terminal_callback_stdout_offset = delivered_stdout_bytes
                                break
            if on_line and not done:
                raise RuntimeError(label + ' ended before required events')
            if not on_line:
                process.wait(timeout=max(0.01, min(5, deadline - time.monotonic())))
        finally:
            if on_line:
                undelivered.write(buffers['out'])
            if process is not None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    exit_code = process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    exit_code = process.wait(timeout=5)
                # Drain the now-terminated process without exceeding the retained byte cap.
                for key in list(selector.get_map().values()):
                    os.set_blocking(key.fileobj.fileno(), False)
                    while True:
                        try:
                            raw = os.read(key.fileobj.fileno(), 4096)
                        except BlockingIOError:
                            break
                        if not raw:
                            break
                        target = out if key.data == 'out' else err
                        retained = raw[:max(0, 2097152 - size)]
                        target.write(retained)
                        if key.data == 'out' and on_line:
                            undelivered.write(retained)
                        size += len(raw)
                put(attempt / (label + '-process.json'), encoded({'exit_code': exit_code, 'received_bytes': size,
                    'retained_prefix_limit': 2097152, 'terminal_callback_stdout_offset': terminal_callback_stdout_offset,
                    'callback_consumed_stdout_bytes': delivered_stdout_bytes,
                    'stdout_scope': 'raw bytes including undelivered tail; use callback offset for delivered evidence'}))
                for pipe in (process.stdin, process.stdout, process.stderr):
                    try:
                        pipe.close()
                    except OSError:
                        pass
    if size > 2097152:
        raise RuntimeError(label + ' output bound exceeded during shutdown; retained prefix only')
    return bytes(buffers['out']), exit_code
