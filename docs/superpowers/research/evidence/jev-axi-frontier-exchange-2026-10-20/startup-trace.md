# The alias warning does not identify the fatal startup failure

The retained compatibility preparation ended before an initialize response,
with exit status 1 and zero native author tasks. Its stderr contains a warning
about creating PATH aliases, followed by a separate read-only-filesystem error.
The [retained failure summary](https://github.com/nisavid/provingkit/issues/471#issuecomment-6222115045)
does not name a failing path. Source inspection narrows the investigation but
does not establish the fatal operation.

## Source binding

The public `rust-v0.162.1` tag resolves through tag object
`7a078f6bb4ce0dc2a81408b334ce52979d92c603` to commit
`092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`. This is version-tagged source
correspondence, not a reproducible-build attestation for the formerly installed
binary. The original executable's path was checked again and is absent.
No replacement executable was selected or run.

## Startup operations visible in source

| Stage | Source fact | Consequence |
| --- | --- | --- |
| Helper aliases | `path_setup_with_package_path` catches alias preparation errors, prints the matching warning, and returns a fallback PATH. | This warning is deliberately nonfatal. It does not prove the later error shares its cause. |
| Alias state | `prepare_path_entry_for_codex_aliases` creates the Codex home and its `tmp/arg0` directory, sets directory permissions, creates a temporary directory and lock, and prepares helper aliases. | These are concrete startup write requirements for that code path; the retained record does not identify which one failed. |
| CLI dispatch | Plain `app-server --stdio` selects stdio and calls `run_main_with_transport_options`. | The relevant path is the CLI dispatcher, not only the standalone app-server binary's main function. |
| Server bootstrap | Startup resolves the home and runtime paths, loads configuration, initializes authentication and environment management, and later initializes SQLite state. Several errors propagate before initialization completes. | A bare filesystem error does not distinguish these paths. The examined top-level SQLite failure adds a specific diagnostic prefix, which is absent in the retained stderr; this is a source clue, not a complete exclusion of all storage-related failures. |

Primary source:

- [Alias warning and continuation](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/arg0/src/lib.rs#L180)
- [Helper-directory and lock preparation](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/arg0/src/lib.rs#L340)
- [CLI app-server dispatch](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/cli/src/main.rs#L1237)
- [Server startup](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/app-server/src/lib.rs#L496)
- [Strict startup configuration handling](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/app-server/src/config_manager.rs#L321)

This is a partial startup dependency trace. It does not exhaust every
transitively called function, identify a syscall from the failed process, or
establish a sufficient writable-path set.

A separate file-only inventory found an existing Node entrypoint whose package
declares `@openai/codex` version `0.147.0`, with a native binary of 258,278,208
bytes and SHA-256
`cb0a15567e9a60a5820d54b0f6ae86d504dc3805c1eab21a47f70e3eb7b73a40`.
The PATH command resolves to a secret-exec wrapper; this inspection does not
establish which runtime that wrapper launches. Neither wrapper nor binary was
invoked. The older package's presence supplies no reason to substitute it for
the original `0.162.1` runtime.

## Minimum useful continuation

First inventory a current runtime candidate and bind its package/version,
binary identity, matching source, supported arguments, and the six metadata
RPCs required by the collector. Historical source checks do not prove its
current interface.

Then prepare one bounded metadata-only diagnostic proposal that identifies
the operation and path if startup fails before initialize. Its collection
method must avoid recording credential contents, unrelated process activity,
or arbitrary file contents. Any diagnostic implementation or changed security
boundary requires the applicable review before execution. Keep ordinary
authoring, provider assessments, and comparison trials out of that preparation.

The proposal must state exactly which local-state writes the selected runtime
requires and how they affect the representative profile. It must preserve the
two original attempts and stop on a failed or incomplete initialization rather
than try a new executable, writable root, or profile automatically. A successful
metadata pass would still only enable review of the observation contract.
