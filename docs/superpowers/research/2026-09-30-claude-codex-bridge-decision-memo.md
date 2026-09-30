# Decision memo: which channel bridges a Claude Code cloud session and Codex

For Ivan. Evidence and sources are in `docs/superpowers/research/2026-09-30-claude-codex-bridge-channels.md`; this memo carries only the recommendation, the smallest confirming experiment for each workload, and what only you can change. Nothing below has been built, installed for future sessions, or posted anywhere. Ivan decides what gets built.

## Recommendation

**Workload (a), synchronous multi-round conferring.** Co-locate the Codex CLI in the Claude cloud environment and drive it with `codex exec --json` and `codex exec resume`, with a device-code login that you approve once per session. This is the only channel with sub-minute turns and no human in the loop after login. The original brief's calling convention survives unchanged; only the environment does not yet permit it. The MCP-server variant the brief allowed for is gone from Codex as of the September 2026 changelog; its replacement, the app server and OpenAI's Claude Code plugin over it, needs the same binary and login and adds nothing for a first experiment.

**Workload (b), asynchronous work bound to a pull request or issue.** Use GitHub as the bus on a private repository: the Claude cloud session subscribed to the pull request, and `@codex` mentions in PR comments to start Codex cloud chats. Provingkit is public, so the exchange itself must not happen there. One fact decides whether this is closed-loop: whether the Claude PR subscription delivers comments authored by the `chatgpt-codex-connector` bot. If it does not, the fallback for (b) is the channel from (a) run inside the PR-subscribed session, which also keeps Codex output off GitHub until Claude chooses to post it.

A self-hosted relay adds nothing: every inbound path into a running Claude cloud session reduces to GitHub events, a routine bound to the session, or `claude -p "…" --cloud <session-id>` from a machine signed in to your account. Reverse co-location (Claude driven by Codex) works on your desktop today without cloud changes, but it is not synchronous from a cloud session and is not recommended for either workload here.

## Experiment A: Codex CLI in the Claude cloud environment

Smallest experiment that confirms channel 1, in order. Stop at the first failure and report it; every step has a documented check.

1. Fresh session in the edited environment. Confirm `which codex` and `codex --version` (setup script ran) and that `CODEX_CA_CERTIFICATE` and `CODEX_HOME` are set.
2. `codex login --device-auth`. The agent relays the URL and one-time code to you in chat; you approve in a browser. Record how long the code stayed valid and whether the proxy logged any 403 during login (`codex-login.log` under the Codex log directory names the failing host if one is missing from the allowlist).
3. `codex debug models` and confirm `gpt-6-astra` is listed and `xhigh` is accepted: `codex exec -m gpt-6-astra -c model_reasoning_effort=xhigh --json --ephemeral "Reply with the single word OK."`
4. `codex sandbox linux true`. If it fails, rerun step 3 with `--sandbox danger-full-access`, which is what the flag's own help text says it is for inside an externally sandboxed container, and record that the inner sandbox is unavailable.
5. A two-turn round trip: `codex exec --json -o first.md "…"` then `codex exec resume --last "…"`, and confirm the second turn saw the first.
6. Note the five-hour usage reading from the usage dashboard before and after, to size how many `xhigh` rounds one analysis can afford on your plan.

One risk is not an environment setting: in this session the auto-mode classifier denied help-only invocations of `codex` subcommands. If it denies `codex exec` as well, the experiment ends there and the finding belongs to the Sys1 case rather than to this bridge.

### What you must change for Experiment A

Environment (cloud environment menu in the session title bar, then Edit), on a copy of the environment rather than the default one:

- **Network access:** Custom, with the default list included, plus `chatgpt.com`, `auth.openai.com`, and `api.openai.com`. If login still fails, the 403 lines name the missing host; `releases.openai.com` is only needed if the update check stays on.
- **Setup script:**

  ```sh
  npm install -g @openai/codex
  ```

- **Environment variables:**

  ```sh
  CODEX_CA_CERTIFICATE=/root/.ccr/ca-bundle.crt
  CODEX_HOME=/root/.codex
  ```

  and, to keep the updater off the network and the credential out of any file, a `config.toml` written by the setup script with `check_for_update_on_startup = false` and `cli_auth_credentials_store = "ephemeral"`. The ephemeral store means each `codex exec` process logs in afresh from memory only, which the documentation describes but which has not been tried with device auth; if it forces a new device code per invocation, fall back to `file`, which writes `auth.json` into the ephemeral container and nowhere else.

ChatGPT account: enable device code login under security settings, as the authentication page requires.

Do not put a Codex `auth.json` into environment variables or the setup script. Anyone who uses the environment can read both, and the documentation says to treat the file like a password.

## Experiment B: GitHub as the bus on a private repository

Smallest experiment that confirms channel 2, using a disposable private repository as this project already does for live qualification.

1. Install the Claude GitHub App on the private repository and connect the repository to Codex in the Codex code-review settings, including a legacy environment for it.
2. Open a pull request with a one-file change and a question in the description.
3. From a Claude cloud session, subscribe to the PR and have Claude post a comment that ends with `@codex <question>`. Claude's comment is posted under your GitHub account, so Codex should treat it as a human mention.
4. Observe whether Codex reacts and posts, and whether its post wakes the Claude session. Record the actor login on Codex's comment and whether the subscribed session received an event for it. This is the deciding observation.
5. If the session did not wake, post the same mention yourself as a control, and separately test whether a routine with a GitHub trigger on the PR fires on Codex's push.
6. Optionally, comment `@codex` on an issue in the same repository to settle whether issue mentions work.

Watch for a mention loop: instruct both sides to mention the other only when they have a question, and cap rounds.

### What you must change for Experiment B

- GitHub: a private fixture repository; the Claude GitHub App installed on it.
- Codex: the repository connected in Codex settings with a legacy environment (a ChatGPT plan feature, not available under API-key sign-in). Known risk: openai/codex issue 20093, open since 2026-04-28, reports non-review `@codex` comments failing in a private repository with "create an environment for this repo".
- Nothing in the Claude cloud environment.

## Tickets

This repository's agent docs track issues in GitHub and give the write procedure, but they do not require tickets for experiments, and the handoff's hygiene rule forbids posting to a public tracker on my own initiative. Provingkit is public. The two tickets are therefore drafted here and not filed. Say the word and I file them with the preflight already done: no existing issue covers this bridge (search on 2026-09-30 found only the Codex and Claude Code trial-rig tickets 314 and 315 and the Queue/Steer ingress research ticket 237, which is adjacent and should be linked from ticket B).

**Draft ticket A.** Title: `Trial a per-session Codex CLI device login inside a Claude Code cloud environment`. Labels: `wayfinder:task`. Body: the six steps of Experiment A, the environment changes above, the expected records (login duration, host 403 lines, model catalog, sandbox result, usage delta), and the stop rule on a classifier denial. Link the research note.

**Draft ticket B.** Title: `Trial a Claude PR subscription and @codex mentions as a two-agent bus on a private fixture repository`. Labels: `wayfinder:task`. Body: the six steps of Experiment B, the deciding observation (bot-authored comment delivery), the loop guard, and a link to issue 237. Link the research note.

## What this memo does not decide

- Which ChatGPT plan tier the synchronous workload needs; the pricing page's estimate of 5 to 45 Astra messages per five hours on Plus, with no five-hour limit on Pro, is the input.
- Whether the arch-pkgs pushback brief should wait for Experiment A or run on your desktop as written. The sibling session has been told the environment is unchanged.
- Whether the classifier denials seen here are in scope for the Sys1 case; they are recorded in the research note's appendix for its owner.
