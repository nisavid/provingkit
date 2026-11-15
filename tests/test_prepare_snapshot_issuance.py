"""Consumer examples for the local, cooperating snapshot issuer CLI."""

import json
import hashlib
import subprocess
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/prepare_snapshot_issuance.py"
SOURCE = "1" * 40


class SnapshotIssuanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.state = self.root / "state.sqlite"

    def call(self, request, *, accepted=True, clock=None):
        path = self.root / "request.json"
        path.write_text(json.dumps(request))
        command = [sys.executable, str(SCRIPT)]
        if clock is not None:
            command = [sys.executable, "-c",
                       "import runpy,sys,time; time.time=lambda: " + str(clock)
                       + "; script=sys.argv.pop(1); sys.path.insert(0,str(__import__('pathlib').Path(script).parent));"
                       + "runpy.run_path(script,run_name='__main__')", str(SCRIPT)]
        result = subprocess.run(
            [*command, "--state", str(self.state), "--request", str(path)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode == 0, accepted, result.stdout + result.stderr)
        self.assertTrue(result.stdout.strip(), "the issuer returned no consumer result")
        return json.loads(result.stdout)

    def initialize(self, **changes):
        return self.call({"operation": "initialize", "custody_owner": "test-release-owner",
                          "endpoint_fingerprint": "sha256:" + "a" * 64,
                          "target_release": "0.1.0", "preceding_cut": "0.1.0-alpha.7",
                          "next_named_release": "0.1.0-alpha.8", **changes})

    def prepare(self, request_id="first", source=SOURCE):
        return self.call({"operation": "prepare", "request_id": request_id, "source_commit": source})

    def git(self, *arguments):
        return subprocess.check_output(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
             "-c", "commit.gpgsign=false", *arguments], cwd=self.transport, text=True,
        ).strip()

    def publication(self, record, target="claude", content=b"retained archive"):
        self.transport = self.root / "transport"
        if not self.transport.exists():
            self.transport.mkdir()
            self.git("init", "-q")
        directory = self.transport / "ad-hoc" / record["source_commit"] / record["version"] / target
        directory.mkdir(parents=True, exist_ok=True)
        preparation_bytes = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
        receipt = {"source": {"commit": record["source_commit"]}, "target": target,
                   "delivery": {"version": record["version"], "request_id": record["request_id"],
                                "preparation_sha256": hashlib.sha256(preparation_bytes).hexdigest()}}
        (directory / "artifact.tar.gz").write_bytes(content)
        (directory / "RECEIPT.json").write_text(json.dumps(receipt))
        (directory / "modes.tsv").write_bytes(b"path\tmode\torigin\n")
        self.git("add", ".")
        self.git("commit", "-qm", "test: prepared transport")
        plan = {"status": "ready", "source_sha": self.git("rev-parse", "HEAD"),
                "destination": {"ref": "refs/heads/ivan/provingkit-ad-hoc-artifacts",
                                "remote": "origin", "endpoint_fingerprint": "sha256:" + "a" * 64}}
        path = self.root / (record["request_id"] + "-" + target + "-plan.json")
        path.write_text(json.dumps(plan))
        return {"operation": "issue", "request_id": record["request_id"],
                "publication_plan": str(path),
                "reviewed_plan_sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
                "transport_repository": str(self.transport),
                "variants": {target: {name: str(directory / name)
                                      for name in ("artifact.tar.gz", "RECEIPT.json", "modes.tsv")}}}

    def reconcile(self, request, *, verified=True, attempted=True):
        plan = json.loads(Path(request["publication_plan"]).read_text())
        result = {"status": "verified" if verified else "blocked", "source_sha": plan["source_sha"],
                  "destination": plan["destination"], "push_attempted": attempted,
                  "reasons": [] if verified else [{"kind": "constructed-unknown"}],
                  "postchecks": [{"kind": "remote_ref_equals", "ref": plan["destination"]["ref"],
                                  "endpoint_fingerprint": plan["destination"]["endpoint_fingerprint"],
                                  "sha": plan["source_sha"]}] if verified else []}
        path = self.root / (request["request_id"] + "-result.json")
        path.write_text(json.dumps(result))
        return self.call({"operation": "reconcile", "request_id": request["request_id"],
                          "publication_result": str(path)})

    def test_owner_prepares_a_snapshot_and_recovers_the_same_request(self):
        self.initialize()
        first = self.prepare()
        self.assertEqual(first, {
            "schema": "provingkit-snapshot-preparation-v1", "request_id": "first",
            "release_unit": "provingkit", "target_release": "0.1.0",
            "preceding_cut": "0.1.0-alpha.7", "next_named_release": "0.1.0-alpha.8",
            "sequence": 1, "version": "0.1.0-alpha.7.snapshot.1", "source_commit": SOURCE,
        })
        self.assertEqual(self.prepare(), first)
        self.assertEqual(self.prepare("second")["version"], "0.1.0-alpha.7.snapshot.2")

    def test_issuance_binds_published_files_and_holds_uncertain_exposure(self):
        self.initialize()
        prepared = self.prepare()
        request = self.publication(prepared)
        issued = self.call(request)
        self.assertEqual(issued["version"], "0.1.0-alpha.7.snapshot.1")
        self.assertEqual(issued["exposure"], "pending")
        self.assertEqual(self.call(request), issued)
        state = self.call({"operation": "inspect"})
        self.assertEqual(state["last_issued"], "0.1.0-alpha.7.snapshot.1")
        self.assertEqual(state["pending"], "first")
        later = self.publication(self.prepare("later"))
        refused = self.call(later, accepted=False)
        self.assertIn("pending", refused["reason"])

    def test_reverse_completion_cannot_expose_an_earlier_reservation(self):
        self.initialize()
        earlier = self.prepare("earlier")
        later = self.publication(self.prepare("later"))
        self.call(later)
        self.assertEqual(self.reconcile(later)["exposure"], "verified")
        refused = self.call(self.publication(earlier), accepted=False)
        self.assertIn("last issued", refused["reason"])
        self.assertEqual(self.call({"operation": "inspect"})["last_issued"], "0.1.0-alpha.7.snapshot.2")

    def test_cut_transition_rejects_stale_preparation_and_continues_sequence(self):
        self.initialize()
        stale = self.prepare("stale")
        self.call({"operation": "advance-cut", "preceding_cut": "0.1.0-alpha.8",
                   "next_named_release": "0.1.0-beta.1"})
        rejected = self.call(self.publication(stale), accepted=False)
        self.assertIn("stale", rejected["reason"])
        self.assertEqual(self.prepare("after-cut")["version"], "0.1.0-alpha.8.snapshot.2")

    def test_new_variant_extends_an_older_version_without_moving_issuance(self):
        self.initialize()
        first = self.prepare()
        initial = self.publication(first)
        self.call(initial)
        self.reconcile(initial)
        later = self.publication(self.prepare("later"))
        self.call(later)
        self.reconcile(later)
        addition = self.publication(first, "cursor", b"cursor archive")
        addition.update(operation="add-variants", request_id="add-cursor", version=first["version"],
                        source_commit=first["source_commit"])
        self.assertEqual(self.call(addition)["operation"], "add-variants")
        self.reconcile(addition)
        state = self.call({"operation": "inspect"})
        self.assertEqual(state["last_issued"], "0.1.0-alpha.7.snapshot.2")
        self.assertEqual(set(state["versions"][first["version"]]["variants"]), {"claude", "cursor"})

    def test_withdrawal_preserves_bytes_and_deliberate_rollback_keeps_high_water(self):
        self.initialize()
        first = self.prepare()
        original = self.publication(first)
        self.call(original)
        self.reconcile(original)
        later = self.publication(self.prepare("later", "2" * 40), content=b"new archive")
        self.call(later)
        self.reconcile(later)
        self.call({"operation": "withdraw", "version": first["version"]})
        Path(original["variants"]["claude"]["artifact.tar.gz"]).unlink()
        output = self.root / "rollback"
        result = self.call({"operation": "redeliver", "version": first["version"],
                            "target": "claude", "output": str(output)})
        self.assertEqual(result["version"], "0.1.0-alpha.7.snapshot.1")
        self.assertEqual((output / "artifact.tar.gz").read_bytes(), b"retained archive")
        self.assertEqual(self.call({"operation": "inspect"})["last_issued"], "0.1.0-alpha.7.snapshot.2")
        replacement = self.publication(first, content=b"replacement bytes")
        replacement.update(operation="add-variants", request_id="replace", version=first["version"],
                           source_commit=first["source_commit"])
        self.assertIn("existing variant", self.call(replacement, accepted=False)["reason"])
        replacement["source_commit"] = "3" * 40
        self.assertIn("source identity", self.call(replacement, accepted=False)["reason"])

    def test_normal_release_closes_issuance_and_next_target_uses_zero_anchor(self):
        self.initialize(preceding_cut="0.1.0-rc.2", next_named_release="0.1.0")
        self.assertEqual(self.prepare()["version"], "0.1.0-rc.2.snapshot.1")
        self.call({"operation": "advance-cut", "preceding_cut": "0.1.0", "next_named_release": "0.1.0"})
        self.assertIn("closed", self.call({"operation": "prepare", "request_id": "too-late",
                                           "source_commit": SOURCE}, accepted=False)["reason"])
        self.call({"operation": "retarget", "target_release": "0.2.0", "next_named_release": "0.2.0-alpha.1"})
        self.assertEqual(self.prepare("new-target")["version"], "0.2.0-0.snapshot.1")
        self.assertEqual(self.call({"operation": "inspect"})["target_history"][0]["target_release"], "0.1.0")

    def test_old_source_and_reversed_clock_still_receive_a_higher_snapshot(self):
        self.initialize()
        first = self.call({"operation": "prepare", "request_id": "newer-source", "source_commit": "2" * 40}, clock=2000)
        publication = self.publication(first)
        self.call(publication)
        self.reconcile(publication)
        older = self.call({"operation": "prepare", "request_id": "older-source", "source_commit": "1" * 40}, clock=1000)
        self.assertEqual(older["version"], "0.1.0-alpha.7.snapshot.2")
        same_source = self.prepare("same-source", "1" * 40)
        self.assertEqual(same_source["version"], "0.1.0-alpha.7.snapshot.3")

    def test_uncertain_attempt_survives_reentry_and_blocks_cut_changes(self):
        self.initialize()
        request = self.publication(self.prepare())
        original = self.call(request)
        self.assertEqual(self.reconcile(request, verified=False)["exposure"], "pending")
        self.assertEqual(self.call(request)["version"], original["version"])
        refused = self.call({"operation": "advance-cut", "preceding_cut": "0.1.0-alpha.8",
                             "next_named_release": "0.1.0-beta.1"}, accepted=False)
        self.assertIn("pending", refused["reason"])
        self.assertEqual(self.reconcile(request)["exposure"], "verified")

    def test_competing_issuers_cannot_both_cross_the_pending_exposure_boundary(self):
        self.initialize()
        earlier = self.publication(self.prepare("earlier"))
        retained_inputs = self.root / "earlier-inputs"
        shutil.copytree(Path(earlier["variants"]["claude"]["RECEIPT.json"]).parent, retained_inputs)
        earlier["variants"]["claude"] = {name: str(retained_inputs / name) for name in earlier["variants"]["claude"]}
        earlier_preparation = self.call({"operation": "prepare", "request_id": "earlier", "source_commit": SOURCE})
        shutil.rmtree(self.transport / "ad-hoc" / SOURCE / earlier_preparation["version"])
        later = self.publication(self.prepare("later"))
        processes = []
        for request in (earlier, later):
            path = self.root / (request["request_id"] + "-request.json")
            path.write_text(json.dumps(request))
            processes.append(subprocess.Popen(
                [sys.executable, str(SCRIPT), "--state", str(self.state), "--request", str(path)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        results = [(process, process.communicate(timeout=15)) for process in processes]
        self.assertEqual(sum(process.returncode == 0 for process, _ in results), 1)
        winner = next(json.loads(output[0]) for process, output in results if process.returncode == 0)
        refused = next(json.loads(output[0]) for process, output in results if process.returncode != 0)
        self.assertIn("pending", refused["reason"])
        state = self.call({"operation": "inspect"})
        self.assertEqual(state["pending"], winner["request_id"])
        self.assertEqual(state["last_issued"], winner["version"])

    def test_immutable_retry_rejects_rebuilt_bytes_and_new_source(self):
        self.initialize()
        request = self.publication(self.prepare())
        self.call(request)
        Path(request["variants"]["claude"]["artifact.tar.gz"]).write_bytes(b"rebuilt bytes")
        self.assertIn("retry changes", self.call(request, accepted=False)["reason"])
        self.assertIn("another source", self.call({"operation": "prepare", "request_id": "first",
                                                  "source_commit": "2" * 40}, accepted=False)["reason"])

    def test_successful_commit_with_wrong_artifact_bytes_is_not_issuance(self):
        self.initialize()
        request = self.publication(self.prepare())
        Path(request["variants"]["claude"]["artifact.tar.gz"]).write_bytes(b"wrong staged bytes")
        self.assertIn("publication changes", self.call(request, accepted=False)["reason"])
        self.assertIsNone(self.call({"operation": "inspect"})["last_issued"])

    def test_cancelled_unattempted_generation_is_not_forced_into_a_later_publication(self):
        self.initialize()
        prepared = self.prepare()
        request = self.publication(prepared)
        self.call(request)
        self.assertEqual(self.reconcile(request, verified=False, attempted=False)["exposure"], "cancelled")
        shutil.rmtree(self.transport / "ad-hoc" / prepared["source_commit"] / prepared["version"])
        later = self.publication(self.prepare("later"))
        self.assertEqual(self.call(later)["version"], "0.1.0-alpha.7.snapshot.2")
        self.assertIn(prepared["version"], self.call({"operation": "inspect"})["versions"])

    def test_publication_cannot_expose_a_target_missing_from_the_issuance_record(self):
        self.initialize()
        prepared = self.prepare()
        claude = self.publication(prepared)
        both = self.publication(prepared, "cursor", b"cursor bytes")
        both["variants"] = claude["variants"]
        refused = self.call(both, accepted=False)
        self.assertIn("unrecorded snapshot", refused["reason"])
        self.assertIsNone(self.call({"operation": "inspect"})["last_issued"])
