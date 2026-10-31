# Explicit Cloud coordination entrypoint

Explicitly ask the current thread to load this `BOOTSTRAP.md` by its actual
readable path. Open `MANIFEST.json` beside this file and resolve its locators
relative to the manifest's directory. Verify its file hashes and the exact
runtime receipt SHA-256, then load `runtime.skills.delegating_cross_agent_work`,
`runtime.skills.choosing_agent_models`, and `runtime.driver.reference`. Use the
manifest's `runtime.driver.script` when operating the driver. This loads the
pinned runtime even when the installed catalog still contains older skills.

Load the pinned [Cloud coordination procedure](README.md) and
[role policy](role-policy.md). Start with the current thread as Concierge;
activate other roles only when useful, authorized, and supported.

A distribution owner supplies the actual readable bootstrap locator and
retains its manifest and exact source/runtime identities. This explicit
pointer claims no installed release or automatic startup. A checkout copy
without a manifest does not select a pinned runtime. If required files are
unavailable or fail integrity checks, continue useful authorized
single-agent work and report the limitation when material. Do not install,
download, or recursively bootstrap during discovery.
