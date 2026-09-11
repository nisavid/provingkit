import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
REPOSITORY = Path(__file__).resolve().parents[4]
SCRIPT = (
    REPOSITORY
    / "plugins/mergecraft/skills/interacting-with-pr-review-feedback/scripts/response_cli.py"
)
TYPED_FIXTURE = (
    REPOSITORY
    / "tests/plugins/mergecraft/addressing-pr-review-feedback/fixtures/typed_feedback_epoch.json"
)


def make_intent(epoch, source, key, body):
    return {
        "schema_version": 1,
        "intent_key": key,
        "intent_kind": "ordinary",
        "admitted_epoch": epoch,
        "source": source,
        "operation": "create_inline_reply",
        "placement": {
            "kind": "review_thread",
            "thread_node_id": source["thread"]["node_id"],
            "root_comment_database_id": source["thread"]["root_comment_database_id"],
        },
        "writer": {
            "identity": "writer-cli",
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "contract": "portable-github-markdown-authoring",
            "contract_version": "1",
            "field": "review_thread_reply",
        },
        "authority": {
            "decision": "authorized",
            "evidence_id": f"authority-{key}",
            "actor_login": "ivan",
        },
        "adjudication": {
            "disposition": "respond",
            "evidence_id": f"adjudication-{key}",
        },
        "classification": {
            "result": "human_feedback",
            "evidence_id": f"classification-{key}",
        },
        "independence_evidence": {
            "availability": "not_applicable",
            "reason": "initial_admission",
        },
    }


class ResponseCliTests(unittest.TestCase):
    def test_cli_keeps_two_indistinguishable_effective_unknowns_unassigned(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = root / "provider.json"
            endpoint = "POST /repos/base-owner/base-repo/pulls/7/comments/301/replies"
            provider.write_text(
                json.dumps(
                    {
                        "actor": "ivan",
                        "next_id": 900,
                        "graphql": json.loads(
                            TYPED_FIXTURE.read_text(encoding="utf-8")
                        ),
                        "queued": {
                            endpoint: [
                                {"returncode": 1, "stderr": "connection reset"},
                                {"returncode": 1, "stderr": "connection reset"},
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )
            fake = TEST_DIR / "fixtures/fake_gh.py"
            common = [
                sys.executable,
                str(SCRIPT),
                "--gh-command-json",
                json.dumps([sys.executable, str(fake), str(provider)]),
            ]
            acquired = subprocess.run(
                [*common, "acquire", "--repo", "base-owner/base-repo", "--pr", "7"],
                check=True,
                capture_output=True,
                text=True,
            )
            epoch = json.loads(acquired.stdout)
            body = b"Same response"
            body_path = root / "body.md"
            body_path.write_bytes(body)
            ledger = root / "ledger"
            for index, key in enumerate(("unknown-a", "unknown-b")):
                intent_path = root / f"{key}.json"
                intent_path.write_text(
                    json.dumps(make_intent(epoch, epoch["sources"][index], key, body)),
                    encoding="utf-8",
                )
                invoked = subprocess.run(
                    [
                        *common,
                        "invoke",
                        "--state-dir",
                        str(ledger),
                        "--intent",
                        str(intent_path),
                        "--body-file",
                        str(body_path),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(json.loads(invoked.stdout)["status"], "unknown")
            state = json.loads(provider.read_text(encoding="utf-8"))
            pr = state["graphql"]["data"]["repository"]["pullRequest"]
            result = json.loads(
                json.dumps(pr["reviewThreads"]["nodes"][0]["comments"]["nodes"][1])
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
                    "url": "https://github.com/base-owner/base-repo/pull/7#discussion_r950",
                }
            )
            pr["reviewThreads"]["nodes"][0]["comments"]["nodes"].append(result)
            calls_before = list(state["calls"])
            provider.write_text(json.dumps(state), encoding="utf-8")

            reconciled = subprocess.run(
                [
                    *common,
                    "reconcile",
                    "--state-dir",
                    str(ledger),
                    "--intent-key",
                    "unknown-a",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            outcome = json.loads(reconciled.stdout)
            self.assertEqual(outcome["status"], "unknown")
            self.assertIn("indistinguishable", outcome["reason"])
            self.assertEqual(
                json.loads(provider.read_text(encoding="utf-8"))["calls"],
                calls_before,
            )

    def test_cli_acquires_invokes_and_reads_append_only_outcomes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
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
            gh_prefix = json.dumps([sys.executable, str(fake), str(provider)])
            common = [sys.executable, str(SCRIPT), "--gh-command-json", gh_prefix]
            acquired = subprocess.run(
                [*common, "acquire", "--repo", "base-owner/base-repo", "--pr", "7"],
                check=True,
                capture_output=True,
                text=True,
            )
            epoch = json.loads(acquired.stdout)
            source = epoch["sources"][0]
            body = b"CLI exact body\r\n"
            intent = {
                "schema_version": 1,
                "intent_key": "cli-intent",
                "intent_kind": "ordinary",
                "admitted_epoch": epoch,
                "source": source,
                "operation": "create_inline_reply",
                "placement": {
                    "kind": "review_thread",
                    "thread_node_id": source["thread"]["node_id"],
                    "root_comment_database_id": source["thread"][
                        "root_comment_database_id"
                    ],
                },
                "writer": {
                    "identity": "writer-cli",
                    "body_sha256": hashlib.sha256(body).hexdigest(),
                    "contract": "portable-github-markdown-authoring",
                    "contract_version": "1",
                    "field": "review_thread_reply",
                },
                "authority": {
                    "decision": "authorized",
                    "evidence_id": "authority-cli",
                    "actor_login": "ivan",
                },
                "adjudication": {
                    "disposition": "respond",
                    "evidence_id": "adjudication-cli",
                },
                "classification": {
                    "result": "human_feedback",
                    "evidence_id": "classification-cli",
                },
                "independence_evidence": {
                    "availability": "not_applicable",
                    "reason": "initial_admission",
                },
            }
            intent_path, body_path = root / "intent.json", root / "body.md"
            intent_path.write_text(json.dumps(intent), encoding="utf-8")
            body_path.write_bytes(body)
            invoked = subprocess.run(
                [
                    *common,
                    "invoke",
                    "--state-dir",
                    str(root / "ledger"),
                    "--intent",
                    str(intent_path),
                    "--body-file",
                    str(body_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            invoked_outcome = json.loads(invoked.stdout)
            self.assertEqual(invoked_outcome["status"], "confirmed_success")
            self.assertFalse(invoked_outcome["all_feedback_addressed"])

            read = subprocess.run(
                [
                    *common,
                    "outcomes",
                    "--state-dir",
                    str(root / "ledger"),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            outcomes = json.loads(read.stdout)
            self.assertEqual([item["intent_key"] for item in outcomes], ["cli-intent"])
            self.assertFalse(outcomes[0]["all_feedback_addressed"])
            calls = json.loads(provider.read_text(encoding="utf-8"))["calls"]
            self.assertTrue(
                any(call["operation"] == "graphql_read_query" for call in calls)
            )
            self.assertEqual(
                sum(call["operation"] == "response_write" for call in calls),
                1,
            )
            ledger = root / "ledger"
            self.assertTrue((ledger / "response-outcome-bundle-v2.json").is_file())
            self.assertTrue((ledger / "records").is_dir())
            self.assertFalse(any(ledger.glob("*.jsonl")))

            provider_state = json.loads(provider.read_text(encoding="utf-8"))
            provider_state["graphql"]["data"]["repository"]["pullRequest"][
                "headRefOid"
            ] = "drifted-head"
            provider.write_text(json.dumps(provider_state), encoding="utf-8")
            intent["intent_key"] = "cli-stale"
            intent_path.write_text(json.dumps(intent), encoding="utf-8")
            replacement_ledger = root / "replacement-ledger"
            blocked = subprocess.run(
                [
                    *common,
                    "invoke",
                    "--state-dir",
                    str(replacement_ledger),
                    "--intent",
                    str(intent_path),
                    "--body-file",
                    str(body_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                json.loads(blocked.stdout)["pre_write_state"],
                "invalidated_unexecuted",
            )
            prepared = subprocess.run(
                [
                    *common,
                    "prepare-replacement",
                    "--state-dir",
                    str(replacement_ledger),
                    "--intent-key",
                    "cli-stale",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            basis = json.loads(prepared.stdout)
            self.assertEqual(basis["terminal_state"], "invalidated_unexecuted")
            self.assertEqual(
                basis["successor_epoch_id"], basis["successor_epoch"]["epoch_id"]
            )
            self.assertEqual(
                sum(
                    call["operation"] == "response_write"
                    for call in json.loads(provider.read_text(encoding="utf-8"))[
                        "calls"
                    ]
                ),
                1,
            )

            legacy_ledger = root / "legacy-ledger"
            legacy_ledger.mkdir()
            legacy = legacy_ledger / "attempts.jsonl"
            legacy.write_bytes(b'{}\n{"torn":')
            before = legacy.read_bytes()
            rejected = subprocess.run(
                [
                    *common,
                    "invoke",
                    "--state-dir",
                    str(legacy_ledger),
                    "--intent",
                    str(intent_path),
                    "--body-file",
                    str(body_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("unsupported-development-format", rejected.stderr)
            self.assertEqual(legacy.read_bytes(), before)
            self.assertFalse((legacy_ledger / "response-runtime.lock").exists())
            calls = json.loads(provider.read_text(encoding="utf-8"))["calls"]
            self.assertEqual(
                sum(call["operation"] == "response_write" for call in calls),
                1,
            )


if __name__ == "__main__":
    unittest.main()
