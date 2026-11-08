"""Pure versioned peer-message serialization; an envelope grants no authority."""
import json

from native_codex_mailbox import MailboxError, text, validate_message


def serialize_peer_message(message, actor):
    message = validate_message(message)
    if not isinstance(actor, dict) or actor.keys() != {"thread_id", "host_id"}:
        raise MailboxError("actor requires exactly thread_id and host_id")
    for key in ("thread_id", "host_id"):
        text(actor[key], f"actor.{key}")
    envelope = {
        "schema": "provingkit-peer-message-v1",
        "message_id": message["message_id"],
        "correlation_id": message.get("correlation_id", message["message_id"]),
        "sender": message["sender"],
        "actor": actor,
        "recipient": message["recipient"],
        "owner": message["owner"],
        "authority_ref": message["authority_ref"],
        "holds": message["holds"],
        "payload": message["payload"],
    }
    return "Peer message (no new operator authority).\n" + json.dumps(
        envelope, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
    )
