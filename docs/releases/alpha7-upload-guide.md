# Install or update Provingkit Alpha 7

Choose the ZIP for your account, compare it with the expected SHA-256, and
upload it through the account's plugin controls. Check the version and try a
skill in a fresh session. These are manual steps for the Alpha 7 candidate.
The [GitHub release page](https://github.com/nisavid/provingkit/releases/tag/v0.1.0-alpha.7) and its downloads are planned.
The account steps draw on the
[Alpha 6 upload guide](https://github.com/nisavid/provingkit/blob/c557b9471f74afa82df8622313282808911453f7/docs/releases/alpha6-upload-guide.md)
and the providers' documented loading behavior. Alpha 7 account uploads and
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
sha256sum provingkit-surreal-intercom-0.1.0-alpha.7-agent-plugins.zip
```

macOS

```sh
shasum -a 256 provingkit-surreal-intercom-0.1.0-alpha.7-agent-plugins.zip
```

Windows PowerShell

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath 'provingkit-surreal-intercom-0.1.0-alpha.7-agent-plugins.zip' | Format-List
```

On Windows, compare `Hash` and the filename at the end of `Path`. Hexadecimal
letter case makes no difference. Match both the filename and digest to the
table. If either differs or the file is missing, stop before uploading.
The release candidate is unsigned. A match verifies the archive against the
bytes recorded here. Use this table as the expected value even if you also
downloaded the archive's checksum sidecar.

<details>
<summary>Expected ZIP hashes for Alpha 7</summary>

| ZIP filename | Expected SHA-256 |
| --- | --- |
| `provingkit-artifact-customs-0.1.0-alpha.7-agent-plugins.zip` | `efe311d36fd3b676f5ee60b7fbcde4b52d24ad13813b3f78990290243fe57e19` |
| `provingkit-artifact-customs-0.1.0-alpha.7-claude.zip` | `673dfacd50c06ef0711cdbe6f9f3214ee805ad8cc9e37cb512d5ddc9ecd16538` |
| `provingkit-mergecraft-0.1.0-alpha.7-agent-plugins.zip` | `4d14d32773878d421a7663338dacf55828cc55a7cbb59eff4a253e820dcf5ea3` |
| `provingkit-mergecraft-0.1.0-alpha.7-claude.zip` | `fa8a99f473d75327ef618b94deb661702de07f81e29a136d9139cc3c10d59f1e` |
| `provingkit-proseweaving-0.1.0-alpha.7-agent-plugins.zip` | `87027b929cbab4cade3fde261f0a05cc2182802f6713b118c6354ee867c59e79` |
| `provingkit-proseweaving-0.1.0-alpha.7-claude.zip` | `7af38e792e3f71f9c9096aa3dd3fb1e491dbfa5c44f606381047d1712ec77105` |
| `provingkit-rolecasting-0.1.0-alpha.7-agent-plugins.zip` | `6e6c247784e7a71920575ba127290c4beb45cde68bd82d2e6130d3440e1c69e0` |
| `provingkit-rolecasting-0.1.0-alpha.7-claude.zip` | `a6f43572138ade690959c09e5b59b27b48c077ee35dd15e0ab150dadf5995415` |
| `provingkit-surreal-intercom-0.1.0-alpha.7-agent-plugins.zip` | `2be6cc01c3246e730da9715c41140cb996da2c731ad5ffd0d236dd6c8b1946fc` |
| `provingkit-surreal-intercom-0.1.0-alpha.7-claude.zip` | `f2fc078787a0f61718c81f2ba64eaa898ab6ebe576997a5a0e147234dd1731ab` |
| `provingkit-tricritical-0.1.0-alpha.7-agent-plugins.zip` | `9145266bc1d05ede2991ddd55646a5fdc0c48422cf2f7eb5508111deddc19e3b` |
| `provingkit-tricritical-0.1.0-alpha.7-claude.zip` | `dccec48fd6af65c045452ec8efb20184f9e465978fa9863faef952bc4df2d71f` |
| `provingkit-versionkeeping-0.1.0-alpha.7-agent-plugins.zip` | `ea8ec1c2f622f19c232e6e6cba09c099644da9d25436ea3b9a98d9596cb5aa2e` |
| `provingkit-versionkeeping-0.1.0-alpha.7-claude.zip` | `190cad271426a8c2a66df535c500c3f78ff0d327be82a59ac9eb4c994dd71043` |

</details>

## ChatGPT personal account

Open ChatGPT in a browser, confirm the intended personal account, and inspect
its plugin list. Use the verified Agent Plugins ZIP for the corresponding
plugin.

**Update an existing entry.** Open its details. Choose **More actions**,
**Upload new version**, then **Choose file**. Select the ZIP. After upload,
check that the same entry shows version `0.1.0-alpha.7` and appears in
**Installed**. The Alpha 6 run used this route across four personal accounts.
Those updates retained the entry IDs and URLs and showed **Installed**.

**Add a plugin for the first time.** The observed entry point is **Plugins**,
**Personal**, **Add**, then **Upload plugin archive**. Use this branch if
the intended account has no corresponding entry. After choosing the ZIP,
follow the controls shown and check the resulting entry's identity, personal
scope, and version. First-upload submission, audience, and the transition
to **Installed** remain unverified. Once the intended entry exists, OpenAI
documents opening its details and using the plus button to install it if
needed, then starting a new chat. See
[OpenAI's plugin guide](https://learn.chatgpt.com/docs/plugins#use-and-install-plugins).

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
for that plugin, that it shows version `0.1.0-alpha.7`, and that it is enabled.
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

Anthropic documents account sync in Claude Code version 2.1.273 or later
with the same signed-in Claude account. API-key and cloud-provider sessions
fall outside this sync route. After startup and a sync notification, run
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
preservation remain unverified for Alpha 7.
