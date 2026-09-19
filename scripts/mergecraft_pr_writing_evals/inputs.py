"""Freeze this method's private inputs from a committed, ready source inventory."""

import argparse
import json
import re
from pathlib import Path

from .binding import PACKAGE, adapter_source, load_processor, require, sha

CORPUS = "evals/mergecraft/skills/writing-reviewable-pr-descriptions/evals.json"
TRIGGERS = CORPUS.removesuffix("evals.json") + "trigger-evals.json"
SKILL = "mergecraft/writing-reviewable-pr-descriptions"


def validate_plan(plan):
    """Recheck immutable method fields independently of the caller's file digest."""
    _, _, contract = load_processor()
    require(
        plan["method_contract_sha256"]
        == sha((PACKAGE / "correspondence.json").read_bytes()),
        "method contract differs",
    )
    for key in (
        "corpus_sha256",
        "thresholds",
        "provider",
        "client",
        "requested_model",
        "requested_effort",
        "timeout_seconds",
        "maximum_concurrency",
        "conditions",
        "repetitions",
        "run_coordinates",
        "input_format",
        "case_instruction_paths",
        "required_source_paths",
        "non_delivered_dependencies",
        "required_projection_equalities",
    ):
        require(plan[key] == contract[key], "fixed application plan differs: " + key)
    kind = plan["processing_identity_kind"]
    require(
        kind in ("published", "constructed-test")
        and plan["published_processor_revision"]
        == contract["published_processor_revision"]
        and (
            (plan["processing_revision"] == plan["published_processor_revision"])
            == (kind == "published")
        ),
        "processing identity differs",
    )
    if kind == "published":
        require(
            {key: plan["client_binding"][key] for key in ("sha256", "version")}
            == {key: contract["reviewed_client"][key] for key in ("sha256", "version")},
            "changed client needs reviewed method correspondence",
        )


def encoded(value):
    return (
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode()


def create(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(value if isinstance(value, bytes) else encoded(value))


def freeze_inputs(
    source,
    revision,
    runtime,
    runtime_sha256,
    processing_revision,
    output,
    *,
    identity_kind="published",
):
    """Create frozen inputs; neither select a source nor authorize an execution.

    Constructed-test identities are for disposable test repositories and local test
    executables only. Their receipts do not represent the published processor P.
    """
    core, inventory, contract = load_processor()
    source, output = Path(source).resolve(), Path(output).resolve()
    require(re.fullmatch(r"[0-9a-f]{40}", revision), "source needs a full commit")
    require(
        re.fullmatch(r"[0-9a-f]{40}", processing_revision),
        "processor needs a full commit",
    )
    require(
        identity_kind in ("published", "constructed-test"),
        "unknown processing identity",
    )
    published = contract["published_processor_revision"]
    require(
        (processing_revision == published) == (identity_kind == "published"),
        "published and constructed processing identities must remain distinct",
    )
    require(core.revision(source, revision) == revision, "source commit differs")
    require(
        core.git(source, "rev-parse", "HEAD").decode().strip() == revision,
        "source checkout differs",
    )
    method_source = adapter_source(source, revision)
    for path, digest in contract["processor_files"].items():
        require(
            sha(core.source_bytes(source, processing_revision, path)) == digest,
            "processing commit differs: " + path,
        )
    runtime_raw = Path(runtime).read_bytes()
    require(sha(runtime_raw) == runtime_sha256, "runtime binding differs")
    client = core.read_json(runtime_raw)
    require(
        set(client) == {"path", "sha256", "version"}, "runtime binding fields differ"
    )
    require(
        Path(client["path"]).is_absolute()
        and Path(client["path"]).is_file()
        and sha(Path(client["path"]).read_bytes()) == client["sha256"],
        "runtime executable differs",
    )
    if identity_kind == "published":
        require(
            {k: client[k] for k in ("sha256", "version")}
            == {key: contract["reviewed_client"][key] for key in ("sha256", "version")},
            "changed client needs reviewed method correspondence",
        )
    descriptor = inventory.descriptor(source, revision, SKILL)
    require(descriptor["status"] == "ready", "selected descriptor is unresolved")
    rubrics = [
        {
            "case_id": case["case_id"],
            "expectations": [
                {key: e[key] for key in ("id", "text", "severity")}
                for e in case["expectations"]
            ],
        }
        for case in descriptor["cases"]
    ]
    require(
        core.document_digest(rubrics) == contract["accepted_rubrics_sha256"],
        "whole accepted criteria differ",
    )
    corpus_raw = core.source_bytes(source, revision, CORPUS)
    require(sha(corpus_raw) == contract["corpus_sha256"], "committed corpus differs")
    corpus = core.read_json(corpus_raw)
    require(len(corpus["evals"]) == 11, "application coverage differs")
    query_raw = core.source_bytes(source, revision, TRIGGERS)
    require(
        sha(query_raw) == contract["trigger_source_sha256"], "direct queries differ"
    )
    queries = core.read_json(query_raw)
    require(len(queries) == 19, "direct query coverage differs")
    mapping_raw = core.source_bytes(source, revision, inventory.EXPECTATION_MAP)
    mapping = core.read_json(mapping_raw)
    entries = [e for e in mapping["entries"] if e["source"]["path"] == CORPUS]
    require(len(entries) == 43, "accepted mapping coverage differs")
    files = {
        "inputs/corpus.json": corpus_raw,
        "inputs/prompt-prefix.txt": contract["request_prefix"].encode(),
        "native-reference/frozen-direct-queries.json": query_raw,
        "withheld/accepted-expectation-map.json": mapping_raw,
        "withheld/accepted-input-map.json": core.source_bytes(
            source, revision, inventory.INPUT_MAP
        ),
        "runtime-binding.json": runtime_raw,
    }
    policy = {
        "status": "derived-from-accepted-committed-mappings",
        "source": inventory.EXPECTATION_MAP,
        "source_sha256": sha(mapping_raw),
        "acceptance_reference": contract["acceptance_reference"],
        "cases": [],
    }
    for number, case in enumerate(corpus["evals"]):
        require(case["id"] == number and len(case["files"]) == 1, "case shape differs")
        fixture_path = "evals/mergecraft/skills/" + case["files"][0]
        fixture = core.source_bytes(source, revision, fixture_path)
        require(
            sha(fixture) == contract["fixture_sha256"].get(fixture_path),
            "fixture differs",
        )
        files["inputs/" + fixture_path] = fixture
        files[f"inputs/eval-{number}/task.json"] = encoded(
            {"prompt": case["prompt"], "fixture": fixture.decode()}
        )
        expectations = [
            {"id": e["id"], "expectation_text": e["text"], "severity": e["severity"]}
            for e in rubrics[number]["expectations"]
        ]
        policy["cases"].append(
            {"case_id": number, "case_name": case["name"], "expectations": expectations}
        )
        files[f"withheld/eval-{number}/grading-contract.json"] = encoded(
            {
                "case": number,
                "name": case["name"],
                "expected_output": case["expected_output"],
                "expectations": [
                    {"id": f"{number}.{n + 1}", "text": e["text"]}
                    for n, e in enumerate(rubrics[number]["expectations"])
                ],
                "executor_inputs": ["with_skill/request.json", "with_skill/prompt.txt"],
                "grading_material_withheld_from_executor": True,
            }
        )
    files["withheld/expectation-policy.json"] = encoded(policy)
    files["withheld/expectation-policy-owner-review.json"] = encoded(
        {
            "status": "source-mapping-accepted",
            "mapping_sha256": sha(files["withheld/expectation-policy.json"]),
            "accepted_map_sha256": sha(mapping_raw),
            "reviews": [e["review"] for e in entries],
            "basis": "Accepted committed mapping references, verified by the owning inventory; no new review.",
        }
    )
    rows, correspondence = [], []
    for number, query in enumerate(queries):
        query_digest = sha(query["query"].encode())
        identifier = f"writing-reviewable-pr-descriptions-{number:02d}"
        rows.append(
            {
                "id": identifier,
                "skill": SKILL.split("/")[1],
                "index": number,
                **query,
                "query_sha256": query_digest,
                "probe_prompt": contract["trigger_prompt_template"].replace(
                    "{query}", query["query"]
                ),
            }
        )
        correspondence.append(
            {
                "native_plan_id": identifier,
                "original_coordinate": {
                    "source": TRIGGERS,
                    "pointer": f"/{number}",
                    "id": None,
                },
                "query_sha256": query_digest,
                "expected_boolean": query["should_trigger"],
                "observation_kind": "recorded-sentinel-body-load",
                "actual_observation": None,
            }
        )
    files["native-reference/selection-contract.json"] = encoded({"rows": rows})
    files["native-reference/trigger-correspondence.json"] = encoded(
        {"source_sha256": sha(query_raw), "count": 19, "rows": correspondence}
    )
    files["native-reference/method-contract.json"] = encoded(contract["native_method"])
    plan = {
        key: contract[key]
        for key in (
            "corpus_sha256",
            "thresholds",
            "provider",
            "client",
            "requested_model",
            "requested_effort",
            "timeout_seconds",
            "maximum_concurrency",
            "conditions",
            "repetitions",
            "run_coordinates",
            "input_format",
            "case_instruction_paths",
            "required_source_paths",
            "non_delivered_dependencies",
            "required_projection_equalities",
            "claim",
            "baseline",
            "limitations",
        )
    }
    plan.update(
        status="source-bound-inputs-awaiting-preparation-and-launch-review",
        source_revision=revision,
        processing_revision=processing_revision,
        processing_identity_kind=identity_kind,
        published_processor_revision=published,
        case_count=11,
        fixture_count=10,
        criteria_count=43,
        client_binding=client,
        runtime_binding_sha256=runtime_sha256,
        method_contract_sha256=sha((PACKAGE / "correspondence.json").read_bytes()),
        adapter_source=method_source,
        policy_sha256=sha(files["withheld/expectation-policy.json"]),
        policy_owner_review_sha256=sha(
            files["withheld/expectation-policy-owner-review.json"]
        ),
        file_sha256={path: sha(raw) for path, raw in sorted(files.items())},
    )
    output.mkdir(parents=True, exist_ok=False)
    create(
        output / "STOP_LAUNCHES",
        b"Input freeze only. Source, method, payload, and launch reviews remain required.\n",
    )
    for path, raw in files.items():
        create(output / path, raw)
    create(output / "input-manifest.json", plan)
    return {
        "input_manifest_sha256": sha((output / "input-manifest.json").read_bytes()),
        "source_revision": revision,
        "launch_stopped": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--runtime-binding", type=Path, required=True)
    parser.add_argument("--runtime-binding-sha256", required=True)
    parser.add_argument("--processing-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            freeze_inputs(
                args.source_root,
                args.revision,
                args.runtime_binding,
                args.runtime_binding_sha256,
                args.processing_revision,
                args.output,
            )
        )
    )


if __name__ == "__main__":
    main()
