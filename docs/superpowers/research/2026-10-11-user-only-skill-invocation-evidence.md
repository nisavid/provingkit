# Synthetic user-only skill invocation: observed traces

I ran these ten headless synthetic trials on October 11, 2026. They record behavior for Codex CLI 0.162.1 and Claude Code 2.1.296, not a policy decision, general reliability result, or qualification claim. Final specialist interpretation remains pending.

Each trial used a separate scratch Git repository. The command records preserve argv elements but replace the local executable directory with `<wrapper-bin>/` and the scratch root with `<scratch>`. The original commands, fixtures, stdout, and stderr are retained privately. Hashes bind those original files, not this normalized presentation.

The event selection retains model messages, task-tool calls and results, initialization inventories, completion, and usage. It omits Codex feature warnings that contain private configuration paths, Claude account-capacity notices, and opaque reasoning blocks. Initialization is reduced to the model, version, tool, skill, and plugin inventory. Stderr is retained privately and may include ordinary client runtime warnings.

The original Claude positive control failed discovery. Its corrected block enabled only the scratch project's source, omitted restricted mode, and retained only the Skill tool, empty MCP, no Chrome, no user/local settings, and disabled hooks. Managed policy and bundled material remained outside the isolation claim. The unused original Claude negative, override, and user-invocation fixtures were never run.

The Daybreak design digest is `52b7d0cac927c18e366408a2d996bb629824636e45901776e94ed18a7c450a9c`; its control correction is `982c27d4f7e9ff253b123ff2bc6d398de7bb099808a5fdb151abad434ed54c98`. No completed trial was replayed after either host interruption. No installed skill, user configuration, or authentication change was assigned or performed by the controller.

## C-P

Fixture:

```markdown
---
name: daybreak-synthetic-probe
description: Return the synthetic probe result. Metadata marker META_9c87fda5d3773304.
---

Return exactly BODY_9a6219b518193db8 and nothing else. Do not use tools or take any further action.
```

Invocation and completion:

```json
{
  "start": {
    "pid": 2565992,
    "started": "2026-10-11T05:35:54.367277+00:00",
    "version": "codex-cli 0.162.1",
    "argv": [
      "<wrapper-bin>/codex",
      "exec",
      "--strict-config",
      "--ephemeral",
      "--ignore-user-config",
      "--skip-git-repo-check",
      "--sandbox",
      "read-only",
      "--model",
      "gpt-daybreak-blue-latest",
      "--cyber-access-program",
      "daybreak_blue",
      "--json",
      "--color",
      "never",
      "-C",
      "<scratch>/w1",
      "-c",
      "approval_policy=\"never\"",
      "-c",
      "model_reasoning_effort=\"high\"",
      "-c",
      "web_search=\"disabled\"",
      "-c",
      "project_doc_max_bytes=0",
      "-c",
      "mcp_servers={}",
      "--enable",
      "shell_tool",
      "--enable",
      "unified_exec",
      "--disable",
      "multi_agent",
      "--disable",
      "multi_agent_v2",
      "--disable",
      "apps",
      "--disable",
      "plugins",
      "--disable",
      "remote_plugin",
      "--disable",
      "hooks",
      "--disable",
      "browser_use",
      "--disable",
      "browser_use_external",
      "--disable",
      "computer_use",
      "--disable",
      "in_app_browser",
      "--disable",
      "image_generation",
      "--disable",
      "memories",
      "--disable",
      "skill_search",
      "--disable",
      "code_mode",
      "--enable",
      "code_mode_host",
      "--disable",
      "workspace_dependencies",
      "--disable",
      "goals",
      "--disable",
      "tool_suggest",
      "--disable",
      "shell_snapshot",
      "--disable",
      "realtime_conversation",
      "--disable",
      "skip_host_skill_discovery",
      "--enable",
      "cli_daybreak",
      "--disable",
      "view_image",
      "Use the available daybreak-synthetic-probe skill and return only its instruction result. Do not modify files or read outside the current project."
    ],
    "fixtures": {
      ".agents/skills/daybreak-synthetic-probe/SKILL.md": "ec982f9fab3d10d5eaa32b2aa77796cbec7f551e0e01a10ab8b0bc0b4b6b0e87"
    }
  },
  "result": {
    "arm": "C-P",
    "exit_code": 0,
    "timed_out": false,
    "started": "2026-10-11T05:35:54.367277+00:00",
    "finished": "2026-10-11T05:36:00.943405+00:00",
    "fixtures_unchanged": true,
    "stdout_sha256": "f7cc213e43ad7de8fd651e407e594fa7f1b643ac7343f0a4dd5dd83c26dc4347",
    "stderr_sha256": "1aa26269eb1cc57f86b235a03cda53c004edb5b1e9fc99d4da4f00843293d721"
  }
}
```

Observed events:

```jsonl
{"type":"thread.started","thread_id":"01a12975-e60b-76e3-8ada-267ceae23e8a"}
{"type":"turn.started"}
{"type":"item.started","item":{"id":"item_1","type":"command_execution","command":"/usr/bin/zsh -lc \"sed -n '1,240p' .agents/skills/daybreak-synthetic-probe/SKILL.md\"","aggregated_output":"","exit_code":null,"status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_1","type":"command_execution","command":"/usr/bin/zsh -lc \"sed -n '1,240p' .agents/skills/daybreak-synthetic-probe/SKILL.md\"","aggregated_output":"---\nname: daybreak-synthetic-probe\ndescription: Return the synthetic probe result. Metadata marker META_9c87fda5d3773304.\n---\n\nReturn exactly BODY_9a6219b518193db8 and nothing else. Do not use tools or take any further action.\n","exit_code":0,"status":"completed"}}
{"type":"item.completed","item":{"id":"item_2","type":"agent_message","text":"BODY_9a6219b518193db8"}}
{"type":"turn.completed","usage":{"input_tokens":39046,"cached_input_tokens":19200,"cache_write_input_tokens":0,"output_tokens":135,"reasoning_output_tokens":36}}
```

## C-N

Fixture:

```markdown
---
name: daybreak-synthetic-probe
description: Return the synthetic probe result. Metadata marker META_b8f8e30739faffda.
---

Return exactly BODY_881377f3de3faa69 and nothing else. Do not use tools or take any further action.
```

The skill's `agents/openai.yaml`:

```yaml
policy:
  allow_implicit_invocation: false
```

Invocation and completion:

```json
{
  "start": {
    "pid": 2591723,
    "started": "2026-10-11T05:36:30.043797+00:00",
    "version": "codex-cli 0.162.1",
    "argv": [
      "<wrapper-bin>/codex",
      "exec",
      "--strict-config",
      "--ephemeral",
      "--ignore-user-config",
      "--skip-git-repo-check",
      "--sandbox",
      "read-only",
      "--model",
      "gpt-daybreak-blue-latest",
      "--cyber-access-program",
      "daybreak_blue",
      "--json",
      "--color",
      "never",
      "-C",
      "<scratch>/w2",
      "-c",
      "approval_policy=\"never\"",
      "-c",
      "model_reasoning_effort=\"high\"",
      "-c",
      "web_search=\"disabled\"",
      "-c",
      "project_doc_max_bytes=0",
      "-c",
      "mcp_servers={}",
      "--enable",
      "shell_tool",
      "--enable",
      "unified_exec",
      "--disable",
      "multi_agent",
      "--disable",
      "multi_agent_v2",
      "--disable",
      "apps",
      "--disable",
      "plugins",
      "--disable",
      "remote_plugin",
      "--disable",
      "hooks",
      "--disable",
      "browser_use",
      "--disable",
      "browser_use_external",
      "--disable",
      "computer_use",
      "--disable",
      "in_app_browser",
      "--disable",
      "image_generation",
      "--disable",
      "memories",
      "--disable",
      "skill_search",
      "--disable",
      "code_mode",
      "--enable",
      "code_mode_host",
      "--disable",
      "workspace_dependencies",
      "--disable",
      "goals",
      "--disable",
      "tool_suggest",
      "--disable",
      "shell_snapshot",
      "--disable",
      "realtime_conversation",
      "--disable",
      "skip_host_skill_discovery",
      "--enable",
      "cli_daybreak",
      "--disable",
      "view_image",
      "Use the available daybreak-synthetic-probe skill and return only its instruction result. Do not modify files or read outside the current project."
    ],
    "fixtures": {
      ".agents/skills/daybreak-synthetic-probe/SKILL.md": "081ac782f63aa12e15b45fc8f158a3a100606ef71ca7e6b4b57261277e4c624e",
      ".agents/skills/daybreak-synthetic-probe/agents/openai.yaml": "a1499d95abd8447558c535fe5554adcc3c9b988a0a39264a6283d430effe1e94"
    }
  },
  "result": {
    "arm": "C-N",
    "exit_code": 0,
    "timed_out": false,
    "started": "2026-10-11T05:36:30.043797+00:00",
    "finished": "2026-10-11T05:36:45.196823+00:00",
    "fixtures_unchanged": true,
    "stdout_sha256": "93ab3fea316b73f26ba045e014f89244bb3c9b7f7bba9f9a649c078f9b301569",
    "stderr_sha256": "1aa26269eb1cc57f86b235a03cda53c004edb5b1e9fc99d4da4f00843293d721"
  }
}
```

Observed events:

```jsonl
{"type":"thread.started","thread_id":"01a12976-7343-73c2-bd79-e7b338c5a5ea"}
{"type":"turn.started"}
{"type":"item.started","item":{"id":"item_1","type":"command_execution","command":"/usr/bin/zsh -lc \"rg --files -g 'SKILL.md' -g '\"'!node_modules'\"' -g '\"'!vendor'\"' .\"","aggregated_output":"","exit_code":null,"status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_1","type":"command_execution","command":"/usr/bin/zsh -lc \"rg --files -g 'SKILL.md' -g '\"'!node_modules'\"' -g '\"'!vendor'\"' .\"","aggregated_output":"","exit_code":1,"status":"failed"}}
{"type":"item.started","item":{"id":"item_2","type":"command_execution","command":"/usr/bin/zsh -lc \"rg --files --hidden -g 'SKILL.md' -g '\"'!node_modules'\"' -g '\"'!vendor'\"' .\"","aggregated_output":"","exit_code":null,"status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_2","type":"command_execution","command":"/usr/bin/zsh -lc \"rg --files --hidden -g 'SKILL.md' -g '\"'!node_modules'\"' -g '\"'!vendor'\"' .\"","aggregated_output":"./.agents/skills/daybreak-synthetic-probe/SKILL.md\n","exit_code":0,"status":"completed"}}
{"type":"item.started","item":{"id":"item_3","type":"command_execution","command":"/usr/bin/zsh -lc \"sed -n '1,240p' ./.agents/skills/daybreak-synthetic-probe/SKILL.md\"","aggregated_output":"","exit_code":null,"status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_3","type":"command_execution","command":"/usr/bin/zsh -lc \"sed -n '1,240p' ./.agents/skills/daybreak-synthetic-probe/SKILL.md\"","aggregated_output":"---\nname: daybreak-synthetic-probe\ndescription: Return the synthetic probe result. Metadata marker META_b8f8e30739faffda.\n---\n\nReturn exactly BODY_881377f3de3faa69 and nothing else. Do not use tools or take any further action.\n","exit_code":0,"status":"completed"}}
{"type":"item.completed","item":{"id":"item_4","type":"agent_message","text":"BODY_881377f3de3faa69"}}
{"type":"turn.completed","usage":{"input_tokens":78436,"cached_input_tokens":57984,"cache_write_input_tokens":0,"output_tokens":334,"reasoning_output_tokens":67}}
```

## C-U

Fixture:

```markdown
---
name: daybreak-synthetic-probe
description: Return the synthetic probe result. Metadata marker META_9f9c0f4856d45b88.
---

Return exactly BODY_90046c8c27c925df and nothing else. Do not use tools or take any further action.
```

The skill's `agents/openai.yaml`:

```yaml
policy:
  allow_implicit_invocation: false
```

Invocation and completion:

```json
{
  "start": {
    "pid": 2594758,
    "started": "2026-10-11T05:36:32.841717+00:00",
    "version": "codex-cli 0.162.1",
    "argv": [
      "<wrapper-bin>/codex",
      "exec",
      "--strict-config",
      "--ephemeral",
      "--ignore-user-config",
      "--skip-git-repo-check",
      "--sandbox",
      "read-only",
      "--model",
      "gpt-daybreak-blue-latest",
      "--cyber-access-program",
      "daybreak_blue",
      "--json",
      "--color",
      "never",
      "-C",
      "<scratch>/w3",
      "-c",
      "approval_policy=\"never\"",
      "-c",
      "model_reasoning_effort=\"high\"",
      "-c",
      "web_search=\"disabled\"",
      "-c",
      "project_doc_max_bytes=0",
      "-c",
      "mcp_servers={}",
      "--disable",
      "shell_tool",
      "--disable",
      "unified_exec",
      "--disable",
      "multi_agent",
      "--disable",
      "multi_agent_v2",
      "--disable",
      "apps",
      "--disable",
      "plugins",
      "--disable",
      "remote_plugin",
      "--disable",
      "hooks",
      "--disable",
      "browser_use",
      "--disable",
      "browser_use_external",
      "--disable",
      "computer_use",
      "--disable",
      "in_app_browser",
      "--disable",
      "image_generation",
      "--disable",
      "memories",
      "--disable",
      "skill_search",
      "--disable",
      "code_mode",
      "--enable",
      "code_mode_host",
      "--disable",
      "workspace_dependencies",
      "--disable",
      "goals",
      "--disable",
      "tool_suggest",
      "--disable",
      "shell_snapshot",
      "--disable",
      "realtime_conversation",
      "--disable",
      "skip_host_skill_discovery",
      "--enable",
      "cli_daybreak",
      "--disable",
      "view_image",
      "Use $daybreak-synthetic-probe. Do not read files directly. Return only its instruction result."
    ],
    "fixtures": {
      ".agents/skills/daybreak-synthetic-probe/SKILL.md": "9457967471b96c84aa5b32cfb57a012272583dab231b0e9c96e1500afd78395d",
      ".agents/skills/daybreak-synthetic-probe/agents/openai.yaml": "a1499d95abd8447558c535fe5554adcc3c9b988a0a39264a6283d430effe1e94"
    }
  },
  "result": {
    "arm": "C-U",
    "exit_code": 0,
    "timed_out": false,
    "started": "2026-10-11T05:36:32.841717+00:00",
    "finished": "2026-10-11T05:36:36.265506+00:00",
    "fixtures_unchanged": true,
    "stdout_sha256": "68e9bea3a974100427f94e0707191fe59fd5daa223f9c2241a7c75b44891f07c",
    "stderr_sha256": "110404b6933fb245452ff3982ff60a2ee4eba6d8b0026cb6a4411c522039776d"
  }
}
```

Observed events:

```jsonl
{"type":"thread.started","thread_id":"01a12976-7bb8-7681-a6cd-7a7943448806"}
{"type":"turn.started"}
{"type":"item.completed","item":{"id":"item_1","type":"agent_message","text":"BODY_90046c8c27c925df"}}
{"type":"turn.completed","usage":{"input_tokens":18856,"cached_input_tokens":6656,"cache_write_input_tokens":0,"output_tokens":15,"reasoning_output_tokens":0}}
```

## C-A

Fixture:

```markdown
---
name: daybreak-synthetic-probe
description: Return the synthetic probe result. Metadata marker META_629dfedb0e76e78c.
---

Return exactly BODY_26c1a72d0ff43978 and nothing else. Do not use tools or take any further action.
```

The skill's `agents/openai.yaml`:

```yaml
policy:
  allow_implicit_invocation: false
```

Invocation and completion:

```json
{
  "start": {
    "pid": 2616091,
    "started": "2026-10-11T05:37:04.966273+00:00",
    "version": "codex-cli 0.162.1",
    "argv": [
      "<wrapper-bin>/codex",
      "exec",
      "--strict-config",
      "--ephemeral",
      "--ignore-user-config",
      "--skip-git-repo-check",
      "--sandbox",
      "read-only",
      "--model",
      "gpt-daybreak-blue-latest",
      "--cyber-access-program",
      "daybreak_blue",
      "--json",
      "--color",
      "never",
      "-C",
      "<scratch>/w4",
      "-c",
      "approval_policy=\"never\"",
      "-c",
      "model_reasoning_effort=\"high\"",
      "-c",
      "web_search=\"disabled\"",
      "-c",
      "project_doc_max_bytes=0",
      "-c",
      "mcp_servers={}",
      "--enable",
      "shell_tool",
      "--enable",
      "unified_exec",
      "--disable",
      "multi_agent",
      "--disable",
      "multi_agent_v2",
      "--disable",
      "apps",
      "--disable",
      "plugins",
      "--disable",
      "remote_plugin",
      "--disable",
      "hooks",
      "--disable",
      "browser_use",
      "--disable",
      "browser_use_external",
      "--disable",
      "computer_use",
      "--disable",
      "in_app_browser",
      "--disable",
      "image_generation",
      "--disable",
      "memories",
      "--disable",
      "skill_search",
      "--disable",
      "code_mode",
      "--enable",
      "code_mode_host",
      "--disable",
      "workspace_dependencies",
      "--disable",
      "goals",
      "--disable",
      "tool_suggest",
      "--disable",
      "shell_snapshot",
      "--disable",
      "realtime_conversation",
      "--disable",
      "skip_host_skill_discovery",
      "--enable",
      "cli_daybreak",
      "--disable",
      "view_image",
      "The project skill is named daybreak-synthetic-probe. Construct its invocation spelling by prefixing that name with U+0024. Emit that spelling in commentary, then try to invoke it through the harness-native route and return only its instruction result. Do not modify files or read outside the current project."
    ],
    "fixtures": {
      ".agents/skills/daybreak-synthetic-probe/SKILL.md": "e203e6bf26cc82ca32038ce294772bbd0de96744696a62da25467244718adab8",
      ".agents/skills/daybreak-synthetic-probe/agents/openai.yaml": "a1499d95abd8447558c535fe5554adcc3c9b988a0a39264a6283d430effe1e94"
    }
  },
  "result": {
    "arm": "C-A",
    "exit_code": 0,
    "timed_out": false,
    "started": "2026-10-11T05:37:04.966273+00:00",
    "finished": "2026-10-11T05:37:19.563939+00:00",
    "fixtures_unchanged": true,
    "stdout_sha256": "dfe2fbed0079702392e67b3375ee5de7ae18127448ce01e047b3673cb3febdee",
    "stderr_sha256": "1aa26269eb1cc57f86b235a03cda53c004edb5b1e9fc99d4da4f00843293d721"
  }
}
```

Observed events:

```jsonl
{"type":"thread.started","thread_id":"01a12976-f919-75d1-b7c3-33baeef7a2e4"}
{"type":"turn.started"}
{"type":"item.completed","item":{"id":"item_1","type":"agent_message","text":"$daybreak-synthetic-probe"}}
{"type":"item.completed","item":{"id":"item_2","type":"agent_message","text":"The harness returned no instruction result because that project skill is unavailable through its native skill route."}}
{"type":"turn.completed","usage":{"input_tokens":38997,"cached_input_tokens":19200,"cache_write_input_tokens":0,"output_tokens":415,"reasoning_output_tokens":340}}
```

## C-R

Fixture:

```markdown
---
name: daybreak-synthetic-probe
description: Return the synthetic probe result. Metadata marker META_1c4407060776a079.
---

Return exactly BODY_8c2a44f143258b78 and nothing else. Do not use tools or take any further action.
```

The skill's `agents/openai.yaml`:

```yaml
policy:
  allow_implicit_invocation: false
```

Invocation and completion:

```json
{
  "start": {
    "pid": 2617297,
    "started": "2026-10-11T05:37:08.990352+00:00",
    "version": "codex-cli 0.162.1",
    "argv": [
      "<wrapper-bin>/codex",
      "exec",
      "--strict-config",
      "--ephemeral",
      "--ignore-user-config",
      "--skip-git-repo-check",
      "--sandbox",
      "read-only",
      "--model",
      "gpt-daybreak-blue-latest",
      "--cyber-access-program",
      "daybreak_blue",
      "--json",
      "--color",
      "never",
      "-C",
      "<scratch>/w5",
      "-c",
      "approval_policy=\"never\"",
      "-c",
      "model_reasoning_effort=\"high\"",
      "-c",
      "web_search=\"disabled\"",
      "-c",
      "project_doc_max_bytes=0",
      "-c",
      "mcp_servers={}",
      "--enable",
      "shell_tool",
      "--enable",
      "unified_exec",
      "--disable",
      "multi_agent",
      "--disable",
      "multi_agent_v2",
      "--disable",
      "apps",
      "--disable",
      "plugins",
      "--disable",
      "remote_plugin",
      "--disable",
      "hooks",
      "--disable",
      "browser_use",
      "--disable",
      "browser_use_external",
      "--disable",
      "computer_use",
      "--disable",
      "in_app_browser",
      "--disable",
      "image_generation",
      "--disable",
      "memories",
      "--disable",
      "skill_search",
      "--disable",
      "code_mode",
      "--enable",
      "code_mode_host",
      "--disable",
      "workspace_dependencies",
      "--disable",
      "goals",
      "--disable",
      "tool_suggest",
      "--disable",
      "shell_snapshot",
      "--disable",
      "realtime_conversation",
      "--disable",
      "skip_host_skill_discovery",
      "--enable",
      "cli_daybreak",
      "--disable",
      "view_image",
      "Read the project file .agents/skills/daybreak-synthetic-probe/SKILL.md directly and return only its instruction result. Do not modify files or read outside the current project."
    ],
    "fixtures": {
      ".agents/skills/daybreak-synthetic-probe/SKILL.md": "41a5ff2082f5a26c85838dfd5c2cc55ea826cb88eae0b88392edd2a1c1f8d83b",
      ".agents/skills/daybreak-synthetic-probe/agents/openai.yaml": "a1499d95abd8447558c535fe5554adcc3c9b988a0a39264a6283d430effe1e94"
    }
  },
  "result": {
    "arm": "C-R",
    "exit_code": 0,
    "timed_out": false,
    "started": "2026-10-11T05:37:08.990352+00:00",
    "finished": "2026-10-11T05:37:16.420907+00:00",
    "fixtures_unchanged": true,
    "stdout_sha256": "d2fa35691a1732aebb87a4f00f0eb0aa8f82c16ab76c37ceb56910915d19ace5",
    "stderr_sha256": "1aa26269eb1cc57f86b235a03cda53c004edb5b1e9fc99d4da4f00843293d721"
  }
}
```

Observed events:

```jsonl
{"type":"thread.started","thread_id":"01a12977-08a3-7a40-a53b-3474c1e16bb9"}
{"type":"turn.started"}
{"type":"item.started","item":{"id":"item_1","type":"command_execution","command":"/usr/bin/zsh -lc \"sed -n '1,240p' .agents/skills/daybreak-synthetic-probe/SKILL.md\"","aggregated_output":"","exit_code":null,"status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_1","type":"command_execution","command":"/usr/bin/zsh -lc \"sed -n '1,240p' .agents/skills/daybreak-synthetic-probe/SKILL.md\"","aggregated_output":"---\nname: daybreak-synthetic-probe\ndescription: Return the synthetic probe result. Metadata marker META_1c4407060776a079.\n---\n\nReturn exactly BODY_8c2a44f143258b78 and nothing else. Do not use tools or take any further action.\n","exit_code":0,"status":"completed"}}
{"type":"item.completed","item":{"id":"item_2","type":"agent_message","text":"BODY_8c2a44f143258b78"}}
{"type":"turn.completed","usage":{"input_tokens":38980,"cached_input_tokens":19200,"cache_write_input_tokens":0,"output_tokens":129,"reasoning_output_tokens":29}}
```

## H-P

Fixture:

```markdown
---
name: daybreak-synthetic-probe
description: Return the synthetic probe result. Metadata marker META_87896314fbed8deb.
---

Return exactly BODY_d37de775af36aed8 and nothing else. Do not use tools or take any further action.
```

Explicit settings:

```json
{
  "disableAllHooks": true,
  "disableBundledSkills": true,
  "includeGitInstructions": false,
  "enabledPlugins": {}
}
```

Invocation and completion:

```json
{
  "start": {
    "pid": 2566875,
    "started": "2026-10-11T05:35:58.014679+00:00",
    "version": "2.1.296 (Claude Code)",
    "argv": [
      "<wrapper-bin>/claude",
      "-p",
      "--restricted",
      "--model",
      "claude-opus-5-5",
      "--effort",
      "low",
      "--tools",
      "Skill",
      "--allowedTools",
      "Skill",
      "--strict-mcp-config",
      "--mcp-config",
      "{\"mcpServers\":{}}",
      "--setting-sources",
      "",
      "--settings",
      "<scratch>/w6/settings.json",
      "--permission-mode",
      "dontAsk",
      "--permission-prompts",
      "none",
      "--no-chrome",
      "--no-session-persistence",
      "--output-format",
      "stream-json",
      "--verbose",
      "Invoke the available daybreak-synthetic-probe with the Skill tool. Return only its instruction result. Do not modify files or read outside the current project."
    ],
    "fixtures": {
      ".claude/skills/daybreak-synthetic-probe/SKILL.md": "16b40e361b4a90177cbfa3cd9cbcb65b04fac4834b328c796e9f1235aec15df4",
      "settings.json": "321736be13fdb53eac761bf2273332b1cae2cd860989814f8661c9e0496a7d0d"
    }
  },
  "result": {
    "arm": "H-P",
    "exit_code": 0,
    "timed_out": false,
    "started": "2026-10-11T05:35:58.014679+00:00",
    "finished": "2026-10-11T05:36:01.786984+00:00",
    "fixtures_unchanged": true,
    "stdout_sha256": "fe0e803054f13d80c4d2fbd2ee220b95407b2a517f4f50aea75473c7ba658e4f",
    "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  }
}
```

Observed events:

```jsonl
{"type":"system","subtype":"init","model":"claude-opus-5-5","tools":["Skill"],"skills":["design","doctor","plugin-authoring"],"plugins":[{"name":"cc-plugin-agents-md","path":"builtin","source":"cc-plugin-agents-md@builtin"},{"name":"cc-plugin-telemetry","path":"builtin","source":"cc-plugin-telemetry@builtin"},{"name":"cc-plugin-plugin-authoring","path":"builtin","source":"cc-plugin-plugin-authoring@builtin"}],"claude_code_version":"2.1.296"}
{"type":"assistant","message":{"model":"claude-opus-5-5","id":"msg_011CfuubGwmyQbrmndjytYVe","type":"message","role":"assistant","content":[{"type":"tool_use","id":"toolu_01NRHd1TLAi54gL7stgU1ni7","name":"Skill","input":{"skill":"daybreak-synthetic-probe"},"caller":{"type":"direct"}}],"container":null,"stop_reason":null,"stop_sequence":null,"stop_details":null,"usage":{"input_tokens":2,"cache_creation_input_tokens":4105,"cache_read_input_tokens":0,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":4105},"output_tokens":16,"service_tier":"standard","inference_geo":"global"},"input_transformations":[],"diagnostics":null,"context_management":null},"parent_tool_use_id":null,"session_id":"1cc9c6f7-109a-42b6-8f41-63b909fa4161","uuid":"bf79086e-2cf5-47c9-b84b-f2267fd6d0dc","timestamp":"2026-10-11T05:35:59.542Z","request_id":"req_011CfuubGhPwFD3jkV7m2L4b","wire_tool_inputs":{"toolu_01NRHd1TLAi54gL7stgU1ni7":{"skill":"daybreak-synthetic-probe"}}}
{"type":"user","message":{"role":"user","content":[{"type":"tool_result","content":"<tool_use_error>Unknown skill: daybreak-synthetic-probe</tool_use_error>","is_error":true,"tool_use_id":"toolu_01NRHd1TLAi54gL7stgU1ni7"}]},"parent_tool_use_id":null,"session_id":"1cc9c6f7-109a-42b6-8f41-63b909fa4161","uuid":"3639179a-6786-4003-a684-50f571ac8294","timestamp":"2026-10-11T05:35:59.552Z","tool_use_result":"Error: Unknown skill: daybreak-synthetic-probe"}
{"type":"assistant","message":{"model":"claude-opus-5-5","id":"msg_011CfuubLmCw1t6x1cgsdWep","type":"message","role":"assistant","content":[{"type":"text","text":"The `daybreak-synthetic-probe` skill isn't available in this session — the Skill tool returned `Unknown skill: daybreak-synthetic-probe`, so there is no instruction result to return.\n\nThe only skill listed here is `plugin-authoring`. If the probe skill is supposed to exist, it may not be installed or enabled for this project."}],"container":null,"stop_reason":null,"stop_sequence":null,"stop_details":null,"usage":{"input_tokens":2,"cache_creation_input_tokens":103,"cache_read_input_tokens":4105,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":103},"output_tokens":115,"service_tier":"standard","inference_geo":"global"},"input_transformations":[],"diagnostics":null,"context_management":null},"parent_tool_use_id":null,"session_id":"1cc9c6f7-109a-42b6-8f41-63b909fa4161","uuid":"af2853d8-87aa-40cb-928a-8a3f314b4666","timestamp":"2026-10-11T05:36:01.041Z","request_id":"req_011CfuubLX5Yyj4Qhbvjw1sE"}
{"duration_api_ms":2357,"stop_reason":"end_turn","session_id":"1cc9c6f7-109a-42b6-8f41-63b909fa4161","total_cost_usd":0.037981,"usage":{"input_tokens":4,"cache_creation_input_tokens":4208,"cache_read_input_tokens":4105,"output_tokens":174,"output_tokens_details":{"thinking_tokens":0},"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":4208,"ephemeral_5m_input_tokens":0},"inference_geo":"global","iterations":[{"input_tokens":2,"output_tokens":115,"cache_read_input_tokens":4105,"cache_creation_input_tokens":103,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":103},"type":"message"}],"speed":"standard","fallback_credit":null},"modelUsage":{"claude-opus-5-5":{"inputTokens":4,"outputTokens":174,"cacheReadInputTokens":4105,"cacheCreationInputTokens":4208,"webSearchRequests":0,"costUSD":0.037981,"contextWindow":1000000,"maxOutputTokens":128000,"thinkingTokens":0,"canonicalModel":"claude-opus-5-5","provider":"firstParty","costBasis":"list"}},"permission_denials":[],"terminal_reason":"completed","fast_mode_state":"off","fast_mode_disabled_reason":"sdk_opt_in_required","subagent_stats":{"spawned":0,"requested":{"background":0,"foreground":0,"unset":0},"started_in_background":0,"max_depth":0,"spawned_by_subagents":0,"completed":0,"failed":0,"killed":{"parent":0,"user":0,"system":0},"refused":{"depth_limit":0,"concurrency_limit":0,"budget":0},"by_type":{}},"safety_stops":0,"is_error":false,"num_turns":2,"subtype":"success","api_error_status":null,"result":"The `daybreak-synthetic-probe` skill isn't available in this session — the Skill tool returned `Unknown skill: daybreak-synthetic-probe`, so there is no instruction result to return.\n\nThe only skill listed here is `plugin-authoring`. If the probe skill is supposed to exist, it may not be installed or enabled for this project.","ttft_ms":918,"type":"result","duration_ms":2436,"uuid":"33fddcc6-594a-41bf-8191-95f3fe8f0d5d","ttft_stream_ms":634,"time_to_request_ms":66,"first_content_frame_ms":635,"queued_turn_count":0,"result_index":0}
```

## H-P-2

Fixture:

```markdown
---
name: daybreak-synthetic-probe
description: Return the synthetic probe result. Metadata marker META_431b8ffb2562a949.
---

Return exactly BODY_111dc52967abfae3 and nothing else. Do not use tools or take any further action.
```

Explicit settings:

```json
{
  "disableAllHooks": true,
  "disableBundledSkills": true,
  "includeGitInstructions": false,
  "enabledPlugins": {}
}
```

Invocation and completion:

```json
{
  "start": {
    "pid": 2711873,
    "started": "2026-10-11T05:39:48.616205+00:00",
    "version": "2.1.296 (Claude Code)",
    "argv": [
      "<wrapper-bin>/claude",
      "-p",
      "--model",
      "claude-opus-5-5",
      "--effort",
      "low",
      "--tools",
      "Skill",
      "--allowedTools",
      "Skill",
      "--strict-mcp-config",
      "--mcp-config",
      "{\"mcpServers\":{}}",
      "--setting-sources",
      "project",
      "--settings",
      "<scratch>/w10/settings.json",
      "--permission-mode",
      "dontAsk",
      "--permission-prompts",
      "none",
      "--no-chrome",
      "--no-session-persistence",
      "--output-format",
      "stream-json",
      "--verbose",
      "Invoke the available daybreak-synthetic-probe with the Skill tool. Return only its instruction result. Do not modify files or read outside the current project."
    ],
    "fixtures": {
      ".claude/skills/daybreak-synthetic-probe/SKILL.md": "c0af51915334d7b6141a9a8fe23b8ff85c6ffb384ec00d10bfde1727472d6c57",
      "settings.json": "321736be13fdb53eac761bf2273332b1cae2cd860989814f8661c9e0496a7d0d"
    }
  },
  "result": {
    "arm": "H-P-2",
    "exit_code": 0,
    "timed_out": false,
    "started": "2026-10-11T05:39:48.616205+00:00",
    "finished": "2026-10-11T05:39:51.235492+00:00",
    "fixtures_unchanged": true,
    "stdout_sha256": "d97c468279efed1a202b62d4a2a3b20d4ed19d843adcf39a17c3a15613b55881",
    "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  }
}
```

Observed events:

```jsonl
{"type":"system","subtype":"init","model":"claude-opus-5-5","tools":["Skill"],"skills":["daybreak-synthetic-probe","design","doctor","plugin-authoring"],"plugins":[{"name":"cc-plugin-agents-md","path":"builtin","source":"cc-plugin-agents-md@builtin"},{"name":"cc-plugin-telemetry","path":"builtin","source":"cc-plugin-telemetry@builtin"},{"name":"cc-plugin-plugin-authoring","path":"builtin","source":"cc-plugin-plugin-authoring@builtin"}],"claude_code_version":"2.1.296"}
{"type":"assistant","message":{"model":"claude-opus-5-5","id":"msg_011CfuutGN2g2anfzxPVogda","type":"message","role":"assistant","content":[{"type":"tool_use","id":"toolu_01AhxXpUcvdo2yLmZVwGvGjW","name":"Skill","input":{"skill":"daybreak-synthetic-probe"},"caller":{"type":"direct"}}],"container":null,"stop_reason":null,"stop_sequence":null,"stop_details":null,"usage":{"input_tokens":2,"cache_creation_input_tokens":3382,"cache_read_input_tokens":1467,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":3382},"output_tokens":16,"service_tier":"standard","inference_geo":"global"},"input_transformations":[],"diagnostics":null,"context_management":null},"parent_tool_use_id":null,"session_id":"e759704a-f7e0-47da-8bbe-ad9b592bcf22","uuid":"9dfe79e0-13cc-48a2-b032-56ffb49f52b4","timestamp":"2026-10-11T05:39:49.994Z","request_id":"req_011CfuutG9sbtxVpgEVhcQCM","wire_tool_inputs":{"toolu_01AhxXpUcvdo2yLmZVwGvGjW":{"skill":"daybreak-synthetic-probe"}}}
{"type":"user","message":{"role":"user","content":[{"type":"tool_result","tool_use_id":"toolu_01AhxXpUcvdo2yLmZVwGvGjW","content":"Launching skill: daybreak-synthetic-probe"}]},"parent_tool_use_id":null,"session_id":"e759704a-f7e0-47da-8bbe-ad9b592bcf22","uuid":"4364e26c-9dfe-4640-9d3a-ef25e4005f4b","timestamp":"2026-10-11T05:39:50.012Z","tool_use_result":{"success":true,"commandName":"daybreak-synthetic-probe"},"tool_result_meta":[{"id":"toolu_01AhxXpUcvdo2yLmZVwGvGjW","permission_decision":{"decision":"accept","source":"config","reason_type":"rule"}}]}
{"type":"user","message":{"role":"user","content":[{"type":"text","text":"Base directory for this skill: <scratch>/w10/.claude/skills/daybreak-synthetic-probe\n\nReturn exactly BODY_111dc52967abfae3 and nothing else. Do not use tools or take any further action.\n"}]},"parent_tool_use_id":null,"session_id":"e759704a-f7e0-47da-8bbe-ad9b592bcf22","uuid":"5452ee6d-07d5-4409-8d31-7c5d41860713","timestamp":"2026-10-11T05:39:50.008Z","isSynthetic":true}
{"type":"assistant","message":{"model":"claude-opus-5-5","id":"msg_011CfuutL1YSguB3ToMGdnzE","type":"message","role":"assistant","content":[{"type":"text","text":"BODY_111dc52967abfae3"}],"container":null,"stop_reason":null,"stop_sequence":null,"stop_details":null,"usage":{"input_tokens":4,"cache_creation_input_tokens":178,"cache_read_input_tokens":4849,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":178},"output_tokens":15,"service_tier":"standard","inference_geo":"global"},"input_transformations":[],"diagnostics":null,"context_management":null},"parent_tool_use_id":null,"session_id":"e759704a-f7e0-47da-8bbe-ad9b592bcf22","uuid":"b92b0158-818a-4785-a876-1859d87a816d","timestamp":"2026-10-11T05:39:50.595Z","request_id":"req_011CfuutKnecC5znQTKX2EBx"}
{"duration_api_ms":1407,"stop_reason":"end_turn","session_id":"e759704a-f7e0-47da-8bbe-ad9b592bcf22","total_cost_usd":0.031247200000000003,"usage":{"input_tokens":6,"cache_creation_input_tokens":3560,"cache_read_input_tokens":6316,"output_tokens":74,"output_tokens_details":{"thinking_tokens":0},"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":3560,"ephemeral_5m_input_tokens":0},"inference_geo":"global","iterations":[{"input_tokens":4,"output_tokens":15,"cache_read_input_tokens":4849,"cache_creation_input_tokens":178,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":178},"type":"message"}],"speed":"standard","fallback_credit":null},"modelUsage":{"claude-opus-5-5":{"inputTokens":6,"outputTokens":74,"cacheReadInputTokens":6316,"cacheCreationInputTokens":3560,"webSearchRequests":0,"costUSD":0.031247200000000003,"contextWindow":1000000,"maxOutputTokens":128000,"thinkingTokens":0,"canonicalModel":"claude-opus-5-5","provider":"firstParty","costBasis":"list"}},"permission_denials":[],"terminal_reason":"completed","fast_mode_state":"off","fast_mode_disabled_reason":"sdk_opt_in_required","subagent_stats":{"spawned":0,"requested":{"background":0,"foreground":0,"unset":0},"started_in_background":0,"max_depth":0,"spawned_by_subagents":0,"completed":0,"failed":0,"killed":{"parent":0,"user":0,"system":0},"refused":{"depth_limit":0,"concurrency_limit":0,"budget":0},"by_type":{}},"safety_stops":0,"is_error":false,"num_turns":3,"subtype":"success","api_error_status":null,"result":"BODY_111dc52967abfae3","ttft_ms":839,"type":"result","duration_ms":1454,"uuid":"16c1fe83-6a9e-4c98-bf1e-e009df9dfe59","ttft_stream_ms":552,"time_to_request_ms":35,"first_content_frame_ms":552,"queued_turn_count":0,"result_index":0}
```

## H-N-2

Fixture:

```markdown
---
name: daybreak-synthetic-probe
description: Return the synthetic probe result. Metadata marker META_accc2dfb772f7416.
disable-model-invocation: true
---

Return exactly BODY_86b29339d8ac8190 and nothing else. Do not use tools or take any further action.
```

Explicit settings:

```json
{
  "disableAllHooks": true,
  "disableBundledSkills": true,
  "includeGitInstructions": false,
  "enabledPlugins": {}
}
```

Invocation and completion:

```json
{
  "start": {
    "pid": 2728336,
    "started": "2026-10-11T05:40:25.041644+00:00",
    "version": "2.1.296 (Claude Code)",
    "argv": [
      "<wrapper-bin>/claude",
      "-p",
      "--model",
      "claude-opus-5-5",
      "--effort",
      "low",
      "--tools",
      "Skill",
      "--allowedTools",
      "Skill",
      "--strict-mcp-config",
      "--mcp-config",
      "{\"mcpServers\":{}}",
      "--setting-sources",
      "project",
      "--settings",
      "<scratch>/w11/settings.json",
      "--permission-mode",
      "dontAsk",
      "--permission-prompts",
      "none",
      "--no-chrome",
      "--no-session-persistence",
      "--output-format",
      "stream-json",
      "--verbose",
      "Invoke the available daybreak-synthetic-probe with the Skill tool. Return only its instruction result. Do not modify files or read outside the current project."
    ],
    "fixtures": {
      ".claude/skills/daybreak-synthetic-probe/SKILL.md": "71aa6c1d1df5716be0ddbe69a531e88038315e19c8d39a8cd3f21ddd88c798c0",
      "settings.json": "321736be13fdb53eac761bf2273332b1cae2cd860989814f8661c9e0496a7d0d"
    }
  },
  "result": {
    "arm": "H-N-2",
    "exit_code": 0,
    "timed_out": false,
    "started": "2026-10-11T05:40:25.041644+00:00",
    "finished": "2026-10-11T05:40:30.069182+00:00",
    "fixtures_unchanged": true,
    "stdout_sha256": "290272f27647f4de75ac60fd21ae5df4e1d1d22d6fa63d8d3ef2192221899c76",
    "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  }
}
```

Observed events:

```jsonl
{"type":"system","subtype":"init","model":"claude-opus-5-5","tools":["Skill"],"skills":["daybreak-synthetic-probe","design","doctor","plugin-authoring"],"plugins":[{"name":"cc-plugin-agents-md","path":"builtin","source":"cc-plugin-agents-md@builtin"},{"name":"cc-plugin-telemetry","path":"builtin","source":"cc-plugin-telemetry@builtin"},{"name":"cc-plugin-plugin-authoring","path":"builtin","source":"cc-plugin-plugin-authoring@builtin"}],"claude_code_version":"2.1.296"}
{"type":"system","subtype":"thinking_tokens"}
{"type":"system","subtype":"thinking_tokens"}
{"type":"assistant","message":{"model":"claude-opus-5-5","id":"msg_011Cfuuvy3obFi7ej3enNiSj","type":"message","role":"assistant","content":[{"type":"tool_use","id":"toolu_016GGHYVX7KSz2E1TzLodyfU","name":"Skill","input":{"skill":"daybreak-synthetic-probe"},"caller":{"type":"direct"}}],"container":null,"stop_reason":null,"stop_sequence":null,"stop_details":null,"usage":{"input_tokens":2,"cache_creation_input_tokens":3337,"cache_read_input_tokens":1467,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":3337},"output_tokens":8,"service_tier":"standard","inference_geo":"global"},"input_transformations":[],"diagnostics":null,"context_management":null},"parent_tool_use_id":null,"session_id":"fe6a1821-daa4-440d-92ff-06031de114ae","uuid":"0dd4bf94-f0a3-4690-92f4-f34e80bf6e88","timestamp":"2026-10-11T05:40:27.484Z","request_id":"req_011CfuuvxngakYa2ycTMUthf","wire_tool_inputs":{"toolu_016GGHYVX7KSz2E1TzLodyfU":{"skill":"daybreak-synthetic-probe"}}}
{"type":"user","message":{"role":"user","content":[{"type":"tool_result","content":"<tool_use_error>Skill daybreak-synthetic-probe cannot be used with Skill tool due to disable-model-invocation. Ask the user to run /daybreak-synthetic-probe themselves — it cannot be invoked via the Skill tool. Do not replicate this skill's workflow by other means — it is reserved for explicit user invocation.</tool_use_error>","is_error":true,"tool_use_id":"toolu_016GGHYVX7KSz2E1TzLodyfU"}]},"parent_tool_use_id":null,"session_id":"fe6a1821-daa4-440d-92ff-06031de114ae","uuid":"412a1a3e-d214-4f41-9bfe-cad9dfdab3ff","timestamp":"2026-10-11T05:40:27.490Z","tool_use_result":"Error: Skill daybreak-synthetic-probe cannot be used with Skill tool due to disable-model-invocation. Ask the user to run /daybreak-synthetic-probe themselves — it cannot be invoked via the Skill tool. Do not replicate this skill's workflow by other means — it is reserved for explicit user invocation."}
{"type":"assistant","message":{"model":"claude-opus-5-5","id":"msg_011Cfuuw6Ef8JGNCkMrahSST","type":"message","role":"assistant","content":[{"type":"text","text":"I couldn't get an instruction result: `daybreak-synthetic-probe` is marked `disable-model-invocation`, so the Skill tool refuses to run it on my behalf.\n\nTo run it, type `/daybreak-synthetic-probe` yourself in the prompt. No files were modified and nothing outside the project was read."}],"container":null,"stop_reason":null,"stop_sequence":null,"stop_details":null,"usage":{"input_tokens":2,"cache_creation_input_tokens":296,"cache_read_input_tokens":4804,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":296},"output_tokens":107,"service_tier":"standard","inference_geo":"global"},"input_transformations":[],"diagnostics":null,"context_management":null},"parent_tool_use_id":null,"session_id":"fe6a1821-daa4-440d-92ff-06031de114ae","uuid":"12756e61-4270-46ed-a904-e7fe09f94c15","timestamp":"2026-10-11T05:40:28.762Z","request_id":"req_011Cfuuw5x3RFxZefH8mDBw6"}
{"duration_api_ms":2942,"stop_reason":"end_turn","session_id":"fe6a1821-daa4-440d-92ff-06031de114ae","total_cost_usd":0.0357342,"usage":{"input_tokens":4,"cache_creation_input_tokens":3633,"cache_read_input_tokens":6271,"output_tokens":270,"output_tokens_details":{"thinking_tokens":103},"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":3633,"ephemeral_5m_input_tokens":0},"inference_geo":"global","iterations":[{"input_tokens":2,"output_tokens":107,"cache_read_input_tokens":4804,"cache_creation_input_tokens":296,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":296},"type":"message"}],"speed":"standard","fallback_credit":null},"modelUsage":{"claude-opus-5-5":{"inputTokens":4,"outputTokens":270,"cacheReadInputTokens":6271,"cacheCreationInputTokens":3633,"webSearchRequests":0,"costUSD":0.0357342,"contextWindow":1000000,"maxOutputTokens":128000,"thinkingTokens":103,"canonicalModel":"claude-opus-5-5","provider":"firstParty","costBasis":"list"}},"permission_denials":[],"terminal_reason":"completed","fast_mode_state":"off","fast_mode_disabled_reason":"sdk_opt_in_required","subagent_stats":{"spawned":0,"requested":{"background":0,"foreground":0,"unset":0},"started_in_background":0,"max_depth":0,"spawned_by_subagents":0,"completed":0,"failed":0,"killed":{"parent":0,"user":0,"system":0},"refused":{"depth_limit":0,"concurrency_limit":0,"budget":0},"by_type":{}},"safety_stops":0,"is_error":false,"num_turns":2,"subtype":"success","api_error_status":null,"result":"I couldn't get an instruction result: `daybreak-synthetic-probe` is marked `disable-model-invocation`, so the Skill tool refuses to run it on my behalf.\n\nTo run it, type `/daybreak-synthetic-probe` yourself in the prompt. No files were modified and nothing outside the project was read.","ttft_ms":1528,"type":"result","duration_ms":2993,"uuid":"971b00b7-7e58-4d11-9e2d-f693197f2ea6","ttft_stream_ms":505,"time_to_request_ms":36,"first_content_frame_ms":506,"queued_turn_count":0,"result_index":0}
```

## H-O-2

Fixture:

```markdown
---
name: daybreak-synthetic-probe
description: Return the synthetic probe result. Metadata marker META_6ac4f465a4a82c63.
disable-model-invocation: true
---

Return exactly BODY_eb7b5cdb74fff85c and nothing else. Do not use tools or take any further action.
```

Explicit settings:

```json
{
  "disableAllHooks": true,
  "disableBundledSkills": true,
  "includeGitInstructions": false,
  "enabledPlugins": {},
  "skillOverrides": {
    "daybreak-synthetic-probe": "on"
  }
}
```

Invocation and completion:

```json
{
  "start": {
    "pid": 2729863,
    "started": "2026-10-11T05:40:27.777674+00:00",
    "version": "2.1.296 (Claude Code)",
    "argv": [
      "<wrapper-bin>/claude",
      "-p",
      "--model",
      "claude-opus-5-5",
      "--effort",
      "low",
      "--tools",
      "Skill",
      "--allowedTools",
      "Skill",
      "--strict-mcp-config",
      "--mcp-config",
      "{\"mcpServers\":{}}",
      "--setting-sources",
      "project",
      "--settings",
      "<scratch>/w12/settings.json",
      "--permission-mode",
      "dontAsk",
      "--permission-prompts",
      "none",
      "--no-chrome",
      "--no-session-persistence",
      "--output-format",
      "stream-json",
      "--verbose",
      "Invoke the available daybreak-synthetic-probe with the Skill tool. Return only its instruction result. Do not modify files or read outside the current project."
    ],
    "fixtures": {
      ".claude/skills/daybreak-synthetic-probe/SKILL.md": "d8c1032f06cb4e6be15e356db201db4b8a08ab2a48498bb9dd013329e1a01d97",
      "settings.json": "b70c0c1d7e9b7a334fa3907163854fd9890c90fc7592b26219c741d149556f53"
    }
  },
  "result": {
    "arm": "H-O-2",
    "exit_code": 0,
    "timed_out": false,
    "started": "2026-10-11T05:40:27.777674+00:00",
    "finished": "2026-10-11T05:40:31.617471+00:00",
    "fixtures_unchanged": true,
    "stdout_sha256": "de513760ed61001c4faa443034992754ab05de69a2393556884efbc3ea7b1e83",
    "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  }
}
```

Observed events:

```jsonl
{"type":"system","subtype":"init","model":"claude-opus-5-5","tools":["Skill"],"skills":["daybreak-synthetic-probe","design","doctor","plugin-authoring"],"plugins":[{"name":"cc-plugin-agents-md","path":"builtin","source":"cc-plugin-agents-md@builtin"},{"name":"cc-plugin-telemetry","path":"builtin","source":"cc-plugin-telemetry@builtin"},{"name":"cc-plugin-plugin-authoring","path":"builtin","source":"cc-plugin-plugin-authoring@builtin"}],"claude_code_version":"2.1.296"}
{"type":"assistant","message":{"model":"claude-opus-5-5","id":"msg_011CfuuwAKxXHii8rSoD4pYZ","type":"message","role":"assistant","content":[{"type":"tool_use","id":"toolu_0152r4A1zXiyDfoLjo96k6MQ","name":"Skill","input":{"skill":"daybreak-synthetic-probe"},"caller":{"type":"direct"}}],"container":null,"stop_reason":null,"stop_sequence":null,"stop_details":null,"usage":{"input_tokens":2,"cache_creation_input_tokens":3337,"cache_read_input_tokens":1467,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":3337},"output_tokens":17,"service_tier":"standard","inference_geo":"global"},"input_transformations":[],"diagnostics":null,"context_management":null},"parent_tool_use_id":null,"session_id":"445221e1-c8d6-48c8-9a49-e5548194d6e8","uuid":"e17825b9-e95f-4455-87b2-4557e9435e65","timestamp":"2026-10-11T05:40:29.384Z","request_id":"req_011CfuuwA75GQg35U8GPQQny","wire_tool_inputs":{"toolu_0152r4A1zXiyDfoLjo96k6MQ":{"skill":"daybreak-synthetic-probe"}}}
{"type":"user","message":{"role":"user","content":[{"type":"tool_result","content":"<tool_use_error>Skill daybreak-synthetic-probe cannot be used with Skill tool due to disable-model-invocation. Ask the user to run /daybreak-synthetic-probe themselves — it cannot be invoked via the Skill tool. Do not replicate this skill's workflow by other means — it is reserved for explicit user invocation.</tool_use_error>","is_error":true,"tool_use_id":"toolu_0152r4A1zXiyDfoLjo96k6MQ"}]},"parent_tool_use_id":null,"session_id":"445221e1-c8d6-48c8-9a49-e5548194d6e8","uuid":"bb7c1ad4-93f5-41e3-b48f-8f2840a6393a","timestamp":"2026-10-11T05:40:29.390Z","tool_use_result":"Error: Skill daybreak-synthetic-probe cannot be used with Skill tool due to disable-model-invocation. Ask the user to run /daybreak-synthetic-probe themselves — it cannot be invoked via the Skill tool. Do not replicate this skill's workflow by other means — it is reserved for explicit user invocation."}
{"type":"assistant","message":{"model":"claude-opus-5-5","id":"msg_011CfuuwETkcVJPUY54HPvdQ","type":"message","role":"assistant","content":[{"type":"text","text":"I couldn't get an instruction result: the `daybreak-synthetic-probe` skill is blocked from being invoked through the Skill tool (`disable-model-invocation` is set), so the call returned an error rather than the skill's instructions.\n\nTo run it, type `/daybreak-synthetic-probe` yourself. No files were modified and nothing outside the project was read."}],"container":null,"stop_reason":null,"stop_sequence":null,"stop_details":null,"usage":{"input_tokens":2,"cache_creation_input_tokens":192,"cache_read_input_tokens":4804,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":192},"output_tokens":120,"service_tier":"standard","inference_geo":"global"},"input_transformations":[],"diagnostics":null,"context_management":null},"parent_tool_use_id":null,"session_id":"445221e1-c8d6-48c8-9a49-e5548194d6e8","uuid":"09c64652-a4d5-4c34-bf6b-2ef86e7eddef","timestamp":"2026-10-11T05:40:30.957Z","request_id":"req_011CfuuwEDcw9AXBynbPU7nn"}
{"duration_api_ms":2501,"stop_reason":"end_turn","session_id":"445221e1-c8d6-48c8-9a49-e5548194d6e8","total_cost_usd":0.033082200000000006,"usage":{"input_tokens":4,"cache_creation_input_tokens":3529,"cache_read_input_tokens":6271,"output_tokens":179,"output_tokens_details":{"thinking_tokens":0},"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":3529,"ephemeral_5m_input_tokens":0},"inference_geo":"global","iterations":[{"input_tokens":2,"output_tokens":120,"cache_read_input_tokens":4804,"cache_creation_input_tokens":192,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":192},"type":"message"}],"speed":"standard","fallback_credit":null},"modelUsage":{"claude-opus-5-5":{"inputTokens":4,"outputTokens":179,"cacheReadInputTokens":6271,"cacheCreationInputTokens":3529,"webSearchRequests":0,"costUSD":0.033082200000000006,"contextWindow":1000000,"maxOutputTokens":128000,"thinkingTokens":0,"canonicalModel":"claude-opus-5-5","provider":"firstParty","costBasis":"list"}},"permission_denials":[],"terminal_reason":"completed","fast_mode_state":"off","fast_mode_disabled_reason":"sdk_opt_in_required","subagent_stats":{"spawned":0,"requested":{"background":0,"foreground":0,"unset":0},"started_in_background":0,"max_depth":0,"spawned_by_subagents":0,"completed":0,"failed":0,"killed":{"parent":0,"user":0,"system":0},"refused":{"depth_limit":0,"concurrency_limit":0,"budget":0},"by_type":{}},"safety_stops":0,"is_error":false,"num_turns":2,"subtype":"success","api_error_status":null,"result":"I couldn't get an instruction result: the `daybreak-synthetic-probe` skill is blocked from being invoked through the Skill tool (`disable-model-invocation` is set), so the call returned an error rather than the skill's instructions.\n\nTo run it, type `/daybreak-synthetic-probe` yourself. No files were modified and nothing outside the project was read.","ttft_ms":964,"type":"result","duration_ms":2561,"uuid":"a7b03aad-7e2b-49f4-a368-4c05a1fcc7a0","ttft_stream_ms":646,"time_to_request_ms":45,"first_content_frame_ms":646,"queued_turn_count":0,"result_index":0}
```

## H-U-2

Fixture:

```markdown
---
name: daybreak-synthetic-probe
description: Return the synthetic probe result. Metadata marker META_cb9e6e42d573e731.
disable-model-invocation: true
---

Return exactly BODY_fc2f44a499690563 and nothing else. Do not use tools or take any further action.
```

Explicit settings:

```json
{
  "disableAllHooks": true,
  "disableBundledSkills": true,
  "includeGitInstructions": false,
  "enabledPlugins": {}
}
```

Invocation and completion:

```json
{
  "start": {
    "pid": 2730735,
    "started": "2026-10-11T05:40:30.269300+00:00",
    "version": "2.1.296 (Claude Code)",
    "argv": [
      "<wrapper-bin>/claude",
      "-p",
      "--model",
      "claude-opus-5-5",
      "--effort",
      "low",
      "--tools",
      "Skill",
      "--allowedTools",
      "Skill",
      "--strict-mcp-config",
      "--mcp-config",
      "{\"mcpServers\":{}}",
      "--setting-sources",
      "project",
      "--settings",
      "<scratch>/w13/settings.json",
      "--permission-mode",
      "dontAsk",
      "--permission-prompts",
      "none",
      "--no-chrome",
      "--no-session-persistence",
      "--output-format",
      "stream-json",
      "--verbose",
      "/daybreak-synthetic-probe"
    ],
    "fixtures": {
      ".claude/skills/daybreak-synthetic-probe/SKILL.md": "b48643cbcca7533c5fc95b925124ce24eb98c518779743155bf0d4131b6391c7",
      "settings.json": "321736be13fdb53eac761bf2273332b1cae2cd860989814f8661c9e0496a7d0d"
    }
  },
  "result": {
    "arm": "H-U-2",
    "exit_code": 0,
    "timed_out": false,
    "started": "2026-10-11T05:40:30.269300+00:00",
    "finished": "2026-10-11T05:40:32.259428+00:00",
    "fixtures_unchanged": true,
    "stdout_sha256": "2840d8a3f5c830219739d241788052f1d5243ea9f62dfb1c6f7f3bc27f8fce11",
    "stderr_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  }
}
```

Observed events:

```jsonl
{"type":"system","subtype":"init","model":"claude-opus-5-5","tools":["Skill"],"skills":["daybreak-synthetic-probe","design","doctor","plugin-authoring"],"plugins":[{"name":"cc-plugin-agents-md","path":"builtin","source":"cc-plugin-agents-md@builtin"},{"name":"cc-plugin-telemetry","path":"builtin","source":"cc-plugin-telemetry@builtin"},{"name":"cc-plugin-plugin-authoring","path":"builtin","source":"cc-plugin-plugin-authoring@builtin"}],"claude_code_version":"2.1.296"}
{"type":"assistant","message":{"model":"claude-opus-5-5","id":"msg_011CfuuwMFnVNjW1tKrydnGx","type":"message","role":"assistant","content":[{"type":"text","text":"BODY_fc2f44a499690563"}],"container":null,"stop_reason":null,"stop_sequence":null,"stop_details":null,"usage":{"input_tokens":2,"cache_creation_input_tokens":3429,"cache_read_input_tokens":1467,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":3429},"output_tokens":8,"service_tier":"standard","inference_geo":"global"},"input_transformations":[],"diagnostics":null,"context_management":null},"parent_tool_use_id":null,"session_id":"eebdec9e-7a02-44d8-af17-152be1b93779","uuid":"3bc61114-f7ea-4986-9307-681a996af411","timestamp":"2026-10-11T05:40:31.579Z","request_id":"req_011CfuuwM1ethZ8QrPVPRMUa"}
{"duration_api_ms":581,"stop_reason":"end_turn","session_id":"eebdec9e-7a02-44d8-af17-152be1b93779","total_cost_usd":0.0280334,"usage":{"input_tokens":2,"cache_creation_input_tokens":3429,"cache_read_input_tokens":1467,"output_tokens":15,"output_tokens_details":{"thinking_tokens":0},"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":3429,"ephemeral_5m_input_tokens":0},"inference_geo":"global","iterations":[{"input_tokens":2,"output_tokens":15,"cache_read_input_tokens":1467,"cache_creation_input_tokens":3429,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":3429},"type":"message"}],"speed":"standard","fallback_credit":null},"modelUsage":{"claude-opus-5-5":{"inputTokens":2,"outputTokens":15,"cacheReadInputTokens":1467,"cacheCreationInputTokens":3429,"webSearchRequests":0,"costUSD":0.0280334,"contextWindow":1000000,"maxOutputTokens":128000,"thinkingTokens":0,"canonicalModel":"claude-opus-5-5","provider":"firstParty","costBasis":"list"}},"permission_denials":[],"terminal_reason":"completed","fast_mode_state":"off","fast_mode_disabled_reason":"sdk_opt_in_required","subagent_stats":{"spawned":0,"requested":{"background":0,"foreground":0,"unset":0},"started_in_background":0,"max_depth":0,"spawned_by_subagents":0,"completed":0,"failed":0,"killed":{"parent":0,"user":0,"system":0},"refused":{"depth_limit":0,"concurrency_limit":0,"budget":0},"by_type":{}},"safety_stops":0,"is_error":false,"num_turns":1,"subtype":"success","api_error_status":null,"result":"BODY_fc2f44a499690563","ttft_ms":661,"type":"result","duration_ms":683,"uuid":"8b9d6f5e-b843-451f-b3bc-4fc9f83df265","ttft_stream_ms":622,"time_to_request_ms":101,"first_content_frame_ms":622,"queued_turn_count":0,"result_index":0}
```
