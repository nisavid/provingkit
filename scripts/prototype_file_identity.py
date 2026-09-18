"""Measure the throwaway file-decision prototype; run with python -m."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from scripts import validate_provingkit
from tests.test_file_identity_prototype import FileCase, ordinary_cases
from tests.test_validate_provingkit import ProvingkitRepositoryContractTests

REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR = REPOSITORY / "scripts/validate_provingkit.py"

# Separate from timing runs: observe the real CLI without replacing its functions.
TRACE_CLI = r"""
import hashlib, json, runpy, sys
validator, repository, target = sys.argv[1:]
observations = []
def profile(frame, event, arg):
    if (event == 'call' and frame.f_code.co_filename == validator
            and frame.f_code.co_name == 'contains_historical_identity'
            and frame.f_locals['relative_path'].as_posix() == target):
        observations.append({
            'caller': frame.f_back.f_code.co_name,
            'caller_file': frame.f_back.f_code.co_filename,
            'sha256': hashlib.sha256(frame.f_locals['original_content']).hexdigest(),
        })
sys.argv = [validator, repository]
sys.setprofile(profile)
try:
    runpy.run_path(validator, run_name='__main__')
finally:
    sys.setprofile(None)
    print('PROTOTYPE_TRACE=' + json.dumps(observations), file=sys.stderr)
"""


def direct_decision(case: FileCase) -> bool | str:
    try:
        return validate_provingkit.contains_historical_identity(
            case.relative_path, case.content
        )
    except validate_provingkit.ValidationError as error:
        return str(error)


def check_cli(case: FileCase, result: subprocess.CompletedProcess[str]) -> None:
    if case.expected is False:
        if result.returncode != 0:
            raise RuntimeError(f"{case.name}: unexpected CLI failure: {result.stderr}")
    else:
        diagnostic = (
            case.expected if isinstance(case.expected, str)
            else "unallowlisted legacy repository identity: " + case.relative_path.as_posix()
        )
        if result.returncode != 1 or diagnostic not in result.stderr:
            raise RuntimeError(f"{case.name}: unexpected CLI result: {result.stderr}")


def main() -> None:
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"], cwd=REPOSITORY
    )
    if dirty:
        raise RuntimeError("Run the prototype from a clean committed worktree")
    report: dict[str, object] = {
        "source_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPOSITORY, text=True
        ).strip(),
        "source_sha256": {
            relative: hashlib.sha256((REPOSITORY / relative).read_bytes()).hexdigest()
            for relative in (
                "scripts/validate_provingkit.py", "scripts/prototype_file_identity.py",
                "tests/test_file_identity_prototype.py", "tests/test_validate_provingkit.py",
                "CONTEXT.md",
            )
        },
        "python": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": {
            name: importlib.metadata.version(name) for name in ("idna", "PyYAML")
        },
        "method": {
            "direct": "5 warm in-process batches of 100 decisions; seconds per decision",
            "cli": "1 untraced real CLI subprocess per case; clone/setup excluded",
            "trace": "Separate BOM-frontmatter CLI run; excluded from timing comparison",
        },
        "cases": [],
    }
    fixture_helper = ProvingkitRepositoryContractTests()
    for case in ordinary_cases():
        observed = direct_decision(case)
        if type(observed) is not type(case.expected) or observed != case.expected:
            raise RuntimeError(f"{case.name}: unexpected direct decision {observed!r}")
        samples = []
        for _ in range(5):
            start = time.perf_counter()
            for _ in range(100):
                direct_decision(case)
            samples.append((time.perf_counter() - start) / 100)
        with tempfile.TemporaryDirectory(prefix="provingkit-file-prototype-") as directory:
            repository = Path(directory) / "repository"
            setup_start = time.perf_counter()
            fixture_helper.clone_with_history(repository)
            fixture = repository / case.relative_path
            fixture.parent.mkdir(parents=True, exist_ok=True)
            fixture.write_bytes(case.content)
            setup_seconds = time.perf_counter() - setup_start
            start = time.perf_counter()
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), str(repository)],
                capture_output=True, text=True, timeout=300, check=False,
            )
            cli_seconds = time.perf_counter() - start
            check_cli(case, result)
            if fixture.read_bytes() != case.content:
                raise RuntimeError(f"{case.name}: original fixture bytes changed")
            content_digest = hashlib.sha256(case.content).hexdigest()
            if case.name == "bom-frontmatter":
                traced = subprocess.run(
                    [sys.executable, "-c", TRACE_CLI, str(VALIDATOR),
                     str(repository), case.relative_path.as_posix()],
                    capture_output=True, text=True, timeout=300, check=False,
                )
                check_cli(case, traced)
                lines = [line for line in traced.stderr.splitlines()
                         if line.startswith("PROTOTYPE_TRACE=")]
                if len(lines) != 1:
                    raise RuntimeError("Missing or ambiguous production trace")
                trace = json.loads(lines[0].removeprefix("PROTOTYPE_TRACE="))
                if trace != [{"caller": "_validate_historical_identities",
                              "caller_file": str(VALIDATOR), "sha256": content_digest}]:
                    raise RuntimeError("Production did not pass the original fixture bytes")
                report["production_trace"] = {
                    "case": case.name, "caller": trace[0]["caller"],
                    "callee": "contains_historical_identity",
                    "original_bytes_sha256": content_digest,
                }
            report["cases"].append({
                "name": case.name, "path": case.relative_path.as_posix(),
                "original_bytes_sha256": content_digest, "direct_result": observed,
                "direct_batch_seconds_per_call": samples,
                "direct_median_seconds": statistics.median(samples),
                "fixture_setup_seconds": setup_seconds,
                "cli_seconds": cli_seconds, "cli_returncode": result.returncode,
                "cli_stderr": result.stderr.strip(),
            })
            print(f"{case.name}: direct and CLI observations passed", file=sys.stderr)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
