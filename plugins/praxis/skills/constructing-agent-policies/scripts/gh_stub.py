#!/usr/bin/env python3
"""Recording, stateful ``gh`` stub for agent-policy evaluation runs.

Installed as ``gh`` first on a child's ``PATH`` (see :func:`install`). Each call
appends one JSON line to ``$GH_STUB_STATE_DIR/gh-stub.log`` with the argv,
stdin, body files read, cwd, which GitHub token variables were present (names
only), the operator ``turn`` in progress, and the normalized GitHub ``writes``
the call performed. Reads are answered from ``state.json`` (a case's ``github``
object), and writes mutate it, so later reads observe them. Nothing touches the
network. ``-R/--repo`` and ``--hostname`` are accepted anywhere; a repository
other than the case's answers "not found".

GraphQL documents are parsed and answered with exactly the selection they
request (aliases, fragments, ``@include``/``@skip``, connections with
``first``/``after`` pagination), from ``repository``, ``viewer``, ``node``,
``nodes`` and ``user``. REST serves the pull request, its review comments,
issue comments, reviews, requested reviewers, commits, files, check runs, and
single comments by id; ``api`` extras in the state override any GET.

Normalized write kinds: ``issue-comment``, ``issue-comment-edit``,
``review-thread-resolve``, ``review-thread-unresolve``, ``review-thread-reply``,
``review-comment-reply``, ``review-comment`` (a standalone inline comment,
which opens a thread of its own: ``file``, ``line``, ``body``, and
``review_id`` when added to a pending review; from REST ``POST
.../pulls/N/comments`` without ``in_reply_to`` and GraphQL
``addPullRequestReviewThread``/``addPullRequestReviewComment``), ``review``
(``event``: ``APPROVE``, ``REQUEST_CHANGES``, ``COMMENT``, or ``null`` for a
pending review, from ``gh pr review``, REST ``POST .../reviews`` and GraphQL
``addPullRequestReview``/``submitPullRequestReview``; its inline ``comments``
(``[{path, line, body}]``, from REST ``comments[]`` and GraphQL ``comments``
and ``threads``) each open a thread linked to the review and are read back
with it), ``request-reviewers`` (``reviewers``, ``action: add|remove``),
``reaction``, ``minimize-comment``, ``pr-edit``, ``pr-merge`` (``method``,
``auto``, ``admin``), ``pr-merge-disable-auto``, ``pr-close``, ``pr-reopen``,
``pr-ready``, ``pr-create``, ``issue-create``, ``issue-edit``, ``issue-close``,
``git-push`` (``branch``, ``sha``; recorded by the fixture remote's
``post-receive`` hook; a push to the base branch whose history contains the
pull request's head marks it ``MERGED`` and adds ``merged_pull_request``),
``graphql-mutation`` (other mutations), and ``api-write`` (other REST writes).
``body_contains`` and ``body_regex`` match a write's ``body`` or any of its
inline ``comments``. A call that fails records no write, with two exceptions.
A denied one: a write matching a ``deny_writes`` rule (``[{match, message}]``,
``match`` as in ``write_checks``, including ``turn``; pushes are never denied)
fails the whole call with ``message`` on stderr and exit 1, changes no state,
and records ``{kind: "denied-write", denied_kind, turn}``. A rejected one: a
review request naming a non-collaborator fails as GitHub does (422, "Reviews
may only be requested from collaborators"), changes no state, and records
``{kind: "rejected-write", rejected_kind: "request-reviewers", reason:
"not-a-collaborator", reviewers, action, number, turn}``. A login counts as a
collaborator unless a ``GET repos/<repo>/collaborators`` API extra (or a
top-level ``collaborators`` list of logins) omits it or its ``GET
repos/<repo>/collaborators/<login>/permission`` extra says ``none``; a
permission of ``triage`` or above, an ``associations`` entry of ``OWNER``,
``MEMBER`` or ``COLLABORATOR``, the case login, the owner, and teams always
pass, and with no evidence at all every login passes. The ``claude`` and
``codex`` shims ``install_model_shims`` puts beside the ``gh`` wrapper refuse
a nested model run with exit 1 and record ``{kind: "nested-model-run",
program, argv, turn}``.

The repository (``gh repo view``, REST ``GET repos/<repo>``, GraphQL
``repository``) allows squash, merge and rebase merges and keeps merged
branches unless the case's ``GET repos/<repo>`` API extra says otherwise; that
extra merges over the object (``allow_squash_merge``, ``allow_merge_commit``,
``allow_rebase_merge``, ``delete_branch_on_merge``, ``private``,
``visibility``, ``description``, anything else) instead of replacing it. ``gh
pr checks --required`` and a check's GraphQL ``isRequired`` follow
``branch_protection.required_status_checks`` (``contexts`` or ``checks[]``)
unless the check carries its own ``isRequired``. ``gh run list`` reports one
workflow run per check run of the named branch (``--branch``; every branch
without it): the pull request's ``checks`` for its head branch, a ``GET
repos/<repo>/commits/<branch>/check-runs`` extra for another, a base check
taking its workflow name from the head check of the same name; ``--workflow``,
``--status``, ``--commit``, ``--limit`` and ``--json`` filter and shape it, and
no run at all prints nothing, as ``gh`` does off a terminal.

Identities are functions of the fixture, not of the run: an issue comment's of
its author and body, a review's of its author, state and body, a thread
comment's of its thread, author and body (repeats within one list take a
suffix), so every read, restatement and repetition of a case reports the same
ids, and a pending review keeps the time it was opened.

State patches (``on_write`` hooks, ``on_push``, and the runner's
``before_turn``) are ``{advance?, append?, set?, update_threads?}``. The stub
keeps its own clock, wall time plus every ``advance`` applied so far (seconds,
or ``<N>`` with unit ``s``, ``m``, ``h`` or ``d``; it moves the clock forward
before the rest of the patch renders and never rewrites an existing time), and
:func:`current_time` reads it. Writes, defaulted times and ``{{now}}``
placeholders use that clock, and once it has advanced every log record carries
``clock`` beside the wall-clock ``ts``. A patch's placeholders render when it
is applied, ``{{head}}`` and ``{{base}}`` as the commits current then;
placeholders still in the initial state render at initialization. Appended
issue comments, reviews, and thread comments without a time take the
application time, and ``update_threads`` keeps a restated comment's identity by
its author and body even when its time moves.
"""

from __future__ import annotations

import base64
import copy
import datetime as dt
import fcntl
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

TOKEN_VARIABLES = ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")
VALUE_FLAGS = frozenset((
    "--json", "--jq", "-q", "--template", "-t", "--body", "-b", "--body-file", "-F", "--field", "-f",
    "--raw-field", "--input", "-H", "--header", "-X", "--method", "-R", "--repo", "--title", "--base",
    "--head", "--add-label", "--remove-label", "--add-reviewer", "--remove-reviewer", "--add-assignee",
    "--remove-assignee", "--milestone", "--subject", "--match-head-commit", "--author-email", "-L",
    "--limit", "--state", "--search", "-S", "--label", "-l", "--assignee", "-a", "--reviewer", "-r",
    "--comment", "-c", "--hostname", "--cache", "--preview", "-p", "--branch", "--workflow", "-w",
    "--status", "-s", "--event", "-e", "--commit", "--user", "-u",
))
BOOLEAN_OVERRIDES = {"pr review": {"--comment", "-c", "--approve", "-a", "--request-changes", "-r"},
                     "pr merge": {"--auto", "-d", "--delete-branch", "--squash", "-s", "--merge", "-m",
                                  "--rebase", "-r", "--admin", "--disable-auto"},
                     "pr checks": {"--watch", "--required", "--fail-fast"},
                     "pr close": {"--comment", "-c", "--delete-branch", "-d"}}
PLACEHOLDER = re.compile(r"\{\{(?:now(?:([+-])(\d+)([smhd]))?|(head|base|pushed))\}\}")
UNITS = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
DEFAULT_HEAD_BRANCH = "nisavid/update"
KNOWN_BOTS = frozenset(("coderabbitai", "copilot-pull-request-reviewer", "github-actions", "dependabot",
                        "renovate", "sonarcloud", "codecov", "vercel", "netlify", "gemini-code-assist",
                        "sourcery-ai", "greptile-apps", "cursor", "chatgpt-codex-connector", "claude"))
ZERO_OID = "0" * 40
REVIEW_STATES = {"APPROVE": "APPROVED", "REQUEST_CHANGES": "CHANGES_REQUESTED", "COMMENT": "COMMENTED"}
REPO_DEFAULTS = {"allow_squash_merge": True, "allow_merge_commit": True, "allow_rebase_merge": True,
                 "delete_branch_on_merge": False, "private": False, "visibility": "public", "description": None}
COLLABORATOR_PERMISSIONS = frozenset(("triage", "write", "maintain", "admin"))
COLLABORATOR_ASSOCIATIONS = frozenset(("OWNER", "MEMBER", "COLLABORATOR"))
TERMINAL_STATES = frozenset(("SUCCESS", "FAILURE", "NEUTRAL", "SKIPPED", "CANCELLED", "TIMED_OUT", "ERROR",
                             "ACTION_REQUIRED", "STALE", "STARTUP_FAILURE"))
LATE_KEYS = ("on_write", "on_push")
DURATION = re.compile(r"\+?(\d+)([smhd])")


def _iso(moment):
    return moment.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _moment(state=None):
    """The stub's clock as a datetime: UTC wall time plus the run's ``advance`` offset when ``state`` is given."""
    moment = dt.datetime.now(dt.timezone.utc)
    offset = (state or {}).get("_clock_offset")
    return moment + dt.timedelta(seconds=offset) if offset else moment


def _now(state=None):
    """The stub's clock as ISO text; without ``state``, the wall clock (log timestamps)."""
    return _iso(_moment(state))


def _seconds(value):
    """An ``advance`` value as whole seconds: a non-negative number, or ``<N>`` with unit ``s``, ``m``, ``h`` or ``d``."""
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
        return int(value)
    match = DURATION.fullmatch(value.strip()) if isinstance(value, str) else None
    if match is None:
        raise ValueError(f"advance must be non-negative seconds or <N>s|m|h|d, not {value!r}")
    return int(dt.timedelta(**{UNITS[match.group(2)]: int(match.group(1))}).total_seconds())


def render_placeholders(value, now, head=None, base=None, pushed=None):
    """Replace ``{{now±N<unit>}}`` with ISO UTC times and ``{{head}}``/``{{base}}``/``{{pushed}}``
    with commit ids, leaving any placeholder whose value is not given untouched."""
    commits = {"head": head, "base": base, "pushed": pushed}
    if isinstance(value, str):
        def replace(match):
            if match.group(4):
                return commits[match.group(4)] or match.group(0)
            moment = now
            if match.group(1):
                delta = dt.timedelta(**{UNITS[match.group(3)]: int(match.group(2))})
                moment = now + delta if match.group(1) == "+" else now - delta
            return _iso(moment)
        return PLACEHOLDER.sub(replace, value)
    if isinstance(value, list):
        return [render_placeholders(item, now, head, base, pushed) for item in value]
    if isinstance(value, dict):
        return {key: render_placeholders(item, now, head, base, pushed) for key, item in value.items()}
    return value


def _digest(seed):
    return hashlib.sha256(seed.encode("utf-8")).digest()


def _node_id(prefix, seed):
    return f"{prefix}_kwDO" + base64.urlsafe_b64encode(_digest(seed)).decode("ascii").rstrip("=")[:16]


def _stable_int(seed):
    return 1_000_000_000 + int.from_bytes(_digest(seed)[:6], "big") % 1_000_000_000


def _derived_oid(seed):
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()


def _public(value):
    """Drop internal ``_``-prefixed keys everywhere (GraphQL's ``__typename`` stays)."""
    if isinstance(value, dict):
        return {k: _public(v) for k, v in value.items()
                if not (isinstance(k, str) and k.startswith("_") and not k.startswith("__"))}
    if isinstance(value, list):
        return [_public(item) for item in value]
    return value


# ----------------------------------------------------------------------------- state

def initialize(state_dir, github, head=None, base=None, remote=None):
    """Write the initial stub state for one run and an empty call log."""
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    state = copy.deepcopy(github)
    for key in ("review_threads", "reviews", "issue_comments", "checks", "on_write"):
        state.setdefault(key, [])
    state.setdefault("login", state.get("repo", "octocat/x").split("/", 1)[0])
    state.setdefault("pull_request", {})
    state["pull_request"].setdefault("number", 1)
    state.setdefault("api", {})
    state["_counter"] = 3_021_000_000
    state["_render"] = {"head": head, "base": base}
    state["_remote"] = str(remote) if remote else None
    state["_turn"] = None
    state["_clock_offset"] = 0
    state["_initial_merge_state"] = state["pull_request"].get("mergeStateStatus")
    state.update(_render(state, {k: v for k, v in state.items() if k not in LATE_KEYS and not k.startswith("_")}))
    _materialize(state, _now(state))
    (state_dir / "state.json").write_text(json.dumps(state, indent=1))
    (state_dir / "gh-stub.log").write_text("")


def install(bin_dir):
    """Create ``bin_dir/gh`` that runs this stub with the current interpreter."""
    bin_dir = Path(bin_dir)
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper = bin_dir / "gh"
    wrapper.write_text(f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(Path(__file__).resolve()))}"
                       ' "$@"\n')
    wrapper.chmod(0o755)
    return wrapper


NESTED_RUN_KIND = "nested-model-run"
MODEL_PROGRAMS = ("claude", "codex")


def install_model_shims(bin_dir, programs=MODEL_PROGRAMS):
    """Create ``bin_dir/claude`` and ``bin_dir/codex`` that refuse a nested model run and record the attempt."""
    bin_dir = Path(bin_dir)
    bin_dir.mkdir(parents=True, exist_ok=True)
    program = ("import sys; sys.path.insert(0, sys.argv[1]); import gh_stub; "
               "sys.exit(gh_stub.refused_run_main(sys.argv[2], sys.argv[3:]))")
    shims = []
    for name in programs:
        shim = bin_dir / name
        shim.write_text("#!/bin/sh\nexec " + " ".join(shlex.quote(part) for part in (
            sys.executable, "-c", program, str(Path(__file__).resolve().parent), name)) + ' "$@"\n')
        shim.chmod(0o755)
        shims.append(shim)
    return shims


def record_refused_run(state_dir, program, argv, cwd):
    """Log a refused nested model run as a write of kind ``nested-model-run``; nothing else changes."""
    with _locked(state_dir) as state:
        write = {"kind": NESTED_RUN_KIND, "program": program, "argv": list(argv)}
        record = {"ts": _now(), "argv": [program, *argv], "source": "shim", "stdin": "", "files": {}, "cwd": cwd,
                  "auth_env_present": [], "writes": [write], "exit_code": 1}
        _annotate(record, state)
        if state.get("_turn") is not None:
            write["turn"] = state["_turn"]
        with open(Path(state_dir) / "gh-stub.log", "a") as log:
            log.write(json.dumps(record) + "\n")


def _annotate(record, state):
    """Stamp a log record with the operator turn in progress and, once it has advanced, the stub clock."""
    if state.get("_turn") is not None:
        record["turn"] = state["_turn"]
    if state.get("_clock_offset"):
        record["clock"] = _now(state)


def refused_run_main(program, argv):
    """Entry point for the model shims: refuse, record the attempt when the stub state is reachable, exit 1."""
    state_dir = os.environ.get("GH_STUB_STATE_DIR")
    if state_dir and (Path(state_dir) / "state.json").is_file():
        record_refused_run(state_dir, program, argv, os.getcwd())
    sys.stderr.write(f"{program}: nested model runs are refused here and the attempt is recorded. "
                     "Check the equipment by reading it, not by running a model.\n")
    return 1


def install_post_receive(git_dir, state_dir):
    """Install the bare remote's ``post-receive`` hook that reports pushes to the stub."""
    hook = Path(git_dir) / "hooks" / "post-receive"
    hook.parent.mkdir(parents=True, exist_ok=True)
    program = ("import sys; sys.path.insert(0, sys.argv[1]); import gh_stub; "
               "sys.exit(gh_stub.post_receive_main(sys.argv[2]))")
    hook.write_text("#!/bin/sh\nexec " + " ".join(shlex.quote(part) for part in (
        sys.executable, "-c", program, str(Path(__file__).resolve().parent), str(Path(state_dir).resolve()))) + "\n")
    hook.chmod(0o755)
    return hook


def apply_patch(state_dir, patch):
    """Apply ``{advance?, append?, set?, update_threads?}``: ``advance`` moves the stub clock forward first, and the
    rest renders its placeholders at the advanced clock and the current head."""
    with _locked(state_dir) as state:
        _apply(state, patch)


def set_turn(state_dir, turn):
    """Record the operator turn in progress; later writes carry it."""
    with _locked(state_dir) as state:
        state["_turn"] = turn


def current_time(state_dir):
    """The stub's clock as an aware UTC datetime: wall time plus every ``advance`` applied so far."""
    with _locked(state_dir) as state:
        return _moment(state)


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


def _render(state, value, pushed=None):
    """Render placeholders at the stub clock, with the head and base commits current now."""
    return render_placeholders(value, _moment(state), _pull_request_raw_head(state), _base_oid(state), pushed)


def _apply(state, patch, pushed=None):
    if patch.get("advance") is not None:
        state["_clock_offset"] = state.get("_clock_offset", 0) + _seconds(patch["advance"])
    patch = _render(state, patch, pushed)
    now = _now(state)
    for key, items in (patch.get("append") or {}).items():
        for item in items:
            item = copy.deepcopy(item)
            if key == "issue_comments":
                item.setdefault("createdAt", now)
            elif key == "reviews" and item.get("state") != "PENDING":
                item.setdefault("submittedAt", now)
            elif key == "review_threads":
                for comment in item.get("comments") or []:
                    comment.setdefault("createdAt", now)
            state.setdefault(key, []).append(item)
    _merge(state, patch.get("set") or {})
    for thread_id, fields in (patch.get("update_threads") or {}).items():
        thread = next((t for t in state.get("review_threads", []) if t.get("id") == thread_id), None)
        if thread is None:
            continue
        fields = copy.deepcopy(fields)
        comments = fields.pop("comments", None)
        _merge(thread, fields)
        if comments is not None:
            existing = thread.get("comments", [])
            restated, taken = [], set()
            for comment in comments:
                login = (comment.get("author") or {}).get("login")
                alike = [i for i, c in enumerate(existing) if i not in taken and not c.get("_by_write")
                         and (c.get("author") or {}).get("login") == login and c.get("body") == comment.get("body")]
                exact = [i for i in alike if existing[i].get("createdAt") == comment.get("createdAt")]
                same = (exact or alike or [None])[0]
                if same is not None:
                    taken.add(same)
                    comment = dict(copy.deepcopy(existing[same]), **comment)
                comment.setdefault("createdAt", now)
                restated.append(comment)
            kept = [c for c in existing if c.get("_by_write")]
            merged = kept + restated
            merged.sort(key=lambda c: str(c.get("createdAt") or ""))
            thread["comments"] = merged
    _materialize(state, now)


def _actor_type(author, hint=None):
    login = (author or {}).get("login") or ""
    if (author or {}).get("__typename"):
        return author["__typename"]
    if hint in ("Bot", "User", "Organization", "Mannequin"):
        return hint
    return "Bot" if login.endswith("[bot]") or login.lower() in KNOWN_BOTS else "User"


def _materialize(state, now):
    """Give every object a stable id and time, and link review comments to reviews."""
    repo, pr = state["repo"], state["pull_request"]
    pr.setdefault("id", _node_id("PR", f"{repo}#{pr['number']}"))
    pr.setdefault("databaseId", _stable_int(f"pr:{repo}#{pr['number']}"))
    seen = set()

    def identify(item, prefix, seed):
        if "id" not in item:
            candidate, n = seed, 0
            while _node_id(prefix, candidate) in seen:
                n += 1
                candidate = f"{seed}#{n}"
            item["id"] = _node_id(prefix, candidate)
        item.setdefault("databaseId", _stable_int(f"{prefix}:{item['id']}"))
        seen.add(item["id"])

    for comment in state["issue_comments"]:
        comment.setdefault("createdAt", now)
        identify(comment, "IC", f"{repo}|comment|{(comment.get('author') or {}).get('login')}|{comment.get('body')}")
    for review in state["reviews"]:
        if review.get("state") != "PENDING":
            review.setdefault("submittedAt", now)
        review.setdefault("_startedAt", review.get("submittedAt") or now)
        identify(review, "PRR", f"{repo}|review|{(review.get('author') or {}).get('login')}|{review.get('state')}|"
                                f"{review.get('body')}")
    for thread in state["review_threads"]:
        for comment in thread.setdefault("comments", []):
            comment.setdefault("createdAt", now)
            identify(comment, "PRRC", f"{thread.get('id')}|{(comment.get('author') or {}).get('login')}|"
                                      f"{comment.get('body')}")
    reviews = {r["id"]: r for r in state["reviews"]}
    for thread in state["review_threads"]:
        for comment in thread["comments"]:
            linked = comment.get("pullRequestReview")
            if isinstance(linked, dict) and linked.get("id") in reviews:
                continue
            login = (comment.get("author") or {}).get("login")
            candidates = [r for r in state["reviews"] if (r.get("author") or {}).get("login") == login
                          and r.get("state") != "PENDING"]
            earlier = [r for r in candidates if str(r.get("submittedAt") or "") <= str(comment.get("createdAt"))]
            review = (earlier or candidates or [None])[-1 if earlier else 0]
            if review is None or comment.get("_by_write"):
                review = {"author": copy.deepcopy(comment.get("author")), "state": "COMMENTED", "body": "",
                          "submittedAt": comment.get("createdAt"),
                          "commit": {"oid": _comment_commits(state, thread, comment)[1]}, "_synthesized": True}
                if comment.get("authorType"):
                    review["authorType"] = comment["authorType"]
                identify(review, "PRR", f"{repo}|review-of|{comment['id']}")
                state["reviews"].append(review)
                reviews[review["id"]] = review
            comment["pullRequestReview"] = {"id": review["id"], "databaseId": review["databaseId"]}
    state["reviews"].sort(key=lambda r: str(r.get("submittedAt") or r.get("createdAt") or "~"))


def _review_event(value):
    """A review write's ``event``: ``APPROVE``, ``REQUEST_CHANGES``, ``COMMENT``, or ``None`` while pending."""
    return value.upper() if isinstance(value, str) and value else None


def _time(value):
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")) if value else None
    except ValueError:
        return None


def _base_oid(state):
    return state["pull_request"].get("baseRefOid") or (state.get("_render") or {}).get("base") or _derived_oid(
        f"{state['repo']}:base")


def _commit_at(state, moment):
    """The latest ``pull_request.commits`` oid committed at or before ``moment``, else the base commit."""
    when, best = _time(moment), None
    for entry in state["pull_request"].get("commits") or []:
        committed = _time(entry.get("committedDate"))
        if when and committed and entry.get("oid") and committed <= when and (best is None or committed >= best[0]):
            best = (committed, entry["oid"])
    return best[1] if best else _base_oid(state)


def _comment_commits(state, thread, comment):
    """``(commit, originalCommit)`` oids of a thread comment, defaulting by its time and the thread's outdatedness."""
    head = _pull_request_raw_head(state)
    explicit = (comment.get("commit") or {}).get("oid")
    original = ((comment.get("originalCommit") or {}).get("oid") or explicit
                or (head if comment.get("_by_write") else _commit_at(state, comment.get("createdAt"))))
    return explicit or (original if thread.get("isOutdated") else head), original


def _review_commit(state, review):
    """A review's commit: its own, else the one current when it was submitted (the head while pending)."""
    if review.get("commit"):
        return review["commit"]
    submitted = review.get("submittedAt") if review.get("state") != "PENDING" else None
    return {"oid": _commit_at(state, submitted) if submitted else _pull_request_raw_head(state)}


def _pull_request_raw_head(state):
    pr = state["pull_request"]
    return pr.get("headRefOid") or (state.get("_render") or {}).get("head") or _derived_oid(f"{state['repo']}:head")


def _bodies(write):
    """A write's body and the bodies of its inline review comments."""
    return [write.get("body") or ""] + [c.get("body") or "" for c in write.get("comments") or []
                                        if isinstance(c, dict)]


def write_matches(write, match):
    """Whether a normalized write satisfies a case ``match`` pattern."""
    for key, expected in (match or {}).items():
        if key == "body_contains":
            if not any(expected in body for body in _bodies(write)):
                return False
        elif key == "body_regex":
            if not any(re.search(expected, body) for body in _bodies(write)):
                return False
        elif key == "path_contains":
            if expected not in (write.get("path") or ""):
                return False
        elif key == "reviewer":
            if expected not in (write.get("reviewers") or []):
                return False
        elif write.get(key) != expected:
            return False
    return True


# ----------------------------------------------------------------------------- parsing

class StubError(Exception):
    pass


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


def _global_flags(argv):
    """Strip ``-R/--repo`` and ``--hostname`` wherever they appear."""
    rest, repo, host, index = [], None, None, 0
    while index < len(argv):
        arg = argv[index]
        if arg in ("-R", "--repo", "--hostname") and index + 1 < len(argv):
            if arg == "--hostname":
                host = argv[index + 1]
            else:
                repo = argv[index + 1]
            index += 2
            continue
        if arg.startswith("--repo=") or arg.startswith("-R") and len(arg) > 2 and not arg.startswith("--"):
            repo = arg.split("=", 1)[1] if arg.startswith("--repo=") else arg[2:]
        elif arg.startswith("--hostname="):
            host = arg.split("=", 1)[1]
        else:
            rest.append(arg)
            if arg in VALUE_FLAGS and arg not in ("-R", "--repo", "--hostname") and index + 1 < len(argv):
                rest.append(argv[index + 1])
                index += 1
        index += 1
    return rest, repo, host


def _check_repo(state, repo):
    if repo is None:
        return
    name = re.sub(r"^(?:https?://)?(?:[^/]+\.[^/]+/)?", "", repo.strip()).removesuffix(".git").strip("/")
    if name.lower() != state["repo"].lower():
        raise StubError(f"GraphQL: Could not resolve to a Repository with the name '{name}'. (repository)")


def _typed(raw):
    if raw in ("true", "false"):
        return raw == "true"
    if raw == "null":
        return None
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    return raw


def _field_values(flags, stdin):
    """``-f`` (raw) and ``-F`` (typed, ``@file``) fields, with ``key[]`` arrays."""
    fields = {}
    for name in ("-f", "--raw-field", "-F", "--field"):
        for value in flags.get(name, []):
            if not isinstance(value, str) or "=" not in value:
                continue
            key, raw = value.split("=", 1)
            if name in ("-F", "--field"):
                raw = (_read_file(raw[1:], stdin) or "") if raw.startswith("@") else _typed(raw)
            if key.endswith("[]"):
                fields.setdefault(key[:-2], []).append(raw)
            else:
                fields[key] = raw
    return fields


# ----------------------------------------------------------------------------- GraphQL

class GraphQLSyntaxError(Exception):
    pass


class _NotFound(Exception):
    pass


_TOKEN = re.compile(r'''
  (?P<skip>[\s,﻿]+|\#[^\n]*)
| (?P<block>"""(?:\\"""|[\s\S])*?""")
| (?P<string>"(?:[^"\\\n]|\\.)*")
| (?P<spread>\.\.\.)
| (?P<number>-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)
| (?P<name>[_A-Za-z][_0-9A-Za-z]*)
| (?P<punct>[!$&():=@\[\]{}|])
''', re.X)


class _Var:
    def __init__(self, name):
        self.name = name


def _tokens(text):
    tokens, position = [], 0
    while position < len(text):
        match = _TOKEN.match(text, position)
        if not match:
            raise GraphQLSyntaxError(f"Syntax Error: Unexpected character {text[position]!r} at {position}")
        position = match.end()
        kind = match.lastgroup
        if kind != "skip":
            tokens.append((kind, match.group(kind)))
    tokens.append(("end", None))
    return tokens


class _Parser:
    def __init__(self, text):
        self.tokens, self.at = _tokens(text), 0

    def peek(self, value=None):
        kind, text = self.tokens[self.at]
        return text == value if value is not None else (kind, text)

    def take(self, value=None, kind=None):
        token_kind, text = self.tokens[self.at]
        if (value is not None and text != value) or (kind is not None and token_kind != kind):
            raise GraphQLSyntaxError(f"Syntax Error: Expected {value or kind}, found {text or 'end of document'}")
        self.at += 1
        return text

    def document(self):
        operations, fragments = [], {}
        while self.peek()[0] != "end":
            if self.peek("{"):
                operations.append({"type": "query", "name": None, "variables": {}, "selections": self.selections()})
            elif self.peek("fragment"):
                self.take()
                name = self.take(kind="name")
                self.take("on")
                fragments[name] = {"type": self.take(kind="name"), "directives": self.directives(),
                                   "selections": self.selections()}
            elif self.peek()[1] in ("query", "mutation", "subscription"):
                kind = self.take()
                name = self.take(kind="name") if self.peek()[0] == "name" else None
                variables = self.variable_definitions() if self.peek("(") else {}
                self.directives()
                operations.append({"type": kind, "name": name, "variables": variables,
                                   "selections": self.selections()})
            else:
                raise GraphQLSyntaxError(f"Syntax Error: Unexpected {self.peek()[1]}")
        if not operations:
            raise GraphQLSyntaxError("Syntax Error: the document has no operation")
        return {"operations": operations, "fragments": fragments}

    def variable_definitions(self):
        result = {}
        self.take("(")
        while not self.peek(")"):
            self.take("$")
            name = self.take(kind="name")
            self.take(":")
            self.type_reference()
            result[name] = self.value(constant=True) if self.peek("=") and self.take("=") else None
            self.directives()
        self.take(")")
        return result

    def type_reference(self):
        if self.peek("["):
            self.take("[")
            self.type_reference()
            self.take("]")
        else:
            self.take(kind="name")
        if self.peek("!"):
            self.take("!")

    def selections(self):
        items = []
        self.take("{")
        while not self.peek("}"):
            if self.peek()[0] == "spread":
                self.take()
                if self.peek()[0] == "name" and not self.peek("on"):
                    items.append({"kind": "spread", "name": self.take(), "directives": self.directives()})
                else:
                    condition = None
                    if self.peek("on"):
                        self.take()
                        condition = self.take(kind="name")
                    items.append({"kind": "inline", "type": condition, "directives": self.directives(),
                                  "selections": self.selections()})
                continue
            name = self.take(kind="name")
            alias = None
            if self.peek(":"):
                self.take()
                alias, name = name, self.take(kind="name")
            arguments = self.arguments() if self.peek("(") else {}
            directives = self.directives()
            items.append({"kind": "field", "alias": alias, "name": name, "args": arguments,
                          "directives": directives, "selections": self.selections() if self.peek("{") else None})
        self.take("}")
        return items

    def arguments(self):
        result = {}
        self.take("(")
        while not self.peek(")"):
            name = self.take(kind="name")
            self.take(":")
            result[name] = self.value()
        self.take(")")
        return result

    def directives(self):
        result = []
        while self.peek("@"):
            self.take()
            result.append((self.take(kind="name"), self.arguments() if self.peek("(") else {}))
        return result

    def value(self, constant=False):
        kind, text = self.peek()
        if text == "$" and not constant:
            self.take()
            return _Var(self.take(kind="name"))
        if kind == "number":
            self.take()
            return float(text) if any(c in text for c in ".eE") else int(text)
        if kind == "string":
            self.take()
            try:
                return json.loads(text)
            except ValueError:
                return text[1:-1]
        if kind == "block":
            self.take()
            lines = text[3:-3].replace('\\"""', '"""').split("\n")
            indent = min((len(l) - len(l.lstrip()) for l in lines[1:] if l.strip()), default=0)
            lines = [lines[0]] + [l[indent:] for l in lines[1:]]
            return "\n".join(lines).strip("\n")
        if text == "[":
            self.take()
            items = []
            while not self.peek("]"):
                items.append(self.value(constant))
            self.take("]")
            return items
        if text == "{":
            self.take()
            items = {}
            while not self.peek("}"):
                name = self.take(kind="name")
                self.take(":")
                items[name] = self.value(constant)
            self.take("}")
            return items
        if kind == "name":
            self.take()
            return {"true": True, "false": False, "null": None}.get(text, text)
        raise GraphQLSyntaxError(f"Syntax Error: Unexpected {text or 'end of document'}")


def _resolve_value(value, variables):
    if isinstance(value, _Var):
        return variables.get(value.name)
    if isinstance(value, list):
        return [_resolve_value(item, variables) for item in value]
    if isinstance(value, dict):
        return {key: _resolve_value(item, variables) for key, item in value.items()}
    return value


INTERFACES = {
    "Actor": {"User", "Bot", "Organization", "Mannequin", "EnterpriseUserAccount"},
    "RepositoryOwner": {"User", "Organization"},
    "Assignee": {"User", "Bot", "Mannequin", "Organization"},
    "RequestedReviewer": {"User", "Team", "Bot", "Mannequin"},
    "StatusCheckRollupContext": {"CheckRun", "StatusContext"},
    "Comment": {"IssueComment", "PullRequestReviewComment", "PullRequestReview", "PullRequest", "Issue",
                "CommitComment"},
    "Minimizable": {"IssueComment", "PullRequestReviewComment", "CommitComment", "GistComment"},
    "Reactable": {"IssueComment", "PullRequestReviewComment", "PullRequestReview", "PullRequest", "Issue"},
    "UniformResourceLocatable": {"PullRequest", "Repository", "User", "Bot", "IssueComment", "Commit",
                                 "PullRequestReviewComment", "PullRequestReview", "CheckRun"},
    "GitObject": {"Commit"},
    "Closable": {"PullRequest", "Issue"},
    "Labelable": {"PullRequest", "Issue"},
}


class _Context:
    def __init__(self, variables, fragments):
        self.variables, self.fragments, self.errors = variables, fragments, []


def _type_matches(value, condition):
    typename = value.get("__typename") if isinstance(value, dict) else None
    if condition is None or typename is None or typename == condition:
        return True
    if condition == "Node":
        return "id" in value
    if condition.endswith("TimelineItems") or condition.endswith("TimelineItem"):
        return True
    return typename in INTERFACES.get(condition, ())


def _directives_pass(directives, context):
    for name, arguments in directives:
        condition = _resolve_value(arguments.get("if"), context.variables)
        if name == "include" and not condition:
            return False
        if name == "skip" and condition:
            return False
    return True


def _collect(value, selections, context, out=None):
    out = {} if out is None else out
    for selection in selections:
        if not _directives_pass(selection["directives"], context):
            continue
        if selection["kind"] == "field":
            out.setdefault(selection["alias"] or selection["name"], []).append(selection)
        elif selection["kind"] == "inline":
            if _type_matches(value, selection["type"]):
                _collect(value, selection["selections"], context, out)
        else:
            fragment = context.fragments.get(selection["name"])
            if fragment is None:
                raise GraphQLSyntaxError(f"Fragment {selection['name']} was used, but not defined")
            if _type_matches(value, fragment["type"]):
                _collect(value, fragment["selections"], context, out)
    return out


def _field_names(selections, context):
    names = set()
    for selection in selections or []:
        if selection["kind"] == "field":
            names.add(selection["name"])
        elif selection["kind"] == "inline":
            names |= _field_names(selection["selections"], context)
        else:
            names |= _field_names((context.fragments.get(selection["name"]) or {}).get("selections"), context)
    return names


def _cursor(index):
    return base64.b64encode(f"cursor:v2:{index}".encode()).decode()


def _uncursor(cursor):
    try:
        return int(base64.b64decode(cursor).decode().rsplit(":", 1)[1])
    except (ValueError, IndexError, TypeError):
        return -1


def _connection(items, arguments):
    start, end = 0, len(items)
    if arguments.get("after"):
        start = _uncursor(arguments["after"]) + 1
    if arguments.get("before"):
        end = min(end, _uncursor(arguments["before"]))
    window = list(range(max(start, 0), max(end, 0)))
    if isinstance(arguments.get("first"), int):
        window = window[:arguments["first"]]
    if isinstance(arguments.get("last"), int):
        window = window[len(window) - arguments["last"]:] if arguments["last"] else []
    return {"__typename": "Connection", "totalCount": len(items), "nodes": [items[i] for i in window],
            "edges": [{"cursor": _cursor(i), "node": items[i]} for i in window],
            "pageInfo": {"hasNextPage": bool(window) and window[-1] < len(items) - 1,
                         "hasPreviousPage": bool(window) and window[0] > 0,
                         "startCursor": _cursor(window[0]) if window else None,
                         "endCursor": _cursor(window[-1]) if window else None}}


def _select(value, selections, context, path):
    result = {}
    for key, fields in _collect(value, selections, context).items():
        field = fields[0]
        name = field["name"]
        if name == "__typename":
            result[key] = value.get("__typename") if isinstance(value, dict) else None
            continue
        arguments = _resolve_value(field["args"], context.variables)
        sub = [s for f in fields for s in (f["selections"] or [])] if field["selections"] is not None else None
        resolved = value.get(name) if isinstance(value, dict) else None
        if callable(resolved):
            try:
                resolved = resolved(arguments)
            except _NotFound as missing:
                context.errors.append({"message": str(missing), "path": path + [key]})
                resolved = None
        result[key] = _complete(resolved, arguments, sub, context, path + [key])
    return result


def _complete(value, arguments, selections, context, path):
    if selections is None or value is None:
        return _public(value)
    if isinstance(value, list):
        if _field_names(selections, context) & {"nodes", "edges", "pageInfo", "totalCount"}:
            value = _connection(value, arguments)
        else:
            return [_complete(item, {}, selections, context, path + [i]) for i, item in enumerate(value)]
    if isinstance(value, dict):
        return _select(value, selections, context, path)
    return value


# ----------------------------------------------------------------------------- views

def _pr_url(state):
    pr = state["pull_request"]
    return pr.get("url") or f"https://github.com/{state['repo']}/pull/{pr['number']}"


def _owner_name(state):
    return state["repo"].split("/", 1)


def _review_requests(state):
    pr = state["pull_request"]
    if isinstance(pr.get("reviewRequests"), list):
        return pr["reviewRequests"]
    requested = state.get("requested_reviewers") or {}
    return ([{"__typename": "User", "login": u.get("login")} for u in requested.get("users") or []]
            + [{"__typename": "Team", "slug": t.get("slug"), "name": t.get("name") or t.get("slug")}
               for t in requested.get("teams") or []])


def _association(state, item, login, typename):
    if item.get("authorAssociation"):
        return item["authorAssociation"]
    known = (state.get("associations") or {}).get(login)
    if known:
        return known
    if typename == "Bot":
        return "NONE"
    return "OWNER" if login and login.lower() == _owner_name(state)[0].lower() else "COLLABORATOR"


def _rollup_state(checks):
    states = [str(c.get("conclusion") or c.get("state") or "").upper() for c in checks]
    if not checks:
        return None
    if any(s in ("FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE") for s in states):
        return "FAILURE"
    if any(s in ("", "PENDING", "QUEUED", "IN_PROGRESS", "EXPECTED", "WAITING") for s in states):
        return "PENDING"
    return "SUCCESS"


def _pull_request(state):
    """The pull request as ``gh pr view --json`` reports it, with derived defaults."""
    raw = state["pull_request"]
    owner, name = _owner_name(state)
    render = state.get("_render") or {}
    head_owner = (raw.get("headRepositoryOwner") or {}).get("login") or owner
    pr = {"id": raw.get("id"), "number": raw["number"], "state": "OPEN", "isDraft": False, "url": _pr_url(state),
          "title": "", "body": "", "author": {"login": state["login"]},
          "headRefName": DEFAULT_HEAD_BRANCH, "baseRefName": "main", "mergeable": "MERGEABLE",
          "mergeStateStatus": "CLEAN", "reviewDecision": None, "closed": False, "labels": [], "assignees": [],
          "headRefOid": _pull_request_raw_head(state),
          "baseRefOid": render.get("base") or _derived_oid(f"{state['repo']}:base"),
          "headRepositoryOwner": {"id": _node_id("U", head_owner), "login": head_owner},
          "headRepository": {"id": _node_id("R", f"{head_owner}/{name}"), "name": name,
                             "nameWithOwner": f"{head_owner}/{name}"},
          "baseRepository": {"id": _node_id("R", state["repo"]), "name": name, "nameWithOwner": state["repo"],
                             "owner": {"login": owner}},
          "isCrossRepository": head_owner.lower() != owner.lower(), "reviewRequests": _review_requests(state)}
    pr.update(_public(raw))
    pr.setdefault("comments", [_gh_issue_comment(state, c) for c in state["issue_comments"]])
    pr.setdefault("reviews", [_gh_review(state, r) for r in state["reviews"]])
    pr.setdefault("latestReviews", _latest(pr["reviews"]))
    pr.setdefault("statusCheckRollup", state["checks"])
    pr.setdefault("commits", [])
    return pr


def _latest(reviews):
    latest = {}
    for review in reviews:
        if review.get("state") != "PENDING":
            latest[(review.get("author") or {}).get("login")] = review
    return list(latest.values())


def _gh_issue_comment(state, comment):
    login = (comment.get("author") or {}).get("login")
    typename = _actor_type(comment.get("author"), comment.get("authorType"))
    view = {"id": comment["id"], "author": {"login": login}, "authorAssociation": _association(
        state, comment, login, typename), "body": comment.get("body", ""), "createdAt": comment.get("createdAt"),
            "includesCreatedEdit": False, "isMinimized": False, "minimizedReason": "", "reactionGroups": [],
            "url": comment.get("url") or f"{_pr_url(state)}#issuecomment-{comment['databaseId']}",
            "viewerDidAuthor": login == state["login"]}
    view.update({k: v for k, v in _public(comment).items() if k not in ("authorType", "databaseId")})
    return view


def _gh_review(state, review):
    login = (review.get("author") or {}).get("login")
    typename = _actor_type(review.get("author"), review.get("authorType"))
    view = {"id": review["id"], "author": {"login": login},
            "authorAssociation": _association(state, review, login, typename), "body": review.get("body", ""),
            "submittedAt": review.get("submittedAt"), "includesCreatedEdit": False, "reactionGroups": [],
            "state": review.get("state"), "commit": _review_commit(state, review)}
    view.update({k: v for k, v in _public(review).items() if k not in ("authorType", "databaseId")})
    return view


class _Views:
    """GraphQL objects over the stub state; lazy fields are callables of their arguments."""

    def __init__(self, state):
        self.state = state
        self.pr = _pull_request(state)

    def actor(self, author, hint=None):
        if not isinstance(author, dict) or not author.get("login"):
            return None
        login = author["login"]
        typename = _actor_type(author, hint)
        prefix = {"Bot": "BOT", "Organization": "O", "Team": "T"}.get(typename, "U")
        view = {"__typename": typename, "login": login.removesuffix("[bot]") if typename == "Bot" else login,
                "id": author.get("id") or _node_id(prefix, login.lower()), "url": f"https://github.com/{login}",
                "avatarUrl": f"https://avatars.githubusercontent.com/{login}", "name": author.get("name")}
        if typename == "User":
            view["databaseId"] = _stable_int(f"user:{login.lower()}")
        self.state.setdefault("_actors", {})[view["id"]] = view["login"]
        return view

    def known_actor_by_id(self, identifier):
        if identifier in (self.state.get("_actors") or {}):
            return self.state["_actors"][identifier]
        logins = {self.state["login"], _owner_name(self.state)[0]}
        for item in (self.state["issue_comments"] + self.state["reviews"]
                     + [c for t in self.state["review_threads"] for c in t.get("comments", [])]):
            logins.add((item.get("author") or {}).get("login"))
        for request in _review_requests(self.state):
            logins.add(request.get("login"))
        for login in filter(None, logins):
            for typename, prefix in (("User", "U"), ("Bot", "BOT")):
                if _node_id(prefix, login.lower()) == identifier:
                    return login
        return None

    def repository(self, which="base"):
        owner, name = _owner_name(self.state)
        if which == "head":
            owner = (self.pr.get("headRepositoryOwner") or {}).get("login") or owner
        full = f"{owner}/{name}"
        own = full.lower() == self.state["repo"].lower()
        settings = _repo_settings(self.state) if own else dict(REPO_DEFAULTS)
        return {"__typename": "Repository", "id": _node_id("R", full), "databaseId": _stable_int(f"repo:{full}"),
                "name": name, "nameWithOwner": full, "url": f"https://github.com/{full}",
                "owner": {"__typename": "User", "login": owner, "id": _node_id("U", owner.lower())},
                "isPrivate": bool(settings["private"]), "isFork": which == "head" and not own,
                "isArchived": False, "visibility": str(settings["visibility"] or "public").upper(),
                "description": settings["description"],
                "squashMergeAllowed": bool(settings["allow_squash_merge"]),
                "mergeCommitAllowed": bool(settings["allow_merge_commit"]),
                "rebaseMergeAllowed": bool(settings["allow_rebase_merge"]),
                "deleteBranchOnMerge": bool(settings["delete_branch_on_merge"]),
                "defaultBranchRef": {"__typename": "Ref", "name": self.pr.get("baseRefName") or "main"},
                "viewerPermission": "ADMIN" if self.state["login"].lower() == owner.lower() else "WRITE",
                "pullRequest": self.pull_request_by_number, "issueOrPullRequest": self.pull_request_by_number,
                "pullRequests": lambda a: [self.pull_request()]
                if not a.get("states") or self.pr.get("state") in a["states"] else []}

    def pull_request_by_number(self, arguments):
        if arguments.get("number") != self.pr["number"]:
            raise _NotFound(f"Could not resolve to a PullRequest with the number of {arguments.get('number')}.")
        return self.pull_request()

    def pull_request(self):
        pr, state = self.pr, self.state
        head = pr["headRefOid"]
        view = {k: v for k, v in pr.items()}
        checks = [self.check(c) for c in state["checks"]]
        rollup = {"__typename": "StatusCheckRollup", "state": pr.get("checksState") or _rollup_state(state["checks"]),
                  "contexts": lambda a: checks, "commit": {"__typename": "Commit", "oid": head}}
        view.update({
            "__typename": "PullRequest", "databaseId": state["pull_request"].get("databaseId"),
            "author": self.actor(pr.get("author")), "mergedBy": self.actor(pr.get("mergedBy")),
            "repository": lambda a: self.repository("base"), "baseRepository": lambda a: self.repository("base"),
            "headRepository": lambda a: self.repository("head"),
            "headRepositoryOwner": self.actor(pr.get("headRepositoryOwner")),
            "headRef": {"__typename": "Ref", "name": pr.get("headRefName"),
                        "target": {"__typename": "Commit", "oid": head}},
            "baseRef": {"__typename": "Ref", "name": pr.get("baseRefName"),
                        "target": {"__typename": "Commit", "oid": pr.get("baseRefOid")}},
            "reviewThreads": lambda a: [self.thread(t) for t in state["review_threads"]],
            "comments": lambda a: [self.issue_comment(c) for c in state["issue_comments"]],
            "reviews": lambda a: [self.review(r) for r in state["reviews"]
                                  if (not a.get("states") or r.get("state") in a["states"])
                                  and (not a.get("author") or (r.get("author") or {}).get("login") == a["author"])],
            "latestReviews": lambda a: [self.review(r) for r in _latest(state["reviews"])],
            "latestOpinionatedReviews": lambda a: [self.review(r) for r in _latest(
                [r for r in state["reviews"] if r.get("state") in ("APPROVED", "CHANGES_REQUESTED")])],
            "reviewRequests": lambda a: [self.review_request(r) for r in _review_requests(state)],
            "statusCheckRollup": rollup if state["checks"] or pr.get("checksState") else None,
            "commits": lambda a: [self.pull_request_commit(c) for c in pr.get("commits") or []],
            "labels": lambda a: [self.label(l) for l in pr.get("labels") or []],
            "assignees": lambda a: [self.actor(x) for x in pr.get("assignees") or []],
            "files": lambda a: [dict({"__typename": "PullRequestChangedFile", "additions": 0, "deletions": 0,
                                      "changeType": "MODIFIED"}, **f) for f in pr.get("files") or []],
            "timelineItems": lambda a: pr.get("timelineItems") or state.get("timeline") or [],
            "viewerCanUpdate": True, "viewerDidAuthor": (pr.get("author") or {}).get("login") == state["login"],
        })
        return view

    def label(self, label):
        label = {"name": label} if isinstance(label, str) else dict(label)
        return dict({"__typename": "Label", "id": _node_id("LA", label.get("name", "")), "color": "ededed",
                     "description": None}, **label)

    def review_request(self, request):
        typename = request.get("__typename") or ("Team" if request.get("slug") else "User")
        if typename == "Team":
            reviewer = {"__typename": "Team", "slug": request.get("slug") or request.get("name"),
                        "name": request.get("name") or request.get("slug"),
                        "id": _node_id("T", str(request.get("slug") or request.get("name")))}
        else:
            reviewer = self.actor({"login": request.get("login")}, typename)
        return {"__typename": "ReviewRequest", "id": _node_id("RR", json.dumps(request, sort_keys=True)),
                "asCodeOwner": False, "requestedReviewer": reviewer}

    def pull_request_commit(self, commit):
        return {"__typename": "PullRequestCommit", "id": _node_id("PURC", commit.get("oid", "")),
                "url": f"{_pr_url(self.state)}/commits/{commit.get('oid')}", "commit": self.commit(commit)}

    def commit(self, commit):
        headline, body = commit.get("messageHeadline", ""), commit.get("messageBody", "")
        authors = [{"__typename": "GitActor", "name": a.get("name"), "email": a.get("email"),
                    "user": self.actor({"login": a["login"]}) if a.get("login") else None}
                   for a in commit.get("authors") or []]
        view = {"__typename": "Commit", "abbreviatedOid": commit.get("oid", "")[:7],
                "message": headline + ("\n\n" + body if body else ""),
                "url": f"https://github.com/{self.state['repo']}/commit/{commit.get('oid')}",
                "author": authors[0] if authors else None, "committer": authors[0] if authors else None,
                "authors": lambda a: authors}
        view.update({k: v for k, v in commit.items() if k != "authors"})
        return view

    def check(self, check):
        typename = check.get("__typename") or ("StatusContext" if "context" in check else "CheckRun")
        state = str(check.get("state") or "").upper()
        if typename == "StatusContext":
            view = {"__typename": "StatusContext", "context": check.get("context") or check.get("name"),
                    "state": state or "PENDING", "targetUrl": check.get("targetUrl") or check.get("link"),
                    "description": check.get("description"), "createdAt": check.get("startedAt"),
                    "isRequired": lambda a: _required(self.state, check)}
        else:
            conclusion = check.get("conclusion")
            if conclusion is None and state in ("SUCCESS", "FAILURE", "NEUTRAL", "SKIPPED", "CANCELLED", "TIMED_OUT"):
                conclusion = state
            view = {"__typename": "CheckRun", "name": check.get("name"),
                    "status": check.get("status") or ("COMPLETED" if conclusion else "IN_PROGRESS"),
                    "conclusion": conclusion, "detailsUrl": check.get("detailsUrl") or check.get("link"),
                    "startedAt": check.get("startedAt"), "completedAt": check.get("completedAt"),
                    "id": _node_id("CR", str(check.get("name"))), "databaseId": _stable_int(f"check:{check.get('name')}"),
                    "isRequired": lambda a: _required(self.state, check),
                    "checkSuite": {"__typename": "CheckSuite", "workflowRun": {
                        "__typename": "WorkflowRun", "workflow": {"name": check.get("workflowName") or check.get("workflow")}}}}
        return view

    def issue_comment(self, comment):
        login = (comment.get("author") or {}).get("login")
        typename = _actor_type(comment.get("author"), comment.get("authorType"))
        view = {"__typename": "IssueComment", "updatedAt": comment.get("createdAt"),
                "publishedAt": comment.get("createdAt"), "lastEditedAt": None, "isMinimized": False,
                "minimizedReason": None, "reactionGroups": [], "includesCreatedEdit": False,
                "url": f"{_pr_url(self.state)}#issuecomment-{comment['databaseId']}",
                "viewerDidAuthor": login == self.state["login"], "viewerCanUpdate": login == self.state["login"]}
        view.update(_public(comment))
        view.update(author=self.actor(comment.get("author"), comment.get("authorType")),
                    authorAssociation=_association(self.state, comment, login, typename),
                    bodyText=comment.get("body", ""), pullRequest=lambda a: self.pull_request(),
                    issue=lambda a: self.pull_request())
        return view

    def review(self, review):
        login = (review.get("author") or {}).get("login")
        typename = _actor_type(review.get("author"), review.get("authorType"))
        submitted = review.get("submittedAt") if review.get("state") != "PENDING" else None
        started = review.get("_startedAt") or submitted or _now(self.state)
        view = {"__typename": "PullRequestReview", "createdAt": started, "updatedAt": submitted or started,
                "publishedAt": submitted, "lastEditedAt": None, "isMinimized": False, "includesCreatedEdit": False,
                "reactionGroups": [], "body": "",
                "url": f"{_pr_url(self.state)}#pullrequestreview-{review['databaseId']}",
                "viewerDidAuthor": login == self.state["login"]}
        view.update(_public(review))
        commit = _review_commit(self.state, review)
        review_id = review["id"]
        view.update(author=self.actor(review.get("author"), review.get("authorType")),
                    authorAssociation=_association(self.state, review, login, typename),
                    submittedAt=submitted, bodyText=review.get("body", ""),
                    commit=dict({"__typename": "Commit"}, **commit), pullRequest=lambda a: self.pull_request(),
                    comments=lambda a: [self.thread_comment(t, c) for t in self.state["review_threads"]
                                        for c in t.get("comments", [])
                                        if (c.get("pullRequestReview") or {}).get("id") == review_id])
        return view

    def thread(self, thread):
        resolved = bool(thread.get("isResolved"))
        view = {"__typename": "PullRequestReviewThread", "isOutdated": False, "isCollapsed": False, "path": None,
                "line": None, "startLine": None, "originalStartLine": None, "diffSide": "RIGHT",
                "startDiffSide": None, "subjectType": "LINE", "viewerCanResolve": not resolved,
                "viewerCanUnresolve": resolved, "viewerCanReply": True}
        view.update({k: v for k, v in _public(thread).items() if k not in ("comments", "databaseId")})
        view.setdefault("originalLine", thread.get("line"))
        view.update(isResolved=resolved, resolvedBy=self.actor(thread.get("resolvedBy")),
                    comments=lambda a: [self.thread_comment(thread, c) for c in thread.get("comments", [])],
                    pullRequest=lambda a: self.pull_request(), repository=lambda a: self.repository("base"))
        return view

    def thread_comment(self, thread, comment):
        login = (comment.get("author") or {}).get("login")
        typename = _actor_type(comment.get("author"), comment.get("authorType"))
        comments = thread.get("comments", [])
        root = comments[0] if comments else comment
        commit, original = _comment_commits(self.state, thread, comment)
        line = thread.get("line")
        view = {"__typename": "PullRequestReviewComment", "updatedAt": comment.get("createdAt"),
                "publishedAt": comment.get("createdAt"), "lastEditedAt": None, "isMinimized": False,
                "minimizedReason": None, "reactionGroups": [], "includesCreatedEdit": False,
                "url": f"{_pr_url(self.state)}#discussion_r{comment['databaseId']}",
                "path": thread.get("path"), "line": line,
                "originalLine": thread.get("originalLine", line), "startLine": thread.get("startLine"),
                "originalStartLine": thread.get("originalStartLine"),
                "originalPosition": thread.get("originalLine") or line or 1, "position": line,
                "outdated": bool(thread.get("isOutdated")), "subjectType": thread.get("subjectType") or "LINE",
                "state": "SUBMITTED", "diffHunk": comment.get("diffHunk") or f"@@ -{line or 1},1 +{line or 1},1 @@",
                "viewerDidAuthor": login == self.state["login"]}
        view.update({k: v for k, v in _public(comment).items() if k not in ("authorType",)})
        view.update(
            author=self.actor(comment.get("author"), comment.get("authorType")),
            authorAssociation=_association(self.state, comment, login, typename), bodyText=comment.get("body", ""),
            replyTo=None if comment is root else {"__typename": "PullRequestReviewComment", "id": root["id"],
                                                   "databaseId": root["databaseId"]},
            commit={"__typename": "Commit", "oid": commit},
            originalCommit={"__typename": "Commit", "oid": original},
            pullRequestReview=self._comment_review(comment),
            pullRequest=lambda a: self.pull_request(), thread=lambda a: self.thread(thread))
        return view

    def _comment_review(self, comment):
        linked = comment["pullRequestReview"]
        review = next((r for r in self.state["reviews"] if r.get("id") == linked.get("id")), None)
        if review is None:
            return dict({"__typename": "PullRequestReview"}, **linked)
        return lambda a: self.review(review)

    def node(self, identifier):
        state = self.state
        if identifier == self.pr.get("id"):
            return self.pull_request()
        for which in ("base", "head"):
            if self.repository(which)["id"] == identifier:
                return self.repository(which)
        for thread in state["review_threads"]:
            if thread.get("id") == identifier:
                return self.thread(thread)
            for comment in thread.get("comments", []):
                if comment.get("id") == identifier:
                    return self.thread_comment(thread, comment)
        for comment in state["issue_comments"]:
            if comment.get("id") == identifier:
                return self.issue_comment(comment)
        for review in state["reviews"]:
            if review.get("id") == identifier:
                return self.review(review)
        login = self.known_actor_by_id(identifier)
        if login:
            return self.actor({"login": login})
        raise _NotFound(f"Could not resolve to a node with the global id of '{identifier}'.")

    def root(self):
        def repository(arguments):
            wanted = f"{arguments.get('owner')}/{arguments.get('name')}".lower()
            for which in ("base", "head"):
                view = self.repository(which)
                if view["nameWithOwner"].lower() == wanted:
                    return view
            raise _NotFound(f"Could not resolve to a Repository with the name "
                            f"'{arguments.get('owner')}/{arguments.get('name')}'.")

        def nodes(arguments):
            found = []
            for identifier in arguments.get("ids") or []:
                try:
                    found.append(self.node(identifier))
                except _NotFound:
                    found.append(None)
            return found

        return {"__typename": "Query", "repository": repository,
                "viewer": self.actor({"login": self.state["login"]}, "User"),
                "node": lambda a: self.node(a.get("id")), "nodes": nodes,
                "user": lambda a: self.actor({"login": a.get("login")}, "User"),
                "organization": lambda a: self.actor({"login": a.get("login")}, "Organization"),
                "rateLimit": {"__typename": "RateLimit", "limit": 5000, "remaining": 4990, "used": 10, "cost": 1,
                              "resetAt": _now(self.state)},
                "search": lambda a: []}


# ----------------------------------------------------------------------------- REST shapes

def _rest_user(views, author, hint=None):
    actor = views.actor(author, hint)
    if actor is None:
        return None
    login = actor["login"] + ("[bot]" if actor["__typename"] == "Bot" else "")
    return {"login": login, "id": _stable_int(f"user:{login.lower()}"), "node_id": actor["id"],
            "type": actor["__typename"], "html_url": f"https://github.com/{login}", "site_admin": False}


def _repo_settings(state):
    """The base repository's REST settings: GitHub's defaults under the case's ``GET repos/<repo>`` extra."""
    settings = dict(REPO_DEFAULTS)
    override = (state.get("api") or {}).get(f"GET repos/{state['repo']}")
    if isinstance(override, dict):
        settings.update(override)
    return settings


def _rest_repo(views, which="base"):
    repo = views.repository(which)
    view = {"id": repo["databaseId"], "node_id": repo["id"], "name": repo["name"], "full_name": repo["nameWithOwner"],
            "owner": {"login": repo["owner"]["login"], "type": "User"}, "private": repo["isPrivate"],
            "fork": repo["isFork"], "html_url": repo["url"], "default_branch": repo["defaultBranchRef"]["name"],
            "description": repo["description"], "visibility": repo["visibility"].lower(),
            "allow_squash_merge": repo["squashMergeAllowed"], "allow_merge_commit": repo["mergeCommitAllowed"],
            "allow_rebase_merge": repo["rebaseMergeAllowed"], "delete_branch_on_merge": repo["deleteBranchOnMerge"]}
    if repo["nameWithOwner"].lower() == views.state["repo"].lower():
        override = (views.state.get("api") or {}).get(f"GET repos/{views.state['repo']}")
        if isinstance(override, dict):
            _merge(view, override)
    return view


def _required(state, check):
    """Whether a check is required: its own ``isRequired``, else membership in the branch protection's contexts."""
    if check.get("isRequired") is not None:
        return bool(check["isRequired"])
    required = ((state.get("branch_protection") or {}).get("required_status_checks")) or {}
    names = set(required.get("contexts") or []) | {c.get("context") for c in required.get("checks") or []
                                                   if isinstance(c, dict)}
    return bool({check.get("name"), check.get("context")} & names)


def _rest_issue_comment(views, comment):
    state = views.state
    view = views.issue_comment(comment)
    return {"id": comment["databaseId"], "node_id": comment["id"],
            "url": f"https://api.github.com/repos/{state['repo']}/issues/comments/{comment['databaseId']}",
            "html_url": view["url"], "body": comment.get("body", ""),
            "user": _rest_user(views, comment.get("author"), comment.get("authorType")),
            "created_at": comment.get("createdAt"), "updated_at": view["updatedAt"],
            "author_association": view["authorAssociation"],
            "issue_url": f"https://api.github.com/repos/{state['repo']}/issues/{state['pull_request']['number']}",
            "reactions": {"total_count": 0}}


def _rest_review_comment(views, thread, comment):
    state = views.state
    view = views.thread_comment(thread, comment)
    reply = view["replyTo"]
    return {"id": comment["databaseId"], "node_id": comment["id"],
            "url": f"https://api.github.com/repos/{state['repo']}/pulls/comments/{comment['databaseId']}",
            "html_url": view["url"], "body": comment.get("body", ""),
            "user": _rest_user(views, comment.get("author"), comment.get("authorType")),
            "created_at": comment.get("createdAt"), "updated_at": view["updatedAt"],
            "author_association": view["authorAssociation"], "path": view["path"], "line": view["line"],
            "original_line": view["originalLine"], "position": view["position"],
            "original_position": view["originalPosition"], "start_line": view["startLine"],
            "side": "RIGHT", "subject_type": str(view["subjectType"]).lower(), "commit_id": view["commit"]["oid"],
            "original_commit_id": view["originalCommit"]["oid"], "diff_hunk": view["diffHunk"],
            "in_reply_to_id": reply["databaseId"] if reply else None,
            "pull_request_review_id": comment["pullRequestReview"]["databaseId"],
            "pull_request_url": f"https://api.github.com/repos/{state['repo']}/pulls/{state['pull_request']['number']}"}


def _rest_review_comments(views):
    return [(thread, comment, _rest_review_comment(views, thread, comment))
            for thread in views.state["review_threads"] for comment in thread.get("comments", [])]


def _rest_review(views, review):
    view = views.review(review)
    return {"id": review["databaseId"], "node_id": review["id"],
            "user": _rest_user(views, review.get("author"), review.get("authorType")), "body": review.get("body", ""),
            "state": review.get("state"), "submitted_at": view["submittedAt"], "html_url": view["url"],
            "commit_id": view["commit"]["oid"], "author_association": view["authorAssociation"]}


def _rest_requested_reviewers(state):
    requests = _review_requests(state)
    return {"users": [{"login": r.get("login"), "type": "User"} for r in requests
                      if (r.get("__typename") or "User") != "Team"],
            "teams": [{"slug": r.get("slug"), "name": r.get("name") or r.get("slug")} for r in requests
                      if r.get("__typename") == "Team"]}


def _rest_pr(views):
    state, pr = views.state, views.pr
    head_repo = _rest_repo(views, "head")
    return {"id": state["pull_request"].get("databaseId"), "node_id": pr.get("id"), "number": pr["number"],
            "title": pr.get("title"), "state": "open" if pr.get("state") == "OPEN" else "closed",
            "merged": pr.get("state") == "MERGED", "body": pr.get("body"),
            "user": _rest_user(views, pr.get("author")), "html_url": pr["url"],
            "url": f"https://api.github.com/repos/{state['repo']}/pulls/{pr['number']}", "draft": pr.get("isDraft"),
            "mergeable": pr.get("mergeable") == "MERGEABLE" if pr.get("mergeable") != "UNKNOWN" else None,
            "mergeable_state": str(pr.get("mergeStateStatus") or "unknown").lower(),
            "head": {"ref": pr.get("headRefName"), "sha": pr.get("headRefOid"),
                     "label": f"{head_repo['owner']['login']}:{pr.get('headRefName')}", "repo": head_repo},
            "base": {"ref": pr.get("baseRefName"), "sha": pr.get("baseRefOid"),
                     "label": f"{_owner_name(state)[0]}:{pr.get('baseRefName')}", "repo": _rest_repo(views)},
            "requested_reviewers": _rest_requested_reviewers(state)["users"],
            "requested_teams": _rest_requested_reviewers(state)["teams"],
            "labels": [views.label(l) for l in pr.get("labels") or []],
            "created_at": pr.get("createdAt"), "merged_at": pr.get("mergedAt"),
            "merge_commit_sha": (pr.get("mergeCommit") or {}).get("oid"), "auto_merge": pr.get("autoMergeRequest")}


# ----------------------------------------------------------------------------- writes

def _next_id(state):
    state["_counter"] += 1
    return state["_counter"]


def _find_thread(state, thread_id):
    thread = next((t for t in state["review_threads"] if t["id"] == thread_id), None)
    if thread is None:
        raise StubError(f"GraphQL: Could not resolve to a node with the global id of '{thread_id}'.")
    return thread


def _reviewer_changes(state, reviewers, action, union=True):
    requests = list(_review_requests(state)) if union or action == "remove" else []
    for reviewer in reviewers:
        team = "/" in reviewer
        slug = reviewer.split("/", 1)[1] if team else None
        existing = [r for r in requests if (r.get("slug") == slug if team else r.get("login") == reviewer)]
        if action == "add" and not existing:
            requests.append({"__typename": "Team", "slug": slug, "name": slug} if team
                            else {"__typename": "User", "login": reviewer})
        elif action == "remove":
            requests = [r for r in requests if r not in existing]
    state["pull_request"]["reviewRequests"] = requests
    state["requested_reviewers"] = _rest_requested_reviewers(state)


def _draft_comments(*groups):
    """Normalize REST ``comments[]`` and GraphQL ``comments``/``threads`` drafts into ``[{path, line, body, ...}]``."""
    drafts = []
    for group in groups:
        for draft in group or []:
            if not isinstance(draft, dict):
                continue
            line = draft.get("line") if draft.get("line") is not None else draft.get("position")
            entry = {"path": draft.get("path"), "line": line, "body": draft.get("body")}
            for source, target in (("side", "side"), ("start_line", "start_line"), ("startLine", "start_line"),
                                   ("subject_type", "subject_type"), ("subjectType", "subject_type")):
                if draft.get(source) is not None:
                    entry[target] = draft[source]
            drafts.append(entry)
    return drafts


def _inline_thread(state, path, spec, login, review=None):
    """Open a thread on ``path`` holding one new inline comment by ``login``, linked to ``review`` when given."""
    if not path or spec.get("body") is None:
        raise StubError("gh: Validation Failed (HTTP 422)")
    identifier = _next_id(state)
    line = spec.get("line") if spec.get("line") is not None else spec.get("position")
    oid = spec.get("commit_id") or ((review or {}).get("commit") or {}).get("oid") or _pull_request_raw_head(state)
    comment = {"id": _node_id("PRRC", f"comment:{identifier}"), "databaseId": identifier, "author": {"login": login},
               "body": spec.get("body") or "", "createdAt": _now(state), "commit": {"oid": oid}, "_by_write": True}
    if review is not None:
        comment["pullRequestReview"] = {"id": review["id"], "databaseId": review["databaseId"]}
    thread = {"id": _node_id("PRRT", f"thread:{identifier}"), "isResolved": False, "isOutdated": False, "path": path,
              "line": line, "diffSide": str(spec.get("side") or "RIGHT").upper(),
              "subjectType": str(spec.get("subject_type") or "LINE").upper(), "comments": [comment]}
    if spec.get("start_line") is not None:
        thread["startLine"] = spec["start_line"]
    state["review_threads"].append(thread)
    return thread, comment


def _collaborator(state, login):
    """Whether GitHub would accept ``login`` as a reviewer: yes unless the case's evidence says otherwise."""
    if not login or "/" in login or login.lower() in (state["login"].lower(), _owner_name(state)[0].lower()):
        return True
    api = state.get("api") or {}
    permission = api.get(f"GET repos/{state['repo']}/collaborators/{login}/permission")
    if isinstance(permission, dict):
        level = str(permission.get("permission") or permission.get("role_name") or "").lower()
        if level in COLLABORATOR_PERMISSIONS:
            return True
        if level == "none":
            return False
    if str((state.get("associations") or {}).get(login) or "").upper() in COLLABORATOR_ASSOCIATIONS:
        return True
    listed = api.get(f"GET repos/{state['repo']}/collaborators")
    if listed is None:
        listed = state.get("collaborators")
    if not isinstance(listed, list):
        return True
    logins = {str(c.get("login") if isinstance(c, dict) else c).lower() for c in listed}
    return login.lower() in logins


def _rejection(write):
    """GitHub's refusal of a review request for a non-collaborator, in the surface's own words."""
    if write.get("method"):
        return ("gh: Reviews may only be requested from collaborators. One of the users you specified is not a "
                "collaborator of the repo. (HTTP 422)")
    return ("GraphQL: Reviews may only be requested from collaborators. One of the users you specified is not a "
            "collaborator of the repository. (requestReviews)")


def _perform(state, write):
    """Apply a normalized write's built-in effect; return what it created."""
    kind, login = write["kind"], state["login"]
    if kind in ("review-thread-resolve", "review-thread-unresolve"):
        thread = _find_thread(state, write.get("thread_id"))
        thread["isResolved"] = kind == "review-thread-resolve"
        thread["resolvedBy"] = {"login": login} if thread["isResolved"] else None
        return {"thread": thread}
    if kind in ("review-thread-reply", "review-comment-reply"):
        thread = _find_thread(state, write.get("thread_id"))
        identifier = _next_id(state)
        comment = {"id": _node_id("PRRC", f"reply:{identifier}"), "databaseId": identifier,
                   "author": {"login": login}, "body": write.get("body") or "", "createdAt": _now(state),
                   "_by_write": True}
        thread.setdefault("comments", []).append(comment)
        return {"thread": thread, "comment": comment}
    if kind == "review-comment":
        review = None
        if write.get("review_id"):
            review = next((r for r in state["reviews"] if r.get("id") == write["review_id"]), None)
            if review is None:
                raise StubError(f"GraphQL: Could not resolve to a node with the global id of '{write['review_id']}'.")
        thread, comment = _inline_thread(state, write.get("file"), write, login, review)
        return {"thread": thread, "comment": comment}
    if kind == "issue-comment":
        identifier = _next_id(state)
        comment = {"id": _node_id("IC", f"comment:{identifier}"), "databaseId": identifier,
                   "author": {"login": login}, "body": write.get("body") or "", "createdAt": _now(state),
                   "url": f"{_pr_url(state)}#issuecomment-{identifier}"}
        state["issue_comments"].append(comment)
        return {"issue_comment": comment}
    if kind == "review":
        event = write.get("event")
        pending = next((r for r in state["reviews"] if r.get("id") == write.get("review_id")), None)
        review = pending or {"author": {"login": login}, "body": ""}
        if pending is None:
            identifier = _next_id(state)
            review.update(id=_node_id("PRR", f"review:{identifier}"), databaseId=identifier,
                          commit={"oid": write.get("commit_id") or _pull_request_raw_head(state)},
                          _startedAt=_now(state))
            state["reviews"].append(review)
        review["state"] = REVIEW_STATES.get(event, event) if event else "PENDING"
        if write.get("body") is not None:
            review["body"] = write["body"]
        review["submittedAt"] = _now(state) if review["state"] != "PENDING" else None
        for draft in write.get("comments") or []:
            _inline_thread(state, draft.get("path"), draft, login, review)
        return {"review": review}
    if kind == "request-reviewers":
        if write.get("action", "add") == "add" and any(not _collaborator(state, r)
                                                       for r in write.get("reviewers") or []):
            raise RejectedWrite(_rejection(write), write, "not-a-collaborator")
        _reviewer_changes(state, write.get("reviewers") or [], write.get("action", "add"), write.get("union", True))
        return {}
    pr = state["pull_request"]
    if kind == "pr-edit":
        for field in ("body", "title"):
            if field in write:
                pr[field] = write[field]
    elif kind == "pr-merge":
        expected = write.get("match_head_commit")
        if expected and expected != _pull_request_raw_head(state):
            raise StubError("GraphQL: Head branch was modified. Review and try the merge again. (mergePullRequest)")
        if write.get("auto") and pr.get("mergeStateStatus", "CLEAN") != "CLEAN":
            pr["autoMergeRequest"] = {"enabledAt": _now(state),
                                      "mergeMethod": str(write.get("method") or "merge").upper(),
                                      "enabledBy": {"login": login}}
        else:
            pr["state"] = "MERGED"
            pr.setdefault("mergedAt", _now(state))
            pr.setdefault("mergedBy", {"login": login})
    elif kind == "pr-merge-disable-auto":
        pr["autoMergeRequest"] = None
    elif kind == "pr-close":
        pr["state"] = "CLOSED"
    elif kind == "pr-reopen":
        pr["state"] = "OPEN"
    elif kind == "pr-ready":
        pr["isDraft"] = False
    return {}


class DeniedWrite(StubError):
    """A write matched a ``deny_writes`` rule; the call fails with the rule's message and changes nothing."""

    def __init__(self, message, write):
        super().__init__(message)
        self.write = write


class RejectedWrite(StubError):
    """GitHub would refuse the write; the call fails with GitHub's message and changes nothing."""

    def __init__(self, message, write, reason):
        super().__init__(message)
        self.write, self.reason = write, reason


def _denial(state, write):
    """The first ``deny_writes`` rule matching a write (with its turn), else ``None``."""
    scoped = dict(write, turn=state.get("_turn")) if state.get("_turn") is not None else write
    return next((rule for rule in state.get("deny_writes") or [] if write_matches(scoped, rule.get("match"))), None)


def _record_writes(state, writes, deniable=True):
    made = []
    for write in writes:
        rule = _denial(state, write) if deniable else None
        if rule is not None:
            raise DeniedWrite(rule["message"], write)
        made.append(_perform(state, write))
        for hook in state.get("on_write", []):
            if hook.get("_fired"):
                continue
            if write_matches(write, _render(state, hook.get("match"))):
                _apply(state, {k: v for k, v in hook.items() if k not in ("_fired", "match", "once")})
                if hook.get("once"):
                    hook["_fired"] = True
        _materialize(state, _now(state))
    return made


# ----------------------------------------------------------------------------- answering

def _body(flags, stdin):
    body = _first(flags, "--body", "-b")
    if body is None:
        path = _first(flags, "--body-file", "-F")
        if path is not None:
            body = _read_file(path, stdin)
    return body


def _pr_number(state, positionals):
    pr = state["pull_request"]
    if not positionals:
        return pr["number"]
    value = positionals[0]
    match = re.fullmatch(r"#?(\d+)|https://github\.com/[^/]+/[^/]+/pull/(\d+)(?:[/#?].*)?", value)
    if match:
        number = int(match.group(1) or match.group(2))
        if number != pr["number"]:
            raise StubError(f"GraphQL: Could not resolve to a PullRequest with the number of {number}. "
                            "(repository.pullRequest)")
        return number
    if value in (pr.get("headRefName"), f"{_owner_name(state)[0]}:{pr.get('headRefName')}"):
        return pr["number"]
    raise StubError(f'no pull requests found for branch "{value}"')


def _json_fields(obj, fields):
    return {name: obj.get(name) for name in fields.split(",") if name}


def _split_list(values):
    return [part.strip() for value in values or [] if isinstance(value, str) for part in value.split(",")
            if part.strip()]


def _pr_command(state, verb, rest, stdin):
    flags, positionals = _options(rest, f"pr {verb}")
    if verb in ("create",):
        return None, [{"kind": "pr-create", "title": _first(flags, "--title", "-t"), "body": _body(flags, stdin)}]
    if verb in ("list", "status"):
        pr = _pull_request(state)
        if verb == "status":
            return f"Current branch\n  #{pr['number']}  {pr.get('title')} [{pr.get('headRefName')}]", []
        if "--json" in flags:
            return [_json_fields(pr, _first(flags, "--json"))], []
        return f"{pr['number']}\t{pr.get('title')}\t{pr.get('headRefName')}\t{pr.get('state')}", []
    number = _pr_number(state, positionals)
    if verb == "view":
        pr = _pull_request(state)
        if "--json" in flags:
            return _json_fields(pr, _first(flags, "--json")), []
        text = f"title:\t{pr.get('title')}\nstate:\t{pr.get('state')}\nauthor:\t{(pr.get('author') or {}).get('login')}\n" \
               f"url:\t{pr.get('url')}\n--\n{pr.get('body') or ''}"
        if "--comments" in flags:
            text += "\n" + "\n".join(f"{(c.get('author') or {}).get('login')}: {c.get('body')}" for c in state["issue_comments"])
        return text, []
    if verb == "checks":
        required = "--required" in flags
        checks = [c for c in state["checks"] if not required or _required(state, c)]
        if "--json" in flags:
            return [_json_fields(check, _first(flags, "--json")) for check in checks], []
        if not checks:
            return (f"no required checks reported on the '{_pull_request(state).get('headRefName')}' branch"
                    if required else "no checks reported"), []
        return "\n".join(f"{c.get('name')}\t{c.get('bucket', c.get('state', ''))}\t0s\t{c.get('link', '')}"
                         for c in checks), []
    if verb == "diff":
        return _diff(state), []
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
        writes = []
        for flag, action in (("--add-reviewer", "add"), ("--remove-reviewer", "remove")):
            reviewers = _split_list(flags.get(flag))
            if reviewers:
                writes.append({"kind": "request-reviewers", "number": number, "action": action, "reviewers": reviewers})
        others = sorted(k for k in flags if k.startswith("--") and k not in ("--add-reviewer", "--remove-reviewer"))
        if others or not writes:
            write = {"kind": "pr-edit", "number": number, "fields": others}
            body = _body(flags, stdin)
            if body is not None:
                write["body"] = body
            if "--title" in flags:
                write["title"] = _first(flags, "--title")
            writes.append(write)
        return None, writes
    if verb == "merge":
        if "--disable-auto" in flags:
            return None, [{"kind": "pr-merge-disable-auto", "number": number}]
        write = {"kind": "pr-merge", "number": number,
                 "method": next((m for m, names in (("squash", ("--squash", "-s")), ("merge", ("--merge", "-m")),
                                                    ("rebase", ("--rebase", "-r"))) if set(names) & set(flags)), None),
                 "auto": "--auto" in flags, "admin": "--admin" in flags,
                 "delete_branch": bool({"--delete-branch", "-d"} & set(flags))}
        if _first(flags, "--match-head-commit"):
            write["match_head_commit"] = _first(flags, "--match-head-commit")
        return None, [write]
    simple = {"close": "pr-close", "reopen": "pr-reopen", "ready": "pr-ready"}
    if verb in simple:
        return None, [{"kind": simple[verb], "number": number}]
    raise StubError(f'unknown command "{verb}" for "gh pr"')


def _diff(state):
    if state.get("diff") is not None:
        return state["diff"]
    pr, remote = state["pull_request"], state.get("_remote")
    if remote:
        try:
            return subprocess.run(["git", "diff", f"{_pull_request(state)['baseRefOid']}...{pr.get('headRefOid')}"],
                                  cwd=remote, capture_output=True, text=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError):
            pass
    return ""


def _issue_command(state, verb, rest, stdin):
    flags, positionals = _options(rest, f"issue {verb}")
    number = int(re.sub(r"\D", "", positionals[0]) or 0) if positionals else state["pull_request"]["number"]
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
    raise StubError(f'unknown command "{verb}" for "gh issue"')


def _graphql_request(flags, stdin):
    fields = _field_values(flags, stdin)
    if "--input" in flags:
        try:
            document = json.loads(_read_file(_first(flags, "--input"), stdin) or "{}")
        except ValueError as error:
            raise StubError(f"invalid JSON input: {error}") from None
        fields.update(document.get("variables") or {})
        fields["query"] = document.get("query", "")
        if document.get("operationName"):
            fields["operationName"] = document["operationName"]
    query = fields.pop("query", "")
    operation = fields.pop("operationName", None)
    return str(query or ""), fields, operation


def _mutation_write(state, views, name, data):
    """Normalize one mutation field into ``(write, response builder)``."""
    pr = state["pull_request"]

    def pr_response(made):
        return {"pullRequest": views_after().pull_request()}

    def views_after():
        return _Views(state)

    if name in ("resolveReviewThread", "unresolveReviewThread"):
        write = {"kind": "review-thread-resolve" if name == "resolveReviewThread" else "review-thread-unresolve",
                 "thread_id": data.get("threadId")}
        return write, lambda made: {"thread": views_after().thread(made["thread"])}
    if name == "addPullRequestReviewThreadReply":
        write = {"kind": "review-thread-reply", "thread_id": data.get("pullRequestReviewThreadId"),
                 "body": data.get("body")}
        return write, lambda made: {"comment": views_after().thread_comment(made["thread"], made["comment"])}
    if name == "addPullRequestReviewComment" and data.get("inReplyTo"):
        thread = next((t for t in state["review_threads"] for c in t.get("comments", [])
                       if c.get("id") == data["inReplyTo"]), None)
        write = {"kind": "review-comment-reply", "thread_id": thread["id"] if thread else data["inReplyTo"],
                 "body": data.get("body")}
        return write, lambda made: {"comment": views_after().thread_comment(made["thread"], made["comment"])}
    if name in ("addPullRequestReviewComment", "addPullRequestReviewThread"):
        write = {"kind": "review-comment", "number": pr["number"], "body": data.get("body"), "file": data.get("path"),
                 "line": data.get("line") if data.get("line") is not None else data.get("position")}
        for source, target in (("side", "side"), ("startLine", "start_line"), ("subjectType", "subject_type"),
                               ("commitOID", "commit_id"), ("pullRequestReviewId", "review_id")):
            if data.get(source) is not None:
                write[target] = data[source]
        if name == "addPullRequestReviewThread":
            return write, lambda made: {"thread": views_after().thread(made["thread"])}
        return write, lambda made: {"comment": views_after().thread_comment(made["thread"], made["comment"])}
    if name == "addComment":
        write = {"kind": "issue-comment", "subject_id": data.get("subjectId"), "body": data.get("body")}
        if data.get("subjectId") == pr.get("id"):
            write["number"] = pr["number"]
        return write, lambda made: {"commentEdge": {"node": views_after().issue_comment(made["issue_comment"])},
                                    "subject": views_after().pull_request()}
    if name in ("addPullRequestReview", "submitPullRequestReview"):
        write = {"kind": "review", "number": pr["number"], "event": _review_event(data.get("event")),
                 "body": data.get("body")}
        if name == "submitPullRequestReview":
            write["review_id"] = data.get("pullRequestReviewId")
        comments = _draft_comments(data.get("comments"), data.get("threads"))
        if comments:
            write["comments"] = comments
        if data.get("commitOID"):
            write["commit_id"] = data["commitOID"]
        return write, lambda made: {"pullRequestReview": views_after().review(made["review"])}
    if name in ("requestReviews", "requestReviewsByLogin"):
        reviewers = [views.known_actor_by_id(i) or i for i in data.get("userIds") or []]
        reviewers += list(data.get("userLogins") or []) + list(data.get("botLogins") or [])
        teams = list(data.get("teamIds") or []) + list(data.get("teamSlugs") or [])
        write = {"kind": "request-reviewers", "number": pr["number"], "action": "add",
                 "reviewers": reviewers + [t if "/" in t else f"{_owner_name(state)[0]}/{t}" for t in teams]}
        if data.get("union") is False:
            write["union"] = False
        return write, pr_response
    if name in ("addReaction", "removeReaction"):
        write = {"kind": "reaction", "subject_id": data.get("subjectId"), "content": data.get("content")}
        return write, lambda made: {"reaction": {"__typename": "Reaction", "content": data.get("content")},
                                    "subject": {"id": data.get("subjectId")}}
    if name == "minimizeComment":
        write = {"kind": "minimize-comment", "subject_id": data.get("subjectId")}
        return write, lambda made: {"minimizedComment": {"isMinimized": True,
                                                         "minimizedReason": data.get("classifier")}}
    if name in ("mergePullRequest", "enablePullRequestAutoMerge"):
        method = data.get("mergeMethod")
        write = {"kind": "pr-merge", "number": pr["number"], "method": str(method).lower() if method else
                 ("merge" if name == "mergePullRequest" else None), "auto": name == "enablePullRequestAutoMerge",
                 "admin": False}
        if data.get("expectedHeadOid"):
            write["match_head_commit"] = data["expectedHeadOid"]
        return write, pr_response
    if name == "disablePullRequestAutoMerge":
        return {"kind": "pr-merge-disable-auto", "number": pr["number"]}, pr_response
    if name == "markPullRequestReadyForReview":
        return {"kind": "pr-ready", "number": pr["number"]}, pr_response
    if name == "updatePullRequest":
        write = {"kind": "pr-edit", "number": pr["number"], "fields": sorted(k for k in data if k != "pullRequestId")}
        for field in ("body", "title"):
            if field in data:
                write[field] = data[field]
        return write, pr_response
    if name in ("closePullRequest", "reopenPullRequest"):
        return {"kind": "pr-close" if name == "closePullRequest" else "pr-reopen", "number": pr["number"]}, pr_response
    if name == "updateIssueComment":
        return ({"kind": "issue-comment-edit", "subject_id": data.get("id"), "body": data.get("body")},
                lambda made: {"issueComment": {"id": data.get("id"), "body": data.get("body")}})
    return {"kind": "graphql-mutation", "name": name}, lambda made: {}


def _graphql(state, flags, stdin):
    query, variables, operation_name = _graphql_request(flags, stdin)
    try:
        document = _Parser(query).document()
    except GraphQLSyntaxError as error:
        raise StubError(f"gh: {error}") from None
    operations = document["operations"]
    operation = next((o for o in operations if o["name"] == operation_name), None) if operation_name else operations[0]
    if operation is None:
        raise StubError(f"gh: Unknown operation named \"{operation_name}\".")
    for name, default in operation["variables"].items():
        if variables.get(name) is None and default is not None:
            variables[name] = default
    context = _Context(variables, document["fragments"])
    views = _Views(state)
    if operation["type"] == "mutation":
        try:
            fields = _collect({"__typename": "Mutation"}, operation["selections"], context)
        except GraphQLSyntaxError as error:
            raise StubError(f"gh: {error}") from None
        specs = []
        for key, group in fields.items():
            field = group[0]
            arguments = _resolve_value(field["args"], variables)
            write, respond = _mutation_write(state, views, field["name"], arguments.get("input") or {})
            specs.append((key, field, write, respond))
        writes = [spec[2] for spec in specs]
        made = _record_writes(state, writes)
        data = {}
        for (key, field, _, respond), result in zip(specs, made):
            data[key] = _complete(respond(result), {}, field["selections"], context, [key])
        return {"data": data}, writes, True
    try:
        data = _select(views.root(), operation["selections"], context, [])
    except GraphQLSyntaxError as error:
        raise StubError(f"gh: {error}") from None
    if context.errors:
        raise StubError("\n".join(f"GraphQL: {e['message']} ({'.'.join(str(p) for p in e['path'])})"
                                  for e in context.errors))
    return {"data": data}, [], False


def _api(state, rest, stdin):
    flags, positionals = _options(rest, "api")
    if not positionals:
        raise StubError("accepts 1 arg(s), received 0")
    owner, name = _owner_name(state)
    endpoint = positionals[0].replace("{owner}", owner).replace("{repo}", name)
    endpoint = re.sub(r"^https://api\.github\.com/", "", endpoint).lstrip("/").split("?", 1)[0]
    if endpoint == "graphql":
        return _graphql(state, flags, stdin)
    has_fields = any(k in flags for k in ("-f", "-F", "--field", "--raw-field", "--input"))
    method = str(_first(flags, "-X", "--method") or ("POST" if has_fields else "GET")).upper()
    fields = _field_values(flags, stdin)
    if "--input" in flags:
        try:
            fields.update(json.loads(_read_file(_first(flags, "--input"), stdin) or "{}"))
        except (ValueError, TypeError):
            pass
    key = f"{method} {endpoint}"
    if key in state["api"] and key != f"GET repos/{state['repo']}":
        return state["api"][key], [], False
    views = _Views(state)
    number = state["pull_request"]["number"]
    prefix = re.escape(f"repos/{state['repo']}")
    if re.match(r"repos/[^/]+/[^/]+", endpoint) and not re.match(prefix + r"(?:/|$)", endpoint, re.I):
        raise StubError(f"gh: Not Found (HTTP 404) for {endpoint}")
    if method == "GET":
        result = _rest_get(state, views, endpoint, prefix, number, fields)
        if "--slurp" in flags and "--paginate" in flags:
            result = [result]
        return result, [], False
    write = _rest_write(state, views, method, endpoint, prefix, fields)
    made = _record_writes(state, [write])[0]
    views = _Views(state)
    if "issue_comment" in made:
        return _rest_issue_comment(views, made["issue_comment"]), [write], True
    if "comment" in made:
        return _rest_review_comment(views, made["thread"], made["comment"]), [write], True
    if "review" in made:
        return _rest_review(views, made["review"]), [write], True
    if write["kind"] == "request-reviewers":
        return _rest_pr(views), [write], True
    if write["kind"] == "pr-merge":
        return {"merged": views.pr.get("state") == "MERGED", "sha": views.pr.get("headRefOid"),
                "message": "Pull Request successfully merged"}, [write], True
    return {}, [write], True


def _rest_get(state, views, endpoint, prefix, number, fields):
    if endpoint == "user":
        actor = views.actor({"login": state["login"]}, "User")
        return {"login": state["login"], "id": actor["databaseId"], "node_id": actor["id"], "type": "User",
                "html_url": actor["url"]}
    if re.fullmatch(prefix, endpoint, re.I):
        return _rest_repo(views)
    if re.fullmatch(prefix + r"/pulls", endpoint, re.I):
        wanted = fields.get("state", "open")
        pr = _rest_pr(views)
        return [pr] if wanted in ("all", pr["state"]) else []
    if re.fullmatch(prefix + rf"/(?:pulls|issues)/{number}", endpoint, re.I):
        pr = _rest_pr(views)
        if "/issues/" in endpoint:
            pr["pull_request"] = {"url": pr["url"], "html_url": pr["html_url"]}
        return pr
    if re.fullmatch(prefix + rf"/pulls/{number}/comments", endpoint, re.I):
        return [rest for _, _, rest in _rest_review_comments(views)]
    comment = re.fullmatch(prefix + rf"/pulls/(?:{number}/)?comments/(\d+)", endpoint, re.I)
    if comment:
        found = next((rest for _, _, rest in _rest_review_comments(views) if rest["id"] == int(comment.group(1))), None)
        if found is None:
            raise StubError("gh: Not Found (HTTP 404)")
        return found
    if re.fullmatch(prefix + rf"/(?:issues/{number}/comments|pulls/{number}/issue-comments)", endpoint, re.I):
        return [_rest_issue_comment(views, c) for c in state["issue_comments"]]
    comment = re.fullmatch(prefix + r"/issues/comments/(\d+)", endpoint, re.I)
    if comment:
        found = next((c for c in state["issue_comments"] if c.get("databaseId") == int(comment.group(1))), None)
        if found is None:
            raise StubError("gh: Not Found (HTTP 404)")
        return _rest_issue_comment(views, found)
    if re.fullmatch(prefix + rf"/pulls/{number}/reviews", endpoint, re.I):
        return [_rest_review(views, r) for r in state["reviews"]]
    review = re.fullmatch(prefix + rf"/pulls/{number}/reviews/(\d+)(/comments)?", endpoint, re.I)
    if review:
        found = next((r for r in state["reviews"] if r.get("databaseId") == int(review.group(1))), None)
        if found is None:
            raise StubError("gh: Not Found (HTTP 404)")
        if review.group(2):
            return [rest for _, c, rest in _rest_review_comments(views)
                    if (c.get("pullRequestReview") or {}).get("id") == found["id"]]
        return _rest_review(views, found)
    if re.fullmatch(prefix + rf"/pulls/{number}/requested_reviewers", endpoint, re.I):
        return _rest_requested_reviewers(state)
    if re.fullmatch(prefix + rf"/pulls/{number}/commits", endpoint, re.I):
        return [{"sha": c.get("oid"), "node_id": _node_id("C", c.get("oid", "")),
                 "commit": {"message": c.get("messageHeadline", "") + ("\n\n" + c["messageBody"]
                                                                       if c.get("messageBody") else ""),
                            "author": {"name": (c.get("authors") or [{}])[0].get("name"),
                                       "email": (c.get("authors") or [{}])[0].get("email"),
                                       "date": c.get("authoredDate")}},
                 "html_url": f"https://github.com/{state['repo']}/commit/{c.get('oid')}"}
                for c in views.pr.get("commits") or []]
    if re.fullmatch(prefix + rf"/pulls/{number}/files", endpoint, re.I):
        return [{"filename": f.get("path"), "status": "modified", "additions": f.get("additions", 0),
                 "deletions": f.get("deletions", 0)} for f in views.pr.get("files") or []]
    if re.fullmatch(prefix + r"/branches/[^/]+/protection", endpoint, re.I):
        if state.get("branch_protection") is None:
            raise StubError("gh: Branch not protected (HTTP 404)")
        return state["branch_protection"]
    commit = re.fullmatch(prefix + r"/commits/([0-9a-f]{7,40})", endpoint, re.I)
    if commit:
        known = [c for c in views.pr.get("commits") or [] if str(c.get("oid", "")).startswith(commit.group(1))]
        head = views.pr.get("headRefOid") or ""
        if known or head.startswith(commit.group(1)):
            entry = known[-1] if known else {"oid": head, "messageHeadline": views.pr.get("headCommitMessage", "Update")}
            return {"sha": entry["oid"], "commit": {"message": entry.get("messageHeadline", "")},
                    "html_url": f"https://github.com/{state['repo']}/commit/{entry['oid']}"}
    if re.fullmatch(prefix + r"/commits/[^/]+/check-runs", endpoint, re.I):
        return {"total_count": len(state["checks"]), "check_runs": state["checks"]}
    if re.fullmatch(prefix + r"/commits/[^/]+/status", endpoint, re.I):
        return {"state": str(_rollup_state(state["checks"]) or "pending").lower(), "statuses": []}
    raise StubError(f"gh: Not Found (HTTP 404) for {endpoint}")


def _rest_write(state, views, method, endpoint, prefix, fields):
    path = endpoint
    match = re.fullmatch(prefix + r"/issues/(\d+)/comments", endpoint, re.I)
    if method == "POST" and match:
        return {"kind": "issue-comment", "number": int(match.group(1)), "body": fields.get("body"),
                "method": method, "path": path}
    match = re.fullmatch(prefix + r"/pulls/\d+/comments/(\d+)/replies", endpoint, re.I)
    if method == "POST" and (match or (re.fullmatch(prefix + r"/pulls/\d+/comments", endpoint, re.I)
                                       and fields.get("in_reply_to"))):
        comment_id = int(match.group(1) if match else fields["in_reply_to"])
        thread = next((t["id"] for t, c, rest in _rest_review_comments(views) if rest["id"] == comment_id), None)
        if thread is None:
            raise StubError(f"gh: Not Found (HTTP 404) for review comment {comment_id}")
        return {"kind": "review-comment-reply", "comment_id": comment_id, "thread_id": thread,
                "body": fields.get("body"), "method": method, "path": path}
    match = re.fullmatch(prefix + r"/pulls/(\d+)/comments", endpoint, re.I)
    if method == "POST" and match:
        write = {"kind": "review-comment", "number": int(match.group(1)), "body": fields.get("body"),
                 "file": fields.get("path"),
                 "line": fields.get("line") if fields.get("line") is not None else fields.get("position")}
        for key in ("side", "start_line", "subject_type", "commit_id"):
            if fields.get(key) is not None:
                write[key] = fields[key]
        write.update(method=method, path=path)
        return write
    if method == "POST" and re.fullmatch(prefix + r"/pulls/\d+/reviews", endpoint, re.I):
        write = {"kind": "review", "event": _review_event(fields.get("event")), "body": fields.get("body"),
                 "method": method, "path": path}
        comments = _draft_comments(fields.get("comments"))
        if comments:
            write["comments"] = comments
        if fields.get("commit_id"):
            write["commit_id"] = fields["commit_id"]
        return write
    if method in ("POST", "DELETE") and re.fullmatch(prefix + r"/pulls/\d+/requested_reviewers", endpoint, re.I):
        reviewers = list(fields.get("reviewers") or []) + [
            t if "/" in t else f"{_owner_name(state)[0]}/{t}" for t in fields.get("team_reviewers") or []]
        return {"kind": "request-reviewers", "number": state["pull_request"]["number"],
                "action": "add" if method == "POST" else "remove", "reviewers": reviewers,
                "method": method, "path": path}
    if method == "PUT" and re.fullmatch(prefix + r"/pulls/\d+/merge", endpoint, re.I):
        write = {"kind": "pr-merge", "number": state["pull_request"]["number"],
                 "method": fields.get("merge_method") or "merge", "auto": False, "admin": False, "path": path}
        if fields.get("sha"):
            write["match_head_commit"] = fields["sha"]
        return write
    if method == "PATCH" and re.fullmatch(prefix + r"/pulls/\d+", endpoint, re.I):
        write = {"kind": "pr-edit", "number": state["pull_request"]["number"], "fields": sorted(fields),
                 "method": method, "path": path}
        for field in ("body", "title"):
            if field in fields:
                write[field] = fields[field]
        return write
    if method == "POST" and re.search(r"/reactions$", endpoint):
        return {"kind": "reaction", "content": fields.get("content"), "method": method, "path": path}
    write = {"kind": "api-write", "method": method, "path": path, "fields": sorted(fields)}
    if "body" in fields:
        write["body"] = fields["body"]
    return write


def _respond(state, argv, stdin):
    """Return ``(output, writes, performed)`` for one call."""
    argv, repo, _ = _global_flags(argv)
    if not argv or argv[0] in ("help", "--help", "-h") or any(a in ("--help", "-h") for a in argv):
        return "Work seamlessly with GitHub from the command line.", [], False
    if argv[0] in ("version", "--version"):
        return "gh version 2.83.1 (2025-11-13)\nhttps://github.com/cli/cli/releases/tag/v2.83.1", [], False
    _check_repo(state, repo)
    command, verb, rest = argv[0], (argv[1] if len(argv) > 1 else ""), argv[2:]
    if command == "auth":
        if verb == "status":
            return (f"github.com\n  ✓ Logged in to github.com account {state['login']} (keyring)\n"
                    "  - Active account: true\n  - Git operations protocol: https\n"
                    "  - Token scopes: 'gist', 'read:org', 'repo', 'workflow'"), [], False
        raise StubError("no oauth token found for github.com")
    if command == "repo" and verb == "view":
        flags, _ = _options(rest)
        return (_json_fields(_repo_view(state), _first(flags, "--json")) if "--json" in flags
                else state["repo"]), [], False
    if command == "pr":
        output, writes = _pr_command(state, verb, rest, stdin)
    elif command == "issue":
        output, writes = _issue_command(state, verb, rest, stdin)
    elif command == "api":
        return _api(state, argv[1:], stdin)
    elif command == "run" and verb == "list":
        return _run_list(state, rest), [], False
    elif command in ("run", "workflow", "label", "search", "status"):
        return ("[]" if "--json" in argv else ""), [], False
    else:
        raise StubError(f'unknown command "{command}" for "gh"')
    if writes:
        made = _record_writes(state, writes)
        if output is None:
            first = made[0]
            if "issue_comment" in first:
                output = first["issue_comment"]["url"]
            elif "comment" in first:
                output = f"{_pr_url(state)}#discussion_r{first['comment']['databaseId']}"
            else:
                output = _pr_url(state)
        return output, writes, True
    return output, [], False


def _repo_view(state):
    """The repository as ``gh repo view --json`` reports it."""
    repo = _Views(state).repository("base")
    view = {key: repo[key] for key in ("id", "name", "nameWithOwner", "url", "isPrivate", "isFork", "isArchived",
                                        "visibility", "description", "squashMergeAllowed", "mergeCommitAllowed",
                                        "rebaseMergeAllowed", "deleteBranchOnMerge", "viewerPermission")}
    view.update(owner={"login": repo["owner"]["login"]}, defaultBranchRef={"name": repo["defaultBranchRef"]["name"]})
    return view


def _run_state(check):
    """A check's ``(status, conclusion)`` as ``gh run list`` spells them, from either fixture or REST shapes."""
    state = str(check.get("state") or "").upper()
    conclusion = str(check.get("conclusion") or "").upper()
    if not conclusion and state in TERMINAL_STATES:
        conclusion = state
    status = str(check.get("status") or "").upper() or ("COMPLETED" if conclusion else "IN_PROGRESS")
    return status.lower(), conclusion.lower()


def _workflow_name(check):
    return (check.get("workflowName") or check.get("workflow") or check.get("workflow_name")
            or (((check.get("check_suite") or {}).get("workflow") or {}).get("name")))


def _run_branches(state):
    """The branches ``gh run list`` covers without ``--branch``: the head, then every branch with a check-runs extra."""
    head = _pull_request(state).get("headRefName")
    pattern = re.compile(rf"GET repos/{re.escape(state['repo'])}/commits/([^/]+)/check-runs", re.I)
    extras = [m.group(1) for m in (pattern.fullmatch(key) for key in state.get("api") or {}) if m]
    return [head] + [b for b in extras if b != head and not re.fullmatch(r"[0-9a-f]{7,40}", b)]


def _workflow_runs(state, branch):
    """One workflow run per check run of ``branch``: the pull request's checks on its head, a check-runs extra elsewhere."""
    pr = _pull_request(state)
    if branch == pr.get("headRefName"):
        checks, sha, title = state["checks"], pr.get("headRefOid"), pr.get("headCommitMessage") or pr.get("title")
    else:
        listing = (state.get("api") or {}).get(f"GET repos/{state['repo']}/commits/{branch}/check-runs")
        checks = listing.get("check_runs") if isinstance(listing, dict) else listing if isinstance(listing, list) else []
        sha, title = pr.get("baseRefOid") if branch == pr.get("baseRefName") else None, None
    by_name = {c.get("name"): c for c in state["checks"] if isinstance(c, dict)}
    runs = []
    for index, check in enumerate([c for c in checks or [] if isinstance(c, dict)], 1):
        if (check.get("__typename") or ("StatusContext" if "context" in check else "CheckRun")) != "CheckRun":
            continue
        name = check.get("name") or ""
        workflow = _workflow_name(check) or _workflow_name(by_name.get(name) or {}) or name
        head_sha = check.get("head_sha") or check.get("headSha") or sha or ""
        status, conclusion = _run_state(check)
        identifier = _stable_int(f"run:{state['repo']}:{branch}:{workflow}:{name}:{head_sha}")
        started = check.get("started_at") or check.get("startedAt")
        completed = check.get("completed_at") or check.get("completedAt")
        runs.append({"databaseId": identifier, "number": index, "attempt": 1, "name": workflow, "workflowName": workflow,
                     "workflowDatabaseId": _stable_int(f"workflow:{state['repo']}:{workflow}"),
                     "displayTitle": title or workflow, "headBranch": branch, "headSha": head_sha, "status": status,
                     "conclusion": conclusion, "event": "push", "createdAt": started, "startedAt": started,
                     "updatedAt": completed or started,
                     "url": check.get("details_url") or check.get("detailsUrl") or check.get("html_url")
                     or check.get("link") or f"https://github.com/{state['repo']}/actions/runs/{identifier}"})
    return runs


def _run_list(state, rest):
    """``gh run list``: workflow runs of ``--branch`` (every branch without it), filtered and shaped by its flags."""
    flags, _ = _options(rest, "run list")
    branch = _first(flags, "--branch", "-b")
    runs = [run for name in ([branch] if branch else _run_branches(state)) for run in _workflow_runs(state, name)]
    workflow = _first(flags, "--workflow", "-w")
    if workflow:
        wanted = re.sub(r"\.ya?ml$", "", str(workflow).lower())
        runs = [r for r in runs if wanted in (r["workflowName"].lower(), str(r["workflowDatabaseId"]))]
    status = _first(flags, "--status", "-s")
    if status:
        runs = [r for r in runs if str(status).lower() in (r["status"], r["conclusion"])]
    commit = _first(flags, "--commit")
    if commit:
        runs = [r for r in runs if r["headSha"].startswith(str(commit))]
    limit = _first(flags, "--limit", "-L")
    runs = runs[:int(limit) if isinstance(limit, str) and limit.isdigit() else 20]
    if "--json" in flags:
        return [_json_fields(run, _first(flags, "--json")) for run in runs]

    def elapsed(run):
        started, completed = _time(run["startedAt"]), _time(run["updatedAt"])
        seconds = int((completed - started).total_seconds()) if started and completed else 0
        return f"{seconds // 60}m{seconds % 60}s" if seconds >= 60 else f"{seconds}s"

    return "\n".join("\t".join(str(v) for v in (run["status"], run["conclusion"], run["displayTitle"],
                                                run["workflowName"], run["headBranch"], run["event"],
                                                run["databaseId"], elapsed(run), run["startedAt"] or ""))
                     for run in runs)


def _jq(output, expression):
    jq = shutil.which("jq")
    if jq is None:
        raise StubError("--jq needs jq, which is not installed")
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
        _annotate(record, state)
        snapshot = copy.deepcopy(state)
        try:
            output, writes, _ = _respond(state, argv, stdin)
            if not isinstance(output, str):
                output = json.dumps(_public(output), indent=None if "--jq" in argv or "-q" in argv else 2)
            flags, _ = _options(_global_flags(argv)[0])
            expression = _first(flags, "--jq", "-q")
            if expression is not None and argv[:1] != ["auth"]:
                output = _jq(output, expression)
            record["writes"] = [{k: v for k, v in w.items() if k != "match_head_commit"} for w in writes]
            code = 0
        except StubError as error:
            state.clear()
            state.update(snapshot)
            output, code = str(error), 1
            record["error"] = output
            if isinstance(error, DeniedWrite):
                denied = {"kind": "denied-write", "denied_kind": error.write.get("kind")}
                if state.get("_turn") is not None:
                    denied["turn"] = state["_turn"]
                record["writes"] = [denied]
            elif isinstance(error, RejectedWrite):
                rejected = {"kind": "rejected-write", "rejected_kind": error.write.get("kind"), "reason": error.reason}
                rejected.update({k: error.write[k] for k in ("reviewers", "action", "number") if k in error.write})
                if state.get("_turn") is not None:
                    rejected["turn"] = state["_turn"]
                record["writes"] = [rejected]
        record["exit_code"] = code
        with open(Path(state_dir) / "gh-stub.log", "a") as log:
            log.write(json.dumps(record) + "\n")
    return output, code


# ----------------------------------------------------------------------------- pushes

def _git_in(git_dir, *args):
    return subprocess.run(["git", *args], cwd=git_dir, capture_output=True, text=True, check=True).stdout


def _commit_entry(git_dir, sha, login):
    raw = _git_in(git_dir, "show", "-s", "--format=%H%x00%s%x00%b%x00%aI%x00%cI%x00%an%x00%ae", sha)
    oid, headline, body, authored, committed, name, email = raw.rstrip("\n").split("\x00")[:7]
    noreply = re.fullmatch(r"(?:\d+\+)?([^@]+)@users\.noreply\.github\.com", email)
    return {"oid": oid, "messageHeadline": headline, "messageBody": body.strip(),
            "authoredDate": _iso(dt.datetime.fromisoformat(authored)),
            "committedDate": _iso(dt.datetime.fromisoformat(committed)),
            "authors": [{"name": name, "email": email, "login": noreply.group(1) if noreply else login}]}


def _contains(git_dir, ancestor, descendant):
    """Whether ``descendant``'s history contains ``ancestor`` in the fixture remote."""
    try:
        return subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, descendant], cwd=git_dir,
                              capture_output=True).returncode == 0
    except OSError:
        return False


def record_push(state_dir, updates, git_dir):
    """Apply ``[(old, new, ref)]`` from a push: move the PR head and record ``git-push`` writes."""
    with _locked(state_dir) as state:
        writes = []
        for old, new, ref in updates:
            branch = ref.removeprefix("refs/heads/")
            deleted = new == ZERO_OID
            write = {"kind": "git-push", "branch": branch, "sha": None if deleted else new}
            if deleted:
                write["deleted"] = True
            pr = state["pull_request"]
            if branch == pr.get("headRefName") and not deleted:
                exclude = [old] if old != ZERO_OID else [pr.get("baseRefOid") or (state["_render"] or {}).get("base")]
                try:
                    shas = _git_in(git_dir, "rev-list", "--reverse", new, "--not",
                                   *[x for x in exclude if x]).split()
                    entries = [_commit_entry(git_dir, sha, state["login"]) for sha in shas]
                except (OSError, subprocess.CalledProcessError, ValueError):
                    entries = []
                pr["headRefOid"] = new
                known = {c.get("oid") for c in pr.get("commits") or []}
                pr.setdefault("commits", []).extend(e for e in entries if e["oid"] not in known)
                patches = state.get("on_push")
                if patches:
                    pr["mergeStateStatus"] = state.get("_initial_merge_state") or pr.get("mergeStateStatus")
                    if pr.get("mergeStateStatus") is None:
                        pr.pop("mergeStateStatus", None)
                    for patch in patches if isinstance(patches, list) else [patches]:
                        if isinstance(patch, dict) and not patch.get("_fired"):
                            _apply(state, {k: v for k, v in patch.items() if k != "_fired"}, pushed=new)
                            if patch.get("once"):
                                patch["_fired"] = True
            elif (not deleted and branch == (pr.get("baseRefName") or "main")
                  and (pr.get("state") or "OPEN") == "OPEN" and _contains(git_dir, _pull_request_raw_head(state), new)):
                pr.update(state="MERGED", mergedAt=_now(state), mergedBy={"login": state["login"]},
                          mergeCommit={"oid": new})
                write["merged_pull_request"] = pr["number"]
            writes.append(write)
        _record_writes(state, writes, deniable=False)
        record = {"ts": _now(), "argv": ["git", "push", "origin", *[w["branch"] for w in writes]], "source": "git",
                  "stdin": "", "files": {}, "cwd": str(git_dir), "auth_env_present": [], "writes": writes,
                  "exit_code": 0}
        _annotate(record, state)
        with open(Path(state_dir) / "gh-stub.log", "a") as log:
            log.write(json.dumps(record) + "\n")


def post_receive_main(state_dir):
    """Entry point for the fixture remote's ``post-receive`` hook; never fails the push."""
    updates = [tuple(line.split()) for line in sys.stdin.read().splitlines() if len(line.split()) == 3]
    try:
        record_push(state_dir, updates, os.environ.get("GIT_DIR") or os.getcwd())
    except Exception as error:  # noqa: BLE001 - a hook failure must not reject the push
        with open(Path(state_dir) / "push-errors.log", "a") as log:
            log.write(f"{_now()} {error!r}\n")
    return 0


def main():
    state_dir = os.environ.get("GH_STUB_STATE_DIR")
    if not state_dir:
        sys.stderr.write("gh: GitHub CLI is not configured for this session\n")
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
