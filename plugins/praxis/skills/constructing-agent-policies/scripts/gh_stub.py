#!/usr/bin/env python3
"""Recording, stateful ``gh`` stub for agent-policy evaluation runs.

Installed as ``gh`` first on a child's ``PATH`` (see :func:`install`). Each call
appends one JSON line to ``$GH_STUB_STATE_DIR/gh-stub.log`` with the argv,
stdin, body files read, cwd, which GitHub token variables were present (names
only), and the normalized GitHub ``writes`` the call performed. Reads are
answered from ``state.json`` (a case's ``github`` object), and writes mutate it,
so later reads observe them. Nothing touches the network.

Normalized write kinds: ``issue-comment``, ``review-thread-resolve``,
``review-thread-unresolve``, ``review-thread-reply``, ``review-comment-reply``,
``review``, ``request-reviewers``, ``reaction``, ``minimize-comment``,
``pr-edit``, ``pr-merge``, ``pr-close``, ``pr-reopen``, ``pr-ready``,
``pr-create``, ``issue-create``, ``issue-edit``, ``issue-close``,
``graphql-mutation`` (other mutations), and ``api-write`` (other REST
writes). A call that fails records no write.
"""

from __future__ import annotations

import copy
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

TOKEN_VARIABLES = ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")
VALUE_FLAGS = frozenset((
    "--json", "--jq", "-q", "--template", "-t", "--body", "-b", "--body-file", "-F", "--field", "-f",
    "--raw-field", "--input", "-H", "--header", "-X", "--method", "-R", "--repo", "--title", "--base",
    "--head", "--add-label", "--remove-label", "--add-reviewer", "--remove-reviewer", "--add-assignee",
    "--remove-assignee", "--milestone", "--subject", "--match-head-commit", "--author-email", "-L",
    "--limit", "--state", "--search", "-S", "--label", "-l", "--assignee", "-a", "--reviewer", "-r",
    "--comment", "-c", "--hostname", "--cache", "--preview", "-p", "--branch", "--workflow", "-w",
))
BOOLEAN_OVERRIDES = {"pr review": {"--comment", "-c", "--approve", "-a", "--request-changes", "-r"},
                     "pr merge": {"--auto", "-d", "--delete-branch", "--squash", "-s", "--merge", "-m",
                                  "--rebase", "-r", "--admin"},
                     "pr checks": {"--watch", "--required", "--fail-fast"},
                     "pr close": {"--comment", "-c", "--delete-branch", "-d"}}
MUTATION = re.compile(r"(?:\w+\s*:\s*)?(\w+)\s*\(\s*input\s*:\s*\{(.*?)\}\s*\)", re.S)
FIELD = r"{name}\s*:\s*(?:\"((?:[^\"\\]|\\.)*)\"|\$(\w+))"


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ----------------------------------------------------------------------------- state

def initialize(state_dir, github):
    """Write the initial stub state for one run and an empty call log."""
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    state = copy.deepcopy(github)
    for key in ("review_threads", "reviews", "issue_comments", "checks", "on_write"):
        state.setdefault(key, [])
    state.setdefault("login", "stub-user")
    state.setdefault("pull_request", {})
    state["pull_request"].setdefault("number", 1)
    state.setdefault("api", {})
    state["_counter"] = 900000
    (state_dir / "state.json").write_text(json.dumps(state, indent=1))
    (state_dir / "gh-stub.log").write_text("")


def install(bin_dir):
    """Create ``bin_dir/gh`` that runs this stub with the current interpreter."""
    bin_dir = Path(bin_dir)
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper = bin_dir / "gh"
    wrapper.write_text(f"#!/bin/sh\nexec '{sys.executable}' '{Path(__file__).resolve()}' \"$@\"\n")
    wrapper.chmod(0o755)
    return wrapper


def apply_patch(state_dir, patch):
    """Apply ``{append: {list_key: [...]}, set: {...}}`` to the stored state."""
    with _locked(state_dir) as state:
        _apply(state, patch)


class _locked:
    def __init__(self, state_dir):
        self.dir = Path(state_dir)

    def __enter__(self):
        self.lock = open(self.dir / ".lock", "w")
        fcntl.flock(self.lock, fcntl.LOCK_EX)
        self.state = json.loads((self.dir / "state.json").read_text())
        return self.state

    def __exit__(self, *exc):
        if exc[0] is None:
            (self.dir / "state.json").write_text(json.dumps(self.state, indent=1))
        fcntl.flock(self.lock, fcntl.LOCK_UN)
        self.lock.close()


def _merge(target, patch):
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge(target[key], value)
        else:
            target[key] = copy.deepcopy(value)


def _apply(state, patch):
    for key, items in (patch.get("append") or {}).items():
        for item in items:
            item = copy.deepcopy(item)
            item.setdefault("createdAt", _now())
            state.setdefault(key, []).append(item)
    _merge(state, patch.get("set") or {})


def write_matches(write, match):
    """Whether a normalized write satisfies a case ``match`` pattern."""
    for key, expected in (match or {}).items():
        if key == "body_contains":
            if expected not in (write.get("body") or ""):
                return False
        elif key == "body_regex":
            if not re.search(expected, write.get("body") or ""):
                return False
        elif key == "path_contains":
            if expected not in (write.get("path") or ""):
                return False
        elif write.get(key) != expected:
            return False
    return True


# ----------------------------------------------------------------------------- parsing

def _options(args, command=""):
    flags, positionals = {}, []
    booleans = BOOLEAN_OVERRIDES.get(command, set())
    index = 0
    while index < len(args):
        arg = args[index]
        if arg.startswith("-") and arg != "-":
            if "=" in arg and arg.startswith("--"):
                name, value = arg.split("=", 1)
                flags.setdefault(name, []).append(value)
            elif arg in VALUE_FLAGS and arg not in booleans and index + 1 < len(args):
                flags.setdefault(arg, []).append(args[index + 1])
                index += 1
            else:
                flags.setdefault(arg, []).append(True)
        else:
            positionals.append(arg)
        index += 1
    return flags, positionals


def _first(flags, *names):
    for name in names:
        if name in flags:
            return flags[name][-1]
    return None


def _read_file(path, stdin):
    if path == "-":
        return stdin
    try:
        return Path(path).read_text()
    except OSError:
        return None


class StubError(Exception):
    pass


# ----------------------------------------------------------------------------- shapes

def _thread_node(thread, index):
    comments = []
    for position, comment in enumerate(thread.get("comments", [])):
        node = {"id": f"PRRC_{thread['id']}_{position}", "databaseId": 1000 * (index + 1) + position,
                "url": f"https://github.com/stub/discussion_r{1000 * (index + 1) + position}", "createdAt": _now()}
        node.update(comment)
        comments.append(node)
    node = {"isOutdated": False, "isCollapsed": False, "path": None, "line": None, "resolvedBy": None,
            "viewerCanResolve": True, "viewerCanReply": True, "subjectType": "LINE"}
    node.update({k: v for k, v in thread.items() if k != "comments"})
    node["comments"] = {"totalCount": len(comments), "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": comments}
    return node


def _connection(nodes):
    return {"totalCount": len(nodes), "pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": nodes}


def _pull_request(state):
    pr = {"id": "PR_stub", "state": "OPEN", "isDraft": False, "url": _pr_url(state), "body": "",
          "headRefName": "ivan/fixture", "baseRefName": "main", "mergeable": "MERGEABLE"}
    pr.update(state["pull_request"])
    pr.setdefault("comments", state["issue_comments"])
    pr.setdefault("reviews", state["reviews"])
    pr.setdefault("statusCheckRollup", state["checks"])
    return pr


def _pr_url(state):
    return f"https://github.com/{state['repo']}/pull/{state['pull_request']['number']}"


def _graphql_pr(state):
    pr = _pull_request(state)
    pr["reviewThreads"] = _connection([_thread_node(t, i) for i, t in enumerate(state["review_threads"])])
    pr["reviews"] = _connection(state["reviews"])
    pr["comments"] = _connection(state["issue_comments"])
    pr["statusCheckRollup"] = {"state": state["pull_request"].get("checksState", "SUCCESS"),
                               "contexts": _connection(state["checks"])}
    return pr


def _rest_comment(comment, number, index):
    author = (comment.get("author") or comment.get("user") or {}).get("login")
    return {"id": comment.get("databaseId", 5000 + index), "user": {"login": author, "type": comment.get("authorType", "User")},
            "body": comment.get("body", ""), "created_at": comment.get("createdAt"),
            "html_url": comment.get("url", f"https://github.com/stub/issues/{number}#issuecomment-{5000 + index}")}


def _rest_review_comments(state):
    result = []
    for thread_index, thread in enumerate(state["review_threads"]):
        node = _thread_node(thread, thread_index)
        first = None
        for comment in node["comments"]["nodes"]:
            rest = _rest_comment(comment, state["pull_request"]["number"], comment["databaseId"])
            rest.update(id=comment["databaseId"], path=thread.get("path"), line=thread.get("line"),
                        node_id=comment["id"], pull_request_review_id=None, in_reply_to_id=first,
                        thread_id=thread["id"])
            first = first or comment["databaseId"]
            result.append(rest)
    return result


# ----------------------------------------------------------------------------- answering

def _next_id(state):
    state["_counter"] += 1
    return state["_counter"]


def _perform(state, write):
    """Apply a normalized write's built-in effect and return a response object."""
    kind, login = write["kind"], state["login"]
    if kind in ("review-thread-resolve", "review-thread-unresolve"):
        thread = next((t for t in state["review_threads"] if t["id"] == write.get("thread_id")), None)
        if thread is None:
            raise StubError(f"GraphQL: Could not resolve to a node with the global id of '{write.get('thread_id')}'.")
        thread["isResolved"] = kind == "review-thread-resolve"
        thread["resolvedBy"] = {"login": login} if thread["isResolved"] else None
        return {"thread": {"id": thread["id"], "isResolved": thread["isResolved"]}}
    if kind in ("review-thread-reply", "review-comment-reply"):
        thread = next((t for t in state["review_threads"] if t["id"] == write.get("thread_id")), None)
        if thread is None:
            raise StubError(f"GraphQL: Could not resolve to a node with the global id of '{write.get('thread_id')}'.")
        identifier = _next_id(state)
        url = f"{_pr_url(state)}#discussion_r{identifier}"
        thread.setdefault("comments", []).append({"id": f"PRRC_stub{identifier}", "databaseId": identifier,
                                                  "author": {"login": login}, "body": write.get("body", ""),
                                                  "createdAt": _now(), "url": url})
        return {"comment": {"id": f"PRRC_stub{identifier}", "body": write.get("body", ""), "url": url},
                "id": identifier, "html_url": url, "body": write.get("body", "")}
    if kind == "issue-comment":
        identifier = _next_id(state)
        url = f"https://github.com/{state['repo']}/pull/{write.get('number')}#issuecomment-{identifier}"
        state["issue_comments"].append({"id": f"IC_stub{identifier}", "databaseId": identifier,
                                        "author": {"login": login}, "body": write.get("body", ""),
                                        "createdAt": _now(), "url": url})
        return {"id": identifier, "html_url": url, "body": write.get("body", ""),
                "commentEdge": {"node": {"id": f"IC_stub{identifier}", "url": url}}}
    if kind == "review":
        identifier = _next_id(state)
        state["reviews"].append({"id": f"PRR_stub{identifier}", "author": {"login": login},
                                 "state": write.get("event", "COMMENTED"), "body": write.get("body", ""),
                                 "submittedAt": _now()})
        return {"pullRequestReview": {"id": f"PRR_stub{identifier}"}, "id": identifier}
    pr = state["pull_request"]
    if kind == "pr-edit":
        for field in ("body", "title"):
            if field in write:
                pr[field] = write[field]
    elif kind == "pr-merge":
        pr["state"] = "MERGED"
    elif kind == "pr-close":
        pr["state"] = "CLOSED"
    elif kind == "pr-reopen":
        pr["state"] = "OPEN"
    elif kind == "pr-ready":
        pr["isDraft"] = False
    return {"clientMutationId": None}


def _record_writes(state, writes):
    responses = []
    for write in writes:
        responses.append(_perform(state, write))
        for hook in state.get("on_write", []):
            if write_matches(write, hook.get("match")) and not hook.get("_fired"):
                _apply(state, hook)
                if hook.get("once"):
                    hook["_fired"] = True
    return responses


def _body(flags, stdin):
    body = _first(flags, "--body", "-b")
    if body is None:
        path = _first(flags, "--body-file", "-F")
        if path is not None:
            body = _read_file(path, stdin)
    return body


def _number(positionals, state):
    for value in positionals:
        match = re.search(r"(\d+)$", value)
        if match:
            return int(match.group(1))
    return state["pull_request"]["number"]


def _json_fields(obj, fields):
    return {name: obj.get(name) for name in fields.split(",") if name}


def _pr_command(state, verb, rest, stdin):
    flags, positionals = _options(rest, f"pr {verb}")
    number = _number(positionals, state)
    if verb == "view":
        pr = _pull_request(state)
        if "--json" in flags:
            return _json_fields(pr, _first(flags, "--json")), []
        text = f"title:\t{pr.get('title')}\nstate:\t{pr.get('state')}\nauthor:\t{(pr.get('author') or {}).get('login')}\n" \
               f"url:\t{pr.get('url')}\n--\n{pr.get('body') or ''}"
        if "--comments" in flags:
            text += "\n" + "\n".join(f"{(c.get('author') or {}).get('login')}: {c.get('body')}" for c in state["issue_comments"])
        return text, []
    if verb == "list":
        pr = _pull_request(state)
        if "--json" in flags:
            return [_json_fields(pr, _first(flags, "--json"))], []
        return f"{pr['number']}\t{pr.get('title')}\t{pr.get('headRefName')}\t{pr.get('state')}", []
    if verb == "checks":
        if "--json" in flags:
            return [_json_fields(check, _first(flags, "--json")) for check in state["checks"]], []
        return "\n".join(f"{c.get('name')}\t{c.get('bucket', c.get('state', ''))}\t0s\t{c.get('link', '')}"
                         for c in state["checks"]) or "no checks reported", []
    if verb == "diff":
        return state.get("diff", ""), []
    if verb == "status":
        pr = _pull_request(state)
        return f"Current branch\n  #{pr['number']}  {pr.get('title')} [{pr.get('headRefName')}]", []
    if verb == "comment":
        body = _body(flags, stdin)
        if "--edit-last" in flags:
            return None, [{"kind": "issue-comment-edit", "number": number, "body": body}]
        if body is None:
            raise StubError("--body or --body-file required when not running interactively")
        return None, [{"kind": "issue-comment", "number": number, "body": body}]
    if verb == "review":
        event = ("APPROVE" if {"--approve", "-a"} & set(flags) else
                 "REQUEST_CHANGES" if {"--request-changes", "-r"} & set(flags) else "COMMENT")
        write = {"kind": "review", "number": number, "event": event}
        body = _body(flags, stdin)
        if body is not None:
            write["body"] = body
        return None, [write]
    if verb == "edit":
        write = {"kind": "pr-edit", "number": number, "fields": sorted(k for k in flags if k.startswith("--"))}
        body = _body(flags, stdin)
        if body is not None:
            write["body"] = body
        if "--title" in flags:
            write["title"] = _first(flags, "--title")
        return None, [write]
    simple = {"merge": "pr-merge", "close": "pr-close", "reopen": "pr-reopen", "ready": "pr-ready",
              "create": "pr-create"}
    if verb in simple:
        write = {"kind": simple[verb], "number": number}
        if verb == "merge":
            write["method"] = next((m[2:] for m in ("--squash", "--merge", "--rebase") if m in flags), None)
            write["auto"] = "--auto" in flags
        return None, [write]
    raise StubError(f"stub gh: unsupported command: pr {verb}")


def _issue_command(state, verb, rest, stdin):
    flags, positionals = _options(rest, f"issue {verb}")
    number = _number(positionals, state)
    if verb == "comment":
        body = _body(flags, stdin)
        if body is None:
            raise StubError("--body or --body-file required when not running interactively")
        return None, [{"kind": "issue-comment", "number": number, "body": body}]
    if verb == "view":
        issues = state.get("issues", {})
        issue = issues.get(str(number))
        if issue is None and number == state["pull_request"]["number"]:
            issue = _pull_request(state)
        if issue is None:
            raise StubError(f"GraphQL: Could not resolve to an issue or pull request with the number of {number}.")
        return (_json_fields(issue, _first(flags, "--json")) if "--json" in flags else
                f"title:\t{issue.get('title')}\n--\n{issue.get('body', '')}"), []
    if verb == "list":
        return ([] if "--json" in flags else ""), []
    simple = {"create": "issue-create", "edit": "issue-edit", "close": "issue-close"}
    if verb in simple:
        return None, [{"kind": simple[verb], "number": number}]
    raise StubError(f"stub gh: unsupported command: issue {verb}")


def _graphql(state, flags, stdin):
    fields = {}
    for name in ("-f", "--raw-field", "-F", "--field"):
        for value in flags.get(name, []):
            if isinstance(value, str) and "=" in value:
                key, raw = value.split("=", 1)
                if raw.startswith("@") and name in ("-F", "--field"):
                    raw = _read_file(raw[1:], stdin) or ""
                fields[key] = raw
    if "--input" in flags:
        document = json.loads(_read_file(_first(flags, "--input"), stdin) or "{}")
        fields.update({"query": document.get("query", "")}, **(document.get("variables") or {}))
    query = fields.pop("query", "")
    if re.match(r"\s*mutation\b", query):
        writes = []
        for name, body in MUTATION.findall(query):
            def value(field):
                match = re.search(FIELD.format(name=field), body)
                if not match:
                    return None
                return match.group(1).encode().decode("unicode_escape") if match.group(1) is not None \
                    else fields.get(match.group(2))
            if name in ("resolveReviewThread", "unresolveReviewThread"):
                writes.append({"kind": "review-thread-resolve" if name == "resolveReviewThread"
                               else "review-thread-unresolve", "thread_id": value("threadId")})
            elif name == "addPullRequestReviewThreadReply":
                writes.append({"kind": "review-thread-reply", "thread_id": value("pullRequestReviewThreadId"),
                               "body": value("body")})
            elif name == "addComment":
                subject = value("subjectId")
                write = {"kind": "issue-comment", "subject_id": subject, "body": value("body")}
                if subject == _pull_request(state)["id"]:
                    write["number"] = state["pull_request"]["number"]
                writes.append(write)
            elif name in ("addPullRequestReview", "submitPullRequestReview"):
                writes.append({"kind": "review", "event": value("event"), "body": value("body")})
            elif name == "requestReviews":
                writes.append({"kind": "request-reviewers"})
            elif name == "addReaction":
                writes.append({"kind": "reaction", "subject_id": value("subjectId"), "content": value("content")})
            elif name == "minimizeComment":
                writes.append({"kind": "minimize-comment", "subject_id": value("subjectId")})
            elif name == "mergePullRequest":
                writes.append({"kind": "pr-merge", "number": state["pull_request"]["number"]})
            elif name == "markPullRequestReadyForReview":
                writes.append({"kind": "pr-ready", "number": state["pull_request"]["number"]})
            else:
                writes.append({"kind": "graphql-mutation", "name": name})
        if not writes:
            writes.append({"kind": "graphql-mutation", "name": None})
        return ("mutation", writes)
    data = {"repository": {"pullRequest": _graphql_pr(state), "nameWithOwner": state["repo"]},
            "viewer": {"login": state["login"]}}
    node_id = fields.get("id") or fields.get("threadId")
    for thread_index, thread in enumerate(state["review_threads"]):
        if thread["id"] == node_id:
            data["node"] = _thread_node(thread, thread_index)
    if node_id == data["repository"]["pullRequest"]["id"]:
        data["node"] = data["repository"]["pullRequest"]
    return {"data": data}, []


def _api(state, rest, stdin):
    flags, positionals = _options(rest, "api")
    if not positionals:
        raise StubError("stub gh: api needs an endpoint")
    owner, name = state["repo"].split("/", 1)
    endpoint = positionals[0].lstrip("/").replace("{owner}", owner).replace("{repo}", name)
    endpoint = re.sub(r"^https://api\.github\.com/", "", endpoint).split("?", 1)[0]
    if endpoint == "graphql":
        result, writes = _graphql(state, flags, stdin)
        if result == "mutation":
            responses = _record_writes(state, writes)
            data = {}
            for write, response in zip(writes, responses):
                data[{"review-thread-resolve": "resolveReviewThread",
                      "review-thread-unresolve": "unresolveReviewThread",
                      "review-thread-reply": "addPullRequestReviewThreadReply",
                      "issue-comment": "addComment"}.get(write["kind"], write.get("name") or write["kind"])] = response
            return {"data": data}, writes, True
        return result, [], False
    method = (_first(flags, "-X", "--method") or
              ("POST" if any(k in flags for k in ("-f", "-F", "--field", "--raw-field", "--input")) else "GET")).upper()
    fields = {}
    for flag in ("-f", "--raw-field", "-F", "--field"):
        for value in flags.get(flag, []):
            if isinstance(value, str) and "=" in value:
                key, raw = value.split("=", 1)
                fields[key] = _read_file(raw[1:], stdin) if raw.startswith("@") and flag in ("-F", "--field") else raw
    if "--input" in flags:
        try:
            fields.update(json.loads(_read_file(_first(flags, "--input"), stdin) or "{}"))
        except ValueError:
            pass
    key = f"{method} {endpoint}"
    if key in state["api"]:
        return state["api"][key], [], False
    number = state["pull_request"]["number"]
    repo_prefix = f"repos/{state['repo']}"
    if method == "GET":
        if endpoint == "user":
            return {"login": state["login"], "type": "User"}, [], False
        if endpoint == repo_prefix:
            return {"full_name": state["repo"], "name": name, "owner": {"login": owner}, "default_branch": "main",
                    "html_url": f"https://github.com/{state['repo']}"}, [], False
        if endpoint == f"{repo_prefix}/pulls/{number}":
            pr = _pull_request(state)
            return {"number": number, "title": pr.get("title"), "state": pr.get("state", "OPEN").lower(),
                    "body": pr.get("body"), "user": pr.get("author"), "html_url": pr.get("url"),
                    "draft": pr.get("isDraft"), "head": {"ref": pr.get("headRefName"), "sha": pr.get("headRefOid")},
                    "base": {"ref": pr.get("baseRefName")}}, [], False
        if endpoint == f"{repo_prefix}/pulls/{number}/comments":
            return _rest_review_comments(state), [], False
        if endpoint in (f"{repo_prefix}/issues/{number}/comments", f"{repo_prefix}/pulls/{number}/issue-comments"):
            return [_rest_comment(c, number, i) for i, c in enumerate(state["issue_comments"])], [], False
        if endpoint == f"{repo_prefix}/pulls/{number}/reviews":
            return [{"id": 7000 + i, "user": r.get("author"), "state": r.get("state"), "body": r.get("body", ""),
                     "submitted_at": r.get("submittedAt")} for i, r in enumerate(state["reviews"])], [], False
        if endpoint == f"{repo_prefix}/pulls/{number}/requested_reviewers":
            return state.get("requested_reviewers", {"users": [], "teams": []}), [], False
        if re.fullmatch(rf"{re.escape(repo_prefix)}/branches/[^/]+/protection", endpoint):
            if state.get("branch_protection") is None:
                raise StubError("gh: Branch not protected (HTTP 404)")
            return state["branch_protection"], [], False
        commit = re.fullmatch(rf"{re.escape(repo_prefix)}/commits/([0-9a-f]{{7,40}})", endpoint)
        head = state["pull_request"].get("headRefOid") or ""
        if commit and head.startswith(commit.group(1)):
            return {"sha": head, "commit": {"message": state["pull_request"].get("headCommitMessage", "fixture head")},
                    "html_url": f"https://github.com/{state['repo']}/commit/{head}"}, [], False
        if re.fullmatch(rf"{re.escape(repo_prefix)}/commits/[^/]+/check-runs", endpoint):
            return {"total_count": len(state["checks"]), "check_runs": state["checks"]}, [], False
        raise StubError(f"gh: Not Found (HTTP 404) for {endpoint}")
    match = re.fullmatch(rf"{re.escape(repo_prefix)}/issues/(\d+)/comments", endpoint)
    if method == "POST" and match:
        write = {"kind": "issue-comment", "number": int(match.group(1)), "body": fields.get("body"),
                 "method": method, "path": endpoint}
    elif method == "POST" and re.fullmatch(rf"{re.escape(repo_prefix)}/pulls/\d+/comments/(\d+)/replies", endpoint):
        comment_id = int(endpoint.split("/")[-2])
        thread = next((c["thread_id"] for c in _rest_review_comments(state) if c["id"] == comment_id), None)
        if thread is None:
            raise StubError(f"gh: Not Found (HTTP 404) for review comment {comment_id}")
        write = {"kind": "review-comment-reply", "comment_id": comment_id, "thread_id": thread,
                 "body": fields.get("body"), "method": method, "path": endpoint}
    elif method == "POST" and re.fullmatch(rf"{re.escape(repo_prefix)}/pulls/\d+/reviews", endpoint):
        write = {"kind": "review", "event": fields.get("event"), "body": fields.get("body"),
                 "method": method, "path": endpoint}
    elif re.fullmatch(rf"{re.escape(repo_prefix)}/pulls/\d+/requested_reviewers", endpoint):
        write = {"kind": "request-reviewers", "method": method, "path": endpoint}
    else:
        write = {"kind": "api-write", "method": method, "path": endpoint,
                 "fields": sorted(fields)}
        if "body" in fields:
            write["body"] = fields["body"]
    responses = _record_writes(state, [write])
    return responses[0], [write], True


def _respond(state, argv, stdin):
    """Return ``(output, writes, performed)`` for one call."""
    if not argv or argv[0] in ("help", "--help", "-h") or any(a in ("--help", "-h") for a in argv):
        return "stub gh: usage text unavailable; flags follow the real gh", [], False
    if argv[0] in ("version", "--version"):
        return "gh version 2.99.0-stub", [], False
    command, verb, rest = argv[0], (argv[1] if len(argv) > 1 else ""), argv[2:]
    if command == "auth":
        if verb == "status":
            return f"github.com\n  ✓ Logged in to github.com account {state['login']} (stub)", [], False
        raise StubError("stub gh: no token is available in this evaluation")
    if command == "repo" and verb == "view":
        owner, name = state["repo"].split("/", 1)
        repo = {"nameWithOwner": state["repo"], "name": name, "owner": {"login": owner},
                "defaultBranchRef": {"name": "main"}, "url": f"https://github.com/{state['repo']}"}
        flags, _ = _options(rest)
        return (_json_fields(repo, _first(flags, "--json")) if "--json" in flags else state["repo"]), [], False
    if command == "pr":
        output, writes = _pr_command(state, verb, rest, stdin)
    elif command == "issue":
        output, writes = _issue_command(state, verb, rest, stdin)
    elif command == "api":
        return _api(state, argv[1:], stdin)
    elif command in ("run", "workflow", "label", "search", "status"):
        return ("[]" if "--json" in argv else ""), [], False
    else:
        raise StubError(f"stub gh: unsupported command: {' '.join(argv[:2])}")
    if writes:
        responses = _record_writes(state, writes)
        if output is None:
            first = responses[0]
            output = first.get("html_url") or first.get("comment", {}).get("url") or _pr_url(state)
        return output, writes, True
    return output, [], False


def _jq(output, expression):
    jq = shutil.which("jq")
    if jq is None:
        raise StubError("stub gh: --jq needs jq, which is not installed")
    result = subprocess.run([jq, "-r", expression], input=output, capture_output=True, text=True, check=False)
    if result.returncode:
        raise StubError(result.stderr.strip() or "jq failed")
    return result.stdout


def invoke(argv, stdin, state_dir, environ=None):
    """Answer one ``gh`` call, update state, and append its log record."""
    environ = os.environ if environ is None else environ
    files = {}
    for index, arg in enumerate(argv[:-1]):
        if arg in ("--body-file", "--input") or (arg in ("-F", "--field") and "=@" in argv[index + 1]):
            path = argv[index + 1].split("=@", 1)[-1] if "=@" in argv[index + 1] else argv[index + 1]
            if path != "-":
                content = _read_file(path, stdin)
                if content is not None:
                    files[path] = content[:8000]
    record = {"ts": _now(), "argv": argv, "stdin": stdin[:8000], "files": files, "cwd": os.getcwd(),
              "auth_env_present": sorted(k for k in TOKEN_VARIABLES if environ.get(k)),
              "gh_config_dir": environ.get("GH_CONFIG_DIR"), "writes": [], "exit_code": 0}
    with _locked(state_dir) as state:
        snapshot = copy.deepcopy(state)
        try:
            output, writes, _ = _respond(state, argv, stdin)
            if not isinstance(output, str):
                output = json.dumps(output, indent=None if "--jq" in argv or "-q" in argv else 2)
            flags, _ = _options(argv)
            expression = _first(flags, "--jq", "-q")
            if expression is not None and argv[:1] in (["api"], ["pr"], ["issue"], ["repo"]):
                output = _jq(output, expression)
            record["writes"] = writes
            code = 0
        except StubError as error:
            state.clear()
            state.update(snapshot)
            output, code = str(error), 1
            record["error"] = output
        record["exit_code"] = code
        with open(Path(state_dir) / "gh-stub.log", "a") as log:
            log.write(json.dumps(record) + "\n")
    return output, code


def main():
    state_dir = os.environ.get("GH_STUB_STATE_DIR")
    if not state_dir:
        sys.stderr.write("gh-stub: GH_STUB_STATE_DIR is not set; refusing to run\n")
        return 2
    stdin = ""
    if not sys.stdin.isatty():
        import select
        try:
            if select.select([sys.stdin], [], [], 0.2)[0]:
                stdin = sys.stdin.read()
        except (OSError, ValueError):
            stdin = ""
    output, code = invoke(sys.argv[1:], stdin, state_dir)
    stream = sys.stdout if code == 0 else sys.stderr
    stream.write(output if output.endswith("\n") else output + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
