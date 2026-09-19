#!/usr/bin/env python3
"""Observe, plan, and reconcile a finite set of evidenced Issue–PR relations."""

from __future__ import annotations

import copy
import hashlib
import re
import json
import os
import argparse
import importlib.util
import uuid
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta


REASONS = {'unrelated-edit', 'no-contribution', 'unchanged-relations',
           'relation-change', 'historical-repair', 'setting-refresh'}
INACTIVE_REASONS = {'unrelated-edit', 'no-contribution', 'unchanged-relations'}


def _has_evidence(value):
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)


def _reference(value):
    if not isinstance(value, dict) or value.get('host') != 'github.com':
        raise ValueError('unsupported-forge')
    if not re.fullmatch(r'[^/\s]+/[^/\s]+', value.get('repository', '')):
        raise ValueError('invalid-repository')
    if type(value.get('number')) is not int or value['number'] < 1 or not isinstance(value.get('id'), str) or not value['id']:
        raise ValueError('invalid-entity-reference')
    return value


def _entity(reference, kind, forge, counts, supplied=None):
    if supplied is None:
        counts['entities'] += 1
        entity = forge.read_entity(reference)
    else:
        entity = copy.deepcopy(supplied)
    if (entity.get('id') != reference['id'] or entity.get('kind') != kind
            or entity.get('host') != reference['host'] or entity.get('number') != reference['number']
            or entity.get('repository', {}).get('name') != reference['repository']):
        raise ValueError('entity-identity-drift')
    path = 'issues' if kind == 'Issue' else 'pull'
    expected_url = f"https://{reference['host']}/{reference['repository']}/{path}/{reference['number']}"
    if entity.get('url') != expected_url or not entity['repository'].get('id'):
        raise ValueError('entity-identity-drift')
    if not all(isinstance(entity.get(key), str) for key in ('body', 'title', 'state')):
        raise ValueError('incomplete-entity')
    if entity['state'] not in (('OPEN', 'CLOSED') if kind == 'Issue' else ('OPEN', 'CLOSED', 'MERGED')):
        raise ValueError('unsupported-entity-state')
    if entity['repository'].get('visibility') not in ('PRIVATE', 'PUBLIC'):
        raise ValueError('unsupported-repository-visibility')
    if kind == 'PullRequest' and (type(entity.get('is_draft')) is not bool or not entity.get('base_ref') or not entity.get('head_oid')):
        raise ValueError('incomplete-pull-request')
    return entity


def _relations(entity, forge, counts):
    relations = {}
    for provenance in ('all', 'manual', 'detected'):
        ids, cursor, cursors, expected_count = [], None, set(), None
        while True:
            counts['connection_pages'] += 1
            page = forge.read_connection_page(entity, provenance, cursor)
            total = page['total_count']
            if type(total) is not int or total < 0 or (expected_count is not None and expected_count != total):
                raise ValueError('connection-drift')
            expected_count = total
            for node in page['nodes']:
                if not isinstance(node.get('id'), str) or not node['id'] or node['id'] in ids:
                    raise ValueError('invalid-connection-node')
                ids.append(node['id'])
            info = page['page_info']
            if type(info.get('has_next_page')) is not bool:
                raise ValueError('incomplete-pagination')
            if not info['has_next_page']:
                if len(ids) != total:
                    raise ValueError('incomplete-pagination')
                break
            cursor = info['end_cursor']
            if not cursor or cursor in cursors or len(ids) >= total:
                raise ValueError('incomplete-pagination')
            cursors.add(cursor)
        relations[provenance] = sorted(ids)
    if set(relations['all']) != set(relations['manual']) | set(relations['detected']):
        raise ValueError('inconsistent-provenance')
    return relations


def _complete_relations(entity):
    if entity.get('pagination_complete') is not True:
        raise ValueError('incomplete-pagination')
    relations = entity['relations']
    for mode in ('all', 'manual', 'detected'):
        ids = relations.get(mode)
        if not isinstance(ids, list) or any(not isinstance(item, str) or not item for item in ids) or len(set(ids)) != len(ids):
            raise ValueError('invalid-connection-node')
    if set(relations['all']) != set(relations['manual']) | set(relations['detected']):
        raise ValueError('inconsistent-provenance')
    return {mode: sorted(ids) for mode, ids in relations.items()}



@contextmanager
def _cache(state_root):
    root = Path(state_root) if state_root is not None else Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'mergecraft/issue-pr-relations'
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (root / 'settings.lock').open('a+b') as lock:
        if os.name == 'nt':
            import msvcrt
            if lock.tell() == 0:
                lock.write(b'0')
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        path = root / 'settings.json'
        value = json.loads(path.read_text()) if path.exists() else {'version': 1, 'repositories': {}}
        if value.get('version') != 1 or not isinstance(value.get('repositories'), dict):
            raise ValueError('invalid-settings-cache')
        before = json.dumps(value, sort_keys=True)
        yield value
        if json.dumps(value, sort_keys=True) != before:
            temporary = root / 'settings.json.pending'
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'w') as stream:
                json.dump(value, stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            if os.name != 'nt':
                directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)



def _instant(value):
    if value is None:
        return datetime.now(timezone.utc)
    if not isinstance(value, str):
        raise ValueError('invalid-timestamp')
    instant = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if instant.tzinfo is None:
        raise ValueError('timestamp-needs-timezone')
    return instant


def _invalidate_setting(record, instant):
    record['generation'] += 1
    record['observation'] = None
    record['tasks'] = {}
    previous = record.get('invalidated_at')
    record['invalidated_at'] = max(instant, _instant(previous) if previous else instant).isoformat()

def _settings(document, entities, state_root, now):
    needed = {}
    for pair in document.get('pairs', []):
        issue, pr = entities[pair['issue']['id']], entities[pair['pr']['id']]
        if pair['intent'] == 'ensure' and pair['completion'] == 'partial':
            repo = issue['repository']
            needed[issue['host'] + ':' + repo['id']] = {'host': issue['host'], 'repository_id': repo['id'], 'repository': repo['name']}
    if not needed and not document.get('invalidate_settings'):
        return {}, []
    ttl = document.get('setting_ttl_days', 30)
    if ttl is not None and (type(ttl) is not int or ttl < 1):
        raise ValueError('invalid-setting-ttl')
    instant = _instant(now)
    supplied = {}
    for observation in document.get('setting_observations', []):
        observation = copy.deepcopy(observation)
        key = observation['host'] + ':' + observation['repository_id']
        if key not in needed:
            continue
        ui_url = f"https://github.com/{needed[key]['repository']}/settings"
        if observation.get('source') == ui_url and observation.get('status') in ('changed-verified', 'already-disabled-verified', 'verified'):
            if type(observation.get('value')) is not bool:
                raise ValueError('invalid-setting-observation')
            observation['auto_close'] = observation['value']
            observation['evidence'] = [observation['status'], observation['source']]
        if (observation.get('source') not in ('github-settings-ui', ui_url)
                or ('value' in observation and observation.get('status') not in ('changed-verified', 'already-disabled-verified', 'verified'))
                or type(observation.get('auto_close')) not in (bool, type(None))
                or not _has_evidence(observation.get('evidence')) or _instant(observation['observed_at']) > instant):
            raise ValueError('invalid-setting-observation')
        if key in supplied:
            raise ValueError('duplicate-setting-observation')
        supplied[key] = copy.deepcopy(observation)
    selected, requests = {}, []
    with _cache(state_root) as cache:
        for invalidation in document.get('invalidate_settings', []):
            if invalidation.get('host') != 'github.com' or not invalidation.get('repository_id') or not invalidation.get('event_id') or invalidation.get('reason') not in {'explicit-refresh', 'observed-change', 'contradictory-behavior'}:
                raise ValueError('invalid-setting-invalidation')
            key = invalidation['host'] + ':' + invalidation['repository_id']
            record = cache['repositories'].setdefault(key, {'generation': 0, 'observation': None, 'tasks': {}})
            events = record.setdefault('invalidations', [])
            if invalidation['event_id'] not in events:
                _invalidate_setting(record, instant)
                events.append(invalidation['event_id'])
        for key, identity in sorted(needed.items()):
            record = cache['repositories'].setdefault(key, {'generation': 0, 'observation': None, 'tasks': {}})
            incoming = supplied.get(key)
            if incoming is not None and record.get('invalidated_at') and _instant(incoming['observed_at']) <= _instant(record['invalidated_at']):
                incoming = None
            if incoming is not None and incoming['auto_close'] is not None and incoming != record['observation']:
                previous = record['observation']
                if previous and _instant(incoming['observed_at']) < _instant(previous['observed_at']):
                    raise ValueError('older-setting-observation')
                record['observation'] = incoming
                record['generation'] += 1
                record['tasks'] = {}
            task = record['tasks'].get(document['task_id'])
            provenance = 'task-cache'
            if task is None:
                observation = record['observation']
                valid = observation is not None and type(observation.get('auto_close')) is bool and (ttl is None or instant - _instant(observation['observed_at']) < timedelta(days=ttl))
                if incoming is not None and incoming['auto_close'] is None:
                    task = {'observation': incoming, 'attempted': True}
                    provenance = 'unavailable'
                elif valid:
                    task = {'observation': observation, 'attempted': True}
                    provenance = 'supplied-observation' if incoming is not None else 'persistent-cache'
                else:
                    requests.append({**identity, 'source': 'github-settings-ui'})
                    task = {'observation': None, 'attempted': True}
                    provenance = 'unavailable'
                record['tasks'][document['task_id']] = task
            observation = task['observation']
            selected[key] = {**identity, 'auto_close': observation['auto_close'] if observation else None,
                             'observed_at': observation['observed_at'] if observation else None,
                             'source': observation['source'] if observation else None,
                             'evidence': observation['evidence'] if observation else [],
                             'provenance': provenance, 'generation': record['generation']}

    return selected, requests

def _observe(document, forge, counts, state_root, now):
    entities = {}
    for pair in _pairs(document):
        for key, kind in (('issue', 'Issue'), ('pr', 'PullRequest')):
            reference = _reference(pair[key])
            if reference['id'] in entities:
                _entity(reference, kind, forge, counts, entities[reference['id']])
            else:
                supplied = document.get('entity_observations', {}).get(reference['id'])
                entity = _entity(reference, kind, forge, counts, supplied)
                if supplied is None:
                    entity['relations'] = _relations(entity, forge, counts)
                    entity['pagination_complete'] = True
                else:
                    entity['relations'] = _complete_relations(entity)
                entities[reference['id']] = entity
    settings, requests = _settings(document, entities, state_root, now)
    return {'version': 1, 'status': 'observed', 'request': copy.deepcopy(document),
            'entities': entities, 'settings': settings, 'setting_requests': requests, 'read_counts': counts}


def _digest(value):
    encoded = value.encode('utf-8') if isinstance(value, str) else json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def _pairs(request):
    pairs, seen = [], {}
    for pair in request.get('pairs', []):
        _reference(pair['issue'])
        _reference(pair['pr'])
        if pair.get('intent') not in ('ensure', 'unlink-native', 'withdraw') or not _has_evidence(pair.get('evidence')):
            raise ValueError('contribution-decision-needs-evidence')
        if pair['intent'] == 'withdraw':
            if pair.get('withdrawal_reason') not in ('mistaken-association', 'scope-dropped'):
                raise ValueError('withdrawal-needs-explicit-reason')
        elif (not isinstance(pair.get('role'), str) or not pair['role'].strip()
              or pair.get('completion') not in ('partial', 'complete')
              or (pair['completion'] == 'complete' and not _has_evidence(pair.get('completion_evidence')))):
            raise ValueError('incomplete-contribution-evidence')
        key = (pair['issue']['id'], pair['pr']['id'])
        if key in seen and seen[key] != pair:
            raise ValueError('conflicting-pair-decisions')
        if key not in seen:
            pairs.append(pair)
            seen[key] = pair
    return sorted(pairs, key=lambda pair: (pair['issue']['id'], pair['pr']['id']))


def _effect(kind, **fields):
    result = {'kind': kind, **fields}
    result['effect_id'] = _digest(result)
    return result



def _writer(entity):
    return 'writing-github-issue-and-pr-markdown' if entity['kind'] == 'Issue' else 'writing-reviewable-pr-descriptions'


def _github_url_tokens(text):
    # This checks lexical identity; the semantic writer owns ledger completeness.
    return {url.rstrip('.,;:!?') for url in re.findall(r'https://github\.com/[^\s<>()\[\]\'"`]+', text)}


def _body_edit(edit, entity, entries, withdrawn):
    if edit.get('writer') != _writer(entity) or not _has_evidence(edit.get('evidence')):
        raise ValueError('body-edit-needs-writer-output')
    body = entity['body']
    if edit.get('expected_body_sha256') != _digest(body):
        raise ValueError('body-preimage-drift')
    start, end = edit['start_byte'], edit['end_byte']
    encoded = body.encode('utf-8')
    if type(start) is not int or type(end) is not int or not 0 <= start <= end <= len(encoded):
        raise ValueError('invalid-authorized-span')
    try:
        before = encoded[start:end].decode('utf-8')
        prefix, suffix = encoded[:start].decode('utf-8'), encoded[end:].decode('utf-8')
    except UnicodeDecodeError as error:
        raise ValueError('span-splits-utf8-character') from error
    if before != edit['before']:
        raise ValueError('body-preimage-drift')
    candidate = edit['candidate_body']
    if not isinstance(candidate, str) or candidate != prefix + edit['replacement'] + suffix:
        raise ValueError('candidate-does-not-match-authorized-span')
    sensitive_path = Path(__file__).resolve().parents[2] / 'writing-reviewable-pr-descriptions/scripts/change_navigation/sensitive_content.py'
    spec = importlib.util.spec_from_file_location('relation_sensitive_content', sensitive_path)
    sensitive = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sensitive)
    if sensitive.contains_suspected_secret(candidate):
        raise ValueError('candidate-contains-suspected-secret')
    candidate_urls = _github_url_tokens(candidate)
    replacement_urls = _github_url_tokens(edit['replacement'])
    if any(entry['url'] not in candidate_urls for entry in entries):
        raise ValueError('candidate-omits-supported-contribution')
    if any(entry['url'] in replacement_urls for entry in withdrawn):
        raise ValueError('candidate-retains-withdrawn-ledger-entry')
    if candidate == body:
        return None
    common = {'entity_id': entity['id'], 'expected_body_sha256': _digest(body),
              'candidate_body': candidate, 'candidate_body_sha256': _digest(candidate),
              'authorized_span': {'start_utf8': start, 'end_utf8': end, 'replacement': edit['replacement']},
              'writer': edit['writer'], 'evidence': edit['evidence']}
    if entity['kind'] == 'Issue':
        return _effect('issue-body', **common)
    return {'kind': 'pr-publisher', 'operation': 'pr-relation-ledger-write', **common,
            'schema_version': 1,
            'target': {'host': entity['host'], 'repository': entity['repository']['name'],
                       'repository_id': entity['repository']['id'], 'entity_id': entity['id'], 'number': entity['number']},
            'preimage': {'title': entity['title'], 'body': body, 'state': entity['state'], 'is_draft': entity['is_draft']},
            'candidate': {'title_sha256': _digest(entity['title']), 'body_sha256': _digest(candidate)}}

def _plan(observed):
    if observed.get('version') != 1 or observed.get('status') != 'observed':
        raise ValueError('plan-needs-complete-observation')
    request, entities = observed['request'], observed['entities']
    if request.get('version') != 1 or request.get('applicability', {}).get('active') is not True or request['applicability'].get('reason') not in REASONS:
        raise ValueError('invalid-request')
    pairs = _pairs(request)
    expected_ids = {pair[key]['id'] for pair in pairs for key in ('issue', 'pr')}
    if set(entities) != expected_ids:
        raise ValueError('unbound-entity-observation')
    ledgers = {entity_id: [] for entity_id in entities}
    withdrawals = {entity_id: [] for entity_id in entities}
    additions, removals, omissions, handoffs = {}, {}, [], []
    for pair in pairs:
        issue, pr = entities[pair['issue']['id']], entities[pair['pr']['id']]
        for key, kind in (('issue', 'Issue'), ('pr', 'PullRequest')):
            _entity(pair[key], kind, None, {}, entities[pair[key]['id']])
            _complete_relations(entities[pair[key]['id']])
        if any(entity.get('pagination_complete') is not True for entity in (issue, pr)):
            raise ValueError('incomplete-pagination')
        if pair['intent'] != 'withdraw':
            ledgers[issue['id']].append({'entity_id': pr['id'], 'url': pr['url'], 'role': pair['role']})
            ledgers[pr['id']].append({'entity_id': issue['id'], 'url': issue['url'], 'role': pair['role']})
        else:
            withdrawals[issue['id']].append({'entity_id': pr['id'], 'url': pr['url']})
            withdrawals[pr['id']].append({'entity_id': issue['id'], 'url': issue['url']})
        in_pr = issue['id'] in pr['relations']['all']
        in_issue = pr['id'] in issue['relations']['all']
        if in_pr != in_issue or any((issue['id'] in pr['relations'][mode]) != (pr['id'] in issue['relations'][mode]) for mode in ('manual', 'detected')):
            raise ValueError('directional-relation-drift')
        if issue['repository']['id'] != pr['repository']['id'] and ('PRIVATE' in (issue['repository']['visibility'], pr['repository']['visibility'])) and pair.get('disclosure_authorized') is not True:
            raise ValueError('private-cross-repository-disclosure-unbound')
        if pair['intent'] in ('unlink-native', 'withdraw'):
            if issue['id'] in pr['relations']['detected']:
                handoffs.append({'kind': 'pr-keyword-removal', 'entity_id': pr['id'], 'issue_id': issue['id']})
            elif issue['id'] in pr['relations']['manual']:
                removals.setdefault(issue['id'], []).append(pr['id'])
        else:
            key = issue['host'] + ':' + issue['repository']['id']
            setting = observed.get('settings', {}).get(key, {})
            safe = pair['completion'] == 'complete' or setting.get('auto_close') is False
            if in_pr and not safe:
                handoffs.append({'kind': 'closing-intent-decision', 'issue_id': issue['id'], 'entity_id': pr['id'],
                                 'reason': 'existing-partial-with-enabled-or-unknown-setting',
                                 'options': ['provide-completion-evidence', 'unlink-native', 'remove-detected-closing-keyword']})
            elif not in_pr and safe:
                additions.setdefault(issue['id'], []).append(pr['id'])
            elif not in_pr:
                omissions.append({'issue_id': issue['id'], 'pr_id': pr['id'], 'reason': 'partial-with-enabled-or-unknown-setting'})
    selections = request.get('native_selection')
    selected_pairs = None
    if selections is not None:
        selected_pairs = {(item['issue_id'], item['pr_id']) for item in selections}
        eligible = {(issue_id, pr_id) for issue_id, pr_ids in additions.items() for pr_id in pr_ids}
        if len(selected_pairs) != len(selections) or not selected_pairs <= eligible:
            raise ValueError('invalid-native-selection')
    for pr_id in sorted({pr_id for values in additions.values() for pr_id in values}):
        candidates = sorted(issue_id for issue_id, values in additions.items() if pr_id in values)
        removed = sum(pr_id in values for values in removals.values())
        capacity = max(0, 10 - len(entities[pr_id]['relations']['manual']) + removed)
        if len(candidates) > capacity:
            chosen = [issue_id for issue_id in candidates if selected_pairs is not None and (issue_id, pr_id) in selected_pairs]
            if len(chosen) > capacity:
                raise ValueError('native-selection-exceeds-capacity')
            if selected_pairs is None:
                handoffs.append({'kind': 'native-selection', 'entity_id': pr_id, 'capacity': capacity,
                                 'candidates': [{'issue_id': issue_id, 'pr_id': pr_id} for issue_id in candidates]})
            for issue_id in candidates:
                if issue_id not in chosen:
                    additions[issue_id].remove(pr_id)
                    omissions.append({'issue_id': issue_id, 'pr_id': pr_id, 'reason': 'manual-capacity'})
    effects = []
    for kind, grouped in (('native-remove', removals), ('native-add', additions)):
        for issue_id, pr_ids in sorted(grouped.items()):
            ordered = sorted(set(pr_ids))
            for start in range(0, len(ordered), 10):
                effects.append(_effect(kind, issue_id=issue_id, pr_ids=ordered[start:start + 10]))
    edits = {}
    for edit in request.get('body_edits', []):
        if edit['entity_id'] in edits or edit['entity_id'] not in entities:
            raise ValueError('unbound-body-edit')
        edits[edit['entity_id']] = edit
    body_effects = []
    for entity_id, entries in sorted(ledgers.items()):
        if entity_id not in edits:
            handoffs.append({'kind': 'body-authoring', 'entity_id': entity_id,
                             'writer': _writer(entities[entity_id]), 'entries': entries,
                             'withdrawals': withdrawals[entity_id], 'preimage_body': entities[entity_id]['body']})
            continue
        prepared = _body_edit(edits[entity_id], entities[entity_id], entries, withdrawals[entity_id])
        if prepared is not None:
            if prepared['kind'] == 'issue-body':
                body_effects.append(prepared)
            else:
                handoffs.append(prepared)
    effects = body_effects + effects
    result = {'version': 1, 'status': 'needs-input' if any(item['kind'] != 'pr-publisher' for item in handoffs) else ('ready' if effects or handoffs else 'no-op'),
              'request': {key: copy.deepcopy(request[key]) for key in ('version', 'task_id', 'applicability', 'pairs', 'body_edits', 'native_selection') if key in request},
              'task_id': request['task_id'], 'decisions': copy.deepcopy(pairs), 'entities': copy.deepcopy(entities),
              'settings': copy.deepcopy(observed.get('settings', {})), 'effects': effects,
              'ledgers': ledgers, 'handoffs': handoffs, 'omitted_native': omissions,
              'read_counts': {'entities': 0, 'connection_pages': 0, 'settings': 0,
                              'external_read_requests': 0, 'external_write_requests': 0}}
    result['plan_sha256'] = _digest(result)
    return result


def _fresh(expected, forge, counts, *, connections=True):
    reference = {'host': expected['host'], 'repository': expected['repository']['name'],
                 'number': expected['number'], 'id': expected['id']}
    entity = _entity(reference, expected['kind'], forge, counts)
    if connections:
        entity['relations'] = _relations(entity, forge, counts)
        entity['pagination_complete'] = True
    return entity


def _native_postimage(expected, effect):
    result = copy.deepcopy(expected)
    issue_id = effect['issue_id']
    for pr_id in effect['pr_ids']:
        for entity_id, other_id in ((issue_id, pr_id), (pr_id, issue_id)):
            for provenance in ('all', 'manual'):
                ids = set(result[entity_id]['relations'][provenance])
                if effect['kind'] == 'native-add':
                    ids.add(other_id)
                else:
                    ids.discard(other_id)
                result[entity_id]['relations'][provenance] = sorted(ids)
    return result



def _check_settings(plan, state_root):
    if not plan.get('settings'):
        return
    with _cache(state_root) as cache:
        _validate_setting_generations(plan, cache)


def _validate_setting_generations(plan, cache):
    for key, selected in plan['settings'].items():
        record = cache['repositories'].get(key)
        if record is None or record['generation'] != selected['generation']:
            raise ValueError('setting-observation-invalidated')
        task = record['tasks'].get(plan['task_id'])
        observation = task.get('observation') if task else None
        if (observation.get('auto_close') if observation else None) != selected['auto_close']:
            raise ValueError('setting-observation-invalidated')


def _plain_entity(entity):
    return {key: value for key, value in entity.items() if key not in ('relations', 'pagination_complete')}


def _attempt_targets(effect):
    if effect['kind'] == 'issue-body':
        return ['body:' + effect['entity_id']]
    return sorted('native:' + effect['issue_id'] + ':' + pr_id for pr_id in effect['pr_ids'])


def _native_fingerprints(entities):
    result = copy.deepcopy(entities)
    for entity in result.values():
        for field in ('body', 'title'):
            entity[field + '_sha256'] = _digest(entity.pop(field))
    return result


def _native_recovery(effect, current, forge, counts, state_root, *, mode, renewal, now):
    """Observe an exact subset of one admitted batch without replaying it."""
    targets = set(_attempt_targets(effect))
    with _cache(state_root) as cache:
        pending = [(key, copy.deepcopy(item)) for key, item in cache.get('attempts', {}).items()
                   if item['status'] == 'attempted' and targets & set(item['targets'])]
    if len(pending) != 1 or not pending[0][1].get('native_context'):
        return None, None
    key, previous = pending[0]
    context = previous['native_context']
    original = context['effect']
    originals = context['preimage']
    if original['kind'] != effect['kind'] or original['issue_id'] != effect['issue_id']:
        return None, None
    actual = {entity_id: current.get(entity_id) for entity_id in originals}
    for entity_id, reference in originals.items():
        if actual[entity_id] is None:
            actual[entity_id] = _fresh(reference, forge, counts)
    fingerprint = _native_fingerprints(actual)
    wanted_present = original['kind'] == 'native-add'
    applied = [pr_id for pr_id in original['pr_ids']
               if (pr_id in fingerprint[original['issue_id']]['relations']['manual']) == wanted_present]
    if not applied or len(applied) == len(original['pr_ids']):
        return None, None
    expected_partial = _native_postimage(originals, {**original, 'pr_ids': applied})
    if fingerprint != expected_partial:
        return None, None
    remaining = [pr_id for pr_id in original['pr_ids'] if pr_id not in applied]
    remaining_effect = _effect(original['kind'], issue_id=original['issue_id'], pr_ids=remaining)
    if effect['effect_id'] not in (original['effect_id'], remaining_effect['effect_id']):
        return None, None
    observation_sha256 = _digest(fingerprint)
    if mode == 'observe':
        receipt = {'attempt_id': previous['attempt_id'], 'effect_id': remaining_effect['effect_id'],
                   'original_effect_id': original['effect_id'], 'position': 'partial',
                   'preimage_sha256': observation_sha256, 'original_endpoint_ids': sorted(originals),
                   'applied_pr_ids': applied, 'remaining_pr_ids': remaining,
                   'observed_at': _instant(now).isoformat(), 'receipt_id': uuid.uuid4().hex}
        receipt['receipt_sha256'] = _digest(receipt)
        with _cache(state_root) as cache:
            live = cache.get('attempts', {}).get(key)
            if live is None or live['attempt_id'] != previous['attempt_id'] or live['status'] != 'attempted':
                raise ValueError('pending-attempt-changed')
            live.setdefault('observations', []).append(receipt)
        return {'status': 'needs-input', 'reason': 'prior-attempt-observed-partial',
                'mutation_attempted': False, 'remaining_effect_id': remaining_effect['effect_id'],
                **{name: value for name, value in receipt.items() if name != 'effect_id'}}, None
    if effect['effect_id'] != remaining_effect['effect_id'] or not renewal:
        return {'status': 'unknown', 'reason': 'partial-native-attempt-needs-observation',
                'mutation_attempted': False, 'attempt_id': previous['attempt_id']}, None
    return None, {'key': key, 'attempt_id': previous['attempt_id'], 'observation_sha256': observation_sha256,
                  'effect_id': remaining_effect['effect_id']}


def _settle_attempt(state_root, effect, actual, attempt_id=None):
    key = _digest(_attempt_targets(effect))
    with _cache(state_root) as cache:
        previous = cache.get('attempts', {}).get(key)
        if previous and previous['status'] == 'attempted' and previous['effect_id'] == effect['effect_id'] and previous['postimage_sha256'] == _digest(actual) and (attempt_id is None or attempt_id == previous['attempt_id']):
            previous['status'] = 'settled'


def _reserve_attempt(state_root, transition_id, effect, preimage, postimage, *, mode, renewal, now, plan, recovery=None):
    """Install one attempt atomically before any remote write can begin."""
    with _cache(state_root) as cache:
        if mode == 'apply':
            _validate_setting_generations(plan, cache)
        attempts = cache.setdefault('attempts', {})
        targets = _attempt_targets(effect)
        key = _digest(targets)
        recovered = None
        if recovery:
            recovered = attempts.get(recovery['key'])
            if recovered is None or recovered['attempt_id'] != recovery['attempt_id'] or recovered['status'] != 'attempted':
                raise ValueError('pending-attempt-changed')
            matches = [item for item in recovered.get('observations', []) if item.get('position') == 'partial'
                       and all(renewal.get(name) == item.get(name) for name in ('effect_id', 'attempt_id', 'receipt_id', 'receipt_sha256'))]
            if not matches or matches[-1]['preimage_sha256'] != recovery['observation_sha256'] or recovery['effect_id'] != effect['effect_id']:
                raise ValueError('partial-recovery-receipt-drift')
        overlapping = [item['attempt_id'] for other_key, item in attempts.items()
                       if other_key != key and item['status'] == 'attempted' and set(targets) & set(item['targets'])
                       and (not recovery or other_key != recovery['key'])]
        if overlapping:
            return None, {'status': 'unknown', 'reason': 'overlapping-pending-intent',
                          'mutation_attempted': False, 'attempt_ids': overlapping}
        previous = attempts.get(key)
        pending = previous is not None and previous['status'] == 'attempted'
        if mode == 'observe':
            if not pending:
                return None, {'status': 'needs-input', 'reason': 'effect-not-applied', 'mutation_attempted': False}
            receipt = {'attempt_id': previous['attempt_id'], 'effect_id': effect['effect_id'],
                       'position': 'preimage', 'preimage_sha256': _digest(preimage),
                       'observed_at': _instant(now).isoformat(), 'receipt_id': uuid.uuid4().hex}
            receipt['receipt_sha256'] = _digest(receipt)
            previous.setdefault('observations', []).append(receipt)
            return None, {'status': 'needs-input', 'reason': 'prior-attempt-observed-preimage',
                          'mutation_attempted': False, **receipt}
        if pending:
            receipts = previous.get('observations', [])
            matching = [item for item in receipts if renewal and all(renewal.get(key) == item.get(key) for key in ('effect_id', 'attempt_id', 'receipt_id', 'receipt_sha256'))]
            if not matching or matching[-1]['preimage_sha256'] != _digest(preimage):
                return None, {'status': 'unknown', 'reason': 'prior-attempt-unresolved',
                              'mutation_attempted': False, 'attempt_id': previous['attempt_id']}
        elif renewal and not recovery:
            raise ValueError('renewal-without-prior-attempt')
        sequence = previous['sequence'] + 1 if previous else 1
        attempt_id = _digest({'transition_id': transition_id, 'sequence': sequence})
        if recovered:
            recovered['status'] = 'superseded-by-authorized-remainder'
            recovered['superseded_by'] = attempt_id
            recovered['renewal_receipt_id'] = renewal['receipt_id']
        attempts[key] = {'attempt_id': attempt_id, 'effect_id': effect['effect_id'],
                                   'targets': targets, 'transition_id': transition_id,
                                   'postimage_sha256': _digest(postimage),
                                   'sequence': sequence, 'status': 'attempted', 'observations': [],
                                   'history': [*(previous.get('history', []) if previous else []),
                                               *([{key: value for key, value in previous.items() if key != 'history'}] if previous else [])]}
        if effect['kind'] in ('native-add', 'native-remove'):
            attempts[key]['native_context'] = {'effect': effect, 'preimage': _native_fingerprints(preimage)}
        if recovered:
            attempts[key]['predecessor_attempt_id'] = recovered['attempt_id']
        return attempt_id, None


def _apply_effect(effect, expected, forge, counts, state_root, *, mode, renewal, now, plan):
    body_change = effect['kind'] == 'issue-body'
    if body_change:
        ids = [effect['entity_id']]
        preimage = {ids[0]: _plain_entity(expected[ids[0]])}
        postimage = copy.deepcopy(preimage)
        postimage[ids[0]]['body'] = effect['candidate_body']
    elif effect['kind'] in ('native-add', 'native-remove'):
        ids = [effect['issue_id'], *effect['pr_ids']]
        if not 1 <= len(effect['pr_ids']) <= 10 or len(set(ids)) != len(ids):
            raise ValueError('invalid-native-batch')
        preimage = {entity_id: expected[entity_id] for entity_id in ids}
        postimage = _native_postimage(expected, effect)
    else:
        raise ValueError('unsupported-effect')
    current = {entity_id: _fresh(expected[entity_id], forge, counts, connections=not body_change) for entity_id in ids}
    recovery = None
    if not body_change:
        held, recovery = _native_recovery(effect, current, forge, counts, state_root, mode=mode, renewal=renewal, now=now)
        if held:
            return held, {}
    def updates(after):
        return {entity_id: {**expected[entity_id], **after[entity_id]} for entity_id in ids}
    if all(current[entity_id] == postimage[entity_id] for entity_id in ids):
        _settle_attempt(state_root, effect, current)
        return {'status': 'no-op', 'mutation_attempted': False}, updates(current)
    if any(current[entity_id] != preimage[entity_id] for entity_id in ids):
        return {'status': 'blocked', 'reason': 'affected-preimage-drift', 'mutation_attempted': False}, {}
    # Reserve the concrete transition before sending it. An interrupted process
    # must reobserve; seeing the old state does not prove a timed-out write failed.
    transition_id = _digest({'effect': effect, 'preimage': preimage})
    attempt_id, held = _reserve_attempt(state_root, transition_id, effect, preimage,
                                       {entity_id: postimage[entity_id] for entity_id in ids},
                                       mode=mode, renewal=renewal, now=now, plan=plan, recovery=recovery)
    if held:
        return held, {}
    response, uncertain = None, False
    try:
        if body_change:
            response = forge.write_issue_body(current[ids[0]], effect['candidate_body'])
            success = response.get('ok') is True and not response.get('errors')
        else:
            operation = 'add' if effect['kind'] == 'native-add' else 'remove'
            response = forge.change_native(operation, current[effect['issue_id']], [current[pr_id] for pr_id in effect['pr_ids']])
            success = not response.get('errors') and response.get('data', {}).get(operation + 'CloseIssueReferences') is not None
    except Exception:
        uncertain, success = True, False
    try:
        after = {entity_id: _fresh(expected[entity_id], forge, counts, connections=not body_change) for entity_id in ids}
    except Exception:
        return {'status': 'unknown', 'reason': 'post-mutation-observation-unavailable', 'mutation_attempted': True}, {}
    reached = all(after[entity_id] == postimage[entity_id] for entity_id in ids)
    unchanged = all(after[entity_id] == current[entity_id] for entity_id in ids)
    state_preserved = all(after[item]['state'] == current[item]['state'] for item in ids)
    if success and reached:
        try:
            _settle_attempt(state_root, effect, after, attempt_id)
        except (OSError, ValueError):
            return {'status': 'unknown', 'reason': 'attempt-settlement-unavailable',
                    'mutation_attempted': True, 'attempt_id': attempt_id}, {}
        return {'status': 'verified', 'mutation_attempted': True}, updates(after)
    if uncertain or reached:
        return {'status': 'unknown', 'reason': 'mutation-outcome-uncertain', 'mutation_attempted': True,
                'attempt_id': attempt_id, 'state_preserved': state_preserved}, {}
    if unchanged:
        return {'status': 'blocked', 'reason': 'mutation-errors', 'mutation_attempted': True}, {}
    return {'status': 'partial', 'reason': 'unexpected-postimage', 'mutation_attempted': True,
            'state_preserved': state_preserved}, {}

def _reconcile(document, forge, counts, state_root, now):
    plan = document['plan']
    unsigned = {key: value for key, value in plan.items() if key != 'plan_sha256'}
    authorization = document['authorization']
    if (document.get('version') != 1 or plan.get('version') != 1
            or plan.get('plan_sha256') != _digest(unsigned)
            or authorization.get('plan_sha256') != plan['plan_sha256']):
        raise ValueError('plan-or-authorization-drift')
    rebuilt = _plan({'version': 1, 'status': 'observed', 'request': plan['request'],
                     'entities': plan['entities'], 'settings': plan['settings']})
    if rebuilt != plan:
        raise ValueError('plan-does-not-match-decisions')
    effects = plan['effects']
    mode = document.get('mode', 'apply')
    if mode not in ('apply', 'observe'):
        raise ValueError('invalid-reconcile-mode')
    permitted = authorization.get('effect_ids', [])
    if len(set(permitted)) != len(permitted) or not set(permitted) <= {effect['effect_id'] for effect in effects}:
        raise ValueError('unbound-effect-authorization')
    renewals = authorization.get('renewals', [])
    renewal_by_effect = {item['effect_id']: item for item in renewals}
    if len(renewal_by_effect) != len(renewals) or not set(renewal_by_effect) <= set(permitted) or (mode == 'observe' and renewals):
        raise ValueError('unbound-renewal-authorization')
    if mode == 'apply':
        _check_settings(plan, state_root)
    pending = [item for item in plan['handoffs'] if item['kind'] != 'pr-publisher']
    supplied_results = document.get('publication_results', [])
    published = {item['entity_id']: item for item in supplied_results}
    if len(published) != len(supplied_results):
        raise ValueError('duplicate-publication-result')
    publisher_ids = {item['entity_id'] for item in plan['handoffs'] if item['kind'] == 'pr-publisher'}
    if not set(published) <= publisher_ids:
        raise ValueError('unbound-publication-result')
    pending.extend(item for item in plan['handoffs'] if item['kind'] == 'pr-publisher' and (item['entity_id'] not in published or published[item['entity_id']].get('status') != 'verified'))
    if pending:
        return {'version': 1, 'status': 'needs-input', 'reason': 'complete-owner-handoffs',
                'handoffs': pending, 'effects': [], 'read_counts': counts}
    expected = copy.deepcopy(plan['entities'])
    for handoff in plan['handoffs']:
        result = published[handoff['entity_id']]
        if (result.get('schema_version') != 1 or result.get('operation') != 'pr-relation-ledger'
                or any(result.get(key) != value for key, value in handoff['target'].items())
                or result.get('before_body_sha256') != handoff['expected_body_sha256']
                or result.get('after_body_sha256') != handoff['candidate_body_sha256']
                or result.get('title_sha256') != handoff['candidate']['title_sha256']
                or result.get('state') != handoff['preimage']['state']
                or result.get('is_draft') != handoff['preimage']['is_draft']
                or (result.get('no_op') is not True and (not result.get('receipt_id') or not re.fullmatch(r'[0-9a-f]{64}', result.get('receipt_sha256', ''))))):
            raise ValueError('publication-result-drift')
        entity_id = handoff['entity_id']
        actual = _fresh(expected[entity_id], forge, counts)
        wanted = copy.deepcopy(expected[entity_id])
        wanted['body'] = handoff['candidate_body']
        if actual != wanted:
            raise ValueError('publisher-postimage-drift')
        expected[entity_id].update(actual)
    outcomes = []
    for effect in effects:
        if effect['effect_id'] not in permitted:
            outcomes.append({'effect_id': effect['effect_id'], 'status': 'blocked', 'reason': 'effect-not-authorized', 'mutation_attempted': False})
            continue
        try:
            if mode == 'apply':
                _check_settings(plan, state_root)
            outcome, updates = _apply_effect(effect, expected, forge, counts, state_root,
                                             mode=mode, renewal=renewal_by_effect.get(effect['effect_id']), now=now, plan=plan)
        except (KeyError, TypeError, ValueError, OSError) as error:
            outcome, updates = {'status': 'blocked', 'reason': str(error), 'mutation_attempted': False}, {}
        outcomes.append({'effect_id': effect['effect_id'], **outcome})
        expected.update(updates)
        if outcome.get('state_preserved') is False:
            affected = expected[effect.get('issue_id', effect.get('entity_id'))]
            affected_key = affected['host'] + ':' + affected['repository']['id']
            try:
                with _cache(state_root) as cache:
                    for key, selected in plan.get('settings', {}).items():
                        if key == affected_key and selected['auto_close'] is False and key in cache['repositories']:
                            record = cache['repositories'][key]
                            _invalidate_setting(record, _instant(now))
            except (OSError, ValueError):
                outcomes[-1].update(status='unknown', reason='setting-invalidation-unavailable')
        if outcome['status'] not in ('verified', 'no-op'):
            break

    statuses = [item['status'] for item in outcomes]
    if 'unknown' in statuses:
        status = 'unknown'
    elif 'partial' in statuses:
        status = 'partial'
    elif 'needs-input' in statuses:
        status = 'needs-input'
    elif 'blocked' in statuses:
        status = 'partial' if any(item in ('verified', 'no-op') for item in statuses) else 'blocked'
    else:
        status = 'verified' if 'verified' in statuses else 'no-op'
    return {'version': 1, 'status': status, 'plan_sha256': plan['plan_sha256'],
            'effects': outcomes, 'read_counts': counts}

def execute(command, document, *, forge=None, state_root=None, now=None):
    """Run the public JSON command with an optional external forge adapter."""
    counts = {'entities': 0, 'connection_pages': 0, 'settings': 0,
              'external_read_requests': 0, 'external_write_requests': 0}
    if not isinstance(document, dict):
        return {'version': 1, 'status': 'blocked', 'reason': 'invalid-document', 'read_counts': counts}
    if forge is None and command != 'plan':
        spec = importlib.util.spec_from_file_location('relation_forge', Path(__file__).with_name('relation_forge.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        forge = module.GitHubForge(counts)
    if command == 'reconcile':
        try:
            return _reconcile(document, forge, counts, state_root, now)
        except (KeyError, TypeError, ValueError, OSError) as error:
            return {'version': 1, 'status': 'blocked', 'reason': str(error), 'read_counts': counts}
    if command == 'plan':
        try:
            return _plan(document)
        except (KeyError, TypeError, ValueError, OSError) as error:
            return {'version': 1, 'status': 'blocked', 'reason': str(error), 'read_counts': counts}
    if command == 'observe':
        applicability = document.get('applicability', {})
        if not isinstance(applicability, dict):
            return {'version': 1, 'status': 'blocked', 'reason': 'invalid-request', 'read_counts': counts}
        reason = applicability.get('reason')
        if document.get('version') != 1 or reason not in REASONS or type(applicability.get('active')) is not bool or not isinstance(document.get('task_id'), str) or not document['task_id']:
            return {'version': 1, 'status': 'blocked', 'reason': 'invalid-request', 'read_counts': counts}
        if applicability.get('active') is False:
            if any(document.get(key) for key in ('pairs', 'body_edits', 'invalidate_settings')):
                return {'version': 1, 'status': 'blocked', 'reason': 'inactive-with-pending-work', 'read_counts': counts}
            if reason not in INACTIVE_REASONS:
                return {'version': 1, 'status': 'blocked', 'reason': 'invalid-applicability', 'read_counts': counts}
            return {'version': 1, 'status': 'no-op', 'reason': reason, 'read_counts': counts}
        try:
            return _observe(document, forge, counts, state_root, now)
        except (KeyError, TypeError, ValueError, OSError) as error:
            return {'version': 1, 'status': 'blocked', 'reason': str(error), 'read_counts': counts}
    raise ValueError('unsupported relation command')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('observe', 'plan', 'reconcile'))
    parser.add_argument('--input', required=True, type=Path, help='UTF-8 JSON request, observation, or authorized plan')
    parser.add_argument('--state-root', type=Path, help='Override XDG state directory (use a temporary directory for tests)')
    args = parser.parse_args()
    try:
        document = json.loads(args.input.read_bytes().decode('utf-8'))
        result = execute(args.command, document, state_root=args.state_root)
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        result = {'version': 1, 'status': 'blocked', 'reason': type(error).__name__ + ': invalid-input'}
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0 if result['status'] in ('observed', 'ready', 'verified', 'no-op') else 1


if __name__ == '__main__':
    raise SystemExit(main())
