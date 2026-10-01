"""Python startup hook that puts an evaluation child's clock on the ``gh`` stub's.

:func:`install` writes ``sitecustomize.py`` into a directory the runner puts first on the child's ``PYTHONPATH``
(any ``PYTHONPATH`` the child already had follows it). Python imports ``sitecustomize`` at startup, so every Python
the agent starts loads this module, under a private name, and calls :func:`startup`, unless it runs with ``-S``,
``-E`` or ``-I``, or with a ``PYTHONPATH`` of its own that leaves the directory out. Where the stub state that
``GH_STUB_STATE_DIR`` names is reachable (the variable and the test the stub's ``date`` and ``sleep`` shims use),
:func:`activate` replaces:

* ``time.time`` and ``time.time_ns`` with the stub's clock: the wall clock plus the ``_clock_offset`` in the
  stub's ``state.json``, read under the stub's lock without applying or writing anything (see
  :func:`clock_offset`);
* ``time.sleep(n)`` with a wait on that clock: ``gh_stub.virtual_sleep``, the ``sleep`` shim's wait, runs in the
  runner's interpreter, moving the clock forward by ``n`` under the stub's lock, which applies every delayed
  response that comes due, then pausing at most 0.2 real seconds. ``time.sleep(0)``, and a value ``time.sleep``
  refuses or cannot reach, go to the real ``time.sleep``;
* ``time.gmtime``, ``time.localtime``, ``time.ctime``, ``time.asctime`` and ``time.strftime``, called without a
  time, with the same functions at the stub's clock;
* ``datetime.date`` and ``datetime.datetime`` with subclasses whose ``date.today``, ``datetime.now``,
  ``datetime.utcnow`` and ``datetime.today`` read the stub's clock. A time zone passes through as
  ``fromtimestamp`` takes it; ``isinstance`` and ``issubclass`` accept the real classes' values too; ``repr`` and
  pickling name ``datetime.date`` and ``datetime.datetime``.

``time.monotonic``, ``time.perf_counter``, ``time.process_time`` and ``time.clock_gettime`` stay real, so
subprocess timeouts and elapsed-time measurements stay honest. Where no stub state is reachable nothing changes.
Either way :func:`startup` then runs the ``sitecustomize`` it shadows, the next one on ``sys.path``, if any.

The stub never sees the replaced clock: every Python it starts, the wait behind ``time.sleep`` included, runs
without ``site`` (``gh_stub.python_command``), and the runner's own process never has the hook on its path. The
child's Python may be older than the runner's, so this module keeps to Python 3.8 syntax, and it imports little at
startup.
"""

import datetime
import os
import sys
import time

STATE_VARIABLE = "GH_STUB_STATE_DIR"
# ``time.sleep``'s own reach: a longer wait overflows its signed 64-bit count of nanoseconds.
LONGEST_SLEEP = (2 ** 63 - 1) / 1e9
SCRIPTS = os.path.dirname(os.path.realpath(__file__))
# The wait ``time.sleep`` runs without ``site``; its arguments are SCRIPTS, the state directory and JSON seconds.
WAIT_PROGRAM = ("import json, sys; sys.path.insert(0, sys.argv[1]); import gh_stub; "
                "gh_stub.virtual_sleep(sys.argv[2], json.loads(sys.argv[3]))")
LOADER = '''"""Written by stub_clock.install: tell time by the gh stub's clock where its state is reachable."""


def _stub_clock():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_stub_clock", {module!r})
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.startup({interpreter!r}, __file__)


_stub_clock()
del _stub_clock
'''

_real_time, _real_time_ns, _real_sleep = time.time, time.time_ns, time.sleep
_real_gmtime, _real_localtime, _real_ctime, _real_asctime, _real_strftime = (
    time.gmtime, time.localtime, time.ctime, time.asctime, time.strftime)
_RealDate, _RealDatetime = datetime.date, datetime.datetime
# Set by :func:`activate`.
_state_dir = _interpreter = None


def install(directory):
    """Write ``directory/sitecustomize.py``, which loads this module at a Python's startup and calls :func:`startup`
    with the current interpreter as the one ``time.sleep`` waits through; return its path."""
    import pathlib
    loader = pathlib.Path(directory) / "sitecustomize.py"
    loader.parent.mkdir(parents=True, exist_ok=True)
    loader.write_text(LOADER.format(module=os.path.join(SCRIPTS, "stub_clock.py"), interpreter=sys.executable))
    return loader


def startup(interpreter, loader):
    """Run by the ``sitecustomize`` at ``loader``: :func:`activate` where the stub state is reachable, then run the
    ``sitecustomize`` it shadows."""
    state_dir = os.environ.get(STATE_VARIABLE)
    if state_dir and os.path.isfile(os.path.join(state_dir, "state.json")):
        activate(state_dir, interpreter)
    _run_shadowed(os.path.dirname(os.path.realpath(loader)))


def activate(state_dir, interpreter):
    """Put this process's ``time`` and ``datetime`` on the stub's clock in ``state_dir``, ``time.sleep`` waiting
    through ``interpreter`` (see the module docstring)."""
    global _state_dir, _interpreter
    _state_dir, _interpreter = state_dir, interpreter
    for name, function in (("time", _time), ("time_ns", _time_ns), ("sleep", _sleep), ("gmtime", _gmtime),
                           ("localtime", _localtime), ("ctime", _ctime), ("asctime", _asctime),
                           ("strftime", _strftime)):
        real = getattr(time, name)
        # Named as the function it replaces, so tracebacks read naturally and pickling finds it by reference.
        function.__module__, function.__name__, function.__qualname__ = "time", name, name
        function.__doc__, function.__wrapped__ = real.__doc__, real
        setattr(time, name, function)
    datetime.date, datetime.datetime = _Date, _Datetime


def clock_offset(state_dir):
    """The stub clock's lead over the wall clock in seconds: ``_clock_offset`` in ``state_dir/state.json``, read
    under a shared hold of the stub's lock (``.lock``, which the stub holds exclusively while it writes)."""
    import fcntl
    import json
    lock = os.open(os.path.join(state_dir, ".lock"), os.O_RDONLY | os.O_CREAT, 0o644)
    try:
        fcntl.flock(lock, fcntl.LOCK_SH)
        with open(os.path.join(state_dir, "state.json"), "rb") as state:
            return json.load(state).get("_clock_offset") or 0
    finally:
        os.close(lock)


def _now():
    return _real_time() + clock_offset(_state_dir)


def _time():
    return _now()


def _time_ns():
    return _real_time_ns() + round(clock_offset(_state_dir) * 1_000_000_000)


def _sleep(seconds):
    if not isinstance(seconds, (int, float)) or not 0 < seconds <= LONGEST_SLEEP:
        return _real_sleep(seconds)
    import json
    import subprocess
    amount = int(seconds) if float(seconds).is_integer() else float(seconds)
    # Never killed midway, unlike ``subprocess.run`` on an exception here, so an interrupted sleep cannot leave the
    # stub's state half-written.
    wait = subprocess.Popen([_interpreter, "-S", "-c", WAIT_PROGRAM, SCRIPTS, _state_dir, json.dumps(amount)],
                            stdin=subprocess.DEVNULL)
    if wait.wait():
        raise subprocess.CalledProcessError(wait.returncode, wait.args)


def _gmtime(secs=None):
    return _real_gmtime(_now() if secs is None else secs)


def _localtime(secs=None):
    return _real_localtime(_now() if secs is None else secs)


def _ctime(secs=None):
    return _real_ctime(_now() if secs is None else secs)


def _asctime(t=None):
    return _real_asctime(_real_localtime(_now()) if t is None else t)


def _strftime(format, t=None):
    return _real_strftime(format, _real_localtime(_now()) if t is None else t)


# Each swapped-in class, and the real class it stands for.
_STANDS_FOR = {}


class _StandIn(type):
    """Metaclass of the swapped-in classes: ``isinstance`` and ``issubclass`` answer for the real class a stand-in
    replaces, so values the real class makes (``datetime.min``, results from C code) still count."""

    def __instancecheck__(cls, instance):
        real = _STANDS_FOR.get(cls)
        return isinstance(instance, real) if real else type.__instancecheck__(cls, instance)

    def __subclasscheck__(cls, subclass):
        real = _STANDS_FOR.get(cls)
        return issubclass(subclass, real) if real else type.__subclasscheck__(cls, subclass)


class _Date(_RealDate, metaclass=_StandIn):
    __slots__ = ()

    @classmethod
    def today(cls):
        return cls.fromtimestamp(_now())

    def __repr__(self):
        return _qualified(self, super().__repr__())


class _Datetime(_RealDatetime, metaclass=_StandIn):
    __slots__ = ()

    @classmethod
    def now(cls, tz=None):
        return cls.fromtimestamp(_now(), tz)

    @classmethod
    def utcnow(cls):
        return cls.fromtimestamp(_now(), datetime.timezone.utc).replace(tzinfo=None)

    @classmethod
    def today(cls):
        return cls.fromtimestamp(_now())

    def __repr__(self):
        return _qualified(self, super().__repr__())


for _stand_in, _real in ((_Date, _RealDate), (_Datetime, _RealDatetime)):
    _stand_in.__module__, _stand_in.__name__, _stand_in.__qualname__ = "datetime", _real.__name__, _real.__name__
    _STANDS_FOR[_stand_in] = _real
del _stand_in, _real


def _qualified(value, text):
    """``text``, a stand-in's own ``repr``, qualified as the real class's is (``datetime.date(...)``)."""
    return "datetime." + text if type(value) in _STANDS_FOR else text


def _run_shadowed(directory):
    """Run the ``sitecustomize`` the loader in ``directory`` shadows: the next one on ``sys.path``, if any."""
    import importlib.machinery
    import importlib.util
    path = [entry for entry in sys.path if os.path.realpath(entry or os.curdir) != directory]
    spec = importlib.machinery.PathFinder.find_spec("sitecustomize", path)
    if spec is not None and spec.loader is not None:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
