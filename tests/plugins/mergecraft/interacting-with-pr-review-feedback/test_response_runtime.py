import base64
import copy
import hashlib
import itertools
import json
import multiprocessing
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
import response_outcome_store
import response_runtime

TYPED_FIXTURE = (
    REPOSITORY
    / "tests/plugins/mergecraft/addressing-pr-review-feedback/fixtures/typed_feedback_epoch.json"
)


def make_intent(epoch, source, key="intent-1", body=b"Done"):
    operation = (
        "create_inline_reply"
        if source["kind"] == "inline_review_comment"
        else "create_pull_request_conversation_comment"
    )
    placement = (
        {
            "kind": "review_thread",
            "thread_node_id": source["thread"]["node_id"],
            "root_comment_database_id": source["thread"]["root_comment_database_id"],
        }
        if operation == "create_inline_reply"
        else {"kind": "pull_request_conversation", "pr_number": 7}
    )
    return {
        "schema_version": 1,
        "intent_key": key,
        "intent_kind": "ordinary",
        "admitted_epoch": epoch,
        "source": source,
        "operation": operation,
        "placement": placement,
        "writer": {
            "identity": "writer-evidence-1",
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "contract": "portable-github-markdown-authoring",
            "contract_version": "1",
            "field": (
                "review_thread_reply"
                if operation == "create_inline_reply"
                else "pull_request_conversation_comment"
            ),
        },
        "authority": {
            "decision": "authorized",
            "evidence_id": "authority-1",
            "actor_login": "ivan",
        },
        "classification": {
            "result": "human_feedback",
            "evidence_id": "classification-1",
        },
        "adjudication": {"disposition": "respond", "evidence_id": "adjudication-1"},
        "independence_evidence": {
            "availability": "not_applicable",
            "reason": "initial_admission",
        },
    }


def response_body(source):
    if source["kind"] == "inline_review_comment":
        return b"Done"
    return f"{source['permalink']}\n\nDone".encode()


def rename_repository(state):
    repository = state["graphql"]["data"]["repository"]
    repository["nameWithOwner"] = "renamed-owner/renamed-repo"
    repository["owner"]["login"] = "renamed-owner"
    pull_request = repository["pullRequest"]
    pull_request["url"] = "https://github.com/renamed-owner/renamed-repo/pull/7"
    pull_request["headRepository"]["nameWithOwner"] = (
        "renamed-owner/renamed-repo"
    )
    pull_request["headRepository"]["owner"]["login"] = "renamed-owner"


def finalize_epoch(epoch):
    epoch["identity_registry_digest"] = response_outcome_store.digest(
        epoch["identity_registry"]
    )
    epoch["observation_digest"] = response_outcome_store.digest(epoch["observations"])
    material = dict(epoch)
    material.pop("epoch_id")
    epoch["epoch_id"] = response_outcome_store.digest(material)
    return epoch


def exact_artifact(value):
    raw = response_outcome_store.canonical_bytes(value)
    return {
        "canonical_utf8_base64": base64.b64encode(raw).decode("ascii"),
        "byte_length": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def decoded_artifact(wrapper):
    return json.loads(base64.b64decode(wrapper["canonical_utf8_base64"]))


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
    writer_result = exact_artifact(
        {
            **common,
            "artifact_kind": "writer_result",
            "identity": "replacement-writer",
            "contract": "portable-github-markdown-authoring",
            "contract_version": "1",
            "field": (
                "review_thread_reply"
                if basis["operation"] == "create_inline_reply"
                else "pull_request_conversation_comment"
            ),
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
        "writer_result_artifact": writer_result,
    }


def concurrent_invoke(state_path, ledger_path, intent, body, queue):
    fake = TEST_DIR / "fixtures/fake_gh.py"
    transport = github_response_provider.GhJsonTransport(
        [sys.executable, str(fake), str(state_path)]
    )
    runtime = response_runtime.ResponseRuntime(
        state_directory=ledger_path,
        epoch_adapter=github_response_provider.TypedEpochAdapter(transport),
        inline_adapter=github_response_provider.InlineReplyAdapter(transport),
        conversation_adapter=github_response_provider.PullRequestConversationAdapter(
            transport
        ),
    )
    try:
        queue.put(("ok", runtime.invoke(intent, body)["status"]))
    except Exception as error:  # noqa: BLE001  # pragma: no cover
        queue.put(("error", repr(error)))


class ResponseRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.provider_state = root / "provider.json"
        page = json.loads(TYPED_FIXTURE.read_text(encoding="utf-8"))
        self.provider_state.write_text(
            json.dumps({"actor": "ivan", "next_id": 900, "graphql": page}),
            encoding="utf-8",
        )
        fake = TEST_DIR / "fixtures/fake_gh.py"
        transport = github_response_provider.GhJsonTransport(
            [sys.executable, str(fake), str(self.provider_state)]
        )
        self.epoch_adapter = github_response_provider.TypedEpochAdapter(transport)
        self.runtime = response_runtime.ResponseRuntime(
            state_directory=root / "ledger",
            epoch_adapter=self.epoch_adapter,
            inline_adapter=github_response_provider.InlineReplyAdapter(transport),
            conversation_adapter=github_response_provider.PullRequestConversationAdapter(
                transport
            ),
        )
        self.epoch = self.epoch_adapter.acquire("base-owner/base-repo", 7)

    def tearDown(self):
        self.temporary.cleanup()

    def provider_calls(self):
        return json.loads(self.provider_state.read_text(encoding="utf-8"))["calls"]

    def graphql_read_query_calls(self):
        return [
            call
            for call in self.provider_calls()
            if call["operation"] == "graphql_read_query"
        ]

    def response_write_calls(self):
        return [
            call
            for call in self.provider_calls()
            if call["operation"] == "response_write"
        ]

    def update_provider(self, update):
        state = json.loads(self.provider_state.read_text(encoding="utf-8"))
        update(state)
        self.provider_state.write_text(json.dumps(state), encoding="utf-8")

    def test_missing_classification_or_independence_evidence_makes_zero_provider_calls(
        self,
    ):
        for missing in ("classification", "independence_evidence"):
            with self.subTest(missing=missing):
                intent = make_intent(self.epoch, self.epoch["sources"][0], missing)
                del intent[missing]
                calls_before = list(self.provider_calls())

                with self.assertRaises(response_runtime.AdmissionError):
                    self.runtime.invoke(intent, b"Done")

                self.assertEqual(self.provider_calls(), calls_before)
                self.assertFalse(self.runtime.store.directory.exists())

    def test_contradictory_pagination_is_rejected_before_provider_access(self):
        mutations = {
            "nonnull_first_request": lambda pages, collection: pages[0].update(
                request_cursor="unexpected"
            ),
            "early_terminal": lambda pages, collection: pages[0].update(
                has_next_page=False
            ),
            "null_continuation": lambda pages, collection: pages[0].update(
                end_cursor=None
            ),
            "empty_continuation": lambda pages, collection: pages[0].update(
                end_cursor=""
            ),
            "nonprogressing_continuation": lambda pages, collection: pages[0].update(
                end_cursor=pages[0].get("request_cursor")
            ),
            "wrong_next_request": lambda pages, collection: pages[1].update(
                request_cursor="wrong"
            ),
            "nonterminal_final": lambda pages, collection: pages[-1].update(
                has_next_page=True, end_cursor="more"
            ),
            "wrong_total_count": lambda pages, collection: collection.update(
                node_count=collection["node_count"] + 1
            ),
            "wrong_page_count": lambda pages, collection: pages[0].update(
                node_count=pages[0]["node_count"] + 1
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                epoch = copy.deepcopy(self.epoch)
                collection = epoch["pagination_evidence"]["collections"]["threads"]
                pages = collection["pages"]
                if len(pages) == 1:
                    first = copy.deepcopy(pages[0])
                    first.update(has_next_page=True, end_cursor="cursor-1")
                    pages[:] = [
                        first,
                        {
                            **copy.deepcopy(pages[0]),
                            "page_index": 1,
                            "request_cursor": "cursor-1",
                        },
                    ]
                    collection["node_count"] = sum(page["node_count"] for page in pages)
                mutate(pages, collection)
                material = dict(epoch)
                material.pop("epoch_id")
                epoch["epoch_id"] = response_outcome_store.digest(material)
                intent = make_intent(epoch, epoch["sources"][0], f"paging-{name}")
                calls_before = list(self.provider_calls())

                with self.assertRaisesRegex(
                    response_runtime.AdmissionError,
                    "invalid-response-outcome-bundle",
                ):
                    self.runtime.invoke(intent, b"Done")

                self.assertEqual(self.provider_calls(), calls_before)

    def test_hydrated_thread_trace_relations_are_rejected_before_provider_access(self):
        mutations = {
            "wrong_request": lambda thread: thread["pages"][1].update(
                request_cursor="wrong"
            ),
            "repeated_cursor": lambda thread: thread["pages"][1].update(
                has_next_page=True, end_cursor="cursor-1"
            ),
            "wrong_terminal": lambda thread: thread.update(terminal_end_cursor="wrong"),
            "wrong_comment_count": lambda thread: thread.update(
                comment_count=thread["comment_count"] + 1
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                epoch = copy.deepcopy(self.epoch)
                thread = epoch["pagination_evidence"]["hydrated_threads"][0]
                first = copy.deepcopy(thread["pages"][0])
                first.update(has_next_page=True, end_cursor="cursor-1")
                second = copy.deepcopy(thread["pages"][0])
                second.update(page_index=1, request_cursor="cursor-1")
                thread["pages"] = [first, second]
                thread["comment_count"] = sum(
                    page["node_count"] for page in thread["pages"]
                )
                thread["terminal_end_cursor"] = second["end_cursor"]
                mutate(thread)
                material = dict(epoch)
                material.pop("epoch_id")
                epoch["epoch_id"] = response_outcome_store.digest(material)
                calls_before = list(self.provider_calls())

                with self.assertRaisesRegex(
                    response_runtime.AdmissionError,
                    "invalid-response-outcome-bundle",
                ):
                    self.runtime.invoke(
                        make_intent(epoch, epoch["sources"][0], f"thread-{name}"),
                        b"Done",
                    )

                self.assertEqual(self.provider_calls(), calls_before)

    def expose_inline_response(self, response_id=900, body="Done"):
        def expose(state):
            pr = state["graphql"]["data"]["repository"]["pullRequest"]
            result = copy.deepcopy(
                pr["reviewThreads"]["nodes"][0]["comments"]["nodes"][1]
            )
            result.update(
                {
                    "id": f"RESPONSE_node_{response_id}",
                    "databaseId": response_id,
                    "body": body,
                    "author": {
                        "__typename": "User",
                        "id": "USER_ivan",
                        "login": "ivan",
                    },
                    "createdAt": "2026-09-09T00:00:00Z",
                    "updatedAt": "2026-09-09T00:00:00Z",
                    "url": f"https://github.com/base-owner/base-repo/pull/7#discussion_r{response_id}",
                }
            )
            pr["reviewThreads"]["nodes"][0]["comments"]["nodes"].append(result)

        self.update_provider(expose)

    def restarted_runtime(self):
        fake = TEST_DIR / "fixtures/fake_gh.py"
        transport = github_response_provider.GhJsonTransport(
            [sys.executable, str(fake), str(self.provider_state)]
        )
        return response_runtime.ResponseRuntime(
            state_directory=self.runtime.store.directory,
            epoch_adapter=github_response_provider.TypedEpochAdapter(transport),
            inline_adapter=github_response_provider.InlineReplyAdapter(transport),
            conversation_adapter=github_response_provider.PullRequestConversationAdapter(
                transport
            ),
        )

    def isolated_runtime(self, name):
        root = Path(self.temporary.name) / name
        root.mkdir()
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
            state_directory=root / "ledger",
            epoch_adapter=epochs,
            inline_adapter=github_response_provider.InlineReplyAdapter(transport),
            conversation_adapter=github_response_provider.PullRequestConversationAdapter(
                transport
            ),
        )
        return state_path, epochs, runtime, epochs.acquire("base-owner/base-repo", 7)

    def inject_store_failure(self, context, step="staging_create"):
        def inject(actual_step, actual_context):
            if actual_step == step and actual_context == context:
                raise OSError(f"injected {context} {step}")

        self.runtime.store = response_outcome_store.ResponseOutcomeStore(
            self.runtime.store.directory, fault_injector=inject
        )

    def test_exact_replay_returns_no_op_and_changed_binding_conflicts_before_write(
        self,
    ):
        source = self.epoch["sources"][0]
        intent = make_intent(self.epoch, source, body=b"Same body")
        first = self.runtime.invoke(intent, b"Same body")
        replay = self.runtime.invoke(intent, b"Same body")

        self.assertEqual(first["status"], "confirmed_success")
        self.assertEqual(replay["status"], "confirmed_no_op")
        self.assertFalse(first["all_feedback_addressed"])
        self.assertFalse(replay["all_feedback_addressed"])
        self.assertTrue(self.graphql_read_query_calls())
        post_calls = self.response_write_calls()
        self.assertEqual(len(post_calls), 1)

        changed = copy.deepcopy(intent)
        changed["writer"]["identity"] = "different-writer"
        with self.assertRaises(response_runtime.IntentConflict):
            self.runtime.invoke(changed, b"Same body")
        post_calls = self.response_write_calls()
        self.assertEqual(len(post_calls), 1)

    def test_repository_rename_keeps_one_owner_for_every_supported_source_kind(self):
        for index, source_kind in enumerate(
            (
                "inline_review_comment",
                "pr_conversation_comment",
                "submitted_review_body",
            )
        ):
            with self.subTest(source_kind=source_kind):
                state_path, epochs, runtime, epoch = self.isolated_runtime(
                    f"rename-{index}"
                )
                source = next(
                    item for item in epoch["sources"] if item["kind"] == source_kind
                )
                body = response_body(source)
                first = runtime.invoke(
                    make_intent(epoch, source, "before-rename", body), body
                )

                state = json.loads(state_path.read_text(encoding="utf-8"))
                rename_repository(state)
                state_path.write_text(json.dumps(state), encoding="utf-8")
                renamed_epoch = epochs.acquire("renamed-owner/renamed-repo", 7)
                renamed_source = next(
                    item
                    for item in renamed_epoch["sources"]
                    if item["kind"] == source_kind
                    and item["provider_identity"] == source["provider_identity"]
                )
                calls_before = list(
                    json.loads(state_path.read_text(encoding="utf-8"))["calls"]
                )

                with self.assertRaisesRegex(
                    response_runtime.IntentConflict,
                    "source revision already has an ordinary owner",
                ):
                    runtime.invoke(
                        make_intent(
                            renamed_epoch,
                            renamed_source,
                            "after-rename",
                            response_body(renamed_source),
                        ),
                        response_body(renamed_source),
                    )

                provider = json.loads(state_path.read_text(encoding="utf-8"))
                writes = [
                    call
                    for call in provider["calls"]
                    if call["operation"] == "response_write"
                ]
                history = response_outcome_store.ResponseOutcomeStore(
                    runtime.store.directory
                ).semantic_history()
                self.assertEqual(first["status"], "confirmed_success")
                self.assertEqual(provider["calls"], calls_before)
                self.assertEqual(len(writes), 1)
                self.assertEqual(len(history["owners"]), 1)
                self.assertEqual(len(history["source_chains"]), 1)

    def test_repository_rename_remains_full_prewrite_drift_and_blocks_write(self):
        intent = make_intent(self.epoch, self.epoch["sources"][0], "stale-context")
        self.update_provider(rename_repository)

        result = self.runtime.invoke(intent, b"Done")

        self.assertEqual(result["status"], "confirmed_failure")
        self.assertEqual(result["pre_write_state"], "validation_indeterminate")
        self.assertIn("first page does not match requested pull request", result["reason"])
        self.assertFalse(result["provider_call"])
        self.assertEqual(self.response_write_calls(), [])

    def test_repository_rename_post_terminal_basis_reuses_owner_with_fresh_context(
        self,
    ):
        self.update_provider(
            lambda state: state["graphql"]["data"]["repository"][
                "pullRequest"
            ].update(headRefOid="terminal-head")
        )
        blocked = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][0], "stale"), b"Done"
        )
        self.assertEqual(blocked["pre_write_state"], "invalidated_unexecuted")
        self.update_provider(rename_repository)

        runtime = self.restarted_runtime()
        basis = runtime.prepare_replacement("stale", "renamed-owner/renamed-repo")
        result = runtime.invoke(
            make_replacement_intent(basis, "renamed-successor"), b"Done"
        )

        history = runtime.store.semantic_history()
        predecessor = history["intents"][history["keys"]["stale"]]
        successor = history["intents"][history["keys"]["renamed-successor"]]
        self.assertEqual(result["status"], "confirmed_success")
        self.assertEqual(successor["owner_id"], predecessor["owner_id"])
        self.assertEqual(len(history["owners"]), 1)
        self.assertEqual(
            basis["successor_epoch"]["repository"]["name_with_owner"],
            "renamed-owner/renamed-repo",
        )
        self.assertEqual(
            successor["binding"]["target"]["repository"]["name_with_owner"],
            "renamed-owner/renamed-repo",
        )
        self.assertEqual(len(self.response_write_calls()), 1)

    def test_replacement_locator_is_validated_before_provider_access(self):
        self.update_provider(
            lambda state: state["graphql"]["data"]["repository"][
                "pullRequest"
            ].update(headRefOid="terminal-head")
        )
        blocked = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][0], "stale-locator"), b"Done"
        )
        self.assertEqual(blocked["pre_write_state"], "invalidated_unexecuted")
        before = len(self.response_write_calls())
        with self.assertRaises(response_runtime.AdmissionError):
            self.runtime.prepare_replacement("stale-locator", "renamed-owner")
        self.assertEqual(len(self.response_write_calls()), before)

    def test_distinct_stable_repository_pr_and_source_revision_remain_distinct(self):
        def different_repository(epoch):
            epoch["repository"]["provider_identity"] = {
                "database_id": 999,
                "node_id": "REPOSITORY_999",
            }

        def different_pull_request(epoch):
            pull_request = epoch["pull_request"]
            old_node = pull_request["node_id"]
            pull_request.update(database_id=999, node_id="PULL_REQUEST_999", number=8)
            for identity in epoch["identity_registry"]:
                if (
                    identity["object_kind"] == "PullRequest"
                    and identity["node_id"] == old_node
                ):
                    identity["node_id"] = "PULL_REQUEST_999"
                    identity["database_id"]["value"] = 999

        def different_source_revision(epoch):
            old = epoch["sources"][0]
            changed = copy.deepcopy(old)
            raw = b"Changed exact source revision"
            changed_body = {
                "utf8_base64": base64.b64encode(raw).decode("ascii"),
                "byte_length": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
            changed["body"] = changed_body
            changed["source_revision_identity"]["body"] = changed_body
            changed["source_revision_identity"]["provider_revision"]["value"] = (
                "changed-provider-revision"
            )
            changed["source_revision"] = response_outcome_store.digest(
                changed["source_revision_identity"]
            )
            epoch["sources"][0] = changed
            epoch["observations"] = [
                changed if item == old else item for item in epoch["observations"]
            ]

        for index, mutate in enumerate(
            (different_repository, different_pull_request, different_source_revision)
        ):
            with self.subTest(case=mutate.__name__):
                _, _, runtime, epoch = self.isolated_runtime(f"distinct-{index}")
                source = epoch["sources"][0]
                first = runtime.invoke(
                    make_intent(epoch, source, "first-owner"), b"Done"
                )
                changed_epoch = copy.deepcopy(epoch)
                mutate(changed_epoch)
                finalize_epoch(changed_epoch)
                changed_source = changed_epoch["sources"][0]

                class FixedEpochAdapter:
                    def __init__(self, fixed_epoch):
                        self.fixed_epoch = copy.deepcopy(fixed_epoch)

                    def acquire(self, _repository, _pr_number):
                        return copy.deepcopy(self.fixed_epoch)

                runtime.epoch_adapter = FixedEpochAdapter(changed_epoch)
                second = runtime.invoke(
                    make_intent(changed_epoch, changed_source, "second-owner"), b"Done"
                )

                history = runtime.store.semantic_history()
                first_intent = history["intents"][history["keys"]["first-owner"]]
                second_intent = history["intents"][history["keys"]["second-owner"]]
                self.assertEqual(first["status"], "confirmed_success")
                self.assertEqual(second["status"], "confirmed_success")
                self.assertNotEqual(first_intent["owner_id"], second_intent["owner_id"])
                self.assertEqual(len(history["owners"]), 2)

    def test_equal_bodies_on_distinct_sources_produce_independent_leaf_operations(self):
        body = b"Same body"
        first = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][0], "one", body), body
        )
        second = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][1], "two", body), body
        )

        self.assertEqual(first["status"], "confirmed_success")
        self.assertEqual(second["status"], "confirmed_success", second)
        self.assertNotEqual(
            first["leaf_receipt"]["response"]["database_id"],
            second["leaf_receipt"]["response"]["database_id"],
        )
        post_calls = self.response_write_calls()
        self.assertEqual(len(post_calls), 2)

    def test_proven_no_write_failure_retries_same_key_after_full_revalidation(self):
        endpoint = "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
        body = "Done exactly.\r\nUnicode: caf\u00e9.\n".encode("utf-8")
        self.update_provider(
            lambda state: state.setdefault("queued", {}).update(
                {endpoint: [{"returncode": 1, "stderr": "HTTP 409"}]}
            )
        )
        intent = make_intent(self.epoch, self.epoch["sources"][0], body=body)

        failed = self.runtime.invoke(intent, body)
        retried = self.runtime.invoke(intent, body)

        self.assertEqual(failed["status"], "confirmed_failure")
        self.assertEqual(failed["leaf_receipt"]["side_effect"], "none")
        self.assertEqual(retried["status"], "confirmed_success")
        self.assertEqual(retried["retry_of_attempt_id"], failed["attempt_id"])
        history = self.runtime.store.semantic_history()
        admitted = history["intents"][history["keys"]["intent-1"]]
        attempts = list(history["attempts"].values())
        self.assertEqual([attempt["ordinal"] for attempt in attempts], [1, 2])
        self.assertEqual(
            attempts[1]["retry_predecessor"],
            {
                "kind": "confirmed_failure_outcome",
                "outcome_id": failed["outcome_id"],
            },
        )
        self.assertTrue(
            all(
                attempt["owner_id"] == admitted["owner_id"]
                and attempt["intent_id"] == admitted["intent_id"]
                and attempt["binding_digest"] == admitted["binding_digest"]
                for attempt in attempts
            )
        )
        self.assertEqual(
            [
                call["request"]["body"].encode("utf-8")
                for call in self.response_write_calls()
            ],
            [body, body],
        )

    def test_write_start_rejects_independent_and_pairwise_lineage_mismatches(self):
        state_path, _, runtime, epoch = self.isolated_runtime("write-link-matrix")
        other = runtime.invoke(
            make_intent(epoch, epoch["sources"][0], "other"), b"Done"
        )
        endpoint = "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.setdefault("queued", {})[endpoint] = [
            {"returncode": 1, "stderr": "HTTP 409"}
        ]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        target_intent = make_intent(epoch, epoch["sources"][1], "target")
        failed = runtime.invoke(target_intent, b"Done")
        runtime.invoke(target_intent, b"Done")
        records = runtime.store.records()
        target_write_index = max(
            index
            for index, record in enumerate(records)
            if record["record_kind"] == "write_started"
        )
        prefix = records[: target_write_index + 1]
        history = response_outcome_store.fold_semantic_history(prefix)
        other_intent = history["intents"][history["keys"]["other"]]
        target = history["intents"][history["keys"]["target"]]
        wrong_predecessor = {
            "kind": "confirmed_failure_outcome",
            "outcome_id": other["outcome_id"],
        }

        def mutate_owner(attempt):
            attempt["owner_id"] = other_intent["owner_id"]

        def mutate_intent(attempt):
            attempt["intent_id"] = other_intent["intent_id"]

        def mutate_binding(attempt):
            attempt["binding_digest"] = other_intent["binding_digest"]

        def mutate_mode(attempt):
            attempt["mode"] = "initial"
            attempt["retry_predecessor"] = None

        def mutate_ordinal(attempt):
            attempt["ordinal"] = 1

        def mutate_predecessor(attempt):
            attempt["retry_predecessor"] = wrong_predecessor

        mutations = {
            "owner": mutate_owner,
            "intent": mutate_intent,
            "binding": mutate_binding,
            "mode": mutate_mode,
            "ordinal": mutate_ordinal,
            "predecessor": mutate_predecessor,
        }
        cases = [(name,) for name in mutations]
        cases.extend(itertools.combinations(mutations, 2))
        for names in cases:
            with self.subTest(fields=names):
                malformed = copy.deepcopy(prefix)
                attempt = malformed[-1]["payload"]["attempt"]
                for name in names:
                    mutations[name](attempt)
                with self.assertRaisesRegex(
                    response_outcome_store.OutcomeStoreError,
                    "invalid-response-outcome-bundle.*write-started",
                ):
                    response_outcome_store.fold_semantic_history(malformed)

        self.assertEqual(failed["status"], "confirmed_failure")
        self.assertEqual(
            target["binding_digest"], prefix[-1]["payload"]["attempt"]["binding_digest"]
        )

    def test_authored_proven_absence_cannot_unfreeze_an_unknown_intent(self):
        endpoint = "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
        self.update_provider(
            lambda state: state.setdefault("queued", {}).update(
                {endpoint: [{"returncode": 1, "stderr": "connection reset"}]}
            )
        )
        intent = make_intent(self.epoch, self.epoch["sources"][0], "absent-retry")
        unknown = self.runtime.invoke(intent, b"Done")
        self.assertEqual(unknown["status"], "unknown")

        with self.runtime.store.locked(exclusive=True):
            history = self.runtime.store.semantic_history()
            admitted = history["intents"][history["keys"]["absent-retry"]]
            attempt = history["attempts"][unknown["attempt_id"]]
            reconciliation_id = "reconciliation-conclusive-absence"
            self.runtime.store.append(
                "reconciliation_started",
                {
                    "schema_version": 2,
                    "reconciliation_id": reconciliation_id,
                    "owner_id": admitted["owner_id"],
                    "intent_id": admitted["intent_id"],
                    "attempt_id": attempt["attempt_id"],
                    "intent_key": admitted["intent_key"],
                    "binding_digest": admitted["binding_digest"],
                    "prior_reconciliation_id": None,
                    "supersedes_incomplete_reconciliation_id": None,
                    "candidate_reservation": None,
                },
                record_id=reconciliation_id,
            )
            with self.assertRaisesRegex(
                response_outcome_store.OutcomeStoreError,
                "invalid-response-outcome-bundle.*reconciliation result is unsupported",
            ):
                self.runtime.store.append(
                    "reconciliation_resolution",
                    {
                        "schema_version": 2,
                        "reconciliation_id": reconciliation_id,
                        "attempt_id": attempt["attempt_id"],
                        "owner_id": admitted["owner_id"],
                        "intent_id": admitted["intent_id"],
                        "result": "proven_absent_retry_eligible",
                        "outcome": None,
                        "identity_observations": [],
                        "identity_claim": None,
                        "absence_evidence": {
                            "conclusive_no_write": True,
                            "evidence_id": "authored-no-write-assertion-1",
                        },
                    },
                    record_id=f"resolution-{reconciliation_id}",
                )

        with self.assertRaises(response_runtime.ReconciliationRequired):
            self.runtime.invoke(intent, b"Done")
        with self.assertRaises(response_runtime.ReconciliationRequired):
            self.runtime.invoke(
                make_intent(
                    self.epoch, self.epoch["sources"][0], "fresh-after-unknown"
                ),
                b"Done",
            )
        self.assertEqual(len(self.response_write_calls()), 1)

    def test_unknown_blocks_same_key_and_fresh_key_and_empty_reconciliation_stays_unknown(
        self,
    ):
        endpoint = "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
        self.update_provider(
            lambda state: state.setdefault("queued", {}).update(
                {endpoint: [{"returncode": 1, "stderr": "connection reset"}]}
            )
        )
        intent = make_intent(self.epoch, self.epoch["sources"][0])
        unknown = self.runtime.invoke(intent, b"Done")
        self.assertEqual(unknown["status"], "unknown")

        with self.assertRaises(response_runtime.ReconciliationRequired):
            self.runtime.invoke(intent, b"Done")
        with self.assertRaises(response_runtime.ReconciliationRequired):
            self.runtime.invoke(
                make_intent(self.epoch, self.epoch["sources"][0], "fresh"),
                b"Done",
            )

        reconciled = self.runtime.reconcile("intent-1")
        self.assertEqual(reconciled["status"], "unknown")
        self.assertIn("does_not_prove_absence", reconciled["leaf_receipt"]["reason"])
        post_calls = self.response_write_calls()
        self.assertEqual(len(post_calls), 1)

    def test_ambiguous_reconciliation_stays_unknown_without_a_second_write(self):
        endpoint = "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
        self.update_provider(
            lambda state: state.setdefault("queued", {}).update(
                {endpoint: [{"returncode": 1, "stderr": "connection reset"}]}
            )
        )
        intent = make_intent(self.epoch, self.epoch["sources"][0], "ambiguous")
        unknown = self.runtime.invoke(intent, b"Done")
        self.assertEqual(unknown["status"], "unknown")

        def expose_two_exact_results(state):
            pr = state["graphql"]["data"]["repository"]["pullRequest"]
            template = copy.deepcopy(
                pr["reviewThreads"]["nodes"][0]["comments"]["nodes"][1]
            )
            for response_id in (950, 951):
                result = copy.deepcopy(template)
                result.update(
                    {
                        "id": f"RESPONSE_node_{response_id}",
                        "databaseId": response_id,
                        "body": "Done",
                        "author": {
                            "__typename": "User",
                            "id": "USER_ivan",
                            "login": "ivan",
                        },
                        "createdAt": "2026-09-09T00:00:00Z",
                        "updatedAt": "2026-09-09T00:00:00Z",
                        "url": (
                            "https://github.com/base-owner/base-repo/pull/7"
                            f"#discussion_r{response_id}"
                        ),
                    }
                )
                pr["reviewThreads"]["nodes"][0]["comments"]["nodes"].append(result)

        self.update_provider(expose_two_exact_results)
        reconciled = self.runtime.reconcile("ambiguous")

        self.assertEqual(reconciled["status"], "unknown")
        self.assertIn("multiple_exact_results_are_ambiguous", reconciled["reason"])
        self.assertEqual(len(self.response_write_calls()), 1)

    def test_two_effective_unknowns_never_attribute_one_indistinguishable_result(self):
        for different_head in (False, True):
            with self.subTest(different_head=different_head):
                state_path, epochs, runtime, first_epoch = self.isolated_runtime(
                    f"two-unknowns-{different_head}"
                )
                endpoint = (
                    "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
                )
                state = json.loads(state_path.read_text(encoding="utf-8"))
                state.setdefault("queued", {})[endpoint] = [
                    {"returncode": 1, "stderr": "connection reset"},
                    {"returncode": 1, "stderr": "connection reset"},
                ]
                state_path.write_text(json.dumps(state), encoding="utf-8")
                body = b"Same response"
                first = runtime.invoke(
                    make_intent(
                        first_epoch, first_epoch["sources"][0], "unknown-a", body
                    ),
                    body,
                )
                second_epoch = first_epoch
                if different_head:
                    state = json.loads(state_path.read_text(encoding="utf-8"))
                    state["graphql"]["data"]["repository"]["pullRequest"][
                        "headRefOid"
                    ] = "different-head-same-typed-pr"
                    state_path.write_text(json.dumps(state), encoding="utf-8")
                    second_epoch = epochs.acquire("base-owner/base-repo", 7)
                second = runtime.invoke(
                    make_intent(
                        second_epoch,
                        second_epoch["sources"][1],
                        "unknown-b",
                        body,
                    ),
                    body,
                )
                self.assertEqual(
                    [first["status"], second["status"]], ["unknown", "unknown"]
                )

                state = json.loads(state_path.read_text(encoding="utf-8"))
                pr = state["graphql"]["data"]["repository"]["pullRequest"]
                result = copy.deepcopy(
                    pr["reviewThreads"]["nodes"][0]["comments"]["nodes"][1]
                )
                result.update(
                    {
                        "id": "RESPONSE_node_950",
                        "databaseId": 950,
                        "body": body.decode(),
                        "author": {
                            "__typename": "User",
                            "id": "USER_ivan",
                            "login": "ivan",
                        },
                        "createdAt": "2026-09-09T00:00:00Z",
                        "updatedAt": "2026-09-09T00:00:00Z",
                        "url": (
                            "https://github.com/base-owner/base-repo/pull/7"
                            "#discussion_r950"
                        ),
                    }
                )
                pr["reviewThreads"]["nodes"][0]["comments"]["nodes"].append(result)
                state.setdefault("objects", {})["950"] = {
                    "id": 950,
                    "node_id": "RESPONSE_node_950",
                    "body": body.decode(),
                    "html_url": result["url"],
                    "user": {"login": "ivan"},
                }
                calls_before = list(state["calls"])
                state_path.write_text(json.dumps(state), encoding="utf-8")

                reconciled = runtime.reconcile("unknown-a")
                reconciled_second = runtime.reconcile("unknown-b")
                reconciled_again = runtime.reconcile("unknown-a")

                self.assertEqual(
                    [
                        reconciled["status"],
                        reconciled_second["status"],
                        reconciled_again["status"],
                    ],
                    ["unknown", "unknown", "unknown"],
                )
                self.assertIn("indistinguishable", reconciled["reason"])
                history = runtime.store.semantic_history()
                self.assertEqual(history["identity_owners"], {})
                self.assertEqual(history["identity_observers"], {})
                self.assertEqual(
                    json.loads(state_path.read_text(encoding="utf-8"))["calls"],
                    calls_before,
                )

    def test_repeated_identical_still_unknown_rounds_have_distinct_outcomes(self):
        endpoint = "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
        self.update_provider(
            lambda state: state.setdefault("queued", {}).update(
                {endpoint: [{"returncode": 1, "stderr": "connection reset"}]}
            )
        )
        original = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][0], "repeat-unknown"),
            b"Done",
        )

        first = self.runtime.reconcile("repeat-unknown")
        second = self.restarted_runtime().reconcile("repeat-unknown")

        self.assertEqual([first["status"], second["status"]], ["unknown", "unknown"])
        self.assertNotEqual(first["outcome_id"], second["outcome_id"])
        history = self.runtime.store.semantic_history()
        attempt_id = original["attempt_id"]
        self.assertEqual(
            history["effective_outcome_by_attempt"][attempt_id],
            second["outcome_id"],
        )
        self.assertEqual(len(self.runtime.store.read("reconciliation_resolution")), 2)
        self.assertEqual(len(self.response_write_calls()), 1)

    def test_nonnull_absence_assertion_cannot_be_retained_on_unknown_resolution(self):
        endpoint = "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
        self.update_provider(
            lambda state: state.setdefault("queued", {}).update(
                {endpoint: [{"returncode": 1, "stderr": "connection reset"}]}
            )
        )
        unknown = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][0], "asserted-absence"),
            b"Done",
        )
        self.assertEqual(unknown["status"], "unknown")
        original_append = self.runtime.store.append

        def append_with_absence_assertion(record_kind, payload, **kwargs):
            if record_kind == "reconciliation_resolution":
                payload = copy.deepcopy(payload)
                payload["absence_evidence"] = {
                    "conclusive_no_write": True,
                    "evidence_id": "authored-no-write-assertion-2",
                }
            return original_append(record_kind, payload, **kwargs)

        self.runtime.store.append = append_with_absence_assertion
        with self.assertRaisesRegex(
            response_outcome_store.OutcomeStoreError,
            "invalid-response-outcome-bundle.*absence",
        ):
            self.runtime.reconcile("asserted-absence")

        self.assertEqual(len(self.response_write_calls()), 1)

    def test_follow_up_requires_and_links_a_confirmed_predecessor(self):
        source = self.epoch["sources"][0]
        first = self.runtime.invoke(make_intent(self.epoch, source), b"Done")
        follow_up = make_intent(self.epoch, source, "addendum", b"Additional detail")
        follow_up["intent_kind"] = "follow_up"
        follow_up["predecessor_outcome_id"] = first["outcome_id"]

        added = self.runtime.invoke(follow_up, b"Additional detail")

        self.assertEqual(added["status"], "confirmed_success")
        self.assertEqual(added["predecessor_outcome_id"], first["outcome_id"])
        invalid = make_intent(self.epoch, source, "bad-follow-up", b"Bad")
        invalid["intent_kind"] = "follow_up"
        invalid["predecessor_outcome_id"] = "missing"
        with self.assertRaises(response_runtime.AdmissionError):
            self.runtime.invoke(invalid, b"Bad")

    def test_top_level_source_kinds_are_independent_and_link_is_pre_frozen(self):
        for index, key in ((2, "conversation"), (3, "review")):
            source = self.epoch["sources"][index]
            body = f"Addressed {source['permalink']}\r\n".encode()
            result = self.runtime.invoke(
                make_intent(self.epoch, source, key, body), body
            )
            self.assertEqual(result["status"], "confirmed_success")
            self.assertEqual(result["placement"]["kind"], "pull_request_conversation")
        posts = self.response_write_calls()
        self.assertEqual(len(posts), 2)
        self.assertTrue(
            all(
                any("/issues/7/comments" in arg for arg in call["argv"])
                for call in posts
            )
        )

    def test_post_write_head_drift_credits_the_response_without_clean_completion(self):
        base = json.loads(TYPED_FIXTURE.read_text(encoding="utf-8"))
        drift = copy.deepcopy(base)
        drift["data"]["repository"]["pullRequest"]["headRefOid"] = "new-head"
        self.update_provider(
            lambda state: state.setdefault("queued", {}).update(
                {
                    "POST graphql": [
                        {"returncode": 0, "json": base},
                        {"returncode": 0, "json": drift},
                    ]
                }
            )
        )

        result = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][0]), b"Done"
        )

        self.assertEqual(result["status"], "confirmed_success")
        self.assertEqual(result["post_write_drift_assessment"]["state"], "observed")
        self.assertIn(
            "head_oid drifted", result["post_write_drift_assessment"]["evidence"]
        )
        self.assertFalse(result["all_feedback_addressed"])

    def test_atomic_resolution_failure_reconciles_without_second_write(
        self,
    ):
        self.inject_store_failure("attempt_resolution")
        intent = make_intent(self.epoch, self.epoch["sources"][0])
        with self.assertRaises(response_runtime.SemanticPersistenceIncomplete):
            self.runtime.invoke(intent, b"Done")
        self.runtime.store._fault_injector = None

        with self.assertRaises(response_runtime.ReconciliationRequired):
            self.runtime.invoke(intent, b"Done")
        self.expose_inline_response()
        reconciled = self.runtime.reconcile("intent-1")

        self.assertEqual(reconciled["status"], "confirmed_success")
        posts = self.response_write_calls()
        self.assertEqual(len(posts), 1)
        self.assertEqual(len(self.runtime.read_outcomes()), 1)

    def test_attempt_resolution_publication_faults_restart_as_unknown_or_whole_resolution(
        self,
    ):
        for step in (
            "staging_create",
            "staging_write",
            "staging_close",
            "file_fsync",
            "hard_link",
            "directory_fsync",
        ):
            with self.subTest(step=step):
                root = Path(self.temporary.name) / f"resolution-fault-{step}"
                root.mkdir()
                provider = root / "provider.json"
                provider.write_text(
                    json.dumps(
                        {
                            "actor": "ivan",
                            "next_id": 900,
                            "graphql": json.loads(
                                TYPED_FIXTURE.read_text(encoding="utf-8")
                            ),
                        }
                    ),
                    encoding="utf-8",
                )
                fake = TEST_DIR / "fixtures/fake_gh.py"
                transport = github_response_provider.GhJsonTransport(
                    [sys.executable, str(fake), str(provider)]
                )
                epochs = github_response_provider.TypedEpochAdapter(transport)
                epoch = epochs.acquire("base-owner/base-repo", 7)

                def inject(actual_step, context, expected=step):
                    if context == "attempt_resolution" and actual_step == expected:
                        raise OSError(f"injected {expected}")

                runtime = response_runtime.ResponseRuntime(
                    state_directory=root / "ledger",
                    epoch_adapter=epochs,
                    inline_adapter=github_response_provider.InlineReplyAdapter(
                        transport
                    ),
                    conversation_adapter=github_response_provider.PullRequestConversationAdapter(
                        transport
                    ),
                    outcome_store=response_outcome_store.ResponseOutcomeStore(
                        root / "ledger", fault_injector=inject
                    ),
                )
                intent = make_intent(epoch, epoch["sources"][0], f"fault-{step}")
                with self.assertRaises(response_runtime.SemanticPersistenceIncomplete):
                    runtime.invoke(intent, b"Done")
                restarted = response_runtime.ResponseRuntime(
                    state_directory=root / "ledger",
                    epoch_adapter=epochs,
                    inline_adapter=github_response_provider.InlineReplyAdapter(
                        transport
                    ),
                    conversation_adapter=github_response_provider.PullRequestConversationAdapter(
                        transport
                    ),
                )
                if step == "directory_fsync":
                    self.assertEqual(
                        restarted.invoke(intent, b"Done")["status"], "confirmed_no_op"
                    )
                else:
                    with self.assertRaises(response_runtime.ReconciliationRequired):
                        restarted.invoke(intent, b"Done")
                calls = json.loads(provider.read_text(encoding="utf-8"))["calls"]
                self.assertEqual(
                    sum(call["operation"] == "response_write" for call in calls),
                    1,
                )

    def test_persistence_failure_preserves_post_write_drift_during_reconciliation(self):
        base = json.loads(TYPED_FIXTURE.read_text(encoding="utf-8"))
        drift = copy.deepcopy(base)
        drift["data"]["repository"]["pullRequest"]["headRefOid"] = "new-head"
        self.update_provider(
            lambda state: state.update(
                {
                    "graphql": drift,
                    "queued": {
                        "POST graphql": [
                            {"returncode": 0, "json": base},
                            {"returncode": 0, "json": drift},
                        ]
                    },
                }
            )
        )
        self.inject_store_failure("attempt_resolution")
        with self.assertRaises(response_runtime.SemanticPersistenceIncomplete):
            self.runtime.invoke(
                make_intent(self.epoch, self.epoch["sources"][0]), b"Done"
            )
        self.runtime.store._fault_injector = None

        self.expose_inline_response()
        reconciled = self.runtime.reconcile("intent-1")

        self.assertEqual(reconciled["status"], "confirmed_success")
        self.assertEqual(reconciled["post_write_drift_assessment"]["state"], "unknown")
        self.assertFalse(reconciled["all_feedback_addressed"])
        self.assertEqual(len(self.response_write_calls()), 1)

    def test_missing_atomic_resolution_blocks_all_keys_until_same_intent_reconciliation(
        self,
    ):
        self.inject_store_failure("attempt_resolution")
        intent = make_intent(self.epoch, self.epoch["sources"][0])
        with self.assertRaises(response_runtime.SemanticPersistenceIncomplete):
            self.runtime.invoke(intent, b"Done")
        self.runtime.store._fault_injector = None

        restarted = self.restarted_runtime()
        with self.assertRaises(response_runtime.ReconciliationRequired):
            restarted.invoke(intent, b"Done")
        with self.assertRaises(response_runtime.ReconciliationRequired):
            restarted.invoke(
                make_intent(self.epoch, self.epoch["sources"][0], "fresh"),
                b"Done",
            )

        def expose_result(state):
            pr = state["graphql"]["data"]["repository"]["pullRequest"]
            result = copy.deepcopy(
                pr["reviewThreads"]["nodes"][0]["comments"]["nodes"][1]
            )
            result.update(
                {
                    "id": "RESPONSE_node_900",
                    "databaseId": 900,
                    "body": "Done",
                    "author": {
                        "__typename": "User",
                        "id": "USER_ivan",
                        "login": "ivan",
                    },
                    "createdAt": "2026-09-02T00:00:00Z",
                    "updatedAt": "2026-09-02T00:00:00Z",
                    "url": "https://github.com/base-owner/base-repo/pull/7#discussion_r900",
                }
            )
            pr["reviewThreads"]["nodes"][0]["comments"]["nodes"].append(result)

        self.update_provider(expose_result)
        initial_attempt = next(iter(restarted.store.semantic_history()["attempts"]))
        reconciled = restarted.reconcile("intent-1")

        self.assertEqual(reconciled["status"], "confirmed_success")
        self.assertEqual(reconciled["leaf_receipt"]["response"]["database_id"], 900)
        self.assertEqual(reconciled["reconciles_attempt_id"], initial_attempt)
        self.assertEqual(len(self.response_write_calls()), 1)

    def test_malformed_post_write_evidence_reconciles_without_second_write(self):
        self.update_provider(
            lambda state: state.update(
                {"reread_overrides": {"900": {"user": ["malformed"]}}}
            )
        )
        intent = make_intent(self.epoch, self.epoch["sources"][0])

        unknown = self.runtime.invoke(intent, b"Done")

        self.assertEqual(unknown["status"], "unknown")
        self.assertEqual(
            unknown["leaf_receipt"]["provider_evidence"]["create_response"]["id"],
            900,
        )
        with self.assertRaises(response_runtime.ReconciliationRequired):
            self.runtime.invoke(intent, b"Done")
        self.update_provider(lambda state: state.pop("reread_overrides"))
        reconciled = self.runtime.reconcile("intent-1")
        self.assertEqual(reconciled["status"], "confirmed_success")
        self.assertEqual(len(self.response_write_calls()), 1)

    def _assert_prewrite_change_blocks(self, change):
        def update(state):
            change(state["graphql"]["data"]["repository"]["pullRequest"])

        self.update_provider(update)
        result = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][0]), b"Done"
        )
        self.assertEqual(result["status"], "confirmed_failure")
        self.assertFalse(result["provider_call"])
        self.assertIn("pre_write_", result["reason"])
        posts = self.response_write_calls()
        self.assertEqual(posts, [])

    def test_source_edit_blocks_before_write(self):
        self._assert_prewrite_change_blocks(
            lambda pr: pr["reviewThreads"]["nodes"][0]["comments"]["nodes"][0].update(
                {"body": "Edited source", "updatedAt": "2026-09-02T00:00:00Z"}
            )
        )

    def test_source_deletion_blocks_before_write(self):
        self._assert_prewrite_change_blocks(
            lambda pr: pr["reviewThreads"]["nodes"][0]["comments"].update(
                {"nodes": pr["reviewThreads"]["nodes"][0]["comments"]["nodes"][1:]}
            )
        )

    def test_thread_state_change_blocks_before_write(self):
        self._assert_prewrite_change_blocks(
            lambda pr: pr["reviewThreads"]["nodes"][0].update({"isResolved": True})
        )

    def test_late_feedback_blocks_before_write(self):
        new_comment = copy.deepcopy(
            json.loads(TYPED_FIXTURE.read_text(encoding="utf-8"))["data"]["repository"][
                "pullRequest"
            ]["comments"]["nodes"][0]
        )
        new_comment.update(
            {
                "id": "NODE_late_777",
                "databaseId": 777,
                "body": "Late feedback",
                "url": "https://github.com/base-owner/base-repo/pull/7#issuecomment-777",
            }
        )
        self._assert_prewrite_change_blocks(
            lambda pr: pr["comments"]["nodes"].append(new_comment)
        )

    def test_head_drift_blocks_before_write(self):
        self._assert_prewrite_change_blocks(
            lambda pr: pr.update({"headRefOid": "new-head"})
        )

    def test_head_drift_remains_terminal_after_provider_reverts(self):
        original = copy.deepcopy(json.loads(TYPED_FIXTURE.read_text(encoding="utf-8")))
        self.update_provider(
            lambda state: state["graphql"]["data"]["repository"]["pullRequest"].update(
                {"headRefOid": "drifted-head"}
            )
        )
        intent = make_intent(self.epoch, self.epoch["sources"][0], "stale")
        first = self.runtime.invoke(intent, b"Done")
        self.update_provider(lambda state: state.update({"graphql": original}))

        with self.assertRaises(response_runtime.AdmissionError):
            self.restarted_runtime().invoke(intent, b"Done")

        self.assertEqual(first["status"], "confirmed_failure")
        self.assertEqual(self.response_write_calls(), [])

    def _assert_context_reversion_is_terminal(self, change):
        original = copy.deepcopy(json.loads(TYPED_FIXTURE.read_text(encoding="utf-8")))
        self.update_provider(
            lambda state: change(state["graphql"]["data"]["repository"]["pullRequest"])
        )
        intent = make_intent(self.epoch, self.epoch["sources"][0], "stale-context")
        first = self.runtime.invoke(intent, b"Done")
        self.update_provider(lambda state: state.update({"graphql": original}))
        with self.assertRaises(response_runtime.AdmissionError):
            self.restarted_runtime().invoke(intent, b"Done")
        self.assertEqual(first["pre_write_state"], "invalidated_unexecuted")
        self.assertEqual(self.response_write_calls(), [])

    def test_source_drift_remains_terminal_after_provider_reverts(self):
        self._assert_context_reversion_is_terminal(
            lambda pr: pr["reviewThreads"]["nodes"][0]["comments"]["nodes"][0].update(
                {"body": "edited", "updatedAt": "2026-09-10T00:00:00Z"}
            )
        )

    def test_thread_drift_remains_terminal_after_provider_reverts(self):
        self._assert_context_reversion_is_terminal(
            lambda pr: pr["reviewThreads"]["nodes"][0].update({"isResolved": True})
        )

    def test_relevant_comment_set_drift_remains_terminal_after_provider_reverts(self):
        def add_comment(pr):
            item = copy.deepcopy(pr["comments"]["nodes"][0])
            item.update(
                {
                    "id": "NODE_late_889",
                    "databaseId": 889,
                    "body": "late",
                    "url": "https://github.com/base-owner/base-repo/pull/7#issuecomment-889",
                }
            )
            pr["comments"]["nodes"].append(item)

        self._assert_context_reversion_is_terminal(add_comment)

    def test_invalidation_publication_faults_leave_old_intent_terminal_after_restart(
        self,
    ):
        for step in (
            "staging_create",
            "staging_write",
            "staging_close",
            "file_fsync",
            "hard_link",
            "directory_fsync",
        ):
            with self.subTest(step=step):
                state_path, epochs, runtime, epoch = self.isolated_runtime(
                    f"invalidation-{step}"
                )
                state = json.loads(state_path.read_text())
                state["graphql"]["data"]["repository"]["pullRequest"]["headRefOid"] = (
                    "drifted-head"
                )
                state_path.write_text(json.dumps(state))

                def inject(actual_step, context, expected=step):
                    if context == "prewrite_invalidated" and actual_step == expected:
                        raise OSError(f"injected {expected}")

                runtime.store = response_outcome_store.ResponseOutcomeStore(
                    runtime.store.directory, fault_injector=inject
                )
                intent = make_intent(epoch, epoch["sources"][0], f"old-{step}")
                with self.assertRaisesRegex(
                    response_outcome_store.OutcomeStoreError,
                    "storage-capability-failure",
                ):
                    runtime.invoke(intent, b"Done")
                restarted = response_runtime.ResponseRuntime(
                    state_directory=runtime.store.directory,
                    epoch_adapter=epochs,
                    inline_adapter=runtime.inline_adapter,
                    conversation_adapter=runtime.conversation_adapter,
                )
                with self.assertRaises(response_runtime.AdmissionError):
                    restarted.invoke(intent, b"Done")
                calls = json.loads(state_path.read_text())["calls"]
                self.assertFalse(
                    any(call["operation"] == "response_write" for call in calls)
                )

    def test_validation_interruption_requires_fresh_atomic_replacement(self):
        self.update_provider(
            lambda state: state.setdefault("queued", {}).update(
                {"POST graphql": [{"returncode": 1, "stderr": "HTTP 500"}]}
            )
        )
        intent = make_intent(self.epoch, self.epoch["sources"][0], "interrupted")
        interrupted = self.runtime.invoke(intent, b"Done")
        self.assertEqual(interrupted["pre_write_state"], "validation_indeterminate")
        with self.assertRaises(response_runtime.AdmissionError):
            self.restarted_runtime().invoke(intent, b"Done")

        basis = self.restarted_runtime().prepare_replacement("interrupted")
        successor = make_replacement_intent(basis, "after-interruption")
        result = self.restarted_runtime().invoke(successor, b"Done")
        self.assertEqual(result["status"], "confirmed_success")
        self.assertEqual(len(self.response_write_calls()), 1)

    def test_source_fix_requires_new_head_acquisition_before_authoring(self):
        self.update_provider(
            lambda state: state["graphql"]["data"]["repository"]["pullRequest"].update(
                {"headRefOid": "fixed-head"}
            )
        )
        old = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][0], "old"), b"Done"
        )
        self.assertEqual(old["status"], "confirmed_failure")

        basis = self.runtime.prepare_replacement("old")
        successor = make_replacement_intent(basis, "new")
        new = self.runtime.invoke(successor, b"Done")
        self.assertEqual(new["status"], "confirmed_success")

    def test_invalidated_intent_cannot_be_revived_by_carry_forward_evidence(self):
        new_comment = copy.deepcopy(
            json.loads(TYPED_FIXTURE.read_text(encoding="utf-8"))["data"]["repository"][
                "pullRequest"
            ]["comments"]["nodes"][0]
        )
        new_comment.update(
            {
                "id": "NODE_late_778",
                "databaseId": 778,
                "body": "Independent late feedback",
                "url": "https://github.com/base-owner/base-repo/pull/7#issuecomment-778",
            }
        )
        self.update_provider(
            lambda state: state["graphql"]["data"]["repository"]["pullRequest"][
                "comments"
            ]["nodes"].append(new_comment)
        )
        old_intent = make_intent(self.epoch, self.epoch["sources"][0])
        failed = self.runtime.invoke(old_intent, b"Done")
        self.assertEqual(failed["status"], "confirmed_failure")

        fresh = self.epoch_adapter.acquire("base-owner/base-repo", 7)
        carried = make_intent(fresh, fresh["sources"][0])
        with self.assertRaises(response_runtime.IntentConflict):
            self.runtime.invoke(carried, b"Done")
        carried["carry_forward"] = {
            "from_epoch_id": self.epoch["epoch_id"],
            "to_epoch": fresh,
            "independence_evidence": {
                "evidence_id": "independent-group-1",
                "assessment": "unchanged",
            },
        }
        with self.assertRaises(response_runtime.IntentConflict):
            self.runtime.invoke(carried, b"Done")
        self.assertEqual(self.response_write_calls(), [])

    def test_pending_intent_can_carry_forward_only_with_exact_unchanged_evidence(self):
        self.inject_store_failure("prewrite_validation_started")
        intent = make_intent(self.epoch, self.epoch["sources"][0], "pending")
        with self.assertRaises(response_outcome_store.OutcomeStoreError):
            self.runtime.invoke(intent, b"Done")
        self.runtime.store._fault_injector = None
        fresh = self.epoch_adapter.acquire("base-owner/base-repo", 7)
        carried = copy.deepcopy(intent)
        carried["carry_forward"] = {
            "from_epoch_id": self.epoch["epoch_id"],
            "to_epoch": fresh,
            "independence_evidence": {
                "evidence_id": "independent-pending-1",
                "assessment": "unchanged",
            },
        }

        result = self.restarted_runtime().invoke(carried, b"Done")

        self.assertEqual(result["status"], "confirmed_success")
        self.assertEqual(len(self.runtime.store.read("carry_forward")), 1)
        self.assertEqual(len(self.response_write_calls()), 1)

    def test_same_intent_reconciliation_credits_one_unique_exact_result(self):
        endpoint = "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
        self.update_provider(
            lambda state: state.setdefault("queued", {}).update(
                {endpoint: [{"returncode": 1, "stderr": "connection reset"}]}
            )
        )
        unknown = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][0]), b"Done"
        )
        self.assertEqual(unknown["status"], "unknown")

        def expose_result(state):
            pr = state["graphql"]["data"]["repository"]["pullRequest"]
            result = copy.deepcopy(
                pr["reviewThreads"]["nodes"][0]["comments"]["nodes"][1]
            )
            result.update(
                {
                    "id": "RESPONSE_node_950",
                    "databaseId": 950,
                    "body": "Done",
                    "author": {
                        "__typename": "User",
                        "id": "USER_ivan",
                        "login": "ivan",
                    },
                    "createdAt": "2026-09-02T00:00:00Z",
                    "updatedAt": "2026-09-02T00:00:00Z",
                    "url": "https://github.com/base-owner/base-repo/pull/7#discussion_r950",
                }
            )
            pr["reviewThreads"]["nodes"][0]["comments"]["nodes"].append(result)
            state.setdefault("objects", {})["950"] = {
                "id": 950,
                "node_id": "RESPONSE_node_950",
                "body": "Done",
                "html_url": result["url"],
                "user": {"login": "ivan"},
            }

        self.update_provider(expose_result)
        reread_known = self.runtime.inline_adapter.reread_known

        def assert_reserved_before_reread(**kwargs):
            identity = kwargs["response_identity"]
            typed = (
                identity["object_kind"],
                identity["database_id"],
                identity["node_id"],
            )
            history = self.runtime.store.semantic_history()
            self.assertIn(typed, history["identity_reservations"])
            return reread_known(**kwargs)

        self.runtime.inline_adapter.reread_known = assert_reserved_before_reread
        reconciled = self.runtime.reconcile("intent-1")

        self.assertEqual(reconciled["status"], "confirmed_success")
        self.assertEqual(reconciled["leaf_receipt"]["response"]["database_id"], 950)
        self.assertEqual(reconciled["reconciles_attempt_id"], unknown["attempt_id"])
        replay = self.restarted_runtime().invoke(
            make_intent(self.epoch, self.epoch["sources"][0]), b"Done"
        )
        history = self.runtime.store.semantic_history()
        self.assertEqual(replay["status"], "confirmed_no_op")
        self.assertEqual(replay["exact_replay_of"], reconciled["outcome_id"])
        self.assertEqual(
            history["current_attempt_by_intent"][reconciled["intent_id"]],
            unknown["attempt_id"],
        )
        self.assertEqual(
            history["effective_disposition_by_attempt"][unknown["attempt_id"]],
            "confirmed_success",
        )
        self.assertEqual(
            history["effective_outcome_by_attempt"][unknown["attempt_id"]],
            reconciled["outcome_id"],
        )
        self.assertEqual(
            history["effective_outcome_by_intent"][reconciled["intent_id"]],
            reconciled["outcome_id"],
        )
        claimed = reconciled["leaf_receipt"]["reread_response_identity"]
        claimed_identity = (
            claimed["object_kind"],
            claimed["database_id"],
            claimed["node_id"],
        )
        self.assertNotIn(claimed_identity, history["identity_reservations"])
        self.assertEqual(
            history["identity_owners"][claimed_identity], reconciled["intent_id"]
        )
        posts = self.response_write_calls()
        self.assertEqual(len(posts), 1)
        follow_up = make_intent(
            self.epoch, self.epoch["sources"][0], "reconciled-follow-up", b"More"
        )
        follow_up["intent_kind"] = "follow_up"
        follow_up["predecessor_outcome_id"] = reconciled["outcome_id"]
        followed = self.restarted_runtime().invoke(follow_up, b"More")
        self.assertEqual(followed["status"], "confirmed_success")
        self.assertEqual(followed["predecessor_outcome_id"], reconciled["outcome_id"])
        self.assertEqual(len(self.response_write_calls()), 2)

    def test_inline_thread_state_is_evidence_and_reply_never_changes_it(self):
        base_page = json.loads(TYPED_FIXTURE.read_text(encoding="utf-8"))
        fake = TEST_DIR / "fixtures/fake_gh.py"
        for resolved, outdated in (
            (False, False),
            (False, True),
            (True, False),
            (True, True),
        ):
            with self.subTest(resolved=resolved, outdated=outdated):
                root = Path(self.temporary.name) / f"state-{resolved}-{outdated}"
                root.mkdir()
                state_path = root / "provider.json"
                page = copy.deepcopy(base_page)
                thread = page["data"]["repository"]["pullRequest"]["reviewThreads"][
                    "nodes"
                ][0]
                thread["isResolved"] = resolved
                thread["isOutdated"] = outdated
                state_path.write_text(
                    json.dumps({"actor": "ivan", "next_id": 900, "graphql": page}),
                    encoding="utf-8",
                )
                transport = github_response_provider.GhJsonTransport(
                    [sys.executable, str(fake), str(state_path)]
                )
                epochs = github_response_provider.TypedEpochAdapter(transport)
                epoch = epochs.acquire("base-owner/base-repo", 7)
                runtime = response_runtime.ResponseRuntime(
                    state_directory=root / "ledger",
                    epoch_adapter=epochs,
                    inline_adapter=github_response_provider.InlineReplyAdapter(
                        transport
                    ),
                    conversation_adapter=github_response_provider.PullRequestConversationAdapter(
                        transport
                    ),
                )
                outcome = runtime.invoke(
                    make_intent(
                        epoch, epoch["sources"][0], f"state-{resolved}-{outdated}"
                    ),
                    b"Done",
                )
                self.assertEqual(outcome["status"], "confirmed_success")
                self.assertEqual(outcome["source"]["thread"]["is_resolved"], resolved)
                self.assertEqual(outcome["source"]["thread"]["is_outdated"], outdated)
                retained = json.loads(state_path.read_text(encoding="utf-8"))[
                    "graphql"
                ]["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"][0]
                self.assertEqual(retained["isResolved"], resolved)
                self.assertEqual(retained["isOutdated"], outdated)

    def test_concurrent_exact_invocations_serialize_to_one_write(self):
        intent = make_intent(self.epoch, self.epoch["sources"][0])
        queue = multiprocessing.Queue()
        ledger = self.runtime.store.directory
        processes = [
            multiprocessing.Process(
                target=concurrent_invoke,
                args=(self.provider_state, ledger, intent, b"Done", queue),
            )
            for _ in range(2)
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(10)
            self.assertEqual(process.exitcode, 0)
        results = sorted(queue.get(timeout=2) for _ in processes)

        self.assertEqual(
            results,
            [("ok", "confirmed_no_op"), ("ok", "confirmed_success")],
        )
        posts = self.response_write_calls()
        self.assertEqual(len(posts), 1)
        self.assertEqual(
            [item["status"] for item in self.runtime.read_outcomes()],
            ["confirmed_success"],
        )

    def test_unknown_freezes_its_scope_but_independent_source_can_proceed(self):
        endpoint = "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
        self.update_provider(
            lambda state: state.setdefault("queued", {}).update(
                {endpoint: [{"returncode": 1, "stderr": "connection reset"}]}
            )
        )
        unknown = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][0], "unknown"), b"Done"
        )
        source = self.epoch["sources"][2]
        body = f"Independent response {source['permalink']}".encode()
        independent = self.runtime.invoke(
            make_intent(self.epoch, source, "independent", body), body
        )

        self.assertEqual(unknown["status"], "unknown")
        self.assertEqual(independent["status"], "confirmed_success")

    def test_correlated_own_response_is_filtered_from_next_revalidation(self):
        first = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][0], "first"), b"Done"
        )
        response = first["leaf_receipt"]["response"]

        def expose_own_result(state):
            pr = state["graphql"]["data"]["repository"]["pullRequest"]
            own = copy.deepcopy(pr["reviewThreads"]["nodes"][0]["comments"]["nodes"][1])
            own.update(
                {
                    "id": response["node_id"],
                    "databaseId": response["database_id"],
                    "body": "Done",
                    "author": {
                        "__typename": "User",
                        "id": "USER_ivan",
                        "login": "ivan",
                    },
                    "url": response["permalink"],
                    "createdAt": "2026-09-02T00:00:00Z",
                    "updatedAt": "2026-09-02T00:00:00Z",
                }
            )
            pr["reviewThreads"]["nodes"][0]["comments"]["nodes"].append(own)

        self.update_provider(expose_own_result)
        second = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][1], "second", b"Other"),
            b"Other",
        )
        self.assertEqual(second["status"], "confirmed_success", second)

    def test_same_database_id_on_another_source_kind_is_not_filtered(self):
        first = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][0], "first"), b"Done"
        )
        self.assertEqual(first["leaf_receipt"]["response"]["database_id"], 900)

        def add_colliding_conversation_source(state):
            pr = state["graphql"]["data"]["repository"]["pullRequest"]
            collision = copy.deepcopy(pr["comments"]["nodes"][0])
            collision.update(
                {
                    "id": "NODE_conversation_collision",
                    "databaseId": 900,
                    "body": "New feedback with a cross-kind numeric collision",
                    "createdAt": "2026-09-03T00:00:00Z",
                    "updatedAt": "2026-09-03T00:00:00Z",
                    "url": "https://github.com/base-owner/base-repo/pull/7#issuecomment-900",
                }
            )
            pr["comments"]["nodes"].append(collision)

        self.update_provider(add_colliding_conversation_source)
        result = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][1], "second", b"Other"),
            b"Other",
        )

        self.assertEqual(result["status"], "confirmed_failure")
        self.assertIn("relevant feedback set changed", result["reason"])
        self.assertFalse(result["provider_call"])
        self.assertEqual(len(self.response_write_calls()), 1)

    def test_late_reviewer_reply_is_new_source_not_a_new_revision_of_the_root(self):
        first = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][0], "root"), b"Done"
        )
        self.assertEqual(first["status"], "confirmed_success")

        def add_reviewer_reply(state):
            comments = state["graphql"]["data"]["repository"]["pullRequest"][
                "reviewThreads"
            ]["nodes"][0]["comments"]["nodes"]
            reply = copy.deepcopy(comments[1])
            reply.update(
                {
                    "id": "NODE_inline_303",
                    "databaseId": 303,
                    "body": "New reviewer question",
                    "createdAt": "2026-09-03T00:00:00Z",
                    "updatedAt": "2026-09-03T00:00:00Z",
                    "url": "https://github.com/base-owner/base-repo/pull/7#discussion_r303",
                }
            )
            comments.append(reply)

        self.update_provider(add_reviewer_reply)
        fresh = self.epoch_adapter.acquire("base-owner/base-repo", 7)
        self.assertEqual(
            fresh["sources"][0]["source_revision"],
            self.epoch["sources"][0]["source_revision"],
        )
        with self.assertRaises(response_runtime.IntentConflict):
            self.runtime.invoke(
                make_intent(fresh, fresh["sources"][0], "root-again"), b"Done"
            )

        new_source = next(
            item
            for item in fresh["sources"]
            if item["provider_identity"]["database_id"] == 303
        )
        response = self.runtime.invoke(
            make_intent(fresh, new_source, "reviewer-reply", b"New answer"),
            b"New answer",
        )
        self.assertEqual(response["status"], "confirmed_success")

    def test_another_intents_equal_body_response_cannot_reconcile_unknown(self):
        endpoint = "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
        self.update_provider(
            lambda state: state.setdefault("queued", {}).update(
                {endpoint: [{"returncode": 1, "stderr": "connection reset"}]}
            )
        )
        body = b"Same response"
        unknown = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][0], "unknown-a", body),
            body,
        )
        successful = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][1], "successful-b", body),
            body,
        )
        response = successful["leaf_receipt"]["response"]

        def expose_b(state):
            pr = state["graphql"]["data"]["repository"]["pullRequest"]
            result = copy.deepcopy(
                pr["reviewThreads"]["nodes"][0]["comments"]["nodes"][1]
            )
            result.update(
                {
                    "id": response["node_id"],
                    "databaseId": response["database_id"],
                    "body": body.decode(),
                    "author": {
                        "__typename": "User",
                        "id": "USER_ivan",
                        "login": "ivan",
                    },
                    "createdAt": "2026-09-09T00:00:00Z",
                    "updatedAt": "2026-09-09T00:00:00Z",
                    "url": response["permalink"],
                }
            )
            pr["reviewThreads"]["nodes"][0]["comments"]["nodes"].append(result)

        self.update_provider(expose_b)
        reconciled = self.runtime.reconcile("unknown-a")

        self.assertEqual(unknown["status"], "unknown")
        self.assertEqual(reconciled["status"], "unknown")
        self.assertIn("does_not_prove_absence", reconciled["reason"])
        claims = self.runtime.store.semantic_history()["identity_owners"]
        expected = successful["leaf_receipt"]["reread_response_identity"]
        self.assertEqual(
            set(claims),
            {(expected["object_kind"], expected["database_id"], expected["node_id"])},
        )
        self.assertEqual(len(self.response_write_calls()), 2)

    def test_unexecuted_head_drift_admits_one_linked_fresh_adjudication(self):
        self.update_provider(
            lambda state: state["graphql"]["data"]["repository"]["pullRequest"].update(
                {"headRefOid": "fresh-head"}
            )
        )
        failed = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][0], "stale"), b"Done"
        )
        self.assertFalse(failed["provider_call"])
        basis = self.runtime.prepare_replacement("stale")
        successor = make_replacement_intent(basis, "fresh")

        result = self.runtime.invoke(successor, b"Done")

        intents = list(self.runtime.store.semantic_history()["intents"].values())
        self.assertEqual(result["status"], "confirmed_success")
        self.assertEqual(intents[0]["owner_id"], intents[1]["owner_id"])
        self.assertEqual(
            intents[1]["replacement_of_intent_id"], intents[0]["intent_id"]
        )
        records = self.runtime.store.records()
        self.assertEqual(
            [item["record_kind"] for item in records].count("prewrite_invalidated"),
            1,
        )
        self.assertEqual(
            [item["record_kind"] for item in records].count("replacement_transition"),
            1,
        )
        self.assertEqual(len(self.response_write_calls()), 1)

    def test_post_terminal_basis_precedes_authored_replacement_and_is_single_use(self):
        original_head = self.epoch["pull_request"]["head_oid"]
        self.update_provider(
            lambda state: state["graphql"]["data"]["repository"]["pullRequest"].update(
                {"headRefOid": "drifted-head"}
            )
        )
        stale = make_intent(self.epoch, self.epoch["sources"][0], "stale")
        failed = self.runtime.invoke(stale, b"Done")
        self.assertEqual(failed["pre_write_state"], "invalidated_unexecuted")
        self.update_provider(
            lambda state: state["graphql"]["data"]["repository"]["pullRequest"].update(
                {"headRefOid": original_head}
            )
        )

        basis = self.restarted_runtime().prepare_replacement("stale")
        successor = make_replacement_intent(basis, body=b"Done")
        result = self.restarted_runtime().invoke(successor, b"Done")

        self.assertEqual(result["status"], "confirmed_success")
        self.assertNotEqual(basis["successor_epoch_id"], self.epoch["epoch_id"])
        records = self.runtime.store.records()
        kinds = [record["record_kind"] for record in records]
        self.assertLess(
            kinds.index("prewrite_invalidated"), kinds.index("replacement_basis")
        )
        self.assertLess(
            kinds.index("replacement_basis"), kinds.index("replacement_transition")
        )
        calls_before = list(self.provider_calls())
        with self.assertRaises(response_runtime.AdmissionError):
            self.restarted_runtime().invoke(
                make_replacement_intent(basis, key="competing", body=b"Done"),
                b"Done",
            )
        self.assertEqual(self.provider_calls(), calls_before)

    def test_replacement_rejects_old_route_and_invalid_artifacts_before_provider(self):
        self.update_provider(
            lambda state: state["graphql"]["data"]["repository"]["pullRequest"].update(
                {"headRefOid": "replacement-head"}
            )
        )
        old = make_intent(self.epoch, self.epoch["sources"][0], "old-route")
        self.runtime.invoke(old, b"Done")
        basis = self.runtime.prepare_replacement("old-route")
        predecessor = self.runtime.store.semantic_history()["intents"][
            self.runtime.store.semantic_history()["keys"]["old-route"]
        ]
        old_shape = make_intent(
            basis["successor_epoch"], basis["successor_source"], "old-shape"
        )
        old_shape["replacement_adjudication"] = {
            "invalidated_intent_id": predecessor["intent_id"],
            "drift_evidence_id": "renamed-label",
        }
        calls_before = list(self.provider_calls())
        with self.assertRaises(response_runtime.AdmissionError):
            self.runtime.invoke(old_shape, b"Done")
        self.assertEqual(self.provider_calls(), calls_before)

        invalid = []
        extra_wrapper = make_replacement_intent(basis, "extra-wrapper")
        extra_wrapper["classification_artifact"]["extra"] = True
        invalid.append(extra_wrapper)
        extra_decoded = make_replacement_intent(basis, "extra-decoded")
        classification = decoded_artifact(extra_decoded["classification_artifact"])
        classification["extra"] = True
        extra_decoded["classification_artifact"] = exact_artifact(classification)
        invalid.append(extra_decoded)
        wrong_basis = make_replacement_intent(basis, "wrong-basis")
        classification = decoded_artifact(wrong_basis["classification_artifact"])
        classification["replacement_basis_id"] = "0" * 64
        wrong_basis["classification_artifact"] = exact_artifact(classification)
        invalid.append(wrong_basis)
        wrong_cross_digest = make_replacement_intent(basis, "wrong-cross-digest")
        adjudication = decoded_artifact(wrong_cross_digest["adjudication_artifact"])
        adjudication["classification_artifact_sha256"] = "0" * 64
        wrong_cross_digest["adjudication_artifact"] = exact_artifact(adjudication)
        invalid.append(wrong_cross_digest)
        noncanonical = make_replacement_intent(basis, "noncanonical")
        value = decoded_artifact(noncanonical["classification_artifact"])
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
        noncanonical["classification_artifact"] = {
            "canonical_utf8_base64": base64.b64encode(raw).decode("ascii"),
            "byte_length": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        invalid.append(noncanonical)
        for candidate in invalid:
            with self.subTest(key=candidate["intent_key"]):
                calls_before = list(self.provider_calls())
                with self.assertRaises(response_runtime.AdmissionError):
                    self.runtime.invoke(candidate, b"Done")
                self.assertEqual(self.provider_calls(), calls_before)
        calls_before = list(self.provider_calls())
        with self.assertRaises(response_runtime.AdmissionError):
            self.runtime.invoke(
                make_replacement_intent(basis, "wrong-body", b"Done"), b"Other"
            )
        self.assertEqual(self.provider_calls(), calls_before)
        accepted = self.runtime.invoke(
            make_replacement_intent(basis, "accepted", b"Done"), b"Done"
        )
        self.assertEqual(accepted["status"], "confirmed_success")

    def test_only_latest_unsuperseded_replacement_basis_can_be_consumed(self):
        self.update_provider(
            lambda state: state["graphql"]["data"]["repository"]["pullRequest"].update(
                {"headRefOid": "replacement-head"}
            )
        )
        self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][0], "superseded"), b"Done"
        )
        first = self.runtime.prepare_replacement("superseded")
        second = self.restarted_runtime().prepare_replacement("superseded")
        self.assertEqual(second["supersedes_basis_id"], first["basis_id"])
        calls_before = list(self.provider_calls())
        with self.assertRaises(response_runtime.AdmissionError):
            self.runtime.invoke(make_replacement_intent(first, "stale-basis"), b"Done")
        self.assertEqual(self.provider_calls(), calls_before)
        old_artifacts = make_replacement_intent(first, "old-artifacts")
        old_artifacts["replacement_basis_id"] = second["basis_id"]
        with self.assertRaises(response_runtime.AdmissionError):
            self.runtime.invoke(old_artifacts, b"Done")
        self.assertEqual(self.provider_calls(), calls_before)
        accepted = self.runtime.invoke(
            make_replacement_intent(second, "current-basis"), b"Done"
        )
        self.assertEqual(accepted["status"], "confirmed_success")

    def test_post_basis_drift_families_terminalize_successor_and_reversion_cannot_revive(
        self,
    ):
        def mutate_head(state):
            state["graphql"]["data"]["repository"]["pullRequest"]["headRefOid"] = (
                "after-basis-head"
            )

        def mutate_source(state):
            source = state["graphql"]["data"]["repository"]["pullRequest"][
                "reviewThreads"
            ]["nodes"][0]["comments"]["nodes"][0]
            source["body"] = "after-basis-source"
            source["updatedAt"] = "2026-09-10T00:00:00Z"

        def mutate_thread(state):
            state["graphql"]["data"]["repository"]["pullRequest"]["reviewThreads"][
                "nodes"
            ][0]["isResolved"] = True

        def mutate_comments(state):
            comment = copy.deepcopy(
                state["graphql"]["data"]["repository"]["pullRequest"]["comments"][
                    "nodes"
                ][0]
            )
            comment["id"] = "LATE_COMMENT"
            comment["databaseId"] = 987
            comment["body"] = "late feedback"
            state["graphql"]["data"]["repository"]["pullRequest"]["comments"][
                "nodes"
            ].append(comment)

        for name, mutate in (
            ("head", mutate_head),
            ("source", mutate_source),
            ("thread", mutate_thread),
            ("comments", mutate_comments),
        ):
            with self.subTest(drift=name):
                state_path, _, runtime, epoch = self.isolated_runtime(f"basis-{name}")
                state = json.loads(state_path.read_text(encoding="utf-8"))
                state["graphql"]["data"]["repository"]["pullRequest"]["headRefOid"] = (
                    "terminal-head"
                )
                state_path.write_text(json.dumps(state), encoding="utf-8")
                runtime.invoke(make_intent(epoch, epoch["sources"][0], "old"), b"Done")
                basis = runtime.prepare_replacement("old")
                prepared_state = state_path.read_bytes()
                state = json.loads(prepared_state)
                mutate(state)
                state_path.write_text(json.dumps(state), encoding="utf-8")
                successor = make_replacement_intent(basis, "successor")
                blocked = runtime.invoke(successor, b"Done")
                self.assertEqual(blocked["pre_write_state"], "invalidated_unexecuted")
                state_path.write_bytes(prepared_state)
                with self.assertRaises(response_runtime.AdmissionError):
                    runtime.invoke(successor, b"Done")
                calls = json.loads(state_path.read_text(encoding="utf-8"))["calls"]
                self.assertFalse(
                    any(call["operation"] == "response_write" for call in calls)
                )

    def test_replacement_writer_artifact_preserves_exact_body_bytes(self):
        bodies = (
            b"LF\n",
            b"CRLF\r\n",
            "Unicode: café".encode(),
            b"terminal-newline\n",
            b"no-terminal-newline",
        )
        for index, body in enumerate(bodies):
            with self.subTest(index=index):
                state_path, _, runtime, epoch = self.isolated_runtime(
                    f"replacement-bytes-{index}"
                )
                state = json.loads(state_path.read_text(encoding="utf-8"))
                state["graphql"]["data"]["repository"]["pullRequest"]["headRefOid"] = (
                    "replacement-head"
                )
                state_path.write_text(json.dumps(state), encoding="utf-8")
                runtime.invoke(
                    make_intent(epoch, epoch["sources"][0], "old", body), body
                )
                basis = runtime.prepare_replacement("old")
                outcome = runtime.invoke(
                    make_replacement_intent(basis, "new", body), body
                )
                self.assertEqual(outcome["status"], "confirmed_success")
                self.assertEqual(
                    base64.b64decode(
                        outcome["leaf_receipt"]["request_body_utf8_base64"]
                    ),
                    body,
                )
                state = json.loads(state_path.read_text(encoding="utf-8"))
                writes = [
                    call
                    for call in state["calls"]
                    if call["operation"] == "response_write"
                ]
                self.assertEqual(
                    [call["request"]["body"].encode("utf-8") for call in writes],
                    [body],
                )

    def test_write_started_permanently_blocks_fresh_adjudication(self):
        endpoint = "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
        self.update_provider(
            lambda state: state.setdefault("queued", {}).update(
                {endpoint: [{"returncode": 1, "stderr": "HTTP 422"}]}
            )
        )
        failed = self.runtime.invoke(
            make_intent(self.epoch, self.epoch["sources"][0], "attempted"), b"Done"
        )
        with self.assertRaises(response_runtime.AdmissionError):
            self.runtime.prepare_replacement("attempted")

        self.assertEqual(failed["status"], "confirmed_failure")
        self.assertFalse(failed["retryable"])
        self.assertEqual(len(self.response_write_calls()), 1)

    def test_missing_atomic_resolution_keeps_historical_drift_unknown(self):
        base = json.loads(TYPED_FIXTURE.read_text(encoding="utf-8"))
        drift = copy.deepcopy(base)
        drift["data"]["repository"]["pullRequest"]["headRefOid"] = "drifted-head"
        self.update_provider(
            lambda state: state.setdefault("queued", {}).update(
                {
                    "POST graphql": [
                        {"returncode": 0, "json": base},
                        {"returncode": 0, "json": drift},
                    ]
                }
            )
        )
        self.inject_store_failure("attempt_resolution")
        with self.assertRaises(response_runtime.SemanticPersistenceIncomplete):
            self.runtime.invoke(
                make_intent(self.epoch, self.epoch["sources"][0], "missing-leaf"),
                b"Done",
            )
        self.runtime.store._fault_injector = None

        def restore_and_expose(state):
            state["graphql"] = copy.deepcopy(base)
            pr = state["graphql"]["data"]["repository"]["pullRequest"]
            result = copy.deepcopy(
                pr["reviewThreads"]["nodes"][0]["comments"]["nodes"][1]
            )
            result.update(
                {
                    "id": "RESPONSE_node_900",
                    "databaseId": 900,
                    "body": "Done",
                    "author": {
                        "__typename": "User",
                        "id": "USER_ivan",
                        "login": "ivan",
                    },
                    "createdAt": "2026-09-09T00:00:00Z",
                    "updatedAt": "2026-09-09T00:00:00Z",
                    "url": "https://github.com/example/repo/pull/7#response-900",
                }
            )
            pr["reviewThreads"]["nodes"][0]["comments"]["nodes"].append(result)

        self.update_provider(restore_and_expose)
        reconciled = self.restarted_runtime().reconcile("missing-leaf")

        self.assertEqual(reconciled["status"], "confirmed_success")
        self.assertEqual(reconciled["post_write_drift_assessment"]["state"], "unknown")
        self.assertEqual(len(self.response_write_calls()), 1)

    def test_write_started_publication_faults_precede_every_provider_call(self):
        for step, context in (
            ("flock", "bundle_lock"),
            ("staging_create", "write_started"),
            ("staging_write_each_prefix", "write_started"),
            ("fchmod", "write_started"),
            ("file_fsync", "write_started"),
            ("staging_close", "write_started"),
            ("hard_link_no_replace", "write_started"),
            ("sync_directory_open", "write_started"),
            ("directory_fsync", "write_started"),
            ("directory_close", "write_started"),
        ):
            with self.subTest(step=step):
                root = Path(self.temporary.name) / f"fault-{step}"

                expected_context = context
                expected_step = step

                def inject(
                    actual_step,
                    context,
                    expected=expected_step,
                    expected_context_value=expected_context,
                ):
                    if actual_step == expected and context == expected_context_value:
                        raise OSError(f"injected {expected}")

                store = response_outcome_store.ResponseOutcomeStore(
                    root, fault_injector=inject
                )
                runtime = response_runtime.ResponseRuntime(
                    state_directory=root,
                    outcome_store=store,
                    epoch_adapter=self.epoch_adapter,
                    inline_adapter=self.runtime.inline_adapter,
                    conversation_adapter=self.runtime.conversation_adapter,
                )
                before = len(self.response_write_calls())
                with self.assertRaisesRegex(
                    response_outcome_store.OutcomeStoreError,
                    "storage-capability-failure",
                ):
                    runtime.invoke(
                        make_intent(
                            self.epoch,
                            self.epoch["sources"][0],
                            f"fault-{step}",
                        ),
                        b"Done",
                    )
                self.assertEqual(len(self.response_write_calls()), before)
                if step in {
                    "sync_directory_open",
                    "directory_fsync",
                    "directory_close",
                }:
                    store._fault_injector = None
                    restarted = response_runtime.ResponseRuntime(
                        state_directory=root,
                        outcome_store=store,
                        epoch_adapter=self.epoch_adapter,
                        inline_adapter=self.runtime.inline_adapter,
                        conversation_adapter=self.runtime.conversation_adapter,
                    )
                    self.assertEqual(len(store.read("write_started")), 1)
                    with self.assertRaises(response_runtime.ReconciliationRequired):
                        restarted.invoke(
                            make_intent(
                                self.epoch,
                                self.epoch["sources"][0],
                                "directory-sync-bypass",
                            ),
                            b"Done",
                        )
                    self.assertEqual(len(self.response_write_calls()), before)

    def test_legacy_stream_is_preserved_and_rejected_before_provider_use(self):
        ledger = Path(self.temporary.name) / "legacy-ledger"
        ledger.mkdir()
        legacy = ledger / "attempts.jsonl"
        legacy.write_bytes(b'{}\n{"torn":')
        before = legacy.read_bytes()
        runtime = response_runtime.ResponseRuntime(
            state_directory=ledger,
            epoch_adapter=self.epoch_adapter,
            inline_adapter=self.runtime.inline_adapter,
            conversation_adapter=self.runtime.conversation_adapter,
        )

        with self.assertRaisesRegex(
            response_outcome_store.OutcomeStoreError,
            "unsupported-development-format",
        ):
            runtime.invoke(
                make_intent(self.epoch, self.epoch["sources"][0], "legacy"),
                b"Done",
            )

        self.assertEqual(legacy.read_bytes(), before)
        self.assertFalse(runtime.store.lock_path.exists())
        self.assertEqual(self.response_write_calls(), [])


if __name__ == "__main__":
    unittest.main()
