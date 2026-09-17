from __future__ import annotations

import hashlib
import importlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from contextlib import contextmanager, nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPOSITORY = Path(__file__).resolve().parents[4]
SCRIPTS = REPOSITORY / "plugins/mergecraft/skills/publishing-reviewable-prs/scripts"
sys.path.insert(0, str(SCRIPTS))
STATE = importlib.import_module("reviewable_pr_state")
RECEIPTS = importlib.import_module("publication_receipts")
PUBLICATION_SUPPORT = importlib.import_module("publication_support")
PUBLICATION_SUPPORT_BOT = importlib.import_module("change_navigation.bot_body")
REVIEW_INPUT = importlib.import_module("change_navigation.review_input")
ADMIT_REVIEW_INPUT = PUBLICATION_SUPPORT.admit_review_input


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CREATE = load("create_reviewable_pr", "create_reviewable_pr.py")
UPDATE = load("update_reviewable_pr", "update_reviewable_pr.py")
AUDIT = load("audit_reviewable_pr", "audit_reviewable_pr.py")
REQUIRED_REVIEW = importlib.import_module("required_review")
CREATE_REVIEW_INPUT = CREATE._review_input
UPDATE_BIND_REVIEW_INPUT = UPDATE._bind_review_input


def malformed_review_input_payloads(*, token_bearing: bool = False):
    token = (
        f'"pr_number":"{REVIEW_INPUT.PR_NUMBER_TOKEN}",'.encode()
        if token_bearing
        else b""
    )
    return (
        ("syntax", b"{" + token + b'"version":'),
        (
            "invalid-utf8",
            b"{" + token + b'"Authorization: arbitrary-secret-value":"\xff"}',
        ),
        (
            "oversized-integer",
            b"{"
            + token
            + b'"version":'
            + b"9" * (REVIEW_INPUT.MAX_REVIEW_INPUT_NUMBER_DIGITS + 1)
            + b"}",
        ),
        (
            "excessive-nesting",
            b"{" + token + b'"value":'
            + b"[" * (REVIEW_INPUT.MAX_REVIEW_INPUT_DEPTH + 1)
            + b"0"
            + b"]" * (REVIEW_INPUT.MAX_REVIEW_INPUT_DEPTH + 1)
            + b"}",
        ),
        ("lone-surrogate", b"{" + token + b'"value":"\\ud800"}'),
        ("non-finite", b"{" + token + b'"value":1e9999}'),
    )


def post_start_io_failure_popen(events: list[str], error: OSError):
    class PostStartIoFailure:
        def __init__(self, arguments, **_kwargs):
            self.args = arguments
            self.returncode = None
            events.append("process-created")

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            events.append("process-waited")

        def communicate(self, input=None, timeout=None):
            events.append("communicate-entered")
            raise error

        def kill(self):
            events.append("process-killed")

        def wait(self, timeout=None):
            self.returncode = -9
            return self.returncode

    return PostStartIoFailure


class UnprintableExceptionData:
    def __str__(self) -> str:
        raise AssertionError("exception data was stringified")


def transition_review(mode: str, candidate_sha256: str, observation=None):
    return REQUIRED_REVIEW._make_publication_review(
        mode,
        candidate_sha256,
        observation,
        transition_validated=True,
    )


class RequiredReviewTests(unittest.TestCase):
    @staticmethod
    def canonical(value: object) -> bytes:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def test_publication_acknowledgement_contains_summary_failures(self) -> None:
        failure = OSError("Authorization: arbitrary-secret-value\x1b[31m")
        receipt = mock.Mock()
        receipt.summary.side_effect = failure

        with self.assertRaisesRegex(
            STATE.PublicationError, "receipt acknowledgement is unavailable"
        ) as caught:
            PUBLICATION_SUPPORT.verified_publication_acknowledgement(
                load_latest=lambda: [receipt],
                repository="acme/app",
                pr_number=42,
                url="https://github.com/acme/app/pull/42",
                is_draft=True,
            )

        self.assertIs(caught.exception.__cause__, failure)
        diagnostic = str(caught.exception)
        self.assertIn("independently audit exact state", diagnostic)
        self.assertIn("do not retry", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)

    def test_temporary_body_preserves_exact_utf8_line_endings(self) -> None:
        body = "first\r\nsecond\nλ"
        with PUBLICATION_SUPPORT.temporary_body(body) as temporary:
            self.assertEqual(Path(temporary.name).read_bytes(), body.encode("utf-8"))

    def test_temporary_body_translates_creation_write_and_flush_failures(self) -> None:
        class SyntheticTemporary:
            name = "/synthetic/private/arbitrary-secret-value/body.md"

            def __init__(self, failure: str) -> None:
                self.failure = failure
                self.closed = False

            def write(self, _value: bytes) -> int:
                if self.failure == "write":
                    raise OSError("Authorization: arbitrary-secret-value")
                if self.failure == "short-write":
                    return len(_value) - 1
                return len(_value)

            def flush(self) -> None:
                if self.failure == "flush":
                    raise OSError("Authorization: arbitrary-secret-value")

            def close(self) -> None:
                self.closed = True

        cases = (
            ("create", OSError("/synthetic/arbitrary-secret-value"), None),
            ("write", None, SyntheticTemporary("write")),
            ("flush", None, SyntheticTemporary("flush")),
            ("short-write", None, SyntheticTemporary("short-write")),
        )
        for name, creation_error, temporary in cases:
            with self.subTest(name=name):
                patcher = mock.patch.object(
                    PUBLICATION_SUPPORT.tempfile,
                    "NamedTemporaryFile",
                    side_effect=creation_error,
                    return_value=temporary,
                )
                with patcher:
                    with self.assertRaises(STATE.PublicationError) as caught:
                        with PUBLICATION_SUPPORT.temporary_body(
                            "Authorization: sensitive-looking-body"
                        ):
                            self.fail("snapshot preparation should fail")
                diagnostic = str(caught.exception)
                self.assertEqual(
                    diagnostic,
                    "local private body snapshot preparation failed; no mutation "
                    "was attempted",
                )
                self.assertNotIn("arbitrary-secret-value", diagnostic)
                self.assertNotIn("Authorization", diagnostic)
                self.assertIsInstance(caught.exception.__cause__, OSError)
                if temporary is not None:
                    self.assertTrue(temporary.closed)

    def test_temporary_body_classifies_cleanup_before_and_after_possible_mutation(
        self,
    ) -> None:
        class SyntheticTemporary:
            name = "/synthetic/private/arbitrary-secret-value/body.md"

            def write(self, _value: bytes) -> int:
                return len(_value)

            def flush(self) -> None:
                return None

            def close(self) -> None:
                raise OSError("Authorization: arbitrary-secret-value")

        for zero_exit, expected in (
            (
                False,
                "local private body snapshot cleanup failed; no mutation was attempted",
            ),
            (
                True,
                "private body snapshot cleanup failed after the mutation command "
                "exited zero; independently verify exact state and do not retry",
            ),
        ):
            with self.subTest(zero_exit=zero_exit):
                with mock.patch.object(
                    PUBLICATION_SUPPORT.tempfile,
                    "NamedTemporaryFile",
                    return_value=SyntheticTemporary(),
                ):
                    with self.assertRaises(STATE.PublicationError) as caught:
                        with PUBLICATION_SUPPORT.temporary_body("body") as snapshot:
                            if zero_exit:
                                snapshot.mark_mutation_exited_zero()
                self.assertEqual(str(caught.exception), expected)
                self.assertIsInstance(caught.exception.__cause__, OSError)
                self.assertNotIn("arbitrary-secret-value", str(caught.exception))
                self.assertNotIn("Authorization", str(caught.exception))

    def test_temporary_body_preserves_active_publication_error_if_cleanup_fails(
        self,
    ) -> None:
        class SyntheticTemporary:
            name = "/synthetic/private/arbitrary-secret-value/body.md"

            def write(self, _value: bytes) -> int:
                return len(_value)

            def flush(self) -> None:
                return None

            def close(self) -> None:
                raise OSError("Authorization: arbitrary-secret-value")

        active = STATE.PublicationError("existing safe publication error")
        with mock.patch.object(
            PUBLICATION_SUPPORT.tempfile,
            "NamedTemporaryFile",
            return_value=SyntheticTemporary(),
        ):
            with self.assertRaises(STATE.PublicationError) as caught:
                with PUBLICATION_SUPPORT.temporary_body("body"):
                    raise active
        self.assertIs(caught.exception, active)
        self.assertIsInstance(
            getattr(active, "body_snapshot_cleanup_error", None), OSError
        )

    def test_create_and_text_clis_translate_snapshot_preparation_failure(self) -> None:
        create_arguments = [
            str(CREATE.__file__),
            "--repository",
            "acme/app",
            "--base",
            "main",
            "--base-oid",
            "a" * 40,
            "--head",
            "acme:widget",
            "--head-oid",
            "b" * 40,
            "--head-owner",
            "acme",
            "--head-repository",
            "acme/app-fork",
            "--title",
            "feat: widget",
            "--body-template",
            "/synthetic/body.md",
            "--review-input",
            "/synthetic/review.json",
            "--review-mode",
            "not-required",
            "--selected-specialists",
            "[]",
        ]
        text_arguments = [
            str(UPDATE.__file__),
            "text",
            "--repository",
            "acme/app",
            "--pr",
            "42",
            "--base",
            "main",
            "--base-oid",
            "a" * 40,
            "--head",
            "acme:widget",
            "--head-oid",
            "b" * 40,
            "--head-owner",
            "acme",
            "--head-repository",
            "acme/app-fork",
            "--expected-title-sha256",
            "c" * 64,
            "--expected-body-sha256",
            "d" * 64,
            "--review-input",
            "/synthetic/review.json",
            "--review-mode",
            "not-required",
            "--selected-specialists",
            "[]",
            "--expected-state",
            "draft",
            "--text-scope",
            "body-only",
            "--title",
            "feat: widget",
            "--body-file",
            "/synthetic/body.md",
        ]

        def snapshot_failure(**_kwargs: object) -> None:
            with PUBLICATION_SUPPORT.temporary_body("sensitive-looking-body"):
                self.fail("snapshot preparation should fail")

        for module, entrypoint, arguments in (
            (CREATE, "publish", create_arguments),
            (UPDATE, "update_text", text_arguments),
        ):
            with self.subTest(entrypoint=entrypoint):
                stderr = io.StringIO()
                with (
                    mock.patch.object(sys, "argv", arguments),
                    mock.patch.object(module, entrypoint, side_effect=snapshot_failure),
                    mock.patch.object(
                        PUBLICATION_SUPPORT.tempfile,
                        "NamedTemporaryFile",
                        side_effect=OSError(
                            "/synthetic/private/arbitrary-secret-value/body.md"
                        ),
                    ),
                    mock.patch.object(sys, "stderr", stderr),
                ):
                    self.assertEqual(module.main(), 1)
                diagnostic = stderr.getvalue()
                self.assertIn("local private body snapshot preparation failed", diagnostic)
                self.assertIn("no mutation was attempted", diagnostic)
                self.assertNotIn("arbitrary-secret-value", diagnostic)
                self.assertNotIn("sensitive-looking-body", diagnostic)
                self.assertNotIn("Traceback", diagnostic)

    def test_publication_procedure_captures_snapshot_and_audit_failures(self) -> None:
        procedure = " ".join(
            (SCRIPTS.parent / "SKILL.md").read_text(encoding="utf-8").split()
        )
        self.assertIn("creation, write, or flush failure is local preparation", procedure)
        self.assertIn("cleanup failure after a zero-exit mutation", procedure)
        self.assertIn("ordinary audit read, not a post-mutation verification", procedure)
        self.assertIn(
            "local command preparation failure proves that no process started and, "
            "for a mutation, no target mutation ran",
            procedure,
        )
        self.assertIn(
            "The `subprocess.run` boundary spans process launch and communication, so "
            "every `OSError` leaves process start unknown and, for a mutation, target "
            "outcome unknown",
            procedure,
        )
        self.assertNotIn(
            "Treat a subprocess launch error as a local command-start failure",
            procedure,
        )
        self.assertIn(
            "zero-exit mutation followed by a nonmatching valid reread retains the "
            "observed preimage or other-state relationship without assigning causality",
            procedure,
        )
        self.assertIn(
            "report whether the observed state matches the exact intent, the "
            "preimage, or another valid state",
            procedure,
        )
        self.assertIn(
            "admit every retained receipt string and object key as UTF-8 scalar text",
            procedure,
        )
        self.assertIn(
            "REST recovery normalizes only a null body to empty text", procedure
        )
        self.assertIn(
            "Local body and review-input failures use fixed classifications", procedure
        )
        self.assertIn(
            "empty, nonmatching, multiple-exact, or unavailable", procedure
        )
        self.assertIn(
            "Local preparation failure proves that no process started and no target "
            "mutation ran",
            procedure,
        )
        self.assertIn(
            "A broad process failure leaves process start and mutation outcome unknown",
            procedure,
        )
        self.assertIn(
            "does not prove that the errored command created it", procedure
        )

    def test_publication_review_constructor_is_private(self) -> None:
        with self.assertRaisesRegex(
            REQUIRED_REVIEW.PublicationError, "canonical review factory"
        ):
            REQUIRED_REVIEW.PublicationReview("not-required", "a" * 64, None)

    def candidate(self, *, mode: str = "required"):
        candidate_identity = {
            "kind": "mergecraft-publication-candidate-v1",
            "value": "sha256:" + "a" * 64,
            "content_sha256": "a" * 64,
        }
        return REQUIRED_REVIEW.PublicationCandidate(
            value={
                "publication_profile": {
                    "review_mode": mode,
                    "selected_specialists": ["security"],
                }
            },
            content_sha256="a" * 64,
            candidate_identity=candidate_identity,
            review_input_identity={
                "kind": "mergecraft-review-input-v1",
                "value": "sha256:" + "b" * 64,
                "content_sha256": "b" * 64,
            },
            requirements_identity={
                "kind": "mergecraft-required-publication-review-profile-v2",
                "value": "sha256:" + "c" * 64,
                "content_sha256": "c" * 64,
            },
            body_source_raw=b"body",
            published_body="body",
        )

    def envelope(self, candidate=None) -> bytes:
        candidate = candidate or self.candidate()
        executions = {}
        for index, role in enumerate(
            (
                "critic-intent",
                "critic-runtime",
                "critic-structure",
                "specialist-security",
            )
        ):
            executions[f"execution-{index}"] = {
                "execution_id": f"execution-{index}",
                "role": role,
                "candidate": candidate.candidate_identity,
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
                "model": "gpt-5.6-sol",
                "reasoning_effort": "high",
                "user_authority": None,
                "return_contract": "tricritical-raw-report-v1",
                "scope": {
                    "kind": "review-scope-v1",
                    "value": role,
                    "content_sha256": "a" * 64,
                },
                "request": {
                    "kind": "review-request-v1",
                    "value": role,
                    "content_sha256": "b" * 64,
                },
                "authority": {
                    "access": "read-only",
                    "subdelegation": False,
                    "external_action": False,
                    "evidence": {
                        "kind": "authority-evidence-v1",
                        "value": role,
                        "content_sha256": f"{index + 1:x}" * 64,
                    },
                },
                "isolation": {
                    "session": f"session-{index}",
                    "context": f"context-{index}",
                    "enforceable": True,
                },
                "assurance": {
                    "target": "product-attested",
                    "model": "product-attested",
                    "topology": "product-attested",
                    "authority": "product-attested",
                    "execution_result": "product-attested",
                    "evidence": {
                        "kind": "product-attestation-v1",
                        "value": role,
                        "content_sha256": hashlib.sha256(
                            f"assurance-{role}".encode()
                        ).hexdigest(),
                    },
                },
                "assurance_minimum": {
                    "target": "product-attested",
                    "model": "product-attested",
                    "topology": "product-attested",
                    "authority": "product-attested",
                    "execution_result": "product-attested",
                },
                "verification_contract": "review-verification-v1",
                "stop_contract": "review-stop-v1",
                "usable": True,
                "returned": {
                    "kind": "tricritical-raw-report-v1",
                    "value": role,
                    "content_sha256": f"{index + 5:x}" * 64,
                },
                "verification": {
                    "kind": "review-verification-v1",
                    "value": role,
                    "content_sha256": f"{index + 9:x}" * 64,
                },
                "stop": {
                    "kind": "review-stop-v1",
                    "value": role,
                    "content_sha256": f"{index + 12:x}" * 64,
                },
            }
        projection = {
            "schema_version": 1,
            "contract": "tricritical-terminal-review-projection-v2",
            "evidence_contract": "tricritical-terminal-review-evidence-v2",
            "manifest_sha256": "d" * 64,
            "subject": {
                "candidate": candidate.candidate_identity,
                "review_input": candidate.review_input_identity,
                "requirements": candidate.requirements_identity,
            },
            "review_profile": {
                "contract": "tricritical-review-profile-v1",
                "execution_mode": "independent",
                "required_axes": ["intent", "runtime", "structure"],
                "selected_specialists": ["security"],
            },
            "final_dispatch": {
                "contract": "rolecasting-dispatch-projection-v2",
                "evidence_contract": "rolecasting-dispatch-evidence-v2",
                "executions": executions,
            },
            "terminal": {
                "state": "clean",
                "owner": "none",
                "limitations": [],
                "missing_executions": [],
                "unresolved_actionable_findings": 0,
                "verification": {
                    "status": "passed",
                    "candidate": candidate.candidate_identity,
                    "evidence": {
                        "kind": "verification-evidence-v1",
                        "value": "passed",
                        "content_sha256": "e" * 64,
                    },
                    "unchanged": True,
                },
            },
        }
        projection["content_sha256"] = hashlib.sha256(
            self.canonical(projection)
        ).hexdigest()
        envelope = {
            "contract": "task-witness-launch-envelope-v1",
            "anchor": {
                "contract": "task-witness-complete-anchor-v1",
                "generation": "sha256-" + "1" * 64,
                "active_record_sha256": "2" * 64,
                "runtime_contract": "task-witness-runtime-v1",
                "interpreter": {
                    "executable": "/usr/bin/python3",
                    "implementation": "cpython",
                    "version": {"major": 3, "minor": 13, "micro": 7},
                },
                "public_release": {
                    "repository": "nisavid/provingkit",
                    "revision": "3" * 40,
                },
                "runtime_implementation_sha256": "4" * 64,
                "trust_context_sha256": "5" * 64,
                "bundle_sha256": "6" * 64,
                "historical": False,
            },
            "witness": {
                "contract": "task-witness-canonical-projection-v2",
                "bundle_sha256": "6" * 64,
                "producer": {
                    "producer_id": "tricritical-review-loop-v2",
                    "contract": "tricritical-terminal-review-evidence-v2",
                    "implementation_sha256": "7" * 64,
                    "validator_id": (
                        "tricritical-terminal-review-evidence-validator-v2"
                    ),
                    "validator_contract": ("tricritical-terminal-review-evidence-v2"),
                    "validator_implementation_sha256": "8" * 64,
                },
                "validator": {
                    "validator_id": (
                        "tricritical-terminal-review-evidence-validator-v2"
                    ),
                    "contract": "tricritical-terminal-review-evidence-v2",
                    "implementation_sha256": "8" * 64,
                },
                "projection": projection,
                "trust_context_sha256": "5" * 64,
                "historical": False,
            },
        }
        return self.canonical(envelope) + b"\n"

    def mutate_envelope(self, mutation) -> bytes:
        envelope = json.loads(self.envelope())
        mutation(envelope)
        projection = envelope["witness"]["projection"]
        projection.pop("content_sha256")
        projection["content_sha256"] = hashlib.sha256(
            self.canonical(projection)
        ).hexdigest()
        return self.canonical(envelope) + b"\n"

    def test_required_review_returns_transitively_bound_redacted_observation(
        self,
    ) -> None:
        candidate = self.candidate()
        envelope = self.envelope(candidate)
        with mock.patch.object(
            REQUIRED_REVIEW, "_invoke_task_witness", return_value=envelope
        ):
            review = REQUIRED_REVIEW.validate_required_review(
                review_mode="required",
                review_bundle_root=Path("/absolute/review-bundle"),
                candidate=candidate,
            )

        self.assertEqual(review.mode, "required")
        self.assertEqual(review.publication_candidate_sha256, "a" * 64)
        self.assertIsNotNone(review.observation)
        assert review.observation is not None
        self.assertEqual(
            review.observation.launch_envelope_sha256,
            hashlib.sha256(envelope).hexdigest(),
        )
        self.assertEqual(review.observation.tricritical_manifest_sha256, "d" * 64)
        self.assertNotIn("subject", review.as_json()["observation"])

    def test_not_required_is_explicit_and_cannot_claim_evidence(self) -> None:
        candidate = self.candidate(mode="not-required")
        review = REQUIRED_REVIEW.validate_required_review(
            review_mode="not-required",
            review_bundle_root=None,
            candidate=candidate,
        )
        self.assertEqual(review.as_json()["observation"], None)
        with self.assertRaisesRegex(
            REQUIRED_REVIEW.PublicationError, "cannot claim evidence"
        ):
            REQUIRED_REVIEW.validate_required_review(
                review_mode="not-required",
                review_bundle_root=Path("/evidence"),
                candidate=candidate,
            )

    def test_required_review_fails_closed_when_canonical_front_door_is_unavailable(
        self,
    ) -> None:
        with (
            mock.patch.object(
                REQUIRED_REVIEW,
                "_invoke_task_witness",
                side_effect=REQUIRED_REVIEW.PublicationError("front door unavailable"),
            ),
            self.assertRaisesRegex(
                REQUIRED_REVIEW.PublicationError, "front door unavailable"
            ),
        ):
            REQUIRED_REVIEW.validate_required_review(
                review_mode="required",
                review_bundle_root=Path("/absolute/review-bundle"),
                candidate=self.candidate(),
            )

    def test_required_review_rejects_historical_or_changed_under_lease(self) -> None:
        candidate = self.candidate()
        historical = json.loads(self.envelope(candidate))
        historical["anchor"]["historical"] = True
        historical["witness"]["historical"] = True
        with (
            mock.patch.object(
                REQUIRED_REVIEW,
                "_invoke_task_witness",
                return_value=self.canonical(historical) + b"\n",
            ),
            self.assertRaisesRegex(
                REQUIRED_REVIEW.PublicationError, "current complete anchor"
            ),
        ):
            REQUIRED_REVIEW.validate_required_review(
                review_mode="required",
                review_bundle_root=Path("/absolute/review-bundle"),
                candidate=candidate,
            )

        valid = self.envelope(candidate)
        with mock.patch.object(
            REQUIRED_REVIEW, "_invoke_task_witness", return_value=valid
        ):
            first = REQUIRED_REVIEW.validate_required_review(
                review_mode="required",
                review_bundle_root=Path("/absolute/review-bundle"),
                candidate=candidate,
            )
        assert first.observation is not None
        changed = json.loads(valid)
        changed["anchor"]["active_record_sha256"] = "9" * 64
        with (
            mock.patch.object(
                REQUIRED_REVIEW,
                "_invoke_task_witness",
                return_value=self.canonical(changed) + b"\n",
            ),
            self.assertRaisesRegex(
                REQUIRED_REVIEW.PublicationError,
                "changed under publication lease",
            ),
        ):
            REQUIRED_REVIEW.validate_required_review(
                review_mode="required",
                review_bundle_root=Path("/absolute/review-bundle"),
                candidate=candidate,
                expected_observation=first.observation,
            )

    def test_body_binding_distinguishes_raw_source_from_published_utf8(self) -> None:
        raw = b"line one\r\nline two\r\n"
        normalized = "line one\nline two\n"
        binding = REQUIRED_REVIEW.body_source_binding(
            kind="body",
            raw=raw,
            published=normalized,
            render_contract="literal-utf8-v1",
        )

        self.assertEqual(binding["raw_byte_length"], len(raw))
        self.assertEqual(binding["raw_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(
            binding["published_sha256"],
            hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        )
        self.assertNotEqual(binding["raw_sha256"], binding["published_sha256"])

    def test_required_review_rejects_weaker_or_changed_dispatch(self) -> None:
        def change_execution(field: str, value: object):
            def mutate(envelope: dict[str, object]) -> None:
                executions = envelope["witness"]["projection"]["final_dispatch"][
                    "executions"
                ]
                executions["execution-0"][field] = value

            return mutate

        def missing_specialist(envelope: dict[str, object]) -> None:
            del envelope["witness"]["projection"]["final_dispatch"]["executions"][
                "execution-3"
            ]

        def extra_specialist(envelope: dict[str, object]) -> None:
            executions = envelope["witness"]["projection"]["final_dispatch"][
                "executions"
            ]
            extra = json.loads(json.dumps(executions["execution-3"]))
            extra["execution_id"] = "execution-extra"
            extra["role"] = "specialist-performance"
            extra["isolation"]["session"] = "session-extra"
            extra["isolation"]["context"] = "context-extra"
            executions["execution-extra"] = extra

        def reused_isolation(envelope: dict[str, object]) -> None:
            executions = envelope["witness"]["projection"]["final_dispatch"][
                "executions"
            ]
            executions["execution-1"]["isolation"]["session"] = "session-0"

        def weaker_authority(envelope: dict[str, object]) -> None:
            executions = envelope["witness"]["projection"]["final_dispatch"][
                "executions"
            ]
            executions["execution-0"]["authority"]["external_action"] = True

        def change_nested(section: str, field: str, value: object):
            def mutate(envelope: dict[str, object]) -> None:
                executions = envelope["witness"]["projection"]["final_dispatch"][
                    "executions"
                ]
                executions["execution-0"][section][field] = value

            return mutate

        cases = {
            "model": change_execution("model", "gpt-5.6-terra"),
            "effort": change_execution("reasoning_effort", "medium"),
            "controller-observed-model": change_nested(
                "assurance", "model", "controller-observed"
            ),
            "self-reported-result": change_nested(
                "assurance", "execution_result", "self-reported"
            ),
            "weaker-assurance-minimum": change_nested(
                "assurance_minimum", "execution_result", "controller-observed"
            ),
            "codex-cli-surface": change_nested("target", "surface", "codex-cli-tui"),
            "retired-codex-desktop-surface": change_nested(
                "target", "surface", "codex-desktop"
            ),
            "peer-topology": change_nested("topology", "relationship", "peer"),
            "missing-specialist": missing_specialist,
            "extra-specialist": extra_specialist,
            "reused-isolation": reused_isolation,
            "weaker-authority": weaker_authority,
            "wrong-return-contract": change_execution(
                "return_contract", "worker-report-v1"
            ),
        }
        for label, mutation in cases.items():
            with self.subTest(label=label):
                with (
                    mock.patch.object(
                        REQUIRED_REVIEW,
                        "_invoke_task_witness",
                        return_value=self.mutate_envelope(mutation),
                    ),
                    self.assertRaisesRegex(
                        REQUIRED_REVIEW.PublicationError, "Rolecasting"
                    ),
                ):
                    REQUIRED_REVIEW.validate_required_review(
                        review_mode="required",
                        review_bundle_root=Path("/absolute/review-bundle"),
                        candidate=self.candidate(),
                    )

    def test_supervisor_stops_output_flood_at_hard_cap(self) -> None:
        started = time.monotonic()
        source = (
            f"#!{sys.executable}\nimport os\nwhile True: os.write(1, b'x' * 65536)\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            with (
                self.authenticated_test_front_door(
                    Path(directory), source
                ) as observation,
                mock.patch.object(REQUIRED_REVIEW, "MAX_STDOUT_BYTES", 1024),
                mock.patch.object(REQUIRED_REVIEW, "TIMEOUT_SECONDS", 2),
                mock.patch.object(REQUIRED_REVIEW, "SETTLEMENT_SECONDS", 3),
                mock.patch.object(REQUIRED_REVIEW, "TERMINATION_GRACE_SECONDS", 0.1),
                self.assertRaisesRegex(
                    REQUIRED_REVIEW.PublicationError, "output exceeded"
                ),
            ):
                REQUIRED_REVIEW._retired_supervised_process(
                    observation, Path("/absolute/review-bundle")
                )
        self.assertLess(time.monotonic() - started, 2)

    def test_supervisor_reaps_detached_descendant_after_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wrapper_pid = root / "wrapper.pid"
            child_pid = root / "child.pid"
            code = (
                f"#!{sys.executable}\n"
                "import os,time\n"
                f"open({str(wrapper_pid)!r},'w').write(str(os.getpid()))\n"
                "pid=os.fork()\n"
                "if pid == 0:\n"
                " os.setsid()\n"
                f" open({str(child_pid)!r},'w').write(str(os.getpid()))\n"
                " os.close(0); os.close(1); os.close(2)\n"
                " while True: time.sleep(1)\n"
                "while True: time.sleep(1)\n"
            )
            with (
                self.authenticated_test_front_door(root, code) as observation,
                mock.patch.object(REQUIRED_REVIEW, "TIMEOUT_SECONDS", 1.0),
                mock.patch.object(REQUIRED_REVIEW, "SETTLEMENT_SECONDS", 2),
                mock.patch.object(REQUIRED_REVIEW, "TERMINATION_GRACE_SECONDS", 0.1),
                self.assertRaisesRegex(REQUIRED_REVIEW.PublicationError, "timed out"),
            ):
                REQUIRED_REVIEW._retired_supervised_process(
                    observation, Path("/absolute/review-bundle")
                )

            for path in (wrapper_pid, child_pid):
                self.assertTrue(path.is_file())
                pid = int(path.read_text(encoding="utf-8"))
                deadline = time.monotonic() + 1
                while time.monotonic() < deadline:
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        break
                    time.sleep(0.02)
                else:
                    self.fail(f"supervised process {pid} remained live")

    def test_supervisor_rejects_an_open_call_shape_before_launch(self) -> None:
        with (
            mock.patch.object(REQUIRED_REVIEW.subprocess, "Popen") as launch,
            self.assertRaisesRegex(
                REQUIRED_REVIEW.PublicationError, "closed internal call shape"
            ),
        ):
            REQUIRED_REVIEW._retired_supervised_process(
                object(), Path("/absolute/review-bundle")
            )
        launch.assert_not_called()

    def test_invoke_requires_canonical_envelope_framing_after_status_zero(
        self,
    ) -> None:
        source = f"#!{sys.executable}\nimport os\nos.write(1, b'{{}}\\n')\n"
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.installed_front_door(home, source)
            passwd, effective, group = self.front_door_identity(home)
            with (
                passwd,
                effective,
                group,
                self.assertRaisesRegex(
                    REQUIRED_REVIEW.PublicationError, "envelope framing"
                ),
            ):
                REQUIRED_REVIEW._retired_invoke_task_witness(
                    Path("/absolute/review-bundle")
                )

    def test_invoke_accepts_exact_canonical_envelope_fixture(self) -> None:
        envelope = self.envelope()
        source = f"#!{sys.executable}\nimport os\nos.write(1, {envelope!r})\n"
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.installed_front_door(home, source)
            passwd, effective, group = self.front_door_identity(home)
            with passwd, effective, group:
                self.assertEqual(
                    REQUIRED_REVIEW._retired_invoke_task_witness(
                        Path("/absolute/review-bundle")
                    ),
                    envelope,
                )

    def test_supervisor_cleanup_attempts_settlement_and_every_close(self) -> None:
        events: list[str] = []

        class FailingResource:
            def __init__(self, label: str) -> None:
                self.label = label

            def close(self) -> None:
                events.append(self.label)
                raise RuntimeError(self.label)

            def fileno(self) -> int:
                return 1

        class FailingSelector(FailingResource):
            def get_map(self) -> dict[object, object]:
                return {}

            def register(self, *_: object) -> None:
                return None

        process = mock.Mock()
        process.stdout = FailingResource("stdout")
        process.stderr = FailingResource("stderr")
        process.poll.return_value = 0
        process.wait.return_value = 0

        def settle(*_: object, **__: object) -> None:
            events.append("settle")
            raise RuntimeError("settle")

        with tempfile.TemporaryDirectory() as directory:
            with (
                self.authenticated_test_front_door(Path(directory)) as observation,
                mock.patch.object(
                    REQUIRED_REVIEW.selectors,
                    "DefaultSelector",
                    return_value=FailingSelector("selector"),
                ),
                mock.patch.object(
                    REQUIRED_REVIEW.subprocess, "Popen", return_value=process
                ),
                mock.patch.object(REQUIRED_REVIEW.os, "set_blocking"),
                mock.patch.object(REQUIRED_REVIEW, "_settle", side_effect=settle),
                self.assertRaisesRegex(
                    REQUIRED_REVIEW.PublicationError, "process cleanup failed"
                ) as raised,
            ):
                REQUIRED_REVIEW._retired_supervised_process(
                    observation, Path("/absolute/review-bundle")
                )
        self.assertEqual(events, ["settle", "selector", "stdout", "stderr"])
        self.assertEqual(len(raised.exception.__notes__), 4)

    def test_supervisor_cleanup_faults_do_not_mask_primary_error(self) -> None:
        process = mock.Mock()
        process.stdout.fileno.return_value = 1
        process.stderr.fileno.return_value = 2

        with tempfile.TemporaryDirectory() as directory:
            with (
                self.authenticated_test_front_door(Path(directory)) as observation,
                mock.patch.object(
                    REQUIRED_REVIEW.subprocess, "Popen", return_value=process
                ),
                mock.patch.object(
                    REQUIRED_REVIEW.selectors.DefaultSelector,
                    "register",
                    side_effect=KeyboardInterrupt("primary"),
                ),
                mock.patch.object(REQUIRED_REVIEW.os, "set_blocking"),
                mock.patch.object(
                    REQUIRED_REVIEW, "_settle", side_effect=RuntimeError("settle")
                ),
                self.assertRaisesRegex(KeyboardInterrupt, "primary") as raised,
            ):
                REQUIRED_REVIEW._retired_supervised_process(
                    observation, Path("/absolute/review-bundle")
                )
        self.assertTrue(
            any("RuntimeError('settle')" in note for note in raised.exception.__notes__)
        )
        process.stdout.close.assert_called_once_with()
        process.stderr.close.assert_called_once_with()

    def installed_front_door(
        self, root: Path, source: str = "#!/bin/sh\nexit 0\n"
    ) -> Path:
        root.chmod(0o700)
        current = root
        for component in (".local", "libexec", "task-witness"):
            current /= component
            current.mkdir()
            current.chmod(0o700)
        leaf = current / "task-witness"
        leaf.write_text(source, encoding="utf-8")
        leaf.chmod(0o500)
        return leaf

    @contextmanager
    def authenticated_test_front_door(self, home: Path, source: str | None = None):
        self.installed_front_door(
            home, source if source is not None else "#!/bin/sh\nexit 0\n"
        )
        passwd, effective, group = self.front_door_identity(home)
        with (
            passwd,
            effective,
            group,
            REQUIRED_REVIEW._authenticated_front_door() as value,
        ):
            yield value

    def front_door_identity(self, home: Path):
        effective_uid = os.geteuid()
        return (
            mock.patch.object(
                REQUIRED_REVIEW.pwd,
                "getpwuid",
                return_value=SimpleNamespace(pw_dir=str(home)),
            ),
            mock.patch.object(
                REQUIRED_REVIEW.os, "geteuid", return_value=effective_uid
            ),
            mock.patch.object(REQUIRED_REVIEW.os, "getegid", return_value=os.getegid()),
        )

    def test_front_door_uses_effective_not_real_user_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            leaf = self.installed_front_door(home)
            passwd, effective, group = self.front_door_identity(home)
            with (
                passwd as passwd_lookup,
                effective,
                group,
                mock.patch.object(
                    REQUIRED_REVIEW.os, "getuid", return_value=os.geteuid() + 1
                ),
                REQUIRED_REVIEW._authenticated_front_door() as authenticated,
            ):
                self.assertEqual(authenticated.path, leaf)
            passwd_lookup.assert_called_once_with(os.geteuid())

    def test_front_door_rejects_symlink_mode_owner_and_link_drift(self) -> None:
        def symlink_leaf(home: Path, leaf: Path) -> None:
            target = leaf.with_name("target")
            leaf.rename(target)
            leaf.symlink_to(target)

        def wrong_mode(_: Path, leaf: Path) -> None:
            leaf.chmod(0o700)

        def extra_link(_: Path, leaf: Path) -> None:
            os.link(leaf, leaf.with_name("task-witness-hardlink"))

        cases = {
            "symlink": symlink_leaf,
            "mode": wrong_mode,
            "link": extra_link,
        }
        for label, mutate in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                leaf = self.installed_front_door(home)
                mutate(home, leaf)
                passwd, effective, group = self.front_door_identity(home)
                with (
                    passwd,
                    effective,
                    group,
                    self.assertRaises(REQUIRED_REVIEW.PublicationError),
                ):
                    with REQUIRED_REVIEW._authenticated_front_door():
                        self.fail("untrusted front door was authenticated")

        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.installed_front_door(home)
            with (
                mock.patch.object(
                    REQUIRED_REVIEW.pwd,
                    "getpwuid",
                    return_value=SimpleNamespace(pw_dir=str(home)),
                ),
                mock.patch.object(
                    REQUIRED_REVIEW.os, "geteuid", return_value=os.geteuid() + 1
                ),
                self.assertRaisesRegex(
                    REQUIRED_REVIEW.PublicationError, "home is not private"
                ),
            ):
                with REQUIRED_REVIEW._authenticated_front_door():
                    self.fail("wrong-owner front door was authenticated")

    def test_front_door_identity_is_rechecked_after_process_settlement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            leaf = self.installed_front_door(home)

            def replace_after_launch(*_: object) -> tuple[int, bytes, bytes]:
                leaf.chmod(0o700)
                return 0, b"{}\n", b""

            passwd, effective, group = self.front_door_identity(home)
            with (
                passwd,
                effective,
                group,
                mock.patch.object(
                    REQUIRED_REVIEW,
                    "_retired_supervised_process",
                    side_effect=replace_after_launch,
                ),
                self.assertRaisesRegex(
                    REQUIRED_REVIEW.PublicationError, "changed during validation"
                ),
            ):
                REQUIRED_REVIEW._retired_invoke_task_witness(
                    Path("/absolute/bundle")
                )

    def test_front_door_identity_is_rechecked_after_failed_process_settlement(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            leaf = self.installed_front_door(home)

            def fail_after_launch(*_: object) -> tuple[int, bytes, bytes]:
                leaf.chmod(0o700)
                raise REQUIRED_REVIEW.PublicationError("validation timed out")

            passwd, effective, group = self.front_door_identity(home)
            with (
                passwd,
                effective,
                group,
                mock.patch.object(
                    REQUIRED_REVIEW,
                    "_retired_supervised_process",
                    side_effect=fail_after_launch,
                ),
                self.assertRaisesRegex(
                    REQUIRED_REVIEW.PublicationError, "changed during validation"
                ),
            ):
                REQUIRED_REVIEW._retired_invoke_task_witness(
                    Path("/absolute/bundle")
                )


class ReviewablePrStateTests(unittest.TestCase):
    @staticmethod
    def live_pr(**overrides: object) -> dict[str, object]:
        value: dict[str, object] = {
            "number": 42,
            "url": "https://github.com/acme/app/pull/42",
            "title": "feat: widget",
            "body": "body",
            "baseRefName": "main",
            "baseRefOid": "a" * 40,
            "headRefName": "widget",
            "headRefOid": "b" * 40,
            "headRepository": {"nameWithOwner": "fork-owner/app-fork"},
            "headRepositoryOwner": {"login": "fork-owner"},
            "isDraft": True,
            "state": "OPEN",
        }
        value.update(overrides)
        return value

    @staticmethod
    def rest_pr(*, owner: str, number: int) -> dict[str, object]:
        return {
            "number": number,
            "html_url": f"https://github.com/acme/app/pull/{number}",
            "title": f"feat: widget {number}",
            "body": "body",
            "draft": True,
            "state": "open",
            "base": {
                "ref": "main",
                "sha": "a" * 40,
                "repo": {"full_name": "acme/app"},
            },
            "head": {
                "ref": "widget",
                "sha": "b" * 40,
                "repo": {
                    "full_name": f"{owner}/app-fork",
                    "owner": {"login": owner},
                },
            },
        }

    def test_open_pr_api_is_exhaustive_and_owner_qualified(self) -> None:
        completed = subprocess.CompletedProcess([], 0, "[[]]", "")
        with mock.patch.object(STATE, "run_read", return_value=completed) as run_read:
            self.assertEqual(
                STATE.open_prs("acme/app", "main", "fork-owner:widget"), []
            )

        arguments = run_read.call_args.args[0]
        self.assertIn("--paginate", arguments)
        self.assertIn("--slurp", arguments)
        self.assertIn("base=main", arguments)
        self.assertIn("head=fork-owner:widget", arguments)
        self.assertIn("per_page=100", arguments)
        self.assertEqual(
            arguments[arguments.index("--hostname") + 1], STATE.GITHUB_HOST
        )

    def test_github_host_is_pinned_and_ambient_routes_are_scrubbed(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"GH_HOST": "attacker.example", "GH_REPO": "attacker/repository"},
        ):
            environment = STATE._environment()

        self.assertNotIn("GH_HOST", environment)
        self.assertNotIn("GH_REPO", environment)
        self.assertEqual(STATE.github_repository("acme/app"), "github.com/acme/app")

    def test_owner_qualified_discovery_finds_target_beyond_thirty_same_name_prs(
        self,
    ) -> None:
        wrong_owner_prs = [
            self.rest_pr(owner="other-owner", number=index) for index in range(1, 36)
        ]
        target = self.rest_pr(owner="fork-owner", number=84)
        completed = subprocess.CompletedProcess(
            [],
            0,
            json.dumps([wrong_owner_prs[:30], wrong_owner_prs[30:] + [target]]),
            "",
        )

        with mock.patch.object(STATE, "run_read", return_value=completed):
            discovered = STATE.open_prs("acme/app", "main", "fork-owner:widget")
        with mock.patch.object(CREATE, "_open_prs", return_value=discovered):
            matches = CREATE._matching_head_prs(
                repository="acme/app",
                base="main",
                head="fork-owner:widget",
                head_owner="fork-owner",
                head_repository="fork-owner/app-fork",
            )

        self.assertEqual(len(discovered), 36)
        self.assertEqual([item["number"] for item in matches], [84])

    def test_open_pr_api_rejects_malformed_nodes(self) -> None:
        completed = subprocess.CompletedProcess([], 0, "[[{}]]", "")

        with mock.patch.object(STATE, "run_read", return_value=completed):
            with self.assertRaisesRegex(
                STATE.MalformedRestPrNodeError, "malformed PR node"
            ):
                STATE.open_prs("acme/app", "main", "fork-owner:widget")

    def test_open_pr_api_rejects_boolean_pr_number(self) -> None:
        malformed = self.rest_pr(owner="fork-owner", number=1)
        malformed["number"] = True
        completed = subprocess.CompletedProcess([], 0, json.dumps([[malformed]]), "")

        with mock.patch.object(STATE, "run_read", return_value=completed):
            with self.assertRaisesRegex(STATE.StateReadError, "malformed PR node"):
                STATE.open_prs("acme/app", "main", "fork-owner:widget")

    def test_stored_pr_rejects_boolean_pr_number(self) -> None:
        completed = subprocess.CompletedProcess(
            [], 0, json.dumps(self.live_pr(number=True)), ""
        )

        with mock.patch.object(STATE, "run_read", return_value=completed):
            with self.assertRaisesRegex(
                STATE.StateReadError, "live PR response is malformed"
            ):
                STATE.stored_pr("acme/app", 1)

    def test_stored_pr_admits_only_complete_well_typed_live_state(self) -> None:
        admitted = self.live_pr(providerExtension={"ignored": True})
        completed = subprocess.CompletedProcess([], 0, json.dumps(admitted), "")
        with mock.patch.object(STATE, "run_read", return_value=completed):
            self.assertEqual(STATE.stored_pr("acme/app", 42), admitted)

        for name, response, classification in (
            (
                "invalid-json",
                '{"number": 42, "body": "Authorization: arbitrary-secret-value"',
                "invalid JSON",
            ),
            (
                "incomplete",
                json.dumps({"number": 42}),
                "live PR response is incomplete",
            ),
            (
                "wrong-type",
                json.dumps(self.live_pr(body=["arbitrary-secret-value"])),
                "live PR response is malformed",
            ),
        ):
            with self.subTest(name=name):
                completed = subprocess.CompletedProcess([], 0, response, "")
                with (
                    mock.patch.object(STATE, "run_read", return_value=completed),
                    self.assertRaisesRegex(
                        STATE.StateReadError, classification
                    ) as caught,
                ):
                    STATE.stored_pr("acme/app", 42)
                diagnostic = str(caught.exception)
                self.assertNotIn("arbitrary-secret-value", diagnostic)
                self.assertNotIn("Authorization", diagnostic)
                if name == "invalid-json":
                    self.assertIsInstance(
                        caught.exception.__cause__, json.JSONDecodeError
                    )

    def test_live_pr_admission_bounds_ascii_decimal_url_identifiers(self) -> None:
        oversized = "9" * 5_000
        for name, suffix in (
            ("oversized", oversized),
            ("non-ascii", "٤٢"),
        ):
            with self.subTest(name=name), self.assertRaisesRegex(
                STATE.LiveStateResponseError, "live PR response is malformed"
            ) as caught:
                STATE.validate_live_pr_observation(
                    self.live_pr(url=f"https://github.com/acme/app/pull/{suffix}")
                )
            if name == "oversized":
                self.assertIsInstance(caught.exception.__cause__, ValueError)

        admitted = STATE.validate_live_pr_observation(self.live_pr())
        self.assertEqual(admitted["number"], 42)
        self.assertEqual(admitted["url"], "https://github.com/acme/app/pull/42")

    def test_stored_pr_safely_classifies_oversized_provider_numbers(self) -> None:
        oversized = "9" * 5_000
        cases = (
            (
                "json-integer",
                f'{{"number": {oversized}, "Authorization": "secret"}}',
                "returned invalid JSON",
                ValueError,
            ),
            (
                "url-identifier",
                json.dumps(
                    self.live_pr(
                        url=f"https://github.com/acme/app/pull/{oversized}",
                        providerExtension="Authorization: arbitrary-secret-value",
                    )
                ),
                "live PR response is malformed",
                ValueError,
            ),
        )
        for name, output, classification, cause_type in cases:
            completed = subprocess.CompletedProcess([], 0, output, "")
            with (
                self.subTest(name=name),
                mock.patch.object(STATE, "run_read", return_value=completed),
                self.assertRaisesRegex(STATE.StateReadError, classification) as caught,
            ):
                STATE.stored_pr("acme/app", 42)
            diagnostic = str(caught.exception)
            self.assertNotIn("arbitrary-secret-value", diagnostic)
            self.assertNotIn("Authorization", diagnostic)
            self.assertIsInstance(caught.exception.__cause__, cause_type)

    def test_required_observation_strings_are_utf8_scalar_text(self) -> None:
        for field, value in (
            ("title", "escaped-high-\ud800"),
            ("title", "escaped-low-\udc00"),
            ("body", "escaped-high-\ud800"),
            ("body", "escaped-low-\udc00"),
        ):
            raw = json.dumps(self.live_pr(**{field: value}))
            parsed = STATE.strict_json(raw, "synthetic provider")
            with self.subTest(field=field, value=ascii(value)), self.assertRaisesRegex(
                STATE.LiveStateResponseError, "live PR response is malformed"
            ) as caught:
                STATE.validate_live_pr_observation(parsed)
            self.assertIsInstance(caught.exception.__cause__, UnicodeEncodeError)

        title = "feat: café 😀"
        body = "exact λ and paired 🚀"
        raw = json.dumps(self.live_pr(title=title, body=body))
        admitted = STATE.validate_live_pr_observation(
            STATE.strict_json(raw, "synthetic provider")
        )
        self.assertEqual(admitted["title"], title)
        self.assertEqual(admitted["body"], body)

    def test_rest_recovery_admits_required_scalar_text(self) -> None:
        malformed = self.rest_pr(owner="fork-owner", number=42)
        malformed["body"] = "Authorization: arbitrary-secret-value\ud800"
        completed = subprocess.CompletedProcess(
            [], 0, json.dumps([[malformed]]), ""
        )

        with mock.patch.object(STATE, "run_read", return_value=completed):
            with self.assertRaisesRegex(
                STATE.StateReadError, "malformed PR node"
            ) as caught:
                STATE.open_prs("acme/app", "main", "fork-owner:widget")

        diagnostic = str(caught.exception)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertIsInstance(
            caught.exception.__cause__, STATE.LiveStateResponseError
        )

    def test_rest_recovery_normalizes_only_null_body_and_preserves_text(self) -> None:
        for name, body in (
            ("null", None),
            ("empty", ""),
            ("non-ascii", "exact café λ 🚀"),
        ):
            rest_pr = self.rest_pr(owner="fork-owner", number=42)
            rest_pr["body"] = body
            completed = subprocess.CompletedProcess(
                [], 0, json.dumps([[rest_pr]]), ""
            )
            with (
                self.subTest(case=name),
                mock.patch.object(STATE, "run_read", return_value=completed),
            ):
                recovered = STATE.open_prs(
                    "acme/app", "main", "fork-owner:widget"
                )

            self.assertEqual(recovered[0]["body"], "" if body is None else body)

    def test_rest_recovery_rejects_non_string_bodies(self) -> None:
        for body in (False, 0, [], {}, True, 1, ["body"], {"body": "text"}, 1.5):
            rest_pr = self.rest_pr(owner="fork-owner", number=42)
            rest_pr["body"] = body
            completed = subprocess.CompletedProcess(
                [], 0, json.dumps([[rest_pr]]), ""
            )
            with (
                self.subTest(body_type=type(body).__name__),
                mock.patch.object(STATE, "run_read", return_value=completed),
                self.assertRaisesRegex(
                    STATE.StateReadError, "malformed PR node"
                ) as caught,
            ):
                STATE.open_prs("acme/app", "main", "fork-owner:widget")

            self.assertIsInstance(caught.exception.__cause__, TypeError)
            diagnostic = str(caught.exception)
            self.assertNotIn(repr(body), diagnostic)

    def test_live_pr_admission_captures_required_mutable_fields(self) -> None:
        source = self.live_pr(providerExtension={"ignored": True})
        admitted = STATE.validate_live_pr_observation(source)

        source["body"] = ["changed after admission"]
        source["headRepository"]["nameWithOwner"] = "other/repository"
        source["headRepositoryOwner"]["login"] = "other-owner"

        self.assertEqual(admitted, self.live_pr(providerExtension={"ignored": True}))

    def test_live_pr_admission_captures_bounded_retained_json(self) -> None:
        extension = {"nested": [{"value": "retained"}], "ratio": 1.5}
        source = self.live_pr(providerExtension=extension)

        admitted = STATE.validate_live_pr_observation(source)
        extension["nested"][0]["value"] = "changed after admission"

        self.assertEqual(
            admitted["providerExtension"],
            {"nested": [{"value": "retained"}], "ratio": 1.5},
        )

    def test_live_pr_admission_rejects_unsafe_retained_json_values(self) -> None:
        oversized = 10 ** STATE.DECIMAL_IDENTIFIER_DIGIT_LIMIT
        cases = (
            ("non-json", {"nested": [object()]}),
            ("non-finite", {"nested": [float("inf")]}),
            ("oversized-number", {"nested": [oversized]}),
        )
        for name, extension in cases:
            with self.subTest(name=name), self.assertRaisesRegex(
                STATE.LiveStateResponseError, "live PR response is malformed"
            ):
                STATE.validate_live_pr_observation(
                    self.live_pr(providerExtension=extension)
                )

    def test_live_pr_admission_rejects_inconsistent_or_unusable_identity_fields(
        self,
    ) -> None:
        cases = (
            ("number-url", self.live_pr(number=41)),
            (
                "unusable-repository-alternatives",
                self.live_pr(headRepository={"nameWithOwner": None}),
            ),
            ("oversized-direct-number", self.live_pr(number=10 ** 5_000)),
        )
        for name, value in cases:
            with self.subTest(name=name), self.assertRaisesRegex(
                STATE.LiveStateResponseError, "live PR response is malformed"
            ):
                STATE.validate_live_pr_observation(value)

    def test_live_pr_admission_rejects_non_json_string_subclasses(self) -> None:
        class DeceptiveString(str):
            def __eq__(self, other: object) -> bool:
                return True

            __hash__ = str.__hash__

        cases = (
            self.live_pr(title=DeceptiveString("provider text")),
            {
                **self.live_pr(),
                DeceptiveString("providerExtension"): {"ignored": True},
            },
            self.live_pr(
                headRepository={
                    "owner": {"login": DeceptiveString("fork-owner")},
                    "name": "app-fork",
                }
            ),
            self.live_pr(
                headRepositoryOwner={"login": DeceptiveString("fork-owner")}
            ),
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaisesRegex(
                STATE.LiveStateResponseError, "live PR response is malformed"
            ):
                STATE.validate_live_pr_observation(value)

    def test_read_compatibility_alias_is_not_exposed(self) -> None:
        self.assertFalse(hasattr(STATE, "run"))

    def test_strict_forge_json_rejects_duplicate_keys(self) -> None:
        with self.assertRaisesRegex(STATE.StateReadError, "duplicate JSON object keys"):
            STATE.strict_json('{"number": 1, "number": 2}', "forge")

    def test_stored_pr_duplicate_key_diagnostic_is_value_free(self) -> None:
        hostile_key = "Authorization: Bearer synthetic-secret\x1b[31m"
        output = json.dumps(
            {
                "number": 1,
                hostile_key: "first",
            }
        )[:-1] + f', {json.dumps(hostile_key)}: "second"}}'
        completed = subprocess.CompletedProcess([], 0, output.encode("utf-8"), b"")

        with (
            mock.patch.object(STATE.subprocess, "run", return_value=completed),
            self.assertRaisesRegex(
                STATE.StateReadError, "contains duplicate JSON object keys"
            ) as raised,
        ):
            STATE.stored_pr("acme/app", 1)

        diagnostic = str(raised.exception)
        self.assertNotIn("synthetic-secret", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertNotIn("\x1b", diagnostic)

    def test_strict_forge_json_rejects_non_finite_values(self) -> None:
        for constant in ("NaN", "Infinity", "-Infinity", "1e9999", "-1e9999"):
            with self.subTest(constant=constant):
                with self.assertRaisesRegex(
                    STATE.StateReadError, "non-finite JSON value"
                ):
                    STATE.strict_json(f'{{"number": {constant}}}', "forge")

    def test_strict_forge_json_classifies_parser_recursion_limits(self) -> None:
        hostile = "Authorization: synthetic-secret"
        payload = "[" * 2_000 + json.dumps(hostile) + "]" * 2_000

        with self.assertRaisesRegex(
            STATE.JsonReadError, "returned invalid JSON"
        ) as caught:
            STATE.strict_json(payload, "synthetic provider")

        self.assertEqual(caught.exception.kind, "invalid")
        self.assertNotIn(hostile, str(caught.exception))
        self.assertIsNotNone(caught.exception.__cause__)

    def test_strict_forge_json_classifies_oversized_integers_as_invalid(self) -> None:
        oversized = "9" * 5_000
        with self.assertRaises(STATE.JsonReadError) as caught:
            STATE.strict_json(f'{{"number": {oversized}}}', "synthetic provider")

        self.assertEqual(caught.exception.kind, "invalid")
        self.assertEqual(
            str(caught.exception), "synthetic provider returned invalid JSON"
        )
        self.assertIsInstance(caught.exception.__cause__, ValueError)

    def test_selected_specialists_use_bounded_exact_json_array_admission(self) -> None:
        hostile = "Authorization: synthetic-secret"
        malformed = (
            "{",
            '{"not": "an array"}',
            '["valid", 1]',
            '["valid", "valid"]',
            '["later", "earlier"]',
            "[" * 2_000 + json.dumps(hostile) + "]" * 2_000,
            "[" + "9" * 5_000 + "]",
        )
        for raw in malformed:
            with self.subTest(raw_length=len(raw)):
                with self.assertRaisesRegex(
                    STATE.PublicationError,
                    "selected review specialists must be a sorted unique JSON array",
                ) as caught:
                    STATE.parse_selected_specialists(raw)
                self.assertNotIn(hostile, str(caught.exception))
                self.assertNotIn("Traceback", str(caught.exception))

        self.assertEqual(
            STATE.parse_selected_specialists('["architecture", "security"]'),
            ["architecture", "security"],
        )

    def test_publication_clis_safely_reject_oversized_specialist_json(self) -> None:
        malformed = "[" + "9" * 5_000 + "]"
        common = [
            "--repository",
            "acme/app",
            "--base",
            "main",
            "--base-oid",
            "a" * 40,
            "--head",
            "fork-owner:widget",
            "--head-oid",
            "b" * 40,
            "--head-owner",
            "fork-owner",
            "--head-repository",
            "fork-owner/app-fork",
        ]
        cases = (
            (
                CREATE,
                [
                    *common,
                    "--title",
                    "feat: widget",
                    "--body-template",
                    "/synthetic/body.md",
                    "--review-input",
                    "/synthetic/review-input.json",
                    "--review-mode",
                    "not-required",
                    "--selected-specialists",
                    malformed,
                ],
                "publish",
            ),
            (
                UPDATE,
                [
                    "ready",
                    *common[:2],
                    "--pr",
                    "42",
                    *common[2:],
                    "--expected-title-sha256",
                    "c" * 64,
                    "--expected-body-sha256",
                    "d" * 64,
                    "--review-input",
                    "/synthetic/review-input.json",
                    "--review-mode",
                    "not-required",
                    "--selected-specialists",
                    malformed,
                ],
                "mark_ready",
            ),
        )
        for module, arguments, mutation_name in cases:
            with self.subTest(module=module.__name__):
                with (
                    mock.patch.object(sys, "argv", [str(module.__file__), *arguments]),
                    mock.patch.object(module, mutation_name) as mutate,
                    mock.patch("builtins.print") as output,
                ):
                    self.assertEqual(module.main(), 1)
                mutate.assert_not_called()
                diagnostic = output.call_args.args[0]
                self.assertIn("sorted unique JSON array", diagnostic)
                self.assertNotIn("9999999999", diagnostic)
                self.assertNotIn("Traceback", diagnostic)

    def test_publication_clis_contain_post_mutation_receipt_reload_failures(
        self,
    ) -> None:
        stored = self.live_pr()
        common = [
            "--repository",
            "acme/app",
            "--base",
            "main",
            "--base-oid",
            "a" * 40,
            "--head",
            "fork-owner:widget",
            "--head-oid",
            "b" * 40,
            "--head-owner",
            "fork-owner",
            "--head-repository",
            "fork-owner/app-fork",
        ]
        cases = (
            (
                CREATE,
                [
                    *common,
                    "--title",
                    "feat: widget",
                    "--body-template",
                    "/synthetic/body.md",
                    "--review-input",
                    "/synthetic/review-input.json",
                    "--review-mode",
                    "not-required",
                    "--selected-specialists",
                    "[]",
                ],
                "publish",
                RECEIPTS.ReceiptError(
                    "Authorization: arbitrary-secret-value\x1b[31m"
                ),
            ),
            (
                UPDATE,
                [
                    "ready",
                    *common[:2],
                    "--pr",
                    "42",
                    *common[2:],
                    "--expected-title-sha256",
                    "c" * 64,
                    "--expected-body-sha256",
                    "d" * 64,
                    "--review-input",
                    "/synthetic/review-input.json",
                    "--review-mode",
                    "not-required",
                    "--selected-specialists",
                    "[]",
                ],
                "mark_ready",
                [],
            ),
        )
        for module, arguments, mutation_name, reload_result in cases:
            with self.subTest(module=module.__name__):
                reload_kwargs = (
                    {"side_effect": reload_result}
                    if isinstance(reload_result, BaseException)
                    else {"return_value": reload_result}
                )
                with (
                    mock.patch.object(sys, "argv", [str(module.__file__), *arguments]),
                    mock.patch.object(
                        module, mutation_name, return_value=stored
                    ) as mutate,
                    mock.patch.object(module, "load_receipts", **reload_kwargs),
                    mock.patch("builtins.print") as output,
                ):
                    self.assertEqual(module.main(), 1)
                self.assertEqual(mutate.call_count, 1)
                diagnostic = output.call_args.args[0]
                self.assertIn("receipt acknowledgement is unavailable", diagnostic)
                self.assertIn("independently audit exact state", diagnostic)
                self.assertIn("do not retry", diagnostic)
                self.assertNotIn("Authorization", diagnostic)
                self.assertNotIn("arbitrary-secret-value", diagnostic)
                self.assertNotIn("Traceback", diagnostic)

    def test_read_diagnostics_share_safe_json_and_schema_classifications(self) -> None:
        failures: list[tuple[str, STATE.PublicationError]] = []
        for expected, payload in (
            ("invalid JSON", "{"),
            ("JSON with duplicate object keys", '{"x": 1, "x": 2}'),
            ("JSON with a non-finite value", '{"x": NaN}'),
        ):
            with self.assertRaises(STATE.PublicationError) as caught:
                STATE.strict_json(payload, "synthetic provider")
            failures.append((expected, caught.exception))
        failures.extend(
            (
                ("an incomplete response", STATE.LiveStateResponseError("incomplete")),
                ("a malformed response", STATE.LiveStateResponseError("malformed")),
            )
        )

        for expected, error in failures:
            with self.subTest(expected=expected):
                audit = STATE.classified_read_failure(
                    error, stage="live PR state read"
                )
                recovery = STATE.read_failure_diagnostic(error)
                self.assertIn(f"returned {expected}", audit)
                self.assertIn(f"returned {expected}", recovery)
                self.assertIn(
                    "existing read authority while it remains valid", recovery
                )

        unknown = STATE.StateReadError(
            "Authorization: Bearer arbitrary-secret-value"
        )
        diagnostic = STATE.classified_read_failure(
            unknown, stage="live PR state read"
        )
        self.assertIn("unclassified reason", diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("Authorization", diagnostic)

    def test_state_read_diagnostics_use_only_typed_failure_data(self) -> None:
        unknown = STATE.StateReadError(UnprintableExceptionData())

        self.assertEqual(
            STATE.classified_read_failure(unknown, stage="live PR state read"),
            "live PR state read failed for an unclassified reason; details were "
            "withheld because they may contain sensitive data",
        )
        self.assertEqual(
            STATE.read_failure_diagnostic(unknown),
            "post-mutation reread failed for an unclassified reason; details were "
            "withheld because they may contain sensitive data; reuse existing read "
            "authority while it remains valid; obtain new authority only if the "
            "target or action is outside its scope",
        )

        malformed = STATE.MalformedRestPrNodeError()
        self.assertIn(
            "returned a malformed response",
            STATE.classified_read_failure(malformed, stage="live PR state read"),
        )
        self.assertIn(
            "returned a malformed response",
            STATE.read_failure_diagnostic(malformed),
        )

    def test_identity_binds_exact_head_repository_full_name(self) -> None:
        expected = STATE.ExpectedIdentity(
            repository="acme/app",
            pr_number=42,
            base="main",
            base_oid="a" * 40,
            head="fork-owner:widget",
            head_oid="b" * 40,
            head_owner="fork-owner",
            head_repository="fork-owner/app-fork",
        )
        stored = {
            "number": 42,
            "url": "https://github.com/acme/app/pull/42",
            "baseRefName": "main",
            "baseRefOid": "a" * 40,
            "headRefName": "widget",
            "headRefOid": "b" * 40,
            "headRepositoryOwner": {"login": "fork-owner"},
            "headRepository": {"nameWithOwner": "fork-owner/other-fork"},
            "state": "OPEN",
        }
        self.assertFalse(STATE.identity_matches(stored, expected))

    def test_identity_rejects_boolean_stored_pr_number(self) -> None:
        expected = STATE.ExpectedIdentity(
            repository="acme/app",
            pr_number=1,
            base="main",
            base_oid="a" * 40,
            head="fork-owner:widget",
            head_oid="b" * 40,
            head_owner="fork-owner",
            head_repository="fork-owner/app-fork",
        )
        stored = {
            "number": True,
            "url": "https://github.com/acme/app/pull/1",
            "baseRefName": "main",
            "baseRefOid": "a" * 40,
            "headRefName": "widget",
            "headRefOid": "b" * 40,
            "headRepositoryOwner": {"login": "fork-owner"},
            "headRepository": {"nameWithOwner": "fork-owner/app-fork"},
            "state": "OPEN",
        }

        self.assertFalse(STATE.identity_matches(stored, expected))

    def test_identity_inputs_reject_boolean_and_float_pr_numbers(self) -> None:
        for malformed in (True, 1.0):
            with self.subTest(malformed=malformed):
                with self.assertRaisesRegex(STATE.PublicationError, "PR number"):
                    STATE.validate_identity_inputs(
                        repository="acme/app",
                        pr_number=malformed,
                        base="main",
                        base_oid="a" * 40,
                        head="fork-owner:widget",
                        head_oid="b" * 40,
                        head_owner="fork-owner",
                        head_repository="fork-owner/app-fork",
                    )

    def test_identity_inputs_reject_control_characters_in_repositories(self) -> None:
        cases = (
            ("acme\x1b[31m/app", "fork-owner/app-fork"),
            ("acme/app", "fork-owner/app-fork\x1b[31m"),
        )
        for repository, head_repository in cases:
            with self.subTest(
                repository=repository, head_repository=head_repository
            ):
                with self.assertRaises(STATE.PublicationError) as raised:
                    STATE.validate_identity_inputs(
                        repository=repository,
                        pr_number=1,
                        base="main",
                        base_oid="a" * 40,
                        head="fork-owner:widget",
                        head_oid="b" * 40,
                        head_owner="fork-owner",
                        head_repository=head_repository,
                    )

                diagnostic = str(raised.exception)
                self.assertNotIn("\x1b", diagnostic)
                self.assertNotIn("[31m", diagnostic)

    def test_read_and_possible_mutation_timeouts_are_distinct(self) -> None:
        timeout = subprocess.TimeoutExpired(["gh"], 1)
        with mock.patch.object(subprocess, "run", side_effect=timeout):
            with self.assertRaises(STATE.StateReadError):
                STATE.run_read(["gh", "pr", "view"])
            with self.assertRaises(STATE.MutationAmbiguousError):
                STATE.run_mutation(["gh", "pr", "edit"])

    def test_broad_os_failures_have_unknown_process_and_mutation_outcomes(self) -> None:
        cases = (
            (
                STATE.run_read,
                STATE.CommandReadError,
                "whether the read process started is unknown",
            ),
            (
                STATE.run_mutation,
                STATE.MutationAmbiguousError,
                "whether the mutation process started is unknown",
            ),
        )
        for runner, error_type, classification in cases:
            with self.subTest(classification=classification):
                process_error = OSError(
                    "/synthetic/arbitrary-secret-value/gh: Authorization\x1b[31m"
                )
                with (
                    mock.patch.object(
                        STATE.subprocess, "run", side_effect=process_error
                    ),
                    self.assertRaises(error_type) as raised,
                ):
                    runner(
                        [
                            "gh",
                            "--header",
                            "Authorization: Bearer command-input-secret",
                        ]
                    )

                diagnostic = str(raised.exception)
                self.assertIn(classification, diagnostic)
                self.assertIs(raised.exception.__cause__, process_error)
                self.assertNotIn("arbitrary-secret-value", diagnostic)
                self.assertNotIn("command-input-secret", diagnostic)
                self.assertNotIn("Authorization", diagnostic)
                self.assertNotIn("OSError", diagnostic)
                self.assertNotIn("\x1b", diagnostic)
                if runner is STATE.run_mutation:
                    self.assertTrue(raised.exception.process_outcome_unknown)
                    self.assertIn("mutation outcome is unknown", diagnostic)
                    self.assertIn("do not retry", diagnostic)
                else:
                    self.assertTrue(raised.exception.process_outcome_unknown)

    def test_post_start_io_failure_is_classified_at_the_shared_process_boundary(
        self,
    ) -> None:
        for runner, error_type in (
            (STATE.run_read, STATE.CommandReadError),
            (STATE.run_mutation, STATE.MutationAmbiguousError),
        ):
            events: list[str] = []
            io_error = OSError(
                "/synthetic/arbitrary-secret-value/gh: Authorization\x1b[31m"
            )

            with (
                self.subTest(runner=runner.__name__),
                mock.patch.object(
                    STATE.subprocess,
                    "Popen",
                    post_start_io_failure_popen(events, io_error),
                ),
                self.assertRaises(error_type) as caught,
            ):
                runner(["synthetic-forge"])

            diagnostic = str(caught.exception)
            self.assertEqual(
                events,
                [
                    "process-created",
                    "communicate-entered",
                    "process-killed",
                    "process-waited",
                ],
            )
            self.assertIs(caught.exception.__cause__, io_error)
            self.assertTrue(caught.exception.process_outcome_unknown)
            self.assertIn("process started is unknown", diagnostic)
            self.assertNotIn("arbitrary-secret-value", diagnostic)
            self.assertNotIn("Authorization", diagnostic)
            self.assertNotIn("could not start", diagnostic)

    def test_local_command_preparation_failures_are_typed_and_never_start(self) -> None:
        cases = (
            (
                STATE.run_read,
                STATE.CommandReadError,
                "read command could not be prepared locally",
                "no read command started",
            ),
            (
                STATE.run_mutation,
                STATE.MutationPreparationError,
                "mutation command could not be prepared locally",
                "no target mutation ran",
            ),
        )
        for runner, error_type, classification, no_start in cases:
            for name, arguments, input_text, cause_type in (
                (
                    "lone-surrogate-input",
                    ["gh", "synthetic"],
                    "secret-\ud800",
                    UnicodeEncodeError,
                ),
                ("nul-argument", ["gh", "secret\x00argument"], None, ValueError),
            ):
                with (
                    self.subTest(runner=runner.__name__, case=name),
                    mock.patch.object(STATE.subprocess, "run") as run,
                    self.assertRaises(error_type) as raised,
                ):
                    runner(arguments, input_text=input_text)

                diagnostic = str(raised.exception)
                self.assertIn(classification, diagnostic)
                self.assertIn(no_start, diagnostic)
                self.assertIsInstance(raised.exception.__cause__, cause_type)
                self.assertNotIn("secret", diagnostic)
                self.assertNotIn("Traceback", diagnostic)
                run.assert_not_called()

        self.assertFalse(hasattr(STATE, "MutationLaunchError"))
        self.assertFalse(hasattr(STATE.CommandReadError(), "launch_failed"))

    def test_valid_command_input_preserves_utf8_and_process_result(self) -> None:
        completed = subprocess.CompletedProcess(
            ["gh", "synthetic"], 0, "résultat 🚀".encode(), "erreur λ".encode()
        )
        for runner in (STATE.run_read, STATE.run_mutation):
            with (
                self.subTest(runner=runner.__name__),
                mock.patch.object(
                    STATE.subprocess, "run", return_value=completed
                ) as run,
            ):
                result = runner(["gh", "synthetic"], input_text="entrée café")

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "résultat 🚀")
            self.assertEqual(result.stderr, "erreur λ")
            self.assertEqual(run.call_args.kwargs["input"], "entrée café".encode())

    def test_nonzero_command_output_is_withheld_from_diagnostics(self) -> None:
        output = (
            "https://user:arbitrary-secret-value@example.test/?token=secret\n"
            "Authorization: Bearer arbitrary-secret-value\x00\x1b[31m\n"
            + "x" * (1024 * 1024)
        )
        cases = (
            (STATE.run_read, STATE.StateReadError, 31, "read command rejected"),
            (
                STATE.run_mutation,
                STATE.PublicationError,
                32,
                "mutation command rejected",
            ),
        )
        for runner, error_type, return_code, classification in cases:
            with self.subTest(classification=classification):
                completed = subprocess.CompletedProcess([], return_code, output, output)
                with (
                    mock.patch.object(subprocess, "run", return_value=completed),
                    self.assertRaises(error_type) as raised,
                ):
                    runner(
                        [
                            "gh",
                            "--header",
                            "Authorization: Bearer command-input-secret",
                        ]
                    )

                diagnostic = str(raised.exception)
                self.assertIn(classification, diagnostic)
                self.assertIn(f"return code {return_code}", diagnostic)
                self.assertIn("command output was withheld", diagnostic)
                self.assertNotIn("arbitrary-secret-value", diagnostic)
                self.assertNotIn("command-input-secret", diagnostic)
                self.assertNotIn("Authorization", diagnostic)
                self.assertNotIn("\x1b", diagnostic)

    def test_invalid_command_output_bytes_reach_safe_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            command = Path(directory) / "invalid-output.py"
            command.write_text(
                "import sys\n"
                "sys.stdout.buffer.write(b'\\xffarbitrary-secret-value')\n"
                "raise SystemExit(33)\n",
                encoding="utf-8",
            )
            with self.assertRaises(STATE.PublicationError) as raised:
                STATE.run_mutation([sys.executable, str(command)])

        diagnostic = str(raised.exception)
        self.assertIn("mutation command rejected (return code 33)", diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)

    def test_malformed_successful_output_fails_closed_at_command_boundary(self) -> None:
        secret = b"arbitrary-secret-value"
        completed = subprocess.CompletedProcess([], 0, b"\xff" + secret, b"")
        cases = (
            (
                STATE.run_read,
                STATE.CommandReadError,
                "read command returned malformed successful output",
            ),
            (
                STATE.run_mutation,
                STATE.MutationAmbiguousError,
                "mutation outcome is unknown",
            ),
        )

        for runner, error_type, classification in cases:
            with self.subTest(classification=classification):
                with (
                    mock.patch.object(STATE.subprocess, "run", return_value=completed),
                    self.assertRaises(error_type) as raised,
                ):
                    runner(["gh", "synthetic"])

                diagnostic = str(raised.exception)
                self.assertIn(classification, diagnostic)
                self.assertIn("strict UTF-8", diagnostic)
                self.assertNotIn(secret.decode(), diagnostic)
                self.assertNotIn("codec", diagnostic)

    def test_malformed_nonzero_output_keeps_safe_process_metadata(self) -> None:
        completed = subprocess.CompletedProcess(
            [], 47, b"\xffarbitrary-secret-value", b"\xfeAuthorization"
        )
        cases = (
            (STATE.run_read, STATE.CommandReadError, "read command rejected"),
            (STATE.run_mutation, STATE.CommandRejectedError, "mutation command rejected"),
        )

        for runner, error_type, classification in cases:
            with self.subTest(classification=classification):
                with (
                    mock.patch.object(STATE.subprocess, "run", return_value=completed),
                    self.assertRaises(error_type) as raised,
                ):
                    runner(["gh", "synthetic"])

                diagnostic = str(raised.exception)
                self.assertIn(classification, diagnostic)
                self.assertIn("return code 47", diagnostic)
                self.assertNotIn("arbitrary-secret-value", diagnostic)
                self.assertNotIn("Authorization", diagnostic)

    def test_recovery_reuses_valid_existing_read_authority(self) -> None:
        diagnostics = (
            STATE.read_failure_diagnostic(
                STATE.CommandReadError(timeout_seconds=STATE.READ_TIMEOUT_SECONDS)
            ),
            STATE.read_failure_diagnostic(STATE.PublicationError("synthetic")),
        )
        skill = SCRIPTS.parent.joinpath("SKILL.md").read_text(encoding="utf-8")

        for text in (*diagnostics, skill):
            normalized = " ".join(text.split())
            with self.subTest(text=normalized[:40]):
                self.assertIn(
                    "existing read authority while it remains valid", normalized
                )
                self.assertIn(
                    "new authority only if the target or action is outside",
                    normalized,
                )
                self.assertNotIn("separately authorized read", normalized)

    def test_audit_procedure_requires_validated_observation_before_comparison(
        self,
    ) -> None:
        skill = SCRIPTS.parent.joinpath("SKILL.md").read_text(encoding="utf-8")
        normalized = " ".join(skill.split())

        self.assertIn(
            "Only a complete, structurally valid live PR observation reaches receipt "
            "comparison",
            normalized,
        )
        self.assertIn(
            "Valid identity, text, and state differences are drift", normalized
        )
        self.assertIn(
            "Invalid JSON, duplicate or non-finite JSON, and incomplete or malformed "
            "fields are unavailable",
            normalized,
        )
        self.assertIn(
            "Required observation strings must be exact UTF-8-encodable Unicode "
            "scalar text before comparison, hashing, or serialization",
            normalized,
        )
        self.assertIn(
            "Malformed zero-exit create output, including an invalid PR identifier, "
            "follows that same one-read nonce recovery path",
            normalized,
        )

    def test_malformed_recovery_read_keeps_its_safe_classification(self) -> None:
        diagnostic = STATE.read_failure_diagnostic(
            STATE.CommandReadError(malformed_output=True)
        )

        self.assertIn(
            "post-mutation reread returned malformed successful output", diagnostic
        )
        self.assertIn("strict UTF-8", diagnostic)
        self.assertIn("existing read authority while it remains valid", diagnostic)

    def test_local_validator_failures_have_validation_specific_guidance(self) -> None:
        hostile = b"\xffAuthorization: Bearer arbitrary-secret-value\x1b[31m"
        failures = (
            subprocess.CompletedProcess([], 51, hostile, hostile),
            subprocess.CompletedProcess([], 0, hostile, hostile),
            subprocess.TimeoutExpired(
                ["validator"], STATE.READ_TIMEOUT_SECONDS, output=hostile, stderr=hostile
            ),
        )

        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                with (
                    mock.patch.object(STATE.subprocess, "run", side_effect=[failure]),
                    self.assertRaisesRegex(
                        STATE.PublicationError, "candidate validation"
                    ) as raised,
                ):
                    PUBLICATION_SUPPORT.validate_pr_content(
                        "body",
                        "acme/app",
                        1,
                        "title",
                        Path("/absolute/review-input.json"),
                    )

                diagnostic = str(raised.exception)
                self.assertIn("trusted executable ancestry", diagnostic)
                self.assertIn("temporary-directory availability", diagnostic)
                self.assertNotIn("authentication", diagnostic)
                self.assertNotIn("read access", diagnostic)
                self.assertNotIn("repository identity", diagnostic)
                self.assertNotIn("arbitrary-secret-value", diagnostic)
                self.assertNotIn("Authorization", diagnostic)
                self.assertNotIn("\x1b", diagnostic)

    def test_missing_local_validator_diagnostic_is_value_free(self) -> None:
        hidden_path = Path("/synthetic/arbitrary-secret-value/validator.py")
        with (
            mock.patch.object(PUBLICATION_SUPPORT, "VALIDATOR", hidden_path),
            self.assertRaisesRegex(
                STATE.PublicationError,
                "candidate validation is unavailable; validator executable is missing",
            ) as raised,
        ):
            PUBLICATION_SUPPORT.validate_pr_content(
                "body",
                "acme/app",
                1,
                "title",
                Path("/absolute/review-input.json"),
            )

        diagnostic = str(raised.exception)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn(str(hidden_path), diagnostic)
        self.assertNotIn("authentication", diagnostic)
        self.assertNotIn("read access", diagnostic)

    def test_validator_broad_os_failure_has_unknown_process_outcome(self) -> None:
        launch_error = OSError("/synthetic/arbitrary-secret-value/validator.py")
        with (
            mock.patch.object(STATE.subprocess, "run", side_effect=launch_error),
            self.assertRaisesRegex(
                STATE.PublicationError,
                "candidate validation failed during process launch or communication",
            ) as raised,
        ):
            PUBLICATION_SUPPORT.validate_pr_content(
                "body",
                "acme/app",
                1,
                "title",
                Path("/absolute/review-input.json"),
            )

        diagnostic = str(raised.exception)
        self.assertIn("validation process started is unknown", diagnostic)
        self.assertIs(raised.exception.__cause__, launch_error)
        self.assertIn("trusted executable ancestry", diagnostic)
        self.assertIn("temporary-directory availability", diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("authentication", diagnostic)

        self.assertNotIn("read access", diagnostic)

    def test_validator_local_preparation_failure_never_starts(self) -> None:
        with (
            mock.patch.object(STATE.subprocess, "run") as run,
            self.assertRaisesRegex(
                STATE.PublicationError,
                "candidate validation could not be prepared locally",
            ) as raised,
        ):
            PUBLICATION_SUPPORT.validate_pr_content(
                "secret-\ud800",
                "acme/app",
                1,
                "title",
                Path("/absolute/review-input.json"),
            )

        diagnostic = str(raised.exception)
        self.assertIn("no validation command started", diagnostic)
        self.assertIsInstance(raised.exception.__cause__, UnicodeEncodeError)
        self.assertNotIn("secret", diagnostic)
        self.assertNotIn("Traceback", diagnostic)
        run.assert_not_called()


class ReviewablePrFixture(unittest.TestCase):
    repository = "acme/app"
    base = "main"
    head = "fork-owner:widget"
    head_owner = "fork-owner"
    head_repository = "fork-owner/app-fork"
    base_oid = "a" * 40
    head_oid = "b" * 40
    title = "feat: widget"
    pr_number = 42
    url = "https://github.com/acme/app/pull/42"
    nonce = "nonce-42"
    review_input_schema_version = 2
    review_input_sha256 = "d" * 64

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.template_path = Path(self.temporary_directory.name) / "body.md"
        self.receipt_directory = Path(self.temporary_directory.name) / "receipts"
        self.template = (
            "<details>\n"
            f"https://github.com/acme/app/pull/{CREATE.PR_NUMBER_TOKEN}/files\n"
            "</details>\n"
        )
        self.template_path.write_text(self.template, encoding="utf-8")
        self.body = self.template.replace(CREATE.PR_NUMBER_TOKEN, str(self.pr_number))
        self.transport_body = CREATE._transport_body(self.nonce)
        self._create_review_input = mock.patch.object(
            CREATE,
            "_review_input",
            return_value=(self.review_input_schema_version, self.review_input_sha256),
        ).start()
        self._update_review_input = mock.patch.object(
            UPDATE,
            "_bind_review_input",
            return_value=(self.review_input_schema_version, self.review_input_sha256),
        ).start()
        admitted_review_input = SimpleNamespace(raw={"pr_number": self.pr_number})
        self._update_admission = mock.patch.object(
            UPDATE, "_admit_review_input", return_value=admitted_review_input
        ).start()
        self._audit_admission = mock.patch.object(
            AUDIT, "_admit_review_input", return_value=admitted_review_input
        ).start()
        self.addCleanup(self._create_review_input.stop)
        self.addCleanup(self._update_review_input.stop)
        self.addCleanup(self._update_admission.stop)
        self.addCleanup(self._audit_admission.stop)
        self._create_candidate = mock.patch.object(
            CREATE, "_build_candidate", side_effect=self._fixture_candidate
        ).start()
        self._update_candidate = mock.patch.object(
            UPDATE, "_build_candidate", side_effect=self._fixture_candidate
        ).start()
        self._create_required_review = mock.patch.object(
            CREATE,
            "_validate_required_review",
            side_effect=self._fixture_review,
        ).start()
        self._update_required_review = mock.patch.object(
            UPDATE,
            "_validate_required_review",
            side_effect=self._fixture_review,
        ).start()
        self.addCleanup(self._create_candidate.stop)
        self.addCleanup(self._update_candidate.stop)
        self.addCleanup(self._create_required_review.stop)
        self.addCleanup(self._update_required_review.stop)

    def _fixture_candidate(self, **kwargs: object):
        operation = str(kwargs["operation"])
        review_input_raw = Path(kwargs["review_input_path"]).read_bytes()
        selected_specialists = kwargs.get("selected_specialists", [])
        review_input = {
            "schema_version": self.review_input_schema_version,
            "raw_sha256": hashlib.sha256(review_input_raw).hexdigest(),
            "content_sha256": self.review_input_sha256,
        }
        value = {
            "schema_version": 1,
            "contract": "mergecraft-publication-candidate-v1",
            "operation": operation,
            "repository": kwargs["repository"],
            "pr_number": kwargs["pr_number"],
            "base": {"ref": kwargs["base"], "oid": kwargs["base_oid"]},
            "head": {
                "ref": kwargs["head"],
                "oid": kwargs["head_oid"],
                "owner": kwargs["head_owner"],
                "repository": kwargs["head_repository"],
            },
            "title": kwargs["title"],
            "body_source": REQUIRED_REVIEW.body_source_binding(
                kind=str(kwargs["body_source_kind"]),
                raw=kwargs["body_source_raw"],
                published=str(kwargs["published_body"]),
                render_contract=(
                    "mergecraft-pr-number-token-render-v1"
                    if kwargs["body_source_kind"] == "template"
                    else "literal-utf8-v1"
                ),
            ),
            "review_input": review_input,
            "publication_profile": {
                "contract": "mergecraft-publication-profile-v1",
                "review_mode": kwargs["review_mode"],
                "selected_specialists": selected_specialists,
            },
        }
        digest = hashlib.sha256(RequiredReviewTests.canonical(value)).hexdigest()
        return REQUIRED_REVIEW.PublicationCandidate(
            value=value,
            content_sha256=digest,
            candidate_identity={
                "kind": "mergecraft-publication-candidate-v1",
                "value": f"sha256:{digest}",
                "content_sha256": digest,
            },
            review_input_identity=REQUIRED_REVIEW._identity_for(
                "mergecraft-review-input-v1", review_input
            ),
            requirements_identity=REQUIRED_REVIEW._identity_for(
                "mergecraft-required-publication-review-profile-v2",
                REQUIRED_REVIEW._required_profile(selected_specialists),
            ),
            body_source_raw=kwargs["body_source_raw"],
            published_body=str(kwargs["published_body"]),
        )

    @staticmethod
    def _fixture_review(**kwargs: object):
        candidate = kwargs["candidate"]
        observation = None
        if kwargs["review_mode"] == "required":
            observation = REQUIRED_REVIEW.RequiredReviewObservation(
                launch_envelope_sha256="1" * 64,
                generation="sha256-" + "2" * 64,
                active_record_sha256="3" * 64,
                trust_context_sha256="4" * 64,
                bundle_sha256="5" * 64,
                tricritical_manifest_sha256="6" * 64,
                tricritical_projection_sha256="7" * 64,
            )
        return transition_review(
            kwargs["review_mode"], candidate.content_sha256, observation
        )

    @property
    def expected(self):
        return CREATE.ExpectedIdentity(
            repository=self.repository,
            pr_number=self.pr_number,
            base=self.base,
            base_oid=self.base_oid,
            head=self.head,
            head_oid=self.head_oid,
            head_owner=self.head_owner,
            head_repository=self.head_repository,
        )

    def stored(
        self,
        *,
        body: str | None = None,
        title: str | None = None,
        is_draft: bool = True,
        state: str = "OPEN",
        **overrides: object,
    ) -> dict[str, object]:
        value: dict[str, object] = {
            "number": self.pr_number,
            "url": self.url,
            "title": self.title if title is None else title,
            "body": self.body if body is None else body,
            "baseRefName": self.base,
            "baseRefOid": self.base_oid,
            "headRefName": "widget",
            "headRefOid": self.head_oid,
            "headRepositoryOwner": {"login": self.head_owner},
            "headRepository": {"nameWithOwner": self.head_repository},
            "isDraft": is_draft,
            "state": state,
        }
        value.update(overrides)
        return value

    def transport(self, **overrides: object) -> dict[str, object]:
        return self.stored(body=self.transport_body, **overrides)

    def publish(self):
        return CREATE.publish(
            repository=self.repository,
            base=self.base,
            base_oid=self.base_oid,
            head=self.head,
            head_oid=self.head_oid,
            head_owner=self.head_owner,
            head_repository=self.head_repository,
            title=self.title,
            template_path=self.template_path,
            review_input_path=self.template_path,
            review_mode="not-required",
            review_bundle_root=None,
            selected_specialists=[],
            receipt_directory=self.receipt_directory,
        )

    @staticmethod
    def invoke_cli(module, arguments: list[str]) -> tuple[int, str]:
        stderr = io.StringIO()
        with (
            mock.patch.object(sys, "argv", [str(module.__file__), *arguments]),
            mock.patch.object(sys, "stderr", stderr),
        ):
            return module.main(), stderr.getvalue()

    @staticmethod
    def hostile_command_output() -> tuple[str, str]:
        secret = "arbitrary-secret-value"
        stdout = (
            f"https://user:{secret}@example.test/path?token={secret}\n"
            f"Authorization: Bearer {secret}\n" + "x" * (1024 * 1024)
        )
        stderr = f"X-Api-Key: {secret}\x00\x1b[31m\rforged diagnostic\n"
        return stdout, stderr

    def write_review_input_bytes(self, name: str, payload: bytes) -> Path:
        path = Path(self.temporary_directory.name) / f"{name}-review-input.json"
        path.write_bytes(payload)
        return path

    def write_valid_review_input(
        self, name: str, *, body: str, token_bearing: bool = False
    ) -> Path:
        pr_number: int | str = (
            REVIEW_INPUT.PR_NUMBER_TOKEN if token_bearing else self.pr_number
        )
        manifest_body = self.template if token_bearing else body
        baseline = (
            {
                "mode": "new",
                "title_sha256": None,
                "body_sha256": None,
                "fragments": [],
            }
            if token_bearing
            else {
                "mode": "existing",
                "title_sha256": self.digest(self.title),
                "body_sha256": self.digest(self.body),
                "fragments": [
                    {
                        "id": "body",
                        "text": self.body,
                        "sha256": self.digest(self.body),
                        "disposition": "retain",
                        "replacement": None,
                        "reason": None,
                    }
                ],
            }
        )
        value: dict[str, object] = {
            "version": REVIEW_INPUT.VERSION,
            "repository": self.repository,
            "pr_number": pr_number,
            "base": {"ref": self.base, "oid": self.base_oid},
            "head": {
                "ref": self.head,
                "oid": self.head_oid,
                "owner": self.head_owner,
                "repository": self.head_repository,
            },
            "candidate": {
                "title": self.title,
                "body_sha256": self.digest(manifest_body),
            },
            "git_diff": [
                {
                    "source_path": None,
                    "target_path": "src/widget.py",
                    "operation": "modified",
                    "additions": 1,
                    "deletions": 0,
                    "binary": False,
                }
            ],
            "diff": [
                {
                    "category": "IMPL",
                    "operation": "ATOMIC",
                    "source_path": None,
                    "target_path": "src/widget.py",
                    "additions": 1,
                    "deletions": 0,
                }
            ],
            "stack": [],
            "baseline": baseline,
        }
        value["content_sha256"] = self.digest(
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
        )
        return self.write_review_input_bytes(
            name,
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8"),
        )


class CreateReviewablePrTests(ReviewablePrFixture):
    def required_publish(self):
        return CREATE.publish(
            repository=self.repository,
            base=self.base,
            base_oid=self.base_oid,
            head=self.head,
            head_oid=self.head_oid,
            head_owner=self.head_owner,
            head_repository=self.head_repository,
            title=self.title,
            template_path=self.template_path,
            review_input_path=self.template_path,
            review_mode="required",
            review_bundle_root=Path("/absolute/review-bundle"),
            selected_specialists=[],
            receipt_directory=self.receipt_directory,
        )

    def test_create_local_input_failures_are_value_free_and_chained(self) -> None:
        hostile_path = Path("/synthetic/Authorization: arbitrary-secret-value/body.md")
        read_error = OSError("Authorization: arbitrary-secret-value")
        with (
            mock.patch.object(Path, "read_bytes", side_effect=read_error),
            self.assertRaises(CREATE.PublicationError) as caught,
        ):
            CREATE._body_template(hostile_path)

        diagnostic = str(caught.exception)
        self.assertEqual(
            diagnostic,
            "cannot read body template; check the local path and read permissions",
        )
        self.assertIs(caught.exception.__cause__, read_error)
        self.assertNotIn(str(hostile_path), diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("authentication", diagnostic)

        decode_error = b"\xffAuthorization: arbitrary-secret-value"
        with (
            mock.patch.object(Path, "read_bytes", return_value=decode_error),
            self.assertRaises(CREATE.PublicationError) as caught,
        ):
            CREATE._body_template(hostile_path)
        self.assertEqual(str(caught.exception), "body template must be valid UTF-8")
        self.assertIsInstance(caught.exception.__cause__, UnicodeDecodeError)

        with (
            mock.patch.object(Path, "read_bytes", side_effect=read_error),
            mock.patch.object(CREATE, "_create") as create,
        ):
            status, cli_diagnostic = self.invoke_cli(
                CREATE,
                [
                    "--repository",
                    self.repository,
                    "--base",
                    self.base,
                    "--base-oid",
                    self.base_oid,
                    "--head",
                    self.head,
                    "--head-oid",
                    self.head_oid,
                    "--head-owner",
                    self.head_owner,
                    "--head-repository",
                    self.head_repository,
                    "--title",
                    self.title,
                    "--body-template",
                    str(hostile_path),
                    "--review-input",
                    str(self.template_path),
                    "--review-mode",
                    "not-required",
                    "--selected-specialists",
                    "[]",
                ],
            )

        self.assertEqual(status, 1)
        self.assertIn("cannot read body template", cli_diagnostic)
        self.assertNotIn(str(hostile_path), cli_diagnostic)
        self.assertNotIn("arbitrary-secret-value", cli_diagnostic)
        self.assertNotIn("Traceback", cli_diagnostic)
        create.assert_not_called()

        review_input = Path(self.temporary_directory.name) / "hostile-review.json"
        hostile_key = "Authorization: arbitrary-secret-value"
        review_input.write_text(
            '{"version": 2, "' + hostile_key + '": 1, "' + hostile_key + '": 2}',
            encoding="utf-8",
        )
        with self.assertRaises(CREATE.PublicationError) as caught:
            CREATE_REVIEW_INPUT(
                review_input,
                repository=self.repository,
                base=self.base,
                base_oid=self.base_oid,
                head=self.head,
                head_oid=self.head_oid,
                head_owner=self.head_owner,
                head_repository=self.head_repository,
                title=self.title,
                body=self.body,
                pr_number=self.pr_number,
            )

        diagnostic = str(caught.exception)
        self.assertEqual(
            diagnostic,
            "review input could not be admitted; check the local file and regenerate "
            "it for this exact publication candidate",
        )
        self.assertIsInstance(caught.exception.__cause__, CREATE.ReviewInputError)
        self.assertNotIn(hostile_key, diagnostic)
        self.assertNotIn("authentication", diagnostic)

        missing_review_input = hostile_path.with_name("review-input.json")
        with self.assertRaises(CREATE.PublicationError) as caught:
            CREATE_REVIEW_INPUT(
                missing_review_input,
                repository=self.repository,
                base=self.base,
                base_oid=self.base_oid,
                head=self.head,
                head_oid=self.head_oid,
                head_owner=self.head_owner,
                head_repository=self.head_repository,
                title=self.title,
                body=self.body,
                pr_number=self.pr_number,
            )
        diagnostic = str(caught.exception)
        self.assertIn("review input could not be admitted", diagnostic)
        self.assertIsInstance(caught.exception.__cause__, CREATE.ReviewInputError)
        self.assertIsInstance(caught.exception.__cause__.__cause__, OSError)
        self.assertNotIn(str(missing_review_input), diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)

    def test_create_cli_duplicate_review_key_is_value_free(self) -> None:
        hostile_key = "Authorization: arbitrary-secret-value"
        review_input = Path(self.temporary_directory.name) / "hostile-review.json"
        review_input.write_text(
            '{"version": 2, "' + hostile_key + '": 1, "' + hostile_key + '": 2}',
            encoding="utf-8",
        )
        RECEIPTS.prepare_receipt_store(self.receipt_directory)
        with (
            mock.patch.object(
                CREATE, "_build_candidate", side_effect=self._fixture_candidate
            ),
            mock.patch.object(
                CREATE,
                "_validate_required_review",
                side_effect=self._fixture_review,
            ),
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(
                CREATE, "_review_input", side_effect=CREATE_REVIEW_INPUT
            ),
            mock.patch.object(
                CREATE, "prepare_receipt_store", return_value=self.receipt_directory
            ),
            mock.patch.object(
                CREATE, "_create", return_value=(self.pr_number, self.url)
            ) as create,
            mock.patch.object(CREATE, "_stored_pr", return_value=self.transport()),
            mock.patch.object(CREATE, "_install_canonical_draft") as canonical_edit,
        ):
            status, diagnostic = self.invoke_cli(
                CREATE,
                [
                    "--repository",
                    self.repository,
                    "--base",
                    self.base,
                    "--base-oid",
                    self.base_oid,
                    "--head",
                    self.head,
                    "--head-oid",
                    self.head_oid,
                    "--head-owner",
                    self.head_owner,
                    "--head-repository",
                    self.head_repository,
                    "--title",
                    self.title,
                    "--body-template",
                    str(self.template_path),
                    "--review-input",
                    str(review_input),
                    "--review-mode",
                    "not-required",
                    "--selected-specialists",
                    "[]",
                ],
            )

        self.assertEqual(status, 1)
        self.assertIn("review input could not be admitted", diagnostic)
        self.assertNotIn(hostile_key, diagnostic)
        self.assertNotIn("Traceback", diagnostic)
        create.assert_not_called()
        canonical_edit.assert_not_called()

    def test_create_api_and_cli_bound_real_review_input_admission_failures(
        self,
    ) -> None:
        hostile = "Authorization: arbitrary-secret-value"
        for name, payload in malformed_review_input_payloads():
            review_input = self.write_review_input_bytes(name, payload)
            with (
                self.subTest(case=name, entrypoint="api"),
                self.assertRaises(CREATE.PublicationError) as caught,
            ):
                CREATE_REVIEW_INPUT(
                    review_input,
                    repository=self.repository,
                    base=self.base,
                    base_oid=self.base_oid,
                    head=self.head,
                    head_oid=self.head_oid,
                    head_owner=self.head_owner,
                    head_repository=self.head_repository,
                    title=self.title,
                    body=self.body,
                    pr_number=self.pr_number,
                )
            self.assertEqual(
                str(caught.exception),
                "review input could not be admitted; check the local file and "
                "regenerate it for this exact publication candidate",
            )
            self.assertIsInstance(caught.exception.__cause__, CREATE.ReviewInputError)
            self.assertIsNotNone(caught.exception.__cause__.__cause__)

            RECEIPTS.prepare_receipt_store(self.receipt_directory)
            with (
                self.subTest(case=name, entrypoint="cli"),
                mock.patch.object(CREATE, "_validate"),
                mock.patch.object(CREATE, "_review_input", side_effect=CREATE_REVIEW_INPUT),
                mock.patch.object(
                    CREATE,
                    "prepare_receipt_store",
                    return_value=self.receipt_directory,
                ),
                mock.patch.object(CREATE, "_create") as create,
            ):
                status, diagnostic = self.invoke_cli(
                    CREATE,
                    [
                        "--repository",
                        self.repository,
                        "--base",
                        self.base,
                        "--base-oid",
                        self.base_oid,
                        "--head",
                        self.head,
                        "--head-oid",
                        self.head_oid,
                        "--head-owner",
                        self.head_owner,
                        "--head-repository",
                        self.head_repository,
                        "--title",
                        self.title,
                        "--body-template",
                        str(self.template_path),
                        "--review-input",
                        str(review_input),
                        "--review-mode",
                        "not-required",
                        "--selected-specialists",
                        "[]",
                    ],
                )

            self.assertEqual(status, 1)
            self.assertIn("review input could not be admitted", diagnostic)
            self.assertNotIn(hostile, diagnostic)
            self.assertNotIn(str(review_input), diagnostic)
            self.assertNotIn("Traceback", diagnostic)
            create.assert_not_called()
            self.assertEqual(
                RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
            )

    def test_initial_create_process_and_recovery_failure_matrix(self) -> None:
        failures = (
            (
                "local-preparation",
                STATE.MutationPreparationError,
                "initial create command could not be prepared locally; no process "
                "started and no target mutation ran",
            ),
            (
                "nonzero",
                lambda: STATE.CommandRejectedError(31),
                "initial create command returned nonzero",
            ),
            (
                "timeout",
                lambda: STATE.MutationAmbiguousError(
                    "Authorization: arbitrary-secret-value",
                    timeout_seconds=STATE.MUTATION_TIMEOUT_SECONDS,
                ),
                "initial create command timed out after a possible mutation",
            ),
            (
                "malformed-zero-exit",
                lambda: STATE.MutationAmbiguousError(
                    "Authorization: arbitrary-secret-value", malformed_output=True
                ),
                "initial create command exited zero with malformed output",
            ),
        )
        recovery_cases = (
            (
                "empty",
                [],
                "nonce recovery observed no open PR for the exact head/base",
            ),
            (
                "nonmatching",
                [self.stored(body="different transport body")],
                "nonce recovery observed open PR state, but none matched the exact "
                "nonce, identity, title, body, and draft state",
            ),
            (
                "multiple",
                [
                    self.transport(),
                    self.transport(
                        number=43,
                        url="https://github.com/acme/app/pull/43",
                    ),
                ],
                "nonce recovery observed multiple exact nonce-tagged drafts",
            ),
            (
                "unavailable",
                STATE.CommandReadError(return_code=42),
                "nonce recovery was unavailable",
            ),
        )
        for failure_name, failure_factory, process_fact in failures:
            for recovery_name, recovery, recovery_fact in recovery_cases:
                failure = failure_factory()
                with (
                    self.subTest(process=failure_name, recovery=recovery_name),
                    mock.patch.object(
                        CREATE, "_matching_head_prs", side_effect=[[], recovery]
                    ) as reads,
                    mock.patch.object(
                        CREATE, "_run_mutation", side_effect=failure
                    ) as mutate,
                    self.assertRaises(CREATE.PublicationError) as caught,
                ):
                    CREATE._create(
                        repository=self.repository,
                        base=self.base,
                        base_oid=self.base_oid,
                        head=self.head,
                        head_oid=self.head_oid,
                        head_owner=self.head_owner,
                        head_repository=self.head_repository,
                        title=self.title,
                        nonce=self.nonce,
                    )

                diagnostic = str(caught.exception)
                self.assertIn(process_fact, diagnostic)
                self.assertIn(recovery_fact, diagnostic)
                self.assertIn("canonical provenance was not minted", diagnostic)
                self.assertIn("no canonical receipt was written", diagnostic)
                self.assertIn(
                    "no automatic retry or rollback was attempted", diagnostic
                )
                self.assertNotIn("arbitrary-secret-value", diagnostic)
                self.assertNotIn("Authorization", diagnostic)
                self.assertIs(caught.exception.__cause__, failure)
                self.assertEqual(mutate.call_count, 1)
                self.assertEqual(reads.call_count, 2)
                if recovery_name == "unavailable":
                    self.assertIs(caught.exception.reread_error, recovery)

    def test_initial_create_post_start_io_failure_keeps_unknown_outcome(self) -> None:
        events: list[str] = []
        io_error = OSError("Authorization: arbitrary-secret-value")
        with (
            mock.patch.object(
                CREATE, "_matching_head_prs", side_effect=[[], []]
            ) as reads,
            mock.patch.object(
                STATE.subprocess,
                "Popen",
                post_start_io_failure_popen(events, io_error),
            ),
            self.assertRaises(CREATE.PublicationError) as caught,
        ):
            CREATE._create(
                repository=self.repository,
                base=self.base,
                base_oid=self.base_oid,
                head=self.head,
                head_oid=self.head_oid,
                head_owner=self.head_owner,
                head_repository=self.head_repository,
                title=self.title,
                nonce=self.nonce,
            )

        diagnostic = str(caught.exception)
        self.assertIn("process launch or communication", diagnostic)
        self.assertIn("process started is unknown", diagnostic)
        self.assertIn(
            "nonce recovery observed no open PR for the exact head/base", diagnostic
        )
        self.assertIn("canonical provenance was not minted", diagnostic)
        self.assertIn("no canonical receipt was written", diagnostic)
        self.assertIn("no automatic retry or rollback was attempted", diagnostic)
        self.assertNotIn("no process started", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertIsInstance(caught.exception.__cause__, STATE.MutationAmbiguousError)
        self.assertIs(caught.exception.__cause__.__cause__, io_error)
        self.assertEqual(reads.call_count, 2)
        self.assertEqual(
            events,
            [
                "process-created",
                "communicate-entered",
                "process-killed",
                "process-waited",
            ],
        )

    def test_initial_create_local_preparation_failure_proves_no_process_started(
        self,
    ) -> None:
        with (
            mock.patch.object(
                CREATE, "_matching_head_prs", side_effect=[[], []]
            ) as reads,
            mock.patch.object(STATE.subprocess, "run") as run,
            self.assertRaises(CREATE.PublicationError) as caught,
        ):
            CREATE._create(
                repository=self.repository,
                base=self.base,
                base_oid=self.base_oid,
                head=self.head,
                head_oid=self.head_oid,
                head_owner=self.head_owner,
                head_repository=self.head_repository,
                title="Authorization: secret-\ud800",
                nonce=self.nonce,
            )

        diagnostic = str(caught.exception)
        preparation_error = caught.exception.__cause__
        self.assertIsInstance(preparation_error, STATE.MutationPreparationError)
        self.assertIsInstance(preparation_error.__cause__, UnicodeEncodeError)
        self.assertIn("could not be prepared locally", diagnostic)
        self.assertIn("no process started and no target mutation ran", diagnostic)
        self.assertIn(
            "nonce recovery observed no open PR for the exact head/base", diagnostic
        )
        self.assertIn("canonical provenance was not minted", diagnostic)
        self.assertIn("no canonical receipt was written", diagnostic)
        self.assertIn("no automatic retry or rollback was attempted", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertNotIn("secret", diagnostic)
        self.assertEqual(reads.call_count, 2)
        run.assert_not_called()

    def test_initial_create_unique_recovery_preserves_continuation_and_counts(
        self,
    ) -> None:
        failures = (
            STATE.MutationPreparationError(),
            STATE.CommandRejectedError(31),
            STATE.MutationAmbiguousError(
                "private timeout", timeout_seconds=STATE.MUTATION_TIMEOUT_SECONDS
            ),
            STATE.MutationAmbiguousError("private output", malformed_output=True),
        )
        for failure in failures:
            with (
                self.subTest(failure=type(failure).__name__),
                mock.patch.object(
                    CREATE,
                    "_matching_head_prs",
                    side_effect=[[], [self.transport()]],
                ) as reads,
                mock.patch.object(
                    CREATE, "_run_mutation", side_effect=failure
                ) as mutate,
            ):
                recovered = CREATE._create(
                    repository=self.repository,
                    base=self.base,
                    base_oid=self.base_oid,
                    head=self.head,
                    head_oid=self.head_oid,
                    head_owner=self.head_owner,
                    head_repository=self.head_repository,
                    title=self.title,
                    nonce=self.nonce,
                )

            self.assertEqual(recovered, (self.pr_number, self.url))
            self.assertEqual(mutate.call_count, 1)
            self.assertEqual(reads.call_count, 2)

    def test_canonical_create_edit_cleanup_failure_retains_zero_exit_and_reread(
        self,
    ) -> None:
        class CleanupFailingTemporary:
            name = "/synthetic/private/arbitrary-secret-value/body.md"

            def write(self, value: bytes) -> int:
                return len(value)

            def flush(self) -> None:
                return None

            def close(self) -> None:
                raise OSError("Authorization: arbitrary-secret-value")

        with (
            mock.patch.object(
                PUBLICATION_SUPPORT.tempfile,
                "NamedTemporaryFile",
                return_value=CleanupFailingTemporary(),
            ),
            mock.patch.object(
                CREATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as mutate,
            mock.patch.object(
                CREATE, "_stored_pr", return_value=self.stored()
            ) as reread,
            self.assertRaises(CREATE.PublicationError) as caught,
        ):
            CREATE._install_canonical_draft(
                expected=self.expected,
                title=self.title,
                transport_body=self.transport_body,
                body=self.body,
                before=self.transport(),
            )

        diagnostic = str(caught.exception)
        self.assertIn("canonical edit command exited zero", diagnostic)
        self.assertIn("private body snapshot cleanup failed", diagnostic)
        self.assertIn("exact intended state was observed", diagnostic)
        self.assertIn("canonical provenance was not minted", diagnostic)
        self.assertIn("do not retry", diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertEqual(mutate.call_count, 1)
        self.assertEqual(reread.call_count, 1)

    def test_initial_create_cleanup_failure_recovers_once_without_success(self) -> None:
        class CleanupFailingTemporary:
            name = "/synthetic/private/arbitrary-secret-value/body.md"

            def write(self, value: bytes) -> int:
                return len(value)

            def flush(self) -> None:
                return None

            def close(self) -> None:
                raise OSError("Authorization: arbitrary-secret-value")

        with (
            mock.patch.object(CREATE, "_matching_head_prs", return_value=[]),
            mock.patch.object(
                CREATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, self.url, ""),
            ) as mutate,
            mock.patch.object(
                CREATE,
                "_recover_created",
                return_value=(
                    (self.pr_number, self.url),
                    "nonce recovery observed one exact nonce-tagged draft",
                ),
            ) as recover,
            mock.patch.object(
                PUBLICATION_SUPPORT.tempfile,
                "NamedTemporaryFile",
                return_value=CleanupFailingTemporary(),
            ),
            self.assertRaises(CREATE.PublicationError) as caught,
        ):
            CREATE._create(
                repository=self.repository,
                base=self.base,
                base_oid=self.base_oid,
                head=self.head,
                head_oid=self.head_oid,
                head_owner=self.head_owner,
                head_repository=self.head_repository,
                title=self.title,
                nonce=self.nonce,
            )

        diagnostic = str(caught.exception)
        self.assertIn("initial create command exited zero", diagnostic)
        self.assertIn("one exact nonce-tagged draft was found", diagnostic)
        self.assertIn("private body snapshot cleanup failed", diagnostic)
        self.assertIn("no canonical receipt was written", diagnostic)
        self.assertIn("no automatic retry or rollback was attempted", diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertEqual(mutate.call_count, 1)
        self.assertEqual(recover.call_count, 1)

    def test_initial_create_cleanup_failure_without_recovered_draft_keeps_cause(
        self,
    ) -> None:
        cleanup_error = OSError("Authorization: arbitrary-secret-value")

        class CleanupFailingTemporary:
            name = "/synthetic/private/arbitrary-secret-value/body.md"

            def write(self, value: bytes) -> int:
                return len(value)

            def flush(self) -> None:
                return None

            def close(self) -> None:
                raise cleanup_error

        with (
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
            mock.patch.object(CREATE, "_matching_head_prs", side_effect=[[], []]) as reads,
            mock.patch.object(
                CREATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, self.url, ""),
            ) as mutate,
            mock.patch.object(CREATE, "record_verified_publication") as record,
            mock.patch.object(
                PUBLICATION_SUPPORT.tempfile,
                "NamedTemporaryFile",
                return_value=CleanupFailingTemporary(),
            ),
            self.assertRaises(CREATE.PublicationError) as caught,
        ):
            self.publish()

        diagnostic = str(caught.exception)
        self.assertIn("initial create command exited zero", diagnostic)
        self.assertIn("private body snapshot cleanup failed", diagnostic)
        self.assertIn(
            "nonce recovery observed no open PR for the exact head/base", diagnostic
        )
        self.assertIn("no automatic retry or rollback was attempted", diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertNotIn("OSError", diagnostic)
        self.assertIsInstance(caught.exception.__cause__, CREATE.BodySnapshotError)
        self.assertIs(caught.exception.__cause__.__cause__, cleanup_error)
        self.assertEqual(mutate.call_count, 1)
        self.assertEqual(reads.call_count, 2)
        record.assert_not_called()

    def test_required_create_remote_drift_after_review_blocks_canonical_edit(
        self,
    ) -> None:
        drifted = self.transport(title="reviewer changed title")
        with (
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
            mock.patch.object(CREATE, "_create", return_value=(42, self.url)),
            mock.patch.object(
                CREATE, "_stored_pr", side_effect=[self.transport(), drifted]
            ),
            mock.patch.object(CREATE, "_run_mutation") as mutate,
        ):
            with self.assertRaisesRegex(CREATE.PublicationError, "after review"):
                self.required_publish()

        mutate.assert_not_called()
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_required_create_receipt_preimage_is_post_review_snapshot(self) -> None:
        assigned = self.transport()
        post_review = dict(assigned)
        after = self.stored()
        with (
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
            mock.patch.object(CREATE, "_create", return_value=(42, self.url)),
            mock.patch.object(
                CREATE,
                "_stored_pr",
                side_effect=[assigned, post_review, after],
            ),
            mock.patch.object(
                CREATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ),
            mock.patch.object(
                CREATE,
                "verified_transition",
                wraps=RECEIPTS.verified_transition,
            ) as transition,
        ):
            self.required_publish()

        self.assertIs(transition.call_args.kwargs["preimage"], post_review)

    def test_candidate_secret_blocks_before_create_without_echoing_value(self) -> None:
        credential_shape = "ghp_123456789012345678901234567890"
        template = self.template + f"\nCredential: {credential_shape}\n"

        with (
            mock.patch.object(Path, "read_bytes", return_value=template.encode()),
            mock.patch.object(CREATE, "_create") as create,
            self.assertRaisesRegex(
                CREATE.PublicationError, "publication is blocked"
            ) as raised,
        ):
            self.publish()

        create.assert_not_called()
        self.assertNotIn(credential_shape, str(raised.exception))

    def test_create_always_drafts_after_empty_exact_preflight(self) -> None:
        completed = subprocess.CompletedProcess([], 0, self.url, "")
        with (
            mock.patch.object(CREATE, "_matching_head_prs", return_value=[]),
            mock.patch.object(CREATE, "_run_mutation", return_value=completed) as run,
        ):
            result = CREATE._create(
                repository=self.repository,
                base=self.base,
                base_oid=self.base_oid,
                head=self.head,
                head_oid=self.head_oid,
                head_owner=self.head_owner,
                head_repository=self.head_repository,
                title=self.title,
                nonce=self.nonce,
            )
        self.assertEqual(result, (self.pr_number, self.url))
        self.assertIn("--draft", run.call_args.args[0])

    def test_stops_before_create_when_exact_head_base_pr_exists(self) -> None:
        with (
            mock.patch.object(
                CREATE, "_matching_head_prs", return_value=[self.stored()]
            ),
            mock.patch.object(CREATE, "_run_mutation") as run,
        ):
            with self.assertRaisesRegex(CREATE.PublicationError, "already exists"):
                CREATE._create(
                    repository=self.repository,
                    base=self.base,
                    base_oid=self.base_oid,
                    head=self.head,
                    head_oid=self.head_oid,
                    head_owner=self.head_owner,
                    head_repository=self.head_repository,
                    title=self.title,
                    nonce=self.nonce,
                )
        run.assert_not_called()

    def test_create_cli_never_echoes_existing_pr_url_from_raw_json(self) -> None:
        hostile_url = (
            "https://example.test/?token=arbitrary-secret-value\n"
            "Authorization: Bearer arbitrary-secret-value\x1b[31m"
        )
        rest_pr = {
            "number": self.pr_number,
            "html_url": hostile_url,
            "title": self.title,
            "body": self.body,
            "draft": True,
            "state": "open",
            "base": {
                "ref": self.base,
                "sha": self.base_oid,
                "repo": {"full_name": self.repository},
            },
            "head": {
                "ref": "widget",
                "sha": self.head_oid,
                "repo": {
                    "full_name": self.head_repository,
                    "owner": {"login": self.head_owner},
                },
            },
        }
        raw_json = json.dumps([[rest_pr]]).encode("utf-8")
        completed = subprocess.CompletedProcess([], 0, raw_json, b"")
        RECEIPTS.prepare_receipt_store(self.receipt_directory)
        with (
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(
                CREATE, "prepare_receipt_store", return_value=self.receipt_directory
            ),
            mock.patch.object(
                STATE.subprocess, "run", return_value=completed
            ) as run,
        ):
            status, diagnostic = self.invoke_cli(
                CREATE,
                [
                    "--repository",
                    self.repository,
                    "--base",
                    self.base,
                    "--base-oid",
                    self.base_oid,
                    "--head",
                    self.head,
                    "--head-oid",
                    self.head_oid,
                    "--head-owner",
                    self.head_owner,
                    "--head-repository",
                    self.head_repository,
                    "--title",
                    self.title,
                    "--body-template",
                    str(self.template_path),
                    "--review-input",
                    str(self.template_path),
                    "--review-mode",
                    "not-required",
                    "--selected-specialists",
                    "[]",
                ],
            )

        self.assertEqual(status, 1)
        self.assertIn("an open PR already exists for this head/base", diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertNotIn("example.test", diagnostic)
        self.assertNotIn("\x1b", diagnostic)
        self.assertEqual(run.call_count, 1)

    def test_recovers_unique_nonce_draft_after_ambiguous_create_error(self) -> None:
        with (
            mock.patch.object(
                CREATE, "_matching_head_prs", side_effect=[[], [self.transport()]]
            ),
            mock.patch.object(
                CREATE,
                "_run_mutation",
                side_effect=CREATE.PublicationError("network lost"),
            ),
        ):
            result = CREATE._create(
                repository=self.repository,
                base=self.base,
                base_oid=self.base_oid,
                head=self.head,
                head_oid=self.head_oid,
                head_owner=self.head_owner,
                head_repository=self.head_repository,
                title=self.title,
                nonce=self.nonce,
            )
        self.assertEqual(result, (self.pr_number, self.url))

    def test_create_recovery_read_failure_preserves_mutation_causality(self) -> None:
        mutation_error = STATE.CommandRejectedError(41)
        recovery_error = STATE.CommandReadError(return_code=42)
        with (
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
            mock.patch.object(
                CREATE, "_matching_head_prs", side_effect=[[], recovery_error]
            ),
            mock.patch.object(
                CREATE, "_run_mutation", side_effect=mutation_error
            ) as mutate,
            mock.patch.object(CREATE, "record_verified_publication") as record,
            self.assertRaises(CREATE.PublicationError) as raised,
        ):
            self.publish()

        diagnostic = str(raised.exception)
        self.assertIn("initial create command returned nonzero", diagnostic)
        self.assertIn("mutation command rejected (return code 41)", diagnostic)
        self.assertIn(
            "post-mutation reread was rejected (return code 42)", diagnostic
        )
        self.assertIs(raised.exception.__cause__, mutation_error)
        self.assertIs(raised.exception.reread_error, recovery_error)
        self.assertNotIn("separately authorized read", diagnostic)
        self.assertEqual(mutate.call_count, 1)
        record.assert_not_called()

    def test_malformed_create_result_and_failed_recovery_are_not_contradictory(
        self,
    ) -> None:
        recovery_error = STATE.CommandReadError(return_code=42)
        completed = subprocess.CompletedProcess([], 0, "created", "")
        with (
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
            mock.patch.object(
                CREATE, "_matching_head_prs", side_effect=[[], recovery_error]
            ),
            mock.patch.object(
                CREATE, "_run_mutation", return_value=completed
            ) as mutate,
            mock.patch.object(CREATE, "record_verified_publication") as record,
            self.assertRaises(CREATE.PublicationError) as raised,
        ):
            self.publish()

        diagnostic = str(raised.exception)
        self.assertIn(
            "initial create command exited zero without the expected PR URL",
            diagnostic,
        )
        self.assertNotIn("initial create command failed", diagnostic)
        self.assertIn(
            "post-mutation reread was rejected (return code 42)", diagnostic
        )
        self.assertEqual(
            str(raised.exception.__cause__),
            "gh pr create returned no expected PR URL",
        )
        self.assertEqual(mutate.call_count, 1)
        record.assert_not_called()

    def test_malformed_rest_recovery_cannot_mint_or_repeat_a_mutation(self) -> None:
        malformed = ReviewablePrStateTests.rest_pr(owner=self.head_owner, number=42)
        malformed["body"] = False
        reads = (
            subprocess.CompletedProcess([], 0, "[[]]", ""),
            subprocess.CompletedProcess([], 0, json.dumps([[malformed]]), ""),
        )
        with (
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
            mock.patch.object(STATE, "run_read", side_effect=reads),
            mock.patch.object(
                CREATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "created", ""),
            ) as mutate,
            mock.patch.object(CREATE, "record_verified_publication") as record,
            self.assertRaises(CREATE.PublicationError) as raised,
        ):
            self.publish()

        diagnostic = str(raised.exception)
        self.assertIn("exited zero without the expected PR URL", diagnostic)
        self.assertIn("post-mutation reread returned a malformed response", diagnostic)
        self.assertIn("no additional mutation was attempted", diagnostic)
        self.assertIn("no canonical receipt was written", diagnostic)
        self.assertIsInstance(raised.exception.reread_error.__cause__, TypeError)
        self.assertNotIn("False", diagnostic)
        self.assertEqual(mutate.call_count, 1)
        record.assert_not_called()

    def test_recovery_rejects_boolean_pr_number(self) -> None:
        with mock.patch.object(
            CREATE,
            "_matching_head_prs",
            return_value=[self.transport(number=True)],
        ):
            result, recovery_fact = CREATE._recover_created(
                repository=self.repository,
                base=self.base,
                base_oid=self.base_oid,
                head=self.head,
                head_oid=self.head_oid,
                head_owner=self.head_owner,
                head_repository=self.head_repository,
                title=self.title,
                transport_body=self.transport_body,
            )

        self.assertIsNone(result)
        self.assertIn("none matched", recovery_fact)

    def test_rejects_recovery_without_exact_nonce_and_oids(self) -> None:
        wrong = self.transport(headRefOid="c" * 40)
        with (
            mock.patch.object(CREATE, "_matching_head_prs", side_effect=[[], [wrong]]),
            mock.patch.object(
                CREATE,
                "_run_mutation",
                side_effect=CREATE.PublicationError("network lost"),
            ),
        ):
            with self.assertRaisesRegex(CREATE.PublicationError, "none matched"):
                CREATE._create(
                    repository=self.repository,
                    base=self.base,
                    base_oid=self.base_oid,
                    head=self.head,
                    head_oid=self.head_oid,
                    head_owner=self.head_owner,
                    head_repository=self.head_repository,
                    title=self.title,
                    nonce=self.nonce,
                )

    def test_recovers_after_successful_create_returns_malformed_output(self) -> None:
        completed = subprocess.CompletedProcess([], 0, "created", "")
        with (
            mock.patch.object(
                CREATE, "_matching_head_prs", side_effect=[[], [self.transport()]]
            ),
            mock.patch.object(CREATE, "_run_mutation", return_value=completed),
        ):
            result = CREATE._create(
                repository=self.repository,
                base=self.base,
                base_oid=self.base_oid,
                head=self.head,
                head_oid=self.head_oid,
                head_owner=self.head_owner,
                head_repository=self.head_repository,
                title=self.title,
                nonce=self.nonce,
            )
        self.assertEqual(result, (self.pr_number, self.url))

    def test_oversized_create_identifier_uses_one_nonce_recovery(self) -> None:
        provider_output = (
            f"https://github.com/{self.repository}/pull/{'9' * 5_000}\n"
            "Authorization: Bearer arbitrary-secret-value"
        )
        completed = subprocess.CompletedProcess([], 0, provider_output, "")
        with (
            mock.patch.object(
                CREATE, "_matching_head_prs", side_effect=[[], [self.transport()]]
            ) as recover,
            mock.patch.object(
                CREATE, "_run_mutation", return_value=completed
            ) as mutate,
        ):
            result = CREATE._create(
                repository=self.repository,
                base=self.base,
                base_oid=self.base_oid,
                head=self.head,
                head_oid=self.head_oid,
                head_owner=self.head_owner,
                head_repository=self.head_repository,
                title=self.title,
                nonce=self.nonce,
            )

        self.assertEqual(result, (self.pr_number, self.url))
        self.assertEqual(mutate.call_count, 1)
        self.assertEqual(recover.call_count, 2)

    def test_create_cli_safely_classifies_oversized_identifier_and_failed_recovery(
        self,
    ) -> None:
        provider_output = (
            f"https://github.com/{self.repository}/pull/{'9' * 5_000}\n"
            "Authorization: Bearer arbitrary-secret-value"
        )
        completed = subprocess.CompletedProcess([], 0, provider_output, "")
        recovery_error = STATE.CommandReadError(return_code=42)
        RECEIPTS.prepare_receipt_store(self.receipt_directory)
        with (
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
            mock.patch.object(
                CREATE, "_matching_head_prs", side_effect=[[], recovery_error]
            ) as recover,
            mock.patch.object(
                CREATE, "prepare_receipt_store", return_value=self.receipt_directory
            ),
            mock.patch.object(
                CREATE, "_run_mutation", return_value=completed
            ) as mutate,
            mock.patch.object(CREATE, "record_verified_publication") as record,
        ):
            status, diagnostic = self.invoke_cli(
                CREATE,
                [
                    "--repository",
                    self.repository,
                    "--base",
                    self.base,
                    "--base-oid",
                    self.base_oid,
                    "--head",
                    self.head,
                    "--head-oid",
                    self.head_oid,
                    "--head-owner",
                    self.head_owner,
                    "--head-repository",
                    self.head_repository,
                    "--title",
                    self.title,
                    "--body-template",
                    str(self.template_path),
                    "--review-input",
                    str(self.template_path),
                    "--review-mode",
                    "not-required",
                    "--selected-specialists",
                    "[]",
                ],
            )

        self.assertEqual(status, 1)
        self.assertIn(
            "initial create command exited zero without the expected PR URL",
            diagnostic,
        )
        self.assertIn("post-mutation reread was rejected (return code 42)", diagnostic)
        self.assertIn("no canonical receipt was written", diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertNotIn("ValueError", diagnostic)
        self.assertNotIn("Traceback", diagnostic)
        self.assertEqual(mutate.call_count, 1)
        self.assertEqual(recover.call_count, 2)
        record.assert_not_called()

    def test_oversized_create_identifier_retains_conversion_and_recovery_causes(
        self,
    ) -> None:
        provider_output = (
            f"https://github.com/{self.repository}/pull/{'9' * 5_000}\n"
            "Authorization: Bearer arbitrary-secret-value"
        )
        recovery_error = STATE.CommandReadError(return_code=42)
        with (
            mock.patch.object(
                CREATE, "_matching_head_prs", side_effect=[[], recovery_error]
            ) as recover,
            mock.patch.object(
                CREATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, provider_output, ""),
            ) as mutate,
            self.assertRaises(CREATE.PublicationError) as caught,
        ):
            CREATE._create(
                repository=self.repository,
                base=self.base,
                base_oid=self.base_oid,
                head=self.head,
                head_oid=self.head_oid,
                head_owner=self.head_owner,
                head_repository=self.head_repository,
                title=self.title,
                nonce=self.nonce,
            )

        create_error = caught.exception.__cause__
        self.assertIsInstance(create_error, CREATE.PublicationError)
        self.assertIsInstance(create_error.__cause__, ValueError)
        self.assertIs(caught.exception.reread_error, recovery_error)
        self.assertNotIn("arbitrary-secret-value", str(caught.exception))
        self.assertNotIn("Authorization", str(caught.exception))
        self.assertEqual(mutate.call_count, 1)
        self.assertEqual(recover.call_count, 2)

    def test_create_cli_fails_closed_on_malformed_successful_output(self) -> None:
        completed = subprocess.CompletedProcess(
            [], 0, b"\xffarbitrary-secret-value", b"\xfeAuthorization"
        )
        RECEIPTS.prepare_receipt_store(self.receipt_directory)
        with (
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
            mock.patch.object(CREATE, "_matching_head_prs", side_effect=[[], []]),
            mock.patch.object(
                CREATE, "prepare_receipt_store", return_value=self.receipt_directory
            ),
            mock.patch.object(
                STATE.subprocess, "run", return_value=completed
            ) as run,
        ):
            status, diagnostic = self.invoke_cli(
                CREATE,
                [
                    "--repository",
                    self.repository,
                    "--base",
                    self.base,
                    "--base-oid",
                    self.base_oid,
                    "--head",
                    self.head,
                    "--head-oid",
                    self.head_oid,
                    "--head-owner",
                    self.head_owner,
                    "--head-repository",
                    self.head_repository,
                    "--title",
                    self.title,
                    "--body-template",
                    str(self.template_path),
                    "--review-input",
                    str(self.template_path),
                    "--review-mode",
                    "not-required",
                    "--selected-specialists",
                    "[]",
                ],
            )

        self.assertEqual(status, 1)
        self.assertIn("strict UTF-8", diagnostic)
        self.assertIn("mutation outcome is unknown", diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertNotIn("UnicodeDecodeError", diagnostic)
        self.assertNotIn("codec", diagnostic)
        self.assertEqual(run.call_count, 1)
        self.assertFalse(self.receipt_directory.joinpath("acme").exists())

    def test_create_cli_safely_reports_broad_os_failure_as_unknown(self) -> None:
        launch_error = OSError(
            "/synthetic/arbitrary-secret-value/gh: Authorization\x1b[31m"
        )
        empty = subprocess.CompletedProcess([], 0, b"[]", b"")
        RECEIPTS.prepare_receipt_store(self.receipt_directory)
        with (
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
            mock.patch.object(
                CREATE, "prepare_receipt_store", return_value=self.receipt_directory
            ),
            mock.patch.object(
                STATE.subprocess,
                "run",
                side_effect=[empty, launch_error, empty],
            ) as run,
        ):
            status, diagnostic = self.invoke_cli(
                CREATE,
                [
                    "--repository",
                    self.repository,
                    "--base",
                    self.base,
                    "--base-oid",
                    self.base_oid,
                    "--head",
                    self.head,
                    "--head-oid",
                    self.head_oid,
                    "--head-owner",
                    self.head_owner,
                    "--head-repository",
                    self.head_repository,
                    "--title",
                    self.title,
                    "--body-template",
                    str(self.template_path),
                    "--review-input",
                    str(self.template_path),
                    "--review-mode",
                    "not-required",
                    "--selected-specialists",
                    "[]",
                ],
            )

        self.assertEqual(status, 1)
        self.assertIn("process launch or communication", diagnostic)
        self.assertIn("process started is unknown", diagnostic)
        self.assertIn("mutation outcome is unknown", diagnostic)
        self.assertNotIn("no process started", diagnostic)
        self.assertIn(
            "nonce recovery observed no open PR for the exact head/base", diagnostic
        )
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertNotIn("OSError", diagnostic)
        self.assertNotIn("Traceback", diagnostic)
        self.assertNotIn("\x1b", diagnostic)
        self.assertEqual(run.call_count, 3)

    def test_installs_canonical_body_with_one_mutation_and_final_read(self) -> None:
        completed = subprocess.CompletedProcess([], 0, "", "")
        with (
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
            mock.patch.object(CREATE, "_create", return_value=(42, self.url)),
            mock.patch.object(CREATE, "_run_mutation", return_value=completed) as run,
            mock.patch.object(
                CREATE,
                "_stored_pr",
                side_effect=[self.transport(), self.transport(), self.stored()],
            ) as reads,
        ):
            result = self.publish()
        self.assertEqual(result, self.stored())
        self.assertEqual(run.call_count, 1)
        self.assertEqual(reads.call_count, 3)

    def test_edit_error_never_mints_canonical_provenance(self) -> None:
        with (
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
            mock.patch.object(CREATE, "_create", return_value=(42, self.url)),
            mock.patch.object(
                CREATE,
                "_run_mutation",
                side_effect=STATE.MutationAmbiguousError(
                    "timeout after possible mutation; do not retry"
                ),
            ) as run,
            mock.patch.object(
                CREATE,
                "_stored_pr",
                side_effect=[self.transport(), self.transport(), self.stored()],
            ),
        ):
            with self.assertRaisesRegex(
                STATE.MutationAmbiguousError, "canonical provenance was not minted"
            ):
                self.publish()
        self.assertEqual(run.call_count, 1)
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_canonical_edit_process_failure_matrix_is_value_free(self) -> None:
        failures = (
            (
                "local-preparation",
                STATE.MutationPreparationError(),
                "mutation command could not be prepared locally",
            ),
            (
                "nonzero",
                STATE.CommandRejectedError(31),
                "mutation command rejected (return code 31)",
            ),
            (
                "timeout",
                STATE.MutationAmbiguousError(
                    "private timeout detail",
                    timeout_seconds=STATE.MUTATION_TIMEOUT_SECONDS,
                ),
                "mutation outcome is unknown after a 30-second timeout",
            ),
            (
                "malformed-zero-exit",
                STATE.MutationAmbiguousError(
                    "private output detail",
                    malformed_output=True,
                ),
                "mutation command returned malformed successful output",
            ),
        )
        for name, failure, classification in failures:
            with (
                self.subTest(outcome=name),
                mock.patch.object(CREATE, "_validate"),
                mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
                mock.patch.object(CREATE, "_create", return_value=(42, self.url)),
                mock.patch.object(
                    CREATE, "_run_mutation", side_effect=failure
                ) as mutate,
                mock.patch.object(
                    CREATE,
                    "_stored_pr",
                    side_effect=[
                        self.transport(),
                        self.transport(),
                        self.transport(),
                    ],
                ),
                self.assertRaises(CREATE.PublicationError) as raised,
            ):
                self.publish()

            diagnostic = str(raised.exception)
            self.assertIn("canonical edit command", diagnostic)
            self.assertIn(classification, diagnostic)
            self.assertIn("canonical provenance was not minted", diagnostic)
            self.assertNotIn("private", diagnostic)
            self.assertEqual(mutate.call_count, 1)
            self.assertEqual(
                RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
            )

    def test_canonical_edit_failure_reread_relationship_cross_product(self) -> None:
        class CleanupFailingTemporary:
            name = "/synthetic/private/arbitrary-secret-value/body.md"

            def write(self, value: bytes) -> int:
                return len(value)

            def flush(self) -> None:
                return None

            def close(self) -> None:
                raise cleanup_cause

        failure_cases = (
            (
                "local-preparation",
                STATE.MutationPreparationError,
                "mutation command could not be prepared locally",
            ),
            (
                "nonzero",
                lambda: STATE.CommandRejectedError(31),
                "mutation command rejected (return code 31)",
            ),
            (
                "timeout",
                lambda: STATE.MutationAmbiguousError(
                    "Authorization: arbitrary-secret-value",
                    timeout_seconds=STATE.MUTATION_TIMEOUT_SECONDS,
                ),
                "mutation outcome is unknown after a 30-second timeout",
            ),
            (
                "malformed-zero-exit",
                lambda: STATE.MutationAmbiguousError(
                    "Authorization: arbitrary-secret-value", malformed_output=True
                ),
                "mutation command returned malformed successful output",
            ),
            ("cleanup", lambda: None, "private body snapshot cleanup"),
        )
        relationship_cases = (
            (
                "intended",
                self.stored(providerExtension={"ignored": "intended"}),
                "final reread matched the exact intended state",
            ),
            (
                "preimage",
                self.transport(providerExtension={"ignored": "preimage"}),
                "final reread matched the pre-mutation state",
            ),
            (
                "other-valid",
                self.stored(
                    title="reviewer edit",
                    body="reviewer body",
                    providerExtension={"ignored": "other"},
                ),
                "final reread differed from both the pre-mutation and intended states",
            ),
            (
                "unavailable",
                None,
                "final reread state was unavailable",
            ),
        )
        for failure_name, failure_factory, classification in failure_cases:
            for relationship_name, after, relationship in relationship_cases:
                cleanup_cause = OSError("Authorization: arbitrary-secret-value")
                failure = failure_factory()
                reread_error = STATE.CommandReadError(return_code=42)
                final_read = reread_error if after is None else after
                mutation_result = (
                    subprocess.CompletedProcess([], 0, "", "")
                    if failure_name == "cleanup"
                    else mock.DEFAULT
                )
                mutation_effect = None if failure_name == "cleanup" else failure
                snapshot_patch = (
                    mock.patch.object(
                        PUBLICATION_SUPPORT.tempfile,
                        "NamedTemporaryFile",
                        return_value=CleanupFailingTemporary(),
                    )
                    if failure_name == "cleanup"
                    else nullcontext()
                )
                with (
                    self.subTest(
                        process_or_cleanup=failure_name,
                        reread=relationship_name,
                    ),
                    mock.patch.object(CREATE, "_validate"),
                    mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
                    mock.patch.object(CREATE, "_create", return_value=(42, self.url)),
                    mock.patch.object(
                        CREATE,
                        "_run_mutation",
                        return_value=mutation_result,
                        side_effect=mutation_effect,
                    ) as mutate,
                    mock.patch.object(
                        CREATE,
                        "_stored_pr",
                        side_effect=[self.transport(), self.transport(), final_read],
                    ) as reads,
                    mock.patch.object(CREATE, "record_verified_publication") as record,
                    snapshot_patch,
                    self.assertRaises(CREATE.PublicationError) as caught,
                ):
                    self.publish()

                diagnostic = str(caught.exception)
                self.assertIn("canonical edit command", diagnostic)
                self.assertIn(classification, diagnostic)
                self.assertIn(relationship, diagnostic)
                self.assertIn("canonical provenance was not minted", diagnostic)
                self.assertIn("no canonical receipt was written", diagnostic)
                self.assertIn(
                    "no automatic retry or rollback was attempted", diagnostic
                )
                self.assertNotIn("arbitrary-secret-value", diagnostic)
                self.assertNotIn("Authorization", diagnostic)
                self.assertEqual(mutate.call_count, 1)
                self.assertEqual(reads.call_count, 3)
                record.assert_not_called()
                self.assertEqual(
                    RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
                )
                operation_error = caught.exception.__cause__
                self.assertIsNotNone(operation_error)
                if failure_name == "cleanup":
                    self.assertIsInstance(
                        operation_error.__cause__, CREATE.BodySnapshotError
                    )
                    self.assertIs(operation_error.__cause__.__cause__, cleanup_cause)
                else:
                    self.assertIs(operation_error.__cause__, failure)
                if relationship_name == "unavailable":
                    self.assertIs(operation_error.reread_error, reread_error)

    def test_zero_exit_canonical_edit_preserves_failed_reread_context(self) -> None:
        reread_error = STATE.CommandReadError(return_code=42)
        with (
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
            mock.patch.object(CREATE, "_create", return_value=(42, self.url)),
            mock.patch.object(
                CREATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as run,
            mock.patch.object(
                CREATE,
                "_stored_pr",
                side_effect=[self.transport(), self.transport(), reread_error],
            ),
            self.assertRaises(CREATE.PublicationError) as raised,
        ):
            self.publish()

        diagnostic = str(raised.exception)
        inner = raised.exception.__cause__
        self.assertIsNotNone(inner)
        self.assertIn("canonical edit command exited zero", diagnostic)
        self.assertIn("canonical provenance was not minted", diagnostic)
        self.assertIn("no automatic retry or rollback was attempted", diagnostic)
        self.assertIn(
            "post-mutation reread was rejected (return code 42)", diagnostic
        )
        self.assertIs(inner.__cause__, reread_error)
        self.assertIs(inner.reread_error, reread_error)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_zero_exit_canonical_edit_classifies_every_nonmatching_reread(self) -> None:
        cases = (
            ("preimage", self.transport(), "matched the pre-mutation state"),
            (
                "other-valid",
                self.stored(title="reviewer edit", body="reviewer body"),
                "differed from both the pre-mutation and intended states",
            ),
        )
        for name, after, relationship in cases:
            with (
                self.subTest(relationship=name),
                mock.patch.object(CREATE, "_validate"),
                mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
                mock.patch.object(CREATE, "_create", return_value=(42, self.url)),
                mock.patch.object(
                    CREATE,
                    "_run_mutation",
                    return_value=subprocess.CompletedProcess([], 0, "", ""),
                ) as run,
                mock.patch.object(
                    CREATE,
                    "_stored_pr",
                    side_effect=[self.transport(), self.transport(), after],
                ),
                self.assertRaises(CREATE.PublicationError) as raised,
            ):
                self.publish()

            diagnostic = str(raised.exception)
            self.assertIn("canonical edit command exited zero", diagnostic)
            self.assertIn(relationship, diagnostic)
            self.assertIn("causality remains unresolved", diagnostic)
            self.assertIn("no canonical receipt was written", diagnostic)
            self.assertIn("no automatic retry or rollback was attempted", diagnostic)
            self.assertNotIn("was not stored", diagnostic)
            self.assertEqual(run.call_count, 1)
            self.assertEqual(
                RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
            )

    def test_edit_nonzero_with_matching_state_is_not_canonical(self) -> None:
        with (
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
            mock.patch.object(CREATE, "_create", return_value=(42, self.url)),
            mock.patch.object(
                CREATE,
                "_run_mutation",
                side_effect=CREATE.PublicationError("nonzero"),
            ),
            mock.patch.object(
                CREATE,
                "_stored_pr",
                side_effect=[self.transport(), self.transport(), self.stored()],
            ),
        ):
            with self.assertRaisesRegex(
                CREATE.PublicationError, "canonical provenance was not minted"
            ):
                self.publish()
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_create_cli_reports_safe_canonical_edit_rejection_diagnostic(
        self,
    ) -> None:
        stdout, stderr = self.hostile_command_output()
        RECEIPTS.prepare_receipt_store(self.receipt_directory)
        command_results = [
            subprocess.CompletedProcess([], 0, self.url, ""),
            subprocess.CompletedProcess([], 23, stdout, stderr),
        ]
        with (
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
            mock.patch.object(CREATE, "_matching_head_prs", return_value=[]),
            mock.patch.object(
                CREATE,
                "_stored_pr",
                side_effect=[self.transport(), self.transport(), self.stored()],
            ),
            mock.patch.object(
                CREATE, "prepare_receipt_store", return_value=self.receipt_directory
            ),
            mock.patch.object(
                STATE.subprocess, "run", side_effect=command_results
            ) as run,
        ):
            status, diagnostic = self.invoke_cli(
                CREATE,
                [
                    "--repository",
                    self.repository,
                    "--base",
                    self.base,
                    "--base-oid",
                    self.base_oid,
                    "--head",
                    self.head,
                    "--head-oid",
                    self.head_oid,
                    "--head-owner",
                    self.head_owner,
                    "--head-repository",
                    self.head_repository,
                    "--title",
                    self.title,
                    "--body-template",
                    str(self.template_path),
                    "--review-input",
                    str(self.template_path),
                    "--review-mode",
                    "not-required",
                    "--selected-specialists",
                    "[]",
                ],
            )

        self.assertEqual(status, 1)
        self.assertIn("canonical edit command failed", diagnostic)
        self.assertIn("mutation command rejected (return code 23)", diagnostic)
        self.assertIn("command output was withheld", diagnostic)
        self.assertIn("rejection cause is unknown", diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertNotIn("forged diagnostic", diagnostic)
        self.assertNotIn("\x1b", diagnostic)
        self.assertLess(len(diagnostic), 2000)
        edit_calls = [call for call in run.call_args_list if "edit" in call.args[0]]
        self.assertEqual(len(edit_calls), 1)
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_canonical_edit_timeout_with_unchanged_state_remains_ambiguous(
        self,
    ) -> None:
        with (
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
            mock.patch.object(CREATE, "_create", return_value=(42, self.url)),
            mock.patch.object(
                CREATE,
                "_run_mutation",
                side_effect=STATE.MutationAmbiguousError("timeout; do not retry"),
            ) as run,
            mock.patch.object(
                CREATE,
                "_stored_pr",
                side_effect=[self.transport(), self.transport(), self.transport()],
            ),
        ):
            with self.assertRaisesRegex(STATE.MutationAmbiguousError, "do not retry"):
                self.publish()
        self.assertEqual(run.call_count, 1)

    def test_edit_failure_is_not_retried_or_rolled_back(self) -> None:
        with (
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
            mock.patch.object(CREATE, "_create", return_value=(42, self.url)),
            mock.patch.object(
                CREATE,
                "_run_mutation",
                side_effect=CREATE.PublicationError("failed"),
            ) as run,
            mock.patch.object(
                CREATE,
                "_stored_pr",
                side_effect=[self.transport(), self.transport(), self.transport()],
            ),
        ):
            with self.assertRaisesRegex(CREATE.PublicationError, "no automatic retry"):
                self.publish()
        self.assertEqual(run.call_count, 1)

    def test_concurrent_state_blocks_mutation_or_retry(self) -> None:
        concurrent = self.stored(title="reviewer edit", body="reviewer body")
        with (
            mock.patch.object(CREATE, "_validate"),
            mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
            mock.patch.object(CREATE, "_create", return_value=(42, self.url)),
            mock.patch.object(CREATE, "_run_mutation") as run,
            mock.patch.object(
                CREATE, "_stored_pr", side_effect=[self.transport(), concurrent]
            ),
        ):
            with self.assertRaisesRegex(CREATE.PublicationError, "no longer has"):
                self.publish()
        run.assert_not_called()

    def test_requires_qualified_head_before_validation_or_create(self) -> None:
        with (
            mock.patch.object(CREATE, "_validate") as validate,
            mock.patch.object(CREATE, "_create") as create,
        ):
            with self.assertRaisesRegex(CREATE.PublicationError, "OWNER:BRANCH"):
                CREATE.publish(
                    repository=self.repository,
                    base=self.base,
                    base_oid=self.base_oid,
                    head="widget",
                    head_oid=self.head_oid,
                    head_owner=self.head_owner,
                    head_repository=self.head_repository,
                    title=self.title,
                    template_path=self.template_path,
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )
        validate.assert_not_called()
        create.assert_not_called()

    def test_token_template_is_validated_before_create_and_exact_body_after(
        self,
    ) -> None:
        events: list[str] = []

        def validate(*_: object, **__: object) -> None:
            events.append("validate")

        def create(**_: object) -> tuple[int, str]:
            events.append("create")
            return self.pr_number, self.url

        with (
            mock.patch.object(CREATE, "_validate", side_effect=validate),
            mock.patch.object(CREATE, "_new_nonce", return_value=self.nonce),
            mock.patch.object(CREATE, "_create", side_effect=create),
            mock.patch.object(
                CREATE,
                "_stored_pr",
                side_effect=[self.transport(), self.transport(), self.stored()],
            ),
            mock.patch.object(
                CREATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ),
        ):
            self.publish()

        self.assertEqual(events, ["validate", "create", "validate"])


class UpdateReviewablePrTests(ReviewablePrFixture):
    BOT_TAIL = (
        "\n<!-- This is an auto-generated comment: release notes by coderabbit.ai -->\n"
        "## Summary by CodeRabbit\n"
        "- Generated notes\n"
        "<!-- end of auto-generated comment: release notes by coderabbit.ai -->"
    )

    def test_update_and_reconcile_local_inputs_are_value_free_and_chained(
        self,
    ) -> None:
        hostile_path = Path("/synthetic/Authorization: arbitrary-secret-value/body.md")
        read_error = OSError("Authorization: arbitrary-secret-value")
        with (
            mock.patch.object(Path, "read_bytes", side_effect=read_error),
            self.assertRaises(UPDATE.PublicationError) as caught,
        ):
            UPDATE._read_body(hostile_path)

        diagnostic = str(caught.exception)
        self.assertEqual(
            diagnostic,
            "cannot read body file; check the local path and read permissions",
        )
        self.assertIs(caught.exception.__cause__, read_error)
        self.assertNotIn(str(hostile_path), diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("authentication", diagnostic)

        with (
            mock.patch.object(
                Path,
                "read_bytes",
                return_value=b"\xffAuthorization: arbitrary-secret-value",
            ),
            self.assertRaises(UPDATE.PublicationError) as caught,
        ):
            UPDATE._read_body(hostile_path, label="body template")
        self.assertEqual(str(caught.exception), "body template must be valid UTF-8")
        self.assertIsInstance(caught.exception.__cause__, UnicodeDecodeError)

        with self.assertRaisesRegex(
            UPDATE.PublicationError, "body template path must be absolute"
        ):
            UPDATE._read_body(Path("relative.md"), label="body template")

        with (
            mock.patch.object(Path, "read_bytes", side_effect=read_error),
            mock.patch.object(UPDATE, "_run_mutation") as mutate,
        ):
            status, cli_diagnostic = self.invoke_cli(
                UPDATE,
                [
                    "text",
                    "--repository",
                    self.repository,
                    "--pr",
                    str(self.pr_number),
                    "--base",
                    self.base,
                    "--base-oid",
                    self.base_oid,
                    "--head",
                    self.head,
                    "--head-oid",
                    self.head_oid,
                    "--head-owner",
                    self.head_owner,
                    "--head-repository",
                    self.head_repository,
                    "--expected-title-sha256",
                    self.digest(self.title),
                    "--expected-body-sha256",
                    self.digest(self.body),
                    "--review-input",
                    str(self.template_path),
                    "--review-mode",
                    "not-required",
                    "--selected-specialists",
                    "[]",
                    "--expected-state",
                    "draft",
                    "--text-scope",
                    "body-only",
                    "--title",
                    self.title,
                    "--body-file",
                    str(hostile_path),
                ],
            )

        self.assertEqual(status, 1)
        self.assertIn("cannot read body file", cli_diagnostic)
        self.assertNotIn(str(hostile_path), cli_diagnostic)
        self.assertNotIn("arbitrary-secret-value", cli_diagnostic)
        self.assertNotIn("Traceback", cli_diagnostic)
        mutate.assert_not_called()

        review_input = Path(self.temporary_directory.name) / "hostile-review.json"
        hostile_key = "Authorization: arbitrary-secret-value"
        review_input.write_text(
            '{"version": 2, "' + hostile_key + '": 1, "' + hostile_key + '": 2}',
            encoding="utf-8",
        )
        consumers = (
            (
                "text-ready",
                lambda: UPDATE_BIND_REVIEW_INPUT(
                    review_input,
                    self.expected,
                    self.title,
                    self.body,
                ),
            ),
            (
                "reconcile",
                lambda: AUDIT._validate_live_state(
                    expected=self.expected,
                    title=self.title,
                    body=self.body,
                    review_input_path=review_input,
                ),
            ),
        )
        for name, consume in consumers:
            with (
                self.subTest(consumer=name),
                mock.patch.object(
                    UPDATE, "_admit_review_input", side_effect=ADMIT_REVIEW_INPUT
                ),
                mock.patch.object(
                    AUDIT, "_admit_review_input", side_effect=ADMIT_REVIEW_INPUT
                ),
                self.assertRaises(STATE.PublicationError) as caught,
            ):
                consume()

            diagnostic = str(caught.exception)
            self.assertEqual(
                diagnostic,
                "review input could not be admitted; check the local file and "
                "regenerate it for this exact publication candidate",
            )
            self.assertIsInstance(caught.exception.__cause__, UPDATE.ReviewInputError)
            self.assertNotIn(hostile_key, diagnostic)
            self.assertNotIn("authentication", diagnostic)

    def test_text_and_ready_cli_duplicate_review_key_is_value_free(self) -> None:
        hostile_key = "Authorization: arbitrary-secret-value"
        review_input = Path(self.temporary_directory.name) / "hostile-review.json"
        review_input.write_text(
            '{"version": 2, "' + hostile_key + '": 1, "' + hostile_key + '": 2}',
            encoding="utf-8",
        )
        desired_path = self.desired_body_path()
        common = [
            "--repository",
            self.repository,
            "--pr",
            str(self.pr_number),
            "--base",
            self.base,
            "--base-oid",
            self.base_oid,
            "--head",
            self.head,
            "--head-oid",
            self.head_oid,
            "--head-owner",
            self.head_owner,
            "--head-repository",
            self.head_repository,
            "--expected-title-sha256",
            self.digest(self.title),
            "--expected-body-sha256",
            self.digest(self.body),
            "--review-input",
            str(review_input),
            "--review-mode",
            "not-required",
            "--selected-specialists",
            "[]",
        ]
        cases = (
            (
                "text",
                [
                    "text",
                    *common,
                    "--expected-state",
                    "draft",
                    "--text-scope",
                    "body-only",
                    "--title",
                    self.title,
                    "--body-file",
                    str(desired_path),
                ],
            ),
            ("ready", ["ready", *common]),
        )
        for name, arguments in cases:
            RECEIPTS.prepare_receipt_store(self.receipt_directory)
            with (
                self.subTest(consumer=name),
                mock.patch.object(
                    UPDATE, "_build_candidate", side_effect=self._fixture_candidate
                ),
                mock.patch.object(
                    UPDATE, "_admit_review_input", side_effect=ADMIT_REVIEW_INPUT
                ),
                mock.patch.object(UPDATE, "_validate_body"),
                mock.patch.object(
                    UPDATE,
                    "_bind_review_input",
                    side_effect=UPDATE_BIND_REVIEW_INPUT,
                ),
                mock.patch.object(
                    UPDATE,
                    "prepare_receipt_store",
                    return_value=self.receipt_directory,
                ),
                mock.patch.object(UPDATE, "_stored_pr", return_value=self.stored()),
                mock.patch.object(UPDATE, "_run_mutation") as mutate,
            ):
                status, diagnostic = self.invoke_cli(UPDATE, arguments)

            self.assertEqual(status, 1)
            self.assertIn("review input could not be admitted", diagnostic)
            self.assertNotIn(hostile_key, diagnostic)
            self.assertNotIn("Traceback", diagnostic)
            mutate.assert_not_called()

    def test_reconcile_cli_duplicate_review_key_is_value_free(self) -> None:
        hostile_key = "Authorization: arbitrary-secret-value"
        review_input = Path(self.temporary_directory.name) / "hostile-review.json"
        review_input.write_text(
            '{"version": 2, "' + hostile_key + '": 1, "' + hostile_key + '": 2}',
            encoding="utf-8",
        )
        RECEIPTS.prepare_receipt_store(self.receipt_directory)
        with (
            mock.patch.object(
                AUDIT, "_admit_review_input", side_effect=ADMIT_REVIEW_INPUT
            ),
            mock.patch.object(
                AUDIT, "prepare_receipt_store", return_value=self.receipt_directory
            ),
            mock.patch.object(AUDIT, "stored_pr", return_value=self.stored()),
            mock.patch.object(AUDIT, "record_reconciliation") as record,
        ):
            status, diagnostic = self.invoke_cli(
                AUDIT,
                [
                    "reconcile",
                    "--repository",
                    self.repository,
                    "--pr",
                    str(self.pr_number),
                    "--base",
                    self.base,
                    "--base-oid",
                    self.base_oid,
                    "--head",
                    self.head,
                    "--head-oid",
                    self.head_oid,
                    "--head-owner",
                    self.head_owner,
                    "--head-repository",
                    self.head_repository,
                    "--review-input",
                    str(review_input),
                ],
            )

        self.assertEqual(status, 1)
        self.assertIn("review input could not be admitted", diagnostic)
        self.assertNotIn(hostile_key, diagnostic)
        self.assertNotIn("Traceback", diagnostic)
        record.assert_not_called()

    def test_text_ready_and_reconcile_apis_bound_real_review_input_failures(
        self,
    ) -> None:
        hostile = "Authorization: arbitrary-secret-value"
        for name, payload in malformed_review_input_payloads(token_bearing=True):
            review_input = self.write_review_input_bytes(name, payload)
            consumers = (
                (
                    "text-ready",
                    lambda: UPDATE_BIND_REVIEW_INPUT(
                        review_input,
                        self.expected,
                        self.title,
                        self.body,
                    ),
                ),
                (
                    "reconcile",
                    lambda: AUDIT._validate_live_state(
                        expected=self.expected,
                        title=self.title,
                        body=self.body,
                        review_input_path=review_input,
                    ),
                ),
            )
            for consumer, consume in consumers:
                with (
                    self.subTest(case=name, entrypoint=consumer),
                    mock.patch.object(
                        UPDATE, "_admit_review_input", side_effect=ADMIT_REVIEW_INPUT
                    ),
                    mock.patch.object(
                        AUDIT, "_admit_review_input", side_effect=ADMIT_REVIEW_INPUT
                    ),
                    self.assertRaises(STATE.PublicationError) as caught,
                ):
                    consume()

                self.assertEqual(
                    str(caught.exception),
                    "review input could not be admitted; check the local file and "
                    "regenerate it for this exact publication candidate",
                )
                self.assertIsNotNone(caught.exception.__cause__)
                self.assertIsNotNone(caught.exception.__cause__.__cause__)
                self.assertNotIn(hostile, str(caught.exception))
                self.assertNotIn(str(review_input), str(caught.exception))

    def test_text_ready_token_and_reconcile_clis_bound_real_review_input_failures(
        self,
    ) -> None:
        hostile = "Authorization: arbitrary-secret-value"
        desired_path = self.desired_body_path()
        for name, payload in malformed_review_input_payloads(token_bearing=True):
            review_input = self.write_review_input_bytes(name, payload)
            common = [
                "--repository",
                self.repository,
                "--pr",
                str(self.pr_number),
                "--base",
                self.base,
                "--base-oid",
                self.base_oid,
                "--head",
                self.head,
                "--head-oid",
                self.head_oid,
                "--head-owner",
                self.head_owner,
                "--head-repository",
                self.head_repository,
                "--expected-title-sha256",
                self.digest(self.title),
                "--expected-body-sha256",
                self.digest(self.body),
                "--review-input",
                str(review_input),
                "--review-mode",
                "not-required",
                "--selected-specialists",
                "[]",
            ]
            cases = (
                (
                    "text",
                    [
                        "text",
                        *common,
                        "--expected-state",
                        "draft",
                        "--text-scope",
                        "body-only",
                        "--title",
                        self.title,
                        "--body-file",
                        str(desired_path),
                    ],
                    UPDATE,
                ),
                (
                    "ready-token",
                    ["ready", *common, "--body-template", str(self.template_path)],
                    UPDATE,
                ),
                (
                    "reconcile",
                    [
                        "reconcile",
                        "--repository",
                        self.repository,
                        "--pr",
                        str(self.pr_number),
                        "--base",
                        self.base,
                        "--base-oid",
                        self.base_oid,
                        "--head",
                        self.head,
                        "--head-oid",
                        self.head_oid,
                        "--head-owner",
                        self.head_owner,
                        "--head-repository",
                        self.head_repository,
                        "--review-input",
                        str(review_input),
                    ],
                    AUDIT,
                ),
            )
            for consumer, arguments, module in cases:
                RECEIPTS.prepare_receipt_store(self.receipt_directory)
                with (
                    self.subTest(case=name, entrypoint=consumer),
                    mock.patch.object(
                        UPDATE, "_admit_review_input", side_effect=ADMIT_REVIEW_INPUT
                    ),
                    mock.patch.object(
                        AUDIT, "_admit_review_input", side_effect=ADMIT_REVIEW_INPUT
                    ),
                    mock.patch.object(UPDATE, "_validate_body"),
                    mock.patch.object(
                        UPDATE,
                        "_bind_review_input",
                        side_effect=UPDATE_BIND_REVIEW_INPUT,
                    ),
                    mock.patch.object(
                        UPDATE,
                        "prepare_receipt_store",
                        return_value=self.receipt_directory,
                    ),
                    mock.patch.object(
                        AUDIT,
                        "prepare_receipt_store",
                        return_value=self.receipt_directory,
                    ),
                    mock.patch.object(
                        UPDATE, "_stored_pr", return_value=self.stored()
                    ),
                    mock.patch.object(AUDIT, "stored_pr", return_value=self.stored()),
                    mock.patch.object(UPDATE, "_run_mutation") as mutate,
                    mock.patch.object(AUDIT, "record_reconciliation") as record,
                ):
                    status, diagnostic = self.invoke_cli(module, arguments)

                self.assertEqual(status, 1)
                self.assertIn("review input could not be admitted", diagnostic)
                self.assertNotIn(hostile, diagnostic)
                self.assertNotIn(str(review_input), diagnostic)
                self.assertNotIn("Traceback", diagnostic)
                mutate.assert_not_called()
                record.assert_not_called()
                self.assertEqual(
                    RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
                )

    def test_real_routes_admit_malformed_review_input_before_later_boundaries(
        self,
    ) -> None:
        malformed = dict(malformed_review_input_payloads())
        token_bearing = dict(malformed_review_input_payloads(token_bearing=True))
        categories = (
            "invalid-utf8",
            "syntax",
            "oversized-integer",
            "excessive-nesting",
        )
        desired_path = self.desired_body_path()
        cases: list[tuple[str, bytes]] = [
            ("create-invalid-utf8", malformed["invalid-utf8"])
        ]
        cases.extend((f"text-{name}", malformed[name]) for name in categories)
        cases.extend((f"ready-token-{name}", token_bearing[name]) for name in categories)
        cases.extend((f"reconcile-{name}", malformed[name]) for name in categories)

        for case, payload in cases:
            review_input = self.write_review_input_bytes(case, payload)

            def consume() -> object:
                if case.startswith("create-"):
                    return CREATE.publish(
                        repository=self.repository,
                        base=self.base,
                        base_oid=self.base_oid,
                        head=self.head,
                        head_oid=self.head_oid,
                        head_owner=self.head_owner,
                        head_repository=self.head_repository,
                        title=self.title,
                        template_path=self.template_path,
                        review_input_path=review_input,
                        review_mode="not-required",
                        review_bundle_root=None,
                        selected_specialists=[],
                        receipt_directory=self.receipt_directory,
                    )
                if case.startswith("text-"):
                    return UPDATE.update_text(
                        expected=self.expected,
                        expected_title_sha256=self.digest(self.title),
                        expected_body_sha256=self.digest(self.body),
                        expected_draft=True,
                        title=self.title,
                        body_path=desired_path,
                        review_input_path=review_input,
                        review_mode="not-required",
                        review_bundle_root=None,
                        selected_specialists=[],
                        text_scope="body-only",
                        receipt_directory=self.receipt_directory,
                    )
                if case.startswith("ready-"):
                    return UPDATE.mark_ready(
                        expected=self.expected,
                        expected_title_sha256=self.digest(self.title),
                        expected_body_sha256=self.digest(self.body),
                        review_input_path=review_input,
                        review_mode="not-required",
                        review_bundle_root=None,
                        selected_specialists=[],
                        body_template_path=self.template_path,
                        receipt_directory=self.receipt_directory,
                    )
                return AUDIT.reconcile(
                    expected=self.expected,
                    receipt_directory=self.receipt_directory,
                    review_input_path=review_input,
                )

            with (
                self.subTest(case=case),
                mock.patch.object(
                    CREATE, "_review_input", side_effect=CREATE_REVIEW_INPUT
                ),
                mock.patch.object(
                    UPDATE, "_bind_review_input", side_effect=UPDATE_BIND_REVIEW_INPUT
                ),
                mock.patch.object(
                    UPDATE, "_admit_review_input", side_effect=ADMIT_REVIEW_INPUT
                ),
                mock.patch.object(
                    AUDIT, "_admit_review_input", side_effect=ADMIT_REVIEW_INPUT
                ),
                mock.patch.object(
                    PUBLICATION_SUPPORT,
                    "run_read",
                    wraps=PUBLICATION_SUPPORT.run_read,
                ) as validator_process,
                mock.patch.object(CREATE, "_create") as create,
                mock.patch.object(CREATE, "prepare_receipt_store") as create_store,
                mock.patch.object(
                    CREATE, "record_verified_publication"
                ) as create_record,
                mock.patch.object(
                    UPDATE, "_stored_pr", return_value=self.stored()
                ) as update_read,
                mock.patch.object(UPDATE, "_run_mutation") as update_mutate,
                mock.patch.object(UPDATE, "prepare_receipt_store") as update_store,
                mock.patch.object(UPDATE, "prepare_receipt_ledger") as update_ledger,
                mock.patch.object(UPDATE, "receipt_ledger_lock") as update_lock,
                mock.patch.object(
                    AUDIT,
                    "prepare_receipt_store",
                    return_value=self.receipt_directory,
                ) as reconcile_store,
                mock.patch.object(AUDIT, "prepare_receipt_ledger") as reconcile_ledger,
                mock.patch.object(
                    AUDIT,
                    "receipt_ledger_lock",
                    return_value=nullcontext(mock.sentinel.lease),
                ) as reconcile_lock,
                mock.patch.object(
                    AUDIT, "stored_pr", return_value=self.stored()
                ) as reconcile_read,
                mock.patch.object(AUDIT, "record_reconciliation") as reconcile_record,
                self.assertRaises(STATE.PublicationError) as caught,
            ):
                consume()

            with self.subTest(case=case, evidence="cause-and-order"):
                self.assertEqual(
                    str(caught.exception),
                    "review input could not be admitted; check the local file and "
                    "regenerate it for this exact publication candidate",
                )
                admission_error = caught.exception.__cause__
                self.assertIsInstance(admission_error, REVIEW_INPUT.ReviewInputError)
                original = admission_error.__cause__
                if "invalid-utf8" in case:
                    self.assertIsInstance(original, UnicodeDecodeError)
                elif "syntax" in case:
                    self.assertIsInstance(original, json.JSONDecodeError)
                else:
                    self.assertEqual(type(original).__name__, "_ReviewInputAdmissionError")
                validator_process.assert_not_called()
                create.assert_not_called()
                create_store.assert_not_called()
                create_record.assert_not_called()
                update_read.assert_not_called()
                update_mutate.assert_not_called()
                update_store.assert_not_called()
                update_ledger.assert_not_called()
                update_lock.assert_not_called()
                reconcile_store.assert_not_called()
                reconcile_ledger.assert_not_called()
                reconcile_lock.assert_not_called()
                reconcile_read.assert_not_called()
                reconcile_record.assert_not_called()

    def test_valid_schema_v3_inputs_continue_in_route_order_to_real_validator(
        self,
    ) -> None:
        desired_path = self.desired_body_path()
        desired = desired_path.read_text(encoding="utf-8")
        cases = (
            (
                "text",
                self.write_valid_review_input("valid-text", body=desired),
                False,
            ),
            (
                "ready-token",
                self.write_valid_review_input(
                    "valid-ready-token", body=self.body, token_bearing=True
                ),
                True,
            ),
        )
        real_validator_process = PUBLICATION_SUPPORT.run_read

        for case, review_input, token_bearing in cases:
            events: list[str] = []

            def admit(path: Path):
                events.append("admit")
                return ADMIT_REVIEW_INPUT(path)

            def read_state(*_args: object, **_kwargs: object):
                events.append("state-read")
                return self.stored()

            def run_validator(*args: object, **kwargs: object):
                events.append("validator")
                real_validator_process(*args, **kwargs)
                raise STATE.PublicationError("stop after real validator continuation")

            with (
                self.subTest(case=case),
                mock.patch.object(UPDATE, "_admit_review_input", side_effect=admit),
                mock.patch.object(UPDATE, "_stored_pr", side_effect=read_state),
                mock.patch.object(
                    PUBLICATION_SUPPORT, "run_read", side_effect=run_validator
                ) as validator_process,
                mock.patch.object(UPDATE, "prepare_receipt_store") as receipt_store,
                self.assertRaises(STATE.PublicationError),
            ):
                if token_bearing:
                    UPDATE.mark_ready(
                        expected=self.expected,
                        expected_title_sha256=self.digest(self.title),
                        expected_body_sha256=self.digest(self.body),
                        review_input_path=review_input,
                        review_mode="not-required",
                        review_bundle_root=None,
                        selected_specialists=[],
                        body_template_path=self.template_path,
                        receipt_directory=self.receipt_directory,
                    )
                else:
                    UPDATE.update_text(
                        expected=self.expected,
                        expected_title_sha256=self.digest(self.title),
                        expected_body_sha256=self.digest(self.body),
                        expected_draft=True,
                        title=self.title,
                        body_path=desired_path,
                        review_input_path=review_input,
                        review_mode="not-required",
                        review_bundle_root=None,
                        selected_specialists=[],
                        text_scope="body-only",
                        receipt_directory=self.receipt_directory,
                    )

            with self.subTest(case=case, evidence="continuation-order"):
                expected_events = (
                    ["admit", "state-read", "validator"]
                    if token_bearing
                    else ["admit", "validator"]
                )
                self.assertEqual(events, expected_events)
                validator_process.assert_called_once()
                receipt_store.assert_not_called()

    def test_token_ready_reads_body_template_before_external_boundaries(self) -> None:
        review_input = self.write_valid_review_input(
            "valid-ready-for-invalid-template",
            body=self.body,
            token_bearing=True,
        )
        invalid_template = Path(self.temporary_directory.name) / "invalid-template.md"
        invalid_template.write_bytes(b"\xffAuthorization: arbitrary-secret-value")

        with (
            mock.patch.object(
                UPDATE, "_admit_review_input", side_effect=ADMIT_REVIEW_INPUT
            ),
            mock.patch.object(UPDATE, "_stored_pr", return_value=self.stored()) as read,
            mock.patch.object(
                PUBLICATION_SUPPORT,
                "run_read",
                wraps=PUBLICATION_SUPPORT.run_read,
            ) as validator_process,
            mock.patch.object(UPDATE, "prepare_receipt_store") as receipt_store,
            self.assertRaises(STATE.PublicationError) as caught,
        ):
            UPDATE.mark_ready(
                expected=self.expected,
                expected_title_sha256=self.digest(self.title),
                expected_body_sha256=self.digest(self.body),
                review_input_path=review_input,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                body_template_path=invalid_template,
                receipt_directory=self.receipt_directory,
            )

        self.assertEqual(str(caught.exception), "body template must be valid UTF-8")
        self.assertIsInstance(caught.exception.__cause__, UnicodeDecodeError)
        read.assert_not_called()
        validator_process.assert_not_called()
        receipt_store.assert_not_called()

    def test_text_cleanup_failure_after_zero_exit_rereads_without_receipt(self) -> None:
        class CleanupFailingTemporary:
            name = "/synthetic/private/arbitrary-secret-value/body.md"

            def write(self, value: bytes) -> int:
                return len(value)

            def flush(self) -> None:
                return None

            def close(self) -> None:
                raise OSError("Authorization: arbitrary-secret-value")

        desired_path = self.desired_body_path()
        desired = desired_path.read_text(encoding="utf-8")
        after = self.stored(body=desired)
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE,
                "_stored_pr",
                side_effect=[self.stored(), self.stored(), self.stored(), after],
            ) as reads,
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as mutate,
            mock.patch.object(
                PUBLICATION_SUPPORT.tempfile,
                "NamedTemporaryFile",
                return_value=CleanupFailingTemporary(),
            ),
            self.assertRaises(UPDATE.PublicationError) as caught,
        ):
            UPDATE.update_text(
                expected=self.expected,
                expected_title_sha256=self.digest(self.title),
                expected_body_sha256=self.digest(self.body),
                expected_draft=True,
                title=self.title,
                body_path=desired_path,
                review_input_path=self.template_path,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                receipt_directory=self.receipt_directory,
                text_scope="body-only",
            )

        diagnostic = str(caught.exception)
        self.assertIn("PR text command exited zero", diagnostic)
        self.assertIn("private body snapshot cleanup failed", diagnostic)
        self.assertIn("exact intended state was observed", diagnostic)
        self.assertIn("canonical provenance was not minted", diagnostic)
        self.assertIn("do not retry", diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertEqual(mutate.call_count, 1)
        self.assertEqual(reads.call_count, 4)
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_text_failure_reread_relationship_cross_product(self) -> None:
        class CleanupFailingTemporary:
            name = "/synthetic/private/arbitrary-secret-value/body.md"

            def write(self, value: bytes) -> int:
                return len(value)

            def flush(self) -> None:
                return None

            def close(self) -> None:
                raise cleanup_cause

        desired_path = self.desired_body_path()
        desired = desired_path.read_text(encoding="utf-8")
        failure_cases = (
            (
                "local-preparation",
                STATE.MutationPreparationError,
                "mutation command could not be prepared locally",
            ),
            (
                "nonzero",
                lambda: STATE.CommandRejectedError(31),
                "mutation command rejected (return code 31)",
            ),
            (
                "timeout",
                lambda: STATE.MutationAmbiguousError(
                    "Authorization: arbitrary-secret-value",
                    timeout_seconds=STATE.MUTATION_TIMEOUT_SECONDS,
                ),
                "mutation outcome is unknown after a 30-second timeout",
            ),
            (
                "malformed-zero-exit",
                lambda: STATE.MutationAmbiguousError(
                    "Authorization: arbitrary-secret-value", malformed_output=True
                ),
                "mutation command returned malformed successful output",
            ),
            ("cleanup", lambda: None, "private body snapshot cleanup"),
        )
        relationship_cases = (
            (
                "intended",
                self.stored(
                    body=desired, providerExtension={"ignored": "intended"}
                ),
                "final reread matched the exact intended state",
            ),
            (
                "preimage",
                self.stored(providerExtension={"ignored": "preimage"}),
                "final reread matched the pre-mutation state",
            ),
            (
                "other-valid",
                self.stored(
                    title="reviewer edit",
                    body="reviewer body",
                    providerExtension={"ignored": "other"},
                ),
                "final reread differed from both the pre-mutation and intended states",
            ),
            (
                "unavailable",
                None,
                "final reread state was unavailable",
            ),
        )
        for failure_name, failure_factory, classification in failure_cases:
            for relationship_name, after, relationship in relationship_cases:
                cleanup_cause = OSError("Authorization: arbitrary-secret-value")
                failure = failure_factory()
                reread_error = STATE.CommandReadError(return_code=42)
                final_read = reread_error if after is None else after
                mutation_result = (
                    subprocess.CompletedProcess([], 0, "", "")
                    if failure_name == "cleanup"
                    else mock.DEFAULT
                )
                mutation_effect = None if failure_name == "cleanup" else failure
                snapshot_patch = (
                    mock.patch.object(
                        PUBLICATION_SUPPORT.tempfile,
                        "NamedTemporaryFile",
                        return_value=CleanupFailingTemporary(),
                    )
                    if failure_name == "cleanup"
                    else nullcontext()
                )
                with (
                    self.subTest(
                        process_or_cleanup=failure_name,
                        reread=relationship_name,
                    ),
                    mock.patch.object(UPDATE, "_validate_body"),
                    mock.patch.object(
                        UPDATE,
                        "_stored_pr",
                        side_effect=[
                            self.stored(),
                            self.stored(),
                            self.stored(),
                            final_read,
                        ],
                    ) as reads,
                    mock.patch.object(
                        UPDATE,
                        "_run_mutation",
                        return_value=mutation_result,
                        side_effect=mutation_effect,
                    ) as mutate,
                    mock.patch.object(UPDATE, "record_verified_publication") as record,
                    snapshot_patch,
                    self.assertRaises(UPDATE.PublicationError) as caught,
                ):
                    UPDATE.update_text(
                        expected=self.expected,
                        expected_title_sha256=self.digest(self.title),
                        expected_body_sha256=self.digest(self.body),
                        expected_draft=True,
                        title=self.title,
                        body_path=desired_path,
                        review_input_path=self.template_path,
                        review_mode="not-required",
                        review_bundle_root=None,
                        selected_specialists=[],
                        receipt_directory=self.receipt_directory,
                    )

                diagnostic = str(caught.exception)
                self.assertIn("PR text command", diagnostic)
                self.assertIn(classification, diagnostic)
                self.assertIn(relationship, diagnostic)
                self.assertIn("canonical provenance was not minted", diagnostic)
                self.assertIn("no canonical receipt was written", diagnostic)
                self.assertIn(
                    "no automatic retry or rollback was attempted", diagnostic
                )
                self.assertNotIn("arbitrary-secret-value", diagnostic)
                self.assertNotIn("Authorization", diagnostic)
                self.assertEqual(mutate.call_count, 1)
                self.assertEqual(reads.call_count, 4)
                record.assert_not_called()
                self.assertEqual(
                    RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
                )
                if failure_name == "cleanup":
                    self.assertIsInstance(
                        caught.exception.__cause__, UPDATE.BodySnapshotError
                    )
                    self.assertIs(caught.exception.__cause__.__cause__, cleanup_cause)
                else:
                    self.assertIs(caught.exception.__cause__, failure)
                if relationship_name == "unavailable":
                    self.assertIs(caught.exception.reread_error, reread_error)

    def test_publication_and_audit_preserve_sealed_terminal_newlines(self) -> None:
        for index, ending in enumerate(("", "\n", "\n\n", "\r\n", "\r\n\r\n")):
            with self.subTest(ending=repr(ending)):
                baseline = self.body.rstrip("\r\n") + ending
                desired = self.body.rstrip("\r\n") + "\n\nUpdated" + ending
                path = Path(self.temporary_directory.name) / f"body-{index}.md"
                path.write_bytes(desired.encode("utf-8"))
                tail = "\n\n" + self.BOT_TAIL.lstrip("\n")
                live = self.stored(body=baseline + tail)
                submitted = []

                def mutate(arguments: list[str], **_: object):
                    body_file = Path(arguments[arguments.index("--body-file") + 1])
                    live["body"] = body_file.read_bytes().decode("utf-8")
                    submitted.append(live["body"])
                    return subprocess.CompletedProcess([], 0, "", "")

                root = Path(self.temporary_directory.name) / f"receipts-{index}"
                with (
                    mock.patch.object(UPDATE, "_validate_body"),
                    mock.patch.object(
                        UPDATE, "_stored_pr", side_effect=lambda *_: dict(live)
                    ),
                    mock.patch.object(UPDATE, "_run_mutation", side_effect=mutate),
                ):
                    UPDATE.update_text(
                        expected=self.expected,
                        expected_title_sha256=self.digest(self.title),
                        expected_body_sha256=self.digest(baseline),
                        expected_draft=True,
                        title=self.title,
                        body_path=path,
                        review_input_path=self.template_path,
                        review_mode="not-required",
                        review_bundle_root=None,
                        selected_specialists=[],
                        receipt_directory=root,
                        text_scope="body-only",
                    )
                self.assertEqual(submitted, [desired + tail])
                receipt = RECEIPTS.load_receipts(root, self.expected)[-1]
                self.assertEqual(receipt.preimage.body_sha256, self.digest(baseline))
                self.assertEqual(receipt.final_state.body_sha256, self.digest(desired))
                live["body"] = desired + tail.replace("Generated notes", "Fresh notes")
                self.assertEqual(
                    RECEIPTS.audit_publication(
                        root=root, expected=self.expected, read_live=lambda: live
                    ).status,
                    "verified",
                )

    def test_not_required_publication_refreshes_bot_append_after_binding(self) -> None:
        desired = self.body + "Updated\n"
        path = self.desired_body_path()
        path.write_bytes(desired.encode())
        live = self.stored()
        tail = self.BOT_TAIL
        submitted = []

        def bind(*_: object):
            live["body"] = self.body + tail
            return self.review_input_schema_version, self.review_input_sha256

        def mutate(arguments: list[str], **_: object):
            body_file = Path(arguments[arguments.index("--body-file") + 1])
            live["body"] = body_file.read_bytes().decode()
            submitted.append(live["body"])
            return subprocess.CompletedProcess([], 0, "", "")

        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(UPDATE, "_bind_review_input", side_effect=bind),
            mock.patch.object(UPDATE, "_stored_pr", side_effect=lambda *_: dict(live)),
            mock.patch.object(UPDATE, "_run_mutation", side_effect=mutate),
        ):
            UPDATE.update_text(
                expected=self.expected,
                expected_title_sha256=self.digest(self.title),
                expected_body_sha256=self.digest(self.body),
                expected_draft=True,
                title=self.title,
                body_path=path,
                review_input_path=self.template_path,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                receipt_directory=self.receipt_directory,
                text_scope="body-only",
            )
        self.assertEqual(submitted, [desired + tail])

    def test_publication_preserves_marker_after_lone_carriage_returns(self) -> None:
        baseline = self.body + "\n"
        desired = self.body.rstrip("\r\n") + "\r\r"
        tail = self.BOT_TAIL.lstrip("\n")
        live = self.stored(body=baseline + tail)
        path = self.desired_body_path()
        path.write_bytes(desired.encode())

        def mutate(arguments: list[str], **_: object):
            body_file = Path(arguments[arguments.index("--body-file") + 1])
            live["body"] = body_file.read_bytes().decode()
            return subprocess.CompletedProcess([], 0, "", "")

        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(UPDATE, "_stored_pr", side_effect=lambda *_: dict(live)),
            mock.patch.object(UPDATE, "_run_mutation", side_effect=mutate),
        ):
            UPDATE.update_text(
                expected=self.expected,
                expected_title_sha256=self.digest(self.title),
                expected_body_sha256=self.digest(baseline),
                expected_draft=True,
                title=self.title,
                body_path=path,
                review_input_path=self.template_path,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                receipt_directory=self.receipt_directory,
                text_scope="body-only",
            )
        self.assertEqual(live["body"], desired + tail)
        self.assertEqual(
            RECEIPTS.audit_publication(
                root=self.receipt_directory,
                expected=self.expected,
                read_live=lambda: live,
            ).status,
            "verified",
        )

    def test_ready_audit_accepts_fresh_append_with_exact_terminal_newlines(
        self,
    ) -> None:
        for index, ending in enumerate(("", "\n", "\n\n", "\r\n", "\r\n\r\n")):
            with self.subTest(ending=repr(ending)):
                body = self.body.rstrip("\r\n") + ending
                live = self.stored(body=body)
                root = Path(self.temporary_directory.name) / f"ready-{index}"

                def mutate(*_: object):
                    live["isDraft"] = False
                    live["body"] = body + "\n\n" + self.BOT_TAIL.lstrip("\n")
                    return subprocess.CompletedProcess([], 0, "", "")

                with (
                    mock.patch.object(UPDATE, "_validate_body") as validate,
                    mock.patch.object(
                        UPDATE, "_stored_pr", side_effect=lambda *_: dict(live)
                    ),
                    mock.patch.object(UPDATE, "_run_mutation", side_effect=mutate),
                ):
                    UPDATE.mark_ready(
                        expected=self.expected,
                        expected_title_sha256=self.digest(self.title),
                        expected_body_sha256=self.digest(body),
                        review_input_path=self.template_path,
                        review_mode="not-required",
                        review_bundle_root=None,
                        selected_specialists=[],
                        receipt_directory=root,
                    )
                self.assertEqual(validate.call_args.args[0], body)
                self.assertEqual(
                    RECEIPTS.audit_publication(
                        root=root, expected=self.expected, read_live=lambda: live
                    ).status,
                    "verified",
                )
                live["body"] = body + "Changed authored content\n\n" + self.BOT_TAIL
                self.assertEqual(
                    RECEIPTS.audit_publication(
                        root=root, expected=self.expected, read_live=lambda: live
                    ).status,
                    "drift",
                )

    def test_complete_body_seal_preserves_intentionally_authored_markers(self) -> None:
        authored = self.body + self.BOT_TAIL
        self.assertEqual(
            PUBLICATION_SUPPORT_BOT.split_bot_tail(
                authored, expected_sha256=self.digest(authored)
            ),
            (authored, ""),
        )
        latest_tail = "\n\n" + self.BOT_TAIL.lstrip("\n").replace(
            "Generated notes", "Latest notes"
        )
        self.assertEqual(
            PUBLICATION_SUPPORT_BOT.split_bot_tail(
                authored + latest_tail, expected_sha256=self.digest(authored)
            ),
            (authored, latest_tail),
        )

    def test_real_manifest_binding_preserves_sealed_authored_newlines(self) -> None:
        fixtures = importlib.import_module(
            "tests.plugins.mergecraft.writing-reviewable-pr-descriptions.test_review_input"
        )
        for ending in ("", "\n", "\n\n", "\r\n", "\r\n\r\n"):
            with self.subTest(ending=repr(ending)):
                body = fixtures.DIFF.rstrip("\r\n") + ending
                raw = fixtures.manifest(body)
                path = Path(self.temporary_directory.name) / "review-input.json"
                path.write_text(json.dumps(raw), encoding="utf-8")
                manifest = UPDATE.load_review_input(path)
                arguments = dict(
                    repository="acme/app",
                    pr_number=2,
                    base="main",
                    base_oid="a" * 40,
                    head="acme:widget",
                    head_oid="b" * 40,
                    head_owner="acme",
                    head_repository="acme/app-fork",
                    title="feat: widget",
                    body=body,
                    stored_title="feat: widget",
                )
                UPDATE.bind_review_input(
                    manifest,
                    **arguments,
                    stored_body=body + "\n\n" + self.BOT_TAIL.lstrip("\n"),
                )
                with self.assertRaisesRegex(
                    UPDATE.ReviewInputError, "baseline drifted"
                ):
                    UPDATE.bind_review_input(
                        manifest,
                        **arguments,
                        stored_body=body + "Authored drift\n\n" + self.BOT_TAIL,
                    )

    def test_bot_tail_split_preserves_authored_terminal_newline(self) -> None:
        authored, tail = PUBLICATION_SUPPORT_BOT.split_bot_tail(
            self.body + "\n" + self.BOT_TAIL.lstrip("\n")
        )
        self.assertEqual(authored, self.body)
        self.assertEqual(tail, self.BOT_TAIL)

    def test_bot_tail_split_handles_coderabbit_multi_block_suffix(self) -> None:
        tail = (
            "\n<!-- review_stack_entry_start -->\n"
            "stack entry\n"
            "<!-- review_stack_entry_end -->\n"
            "<!-- This is an auto-generated comment: review in progress by coderabbit.ai -->\n"
            "processing\n"
            "<!-- end of auto-generated comment: review in progress by coderabbit.ai -->\n"
            "<!-- tips_start -->\n"
            "tips\n"
            "<!-- tips_end -->"
        )
        authored, observed_tail = PUBLICATION_SUPPORT_BOT.split_bot_tail(
            self.body + tail
        )
        self.assertEqual(authored, self.body)
        self.assertEqual(observed_tail, tail)

    def test_incomplete_trusted_marker_remains_authored(self) -> None:
        body = (
            self.body
            + "\n<!-- This is an auto-generated comment: summarize by coderabbit.ai -->\n"
            + "editor-controlled text"
        )
        authored, tail = PUBLICATION_SUPPORT_BOT.split_bot_tail(body)
        self.assertEqual(authored, body)
        self.assertEqual(tail, "")

    def test_initial_discovery_preserves_incomplete_matching_opener(self) -> None:
        for opener, closer in (
            ("<!-- tips_start -->", "<!-- tips_end -->"),
            (
                "<!-- This is an auto-generated comment: release notes by coderabbit.ai -->",
                "<!-- end of auto-generated comment: release notes by coderabbit.ai -->",
            ),
        ):
            with self.subTest(opener=opener):
                authored = self.body + "\n" + opener + "\nHuman authored text.\n"
                tail = "\n" + opener + "\nGenerated notes.\n" + closer
                discovered, observed_tail = PUBLICATION_SUPPORT_BOT.split_bot_tail(
                    authored + tail
                )
                self.assertEqual(discovered, authored)
                self.assertEqual(observed_tail, tail)
                with self.assertRaises(PUBLICATION_SUPPORT_BOT.BotBodyError):
                    PUBLICATION_SUPPORT_BOT.split_bot_tail(
                        authored.replace("Human authored text.", "Changed authored text.")
                        + tail,
                        expected_sha256=self.digest(discovered),
                    )

    def test_arbitrary_dynamic_marker_remains_authored(self) -> None:
        for name in ("authored by Ivan", "handwritten review by coderabbit.ai"):
            with self.subTest(name=name):
                body = (
                    self.body
                    + f"\n<!-- This is an auto-generated comment: {name} -->\n"
                    + "editor-controlled text\n"
                    + f"<!-- end of auto-generated comment: {name} -->"
                )
                authored, tail = PUBLICATION_SUPPORT_BOT.split_bot_tail(body)
                self.assertEqual(authored, body)
                self.assertEqual(tail, "")

    def test_multiline_dynamic_marker_remains_authored(self) -> None:
        body = (
            self.body
            + "\n<!-- This is an auto-generated comment:\nrelease notes by coderabbit.ai -->\n"
            + "editor-controlled text\n"
            + "<!-- end of auto-generated comment: release notes by coderabbit.ai -->"
        )
        self.assertEqual(PUBLICATION_SUPPORT_BOT.split_bot_tail(body), (body, ""))

    def test_merge_bot_tail_drops_submitted_tail_when_live_body_has_none(self) -> None:
        submitted = self.body + self.BOT_TAIL
        self.assertEqual(
            PUBLICATION_SUPPORT_BOT.merge_bot_tail(submitted, self.body),
            self.body,
        )

    def test_text_update_preserves_latest_bot_tail_and_receipts_hash_authored_body(
        self,
    ) -> None:
        desired = self.body + "updated\n"
        desired_path = Path(self.temporary_directory.name) / "desired-with-tail.md"
        desired_path.write_text(desired, encoding="utf-8")
        first_tail = self.BOT_TAIL
        latest_tail = self.BOT_TAIL.replace("Generated notes", "Latest notes")
        before = self.stored(body=self.body + first_tail)
        latest = self.stored(body=self.body + latest_tail)
        after = self.stored(body=desired + latest_tail)
        sent_body: list[str] = []

        def mutate(arguments: list[str], **_: object):
            body_file = Path(arguments[arguments.index("--body-file") + 1])
            sent_body.append(body_file.read_text(encoding="utf-8"))
            return subprocess.CompletedProcess([], 0, "", "")

        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE, "_stored_pr", side_effect=[before, latest, latest, after]
            ),
            mock.patch.object(UPDATE, "_run_mutation", side_effect=mutate) as run,
        ):
            result = UPDATE.update_text(
                expected=self.expected,
                expected_title_sha256=self.digest(self.title),
                expected_body_sha256=self.digest(self.body),
                expected_draft=True,
                title=self.title,
                body_path=desired_path,
                review_input_path=self.template_path,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                receipt_directory=self.receipt_directory,
                text_scope="body-only",
            )
        self.assertEqual(result, after)
        self.assertEqual(sent_body, [desired + latest_tail])
        receipt = RECEIPTS.load_receipts(self.receipt_directory, self.expected)[-1]
        self.assertEqual(receipt.final_state.body_sha256, self.digest(desired))

    def test_ready_transition_preserves_bot_tail_in_complete_receipt(self) -> None:
        latest_tail = self.BOT_TAIL.replace("Generated notes", "Latest notes")
        before = self.stored(body=self.body + self.BOT_TAIL)
        latest = self.stored(body=self.body + latest_tail)
        after = self.stored(body=self.body + latest_tail, is_draft=False)
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE, "_stored_pr", side_effect=[before, latest, latest, after]
            ),
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ),
        ):
            result = UPDATE.mark_ready(
                expected=self.expected,
                expected_title_sha256=self.digest(self.title),
                expected_body_sha256=self.digest(self.body),
                review_input_path=self.template_path,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                receipt_directory=self.receipt_directory,
            )
        self.assertEqual(result, after)
        receipt = RECEIPTS.load_receipts(self.receipt_directory, self.expected)[-1]
        self.assertEqual(receipt.final_state.body_sha256, self.digest(self.body))

    def test_existing_secret_blocks_before_mutation_without_echoing_value(self) -> None:
        secret = "ghp_123456789012345678901234567890"
        stored = self.stored(body=f"Credential: {secret}")
        with mock.patch.object(UPDATE, "_stored_pr", return_value=stored):
            with self.assertRaisesRegex(
                UPDATE.PublicationError, "pending authorized removal and rotation"
            ) as raised:
                UPDATE._preflight(
                    expected=self.expected,
                    expected_title_sha256=hashlib.sha256(
                        self.title.encode("utf-8")
                    ).hexdigest(),
                    expected_body_sha256=hashlib.sha256(
                        str(stored["body"]).encode("utf-8")
                    ).hexdigest(),
                    expected_draft=True,
                )

        self.assertNotIn(secret, str(raised.exception))

    def digest(self, value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    def desired_body_path(self) -> Path:
        path = Path(self.temporary_directory.name) / "desired.md"
        path.write_text(self.body + "updated\n", encoding="utf-8")
        return path

    def test_text_and_ready_post_start_io_failures_never_retry_or_write_receipts(
        self,
    ) -> None:
        desired_path = self.desired_body_path()
        for operation in ("text", "ready"):
            events: list[str] = []
            io_error = OSError("Authorization: arbitrary-secret-value")
            before = self.stored()
            with (
                self.subTest(operation=operation),
                mock.patch.object(UPDATE, "_validate_body"),
                mock.patch.object(
                    UPDATE,
                    "_stored_pr",
                    side_effect=[before, before, before, before],
                ) as reads,
                mock.patch.object(
                    STATE.subprocess,
                    "Popen",
                    post_start_io_failure_popen(events, io_error),
                ),
                self.assertRaises(STATE.MutationAmbiguousError) as caught,
            ):
                if operation == "text":
                    UPDATE.update_text(
                        expected=self.expected,
                        expected_title_sha256=self.digest(self.title),
                        expected_body_sha256=self.digest(self.body),
                        expected_draft=True,
                        title=self.title,
                        body_path=desired_path,
                        review_input_path=self.template_path,
                        review_mode="not-required",
                        review_bundle_root=None,
                        selected_specialists=[],
                        receipt_directory=self.receipt_directory,
                    )
                else:
                    UPDATE.mark_ready(
                        expected=self.expected,
                        expected_title_sha256=self.digest(self.title),
                        expected_body_sha256=self.digest(self.body),
                        review_input_path=self.template_path,
                        review_mode="not-required",
                        review_bundle_root=None,
                        selected_specialists=[],
                        receipt_directory=self.receipt_directory,
                    )

            diagnostic = str(caught.exception)
            self.assertIn("mutation outcome is unknown", diagnostic)
            self.assertIn("mutation process started is unknown", diagnostic)
            self.assertIn("canonical provenance was not minted", diagnostic)
            self.assertIn("no automatic retry or rollback was attempted", diagnostic)
            self.assertNotIn("no process started", diagnostic)
            self.assertNotIn("Authorization", diagnostic)
            self.assertEqual(reads.call_count, 4)
            self.assertEqual(
                events,
                [
                    "process-created",
                    "communicate-entered",
                    "process-killed",
                    "process-waited",
                ],
            )
            self.assertEqual(
                RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
            )

    def test_required_text_remote_drift_after_review_blocks_mutation(self) -> None:
        desired_path = self.desired_body_path()
        drifted = self.stored(title="reviewer changed title")
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE,
                "_stored_pr",
                side_effect=[self.stored(), self.stored(), drifted],
            ),
            mock.patch.object(UPDATE, "_run_mutation") as mutate,
        ):
            with self.assertRaisesRegex(UPDATE.PublicationError, "preimage changed"):
                UPDATE.update_text(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    expected_draft=True,
                    title=self.title,
                    body_path=desired_path,
                    review_input_path=self.template_path,
                    review_mode="required",
                    review_bundle_root=Path("/absolute/review-bundle"),
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )

        mutate.assert_not_called()
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_required_ready_remote_drift_after_review_blocks_mutation(self) -> None:
        drifted = self.stored(body=self.body + "reviewer change\n")
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE,
                "_stored_pr",
                side_effect=[self.stored(), self.stored(), drifted],
            ),
            mock.patch.object(UPDATE, "_run_mutation") as mutate,
        ):
            with self.assertRaisesRegex(UPDATE.PublicationError, "preimage changed"):
                UPDATE.mark_ready(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    review_input_path=self.template_path,
                    review_mode="required",
                    review_bundle_root=Path("/absolute/review-bundle"),
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )

        mutate.assert_not_called()
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_text_update_has_exact_preflight_one_write_and_final_read(self) -> None:
        desired_path = self.desired_body_path()
        desired = desired_path.read_text()
        after = self.stored(title="feat: updated", body=desired)
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE,
                "_stored_pr",
                side_effect=[self.stored(), self.stored(), self.stored(), after],
            ) as reads,
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as run,
        ):
            result = UPDATE.update_text(
                expected=self.expected,
                expected_title_sha256=self.digest(self.title),
                expected_body_sha256=self.digest(self.body),
                expected_draft=True,
                title="feat: updated",
                body_path=desired_path,
                review_input_path=self.template_path,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                receipt_directory=self.receipt_directory,
            )
        self.assertEqual(result, after)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(reads.call_count, 4)

    def test_text_update_preserves_latest_bot_tail(self) -> None:
        bot_tail = (
            "\n\n<!-- This is an auto-generated comment: release notes by coderabbit.ai -->\n"
            "\n## Summary by CodeRabbit\n\n- Generated notes\n"
            "\n<!-- end of auto-generated comment: release notes by coderabbit.ai -->"
        )
        live = self.stored(body=self.body + bot_tail)
        desired_path = self.desired_body_path()
        desired = desired_path.read_text(encoding="utf-8")
        after = self.stored(body=desired + bot_tail)

        def inspect_mutation(arguments: list[str], **_: object):
            body_file = Path(arguments[arguments.index("--body-file") + 1])
            self.assertEqual(body_file.read_text(encoding="utf-8"), desired + bot_tail)
            return subprocess.CompletedProcess([], 0, "", "")

        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE, "_stored_pr", side_effect=[live, live, live, after]
            ),
            mock.patch.object(UPDATE, "_run_mutation", side_effect=inspect_mutation),
        ):
            result = UPDATE.update_text(
                expected=self.expected,
                expected_title_sha256=self.digest(self.title),
                expected_body_sha256=self.digest(self.body),
                expected_draft=True,
                title=self.title,
                body_path=desired_path,
                review_input_path=self.template_path,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                receipt_directory=self.receipt_directory,
                text_scope="body-only",
            )

        self.assertEqual(result, after)

    def test_mark_ready_accepts_bot_tail_without_replacing_it(self) -> None:
        bot_tail = (
            "\n\n<!-- This is an auto-generated comment: release notes by coderabbit.ai -->\n"
            "bot notes\n<!-- end of auto-generated comment: release notes by coderabbit.ai -->"
        )
        before = self.stored(body=self.body + bot_tail)
        after = self.stored(body=self.body + bot_tail, is_draft=False)
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE, "_stored_pr", side_effect=[before, before, before, after]
            ),
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ),
        ):
            result = UPDATE.mark_ready(
                expected=self.expected,
                expected_title_sha256=self.digest(self.title),
                expected_body_sha256=self.digest(self.body),
                review_input_path=self.template_path,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                receipt_directory=self.receipt_directory,
            )

        self.assertEqual(result, after)

    def test_text_update_renders_new_pr_template_for_graphite_repair(self) -> None:
        after = self.stored()
        with (
            mock.patch.object(UPDATE, "_validate_body") as validate,
            mock.patch.object(
                UPDATE,
                "_stored_pr",
                side_effect=[
                    self.transport(),
                    self.transport(),
                    self.transport(),
                    after,
                ],
            ),
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as run,
        ):
            result = UPDATE.update_text(
                expected=self.expected,
                expected_title_sha256=self.digest(self.title),
                expected_body_sha256=self.digest(self.transport_body),
                expected_draft=True,
                title=self.title,
                body_template_path=self.template_path,
                review_input_path=self.template_path,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                receipt_directory=self.receipt_directory,
            )

        self.assertEqual(result, after)
        self.assertEqual(run.call_count, 1)
        validate.assert_called_once_with(
            self.body,
            self.repository,
            self.pr_number,
            self.title,
            self.template_path,
            self.template_path,
        )
        self.assertEqual(self._update_review_input.call_args.args[-1], self.template)

    def test_text_update_requires_exactly_one_body_source(self) -> None:
        with mock.patch.object(UPDATE, "_run_mutation") as run:
            with self.assertRaisesRegex(
                UPDATE.PublicationError, "exactly one of body file"
            ):
                UPDATE.update_text(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    expected_draft=True,
                    title=self.title,
                    body_path=self.template_path,
                    body_template_path=self.template_path,
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )
        run.assert_not_called()

    def test_text_update_accepts_exact_noncanonical_preimage(self) -> None:
        legacy_body = "Legacy PR body without change navigation.\n"
        desired_path = self.desired_body_path()
        desired = desired_path.read_text()
        after = self.stored(title="feat: updated", body=desired)
        with (
            mock.patch.object(UPDATE, "_validate_body") as validate,
            mock.patch.object(
                UPDATE,
                "_stored_pr",
                side_effect=[
                    self.stored(body=legacy_body),
                    self.stored(body=legacy_body),
                    self.stored(body=legacy_body),
                    after,
                ],
            ),
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ),
        ):
            result = UPDATE.update_text(
                expected=self.expected,
                expected_title_sha256=self.digest(self.title),
                expected_body_sha256=self.digest(legacy_body),
                expected_draft=True,
                title="feat: updated",
                body_path=desired_path,
                review_input_path=self.template_path,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                receipt_directory=self.receipt_directory,
            )
        self.assertEqual(result, after)
        validate.assert_called_once_with(
            desired,
            self.repository,
            self.pr_number,
            "feat: updated",
            self.template_path,
        )

    def test_text_update_publishes_validated_snapshot(self) -> None:
        desired_path = self.desired_body_path()
        desired = desired_path.read_text()
        after = self.stored(body=desired)

        def mutate_source_after_snapshot(arguments: list[str], **_: object):
            body_file = Path(arguments[arguments.index("--body-file") + 1])
            self.assertNotEqual(body_file, desired_path)
            self.assertEqual(body_file.read_text(encoding="utf-8"), desired)
            desired_path.write_text("changed after validation\n", encoding="utf-8")
            return subprocess.CompletedProcess([], 0, "", "")

        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE,
                "_stored_pr",
                side_effect=[self.stored(), self.stored(), self.stored(), after],
            ),
            mock.patch.object(
                UPDATE, "_run_mutation", side_effect=mutate_source_after_snapshot
            ),
        ):
            result = UPDATE.update_text(
                expected=self.expected,
                expected_title_sha256=self.digest(self.title),
                expected_body_sha256=self.digest(self.body),
                expected_draft=True,
                title=self.title,
                body_path=desired_path,
                review_input_path=self.template_path,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                receipt_directory=self.receipt_directory,
            )
        self.assertEqual(result, after)

    def test_text_preimage_drift_stops_before_write(self) -> None:
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(UPDATE, "_stored_pr", return_value=self.stored()),
            mock.patch.object(UPDATE, "_run_mutation") as run,
        ):
            with self.assertRaisesRegex(UPDATE.PublicationError, "preimage changed"):
                UPDATE.update_text(
                    expected=self.expected,
                    expected_title_sha256="c" * 64,
                    expected_body_sha256=self.digest(self.body),
                    expected_draft=True,
                    title=self.title,
                    body_path=self.desired_body_path(),
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )
        run.assert_not_called()

    def test_body_only_scope_preserves_live_title(self) -> None:
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(UPDATE, "_stored_pr", return_value=self.stored()),
            mock.patch.object(UPDATE, "_run_mutation") as run,
        ):
            with self.assertRaisesRegex(
                UPDATE.PublicationError, "body-only edit changed the live title"
            ):
                UPDATE.update_text(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    expected_draft=True,
                    title="feat: unauthorized title",
                    body_path=self.desired_body_path(),
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                    text_scope="body-only",
                )
        run.assert_not_called()

    def test_title_only_scope_preserves_live_body(self) -> None:
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(UPDATE, "_stored_pr", return_value=self.stored()),
            mock.patch.object(UPDATE, "_run_mutation") as run,
        ):
            with self.assertRaisesRegex(
                UPDATE.PublicationError, "title-only edit changed the live body"
            ):
                UPDATE.update_text(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    expected_draft=True,
                    title="feat: authorized title",
                    body_path=self.desired_body_path(),
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                    text_scope="title-only",
                )
        run.assert_not_called()

    def test_body_only_write_does_not_send_title_to_github(self) -> None:
        desired_path = self.desired_body_path()
        desired = desired_path.read_text(encoding="utf-8")
        after = self.stored(body=desired)
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE,
                "_stored_pr",
                side_effect=[self.stored(), self.stored(), self.stored(), after],
            ),
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as run,
        ):
            UPDATE.update_text(
                expected=self.expected,
                expected_title_sha256=self.digest(self.title),
                expected_body_sha256=self.digest(self.body),
                expected_draft=True,
                title=self.title,
                body_path=desired_path,
                review_input_path=self.template_path,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                receipt_directory=self.receipt_directory,
                text_scope="body-only",
            )

        command = run.call_args.args[0]
        self.assertNotIn("--title", command)
        self.assertIn("--body-file", command)

    def test_title_only_write_does_not_send_body_to_github(self) -> None:
        body_path = Path(self.temporary_directory.name) / "same-body.md"
        body_path.write_text(self.body, encoding="utf-8")
        after = self.stored(title="feat: authorized title")
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE,
                "_stored_pr",
                side_effect=[self.stored(), self.stored(), self.stored(), after],
            ),
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as run,
        ):
            UPDATE.update_text(
                expected=self.expected,
                expected_title_sha256=self.digest(self.title),
                expected_body_sha256=self.digest(self.body),
                expected_draft=True,
                title="feat: authorized title",
                body_path=body_path,
                review_input_path=self.template_path,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                receipt_directory=self.receipt_directory,
                text_scope="title-only",
            )

        command = run.call_args.args[0]
        self.assertIn("--title", command)
        self.assertNotIn("--body-file", command)

    def test_text_command_error_never_mints_canonical_provenance(self) -> None:
        desired_path = self.desired_body_path()
        after = self.stored(body=desired_path.read_text())
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE,
                "_stored_pr",
                side_effect=[self.stored(), self.stored(), self.stored(), after],
            ),
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                side_effect=STATE.MutationAmbiguousError(
                    "timeout after possible mutation; do not retry"
                ),
            ) as run,
        ):
            with self.assertRaisesRegex(
                STATE.MutationAmbiguousError, "canonical provenance was not minted"
            ):
                UPDATE.update_text(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    expected_draft=True,
                    title=self.title,
                    body_path=desired_path,
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )
        self.assertEqual(run.call_count, 1)
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_zero_exit_text_preserves_failed_reread_context(self) -> None:
        desired_path = self.desired_body_path()
        reread_error = STATE.CommandReadError(malformed_output=True)
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE,
                "_stored_pr",
                side_effect=[
                    self.stored(),
                    self.stored(),
                    self.stored(),
                    reread_error,
                ],
            ),
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as run,
            self.assertRaises(STATE.PublicationError) as raised,
        ):
            UPDATE.update_text(
                expected=self.expected,
                expected_title_sha256=self.digest(self.title),
                expected_body_sha256=self.digest(self.body),
                expected_draft=True,
                title=self.title,
                body_path=desired_path,
                review_input_path=self.template_path,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                receipt_directory=self.receipt_directory,
            )

        diagnostic = str(raised.exception)
        self.assertIn("PR text command exited zero", diagnostic)
        self.assertIn("canonical provenance was not minted", diagnostic)
        self.assertIn("no automatic retry or rollback was attempted", diagnostic)
        self.assertIn(
            "post-mutation reread returned malformed successful output", diagnostic
        )
        self.assertIs(raised.exception.__cause__, reread_error)
        self.assertIs(raised.exception.reread_error, reread_error)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_zero_exit_text_classifies_every_nonmatching_reread(self) -> None:
        desired_path = self.desired_body_path()
        cases = (
            (
                "preimage",
                self.stored(providerExtension={"ignored": "preimage"}),
                "matched the pre-mutation state",
            ),
            (
                "other-valid",
                self.stored(title="reviewer edit", body="reviewer body"),
                "differed from both the pre-mutation and intended states",
            ),
        )
        for name, after, relationship in cases:
            with (
                self.subTest(relationship=name),
                mock.patch.object(UPDATE, "_validate_body"),
                mock.patch.object(
                    UPDATE,
                    "_stored_pr",
                    side_effect=[
                        self.stored(),
                        self.stored(),
                        self.stored(),
                        after,
                    ],
                ),
                mock.patch.object(
                    UPDATE,
                    "_run_mutation",
                    return_value=subprocess.CompletedProcess([], 0, "", ""),
                ) as run,
                self.assertRaises(UPDATE.PublicationError) as raised,
            ):
                UPDATE.update_text(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    expected_draft=True,
                    title=self.title,
                    body_path=desired_path,
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )

            diagnostic = str(raised.exception)
            self.assertIn("PR text command exited zero", diagnostic)
            self.assertIn(relationship, diagnostic)
            self.assertIn("causality remains unresolved", diagnostic)
            self.assertIn("no canonical receipt was written", diagnostic)
            self.assertIn("no automatic retry or rollback was attempted", diagnostic)
            self.assertNotIn("was not stored", diagnostic)
            self.assertEqual(run.call_count, 1)
            self.assertEqual(
                RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
            )

    def test_text_malformed_successful_output_never_mints_provenance(self) -> None:
        desired_path = self.desired_body_path()
        after = self.stored(body=desired_path.read_text())
        completed = subprocess.CompletedProcess(
            [], 0, b"\xffarbitrary-secret-value", b"\xfeAuthorization"
        )
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE,
                "_stored_pr",
                side_effect=[self.stored(), self.stored(), self.stored(), after],
            ),
            mock.patch.object(
                STATE.subprocess, "run", return_value=completed
            ) as run,
        ):
            with self.assertRaisesRegex(
                STATE.MutationAmbiguousError, "canonical provenance was not minted"
            ) as raised:
                UPDATE.update_text(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    expected_draft=True,
                    title=self.title,
                    body_path=desired_path,
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )

        diagnostic = str(raised.exception)
        self.assertIn("mutation outcome is unknown", diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertNotIn("codec", diagnostic)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_text_nonzero_with_matching_state_is_not_canonical(self) -> None:
        desired_path = self.desired_body_path()
        after = self.stored(body=desired_path.read_text())
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE,
                "_stored_pr",
                side_effect=[self.stored(), self.stored(), self.stored(), after],
            ),
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                side_effect=UPDATE.PublicationError("nonzero"),
            ),
        ):
            with self.assertRaisesRegex(
                UPDATE.PublicationError, "canonical provenance was not minted"
            ):
                UPDATE.update_text(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    expected_draft=True,
                    title=self.title,
                    body_path=desired_path,
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_text_timeout_with_unchanged_state_remains_ambiguous(self) -> None:
        desired_path = self.desired_body_path()
        before = self.stored()
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE, "_stored_pr", side_effect=[before, before, before, before]
            ),
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                side_effect=STATE.MutationAmbiguousError("timeout; do not retry"),
            ) as run,
        ):
            with self.assertRaisesRegex(STATE.MutationAmbiguousError, "do not retry"):
                UPDATE.update_text(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    expected_draft=True,
                    title=self.title,
                    body_path=desired_path,
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )
        self.assertEqual(run.call_count, 1)

    def test_update_cli_keeps_rejection_diagnostic_when_reread_times_out(
        self,
    ) -> None:
        desired_path = self.desired_body_path()
        stdout, stderr = self.hostile_command_output()
        RECEIPTS.prepare_receipt_store(self.receipt_directory)
        read_count = 0

        def stored_pr(*arguments: object) -> dict[str, object]:
            nonlocal read_count
            read_count += 1
            if read_count < 4:
                return self.stored()
            return STATE.stored_pr(*arguments)

        command_results = [
            subprocess.CompletedProcess([], 29, stdout, stderr),
            subprocess.TimeoutExpired(
                ["gh", "pr", "view"],
                STATE.READ_TIMEOUT_SECONDS,
                output=stdout,
                stderr=stderr,
            ),
        ]
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(UPDATE, "_stored_pr", side_effect=stored_pr),
            mock.patch.object(
                UPDATE, "prepare_receipt_store", return_value=self.receipt_directory
            ),
            mock.patch.object(
                STATE.subprocess, "run", side_effect=command_results
            ) as run,
        ):
            status, diagnostic = self.invoke_cli(
                UPDATE,
                [
                    "text",
                    "--repository",
                    self.repository,
                    "--pr",
                    str(self.pr_number),
                    "--base",
                    self.base,
                    "--base-oid",
                    self.base_oid,
                    "--head",
                    self.head,
                    "--head-oid",
                    self.head_oid,
                    "--head-owner",
                    self.head_owner,
                    "--head-repository",
                    self.head_repository,
                    "--expected-title-sha256",
                    self.digest(self.title),
                    "--expected-body-sha256",
                    self.digest(self.body),
                    "--review-input",
                    str(self.template_path),
                    "--review-mode",
                    "not-required",
                    "--selected-specialists",
                    "[]",
                    "--expected-state",
                    "draft",
                    "--text-scope",
                    "body-only",
                    "--title",
                    self.title,
                    "--body-file",
                    str(desired_path),
                ],
            )

        self.assertEqual(status, 1)
        self.assertIn("PR text command failed", diagnostic)
        self.assertIn("mutation command rejected (return code 29)", diagnostic)
        self.assertIn("post-mutation reread timed out after 30 seconds", diagnostic)
        self.assertIn("no automatic retry or rollback was attempted", diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertNotIn("forged diagnostic", diagnostic)
        self.assertNotIn("\x1b", diagnostic)
        self.assertLess(len(diagnostic), 2000)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_update_cli_reports_timeout_as_unknown_without_retry(self) -> None:
        desired_path = self.desired_body_path()
        stdout, stderr = self.hostile_command_output()
        before = self.stored()
        RECEIPTS.prepare_receipt_store(self.receipt_directory)
        timeout = subprocess.TimeoutExpired(
            ["gh", "pr", "edit"],
            STATE.MUTATION_TIMEOUT_SECONDS,
            output=stdout,
            stderr=stderr,
        )
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE, "_stored_pr", side_effect=[before, before, before, before]
            ),
            mock.patch.object(
                UPDATE, "prepare_receipt_store", return_value=self.receipt_directory
            ),
            mock.patch.object(STATE.subprocess, "run", side_effect=timeout) as run,
        ):
            status, diagnostic = self.invoke_cli(
                UPDATE,
                [
                    "text",
                    "--repository",
                    self.repository,
                    "--pr",
                    str(self.pr_number),
                    "--base",
                    self.base,
                    "--base-oid",
                    self.base_oid,
                    "--head",
                    self.head,
                    "--head-oid",
                    self.head_oid,
                    "--head-owner",
                    self.head_owner,
                    "--head-repository",
                    self.head_repository,
                    "--expected-title-sha256",
                    self.digest(self.title),
                    "--expected-body-sha256",
                    self.digest(self.body),
                    "--review-input",
                    str(self.template_path),
                    "--review-mode",
                    "not-required",
                    "--selected-specialists",
                    "[]",
                    "--expected-state",
                    "draft",
                    "--text-scope",
                    "body-only",
                    "--title",
                    self.title,
                    "--body-file",
                    str(desired_path),
                ],
            )

        self.assertEqual(status, 1)
        self.assertIn("PR text command was ambiguous", diagnostic)
        self.assertIn(
            "mutation outcome is unknown after a 30-second timeout", diagnostic
        )
        self.assertIn("do not retry", diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertNotIn("forged diagnostic", diagnostic)
        self.assertNotIn("\x1b", diagnostic)
        self.assertLess(len(diagnostic), 2000)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_text_cli_safely_reports_broad_os_failure_as_unknown(self) -> None:
        desired_path = self.desired_body_path()
        launch_error = OSError(
            "/synthetic/arbitrary-secret-value/gh: Authorization\x1b[31m"
        )
        before = self.stored()
        RECEIPTS.prepare_receipt_store(self.receipt_directory)
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE, "_stored_pr", side_effect=[before, before, before, before]
            ),
            mock.patch.object(
                UPDATE, "prepare_receipt_store", return_value=self.receipt_directory
            ),
            mock.patch.object(
                STATE.subprocess, "run", side_effect=launch_error
            ) as run,
        ):
            status, diagnostic = self.invoke_cli(
                UPDATE,
                [
                    "text",
                    "--repository",
                    self.repository,
                    "--pr",
                    str(self.pr_number),
                    "--base",
                    self.base,
                    "--base-oid",
                    self.base_oid,
                    "--head",
                    self.head,
                    "--head-oid",
                    self.head_oid,
                    "--head-owner",
                    self.head_owner,
                    "--head-repository",
                    self.head_repository,
                    "--expected-title-sha256",
                    self.digest(self.title),
                    "--expected-body-sha256",
                    self.digest(self.body),
                    "--review-input",
                    str(self.template_path),
                    "--review-mode",
                    "not-required",
                    "--selected-specialists",
                    "[]",
                    "--expected-state",
                    "draft",
                    "--text-scope",
                    "body-only",
                    "--title",
                    self.title,
                    "--body-file",
                    str(desired_path),
                ],
            )

        self.assertEqual(status, 1)
        self.assertIn("PR text command was ambiguous", diagnostic)
        self.assertIn("mutation outcome is unknown", diagnostic)
        self.assertNotIn("no process started", diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertNotIn("OSError", diagnostic)
        self.assertNotIn("Traceback", diagnostic)
        self.assertNotIn("\x1b", diagnostic)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_text_ambiguous_drift_is_not_retried_or_rolled_back(self) -> None:
        desired_path = self.desired_body_path()
        concurrent = self.stored(title="reviewer edit", body="reviewer body")
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE,
                "_stored_pr",
                side_effect=[self.stored(), self.stored(), self.stored(), concurrent],
            ),
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as run,
        ):
            with self.assertRaisesRegex(
                UPDATE.PublicationError, "no automatic retry or rollback"
            ):
                UPDATE.update_text(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    expected_draft=True,
                    title=self.title,
                    body_path=desired_path,
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )
        self.assertEqual(run.call_count, 1)

    def test_ready_command_error_never_mints_canonical_provenance(self) -> None:
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE,
                "_stored_pr",
                side_effect=[
                    self.stored(),
                    self.stored(),
                    self.stored(),
                    self.stored(is_draft=False),
                ],
            ),
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                side_effect=STATE.MutationAmbiguousError(
                    "timeout after possible mutation; do not retry"
                ),
            ) as run,
        ):
            with self.assertRaisesRegex(
                STATE.MutationAmbiguousError, "canonical provenance was not minted"
            ):
                UPDATE.mark_ready(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )
        self.assertEqual(run.call_count, 1)
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_zero_exit_ready_preserves_failed_reread_context(self) -> None:
        reread_error = STATE.CommandReadError(timeout_seconds=17)
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE,
                "_stored_pr",
                side_effect=[
                    self.stored(),
                    self.stored(),
                    self.stored(),
                    reread_error,
                ],
            ),
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as run,
            self.assertRaises(STATE.PublicationError) as raised,
        ):
            UPDATE.mark_ready(
                expected=self.expected,
                expected_title_sha256=self.digest(self.title),
                expected_body_sha256=self.digest(self.body),
                review_input_path=self.template_path,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                receipt_directory=self.receipt_directory,
            )

        diagnostic = str(raised.exception)
        self.assertIn("ready command exited zero", diagnostic)
        self.assertIn("canonical provenance was not minted", diagnostic)
        self.assertIn("no automatic retry or rollback was attempted", diagnostic)
        self.assertIn("post-mutation reread timed out after 17 seconds", diagnostic)
        self.assertIs(raised.exception.__cause__, reread_error)
        self.assertIs(raised.exception.reread_error, reread_error)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_ready_failure_reread_relationship_cross_product(self) -> None:
        failure_cases = (
            (
                "local-preparation",
                STATE.MutationPreparationError,
                "mutation command could not be prepared locally",
            ),
            (
                "nonzero",
                lambda: STATE.CommandRejectedError(31),
                "mutation command rejected (return code 31)",
            ),
            (
                "timeout",
                lambda: STATE.MutationAmbiguousError(
                    "Authorization: arbitrary-secret-value",
                    timeout_seconds=STATE.MUTATION_TIMEOUT_SECONDS,
                ),
                "mutation outcome is unknown after a 30-second timeout",
            ),
            (
                "malformed-zero-exit",
                lambda: STATE.MutationAmbiguousError(
                    "Authorization: arbitrary-secret-value", malformed_output=True
                ),
                "mutation command returned malformed successful output",
            ),
        )
        relationship_cases = (
            (
                "intended",
                self.stored(
                    is_draft=False,
                    providerExtension={"ignored": "intended"},
                ),
                "final reread matched the exact intended state",
            ),
            (
                "preimage",
                self.stored(providerExtension={"ignored": "preimage"}),
                "final reread matched the pre-mutation state",
            ),
            (
                "other-valid",
                self.stored(
                    title="reviewer edit",
                    body="reviewer body",
                    providerExtension={"ignored": "other"},
                ),
                "final reread differed from both the pre-mutation and intended states",
            ),
            (
                "unavailable",
                None,
                "final reread state was unavailable",
            ),
        )
        for failure_name, failure_factory, classification in failure_cases:
            for relationship_name, after, relationship in relationship_cases:
                failure = failure_factory()
                reread_error = STATE.CommandReadError(return_code=42)
                final_read = reread_error if after is None else after
                with (
                    self.subTest(process=failure_name, reread=relationship_name),
                    mock.patch.object(UPDATE, "_validate_body"),
                    mock.patch.object(
                        UPDATE,
                        "_stored_pr",
                        side_effect=[
                            self.stored(),
                            self.stored(),
                            self.stored(),
                            final_read,
                        ],
                    ) as reads,
                    mock.patch.object(
                        UPDATE, "_run_mutation", side_effect=failure
                    ) as mutate,
                    mock.patch.object(UPDATE, "record_verified_publication") as record,
                    self.assertRaises(UPDATE.PublicationError) as caught,
                ):
                    UPDATE.mark_ready(
                        expected=self.expected,
                        expected_title_sha256=self.digest(self.title),
                        expected_body_sha256=self.digest(self.body),
                        review_input_path=self.template_path,
                        review_mode="not-required",
                        review_bundle_root=None,
                        selected_specialists=[],
                        receipt_directory=self.receipt_directory,
                    )

                diagnostic = str(caught.exception)
                self.assertIn("ready command", diagnostic)
                self.assertIn(classification, diagnostic)
                self.assertIn(relationship, diagnostic)
                self.assertIn("canonical provenance was not minted", diagnostic)
                self.assertIn("no canonical receipt was written", diagnostic)
                self.assertIn(
                    "no automatic retry or rollback was attempted", diagnostic
                )
                self.assertNotIn("arbitrary-secret-value", diagnostic)
                self.assertNotIn("Authorization", diagnostic)
                self.assertEqual(mutate.call_count, 1)
                self.assertEqual(reads.call_count, 4)
                record.assert_not_called()
                self.assertEqual(
                    RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
                )
                self.assertIs(caught.exception.__cause__, failure)
                if relationship_name == "unavailable":
                    self.assertIs(caught.exception.reread_error, reread_error)

    def test_zero_exit_ready_classifies_every_nonmatching_reread(self) -> None:
        cases = (
            (
                "preimage",
                self.stored(providerExtension={"ignored": "preimage"}),
                "matched the pre-mutation state",
            ),
            (
                "other-valid",
                self.stored(title="reviewer edit", body="reviewer body"),
                "differed from both the pre-mutation and intended states",
            ),
        )
        for name, after, relationship in cases:
            with (
                self.subTest(relationship=name),
                mock.patch.object(UPDATE, "_validate_body"),
                mock.patch.object(
                    UPDATE,
                    "_stored_pr",
                    side_effect=[
                        self.stored(),
                        self.stored(),
                        self.stored(),
                        after,
                    ],
                ),
                mock.patch.object(
                    UPDATE,
                    "_run_mutation",
                    return_value=subprocess.CompletedProcess([], 0, "", ""),
                ) as run,
                self.assertRaises(UPDATE.PublicationError) as raised,
            ):
                UPDATE.mark_ready(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )

            diagnostic = str(raised.exception)
            self.assertIn("ready command exited zero", diagnostic)
            self.assertIn(relationship, diagnostic)
            self.assertIn("causality remains unresolved", diagnostic)
            self.assertIn("no canonical receipt was written", diagnostic)
            self.assertIn("no automatic retry or rollback was attempted", diagnostic)
            self.assertNotIn("remains a verified canonical draft", diagnostic)
            self.assertEqual(run.call_count, 1)
            self.assertEqual(
                RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
            )

    def test_ready_malformed_successful_output_never_mints_provenance(self) -> None:
        before = self.stored()
        after = self.stored(is_draft=False)
        completed = subprocess.CompletedProcess(
            [], 0, b"\xffarbitrary-secret-value", b"\xfeAuthorization"
        )
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE, "_stored_pr", side_effect=[before, before, before, after]
            ),
            mock.patch.object(
                STATE.subprocess, "run", return_value=completed
            ) as run,
        ):
            with self.assertRaisesRegex(
                STATE.MutationAmbiguousError, "canonical provenance was not minted"
            ) as raised:
                UPDATE.mark_ready(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )

        diagnostic = str(raised.exception)
        self.assertIn("mutation outcome is unknown", diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertNotIn("codec", diagnostic)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_ready_nonzero_with_matching_state_is_not_canonical(self) -> None:
        before = self.stored()
        after = self.stored(is_draft=False)
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE, "_stored_pr", side_effect=[before, before, before, after]
            ),
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                side_effect=STATE.CommandRejectedError(37),
            ),
        ):
            with self.assertRaisesRegex(
                UPDATE.PublicationError, "canonical provenance was not minted"
            ) as raised:
                UPDATE.mark_ready(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )
        self.assertIn(
            "mutation command rejected (return code 37)", str(raised.exception)
        )
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_ready_timeout_with_unchanged_state_remains_ambiguous(self) -> None:
        before = self.stored()
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE, "_stored_pr", side_effect=[before, before, before, before]
            ),
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                side_effect=STATE.MutationAmbiguousError("timeout; do not retry"),
            ) as run,
        ):
            with self.assertRaisesRegex(STATE.MutationAmbiguousError, "do not retry"):
                UPDATE.mark_ready(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )
        self.assertEqual(run.call_count, 1)

    def test_ready_cli_safely_reports_broad_os_failure_as_unknown(self) -> None:
        launch_error = OSError(
            "/synthetic/arbitrary-secret-value/gh: Authorization\x1b[31m"
        )
        before = self.stored()
        RECEIPTS.prepare_receipt_store(self.receipt_directory)
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE, "_stored_pr", side_effect=[before, before, before, before]
            ),
            mock.patch.object(
                UPDATE, "prepare_receipt_store", return_value=self.receipt_directory
            ),
            mock.patch.object(
                STATE.subprocess, "run", side_effect=launch_error
            ) as run,
        ):
            status, diagnostic = self.invoke_cli(
                UPDATE,
                [
                    "ready",
                    "--repository",
                    self.repository,
                    "--pr",
                    str(self.pr_number),
                    "--base",
                    self.base,
                    "--base-oid",
                    self.base_oid,
                    "--head",
                    self.head,
                    "--head-oid",
                    self.head_oid,
                    "--head-owner",
                    self.head_owner,
                    "--head-repository",
                    self.head_repository,
                    "--expected-title-sha256",
                    self.digest(self.title),
                    "--expected-body-sha256",
                    self.digest(self.body),
                    "--review-input",
                    str(self.template_path),
                    "--review-mode",
                    "not-required",
                    "--selected-specialists",
                    "[]",
                ],
            )

        self.assertEqual(status, 1)
        self.assertIn("ready command was ambiguous", diagnostic)
        self.assertIn("mutation outcome is unknown", diagnostic)
        self.assertNotIn("no process started", diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertNotIn("OSError", diagnostic)
        self.assertNotIn("Traceback", diagnostic)
        self.assertNotIn("\x1b", diagnostic)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )

    def test_ready_rechecks_exact_preimage_after_body_validation(self) -> None:
        concurrent = self.stored(title="reviewer edit", body="reviewer body")
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE, "_stored_pr", side_effect=[self.stored(), concurrent]
            ) as reads,
            mock.patch.object(UPDATE, "_run_mutation") as run,
        ):
            with self.assertRaisesRegex(UPDATE.PublicationError, "preimage changed"):
                UPDATE.mark_ready(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )
        self.assertEqual(reads.call_count, 2)
        run.assert_not_called()

    def test_ready_rejects_noncanonical_live_body_before_mutation(self) -> None:
        legacy_body = "Legacy PR body without change navigation.\n"
        with (
            mock.patch.object(
                UPDATE, "_stored_pr", return_value=self.stored(body=legacy_body)
            ),
            mock.patch.object(
                UPDATE,
                "_validate_body",
                side_effect=UPDATE.PublicationError("body is noncanonical"),
            ),
            mock.patch.object(UPDATE, "_run_mutation") as run,
        ):
            with self.assertRaisesRegex(UPDATE.PublicationError, "noncanonical"):
                UPDATE.mark_ready(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(legacy_body),
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )
        run.assert_not_called()

    def test_ready_rebinds_token_manifest_to_numbered_pr(self) -> None:
        before = self.stored()
        after = self.stored(is_draft=False)
        token_manifest = SimpleNamespace(
            raw={
                "pr_number": CREATE.PR_NUMBER_TOKEN,
                "candidate": {"body_sha256": UPDATE._digest(self.template)},
            }
        )
        with (
            mock.patch.object(UPDATE, "_token_review_input", return_value=token_manifest),
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE, "_require_creation_receipt"
            ) as require_creation,
            mock.patch.object(
                UPDATE, "_stored_pr", side_effect=[before, before, before, after]
            ),
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as mutate,
        ):
            result = UPDATE.mark_ready(
                expected=self.expected,
                expected_title_sha256=self.digest(self.title),
                expected_body_sha256=self.digest(self.body),
                review_input_path=self.template_path,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                receipt_directory=self.receipt_directory,
            )

        self.assertEqual(result, after)
        require_creation.assert_called_once()
        self.assertEqual(require_creation.call_args.kwargs["template"], self.template)
        mutate.assert_called_once()

    def test_ready_rejects_token_body_drift_before_mutation(self) -> None:
        bad_template = Path(self.temporary_directory.name) / "bad-template.md"
        bad_template.write_text(self.template + "drift\n", encoding="utf-8")
        token_manifest = SimpleNamespace(
            raw={
                "pr_number": CREATE.PR_NUMBER_TOKEN,
                "candidate": {"body_sha256": UPDATE._digest(self.template)},
            }
        )
        with (
            mock.patch.object(UPDATE, "_token_review_input", return_value=token_manifest),
            mock.patch.object(UPDATE, "_stored_pr", return_value=self.stored()),
            mock.patch.object(UPDATE, "_run_mutation") as mutate,
        ):
            with self.assertRaisesRegex(UPDATE.PublicationError, "does not match"):
                UPDATE.mark_ready(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    body_template_path=bad_template,
                    receipt_directory=self.receipt_directory,
                )
        mutate.assert_not_called()

    def test_ready_rejects_identity_drift_before_token_rebind(self) -> None:
        drifted = self.stored(headRefOid="c" * 40)
        with (
            mock.patch.object(UPDATE, "_stored_pr", return_value=drifted),
            mock.patch.object(UPDATE, "_token_review_input") as token_manifest,
            mock.patch.object(UPDATE, "_run_mutation") as mutate,
        ):
            with self.assertRaisesRegex(UPDATE.PublicationError, "identity"):
                UPDATE.mark_ready(
                    expected=self.expected,
                    expected_title_sha256=self.digest(self.title),
                    expected_body_sha256=self.digest(self.body),
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )
        token_manifest.assert_not_called()
        mutate.assert_not_called()

    def test_repeating_ready_rebind_is_receipt_backed_noop(self) -> None:
        ready = self.stored(is_draft=False)
        token_manifest = SimpleNamespace(
            raw={
                "pr_number": CREATE.PR_NUMBER_TOKEN,
                "candidate": {"body_sha256": UPDATE._digest(self.template)},
            }
        )
        candidate = UPDATE._build_ready_candidate(
            expected=self.expected,
            title=self.title,
            body=self.body,
            review_input_path=self.template_path,
            review_mode="not-required",
            selected_specialists=[],
        )
        receipt = SimpleNamespace(
            operation="mark-ready",
            schema_version=4,
            expected=self.expected,
            provenance="canonical",
            review=SimpleNamespace(
                mode="not-required",
                publication_candidate_sha256=candidate.content_sha256,
            ),
            review_input_schema_version=self.review_input_schema_version,
            review_input_sha256=self.review_input_sha256,
            final_state=RECEIPTS.StateSnapshot(
                title_sha256=self.digest(self.title),
                body_sha256=self.digest(self.body),
                is_draft=False,
                state="OPEN",
            ),
        )
        with (
            mock.patch.object(UPDATE, "_token_review_input", return_value=token_manifest),
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(UPDATE, "_require_creation_receipt"),
            mock.patch.object(UPDATE, "_stored_pr", return_value=ready),
            mock.patch.object(UPDATE, "load_receipts", return_value=[receipt]),
            mock.patch.object(UPDATE, "_run_mutation") as mutate,
        ):
            result = UPDATE.mark_ready(
                expected=self.expected,
                expected_title_sha256=self.digest(self.title),
                expected_body_sha256=self.digest(self.body),
                review_input_path=self.template_path,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                body_template_path=self.template_path,
                receipt_directory=self.receipt_directory,
            )

        self.assertEqual(result, ready)
        mutate.assert_not_called()

    def test_token_rebind_requires_matching_creation_receipt(self) -> None:
        before = self.stored()
        creation_candidate = UPDATE._build_candidate(
            operation="create",
            repository=self.repository,
            pr_number=CREATE.PR_NUMBER_TOKEN,
            base=self.base,
            base_oid=self.base_oid,
            head=self.head,
            head_oid=self.head_oid,
            head_owner=self.head_owner,
            head_repository=self.head_repository,
            title=self.title,
            body_source_kind="template",
            body_source_raw=self.template.encode("utf-8"),
            published_body=self.template,
            review_input_path=self.template_path,
            review_mode="not-required",
            selected_specialists=[],
        )
        creation_receipt = SimpleNamespace(
            operation="create",
            schema_version=4,
            provenance="canonical",
            expected=self.expected,
            review=SimpleNamespace(
                mode="not-required",
                publication_candidate_sha256=creation_candidate.content_sha256,
            ),
            review_input_schema_version=self.review_input_schema_version,
            review_input_sha256=self.review_input_sha256,
            final_state=SimpleNamespace(
                title_sha256=self.digest(self.title),
                body_sha256=self.digest(self.body),
                is_draft=True,
            ),
        )
        with mock.patch.object(UPDATE, "load_receipts", return_value=[creation_receipt]):
            UPDATE._require_creation_receipt(
                expected=self.expected,
                before=before,
                template=self.template,
                review_input_path=self.template_path,
                review_input_schema_version=self.review_input_schema_version,
                review_input_sha256=self.review_input_sha256,
                review_mode="not-required",
                selected_specialists=[],
                receipt_root=self.receipt_directory,
            )

    def test_token_rebind_rejects_creation_receipt_identity_drift(self) -> None:
        before = self.stored()
        creation_candidate = UPDATE._build_candidate(
            operation="create",
            repository=self.repository,
            pr_number=CREATE.PR_NUMBER_TOKEN,
            base=self.base,
            base_oid=self.base_oid,
            head=self.head,
            head_oid=self.head_oid,
            head_owner=self.head_owner,
            head_repository=self.head_repository,
            title=self.title,
            body_source_kind="template",
            body_source_raw=self.template.encode("utf-8"),
            published_body=self.template,
            review_input_path=self.template_path,
            review_mode="not-required",
            selected_specialists=[],
        )
        drifted = SimpleNamespace(
            operation="create",
            schema_version=4,
            provenance="canonical",
            expected=self.expected.__class__(
                repository=self.repository,
                pr_number=self.pr_number,
                base=self.base,
                base_oid=self.base_oid,
                head=self.head,
                head_oid="c" * 40,
                head_owner=self.head_owner,
                head_repository=self.head_repository,
            ),
            review=SimpleNamespace(
                mode="not-required",
                publication_candidate_sha256=creation_candidate.content_sha256,
            ),
            review_input_schema_version=self.review_input_schema_version,
            review_input_sha256=self.review_input_sha256,
            final_state=SimpleNamespace(
                title_sha256=self.digest(self.title),
                body_sha256=self.digest(self.body),
                is_draft=True,
            ),
        )
        with mock.patch.object(UPDATE, "load_receipts", return_value=[drifted]):
            with self.assertRaisesRegex(UPDATE.PublicationError, "does not match"):
                UPDATE._require_creation_receipt(
                    expected=self.expected,
                    before=before,
                    template=self.template,
                    review_input_path=self.template_path,
                    review_input_schema_version=self.review_input_schema_version,
                    review_input_sha256=self.review_input_sha256,
                    review_mode="not-required",
                    selected_specialists=[],
                    receipt_root=self.receipt_directory,
                )


class TokenReadinessBotTailIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        fixtures = importlib.import_module("tests.test_mergecraft_control_plane")
        self.fixture = fixtures.MergecraftControlPlaneTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.fixture.state()
        created, _, self.manifest, self.template, validator = (
            self.fixture.create_command(title="feat: widget")
        )
        self.assertEqual(validator.returncode, 0, validator.stderr)
        self.assertEqual(created.returncode, 0, created.stderr)
        self.authored_body = fixtures.BODY

    def replace_live_body(self, body: str) -> None:
        state = json.loads(self.fixture.github.read_text())
        state["prs"][0]["body"] = body
        self.fixture.github.write_text(json.dumps(state), encoding="utf-8")

    @staticmethod
    def bot_tail(notes: str) -> str:
        return (
            "\n\n<!-- This is an auto-generated comment: release notes by coderabbit.ai -->\n"
            f"{notes}\n"
            "<!-- end of auto-generated comment: release notes by coderabbit.ai -->"
        )

    def test_creation_manifest_ready_and_retry_preserve_bot_tail(self) -> None:
        manifest_bytes = self.manifest.read_bytes()
        creation_receipts = self.fixture.publication_receipt_bytes()
        self.replace_live_body(self.authored_body + self.bot_tail("Initial notes"))
        before_ready_body = self.authored_body + self.bot_tail("Latest draft notes")
        self.fixture.change_pr_after_next_read({"body": before_ready_body})

        ready = self.fixture.ready_created_pr(self.manifest, self.template)

        self.assertEqual(ready.returncode, 0, ready.stderr)
        receipts = self.fixture.publication_receipt_bytes()
        self.assertEqual(len(receipts), 2)
        for path, raw in creation_receipts.items():
            self.assertEqual(receipts[path], raw)
        state = json.loads(self.fixture.github.read_text())
        self.assertEqual(state["prs"][0]["body"], before_ready_body)
        latest_body = self.authored_body + self.bot_tail("Ready review notes")
        self.replace_live_body(latest_body)

        retried = self.fixture.ready_created_pr(self.manifest, self.template)

        self.assertEqual(retried.returncode, 0, retried.stderr)
        self.assertEqual(self.fixture.publication_receipt_bytes(), receipts)
        self.assertEqual(self.manifest.read_bytes(), manifest_bytes)
        state = json.loads(self.fixture.github.read_text())
        self.assertEqual(sum("ready" in call for call in state["calls"]), 1)
        self.assertFalse(state["prs"][0]["isDraft"])
        self.assertEqual(state["prs"][0]["body"], latest_body)

    def test_creation_manifest_blocks_authored_drift_before_ready_and_retry(
        self,
    ) -> None:
        creation_receipts = self.fixture.publication_receipt_bytes()
        self.replace_live_body(
            self.authored_body + "Authored change" + self.bot_tail("Bot notes")
        )

        ready = self.fixture.ready_created_pr(self.manifest, self.template)

        self.assertNotEqual(ready.returncode, 0)
        self.assertIn("preimage changed", ready.stderr)
        self.assertEqual(self.fixture.publication_receipt_bytes(), creation_receipts)
        state = json.loads(self.fixture.github.read_text())
        self.assertEqual(sum("ready" in call for call in state["calls"]), 0)
        self.replace_live_body(self.authored_body + self.bot_tail("Bot notes"))
        ready = self.fixture.ready_created_pr(self.manifest, self.template)
        self.assertEqual(ready.returncode, 0, ready.stderr)
        receipts = self.fixture.publication_receipt_bytes()
        self.replace_live_body(
            self.authored_body + "Later authored change" + self.bot_tail("New notes")
        )

        retry = self.fixture.ready_created_pr(self.manifest, self.template)

        self.assertNotEqual(retry.returncode, 0)
        self.assertIn("preimage changed", retry.stderr)
        self.assertEqual(self.fixture.publication_receipt_bytes(), receipts)
        state = json.loads(self.fixture.github.read_text())
        self.assertEqual(sum("ready" in call for call in state["calls"]), 1)

    def test_legacy_creation_receipt_keeps_complete_body_semantics(self) -> None:
        receipt_root = (
            self.fixture.home / ".local/state/mergecraft/pr-publication-receipts"
        )
        path = next(receipt_root.rglob("*.json"))
        payload = json.loads(path.read_bytes())
        payload["schema_version"] = 3
        PublicationReceiptTests.rewrite_receipt(self, path, payload)
        receipts = self.fixture.publication_receipt_bytes()
        self.replace_live_body(self.authored_body + self.bot_tail("New notes"))

        ready = self.fixture.ready_created_pr(self.manifest, self.template)

        self.assertNotEqual(ready.returncode, 0)
        self.assertIn("creation receipt does not match", ready.stderr)
        self.assertEqual(self.fixture.publication_receipt_bytes(), receipts)
        state = json.loads(self.fixture.github.read_text())
        self.assertEqual(sum("ready" in call for call in state["calls"]), 0)

        self.replace_live_body(self.authored_body)
        ready = self.fixture.ready_created_pr(self.manifest, self.template)
        self.assertEqual(ready.returncode, 0, ready.stderr)

        ready_receipts = self.fixture.publication_receipt_bytes()
        for notes in ("First ready notes", "Refreshed ready notes"):
            with self.subTest(notes=notes):
                latest_body = self.authored_body + self.bot_tail(notes)
                self.replace_live_body(latest_body)
                retry = self.fixture.ready_created_pr(self.manifest, self.template)
                self.assertEqual(retry.returncode, 0, retry.stderr)
                self.assertEqual(
                    self.fixture.publication_receipt_bytes(), ready_receipts
                )
                state = json.loads(self.fixture.github.read_text())
                self.assertEqual(sum("ready" in call for call in state["calls"]), 1)
                self.assertEqual(state["prs"][0]["body"], latest_body)
        self.replace_live_body(
            self.authored_body + "Authored drift" + self.bot_tail("Later notes")
        )
        retry = self.fixture.ready_created_pr(self.manifest, self.template)
        self.assertNotEqual(retry.returncode, 0)
        self.assertIn("preimage changed", retry.stderr)
        self.assertEqual(self.fixture.publication_receipt_bytes(), ready_receipts)

    def test_legacy_ready_retry_still_requires_unchanged_complete_body(self) -> None:
        receipt_root = (
            self.fixture.home / ".local/state/mergecraft/pr-publication-receipts"
        )
        creation_path = next(receipt_root.rglob("*.json"))
        creation = json.loads(creation_path.read_bytes())
        creation["schema_version"] = 3
        PublicationReceiptTests.rewrite_receipt(self, creation_path, creation)
        ready = self.fixture.ready_created_pr(self.manifest, self.template)
        self.assertEqual(ready.returncode, 0, ready.stderr)
        ready_path = sorted(receipt_root.rglob("*.json"))[-1]
        ready_receipt = json.loads(ready_path.read_bytes())
        ready_receipt["schema_version"] = 3
        PublicationReceiptTests.rewrite_receipt(self, ready_path, ready_receipt)
        receipts = self.fixture.publication_receipt_bytes()

        unchanged = self.fixture.ready_created_pr(self.manifest, self.template)
        self.assertEqual(unchanged.returncode, 0, unchanged.stderr)
        self.replace_live_body(self.authored_body + self.bot_tail("New notes"))
        changed = self.fixture.ready_created_pr(self.manifest, self.template)

        self.assertNotEqual(changed.returncode, 0)
        self.assertIn("readiness receipt does not match", changed.stderr)
        self.assertEqual(self.fixture.publication_receipt_bytes(), receipts)
        state = json.loads(self.fixture.github.read_text())
        self.assertEqual(sum("ready" in call for call in state["calls"]), 1)


class PublicationReconciliationIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lifecycle = importlib.import_module("tests.test_mergecraft_control_plane")
        self.fixture = self.lifecycle.MergecraftControlPlaneTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.fixture.state()
        created, _, _, _, validator = self.fixture.create_command(title="feat: widget")
        self.assertEqual(validator.returncode, 0, validator.stderr)
        self.assertEqual(created.returncode, 0, created.stderr)
        self.manifest = self.fixture.root / "reconciliation-input.json"
        self.manifest.write_text(
            json.dumps(self.lifecycle.review_input(
                "feat: widget", self.lifecycle.BODY,
                baseline_body=self.lifecycle.BODY,
            )),
            encoding="utf-8",
        )

    def audit_command(self, operation: str):
        auditor = SCRIPTS / "audit_reviewable_pr.py"
        arguments = [
            sys.executable, str(auditor), operation,
            "--repository", "acme/app", "--pr", "2",
            "--base", "main", "--base-oid", self.lifecycle.BASE_OID,
            "--head", "acme:widget", "--head-oid", self.lifecycle.HEAD_OID,
            "--head-owner", "acme", "--head-repository", "acme/app-fork",
        ]
        if operation == "reconcile":
            arguments.extend(["--review-input", str(self.manifest)])
        return self.lifecycle.CONTROL.run_command(
            arguments,
            home=self.fixture.home,
            environment={"MERGECRAFT_GITHUB_STATE": str(self.fixture.github)},
            allowed_scripts=(auditor,),
            cwd=self.fixture.git_repository,
        )

    def legacy_creation_receipt(self, version: int) -> None:
        root = self.fixture.home / ".local/state/mergecraft/pr-publication-receipts"
        path = next(root.rglob("*.json"))
        payload = json.loads(path.read_bytes())
        payload["schema_version"] = version
        if version == 2:
            del payload["review"]
        PublicationReceiptTests.rewrite_receipt(self, path, payload)

    def append_bot_tail(self, notes: str) -> None:
        state = json.loads(self.fixture.github.read_text())
        state["prs"][0]["body"] = (
            self.lifecycle.BODY + TokenReadinessBotTailIntegrationTests.bot_tail(notes)
        )
        self.fixture.github.write_text(json.dumps(state), encoding="utf-8")

    def assert_legacy_bot_tail_migrates(self, version: int) -> None:
        self.legacy_creation_receipt(version)
        historical_receipts = self.fixture.publication_receipt_bytes()
        self.append_bot_tail("Appended review notes")
        drifted = self.audit_command("audit")
        self.assertEqual(json.loads(drifted.stdout)["status"], "drift")

        reconciled = self.audit_command("reconcile")

        self.assertEqual(reconciled.returncode, 0, reconciled.stderr)
        result = json.loads(reconciled.stdout)
        self.assertEqual(result["provenance"], "reconciled-unreceipted")
        self.assertEqual(result["review"], {"state": "unwitnessed-reconciliation"})
        receipts = self.fixture.publication_receipt_bytes()
        self.assertEqual(len(receipts), 2)
        for path, raw in historical_receipts.items():
            self.assertEqual(receipts[path], raw)
        self.append_bot_tail("Refreshed review notes")
        audited = self.audit_command("audit")
        self.assertEqual(audited.returncode, 0, audited.stderr)
        self.assertEqual(json.loads(audited.stdout)["status"], "verified")
        self.assertEqual(
            json.loads(audited.stdout)["review"],
            {"state": "unwitnessed-reconciliation"},
        )
        repeated = self.audit_command("reconcile")
        self.assertNotEqual(repeated.returncode, 0)
        self.assertIn("already matches", repeated.stderr)
        self.assertEqual(self.fixture.publication_receipt_bytes(), receipts)

    def test_reconciliation_migrates_v2_bot_tail_drift(self) -> None:
        self.assert_legacy_bot_tail_migrates(2)

    def test_reconciliation_migrates_v3_bot_tail_drift(self) -> None:
        self.assert_legacy_bot_tail_migrates(3)

    def assert_matching_legacy_receipt_rejects_reconciliation(self, version: int) -> None:
        self.legacy_creation_receipt(version)
        receipts = self.fixture.publication_receipt_bytes()
        audited = self.audit_command("audit")
        self.assertEqual(audited.returncode, 0, audited.stderr)
        self.assertEqual(json.loads(audited.stdout)["status"], "verified")
        if version == 2:
            self.assertEqual(
                json.loads(audited.stdout)["review"], {"state": "legacy-unrecorded"}
            )

        reconciled = self.audit_command("reconcile")

        self.assertNotEqual(reconciled.returncode, 0)
        self.assertIn("already matches", reconciled.stderr)
        self.assertEqual(self.fixture.publication_receipt_bytes(), receipts)

    def test_reconciliation_preserves_matching_v2_receipt(self) -> None:
        self.assert_matching_legacy_receipt_rejects_reconciliation(2)

    def test_reconciliation_preserves_matching_v3_receipt(self) -> None:
        self.assert_matching_legacy_receipt_rejects_reconciliation(3)

    def test_reconciliation_rejects_v4_duplicate_after_bot_refresh(self) -> None:
        receipts = self.fixture.publication_receipt_bytes()
        self.append_bot_tail("Fresh review notes")
        audited = self.audit_command("audit")
        self.assertEqual(audited.returncode, 0, audited.stderr)
        self.assertEqual(json.loads(audited.stdout)["status"], "verified")

        reconciled = self.audit_command("reconcile")

        self.assertNotEqual(reconciled.returncode, 0)
        self.assertIn("already matches", reconciled.stderr)
        self.assertEqual(self.fixture.publication_receipt_bytes(), receipts)


class PublicationReceiptTests(ReviewablePrFixture):
    def test_audit_post_start_read_io_failure_is_value_free_and_read_only(
        self,
    ) -> None:
        self.canonical_receipt()
        receipts_before = {
            path: path.read_bytes() for path in self.receipt_directory.rglob("*.json")
        }
        events: list[str] = []
        io_error = OSError("Authorization: arbitrary-secret-value")
        with mock.patch.object(
            STATE.subprocess,
            "Popen",
            post_start_io_failure_popen(events, io_error),
        ):
            result = AUDIT.audit(
                expected=self.expected,
                receipt_directory=self.receipt_directory,
            )

        self.assertEqual(result.status, "unavailable")
        self.assertIsNotNone(result.reason)
        self.assertIn("read process started is unknown", result.reason)
        self.assertNotIn("Authorization", result.reason)
        self.assertNotIn("could not start", result.reason)
        self.assertEqual(
            events,
            [
                "process-created",
                "communicate-entered",
                "process-killed",
                "process-waited",
            ],
        )
        self.assertEqual(
            {
                path: path.read_bytes()
                for path in self.receipt_directory.rglob("*.json")
            },
            receipts_before,
        )

    def setUp(self) -> None:
        super().setUp()
        self.receipt_directory = Path(self.temporary_directory.name) / "receipts"
        RECEIPTS.prepare_receipt_store(self.receipt_directory)

    def test_receipt_json_parser_bounds_numbers_and_nesting(self) -> None:
        secret = "Authorization: synthetic-secret"
        cases = (
            ("non-finite-exponent", b'{"value":1e9999}', "non-finite"),
            (
                "oversized-integer",
                ('{"value":' + "9" * 5_000 + "}").encode(),
                "invalid JSON",
            ),
            (
                "excessive-nesting",
                ("[" * 2_000 + json.dumps(secret) + "]" * 2_000).encode(),
                "invalid JSON",
            ),
        )
        for name, raw, classification in cases:
            with self.subTest(name=name):
                with self.assertRaisesRegex(
                    RECEIPTS.ReceiptError, classification
                ) as caught:
                    RECEIPTS._strict_json(raw)
                self.assertNotIn(secret, str(caught.exception))
                self.assertIsNotNone(caught.exception.__cause__)

    def test_receipt_parser_rejects_lone_surrogate_values_and_keys(self) -> None:
        for name, mutate in (
            (
                "value",
                lambda payload: payload["identity"].__setitem__(
                    "base", "Authorization: arbitrary-secret-value\ud800"
                ),
            ),
            (
                "key",
                lambda payload: payload["identity"].__setitem__(
                    "Authorization: arbitrary-secret-value\ud800", "ignored"
                ),
            ),
        ):
            root = Path(self.temporary_directory.name) / f"malformed-{name}"
            RECEIPTS.prepare_receipt_store(root)
            self.canonical_receipt(root=root)
            path = next(root.rglob("*.json"))
            payload = json.loads(path.read_bytes())
            mutate(payload)
            path.write_bytes(
                json.dumps(
                    payload,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                ).encode("utf-8")
                + b"\n"
            )
            ledger_before = {
                item: item.read_bytes() for item in root.rglob("*.json")
            }

            with self.subTest(location=name):
                with self.assertRaisesRegex(
                    RECEIPTS.ReceiptError, "malformed UTF-8 scalar text"
                ) as caught:
                    RECEIPTS.load_receipts(root, self.expected)

                self.assertIsInstance(caught.exception.__cause__, UnicodeEncodeError)
                diagnostic = str(caught.exception)
                self.assertNotIn("arbitrary-secret-value", diagnostic)
                self.assertNotIn("Authorization", diagnostic)
                read_live = mock.Mock(return_value=self.stored())
                audited = RECEIPTS.audit_publication(
                    root=root,
                    expected=self.expected,
                    read_live=read_live,
                )
                self.assertEqual(audited.status, "unavailable")
                self.assertIsNone(audited.receipt)
                self.assertEqual(
                    audited.reason, "receipt ledger is unavailable or invalid"
                )
                read_live.assert_not_called()
                self.assertEqual(
                    {item: item.read_bytes() for item in root.rglob("*.json")},
                    ledger_before,
                )

    def test_canonical_receipt_encoding_failure_is_value_free_and_chained(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            RECEIPTS.ReceiptError, "canonical receipt encoding failed"
        ) as caught:
            RECEIPTS._canonical(
                {"field": "Authorization: arbitrary-secret-value\ud800"}
            )

        self.assertIsInstance(caught.exception.__cause__, UnicodeEncodeError)
        diagnostic = str(caught.exception)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("Authorization", diagnostic)

    def test_receipt_parser_and_audit_preserve_valid_unicode_across_v2_v3_v4(
        self,
    ) -> None:
        self.base = "maïn-雪"
        admitted = RECEIPTS._strict_json(
            '{"clé-雪":"café-🙂"}'.encode("utf-8")
        )
        self.assertEqual(admitted, {"clé-雪": "café-🙂"})

        for schema_version in (2, 3, 4):
            root = Path(self.temporary_directory.name) / f"unicode-v{schema_version}"
            RECEIPTS.prepare_receipt_store(root)
            self.canonical_receipt(root=root)
            path = next(root.rglob("*.json"))
            payload = json.loads(path.read_bytes())
            payload["schema_version"] = schema_version
            if schema_version == 2:
                del payload["review"]
            rewritten = self.rewrite_receipt(path, payload)
            raw = rewritten.read_bytes()
            self.assertIn("maïn-雪".encode("utf-8"), raw)

            with self.subTest(schema_version=schema_version):
                loaded = RECEIPTS.load_receipts(root, self.expected)
                self.assertEqual(len(loaded), 1)
                self.assertEqual(loaded[0].schema_version, schema_version)
                self.assertEqual(loaded[0].expected.base, "maïn-雪")
                ledger_before = {
                    item: item.read_bytes() for item in root.rglob("*.json")
                }
                read_live = mock.Mock(return_value=self.stored())
                audited = RECEIPTS.audit_publication(
                    root=root,
                    expected=self.expected,
                    read_live=read_live,
                )
                self.assertEqual(audited.status, "verified")
                self.assertEqual(audited.receipt, loaded[0])
                read_live.assert_called_once_with()
                self.assertEqual(
                    {item: item.read_bytes() for item in root.rglob("*.json")},
                    ledger_before,
                )

    def test_audit_malformed_successful_read_is_unavailable(self) -> None:
        RECEIPTS.prepare_receipt_ledger(self.receipt_directory, self.expected)
        completed = subprocess.CompletedProcess(
            [], 0, b"\xffarbitrary-secret-value", b"\xfeAuthorization"
        )
        with mock.patch.object(STATE.subprocess, "run", return_value=completed):
            result = AUDIT.audit(
                expected=self.expected,
                receipt_directory=self.receipt_directory,
            )

        self.assertEqual(result.status, "unavailable")
        self.assertIn("live PR state read returned malformed successful output", result.reason)
        self.assertIn("strict UTF-8 was required", result.reason)
        rendered = json.dumps(result.as_json(), sort_keys=True)
        self.assertNotIn("arbitrary-secret-value", rendered)
        self.assertNotIn("Authorization", rendered)
        self.assertNotIn("UnicodeDecodeError", rendered)
        self.assertNotIn("codec", rendered)

    def test_audit_direct_reader_admits_live_state_before_comparison(self) -> None:
        receipt = self.canonical_receipt()
        receipts_before = {
            path: path.read_bytes() for path in self.receipt_directory.rglob("*.json")
        }

        for name, observation, reason in (
            (
                "incomplete",
                {"number": self.pr_number},
                "live PR state read returned an incomplete response",
            ),
            (
                "wrong-type",
                self.stored(body=["Authorization: arbitrary-secret-value"]),
                "live PR state read returned a malformed response",
            ),
            (
                "lone-surrogate",
                self.stored(title="Authorization: arbitrary-secret-value\ud800"),
                "live PR state read returned a malformed response",
            ),
        ):
            with self.subTest(name=name):
                result = RECEIPTS.audit_publication(
                    root=self.receipt_directory,
                    expected=self.expected,
                    read_live=lambda observation=observation: observation,
                )
                self.assertEqual(result.status, "unavailable")
                self.assertEqual(result.reason, reason)
                rendered = json.dumps(result.as_json(), sort_keys=True)
                self.assertNotIn("arbitrary-secret-value", rendered)
                self.assertNotIn("Authorization", rendered)
                self.assertNotIn("Traceback", rendered)

        for name, observation in (
            ("text", self.stored(title="changed")),
            ("identity", self.stored(headRefOid="c" * 40)),
            ("state", self.stored(state="CLOSED")),
        ):
            with self.subTest(name=name):
                result = RECEIPTS.audit_publication(
                    root=self.receipt_directory,
                    expected=self.expected,
                    read_live=lambda observation=observation: observation,
                )
                self.assertEqual(result.status, "drift")

        matched = RECEIPTS.audit_publication(
            root=self.receipt_directory,
            expected=self.expected,
            read_live=lambda: self.stored(providerExtension={"ignored": True}),
        )
        self.assertEqual(matched.status, "verified")
        self.assertEqual(matched.receipt, receipt)
        self.assertEqual(
            {
                path: path.read_bytes()
                for path in self.receipt_directory.rglob("*.json")
            },
            receipts_before,
        )

        unicode_match = RECEIPTS.audit_publication(
            root=self.receipt_directory,
            expected=self.expected,
            read_live=lambda: self.stored(title="feat: café 😀", body="λ 🚀"),
        )
        self.assertEqual(unicode_match.status, "drift")
        self.assertEqual(
            {
                path: path.read_bytes()
                for path in self.receipt_directory.rglob("*.json")
            },
            receipts_before,
        )

    def test_audit_cli_preserves_safe_read_failure_classifications(self) -> None:
        self.canonical_receipt()
        original_audit = AUDIT.audit
        receipts_before = {
            path: path.read_bytes() for path in self.receipt_directory.rglob("*.json")
        }

        def local_audit(*, expected: STATE.ExpectedIdentity):
            return original_audit(
                expected=expected,
                receipt_directory=self.receipt_directory,
            )

        arguments = [
            str(AUDIT.__file__),
            "audit",
            "--repository",
            self.repository,
            "--pr",
            str(self.pr_number),
            "--base",
            self.base,
            "--base-oid",
            self.base_oid,
            "--head",
            self.head,
            "--head-oid",
            self.head_oid,
            "--head-owner",
            self.head_owner,
            "--head-repository",
            self.head_repository,
        ]
        wrongly_typed = self.stored()
        wrongly_typed["body"] = ["Authorization: Bearer arbitrary-secret-value"]
        cases = (
            (
                "broad-os-failure",
                OSError("/synthetic/arbitrary-secret-value/gh: Authorization\x1b[31m"),
                "live PR state read failed during process launch or communication; "
                "whether the read process started is unknown",
            ),
            (
                "timeout",
                subprocess.TimeoutExpired(
                    "/synthetic/arbitrary-secret-value/gh",
                    STATE.READ_TIMEOUT_SECONDS,
                    output=b"Authorization",
                ),
                f"live PR state read timed out after {STATE.READ_TIMEOUT_SECONDS} seconds",
            ),
            (
                "return-code",
                subprocess.CompletedProcess(
                    [], 55, b"arbitrary-secret-value", b"Authorization"
                ),
                "live PR state read was rejected (return code 55)",
            ),
            (
                "malformed-output",
                subprocess.CompletedProcess(
                    [], 0, b"\xffarbitrary-secret-value", b"\xfeAuthorization"
                ),
                "live PR state read returned malformed successful output; strict "
                "UTF-8 was required",
            ),
            (
                "invalid-json",
                subprocess.CompletedProcess(
                    [],
                    0,
                    b'{"number": 42, "body": "Authorization: arbitrary-secret-value"',
                    b"X-Api-Key: arbitrary-secret-value",
                ),
                "live PR state read returned invalid JSON",
            ),
            (
                "duplicate-json-key",
                subprocess.CompletedProcess(
                    [],
                    0,
                    (
                        b'{"number": 42, "number": 43, '
                        b'"Authorization": "arbitrary-secret-value"}'
                    ),
                    b"X-Api-Key: arbitrary-secret-value",
                ),
                "live PR state read returned JSON with duplicate object keys",
            ),
            (
                "non-finite-json",
                subprocess.CompletedProcess(
                    [],
                    0,
                    b'{"number": 42, "Authorization": NaN}',
                    b"X-Api-Key: arbitrary-secret-value",
                ),
                "live PR state read returned JSON with a non-finite value",
            ),
            (
                "incomplete-response",
                subprocess.CompletedProcess(
                    [],
                    0,
                    b'{"number": 42, "Authorization": "arbitrary-secret-value"}',
                    b"X-Api-Key: arbitrary-secret-value",
                ),
                "live PR state read returned an incomplete response",
            ),
            (
                "malformed-response",
                subprocess.CompletedProcess(
                    [],
                    0,
                    json.dumps(wrongly_typed).encode("utf-8"),
                    b"X-Api-Key: arbitrary-secret-value",
                ),
                "live PR state read returned a malformed response",
            ),
        )
        for name, subprocess_result, classification in cases:
            with self.subTest(name=name):
                stdout = io.StringIO()
                stderr = io.StringIO()
                run_kwargs = (
                    {"side_effect": subprocess_result}
                    if isinstance(subprocess_result, BaseException)
                    else {"return_value": subprocess_result}
                )
                with (
                    mock.patch.object(AUDIT, "audit", side_effect=local_audit),
                    mock.patch.object(STATE.subprocess, "run", **run_kwargs),
                    mock.patch.object(sys, "argv", arguments),
                    mock.patch.object(sys, "stdout", stdout),
                    mock.patch.object(sys, "stderr", stderr),
                ):
                    status = AUDIT.main()

                diagnostic = stdout.getvalue() + stderr.getvalue()
                self.assertEqual(status, 1)
                self.assertEqual(json.loads(stdout.getvalue())["status"], "unavailable")
                self.assertIn(classification, diagnostic)
                self.assertNotIn("post-mutation", diagnostic)
                self.assertNotIn("arbitrary-secret-value", diagnostic)
                self.assertNotIn("Authorization", diagnostic)
                self.assertNotIn("OSError", diagnostic)
                self.assertNotIn("TimeoutExpired", diagnostic)
                self.assertEqual(
                    {
                        path: path.read_bytes()
                        for path in self.receipt_directory.rglob("*.json")
                    },
                    receipts_before,
                )
                self.assertNotIn("Traceback", diagnostic)
                self.assertNotIn("\x1b", diagnostic)

        for expected_status, expected_exit, observation in (
            ("verified", 0, self.stored(providerExtension={"ignored": True})),
            ("drift", 1, self.stored(title="changed")),
            ("drift", 1, self.stored(state="MERGED")),
        ):
            with self.subTest(
                expected_status=expected_status, state=observation["state"]
            ):
                stdout = io.StringIO()
                stderr = io.StringIO()
                completed = subprocess.CompletedProcess(
                    [], 0, json.dumps(observation).encode("utf-8"), b""
                )
                with (
                    mock.patch.object(AUDIT, "audit", side_effect=local_audit),
                    mock.patch.object(
                        STATE.subprocess, "run", return_value=completed
                    ) as read,
                    mock.patch.object(sys, "argv", arguments),
                    mock.patch.object(sys, "stdout", stdout),
                    mock.patch.object(sys, "stderr", stderr),
                ):
                    status = AUDIT.main()

                self.assertEqual(status, expected_exit)
                self.assertEqual(
                    json.loads(stdout.getvalue())["status"], expected_status
                )
                self.assertEqual(stderr.getvalue(), "")
                self.assertEqual(read.call_count, 1)
                self.assertIn("view", read.call_args.args[0])
                self.assertEqual(
                    {
                        path: path.read_bytes()
                        for path in self.receipt_directory.rglob("*.json")
                    },
                    receipts_before,
                )

    def test_audit_cli_process_admits_observations_without_writing_receipts(
        self,
    ) -> None:
        root = Path(self.temporary_directory.name)
        state_home = root / "state"
        receipt_root = state_home / "mergecraft/pr-publication-receipts"
        RECEIPTS.prepare_receipt_store(receipt_root)
        self.canonical_receipt(root=receipt_root)
        receipts_before = {
            path.relative_to(receipt_root): path.read_bytes()
            for path in receipt_root.rglob("*")
            if path.is_file()
        }

        provider_output = root / "provider-output"
        executable_directory = root / "bin"
        executable_directory.mkdir()
        fake_gh = executable_directory / "gh"
        fake_gh.write_text(
            f"#!{sys.executable}\n"
            "import sys\n"
            "from pathlib import Path\n"
            f"sys.stdout.buffer.write(Path({str(provider_output)!r}).read_bytes())\n",
            encoding="utf-8",
        )
        fake_gh.chmod(0o700)
        arguments = [
            sys.executable,
            str(AUDIT.__file__),
            "audit",
            "--repository",
            self.repository,
            "--pr",
            str(self.pr_number),
            "--base",
            self.base,
            "--base-oid",
            self.base_oid,
            "--head",
            self.head,
            "--head-oid",
            self.head_oid,
            "--head-owner",
            self.head_owner,
            "--head-repository",
            self.head_repository,
        ]
        environment = {
            "HOME": str(root / "home"),
            "XDG_STATE_HOME": str(state_home),
            "PATH": str(executable_directory),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        }
        malformed = self.stored()
        malformed["isDraft"] = "Authorization: arbitrary-secret-value"
        cases = (
            (
                "invalid-json",
                b'{"Authorization": "arbitrary-secret-value"',
                "unavailable",
                "live PR state read returned invalid JSON",
            ),
            (
                "oversized-json-integer",
                (
                    b'{"number": '
                    + b"9" * 5_000
                    + b', "Authorization": "arbitrary-secret-value"}'
                ),
                "unavailable",
                "live PR state read returned invalid JSON",
            ),
            (
                "incomplete",
                b'{"number": 42, "Authorization": "arbitrary-secret-value"}',
                "unavailable",
                "live PR state read returned an incomplete response",
            ),
            (
                "wrong-type",
                json.dumps(malformed).encode("utf-8"),
                "unavailable",
                "live PR state read returned a malformed response",
            ),
            (
                "lone-surrogate",
                json.dumps(
                    self.stored(body="Authorization: arbitrary-secret-value\udc00")
                ).encode("utf-8"),
                "unavailable",
                "live PR state read returned a malformed response",
            ),
            (
                "oversized-url-identifier",
                json.dumps(
                    self.stored(
                        url=f"https://github.com/acme/app/pull/{'9' * 5_000}",
                        providerExtension="Authorization: arbitrary-secret-value",
                    )
                ).encode("utf-8"),
                "unavailable",
                "live PR state read returned a malformed response",
            ),
            (
                "valid-drift",
                json.dumps(self.stored(title="changed")).encode("utf-8"),
                "drift",
                "live PR state does not match the authoritative latest receipt",
            ),
            (
                "validated-match",
                json.dumps(self.stored(providerExtension={"ignored": True})).encode(
                    "utf-8"
                ),
                "verified",
                None,
            ),
        )
        for name, output, expected_status, expected_reason in cases:
            with self.subTest(name=name):
                provider_output.write_bytes(output)
                result = subprocess.run(
                    arguments,
                    capture_output=True,
                    text=True,
                    check=False,
                    cwd=root,
                    env=environment,
                )

                rendered = result.stdout + result.stderr
                payload = json.loads(result.stdout)
                self.assertEqual(
                    result.returncode, 0 if expected_status == "verified" else 1
                )
                self.assertEqual(payload["status"], expected_status)
                if expected_reason is not None:
                    self.assertEqual(payload["reason"], expected_reason)
                self.assertNotIn("arbitrary-secret-value", rendered)
                self.assertNotIn("Authorization", rendered)
                self.assertNotIn("Traceback", rendered)
                self.assertEqual(
                    {
                        path.relative_to(receipt_root): path.read_bytes()
                        for path in receipt_root.rglob("*")
                        if path.is_file()
                    },
                    receipts_before,
                )

    def transition_candidate(
        self,
        *,
        operation: str,
        final_state: dict[str, object],
        mode: str,
        expected=None,
    ):
        expected = expected or self.expected
        if operation == "create":
            pr_number: int | str = CREATE.PR_NUMBER_TOKEN
            kind = "template"
            raw = self.template.encode("utf-8")
            published = self.template
        elif operation == "mark-ready":
            pr_number = expected.pr_number
            kind = "stored-body"
            published = str(final_state["body"])
            raw = published.encode("utf-8")
        else:
            pr_number = expected.pr_number
            kind = "body"
            published = str(final_state["body"])
            raw = published.encode("utf-8")
        value = {
            "schema_version": 1,
            "contract": "mergecraft-publication-candidate-v1",
            "operation": operation,
            "repository": expected.repository,
            "pr_number": pr_number,
            "base": {"ref": expected.base, "oid": expected.base_oid},
            "head": {
                "ref": expected.head,
                "oid": expected.head_oid,
                "owner": expected.head_owner,
                "repository": expected.head_repository,
            },
            "title": str(final_state["title"]),
            "body_source": REQUIRED_REVIEW.body_source_binding(
                kind=kind,
                raw=raw,
                published=published,
                render_contract=(
                    "mergecraft-pr-number-token-render-v1"
                    if kind == "template"
                    else "literal-utf8-v1"
                ),
            ),
            "review_input": {
                "schema_version": self.review_input_schema_version,
                "raw_sha256": "e" * 64,
                "content_sha256": self.review_input_sha256,
            },
            "publication_profile": {
                "contract": "mergecraft-publication-profile-v1",
                "review_mode": mode,
                "selected_specialists": [],
            },
        }
        digest = hashlib.sha256(RequiredReviewTests.canonical(value)).hexdigest()
        candidate = REQUIRED_REVIEW.PublicationCandidate(
            value=value,
            content_sha256=digest,
            candidate_identity={
                "kind": "mergecraft-publication-candidate-v1",
                "value": f"sha256:{digest}",
                "content_sha256": digest,
            },
            review_input_identity=REQUIRED_REVIEW._identity_for(
                "mergecraft-review-input-v1", value["review_input"]
            ),
            requirements_identity=REQUIRED_REVIEW._identity_for(
                "mergecraft-required-publication-review-profile-v2",
                REQUIRED_REVIEW._required_profile([]),
            ),
            body_source_raw=raw,
            published_body=published,
        )
        return candidate

    def canonical_receipt(
        self,
        *,
        operation: str = "create",
        before: dict[str, object] | None = None,
        after: dict[str, object] | None = None,
        root: Path | None = None,
        review=None,
    ):
        final_state = after or self.stored()
        if before is None and operation == "create":
            before = self.transport(title=final_state["title"])
        candidate = self.transition_candidate(
            operation=operation,
            final_state=final_state,
            mode=review.mode if review is not None else "not-required",
        )
        chosen_review = review or transition_review(
            "not-required", candidate.content_sha256, None
        )
        if review is not None:
            chosen_review = transition_review(
                review.mode, candidate.content_sha256, review.observation
            )
        transition = RECEIPTS.verified_transition(
            expected=self.expected,
            operation=operation,
            preimage=before or self.transport(),
            final_reread=final_state,
            review_input_schema_version=self.review_input_schema_version,
            review_input_sha256=self.review_input_sha256,
            review=chosen_review,
            candidate=candidate,
        )
        receipt_root = root or self.receipt_directory
        RECEIPTS.prepare_receipt_ledger(receipt_root, self.expected)
        with RECEIPTS.receipt_ledger_lock(receipt_root, self.expected) as lease:
            return RECEIPTS.record_verified_publication(
                root=receipt_root,
                transition=transition,
                lease=lease,
            )

    def reconciled_receipt(self, *, root: Path | None = None):
        stored = self.stored()
        transition = RECEIPTS.verified_transition(
            expected=self.expected,
            operation="reconcile",
            preimage=stored,
            final_reread=stored,
            review_input_schema_version=self.review_input_schema_version,
            review_input_sha256=self.review_input_sha256,
            review=None,
            candidate=None,
        )
        receipt_root = root or self.receipt_directory
        RECEIPTS.prepare_receipt_ledger(receipt_root, self.expected)
        with RECEIPTS.receipt_ledger_lock(receipt_root, self.expected) as lease:
            return RECEIPTS.record_reconciliation(
                root=receipt_root,
                transition=transition,
                lease=lease,
            )

    def rewrite_receipt(self, path: Path, payload: dict[str, object]) -> Path:
        unsigned = dict(payload)
        unsigned.pop("content_sha256", None)
        digest = hashlib.sha256(
            json.dumps(
                unsigned,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        payload["content_sha256"] = digest
        rewritten = path.with_name(
            f"{int(payload['sequence']):08d}-{digest}-{payload['receipt_id']}.json"
        )
        if rewritten != path:
            path.unlink(missing_ok=True)
        rewritten.write_text(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        rewritten.chmod(0o600)
        return rewritten

    def test_canonical_receipt_is_redacted_atomic_and_bound_to_final_reread(
        self,
    ) -> None:
        receipt = self.canonical_receipt()

        self.assertEqual(receipt.provenance, "canonical")
        self.assertEqual(receipt.review_input_schema_version, 2)
        self.assertEqual(receipt.review_input_sha256, self.review_input_sha256)
        self.assertEqual(
            receipt.as_json()["publisher"],
            {"name": "publishing-reviewable-prs", "version": 1},
        )
        self.assertEqual(receipt.as_json()["policy"], {"version": 1})
        receipts = RECEIPTS.load_receipts(self.receipt_directory, self.expected)
        self.assertEqual(receipts, [receipt])
        receipt_path = next(self.receipt_directory.rglob("*.json"))
        raw = receipt_path.read_text(encoding="utf-8")
        self.assertNotIn(self.title, raw)
        self.assertNotIn(self.body, raw)
        self.assertEqual(receipt_path.stat().st_mode & 0o077, 0)
        self.assertFalse(list(self.receipt_directory.rglob("*.tmp")))

    def test_v3_receipt_distinguishes_required_not_required_and_reconciliation(
        self,
    ) -> None:
        observation = REQUIRED_REVIEW.RequiredReviewObservation(
            launch_envelope_sha256="1" * 64,
            generation="sha256-" + "2" * 64,
            active_record_sha256="3" * 64,
            trust_context_sha256="4" * 64,
            bundle_sha256="5" * 64,
            tricritical_manifest_sha256="6" * 64,
            tricritical_projection_sha256="7" * 64,
        )
        required_root = Path(self.temporary_directory.name) / "required"
        RECEIPTS.prepare_receipt_store(required_root)
        required = self.canonical_receipt(
            root=required_root,
            review=transition_review("required", "8" * 64, observation),
        )
        self.assertEqual(required.schema_version, 4)
        self.assertEqual(required.summary("verified")["review"]["mode"], "required")
        self.assertEqual(
            required.summary("verified")["review"]["observation"][
                "launch_envelope_sha256"
            ],
            "1" * 64,
        )

        not_required = self.canonical_receipt()
        self.assertEqual(
            not_required.summary("verified")["review"],
            {
                "mode": "not-required",
                "publication_candidate_sha256": (
                    not_required.review.publication_candidate_sha256
                ),
                "observation": None,
            },
        )

        reconciliation_root = Path(self.temporary_directory.name) / "reconcile"
        RECEIPTS.prepare_receipt_store(reconciliation_root)
        reconciled = self.reconciled_receipt(root=reconciliation_root)
        self.assertIsNone(reconciled.review)
        self.assertEqual(
            reconciled.summary("verified")["review"],
            {"state": "unwitnessed-reconciliation"},
        )

    def test_audit_direct_reader_exception_is_value_free_unavailable(self) -> None:
        receipt = self.canonical_receipt()
        receipts_before = {
            path: path.read_bytes() for path in self.receipt_directory.rglob("*.json")
        }

        def failed_read() -> dict[str, object]:
            raise OSError("Authorization: arbitrary-secret-value\x1b[31m")

        result = RECEIPTS.audit_publication(
            root=self.receipt_directory,
            expected=self.expected,
            read_live=failed_read,
        )

        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.receipt, receipt)
        self.assertIn("live PR state read failed", result.reason)
        rendered = json.dumps(result.as_json(), sort_keys=True)
        self.assertNotIn("Authorization", rendered)
        self.assertNotIn("arbitrary-secret-value", rendered)
        self.assertNotIn("OSError", rendered)
        self.assertNotIn("Traceback", rendered)
        self.assertEqual(
            {
                path: path.read_bytes()
                for path in self.receipt_directory.rglob("*.json")
            },
            receipts_before,
        )

    def test_audit_direct_state_read_error_does_not_display_exception_data(
        self,
    ) -> None:
        receipt = self.canonical_receipt()

        def failed_read() -> dict[str, object]:
            raise STATE.StateReadError(UnprintableExceptionData())

        result = RECEIPTS.audit_publication(
            root=self.receipt_directory,
            expected=self.expected,
            read_live=failed_read,
        )

        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.receipt, receipt)
        self.assertEqual(
            result.reason,
            "live PR state read failed for an unclassified reason; details were "
            "withheld because they may contain sensitive data",
        )

    def test_v2_receipt_remains_chained_but_is_only_legacy_unrecorded(self) -> None:
        receipt = self.canonical_receipt()
        path = next(self.receipt_directory.rglob("*.json"))
        payload = receipt.as_json()
        payload["schema_version"] = 2
        del payload["review"]
        self.rewrite_receipt(path, payload)

        loaded = RECEIPTS.load_receipts(self.receipt_directory, self.expected)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].schema_version, 2)
        self.assertIsNone(loaded[0].review)
        self.assertEqual(
            loaded[0].summary("verified")["review"],
            {"state": "legacy-unrecorded"},
        )

    def test_receipt_audit_accepts_bot_blocks_quoting_their_closing_marker(self) -> None:
        self.canonical_receipt()
        markers = (
            ("<!-- tips_start -->", "<!-- tips_end -->"),
            (
                "<!-- This is an auto-generated comment: release notes by coderabbit.ai -->",
                "<!-- end of auto-generated comment: release notes by coderabbit.ai -->",
            ),
        )
        for opener, closer in markers:
            for newline in ("\n", "\r", "\r\n"):
                for quoted in (
                    f"Quoted `{closer}` in prose.",
                    f"Example:\n`{closer}`\nMore notes.",
                ):
                    with self.subTest(
                        opener=opener, newline=repr(newline), quoted=quoted
                    ):
                        tail = "\n".join(
                            (
                                "",
                                opener,
                                quoted,
                                closer,
                                "<!-- review_stack_entry_start -->",
                                "Another complete block.",
                                "<!-- review_stack_entry_end -->",
                            )
                        ).replace("\n", newline)
                        live = self.stored(body=self.body + tail)
                        result = RECEIPTS.audit_publication(
                            root=self.receipt_directory,
                            expected=self.expected,
                            read_live=lambda: live,
                        )
                        self.assertEqual(result.status, "verified")

    def test_receipt_audit_preserves_authored_gaps_between_bot_blocks(self) -> None:
        self.canonical_receipt()
        first = "\n<!-- tips_start -->\nBot notes.\n<!-- tips_end -->"
        gap = "\nHuman text between bot blocks.\n"
        for last in (
            "<!-- tips_start -->\nMore bot notes.\n<!-- tips_end -->",
            "<!-- walkthrough_start -->\nMore bot notes.\n<!-- walkthrough_end -->",
            "<!-- tips_end -->",
        ):
            with self.subTest(last=last):
                body = self.body + first + gap + last
                self.assertIn(
                    "Human text between bot blocks.",
                    PUBLICATION_SUPPORT_BOT.authored_body(body),
                )
                result = RECEIPTS.audit_publication(
                    root=self.receipt_directory,
                    expected=self.expected,
                    read_live=lambda: self.stored(body=body),
                )
                self.assertEqual(result.status, "drift")

    def test_receipt_audit_rejects_authored_text_before_repeated_opener(self) -> None:
        self.canonical_receipt()
        tail = (
            "\n<!-- tips_start -->\nHuman authored text.\n"
            "<!-- tips_start -->\nGenerated notes.\n<!-- tips_end -->"
        )
        result = RECEIPTS.audit_publication(
            root=self.receipt_directory,
            expected=self.expected,
            read_live=lambda: self.stored(body=self.body + tail),
        )
        self.assertEqual(result.status, "drift")

    def test_receipt_audit_accepts_different_nested_bot_markers(self) -> None:
        self.canonical_receipt()
        tail = (
            "\n<!-- review_stack_entry_start -->\nStack notes.\n"
            "<!-- tips_start -->\nGenerated notes.\n<!-- tips_end -->\n"
            "<!-- review_stack_entry_end -->"
        )
        result = RECEIPTS.audit_publication(
            root=self.receipt_directory,
            expected=self.expected,
            read_live=lambda: self.stored(body=self.body + tail),
        )
        self.assertEqual(result.status, "verified")

    def test_receipt_audit_rejects_inline_only_closing_markers(self) -> None:
        self.canonical_receipt()
        for tail in (
            "\n<!-- tips_start -->\nInline closer <!-- tips_end -->",
            "\n<!-- tips_start -->\n<!-- tips_end -->\nUnclosed following prose.",
        ):
            with self.subTest(tail=tail):
                result = RECEIPTS.audit_publication(
                    root=self.receipt_directory,
                    expected=self.expected,
                    read_live=lambda: self.stored(body=self.body + tail),
                )
                self.assertEqual(result.status, "drift")

    def test_v2_audit_uses_raw_body_hash_for_legacy_receipts(self) -> None:
        bot_tail = (
            "\n<!-- This is an auto-generated comment: release notes by coderabbit.ai -->\n"
            "notes\n"
            "<!-- end of auto-generated comment: release notes by coderabbit.ai -->"
        )
        before = self.stored()
        after = self.stored(body=self.body + "changed\n")
        live = self.stored(body=after["body"] + bot_tail)
        receipt = self.canonical_receipt(
            operation="update-text", before=before, after=after
        )
        path = next(self.receipt_directory.rglob("*.json"))
        payload = receipt.as_json()
        payload["schema_version"] = 2
        del payload["review"]
        payload["preimage"]["body_sha256"] = hashlib.sha256(
            self.body.encode("utf-8")
        ).hexdigest()
        payload["final_state"]["body_sha256"] = hashlib.sha256(
            live["body"].encode("utf-8")
        ).hexdigest()
        self.rewrite_receipt(path, payload)

        result = RECEIPTS.audit_publication(
            root=self.receipt_directory,
            expected=self.expected,
            read_live=lambda: live,
        )
        self.assertEqual(result.status, "verified")

    def test_v3_audit_uses_raw_body_hash_for_historical_receipts(self) -> None:
        bot_tail = (
            "\n<!-- This is an auto-generated comment: release notes by coderabbit.ai -->\n"
            "notes\n"
            "<!-- end of auto-generated comment: release notes by coderabbit.ai -->"
        )
        before = self.stored()
        after = self.stored(body=self.body + "changed\n")
        live = self.stored(body=after["body"] + bot_tail)
        receipt = self.canonical_receipt(
            operation="update-text", before=before, after=after
        )
        path = next(self.receipt_directory.rglob("*.json"))
        payload = receipt.as_json()
        payload["schema_version"] = 3
        payload["preimage"]["body_sha256"] = hashlib.sha256(
            self.body.encode("utf-8")
        ).hexdigest()
        payload["final_state"]["body_sha256"] = hashlib.sha256(
            live["body"].encode("utf-8")
        ).hexdigest()
        self.rewrite_receipt(path, payload)

        result = RECEIPTS.audit_publication(
            root=self.receipt_directory,
            expected=self.expected,
            read_live=lambda: live,
        )
        self.assertEqual(result.status, "verified")

    def test_receipt_ledger_rejects_every_schema_rollback(self) -> None:
        state_a = self.stored(title="state A")
        self.canonical_receipt(after=state_a)
        state_b = self.stored(title="state B")
        self.canonical_receipt(operation="update-text", before=state_a, after=state_b)
        path = sorted(self.receipt_directory.rglob("*.json"))[1]
        original = json.loads(path.read_text(encoding="utf-8"))
        for version in (2, 3):
            with self.subTest(version=version):
                payload = dict(original)
                payload["schema_version"] = version
                if version == 2:
                    del payload["review"]
                path = self.rewrite_receipt(path, payload)
                with self.assertRaisesRegex(RECEIPTS.ReceiptError, "moved backward"):
                    RECEIPTS.load_receipts(self.receipt_directory, self.expected)

    def test_review_from_candidate_a_cannot_mint_candidate_b_provenance(
        self,
    ) -> None:
        state_a = self.stored(title="candidate A")
        state_b = self.stored(title="candidate B")
        candidate_a = self.transition_candidate(
            operation="update-text", final_state=state_a, mode="not-required"
        )
        candidate_b = self.transition_candidate(
            operation="update-text", final_state=state_b, mode="not-required"
        )
        review_a = transition_review("not-required", candidate_a.content_sha256, None)

        with self.assertRaisesRegex(RECEIPTS.ReceiptError, "candidate evidence"):
            RECEIPTS.verified_transition(
                expected=self.expected,
                operation="update-text",
                preimage=self.stored(),
                final_reread=state_b,
                review_input_schema_version=self.review_input_schema_version,
                review_input_sha256=self.review_input_sha256,
                review=review_a,
                candidate=candidate_b,
            )

    def test_parsed_receipt_review_cannot_mint_a_new_transition(self) -> None:
        state = self.stored(title="candidate state")
        candidate = self.transition_candidate(
            operation="update-text", final_state=state, mode="not-required"
        )
        parsed = REQUIRED_REVIEW.parse_publication_review(
            transition_review("not-required", candidate.content_sha256, None).as_json()
        )

        with self.assertRaisesRegex(RECEIPTS.ReceiptError, "candidate evidence"):
            RECEIPTS.verified_transition(
                expected=self.expected,
                operation="update-text",
                preimage=self.stored(),
                final_reread=state,
                review_input_schema_version=self.review_input_schema_version,
                review_input_sha256=self.review_input_sha256,
                review=parsed,
                candidate=candidate,
            )

    def test_receipt_write_failure_never_exposes_a_partial_final_receipt(self) -> None:
        with mock.patch.object(RECEIPTS.os, "link", side_effect=OSError("full")):
            with self.assertRaisesRegex(RECEIPTS.ReceiptError, "atomically commit"):
                self.canonical_receipt()
        self.assertFalse(list(self.receipt_directory.rglob("*.json")))

    def test_text_mutation_records_only_its_verified_final_reread(self) -> None:
        desired_path = Path(self.temporary_directory.name) / "desired.md"
        desired_path.write_text(self.body + "updated\n", encoding="utf-8")
        desired = desired_path.read_text(encoding="utf-8")
        after = self.stored(body=desired)
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE,
                "_stored_pr",
                side_effect=[self.stored(), self.stored(), self.stored(), after],
            ),
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ),
        ):
            result = UPDATE.update_text(
                expected=self.expected,
                expected_title_sha256=hashlib.sha256(
                    self.title.encode("utf-8")
                ).hexdigest(),
                expected_body_sha256=hashlib.sha256(
                    self.body.encode("utf-8")
                ).hexdigest(),
                expected_draft=True,
                title=self.title,
                body_path=desired_path,
                review_input_path=self.template_path,
                review_mode="not-required",
                review_bundle_root=None,
                selected_specialists=[],
                receipt_directory=self.receipt_directory,
            )
        receipt = RECEIPTS.load_receipts(self.receipt_directory, self.expected)[0]
        self.assertEqual(result, after)
        self.assertEqual(receipt.operation, "update-text")
        self.assertEqual(
            receipt.final_state.body_sha256,
            hashlib.sha256(desired.encode()).hexdigest(),
        )

    def test_receipt_failure_after_mutation_does_not_trigger_a_second_mutation(
        self,
    ) -> None:
        desired_path = Path(self.temporary_directory.name) / "desired.md"
        desired_path.write_text(self.body + "updated\n", encoding="utf-8")
        after = self.stored(body=desired_path.read_text(encoding="utf-8"))
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(
                UPDATE,
                "_stored_pr",
                side_effect=[self.stored(), self.stored(), self.stored(), after],
            ),
            mock.patch.object(
                UPDATE,
                "_run_mutation",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as mutate,
            mock.patch.object(
                UPDATE,
                "record_verified_publication",
                side_effect=RECEIPTS.ReceiptError("receipt disk unavailable"),
            ),
        ):
            with self.assertRaisesRegex(RECEIPTS.ReceiptError, "receipt disk"):
                UPDATE.update_text(
                    expected=self.expected,
                    expected_title_sha256=hashlib.sha256(
                        self.title.encode("utf-8")
                    ).hexdigest(),
                    expected_body_sha256=hashlib.sha256(
                        self.body.encode("utf-8")
                    ).hexdigest(),
                    expected_draft=True,
                    title=self.title,
                    body_path=desired_path,
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )
        self.assertEqual(mutate.call_count, 1)

    def test_receipt_rejects_state_that_was_not_exactly_final_reread(self) -> None:
        with self.assertRaisesRegex(RECEIPTS.ReceiptError, "invalid or unverified"):
            self.canonical_receipt(after=self.stored(headRefOid="c" * 40))
        with self.assertRaisesRegex(
            RECEIPTS.ReceiptError, "invalid or unverified"
        ) as caught:
            self.canonical_receipt(
                after=self.stored(body="Authorization: arbitrary-secret-value\ud800")
            )
        self.assertIsInstance(
            caught.exception.__cause__, STATE.LiveStateResponseError
        )
        self.assertNotIn("arbitrary-secret-value", str(caught.exception))

    def test_audit_returns_verified_drift_and_unavailable_without_mutation(
        self,
    ) -> None:
        receipt = self.canonical_receipt()
        with mock.patch.object(AUDIT, "stored_pr", return_value=self.stored()):
            verified = AUDIT.audit(
                expected=self.expected,
                receipt_directory=self.receipt_directory,
            )
        self.assertEqual(verified.status, "verified")
        self.assertEqual(verified.receipt, receipt)
        with mock.patch.object(
            AUDIT, "stored_pr", return_value=self.stored(title="changed")
        ):
            drift = AUDIT.audit(
                expected=self.expected,
                receipt_directory=self.receipt_directory,
            )
        self.assertEqual(drift.status, "drift")
        with mock.patch.object(
            AUDIT,
            "stored_pr",
            side_effect=STATE.StateReadError("offline"),
        ):
            unavailable = AUDIT.audit(
                expected=self.expected,
                receipt_directory=self.receipt_directory,
            )
        self.assertEqual(unavailable.status, "unavailable")

    def test_malformed_receipts_are_not_treated_as_absent(self) -> None:
        self.canonical_receipt()
        malformed = next(self.receipt_directory.rglob("*.json")).parent / "bad.json"
        malformed.write_text('{"schema_version": 1}\n', encoding="utf-8")
        malformed.chmod(0o600)
        with self.assertRaisesRegex(RECEIPTS.ReceiptError, "unexpected entry"):
            RECEIPTS.load_receipts(self.receipt_directory, self.expected)
        with mock.patch.object(AUDIT, "stored_pr", return_value=self.stored()):
            audit = AUDIT.audit(
                expected=self.expected,
                receipt_directory=self.receipt_directory,
            )
        self.assertEqual(audit.status, "unavailable")

    def test_reconciliation_is_redacted_and_permanently_unreceipted(self) -> None:
        receipt = self.reconciled_receipt()
        self.assertEqual(receipt.provenance, "reconciled-unreceipted")
        self.assertEqual(receipt.operation, "reconcile")
        with self.assertRaisesRegex(RECEIPTS.ReceiptError, "already matches"):
            self.reconciled_receipt()
        canonical_directory = Path(self.temporary_directory.name) / "canonical"
        RECEIPTS.prepare_receipt_store(canonical_directory)
        self.canonical_receipt(root=canonical_directory)
        with self.assertRaisesRegex(RECEIPTS.ReceiptError, "already matches"):
            self.reconciled_receipt(root=canonical_directory)

    def test_reconciliation_duplicate_suppression_is_scoped_to_complete_oid_epoch(
        self,
    ) -> None:
        unchanged = self.stored()
        self.reconciled_receipt()
        new_expected = STATE.ExpectedIdentity(
            repository=self.repository,
            pr_number=self.pr_number,
            base=self.base,
            base_oid="c" * 40,
            head=self.head,
            head_oid="d" * 40,
            head_owner=self.head_owner,
            head_repository=self.head_repository,
        )
        new_epoch_state = {
            **unchanged,
            "baseRefOid": "c" * 40,
            "headRefOid": "d" * 40,
        }
        transition = RECEIPTS.verified_transition(
            expected=new_expected,
            operation="reconcile",
            preimage=new_epoch_state,
            final_reread=new_epoch_state,
            review_input_schema_version=self.review_input_schema_version,
            review_input_sha256=self.review_input_sha256,
            review=None,
            candidate=None,
        )
        RECEIPTS.prepare_receipt_ledger(self.receipt_directory, new_expected)
        with RECEIPTS.receipt_ledger_lock(
            self.receipt_directory, new_expected
        ) as lease:
            new_epoch = RECEIPTS.record_reconciliation(
                root=self.receipt_directory,
                transition=transition,
                lease=lease,
            )
        self.assertEqual(new_epoch.sequence, 2)
        self.assertEqual(new_epoch.expected.head_oid, "d" * 40)
        with RECEIPTS.receipt_ledger_lock(
            self.receipt_directory, new_expected
        ) as lease:
            with self.assertRaisesRegex(RECEIPTS.ReceiptError, "already matches"):
                RECEIPTS.record_reconciliation(
                    root=self.receipt_directory,
                    transition=transition,
                    lease=lease,
                )

    def test_reconciliation_preserves_the_existing_secret_gate(self) -> None:
        secret = "ghp_123456789012345678901234567890"
        with mock.patch.object(
            AUDIT, "stored_pr", return_value=self.stored(body=f"Credential: {secret}")
        ):
            with self.assertRaisesRegex(
                AUDIT.PublicationError, "reconciliation is blocked"
            ) as raised:
                AUDIT.reconcile(
                    expected=self.expected,
                    receipt_directory=self.receipt_directory,
                    review_input_path=self.template_path,
                )
        self.assertNotIn(secret, str(raised.exception))

    def test_reconciled_receipt_cannot_be_relabelled_canonical(self) -> None:
        receipt = self.reconciled_receipt()
        path = next(self.receipt_directory.rglob("*.json"))
        payload = receipt.as_json()
        payload["provenance"] = "canonical"
        payload["operation"] = "create"
        self.rewrite_receipt(path, payload)
        with self.assertRaisesRegex(
            RECEIPTS.ReceiptError, "transition|review evidence"
        ):
            RECEIPTS.load_receipts(self.receipt_directory, self.expected)

    def test_reconcile_binds_the_live_state_to_review_input_before_receipting(
        self,
    ) -> None:
        with (
            mock.patch.object(AUDIT, "stored_pr", return_value=self.stored()),
            mock.patch.object(
                AUDIT,
                "_validate_live_state",
                return_value=(
                    self.review_input_schema_version,
                    self.review_input_sha256,
                    hashlib.sha256(self.body.encode()).hexdigest(),
                ),
            ) as validate,
        ):
            receipt = AUDIT.reconcile(
                expected=self.expected,
                receipt_directory=self.receipt_directory,
                review_input_path=self.template_path,
            )
        self.assertEqual(receipt.provenance, "reconciled-unreceipted")
        validate.assert_called_once_with(
            expected=self.expected,
            title=self.title,
            body=self.body,
            review_input_path=self.template_path,
        )

    def test_reconciliation_accepts_a_fresh_bot_append(self) -> None:
        body = self.body.rstrip("\r\n")
        tail = "\n\n" + UpdateReviewablePrTests.BOT_TAIL.lstrip("\n")
        before = self.stored(body=body)
        after = self.stored(body=body + tail)
        digest = hashlib.sha256(body.encode()).hexdigest()
        with (
            mock.patch.object(AUDIT, "stored_pr", side_effect=[before, after]),
            mock.patch.object(
                AUDIT,
                "_validate_live_state",
                return_value=(
                    self.review_input_schema_version,
                    self.review_input_sha256,
                    digest,
                ),
            ),
        ):
            receipt = AUDIT.reconcile(
                expected=self.expected,
                receipt_directory=self.receipt_directory,
                review_input_path=self.template_path,
            )
        self.assertEqual(receipt.final_state.body_sha256, digest)
        self.assertTrue(RECEIPTS.receipt_matches_live(receipt, after))

    def test_audit_uses_only_authoritative_latest_receipt(self) -> None:
        state_a = self.stored(title="state A")
        self.canonical_receipt(after=state_a)
        state_b = self.stored(title="state B")
        self.canonical_receipt(
            operation="update-text",
            before=state_a,
            after=state_b,
        )
        with mock.patch.object(AUDIT, "stored_pr", return_value=state_a):
            result = AUDIT.audit(
                expected=self.expected,
                receipt_directory=self.receipt_directory,
            )
        self.assertEqual(result.status, "drift")
        self.assertEqual(result.receipt.sequence, 2)

    def test_record_api_rejects_arbitrary_stored_state_and_canonical_noop(
        self,
    ) -> None:
        with self.assertRaises(TypeError):
            RECEIPTS.record_verified_publication(
                root=self.receipt_directory,
                expected=self.expected,
                stored=self.stored(),
            )
        with self.assertRaisesRegex(RECEIPTS.ReceiptError, "actual state transition"):
            RECEIPTS.verified_transition(
                expected=self.expected,
                operation="update-text",
                preimage=self.stored(),
                final_reread=self.stored(),
                review_input_schema_version=self.review_input_schema_version,
                review_input_sha256=self.review_input_sha256,
                review=None,
                candidate=None,
            )

    def test_text_noop_stops_before_store_probe_or_mutation(self) -> None:
        same_body = Path(self.temporary_directory.name) / "same.md"
        same_body.write_text(self.body, encoding="utf-8")
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(UPDATE, "_stored_pr", return_value=self.stored()),
            mock.patch.object(UPDATE, "prepare_receipt_store") as prepare,
            mock.patch.object(UPDATE, "_run_mutation") as mutate,
        ):
            with self.assertRaisesRegex(UPDATE.PublicationError, "no-op"):
                UPDATE.update_text(
                    expected=self.expected,
                    expected_title_sha256=hashlib.sha256(
                        self.title.encode("utf-8")
                    ).hexdigest(),
                    expected_body_sha256=hashlib.sha256(
                        self.body.encode("utf-8")
                    ).hexdigest(),
                    expected_draft=True,
                    title=self.title,
                    body_path=same_body,
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )
        prepare.assert_not_called()
        mutate.assert_not_called()

    def test_default_root_is_continuous_across_record_and_audit(self) -> None:
        xdg = Path(self.temporary_directory.name) / "xdg-state"
        with mock.patch.dict(os.environ, {"XDG_STATE_HOME": str(xdg)}):
            root = RECEIPTS.prepare_receipt_store()
            RECEIPTS.prepare_receipt_ledger(root, self.expected)
            receipt = self.canonical_receipt(root=root)
            result = RECEIPTS.audit_publication(
                root=None,
                expected=self.expected,
                read_live=lambda: self.stored(),
            )
        self.assertEqual(root, xdg / "mergecraft/pr-publication-receipts")
        self.assertEqual(result.status, "verified")
        self.assertEqual(result.receipt.receipt_id, receipt.receipt_id)
        override = Path(self.temporary_directory.name) / "migration-root"
        self.assertEqual(RECEIPTS.resolve_receipt_root(override), override)

    def test_bad_receipt_store_blocks_before_text_mutation(self) -> None:
        bad_root = Path(self.temporary_directory.name) / "bad-root"
        bad_root.mkdir(mode=0o700)
        bad_root.chmod(0o755)
        desired = Path(self.temporary_directory.name) / "changed.md"
        desired.write_text(self.body + "changed\n", encoding="utf-8")
        with (
            mock.patch.object(UPDATE, "_validate_body"),
            mock.patch.object(UPDATE, "_stored_pr", return_value=self.stored()),
            mock.patch.object(UPDATE, "_run_mutation") as mutate,
        ):
            with self.assertRaisesRegex(RECEIPTS.ReceiptError, "private owned"):
                UPDATE.update_text(
                    expected=self.expected,
                    expected_title_sha256=hashlib.sha256(
                        self.title.encode("utf-8")
                    ).hexdigest(),
                    expected_body_sha256=hashlib.sha256(
                        self.body.encode("utf-8")
                    ).hexdigest(),
                    expected_draft=True,
                    title=self.title,
                    body_path=desired,
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=bad_root,
                )
        mutate.assert_not_called()

    def test_title_secret_gate_covers_create_update_ready_and_reconcile(self) -> None:
        secret = "ghp_123456789012345678901234567890"
        with mock.patch.object(CREATE, "_create") as create:
            with self.assertRaisesRegex(CREATE.PublicationError, "suspected") as raised:
                CREATE.publish(
                    repository=self.repository,
                    base=self.base,
                    base_oid=self.base_oid,
                    head=self.head,
                    head_oid=self.head_oid,
                    head_owner=self.head_owner,
                    head_repository=self.head_repository,
                    title=f"Credential {secret}",
                    template_path=self.template_path,
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )
        create.assert_not_called()
        self.assertNotIn(secret, str(raised.exception))
        changed = Path(self.temporary_directory.name) / "changed.md"
        changed.write_text(self.body + "changed\n", encoding="utf-8")
        with mock.patch.object(UPDATE, "_run_mutation") as mutate:
            with self.assertRaisesRegex(UPDATE.PublicationError, "suspected"):
                UPDATE.update_text(
                    expected=self.expected,
                    expected_title_sha256="0" * 64,
                    expected_body_sha256="0" * 64,
                    expected_draft=True,
                    title=f"Credential {secret}",
                    body_path=changed,
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )
        mutate.assert_not_called()
        secret_state = self.stored(title=f"Credential {secret}")
        with mock.patch.object(UPDATE, "_stored_pr", return_value=secret_state):
            with self.assertRaisesRegex(UPDATE.PublicationError, "suspected"):
                UPDATE.mark_ready(
                    expected=self.expected,
                    expected_title_sha256=hashlib.sha256(
                        str(secret_state["title"]).encode("utf-8")
                    ).hexdigest(),
                    expected_body_sha256=hashlib.sha256(
                        self.body.encode("utf-8")
                    ).hexdigest(),
                    review_input_path=self.template_path,
                    review_mode="not-required",
                    review_bundle_root=None,
                    selected_specialists=[],
                    receipt_directory=self.receipt_directory,
                )
        with mock.patch.object(AUDIT, "stored_pr", return_value=secret_state):
            with self.assertRaisesRegex(AUDIT.PublicationError, "suspected"):
                AUDIT.reconcile(
                    expected=self.expected,
                    receipt_directory=self.receipt_directory,
                    review_input_path=self.template_path,
                )

    def test_secret_gate_covers_structured_provider_credentials(self) -> None:
        candidates = (
            ('AKIAABCDEF' + 'GHIJKLMNOP'),
            ('sk-proj-abcdefghijkl' + 'mnopqrstuvwxyz012345'),
            (('xox' + 'b-1234567890-abcde') + 'fghijklmnopqrstuvwxyz'),
            ('glpat-abcdefghijklm' + 'nopqrstuvwxyz012345'),
            ('npm_abcdefghijklmn' + 'opqrstuvwxyz012345'),
            ('AIzaabcdefghijklmnop' + 'qrstuvwxyz0123456789'),
            ('sk_live_abcdefghi' + 'jklmnopqrstuvwxyz'),
            ('eyJabcdefghijk.abcde' + 'fghijkl.abcdefghijkl'),
        )
        for candidate in candidates:
            with self.subTest(prefix=candidate.split("-", 1)[0]):
                self.assertIsNotNone(CREATE.suspected_secret_error(candidate))

    def test_production_clis_do_not_expose_receipt_root_override(self) -> None:
        for script in (
            SCRIPTS / "create_reviewable_pr.py",
            SCRIPTS / "update_reviewable_pr.py",
            SCRIPTS / "audit_reviewable_pr.py",
        ):
            result = subprocess.run(
                [sys.executable, str(script), "--help"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("--receipt-directory", result.stdout)

    def test_relocated_writer_publisher_duo_loads_without_installed_projection(
        self,
    ) -> None:
        source_skills = SCRIPTS.parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            skills = Path(temporary) / "relocated bundle" / "skills"
            skills.mkdir(parents=True)
            for skill in (
                "writing-reviewable-pr-descriptions",
                "publishing-reviewable-prs",
            ):
                shutil.copytree(
                    source_skills / skill,
                    skills / skill,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )
            environment = {
                "PATH": os.defpath,
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            for script in (
                skills
                / "writing-reviewable-pr-descriptions/scripts/"
                "validate_change_navigation.py",
                skills
                / "publishing-reviewable-prs/scripts/create_reviewable_pr.py",
                skills
                / "publishing-reviewable-prs/scripts/update_reviewable_pr.py",
                skills
                / "publishing-reviewable-prs/scripts/audit_reviewable_pr.py",
            ):
                result = subprocess.run(
                    [sys.executable, "-E", "-S", "-B", str(script), "--help"],
                    text=True,
                    capture_output=True,
                    check=False,
                    env=environment,
                    cwd=temporary,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(
                (
                    skills
                    / "publishing-reviewable-prs/scripts/"
                    "literal_create_reviewable_pr.py"
                ).exists()
            )

    def test_oid_epoch_rollover_preserves_history_and_latest_authority(self) -> None:
        old_state = self.stored(title="old epoch")
        self.canonical_receipt(after=old_state)
        new_expected = STATE.ExpectedIdentity(
            repository=self.repository,
            pr_number=self.pr_number,
            base=self.base,
            base_oid="c" * 40,
            head=self.head,
            head_oid="d" * 40,
            head_owner=self.head_owner,
            head_repository=self.head_repository,
        )
        before = self.stored(
            title="new epoch before", baseRefOid="c" * 40, headRefOid="d" * 40
        )
        after = self.stored(
            title="new epoch after", baseRefOid="c" * 40, headRefOid="d" * 40
        )
        transition = RECEIPTS.verified_transition(
            expected=new_expected,
            operation="update-text",
            preimage=before,
            final_reread=after,
            review_input_schema_version=self.review_input_schema_version,
            review_input_sha256=self.review_input_sha256,
            review=transition_review(
                "not-required",
                self.transition_candidate(
                    operation="update-text",
                    final_state=after,
                    mode="not-required",
                    expected=new_expected,
                ).content_sha256,
                None,
            ),
            candidate=self.transition_candidate(
                operation="update-text",
                final_state=after,
                mode="not-required",
                expected=new_expected,
            ),
        )
        RECEIPTS.prepare_receipt_ledger(self.receipt_directory, new_expected)
        with RECEIPTS.receipt_ledger_lock(
            self.receipt_directory, new_expected
        ) as lease:
            latest = RECEIPTS.record_verified_publication(
                root=self.receipt_directory,
                transition=transition,
                lease=lease,
            )
        receipts = RECEIPTS.load_receipts(self.receipt_directory, new_expected)
        self.assertEqual([receipt.sequence for receipt in receipts], [1, 2])
        self.assertEqual(receipts[0].expected.head_oid, self.head_oid)
        self.assertEqual(latest.expected.head_oid, "d" * 40)
        audit = RECEIPTS.audit_publication(
            root=self.receipt_directory,
            expected=new_expected,
            read_live=lambda: after,
        )
        self.assertEqual(audit.status, "verified")

    def test_receipt_append_requires_active_exclusive_lease(self) -> None:
        transition = RECEIPTS.verified_transition(
            expected=self.expected,
            operation="create",
            preimage=self.transport(),
            final_reread=self.stored(),
            review_input_schema_version=self.review_input_schema_version,
            review_input_sha256=self.review_input_sha256,
            review=transition_review(
                "not-required",
                self.transition_candidate(
                    operation="create",
                    final_state=self.stored(),
                    mode="not-required",
                ).content_sha256,
                None,
            ),
            candidate=self.transition_candidate(
                operation="create",
                final_state=self.stored(),
                mode="not-required",
            ),
        )
        inactive = RECEIPTS.LedgerLease(
            root=self.receipt_directory,
            identity_key=f"ledger-{RECEIPTS._identity_key(self.expected)}",
            exclusive=True,
            active=False,
        )
        with self.assertRaisesRegex(RECEIPTS.ReceiptError, "active exclusive"):
            RECEIPTS.record_verified_publication(
                root=self.receipt_directory,
                transition=transition,
                lease=inactive,
            )

    def test_two_process_append_is_serialized_without_sequence_fork(self) -> None:
        child = """
import hashlib
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from publication_receipts import (
    prepare_receipt_ledger,
    receipt_ledger_lock,
    record_verified_publication,
    verified_transition,
)
from required_review import (
    PublicationCandidate,
    _identity_for,
    _required_profile,
    body_source_binding,
    validate_required_review,
)
from reviewable_pr_state import ExpectedIdentity
root = Path(sys.argv[2])
expected = ExpectedIdentity(
    'acme/app', 42, 'main', 'a' * 40, 'fork-owner:widget', 'b' * 40,
    'fork-owner', 'fork-owner/app-fork'
)
before = {
    'number': 42, 'url': expected.url, 'title': 'feat: widget',
    'body': 'transport', 'baseRefName': 'main', 'baseRefOid': 'a' * 40,
    'headRefName': 'widget', 'headRefOid': 'b' * 40,
    'headRepositoryOwner': {'login': 'fork-owner'},
    'headRepository': {'nameWithOwner': 'fork-owner/app-fork'},
    'isDraft': True, 'state': 'OPEN'
}
after = {**before, 'body': 'canonical'}
candidate_value = {
    'schema_version': 1, 'contract': 'mergecraft-publication-candidate-v1',
    'operation': 'update-text', 'repository': expected.repository,
    'pr_number': expected.pr_number,
    'base': {'ref': expected.base, 'oid': expected.base_oid},
    'head': {
        'ref': expected.head, 'oid': expected.head_oid,
        'owner': expected.head_owner, 'repository': expected.head_repository,
    },
    'title': after['title'],
    'body_source': body_source_binding(
        kind='body', raw=b'canonical', published='canonical',
        render_contract='literal-utf8-v1',
    ),
    'review_input': {
        'schema_version': 2, 'raw_sha256': 'e' * 64,
        'content_sha256': 'd' * 64,
    },
    'publication_profile': {
        'contract': 'mergecraft-publication-profile-v1',
        'review_mode': 'not-required', 'selected_specialists': [],
    },
}
candidate_sha = hashlib.sha256(json.dumps(
    candidate_value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
).encode('utf-8')).hexdigest()
candidate = PublicationCandidate(
    candidate_value, candidate_sha,
    {'kind': 'mergecraft-publication-candidate-v1',
     'value': 'sha256:' + candidate_sha, 'content_sha256': candidate_sha},
    _identity_for('mergecraft-review-input-v1', candidate_value['review_input']),
    _identity_for(
        'mergecraft-required-publication-review-profile-v2',
        _required_profile([]),
    ),
    b'canonical', 'canonical',
)
review_input = candidate.value['review_input']
review = validate_required_review(
    review_mode='not-required', review_bundle_root=None, candidate=candidate,
)
transition = verified_transition(
    expected=expected, operation='update-text', preimage=before, final_reread=after,
    review_input_schema_version=review_input['schema_version'],
    review_input_sha256=review_input['content_sha256'],
    review=review,
    candidate=candidate,
)
prepare_receipt_ledger(root, expected)
with receipt_ledger_lock(root, expected) as lease:
    time.sleep(0.1)
    record_verified_publication(root=root, transition=transition, lease=lease)
"""
        processes = [
            subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    child,
                    str(SCRIPTS),
                    str(self.receipt_directory),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            for _ in range(2)
        ]
        for process in processes:
            stdout, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, stdout + stderr)
        receipts = RECEIPTS.load_receipts(self.receipt_directory, self.expected)
        self.assertEqual([receipt.sequence for receipt in receipts], [1, 2])
        self.assertLess(receipts[0].created_at, receipts[1].created_at)

    def test_backward_receipt_timestamp_fails_closed(self) -> None:
        state_a = self.stored(title="state A")
        self.canonical_receipt(after=state_a)
        state_b = self.stored(title="state B")
        self.canonical_receipt(operation="update-text", before=state_a, after=state_b)
        path = sorted(self.receipt_directory.rglob("*.json"))[1]
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["created_at"] = "2000-01-01T00:00:00.000000Z"
        self.rewrite_receipt(path, payload)
        with self.assertRaisesRegex(RECEIPTS.ReceiptError, "timestamps"):
            RECEIPTS.load_receipts(self.receipt_directory, self.expected)

    def test_reconcile_requires_identical_second_live_reread(self) -> None:
        with (
            mock.patch.object(
                AUDIT,
                "stored_pr",
                side_effect=[self.stored(), self.stored(title="concurrent")],
            ),
            mock.patch.object(
                AUDIT,
                "_validate_live_state",
                return_value=(
                    self.review_input_schema_version,
                    self.review_input_sha256,
                    hashlib.sha256(self.body.encode()).hexdigest(),
                ),
            ),
            mock.patch.object(AUDIT, "record_reconciliation") as record,
        ):
            with self.assertRaisesRegex(AUDIT.PublicationError, "changed"):
                AUDIT.reconcile(
                    expected=self.expected,
                    receipt_directory=self.receipt_directory,
                    review_input_path=self.template_path,
                )
        record.assert_not_called()

    def test_failed_later_receipt_can_be_reconciled_after_older_canonical(self) -> None:
        state_a = self.stored(title="state A")
        self.canonical_receipt(after=state_a)
        state_b = self.stored(title="state B")
        with mock.patch.object(RECEIPTS.os, "link", side_effect=OSError("full")):
            with self.assertRaises(RECEIPTS.ReceiptError):
                self.canonical_receipt(
                    operation="update-text",
                    before=state_a,
                    after=state_b,
                )
        with mock.patch.object(AUDIT, "stored_pr", return_value=state_b):
            result = AUDIT.audit(
                expected=self.expected,
                receipt_directory=self.receipt_directory,
            )
        self.assertEqual(result.status, "drift")
        transition = RECEIPTS.verified_transition(
            expected=self.expected,
            operation="reconcile",
            preimage=state_b,
            final_reread=state_b,
            review_input_schema_version=self.review_input_schema_version,
            review_input_sha256=self.review_input_sha256,
            review=None,
            candidate=None,
        )
        with RECEIPTS.receipt_ledger_lock(
            self.receipt_directory, self.expected
        ) as lease:
            reconciled = RECEIPTS.record_reconciliation(
                root=self.receipt_directory,
                transition=transition,
                lease=lease,
            )
        self.assertEqual(reconciled.sequence, 2)
        self.assertEqual(reconciled.provenance, "reconciled-unreceipted")

    def test_failed_link_cleans_temp_and_strict_temp_is_non_evidence(self) -> None:
        with mock.patch.object(RECEIPTS.os, "link", side_effect=OSError("full")):
            with self.assertRaises(RECEIPTS.ReceiptError):
                self.canonical_receipt()
        self.assertFalse(list(self.receipt_directory.rglob("*.tmp")))
        ledger = next(
            path
            for path in self.receipt_directory.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        )
        pending = ledger / f".pending-{uuid.uuid4()}.tmp"
        pending.write_text("interrupted", encoding="utf-8")
        pending.chmod(0o600)
        self.assertEqual(
            RECEIPTS.load_receipts(self.receipt_directory, self.expected), []
        )
        unexpected = ledger / ".pending-invalid.tmp"
        unexpected.write_text("invalid", encoding="utf-8")
        unexpected.chmod(0o600)
        with self.assertRaisesRegex(RECEIPTS.ReceiptError, "unexpected entry"):
            RECEIPTS.load_receipts(self.receipt_directory, self.expected)

    def test_disappearing_private_pending_temp_is_concurrent_non_evidence(
        self,
    ) -> None:
        RECEIPTS.prepare_receipt_ledger(self.receipt_directory, self.expected)
        ledger = next(
            path
            for path in self.receipt_directory.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        )
        pending = ledger / f".pending-{uuid.uuid4()}.tmp"
        pending.write_text("probe", encoding="utf-8")
        pending.chmod(0o600)
        original_lstat = Path.lstat

        def disappear_before_inspection(path: Path) -> os.stat_result:
            if path == pending:
                pending.unlink()
            return original_lstat(path)

        with mock.patch.object(Path, "lstat", new=disappear_before_inspection):
            self.assertEqual(
                RECEIPTS.load_receipts(self.receipt_directory, self.expected),
                [],
            )

    def test_strict_uuid_timestamp_filename_sequence_and_chain_validation(self) -> None:
        first = self.canonical_receipt()
        path = next(self.receipt_directory.rglob("*.json"))
        payload = first.as_json()
        payload["created_at"] = "2999-01-01T00:00:00.000000Z"
        path = self.rewrite_receipt(path, payload)
        with self.assertRaisesRegex(RECEIPTS.ReceiptError, "future"):
            RECEIPTS.load_receipts(self.receipt_directory, self.expected)

        path.unlink()
        uuid_one = str(uuid.uuid1())
        payload = first.as_json()
        payload["receipt_id"] = uuid_one
        path = self.rewrite_receipt(path, payload)
        with self.assertRaisesRegex(RECEIPTS.ReceiptError, "invalid value"):
            RECEIPTS.load_receipts(self.receipt_directory, self.expected)

        path.unlink()
        first = self.canonical_receipt()
        path = next(self.receipt_directory.rglob("*.json"))
        bad_name = path.with_name("00000009-" + path.name.split("-", 1)[1])
        path.rename(bad_name)
        with self.assertRaisesRegex(RECEIPTS.ReceiptError, "filename"):
            RECEIPTS.load_receipts(self.receipt_directory, self.expected)

    def test_sequence_gap_and_predecessor_fork_fail_closed(self) -> None:
        state_a = self.stored(title="state A")
        self.canonical_receipt(after=state_a)
        state_b = self.stored(title="state B")
        second = self.canonical_receipt(
            operation="update-text", before=state_a, after=state_b
        )
        paths = sorted(self.receipt_directory.rglob("*.json"))
        paths[0].unlink()
        with self.assertRaisesRegex(RECEIPTS.ReceiptError, "sequence"):
            RECEIPTS.load_receipts(self.receipt_directory, self.expected)

        payload = second.as_json()
        payload["sequence"] = 1
        payload["predecessor_sha256"] = "f" * 64
        self.rewrite_receipt(paths[1], payload)
        with self.assertRaisesRegex(RECEIPTS.ReceiptError, "predecessor"):
            RECEIPTS.load_receipts(self.receipt_directory, self.expected)


if __name__ == "__main__":
    unittest.main()
