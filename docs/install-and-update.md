# Install or update Provingkit

This guide covers installing the current release in ChatGPT and Claude,
updating existing plugins, and making their skills available in a new session.

## Download

Download the plugins you want from [Releases](https://github.com/nisavid/provingkit/releases).
Choose the ZIPs for **ChatGPT** or **Claude**, and leave them compressed.
The files ending in `-claude.zip` are for Claude; use the other plugin ZIPs
for ChatGPT. GitHub's **Source code** archives are for development.

Install all plugins in the release for the complete Kit. For individual
plugins, include the companions listed in their README.

## ChatGPT

Upload through [ChatGPT on the web](https://chatgpt.com/):

| Action | Steps |
| --- | --- |
| **Install** | Open **Plugins**, select **Personal**, then choose **Add** and **Upload plugin archive**. Select the ZIP and complete the upload prompts. |
| **Update** | Open the existing plugin, then choose **More actions**, **Upload new version**, and **Choose file**. Select the new ZIP. |

If the plugin is not in **Installed**, open its details and select **+** to
install it. Start a new chat in the web or **ChatGPT desktop app** and use
`@` to select a skill, or ask for it by name.

See [ChatGPT's plugin guide](https://learn.chatgpt.com/docs/plugins#use-and-install-plugins).

## Claude

In [Claude on the web](https://claude.ai/) or the **Claude desktop app**:

1. Open **Customize**, then **Plugins**. Choose **Add**, then **Upload plugin**.
2. Select the Claude ZIP. When updating, confirm **Replace** for the existing
   plugin.
3. Enable the plugin, then start a new chat and type `/` to find its skills,
   or start a new Cowork task.

See [Claude's plugin guide](https://claude.com/docs/plugins/overview#find-and-add-a-plugin).

### Claude Code

Claude Code 2.1.273 or later syncs uploaded plugins when signed in with the
same Claude account. Start Claude Code, wait for the sync notification, then
run `/reload-plugins` or start a new session. API-key and cloud-provider
sessions do not use this account sync.

If an old or missing skill persists, check `/plugin` for a same-named local
or marketplace copy that takes precedence over `@synced`.
See [Claude Code's sync guidance](https://code.claude.com/docs/en/plugins/loading#synced-plugins).

## If a skill is missing

Check that the plugin is installed or enabled, then try a new session. After
an update, compare the plugin's displayed version with the release you downloaded.
If the problem persists, [report it](https://github.com/nisavid/provingkit/issues)
with the app, plugin, version, and error message.

<details>
<summary>Optional: verify a download</summary>

Compare the ZIP's SHA-256 with its checksum on the release page. Replace
`plugin.zip` below with your downloaded filename.

**Linux**

```sh
sha256sum plugin.zip
```

**macOS**

```sh
shasum -a 256 plugin.zip
```

**Windows PowerShell**

```powershell
Get-FileHash .\plugin.zip -Algorithm SHA256
```

</details>
