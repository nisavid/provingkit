#!/usr/bin/env python3
"""Discover immutable behavior inputs and compare their consumers across commits."""

from __future__ import annotations

import hashlib
import ast
import argparse
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
from urllib.parse import unquote, urlsplit

if __package__:
    from . import behavior_eval_receipts as core
    from . import behavior_eval_corpora as corpora
else:
    import behavior_eval_receipts as core
    import behavior_eval_corpora as corpora

DEFINITION = "release/provingkit/definition-v1.json"
INPUT_MAP = "release/behavior-eval-input-map.json"
EXPECTATION_MAP = "release/behavior-eval-expectation-map.json"
INPUT_MAPPING_FIELDS = ("source", "pointer", "owners", "role", "behavior_inputs", "dependencies")


def _mapping_applicability(entry):
    """Project behavioral consumption separately from the full reviewed binding."""
    role = entry.get("role")
    if role == "current-corpus":
        source = entry.get("source")
        return {"source": {"path": source.get("path")} if isinstance(source, dict) else source,
                "pointer": entry.get("pointer"), "owners": entry.get("owners"),
                "role": role, "behavior_inputs": entry.get("behavior_inputs")}
    if role in ("current-support", "reference-only", "retained-evidence"):
        if entry.get("behavior_inputs") == []:
            return None
        return {"owners": entry.get("owners"), "behavior_inputs": entry.get("behavior_inputs")}
    # Preserve malformed accepted declarations so selecting their owners still
    # exposes the full mapping-validation diagnosis instead of dropping them.
    return entry


class InventoryError(ValueError):
    """The source cannot establish the requested inventory or comparison."""


class Source:
    """Read committed regular blobs without executing repository code."""

    def __init__(self, repository, revision):
        self.repository = repository
        self.revision = core.revision(repository, revision)
        self.files = {}
        self._bytes = {}
        for row in core.git(repository, "ls-tree", "-rz", self.revision).split(b"\0"):
            if row:
                metadata, path = row.split(b"\t", 1)
                mode, kind, oid = metadata.decode().split()
                self.files[path.decode()] = {"mode": mode, "kind": kind, "oid": oid}

    def read(self, path):
        core.relative_path(path)
        metadata = self.files.get(path)
        if not metadata or metadata["kind"] != "blob" or metadata["mode"] not in ("100644", "100755"):
            raise InventoryError(f"committed regular input is unavailable: {path}")
        if path not in self._bytes:
            self._bytes[path] = core.source_bytes(self.repository, self.revision, path)
        return self._bytes[path]

    def json(self, path):
        return core.read_json(self.read(path))

    def identity(self, path):
        return {**self.files[path], "sha256": hashlib.sha256(self.read(path)).hexdigest()}


def _roster(source):
    definition = source.json(DEFINITION)
    members = definition.get("membership", {}).get("members")
    if not isinstance(members, list) or not members:
        raise InventoryError("the committed Kit Slate is absent")
    skills, diagnostics = {}, []
    seen = set()
    for member in members:
        plugin = member["id"]
        core.relative_path(plugin)
        if "/" in plugin or plugin in seen:
            raise InventoryError("duplicate or invalid Slate member")
        seen.add(plugin)
        topology_path = f"plugins/{plugin}/topology.json"
        topology = source.json(topology_path)
        nodes = topology.get("skills")
        if isinstance(nodes, list):
            names = [node["name"] for node in nodes]
            if len(names) != len(set(names)):
                raise InventoryError("duplicate topology skill")
            nodes = {node["name"]: node for node in nodes}
        if not isinstance(nodes, dict):
            raise InventoryError("unsupported topology roster")
        prefix = f"plugins/{plugin}/skills/"
        entrypoints = {
            path[len(prefix):-len("/SKILL.md")]
            for path in source.files
            if path.startswith(prefix) and path.endswith("/SKILL.md")
            and "/" not in path[len(prefix):-len("/SKILL.md")]
        }
        if set(nodes) != entrypoints:
            diagnostics.append({"kind": "roster-mismatch", "plugin": plugin,
                                "topology_only": sorted(set(nodes) - entrypoints),
                                "entrypoint_only": sorted(entrypoints - set(nodes))})
        for name in sorted(set(nodes) | entrypoints):
            if "/" in name or not name:
                raise InventoryError("invalid topology skill name")
            core.relative_path(name)
            skills[f"{plugin}/{name}"] = {
                "plugin": plugin, "skill": name,
                "entrypoint": prefix + name + "/SKILL.md",
                "content_lock": member["content_identity"]["path"],
                "topology_path": topology_path, "topology_node": nodes.get(name),
            }
    return skills, diagnostics


def _input_mappings(source, skills):
    if INPUT_MAP not in source.files:
        return [], [], []
    document = source.json(INPUT_MAP)
    if not isinstance(document, dict) or document.get("schema_version") != 1 or not isinstance(document.get("entries"), list):
        raise InventoryError("unsupported input mapping document")
    accepted, projected, diagnostics, seen = [], [], [], set()
    for entry in document["entries"]:
        if not isinstance(entry, dict):
            raise InventoryError("input mapping must be an object")
        if entry.get("status") != "accepted":
            continue
        # Applicability compares declarations independently from review metadata.
        # Invalid reviews still block use when the consumer is selected.
        projected.append({key: entry.get(key) for key in INPUT_MAPPING_FIELDS})
        try:
            semantic = {key: entry[key] for key in INPUT_MAPPING_FIELDS}
            path = semantic["source"]["path"]
            pointer = semantic["pointer"]
            coordinate = (path, pointer)
            if coordinate in seen:
                raise InventoryError("duplicate accepted input mapping")
            seen.add(coordinate)
            if semantic["source"]["sha256"] != source.identity(path)["sha256"]:
                raise InventoryError("stale input mapping")
            target = source.json(path)
            if pointer:
                if not pointer.startswith("/"):
                    raise InventoryError("input mapping pointer is invalid")
                for component in pointer[1:].split("/"):
                    component = component.replace("~1", "/").replace("~0", "~")
                    target = target[int(component)] if isinstance(target, list) else target[component]
            owners = semantic["owners"]
            if not isinstance(owners, list) or not owners or len(owners) != len(set(owners)) or not set(owners) <= set(skills):
                raise InventoryError("input mapping owners are outside the roster")
            if semantic["role"] not in ("current-corpus", "current-support", "reference-only", "retained-evidence"):
                raise InventoryError("unsupported input mapping role")
            for field in ("behavior_inputs", "dependencies"):
                if not isinstance(semantic[field], list):
                    raise InventoryError("input mapping paths must be arrays")
                for value in semantic[field]:
                    core.relative_path(value)
            review = entry.get("review", {})
            if review.get("decision") != "accepted" or not isinstance(review.get("reference"), str) or not review["reference"].strip() or review.get("mapping_sha256") != core.document_digest(semantic):
                raise InventoryError("input mapping has no matching reviewed decision")
            accepted.append(semantic)
        except (InventoryError, core.ReceiptError, KeyError, TypeError, ValueError, IndexError) as error:
            diagnostics.append({"code": "invalid-input-mapping", "message": str(error), "entry": entry})
    return accepted, projected, diagnostics


def _runtime_path(path):
    """Current control-plane runner's declared runtime-file selection rule."""
    parts = PurePosixPath(path).parts
    if any(part.lower() in {"__pycache__", "answer", "answers", "eval", "evals", "fixture", "fixtures", "test", "tests"} for part in parts[:-1]):
        return False
    tokens = set(re.split(r"[^a-z0-9]+", parts[-1].lower()))
    return not (tokens & {"answer", "answers"}
        or "rubric" in tokens and tokens & {"eval", "evaluation", "expected", "grader", "grading"}
        or "expected" in tokens and tokens & {"output", "response"})


def _ordinary_scope(item):
    return item.get("scope") != "production-release" or item.get("ordinary_required") is True


def _ordinary_record(record):
    return record["role"] in ("application", "trigger") and _ordinary_scope(record)


def _mapping_selects(row, record):
    return record["source"]["path"] == row["source"]["path"] and (
        not row["pointer"] or record["pointer"] == row["pointer"])


def _assign_records(records, mappings):
    for row in mappings:
        if (not isinstance(row.get("source"), dict) or not isinstance(row["source"].get("path"), str)
                or not isinstance(row.get("pointer"), str) or not isinstance(row.get("owners"), list)
                or any(not isinstance(owner, str) for owner in row["owners"])
                or row.get("role") not in ("current-corpus", "current-support", "reference-only", "retained-evidence")):
            continue
        for record in records:
            if _mapping_selects(row, record):
                record["owners"] = row["owners"]
                if row["role"] == "current-corpus":
                    record["ordinary_required"] = True
                else:
                    record["role"] = row["role"]


def _resource_inputs(source, skill, *, runtime_only=False):
    prefix = f"plugins/{skill['plugin']}/skills/{skill['skill']}/"
    pending = [path for path in source.files if path.startswith(prefix) and path.endswith(".md")
               and (not runtime_only or _runtime_path(path))]
    visited, resources = set(), set()
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        try:
            content = source.read(path).decode("utf-8")
        except (InventoryError, UnicodeError):
            continue
        for target in re.findall(r"\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)", content):
            target = target.strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), unquote(parsed.path)))
            if resolved not in source.files and re.fullmatch(r"[A-Z][A-Z0-9_]*", parsed.path):
                continue
            resources.add(resolved)
            if resolved in source.files and resolved.endswith(".md") and resolved not in visited:
                pending.append(resolved)
    return resources


def _catalog(source, skills):
    members = {skill["plugin"] for skill in skills.values()}
    documents, records, diagnostics = {}, [], []
    for path in sorted(source.files):
        parts = path.split("/")
        if not path.endswith(".json") or "fixtures" in parts:
            continue
        plugin, skill = None, None
        if path.startswith("evals/"):
            plugin = parts[1] if len(parts) > 2 and parts[1] in members else None
            if len(parts) > 4 and parts[2] == "skills":
                skill = parts[3]
        elif len(parts) > 3 and parts[0] == "plugins" and parts[1] in members and "evals" in parts:
            plugin = parts[1]
            if parts[2] == "skills" and len(parts) > 5:
                skill = parts[3]
        else:
            continue
        try:
            content = source.read(path)
            observed = corpora.inspect_document(path, content, plugin=plugin, skill=skill)
        except InventoryError as error:
            observed = {"source": {"path": path, "sha256": None}, "format": "unsupported", "role": "unsupported", "records": [],
                "references": [], "diagnostics": [{"code": "corpus-unavailable", "source": {"path": path}, "message": str(error)}]}
            corpora.apply_source_scope(path, observed)
        except (ValueError, KeyError, TypeError) as error:
            observed = {"source": {"path": path, "sha256": hashlib.sha256(content).hexdigest()},
                        "format": "unsupported", "role": "unsupported", "records": [],
                        "references": [], "diagnostics": [{"code": "malformed-corpus", "message": str(error)}]}
            corpora.apply_source_scope(path, observed)
        observed["context"] = {"plugin": plugin, "skill": skill}
        documents[path] = observed
        diagnostics.extend(observed["diagnostics"])
        for record in observed["records"]:
            owners = [owner.replace(":", "/", 1) for owner in record["owners"]]
            if record["role"] == "trigger" and not owners and plugin and skill:
                owners = [f"{plugin}/{skill}"]
            record["owners"] = owners
            record["context"] = observed["context"]
            records.append(record)
    return documents, records, diagnostics


def _projection_sources(source, skill):
    plugin, name = skill["plugin"], skill["skill"]
    validator = f"scripts/validate_{plugin.replace('-', '_')}.py"
    if validator not in source.files or plugin not in ("mergecraft", "artifact-customs", "tricritical"):
        return {}
    constants = {}
    for node in ast.parse(source.read(validator)).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                constants[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    pairs = {}
    if plugin == "mergecraft":
        target = constants.get("MARKDOWN_AUTHORING_PROJECTIONS", {}).get(name)
        if target:
            pairs[target] = constants["MARKDOWN_AUTHORING_SOURCE"]
    elif plugin == "artifact-customs":
        for filename in constants.get("SKILL_REFERENCES", {}).get(name, []):
            pairs["references/" + filename] = "references/" + filename
    else:
        for constant in ("SHARED_INPUT_BOUNDARY_PATH", "SHARED_INVOCATION_BOUNDARY_PATH"):
            if constant in constants:
                pairs[constants[constant]] = constants[constant]
        pairs["references/topology.json"] = "topology.json"
        if name in constants.get("REVIEW_OUTPUT_SKILLS", []):
            pairs[constants["SHARED_OUTPUT_CONTRACT_PATH"]] = constants["SHARED_OUTPUT_CONTRACT_PATH"]
    return {f"plugins/{plugin}/skills/{name}/{local}": f"plugins/{plugin}/{canonical}"
            for local, canonical in pairs.items()}


def _declared_resources(skill):
    node = skill["topology_node"] or {}
    paths = []
    for field in ("entrypoint", "interface"):
        if field in node:
            paths.append(node[field])
    for field in ("references", "scripts", "modules"):
        if not isinstance(node.get(field, []), list):
            raise InventoryError("topology resource declaration must be an array")
        paths.extend(node.get(field, []))
    for path in paths:
        core.relative_path(path)
    return {f"plugins/{skill['plugin']}/{path}" for path in paths}


def _link_references(source, documents, records, skills, mappings):
    """Resolve declared selectors without assigning neighboring unowned cases."""
    diagnostics, consumed, matrix_consumption, whole_inputs = [], {}, {}, {}
    for row in mappings:
        if row["role"] == "current-corpus" and not any(
                record["role"] in ("application", "trigger") and _mapping_selects(row, record)
                for record in records):
            diagnostics.append({"code": "corpus-coordinate-unresolved", "source": row["source"],
                "pointer": row["pointer"], "owners": row["owners"],
                "message": "The current-corpus mapping does not select an original application or trigger coordinate."})
    for record in records:
        scenario = record.get("scenario")
        if scenario is None:
            continue
        ordinary_owners = record["owners"] if _ordinary_scope(record) else []
        selected = [item for item in records if item["role"] == "application"
            and item["source"]["path"] == scenario["source"]
            and (item["name"] if scenario["kind"] == "skill-evals" else
                 item["key"] if scenario["kind"] == "tricritical-corpus" else item["id"]) == scenario["selector"]]
        if len(selected) != 1:
            diagnostics.append({"code": "scenario-selector-unresolved", "source": record["source"],
                "pointer": record["pointer"], "owners": record["owners"],
                "ordinary_owners": ordinary_owners,
                "scope": "ordinary" if _ordinary_scope(record) else "production-release",
                "message": "The declared scenario selector does not resolve exactly one current case."})
            continue
        selected[0]["owners"] = sorted(set(selected[0]["owners"] + ordinary_owners))
        for owner in ordinary_owners:
            consumed.setdefault(owner, set()).add(record["source"]["path"])
    for document in documents.values():
        document_owners = sorted({owner for record in document["records"] for owner in record["owners"]})
        production_scope = not _ordinary_scope(document)
        adoptions = [row for row in mappings if row["role"] == "current-corpus"
            and row["source"]["path"] == document["source"]["path"]]
        adopted = {owner for row in adoptions for owner in row["owners"]}
        if production_scope and adopted and document["format"] == "unsupported":
            diagnostics.append({"code": "unsupported-adopted-corpus", "source": document["source"],
                "owners": sorted(adopted), "message": "An explicitly required corpus has an unsupported source format."})
        for reference in document["references"]:
            declared_owners = [owner.replace(":", "/", 1) for owner in reference.get("owners", [])]
            owners = declared_owners or document_owners
            ordinary_owners = sorted({owner for row in adoptions
                if not declared_owners or any(_mapping_selects(row, record)
                    and set(record["owners"]) & set(declared_owners) for record in document["records"])
                for owner in row["owners"]}) if production_scope else owners
            path = reference["path"]
            if path not in source.files:
                problem = "reference-missing"
            elif source.files[path]["kind"] != "blob" or source.files[path]["mode"] not in ("100644", "100755"):
                problem = "reference-unavailable"
            elif reference.get("sha256") and source.identity(path)["sha256"] != reference["sha256"]:
                problem = "reference-digest-mismatch"
            else:
                problem = None
            if problem:
                diagnostics.append({"code": problem, "source": document["source"],
                    "pointer": reference["pointer"], "owners": owners,
                    "ordinary_owners": ordinary_owners,
                    "scope": "production-release" if production_scope and not ordinary_owners else "ordinary",
                    "message": "The declared referenced bytes are absent or differ from the bound digest."})
            for owner in ordinary_owners:
                consumed.setdefault(owner, set()).add(path)
                whole_inputs.setdefault(owner, set()).add(path)
        raw = document.get("raw")
        if document["format"] == "scenario-matrix":
            runtime_dependencies = {}
            for owner, paths in raw.get("runtime_dependencies", {}).items():
                runtime_dependencies.setdefault(owner.replace(":", "/", 1), set()).update(paths)
            runtime_dependencies = {owner: sorted(paths) for owner, paths in runtime_dependencies.items()}
            if not production_scope:
                # Compare consumed declarations without narrowing the full
                # matrix byte binding already recorded in consumed inputs.
                matrix_path = document["source"]["path"]
                for owner in set(document_owners) | set(runtime_dependencies):
                    consumed.setdefault(owner, set()).add(matrix_path)
                    matrix_consumption.setdefault(owner, {})[matrix_path] = {
                        "declarations": [record["raw"] for record in document["records"] if owner in record["owners"]],
                        "runtime_dependencies": runtime_dependencies.get(owner, []),
                        "companions": {},
                    }
            for owner, paths in runtime_dependencies.items():
                runtime_files = {path: [name for name in source.files if name == path or name.startswith(path + "/")]
                                 for path in paths}
                if owner not in skills:
                    diagnostics.append({"code": "unknown-owner", "source": document["source"],
                        "owners": [owner], "ordinary_owners": [] if production_scope else [owner],
                        "inputs": sorted({name for files in runtime_files.values() for name in files}),
                        "scope": "production-release" if production_scope else "ordinary",
                        "message": "Declared runtime consumer is outside the committed roster."})
                for path, files in runtime_files.items():
                    if not production_scope:
                        consumed.setdefault(owner, set()).update(files)
                        whole_inputs.setdefault(owner, set()).update(files)
                    if not files:
                        diagnostics.append({"code": "runtime-input-missing", "source": document["source"],
                            "ordinary_owners": [] if production_scope else [owner],
                            "scope": "production-release" if production_scope else "ordinary",
                            "owners": [owner], "message": "Declared runtime input is unavailable: " + path})
            declarations = {}
            for record in document["records"]:
                for owner in record["owners"]:
                    declarations.setdefault(owner, []).append(record["raw"])
            for owner, owner_declarations in declarations.items():
                pending = [companion for declaration in owner_declarations for companion in declaration.get("companions", [])]
                visited = {owner}
                while pending:
                    companion = pending.pop().replace(":", "/", 1)
                    if companion in visited:
                        continue
                    visited.add(companion)
                    if not production_scope:
                        companion_rows = declarations.get(companion)
                        matrix_consumption[owner][matrix_path]["companions"][companion] = None if companion_rows is None else {
                            "declarations": [{"entrypoint": row.get("entrypoint"), "companions": row.get("companions", [])}
                                             for row in companion_rows],
                            "runtime_dependencies": runtime_dependencies.get(companion, []),
                        }
                    if companion not in declarations or companion not in skills:
                        diagnostics.append({"code": "companion-unresolved", "source": document["source"],
                            "ordinary_owners": [] if production_scope else [owner],
                            "scope": "production-release" if production_scope else "ordinary",
                            "owners": [owner], "message": "Declared companion is absent from this matrix or roster: " + companion})
                        continue
                    companion_skill = skills[companion]
                    prefix = str(PurePosixPath(companion_skill["entrypoint"]).parent) + "/"
                    paths = {path for path in source.files if path.startswith(prefix) and _runtime_path(path)}
                    paths.add(companion_skill["entrypoint"])
                    paths.update(_resource_inputs(source, companion_skill, runtime_only=True))
                    for declared in runtime_dependencies.get(companion, []):
                        files = {path for path in source.files if (path == declared or path.startswith(declared + "/")) and _runtime_path(path)}
                        paths.update(files or {declared})
                    if not production_scope:
                        consumed.setdefault(owner, set()).update(paths)
                        whole_inputs.setdefault(owner, set()).update(paths)
                    pending.extend(nested for row in declarations[companion] for nested in row.get("companions", []))
    for owner, paths in whole_inputs.items():
        for path in paths:
            # A reference or runtime input can also consume the complete file.
            matrix_consumption.get(owner, {}).pop(path, None)
    return diagnostics, consumed, matrix_consumption


def discover(repository, revision):
    """Return the Slate's roster and explicit completeness observations at a commit."""
    source = Source(repository, revision)
    skills, diagnostics = _roster(source)
    roster_complete = not diagnostics
    mappings, projections, mapping_diagnostics = _input_mappings(source, skills)
    diagnostics.extend(mapping_diagnostics)
    documents, records, corpus_diagnostics = _catalog(source, skills)
    diagnostics.extend(corpus_diagnostics)
    reference_diagnostics, consumed, matrix_consumption = _link_references(source, documents, records, skills, mappings)
    diagnostics.extend(reference_diagnostics)
    # Applicability uses accepted declarations independent of review metadata;
    # normalization below uses only mappings whose full binding was validated.
    applicability_records = [record.copy() for record in records]
    _assign_records(applicability_records, projections)
    _assign_records(records, mappings)
    unresolved = [record for record in records if _ordinary_record(record)
                  and (not record["owners"] or not set(record["owners"]) <= set(skills))]
    for record in records:
        unknown = sorted(set(record["owners"]) - set(skills))
        if unknown:
            diagnostics.append({"code": "unknown-owner", "source": record["source"],
                "pointer": record["pointer"], "owners": unknown,
                "scope": "ordinary" if record.get("ordinary_required") else record.get("scope", "ordinary"),
                "message": "Declared consumers are outside the committed roster."})
    expectation_map = source.json(EXPECTATION_MAP) if EXPECTATION_MAP in source.files else {"schema_version": 1, "entries": []}
    entries = expectation_map.get("entries", []) if isinstance(expectation_map, dict) else []
    if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
        entries = []
    for key, skill in skills.items():
        skill["mapping_projection"] = sorted(
            [projected for row in projections
             if isinstance(row.get("owners"), list) and key in row["owners"]
             if (projected := _mapping_applicability(row)) is not None],
            key=core.canonical_bytes)
        skill["case_selection_projection"] = sorted([
            {"source": record["source"]["path"], "pointer": record["pointer"], "role": record["role"]}
            for record in applicability_records
            if key in record["owners"] and _ordinary_record(record)
        ], key=core.canonical_bytes)
        skill["diagnostics"] = [row for row in mapping_diagnostics
            if key in row["entry"].get("owners", [])]
        skill["diagnostics"].extend(row for row in reference_diagnostics if key in row.get("ordinary_owners", row["owners"]))
        for document in documents.values():
            context = document["context"]
            relevant = context["plugin"] == skill["plugin"] and context["skill"] in (None, skill["skill"])
            if relevant and document["role"] == "unsupported":
                skill["diagnostics"].extend(document["diagnostics"])
        for record in unresolved:
            if record["context"]["plugin"] in (None, skill["plugin"]):
                skill["diagnostics"].append({"code": "unresolved-owner", "source": record["source"],
                    "pointer": record["pointer"], "message": "A current record has no declared or reviewed owner."})
        selected = [record for record in records if key in record["owners"]]
        skill["records"] = selected
        skill["expectation_mapping_projection"] = corpora.mapping_projection(entries,
            [record for record in selected if _ordinary_record(record)])
        skill["projections"] = _projection_sources(source, skill)
        skill["shared_references"] = sorted(set(skill["projections"].values()))
        support = {path for path, document in documents.items()
            if document["role"] == "support" and document["context"]["plugin"] == skill["plugin"]
            and document["context"]["skill"] in (None, skill["skill"])}
        skill["dependencies"] = sorted(support | {
            path for row in mappings if key in row["owners"]
            for path in row["dependencies"] + ([row["source"]["path"]] if row["role"] == "current-support" else [])
        } | {path for path in (DEFINITION, skill["topology_path"], skill["content_lock"], INPUT_MAP, EXPECTATION_MAP)
             if path in source.files})
        try:
            declared_resources = _declared_resources(skill)
        except (InventoryError, core.ReceiptError, TypeError) as error:
            declared_resources = set()
            skill["diagnostics"].append({"code": "topology-input-invalid", "message": str(error)})
        direct_inputs = _resource_inputs(source, skill) | declared_resources | {
            path for row in mappings if key in row["owners"]
            for path in ([row["source"]["path"]] if row["role"] == "current-corpus" else []) + row["behavior_inputs"]
        }
        skill["matrix_consumption"] = {path: projection for path, projection in matrix_consumption.get(key, {}).items()
                                       if path not in direct_inputs}
        skill["behavior_inputs"] = sorted(direct_inputs | consumed.get(key, set()) | {
            path for record in selected if _ordinary_record(record)
            for path in [record["source"]["path"]] + [fixture["path"] for fixture in record["fixtures"] if fixture["path"]]
        })
        prefix = f"plugins/{skill['plugin']}/skills/{skill['skill']}/"
        inputs = set(skill["behavior_inputs"] + skill["shared_references"] + skill["dependencies"])
        inputs.update(skill["projections"])
        inputs.update(path for path in source.files if path.startswith(prefix))
        inputs.update((skill["entrypoint"], skill["topology_path"], skill["content_lock"]))
        skill["source_identities"] = {}
        for path in sorted(inputs):
            try:
                skill["source_identities"][path] = source.identity(path)
            except (InventoryError, core.ReceiptError, KeyError) as error:
                skill["diagnostics"].append({"code": "input-unavailable", "path": path,
                    "message": f"Committed regular input is unavailable: {error}"})
        for local, canonical in skill["projections"].items():
            if local in skill["source_identities"] and canonical in skill["source_identities"]:
                if skill["source_identities"][local]["sha256"] != skill["source_identities"][canonical]["sha256"]:
                    skill["diagnostics"].append({"code": "projection-bytes-mismatch",
                        "path": local, "canonical": canonical,
                        "message": "Per-skill projection differs from its declared canonical source."})
    return {"schema_version": 1, "revision": source.revision, "skills": skills,
            "roster_complete": roster_complete, "diagnostics": diagnostics,
            "documents": documents, "unresolved_records": unresolved,
            "input_mapping_projection": projections}


def normalize(repository, revision, skill):
    """Preserve selected source coordinates and report unsupported coverage explicitly."""
    observed = discover(repository, revision)
    if skill not in observed["skills"]:
        raise InventoryError("skill is outside the committed roster")
    source = Source(repository, revision)
    selected = observed["skills"][skill]
    records = [record for record in selected["records"] if _ordinary_record(record)]
    mappings = source.json(EXPECTATION_MAP) if EXPECTATION_MAP in source.files else {"schema_version": 1, "entries": []}
    documents = {record["source"]["path"]: source.read(record["source"]["path"])
                 for record in records}
    for record in records:
        for fixture in record["fixtures"]:
            if fixture["path"] in source.files:
                try:
                    documents[fixture["path"]] = source.read(fixture["path"])
                except InventoryError:
                    pass  # Discovery and normalization retain the missing-input diagnosis.
    result = corpora.normalize_records(records, mappings, documents)
    result["diagnostics"].extend(selected["diagnostics"])
    for field in ("cases", "triggers"):
        if not result[field]:
            result["diagnostics"].append({"code": "missing-" + field,
                "message": "No current " + field + " have a supported owner."})
    result.update(skill=skill, revision=revision,
                  status="unresolved" if result["diagnostics"] else "ready")
    return result


def canonical_catalog(repository, revision):
    """Read the complete Slate's skill metadata and original source identities."""
    source = Source(repository, revision)
    skills, diagnostics = _roster(source)
    if diagnostics:
        raise InventoryError("canonical catalog requires a complete committed roster")
    paths = {DEFINITION, *(
        f"plugins/{member['id']}/topology.json"
        for member in source.json(DEFINITION)["membership"]["members"])}
    members, names = [], set()
    for key, skill in sorted(skills.items()):
        path = skill["entrypoint"]
        metadata = core._probe_metadata(source.read(path).decode("utf-8"))
        if metadata["name"] in names:
            raise InventoryError("canonical catalog has duplicate unqualified skill names")
        names.add(metadata["name"])
        paths.add(path)
        members.append({"skill": key, **metadata,
                        "entrypoint": {"path": path, "sha256": source.identity(path)["sha256"]}})
    return {"revision": source.revision, "members": members,
            "source_identities": {path: source.identity(path) for path in sorted(paths)}}


def descriptor(repository, revision, skill):
    """Describe every current owned case and its complete committed input closure."""
    observed = discover(repository, revision)
    if skill not in observed["skills"]:
        return {"status": "unresolved", "revision": observed["revision"], "skill": skill,
                "descriptor": None, "cases": [], "triggers": [],
                "diagnostics": [{"code": "unknown-skill", "message": "Skill is outside the committed roster."}]}
    selected = observed["skills"][skill]
    normalized = normalize(repository, revision, skill)
    diagnostics = list(normalized["diagnostics"])
    if not observed["roster_complete"]:
        diagnostics.extend(item for item in observed["diagnostics"] if item.get("kind") == "roster-mismatch")
    catalog_inputs = set()
    if any("expected_selection" in trigger for trigger in normalized["triggers"]):
        try:
            catalog_inputs.update(canonical_catalog(repository, revision)["source_identities"])
        except (InventoryError, core.ReceiptError, UnicodeError) as error:
            diagnostics.append({"code": "catalog-unavailable", "message": str(error)})
    spec = None
    if not diagnostics:
        maps = {INPUT_MAP, EXPECTATION_MAP}
        spec = {key: selected[key] for key in ("plugin", "skill", "content_lock", "shared_references")}
        spec.update(
            dependencies=sorted(set(selected["dependencies"]) | catalog_inputs),
            behavior_inputs=sorted(set(selected["behavior_inputs"]) - maps),
            evals=normalized["cases"][0]["case_id"]["source"],
            trigger_evals=normalized["triggers"][0]["case_id"]["source"],
            closure_complete=True, corpus_format="provingkit-v1",
            case_selection=sorted([
                {"source": record["source"]["path"], "pointer": record["pointer"]}
                for record in selected["records"] if _ordinary_record(record)
            ], key=lambda row: (row["source"], row["pointer"])))
        if EXPECTATION_MAP in selected["source_identities"]:
            spec["expectation_map"] = EXPECTATION_MAP
        try:
            core.validate(spec, "skill")
            core.corpus(repository, {"candidate_revision": revision, "skill": spec})
        except core.ReceiptError as error:
            diagnostics.append({"code": "unsupported-selected-corpus", "message": str(error)})
            spec = None
    return {"status": "unresolved" if diagnostics else "ready", "revision": observed["revision"],
            "skill": skill, "descriptor": spec, "cases": normalized["cases"],
            "triggers": normalized["triggers"], "diagnostics": diagnostics}


def _ready_descriptor(repository, revision, skill):
    result = descriptor(repository, revision, skill)
    if result["status"] != "ready":
        raise InventoryError("selected inventory is unresolved: " + json.dumps(result["diagnostics"], sort_keys=True))
    return result["descriptor"]


def prepare(repository, revision, skill):
    """Freeze the full normalized inventory; do not execute an evaluation."""
    return core.prepare(repository, revision, _ready_descriptor(repository, revision, skill))


def reconcile(repository, revision, skill, results_path, processing_revision):
    """Reconcile retained observations against every current owned coordinate."""
    return core.reconcile(repository, revision, _ready_descriptor(repository, revision, skill),
                          results_path, processing_revision)


def compare(repository, base_revision, candidate_revision):
    """Select old and new consumers without embedding full discovery records."""
    base = discover(repository, base_revision)
    candidate = discover(repository, candidate_revision)
    changed = sorted(set(core.git(
        repository, "diff", "--name-only", "-z", "--no-renames",
        base_revision, candidate_revision, "--").decode().split("\0")) - {""})
    causes = {}
    for side, inventory in (("base", base), ("candidate", candidate)):
        for key, skill in inventory["skills"].items():
            prefix = f"plugins/{skill['plugin']}/skills/{skill['skill']}/"
            for path in changed:
                if path in (INPUT_MAP, EXPECTATION_MAP):
                    continue  # Per-consumer operative projections own map applicability.
                if (path.startswith(prefix) or path in skill["shared_references"]
                        or path in skill["behavior_inputs"] and path not in skill["matrix_consumption"]):
                    causes.setdefault(key, []).append({"path": path, "side": side,
                                                       "kind": "behavioral-input"})
    for key in set(base["skills"]) | set(candidate["skills"]):
        old_matrices = base["skills"].get(key, {}).get("matrix_consumption", {})
        new_matrices = candidate["skills"].get(key, {}).get("matrix_consumption", {})
        for path in sorted(set(old_matrices) | set(new_matrices)):
            if old_matrices.get(path) != new_matrices.get(path):
                causes.setdefault(key, []).append({"path": path, "side": "both", "kind": "matrix-consumption-change"})
        old = base["skills"].get(key, {}).get("mapping_projection", [])
        new = candidate["skills"].get(key, {}).get("mapping_projection", [])
        if old != new:
            causes.setdefault(key, []).append({"path": INPUT_MAP, "side": "both",
                                               "kind": "operative-mapping-change"})
        old_cases = base["skills"].get(key, {}).get("case_selection_projection", [])
        new_cases = candidate["skills"].get(key, {}).get("case_selection_projection", [])
        if INPUT_MAP in changed and old_cases != new_cases:
            causes.setdefault(key, []).append({"path": INPUT_MAP, "side": "both",
                                               "kind": "corpus-consumption-change"})
        old_rubric = base["skills"].get(key, {}).get("expectation_mapping_projection", [])
        new_rubric = candidate["skills"].get(key, {}).get("expectation_mapping_projection", [])
        if old_rubric != new_rubric:
            causes.setdefault(key, []).append({"path": EXPECTATION_MAP, "side": "both",
                "kind": "operative-expectation-change"})
        old_projections = base["skills"].get(key, {}).get("projections", {})
        new_projections = candidate["skills"].get(key, {}).get("projections", {})
        if old_projections != new_projections:
            plugin = key.split("/", 1)[0].replace("-", "_")
            causes.setdefault(key, []).append({"path": f"scripts/validate_{plugin}.py",
                "side": "both", "kind": "projection-consumption-change"})
        old_node = base["skills"].get(key, {}).get("topology_node")
        new_node = candidate["skills"].get(key, {}).get("topology_node")
        if old_node != new_node:
            causes.setdefault(key, []).append({"path": f"plugins/{key.split('/')[0]}/topology.json",
                "side": "both", "kind": "topology-consumption-change"})
    unsupported = [{"code": "removed-or-renamed-skill", "skill": key}
                   for key in sorted(set(base["skills"]) - set(candidate["skills"]))]
    complete = base["roster_complete"] and candidate["roster_complete"]
    for side, observed in (("base", base), ("candidate", candidate)):
        other = candidate if side == "base" else base
        other_mappings = {core.canonical_bytes(row) for row in other["input_mapping_projection"]}
        for row in observed["input_mapping_projection"]:
            if core.canonical_bytes(row) in other_mappings:
                continue
            owners = row.get("owners")
            if not isinstance(owners, list) or not owners or any(not isinstance(owner, str) for owner in owners):
                complete = False
                unsupported.append({"code": "unresolved-owner", "source": row.get("source"), "side": side})
            elif not set(owners) <= set(observed["skills"]):
                complete = False
                unsupported.append({"code": "unknown-owner", "source": row.get("source"),
                    "owners": sorted(set(owners) - set(observed["skills"])), "side": side})
        for diagnostic in observed["diagnostics"]:
            if (diagnostic.get("code") == "unknown-owner" and diagnostic.get("scope") != "production-release"
                    and {diagnostic["source"]["path"], *diagnostic.get("inputs", [])}.intersection(changed)):
                complete = False
                unsupported.append({**diagnostic, "side": side})
        for path, document in observed["documents"].items():
            if path in changed and document["role"] == "unsupported":
                complete = False
                unsupported.append({"code": "unsupported-corpus", "path": path, "side": side})
        for record in observed["unresolved_records"]:
            paths = {record["source"]["path"], *[item["path"] for item in record["fixtures"]]}
            if paths.intersection(changed):
                complete = False
                unsupported.append({"code": "unresolved-owner", "source": record["source"],
                    "pointer": record["pointer"], "side": side})
    return {"schema_version": 1, "status": "complete" if complete and not unsupported else "unsupported",
            "base_revision": base_revision,
            "candidate_revision": candidate_revision, "changed_paths": changed,
            "affected_skills": sorted(causes), "causes": causes,
            "selection_complete": complete, "unsupported": unsupported,
            "inventory_diagnostics": {side: observed["diagnostics"] + [
                {**row, "skill": key} for key, skill in sorted(observed["skills"].items())
                for row in skill["diagnostics"]
            ] for side, observed in (("base", base), ("candidate", candidate))},
            "inventory_summary": {side: {
                "revision": observed["revision"], "roster_complete": observed["roster_complete"],
                "skill_count": len(observed["skills"]), "document_count": len(observed["documents"]),
                "unresolved_record_count": len(observed["unresolved_records"]),
            } for side, observed in (("base", base), ("candidate", candidate))}}


def check(repository, base_revision, candidate_revision, receipt_root):
    """Check selected consumers using only regular receipt blobs committed at C.

    Inventory owns B-to-C applicability. Each core check receives C as both
    revisions and the one explicit selected skill, so whole mapping-file bytes
    cannot expand this selection. Core still checks the receipt's S-to-C closure.
    """
    receipt_root = core.relative_path(receipt_root)
    comparison = compare(repository, base_revision, candidate_revision)
    source = Source(repository, candidate_revision)
    results = []
    for key in comparison["affected_skills"]:
        described = descriptor(repository, candidate_revision, key)
        row = {"skill": key, "diagnostics": described["diagnostics"]}
        if described["status"] != "ready":
            row.update(status="fail", reason="selected inventory is unresolved")
        else:
            path = f"{receipt_root}/{key}.json"
            try:
                raw = source.read(path)
                row["receipt_source"] = {"path": path, **source.identity(path)}
                request = {"schema_version": 1, "base_revision": candidate_revision, "candidate_revision": candidate_revision,
                           "skills": [described["descriptor"]], "changed_skills": [key], "inventory_complete": True}
                checked = core.check(repository, request, {key: raw})
                row.update(checked["skills"][0])
            except (InventoryError, core.ReceiptError) as error:
                row.update(status="fail", reason=str(error))
        results.append(row)
    failed = comparison["status"] != "complete" or any(row["status"] != "pass" for row in results)
    return {"schema_version": 1, "status": "fail" if failed else "pass" if results else "not-required",
            "base_revision": base_revision, "candidate_revision": candidate_revision, "receipt_root": receipt_root,
            "coverage_basis": {"selection": "committed-inventory-comparison",
                "core_check": "candidate-as-both-revisions-with-explicit-selected-skill",
                "freshness": "evaluated-source-to-containing-commit"},
            "affected_skills": comparison["affected_skills"], "changed_paths": comparison["changed_paths"],
            "selection_complete": comparison["selection_complete"], "causes": comparison["causes"],
            "unsupported": comparison["unsupported"], "inventory_diagnostics": comparison["inventory_diagnostics"],
            "inventory_summary": comparison["inventory_summary"], "skills": results}


CORRESPONDENCE_CONTRACT = "provingkit.receipt-correspondence/v1"


def _validate_landed_context(repository, context):
    required = {"contract", "original_base", "reviewed_head", "reviewed_target", "operation",
                "consumer_revision", "procedure_revision", "receipt_root", "receipts"}
    core._correspondence_require(isinstance(context, dict) and set(context) == required,
        "request-malformed", "request", "Reviewed context fields are incomplete or unknown", status="error")
    core._correspondence_require(context["contract"] == CORRESPONDENCE_CONTRACT,
        "request-malformed", "request", "Reviewed context contract is unsupported", status="error")
    core._correspondence_require(isinstance(context["operation"], str),
        "request-malformed", "request", "Operation must be a string", status="error")
    core._correspondence_require(context["operation"] in ("squash", "rebase"),
        "operation-unsupported", "context", "Reviewed operation is unsupported")
    revisions = {field: core._correspondence_revision(repository, context[field], field)
        for field in ("original_base", "reviewed_head", "reviewed_target", "consumer_revision", "procedure_revision")}
    root = core.relative_path(context["receipt_root"])
    bindings = context["receipts"]
    core._correspondence_require(isinstance(bindings, dict), "request-malformed", "request",
        "Reviewed Receipt bindings must be an object", status="error")
    for key, binding in bindings.items():
        core._correspondence_require(isinstance(key, str) and re.fullmatch(r"[a-z0-9-]+/[a-z0-9-]+", key),
            "request-malformed", "request", "Receipt key must be plugin/skill", status="error")
        core._validate_correspondence_binding(repository, binding)
        core._correspondence_require(binding["path"] == f"{root}/{key}.json",
            "context-mismatch", "context", f"Reviewed Receipt path differs for {key}")
    return {**revisions, "receipt_root": root, "receipts": bindings}


def _validate_landing(repository, context, landing):
    required = {"contract", "context_sha256", "operation", "reviewed_head", "target_before", "candidate_revision"}
    core._correspondence_require(isinstance(landing, dict) and set(landing) == required,
        "request-malformed", "request", "Landing fields are incomplete or unknown", status="error")
    core._correspondence_require(landing["contract"] == CORRESPONDENCE_CONTRACT
        and isinstance(landing["operation"], str)
        and isinstance(landing["context_sha256"], str)
        and re.fullmatch(r"[0-9a-f]{64}", landing["context_sha256"]),
        "request-malformed", "request", "Landing contract, operation, or digest is invalid", status="error")
    for field in ("reviewed_head", "target_before", "candidate_revision"):
        core._correspondence_revision(repository, landing[field], field)
    core._correspondence_require(landing["operation"] in ("squash", "rebase"),
        "operation-unsupported", "landing", "Landing operation is unsupported")
    core._correspondence_require(landing["context_sha256"] == core.document_digest(context)
        and landing["operation"] == context["operation"]
        and landing["reviewed_head"] == context["reviewed_head"],
        "context-mismatch", "landing", "Actual landing differs from the reviewed context")
    core._correspondence_require(landing["target_before"] == context["reviewed_target"],
        "target-moved", "landing", "Landing target differs from the reviewed target")
    target, candidate = landing["target_before"], landing["candidate_revision"]
    try:
        core.git(repository, "merge-base", "--is-ancestor", target, candidate)
    except core.ReceiptError as error:
        raise core.CorrespondenceError("fail", "context-mismatch", "landing",
                                      "Landing target is not an ancestor of the candidate") from error
    if context["operation"] == "squash":
        parents = core.git(repository, "rev-list", "--parents", "-n", "1", candidate).decode().split()[1:]
        core._correspondence_require(parents == [target], "context-mismatch", "landing",
                                    "Squash landing must have only the reviewed target as parent")
    return candidate


def _landed_row(repository, key, binding, reviewed_source, landed_source, receipt_root):
    row = {"skill": key, "binding": binding, "status": "fail", "stage": "reviewed-receipt",
           "reason_code": "reviewed-receipt-mismatch", "reviewed_receipt": None,
           "landed_receipt": None, "reviewed_binding": None, "landed_correspondence": None}
    if binding is None:
        return {**row, "reason": "Required consumer has no reviewed Receipt binding"}
    try:
        path = binding["path"]
        # Preserve observed blob identities before parsing or resolving descriptors.
        h_raw = reviewed_source.read(path)
        row["reviewed_receipt"] = {"path": path, **reviewed_source.identity(path)}
        h_identity = row["reviewed_receipt"]
        core._correspondence_require(h_identity["sha256"] == binding["raw_sha256"]
            and h_identity["mode"] == binding["mode"], "reviewed-receipt-mismatch", "reviewed-receipt",
            "Reviewed Receipt bytes or mode differ")
        h_result = {"status": "fail", "stage": "binding", "reason_code": "reviewed-receipt-mismatch"}
        row["reviewed_binding"] = h_result
        try:
            core._read_bound_receipt(repository, h_raw, binding, h_result)
            h_result.update(status="pass", stage="complete", reason_code="complete",
                            reason="Reviewed Receipt binding verified")
        except core.CorrespondenceError as error:
            h_result.update(status=error.status, stage=error.stage, reason_code=error.code, reason=str(error))
        except core.ReceiptError as error:
            h_result.update(reason=str(error))
        if h_result["status"] != "pass":
            return {**row, "status": h_result["status"],
                    "reason_code": h_result["reason_code"] if h_result["status"] == "error" else "reviewed-receipt-mismatch",
                    "reason": h_result["reason"], "cause": h_result["reason_code"]}
        row.update(stage="landed-receipt", reason_code="receipt-missing")
        c_raw = landed_source.read(path)
        row["landed_receipt"] = {"path": path, **landed_source.identity(path)}
        c_identity = row["landed_receipt"]
        core._correspondence_require(c_identity["sha256"] == binding["raw_sha256"]
            and c_identity["mode"] == binding["mode"], "receipt-changed", "landed-receipt",
            "Landed Receipt bytes or mode differ")
        row.update(stage="descriptor", reason_code="descriptor-unresolved")
        c_descriptor = _ready_descriptor(repository, landed_source.revision, key)
        closure = core.input_closure(repository, landed_source.revision, c_descriptor,
                                    profile=binding["profile"], method=binding["method"])
        core._correspondence_require(not any(p == receipt_root or p.startswith(receipt_root + "/")
            for p in closure["inputs"]), "context-mismatch", "descriptor",
            "Receipt directory intersects the selected evaluated closure")
        c_result = core.check_correspondence(repository, candidate_revision=landed_source.revision,
            descriptor=c_descriptor, receipt_bytes=c_raw, binding=binding)
        row.update(landed_correspondence=c_result, status=c_result["status"], stage=c_result["stage"],
                   reason_code=c_result["reason_code"], reason=c_result["reason"])
    except core.CorrespondenceError as error:
        row.update(status=error.status, stage=error.stage, reason_code=error.code, reason=str(error))
    except (InventoryError, core.ReceiptError) as error:
        row.update(reason=str(error))
    return row


def check_landed(repository, *, context, landing):
    """Check every authoritative consumer and report explicit incomplete outcomes."""
    result = {"contract": CORRESPONDENCE_CONTRACT, "status": "error", "stage": "request",
        "reason_code": "request-malformed", "original_base": None, "reviewed_head": None,
        "target_before": None, "candidate_revision": None, "context_sha256": None,
        "consumer_revision": None, "procedure_revision": None, "coverage_basis": "complete-inventory",
        "comparisons": {"reviewed": None, "landed": None}, "selection_complete": False,
        "qualification_scope": "ordinary-receipt-correspondence", "member_qualification": "not-evaluated",
        "skills": []}
    # An identity can be available even when the claimed relations are rejected.
    for document, fields in ((context, ("original_base", "reviewed_head", "consumer_revision", "procedure_revision")),
                             (landing, ("target_before", "candidate_revision"))):
        if isinstance(document, dict):
            for field in fields:
                try:
                    result[field] = core._correspondence_revision(repository, document.get(field), field)
                except core.CorrespondenceError:
                    pass  # Full validation below reports the invalid or unavailable value.
    if isinstance(context, dict):
        try:
            result["context_sha256"] = core.document_digest(context)
        except (TypeError, ValueError):
            pass
    try:
        normalized = _validate_landed_context(repository, context)
        candidate = _validate_landing(repository, context, landing)
        result.update({field: normalized[field] for field in ("original_base", "reviewed_head",
                                                            "consumer_revision", "procedure_revision")})
        result.update(status="fail", target_before=normalized["reviewed_target"], candidate_revision=candidate,
                      context_sha256=core.document_digest(context), stage="selection", reason_code="selection-incomplete")
        reviewed = compare(repository, normalized["original_base"], normalized["reviewed_head"])
        landed = compare(repository, normalized["original_base"], candidate)
        result["comparisons"] = {"reviewed": reviewed, "landed": landed}
        expected = set(normalized["receipts"])
        required = set(reviewed["affected_skills"]) | set(landed["affected_skills"])
        complete = reviewed["status"] == "complete" and landed["status"] == "complete"
        matches = set(reviewed["affected_skills"]) == expected == set(landed["affected_skills"])
        result["selection_complete"] = complete and matches
        result["skills"] = [{"skill": key, "status": "not-checked", "reason": "Check has not completed"}
                            for key in sorted(required | expected)]
        h_source, c_source = Source(repository, normalized["reviewed_head"]), Source(repository, candidate)
        for index, key in enumerate(sorted(required | expected)):
            result["skills"][index] = _landed_row(repository, key, normalized["receipts"].get(key),
                                                h_source, c_source, normalized["receipt_root"])
        errors = [row for row in result["skills"] if row["status"] == "error"]
        failures = [row for row in result["skills"] if row["status"] != "pass"]
        if errors:
            result.update(status="error", stage=errors[0]["stage"], reason_code=errors[0]["reason_code"])
        elif not complete or not matches:
            result.update(status="fail", reason_code="selection-incomplete" if not complete else "selection-changed")
        elif failures:
            result.update(status="fail", stage=failures[0]["stage"], reason_code=failures[0]["reason_code"])
        else:
            result.update(status="pass" if result["skills"] else "not-required", stage="complete", reason_code="complete")
    except core.CorrespondenceError as error:
        result.update(status=error.status, stage=error.stage, reason_code=error.code, reason=str(error))
    except (InventoryError, core.ReceiptError) as error:
        result.update(reason=str(error))
    return result


def proposals(repository, revision, skill):
    """Return original unresolved values for review without proposing policy.

    Existing proposed map entries are retained separately. No semantic ID,
    severity, owner, or acceptance decision is generated by this operation.
    """
    observed = discover(repository, revision)
    if skill not in observed["skills"]:
        raise InventoryError("skill is outside the committed roster")
    normalized = normalize(repository, revision, skill)
    expectations = [expectation for case in normalized["cases"] for expectation in case["expectations"]
                    if expectation["id"] is None or expectation["severity"] is None]
    coordinates = {(record["source"]["path"], expectation["pointer"])
        for record in observed["skills"][skill]["records"] for expectation in record["expectations"]}
    source = Source(repository, revision)
    mapping = source.json(EXPECTATION_MAP) if EXPECTATION_MAP in source.files else {"entries": []}
    proposed = [entry for entry in mapping.get("entries", []) if entry.get("status") == "proposed"
        and (entry.get("source", {}).get("path"), entry.get("pointer")) in coordinates]
    plugin = observed["skills"][skill]["plugin"]
    owners = [record for record in observed["unresolved_records"]
              if record["context"]["plugin"] in (None, plugin)]
    return {"schema_version": 1, "revision": source.revision, "skill": skill,
            "status": normalized["status"], "expectations": expectations,
            "unresolved_owners": owners, "proposed_entries": proposed,
            "diagnostics": normalized["diagnostics"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=".", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    discover_parser = commands.add_parser("discover", help="Report committed source inventory and completeness observations")
    discover_parser.add_argument("--revision", required=True)
    compare_parser = commands.add_parser("compare", help="Summarize affected consumers and diagnostics; use discover for full source records")
    compare_parser.add_argument("--base", required=True)
    compare_parser.add_argument("--candidate", required=True)
    catalog_parser = commands.add_parser("catalog", help="Read canonical metadata for the complete committed Slate")
    catalog_parser.add_argument("--revision", required=True)
    check_parser = commands.add_parser("check", help="Check receipts committed at C for inventory-selected consumers")
    check_parser.add_argument("--base", required=True)
    check_parser.add_argument("--candidate", required=True)
    check_parser.add_argument("--receipt-root", required=True, help="Normalized repository directory containing plugin/skill.json receipts")
    landed_parser = commands.add_parser(
        "check-landed", help="Check reviewed Receipt bindings against an actual landed commit"
    )
    landed_parser.add_argument("--context", required=True, type=Path)
    landed_parser.add_argument("--landing", required=True, type=Path)
    for name in ("normalize", "proposals", "descriptor", "prepare", "reconcile"):
        command = commands.add_parser(name)
        command.add_argument("--revision", required=True)
        command.add_argument("--skill", required=True, help="plugin/skill from the committed roster")
        if name == "reconcile":
            command.add_argument("--results", required=True, type=Path)
            command.add_argument("--processing-revision", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "discover":
            result = discover(args.repository, args.revision)
            code = 0 if result["roster_complete"] else 1
        elif args.command == "compare":
            result = compare(args.repository, args.base, args.candidate)
            code = 0 if result["status"] == "complete" else 1
        elif args.command == "catalog":
            result, code = canonical_catalog(args.repository, args.revision), 0
        elif args.command == "check":
            result = check(args.repository, args.base, args.candidate, args.receipt_root)
            code = 1 if result["status"] == "fail" else 0
        elif args.command == "check-landed":
            context = core.read_json(args.context.read_bytes())
            landing = core.read_json(args.landing.read_bytes())
            result = check_landed(args.repository, context=context, landing=landing)
            code = {"pass": 0, "not-required": 0, "fail": 1, "error": 2}[result["status"]]
        elif args.command == "prepare":
            result, code = prepare(args.repository, args.revision, args.skill), 0
        elif args.command == "reconcile":
            result = reconcile(args.repository, args.revision, args.skill, args.results, args.processing_revision)
            code = 0
        else:
            action = {"normalize": normalize, "proposals": proposals, "descriptor": descriptor}[args.command]
            result = action(args.repository, args.revision, args.skill)
            code = 0 if result["status"] == "ready" else 1
    except (InventoryError, core.ReceiptError, ValueError, KeyError, TypeError, OSError) as error:
        result, code = {"status": "error", "message": str(error)}, 2
    print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
