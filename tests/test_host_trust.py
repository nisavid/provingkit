from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import unittest.mock as mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import host_trust as trust
import validate_host_trust_projections as projections


class HostTrustTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT, prefix="host-trust-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.executable = self.root / "tool"
        self.executable.write_text("#!/bin/sh\nexit 0\n")
        self.executable.chmod(0o700)

    def test_fixed_host_selection_accepts_nonzero_system_owner(self):
        original = Path.lstat

        def foreign_owner(path):
            metadata = original(path)
            fields = list(metadata)
            fields[4] = 65534
            return os.stat_result(fields)

        with mock.patch.object(Path, "lstat", foreign_owner), mock.patch.dict(
            os.environ, {"PATH": str(self.root / "absent")}
        ):
            bound = trust.bind_host_executable(self.executable)
            self.assertEqual(bound.path, str(self.executable))
            trust.recheck_host_executable(bound)

    def test_only_absolute_filesystem_root_is_namespace_anchor(self):
        self.assertTrue(trust.is_host_namespace_anchor(Path("/")))
        for value in (".", "relative", "/tmp", str(self.root)):
            self.assertFalse(trust.is_host_namespace_anchor(Path(value)))

    def test_refuses_missing_relative_nonregular_and_unsafe_modes(self):
        for path in (Path("tool"), self.root / "missing", self.root):
            with self.subTest(path=path), self.assertRaises(trust.HostTrustError):
                trust.bind_host_executable(path)
        for mode in (0o600, 0o722, 0o770):
            self.executable.chmod(mode)
            with self.subTest(mode=mode), self.assertRaises(trust.HostTrustError):
                trust.bind_host_executable(self.executable)
        self.executable.chmod(0o700)
        self.root.chmod(0o777)
        with self.assertRaises(trust.HostTrustError):
            trust.bind_host_executable(self.executable)
        self.root.chmod(0o700)

    def test_candidate_exclusion_covers_lexical_and_resolved_roots(self):
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        for root in (self.root, alias):
            with self.subTest(root=root), self.assertRaisesRegex(
                trust.HostTrustError, "candidate-controlled"
            ):
                trust.bind_host_executable(self.executable, excluded_roots=(root,))
        with self.assertRaisesRegex(trust.HostTrustError, "candidate-controlled"):
            trust.bind_host_executable(
                alias / "tool", excluded_roots=(self.root,), allow_symlink=True
            )

    def test_symlinks_require_explicit_selection_and_target_rechecks(self):
        alias = self.root / "alias"
        alias.symlink_to(self.executable)
        with self.assertRaisesRegex(trust.HostTrustError, "redirected"):
            trust.bind_host_executable(alias)
        bound = trust.bind_host_executable(alias, allow_symlink=True)
        trust.recheck_host_executable(bound)
        self.executable.write_text("#!/bin/sh\nexit 1\n")
        with self.assertRaisesRegex(trust.HostTrustError, "changed"):
            trust.recheck_host_executable(bound)

    def test_replacement_and_ancestor_changes_invalidate_snapshot(self):
        bound = trust.bind_host_executable(self.executable)
        self.executable.unlink()
        self.executable.write_text("#!/bin/sh\nexit 0\n")
        self.executable.chmod(0o700)
        with self.assertRaisesRegex(trust.HostTrustError, "changed"):
            trust.recheck_host_executable(bound)
        bound = trust.bind_host_executable(self.executable)
        self.root.chmod(0o750)
        with self.assertRaisesRegex(trust.HostTrustError, "changed"):
            trust.recheck_host_executable(bound)

    def test_unrelated_ancestor_entries_preserve_execution_and_rebinding(self):
        runtime = self.root / "runtime"
        runtime.mkdir(mode=0o700)
        executable = runtime / "tool"
        executable.write_bytes(self.executable.read_bytes())
        executable.chmod(0o700)
        bound = trust.bind_host_executable(executable)
        sibling = self.root / "unrelated"
        renamed = self.root / "renamed"
        actions = (
            lambda: sibling.write_text("unrelated\n"),
            lambda: sibling.rename(renamed),
            renamed.unlink,
            sibling.mkdir,
            lambda: sibling.rename(renamed),
            renamed.rmdir,
        )
        for index, action in enumerate(actions):
            with self.subTest(activity=index):
                action()
                trust.recheck_host_executable(bound)
                self.assertEqual(trust.bind_host_executable(executable), bound)
                result = subprocess.run([bound.path], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_binding_keeps_all_lexical_and_resolved_ancestors(self):
        runtime = self.root / "runtime"
        runtime.mkdir(mode=0o700)
        executable = runtime / "tool"
        executable.write_bytes(self.executable.read_bytes())
        executable.chmod(0o700)
        alias = self.root / "alias"
        alias.symlink_to(executable)
        selected = alias
        bound = trust.bind_host_executable(selected, allow_symlink=True)
        paths = {path for path, _ in bound.identities}
        self.assertEqual(paths, {*selected.parents, selected, *executable.parents, executable})
        (runtime / "unrelated").mkdir()
        trust.recheck_host_executable(bound)
        self.assertEqual(trust.bind_host_executable(selected, allow_symlink=True), bound)

    def test_directory_replacement_is_rejected(self):
        # Replace a bound ancestor while retaining the same executable inode.
        runtime = self.root / "runtime"
        runtime.mkdir(mode=0o700)
        self.executable.rename(runtime / "tool")
        bound = trust.bind_host_executable(runtime / "tool")
        runtime.rename(self.root / "old-runtime")
        runtime.mkdir(mode=0o700)
        (self.root / "old-runtime" / "tool").rename(runtime / "tool")
        with self.assertRaisesRegex(trust.HostTrustError, "changed"):
            trust.recheck_host_executable(bound)

    def test_symlink_entry_change_and_retarget_are_rejected(self):
        alias = self.root / "alias"
        alias.symlink_to(self.executable)
        bound = trust.bind_host_executable(alias, allow_symlink=True)
        # A changed spelling keeps the same resolved target but changes the link.
        alias.unlink()
        alias.symlink_to(str(self.root) + "/./tool")
        with self.assertRaisesRegex(trust.HostTrustError, "changed"):
            trust.recheck_host_executable(bound)
        bound = trust.bind_host_executable(alias, allow_symlink=True)
        other = self.root / "other"
        other.write_bytes(self.executable.read_bytes())
        other.chmod(0o700)
        alias.unlink()
        alias.symlink_to(other)
        with self.assertRaisesRegex(trust.HostTrustError, "changed"):
            trust.recheck_host_executable(bound)

    def test_directory_identity_observes_exactly_object_owner_and_mode_fields(self):
        bound = trust.bind_host_executable(self.executable)
        original = Path.lstat
        metadata = original(self.root)
        retained = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid")
        omitted = ("st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
        for field in (*retained, *omitted):
            with self.subTest(field=field):
                values = {name: getattr(metadata, name) for name in (*retained, *omitted)}
                values[field] += 1

                def changed(path):
                    return SimpleNamespace(**values) if path == self.root else original(path)

                with mock.patch.object(Path, "lstat", changed):
                    if field in retained:
                        with self.assertRaisesRegex(trust.HostTrustError, "changed"):
                            trust.recheck_host_executable(bound)
                    else:
                        trust.recheck_host_executable(bound)
        values["st_mode"] = stat.S_IFREG | 0o700
        with mock.patch.object(Path, "lstat", changed):
            with self.assertRaisesRegex(trust.HostTrustError, "changed"):
                trust.recheck_host_executable(bound)

    def test_non_directory_identity_retains_every_existing_field(self):
        fields = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
                  "st_size", "st_mtime_ns", "st_ctime_ns")
        for kind in (stat.S_IFREG, stat.S_IFLNK, stat.S_IFIFO):
            values = dict(zip(fields, (11, 12, kind | 0o700, 13, 14, 15, 16, 17, 18)))
            expected = tuple(values[field] for field in fields)
            with self.subTest(kind=kind):
                self.assertEqual(trust._identity(SimpleNamespace(**values)), expected)
                for field in fields:
                    changed = {**values, field: values[field] + 1}
                    self.assertNotEqual(trust._identity(SimpleNamespace(**changed)), expected)

    def test_selected_file_content_and_mode_changes_are_rejected(self):
        for change in (lambda: self.executable.write_text("#!/bin/sh\nexit 1\n"),
                       lambda: self.executable.chmod(0o500)):
            bound = trust.bind_host_executable(self.executable)
            change()
            with self.assertRaisesRegex(trust.HostTrustError, "changed"):
                trust.recheck_host_executable(bound)


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT, prefix="projection-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        source = self.root / projections.SOURCE
        source.parent.mkdir(parents=True)
        source.write_bytes((ROOT / projections.SOURCE).read_bytes())
        for relative in projections.PROJECTIONS:
            (self.root / relative).parent.mkdir(parents=True, exist_ok=True)

    def test_writer_restores_exact_projections_and_checker_rejects_drift(self):
        projections.write(self.root)
        projections.validate(self.root)
        altered = self.root / projections.PROJECTIONS[0]
        altered.write_text("drift\n")
        with self.assertRaisesRegex(ValueError, "projection drift"):
            projections.validate(self.root)
        projections.write(self.root)
        projections.validate(self.root)

    def test_writer_refuses_destination_links_without_touching_target(self):
        target = self.root / "sentinel"
        target.write_text("preserve\n")
        (self.root / projections.PROJECTIONS[0]).symlink_to(target)
        with self.assertRaisesRegex(ValueError, "regular file"):
            projections.write(self.root)
        self.assertEqual(target.read_text(), "preserve\n")

    def test_installed_helpers_import_without_checkout_or_sibling_plugin(self):
        projections.write(self.root)
        # Isolated Python ignores PYTHONPATH; only this installed file is loaded.
        source = (
            "import importlib.util, pathlib, sys; "
            "p=pathlib.Path(sys.argv[1]); "
            "s=importlib.util.spec_from_file_location('installed_host_trust',p); "
            "m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; "
            "s.loader.exec_module(m); "
            "assert m.is_host_namespace_anchor(pathlib.Path('/')); "
            "assert m.bind_host_executable(pathlib.Path('/usr/bin/git')).path == '/usr/bin/git'"
        )
        for relative in projections.PROJECTIONS:
            with self.subTest(projection=relative):
                result = subprocess.run(
                    [sys.executable, "-I", "-B", "-c", source, str(self.root / relative)],
                    cwd=self.root, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
