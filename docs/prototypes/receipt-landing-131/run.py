#!/usr/bin/env python3
"""Reproduce the landing comparison in disposable repositories; no model runs."""

import argparse
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import json
import shutil
import tempfile

from consumer import check, context_for
from fixtures import (CONTEXT, CORPUS, ENTRY, KEY, PROCESSING, PROCESSOR, RECEIPT,
                      REFERENCE, ROOT, commit, create_repo, encoded, fetch_processor, git, land,
                      load_adapter, prepared_receipt, reconciled_receipt, sha, write)


@dataclass(frozen=True)
class EvaluatedFixture:
    repository: Path
    base: str
    source: str
    head: str
    context: dict


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write measured JSON to this path")
    parser.add_argument("--fetch-processor", action="store_true",
                        help="fetch and verify P24 from public PR #116 in a separate temporary repository")
    args = parser.parse_args()
    source_repo = Path(__file__).resolve().parents[3]
    scratch = Path(tempfile.mkdtemp(prefix="receipt-landing-131-"))
    acquisition = None
    if args.fetch_processor:
        source_repo = scratch / "processor-source"
        acquisition = fetch_processor(source_repo)
    adapter = scratch / "adapter"
    inventory, processing = load_adapter(source_repo, adapter)
    repo = scratch / "template"
    base, source = create_repo(repo, adapter)
    receipt = prepared_receipt(repo, source, inventory, scratch / "private")

    def freeze_fixture(repository, comparison_base, evaluated_source, recorded_receipt):
        write(repository, RECEIPT, recorded_receipt)
        handoff = context_for(repository, comparison_base, comparison_base, inventory)
        write(repository, CONTEXT, handoff)
        containing = commit(repository, "Retain constructed Receipt and original comparison")
        return EvaluatedFixture(repository, comparison_base, evaluated_source, containing, handoff)

    baseline_fixture = freeze_fixture(repo, base, source, receipt)
    head, context = baseline_fixture.head, baseline_fixture.context
    original = inventory.check(repo, base, head, ROOT)
    assert original["status"] == "pass", original
    results = []

    def scenario(name, operation="squash", mutate=None, rebind=False, request_change=None,
                 target_change=None, refresh=False, expected=("pass", "fail"),
                 expected_reason=None, expected_stage=None, expected_affected=None, expected_code=None, fixture=None):
        fixture = fixture or baseline_fixture
        base, source, head = fixture.base, fixture.source, fixture.head
        directory = scratch / name
        shutil.copytree(fixture.repository, directory)
        ctx = deepcopy(fixture.context)
        target = base
        if target_change:
            git(directory, "checkout", "--detach", "-q", base)
            target_change(directory)
            target = commit(directory, "Concurrent target change")
            git(directory, "checkout", "--detach", "-q", head)
        if mutate:
            mutate(directory)
        if rebind == "raw":
            # Bind intentionally malformed bytes so the negative control reaches
            # parsing/schema validation instead of stopping at the byte check.
            ctx["receipts"][KEY]["raw_sha256"] = sha((directory / RECEIPT).read_bytes())
        elif rebind:
            ctx = context_for(directory, base, base, inventory)
        if refresh:
            ctx["reviewed_target"] = target
        write(directory, CONTEXT, ctx)
        if git(directory, "status", "--porcelain"):
            proposed = commit(directory, "Scenario variation before landing")
        else:
            proposed = head
        final = land(directory, proposed, target, operation)
        event = {"commit": final, "target_before": target, "operation": operation}
        request = {"context": ctx, "event": event, "base": base, "candidate": final}
        if request_change:
            request_change(request, directory, final)
        observations = {strategy: check(directory, inventory, strategy=strategy, **request)
                        for strategy in ("correspondence", "ancestry")}
        ordinary = inventory.check(directory, base, final, ROOT)
        row = {"name": name, "operation": operation, "expected": dict(zip(observations, expected)),
               "original_base": base, "evaluated_source": source, "reviewed_head": proposed,
               "target_before": target, "landed_commit": final, "ordinary_adapter": ordinary,
               "observations": observations}
        if expected_reason:
            row["expected_reason"] = expected_reason
        if expected_stage:
            row["expected_stage"] = expected_stage
        if expected_affected is not None:
            row["expected_affected_skills"] = expected_affected
        if expected_code:
            row["expected_diagnostic_code"] = expected_code
        results.append(row)
        for strategy, outcome in row["expected"].items():
            assert observations[strategy]["status"] == outcome, (name, strategy, observations[strategy])
            if expected_reason:
                assert observations[strategy]["reason"] == expected_reason, (name, strategy, observations[strategy])
            if expected_stage:
                assert observations[strategy]["stage"] == expected_stage, (name, strategy, observations[strategy])
            if expected_affected is not None:
                assert observations[strategy]["affected_skills"] == expected_affected, (name, strategy, observations[strategy])
            if expected_code:
                diagnostics = observations[strategy].get("descriptor_diagnostics", []) + observations[strategy]["unsupported"]
                assert expected_code in [item["code"] for item in diagnostics], (name, strategy, diagnostics)
        return directory, row

    squash_repo, squashed = scenario("unchanged-squash")
    assert squashed["ordinary_adapter"]["status"] == "fail", squashed
    merge_repo, merged = scenario("unchanged-merge", "merge", expected=("pass", "pass"))
    scenario("unchanged-fast-forward", "ff-only", expected=("pass", "pass"))
    scenario("unchanged-forced-rebase", "rebase")
    stable_ids = {row["observations"]["correspondence"]["skills"][0]["stable_input_identity"]
                  for row in results}
    assert len(stable_ids) == 1, stable_ids
    assert all(row["observations"]["correspondence"]["skills"][0]["failed_observations_retained"] == 2
               for row in results), "The two constructed failed quality observations must remain present."

    def edit_receipt(change):
        def mutate(directory):
            value = json.loads((directory / RECEIPT).read_bytes())
            change(value)
            write(directory, RECEIPT, value)
        return mutate

    failures = [
        ("changed-entrypoint", lambda directory: write(directory, ENTRY, (directory / ENTRY).read_bytes() + b"Alter meaning.\n")),
        ("changed-mode", lambda directory: (directory / ENTRY).chmod(0o755)),
        ("changed-reference", lambda directory: write(directory, REFERENCE, "Different guidance.\n")),
        ("changed-topology", lambda directory: write(directory, "plugins/example/topology.json",
            {"skills": {"writing": {"calls": ["editing"]}, "editing": {"calls": []}}})),
        ("changed-processing", lambda directory: write(directory, PROCESSING[0],
            (directory / PROCESSING[0]).read_bytes() + b"\n# Constructed processing change.\n")),
        ("missing-receipt", lambda directory: (directory / RECEIPT).unlink()),
        ("receipt-rewritten", edit_receipt(lambda value: value["runs"][2]["expectations"][0].update(passed=True))),
    ]
    for name, mutation in failures:
        scenario(name, mutate=mutation, expected=("fail", "fail"))

    def add_mapping(directory):
        path = "evals/example/additional.json"
        write(directory, path, {"skill_name": "writing", "evals": [
            {"id": 9, "prompt": "Additional mapped case.", "expectations": [
                {"id": "keep", "text": "Keep the supplied meaning.", "severity": "quality"}]}]})
        semantic = {"source": {"path": path, "sha256": sha((directory / path).read_bytes())},
                    "pointer": "/evals/0", "owners": [KEY], "role": "current-corpus",
                    "behavior_inputs": [], "dependencies": []}
        write(directory, inventory.INPUT_MAP, {"schema_version": 1, "entries": [
            {**semantic, "status": "accepted", "review": {"decision": "accepted",
             "reference": "constructed-map-review", "mapping_sha256": inventory.core.document_digest(semantic)}}]})

    scenario("changed-input-mapping", mutate=add_mapping, expected=("fail", "fail"))
    scenario("changed-expectation-map-bytes", mutate=lambda directory: write(directory,
             inventory.EXPECTATION_MAP, b'{"entries": [], "schema_version": 1}\n'), expected=("fail", "fail"))
    for name, change in (
        ("missing-case", lambda value: value.update(runs=value["runs"][:3])),
        ("missing-repetition", lambda value: value["runs"].pop()),
        ("missing-trigger", lambda value: value["triggers"].pop()),
        ("failed-quality", lambda value: value["runs"][0]["expectations"][0].update(passed=False)),
        ("failed-safety", lambda value: value["runs"][0]["expectations"][1].update(passed=False)),
        ("failed-trigger", lambda value: value["triggers"][0].update(triggered=False)),
        ("wrong-snapshot", lambda value: value["snapshot"]["inputs"][ENTRY].update(sha256="0" * 64)),
        ("wrong-source", lambda value: value.update(candidate_revision=base)),
        ("wrong-skill", lambda value: value["snapshot"]["skill"].update(skill="editing")),
    ):
        scenario(name, mutate=edit_receipt(change), rebind=True, expected=("fail", "fail"))

    def add_dependency(directory):
        write(directory, "plugins/example/references/additional.md", "Required additional guidance.\n")
        write(directory, "plugins/example/topology.json", {"skills": {
            "writing": {"calls": [], "references": ["references/additional.md"]}, "editing": {"calls": []}}})

    scenario("added-declared-dependency", mutate=add_dependency, expected=("fail", "fail"),
             expected_stage="historical", expected_reason="historical Receipt: stale or wrong-skill receipt descriptor")
    scenario("deleted-declared-dependency", mutate=lambda directory: (directory / REFERENCE).unlink(),
             expected=("fail", "fail"), expected_stage="descriptor", expected_reason="landed descriptor is unresolved",
             expected_code="input-unavailable")

    def transfer_ownership(directory):
        corpus = json.loads((directory / CORPUS).read_bytes())
        corpus["skill_name"] = "editing"
        write(directory, CORPUS, corpus)

    scenario("ownership-transfer", mutate=transfer_ownership, expected=("fail", "fail"),
             expected_stage="selection", expected_reason="reviewed Receipt inventory differs from the full original comparison",
             expected_affected=["example/editing", KEY])

    def remove_skill(directory):
        shutil.rmtree(directory / "plugins/example/skills/writing")
        write(directory, "plugins/example/topology.json", {"skills": {"editing": {"calls": []}}})

    scenario("removed-skill", mutate=remove_skill, expected=("fail", "fail"), expected_stage="selection",
             expected_reason="affected consumer selection is unsupported", expected_affected=[KEY],
             expected_code="removed-or-renamed-skill")
    scenario("unresolved-affected-corpus", mutate=lambda directory: write(directory, CORPUS, "{\n"),
             expected=("fail", "fail"), expected_stage="selection",
             expected_reason="affected consumer selection is unsupported", expected_affected=[KEY],
             expected_code="unsupported-corpus")

    def unclassified_corpus(directory):
        corpus = json.loads((directory / CORPUS).read_bytes())
        corpus["evals"][0]["expectations"] = ["An ordinary expectation whose classification is unresolved."]
        write(directory, CORPUS, corpus)

    scenario("unclassified-affected-corpus", mutate=unclassified_corpus, expected=("fail", "fail"),
             expected_stage="descriptor", expected_reason="landed descriptor is unresolved",
             expected_affected=[KEY], expected_code="expectation-mapping-required")
    scenario("malformed-committed-receipt", mutate=lambda directory: write(directory, RECEIPT, "{\n"),
             rebind="raw", expected=("fail", "fail"), expected_stage="receipt-parse",
             expected_reason="invalid or duplicate-key JSON")
    scenario("invalid-committed-receipt-shape", mutate=edit_receipt(lambda value: value.pop("runs")),
             rebind="raw", expected=("fail", "fail"), expected_stage="receipt-schema",
             expected_reason="receipt schema mismatch")
    for name, change, reason in (
        ("duplicate-repetition", lambda value: value["runs"].append(deepcopy(value["runs"][0])),
         "run coverage must include each case at repetitions 1, 2, and 3 exactly once"),
        ("missing-expectation", lambda value: value["runs"][0]["expectations"].pop(),
         "expectation coverage differs from the corpus"),
        ("wrong-severity", lambda value: value["runs"][0]["expectations"][0].update(severity="safety"),
         "grade severity or Boolean result differs from the corpus contract"),
    ):
        scenario(name, mutate=edit_receipt(change), rebind="raw", expected=("fail", "fail"),
                 expected_stage="historical", expected_reason="historical Receipt: " + reason)

    scenario("receipt-only-comparison", request_change=lambda request, directory, final:
             request.update(base=final), expected=("fail", "fail"))
    assert inventory.check(squash_repo, squashed["landed_commit"], squashed["landed_commit"], ROOT)["status"] == "not-required"
    scenario("wrong-final-commit", request_change=lambda request, directory, final:
             request.update(candidate=head), expected=("fail", "fail"))
    scenario("unsupported-event-operation", request_change=lambda request, directory, final:
             request["event"].update(operation="cherry-pick"), expected=("fail", "fail"))
    scenario("ignore-uncommitted-receipt", request_change=lambda request, directory, final:
             write(directory, RECEIPT, "Invalid uncommitted replacement.\n"))
    scenario("moved-base", target_change=lambda directory: write(directory, "notes.txt", "Concurrent unrelated work.\n"),
             expected=("fail", "fail"))
    scenario("refreshed-base", target_change=lambda directory: write(directory, "notes.txt", "Concurrent unrelated work.\n"),
             refresh=True)
    scenario("refreshed-base-new-consumer", target_change=lambda directory: write(directory,
             "plugins/example/skills/editing/SKILL.md", "Changed editing behavior.\n"),
             refresh=True, expected=("fail", "fail"))

    retained_receipt = reconciled_receipt(repo, source, base, inventory, scratch / "reconciled-private")
    scenario("reconciled-squash", mutate=lambda directory: write(directory, RECEIPT, retained_receipt), rebind=True)
    scenario("reconciled-merge", "merge", mutate=lambda directory: write(directory, RECEIPT, retained_receipt),
             rebind=True, expected=("pass", "pass"))
    bad_processing = deepcopy(retained_receipt)
    bad_processing["processing"]["inputs"][PROCESSING[0]]["sha256"] = "0" * 64
    scenario("wrong-reconciled-processing", mutate=lambda directory: write(directory, RECEIPT, bad_processing),
             rebind=True, expected=("fail", "fail"))

    lineage_repo = scratch / "changed-rubric-template"
    shutil.copytree(repo, lineage_repo)
    git(lineage_repo, "checkout", "--detach", "-q", source)
    revised_corpus = json.loads((lineage_repo / CORPUS).read_bytes())
    for case in revised_corpus["evals"]:
        case["expectations"][0]["text"] = "Preserve essential facts while allowing paraphrases."
    write(lineage_repo, CORPUS, revised_corpus)
    current_source = commit(lineage_repo, "Change rubric while retaining delivered source and responses")
    lineage_private = scratch / "changed-rubric-private"
    lineage_receipt = reconciled_receipt(lineage_repo, current_source, base, inventory, lineage_private,
                                         original_source=source)
    lineage_fixture = freeze_fixture(lineage_repo, base, current_source, lineage_receipt)
    scenario("changed-rubric-with-lineage", fixture=lineage_fixture)
    scenario("changed-rubric-with-lineage-merge", "merge", fixture=lineage_fixture, expected=("pass", "pass"))
    for name, change in (
        ("changed-rubric-missing-prior-grading", lambda value: value["runs"][0]["reconciliation"].update(previous_grading=[])),
        ("changed-rubric-missing-adjudication", lambda value: value["runs"][0]["reconciliation"].update(adjudication=None)),
    ):
        scenario(name, fixture=lineage_fixture, mutate=edit_receipt(change), rebind="raw", expected=("fail", "fail"),
                 expected_stage="historical", expected_reason="historical Receipt: changed rubric requires original grading and adjudication lineage")

    original_raw = (lineage_private / "original.json").read_bytes()
    original_records = json.loads(original_raw)
    regrading_raw = (lineage_private / "regrading.json").read_bytes()
    assert len(original_records["runs"]) == len(lineage_receipt["runs"]) == 6
    assert sum(not grade["passed"] for run in original_records["runs"] for grade in run["grades"]) == 4
    assert sum(not grade["passed"] for run in lineage_receipt["runs"] for grade in run["expectations"]) == 2
    for index, (original_run, current_run) in enumerate(zip(original_records["runs"], lineage_receipt["runs"], strict=True)):
        retained = current_run["reconciliation"]
        assert retained["original_revision"] == source != current_source
        assert retained["original_corpus_sha256"] == sha(inventory.core.source_bytes(lineage_repo, source, CORPUS))
        assert retained["original_expectations_sha256"] == inventory.core.document_digest(original_run["rubric"])
        assert retained["original_expectations_sha256"] != inventory.core.document_digest(
            revised_corpus["evals"][original_run["case_id"]]["expectations"])
        assert retained["execution_record"] == {"sha256": sha(original_raw), "format": "json", "pointer": f"/runs/{index}"}
        assert retained["execution_identity"]["identity_sha256"] == sha(original_run["native_agent"].encode())
        assert current_run["executor_output_sha256"] == sha(original_run["response"].encode())
        assert retained["inputs"] == {ENTRY: sha(original_run["runtime"].encode()),
                                       REFERENCE: sha(original_run["guidance"].encode())}
        assert retained["executor_model_basis"] == retained["grader_model_basis"] == "configured"
        assert retained["previous_grading"] == [{"sha256": sha(original_raw), "format": "json", "pointer": f"/runs/{index}/grades"}]
        assert retained["adjudication"] == {"sha256": sha(regrading_raw), "format": "json", "pointer": f"/runs/{index}/adjudication"}

    # A genuine Q-to-T Receipt-only commit, not just the degenerate C-to-C range.
    receipt_only = scratch / "receipt-only-range"
    shutil.copytree(squash_repo, receipt_only)
    previous = squashed["landed_commit"]
    write(receipt_only, RECEIPT, (receipt_only / RECEIPT).read_bytes() + b"\n")
    followup = commit(receipt_only, "Receipt-only formatting")
    narrow = inventory.check(receipt_only, previous, followup, ROOT)
    assert narrow["status"] == "not-required", narrow
    guarded = check(receipt_only, inventory, context=context,
                    event={"commit": followup, "target_before": previous, "operation": "squash"},
                    base=previous, candidate=followup, strategy="correspondence")
    assert guarded["status"] == "fail" and guarded["reason"] == "original comparison was replaced", guarded

    # --no-local prevents a local clone from copying otherwise unreachable S.
    # These refs and branch deletions exist only inside disposable fixtures.
    retention = []

    def fresh_clone(origin, landed, label, expected, fetch=None):
        git(origin, "branch", "-f", "main", landed)
        if git(origin, "show-ref", "--verify", "refs/heads/source", check=False) == 0:
            git(origin, "branch", "-D", "source")
        destination = scratch / label
        git(scratch, "clone", "-q", "--no-local", "--single-branch", "--branch", "main", str(origin), str(destination))
        if fetch:
            git(destination, "fetch", "-q", *fetch)
        observed = check(destination, inventory, context=context,
                         event={"commit": landed, "target_before": base, "operation": "merge" if origin == merge_repo else "squash"},
                         base=base, candidate=landed, strategy="correspondence")
        assert observed["status"] == expected, (label, observed)
        available = git(destination, "cat-file", "-e", source + "^{commit}", check=False) == 0
        assert available == (expected == "pass"), (label, available)
        retention.append({"name": label, "expected": expected, "observation": observed,
                          "evaluated_source_available": available})

    fresh_clone(squash_repo, squashed["landed_commit"], "clone-without-provenance", "fail")
    retained_ref = "refs/evidence/prototype/evaluated-source"
    git(squash_repo, "update-ref", retained_ref, source)
    fresh_clone(squash_repo, squashed["landed_commit"], "clone-with-retained-ref", "pass",
                ["origin", f"{retained_ref}:{retained_ref}"])
    bundle = scratch / "retained-source.bundle"
    git(squash_repo, "bundle", "create", str(bundle), retained_ref)
    fresh_clone(squash_repo, squashed["landed_commit"], "clone-with-source-bundle", "pass",
                [str(bundle), f"{retained_ref}:{retained_ref}"])
    fresh_clone(merge_repo, merged["landed_commit"], "clone-with-merged-ancestry", "pass")

    diverged = scratch / "diverged-fast-forward"
    shutil.copytree(repo, diverged)
    git(diverged, "checkout", "--detach", "-q", base)
    write(diverged, "notes.txt", "Concurrent target movement.\n")
    moved = commit(diverged, "Diverged target")
    ff_exit = git(diverged, "merge", "--ff-only", head, check=False)
    assert ff_exit != 0 and git(diverged, "rev-parse", "HEAD") == moved

    report = {"schema_version": 1, "scope": "ordinary constructed fixtures; no model runs or hosted CI",
              "processor_revision": PROCESSOR, "processing_files": processing,
              "prototype_files": {path.name: sha(path.read_bytes()) for path in Path(__file__).parent.glob("*.py")},
              "baseline_check": original, "scenarios": results, "retention": retention,
              "source_bundle_sha256": sha(bundle.read_bytes()),
              "diverged_fast_forward": {"exit_code": ff_exit, "target_before": moved,
                                         "target_after": git(diverged, "rev-parse", "HEAD"), "landed": False},
              "constructed_original_records_sha256": sha((scratch / "reconciled-private/original.json").read_bytes()),
              "changed_rubric_lineage": {"scope": "constructed retained records and regrading; no model or new execution",
                  "original_source": source, "current_evaluated_source": current_source,
                  "original_records_sha256": sha(original_raw), "original_records": original_records,
                  "regrading_sha256": sha(regrading_raw), "regrading": json.loads(regrading_raw),
                  "public_receipt": lineage_receipt},
              "receipt_only_range": {"base": previous, "candidate": followup,
                                     "ordinary_adapter": narrow, "guarded_consumer": guarded}}
    write(scratch, "results.json", report)
    if args.output:
        args.output.write_bytes(encoded(report))
    print(json.dumps({"scratch": str(scratch), "scenarios": len(results),
                      "processor_acquisition": acquisition,
                      "all_expected_outcomes": True, "results_sha256": sha(encoded(report))}, indent=2))


if __name__ == "__main__":
    main()
