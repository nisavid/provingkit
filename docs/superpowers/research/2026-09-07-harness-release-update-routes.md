# Release and update routes for six target harness surfaces

Observed 2026-09-07, America/New_York.

The six selected surfaces all separate the host product lifecycle from a plugin, extension, or other equipment lifecycle. No reviewed primary source documents one end-to-end operation or receipt that binds the installed host build, the exact loaded equipment bytes, the resolved source revision, and a real invocation. Claude Code exposes the most complete exactness primitives—exact product installation, signed checksum manifests, deterministic plugin-resolution identities, explicit plugin update, and uninstall—but it still has no named plugin rollback command or run-bound plugin digest receipt. [CC-P1], [CC-E1], [CC-E2] ChatGPT Codex, Codex CLI/TUI, Claude Desktop, Cursor desktop, and Cursor Agent CLI each leave at least one of exact selection, rollback, uninstall, resolved-revision visibility, or installed-byte digest undocumented. [OAI-UPDATES], [OAI-PLUGIN-DOC], [OAI-CODEX-MAIN], [CD-P2], [CD-G1], [CUR-DOWNLOAD], [CUR-CLI-PARAMS], [CUR-PLUGIN]

This is a factual mechanism inventory for [`nisavid/provingkit#1`][PK-I1] at repository base `e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08`. It does not select a Provingkit release, adapter, signing, custody, installation, rollback, or deployment policy; establish release eligibility or production readiness; report either target host's state; or authorize installation, publication, signing, credentials, or host mutation. Those boundaries match the repository's separation of source work from release and installation authority. [PK-CONTEXT], [PK-CONTRIB]

## 1. Scope, taxonomy, and cutoff

The selected surfaces are:

1. ChatGPT Codex: Codex mode in the ChatGPT desktop app.
2. Codex CLI/TUI.
3. Claude Code.
4. Claude Desktop.
5. Cursor desktop.
6. Cursor Agent CLI.

The report uses these claim classes:

- **D — documented:** a current official product document directly states the claim.
- **S — source-observed:** immutable official vendor source implements or records the mechanism; this is not proof that a particular distributed build or host has it.
- **L — local CLI-observed:** dated `--help` or `--version` output from a local binary. No L claims appear because this contract forbade invoking local harnesses.
- **U — unknown:** the listed primary-source survey did not establish the fact. This is not proof of impossibility.
- **X — unsupported:** an official source expressly excludes the surface or the platform is outside an explicit closed support set.

Platform evidence uses four independent fields. A claim class applies inside each field, and a source populating one field does not populate another:

- **Downloadable artifact architecture:** architecture labels or filenames exposed by an official download or release source. This does not establish package-repository behavior, declared OS/distro support, successful installation, or compatibility with a live host.
- **Package-repository architecture:** architectures expressly accepted or served by a documented vendor repository/install route. This is route-specific and does not establish every downloadable artifact, every distribution, or live-host compatibility.
- **Declared OS/distro support:** formal requirements, minimum OS versions, or an explicit closed support set. A separately documented install route does not enlarge that set; any conflict between the two remains a conflict.
- **Live-host qualification:** observed product presence, package ownership, processor/packaging compatibility, install/update capability, and behavior on work macOS or Hatchery. Issue #1 makes no live-host claim; `nisavid/agents#42` owns those observations.

Every D, U, or X claim below inherits the observation cutoff **2026-09-07 in America/New_York**. Every S claim names or inherits the immutable source revision in its citation. A moving documentation URL is evidence only for that observation date. Reinstalling an older artifact is called a downgrade building block, not a documented rollback command, unless the vendor says otherwise.

The portable Agent Plugins v1.0.0 package is a directory with root `plugin.json`, direct-child skills under `skills/<name>/SKILL.md`, and optional `mcp.json`; the specification defines version metadata for update/cache decisions but no portable installer, update actuator, rollback command, uninstall command, or digest receipt. [AP-SPEC] The official compatible-client source at `c4a3a8dc683838f14d178392aaeaabeba4533377` lists “ChatGPT & Codex” and Cursor for skills and MCP, but not Claude; Claude's routes below are therefore Claude-native routes, not Agent Plugins conformance claims. [AP-CLIENTS]

## 2. Cross-surface matrix

Each cell carries a claim class and primary-source citation. “No command found” is U relative to the cited official source set.

| Surface | Host product lifecycle | Plugin or equipment lifecycle | Exactness and observability | Material unsupported or unknown boundary |
| --- | --- | --- | --- | --- |
| **ChatGPT Codex** | **D:** Chat, Work, and Codex are views in the current unified ChatGPT desktop app. **Downloadable artifact architecture — D/U:** the documented Apple Silicon macOS package is a DMG; the current Mac download flow detects Apple Silicon or Intel and supplies the appropriate installer, but does not name the Intel installer's package format. Windows offers Store-signed x64/Arm64 MSIX packages, and Linux preview offers x64/ARM64 `.deb` and `.rpm` packages. Windows also offers web-installer and WinGet routes. **Package-repository architecture — U:** Linux packages configure signed OpenAI APT/DNF update repositories, but the reviewed source set does not expressly state those repositories' architecture contracts. **D:** the app normally self-updates; Linux updates through APT/DNF. Managed macOS/Windows deployments may disable in-app updates, but OpenAI says that is not OpenAI-managed pinning. [OAI-APP], [OAI-CHATGPT-APP], [OAI-MAC-REQ], [OAI-MAC-DOWNLOAD], [OAI-LINUX], [OAI-WINDOWS], [OAI-WINDOWS-REQ], [OAI-UPDATES] | **D/S:** The universal Plugins directory installs OpenAI plugins for new chats; `@` selects a plugin or skill. Native packages use `.codex-plugin/plugin.json`. Workspace Git marketplaces can sync daily or on “Sync now,” accept a branch/tag/commit, and uninstall through the plugin browser. Agent Plugins v1 skills/MCP support is documented at the client-family level and implemented in Codex source. [OAI-PLUGIN-DOC], [OAI-BUILD-PLUGIN], [OAI-PLUGIN-MGMT], [AP-CLIENTS], [OAI-AGENT-MANIFEST] | **D/U:** a workspace marketplace can stay on a fixed commit and native manifests carry a version, but the consumer UI does not document a loaded-bundle digest, resolved revision receipt, per-chat plugin version, or installed-byte inventory. Product version inventory is delegated to deployment tooling in managed flows. [OAI-PLUGIN-MGMT], [OAI-UPDATES], [OAI-PLUGIN-DOC] | **X:** OpenAI expressly does not provide standalone MSI or non-Store EXE packages. **Declared OS/distro support — D/X:** the unified app requires macOS 14 on Apple Silicon M1+ or Intel and Windows 10 build 17763+ on x64/Arm64; Linux preview formally supports only Ubuntu 24.04/26.04, Debian 13, and Fedora 43/44 on x64/ARM64. OpenAI excludes older macOS releases and Linux distributions outside that closed set. **Live-host qualification — U:** the documented requirements, distribution routes, and processor-detecting Mac flow establish neither target host, the installer selected there, installation success, nor compatibility. **U:** no exact app-version selector, first-party app rollback, complete end-user app uninstall guide, consumer plugin pin, plugin rollback, or personal-directory update cadence was found. [OAI-MAC-REQ], [OAI-MAC-DOWNLOAD], [OAI-CHATGPT-APP], [OAI-LINUX], [OAI-WINDOWS], [OAI-WINDOWS-REQ], [OAI-UPDATES], [OAI-PLUGIN-DOC] |
| **Codex CLI/TUI** | **D/S/U:** install through standalone shell/PowerShell installers, npm, Homebrew, or release archives; invoke with `codex` or `codex exec`. The source exposes `codex update` and startup update checks. Exact npm versions and tagged archives can replace a build, but no named rollback or complete product-uninstall contract was found. `codex --version` is supported by the CLI parser. **Downloadable artifact architecture — S:** the pre-cutoff 0.153.4 `codex-package_SHA256SUMS` names 12 aarch64/x86_64 Apple Darwin, Windows MSVC, and Linux musl package archives. Those names do not establish a closed declared-support set, a package-repository contract, installed-byte identity, or a live-host result; the file also does not cover every release artifact or establish signature semantics or a run receipt. [OAI-CODEX-README], [OAI-CLI], [OAI-CODEX-MAIN], [OAI-CODEX-UPDATES], [OAI-CODEX-1534-RELEASE], [OAI-CODEX-1534-SUMS] | **D/S:** `/plugins` browses configured marketplaces; source exposes `codex plugin add/list/remove` and `codex plugin marketplace add/list/upgrade/remove`. Marketplaces may be local or Git; plugin entries may be local, Git/ref/SHA, or npm/version. New sessions load installed capabilities. [OAI-PLUGIN-DOC], [OAI-PLUGIN-CLI], [OAI-MARKET-CLI], [OAI-MARKET-SRC] | **S:** `plugin add` output reports the installed root; `plugin list` output reports installed/enabled state, manifest version, and configured source selector. Git-marketplace activation records the resolved revision in internal metadata, but the reviewed list output does not surface that resolved revision for a moving ref. No cryptographic plugin digest or byte inventory is emitted. [OAI-PLUGIN-CLI], [OAI-MARKET-ACT] | **S:** marketplace commands refresh snapshots, and source selectors can name older known inputs. **U:** no source binds refresh, installed replacement, and session reload into one atomic receipt or documents first-class rollback; selecting an older input is only a downgrade technique. [OAI-MARKET-CLI], [OAI-LOCAL-UPDATE], [OAI-MARKET-ACT] |
| **Claude Code** | **Declared OS/distro support — D/U:** formal system requirements list macOS, Windows, and Linux on Ubuntu, Debian, or Alpine with x64/ARM64 hardware; the separately documented DNF route for Fedora/RHEL leaves Fedora/RHEL support unresolved rather than enlarging that formal set. **Package-repository architecture — U:** signed APT, DNF, and APK routes are documented, but the reviewed route definitions do not expressly state their architecture contracts. **D:** other documented installation routes include native installers, Homebrew, WinGet, and npm. Native install accepts `latest`, `stable`, or an exact version; `claude update` actuates updates; bounds and updater-disable controls exist; `claude --version` and `claude doctor` expose state. Releases publish per-platform SHA-256 manifests and, from 2.1.89, detached signatures. Per-route uninstall is documented. [CC-P1], [CC-P2] | **D:** native plugin directories use optional `.claude-plugin/plugin.json` plus skills, commands, agents, hooks, MCP, LSP, and other Claude components. Marketplaces accept Git/local/URL/archive/npm/command forms; `claude plugin install/update/uninstall` and marketplace refresh commands exist; `--plugin-dir`/`--plugin-url` load session-only equipment. Copied marketplace plugins use a separate cache directory per resolved version and automatically install frozen-lockfile Node dependencies. That dependency pass suppresses lifecycle scripts, but fetching an npm-source plugin first runs `npm install` with lifecycle scripts enabled; a 60-second timeout can leave partial `node_modules`. [CC-E1], [CC-E2], [CC-E3] | **D/U:** resolution identity prefers plugin version, marketplace version, Git commit, archive SHA-256, or a content hash depending on source. `plugin list --json` reports installed version/source/enabled state; `plugin details` inventories components. `${CLAUDE_PLUGIN_DATA}` survives updates; last-scope uninstall deletes it by default unless `--keep-data`, while `--prune` removes orphaned auto-installed dependencies. The top-level install command has no consumer version selector. [CC-E2], [CC-E3] | **D:** an exact older product version can be installed. Orphaned plugin-cache entries are marked for a background sweep roughly 14 days later to protect running sessions; that sweep runs only while at least one plugin remains installed. **U:** cache retention, dependency installation, and data-management flags are not exact installed-byte or cryptographic identity, an atomic update/load receipt, or rollback. No named product rollback, plugin rollback/previous-cache activation, or run-bound plugin digest receipt was found. [CC-P1], [CC-P2], [CC-E2] |
| **Claude Desktop** | **Declared OS/distro support — D:** macOS 11+, Windows 10+, and Linux beta on Ubuntu 22.04+/Debian 12+ x64/ARM64. **D:** macOS uses DMG/PKG and Windows uses MSIX. **Downloadable artifact architecture — D:** the direct Linux `.deb` route expressly offers x64 and ARM64 files. **Package-repository architecture — U:** the APT route is documented, but its repository definition does not expressly state an architecture contract. **D:** macOS/Windows self-update unless enterprise policy delegates updates to MDM; Linux repository installs update through APT, while direct `.deb` installs lack that feed. Normal launch and `claude://` deep links invoke the product. [CD-P1], [CD-P2], [CD-P3], [CD-P4], [CD-P5], [CD-P6] | **D/U:** current official pages agree that Claude plugins apply to Cowork but conflict on Chat: the Help Center includes web/Desktop Chat, while the Cowork guide says plugins are not used in Chat. Desktop Extensions are a separate `.mcpb`/root-`manifest.json` plane for local MCP servers; directory extensions auto-update and private bundles update manually. [CD-G1], [CD-G2], [CD-G4], [MCPB-README], [MCPB-MANIFEST], [CD-X1], [CD-X2] | **D/U:** manifests carry versions and MCPB can constrain client/platform compatibility. Windows deployment can query the installed package/version; users can inspect plugin components and extension status/logs. No single machine-readable inventory, exact installed-content digest, immutable source provenance, or session receipt spans those planes. [CD-P4], [CD-G2], [CD-G4], [CD-X1], [MCPB-MANIFEST] | **S:** immutable MCPB documentation labels the current manifest 0.3 while showing a 0.4 `uv` example. **Declared OS/distro support — U:** native support outside the listed Linux distributions was not found. **Live-host qualification — U:** none of those platform statements establishes either target host. **U:** no first-party Desktop exact selector, product rollback/uninstall, Claude-plugin consumer pin/rollback, or MCPB consumer pin/rollback was found. [CD-P2], [CD-P5], [CD-G1], [CD-X1], [MCPB-MANIFEST] |
| **Cursor desktop** | **Downloadable artifact architecture — D:** the official download page offers both ARM64 and x64 RPM and AppImage artifacts, alongside macOS DMG, Windows user/system EXE, and Linux DEB downloads. **Package-repository architecture — D/U:** APT expressly accepts `amd64`/`arm64`; the reviewed source set does not establish the DNF repository's architecture contract. **Declared OS/distro support — D/U:** macOS 12+ supports Apple Silicon and Intel; Windows 10+ is documented; Debian/Ubuntu APT and RHEL/Fedora DNF routes are documented; broader Linux support is not established. **D/U:** Stable/Early Access select release streams; `UpdateMode` controls when and how updates occur; neither selects an exact version. About exposes the product version. Prior downloads exist, but no transactional rollback or old-state compatibility promise is documented. [CUR-DOWNLOAD], [CUR-QUICKSTART], [CUR-DEPLOY], [CUR-TROUBLE], [CUR-AGENT-ISSUES] | **D/S:** Cursor accepts Agent Plugins with root `plugin.json` and Cursor Plugins with `.cursor-plugin/plugin.json`. Public, team-Git, and local-directory routes feed Customize; skills use `/skill-name`, and native rules/agents/commands/hooks/MCP have component-specific loading. VSIX is a separate editor-extension plane, not a Provingkit plugin format. [CUR-PLUGIN], [CUR-PLUGIN-REF], [CUR-CATALOG], [CUR-EXT] | **D/U:** team marketplaces reindex a tracked branch and support manual refresh; manifests can carry version metadata and compatibility floors. The UI does not document a per-plugin exact selector, resolved commit, content digest, or invocation-bound byte receipt. [CUR-PLUGIN], [CUR-PLUGIN-REF], [CUR-SCHEMA] | **D/S:** the moving plugin reference and immutable official marketplace schema disagree on allowed/required fields. **Live-host qualification — U here:** no work-macOS or Hatchery fact follows from the three source fields; every live-host field remains for `nisavid/agents#42`. No supported per-plugin rollback, complete ordinary-plugin uninstall/state-retention procedure, or public runtime/publication-validator version was found. [CUR-DOWNLOAD], [CUR-QUICKSTART], [CUR-PLUGIN-REF], [CUR-MARKET-SCHEMA] |
| **Cursor Agent CLI** | **Declared OS/distro support — U:** the official install page documents shell-installer routes for macOS, Linux, and Windows through WSL plus a native Windows PowerShell route, but no minimum OS versions, Linux distro set, or closed support set. **D/U:** the CLI auto-updates; `agent update`/`/update` actuate latest, and a documented channel setting selects the updater track. A January 2026 changelog entry says `--disable-auto-update` turns off background updates, but current parameter/configuration references omit the flag, so present availability and semantics are unknown. `agent --version`, `agent about --format json`, and logs expose product state. An August 11, 2026 changelog entry documents a Windows uninstaller with optional Cursor user-data deletion. How to launch it, its complete cleanup behavior, and product removal on macOS, Linux, or WSL remain unknown. No supported exact-build selector or rollback route was found. [CUR-CLI-INSTALL], [CUR-CLI-PARAMS], [CUR-CLI-SLASH], [CUR-CLI-CONFIG], [CUR-CLI-CHANGELOG] | **D:** CLI is a documented Cursor-plugin surface. Repeated `--plugin-dir` loads local plugin directories; a March 2026 changelog entry documents browsing the marketplace and installing or uninstalling plugins at user or project scope through `/plugin`; `agent plugin marketplace add/list/update/remove` manages user marketplaces, and `--git-ref` accepts branch, tag, or commit. `agent mcp` observes separately configured MCP servers/tools. [CUR-PLUGIN], [CUR-CLI-PARAMS], [CUR-CLI-SLASH], [CUR-CLI-MCP], [CUR-CLI-CHANGELOG] | **D/U:** a full commit can pin the marketplace registration input, but list JSON documents name/scope/Git URL rather than the resolved commit; no per-plugin content digest or loaded-byte receipt is documented. [CUR-CLI-CHANGELOG], [CUR-CLI-MCP] | **S:** the exact observed public installer scripts selected an artifact path labeled `lab`. **Live-host qualification — U:** no target-host channel, build, compatibility, or behavior follows from those scripts or install routes. **U:** no source says product update refreshes plugins; no CLI-specific installed-plugin exact-version selector, rollback, installed-byte deletion semantics, or retained-state semantics follows from the reviewed sources. [CUR-INSTALL-SH], [CUR-INSTALL-PS], [CUR-CLI-CONFIG], [CUR-CLI-CHANGELOG] |

## 3. ChatGPT Codex evidence

### Product lifecycle

- **D:** the current unified ChatGPT desktop app contains Chat, Work, and Codex; Codex is selected inside the app rather than installed as a separate plugin. macOS/Windows migration guidance and Linux preview documentation establish the product surfaces. [OAI-APP], [OAI-MAC-REQ], [OAI-APP-MIGRATION], [OAI-LINUX]
- **Downloadable artifact architecture — D/U:** the documented Apple Silicon macOS package is a DMG. The current Mac download page detects Apple Silicon or Intel and supplies the appropriate installer, but it does not name the Intel installer's package format. Windows offers Store-signed x64/Arm64 MSIX packages, and Linux preview offers x64/ARM64 `.deb` and `.rpm` packages. Windows also offers web-installer and WinGet routes. **X:** standalone MSI and non-Store EXE packages are expressly unavailable. [OAI-CHATGPT-APP], [OAI-MAC-DOWNLOAD], [OAI-LINUX], [OAI-WINDOWS]
- **Package-repository architecture — U:** Linux preview packages configure signed OpenAI APT/DNF repositories for updates, but the reviewed source set does not expressly state those repositories' architecture contracts. [OAI-LINUX]
- **Declared OS/distro support — D/X:** the unified app requires macOS 14 on Apple Silicon M1+ or Intel and Windows 10 build 17763+ on x64/Arm64. Linux preview formally supports only Ubuntu 24.04/26.04, Debian 13, and Fedora 43/44 on x64/ARM64. OpenAI excludes older macOS releases and Linux distributions outside that closed set. [OAI-MAC-REQ], [OAI-WINDOWS-REQ], [OAI-LINUX]
- **Live-host qualification — U here:** none of those artifact, repository, or support statements proves either target host currently has the app or establishes the installer selected there, installation success, architecture compatibility, or behavior. [OAI-CHATGPT-APP], [OAI-MAC-REQ], [OAI-MAC-DOWNLOAD], [OAI-LINUX], [OAI-WINDOWS], [OAI-WINDOWS-REQ]
- **D/U:** ordinary app updates are self-managed. Managed macOS/Windows deployments can set `in_app_updates = false` and deploy approved packages externally; OpenAI expressly says this does not provide OpenAI-managed version pinning or an older-version compatibility guarantee. The routes do not establish a complete uninstall, exact version selection, or rollback. [OAI-UPDATES], [OAI-LINUX], [OAI-WINDOWS]
- **U:** the surveyed OpenAI pages do not give a first-party rollback operation, complete end-user uninstall procedure, stable prior-build selector, Codex-mode-specific version identity, or cryptographic installed-app byte receipt. [OAI-APP], [OAI-UPDATES], [OAI-WINDOWS], [OAI-LINUX]

### Plugin lifecycle

- **D:** the consumer route is Plugins → browse/details → install; a new chat loads the plugin. Users can describe the task or type `@` to choose a plugin or bundled skill. Uninstall removes the bundle but does not disconnect separately managed connectors; required/default workspace plugins may constrain removal. [OAI-PLUGIN-DOC]
- **D:** native authoring uses `.codex-plugin/plugin.json`, with components at the plugin root. Local/repository marketplaces use `.agents/plugins/marketplace.json`; workspace Git import supports a fixed commit, daily sync, and manual “Sync now.” [OAI-BUILD-PLUGIN], [OAI-PLUGIN-MGMT]
- **S:** `openai/codex@7769bccbb2b4e9469a36b12510e73594fa03c5d5` recognizes Agent Plugins v1.0.0 root `plugin.json` before legacy manifests, maps `skills/` and `mcp.json`, uses direct-child skill discovery, and does not load apps or hooks from the standard-format path. This describes source at that commit, not a host or deployed-app receipt. [OAI-PLUGIN-NS], [OAI-AGENT-MANIFEST], [OAI-LOADER]
- **U:** no current consumer documentation establishes personal/public-directory update cadence, an exact-version install selector, rollback, resolved-source display, loaded digest, installed-byte inventory, or a per-chat plugin receipt. [OAI-PLUGIN-DOC], [OAI-BUILD-PLUGIN]

## 4. Codex CLI/TUI evidence

### Product lifecycle

- **Declared OS/distro support — U:** the current official README's Mac/Linux and Windows install routes do not define formal OS/distro requirements or a closed support set. **D/S:** the documented routes include native installers, npm, Homebrew, and tagged archives. Source defines `codex update` and update discovery appropriate to the detected installation method; `codex` opens the TUI and `codex exec` is the non-interactive entry point. [OAI-CODEX-README], [OAI-CODEX-MAIN], [OAI-CODEX-UPDATES], [OAI-CLI]
- **D/U:** exact npm package versions and tagged release assets can select old or current bytes. That is exact replacement, not a separately documented rollback command or downgrade-compatibility promise. [OAI-CHANGELOG], [OAI-CODEX-README]
- **Downloadable artifact architecture — S:** OpenAI's 0.153.4 release, tag `rust-v0.153.4`, was published 2026-09-04 and includes `codex-package_SHA256SUMS`. The file fetched on 2026-09-07 was 1,392 bytes with SHA-256 `645fb8d4a1f821357a7160f04a6d15bf54ff97ab6946a79239c551ebed734d23`; its 12 rows give SHA-256 values for `codex-package` and `codex-app-server-package` `.tar.gz` archives for aarch64/x86_64 Apple Darwin, Windows MSVC, and Linux musl. Those artifact names establish neither a package-repository contract nor declared OS/distro support or live-host qualification. The evidence covers only those named release archives, not every artifact, cryptographic signature semantics, installed-byte identity, or a run receipt. [OAI-CODEX-1534-RELEASE], [OAI-CODEX-1534-SUMS]
- **S/U:** Clap exposes the CLI version, but no unified official product-uninstall/state-cleanup contract was found for all installation routes. [OAI-CODEX-MAIN], [OAI-CLI]

### Plugin lifecycle

- **D/S:** `/plugins` is the interactive browser. Immutable source adds `add`, `list`, and `remove`, plus marketplace `add/list/upgrade/remove` for local or Git sources. Plugin sources include local directories, Git refs/SHAs/subdirectories, and npm versions/ranges/tags. [OAI-PLUGIN-DOC], [OAI-PLUGIN-CLI], [OAI-MARKET-CLI], [OAI-MARKET-SRC]
- **S:** install JSON reports plugin identity, version, and installed root; list JSON reports installed/enabled state, version, and configured source selector. Marketplace activation persists the resolved Git revision and restores the previous snapshot when an activation fails, but that internal failure recovery is not a user rollback command and the list output does not expose the resolved revision for a moving ref. [OAI-PLUGIN-CLI], [OAI-MARKET-ACT]
- **D/S/U:** updates are split: a configured Git marketplace can be upgraded, while local development changes use cachebuster plus reinstall and a new session. No source binds discovery, replacement, and reload into one success receipt. [OAI-MARKET-CLI], [OAI-LOCAL-UPDATE]
- **U:** no first-class plugin rollback, cryptographic installed-bundle digest, complete byte inventory, or invocation-bound loaded-version receipt was found. [OAI-PLUGIN-CLI], [OAI-PLUGIN-DOC]

## 5. Claude Code evidence

### Product lifecycle

- **Declared OS/distro support — D/U:** formal system requirements list macOS 13+, Windows 10 1809+/Server 2019+, and Linux on Ubuntu 20.04+, Debian 10+, or Alpine 3.19+, with x64 or ARM64 hardware. A separately documented DNF route covers Fedora/RHEL, so Fedora/RHEL support status remains unresolved rather than enlarging the formal set. [CC-P1]
- **Package-repository architecture — U:** signed APT, DNF, and APK repositories are documented for Debian/Ubuntu, Fedora/RHEL, and Alpine, but the reviewed repository definitions do not expressly state their architecture contracts. [CC-P1]
- **D:** other documented installation routes include native installers, Homebrew, WinGet, and npm. Exact version, `stable`, and `latest` are native-install selectors; `claude` starts the interactive product, with print/headless modes also documented. [CC-P1], [CC-P2]
- **D:** native installs check periodically, apply on restart, and accept `claude update`. `DISABLE_AUTOUPDATER` stops background updates while `DISABLE_UPDATES` blocks background and manual update paths; managed minimum/maximum versions are bounds, not an exact pin. [CC-P1]
- **D:** `claude --version` and `claude doctor` expose active version, install health, and update-attempt results. Release manifests carry per-platform SHA-256 and detached signatures from release 2.1.89; route-specific uninstall and optional state deletion are documented. [CC-P1], [CC-P2]
- **D/U:** `claude install <older-version>` is an exact downgrade building block. There is no separately named rollback command, automatic health rollback, or documented compatibility guarantee for local state after downgrade. [CC-P1], [CC-P2]

### Plugin lifecycle

- **D:** Claude-native plugins are self-contained directories with optional `.claude-plugin/plugin.json` and conventional skills, commands, agents, hooks, MCP, LSP, and other roots. Marketplaces use `.claude-plugin/marketplace.json` and may resolve Git/local/URL/archive/npm/command sources. [CC-E2], [CC-E3], [CC-E5], [CC-E6]
- **D:** `claude plugin install/update/uninstall`, marketplace refresh, `--plugin-dir`, and `--plugin-url` are documented. Installed changes require `/reload-plugins` or restart; skills can be model-selected or invoked as `/plugin-name:skill-name`. [CC-E1], [CC-E2]
- **D:** copied marketplace plugins use a separate cache directory per resolved version, each with its own files and Node dependencies. A supported lockfile triggers automatic frozen dependency installation with lifecycle scripts suppressed; fetching an npm-source plugin first runs `npm install` with lifecycle scripts enabled. Claude Code stops that install after 60 seconds, and a timeout can leave partial `node_modules` in the cached copy. [CC-E2]
- **D/U:** non-command resolution identity prefers plugin version, marketplace version, Git commit SHA, archive SHA-256/content digest, or `unknown` depending on source. Explicit version metadata is publisher-side update identity; the consumer install command has no exact-version argument. [CC-E2], [CC-E3]
- **D/U:** `plugin list --json` and `plugin details` expose installed version/source/enabled state and component inventory. `${CLAUDE_PLUGIN_DATA}` persists across updates and is deleted by default when uninstall removes the last installed scope; `--keep-data` preserves it. Orphaned cache versions are marked for a background sweep roughly 14 days later to support already-running sessions; the sweep runs only while at least one plugin remains installed. `--prune` removes orphaned dependencies that Claude Code auto-installed for other plugins, not directly installed plugins. None of these is exact installed-byte or cryptographic identity, an atomic update/load receipt, previous-cache activation, or rollback; no per-invocation content digest is emitted. [CC-E1], [CC-E2]

## 6. Claude Desktop evidence

### Product lifecycle

- **Declared OS/distro support — D:** Claude Desktop requires macOS 11+, Windows 10+, or Linux beta on Ubuntu 22.04+/Debian 12+ with x64 or ARM64 hardware. macOS DMG/PKG and Windows MSIX routes are documented. [CD-P1], [CD-P2], [CD-P3], [CD-P4]
- **Downloadable artifact architecture — D:** the direct Linux `.deb` route expressly offers x64 and ARM64 files. [CD-P2]
- **Package-repository architecture — U:** the Linux APT route is documented, but its repository definition does not expressly state an architecture contract. [CD-P2]
- **Live-host qualification — U here:** the Linux support, artifact, and repository statements are not evidence of Hatchery state, installation, architecture compatibility, or behavior. Linux lacks computer use and dictation in the observed documentation. [CD-P2]
- **D:** macOS/Windows use in-app updates unless enterprise policy delegates to MDM; Linux repository installs use APT, while a direct DEB has no enrolled update feed. Users launch from the OS application surface or the Linux `claude-desktop` command; `claude://` links can open product modes. [CD-P2], [CD-P5], [CD-P6]
- **U:** no consumer exact-version selector, public historical-build selector, first-party rollback procedure, or official complete uninstall/state-removal procedure was found. MDM control is an ownership boundary, not an Anthropic exact-version API. [CD-P2], [CD-P3], [CD-P4], [CD-P5]
- **D/U:** Windows deployment can query the installed package/version, and Desktop exposes troubleshooting logs. No cross-platform machine-readable updater history, available-version feed, or product provenance receipt was found. [CD-P4]

### Claude plugins

- **D:** the Help Center points authors to the shared Claude-native plugin structure: a self-contained directory with optional `.claude-plugin/plugin.json` and conventional component roots. Personal package upload and organization ZIP/Git marketplace routes are documented. [CD-G1], [CD-G2], [CC-E2]
- **D/U:** the Help Center says Claude-native plugins install in web Chat, Desktop Chat, and Cowork, with skills across those surfaces and hooks/subagents only in Cowork. The current Cowork guide instead says plugins apply to Cowork and Code and are not used in Chat. Cowork support is common to both pages; Chat and Desktop Chat applicability remain unresolved from the conflicting moving documentation. [CD-G1], [CD-G4]
- **D:** organization updates replace a same-name ZIP or sync a Git marketplace; the Cowork guide exposes Update for a personal repository marketplace. Installed/shared equipment takes effect on a later session or refresh. User-installed plugins can be uninstalled; Required organization plugins cannot. [CD-G1], [CD-G2], [CD-G4]
- **D:** the Help Center says installed skills appear through `/` or `+` and may also be selected by Claude; Cowork is a supported surface in both conflicting pages. [CD-G1], [CD-G3], [CD-G4]
- **U:** Desktop and Cowork UI docs do not expose an end-user exact selector, installed digest, immutable resolved commit, per-user update history, or rollback. Claude Code's broader source resolvers must not be projected onto these surfaces without qualification because their administration narrows accepted source types. [CD-G1], [CD-G2], [CC-E2]

### Desktop Extensions

- **D:** MCPB is a ZIP-based local-MCP package with root `manifest.json`. It records name, semantic version, server entry/configuration, optional client/platform compatibility, tools/prompts, and user configuration. `mcpb init` and `mcpb pack` create bundles. [MCPB-README], [MCPB-MANIFEST], [MCPB-CLI]
- **D:** official-directory extensions auto-update; private bundles update by manually installing new `.mcpb` files; organization custom updates require the same name and a higher version. Settings expose status and logs. [CD-X1], [CD-X2]
- **D:** after installation and configuration, an extension becomes available automatically in conversations; `+` → Connectors exposes servers/tools. Desktop restart refreshes the extension registry when an installed extension is unavailable. [CD-X1]
- **U:** no consumer exact-version pin, directory-update hold, content-digest pin, rollback, or explicit end-user uninstall flow was found. The immutable manifest document's 0.3/0.4 inconsistency remains a validator-authority gap. [MCPB-MANIFEST], [CD-X1], [CD-X2]

## 7. Cursor desktop evidence

### Product lifecycle

- **Downloadable artifact architecture — D:** the official download page observed 2026-09-07 offers both ARM64 and x64 RPM and AppImage artifacts. It also lists macOS DMG, Windows user/system EXE, and Linux DEB downloads. These labels establish downloadable artifacts only; they do not establish a repository contract, declared distro support, host compatibility, successful installation, rollback, or state compatibility. [CUR-DOWNLOAD]
- **Package-repository architecture — D/U:** the Debian/Ubuntu APT route expressly accepts `amd64`/`arm64`; the reviewed source set does not establish the RHEL/Fedora DNF repository's architecture contract. [CUR-QUICKSTART]
- **Declared OS/distro support — D/U:** macOS 12+ supports Apple Silicon and Intel; Windows 10+ is documented; Debian/Ubuntu APT and RHEL/Fedora DNF routes are documented; broader Linux support is not established. [CUR-QUICKSTART]
- **Live-host qualification — U here:** no work-macOS or Hatchery presence, ownership, architecture compatibility, install/update capability, or behavior follows from those source fields; `nisavid/agents#42` owns every such observation. [CUR-DOWNLOAD], [CUR-QUICKSTART]
- **D:** Cursor-owned repositories provide package-manager updates; Cursor also documents manual/in-app update and managed update modes. [CUR-QUICKSTART], [CUR-DEPLOY], [CUR-TROUBLE]
- **D/U:** Stable and Early Access select release streams, while `UpdateMode` controls when and how updates occur; neither selects an exact release. Current and prior installers appear on the moving download page; reinstalling one is not a documented transactional rollback, does not guarantee state compatibility, and remains subject to backend minimum-version floors. [CUR-TROUBLE], [CUR-DOWNLOAD], [CUR-DEPLOY]
- **D/U:** About exposes version and diagnostics/log export provides operational evidence. No public signed checksum/release-manifest route or complete cross-platform uninstall/state-cleanup contract was found. [CUR-AGENT-ISSUES]

### Plugin and extension lifecycle

- **D:** Agent Plugins use root `plugin.json`; Cursor Plugins use `.cursor-plugin/plugin.json` with Cursor-native rules, skills, agents, commands, hooks, variables, and MCP. Public marketplace, team Git marketplace, and local-directory development routes feed Customize; project/user/team scopes and Required policy are documented. [CUR-PLUGIN], [CUR-PLUGIN-REF], [CUR-CATALOG]
- **D:** skills can be model-selected or invoked as `/skill-name`; rules, commands, hooks, and MCP follow their own loading/invocation semantics. Team marketplaces track a branch and reindex on GitHub events or Refresh. That is catalog discovery, not a receipt proving which bytes a process loaded. [CUR-PLUGIN], [CUR-PLUGIN-REF]
- **D/U:** plugin manifests can carry semantic version metadata and client-version floors, but no consumer per-plugin selector, digest lock, rollback, or complete ordinary uninstall/state-retention sequence is documented. Customize exposes installed scope/components, not an immutable run receipt. [CUR-PLUGIN], [CUR-PLUGIN-REF], [CUR-SCHEMA]
- **D/S/U concern:** the moving reference describes marketplace fields that the official immutable schema at `cursor/plugins@93b00b89ef425a9c1bac0d0b317dfc49c930ac99` rejects, while that schema contains `minClientVersions` omitted from part of the moving field table. Runtime parser and publication-validator versions remain U. [CUR-PLUGIN-REF], [CUR-MARKET-SCHEMA]
- **D/U boundary:** VSIX editor extensions are a separate Open VSX equipment plane. No primary source reviewed establishes VSIX as a Provingkit Agent Plugin route. [CUR-EXT]

## 8. Cursor Agent CLI evidence

### Product lifecycle

- **Declared OS/distro support — U:** Cursor documents shell-installer routes for macOS, Linux, and Windows through WSL plus a native Windows PowerShell route, but no minimum OS versions, Linux distro set, or closed support set. **D:** `agent` supports interactive, headless, and ACP modes. Auto-update is default; `agent update` and `/update` request latest, and the configuration reference exposes an updater-channel setting. [CUR-CLI-INSTALL], [CUR-CLI-OVERVIEW], [CUR-CLI-PARAMS], [CUR-CLI-SLASH], [CUR-CLI-CONFIG]
- **D:** `agent --version`, `agent about --format json`, `/logs`, request/conversation identifiers, and structured headless/ACP output provide product and operational observations. [CUR-CLI-PARAMS], [CUR-CLI-SLASH], [CUR-CLI-ACP]
- **D/S/U:** the observed public installer scripts selected exact build-named archives and versioned installation directories, while supported commands expose channel/latest rather than an exact-build selector. **Live-host qualification — U here:** those installer paths and routes establish no target-host channel, build, compatibility, or behavior. A January 2026 changelog entry documents `--disable-auto-update` for background updates, but current parameter/configuration references omit it; current flag availability and semantics are therefore unknown. An August 11, 2026 changelog entry documents a Windows uninstaller with optional Cursor user-data deletion. The surveyed sources do not document how to launch it, its complete cleanup behavior, or a product-removal route for macOS, Linux, or WSL. No official exact pin or rollback procedure was found; filesystem repointing would be unsupported intervention. [CUR-INSTALL-SH], [CUR-INSTALL-PS], [CUR-CLI-INSTALL], [CUR-CLI-PARAMS], [CUR-CLI-CONFIG], [CUR-CLI-CHANGELOG]

### Plugin and MCP lifecycle

- **D:** Cursor documents CLI as a plugin surface. `--plugin-dir` is repeatable. A March 2026 changelog entry documents browsing the marketplace and installing or uninstalling plugins at user or project scope through `/plugin`; `agent plugin marketplace` manages marketplaces, and `--git-ref` accepts a branch, tag, or commit. Skills work in interactive/headless flows, subject to the component support matrix. [CUR-PLUGIN], [CUR-CLI-PARAMS], [CUR-CLI-SLASH], [CUR-CLI-CHANGELOG]
- **D:** `agent mcp list` and `list-tools` expose separately configured MCP source, status, transport, and tools. These are discovery/health observations, not server-build or content-digest receipts. [CUR-CLI-MCP]
- **U:** no source says `agent update` refreshes plugins. Marketplace list JSON does not document the resolved Git commit, and no CLI-specific per-plugin exact-version selector, installed-byte digest, rollback, installed-byte deletion semantics, or retained-state semantics was found. [CUR-CLI-PARAMS], [CUR-CLI-CHANGELOG], [CUR-CLI-MCP]

## 9. Host-applicability handoff to `nisavid/agents#42`

This report contains no live result for work macOS or Hatchery CachyOS. For each host and each of the six surfaces, #42 must keep these handoff fields independent:

1. observation timestamp and sanitized evidence command;
2. downloadable artifact name/format and architecture label, with source binding and claim class;
3. package-repository route and expressly documented architecture contract, with source binding and claim class;
4. declared OS/distro support, minimum version, and closed-set boundary, with source binding and claim class;
5. observed host OS/distro and processor architecture;
6. product present/absent, exact product version, and actual installer/package owner;
7. observed architecture compatibility, install/update capability, and behavior;
8. product update channel, discovery state, and actuator actually available;
9. plugin/equipment manager or local-directory route actually available;
10. installed/enabled scope and plugin/equipment declared version;
11. configured source selector and independently resolved immutable revision;
12. digest algorithm, digest, and byte-set boundary for the installed equipment;
13. observed installed-byte inventory or a precise “not observable” result;
14. discovery/load result in a fresh process or session;
15. user invocation route and a non-mutating representative discovery receipt;
16. documented/observed rollback and removal availability, without actuating either unless separately authorized;
17. mismatches among artifact labels, repository contracts, declared support, and the actual host;
18. unknowns and unsupported cells, kept distinct from absence.

Fields 2–4 remain dated vendor-source claims; fields 5–7 require host observation. No artifact label, processor-detecting selection route, repository contract, or operating-system statement may pre-fill product presence, package ownership, architecture compatibility, installation, manager availability, update capability, version, or behavior on either host. [OAI-MAC-DOWNLOAD], [OAI-MAC-REQ], [OAI-WINDOWS-REQ], [OAI-LINUX], [CC-P1], [CD-P2], [CUR-DOWNLOAD], [CUR-QUICKSTART], [CUR-CLI-INSTALL]

## 10. Separable downstream facts

These are factual inputs, not decisions.

### For Provingkit #8

- Product identity, plugin-declared version, resolved source revision, installed-byte digest, enablement, load, and invocation are separate evidence fields across the reviewed managers. No vendor source collapses them into one assurance claim. [OAI-PLUGIN-CLI], [CC-E2], [CD-G1], [CUR-PLUGIN], [CUR-CLI-MCP]
- Useful native evidence exists—Claude release checksums/signatures, the Codex 0.153.4 checksum file for its 12 named package archives, exact source selectors, updater diagnostics, plugin inventories, and logs—but none establishes Provingkit release eligibility, compromise survival, or production readiness. [CC-P1], [CC-E2], [OAI-CODEX-1534-RELEASE], [OAI-CODEX-1534-SUMS], [OAI-MARKET-ACT], [CUR-AGENT-ISSUES]
- This report does not reopen accepted #8 Q1–Q11 records; it supplies mechanism facts only.

### For Provingkit #3

- The documented package entry points are heterogeneous: Agent Plugins root `plugin.json`, OpenAI `.codex-plugin/plugin.json`, Claude `.claude-plugin/plugin.json`, Cursor `.cursor-plugin/plugin.json`, and Claude Desktop `.mcpb`/`manifest.json` are distinct shapes with different supported components. [AP-SPEC], [OAI-BUILD-PLUGIN], [CC-E2], [CUR-PLUGIN-REF], [MCPB-MANIFEST]
- Update actuation is likewise heterogeneous: product self-update/package managers, marketplace refresh, installed-plugin update, local reinstall, session reload, and directory auto-update are different events. [OAI-UPDATES], [OAI-MARKET-CLI], [CC-P1], [CC-E1], [CD-X1], [CUR-PLUGIN], [CUR-CLI-INSTALL]
- Manager-reported semantic version is not a universal immutable byte identity. The Codex 0.153.4 checksum file binds only its 12 named package archives, not installed bytes or invocation; digest and resolved-revision coverage is incomplete and nonuniform across the six surfaces. [AP-SPEC], [OAI-CODEX-1534-SUMS], [OAI-PLUGIN-CLI], [CC-E2], [CD-G1], [CUR-PLUGIN]

### For agents #46

- Across the reviewed managers, the observed applicability dimensions include downloadable artifact architecture, package-repository architecture, declared OS/distro support, live-host qualification, product version, equipment version, source selector, resolved revision, digest boundary, installed/enabled scope, update behavior, load observation, invocation, rollback availability, and removal availability. Each vendor exposes only a subset; claim class and observation time therefore remain separate report metadata. [OAI-MAC-DOWNLOAD], [OAI-MAC-REQ], [OAI-WINDOWS-REQ], [OAI-LINUX], [CC-P1], [CD-P2], [CUR-DOWNLOAD], [CUR-QUICKSTART], [OAI-PLUGIN-CLI], [CC-E2], [CD-X1], [CUR-CLI-PARAMS]
- The report's `documented`, `source-observed`, `local CLI-observed`, `unknown`, and `unsupported` classes are non-equivalent. Download labels, processor-detecting selection routes, repository contracts, declared support, source support, and marketplace listings remain evidence at their stated layers, not live-host evidence. [AP-CLIENTS], [OAI-MAC-DOWNLOAD], [OAI-MAC-REQ], [OAI-WINDOWS-REQ], [OAI-LINUX], [OAI-LOADER], [CD-P2], [CUR-DOWNLOAD], [CUR-QUICKSTART], [CUR-PLUGIN]

## 11. Unresolved factual gaps

1. **Live-host qualification:** every work-macOS and Hatchery cell remains for #42.
2. **OpenAI desktop:** the Mac download flow selects between Apple Silicon and Intel, but it does not name the Intel installer's package format or establish which installer either target host would receive. Other downloadable artifact architectures are documented, while the Linux APT/DNF repository architecture contracts remain unstated in the reviewed source set and no route establishes either target host, exact product selection, installation success, compatibility, rollback, or complete uninstall. No consumer plugin update cadence, exact plugin selector, loaded digest, or per-chat version receipt was found. [OAI-CHATGPT-APP], [OAI-MAC-DOWNLOAD], [OAI-MAC-REQ], [OAI-LINUX], [OAI-WINDOWS], [OAI-WINDOWS-REQ], [OAI-PLUGIN-DOC], [OAI-UPDATES]
3. **Codex CLI:** the 0.153.4 checksum file covers only 12 named package archives and supplies no release-wide artifact coverage, signature semantics, installed-byte identity, or run receipt. No unified product uninstall/state contract, downgrade-compatibility contract, first-class plugin rollback, or atomic marketplace-refresh/install/reload receipt was found. [OAI-CODEX-1534-RELEASE], [OAI-CODEX-1534-SUMS], [OAI-CLI], [OAI-MARKET-CLI], [OAI-PLUGIN-CLI]
4. **Claude Code:** Fedora/RHEL declared support remains unresolved between the formal system-requirements list and the documented DNF route, and the reviewed APT/DNF/APK definitions do not expressly state repository architecture contracts. Per-version cache copies, dependency installation, orphan retention, persistent data, `--keep-data`, and `--prune` supply no exact installed-byte or cryptographic identity, atomic update/load receipt, previous-cache activation, or rollback. No automatic product rollback, plugin consumer version selector, or run-bound plugin digest receipt was found. [CC-P1], [CC-E2]
5. **Claude Desktop:** the direct Linux `.deb` architecture labels do not establish the APT repository architecture contract or live-host qualification; both remain unknown at those layers. Exact product selection, rollback, uninstall/state cleanup, Desktop-plugin exact Git-resolution parity, and equipment digest receipts remain unknown. Current official moving pages also conflict on Chat and Desktop Chat plugin applicability. [CD-P2], [CD-G1], [CD-G2], [CD-G4]
6. **MCPB:** the accepted current manifest schema must be resolved because the immutable official document mixes 0.3 and a 0.4 `uv` example; Linux loader parity is not established by the older immutable README. [MCPB-README], [MCPB-MANIFEST], [CD-X1]
7. **Cursor desktop:** **downloadable artifact architecture — D:** the download page labels both RPM and AppImage artifacts ARM64 and x64. **Package-repository architecture — D/U:** APT expressly accepts `amd64`/`arm64`; the DNF repository contract remains unknown. **Declared OS/distro support — D/U:** macOS 12+ on Apple Silicon/Intel, Windows 10+, and the Debian/Ubuntu APT and RHEL/Fedora DNF routes are documented; broader Linux support remains unknown. **Live-host qualification — U here:** neither target host follows from those source fields. Current backend minimum-version numbers, signed artifact/checksum feeds, exact plugin selection, rollback, ordinary uninstall/state semantics, and the runtime/publication-validator schema version remain unknown. [CUR-DOWNLOAD], [CUR-QUICKSTART], [CUR-DEPLOY], [CUR-PLUGIN-REF], [CUR-MARKET-SCHEMA]
8. **Cursor Agent CLI:** the documented install routes do not supply minimum OS versions, a Linux distro set, or a closed declared-support set. An August 11, 2026 changelog entry documents a Windows uninstaller with optional Cursor user-data deletion; a March 2026 entry documents installing and uninstalling plugins at user or project scope through `/plugin`. Exact product version pin/install, product or plugin rollback, how to launch the Windows uninstaller, its complete cleanup behavior, product removal on macOS, Linux, or WSL, resolved marketplace revision reporting, plugin digest receipts, installed-plugin byte deletion, and retained plugin state remain unknown. The changelog-documented `--disable-auto-update` flag is absent from current parameter/configuration references, leaving its current availability and semantics unknown. The relationship between the observed installer path label and the configurable update channel is also unknown. [CUR-CLI-INSTALL], [CUR-INSTALL-SH], [CUR-INSTALL-PS], [CUR-CLI-PARAMS], [CUR-CLI-CONFIG], [CUR-CLI-CHANGELOG]
9. **Cross-surface:** no reviewed source defines an atomic receipt binding marketplace discovery, exact installed bytes, enablement, process/session load, and invocation. [OAI-PLUGIN-CLI], [CC-E2], [CD-X1], [CUR-PLUGIN], [CUR-CLI-MCP]
10. **Signer and custody:** signer identity, key custody, threshold/rotation, signing-provider choice, and procurement are **outside this report**. They are not issue #1 assignments or inferred follow-up authority.

## 12. Primary-source ledger

The repository sources are immutable at the required base; vendor GitHub sources use full SHAs; all other pages are moving official documentation observed 2026-09-07 unless a publication date is stated on the page.

| ID | Class and binding | Exact claim area | Full primary-source URL |
| --- | --- | --- | --- |
| PK-I1 | GitHub issue, observed 2026-09-07 | Issue question and factual/policy boundary | <https://github.com/nisavid/provingkit/issues/1> |
| PK-AGENTS | Repository source at `e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08` | Repository research and authority conventions | <https://raw.githubusercontent.com/nisavid/provingkit/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/AGENTS.md> |
| PK-CONTEXT | Same immutable base | Canonical plugin/client/release terminology | <https://raw.githubusercontent.com/nisavid/provingkit/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/CONTEXT.md> |
| PK-CONTRIB | Same immutable base | No release/install authority from source work | <https://raw.githubusercontent.com/nisavid/provingkit/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/CONTRIBUTING.md> |
| PK-TRACKER | Same immutable base | Tracker conventions, read only | <https://raw.githubusercontent.com/nisavid/provingkit/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/docs/agents/issue-tracker.md> |
| PK-HIST | Same immutable base; historical lead only | Earlier client/source leads, not current proof | <https://raw.githubusercontent.com/nisavid/provingkit/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/docs/superpowers/research/2026-08-12-agent-plugins-standard-adoption.md> |
| PK-COMMENT-1 | Historical lead, 2026-08-24 | Prior research checkpoint only | <https://github.com/nisavid/provingkit/issues/1#issuecomment-5498560106> |
| PK-COMMENT-2 | Historical lead, 2026-08-24 | Prior fact-matrix leads only | <https://github.com/nisavid/provingkit/issues/1#issuecomment-5498560152> |
| AP-SPEC | Immutable `agent-plugins-spec@bd383552095128f6effe895b9257cfd580a6d179` | v1.0.0 package, components, loading, version scope | <https://github.com/agentplugins/agent-plugins-spec/blob/bd383552095128f6effe895b9257cfd580a6d179/spec/1.0.0.md> |
| AP-CLIENTS | Immutable site source `c4a3a8dc683838f14d178392aaeaabeba4533377` | Listed compatible clients/components | <https://github.com/agentplugins/agent-plugins-site/blob/c4a3a8dc683838f14d178392aaeaabeba4533377/lib/compatible-clients.ts> |
| OAI-APP | Moving official docs | Unified desktop app and platform download surface | <https://developers.openai.com/codex/app> |
| OAI-CHATGPT-APP | Moving official docs | macOS Apple Silicon DMG route | <https://learn.chatgpt.com/docs/app> |
| OAI-MAC-REQ | Moving Help Center | Unified ChatGPT macOS app scope and macOS 14 support on Apple Silicon M1+ or Intel | <https://help.openai.com/en/articles/9395554-what-are-the-system-requirements-for-the-chatgpt-macos-app> |
| OAI-MAC-DOWNLOAD | Moving Help Center | Processor-detecting Mac installer selection route; Intel package format not stated | <https://help.openai.com/en/articles/9275200-downloading-the-chatgpt-macos-app> |
| OAI-APP-MIGRATION | Moving Help Center | Codex-to-unified-app migration and invocation | <https://help.openai.com/en/articles/20001276-moving-to-the-new-chatgpt-desktop-app> |
| OAI-LINUX | Moving official docs | Linux preview packages, support set, updates | <https://learn.chatgpt.com/docs/linux/linux-app> |
| OAI-WINDOWS | Moving official docs | Windows web/WinGet and Store-signed x64/Arm64 MSIX routes, unavailable standalone MSI/non-Store EXE, and updates | <https://learn.chatgpt.com/docs/enterprise/windows-deployment> |
| OAI-WINDOWS-REQ | Moving Help Center | Windows 10 build 17763+ support on x64/Arm64 | <https://help.openai.com/en/articles/9982051-using-the-chatgpt-windows-app> |
| OAI-UPDATES | Moving official docs | App self-update, managed disablement, no OpenAI pin | <https://learn.chatgpt.com/docs/enterprise/manage-app-updates> |
| OAI-PLUGIN-DOC | Moving official docs | Plugin install/use/invoke/remove and supported surfaces | <https://developers.openai.com/codex/plugins> |
| OAI-BUILD-PLUGIN | Moving official docs | Native package/marketplace/source/cache shapes | <https://developers.openai.com/plugins/build/plugins> |
| OAI-PLUGIN-MGMT | Moving official docs | Workspace Git import, fixed commit, sync, retention | <https://developers.openai.com/codex/enterprise/plugin-management> |
| OAI-CLI | Moving official docs | CLI install/update/invocation | <https://developers.openai.com/codex/cli> |
| OAI-CHANGELOG | Moving official changelog | Versioned npm/tag examples | <https://developers.openai.com/codex/changelog> |
| OAI-CODEX-1534-RELEASE | Official GitHub release `rust-v0.153.4`, published 2026-09-04 and observed 2026-09-07 | Release identity and `codex-package_SHA256SUMS` asset presence | <https://github.com/openai/codex/releases/tag/rust-v0.153.4> |
| OAI-CODEX-1534-SUMS | Exact release-asset bytes; SHA-256 `645fb8d4a1f821357a7160f04a6d15bf54ff97ab6946a79239c551ebed734d23`, 1,392 bytes | SHA-256 values for 12 named `codex-package` and `codex-app-server-package` `.tar.gz` archives only | <https://github.com/openai/codex/releases/download/rust-v0.153.4/codex-package_SHA256SUMS> |
| OAI-CODEX-README | Immutable `openai/codex@7769bccbb2b4e9469a36b12510e73594fa03c5d5` | Product installers, packages, platform archives | <https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/README.md> |
| OAI-CODEX-MAIN | Same immutable source | CLI version/update commands | <https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/cli/src/main.rs> |
| OAI-CODEX-UPDATES | Same immutable source | Startup update discovery by install method | <https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/tui/src/updates.rs> |
| OAI-PLUGIN-NS | Same immutable source | Agent Plugins schema recognition and manifest precedence | <https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/utils/plugins/src/plugin_namespace.rs> |
| OAI-AGENT-MANIFEST | Same immutable source | Standard skills/MCP and Codex extension mapping | <https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/core-plugins/src/agent_plugin_manifest.rs> |
| OAI-LOADER | Same immutable source | Direct-child loading and standard/native boundaries | <https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/core-plugins/src/loader.rs> |
| OAI-PLUGIN-CLI | Same immutable source | Plugin add/list/remove and observable fields | <https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/cli/src/plugin_cmd.rs> |
| OAI-MARKET-CLI | Same immutable source | Marketplace add/list/upgrade/remove | <https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/cli/src/marketplace_cmd.rs> |
| OAI-MARKET-SRC | Same immutable source | Local/Git/ref/SHA/npm source model | <https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/core-plugins/src/marketplace.rs> |
| OAI-MARKET-ACT | Same immutable source | Resolved revision metadata and activation recovery | <https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/core-plugins/src/marketplace_upgrade/activation.rs> |
| OAI-LOCAL-UPDATE | Same immutable source | Local plugin cachebuster/reinstall/new-session loop | <https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/skills/src/assets/samples/plugin-creator/references/installing-and-updating.md> |
| CC-P1 | Moving official docs | Claude Code install/update/exactness/integrity/uninstall/platforms | <https://code.claude.com/docs/en/installation> |
| CC-P2 | Moving official docs | Claude Code CLI invocation and command syntax | <https://code.claude.com/docs/en/cli-usage> |
| CC-E1 | Moving official docs | Plugin discovery/install/update/uninstall | <https://code.claude.com/docs/en/discover-plugins> |
| CC-E2 | Moving official docs | Plugin format/resolution, per-version cache and orphan retention, locked dependencies and npm lifecycle boundary, persistent data/uninstall flags, loading, and observability | <https://code.claude.com/docs/en/plugins-reference> |
| CC-E3 | Moving official docs | Marketplace sources/versioning/update | <https://code.claude.com/docs/en/plugin-marketplaces> |
| CC-E5 | Immutable `anthropics/claude-code@ab9b2cf7bb9e4f98ff264c07a22e46d83c29c558` | Official marketplace example | <https://github.com/anthropics/claude-code/blob/ab9b2cf7bb9e4f98ff264c07a22e46d83c29c558/.claude-plugin/marketplace.json> |
| CC-E6 | Immutable `anthropics/skills@41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f` | Official skills marketplace example | <https://github.com/anthropics/skills/blob/41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f/.claude-plugin/marketplace.json> |
| CD-P1 | Moving official download | Desktop platforms/downloads | <https://claude.com/download> |
| CD-P2 | Moving Help Center | Desktop install, minimum platforms, Linux feature limits, invocation, and Linux update behavior | <https://support.claude.com/en/articles/10065433-install-claude-desktop> |
| CD-P3 | Moving Help Center | macOS package/deployment | <https://support.claude.com/en/articles/12611117-deploy-claude-desktop-for-macos> |
| CD-P4 | Moving Help Center | Windows MSIX/deployment/update and installed package/version observation | <https://support.claude.com/en/articles/12622703-deploy-claude-desktop-for-windows> |
| CD-P5 | Moving Help Center | Enterprise updater ownership | <https://support.claude.com/en/articles/12622667-enterprise-configuration-for-claude-desktop> |
| CD-P6 | Moving Help Center | `claude://` invocation | <https://support.claude.com/en/articles/14729294-open-claude-desktop-with-a-link> |
| CD-G1 | Moving Help Center; conflicts with CD-G4 on Chat applicability | Shared format pointer, Help Center plugin surfaces, install, invoke, and uninstall | <https://support.claude.com/en/articles/13837440-use-plugins-in-claude> |
| CD-G2 | Moving Help Center | Organization ZIP/Git sync and policy | <https://support.claude.com/en/articles/13837433-manage-plugins-for-your-organization> |
| CD-G3 | Moving Help Center | Unified directory/discovery | <https://support.claude.com/en/articles/14328846-browse-skills-connectors-and-plugins-in-one-directory> |
| CD-G4 | Moving official docs; conflicts with CD-G1 on Chat applicability | Cowork/Code plugin scope, update, loading, and use | <https://claude.com/docs/cowork/guide/plugins> |
| CD-X1 | Moving Help Center | MCPB directory/private install, update, loading, invocation, registry refresh, status, and logs | <https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop> |
| CD-X2 | Moving Help Center | Extension allowlist and same-name higher-version update | <https://support.claude.com/en/articles/12592343-enabling-and-using-the-desktop-extension-allowlist> |
| MCPB-README | Immutable `modelcontextprotocol/mcpb@70fe3b34cd6dff1b3bba046638edc72a6467a4fb` | Bundle/archive model and host scope | <https://github.com/modelcontextprotocol/mcpb/blob/70fe3b34cd6dff1b3bba046638edc72a6467a4fb/README.md> |
| MCPB-MANIFEST | Same immutable source | Manifest fields/server types/version inconsistency | <https://github.com/modelcontextprotocol/mcpb/blob/70fe3b34cd6dff1b3bba046638edc72a6467a4fb/MANIFEST.md> |
| MCPB-CLI | Same immutable source | `mcpb init` and `mcpb pack` | <https://github.com/modelcontextprotocol/mcpb/blob/70fe3b34cd6dff1b3bba046638edc72a6467a4fb/CLI.md> |
| CUR-DOWNLOAD | Moving official page | Current/prior desktop downloads; ARM64 and x64 RPM and AppImage artifact labels | <https://cursor.com/download> |
| CUR-QUICKSTART | Moving official docs | macOS 12+ Apple Silicon/Intel, Windows 10+, Debian/Ubuntu APT `amd64`/`arm64`, and RHEL/Fedora DNF routes | <https://cursor.com/docs/get-started/quickstart> |
| CUR-DEPLOY | Moving official docs | Managed updates, modes, version floors | <https://cursor.com/docs/enterprise/deployment-patterns> |
| CUR-TROUBLE | Moving official docs | Manual update, Stable/Early Access streams, and macOS reinstall fragments | <https://cursor.com/help/troubleshooting/install-issues> |
| CUR-AGENT-ISSUES | Moving official docs | About/version, Desktop agent diagnostics, and log export | <https://cursor.com/help/troubleshooting/agent-issues> |
| CUR-EXT | Moving official docs | Separate Open VSX extension plane | <https://cursor.com/help/customization/extensions> |
| CUR-PLUGIN | Moving official docs | Plugin formats/surfaces/install/update/invocation/policy | <https://cursor.com/docs/plugins> |
| CUR-PLUGIN-REF | Moving official docs | Cursor manifest/component/source contract | <https://cursor.com/docs/reference/plugins> |
| CUR-CATALOG | Immutable `cursor/plugins@93b00b89ef425a9c1bac0d0b317dfc49c930ac99` | Official repository/marketplace shape | <https://github.com/cursor/plugins/blob/93b00b89ef425a9c1bac0d0b317dfc49c930ac99/README.md> |
| CUR-SCHEMA | Same immutable source | Cursor plugin schema/version floors | <https://github.com/cursor/plugins/blob/93b00b89ef425a9c1bac0d0b317dfc49c930ac99/schemas/plugin.schema.json> |
| CUR-MARKET-SCHEMA | Same immutable source | Marketplace schema and source conflict | <https://github.com/cursor/plugins/blob/93b00b89ef425a9c1bac0d0b317dfc49c930ac99/schemas/marketplace.schema.json> |
| CUR-CLI-INSTALL | Moving official docs | CLI install, platform, update, and version observation | <https://cursor.com/docs/cli/installation> |
| CUR-INSTALL-SH | Moving official installer; exact fetched bytes SHA-256 `e3f0427f5391edeb3cf22f78d340281cffb192255496eeeaca8b6c4d0c34330f` | Unix installer-selected build and installation layout | <https://cursor.com/install> |
| CUR-INSTALL-PS | Moving official installer; exact fetched bytes SHA-256 `400536224b5d8945b550bd45ba57902a3b500b2bb39bbfb01b35d0d3c3bf6d17` | Windows installer-selected build and installation layout | <https://cursor.com/install?win32=true> |
| CUR-CLI-OVERVIEW | Moving official docs | Interactive/headless invocation | <https://cursor.com/docs/cli/overview> |
| CUR-CLI-PARAMS | Moving official docs | `--plugin-dir`, version/about/update/output | <https://cursor.com/docs/cli/reference/parameters> |
| CUR-CLI-SLASH | Moving official docs | `/plugin`, `/update`, logs | <https://cursor.com/docs/cli/reference/slash-commands> |
| CUR-CLI-CONFIG | Moving official docs | CLI channel/configuration | <https://cursor.com/docs/cli/reference/configuration> |
| CUR-CLI-MCP | Moving official docs | MCP source/status/tools | <https://cursor.com/docs/cli/mcp> |
| CUR-CLI-ACP | Moving official docs | ACP transport and logging | <https://cursor.com/docs/cli/acp> |
| CUR-CLI-CHANGELOG | Moving official changelog | January 2026 `--disable-auto-update`; March 2026 `/plugin` install/uninstall scope; August 11, 2026 Windows uninstaller with optional Cursor user-data deletion; plugin marketplace commands/ref support, reload behavior, and updater notes | <https://cursor.com/docs/cli/changelog> |

## 13. Non-authority statement

Nothing in this report grants or implies release eligibility, production readiness, installation, publication, signing, credential access, deployment, rollback actuation, issue closure, or host mutation authority. Moving documentation, source-observed behavior, marketplace visibility, semantic version equality, and successful discovery are each evidence only at their stated layer.

[PK-I1]: https://github.com/nisavid/provingkit/issues/1
[PK-CONTEXT]: https://raw.githubusercontent.com/nisavid/provingkit/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/CONTEXT.md
[PK-CONTRIB]: https://raw.githubusercontent.com/nisavid/provingkit/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/CONTRIBUTING.md
[AP-SPEC]: https://github.com/agentplugins/agent-plugins-spec/blob/bd383552095128f6effe895b9257cfd580a6d179/spec/1.0.0.md
[AP-CLIENTS]: https://github.com/agentplugins/agent-plugins-site/blob/c4a3a8dc683838f14d178392aaeaabeba4533377/lib/compatible-clients.ts
[OAI-APP]: https://developers.openai.com/codex/app
[OAI-CHATGPT-APP]: https://learn.chatgpt.com/docs/app
[OAI-APP-MIGRATION]: https://help.openai.com/en/articles/20001276-moving-to-the-new-chatgpt-desktop-app
[OAI-MAC-REQ]: https://help.openai.com/en/articles/9395554-what-are-the-system-requirements-for-the-chatgpt-macos-app
[OAI-MAC-DOWNLOAD]: https://help.openai.com/en/articles/9275200-downloading-the-chatgpt-macos-app
[OAI-WINDOWS-REQ]: https://help.openai.com/en/articles/9982051-using-the-chatgpt-windows-app
[OAI-LINUX]: https://learn.chatgpt.com/docs/linux/linux-app
[OAI-WINDOWS]: https://learn.chatgpt.com/docs/enterprise/windows-deployment
[OAI-UPDATES]: https://learn.chatgpt.com/docs/enterprise/manage-app-updates
[OAI-PLUGIN-DOC]: https://developers.openai.com/codex/plugins
[OAI-BUILD-PLUGIN]: https://developers.openai.com/plugins/build/plugins
[OAI-PLUGIN-MGMT]: https://developers.openai.com/codex/enterprise/plugin-management
[OAI-CLI]: https://developers.openai.com/codex/cli
[OAI-CHANGELOG]: https://developers.openai.com/codex/changelog
[OAI-CODEX-1534-RELEASE]: https://github.com/openai/codex/releases/tag/rust-v0.153.4
[OAI-CODEX-1534-SUMS]: https://github.com/openai/codex/releases/download/rust-v0.153.4/codex-package_SHA256SUMS
[OAI-CODEX-README]: https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/README.md
[OAI-CODEX-MAIN]: https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/cli/src/main.rs
[OAI-CODEX-UPDATES]: https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/tui/src/updates.rs
[OAI-PLUGIN-NS]: https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/utils/plugins/src/plugin_namespace.rs
[OAI-AGENT-MANIFEST]: https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/core-plugins/src/agent_plugin_manifest.rs
[OAI-LOADER]: https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/core-plugins/src/loader.rs
[OAI-PLUGIN-CLI]: https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/cli/src/plugin_cmd.rs
[OAI-MARKET-CLI]: https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/cli/src/marketplace_cmd.rs
[OAI-MARKET-SRC]: https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/core-plugins/src/marketplace.rs
[OAI-MARKET-ACT]: https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/core-plugins/src/marketplace_upgrade/activation.rs
[OAI-LOCAL-UPDATE]: https://github.com/openai/codex/blob/7769bccbb2b4e9469a36b12510e73594fa03c5d5/codex-rs/skills/src/assets/samples/plugin-creator/references/installing-and-updating.md
[CC-P1]: https://code.claude.com/docs/en/installation
[CC-P2]: https://code.claude.com/docs/en/cli-usage
[CC-E1]: https://code.claude.com/docs/en/discover-plugins
[CC-E2]: https://code.claude.com/docs/en/plugins-reference
[CC-E3]: https://code.claude.com/docs/en/plugin-marketplaces
[CC-E5]: https://github.com/anthropics/claude-code/blob/ab9b2cf7bb9e4f98ff264c07a22e46d83c29c558/.claude-plugin/marketplace.json
[CC-E6]: https://github.com/anthropics/skills/blob/41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f/.claude-plugin/marketplace.json
[CD-P1]: https://claude.com/download
[CD-P2]: https://support.claude.com/en/articles/10065433-install-claude-desktop
[CD-P3]: https://support.claude.com/en/articles/12611117-deploy-claude-desktop-for-macos
[CD-P4]: https://support.claude.com/en/articles/12622703-deploy-claude-desktop-for-windows
[CD-P5]: https://support.claude.com/en/articles/12622667-enterprise-configuration-for-claude-desktop
[CD-P6]: https://support.claude.com/en/articles/14729294-open-claude-desktop-with-a-link
[CD-G1]: https://support.claude.com/en/articles/13837440-use-plugins-in-claude
[CD-G2]: https://support.claude.com/en/articles/13837433-manage-plugins-for-your-organization
[CD-G3]: https://support.claude.com/en/articles/14328846-browse-skills-connectors-and-plugins-in-one-directory
[CD-G4]: https://claude.com/docs/cowork/guide/plugins
[CD-X1]: https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop
[CD-X2]: https://support.claude.com/en/articles/12592343-enabling-and-using-the-desktop-extension-allowlist
[MCPB-README]: https://github.com/modelcontextprotocol/mcpb/blob/70fe3b34cd6dff1b3bba046638edc72a6467a4fb/README.md
[MCPB-MANIFEST]: https://github.com/modelcontextprotocol/mcpb/blob/70fe3b34cd6dff1b3bba046638edc72a6467a4fb/MANIFEST.md
[MCPB-CLI]: https://github.com/modelcontextprotocol/mcpb/blob/70fe3b34cd6dff1b3bba046638edc72a6467a4fb/CLI.md
[CUR-DOWNLOAD]: https://cursor.com/download
[CUR-QUICKSTART]: https://cursor.com/docs/get-started/quickstart
[CUR-DEPLOY]: https://cursor.com/docs/enterprise/deployment-patterns
[CUR-TROUBLE]: https://cursor.com/help/troubleshooting/install-issues
[CUR-AGENT-ISSUES]: https://cursor.com/help/troubleshooting/agent-issues
[CUR-EXT]: https://cursor.com/help/customization/extensions
[CUR-PLUGIN]: https://cursor.com/docs/plugins
[CUR-PLUGIN-REF]: https://cursor.com/docs/reference/plugins
[CUR-CATALOG]: https://github.com/cursor/plugins/blob/93b00b89ef425a9c1bac0d0b317dfc49c930ac99/README.md
[CUR-SCHEMA]: https://github.com/cursor/plugins/blob/93b00b89ef425a9c1bac0d0b317dfc49c930ac99/schemas/plugin.schema.json
[CUR-MARKET-SCHEMA]: https://github.com/cursor/plugins/blob/93b00b89ef425a9c1bac0d0b317dfc49c930ac99/schemas/marketplace.schema.json
[CUR-CLI-INSTALL]: https://cursor.com/docs/cli/installation
[CUR-INSTALL-SH]: https://cursor.com/install
[CUR-INSTALL-PS]: https://cursor.com/install?win32=true
[CUR-CLI-OVERVIEW]: https://cursor.com/docs/cli/overview
[CUR-CLI-PARAMS]: https://cursor.com/docs/cli/reference/parameters
[CUR-CLI-SLASH]: https://cursor.com/docs/cli/reference/slash-commands
[CUR-CLI-CONFIG]: https://cursor.com/docs/cli/reference/configuration
[CUR-CLI-MCP]: https://cursor.com/docs/cli/mcp
[CUR-CLI-ACP]: https://cursor.com/docs/cli/acp
[CUR-CLI-CHANGELOG]: https://cursor.com/docs/cli/changelog
