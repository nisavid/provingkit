import base64
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
REPOSITORY = Path(__file__).resolve().parents[4]
SCRIPTS = (
    REPOSITORY / "plugins/mergecraft/skills/interacting-with-pr-review-feedback/scripts"
)
sys.path.insert(0, str(SCRIPTS))

import github_response_provider
import response_identity_lifecycle
import response_outcome_store
import response_runtime

TYPED_FIXTURE = (
    REPOSITORY
    / "tests/plugins/mergecraft/addressing-pr-review-feedback/fixtures/typed_feedback_epoch.json"
)


def make_intent(epoch, source, key="intent-1", body=b"Done"):
    inline = source["kind"] == "inline_review_comment"
    return {
        "schema_version": 1,
        "intent_key": key,
        "intent_kind": "ordinary",
        "admitted_epoch": epoch,
        "source": source,
        "operation": "create_inline_reply"
        if inline
        else "create_pull_request_conversation_comment",
        "placement": (
            {
                "kind": "review_thread",
                "thread_node_id": source["thread"]["node_id"],
                "root_comment_database_id": source["thread"][
                    "root_comment_database_id"
                ],
            }
            if inline
            else {"kind": "pull_request_conversation", "pr_number": 7}
        ),
        "writer": {
            "identity": "writer-1",
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "contract": "portable-github-markdown-authoring",
            "contract_version": "1",
            "field": "review_thread_reply"
            if inline
            else "pull_request_conversation_comment",
        },
        "classification": {
            "result": "human_feedback",
            "evidence_id": "classification-1",
        },
        "adjudication": {"disposition": "respond", "evidence_id": "adjudication-1"},
        "authority": {
            "decision": "authorized",
            "evidence_id": "authority-1",
            "actor_login": "ivan",
        },
        "independence_evidence": {
            "availability": "not_applicable",
            "reason": "initial_admission",
        },
    }


def exact_artifact(value):
    raw = response_outcome_store.canonical_bytes(value)
    return {
        "canonical_utf8_base64": base64.b64encode(raw).decode("ascii"),
        "byte_length": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def make_replacement_intent(basis, key="replacement", body=b"Done"):
    common = {
        "schema_version": 1,
        "replacement_basis_id": basis["basis_id"],
        "predecessor_intent_id": basis["predecessor_intent_id"],
        "predecessor_validation_id": basis["predecessor_validation_id"],
        "terminal_state": basis["terminal_state"],
        "terminal_record_id": basis["terminal_record_id"],
        "terminal_record_sha256": basis["terminal_record_sha256"],
        "successor_epoch_id": basis["successor_epoch_id"],
        "successor_epoch_sha256": basis["successor_epoch_sha256"],
        "source_scope_digest": basis["source_scope_digest"],
        "operation": basis["operation"],
        "placement": basis["placement"],
    }
    classification = exact_artifact(
        {
            **common,
            "artifact_kind": "classification",
            "result": "human_feedback",
            "evidence_id": "replacement-classification",
        }
    )
    adjudication = exact_artifact(
        {
            **common,
            "artifact_kind": "adjudication",
            "disposition": "respond",
            "evidence_id": "replacement-adjudication",
            "classification_artifact_sha256": classification["sha256"],
        }
    )
    authority = exact_artifact(
        {
            **common,
            "artifact_kind": "authority",
            "decision": "authorized",
            "evidence_id": "replacement-authority",
            "actor_login": "ivan",
            "classification_artifact_sha256": classification["sha256"],
            "adjudication_artifact_sha256": adjudication["sha256"],
        }
    )
    writer = exact_artifact(
        {
            **common,
            "artifact_kind": "writer_result",
            "identity": "replacement-writer",
            "contract": "portable-github-markdown-authoring",
            "contract_version": "1",
            "field": "review_thread_reply"
            if basis["operation"] == "create_inline_reply"
            else "pull_request_conversation_comment",
            "body": {
                "canonical_utf8_base64": base64.b64encode(body).decode("ascii"),
                "byte_length": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            },
            "classification_artifact_sha256": classification["sha256"],
            "adjudication_artifact_sha256": adjudication["sha256"],
            "authority_artifact_sha256": authority["sha256"],
        }
    )
    return {
        "schema_version": 2,
        "intent_key": key,
        "intent_kind": "ordinary",
        "replacement_basis_id": basis["basis_id"],
        "classification_artifact": classification,
        "adjudication_artifact": adjudication,
        "authority_artifact": authority,
        "writer_result_artifact": writer,
    }


def append_unknown_attempt(store, epoch, source, key):
    proposal = response_runtime._proposal(make_intent(epoch, source, key), b"Done")
    owner = response_runtime._owner(epoch, source, None)
    intent = response_runtime._intent_record(proposal, owner)
    validation_id = f"validation-{key}"
    attempt = {
        "attempt_id": f"attempt-{key}",
        "owner_id": owner["owner_id"],
        "intent_id": intent["intent_id"],
        "binding_digest": intent["binding_digest"],
        "ordinal": 1,
        "mode": "initial",
        "retry_predecessor": None,
    }
    store.append(
        "ordinary_admission",
        {"schema_version": 2, "owner": owner, "intent": intent},
        record_id=f"ordinary-{key}",
    )
    store.append(
        "prewrite_validation_started",
        {
            "schema_version": 2,
            "validation_id": validation_id,
            "owner_id": owner["owner_id"],
            "intent_id": intent["intent_id"],
            "epoch": epoch,
            "binding_digest": intent["binding_digest"],
            "invocation_mode": "initial",
        },
        record_id=validation_id,
    )
    store.append(
        "write_started",
        {
            "schema_version": 2,
            "validation_id": validation_id,
            "attempt": attempt,
            "validation_epoch": epoch,
            "revalidation_digest": response_outcome_store.digest(epoch),
            "effect_assessment": "unknown",
            "post_write_drift_assessment": {
                "state": "unknown",
                "evidence": "test write boundary",
            },
        },
        record_id=f"write-started-{key}",
    )
    return intent, attempt


class ResponseOutcomeStoreTests(unittest.TestCase):
    def environment(self, root: Path):
        state_path = root / "provider.json"
        state_path.write_text(
            json.dumps(
                {
                    "actor": "ivan",
                    "next_id": 900,
                    "graphql": json.loads(TYPED_FIXTURE.read_text(encoding="utf-8")),
                }
            ),
            encoding="utf-8",
        )
        fake = TEST_DIR / "fixtures/fake_gh.py"
        transport = github_response_provider.GhJsonTransport(
            [sys.executable, str(fake), str(state_path)]
        )
        epochs = github_response_provider.TypedEpochAdapter(transport)
        runtime = response_runtime.ResponseRuntime(
            state_directory=root / "bundle",
            epoch_adapter=epochs,
            inline_adapter=github_response_provider.InlineReplyAdapter(transport),
            conversation_adapter=github_response_provider.PullRequestConversationAdapter(
                transport
            ),
        )
        epoch = epochs.acquire("base-owner/base-repo", 7)
        return state_path, epochs, runtime, epoch

    def test_restart_accepts_one_legacy_owner_but_rejects_rename_split_history(self):
        def legacy_admission(admission_epoch, key):
            source = admission_epoch["sources"][0]
            legacy_identity = response_outcome_store.digest(
                {
                    "provider_host": "github.com",
                    "repository": admission_epoch["repository"],
                    "pull_request": {
                        "number": admission_epoch["pull_request"]["number"],
                        "database_id": admission_epoch["pull_request"]["database_id"],
                        "node_id": admission_epoch["pull_request"]["node_id"],
                    },
                    "source_kind": source["kind"],
                    "source_identity": source["provider_identity"],
                }
            )
            legacy_scope = response_outcome_store.digest(
                {
                    "source_identity_digest": legacy_identity,
                    "source_revision_identity": source["source_revision_identity"],
                }
            )
            owner = response_runtime._owner(admission_epoch, source, None)
            owner.update(
                owner_id=f"owner-{legacy_scope}",
                source_identity_digest=legacy_identity,
                source_scope_digest=legacy_scope,
            )
            proposal = response_runtime._proposal(
                make_intent(admission_epoch, source, key), b"Done"
            )
            intent = response_runtime._intent_record(proposal, owner)
            return {
                "record_kind": "ordinary_admission",
                "record_id": f"ordinary-{key}",
                "payload": {"schema_version": 2, "owner": owner, "intent": intent},
            }

        with tempfile.TemporaryDirectory() as temporary:
            _, _, runtime, epoch = self.environment(Path(temporary))
            original = legacy_admission(epoch, "before-rename")
            with runtime.store.locked(exclusive=True):
                runtime.store.append(
                    original["record_kind"],
                    original["payload"],
                    record_id=original["record_id"],
                )
            restarted = response_outcome_store.ResponseOutcomeStore(
                runtime.store.directory
            )
            accepted = restarted.semantic_history()
            self.assertEqual(len(accepted["owners"]), 1)

            renamed = copy.deepcopy(epoch)
            renamed["repository"].update(
                name_with_owner="renamed-owner/renamed-repo",
                owner_login="renamed-owner",
            )
            renamed["pull_request"].update(
                permalink="https://github.com/renamed-owner/renamed-repo/pull/7",
                head_repository="renamed-owner/renamed-repo",
            )
            material = dict(renamed)
            material.pop("epoch_id")
            renamed["epoch_id"] = response_outcome_store.digest(material)
            duplicate = legacy_admission(renamed, "after-rename")
            self.raw_append(
                runtime.store,
                duplicate["record_kind"],
                duplicate["payload"],
                duplicate["record_id"],
            )

            with self.assertRaisesRegex(
                response_outcome_store.OutcomeStoreError,
                "owner or source scope has multiple creators",
            ):
                restarted.semantic_history()

    @staticmethod
    def raw_append(store, record_kind, payload, record_id="injected-invalid"):
        records = store._envelope_records()
        sequence = records[-1]["sequence"] + 1 if records else 1
        prior = records[-1]["record_digest"] if records else None
        record = {
            "schema_version": 2,
            "sequence": sequence,
            "record_kind": record_kind,
            "record_id": record_id,
            "prior_record_digest": prior,
            "payload": payload,
            "payload_digest": response_outcome_store.digest(payload),
        }
        data = response_outcome_store.canonical_bytes(record)
        record_digest = hashlib.sha256(data).hexdigest()
        path = store.records_directory / f"{sequence:020d}-{record_digest}.json"
        path.write_bytes(data)
        path.chmod(0o400)
        return path

    def assert_wrong_reference_rejected(self, records, record_index, mutate):
        malformed = copy.deepcopy(records[: record_index + 1])
        mutate(malformed[-1]["payload"])
        with self.assertRaisesRegex(
            response_outcome_store.OutcomeStoreError,
            f"invalid-response-outcome-bundle.*{malformed[-1]['record_id']}",
        ):
            response_outcome_store.fold_semantic_history(malformed)

    def test_restart_reads_the_same_complete_semantic_transitions(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, _, runtime, epoch = self.environment(Path(temporary))
            outcome = runtime.invoke(make_intent(epoch, epoch["sources"][0]), b"Done")
            restarted = response_outcome_store.ResponseOutcomeStore(
                runtime.store.directory
            )
            with restarted.locked(exclusive=False):
                records = restarted.records()
                records_before_fold = copy.deepcopy(records)
                history = restarted.semantic_history()
            self.assertEqual(
                [item["record_kind"] for item in records],
                [
                    "ordinary_admission",
                    "prewrite_validation_started",
                    "write_started",
                    "attempt_resolution",
                ],
            )
            self.assertEqual(list(history["outcomes"]), [outcome["outcome_id"]])
            self.assertTrue(
                all(item["path"].stat().st_mode & 0o777 == 0o400 for item in records)
            )
            response_outcome_store.fold_semantic_history(records)
            self.assertEqual(records, records_before_fold)
            with runtime.store.locked(exclusive=False):
                self.assertEqual(runtime.store.staging_remnants(), [])

    def test_staging_remnants_are_reported_but_never_folded_as_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, _, runtime, _ = self.environment(Path(temporary))
            with runtime.store.locked(exclusive=True):
                remnant = runtime.store.staging_directory / "interrupted.tmp"
                remnant.write_bytes(b"partial")
                self.assertIn("interrupted.tmp", runtime.store.staging_remnants())
                self.assertEqual(runtime.store.records(), [])

    def test_staging_cleanup_failure_keeps_committed_append_successful(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, _, runtime, epoch = self.environment(Path(temporary))

            def inject(step, _context):
                if step == "staging_unlink":
                    raise OSError("injected staging cleanup failure")

            runtime.store = response_outcome_store.ResponseOutcomeStore(
                runtime.store.directory, fault_injector=inject
            )
            outcome = runtime.invoke(make_intent(epoch, epoch["sources"][0]), b"Done")

            self.assertEqual(outcome["status"], "confirmed_success")
            with runtime.store.locked(exclusive=False):
                self.assertTrue(runtime.store.records())
                self.assertTrue(runtime.store.staging_remnants())

    def test_malformed_committed_record_blocks_without_repair(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, _, runtime, epoch = self.environment(Path(temporary))
            runtime.invoke(make_intent(epoch, epoch["sources"][0]), b"Done")
            committed = runtime.store.records()[-1]["path"]
            committed.chmod(0o600)
            committed.write_bytes(b"{}")
            before = committed.read_bytes()
            restarted = response_outcome_store.ResponseOutcomeStore(
                runtime.store.directory
            )
            with (
                self.assertRaisesRegex(
                    response_outcome_store.OutcomeStoreError,
                    "invalid-response-outcome-bundle",
                ),
                restarted.locked(exclusive=False),
            ):
                pass
            self.assertEqual(committed.read_bytes(), before)

    def test_every_record_kind_is_semantically_validated(self):
        self.assertEqual(
            set(response_outcome_store.RECORD_VALIDATORS),
            response_outcome_store.RECORD_KINDS,
        )
        for record_kind in sorted(response_outcome_store.RECORD_KINDS):
            with (
                self.subTest(record_kind=record_kind),
                tempfile.TemporaryDirectory() as temporary,
            ):
                store = response_outcome_store.ResponseOutcomeStore(temporary)
                with store.locked(exclusive=True):
                    self.raw_append(store, record_kind, {"schema_version": 2})
                    with self.assertRaisesRegex(
                        response_outcome_store.OutcomeStoreError,
                        "invalid-response-outcome-bundle",
                    ):
                        store.semantic_history()

    def test_committed_contradictory_pagination_blocks_restart_and_provider_use(self):
        with tempfile.TemporaryDirectory() as temporary:
            state_path, _, runtime, epoch = self.environment(Path(temporary))
            malformed_input = copy.deepcopy(epoch)
            proposal = response_runtime._proposal(
                make_intent(
                    malformed_input,
                    malformed_input["sources"][0],
                    "malformed-paging",
                ),
                b"Done",
            )
            owner = response_runtime._owner(
                malformed_input, malformed_input["sources"][0], None
            )
            intent = response_runtime._intent_record(proposal, owner)
            malformed_epoch = intent["binding"]["admission_epoch"]
            pages = malformed_epoch["pagination_evidence"]["collections"]["threads"][
                "pages"
            ]
            pages[0]["has_next_page"] = True
            pages[0]["end_cursor"] = "cursor-1"
            pages.append(
                {
                    **copy.deepcopy(pages[0]),
                    "page_index": 1,
                    "request_cursor": "wrong-request-cursor",
                    "has_next_page": False,
                    "end_cursor": None,
                }
            )
            collection = malformed_epoch["pagination_evidence"]["collections"][
                "threads"
            ]
            collection["node_count"] = sum(
                page["node_count"] for page in collection["pages"]
            )
            epoch_material = dict(malformed_epoch)
            epoch_material.pop("epoch_id")
            malformed_epoch["epoch_id"] = response_outcome_store.digest(epoch_material)
            intent["binding_digest"] = response_outcome_store.digest(intent["binding"])
            with runtime.store.locked(exclusive=True):
                self.raw_append(
                    runtime.store,
                    "ordinary_admission",
                    {"schema_version": 2, "owner": owner, "intent": intent},
                    record_id="malformed-pagination",
                )
            calls_before = len(json.loads(state_path.read_text())["calls"])
            restarted = response_runtime.ResponseRuntime(
                state_directory=runtime.store.directory,
                epoch_adapter=runtime.epoch_adapter,
                inline_adapter=runtime.inline_adapter,
                conversation_adapter=runtime.conversation_adapter,
            )

            with self.assertRaisesRegex(
                response_outcome_store.OutcomeStoreError,
                "invalid-response-outcome-bundle.*malformed-pagination",
            ):
                restarted.invoke(make_intent(epoch, epoch["sources"][0]), b"Done")

            self.assertEqual(
                len(json.loads(state_path.read_text())["calls"]), calls_before
            )

    def test_envelope_valid_dangling_reference_blocks_restart_and_provider_use(self):
        with tempfile.TemporaryDirectory() as temporary:
            state_path, _, runtime, epoch = self.environment(Path(temporary))
            with runtime.store.locked(exclusive=True):
                self.raw_append(
                    runtime.store,
                    "carry_forward",
                    {
                        "schema_version": 2,
                        "owner_id": "missing-owner",
                        "intent_id": "missing-intent",
                        "from_epoch_id": epoch["epoch_id"],
                        "to_epoch": epoch,
                        "binding_digest": "0" * 64,
                        "independence_evidence": {
                            "evidence_id": "independent-1",
                            "assessment": "unchanged",
                        },
                    },
                )
            calls_before = len(json.loads(state_path.read_text())["calls"])
            restarted = response_runtime.ResponseRuntime(
                state_directory=runtime.store.directory,
                epoch_adapter=runtime.epoch_adapter,
                inline_adapter=runtime.inline_adapter,
                conversation_adapter=runtime.conversation_adapter,
            )
            with self.assertRaisesRegex(
                response_outcome_store.OutcomeStoreError,
                "invalid-response-outcome-bundle",
            ):
                restarted.invoke(make_intent(epoch, epoch["sources"][0]), b"Done")
            calls_after = len(json.loads(state_path.read_text())["calls"])
            self.assertEqual(calls_after, calls_before)

    def test_envelope_valid_forged_proven_absence_blocks_restart_and_provider_use(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            state_path, _, runtime, epoch = self.environment(Path(temporary))
            endpoint = "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state.setdefault("queued", {})[endpoint] = [
                {"returncode": 1, "stderr": "connection reset"}
            ]
            state_path.write_text(json.dumps(state), encoding="utf-8")
            intent = make_intent(epoch, epoch["sources"][0], "forged-absence")
            unknown = runtime.invoke(intent, b"Done")
            self.assertEqual(unknown["status"], "unknown")

            with runtime.store.locked(exclusive=True):
                history = runtime.store.semantic_history()
                admitted = history["intents"][history["keys"]["forged-absence"]]
                reconciliation_id = "forged-proven-absence"
                runtime.store.append(
                    "reconciliation_started",
                    {
                        "schema_version": 2,
                        "reconciliation_id": reconciliation_id,
                        "owner_id": admitted["owner_id"],
                        "intent_id": admitted["intent_id"],
                        "attempt_id": unknown["attempt_id"],
                        "intent_key": admitted["intent_key"],
                        "binding_digest": admitted["binding_digest"],
                        "prior_reconciliation_id": None,
                        "supersedes_incomplete_reconciliation_id": None,
                        "candidate_reservation": None,
                    },
                    record_id=reconciliation_id,
                )
                self.raw_append(
                    runtime.store,
                    "reconciliation_resolution",
                    {
                        "schema_version": 2,
                        "reconciliation_id": reconciliation_id,
                        "attempt_id": unknown["attempt_id"],
                        "owner_id": admitted["owner_id"],
                        "intent_id": admitted["intent_id"],
                        "result": "proven_absent_retry_eligible",
                        "outcome": None,
                        "identity_observations": [],
                        "identity_claim": None,
                        "absence_evidence": {
                            "conclusive_no_write": True,
                            "evidence_id": "authored-no-write-assertion",
                        },
                    },
                    record_id="forged-proven-absence-resolution",
                )

            calls_before = len(
                json.loads(state_path.read_text(encoding="utf-8"))["calls"]
            )
            restarted = response_runtime.ResponseRuntime(
                state_directory=runtime.store.directory,
                epoch_adapter=runtime.epoch_adapter,
                inline_adapter=runtime.inline_adapter,
                conversation_adapter=runtime.conversation_adapter,
            )
            with self.assertRaisesRegex(
                response_outcome_store.OutcomeStoreError,
                "invalid-response-outcome-bundle.*forged-proven-absence-resolution",
            ):
                restarted.invoke(intent, b"Done")
            self.assertEqual(
                len(json.loads(state_path.read_text(encoding="utf-8"))["calls"]),
                calls_before,
            )

    def test_old_proven_absence_retry_predecessor_variant_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            state_path, _, runtime, epoch = self.environment(Path(temporary))
            endpoint = "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state.setdefault("queued", {})[endpoint] = [
                {"returncode": 1, "stderr": "HTTP 409"}
            ]
            state_path.write_text(json.dumps(state), encoding="utf-8")
            intent = make_intent(epoch, epoch["sources"][0], "known-failure")
            failed = runtime.invoke(intent, b"Done")
            runtime.invoke(intent, b"Done")
            records = copy.deepcopy(runtime.store.records())
            retry_record = [
                record for record in records if record["record_kind"] == "write_started"
            ][-1]
            retry_record["payload"]["attempt"]["retry_predecessor"] = {
                "kind": "proven_absent_reconciliation",
                "reconciliation_id": "retired-reconciliation",
                "attempt_id": failed["attempt_id"],
            }

            with self.assertRaisesRegex(
                response_outcome_store.OutcomeStoreError,
                "invalid-response-outcome-bundle: retry attempt predecessor "
                "shape is contradictory",
            ):
                response_outcome_store.fold_semantic_history(records)

    def test_well_shaped_wrong_references_are_rejected_for_each_record_kind(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, _, runtime, epoch = self.environment(Path(temporary))
            first = runtime.invoke(
                make_intent(epoch, epoch["sources"][0], "first"), b"Done"
            )
            second = runtime.invoke(
                make_intent(epoch, epoch["sources"][1], "second"), b"Done"
            )
            follow = make_intent(epoch, epoch["sources"][0], "follow", b"More")
            follow["intent_kind"] = "follow_up"
            follow["predecessor_outcome_id"] = first["outcome_id"]
            runtime.invoke(follow, b"More")
            records = runtime.store.records()
            history = runtime.store.semantic_history()
            first_intent = history["intents"][history["keys"]["first"]]
            second_intent = history["intents"][history["keys"]["second"]]

            ordinary_index = next(
                index
                for index, record in enumerate(records)
                if record["record_kind"] == "ordinary_admission"
                and record["payload"]["intent"]["intent_key"] == "second"
            )

            def wrong_ordinary_owner(payload):
                intent = payload["intent"]
                intent["owner_id"] = first_intent["owner_id"]
                intent["binding"]["owner_id"] = first_intent["owner_id"]
                intent["binding"]["source_scope_digest"] = first_intent["binding"][
                    "source_scope_digest"
                ]
                intent["binding_digest"] = response_outcome_store.digest(
                    intent["binding"]
                )

            self.assert_wrong_reference_rejected(
                records, ordinary_index, wrong_ordinary_owner
            )

            follow_index = next(
                index
                for index, record in enumerate(records)
                if record["record_kind"] == "follow_up_admission"
            )

            def wrong_follow_up(payload):
                payload["predecessor_outcome_id"] = second["outcome_id"]
                payload["intent"]["binding"]["predecessor_outcome_id"] = second[
                    "outcome_id"
                ]
                payload["intent"]["binding_digest"] = response_outcome_store.digest(
                    payload["intent"]["binding"]
                )

            self.assert_wrong_reference_rejected(records, follow_index, wrong_follow_up)

            for kind, mutate in (
                (
                    "prewrite_validation_started",
                    lambda payload: payload.update(owner_id=first_intent["owner_id"]),
                ),
                (
                    "write_started",
                    lambda payload: payload["attempt"].update(
                        binding_digest=first_intent["binding_digest"]
                    ),
                ),
                (
                    "attempt_resolution",
                    lambda payload: payload.update(owner_id=first_intent["owner_id"]),
                ),
            ):
                index = next(
                    index
                    for index, record in enumerate(records)
                    if record["record_kind"] == kind
                    and (
                        record["payload"].get("intent_id") == second_intent["intent_id"]
                        or record["payload"].get("attempt", {}).get("intent_id")
                        == second_intent["intent_id"]
                    )
                )
                self.assert_wrong_reference_rejected(records, index, mutate)

        with tempfile.TemporaryDirectory() as temporary:
            _, _, runtime, epoch = self.environment(Path(temporary))
            runtime.invoke(make_intent(epoch, epoch["sources"][0], "other"), b"Done")
            history = runtime.store.semantic_history()
            other_intent = history["intents"][history["keys"]["other"]]
            proposal = response_runtime._proposal(
                make_intent(epoch, epoch["sources"][1], "pending"), b"Done"
            )
            owner = response_runtime._owner(epoch, epoch["sources"][1], None)
            pending = response_runtime._intent_record(proposal, owner)
            with runtime.store.locked(exclusive=True):
                runtime.store.append(
                    "ordinary_admission",
                    {"schema_version": 2, "owner": owner, "intent": pending},
                    record_id="ordinary-pending",
                )
                fresh = copy.deepcopy(epoch)
                fresh["acquisition_end_observation"]["monotonic_ns"] += 1
                material = dict(fresh)
                material.pop("epoch_id")
                fresh["epoch_id"] = response_outcome_store.digest(material)
                runtime.store.append(
                    "carry_forward",
                    {
                        "schema_version": 2,
                        "owner_id": pending["owner_id"],
                        "intent_id": pending["intent_id"],
                        "from_epoch_id": epoch["epoch_id"],
                        "to_epoch": fresh,
                        "binding_digest": pending["binding_digest"],
                        "independence_evidence": {
                            "evidence_id": "unchanged-1",
                            "assessment": "unchanged",
                        },
                    },
                    record_id="carry-pending",
                )
            records = runtime.store.records()
            carry_index = next(
                index
                for index, record in enumerate(records)
                if record["record_id"] == "carry-pending"
            )
            self.assert_wrong_reference_rejected(
                records,
                carry_index,
                lambda payload: payload.update(owner_id=other_intent["owner_id"]),
            )

        with tempfile.TemporaryDirectory() as temporary:
            state_path, _, runtime, epoch = self.environment(Path(temporary))
            runtime.invoke(make_intent(epoch, epoch["sources"][1], "other"), b"Done")
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["graphql"]["data"]["repository"]["pullRequest"]["headRefOid"] = (
                "fresh-head"
            )
            state_path.write_text(json.dumps(state), encoding="utf-8")
            runtime.invoke(make_intent(epoch, epoch["sources"][0], "stale"), b"Done")
            history = runtime.store.semantic_history()
            other_intent = history["intents"][history["keys"]["other"]]
            basis = runtime.prepare_replacement("stale")
            replacement = make_replacement_intent(basis, "replacement")
            runtime.invoke(replacement, b"Done")
            records = runtime.store.records()
            invalidation_index = next(
                index
                for index, record in enumerate(records)
                if record["record_kind"] == "prewrite_invalidated"
            )
            self.assert_wrong_reference_rejected(
                records,
                invalidation_index,
                lambda payload: payload.update(owner_id=other_intent["owner_id"]),
            )
            replacement_index = next(
                index
                for index, record in enumerate(records)
                if record["record_kind"] == "replacement_transition"
            )
            self.assert_wrong_reference_rejected(
                records,
                replacement_index,
                lambda payload: payload.update(
                    predecessor_owner_id=other_intent["owner_id"]
                ),
            )

        with tempfile.TemporaryDirectory() as temporary:
            state_path, _, runtime, epoch = self.environment(Path(temporary))
            runtime.invoke(make_intent(epoch, epoch["sources"][1], "other"), b"Done")
            state = json.loads(state_path.read_text(encoding="utf-8"))
            endpoint = "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
            state.setdefault("queued", {})[endpoint] = [
                {"returncode": 1, "stderr": "connection reset"}
            ]
            state_path.write_text(json.dumps(state), encoding="utf-8")
            runtime.invoke(make_intent(epoch, epoch["sources"][0], "unknown"), b"Done")
            runtime.reconcile("unknown")
            history = runtime.store.semantic_history()
            other_intent = history["intents"][history["keys"]["other"]]
            records = runtime.store.records()
            for kind in ("reconciliation_started", "reconciliation_resolution"):
                index = next(
                    index
                    for index, record in enumerate(records)
                    if record["record_kind"] == kind
                )
                self.assert_wrong_reference_rejected(
                    records,
                    index,
                    lambda payload, owner_id=other_intent["owner_id"]: payload.update(
                        owner_id=owner_id
                    ),
                )

    def test_wrong_earlier_attempt_reconciliation_invalidates_restart_before_provider(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            state_path, _, runtime, epoch = self.environment(Path(temporary))
            endpoint = "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state.setdefault("queued", {})[endpoint] = [
                {"returncode": 1, "stderr": "HTTP 409"},
                {"returncode": 1, "stderr": "connection reset"},
            ]
            state_path.write_text(json.dumps(state), encoding="utf-8")
            first = runtime.invoke(make_intent(epoch, epoch["sources"][0]), b"Done")
            second = runtime.invoke(make_intent(epoch, epoch["sources"][0]), b"Done")
            self.assertEqual(first["status"], "confirmed_failure")
            self.assertEqual(second["status"], "unknown")
            history = runtime.store.semantic_history()
            intent = history["intents"][history["keys"]["intent-1"]]
            attempts = sorted(
                (
                    item
                    for item in history["attempts"].values()
                    if item["intent_id"] == intent["intent_id"]
                ),
                key=lambda item: item["ordinal"],
            )
            wrong = {
                "schema_version": 2,
                "reconciliation_id": "wrong-attempt-round",
                "owner_id": intent["owner_id"],
                "intent_id": intent["intent_id"],
                "attempt_id": attempts[0]["attempt_id"],
                "intent_key": intent["intent_key"],
                "binding_digest": intent["binding_digest"],
                "prior_reconciliation_id": None,
                "supersedes_incomplete_reconciliation_id": None,
                "candidate_reservation": None,
            }
            path = self.raw_append(
                runtime.store,
                "reconciliation_started",
                wrong,
                record_id="wrong-attempt-round",
            )
            retained = path.read_bytes()
            calls_before = json.loads(state_path.read_text(encoding="utf-8"))["calls"]

            with self.assertRaisesRegex(
                response_outcome_store.OutcomeStoreError,
                "invalid-response-outcome-bundle",
            ):
                runtime.reconcile("intent-1")

            self.assertEqual(path.read_bytes(), retained)
            self.assertEqual(
                json.loads(state_path.read_text(encoding="utf-8"))["calls"],
                calls_before,
            )

    def test_conflicting_reservation_invalidates_restart_before_reread(self):
        with tempfile.TemporaryDirectory() as temporary:
            state_path, _, runtime, epoch = self.environment(Path(temporary))
            with runtime.store.locked(exclusive=True):
                first_intent, first_attempt = append_unknown_attempt(
                    runtime.store, epoch, epoch["sources"][0], "first"
                )
                second_intent, second_attempt = append_unknown_attempt(
                    runtime.store, epoch, epoch["sources"][1], "second"
                )
                candidate = {
                    "object_kind": "PullRequestReviewComment",
                    "database_id": 991,
                    "node_id": "RESPONSE_991",
                }
                first_round = {
                    "schema_version": 2,
                    "reconciliation_id": "first-round",
                    "owner_id": first_intent["owner_id"],
                    "intent_id": first_intent["intent_id"],
                    "attempt_id": first_attempt["attempt_id"],
                    "intent_key": first_intent["intent_key"],
                    "binding_digest": first_intent["binding_digest"],
                    "prior_reconciliation_id": None,
                    "supersedes_incomplete_reconciliation_id": None,
                    "candidate_reservation": candidate,
                }
                runtime.store.append(
                    "reconciliation_started", first_round, record_id="first-round"
                )
                second_round = {
                    **first_round,
                    "reconciliation_id": "second-round",
                    "owner_id": second_intent["owner_id"],
                    "intent_id": second_intent["intent_id"],
                    "attempt_id": second_attempt["attempt_id"],
                    "intent_key": second_intent["intent_key"],
                    "binding_digest": second_intent["binding_digest"],
                }
                path = self.raw_append(
                    runtime.store,
                    "reconciliation_started",
                    second_round,
                    record_id="second-round",
                )
            retained = path.read_bytes()
            calls_before = json.loads(state_path.read_text(encoding="utf-8"))["calls"]

            with self.assertRaisesRegex(
                response_outcome_store.OutcomeStoreError,
                "invalid-response-outcome-bundle",
            ):
                runtime.read_outcomes()

            self.assertEqual(path.read_bytes(), retained)
            self.assertEqual(
                json.loads(state_path.read_text(encoding="utf-8"))["calls"],
                calls_before,
            )

    def test_reconciliation_observations_cannot_cross_another_intent_lifecycle(self):
        with tempfile.TemporaryDirectory() as temporary:
            state_path, _, runtime, epoch = self.environment(Path(temporary))
            endpoint = "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state.setdefault("queued", {})[endpoint] = [
                {"returncode": 1, "stderr": "connection reset"},
                {"returncode": 1, "stderr": "connection reset"},
            ]
            state_path.write_text(json.dumps(state), encoding="utf-8")
            first = runtime.invoke(
                make_intent(epoch, epoch["sources"][0], "first", b"Same"), b"Same"
            )
            runtime.invoke(
                make_intent(epoch, epoch["sources"][1], "second", b"Same"), b"Same"
            )
            history = runtime.store.semantic_history()
            first_intent = history["intents"][history["keys"]["first"]]
            identity = {
                "object_kind": "PullRequestReviewComment",
                "database_id": 950,
                "node_id": "RESPONSE_node_950",
            }
            with runtime.store.locked(exclusive=True):
                runtime.store.append(
                    "reconciliation_started",
                    {
                        "schema_version": 2,
                        "reconciliation_id": "first-reserves-950",
                        "owner_id": first_intent["owner_id"],
                        "intent_id": first_intent["intent_id"],
                        "attempt_id": first["attempt_id"],
                        "intent_key": "first",
                        "binding_digest": first_intent["binding_digest"],
                        "prior_reconciliation_id": None,
                        "supersedes_incomplete_reconciliation_id": None,
                        "candidate_reservation": identity,
                    },
                    record_id="first-reserves-950",
                )
            runtime.reconcile("second")
            records = copy.deepcopy(runtime.store.records())
            resolution = next(
                record
                for record in records
                if record["record_kind"] == "reconciliation_resolution"
                and record["payload"]["intent_id"] == history["keys"]["second"]
            )
            resolution["payload"]["identity_observations"] = [identity]
            fold = response_outcome_store.SemanticHistoryFold()

            with self.assertRaisesRegex(
                response_outcome_store.OutcomeStoreError,
                "belongs to another intent lifecycle",
            ):
                fold.fold(records)

            typed = ("PullRequestReviewComment", 950, "RESPONSE_node_950")
            self.assertEqual(
                fold.state["identity_reservations"][typed]["intent_id"],
                first_intent["intent_id"],
            )
            self.assertNotIn(
                history["keys"]["second"],
                fold.state["identity_observers"].get(typed, set()),
            )
            second_attempt = fold.state["current_attempt_by_intent"][
                history["keys"]["second"]
            ]
            self.assertEqual(
                fold.state["effective_outcome_by_attempt"][second_attempt],
                history["effective_outcome_by_attempt"][second_attempt],
            )

    def test_reservation_supersession_and_unknown_conversion_survive_restart(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, _, runtime, epoch = self.environment(Path(temporary))
            with runtime.store.locked(exclusive=True):
                intent, attempt = append_unknown_attempt(
                    runtime.store, epoch, epoch["sources"][0], "reserved"
                )
                first = {
                    "schema_version": 2,
                    "reconciliation_id": "round-1",
                    "owner_id": intent["owner_id"],
                    "intent_id": intent["intent_id"],
                    "attempt_id": attempt["attempt_id"],
                    "intent_key": intent["intent_key"],
                    "binding_digest": intent["binding_digest"],
                    "prior_reconciliation_id": None,
                    "supersedes_incomplete_reconciliation_id": None,
                    "candidate_reservation": {
                        "object_kind": "PullRequestReviewComment",
                        "database_id": 991,
                        "node_id": "RESPONSE_991",
                    },
                }
                runtime.store.append(
                    "reconciliation_started", first, record_id="round-1"
                )
                second = {
                    **first,
                    "reconciliation_id": "round-2",
                    "prior_reconciliation_id": "round-1",
                    "supersedes_incomplete_reconciliation_id": "round-1",
                }
                runtime.store.append(
                    "reconciliation_started", second, record_id="round-2"
                )
                third = {
                    **second,
                    "reconciliation_id": "round-3",
                    "prior_reconciliation_id": "round-2",
                    "supersedes_incomplete_reconciliation_id": "round-2",
                    "candidate_reservation": {
                        "object_kind": "PullRequestReviewComment",
                        "database_id": 992,
                        "node_id": "RESPONSE_992",
                    },
                }
                runtime.store.append(
                    "reconciliation_started", third, record_id="round-3"
                )
            before = response_outcome_store.ResponseOutcomeStore(
                runtime.store.directory
            ).semantic_history()
            first_identity = ("PullRequestReviewComment", 991, "RESPONSE_991")
            second_identity = ("PullRequestReviewComment", 992, "RESPONSE_992")
            self.assertEqual(
                before["reconciliations"]["round-1"]["state"], "superseded"
            )
            self.assertEqual(
                before["reconciliations"]["round-2"]["state"], "superseded"
            )
            self.assertIn(first_identity, before["identity_observers"])
            self.assertEqual(
                before["identity_reservations"][second_identity]["reconciliation_id"],
                "round-3",
            )

            outcome = runtime.reconcile("reserved")
            after = response_outcome_store.ResponseOutcomeStore(
                runtime.store.directory
            ).semantic_history()
            self.assertEqual(outcome["status"], "unknown")
            self.assertNotIn(second_identity, after["identity_reservations"])
            self.assertIn(
                intent["intent_id"], after["identity_observers"][second_identity]
            )

    def test_correlation_uses_exact_provider_observable_projection(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, _, runtime, epoch = self.environment(Path(temporary))
            with runtime.store.locked(exclusive=True):
                first, _ = append_unknown_attempt(
                    runtime.store, epoch, epoch["sources"][0], "first"
                )
                second, _ = append_unknown_attempt(
                    runtime.store, epoch, epoch["sources"][1], "second"
                )
            history = runtime.store.semantic_history()
            self.assertEqual(
                history["reconciliation_decisions"][first["intent_id"]]["kind"],
                "ambiguous_effective_unknown",
            )
            mutable = copy.deepcopy(history)
            second_binding = mutable["intents"][second["intent_id"]]["binding"]
            second_binding["target"]["repository"]["name_with_owner"] = "renamed/repo"
            second_binding["target"]["repository"]["owner_login"] = "renamed"
            second_binding["target"]["pull_request"].update(
                {
                    "head_oid": "changed-head",
                    "base_oid": "changed-base",
                    "head_repository": "renamed/repo",
                    "permalink": "https://github.com/renamed/repo/pull/7",
                }
            )
            second_binding["admission_epoch"]["repository"] = copy.deepcopy(
                second_binding["target"]["repository"]
            )
            second_binding["admission_epoch"]["pull_request"] = copy.deepcopy(
                second_binding["target"]["pull_request"]
            )
            authority = response_identity_lifecycle.ResponseIdentityAuthority(
                lambda: mutable
            )
            self.assertEqual(
                authority.reconciliation_decision(first["intent_id"])["kind"],
                "ambiguous_effective_unknown",
            )

            variants = {
                "repository_identity": lambda binding: binding["target"]["repository"][
                    "provider_identity"
                ].update(database_id=999),
                "pull_request_identity": lambda binding: binding["target"][
                    "pull_request"
                ].update(database_id=999, node_id="PR_999", number=99),
                "operation": lambda binding: binding.update(
                    operation="create_pull_request_conversation_comment",
                    placement={"kind": "pull_request_conversation", "pr_number": 7},
                ),
                "placement": lambda binding: binding.update(
                    placement={
                        "kind": "review_thread",
                        "thread_node_id": "OTHER_THREAD",
                        "root_comment_database_id": 302,
                    }
                ),
                "actor": lambda binding: (
                    binding["expected_actor_identity"].update(login="other"),
                    binding["authority"].update(actor_login="other"),
                ),
                "body": lambda binding: binding["body"].update(
                    utf8_base64="T3RoZXI=",
                    byte_length=5,
                    sha256=hashlib.sha256(b"Other").hexdigest(),
                ),
            }
            for name, change in variants.items():
                with self.subTest(discriminator=name):
                    separated = copy.deepcopy(history)
                    change(separated["intents"][second["intent_id"]]["binding"])
                    authority = response_identity_lifecycle.ResponseIdentityAuthority(
                        lambda separated=separated: separated
                    )
                    self.assertEqual(
                        authority.reconciliation_decision(first["intent_id"])["kind"],
                        "collection_discovery_candidate",
                    )

    def test_every_cross_intent_identity_role_relation_rejects(self):
        identity_value = {
            "object_kind": "PullRequestReviewComment",
            "database_id": 950,
            "node_id": "RESPONSE_950",
        }
        identity = ("PullRequestReviewComment", 950, "RESPONSE_950")
        binding = {
            "operation": "create_inline_reply",
            "target": {},
            "placement": {},
            "expected_actor_identity": {},
            "body": {},
        }
        base = {
            "intents": {
                "intent-a": {"binding": copy.deepcopy(binding)},
                "intent-b": {"binding": copy.deepcopy(binding)},
            },
            "reconciliations": {},
            "current_attempt_by_intent": {},
            "effective_disposition_by_attempt": {},
            "effective_outcome_by_attempt": {},
            "outcomes": {},
            "identity_owners": {},
            "identity_observers": {},
            "identity_reservations": {},
        }

        def reservation(intent_id, reconciliation_id):
            return {
                "reconciliation_id": reconciliation_id,
                "attempt_id": f"attempt-{intent_id}",
                "intent_id": intent_id,
                "binding_digest": "a" * 64,
            }

        cases = []
        owner = copy.deepcopy(base)
        owner["identity_owners"][identity] = "intent-a"
        cases.extend(
            [
                (
                    "owner-observer",
                    owner,
                    "attempt_resolution",
                    {
                        "intent_id": "intent-b",
                        "identity_observations": [identity_value],
                        "identity_claim": None,
                    },
                ),
                (
                    "owner-reservation",
                    owner,
                    "reconciliation_started",
                    {
                        "intent_id": "intent-b",
                        "attempt_id": "attempt-b",
                        "binding_digest": "b" * 64,
                        "reconciliation_id": "round-b",
                        "supersedes_incomplete_reconciliation_id": None,
                        "candidate_reservation": identity_value,
                    },
                ),
            ]
        )
        observer = copy.deepcopy(base)
        observer["identity_observers"][identity] = {"intent-a"}
        cases.extend(
            [
                (
                    "observer-observer",
                    observer,
                    "attempt_resolution",
                    {
                        "intent_id": "intent-b",
                        "identity_observations": [identity_value],
                        "identity_claim": None,
                    },
                ),
                (
                    "observer-reservation",
                    observer,
                    "reconciliation_started",
                    {
                        "intent_id": "intent-b",
                        "attempt_id": "attempt-b",
                        "binding_digest": "b" * 64,
                        "reconciliation_id": "round-b",
                        "supersedes_incomplete_reconciliation_id": None,
                        "candidate_reservation": identity_value,
                    },
                ),
            ]
        )
        reserved = copy.deepcopy(base)
        reserved["identity_reservations"][identity] = reservation("intent-a", "round-a")
        cases.extend(
            [
                (
                    "reservation-observation",
                    reserved,
                    "attempt_resolution",
                    {
                        "intent_id": "intent-b",
                        "identity_observations": [identity_value],
                        "identity_claim": None,
                    },
                ),
                (
                    "reservation-claim",
                    reserved,
                    "attempt_resolution",
                    {
                        "intent_id": "intent-b",
                        "identity_observations": [identity_value],
                        "identity_claim": identity_value,
                    },
                ),
            ]
        )
        for name, state, kind, payload in cases:
            with self.subTest(relation=name):
                authority = response_identity_lifecycle.ResponseIdentityAuthority(
                    lambda state=state: state
                )
                with self.assertRaises(
                    response_identity_lifecycle.ResponseIdentityError
                ):
                    authority.apply_transition(kind, payload)

        same_intent = copy.deepcopy(base)
        same_intent["identity_owners"][identity] = "intent-a"
        authority = response_identity_lifecycle.ResponseIdentityAuthority(
            lambda: same_intent
        )
        authority.apply_transition(
            "attempt_resolution",
            {
                "intent_id": "intent-a",
                "identity_observations": [identity_value],
                "identity_claim": identity_value,
            },
        )
        same_intent["identity_reservations"].clear()
        authority.apply_transition(
            "reconciliation_started",
            {
                "intent_id": "intent-a",
                "attempt_id": "attempt-a",
                "binding_digest": "a" * 64,
                "reconciliation_id": "round-a",
                "supersedes_incomplete_reconciliation_id": None,
                "candidate_reservation": identity_value,
            },
        )
        self.assertEqual(
            authority.projection()["identity_reservations"][identity]["intent_id"],
            "intent-a",
        )

    def test_runtime_consumes_authority_projections_without_rebuilding_role_policy(
        self,
    ):
        runtime_source = (SCRIPTS / "response_runtime.py").read_text(encoding="utf-8")
        for private_role_map in (
            'history["identity_owners"]',
            'history["identity_observers"]',
            'history["identity_reservations"]',
        ):
            self.assertNotIn(private_role_map, runtime_source)
        self.assertIn('history["reconciliation_decisions"]', runtime_source)
        self.assertIn('history["known_identities"]', runtime_source)
        authority_source = (SCRIPTS / "response_identity_lifecycle.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("canonical = _canonical(value)", authority_source)
        self.assertNotIn("import hashlib", authority_source)

    def test_old_baseless_replacement_history_is_retained_and_rejected_on_restart(self):
        with tempfile.TemporaryDirectory() as temporary:
            state_path, epochs, runtime, epoch = self.environment(Path(temporary))
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["graphql"]["data"]["repository"]["pullRequest"]["headRefOid"] = (
                "replacement-head"
            )
            state_path.write_text(json.dumps(state), encoding="utf-8")
            runtime.invoke(make_intent(epoch, epoch["sources"][0], "old"), b"Done")
            history = runtime.store.semantic_history()
            predecessor = history["intents"][history["keys"]["old"]]
            owner = history["owners"][predecessor["owner_id"]]
            validation = next(iter(history["validations"].values()))
            fresh = epochs.acquire("base-owner/base-repo", 7)
            proposal = response_runtime._proposal(
                make_intent(fresh, fresh["sources"][0], "old-successor"), b"Done"
            )
            successor = response_runtime._intent_record(
                proposal, owner, replacement_of=predecessor["intent_id"]
            )
            old_payload = {
                "schema_version": 2,
                "predecessor_validation_id": validation["validation_id"],
                "predecessor_intent_id": predecessor["intent_id"],
                "predecessor_owner_id": owner["owner_id"],
                "predecessor_epoch_id": validation["epoch"]["epoch_id"],
                "terminal_state": "invalidated_unexecuted",
                "drift_evidence_id": "authored-freshness-label",
                "successor_owner": None,
                "successor_intent": successor,
            }
            path = self.raw_append(
                runtime.store,
                "replacement_transition",
                old_payload,
                record_id="old-baseless-replacement",
            )
            retained = path.read_bytes()
            calls_before = json.loads(state_path.read_text(encoding="utf-8"))["calls"]

            with self.assertRaisesRegex(
                response_outcome_store.OutcomeStoreError,
                "invalid-response-outcome-bundle",
            ):
                runtime.prepare_replacement("old")

            self.assertEqual(path.read_bytes(), retained)
            self.assertEqual(
                json.loads(state_path.read_text(encoding="utf-8"))["calls"],
                calls_before,
            )

    def test_replacement_basis_publication_faults_restart_at_whole_record_boundary(
        self,
    ):
        fault_cases = (
            ("flock", "bundle_lock"),
            ("staging_create", "replacement_basis"),
            ("staging_write_each_prefix", "replacement_basis"),
            ("staging_write", "replacement_basis"),
            ("fchmod", "replacement_basis"),
            ("file_fsync", "replacement_basis"),
            ("staging_close", "replacement_basis"),
            ("hard_link_no_replace", "replacement_basis"),
            ("hard_link", "replacement_basis"),
            ("sync_directory_open", "replacement_basis"),
            ("directory_fsync", "replacement_basis"),
            ("directory_close", "replacement_basis"),
        )
        survives = {
            "sync_directory_open",
            "directory_fsync",
            "directory_close",
        }
        for step, context in fault_cases:
            with (
                self.subTest(step=step),
                tempfile.TemporaryDirectory() as temporary,
            ):
                state_path, _, runtime, epoch = self.environment(Path(temporary))
                state = json.loads(state_path.read_text(encoding="utf-8"))
                state["graphql"]["data"]["repository"]["pullRequest"]["headRefOid"] = (
                    "replacement-head"
                )
                state_path.write_text(json.dumps(state), encoding="utf-8")
                runtime.invoke(make_intent(epoch, epoch["sources"][0], "old"), b"Done")

                def inject(
                    actual_step,
                    actual_context,
                    expected_step=step,
                    expected_context=context,
                ):
                    if (
                        actual_step == expected_step
                        and actual_context == expected_context
                    ):
                        raise OSError(f"injected {expected_step}")

                runtime.store = response_outcome_store.ResponseOutcomeStore(
                    runtime.store.directory, fault_injector=inject
                )
                writes_before = sum(
                    call["operation"] == "response_write"
                    for call in json.loads(state_path.read_text(encoding="utf-8"))[
                        "calls"
                    ]
                )
                with self.assertRaisesRegex(
                    response_outcome_store.OutcomeStoreError,
                    "storage-capability-failure",
                ):
                    runtime.prepare_replacement("old")
                runtime.store._fault_injector = None
                restarted = response_outcome_store.ResponseOutcomeStore(
                    runtime.store.directory
                )
                with restarted.locked(exclusive=False):
                    bases = restarted.read("replacement_basis")
                self.assertEqual(len(bases), 1 if step in survives else 0)
                writes_after = sum(
                    call["operation"] == "response_write"
                    for call in json.loads(state_path.read_text(encoding="utf-8"))[
                        "calls"
                    ]
                )
                self.assertEqual(writes_after, writes_before)

    def test_reconciliation_publications_restart_at_whole_record_boundaries(self):
        fault_steps = (
            "staging_create",
            "staging_write_each_prefix",
            "staging_write",
            "fchmod",
            "file_fsync",
            "staging_close",
            "hard_link_no_replace",
            "hard_link",
            "sync_directory_open",
            "directory_fsync",
            "directory_close",
        )
        survives = {
            "sync_directory_open",
            "directory_fsync",
            "directory_close",
        }
        for record_kind in ("reconciliation_started", "reconciliation_resolution"):
            for step in fault_steps:
                with (
                    self.subTest(record_kind=record_kind, step=step),
                    tempfile.TemporaryDirectory() as temporary,
                ):
                    state_path, _, runtime, epoch = self.environment(Path(temporary))
                    state = json.loads(state_path.read_text(encoding="utf-8"))
                    endpoint = (
                        "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
                    )
                    state.setdefault("queued", {})[endpoint] = [
                        {"returncode": 1, "stderr": "connection reset"}
                    ]
                    state_path.write_text(json.dumps(state), encoding="utf-8")
                    unknown = runtime.invoke(
                        make_intent(epoch, epoch["sources"][0], "unknown"),
                        b"Done",
                    )
                    self.assertEqual(unknown["status"], "unknown")

                    def inject(
                        actual_step,
                        actual_context,
                        expected_step=step,
                        expected_context=record_kind,
                    ):
                        if (
                            actual_step == expected_step
                            and actual_context == expected_context
                        ):
                            raise OSError(f"injected {expected_step}")

                    runtime.store = response_outcome_store.ResponseOutcomeStore(
                        runtime.store.directory, fault_injector=inject
                    )
                    writes_before = sum(
                        call["operation"] == "response_write"
                        for call in json.loads(state_path.read_text(encoding="utf-8"))[
                            "calls"
                        ]
                    )
                    with self.assertRaisesRegex(
                        response_outcome_store.OutcomeStoreError,
                        "storage-capability-failure",
                    ):
                        runtime.reconcile("unknown")

                    restarted = response_outcome_store.ResponseOutcomeStore(
                        runtime.store.directory
                    )
                    with restarted.locked(exclusive=False):
                        history = restarted.semantic_history()
                    rounds = list(history["reconciliations"].values())
                    if record_kind == "reconciliation_started":
                        self.assertEqual(len(rounds), 1 if step in survives else 0)
                        if rounds:
                            self.assertEqual(rounds[0]["state"], "live")
                    else:
                        self.assertEqual(len(rounds), 1)
                        self.assertEqual(
                            rounds[0]["state"],
                            "resolved" if step in survives else "live",
                        )
                    writes_after = sum(
                        call["operation"] == "response_write"
                        for call in json.loads(state_path.read_text(encoding="utf-8"))[
                            "calls"
                        ]
                    )
                    self.assertEqual(writes_after, writes_before)

    def test_atomic_replacement_faults_leave_predecessor_or_whole_successor(self):
        fault_steps = (
            "staging_create",
            "staging_write_each_prefix",
            "staging_write",
            "fchmod",
            "staging_close",
            "file_fsync",
            "hard_link_no_replace",
            "hard_link",
            "sync_directory_open",
            "directory_fsync",
            "directory_close",
        )
        for changed_revision in (False, True):
            for step in fault_steps:
                with (
                    self.subTest(changed_revision=changed_revision, step=step),
                    tempfile.TemporaryDirectory() as temporary,
                ):
                    root = Path(temporary)
                    state_path, _, runtime, epoch = self.environment(root)
                    state = json.loads(state_path.read_text())
                    state["graphql"]["data"]["repository"]["pullRequest"][
                        "headRefOid"
                    ] = "fresh-head"
                    state_path.write_text(json.dumps(state))
                    blocked = runtime.invoke(
                        make_intent(epoch, epoch["sources"][0], "old"), b"Done"
                    )
                    self.assertEqual(
                        blocked["pre_write_state"], "invalidated_unexecuted"
                    )
                    if changed_revision:
                        state = json.loads(state_path.read_text())
                        source = state["graphql"]["data"]["repository"]["pullRequest"][
                            "reviewThreads"
                        ]["nodes"][0]["comments"]["nodes"][0]
                        source.update(
                            {
                                "body": "Edited source",
                                "updatedAt": "2026-09-10T00:00:00Z",
                            }
                        )
                        state_path.write_text(json.dumps(state))
                    basis = runtime.prepare_replacement("old")
                    successor = make_replacement_intent(basis, "successor")

                    def inject(actual_step, context, expected=step):
                        if (
                            context == "replacement_transition"
                            and actual_step == expected
                        ):
                            raise OSError(f"injected {expected}")

                    runtime.store = response_outcome_store.ResponseOutcomeStore(
                        runtime.store.directory, fault_injector=inject
                    )
                    writes_before = sum(
                        call["operation"] == "response_write"
                        for call in json.loads(state_path.read_text())["calls"]
                    )
                    with self.assertRaisesRegex(
                        response_outcome_store.OutcomeStoreError,
                        "storage-capability-failure",
                    ):
                        runtime.invoke(successor, b"Done")
                    restarted = response_outcome_store.ResponseOutcomeStore(
                        runtime.store.directory
                    )
                    with restarted.locked(exclusive=False):
                        history = restarted.semantic_history()
                    successors = [
                        item
                        for item in history["intents"].values()
                        if item["intent_key"] == "successor"
                    ]
                    self.assertEqual(
                        len(successors),
                        1
                        if step
                        in {
                            "sync_directory_open",
                            "directory_fsync",
                            "directory_close",
                        }
                        else 0,
                    )
                    for owner_id in history["owners"]:
                        self.assertTrue(
                            any(
                                item["owner_id"] == owner_id
                                for item in history["intents"].values()
                            )
                        )
                    writes_after = sum(
                        call["operation"] == "response_write"
                        for call in json.loads(state_path.read_text())["calls"]
                    )
                    self.assertEqual(writes_after, writes_before)

    def test_atomic_ordinary_and_follow_up_admission_faults_never_leave_partial_intents(
        self,
    ):
        fault_steps = (
            "staging_create",
            "staging_write",
            "staging_close",
            "file_fsync",
            "hard_link",
            "directory_fsync",
        )
        for record_kind in ("ordinary_admission", "follow_up_admission"):
            for step in fault_steps:
                with (
                    self.subTest(record_kind=record_kind, step=step),
                    tempfile.TemporaryDirectory() as temporary,
                ):
                    state_path, _, runtime, epoch = self.environment(Path(temporary))
                    source = epoch["sources"][0]
                    if record_kind == "follow_up_admission":
                        first = runtime.invoke(
                            make_intent(epoch, source, "first"), b"Done"
                        )
                        intent = make_intent(epoch, source, "follow-up", b"More")
                        intent["intent_kind"] = "follow_up"
                        intent["predecessor_outcome_id"] = first["outcome_id"]
                    else:
                        intent = make_intent(epoch, source, "ordinary")

                    def inject(actual_step, context, expected=step, kind=record_kind):
                        if context == kind and actual_step == expected:
                            raise OSError(f"injected {kind} {expected}")

                    runtime.store = response_outcome_store.ResponseOutcomeStore(
                        runtime.store.directory, fault_injector=inject
                    )
                    body = b"More" if record_kind == "follow_up_admission" else b"Done"
                    with self.assertRaises(response_outcome_store.OutcomeStoreError):
                        runtime.invoke(intent, body)
                    restarted = response_outcome_store.ResponseOutcomeStore(
                        runtime.store.directory
                    )
                    with restarted.locked(exclusive=False):
                        history = restarted.semantic_history()
                    self.assertTrue(
                        all(
                            item["owner_id"] in history["owners"]
                            for item in history["intents"].values()
                        )
                    )
                    admitted = [
                        item
                        for item in history["intents"].values()
                        if item["intent_key"] == intent["intent_key"]
                    ]
                    self.assertEqual(
                        len(admitted),
                        1
                        if step == "directory_fsync"
                        else 0,
                    )
                    writes = sum(
                        call["operation"] == "response_write"
                        for call in json.loads(state_path.read_text())["calls"]
                    )
                    self.assertEqual(
                        writes, 1 if record_kind == "follow_up_admission" else 0
                    )

    def test_every_legacy_stream_shape_is_rejected_before_lock_and_preserved(self):
        shapes = (b"", b"{}\n", b'{"broken":', b'{}\n{"torn":')
        for name in response_outcome_store.LEGACY_NAMES:
            for legacy_bytes in shapes:
                with (
                    self.subTest(name=name, legacy_bytes=legacy_bytes),
                    tempfile.TemporaryDirectory() as temporary,
                ):
                    root = Path(temporary)
                    legacy = root / name
                    legacy.write_bytes(legacy_bytes)
                    before = {item.name: item.read_bytes() for item in root.iterdir()}
                    store = response_outcome_store.ResponseOutcomeStore(root)
                    with (
                        self.assertRaisesRegex(
                            response_outcome_store.OutcomeStoreError,
                            "unsupported-development-format",
                        ),
                        store.locked(exclusive=True),
                    ):
                        pass
                    self.assertEqual(
                        {item.name: item.read_bytes() for item in root.iterdir()},
                        before,
                    )
                    self.assertFalse(store.lock_path.exists())

    def test_flock_failure_is_an_explicit_capability_diagnostic(self):
        with tempfile.TemporaryDirectory() as temporary:

            def inject(step, _context):
                if step == "flock":
                    raise OSError("injected flock")

            store = response_outcome_store.ResponseOutcomeStore(
                temporary, fault_injector=inject
            )
            with (
                self.assertRaisesRegex(
                    response_outcome_store.OutcomeStoreError,
                    "storage-capability-failure.*flock",
                ),
                store.locked(exclusive=True),
            ):
                pass


if __name__ == "__main__":
    unittest.main()
