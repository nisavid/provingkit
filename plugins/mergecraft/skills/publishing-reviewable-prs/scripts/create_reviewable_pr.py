#!/usr/bin/env python3
"""Create a nonce-tagged draft PR and install its canonical body safely."""

from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path
from typing import Any

WRITER_SCRIPTS = (
    Path(__file__).parents[2] / "writing-reviewable-pr-descriptions/scripts"
)
if str(WRITER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WRITER_SCRIPTS))
from change_navigation.review_input import (  # noqa: E402
    ReviewInputError,
    bind_review_input,
)
from change_navigation.sensitive_content import suspected_secret_error  # noqa: E402
from publication_receipts import (  # noqa: E402
    creation_transaction_lock,
    load_receipts,
    prepare_receipt_ledger,
    prepare_receipt_store,
    receipt_ledger_lock,
    record_verified_publication,
    resolve_receipt_root,
    verified_transition,
)
from publication_support import (  # noqa: E402
    BodySnapshotError,
    admit_review_input as _admit_review_input,
    expected_identity as _expected_identity,
    reread_relationship_diagnostic,
)
from publication_support import (  # noqa: E402
    temporary_body as _write_temporary_body,
)
from publication_support import (  # noqa: E402
    validate_pr_content as _validate,
)
from publication_support import verified_publication_acknowledgement  # noqa: E402
from required_review import (  # noqa: E402
    build_candidate as _build_candidate,
)
from required_review import (  # noqa: E402
    validate_create_rendering,
    validate_review_input_binding,
)
from required_review import (  # noqa: E402
    validate_required_review as _validate_required_review,
)
from reviewable_pr_state import (  # noqa: E402
    CommandRejectedError,
    PR_URL_RE,
    ExpectedIdentity,
    MutationAmbiguousError,
    MutationPreparationError,
    PublicationError,
    github_repository,
    head_base_matches,
    mutation_failure_diagnostic,
    parse_positive_decimal_identifier,
    parse_selected_specialists,
    read_failure_diagnostic,
    state_matches,
    validate_identity_inputs,
    validate_selected_specialists,
)
from reviewable_pr_state import (  # noqa: E402
    open_prs as _open_prs,
)
from reviewable_pr_state import (  # noqa: E402
    run_mutation as _run_mutation,
)
from reviewable_pr_state import (  # noqa: E402
    stored_pr as _stored_pr,
)

PR_NUMBER_TOKEN = "__PUBLISHING_REVIEWABLE_PRS_PR_NUMBER__"
VALIDATION_PR_NUMBER = 2_147_483_647


def _transport_body(nonce: str) -> str:
    return (
        "<!-- publishing-reviewable-prs: canonical body pending GitHub PR identity; "
        f"transaction={nonce} -->\n"
    )


def _new_nonce() -> str:
    return secrets.token_hex(16)


def _body_template(path: Path) -> tuple[str, bytes]:
    if not path.is_absolute():
        raise PublicationError("body template path must be absolute")
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise PublicationError(
            "cannot read body template; check the local path and read permissions"
        ) from error
    try:
        template = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PublicationError("body template must be valid UTF-8") from error
    if suspected_secret_error(template) is not None:
        raise PublicationError(
            "PR body contains a suspected credential or secret; publication is blocked"
        )
    if PR_NUMBER_TOKEN not in template:
        raise PublicationError(f"body template must contain {PR_NUMBER_TOKEN}")
    return template, raw


def _reject_secret_text(*values: str) -> None:
    if any(suspected_secret_error(value) is not None for value in values):
        raise PublicationError(
            "PR publication text contains a suspected credential or secret; "
            "publication is blocked"
        )


def _review_input(
    path: Path,
    *,
    repository: str,
    base: str,
    base_oid: str,
    head: str,
    head_oid: str,
    head_owner: str,
    head_repository: str,
    title: str,
    body: str,
    pr_number: int,
    template_body: str | None = None,
) -> tuple[int, str]:
    manifest = _admit_review_input(path)
    try:
        bind_review_input(
            manifest,
            repository=repository,
            pr_number=pr_number,
            base=base,
            base_oid=base_oid,
            head=head,
            head_oid=head_oid,
            head_owner=head_owner,
            head_repository=head_repository,
            title=title,
            body=body,
            template_body=template_body,
            git_repository=Path.cwd(),
        )
        return int(manifest.raw["version"]), manifest.content_sha256
    except ReviewInputError as error:
        raise PublicationError(
            "review input could not be admitted; check the local file and regenerate "
            "it for this exact publication candidate"
        ) from error


def _matching_head_prs(
    *,
    repository: str,
    base: str,
    head: str,
    head_owner: str,
    head_repository: str,
) -> list[dict[str, Any]]:
    return [
        stored
        for stored in _open_prs(repository, base, head)
        if head_base_matches(
            stored,
            base=base,
            head=head,
            head_owner=head_owner,
            head_repository=head_repository,
        )
    ]


def _recover_created(
    *,
    repository: str,
    base: str,
    base_oid: str,
    head: str,
    head_oid: str,
    head_owner: str,
    head_repository: str,
    title: str,
    transport_body: str,
) -> tuple[tuple[int, str] | None, str]:
    matches: list[dict[str, Any]] = []
    candidates = _matching_head_prs(
        repository=repository,
        base=base,
        head=head,
        head_owner=head_owner,
        head_repository=head_repository,
    )
    for stored in candidates:
        number = stored.get("number")
        if type(number) is not int or number <= 0:
            continue
        expected = _expected_identity(
            repository=repository,
            pr_number=number,
            base=base,
            base_oid=base_oid,
            head=head,
            head_oid=head_oid,
            head_owner=head_owner,
            head_repository=head_repository,
        )
        if state_matches(
            stored,
            expected,
            title=title,
            body=transport_body,
            is_draft=True,
        ):
            matches.append(stored)
    if len(matches) == 1:
        return (
            (matches[0]["number"], matches[0]["url"]),
            "nonce recovery observed one exact nonce-tagged draft",
        )
    if len(matches) > 1:
        return None, "nonce recovery observed multiple exact nonce-tagged drafts"
    if candidates:
        return (
            None,
            "nonce recovery observed open PR state, but none matched the exact "
            "nonce, identity, title, body, and draft state",
        )
    return None, "nonce recovery observed no open PR for the exact head/base"


def _initial_create_process_fact(
    error: PublicationError, *, zero_exit_without_url: bool
) -> str:
    if zero_exit_without_url:
        return "initial create command exited zero without the expected PR URL"
    if isinstance(error, MutationPreparationError):
        return (
            "initial create command could not be prepared locally; no process "
            "started and no target mutation ran"
        )
    if isinstance(error, CommandRejectedError):
        return "initial create command returned nonzero"
    if isinstance(error, MutationAmbiguousError):
        if error.malformed_output:
            return "initial create command exited zero with malformed output"
        if error.timeout_seconds is not None:
            return "initial create command timed out after a possible mutation"
        if error.process_outcome_unknown:
            return (
                "initial create command failed during process launch or "
                "communication; whether the process started is unknown and mutation "
                "outcome is unknown"
            )
        return "initial create command ended with an unverified mutation outcome"
    return "initial create command failed"


def _create_output_identity(
    output: str, repository: str
) -> tuple[int, str] | None:
    match = PR_URL_RE.search(output)
    if match is None or match.group("repository") != repository:
        return None
    try:
        pr_number = parse_positive_decimal_identifier(match.group("pr"))
    except ValueError as error:
        raise PublicationError("gh pr create returned no expected PR URL") from error
    return pr_number, f"https://github.com/{repository}/pull/{pr_number}"


def _create(
    *,
    repository: str,
    base: str,
    base_oid: str,
    head: str,
    head_oid: str,
    head_owner: str,
    head_repository: str,
    title: str,
    nonce: str,
) -> tuple[int, str]:
    existing = _matching_head_prs(
        repository=repository,
        base=base,
        head=head,
        head_owner=head_owner,
        head_repository=head_repository,
    )
    if existing:
        raise PublicationError("an open PR already exists for this head/base")

    transport_body = _transport_body(nonce)
    create_error: PublicationError | None = None
    snapshot_error: BodySnapshotError | None = None
    result = None
    try:
        with _write_temporary_body(transport_body) as body_file:
            result = _run_mutation(
                [
                    "gh",
                    "-R",
                    github_repository(repository),
                    "pr",
                    "create",
                    "--base",
                    base,
                    "--head",
                    head,
                    "--title",
                    title,
                    "--body-file",
                    body_file.name,
                    "--draft",
                ]
            )
            body_file.mark_mutation_exited_zero()
    except BodySnapshotError as error:
        if not error.after_zero_exit:
            raise
        snapshot_error = error
    except PublicationError as error:
        create_error = error

    malformed_success = result is not None and snapshot_error is None
    if result is not None and snapshot_error is None:
        try:
            identity = _create_output_identity(result.stdout, repository)
        except PublicationError as error:
            create_error = error
        else:
            if identity is not None:
                return identity
            create_error = PublicationError("gh pr create returned no expected PR URL")

    try:
        recovered, recovery_fact = _recover_created(
            repository=repository,
            base=base,
            base_oid=base_oid,
            head=head,
            head_oid=head_oid,
            head_owner=head_owner,
            head_repository=head_repository,
            title=title,
            transport_body=transport_body,
        )
    except PublicationError as reread_error:
        if snapshot_error is not None:
            failure = (
                "initial create command exited zero, but private body snapshot "
                "cleanup failed"
            )
            diagnostic = ""
        else:
            if create_error is None:
                raise AssertionError(
                    "initial create failure has no retained process error"
                ) from reread_error
            failure = _initial_create_process_fact(
                create_error, zero_exit_without_url=malformed_success
            )
            diagnostic = (
                ""
                if malformed_success
                else "; " + mutation_failure_diagnostic(create_error)
            )
        original_error = snapshot_error or create_error
        error_type = (
            MutationAmbiguousError
            if isinstance(create_error, MutationAmbiguousError)
            else PublicationError
        )
        combined = error_type(
            f"{failure}{diagnostic}; nonce recovery was unavailable, so no exact "
            "nonce-tagged draft could be established; "
            f"{read_failure_diagnostic(reread_error)}; no additional mutation was "
            "attempted; canonical provenance was not minted and no canonical receipt "
            "was written; no automatic retry or rollback was attempted"
        )
        combined.reread_error = reread_error
        raise combined from original_error
    if recovered is not None:
        if snapshot_error is not None:
            raise PublicationError(
                "initial create command exited zero and one exact nonce-tagged draft "
                "was found, but private body snapshot cleanup failed; no additional "
                "mutation was attempted; canonical provenance was not minted and no "
                "canonical receipt was written; no automatic retry or rollback was "
                "attempted; independently inspect the draft"
            ) from snapshot_error
        return recovered
    if snapshot_error is not None:
        raise PublicationError(
            "initial create command exited zero, but private body snapshot cleanup "
            f"failed; {recovery_fact}; no additional mutation was attempted; canonical "
            "provenance was not minted and no canonical receipt was written; no "
            "automatic retry or rollback was attempted; independently inspect the draft"
        ) from snapshot_error
    if create_error is None:
        raise AssertionError("initial create failure has no retained process error")
    process_fact = _initial_create_process_fact(
        create_error, zero_exit_without_url=malformed_success
    )
    diagnostic = (
        "" if malformed_success else f"; {mutation_failure_diagnostic(create_error)}"
    )
    raise PublicationError(
        f"{process_fact}{diagnostic}; {recovery_fact}; canonical provenance was not "
        "minted and no canonical receipt was written; no automatic retry or rollback "
        "was attempted"
    ) from create_error


def _install_canonical_draft(
    *,
    expected: ExpectedIdentity,
    title: str,
    transport_body: str,
    body: str,
    before: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not state_matches(
        before,
        expected,
        title=title,
        body=transport_body,
        is_draft=True,
    ):
        raise PublicationError(
            "canonical body was not written because the created PR no longer has "
            "the exact nonce-tagged transport state"
        )

    command_error: PublicationError | None = None
    snapshot_error: BodySnapshotError | None = None
    try:
        with _write_temporary_body(body) as body_file:
            _run_mutation(
                [
                    "gh",
                    "-R",
                    github_repository(expected.repository),
                    "pr",
                    "edit",
                    str(expected.pr_number),
                    "--title",
                    title,
                    "--body-file",
                    body_file.name,
                ]
            )
            body_file.mark_mutation_exited_zero()
    except BodySnapshotError as error:
        if not error.after_zero_exit:
            raise
        snapshot_error = error
    except PublicationError as error:
        command_error = error

    try:
        after = _stored_pr(expected.repository, expected.pr_number)
    except PublicationError as reread_error:
        if snapshot_error is not None:
            combined = PublicationError(
                "canonical edit command exited zero, but private body snapshot "
                "cleanup and post-mutation verification failed; the final reread "
                "state was unavailable; canonical provenance was not minted and no "
                "canonical receipt was written; no automatic retry or rollback was "
                "attempted; "
                f"{read_failure_diagnostic(reread_error)}"
            )
            combined.reread_error = reread_error
            raise combined from snapshot_error
        if command_error is None:
            combined = PublicationError(
                "canonical edit command exited zero, but post-mutation "
                "verification failed; the final reread state was unavailable; "
                "canonical provenance was not minted and no canonical receipt was "
                "written; no automatic retry or rollback was attempted; "
                f"{read_failure_diagnostic(reread_error)}"
            )
            combined.reread_error = reread_error
            raise combined from reread_error
        diagnostic = (
            "canonical edit command was ambiguous"
            if isinstance(command_error, MutationAmbiguousError)
            else "canonical edit command failed"
        )
        error_type = (
            MutationAmbiguousError
            if isinstance(command_error, MutationAmbiguousError)
            else PublicationError
        )
        combined = error_type(
            f"{diagnostic}; the final reread state was unavailable; canonical "
            "provenance was not minted and no canonical receipt was written; no "
            "automatic retry or rollback was attempted; "
            f"{mutation_failure_diagnostic(command_error)}; "
            f"{read_failure_diagnostic(reread_error)}"
        )
        combined.reread_error = reread_error
        raise combined from command_error
    relationship = reread_relationship_diagnostic(
        matches_intended=state_matches(
            after, expected, title=title, body=body, is_draft=True
        ),
        matches_preimage=state_matches(
            after, expected, title=title, body=transport_body, is_draft=True
        ),
    )
    if snapshot_error is not None:
        raise PublicationError(
            "canonical edit command exited zero, but private body snapshot cleanup "
            f"failed; {relationship}; that observed relationship does not establish "
            "a canonical transition, so canonical provenance was not minted and no "
            "canonical receipt was written; no automatic retry or rollback was "
            "attempted; independently inspect the PR and do not retry"
        ) from snapshot_error
    if command_error is not None:
        diagnostic = (
            "canonical edit command was ambiguous"
            if isinstance(command_error, MutationAmbiguousError)
            else "canonical edit command failed"
        )
        error_type = (
            MutationAmbiguousError
            if isinstance(command_error, MutationAmbiguousError)
            else PublicationError
        )
        raise error_type(
            f"{diagnostic}; {relationship}; that observed relationship does not "
            "establish a canonical transition, so canonical provenance was not minted "
            "and no canonical receipt was written; no automatic retry or rollback was "
            "attempted; "
            f"{mutation_failure_diagnostic(command_error)}"
        ) from command_error
    if state_matches(after, expected, title=title, body=body, is_draft=True):
        return before, after
    if state_matches(
        after,
        expected,
        title=title,
        body=transport_body,
        is_draft=True,
    ):
        raise PublicationError(
            "canonical edit command exited zero, but the final reread matched the "
            "pre-mutation state; an unchanged preimage does not establish whether "
            "the command stored the intended state before another change, so "
            "causality remains unresolved; canonical provenance was not minted "
            "and no canonical receipt was written; no automatic retry or rollback "
            "was attempted"
        )
    raise PublicationError(
        "canonical edit command exited zero, but the final reread differed from "
        "both the pre-mutation and intended states; causality remains unresolved; "
        "canonical provenance was not minted and no canonical receipt was written; "
        "no automatic retry or rollback was attempted; the observed state requires "
        "operator inspection"
    )


def publish(
    *,
    repository: str,
    base: str,
    base_oid: str,
    head: str,
    head_oid: str,
    head_owner: str,
    head_repository: str,
    title: str,
    template_path: Path,
    review_input_path: Path,
    review_mode: str,
    review_bundle_root: Path | None,
    selected_specialists: list[str],
    receipt_directory: Path | None = None,
) -> dict[str, Any]:
    selected_specialists = validate_selected_specialists(selected_specialists)
    validate_identity_inputs(
        repository=repository,
        pr_number=None,
        base=base,
        base_oid=base_oid,
        head=head,
        head_oid=head_oid,
        head_owner=head_owner,
        head_repository=head_repository,
    )
    if not title.strip():
        raise PublicationError("title must be non-empty")

    template, template_raw = _body_template(template_path)
    _reject_secret_text(title, template)
    validation_body = template.replace(PR_NUMBER_TOKEN, str(VALIDATION_PR_NUMBER))
    review_input_schema_version, review_input_sha256 = _review_input(
        review_input_path,
        repository=repository,
        base=base,
        base_oid=base_oid,
        head=head,
        head_oid=head_oid,
        head_owner=head_owner,
        head_repository=head_repository,
        title=title,
        body=validation_body,
        pr_number=VALIDATION_PR_NUMBER,
        template_body=template,
    )
    _validate(
        validation_body,
        repository,
        VALIDATION_PR_NUMBER,
        title,
        review_input_path,
        template_path,
    )
    candidate = _build_candidate(
        operation="create",
        repository=repository,
        pr_number=PR_NUMBER_TOKEN,
        base=base,
        base_oid=base_oid,
        head=head,
        head_oid=head_oid,
        head_owner=head_owner,
        head_repository=head_repository,
        title=title,
        body_source_kind="template",
        body_source_raw=template_raw,
        published_body=template,
        review_input_path=review_input_path,
        review_mode=review_mode,
        selected_specialists=selected_specialists,
    )
    validate_review_input_binding(
        candidate,
        review_input_schema_version,
        review_input_sha256,
        review_input_path,
    )
    receipt_root = prepare_receipt_store(receipt_directory)
    with creation_transaction_lock(
        receipt_root,
        repository=repository,
        base=base,
        head=head,
        head_owner=head_owner,
        head_repository=head_repository,
    ):
        initial_review = _validate_required_review(
            review_mode=review_mode,
            review_bundle_root=review_bundle_root,
            candidate=candidate,
        )
        nonce = _new_nonce()
        transport_body = _transport_body(nonce)
        pr_number, url = _create(
            repository=repository,
            base=base,
            base_oid=base_oid,
            head=head,
            head_oid=head_oid,
            head_owner=head_owner,
            head_repository=head_repository,
            title=title,
            nonce=nonce,
        )
        expected = _expected_identity(
            repository=repository,
            pr_number=pr_number,
            base=base,
            base_oid=base_oid,
            head=head,
            head_oid=head_oid,
            head_owner=head_owner,
            head_repository=head_repository,
        )
        prepare_receipt_ledger(receipt_root, expected)
        body = template.replace(PR_NUMBER_TOKEN, str(pr_number))
        try:
            with receipt_ledger_lock(receipt_root, expected) as lease:
                created = _stored_pr(repository, pr_number)
                if not state_matches(
                    created,
                    expected,
                    title=title,
                    body=transport_body,
                    is_draft=True,
                ):
                    raise PublicationError(
                        "created PR does not have the exact nonce-tagged "
                        "transport state"
                    )
                review_input_schema_version, review_input_sha256 = _review_input(
                    review_input_path,
                    repository=repository,
                    base=base,
                    base_oid=base_oid,
                    head=head,
                    head_oid=head_oid,
                    head_owner=head_owner,
                    head_repository=head_repository,
                    title=title,
                    body=body,
                    pr_number=pr_number,
                    template_body=template,
                )
                _validate(
                    body,
                    repository,
                    pr_number,
                    title,
                    review_input_path,
                    template_path,
                )
                validate_review_input_binding(
                    candidate,
                    review_input_schema_version,
                    review_input_sha256,
                    review_input_path,
                )
                validate_create_rendering(
                    candidate=candidate,
                    template=template,
                    rendered_body=body,
                    pr_number=pr_number,
                )
                review = _validate_required_review(
                    review_mode=review_mode,
                    review_bundle_root=review_bundle_root,
                    candidate=candidate,
                    expected_observation=initial_review.observation,
                )
                final_preflight = _stored_pr(repository, pr_number)
                if not state_matches(
                    final_preflight,
                    expected,
                    title=title,
                    body=transport_body,
                    is_draft=True,
                ):
                    raise PublicationError(
                        "canonical body was not written because the created PR no "
                        "longer has the exact nonce-tagged transport state after review"
                    )
                before, stored = _install_canonical_draft(
                    expected=expected,
                    title=title,
                    transport_body=transport_body,
                    body=body,
                    before=final_preflight,
                )
                transition = verified_transition(
                    expected=expected,
                    operation="create",
                    preimage=before,
                    final_reread=stored,
                    review_input_schema_version=review_input_schema_version,
                    review_input_sha256=review_input_sha256,
                    review=review,
                    candidate=candidate,
                )
                record_verified_publication(
                    root=receipt_root, transition=transition, lease=lease
                )
                return stored
        except MutationAmbiguousError as error:
            raise MutationAmbiguousError(
                f"PR {url} requires inspection; no automatic retry or rollback was "
                f"attempted: {error}"
            ) from error
        except PublicationError as error:
            raise PublicationError(
                f"PR {url} requires inspection; no automatic retry or rollback was "
                f"attempted: {error}"
            ) from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--base-oid", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--head-oid", required=True)
    parser.add_argument("--head-owner", required=True)
    parser.add_argument("--head-repository", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-template", required=True, type=Path)
    parser.add_argument("--review-input", required=True, type=Path)
    parser.add_argument(
        "--review-mode", choices=("required", "not-required"), required=True
    )
    parser.add_argument("--review-bundle", type=Path)
    parser.add_argument(
        "--selected-specialists",
        required=True,
        help="sorted unique specialist names as a JSON array; use [] for none",
    )
    args = parser.parse_args()
    try:
        selected_specialists = parse_selected_specialists(args.selected_specialists)
        stored = publish(
            repository=args.repository,
            base=args.base,
            base_oid=args.base_oid,
            head=args.head,
            head_oid=args.head_oid,
            head_owner=args.head_owner,
            head_repository=args.head_repository,
            title=args.title,
            template_path=args.body_template,
            review_input_path=args.review_input,
            review_mode=args.review_mode,
            review_bundle_root=args.review_bundle,
            selected_specialists=selected_specialists,
            receipt_directory=None,
        )
        expected = _expected_identity(
            repository=args.repository,
            pr_number=int(stored["number"]),
            base=args.base,
            base_oid=args.base_oid,
            head=args.head,
            head_oid=args.head_oid,
            head_owner=args.head_owner,
            head_repository=args.head_repository,
        )
        acknowledgement = verified_publication_acknowledgement(
            load_latest=lambda: load_receipts(resolve_receipt_root(), expected),
            repository=args.repository,
            pr_number=stored["number"],
            url=stored["url"],
            is_draft=stored["isDraft"],
        )
    except PublicationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(acknowledgement)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
