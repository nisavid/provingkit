"""History-only publication through the writer and publisher command boundaries."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
WRITER = ROOT / 'plugins/mergecraft/skills/writing-reviewable-pr-descriptions/scripts/validate_change_navigation.py'
PUBLISHER = ROOT / 'plugins/mergecraft/skills/publishing-reviewable-prs/scripts'
TOKEN = '__PUBLISHING_REVIEWABLE_PRS_PR_NUMBER__'
TITLE = 'chore: synchronize upstream history'


class EmptyDiffPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repository'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.com')
        self.git('config', 'user.name', 'Fixture')
        (self.repo / 'file.txt').write_text('same tree\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD')
        self.git('commit', '--allow-empty', '-qm', 'upstream history')
        self.head = self.git('rev-parse', 'HEAD')
        self.prepare()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def prepare(self):
        tree = self.git('rev-parse', self.base + '^{tree}')
        self.body = (
            '<details>\n'
            '<summary><picture><img alt="DIFF" src="https://img.shields.io/badge/DIFF-57606A?style=for-the-badge" height="16"></picture>&nbsp;<picture><img alt="FILES: 0 touched" src="https://img.shields.io/badge/FILES-0-5F6B78?style=flat" height="16"></picture></summary>\n\n'
            'No file changes in the reviewer-visible comparison. '
            f'[Review the commits](https://github.com/acme/app/pull/{TOKEN}/commits) and '
            f'[view the immutable history comparison](https://github.com/acme/app/compare/{self.base}...{self.head}).\n\n'
            '</details>\n\n'
            f'Synchronize upstream history in PR #{TOKEN}.\n'
        )
        self.raw = {
            'version': 4, 'repository': 'acme/app', 'pr_number': TOKEN,
            'base': {'ref': 'main', 'oid': self.base},
            'head': {'ref': 'acme:sync', 'oid': self.head, 'owner': 'acme', 'repository': 'acme/app-fork'},
            'candidate': {'title': TITLE, 'body_sha256': hashlib.sha256(self.body.encode()).hexdigest()},
            'git_diff': [], 'diff': [], 'stack': [],
            'git_history': {'merge_base_oid': self.base, 'base_tree_oid': tree,
                            'merge_base_tree_oid': tree, 'head_tree_oid': tree,
                            'head_only_commits': self.git('rev-list', '--reverse', f'{self.base}..{self.head}').splitlines()},
            'baseline': {'mode': 'new', 'title_sha256': None, 'body_sha256': None, 'fragments': []},
        }
        self.manifest_path = self.root / 'review-input.json'
        self.template_path = self.root / 'template.md'
        self.body_path = self.root / 'body.md'
        self.save()

    def save(self):
        raw = copy.deepcopy(self.raw)
        raw.pop('content_sha256', None)
        raw['content_sha256'] = hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        self.manifest_path.write_text(json.dumps(raw))
        self.template_path.write_text(self.body)
        self.body_path.write_text(self.body.replace(TOKEN, '2'))

    def writer(self, repository=None):
        return subprocess.run([sys.executable, str(WRITER), '--repository', 'acme/app', '--pr', '2', '--title', TITLE,
                               '--review-input', str(self.manifest_path), '--template-body', str(self.template_path),
                               '--git-repository', str(repository or self.repo), str(self.body_path)],
                              cwd=self.repo, capture_output=True, text=True)

    def test_writer_accepts_new_history_with_an_identical_file_tree(self):
        result = self.writer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'Change navigation is valid')

    def prepare_file_changing_stack(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_review_input import DIFF, manifest
        from test_validate_change_navigation import STACK, badge
        source = self.repo / 'src/widget.ts'
        source.parent.mkdir()
        source.write_text('one\ntwo\nthree\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'file base')
        self.base = self.git('rev-parse', 'HEAD')
        source.write_text(''.join(f'new {index}\n' for index in range(9)))
        self.git('commit', '-qam', 'ordinary file diff')
        self.head = self.git('rev-parse', 'HEAD')
        zero_files = badge('FILES: 0 added, 0 modified, 0 removed',
                           'FILES-%2B0%20~0%20%E2%88%920-5F6B78')
        lines = STACK.replace('feat: top', TITLE).splitlines()
        for index, line in enumerate(lines):
            if line.startswith('- **[#1 '):
                lines[index] = line.split('<br>', 1)[0] + '<br>' + zero_files
            elif '**← this PR**' in line:
                lines[index] = line.replace('#2', '#' + TOKEN).replace('/pull/2)', '/pull/' + TOKEN + ')')
        diff = DIFF.replace('/pull/2/', '/pull/' + TOKEN + '/')
        self.body = '\n'.join(lines).rstrip() + '\n\n' + diff
        self.raw = manifest(DIFF, title=TITLE, pr_number=TOKEN)
        self.raw['base']['oid'] = self.base
        self.raw['head']['oid'] = self.head
        self.raw['head']['ref'] = 'acme:sync'
        self.raw['stack'] = [
            {'number': 1, 'title': 'feat: base', 'url': 'https://github.com/acme/app/pull/1',
             'current': False, 'metrics': {},
             'file_operations': {'added': 0, 'modified': 0, 'removed': 0, 'moved': 0, 'copied': 0}},
            {'number': TOKEN, 'title': TITLE, 'url': f'https://github.com/acme/app/pull/{TOKEN}',
             'current': True, 'metrics': {'IMPL': [9, 3]},
             'file_operations': {'added': 0, 'modified': 1, 'removed': 0, 'moved': 0, 'copied': 0}},
        ]
        self.raw['candidate']['body_sha256'] = hashlib.sha256(self.body.encode()).hexdigest()
        self.save()

    def test_writer_accepts_prior_history_only_row_before_a_file_changing_current_pr(self):
        self.prepare_file_changing_stack()
        result = self.writer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'Change navigation is valid')

    def test_writer_holds_empty_prior_categories_with_any_nonzero_file_operation(self):
        self.prepare_file_changing_stack()
        from test_validate_change_navigation import badge
        original_body, original_raw = self.body, copy.deepcopy(self.raw)
        cases = (
            ('added', 'FILES: 1 added, 0 modified, 0 removed', 'FILES-%2B1%20~0%20%E2%88%920-5F6B78'),
            ('modified', 'FILES: 0 added, 1 modified, 0 removed', 'FILES-%2B0%20~1%20%E2%88%920-5F6B78'),
            ('removed', 'FILES: 0 added, 0 modified, 1 removed', 'FILES-%2B0%20~0%20%E2%88%921-5F6B78'),
            ('moved', 'FILES: 0 added, 0 modified, 0 removed, 1 moved', 'FILES-%2B0%20~0%20%E2%88%920%20MOVED%201-5F6B78'),
            ('copied', 'FILES: 0 added, 0 modified, 0 removed, 1 copied', 'FILES-%2B0%20~0%20%E2%88%920%20COPIED%201-5F6B78'),
        )
        for operation, alt, path in cases:
            with self.subTest(operation=operation):
                lines = original_body.splitlines()
                for index, line in enumerate(lines):
                    if line.startswith('- **[#1 '):
                        lines[index] = line.split('<br>', 1)[0] + '<br>' + badge(alt, path)
                self.body = '\n'.join(lines) + '\n'
                self.raw = copy.deepcopy(original_raw)
                self.raw['stack'][0]['file_operations'][operation] = 1
                self.raw['candidate']['body_sha256'] = hashlib.sha256(self.body.encode()).hexdigest()
                self.save()
                result = self.writer()
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('Change navigation is invalid', result.stderr)

    def test_writer_holds_missing_duplicate_and_malformed_prior_file_metrics(self):
        self.prepare_file_changing_stack()
        from test_validate_change_navigation import badge
        original = self.body
        zero_files = badge('FILES: 0 added, 0 modified, 0 removed',
                           'FILES-%2B0%20~0%20%E2%88%920-5F6B78')
        for metrics in (' ', zero_files + ' ' + zero_files,
                        zero_files.replace('0 removed', 'removed'),
                        zero_files.replace('0 removed', '0 removed, 0 moved')):
            with self.subTest(metrics=metrics):
                self.body = original.replace('<br>' + zero_files, '<br>' + metrics)
                self.raw['candidate']['body_sha256'] = hashlib.sha256(self.body.encode()).hexdigest()
                self.save()
                result = self.writer()
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('Change navigation is invalid', result.stderr)

    def test_writer_holds_prior_zero_file_row_that_disagrees_with_sealed_operations(self):
        self.prepare_file_changing_stack()
        self.raw['stack'][0]['file_operations']['added'] = 1
        self.save()
        self.assertNotEqual(self.writer().returncode, 0)

    def test_writer_holds_current_operations_that_disagree_with_the_file_diff(self):
        self.prepare_file_changing_stack()
        self.body = self.body.replace('FILES: 0 added, 1 modified, 0 removed',
                                      'FILES: 1 added, 0 modified, 0 removed').replace(
                                          'FILES-%2B0%20~1%20%E2%88%920-5F6B78',
                                          'FILES-%2B1%20~0%20%E2%88%920-5F6B78')
        self.raw['stack'][1]['file_operations']['added'] = 1
        self.raw['stack'][1]['file_operations']['modified'] = 0
        self.raw['candidate']['body_sha256'] = hashlib.sha256(self.body.encode()).hexdigest()
        self.save()
        self.assertNotEqual(self.writer().returncode, 0)

    def test_writer_reobserves_current_git_diff_with_a_prior_history_only_row(self):
        self.prepare_file_changing_stack()
        source = self.repo / 'src/widget.ts'
        source.write_text('changed after the inventory was sealed\n')
        self.git('commit', '-qam', 'different current file diff')
        self.raw['head']['oid'] = self.git('rev-parse', 'HEAD')
        self.save()
        self.assertNotEqual(self.writer().returncode, 0)

    def test_writer_holds_extra_history_summary_content(self):
        original = self.body
        extras = (
            '<a href="https://github.com/acme/app/pull/2/files#diff-invented">invented.txt</a>',
            '[invented.txt](https://github.com/acme/app/pull/2/files#diff-invented)',
            'invented.txt',
            '<!-- invented file navigation -->',
            '<a href="https://github.com/acme/app/pull/2/files#diff-invented"></a>',
        )
        for extra in extras:
            for boundary in ('<summary>', '&nbsp;', '</summary>'):
                with self.subTest(extra=extra, boundary=boundary):
                    replacement = extra + boundary if boundary == '</summary>' else boundary + extra
                    self.body = original.replace(boundary, replacement)
                    self.raw['candidate']['body_sha256'] = hashlib.sha256(self.body.encode()).hexdigest()
                    self.save()
                    result = self.writer()
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn('Change navigation is invalid', result.stderr)

    def test_writer_holds_linked_or_extra_history_summary_wrappers(self):
        original = self.body
        file_url = 'https://github.com/acme/app/pull/2/files#diff-invented'
        summaries = (
            original.replace('&nbsp;', f'&nbsp;<a href="{file_url}">').replace('</summary>', '</a></summary>'),
            original.replace('&nbsp;', '&nbsp;[').replace('</summary>', f']({file_url})</summary>'),
            original.replace('&nbsp;', '&nbsp;<picture>').replace('</summary>', '</picture></summary>'),
            original.replace('<summary>', '<summary><span>').replace('</summary>', '</span></summary>'),
            original.replace('&nbsp;', '&nbsp; '),
        )
        for changed in summaries:
            with self.subTest(body=changed):
                self.body = changed
                self.raw['candidate']['body_sha256'] = hashlib.sha256(changed.encode()).hexdigest()
                self.save()
                result = self.writer()
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('Change navigation is invalid', result.stderr)

    def test_writer_accepts_supported_history_summary_attribute_order(self):
        self.body = self.body.replace(
            'alt="FILES: 0 touched" src=', 'src='
        ).replace(
            'height="16"></picture></summary>',
            'height="16" alt="FILES: 0 touched"></picture></summary>',
        )
        self.raw['candidate']['body_sha256'] = hashlib.sha256(self.body.encode()).hexdigest()
        self.save()
        result = self.writer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'Change navigation is valid')

    def test_writer_retains_history_summary_badge_presentation_checks(self):
        original = self.body
        for changed in (
            original.replace('height="16"', 'height="17"'),
            original.replace('alt="FILES: 0 touched"', 'alt="FILES: 0 touched" title="FILES: 0 touched"'),
            original.replace('alt="FILES: 0 touched"', 'alt="FILES: 0 touched" alt="FILES: 0 touched"'),
            original.replace('alt="FILES: 0 touched"', 'alt="FILES: 0 touched" class="unexpected"'),
            original.replace('FILES-0-5F6B78?style=flat', 'FILES-0-5F6B78?style=for-the-badge'),
        ):
            with self.subTest(body=changed):
                self.body = changed
                self.raw['candidate']['body_sha256'] = hashlib.sha256(changed.encode()).hexdigest()
                self.save()
                result = self.writer()
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('Change navigation is invalid', result.stderr)

    def test_writer_accepts_change_then_revert_history(self):
        (self.repo / 'file.txt').write_text('temporary change\n')
        self.git('commit', '-qam', 'change')
        self.git('revert', '--no-edit', 'HEAD')
        self.head = self.git('rev-parse', 'HEAD')
        self.prepare()
        self.assertEqual(self.writer().returncode, 0)

    def test_writer_holds_missing_stale_and_manipulated_history(self):
        original = copy.deepcopy(self.raw)
        for mutation in ('missing', 'v3', 'no-commits', 'wrong-commit', 'wrong-tree', 'same-tip', 'invented-file'):
            with self.subTest(mutation=mutation):
                self.raw = copy.deepcopy(original)
                if mutation == 'missing':
                    del self.raw['git_history']
                elif mutation == 'v3':
                    self.raw['version'] = 3
                elif mutation == 'no-commits':
                    self.raw['git_history']['head_only_commits'] = []
                elif mutation == 'wrong-commit':
                    self.raw['git_history']['head_only_commits'].insert(0, 'f' * 40)
                elif mutation == 'wrong-tree':
                    for key in ('base_tree_oid', 'merge_base_tree_oid', 'head_tree_oid'):
                        self.raw['git_history'][key] = 'f' * 40
                elif mutation == 'same-tip':
                    self.raw['head']['oid'] = self.base
                else:
                    self.raw['diff'] = [{'category': 'DOC', 'operation': 'ATOMIC', 'source_path': None,
                                         'target_path': 'invented.txt', 'additions': 0, 'deletions': 0}]
                self.save()
                self.assertNotEqual(self.writer().returncode, 0)

    def test_writer_holds_invented_commits_or_comparison_navigation(self):
        original = self.body
        for changed in (original.replace('/pull/' + TOKEN + '/commits', '/pull/99/commits'),
                        original.replace('/compare/' + self.base, '/compare/' + 'f' * 40),
                        original.replace('No file changes', 'No important file changes')):
            with self.subTest(body=changed):
                self.body = changed
                self.raw['candidate']['body_sha256'] = hashlib.sha256(changed.encode()).hexdigest()
                self.save()
                self.assertNotEqual(self.writer().returncode, 0)

    def test_writer_holds_dirty_missing_shallow_and_replaced_git_history(self):
        (self.repo / 'dirty.txt').write_text('dirty\n')
        self.assertNotEqual(self.writer().returncode, 0)
        (self.repo / 'dirty.txt').unlink()
        self.git('replace', self.head, self.base)
        self.assertNotEqual(self.writer().returncode, 0)
        self.git('replace', '-d', self.head)
        shallow = self.root / 'shallow'
        subprocess.run(['git', 'clone', '--quiet', '--depth=2', self.repo.as_uri(), str(shallow)], check=True)
        self.assertNotEqual(self.writer(shallow).returncode, 0)
        self.raw['head']['oid'] = 'f' * 40
        self.save()
        self.assertNotEqual(self.writer().returncode, 0)

    def test_writer_holds_head_already_reachable_from_base(self):
        self.base, self.head = self.head, self.base
        self.prepare()
        # A caller's nonempty declaration cannot replace the observed ancestry.
        self.raw['git_history']['head_only_commits'] = [self.head]
        self.save()
        self.assertNotEqual(self.writer().returncode, 0)

    def test_writer_holds_divergent_base_even_with_equal_trees(self):
        fork = self.base
        self.git('switch', '-qc', 'divergent-base', fork)
        self.git('commit', '--allow-empty', '-qm', 'base-side history')
        self.base = self.git('rev-parse', 'HEAD')
        self.prepare()
        self.assertNotEqual(self.writer().returncode, 0)

    def test_writer_holds_file_changes_disguised_as_history_only(self):
        (self.repo / 'file.txt').write_text('actual file change\n')
        self.git('commit', '-qam', 'file change')
        self.head = self.git('rev-parse', 'HEAD')
        self.prepare()
        self.assertNotEqual(self.writer().returncode, 0)

    def test_publisher_creates_readies_and_audits_history_only_pr_using_real_git(self):
        self.publish_and_audit_current_pr()

    def test_publisher_creates_readies_and_audits_file_change_after_history_only_pr(self):
        self.prepare_file_changing_stack()
        self.publish_and_audit_current_pr()

    def publish_and_audit_current_pr(self):
        executable_dir = self.root / 'bin'
        executable_dir.mkdir()
        state_path = self.root / 'forge-state.json'
        state_path.write_text(json.dumps({
            'number': 2, 'url': 'https://github.com/acme/app/pull/2', 'title': TITLE, 'body': '',
            'baseRefName': 'main', 'baseRefOid': self.base, 'headRefName': 'sync', 'headRefOid': self.head,
            'headRepository': {'nameWithOwner': 'acme/app-fork'}, 'headRepositoryOwner': {'login': 'acme'},
            'isDraft': True, 'state': 'OPEN',
        }))
        fake_gh = executable_dir / 'gh'
        fake_gh.write_text('#!' + sys.executable + '\n' + '''import json, os, sys
from pathlib import Path
args = sys.argv[1:]
state_path = Path(os.environ['EMPTY_DIFF_FORGE_STATE'])
state = json.loads(state_path.read_text())
if args[:1] == ['api']:
    print('[[]]')
elif 'view' in args:
    print(json.dumps(state))
elif 'ready' in args:
    state['isDraft'] = False
    state_path.write_text(json.dumps(state))
elif 'create' in args or 'edit' in args:
    state['body'] = Path(args[args.index('--body-file') + 1]).read_text()
    state['title'] = args[args.index('--title') + 1]
    state_path.write_text(json.dumps(state))
    print(state['url'])
else:
    sys.exit('Unexpected forge boundary command')
''')
        fake_gh.chmod(0o755)
        environment = dict(os.environ, PATH=str(executable_dir) + os.pathsep + os.environ['PATH'],
                           XDG_STATE_HOME=str(self.root / 'state'), EMPTY_DIFF_FORGE_STATE=str(state_path))
        identity = ['--repository', 'acme/app', '--base', 'main', '--base-oid', self.base,
                    '--head', 'acme:sync', '--head-oid', self.head, '--head-owner', 'acme',
                    '--head-repository', 'acme/app-fork']
        result = subprocess.run([sys.executable, str(PUBLISHER / 'create_reviewable_pr.py'), *identity,
                                 '--title', TITLE, '--body-template', str(self.template_path),
                                 '--review-input', str(self.manifest_path), '--review-mode', 'not-required',
                                 '--selected-specialists', '[]'], cwd=self.repo, env=environment,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        stored = json.loads(state_path.read_text())
        self.assertEqual(stored['body'], self.body.replace(TOKEN, '2'))
        self.assertTrue(stored['isDraft'])
        audit = subprocess.run([sys.executable, str(PUBLISHER / 'audit_reviewable_pr.py'), 'audit',
                                *identity, '--pr', '2'], cwd=self.repo, env=environment,
                               capture_output=True, text=True)
        self.assertEqual(audit.returncode, 0, audit.stderr)
        self.assertEqual(json.loads(audit.stdout)['status'], 'verified')
        ready = subprocess.run([sys.executable, str(PUBLISHER / 'update_reviewable_pr.py'), 'ready',
                                *identity, '--pr', '2', '--review-input', str(self.manifest_path),
                                '--body-template', str(self.template_path), '--review-mode', 'not-required',
                                '--selected-specialists', '[]', '--expected-title-sha256', hashlib.sha256(TITLE.encode()).hexdigest(),
                                '--expected-body-sha256', hashlib.sha256(stored['body'].encode()).hexdigest()],
                               cwd=self.repo, env=environment, capture_output=True, text=True)
        self.assertEqual(ready.returncode, 0, ready.stderr)
        self.assertFalse(json.loads(state_path.read_text())['isDraft'])
        final_audit = subprocess.run([sys.executable, str(PUBLISHER / 'audit_reviewable_pr.py'), 'audit',
                                      *identity, '--pr', '2'], cwd=self.repo, env=environment,
                                     capture_output=True, text=True)
        self.assertEqual(final_audit.returncode, 0, final_audit.stderr)
        self.assertEqual(json.loads(final_audit.stdout)['status'], 'verified')

    def test_writer_holds_an_invented_zero_line_category_in_the_summary(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_validate_change_navigation import badge
        extra = badge('DOC: 0 additions, 0 deletions', 'DOC-%2B0%20%E2%88%920-3F7770')
        self.body = self.body.replace('</summary>', ' ' + extra + '</summary>')
        self.raw['candidate']['body_sha256'] = hashlib.sha256(self.body.encode()).hexdigest()
        self.save()
        self.assertNotEqual(self.writer().returncode, 0)

    def test_writer_holds_an_invented_file_operation_badge_in_the_summary(self):
        extra = '<picture><img alt="BINARY" title="BINARY" src="https://img.shields.io/badge/BINARY-5F6B78?style=flat" height="16"></picture>'
        self.body = self.body.replace('</summary>', ' ' + extra + '</summary>')
        self.raw['candidate']['body_sha256'] = hashlib.sha256(self.body.encode()).hexdigest()
        self.save()
        self.assertNotEqual(self.writer().returncode, 0)

    def test_writer_accepts_history_only_current_stack_row_without_a_category(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_validate_change_navigation import STACK, badge
        zero_files = badge('FILES: 0 added, 0 modified, 0 removed', 'FILES-%2B0%20~0%20%E2%88%920-5F6B78')
        lines = STACK.splitlines()
        for index, line in enumerate(lines):
            if '**← this PR**' in line:
                lines[index] = f'- **[#{TOKEN} — {TITLE}](https://github.com/acme/app/pull/{TOKEN})** **← this PR**<br>' + zero_files
        self.body = '\n'.join(lines).rstrip() + '\n\n' + self.body
        self.raw['stack'] = [
            {'number': 1, 'title': 'feat: base', 'url': 'https://github.com/acme/app/pull/1',
             'current': False, 'metrics': {'IMPL': [1, 0]},
             'file_operations': {'added': 1, 'modified': 0, 'removed': 0, 'moved': 0, 'copied': 0}},
            {'number': TOKEN, 'title': TITLE, 'url': f'https://github.com/acme/app/pull/{TOKEN}',
             'current': True, 'metrics': {},
             'file_operations': {'added': 0, 'modified': 0, 'removed': 0, 'moved': 0, 'copied': 0}},
        ]
        self.raw['candidate']['body_sha256'] = hashlib.sha256(self.body.encode()).hexdigest()
        self.save()
        result = self.writer()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_writer_retains_ordinary_v3_file_diff_validation(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_review_input import DIFF, manifest, reseal
        source = self.repo / 'src/widget.ts'
        source.parent.mkdir()
        source.write_text('one\ntwo\nthree\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'file base')
        self.base = self.git('rev-parse', 'HEAD')
        source.write_text(''.join(f'new {index}\n' for index in range(9)))
        self.git('commit', '-qam', 'ordinary file diff')
        self.head = self.git('rev-parse', 'HEAD')
        raw = manifest(DIFF)
        raw['version'] = 3
        raw['base']['oid'] = self.base
        raw['head']['oid'] = self.head
        self.manifest_path.write_text(json.dumps(reseal(raw)))
        self.body_path.write_text(DIFF)
        result = subprocess.run([sys.executable, str(WRITER), '--repository', 'acme/app', '--pr', '2',
                                 '--title', 'feat: widget', '--review-input', str(self.manifest_path),
                                 '--git-repository', str(self.repo), str(self.body_path)],
                                cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        raw['git_history'] = None
        self.manifest_path.write_text(json.dumps(reseal(raw)))
        result = subprocess.run([sys.executable, str(WRITER), '--repository', 'acme/app', '--pr', '2',
                                 '--title', 'feat: widget', '--review-input', str(self.manifest_path),
                                 '--git-repository', str(self.repo), str(self.body_path)],
                                cwd=self.repo, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)

    def test_publisher_holds_extra_history_summary_content_before_the_forge_boundary(self):
        bin_path = self.root / 'bin'
        bin_path.mkdir()
        marker = self.root / 'forge-reached'
        gh = bin_path / 'gh'
        gh.write_text('#!' + sys.executable + '\nfrom pathlib import Path\nPath(' + repr(str(marker)) + ').touch()\nraise SystemExit(99)\n')
        gh.chmod(0o755)
        environment = dict(os.environ, PATH=str(bin_path) + os.pathsep + os.environ['PATH'],
                           XDG_STATE_HOME=str(self.root / 'state'))
        original = self.body
        for extra in (
            '<a href="https://github.com/acme/app/pull/2/files#diff-invented">invented.txt</a>',
            '[invented.txt](https://github.com/acme/app/pull/2/files#diff-invented)',
            'invented.txt',
        ):
            with self.subTest(extra=extra):
                self.body = original.replace('</summary>', extra + '</summary>')
                self.raw['candidate']['body_sha256'] = hashlib.sha256(self.body.encode()).hexdigest()
                self.save()
                result = subprocess.run([sys.executable, str(PUBLISHER / 'create_reviewable_pr.py'),
                                         '--repository', 'acme/app', '--base', 'main', '--base-oid', self.base,
                                         '--head', 'acme:sync', '--head-oid', self.head, '--head-owner', 'acme',
                                         '--head-repository', 'acme/app-fork', '--title', TITLE,
                                         '--body-template', str(self.template_path), '--review-input', str(self.manifest_path),
                                         '--review-mode', 'not-required', '--selected-specialists', '[]'],
                                        cwd=self.repo, env=environment, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Change navigation is invalid', result.stderr)
                self.assertFalse(marker.exists())

    def test_publisher_holds_missing_history_before_the_forge_boundary(self):
        del self.raw['git_history']
        self.save()
        bin_path = self.root / 'bin'
        bin_path.mkdir()
        marker = self.root / 'forge-reached'
        gh = bin_path / 'gh'
        gh.write_text('#!' + sys.executable + '\nfrom pathlib import Path\nPath(' + repr(str(marker)) + ').touch()\nraise SystemExit(99)\n')
        gh.chmod(0o755)
        environment = dict(os.environ, PATH=str(bin_path) + os.pathsep + os.environ['PATH'],
                           XDG_STATE_HOME=str(self.root / 'state'))
        result = subprocess.run([sys.executable, str(PUBLISHER / 'create_reviewable_pr.py'),
                                 '--repository', 'acme/app', '--base', 'main', '--base-oid', self.base,
                                 '--head', 'acme:sync', '--head-oid', self.head, '--head-owner', 'acme',
                                 '--head-repository', 'acme/app-fork', '--title', TITLE,
                                 '--body-template', str(self.template_path), '--review-input', str(self.manifest_path),
                                 '--review-mode', 'not-required', '--selected-specialists', '[]'],
                                cwd=self.repo, env=environment, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('review input drift', result.stderr)
        self.assertFalse(marker.exists())
