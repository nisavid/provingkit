#!/usr/bin/env python3
"""Execute every current repository-contract method in two worker processes."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import math
import os
import re
import resource
import shutil
import signal
from pathlib import Path
import subprocess
import sys
import time
import unittest


MODULE = "tests.test_validate_provingkit"


def cgroup_capacity(membership, mountinfo, available_cpus):
    """Observe affinity and every visible ancestor quota; unknown capacity stays null."""
    report = {"complete": False, "effective_cpu_capacity": None, "ancestors": [], "issues": []}
    try:
        memberships = [line.split(":", 2) for line in membership.splitlines()]
        mounts = [line.split(" - ", 1) for line in mountinfo.splitlines()]
        candidates = []
        for before, after in mounts:
            fields, filesystem = before.split(), after.split()
            version = 2 if filesystem[0] == "cgroup2" else 1
            if version == 1 and (filesystem[0] != "cgroup" or "cpu" not in filesystem[2].split(",")):
                continue
            for _, controllers, process_path in memberships:
                if (version == 2 and controllers == "") or (version == 1 and "cpu" in controllers.split(",")):
                    decode = lambda text: re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), text)
                    root, mount = Path(decode(fields[3])), Path(decode(fields[4]))
                    relative = Path(process_path).relative_to(root)
                    if ".." in relative.parts:
                        raise ValueError("cgroup membership escapes visible mount")
                    candidates.append((version, root, mount, mount / relative))
        if not candidates or not available_cpus:
            raise ValueError("CPU cgroup membership or CPU availability is unavailable")
        limits = [float(available_cpus)]
        for version, root, mount, current in candidates:
            if root != Path("/"):
                report["issues"].append(f"ancestors above mount root {root} are unavailable")
            while True:
                entry = {"path": str(current), "version": version}
                try:
                    if version == 2:
                        entry["cpu.max"] = (current / "cpu.max").read_text().strip()
                        quota, period = entry["cpu.max"].split()
                    else:
                        quota = (current / "cpu.cfs_quota_us").read_text().strip()
                        period = (current / "cpu.cfs_period_us").read_text().strip()
                        entry.update(quota=quota, period=period)
                    if int(period) <= 0:
                        raise ValueError("nonpositive quota period")
                    if quota not in {"max", "-1"}:
                        capacity = int(quota) / int(period)
                        if capacity <= 0:
                            raise ValueError("nonpositive quota")
                        limits.append(capacity)
                except FileNotFoundError:
                    if current == mount and root == Path("/") and current.is_dir():
                        entry["quota"] = "unlimited root"
                    else:
                        report["issues"].append(f"quota unavailable at {current}")
                except (OSError, ValueError) as error:
                    report["issues"].append(f"quota unreadable at {current}: {error}")
                report["ancestors"].append(entry)
                if current == mount:
                    break
                current = current.parent
        report["complete"] = not report["issues"]
        if report["complete"]:
            report["effective_cpu_capacity"] = min(limits)
    except (ValueError, IndexError) as error:
        report["issues"].append(str(error))
    return report


def cpu_capacity():
    affinity = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count()
    return cgroup_capacity(Path("/proc/self/cgroup").read_text(),
                           Path("/proc/self/mountinfo").read_text(), affinity)


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def discover(root):
    sys.path.insert(0, str(root))
    module = importlib.import_module(MODULE)
    if Path(module.__file__).resolve() != root / "tests/test_validate_provingkit.py":
        raise ValueError("test module was not loaded from the requested repository")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(module)
    if loader.errors:
        raise ValueError("test discovery failed: " + "\n".join(loader.errors))
    ids = [test.id() for test in flatten(suite)]
    if not ids:
        raise ValueError("test discovery returned no methods")
    if len(set(ids)) != len(ids):
        raise ValueError("test discovery returned duplicate method IDs")
    return suite


def select(suite, ids):
    selected = set(ids)
    return unittest.TestSuite(
        select(item, ids) if isinstance(item, unittest.TestSuite) else item
        for item in suite if isinstance(item, unittest.TestSuite) or item.id() in selected
    )


class RecordingResult(unittest.TextTestResult):
    """Retain unittest outcomes and subtests at complete-method boundaries."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
        self.current = None
        self.started_ids = []
        self.stopped_ids = []

    def startTest(self, test):
        super().startTest(test)
        self.started_ids.append(test.id())
        self.current = {
            "id": test.id(), "outcome": "incomplete", "duration_seconds": None,
            "subtests": {"success": 0, "failure": 0, "error": 0, "skip": 0},
            "skip_reasons": [],
        }
        self.records.append(self.current)
        self.started = time.monotonic()

    def stopTest(self, test):
        self.current["duration_seconds"] = time.monotonic() - self.started
        self.stopped_ids.append(test.id())
        self.current = None
        super().stopTest(test)

    def outcome(self, outcome):
        if self.current is not None and self.current["outcome"] not in {"failure", "error"}:
            self.current["outcome"] = outcome

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcome("success")

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.outcome("failure")

    def addError(self, test, error):
        super().addError(test, error)
        self.outcome("error")

    def addExpectedFailure(self, test, error):
        super().addExpectedFailure(test, error)
        self.outcome("expected_failure")

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.outcome("unexpected_success")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        if self.current is not None:
            self.current["skip_reasons"].append(reason)
            if test.id() == self.current["id"]:
                self.outcome("skip")
            else:
                self.current["subtests"]["skip"] += 1
                # unittest omits addSuccess when any subtest is skipped.
                self.outcome("success")

    def addSubTest(self, test, subtest, error):
        super().addSubTest(test, subtest, error)
        outcome = "success" if error is None else (
            "failure" if issubclass(error[0], test.failureException) else "error"
        )
        self.current["subtests"][outcome] += 1
        if error is not None:
            self.outcome(outcome)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def source_snapshot(root):
    if not (root / ".git").exists():
        return None  # Disposable command fixtures need no Git history.
    def git(*arguments):
        return subprocess.check_output(["git", "-C", str(root), *arguments])
    files = {}
    for name in git("ls-files", "-z").split(b"\0"):
        if name:
            relative = os.fsdecode(name)
            path = root / relative
            data = os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes()
            files[relative] = {"sha256": hashlib.sha256(data).hexdigest(), "mode": path.lstat().st_mode}
    return {
        "head": git("rev-parse", "HEAD").decode().strip(), "files": files,
        "retained_refs": git("for-each-ref", "refs/remotes/origin/retained/").decode(),
        "shallow": git("rev-parse", "--is-shallow-repository").decode().strip(),
    }


def signal_group(group, sig):
    try:
        os.killpg(group, sig)
        return True
    except ProcessLookupError:
        return False


def cleanup_workers(processes):
    # The interpreter leader can exit while its test subprocesses remain alive.
    # Group ownership, not leader liveness, determines cleanup responsibility.
    remaining = [process.pid for process in processes if signal_group(process.pid, signal.SIGTERM)]
    deadline = time.monotonic() + 1
    while remaining and time.monotonic() < deadline:
        remaining = [group for group in remaining if signal_group(group, 0)]
        if remaining:
            time.sleep(0.01)
    for group in remaining:
        signal_group(group, signal.SIGKILL)
    for process in processes:
        process.wait()
    groups = {process.pid for process in processes}
    deadline = time.monotonic() + 2
    while True:
        live = []
        for stat in Path("/proc").glob("[0-9]*/stat"):
            try:
                fields = stat.read_text().rsplit(")", 1)[1].split()
                if int(fields[2]) in groups and fields[0] != "Z":
                    live.append(int(stat.parent.name))
            except (FileNotFoundError, ProcessLookupError):
                continue
        if not live or time.monotonic() >= deadline:
            break
        time.sleep(0.01)
    return {"successful": not live, "process_groups": sorted(groups), "live_members": live}


def wait_workers(processes, deadline, check_cancelled):
    while any(process.poll() is None for process in processes):
        check_cancelled()
        if time.monotonic() >= deadline:
            raise TimeoutError("suite execution timed out")
        time.sleep(0.01)
    check_cancelled()
    return [process.returncode for process in processes]


def run_worker(root, output, index):
    started = time.monotonic()
    plan = json.loads((output / "plan.json").read_text())
    discovered = discover(root)
    if [test.id() for test in flatten(discovered)] != plan["ids"]:
        raise ValueError("worker discovery differs from the complete planned suite")
    suite = select(discovered, plan["workers"][index])
    runner = unittest.TextTestRunner(verbosity=2, resultclass=RecordingResult)
    result = runner.run(suite)
    own = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    report = {
        "successful": result.wasSuccessful(), "records": result.records,
        "selected_ids": plan["workers"][index], "started_ids": result.started_ids,
        "stopped_ids": result.stopped_ids, "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors),
        "unexpected_successes": len(result.unexpectedSuccesses),
        "duration_seconds": time.monotonic() - started,
        "cpu_seconds": own.ru_utime + own.ru_stime + children.ru_utime + children.ru_stime,
        "max_rss_kib": {"worker": own.ru_maxrss, "waited_children": children.ru_maxrss},
    }
    write_json(output / f"worker-{index}.json", report)
    return 0 if report["successful"] else 1


def run(root, output, timeout, hints_path):
    if output.is_relative_to(root):
        print("evidence directory must be outside the candidate repository", file=sys.stderr)
        return 1
    output.mkdir(parents=True, exist_ok=False)
    cancellation = []
    def interrupted(signum, frame):
        # The wait loop observes cancellation; handlers never interrupt cleanup.
        cancellation.append(signum)

    def check_cancelled():
        if cancellation:
            raise InterruptedError(f"suite cancelled by signal {cancellation[0]}")

    previous = {sig: signal.signal(sig, interrupted) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        status = execute(root, output, timeout, hints_path, check_cancelled)
        check_cancelled()
        return status
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        write_json(output / "result.json", {"successful": False, "error": str(error)})
        print(str(error), file=sys.stderr)
        return 1
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def execute(root, output, timeout, hints_path, check_cancelled):
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a positive finite number of seconds")
    started = time.monotonic()
    deadline = started + timeout
    capacity = cpu_capacity()
    if not capacity["complete"] or capacity["effective_cpu_capacity"] < 2:
        raise ValueError("two workers require at least two effective CPUs with complete capacity observations: " + str(capacity))
    before = source_snapshot(root)
    write_json(output / "source-before.json", before)
    write_json(output / "environment.json", {
        "python": sys.version, "executable": sys.executable,
        "distributions": sorted((d.metadata["Name"], d.version) for d in importlib.metadata.distributions()),
        "affinity": sorted(os.sched_getaffinity(0)), "cpu_capacity": capacity,
        "locale": {key: os.environ.get(key) for key in ("LANG", "LC_ALL", "TZ")},
    })
    discovery = []
    try:
        with (output / "discovery.log").open("w") as log:
            discovery.append(subprocess.Popen(
                [sys.executable, "-I", "-B", str(Path(__file__).resolve()), str(root),
                 "--output-dir", str(output), "--discover"],
                cwd=root, start_new_session=True, stdout=log, stderr=subprocess.STDOUT,
            ))
            if wait_workers(discovery, deadline, check_cancelled) != [0]:
                raise ValueError("test discovery failed: " + (output / "discovery.log").read_text())
    finally:
        cleanup = cleanup_workers(discovery)
        write_json(output / "discovery-cleanup.json", cleanup)
        if not cleanup["successful"]:
            raise RuntimeError("discovery process cleanup failed")
    check_cancelled()
    ids = json.loads((output / "discovery.json").read_text())
    hints = json.loads(hints_path.read_text())
    if not isinstance(hints, dict) or any(
        not isinstance(value, (int, float)) or isinstance(value, bool)
        or not math.isfinite(value) or value < 0 for value in hints.values()
    ):
        raise ValueError("timing hints must map method IDs to nonnegative finite seconds")
    current_hints = {key: hints[key] for key in ids if key in hints}
    fallback = max(current_hints.values(), default=1)
    estimates = {key: current_hints.get(key, fallback) for key in ids}
    workers, loads = [[], []], [0.0, 0.0]
    for key in sorted(ids, key=lambda key: (-estimates[key], key)):
        index = min(range(2), key=lambda index: (loads[index], len(workers[index]), index))
        workers[index].append(key)
        loads[index] += estimates[key]
    workers = [[key for key in ids if key in worker] for worker in workers]
    plan = {"ids": ids, "workers": workers, "estimated_seconds": loads, "cpu_capacity": capacity}
    write_json(output / "plan.json", plan)
    processes = []
    try:
        for index in range(2):
            temporary = output / f"tmp-{index}"
            temporary.mkdir()
            with (output / f"worker-{index}.log").open("w") as log:
                processes.append(subprocess.Popen(
                    [sys.executable, "-I", "-B", str(Path(__file__).resolve()), str(root),
                     "--output-dir", str(output), "--worker", str(index)],
                    cwd=root, env={**os.environ, "TMPDIR": str(temporary)}, start_new_session=True,
                    stdout=log, stderr=subprocess.STDOUT,
                ))
        codes = wait_workers(processes, deadline, check_cancelled)
    finally:
        cleanup = cleanup_workers(processes)
        write_json(output / "cleanup.json", cleanup)
        if not cleanup["successful"]:
            raise RuntimeError("worker process cleanup failed")
        for index in range(2):
            temporary = output / f"tmp-{index}"
            if temporary.exists():
                shutil.rmtree(temporary)
    check_cancelled()
    workers = [json.loads((output / f"worker-{i}.json").read_text()) for i in range(2)]
    after = source_snapshot(root)
    write_json(output / "source-after.json", after)
    if after != before:
        raise ValueError("candidate changed during suite execution")
    for worker, expected in zip(workers, plan["workers"]):
        for actual in (worker["selected_ids"], worker["started_ids"], worker["stopped_ids"],
                       [record["id"] for record in worker["records"]]):
            if len(actual) != len(set(actual)) or set(actual) != set(expected):
                raise ValueError("worker execution contains missing, duplicate, or unknown method IDs")
        if worker["started_ids"] != worker["stopped_ids"] or worker["tests_run"] != len(expected):
            raise ValueError("worker execution did not complete every selected method")
        if any(record["outcome"] == "incomplete" for record in worker["records"]):
            raise ValueError("worker execution has an incomplete method outcome")
    report = {
        "successful": all(code == 0 for code in codes), "workers": workers,
        "records": [record for worker in workers for record in worker["records"]],
        "duration_seconds": time.monotonic() - started,
        "worker_returncodes": codes,
    }
    write_json(output / "result.json", report)
    return 0 if report["successful"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=4800)
    parser.add_argument("--timing-hints", type=Path,
                        default=Path(__file__).with_name("provingkit_test_timings.json"))
    parser.add_argument("--worker", type=int, choices=(0, 1), help=argparse.SUPPRESS)
    parser.add_argument("--discover", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output_dir.resolve()
    if args.discover:
        write_json(output / "discovery.json", [test.id() for test in flatten(discover(root))])
        return 0
    return run(root, output, args.timeout_seconds, args.timing_hints) if args.worker is None else run_worker(root, output, args.worker)


if __name__ == "__main__":
    raise SystemExit(main())
