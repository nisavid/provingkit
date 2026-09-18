"""Ordinary examples for the throwaway production file-decision prototype."""

from dataclasses import dataclass
from pathlib import Path
import unittest

from scripts import validate_provingkit


@dataclass(frozen=True)
class FileCase:
    name: str
    relative_path: Path
    content: bytes
    expected: bool | str


def ordinary_cases() -> tuple[FileCase, ...]:
    yaml_metadata = (
        'repository: "https://github.com/nisavid/' + r"\x61gents" + '"\n'
    ).encode()
    return (
        FileCase(
            "plain", Path("release/provingkit/identity-prototype.txt"),
            ("See https://github.com/nisavid/" + "agents\n").encode(), True,
        ),
        FileCase(
            "yaml", Path("release/provingkit/identity-prototype.yaml"),
            yaml_metadata, True,
        ),
        FileCase(
            "bom-frontmatter", Path("release/provingkit/identity-prototype.md"),
            b"\xef\xbb\xbf---\n" + yaml_metadata + b"---\n# Documentary fixture\n", True,
        ),
        FileCase(
            "exact-context-path", Path("CONTEXT.md"),
            (Path(__file__).resolve().parents[1] / "CONTEXT.md").read_bytes(), False,
        ),
        FileCase(
            "parse-error", Path("release/provingkit/identity-prototype.yaml"),
            b"title: [\n",
            "YAML identity source is unreadable: release/provingkit/identity-prototype.yaml",
        ),
        FileCase(
            "accepted-literal", Path("release/provingkit/identity-prototype.yaml"),
            ("repository: 'https://github.com/nisavid/" + r"\x61gents" + "'\n").encode(),
            False,
        ),
    )


class FileIdentityPrototypeTests(unittest.TestCase):
    def test_plain_identity_is_detected(self) -> None:
        content = ("See https://github.com/nisavid/" + "agents\n").encode()
        self.assertTrue(
            validate_provingkit.contains_historical_identity(Path("example.txt"), content)
        )

    def test_ordinary_file_decisions(self) -> None:
        for case in ordinary_cases():
            with self.subTest(case=case.name):
                if isinstance(case.expected, str):
                    with self.assertRaises(validate_provingkit.ValidationError) as caught:
                        validate_provingkit.contains_historical_identity(
                            case.relative_path, case.content
                        )
                    self.assertEqual(str(caught.exception), case.expected)
                else:
                    self.assertIs(
                        validate_provingkit.contains_historical_identity(
                            case.relative_path, case.content
                        ),
                        case.expected,
                    )


if __name__ == "__main__":
    unittest.main()
