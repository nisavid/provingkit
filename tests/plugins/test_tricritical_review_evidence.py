from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path
from typing import Any, ClassVar

REPOSITORY = Path(__file__).resolve().parents[2]
PROVIDER = REPOSITORY / "plugins" / "tricritical" / "task-witness-provider.json"
VALIDATOR = (
    REPOSITORY
    / "plugins"
    / "tricritical"
    / "skills"
    / "loop"
    / "scripts"
    / "review_evidence.py"
)


def canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def raw_document(value: object) -> bytes:
    return canonical(value) + b"\n"


def sha(value: bytes | str) -> str:
    return hashlib.sha256(
        value.encode() if isinstance(value, str) else value
    ).hexdigest()


def signed(value: dict[str, Any]) -> dict[str, Any]:
    return {**value, "content_sha256": sha(canonical(value))}


def identity(kind: str, value: str) -> dict[str, str]:
    return {"kind": kind, "value": value, "content_sha256": sha(value)}


def validator_identity(
    contract: str, entrypoint: str, modules: list[tuple[str, str]]
) -> str:
    return sha(
        canonical(
            {
                "contract": "task-witness-validator-artifact-manifest-v1",
                "validator_contract": contract,
                "entrypoint_module": entrypoint,
                "modules": [
                    {"name": name, "content_sha256": digest} for name, digest in modules
                ],
            }
        )
    )


class EvidenceError(ValueError):
    pass


class Witness:
    EvidenceError = EvidenceError
    canonical_bytes = staticmethod(canonical)
    digest = staticmethod(lambda value: sha(canonical(value)))
    dispatches: ClassVar[dict[str, dict[str, Any]]] = {}

    @staticmethod
    def absolute(path: Path, label: str) -> Path:
        if not path.is_absolute() or ".." in path.parts:
            raise EvidenceError(f"{label} must be absolute and traversal-free")
        return path

    @staticmethod
    def exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
        if not isinstance(value, dict) or set(value) != keys:
            raise EvidenceError(f"{label} schema drift")
        return value

    @staticmethod
    def text(value: Any, label: str) -> str:
        if not isinstance(value, str) or not value:
            raise EvidenceError(f"{label} must be a non-empty string")
        return value

    @classmethod
    def token(cls, value: Any, label: str) -> str:
        value = cls.text(value, label)
        if not value[0].islower() or any(
            not (character.islower() or character.isdigit() or character == "-")
            for character in value
        ):
            raise EvidenceError(f"{label} is not a closed token")
        return value

    @classmethod
    def sha(cls, value: Any, label: str) -> str:
        value = cls.text(value, label)
        if len(value) != 64 or any(
            character not in "0123456789abcdef" for character in value
        ):
            raise EvidenceError(f"{label} must be a SHA-256 digest")
        return value

    @classmethod
    def identity(
        cls, value: Any, label: str, *, absent: bool = False
    ) -> dict[str, Any]:
        if absent and value == {"kind": "absent"}:
            return value
        value = cls.exact(value, {"kind", "value", "content_sha256"}, label)
        cls.text(value["kind"], f"{label}.kind")
        cls.text(value["value"], f"{label}.value")
        cls.sha(value["content_sha256"], f"{label}.content_sha256")
        return value

    @classmethod
    def document(
        cls,
        value: Any,
        keys: set[str],
        label: str,
        contract: str,
    ) -> dict[str, Any]:
        value = cls.exact(
            value,
            keys | {"schema_version", "contract", "content_sha256"},
            label,
        )
        unsigned = {key: item for key, item in value.items() if key != "content_sha256"}
        if (
            type(value["schema_version"]) is not int
            or value["schema_version"] != 1
            or value["contract"] != contract
            or value["content_sha256"] != cls.digest(unsigned)
        ):
            raise EvidenceError(f"{label} contract mismatch")
        return value

    @classmethod
    def producer(
        cls, value: Any, snapshot: dict[str, Any], label: str
    ) -> dict[str, Any]:
        value = cls.exact(
            value, {"producer_id", "contract", "implementation_sha256"}, label
        )
        if value != snapshot["producer"]:
            raise EvidenceError(
                f"{label} is not accepted by the operator trust context"
            )
        return {
            **value,
            "validator_id": "tricritical-terminal-review-evidence-validator-v2",
            "validator_contract": "tricritical-terminal-review-evidence-v2",
            "validator_implementation_sha256": "f" * 64,
        }

    @classmethod
    def issuer(
        cls,
        value: Any,
        snapshot: dict[str, Any],
        label: str,
        capability: str,
    ) -> dict[str, Any]:
        value = cls.exact(
            value, {"issuer_id", "contract", "implementation_sha256"}, label
        )
        entry = next(
            (item for item in snapshot["issuers"] if item["identity"] == value), None
        )
        if entry is None or capability not in entry["capabilities"]:
            raise EvidenceError(f"{label} is not authorized for {capability}")
        return value

    @classmethod
    def invoke_registered_validator(
        cls, path: Path, _snapshot: dict[str, Any]
    ) -> dict[str, Any]:
        try:
            return copy.deepcopy(cls.dispatches[str(path)])
        except KeyError as error:
            raise EvidenceError(
                "Rolecasting dispatch bundle is unregistered"
            ) from error


class Bundle:
    def __init__(self, manifest: dict[str, Any]) -> None:
        self.files = {"manifest.json": raw_document(manifest)}

    @property
    def names(self) -> set[str]:
        return set(self.files)

    def read_json(self, name: str, label: str) -> tuple[dict[str, Any], bytes]:
        try:
            raw = self.files[name]
        except KeyError as error:
            raise EvidenceError(f"{label} is absent") from error
        value = json.loads(raw)
        if raw != raw_document(value):
            raise EvidenceError(f"{label} is not canonical")
        return value, raw


def load_validator() -> Any:
    specification = importlib.util.spec_from_file_location(
        "registered_tricritical_validator", VALIDATOR
    )
    if specification is None or specification.loader is None:
        raise AssertionError("Tricritical validator could not be loaded")
    module = importlib.util.module_from_spec(specification)
    module.__dict__.update({"_TASK_WITNESS": Witness, "_VERIFIED_MODULES": {}})
    specification.loader.exec_module(module)
    return module


class TricriticalReviewEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = load_validator()
        self.producer = {
            "producer_id": "tricritical-review-loop-v2",
            "contract": "tricritical-terminal-review-evidence-v2",
            "implementation_sha256": "1" * 64,
        }
        self.issuer = {
            "issuer_id": "tricritical-native-review-adapter-v1",
            "contract": "tricritical-native-review-adapter-v1",
            "implementation_sha256": "2" * 64,
        }
        self.trust = {
            "producer": self.producer,
            "issuers": [
                {
                    "identity": self.issuer,
                    "capabilities": ["feedback-observation", "terminal-verification"],
                }
            ],
        }
        self.candidate = identity("git-commit", "a" * 40)
        self.increment = self.current_increment()
        self.subject = {
            "candidate": self.candidate,
            "review_input": self.increment_identity(self.increment),
            "requirements": identity("review-requirements-v1", "requirements"),
        }

    def reviewer_scope(self, role: str) -> dict[str, Any]:
        return {
            "role": role,
            "scope": identity("review-scope-v1", role),
            "dependencies": [identity("review-dependencies-v1", role)],
        }

    def current_increment(
        self, roles: list[str] | None = None, *, label: str = "current"
    ) -> dict[str, Any]:
        roles = (
            ["critic-intent", "critic-runtime", "critic-structure"]
            if roles is None
            else roles
        )
        return signed(
            {
                "schema_version": 1,
                "contract": "tricritical-current-increment-v1",
                "authorized_outcome": identity(
                    "authorized-outcome-v1", f"{label}-outcome"
                ),
                "claims": [identity("increment-claim-v1", f"{label}-claim")],
                "supported_inputs": [identity("supported-input-v1", f"{label}-input")],
                "acceptance_criteria": [
                    identity("acceptance-criterion-v1", f"{label}-acceptance")
                ],
                "reviewer_scopes": [
                    self.reviewer_scope(role) for role in sorted(roles)
                ],
            }
        )

    @staticmethod
    def increment_identity(increment: dict[str, Any]) -> dict[str, str]:
        digest = sha(canonical(increment))
        return {
            "kind": "tricritical-current-increment-v1",
            "value": digest,
            "content_sha256": digest,
        }

    def role_subject(self, kind: str, payload: object) -> dict[str, str]:
        digest = sha(canonical(payload))
        return {"kind": kind, "value": digest, "content_sha256": digest}

    def store_manifest(self, bundle: Bundle, manifest: dict[str, Any]) -> None:
        bundle.files["manifest.json"] = raw_document(
            signed(
                {
                    key: value
                    for key, value in manifest.items()
                    if key != "content_sha256"
                }
            )
        )

    def terminal(
        self,
        state: str,
        owner: str,
        *,
        limitations: list[str] | None = None,
        missing: list[str] | None = None,
        unresolved: int = 0,
        verification: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "state": state,
            "owner": owner,
            "limitations": [] if limitations is None else limitations,
            "missing_executions": [] if missing is None else missing,
            "unresolved_actionable_findings": unresolved,
            "verification": verification,
        }

    def finding(
        self,
        finding_id: str,
        *,
        cause: str | None = None,
        reviewer_scope: str = "critic-intent",
        contract_relation: str = "current-contract-contradiction",
        material_current_risk: bool = True,
        current_dependency: bool = True,
    ) -> dict[str, Any]:
        return {
            "finding_id": finding_id,
            "kind": "contract-defect",
            "cause": identity("finding-cause-v1", cause or finding_id),
            "reviewer_scope": reviewer_scope,
            "contract_relation": contract_relation,
            "material_current_risk": material_current_risk,
            "current_dependency": current_dependency,
            "evidence": [identity("finding-evidence-v1", finding_id)],
            "affected_contract": "review contract",
            "causal_path": "candidate to observable behavior",
            "impact": "incorrect behavior",
            "severity": "major",
            "direction": "correct the candidate",
            "proof_required": "targeted verification",
            "limitations": [],
            "residual_risk": "bounded",
        }

    def rebind_complete_cycle(
        self,
        bundle: Bundle,
        dispositions: list[str],
        *,
        cycle_index: int = 0,
        findings: list[dict[str, Any]] | None = None,
        report_limitations: list[str] | None = None,
        adjudication_limitations: list[str] | None = None,
        execution_mode: str | None = None,
    ) -> tuple[dict[str, Any], list[str]]:
        report_limitations = [] if report_limitations is None else report_limitations
        adjudication_limitations = (
            [] if adjudication_limitations is None else adjudication_limitations
        )
        manifest = json.loads(bundle.files["manifest.json"])
        cycle = manifest["cycles"][cycle_index]
        report_id = min(cycle["reports"])
        report = cycle["reports"][report_id]
        findings = (
            [
                self.finding(
                    f"finding-{index}",
                    contract_relation=(
                        "stronger-future-guarantee"
                        if disposition == "follow-up outside scope"
                        else "current-contract-contradiction"
                    ),
                    material_current_risk=disposition != "follow-up outside scope",
                    current_dependency=disposition != "follow-up outside scope",
                )
                for index, disposition in enumerate(dispositions)
            ]
            if findings is None
            else findings
        )
        self.assertEqual(len(findings), len(dispositions))
        report["findings"] = findings
        report["limitations"] = report_limitations
        report = signed(
            {key: value for key, value in report.items() if key != "content_sha256"}
        )
        cycle["reports"][report_id] = report

        review = Witness.dispatches[cycle["review_dispatch"]["path"]]
        review_projection = review["projection"]
        execution = review_projection["executions"][report_id]
        execution["returned"]["content_sha256"] = sha(raw_document(report))
        review["projection"] = signed(
            {
                key: value
                for key, value in review_projection.items()
                if key != "content_sha256"
            }
        )
        review_projection = review["projection"]

        report_hashes = {
            execution_id: sha(raw_document(value))
            for execution_id, value in cycle["reports"].items()
        }
        ensemble = cycle["ensemble"]
        ensemble["reports"] = report_hashes
        ensemble["dispatch_projection_sha256"] = sha(canonical(review_projection))
        ensemble["limitations"] = report_limitations
        if execution_mode is not None:
            ensemble["completeness"]["execution_mode"] = execution_mode
        cycle["ensemble"] = signed(
            {key: value for key, value in ensemble.items() if key != "content_sha256"}
        )

        feedback = cycle["feedback"]
        feedback["freeze"]["reports_sha256"] = sha(canonical(report_hashes))
        feedback["freeze"]["ensemble_sha256"] = sha(raw_document(cycle["ensemble"]))
        cycle["feedback"] = signed(
            {key: value for key, value in feedback.items() if key != "content_sha256"}
        )

        source = f"{report_id}:{execution['result_sha256']}"
        finding_refs = [
            f"{source}:{finding['finding_id']}:{sha(canonical(finding))}"
            for finding in findings
        ]
        adjudication = cycle["adjudication"]
        adjudication["findings_sha256"] = sha(canonical(sorted(finding_refs)))
        adjudication["items"] = [
            {
                "finding_ref": finding_ref,
                "disposition": disposition,
                "evidence": [identity("adjudication-evidence-v1", str(index))],
                "next_owner": {
                    "accept": "reviser",
                    "reject": "none",
                    "already addressed": "none",
                    "stale": "none",
                    "duplicate": "none",
                    "needs operator decision": "operator",
                    "blocked": "blocker",
                    "follow-up outside scope": "follow-up",
                }[disposition],
            }
            for index, (finding_ref, disposition) in enumerate(
                zip(finding_refs, dispositions, strict=True)
            )
        ]
        adjudication["limitations"] = adjudication_limitations
        cycle["adjudication"] = signed(
            {
                key: value
                for key, value in adjudication.items()
                if key != "content_sha256"
            }
        )
        adjudication_dispatch = Witness.dispatches[
            cycle["adjudication_dispatch"]["path"]
        ]
        adjudication_projection = adjudication_dispatch["projection"]
        adjudicator = next(iter(adjudication_projection["executions"].values()))
        adjudicator["returned"]["content_sha256"] = sha(
            raw_document(cycle["adjudication"])
        )
        adjudication_projection["subject"] = self.role_subject(
            "tricritical-adjudication-subject-v1",
            {
                "subject": cycle["subject"],
                "findings_sha256": adjudication["findings_sha256"],
                "ensemble_sha256": sha(raw_document(cycle["ensemble"])),
                "feedback_sha256": sha(raw_document(cycle["feedback"])),
            },
        )
        adjudication_dispatch["projection"] = signed(
            {
                key: value
                for key, value in adjudication_projection.items()
                if key != "content_sha256"
            }
        )
        self.store_manifest(bundle, manifest)
        return manifest, finding_refs

    def resign_adjudication(
        self,
        bundle: Bundle,
        manifest: dict[str, Any],
        cycle_index: int = 0,
    ) -> None:
        cycle = manifest["cycles"][cycle_index]
        adjudication = cycle["adjudication"]
        cycle["adjudication"] = signed(
            {
                key: value
                for key, value in adjudication.items()
                if key != "content_sha256"
            }
        )
        envelope = Witness.dispatches[cycle["adjudication_dispatch"]["path"]]
        projection = envelope["projection"]
        adjudicator = next(iter(projection["executions"].values()))
        adjudicator["returned"]["content_sha256"] = sha(
            raw_document(cycle["adjudication"])
        )
        envelope["projection"] = signed(
            {key: value for key, value in projection.items() if key != "content_sha256"}
        )
        self.store_manifest(bundle, manifest)

    def revision_bundle(
        self,
        dispositions: list[str] | None = None,
        *,
        adapted_increment: dict[str, Any] | None = None,
    ) -> tuple[Bundle, dict[str, Any]]:
        dispositions = ["accept"] if dispositions is None else dispositions
        self.trust["issuers"][0]["capabilities"].append("mutation-authority")
        successor_increment = (
            self.increment if adapted_increment is None else adapted_increment
        )
        successor = {
            "candidate": identity("git-commit", "c" * 40),
            "review_input": self.increment_identity(successor_increment),
            "requirements": self.subject["requirements"],
        }
        first_bundle, _ = self.clean_bundle(path_tag="-cycle-0")
        first_manifest, finding_refs = self.rebind_complete_cycle(
            first_bundle, dispositions
        )
        accepted_refs = [
            finding_ref
            for finding_ref, disposition in zip(finding_refs, dispositions, strict=True)
            if disposition == "accept"
        ]
        second_bundle, _ = self.clean_bundle(
            subject=successor,
            increment=successor_increment,
            path_tag="-cycle-1",
        )
        second_manifest = json.loads(second_bundle.files["manifest.json"])
        authority = signed(
            {
                "schema_version": 1,
                "contract": "tricritical-mutation-authority-v1",
                "issuer": self.issuer,
                "subject": self.subject,
                "authority": identity("authority-scope-v1", "bounded-edit"),
                "scope": identity("mutation-scope-v1", "accepted-findings-only"),
                "declared_verification": identity(
                    "verification-contract-v1", "targeted"
                ),
            }
        )
        first = first_manifest["cycles"][0]
        first["revision"] = signed(
            {
                "schema_version": 1,
                "contract": "tricritical-revision-v1",
                "subject": self.subject,
                "accepted_findings": accepted_refs,
                "mutation_authority_sha256": sha(raw_document(authority)),
                "pre_edit_candidate": self.subject["candidate"],
                "successor_subject": successor,
                "deletion_alternatives": ["retain only the required behavior"],
                "resolution_evidence": {
                    finding_ref: [identity("revision-evidence-v1", f"resolved-{index}")]
                    for index, finding_ref in enumerate(accepted_refs)
                },
                "verification": {
                    "status": "passed",
                    "before_candidate": self.subject["candidate"],
                    "after_candidate": successor["candidate"],
                    "evidence": identity("revision-verification-v1", "passed"),
                },
                "fresh_review_required": True,
                "clarified_requirements": None,
                "adapted_increment": adapted_increment,
            }
        )
        first["verification"] = None
        first["progress"] = {
            "status": "progressed",
            "evidence": [identity("material-progress-v1", "successor-c")],
        }
        first["mutation_authority"] = {
            "available": True,
            "receipt_sha256": sha(raw_document(authority)),
        }
        first["owner"] = "reviser"
        second = second_manifest["cycles"][0]
        second["mutation_authority"] = {
            "available": True,
            "receipt_sha256": sha(raw_document(authority)),
        }
        manifest = signed(
            {
                "schema_version": 1,
                "contract": "tricritical-terminal-review-evidence-v2",
                "producer": self.producer,
                "initial_subject": self.subject,
                "terminal_subject": successor,
                "mutation_authority": authority,
                "cycles": [first, second],
                "terminal": second_manifest["terminal"],
            }
        )
        return Bundle(manifest), successor

    def rolecasting(
        self,
        path: str,
        subject: dict[str, str],
        roles: list[str],
        returned: dict[str, dict[str, str]],
        *,
        candidate: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        candidate = self.candidate if candidate is None else candidate
        executions = {}
        for index, role in enumerate(roles):
            execution_id = f"{path.rsplit('/', 1)[-1]}-{index}"
            executions[execution_id] = {
                "execution_id": execution_id,
                "role": role,
                "target": {
                    "product_family": "codex",
                    "surface": "chatgpt-codex",
                    "executor": "codex",
                    "version": "2026.08.13",
                },
                "topology": {
                    "relationship": "child",
                    "ownership": "leader-owned",
                    "transport": "native-tool",
                },
                "candidate": candidate,
                "scope": identity("review-scope-v1", role),
                "request": identity("review-request-v1", role),
                "return_contract": returned[role]["kind"],
                "verification_contract": "review-verification-v1",
                "stop_contract": "review-stop-v1",
                "authority": {
                    "access": "read-only",
                    "subdelegation": False,
                    "external_action": False,
                    "evidence": identity("dispatch-authority-v1", role),
                },
                "user_authority": None,
                "isolation": {
                    "session": f"session-{path}-{index}",
                    "context": f"context-{path}-{index}",
                    "enforceable": True,
                },
                "assurance": {
                    "target": "product-attested",
                    "model": "product-attested",
                    "topology": "product-attested",
                    "authority": "product-attested",
                    "execution_result": "product-attested",
                    "evidence": identity("product-attestation-v1", role),
                },
                "assurance_minimum": {
                    "target": "product-attested",
                    "model": "product-attested",
                    "topology": "product-attested",
                    "authority": "product-attested",
                    "execution_result": "product-attested",
                },
                "dispatch_sha256": f"{index + 1:x}" * 64,
                "model": "gpt-5.6-sol",
                "reasoning_effort": "high",
                "model_sha256": f"{index + 5:x}" * 64,
                "result_sha256": f"{index + 9:x}" * 64,
                "usable": True,
                "model_issuer": identity("issuer-v1", f"model-{path}-{role}"),
                "result_issuer": identity("issuer-v1", f"result-{path}-{role}"),
                "returned": returned[role],
                "verification": identity("review-verification-v1", role),
                "stop": identity("review-stop-v1", role),
            }
        projection = signed(
            {
                "schema_version": 1,
                "contract": "rolecasting-dispatch-projection-v2",
                "evidence_contract": "rolecasting-dispatch-evidence-v2",
                "manifest_sha256": "3" * 64,
                "plan_sha256": "4" * 64,
                "subject": subject,
                "producer": {
                    "producer_id": "rolecasting-bootstrap-dispatch-v2",
                    "contract": "rolecasting-dispatch-evidence-v2",
                    "implementation_sha256": "5" * 64,
                },
                "executions": executions,
            }
        )
        bundle_sha256 = sha(path)
        envelope = {
            "contract": "task-witness-canonical-projection-v2",
            "bundle_sha256": bundle_sha256,
            "producer": {
                **projection["producer"],
                "validator_id": "rolecasting-dispatch-evidence-validator-v2",
                "validator_contract": "rolecasting-dispatch-evidence-v2",
                "validator_implementation_sha256": "6" * 64,
            },
            "validator": {
                "validator_id": "rolecasting-dispatch-evidence-validator-v2",
                "contract": "rolecasting-dispatch-evidence-v2",
                "implementation_sha256": "6" * 64,
            },
            "projection": projection,
        }
        Witness.dispatches[path] = envelope
        return envelope

    def clean_bundle(
        self,
        *,
        subject: dict[str, Any] | None = None,
        increment: dict[str, Any] | None = None,
        path_tag: str = "",
    ) -> tuple[Bundle, dict[str, Any]]:
        subject = self.subject if subject is None else subject
        increment = self.increment if increment is None else increment
        self.assertEqual(subject["review_input"], self.increment_identity(increment))
        candidate = subject["candidate"]
        review_path = f"/evidence/review{path_tag}"
        review_name = review_path.rsplit("/", 1)[-1]
        adjudication_path = f"/evidence/adjudication{path_tag}"
        adjudication_name = adjudication_path.rsplit("/", 1)[-1]
        reports: dict[str, dict[str, Any]] = {}
        returned: dict[str, dict[str, str]] = {}
        roles = [item["role"] for item in increment["reviewer_scopes"]]
        for index, role in enumerate(roles):
            execution_id = f"{review_name}-{index}"
            report = signed(
                {
                    "schema_version": 1,
                    "contract": "tricritical-raw-report-v1",
                    "subject": subject,
                    "execution_id": execution_id,
                    "findings": [],
                    "falsification_attempts": [f"{role} found no counterexample"],
                    "outcome": {"status": "complete", "usable": True, "failure": None},
                    "limitations": [],
                }
            )
            reports[execution_id] = report
            returned[role] = {
                "kind": "tricritical-raw-report-v1",
                "value": execution_id,
                "content_sha256": sha(raw_document(report)),
            }
        review_subject = self.role_subject("tricritical-review-subject-v1", subject)
        review = self.rolecasting(
            review_path, review_subject, roles, returned, candidate=candidate
        )
        report_hashes = {
            execution_id: sha(raw_document(report))
            for execution_id, report in reports.items()
        }
        ensemble = signed(
            {
                "schema_version": 1,
                "contract": "tricritical-ensemble-v1",
                "subject": subject,
                "dispatch_bundle_sha256": review["bundle_sha256"],
                "dispatch_projection_sha256": sha(canonical(review["projection"])),
                "reports": report_hashes,
                "risk": {
                    "rationale": "bounded review",
                    "selected_axes": sorted(
                        role.removeprefix("critic-")
                        for role in roles
                        if role.startswith("critic-")
                    ),
                    "selected_specialists": sorted(
                        role.removeprefix("specialist-")
                        for role in roles
                        if role.startswith("specialist-")
                    ),
                    "waived_specialists": [],
                },
                "completeness": {
                    "execution_mode": "independent",
                    "missing": [],
                    "failed": [],
                    "unusable": [],
                    "budget_exhausted": [],
                },
                "causal_synthesis": [],
                "limitations": [],
            }
        )
        feedback = signed(
            {
                "schema_version": 1,
                "contract": "tricritical-external-feedback-v1",
                "issuer": self.issuer,
                "subject": subject,
                "freeze": {
                    "reports_sha256": sha(canonical(report_hashes)),
                    "ensemble_sha256": sha(raw_document(ensemble)),
                    "sequence": 1,
                },
                "acquisition": {"sequence": 2, "forge_state": "pre-forge"},
                "state": "not-applicable-pre-forge",
                "source": None,
                "findings": [],
                "reason": "pre-forge",
            }
        )
        adjudication = signed(
            {
                "schema_version": 1,
                "contract": "tricritical-adjudication-v1",
                "subject": subject,
                "execution_id": f"{adjudication_name}-0",
                "findings_sha256": sha(canonical([])),
                "items": [],
                "causal_groups": [],
                "disagreements": [],
                "limitations": [],
            }
        )
        adjudication_subject = self.role_subject(
            "tricritical-adjudication-subject-v1",
            {
                "subject": subject,
                "findings_sha256": adjudication["findings_sha256"],
                "ensemble_sha256": sha(raw_document(ensemble)),
                "feedback_sha256": sha(raw_document(feedback)),
            },
        )
        adjudication_dispatch = self.rolecasting(
            adjudication_path,
            adjudication_subject,
            ["adjudicator"],
            {
                "adjudicator": {
                    "kind": "tricritical-adjudication-v1",
                    "value": f"{adjudication_name}-0",
                    "content_sha256": sha(raw_document(adjudication)),
                }
            },
        )
        verification = {
            "issuer": self.issuer,
            "status": "passed",
            "candidate": candidate,
            "evidence": identity("verification-evidence-v1", "clean"),
            "unchanged": True,
        }
        terminal = {
            "state": "clean",
            "owner": "none",
            "limitations": [],
            "missing_executions": [],
            "unresolved_actionable_findings": 0,
            "verification": {
                key: verification[key]
                for key in ("status", "candidate", "evidence", "unchanged")
            },
        }
        manifest = signed(
            {
                "schema_version": 1,
                "contract": "tricritical-terminal-review-evidence-v2",
                "producer": self.producer,
                "initial_subject": subject,
                "terminal_subject": subject,
                "mutation_authority": None,
                "cycles": [
                    {
                        "subject": subject,
                        "increment": increment,
                        "review_dispatch": {
                            "path": review_path,
                            "bundle_sha256": review["bundle_sha256"],
                        },
                        "reports": reports,
                        "ensemble": ensemble,
                        "feedback": feedback,
                        "adjudication_dispatch": {
                            "path": adjudication_path,
                            "bundle_sha256": adjudication_dispatch["bundle_sha256"],
                        },
                        "adjudication": adjudication,
                        "revision": None,
                        "verification": verification,
                        "retained_scopes": [],
                        "seam_choices": [],
                        "progress": {"status": "fixed-point", "evidence": []},
                        "mutation_authority": {
                            "available": False,
                            "receipt_sha256": None,
                        },
                        "owner": "none",
                    }
                ],
                "terminal": terminal,
            }
        )
        expected = signed(
            {
                "schema_version": 1,
                "contract": "tricritical-terminal-review-projection-v2",
                "evidence_contract": "tricritical-terminal-review-evidence-v2",
                "manifest_sha256": sha(raw_document(manifest)),
                "subject": subject,
                "review_profile": {
                    "contract": "tricritical-review-profile-v1",
                    "execution_mode": "independent",
                    "required_axes": ["intent", "runtime", "structure"],
                    "selected_specialists": [],
                },
                "final_dispatch": review["projection"],
                "terminal": terminal,
            }
        )
        return Bundle(manifest), expected

    def rewrite_review_assurance(
        self,
        bundle: Bundle,
        level: str,
    ) -> dict[str, Any]:
        manifest = json.loads(bundle.files["manifest.json"])
        cycle = manifest["cycles"][0]
        review_envelope = Witness.dispatches[cycle["review_dispatch"]["path"]]
        review_projection = review_envelope["projection"]
        for execution_id, execution in review_projection["executions"].items():
            execution["assurance"] = {
                "target": level,
                "model": level,
                "topology": level,
                "authority": level,
                "execution_result": level,
                "evidence": identity(
                    "dispatch-assurance-v2", f"{level}-{execution_id}"
                ),
            }
            execution["assurance_minimum"] = {
                field: level
                for field in (
                    "target",
                    "model",
                    "topology",
                    "authority",
                    "execution_result",
                )
            }
        review_projection = signed(
            {
                key: value
                for key, value in review_projection.items()
                if key != "content_sha256"
            }
        )
        review_envelope["projection"] = review_projection
        ensemble = cycle["ensemble"]
        ensemble["dispatch_projection_sha256"] = sha(canonical(review_projection))
        cycle["ensemble"] = signed(
            {key: value for key, value in ensemble.items() if key != "content_sha256"}
        )
        feedback = cycle["feedback"]
        feedback["freeze"]["ensemble_sha256"] = sha(raw_document(cycle["ensemble"]))
        cycle["feedback"] = signed(
            {key: value for key, value in feedback.items() if key != "content_sha256"}
        )
        adjudication_path = cycle["adjudication_dispatch"]["path"]
        adjudication_envelope = Witness.dispatches[adjudication_path]
        adjudication_projection = adjudication_envelope["projection"]
        adjudication_projection["subject"] = self.role_subject(
            "tricritical-adjudication-subject-v1",
            {
                "subject": cycle["subject"],
                "findings_sha256": sha(canonical([])),
                "ensemble_sha256": sha(raw_document(cycle["ensemble"])),
                "feedback_sha256": sha(raw_document(cycle["feedback"])),
            },
        )
        adjudication_envelope["projection"] = signed(
            {
                key: value
                for key, value in adjudication_projection.items()
                if key != "content_sha256"
            }
        )
        self.store_manifest(bundle, manifest)
        return review_projection

    def refresh_empty_complete_cycle(
        self, bundle: Bundle, manifest: dict[str, Any], cycle_index: int
    ) -> None:
        cycle = manifest["cycles"][cycle_index]
        review = Witness.dispatches[cycle["review_dispatch"]["path"]]
        review["projection"] = signed(
            {
                key: value
                for key, value in review["projection"].items()
                if key != "content_sha256"
            }
        )
        report_hashes = {
            execution_id: sha(raw_document(report))
            for execution_id, report in cycle["reports"].items()
        }
        ensemble = cycle["ensemble"]
        ensemble["dispatch_projection_sha256"] = sha(canonical(review["projection"]))
        ensemble["reports"] = report_hashes
        cycle["ensemble"] = signed(
            {key: value for key, value in ensemble.items() if key != "content_sha256"}
        )
        feedback = cycle["feedback"]
        feedback["freeze"]["reports_sha256"] = sha(canonical(report_hashes))
        feedback["freeze"]["ensemble_sha256"] = sha(raw_document(cycle["ensemble"]))
        cycle["feedback"] = signed(
            {key: value for key, value in feedback.items() if key != "content_sha256"}
        )
        adjudication = Witness.dispatches[cycle["adjudication_dispatch"]["path"]]
        projection = adjudication["projection"]
        projection["subject"] = self.role_subject(
            "tricritical-adjudication-subject-v1",
            {
                "subject": cycle["subject"],
                "findings_sha256": sha(canonical([])),
                "ensemble_sha256": sha(raw_document(cycle["ensemble"])),
                "feedback_sha256": sha(raw_document(cycle["feedback"])),
            },
        )
        adjudication["projection"] = signed(
            {key: value for key, value in projection.items() if key != "content_sha256"}
        )
        self.store_manifest(bundle, manifest)

    def retained_scope(
        self,
        manifest: dict[str, Any],
        source_cycle_index: int,
        role: str,
    ) -> dict[str, Any]:
        source_cycle = manifest["cycles"][source_cycle_index]
        scope = next(
            item
            for item in source_cycle["increment"]["reviewer_scopes"]
            if item["role"] == role
        )
        projection = Witness.dispatches[source_cycle["review_dispatch"]["path"]][
            "projection"
        ]
        execution = next(
            item for item in projection["executions"].values() if item["role"] == role
        )
        report = source_cycle["reports"][execution["execution_id"]]
        target_subject = manifest["cycles"][source_cycle_index + 1]["subject"]
        unchanged_proof = signed(
            {
                "schema_version": 1,
                "contract": "tricritical-unchanged-scope-proof-v1",
                "source_subject": source_cycle["subject"],
                "target_subject": target_subject,
                "role": role,
                "scope": scope["scope"],
                "dependencies": scope["dependencies"],
                "evidence": [identity("unchanged-scope-evidence-v1", role)],
            }
        )
        return signed(
            {
                "schema_version": 1,
                "contract": "tricritical-retained-scope-v1",
                "role": role,
                "scope": scope["scope"],
                "dependencies": scope["dependencies"],
                "source_subject": source_cycle["subject"],
                "prior_report": {
                    "kind": "tricritical-raw-report-v1",
                    "value": execution["execution_id"],
                    "content_sha256": sha(raw_document(report)),
                },
                "unchanged_proof": unchanged_proof,
            }
        )

    def retain_successor_scope(self, bundle: Bundle, role: str) -> dict[str, Any]:
        manifest = json.loads(bundle.files["manifest.json"])
        second = manifest["cycles"][1]
        retained = self.retained_scope(manifest, 0, role)
        review = Witness.dispatches[second["review_dispatch"]["path"]]
        execution_id = next(
            execution_id
            for execution_id, execution in review["projection"]["executions"].items()
            if execution["role"] == role
        )
        del review["projection"]["executions"][execution_id]
        del second["reports"][execution_id]
        second["retained_scopes"] = [retained]
        self.refresh_empty_complete_cycle(bundle, manifest, 1)
        return manifest

    def test_bare_clean_requires_fresh_complete_independent_review_and_adjudication(
        self,
    ) -> None:
        bundle, expected = self.clean_bundle()

        projection = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(projection, expected)

    def test_current_increment_is_signed_cycle_bound_and_role_unique(self) -> None:
        attacks: dict[str, Any] = {
            "stale-signature": lambda manifest: manifest["cycles"][0][
                "increment"
            ].update({"claims": [identity("increment-claim-v1", "changed")]}),
            "wrong-review-input": lambda manifest: manifest["cycles"][0][
                "subject"
            ].update({"review_input": identity("review-input-v1", "wrong")}),
            "duplicate-role": lambda manifest: manifest["cycles"][0]["increment"][
                "reviewer_scopes"
            ].append(
                copy.deepcopy(manifest["cycles"][0]["increment"]["reviewer_scopes"][0])
            ),
        }
        for name, mutate in attacks.items():
            with self.subTest(attack=name):
                bundle, _ = self.clean_bundle(path_tag=f"-increment-{name}")
                manifest = json.loads(bundle.files["manifest.json"])
                mutate(manifest)
                self.store_manifest(bundle, manifest)

                with self.assertRaises(EvidenceError):
                    self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def test_legacy_tranche_and_extension_contracts_are_absent(self) -> None:
        self.assertFalse(hasattr(self.validator, "DEFAULT_TRANCHES"))
        self.assertFalse(hasattr(self.validator, "OPERATOR_CHOICE_CONTRACT"))
        self.assertFalse(hasattr(self.validator, "EXTENSION_ELIGIBILITY_CONTRACT"))
        self.assertFalse(hasattr(self.validator, "_validate_budget_chain"))
        bundle, _ = self.clean_bundle(path_tag="-legacy-controls")
        manifest = json.loads(bundle.files["manifest.json"])
        manifest["cycles"][0]["budget"] = {"used": 0}
        manifest["cycles"][0]["extension"] = None
        self.store_manifest(bundle, manifest)

        with self.assertRaisesRegex(EvidenceError, "schema drift"):
            self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def test_controller_observed_dispatch_is_preserved_without_assurance_laundering(
        self,
    ) -> None:
        bundle, _ = self.clean_bundle(path_tag="-controller-observed")
        expected_dispatch = self.rewrite_review_assurance(bundle, "controller-observed")

        projection = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(projection["final_dispatch"], expected_dispatch)
        self.assertEqual(
            {
                execution["assurance"]["execution_result"]
                for execution in projection["final_dispatch"]["executions"].values()
            },
            {"controller-observed"},
        )
        self.assertEqual(
            {
                minimum
                for execution in projection["final_dispatch"]["executions"].values()
                for minimum in execution["assurance_minimum"].values()
            },
            {"controller-observed"},
        )

    def test_owner_accepts_every_registered_rolecasting_assurance_tier(self) -> None:
        for level in ("product-attested", "controller-observed", "self-reported"):
            with self.subTest(level=level):
                bundle, _ = self.clean_bundle(path_tag=f"-{level}")
                expected_dispatch = self.rewrite_review_assurance(bundle, level)

                projection = self.validator._validate_bundle(
                    bundle, trust_snapshot=self.trust
                )

                self.assertEqual(projection["final_dispatch"], expected_dispatch)

    def test_provider_registers_only_the_exact_v2_owner_validator(self) -> None:
        source = VALIDATOR.read_bytes()
        source_sha256 = sha(source)
        expected = signed(
            {
                "schema_version": 1,
                "contract": "task-witness-provider-declaration-v1",
                "plugin_id": "tricritical",
                "publisher": "nisavid",
                "repository": "https://github.com/nisavid/provingkit",
                "authority_profile": "tricritical-cooperative-review-v1",
                "producers": [],
                "issuers": [],
                "validators": [
                    {
                        "validator_id": (
                            "tricritical-terminal-review-evidence-validator-v2"
                        ),
                        "contract": "tricritical-terminal-review-evidence-v2",
                        "implementation_sha256": validator_identity(
                            "tricritical-terminal-review-evidence-v2",
                            "validator",
                            [("validator", source_sha256)],
                        ),
                        "entrypoint": "validator",
                        "modules": [
                            {
                                "name": "validator",
                                "relative_path": (
                                    "skills/loop/scripts/review_evidence.py"
                                ),
                                "length": len(source),
                                "sha256": source_sha256,
                            }
                        ],
                        "lifecycle": {
                            "state": "active",
                            "usable_for_new_publication": True,
                        },
                    }
                ],
            }
        )

        self.assertEqual(json.loads(PROVIDER.read_bytes()), expected)

    def test_owner_accepts_alternate_model_because_model_policy_is_rolecasting_owned(
        self,
    ) -> None:
        bundle, expected = self.clean_bundle(path_tag="-alternate-model")
        manifest = json.loads(bundle.files["manifest.json"])
        for dispatch_key in ("review_dispatch", "adjudication_dispatch"):
            path = manifest["cycles"][0][dispatch_key]["path"]
            envelope = Witness.dispatches[path]
            projection = envelope["projection"]
            for execution in projection["executions"].values():
                execution["model"] = "registered-alternate-model"
                execution["reasoning_effort"] = "medium"
            envelope["projection"] = signed(
                {
                    key: value
                    for key, value in projection.items()
                    if key != "content_sha256"
                }
            )
        review = Witness.dispatches[manifest["cycles"][0]["review_dispatch"]["path"]]
        ensemble = manifest["cycles"][0]["ensemble"]
        ensemble["dispatch_projection_sha256"] = sha(canonical(review["projection"]))
        manifest["cycles"][0]["ensemble"] = signed(
            {key: value for key, value in ensemble.items() if key != "content_sha256"}
        )
        feedback = manifest["cycles"][0]["feedback"]
        feedback["freeze"]["ensemble_sha256"] = sha(
            raw_document(manifest["cycles"][0]["ensemble"])
        )
        manifest["cycles"][0]["feedback"] = signed(
            {key: value for key, value in feedback.items() if key != "content_sha256"}
        )
        adjudication_path = manifest["cycles"][0]["adjudication_dispatch"]["path"]
        adjudication_envelope = Witness.dispatches[adjudication_path]
        adjudication_projection = adjudication_envelope["projection"]
        adjudication_projection["subject"] = self.role_subject(
            "tricritical-adjudication-subject-v1",
            {
                "subject": manifest["cycles"][0]["subject"],
                "findings_sha256": sha(canonical([])),
                "ensemble_sha256": sha(raw_document(manifest["cycles"][0]["ensemble"])),
                "feedback_sha256": sha(raw_document(manifest["cycles"][0]["feedback"])),
            },
        )
        adjudication_envelope["projection"] = signed(
            {
                key: value
                for key, value in adjudication_projection.items()
                if key != "content_sha256"
            }
        )
        self.store_manifest(bundle, manifest)
        expected["final_dispatch"] = review["projection"]
        expected["manifest_sha256"] = sha(bundle.files["manifest.json"])
        expected = signed(
            {key: value for key, value in expected.items() if key != "content_sha256"}
        )

        projection = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(projection, expected)

    def test_unusable_execution_is_preserved_as_incomplete_without_later_phases(
        self,
    ) -> None:
        bundle, _ = self.clean_bundle()
        manifest = json.loads(bundle.files["manifest.json"])
        cycle = manifest["cycles"][0]
        execution_id = "review-1"
        report = cycle["reports"][execution_id]
        report["outcome"] = {
            "status": "unusable",
            "usable": False,
            "failure": identity("execution-failure-v1", "unusable-runtime-report"),
        }
        report["limitations"] = ["runtime report was unusable"]
        report = signed(
            {key: value for key, value in report.items() if key != "content_sha256"}
        )
        cycle["reports"][execution_id] = report
        review = Witness.dispatches["/evidence/review"]
        review["projection"]["executions"][execution_id]["usable"] = False
        review["projection"]["executions"][execution_id]["returned"][
            "content_sha256"
        ] = sha(raw_document(report))
        review_projection = review["projection"]
        review_projection["content_sha256"] = sha(
            canonical(
                {
                    key: value
                    for key, value in review_projection.items()
                    if key != "content_sha256"
                }
            )
        )
        ensemble = cycle["ensemble"]
        ensemble["reports"][execution_id] = sha(raw_document(report))
        ensemble["limitations"] = ["runtime report was unusable"]
        ensemble["completeness"]["execution_mode"] = "incomplete / non-clean"
        ensemble["completeness"]["unusable"] = [execution_id]
        ensemble["dispatch_projection_sha256"] = sha(canonical(review_projection))
        cycle["ensemble"] = signed(
            {key: value for key, value in ensemble.items() if key != "content_sha256"}
        )
        cycle["feedback"] = None
        cycle["adjudication_dispatch"] = None
        cycle["adjudication"] = None
        cycle["revision"] = None
        cycle["verification"] = None
        cycle["progress"] = {"status": "stopped", "evidence": []}
        cycle["owner"] = "reviewer"
        terminal = {
            "state": "incomplete / non-clean",
            "owner": "reviewer",
            "limitations": ["runtime report was unusable"],
            "missing_executions": [execution_id],
            "unresolved_actionable_findings": 0,
            "verification": None,
        }
        manifest["terminal"] = terminal
        bundle.files["manifest.json"] = raw_document(
            signed(
                {
                    key: value
                    for key, value in manifest.items()
                    if key != "content_sha256"
                }
            )
        )

        projection = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(projection["terminal"], terminal)

    def test_missing_selected_axis_is_preserved_as_incomplete(self) -> None:
        bundle, _ = self.clean_bundle(path_tag="-missing-axis")
        manifest = json.loads(bundle.files["manifest.json"])
        cycle = manifest["cycles"][0]
        review = Witness.dispatches[cycle["review_dispatch"]["path"]]
        projection = review["projection"]
        missing_id = next(
            execution_id
            for execution_id, execution in projection["executions"].items()
            if execution["role"] == "critic-runtime"
        )
        del projection["executions"][missing_id]
        review["projection"] = signed(
            {key: value for key, value in projection.items() if key != "content_sha256"}
        )
        del cycle["reports"][missing_id]
        ensemble = cycle["ensemble"]
        del ensemble["reports"][missing_id]
        ensemble["dispatch_projection_sha256"] = sha(canonical(review["projection"]))
        ensemble["completeness"] = {
            "execution_mode": "incomplete / non-clean",
            "missing": ["critic-runtime"],
            "failed": [],
            "unusable": [],
            "budget_exhausted": [],
        }
        cycle["ensemble"] = signed(
            {key: value for key, value in ensemble.items() if key != "content_sha256"}
        )
        for field in (
            "feedback",
            "adjudication_dispatch",
            "adjudication",
            "revision",
            "verification",
        ):
            cycle[field] = None
        cycle["progress"] = {"status": "stopped", "evidence": []}
        cycle["owner"] = "reviewer"
        expected = self.terminal(
            "incomplete / non-clean", "reviewer", missing=["critic-runtime"]
        )
        manifest["terminal"] = expected
        self.store_manifest(bundle, manifest)

        result = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(result["terminal"], expected)

    def test_clean_degraded_aggregates_report_ensemble_and_adjudication_limits(
        self,
    ) -> None:
        bundle, _ = self.clean_bundle(path_tag="-degraded")
        manifest, _ = self.rebind_complete_cycle(
            bundle,
            [],
            report_limitations=["critic isolation unavailable"],
            adjudication_limitations=["adjudicator evidence was bounded"],
            execution_mode="non-independent / degraded",
        )
        cycle = manifest["cycles"][0]
        verification = {
            key: cycle["verification"][key]
            for key in ("status", "candidate", "evidence", "unchanged")
        }
        expected = self.terminal(
            "clean / degraded",
            "none",
            limitations=[
                "adjudicator evidence was bounded",
                "critic isolation unavailable",
            ],
            verification=verification,
        )
        manifest["terminal"] = expected
        self.store_manifest(bundle, manifest)

        projection = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(projection["terminal"], expected)

    def test_failed_verification_is_derived_with_verifier_owner(self) -> None:
        bundle, _ = self.clean_bundle(path_tag="-failed")
        manifest = json.loads(bundle.files["manifest.json"])
        cycle = manifest["cycles"][0]
        cycle["verification"]["status"] = "failed"
        cycle["progress"] = {"status": "stopped", "evidence": []}
        cycle["owner"] = "verifier"
        verification = {
            key: cycle["verification"][key]
            for key in ("status", "candidate", "evidence", "unchanged")
        }
        expected = self.terminal(
            "failed_verification", "verifier", verification=verification
        )
        manifest["terminal"] = expected
        self.store_manifest(bundle, manifest)

        projection = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(projection["terminal"], expected)

    def test_candidate_drift_is_blocked_not_failed_verification(self) -> None:
        bundle, _ = self.clean_bundle(path_tag="-drift")
        manifest = json.loads(bundle.files["manifest.json"])
        cycle = manifest["cycles"][0]
        cycle["verification"]["unchanged"] = False
        cycle["progress"] = {"status": "stopped", "evidence": []}
        cycle["owner"] = "verifier"
        verification = {
            key: cycle["verification"][key]
            for key in ("status", "candidate", "evidence", "unchanged")
        }
        expected = self.terminal("blocked", "verifier", verification=verification)
        manifest["terminal"] = expected
        self.store_manifest(bundle, manifest)

        projection = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(projection["terminal"], expected)

    def test_candidate_drift_precedes_declared_verification_failure(self) -> None:
        bundle, _ = self.clean_bundle(path_tag="-drift-failed")
        manifest = json.loads(bundle.files["manifest.json"])
        cycle = manifest["cycles"][0]
        cycle["verification"].update({"status": "failed", "unchanged": False})
        cycle["progress"] = {"status": "stopped", "evidence": []}
        cycle["owner"] = "verifier"
        verification = {
            key: cycle["verification"][key]
            for key in ("status", "candidate", "evidence", "unchanged")
        }
        expected = self.terminal("blocked", "verifier", verification=verification)
        manifest["terminal"] = expected
        self.store_manifest(bundle, manifest)

        projection = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(projection["terminal"], expected)

    def test_all_eight_dispositions_have_closed_owner_and_terminal_semantics(
        self,
    ) -> None:
        cases = {
            "accept": ("blocked", "operator", 1, None),
            "reject": ("clean", "none", 0, "passed"),
            "already addressed": ("clean", "none", 0, "passed"),
            "stale": ("clean", "none", 0, "passed"),
            "duplicate": ("clean", "none", 0, "passed"),
            "needs operator decision": (
                "needs operator decision",
                "operator",
                1,
                None,
            ),
            "blocked": ("blocked", "blocker", 1, None),
            "follow-up outside scope": ("clean", "none", 0, "passed"),
        }
        for index, (disposition, expected_values) in enumerate(cases.items()):
            with self.subTest(disposition=disposition):
                bundle, _ = self.clean_bundle(path_tag=f"-disposition-{index}")
                if disposition == "duplicate":
                    findings = [
                        self.finding("finding-0", cause="shared-duplicate"),
                        self.finding("finding-1", cause="shared-duplicate"),
                    ]
                    manifest, _ = self.rebind_complete_cycle(
                        bundle,
                        ["duplicate", "already addressed"],
                        findings=findings,
                    )
                else:
                    manifest, _ = self.rebind_complete_cycle(bundle, [disposition])
                cycle = manifest["cycles"][0]
                state, owner, unresolved, verification_status = expected_values
                if verification_status is None:
                    cycle["verification"] = None
                    verification = None
                    cycle["progress"] = {"status": "stopped", "evidence": []}
                else:
                    verification = {
                        key: cycle["verification"][key]
                        for key in ("status", "candidate", "evidence", "unchanged")
                    }
                cycle["owner"] = owner
                expected = self.terminal(
                    state,
                    owner,
                    unresolved=unresolved,
                    verification=verification,
                )
                manifest["terminal"] = expected
                self.store_manifest(bundle, manifest)

                projection = self.validator._validate_bundle(
                    bundle, trust_snapshot=self.trust
                )

                self.assertEqual(projection["terminal"], expected)

    def test_every_adjudication_disposition_requires_nonempty_evidence(self) -> None:
        bundle, _ = self.clean_bundle(path_tag="-empty-adjudication-evidence")
        manifest, _ = self.rebind_complete_cycle(bundle, ["reject"])
        manifest["cycles"][0]["adjudication"]["items"][0]["evidence"] = []
        self.resign_adjudication(bundle, manifest)

        with self.assertRaisesRegex(EvidenceError, "evidence must not be empty"):
            self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def test_singleton_duplicate_disposition_is_rejected(self) -> None:
        bundle, _ = self.clean_bundle(path_tag="-singleton-duplicate")
        self.rebind_complete_cycle(bundle, ["duplicate"])

        with self.assertRaisesRegex(
            EvidenceError, "distinct finding with the same cause"
        ):
            self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def test_all_duplicate_cause_group_lacks_a_canonical_disposition(self) -> None:
        bundle, _ = self.clean_bundle(path_tag="-all-duplicate-cause")
        findings = [
            self.finding("duplicate-0", cause="shared-duplicate"),
            self.finding("duplicate-1", cause="shared-duplicate"),
        ]
        self.rebind_complete_cycle(
            bundle,
            ["duplicate", "duplicate"],
            findings=findings,
        )

        with self.assertRaisesRegex(
            EvidenceError, "duplicate cause lacks a canonical disposition"
        ):
            self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def test_raw_report_finding_scope_must_equal_its_producing_role(self) -> None:
        bundle, _ = self.clean_bundle(path_tag="-cross-role-finding")
        finding = self.finding("cross-role", reviewer_scope="critic-runtime")
        self.rebind_complete_cycle(bundle, ["reject"], findings=[finding])

        with self.assertRaisesRegex(EvidenceError, "producing execution role"):
            self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def test_external_feedback_can_name_any_frozen_reviewer_scope(self) -> None:
        bundle, _ = self.clean_bundle(path_tag="-external-scope")
        manifest = json.loads(bundle.files["manifest.json"])
        cycle = manifest["cycles"][0]
        finding = self.finding(
            "external-runtime",
            reviewer_scope="critic-runtime",
            contract_relation="stronger-future-guarantee",
            material_current_risk=False,
            current_dependency=False,
        )
        feedback = cycle["feedback"]
        feedback["acquisition"]["forge_state"] = "forged"
        feedback["state"] = "observed"
        feedback["source"] = identity("forge-feedback-v1", "external-runtime")
        feedback["findings"] = [finding]
        feedback["reason"] = None
        cycle["feedback"] = signed(
            {key: value for key, value in feedback.items() if key != "content_sha256"}
        )
        finding_ref = (
            f"external-feedback:{finding['finding_id']}:{sha(canonical(finding))}"
        )
        adjudication = cycle["adjudication"]
        adjudication["findings_sha256"] = sha(canonical([finding_ref]))
        adjudication["items"] = [
            {
                "finding_ref": finding_ref,
                "disposition": "reject",
                "evidence": [identity("adjudication-evidence-v1", "external")],
                "next_owner": "none",
            }
        ]
        cycle["adjudication"] = signed(
            {
                key: value
                for key, value in adjudication.items()
                if key != "content_sha256"
            }
        )
        envelope = Witness.dispatches[cycle["adjudication_dispatch"]["path"]]
        projection = envelope["projection"]
        adjudicator = next(iter(projection["executions"].values()))
        adjudicator["returned"]["content_sha256"] = sha(
            raw_document(cycle["adjudication"])
        )
        projection["subject"] = self.role_subject(
            "tricritical-adjudication-subject-v1",
            {
                "subject": cycle["subject"],
                "findings_sha256": adjudication["findings_sha256"],
                "ensemble_sha256": sha(raw_document(cycle["ensemble"])),
                "feedback_sha256": sha(raw_document(cycle["feedback"])),
            },
        )
        envelope["projection"] = signed(
            {key: value for key, value in projection.items() if key != "content_sha256"}
        )
        self.store_manifest(bundle, manifest)

        result = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(result["terminal"]["state"], "clean")

    def test_current_contract_risk_or_dependency_cannot_be_deferred_as_follow_up(
        self,
    ) -> None:
        findings = {
            "contradiction": self.finding(
                "finding-0",
                contract_relation="current-contract-contradiction",
                material_current_risk=False,
                current_dependency=False,
            ),
            "material-risk": self.finding(
                "finding-0",
                contract_relation="stronger-future-guarantee",
                material_current_risk=True,
                current_dependency=False,
            ),
            "current-dependency": self.finding(
                "finding-0",
                contract_relation="stronger-future-guarantee",
                material_current_risk=False,
                current_dependency=True,
            ),
        }
        for name, finding in findings.items():
            with self.subTest(blocker=name):
                bundle, _ = self.clean_bundle(path_tag=f"-follow-up-{name}")
                self.rebind_complete_cycle(
                    bundle,
                    ["follow-up outside scope"],
                    findings=[finding],
                )

                with self.assertRaisesRegex(EvidenceError, "cannot be follow-up"):
                    self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def test_needs_operator_decision_precedes_blocked_and_accepted_findings(
        self,
    ) -> None:
        bundle, _ = self.clean_bundle(path_tag="-precedence")
        manifest, _ = self.rebind_complete_cycle(
            bundle, ["accept", "blocked", "needs operator decision"]
        )
        cycle = manifest["cycles"][0]
        cycle["verification"] = None
        cycle["progress"] = {"status": "stopped", "evidence": []}
        cycle["owner"] = "operator"
        expected = self.terminal("needs operator decision", "operator", unresolved=3)
        manifest["terminal"] = expected
        self.store_manifest(bundle, manifest)

        projection = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(projection["terminal"], expected)

    def test_terminal_claim_cannot_override_derived_evidence(self) -> None:
        bundle, _ = self.clean_bundle(path_tag="-dishonest-terminal")
        manifest = json.loads(bundle.files["manifest.json"])
        manifest["terminal"]["state"] = "blocked"
        manifest["terminal"]["owner"] = "verifier"
        self.store_manifest(bundle, manifest)

        with self.assertRaisesRegex(EvidenceError, "not derived from evidence"):
            self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def test_frozen_single_axis_scope_can_finish_bare_clean(self) -> None:
        increment = self.current_increment(["critic-intent"], label="intent-only")
        subject = {
            **self.subject,
            "review_input": self.increment_identity(increment),
        }
        bundle, _ = self.clean_bundle(
            subject=subject,
            increment=increment,
            path_tag="-subset",
        )

        projection = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(projection["review_profile"]["required_axes"], ["intent"])
        self.assertEqual(projection["terminal"]["state"], "clean")

    def test_frozen_specialist_only_scope_can_finish_bare_clean(self) -> None:
        increment = self.current_increment(
            ["specialist-security"], label="security-only"
        )
        subject = {
            **self.subject,
            "review_input": self.increment_identity(increment),
        }
        bundle, _ = self.clean_bundle(
            subject=subject,
            increment=increment,
            path_tag="-specialist-only",
        )

        projection = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(projection["review_profile"]["required_axes"], [])
        self.assertEqual(
            projection["review_profile"]["selected_specialists"], ["security"]
        )
        self.assertEqual(projection["terminal"]["state"], "clean")

    def test_retained_unused_mutation_authority_is_reported_and_clean_can_finish(
        self,
    ) -> None:
        self.trust["issuers"][0]["capabilities"].append("mutation-authority")
        bundle, _ = self.clean_bundle(path_tag="-unused-authority")
        manifest = json.loads(bundle.files["manifest.json"])
        authority = signed(
            {
                "schema_version": 1,
                "contract": "tricritical-mutation-authority-v1",
                "issuer": self.issuer,
                "subject": self.subject,
                "authority": identity("authority-scope-v1", "bounded-edit"),
                "scope": identity("mutation-scope-v1", "review-findings-only"),
                "declared_verification": identity(
                    "verification-contract-v1", "targeted"
                ),
            }
        )
        manifest["mutation_authority"] = authority
        manifest["cycles"][0]["mutation_authority"] = {
            "available": True,
            "receipt_sha256": sha(raw_document(authority)),
        }
        self.store_manifest(bundle, manifest)

        projection = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(projection["terminal"]["state"], "clean")

    def test_accepted_finding_with_retained_authority_waits_for_reviser(self) -> None:
        self.trust["issuers"][0]["capabilities"].append("mutation-authority")
        bundle, _ = self.clean_bundle(path_tag="-accepted-authority")
        manifest, _ = self.rebind_complete_cycle(bundle, ["accept"])
        authority = signed(
            {
                "schema_version": 1,
                "contract": "tricritical-mutation-authority-v1",
                "issuer": self.issuer,
                "subject": self.subject,
                "authority": identity("authority-scope-v1", "bounded-edit"),
                "scope": identity("mutation-scope-v1", "accepted-findings-only"),
                "declared_verification": identity(
                    "verification-contract-v1", "targeted"
                ),
            }
        )
        cycle = manifest["cycles"][0]
        manifest["mutation_authority"] = authority
        cycle["mutation_authority"] = {
            "available": True,
            "receipt_sha256": sha(raw_document(authority)),
        }
        cycle["verification"] = None
        cycle["progress"] = {"status": "stopped", "evidence": []}
        cycle["owner"] = "reviser"
        expected = self.terminal("blocked", "reviser", unresolved=1)
        manifest["terminal"] = expected
        self.store_manifest(bundle, manifest)

        projection = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(projection["terminal"], expected)

    def test_reused_critic_or_adjudicator_isolation_is_rejected(self) -> None:
        bundle, _ = self.clean_bundle(path_tag="-reuse")
        manifest = json.loads(bundle.files["manifest.json"])
        cycle = manifest["cycles"][0]
        review_projection = Witness.dispatches[cycle["review_dispatch"]["path"]][
            "projection"
        ]
        adjudication = Witness.dispatches[cycle["adjudication_dispatch"]["path"]]
        adjudication_projection = adjudication["projection"]
        adjudicator = next(iter(adjudication_projection["executions"].values()))
        critic = next(iter(review_projection["executions"].values()))
        adjudicator["isolation"] = copy.deepcopy(critic["isolation"])
        adjudication["projection"] = signed(
            {
                key: value
                for key, value in adjudication_projection.items()
                if key != "content_sha256"
            }
        )

        with self.assertRaisesRegex(EvidenceError, "reuses execution isolation"):
            self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def test_authority_bound_revision_requires_fresh_successor_review(self) -> None:
        bundle, successor = self.revision_bundle()

        projection = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(projection["subject"], successor)
        self.assertEqual(projection["terminal"]["state"], "clean")
        self.assertEqual(
            projection["final_dispatch"]["subject"],
            self.role_subject("tricritical-review-subject-v1", successor),
        )

    def test_revision_can_adapt_and_refreeze_the_current_increment(self) -> None:
        adapted = self.current_increment(["critic-runtime"], label="adapted")
        bundle, successor = self.revision_bundle(adapted_increment=adapted)

        projection = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(successor["review_input"], self.increment_identity(adapted))
        self.assertEqual(projection["review_profile"]["required_axes"], ["runtime"])
        self.assertEqual(projection["terminal"]["state"], "clean")

    def test_unchanged_scope_can_retain_prior_usable_report_and_proof(self) -> None:
        bundle, _ = self.revision_bundle()
        self.retain_successor_scope(bundle, "critic-runtime")

        projection = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(projection["terminal"]["state"], "clean")
        self.assertEqual(
            {
                execution["role"]
                for execution in projection["final_dispatch"]["executions"].values()
            },
            {"critic-intent", "critic-structure"},
        )

    def test_revision_cannot_retain_scope_that_produced_accepted_finding(self) -> None:
        bundle, _ = self.revision_bundle()
        self.retain_successor_scope(bundle, "critic-intent")

        with self.assertRaisesRegex(
            EvidenceError, "accepted finding scope requires fresh successor review"
        ):
            self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def test_retained_scope_rejects_overlap_changed_dependencies_and_stale_report(
        self,
    ) -> None:
        for name in (
            "fresh-overlap",
            "changed-dependencies",
            "stale-report",
            "opaque-proof",
            "wrong-proof-target",
        ):
            with self.subTest(attack=name):
                bundle, _ = self.revision_bundle()
                before = json.loads(bundle.files["manifest.json"])
                second = before["cycles"][1]
                review = Witness.dispatches[second["review_dispatch"]["path"]]
                execution_id, execution = next(
                    (execution_id, execution)
                    for execution_id, execution in review["projection"][
                        "executions"
                    ].items()
                    if execution["role"] == "critic-runtime"
                )
                fresh_execution = copy.deepcopy(execution)
                fresh_report = copy.deepcopy(second["reports"][execution_id])
                manifest = self.retain_successor_scope(bundle, "critic-runtime")
                retained = manifest["cycles"][1]["retained_scopes"][0]
                if name == "fresh-overlap":
                    review["projection"]["executions"][execution_id] = fresh_execution
                    manifest["cycles"][1]["reports"][execution_id] = fresh_report
                elif name == "changed-dependencies":
                    retained["dependencies"] = [
                        identity("review-dependencies-v1", "changed")
                    ]
                elif name == "stale-report":
                    retained["prior_report"]["content_sha256"] = "f" * 64
                elif name == "opaque-proof":
                    retained["unchanged_proof"] = identity(
                        "tricritical-unchanged-scope-proof-v1", "opaque"
                    )
                else:
                    proof = retained["unchanged_proof"]
                    proof["target_subject"] = self.subject
                    retained["unchanged_proof"] = signed(
                        {
                            key: value
                            for key, value in proof.items()
                            if key != "content_sha256"
                        }
                    )
                retained = manifest["cycles"][1]["retained_scopes"][0]
                manifest["cycles"][1]["retained_scopes"][0] = signed(
                    {
                        key: value
                        for key, value in retained.items()
                        if key != "content_sha256"
                    }
                )
                if name == "fresh-overlap":
                    self.refresh_empty_complete_cycle(bundle, manifest, 1)
                else:
                    self.store_manifest(bundle, manifest)

                with self.assertRaises(EvidenceError):
                    self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def recurring_finding_bundle(self) -> tuple[Bundle, dict[str, Any]]:
        bundle, _ = self.revision_bundle()
        finding = self.finding(
            "successor-finding",
            cause="finding-0",
            contract_relation="stronger-future-guarantee",
            material_current_risk=False,
            current_dependency=False,
        )
        manifest, _ = self.rebind_complete_cycle(
            bundle,
            ["reject"],
            cycle_index=1,
            findings=[finding],
        )
        return bundle, manifest

    def seam_choice(self, subject: dict[str, Any], choice: str) -> dict[str, Any]:
        return signed(
            {
                "schema_version": 1,
                "contract": "tricritical-seam-choice-v1",
                "issuer": self.issuer,
                "subject": subject,
                "cause": identity("finding-cause-v1", "finding-0"),
                "choice": choice,
                "evidence": identity("seam-choice-evidence-v1", choice),
            }
        )

    def adapted_increment_field(self, field: str, label: str) -> dict[str, Any]:
        increment = copy.deepcopy(self.increment)
        kinds = {
            "claims": "increment-claim-v1",
            "supported_inputs": "supported-input-v1",
            "acceptance_criteria": "acceptance-criterion-v1",
        }
        increment[field] = [identity(kinds[field], label)]
        return signed(
            {key: value for key, value in increment.items() if key != "content_sha256"}
        )

    def adapted_authorized_outcome(self, label: str) -> dict[str, Any]:
        increment = copy.deepcopy(self.increment)
        increment["authorized_outcome"] = identity("authorized-outcome-v1", label)
        return signed(
            {key: value for key, value in increment.items() if key != "content_sha256"}
        )

    def recurring_outcome_bundle(
        self,
        choice: str,
        disposition: str,
        *,
        adapted_increment: dict[str, Any] | None,
        contract_relation: str,
        material_current_risk: bool,
        current_dependency: bool,
    ) -> Bundle:
        bundle, _ = self.revision_bundle()
        finding = self.finding(
            "successor-finding",
            cause="finding-0",
            contract_relation=contract_relation,
            material_current_risk=material_current_risk,
            current_dependency=current_dependency,
        )
        manifest, finding_refs = self.rebind_complete_cycle(
            bundle,
            [disposition],
            cycle_index=1,
            findings=[finding],
        )
        cycle = manifest["cycles"][1]
        cycle["seam_choices"] = [self.seam_choice(cycle["subject"], choice)]
        if disposition != "accept":
            self.store_manifest(bundle, manifest)
            return bundle

        authority = manifest["mutation_authority"]
        successor_increment = (
            self.increment if adapted_increment is None else adapted_increment
        )
        successor = {
            "candidate": identity("git-commit", "d" * 40),
            "review_input": self.increment_identity(successor_increment),
            "requirements": cycle["subject"]["requirements"],
        }
        cycle["revision"] = signed(
            {
                "schema_version": 1,
                "contract": "tricritical-revision-v1",
                "subject": cycle["subject"],
                "accepted_findings": finding_refs,
                "mutation_authority_sha256": sha(raw_document(authority)),
                "pre_edit_candidate": cycle["subject"]["candidate"],
                "successor_subject": successor,
                "deletion_alternatives": ["retain only the required behavior"],
                "resolution_evidence": {
                    finding_ref: [
                        identity("revision-evidence-v1", "successor-resolution")
                    ]
                    for finding_ref in finding_refs
                },
                "verification": {
                    "status": "passed",
                    "before_candidate": cycle["subject"]["candidate"],
                    "after_candidate": successor["candidate"],
                    "evidence": identity(
                        "revision-verification-v1", "successor-passed"
                    ),
                },
                "fresh_review_required": True,
                "clarified_requirements": None,
                "adapted_increment": adapted_increment,
            }
        )
        cycle["verification"] = None
        cycle["progress"] = {
            "status": "progressed",
            "evidence": [identity("material-progress-v1", "successor-d")],
        }
        cycle["owner"] = "reviser"
        third_bundle, _ = self.clean_bundle(
            subject=successor,
            increment=successor_increment,
            path_tag=f"-cycle-2-{choice}-{contract_relation}",
        )
        third_manifest = json.loads(third_bundle.files["manifest.json"])
        third = third_manifest["cycles"][0]
        third["mutation_authority"] = {
            "available": True,
            "receipt_sha256": sha(raw_document(authority)),
        }
        manifest["cycles"].append(third)
        manifest["terminal_subject"] = successor
        manifest["terminal"] = third_manifest["terminal"]
        self.store_manifest(bundle, manifest)
        return bundle

    def test_recurring_cause_requires_one_explicit_evidenced_seam_choice(self) -> None:
        bundle, _ = self.recurring_finding_bundle()

        with self.assertRaisesRegex(EvidenceError, "recurring cause"):
            self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def test_rejected_cause_recurrence_does_not_require_seam_choice(self) -> None:
        bundle, _ = self.revision_bundle(["reject", "accept"])
        finding = self.finding(
            "rejected-again",
            cause="finding-0",
            contract_relation="stronger-future-guarantee",
            material_current_risk=False,
            current_dependency=False,
        )
        self.rebind_complete_cycle(
            bundle,
            ["reject"],
            cycle_index=1,
            findings=[finding],
        )

        projection = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(projection["terminal"]["state"], "clean")

    def test_incomplete_cycle_authenticates_choice_without_claiming_its_effect(
        self,
    ) -> None:
        self.trust["issuers"][0]["capabilities"].append("seam-choice")
        bundle, manifest = self.recurring_finding_bundle()
        cycle = manifest["cycles"][1]
        execution_id = min(cycle["reports"])
        report = cycle["reports"][execution_id]
        report["outcome"] = {
            "status": "budget-exhausted",
            "usable": False,
            "failure": identity("review-budget-exhaustion-v1", execution_id),
        }
        report["limitations"] = ["review budget exhausted before adaptation"]
        report = signed(
            {key: value for key, value in report.items() if key != "content_sha256"}
        )
        cycle["reports"][execution_id] = report
        review = Witness.dispatches[cycle["review_dispatch"]["path"]]
        execution = review["projection"]["executions"][execution_id]
        execution["usable"] = False
        execution["returned"]["content_sha256"] = sha(raw_document(report))
        review["projection"] = signed(
            {
                key: value
                for key, value in review["projection"].items()
                if key != "content_sha256"
            }
        )
        ensemble = cycle["ensemble"]
        ensemble["reports"][execution_id] = sha(raw_document(report))
        ensemble["dispatch_projection_sha256"] = sha(canonical(review["projection"]))
        ensemble["limitations"] = ["review budget exhausted before adaptation"]
        ensemble["completeness"]["execution_mode"] = "incomplete / non-clean"
        ensemble["completeness"]["budget_exhausted"] = [execution_id]
        cycle["ensemble"] = signed(
            {key: value for key, value in ensemble.items() if key != "content_sha256"}
        )
        for field in (
            "feedback",
            "adjudication_dispatch",
            "adjudication",
            "revision",
            "verification",
        ):
            cycle[field] = None
        cycle["seam_choices"] = [self.seam_choice(cycle["subject"], "narrow-claim")]
        cycle["progress"] = {"status": "stopped", "evidence": []}
        cycle["owner"] = "reviewer"
        expected = self.terminal(
            "incomplete / non-clean",
            "reviewer",
            limitations=["review budget exhausted before adaptation"],
            missing=[execution_id],
            unresolved=1,
        )
        manifest["terminal"] = expected
        self.store_manifest(bundle, manifest)

        result = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(result["terminal"], expected)

    def test_each_recurring_seam_choice_requires_its_declared_effect(self) -> None:
        self.trust["issuers"][0]["capabilities"].append("seam-choice")
        cases = {
            "narrow-claim": (
                "accept",
                self.adapted_increment_field("claims", "narrowed-claim"),
                "current-contract-contradiction",
                True,
                True,
            ),
            "narrow-supported-input": (
                "accept",
                self.adapted_increment_field(
                    "supported_inputs", "narrowed-supported-input"
                ),
                "current-contract-contradiction",
                True,
                True,
            ),
            "redesign": (
                "accept",
                None,
                "current-contract-contradiction",
                True,
                True,
            ),
            "accept-residual-risk-outside-claim": (
                "follow-up outside scope",
                None,
                "stronger-future-guarantee",
                False,
                False,
            ),
            "confirm-stronger-guarantee": (
                "accept",
                self.adapted_increment_field(
                    "acceptance_criteria", "confirmed-guarantee"
                ),
                "stronger-future-guarantee",
                False,
                False,
            ),
        }
        for choice, case in cases.items():
            with self.subTest(choice=choice):
                disposition, adapted, relation, material, dependency = case
                bundle = self.recurring_outcome_bundle(
                    choice,
                    disposition,
                    adapted_increment=adapted,
                    contract_relation=relation,
                    material_current_risk=material,
                    current_dependency=dependency,
                )

                projection = self.validator._validate_bundle(
                    bundle, trust_snapshot=self.trust
                )

                self.assertEqual(projection["terminal"]["state"], "clean")

    def test_each_recurring_seam_choice_rejects_a_mismatched_effect(self) -> None:
        self.trust["issuers"][0]["capabilities"].append("seam-choice")
        cases = {
            "narrow-claim": (
                "accept",
                self.adapted_increment_field("supported_inputs", "wrong-field"),
                "current-contract-contradiction",
                True,
                True,
            ),
            "narrow-supported-input": (
                "accept",
                self.adapted_increment_field("claims", "wrong-field"),
                "current-contract-contradiction",
                True,
                True,
            ),
            "redesign": (
                "reject",
                None,
                "stronger-future-guarantee",
                False,
                False,
            ),
            "accept-residual-risk-outside-claim": (
                "reject",
                None,
                "stronger-future-guarantee",
                False,
                False,
            ),
            "confirm-stronger-guarantee": (
                "accept",
                self.adapted_authorized_outcome("wrong-confirmation-change"),
                "stronger-future-guarantee",
                False,
                False,
            ),
        }
        for choice, case in cases.items():
            with self.subTest(choice=choice):
                disposition, adapted, relation, material, dependency = case
                bundle = self.recurring_outcome_bundle(
                    choice,
                    disposition,
                    adapted_increment=adapted,
                    contract_relation=relation,
                    material_current_risk=material,
                    current_dependency=dependency,
                )

                with self.assertRaisesRegex(EvidenceError, "seam choice outcome"):
                    self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def test_future_only_finding_cannot_be_accepted_without_confirmed_adaptation(
        self,
    ) -> None:
        for relation in (
            "stronger-future-guarantee",
            "unsupported-input-defense",
            "hypothetical-extension",
        ):
            with self.subTest(relation=relation):
                bundle, _ = self.clean_bundle(path_tag=f"-future-accept-{relation}")
                finding = self.finding(
                    "future-only",
                    contract_relation=relation,
                    material_current_risk=False,
                    current_dependency=False,
                )
                self.rebind_complete_cycle(
                    bundle,
                    ["accept"],
                    findings=[finding],
                )

                with self.assertRaisesRegex(
                    EvidenceError, "future-only finding cannot be accepted"
                ):
                    self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def test_confirmed_adaptation_can_accept_each_future_only_relation(self) -> None:
        self.trust["issuers"][0]["capabilities"].append("seam-choice")
        for relation in (
            "stronger-future-guarantee",
            "unsupported-input-defense",
            "hypothetical-extension",
        ):
            with self.subTest(relation=relation):
                adapted = self.adapted_increment_field(
                    "acceptance_criteria", f"confirmed-{relation}"
                )
                bundle = self.recurring_outcome_bundle(
                    "confirm-stronger-guarantee",
                    "accept",
                    adapted_increment=adapted,
                    contract_relation=relation,
                    material_current_risk=False,
                    current_dependency=False,
                )

                projection = self.validator._validate_bundle(
                    bundle, trust_snapshot=self.trust
                )

                self.assertEqual(projection["terminal"]["state"], "clean")

    def test_recurring_seam_choice_rejects_duplicate_wrong_cause_or_subject(
        self,
    ) -> None:
        self.trust["issuers"][0]["capabilities"].append("seam-choice")
        for name in ("duplicate", "wrong-cause", "wrong-subject"):
            with self.subTest(attack=name):
                bundle, manifest = self.recurring_finding_bundle()
                cycle = manifest["cycles"][1]
                choice = self.seam_choice(cycle["subject"], "redesign")
                cycle["seam_choices"] = [choice]
                if name == "duplicate":
                    cycle["seam_choices"].append(copy.deepcopy(choice))
                elif name == "wrong-cause":
                    choice["cause"] = identity("finding-cause-v1", "other")
                    cycle["seam_choices"][0] = signed(
                        {
                            key: value
                            for key, value in choice.items()
                            if key != "content_sha256"
                        }
                    )
                else:
                    choice["subject"] = self.subject
                    cycle["seam_choices"][0] = signed(
                        {
                            key: value
                            for key, value in choice.items()
                            if key != "content_sha256"
                        }
                    )
                self.store_manifest(bundle, manifest)

                with self.assertRaises(EvidenceError):
                    self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def test_every_revision_cycle_must_preserve_its_derived_reviser_owner(self) -> None:
        bundle, _ = self.revision_bundle()
        manifest = json.loads(bundle.files["manifest.json"])
        manifest["cycles"][0]["owner"] = "none"
        self.store_manifest(bundle, manifest)

        with self.assertRaisesRegex(EvidenceError, "cycle 0 owner is dishonest"):
            self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def test_needs_operator_disposition_cannot_be_laundered_through_revision(
        self,
    ) -> None:
        bundle, _ = self.revision_bundle(["accept", "needs operator decision"])

        with self.assertRaisesRegex(
            EvidenceError,
            "terminal disposition requires revision and verification null",
        ):
            self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def test_blocked_disposition_cannot_be_laundered_through_revision(self) -> None:
        bundle, _ = self.revision_bundle(["accept", "blocked"])

        with self.assertRaisesRegex(
            EvidenceError,
            "terminal disposition requires revision and verification null",
        ):
            self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def test_budget_exhaustion_is_preserved_as_incomplete_raw_report_evidence(
        self,
    ) -> None:
        bundle, _ = self.clean_bundle(path_tag="-budget-exhausted")
        manifest = json.loads(bundle.files["manifest.json"])
        cycle = manifest["cycles"][0]
        execution_id = min(cycle["reports"])
        report = cycle["reports"][execution_id]
        report["findings"] = [self.finding("preserved-at-exhaustion")]
        report["outcome"] = {
            "status": "budget-exhausted",
            "usable": False,
            "failure": identity("review-budget-exhaustion-v1", execution_id),
        }
        report["limitations"] = ["review budget exhausted"]
        report = signed(
            {key: value for key, value in report.items() if key != "content_sha256"}
        )
        cycle["reports"][execution_id] = report
        review = Witness.dispatches[cycle["review_dispatch"]["path"]]
        execution = review["projection"]["executions"][execution_id]
        execution["usable"] = False
        execution["returned"]["content_sha256"] = sha(raw_document(report))
        review["projection"] = signed(
            {
                key: value
                for key, value in review["projection"].items()
                if key != "content_sha256"
            }
        )
        ensemble = cycle["ensemble"]
        ensemble["reports"][execution_id] = sha(raw_document(report))
        ensemble["dispatch_projection_sha256"] = sha(canonical(review["projection"]))
        ensemble["limitations"] = ["review budget exhausted"]
        ensemble["completeness"]["execution_mode"] = "incomplete / non-clean"
        ensemble["completeness"]["budget_exhausted"] = [execution_id]
        cycle["ensemble"] = signed(
            {key: value for key, value in ensemble.items() if key != "content_sha256"}
        )
        for field in (
            "feedback",
            "adjudication_dispatch",
            "adjudication",
            "revision",
            "verification",
        ):
            cycle[field] = None
        cycle["progress"] = {"status": "stopped", "evidence": []}
        cycle["owner"] = "reviewer"
        expected = self.terminal(
            "incomplete / non-clean",
            "reviewer",
            limitations=["review budget exhausted"],
            missing=[execution_id],
            unresolved=1,
        )
        manifest["terminal"] = expected
        self.store_manifest(bundle, manifest)

        projection = self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

        self.assertEqual(projection["terminal"], expected)

    def test_revision_must_cover_every_accepted_finding_exactly(self) -> None:
        bundle, _ = self.revision_bundle()
        manifest = json.loads(bundle.files["manifest.json"])
        revision = manifest["cycles"][0]["revision"]
        revision["accepted_findings"] = []
        manifest["cycles"][0]["revision"] = signed(
            {key: value for key, value in revision.items() if key != "content_sha256"}
        )
        self.store_manifest(bundle, manifest)

        with self.assertRaisesRegex(EvidenceError, "cover accepted findings"):
            self.validator._validate_bundle(bundle, trust_snapshot=self.trust)

    def test_revision_cycle_cannot_reuse_prior_dispatch_isolation(self) -> None:
        bundle, _ = self.revision_bundle()
        manifest = json.loads(bundle.files["manifest.json"])
        first = manifest["cycles"][0]
        second = manifest["cycles"][1]
        first_projection = Witness.dispatches[first["review_dispatch"]["path"]][
            "projection"
        ]
        second_dispatch = Witness.dispatches[second["review_dispatch"]["path"]]
        second_projection = second_dispatch["projection"]
        first_execution = next(iter(first_projection["executions"].values()))
        second_execution = next(iter(second_projection["executions"].values()))
        second_execution["isolation"] = copy.deepcopy(first_execution["isolation"])
        second_dispatch["projection"] = signed(
            {
                key: value
                for key, value in second_projection.items()
                if key != "content_sha256"
            }
        )

        with self.assertRaisesRegex(EvidenceError, "reuses execution isolation"):
            self.validator._validate_bundle(bundle, trust_snapshot=self.trust)


if __name__ == "__main__":
    unittest.main()
