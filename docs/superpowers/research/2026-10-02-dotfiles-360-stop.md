# Why the dotfiles Git-defaults pull request stopped at ready

The agent that opened and readied [fix(agents): move personal Git defaults into user-level rules](https://github.com/nisavid/dotfiles/pull/360) stopped on the merge condition in its own task text. Its first prompt opened "Resolve https://github.com/nisavid/dotfiles/issues/359 end to end" and ended "take the change through a PR that closes #359 (use /mergecraft:getting-prs-merged if the operator asks for merge)". Another Claude Opus 5.5 session wrote that prompt and handed it over through a suggested-task chip, and Ivan started it. The agent restated the condition before it waited on CI and again when it stopped, and its recorded reasoning never mentions "end to end". None of the three texts the ticket names was in its context when it stopped. It never invoked, opened, or reasoned about `getting-prs-merged`. This was a **scope stop**: the agent took the conditional clause as the task's bound, so merge never entered its outcome set, even though the opening "end to end" could have been read to include it. The four other fix threads spawned in the same batch carried no merge condition and no "end to end", and none of them continued into merge either. The dotfiles#324 record matches the cause the readiness-ownership decision already records.

## Evidence boundary

This note answers [Find why the agent that marked the dotfiles Git-defaults pull request ready stopped short of merge closeout](https://github.com/nisavid/provingkit/issues/312) on map [Let a repository's autonomy declaration carry PR work through merge closeout](https://github.com/nisavid/provingkit/issues/248). It decides nothing.

- **Base.** `origin/main` = [`cdfdef5d940b165051cc99845ce6cb80c5660006`](https://github.com/nisavid/provingkit/commit/cdfdef5d940b165051cc99845ce6cb80c5660006). The earlier note is [Merge-closeout authority across the Kit and both harnesses](https://github.com/nisavid/provingkit/blob/4e654eeb13e198f0eb5257df7e6aa9095b630eec/docs/superpowers/research/2026-09-27-merge-closeout-authority.md) at `4e654eeb13e198f0eb5257df7e6aa9095b630eec`.
- **Method.** This was read-only work on 2026-10-02 over Ivan's local Claude Code transcripts and Codex rollouts, plus read-only GitHub API calls. There were no model runs, so no executor or grader model was involved. There were no GitHub writes, no pushes, and no configuration edits.
- **Reasoning records.** All 48 thinking blocks in the #360 transcript before the stop carry text. That text may summarize the model's reasoning rather than reproduce it, so "never reasoned about" below means "never in the recorded reasoning".
- **Harness of the incident.** The transcript records Claude Code `2.1.280`, `entrypoint: "claude-desktop"`, model `claude-opus-5-5`, `effort: "high"`, and `permissionMode: "auto"`. The host now runs Claude Code `2.1.287`, which was used only to print its version. No Codex rollout touches #360 before its merge, and the first Codex mention of its branch is at 2026-09-28T06:53Z (see "Which harness and model ran").
- **Plugin text the agent could load.** The installed copies of Mergecraft and Versionkeeping `0.1.0-alpha.3` under `~/.claude/plugins/cache/provingkit/`, all with mtime 2026-09-25 10:39 -0400, before the session:

| File | SHA-256 |
| --- | --- |
| `mergecraft/0.1.0-alpha.3/skills/getting-prs-merged/SKILL.md` | `b10273c0eec59e9f3b2818425754cdf8c85123cf7b720e6aff51aac0b36d8ce8` |
| `mergecraft/0.1.0-alpha.3/skills/getting-prs-ready-for-review/SKILL.md` | `2985d269678d66d67e45a8b6be28882a2d99e6c127b58f17cfd0c8c637e0e2db` |
| `mergecraft/0.1.0-alpha.3/skills/publishing-reviewable-prs/SKILL.md` | `5fcff737b21e8f2f1f0ddc5cab824fbc7bf76f168b794ea9002f52a77f962fc3` |
| `mergecraft/0.1.0-alpha.3/skills/getting-prs-merged/references/caller-continuation.md` | `43133f81f7215bbbd43b5bbc202798a0f6b06e76366e169ac5ec1c9f77cf7f9b` |

Refs read in `nisavid/dotfiles` (local chezmoi clone, fetched):

| Ref | SHA | Note |
| --- | --- | --- |
| `origin/main` at session start | `4f20fce28c3b1d0b898bcb4003c8d56abcfa34fd` | the base the agent branched from |
| worktree `HEAD` at session start | `10bd54941a671525247629c12e7a2b90142a852a` | a local commit not on GitHub; same `AGENTS.md` |
| `AGENTS.md` blob at both | `869cfe432e6b17bc507abfc36dc5d5d9e39a973b` | content SHA-256 `158f1875c90e2a06e037a8e1794d5ff2ea03e44116fe429f8339aea0f6955ebc`; the `CLAUDE.md` the session loaded equals it except for the blob's trailing newline (2,353 bytes against 2,354) |
| [#362](https://github.com/nisavid/dotfiles/pull/362) merge | `689df84bc7c7c874bf50f534f2f6c36f38b19fe6` | adds `## Operating Policy` at 2026-09-26T23:53:23Z |
| #360 merge | `df7c4799647ea75f10061b14b575787da2eeb259` | 2026-09-27T00:26:11Z |

Records are under `~/.local/state/provingkit/merge-closeout-248/research-dotfiles-360-stop/`. `SHA256SUMS` covers every file there and was checked after it was regenerated on 2026-10-08. The research read seven Claude Code transcripts through byte-exact copies, each of which matched its source's digest on 2026-10-02. On 2026-10-08 the copies were reduced to `extracts/`, one file per transcript, which hold every transcript line this note cites, byte for byte. Each extracted line was checked byte-equal to its source line before the copies were deleted.

| Record | SHA-256 |
| --- | --- |
| `SHA256SUMS` | `982eefaf1436b15cb74959095e3439b53f3238f8934776ca4816af9f618d83c2` |
| `extracts/dotfiles-360-session-ab759d6b.extract.txt` | `8a22e646d24688b1e3b0121f86c07d3d0f30d592308c956011b783542eb58cda` |
| `extracts/dispatcher-session-ea7fca83.extract.txt` | `2b373242eefca918a85de0589662aaab5c618ff6ae86e9ce70ae51fbdb96d1f5` |
| `extracts/dotfiles-324-session-a3f7cc7f.extract.txt` | `a783772cd2a87d202ff32dd477a1c7559ed4020ebeefcb33dacb0ad43a35e7d3` |
| `extracts/sibling-codiquary-45-session-97986a01.extract.txt` | `6abaf2636db7f2f32de8bd209f3509ab7c2f68663e6ba6f49b1faec9715c0d46` |
| `extracts/sibling-sacrysty-27-session-08ff6754.extract.txt` | `eb71f8828c05c15be6d6eacd7ee6a4b346b3e77999e0f2c60dba9fbfd1f68a9b` |
| `extracts/sibling-cqmgr-114-session-c9a8a40f.extract.txt` | `2653ca0218f91266f2f6a138f4f48d0a113141b86c8cf0e9794ac976efa35e74` |
| `extracts/sibling-provingkit-235-session-4cd3fb0b.extract.txt` | `6e99d0095c44c9958199d84094695af3a90c037029f9889522b3e2299a32176a` |
| `raw/anchors.tsv`, an earlier table of byte offsets, timestamps, and record uuids for most cited lines, keyed by the former copies' names | `533575f695dc0a8fbe5050c0e747ca6645e6e6f02563beca14e113de66c9b05f` |
| `raw/first-prompt-line9-body.txt` and `raw/spawn-task-prompt-line532.txt` (identical) | `1786a4253408b4d31aa917760b273c1f5293ac9c80126f6e01986af8d8b068cd` |
| `raw/memory-merge-authorization-classifier.md` (mtime 2026-09-25 03:40 -0400) | `c47012d83afcfece5aeb2da9bfc3ae214ec32d3141da9614ef0c76606f79b44d` |

The sources are under `~/.claude/projects/`. The digest column covers the bytes the research read. Five sources are unchanged, so for them it is the whole file's digest on 2026-10-08. The sacrysty and provingkit sources were appended after 2026-10-02, so for them it is the digest of the leading bytes shown. Each extract's header also gives its source's whole-file digest and size on 2026-10-08.

| Transcript (extract name) | Source | SHA-256 of the researched bytes |
| --- | --- | --- |
| #360 session, `S360` (`dotfiles-360-session-ab759d6b`) | `-home-nisavid--claude-worktrees-dotfiles-lucid-hugle-6371e9/ab759d6b-1648-44ae-881c-96da32e959fb.jsonl` | `b0e3a3c8186cf464a8f96ae90da39f5516681e32c0578bf66239b3829ba955f5` |
| dispatcher, `D` (`dispatcher-session-ea7fca83`) | `-home-nisavid--claude-worktrees-agents-setup-matt-pocock-skills-07d078/ea7fca83-fa19-4eb4-94ae-e983a7081f39.jsonl` | `f057b6da08e68fa5aede127ff1df29ba1b04b4f13b2e77ffe8a86118155a474e` |
| #324 session, `S324` (`dotfiles-324-session-a3f7cc7f`) | `-home-nisavid--claude-worktrees-chezmoi-exciting-margulis-9ba155/a3f7cc7f-41b4-4947-aa7b-800457bb8019.jsonl` | `c13a1512469cb4b57baea02402ff6b82093f20fe51c1f80bd93eb05f99430cae` |
| codiquary#45 sibling (`sibling-codiquary-45-session-97986a01`) | `-home-nisavid-src-nisavid-codiquary/97986a01-cb90-4862-9d05-ac08ddfd91c1.jsonl` | `822ed3db6001d28956a5d2c1483f316fb2043509a3d92b6d25e075c8f1bf303e` |
| sacrysty#27 sibling (`sibling-sacrysty-27-session-08ff6754`) | `-home-nisavid-src-nisavid-sacrysty/08ff6754-0fd2-454d-a009-632d35619d17.jsonl` | `84c92cd02364e7eb5d20b4b1f856943ef37cda4530d6c2f870be05d68cc1116d` (first 2,134,536 bytes) |
| cqmgr#114 sibling (`sibling-cqmgr-114-session-c9a8a40f`) | `-home-nisavid--claude-worktrees-cqmgr-intelligent-matsumoto-4d1109/c9a8a40f-6775-4265-8d7c-12a0f023b279.jsonl` | `8ddb87e34c598cb2eeac5ba8d819ee76c2c3a4563b679ecca7fe72aad8edc493` |
| provingkit#235 sibling (`sibling-provingkit-235-session-4cd3fb0b`) | `-home-nisavid--claude-worktrees-provingkit-trusting-shaw-ecfc2f/4cd3fb0b-aabe-4afb-bfea-7111b9d7edbb.jsonl` | `46c834ffa5c22851619534b71e0d1baf887bad550cc1d692c3b6f51c43716ac5` (first 1,773,173 bytes) |

**Citation form.** `S360:N` means line N of the #360 session transcript, `D:N` line N of the dispatcher transcript, and `S324:N` line N of the #324 transcript. In the sibling table, `:N` means line N of that row's sibling transcript. Line numbers are 1-based JSONL lines of the sources above. Every cited line is in `extracts/<name>.extract.txt` for its transcript's extract name, after a label that gives its source path, line number, byte offset, and source digest. Claims that cite a range, a count, an absence, or only a timestamp cover lines outside the extracts and are checkable against the sources.

**Retention.** Claude Code keeps Claude Desktop transcripts at any age unless `desktopSessionCleanupPeriodDays` is set; other transcripts age out under `cleanupPeriodDays`, which defaults to 30 days ([`.claude` directory reference](https://code.claude.com/docs/en/claude-directory), via Context7 `/websites/code_claude`, fetched 2026-10-02). `~/.claude/settings.json` sets neither key, and all seven sources are Claude Desktop transcripts (`"entrypoint":"claude-desktop"`). Some are still being appended, so a source's whole-file digest can change. The digest of its researched bytes stays checkable as long as the file only grows.

## Summary

- **Which text it followed.** It followed the task text's narrower clause. The opening prompt (`S360:9`) opens with "Resolve https://github.com/nisavid/dotfiles/issues/359 end to end" and closes with "take the change through a PR that closes #359 (use /mergecraft:getting-prs-merged if the operator asks for merge)". The agent's reasoning before its CI wait (`S360:602`) restates the closing clause: "the user asked to get the change through a PR, and "ready for review" fits that without merging unless explicitly requested." Its stopping turn (`S360:651`) says "I haven't merged it because you didn't ask for that." No recorded reasoning or reply before the stop mentions "end to end".
- **The three named texts were absent.**
  - **Operating Policy.** The loaded `CLAUDE.md` had no `## Operating Policy`. dotfiles adopted it in #362, 2 h 14 min after the stop.
  - **Readiness skill.** The agent never invoked or opened the readiness skill. It marked the PR ready through the publisher's `update_reviewable_pr.py ready`. In its skill listing, `mergecraft:getting-prs-ready-for-review` appears as a bare name with no description, so the "keep readiness separate from … closeout outcomes" wording never reached it.
  - **`caller-continuation.md`.** The agent first read it at `S360:699`, 29 minutes after the stop, while answering Ivan's complaint.
- **`getting-prs-merged`.** The agent never considered the skill as a skill. The skill's name appeared in the prompt's condition, and its listing description began "Use when the operator explicitly requests a GitHub branch or PR merge outcome". Before the stop there was no Skill call for it, no read of its files, and no mention of it in any reasoning or reply. Merge appears as an action only at `S360:602` and `S360:651`, each time as excluded by the request's condition.
- **Classification: scope stop.** It was not a trigger miss, because the skill was never weighed against the request. It was not a classifier denial: no merge was attempted, and no tool call before the stop failed. It was not unaided model inference, because the boundary was in the prompt, though the agent chose the conditional clause over the opening "end to end". That boundary was the dispatching session's own wording (`D:532`): Ivan had asked that session to kick off the fix threads (`D:390`) but gave no merge scope for them.
- **Harness and model.** Claude Code 2.1.280 inside Claude Desktop, with Claude Opus 5.5 at high effort in auto mode. The run did not use Sonnet 5 or a replaced system prompt, so the classifier study's 14 of 55 Sonnet 5 stops are a different population.
- **Siblings.** The four other fix threads from the same dispatch each opened "Resolve \<issue URL>" and ended "take the change through a PR that closes #N", with no merge condition and no "end to end". None of them continued into merge on that prompt: one asked, and three reported and stopped. In those four runs, a stop happened without the condition.
- **dotfiles#324.** The record confirms the recorded cause. Ivan approved posting the PR, the agent opened it as a draft and asked to be told when to mark it ready, and Ivan corrected it. That is the case [Make Mergecraft's PR readiness and body style depend on repository ownership](https://github.com/nisavid/provingkit/issues/195) records in its decision on readiness in owned repositories.

## Which harness and model ran

- **Claude Code Desktop.** `S360:3` onward record `"version":"2.1.280"`, `"entrypoint":"claude-desktop"`, and `cwd` `/home/nisavid/.claude/worktrees/dotfiles/lucid-hugle-6371e9`. `S360:11` is the model attachment: `"modelId":"claude-opus-5-5"`, "Opus 5.5". All 140 assistant records up to the stop carry `"effort":"high"` and `"perTurnEffort":"high"`. `S360:9` carries `"permissionMode":"auto"`, `"origin":{"kind":"human"}`, and `"promptSource":"sdk"`. `S360:16` is the `auto_mode` attachment.
- **The GitHub ready event is this session's.** The session called the publisher's ready helper at 21:38:40.747Z (`S360:639`). It got back `"status": "verified"`, `"is_draft": false`, and receipt `f8d02e22-0f5b-460e-87ce-dae808275c7f` (`S360:642`). GitHub's `ready_for_review` event on #360 is at 21:38:44Z (issue timeline API).
- **No other transcript touched #360 before then.** Among Claude transcripts, the only one that names the head branch `nisavid/move-personal-git-policy-to-user-rules` before 22:01Z is this session; it first names it at 21:01:57Z. All Codex rollouts that name the branch (16 when this note was researched, 18 at its verification, because more were appended) do so first on 2026-09-28 or later, after the merge. One example is the coordination rollout `rollout-2026-09-26T07-15-18-01a0dd6d-….jsonl` (originator `claude_dispatch`), whose first mention is 2026-09-28T06:53Z.

## What the agent had in context at the stop

| Candidate text | In context before the stop? | Evidence |
| --- | --- | --- |
| Opening prompt, which opens "Resolve … end to end" and closes with the merge condition | **Yes**, as the first user turn | `S360:9`; body bytes identical to the dispatcher's `spawn_task` prompt (`D:532`), SHA-256 `1786a425…` |
| `getting-prs-merged` listing description | Yes, one line in the skill listing | `S360:15` (`skill_listing`, 633 skills): "Use when the operator explicitly requests a GitHub branch or PR merge outcome. … Do not use for description, review, status, check, comment, draft, or publication work without merge." |
| Readiness skill's "keep readiness separate from … closeout outcomes" | **No** | The listing's line for it is the bare name `- mergecraft:getting-prs-ready-for-review` (`S360:15`, listing line 127). No Skill call to it, and no read of its files, before `S360:651`. |
| Operating Policy escalation rule | **No** | The loaded `CLAUDE.md` (`S360:26`, `type: "Project"`, 2,353 bytes) equals `AGENTS.md` blob `869cfe43` (2,354 bytes) at `4f20fce` and `10bd549` except for the blob's trailing newline. That blob has no `## Operating Policy` and never says merge or escalate. "Operating Policy" occurs 0 times in `S360:1-650`. #362 added the section at `689df84` (23:53:23Z). |
| `caller-continuation.md` | **No** | First read at `S360:699` (22:08:23Z), after Ivan's reply at `S360:658`. |
| `getting-prs-merged/SKILL.md` body | **No** | First loaded at `S360:784` (22:20:59Z), after Ivan's "Yes and yes" at `S360:756`. |
| Publisher skill body | Yes | Loaded at `S360:341` from the alpha.3 cache. It equals the installed `SKILL.md` body except for one trailing blank line. Line 32 sends "merge-only work" to "their own owners". Lines 262-263 say "Comments, feedback, CI, merge, and Git/ref publication retain distinct owners". |
| Memory index line on merges | Yes, as one index line | `S360:26` (`AutoMem`, `-home-nisavid--local-share-chezmoi/memory/MEMORY.md`): "Claude merges approved PRs; if the classifier blocks one, ask Ivan per PR via AskUserQuestion". The file itself was not opened before the stop. It records Ivan's 2026-09-25 grant for "a set of merges" he approves. At the stop, #360 had no approving review (the only review was Copilot's `COMMENTED` at 21:38:50Z). |
| Claude Desktop system prompt | Yes | `S360:30` (`prompt_snapshot`): "After opening a PR, use the ccd_pr tools to read CI … never enable auto-merge unless the user asked." This covers auto-merge only. |

User-level rules loaded at `S360:26` were `~/.claude/rules/context7.md` and `~/.claude/rules/ticket-tracker-preflight.md`. Neither mentions merge. The `git-defaults` rule is what #360 itself added.

## The stopping turn and the last skill invocation before it

- **Last skill invocations.** At 21:07:31.733Z the agent called `Skill` with `{"skill":"mergecraft:publishing-reviewable-prs"}` (`S360:336`), and the body loaded at `S360:341`. Five seconds later one assistant turn issued the session's last two Skill calls before the stop: `{"skill":"mergecraft:writing-reviewable-pr-descriptions"}` at 21:07:36.793Z (`S360:351`) and `{"skill":"mergecraft:maintaining-issue-pr-relations"}` at 21:07:36.798Z (`S360:352`). The ready transition later ran under the publisher's "Mark Existing Draft Ready" section, with no new Skill call.
- **The decision to stop at ready.** It was made 27 minutes before the stop, at 21:11:12.568Z (`S360:602`, thinking): "CI takes about 13 minutes normally, so I'll wait for it before marking the PR ready — the user asked to get the change through a PR, and "ready for review" fits that without merging unless explicitly requested." The visible reply (`S360:623`) said: "I'll mark #360 ready once CI finishes. The background watcher will wake me when it's done."
- **The ready call.** At 21:38:40.747Z (`S360:639`) the agent ran `update_reviewable_pr.py ready`. The verified receipt came back at 21:38:45.793Z (`S360:642`).
- **The stopping turn.** It is at 21:39:00.519Z (`S360:651`, byte offset 1988534): "I've opened [#360](https://github.com/nisavid/dotfiles/pull/360) and marked it ready for review. It closes #359 when merged, and all 19 CI checks passed. I haven't merged it because you didn't ask for that." The thinking just before it (`S360:650`) covers only the receipt check and what to report. No question was asked; the turn ended.
- **The Stop hooks.** `S360:655` (`stop_hook_summary`, 21:39:02.482Z) records 10 Stop hooks, including `jev-axi hook stop`, with `"preventedContinuation": false`.
- **Afterwards.** Ivan replied at 22:07:34Z (`S360:658`), quoting the stop line: "In a repo that declares itself (in `AGENTS.md`) to have high-agentic-autonomy repo-ops policy, I fully expect /mergecraft:getting-prs-merged to follow automatically". dotfiles declared no such policy at the time, as shown above.

## Classification

**Scope stop.** The task text opened "Resolve https://github.com/nisavid/dotfiles/issues/359 end to end", but its closing clause bounded the outcome at "a PR that closes #359" and put merge behind "if the operator asks for merge". The agent took that conditional clause as the task's bound and carried it unchanged from `S360:9` to `S360:602` to `S360:651`. Its recorded reasoning never weighs "end to end", which could have been read to include merge. The ticket's other classes do not fit:

- **Trigger miss.** It requires the skill to be weighed and passed over. Here the agent read the request's conditional clause as excluding merge, and the skill was never weighed. The skill's trigger ("the operator explicitly requests … merge") and the prompt's condition agree, so changing the trigger alone would not have changed this run.
- **Classifier denial.** No tool result before the stop has `is_error: true`, and no merge command was issued. The classifier did deny merges later in this session, after Ivan's go-ahead. At 22:57:13Z it denied #362's merge with reason `[Merge Without Review]`. At 00:28:21Z, after #360 had merged at 00:26:11Z, it denied a follow-up read with the same reason. Both are outside this question.
- **Unaided model inference.** The boundary was written in the prompt. The agent's own part was to follow that clause over the broader opening "end to end". The boundary's wording comes from one step upstream, in the dispatching session (next section).

## Where the condition came from

- **Who wrote it.** The "Matt Pocock skills setup" session (`ea7fca83`, Claude Opus 5.5, Claude Code 2.1.280) wrote the #360 session's first prompt. It called `mcp__ccd_session__spawn_task` at 20:56:01.075Z (`D:532`) with title "Move personal Git policy out of dotfiles AGENTS.md". The prompt bytes equal `S360:9`'s body. The app later told that session "The user started your suggested background task task_c34e8944 ("Move personal Git policy out of dotfiles AGENTS.md")" (`D:901`).
- **What Ivan had asked that session.** His only prompt was `/setup-matt-pocock-skills` with arguments ", then /mergecraft:getting-prs-merged" (`D:9`, 20:20:29Z, `origin.kind: "human"`). Eight question answers precede `D:532`. The last, at `D:390` (20:53:10Z), asked the session to "kick off a thread to fix it" for each polluted repository and gave no merge scope. The "if the operator asks for merge" clause was the dispatcher's own wording.
- **What the dispatcher had loaded.** It had read the `getting-prs-merged` skill body at `D:268` (20:43:48Z) for its own closeout. Its reasoning records at `D:417-530` contain no text about the fix threads' scope.
- **Where the five prompts differ.** It spawned five fix threads at `D:532`, 537, 542, 547, and 552. Each opens with "Resolve \<issue URL>" and ends with "take the change through a PR that closes #N". The dotfiles prompt alone opens "end to end", and it alone adds the merge condition.
- **Recorded origin.** The executing session records that prompt as a human turn (`origin.kind: "human"`, `promptSource: "sdk"`), although an agent wrote it.

## The four sibling threads

These are uncontrolled observations, not a trial: one run each, in different repositories, with prompts that also differ from the dotfiles prompt in their opening clause, all started within seven seconds of 21:00:35Z. All ran Claude Opus 5.5 in Claude Code 2.1.280.

| Pull request | Operating Policy at base | What the agent did after opening | What carried it to merge |
| --- | --- | --- | --- |
| [nisavid/dotfiles#360](https://github.com/nisavid/dotfiles/pull/360) (condition in prompt) | absent | marked ready (`S360:639`), then reported and stopped (`S360:651`) | Ivan's "Yes" at 22:20:22Z (`S360:756`) |
| [nisavid/codiquary#45](https://github.com/nisavid/codiquary/pull/45) | absent (`AGENTS.md` at base `50c4762`) | opened non-draft; reported "Merging it will close the issue." and stopped (`sibling-codiquary…:122`) | Ivan's own `/mergecraft:getting-prs-merged` at 22:21:54Z (`:129`) |
| [nisavid/sacrysty#27](https://github.com/nisavid/sacrysty/pull/27) | absent (base `c4c0c2c`) | opened non-draft; reported "The branch can't merge until the required checks pass and it gets a review." and stopped (`sibling-sacrysty…:149`) | a cross-session relay on 2026-09-29 (`:208`), on which it invoked `getting-prs-merged` (`:242`) |
| [nisavid/cqmgr#114](https://github.com/nisavid/cqmgr/pull/114) | present (base `22b3f34`) | marked ready (`:399`); reported "It's marked ready for review but not merged; it needs a review before it can merge." and stopped (`:424`) | Ivan's own `/mergecraft:getting-prs-merged` at 22:21:41Z (`:431`) |
| [nisavid/provingkit#235](https://github.com/nisavid/provingkit/pull/235) | present (base `7ce7f56`) | reasoned that "take the change through a PR that closes #234" "is ambiguous about whether it includes merging" (`:380`); marked ready (`:536`); asked "Should I squash-merge it now?" (`:569`) | Ivan answered "Leave #235 open" (`:571`); merged later |

So none of the five continued into merge on its opening prompt (0 of 5). With the Operating Policy present (cqmgr, provingkit), one agent stopped and one asked. The provingkit agent's reasoning at `:568` reads the Operating Policy as making merge "an explicit actuation step", which matches the earlier note's Codex finding that the policy carried 0 of 6 runs to a merge.

## dotfiles#324

**Confirmed.** In `S324` (Claude Code 2.1.280, Claude Opus 5.5, Claude Desktop, plugin cache `mergecraft/1.0.0`), the steps were:

- At 21:09:13Z (`S324:1324`) the agent sent Ivan four drafted texts, the PR title and body among them, and asked him to choose to post all, post only some, or edit.
- Ivan answered "LGTM, proceed" at 21:15:16Z (`S324:1337`).
- The agent created [#324](https://github.com/nisavid/dotfiles/pull/324) as a draft (`S324:1450`) and ended its turn with "Say the word when you want it marked ready for review." (`S324:1535`).
- Ivan replied at 21:21:01Z: "Why are you asking for this? You're supposed to drive it autonomously. Does the repo's `AGENTS.md` not instruct that?" (`S324:1542`).
- The agent then reasoned "My instructions say to treat completion steps like this as routine, not something to check in on" (`S324:1570`) and invoked `mergecraft:getting-prs-ready-for-review` (`S324:1571`). GitHub's ready event is at 22:37:05Z.

`nisavid/dotfiles` is Ivan's own repository. This is the case that the decision on readiness in owned repositories records: in an owned repository, authorization to open a pull request covers driving it to ready. [Make Mergecraft's PR readiness and body style depend on repository ownership](https://github.com/nisavid/provingkit/issues/195) records that decision and owns the fix.

## Corrections to the earlier note

- **Architecture read, "The dotfiles#360 trace."** The read said "Readiness returned no handoff. `caller-continuation.md` continues only already-authorized work. The Operating Policy says to escalate when stakeholder policy is unknown." None of those texts was in the agent's context at the stop (see the context table). The scope gap the read named is the right gap, but in this incident it was written into the delegated prompt rather than left implicit.
- **"The main model often stops at readiness before the classifier is involved."** This finding, eighth in the earlier note's section on Claude Code's auto-mode classifier, says the Sonnet 5 rig stop "is the nisavid/dotfiles#360 stop". The incident ran Claude Opus 5.5 at high effort under Claude Desktop's own system prompt, with an explicit merge condition in the first prompt. The two stops look alike, but they are different populations, as #312's body anticipated.

## What this means for the tickets this one unblocks

- **[Choose the skill-side design for the continuation into merge closeout](https://github.com/nisavid/provingkit/issues/326)** (blocked by this ticket).
  - The incident is a scope stop. A reframed `getting-prs-merged` trigger fixes only whether the skill accepts an invocation, and here nothing ever tried to invoke it.
  - A declaration-based design would not have changed this run either. dotfiles declared nothing at the time, and the map keeps today's behavior where a repository says nothing.
  - For a run like this one in a declaring repository, a design would have to put merge into the caller's outcome set and say how the declaration meets task text that is silent on merge or names it only conditionally, including text a dispatching agent wrote. [Decide whether repository instructions may grant mutation authority, what a merge-closeout grant covers, and how it ranks](https://github.com/nisavid/provingkit/issues/308) decides which of the two wins.
  - The scope can be set by text the Kit never sees. A delegating agent wrote "if the operator asks for merge" into a prompt the executing agent saw as a human turn. In the four uncontrolled sibling runs, prompts with no merge condition also stopped short of merge. The phrasing that dispatching agents use for delegated scope is a second carrier of the same gap.
  - Since the readiness skill was never invoked, editing its description would not have reached this agent either.
- **[Approve or decline a hook component, and decide whether this effort wants a Jev component](https://github.com/nisavid/provingkit/issues/328).**
  - #360 was neither "forgot to continue" nor "asked instead of continuing": the agent declined on purpose, stated why, and asked nothing. #324 was "asked instead of continuing".
  - A detection hook would have had its markers: a `Bash` call to `update_reviewable_pr.py ready` with a verified receipt (`S360:639`, `S360:642`), no `getting-prs-merged` Skill call, and a `Stop` event with 10 hooks already firing (`S360:655`).
  - A hook gated on a repository declaration would have stayed silent, because dotfiles declared nothing at 21:39Z, and even the Operating Policy adopted later names no merge.
  - An ungated nudge would have pushed against an explicit merge condition in a turn the harness records as human. That is the "in-session operator restriction the hook cannot see" risk the earlier note flagged, now observed.
  - A report-only hook would have told Ivan what the stopping turn already said.
- **[Set this effort's case list, trial counts, harnesses, and grader panels](https://github.com/nisavid/provingkit/issues/317)**, for the journey-level incident case the map lists under "Not yet specified".
  - A faithful #360 case is Claude Opus 5.5 at high effort, not Sonnet 5. Its first turn is the delegated prompt verbatim, including the condition, in a repository whose `AGENTS.md` lacks the Operating Policy.
  - A second case without the condition, matching the four siblings, separates the delegated condition from the plain "through a PR" wording.

## Open questions

- **Precedence over a delegated condition.** Should a repository declaration that grants merge closeout override an explicit "if the operator asks for merge" in a first turn that another agent wrote? This belongs to [Decide whether repository instructions may grant mutation authority, what a merge-closeout grant covers, and how it ranks](https://github.com/nisavid/provingkit/issues/308). The incident shows the case is real, and the harness records such a turn as human.
- **Wording that carries merge.** Would "take the change through merge closeout" in the delegated prompt have carried any of these agents into `getting-prs-merged`? No run tested it.
- **Who governs dispatch wording.** Should `rolecasting:delegating-cross-agent-work` or the caller-level rule govern how a dispatching agent states merge scope for spawned work? The dispatcher's own task included merge, and it narrowed its fix threads without asking.
- **Listing truncation.** Does the skill-listing budget routinely drop the readiness skill's description? Here 633 skills were listed and that entry carried a bare name. If so, any fix that relies on the readiness or publisher description text may not reach the agent at all.
- **The memory grant.** Would the agent have merged had #360 been approved and had it opened the memory file? The index line's "Claude merges approved PRs" was in context, but the PR had no approval at the stop, and the grant it records is scoped to a set of merges Ivan approved on 2026-09-25.
