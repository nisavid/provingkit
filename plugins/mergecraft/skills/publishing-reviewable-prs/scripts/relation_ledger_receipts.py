"""Private body-edit evidence, isolated from ordinary publication receipt chains."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import stat
import uuid

from publication_receipts import (
    ReceiptError, _fsync_directory, _private_directory, _write_probe,
)
from validate_relation_ledger import canonical_json, sha256, strict_json


@dataclass(frozen=True)
class LeaseIdentity:
    """The repository/number identity consumed by the canonical publication lease."""

    repository: str
    pr_number: int


class RelationLedgerReceipts:
    """One unresolved mutation marker per PR; immutable, redacted result receipts."""

    def __init__(self, root: Path, target: dict):
        parent = _private_directory(root / "relation-ledger", create=True, parent=root)
        key = sha256("\0".join(target[name] for name in ("host", "repository_id", "entity_id")))
        self.directory = _private_directory(parent / key, create=True, parent=parent)
        _write_probe(self.directory)
        self.pending = self.directory / "pending.json"

    def _read(self, path: Path) -> dict:
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(descriptor, "rb") as stream:
                metadata = os.fstat(stream.fileno())
                if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                        or metadata.st_mode & 0o077 or metadata.st_size > 65536):
                    raise ReceiptError("relation-ledger evidence must be private owned regular files")
                raw = stream.read(65537)
            value = strict_json(raw.decode("utf-8"))
            if not isinstance(value, dict) or raw != canonical_json(value).encode("utf-8"):
                raise ReceiptError("relation-ledger evidence is not canonical")
            return value
        except (OSError, ValueError):
            raise ReceiptError("cannot read relation-ledger evidence") from None

    def pending_attempt(self, result: dict, manifest_sha256: str) -> dict | None:
        try:
            self.pending.lstat()
        except FileNotFoundError:
            return None
        value = self._read(self.pending)
        expected = {**result, "status": "pending", "scope": "pr-relation-ledger",
                    "manifest_sha256": manifest_sha256, "attempt_id": value.get("attempt_id"),
                    "renewal_receipt_sha256": value.get("renewal_receipt_sha256")}
        if (value != expected or not isinstance(value.get("attempt_id"), str)
                or re.fullmatch(r"[0-9a-f-]{36}", value["attempt_id"]) is None
                or (value.get("renewal_receipt_sha256") is not None
                    and (not isinstance(value["renewal_receipt_sha256"], str)
                         or re.fullmatch(r"[0-9a-f]{64}", value["renewal_receipt_sha256"]) is None))):
            raise ReceiptError("pending attempt does not match the supplied intent")
        return value

    def validate_renewal(self, digest: str, pending: dict) -> None:
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ReceiptError("invalid renewal receipt digest")
        value = self._read(self.directory / f"{digest}.json")
        unsigned = dict(value)
        stored_digest = unsigned.pop("receipt_sha256", None)
        bindings = ("manifest_sha256", "attempt_id", "scope", "schema_version", "operation", "host",
                    "repository", "repository_id", "entity_id", "number", "before_body_sha256",
                    "after_body_sha256", "title_sha256", "state", "is_draft")
        if (stored_digest != digest or sha256(canonical_json(unsigned)) != digest
                or any(value.get(key) != pending[key] for key in bindings)
                or value.get("provenance") != "observed-preimage" or value.get("status") != "blocked"
                or value.get("no_op") is not True or value.get("renewal_required") is not True):
            raise ReceiptError("renewal receipt does not match this unresolved attempt")

    def _write(self, path: Path, value: dict, *, replace_preimage: dict | None = None) -> None:
        payload = canonical_json(value).encode("utf-8")
        staged = self.directory / f".{path.name}.{uuid.uuid4()}.tmp"
        descriptor = None
        created = False
        try:
            descriptor = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            created = True
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = None
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            if replace_preimage is None:
                # Linking is atomic and cannot overwrite an existing intent or
                # receipt. A crash exposes either no final file or complete bytes.
                os.link(staged, path, follow_symlinks=False)
            else:
                # The caller holds the canonical publication lease. Renew only
                # its bound predecessor; staging failures leave that guard intact.
                if self._read(path) != replace_preimage:
                    raise ReceiptError("pending attempt changed before renewal installation")
                os.replace(staged, path)
            _fsync_directory(self.directory)
        except OSError:
            raise ReceiptError("cannot durably record relation-ledger evidence") from None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if created:
                try:
                    staged.unlink(missing_ok=True)
                    _fsync_directory(self.directory)
                except OSError:
                    raise ReceiptError("cannot clean this operation's staged evidence") from None

    def begin(self, result: dict, manifest_sha256: str, renewal_receipt_sha256: str | None = None,
              prior_attempt: dict | None = None) -> str:
        attempt_id = str(uuid.uuid4())
        value = {**result, "status": "pending", "scope": "pr-relation-ledger",
                 "attempt_id": attempt_id, "manifest_sha256": manifest_sha256,
                 "renewal_receipt_sha256": renewal_receipt_sha256}
        if renewal_receipt_sha256 is None:
            self._write(self.pending, value)
        else:
            if prior_attempt is None:
                raise ReceiptError("renewal requires the bound prior attempt")
            self._write(self.pending, value, replace_preimage=prior_attempt)
        return attempt_id

    def clear(self) -> None:
        try:
            self.pending.unlink()
            _fsync_directory(self.directory)
        except OSError:
            raise ReceiptError("cannot clear relation-ledger attempt") from None

    def record(self, result: dict, manifest_sha256: str, review: dict, attempt_id: str | None,
               renewal_receipt_sha256: str | None = None) -> dict:
        receipt_id = str(uuid.uuid4())
        value = {**result, "scope": "pr-relation-ledger", "receipt_id": receipt_id,
                 "manifest_sha256": manifest_sha256, "review": review, "attempt_id": attempt_id,
                 "renewal_receipt_sha256": renewal_receipt_sha256,
                 "created_at": datetime.now(timezone.utc).isoformat()}
        value.pop("receipt_sha256", None)
        digest = sha256(canonical_json(value))
        value["receipt_sha256"] = digest
        self._write(self.directory / f"{digest}.json", value)
        return {**result, "receipt_id": receipt_id, "receipt_sha256": digest}
