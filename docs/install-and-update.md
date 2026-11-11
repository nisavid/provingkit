# Install or update Provingkit

This guide covers installing and updating Provingkit in Codex, Claude Code,
ChatGPT, and Claude.

## Download

Download the plugins you want from [Releases](https://github.com/nisavid/provingkit/releases).
Choose the standard plugin ZIPs for **Codex or ChatGPT**, or the files ending
in `-claude.zip` for **Claude Code or Claude**. GitHub's **Source code** archives
are for development.

The release page lists the plugins available in that release. For partial
installs, these common workflows need companions in the same format:

- **Tricritical reviews:** include Rolecasting.
- **Mergecraft PR publication:** include Tricritical and Rolecasting for review,
  plus Versionkeeping for commits and pushes.
- **Artifact Customs:** add Rolecasting for delegation, Tricritical for review,
  Versionkeeping for Git, and Mergecraft for PRs, as your workflow needs.

## Codex CLI

Register the downloaded plugins in a local marketplace. This example installs
Rolecasting; add an entry for each plugin you want.

1. Create a `provingkit-release` folder. Inside it, extract the standard
   Rolecasting ZIP into `plugins/rolecasting`, so that
   `plugins/rolecasting/plugin.json` exists.
2. Create `provingkit-release/.agents/plugins/marketplace.json`:

   ```json
   {
     "name": "provingkit-release",
     "plugins": [
       {
         "name": "rolecasting",
         "source": {"source": "local", "path": "./plugins/rolecasting"},
         "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
         "category": "Productivity"
       }
     ]
   }
   ```

3. From the folder containing `provingkit-release`, run:

   ```sh
   codex plugin marketplace add ./provingkit-release
   codex plugin add rolecasting@provingkit-release
   ```

For additional plugins, extract each ZIP into its own `plugins/<name>` folder,
add its name and path to the catalog, and install it through `/plugins` or
`codex plugin add NAME@provingkit-release`, replacing `NAME` with the plugin's
name. Start a new session to use it.

To update a plugin, remove its installed copy before replacing its extracted
folder, then install it again and start a new session. Replace `NAME` with the
plugin name:

```sh
codex plugin remove NAME@provingkit-release
# Replace plugins/NAME with a fresh extraction of its new ZIP.
codex plugin add NAME@provingkit-release
codex plugin list --marketplace provingkit-release --json
```

Check that the installed version matches the release you downloaded.

See the [Codex plugin commands](https://learn.chatgpt.com/docs/cli/reference#codex-plugin)
and [local marketplace format](https://developers.openai.com/plugins/build/plugins#install-a-local-plugin-manually).

## Claude Code

To load a downloaded Claude ZIP for one session:

```sh
claude --plugin-dir ./plugin-claude.zip
```

Replace the example filename with your download. Repeat `--plugin-dir` for
each companion plugin. To update, start the next session with the new ZIPs.

For persistent installation, [upload the Claude ZIPs to your account](#claude-web-and-desktop).
Claude Code 2.1.273 or later syncs them when signed in with the same Claude
account. Start Claude Code, wait for the sync notification, then run
`/reload-plugins` or start a new session. Updates sync after you replace the
account's uploaded ZIPs. API-key and cloud-provider sessions do not use account
sync.

See [session plugin flags](https://code.claude.com/docs/en/cli-reference#cli-flags)
and [account sync](https://code.claude.com/docs/en/plugins/loading#synced-plugins).

## ChatGPT

Upload the compressed ZIP through [ChatGPT on the web](https://chatgpt.com/):

| Action | Steps |
| --- | --- |
| **Install** | Open **Plugins**, select **Personal**, then choose **Add** and **Upload plugin archive**. Select the ZIP, then choose **Add plugin** and **Install plugin** when prompted. |
| **Update an uploaded ZIP** | Open the existing plugin, then choose **More actions**, **Upload new version**, and **Choose file**. Select the new ZIP. |

If the plugin is not in **Installed**, open its details and select **+** to
install it. After an update, check that its displayed version matches the release
you downloaded. Start a new chat in the web or **ChatGPT desktop app** and use
`@` to select a skill, or ask for it by name.

See [ChatGPT's plugin guide](https://learn.chatgpt.com/docs/plugins#use-and-install-plugins).

## Claude web and desktop

In [Claude on the web](https://claude.ai/) or the **Claude desktop app**:

1. Open **Customize**, then **Plugins**. Choose **Add**, then **Upload plugin**.
2. Select the compressed Claude ZIP, then choose **Upload**. When updating, confirm
   **Replace** for the existing plugin and check that its displayed version
   matches the release you downloaded.
3. Enable the plugin, then start a new chat and type `/` to find its skills,
   or start a new Cowork task.

See [Claude's plugin guide](https://claude.com/docs/plugins/overview#find-and-add-a-plugin).

## If a skill is missing

Check that the plugin is installed or enabled, then try a new session.
In Claude Code, check `/plugin` for a same-named local or marketplace copy
that takes precedence over an account-synced plugin.
If the problem persists, [search existing reports](https://github.com/nisavid/provingkit/issues).
Add details to a matching report, or open a new one with the app, plugin,
version, and error message.

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
