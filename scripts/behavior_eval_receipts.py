#!/usr/bin/env python3
"""Record and check ordinary behavior results; see docs/behavior-eval-receipts.md."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess

POLICY_PATH = "release/behavior-eval-policy.json"
SCHEMA_PATH = "release/behavior-eval-receipt-v1.schema.json"
TOOL_PATH = "scripts/behavior_eval_receipts.py"
CORPORA_PATH = "scripts/behavior_eval_corpora.py"
INVENTORY_PATH = "scripts/behavior_eval_inventory.py"


class ReceiptError(ValueError):
    """The supplied ordinary evidence cannot support the requested check."""


def require(condition, message):
    if not condition:
        raise ReceiptError(message)


def canonical_bytes(value):
    """Admit finite JSON values that can be serialized as UTF-8 scalar text."""
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as error:
        raise ReceiptError(
            "value cannot be represented as canonical UTF-8 JSON"
        ) from error


def document_digest(value):
    """SHA-256 of UTF-8 JSON, sorted keys, compact separators, and no final newline."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_json(content):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(_):
        raise ReceiptError("non-finite JSON number")

    try:
        value = json.loads(
            content, object_pairs_hook=pairs, parse_constant=invalid_constant
        )
        canonical_bytes(value)
        return value
    except (ValueError, UnicodeError) as error:
        raise ReceiptError("invalid or duplicate-key JSON") from error


def validate(value, definition=None):
    """Validate the public receipt or a named input shape in its schema."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError as error:
        raise ReceiptError(
            "jsonschema is required; use uv run --with jsonschema==4.26.0"
        ) from error
    schema = read_json((Path(__file__).resolve().parents[1] / SCHEMA_PATH).read_bytes())
    if definition:
        schema = {"$ref": "#/$defs/" + definition, "$defs": schema["$defs"]}
    require(
        not list(Draft202012Validator(schema).iter_errors(value)),
        f"{definition or 'receipt'} schema mismatch",
    )


def git(repository, *arguments):
    result = subprocess.run(
        ["git", *arguments], cwd=repository, capture_output=True, check=False
    )
    require(result.returncode == 0, "Git source observation failed")
    return result.stdout


def revision(repository, value):
    require(
        isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value),
        "candidate must be a full commit identity",
    )
    require(
        git(repository, "rev-parse", "--verify", value + "^{commit}").decode().strip()
        == value,
        "candidate must name a commit",
    )
    return value


def relative_path(value):
    require(
        isinstance(value, str)
        and value
        and not any(ord(c) < 32 for c in value)
        and "\\" not in value,
        "expected a repository-relative path",
    )
    path = PurePosixPath(value)
    require(
        not path.is_absolute()
        and ".." not in path.parts
        and str(path) == value
        and value != ".",
        "expected a normalized repository-relative path",
    )
    return value


def source_bytes(repository, commit, path):
    return git(repository, "show", commit + ":" + relative_path(path))


def source_inventory(repository, commit):
    inventory = {}
    for record in git(repository, "ls-tree", "-rz", commit).split(b"\0"):
        if record:
            metadata, path = record.split(b"\t", 1)
            mode, kind, _ = metadata.decode().split()
            inventory[path.decode()] = (mode, kind)
    return inventory


def prepare(repository, candidate_revision, skill):
    """Freeze the caller's declared evaluation inputs at an existing source commit."""
    return _freeze(repository, candidate_revision, skill, bind_processing=True)


def _freeze(repository, candidate_revision, skill, *, bind_processing):
    validate(skill, "skill")
    revision(repository, candidate_revision)
    if bind_processing:
        validate(read_json(source_bytes(repository, candidate_revision, POLICY_PATH)), "policy")
    prefix = f"plugins/{skill['plugin']}/skills/{skill['skill']}"
    inventory = source_inventory(repository, candidate_revision)
    paths = {path for path in inventory if path.startswith(prefix + "/")}
    require(prefix + "/SKILL.md" in paths, "skill source is absent")
    paths.update(
        [
            skill["content_lock"],
            skill["evals"],
            skill["trigger_evals"],
        ]
    )
    if bind_processing:
        paths.update((POLICY_PATH, SCHEMA_PATH, TOOL_PATH))
        if skill.get("corpus_format"):
            paths.update((CORPORA_PATH, INVENTORY_PATH))
    paths.update(skill["dependencies"])
    paths.update(skill["behavior_inputs"])
    paths.update(skill["shared_references"])
    paths.update(item["source"] for item in skill.get("case_selection", []))
    if skill.get("expectation_map"):
        paths.add(skill["expectation_map"])
    parsed = corpus(
        repository, {"candidate_revision": candidate_revision, "skill": skill}
    )
    require(
        all(
            path.startswith(prefix + "/") or path in skill["behavior_inputs"]
            for path in parsed[2]
        ),
        "external fixture is absent from declared behavior inputs",
    )
    paths.update(parsed[2])
    inputs = {}
    for path in sorted(paths):
        relative_path(path)
        require(
            path in inventory
            and inventory[path] in (("100644", "blob"), ("100755", "blob")),
            "evaluation input must be a committed regular file",
        )
        inputs[path] = {
            "sha256": hashlib.sha256(
                source_bytes(repository, candidate_revision, path)
            ).hexdigest(),
            "mode": inventory[path][0],
        }
    return {
        "schema_version": 1,
        "candidate_revision": candidate_revision,
        "skill": skill,
        "inputs": inputs,
    }


def corpus(repository, snapshot):
    spec = snapshot["skill"]
    source = snapshot["candidate_revision"]
    if spec.get("corpus_format") == "provingkit-v1":
        normalized = _normalized_corpus(repository, snapshot)
        return ({coordinate_key(case["case_id"]): [{key: item[key] for key in ("id", "text", "severity")}
                                                  for item in case["expectations"]] for case in normalized["cases"]},
                {coordinate_key(case["case_id"]): case.get("expected_selection", case.get("should_trigger"))
                 for case in normalized["triggers"]},
                {fixture["path"] for case in normalized["cases"] for fixture in case["fixtures"]})
    document = read_json(source_bytes(repository, source, spec["evals"]))
    require(
        isinstance(document, dict)
        and document.get("skill_name") == spec["skill"]
        and isinstance(document.get("evals"), list)
        and document["evals"],
        "unsupported per-skill evaluation corpus",
    )
    cases, fixtures = {}, set()
    fixture_root = spec.get(
        "fixture_root", f"plugins/{spec['plugin']}/skills/{spec['skill']}"
    )
    relative_path(fixture_root)
    for case in document["evals"]:
        require(
            isinstance(case, dict) and type(case.get("id")) is int and case["id"] > 0,
            "corpus case must have a positive integer identity",
        )
        key = str(case["id"])
        require(key not in cases, "duplicate corpus case identity")
        expectations = case.get("expectations")
        require(
            isinstance(expectations, list) and expectations,
            "expectation coverage is absent",
        )
        seen = set()
        for expectation in expectations:
            require(
                isinstance(expectation, dict)
                and set(expectation) == {"id", "text", "severity"}
                and expectation["severity"] in ("safety", "quality"),
                "unsupported expectation: explicit safety/quality severity is required",
            )
            require(
                isinstance(expectation["id"], str)
                and re.fullmatch(
                    r"[a-zA-Z0-9][a-zA-Z0-9._:-]{0,159}", expectation["id"]
                )
                and expectation["id"] not in seen,
                "invalid or duplicate expectation identity",
            )
            require(
                isinstance(expectation["text"], str) and expectation["text"].strip(),
                "expectation text is absent",
            )
            seen.add(expectation["id"])
        require(
            isinstance(case.get("fixture_paths"), list), "unsupported fixture inventory"
        )
        for path in case["fixture_paths"]:
            fixtures.add(fixture_root + "/" + relative_path(path))
        cases[key] = expectations
    triggers = read_json(source_bytes(repository, source, spec["trigger_evals"]))
    require(
        isinstance(triggers, list) and triggers,
        "declared trigger corpus must contain cases",
    )
    queries = set()
    for item in triggers:
        require(
            isinstance(item, dict)
            and set(item) == {"query", "should_trigger"}
            and isinstance(item["query"], str)
            and item["query"].strip()
            and item["query"] not in queries
            and type(item["should_trigger"]) is bool,
            "unsupported or duplicate trigger case",
        )
        queries.add(item["query"])
    return (
        cases,
        {str(i): item["should_trigger"] for i, item in enumerate(triggers, 1)},
        fixtures,
    )


def coordinate_key(value):
    """Use original document coordinates internally while retaining public IDs."""
    return value if isinstance(value, str) else canonical_bytes(value).decode("utf-8")


def _normalized_corpus(repository, snapshot):
    if __package__:
        from . import behavior_eval_corpora as adapter
    else:
        import behavior_eval_corpora as adapter
    spec, source = snapshot["skill"], snapshot["candidate_revision"]
    documents, observed = {}, {}
    for selection in spec["case_selection"]:
        path = relative_path(selection["source"])
        if path not in documents:
            documents[path] = source_bytes(repository, source, path)
            result = adapter.inspect_document(path, documents[path], plugin=spec["plugin"])
            require(result["role"] != "unsupported", "unsupported selected corpus source")
            observed.update({(path, record["pointer"]): record for record in result["records"]})
    selected = []
    seen = set()
    for selection in spec["case_selection"]:
        coordinate = selection["source"], selection["pointer"]
        require(coordinate not in seen and coordinate in observed, "duplicate or unavailable source case coordinate")
        seen.add(coordinate)
        record = observed[coordinate]
        require(record["role"] in ("application", "trigger"), "selected reference is not an application or trigger case")
        selected.append(record)
        for fixture in record["fixtures"]:
            require(fixture["path"] is not None, "selected fixture path is unresolved")
            documents[fixture["path"]] = source_bytes(repository, source, fixture["path"])
    mapping = read_json(source_bytes(repository, source, spec["expectation_map"])) if spec.get("expectation_map") else {"schema_version": 1, "entries": []}
    normalized = adapter.normalize_records(selected, mapping, documents)
    require(not normalized["diagnostics"], "selected normalization is unresolved: " + ", ".join(
        sorted({item["code"] for item in normalized["diagnostics"]})))
    require(normalized["cases"] and normalized["triggers"], "application and discovery coverage are required")
    require(all(isinstance(case["prompt"], str) and case["prompt"].strip() for case in normalized["cases"]),
            "selected application prompt is absent")
    return normalized


def _case_details(repository, snapshot):
    spec, source = snapshot["skill"], snapshot["candidate_revision"]
    if spec.get("corpus_format") == "provingkit-v1":
        normalized = _normalized_corpus(repository, snapshot)
        return ({coordinate_key(case["case_id"]): {**case,
                    "expectations": [{key: item[key] for key in ("id", "text", "severity")}
                                     for item in case["expectations"]],
                    "fixtures": [item["path"] for item in case["fixtures"]]}
                 for case in normalized["cases"]},
                {coordinate_key(case["case_id"]): case for case in normalized["triggers"]})
    prefix = spec.get("fixture_root", f"plugins/{spec['plugin']}/skills/{spec['skill']}")
    return ({str(case["id"]): {**case, "source": {"path": spec["evals"]},
                              "fixtures": [prefix + "/" + value for value in case["fixture_paths"]]}
             for case in read_json(source_bytes(repository, source, spec["evals"]))["evals"]},
            {str(index): case for index, case in enumerate(
                read_json(source_bytes(repository, source, spec["trigger_evals"])), 1)})


def local_bytes(path):
    try:
        return Path(path).read_bytes()
    except OSError as error:
        raise ReceiptError("local evidence artifact unavailable") from error


def artifact_bytes(directory, relative):
    path = Path(directory) / relative_path(relative)
    require(
        path.resolve().is_relative_to(Path(directory).resolve()),
        "artifact must remain inside the private result directory",
    )
    return local_bytes(path)


def check_coordinates(runs, triggers, cases, expected_triggers):
    required = {(case_id, repetition) for case_id in cases for repetition in (1, 2, 3)}
    coordinates = [(coordinate_key(run["case_id"]), run["repetition"]) for run in runs]
    require(
        len(coordinates) == len(required) and set(coordinates) == required,
        "run coverage must include each case at repetitions 1, 2, and 3 exactly once",
    )
    require(
        len(triggers) == len(expected_triggers)
        and {coordinate_key(item["case_id"]) for item in triggers} == set(expected_triggers),
        "trigger coverage differs from the corpus",
    )


def processing_snapshot(repository, processing_revision, *, normalized=False):
    """Bind the committed processor actually performing this reconciliation."""
    revision(repository, processing_revision)
    root = Path(__file__).resolve().parents[1]
    inventory = source_inventory(repository, processing_revision)
    inputs = {}
    paths = (TOOL_PATH, SCHEMA_PATH, POLICY_PATH, CORPORA_PATH, INVENTORY_PATH) if normalized else (TOOL_PATH, SCHEMA_PATH, POLICY_PATH)
    for path in paths:
        require(inventory.get(path) in (("100644", "blob"), ("100755", "blob")),
                "processing input must be a committed regular file")
        content = source_bytes(repository, processing_revision, path)
        require(content == (root / path).read_bytes(),
                "processing revision differs from the running tool, schema, or policy")
        inputs[path] = {"sha256": hashlib.sha256(content).hexdigest(), "mode": inventory[path][0]}
    validate(read_json(source_bytes(repository, processing_revision, POLICY_PATH)), "policy")
    return {"revision": processing_revision, "inputs": inputs}


class _RetainedEvidence:
    """Read original artifacts by byte identity; never write historical records."""

    def __init__(self, directory):
        self.directory = directory
        self.references = []

    def value(self, reference):
        validate(reference, "evidenceReference")
        content = artifact_bytes(self.directory, reference["path"])
        require(hashlib.sha256(content).hexdigest() == reference["sha256"],
                "retained artifact byte digest differs")
        try:
            if reference["format"] == "utf8":
                require(reference["pointer"] == "", "text evidence cannot have a JSON pointer")
                value = content.decode("utf-8")
            elif reference["format"] == "jsonl":
                value = [read_json(line) if line.strip() else None for line in content.splitlines()]
            else:
                value = read_json(content)
            pointer = reference["pointer"]
            if pointer:
                require(pointer.startswith("/"), "invalid evidence JSON pointer")
                for token in pointer[1:].split("/"):
                    require(not re.search(r"~(?![01])", token), "invalid evidence JSON pointer escape")
                    token = token.replace("~1", "/").replace("~0", "~")
                    if isinstance(value, list):
                        require(re.fullmatch(r"0|[1-9][0-9]*", token), "invalid evidence array index")
                        value = value[int(token)]
                    else:
                        value = value[token]
        except (KeyError, IndexError, TypeError, UnicodeError) as error:
            raise ReceiptError("retained evidence coordinate is unavailable") from error
        self.references.append(self.public(reference))
        return value

    @staticmethod
    def public(reference):
        return {key: reference[key] for key in ("sha256", "format", "pointer")}

    def digest(self, binding):
        validate(binding, "contentBinding")
        value = self.value(binding["value"])
        if binding["representation"] == "sha256":
            require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value),
                    "retained input digest is unknown")
            return value
        require(isinstance(value, str), "retained input must contain exact UTF-8 text")
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def model(self, binding, expected):
        validate(binding, "modelBinding")
        require(self.value(binding["value"]) == expected, "retained model identity differs or is unknown")
        return binding["basis"]


def _probe_metadata(content):
    """Read the plain and folded name/description scalars used by these probes."""
    require(isinstance(content, str) and content.startswith("---\n"), "probe metadata is unavailable")
    header, separator, _ = content[4:].partition("\n---")
    require(separator, "probe frontmatter is incomplete")
    lines, result = header.splitlines(), {}
    for index, line in enumerate(lines):
        match = re.fullmatch(r"(name|description):\s*(.*)", line)
        if not match:
            continue
        name, value = match.groups()
        require(name not in result, "duplicate probe metadata")
        if value in (">", ">-"):
            folded = []
            for following in lines[index + 1:]:
                if not following.startswith((" ", "\t")):
                    break
                folded.append(following.strip())
            value = " ".join(folded)
        elif value.startswith('"'):
            value = read_json(value)
        elif value.startswith("'"):
            require(value.endswith("'"), "unsupported probe scalar")
            value = value[1:-1].replace("''", "'")
        require(isinstance(value, str) and value.strip(), "probe metadata is empty")
        result[name] = value
    require(set(result) == {"name", "description"}, "probe name and description are required")
    return result


def _probe_body_read(command, name, projection):
    """Admit a recorded cat of this temporary skill; never execute shell text."""
    require(isinstance(command, str), "probe read command is unavailable")
    try:
        outer = shlex.split(command)
        require(len(outer) == 3 and outer[0] in ("/bin/sh", "/bin/bash", "/usr/bin/bash", "/bin/zsh", "/usr/bin/zsh")
                and outer[1] in ("-c", "-lc"), "probe command is outside the supported read grammar")
        inner = shlex.split(outer[2])
    except ValueError as error:
        raise ReceiptError("probe read command is malformed") from error
    require(len(inner) in (2, 3) and inner[0] in ("cat", "/bin/cat", "/usr/bin/cat")
            and (len(inner) == 2 or inner[1] == "--"), "probe command is not a single body read")
    path = inner[-1]
    if path.startswith("<probe-root>/"):
        require(projection is not None, "symbolic probe path lacks its retained projection provenance")
        path = "/probe-root/" + path[len("<probe-root>/"):]
    require(re.fullmatch(r"/[A-Za-z0-9_./-]+", path) and str(PurePosixPath(path)) == path
            and ".." not in PurePosixPath(path).parts and path.endswith(f"/.agents/skills/{name}/SKILL.md"),
            "probe read does not address the temporary skill entrypoint")


def _codex_sentinel_trace(evidence, item, target_source):
    probe = evidence.value(item["probe_skill"])
    metadata = _probe_metadata(probe)
    require(metadata == _probe_metadata(target_source),
            "probe name or description differs from current skill")
    prompt = evidence.value(item["probe_prompt"])
    require(isinstance(prompt, str), "probe prompt is unavailable")
    negative_match = re.search(r"If no temporary skill is loaded, answer exactly: ([^\n]+)\n?\Z", prompt)
    require(negative_match, "unsupported documented negative probe boundary")
    sentinel = evidence.value(item["sentinel"])
    require(isinstance(sentinel, str) and sentinel and sentinel in probe, "sentinel is absent from original probe")
    record, projection = evidence.value(item["record"]), None
    if isinstance(record, dict) and "trace_path_normalization" in record:
        require(isinstance(record["trace_path_normalization"], str) and record["trace_path_normalization"].strip()
                and isinstance(record.get("original_transcript_sha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", record["original_transcript_sha256"]),
                "probe projection lacks its recorded original trace identity")
        projection = {"kind": "symbolic-paths", "original_trace_sha256": record["original_transcript_sha256"]}
    events = evidence.value(item["trace"])
    require(isinstance(events, list) and all(isinstance(event, dict) and event.get("type") in (
        "thread.started", "turn.started", "turn.completed", "item.started", "item.completed") for event in events),
        "unsupported or unsuccessful Codex probe trace")
    started, finished, pending, reads, response = False, False, None, {}, None
    for event in events:
        kind = event["type"]
        require(not finished, "probe events occur after turn completion")
        if kind == "thread.started":
            require(not started, "probe thread starts inside a running turn")
            continue
        if kind == "turn.started":
            require(not started, "probe trace contains multiple turns")
            started = True
            continue
        require(started, "probe event precedes its turn")
        if kind == "turn.completed":
            require(pending is None and response is not None, "probe turn completes before its read or response")
            finished = True
            continue
        observed = event.get("item")
        require(isinstance(observed, dict), "probe item is malformed")
        item_kind = observed.get("type")
        if item_kind == "command_execution":
            identifier = observed.get("id")
            require(isinstance(identifier, str) and identifier and identifier not in reads,
                    "probe read identity is missing or repeated")
            _probe_body_read(observed.get("command"), metadata["name"], projection)
            # CLI messages have no final phase. A read needs a later terminal response.
            response = None
            if kind == "item.started":
                require(pending is None, "probe contains concurrent reads")
                pending = observed
            else:
                require(pending is None or (pending["id"] == identifier and pending["command"] == observed["command"]),
                        "probe read completion differs from its start")
                require(observed.get("aggregated_output") == probe and type(observed.get("exit_code")) is int
                        and observed["exit_code"] == 0 and observed.get("status") == "completed",
                        "probe read failed or returned different bytes")
                reads[identifier] = observed
                pending = None
        elif item_kind == "agent_message" and kind == "item.completed":
            require(pending is None and isinstance(observed.get("text"), str),
                    "probe response is unavailable or precedes read completion")
            response = observed["text"]
        elif item_kind == "error":
            require(isinstance(observed.get("message"), str)
                    and observed["message"].startswith("Skill descriptions were shortened"),
                    "unsupported probe error observation")
        else:
            require(item_kind in ("agent_message", "reasoning"), "probe crossed its documented tool boundary")
    require(finished and len(reads) <= 1, "probe action completion or single body read is absent")
    return bool(reads), response, sentinel, negative_match[1], len(reads), evidence.value(item["returncode"]), projection


def _literal_read(value, path):
    """Parse the supported literal wrapper as data, without evaluating JavaScript."""
    require(isinstance(path, str) and re.fullmatch(r"/[A-Za-z0-9_./-]+", path)
            and str(PurePosixPath(path)) == path and ".." not in PurePosixPath(path).parts,
            "routing body path is outside the literal read grammar")
    require(isinstance(value, str), "routing read call must be literal text")
    match = re.fullmatch(r"\s*text\s*\(\s*await\s+tools\.exec_command\s*\((.*)\)\s*\)\s*;?\s*", value, re.DOTALL)
    require(match, "routing call is outside the literal read grammar")
    args = read_json(match[1])
    require(args == {"cmd": "/usr/bin/cat -- " + path, "shell": "/bin/sh", "login": False,
                     "tty": False, "max_output_tokens": 1024}, "routing read arguments differ from the allowed command")
    require(type(args["login"]) is bool and type(args["tty"]) is bool and type(args["max_output_tokens"]) is int,
            "routing read arguments have invalid types")
    return args


def _user_message_text(payload):
    if payload.get("type") == "user_message":
        require(isinstance(payload.get("message"), str), "recorded user input is unavailable")
        return payload["message"]
    content = payload.get("content")
    require(payload.get("type") == "message" and payload.get("role") == "user"
            and isinstance(content, list) and content
            and all(isinstance(block, dict) and block.get("type") == "input_text"
                    and isinstance(block.get("text"), str) for block in content), "recorded user input is unavailable")
    return "".join(block["text"] for block in content)


def _ambient_provenance(payload):
    """Identify the bounded harness envelope whose exact contents need review."""
    text = _user_message_text(payload)
    agents = re.fullmatch(r"# AGENTS\.md instructions for (/[^\n]+)\n\s*<INSTRUCTIONS>\s*(.*?)\s*</INSTRUCTIONS>\s*"
                          r"<environment_context>\s*(.*?)\s*</environment_context>\s*", text, re.DOTALL)
    environment = re.fullmatch(r"<environment_context>\s*(.*?)\s*</environment_context>\s*", text, re.DOTALL)
    require(agents or environment, "ambient allowance is not a supported AGENTS/environment envelope")
    if agents:
        return {"kind": "harness-agents-environment",
                "repository_path_sha256": hashlib.sha256(agents[1].encode()).hexdigest(),
                "instructions_sha256": hashlib.sha256(agents[2].encode()).hexdigest(),
                "environment_sha256": hashlib.sha256(agents[3].encode()).hexdigest()}
    return {"kind": "harness-environment", "environment_sha256": hashlib.sha256(environment[1].encode()).hexdigest()}


def _reviewed_ambient(evidence, sequence, allowed):
    ambient = sequence.get("ambient")
    if ambient is None:
        return [], None
    records, identities = [], []
    for item in ambient["records"]:
        reference = item["reference"]
        require(reference["sha256"] == sequence["trace"]["sha256"] and reference["format"] == sequence["trace"]["format"],
                "reviewed ambient record is outside the original native trace")
        payload = evidence.value(reference)
        require(isinstance(payload, dict), "reviewed ambient user record is unavailable")
        provenance = _ambient_provenance(payload)
        require(provenance == item["provenance"], "ambient AGENTS/environment provenance differs")
        text = _user_message_text(payload)
        require(not any(entry["token"] in text for entry in allowed.values()), "ambient record exposes a routing marker")
        identity = document_digest(payload)
        identities.append(identity)
        records.append({"reference": evidence.public(reference), "record_sha256": identity, "provenance": provenance})
    require(len(set(identities)) == len(identities), "duplicate ambient user record")
    require(ambient["review"]["records_sha256"] == document_digest(records),
            "ambient content review does not bind these exact original records")
    return identities, {"records": records, "review": ambient["review"]}


def _admit_native_routing_records(events):
    """Admit the nested record types before interpreting order or correspondence."""
    require(isinstance(events, list) and all(isinstance(event, dict) and isinstance(event.get("payload"), dict) for event in events),
            "routing native trace is unavailable")
    def strings(record, *fields):
        return all(isinstance(record.get(field), str) and record[field].strip() for field in fields)

    for event in events:
        category, payload = event.get("type"), event["payload"]
        require(category in ("session_meta", "turn_context", "event_msg", "response_item"), "unsupported native routing record")
        if "turn_id" in payload:
            require(strings(payload, "turn_id"), "routing turn identity is malformed")
        if category == "session_meta":
            require(strings(payload, "id"), "routing session identity is malformed")
        elif category == "turn_context":
            require(strings(payload, "turn_id", "model"), "routing context identity is malformed")
        else:
            require(strings(payload, "type"), "routing record type is unavailable")
            kind = payload["type"]
            if category == "event_msg" and kind in ("item_started", "item_completed"):
                item = payload.get("item")
                require(isinstance(item, dict) and strings(item, "type"), "routing item is malformed")
                if item["type"] == "CommandExecution":
                    require(strings(item, "id"), "routing command identity is malformed")
                    if kind == "item_completed":
                        require(isinstance(item.get("command"), list) and all(isinstance(arg, str) for arg in item["command"])
                                and isinstance(item.get("parsed_cmd"), list) and all(isinstance(row, dict) for row in item["parsed_cmd"]),
                                "routing command arguments are malformed")
            elif category == "response_item":
                if kind == "custom_tool_call":
                    require(strings(payload, "name", "call_id", "input"), "routing tool call is malformed")
                elif kind == "custom_tool_call_output":
                    output = payload.get("output")
                    require(strings(payload, "call_id") and isinstance(output, list)
                            and all(isinstance(block, dict) and block.get("type") == "input_text"
                                    and isinstance(block.get("text"), str) for block in output), "routing tool output is malformed")
                elif kind == "message":
                    content = payload.get("content")
                    require(payload.get("role") in ("assistant", "user") and isinstance(content, list) and content
                            and all(isinstance(block, dict) and isinstance(block.get("text"), str)
                                    and block.get("type") in ("input_text", "output_text") for block in content),
                            "routing message is malformed or has an unsupported role")


def _native_routing_reads(events, allowed, model_id, message, ambient):
    """Derive every sequential successful body read from a complete native turn."""
    _admit_native_routing_records(events)
    contexts = [event["payload"] for event in events if event.get("type") == "turn_context"]
    sessions = [event["payload"] for event in events if event.get("type") == "session_meta"]
    starts = [event["payload"] for event in events if event.get("type") == "event_msg"
              and event.get("payload", {}).get("type") == "task_started"]
    ends = [event["payload"] for event in events if event.get("type") == "event_msg"
            and event.get("payload", {}).get("type") == "task_complete"]
    require(len(sessions) == len(contexts) == len(starts) == len(ends) == 1
            and isinstance(sessions[0].get("id"), str) and sessions[0]["id"],
            "routing trace must contain one identified session and complete native turn")
    turn = contexts[0].get("turn_id")
    require(turn and contexts[0].get("model") == model_id and starts[0].get("turn_id") == turn
            and ends[0].get("turn_id") == turn and not ends[0].get("error")
            and type(ends[0].get("started_at")) is int and type(ends[0].get("completed_at")) is int
            and ends[0]["completed_at"] >= ends[0]["started_at"], "routing turn or configured model differs")
    pending, commands, calls, reads, final, finished, started = None, set(), set(), [], None, False, False
    pending_ambient = set(ambient)
    for event in events:
        payload = event.get("payload", {})
        require(isinstance(payload, dict), "malformed native routing record")
        kind = payload.get("type")
        if (event.get("type") == "response_item" and kind == "message" and payload.get("role") == "user"
                or event.get("type") == "event_msg" and kind == "user_message"):
            identity = document_digest(payload)
            require(not finished, "routing user input occurs after completion")
            if identity in pending_ambient:
                pending_ambient.remove(identity)
            else:
                require(_user_message_text(payload) == message,
                        "recorded user input differs from the frozen routing dispatch and reviewed ambient set")
        if event.get("type") == "event_msg":
            if kind in ("item_started", "item_completed"):
                require(isinstance(payload.get("item"), dict) and payload["item"].get("type")
                        in ("CommandExecution", "AgentMessage", "Reasoning"),
                        "routing trace contains an unsupported tool or item event")
            if kind == "task_started":
                started = True
            elif kind == "task_complete":
                require(started and pending is None and final is not None and payload.get("last_agent_message") == final,
                        "routing completion lacks its completed reads or final response")
                finished = True
            elif kind in ("turn_aborted", "error", "stream_error"):
                raise ReceiptError("routing trace contains an unsuccessful turn")
            elif kind == "item_started" and payload["item"]["type"] == "CommandExecution":
                require(started and not finished and pending is not None and pending["command"] is None
                        and pending["started"] is None and payload.get("turn_id") == turn
                        and isinstance(payload["item"].get("id"), str), "routing command start is unmatched or concurrent")
                pending["started"] = payload["item"]["id"]
            elif kind == "item_completed" and payload.get("item", {}).get("type") == "CommandExecution":
                command = payload["item"]
                require(started and not finished and pending is not None and pending["command"] is None
                        and payload.get("turn_id") == turn and command.get("id") not in commands
                        and isinstance(command.get("id"), str) and pending["started"] in (None, command["id"]),
                        "routing commands are unmatched, repeated, or concurrent")
                entry, args = pending["entry"], pending["args"]
                parsed = command.get("parsed_cmd")
                require(command.get("command") == ["/bin/sh", "-c", args["cmd"]]
                        and isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict)
                        and parsed[0].get("type") == "read" and parsed[0].get("cmd") == args["cmd"]
                        and parsed[0].get("path", entry["path"]) == entry["path"],
                        "routing command differs from its literal body read")
                require(command.get("status") == "completed" and type(command.get("exit_code")) is int
                        and command["exit_code"] == 0 and command.get("stderr") == ""
                        and command.get("stdout") == command.get("aggregated_output") == entry["body"]
                        and command.get("formatted_output", entry["body"]) == entry["body"],
                        "routing body read failed or returned different bytes")
                commands.add(command["id"])
                pending["command"] = command["id"]
        elif event.get("type") == "response_item":
            require(kind in ("custom_tool_call", "custom_tool_call_output", "function_call", "function_call_output",
                             "message", "reasoning"), "routing contains an unsupported response or tool record")
            if kind == "custom_tool_call":
                require(started and not finished and final is None and pending is None
                        and payload.get("name") == "exec" and isinstance(payload.get("call_id"), str)
                        and payload["call_id"] not in calls, "routing crossed its sequential tool boundary")
                candidates = []
                for entry in allowed.values():
                    try:
                        args = _literal_read(payload.get("input", ""), entry["path"])
                        candidates.append((entry, args))
                    except ReceiptError:
                        pass
                require(len(candidates) == 1, "routing call is not a listed literal body read")
                entry, args = candidates[0]
                calls.add(payload["call_id"])
                pending = {"id": payload["call_id"], "entry": entry, "args": args, "command": None, "started": None}
            elif kind == "custom_tool_call_output":
                require(pending is not None and payload.get("call_id") == pending["id"] and pending["command"],
                        "routing outer result is unmatched or precedes its command")
                output = payload.get("output")
                require(isinstance(output, list) and len(output) == 2
                        and all(isinstance(block, dict) and block.get("type") == "input_text" for block in output)
                        and output[0].get("text", "").startswith("Script completed\n"), "routing outer result is incomplete")
                result = read_json(output[1].get("text", ""))
                require(isinstance(result, dict) and type(result.get("exit_code")) is int and result["exit_code"] == 0
                        and "session_id" not in result and result.get("output") == pending["entry"]["body"],
                        "routing outer result differs from the successful body read")
                entry = pending["entry"]
                reads.append({"name": entry["name"], "call_id": pending["id"], "command_id": pending["command"],
                              "body_sha256": entry["body_sha256"], "token_sha256": entry["token_sha256"]})
                pending = None
            elif kind in ("function_call", "function_call_output"):
                raise ReceiptError("routing crossed its allowed tool boundary")
            elif kind == "message" and payload.get("role") == "assistant":
                require(started and not finished and final is None and pending is None
                        and (payload.get("phase") == "final" or payload.get("channel") == "final")
                        and payload.get("phase", "final") == payload.get("channel", "final") == "final",
                        "routing contains an unexpected assistant response")
                content = payload.get("content")
                require(isinstance(content, list) and len(content) == 1 and content[0].get("type") == "output_text"
                        and isinstance(content[0].get("text"), str), "routing final response is unavailable")
                final = content[0]["text"]
    require(finished and pending is None and final is not None and not pending_ambient, "routing trace or reviewed ambient coverage is incomplete")
    require(read_json(final) == {"tokens": [allowed[read["name"]]["token"] for read in reads]},
            "routing final tokens differ from actual ordered body reads")
    return reads, sessions[0]["id"], turn


def _canonical_routing_catalog(repository, revision):
    if __package__:
        from . import behavior_eval_inventory as inventory
    else:
        import behavior_eval_inventory as inventory
    try:
        return inventory.canonical_catalog(repository, revision)
    except inventory.InventoryError as error:
        raise ReceiptError("routing catalog is unavailable: " + str(error)) from error


def _catalog_sequence(repository, snapshot, evidence, sequence, query, model_id):
    source = evidence.value(sequence["source_catalog"])
    require(isinstance(source, dict), "routing source catalog is unavailable")
    canonical = _canonical_routing_catalog(repository, source.get("revision"))
    require(source.get("tree") == git(repository, "rev-parse", canonical["revision"] + "^{tree}").decode().strip(),
            "routing source tree differs")
    members = {entry["name"]: entry for entry in canonical["members"]}
    original = source.get("entries")
    require(isinstance(original, list) and len(original) == len(members)
            and all(isinstance(entry, dict) for entry in original)
            and {entry.get("name") for entry in original} == set(members), "routing source catalog is incomplete")
    for entry in original:
        current = members[entry["name"]]
        require(entry.get("id") == current["skill"].replace("/", ":") and entry.get("description") == current["description"]
                and entry.get("source_path") == current["entrypoint"]["path"]
                and entry.get("source_sha256") == current["entrypoint"]["sha256"], "routing source metadata differs")
    source_inputs = {path: {key: identity[key] for key in ("sha256", "mode")}
                     for path, identity in canonical["source_identities"].items()}
    require(all(snapshot["inputs"].get(path) == identity for path, identity in source_inputs.items()),
            "full routing catalog is absent from current source closure")
    offered_text = evidence.value(sequence["offered_catalog"])
    require(isinstance(offered_text, str), "exact offered catalog bytes are required")
    offered = read_json(offered_text)
    markers = evidence.value(sequence["marker_map"])
    require(isinstance(offered, list) and isinstance(markers, list) and len(offered) == len(markers) == len(members)
            and all(isinstance(entry, dict) for entry in offered + markers)
            and {entry.get("name") for entry in offered} == {entry.get("name") for entry in markers} == set(members)
            and set(sequence["bodies"]) == set(members), "supplied catalog or marker-body inventory is incomplete")
    marker_map = {entry["name"]: entry for entry in markers}
    allowed, public_members, paths, tokens = {}, [], set(), set()
    for entry in offered:
        name = entry["name"]
        marker, current = marker_map[name], members[name]
        require(entry.get("description") == current["description"] and marker.get("skill_id") == current["skill"].replace("/", ":")
                and marker.get("absolute_body_path") == entry.get("body_path") and marker.get("allowed_tool") == "functions.exec",
                "offered catalog or marker correspondence differs")
        args = _literal_read(entry.get("read_call", ""), entry.get("body_path"))
        require(_literal_read(marker.get("allowed_read_javascript", ""), entry["body_path"]) == args,
                "marker and offered read commands differ")
        body = evidence.value(sequence["bodies"][name])
        token = marker.get("token")
        require(isinstance(token, str) and re.fullmatch(r"[A-Za-z0-9_-]+", token) and body == token + "\n"
                and entry["body_path"] not in paths and token not in tokens, "routing marker bodies are ambiguous or changed")
        body_digest = hashlib.sha256(body.encode()).hexdigest()
        require(isinstance(marker.get("body"), dict) and marker["body"].get("sha256") == body_digest
                and marker["body"].get("bytes") == len(body.encode()), "routing marker body digest differs")
        paths.add(entry["body_path"])
        tokens.add(token)
        public = {"skill": current["skill"], "name": name, "entrypoint": current["entrypoint"],
            "description_sha256": hashlib.sha256(current["description"].encode()).hexdigest(),
            "body_sha256": body_digest, "token_sha256": hashlib.sha256(token.encode()).hexdigest()}
        public_members.append(public)
        allowed[name] = {**public, "body": body, "token": token, "path": entry["body_path"]}
    protocol = evidence.value(sequence["protocol"])
    message = evidence.value(sequence["executor_message"])
    require(isinstance(protocol, str) and protocol.strip() and isinstance(message, str)
            and message == protocol + "\nRequest:\n" + query + "\n\nAvailable skill catalog:\n" + offered_text,
            "frozen routing message differs from query and complete offered catalog")
    dispatch, spawn = evidence.value(sequence["dispatch"]), evidence.value(sequence["spawn"])
    require(isinstance(dispatch, dict) and isinstance(spawn, dict) and isinstance(dispatch.get("arguments"), dict),
            "original routing dispatch and spawn records are unavailable")
    arguments = dispatch["arguments"]
    require(arguments.get("message") == message and arguments.get("fork_turns") == "none"
            and isinstance(arguments.get("task_name"), str) and re.fullmatch(r"[a-z0-9_]+", arguments["task_name"])
            and isinstance(dispatch.get("call_id"), str) and dispatch["call_id"]
            and spawn.get("call_id") == dispatch["call_id"] and isinstance(spawn.get("agent_path"), str)
            and spawn["agent_path"].endswith("/" + arguments["task_name"]), "routing dispatch differs from its frozen task or spawn")
    ambient, public_ambient = _reviewed_ambient(evidence, sequence, allowed)
    reads, child_id, turn_id = _native_routing_reads(evidence.value(sequence["trace"]), allowed, model_id, message, ambient)
    require(spawn.get("agent_thread_id") == child_id, "routing spawn belongs to another native child")
    catalog = {"source_revision": canonical["revision"], "catalog_sha256": document_digest(canonical["members"]),
        "members": public_members, "inputs": source_inputs, "reads": reads,
        "dispatch": {"record": evidence.public(sequence["dispatch"]), "spawn": evidence.public(sequence["spawn"]),
            "call_id_sha256": hashlib.sha256(dispatch["call_id"].encode()).hexdigest(),
            "task_name_sha256": hashlib.sha256(arguments["task_name"].encode()).hexdigest(),
            "child_session_sha256": hashlib.sha256(child_id.encode()).hexdigest(),
            "turn_id_sha256": hashlib.sha256(turn_id.encode()).hexdigest()},
        "prompt_sha256": hashlib.sha256(message.encode()).hexdigest(), "prompt_basis": sequence["prompt_basis"],
        "offered_catalog_sha256": hashlib.sha256(offered_text.encode()).hexdigest(),
        "marker_map_sha256": document_digest(markers), "trace_sha256": sequence["trace"]["sha256"]}
    if public_ambient is not None:
        catalog["ambient"] = public_ambient
    return [read["name"] for read in reads], catalog


def _check_routing_catalog(repository, snapshot, trigger):
    details = trigger["reconciliation"]
    require(details["source_binding"] == "supplied-catalog-body-load" and "catalog" in details,
            "routing catalog correspondence is absent")
    catalog = details["catalog"]
    canonical = _canonical_routing_catalog(repository, catalog["source_revision"])
    inputs = {path: {key: identity[key] for key in ("sha256", "mode")}
              for path, identity in canonical["source_identities"].items()}
    require(catalog["inputs"] == inputs and all(snapshot["inputs"].get(path) == identity for path, identity in inputs.items())
            and catalog["catalog_sha256"] == document_digest(canonical["members"]),
            "routing catalog differs from its original or current bound source")
    members = {entry["name"]: entry for entry in canonical["members"]}
    public = {entry["name"]: entry for entry in catalog["members"]}
    require(len(public) == len(catalog["members"]) == len(members) and set(public) == set(members),
            "routing catalog member coverage differs")
    for name, current in members.items():
        entry = public[name]
        require(entry["skill"] == current["skill"] and entry["entrypoint"] == current["entrypoint"]
                and entry["description_sha256"] == hashlib.sha256(current["description"].encode()).hexdigest(),
                "routing catalog member differs from current metadata")
    reads = catalog["reads"]
    require(len({read["call_id"] for read in reads}) == len({read["command_id"] for read in reads}) == len(reads)
            and trigger["observed_selection"] == [read["name"] for read in reads],
            "routing sequence differs from its complete ordered reads")
    for read in reads:
        require(read["name"] in public and all(read[key] == public[read["name"]][key]
                for key in ("body_sha256", "token_sha256")), "routing body read differs from the catalog marker")
    require(catalog["trace_sha256"] in {ref["sha256"] for ref in details["evidence"]},
            "routing raw trace is absent from retained evidence")
    require(all(catalog["dispatch"][field] in details["evidence"] for field in ("record", "spawn")),
            "routing dispatch or spawn is absent from retained evidence")
    if "ambient" in catalog:
        ambient = catalog["ambient"]
        require(ambient["review"]["records_sha256"] == document_digest(ambient["records"])
                and all(record["reference"] in details["evidence"] and record["reference"]["sha256"] == catalog["trace_sha256"]
                        for record in ambient["records"]), "routing ambient review or original-record binding differs")


def _reconcile_trigger(evidence, item, expected, query, target_source, model_id, *, repository=None, snapshot=None):
    evidence.value(item["record"])
    model_basis = evidence.model(item["model"], model_id)
    require(evidence.value(item["query"]) == query, "discovery query differs from current source")
    entrypoint_digest = hashlib.sha256(target_source.encode()).hexdigest()
    if "trace" not in item and "sequence" not in item:
        require(evidence.digest(item["entrypoint"]) == entrypoint_digest,
                "discovery source differs from current skill")
    kind = item["observation_kind"]
    require(kind != "authored-selection", "authored selection supplies no observed discovery coverage")
    details = {"model_basis": model_basis, "limits": item["limits"],
               "source_binding": "name-and-description" if "trace" in item else "entrypoint-bytes",
               "query_sha256": hashlib.sha256(query.encode()).hexdigest(),
               "entrypoint_sha256": entrypoint_digest,
               "evidence": evidence.references.copy()}
    if isinstance(expected, list):
        require(kind in ("recorded-invocation-sequence", "recorded-sentinel-sequence"),
                "a complete recorded selection sequence is required for this routing case")
        if kind == "recorded-sentinel-sequence":
            observed, details["catalog"] = _catalog_sequence(repository, snapshot, evidence, item["sequence"], query, model_id)
            details["source_binding"] = "supplied-catalog-body-load"
        else:
            observed = evidence.value(item["observed_selection"])
        require(isinstance(observed, list) and all(isinstance(value, str) and value.strip() for value in observed),
                "observed selection must retain its complete ordered sequence")
        details["evidence"] = evidence.references.copy()
        return {"case_id": item["case_id"], "expected_selection": expected, "observed_selection": observed,
                "observation_kind": kind, "observation_sha256": item["record"]["sha256"],
                "reconciliation": details}
    require(kind in ("recorded-invocation", "recorded-sentinel-body-load"),
            "Boolean discovery requires its recorded observation kind")
    if kind == "recorded-invocation":
        triggered = evidence.value(item["triggered"])
        require(type(triggered) is bool, "native invocation result must be observed Boolean data")
    else:
        if "trace" in item:
            loaded, response, sentinel, negative, actions, returncode, projection = _codex_sentinel_trace(evidence, item, target_source)
            if projection is not None:
                details["trace_projection"] = projection
        else:
            loaded = evidence.value(item["body_loaded"])
            response = evidence.value(item["response"])
            sentinel = evidence.value(item["sentinel"])
            negative = evidence.value(item["negative_response"])
            actions = evidence.value(item["tool_action_count"])
            returncode = evidence.value(item["returncode"])
        require(type(loaded) is bool and isinstance(response, str)
                and isinstance(sentinel, str) and sentinel and isinstance(negative, str)
                and negative and sentinel != negative and type(actions) is int and actions >= 0
                and type(returncode) is int and returncode == 0,
                "sentinel discovery lacks its recorded body, response, or completion boundary")
        triggered = loaded and response == sentinel
        require(triggered or (not loaded and response == negative and actions == 0),
                "sentinel discovery does not satisfy its observed positive or negative boundary")
        details.update(body_loaded=loaded, response_sha256=hashlib.sha256(response.encode()).hexdigest(),
            sentinel_sha256=hashlib.sha256(sentinel.encode()).hexdigest(),
            negative_response_sha256=hashlib.sha256(negative.encode()).hexdigest(),
            tool_action_count=actions, returncode=returncode)
    details["evidence"] = evidence.references.copy()
    return {"case_id": item["case_id"], "expected": expected, "triggered": triggered,
            "observation_kind": kind, "observation_sha256": item["record"]["sha256"],
            "reconciliation": details}


def _original_execution(record, response, run):
    """Bind supported retained execution records, not arbitrary artifact fields."""
    require(isinstance(record, dict), "original execution must be a recorded run object")
    response_digest = hashlib.sha256(response.encode()).hexdigest()
    if "execution" in record:
        execution = record["execution"]
        require(isinstance(execution, dict) and execution.get("completed") is True
                and type(execution.get("returncode")) is int and execution["returncode"] == 0,
                "original execution did not complete")
        identifiers = execution.get("thread_ids")
        require(isinstance(identifiers, list) and len(identifiers) == 1,
                "original execution thread identity is unavailable or ambiguous")
        identity, basis = identifiers[0], "recorded-thread"
        require(execution.get("response_sha256") == response_digest,
                "original execution response digest differs")
    else:
        identity, basis = record.get("native_agent"), "recorded-native-agent"
    require(isinstance(identity, str) and identity.strip(), "original execution identity is unavailable")
    require("native_agent" not in record or record["native_agent"] == identity,
            "original execution identifiers disagree")
    require(record.get("response") == response or record.get("response_sha256") == response_digest,
            "original execution record belongs to another response")
    if "response" in record:
        require(record["response"] == response, "original execution response differs")
    if "response_sha256" in record:
        require(record["response_sha256"] == response_digest, "original execution response digest differs")
    original_id = run["case_id"].get("id") if isinstance(run["case_id"], dict) else run["case_id"]
    for field in ("case", "case_id", "id"):
        if field in record and original_id is not None:
            require(str(record[field]) == str(original_id), "original execution case differs")
    if "repetition" in record:
        require(type(record["repetition"]) is int and record["repetition"] == run["repetition"],
                "original execution repetition differs")
    return {"basis": basis, "identity_sha256": hashlib.sha256(identity.encode()).hexdigest()}


def reconcile(repository, candidate_revision, skill, results_path, processing_revision):
    """Reconcile original observations with current source, without backdating a snapshot."""
    processing = processing_snapshot(repository, processing_revision, normalized=bool(skill.get("corpus_format")))
    snapshot = _freeze(repository, candidate_revision, skill, bind_processing=False)
    path = Path(results_path)
    raw = local_bytes(path)
    results = read_json(raw)
    validate(results, "reconciliationResults")
    cases, expected_triggers, fixtures = corpus(repository, snapshot)
    check_coordinates(results["runs"], results["triggers"], cases, expected_triggers)
    original_cases, trigger_source = _case_details(repository, snapshot)
    prefix = f"plugins/{skill['plugin']}/skills/{skill['skill']}"
    runtime = set(results["runtime_inputs"])
    require(prefix + "/SKILL.md" in runtime and runtime <= set(snapshot["inputs"]),
            "declared delivered runtime inputs must include the skill and belong to bound source")
    runs, executions, identities = [], set(), set()
    for run in results["runs"]:
        evidence = _RetainedEvidence(path.parent)
        original_execution = evidence.value(run["execution_record"])
        identity = document_digest(evidence.public(run["execution_record"]))
        require(identity not in executions, "an original execution record cannot supply two repetitions")
        executions.add(identity)
        original_revision = evidence.value(run["original_revision"])
        require(original_revision is None or isinstance(original_revision, str)
                and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", original_revision),
                "original revision must retain its recorded identity or explicit unknown value")
        original_corpus_digest = evidence.value(run["original_corpus_sha256"])
        require(isinstance(original_corpus_digest, str) and re.fullmatch(r"[0-9a-f]{64}", original_corpus_digest),
                "original corpus identity is required")
        case = original_cases[coordinate_key(run["case_id"])]
        expected_inputs = runtime | set(case["fixtures"])
        require(set(run["inputs"]) == expected_inputs, "delivered input coverage differs from current case")
        inputs = {name: evidence.digest(binding) for name, binding in run["inputs"].items()}
        require(all(value == snapshot["inputs"][name]["sha256"] for name, value in inputs.items()),
                "historical delivered input differs from current source")
        prompt = evidence.value(run["prompt"])
        require(prompt == case["prompt"], "historical prompt differs from current case")
        response = evidence.value(run["response"])
        require(isinstance(response, str), "historical response is absent")
        execution_identity = _original_execution(original_execution, response, run)
        identity_key = execution_identity["identity_sha256"]
        require(identity_key not in identities, "one original execution cannot supply two repetitions or cases")
        identities.add(identity_key)
        response_digest = hashlib.sha256(response.encode("utf-8")).hexdigest()
        executor_basis = evidence.model(run["executor_model"], results["executor_model_id"])
        grader_basis = evidence.model(run["grader_model"], results["grader_model_id"])
        evidence.value(run["grading_record"])
        require(evidence.digest(run["graded_response"]) == response_digest,
                "historical grading belongs to another response")
        rubric = evidence.value(run["rubric"]["value"])
        require(rubric == (cases[coordinate_key(run["case_id"])] if run["rubric"]["representation"] == "expectations"
                           else snapshot["inputs"][case["source"]["path"]]["sha256"]),
                "grading rubric differs from current expectations")
        prior_expectations = evidence.value(run["original_expectations"])
        require(isinstance(prior_expectations, list) and prior_expectations, "original rubric is unknown")
        for reference in run["previous_grading"]:
            evidence.value(reference)
        if run["adjudication"] is not None:
            evidence.value(run["adjudication"])
        require(prior_expectations == cases[coordinate_key(run["case_id"])]
                or run["previous_grading"] and run["adjudication"] is not None,
                "changed grading criteria require retained original grading and explicit adjudication")
        grades = evidence.value(run["grades"])
        require(isinstance(grades, list) and len(grades) == len(cases[coordinate_key(run["case_id"])])
                and all(isinstance(grade, dict) and isinstance(grade.get("id"), str)
                        and type(grade.get("passed")) is bool for grade in grades),
                "actual per-expectation Boolean grades are required")
        expected = {item["id"]: item for item in cases[coordinate_key(run["case_id"])]}
        require({grade["id"] for grade in grades} == set(expected), "grade expectation coverage differs")
        for grade in grades:
            require(all(field not in grade or grade[field] == expected[grade["id"]][field]
                        for field in ("severity", "text")), "recorded grade differs from current criterion")
        runs.append({"case_id": run["case_id"], "repetition": run["repetition"],
            "expectations": [{"id": grade["id"], "severity": expected[grade["id"]]["severity"],
                              "passed": grade["passed"]} for grade in grades],
            "executor_output_sha256": response_digest, "grading_sha256": run["grading_record"]["sha256"],
            "reconciliation": {"execution_record": evidence.public(run["execution_record"]),
                "execution_identity": execution_identity,
                "original_revision": original_revision, "original_corpus_sha256": original_corpus_digest,
                "original_expectations_sha256": document_digest(prior_expectations),
                "inputs": inputs, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "executor_model_basis": executor_basis, "grader_model_basis": grader_basis,
                "previous_grading": [evidence.public(ref) for ref in run["previous_grading"]],
                "adjudication": evidence.public(run["adjudication"]) if run["adjudication"] is not None else None,
                "evidence": evidence.references}})
    triggers = [_reconcile_trigger(_RetainedEvidence(path.parent), item, expected_triggers[coordinate_key(item["case_id"])],
        trigger_source[coordinate_key(item["case_id"])]["query"], source_bytes(repository, candidate_revision, prefix + "/SKILL.md").decode("utf-8"),
        results["executor_model_id"], repository=repository, snapshot=snapshot) for item in results["triggers"]]
    receipt = {"schema_version": 1, "kind": "evaluation", "method": "reconciled-after-run",
        "reconciliation": {"runtime_inputs": results["runtime_inputs"], "runtime_inputs_complete": True},
        "processing": processing, "candidate_revision": candidate_revision, "snapshot": snapshot,
        "executor_model_id": results["executor_model_id"], "grader_model_id": results["grader_model_id"],
        "runs_per_case": 3, "runs": runs, "triggers": triggers,
        "private_evidence": {"manifest_sha256": hashlib.sha256(raw).hexdigest()}, "attestation": None}
    validate(receipt)
    evaluate(repository, receipt)
    return receipt


def produce(repository, snapshot, results_path):
    """Project local result artifacts into a public receipt without their private paths."""
    validate(snapshot, "snapshot")
    require(
        snapshot
        == prepare(repository, snapshot["candidate_revision"], snapshot["skill"]),
        "evaluation input snapshot differs from source",
    )
    results_path = Path(results_path)
    raw = local_bytes(results_path)
    results = read_json(raw)
    validate(results, "results")
    require(
        results["snapshot_sha256"] == document_digest(snapshot),
        "results name another snapshot",
    )
    cases, expected_triggers, _ = corpus(repository, snapshot)
    check_coordinates(results["runs"], results["triggers"], cases, expected_triggers)
    runs = []
    for run in results["runs"]:
        output = artifact_bytes(results_path.parent, run["executor_output"])
        grading = artifact_bytes(results_path.parent, run["grading"])
        execution = read_json(output)
        validate(execution, "execution")
        require(
            execution["snapshot_sha256"] == results["snapshot_sha256"]
            and execution["case_id"] == run["case_id"]
            and execution["repetition"] == run["repetition"]
            and execution["model_id"] == results["executor_model_id"],
            "executor artifact belongs to another evaluation coordinate",
        )
        grading_document = read_json(grading)
        validate(grading_document, "grading")
        require(
            grading_document["snapshot_sha256"] == results["snapshot_sha256"]
            and grading_document["case_id"] == run["case_id"]
            and grading_document["repetition"] == run["repetition"]
            and grading_document["model_id"] == results["grader_model_id"]
            and grading_document["executor_output_sha256"]
            == hashlib.sha256(output).hexdigest(),
            "grading artifact belongs to another executor output",
        )
        observed_grades = grading_document["expectations"]
        expected_ids = {item["id"] for item in cases[coordinate_key(run["case_id"])]}
        require(
            len(observed_grades) == len(expected_ids)
            and {item["id"] for item in observed_grades} == expected_ids,
            "grading expectation coverage differs from the corpus",
        )
        grades = {item["id"]: item["passed"] for item in observed_grades}
        expectations = [
            {
                "id": item["id"],
                "severity": item["severity"],
                "passed": grades[item["id"]],
            }
            for item in cases[coordinate_key(run["case_id"])]
        ]
        runs.append(
            {
                "case_id": run["case_id"],
                "repetition": run["repetition"],
                "expectations": expectations,
                "executor_output_sha256": hashlib.sha256(output).hexdigest(),
                "grading_sha256": hashlib.sha256(grading).hexdigest(),
            }
        )
    triggers = []
    for item in results["triggers"]:
        observed = artifact_bytes(results_path.parent, item["observation"])
        observation = read_json(observed)
        validate(observation, "triggerObservation")
        require(
            observation["snapshot_sha256"] == results["snapshot_sha256"]
            and observation["case_id"] == item["case_id"]
            and observation["model_id"] == results["executor_model_id"],
            "trigger artifact belongs to another evaluation coordinate",
        )
        trigger = {"case_id": item["case_id"], "observation_kind": observation["observation_kind"],
                   "observation_sha256": hashlib.sha256(observed).hexdigest()}
        expected = expected_triggers[coordinate_key(item["case_id"])]
        if isinstance(expected, list):
            require(observation["observation_kind"] == "recorded-invocation-sequence",
                    "routing coverage requires a complete recorded sequence")
            trigger.update(expected_selection=expected, observed_selection=observation["observed_selection"])
        else:
            require(observation["observation_kind"] == "recorded-invocation", "Boolean trigger requires its recorded invocation")
            trigger.update(expected=expected, triggered=observation["triggered"])
        triggers.append(trigger)
    receipt = {
        "schema_version": 1,
        "kind": "evaluation",
        "method": "prepared-before-run",
        "candidate_revision": snapshot["candidate_revision"],
        "snapshot": snapshot,
        "executor_model_id": results["executor_model_id"],
        "grader_model_id": results["grader_model_id"],
        "runs_per_case": 3,
        "runs": runs,
        "triggers": triggers,
        "private_evidence": {"manifest_sha256": hashlib.sha256(raw).hexdigest()},
        "attestation": None,
    }
    validate(receipt)
    evaluate(repository, receipt)
    return receipt


def _check_reconciled_source(repository, receipt):
    """Check the public correspondence without reopening private raw artifacts."""
    snapshot, spec = receipt["snapshot"], receipt["snapshot"]["skill"]
    source = receipt["candidate_revision"]
    require(snapshot == _freeze(repository, source, spec, bind_processing=False),
            "reconciled source snapshot differs from committed source")
    cases, queries = _case_details(repository, snapshot)
    runtime = set(receipt["reconciliation"]["runtime_inputs"])
    prefix = f"plugins/{spec['plugin']}/skills/{spec['skill']}"
    _, _, fixtures = corpus(repository, snapshot)
    require(prefix + "/SKILL.md" in runtime and runtime <= set(snapshot["inputs"]),
            "declared delivered runtime inputs must include the skill and belong to bound source")
    executions, identities = set(), set()
    for run in receipt["runs"]:
        record = run["reconciliation"]
        identity = document_digest(record["execution_record"])
        require(identity not in executions, "an original execution record cannot supply two repetitions")
        executions.add(identity)
        original_identity = record["execution_identity"]["identity_sha256"]
        require(original_identity not in identities, "one original execution cannot supply two repetitions or cases")
        identities.add(original_identity)
        case = cases[coordinate_key(run["case_id"])]
        expected_inputs = runtime | set(case["fixtures"])
        require(set(record["inputs"]) == expected_inputs
                and all(value == snapshot["inputs"][name]["sha256"] for name, value in record["inputs"].items()),
                "reconciled delivered input differs from current source")
        require(record["prompt_sha256"] == hashlib.sha256(case["prompt"].encode()).hexdigest(),
                "reconciled prompt differs from current case")
        require(record["original_expectations_sha256"] == document_digest(case["expectations"])
                or record["previous_grading"] and record["adjudication"] is not None,
                "changed rubric requires original grading and adjudication lineage")
    routing_sessions = set()
    for trigger in receipt["triggers"]:
        details = trigger["reconciliation"]
        query = queries[coordinate_key(trigger["case_id"])]["query"]
        require(details["query_sha256"] == hashlib.sha256(query.encode()).hexdigest()
                and details["entrypoint_sha256"] == snapshot["inputs"][prefix + "/SKILL.md"]["sha256"],
                "reconciled discovery source or query differs")
        if trigger["observation_kind"] == "recorded-sentinel-body-load":
            required = {"body_loaded", "response_sha256", "sentinel_sha256", "negative_response_sha256", "tool_action_count", "returncode"}
            require(required <= set(details), "sentinel discovery details are incomplete")
            positive = details["body_loaded"] and details["response_sha256"] == details["sentinel_sha256"]
            negative = not details["body_loaded"] and details["response_sha256"] == details["negative_response_sha256"] and details["tool_action_count"] == 0
            require(details["returncode"] == 0 and details["sentinel_sha256"] != details["negative_response_sha256"]
                    and (positive or negative) and trigger["triggered"] == positive,
                    "sentinel discovery result differs from its recorded boundary")
        elif trigger["observation_kind"] == "recorded-sentinel-sequence":
            _check_routing_catalog(repository, snapshot, trigger)
            session = details["catalog"]["dispatch"]["child_session_sha256"]
            require(session not in routing_sessions, "one native routing session cannot supply two observations")
            routing_sessions.add(session)


def evaluate(repository, receipt):
    """Recompute coverage and thresholds without trusting a stored overall verdict."""
    cases, expected_triggers, _ = corpus(repository, receipt["snapshot"])
    check_coordinates(receipt["runs"], receipt["triggers"], cases, expected_triggers)
    reconciled = receipt.get("method") == "reconciled-after-run"
    if reconciled:
        require(receipt["processing"] == processing_snapshot(repository, receipt["processing"]["revision"],
                normalized=bool(receipt["snapshot"]["skill"].get("corpus_format"))),
                "stale processing identity")
        _check_reconciled_source(repository, receipt)
    policy_revision = receipt["processing"]["revision"] if reconciled else receipt["candidate_revision"]
    policy = read_json(source_bytes(repository, policy_revision, POLICY_PATH))
    counts = {
        (case_id, item["id"]): 0 for case_id, items in cases.items() for item in items
    }
    for run in receipt["runs"]:
        expected = {item["id"]: item["severity"] for item in cases[coordinate_key(run["case_id"])]}
        grades = run["expectations"]
        require(
            len(grades) == len(expected)
            and {item["id"] for item in grades} == set(expected),
            "expectation coverage differs from the corpus",
        )
        for grade in grades:
            require(
                grade["severity"] == expected[grade["id"]]
                and type(grade["passed"]) is bool,
                "grade severity or Boolean result differs from the corpus contract",
            )
            counts[coordinate_key(run["case_id"]), grade["id"]] += grade["passed"]
    threshold_passed = all(
        counts[case_id, item["id"]] >= policy[item["severity"]]["required_passes"]
        for case_id, items in cases.items()
        for item in items
    )
    triggers = receipt["triggers"]
    correct = 0
    for item in triggers:
        expected = expected_triggers[coordinate_key(item["case_id"])]
        if isinstance(expected, list):
            require(item.get("expected_selection") == expected and isinstance(item.get("observed_selection"), list),
                    "routing expectation differs from complete corpus sequence")
            correct += item["expected_selection"] == item["observed_selection"]
        else:
            require(type(item.get("expected")) is bool and type(item.get("triggered")) is bool
                    and item["expected"] == expected, "trigger expectation differs from corpus")
            correct += item["expected"] == item["triggered"]
    passed = threshold_passed and correct == len(triggers)
    return {
        "status": "pass" if passed else "fail",
        "reason": "threshold satisfied" if passed else "threshold failed",
        "trigger_precision": {"correct": correct, "total": len(triggers)},
    }


def check(repository, request, receipts):
    """Check declared changed skills using supplied JSON records or raw receipt bytes."""
    validate(request, "request")
    revision(repository, request["base_revision"])
    revision(repository, request["candidate_revision"])
    require(
        request.get("inventory_complete") is True,
        "complete caller-owned skill inventory is required",
    )
    keys = [spec["plugin"] + "/" + spec["skill"] for spec in request["skills"]]
    require(len(keys) == len(set(keys)), "duplicate skill inventory entry")
    require(
        set(request["changed_skills"]) <= set(keys),
        "changed skill is absent from the declared inventory",
    )
    changed = set(
        git(
            repository,
            "diff",
            "--name-only",
            "-z",
            "--no-renames",
            request["base_revision"],
            request["candidate_revision"],
            "--",
        )
        .decode()
        .split("\0")
    ) - {""}
    results = []
    for spec in request["skills"]:
        key = spec["plugin"] + "/" + spec["skill"]
        prefix = f"plugins/{spec['plugin']}/skills/{spec['skill']}/"
        behavior_paths = {
            spec["evals"],
            spec["trigger_evals"],
            *spec["behavior_inputs"],
            *spec["shared_references"],
            *(item["source"] for item in spec.get("case_selection", [])),
        }
        for path in (
            *behavior_paths,
            *spec["dependencies"],
            spec["content_lock"],
            spec.get("fixture_root", prefix[:-1]),
        ):
            relative_path(path)
        require(
            spec.get("closure_complete") is True,
            "complete caller-owned dependency closure is required",
        )
        if (
            key not in request["changed_skills"]
            and not any(
                path.startswith(prefix) or path in behavior_paths for path in changed
            )
        ):
            continue
        receipt_identity = {}
        try:
            corpus(
                repository,
                {"candidate_revision": request["candidate_revision"], "skill": spec},
            )
            require(key in receipts, "receipt missing")
            receipt = receipts[key]
            if isinstance(receipt, bytes):
                receipt_identity["receipt_raw_sha256"] = hashlib.sha256(
                    receipt
                ).hexdigest()
                receipt = read_json(receipt)
            receipt_identity["receipt_sha256"] = document_digest(receipt)
            validate(receipt)
            require(
                receipt["snapshot"]["skill"] == spec,
                "stale or wrong-skill receipt descriptor",
            )
            require(
                receipt["candidate_revision"]
                == receipt["snapshot"]["candidate_revision"],
                "receipt revision differs from its evaluated snapshot",
            )
            source = receipt["candidate_revision"]
            git(
                repository,
                "merge-base",
                "--is-ancestor",
                source,
                request["candidate_revision"],
            )
            if receipt.get("method") == "reconciled-after-run":
                observed = _freeze(repository, source, spec, bind_processing=False)
                current = _freeze(repository, request["candidate_revision"], spec, bind_processing=False)
            else:
                observed = prepare(repository, source, spec)
                current = prepare(repository, request["candidate_revision"], spec)
            require(
                receipt["snapshot"] == observed,
                "receipt snapshot differs from evaluated source",
            )
            require(
                observed["inputs"] == current["inputs"], "stale evaluated input closure"
            )
            if receipt["kind"] == "waiver":
                result = {
                    "status": "waiver-pending",
                    "operator_authority_verified": False,
                    "expiry_verified": False,
                    "reason": "separate operator decision and next-release expiry verification required",
                    "waiver_receipt_sha256": document_digest(receipt),
                }
            else:
                result = evaluate(repository, receipt)
            result["evaluated_revision"] = source
        except ReceiptError as error:
            result = {"status": "fail", "reason": str(error)}
        results.append({"skill": key, **receipt_identity, **result})
    return {
        "status": (
            "not-required"
            if not results
            else "pass"
            if all(item["status"] == "pass" for item in results)
            else "fail"
        ),
        "coverage_basis": "caller-declared-complete",
        "candidate_revision": request["candidate_revision"],
        "skills": results,
    }


class _ReceiptFiles(dict):
    """Load only receipts selected by the check; unrelated evidence is a no-op."""

    def __getitem__(self, key):
        return local_bytes(super().__getitem__(key))


def main(argv=None):
    """Run the local JSON adapter; no subcommand executes evaluations."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="command", required=True)
    preparation = commands.add_parser(
        "prepare", help="freeze declared committed evaluation inputs"
    )
    preparation.add_argument("--revision", required=True)
    preparation.add_argument("--skill-spec", type=Path, required=True)
    production = commands.add_parser(
        "produce", help="project actual local result artifacts"
    )
    production.add_argument("--snapshot", type=Path, required=True)
    production.add_argument("--results", type=Path, required=True)
    reconciliation = commands.add_parser("reconcile", help="reconcile original artifacts against current source")
    reconciliation.add_argument("--revision", required=True)
    reconciliation.add_argument("--processing-revision", required=True)
    reconciliation.add_argument("--skill-spec", type=Path, required=True)
    reconciliation.add_argument("--results", type=Path, required=True)
    checking = commands.add_parser(
        "check", help="check supplied receipts against a candidate"
    )
    checking.add_argument("--request", type=Path, required=True)
    checking.add_argument("--receipts", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(
                args.repository, args.revision, read_json(args.skill_spec.read_bytes())
            )
        elif args.command == "produce":
            result = produce(
                args.repository, read_json(args.snapshot.read_bytes()), args.results
            )
        elif args.command == "reconcile":
            result = reconcile(args.repository, args.revision,
                read_json(args.skill_spec.read_bytes()), args.results, args.processing_revision)
        else:
            request = read_json(args.request.read_bytes())
            validate(request, "request")
            supplied = _ReceiptFiles()
            for spec in request["skills"]:
                path = args.receipts / spec["plugin"] / (spec["skill"] + ".json")
                if path.exists():
                    supplied[spec["plugin"] + "/" + spec["skill"]] = path
            result = check(args.repository, request, supplied)
        print(
            json.dumps(
                result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False
            )
        )
        return 1 if args.command == "check" and result["status"] == "fail" else 0
    except ReceiptError as error:
        print(json.dumps({"status": "error", "reason": str(error)}))
        return 2
    except OSError:
        print(
            json.dumps(
                {
                    "status": "error",
                    "reason": "local input or Git executable unavailable",
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
