"""Synthetic Git fixtures only. None is the final PR84 source S."""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from scripts.mergecraft_pr_writing_evals.binding import PACKAGE, load_processor

ROOT = Path(__file__).resolve().parents[2]
CORPUS = "evals/mergecraft/skills/writing-reviewable-pr-descriptions/evals.json"
SKILL = "mergecraft/writing-reviewable-pr-descriptions"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        value if isinstance(value, bytes) else (json.dumps(value) + "\n").encode()
    )


def read(path):
    return json.loads(path.read_bytes())


def reference():
    core, inventory, _ = load_processor()
    return core, inventory


class SourceFixture:
    def __init__(self, root):
        self.root = root
        self.source = root / "synthetic-source"
        self.source.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic Test")
        self.git("config", "user.email", "synthetic@example.invalid")
        core, inventory = reference()
        plan = read(PACKAGE / "correspondence.json")
        for path in plan["required_source_paths"]:
            write(
                self.source / path,
                b"Synthetic source fixture; not reviewed instructions.\n",
            )
        write(
            self.source / "plugins/mergecraft/topology.json",
            {
                "skills": {
                    "writing-reviewable-pr-descriptions": {"calls": []},
                    "interacting-with-pr-review-feedback": {"calls": []},
                    "writing-github-issue-and-pr-markdown": {"calls": []},
                }
            },
        )
        for name in (
            "interacting-with-pr-review-feedback",
            "writing-github-issue-and-pr-markdown",
        ):
            write(
                self.source / f"plugins/mergecraft/skills/{name}/SKILL.md",
                b"Synthetic neighbor.\n",
            )
        write(
            self.source / "plugins/proseweaving/topology.json",
            {"skills": {"writing-for-people": {"calls": []}}},
        )
        write(
            self.source / "release/provingkit/definition-v1.json",
            {
                "membership": {
                    "members": [
                        {
                            "id": "mergecraft",
                            "content_identity": {
                                "path": "release/plugin-content-locks/mergecraft.json"
                            },
                        },
                        {
                            "id": "proseweaving",
                            "content_identity": {
                                "path": "release/plugin-content-locks/proseweaving.json"
                            },
                        },
                    ]
                }
            },
        )
        for member in ("mergecraft", "proseweaving"):
            write(
                self.source / f"release/plugin-content-locks/{member}.json",
                {"synthetic": True},
            )
        write(self.source / CORPUS, (ROOT / CORPUS).read_bytes())
        corpus = json.loads((ROOT / CORPUS).read_bytes())
        for case in corpus["evals"]:
            for fixture in case["files"]:
                path = "evals/mergecraft/skills/" + fixture
                write(self.source / path, (ROOT / path).read_bytes())
        write(
            self.source
            / "evals/mergecraft/skills/writing-reviewable-pr-descriptions/trigger-evals.json",
            (ROOT / CORPUS.replace("evals.json", "trigger-evals.json")).read_bytes(),
        )
        # Retain the canonical accepted strings, identities, severities, and reviews.
        entries = [
            e
            for e in read(ROOT / inventory.EXPECTATION_MAP)["entries"]
            if e["source"]["path"] == CORPUS
        ]
        write(
            self.source / inventory.EXPECTATION_MAP,
            {"schema_version": 1, "entries": entries},
        )
        semantic = {
            "source": {
                "path": CORPUS,
                "sha256": sha((self.source / CORPUS).read_bytes()),
            },
            "pointer": "",
            "owners": [SKILL],
            "role": "current-corpus",
            "behavior_inputs": plan["required_source_paths"],
            "dependencies": [],
        }
        write(
            self.source / inventory.INPUT_MAP,
            {
                "schema_version": 1,
                "entries": [
                    {
                        **semantic,
                        "status": "accepted",
                        "review": {
                            "decision": "accepted",
                            "reference": "synthetic-test-only",
                            "mapping_sha256": core.document_digest(semantic),
                        },
                    }
                ],
            },
        )
        contract = read(PACKAGE / "correspondence.json")
        for path in contract["processor_files"]:
            target = self.source / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)
        for path in PACKAGE.iterdir():
            if path.suffix in (".py", ".json"):
                write(
                    self.source / "scripts/mergecraft_pr_writing_evals" / path.name,
                    path.read_bytes(),
                )
        self.revision = self.commit("Synthetic committed fixture, never final S")
        self.processing_revision = self.revision
        self.inputs = root / "frozen-inputs"
        self.runtime = root / "runtime.json"
        write(
            self.runtime,
            {
                "path": sys.executable,
                "sha256": sha(Path(sys.executable).read_bytes()),
                "version": "constructed-test",
            },
        )
        self.descriptor = inventory.descriptor(self.source, self.revision, SKILL)
        assert self.descriptor["status"] == "ready", self.descriptor["diagnostics"]
        self.snapshot = inventory.prepare(self.source, self.revision, SKILL)
        self.snapshot_path = root / "synthetic-snapshot.json"
        self.descriptor_path = root / "synthetic-descriptor.json"
        write(self.snapshot_path, self.snapshot)
        write(self.descriptor_path, self.descriptor)
        review = root / "synthetic-review.json"
        write(review, {"scope": "Synthetic tests only; no real source review."})
        self.binding = {
            "status": "reviewed-final-pr84-source",
            "repository_head": self.revision,
            "source_review": {"path": str(review), "sha256": sha(review.read_bytes())},
            "source_sha256": {
                p: sha((self.source / p).read_bytes())
                for p in plan["required_source_paths"]
            },
        }
        self.binding_path = root / "synthetic-binding.json"
        write(self.binding_path, self.binding)

    def git(self, *args):
        return subprocess.check_output(
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "commit.gpgsign=false",
                *args,
            ],
            cwd=self.source,
            text=True,
        ).strip()

    def commit(self, message):
        self.git("add", "--all")
        self.git("commit", "-qm", message)
        return self.git("rev-parse", "HEAD")

    def freeze(self):
        from scripts.mergecraft_pr_writing_evals.inputs import freeze_inputs

        freeze_inputs(
            self.source,
            self.revision,
            self.runtime,
            sha(self.runtime.read_bytes()),
            self.processing_revision,
            self.inputs,
            identity_kind="constructed-test",
        )
        return self.inputs

    def prepare(self, output):
        from scripts.mergecraft_pr_writing_evals.prepare_application import prepare

        if not self.inputs.exists():
            self.freeze()
        core, _ = reference()
        return prepare(
            self.source,
            self.binding_path,
            sha(self.binding_path.read_bytes()),
            sha((self.inputs / "input-manifest.json").read_bytes()),
            output,
            inputs=self.inputs,
            receipt_snapshot=self.snapshot_path,
            receipt_snapshot_file_sha256=sha(self.snapshot_path.read_bytes()),
            receipt_snapshot_sha256=core.document_digest(self.snapshot),
            receipt_descriptor=self.descriptor_path,
            receipt_descriptor_sha256=sha(self.descriptor_path.read_bytes()),
        )


def synthetic_execute(
    output,
    manifest_hash,
    number=0,
    repetition=1,
    *,
    response="Synthetic answer.\u2028\r\nExact bytes.",
    code=0,
    thread_id=None,
):
    """Only the provider process boundary is substituted; never launch Codex."""
    from scripts.mergecraft_pr_writing_evals.run_application import execute

    actual_run = subprocess.run
    manifest = json.loads((output / "manifest.json").read_bytes())
    events = [
        {
            "type": "thread.started",
            "thread_id": f"synthetic-{number}-{repetition}"
            if thread_id is None
            else thread_id,
        },
        {"type": "item.completed", "item": {"type": "agent_message", "text": response}},
        {"type": "turn.completed", "usage": {}},
    ]
    stdout = (
        "\r\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\r\n"
    ).encode()

    def boundary(command, **kwargs):
        if command[0] == manifest["client_binding"]["path"]:
            assert (
                kwargs["input"]
                == (output / f"eval-{number}/with_skill/prompt.txt").read_bytes()
            )
            assert command[1:8] == [
                "exec",
                "--json",
                "--ephemeral",
                "--ignore-user-config",
                "--skip-git-repo-check",
                "--sandbox",
                "read-only",
            ]
            assert command[-5:] == [
                "-m",
                "gpt-6-astra",
                "-c",
                "model_reasoning_effort=xhigh",
                "-",
            ]
            kwargs["stdout"].write(stdout)
            kwargs["stderr"].write(b"")
            return subprocess.CompletedProcess(command, code)
        assert command[0] == "git", command
        return actual_run(command, **kwargs)

    with patch("subprocess.run", side_effect=boundary):
        return execute(output, manifest_hash, number, repetition)


def synthetic_grade(output, projection, number=0, repetition=1, passed=True):
    envelope = json.loads((output / projection["executor_output"]).read_bytes())
    policy = json.loads(
        (output / "method-inputs/withheld/expectation-policy.json").read_bytes()
    )
    expectations = next(
        c["expectations"] for c in policy["cases"] if c["case_id"] == number
    )
    grade = {k: envelope[k] for k in ("snapshot_sha256", "case_id", "repetition")}
    grade.update(
        model_id="synthetic-grader",
        executor_output_sha256=projection["executor_output_sha256"],
        response_sha256=sha(envelope["response"].encode()),
        expectations=[
            {
                "id": e["id"],
                "passed": passed,
                "evidence": "Synthetic mechanical judgment, not model evidence.",
            }
            for e in expectations
        ],
        supplemental_observations=[
            {
                "detail": "Synthetic supplementary observation retained only in the rich grade."
            }
        ],
    )
    grade_path = output / f"grading-inputs/case-{number}/repetition-{repetition}.json"
    config_path = (
        output
        / f"grading-inputs/case-{number}/repetition-{repetition}-configuration.json"
    )
    write(grade_path, grade)
    write(
        config_path,
        {
            "model_id": "synthetic-grader",
            "basis": "Synthetic test only; no grader session.",
        },
    )
    return grade_path, config_path


def retained_value(root, reference):
    value = read(root / reference["path"])
    for key in reference.get("pointer", "").split("/")[1:]:
        key = key.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value
