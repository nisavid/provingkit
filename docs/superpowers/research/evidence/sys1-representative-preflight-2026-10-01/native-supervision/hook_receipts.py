"""Reconcile documented lifecycle receipts with passive captures by event count.

Native run IDs and observer UUIDs are distinct. Aggregate agreement is not a
per-invocation identity join or proof of effective containment.
"""

from collections import Counter
import json


def require(condition, message):
    if not condition:
        raise ValueError(message)


class HookReceipts:
    def __init__(self, harness, settings):
        self.harness, self.settings = harness, str(settings)
        self.started, self.completed = {}, {}

    def receive(self, message, session):
        if self.harness == "claude":
            subtype = message.get("subtype")
            if message.get("type") != "system" or subtype not in {"hook_started", "hook_progress", "hook_response"}:
                return False
            require(message.get("session_id") == session, "hook receipt session differs")
            ident, event = message.get("hook_id"), message.get("hook_event")
            require(event in {"PostToolUse", "Stop"} and isinstance(message.get("hook_name"), str),
                    "unexpected Claude hook")
            identity = (event, message["hook_name"])
            phase = {"hook_started": "start", "hook_progress": "progress", "hook_response": "end"}[subtype]
            if phase != "start":
                require(all(message.get(key) == "" for key in ("stdout", "stderr", "output")),
                        "passive Claude hook emitted output")
            if phase == "end":
                require(message.get("outcome") == "success" and message.get("exit_code", 0) == 0,
                        "Claude passive hook did not succeed")
        else:
            method = message.get("method")
            if method not in {"hook/started", "hook/completed"}:
                return False
            params = message.get("params", {})
            run = params.get("run", {})
            require(params.get("threadId") == session, "hook receipt session differs")
            ident, native_event = run.get("id"), run.get("eventName")
            events = {"postToolUse": "PostToolUse", "stop": "Stop"}
            require(native_event in events and run.get("sourcePath") == self.settings
                    and run.get("handlerType") == "command" and run.get("executionMode") == "sync"
                    and run.get("entries") == [], "unexpected Codex hook or emitted output")
            event = events[native_event]
            identity = (event, params.get("turnId"), run.get("scope"), run.get("sourcePath"), run.get("startedAt"))
            phase = "start" if method == "hook/started" else "end"
            require(run.get("status") == ("running" if phase == "start" else "completed"),
                    "Codex passive hook did not succeed")
        require(isinstance(ident, str) and bool(ident), "hook receipt ID missing")
        key = (session, None if self.harness == "claude" else params.get("turnId"), ident)
        if phase == "start":
            require(key not in self.started, "duplicate hook start")
            self.started[key] = identity
        else:
            require(self.started.get(key) == identity and key not in self.completed,
                    "unmatched or duplicate hook receipt")
            if phase == "end":
                self.completed[key] = identity
        return True

    def reconcile(self, root, session, completed_turns):
        require(not (root / "private/observer-failure.json").exists(), "passive observer unavailable")
        require(self.started == self.completed, "unfinished native hook receipts")
        counts = Counter(identity[0] for identity in self.completed.values())
        captured = Counter()
        paths = sorted((root / "private/hooks").iterdir())
        for path in paths:
            require(path.is_file() and path.suffix == ".json", "unfinished or unexpected hook capture")
            record = json.loads(path.read_text())
            raw = record.get("raw_hook", {})
            require(record.get("status") == "captured" and record.get("invocation_id") == path.stem
                    and raw.get("session_id") == session and raw.get("cwd") == str(root / "project")
                    and raw.get("hook_event_name") in {"PostToolUse", "Stop"}, "invalid passive capture")
            captured[raw["hook_event_name"]] += 1
        require(counts == captured, "native hook and capture counts differ")
        require(counts["Stop"] >= completed_turns, "native Stop coverage unavailable")
        return {"completed_native_invocations": [
                    {"session_id": item[0], "turn_id": item[1], "hook_id": item[2]}
                    for item in sorted(self.completed, key=json.dumps)], "event_counts": dict(counts),
                "capture_files": [str(path) for path in paths],
                "claim": "aggregate agreement by event; no individual native/capture identity join"}
