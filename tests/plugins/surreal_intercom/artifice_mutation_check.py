"""Run the author CLI cases against an explicitly selected sender mutant.

Usage: python -m tests.plugins.surreal_intercom.artifice_mutation_check SENDER
This diagnostic does not change the ordinary suite's checkout binding.
"""

import argparse
from pathlib import Path
import unittest
from unittest.mock import patch

from tests.plugins.surreal_intercom import test_artifice_author_cli as author
from tests.plugins.surreal_intercom import test_rolecasting_codex_owner_admission as peer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sender', type=Path, help='explicit path to a sender mutant')
    sender = parser.parse_args().sender.resolve(strict=True)
    names = (
        'test_wrong_type_in_scope_refuses_before_connection',
        'test_incomplete_scope_refuses_before_connection',
        'test_malformed_json_refuses_before_connection',
        'test_valid_request_reaches_disposable_peer',
    )
    suite = unittest.TestSuite(author.AuthorVerificationCliTests(name) for name in names)
    with patch.object(author, 'SENDER', sender), patch.object(peer, 'PROTOTYPE', sender):
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
