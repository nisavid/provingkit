from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import uuid
def put(path, data):
    with path.open('xb') as stream:
        stream.write(data)

def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()

def collect(command, project, attempt, label, deadline, on_line=None, begin=None,
            max_output_bytes=2097152):
    """Retain bounded byte chunks before parsing; terminate the child process group."""
    if type(max_output_bytes) is not int or max_output_bytes <= 0:
        raise ValueError("positive integer output bound required")

    class _CallbackDeadline(BaseException):
        pass

    def call_with_deadline(callback, *arguments):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise _CallbackDeadline()

        previous_handler = signal.getsignal(signal.SIGALRM)
        previous_timer = signal.getitimer(signal.ITIMER_REAL)
        started = time.monotonic()

        def interrupt_callback(signum, frame):
            raise _CallbackDeadline()

        signal.signal(signal.SIGALRM, interrupt_callback)
        try:
            signal.setitimer(signal.ITIMER_REAL, remaining)
            return callback(*arguments)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)
            delay, interval = previous_timer
            if delay > 0:
                delay = max(
                    0.000001,
                    delay - (time.monotonic() - started),
                )
            signal.setitimer(signal.ITIMER_REAL, delay, interval)

    buffers = {'out': bytearray(), 'err': bytearray()}
    size = 0
    process = None
    exit_code = None
    delivered_stdout_bytes = 0
    terminal_callback_stdout_offset = None
    callback_error = None
    with (attempt / (label + '-stdout.log')).open('xb') as out, (attempt / (label + '-stderr.log')).open('xb') as err, (attempt / (label + '-sent.jsonl')).open('xb') as sent, (attempt / (label + '-undelivered-stdout.log')).open('xb') as undelivered, selectors.DefaultSelector() as selector:
        def send(value):
            raw = (json.dumps(value) + '\n').encode()
            sent.write(raw); sent.flush()
            process.stdin.write(raw); process.stdin.flush()
        def deliver_complete_stdout():
            nonlocal delivered_stdout_bytes
            nonlocal terminal_callback_stdout_offset
            nonlocal callback_error
            terminal = False
            while (
                callback_error is None
                and b'\n' in buffers['out']
            ):
                line, _, tail = buffers['out'].partition(b'\n')
                try:
                    completed = call_with_deadline(
                        on_line,
                        json.loads(line),
                        send,
                    )
                except _CallbackDeadline:
                    callback_error = TimeoutError(
                        label + ' deadline exceeded'
                    )
                    break
                except Exception as failure:
                    buffers['out'] = bytearray(tail)
                    delivered_stdout_bytes += len(line) + 1
                    callback_error = failure
                    break
                buffers['out'] = bytearray(tail)
                delivered_stdout_bytes += len(line) + 1
                if completed:
                    terminal = True
                    if terminal_callback_stdout_offset is None:
                        terminal_callback_stdout_offset = (
                            delivered_stdout_bytes
                        )
            return terminal
        try:
            process = subprocess.Popen(command, cwd=project, stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       start_new_session=True)
            selector.register(process.stdout, selectors.EVENT_READ, 'out')
            selector.register(process.stderr, selectors.EVENT_READ, 'err')
            if begin:
                try:
                    call_with_deadline(begin, send)
                except _CallbackDeadline:
                    raise TimeoutError(
                        label + ' deadline exceeded'
                    ) from None
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
                    retained = raw[:max(0, max_output_bytes - size)]
                    target = out if kind == 'out' else err
                    target.write(retained); target.flush()
                    size += len(raw)
                    if size > max_output_bytes:
                        raise RuntimeError(label + ' output bound exceeded; retained prefix only')
                    buffers[kind].extend(retained)
                    if kind == 'out' and on_line:
                        if deliver_complete_stdout():
                            done = True
                        if callback_error is not None:
                            raise callback_error
            if on_line and not done:
                raise RuntimeError(label + ' ended before required events')
            if not on_line:
                process.wait(timeout=max(0.01, min(5, deadline - time.monotonic())))
        finally:
            active_error = sys.exc_info()[0] is not None
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
                        retained = raw[:max(0, max_output_bytes - size)]
                        target.write(retained)
                        target.flush()
                        size += len(raw)
                        if key.data == 'out' and on_line:
                            buffers['out'].extend(retained)
                            deliver_complete_stdout()
                if on_line:
                    undelivered.write(buffers['out'])
                put(attempt / (label + '-process.json'), encoded({'exit_code': exit_code, 'received_bytes': size,
                    'retained_prefix_limit': max_output_bytes, 'terminal_callback_stdout_offset': terminal_callback_stdout_offset,
                    'callback_consumed_stdout_bytes': delivered_stdout_bytes,
                    'stdout_scope': 'raw bytes including undelivered tail; use callback offset for delivered evidence'}))
                for pipe in (process.stdin, process.stdout, process.stderr):
                    try:
                        pipe.close()
                    except OSError:
                        pass
                if callback_error is not None and not active_error:
                    raise callback_error
    if size > max_output_bytes:
        raise RuntimeError(label + ' output bound exceeded during shutdown; retained prefix only')
    return bytes(buffers['out']), exit_code
