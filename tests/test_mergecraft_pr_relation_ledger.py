"""Public historical PR body-edit contracts, using an isolated forge boundary."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import threading
import unittest


ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "plugins/mergecraft/skills/writing-reviewable-pr-descriptions/scripts"
PUBLISHER = ROOT / "plugins/mergecraft/skills/publishing-reviewable-prs/scripts"
sys.path.insert(0, str(WRITER))
sys.path.insert(0, str(PUBLISHER))

from validate_relation_ledger import LedgerValidationError, validate_request


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def fixture(state="MERGED"):
    before = "Résumé\r\n\r\nOld relation.\r\n\r\n<!-- tips_start -->\r\nkeep 🧭 exactly\r\n<!-- tips_end -->\r\n"
    replacement = "Tracks https://github.com/example/project/issues/4."
    start = len("Résumé\r\n\r\n".encode("utf-8"))
    end = start + len("Old relation.".encode("utf-8"))
    after = (before.encode()[:start] + replacement.encode() + before.encode()[end:]).decode()
    title = "feat: improve navigation"
    manifest = {
        "schema_version": 1,
        "operation": "pr-relation-ledger-write",
        "target": {"host": "github.com", "repository": "example/project",
                   "repository_id": "R_example", "entity_id": "PR_example", "number": 17},
        "preimage": {"title": title, "body": before, "state": state, "is_draft": False},
        "authorized_span": {"start_utf8": start, "end_utf8": end, "replacement": replacement},
        "candidate": {"title_sha256": digest(title), "body_sha256": digest(after)},
        "review": {"mode": "not-required", "selected_specialists": []},
    }
    return manifest, title.encode(), after.encode()


class RelationLedgerValidationTests(unittest.TestCase):
    def validate(self, manifest, title, body):
        return validate_request(manifest, title, body, review_mode="not-required", selected_specialists=[])

    def test_historical_states_preserve_every_unselected_utf8_byte(self):
        for state in ("OPEN", "CLOSED", "MERGED"):
            with self.subTest(state=state):
                manifest, title, body = fixture(state)
                request = self.validate(manifest, title, body)
                self.assertEqual(request.body.encode(), body)
                self.assertEqual(request.title.encode(), title)
                self.assertEqual(request.preimage["state"], state)

    def test_candidate_hash_cannot_authorize_changes_outside_the_span(self):
        manifest, title, body = fixture()
        body = body.replace(b"keep", b"lose")
        manifest["candidate"]["body_sha256"] = hashlib.sha256(body).hexdigest()
        with self.assertRaises(LedgerValidationError):
            self.validate(manifest, title, body)

    def test_byte_offsets_must_end_on_utf8_boundaries(self):
        manifest, title, body = fixture()
        manifest["authorized_span"].update(start_utf8=2, end_utf8=3)
        with self.assertRaises(LedgerValidationError):
            self.validate(manifest, title, body)

    def test_title_changes_and_unbound_review_selections_are_rejected(self):
        manifest, title, body = fixture()
        manifest["candidate"]["title_sha256"] = digest("feat: another title")
        with self.assertRaises(LedgerValidationError):
            self.validate(manifest, b"feat: another title", body)
        manifest, title, body = fixture()
        with self.assertRaises(LedgerValidationError):
            validate_request(manifest, title, body, review_mode="required", selected_specialists=["security"])

    def test_secret_guard_reuses_existing_detection(self):
        manifest, title, body = fixture()
        manifest["preimage"]["body"] += "ghp_" + "x" * 30
        with self.assertRaisesRegex(LedgerValidationError, "sensitive"):
            self.validate(manifest, title, body)

    def test_authorized_span_cannot_replace_recognized_bot_content(self):
        manifest, title, _ = fixture()
        original = manifest["preimage"]["body"].encode()
        start = original.index(b"keep")
        body = original[:start] + b"lose" + original[start + 4:]
        manifest["authorized_span"] = {"start_utf8": start, "end_utf8": start + 4, "replacement": "lose"}
        manifest["candidate"]["body_sha256"] = hashlib.sha256(body).hexdigest()
        with self.assertRaisesRegex(LedgerValidationError, "bot"):
            self.validate(manifest, title, body)


class MemoryForge:
    def __init__(self, manifest):
        self.live = {**manifest["target"], **manifest["preimage"], "kind": "PullRequest"}
        self.writes = []
        self.reads = 0

    def read(self, target):
        self.reads += 1
        return dict(self.live)

    def write_body(self, target, body):
        self.writes.append((dict(target), body))
        self.live["body"] = body


class RelationLedgerPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.receipt_root = Path(self.temporary.name) / "receipts"

    def publish(self, manifest, title, body, forge):
        from publish_relation_ledger import publish
        return publish(manifest, title, body, review_mode=manifest["review"]["mode"],
                       selected_specialists=manifest["review"]["selected_specialists"],
                       forge=forge, receipt_root=self.receipt_root)

    def test_historical_publication_is_one_body_only_write_with_separate_receipt(self):
        for state in ("OPEN", "CLOSED", "MERGED"):
            with self.subTest(state=state):
                manifest, title, body = fixture(state)
                forge = MemoryForge(manifest)
                result = self.publish(manifest, title, body, forge)
                self.assertEqual(result["status"], "verified")
                self.assertFalse(result["no_op"])
                self.assertEqual(forge.writes, [(manifest["target"], body.decode())])
                self.assertEqual(forge.reads, 3)
                self.assertEqual(result["state"], state)
                self.assertEqual(forge.live["title"], title.decode())
                self.assertEqual(result["before_body_sha256"], digest(manifest["preimage"]["body"]))
                self.assertEqual(result["after_body_sha256"], hashlib.sha256(body).hexdigest())
                self.assertEqual(result["operation"], "pr-relation-ledger")
                receipts = list((self.receipt_root / "relation-ledger").rglob("*.json"))
                receipt = next(json.loads(path.read_text()) for path in receipts
                               if json.loads(path.read_text()).get("receipt_id") == result["receipt_id"])
                self.assertNotIn("body", receipt)
                self.assertNotIn("title", receipt)
                self.assertEqual(receipt["scope"], "pr-relation-ledger")
                digest_value = receipt.pop("receipt_sha256")
                encoded = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
                self.assertEqual(hashlib.sha256(encoded).hexdigest(), digest_value)
                self.assertEqual(digest_value, result["receipt_sha256"])
        canonical_key = digest("example/project\x0017")
        self.assertFalse((self.receipt_root / canonical_key).exists())

    def test_matching_candidate_is_an_observation_only_noop(self):
        manifest, title, body = fixture()
        forge = MemoryForge(manifest)
        forge.live["body"] = body.decode()
        result = self.publish(manifest, title, body, forge)
        self.assertEqual(result["status"], "verified")
        self.assertTrue(result["no_op"])
        self.assertEqual(result["provenance"], "observed-existing")
        self.assertEqual(forge.writes, [])

    def test_wrong_type_identity_and_drift_block_before_mutation(self):
        for field, value in (("kind", "Issue"), ("entity_id", "PR_other"),
                             ("repository_id", "R_other"), ("number", 18),
                             ("host", "other.example"), ("repository", "other/project"),
                             ("title", "changed"), ("state", "OPEN"), ("is_draft", True),
                             ("body", "concurrent bot addition")):
            with self.subTest(field=field):
                manifest, title, body = fixture()
                forge = MemoryForge(manifest)
                forge.live[field] = value
                result = self.publish(manifest, title, body, forge)
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(forge.writes, [])
                self.assertIsNone(result["receipt_id"])

    def test_required_review_is_honestly_unsupported(self):
        manifest, title, body = fixture()
        manifest["review"] = {"mode": "required", "selected_specialists": ["security"]}
        forge = MemoryForge(manifest)
        result = self.publish(manifest, title, body, forge)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("required review", result["reason"])
        self.assertEqual(forge.writes, [])

    def test_final_preimage_reread_preserves_concurrent_bot_changes(self):
        manifest, title, body = fixture()

        class BotDriftForge(MemoryForge):
            def read(self, target):
                if self.reads == 1:
                    self.live["body"] = self.live["body"].replace("keep", "new bot content")
                return super().read(target)

        forge = BotDriftForge(manifest)
        result = self.publish(manifest, title, body, forge)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("new bot content", forge.live["body"])
        self.assertEqual(forge.writes, [])
        self.assertFalse(list(self.receipt_root.rglob("pending.json")))

    def test_post_write_drift_and_read_failure_remain_unknown(self):
        from reviewable_pr_state import PublicationError
        for failure in ("title", "state", "body", "read"):
            with self.subTest(failure=failure):
                manifest, title, body = fixture()
                # Distinct PR identities isolate each unresolved attempt.
                manifest["target"]["entity_id"] += failure
                manifest["target"]["number"] += len(failure)

                class PostDriftForge(MemoryForge):
                    def read(self, target):
                        if self.reads == 2:
                            if failure == "read":
                                raise PublicationError("private error details")
                            self.live[failure] = "concurrent change"
                        return super().read(target)

                forge = PostDriftForge(manifest)
                result = self.publish(manifest, title, body, forge)
                self.assertEqual(result["status"], "unknown")
                self.assertEqual(len(forge.writes), 1)
                again = self.publish(manifest, title, body, forge)
                self.assertEqual(again["status"], "unknown")
                self.assertEqual(len(forge.writes), 1)
                self.assertIsNone(result["receipt_id"])
                self.assertNotIn("private", json.dumps(result))

    def test_existing_publication_lease_serializes_historical_body_edits(self):
        from publication_receipts import load_receipts, prepare_receipt_store, receipt_ledger_lock
        from reviewable_pr_state import ExpectedIdentity
        manifest, title, body = fixture()
        forge = MemoryForge(manifest)
        expected = ExpectedIdentity(repository="example/project", pr_number=17, base="main",
                                    base_oid="a" * 40, head="example:feature", head_oid="b" * 40,
                                    head_owner="example", head_repository="example/project")
        prepare_receipt_store(self.receipt_root)
        started = threading.Event()

        def invoke():
            started.set()
            return self.publish(manifest, title, body, forge)

        with ThreadPoolExecutor(max_workers=1) as executor:
            with receipt_ledger_lock(self.receipt_root, expected):
                future = executor.submit(invoke)
                self.assertTrue(started.wait(2))
                with self.assertRaises(FutureTimeout):
                    future.result(timeout=0.1)
                self.assertEqual(forge.reads, 0)
            self.assertEqual(future.result(timeout=3)["status"], "verified")
        self.assertEqual(load_receipts(self.receipt_root, expected), [])

    def test_missing_durable_receipt_after_possible_write_is_unknown(self):
        manifest, title, body = fixture()
        root = self.receipt_root

        class BrokenStorageForge(MemoryForge):
            def write_body(self, target, body):
                super().write_body(target, body)
                directory = next((root / "relation-ledger").iterdir())
                directory.rename(directory.with_suffix(".retained"))
                directory.write_text("storage unavailable")

        forge = BrokenStorageForge(manifest)
        result = self.publish(manifest, title, body, forge)
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(len(forge.writes), 1)
        self.assertIsNone(result["receipt_id"])

    def test_renewal_preflight_failure_keeps_the_uncertain_attempt_guard(self):
        from publish_relation_ledger import publish
        from reviewable_pr_state import PublicationError
        manifest, title, body = fixture()

        class FailedRenewalForge(MemoryForge):
            def write_body(self, target, body):
                self.writes.append((dict(target), body))
                raise PublicationError("request outcome unavailable")

            def read(self, target):
                if self.reads == 6:
                    raise PublicationError("renewal final preflight unavailable")
                return super().read(target)

        forge = FailedRenewalForge(manifest)
        self.assertEqual(self.publish(manifest, title, body, forge)["status"], "unknown")
        args = dict(review_mode="not-required", selected_specialists=[], forge=forge, receipt_root=self.receipt_root)
        observed = publish(manifest, title, body, **args, reconcile=True)
        renewed = publish(manifest, title, body, **args, renew_after_receipt=observed["receipt_sha256"])
        self.assertEqual(renewed["status"], "unknown")
        self.assertTrue(list(self.receipt_root.rglob("pending.json")))
        self.assertEqual(self.publish(manifest, title, body, forge)["status"], "unknown")
        self.assertEqual(len(forge.writes), 1)

    def test_renewal_never_replaces_an_unrelated_pending_attempt(self):
        from publish_relation_ledger import publish
        from reviewable_pr_state import PublicationError
        manifest, title, body = fixture()
        root = self.receipt_root
        unrelated = b'{"attempt":"another operation"}'

        class ChangedIntentForge(MemoryForge):
            def write_body(self, target, body):
                self.writes.append((dict(target), body))
                raise PublicationError("request outcome unavailable")

            def read(self, target):
                if self.reads == 5:
                    next(root.rglob("pending.json")).write_bytes(unrelated)
                return super().read(target)

        forge = ChangedIntentForge(manifest)
        self.assertEqual(self.publish(manifest, title, body, forge)["status"], "unknown")
        args = dict(review_mode="not-required", selected_specialists=[], forge=forge, receipt_root=root)
        observed = publish(manifest, title, body, **args, reconcile=True)
        renewed = publish(manifest, title, body, **args, renew_after_receipt=observed["receipt_sha256"])
        self.assertEqual(renewed["status"], "unknown")
        self.assertEqual(next(root.rglob("pending.json")).read_bytes(), unrelated)
        self.assertEqual(len(forge.writes), 1)
        self.assertFalse(list(root.rglob("*.tmp")))


FAKE_GH = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
path = pathlib.Path(os.environ["RELATION_LEDGER_FIXTURE"])
saved = json.loads(path.read_text())
request = json.load(sys.stdin)
assert sys.argv[1:] == ["api", "--hostname", "github.com", "graphql", "--input", "-"]
assert "GH_HOST" not in os.environ and "GH_REPO" not in os.environ
saved["requests"].append(request)
query = request["query"]
live = saved["live"]
mode = saved.get("mode")
if query.lstrip().startswith("mutation"):
    assert set(request["variables"]) == {"id", "body"}
    assert "title:" not in query and "state:" not in query and "isDraft:" not in query
    assert request["variables"]["id"] == live["entity_id"]
    if mode == "lost_without_apply":
        path.write_text(json.dumps(saved))
        print("private response must not be echoed", file=sys.stderr)
        sys.exit(1)
    live["body"] = request["variables"]["body"]
    response = {"data": {"updatePullRequest": {"pullRequest": {"id": live["entity_id"]}}}}
    if mode == "partial_mutation":
        response["errors"] = [{"message": "private response must not be echoed"}]
    if mode == "lost_ack":
        path.write_text(json.dumps(saved))
        print("private response must not be echoed", file=sys.stderr)
        sys.exit(1)
else:
    pr = {"__typename": live["kind"], "id": live["entity_id"], "number": live["number"],
          "title": live["title"], "body": live["body"], "state": live["state"], "isDraft": live["is_draft"],
          "url": "https://github.com/" + live["repository"] + "/pull/" + str(live["number"])}
    response = {"data": {"repository": {"id": live["repository_id"], "nameWithOwner": live["repository"], "pullRequest": pr}}}
    if mode == "partial_read":
        response["errors"] = [{"message": "private response must not be echoed"}]
path.write_text(json.dumps(saved))
print(json.dumps(response))
'''


# Faults only the child process's OS file boundary. The actual publisher CLI,
# serializer, journal lifecycle, and recovery commands run without internal mocks.
CRASH_AFTER_OPEN = r'''
import os, re
_real_open = os.open
def _fault_open(path, flags, *args, **kwargs):
    descriptor = _real_open(path, flags, *args, **kwargs)
    name = os.path.basename(os.fspath(path))
    phase = os.environ.get("RELATION_LEDGER_CRASH_PHASE")
    journal = name == "pending.json" or name.startswith(".pending.json.")
    receipt = re.fullmatch(r"\.?[0-9a-f]{64}\.json(?:\.[0-9a-f-]+\.tmp)?", name) is not None
    successor = re.fullmatch(r"[0-9a-f-]{36}\.tmp", name) is not None
    selected = ((phase == "journal" and journal) or (phase == "receipt" and receipt)
                or (phase == "renewal" and (journal or successor)))
    if selected and flags & os.O_CREAT and "/relation-ledger/" in os.fspath(path):
        os._exit(77)
    return descriptor
os.open = _fault_open
'''


INSTALL_CONFLICT = r'''
import os
_real_link = os.link
def _conflicting_link(source, destination, *args, **kwargs):
    if os.path.basename(os.fspath(destination)) == "pending.json":
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(b'{"attempt":"another operation"}')
    return _real_link(source, destination, *args, **kwargs)
os.link = _conflicting_link
'''


class RelationLedgerCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.manifest, title, body = fixture()
        self.title_bytes, self.body_bytes = title, body
        self.title = self.directory / "title.txt"
        self.body = self.directory / "body.txt"
        self.input = self.directory / "manifest.json"
        self.title.write_bytes(title)
        self.body.write_bytes(body)
        self.input.write_text(json.dumps(self.manifest))
        self.forge_path = self.directory / "forge.json"
        self.forge_path.write_text(json.dumps({"live": MemoryForge(self.manifest).live, "requests": []}))
        gh = self.directory / "gh"
        gh.write_text(FAKE_GH)
        gh.chmod(0o700)
        self.environment = {**os.environ, "PATH": f"{self.directory}:{os.environ['PATH']}",
                            "RELATION_LEDGER_FIXTURE": str(self.forge_path),
                            "XDG_STATE_HOME": str(self.directory / "state"),
                            "GH_HOST": "wrong.example", "GH_REPO": "wrong/repo"}

    def run_command(self, script=PUBLISHER / "publish_relation_ledger.py", extra=()):
        return subprocess.run([sys.executable, str(script), "--manifest", str(self.input),
                               "--title-file", str(self.title), "--body-file", str(self.body),
                               "--review-mode", "not-required", "--selected-specialists", "[]", *extra],
                              cwd=self.directory, env=self.environment, capture_output=True, text=True, timeout=15)

    def mode(self, mode):
        data = json.loads(self.forge_path.read_text())
        data["mode"] = mode
        self.forge_path.write_text(json.dumps(data))

    def interrupt_after_evidence_open(self, phase):
        (self.directory / "sitecustomize.py").write_text(CRASH_AFTER_OPEN)
        self.environment["PYTHONPATH"] = str(self.directory)
        self.environment["RELATION_LEDGER_CRASH_PHASE"] = phase

    def stop_interrupting(self):
        self.environment.pop("RELATION_LEDGER_CRASH_PHASE", None)

    def assert_no_partial_final_evidence(self):
        for path in (self.directory / "state").rglob("*.json"):
            self.assertIsInstance(json.loads(path.read_text()), dict, str(path))

    def test_interrupted_initial_journal_never_exposes_partial_pending_file(self):
        self.interrupt_after_evidence_open("journal")
        interrupted = self.run_command()
        self.assertEqual(interrupted.returncode, 77, interrupted.stdout + interrupted.stderr)
        self.assertFalse(list((self.directory / "state").rglob("pending.json")))
        retained = {path: path.read_bytes() for path in (self.directory / "state").rglob("*.tmp")}
        self.assertTrue(retained)
        requests = json.loads(self.forge_path.read_text())["requests"]
        self.assertFalse(any(request["query"].lstrip().startswith("mutation") for request in requests))
        self.stop_interrupting()
        observed = self.run_command(extra=("--reconcile",))
        self.assertEqual(observed.returncode, 1, observed.stdout + observed.stderr)
        self.assertGreater(len(json.loads(self.forge_path.read_text())["requests"]), len(requests))
        published = self.run_command()
        self.assertEqual(published.returncode, 0, published.stdout + published.stderr)
        self.assert_no_partial_final_evidence()
        self.assertTrue(all(path.read_bytes() == content for path, content in retained.items()))

    def test_initial_installation_conflict_preserves_other_attempt_and_cleans_own_stage(self):
        (self.directory / "sitecustomize.py").write_text(INSTALL_CONFLICT)
        self.environment["PYTHONPATH"] = str(self.directory)
        result = self.run_command()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        pending_path = next((self.directory / "state").rglob("pending.json"))
        self.assertEqual(pending_path.read_bytes(), b'{"attempt":"another operation"}')
        self.assertFalse(list((self.directory / "state").rglob("*.tmp")))
        requests = json.loads(self.forge_path.read_text())["requests"]
        self.assertFalse(any(request["query"].lstrip().startswith("mutation") for request in requests))

    def test_interrupted_receipt_keeps_complete_journal_and_is_reconcilable(self):
        self.interrupt_after_evidence_open("receipt")
        interrupted = self.run_command()
        self.assertEqual(interrupted.returncode, 77, interrupted.stdout + interrupted.stderr)
        self.assert_no_partial_final_evidence()
        self.assertEqual(len(list((self.directory / "state").rglob("pending.json"))), 1)
        self.stop_interrupting()
        observed = self.run_command(extra=("--reconcile",))
        self.assertEqual(observed.returncode, 0, observed.stdout + observed.stderr)
        self.assertEqual(json.loads(observed.stdout)["provenance"], "observed-after-uncertain")
        requests = json.loads(self.forge_path.read_text())["requests"]
        self.assertEqual(sum(request["query"].lstrip().startswith("mutation") for request in requests), 1)
        self.assert_no_partial_final_evidence()

    def test_interrupted_renewal_preserves_prior_complete_journal(self):
        self.mode("lost_without_apply")
        self.assertEqual(json.loads(self.run_command().stdout)["status"], "unknown")
        observed = json.loads(self.run_command(extra=("--reconcile",)).stdout)
        pending_path = next((self.directory / "state").rglob("pending.json"))
        pending_bytes = pending_path.read_bytes()
        self.interrupt_after_evidence_open("renewal")
        interrupted = self.run_command(extra=("--renew-after-receipt", observed["receipt_sha256"]))
        self.assertEqual(interrupted.returncode, 77, interrupted.stdout + interrupted.stderr)
        self.assertEqual(pending_path.read_bytes(), pending_bytes)
        self.stop_interrupting()
        again = self.run_command(extra=("--reconcile",))
        self.assertEqual(json.loads(again.stdout)["provenance"], "observed-preimage")
        self.assert_no_partial_final_evidence()

    def test_cli_publishes_without_git_and_preserves_exact_literal_bytes(self):
        result = self.run_command()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        value = json.loads(result.stdout)
        self.assertEqual(value["status"], "verified")
        forge = json.loads(self.forge_path.read_text())
        self.assertEqual(forge["live"]["body"].encode(), self.body_bytes)
        self.assertEqual(forge["live"]["title"].encode(), self.title_bytes)
        self.assertEqual(len(forge["requests"]), 4)
        receipts = self.directory / "state/mergecraft/pr-publication-receipts/relation-ledger"
        self.assertTrue(list(receipts.rglob("*.json")))

    def test_graphql_data_plus_errors_never_produces_verified_result(self):
        for mode, status, count in (("partial_read", "blocked", 1), ("partial_mutation", "unknown", 4)):
            with self.subTest(mode=mode):
                self.mode(mode)
                result = self.run_command()
                self.assertEqual(json.loads(result.stdout)["status"], status, result.stderr)
                self.assertNotIn("private response", result.stdout + result.stderr)
                self.assertEqual(len(json.loads(self.forge_path.read_text())["requests"]), count)
                saved = json.loads(self.forge_path.read_text())
                saved["requests"] = []
                self.forge_path.write_text(json.dumps(saved))

    def test_lost_acknowledgement_is_unknown_and_repeat_does_not_write(self):
        self.mode("lost_ack")
        first = self.run_command()
        self.assertEqual(json.loads(first.stdout)["status"], "unknown", first.stderr)
        second = self.run_command()
        self.assertEqual(json.loads(second.stdout)["status"], "unknown", second.stderr)
        self.assertNotIn("private response", first.stdout + first.stderr + second.stdout + second.stderr)
        requests = json.loads(self.forge_path.read_text())["requests"]
        self.assertEqual(sum(request["query"].lstrip().startswith("mutation") for request in requests), 1)

    def test_uncertain_write_can_be_reconciled_without_claiming_causality(self):
        self.mode("lost_ack")
        self.assertEqual(json.loads(self.run_command().stdout)["status"], "unknown")
        observed = self.run_command(extra=("--reconcile",))
        self.assertEqual(observed.returncode, 0, observed.stderr + observed.stdout)
        result = json.loads(observed.stdout)
        self.assertTrue(result["no_op"])
        self.assertEqual(result["provenance"], "observed-after-uncertain")
        self.assertIsNotNone(result["receipt_sha256"])
        requests = json.loads(self.forge_path.read_text())["requests"]
        self.assertEqual(sum(request["query"].lstrip().startswith("mutation") for request in requests), 1)
        self.assertFalse(list((self.directory / "state").rglob("pending.json")))

    def test_preimage_observation_requires_explicit_bound_renewal_before_next_write(self):
        self.mode("lost_without_apply")
        self.assertEqual(json.loads(self.run_command().stdout)["status"], "unknown")
        observed = self.run_command(extra=("--reconcile",))
        self.assertEqual(observed.returncode, 1, observed.stderr + observed.stdout)
        result = json.loads(observed.stdout)
        self.assertEqual(result["provenance"], "observed-preimage")
        self.assertTrue(result["renewal_required"])
        self.assertEqual(json.loads(self.run_command().stdout)["status"], "unknown")
        self.mode(None)
        renewed = self.run_command(extra=("--renew-after-receipt", result["receipt_sha256"]))
        self.assertEqual(renewed.returncode, 0, renewed.stderr + renewed.stdout)
        self.assertEqual(json.loads(renewed.stdout)["provenance"], "wrote-and-verified")
        stale = self.run_command(extra=("--renew-after-receipt", result["receipt_sha256"]))
        self.assertEqual(stale.returncode, 1, stale.stderr + stale.stdout)
        requests = json.loads(self.forge_path.read_text())["requests"]
        self.assertEqual(sum(request["query"].lstrip().startswith("mutation") for request in requests), 2)

    def test_reconcile_never_writes_when_there_is_no_pending_attempt(self):
        result = self.run_command(extra=("--reconcile",))
        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
        self.assertEqual(json.loads(result.stdout)["status"], "blocked")
        requests = json.loads(self.forge_path.read_text())["requests"]
        self.assertFalse(any(request["query"].lstrip().startswith("mutation") for request in requests))

    def test_renewal_receipt_cannot_authorize_a_later_uncertain_attempt(self):
        self.mode("lost_without_apply")
        self.assertEqual(json.loads(self.run_command().stdout)["status"], "unknown")
        observed = json.loads(self.run_command(extra=("--reconcile",)).stdout)
        renewal = ("--renew-after-receipt", observed["receipt_sha256"])
        self.assertEqual(json.loads(self.run_command(extra=renewal).stdout)["status"], "unknown")
        before = len(json.loads(self.forge_path.read_text())["requests"])
        stale = self.run_command(extra=renewal)
        self.assertNotEqual(json.loads(stale.stdout)["status"], "verified")
        self.assertEqual(len(json.loads(self.forge_path.read_text())["requests"]), before)

    def test_validator_cli_is_read_only_and_rejects_duplicate_fields(self):
        result = self.run_command(WRITER / "validate_relation_ledger.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "validated")
        self.assertEqual(json.loads(self.forge_path.read_text())["requests"], [])
        self.input.write_text(self.input.read_text().replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1'))
        result = self.run_command(WRITER / "validate_relation_ledger.py")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "blocked")

    def test_cli_has_no_receipt_root_override(self):
        result = self.run_command(extra=("--receipt-root", str(self.directory / "alternate")))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(self.forge_path.read_text())["requests"], [])


if __name__ == "__main__":
    unittest.main()
