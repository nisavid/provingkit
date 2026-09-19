"""Narrow #111 correspondence adapter over the explicitly pinned receipt processor."""

import hashlib
import json
from pathlib import Path

from .binding import PACKAGE, REPOSITORY, adapter_source, load_processor
from .inputs import validate_plan

SKILL = "mergecraft/writing-reviewable-pr-descriptions"
CORPUS = "evals/mergecraft/skills/writing-reviewable-pr-descriptions/evals.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def processor():
    return load_processor()


def read(path):
    core, _, _ = processor()
    return core.read_json(Path(path).read_bytes().decode("utf-8"))


def write_new(path, value):
    raw = (
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
    return sha(raw)


def method_digests():
    _, _, contract = processor()
    files = {
        "scripts/mergecraft_pr_writing_evals/" + p.name: sha(p.read_bytes())
        for p in sorted(PACKAGE.iterdir())
        if p.suffix in (".py", ".json")
    }
    files.update(
        {
            path: sha((REPOSITORY / path).read_bytes())
            for path in contract["processor_files"]
        }
    )
    return files


def delivery_inputs(number, request_bytes, snapshot, inputs):
    """Retain actual request pointers; never infer delivery from snapshot membership."""
    core, _, _ = processor()
    plan = read(inputs / "input-manifest.json")
    corpus = read(inputs / "inputs/corpus.json")
    task = read(inputs / f"inputs/eval-{number}/task.json")
    request = core.read_json(request_bytes.decode("utf-8"))
    require(
        list(request) == ["prompt", "fixture", "candidate_bundle"],
        "provider payload shape differs",
    )
    require(
        request["prompt"] == task["prompt"] and request["fixture"] == task["fixture"],
        "supplied task or fixture differs",
    )
    paths = plan["case_instruction_paths"][str(number)]
    require(list(request["candidate_bundle"]) == paths, "delivered runtime set differs")
    fixtures = [
        "evals/mergecraft/skills/" + p for p in corpus["evals"][number]["files"]
    ]
    require(len(fixtures) == 1, "fixed case needs its one original fixture")
    values = {**request["candidate_bundle"], fixtures[0]: request["fixture"]}
    references = {}
    for path, value in values.items():
        require(
            isinstance(value, str)
            and sha(value.encode("utf-8"))
            == snapshot["inputs"].get(path, {}).get("sha256"),
            "delivered input differs from committed source: " + path,
        )
        pointer = (
            "/fixture"
            if path == fixtures[0]
            else "/candidate_bundle/" + path.replace("~", "~0").replace("/", "~1")
        )
        reference = {
            "path": f"eval-{number}/with_skill/request.json",
            "sha256": sha(request_bytes),
            "format": "json",
            "pointer": pointer,
        }
        core.validate(reference, "evidenceReference")
        references[path] = {"representation": "utf8", "value": reference}
    return references


def delivery_table(coordinates):
    return {
        "runtime_inputs": sorted(
            {path for c in coordinates for path in c["input_paths"]}
        ),
        "case_runtime_inputs": [
            {"case_id": c["receipt_case_id"], "runtime_inputs": c["input_paths"]}
            for c in coordinates
        ],
        "basis": "Exact explicitly supplied candidate_bundle keys, separate from fixtures and full snapshot freshness.",
        "receipt_compatibility": "Exact per-case declaration for reconciliation with the bound reviewed processor; application collection alone does not supply discovery or a public receipt.",
    }


def verify_preparation(
    source,
    binding,
    plan,
    snapshot_path,
    snapshot_file_hash,
    snapshot_hash,
    descriptor_path,
    descriptor_hash,
    inputs,
):
    core, inventory, contract = processor()
    validate_plan(plan)
    require(
        plan["source_revision"] == binding["repository_head"], "frozen source differs"
    )
    method_source = adapter_source(source, binding["repository_head"])
    require(plan["adapter_source"] == method_source, "frozen adapter source differs")
    for path, digest in contract["processor_files"].items():
        require(
            sha(core.source_bytes(source, plan["processing_revision"], path)) == digest,
            "processing commit differs: " + path,
        )
    require(
        all(
            (
                snapshot_path,
                snapshot_file_hash,
                snapshot_hash,
                descriptor_path,
                descriptor_hash,
            )
        ),
        "receipt snapshot and descriptor bindings are required",
    )
    source = Path(source).resolve()
    revision = core.revision(source, binding["repository_head"])
    require(
        core.git(source, "rev-parse", "HEAD").decode().strip() == revision,
        "source checkout differs",
    )
    snapshot_raw = Path(snapshot_path).read_bytes()
    descriptor_raw = Path(descriptor_path).read_bytes()
    require(sha(snapshot_raw) == snapshot_file_hash, "snapshot file differs")
    require(sha(descriptor_raw) == descriptor_hash, "descriptor file differs")
    snapshot = core.read_json(snapshot_raw.decode("utf-8"))
    descriptor = core.read_json(descriptor_raw.decode("utf-8"))
    core.validate(snapshot, "snapshot")
    require(
        core.document_digest(snapshot) == snapshot_hash,
        "snapshot document digest differs",
    )
    observed = inventory.descriptor(source, revision, SKILL)
    require(observed["status"] == "ready", "selected descriptor is unresolved")
    require(descriptor == observed, "descriptor differs from committed source")
    require(
        snapshot == inventory.prepare(source, revision, SKILL),
        "snapshot differs from committed source",
    )
    direct = read(inputs / "native-reference/trigger-correspondence.json")
    queries = read(inputs / "native-reference/frozen-direct-queries.json")
    require(
        len(descriptor["triggers"]) == 19
        and [
            (
                row["case_id"],
                row["query"],
                row["should_trigger"],
                row["source"]["sha256"],
            )
            for row in descriptor["triggers"]
        ]
        == [
            (
                row["original_coordinate"],
                query["query"],
                query["should_trigger"],
                direct["source_sha256"],
            )
            for row, query in zip(direct["rows"], queries)
        ],
        "direct query source or coordinates differ before preparation",
    )
    policy = read(inputs / "withheld/expectation-policy.json")
    owner = read(inputs / "withheld/expectation-policy-owner-review.json")
    require(
        owner["status"] == "source-mapping-accepted"
        and owner["mapping_sha256"]
        == sha((inputs / "withheld/expectation-policy.json").read_bytes()),
        "accepted expectation mapping differs",
    )
    expected = {}
    for index, case in enumerate(policy["cases"]):
        coordinate = {
            "source": CORPUS,
            "pointer": f"/evals/{index}",
            "id": case["case_id"],
        }
        expected[core.coordinate_key(coordinate)] = (coordinate, case["expectations"])
    require(
        len(descriptor["cases"]) == 11
        and {core.coordinate_key(c["case_id"]) for c in descriptor["cases"]}
        == set(expected),
        "application coverage differs from the fixed eleven cases",
    )
    for case in descriptor["cases"]:
        _, expectations = expected[core.coordinate_key(case["case_id"])]
        require(
            [
                {k: e[k] for k in ("id", "text", "severity")}
                for e in case["expectations"]
            ]
            == [
                {
                    "id": e["id"],
                    "text": e["expectation_text"],
                    "severity": e["severity"],
                }
                for e in expectations
            ],
            "original expectations or accepted mapping differ",
        )
    require(
        all(
            row["source"] != "evals/skill-routing-matrix.json"
            for row in snapshot["skill"]["case_selection"]
        ),
        "Phase 2 adoption is outside this plan",
    )
    for path in contract["processor_files"]:
        require(
            snapshot["inputs"].get(path, {}).get("sha256")
            == contract["processor_files"][path],
            "integrated processor differs from reviewed P: " + path,
        )
    for path, digest in binding["source_sha256"].items():
        require(
            snapshot["inputs"].get(path, {}).get("sha256") == digest,
            "source binding is absent or differs: " + path,
        )
    for path, identity in snapshot["inputs"].items():
        working = source / path
        require(
            working.is_file()
            and not working.is_symlink()
            and sha(working.read_bytes()) == identity["sha256"]
            and bool(working.stat().st_mode & 0o111) == (identity["mode"] == "100755"),
            "working input differs from committed snapshot: " + path,
        )
    require(
        core.source_bytes(source, revision, CORPUS)
        == (inputs / "inputs/corpus.json").read_bytes(),
        "committed corpus differs",
    )
    return {
        "source_root": str(source),
        "source_revision": revision,
        "processor_revision": plan["processing_revision"],
        "processing_identity_kind": plan["processing_identity_kind"],
        "published_processor_revision": plan["published_processor_revision"],
        "adapter_source": method_source,
        "snapshot_path": "receipt/snapshot.json",
        "snapshot_file_sha256": snapshot_file_hash,
        "snapshot_sha256": snapshot_hash,
        "descriptor_path": "receipt/descriptor.json",
        "descriptor_sha256": descriptor_hash,
        "case_coordinates": {
            str(c["case_id"]["id"]): c["case_id"] for c in descriptor["cases"]
        },
        "claim": "Prepared supplied-instruction applications; trigger observations remain separate.",
    }


def normalized_rubrics(descriptor):
    return {
        "kind": "preparation-time-grader-only-rubrics",
        "acceptance_reference": "https://github.com/nisavid/provingkit/issues/111#issuecomment-5729835933",
        "cases": [
            {
                "case_id": case["case_id"],
                "expectations": [
                    {key: expectation[key] for key in ("id", "text", "severity")}
                    for expectation in case["expectations"]
                ],
            }
            for case in descriptor["cases"]
        ],
    }


def verify_manifest(root, manifest_hash):
    root = Path(root).resolve()
    inputs = root / "method-inputs"
    raw = (root / "manifest.json").read_bytes()
    require(sha(raw) == manifest_hash, "execution manifest differs")
    manifest = read(root / "manifest.json")
    require(
        manifest["status"] == "prepared-final-source-awaiting-launch-review",
        "final source review is pending",
    )
    require(manifest["method_sha256"] == method_digests(), "reviewed method differs")
    plan = read(inputs / "input-manifest.json")
    require(
        manifest["input_manifest_sha256"]
        == sha((inputs / "input-manifest.json").read_bytes()),
        "input plan differs",
    )
    for path, digest in plan["file_sha256"].items():
        require(
            sha((inputs / path).read_bytes()) == digest, "frozen input differs: " + path
        )
    for key in (
        "provider",
        "client",
        "requested_model",
        "requested_effort",
        "client_binding",
        "timeout_seconds",
        "maximum_concurrency",
        "conditions",
        "repetitions",
        "run_coordinates",
        "thresholds",
    ):
        require(manifest[key] == plan[key], "fixed application plan differs: " + key)
    for path, digest in manifest["artifact_sha256"].items():
        require(
            sha((root / path).read_bytes()) == digest, "prepared input differs: " + path
        )
    receipt = manifest["receipt"]
    binding = read(root / "final-source-binding.json")
    require(manifest["source_sha256"] == binding["source_sha256"], "source map differs")
    observed = verify_preparation(
        Path(receipt["source_root"]),
        binding,
        plan,
        root / receipt["snapshot_path"],
        receipt["snapshot_file_sha256"],
        receipt["snapshot_sha256"],
        root / receipt["descriptor_path"],
        receipt["descriptor_sha256"],
        inputs,
    )
    require(receipt == observed, "receipt binding differs")
    snapshot = read(root / receipt["snapshot_path"])
    require(
        read(root / "receipt/grading-rubrics.json")
        == normalized_rubrics(read(root / receipt["descriptor_path"])),
        "prepared grader rubric differs",
    )
    require(
        len(manifest["coordinates"]) == 11
        and [c["id"] for c in manifest["coordinates"]] == list(range(11)),
        "case metadata coverage differs",
    )
    for metadata in manifest["coordinates"]:
        number = metadata["id"]
        require(
            metadata == read(root / f"eval-{number}/eval_metadata.json"),
            "case metadata differs",
        )
        require(
            metadata["receipt_case_id"] == receipt["case_coordinates"][str(number)],
            "case coordinate differs",
        )
        request_bytes = (root / f"eval-{number}/with_skill/request.json").read_bytes()
        evidence = delivery_inputs(number, request_bytes, snapshot, inputs)
        require(
            metadata["input_paths"] == plan["case_instruction_paths"][str(number)]
            and metadata["input_evidence"] == evidence,
            "per-case input declaration differs",
        )
        require(
            metadata["request_sha256"] == sha(request_bytes), "request digest differs"
        )
        prompt = (
            (inputs / "inputs/prompt-prefix.txt").read_bytes() + b"\n\n" + request_bytes
        )
        require(
            (root / f"eval-{number}/with_skill/prompt.txt").read_bytes() == prompt
            and sha(prompt) == metadata["submitted_prompt_sha256"],
            "submitted prompt differs",
        )
    require(
        manifest["delivery"] == delivery_table(manifest["coordinates"]),
        "complete per-case delivery table or union differs",
    )
    return manifest


def execution_observation(root, manifest, manifest_hash, number, repetition):
    from .run_application import command_for, execution_record, launch_metadata, observe

    coordinate = next(
        c
        for c in manifest["run_coordinates"]
        if c["case"] == number and c["repetition"] == repetition
    )
    metadata = next(c for c in manifest["coordinates"] if c["id"] == number)
    run = root / coordinate["output_directory"]
    require(
        read(run / "command.json") == command_for(root, manifest),
        "recorded command differs",
    )
    require(
        read(run / "launch-metadata.json")
        == launch_metadata(manifest, manifest_hash, metadata, coordinate),
        "recorded launch binding differs",
    )
    result = read(run / "result.json")
    response, observed = observe(
        run,
        result["returncode"],
        result["duration_seconds"],
        result["started_at_utc"],
        result["finished_at_utc"],
        coordinate,
        result["launch_error"],
        result["timed_out"],
    )
    require(
        result == observed and observed["valid_application"],
        "application record is invalid or differs from raw streams",
    )
    require(
        len(observed["thread_ids"]) == 1
        and isinstance(observed["thread_ids"][0], str)
        and observed["thread_ids"][0].strip(),
        "original session identity is unavailable or ambiguous",
    )
    require(
        (run / "response.txt").read_bytes() == response.encode("utf-8"),
        "response differs from raw streams",
    )
    original = read(run / "execution-record.json")
    require(
        original
        == execution_record(manifest, manifest_hash, metadata, coordinate, result),
        "original execution record differs",
    )
    envelope = {
        "snapshot_sha256": manifest["receipt"]["snapshot_sha256"],
        "case_id": metadata["receipt_case_id"],
        "repetition": repetition,
        "model_id": manifest["requested_model"],
        "response": response,
    }
    core, _, _ = processor()
    core.validate(envelope, "execution")
    paths = [
        run / name
        for name in (
            "command.json",
            "launch-metadata.json",
            "transcript.jsonl",
            "stderr.log",
            "response.txt",
            "result.json",
            "execution-record.json",
        )
    ]
    paths += [
        root / f"eval-{number}/with_skill" / name
        for name in ("request.json", "prompt.txt")
    ]
    provenance = {
        "runner_manifest_sha256": manifest_hash,
        "source_revision": manifest["receipt"]["source_revision"],
        "runtime_inputs": metadata["input_paths"],
        "input_evidence": metadata["input_evidence"],
        "execution_record": str((run / "execution-record.json").relative_to(root)),
        "execution_record_sha256": sha((run / "execution-record.json").read_bytes()),
        "thread_id": observed["thread_ids"][0],
        "files": {str(p.relative_to(root)): sha(p.read_bytes()) for p in paths},
    }
    return envelope, provenance


def execution_paths(number, repetition):
    return (
        f"receipt/executions/case-{number}/repetition-{repetition}.json",
        f"receipt/correspondence/case-{number}/repetition-{repetition}-execution.json",
    )


def project_execution(root, manifest_hash, number, repetition):
    root = Path(root).resolve()
    manifest = verify_manifest(root, manifest_hash)
    envelope, provenance = execution_observation(
        root, manifest, manifest_hash, number, repetition
    )
    output, correspondence = execution_paths(number, repetition)
    for path in (output, correspondence):
        if (root / path).exists():
            raise FileExistsError(root / path)
    digest = write_new(root / output, envelope)
    write_new(
        root / correspondence,
        {**provenance, "executor_output": output, "executor_output_sha256": digest},
    )
    return {
        "executor_output": output,
        "executor_output_sha256": digest,
        "correspondence": correspondence,
    }


def verified_execution(root, manifest, manifest_hash, number, repetition):
    envelope, provenance = execution_observation(
        root, manifest, manifest_hash, number, repetition
    )
    output, correspondence = execution_paths(number, repetition)
    digest = sha((root / output).read_bytes())
    require(
        read(root / output) == envelope,
        "execution envelope differs from original record",
    )
    require(
        read(root / correspondence)
        == {**provenance, "executor_output": output, "executor_output_sha256": digest},
        "execution correspondence differs",
    )
    return envelope, output, digest


def grading_paths(number, repetition):
    return (
        f"receipt/gradings/case-{number}/repetition-{repetition}.json",
        f"receipt/correspondence/case-{number}/repetition-{repetition}-grading.json",
    )


def grading_observation(
    root,
    manifest,
    manifest_hash,
    number,
    repetition,
    grade_path,
    grade_hash,
    configuration_path,
    configuration_hash,
):
    execution, output, output_hash = verified_execution(
        root, manifest, manifest_hash, number, repetition
    )
    inputs = {}
    for path, digest in (
        (grade_path, grade_hash),
        (configuration_path, configuration_hash),
    ):
        path = Path(path).resolve()
        require(
            path.is_relative_to(root),
            "grading input must belong to the private run directory",
        )
        require(sha(path.read_bytes()) == digest, "original grading input differs")
        inputs[str(path.relative_to(root))] = digest
    grade = read(grade_path)
    configuration = read(configuration_path)
    require(
        grade["executor_output_sha256"] == output_hash,
        "grade belongs to another executor output",
    )
    require(
        grade["response_sha256"] == sha(execution["response"].encode()),
        "grade response differs",
    )
    for key in ("snapshot_sha256", "case_id", "repetition"):
        require(grade[key] == execution[key], "grade coordinate differs: " + key)
    require(
        grade["model_id"] == configuration["model_id"]
        and isinstance(configuration.get("basis"), str)
        and configuration["basis"].strip(),
        "grader configuration differs or has no recorded basis",
    )
    policy = read(root / "method-inputs/withheld/expectation-policy.json")
    expected = next(
        c["expectations"] for c in policy["cases"] if c["case_id"] == number
    )
    judgments = grade["expectations"]
    require(
        isinstance(judgments, list)
        and len(judgments) == len(expected)
        and {e["id"] for e in judgments} == {e["id"] for e in expected},
        "grading expectation coverage differs",
    )
    require(
        all(
            type(e["passed"]) is bool
            and isinstance(e.get("evidence"), str)
            and e["evidence"].strip()
            for e in judgments
        ),
        "grading needs Boolean judgments and concrete evidence",
    )
    require(
        isinstance(grade.get("supplemental_observations"), list),
        "retain supplementary observations explicitly",
    )
    by_id = {e["id"]: e["passed"] for e in judgments}
    envelope = {
        k: grade[k]
        for k in (
            "snapshot_sha256",
            "case_id",
            "repetition",
            "model_id",
            "executor_output_sha256",
        )
    }
    envelope["expectations"] = [
        {"id": e["id"], "passed": by_id[e["id"]]} for e in expected
    ]
    core, _, _ = processor()
    core.validate(envelope, "grading")
    provenance = {
        "runner_manifest_sha256": manifest_hash,
        "original_grade": str(Path(grade_path).resolve().relative_to(root)),
        "grader_configuration": str(
            Path(configuration_path).resolve().relative_to(root)
        ),
        "files": inputs,
        "executor_output": output,
        "executor_output_sha256": output_hash,
        "supplemental_observations_sha256": core.document_digest(
            grade["supplemental_observations"]
        ),
        "model_basis": "Recorded caller-supplied grader configuration; not served-model attestation.",
    }
    return envelope, provenance


def project_grading(
    root,
    manifest_hash,
    number,
    repetition,
    grade_path,
    grade_hash,
    configuration_path,
    configuration_hash,
):
    root = Path(root).resolve()
    manifest = verify_manifest(root, manifest_hash)
    envelope, provenance = grading_observation(
        root,
        manifest,
        manifest_hash,
        number,
        repetition,
        grade_path,
        grade_hash,
        configuration_path,
        configuration_hash,
    )
    output, correspondence = grading_paths(number, repetition)
    for path in (output, correspondence):
        if (root / path).exists():
            raise FileExistsError(root / path)
    digest = write_new(root / output, envelope)
    write_new(
        root / correspondence,
        {**provenance, "grading": output, "grading_sha256": digest},
    )
    return {
        "grading": output,
        "grading_sha256": digest,
        "correspondence": correspondence,
    }


def collect_applications(root, manifest_hash, output):
    root, output = Path(root).resolve(), Path(output) if output is not None else None
    if output is not None and output.exists():
        raise FileExistsError(output)
    manifest = verify_manifest(root, manifest_hash)
    planned = manifest["run_coordinates"]
    expected_attempts = {root / c["output_directory"] for c in planned}
    require(
        set(root.glob("eval-*/with_skill/repetition-*/attempt-*")) <= expected_attempts,
        "unplanned attempt directory",
    )
    for kind in ("executions", "gradings"):
        expected = {
            root / f"receipt/{kind}/case-{c['case']}/repetition-{c['repetition']}.json"
            for c in planned
        }
        require(
            set((root / "receipt" / kind).glob("case-*/repetition-*.json")) <= expected,
            "unplanned " + kind + " envelope",
        )
    runs, grader_models, sessions = [], set(), set()
    for coordinate in planned:
        number, repetition = coordinate["case"], coordinate["repetition"]
        execution, executor_path, executor_hash = verified_execution(
            root, manifest, manifest_hash, number, repetition
        )
        execution_correspondence = read(root / execution_paths(number, repetition)[1])
        thread_id = execution_correspondence["thread_id"]
        require(
            thread_id not in sessions,
            "one original session cannot supply multiple coordinates",
        )
        sessions.add(thread_id)
        grading_path, correspondence_path = grading_paths(number, repetition)
        correspondence = read(root / correspondence_path)
        grade_path, configuration_path = (
            correspondence["original_grade"],
            correspondence["grader_configuration"],
        )
        grading, provenance = grading_observation(
            root,
            manifest,
            manifest_hash,
            number,
            repetition,
            root / grade_path,
            correspondence["files"][grade_path],
            root / configuration_path,
            correspondence["files"][configuration_path],
        )
        grading_hash = sha((root / grading_path).read_bytes())
        require(
            read(root / grading_path) == grading,
            "grading envelope differs from original judgments",
        )
        require(
            correspondence
            == {**provenance, "grading": grading_path, "grading_sha256": grading_hash},
            "grading correspondence differs",
        )
        grader_models.add(grading["model_id"])
        runs.append(
            {
                "case_id": execution["case_id"],
                "repetition": repetition,
                "executor_output": executor_path,
                "executor_output_sha256": executor_hash,
                "execution_correspondence_sha256": sha(
                    (root / execution_paths(number, repetition)[1]).read_bytes()
                ),
                "grading": grading_path,
                "grading_sha256": grading_hash,
                "grading_correspondence_sha256": sha(
                    (root / correspondence_path).read_bytes()
                ),
                "expectations": grading["expectations"],
            }
        )
    require(len(grader_models) == 1, "mixed grader model IDs require an owner decision")
    judgments = [e for run in runs for e in run["expectations"]]
    require(
        len(runs) == 33 and len(judgments) == 129,
        "application or judgment count differs",
    )
    result = {
        "kind": "pr-writing-application-index",
        "status": "applications-complete-discovery-and-reconciliation-pending",
        "runner_manifest_sha256": manifest_hash,
        "receipt_snapshot_sha256": manifest["receipt"]["snapshot_sha256"],
        "source_revision": manifest["receipt"]["source_revision"],
        "processor_revision": manifest["receipt"]["processor_revision"],
        "processing_identity_kind": manifest["receipt"]["processing_identity_kind"],
        "executor_model_id": manifest["requested_model"],
        "grader_model_id": next(iter(grader_models)),
        "application_runs": len(runs),
        "judgment_count": len(judgments),
        "negative_judgment_count": sum(not e["passed"] for e in judgments),
        "runs": runs,
        "delivery": manifest["delivery"],
        "public_receipt_ready": False,
        "receipt_route_dependency": "A complete source-bound set of nineteen original sentinel traces and reconciliation/check with the bound reviewed processor remain required. This application index is not a receipt.",
        "limits": [
            "Configured model metadata is not served-model attestation.",
            "Application index only: no trigger, native composition, installation, or receipt-threshold claim.",
            "Original raw execution and grading records remain the evidence; envelopes do not replace them.",
        ],
    }
    if output is not None:
        write_new(output, result)
    return result


def retained_file(root, relative):
    """Read a regular original file beneath the declared evidence directory."""
    path = Path(relative)
    require(
        not path.is_absolute() and ".." not in path.parts,
        "evidence path is not relative",
    )
    result = root / path
    require(
        result.is_file()
        and not any(
            p.is_symlink() for p in (result, *result.parents) if p != root.parent
        ),
        "evidence file is missing or symbolic",
    )
    require(
        result.resolve().is_relative_to(root.resolve()),
        "evidence escapes its directory",
    )
    return result.read_bytes()


def evidence_reference(root, relative, pointer="", format="json"):
    raw = retained_file(root, relative)
    return {
        "path": str(relative),
        "sha256": sha(raw),
        "format": format,
        "pointer": pointer,
    }


def discovery_copies(freeze, expected_hash, manifest):
    """Check original native records; preserve wrong but complete decisions."""
    inputs = Path(manifest["_root"]) / "method-inputs"
    core, _, _ = processor()
    freeze = Path(freeze).resolve()
    raw = retained_file(freeze, "manifest.json")
    require(sha(raw) == expected_hash, "native manifest differs")
    native = read(freeze / "manifest.json")
    method = read(inputs / "native-reference/method-contract.json")
    require(
        native.get("helper_sha256") == method["helper_sha256"],
        "native recorder method differs",
    )
    constructors = native.get("selection_runner_sha256", {})
    require(
        len(constructors) == len(method["selection_constructor_sha256"])
        and {Path(name).name: digest for name, digest in constructors.items()}
        == method["selection_constructor_sha256"],
        "native prompt constructor binding differs",
    )
    for path, digest in native["artifacts"].items():
        require(
            sha(retained_file(freeze, path)) == digest,
            "native frozen artifact differs: " + path,
        )
    require(
        "selection-plan.json" in native["artifacts"],
        "native selection plan is not frozen",
    )
    snapshot = read(Path(manifest["_root"]) / manifest["receipt"]["snapshot_path"])
    entry = (
        "plugins/"
        + SKILL.split("/")[0]
        + "/skills/"
        + SKILL.split("/")[1]
        + "/SKILL.md"
    )
    queries_path = CORPUS.removesuffix("evals.json") + "trigger-evals.json"
    for path in (entry, queries_path):
        require(
            native["source_sha256"].get(path)
            == snapshot["inputs"].get(path, {}).get("sha256"),
            "native source differs: " + path,
        )
    require(
        native["codex"]["model"] == manifest["requested_model"]
        and native["codex"]["effort"] == manifest["requested_effort"],
        "native requested model or effort differs",
    )
    require(
        native["codex"]["path"] == manifest["client_binding"]["path"]
        and native["codex"]["sha256"] == manifest["client_binding"]["sha256"],
        "native recorded client differs",
    )
    expected = read(inputs / "native-reference/selection-contract.json")["rows"]
    plan = read(freeze / "selection-plan.json")
    rows = [row for row in plan if row["skill"] == SKILL.split("/")[1]]
    require(
        len(rows) == 19
        and [{key: row.get(key) for key in fixed} for row, fixed in zip(rows, expected)]
        == expected,
        "native direct query coverage or prompt differs",
    )
    copies = {
        "manifest.json": raw,
        "selection-plan.json": retained_file(freeze, "selection-plan.json"),
    }
    records = []
    sessions = set()
    for row in rows:
        prefix = "selection-runs/" + row["id"]
        run = freeze / prefix
        record_raw = retained_file(run, "record.json")
        record = core.read_json(record_raw)
        require(
            record["manifest_sha256"] == expected_hash
            and record["case_id"] == row["id"],
            "native record identity differs",
        )
        require(
            record["technically_valid"] is True
            and type(record["exit_code"]) is int
            and record["exit_code"] == 0
            and record["timed_out"] is False
            and record["launch_error"] is None
            and record["source_error"] is None,
            "native attempt did not complete successfully",
        )
        probe = f"home/.agents/skills/{row['skill']}/SKILL.md"
        names = {
            "case.json",
            "command.json",
            "prompt.txt",
            "query.json",
            "environment.json",
            "stdout.jsonl",
            "stderr.log",
            "response.txt",
            probe,
        }
        require(
            set(record["artifact_sha256"]) == names,
            "native recorded artifact coverage differs",
        )
        require(
            {str(p.relative_to(run)) for p in run.rglob("*") if p.is_file()}
            == names | {"record.json"},
            "native attempt has extra or missing files",
        )
        for name, digest in record["artifact_sha256"].items():
            content = retained_file(run, name)
            require(sha(content) == digest, "native original artifact differs: " + name)
            copies[prefix + "/" + name] = content
        copies[prefix + "/record.json"] = record_raw
        require(read(run / "case.json") == row, "native executed case differs")
        command = [
            native["codex"]["path"],
            "exec",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "-C",
            str(run / "cwd"),
            "-c",
            "model_reasoning_effort=xhigh",
            "-m",
            manifest["requested_model"],
            row["probe_prompt"],
        ]
        require(
            read(run / "command.json") == row["command"] == command,
            "native executed command differs",
        )
        require(
            read(run / "query.json") == {"query": row["query"], "effort": "xhigh"},
            "native executed query differs",
        )
        require(
            retained_file(run, "prompt.txt") == row["probe_prompt"].encode(),
            "native executed prompt differs",
        )
        require(
            row["probe_file"] in native["artifacts"]
            and retained_file(run, probe) == retained_file(freeze, row["probe_file"]),
            "native executed probe differs",
        )
        copies[row["probe_file"]] = retained_file(freeze, row["probe_file"])
        # Strict LF-delimited parsing; neither Unicode line separators nor bad JSON is normalized.
        events = [
            core.read_json(line)
            for line in retained_file(run, "stdout.jsonl").decode("utf-8").split("\n")
            if line.strip()
        ]
        retained_file(run, "stderr.log").decode("utf-8")
        require(
            all(isinstance(e, dict) for e in events), "native protocol object missing"
        )
        starts = [e for e in events if e.get("type") == "thread.started"]
        require(
            len(starts) == 1
            and isinstance(starts[0].get("thread_id"), str)
            and starts[0]["thread_id"]
            and starts[0]["thread_id"] not in sessions,
            "native original session is missing or reused",
        )
        sessions.add(starts[0]["thread_id"])
        messages = [
            e["item"]["text"]
            for e in events
            if e.get("type") == "item.completed"
            and e.get("item", {}).get("type") == "agent_message"
        ]
        response = "\n".join(messages)
        require(
            response.encode() == retained_file(run, "response.txt"),
            "native response differs from raw trace",
        )
        tools = [
            e
            for e in events
            if isinstance(e.get("item"), dict)
            and not (
                e["item"].get("type") == "agent_message"
                and e.get("type") == "item.completed"
            )
            and e["item"].get("type") != "reasoning"
        ]
        observed = {
            "encoding_errors": [],
            "protocol_errors": [],
            "protocol_valid": True,
            "messages": messages,
            "events": events,
            "tool_events": tools,
            "triggered": row["marker"] in response,
            "decision_matches_expected": (row["marker"] in response)
            == row["should_trigger"],
        }
        require(
            all(record.get(k) == v for k, v in observed.items()),
            "native recorded observations differ from raw trace",
        )
        records.append((row, prefix, probe))
    return copies, records


def assemble_reconciliation(
    root, manifest_hash, discovery_freeze, discovery_hash, output
):
    """Create private input for the bound processor; never execute, grade, retry, or publish."""
    root, output = Path(root).resolve(), Path(output).resolve()
    require(output.parent == root, "reconciliation must be at the application root")
    inputs = root / "method-inputs"
    destination = root / "receipt-source/discovery"
    provenance_path = root / "receipt-source/provenance.json"
    for path in (output, destination, provenance_path):
        if path.exists():
            raise FileExistsError(path)
    manifest = verify_manifest(root, manifest_hash)
    index = collect_applications(root, manifest_hash, None)
    copies, native_rows = discovery_copies(
        discovery_freeze, discovery_hash, {**manifest, "_root": str(root)}
    )
    core, inventory, _ = processor()
    runs = []
    for coordinate in manifest["run_coordinates"]:
        number, repetition = coordinate["case"], coordinate["repetition"]
        metadata = manifest["coordinates"][number]
        run = coordinate["output_directory"]
        original = run + "/execution-record.json"
        correspondence = read(root / grading_paths(number, repetition)[1])
        grade, configuration = (
            correspondence["original_grade"],
            correspondence["grader_configuration"],
        )
        config = read(root / configuration)
        require(
            config.get("model_basis") in ("configured", "requested", "reported"),
            "grader needs its explicit recorded model basis",
        )
        rich_grade = read(root / grade)
        require(
            not rich_grade.get("previous_grading")
            and rich_grade.get("adjudication") is None,
            "adjudicated grade needs a separately reviewed lineage adapter",
        )
        rubric = evidence_reference(
            root, "receipt/grading-rubrics.json", f"/cases/{number}/expectations"
        )
        ref = lambda path, pointer="", format="json": evidence_reference(
            root, path, pointer, format
        )
        runs.append(
            {
                "case_id": metadata["receipt_case_id"],
                "repetition": repetition,
                "execution_record": ref(original),
                "original_revision": ref(original, "/source_revision"),
                "original_corpus_sha256": ref(original, "/original_corpus_sha256"),
                "prompt": ref(f"eval-{number}/with_skill/request.json", "/prompt"),
                "response": ref(run + "/response.txt", format="utf8"),
                "inputs": metadata["input_evidence"],
                "executor_model": {
                    "basis": "requested",
                    "value": ref(original, "/requested_model"),
                },
                "grader_model": {
                    "basis": config["model_basis"],
                    "value": ref(configuration, "/model_id"),
                },
                "grading_record": ref(grade),
                "graded_response": {
                    "representation": "sha256",
                    "value": ref(grade, "/response_sha256"),
                },
                "original_expectations": rubric,
                "rubric": {"representation": "expectations", "value": rubric},
                "grades": ref(grade, "/expectations"),
                "previous_grading": [],
                "adjudication": None,
            }
        )
    triggers = []
    correspondence = read(inputs / "native-reference/trigger-correspondence.json")[
        "rows"
    ]
    for (row, prefix, probe), fixed in zip(native_rows, correspondence):

        def copied_ref(name, pointer="", format="json", prefix=prefix):
            relative = prefix + "/" + name
            return {
                "path": "receipt-source/discovery/" + relative,
                "sha256": sha(copies[relative]),
                "format": format,
                "pointer": pointer,
            }

        triggers.append(
            {
                "case_id": fixed["original_coordinate"],
                "observation_kind": "recorded-sentinel-body-load",
                "record": copied_ref("record.json"),
                "model": {
                    "basis": "requested",
                    "value": copied_ref("command.json", "/13"),
                },
                "query": copied_ref("query.json", "/query"),
                "trace": copied_ref("stdout.jsonl", format="jsonl"),
                "probe_skill": copied_ref(probe, format="utf8"),
                "probe_prompt": copied_ref("prompt.txt", format="utf8"),
                "sentinel": copied_ref("case.json", "/marker"),
                "returncode": copied_ref("record.json", "/exit_code"),
                "limits": [
                    "Temporary name/description selection and sentinel body-read observation; not current body execution or native plugin invocation.",
                    "No host isolation or served-model attestation; model identity is requested configuration.",
                ],
            }
        )
    result = {
        "schema_version": 1,
        "method": "reconciled-after-run",
        "executor_model_id": index["executor_model_id"],
        "grader_model_id": index["grader_model_id"],
        "runtime_inputs": index["delivery"]["runtime_inputs"],
        "runtime_inputs_complete": True,
        "case_runtime_inputs": index["delivery"]["case_runtime_inputs"],
        "runs": runs,
        "triggers": triggers,
    }
    core.validate(result, "reconciliationResults")
    destination.mkdir(parents=True, exist_ok=False)
    for relative, raw in copies.items():
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
    digest = write_new(output, result)
    # The actual pinned processor interprets raw traces and the complete original records.
    # On failure keep the new capsule and explicit failure; never retry or erase evidence.
    provenance = {
        "kind": "private-original-to-copy-reconciliation",
        "processing_revision": manifest["receipt"]["processor_revision"],
        "processing_identity_kind": manifest["receipt"]["processing_identity_kind"],
        "application_manifest_sha256": manifest_hash,
        "prepared_snapshot_sha256": manifest["receipt"]["snapshot_sha256"],
        "original_discovery_root": str(Path(discovery_freeze).resolve()),
        "original_discovery_manifest_sha256": discovery_hash,
        "copies": {
            name: {
                "source_sha256": sha(raw),
                "destination": "receipt-source/discovery/" + name,
                "copied_sha256": sha(raw),
            }
            for name, raw in copies.items()
        },
        "reconciliation_sha256": digest,
        "application_runs": 33,
        "judgments": 129,
        "direct_triggers": 19,
        "public_receipt_ready": False,
    }
    try:
        receipt = inventory.reconcile(
            Path(manifest["receipt"]["source_root"]),
            manifest["receipt"]["source_revision"],
            SKILL,
            output,
            manifest["receipt"]["processor_revision"],
        )
        provenance["processor_validation"] = {
            "status": "complete",
            "thresholds": core.evaluate(
                Path(manifest["receipt"]["source_root"]), receipt
            ),
            "reconciliation_snapshot_sha256": core.document_digest(receipt["snapshot"]),
        }
    except (ValueError, OSError, KeyError, TypeError) as error:
        provenance["processor_validation"] = {"status": "invalid", "reason": str(error)}
        write_new(provenance_path, provenance)
        raise
    write_new(provenance_path, provenance)
    return {
        "results": str(output),
        "sha256": digest,
        "provenance_sha256": sha(provenance_path.read_bytes()),
        "public_receipt_ready": False,
        "processor_validation": provenance["processor_validation"],
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("project-execution", "project-grading"):
        command = commands.add_parser(name)
        command.add_argument("--case", type=int, choices=range(11), required=True)
        command.add_argument("--repetition", type=int, choices=(1, 2, 3), required=True)
        if name == "project-grading":
            command.add_argument("--grade", type=Path, required=True)
            command.add_argument("--grade-sha256", required=True)
            command.add_argument("--grader-configuration", type=Path, required=True)
            command.add_argument("--grader-configuration-sha256", required=True)
    commands.add_parser("collect-applications").add_argument(
        "--output", type=Path, required=True
    )
    command = commands.add_parser("assemble-reconciliation")
    command.add_argument("--discovery-freeze", type=Path, required=True)
    command.add_argument("--discovery-manifest-sha256", required=True)
    command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "project-execution":
            result = project_execution(
                args.root, args.manifest_sha256, args.case, args.repetition
            )
        elif args.command == "project-grading":
            result = project_grading(
                args.root,
                args.manifest_sha256,
                args.case,
                args.repetition,
                args.grade,
                args.grade_sha256,
                args.grader_configuration,
                args.grader_configuration_sha256,
            )
        elif args.command == "assemble-reconciliation":
            result = assemble_reconciliation(
                args.root,
                args.manifest_sha256,
                args.discovery_freeze,
                args.discovery_manifest_sha256,
                args.output,
            )
        else:
            result = collect_applications(args.root, args.manifest_sha256, args.output)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, StopIteration) as error:
        print(
            json.dumps(
                {"status": "unavailable", "reason": str(error)}, ensure_ascii=True
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
