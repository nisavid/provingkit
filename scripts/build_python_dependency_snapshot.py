#!/usr/bin/env python3
"""Build a dependency-submission snapshot from an existing pip resolution."""

import argparse
from decimal import Decimal
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from urllib.parse import quote

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version


ENVIRONMENT_FIELDS = {
    "implementation_name", "implementation_version", "os_name", "platform_machine",
    "platform_release", "platform_system", "platform_version", "python_full_version",
    "platform_python_implementation", "python_version", "sys_platform",
}


class SnapshotError(ValueError):
    """The supplied evidence cannot establish the requested snapshot."""


def read_report(path):
    with Path(path).open("rb") as stream:
        data = stream.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise SnapshotError("invalid pip report: input exceeds 10 MiB")
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise SnapshotError("duplicate JSON field")
            result[key] = value
        return result

    def invalid_constant(_value):
        raise SnapshotError("invalid pip report: non-finite JSON constant")

    report = json.loads(
        data.decode("utf-8"), object_pairs_hook=unique_object,
        parse_float=Decimal, parse_constant=invalid_constant,
    )
    if (not isinstance(report, dict) or report.get("version") != "1"
            or not isinstance(report.get("install"), list) or not report["install"]
            or not isinstance(report.get("environment"), dict)
            or not ENVIRONMENT_FIELDS.issubset(report["environment"])
            or any(not isinstance(report["environment"][key], str)
                   for key in ENVIRONMENT_FIELDS)):
        raise SnapshotError("invalid pip report")
    if any(len(report["environment"][key].encode("utf-8")) > 256
           for key in ENVIRONMENT_FIELDS):
        raise SnapshotError("environment value exceeds 256 bytes")
    for item in report["install"]:
        if (not isinstance(item, dict) or type(item.get("requested")) is not bool
                or item.get("is_direct") is not False
                or not isinstance(item.get("metadata"), dict)):
            raise SnapshotError("invalid pip report")
        if item.get("requested_extras", []):
            raise SnapshotError("selected extras are unsupported")
        metadata = item["metadata"]
        if (not isinstance(metadata.get("name"), str)
                or not isinstance(metadata.get("version"), str)
                or not isinstance(metadata.get("requires_dist", []), list)
                or any(not isinstance(value, str) for value in metadata.get("requires_dist", []))):
            raise SnapshotError("invalid pip report")
        if len(metadata["version"].encode("utf-8")) > 256:
            raise SnapshotError("resolved version exceeds 256 bytes")
    return report


def parse_requirement(raw):
    if len(raw.encode("utf-8")) > 128 * 1024:
        raise SnapshotError("requirement exceeds 128 KiB")
    # Counting all opening parentheses also bounds marker nesting, including
    # quoted occurrences conservatively, before the recursive parser runs.
    if raw.count("(") > 32:
        raise SnapshotError("requirement parenthesis limit exceeds 32")
    return Requirement(raw)


def read_requirements(path):
    with Path(path).open("rb") as stream:
        data = stream.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise SnapshotError("requirements inventory exceeds 1 MiB")
    requirements = {}
    for line in data.decode("utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        requirement = parse_requirement(line.strip())
        pins = list(requirement.specifier)
        if (requirement.url or requirement.marker or requirement.extras
                or len(pins) != 1 or pins[0].operator != "=="):
            raise SnapshotError("requirements inventory needs plain exact pins without selected extras")
        Version(pins[0].version)
        name = canonicalize_name(requirement.name)
        if name in requirements:
            raise SnapshotError("duplicate requirements inventory entry")
        requirements[name] = requirement
    if not requirements:
        raise SnapshotError("empty requirements inventory")
    return requirements


def satisfies(requirement, version):
    # Test the conjunction directly: constructing SpecifierSet ranges can be
    # quadratic for many exclusions when the candidate has a local version.
    return all(clause.contains(version, prereleases=True)
               for clause in requirement.specifier)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("requirements", "report", "sha", "ref", "repository", "run-id", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    if (args.ref != "refs/heads/main"
            or re.fullmatch(r"[0-9a-f]{40}", args.sha) is None
            or re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository) is None
            or re.fullmatch(r"[0-9]+", args.run_id) is None):
        raise SnapshotError("invalid source identity")
    requirements = read_requirements(args.requirements)
    report = read_report(args.report)
    resolved = {}
    versions = {}
    active_requirements = []
    for item in report["install"]:
        metadata = item["metadata"]
        name = canonicalize_name(metadata["name"], validate=True)
        if name in resolved:
            raise SnapshotError("duplicate package identity")
        versions[name] = Version(metadata["version"])
        dependencies = set()
        for raw in metadata.get("requires_dist", []):
            requirement = parse_requirement(raw)
            if requirement.url:
                raise SnapshotError("direct URL dependencies are unsupported")
            if requirement.marker is None or requirement.marker.evaluate(
                environment={**{key: report["environment"][key] for key in ENVIRONMENT_FIELDS},
                             "extra": ""},
                context="metadata",
            ):
                if requirement.extras:
                    raise SnapshotError("selected extras are unsupported")
                dependencies.add(canonicalize_name(requirement.name))
                active_requirements.append(requirement)
        resolved[name] = {
            "package_url": f"pkg:pypi/{name}@{quote(str(versions[name]), safe='')}",
            "relationship": "direct" if item["requested"] else "indirect",
            "scope": "development",
            "dependencies": sorted(dependencies),
        }
    for package in resolved.values():
        if not set(package["dependencies"]).issubset(resolved):
            raise SnapshotError("missing resolved dependency")
    if any(not satisfies(requirement, versions[canonicalize_name(requirement.name)])
           for requirement in active_requirements):
        raise SnapshotError("incompatible resolved dependency version")
    requested = {name for name, package in resolved.items() if package["relationship"] == "direct"}
    if requested != set(requirements):
        raise SnapshotError("report does not match requirements inventory")
    if any(not satisfies(requirement, versions[name])
           for name, requirement in requirements.items()):
        raise SnapshotError("resolved version does not match requirements inventory")
    reachable = set()
    pending = list(requested)
    while pending:
        name = pending.pop()
        if name not in reachable:
            reachable.add(name)
            pending.extend(resolved[name]["dependencies"])
    if reachable != set(resolved):
        raise SnapshotError("unreachable package in reported resolution")
    snapshot = {
        "version": 0, "sha": args.sha, "ref": args.ref,
        "job": {
            "id": args.run_id, "correlator": "python-validation-dependencies",
            "html_url": f"https://github.com/{args.repository}/actions/runs/{args.run_id}",
        },
        "detector": {
            "name": "provingkit-pip-report", "version": "1",
            "url": f"https://github.com/{args.repository}/blob/{args.sha}/scripts/build_python_dependency_snapshot.py",
        },
        "scanned": datetime.now(timezone.utc).isoformat(),
        "manifests": {"requirements.txt": {
            "name": "requirements.txt", "file": {"source_location": "requirements.txt"},
            "resolved": {
                package["package_url"]: {
                    **package,
                    "dependencies": [resolved[name]["package_url"]
                                     for name in package["dependencies"]],
                }
                for package in resolved.values()
            },
        }},
    }
    encoded = json.dumps(snapshot, indent=2) + "\n"
    with Path(args.output).open("x", encoding="utf-8") as stream:
        stream.write(encoded)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SnapshotError as error:
        print(f"rejected: {error}", file=sys.stderr)
        raise SystemExit(1)
    except (ValueError, TypeError, KeyError, OSError, RecursionError):
        print("rejected: invalid dependency input or unavailable output", file=sys.stderr)
        raise SystemExit(1)
