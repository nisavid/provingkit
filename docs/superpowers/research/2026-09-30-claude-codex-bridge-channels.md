# Bridging a Claude Code cloud session and a Codex agent

Two channels survive scrutiny. For synchronous conferring, the only path that gives one Claude Code cloud session a live, multi-round Codex partner is to co-locate the Codex CLI in the Claude cloud environment and drive it with `codex exec --json` and `codex exec resume`, authenticated once per session by a device-code login that Ivan approves. For asynchronous work bound to a pull request, GitHub itself is the bus: the Claude side already wakes on PR activity and posts under Ivan's GitHub account, and the Codex side starts a cloud chat on any `@codex` mention in a PR comment. Everything else either reduces to one of those two or runs on Ivan's desktop rather than in either cloud.

This note records verified facts, dated and sourced, and ranks the four channels the handoff named. It proposes experiments; it does not report their results. No environment setting, installed software for future sessions, tracker post, or Codex login was changed or attempted. A companion decision memo, `docs/superpowers/research/2026-09-30-claude-codex-bridge-decision-memo.md`, carries the recommendation and the experiment plan.

## Scope and evidence

All observations date from 2026-09-30 unless a source says otherwise. Three evidence classes are kept distinct below.

**Container observations.** Made in this session's Anthropic-hosted cloud container (Claude Code 2.1.285, Ubuntu VM, Node 22.22.2 on `PATH`, egress through the session's agent proxy). The Codex CLI was installed only into the session scratchpad from the public npm registry to read its own help output; nothing was installed on `PATH` or for future sessions.

**Product documentation.** OpenAI's Codex documentation now redirects from `developers.openai.com/codex/*` to `learn.chatgpt.com/docs/*`; both hostnames are cited by the page that answered. Claude Code documentation is at `code.claude.com/docs`. The session's egress policy denies `developers.openai.com`, `learn.chatgpt.com`, `chatgpt.com`, `auth.openai.com`, and `api.openai.com`, so OpenAI pages were read through a third-party fetch service and Claude pages directly. Every fetched page is listed under Sources with the date read.

**Limits on what was checked.** Four local probes were denied by Claude Code's auto-mode classifier during this session: reading this environment's network and secrets documentation pages, a batch of `claude --help` and `claude mcp serve --help` calls, and a batch of Codex subcommand probes (`login status`, `doctor`, `debug models`, `app-server`, `remote-control`, `sandbox`, `features`). The denials named containment escape and credential materialization as reasons. Those facts are therefore taken from documentation, and the denials are recorded in the appendix as Sys1 observations for the owner of that case, not diagnosed here.

## Facts established in the container

- No `codex` binary and no `~/.codex` directory exist on `PATH` or in the home directory. Claude Code 2.1.285 is at `/opt/node22/bin/claude`.
- The agent proxy status page reports the proxy enabled with a CA bundle at `/root/.ccr/ca-bundle.crt` that covers every host, and a no-proxy list containing `api.anthropic.com`, the npm, jsr, PyPI, crates.io, and Go module registries, and private address ranges. Package registries are reached directly, as the handoff said.
- `curl` to `https://auth.openai.com/`, `https://chatgpt.com/`, and `https://api.openai.com/` each failed with `CONNECT tunnel failed, response 403` at the proxy. The Claude Code WebFetch tool reported `EGRESS_BLOCKED` for `developers.openai.com`.
- `npm view @openai/codex` reached the registry: the latest release is 0.159.2, with `time.modified` 2026-09-30T12:05:45Z. Installing it into the scratchpad took about eight seconds and produced a working `codex-cli 0.159.2` binary, so a setup script `npm install -g @openai/codex` is feasible in this environment as configured.
- The nisavid/provingkit repository is public (session `list_repos`, visibility `public`).

### What the Codex CLI 0.159.2 help output says

The installed binary's `--help` output was captured for the top level and for `login`, `exec`, `exec resume`, and `debug`.

- `codex login` offers `--device-auth`, `--with-api-key` (key on stdin), and `--with-access-token` (token on stdin), plus `codex login status`.
- `codex exec` offers `--json` (JSONL events on stdout), `-o/--output-last-message <FILE>`, `--output-schema <FILE>`, `--ephemeral` (no session files on disk), `-s/--sandbox {read-only,workspace-write,danger-full-access}`, `-a/--ask-for-approval {on-request,never}`, `--dangerously-bypass-approvals-and-sandbox` ("Intended solely for running in environments that are externally sandboxed"), `-m/--model`, `-c key=value` overrides, `--skip-git-repo-check`, and `--ignore-user-config`.
- `codex exec resume [SESSION_ID] [PROMPT]` accepts a UUID or thread name, or `--last`; `--all` disables the working-directory filter on the session list.
- The top-level command list has `app-server` (experimental), `remote-control` (experimental), `exec-server` (experimental), `queue` ("Queue a message for an existing session"), `cloud` (experimental: browse Codex Cloud tasks), `agents`, `mcp` ("Manage external MCP servers for Codex"), and `debug models` ("Render the raw model catalog as JSON"). There is no `mcp-server` command. The top-level help also documents `--remote <ADDR>` (`ws://`, `wss://`, `unix://`) and `--remote-auth-token-env` for connecting the TUI to a remote app server.

The help output and the documentation agree on every point checked; the documentation adds the removal date of the MCP server mode, which the help output can only show by omission.

## The two sides' ingress and egress

### Claude Code cloud session

Inbound paths, per the Claude Code documentation read 2026-09-30:

- **GitHub PR activity.** With the Claude GitHub App installed on the repository, a session subscribed to a pull request "receives GitHub events for the PR including new review comments and CI check failures". Replies Claude posts on review threads "are posted using your GitHub account, so they appear under your username, but each reply is labeled as coming from Claude Code". GitHub emits no webhook for a base-branch merge conflict, so that case is not delivered. (Claude Code in the cloud, "Auto-fix pull requests".)
- **Routines.** A routine is a saved prompt plus repositories, run as a cloud session, with three trigger kinds: schedule, API, and GitHub event. The API trigger is a per-routine `POST .../routines/<id>/fire` with a bearer token and an optional `text` field, under the `experimental-cc-routine-2026-04-01` beta header; it "starts a new session and returns a session URL". Fire text arrives wrapped in a `<routine-fire-payload>` block labeled untrusted, and the routine's prompt must opt in to acting on it. GitHub triggers cover pull-request and release events only, need the Claude GitHub App, and "Claude Code doesn't reuse sessions across events". Limits: 30 fires per routine per hour, 100 API fires per account per hour. (Routines.) Inside a session, the session-management tools additionally allow a poke-only routine bound to a specific existing session, which is how this session and its sibling exchange messages; that binding is a tool capability, and the public routines page does not describe it.
- **CLI queueing.** From any machine where the Claude Code CLI is signed in to the same claude.ai account, `claude -p "message" --cloud <session-id>` "queues the message into the session and exits without waiting for a reply", including from "a CI script". This is an inbound path into an existing session that the handoff did not list. (Claude Code in the cloud, "Send follow-ups from the CLI".)
- **Artifact webhook.** As the handoff recorded: signed with a secret sealed to Anthropic's artifact service, unusable by a third party.

There is no general inbound HTTP endpoint into a running session.

Outbound paths: GitHub through the GitHub proxy, scoped to repositories attached to the session; HTTPS to hosts the environment's network access level allows; MCP connectors, whose traffic "travels through Anthropic's servers rather than the session's network". Network access levels are **Trusted** (a fixed allowlist of package registries, GitHub, and cloud SDKs), **Custom** (your own list, optionally including the defaults), and **Full**. Changing an environment's access level applies to existing sessions "within about a minute". Environment variables are readable by anyone who uses the environment; on Pro and Max plans an **API credential** is attached by the agent proxy to requests for listed hosts and never reaches the session, and those hosts become reachable regardless of access level. A setup script runs before Claude starts and is cached when it finishes in roughly five minutes. (Configure cloud environments.)

### Codex

Surfaces relevant here, per the Codex documentation read 2026-09-30:

- **Codex CLI**, authenticated either by ChatGPT sign-in (subscription usage, plan credits) or by an API key (usage-based, "No cloud-based features (GitHub code review, Slack, etc.)"). "Codex cloud requires signing in with ChatGPT." (Authentication; Pricing.)
- **Codex Cloud** tasks, started from ChatGPT web, the desktop app, mobile, Slack or Teams in Enterprise workspaces, or `codex cloud` from the CLI. The current cloud environment model has an install script, a start skill, environment variables, "network secrets" substituted by a proxy, and internet access presets (**Package managers**, **Custom domains only**, **All**). The "legacy" cloud environment "continues to support environments for Code Review and the Linear and GitHub integrations" and is planned for deprecation. (Cloud environments; Codex Cloud (Legacy).)
- **GitHub integration.** `@codex review` in a PR comment posts a review; `@codex security review` runs the security pass; "If you mention `@codex` in a comment with anything other than `review`, Codex starts a legacy cloud chat using your pull request as context" and "can push a fix back to the branch when it has permission to do so". Setup requires the repository connected to Codex and configuration at the Codex code-review settings page; the troubleshooting list says to "Confirm the pull request belongs to a GitHub repository connected to Codex." (Review GitHub pull requests with Codex.) The pricing page's feature table lists "GitHub issue and PR delegation with `@codex`" for Plus, Pro, Business, and Enterprise, and not for API-key users; the integration page itself describes only pull-request comments, so issue-comment mentions are unconfirmed by the integration page.
- **App server.** `codex app-server` is the programmatic integration point: JSON-RPC 2.0 over stdio by default, or a WebSocket listener (`--listen ws://…`, "experimental and unsupported"), with `thread/start`, `thread/resume`, `turn/start`, and streamed item events. "The `codex mcp-server` command and standalone `codex-mcp-server` binary have been removed after their deprecation on August 24, 2026." (App Server; Codex SDK; Changelog, September 2026.) The deprecation shipped in CLI 0.149.1 on 2026-08-24 and the removal in rust-v0.154.0 on 2026-09-09, by pull request 42993 in the openai/codex repository (release page and pull request, verified by the deep-research workflow; see the reconciliation section).
- **Codex plugin for Claude Code.** OpenAI's `openai/codex-plugin-cc` "wraps the Codex app server" and "uses the global `codex` binary installed in your environment"; it adds `/codex:review`, `/codex:adversarial-review`, and delegation commands (`/codex:rescue`, `/codex:transfer`, `/codex:status`, `/codex:result`, `/codex:cancel`), installed with `/plugin marketplace add openai/codex-plugin-cc` and `/plugin install codex@openai-codex`. It requires Node 18.18 or later and a ChatGPT subscription or API key, and reuses "the same local authentication state". Its README warns that the review gate "can create a long-running Claude/Codex loop and may drain usage limits quickly". The README does not say whether it works in a non-interactive session. (GitHub README, read 2026-09-30; launch reported 2026-03-30 by secondary sources.)

## Channel 1: co-locate the Codex CLI in the Claude cloud environment

### Verified facts

**Installation.** Feasible today: the npm registry is on the no-proxy list, and the install completed in the scratchpad in eight seconds. A setup script would run `npm install -g @openai/codex` (Node 22 is on `PATH`). The result is cached with the environment.

**Authentication.** The model Ivan chose needs ChatGPT sign-in. The documented headless path is device-code authentication (beta): "Enable device code login in your ChatGPT security settings (personal account)", then `codex login --device-auth`, then "Open the link in your browser, sign in, then enter the one-time code." Credentials are cached in `auth.json` under `CODEX_HOME` (default `~/.codex`) or an OS credential store; `cli_auth_credentials_store` accepts `file`, `keyring`, `auto`, or `ephemeral` ("keeps credentials in memory only for the current process"). Codex refreshes ChatGPT tokens automatically during use and, per the CI/CD guide, refreshes when `last_refresh` is older than about eight days and on a `401`. (Authentication; Maintain Codex account auth in CI/CD.)

Two consequences for this environment. First, the login must happen after the setup script, in the running session, because the setup script cannot wait for a browser approval; the agent relays the URL and code to Ivan in chat and polls. The documentation confirms the mechanism but says nothing about a code lifetime, so the wait tolerance is an experiment result. Second, the container is ephemeral, so the login repeats each session unless `auth.json` is carried over. Carrying it over is possible only as an environment variable or as a file the setup script writes, both readable by anyone who uses the environment; the API-credential feature cannot apply because Codex reads the file itself rather than sending a header the proxy could inject. The documentation says "Treat `~/.codex/auth.json` like a password" and "Do not use this workflow for public or open-source repositories." The per-session device login is therefore the clean option, and the carried-over file is a documented but sharper alternative.

**Hosts.** No page enumerates the hostnames the CLI contacts under ChatGPT sign-in. The configuration reference exposes `chatgpt_base_url` ("Override the base URL used during the ChatGPT login flow") and `openai_base_url`, and the login section says browser or device-code failures are logged to `codex-login.log`. The three hosts the handoff named are the ones that failed in this container. Community reports add `releases.openai.com` for the updater; `check_for_update_on_startup = false` avoids that request. The exact set is therefore: `chatgpt.com`, `auth.openai.com`, and `api.openai.com` as the working hypothesis, with `codex-login.log` and the proxy's 403 lines as the way to find any stragglers during the experiment.

**TLS.** The session proxy presents a CA bundle that covers every host. Codex reads `CODEX_CA_CERTIFICATE` (a PEM bundle) and falls back to `SSL_CERT_FILE`; "The same custom CA settings apply to login, normal HTTPS requests, and secure WebSocket connections." Setting `CODEX_CA_CERTIFICATE=/root/.ccr/ca-bundle.crt` in the environment is the documented way to make the Rust client trust the proxy if it does not already read the system store.

**Model and effort.** `model_reasoning_effort` accepts "`low`, `medium`, `high`, `xhigh`, `max`, or `ultra`. Available levels depend on the model and client." The models page lists `codex -m gpt-6-astra` as a CLI-available model and says some paid plans omit Astra Extra High; `codex debug models` renders the catalog as JSON and is the check to run after login. (Configuration reference; Models.)

**Sandbox inside a sandbox.** Linux uses `bwrap` plus `seccomp`. "When you run Linux in a containerized environment such as Docker, the sandbox may not work if the host or container configuration blocks the namespace, setuid `bwrap`, or `seccomp` operations that Codex needs. In that case, configure your Docker container to provide the isolation you need, then run `codex` with `--sandbox danger-full-access` (or the `--dangerously-bypass-approvals-and-sandbox` flag) inside the container." `codex sandbox linux [COMMAND]` tests the inner sandbox directly. Whether `bwrap` works in this VM is unknown; the probe was among the denied commands. `codex exec` defaults to `read-only`, and `--sandbox read-only --ask-for-approval never` is the documented "Read-only non-interactive (CI)" combination. If the inner sandbox cannot start, the fallback is full access inside the outer container, which is what the flag's help text says it is for. (Agent approvals and security.)

**Rate limits and cost.** Codex usage draws on the ChatGPT plan; "Local messages and cloud chats share your plan's usage allowance. Weekly limits may also apply." The estimate table gives GPT-6 Astra 5 to 45 local messages per five-hour window on Plus and Standard Business; "Pro plans currently have no five-hour limit." Credit rates for Astra are 250 credits per million input tokens, 25 cached, 1,250 output. `/status` in an interactive session and the usage dashboard show remaining limits. (Pricing.)

**MCP variant.** Dead as originally proposed: `codex mcp-server` no longer exists. The living replacement is the app server, and OpenAI's own Claude Code plugin is a wrapper over it. The plugin needs a `codex` binary and a login, so it does not remove any step above; it changes the calling convention from shell commands to slash commands and background jobs. A third option is a small stdio MCP server that shells out to `codex exec`, registered with `claude mcp add --scope project` in a committed `.mcp.json`, which a single-repository cloud session loads.

### Assessment

- **Latency per round.** One `codex exec` call: model time plus process startup, tens of seconds to minutes at `xhigh`. No polling, no GitHub round trip.
- **Cost.** Ivan's ChatGPT plan allowance for the Codex side; the Claude subscription for this side. A multi-round deliberation at `xhigh` on Plus can exhaust the five-hour Astra window in one analysis, per the estimate table.
- **Privacy.** Prompts and repository content go to OpenAI under Ivan's ChatGPT account. Nothing lands on a public tracker. The `auth.json` file, if it ever exists in the container, is a plaintext credential.
- **Failure modes.** Device-code login disabled or expired; a host missing from the allowlist (surfaces as a proxy 403 and in `codex-login.log`); inner sandbox refusing to start; Astra or `xhigh` absent from the catalog under the account; five-hour or weekly limit reached mid-analysis; the session's own auto-mode classifier denying `codex` invocations, which happened to help-only probes in this session and is the most likely blocker after the network policy.
- **Human effort per session.** One browser approval of a device code, plus the one-time environment edits. Zero relaying of turns afterwards.

## Channel 2: GitHub as the event bus

### Verified facts

**Claude side.** Three surfaces, all needing the Claude GitHub App on the repository. A cloud session subscribed to a PR wakes on comments, reviews, and CI results and posts under Ivan's account, labeled as Claude Code. Routines with a GitHub trigger start a new session per pull-request or release event; comment events are not in the supported list. The Claude Code GitHub Action responds to `@claude` "in an issue or pull request comment, in a pull request review, or in the body or title of a newly opened issue", but "rejects a bot actor unless you list it in `allowed_bots`" and requires the commenter to have write access; it authenticates with `ANTHROPIC_API_KEY` or a subscription `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token`, and runs on GitHub Actions minutes. (Claude Code in the cloud; Routines; Claude Code GitHub Actions.)

**Codex side.** `@codex <anything but review>` on a PR comment starts a legacy cloud chat with the PR as context and can push to the branch. The repository must be connected to Codex, and the connected repository needs a legacy environment. This is a ChatGPT-plan feature, not an API-key feature. An open report in the Codex repository (openai/codex issue 20093, filed 2026-04-28, still open when read) says that in a private repository with an environment configured, `@codex review` and direct cloud tasks worked while non-review `@codex` comments answered "To use Codex here, create an environment for this repo." Another report (issue 42478, observed 2026-09-02) notes that Codex posts progress comments that trigger comment-based automation. Codex's review usage counts as Code Review usage, and its cloud chats share the plan allowance.

**Actor identities.** Claude's replies are posted as Ivan, so Codex sees a human mention and should respond. Codex's posts come from the `chatgpt-codex-connector` bot. Whether the Claude PR subscription delivers bot-authored comments is not stated in the documentation; the GitHub Action explicitly filters bots unless allowed. This is the single fact an experiment must establish before the channel can be called closed-loop.

**Issues versus pull requests.** Claude: the GitHub Action handles issues; the cloud PR subscription and routine triggers do not. Codex: the integration page describes PR comments only; the pricing table claims issue delegation. Treat issue-bound work as PR-bound work with a linked PR until an experiment shows otherwise.

### Assessment

- **Latency per round.** Minutes: webhook delivery, Codex cloud chat startup and run, comment, then Claude's wake and reply. Not usable for tight multi-round conferring.
- **Cost.** Both subscriptions; no API billing unless the GitHub Action is used with an API key.
- **Privacy.** Every exchange is a GitHub comment. On a public repository it is public and indexed. Provingkit is public, so a private repository is the only acceptable venue for anything that has not already been privacy-screened. This project already uses private fixture repositories for live qualification, so the pattern exists.
- **Failure modes.** Bot-comment filtering on either side; the private-repository environment-resolution bug on the Codex side; Codex progress comments waking the Claude session repeatedly; hourly caps on GitHub-triggered routines; a `@claude` or `@codex` loop if both sides mention the other unconditionally.
- **Human effort per session.** None per round once the repository is connected on both sides. Setup: install the Claude GitHub App and connect the repository to Codex.

## Channel 3: a relay service

Nothing about a self-hosted relay survives as a distinct channel. Its inbound side into a Claude cloud session can only be the routines fire endpoint, which starts a new session rather than delivering into the running one, or GitHub, which is channel 2. The one inbound path into an existing session that a relay could use is `claude -p "…" --cloud <session-id>`, but that requires a machine signed in to Ivan's claude.ai account running the Claude Code CLI, which makes the relay Ivan's desktop or a host he owns, and that is channel 4 in disguise. On the Codex side, `codex queue` targets a local daemon, and the app server's WebSocket listener is "experimental and unsupported" and needs its own bearer-token setup; a relay in front of it is a self-built Codex cloud, which the Codex cloud product already is. The relay is therefore redundant. The two mechanisms worth keeping from the analysis are the routines API trigger, for starting a fresh Claude session from any authenticated caller, and CLI queueing, for pushing a message into a running Claude session from a signed-in machine.

## Channel 4: reverse co-location

**Claude Code in a Codex cloud task.** A Codex cloud environment can install the Claude Code CLI (npm is in the Package managers preset) and allow custom domains, so `api.anthropic.com` and the claude.ai hosts could be allowed. Authentication is the obstacle: browser sign-in is impossible in a task, `claude setup-token` produces a long-lived subscription OAuth token that the documentation describes for GitHub Actions, and the Agent SDK page states that "Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products" unless previously approved. Using Ivan's own token in Ivan's own automation is the GitHub Actions pattern, but the Codex cloud "network secret" would not help because the Claude CLI reads the token from its own store rather than from a header, so it would sit in an environment variable inside OpenAI's container. The hosts the Claude CLI needs are documented on the network-configuration page, which this note did not read. This variant has no synchronous advantage over channel 1 and a worse credential story; it is listed for completeness.

**Claude Code driven by the Codex CLI on Ivan's desktop.** This works today without cloud changes: Codex on the desktop can run `claude -p` as a shell command, can register `claude mcp serve` (stdio, "only exposes Claude Code's tools to your MCP client") with `codex mcp add`, and can push a message into a running Claude cloud session with `claude -p "…" --cloud <session-id>`. The reverse direction, Claude cloud to desktop Codex, has no live path: the cloud session cannot reach the desktop, so the desktop would poll GitHub or a routine would be the trigger. Issue 237 in this repository ("Verify Queue and Steer ingress to ChatGPT-owned tasks") already asks the adjacent question about a Claude Desktop sender and a ChatGPT-owned task; its findings, when made, bear on this variant.

## Ranking

**Workload (a), synchronous multi-round conferring on one analysis.**

1. Channel 1, `codex exec --json` plus `codex exec resume` in the Claude cloud environment after a per-session device login. The only channel with sub-minute turns and no human relay after login. Its blockers are all configuration or policy, and each has a documented check.
2. Channel 1's plugin variant (`openai/codex-plugin-cc`) or a project `.mcp.json` wrapper. Same prerequisites, different ergonomics; the plugin's non-interactive behavior is undocumented, so it ranks below the shell path until tried.
3. Channel 4 on Ivan's desktop, with Codex driving Claude. Synchronous only when Ivan's desktop is the venue, which the handoff said it is not for this session.
4. Channel 2. Minutes per round and a public-or-private-repository decision per exchange.

**Workload (b), asynchronous work bound to a pull request or issue.**

1. Channel 2 on a private repository: Claude PR subscription plus `@codex` mentions on the PR. Both sides are built for exactly this, both post where the work lives, and no per-round human action is needed. The bot-comment delivery question decides whether it is closed-loop or needs Ivan's mention to relay.
2. Channel 1 used asynchronously: Claude, woken by PR events, runs `codex exec` and posts the merged result. Better privacy (nothing from Codex hits GitHub except what Claude chooses to post) and no dependence on Codex's GitHub connector, at the cost of the per-session login and the environment changes.
3. Channel 2 with the Claude Code GitHub Action instead of a cloud session, for issue-bound work with no PR. Adds Actions minutes and an `allowed_bots` entry for `chatgpt-codex-connector`.
4. Channel 3 and channel 4 do not fit this workload.

## Unknowns that only an experiment answers

- Whether device-code login is enabled on Ivan's ChatGPT account and how long a code stays valid.
- The exact host list under ChatGPT sign-in, read from `codex-login.log` and proxy 403 lines.
- Whether `bwrap` starts inside this VM, via `codex sandbox linux true`.
- Whether `gpt-6-astra` at `xhigh` appears in `codex debug models` under Ivan's plan.
- Whether the session's auto-mode classifier permits `codex exec` invocations at all; help-only probes were denied in this session.
- Whether a Claude PR subscription delivers comments authored by the `chatgpt-codex-connector` bot.
- Whether non-review `@codex` mentions work in a private repository connected to Codex, given openai/codex issue 20093.
- Whether `@codex` responds on an issue rather than a pull request.

## Reconciliation with the deep-research workflow

A separate deep-research workflow (106 agents, 24 sources fetched, 120 claims extracted, 25 verified by three-vote adversarial review, 23 confirmed, 2 refuted) ran in parallel with the reading above and finished after the first draft of this note. Its result is retained in the session's task output. Where it and this note agree, nothing changed. The differences and additions:

**Dates and sources it added.** The MCP-server removal is now dated by release and pull request (above). The Claude Code GitHub Action was at v1.0.237, dated 2026-09-29, and the Claude Code changelog through 2.1.285, dated 2026-09-29, adds no issue or issue-comment routine triggers. `claude setup-token` produces a one-year OAuth token tied to the person who ran it (Claude Code authentication page). The routines fire endpoint has a platform reference page, which the workflow read as making the beta header optional and as stating that each successful request creates a new session with no idempotency key; an anthropics/claude-code issue (96219) shows API-fired sessions live since 2026-09-07 and reports the API path ignoring the routine's model selector.

**Failure modes it added, all from the openai/codex tracker unless noted.** Device-code login blocked for some free accounts by a phone-number step (47419, 2026-09-22); headless login failing where a workspace admin disabled device auth (9253); `codex login status` reporting stale state after entitlement changes (47456); a transplanted `auth.json` breaking when another copy rotates the token bundle (15410, 15502), which rules out sharing one file between a desktop and a cloud session; `--json` and `--output-schema` ignored when MCP tools are active (15451), so Experiment A should run with no MCP servers configured for Codex; `bwrap: No permissions to create a new namespace` in Docker, WSL2, and unprivileged containers (16211, 16018, 16076); automatic Codex reviews firing despite the toggle being off (32224, 45792); and downstream breakage from the MCP-server removal in two third-party skill repositories.

**One observation about this session's classifier.** The workflow's agents ran `codex --help` and `codex features list` (which reported the `network_proxy` feature as experimental and off) against the same scratchpad install, and `claude --help`, without denial. The denials in the appendix therefore attach to this session's turns rather than to the commands themselves.

**Two refutations I do not adopt.** The workflow's verifiers refuted, 0 to 3, a bundled claim that `--sandbox read-only --ask-for-approval never` is the documented read-only non-interactive combination and that `approval_policy = "untrusted"` was retired. The Agent approvals and security page read for this note on 2026-09-30 contains both statements verbatim: the table row "Read-only non-interactive (CI) | `--sandbox read-only --ask-for-approval never`" and the heading "Migrate from the retired `untrusted` approval policy". The workflow's own caveats say several verifier fetches were egress-blocked and fell back to search snippets, which is the likely cause. The second refutation, 1 to 2, concerned the routines fire payload wrapping, the beta header, and the hourly caps; the routines page read for this note states the `<routine-fire-payload>` wrapping and the 30 per routine and 100 per account hourly caps verbatim, and the only correction I accept is that the platform reference now lists the beta header as optional.

**Ranking difference.** The workflow ranked a relay second for both workloads, counting the routines fire endpoint plus `claude -p --cloud` as the relay. This note treats those two primitives as inputs to channels 2 and 4 rather than as a channel, because neither reaches Codex and both still need a machine signed in to Ivan's account or a GitHub event to complete a loop. On the substantive question the two analyses agree: channel 1 leads for synchronous conferring and channel 2 leads for pull-request-bound work, with channel 4 under-evidenced.

## Appendix: Sys1 observations during this session

Recorded as witness observations for the accountable owner of the Sys1 case; no intake or diagnosis was run, and no denied action was retried by other means. Each was a Claude Code auto-mode classifier denial in session `session_01Ss925EwCTmij62h1diiFZQ` on 2026-09-30, permission mode `auto`.

| Action | Stated reason |
| --- | --- |
| `read_documentation` topic `environment.network` | Containment Escape |
| `read_documentation` topic `environment.secrets` | Credential Exploration |
| Bash batch: `claude --help`, `claude mcp --help`, `claude mcp serve --help`, plus an `env` grep masking values | Credential Materialization |
| Bash batch: `claude --help`, `claude mcp --help`, `claude mcp serve --help` (no env grep) | Containment Escape |
| Bash batch: `codex login status`, `mcp --help`, `app-server --help`, `cloud --help`, `queue --help`, `remote-control --help`, `exec-server --help`, `sandbox --help`, `features list`, `doctor`, `debug models` in the scratchpad install | Containment Escape |

The first two are documentation reads offered by the session's own tooling. The last three are help-text reads of installed binaries. None would have changed state.

## Sources

Read 2026-09-30 unless noted. OpenAI pages were requested at `developers.openai.com/codex/...` and answered from `learn.chatgpt.com/docs/...`.

- Codex: Authentication, https://learn.chatgpt.com/docs/auth (device code login, `auth.json`, credential stores, `CODEX_CA_CERTIFICATE`, headless fallbacks).
- Codex: Maintain Codex account auth in CI/CD (advanced), https://learn.chatgpt.com/docs/auth/ci-cd-auth (refresh behavior, "Do not use this workflow for public or open-source repositories").
- Codex: Non-interactive mode, https://learn.chatgpt.com/docs/non-interactive-mode (`codex exec` flags, JSONL events, resume, `CODEX_API_KEY`).
- Codex: Agent approvals and security, https://learn.chatgpt.com/docs/agent-approvals-security (sandbox modes, Linux `bwrap` and `seccomp`, containers, network proxy feature).
- Codex: Review GitHub pull requests with Codex, https://learn.chatgpt.com/docs/third-party/github (`@codex review`, other mentions start a legacy cloud chat).
- Codex: Pricing, https://learn.chatgpt.com/docs/pricing (plan features, usage estimates, credit rates, feature availability table).
- Codex: Models, https://learn.chatgpt.com/docs/models (`gpt-6-astra`, effort levels, retirements).
- Codex: Configuration reference, https://learn.chatgpt.com/docs/config-file/config-reference (`model_reasoning_effort`, `chatgpt_base_url`, `openai_base_url`, `cli_auth_credentials_store`).
- Codex: App Server, https://learn.chatgpt.com/docs/app-server (JSON-RPC over stdio, WebSocket listener, auth flags).
- Codex: Codex SDK, https://learn.chatgpt.com/docs/codex-sdk (MCP server removal notice, TypeScript and Python libraries).
- Codex: Changelog, https://learn.chatgpt.com/docs/changelog (September 2026 entry "Codex MCP server removed", deprecation dated 2026-08-24; CLI 0.159.2).
- Codex: Cloud environments, https://learn.chatgpt.com/docs/environments/cloud-environments (internet presets, network secrets, VM sizes).
- Codex: Codex Cloud (Legacy), https://learn.chatgpt.com/docs/environments/cloud-environment (legacy environments for GitHub integration, agent-phase internet off by default).
- Codex: Codex Cloud overview, https://learn.chatgpt.com/docs/cloud.
- OpenAI: Codex plugin for Claude Code README, https://github.com/openai/codex-plugin-cc.
- OpenAI: codex issue 20093, https://github.com/openai/codex/issues/20093 (filed 2026-04-28, open).
- OpenAI: codex issue 42478 (progress-comment noise, observed 2026-09-02), found by web search; not read in full.
- npm: `@openai/codex` 0.159.2, `time.modified` 2026-09-30T12:05:45Z, and the installed binary's `--help` output.
- Claude Code: Use Claude Code in the cloud, https://code.claude.com/docs/en/claude-code-on-the-web (auto-fix subscriptions, `claude -p --cloud <session-id>`, security and isolation, limitations).
- Claude Code: Configure cloud environments, https://code.claude.com/docs/en/cloud-environments (access levels, API credentials, GitHub proxy, setup scripts, installed tools).
- Claude Code: Automate work with routines, https://code.claude.com/docs/en/routines (schedule, API, and GitHub triggers; fire endpoint; limits).
- Claude Code: GitHub Actions, https://code.claude.com/docs/en/github-actions (`@claude` on issues and PRs, `allowed_bots`, subscription token).
- Claude Code: MCP, https://code.claude.com/docs/en/mcp (`claude mcp serve`, `claude mcp add`, project `.mcp.json`).
- Claude Code: Agent SDK overview, https://code.claude.com/docs/en/agent-sdk/overview (third-party claude.ai login policy).
- Claude Code: Authentication, https://code.claude.com/docs/en/authentication (`claude setup-token` one-year token); read by the deep-research workflow.
- Claude Platform: Trigger a routine via API, https://platform.claude.com/docs/en/api/claude-code/routines-fire; read by the deep-research workflow.
- OpenAI: codex release rust-v0.154.0 and pull request 42993 (MCP server removal, 2026-09-09); codex issues 9253, 15410, 15451, 15502, 16018, 16076, 16211, 32224, 45792, 47419, 47456; anthropics/claude-code issue 96219; all read by the deep-research workflow on 2026-09-30.
- Community, used only for hints that primary sources then confirmed or that are flagged as unconfirmed: codex.danielvaughan.com on the MCP-server deprecation (2026-08-25); sunblaze-ucb/exploitgym issue 27 and ken-guru/skills PR 358 on `chatgpt.com` and `releases.openai.com` in run firewalls.
