"""Narrow GitHub transport for the qualified Issue–PR relation operations."""

from __future__ import annotations

import json
import subprocess


class GitHubForge:
    def __init__(self, counts):
        self.counts = counts
        self.first_pages = {}

    def _graphql(self, query, variables, *, mutation=False):
        counter = 'external_write_requests' if mutation else 'external_read_requests'
        self.counts[counter] += 1
        try:
            result = subprocess.run(
                ['gh', 'api', 'graphql', '--hostname', 'github.com', '--input', '-'],
                input=json.dumps({'query': query, 'variables': variables}),
                text=True, capture_output=True, timeout=60,
            )
            response = json.loads(result.stdout)
        except (OSError, subprocess.TimeoutExpired, ValueError) as error:
            raise OSError('github-response-unavailable') from error
        if not isinstance(response, dict):
            raise OSError('github-response-unavailable')
        if mutation:
            # GraphQL may return both data and errors, including on a nonzero exit.
            if result.returncode and not response.get('errors'):
                response['errors'] = [{'type': 'TRANSPORT_ERROR'}]
            return response
        if result.returncode or response.get('errors') or not response.get('data'):
            raise OSError('github-observation-unavailable')
        return response['data']

    @staticmethod
    def _connection(kind, provenance, *, after=False):
        field = 'closedByPullRequestsReferences' if kind == 'Issue' else 'closingIssuesReferences'
        args = ['first:100']
        if after:
            args.append('after:$cursor')
        if kind == 'Issue':
            args.append('includeClosedPrs:true')
        if provenance == 'manual':
            args.append('userLinkedOnly:true')
        elif provenance == 'detected':
            args.append('excludeUserLinked:true')
        return provenance + ':' + field + '(' + ','.join(args) + ') { totalCount nodes { id } pageInfo { hasNextPage endCursor } }'

    @staticmethod
    def _page(value):
        return {'nodes': value['nodes'], 'total_count': value['totalCount'],
                'page_info': {'has_next_page': value['pageInfo']['hasNextPage'],
                              'end_cursor': value['pageInfo']['endCursor']}}

    def read_entity(self, reference):
        fields = 'id number url title body state repository { id nameWithOwner visibility defaultBranchRef { name } }'
        fragments = []
        for kind in ('Issue', 'PullRequest'):
            connections = ' '.join(self._connection(kind, mode) for mode in ('all', 'manual', 'detected'))
            specific = 'isDraft baseRefName headRefOid' if kind == 'PullRequest' else ''
            fragments.append(f'... on {kind} {{ {fields} {specific} {connections} }}')
        query = 'query($id:ID!) { node(id:$id) { __typename ' + ' '.join(fragments) + ' } }'
        node = self._graphql(query, {'id': reference['id']})['node']
        if not node or node['__typename'] not in ('Issue', 'PullRequest'):
            raise ValueError('entity-not-found-or-unsupported')
        repository = node['repository']
        entity = {key: node[key] for key in ('id', 'number', 'url', 'title', 'body', 'state')}
        entity.update(host=reference['host'], kind=node['__typename'], repository={
            'id': repository['id'], 'name': repository['nameWithOwner'], 'visibility': repository['visibility'],
            'default_branch': (repository.get('defaultBranchRef') or {}).get('name'),
        })
        if node['__typename'] == 'PullRequest':
            entity.update(is_draft=node['isDraft'], base_ref=node['baseRefName'], head_oid=node['headRefOid'])
        self.first_pages[entity['id']] = {mode: self._page(node[mode]) for mode in ('all', 'manual', 'detected')}
        return entity

    def read_connection_page(self, entity, provenance, cursor):
        if cursor is None:
            return self.first_pages[entity['id']].pop(provenance)
        connection = self._connection(entity['kind'], provenance, after=True)
        query = f"query($id:ID!,$cursor:String) {{ node(id:$id) {{ ... on {entity['kind']} {{ {connection} }} }} }}"
        node = self._graphql(query, {'id': entity['id'], 'cursor': cursor})['node']
        return self._page(node[provenance])

    def change_native(self, operation, issue, prs):
        if operation not in ('add', 'remove') or not 1 <= len(prs) <= 10:
            raise ValueError('unsupported-native-mutation')
        query = f'mutation($issue:ID!,$prs:[ID!]!) {{ {operation}CloseIssueReferences(input:{{issueId:$issue,pullRequestIds:$prs}}) {{ clientMutationId }} }}'
        return self._graphql(query, {'issue': issue['id'], 'prs': [pr['id'] for pr in prs]}, mutation=True)

    def write_issue_body(self, entity, candidate_body):
        if entity['kind'] != 'Issue':
            raise ValueError('issue-body-target-required')
        query = 'mutation($id:ID!,$body:String!) { updateIssue(input:{id:$id,body:$body}) { issue { id } } }'
        response = self._graphql(query, {'id': entity['id'], 'body': candidate_body}, mutation=True)
        result = (response.get('data') or {}).get('updateIssue') or {}
        return {'ok': not response.get('errors') and (result.get('issue') or {}).get('id') == entity['id'],
                'errors': response.get('errors', [])}
