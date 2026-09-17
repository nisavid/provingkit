#!/usr/bin/env python3
"""Post one authorized top-level PR comment and verify its exact receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PUBLISHER_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "publishing-reviewable-prs" / "scripts"
)
sys.path.insert(0, str(PUBLISHER_SCRIPTS))

from reviewable_pr_state import (  # noqa: E402
    CommandRejectedError,
    ExpectedIdentity,
    GITHUB_HOST,
    MutationAmbiguousError,
    MutationPreparationError,
    PublicationError,
    StateReadError,
    classified_read_failure,
    identity_matches,
    run_mutation as _run_mutation,
    run_read as _run_read,
    stored_pr as _stored_pr,
    strict_json,
    validate_identity_inputs,
)

DISPLAY_SAFE_LOGIN_RE = re.compile(r"[A-Za-z0-9_-]+(?:\[bot\])?")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _display_safe_login(value: Any) -> str:
    if (
        type(value) is not str
        or DISPLAY_SAFE_LOGIN_RE.fullmatch(value) is None
    ):
        raise PublicationError(
            "actor identity is not a display-safe GitHub.com actor login"
        )
    return value


def _comment_receipt(
    value: Any, expected: ExpectedIdentity, body: str, expected_login: str
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PublicationError("comment receipt is not an object")
    identifier = value.get("id")
    url = value.get("html_url")
    user = value.get("user")
    created_at = value.get("created_at")
    safe_expected_login = _display_safe_login(expected_login)
    if not isinstance(user, dict):
        raise PublicationError("comment receipt does not match exact PR/body authority")
    observed_login = _display_safe_login(user.get("login"))
    if type(identifier) is not int or identifier <= 0:
        raise PublicationError("comment receipt does not match exact PR/body authority")
    expected_url = f"{expected.url}#issuecomment-{identifier}"
    if (
        url != expected_url
        or value.get("body") != body
        or observed_login != safe_expected_login
        or not isinstance(created_at, str)
    ):
        raise PublicationError("comment receipt does not match exact PR/body authority")
    try:
        parsed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise PublicationError("comment receipt has an invalid created_at") from error
    if parsed.tzinfo is None:
        raise PublicationError("comment receipt has an invalid created_at")
    return {
        "id": identifier,
        "html_url": expected_url,
        "body_sha256": _digest(body),
        "user": {"login": safe_expected_login},
        "created_at": created_at,
    }


def _zero_exit_verification_error(
    classification: str, error: PublicationError
) -> PublicationError:
    failure = PublicationError(
        "comment stage: POST exited zero, but "
        f"{classification}; comment state is not trustworthy and canonical success "
        "was not acknowledged; independently inspect the comment and do not retry"
    )
    failure.verification_error = error
    return failure


def _nonzero_post_error(error: CommandRejectedError) -> PublicationError:
    failure = PublicationError(
        "comment stage: POST exited nonzero "
        f"(return code {error.return_code}); remote outcome is unknown and canonical "
        "success was not acknowledged; independently inspect the comment using "
        "existing valid read authority and do not retry"
    )
    failure.mutation_error = error
    return failure


def _post_process_error(error: PublicationError) -> PublicationError:
    if isinstance(error, CommandRejectedError):
        return _nonzero_post_error(error)
    if isinstance(error, MutationAmbiguousError) and error.malformed_output:
        failure: PublicationError = MutationAmbiguousError(
            "comment stage: POST exited zero, but successful output was not strict "
            "UTF-8; remote outcome is unknown and canonical success was not "
            "acknowledged; independently inspect the comment and do not retry; no "
            "automatic retry was attempted",
            malformed_output=True,
        )
    elif isinstance(error, MutationAmbiguousError) and error.timeout_seconds is not None:
        failure = MutationAmbiguousError(
            "comment stage: POST timed out after "
            f"{error.timeout_seconds} seconds; remote outcome is unknown and canonical "
            "success was not acknowledged; independently inspect the comment and do "
            "not retry; no automatic retry was attempted",
            timeout_seconds=error.timeout_seconds,
        )
    elif isinstance(error, MutationAmbiguousError) and error.process_outcome_unknown:
        failure = MutationAmbiguousError(
            "comment stage: POST failed during process launch or communication; "
            "whether the POST process started is unknown and the remote outcome "
            "unknown; canonical success was not acknowledged; independently inspect "
            "the comment and do not retry; no automatic retry was attempted",
            process_outcome_unknown=True,
        )
    elif isinstance(error, MutationAmbiguousError):
        failure = MutationAmbiguousError(
            "comment stage: POST timeout or other ambiguous failure left the remote "
            "outcome unknown and canonical success was not acknowledged; independently "
            "inspect the comment and do not retry; no automatic retry was attempted"
        )
    elif isinstance(error, MutationPreparationError):
        failure = PublicationError(
            "comment stage: POST could not be prepared locally; no target mutation "
            "ran and canonical success was not acknowledged; command inputs and "
            "preparation details were withheld because they may contain sensitive "
            "data; correct the local command inputs before any separately authorized "
            "attempt; no automatic retry was attempted"
        )
    else:
        failure = PublicationError(
            "comment stage: POST failed for an unclassified reason; remote outcome is "
            "unknown and canonical success was not acknowledged; independently inspect "
            "the comment and do not retry; no automatic retry was attempted"
        )
    failure.mutation_error = error
    return failure


def _active_login() -> str:
    result = _run_read(
        ["gh", "api", "--hostname", GITHUB_HOST, "--method", "GET", "user"]
    )
    value = strict_json(result.stdout, "authenticated login response")
    login = value.get("login") if isinstance(value, dict) else None
    return _display_safe_login(login)


def post_comment(
    *,
    expected: ExpectedIdentity,
    expected_authenticated_login: str,
    body: str,
    body_sha256: str,
) -> dict[str, Any]:
    if not body:
        raise PublicationError("comment body must be non-empty")
    if _digest(body) != body_sha256:
        raise PublicationError("comment body SHA-256 does not match supplied bytes")
    safe_expected_login = _display_safe_login(expected_authenticated_login)
    if _display_safe_login(_active_login()) != safe_expected_login:
        raise PublicationError("active authenticated login does not match authority")
    before = _stored_pr(expected.repository, expected.pr_number)
    if not identity_matches(before, expected):
        raise PublicationError("PR identity or pushed head changed before comment")
    payload = json.dumps(
        {"body": body},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    try:
        result = _run_mutation(
            [
                "gh",
                "api",
                "--hostname",
                GITHUB_HOST,
                "--method",
                "POST",
                f"repos/{expected.repository}/issues/{expected.pr_number}/comments",
                "--input",
                "-",
            ],
            input_text=payload,
        )
    except PublicationError as error:
        raise _post_process_error(error) from error
    try:
        created = _comment_receipt(
            strict_json(result.stdout, "comment creation response"),
            expected,
            body,
            safe_expected_login,
        )
    except (PublicationError, StateReadError) as error:
        raise _zero_exit_verification_error(
            "creation response validation failed", error
        ) from error
    identifier = int(created["id"])
    try:
        reread = _run_read(
            [
                "gh",
                "api",
                "--hostname",
                GITHUB_HOST,
                "--method",
                "GET",
                f"repos/{expected.repository}/issues/comments/{identifier}",
            ]
        )
    except PublicationError as error:
        raise _zero_exit_verification_error(
            classified_read_failure(error, stage="comment reread"), error
        ) from error
    try:
        receipt = _comment_receipt(
            strict_json(reread.stdout, "comment reread response"),
            expected,
            body,
            safe_expected_login,
        )
    except (PublicationError, StateReadError) as error:
        raise _zero_exit_verification_error(
            "comment reread response validation failed", error
        ) from error
    if any(receipt[key] != created[key] for key in ("id", "html_url", "created_at")):
        error = PublicationError("comment reread identity differs from creation receipt")
        raise _zero_exit_verification_error(
            "comment identity verification failed", error
        ) from error
    try:
        after = _stored_pr(expected.repository, expected.pr_number)
    except PublicationError as error:
        raise _zero_exit_verification_error(
            classified_read_failure(error, stage="PR identity reread"), error
        ) from error
    if not identity_matches(after, expected):
        error = PublicationError("PR identity or pushed head changed after comment")
        raise _zero_exit_verification_error(
            "PR identity verification failed", error
        ) from error
    return receipt


def _read_body(path: Path) -> str:
    if not path.is_absolute():
        raise PublicationError("comment body path must be absolute")
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise PublicationError(
            "cannot read comment body; check the local path and read permissions"
        ) from error
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PublicationError("comment body must be valid UTF-8") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--base", required=True)
    parser.add_argument("--base-oid", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--head-oid", required=True)
    parser.add_argument("--head-owner", required=True)
    parser.add_argument("--head-repository", required=True)
    parser.add_argument("--body-file", required=True, type=Path)
    parser.add_argument("--body-sha256", required=True)
    parser.add_argument("--expected-authenticated-login", required=True)
    args = parser.parse_args()
    try:
        validate_identity_inputs(
            repository=args.repository,
            pr_number=args.pr,
            base=args.base,
            base_oid=args.base_oid,
            head=args.head,
            head_oid=args.head_oid,
            head_owner=args.head_owner,
            head_repository=args.head_repository,
        )
        expected = ExpectedIdentity(
            repository=args.repository,
            pr_number=args.pr,
            base=args.base,
            base_oid=args.base_oid,
            head=args.head,
            head_oid=args.head_oid,
            head_owner=args.head_owner,
            head_repository=args.head_repository,
        )
        receipt = post_comment(
            expected=expected,
            expected_authenticated_login=args.expected_authenticated_login,
            body=_read_body(args.body_file),
            body_sha256=args.body_sha256,
        )
    except (PublicationError, MutationAmbiguousError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
