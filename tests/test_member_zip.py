"""Synthetic contract checks through the approved derive/verify CLI seam."""

import hashlib
import copy
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import textwrap
import unittest
import warnings
import zipfile
import zlib


ROOT = Path(__file__).resolve().parent
CLI = ROOT.parent / "scripts" / "member_zip.py"
SLATE = ["rolecasting", "tricritical", "versionkeeping", "mergecraft",
         "artifact-customs", "proseweaving", "surreal-intercom"]
VERSION = "0.1.0-alpha.7.snapshot.9"
SOURCE = "1" * 40
PROJECTOR = "2" * 40
EPOCH = (1980, 1, 1, 0, 0, 0)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


class SyntheticParent:
    """Make disposable evidence without invoking issuer, projector, or publisher."""

    def __init__(self, directory, target="agent-plugins", version=VERSION):
        self.directory = directory
        directory.mkdir()
        self.target = target
        self.version = version
        self.files = {}
        self.modes = {}
        for member in SLATE:
            manifest = encoded({"name": member, "version": version})
            self.files[f"plugins/{member}/plugin.json"] = manifest
            if target == "claude":
                self.files[f"plugins/{member}/.claude-plugin/plugin.json"] = manifest
        self.files.update({
            "plugins/mergecraft/README.md": b"# Mergecraft synthetic\n",
            "plugins/mergecraft/skills/do/SKILL.md": b"---\nname: do\n---\n",
            "plugins/mergecraft/skills/do/run.py": b"print('synthetic')\n",
            "plugins/mergecraft/a/z": b"nested\n",
            "plugins/mergecraft/a.b": b"dotted\n",
        })
        self.catalog_path = (".agents/plugins/marketplace.json" if target == "agent-plugins"
                             else ".claude-plugin/marketplace.json")
        entries = [{"name": member, "source": {"source": "local", "path": f"./plugins/{member}"}}
                   if target == "agent-plugins" else
                   {"name": member, "source": f"./plugins/{member}", "version": version}
                   for member in SLATE]
        self.files[self.catalog_path] = encoded({"name": "provingkit", "plugins": entries})
        self.modes = {name: 0o644 for name in self.files}
        self.modes["plugins/mergecraft/skills/do/run.py"] = 0o755
        self.directories = {str(parent): 0o755 for name in self.files
                            for parent in PurePosixPath(name).parents if str(parent) != "."}
        self.directories["plugins/mergecraft"] = 0o750
        self.directories["plugins/mergecraft/skills/do"] = 0o750
        self.root_name = f"provingkit-ad-hoc-{SOURCE}-{version}-{target}"
        self.archive_path = directory / "artifact.tar.gz"
        self.receipt_path = directory / "RECEIPT.json"
        self.modes_path = directory / "modes.tsv"
        self.issuer_path = directory / "ISSUER-RESULT.json"
        self.request_path = directory / "request.json"
        self.refresh()

    def refresh(self):
        inventory = []
        framing = bytearray(b"provingkit-tree-v1\0")
        for name in sorted(self.files, key=PurePosixPath):
            raw = self.files[name]
            path_bytes = name.encode()
            inventory.append({"path": name, "sha256": digest(raw)})
            framing.extend(len(path_bytes).to_bytes(8, "big") + path_bytes)
            framing.extend(len(raw).to_bytes(8, "big") + raw)
        self.receipt = {
            "schema": "provingkit-artifact-receipt-v1",
            "builder": {"name": "provingkit-artifact-projector-v1", "revision": PROJECTOR},
            "source": {"repository": "https://github.com/nisavid/provingkit", "commit": SOURCE,
                       "channel": "main", "preview_label": "preview-" + SOURCE[:12]},
            "target": self.target, "plugin_slate": SLATE,
            "policy_sha256": "4" * 64, "artifact_sha256": digest(framing), "files": inventory,
            "delivery": {"version": self.version, "request_id": "synthetic-zip-9", "preparation_sha256": "3" * 64},
        }
        self.receipt_path.write_bytes(encoded(self.receipt))
        self.modes_path.write_text("path\tmode\torigin\n" + "".join(
            f"{name}\t{mode:04o}\tsynthetic\n" for name, mode in sorted(self.modes.items())))
        self.write_tar()
        self.request = {
            "schema": "provingkit-member-zip-request-v1", "target": self.target, "member": "mergecraft",
            "identity": {"source_commit": SOURCE, "projector_revision": PROJECTOR, "version": self.version,
                         "request_id": "synthetic-zip-9", "preparation_sha256": "3" * 64,
                         "issuer_request_id": "synthetic-zip-9",
                         "policy_sha256": "4" * 64, "plugin_slate": SLATE},
            "parent": {label: {"path": str(path), "sha256": digest(path.read_bytes())}
                       for label, path in (("archive", self.archive_path), ("receipt", self.receipt_path),
                                           ("modes", self.modes_path))},
        }
        self.write_issuer_result()
        self.save_request()

    def write_issuer_result(self):
        self.issuer_result = {
            "operation": "issue", "request_id": "synthetic-zip-9", "version": self.version,
            "source_commit": SOURCE,
            "publication": {"commit": "5" * 40, "outgoing_shas": ["5" * 40],
                            "plan_sha256": "sha256:" + "6" * 64,
                            "destination": {"ref": "refs/heads/ivan/provingkit-ad-hoc-artifacts",
                                            "endpoint_fingerprint": "sha256:" + "7" * 64}},
            "variants": {self.target: {filename: {"bytes": path.stat().st_size,
                                                  "sha256": digest(path.read_bytes())}
                                        for filename, path in (("artifact.tar.gz", self.archive_path),
                                                               ("RECEIPT.json", self.receipt_path),
                                                               ("modes.tsv", self.modes_path))}},
            "exposure": "pending",
        }
        self.save_issuer_result()

    def save_issuer_result(self):
        self.issuer_path.write_bytes(encoded(self.issuer_result))
        self.request["issuer_result"] = {"path": str(self.issuer_path),
                                         "sha256": digest(self.issuer_path.read_bytes())}

    def save_request(self):
        self.request_path.write_bytes(encoded(self.request))

    def write_tar(self, extra=()):
        with tarfile.open(self.archive_path, "w:gz", format=tarfile.GNU_FORMAT) as archive:
            root = tarfile.TarInfo(self.root_name)
            root.type = tarfile.DIRTYPE
            root.mode = 0o755
            archive.addfile(root)
            for name, mode in sorted(self.directories.items()):
                entry = tarfile.TarInfo(self.root_name + "/" + name)
                entry.type = tarfile.DIRTYPE
                entry.mode = mode
                archive.addfile(entry)
            for name, data in sorted({**self.files, "RECEIPT.json": self.receipt_path.read_bytes()}.items()):
                entry = tarfile.TarInfo(self.root_name + "/" + name)
                entry.mode = self.modes.get(name, 0o644)
                entry.size = len(data)
                archive.addfile(entry, io.BytesIO(data))
            for entry, data in extra:
                archive.addfile(entry, io.BytesIO(data) if data is not None else None)

    def repin(self, *labels):
        for label in labels:
            path = Path(self.request["parent"][label]["path"])
            self.request["parent"][label]["sha256"] = digest(path.read_bytes())
        self.write_issuer_result()
        self.save_request()

    def tar_entries(self):
        with tarfile.open(self.archive_path, "r:gz") as archive:
            return [(entry, archive.extractfile(entry).read() if entry.isfile() else None)
                    for entry in archive]

    def replace_tar(self, entries):
        with tarfile.open(self.archive_path, "w:gz", format=tarfile.GNU_FORMAT) as archive:
            for entry, data in entries:
                archive.addfile(entry, io.BytesIO(data) if data is not None else None)
        self.repin("archive")


class MemberZipContract(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="synthetic-")
        self.base = Path(self.scratch.name).resolve()

    def tearDown(self):
        self.scratch.cleanup()

    def invoke(self, parent, output, operation="derive", record_digest=None):
        command = [sys.executable, str(CLI), operation, "--request", str(parent.request_path),
                   "--output", str(output)]
        if record_digest is not None:
            command += ["--record-sha256", record_digest]
        return subprocess.run(command, capture_output=True, text=True,
                              env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=10)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "verified")

    def assert_rejected(self, result, reason=None):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        message = json.loads(result.stdout)
        self.assertEqual(message["status"], "rejected")
        if reason is not None:
            self.assertIn(reason, message["reason"])

    def test_canonical_download_names_sidecars_and_records_round_trip(self):
        names = {
            "agent-plugins": "provingkit-mergecraft-0.1.0-alpha.7.snapshot.9.zip",
            "claude": "provingkit-mergecraft-0.1.0-alpha.7.snapshot.9-claude.zip",
        }
        for target, name in names.items():
            with self.subTest(target=target):
                parent = SyntheticParent(self.base / target, target)
                output = self.base / (target + "-derived")
                result = self.invoke(parent, output)
                self.assert_success(result)
                self.assertEqual({p.name for p in output.iterdir()},
                                 {name, name + ".sha256", "DERIVATIVE.json"})
                archive = (output / name).read_bytes()
                sidecar = (output / (name + ".sha256")).read_bytes()
                self.assertEqual(sidecar, (digest(archive) + "  " + name + "\n").encode())
                record_bytes = (output / "DERIVATIVE.json").read_bytes()
                record = json.loads(record_bytes)
                self.assertEqual(record["zip"],
                                 {"name": name, "bytes": len(archive), "sha256": digest(archive)})
                self.assertEqual(record["sidecar"],
                                 {"name": name + ".sha256", "bytes": len(sidecar),
                                  "sha256": digest(sidecar)})
                pin = json.loads(result.stdout)["record_sha256"]
                self.assertEqual(pin, digest(record_bytes))
                self.assert_success(self.invoke(parent, output, "verify", pin))

    def test_agent_derivation_preserves_complete_root_relative_member(self):
        parent = SyntheticParent(self.base / "parent")
        output = self.base / "derived"
        self.assert_success(self.invoke(parent, output))
        expected = ["README.md", "a/", "a.b", "a/z", "plugin.json", "skills/", "skills/do/",
                    "skills/do/SKILL.md", "skills/do/run.py"]
        with zipfile.ZipFile(next(output.glob("*.zip"))) as archive:
            self.assertEqual(archive.namelist(), expected)
            self.assertEqual(archive.read("README.md"), b"# Mergecraft synthetic\n")
            self.assertEqual(archive.read("skills/do/run.py"), b"print('synthetic')\n")
            self.assertEqual(archive.getinfo("skills/do/run.py").external_attr >> 16,
                             stat.S_IFREG | 0o755)
            self.assertEqual(archive.getinfo("skills/do/").external_attr >> 16,
                             stat.S_IFDIR | 0o750)
        record = json.loads((output / "DERIVATIVE.json").read_bytes())
        self.assertEqual(record["member_root"]["mode"], "0750")

    def test_both_targets_freeze_identical_outputs_and_verify_against_original_parent(self):
        for target in ("agent-plugins", "claude"):
            with self.subTest(target=target):
                parent = SyntheticParent(self.base / target, target)
                before = {path.name: path.read_bytes() for path in
                          (parent.archive_path, parent.receipt_path, parent.modes_path, parent.issuer_path)}
                first, second = self.base / (target + "-first"), self.base / (target + "-second")
                first_result = self.invoke(parent, first)
                self.assert_success(first_result)
                self.assert_success(self.invoke(parent, second))
                self.assertEqual({p.name: p.read_bytes() for p in first.iterdir()},
                                 {p.name: p.read_bytes() for p in second.iterdir()})
                pin = json.loads(first_result.stdout)["record_sha256"]
                self.assert_success(self.invoke(parent, first, "verify", pin))
                self.assertEqual(before, {path.name: path.read_bytes() for path in
                                         (parent.archive_path, parent.receipt_path, parent.modes_path, parent.issuer_path)})
                record = json.loads((first / "DERIVATIVE.json").read_bytes())
                self.assertEqual(record["identity"]["source_commit"], SOURCE)
                self.assertEqual(record["identity"]["projector_revision"], PROJECTOR)
                self.assertEqual(record["identity"]["request_id"], "synthetic-zip-9")
                self.assertEqual(record["identity"]["preparation_sha256"], "3" * 64)
                self.assertEqual(record["recipe"]["sha256"], digest(CLI.read_bytes()))
                self.assertEqual(record["recipe"]["runtime"],
                                 {"python": sys.version.split()[0], "zlib": zlib.ZLIB_RUNTIME_VERSION})
                with zipfile.ZipFile(first / record["zip"]["name"]) as archive:
                    self.assertEqual(archive.testzip(), None)
                    self.assertEqual(archive.comment, b"")
                    for entry in archive.infolist():
                        self.assertEqual(entry.date_time, EPOCH)
                        self.assertEqual(entry.create_system, 3)
                        self.assertEqual(entry.compress_type,
                                         zipfile.ZIP_STORED if entry.is_dir() else zipfile.ZIP_DEFLATED)
                    self.assertEqual(json.loads(archive.read("plugin.json")),
                                     {"name": "mergecraft", "version": VERSION})
                    if target == "claude":
                        self.assertEqual(json.loads(archive.read(".claude-plugin/plugin.json")),
                                         {"name": "mergecraft", "version": VERSION})
                    else:
                        self.assertNotIn(".claude-plugin/plugin.json", archive.namelist())
                zip_path = first / record["zip"]["name"]
                self.assertEqual((first / record["sidecar"]["name"]).read_bytes(),
                                 f"{digest(zip_path.read_bytes())}  {zip_path.name}\n".encode())

    def test_parent_evidence_must_match_all_three_separately_held_digest_pins(self):
        for index, label in enumerate(("archive", "receipt", "modes")):
            with self.subTest(label=label):
                parent = SyntheticParent(self.base / str(index))
                path = Path(parent.request["parent"][label]["path"])
                path.write_bytes(path.read_bytes() + b"\n")
                output = self.base / (str(index) + "-out")
                self.assert_rejected(self.invoke(parent, output), "parent digest differs")
                self.assertFalse(output.exists())

    def test_entire_parent_path_and_kind_safety_is_checked_before_member_selection(self):
        bad_names = ["../escape", "/absolute", "plugins//extra", "plugins/./extra",
                     "plugins/../extra", "plugins\\extra", "C:drive", "other-root/file"]
        cases = [("name-" + str(index), name, tarfile.REGTYPE) for index, name in enumerate(bad_names)]
        cases += [("type-" + str(index), "plugins/unselected-extra", kind) for index, kind in enumerate(
            (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE))]
        for label, name, kind in cases:
            with self.subTest(case=label):
                parent = SyntheticParent(self.base / label)
                entry = tarfile.TarInfo(name if name.startswith(("/", "other-root")) else
                                        parent.root_name + "/" + name)
                entry.type = kind
                entry.linkname = "elsewhere" if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE) else ""
                entry.size = 1 if kind == tarfile.REGTYPE else 0
                parent.replace_tar(parent.tar_entries() + [(entry, b"x" if entry.size else None)])
                output = self.base / (label + "-out")
                self.assert_rejected(self.invoke(parent, output), "parent archive")
                self.assertFalse(output.exists())

    def test_parent_rejects_duplicate_missing_and_wrong_kind_directory_evidence(self):
        for case in ("duplicate", "missing-directory", "file-as-directory", "wrong-root"):
            with self.subTest(case=case):
                parent = SyntheticParent(self.base / case)
                entries = parent.tar_entries()
                if case == "duplicate":
                    entries.append(entries[-1])
                elif case == "missing-directory":
                    entries = [(entry, data) for entry, data in entries
                               if entry.name != parent.root_name + "/plugins/mergecraft/skills/do"]
                elif case == "file-as-directory":
                    for entry, _ in entries:
                        if entry.name == parent.root_name + "/plugins/mergecraft/skills/do":
                            entry.type = tarfile.REGTYPE
                else:
                    for entry, _ in entries:
                        entry.name = entry.name.replace(parent.root_name, "wrong-root", 1)
                parent.replace_tar(entries)
                output = self.base / (case + "-out")
                self.assert_rejected(self.invoke(parent, output), "parent archive")
                self.assertFalse(output.exists())

    def test_parent_receipt_and_modes_bind_all_files_including_unselected_siblings(self):
        cases = ("receipt-bytes", "receipt-missing", "receipt-duplicate", "receipt-extra",
                 "receipt-unsafe", "receipt-hash", "tree-hash", "extra-file", "missing-file",
                 "selected-bytes", "sibling-bytes", "file-mode", "mode-missing", "mode-duplicate",
                 "mode-extra", "mode-unsafe", "mode-invalid")
        for case in cases:
            with self.subTest(case=case):
                parent = SyntheticParent(self.base / case)
                entries = parent.tar_entries()
                if case == "receipt-bytes":
                    parent.receipt_path.write_bytes(parent.receipt_path.read_bytes() + b"\n")
                    parent.repin("receipt")
                elif case.startswith("receipt-") or case == "tree-hash":
                    if case == "receipt-missing":
                        parent.receipt["files"].pop()
                    elif case == "receipt-duplicate":
                        parent.receipt["files"].append(parent.receipt["files"][0])
                    elif case == "receipt-extra":
                        parent.receipt["files"].append({"path": "extra", "sha256": "0" * 64})
                    elif case == "receipt-unsafe":
                        parent.receipt["files"][0]["path"] = "../escape"
                    elif case == "receipt-hash":
                        parent.receipt["files"][0]["sha256"] = "0" * 64
                    else:
                        parent.receipt["artifact_sha256"] = "0" * 64
                    parent.receipt_path.write_bytes(encoded(parent.receipt))
                    parent.write_tar()
                    parent.repin("archive", "receipt")
                elif case.startswith("mode-"):
                    rows = parent.modes_path.read_text().splitlines()
                    if case == "mode-missing":
                        rows.pop()
                    elif case == "mode-duplicate":
                        rows.append(rows[-1])
                    elif case == "mode-extra":
                        rows.append("extra\t0644\tsynthetic")
                    elif case == "mode-unsafe":
                        rows.append("../escape\t0644\tsynthetic")
                    else:
                        rows[-1] = rows[-1].replace("0644", "not-octal")
                    parent.modes_path.write_text("\n".join(rows) + "\n")
                    parent.repin("modes")
                else:
                    selected = parent.root_name + "/plugins/mergecraft/README.md"
                    sibling = parent.root_name + "/plugins/rolecasting/plugin.json"
                    if case == "missing-file":
                        entries = [(entry, data) for entry, data in entries if entry.name != selected]
                    elif case == "extra-file":
                        entry = tarfile.TarInfo(parent.root_name + "/plugins/mergecraft/extra")
                        entries.append((entry, b""))
                    else:
                        updated = []
                        for entry, data in entries:
                            if entry.name == (sibling if case == "sibling-bytes" else selected):
                                if case == "file-mode":
                                    entry.mode = 0o600
                                else:
                                    data = b"changed bytes\n"
                                    entry.size = len(data)
                            updated.append((entry, data))
                        entries = updated
                    parent.replace_tar(entries)
                output = self.base / (case + "-out")
                self.assert_rejected(self.invoke(parent, output), "parent")
                self.assertFalse(output.exists())

    def test_stamped_parent_identity_cannot_drift_from_the_selected_snapshot(self):
        cases = ("schema", "source", "repository", "projector-name", "projector-revision", "target",
                 "policy", "version", "request", "preparation", "slate-missing", "slate-duplicate",
                 "manifest-name", "manifest-version", "sibling-version", "adapter-name", "adapter-version",
                 "adapter-missing", "catalog-source", "catalog-version", "catalog-missing", "catalog-duplicate")
        for case in cases:
            with self.subTest(case=case):
                parent = SyntheticParent(self.base / case, "claude")
                if case.startswith("manifest-") or case in ("sibling-version", "adapter-name", "adapter-version"):
                    path = ("plugins/rolecasting/plugin.json" if case == "sibling-version" else
                            "plugins/mergecraft/.claude-plugin/plugin.json" if case.startswith("adapter-") else
                            "plugins/mergecraft/plugin.json")
                    manifest = json.loads(parent.files[path])
                    manifest["name" if case.endswith("name") else "version"] = "wrong"
                    parent.files[path] = encoded(manifest)
                    parent.refresh()
                elif case == "adapter-missing":
                    del parent.files["plugins/mergecraft/.claude-plugin/plugin.json"]
                    del parent.modes["plugins/mergecraft/.claude-plugin/plugin.json"]
                    parent.refresh()
                elif case.startswith("catalog-"):
                    catalog = json.loads(parent.files[parent.catalog_path])
                    if case == "catalog-source":
                        catalog["plugins"][0]["source"] = "./wrong"
                    elif case == "catalog-version":
                        catalog["plugins"][0]["version"] = "wrong"
                    elif case == "catalog-missing":
                        catalog["plugins"].pop()
                    else:
                        catalog["plugins"].append(catalog["plugins"][0])
                    parent.files[parent.catalog_path] = encoded(catalog)
                    parent.refresh()
                else:
                    if case == "schema":
                        parent.receipt["schema"] = "wrong"
                    elif case == "source":
                        parent.receipt["source"]["commit"] = "5" * 40
                    elif case == "repository":
                        parent.receipt["source"]["repository"] = "https://example.invalid/other"
                    elif case == "projector-name":
                        parent.receipt["builder"]["name"] = "wrong"
                    elif case == "projector-revision":
                        parent.receipt["builder"]["revision"] = "5" * 40
                    elif case == "target":
                        parent.receipt["target"] = "agent-plugins"
                    elif case == "policy":
                        parent.receipt["policy_sha256"] = "5" * 64
                    elif case == "version":
                        parent.receipt["delivery"]["version"] = "0.1.0-alpha.7"
                    elif case == "request":
                        parent.receipt["delivery"]["request_id"] = "different-request"
                    elif case == "preparation":
                        parent.receipt["delivery"]["preparation_sha256"] = "5" * 64
                    elif case == "slate-missing":
                        parent.receipt["plugin_slate"] = SLATE[:-1]
                    else:
                        parent.receipt["plugin_slate"] = SLATE + [SLATE[0]]
                    parent.receipt_path.write_bytes(encoded(parent.receipt))
                    parent.write_tar()
                    parent.repin("archive", "receipt")
                output = self.base / (case + "-out")
                self.assert_rejected(self.invoke(parent, output), "identity")
                self.assertFalse(output.exists())

    def test_agent_plugins_rejects_a_claude_adapter_even_when_its_receipt_is_consistent(self):
        parent = SyntheticParent(self.base / "parent")
        path = "plugins/mergecraft/.claude-plugin/plugin.json"
        parent.files[path] = encoded({"name": "mergecraft", "version": VERSION})
        parent.modes[path] = 0o644
        parent.directories["plugins/mergecraft/.claude-plugin"] = 0o755
        parent.refresh()
        self.assert_rejected(self.invoke(parent, self.base / "output"), "identity")

    def test_request_decoder_rejects_ambiguous_and_unsupported_inputs_before_output(self):
        cases = ("schema", "extra", "not-object", "target", "member", "identity-type", "source",
                 "projector", "version", "preparation", "policy", "slate-missing", "slate-duplicate",
                 "parent-extra", "bad-pin", "duplicate-json", "nan")
        for case in cases:
            with self.subTest(case=case):
                parent = SyntheticParent(self.base / case)
                request = parent.request
                if case == "schema":
                    request["schema"] = "wrong"
                elif case == "extra":
                    request["extra"] = "unused"
                elif case == "not-object":
                    request = []
                elif case == "target":
                    request["target"] = "cursor"
                elif case == "member":
                    request["member"] = "../mergecraft"
                elif case == "identity-type":
                    request["identity"] = []
                elif case == "source":
                    request["identity"]["source_commit"] = "short"
                elif case == "projector":
                    request["identity"]["projector_revision"] = "short"
                elif case == "version":
                    request["identity"]["version"] = "../../escape"
                elif case == "preparation":
                    request["identity"]["preparation_sha256"] = "short"
                elif case == "policy":
                    request["identity"]["policy_sha256"] = "short"
                elif case == "slate-missing":
                    request["identity"]["plugin_slate"] = SLATE[:-1]
                elif case == "slate-duplicate":
                    request["identity"]["plugin_slate"] = SLATE + [SLATE[0]]
                elif case == "parent-extra":
                    request["parent"]["extra"] = request["parent"]["receipt"]
                elif case == "bad-pin":
                    request["parent"]["archive"]["sha256"] = "short"
                parent.request_path.write_bytes(encoded(request))
                if case == "duplicate-json":
                    parent.request_path.write_bytes(b'{"member":"ignored",' + encoded(request)[1:])
                elif case == "nan":
                    parent.request_path.write_bytes(b'{"invalid":NaN,' + encoded(request)[1:])
                output = self.base / (case + "-out")
                self.assert_rejected(self.invoke(parent, output), "request")
                self.assertFalse(output.exists())

    def test_receipt_and_manifest_json_duplicate_keys_are_rejected(self):
        for case in ("receipt", "manifest"):
            with self.subTest(case=case):
                parent = SyntheticParent(self.base / case)
                if case == "receipt":
                    parent.receipt_path.write_bytes(b'{"schema":"ambiguous",' + encoded(parent.receipt)[1:])
                    parent.write_tar()
                    parent.repin("archive", "receipt")
                else:
                    path = "plugins/mergecraft/plugin.json"
                    parent.files[path] = b'{"name":"ambiguous",' + parent.files[path][1:]
                    parent.refresh()
                self.assert_rejected(self.invoke(parent, self.base / (case + "-out")), "duplicate")

    def test_cli_rejects_symlinked_input_and_output_paths_and_preserves_existing_outputs(self):
        for case in ("archive", "receipt", "modes", "request", "ancestor", "output-ancestor", "existing-output"):
            with self.subTest(case=case):
                parent = SyntheticParent(self.base / case)
                output = self.base / (case + "-out")
                if case in ("archive", "receipt", "modes"):
                    original = Path(parent.request["parent"][case]["path"])
                    link = parent.directory / (case + "-link")
                    link.symlink_to(original)
                    parent.request["parent"][case]["path"] = str(link)
                    parent.save_request()
                elif case == "request":
                    original = parent.request_path
                    parent.request_path = parent.directory / "request-link"
                    parent.request_path.symlink_to(original)
                elif case == "ancestor":
                    link = self.base / "input-link"
                    link.symlink_to(parent.directory, target_is_directory=True)
                    parent.request["parent"]["receipt"]["path"] = str(link / "RECEIPT.json")
                    parent.save_request()
                elif case == "output-ancestor":
                    real = self.base / "real-output-parent"
                    real.mkdir(mode=0o700)
                    link = self.base / "output-link"
                    link.symlink_to(real, target_is_directory=True)
                    output = link / "fresh"
                else:
                    output.mkdir()
                    (output / "keep.txt").write_bytes(b"keep me\n")
                self.assert_rejected(self.invoke(parent, output))
                if case == "existing-output":
                    self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()},
                                     {"keep.txt": b"keep me\n"})
                else:
                    self.assertFalse(output.exists())

    def test_verify_rejects_symlinked_derivative_files_even_if_the_bytes_match(self):
        parent = SyntheticParent(self.base / "parent")
        output = self.base / "output"
        result = self.invoke(parent, output)
        self.assert_success(result)
        pin = json.loads(result.stdout)["record_sha256"]
        original = output / "DERIVATIVE.json"
        retained = self.base / "retained-record.json"
        original.rename(retained)
        original.symlink_to(retained)
        self.assert_rejected(self.invoke(parent, output, "verify", pin))

    def test_verify_rejects_changed_zip_encoding_contents_sidecar_record_and_parent(self):
        cases = ("missing", "extra", "duplicate", "unsafe", "kind", "mode", "bytes", "identity",
                 "compression", "timestamp", "comment", "crc", "deflate", "trailing",
                 "sidecar", "record", "record-new-pin", "output-extra", "parent-changed",
                 "pin-missing", "pin-wrong")
        for case in cases:
            with self.subTest(case=case):
                parent = SyntheticParent(self.base / case)
                output = self.base / (case + "-out")
                result = self.invoke(parent, output)
                self.assert_success(result)
                pin = json.loads(result.stdout)["record_sha256"]
                archive_path = next(output.glob("*.zip"))
                if case in ("sidecar", "record", "record-new-pin", "output-extra", "parent-changed",
                            "pin-missing", "pin-wrong"):
                    if case == "sidecar":
                        next(output.glob("*.sha256")).write_bytes(b"wrong\n")
                    elif case.startswith("record"):
                        path = output / "DERIVATIVE.json"
                        record = json.loads(path.read_bytes())
                        record["member_root"]["mode"] = "0777"
                        path.write_bytes(encoded(record))
                        if case == "record-new-pin":
                            pin = digest(path.read_bytes())
                    elif case == "output-extra":
                        (output / "unexpected").write_bytes(b"extra")
                    elif case == "parent-changed":
                        parent.files["plugins/mergecraft/README.md"] = b"replacement parent\n"
                        parent.refresh()
                    elif case == "pin-missing":
                        pin = None
                    else:
                        pin = "0" * 64
                elif case in ("crc", "deflate", "trailing"):
                    raw = bytearray(archive_path.read_bytes())
                    if case == "crc":
                        offset = raw.index(b"PK\x01\x02") + 16
                        raw[offset] ^= 1
                    elif case == "deflate":
                        with zipfile.ZipFile(archive_path) as archive:
                            offset = archive.getinfo("README.md").header_offset
                        filename_size, extra_size = struct.unpack_from("<HH", raw, offset + 26)
                        raw[offset + 30 + filename_size + extra_size] = 7
                    else:
                        raw.extend(b"trailing bytes")
                    archive_path.write_bytes(raw)
                else:
                    with zipfile.ZipFile(archive_path) as archive:
                        entries = [(copy.copy(entry), archive.read(entry)) for entry in archive.infolist()]
                    if case == "missing":
                        entries = [(entry, data) for entry, data in entries if entry.filename != "README.md"]
                    elif case in ("extra", "unsafe"):
                        entries.append((zipfile.ZipInfo("extra" if case == "extra" else "../escape", EPOCH), b"x"))
                    elif case == "duplicate":
                        entries.append(entries[0])
                    else:
                        for entry, data in entries:
                            if entry.filename == ("plugin.json" if case == "identity" else "README.md"):
                                if case == "kind":
                                    entry.external_attr = (stat.S_IFLNK | 0o644) << 16
                                elif case == "mode":
                                    entry.external_attr = (stat.S_IFREG | 0o600) << 16
                                elif case == "compression":
                                    entry.compress_type = zipfile.ZIP_STORED
                                elif case == "timestamp":
                                    entry.date_time = (2000, 1, 1, 0, 0, 0)
                                elif case == "bytes":
                                    entries[entries.index((entry, data))] = (entry, b"changed\n")
                                elif case == "identity":
                                    entries[entries.index((entry, data))] = (entry, b'{"name":"wrong","version":"wrong"}')
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", UserWarning)
                        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED,
                                             compresslevel=9) as archive:
                            for entry, data in entries:
                                archive.writestr(entry, data, compress_type=entry.compress_type, compresslevel=9)
                            if case == "comment":
                                archive.comment = b"unexpected comment"
                self.assert_rejected(self.invoke(parent, output, "verify", pin))

    def test_supported_snapshot_anchors_and_preserved_nondefault_inputs_remain_eligible(self):
        for index, version in enumerate(("0.2.0-0.snapshot.1", "0.1.0-beta.1.snapshot.27",
                                         "0.1.0-rc.2.snapshot.100")):
            with self.subTest(version=version):
                parent = SyntheticParent(self.base / str(index), "claude", version)
                parent.files["plugins/mergecraft/skills/do/référence.md"] = "Référence\n".encode()
                parent.modes["plugins/mergecraft/skills/do/référence.md"] = 0o640
                parent.modes["plugins/mergecraft/plugin.json"] = 0o600
                parent.directories["plugins/mergecraft/empty"] = 0o710
                parent.refresh()
                hardlink = parent.directory / "hardlinked-receipt.json"
                os.link(parent.receipt_path, hardlink)
                parent.request["parent"]["receipt"]["path"] = str(hardlink)
                parent.save_request()
                output = self.base / (str(index) + "-out")
                self.assert_success(self.invoke(parent, output))
                with zipfile.ZipFile(next(output.glob("*.zip"))) as archive:
                    self.assertEqual(archive.read("skills/do/référence.md"), "Référence\n".encode())
                    self.assertEqual(archive.getinfo("skills/do/référence.md").external_attr >> 16,
                                     stat.S_IFREG | 0o640)
                    self.assertEqual(archive.getinfo("plugin.json").external_attr >> 16,
                                     stat.S_IFREG | 0o600)
                    self.assertEqual(archive.getinfo("empty/").external_attr >> 16, stat.S_IFDIR | 0o710)

    def test_complete_slate_order_comes_from_the_bound_projection(self):
        parent = SyntheticParent(self.base / "parent")
        catalog = json.loads(parent.files[parent.catalog_path])
        catalog["plugins"].reverse()
        parent.files[parent.catalog_path] = encoded(catalog)
        parent.refresh()
        parent.receipt["plugin_slate"] = list(reversed(SLATE))
        parent.receipt_path.write_bytes(encoded(parent.receipt))
        parent.write_tar()
        parent.request["identity"]["plugin_slate"] = list(reversed(SLATE))
        parent.repin("archive", "receipt")
        self.assert_success(self.invoke(parent, self.base / "output"))

    def test_special_files_are_rejected_without_blocking_on_a_fifo(self):
        parent = SyntheticParent(self.base / "parent")
        fifo = parent.directory / "fifo"
        os.mkfifo(fifo)
        parent.request["parent"]["modes"]["path"] = str(fifo)
        parent.save_request()
        self.assert_rejected(self.invoke(parent, self.base / "output"), "regular file")

    def test_derivative_binds_original_addition_request_separately_from_preparation_and_exposure(self):
        parent = SyntheticParent(self.base / "parent")
        parent.issuer_result.update(operation="add-variants", request_id="synthetic-target-addition", retry_of=[])
        parent.request["identity"]["issuer_request_id"] = "synthetic-target-addition"
        parent.save_issuer_result()
        parent.save_request()
        output = self.base / "output"
        result = self.invoke(parent, output)
        self.assert_success(result)
        record = json.loads((output / "DERIVATIVE.json").read_bytes())
        self.assertEqual(record["identity"]["request_id"], "synthetic-zip-9")
        self.assertEqual(record["issuer_result"]["request_id"], "synthetic-target-addition")
        self.assertEqual(record["issuer_result"]["operation"], "add-variants")
        self.assertEqual(record["issuer_result"]["exposure"], "pending")
        self.assertEqual(record["issuer_result"]["sha256"], digest(parent.issuer_path.read_bytes()))
        self.assertEqual(json.loads(result.stdout)["scope"], "local-derivative-integrity")
        self.assertEqual(json.loads(result.stdout)["issuer_exposure"], "pending")

    def test_original_issuer_result_identity_and_variant_pins_cannot_be_substituted(self):
        cases = ("operation", "request", "version", "source", "exposure", "target", "archive",
                 "receipt", "modes", "extra-file", "issuer-pin", "duplicate-json")
        for case in cases:
            with self.subTest(case=case):
                parent = SyntheticParent(self.base / case)
                issuer = parent.issuer_result
                if case == "operation":
                    issuer["operation"] = "prepare"
                elif case == "request":
                    issuer["request_id"] = "another-request"
                elif case == "version":
                    issuer["version"] = "0.1.0-alpha.7.snapshot.10"
                elif case == "source":
                    issuer["source_commit"] = "8" * 40
                elif case == "exposure":
                    issuer["exposure"] = "invented"
                elif case == "target":
                    issuer["variants"] = {}
                elif case in ("archive", "receipt", "modes"):
                    filename = {"archive": "artifact.tar.gz", "receipt": "RECEIPT.json", "modes": "modes.tsv"}[case]
                    issuer["variants"][parent.target][filename]["sha256"] = "0" * 64
                elif case == "extra-file":
                    issuer["variants"][parent.target]["extra"] = {"sha256": "0" * 64, "bytes": 1}
                parent.save_issuer_result()
                parent.save_request()
                if case in ("issuer-pin", "duplicate-json"):
                    raw = parent.issuer_path.read_bytes()
                    parent.issuer_path.write_bytes(raw + b"\n" if case == "issuer-pin" else
                                                  b'{"request_id":"ambiguous",' + raw[1:])
                    if case == "duplicate-json":
                        parent.request["issuer_result"]["sha256"] = digest(parent.issuer_path.read_bytes())
                        parent.save_request()
                output = self.base / (case + "-out")
                self.assert_rejected(self.invoke(parent, output), "issuer result")
                self.assertFalse(output.exists())

    def test_issuer_operation_requires_the_corresponding_preparation_request_pairing(self):
        for operation, request_id in (("issue", "synthetic-different-issue"),
                                      ("add-variants", "synthetic-zip-9")):
            with self.subTest(operation=operation):
                parent = SyntheticParent(self.base / operation)
                parent.issuer_result.update(operation=operation, request_id=request_id)
                if operation == "add-variants":
                    parent.issuer_result["retry_of"] = []
                parent.request["identity"]["issuer_request_id"] = request_id
                parent.save_issuer_result()
                parent.save_request()
                output = self.base / (operation + "-out")
                self.assert_rejected(self.invoke(parent, output), "issuer result request pairing")
                self.assertFalse(output.exists())

    def test_output_requires_an_owned_parent_without_group_or_other_permissions(self):
        parent = SyntheticParent(self.base / "parent")
        for mode in (0o777, 0o770, 0o1777, 0o755):
            with self.subTest(mode=f"{mode:04o}"):
                directory = self.base / f"shared-{mode:o}"
                directory.mkdir()
                directory.chmod(mode)
                output = directory / "derived"
                self.assert_rejected(self.invoke(parent, output), "output parent")
                self.assertFalse(output.exists())
        writable_ancestor = self.base / "writable-ancestor"
        writable_ancestor.mkdir()
        writable_ancestor.chmod(0o777)
        private_parent = writable_ancestor / "private-parent"
        private_parent.mkdir(mode=0o700)
        output = private_parent / "derived"
        self.assert_rejected(self.invoke(parent, output), "output ancestor")
        self.assertFalse(output.exists())

    def test_prequalified_private_parent_supports_derivation_and_readback_below_a_sticky_ancestor(self):
        parent = SyntheticParent(self.base / "parent")
        sticky = self.base / "sticky"
        sticky.mkdir()
        sticky.chmod(0o1777)
        private_parent = sticky / "owned-private"
        private_parent.mkdir(mode=0o700)
        output = private_parent / "derived"
        result = self.invoke(parent, output)
        self.assert_success(result)
        pin = json.loads(result.stdout)["record_sha256"]
        self.assert_success(self.invoke(parent, output, "verify", pin))
        before = {p.name: p.read_bytes() for p in output.iterdir()}
        private_parent.chmod(0o777)
        try:
            self.assert_rejected(self.invoke(parent, output, "verify", pin), "output parent")
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})
        finally:
            private_parent.chmod(0o700)

    def test_writable_parent_substitution_is_blocked_before_the_contender_can_replace_the_leaf(self):
        if not hasattr(os, "fork"):
            self.skipTest("the bounded two-process scheduling fixture uses fork")
        parent = SyntheticParent(self.base / "parent")
        shared = self.base / "shared"
        shared.mkdir()
        shared.chmod(0o777)
        hooks = self.base / "hooks"
        hooks.mkdir()
        event = self.base / "contender.json"
        (hooks / "sitecustomize.py").write_text(textwrap.dedent('''
            import json
            import os
            original_mkdir = os.mkdir
            def mkdir_with_contender(path, mode=0o777, *, dir_fd=None):
                original_mkdir(path, mode, dir_fd=dir_fd)
                if os.fspath(path) != "derived" or dir_fd is None:
                    return
                child = os.fork()
                if child == 0:
                    try:
                        os.rename("derived", "displaced", src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
                        original_mkdir("derived", 0o700, dir_fd=dir_fd)
                        with open(os.environ["MEMBER_ZIP_CONTENDER_EVENT"], "x") as stream:
                            json.dump({"substituted_directory": True}, stream)
                    finally:
                        os._exit(0)
                _, status = os.waitpid(child, 0)
                if status:
                    raise RuntimeError("bounded contender failed")
            os.mkdir = mkdir_with_contender
            os.supports_dir_fd = (os.supports_dir_fd - {original_mkdir}) | {mkdir_with_contender}
        '''))
        output = shared / "derived"
        result = subprocess.run([sys.executable, str(CLI), "derive", "--request", str(parent.request_path),
                                 "--output", str(output)], capture_output=True, text=True, timeout=10,
                                env={**os.environ, "PYTHONPATH": str(hooks), "PYTHONDONTWRITEBYTECODE": "1",
                                     "MEMBER_ZIP_CONTENDER_EVENT": str(event)})
        self.assertNotEqual(result.returncode, 0,
                            f"{result.stdout}\nchild_directory_substitution={event.exists()}")
        self.assert_rejected(result, "output parent")
        self.assertFalse(event.exists(), "parent rejection must precede output creation")
        self.assertEqual(list(shared.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
