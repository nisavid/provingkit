# Install or update Provingkit Alpha 6

Download one plugin ZIP for your account, check its checksum, and upload it through that account’s plugin controls. Repeat for each plugin you need; installing all six gives you the complete Kit and its cooperating workflows.

## Get the files

Use the [Alpha 6 download table](https://github.com/nisavid/provingkit/releases/tag/v0.1.0-alpha.6). Choose `agent-plugins.zip` for an OpenAI account or `claude.zip` for Claude. Keep the ZIP intact. The automatic **Source code** archives are not uploadable plugin packages.

For a smaller installation, include the companions used by your workflow. Tricritical review uses Rolecasting for its reviewers. Mergecraft’s PR publication uses Versionkeeping for Git publication and Tricritical with Rolecasting for required reviews. Artifact Customs workflows call those delegation, review, Git, and PR owners as needed. The [plugin front pages](https://github.com/nisavid/provingkit/tree/v0.1.0-alpha.6/plugins) describe the individual workflows; download the same target format for their companions.

Use the version-pinned copy of this guide linked from the repository README for the expected hashes below. From the directory containing your downloaded ZIP, calculate its SHA-256 on Linux:

```sh
sha256sum provingkit-rolecasting-0.1.0-alpha.6-agent-plugins.zip
```

On macOS:

```sh
shasum -a 256 provingkit-rolecasting-0.1.0-alpha.6-agent-plugins.zip
```

Use the matching filename for the plugin and target you downloaded. **Compare the printed hash and filename with the matching row below before uploading.** Stop if the file is missing or either value differs. A matching hash confirms that the ZIP matches the bytes recorded in this guide revision. The release is unsigned; this check does not authenticate the publisher.

The release also supplies adjacent `.sha256` files. A sidecar can be replaced alongside its ZIP, so agreement between those two downloads alone does not establish a match to this guide's recorded bytes.

<details>
<summary>Expected ZIP hashes for Alpha 6</summary>

| ZIP filename | Expected SHA-256 |
| --- | --- |
| `provingkit-artifact-customs-0.1.0-alpha.6-agent-plugins.zip` | `f752c1d8e305c4daf082038666ab7d17908fe88f88238ce3b9fbe6b0ee90d021` |
| `provingkit-artifact-customs-0.1.0-alpha.6-claude.zip` | `b40e3a5de0fe767c790d7da55ab4a1ac86210a98bf1c5df1fd2b2487e417fef5` |
| `provingkit-mergecraft-0.1.0-alpha.6-agent-plugins.zip` | `906859a449973c58cecba4a5dc537f95e99edf8d7ce7b96c34a79be17960f567` |
| `provingkit-mergecraft-0.1.0-alpha.6-claude.zip` | `84cd390f83619c8622ac838c48707a5f430e76c617b6725b0d0370aa40c834ad` |
| `provingkit-proseweaving-0.1.0-alpha.6-agent-plugins.zip` | `3fcddaabc5ea060bb373b8d4739e5bf2278fdbcb5ac210697a8486ad90ba1118` |
| `provingkit-proseweaving-0.1.0-alpha.6-claude.zip` | `f77a2c0e2f1d1104077c490c2b9bc1e1e59503c99fa05bd525c8370bd1703211` |
| `provingkit-rolecasting-0.1.0-alpha.6-agent-plugins.zip` | `55729c44795ccf9772d5f2ea88a5e58e201f034fbfe79f90cacaf39af9e7afe8` |
| `provingkit-rolecasting-0.1.0-alpha.6-claude.zip` | `7117b08cc7152eb0a2594e7b0d14505cdea0cba203e67a21a7c845f6c1327215` |
| `provingkit-tricritical-0.1.0-alpha.6-agent-plugins.zip` | `2a155de664e167c07426ff5bc09dd9b4893a6baa3d088b677f81aef9681767ac` |
| `provingkit-tricritical-0.1.0-alpha.6-claude.zip` | `baf0b91f085a83dab311d4b8104564fff712140865f5d39e66222319f7395751` |
| `provingkit-versionkeeping-0.1.0-alpha.6-agent-plugins.zip` | `e0ac9cb67032943814fb25f7a407e050ecbe7f1a880d9fd64bc0f22b3d510a42` |
| `provingkit-versionkeeping-0.1.0-alpha.6-claude.zip` | `90e241d5a599bcc035e48748bd4e084daed3d255d44d379fdec10eb4a877c9a8` |

</details>

## ChatGPT and Codex account plugins

Open ChatGPT in a web browser and confirm the intended account or workspace. These steps require its plugin upload and installation controls to be available; if your workspace does not expose them, check with its administrator. For a new plugin:

1. Open the profile icon at the bottom of the menu bar, then **Settings → Plugins → Browse directory**.
2. Choose **Add → Upload plugin archive**.
3. Select or drag in the checked Agent Plugins ZIP, then choose **Add plugin**.
4. Choose **Install plugin**, then check the saved version is `0.1.0-alpha.6` and the plugin appears in **Installed**.

Start a new chat or Codex session after installation. If the plugin was uploaded earlier but is not installed, open its details and use the plus button. [OpenAI’s plugin guide](https://learn.chatgpt.com/docs/plugins#use-and-install-plugins) describes installation and fresh-session loading.

**Update an earlier account upload:** open the existing uploaded plugin, choose **More actions → Upload new version**, and select that plugin’s checked Agent Plugins ZIP. Check the saved version and the separate Installed listing after completing the displayed controls. Keep the previous archive and configuration until you have confirmed the result. An upload does not itself prove installation, enablement, or successful loading.

**Coming from the older preview:** its guide registered a local marketplace. These web controls manage an account upload, so use the new-plugin steps if you choose that delivery route. They do not establish migration of your local installation or which same-named copy your client selects. Keep the existing installation and configuration until you have confirmed the Alpha 6 version and skills in a fresh session; if you cannot establish which copy loaded, stop before removing either copy.

The first-upload navigation follows a firsthand walkthrough recorded on November 3, 2026. On November 6, the update route above produced Alpha 6 saved versions and Installed entries for all six plugins across four personal ChatGPT accounts. Those observations do not establish fresh-session loading, complete preservation, or rollback. Account and workspace controls can differ; these instructions do not use the separate public plugin-submission portal.

## Claude account plugins

Open Claude in a web browser. On Team and Enterprise plans, an organization Owner controls whether members can add their own plugins; confirm uploads are permitted before proceeding.

1. Confirm the intended account and organization. Open the profile badge at the bottom of the menu drawer, then **Settings → Customize → Plugins**. Some interfaces expose **Plugins** directly.
2. Choose **Add → Upload plugin**, then select or drag in the checked Claude ZIP.
3. Choose **Upload**. Open the saved plugin and check its version, components, and enabled state.
4. In chat, type `/` to select a skill. Start a new Cowork task to load its components there.

Anthropic documents ZIP uploads containing one `.claude-plugin/plugin.json` and records the installation on the selected account and organization. Chat exposes skills, commands, and connectors; Cowork also loads agents. Do not assume an upload makes every plugin component available in every app. [Claude’s plugin guide](https://claude.com/docs/plugins/overview#find-and-add-a-plugin) describes those controls and supported surfaces.

For Claude Code account sync, use a terminal session signed in to the same Claude account with version 2.1.273 or later. Sync runs at startup; use `/reload-plugins` after a sync notification or start another session. Check the selected origin: an enabled local plugin with the same manifest name can take precedence over the synced copy. [Claude Code’s loading guide](https://code.claude.com/docs/en/plugins/loading#synced-plugins) covers sign-in restrictions, sync timing, and name conflicts.

**Update an earlier personal upload:** upload the matching checked Claude ZIP. When **Replace existing plugin?** identifies the intended plugin, choose **Replace**, then reopen its details and check the saved version and enabled state. Stop if the named plugin is wrong or the replacement control is absent. This same-name route produced Alpha 6 saved versions and enabled entries for all six plugins across three personal Claude accounts on November 6, 2026. Keep the previous archive and configuration: those observations do not establish preserved backend identifiers or all contents, fresh-session loading, or rollback. Marketplace update controls apply to marketplace installations, not automatically to uploaded ZIPs.

## Confirm the installation

For each receiving account and client, check the saved version, installed/enabled state, and availability in a fresh session. Then use a relevant skill on a real task—for example, ask the agent to use Tricritical to review a change or Proseweaving to revise a document.

If the expected version or skills are absent, record the client, plugin, filename, and visible error before making another account change. A saved version alone does not establish successful loading. Provider-specific recovery and rollback must follow the supported controls for that account.

These are manual account-upload instructions. They do not register a repository marketplace, promise automatic Provingkit upgrades, or qualify every plugin component on every client.
