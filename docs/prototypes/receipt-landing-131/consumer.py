"""Proposed ordinary consumer; caller context/event authority is NOT implemented.

The frozen adapter remains unchanged. Historical validation asks it about S/S;
correspondence to C is an additional, explicitly different consumer contract.
"""

from fixtures import CONTEXT, RECEIPT, ROOT, git, sha


def context_for(repo, base, target, inventory):
    """Fixture's reviewed handoff, captured before landing and kept independently."""
    raw = (repo / RECEIPT).read_bytes()
    receipt = inventory.core.read_json(raw)
    processor = receipt.get("processing", {}).get("revision", receipt["candidate_revision"])
    identity = inventory.core.processing_snapshot(repo, processor, normalized=True)
    key = receipt["snapshot"]["skill"]["plugin"] + "/" + receipt["snapshot"]["skill"]["skill"]
    return {"schema_version": 1, "original_base": base, "reviewed_target": target,
            "receipts": {key: {"raw_sha256": sha(raw), "processing": identity}}}


def check(repo, inventory, *, context, event, base, candidate, strategy):
    """Check actual committed C; never derive the original B from C's parent.

    This interface assumes an independent caller supplies the reviewed context
    and event. The fixture is that caller; it proves no hosted authentication,
    event delivery, protected execution, or ability to block a forge operation.
    """
    core = inventory.core
    output = {"status": "fail", "strategy": strategy, "base_revision": base,
              "candidate_revision": candidate, "context_sha256": core.document_digest(context),
              "skills": [], "stage": "context"}
    try:
        core.require(strategy in ("correspondence", "ancestry"), "unsupported strategy")
        core.require(event["operation"] in ("squash", "rebase", "merge", "ff-only"),
                     "unsupported landing operation")
        core.require(base == context["original_base"], "original comparison was replaced")
        core.require(candidate == event["commit"], "candidate is not the actual landing event commit")
        core.require(event["target_before"] == context["reviewed_target"], "target moved; refresh required")
        for revision in (base, candidate, context["reviewed_target"]):
            core.revision(repo, revision)
        core.require(git(repo, "merge-base", "--is-ancestor", base, candidate, check=False) == 0,
                     "original comparison base is not an ancestor of the landed commit")
        core.require(git(repo, "merge-base", "--is-ancestor", context["reviewed_target"], candidate, check=False) == 0,
                     "reviewed target is not an ancestor of the landed commit")
        if event["operation"] in ("squash", "merge"):
            core.require(git(repo, "rev-parse", candidate + "^1") == event["target_before"],
                         "landing first parent differs from the observed target")
        committed = inventory.Source(repo, candidate)
        core.require(core.read_json(committed.read(CONTEXT)) == context,
                     "committed context differs from the independent reviewed handoff")
        output["stage"] = "selection"
        comparison = inventory.compare(repo, base, candidate)
        output.update(affected_skills=comparison["affected_skills"],
                      selection_complete=comparison["selection_complete"], unsupported=comparison["unsupported"])
        core.require(comparison["status"] == "complete", "affected consumer selection is unsupported")
        core.require(set(comparison["affected_skills"]) == set(context["receipts"]),
                     "reviewed Receipt inventory differs from the full original comparison")
        for key in comparison["affected_skills"]:
            output["stage"] = "descriptor"
            described = inventory.descriptor(repo, candidate, key)
            output["descriptor_diagnostics"] = described["diagnostics"]
            core.require(described["status"] == "ready", "landed descriptor is unresolved")
            spec = described["descriptor"]
            path = f"{ROOT}/{key}.json"
            output["stage"] = "receipt-bytes"
            raw = committed.read(path)
            core.require(sha(raw) == context["receipts"][key]["raw_sha256"],
                         "committed Receipt differs from the reviewed bytes")
            output["stage"] = "receipt-parse"
            receipt = core.read_json(raw)
            output["stage"] = "receipt-schema"
            core.validate(receipt)
            source = receipt["candidate_revision"]
            processor = receipt.get("processing", {}).get("revision", source)
            output["stage"] = "processing"
            processing = core.processing_snapshot(repo, processor, normalized=True)
            core.require(processing == context["receipts"][key]["processing"],
                         "processing identity differs from the reviewed contract")
            output["stage"] = "historical"
            historical = core.check(repo, {
                "schema_version": 1, "base_revision": source, "candidate_revision": source,
                "skills": [spec], "changed_skills": [key], "inventory_complete": True}, {key: raw})
            core.require(historical["status"] == "pass",
                         "historical Receipt: " + historical["skills"][0]["reason"])
            # A proposed public closure-comparison API would replace this private
            # call before production adoption. No ancestry code is patched out.
            output["stage"] = "correspondence"
            current = core._freeze(repo, candidate, spec,
                                   bind_processing=receipt.get("method") != "reconciled-after-run")
            core.require(receipt["snapshot"]["inputs"] == current["inputs"],
                         "landed input closure differs in paths, bytes, or Git modes")
            if strategy == "ancestry":
                output["stage"] = "ancestry"
                core.require(git(repo, "merge-base", "--is-ancestor", source, candidate, check=False) == 0,
                             "evaluated source is not an ancestor of the landed commit")
            output["skills"].append({
                "skill": key, "evaluated_revision": source, "receipt_raw_sha256": sha(raw),
                "stable_input_identity": core.document_digest({"skill": spec,
                    "inputs": current["inputs"], "processing_inputs": processing["inputs"]}),
                "processing_revision": processor, "historical_check": historical,
                "failed_observations_retained": sum(not grade["passed"] for run in receipt["runs"]
                                                    for grade in run["expectations"]),
                "source_is_ancestor": git(repo, "merge-base", "--is-ancestor", source, candidate, check=False) == 0})
        if strategy == "ancestry":
            ordinary = inventory.check(repo, base, candidate, ROOT)
            core.require(ordinary["status"] == "pass", "ordinary landed adapter did not pass")
            output["ordinary_landed_check"] = ordinary["status"]
        output.update(status="pass" if output["skills"] else "not-required", stage="complete",
                      reason="all selected Receipts match the actual landed inputs")
    except (core.ReceiptError, inventory.InventoryError) as error:
        output["reason"] = str(error)
    return output
