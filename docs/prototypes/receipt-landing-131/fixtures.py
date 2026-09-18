"""Ordinary constructed records and real disposable Git histories for #131."""

import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

PROCESSOR = "24c2d712a0be6a95958713ec80c7e06a89abdc6c"
PROCESSING = (
    "scripts/behavior_eval_receipts.py",
    "scripts/behavior_eval_corpora.py",
    "scripts/behavior_eval_inventory.py",
    "release/behavior-eval-policy.json",
    "release/behavior-eval-receipt-v1.schema.json",
)
KEY = "example/writing"
ROOT = "release/receipts"
RECEIPT = f"{ROOT}/{KEY}.json"
CONTEXT = "release/prototype-landing-context.json"
ENTRY = "plugins/example/skills/writing/SKILL.md"
REFERENCE = "plugins/example/references/writing.md"
CORPUS = "plugins/example/skills/writing/evals/evals.json"
TRIGGERS = "plugins/example/skills/writing/evals/trigger-evals.json"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def write(repo, path, value):
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(value if isinstance(value, bytes) else
                       value.encode() if isinstance(value, str) else encoded(value))


def git(repo, *args, raw=False, check=True, committer_date="2026-09-18T12:00:00Z"):
    # These settings apply only to this disposable-fixture command. They never
    # alter the real repository's signing, hooks, configuration, or credentials.
    env = {**{key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
           "GIT_AUTHOR_DATE": "2026-09-18T12:00:00Z",
           "GIT_COMMITTER_DATE": committer_date, "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": os.devnull}
    result = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c",
                             "commit.gpgsign=false", *args], cwd=repo, env=env,
                            capture_output=True, check=check)
    if not check:
        return result.returncode
    return result.stdout if raw else result.stdout.decode().strip()


def commit(repo, message):
    git(repo, "add", "--all")
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD")


def load_adapter(source, destination):
    identities = {}
    for path in PROCESSING:
        raw = subprocess.check_output(["git", "show", f"{PROCESSOR}:{path}"], cwd=source)
        write(destination, path, raw)
        identities[path] = {"sha256": sha(raw), "mode": "100644"}
        observed = subprocess.check_output(
            ["git", "ls-tree", PROCESSOR, "--", path], cwd=source).decode().split()[0]
        assert observed == "100644", (path, observed)
    sys.path.insert(0, str(destination / "scripts"))
    inventory = importlib.import_module("behavior_eval_inventory")
    return inventory, identities


def create_repo(repo, adapter):
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "Receipt Prototype")
    git(repo, "config", "user.email", "prototype@example.invalid")
    for path in PROCESSING:
        write(repo, path, (adapter / path).read_bytes())
    write(repo, "release/provingkit/definition-v1.json", {"membership": {"members": [
        {"id": "example", "content_identity": {"path": "release/plugin-content-locks/example.json"}}]}})
    write(repo, "release/plugin-content-locks/example.json", {})
    write(repo, "plugins/example/topology.json", {"skills": {
        "writing": {"calls": []}, "editing": {"calls": []}}})
    write(repo, REFERENCE, "Preserve the supplied facts.\n")
    for name in ("writing", "editing"):
        prefix = f"plugins/example/skills/{name}"
        write(repo, f"{prefix}/SKILL.md", f"---\nname: {name}\ndescription: Use for {name}.\n---\n"
              f"Do {name}.\n" + ("Read [writing guidance](../../references/writing.md).\n" if name == "writing" else ""))
        write(repo, f"{prefix}/evals/evals.json", {"skill_name": name, "evals": [
            {"id": index, "prompt": f"Constructed case {index}.", "fixture_paths": [], "expectations": [
                {"id": "keep", "text": "Keep the supplied meaning.", "severity": "quality"},
                {"id": "safe", "text": "Keep the supplied boundary.", "severity": "safety"}]}
            for index in (0, 1)]})
        write(repo, f"{prefix}/evals/trigger-evals.json", [
            {"query": f"Do {name}.", "should_trigger": True},
            {"query": "What time is it?", "should_trigger": False}])
    for path in ("release/behavior-eval-input-map.json", "release/behavior-eval-expectation-map.json"):
        write(repo, path, {"schema_version": 1, "entries": []})
    base = commit(repo, "Original comparison base")
    git(repo, "switch", "-qc", "source")
    write(repo, ENTRY, (repo / ENTRY).read_bytes() + b"Use precise wording.\n")
    source = commit(repo, "Evaluated source")
    return base, source


def prepared_receipt(repo, source, inventory, private):
    snapshot = inventory.prepare(repo, source, KEY)
    snapshot_hash = inventory.core.document_digest(snapshot)
    runs = []
    for case_id in (0, 1):
        coordinate = {"source": CORPUS, "pointer": f"/evals/{case_id}", "id": case_id}
        for repetition in (1, 2, 3):
            stem = f"{case_id}-{repetition}"
            output = encoded({"snapshot_sha256": snapshot_hash, "case_id": coordinate,
                              "repetition": repetition, "model_id": "constructed-executor",
                              "response": "Constructed answer; no model was invoked."})
            write(private, f"output-{stem}.json", output)
            write(private, f"grade-{stem}.json", {
                "snapshot_sha256": snapshot_hash, "case_id": coordinate, "repetition": repetition,
                "model_id": "constructed-grader", "executor_output_sha256": sha(output),
                "expectations": [{"id": "keep", "passed": repetition != 3}, {"id": "safe", "passed": True}]})
            runs.append({"case_id": coordinate, "repetition": repetition,
                         "executor_output": f"output-{stem}.json", "grading": f"grade-{stem}.json"})
    triggers = []
    for index, triggered in enumerate((True, False)):
        coordinate = {"source": TRIGGERS, "pointer": f"/{index}", "id": None}
        write(private, f"trigger-{index}.json", {
            "snapshot_sha256": snapshot_hash, "case_id": coordinate, "model_id": "constructed-executor",
            "observation_kind": "recorded-invocation", "triggered": triggered})
        triggers.append({"case_id": coordinate, "observation": f"trigger-{index}.json"})
    write(private, "results.json", {"schema_version": 1, "snapshot_sha256": snapshot_hash,
        "executor_model_id": "constructed-executor", "grader_model_id": "constructed-grader",
        "runs": runs, "triggers": triggers})
    return inventory.core.produce(repo, snapshot, private / "results.json")


def reconciled_receipt(repo, source, processor, inventory, private):
    """Construct retained records, then invoke the unchanged reconciliation API."""
    cases = json.loads((repo / CORPUS).read_bytes())["evals"]
    queries = json.loads((repo / TRIGGERS).read_bytes())
    runs = [{"revision": source, "corpus": sha((repo / CORPUS).read_bytes()),
             "native_agent": f"constructed-{case['id']}-{rep}", "case_id": case["id"],
             "repetition": rep, "prompt": case["prompt"], "runtime": (repo / ENTRY).read_text(),
             "guidance": (repo / REFERENCE).read_text(), "response": "Constructed retained answer.",
             "executor": "constructed-executor", "grader": "constructed-grader",
             "rubric": case["expectations"], "grades": [
                 {"id": "keep", "passed": rep != 3}, {"id": "safe", "passed": True}]}
            for case in cases for rep in (1, 2, 3)]
    original = {"runs": runs, "triggers": [{"query": row["query"], "triggered": row["should_trigger"],
                "entrypoint": (repo / ENTRY).read_text(), "model": "constructed-executor"} for row in queries]}
    raw = encoded(original)
    write(private, "original.json", raw)

    def ref(pointer):
        return {"path": "original.json", "sha256": sha(raw), "format": "json", "pointer": pointer}

    declarations = []
    for index, run in enumerate(runs):
        prefix = f"/runs/{index}"
        declarations.append({
            "case_id": {"source": CORPUS, "pointer": f"/evals/{run['case_id']}", "id": run["case_id"]},
            "repetition": run["repetition"], "execution_record": ref(prefix),
            "original_revision": ref(prefix + "/revision"), "original_corpus_sha256": ref(prefix + "/corpus"),
            "prompt": ref(prefix + "/prompt"), "response": ref(prefix + "/response"),
            "grading_record": ref(prefix + "/grades"), "original_expectations": ref(prefix + "/rubric"),
            "grades": ref(prefix + "/grades"), "inputs": {
                ENTRY: {"representation": "utf8", "value": ref(prefix + "/runtime")},
                REFERENCE: {"representation": "utf8", "value": ref(prefix + "/guidance")}},
            "executor_model": {"basis": "configured", "value": ref(prefix + "/executor")},
            "grader_model": {"basis": "configured", "value": ref(prefix + "/grader")},
            "graded_response": {"representation": "utf8", "value": ref(prefix + "/response")},
            "rubric": {"representation": "expectations", "value": ref(prefix + "/rubric")},
            "previous_grading": [], "adjudication": None})
    triggers = [{"case_id": {"source": TRIGGERS, "pointer": f"/{index}", "id": None},
                 "observation_kind": "recorded-invocation", "record": ref(f"/triggers/{index}"),
                 "model": {"basis": "configured", "value": ref(f"/triggers/{index}/model")},
                 "query": ref(f"/triggers/{index}/query"), "triggered": ref(f"/triggers/{index}/triggered"),
                 "entrypoint": {"representation": "utf8", "value": ref(f"/triggers/{index}/entrypoint")},
                 "limits": ["Constructed local records; no model invocation."]} for index in range(2)]
    write(private, "reconciliation.json", {"schema_version": 1, "method": "reconciled-after-run",
        "executor_model_id": "constructed-executor", "grader_model_id": "constructed-grader",
        "runtime_inputs": [ENTRY, REFERENCE], "runtime_inputs_complete": True,
        "runs": declarations, "triggers": triggers})
    receipt = inventory.reconcile(repo, source, KEY, private / "reconciliation.json", processor)
    assert (private / "original.json").read_bytes() == raw
    return receipt


def land(repo, head, target, operation):
    git(repo, "checkout", "--detach", "-q", target)
    if operation == "squash":
        git(repo, "merge", "--squash", head)
        return commit(repo, "Squashed source and unchanged Receipt")
    if operation == "merge":
        git(repo, "merge", "--no-ff", "-qm", "Ancestry-preserving landing", head)
    elif operation == "ff-only":
        git(repo, "merge", "--ff-only", head)
    elif operation == "rebase":
        git(repo, "checkout", "--detach", "-q", head)
        git(repo, "rebase", "--force-rebase", "--onto", target, git(repo, "merge-base", head, target),
            committer_date="2026-09-18T13:00:00Z")
    else:
        raise ValueError(operation)
    return git(repo, "rev-parse", "HEAD")
