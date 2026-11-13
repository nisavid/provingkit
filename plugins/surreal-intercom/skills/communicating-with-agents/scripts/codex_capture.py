"""Invocation-owned, create-only capture IO with a per-run new-write allowance.

Adapted from execution_storage.py SHA-256
a5d72361b11ebd1da046ca1b763205c9751dcf47bf06e736b3e8e2ded45b25dd.
Trusted capture inputs name an existing run_root, allowance_bytes,
terminal_provision_bytes (512 KiB), and later_forecast_bytes. Existing retained
files do not consume this invocation's allowance; writes never replace them.
"""
import hashlib
import json
import os
import tempfile
from pathlib import Path


TERMINAL = 524288


class StorageRefusal(OSError):
    pass


class CaptureWriter:
    def __init__(self, settings):
        if not isinstance(settings, dict) or settings.keys() != {
            "run_root", "allowance_bytes", "terminal_provision_bytes", "later_forecast_bytes",
        }:
            raise StorageRefusal("invalid-local-storage-settings")
        try:
            self.root = Path(settings["run_root"])
            valid = (
                self.root.is_absolute() and self.root.is_dir()
                and not any(p.is_symlink() for p in [self.root, *self.root.parents])
                and type(settings["allowance_bytes"]) is int and settings["allowance_bytes"] > TERMINAL
                and type(settings["terminal_provision_bytes"]) is int and settings["terminal_provision_bytes"] == TERMINAL
                and type(settings["later_forecast_bytes"]) is int and settings["later_forecast_bytes"] >= 0
            )
        except (TypeError, ValueError, OSError) as exc:
            raise StorageRefusal("invalid-local-storage-settings") from exc
        if not valid:
            raise StorageRefusal("invalid-local-storage-settings")
        self.settings = dict(settings)
        self.new_bytes = 0
        self.terminal_bytes = 0
        self.observations = []

    def require(self, path):
        path = Path(path)
        if (not path.resolve().is_relative_to(self.root.resolve())
                or any(p.is_symlink() for p in [path, *path.parents])):
            raise StorageRefusal("output-outside-owned-run")

    def write_json(self, path, value):
        data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        self.write(path, data)
        return hashlib.sha256(data).hexdigest()

    def write(self, path, data, *, terminal=False):
        path = Path(path)
        self.require(path)
        allowed_terminal = {"stdout": 65536, "stderr": 65536, "consumer.stdout": 65536,
                            "consumer.stderr": 65536, "process.json": 131072, "driver.json": 131072}
        if terminal and (path.parent != self.root or path.name not in allowed_terminal
                         or len(data) > allowed_terminal[path.name]):
            raise StorageRefusal("invalid-terminal-control-write")
        ceiling = self.settings["allowance_bytes"] - (0 if terminal else TERMINAL)
        if self.new_bytes + len(data) > ceiling:
            raise StorageRefusal("run-storage-limit")
        terminal_after = max(0, TERMINAL - self.terminal_bytes - (len(data) if terminal else 0))
        target = path.parent
        while not target.exists():
            target = target.parent
        fs = os.statvfs(target)
        fragment = fs.f_frsize
        if fragment <= 0:
            raise StorageRefusal("invalid-filesystem-observation")
        allocation = ((len(data) + fragment - 1) // fragment) * fragment
        available = fs.f_bavail * fragment
        required = allocation + terminal_after + self.settings["later_forecast_bytes"]
        self.observations.append({
            "path": str(path.relative_to(self.root)), "logicalBytesBefore": self.new_bytes,
            "encodedBytes": len(data), "ceilingBytes": ceiling, "terminal": terminal,
            "availableBytes": available, "fragmentBytes": fragment,
            "allocationEstimateBytes": allocation, "terminalAfterBytes": terminal_after,
            "laterForecastBytes": self.settings["later_forecast_bytes"],
            "requiredAvailableBytes": required, "admitted": available >= required,
        })
        if available < required:
            raise StorageRefusal("filesystem-capacity-insufficient")
        path.parent.mkdir(parents=True, exist_ok=True)
        # A final name advertises complete bytes only. Staging is invocation-owned
        # and stays in the destination parent so link publication is atomic.
        fd, staging_name = tempfile.mkstemp(prefix=".codex-capture-", suffix=".tmp", dir=path.parent)
        staging = Path(staging_name)
        try:
            try:
                os.fchmod(fd, 0o600)
                remaining = memoryview(data)
                while remaining:
                    written = os.write(fd, remaining)
                    if written <= 0:
                        raise StorageRefusal("capture-write-incomplete")
                    remaining = remaining[written:]
                if os.fstat(fd).st_size != len(data):
                    raise StorageRefusal("capture-write-incomplete")
                os.fsync(fd)
            finally:
                try:
                    # Failed staging still consumes this invocation's allowance.
                    count = os.fstat(fd).st_size
                    self.new_bytes += count
                    if terminal:
                        self.terminal_bytes += count
                finally:
                    os.close(fd)
            # Unlike rename/replace, link refuses a final name that already exists,
            # including one created after admission. Never remove that final name.
            os.link(staging, path)
        finally:
            # Only this call's staging name is eligible for cleanup. Abrupt process
            # termination may leave staging; a fresh call uses a new unique name.
            staging.unlink(missing_ok=True)
