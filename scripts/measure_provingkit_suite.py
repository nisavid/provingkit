#!/usr/bin/env python3
"""Measure unchanged unittest methods in a separate immutable candidate checkout."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import unittest

MODULE = "tests.test_validate_provingkit"
REQUIRED_REFS = tuple(
    f"refs/remotes/origin/retained/{name}" for name in (
        "issue-81-history-import", "agents-pr-69", "pr-11-reviewed-carrier"
    )
)
SOURCE_FILES = (
    "scripts/validate_provingkit.py", "tests/test_validate_provingkit.py",
    ".github/workflows/provingkit-source.yml",
)
CHECKOUT_SETTINGS = (
    "core.repositoryformatversion", "core.filemode", "core.bare", "core.logallrefupdates",
    "core.symlinks", "core.ignorecase", "core.autocrlf", "core.eol", "extensions.objectformat",
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def git(candidate, *arguments, input_text=None, missing_ok=False):
    result = subprocess.run(["git", "-C", str(candidate), *arguments],
                            input=input_text, text=True, capture_output=True)
    if missing_ok and result.returncode == 1:
        return None
    if result.returncode:
        raise ValueError(f"git {' '.join(arguments)}: {result.stderr.strip()}")
    return result.stdout.strip()


def source_identity(candidate, *, require_clean=True):
    if Path(git(candidate, "rev-parse", "--show-toplevel")).resolve() != candidate:
        raise ValueError("candidate must be the checkout root")
    status = git(candidate, "status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching")
    if require_clean and status:
        raise ValueError(f"candidate is not clean: {status}")
    if git(candidate, "rev-parse", "--is-shallow-repository") != "false":
        raise ValueError("candidate must have complete history, not a shallow clone")
    objects = git(candidate, "rev-list", "--objects", "--all", "HEAD", "--missing=print", "--no-object-names")
    if any(line.startswith("?") for line in objects.splitlines()):
        raise ValueError("candidate history has missing objects")
    object_ids = sorted(set(objects.splitlines()))
    inventory = git(candidate, "cat-file", "--batch-check=%(objectname) %(objecttype)",
                    input_text="\n".join(object_ids) + "\n").splitlines()
    type_counts = dict.fromkeys(("blob", "tree", "commit", "tag"), 0)
    tag_ids = []
    if len(inventory) != len(object_ids):
        raise ValueError("candidate object inventory is incomplete")
    for expected_id, line in zip(object_ids, inventory):
        object_id, object_type = line.split()
        if object_id != expected_id or object_type not in type_counts:
            raise ValueError("candidate object inventory contains a missing or unknown object")
        type_counts[object_type] += 1
        if object_type == "tag":
            tag_ids.append(object_id)
    bundle_path = candidate / git(candidate, "rev-parse", "--git-path", "ci-measurement-bundle.sha256")
    bundle_digest = bundle_path.read_text().strip() if bundle_path.exists() else None
    if bundle_digest is not None and not re.fullmatch(r"[0-9a-f]{64}", bundle_digest):
        raise ValueError("input bundle metadata must contain a lowercase SHA-256 digest")
    return {
        "head": git(candidate, "rev-parse", "HEAD"),
        "tree": git(candidate, "rev-parse", "HEAD^{tree}"),
        "status": status,
        "required_refs": {ref: git(candidate, "rev-parse", "--verify", f"{ref}^{{commit}}")
                          for ref in REQUIRED_REFS},
        "refs": git(candidate, "for-each-ref", "--format=%(refname) %(objectname)").splitlines(),
        "file_sha256": {name: hashlib.sha256((candidate / name).read_bytes()).hexdigest()
                        for name in SOURCE_FILES},
        "object_inventory": {"sha256": digest(inventory), "count": len(inventory),
                             "type_counts": type_counts, "tag_ids": tag_ids},
        "git_config": {name: git(candidate, "config", "--get", name, missing_ok=True)
                       for name in CHECKOUT_SETTINGS},
        "input_bundle_sha256": bundle_digest,
    }


def environment_identity():
    dependencies = {}
    for name in ("idna", "jsonschema", "PyYAML", "pytest"):
        try:
            dependencies[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            dependencies[name] = None
    distributions = {}
    for distribution in importlib.metadata.distributions():
        name = re.sub(r"[-_.]+", "-", distribution.metadata["Name"]).lower()
        if name in distributions:
            raise ValueError(f"duplicate installed distribution: {name}")
        distributions[name] = distribution.version
    observations = {"cpu_count": os.cpu_count(), "platform": platform.platform(),
                    "machine": platform.machine(), "cpu_affinity": None, "cgroup": {}}
    observations["hosted"] = {name: os.environ.get(name) for name in (
        "ImageOS", "ImageVersion", "RUNNER_OS", "RUNNER_ARCH", "RUNNER_ENVIRONMENT",
        "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_JOB", "GITHUB_SHA",
    )}
    if hasattr(os, "sched_getaffinity"):
        observations["cpu_affinity"] = sorted(os.sched_getaffinity(0))
    for name in (
        "/proc/self/cgroup", "/proc/self/mountinfo", "/sys/fs/cgroup/cpu.max",
        "/sys/fs/cgroup/cpu.stat", "/sys/fs/cgroup/cpuset.cpus.effective",
        "/sys/fs/cgroup/cpu/cpu.cfs_quota_us", "/sys/fs/cgroup/cpu/cpu.cfs_period_us",
    ):
        path = Path(name)
        if path.is_file():
            observations["cgroup"][name] = path.read_text()
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        observations["cpu_model"] = next(
            (line.split(":", 1)[1].strip() for line in cpuinfo.read_text().splitlines()
             if line.startswith("model name")), None
        )
    cgroup = observations["cgroup"]
    capacity = cgroup_capacity(cgroup.get("/proc/self/cgroup", ""),
                               cgroup.get("/proc/self/mountinfo", ""),
                               len(observations["cpu_affinity"]) if observations["cpu_affinity"]
                               else observations["cpu_count"])
    observations["cgroup_capacity"] = capacity
    observations["effective_cpu_capacity"] = capacity["effective_cpu_capacity"]
    return {
        "compatibility": {"python": platform.python_version(),
                          "implementation": platform.python_implementation(),
                          "dependencies": dependencies,
                          "distributions": dict(sorted(distributions.items())),
                          "git_version": git(Path.cwd(), "--version"),
                          "git_config_environment": {name: os.environ.get(name) for name in (
                              "GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL")},
                          "locale": {name: os.environ.get(name) for name in (
                              "LANG", "LANGUAGE", "LC_ALL", "LC_CTYPE", "LC_COLLATE",
                              "LC_MESSAGES", "LC_NUMERIC", "LC_TIME")}},
        "observations": observations,
    }


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


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def discover(candidate):
    # This function runs in a fresh -I -B interpreter, never in the harness's imports.
    harness = Path(__file__).resolve().parents[1]
    sys.path[:] = [str(candidate)] + [entry for entry in sys.path if entry and
                                     not Path(entry).resolve().is_relative_to(harness)]
    module = importlib.import_module(MODULE)
    expected = candidate / "tests/test_validate_provingkit.py"
    if Path(module.__file__).resolve() != expected:
        raise ValueError("test module was not imported from the candidate")
    validator = sys.modules.get("scripts.validate_provingkit")
    if validator is not None and Path(validator.__file__).resolve() != candidate / SOURCE_FILES[0]:
        raise ValueError("validator was not imported from the candidate")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(module)
    if loader.errors:
        raise ValueError("unittest discovery failed: " + "\n".join(loader.errors))
    ids = [test.id() for test in flatten(suite)]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("discovery must contain nonempty unique test IDs")
    return suite, {"ids": ids, "sha256": digest(ids)}


def cpu_usage():
    try:
        import resource
    except ImportError:
        return None
    return {
        name: {"user_seconds": usage.ru_utime, "system_seconds": usage.ru_stime}
        for name, usage in (
            ("self", resource.getrusage(resource.RUSAGE_SELF)),
            ("children", resource.getrusage(resource.RUSAGE_CHILDREN)),
        )
    }


class TimingResult(unittest.TextTestResult):
    """Keep unittest's result semantics while observing method lifetimes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
        self.started_ids = []
        self.stopped_ids = []
        self.current = None

    def startTest(self, test):
        super().startTest(test)
        self.started_ids.append(test.id())
        self.current = {
            "id": test.id(), "duration_seconds": None, "outcome": "incomplete",
            "subtests": {"success": 0, "failure": 0, "error": 0, "skip": 0},
            "skip_reasons": [],
        }
        self.records.append(self.current)
        self.started_at = time.perf_counter()

    def stopTest(self, test):
        self.current["duration_seconds"] = time.perf_counter() - self.started_at
        self.stopped_ids.append(test.id())
        self.current = None
        super().stopTest(test)

    def outcome(self, value):
        if self.current is not None:
            if self.current["outcome"] not in {"error", "failure"}:
                self.current["outcome"] = value

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcome("success")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.outcome("failure")

    def addError(self, test, err):
        super().addError(test, err)
        self.outcome("error")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        if self.current is not None:
            self.current["skip_reasons"].append(reason)
            if test.id() == self.current["id"]:
                self.outcome("skip")
            else:
                self.current["subtests"]["skip"] += 1

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.outcome("expected_failure")

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.outcome("unexpected_success")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        outcome = "success" if err is None else (
            "failure" if issubclass(err[0], test.failureException) else "error"
        )
        self.current["subtests"][outcome] += 1
        if err is not None:
            self.outcome(outcome)


def measure_suite(suite, *, stream=None):
    runner = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=TimingResult)
    cpu_before = cpu_usage()
    started = time.perf_counter()
    result = runner.run(suite)
    return {
        "successful": result.wasSuccessful(),
        "records": result.records,
        "started_ids": result.started_ids,
        "stopped_ids": result.stopped_ids,
        "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors),
        "unexpected_successes": len(result.unexpectedSuccesses),
        "skips": len(result.skipped),
        "duration_seconds": time.perf_counter() - started,
        "cpu_before": cpu_before, "cpu_after": cpu_usage(),
    }


def unique_ids(ids):
    if not isinstance(ids, list) or not ids or any(not isinstance(item, str) or not item for item in ids):
        raise ValueError("expected nonempty test ID list")
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate test ID")
    return set(ids)


def same_ids(actual, expected):
    if unique_ids(actual) != unique_ids(expected):
        raise ValueError("missing or unknown test IDs")


def validate_suite(suite):
    unique_ids(suite["ids"])
    if suite["sha256"] != digest(suite["ids"]):
        raise ValueError("discovered suite digest does not match its IDs")


def duration(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("invalid method duration")
    return value


def method_semantics(record):
    return {key: record[key] for key in ("id", "outcome", "subtests", "skip_reasons")}


def validate_run(report, expected):
    if report["schema_version"] != 1 or report["kind"] != "run" or report["successful"] is not True:
        raise ValueError("run is failed or incomplete")
    if report["source"] != report["source_after"] or not report["source"]:
        raise ValueError("candidate source changed")
    validate_suite(report["suite"])
    for key in ("selected_ids", "started_ids", "stopped_ids"):
        same_ids(report[key], expected)
    if report["started_ids"] != report["stopped_ids"]:
        raise ValueError("test starts and stops do not match")
    records = report["records"]
    same_ids([record["id"] for record in records], expected)
    if report["tests_run"] != len(expected):
        raise ValueError("unittest execution count does not match selected methods")
    if any(report[key] != 0 for key in ("failures", "errors", "unexpected_successes")):
        raise ValueError("unittest recorded failed execution")
    for record in records:
        duration(record["duration_seconds"])
        if record["outcome"] not in {"success", "skip", "expected_failure"}:
            raise ValueError(f"unsuccessful method: {record['id']}")
        counts = record["subtests"]
        if set(counts) != {"success", "failure", "error", "skip"} or any(
                type(value) is not int or value < 0 for value in counts.values()):
            raise ValueError("invalid subtest counts")
        if counts["failure"] or counts["error"]:
            raise ValueError("subtest failure or error")
        if not isinstance(record["skip_reasons"], list) or any(
                not isinstance(reason, str) for reason in record["skip_reasons"]):
            raise ValueError("invalid skip reasons")
        if record["outcome"] == "skip" and not record["skip_reasons"]:
            raise ValueError("intentional skip reason is missing")


def create_plan(baseline, workers):
    ids = baseline["suite"]["ids"]
    validate_run(baseline, ids)
    if baseline["plan_sha256"] is not None or baseline["shard_index"] != 0:
        raise ValueError("baseline must be a complete serial run")
    if type(workers) is not int or not 1 <= workers <= len(ids):
        raise ValueError("worker count must be between one and the number of methods")
    shards = [{"index": index, "ids": [], "estimated_seconds": 0.0} for index in range(workers)]
    for record in sorted(baseline["records"], key=lambda item: (-item["duration_seconds"], item["id"])):
        shard = min(shards, key=lambda item: (item["estimated_seconds"], len(item["ids"]), item["index"]))
        shard["ids"].append(record["id"])
        shard["estimated_seconds"] += record["duration_seconds"]
    # Retain unittest's discovery order within each shard and its fixture groups.
    for shard in shards:
        selected = set(shard["ids"])
        shard["ids"] = [test_id for test_id in ids if test_id in selected]
    plan = {
        "schema_version": 1, "kind": "plan", "successful": True,
        "source": baseline["source"], "suite": baseline["suite"],
        "environment": baseline["environment"], "baseline_sha256": digest(baseline),
        "expected_records": [method_semantics(record) for record in baseline["records"]],
        "workers": workers, "shards": shards,
    }
    plan["plan_sha256"] = digest(plan)
    return plan


def validate_plan(plan, source, suite, environment):
    if plan["schema_version"] != 1 or plan["kind"] != "plan" or plan["successful"] is not True:
        raise ValueError("invalid plan")
    if plan["plan_sha256"] != digest({key: value for key, value in plan.items() if key != "plan_sha256"}):
        raise ValueError("plan digest mismatch")
    validate_suite(plan["suite"])
    same_ids([record["id"] for record in plan["expected_records"]], plan["suite"]["ids"])
    if plan["source"] != source or plan["suite"] != suite:
        raise ValueError("plan candidate source or discovered suite changed")
    if plan["environment"]["compatibility"] != environment["compatibility"]:
        raise ValueError("plan environment is incompatible")
    workers = plan["workers"]
    if type(workers) is not int or not 1 <= workers <= len(suite["ids"]):
        raise ValueError("invalid plan worker count")
    shards = plan["shards"]
    indexes = [shard["index"] for shard in shards]
    if any(type(index) is not int for index in indexes) or sorted(indexes) != list(range(workers)):
        raise ValueError("missing, duplicate, or unknown plan shard")
    ids = []
    for shard in shards:
        unique_ids(shard["ids"])
        duration(shard["estimated_seconds"])
        ids.extend(shard["ids"])
    same_ids(ids, suite["ids"])


def select_suite(suite, ids):
    selected = set(ids)
    return unittest.TestSuite(
        select_suite(item, ids) if isinstance(item, unittest.TestSuite) else item
        for item in suite if isinstance(item, unittest.TestSuite) or item.id() in selected
    )


def aggregate_results(plan, results, source, suite, environment):
    validate_plan(plan, source, suite, environment)
    indexes = [result["shard_index"] for result in results]
    if any(type(index) is not int for index in indexes) or sorted(indexes) != list(range(plan["workers"])):
        raise ValueError("missing, duplicate, or unknown result shard")
    shards = {shard["index"]: shard for shard in plan["shards"]}
    records = []
    for result in results:
        validate_run(result, shards[result["shard_index"]]["ids"])
        if result["source"] != source or result["suite"] != suite:
            raise ValueError("result candidate source or discovered suite changed")
        if result["environment"]["compatibility"] != environment["compatibility"]:
            raise ValueError("result environment is incompatible")
        if result["plan_sha256"] != plan["plan_sha256"]:
            raise ValueError("result belongs to a different plan")
        records.extend(result["records"])
    same_ids([record["id"] for record in records], suite["ids"])
    actual = {record["id"]: method_semantics(record) for record in records}
    expected = {record["id"]: record for record in plan["expected_records"]}
    if actual != expected:
        changed = sorted(test_id for test_id in actual if actual[test_id] != expected[test_id])
        raise ValueError("method outcomes, subtests, or skip reasons differ from baseline: " + ", ".join(changed))
    return {
        "plan_sha256": plan["plan_sha256"], "workers": plan["workers"],
        "records": sorted(records, key=lambda record: record["id"]),
        "shard_results": [{"index": result["shard_index"], "sha256": digest(result),
                           "duration_seconds": result["duration_seconds"],
                           "environment": result["environment"]}
                          for result in sorted(results, key=lambda result: result["shard_index"])],
        "successful": True,
    }


def read_json(path):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON field: {key}")
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique_object)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("discover", "run", "aggregate"):
        subparser = commands.add_parser(command)
        subparser.add_argument("--candidate", type=Path, required=True)
        subparser.add_argument("--output", type=Path, required=True)
        if command == "run":
            subparser.add_argument("--plan", type=Path)
            subparser.add_argument("--shard-index", type=int)
        if command == "aggregate":
            subparser.add_argument("--plan", type=Path, required=True)
            subparser.add_argument("--results", type=Path, nargs="+", required=True)
    planner = commands.add_parser("plan")
    planner.add_argument("--baseline", type=Path, required=True)
    planner.add_argument("--workers", type=int, required=True)
    planner.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for name in ("baseline", "plan"):
        if getattr(args, name, None) is not None:
            setattr(args, name, getattr(args, name).resolve())
    if hasattr(args, "results"):
        args.results = [path.resolve() for path in args.results]
    candidate = args.candidate.resolve() if hasattr(args, "candidate") else None
    output = args.output.resolve()
    if candidate and Path(__file__).resolve().is_relative_to(candidate):
        parser.error("measurement harness must be outside the candidate")
    if candidate and output.is_relative_to(candidate):
        parser.error("measurement output must be outside the candidate")
    if candidate and not args.worker:
        environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        environment.pop("PYTHONPATH", None)
        return subprocess.run(
            [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--worker", *sys.argv[1:]],
            env=environment,
        ).returncode
    if args.worker and not (sys.flags.isolated and sys.dont_write_bytecode):
        parser.error("internal worker requires isolated Python with bytecode disabled")
    report = {"schema_version": 1, "kind": args.command, "successful": False}
    try:
        if args.command == "plan":
            report = create_plan(read_json(args.baseline), args.workers)
        else:
            os.chdir(candidate)
            report["source"] = source_identity(candidate)
            report["environment"] = environment_identity()
            report["successful"] = True
            suite, report["suite"] = discover(candidate)
            if args.command == "run":
                report["selected_ids"] = report["suite"]["ids"]
                report["shard_index"] = 0
                report["plan_sha256"] = None
                if (args.plan is None) != (args.shard_index is None):
                    raise ValueError("--plan and --shard-index must be supplied together")
                if args.plan:
                    plan = read_json(args.plan)
                    validate_plan(plan, report["source"], report["suite"], report["environment"])
                    shards = {shard["index"]: shard for shard in plan["shards"]}
                    if args.shard_index not in shards:
                        raise ValueError("unknown requested shard index")
                    report["selected_ids"] = shards[args.shard_index]["ids"]
                    report["shard_index"] = args.shard_index
                    report["plan_sha256"] = plan["plan_sha256"]
                    suite = select_suite(suite, report["selected_ids"])
                report.update(measure_suite(suite))
            elif args.command == "aggregate":
                report.update(aggregate_results(read_json(args.plan), [read_json(path) for path in args.results],
                                                report["source"], report["suite"], report["environment"]))
            report["source_after"] = source_identity(candidate, require_clean=False)
            if report["source_after"] != report["source"]:
                raise ValueError("candidate changed during discovery or execution")
            if args.command == "run" and report["successful"]:
                validate_run(report, report["selected_ids"])
    except Exception as error:
        report["successful"] = False
        report["error"] = f"{type(error).__name__}: {error}"
        print(report["error"], file=sys.stderr)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if report["successful"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
