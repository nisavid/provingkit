import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PLAN = Path(__file__).with_name("accounting-command-plan.md")
LINUX = ["Linux", "synthetic-controller"]

CHILD = r'''
import json
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace
from unittest.mock import patch

plan, root, initial, admission_host, dispatch_host, accepted = sys.argv[1:]
root = Path(root)
initial = json.loads(initial)
admission_host = json.loads(admission_host)
dispatch_host = json.loads(dispatch_host)
accepted = json.loads(accepted)

blocks = re.findall(
    r"^```python\n(.*?)^```",
    Path(plan).read_text(),
    re.MULTILINE | re.DOTALL,
)

def block(prefix):
    matches = [code for code in blocks if code.startswith(prefix)]
    if len(matches) != 1:
        raise RuntimeError("Expected one displayed block: " + prefix)
    return matches[0]

producer = block("import datetime as dt\n").replace(
    'Path("<new invocation directory>")',
    "Path(" + repr(str(root / "invocation")) + ")",
)
preparation = block('prep = begin(').replace(
    "# Coordinator performs the bound preparation actions.",
    "Path(" + repr(str(root / "prepared")) + ").write_text('prepared')",
)
acceptance = block("accepted_at = tick()\n")
admission = block('admission = begin(')
admission, dispatch = admission.split(
    "# Recheck immediately before the bound start action:\n", 1
)
action_comments = [
    "    # Coordinator invokes the bound collector run CLI exactly once.",
    "    # Coordinator invokes the bound collector run CLI locally exactly once.",
]
matches = [comment for comment in action_comments if comment in dispatch]
if len(matches) != 1:
    raise RuntimeError("Expected one displayed local dispatch action.")
dispatch = dispatch.replace(
    matches[0],
    "    Path(" + repr(str(root / "dispatched")) + ").write_text('dispatched')",
)

current_host = initial

def observe_host():
    if current_host is None:
        raise OSError("Synthetic missing host observation.")
    return SimpleNamespace(
        sysname=current_host[0],
        nodename=current_host[1],
    )

original_read_text = Path.read_text

def observe_text(path, *args, **kwargs):
    if path == Path("/proc/sys/kernel/random/boot_id"):
        return "synthetic-boot\n"
    return original_read_text(path, *args, **kwargs)

namespace = {
    "PREPARATION_REFS": [],
    "PREPARED_REFS": [],
    "PREPARATION_OUTCOME": "synthetic preparation completed",
    "ACCEPTANCE_REQUEST_REFS": [],
    "ACCEPTANCE_REFS": [],
    "ACCEPTED_LIMITS": {
        "coordinator": 9000,
        "native": 3600,
        "shutdown": [5, 5],
    },
    "BOUNDARY_EVIDENCE": {
        "status": "observed",
        "reason": "Synthetic acceptance boundary for this test only.",
    },
    "FRESHNESS_REFS": [],
    "NATIVE_INPUT_REFS": [],
    "fresh": True,
}
with patch.object(os, "uname", observe_host), \
        patch.object(Path, "read_text", observe_text):
    try:
        exec(compile(producer, plan + ":producer", "exec"), namespace)
        exec(compile(preparation, plan + ":preparation", "exec"), namespace)
        if accepted:
            exec(compile(acceptance, plan + ":acceptance", "exec"), namespace)
            current_host = admission_host
            exec(compile(admission, plan + ":admission", "exec"), namespace)
            current_host = dispatch_host
            exec(compile(dispatch, plan + ":dispatch", "exec"), namespace)
    except RuntimeError as error:
        (root / "stopped").write_text(str(error))
'''


class AccountingProducerTests(unittest.TestCase):
    def run_session(
        self,
        initial,
        admission_host=LINUX,
        dispatch_host=LINUX,
        accepted=True,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    CHILD,
                    str(PLAN),
                    str(root),
                    json.dumps(initial),
                    json.dumps(admission_host),
                    json.dumps(dispatch_host),
                    json.dumps(accepted),
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            records = [
                json.loads(path.read_text())
                for path in (root / "invocation").glob("*.json")
            ]
            records.sort(key=lambda record: record["sequence"])
            return {
                "prepared": (root / "prepared").exists(),
                "dispatched": (root / "dispatched").exists(),
                "records": records,
            }

    def event(self, result, purpose):
        matches = [
            record
            for record in result["records"]
            if record.get("purpose") == purpose
        ]
        self.assertEqual(len(matches), 1, purpose)
        return matches[0]

    def test_non_linux_is_refused_before_preparation(self):
        result = self.run_session(["Darwin", "synthetic-controller"])

        self.assertFalse(result["prepared"])
        self.assertFalse(result["dispatched"])
        start = result["records"][0]
        self.assertEqual(
            start["start"]["host"],
            {"sysname": "Darwin", "nodename": "synthetic-controller"},
        )
        refusal = self.event(result, "Preparation refused")
        self.assertFalse(refusal["admitted"])
        self.assertTrue(refusal["host_reason"])
        self.assertFalse(
            any(
                record["schema"] == "compatibility-coordinator-work-start/v1"
                for record in result["records"]
            )
        )

    def test_non_linux_host_is_refused_at_admission(self):
        result = self.run_session(LINUX, admission_host=["Darwin", "synthetic-controller"])
        self.assertTrue(result["prepared"])
        self.assertFalse(result["dispatched"])
        admission = self.event(result, "Admission")
        self.assertFalse(admission["admitted"])
        self.assertTrue(admission["host_reason"])


    def test_non_linux_host_is_refused_immediately_before_dispatch(self):
        result = self.run_session(
            LINUX,
            dispatch_host=["Darwin", "synthetic-controller"],
        )

        self.assertTrue(self.event(result, "Admission")["admitted"])
        self.assertFalse(result["dispatched"])
        dispatch = self.event(result, "Dispatch-boundary reservation")
        self.assertFalse(dispatch["admitted"])
        self.assertTrue(dispatch["host_reason"])

    def test_linux_dispatches_with_acceptance_and_other_prerequisites(self):
        result = self.run_session(LINUX)

        self.assertTrue(result["prepared"])
        self.assertTrue(result["dispatched"])
        self.assertEqual(
            result["records"][0]["start"]["host"],
            {"sysname": "Linux", "nodename": "synthetic-controller"},
        )
        admission = self.event(result, "Admission")
        dispatch = self.event(result, "Dispatch-boundary reservation")
        self.assertTrue(admission["admitted"])
        self.assertTrue(dispatch["admitted"])
        self.assertIsNone(admission["host_reason"])
        self.assertIsNone(dispatch["host_reason"])
        self.assertEqual(
            dispatch["boundary"]["host"],
            result["records"][0]["start"]["host"],
        )

    def test_missing_host_is_refused_before_preparation(self):
        result = self.run_session(None)

        self.assertFalse(result["prepared"])
        self.assertFalse(result["dispatched"])
        self.assertIsNone(result["records"][0]["start"]["host"])
        refusal = self.event(result, "Preparation refused")
        self.assertFalse(refusal["admitted"])
        self.assertTrue(refusal["host_reason"])
        self.assertFalse(
            any(
                record["schema"] == "compatibility-coordinator-work-start/v1"
                for record in result["records"]
            )
        )

    def test_changed_host_is_refused_at_admission(self):
        result = self.run_session(
            LINUX,
            admission_host=["Linux", "different-controller"],
        )

        self.assertTrue(result["prepared"])
        self.assertFalse(result["dispatched"])
        admission = self.event(result, "Admission")
        self.assertFalse(admission["admitted"])
        self.assertTrue(admission["host_reason"])
        self.assertEqual(
            admission["boundary"]["host"],
            {"sysname": "Linux", "nodename": "different-controller"},
        )
        self.assertEqual(
            result["records"][0]["start"]["host"],
            {"sysname": "Linux", "nodename": "synthetic-controller"},
        )

    def test_missing_host_is_refused_at_admission(self):
        result = self.run_session(LINUX, admission_host=None)

        self.assertFalse(result["dispatched"])
        admission = self.event(result, "Admission")
        self.assertFalse(admission["admitted"])
        self.assertIsNone(admission["boundary"]["host"])
        self.assertTrue(admission["host_reason"])

    def test_changed_linux_host_is_refused_immediately_before_dispatch(self):
        result = self.run_session(
            LINUX,
            dispatch_host=["Linux", "different-controller"],
        )

        self.assertTrue(self.event(result, "Admission")["admitted"])
        self.assertFalse(result["dispatched"])
        dispatch = self.event(result, "Dispatch-boundary reservation")
        self.assertFalse(dispatch["admitted"])
        self.assertTrue(dispatch["host_reason"])
        self.assertEqual(
            dispatch["boundary"]["host"],
            {"sysname": "Linux", "nodename": "different-controller"},
        )

    def test_missing_host_is_refused_immediately_before_dispatch(self):
        result = self.run_session(LINUX, dispatch_host=None)

        self.assertTrue(self.event(result, "Admission")["admitted"])
        self.assertFalse(result["dispatched"])
        dispatch = self.event(result, "Dispatch-boundary reservation")
        self.assertFalse(dispatch["admitted"])
        self.assertIsNone(dispatch["boundary"]["host"])
        self.assertTrue(dispatch["host_reason"])

    def test_linux_without_acceptance_has_no_work_window_or_dispatch(self):
        result = self.run_session(LINUX, accepted=False)

        self.assertTrue(result["prepared"])
        self.assertFalse(result["dispatched"])
        self.assertIsNone(result["records"][0]["active_deadline"])
        self.assertFalse(
            any(
                record["schema"] == "compatibility-coordinator-work-start/v1"
                for record in result["records"]
            )
        )


if __name__ == "__main__":
    unittest.main()
