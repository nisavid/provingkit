"""Behavior of the public relation command with an external forge adapter."""

from __future__ import annotations

import importlib.util
import copy
import hashlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'plugins/mergecraft/skills/maintaining-issue-pr-relations/scripts/relation_state.py'


def command_module():
    spec = importlib.util.spec_from_file_location('mergecraft_relation_state', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NoForgeAccess:
    def __getattr__(self, name):
        raise AssertionError(f'unrelated work must not access the forge: {name}')


ISSUE = {'host': 'github.com', 'repository': 'owner/project', 'number': 1, 'id': 'I1'}
PR = {'host': 'github.com', 'repository': 'owner/project', 'number': 2, 'id': 'P1'}


def request(completion='partial', task='task-1'):
    return {'version': 1, 'task_id': task,
            'applicability': {'active': True, 'reason': 'relation-change'},
            'pairs': [{'issue': copy.deepcopy(ISSUE), 'pr': copy.deepcopy(PR),
                       'intent': 'ensure', 'role': 'implementation',
                       'evidence': ['task: reviewed implementation'],
                       'completion': completion,
                       'completion_evidence': ['task: all Issue gates met'] if completion == 'complete' else [],
                       'disclosure_authorized': False}]}


class FakeForge:
    """External forge double; the public command owns all domain behavior."""
    def __init__(self):
        repository = {'id': 'R1', 'name': 'owner/project', 'visibility': 'PRIVATE', 'default_branch': 'main'}
        self.entities = {
            'I1': {**ISSUE, 'kind': 'Issue', 'repository': repository,
                   'url': 'https://github.com/owner/project/issues/1', 'body': 'Issue body', 'title': 'Issue', 'state': 'OPEN'},
            'P1': {**PR, 'kind': 'PullRequest', 'repository': repository,
                   'url': 'https://github.com/owner/project/pull/2', 'body': 'PR body', 'title': 'PR',
                   'state': 'OPEN', 'is_draft': False, 'base_ref': 'main', 'head_oid': 'a' * 40},
        }
        self.connections = {key: {'all': [], 'manual': [], 'detected': []} for key in self.entities}

    def read_entity(self, reference):
        return copy.deepcopy(self.entities[reference['id']])

    def read_connection_page(self, entity, provenance, cursor):
        values = self.connections[entity['id']][provenance]
        start = int(cursor or 0)
        end = start + 2
        return {'nodes': [{'id': item} for item in values[start:end]], 'total_count': len(values),
                'page_info': {'has_next_page': end < len(values),
                              'end_cursor': str(end) if end < len(values) else None}}


    def change_native(self, operation, issue, prs):
        for pr in prs:
            for entity_id, other_id in ((issue['id'], pr['id']), (pr['id'], issue['id'])):
                for provenance in ('all', 'manual'):
                    values = self.connections[entity_id][provenance]
                    if operation == 'add' and other_id not in values:
                        values.append(other_id)
                    elif operation == 'remove' and other_id in values:
                        values.remove(other_id)
        return {'data': {operation + 'CloseIssueReferences': {'issue': {'id': issue['id']}}}}


def with_existing_ledgers(forge, desired):
    desired = copy.deepcopy(desired)
    desired['body_edits'] = []
    for entity_id, url in [('I1', 'https://github.com/owner/project/pull/2'), ('P1', 'https://github.com/owner/project/issues/1')]:
        body = f'Contributions: {url}'
        forge.entities[entity_id]['body'] = body
        desired['body_edits'].append({'entity_id': entity_id, 'expected_body_sha256': hashlib.sha256(body.encode()).hexdigest(), 'start_byte': 0, 'end_byte': len(body.encode()), 'before': body, 'replacement': body, 'candidate_body': body, 'writer': 'writing-github-issue-and-pr-markdown' if entity_id == 'I1' else 'writing-reviewable-pr-descriptions', 'evidence': ['task: existing complete ledger retained']})
    return desired


def with_two_pr_ledgers(forge):
    desired = with_existing_ledgers(forge, request('complete'))
    forge.entities['P2'] = {**copy.deepcopy(forge.entities['P1']), 'id': 'P2', 'number': 3, 'url': 'https://github.com/owner/project/pull/3'}
    forge.connections['P2'] = {'all': [], 'manual': [], 'detected': []}
    pair = copy.deepcopy(desired['pairs'][0])
    pair['pr'].update(id='P2', number=3)
    desired['pairs'].append(pair)
    forge.entities['I1']['body'] += ' https://github.com/owner/project/pull/3'
    desired['body_edits'] = []
    for entity_id in ('I1', 'P1', 'P2'):
        body = forge.entities[entity_id]['body']
        desired['body_edits'].append({'entity_id': entity_id, 'expected_body_sha256': hashlib.sha256(body.encode()).hexdigest(), 'start_byte': 0, 'end_byte': len(body.encode()), 'before': body, 'replacement': body, 'candidate_body': body, 'writer': 'writing-github-issue-and-pr-markdown' if entity_id == 'I1' else 'writing-reviewable-pr-descriptions', 'evidence': ['complete ledger retained']})
    return desired


def authorize(plan):
    return {'version': 1, 'plan': plan, 'authorization': {
        'plan_sha256': plan['plan_sha256'],
        'effect_ids': [item['effect_id'] for item in plan['effects']]}}


class PartialBatchForge(FakeForge):
    def __init__(self):
        super().__init__()
        self.batches = []
        self.read_ids = []

    def read_entity(self, reference):
        self.read_ids.append(reference['id'])
        return super().read_entity(reference)

    def change_native(self, operation, issue, prs):
        self.batches.append([pr['id'] for pr in prs])
        if len(self.batches) == 1:
            super().change_native(operation, issue, prs[:1])
            return {'data': {operation + 'CloseIssueReferences': {'issue': {'id': issue['id']}}},
                    'errors': [{'type': 'UNPROCESSABLE'}]}
        return super().change_native(operation, issue, prs)


class RelationCommandTests(unittest.TestCase):
    def test_unrelated_edit_skips_without_forge_or_cache_access(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'absent-state'
            result = command_module().execute(
                'observe',
                {'version': 1, 'task_id': 'task-1',
                 'applicability': {'active': False, 'reason': 'unrelated-edit'},
                 'pairs': []},
                forge=NoForgeAccess(), state_root=state,
                now='2026-09-17T12:00:00Z',
            )
            self.assertEqual(result['status'], 'no-op')
            self.assertEqual(result['read_counts'], {'entities': 0, 'connection_pages': 0, 'settings': 0, 'external_read_requests': 0, 'external_write_requests': 0})
            self.assertFalse(state.exists())


    def test_skip_cannot_discard_pending_relation_work(self):
        with tempfile.TemporaryDirectory() as directory:
            result = command_module().execute(
                'observe',
                {'version': 1, 'task_id': 'task-1',
                 'applicability': {'active': False, 'reason': 'unrelated-edit'},
                 'pairs': [{'intent': 'ensure'}]},
                forge=NoForgeAccess(), state_root=Path(directory),
                now='2026-09-17T12:00:00Z',
            )
            self.assertEqual(result['status'], 'blocked')
            self.assertEqual(result['reason'], 'inactive-with-pending-work')


    def test_complete_fix_observation_paginates_provenance_without_setting_acquisition(self):
        forge = FakeForge()
        forge.connections['P1']['all'] = ['I2', 'I3', 'I4']
        forge.connections['P1']['manual'] = ['I2', 'I3', 'I4']
        with tempfile.TemporaryDirectory() as directory:
            result = command_module().execute('observe', request('complete'), forge=forge,
                                              state_root=Path(directory), now='2026-09-17T12:00:00Z')
            self.assertEqual(result['status'], 'observed')
            self.assertEqual(result['entities']['P1']['relations']['manual'], ['I2', 'I3', 'I4'])
            self.assertEqual(result['read_counts'], {'entities': 2, 'connection_pages': 8, 'settings': 0, 'external_read_requests': 0, 'external_write_requests': 0})
            self.assertEqual(result['setting_requests'], [])


    def test_missing_setting_requests_one_ui_observation_per_repository_per_task(self):
        with tempfile.TemporaryDirectory() as directory:
            api = command_module()
            first = api.execute('observe', request(), forge=FakeForge(), state_root=Path(directory), now='2026-09-17T12:00:00Z')
            resumed = api.execute('observe', request(), forge=FakeForge(), state_root=Path(directory), now='2026-10-30T12:00:00Z')
            self.assertEqual(first['setting_requests'], [{'host': 'github.com', 'repository_id': 'R1', 'repository': 'owner/project', 'source': 'github-settings-ui'}])
            self.assertEqual(resumed['setting_requests'], [])
            self.assertIsNone(resumed['settings']['github.com:R1']['auto_close'])
            self.assertEqual(resumed['read_counts']['settings'], 0)


    def test_setting_age_survives_task_resume_and_cross_task_cache_hits(self):
        observed = {'host': 'github.com', 'repository_id': 'R1', 'repository': 'owner/project',
                    'auto_close': False, 'observed_at': '2026-09-01T12:00:00Z',
                    'source': 'github-settings-ui', 'evidence': ['task: settings checkbox unchecked']}
        with tempfile.TemporaryDirectory() as directory:
            api = command_module()
            first_request = request()
            first_request['setting_observations'] = [observed]
            first = api.execute('observe', first_request, forge=FakeForge(), state_root=Path(directory), now='2026-09-01T12:00:00Z')
            resumed = api.execute('observe', request(), forge=FakeForge(), state_root=Path(directory), now='2026-11-01T12:00:00Z')
            hit = api.execute('observe', request(task='task-2'), forge=FakeForge(), state_root=Path(directory), now='2026-09-20T12:00:00Z')
            expired = api.execute('observe', request(task='task-3'), forge=FakeForge(), state_root=Path(directory), now='2026-10-02T12:00:00Z')
            forever_request = request(task='task-4')
            forever_request['setting_ttl_days'] = None
            forever = api.execute('observe', forever_request, forge=FakeForge(), state_root=Path(directory), now='2027-09-01T12:00:00Z')
            for result in (first, resumed, hit, forever):
                self.assertIs(result['settings']['github.com:R1']['auto_close'], False)
                self.assertEqual(result['settings']['github.com:R1']['observed_at'], '2026-09-01T12:00:00Z')
                self.assertEqual(result['setting_requests'], [])
            self.assertEqual(resumed['settings']['github.com:R1']['provenance'], 'task-cache')
            self.assertEqual(hit['settings']['github.com:R1']['provenance'], 'persistent-cache')
            self.assertIsNone(expired['settings']['github.com:R1']['auto_close'])
            self.assertEqual(len(expired['setting_requests']), 1)


    def test_explicit_invalidation_refreshes_once_without_rereading_supplied_workflow_facts(self):
        with tempfile.TemporaryDirectory() as directory:
            api = command_module()
            first_request = request()
            first_request['setting_observations'] = [{'host': 'github.com', 'repository_id': 'R1', 'repository': 'owner/project', 'auto_close': False, 'observed_at': '2026-09-01T12:00:00Z', 'source': 'github-settings-ui', 'evidence': ['task: checkbox unchecked']}]
            first = api.execute('observe', first_request, forge=FakeForge(), state_root=Path(directory), now='2026-09-01T12:00:00Z')
            refreshed_request = request()
            refreshed_request['entity_observations'] = first['entities']
            refreshed_request['invalidate_settings'] = [{'host': 'github.com', 'repository_id': 'R1', 'reason': 'explicit-refresh', 'event_id': 'refresh-1'}]
            refreshed = api.execute('observe', refreshed_request, forge=NoForgeAccess(), state_root=Path(directory), now='2026-09-02T12:00:00Z')
            resumed = api.execute('observe', refreshed_request, forge=NoForgeAccess(), state_root=Path(directory), now='2026-09-02T13:00:00Z')
            self.assertEqual(refreshed['read_counts'], {'entities': 0, 'connection_pages': 0, 'settings': 0, 'external_read_requests': 0, 'external_write_requests': 0})
            self.assertEqual(len(refreshed['setting_requests']), 1)
            self.assertEqual(resumed['setting_requests'], [])
            self.assertIsNone(refreshed['settings']['github.com:R1']['auto_close'])
            self.assertNotEqual(refreshed['settings']['github.com:R1']['generation'], first['settings']['github.com:R1']['generation'])


    def test_plan_keeps_partial_contribution_in_both_ledgers_and_uses_issue_setting(self):
        with tempfile.TemporaryDirectory() as directory:
            api = command_module()
            desired = request()
            desired['setting_observations'] = [{'host': 'github.com', 'repository_id': 'R1', 'repository': 'owner/project', 'auto_close': False, 'observed_at': '2026-09-17T12:00:00Z', 'source': 'github-settings-ui', 'evidence': ['task: checkbox unchecked']}]
            observed = api.execute('observe', desired, forge=FakeForge(), state_root=Path(directory), now='2026-09-17T12:00:00Z')
            plan = api.execute('plan', observed, forge=NoForgeAccess(), state_root=Path(directory))
            self.assertEqual(plan['effects'][0]['kind'], 'native-add')
            self.assertEqual(plan['effects'][0]['issue_id'], 'I1')
            self.assertEqual(plan['effects'][0]['pr_ids'], ['P1'])
            self.assertEqual(plan['ledgers']['I1'], [{'entity_id': 'P1', 'url': 'https://github.com/owner/project/pull/2', 'role': 'implementation'}])
            self.assertEqual(plan['ledgers']['P1'], [{'entity_id': 'I1', 'url': 'https://github.com/owner/project/issues/1', 'role': 'implementation'}])
            self.assertEqual({h['entity_id'] for h in plan['handoffs']}, {'I1', 'P1'})
            self.assertEqual(plan['read_counts'], {'entities': 0, 'connection_pages': 0, 'settings': 0, 'external_read_requests': 0, 'external_write_requests': 0})
            self.assertEqual(plan, api.execute('plan', observed, forge=NoForgeAccess()))


    def test_manual_capacity_blocks_new_native_edge_without_dropping_ledger_contribution(self):
        forge = FakeForge()
        forge.connections['P1']['all'] = [f'other-{i}' for i in range(10)]
        forge.connections['P1']['manual'] = [f'other-{i}' for i in range(10)]
        with tempfile.TemporaryDirectory() as directory:
            api = command_module()
            observed = api.execute('observe', request('complete'), forge=forge, state_root=Path(directory))
            plan = api.execute('plan', observed)
            self.assertEqual(plan['effects'], [])
            self.assertEqual(plan['omitted_native'], [{'issue_id': 'I1', 'pr_id': 'P1', 'reason': 'manual-capacity'}])
            self.assertEqual(plan['ledgers']['P1'][0]['entity_id'], 'I1')
            self.assertIn('native-selection', {item['kind'] for item in plan['handoffs']})


    def test_writer_candidates_preserve_exact_issue_bytes_and_make_pr_publication_a_handoff(self):
        forge = FakeForge()
        forge.entities['I1']['body'] = 'Préface\r\nOLD\r\nTail'
        prefix = 'Préface\r\n'
        issue_replacement = '[owner/project#2](https://github.com/owner/project/pull/2)'
        issue_candidate = prefix + issue_replacement + '\r\nTail'
        pr_candidate = '[owner/project#1](https://github.com/owner/project/issues/1)'
        desired = request('complete')
        desired['body_edits'] = [
            {'entity_id': 'I1', 'expected_body_sha256': hashlib.sha256(forge.entities['I1']['body'].encode()).hexdigest(),
             'start_byte': len(prefix.encode()), 'end_byte': len(prefix.encode()) + 3, 'before': 'OLD',
             'replacement': issue_replacement, 'candidate_body': issue_candidate,
             'writer': 'writing-github-issue-and-pr-markdown', 'evidence': ['task: exact writer output']},
            {'entity_id': 'P1', 'expected_body_sha256': hashlib.sha256(b'PR body').hexdigest(),
             'start_byte': 0, 'end_byte': 7, 'before': 'PR body', 'replacement': pr_candidate,
             'candidate_body': pr_candidate, 'writer': 'writing-reviewable-pr-descriptions', 'evidence': ['task: exact writer output']},
        ]
        with tempfile.TemporaryDirectory() as directory:
            api = command_module()
            observed = api.execute('observe', desired, forge=forge, state_root=Path(directory))
            plan = api.execute('plan', observed)
            body_effect = next(effect for effect in plan['effects'] if effect['kind'] == 'issue-body')
            self.assertEqual(body_effect['candidate_body'], issue_candidate)
            self.assertEqual([effect['kind'] for effect in plan['effects']], ['issue-body', 'native-add'])
            handoff = next(item for item in plan['handoffs'] if item['kind'] == 'pr-publisher')
            self.assertEqual(handoff['candidate_body'], pr_candidate)
            self.assertEqual(handoff['operation'], 'pr-relation-ledger-write')
            self.assertEqual(handoff['preimage']['state'], 'OPEN')
            self.assertEqual(handoff['target']['repository_id'], 'R1')
            bad = copy.deepcopy(observed)
            bad['request']['body_edits'][0]['candidate_body'] = issue_candidate + '!'
            self.assertEqual(api.execute('plan', bad)['reason'], 'candidate-does-not-match-authorized-span')


    def test_reconcile_adds_only_authorized_native_edge_and_is_safe_to_resume(self):
        forge = FakeForge()
        desired = with_existing_ledgers(forge, request('complete'))
        with tempfile.TemporaryDirectory() as directory:
            api = command_module()
            observed = api.execute('observe', desired, forge=forge, state_root=Path(directory))
            plan = api.execute('plan', observed)
            instruction = {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': [effect['effect_id'] for effect in plan['effects']]}}
            result = api.execute('reconcile', instruction, forge=forge, state_root=Path(directory))
            self.assertEqual(result['status'], 'verified')
            after = api.execute('observe', desired, forge=forge, state_root=Path(directory))
            self.assertEqual(after['entities']['I1']['relations']['manual'], ['P1'])
            self.assertEqual(after['entities']['P1']['relations']['manual'], ['I1'])
            self.assertEqual(after['entities']['I1']['state'], 'OPEN')
            resumed = api.execute('reconcile', instruction, forge=forge, state_root=Path(directory))
            self.assertEqual(resumed['status'], 'no-op')


    def test_invalidated_setting_blocks_old_plan_before_any_forge_read(self):
        forge = FakeForge()
        desired = with_existing_ledgers(forge, request())
        desired['setting_observations'] = [{'host': 'github.com', 'repository_id': 'R1', 'repository': 'owner/project', 'auto_close': False, 'observed_at': '2026-09-17T12:00:00Z', 'source': 'github-settings-ui', 'evidence': ['task: checkbox unchecked']}]
        with tempfile.TemporaryDirectory() as directory:
            api = command_module()
            observed = api.execute('observe', desired, forge=forge, state_root=Path(directory), now='2026-09-17T12:00:00Z')
            plan = api.execute('plan', observed)
            refresh = request()
            refresh['entity_observations'] = observed['entities']
            refresh['invalidate_settings'] = [{'host': 'github.com', 'repository_id': 'R1', 'reason': 'observed-change', 'event_id': 'change-1'}]
            api.execute('observe', refresh, forge=NoForgeAccess(), state_root=Path(directory), now='2026-09-17T13:00:00Z')
            instruction = {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': [effect['effect_id'] for effect in plan['effects']]}}
            result = api.execute('reconcile', instruction, forge=NoForgeAccess(), state_root=Path(directory))
            self.assertEqual(result['status'], 'blocked')
            self.assertEqual(result['reason'], 'setting-observation-invalidated')
            self.assertEqual(result['read_counts'], {'entities': 0, 'connection_pages': 0, 'settings': 0, 'external_read_requests': 0, 'external_write_requests': 0})


    def test_body_success_then_graphql_errors_with_data_reports_partial_without_retry(self):
        class RefusingForge(FakeForge):
            def write_issue_body(self, entity, candidate_body):
                self.entities[entity['id']]['body'] = candidate_body
                return {'ok': True}

            def change_native(self, operation, issue, prs):
                return {'data': {'addCloseIssueReferences': {'issue': {'id': issue['id']}}},
                        'errors': [{'type': 'UNPROCESSABLE', 'message': 'Pull request exceeds manual reference limit'}]}

        forge = RefusingForge()
        desired = with_existing_ledgers(forge, request('complete'))
        desired['body_edits'][0]['replacement'] += ' — implementation'
        desired['body_edits'][0]['candidate_body'] += ' — implementation'
        with tempfile.TemporaryDirectory() as directory:
            api = command_module()
            observed = api.execute('observe', desired, forge=forge, state_root=Path(directory))
            plan = api.execute('plan', observed)
            instruction = {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': [effect['effect_id'] for effect in plan['effects']]}}
            result = api.execute('reconcile', instruction, forge=forge, state_root=Path(directory))
            self.assertEqual(result['status'], 'partial')
            self.assertEqual([item['status'] for item in result['effects']], ['verified', 'blocked'])
            after = api.execute('observe', request('complete'), forge=forge, state_root=Path(directory))
            self.assertEqual(after['entities']['I1']['body'], desired['body_edits'][0]['candidate_body'])
            self.assertEqual(after['entities']['I1']['relations']['all'], [])
            self.assertEqual(after['entities']['I1']['state'], 'OPEN')


    def test_partial_native_batch_observation_authorizes_only_the_exact_remaining_effect(self):
        for operation in ('add', 'remove'):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as directory:
                api, forge = command_module(), PartialBatchForge()
                desired = with_two_pr_ledgers(forge)
                if operation == 'remove':
                    FakeForge.change_native(forge, 'add', forge.entities['I1'], [forge.entities['P1'], forge.entities['P2']])
                    for pair in desired['pairs']:
                        pair['intent'] = 'unlink-native'
                plan = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
                self.assertEqual(api.execute('reconcile', authorize(plan), forge=forge, state_root=directory)['status'], 'partial')
                observed = api.execute('reconcile', {**authorize(plan), 'mode': 'observe'}, forge=forge, state_root=directory)
                self.assertEqual(observed['status'], 'needs-input')
                self.assertEqual(observed['effects'][0]['reason'], 'prior-attempt-observed-partial')
                remaining_request = copy.deepcopy(desired)
                remaining_request['pairs'] = desired['pairs'][1:]
                remaining_request['body_edits'] = [edit for edit in desired['body_edits'] if edit['entity_id'] != 'P1']
                remaining = api.execute('plan', api.execute('observe', remaining_request, forge=forge, state_root=directory))
                self.assertEqual(remaining['effects'][0]['pr_ids'], ['P2'])
                self.assertEqual(api.execute('reconcile', authorize(remaining), forge=forge, state_root=directory)['status'], 'unknown')
                receipt = api.execute('reconcile', {**authorize(remaining), 'mode': 'observe'}, forge=forge, state_root=directory)['effects'][0]
                self.assertEqual(receipt['applied_pr_ids'], ['P1'])
                self.assertEqual(receipt['remaining_pr_ids'], ['P2'])
                self.assertEqual(receipt['original_endpoint_ids'], ['I1', 'P1', 'P2'])
                renewed = authorize(remaining)
                renewed['authorization']['renewals'] = [{'effect_id': receipt['remaining_effect_id'], **{key: receipt[key] for key in ('attempt_id', 'receipt_id', 'receipt_sha256')}}]
                tampered = copy.deepcopy(renewed)
                tampered['authorization']['renewals'][0]['receipt_sha256'] = '0' * 64
                self.assertEqual(api.execute('reconcile', tampered, forge=forge, state_root=directory)['status'], 'blocked')
                self.assertEqual(api.execute('reconcile', authorize(plan), forge=forge, state_root=directory)['status'], 'unknown')
                self.assertEqual(forge.batches, [['P1', 'P2']])
                result = api.execute('reconcile', renewed, forge=forge, state_root=directory)
                self.assertEqual(result['status'], 'verified')
                self.assertEqual(forge.batches, [['P1', 'P2'], ['P2']])
                self.assertEqual(forge.connections['I1']['manual'], ['P1', 'P2'] if operation == 'add' else [])
                self.assertEqual(api.execute('reconcile', authorize(plan), forge=forge, state_root=directory)['status'], 'no-op')


    def test_partial_recovery_rereads_completed_endpoint_and_rejects_unrelated_drift(self):
        for field in ('body', 'title', 'head_oid'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                api, forge = command_module(), PartialBatchForge()
                desired = with_two_pr_ledgers(forge)
                original = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
                api.execute('reconcile', authorize(original), forge=forge, state_root=directory)
                desired['pairs'] = desired['pairs'][1:]
                desired['body_edits'] = [edit for edit in desired['body_edits'] if edit['entity_id'] != 'P1']
                remaining = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
                receipt = api.execute('reconcile', {**authorize(remaining), 'mode': 'observe'}, forge=forge, state_root=directory)['effects'][0]
                renewed = authorize(remaining)
                renewed['authorization']['renewals'] = [{'effect_id': receipt['remaining_effect_id'], **{key: receipt[key] for key in ('attempt_id', 'receipt_id', 'receipt_sha256')}}]
                forge.entities['P1'][field] += ' changed'
                forge.read_ids.clear()
                result = api.execute('reconcile', renewed, forge=forge, state_root=directory)
                self.assertEqual(result['status'], 'unknown')
                self.assertIn('P1', forge.read_ids)
                self.assertEqual(forge.batches, [['P1', 'P2']])


    def test_interrupted_remainder_retains_a_new_attempt_without_replaying_original_batch(self):
        class InterruptedRemainderForge(PartialBatchForge):
            def change_native(self, operation, issue, prs):
                if len(self.batches) == 1:
                    self.batches.append([pr['id'] for pr in prs])
                    raise KeyboardInterrupt('process interrupted after remainder admission')
                return super().change_native(operation, issue, prs)
        api, forge = command_module(), InterruptedRemainderForge()
        with tempfile.TemporaryDirectory() as directory:
            desired = with_two_pr_ledgers(forge)
            original = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
            api.execute('reconcile', authorize(original), forge=forge, state_root=directory)
            remaining = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
            partial_receipt = api.execute('reconcile', {**authorize(remaining), 'mode': 'observe'}, forge=forge, state_root=directory)['effects'][0]
            renewed = authorize(remaining)
            renewed['authorization']['renewals'] = [{'effect_id': partial_receipt['remaining_effect_id'], **{key: partial_receipt[key] for key in ('attempt_id', 'receipt_id', 'receipt_sha256')}}]
            with self.assertRaises(KeyboardInterrupt):
                api.execute('reconcile', renewed, forge=forge, state_root=directory)
            api = command_module()
            self.assertEqual(api.execute('reconcile', renewed, forge=forge, state_root=directory)['status'], 'unknown')
            self.assertEqual(forge.batches, [['P1', 'P2'], ['P2']])
            receipt = api.execute('reconcile', {**authorize(remaining), 'mode': 'observe'}, forge=forge, state_root=directory)['effects'][0]
            self.assertEqual(receipt['reason'], 'prior-attempt-observed-preimage')
            self.assertNotEqual(receipt['attempt_id'], partial_receipt['attempt_id'])
            renewed['authorization']['renewals'] = [{key: receipt[key] for key in ('effect_id', 'attempt_id', 'receipt_id', 'receipt_sha256')}]
            self.assertEqual(api.execute('reconcile', renewed, forge=forge, state_root=directory)['status'], 'verified')
            self.assertEqual(forge.batches, [['P1', 'P2'], ['P2'], ['P2']])
            self.assertEqual(api.execute('reconcile', authorize(original), forge=forge, state_root=directory)['status'], 'no-op')


    def test_setting_change_during_partial_recovery_blocks_renewed_native_admission(self):
        api = command_module()
        with tempfile.TemporaryDirectory() as directory:
            class RacingRemainderForge(PartialBatchForge):
                trigger = False
                def read_entity(self, reference):
                    value = super().read_entity(reference)
                    if self.trigger and reference['id'] == 'P1':
                        self.trigger = False
                        invalidation = {'version': 1, 'task_id': 'other-task', 'applicability': {'active': True, 'reason': 'setting-refresh'}, 'pairs': [], 'invalidate_settings': [{'host': 'github.com', 'repository_id': 'R1', 'reason': 'observed-change', 'event_id': 'during-remainder-preflight'}]}
                        api.execute('observe', invalidation, forge=NoForgeAccess(), state_root=directory, now='2026-09-17T12:01:00Z')
                    return value
            forge = RacingRemainderForge()
            desired = with_two_pr_ledgers(forge)
            for pair in desired['pairs']:
                pair['completion'] = 'partial'
                pair['completion_evidence'] = []
            desired['setting_observations'] = [{'host': 'github.com', 'repository_id': 'R1', 'auto_close': False, 'observed_at': '2026-09-17T12:00:00Z', 'source': 'github-settings-ui', 'evidence': ['checkbox unchecked']}]
            original = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory, now='2026-09-17T12:00:00Z'))
            api.execute('reconcile', authorize(original), forge=forge, state_root=directory)
            desired['pairs'] = desired['pairs'][1:]
            desired['body_edits'] = [edit for edit in desired['body_edits'] if edit['entity_id'] != 'P1']
            remaining = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory, now='2026-09-17T12:00:00Z'))
            receipt = api.execute('reconcile', {**authorize(remaining), 'mode': 'observe'}, forge=forge, state_root=directory)['effects'][0]
            renewed = authorize(remaining)
            renewed['authorization']['renewals'] = [{'effect_id': receipt['remaining_effect_id'], **{key: receipt[key] for key in ('attempt_id', 'receipt_id', 'receipt_sha256')}}]
            forge.trigger = True
            result = api.execute('reconcile', renewed, forge=forge, state_root=directory)
            self.assertEqual(result['status'], 'blocked')
            self.assertEqual(result['effects'][0]['reason'], 'setting-observation-invalidated')
            self.assertEqual(forge.batches, [['P1', 'P2']])
            recovery = api.execute('reconcile', {**authorize(remaining), 'mode': 'observe'}, forge=forge, state_root=directory)
            self.assertEqual(recovery['status'], 'needs-input')
            self.assertEqual(recovery['effects'][0]['reason'], 'prior-attempt-observed-partial')


    def test_read_only_recovery_survives_setting_invalidation_but_write_does_not(self):
        class UncertainForge(FakeForge):
            writes = 0
            def change_native(self, operation, issue, prs):
                self.writes += 1
                raise TimeoutError('response lost')
        api, forge = command_module(), UncertainForge()
        desired = with_existing_ledgers(forge, request())
        desired['setting_observations'] = [{'host': 'github.com', 'repository_id': 'R1', 'auto_close': False, 'observed_at': '2026-09-17T12:00:00Z', 'source': 'github-settings-ui', 'evidence': ['checkbox unchecked']}]
        with tempfile.TemporaryDirectory() as directory:
            plan = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory, now='2026-09-17T12:00:00Z'))
            instruction = {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': [item['effect_id'] for item in plan['effects']]}}
            self.assertEqual(api.execute('reconcile', instruction, forge=forge, state_root=directory)['status'], 'unknown')
            refresh = {'version': 1, 'task_id': 'refresh-task', 'applicability': {'active': True, 'reason': 'setting-refresh'}, 'pairs': [], 'invalidate_settings': [{'host': 'github.com', 'repository_id': 'R1', 'reason': 'explicit-refresh', 'event_id': 'after-timeout'}]}
            api.execute('observe', refresh, forge=NoForgeAccess(), state_root=directory, now='2026-09-17T12:01:00Z')
            recovered = api.execute('reconcile', {**instruction, 'mode': 'observe'}, forge=forge, state_root=directory)
            self.assertEqual(recovered['status'], 'needs-input')
            self.assertEqual(recovered['effects'][0]['reason'], 'prior-attempt-observed-preimage')
            self.assertEqual(forge.writes, 1)
            self.assertEqual(api.execute('reconcile', instruction, forge=NoForgeAccess(), state_root=directory)['reason'], 'setting-observation-invalidated')


    def test_setting_invalidation_during_remote_preflight_blocks_native_admission(self):
        api = command_module()
        with tempfile.TemporaryDirectory() as directory:
            class RacingForge(FakeForge):
                trigger = False
                writes = 0
                def read_entity(self, reference):
                    value = super().read_entity(reference)
                    if self.trigger:
                        self.trigger = False
                        invalidation = {'version': 1, 'task_id': 'other-task', 'applicability': {'active': True, 'reason': 'setting-refresh'}, 'pairs': [], 'invalidate_settings': [{'host': 'github.com', 'repository_id': 'R1', 'reason': 'observed-change', 'event_id': 'during-preflight'}]}
                        self.invalidated = api.execute('observe', invalidation, forge=NoForgeAccess(), state_root=directory, now='2026-09-17T12:01:00Z')
                    return value
                def change_native(self, operation, issue, prs):
                    self.writes += 1
                    return super().change_native(operation, issue, prs)
            forge = RacingForge()
            desired = with_existing_ledgers(forge, request())
            desired['setting_observations'] = [{'host': 'github.com', 'repository_id': 'R1', 'auto_close': False, 'observed_at': '2026-09-17T12:00:00Z', 'source': 'github-settings-ui', 'evidence': ['checkbox unchecked']}]
            plan = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory, now='2026-09-17T12:00:00Z'))
            instruction = {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': [item['effect_id'] for item in plan['effects']]}}
            forge.trigger = True
            result = api.execute('reconcile', instruction, forge=forge, state_root=directory)
            self.assertEqual(forge.invalidated['status'], 'observed')
            self.assertEqual(result['status'], 'blocked')
            self.assertEqual(forge.writes, 0)
            self.assertEqual(result['effects'][0]['reason'], 'setting-observation-invalidated')


    def test_invalidation_rejects_replayed_old_observation_until_a_new_ui_check(self):
        api, forge = command_module(), FakeForge()
        desired = request()
        old = {'host': 'github.com', 'repository_id': 'R1', 'auto_close': False, 'observed_at': '2026-09-17T12:00:00Z', 'source': 'github-settings-ui', 'evidence': ['checkbox unchecked']}
        desired['setting_observations'] = [old]
        with tempfile.TemporaryDirectory() as directory:
            api.execute('observe', desired, forge=forge, state_root=directory, now='2026-09-17T12:00:00Z')
            desired['invalidate_settings'] = [{'host': 'github.com', 'repository_id': 'R1', 'reason': 'explicit-refresh', 'event_id': 'refresh-once'}]
            invalidated = api.execute('observe', desired, forge=forge, state_root=directory, now='2026-09-17T12:01:00Z')
            self.assertIsNone(invalidated['settings']['github.com:R1']['auto_close'])
            self.assertEqual(len(invalidated['setting_requests']), 1)
            replay = api.execute('observe', desired, forge=forge, state_root=directory, now='2026-09-17T12:02:00Z')
            self.assertIsNone(replay['settings']['github.com:R1']['auto_close'])
            self.assertEqual(replay['setting_requests'], [])
            desired['setting_observations'] = [{**old, 'observed_at': '2026-09-17T12:02:30Z'}]
            fresh = api.execute('observe', desired, forge=forge, state_root=directory, now='2026-09-17T12:03:00Z')
            self.assertFalse(fresh['settings']['github.com:R1']['auto_close'])
            self.assertEqual(fresh['setting_requests'], [])


    def test_unavailable_ui_observation_is_memoized_only_for_the_current_task(self):
        desired = request()
        desired['setting_observations'] = [{'host': 'github.com', 'repository_id': 'R1', 'auto_close': None, 'observed_at': '2026-09-17T12:00:00Z', 'source': 'github-settings-ui', 'evidence': ['UI unavailable in this task']}]
        with tempfile.TemporaryDirectory() as directory:
            api = command_module()
            first = api.execute('observe', desired, forge=FakeForge(), state_root=directory, now='2026-09-17T12:00:00Z')
            self.assertEqual(first['setting_requests'], [])
            same = api.execute('observe', request(), forge=FakeForge(), state_root=directory, now='2026-09-17T13:00:00Z')
            self.assertEqual(same['setting_requests'], [])
            other = api.execute('observe', request(task='another-task'), forge=FakeForge(), state_root=directory, now='2026-09-17T13:00:00Z')
            self.assertEqual(len(other['setting_requests']), 1)
            self.assertIsNone(other['settings']['github.com:R1']['auto_close'])


    def test_receipt_storage_failure_after_a_verified_write_reports_unknown_attempted(self):
        class StorageFailureForge(FakeForge):
            def change_native(self, operation, issue, prs):
                result = super().change_native(operation, issue, prs)
                (self.state_root / 'settings.json.pending').mkdir()
                return result
        api, forge = command_module(), StorageFailureForge()
        with tempfile.TemporaryDirectory() as directory:
            forge.state_root = Path(directory)
            desired = with_existing_ledgers(forge, request('complete'))
            plan = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
            instruction = {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': [item['effect_id'] for item in plan['effects']]}}
            result = api.execute('reconcile', instruction, forge=forge, state_root=directory)
            self.assertEqual(result['status'], 'unknown')
            self.assertTrue(result['effects'][0]['mutation_attempted'])
            self.assertEqual(result['effects'][0]['reason'], 'attempt-settlement-unavailable')
            self.assertEqual(forge.connections['I1']['manual'], ['P1'])


    def test_replanning_after_unrelated_drift_cannot_bypass_pending_attempt_ownership(self):
        class UncertainForge(FakeForge):
            attempts = 0
            def change_native(self, operation, issue, prs):
                self.attempts += 1
                raise TimeoutError('response lost')
        api, forge = command_module(), UncertainForge()
        with tempfile.TemporaryDirectory() as directory:
            desired = with_existing_ledgers(forge, request('complete'))
            plan = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
            def instruction(plan):
                return {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': [item['effect_id'] for item in plan['effects']]}}
            api.execute('reconcile', instruction(plan), forge=forge, state_root=directory)
            forge.entities['I1']['body'] += ' Human note.'
            edit = desired['body_edits'][0]
            edit['before'] = edit['replacement'] = edit['candidate_body'] = forge.entities['I1']['body']
            edit['end_byte'] = len(edit['before'].encode())
            edit['expected_body_sha256'] = hashlib.sha256(edit['before'].encode()).hexdigest()
            fresh_plan = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
            resumed = api.execute('reconcile', instruction(fresh_plan), forge=forge, state_root=directory)
            self.assertEqual(resumed['status'], 'unknown')
            self.assertEqual(forge.attempts, 1)
            receipt = api.execute('reconcile', {**instruction(fresh_plan), 'mode': 'observe'}, forge=forge, state_root=directory)['effects'][0]
            self.assertEqual(receipt['reason'], 'prior-attempt-observed-preimage')


    def test_supplied_provenance_requires_real_distinct_node_ids_in_every_mode(self):
        api = command_module()
        with tempfile.TemporaryDirectory() as directory:
            observed = api.execute('observe', request('complete'), forge=FakeForge(), state_root=directory)
            supplied = request('complete')
            supplied['entity_observations'] = observed['entities']
            supplied['entity_observations']['I1']['relations'] = {'all': [None], 'manual': [None], 'detected': []}
            rejected = api.execute('observe', supplied, forge=NoForgeAccess(), state_root=directory)
            self.assertEqual(rejected['status'], 'blocked')
            self.assertEqual(rejected['reason'], 'invalid-connection-node')


    def test_publisher_postimage_verification_catches_new_closing_keyword_edges(self):
        api, forge = command_module(), FakeForge()
        desired = with_existing_ledgers(forge, request())
        desired['body_edits'][1]['replacement'] += ' Closes #1.'
        desired['body_edits'][1]['candidate_body'] += ' Closes #1.'
        with tempfile.TemporaryDirectory() as directory:
            plan = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
            handoff = next(item for item in plan['handoffs'] if item['kind'] == 'pr-publisher')
            publication = {'schema_version': 1, 'operation': 'pr-relation-ledger', **handoff['target'], 'before_body_sha256': handoff['expected_body_sha256'], 'after_body_sha256': handoff['candidate_body_sha256'], 'title_sha256': handoff['candidate']['title_sha256'], 'state': 'OPEN', 'is_draft': False, 'status': 'verified', 'no_op': True}
            forge.entities['P1']['body'] = handoff['candidate_body']
            forge.connections['P1'] = {'all': ['I1'], 'manual': [], 'detected': ['I1']}
            forge.connections['I1'] = {'all': ['P1'], 'manual': [], 'detected': ['P1']}
            instruction = {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': []}, 'publication_results': [publication]}
            result = api.execute('reconcile', instruction, forge=forge, state_root=directory)
            self.assertEqual(result['status'], 'blocked')
            self.assertEqual(result['reason'], 'publisher-postimage-drift')


    def test_historical_closed_issue_relation_changes_preserve_both_states(self):
        api, forge = command_module(), FakeForge()
        forge.entities['I1']['state'] = 'CLOSED'
        forge.entities['P1']['state'] = 'MERGED'
        with tempfile.TemporaryDirectory() as directory:
            for intent in ('ensure', 'unlink-native'):
                desired = with_existing_ledgers(forge, request('complete'))
                desired['pairs'][0]['intent'] = intent
                plan = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
                instruction = {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': [item['effect_id'] for item in plan['effects']]}}
                result = api.execute('reconcile', instruction, forge=forge, state_root=directory)
                self.assertEqual(result['status'], 'verified')
                self.assertEqual(forge.entities['I1']['state'], 'CLOSED')
                self.assertEqual(forge.entities['P1']['state'], 'MERGED')
            self.assertEqual(forge.connections['I1']['manual'], [])


    def test_reconcile_rejects_a_digest_valid_plan_with_an_unauthored_body(self):
        api, forge = command_module(), FakeForge()
        with tempfile.TemporaryDirectory() as directory:
            desired = with_existing_ledgers(forge, request('complete'))
            desired['body_edits'][0]['replacement'] += ' — implementation'
            desired['body_edits'][0]['candidate_body'] += ' — implementation'
            plan = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
            def digest(value):
                return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
            effect = plan['effects'][0]
            effect['candidate_body'] += ' Unauthored note.'
            effect['candidate_body_sha256'] = hashlib.sha256(effect['candidate_body'].encode()).hexdigest()
            effect['effect_id'] = digest({key: value for key, value in effect.items() if key != 'effect_id'})
            plan['plan_sha256'] = digest({key: value for key, value in plan.items() if key != 'plan_sha256'})
            instruction = {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': [item['effect_id'] for item in plan['effects']]}}
            result = api.execute('reconcile', instruction, forge=NoForgeAccess(), state_root=directory)
            self.assertEqual(result['status'], 'blocked')
            self.assertEqual(result['reason'], 'plan-does-not-match-decisions')


    def test_lost_response_with_observed_postimage_resumes_without_another_write(self):
        class LostResponseForge(FakeForge):
            attempts = 0
            def change_native(self, operation, issue, prs):
                self.attempts += 1
                super().change_native(operation, issue, prs)
                raise TimeoutError('response lost')
        api, forge = command_module(), LostResponseForge()
        with tempfile.TemporaryDirectory() as directory:
            desired = with_existing_ledgers(forge, request('complete'))
            plan = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
            instruction = {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': [item['effect_id'] for item in plan['effects']]}}
            self.assertEqual(api.execute('reconcile', instruction, forge=forge, state_root=directory)['status'], 'unknown')
            result = api.execute('reconcile', {**instruction, 'mode': 'observe'}, forge=forge, state_root=directory)
            self.assertEqual(result['status'], 'no-op')
            self.assertEqual(forge.attempts, 1)

    def test_interruption_reserves_issue_body_attempt_and_receipt_renewal_rechecks_preimage(self):
        class InterruptedForge(FakeForge):
            attempts = 0
            def write_issue_body(self, entity, candidate_body):
                self.attempts += 1
                if self.attempts == 1:
                    raise KeyboardInterrupt('process interrupted at forge boundary')
                self.entities[entity['id']]['body'] = candidate_body
                return {'ok': True}
        api, forge = command_module(), InterruptedForge()
        with tempfile.TemporaryDirectory() as directory:
            desired = with_existing_ledgers(forge, request('complete'))
            forge.change_native('add', forge.entities['I1'], [forge.entities['P1']])
            desired['body_edits'][0]['replacement'] += ' — implementation'
            desired['body_edits'][0]['candidate_body'] += ' — implementation'
            plan = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
            instruction = {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': [item['effect_id'] for item in plan['effects']]}}
            with self.assertRaises(KeyboardInterrupt):
                api.execute('reconcile', instruction, forge=forge, state_root=directory)
            resumed = command_module().execute('reconcile', instruction, forge=forge, state_root=directory)
            self.assertEqual(resumed['status'], 'unknown')
            self.assertEqual(forge.attempts, 1)
            receipt = api.execute('reconcile', {**instruction, 'mode': 'observe'}, forge=forge, state_root=directory)['effects'][0]
            renewed = copy.deepcopy(instruction)
            renewed['authorization']['renewals'] = [{key: receipt[key] for key in ('effect_id', 'attempt_id', 'receipt_id', 'receipt_sha256')}]
            forge.entities['I1']['body'] += ' Human note.'
            self.assertEqual(api.execute('reconcile', renewed, forge=forge, state_root=directory)['status'], 'blocked')
            self.assertEqual(forge.attempts, 1)
            forge.entities['I1']['body'] = plan['entities']['I1']['body']
            self.assertEqual(api.execute('reconcile', renewed, forge=forge, state_root=directory)['status'], 'verified')
            self.assertEqual(forge.attempts, 2)

    def test_known_rejection_can_be_renewed_after_a_read_only_preimage_receipt(self):
        class RejectedForge(FakeForge):
            attempts = 0
            def change_native(self, operation, issue, prs):
                self.attempts += 1
                if self.attempts == 1:
                    return {'data': {'addCloseIssueReferences': None}, 'errors': [{'type': 'UNPROCESSABLE'}]}
                return super().change_native(operation, issue, prs)
        api, forge = command_module(), RejectedForge()
        with tempfile.TemporaryDirectory() as directory:
            desired = with_existing_ledgers(forge, request('complete'))
            plan = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
            instruction = {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': [item['effect_id'] for item in plan['effects']]}}
            self.assertEqual(api.execute('reconcile', instruction, forge=forge, state_root=directory)['status'], 'blocked')
            receipt = api.execute('reconcile', {**instruction, 'mode': 'observe'}, forge=forge, state_root=directory)['effects'][0]
            instruction['authorization']['renewals'] = [{key: receipt[key] for key in ('effect_id', 'attempt_id', 'receipt_id', 'receipt_sha256')}]
            self.assertEqual(api.execute('reconcile', instruction, forge=forge, state_root=directory)['status'], 'verified')
            self.assertEqual(forge.attempts, 2)


    def test_uncertain_preimage_needs_read_only_receipt_and_explicit_renewal(self):
        class RecoveringForge(FakeForge):
            attempts = 0
            def change_native(self, operation, issue, prs):
                self.attempts += 1
                if self.attempts == 1:
                    raise TimeoutError('response lost')
                return super().change_native(operation, issue, prs)
        api, forge = command_module(), RecoveringForge()
        desired = with_existing_ledgers(forge, request('complete'))
        with tempfile.TemporaryDirectory() as directory:
            plan = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
            instruction = {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': [item['effect_id'] for item in plan['effects']]}}
            self.assertEqual(api.execute('reconcile', instruction, forge=forge, state_root=directory)['status'], 'unknown')
            recovery = {**instruction, 'mode': 'observe'}
            observed = api.execute('reconcile', recovery, forge=forge, state_root=directory)
            self.assertEqual(observed['status'], 'needs-input')
            receipt = observed['effects'][0]
            self.assertEqual(receipt['reason'], 'prior-attempt-observed-preimage')
            self.assertEqual(forge.attempts, 1)
            renewed = copy.deepcopy(instruction)
            renewed['authorization']['renewals'] = [{key: receipt[key] for key in ('effect_id', 'attempt_id', 'receipt_id', 'receipt_sha256')}]
            result = api.execute('reconcile', renewed, forge=forge, state_root=directory)
            self.assertEqual(result['status'], 'verified')
            self.assertEqual(forge.attempts, 2)
            self.assertEqual(api.execute('reconcile', renewed, forge=forge, state_root=directory)['status'], 'no-op')
            self.assertEqual(forge.attempts, 2)


    def test_resupplying_an_old_observation_does_not_reset_cross_task_expiry(self):
        desired = request()
        desired['setting_observations'] = [{'host': 'github.com', 'repository_id': 'R1', 'auto_close': False, 'observed_at': '2026-09-01T12:00:00Z', 'source': 'github-settings-ui', 'evidence': ['checkbox observation']}]
        with tempfile.TemporaryDirectory() as directory:
            result = command_module().execute('observe', desired, forge=FakeForge(), state_root=directory, now='2026-10-02T12:00:00Z')
            self.assertEqual(result['status'], 'observed')
            self.assertIsNone(result['settings']['github.com:R1']['auto_close'])
            self.assertEqual(len(result['setting_requests']), 1)


    def test_simultaneous_resumes_request_one_setting_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            api = command_module()
            def observe(_):
                return api.execute('observe', request(), forge=FakeForge(), state_root=directory)
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(observe, range(8)))
            self.assertTrue(all(item['status'] == 'observed' for item in results))
            self.assertEqual(sum(len(item['setting_requests']) for item in results), 1)

    def test_concurrent_body_edit_blocks_native_write_and_preserves_the_editor_change(self):
        api, forge = command_module(), FakeForge()
        desired = with_existing_ledgers(forge, request('complete'))
        with tempfile.TemporaryDirectory() as directory:
            plan = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
            forge.entities['I1']['body'] += ' New human note.'
            instruction = {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': [item['effect_id'] for item in plan['effects']]}}
            result = api.execute('reconcile', instruction, forge=forge, state_root=directory)
            self.assertEqual(result['status'], 'blocked')
            self.assertEqual(result['effects'][0]['reason'], 'affected-preimage-drift')
            self.assertFalse(result['effects'][0]['mutation_attempted'])
            self.assertTrue(forge.entities['I1']['body'].endswith('New human note.'))
            self.assertEqual(forge.connections['I1']['all'], [])

    def test_unlink_preserves_history_and_withdraw_requires_separate_body_edits(self):
        for intent in ('unlink-native', 'withdraw'):
            with self.subTest(intent=intent), tempfile.TemporaryDirectory() as directory:
                api, forge = command_module(), FakeForge()
                forge.change_native('add', forge.entities['I1'], [forge.entities['P1']])
                desired = with_existing_ledgers(forge, request())
                desired['pairs'][0]['intent'] = intent
                if intent == 'withdraw':
                    desired['pairs'][0]['withdrawal_reason'] = 'scope-dropped'
                    desired['pairs'][0]['evidence'] = ['operator: work will not address this Issue']
                    for edit in desired['body_edits']:
                        edit['replacement'] = edit['candidate_body'] = 'No contributions.'
                observed = api.execute('observe', desired, forge=forge, state_root=directory)
                self.assertEqual(observed['setting_requests'], [])
                plan = api.execute('plan', observed)
                self.assertIn('native-remove', [item['kind'] for item in plan['effects']])
                self.assertEqual(len(plan['ledgers']['I1']), 1 if intent == 'unlink-native' else 0)
                if intent == 'withdraw':
                    self.assertEqual(plan['handoffs'][0]['kind'], 'pr-publisher')
                else:
                    instruction = {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': [item['effect_id'] for item in plan['effects']]}}
                    result = api.execute('reconcile', instruction, forge=forge, state_root=directory)
                    self.assertEqual(result['status'], 'verified')
                    self.assertIn('https://github.com/owner/project/pull/2', forge.entities['I1']['body'])
                    self.assertEqual(forge.connections['I1']['manual'], [])

    def test_detected_link_removal_is_a_content_handoff(self):
        api, forge = command_module(), FakeForge()
        forge.connections['I1'] = {'all': ['P1'], 'manual': [], 'detected': ['P1']}
        forge.connections['P1'] = {'all': ['I1'], 'manual': [], 'detected': ['I1']}
        desired = with_existing_ledgers(forge, request())
        desired['pairs'][0]['intent'] = 'unlink-native'
        with tempfile.TemporaryDirectory() as directory:
            plan = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
            self.assertEqual(plan['status'], 'needs-input')
            self.assertEqual(plan['effects'], [])
            self.assertEqual(plan['handoffs'][0]['kind'], 'pr-keyword-removal')

    def test_incomplete_pagination_is_not_accepted_as_a_complete_ledger_observation(self):
        class IncompleteForge(FakeForge):
            def read_connection_page(self, entity, provenance, cursor):
                return {'nodes': [], 'total_count': 1, 'page_info': {'has_next_page': False, 'end_cursor': None}}
        with tempfile.TemporaryDirectory() as directory:
            result = command_module().execute('observe', request('complete'), forge=IncompleteForge(), state_root=directory)
            self.assertEqual(result['status'], 'blocked')
            self.assertEqual(result['reason'], 'incomplete-pagination')


    def test_authorized_candidate_cannot_publish_secret_shaped_content(self):
        api, forge = command_module(), FakeForge()
        desired = with_existing_ledgers(forge, request('complete'))
        suspicious = 'ghp_' + 'x' * 24
        desired['body_edits'][0]['candidate_body'] += ' ' + suspicious
        desired['body_edits'][0]['replacement'] += ' ' + suspicious
        with tempfile.TemporaryDirectory() as directory:
            result = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
            self.assertEqual(result['status'], 'blocked')
            self.assertEqual(result['reason'], 'candidate-contains-suspected-secret')
            self.assertNotIn(suspicious, json.dumps(result))


    def test_conflicting_stable_identity_and_non_boolean_applicability_are_rejected(self):
        desired = request('complete')
        second = copy.deepcopy(desired['pairs'][0])
        second['issue']['number'] = 99
        second['pr']['id'] = 'P2'
        desired['pairs'].append(second)
        with tempfile.TemporaryDirectory() as directory:
            result = command_module().execute('observe', desired, forge=FakeForge(), state_root=directory)
            self.assertEqual(result['reason'], 'entity-identity-drift')
            desired = request('complete')
            desired['applicability']['active'] = 'yes'
            result = command_module().execute('observe', desired, forge=NoForgeAccess(), state_root=directory)
            self.assertEqual(result['reason'], 'invalid-request')


    def test_state_change_after_native_write_invalidates_the_disabled_observation(self):
        class ClosingForge(FakeForge):
            def change_native(self, operation, issue, prs):
                result = super().change_native(operation, issue, prs)
                self.entities[issue['id']]['state'] = 'CLOSED'
                return result
        api, forge = command_module(), ClosingForge()
        desired = with_existing_ledgers(forge, request())
        desired['setting_observations'] = [{'host': 'github.com', 'repository_id': 'R1', 'auto_close': False, 'observed_at': '2026-09-17T12:00:00Z', 'source': 'github-settings-ui', 'evidence': ['checkbox observation']}]
        with tempfile.TemporaryDirectory() as directory:
            observed = api.execute('observe', desired, forge=forge, state_root=directory, now='2026-09-17T12:00:00Z')
            plan = api.execute('plan', observed)
            instruction = {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': [item['effect_id'] for item in plan['effects']]}}
            result = api.execute('reconcile', instruction, forge=forge, state_root=directory)
            self.assertEqual(result['status'], 'partial')
            self.assertFalse(result['effects'][0]['state_preserved'])
            self.assertEqual(forge.entities['I1']['state'], 'CLOSED')
            fresh = api.execute('observe', request(), forge=forge, state_root=directory)
            self.assertEqual(len(fresh['setting_requests']), 1)
            self.assertIsNone(fresh['settings']['github.com:R1']['auto_close'])


    def test_uncertain_write_is_not_retried_when_the_preimage_is_still_visible(self):
        class UncertainForge(FakeForge):
            attempts = 0
            def change_native(self, operation, issue, prs):
                self.attempts += 1
                raise TimeoutError('response lost')
        forge, api = UncertainForge(), command_module()
        desired = with_existing_ledgers(forge, request('complete'))
        with tempfile.TemporaryDirectory() as directory:
            plan = api.execute('plan', api.execute('observe', desired, forge=forge, state_root=directory))
            instruction = {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': [item['effect_id'] for item in plan['effects']]}}
            first = api.execute('reconcile', instruction, forge=forge, state_root=directory)
            self.assertEqual(first['status'], 'unknown')
            resumed = api.execute('reconcile', instruction, forge=forge, state_root=directory)
            self.assertEqual(resumed['status'], 'unknown')
            self.assertEqual(forge.attempts, 1)
            self.assertEqual(resumed['effects'][0]['reason'], 'prior-attempt-unresolved')


    def test_cli_observation_groups_first_pages_and_reports_external_request_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            desired = request('complete')
            (root / 'request.json').write_text(json.dumps(desired))
            forge = FakeForge()
            nodes = {}
            for entity_id, entity in forge.entities.items():
                node = {key: entity[key] for key in ('id', 'number', 'url', 'body', 'title', 'state')}
                node['__typename'] = entity['kind']
                node['repository'] = {'id': 'R1', 'nameWithOwner': 'owner/project', 'visibility': 'PRIVATE', 'defaultBranchRef': {'name': 'main'}}
                if entity['kind'] == 'PullRequest':
                    node.update(isDraft=False, baseRefName='main', headRefOid='a' * 40)
                for mode in ('all', 'manual', 'detected'):
                    node[mode] = {'totalCount': 0, 'nodes': [], 'pageInfo': {'hasNextPage': False, 'endCursor': None}}
                nodes[entity_id] = node
            (root / 'nodes.json').write_text(json.dumps(nodes))
            fake = root / 'gh'
            fake.write_text('#!' + sys.executable + '\n' + """
import json, pathlib, sys
root = pathlib.Path(__file__).parent
payload = json.load(sys.stdin)
with (root / 'calls.jsonl').open('a') as stream:
    stream.write(json.dumps(payload) + '\\n')
node = json.loads((root / 'nodes.json').read_text())[payload['variables']['id']]
print(json.dumps({'data': {'node': node}}))
""")
            fake.chmod(0o700)
            result = subprocess.run([sys.executable, str(SCRIPT), 'observe', '--input', str(root / 'request.json'), '--state-root', str(root / 'state')], text=True, capture_output=True, env={**os.environ, 'PATH': str(root) + os.pathsep + os.environ.get('PATH', '')})
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            observed = json.loads(result.stdout)
            self.assertEqual(observed['status'], 'observed')
            self.assertEqual(observed['read_counts']['external_read_requests'], 2)
            self.assertEqual(observed['read_counts']['connection_pages'], 6)
            calls = [json.loads(line) for line in (root / 'calls.jsonl').read_text().splitlines()]
            self.assertEqual(len(calls), 2)
            self.assertTrue(all(all(alias + ':' in item['query'] for alias in ('all', 'manual', 'detected')) for item in calls))
            self.assertIn('includeClosedPrs:true', calls[0]['query'])
            self.assertFalse((root / 'state').exists())


    def test_verified_ui_rollout_records_are_consumed_without_new_acquisition(self):
        desired = request()
        desired['setting_observations'] = [{'repository_id': 'R1', 'repository': 'owner/project', 'host': 'github.com', 'before': True, 'value': False, 'source': 'https://github.com/owner/project/settings', 'observed_at': '2026-09-17T12:00:00.123Z', 'status': 'changed-verified'}]
        with tempfile.TemporaryDirectory() as directory:
            observed = command_module().execute('observe', desired, forge=FakeForge(), state_root=directory, now='2026-09-17T12:01:00Z')
            self.assertEqual(observed['status'], 'observed')
            self.assertFalse(observed['settings']['github.com:R1']['auto_close'])
            self.assertEqual(observed['settings']['github.com:R1']['source'], desired['setting_observations'][0]['source'])
            self.assertEqual(observed['setting_requests'], [])
            desired['setting_observations'][0]['status'] = 'not-verified'
            rejected = command_module().execute('observe', desired, forge=FakeForge(), state_root=directory, now='2026-09-17T12:01:00Z')
            self.assertEqual(rejected['reason'], 'invalid-setting-observation')


    def test_existing_partial_closing_intent_requires_disabled_setting_or_an_owner_decision(self):
        for provenance in ('manual', 'detected'):
            for setting in (None, True, False):
                with self.subTest(provenance=provenance, setting=setting), tempfile.TemporaryDirectory() as directory:
                    api, forge = command_module(), FakeForge()
                    forge.connections['I1'] = {'all': ['P1'], 'manual': [], 'detected': []}
                    forge.connections['P1'] = {'all': ['I1'], 'manual': [], 'detected': []}
                    forge.connections['I1'][provenance] = ['P1']
                    forge.connections['P1'][provenance] = ['I1']
                    desired = with_existing_ledgers(forge, request())
                    if setting is not None:
                        desired['setting_observations'] = [{'host': 'github.com', 'repository_id': 'R1', 'auto_close': setting, 'observed_at': '2026-09-17T12:00:00Z', 'source': 'github-settings-ui', 'evidence': ['checkbox observation']}]
                    observed = api.execute('observe', desired, forge=forge, state_root=directory, now='2026-09-17T12:00:00Z')
                    plan = api.execute('plan', observed)
                    self.assertEqual(plan['effects'], [])
                    self.assertEqual(plan['status'], 'no-op' if setting is False else 'needs-input')
                    if setting is not False:
                        self.assertEqual(plan['handoffs'][0]['kind'], 'closing-intent-decision')
                    self.assertEqual(len(observed['setting_requests']), 1 if setting is None else 0)


    def test_body_authoring_requires_the_endpoint_owner(self):
        api = command_module()
        with tempfile.TemporaryDirectory() as directory:
            observed = api.execute('observe', request('complete'), forge=FakeForge(), state_root=directory)
            plan = api.execute('plan', observed)
            writers = {item['entity_id']: item['writer'] for item in plan['handoffs'] if item['kind'] == 'body-authoring'}
            self.assertEqual(writers, {'I1': 'writing-github-issue-and-pr-markdown', 'P1': 'writing-reviewable-pr-descriptions'})
            forge = FakeForge()
            desired = with_existing_ledgers(forge, request('complete'))
            desired['body_edits'][1]['writer'] = 'writing-github-issue-and-pr-markdown'
            observed = api.execute('observe', desired, forge=forge, state_root=directory)
            self.assertEqual(api.execute('plan', observed)['reason'], 'body-edit-needs-writer-output')


    def test_pr_publisher_result_requires_independent_live_postimage_verification(self):
        forge = FakeForge()
        desired = with_existing_ledgers(forge, request('complete'))
        desired['body_edits'][1]['replacement'] += ' — implementation'
        desired['body_edits'][1]['candidate_body'] += ' — implementation'
        with tempfile.TemporaryDirectory() as directory:
            api = command_module()
            observed = api.execute('observe', desired, forge=forge, state_root=Path(directory))
            plan = api.execute('plan', observed)
            handoff = plan['handoffs'][0]
            result = {'schema_version': 1, 'operation': 'pr-relation-ledger', **handoff['target'],
                      'before_body_sha256': handoff['expected_body_sha256'],
                      'after_body_sha256': handoff['candidate_body_sha256'],
                      'title_sha256': handoff['candidate']['title_sha256'],
                      'state': 'OPEN', 'is_draft': False, 'status': 'verified', 'no_op': False,
                      'receipt_id': 'receipt-1', 'receipt_sha256': 'a' * 64}
            instruction = {'version': 1, 'plan': plan, 'authorization': {'plan_sha256': plan['plan_sha256'], 'effect_ids': [effect['effect_id'] for effect in plan['effects']]}, 'publication_results': [result]}
            refused = api.execute('reconcile', instruction, forge=forge, state_root=Path(directory))
            self.assertEqual(refused['status'], 'blocked')
            self.assertEqual(refused['reason'], 'publisher-postimage-drift')
            forge.entities['P1']['body'] = handoff['candidate_body']
            verified = api.execute('reconcile', instruction, forge=forge, state_root=Path(directory))
            self.assertEqual(verified['status'], 'verified')
            after = api.execute('observe', request('complete'), forge=forge, state_root=Path(directory))
            self.assertEqual(after['entities']['P1']['body'], handoff['candidate_body'])
            self.assertEqual(after['entities']['P1']['state'], 'OPEN')


if __name__ == '__main__':
    unittest.main()
