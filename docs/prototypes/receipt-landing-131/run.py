#!/usr/bin/env python3
"""Reproduce the landing comparison in disposable repositories; no model runs."""

import argparse
from copy import deepcopy
from pathlib import Path
import json
import shutil
import tempfile

from consumer import check, context_for
from fixtures import (CONTEXT, CORPUS, ENTRY, KEY, PROCESSING, PROCESSOR, RECEIPT,
                      REFERENCE, ROOT, commit, create_repo, encoded, git, land,
                      load_adapter, prepared_receipt, reconciled_receipt, sha, write)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write measured JSON to this path")
    args = parser.parse_args()
    source_repo = Path(__file__).resolve().parents[3]
    scratch = Path(tempfile.mkdtemp(prefix="receipt-landing-131-"))
    adapter = scratch / "adapter"
    inventory, processing = load_adapter(source_repo, adapter)
    repo = scratch / "template"
    base, source = create_repo(repo, adapter)
    receipt = prepared_receipt(repo, source, inventory, scratch / "private")
    write(repo, RECEIPT, receipt)
    context = context_for(repo, base, base, inventory)
    write(repo, CONTEXT, context)
    head = commit(repo, "Retain constructed Receipt and original comparison")
    original = inventory.check(repo, base, head, ROOT)
    assert original["status"] == "pass", original
    results = []

    def scenario(name, operation="squash", mutate=None, rebind=False, request_change=None,
                 target_change=None, refresh=False, expected=("pass", "fail")):
        directory = scratch / name
        shutil.copytree(repo, directory)
        ctx = deepcopy(context)
        target = base
        if target_change:
            git(directory, "checkout", "--detach", "-q", base)
            target_change(directory)
            target = commit(directory, "Concurrent target change")
            git(directory, "checkout", "--detach", "-q", head)
        if mutate:
            mutate(directory)
        if rebind:
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
        results.append(row)
        for strategy, outcome in row["expected"].items():
            assert observations[strategy]["status"] == outcome, (name, strategy, observations[strategy])
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
              "receipt_only_range": {"base": previous, "candidate": followup,
                                     "ordinary_adapter": narrow, "guarded_consumer": guarded}}
    write(scratch, "results.json", report)
    if args.output:
        args.output.write_bytes(encoded(report))
    print(json.dumps({"scratch": str(scratch), "scenarios": len(results),
                      "all_expected_outcomes": True, "results_sha256": sha(encoded(report))}, indent=2))


if __name__ == "__main__":
    main()
