#!/usr/bin/env python3
"""Coordinate isolated scheduling trials and require complete evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

RUNNER = Path(__file__).with_name("measure_provingkit_suite.py")
SERIAL_BRANCH = "ivan/ci-measure-serial"
WORKFLOW = ".github/workflows/ci-scheduling-experiment.yml"


def read_json(path):
    return json.loads(path.read_text())


def runner(*args):
    return [sys.executable, "-B", str(RUNNER), *map(str, args)]


def baseline_run(args):
    runs = [run for page in read_json(args.runs) for run in page["workflow_runs"]]
    if len(runs) != 1:
        raise ValueError("require one unique successful serial baseline for this harness revision")
    run = runs[0]
    expected = dict(head_sha=args.head, head_branch=SERIAL_BRANCH, status="completed",
                    conclusion="success", run_attempt=1, path=WORKFLOW)
    if any(run.get(key) != value for key, value in expected.items()):
        raise ValueError("baseline must be the first successful serial run of this harness revision")
    if type(run.get("id")) is not int or run["id"] <= 0:
        raise ValueError("baseline run ID must be a positive integer")
    with args.output.open("a") as stream:
        stream.write(f"run_id={run['id']}\n")


def restore_candidate(args):
    # A new owned clone receives the complete baseline ref namespace. Fetching
    # current origin refs here would change the experimental input between arms.
    if args.candidate.exists():
        raise ValueError("restore destination must not already exist")
    source = read_json(args.acquisition)["source"]
    bundle_sha256 = hashlib.sha256(args.bundle.read_bytes()).hexdigest()
    if args.bundle_digest.read_text().strip() != bundle_sha256:
        raise ValueError("bundle bytes do not match the recorded acquisition digest")
    subprocess.run(["git", "init", "--quiet", str(args.candidate)], check=True)
    subprocess.run(["git", "-C", str(args.candidate), "fetch", "--quiet", "--no-tags", "--update-head-ok",
                    str(args.bundle.resolve()), "+refs/*:refs/*"], check=True)
    subprocess.run(["git", "-C", str(args.candidate), "checkout", "--quiet", "--detach",
                    source["head"]], check=True)
    (args.candidate / ".git/ci-measurement-bundle.sha256").write_text(bundle_sha256 + "\n")
    discovery = args.acquisition.parent / "restored-discovery.json"
    subprocess.run(runner("discover", "--candidate", args.candidate,
                          "--output", discovery), check=True)
    restored = read_json(discovery)["source"]
    # The initial fetcher's checkout configuration is observed separately. Every
    # measured arm uses this same restoration path and compares its full source
    # identity, including reconstructed checkout settings, with the serial run.
    if any(restored[key] != value for key, value in source.items()
           if key not in {"git_config", "input_bundle_sha256"}):
        raise ValueError("restored candidate does not match acquired history and refs")
    if args.baseline and restored != read_json(args.baseline)["source"]:
        raise ValueError("restored candidate does not match the complete serial input")


def require_two_cpus(discovery):
    observations = discovery["environment"]["observations"]
    capacity = observations["effective_cpu_capacity"]
    if (observations["cgroup_capacity"]["complete"] is not True
            or type(capacity) not in (int, float) or not math.isfinite(capacity)
            or capacity < 2):
        raise ValueError("two processes require complete CPU observations and capacity of at least two")


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


def in_job(args):
    if read_json(args.plan)["workers"] != 2:
        raise ValueError("in-job experiment requires exactly two workers")
    if args.output_dir.resolve().is_relative_to(args.candidate.resolve()):
        raise ValueError("measurement output must be outside the candidate")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    discovery = args.output_dir / "discovery.json"
    subprocess.run(runner("discover", "--candidate", args.candidate,
                          "--output", discovery), check=True)
    require_two_cpus(read_json(discovery))
    paths = [args.output_dir / f"shard-{index}.json" for index in range(2)]
    processes, streams, codes = [], [], []
    started = time.perf_counter()
    try:
        for index, path in enumerate(paths):
            if path.exists():
                raise ValueError("worker output already exists; use a fresh result directory")
            stream = path.with_suffix(".log").open("w")
            streams.append(stream)
            processes.append(subprocess.Popen(runner(
                "run", "--candidate", args.candidate, "--plan", args.plan,
                "--shard-index", index, "--output", path), stdout=stream, stderr=stream,
                start_new_session=True))
        codes = [process.wait() for process in processes]
    finally:
        cleanup_workers(processes)
        for stream in streams:
            stream.close()
        (args.output_dir / "controller.json").write_text(json.dumps({
            "duration_seconds": time.perf_counter() - started,
            "worker_returncodes": codes,
        }, indent=2) + "\n")
    # Validate results even after an ordinary test failure to retain the reason.
    aggregate = subprocess.run(runner("aggregate", "--candidate", args.candidate,
                                     "--plan", args.plan, "--results", *paths,
                                     "--output", args.output_dir / "aggregate.json"))
    if any(code != 0 for code in codes) or aggregate.returncode:
        raise ValueError("in-job execution failed or did not produce complete results")


def separate_jobs(args):
    folders = sorted(args.input_dir.glob("measurement-shard-*"))
    expected = [args.input_dir / f"measurement-shard-{index}" for index in range(4)]
    if folders != expected or any(not folder.is_dir() for folder in folders):
        raise ValueError("require exactly four shard artifacts")
    plans = [folder / "plan.json" for folder in folders]
    if any(not plan.is_file() for plan in plans) or len({plan.read_bytes() for plan in plans}) != 1:
        raise ValueError("shard artifacts must contain identical plans")
    if read_json(plans[0])["workers"] != 4:
        raise ValueError("separate-job experiment requires exactly four workers")
    results = [folder / f"shard-{index}.json" for index, folder in enumerate(folders)]
    if any(not result.is_file() for result in results):
        raise ValueError("every shard artifact must contain its result")
    subprocess.run(runner("aggregate", "--candidate", args.candidate,
                          "--plan", plans[0], "--results", *results,
                          "--output", args.output), check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    baseline = commands.add_parser("baseline-run")
    baseline.add_argument("--runs", type=Path, required=True)
    baseline.add_argument("--head", required=True)
    baseline.add_argument("--output", type=Path, required=True)
    restore = commands.add_parser("restore-candidate")
    restore.add_argument("--candidate", type=Path, required=True)
    restore.add_argument("--bundle", type=Path, required=True)
    restore.add_argument("--bundle-digest", type=Path, required=True)
    restore.add_argument("--acquisition", type=Path, required=True)
    restore.add_argument("--baseline", type=Path)
    injob = commands.add_parser("in-job")
    injob.add_argument("--candidate", type=Path, required=True)
    injob.add_argument("--plan", type=Path, required=True)
    injob.add_argument("--output-dir", type=Path, required=True)
    separate = commands.add_parser("separate-jobs")
    separate.add_argument("--candidate", type=Path, required=True)
    separate.add_argument("--input-dir", type=Path, required=True)
    separate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        {"baseline-run": baseline_run, "restore-candidate": restore_candidate,
         "in-job": in_job, "separate-jobs": separate_jobs}[args.command](args)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
