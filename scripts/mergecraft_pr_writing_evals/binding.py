"""Explicit correspondence to the reviewed, repository-owned processor."""

import hashlib
import importlib
import json
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
REPOSITORY = PACKAGE.parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def _method_files():
    return {
        "scripts/mergecraft_pr_writing_evals/" + path.name: {
            "sha256": sha(path.read_bytes()),
            "mode": "100755" if path.stat().st_mode & 0o111 else "100644",
        }
        for path in sorted(PACKAGE.iterdir())
        if path.suffix in (".py", ".json")
    }


_LOADED_METHOD_FILES = _method_files()


def adapter_source(repository, revision):
    """Bind the loaded method's canonical paths, bytes, and Git modes to S."""
    require(
        PACKAGE == REPOSITORY / "scripts/mergecraft_pr_writing_evals",
        "loaded adapter path differs",
    )
    observed = _method_files()
    require(observed == _LOADED_METHOD_FILES, "loaded adapter changed after import")
    core, _, _ = load_processor()
    inventory = core.source_inventory(repository, revision)
    for path, identity in observed.items():
        loaded = REPOSITORY / path
        working = Path(repository) / path
        require(
            not loaded.is_symlink()
            and inventory.get(path) == (identity["mode"], "blob")
            and sha(core.source_bytes(repository, revision, path))
            == identity["sha256"],
            "committed adapter differs: " + path,
        )
        require(
            working.is_file()
            and not working.is_symlink()
            and sha(working.read_bytes()) == identity["sha256"]
            and bool(working.stat().st_mode & 0o111) == (identity["mode"] == "100755"),
            "working adapter differs: " + path,
        )
    return observed


def load_processor(repository=REPOSITORY):
    repository = Path(repository).resolve()
    contract = json.loads((PACKAGE / "correspondence.json").read_bytes())
    for path, digest in contract["processor_files"].items():
        require(
            (repository / path).is_file()
            and sha((repository / path).read_bytes()) == digest,
            "reviewed processor differs or is not integrated: " + path,
        )
    scripts = repository / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    core = importlib.import_module("behavior_eval_receipts")
    inventory = importlib.import_module("behavior_eval_inventory")
    for module in (core, inventory, inventory.corpora):
        require(
            Path(module.__file__).resolve().parent == scripts,
            "another processor is already loaded",
        )
    return core, inventory, contract
