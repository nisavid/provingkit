"""Shared internal support for reviewable-PR publication commands."""

from __future__ import annotations

import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, BinaryIO, Callable, Iterator

from reviewable_pr_state import (
    CommandReadError,
    ExpectedIdentity,
    PublicationError,
    run_read,
    validate_identity_inputs,
)

WRITER_SCRIPTS = (
    Path(__file__).parents[2] / "writing-reviewable-pr-descriptions/scripts"
)
if str(WRITER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WRITER_SCRIPTS))
from change_navigation.review_input import (  # noqa: E402
    ReviewInput,
    ReviewInputError,
    load_review_input,
)

VALIDATOR = WRITER_SCRIPTS / "validate_change_navigation.py"
VALIDATOR_GUIDANCE = (
    "validator output was withheld because it may contain sensitive data; check "
    "candidate structure, review-input binding, local runtime availability, "
    "trusted executable ancestry, and temporary-directory availability"
)


class BodySnapshotError(PublicationError):
    """A private body snapshot failed at a value-free local boundary."""

    def __init__(self, message: str, *, after_zero_exit: bool = False) -> None:
        self.after_zero_exit = after_zero_exit
        super().__init__(message)


class PrivateBodySnapshot:
    """Expose only the private file name and mutation-use marker to callers."""

    def __init__(self, temporary: BinaryIO) -> None:
        self._temporary = temporary
        self.name = temporary.name
        self.mutation_exited_zero = False

    def mark_mutation_exited_zero(self) -> None:
        self.mutation_exited_zero = True


def admit_review_input(path: Path) -> ReviewInput:
    """Admit bounded local review-input bytes with a value-free classification."""

    try:
        return load_review_input(path)
    except ReviewInputError as error:
        raise PublicationError(
            "review input could not be admitted; check the local file and regenerate "
            "it for this exact publication candidate"
        ) from error


def reread_relationship_diagnostic(
    *, matches_intended: bool, matches_preimage: bool
) -> str:
    """Describe one admitted reread using only caller-classified state fields."""

    if matches_intended:
        return (
            "the exact intended state was observed because the final reread matched "
            "the exact intended state"
        )
    if matches_preimage:
        return "the final reread matched the pre-mutation state"
    return "the final reread differed from both the pre-mutation and intended states"


def verified_publication_acknowledgement(
    *,
    load_latest: Callable[[], list[Any]],
    repository: str,
    pr_number: int,
    url: str,
    is_draft: bool,
) -> str:
    """Render a canonical CLI acknowledgement or fail safe after publication."""

    try:
        receipts = load_latest()
        if type(receipts) is not list or not receipts:
            raise ValueError("canonical receipt ledger is empty")
        summary = receipts[-1].summary("verified")
        if type(summary) is not dict:
            raise TypeError("canonical receipt summary is not an object")
        if (
            type(repository) is not str
            or type(pr_number) is not int
            or pr_number <= 0
            or type(url) is not str
            or type(is_draft) is not bool
        ):
            raise TypeError("publication acknowledgement fields are invalid")
        repository.encode("utf-8")
        url.encode("utf-8")
        return json.dumps(
            {
                "repository": repository,
                "pr": pr_number,
                "url": url,
                "is_draft": is_draft,
                **summary,
            },
            sort_keys=True,
            allow_nan=False,
        )
    except Exception as error:
        raise PublicationError(
            "publication may have completed, but its verified receipt acknowledgement "
            "is unavailable; independently audit exact state and do not retry"
        ) from error


def validate_pr_content(
    body: str,
    repository: str,
    pr_number: int,
    title: str,
    review_input_path: Path,
    template_path: Path | None = None,
) -> None:
    """Validate one complete candidate title/body at the canonical CLI seam."""

    if not VALIDATOR.is_file():
        raise PublicationError(
            "candidate validation is unavailable; validator executable is missing; "
            f"{VALIDATOR_GUIDANCE}"
        )
    arguments = [
        sys.executable,
        str(VALIDATOR),
        "/dev/stdin",
        "--repository",
        repository,
        "--pr",
        str(pr_number),
        "--title",
        title,
        "--review-input",
        str(review_input_path),
    ]
    if template_path is not None:
        arguments.extend(["--template-body", str(template_path)])
    try:
        run_read(arguments, input_text=body)
    except CommandReadError as error:
        if error.local_preparation_failed:
            classification = (
                "candidate validation could not be prepared locally; no validation "
                "command started"
            )
        elif error.process_outcome_unknown:
            classification = (
                "candidate validation failed during process launch or communication; "
                "whether the validation process started is unknown"
            )
        elif error.timeout_seconds is not None:
            classification = (
                "candidate validation timed out after "
                f"{error.timeout_seconds} seconds"
            )
        elif error.return_code is not None:
            classification = (
                f"candidate validation failed (return code {error.return_code})"
            )
        elif error.malformed_output:
            classification = (
                "candidate validation returned malformed successful output; "
                "strict UTF-8 was required"
            )
        else:
            classification = "candidate validation failed for an unclassified reason"
        cause = (
            error.__cause__
            if (
                error.local_preparation_failed
                or error.process_outcome_unknown
            )
            else error
        )
        raise PublicationError(
            f"{classification}; {VALIDATOR_GUIDANCE}"
        ) from cause
    except OSError as error:
        raise PublicationError(
            "candidate validation failed during process launch or communication; "
            "whether the validation process started is unknown; "
            f"{VALIDATOR_GUIDANCE}"
        ) from error


@contextmanager
def temporary_body(body: str) -> Iterator[PrivateBodySnapshot]:
    """Yield a flushed private body file with value-free lifecycle failures."""

    temporary: BinaryIO | None = None
    try:
        temporary = tempfile.NamedTemporaryFile(mode="wb")
        encoded = body.encode("utf-8")
        if temporary.write(encoded) != len(encoded):
            raise OSError("private body snapshot write was incomplete")
        temporary.flush()
    except (OSError, UnicodeEncodeError) as error:
        if temporary is not None:
            try:
                temporary.close()
            except OSError as cleanup_error:
                error.body_snapshot_cleanup_error = cleanup_error
        raise BodySnapshotError(
            "local private body snapshot preparation failed; no mutation was attempted"
        ) from error

    snapshot = PrivateBodySnapshot(temporary)
    active_error: BaseException | None = None
    try:
        yield snapshot
    except BaseException as error:
        active_error = error
        raise
    finally:
        try:
            temporary.close()
        except OSError as cleanup_error:
            if active_error is not None:
                active_error.body_snapshot_cleanup_error = cleanup_error
            elif snapshot.mutation_exited_zero:
                raise BodySnapshotError(
                    "private body snapshot cleanup failed after the mutation command "
                    "exited zero; independently verify exact state and do not retry",
                    after_zero_exit=True,
                ) from cleanup_error
            else:
                raise BodySnapshotError(
                    "local private body snapshot cleanup failed; no mutation was attempted"
                ) from cleanup_error


def expected_identity(
    *,
    repository: str,
    pr_number: int,
    base: str,
    base_oid: str,
    head: str,
    head_oid: str,
    head_owner: str,
    head_repository: str,
) -> ExpectedIdentity:
    """Validate and construct the exact PR identity shared by all commands."""

    validate_identity_inputs(
        repository=repository,
        pr_number=pr_number,
        base=base,
        base_oid=base_oid,
        head=head,
        head_oid=head_oid,
        head_owner=head_owner,
        head_repository=head_repository,
    )
    return ExpectedIdentity(
        repository=repository,
        pr_number=pr_number,
        base=base,
        base_oid=base_oid,
        head=head,
        head_oid=head_oid,
        head_owner=head_owner,
        head_repository=head_repository,
    )
