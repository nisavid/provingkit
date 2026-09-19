"""Bind an explicit member Receipt check to the structurally checked source."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import behavior_eval_receipts as core
import behavior_eval_inventory as inventory


PROCEDURE_PATH = "docs/behavior-eval-receipts.md"


@dataclass(frozen=True)
class Context:
    repository: Path
    base: str
    candidate: str
    receipt_root: str
    procedure_revision: str
    procedure_sha256: str


def _check_checkout(repository, candidate):
    root = core.git(repository, "rev-parse", "--show-toplevel").decode().strip()
    core.require(Path(root).resolve() == repository, "repository must be the Git checkout root")
    head = core.git(repository, "rev-parse", "HEAD").decode().strip()
    core.require(head == candidate, "checkout HEAD does not match candidate")
    core.require(not core.git(repository, "status", "--porcelain", "-z", "--untracked-files=all"),
                 "Receipt source-stage validation requires a clean candidate checkout")


def prepare_context(parser, arguments, repository, *, writing=False):
    """Reject incomplete or conflicting context before structural work or writes."""
    values = [arguments.base, arguments.candidate, arguments.receipt_root, arguments.procedure_revision]
    if all(value is None for value in values):
        return None
    if not all(value is not None for value in values):
        parser.error("Receipt context requires --base, --candidate, --receipt-root, and --procedure-revision together")
    if not arguments.source_stage:
        parser.error("Receipt context requires --source-stage")
    if writing:
        parser.error("Receipt context cannot be combined with source preparation or content-lock writes")
    try:
        repository = Path(repository).resolve()
        base = core.revision(repository, arguments.base)
        candidate = core.revision(repository, arguments.candidate)
        procedure_revision = core.revision(repository, arguments.procedure_revision)
        receipt_root = core.relative_path(arguments.receipt_root)
        _check_checkout(repository, candidate)
        procedure = core.source_bytes(repository, procedure_revision, PROCEDURE_PATH)
        maintained = (Path(__file__).resolve().parents[1] / PROCEDURE_PATH).read_bytes()
        core.require(procedure == maintained, "procedure revision differs from the running source-stage procedure")
        return Context(repository, base, candidate, receipt_root, procedure_revision,
                       hashlib.sha256(procedure).hexdigest())
    except (core.ReceiptError, OSError, UnicodeError) as error:
        parser.error(str(error))


def check_context(context, member):
    """Emit the member Receipt result after structural success on the same C."""
    try:
        _check_checkout(context.repository, context.candidate)
        result = inventory.check_member(context.repository, context.base, context.candidate,
                                        context.receipt_root, member)
        result["source_stage"] = {
            "structural_candidate_revision": context.candidate,
            "procedure_revision": context.procedure_revision,
            "procedure_sha256": context.procedure_sha256,
            "member_qualification": "not-evaluated",
        }
    except (core.ReceiptError, inventory.InventoryError, ValueError, KeyError, TypeError, OSError) as error:
        result = {"status": "error", "message": str(error)}
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False))
    return {"pass": 0, "not-required": 0, "fail": 1}.get(result["status"], 2)
