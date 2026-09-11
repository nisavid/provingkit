import base64
import copy
import json
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

TEST_DIR = Path(__file__).resolve().parent
REPOSITORY = Path(__file__).resolve().parents[4]
SKILL_DIR = REPOSITORY / "plugins/mergecraft/skills/addressing-pr-review-feedback"
sys.path.insert(0, str(SKILL_DIR / "scripts"))
RESPONSE_SKILL_DIR = (
    REPOSITORY / "plugins/mergecraft/skills/interacting-with-pr-review-feedback"
)
sys.path.insert(0, str(RESPONSE_SKILL_DIR / "scripts"))

import response_outcome_store
import review_feedback_state


def fixture():
    return json.loads(
        (TEST_DIR / "fixtures" / "typed_feedback_epoch.json").read_text(
            encoding="utf-8"
        )
    )


def repeated_pages():
    first = fixture()
    second = copy.deepcopy(first)
    first_pr = first["data"]["repository"]["pullRequest"]
    second_pr = second["data"]["repository"]["pullRequest"]
    for index, field in enumerate(
        ("reviewThreads", "comments", "reviews", "reviewRequests")
    ):
        first_pr[field]["pageInfo"] = {
            "hasNextPage": True,
            "endCursor": f"cursor-{index}",
        }
        second_pr[field]["pageInfo"] = {
            "hasNextPage": False,
            "endCursor": f"terminal-{index}",
        }
    first_pr["statusCheckRollup"]["contexts"]["pageInfo"] = {
        "hasNextPage": True,
        "endCursor": "cursor-checks",
    }
    second_pr["statusCheckRollup"]["contexts"]["pageInfo"] = {
        "hasNextPage": False,
        "endCursor": "terminal-checks",
    }
    return first, second


class TypedFeedbackEpochTests(unittest.TestCase):
    def test_empty_submitted_review_is_retained_as_metadata_and_runtime_valid(self):
        page = fixture()
        reviews = page["data"]["repository"]["pullRequest"]["reviews"]["nodes"]
        empty_review = copy.deepcopy(reviews[0])
        empty_review.update(
            {
                "id": "REVIEW_node_52",
                "databaseId": 52,
                "url": "https://github.com/base-owner/base-repo/pull/7#pullrequestreview-52",
                "body": "",
                "state": "APPROVED",
            }
        )
        reviews.append(empty_review)

        epoch = review_feedback_state.typed_epoch_from_pages(
            "base-owner/base-repo", [page], pr_number=7
        )
        empty_observation = next(
            observation
            for observation in epoch["observations"]
            if observation["provider_identity"]["database_id"] == 52
        )

        self.assertEqual(empty_observation["body"]["utf8_base64"], "")
        self.assertEqual(empty_observation["body"]["byte_length"], 0)
        self.assertNotIn(empty_observation, epoch["sources"])
        self.assertTrue(
            all(
                base64.b64decode(source["body"]["utf8_base64"]).strip()
                for source in epoch["sources"]
            )
        )
        self.assertIs(
            response_outcome_store.validate_epoch(
                epoch, "producer-consumer-empty-review"
            ),
            epoch,
        )
        invalid_epoch = copy.deepcopy(epoch)
        invalid_epoch["sources"].append(copy.deepcopy(empty_observation))
        with self.assertRaisesRegex(
            response_outcome_store.OutcomeStoreError,
            "source.body.utf8_base64 must be nonempty text",
        ):
            response_outcome_store.validate_epoch(
                invalid_epoch, "producer-consumer-empty-source"
            )

    def test_real_acquisition_trace_retains_the_cursor_sent_with_each_request(self):
        first, second = repeated_pages()
        responses = iter((first, second))
        requests = []

        def graphql(_query, variables):
            requests.append(copy.deepcopy(variables))
            return next(responses)

        with mock.patch.object(
            review_feedback_state, "run_gh_graphql", side_effect=graphql
        ):
            pages = review_feedback_state.fetch_pages("base-owner/base-repo", 7)
        epoch = review_feedback_state.typed_epoch_from_pages(
            "base-owner/base-repo", pages, pr_number=7
        )

        self.assertEqual(len(requests), 2)
        variable_names = {
            "threads": "threadsCursor",
            "comments": "commentsCursor",
            "reviews": "reviewsCursor",
            "checks": "checksCursor",
            "review_requests": "reviewRequestsCursor",
        }
        for name, collection in epoch["pagination_evidence"]["collections"].items():
            self.assertIsNone(collection["pages"][0]["request_cursor"])
            self.assertEqual(
                collection["pages"][1]["request_cursor"],
                requests[1][variable_names[name]],
            )

    def test_acquires_each_nonempty_typed_text_object_without_coalescing(self):
        epoch = review_feedback_state.typed_epoch_from_pages(
            "base-owner/base-repo", [fixture()], pr_number=7
        )

        self.assertEqual(epoch["schema_version"], 1)
        self.assertEqual(
            epoch["repository"]["provider_identity"],
            {"database_id": 77, "node_id": "REPO_node_77"},
        )
        self.assertEqual(epoch["pull_request"]["node_id"], "PR_node_7")
        self.assertEqual(
            epoch["acquisition_start_observation"]["kind"],
            "local_acquisition_observation",
        )
        self.assertEqual(
            epoch["acquisition_end_observation"]["kind"],
            "local_acquisition_observation",
        )
        self.assertTrue(epoch["pagination_evidence"]["complete"])
        self.assertEqual(
            set(epoch["pagination_evidence"]["collections"]),
            {"threads", "comments", "reviews", "checks", "review_requests"},
        )
        for collection in epoch["pagination_evidence"]["collections"].values():
            self.assertIsNone(collection["pages"][0]["request_cursor"])
            self.assertEqual(
                collection["node_count"],
                sum(page["node_count"] for page in collection["pages"]),
            )
        self.assertEqual(
            [source["kind"] for source in epoch["sources"]],
            [
                "inline_review_comment",
                "inline_review_comment",
                "pr_conversation_comment",
                "submitted_review_body",
            ],
        )
        inline = epoch["sources"][0]
        self.assertEqual(inline["provider_identity"]["database_id"], 301)
        self.assertEqual(inline["thread"]["root_comment_database_id"], 301)
        self.assertEqual(inline["review"]["node_id"], "REVIEW_node_51")
        self.assertEqual(inline["associated_revision"]["oid"], "review-sha")
        self.assertEqual(inline["original_revision"]["oid"], "original-review-sha")
        self.assertEqual(inline["state"]["value"], "SUBMITTED")
        self.assertFalse(inline["state"]["outdated"])
        self.assertEqual(inline["location"]["subject_type"], "LINE")
        self.assertEqual(inline["location"]["original_position"], 5)
        self.assertEqual(inline["thread"]["diff_side"], "RIGHT")
        self.assertEqual(inline["thread"]["original_start_line"], 10)
        self.assertEqual(inline["author"]["association"], "NONE")
        self.assertEqual(inline["reply_to"]["availability"], "unavailable")
        self.assertEqual(inline["reply_to"]["reason"], "thread_root")
        self.assertEqual(
            epoch["sources"][1]["reply_to"],
            {
                "availability": "available",
                "node_id": "NODE_inline_301",
                "database_id": 301,
            },
        )
        self.assertEqual(
            base64.b64decode(inline["body"]["utf8_base64"]), b"Inline root"
        )
        self.assertEqual(inline["body"]["byte_length"], len(b"Inline root"))
        self.assertEqual(
            inline["source_revision_identity"]["associated_commit"]["oid"],
            "review-sha",
        )
        self.assertEqual(epoch["sources"][1]["provider_identity"]["database_id"], 302)
        self.assertEqual(epoch["sources"][3]["provider_identity"]["database_id"], 51)
        self.assertEqual(epoch["sources"][3]["created_at"], "2026-09-01T08:58:00Z")
        self.assertEqual(
            epoch["sources"][3]["submitted_at"],
            {"availability": "available", "value": "2026-09-01T09:03:00Z"},
        )
        self.assertNotEqual(
            epoch["sources"][0]["source_revision"],
            epoch["sources"][1]["source_revision"],
        )

    def test_resolved_and_outdated_are_retained_as_evidence(self):
        page = fixture()
        thread = page["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"][0]
        thread["isResolved"] = True
        thread["isOutdated"] = True
        for comment in thread["comments"]["nodes"]:
            comment["outdated"] = True

        epoch = review_feedback_state.typed_epoch_from_pages(
            "base-owner/base-repo", [page], pr_number=7
        )

        self.assertTrue(epoch["sources"][0]["thread"]["is_resolved"])
        self.assertTrue(epoch["sources"][0]["thread"]["is_outdated"])

    def test_context_drift_does_not_manufacture_a_new_source_revision(self):
        base = review_feedback_state.typed_epoch_from_pages(
            "base-owner/base-repo", [fixture()], pr_number=7
        )
        changed_page = fixture()
        thread = changed_page["data"]["repository"]["pullRequest"]["reviewThreads"][
            "nodes"
        ][0]
        thread["isResolved"] = True
        changed = review_feedback_state.typed_epoch_from_pages(
            "base-owner/base-repo", [changed_page], pr_number=7
        )
        self.assertEqual(
            base["sources"][0]["source_revision"],
            changed["sources"][0]["source_revision"],
        )
        self.assertNotEqual(
            base["sources"][0]["thread"], changed["sources"][0]["thread"]
        )

    def test_legacy_orientation_remains_readable_but_not_response_admissible(self):
        legacy = json.loads(
            (TEST_DIR / "fixtures" / "outdated_thread.json").read_text(encoding="utf-8")
        )
        state = review_feedback_state.state_from_pages(
            "base-owner/base-repo", [legacy], pr_number=7
        )
        self.assertEqual(state["schema_version"], 2)

        with self.assertRaisesRegex(
            review_feedback_state.ResponseShapeError, "strict response evidence"
        ):
            review_feedback_state.typed_epoch_from_pages(
                "base-owner/base-repo", [legacy], pr_number=7
            )

    def test_typed_identity_is_never_recovered_from_permalink_or_body(self):
        page = copy.deepcopy(fixture())
        comment = page["data"]["repository"]["pullRequest"]["comments"]["nodes"][0]
        del comment["id"]
        comment["body"] += " NODE_conversation_401"
        comment["url"] += "?id=NODE_conversation_401"

        with self.assertRaisesRegex(
            review_feedback_state.ResponseShapeError, "strict response evidence"
        ):
            review_feedback_state.typed_epoch_from_pages(
                "base-owner/base-repo", [page], pr_number=7
            )

    def test_query_requests_stable_typed_response_evidence(self):
        query, _ = review_feedback_state.build_pr_query(
            "base-owner/base-repo", 7, cursors={}
        )

        for field in (
            "databaseId",
            "updatedAt",
            "pullRequestReview",
            "commit { oid }",
            "state",
            "replyTo { id databaseId }",
            "outdated",
            "originalCommit { oid }",
            "originalPosition",
            "originalStartLine",
            "subjectType",
            "diffSide",
            "startDiffSide",
            "createdAt",
            "submittedAt",
        ):
            with self.subTest(field=field):
                self.assertIn(field, query)

        compact = " ".join(query.split())
        self.assertIn(
            "repository(owner: $owner, name: $name) { id databaseId",
            compact,
        )
        self.assertIn(
            "fragment ActorIdentity on Actor { __typename login ... on Node { id } }",
            compact,
        )
        self.assertIsNone(re.search(r"author\s*\{[^}]*\bid\b", query))

    def test_repository_identity_fields_exist_in_verified_public_schema(self):
        schema = json.loads(
            (TEST_DIR / "fixtures" / "github_schema_fields.json").read_text(
                encoding="utf-8"
            )
        )
        repository = next(
            item for item in schema["types"] if item["name"] == "Repository"
        )
        field_types = {field["name"]: field["type"] for field in repository["fields"]}

        self.assertEqual(
            repository["capture_sha256"],
            "ad360cc48bc1c9e745b1e13f0010a4c76684467e07d45152172d39f9ea5904f5",
        )
        self.assertEqual(
            field_types,
            {
                "databaseId": {
                    "kind": "SCALAR",
                    "name": "Int",
                    "ofType": None,
                },
                "id": {
                    "kind": "NON_NULL",
                    "name": None,
                    "ofType": {
                        "kind": "SCALAR",
                        "name": "ID",
                        "ofType": None,
                    },
                },
            },
        )

    def test_selected_source_fields_exist_in_captured_public_schema(self):
        schema = json.loads(
            (TEST_DIR / "fixtures" / "github_schema_fields.json").read_text()
        )
        schema_fields = {
            item["name"]: {field["name"] for field in item.get("fields", [])}
            for item in schema["types"]
        }

        for (
            type_name,
            selected_fields,
        ) in review_feedback_state.ACQUISITION_FIELD_CONTRACT.items():
            with self.subTest(type_name=type_name):
                self.assertLessEqual(set(selected_fields), schema_fields[type_name])

        actor_possible = next(
            item for item in schema["types"] if item["name"] == "Actor"
        )["possibleTypes"]
        node_possible = {
            item["name"]
            for item in next(
                item for item in schema["types"] if item["name"] == "Node"
            )["possibleTypes"]
        }
        self.assertLessEqual({item["name"] for item in actor_possible}, node_possible)

    def test_thread_pagination_query_uses_the_same_strict_comment_fragment(self):
        query, variables = review_feedback_state.build_thread_comments_query(
            "THREAD_node_21", "cursor-1"
        )
        compact = " ".join(query.split())

        self.assertIn(
            "nodes { ...ReviewCommentEvidence }",
            compact,
        )
        self.assertIn(
            "fragment ActorIdentity on Actor { __typename login ... on Node { id } }",
            compact,
        )
        self.assertIn("replyTo { id databaseId }", compact)
        self.assertIn("originalCommit { oid }", compact)
        self.assertEqual(
            variables,
            {"threadId": "THREAD_node_21", "commentsCursor": "cursor-1"},
        )

    def test_pending_review_body_remains_metadata_not_a_submitted_source(self):
        page = fixture()
        review = page["data"]["repository"]["pullRequest"]["reviews"]["nodes"][0]
        review.update(
            {
                "state": "PENDING",
                "body": "Draft only",
                "submittedAt": None,
                "commit": None,
            }
        )

        epoch = review_feedback_state.typed_epoch_from_pages(
            "base-owner/base-repo", [page], pr_number=7
        )

        self.assertNotIn(
            "submitted_review_body", [source["kind"] for source in epoch["sources"]]
        )
        pending = epoch["observations"][-1]
        self.assertEqual(pending["state"]["value"], "PENDING")
        self.assertEqual(pending["created_at"], "2026-09-01T08:58:00Z")
        self.assertEqual(pending["submitted_at"]["availability"], "unavailable")

    def test_pending_and_empty_inline_comments_remain_metadata_only(self):
        page = fixture()
        comments = page["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"][
            0
        ]["comments"]["nodes"]
        comments[0]["state"] = "PENDING"
        comments[0]["pullRequestReview"] = None
        comments[1]["body"] = "  \n"

        epoch = review_feedback_state.typed_epoch_from_pages(
            "base-owner/base-repo", [page], pr_number=7
        )

        self.assertEqual(
            [source["kind"] for source in epoch["sources"]],
            ["pr_conversation_comment", "submitted_review_body"],
        )
        self.assertEqual(epoch["observations"][0]["state"]["value"], "PENDING")
        self.assertEqual(
            epoch["observations"][0]["review"]["availability"], "unavailable"
        )

    def test_deleted_author_and_unavailable_revision_are_preserved(self):
        page = fixture()
        comment = page["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"][
            0
        ]["comments"]["nodes"][0]
        comment["author"] = None
        comment["commit"] = None
        comment["originalCommit"] = None

        epoch = review_feedback_state.typed_epoch_from_pages(
            "base-owner/base-repo", [page], pr_number=7
        )

        source = epoch["sources"][0]
        self.assertEqual(source["author"]["reason"], "provider_returned_null")
        self.assertEqual(
            source["associated_revision"],
            {"availability": "unavailable", "reason": "provider_returned_null"},
        )
        self.assertEqual(
            source["original_revision"],
            {"availability": "unavailable", "reason": "provider_returned_null"},
        )

    def test_omitted_nullable_field_is_not_treated_as_provider_null(self):
        page = fixture()
        comment = page["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"][
            0
        ]["comments"]["nodes"][0]
        del comment["originalCommit"]

        with self.assertRaisesRegex(
            review_feedback_state.ResponseShapeError, "originalCommit"
        ):
            review_feedback_state.typed_epoch_from_pages(
                "base-owner/base-repo", [page], pr_number=7
            )

    def test_contradictory_inline_root_and_review_associations_fail_closed(self):
        page = fixture()
        comments = page["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"][
            0
        ]["comments"]["nodes"]
        comments[1]["replyTo"] = {
            "id": "NODE_not_the_root",
            "databaseId": 999,
        }

        with self.assertRaisesRegex(
            review_feedback_state.ResponseShapeError, "replyTo.*thread root"
        ):
            review_feedback_state.typed_epoch_from_pages(
                "base-owner/base-repo", [page], pr_number=7
            )

        page = fixture()
        review = page["data"]["repository"]["pullRequest"]["reviews"]["nodes"][0]
        review["submittedAt"] = None
        with self.assertRaisesRegex(
            review_feedback_state.ResponseShapeError, "submittedAt"
        ):
            review_feedback_state.typed_epoch_from_pages(
                "base-owner/base-repo", [page], pr_number=7
            )

    def test_inline_review_and_placement_must_match_containing_objects(self):
        page = fixture()
        comment = page["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"][
            0
        ]["comments"]["nodes"][0]
        comment["pullRequestReview"]["databaseId"] = 999

        with self.assertRaisesRegex(
            review_feedback_state.ResponseShapeError, "review association"
        ):
            review_feedback_state.typed_epoch_from_pages(
                "base-owner/base-repo", [page], pr_number=7
            )

    def test_epoch_registry_deduplicates_exact_page_boundary_objects(self):
        epoch = review_feedback_state.typed_epoch_from_pages(
            "base-owner/base-repo", list(repeated_pages()), pr_number=7
        )

        self.assertEqual(len(epoch["sources"]), 4)
        self.assertRegex(epoch["identity_registry_digest"], r"^[0-9a-f]{64}$")
        thread = next(
            item
            for item in epoch["identity_registry"]
            if item["object_kind"] == "PullRequestReviewThread"
        )
        self.assertEqual(
            thread["database_id"],
            {
                "availability": "unavailable",
                "reason": "not_exposed_by_public_schema",
            },
        )

    def test_epoch_admission_rejects_repository_node_id_drift(self):
        first, second = repeated_pages()
        second["data"]["repository"]["id"] = "REPO_node_other"

        with self.assertRaisesRegex(
            review_feedback_state.IdentityError,
            "repository drifted from first-page identity: node_id",
        ):
            review_feedback_state.typed_epoch_from_pages(
                "base-owner/base-repo", [first, second], pr_number=7
            )

    def test_epoch_admission_rejects_repository_database_id_drift(self):
        first, second = repeated_pages()
        second["data"]["repository"]["databaseId"] = 999

        with self.assertRaisesRegex(
            review_feedback_state.IdentityError,
            "repository drifted from first-page identity: database_id",
        ):
            review_feedback_state.typed_epoch_from_pages(
                "base-owner/base-repo", [first, second], pr_number=7
            )

    def test_epoch_registry_rejects_both_identity_mapping_directions(self):
        for mutate in (
            lambda comment: comment.update({"databaseId": 999}),
            lambda comment: comment.update({"id": "NODE_conversation_other"}),
        ):
            with self.subTest(mutate=mutate):
                first, second = repeated_pages()
                mutate(
                    second["data"]["repository"]["pullRequest"]["comments"]["nodes"][0]
                )
                with self.assertRaisesRegex(
                    review_feedback_state.IdentityError, "contradictory typed identity"
                ):
                    review_feedback_state.typed_epoch_from_pages(
                        "base-owner/base-repo", [first, second], pr_number=7
                    )

    def test_epoch_registry_rejects_changed_repeated_revision_and_thread_scalars(self):
        first, second = repeated_pages()
        second["data"]["repository"]["pullRequest"]["comments"]["nodes"][0].update(
            {"body": "changed", "updatedAt": "2026-09-09T00:00:00Z"}
        )
        with self.assertRaisesRegex(
            review_feedback_state.IdentityError, "repeated provider object"
        ):
            review_feedback_state.typed_epoch_from_pages(
                "base-owner/base-repo", [first, second], pr_number=7
            )

        first, second = repeated_pages()
        second["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"][0][
            "isResolved"
        ] = True
        with self.assertRaisesRegex(
            review_feedback_state.IdentityError, "thread scalars"
        ):
            review_feedback_state.typed_epoch_from_pages(
                "base-owner/base-repo", [first, second], pr_number=7
            )

    def test_epoch_registry_rejects_association_identity_conflicts(self):
        page = fixture()
        reply = page["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"][0][
            "comments"
        ]["nodes"][1]["replyTo"]
        reply["databaseId"] = 999

        with self.assertRaisesRegex(
            review_feedback_state.IdentityError, "contradictory typed identity"
        ):
            review_feedback_state.typed_epoch_from_pages(
                "base-owner/base-repo", [page], pr_number=7
            )

        page = fixture()
        thread = page["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"][0]
        thread["path"] = "src/other.py"
        with self.assertRaisesRegex(
            review_feedback_state.ResponseShapeError, "placement.*thread"
        ):
            review_feedback_state.typed_epoch_from_pages(
                "base-owner/base-repo", [page], pr_number=7
            )


if __name__ == "__main__":
    unittest.main()
