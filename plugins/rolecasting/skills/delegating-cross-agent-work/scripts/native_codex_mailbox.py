#!/usr/bin/env python3
"""Durable local bookkeeping for externally performed native Codex messaging."""

import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys


KINDS = frozenset({"submitted", "unknown", "refused", "received", "handled", "completed", "not_delivered"})
SUBMISSION_KINDS = frozenset({"submitted", "unknown", "refused"})


class MailboxError(ValueError):
    """An invalid or conflicting bookkeeping request."""


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise MailboxError(f"{name} must be a nonempty string")
    return value


def validate_message(message):
    required = {"message_id", "sender", "recipient", "owner", "payload", "authority_ref"}
    if not isinstance(message, dict) or not required <= message.keys():
        raise MailboxError("message requires message_id, sender, recipient, owner, payload, authority_ref")
    if message.keys() - required - {"holds"}:
        raise MailboxError("unknown message fields")
    for name in ("message_id", "authority_ref"):
        text(message[name], name)
    if not isinstance(message["payload"], str):
        raise MailboxError("payload must be a string")
    for name in ("sender", "recipient", "owner"):
        identity = message[name]
        if not isinstance(identity, dict) or identity.keys() != {"thread_id", "host_id"}:
            raise MailboxError(f"{name} requires exactly thread_id and host_id")
        for key in ("thread_id", "host_id"):
            text(identity[key], f"{name}.{key}")
    holds = message.get("holds", [])
    if not isinstance(holds, list) or any(not isinstance(item, str) for item in holds):
        raise MailboxError("holds must be a list of strings")
    return {**message, "holds": holds}


class Mailbox:
    """An offline store. No method sends, authenticates, authorizes, or retries."""

    def __init__(self, path, initialize=False):
        path = Path(path).resolve()
        if initialize:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
        self.db = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)
        try:
            self.db.execute("PRAGMA foreign_keys = ON")
            self.db.execute("PRAGMA synchronous = FULL")
            if initialize:
                self.db.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE messages (
                        message_id TEXT PRIMARY KEY NOT NULL,
                        content TEXT NOT NULL
                    );
                    CREATE TABLE attempts (
                        sequence INTEGER PRIMARY KEY,
                        message_id TEXT NOT NULL REFERENCES messages(message_id),
                        attempt_id TEXT UNIQUE NOT NULL,
                        actor TEXT NOT NULL,
                        after_attempt TEXT REFERENCES attempts(attempt_id),
                        nondelivery_ref TEXT,
                        decision_ref TEXT
                    );
                    CREATE TABLE observations (
                        sequence INTEGER PRIMARY KEY,
                        attempt_id TEXT NOT NULL REFERENCES attempts(attempt_id),
                        kind TEXT NOT NULL,
                        evidence_ref TEXT NOT NULL,
                        detail TEXT NOT NULL
                    );
                    PRAGMA user_version = 1;
                    COMMIT;
                """)
            if self.db.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise MailboxError("unsupported or uninitialized mailbox")
            self.db.execute("""
                SELECT m.content, a.attempt_id, o.kind
                FROM messages m LEFT JOIN attempts a USING (message_id)
                LEFT JOIN observations o USING (attempt_id) LIMIT 0
            """)
        except BaseException:
            self.db.close()
            raise

    def close(self):
        self.db.close()

    def plan(self, message):
        message = validate_message(message)
        content = json.dumps(message, ensure_ascii=True, sort_keys=True)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            row = self.db.execute(
                "SELECT content FROM messages WHERE message_id = ?", (message["message_id"],)
            ).fetchone()
            if row is not None and row[0] != content:
                raise MailboxError("message identity already binds different content")
            if row is None:
                self.db.execute(
                    "INSERT INTO messages VALUES (?, ?)", (message["message_id"], content)
                )
            result = {"created": row is None, "message": self.get(message["message_id"])}
        return result

    def claim(self, message_id, attempt_id, actor, after_attempt=None, decision_ref=None):
        text(message_id, "message_id")
        text(attempt_id, "attempt_id")
        if not isinstance(actor, dict) or actor.keys() != {"thread_id", "host_id"}:
            raise MailboxError("actor requires exactly thread_id and host_id")
        for key in ("thread_id", "host_id"):
            text(actor[key], f"actor.{key}")
        actor_content = json.dumps(actor, ensure_ascii=True, sort_keys=True)
        if (after_attempt is None) != (decision_ref is None):
            raise MailboxError("after_attempt and decision_ref must be supplied together")
        if after_attempt is not None:
            text(after_attempt, "after_attempt")
            text(decision_ref, "decision_ref")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            message = self.get(message_id)
            bound = self.db.execute(
                "SELECT message_id, actor FROM attempts WHERE attempt_id = ?", (attempt_id,)
            ).fetchone()
            if bound is not None and bound[0] != message_id:
                raise MailboxError("attempt identity already belongs to another message")
            if bound is not None and bound[1] != actor_content:
                raise MailboxError("attempt identity already binds a different submitting actor")
            claimed = False
            nondelivery_ref = None
            if bound is None:
                if not message["attempts"]:
                    if after_attempt is not None:
                        raise MailboxError("first attempt cannot refer to an earlier attempt")
                    claimed = True
                else:
                    latest = message["attempts"][-1]
                    observations = latest["observations"]
                    nondelivery = all(
                        attempt["observations"]
                        and attempt["observations"][-1]["kind"] == "not_delivered"
                        for attempt in message["attempts"]
                    )
                    progress = any(
                        attempt[stage]
                        for attempt in message["attempts"]
                        for stage in ("received", "handled", "completed")
                    )
                    if (
                        after_attempt == latest["attempt_id"]
                        and decision_ref is not None
                        and nondelivery
                        and not progress
                    ):
                        claimed = True
                        nondelivery_ref = observations[-1]["evidence_ref"]
            if claimed:
                self.db.execute("""
                    INSERT INTO attempts (
                        message_id, attempt_id, actor, after_attempt, nondelivery_ref, decision_ref
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    message_id, attempt_id, actor_content,
                    after_attempt, nondelivery_ref, decision_ref,
                ))
            result = {"claimed": claimed, "message": self.get(message_id)}
        return result

    def observe(self, message_id, attempt_id, kind, evidence_ref, detail):
        if kind not in KINDS:
            raise MailboxError("unsupported observation kind")
        text(evidence_ref, "evidence_ref")
        if not isinstance(detail, str):
            raise MailboxError("detail must be a string")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            binding = self.db.execute(
                "SELECT message_id FROM attempts WHERE attempt_id = ?", (attempt_id,)
            ).fetchone()
            if binding is None or binding[0] != message_id:
                raise MailboxError("observation does not match a claimed message and attempt")
            self.db.execute(
                "INSERT INTO observations (attempt_id, kind, evidence_ref, detail) VALUES (?, ?, ?, ?)",
                (attempt_id, kind, evidence_ref, detail),
            )
            result = self.get(message_id)
        return result

    def get(self, message_id):
        rows = self.db.execute("""
            SELECT m.content, a.attempt_id, a.actor, a.after_attempt,
                   a.nondelivery_ref, a.decision_ref, o.kind, o.evidence_ref, o.detail
            FROM messages m LEFT JOIN attempts a USING (message_id)
            LEFT JOIN observations o USING (attempt_id)
            WHERE m.message_id = ? ORDER BY a.sequence, o.sequence
        """, (message_id,)).fetchall()
        if not rows:
            raise MailboxError("unknown message identity")
        message = json.loads(rows[0][0])
        attempts = {}
        for row in rows:
            if row[1] is None:
                continue
            if row[1] not in attempts:
                attempts[row[1]] = {
                    "attempt_id": row[1],
                    "actor": json.loads(row[2]),
                    "reconciliation": None if row[3] is None else {
                        "after_attempt": row[3],
                        "nondelivery_ref": row[4],
                        "decision_ref": row[5],
                    },
                    "submission": "unknown",
                    "received": False,
                    "handled": False,
                    "completed": False,
                    "observations": [],
                }
            attempt = attempts[row[1]]
            if row[6] is not None:
                kind = row[6]
                attempt["observations"].append(
                    {"kind": kind, "evidence_ref": row[7], "detail": row[8]}
                )
                if kind in SUBMISSION_KINDS:
                    attempt["submission"] = kind
                elif kind in ("received", "handled", "completed"):
                    attempt[kind] = True
        message["attempts"] = list(attempts.values())
        message["state"] = message["attempts"][-1]["submission"] if attempts else "planned"
        for stage in ("received", "handled", "completed"):
            if any(attempt[stage] for attempt in message["attempts"]):
                message["state"] = stage
        return message

    def pending(self):
        with self.db:
            self.db.execute("BEGIN")
            identities = self.db.execute(
                "SELECT message_id FROM messages ORDER BY message_id"
            ).fetchall()
            messages = [self.get(row[0]) for row in identities]
        return [message for message in messages if message["state"] != "completed"]


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--store", required=True, help="explicit path to the local SQLite store")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="create a new store; refuse an existing path")
    plan = commands.add_parser("plan", help="capture an immutable message JSON object")
    plan.add_argument("--input", required=True, help="UTF-8 JSON file")
    claim = commands.add_parser("claim", help="persist uncertainty before one external submission")
    claim.add_argument("message_id")
    claim.add_argument("attempt_id")
    claim.add_argument("--actor-thread-id", required=True)
    claim.add_argument("--actor-host-id", required=True)
    claim.add_argument("--after-attempt", help="latest attempt with conclusive nondelivery evidence")
    claim.add_argument("--decision-ref", help="owning-task decision for this later attempt")
    observe = commands.add_parser("observe", help="append a supplied observation")
    observe.add_argument("message_id")
    observe.add_argument("attempt_id")
    observe.add_argument("kind", choices=sorted(KINDS))
    observe.add_argument("--evidence-ref", required=True)
    observe.add_argument("--detail-file", required=True, help="UTF-8 text, retained without newline conversion")
    show = commands.add_parser("show")
    show.add_argument("message_id")
    commands.add_parser("pending", help="list every message without a completion observation")
    return result


def main(argv=None):
    arguments = parser().parse_args(argv)
    mailbox = None
    try:
        mailbox = Mailbox(arguments.store, initialize=arguments.command == "init")
        if arguments.command == "init":
            result = {"initialized": True}
        elif arguments.command == "plan":
            message = json.loads(Path(arguments.input).read_bytes().decode("utf-8"))
            result = mailbox.plan(message)
        elif arguments.command == "claim":
            result = mailbox.claim(
                arguments.message_id, arguments.attempt_id,
                {"thread_id": arguments.actor_thread_id, "host_id": arguments.actor_host_id},
                arguments.after_attempt, arguments.decision_ref,
            )
        elif arguments.command == "observe":
            detail = Path(arguments.detail_file).read_bytes().decode("utf-8")
            result = mailbox.observe(
                arguments.message_id, arguments.attempt_id, arguments.kind,
                arguments.evidence_ref, detail,
            )
        elif arguments.command == "show":
            result = mailbox.get(arguments.message_id)
        else:
            result = mailbox.pending()
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0
    except (MailboxError, OSError, sqlite3.Error, UnicodeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=True), file=sys.stderr)
        return 2
    except json.JSONDecodeError as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=True), file=sys.stderr)
        return 2
    finally:
        if mailbox is not None:
            mailbox.close()


if __name__ == "__main__":
    sys.exit(main())
