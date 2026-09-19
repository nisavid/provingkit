"""Full real case/rubric/query fixtures with explicitly synthetic observations only."""

import json
import shlex

from .support import (
    ROOT,
    SKILL,
    SourceFixture,
    reference,
    sha,
    synthetic_execute,
    synthetic_grade,
    write,
)

ENTRY = "plugins/mergecraft/skills/writing-reviewable-pr-descriptions/SKILL.md"
TRIGGERS = (
    "evals/mergecraft/skills/writing-reviewable-pr-descriptions/trigger-evals.json"
)


class ReconciliationFixture(SourceFixture):
    def __init__(self, root):
        super().__init__(root)
        _core, inventory = reference()
        write(
            self.source / TRIGGERS,
            (ROOT / TRIGGERS).read_bytes(),
        )
        write(
            self.source / ENTRY,
            b"---\nname: writing-reviewable-pr-descriptions\ndescription: Synthetic test description.\n---\nSynthetic baseline body.\n",
        )
        self.baseline = self.commit(
            "Synthetic baseline with all real case and query coordinates"
        )
        with (self.source / ENTRY).open("ab") as stream:
            stream.write(
                b"Synthetic changed writer input to make receipt selection required.\n"
            )
        self.revision = self.commit("Synthetic source S for adapter mechanics only")
        self.descriptor = inventory.descriptor(self.source, self.revision, SKILL)
        assert self.descriptor["status"] == "ready", self.descriptor["diagnostics"]
        self.snapshot = inventory.prepare(self.source, self.revision, SKILL)
        write(self.snapshot_path, self.snapshot)
        write(self.descriptor_path, self.descriptor)
        self.binding["repository_head"] = self.revision
        self.binding["source_sha256"] = {
            p: sha((self.source / p).read_bytes())
            for p in self.binding["source_sha256"]
        }
        write(self.binding_path, self.binding)

    def applications(self, output, failures=()):
        from scripts.mergecraft_pr_writing_evals import receipt_artifacts as a

        result = self.prepare(output)
        digest = result["manifest_sha256"]
        (output / "STOP_LAUNCHES").unlink()  # Disposable synthetic fixture only.
        for number in range(11):
            for repetition in (1, 2, 3):
                synthetic_execute(output, digest, number, repetition)
                execution = a.project_execution(output, digest, number, repetition)
                grade, config = synthetic_grade(output, execution, number, repetition)
                value = a.read(grade)
                config_value = a.read(config)
                config_value["model_basis"] = "configured"
                write(config, config_value)
                for n, rep, expectation in failures:
                    if (n, rep) == (number, repetition):
                        value["expectations"][expectation]["passed"] = False
                write(grade, value)
                a.project_grading(
                    output,
                    digest,
                    number,
                    repetition,
                    grade,
                    sha(grade.read_bytes()),
                    config,
                    sha(config.read_bytes()),
                )
        (output / "STOP_LAUNCHES").write_text(
            "Synthetic fixture complete; no provider dispatch.\n"
        )
        return digest

    def discovery(self, freeze, wrong_selection=None):
        from scripts.mergecraft_pr_writing_evals import receipt_artifacts as a

        freeze.mkdir()
        rows = a.read(self.inputs / "native-reference/selection-contract.json")["rows"]
        plan = []
        client = a.read(self.inputs / "input-manifest.json")["client_binding"]
        for original in rows:
            row = dict(original)
            row["marker"] = "SYNTHETIC_SENTINEL_" + str(row["index"])
            row["probe_file"] = (
                f"selection-probes/{row['id']}/.agents/skills/{row['skill']}/SKILL.md"
            )
            row["command"] = [
                client["path"],
                "exec",
                "--json",
                "--ephemeral",
                "--ignore-user-config",
                "--skip-git-repo-check",
                "--sandbox",
                "read-only",
                "-C",
                str(freeze / "selection-runs" / row["id"] / "cwd"),
                "-c",
                "model_reasoning_effort=xhigh",
                "-m",
                "gpt-6-astra",
                row["probe_prompt"],
            ]
            probe = (
                "---\nname: writing-reviewable-pr-descriptions\ndescription: Synthetic test description.\n---\nReply exactly: "
                + row["marker"]
                + "\n"
            )
            write(freeze / row["probe_file"], probe.encode())
            plan.append(row)
        write(freeze / "selection-plan.json", plan)
        method = a.read(self.inputs / "native-reference/method-contract.json")
        manifest = {
            "helper_sha256": method["helper_sha256"],
            "selection_runner_sha256": method["selection_constructor_sha256"],
            "kind": "synthetic-native-freeze-not-runtime-evidence",
            "source_sha256": {
                ENTRY: sha((self.source / ENTRY).read_bytes()),
                TRIGGERS: sha((self.source / TRIGGERS).read_bytes()),
            },
            "codex": {**client, "model": "gpt-6-astra", "effort": "xhigh"},
            "artifacts": {
                str(p.relative_to(freeze)): sha(p.read_bytes())
                for p in freeze.rglob("*")
                if p.is_file()
            },
        }
        write(freeze / "manifest.json", manifest)
        digest = sha((freeze / "manifest.json").read_bytes())
        for row in plan:
            run = freeze / "selection-runs" / row["id"]
            probe_path = f"home/.agents/skills/{row['skill']}/SKILL.md"
            probe = (freeze / row["probe_file"]).read_bytes()
            loaded = row["should_trigger"] != (row["index"] == wrong_selection)
            response = row["marker"] if loaded else "SKILL_NOT_TRIGGERED"
            events = [
                {"type": "thread.started", "thread_id": "synthetic-probe-" + row["id"]},
                {"type": "turn.started"},
            ]
            if loaded:
                events.append(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "command_execution",
                            "id": "read-1",
                            "command": "/bin/sh -c "
                            + shlex.quote("cat " + str(run / probe_path)),
                            "aggregated_output": probe.decode(),
                            "exit_code": 0,
                            "status": "completed",
                        },
                    }
                )
            events.extend(
                [
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": response},
                    },
                    {"type": "turn.completed"},
                ]
            )
            for name, value in {
                "case.json": row,
                "command.json": row["command"],
                "prompt.txt": row["probe_prompt"].encode(),
                "query.json": {"query": row["query"], "effort": "xhigh"},
                "environment.json": {"synthetic": True},
                "stdout.jsonl": b"".join(
                    (json.dumps(e) + "\n").encode() for e in events
                ),
                "stderr.log": b"",
                "response.txt": response.encode(),
                probe_path: probe,
            }.items():
                write(run / name, value)
            record = {
                "manifest_sha256": digest,
                "case_id": row["id"],
                "started_at": "synthetic",
                "finished_at": "synthetic",
                "exit_code": 0,
                "timed_out": False,
                "launch_error": None,
                "source_error": None,
                "encoding_errors": [],
                "protocol_errors": [],
                "protocol_valid": True,
                "messages": [response],
                "events": events,
                "tool_events": [
                    e
                    for e in events
                    if e.get("item", {}).get("type") == "command_execution"
                ],
                "triggered": loaded,
                "decision_matches_expected": loaded == row["should_trigger"],
                "tool_trace_review": "pending: inspect actual probe-body read and other tool events",
                "technically_valid": True,
                "artifact_sha256": {
                    str(p.relative_to(run)): sha(p.read_bytes())
                    for p in run.rglob("*")
                    if p.is_file()
                },
            }
            write(run / "record.json", record)
        return digest
