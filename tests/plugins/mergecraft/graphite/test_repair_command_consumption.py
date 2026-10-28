from __future__ import annotations

import hashlib
import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIXTURES = _load_module(
    "graphite_repair_transport_fixtures",
    Path(__file__).with_name("test_submit_draft_stack.py"),
)
GRAPHITE = FIXTURES.GRAPHITE
PUBLISHER = _load_module("graphite_repair_publisher_consumer", GRAPHITE.UPDATE)


class PublicationReached(Exception):
    def __init__(self, operation, arguments):
        self.operation = operation
        self.arguments = arguments


def consume_publication(command):
    """Run the real publisher parser, stopping at either inert operation handler.

    This observes CLI compatibility and the exact arguments delivered to an
    operation. It does not validate content, access receipts, or mutate a PR.
    """
    errors = io.StringIO()

    def reached(operation):
        def handler(**arguments):
            raise PublicationReached(operation, arguments)

        return handler

    with (
        mock.patch.object(sys, "argv", command[1:]),
        mock.patch.object(PUBLISHER, "update_text", side_effect=reached("text")),
        mock.patch.object(PUBLISHER, "mark_ready", side_effect=reached("ready")),
        mock.patch.object(
            PUBLISHER,
            "load_receipts",
            side_effect=AssertionError("consumer observation accessed receipts"),
        ),
        redirect_stdout(io.StringIO()),
        redirect_stderr(errors),
    ):
        try:
            exit_code = PUBLISHER.main()
        except PublicationReached as observed:
            return (observed.operation, observed.arguments), None, errors.getvalue()
        except SystemExit as rejected:
            return None, rejected.code, errors.getvalue()
    return None, exit_code, errors.getvalue()


class RepairCommandConsumptionTests(unittest.TestCase):
    def setUp(self) -> None:
        # Reuse producer inputs without inheriting or rediscovering its tests.
        # Its candidate builder and review loader are inert; this observation
        # qualifies command consumption, not manifest or review validity.
        self.fixture = FIXTURES.GraphiteTransportTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.expected = GRAPHITE.ExpectedIdentity(
            repository="acme/app",
            pr_number=42,
            base="main",
            base_oid="a" * 40,
            head="acme:feature",
            head_oid="b" * 40,
            head_owner="acme",
            head_repository="acme/app",
        )

    @staticmethod
    def digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def observed(self, command):
        observed, parser_exit, errors = consume_publication(command)
        self.assertIsNotNone(
            observed,
            f"publication did not reach a handler: parser exit {parser_exit}; {errors}",
        )
        self.assertIsNone(parser_exit, errors)
        return observed

    def observe_repair(self, item):
        """Consume admitted commands while their member's frozen inputs exist.

        Represent private path arguments by their exact bytes for semantic
        comparison. Expected identities, bytes, and all other handler arguments
        are specified independently in each example, not read from argv.
        """
        expected, entry, commands, _audit = GRAPHITE._repair_commands(item)
        observations = []
        with GRAPHITE._repair_payload_snapshot(
            item, expected, entry, commands
        ) as frozen_commands:
            for command in frozen_commands:
                operation, arguments = self.observed(command)
                arguments = dict(arguments)
                for field, original in (
                    ("review_input_path", self.fixture.review_input),
                    ("body_path", Path(item["target_body_source"]["path"])),
                    ("body_template_path", Path(item["target_body_source"]["path"])),
                ):
                    path = arguments.get(field)
                    if path is not None:
                        self.assertIsInstance(path, Path)
                        self.assertTrue(path.is_absolute())
                        self.assertNotEqual(path, original)
                        arguments[field] = path.read_bytes()
                observations.append((operation, arguments))
        return observations

    def common_arguments(self, *, required=True):
        return {
            "expected": self.expected,
            "review_input_path": b"{}\n",
            "review_mode": "required" if required else "not-required",
            "review_bundle_root": (
                Path(self.fixture.temporary.name) / "review-bundle"
                if required
                else None
            ),
            "selected_specialists": ["security"] if required else [],
            "receipt_directory": None,
        }

    def literal_item(self, *, transport_body, transport_draft, restore_ready):
        source = Path(self.fixture.temporary.name) / "canonical-body.md"
        source.write_bytes(b"Canonical body\r\n")
        entry = {
            **self.fixture.candidate,
            "body_source": {"mode": "file", "path": str(source)},
            "review_input_pr": 42,
            "review_mode": "required" if restore_ready else "not-required",
            "review_bundle": (
                str(Path(self.fixture.temporary.name) / "review-bundle")
                if restore_ready
                else None
            ),
            "selected_specialists": ["security"] if restore_ready else [],
        }
        preimage = {
            "number": 42,
            "url": "https://github.com/acme/app/pull/42",
            "title_sha256": "1" * 64,
            "body_sha256": "2" * 64,
            "is_draft": False,
        }
        return GRAPHITE._handoff_entry(
            entry,
            preimage,
            self.fixture.stored(body=transport_body, draft=transport_draft),
            "acme/app",
        )

    def test_generated_template_text_reaches_the_bound_required_publication(self):
        observations = self.observe_repair(self.fixture.required_item())
        self.assertEqual(
            observations,
            [
                (
                    "text",
                    {
                        **self.common_arguments(),
                        "expected_title_sha256": self.digest("feat: feature"),
                        "expected_body_sha256": self.digest("Graphite transport\n"),
                        "expected_draft": True,
                        "title": "feat: feature",
                        "body_path": None,
                        "body_template_path": b"PR __PUBLISHING_REVIEWABLE_PRS_PR_NUMBER__\n",
                        "text_scope": "title-body",
                    },
                ),
            ],
        )

    def test_generated_literal_text_preserves_ready_state_and_review_exemption(self):
        item = self.literal_item(
            transport_body="Graphite transport\n",
            transport_draft=False,
            restore_ready=False,
        )
        self.assertEqual(
            self.observe_repair(item),
            [
                (
                    "text",
                    {
                        **self.common_arguments(required=False),
                        "expected_title_sha256": self.digest("feat: feature"),
                        "expected_body_sha256": self.digest("Graphite transport\n"),
                        "expected_draft": False,
                        "title": "feat: feature",
                        "body_path": b"Canonical body\r\n",
                        "body_template_path": None,
                        "text_scope": "title-body",
                    },
                ),
            ],
        )

    def test_ready_only_and_text_then_ready_preserve_the_same_member_and_review(self):
        for transport_body, operations in (
            ("Canonical body\r\n", ["ready"]),
            ("Graphite transport\n", ["text", "ready"]),
        ):
            with self.subTest(operations=operations):
                item = self.literal_item(
                    transport_body=transport_body,
                    transport_draft=True,
                    restore_ready=True,
                )
                observed = self.observe_repair(item)
                self.assertEqual([operation for operation, _ in observed], operations)
                for operation, arguments in observed:
                    expected_arguments = {
                        **self.common_arguments(),
                        "expected_title_sha256": self.digest("feat: feature"),
                        "expected_body_sha256": self.digest(
                            transport_body if operation == "text" else "Canonical body\r\n"
                        ),
                        "body_template_path": None,
                    }
                    if operation == "text":
                        expected_arguments.update(
                            expected_draft=True,
                            title="feat: feature",
                            body_path=b"Canonical body\r\n",
                            text_scope="title-body",
                        )
                    self.assertEqual(arguments, expected_arguments)

    def test_parser_overrides_redirect_both_operations_but_admission_refuses_them(self):
        item = self.literal_item(
            transport_body="Graphite transport\n",
            transport_draft=True,
            restore_ready=True,
        )
        other_member = GRAPHITE.ExpectedIdentity(
            repository="acme/app",
            pr_number=43,
            base="main",
            base_oid="a" * 40,
            head="acme:feature",
            head_oid="b" * 40,
            head_owner="acme",
            head_repository="acme/app",
        )
        for index, command in enumerate(item["publisher_commands"]):
            for override in (["--pr=43"], ["--pr", "43"], ["--p", "43"]):
                with self.subTest(operation=command[2], override=override):
                    redirected = [*command, *override]
                    _operation, arguments = self.observed(redirected)
                    self.assertEqual(arguments["expected"], other_member)
                    redirected_commands = list(item["publisher_commands"])
                    redirected_commands[index] = redirected
                    with mock.patch.object(
                        PUBLISHER, "main", wraps=PUBLISHER.main
                    ) as parser:
                        with self.assertRaises(GRAPHITE.GraphiteTransportError):
                            self.observe_repair(
                                {**item, "publisher_commands": redirected_commands}
                            )
                    parser.assert_not_called()

    def test_consumer_driver_distinguishes_parser_refusal_from_operation_entry(self):
        command = self.fixture.required_item()["publisher_commands"][0]
        observed, parser_exit, errors = consume_publication(
            [*command, "--unsupported-publication-option"]
        )
        self.assertIsNone(observed)
        self.assertEqual(parser_exit, 2)
        self.assertIn("unrecognized arguments", errors)

    def test_consumer_driver_detects_a_wrong_expected_member_and_payload(self):
        _operation, arguments = self.observe_repair(self.fixture.required_item())[0]
        wrong_member = GRAPHITE.ExpectedIdentity(
            repository="acme/app",
            pr_number=43,
            base="main",
            base_oid="a" * 40,
            head="acme:feature",
            head_oid="b" * 40,
            head_owner="acme",
            head_repository="acme/app",
        )
        with self.assertRaises(AssertionError):
            self.assertEqual(arguments["expected"], wrong_member)
        with self.assertRaises(AssertionError):
            self.assertEqual(arguments["title"], "feat: unrelated feature")
        with self.assertRaises(AssertionError):
            self.assertEqual(arguments["body_template_path"], b"Unrelated body\n")


if __name__ == "__main__":
    unittest.main()
