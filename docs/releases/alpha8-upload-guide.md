# Install or update Provingkit Alpha 8

Choose the ZIP for your account, compare it with the expected SHA-256, and
upload it through the account's plugin controls. Check the version and try a
skill in a fresh session. These are manual steps for Alpha 8.
Find the downloads on the [GitHub release page](https://github.com/nisavid/provingkit/releases/tag/v0.1.0-alpha.8).
The account steps draw on the
[Alpha 6 upload guide](https://github.com/nisavid/provingkit/blob/c557b9471f74afa82df8622313282808911453f7/docs/releases/alpha6-upload-guide.md)
and the providers' documented loading behavior. Alpha 8 account uploads and
fresh-session loading still need verification.

## Choose the plugins

Select `-agent-plugins.zip` for an OpenAI account or `-claude.zip` for a
Claude account. Keep each ZIP intact for upload. GitHub's automatic **Source
code** archives contain the repository source.

Install all seven plugins for the complete Kit, or choose the ones you use
and include their companions in the same target format.

| If you use | Include |
| --- | --- |
| Tricritical for independent review | Rolecasting for reviewer selection and dispatch |
| Mergecraft for PR publication | Versionkeeping for Git publication, plus Tricritical and Rolecasting when independent review is required |
| Artifact Customs workflows that delegate, review, publish Git work, or publish a PR | The Rolecasting, Tricritical, Versionkeeping, and Mergecraft companions those steps call |
| Addressed peer messaging | Surreal Intercom, which can be used independently of Rolecasting |

Intercom needs the chosen recipient's binding, permission to act, and a
protected local mailbox and capture location. Its Claude-receiving route needs
a nominated Claude MCP child with `SendMessage`. Its Codex-receiving routes
need access to local Codex IPC, and the Daybreak route also needs native Codex
controls to create and read a local child. Current-app compatibility and live
delivery remain unqualified.

Inspect the intended account's plugin list before choosing a first upload or
replacement for Intercom. Earlier local records showed no Intercom in either
Desktop selection. Its cloud catalog status remains unknown.

## Verify the ZIP

From the download directory, run the command for your platform with the
filename of the ZIP you downloaded. This example checks Surreal Intercom's
Agent Plugins archive.

Linux

```sh
sha256sum provingkit-surreal-intercom-0.1.0-alpha.8-agent-plugins.zip
```

macOS

```sh
shasum -a 256 provingkit-surreal-intercom-0.1.0-alpha.8-agent-plugins.zip
```

Windows PowerShell

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath 'provingkit-surreal-intercom-0.1.0-alpha.8-agent-plugins.zip' | Format-List
```

On Windows, compare `Hash` and the filename at the end of `Path`. Hexadecimal
letter case makes no difference. Match both the filename and digest to the
table. If either differs or the file is missing, stop before uploading.
The release is unsigned. A match verifies the archive against the
bytes recorded here. Use this table as the expected value even if you also
downloaded the archive's checksum sidecar.

<details>
<summary>Expected ZIP hashes for Alpha 8</summary>

| ZIP filename | Expected SHA-256 |
| --- | --- |
| `provingkit-artifact-customs-0.1.0-alpha.8-agent-plugins.zip` | `8852ffc7e3b66b5757626f0dd435fec5781bdfb421977f233e556912a43a9e55` |
| `provingkit-artifact-customs-0.1.0-alpha.8-claude.zip` | `f988c7c47c4728b1516811eae86b363fcf7241c38e72fe159e60c768d18fcfa0` |
| `provingkit-mergecraft-0.1.0-alpha.8-agent-plugins.zip` | `e17fbb8141815ae685ee5986ed48c4c7676c493511aa796b1f0b585d7b7e96a1` |
| `provingkit-mergecraft-0.1.0-alpha.8-claude.zip` | `15a31c9bc87331fb9ff30c8e820688bb0072443311bac3350df5eae3c93228da` |
| `provingkit-proseweaving-0.1.0-alpha.8-agent-plugins.zip` | `28111f89aa98a61f2aeb82a8e8b013a52a64fc492568922273bf77ad033583eb` |
| `provingkit-proseweaving-0.1.0-alpha.8-claude.zip` | `02a10e205f23c71760509129277c49f27238a0fb4349552265ee227f4bda304d` |
| `provingkit-rolecasting-0.1.0-alpha.8-agent-plugins.zip` | `faf030f482911256f9d78141a8fb2d545dac3765c4aeae27dab5cbb1e484a59c` |
| `provingkit-rolecasting-0.1.0-alpha.8-claude.zip` | `851bd7bc9556137a5908dac527e577ad3fd2b01674a59e1ac57340225d3fc72f` |
| `provingkit-surreal-intercom-0.1.0-alpha.8-agent-plugins.zip` | `2bb4387fed1af1e224f7f8b812c68f73f9848cb634780dc8dd44c33fe6413d07` |
| `provingkit-surreal-intercom-0.1.0-alpha.8-claude.zip` | `134a78fb0556af56bba1c2ee187018d60dc1e02628b5b44707ecf5df7fb011d0` |
| `provingkit-tricritical-0.1.0-alpha.8-agent-plugins.zip` | `0946e5424f0e05738171b2bdd553d956808f7ece10e2e05f8b61edfe004aef85` |
| `provingkit-tricritical-0.1.0-alpha.8-claude.zip` | `b93f1eaed831c7e525534e6cc0a0affdb593beb0827e78730dccb349c0673c94` |
| `provingkit-versionkeeping-0.1.0-alpha.8-agent-plugins.zip` | `5414eb321b0e22065985b6444948c0d5e899274605526f3afe27be0c33364168` |
| `provingkit-versionkeeping-0.1.0-alpha.8-claude.zip` | `acc998c03818036c1bebc0c63a2a7d474e9177d0a4c6ecdb77812838f3e28301` |

</details>

## ChatGPT personal account

Open ChatGPT in a browser, confirm the intended personal account, and inspect
its plugin list. Use the verified Agent Plugins ZIP for the corresponding
plugin.

**Update an existing entry.** Open its details. Choose **More actions**,
**Upload new version**, then **Choose file**. Select the ZIP. After upload,
check that the same entry shows version `0.1.0-alpha.8` and appears in
**Installed**. The Alpha 6 run used this route across four personal accounts.
Those updates retained the entry IDs and URLs and showed **Installed**.

**Add a plugin for the first time.** The observed entry point is **Plugins**,
**Personal**, **Add**, then **Upload plugin archive**. Use this branch if
the intended account has no corresponding entry. After choosing the ZIP,
follow the controls shown and check the resulting entry's identity, personal
scope, and version. First-upload submission, audience, and the transition
to **Installed** remain unverified. Once the intended entry exists, check whether it is installed and start a new
chat to verify loading. See [OpenAI's plugin guide](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt) for current installation controls.

If you have a copy from the pinned preview's local marketplace, keep that copy
and its configuration until you identify which origin the receiving client
loads.

### Codex Desktop

Confirm that Codex Desktop is signed in to the intended account. After the
account upload, check the plugin's selected origin and version where Desktop
shows them, then look for the expected skill in a fresh session. Earlier
local install markers matched the six Alpha 6 cloud entry IDs, and cached
manifests showed Alpha 6. The Desktop update and refresh controls, sync timing,
current enabled state, and fresh-session loading remain unverified. A first
Intercom upload still needs its own Desktop availability check.

## Claude personal account

Open Claude in a browser, confirm the intended account and organization, and
inspect its plugin list. On Team and Enterprise, an organization Owner
controls whether members can add their own plugins. Use the verified Claude
ZIP for the corresponding plugin.

**Update an existing personal upload.** Open **Customize**, **Plugins**,
**Add**, then **Upload plugin**. Some interfaces expose **Plugins** directly.
Select the ZIP and use **Replace existing** when offered. Choose **Replace**
only when the confirmation names the intended plugin. Stop if the expected
confirmation is missing or names another plugin. Check that there is one entry
for that plugin, that it shows version `0.1.0-alpha.8`, and that it is enabled.
This route left one enabled Alpha 6 entry per target across three personal
accounts. Backend entry identity preservation remains unverified.

**Add a plugin for the first time.** Open the same **Upload plugin** control
and select the verified ZIP. Follow the controls shown, then verify the new
entry's account and organization, version, components, and enabled state.
The Alpha 6 replacement run leaves the new-entry confirmation and permissions
flow unverified. Claude documents choosing a skill with `/` in a new chat and
loading available components in a new Cowork task. See
[Claude's plugin guide](https://claude.com/docs/plugins/overview#find-and-add-a-plugin).

### Claude Desktop

Confirm the intended account and organization in Claude Desktop. After the
account upload, check the selected plugin version and enabled state in the
Desktop mode you use. Then check which components appear in a fresh session
in that mode. Earlier local-agent metadata recorded six Alpha 6 plugins
selected and enabled under **My Uploads**. The Desktop update and refresh
controls, sync timing, current enabled state, and fresh-session loading remain
unverified. Intercom's Claude ZIP targets Claude Code. Its availability in
Claude Desktop still needs a separate observation.

### Claude Code account sync

Anthropic documents account sync in Claude Code 2.1.273 or later when you
sign in with the same Claude account. The `syncClaudeAiPlugins` setting can
disable that sync. After startup and a sync notification, run
`/reload-plugins` or start another session. Check the loaded origin in the
Installed tab of `/plugin`. An enabled same-name local plugin can take
precedence over the synced one. See
[Claude Code's synced-plugin guidance](https://code.claude.com/docs/en/plugins/loading#synced-plugins).

## Confirm loading and recover an incomplete update

For each account and client you use, check the saved version, the installed
or enabled state, and whether the expected skills are available in a fresh
session. Where the client exposes a loaded version or origin, compare that
with the intended copy. Try a small skill task, such as asking Proseweaving
to tighten one paragraph. For Surreal Intercom, you can check skill discovery
by asking it to identify the recipient binding and required authority in a
hypothetical exchange. Live message delivery and Daybreak remain separate
checks.

When moving messaging callers from Rolecasting to Surreal Intercom, load
`surreal-intercom:communicating-with-agents` from the intended installation.
Keep any existing mailbox, pinned resources, and attempt references until
you've confirmed the new caller binding. Reconcile uncertain sends through
their original records.

Keep the previous verified ZIP and configuration until the update is confirmed.
If the expected version or skill is missing, record the account or workspace,
client, plugin name, ZIP filename, origin if shown, and any visible error.
Check for a competing local or synced copy before removing either one. Use
the account's supported enablement or replacement controls to recover. If the
provider offers replacement with the earlier archive, verify the prior version
and skill loading in a fresh session after restoring it. Rollback and settings
preservation remain unverified for Alpha 8.
