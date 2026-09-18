# Review and publication handoff regression evidence

This experiment records correct decisions for 15 review/publication and dispatch decisions
under their supplied premises.
It preserves bounded regression evidence for
[issue #104](https://github.com/nisavid/provingkit/issues/104).
The separate [issue #33](https://github.com/nisavid/provingkit/issues/33)
evaluation framework and [strict control-plane evaluation](../README.md)
retain their own qualification requirements.

## Protocol and result

The cooperative probes used native subagents with `fork_turns: none`, frozen
workflow source, and case prompts asking for decisions without critic dispatch
or forge mutation. That context setting does not prove that ambient tools,
repository access, or policy were absent. The retained JSON files are response
artifacts, not provider streams or tool-event traces.

The baseline probe applied the ordinary-admission case to source at commit
`147e1ddfc969b5119001488ce1556627d3b2449b`. Its
[response](baseline/response.json) blocked at the unconditional authenticated
adapter-receipt gate. This is one baseline observation, not a complete
comparative matrix.

The candidate probes each answered the nine handoff [cases](cases): ordinary admission,
ordinary clean handoff, unavailable witnessed evidence, nonclean terminals,
candidate drift, dependency drift, resume without observations, stronger
ordinary assurance minima, and status-only work. Six additional cases exercise
ordinary selection-record absence, a valid four-execution plan, unauthorized
user-owned tasks, shared foreign contexts, prohibited delegated powers, and
unavailable witnessed receipts. These six prompts are byte-identical to their
corresponding packaged Tricritical fixtures. After all three runs finished,
a separate grader received their explanations, [criteria](grading-criteria.json),
cases, and frozen source. It checked each expectation against reasoning and
conditions rather than accepting action labels. The grader was not blinded to
source or run identity.

[Grading](grading.json) records 90 passing expectations and no failures across
45 case-runs. Each run contributes 30 expectations.
[Probe 1](probe-1.json), [probe 2](probe-2.json), and [probe 3](probe-3.json) retain
their complete response bytes. The baseline result is outside that total.

For a fresh regression run, first verify the intended source and case bytes.
Give fresh probe contexts the case prompts and that source; keep the criteria
grader-side until every response is complete. Then have a separate grader
assess every explanation and retain failures and uncertainty. Record the
actual context/tool boundary and new source identities with the new results;
these passes do not transfer to changed inputs. This is a decision-probe
protocol, not authority to perform the workflows described by the cases.

## Source and artifact identities

[Baseline manifest](baseline/manifest.json) binds 119 repository-relative paths
to SHA-256 digests and the baseline commit. Retrieve each baseline file with
`git show <source_commit>:<repo-path>` and verify its digest. The
[candidate manifest](candidate/manifest.json) binds 119 paths to the tested
candidate bytes. Retrieve those paths from a repository revision matching all
recorded hashes; at capture, every entry matched the working candidate. Keep
the matching source revision reachable when publishing this evidence. Neither
manifest authenticates execution or qualifies a runtime.

Source trees are not duplicated here. Resolve retained references as follows:

- `cases/<name>.md`, `probe-*.json`, and `grading-criteria.json` are relative to
  this directory. A response's bare `case` filename resolves under `cases/`.
- `candidate/<repo-path>` identifies the repository path and digest in
  `candidate/manifest.json`; it is not a file beneath this directory's
  `candidate/` directory.
- Bare `plugins/...` evidence paths in candidate responses identify entries in
  the candidate manifest. In `baseline/response.json`, they identify entries in
  the baseline manifest and its recorded commit.
- Grading JSON pointers address the retained probe arrays. Its `input_sha256`
  entries use the same artifact and candidate-source mapping.

All 23 retained input/output artifacts are byte-preserved. `SHA256SUMS` binds
them and this README. From the repository root, verify them with:

```sh
(cd evals/review-publication-handoffs && sha256sum -c SHA256SUMS)
```

## Evidence limits

The grader records the limits of the supplied premises, conditional future
routes, foreign enforcement, report retention, publication, coverage, and
experimental scope. Execution and isolation were not observed. Positive
ordinary cases supply complete plans and clean results; no actual report
retention, successful witnessed publication, or qualified foreign route was
exercised.

The results establish decisions within those premises. They establish no actual
critic launch, completed review loop, verification execution, forge actuation,
enforced tool isolation, authenticated review provenance, or effective-model
attestation. They make no statistical reliability claim and do not satisfy the
four-condition matrix, blinding, trace, isolation, or qualification requirements
of the strict control-plane evaluation.
