"""Correspondence against exact retained processors; constructed evidence only.

Profile qualification requires the two historical Git objects locally. Tests
never fetch from the network; shallow/source-only checkouts report skips rather
than substituting current code for a historical profile.
"""

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import behavior_eval_receipts as core
from scripts import behavior_eval_inventory as inventory
from tests import test_behavior_eval_receipts as fixtures


PROFILES = {"p957": "957550119aca20a31a26f4e5f9a3f09a2d6bd148",
            "p24": "24c2d712a0be6a95958713ec80c7e06a89abdc6c"}
PROCESSING_FILES = ("scripts/behavior_eval_receipts.py", "scripts/behavior_eval_corpora.py",
                    "scripts/behavior_eval_inventory.py", "release/behavior-eval-policy.json",
                    "release/behavior-eval-receipt-v1.schema.json")


class ProfileCorrespondenceTests(unittest.TestCase):
    def fixture(self, profile):
        source = Path(__file__).resolve().parents[1]
        revision = PROFILES[profile]
        observed = subprocess.run(["git", "cat-file", "-e", revision + "^{commit}"],
                                  cwd=source, capture_output=True)
        if observed.returncode:
            self.skipTest(f"Retained {profile} source unavailable; historical compatibility not qualified")
        case = fixtures.ReceiptWorkflowTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.git("fetch", "--quiet", "--no-tags", str(source), revision)
        for path in PROCESSING_FILES:
            raw = subprocess.check_output(["git", "show", revision + ":" + path], cwd=source)
            (case.repo / path).write_bytes(raw)
        case.candidate = case.commit("retained processor source")
        return case

    def receipt(self, case, method="prepared", *, normalized=False, per_case=False):
        if method == "prepared":
            snapshot = core.input_closure(case.repo, case.candidate, case.spec, profile="p24", method="prepared")
            receipt = core.produce(case.repo, snapshot, case.results(snapshot))
        else:
            path = case.normalized_retained_results() if normalized else case.retained_results()
            if per_case:
                data = json.loads(path.read_text())
                data["case_runtime_inputs"] = [{"case_id": run["case_id"],
                    "runtime_inputs": data["runtime_inputs"]} for run in data["runs"] if run["repetition"] == 1]
                path.write_text(json.dumps(data))
            spec = case.private / "descriptor.json"
            spec.write_text(json.dumps(case.spec))
            output = subprocess.check_output([sys.executable, str(case.repo / "scripts/behavior_eval_receipts.py"),
                "--repository", str(case.repo), "reconcile", "--revision", case.candidate,
                "--processing-revision", case.candidate, "--skill-spec", str(spec), "--results", str(path)])
            receipt = json.loads(output)
        return receipt

    def check(self, case, receipt, profile, *, candidate=None):
        raw = core.canonical_bytes(receipt)
        binding = {"path": "receipts/example/writing.json", "raw_sha256": hashlib.sha256(raw).hexdigest(),
                   "mode": "100644", "evaluated_revision": case.candidate,
                   "method": "reconciled-after-run" if receipt.get("method") == "reconciled-after-run" else "prepared",
                   "profile": profile, "processing": receipt.get("processing"),
                   "producer_procedure_revision": case.candidate}
        return core.check_correspondence(case.repo, candidate_revision=candidate or case.candidate,
            descriptor=case.spec, receipt_bytes=raw, binding=binding)

    def test_prepared_profiles_execute_retained_check_and_accept_missing_method(self):
        for profile in PROFILES:
            with self.subTest(profile=profile):
                case = self.fixture(profile)
                receipt = self.receipt(case)
                del receipt["method"]
                result = self.check(case, receipt, profile)
                self.assertEqual(result["status"], "pass", result)
                self.assertEqual(result["historical_validation_implementation"]["revision"], PROFILES[profile])
                self.assertEqual(result["historical"]["candidate_revision"], case.candidate)
                self.assertEqual(result["historical"]["skills"][0]["status"], "pass")
                self.assertEqual(result["member_qualification"], "not-evaluated")

    def test_reconciled_profiles_preserve_uniform_and_per_case_results(self):
        for profile, per_case in (("p957", False), ("p24", False), ("p24", True)):
            for normalized in (False, True):
                with self.subTest(profile=profile, per_case=per_case, normalized=normalized):
                    case = self.fixture(profile)
                    receipt = self.receipt(case, "reconciled-after-run", normalized=normalized, per_case=per_case)
                    original = core.canonical_bytes(receipt)
                    result = self.check(case, receipt, profile)
                    self.assertEqual(result["status"], "pass", result)
                    self.assertEqual(result["failed_grade_count"], 1)
                    self.assertEqual(result["processing"], receipt["processing"])
                    self.assertEqual(core.canonical_bytes(receipt), original)

    def test_foreign_profile_and_failed_threshold_cannot_pass(self):
        case = self.fixture("p24")
        source = Path(__file__).resolve().parents[1]
        case.git("fetch", "--quiet", "--no-tags", str(source), PROFILES["p957"])
        receipt = self.receipt(case)
        result = self.check(case, receipt, "p957")
        self.assertEqual((result["status"], result["reason_code"]), ("fail", "processing-mismatch"))
        receipt["runs"][0]["expectations"][0]["passed"] = False
        result = self.check(case, receipt, "p24")
        self.assertEqual((result["status"], result["reason_code"]), ("fail", "historical-failed"))
        self.assertIsNotNone(result["receipt_raw_sha256"])
        self.assertIsNotNone(result["receipt_sha256"])
        self.assertIsNone(result["input_identity"])

    def test_squash_without_source_ancestry_preserves_closure_but_mode_change_fails(self):
        case = self.fixture("p24")
        receipt = self.receipt(case)
        tree = case.git("rev-parse", case.candidate + "^{tree}")
        landed = case.git("commit-tree", tree, "-p", case.base, "-m", "squashed source")
        self.assertNotEqual(landed, case.candidate)
        self.assertEqual(self.check(case, receipt, "p24", candidate=landed)["status"], "pass")
        case.git("update-index", "--chmod=+x", case.prefix + "/SKILL.md")
        mode_tree = case.git("write-tree")
        mode_commit = case.git("commit-tree", mode_tree, "-p", landed, "-m", "mode changed")
        result = self.check(case, receipt, "p24", candidate=mode_commit)
        self.assertEqual((result["status"], result["reason_code"]), ("fail", "closure-mismatch"))
        self.assertEqual(result["diagnostics"][0]["changes"], ["mode"])

    def landed_fixture(self, profile="p24"):
        case = self.fixture(profile)
        case.write("release/provingkit/definition-v1.json", {"membership": {"members": [
            {"id": "example", "content_identity": {"path": "release/plugin-content-locks/example.json"}}]}})
        case.write("plugins/example/topology.json", {"skills": {"writing": {}}})
        case.base = case.commit("complete base inventory")
        case.write(case.prefix + "/SKILL.md", "The reviewed changed skill.\n")
        case.candidate = case.commit("evaluated source")
        described = inventory.descriptor(case.repo, case.candidate, "example/writing")
        self.assertEqual(described["status"], "ready", described)
        case.spec = described["descriptor"]
        snapshot = inventory.prepare(case.repo, case.candidate, "example/writing")
        path = case.results(snapshot)
        cases, triggers = described["cases"], described["triggers"]
        for artifact in case.private.iterdir():
            data = json.loads(artifact.read_text())
            if "case_id" in data:
                data["case_id"] = (triggers[int(data["case_id"]) - 1]["case_id"]
                    if artifact.name.startswith("trigger-") else cases[0]["case_id"])
                artifact.write_text(json.dumps(data))
        for artifact in case.private.glob("grading-*.json"):
            data = json.loads(artifact.read_text())
            output = case.private / f"output-{data['repetition']}.txt"
            data["executor_output_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
            artifact.write_text(json.dumps(data))
        data = json.loads(path.read_text())
        for row in data["runs"]:
            row["case_id"] = cases[0]["case_id"]
        for index, row in enumerate(data["triggers"]):
            row["case_id"] = triggers[index]["case_id"]
        path.write_text(json.dumps(data))
        receipt = core.produce(case.repo, snapshot, path)
        raw = core.canonical_bytes(receipt)
        receipt_path = "release/receipts/example/writing.json"
        case.write(receipt_path, raw.decode())
        head = case.commit("reviewed Receipt")
        tree = case.git("rev-parse", head + "^{tree}")
        candidate = case.git("commit-tree", tree, "-p", case.base, "-m", "squash")
        binding = {"path": receipt_path, "raw_sha256": hashlib.sha256(raw).hexdigest(),
                   "mode": "100644", "evaluated_revision": case.candidate, "method": "prepared",
                   "profile": profile, "processing": None, "producer_procedure_revision": case.candidate}
        context = {"contract": "provingkit.receipt-correspondence/v1", "original_base": case.base,
                   "reviewed_head": head, "reviewed_target": case.base, "operation": "squash",
                   "consumer_revision": case.candidate, "procedure_revision": case.candidate,
                   "receipt_root": "release/receipts", "receipts": {"example/writing": binding}}
        landing = {"contract": context["contract"], "context_sha256": core.document_digest(context),
                   "operation": "squash", "reviewed_head": head, "target_before": case.base,
                   "candidate_revision": candidate}
        return case, context, landing

    def test_complete_landed_check_reads_committed_receipts_and_preserves_original_base(self):
        case, context, landing = self.landed_fixture()
        case.write("release/receipts/example/writing.json", "dirty invalid JSON")
        result = inventory.check_landed(case.repo, context=context, landing=landing)
        self.assertEqual(result["status"], "pass", result)

        self.assertEqual(result["candidate_revision"], landing["candidate_revision"])
        row = result["skills"][0]
        self.assertEqual(row["reviewed_receipt"]["oid"], row["landed_receipt"]["oid"])
        self.assertEqual(row["landed_correspondence"]["historical_validation_implementation"]["revision"], PROFILES["p24"])
        # An independently retained B need not be an ancestor of H or C.
        tree = case.git("rev-parse", case.base + "^{tree}")
        context["original_base"] = case.git("commit-tree", tree, "-m", "independent comparison base")
        landing["context_sha256"] = core.document_digest(context)
        result = inventory.check_landed(case.repo, context=context, landing=landing)
        self.assertEqual(result["status"], "pass", result)

    def test_normalized_prepared_p957_executes_its_matching_profile(self):
        case, context, landing = self.landed_fixture("p957")
        result = inventory.check_landed(case.repo, context=context, landing=landing)
        self.assertEqual(result["status"], "pass", result)
        row = result["skills"][0]["landed_correspondence"]
        self.assertEqual(row["historical_validation_implementation"]["revision"], PROFILES["p957"])
        self.assertEqual(row["processing_binding"]["basis"], "source-snapshot")

    def test_reviewed_head_requires_receipt_binding_not_landed_source_correspondence(self):
        case, context, landing = self.landed_fixture()
        case.write(case.prefix + "/SKILL.md", "Reviewed branch source differs from the landed source.\n")
        context["reviewed_head"] = landing["reviewed_head"] = case.commit("reviewed source only")
        landing["context_sha256"] = core.document_digest(context)
        result = inventory.check_landed(case.repo, context=context, landing=landing)
        self.assertEqual(result["status"], "pass", result)
        row = result["skills"][0]
        self.assertEqual(row["reviewed_binding"]["status"], "pass")
        self.assertEqual(row["landed_correspondence"]["status"], "pass")

    def test_rejected_landing_preserves_available_context_and_candidate_identities(self):
        case, context, landing = self.landed_fixture()
        landing["target_before"] = context["reviewed_head"]
        result = inventory.check_landed(case.repo, context=context, landing=landing)
        self.assertEqual((result["status"], result["reason_code"]), ("fail", "target-moved"))
        for field in ("original_base", "reviewed_head", "consumer_revision", "procedure_revision"):
            self.assertEqual(result[field], context[field])
        for field in ("target_before", "candidate_revision"):
            self.assertEqual(result[field], landing[field])
        self.assertEqual(result["context_sha256"], core.document_digest(context))

        landing["candidate_revision"] = "f" * 40
        result = inventory.check_landed(case.repo, context=context, landing=landing)
        self.assertEqual((result["status"], result["reason_code"]), ("fail", "provenance-missing"))
        self.assertIsNone(result["candidate_revision"])
        self.assertEqual(result["original_base"], context["original_base"])
        self.assertEqual(result["target_before"], landing["target_before"])

    def test_changed_h_receipt_and_changed_c_receipt_have_distinct_failures(self):
        case, context, landing = self.landed_fixture()
        case.write("release/receipts/example/writing.json", "malformed changed evidence")
        changed = case.commit("changed Receipt")
        h_context, h_landing = copy.deepcopy(context), copy.deepcopy(landing)
        h_context["reviewed_head"] = h_landing["reviewed_head"] = changed
        h_landing["context_sha256"] = core.document_digest(h_context)
        result = inventory.check_landed(case.repo, context=h_context, landing=h_landing)
        self.assertEqual(result["reason_code"], "reviewed-receipt-mismatch", result)
        tree = case.git("rev-parse", changed + "^{tree}")
        landing["candidate_revision"] = case.git("commit-tree", tree, "-p", case.base, "-m", "changed squash")
        result = inventory.check_landed(case.repo, context=context, landing=landing)
        self.assertEqual(result["reason_code"], "receipt-changed", result)

    def test_cli_distinguishes_unsupported_operation_from_malformed_request(self):
        case, context, landing = self.landed_fixture()
        script = Path(__file__).resolve().parents[1] / "scripts/behavior_eval_inventory.py"
        for operation, status, code in (("merge", "fail", 1), ([], "error", 2)):
            with self.subTest(operation=operation):
                context["operation"] = landing["operation"] = operation
                landing["context_sha256"] = core.document_digest(context)
                cpath, lpath = case.private / "context.json", case.private / "landing.json"
                cpath.write_text(json.dumps(context)); lpath.write_text(json.dumps(landing))
                process = subprocess.run([sys.executable, str(script), "--repository", str(case.repo),
                    "check-landed", "--context", str(cpath), "--landing", str(lpath)], capture_output=True, text=True)
                self.assertEqual(process.returncode, code, process.stdout + process.stderr)
                self.assertEqual(json.loads(process.stdout)["status"], status)

    def test_cli_reports_missing_validation_dependency_as_unavailable_machinery(self):
        case, context, landing = self.landed_fixture()
        script = Path(__file__).resolve().parents[1] / "scripts/behavior_eval_inventory.py"
        cpath, lpath = case.private / "context.json", case.private / "landing.json"
        cpath.write_text(json.dumps(context))
        lpath.write_text(json.dumps(landing))
        process = subprocess.run([sys.executable, "-S", str(script), "--repository", str(case.repo),
            "check-landed", "--context", str(cpath), "--landing", str(lpath)], capture_output=True, text=True)
        self.assertEqual(process.returncode, 2, process.stdout + process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual((result["status"], result["reason_code"]),
                         ("error", "historical-runtime-unavailable"))
