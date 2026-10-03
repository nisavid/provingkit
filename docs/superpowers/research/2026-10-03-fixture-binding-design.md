# Identify the fixture's executable and metadata directory

The disposable fixture can obtain a concrete Code-process witness from its own Stop hook. The source also identifies how Desktop chooses the metadata directory, but that directory still needs an independent binding to the selected profile. Neither mechanism has been implemented or observed on a live fixture.

This resolves the source investigation in [Bind the fixture executor and acquisition scope](https://github.com/nisavid/provingkit/issues/410). [Prepare and review the disposable observer probe](https://github.com/nisavid/provingkit/issues/278) owns choosing and integrating the design into an exact proposal. Full-state qualification continues independently under [Choose how to close runtime-state qualification gaps](https://github.com/nisavid/provingkit/issues/411#issuecomment-5972858593).

## What the source establishes

The [exact research report](2026-10-03-fixture-binding-sources/research.md) contains the retained source identities, byte spans, path formulas, acquisition alternatives, and limitations.

- Desktop places its task identity in the spawn environment and later associates the Code-reported session ID with its own metadata record.
- Code passes its own PID and hook session identity to the command hook. A shell or launcher may sit between Code and the collector, so the collector's PID or immediate parent alone does not identify Code.
- Desktop also retains a Code-reported PID while the corresponding local query is current. That internal field is a possible app observation; this research establishes no externally callable reader for it.
- Desktop constructs its metadata directory from the running manager's user-data root, base directory, account ID, and organization ID. The hook socket and Code's config home do not supply that tuple.
- A single PID-derived Code registry record can support the identity join. It requires a separately known registry root and a separate read scope. Existing scanning/cleanup helpers are unsuitable for an exact-file observation.

The report concerns the retained Desktop and Code artifacts named by their digests. It does not identify the executable currently selected by Desktop. An unmatched build remains unassessed under the accepted graduated compatibility policy; a hash difference alone does not establish incompatibility.

## Proposed next mechanism

For the assessed local native Code case, the least app integration in the researched design is:

1. Independently bind the selected Desktop profile and the one account/organization metadata directory.
2. At the admitted Stop hook, retain the bounded Code PID, Code ID, optional Desktop host ID, and socket value.
3. Observe a bounded parent chain from that collector to the claimed Code PID. Read the selected process's executable as data and compare it with the assessed artifact.
4. Join the independently selected UI fixture and whole setup response to the event and a unique current metadata match among the authorized candidates.
5. Preserve separate observation intervals and partial outcomes. Recheck only the lifecycle facts covered by the eventual packet.

The executable read would acquire about 243 MB for the inspected native artifact. Its elapsed cost is unmeasured. The command's existing stdin timeout is not a deadline for this additional stage. A process that disappears, a wrapper chain beyond the chosen bound, or an interpreter-based executor yields an explicit gap. This observation would establish which executable was opened near the hook invocation; it would not prove unchanged execution throughout the turn.

The optional registry read adds a private file and recorded host/Code/socket/start-time associations. It cannot substitute for the actual executable observation. Keep it optional unless a particular missing join requires it.

If the selected profile root and current manager account/organization pair cannot be supplied independently, the remaining app gap is precise: a projection from the already loaded manager of its selected task, storage directory, Code ID/PID, and query/lifecycle identity. That projection remains a proposed adapter, with access, installation, interruption, and restoration costs to decide. Parent listings can nominate directories but do not establish the active selection.

## Acquisition choices still to settle

The accepted design limits inside one bound account/organization directory remain 128 nonrecursive entries plus one overflow entry and at most three selected metadata files, each limited to 1 MiB plus one overflow byte. They are design limits, not an authorization to read those files.

The research proposes additional limits for the process witness: at most six selected PIDs, up to twelve bounded stat reads, two executable-link/target observations, and one bounded whole-executable read. Its optional registry alternative proposes up to two reads of one exact file, each limited to 256 KiB plus one overflow byte. These are proposals for later selection. No process, executable, registry, profile, settings, or private metadata read is authorized by this report. References to a grant in the retained research describe a prospective live grant; the accepted directory limits themselves carry no read permission.

Before source implementation or a live proposal, the preparer must settle:

- how the selected profile root and current account/organization directory are independently bound;
- whether the hook process/executable witness is the selected mechanism, and whether the optional registry record adds necessary evidence;
- the exact supported process/launcher shape, named environment values, acquisition caps, observation-stage deadline, and failure behavior;
- the maximum join age and the concrete selection/lifecycle recheck;
- the new implementation test boundary and applicable private-data/control review;
- exact setup, integration, cleanup, and restoration inputs.

Only the first two choices select an observation mechanism. Numerical limits and an executable digest are not claims of producer authentication, containment, or protection from hostile processes. Those properties have not been assessed here.

## Preparation and capture contract

The current collector does not implement the proposed witness. A later preparer must load this design, its retained source report, and the [published collector contract](../prototypes/receiver-evidence/collector-contract.md) and [fixture procedure](../prototypes/receiver-evidence/fixture-check-procedure.md), recording the reviewed revisions consumed. It then integrates only the selected alternative, reviews the final source and acquisition proposal, and returns any remaining decision before requesting live authorization.

Keep UI/Code association, directory binding, event-time endpoint, actual executable observation, hook behavior, lifecycle recheck, and restoration as distinct results. A successful subset remains useful partial evidence. The setup response establishes no notification delivery or correlated acknowledgment. The old receipt mechanism's restart plan and 15-minute acquisition deadline do not apply automatically.

This is a provisional source procedure under `capturing-agent-procedures`. Publication makes the design available for preparation; it does not install an operating skill or qualify the route. Return useful corrections to this source. No live receiver action or source implementation was performed in this research increment.
