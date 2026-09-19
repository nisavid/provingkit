"""Finalize the frozen eleven-case #111 inputs after PR84 source review."""

import argparse
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

from .receipt_artifacts import (
    delivery_inputs,
    delivery_table,
    method_digests,
    normalized_rubrics,
    verify_preparation,
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def create(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def build_request(case, bundle, inputs):
    task = json.loads((inputs / f"inputs/eval-{case}/task.json").read_bytes())
    request = encoded(
        {
            "prompt": task["prompt"],
            "fixture": task["fixture"],
            "candidate_bundle": bundle,
        }
    )
    prompt = (inputs / "inputs/prompt-prefix.txt").read_bytes() + b"\n\n" + request
    return request, prompt


def prepare(
    source,
    binding_path,
    binding_sha256,
    input_sha256,
    output,
    *,
    inputs,
    receipt_snapshot=None,
    receipt_snapshot_file_sha256=None,
    receipt_snapshot_sha256=None,
    receipt_descriptor=None,
    receipt_descriptor_sha256=None,
):
    inputs = Path(inputs).resolve()
    plan_bytes = (inputs / "input-manifest.json").read_bytes()
    require(sha(plan_bytes) == input_sha256, "frozen input manifest differs")
    plan = json.loads(plan_bytes)
    for path, digest in plan["file_sha256"].items():
        require(
            sha((inputs / path).read_bytes()) == digest, f"frozen input differs: {path}"
        )
    binding_bytes = binding_path.read_bytes()
    require(sha(binding_bytes) == binding_sha256, "source binding differs")
    binding = json.loads(binding_bytes)
    require(
        binding["status"] == "reviewed-final-pr84-source",
        "reviewed final PR84 source is pending",
    )
    require(
        set(binding["source_sha256"]) == set(plan["required_source_paths"]),
        "final source closure differs; amend and review this plan before preparation",
    )
    review = Path(binding["source_review"]["path"]).read_bytes()
    require(
        sha(review) == binding["source_review"]["sha256"],
        "source review record differs",
    )
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=source, text=True
    ).strip()
    require(head == binding["repository_head"], "source checkout base differs")
    receipt = verify_preparation(
        source,
        binding,
        plan,
        receipt_snapshot,
        receipt_snapshot_file_sha256,
        receipt_snapshot_sha256,
        receipt_descriptor,
        receipt_descriptor_sha256,
        inputs,
    )
    source_bytes = {
        path: (source / path).read_bytes() for path in plan["required_source_paths"]
    }
    for path, raw in source_bytes.items():
        require(
            sha(raw) == binding["source_sha256"][path], f"final source differs: {path}"
        )
        raw.decode("utf-8")
    for canonical, projection in plan["required_projection_equalities"]:
        require(
            source_bytes[canonical] == source_bytes[projection],
            f"projection differs: {projection}",
        )
    corpus_path = (
        "evals/mergecraft/skills/writing-reviewable-pr-descriptions/evals.json"
    )
    require(
        (source / corpus_path).read_bytes()
        == (inputs / "inputs/corpus.json").read_bytes(),
        "final corpus differs from frozen corpus",
    )
    corpus = json.loads((inputs / "inputs/corpus.json").read_bytes())
    for case in corpus["evals"]:
        for fixture in case["files"]:
            relative = "evals/mergecraft/skills/" + fixture
            require(
                (source / relative).read_bytes()
                == (inputs / "inputs" / relative).read_bytes(),
                f"final fixture differs: {relative}",
            )
    client = plan["client_binding"]
    require(
        sha(Path(client["path"]).read_bytes()) == client["sha256"],
        "Codex client bytes differ",
    )
    output.mkdir(parents=True, exist_ok=False)
    (output / "cwd").mkdir()
    create(
        output / "STOP_LAUNCHES",
        b"Root must review the final manifest and method before enabling this run directory.\n",
    )
    for relative in ["input-manifest.json", *plan["file_sha256"]]:
        create(output / "method-inputs" / relative, (inputs / relative).read_bytes())
    create(output / "final-source-binding.json", binding_bytes)
    create(output / "source-review.json", review)
    create(output / "receipt/snapshot.json", receipt_snapshot.read_bytes())
    create(output / "receipt/descriptor.json", receipt_descriptor.read_bytes())
    create(
        output / "receipt/grading-rubrics.json",
        encoded(normalized_rubrics(json.loads(receipt_descriptor.read_bytes()))),
    )
    for path, raw in source_bytes.items():
        create(output / "source" / path, raw)
    coordinates = []
    for case in corpus["evals"]:
        number = case["id"]
        paths = plan["case_instruction_paths"][str(number)]
        bundle = {path: source_bytes[path].decode("utf-8") for path in paths}
        request, prompt = build_request(number, bundle, inputs)
        target = output / f"eval-{number}/with_skill"
        create(target / "request.json", request)
        create(target / "prompt.txt", prompt)
        create(
            output / f"eval-{number}/grading-contract.json",
            (inputs / f"withheld/eval-{number}/grading-contract.json").read_bytes(),
        )
        metadata = {
            "id": number,
            "receipt_case_id": receipt["case_coordinates"][str(number)],
            "name": case["name"],
            "input_paths": paths,
            "input_evidence": delivery_inputs(
                number, request, json.loads(receipt_snapshot.read_bytes()), inputs
            ),
            "request_sha256": sha(request),
            "submitted_prompt_sha256": sha(prompt),
            "source_sha256": {path: binding["source_sha256"][path] for path in paths},
            "provider_delivery": "omitted; stipulated unavailable"
            if number == 10
            else "explicit source bundle",
        }
        create(output / f"eval-{number}/eval_metadata.json", encoded(metadata))
        coordinates.append(metadata)
    for name in ("expectation-policy.json", "expectation-policy-owner-review.json"):
        create(output / "withheld" / name, (inputs / "withheld" / name).read_bytes())
    artifacts = {
        str(p.relative_to(output)): sha(p.read_bytes())
        for p in output.rglob("*")
        if p.is_file() and p.name != "STOP_LAUNCHES"
    }
    manifest = {
        **{
            key: plan[key]
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
                "claim",
                "baseline",
                "limitations",
            )
        },
        "status": "prepared-final-source-awaiting-launch-review",
        "prepared_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "repository_base": head,
        "receipt": receipt,
        "source_binding_sha256": binding_sha256,
        "source_review_sha256": sha(review),
        "input_manifest_sha256": input_sha256,
        "source_sha256": binding["source_sha256"],
        "corpus_sha256": plan["corpus_sha256"],
        "policy_sha256": plan["policy_sha256"],
        "policy_owner_review_sha256": plan["policy_owner_review_sha256"],
        "coordinates": coordinates,
        "delivery": delivery_table(coordinates),
        "artifact_sha256": artifacts,
        "method_sha256": method_digests(),
    }
    create(output / "manifest.json", encoded(manifest))
    return {
        "output": str(output),
        "manifest_sha256": sha((output / "manifest.json").read_bytes()),
        "runs": 33,
        "launches_stopped": True,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--binding-sha256", required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--input-manifest-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt-snapshot", type=Path, required=True)
    parser.add_argument("--receipt-snapshot-file-sha256", required=True)
    parser.add_argument("--receipt-snapshot-sha256", required=True)
    parser.add_argument("--receipt-descriptor", type=Path, required=True)
    parser.add_argument("--receipt-descriptor-sha256", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            prepare(
                args.source_root.resolve(),
                args.binding,
                args.binding_sha256,
                args.input_manifest_sha256,
                args.output.resolve(),
                inputs=args.inputs,
                receipt_snapshot=args.receipt_snapshot,
                receipt_snapshot_file_sha256=args.receipt_snapshot_file_sha256,
                receipt_snapshot_sha256=args.receipt_snapshot_sha256,
                receipt_descriptor=args.receipt_descriptor,
                receipt_descriptor_sha256=args.receipt_descriptor_sha256,
            )
        )
    )
