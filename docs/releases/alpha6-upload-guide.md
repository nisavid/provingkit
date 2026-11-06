# Install or update Provingkit Alpha 6

Download one plugin ZIP for your account, check its checksum, and upload it through that account’s plugin controls. Repeat for each plugin you need; installing all six gives you the complete Kit and its cooperating workflows.

## Get the files

Use the [Alpha 6 download table](https://github.com/nisavid/provingkit/releases/tag/v0.1.0-alpha.6). Choose `agent-plugins.zip` for an OpenAI account or `claude.zip` for Claude, and download the adjacent `.sha256` file. Keep the ZIP intact. The automatic **Source code** archives are not uploadable plugin packages.

For a smaller installation, include the companions used by your workflow. Tricritical review uses Rolecasting for its reviewers. Mergecraft’s PR publication uses Versionkeeping for Git publication and Tricritical with Rolecasting for required reviews. Artifact Customs workflows call those delegation, review, Git, and PR owners as needed. The [plugin front pages](https://github.com/nisavid/provingkit/tree/v0.1.0-alpha.6/plugins) describe the individual workflows; download the same target format for their companions.

Put a ZIP and its checksum file in the same directory. From that directory, verify it on Linux:

```sh
sha256sum -c provingkit-rolecasting-0.1.0-alpha.6-agent-plugins.zip.sha256
```

On macOS:

```sh
shasum -a 256 -c provingkit-rolecasting-0.1.0-alpha.6-agent-plugins.zip.sha256
```

Use the matching filename for the plugin and target you downloaded. The result should name that ZIP and say `OK`. Stop if a file is missing or differs. A matching checksum verifies the download’s bytes; the release is unsigned.

## ChatGPT and Codex account plugins

Open ChatGPT in a web browser and confirm the intended account or workspace. These steps require its plugin upload and installation controls to be available; if your workspace does not expose them, check with its administrator. For a new plugin:

1. Open the profile icon at the bottom of the menu bar, then **Settings → Plugins → Browse directory**.
2. Choose **Add → Upload plugin archive**.
3. Select or drag in the checked Agent Plugins ZIP, then choose **Add plugin**.
4. Choose **Install plugin**, then check the saved version is `0.1.0-alpha.6` and the plugin appears in **Installed**.

Start a new chat or Codex session after installation. If the plugin was uploaded earlier but is not installed, open its details and use the plus button. [OpenAI’s plugin guide](https://learn.chatgpt.com/docs/plugins#use-and-install-plugins) describes installation and fresh-session loading.

**Update:** open the existing plugin, choose **More actions → Upload new version**, and select that plugin’s checked Agent Plugins ZIP. Check the saved version and the separate Installed listing after completing the displayed controls. Keep the previous archive and configuration until you have confirmed the result. An upload does not itself prove installation, enablement, or successful loading.

The first-upload navigation follows a firsthand walkthrough recorded on November 3, 2026. Account and workspace controls can differ. Replacement and rollback behavior have not been verified across accounts; these instructions do not use the separate public plugin-submission portal.

## Claude account plugins

Open Claude in a web browser. On Team and Enterprise plans, an organization Owner controls whether members can add their own plugins; confirm uploads are permitted before proceeding.

1. Confirm the intended account and organization. Open the profile badge at the bottom of the menu drawer, then **Settings → Customize → Plugins**. Some interfaces expose **Plugins** directly.
2. Choose **Add → Upload plugin**, then select or drag in the checked Claude ZIP.
3. Choose **Upload**. Open the saved plugin and check its version, components, and enabled state.
4. In chat, type `/` to select a skill. Start a new Cowork task to load its components there.

Anthropic documents ZIP uploads containing one `.claude-plugin/plugin.json` and records the installation on the selected account and organization. Chat exposes skills, commands, and connectors; Cowork also loads agents. Do not assume an upload makes every plugin component available in every app. [Claude’s plugin guide](https://claude.com/docs/plugins/overview#find-and-add-a-plugin) describes those controls and supported surfaces.

For Claude Code account sync, use a terminal session signed in to the same Claude account with version 2.1.273 or later. Sync runs at startup; use `/reload-plugins` after a sync notification or start another session. Check the selected origin: an enabled local plugin with the same manifest name can take precedence over the synced copy. [Claude Code’s loading guide](https://code.claude.com/docs/en/plugins/loading#synced-plugins) covers sign-in restrictions, sync timing, and name conflicts.

For an existing personally uploaded plugin, the checked documentation does not establish a replacement or rollback procedure. Keep its archive and configuration, and follow the account’s current controls rather than assuming another same-name upload replaces it. Marketplace update controls apply to marketplace installations, not automatically to uploaded ZIPs.

## Confirm the installation

For each receiving account and client, check the saved version, installed/enabled state, and availability in a fresh session. Then use a relevant skill on a real task—for example, ask the agent to use Tricritical to review a change or Proseweaving to revise a document.

If the expected version or skills are absent, record the client, plugin, filename, and visible error before making another account change. A saved version alone does not establish successful loading. Provider-specific recovery and rollback must follow the supported controls for that account.

These are manual account-upload instructions. They do not register a repository marketplace, promise automatic Provingkit upgrades, or qualify every plugin component on every client.
