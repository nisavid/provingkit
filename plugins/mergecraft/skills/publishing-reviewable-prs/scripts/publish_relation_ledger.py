#!/usr/bin/env python3
"""Publish one validated relation-ledger span in an open or historical PR body."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Protocol

_WRITER = Path(__file__).resolve().parents[2] / "writing-reviewable-pr-descriptions/scripts"
if str(_WRITER) not in sys.path:
    sys.path.insert(0, str(_WRITER))

from change_navigation.sensitive_content import contains_suspected_secret
from validate_relation_ledger import (
    LedgerRequest, LedgerValidationError, add_arguments, canonical_json,
    read_inputs, sha256, strict_json, validate_request,
)
from publication_receipts import prepare_receipt_store, receipt_ledger_lock
from relation_ledger_receipts import LeaseIdentity, RelationLedgerReceipts
from reviewable_pr_state import PublicationError, run_mutation, run_read


class Forge(Protocol):
    def read(self, target: dict) -> dict: ...
    def write_body(self, target: dict, body: str) -> None: ...


class GitHubForge:
    """Targeted GraphQL reads and a single body-only mutation; no branch dependency."""

    @staticmethod
    def _call(target: dict, query: str, variables: dict, *, mutation: bool = False) -> dict:
        runner = run_mutation if mutation else run_read
        output = runner(["gh", "api", "--hostname", target["host"], "graphql", "--input", "-"],
                        input_text=canonical_json({"query": query, "variables": variables}))
        value = strict_json(output.stdout)
        if not isinstance(value, dict) or value.get("errors") or not isinstance(value.get("data"), dict):
            raise PublicationError("GraphQL did not return complete data")
        return value["data"]

    def read(self, target: dict) -> dict:
        owner, name = target["repository"].split("/")
        data = self._call(target, """query($owner:String!,$name:String!,$number:Int!){
          repository(owner:$owner,name:$name){id nameWithOwner
            pullRequest(number:$number){__typename id number url title body state isDraft}}} """,
                          {"owner": owner, "name": name, "number": target["number"]})
        repository = data.get("repository")
        if not isinstance(repository, dict) or not isinstance(repository.get("pullRequest"), dict):
            raise PublicationError("PR is unavailable")
        pr = repository["pullRequest"]
        if pr.get("url") != f"https://{target['host']}/{target['repository']}/pull/{target['number']}":
            raise PublicationError("PR URL does not match target")
        return {"host": target["host"], "repository": repository.get("nameWithOwner"),
                "repository_id": repository.get("id"), "entity_id": pr.get("id"),
                "number": pr.get("number"), "kind": pr.get("__typename"),
                "title": pr.get("title"), "body": pr.get("body"),
                "state": pr.get("state"), "is_draft": pr.get("isDraft")}

    def write_body(self, target: dict, body: str) -> None:
        data = self._call(target, """mutation($id:ID!,$body:String!){
          updatePullRequest(input:{pullRequestId:$id,body:$body}){pullRequest{id}}} """,
                          {"id": target["entity_id"], "body": body}, mutation=True)
        response = data.get("updatePullRequest")
        if (not isinstance(response, dict) or not isinstance(response.get("pullRequest"), dict)
                or response["pullRequest"].get("id") != target["entity_id"]):
            raise PublicationError("mutation acknowledgement does not identify the target")


def _result(request: LedgerRequest) -> dict:
    return {"schema_version": 1, "operation": "pr-relation-ledger", **request.target,
            "before_body_sha256": sha256(request.preimage["body"]),
            "after_body_sha256": sha256(request.body), "title_sha256": sha256(request.title),
            "state": request.preimage["state"], "is_draft": request.preimage["is_draft"],
            "status": "blocked", "no_op": False, "receipt_id": None, "receipt_sha256": None}


def _matches(request: LedgerRequest, live: dict, body: str) -> bool:
    return (isinstance(live, dict) and live.get("kind") == "PullRequest"
            and type(live.get("number")) is int
            and all(live.get(key) == value for key, value in request.target.items())
            and live.get("title") == request.title and live.get("body") == body
            and live.get("state") == request.preimage["state"]
            and live.get("is_draft") is request.preimage["is_draft"])


def _safe_read(forge: Forge, target: dict) -> dict:
    live = forge.read(target)
    if (not isinstance(live, dict) or not all(isinstance(live.get(key), str) for key in ("title", "body"))
            or any(contains_suspected_secret(live[key]) for key in ("title", "body"))):
        raise PublicationError("stored PR text is unavailable or sensitive")
    return live


def publish(manifest: dict, title_bytes: bytes, body_bytes: bytes, *, review_mode: str,
            selected_specialists: list[str], forge: Forge | None = None,
            receipt_root: Path | None = None, reconcile: bool = False,
            renew_after_receipt: str | None = None) -> dict:
    """Validate, lease, reread, write once, and verify. Root injection is for tests only."""
    request = validate_request(manifest, title_bytes, body_bytes, review_mode=review_mode,
                               selected_specialists=selected_specialists)
    result = _result(request)
    if reconcile and renew_after_receipt is not None:
        return {**result, "reason": "reconciliation and renewed publication are separate operations"}
    if review_mode == "required":
        return {**result, "reason": "required review is unsupported for historical relation-ledger edits"}
    forge = forge or GitHubForge()
    attempted = False
    uncertain = False
    try:
        root = prepare_receipt_store(receipt_root)
        identity = LeaseIdentity(request.target["repository"], request.target["number"])
        with receipt_ledger_lock(root, identity):
            receipts = RelationLedgerReceipts(root, request.target)
            pending = receipts.pending_attempt(result, request.manifest_sha256)
            uncertain = pending is not None
            if pending is not None:
                if reconcile:
                    live = _safe_read(forge, request.target)
                    if _matches(request, live, request.body):
                        observed = {**result, "status": "verified", "no_op": True,
                                    "provenance": "observed-after-uncertain"}
                        observed = receipts.record(observed, request.manifest_sha256, request.review,
                                                   pending["attempt_id"], pending["renewal_receipt_sha256"])
                        receipts.clear()
                        return observed
                    if _matches(request, live, request.preimage["body"]):
                        observed = {**result, "no_op": True, "provenance": "observed-preimage",
                                    "renewal_required": True,
                                    "reason": "preimage observed; explicitly renew against this receipt before another write"}
                        return receipts.record(observed, request.manifest_sha256, request.review,
                                               pending["attempt_id"], pending["renewal_receipt_sha256"])
                    return {**result, "status": "unknown", "reason": "live state matches neither bound preimage nor candidate"}
                if renew_after_receipt is None:
                    return {**result, "status": "unknown", "reason": "prior mutation requires --reconcile with the same intent"}
                receipts.validate_renewal(renew_after_receipt, pending)
                live = _safe_read(forge, request.target)
                if not _matches(request, live, request.preimage["body"]):
                    return {**result, "status": "unknown", "reason": "renewal preimage drifted; reconcile before further action"}
            elif renew_after_receipt is not None:
                return {**result, "reason": "renewal receipt has no matching unresolved attempt"}
            live = _safe_read(forge, request.target)
            if _matches(request, live, request.body):
                result.update(status="verified", no_op=True,
                              provenance="observed-after-uncertain" if pending else "observed-existing")
                result = receipts.record(result, request.manifest_sha256, request.review,
                                         pending["attempt_id"] if pending else None,
                                         pending["renewal_receipt_sha256"] if pending else None)
                if pending:
                    receipts.clear()
                return result
            if not _matches(request, live, request.preimage["body"]):
                return {**result, "reason": "target identity or expected text/state drifted"}
            if reconcile:
                return {**result, "reason": "no pending mutation to reconcile; publication requires an explicit invocation"}
            attempt_id = receipts.begin(result, request.manifest_sha256, renew_after_receipt, pending)
            try:
                live = _safe_read(forge, request.target)
            except (PublicationError, OSError, ValueError):
                if not uncertain:
                    receipts.clear()
                return {**result, "status": "unknown" if uncertain else "blocked", "reason": "final preimage read failed"}
            if not _matches(request, live, request.preimage["body"]):
                if not uncertain:
                    receipts.clear()
                return {**result, "status": "unknown" if uncertain else "blocked",
                        "reason": "target drifted immediately before mutation"}
            attempted = True
            acknowledged = True
            try:
                forge.write_body(request.target, request.body)
            except (PublicationError, OSError, ValueError):
                acknowledged = False
            try:
                live = _safe_read(forge, request.target)
            except (PublicationError, OSError, ValueError):
                return {**result, "status": "unknown", "reason": "post-mutation read failed; do not retry"}
            if not acknowledged or not _matches(request, live, request.body):
                return {**result, "status": "unknown", "reason": "mutation outcome is uncertain; do not retry"}
            result.update(status="verified", provenance="wrote-and-verified")
            result = receipts.record(result, request.manifest_sha256, request.review, attempt_id, renew_after_receipt)
            receipts.clear()
            return result
    except (PublicationError, OSError, ValueError):
        return {**_result(request), "status": "unknown" if attempted or uncertain else "blocked",
                "reason": "publication evidence or forge read failed; reconcile before retry"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    recovery = parser.add_mutually_exclusive_group()
    recovery.add_argument("--reconcile", action="store_true", help="observe an unresolved attempt without a forge mutation")
    recovery.add_argument("--renew-after-receipt", help="explicitly renew an attempt after its observed-preimage receipt")
    args = parser.parse_args(argv)
    try:
        manifest, title, body, specialists = read_inputs(args)
        result = publish(manifest, title, body, review_mode=args.review_mode, selected_specialists=specialists,
                         reconcile=args.reconcile, renew_after_receipt=args.renew_after_receipt)
    except LedgerValidationError as error:
        result = {"schema_version": 1, "operation": "pr-relation-ledger", "status": "blocked", "reason": str(error)}
    print(canonical_json(result))
    return 0 if result["status"] == "verified" else 2 if result["status"] == "unknown" else 1


if __name__ == "__main__":
    raise SystemExit(main())
