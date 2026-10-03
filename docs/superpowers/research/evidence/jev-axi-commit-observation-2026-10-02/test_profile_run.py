"""Run-CLI record tests with a synthetic external protocol peer, never a model."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parent
PEER = r'''
import json, os, subprocess, sys
from pathlib import Path
if '--version' in sys.argv:
    print('codex-cli fixture')
    raise SystemExit()
home = Path(os.environ['CODEX_HOME'])
project = Path.cwd()
task = None
experimental_api = False
thread_started = False
overrides = dict(arg.split('=', 1) for index, arg in enumerate(sys.argv)
                 if index and sys.argv[index - 1] == '-c')
for line in sys.stdin:
    message = json.loads(line)
    ident, method = message.get('id'), message.get('method')
    if ident is None:
        continue
    if method == 'initialize':
        experimental_api = message.get('params', {}).get('capabilities', {}).get('experimentalApi', False)
        result = {}
    elif method == 'skills/list':
        result = {'data': [{'cwd': str(project), 'errors': [], 'skills': [
            {'name': 'tdd', 'scope': 'user', 'enabled': True,
             'path': str(home / 'tdd/SKILL.md')}]}]}
    elif method == 'model/list':
        result = {'nextCursor': None, 'data': [{'model': 'gpt-6.1-sol',
            'supportedReasoningEfforts': [{'reasoningEffort': 'medium'},
                                         {'reasoningEffort': 'high'}]}]}
    elif method == 'thread/start':
        if not experimental_api or (home / 'reject-thread').exists():
            print(json.dumps({'id': ident, 'error': {'code': -32600,
                'message': 'thread/start.historyMode requires experimentalApi capability'}}), flush=True)
            continue
        thread_started = True
        instructions = [str(home / 'AGENTS.md')]
        if (home / 'extra.md').exists():
            instructions.append(str(home / 'extra.md'))
        result = {'model': 'gpt-6.1-sol', 'cwd': str(project),
            'approvalPolicy': 'on-request', 'approvalsReviewer': 'user',
            'instructionSources': instructions,
            'sandbox': {'type': 'workspaceWrite', 'writableRoots': [],
                        'networkAccess': False, 'excludeTmpdirEnvVar': True,
                        'excludeSlashTmp': True},
            'thread': {'id': 'fixture-parent', 'cwd': str(project),
                       'cliVersion': 'fixture', 'turns': []}}
    elif method == 'mcpServerStatus/list':
        if (home / 'git-drift-during-discovery').exists():
            subprocess.run(['git', 'config', 'core.hooksPath', '/dev/null'], check=True)
        servers = []
        for plugin, name in [('unified-computer-use@openai-bundled', 'cua_repl'),
                             ('fork-ops@fork-ops', 'fork-ops')]:
            disabled = overrides.get('plugins.' + plugin + '.mcp_servers.' + name + '.enabled') == 'false'
            servers.append({'name': name, 'pluginId': plugin,
                'runtimeStatus': ('disabled' if disabled else 'connected') if thread_started else None,
                'tools': {} if disabled else {'synthetic-tool': {}}})
        if (home / 'unexpected-connector').exists():
            servers.append({'name': 'unexpected', 'pluginId': 'new@fixture',
                            'runtimeStatus': 'connected', 'tools': {'synthetic-tool': {}}})
        result = {'nextCursor': None, 'data': servers}
    elif method == 'turn/start':
        task = message['params']['input'][0]['text']
        (home / 'task-delivered').touch()
        if (home / 'incomplete-record').exists():
            partial = project / '.observation/records/partial-attempt'
            partial.mkdir()
            (partial / 'message.txt').write_text('retained partial message')
        if (home / 'display-items').exists():
            for index in range(41):
                print(json.dumps({'method': 'item/completed', 'params': {
                    'threadId': 'fixture-parent', 'item': {'id': str(index), 'type': 'plan'}}}), flush=True)
        (project / 'observed.txt').write_text('synthetic protocol fixture\n')
        subprocess.run(['git', 'add', 'observed.txt'], check=True)
        subprocess.run(['git', 'commit', '--quiet', '-m', 'test: retain observation'], check=True)
        print(json.dumps({'id': ident, 'result': {'turn': {'id': 'fixture-turn'}}}), flush=True)
        if (home / 'complete').exists():
            print(json.dumps({'method': 'thread/settings/updated', 'params': {
                'threadId': 'fixture-parent', 'threadSettings': {
                    'model': 'gpt-6.1-sol', 'effort': 'medium',
                    'approvalPolicy': 'on-request', 'approvalsReviewer': 'user',
                    'sandboxPolicy': {'type': 'workspaceWrite', 'writableRoots': [],
                        'networkAccess': False, 'excludeTmpdirEnvVar': True,
                        'excludeSlashTmp': True}}}}), flush=True)
            print(json.dumps({'method': 'turn/completed', 'params': {
                'threadId': 'fixture-parent', 'turn': {'id': 'fixture-turn',
                    'status': 'completed', 'error': None}}}), flush=True)
            continue
        print(json.dumps({'id': 900, 'method': 'item/commandExecution/requestApproval',
                          'params': {'reason': 'synthetic boundary stop'}}), flush=True)
        continue
    elif method == 'thread/read':
        result = {'thread': {'id': 'fixture-parent', 'cwd': str(project)}}
    elif method == 'thread/turns/list':
        result = {'nextCursor': None, 'data': [{'id': 'fixture-turn', 'status': 'completed',
            'error': None, 'items': [{'type': 'userMessage', 'id': 'fixture-user',
                'content': [{'type': 'text', 'text': task}]}]}]}
    else:
        (home / 'unexpected-task').write_text(method)
        result = {}
    print(json.dumps({'id': ident, 'result': result}), flush=True)
'''


class ProfileRun(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        (self.home / "tdd").mkdir(parents=True)
        (self.home / "tdd/SKILL.md").write_text("# Synthetic skill\n")
        (self.home / "AGENTS.md").write_text("Synthetic test instructions.\n")
        (self.home / "config.toml").write_text("")
        binary = self.root / "bin"
        binary.mkdir()
        peer = binary / "codex"
        peer.write_text("#!" + sys.executable + "\n" + PEER)
        peer.chmod(0o755)
        self.env = {**os.environ, "CODEX_HOME": str(self.home),
                    "PATH": str(binary) + os.pathsep + os.environ["PATH"]}
        self.receipts = self.root / "receipts"
        self.receipts.mkdir()
        result = subprocess.run([sys.executable, str(SOURCE / "prepare.py"),
            "--parent", str(self.root), "--discover-profile"], env=self.env,
            capture_output=True, text=True, check=True)
        prepared = json.loads(result.stdout)
        self.manifest = Path(prepared["manifest"])
        self.sha256 = prepared["sha256"]

    def invoke(self):
        result = subprocess.run([sys.executable, str(SOURCE / "run.py"),
            "--manifest", str(self.manifest), "--expected-sha256", self.sha256,
            "--receipt-dir", str(self.receipts)], env=self.env, capture_output=True, text=True)
        receipt = json.loads(next(self.receipts.glob("*.json")).read_text())
        return result, receipt

    def test_added_skill_resource_is_rejected_before_native_task(self):
        (self.home / "tdd/new-reference.md").write_text("unbound new resource\n")
        result, receipt = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / "unexpected-task").exists())
        self.assertIn("resource tree drift", receipt["error"])

    def test_preparation_rejects_an_active_plugin_server_without_delivering_task(self):
        (self.home / "unexpected-connector").touch()
        result = subprocess.run([sys.executable, str(SOURCE / "prepare.py"),
            "--parent", str(self.root), "--discover-profile"], env=self.env,
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("active connector outside the profile", result.stderr)
        receipts = [json.loads(p.read_text()) for p in self.root.glob("preparation-*.json")]
        failed = [r for r in receipts if r["status"] == "failed"]
        self.assertEqual(len(failed), 1)
        self.assertFalse((Path(failed[0]["root"]) / "manifest.json").exists())
        self.assertFalse((self.home / "task-delivered").exists())

    def test_unprepared_instruction_source_stops_before_task_delivery(self):
        (self.home / "extra.md").write_text("additional instruction source\n")
        result, receipt = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / "unexpected-task").exists())
        self.assertIn("instruction sources differ", receipt["error"])

    def test_permission_stop_retains_completed_commit_and_primary_reason(self):
        result, receipt = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("native permission or user input", receipt["error"])
        evidence = json.loads((self.manifest.parent / "git-evidence.json").read_text())
        self.assertEqual(len(evidence["commits"]), 1)
        self.assertEqual(evidence["commits"][0]["message"].strip(), "test: retain observation")
        self.assertEqual(evidence["git_boundary"], "matched")
        self.assertEqual(receipt["status"], "native-incomplete")

    def test_display_items_do_not_consume_tool_call_budget(self):
        (self.home / "display-items").touch()
        result, receipt = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("native permission or user input", receipt["error"])
        evidence = json.loads((self.manifest.parent / "git-evidence.json").read_text())
        self.assertEqual(len(evidence["commits"]), 1)

    def test_partial_observer_attempt_prevents_qualified_context_match(self):
        (self.home / "incomplete-record").touch()
        result, receipt = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        evidence = json.loads((self.manifest.parent / "git-evidence.json").read_text())
        self.assertEqual(evidence["git_boundary"], "unqualified")
        self.assertEqual(len(evidence["observations"]), 2)
        partial = next(r for r in evidence["observations"] if r["directory"] == "partial-attempt")
        self.assertFalse(partial["valid"])
        self.assertIn("message.txt", partial["retained_files"])
        self.assertTrue(evidence["commits"][0]["matching_observations"])

    def test_git_drift_during_discovery_stops_before_task_delivery(self):
        (self.home / "git-drift-during-discovery").touch()
        result, receipt = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / "task-delivered").exists())
        self.assertIn("Git state drift", receipt["error"])

    def test_complete_protocol_with_default_fields_retains_delivery_and_commit(self):
        (self.home / "complete").touch()
        result, receipt = self.invoke()
        self.assertEqual(result.returncode, 0, receipt.get("error"))
        self.assertEqual(receipt["status"], "observed")
        self.assertEqual(receipt["observation"]["git_boundary"], "matched")
        outcome = json.loads((self.manifest.parent / "outcome.json").read_text())
        self.assertEqual(len(outcome["histories"]["fixture-parent"]), 1)

    def test_server_error_is_retained_without_inventing_instruction_drift(self):
        (self.home / "reject-thread").touch()
        result, receipt = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("-32600", receipt["error"])
        self.assertIn("thread/start.historyMode requires experimentalApi capability", receipt["error"])
        self.assertNotIn("instruction sources differ", receipt["error"])
        self.assertFalse((self.home / "task-delivered").exists())


if __name__ == "__main__":
    unittest.main()
