"""Validate one Tricritical-owned terminal review-evidence bundle.

Task Witness supplies a descriptor-bound flat bundle, retained trust snapshot,
and this exact registered validator. Rolecasting evidence is always validated
through Task Witness's registered-validator capability.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

BUNDLE_CONTRACT = "tricritical-terminal-review-evidence-v2"
PROJECTION_CONTRACT = "tricritical-terminal-review-projection-v2"
PROFILE_CONTRACT = "tricritical-review-profile-v1"
REPORT_CONTRACT = "tricritical-raw-report-v1"
ENSEMBLE_CONTRACT = "tricritical-ensemble-v1"
FEEDBACK_CONTRACT = "tricritical-external-feedback-v1"
ADJUDICATION_CONTRACT = "tricritical-adjudication-v1"
REVISION_CONTRACT = "tricritical-revision-v1"
MUTATION_AUTHORITY_CONTRACT = "tricritical-mutation-authority-v1"
CURRENT_INCREMENT_CONTRACT = "tricritical-current-increment-v1"
RETAINED_SCOPE_CONTRACT = "tricritical-retained-scope-v1"
UNCHANGED_SCOPE_PROOF_CONTRACT = "tricritical-unchanged-scope-proof-v1"
SEAM_CHOICE_CONTRACT = "tricritical-seam-choice-v1"
ROLECASTING_EVIDENCE_CONTRACT = "rolecasting-dispatch-evidence-v2"
ROLECASTING_PROJECTION_CONTRACT = "rolecasting-dispatch-projection-v2"

TERMINALS = {
    "clean",
    "clean / degraded",
    "incomplete / non-clean",
    "blocked",
    "failed_verification",
    "needs operator decision",
}
DISPOSITIONS = {
    "accept",
    "reject",
    "already addressed",
    "stale",
    "duplicate",
    "needs operator decision",
    "blocked",
    "follow-up outside scope",
}
DISPOSITION_OWNERS = {
    "accept": "reviser",
    "reject": "none",
    "already addressed": "none",
    "stale": "none",
    "duplicate": "none",
    "needs operator decision": "operator",
    "blocked": "blocker",
    "follow-up outside scope": "follow-up",
}
CONTRACT_RELATIONS = {
    "current-contract-contradiction",
    "stronger-future-guarantee",
    "unsupported-input-defense",
    "hypothetical-extension",
}
FUTURE_RELATIONS = CONTRACT_RELATIONS - {"current-contract-contradiction"}
SEAM_CHOICES = {
    "narrow-claim",
    "narrow-supported-input",
    "redesign",
    "accept-residual-risk-outside-claim",
    "confirm-stronger-guarantee",
}


def _witness() -> Any:
    witness = globals().get("_TASK_WITNESS")
    if witness is None:
        raise RuntimeError("Tricritical review evidence requires Task Witness")
    return witness


def _raw_sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _subject(value: Any, label: str) -> dict[str, Any]:
    witness = _witness()
    value = witness.exact(value, {"candidate", "review_input", "requirements"}, label)
    return {
        "candidate": witness.identity(value["candidate"], f"{label}.candidate"),
        "review_input": witness.identity(
            value["review_input"], f"{label}.review_input"
        ),
        "requirements": witness.identity(
            value["requirements"], f"{label}.requirements", absent=True
        ),
    }


def _role_subject(kind: str, value: Any) -> dict[str, str]:
    digest = _witness().digest(value)
    return {"kind": kind, "value": digest, "content_sha256": digest}


def _identity_list(value: Any, label: str) -> list[dict[str, Any]]:
    witness = _witness()
    if not isinstance(value, list):
        raise witness.EvidenceError(f"{label} must be a list")
    result = [witness.identity(item, f"{label} item") for item in value]
    if len({witness.digest(item) for item in result}) != len(result):
        raise witness.EvidenceError(f"{label} contains duplicates")
    return result


def _token_list(value: Any, label: str) -> list[str]:
    witness = _witness()
    if not isinstance(value, list):
        raise witness.EvidenceError(f"{label} must be a list")
    result = [witness.token(item, f"{label} item") for item in value]
    if result != sorted(set(result)):
        raise witness.EvidenceError(f"{label} must be sorted and unique")
    return result


def _text_list(value: Any, label: str) -> list[str]:
    witness = _witness()
    if not isinstance(value, list):
        raise witness.EvidenceError(f"{label} must be a list")
    result = [witness.text(item, f"{label} item") for item in value]
    if len(result) != len(set(result)):
        raise witness.EvidenceError(f"{label} contains duplicates")
    return result


def _current_increment(value: Any, label: str) -> dict[str, Any]:
    witness = _witness()
    value = witness.document(
        value,
        {
            "authorized_outcome",
            "claims",
            "supported_inputs",
            "acceptance_criteria",
            "reviewer_scopes",
        },
        label,
        CURRENT_INCREMENT_CONTRACT,
    )
    witness.identity(value["authorized_outcome"], f"{label}.authorized_outcome")
    for field in ("claims", "supported_inputs", "acceptance_criteria"):
        if not _identity_list(value[field], f"{label}.{field}"):
            raise witness.EvidenceError(f"{label}.{field} must not be empty")
    if not isinstance(value["reviewer_scopes"], list) or not value["reviewer_scopes"]:
        raise witness.EvidenceError(f"{label}.reviewer_scopes must not be empty")
    scopes: dict[str, dict[str, Any]] = {}
    for item in value["reviewer_scopes"]:
        item = witness.exact(
            item, {"role", "scope", "dependencies"}, f"{label} reviewer scope"
        )
        role = witness.token(item["role"], f"{label} reviewer role")
        if role not in {
            "critic-intent",
            "critic-runtime",
            "critic-structure",
        } and not role.startswith("specialist-"):
            raise witness.EvidenceError(f"{label} reviewer role is invalid")
        if role in scopes:
            raise witness.EvidenceError(f"{label} reviewer roles are duplicated")
        scope = witness.identity(item["scope"], f"{label}.{role}.scope")
        dependencies = _identity_list(
            item["dependencies"], f"{label}.{role}.dependencies"
        )
        scopes[role] = {
            "role": role,
            "scope": scope,
            "dependencies": dependencies,
        }
    if list(scopes) != sorted(scopes):
        raise witness.EvidenceError(f"{label} reviewer scopes must be sorted")
    return {"document": value, "scopes": scopes}


def _increment_identity(increment: dict[str, Any]) -> dict[str, str]:
    digest = _witness().digest(increment)
    return {
        "kind": CURRENT_INCREMENT_CONTRACT,
        "value": digest,
        "content_sha256": digest,
    }


def _dispatch(
    reference: Any,
    expected_subject: dict[str, str],
    expected_bundle_sha256: str,
    trust_snapshot: dict[str, Any],
    label: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    witness = _witness()
    reference = witness.exact(
        reference, {"path", "bundle_sha256"}, f"{label} reference"
    )
    path = witness.absolute(
        Path(witness.text(reference["path"], f"{label}.path")), label
    )
    witness.sha(reference["bundle_sha256"], f"{label}.bundle_sha256")
    envelope = witness.invoke_registered_validator(path, trust_snapshot)
    envelope = witness.exact(
        envelope,
        {"contract", "bundle_sha256", "producer", "validator", "projection"},
        f"{label} canonical envelope",
    )
    projection = witness.exact(
        envelope["projection"],
        {
            "schema_version",
            "contract",
            "evidence_contract",
            "manifest_sha256",
            "plan_sha256",
            "subject",
            "producer",
            "executions",
            "content_sha256",
        },
        f"{label} projection",
    )
    if (
        envelope["contract"] != "task-witness-canonical-projection-v2"
        or envelope["bundle_sha256"] != reference["bundle_sha256"]
        or envelope["bundle_sha256"] != expected_bundle_sha256
        or projection["contract"] != ROLECASTING_PROJECTION_CONTRACT
        or projection["evidence_contract"] != ROLECASTING_EVIDENCE_CONTRACT
        or projection["subject"] != expected_subject
    ):
        raise witness.EvidenceError(f"{label} registered Rolecasting binding mismatch")
    unsigned = {
        key: item for key, item in projection.items() if key != "content_sha256"
    }
    if projection["content_sha256"] != witness.digest(unsigned):
        raise witness.EvidenceError(f"{label} projection content digest mismatch")
    return envelope, projection


def _finding(
    value: Any,
    label: str,
    source: str,
    reviewer_roles: set[str],
    expected_reviewer_scope: str | None = None,
) -> tuple[str, dict[str, Any]]:
    witness = _witness()
    value = witness.exact(
        value,
        {
            "finding_id",
            "kind",
            "cause",
            "reviewer_scope",
            "contract_relation",
            "material_current_risk",
            "current_dependency",
            "evidence",
            "affected_contract",
            "causal_path",
            "impact",
            "severity",
            "direction",
            "proof_required",
            "limitations",
            "residual_risk",
        },
        label,
    )
    finding_id = witness.token(value["finding_id"], f"{label}.finding_id")
    witness.token(value["kind"], f"{label}.kind")
    cause = witness.identity(value["cause"], f"{label}.cause")
    reviewer_scope = witness.token(value["reviewer_scope"], f"{label}.reviewer_scope")
    if reviewer_scope not in reviewer_roles:
        raise witness.EvidenceError(f"{label} is outside the frozen reviewer scopes")
    if (
        expected_reviewer_scope is not None
        and reviewer_scope != expected_reviewer_scope
    ):
        raise witness.EvidenceError(
            f"{label} reviewer scope differs from its producing execution role"
        )
    relation = witness.token(value["contract_relation"], f"{label}.contract_relation")
    if relation not in CONTRACT_RELATIONS:
        raise witness.EvidenceError(f"{label} contract relation is invalid")
    for field in ("material_current_risk", "current_dependency"):
        if type(value[field]) is not bool:
            raise witness.EvidenceError(f"{label}.{field} must be boolean")
    for field in (
        "affected_contract",
        "causal_path",
        "impact",
        "severity",
        "direction",
        "proof_required",
        "residual_risk",
    ):
        witness.text(value[field], f"{label}.{field}")
    _identity_list(value["evidence"], f"{label}.evidence")
    _text_list(value["limitations"], f"{label}.limitations")
    finding_ref = f"{source}:{finding_id}:{witness.digest(value)}"
    return finding_ref, {
        "cause": cause,
        "reviewer_scope": reviewer_scope,
        "contract_relation": relation,
        "material_current_risk": value["material_current_risk"],
        "current_dependency": value["current_dependency"],
    }


def _report(
    value: Any,
    subject: dict[str, Any],
    execution_id: str,
    execution: dict[str, Any],
    reviewer_roles: set[str],
) -> tuple[dict[str, dict[str, Any]], set[str], str]:
    witness = _witness()
    value = witness.document(
        value,
        {
            "subject",
            "execution_id",
            "findings",
            "falsification_attempts",
            "outcome",
            "limitations",
        },
        "Tricritical raw report",
        REPORT_CONTRACT,
    )
    if (
        _subject(value["subject"], "raw report.subject") != subject
        or value["execution_id"] != execution_id
    ):
        raise witness.EvidenceError("Tricritical raw report is cross-bound")
    if not isinstance(value["findings"], list):
        raise witness.EvidenceError("Tricritical raw report findings must be a list")
    source = f"{execution_id}:{execution['result_sha256']}"
    findings = dict(
        _finding(
            item,
            "raw report finding",
            source,
            reviewer_roles,
            execution["role"],
        )
        for item in value["findings"]
    )
    if len(findings) != len(value["findings"]):
        raise witness.EvidenceError("Tricritical raw report has duplicate findings")
    _text_list(value["falsification_attempts"], "raw report falsification attempts")
    limitations = set(_text_list(value["limitations"], "raw report limitations"))
    outcome = witness.exact(
        value["outcome"], {"status", "usable", "failure"}, "raw report outcome"
    )
    if outcome["status"] not in {
        "complete",
        "failed",
        "timed-out",
        "unusable",
        "budget-exhausted",
    }:
        raise witness.EvidenceError("Tricritical raw report outcome is invalid")
    if type(outcome["usable"]) is not bool:
        raise witness.EvidenceError("Tricritical raw report usable flag is invalid")
    if (outcome["status"] == "complete") != outcome["usable"]:
        raise witness.EvidenceError("Tricritical raw report outcome is inconsistent")
    if outcome["usable"]:
        if outcome["failure"] is not None:
            raise witness.EvidenceError("usable raw report carries failure evidence")
    else:
        witness.identity(outcome["failure"], "raw report failure")
    return findings, limitations, outcome["status"]


def _ensemble(
    value: Any,
    subject: dict[str, Any],
    envelope: dict[str, Any],
    projection: dict[str, Any],
    report_hashes: dict[str, str],
    report_limitations: set[str],
) -> dict[str, Any]:
    witness = _witness()
    value = witness.document(
        value,
        {
            "subject",
            "dispatch_bundle_sha256",
            "dispatch_projection_sha256",
            "reports",
            "risk",
            "completeness",
            "causal_synthesis",
            "limitations",
        },
        "Tricritical review ensemble",
        ENSEMBLE_CONTRACT,
    )
    if (
        _subject(value["subject"], "ensemble.subject") != subject
        or value["dispatch_bundle_sha256"] != envelope["bundle_sha256"]
        or value["dispatch_projection_sha256"] != witness.digest(projection)
        or value["reports"] != report_hashes
    ):
        raise witness.EvidenceError("Tricritical review ensemble is cross-bound")
    risk = witness.exact(
        value["risk"],
        {
            "rationale",
            "selected_axes",
            "selected_specialists",
            "waived_specialists",
        },
        "ensemble risk",
    )
    witness.text(risk["rationale"], "ensemble risk rationale")
    axes = _token_list(risk["selected_axes"], "selected axes")
    if not set(axes).issubset({"intent", "runtime", "structure"}):
        raise witness.EvidenceError("Tricritical selected axes are invalid")
    selected = _token_list(risk["selected_specialists"], "selected specialists")
    waived = _token_list(risk["waived_specialists"], "waived specialists")
    if set(selected) & set(waived):
        raise witness.EvidenceError(
            "Tricritical selected and waived specialists overlap"
        )
    limitations = _text_list(value["limitations"], "ensemble limitations")
    if set(limitations) != report_limitations:
        raise witness.EvidenceError("Tricritical ensemble loses raw limitations")
    _text_list(value["causal_synthesis"], "ensemble causal synthesis")
    completeness = witness.exact(
        value["completeness"],
        {
            "execution_mode",
            "missing",
            "failed",
            "unusable",
            "budget_exhausted",
        },
        "ensemble completeness",
    )
    if completeness["execution_mode"] not in {
        "independent",
        "non-independent / degraded",
        "incomplete / non-clean",
    }:
        raise witness.EvidenceError("Tricritical execution mode is invalid")
    for field in ("missing", "failed", "unusable", "budget_exhausted"):
        _token_list(completeness[field], f"ensemble completeness {field}")
    if "disposition" in value or "terminal" in value:
        raise witness.EvidenceError(
            "Tricritical ensemble cannot adjudicate or terminate"
        )
    return {
        "risk": risk,
        "selected_axes": axes,
        "selected_specialists": selected,
        "waived_specialists": waived,
        "limitations": limitations,
        "completeness": completeness,
    }


def _feedback(
    value: Any,
    subject: dict[str, Any],
    report_hashes: dict[str, str],
    ensemble_raw: bytes,
    trust_snapshot: dict[str, Any],
    reviewer_roles: set[str],
) -> dict[str, dict[str, Any]]:
    witness = _witness()
    value = witness.document(
        value,
        {
            "issuer",
            "subject",
            "freeze",
            "acquisition",
            "state",
            "source",
            "findings",
            "reason",
        },
        "Tricritical external feedback",
        FEEDBACK_CONTRACT,
    )
    witness.issuer(
        value["issuer"],
        trust_snapshot,
        "external feedback issuer",
        "feedback-observation",
    )
    if _subject(value["subject"], "external feedback.subject") != subject:
        raise witness.EvidenceError("Tricritical external feedback is cross-bound")
    freeze = witness.exact(
        value["freeze"],
        {"reports_sha256", "ensemble_sha256", "sequence"},
        "external feedback freeze",
    )
    acquisition = witness.exact(
        value["acquisition"], {"sequence", "forge_state"}, "feedback acquisition"
    )
    if (
        freeze["reports_sha256"] != witness.digest(report_hashes)
        or freeze["ensemble_sha256"] != _raw_sha(ensemble_raw)
        or type(freeze["sequence"]) is not int
        or type(acquisition["sequence"]) is not int
        or acquisition["sequence"] <= freeze["sequence"]
    ):
        raise witness.EvidenceError(
            "external feedback was not acquired after review freeze"
        )
    if not isinstance(value["findings"], list):
        raise witness.EvidenceError("external feedback findings must be a list")
    state = value["state"]
    if state == "observed":
        witness.identity(value["source"], "external feedback source")
        valid = (
            bool(value["findings"])
            and value["reason"] is None
            and acquisition["forge_state"] == "forged"
        )
    elif state == "empty":
        witness.identity(value["source"], "external feedback source")
        valid = (
            not value["findings"]
            and isinstance(value["reason"], str)
            and acquisition["forge_state"] == "forged"
        )
    elif state == "not-applicable-pre-forge":
        valid = (
            value["source"] is None
            and not value["findings"]
            and value["reason"] == "pre-forge"
            and acquisition["forge_state"] == "pre-forge"
        )
    else:
        valid = False
    if not valid:
        raise witness.EvidenceError("external feedback conditional state is invalid")
    findings = dict(
        _finding(
            item,
            "external feedback finding",
            "external-feedback",
            reviewer_roles,
        )
        for item in value["findings"]
    )
    if len(findings) != len(value["findings"]):
        raise witness.EvidenceError("external feedback has duplicate findings")
    return findings


def _adjudication(
    value: Any,
    subject: dict[str, Any],
    findings: dict[str, dict[str, Any]],
    execution_id: str,
    returned: dict[str, Any],
    expected_findings_sha256: str,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    witness = _witness()
    value = witness.document(
        value,
        {
            "subject",
            "execution_id",
            "findings_sha256",
            "items",
            "causal_groups",
            "disagreements",
            "limitations",
        },
        "Tricritical adjudication",
        ADJUDICATION_CONTRACT,
    )
    if (
        _subject(value["subject"], "adjudication.subject") != subject
        or value["execution_id"] != execution_id
        or value["findings_sha256"] != expected_findings_sha256
        or returned["kind"] != ADJUDICATION_CONTRACT
        or returned["value"] != execution_id
        or returned["content_sha256"]
        != _raw_sha(_witness().canonical_bytes(value) + b"\n")
    ):
        raise witness.EvidenceError("Tricritical adjudication is cross-bound")
    if not isinstance(value["items"], list):
        raise witness.EvidenceError("Tricritical adjudication items must be a list")
    items: dict[str, dict[str, Any]] = {}
    for item in value["items"]:
        item = witness.exact(
            item,
            {"finding_ref", "disposition", "evidence", "next_owner"},
            "adjudication item",
        )
        finding_ref = witness.text(item["finding_ref"], "adjudication finding ref")
        if finding_ref in items or item["disposition"] not in DISPOSITIONS:
            raise witness.EvidenceError("adjudication disposition is invalid")
        if not _identity_list(item["evidence"], "adjudication evidence"):
            raise witness.EvidenceError("adjudication evidence must not be empty")
        if item["next_owner"] != DISPOSITION_OWNERS[item["disposition"]]:
            raise witness.EvidenceError(
                "adjudication next owner disagrees with disposition"
            )
        finding = findings.get(finding_ref)
        if (
            finding is not None
            and item["disposition"] == "follow-up outside scope"
            and (
                finding["contract_relation"] == "current-contract-contradiction"
                or finding["material_current_risk"]
                or finding["current_dependency"]
            )
        ):
            raise witness.EvidenceError(
                "current contract finding cannot be follow-up outside scope"
            )
        items[finding_ref] = item
    if set(items) != set(findings):
        raise witness.EvidenceError("every finding must be adjudicated exactly once")
    for finding_ref, item in items.items():
        if item["disposition"] == "duplicate":
            cause = witness.digest(findings[finding_ref]["cause"])
            if not any(
                other_ref != finding_ref and witness.digest(other["cause"]) == cause
                for other_ref, other in findings.items()
            ):
                raise witness.EvidenceError(
                    "duplicate disposition requires a distinct finding with the same cause"
                )
    dispositions_by_cause: dict[str, set[str]] = {}
    for finding_ref, item in items.items():
        cause = witness.digest(findings[finding_ref]["cause"])
        dispositions_by_cause.setdefault(cause, set()).add(item["disposition"])
    if any(
        dispositions == {"duplicate"}
        for dispositions in dispositions_by_cause.values()
    ):
        raise witness.EvidenceError("duplicate cause lacks a canonical disposition")
    if not isinstance(value["causal_groups"], list):
        raise witness.EvidenceError("adjudication causal groups must be a list")
    for group in value["causal_groups"]:
        group = witness.exact(group, {"group_id", "findings"}, "causal group")
        witness.token(group["group_id"], "causal group id")
        refs = _text_list(group["findings"], "causal group findings")
        if not set(refs).issubset(findings):
            raise witness.EvidenceError("causal group contains an unknown finding")
    _text_list(value["disagreements"], "adjudication disagreements")
    limitations = _text_list(value["limitations"], "adjudication limitations")
    return items, limitations


def _verification(
    value: Any,
    subject: dict[str, Any],
    trust_snapshot: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    witness = _witness()
    value = witness.exact(
        value,
        {"issuer", "status", "candidate", "evidence", "unchanged"},
        label,
    )
    witness.issuer(
        value["issuer"], trust_snapshot, f"{label} issuer", "terminal-verification"
    )
    if value["status"] not in {"passed", "failed", "unavailable"}:
        raise witness.EvidenceError(f"{label} status is invalid")
    candidate = witness.identity(value["candidate"], f"{label}.candidate")
    witness.identity(value["evidence"], f"{label}.evidence")
    if type(value["unchanged"]) is not bool or candidate != subject["candidate"]:
        raise witness.EvidenceError(f"{label} candidate binding is invalid")
    return {
        "status": value["status"],
        "candidate": candidate,
        "evidence": value["evidence"],
        "unchanged": value["unchanged"],
    }


def _claim_dispatch_isolation(
    projection: dict[str, Any],
    seen: dict[str, set[str]],
    label: str,
) -> None:
    witness = _witness()
    executions = projection["executions"]
    execution_ids = {item["execution_id"] for item in executions.values()}
    sessions = {item["isolation"]["session"] for item in executions.values()}
    contexts = {item["isolation"]["context"] for item in executions.values()}
    if (
        any(key != item["execution_id"] for key, item in executions.items())
        or len(execution_ids) != len(executions)
        or len(sessions) != len(executions)
        or len(contexts) != len(executions)
        or execution_ids & seen["executions"]
        or sessions & seen["sessions"]
        or contexts & seen["contexts"]
    ):
        raise witness.EvidenceError(f"{label} reuses execution isolation")
    seen["executions"].update(execution_ids)
    seen["sessions"].update(sessions)
    seen["contexts"].update(contexts)


def _mutation_authority(
    value: Any,
    initial_subject: dict[str, Any],
    trust_snapshot: dict[str, Any],
) -> dict[str, Any] | None:
    if value is None:
        return None
    witness = _witness()
    value = witness.document(
        value,
        {"issuer", "subject", "authority", "scope", "declared_verification"},
        "Tricritical mutation authority",
        MUTATION_AUTHORITY_CONTRACT,
    )
    witness.issuer(
        value["issuer"],
        trust_snapshot,
        "mutation authority issuer",
        "mutation-authority",
    )
    if _subject(value["subject"], "mutation authority subject") != initial_subject:
        raise witness.EvidenceError("Tricritical mutation authority is cross-bound")
    for field in ("authority", "scope", "declared_verification"):
        witness.identity(value[field], f"mutation authority {field}")
    return {
        "document": value,
        "receipt_sha256": _raw_sha(witness.canonical_bytes(value) + b"\n"),
    }


def _revision(
    value: Any,
    subject: dict[str, Any],
    accepted: set[str],
    authority: dict[str, Any] | None,
    increment: dict[str, Any],
) -> dict[str, Any] | None:
    if value is None:
        return None
    witness = _witness()
    if not accepted or authority is None:
        raise witness.EvidenceError(
            "Tricritical revision lacks accepted work or authority"
        )
    value = witness.document(
        value,
        {
            "subject",
            "accepted_findings",
            "mutation_authority_sha256",
            "pre_edit_candidate",
            "successor_subject",
            "deletion_alternatives",
            "resolution_evidence",
            "verification",
            "fresh_review_required",
            "clarified_requirements",
            "adapted_increment",
        },
        "Tricritical revision",
        REVISION_CONTRACT,
    )
    accepted_findings = _text_list(value["accepted_findings"], "revision findings")
    if set(accepted_findings) != accepted:
        raise witness.EvidenceError(
            "Tricritical revision does not cover accepted findings"
        )
    if value["mutation_authority_sha256"] != authority["receipt_sha256"]:
        raise witness.EvidenceError(
            "Tricritical revision does not use original authority"
        )
    if (
        witness.identity(value["pre_edit_candidate"], "revision pre-edit candidate")
        != subject["candidate"]
    ):
        raise witness.EvidenceError("Tricritical revision pre-edit identity drift")
    successor = _subject(value["successor_subject"], "revision successor subject")
    if successor["candidate"] == subject["candidate"]:
        raise witness.EvidenceError("Tricritical revision successor is not distinct")
    adapted = value["adapted_increment"]
    if adapted is None:
        successor_increment = increment
    else:
        successor_increment = _current_increment(adapted, "revision adapted increment")[
            "document"
        ]
        if successor_increment == increment:
            raise witness.EvidenceError(
                "Tricritical adapted increment does not change the frozen contract"
            )
    if successor["review_input"] != _increment_identity(successor_increment):
        raise witness.EvidenceError(
            "Tricritical revision successor is not bound to its frozen increment"
        )
    clarified = value["clarified_requirements"]
    if clarified is None:
        if successor["requirements"] != subject["requirements"]:
            raise witness.EvidenceError(
                "Tricritical revision changes requirements without clarification"
            )
    elif (
        witness.identity(clarified, "revision clarified requirements")
        != successor["requirements"]
        or successor["requirements"] == subject["requirements"]
    ):
        raise witness.EvidenceError("Tricritical revision clarification is invalid")
    alternatives = _text_list(value["deletion_alternatives"], "revision alternatives")
    if not alternatives:
        raise witness.EvidenceError("Tricritical revision lacks deletion alternatives")
    resolutions = value["resolution_evidence"]
    if not isinstance(resolutions, dict) or set(resolutions) != accepted:
        raise witness.EvidenceError(
            "Tricritical revision resolution inventory is incomplete"
        )
    for finding_ref, evidence in resolutions.items():
        if not _identity_list(evidence, f"revision resolution {finding_ref}"):
            raise witness.EvidenceError(
                "Tricritical revision resolution lacks evidence"
            )
    verification = witness.exact(
        value["verification"],
        {"status", "before_candidate", "after_candidate", "evidence"},
        "revision verification",
    )
    if (
        verification["status"] != "passed"
        or witness.identity(
            verification["before_candidate"], "revision verification before"
        )
        != subject["candidate"]
        or witness.identity(
            verification["after_candidate"], "revision verification after"
        )
        != successor["candidate"]
    ):
        raise witness.EvidenceError("Tricritical revision verification is invalid")
    witness.identity(verification["evidence"], "revision verification evidence")
    if value["fresh_review_required"] is not True:
        raise witness.EvidenceError("Tricritical revision must require fresh review")
    return {
        "document": value,
        "successor": successor,
        "successor_increment": successor_increment,
    }


def _cycle_state(
    cycle: dict[str, Any],
    authority: dict[str, Any] | None,
    revision: dict[str, Any] | None,
    index: int,
) -> dict[str, Any]:
    witness = _witness()
    progress = witness.exact(
        cycle["progress"], {"status", "evidence"}, f"cycle {index} progress"
    )
    evidence = _identity_list(progress["evidence"], f"cycle {index} progress evidence")
    if revision is not None:
        if progress["status"] != "progressed" or not evidence:
            raise witness.EvidenceError(
                "revision cycle lacks material progress evidence"
            )
    elif progress["status"] not in {"fixed-point", "stopped"} or evidence:
        raise witness.EvidenceError("non-revision cycle progress state is invalid")
    state = witness.exact(
        cycle["mutation_authority"],
        {"available", "receipt_sha256"},
        f"cycle {index} mutation authority",
    )
    expected_state = {
        "available": authority is not None,
        "receipt_sha256": authority["receipt_sha256"]
        if authority is not None
        else None,
    }
    if state != expected_state:
        raise witness.EvidenceError(
            "Tricritical cycle mutation authority state is invalid"
        )
    return {"progress": progress}


def _retained_scope(
    value: Any,
    current_subject: dict[str, Any],
    current_scope: dict[str, Any],
    history: list[dict[str, Any]],
    label: str,
) -> str:
    witness = _witness()
    value = witness.document(
        value,
        {
            "role",
            "scope",
            "dependencies",
            "source_subject",
            "prior_report",
            "unchanged_proof",
        },
        label,
        RETAINED_SCOPE_CONTRACT,
    )
    role = witness.token(value["role"], f"{label}.role")
    scope = witness.identity(value["scope"], f"{label}.scope")
    dependencies = _identity_list(value["dependencies"], f"{label}.dependencies")
    source_subject = _subject(value["source_subject"], f"{label}.source_subject")
    prior_report = witness.identity(value["prior_report"], f"{label}.prior_report")
    proof = witness.document(
        value["unchanged_proof"],
        {
            "source_subject",
            "target_subject",
            "role",
            "scope",
            "dependencies",
            "evidence",
        },
        f"{label}.unchanged_proof",
        UNCHANGED_SCOPE_PROOF_CONTRACT,
    )
    proof_evidence = _identity_list(
        proof["evidence"], f"{label}.unchanged_proof.evidence"
    )
    if not proof_evidence:
        raise witness.EvidenceError(
            f"{label} unchanged proof evidence must not be empty"
        )
    if (
        role != current_scope["role"]
        or scope != current_scope["scope"]
        or dependencies != current_scope["dependencies"]
    ):
        raise witness.EvidenceError(f"{label} changes its frozen scope or dependencies")
    if (
        _subject(proof["source_subject"], f"{label} proof source subject")
        != source_subject
        or _subject(proof["target_subject"], f"{label} proof target subject")
        != current_subject
        or proof["role"] != role
        or witness.identity(proof["scope"], f"{label} proof scope") != scope
        or _identity_list(proof["dependencies"], f"{label} proof dependencies")
        != dependencies
    ):
        raise witness.EvidenceError(
            f"{label} unchanged proof is not bound to the retained scope"
        )
    if prior_report["kind"] != REPORT_CONTRACT or not any(
        entry["role"] == role
        and entry["scope"] == scope
        and entry["dependencies"] == dependencies
        and entry["subject"] == source_subject
        and entry["report"] == prior_report
        for entry in history
    ):
        raise witness.EvidenceError(f"{label} lacks a prior usable report identity")
    return role


def _seam_choices(
    values: Any,
    subject: dict[str, Any],
    recurring_causes: dict[str, dict[str, Any]],
    trust_snapshot: dict[str, Any],
    index: int,
) -> dict[str, dict[str, Any]]:
    witness = _witness()
    if not isinstance(values, list):
        raise witness.EvidenceError(f"cycle {index} seam choices must be a list")
    choices: dict[str, dict[str, Any]] = {}
    for value in values:
        value = witness.document(
            value,
            {"issuer", "subject", "cause", "choice", "evidence"},
            f"cycle {index} seam choice",
            SEAM_CHOICE_CONTRACT,
        )
        witness.issuer(
            value["issuer"],
            trust_snapshot,
            f"cycle {index} seam choice issuer",
            "seam-choice",
        )
        if _subject(value["subject"], f"cycle {index} seam choice subject") != subject:
            raise witness.EvidenceError("Tricritical seam choice is cross-bound")
        cause = witness.identity(value["cause"], f"cycle {index} seam choice cause")
        cause_key = witness.digest(cause)
        if cause_key in choices or value["choice"] not in SEAM_CHOICES:
            raise witness.EvidenceError(
                "Tricritical seam choice is invalid or duplicated"
            )
        witness.identity(value["evidence"], f"cycle {index} seam choice evidence")
        choices[cause_key] = value
    if set(choices) != set(recurring_causes):
        raise witness.EvidenceError(
            "every recurring cause requires exactly one evidenced seam choice"
        )
    return choices


def _cause_matches(
    cause_key: str,
    findings: dict[str, dict[str, Any]],
    items: dict[str, dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    witness = _witness()
    return [
        (finding, items[finding_ref])
        for finding_ref, finding in findings.items()
        if witness.digest(finding["cause"]) == cause_key
    ]


def _changed_increment_fields(
    revision: dict[str, Any] | None,
    increment: dict[str, Any],
) -> set[str]:
    if revision is None or revision["document"]["adapted_increment"] is None:
        return set()
    successor = revision["successor_increment"]
    return {
        field
        for field in ("claims", "supported_inputs", "acceptance_criteria")
        if successor[field] != increment[field]
    }


def _require_confirm_for_future_accepts(
    findings: dict[str, dict[str, Any]],
    items: dict[str, dict[str, Any]],
    seam_choices: dict[str, dict[str, Any]],
) -> None:
    witness = _witness()
    for finding_ref, finding in findings.items():
        if (
            items[finding_ref]["disposition"] == "accept"
            and finding["contract_relation"] in FUTURE_RELATIONS
            and not finding["material_current_risk"]
            and not finding["current_dependency"]
        ):
            cause_key = witness.digest(finding["cause"])
            choice = seam_choices.get(cause_key)
            if choice is None or choice["choice"] != "confirm-stronger-guarantee":
                raise witness.EvidenceError(
                    "future-only finding cannot be accepted without a confirmed adaptation"
                )


def _enforce_seam_outcomes(
    seam_choices: dict[str, dict[str, Any]],
    findings: dict[str, dict[str, Any]],
    items: dict[str, dict[str, Any]],
    revision: dict[str, Any] | None,
    increment: dict[str, Any],
) -> None:
    changed = _changed_increment_fields(revision, increment)
    for cause_key, choice_document in seam_choices.items():
        matches = _cause_matches(cause_key, findings, items)
        accepted = any(item["disposition"] == "accept" for _, item in matches)
        choice = choice_document["choice"]
        if choice == "narrow-claim":
            valid = accepted and revision is not None and "claims" in changed
        elif choice == "narrow-supported-input":
            valid = accepted and revision is not None and "supported_inputs" in changed
        elif choice == "redesign":
            valid = (
                accepted
                and revision is not None
                and revision["successor"]["candidate"]
                != revision["document"]["pre_edit_candidate"]
            )
        elif choice == "accept-residual-risk-outside-claim":
            valid = bool(matches) and all(
                item["disposition"] == "follow-up outside scope"
                and finding["contract_relation"] != "current-contract-contradiction"
                and not finding["material_current_risk"]
                and not finding["current_dependency"]
                for finding, item in matches
            )
        else:
            valid = (
                any(
                    item["disposition"] == "accept"
                    and finding["contract_relation"] in FUTURE_RELATIONS
                    for finding, item in matches
                )
                and revision is not None
                and bool(changed)
            )
        if not valid:
            raise _witness().EvidenceError(
                "Tricritical seam choice outcome is not evidenced"
            )


def _finding_causes(
    findings: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    witness = _witness()
    return {
        witness.digest(finding["cause"]): finding["cause"]
        for finding in findings.values()
    }


def _cycle(
    cycle: Any,
    prior_subject: dict[str, Any],
    expected_increment: dict[str, Any],
    trust_snapshot: dict[str, Any],
    authority: dict[str, Any] | None,
    seen: dict[str, set[str]],
    scope_history: list[dict[str, Any]],
    seen_causes: dict[str, dict[str, Any]],
    required_fresh_roles: set[str],
    index: int,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any]]:
    witness = _witness()
    cycle = witness.exact(
        cycle,
        {
            "subject",
            "increment",
            "review_dispatch",
            "reports",
            "ensemble",
            "feedback",
            "adjudication_dispatch",
            "adjudication",
            "revision",
            "verification",
            "retained_scopes",
            "seam_choices",
            "progress",
            "mutation_authority",
            "owner",
        },
        f"Tricritical cycle {index}",
    )
    subject = _subject(cycle["subject"], f"cycle {index}.subject")
    if subject != prior_subject:
        raise witness.EvidenceError("Tricritical cycle subject chain is discontinuous")
    increment = _current_increment(
        cycle["increment"], f"cycle {index} current increment"
    )
    if increment["document"] != expected_increment or subject[
        "review_input"
    ] != _increment_identity(increment["document"]):
        raise witness.EvidenceError(
            "Tricritical cycle is not bound to its frozen current increment"
        )
    increment_scopes = increment["scopes"]
    reviewer_roles = set(increment_scopes)
    ensemble_value = witness.exact(
        cycle["ensemble"],
        set(cycle["ensemble"]),
        f"cycle {index} ensemble",
    )
    review_envelope, review_projection = _dispatch(
        cycle["review_dispatch"],
        _role_subject("tricritical-review-subject-v1", subject),
        ensemble_value.get("dispatch_bundle_sha256"),
        trust_snapshot,
        f"cycle {index} review dispatch",
    )
    _claim_dispatch_isolation(review_projection, seen, f"cycle {index} review")
    executions = review_projection["executions"]
    roles = [item["role"] for item in executions.values()]
    if len(roles) != len(set(roles)):
        raise witness.EvidenceError("Tricritical review roles are duplicated")
    fresh_roles = set(roles)
    if not fresh_roles.issubset(reviewer_roles):
        raise witness.EvidenceError(
            "Tricritical review dispatch contains an extra role"
        )
    for execution in executions.values():
        role = execution["role"]
        if execution["scope"] != increment_scopes[role]["scope"]:
            raise witness.EvidenceError(
                "Tricritical review dispatch scope differs from the frozen increment"
            )
    if not isinstance(cycle["retained_scopes"], list):
        raise witness.EvidenceError("Tricritical retained scopes must be a list")
    retained_roles: set[str] = set()
    for value in cycle["retained_scopes"]:
        raw_role = witness.token(
            value.get("role") if isinstance(value, dict) else None,
            f"cycle {index} retained scope role",
        )
        if raw_role not in increment_scopes:
            raise witness.EvidenceError("Tricritical retained scope has an extra role")
        role = _retained_scope(
            value,
            subject,
            increment_scopes[raw_role],
            scope_history,
            f"cycle {index} retained scope",
        )
        if role in retained_roles:
            raise witness.EvidenceError("Tricritical retained scopes are duplicated")
        retained_roles.add(role)
    if fresh_roles & retained_roles:
        raise witness.EvidenceError(
            "Tricritical fresh and retained reviewer scopes overlap"
        )
    if retained_roles & required_fresh_roles:
        raise witness.EvidenceError(
            "accepted finding scope requires fresh successor review"
        )
    if not isinstance(cycle["reports"], dict) or set(cycle["reports"]) != set(
        executions
    ):
        raise witness.EvidenceError("Tricritical report inventory is incomplete")
    findings: dict[str, dict[str, Any]] = {}
    report_limitations: set[str] = set()
    report_hashes: dict[str, str] = {}
    outcomes: dict[str, str] = {}
    for execution_id, report in cycle["reports"].items():
        execution = executions[execution_id]
        report_raw = witness.canonical_bytes(report) + b"\n"
        if (
            execution["returned"]["kind"] != REPORT_CONTRACT
            or execution["returned"]["value"] != execution_id
            or execution["returned"]["content_sha256"] != _raw_sha(report_raw)
        ):
            raise witness.EvidenceError(
                "raw report bytes do not match Rolecasting return"
            )
        report_findings, limitations, outcome = _report(
            report, subject, execution_id, execution, reviewer_roles
        )
        if type(execution.get("usable")) is not bool or execution["usable"] != (
            outcome == "complete"
        ):
            raise witness.EvidenceError(
                "raw report usability disagrees with Rolecasting"
            )
        findings.update(report_findings)
        report_limitations.update(limitations)
        report_hashes[execution_id] = _raw_sha(report_raw)
        outcomes[execution_id] = outcome
    for execution_id, execution in executions.items():
        if outcomes[execution_id] == "complete":
            role = execution["role"]
            scope_history.append(
                {
                    "role": role,
                    "scope": increment_scopes[role]["scope"],
                    "dependencies": increment_scopes[role]["dependencies"],
                    "subject": subject,
                    "report": {
                        "kind": REPORT_CONTRACT,
                        "value": execution_id,
                        "content_sha256": report_hashes[execution_id],
                    },
                }
            )
    ensemble_raw = witness.canonical_bytes(cycle["ensemble"]) + b"\n"
    ensemble = _ensemble(
        cycle["ensemble"],
        subject,
        review_envelope,
        review_projection,
        report_hashes,
        report_limitations,
    )
    expected_axes = sorted(
        role.removeprefix("critic-")
        for role in reviewer_roles
        if role.startswith("critic-")
    )
    expected_specialists = sorted(
        role.removeprefix("specialist-")
        for role in reviewer_roles
        if role.startswith("specialist-")
    )
    if (
        ensemble["selected_axes"] != expected_axes
        or ensemble["selected_specialists"] != expected_specialists
    ):
        raise witness.EvidenceError(
            "Tricritical ensemble roles differ from the frozen increment"
        )
    completeness = ensemble["completeness"]
    expected_missing = sorted(reviewer_roles - fresh_roles - retained_roles)
    expected_failed = sorted(
        execution_id
        for execution_id, status in outcomes.items()
        if status in {"failed", "timed-out"}
    )
    expected_unusable = sorted(
        execution_id
        for execution_id, status in outcomes.items()
        if status == "unusable"
    )
    expected_budget_exhausted = sorted(
        execution_id
        for execution_id, status in outcomes.items()
        if status == "budget-exhausted"
    )
    if (
        completeness["missing"] != expected_missing
        or completeness["failed"] != expected_failed
        or completeness["unusable"] != expected_unusable
        or completeness["budget_exhausted"] != expected_budget_exhausted
    ):
        raise witness.EvidenceError(
            "Tricritical completeness does not match executions"
        )
    incomplete = bool(
        expected_missing
        or expected_failed
        or expected_unusable
        or expected_budget_exhausted
    )
    if incomplete != (completeness["execution_mode"] == "incomplete / non-clean"):
        raise witness.EvidenceError(
            "Tricritical incomplete execution mode is dishonest"
        )
    if (
        completeness["execution_mode"] == "non-independent / degraded"
        and not ensemble["limitations"]
    ):
        raise witness.EvidenceError(
            "degraded review must preserve an isolation limitation"
        )
    missing_executions = sorted(
        expected_missing
        + expected_failed
        + expected_unusable
        + expected_budget_exhausted
    )
    if incomplete:
        if any(
            cycle[field] is not None
            for field in (
                "feedback",
                "adjudication_dispatch",
                "adjudication",
                "revision",
                "verification",
            )
        ):
            raise witness.EvidenceError("incomplete review must stop later phases")
        causes = _finding_causes(findings)
        recurring_causes = {
            key: cause for key, cause in causes.items() if key in seen_causes
        }
        _seam_choices(
            cycle["seam_choices"],
            subject,
            recurring_causes,
            trust_snapshot,
            index,
        )
        controls = _cycle_state(cycle, authority, None, index)
        return (
            subject,
            None,
            {
                "review_projection": review_projection,
                "ensemble": ensemble,
                "items": {},
                "verification": None,
                "outcomes": outcomes,
                "limitations": sorted(report_limitations),
                "missing_executions": missing_executions,
                "unresolved": len(findings),
                "revision": None,
                "causes": causes,
                "cycle_owner": cycle["owner"],
                "controls": controls,
                "gate": "incomplete",
                "authority_available": authority is not None,
            },
        )
    if cycle["feedback"] is None:
        raise witness.EvidenceError(
            "complete review lacks external-feedback observation"
        )
    findings.update(
        _feedback(
            cycle["feedback"],
            subject,
            report_hashes,
            ensemble_raw,
            trust_snapshot,
            reviewer_roles,
        )
    )
    causes = _finding_causes(findings)
    finding_refs = sorted(findings)
    feedback_raw = witness.canonical_bytes(cycle["feedback"]) + b"\n"
    adjudication_subject = _role_subject(
        "tricritical-adjudication-subject-v1",
        {
            "subject": subject,
            "findings_sha256": witness.digest(finding_refs),
            "ensemble_sha256": _raw_sha(ensemble_raw),
            "feedback_sha256": _raw_sha(feedback_raw),
        },
    )
    if cycle["adjudication_dispatch"] is None or cycle["adjudication"] is None:
        raise witness.EvidenceError("complete review lacks independent adjudication")
    adjudication_document = cycle["adjudication"]
    adjudication_envelope, adjudication_projection = _dispatch(
        cycle["adjudication_dispatch"],
        adjudication_subject,
        cycle["adjudication_dispatch"]["bundle_sha256"],
        trust_snapshot,
        f"cycle {index} adjudication dispatch",
    )
    del adjudication_envelope
    _claim_dispatch_isolation(
        adjudication_projection, seen, f"cycle {index} adjudication"
    )
    adjudicators = [
        item
        for item in adjudication_projection["executions"].values()
        if item["role"] == "adjudicator"
    ]
    if len(adjudication_projection["executions"]) != 1 or len(adjudicators) != 1:
        raise witness.EvidenceError(
            "Tricritical adjudication must be independently dispatched"
        )
    adjudicator = adjudicators[0]
    if adjudicator.get("usable") is not True:
        raise witness.EvidenceError("Tricritical adjudication result is unusable")
    items, adjudication_limitations = _adjudication(
        adjudication_document,
        subject,
        findings,
        adjudicator["execution_id"],
        adjudicator["returned"],
        witness.digest(finding_refs),
    )
    accepted = {ref for ref, item in items.items() if item["disposition"] == "accept"}
    accepted_causes = _finding_causes(
        {finding_ref: findings[finding_ref] for finding_ref in accepted}
    )
    recurring_causes = {
        key: cause for key, cause in causes.items() if key in seen_causes
    }
    seam_choices = _seam_choices(
        cycle["seam_choices"],
        subject,
        recurring_causes,
        trust_snapshot,
        index,
    )
    _require_confirm_for_future_accepts(findings, items, seam_choices)
    gate_dispositions = {item["disposition"] for item in items.values()}
    terminal_dispositions = gate_dispositions & {
        "needs operator decision",
        "blocked",
    }
    if terminal_dispositions:
        if cycle["revision"] is not None or cycle["verification"] is not None:
            raise witness.EvidenceError(
                "terminal disposition requires revision and verification null"
            )
        revision = None
        verification = None
    else:
        revision = _revision(
            cycle["revision"],
            subject,
            accepted,
            authority,
            increment["document"],
        )
        if revision is not None:
            revision["fresh_roles_required"] = {
                findings[finding_ref]["reviewer_scope"]
                for finding_ref in accepted
            }
        if revision is not None or accepted:
            if cycle["verification"] is not None:
                raise witness.EvidenceError(
                    "non-occurring terminal verification must be null"
                )
            verification = None
        else:
            if cycle["verification"] is None:
                raise witness.EvidenceError(
                    "terminal review lacks declared verification"
                )
            verification = _verification(
                cycle["verification"],
                subject,
                trust_snapshot,
                f"cycle {index} verification",
            )
    _enforce_seam_outcomes(
        seam_choices,
        findings,
        items,
        revision,
        increment["document"],
    )
    controls = _cycle_state(cycle, authority, revision, index)
    limitations = sorted(set(ensemble["limitations"]) | set(adjudication_limitations))
    unresolved = sum(
        item["disposition"] in {"accept", "needs operator decision", "blocked"}
        for item in items.values()
    )
    return (
        subject,
        None if revision is None else revision["successor"],
        {
            "review_projection": review_projection,
            "ensemble": ensemble,
            "items": items,
            "verification": verification,
            "outcomes": outcomes,
            "limitations": limitations,
            "missing_executions": missing_executions,
            "unresolved": unresolved,
            "revision": revision,
            "causes": accepted_causes,
            "cycle_owner": cycle["owner"],
            "controls": controls,
            "gate": "complete",
            "authority_available": authority is not None,
        },
    )


def _derived_terminal(final: dict[str, Any]) -> dict[str, Any]:
    items = final["items"]
    dispositions = {item["disposition"] for item in items.values()}
    verification = final["verification"]
    if final["gate"] == "incomplete":
        state, owner = "incomplete / non-clean", "reviewer"
    elif "needs operator decision" in dispositions:
        state, owner = "needs operator decision", "operator"
    elif "blocked" in dispositions:
        state, owner = "blocked", "blocker"
    elif "accept" in dispositions:
        state, owner = (
            "blocked",
            "reviser" if final["authority_available"] else "operator",
        )
    elif verification is None:
        raise _witness().EvidenceError("Tricritical terminal verification is absent")
    elif (
        verification["status"] == "unavailable" or verification["unchanged"] is not True
    ):
        state, owner = "blocked", "verifier"
    elif verification["status"] == "failed":
        state, owner = "failed_verification", "verifier"
    elif verification["status"] != "passed":
        raise _witness().EvidenceError("Tricritical terminal verification is invalid")
    elif (
        final["ensemble"]["completeness"]["execution_mode"]
        == "non-independent / degraded"
        or final["limitations"]
    ):
        state, owner = "clean / degraded", "none"
    else:
        state, owner = "clean", "none"
    return {
        "state": state,
        "owner": owner,
        "limitations": final["limitations"],
        "missing_executions": final["missing_executions"],
        "unresolved_actionable_findings": final["unresolved"],
        "verification": verification,
    }


def _validate_bundle(bundle: Any, *, trust_snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return Tricritical's canonical terminal projection."""

    witness = _witness()
    manifest, manifest_raw = bundle.read_json(
        "manifest.json", "Tricritical terminal review manifest"
    )
    manifest = witness.document(
        manifest,
        {
            "producer",
            "initial_subject",
            "terminal_subject",
            "mutation_authority",
            "cycles",
            "terminal",
        },
        "Tricritical terminal review manifest",
        BUNDLE_CONTRACT,
    )
    witness.producer(
        manifest["producer"], trust_snapshot, "Tricritical terminal review producer"
    )
    initial_subject = _subject(manifest["initial_subject"], "initial subject")
    terminal_subject = _subject(manifest["terminal_subject"], "terminal subject")
    authority = _mutation_authority(
        manifest["mutation_authority"], initial_subject, trust_snapshot
    )
    if not isinstance(manifest["cycles"], list) or not manifest["cycles"]:
        raise witness.EvidenceError("Tricritical terminal review requires a cycle")
    prior_subject = initial_subject
    first_cycle = manifest["cycles"][0]
    if not isinstance(first_cycle, dict) or "increment" not in first_cycle:
        raise witness.EvidenceError("Tricritical initial increment is absent")
    expected_increment = first_cycle["increment"]
    final: dict[str, Any] | None = None
    seen = {"executions": set(), "sessions": set(), "contexts": set()}
    scope_history: list[dict[str, Any]] = []
    seen_causes: dict[str, dict[str, Any]] = {}
    required_fresh_roles: set[str] = set()
    seen_candidates = {witness.digest(initial_subject["candidate"])}
    for index, cycle in enumerate(manifest["cycles"]):
        cycle_subject, successor, final = _cycle(
            cycle,
            prior_subject,
            expected_increment,
            trust_snapshot,
            authority,
            seen,
            scope_history,
            seen_causes,
            required_fresh_roles,
            index,
        )
        expected_cycle_owner = (
            "reviser"
            if final["revision"] is not None
            else _derived_terminal(final)["owner"]
        )
        if final["cycle_owner"] != expected_cycle_owner:
            raise witness.EvidenceError(f"cycle {index} owner is dishonest")
        seen_causes.update(final["causes"])
        if cycle_subject != prior_subject:
            raise witness.EvidenceError("Tricritical cycle subject chain is invalid")
        if successor is not None:
            if index == len(manifest["cycles"]) - 1:
                raise witness.EvidenceError(
                    "Tricritical revision lacks fresh successor review"
                )
            candidate_digest = witness.digest(successor["candidate"])
            if candidate_digest in seen_candidates:
                raise witness.EvidenceError("Tricritical revision repeats a candidate")
            seen_candidates.add(candidate_digest)
            prior_subject = successor
            expected_increment = final["revision"]["successor_increment"]
            required_fresh_roles = set(
                final["revision"]["fresh_roles_required"]
            )
        elif index != len(manifest["cycles"]) - 1:
            raise witness.EvidenceError(
                "Tricritical non-revision cycle cannot continue"
            )
    if prior_subject != terminal_subject or final is None:
        raise witness.EvidenceError("Tricritical terminal subject chain is invalid")
    if bundle.names != {"manifest.json"}:
        raise witness.EvidenceError("Tricritical bundle has missing or extra files")
    terminal = manifest["terminal"]
    terminal = witness.exact(
        terminal,
        {
            "state",
            "owner",
            "limitations",
            "missing_executions",
            "unresolved_actionable_findings",
            "verification",
        },
        "Tricritical terminal",
    )
    if terminal["state"] not in TERMINALS:
        raise witness.EvidenceError("Tricritical terminal state is invalid")
    limitations = _text_list(terminal["limitations"], "terminal limitations")
    _token_list(terminal["missing_executions"], "terminal missing executions")
    if (
        type(terminal["unresolved_actionable_findings"]) is not int
        or terminal["unresolved_actionable_findings"] < 0
    ):
        raise witness.EvidenceError("terminal unresolved finding count is invalid")
    witness.token(terminal["owner"], "terminal owner")
    if limitations != sorted(limitations):
        raise witness.EvidenceError("terminal limitations must be sorted")
    expected_terminal = _derived_terminal(final)
    if terminal != expected_terminal:
        raise witness.EvidenceError(
            "Tricritical terminal state is not derived from evidence"
        )
    if expected_terminal["state"] in {"clean", "clean / degraded"}:
        expected_progress = "fixed-point"
    else:
        expected_progress = "stopped"
    if final["controls"]["progress"]["status"] != expected_progress:
        raise witness.EvidenceError("Tricritical final cycle progress is dishonest")
    completeness = final["ensemble"]["completeness"]
    clean = terminal["state"] == "clean"
    if clean and (
        completeness["execution_mode"] != "independent"
        or any(
            completeness[field]
            for field in ("missing", "failed", "unusable", "budget_exhausted")
        )
        or terminal["owner"] != "none"
        or terminal["limitations"]
        or terminal["missing_executions"]
        or terminal["unresolved_actionable_findings"] != 0
        or terminal["verification"]["status"] != "passed"
        or terminal["verification"]["unchanged"] is not True
        or any(
            item["disposition"] in {"accept", "needs operator decision", "blocked"}
            for item in final["items"].values()
        )
    ):
        raise witness.EvidenceError("Tricritical terminal is not bare clean")
    projection = {
        "schema_version": 1,
        "contract": PROJECTION_CONTRACT,
        "evidence_contract": BUNDLE_CONTRACT,
        "manifest_sha256": _raw_sha(manifest_raw),
        "subject": terminal_subject,
        "review_profile": {
            "contract": PROFILE_CONTRACT,
            "execution_mode": completeness["execution_mode"],
            "required_axes": final["ensemble"]["selected_axes"],
            "selected_specialists": final["ensemble"]["selected_specialists"],
        },
        "final_dispatch": final["review_projection"],
        "terminal": terminal,
    }
    return {**projection, "content_sha256": witness.digest(projection)}
