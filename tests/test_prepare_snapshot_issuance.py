"""Consumer examples for the local, cooperating snapshot issuer CLI."""

import json
import hashlib
import subprocess
import shutil
import sys
import tempfile
import tarfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/prepare_snapshot_issuance.py"
SOURCE = "1" * 40


def observe_variant_bytes(directory):
    return {name: (directory / name).read_bytes()
            for name in ("artifact.tar.gz", "RECEIPT.json", "modes.tsv")}


def pack_projection(output, workspace):
    """Fixture protocol driver; no claim of production packing qualification."""
    archive = workspace / "artifact.tar.gz"
    with tarfile.open(archive, "w:gz") as packed:
        packed.add(output, arcname="projected")
    modes = workspace / "modes.tsv"
    modes.write_text("path\tmode\torigin\n" + "".join(
        f"{path.relative_to(output).as_posix()}\t{path.stat().st_mode & 0o777:04o}\tfixture\n"
        for path in sorted(output.rglob("*")) if path.is_file()))
    return {"artifact.tar.gz": archive, "RECEIPT.json": output / "RECEIPT.json", "modes.tsv": modes}


def project_issuance_variant(prepared, workspace):
    """Drive the actual producer and return consumer observations and immutable inputs."""
    record = workspace / "producer-preparation.json"
    record.write_text(json.dumps(prepared, sort_keys=True, separators=(",", ":")) + "\n")
    output = workspace / "projected"
    result = subprocess.run([sys.executable, str(ROOT / "scripts/build_release_artifacts.py"),
                             "--source", str(ROOT), "--output", str(output), "--target", "claude",
                             "--snapshot-record", str(record)], capture_output=True, text=True)
    observation = {"accepted": result.returncode == 0, "diagnostic": result.stderr}
    if not observation["accepted"]:
        return observation
    receipt = json.loads((output / "RECEIPT.json").read_text())
    observation.update(member_versions={member.name: json.loads((member / "plugin.json").read_text())["version"]
                                       for member in (output / "plugins").iterdir()},
                       delivery=receipt["delivery"], source_commit=receipt["source"]["commit"])
    observation["files"] = pack_projection(output, workspace)
    observation["file_bytes"] = {name: path.read_bytes() for name, path in observation["files"].items()}
    return observation


class SnapshotIssuanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.state = self.root / "state.sqlite"

    def call(self, request, *, accepted=True, clock=None, state=None,
             swap_before_connect=None, system_alias=None):
        path = self.root / "request.json"
        path.write_text(json.dumps(request))
        command = [sys.executable, str(SCRIPT)]
        if clock is not None:
            command = [sys.executable, "-c",
                       "import runpy,sys,time; time.time=lambda: " + str(clock)
                       + "; script=sys.argv.pop(1); sys.path.insert(0,str(__import__('pathlib').Path(script).parent));"
                       + "runpy.run_path(script,run_name='__main__')", str(SCRIPT)]
        if swap_before_connect is not None:
            selected, displaced, replacement = map(str, swap_before_connect)
            command = [sys.executable, "-c", """
import os
import runpy
import sqlite3
import sys

script, selected, displaced, replacement = sys.argv[1:5]
sys.argv = [script, *sys.argv[5:]]
real_connect = sqlite3.connect

def raced_connect(database, *args, **kwargs):
    os.rename(selected, displaced)
    os.rename(replacement, selected)
    return real_connect(database, *args, **kwargs)

sqlite3.connect = raced_connect
sys.path.insert(0, str(__import__('pathlib').Path(script).parent))
runpy.run_path(script, run_name='__main__')
""", str(SCRIPT), selected, displaced, replacement]
        if system_alias is not None:
            alias, target = map(str, system_alias)
            command = [sys.executable, "-c", """
import os
import runpy
import stat
import sys
from pathlib import Path

script, alias_value, target_value = sys.argv[1:4]
sys.argv = [script, *sys.argv[4:]]
alias = Path(alias_value)
target = Path(target_value)
real_lstat = Path.lstat
real_readlink = Path.readlink
real_resolve = Path.resolve
root_metadata = alias.parent.stat()
resolved_target = real_resolve(target, strict=True)
fields = list(root_metadata)
fields[0] = stat.S_IFLNK | 0o777
alias_metadata = os.stat_result(fields)

def alias_lstat(path):
    return alias_metadata if path == alias else real_lstat(path)

def alias_readlink(path):
    return target if path == alias else real_readlink(path)

def alias_resolve(path, *args, **kwargs):
    return resolved_target if path == alias else real_resolve(path, *args, **kwargs)

Path.lstat = alias_lstat
Path.readlink = alias_readlink
Path.resolve = alias_resolve
sys.path.insert(0, str(Path(script).parent))
runpy.run_path(script, run_name='__main__')
""", str(SCRIPT), alias, target]
        state = self.state if state is None else state
        result = subprocess.run(
            [*command, "--state", str(state), "--request", str(path)],
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

    def configure_cloud(self, *, accepted=True, **changes):
        return self.call({"operation": "configure-cloud-member", "member": "versionkeeping",
                          "floor": "1.0.0", "target_release": "1.0.1",
                          "preceding_cut": "1.0.1-0", "next_named_release": "1.0.1-alpha.1",
                          **changes}, accepted=accepted)

    def prepare_cloud(self, request_id="cloud-first", members=None, source=SOURCE, **options):
        return self.call({"operation": "prepare-cloud", "request_id": request_id,
                          "source_commit": source, "members": ["versionkeeping"] if members is None else members},
                         **options)

    def test_cloud_member_exceeds_stable_floor_without_changing_kit_identity(self):
        self.initialize()
        self.configure_cloud()
        first = self.prepare_cloud()
        self.assertEqual(first["version"], "0.1.0-alpha.7.snapshot.1")
        self.assertEqual(first["cloud_members"], {"versionkeeping": {
            "floor": "1.0.0", "target_release": "1.0.1", "preceding_cut": "1.0.1-0",
            "next_named_release": "1.0.1-alpha.1", "sequence": 1,
            "version": "1.0.1-0.snapshot.1"}})
        self.assertEqual(first["source_commit"], SOURCE)
        self.assertEqual(first["schema"], "provingkit-cloud-snapshot-preparation-v1")
        self.assertEqual(self.prepare_cloud(), first)
        self.assertEqual(self.prepare_cloud("cloud-second")["cloud_members"]["versionkeeping"]["version"],
                         "1.0.1-0.snapshot.2")
        self.assertNotIn("cloud_members", self.prepare("ordinary"))

    def git(self, *arguments):
        return subprocess.check_output(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
             "-c", "commit.gpgsign=false", *arguments], cwd=self.transport, text=True,
        ).strip()

    def publication(self, record, target="claude", content=b"retained archive", files=None):
        self.transport = self.root / "transport"
        if not self.transport.exists():
            self.transport.mkdir()
            self.git("init", "-q")
            self.git("commit", "--allow-empty", "-qm", "test: transport creation base")
            self.initial_transport_base = self.git("rev-parse", "HEAD")
        directory = self.transport / "ad-hoc" / record["source_commit"] / record["version"] / target
        directory.mkdir(parents=True, exist_ok=True)
        preparation_bytes = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
        receipt = {"source": {"commit": record["source_commit"]}, "target": target,
                   "delivery": {"version": record["version"], "request_id": record["request_id"],
                                "preparation_sha256": hashlib.sha256(preparation_bytes).hexdigest()}}
        if "cloud_members" in record:
            receipt["delivery"]["cloud_members"] = record["cloud_members"]
        (directory / "artifact.tar.gz").write_bytes(content)
        (directory / "RECEIPT.json").write_text(json.dumps(receipt))
        (directory / "modes.tsv").write_bytes(b"path\tmode\torigin\n")
        if files is not None:
            for name, path in files.items():
                shutil.copy2(path, directory / name)
        self.git("add", ".")
        self.git("commit", "-qm", "test: prepared transport")
        boundary = getattr(self, "published_commit", self.initial_transport_base)
        plan = {"status": "ready", "source_sha": self.git("rev-parse", "HEAD"),
                "outgoing_shas": self.git("rev-list", boundary + "..HEAD").splitlines(),
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

    def reconcile(self, request, *, verified=True, attempted=True, accepted=True, **result_changes):
        plan = json.loads(Path(request["publication_plan"]).read_text())
        result = {"status": "verified" if verified else "blocked", "source_sha": plan["source_sha"],
                  "destination": plan["destination"], "push_attempted": attempted,
                  "reasons": [] if verified else [{"kind": "constructed-unknown"}],
                  "postchecks": [{"kind": "remote_ref_equals", "ref": plan["destination"]["ref"],
                                  "endpoint_fingerprint": plan["destination"]["endpoint_fingerprint"],
                                  "sha": plan["source_sha"]}] if verified else []}
        result.update(result_changes)
        path = self.root / (request["request_id"] + "-result.json")
        path.write_text(json.dumps(result))
        response = self.call({"operation": "reconcile", "request_id": request["request_id"],
                              "publication_result": str(path)}, accepted=accepted)
        if response.get("exposure") == "verified":
            self.published_commit = plan["source_sha"]
        return response

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

    def test_cloud_issuance_retains_member_and_kit_identity_in_one_record(self):
        self.initialize()
        self.configure_cloud()
        prepared = self.prepare_cloud()
        issued = self.call(self.publication(prepared))
        self.assertEqual(issued["version"], "0.1.0-alpha.7.snapshot.1")
        state = self.call({"operation": "inspect"})
        self.assertEqual(state["cloud_members"]["versionkeeping"]["last_issued"], "1.0.1-0.snapshot.1")
        self.assertEqual(state["versions"]["0.1.0-alpha.7.snapshot.1"]["preparation"], prepared)
        self.assertEqual(state["pending"], "cloud-first")

    def test_uncertain_cloud_exposure_keeps_configuration_and_issue_barriers(self):
        self.initialize()
        self.configure_cloud()
        original = self.publication(self.prepare_cloud())
        self.call(original)
        self.assertEqual(self.reconcile(original, verified=False)["exposure"], "pending")
        before = self.call({"operation": "inspect"})
        refused = self.configure_cloud(accepted=False, floor="1.0.1", target_release="1.0.2",
                                       preceding_cut="1.0.2-0", next_named_release="1.0.2-alpha.1")
        self.assertIn("pending", refused["reason"])
        self.assertEqual(self.call({"operation": "inspect"}), before)
        later = self.publication(self.prepare_cloud("cloud-later"))
        self.assertIn("pending", self.call(later, accepted=False)["reason"])
        self.assertEqual(self.call(original)["exposure"], "pending")
        self.assertEqual(self.reconcile(original)["exposure"], "verified")
        self.call(later)
        self.assertEqual(self.call({"operation": "inspect"})["cloud_members"]["versionkeeping"]["last_issued"],
                         "1.0.1-0.snapshot.2")

    def test_cloud_configuration_preserves_floors_and_declared_cut_order(self):
        self.initialize()
        self.configure_cloud()
        reserved = self.prepare_cloud()
        before = self.call({"operation": "inspect"})
        self.configure_cloud(accepted=False, floor="0.9.9")
        self.assertEqual(self.call({"operation": "inspect"}), before)
        self.configure_cloud(accepted=False, next_named_release="1.0.1-beta.1")
        self.configure_cloud(preceding_cut="1.0.1-alpha.1", next_named_release="1.0.1")
        self.assertIn("stale", self.call(self.publication(reserved), accepted=False)["reason"])
        self.configure_cloud(accepted=False)
        self.assertEqual(self.prepare_cloud("after-member-cut")["cloud_members"]["versionkeeping"]["version"],
                         "1.0.1-alpha.1.snapshot.2")
        self.configure_cloud(preceding_cut="1.0.1", next_named_release="1.0.1")
        self.prepare_cloud("closed", accepted=False)
        self.configure_cloud(floor="1.0.1", target_release="1.0.2", preceding_cut="1.0.2-0",
                             next_named_release="1.0.2-alpha.1")
        self.assertEqual(self.prepare_cloud("new-member-target")["cloud_members"]["versionkeeping"]["version"],
                         "1.0.2-0.snapshot.3")

    def test_cloud_reservations_survive_kit_retarget_without_reusing_member_versions(self):
        self.initialize(preceding_cut="0.1.0-rc.2", next_named_release="0.1.0")
        self.configure_cloud()
        first = self.prepare_cloud()
        publication = self.publication(first)
        self.call(publication)
        self.reconcile(publication)
        self.prepare_cloud("consumed-unused")
        self.call({"operation": "advance-cut", "preceding_cut": "0.1.0", "next_named_release": "0.1.0"})
        self.call({"operation": "retarget", "target_release": "0.2.0", "next_named_release": "0.2.0-alpha.1"})
        later = self.prepare_cloud("next-kit")
        self.assertEqual(later["version"], "0.2.0-0.snapshot.1")
        self.assertEqual(later["cloud_members"]["versionkeeping"]["version"], "1.0.1-0.snapshot.3")
        self.assertEqual(self.prepare_cloud(), first)
        self.call(self.publication(later))
        self.assertEqual(self.call({"operation": "inspect"})["cloud_members"]["versionkeeping"]["last_issued"],
                         "1.0.1-0.snapshot.3")

    def test_cloud_variant_addition_and_withdrawal_preserve_original_identity(self):
        self.initialize()
        self.configure_cloud()
        first = self.prepare_cloud()
        initial = self.publication(first)
        self.call(initial)
        self.reconcile(initial)
        original = self.call({"operation": "inspect"})["versions"][first["version"]]
        self.call({"operation": "withdraw", "version": first["version"]})
        later = self.publication(self.prepare_cloud("cloud-second"), content=b"later archive")
        self.call(later)
        self.reconcile(later)
        addition = self.publication(first, "cursor", b"new target archive")
        addition.update(operation="add-variants", request_id="cloud-cursor", version=first["version"],
                        source_commit=SOURCE)
        self.call(addition)
        self.reconcile(addition)
        state = self.call({"operation": "inspect"})
        self.assertEqual(state["versions"][first["version"]]["preparation"], first)
        self.assertEqual(state["versions"][first["version"]]["variants"]["claude"], original["variants"]["claude"])
        self.assertEqual(state["cloud_members"]["versionkeeping"]["last_issued"], "1.0.1-0.snapshot.2")
        changed = self.publication(first, "cursor", b"conflicting bytes")
        changed.update(operation="add-variants", request_id="cloud-reuse", version=first["version"],
                       source_commit=SOURCE)
        self.assertIn("existing variant", self.call(changed, accepted=False)["reason"])
        output = self.root / "retained-cloud"
        self.call({"operation": "redeliver", "version": first["version"], "target": "claude", "output": str(output)})
        self.assertEqual((output / "artifact.tar.gz").read_bytes(), b"retained archive")
        self.assertEqual(json.loads((output / "RECEIPT.json").read_text())["delivery"]["cloud_members"], first["cloud_members"])

    def test_competing_cloud_reservations_consume_distinct_member_sequences(self):
        self.initialize()
        self.configure_cloud()
        processes = []
        for number in range(4):
            request = {"operation": "prepare-cloud", "request_id": f"parallel-{number}",
                       "source_commit": SOURCE, "members": ["versionkeeping"]}
            path = self.root / (request["request_id"] + ".json")
            path.write_text(json.dumps(request))
            processes.append(subprocess.Popen([sys.executable, str(SCRIPT), "--state", str(self.state),
                                               "--request", str(path)], stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE, text=True))
        records = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, stdout + stderr)
            records.append(json.loads(stdout))
        self.assertEqual({record["cloud_members"]["versionkeeping"]["version"] for record in records},
                         {"1.0.1-0.snapshot.1", "1.0.1-0.snapshot.2", "1.0.1-0.snapshot.3", "1.0.1-0.snapshot.4"})
        self.assertEqual(self.prepare_cloud("next")["cloud_members"]["versionkeeping"]["version"], "1.0.1-0.snapshot.5")

    def test_cloud_inputs_and_conflicting_preparation_reuse_do_not_consume_reservations(self):
        self.initialize()
        self.configure_cloud()
        before = self.call({"operation": "inspect"})
        for changes in ({"member": "unknown"}, {"floor": "1.0.0+metadata"},
                        {"target_release": "1.0.0", "preceding_cut": "1.0.0-0",
                         "next_named_release": "1.0.0-alpha.1"}):
            self.configure_cloud(accepted=False, **changes)
        for members in ([], ["unknown"], ["versionkeeping", "versionkeeping"], [7], "versionkeeping"):
            self.prepare_cloud("invalid", members, accepted=False)
        self.assertEqual(self.call({"operation": "inspect"}), before)
        original = self.prepare_cloud()
        self.call({"operation": "prepare", "request_id": "cloud-first", "source_commit": SOURCE}, accepted=False)
        self.prepare("ordinary")
        self.prepare_cloud("ordinary", accepted=False)
        self.call({"operation": "prepare-cloud", "request_id": "cloud-first", "source_commit": "2" * 40,
                   "members": ["versionkeeping"]}, accepted=False)
        self.assertEqual(self.prepare_cloud(), original)
        self.assertEqual(self.prepare_cloud("next")["cloud_members"]["versionkeeping"]["version"], "1.0.1-0.snapshot.2")

    def test_successful_preparation_cannot_issue_a_receipt_with_the_wrong_member_version(self):
        self.initialize()
        self.configure_cloud()
        prepared = self.prepare_cloud()
        request = self.publication(prepared)
        receipt_path = Path(request["variants"]["claude"]["RECEIPT.json"])
        receipt = json.loads(receipt_path.read_text())
        receipt["delivery"]["cloud_members"]["versionkeeping"]["version"] = "1.0.0"
        receipt_path.write_text(json.dumps(receipt))
        before = self.call({"operation": "inspect"})
        self.assertIn("receipt", self.call(request, accepted=False)["reason"])
        self.assertEqual(self.call({"operation": "inspect"}), before)

    def test_issuance_rechecks_a_member_floor_changed_after_preparation(self):
        self.initialize()
        self.configure_cloud()
        stale = self.prepare_cloud()
        self.configure_cloud(floor="1.0.1-0.snapshot.1")
        before = self.call({"operation": "inspect"})
        self.assertIn("stale", self.call(self.publication(stale), accepted=False)["reason"])
        self.assertEqual(self.call({"operation": "inspect"}), before)
        self.assertEqual(self.prepare_cloud("above-new-floor")["cloud_members"]["versionkeeping"]["version"],
                         "1.0.1-0.snapshot.2")

    def test_first_cloud_issue_cannot_regress_a_prior_synchronized_member_identity(self):
        self.initialize()
        ordinary = self.publication(self.prepare())
        self.call(ordinary)
        self.reconcile(ordinary)
        self.configure_cloud(floor="0.0.9", target_release="0.1.0", preceding_cut="0.1.0-0",
                             next_named_release="0.1.0-alpha.1")
        cloud = self.prepare_cloud()
        self.assertEqual(cloud["cloud_members"]["versionkeeping"]["version"], "0.1.0-0.snapshot.1")
        before = self.call({"operation": "inspect"})
        self.assertIn("last issued", self.call(self.publication(cloud), accepted=False)["reason"])
        self.assertEqual(self.call({"operation": "inspect"}), before)

    def test_cloud_issue_rechecks_later_synchronized_member_identity(self):
        self.initialize()
        self.configure_cloud(floor="0.0.9", target_release="0.1.0", preceding_cut="0.1.0-0",
                             next_named_release="0.1.0-alpha.1")
        first = self.publication(self.prepare_cloud())
        self.call(first)
        self.reconcile(first)
        ordinary = self.publication(self.prepare("synchronized-later"))
        self.call(ordinary)
        self.reconcile(ordinary)
        later = self.prepare_cloud("cloud-after-synchronized")
        before = self.call({"operation": "inspect"})
        self.assertIn("last issued", self.call(self.publication(later), accepted=False)["reason"])
        self.assertEqual(self.call({"operation": "inspect"}), before)

    def test_cloud_issue_rechecks_later_omitted_member_identity(self):
        self.initialize()
        self.configure_cloud(floor="0.0.9", target_release="0.1.0", preceding_cut="0.1.0-0",
                             next_named_release="0.1.0-alpha.1")
        first = self.publication(self.prepare_cloud())
        self.call(first)
        self.reconcile(first)
        self.configure_cloud(member="mergecraft")
        other = self.publication(self.prepare_cloud("another-selected-member", ["mergecraft"]))
        self.call(other)
        self.reconcile(other)
        later = self.prepare_cloud("cloud-after-omission")
        before = self.call({"operation": "inspect"})
        self.assertIn("last issued", self.call(self.publication(later), accepted=False)["reason"])
        self.assertEqual(self.call({"operation": "inspect"}), before)

    def test_cancelled_cloud_attempt_keeps_member_high_water_and_consumed_sequence(self):
        self.initialize()
        self.configure_cloud()
        original = self.publication(self.prepare_cloud())
        self.call(original)
        self.assertEqual(self.reconcile(original, verified=False, attempted=False)["exposure"], "cancelled")
        self.assertEqual(self.call(original)["exposure"], "cancelled")
        self.assertEqual(self.prepare_cloud("later")["cloud_members"]["versionkeeping"]["version"], "1.0.1-0.snapshot.2")
        self.assertEqual(self.call({"operation": "inspect"})["cloud_members"]["versionkeeping"]["last_issued"],
                         "1.0.1-0.snapshot.1")

    def test_actual_projector_receipt_is_issued_and_retained_without_rebinding_member_identity(self):
        self.initialize()
        self.configure_cloud()
        source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        prepared = self.prepare_cloud(source=source)
        produced = project_issuance_variant(prepared, self.root)
        self.assertTrue(produced["accepted"], produced["diagnostic"])
        self.assertEqual(produced["member_versions"]["versionkeeping"], "1.0.1-0.snapshot.1")
        self.assertEqual(produced["delivery"]["version"], "0.1.0-alpha.7.snapshot.1")
        self.assertEqual(produced["source_commit"], source)
        publication = self.publication(prepared, files=produced["files"])
        self.call(publication)
        self.reconcile(publication)
        retained = self.root / "consumer-recovery"
        self.call({"operation": "redeliver", "version": "0.1.0-alpha.7.snapshot.1",
                   "target": "claude", "output": str(retained)})
        self.assertEqual(observe_variant_bytes(retained), produced["file_bytes"])

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

    def test_addition_identifier_cannot_become_a_preparation_or_break_recovery(self):
        self.initialize()
        prepared = self.prepare()
        initial = self.publication(prepared)
        self.call(initial)
        self.reconcile(initial)
        addition = self.publication(prepared, "cursor", b"cursor archive")
        addition.update(operation="add-variants", request_id="add-cursor", version=prepared["version"],
                        source_commit=SOURCE)
        original = self.call(addition)
        for exposure in ("pending", "verified"):
            before = self.call({"operation": "inspect"})
            refused = self.call({"operation": "prepare", "request_id": "add-cursor",
                                 "source_commit": SOURCE}, accepted=False)
            self.assertIn("identifier", refused["reason"])
            self.assertEqual(self.call({"operation": "inspect"}), before)
            recovered = self.call(addition)
            self.assertEqual(recovered["variants"], original["variants"])
            self.assertEqual(recovered["exposure"], exposure)
            if exposure == "pending":
                self.reconcile(addition)
        self.assertEqual(self.prepare("next")["version"], "0.1.0-alpha.7.snapshot.2")

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

    def test_rejected_verification_retains_attempt_and_pending_hold_across_reentry(self):
        self.initialize()
        request = self.publication(self.prepare())
        self.call(request)
        refused = self.reconcile(request, postchecks=[], accepted=False)
        self.assertIn("postcheck", refused["reason"])
        state = self.call({"operation": "inspect"})
        self.assertEqual(state["pending"], "first")
        self.assertEqual(state["deliveries"]["first"]["exposure"], "pending")
        self.assertTrue(state["deliveries"]["first"].get("attempt_observed"))
        refused = self.reconcile(request, verified=False, attempted=False, accepted=False)
        self.assertIn("earlier uncertain attempt", refused["reason"])
        later = self.publication(self.prepare("later"))
        self.assertIn("pending", self.call(later, accepted=False)["reason"])
        cut = {"operation": "advance-cut", "preceding_cut": "0.1.0-alpha.8",
               "next_named_release": "0.1.0-beta.1"}
        self.assertIn("pending", self.call(cut, accepted=False)["reason"])
        self.assertEqual(self.reconcile(request)["exposure"], "verified")
        self.assertIsNone(self.call({"operation": "inspect"})["pending"])

    def test_competing_issuers_cannot_both_cross_the_pending_exposure_boundary(self):
        self.initialize()
        earlier = self.publication(self.prepare("earlier"))
        retained_inputs = self.root / "earlier-inputs"
        shutil.copytree(Path(earlier["variants"]["claude"]["RECEIPT.json"]).parent, retained_inputs)
        earlier["variants"]["claude"] = {name: str(retained_inputs / name) for name in earlier["variants"]["claude"]}
        self.git("reset", "--hard", self.initial_transport_base)
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

    def test_ancestor_swap_cannot_redirect_the_state_database(self):
        selected = self.root / "selected"
        displaced = self.root / "displaced"
        replacement = self.root / "replacement"
        selected.mkdir(mode=0o700)
        replacement.mkdir(mode=0o700)
        selected_state = selected / "state.sqlite"
        replacement_state = replacement / "state.sqlite"
        request = {"operation": "initialize", "custody_owner": "selected-owner",
                   "endpoint_fingerprint": "sha256:" + "a" * 64,
                   "target_release": "0.1.0", "preceding_cut": "0.1.0-alpha.7",
                   "next_named_release": "0.1.0-alpha.8"}
        self.call(request, state=selected_state)
        self.call(dict(request, custody_owner="replacement-owner"), state=replacement_state)

        state = self.call({"operation": "inspect"}, state=selected_state,
                          swap_before_connect=(selected, displaced, replacement))

        self.assertEqual(state["custody_owner"], "selected-owner")

    def test_nonsticky_writable_state_ancestor_is_refused(self):
        shared = self.root / "shared"
        private = shared / "private"
        private.mkdir(parents=True, mode=0o700)
        shared.chmod(0o777)
        request = {"operation": "initialize", "custody_owner": "selected-owner",
                   "endpoint_fingerprint": "sha256:" + "a" * 64,
                   "target_release": "0.1.0", "preceding_cut": "0.1.0-alpha.7",
                   "next_named_release": "0.1.0-alpha.8"}

        refused = self.call(request, state=private / "state.sqlite", accepted=False)

        self.assertIn("ancestor is writable by other users", refused["reason"])
        self.assertFalse((private / "state.sqlite").exists())
        shared.chmod(0o700)

    def test_symlinked_state_ancestor_is_refused_without_touching_its_target(self):
        target = self.root / "target"
        private = target / "private"
        private.mkdir(parents=True, mode=0o700)
        alias = self.root / "alias"
        alias.symlink_to(target, target_is_directory=True)
        request = {"operation": "initialize", "custody_owner": "selected-owner",
                   "endpoint_fingerprint": "sha256:" + "a" * 64,
                   "target_release": "0.1.0", "preceding_cut": "0.1.0-alpha.7",
                   "next_named_release": "0.1.0-alpha.8"}

        self.call(request, state=alias / "private/state.sqlite", accepted=False)

        self.assertFalse((private / "state.sqlite").exists())

    def test_private_state_below_a_sticky_shared_ancestor_is_supported(self):
        shared = self.root / "shared"
        private = shared / "private"
        private.mkdir(parents=True, mode=0o700)
        shared.chmod(0o1777)
        request = {"operation": "initialize", "custody_owner": "selected-owner",
                   "endpoint_fingerprint": "sha256:" + "a" * 64,
                   "target_release": "0.1.0", "preceding_cut": "0.1.0-alpha.7",
                   "next_named_release": "0.1.0-alpha.8"}

        initialized = self.call(request, state=private / "state.sqlite")

        self.assertEqual(initialized["outcome"], "initialized")
        shared.chmod(0o700)

    def test_search_only_state_ancestor_supports_initialization_and_reentry(self):
        searchable = self.root / "searchable"
        private = searchable / "private"
        private.mkdir(parents=True, mode=0o700)
        state_path = private / "state.sqlite"
        searchable.chmod(0o111)
        request = {"operation": "initialize", "custody_owner": "selected-owner",
                   "endpoint_fingerprint": "sha256:" + "a" * 64,
                   "target_release": "0.1.0", "preceding_cut": "0.1.0-alpha.7",
                   "next_named_release": "0.1.0-alpha.8"}

        try:
            self.call(request, state=state_path)
            inspected = self.call({"operation": "inspect"}, state=state_path)
        finally:
            searchable.chmod(0o700)

        self.assertEqual(inspected["custody_owner"], "selected-owner")

    def test_system_alias_cannot_hide_a_nested_symlink(self):
        target = self.root / "target"
        private = target / "private"
        private.mkdir(parents=True, mode=0o700)
        state_path = private / "state.sqlite"
        request = {"operation": "initialize", "custody_owner": "selected-owner",
                   "endpoint_fingerprint": "sha256:" + "a" * 64,
                   "target_release": "0.1.0", "preceding_cut": "0.1.0-alpha.7",
                   "next_named_release": "0.1.0-alpha.8"}
        self.call(request, state=state_path)
        nested_alias = self.root / "nested-alias"
        nested_alias.symlink_to(target, target_is_directory=True)
        system_alias = Path(self.root.anchor) / "provingkit-snapshot-state-alias"

        self.call({"operation": "inspect"},
                  state=system_alias / "private/state.sqlite", accepted=False,
                  system_alias=(system_alias, nested_alias))

    def test_safe_one_hop_system_alias_is_supported(self):
        target = self.root / "target"
        private = target / "private"
        private.mkdir(parents=True, mode=0o700)
        state_path = private / "state.sqlite"
        request = {"operation": "initialize", "custody_owner": "selected-owner",
                   "endpoint_fingerprint": "sha256:" + "a" * 64,
                   "target_release": "0.1.0", "preceding_cut": "0.1.0-alpha.7",
                   "next_named_release": "0.1.0-alpha.8"}
        self.call(request, state=state_path)
        system_alias = Path(self.root.anchor) / "provingkit-snapshot-state-alias"

        inspected = self.call({"operation": "inspect"},
                              state=system_alias / "private/state.sqlite",
                              system_alias=(system_alias, target))

        self.assertEqual(inspected["custody_owner"], "selected-owner")

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

    def test_cancelled_generation_must_be_excluded_from_later_publication_ancestry(self):
        self.initialize()
        prepared = self.prepare()
        request = self.publication(prepared)
        self.call(request)
        self.assertEqual(self.reconcile(request, verified=False, attempted=False)["exposure"], "cancelled")
        shutil.rmtree(self.transport / "ad-hoc" / prepared["source_commit"] / prepared["version"])
        later_preparation = self.prepare("later")
        later = self.publication(later_preparation)
        self.assertIn("unrecorded snapshot", self.call(later, accepted=False)["reason"])
        self.git("reset", "--hard", self.initial_transport_base)
        reconstructed = self.publication(later_preparation)
        self.assertEqual(self.call(reconstructed)["version"], "0.1.0-alpha.7.snapshot.2")
        self.assertIn(prepared["version"], self.call({"operation": "inspect"})["versions"])

    def test_unrecorded_intermediate_variant_is_rejected_even_when_absent_at_tip(self):
        self.initialize()
        prepared = self.prepare()
        self.publication(prepared)
        self.publication(prepared, "cursor", b"unrecorded intermediate target")
        shutil.rmtree(self.transport / "ad-hoc" / SOURCE / prepared["version"] / "cursor")
        tip = self.publication(prepared)
        self.assertIn("unrecorded snapshot", self.call(tip, accepted=False)["reason"])
        self.assertIsNone(self.call({"operation": "inspect"})["pending"])

    def test_publication_cannot_expose_a_target_missing_from_the_issuance_record(self):
        self.initialize()
        prepared = self.prepare()
        claude = self.publication(prepared)
        both = self.publication(prepared, "cursor", b"cursor bytes")
        both["variants"] = claude["variants"]
        refused = self.call(both, accepted=False)
        self.assertIn("unrecorded snapshot", refused["reason"])
        self.assertIsNone(self.call({"operation": "inspect"})["last_issued"])

    def test_cancelled_addition_can_retry_retained_bytes_through_a_fresh_request(self):
        self.initialize()
        prepared = self.prepare()
        initial = self.publication(prepared)
        self.call(initial)
        self.reconcile(initial)
        agent = self.publication(prepared, "agent-plugins", b"agent plugins archive")
        agent.update(operation="add-variants", request_id="add-agent", version=prepared["version"], source_commit=SOURCE)
        self.call(agent)
        self.reconcile(agent)
        cancelled = self.publication(prepared, "cursor", b"cursor archive")
        cancelled.update(operation="add-variants", request_id="add-cursor", version=prepared["version"], source_commit=SOURCE)
        original = self.call(cancelled)
        self.reconcile(cancelled, verified=False, attempted=False)
        self.git("reset", "--hard", self.published_commit)
        retry = self.publication(prepared, "cursor", b"cursor archive")
        retry.update(operation="add-variants", request_id="retry-cursor", version=prepared["version"], source_commit=SOURCE)
        altered = dict(retry, request_id="changed-source", source_commit="2" * 40)
        self.assertIn("source identity", self.call(altered, accepted=False)["reason"])
        archive = Path(retry["variants"]["cursor"]["artifact.tar.gz"])
        archive.write_bytes(b"changed cursor bytes")
        self.assertIn("existing variant bytes", self.call(dict(retry, request_id="changed-bytes"), accepted=False)["reason"])
        archive.write_bytes(b"cursor archive")
        recovered = self.call(retry)
        self.assertEqual(recovered["version"], "0.1.0-alpha.7.snapshot.1")
        self.assertEqual(recovered["variants"], original["variants"])
        self.assertEqual(recovered["retry_of"], ["add-cursor"])
        self.reconcile(retry)
        state = self.call({"operation": "inspect"})
        self.assertEqual(state["last_issued"], "0.1.0-alpha.7.snapshot.1")
        self.assertEqual(state["deliveries"]["add-cursor"]["exposure"], "cancelled")
        self.assertEqual(state["versions"][prepared["version"]]["source_commit"], SOURCE)

    def test_uncertain_addition_blocks_fresh_retry_and_cut_transition(self):
        self.initialize()
        prepared = self.prepare()
        initial = self.publication(prepared)
        self.call(initial)
        self.reconcile(initial)
        addition = self.publication(prepared, "cursor", b"cursor archive")
        addition.update(operation="add-variants", request_id="add-cursor", version=prepared["version"], source_commit=SOURCE)
        self.call(addition)
        self.reconcile(addition, verified=False)
        retry = dict(addition, request_id="retry-cursor")
        self.assertIn("pending", self.call(retry, accepted=False)["reason"])
        self.assertIn("pending", self.call({"operation": "advance-cut", "preceding_cut": "0.1.0-alpha.8",
                                           "next_named_release": "0.1.0-beta.1"}, accepted=False)["reason"])
        self.assertEqual(self.call({"operation": "inspect"})["pending"], "add-cursor")
