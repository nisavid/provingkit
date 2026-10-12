#!/usr/bin/env python3
"""Validate coordination metadata and project reproducible navigation data."""

import argparse
from collections import deque
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit


CLAIM_SHAPE = {
    "operation": str, "milestone": str, "stage": str, "coverage": str,
    "evidence": [str], "limits": [str], "outcome?": str,
}
SCHEMA = {
    "schema_version": int,
    "snapshot": {"revision": str, "generated_at": str, "coverage": str},
    "decisions": [str],
    "evidence": [{"id": str, "kind": str, "uri": str, "observed_at": str,
                  "limits": [str], "revision?": str, "sha256?": str}],
    "endpoints": [{"id": str, "name": str, "host": str, "surface": str,
                   "wave": int, "evidence": [str], "limits": [str]}],
    "fabrics": [{
        "id": str, "name": str, "role": str, "status": str,
        "parent": (str, type(None)), "dependencies": [str], "crosswalk": [str],
        "evidence": [str], "source_scope": str,
        "compatibility": {"status": str, "scope": str, "evidence": [str]},
        "gaps": [str], "next_check": str,
        "effort": {"active_minutes": (int, float, type(None)), "cost": (str, type(None))},
    }],
    "profiles": [{
        "id": str, "fabric": str, "channel": (str, type(None)),
        "population": str, "ownership": str, "relationship": str,
        "target_input": str, "input_semantics": str,
        "consent": {"references": [str], "limits": [str]},
        "continuity": {"idle": str, "busy": str, "restart": str},
        "assurance": str, "claims": [CLAIM_SHAPE], "gaps": [str], "next_check": str,
        "source_assessment?": {"vector": str, "evidence": [str], "limits": [str]},
    }],
    "channels": [{
        "id": str, "source": str, "target": str, "fabrics": [str], "profiles": [str],
        "caller_access": str, "target_binding": str, "evidence": [str],
        "gaps": [str], "next_check": str,
    }],
    "provenance?": dict,
}
OPERATIONS = {
    "notify": ["submitted", "receipt", "acknowledged"],
    "request-work": ["submitted", "receipt", "accepted", "executing", "output", "fulfilled"],
    "create-task": ["submitted", "addressable", "executing"],
    "inspect": ["status", "result"],
    "reply": ["synchronous-return", "later-reply"],
    "continue-task": ["submitted", "same-task-context", "replacement", "fork"],
}
STAGES = ["discovered", "source-assessed", "prototyped", "selected", "implemented", "qualified", "released", "deployed"]
COVERAGE = ["unknown", "partial", "declared", "proved", "unsuitable", "inapplicable"]
OUTCOMES = ["queued", "held", "refused", "stale", "incomplete", "unknown"]


def shape_errors(value, schema, path="catalog"):
    """Check required fields and JSON types before traversing references."""
    if isinstance(schema, dict):
        if not isinstance(value, dict):
            return [f"{path}: expected an object"]
        fields = {key.rstrip("?"): spec for key, spec in schema.items()}
        errors = [f"{path}.{key}: unknown field" for key in sorted(value.keys() - fields.keys())]
        for key, spec in schema.items():
            name = key.rstrip("?")
            if name in value:
                errors.extend(shape_errors(value[name], spec, f"{path}.{name}"))
            elif not key.endswith("?"):
                errors.append(f"{path}.{name}: required field missing")
        return errors
    if isinstance(schema, list):
        if not isinstance(value, list):
            return [f"{path}: expected an array"]
        return [error for index, item in enumerate(value)
                for error in shape_errors(item, schema[0], f"{path}[{index}]")]
    types = schema if isinstance(schema, tuple) else (schema,)
    # bool is a distinct JSON type even though Python makes it an int subclass.
    if type(value) not in types:
        return [f"{path}: invalid value type"]
    if isinstance(value, str) and not value.strip():
        return [f"{path}: expected nonempty text"]
    return []


def has_cycle(records, field):
    edges = {}
    for identity, record in records.items():
        values = record[field] if field == "dependencies" else [record[field]]
        edges[identity] = {value for value in values if value in records}
    dependents = {identity: set() for identity in records}
    for identity, dependencies in edges.items():
        for dependency in dependencies:
            dependents[dependency].add(identity)
    remaining = {identity: len(dependencies) for identity, dependencies in edges.items()}
    ready = deque(identity for identity, count in remaining.items() if count == 0)
    removed = 0
    while ready:
        dependency = ready.popleft()
        removed += 1
        for identity in dependents[dependency]:
            remaining[identity] -= 1
            if remaining[identity] == 0:
                ready.append(identity)
    return removed != len(records)


def validate(catalog):
    errors = shape_errors(catalog, SCHEMA)
    if errors:
        return errors
    indexes = {}
    for collection in ("evidence", "endpoints", "fabrics", "profiles", "channels"):
        indexes[collection] = {}
        for index, record in enumerate(catalog[collection]):
            if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", record["id"]):
                errors.append(f"{collection}[{index}].id: expected readable lowercase hyphenated identity")
            if record["id"] in indexes[collection]:
                errors.append(f"{collection}[{index}].id: duplicate identity {record['id']}")
            indexes[collection][record["id"]] = record

    def timestamp(value, path):
        try:
            if datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() is None:
                raise ValueError("timezone missing")
        except ValueError:
            errors.append(f"{path}: expected an ISO timestamp with timezone")

    timestamp(catalog["snapshot"]["generated_at"], "snapshot.generated_at")
    for index, evidence in enumerate(catalog["evidence"]):
        timestamp(evidence["observed_at"], f"evidence[{index}].observed_at")
        if not ("revision" in evidence or "sha256" in evidence):
            errors.append(f"evidence[{index}]: revision or sha256 required")
        if "sha256" in evidence and not re.fullmatch(r"[0-9a-f]{64}", evidence["sha256"]):
            errors.append(f"evidence[{index}].sha256: expected lowercase SHA-256")
    def ref(value, collection, path):
        if value not in indexes[collection]:
            errors.append(f"{path}: unknown {collection} identity {value}")

    def refs(values, collection, path):
        for index, value in enumerate(values):
            ref(value, collection, f"{path}[{index}]")

    def choice(value, choices, path):
        if value not in choices:
            errors.append(f"{path}: expected one of {', '.join(choices)}")

    def pointer(value, path, https_only=False):
        try:
            parsed = urlsplit(value)
            if parsed.scheme == "https":
                _ = parsed.port
                valid = bool(parsed.hostname) and parsed.username is None and parsed.password is None
            else:
                valid = (not https_only and not parsed.scheme and not parsed.netloc
                         and not value.startswith("/") and ".." not in Path(parsed.path).parts)
        except ValueError:
            valid = False
        if not valid:
            errors.append(f"{path}: expected public HTTPS or repository-relative pointer without credentials")

    for index, evidence in enumerate(catalog["evidence"]):
        pointer(evidence["uri"], f"evidence[{index}].uri")
        choice(evidence["kind"], ["source", "synthetic", "behavioral", "live", "review", "release", "deployment", "decision"], f"evidence[{index}].kind")
    for index, decision in enumerate(catalog["decisions"]):
        pointer(decision, f"decisions[{index}]", https_only=True)
    for index, endpoint in enumerate(catalog["endpoints"]):
        if endpoint["wave"] not in (1, 2, 3):
            errors.append(f"endpoints[{index}].wave: expected 1, 2, or 3")

    def evidence_refs(value, path):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "evidence":
                    refs(item, "evidence", f"{path}.{key}")
                else:
                    evidence_refs(item, f"{path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                evidence_refs(item, f"{path}[{index}]")

    for collection in indexes:
        for index, record in enumerate(catalog[collection]):
            evidence_refs(record, f"{collection}[{index}]")
    for index, fabric in enumerate(catalog["fabrics"]):
        choice(fabric["role"], ["actuator", "host", "protocol", "router", "observer", "presentation", "trigger", "support"], f"fabrics[{index}].role")
        choice(fabric["status"], ["discovered", "unsuitable"], f"fabrics[{index}].status")
        choice(fabric["compatibility"]["status"], ["unassessed", "assessed", "incompatible", "mixed"], f"fabrics[{index}].compatibility.status")
        if fabric["compatibility"]["status"] != "unassessed" and not fabric["compatibility"]["evidence"]:
            errors.append(f"fabrics[{index}].compatibility: assessment evidence required")
        if fabric["status"] == "unsuitable" and not fabric["gaps"]:
            errors.append(f"fabrics[{index}].gaps: unsuitable reason required")
        minutes = fabric["effort"]["active_minutes"]
        if minutes is not None and (minutes < 0 or (isinstance(minutes, float) and not math.isfinite(minutes))):
            errors.append(f"fabrics[{index}].effort.active_minutes: expected finite nonnegative minutes or null")
        if fabric["parent"] is not None:
            ref(fabric["parent"], "fabrics", f"fabrics[{index}].parent")
        refs(fabric["dependencies"], "fabrics", f"fabrics[{index}].dependencies")
    for field in ("parent", "dependencies"):
        if has_cycle(indexes["fabrics"], field):
            errors.append(f"fabrics.{field}: cycle")
    for index, profile in enumerate(catalog["profiles"]):
        path = f"profiles[{index}]"
        choice(profile["population"], ["existing", "controlled"], path + ".population")
        choice(profile["target_input"], ["exact-reference", "creation-contract"], path + ".target_input")
        if "source_assessment" in profile and not re.fullmatch(r"[SKP?U–-]{6}", profile["source_assessment"]["vector"]):
            errors.append(f"{path}.source_assessment.vector: expected six archived capability symbols")
        for number, reference in enumerate(profile["consent"]["references"]):
            pointer(reference, f"{path}.consent.references[{number}]", https_only=True)
        if profile["population"] == "existing" and profile["target_input"] != "exact-reference":
            errors.append(f"{path}.target_input: existing targets require an exact reference")
        for number, claim in enumerate(profile["claims"]):
            claim_path = f"{path}.claims[{number}]"
            for field in ("evidence", "limits"):
                if not claim[field]:
                    errors.append(f"{claim_path}.{field}: explicit {field} required")
            choice(claim["operation"], OPERATIONS, claim_path + ".operation")
            choice(claim["stage"], STAGES, claim_path + ".stage")
            choice(claim["coverage"], COVERAGE, claim_path + ".coverage")
            if "outcome" in claim:
                choice(claim["outcome"], OUTCOMES, claim_path + ".outcome")
            if claim["operation"] in OPERATIONS:
                choice(claim["milestone"], OPERATIONS[claim["operation"]], claim_path + ".milestone")
            if (profile["population"] == "existing" and claim["operation"] == "create-task"
                    and claim["coverage"] != "inapplicable"):
                errors.append(f"{claim_path}: creation of an existing addressed target is inapplicable")
            required_kind = {"qualified": "live", "released": "release", "deployed": "deployment"}.get(claim["stage"])
            if required_kind:
                kinds = {indexes["evidence"][identity]["kind"] for identity in claim["evidence"]
                         if identity in indexes["evidence"]}
                if required_kind not in kinds:
                    errors.append(f"{claim_path}: {claim['stage']} requires {required_kind} evidence")
                if profile["channel"] is None:
                    errors.append(f"{claim_path}: {claim['stage']} requires a named channel")
        ref(profile["fabric"], "fabrics", f"profiles[{index}].fabric")
        if profile["channel"] is not None:
            ref(profile["channel"], "channels", f"profiles[{index}].channel")
            bound_channel = indexes["channels"].get(profile["channel"])
            if bound_channel and profile["id"] not in bound_channel["profiles"]:
                errors.append(f"{path}: profile must be listed on its bound channel")
    pairs = set()
    for index, channel in enumerate(catalog["channels"]):
        pair = (channel["source"], channel["target"])
        if pair[0] == pair[1]:
            errors.append(f"channels[{index}]: self-pairs belong to separate controls")
        if pair in pairs:
            errors.append(f"channels[{index}]: duplicate direction")
        pairs.add(pair)
        for field in ("source", "target"):
            ref(channel[field], "endpoints", f"channels[{index}].{field}")
        for collection in ("fabrics", "profiles"):
            refs(channel[collection], collection, f"channels[{index}].{collection}")
        for identity in channel["profiles"]:
            profile = indexes["profiles"].get(identity)
            if profile and profile["channel"] not in (None, channel["id"]):
                errors.append(f"channels[{index}] {channel['id']}: profile {identity} is bound to another channel")
            if profile and profile["fabric"] not in channel["fabrics"]:
                errors.append(f"channels[{index}]: linked profile fabric must be listed on the channel")
    return errors


def project(catalog, source_sha256, through_wave):
    endpoints = sorted((endpoint for endpoint in catalog["endpoints"] if endpoint["wave"] <= through_wave),
                       key=lambda record: record["id"])
    selected = {endpoint["id"] for endpoint in endpoints}
    associations = {(channel["source"], channel["target"]): channel for channel in catalog["channels"]
                    if channel["source"] in selected and channel["target"] in selected}
    channels = []
    pair_ids = {}
    for source in endpoints:
        for target in endpoints:
            if source["id"] == target["id"]:
                continue
            pair = (source["id"], target["id"])
            if pair in associations:
                channel = dict(associations[pair], association="recorded")
            else:
                # The colon namespace cannot collide with valid catalog IDs.
                channel = {
                    "id": f"unassessed:{pair[0]}:{pair[1]}", "source": pair[0], "target": pair[1],
                    "association": "unassessed", "fabrics": [], "profiles": [], "evidence": [],
                    "caller_access": "Unassessed", "target_binding": "Unassessed",
                    "gaps": ["No direction-specific candidate association in this snapshot."],
                    "next_check": "Research caller access and target binding before associating candidates.",
                }
            pair_ids[pair] = channel["id"]
            channels.append(channel)
    return {
        "schema_version": 1, "snapshot": catalog["snapshot"], "source_sha256": source_sha256,
        "filters": {"through_wave": through_wave},
        "operations": OPERATIONS, "decisions": catalog["decisions"],
        "counts": {"endpoints": len(endpoints), "potential_channels": len(channels),
                   "associated_channels": len(associations)},
        "graph": {"nodes": endpoints, "arcs": [{key: channel[key] for key in ("id", "source", "target")}
                                                  for channel in channels]},
        "matrix": {"columns": [endpoint["id"] for endpoint in endpoints],
                   "rows": [{"source": source["id"],
                             "cells": [{"target": target["id"], "channel": pair_ids.get((source["id"], target["id"]))}
                                       for target in endpoints]} for source in endpoints]},
        "channels": channels,
        "profiles": [dict(profile, operations={operation: [claim for claim in profile["claims"]
                                                            if claim["operation"] == operation]
                                              for operation in OPERATIONS})
                     for profile in sorted(catalog["profiles"], key=lambda record: record["id"])],
        **{collection: sorted(catalog[collection], key=lambda record: record["id"])
           for collection in ("fabrics", "evidence")},
        "provenance": catalog.get("provenance", {}),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "project"])
    parser.add_argument("catalog", type=Path)
    parser.add_argument("--through-wave", type=int, choices=(1, 2, 3), default=3,
                        help="include navigation for waves 1 through this wave (project only)")
    args = parser.parse_args()
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("non-finite number is unsupported")
        return result

    def reject_constant(value):
        raise ValueError(f"non-finite JSON constant {value} is unsupported")

    try:
        with args.catalog.open("rb") as stream:
            raw = stream.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError("catalog exceeds the 8 MiB intake limit")
        catalog = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                             parse_float=finite_float, parse_constant=reject_constant)
    except (OSError, ValueError, RecursionError) as error:
        print(f"Catalog intake failed: {error}", file=sys.stderr)
        return 1
    if not isinstance(catalog, dict) or catalog.get("schema_version") != 1:
        parser.error("schema_version must be 1 on a catalog object")
    errors = validate(catalog)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if args.command == "project":
        print(json.dumps(project(catalog, hashlib.sha256(raw).hexdigest(), args.through_wave), indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print("Catalog metadata accepted; source truth and harness outcomes are not verified.")


if __name__ == "__main__":
    sys.exit(main())
