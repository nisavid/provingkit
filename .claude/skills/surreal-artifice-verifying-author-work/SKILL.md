---
name: surreal-artifice-verifying-author-work
description: Use when preparing to request independent review of agent-equipment changes or consequential operational scripts, to run proportionate author checks and hand off evidence.
---

# Verify Author Work

Use this Surreal Artifice procedure before the first independent review of an
agent-equipment change or consequential operational script. The author owns
these checks; independent review and adjudication retain their own owners.

## Select the checks

Bind the intended behavior, candidate revision or content digest, changed
interfaces, supported inputs, consequences, and repository requirements. Choose
the smallest existing checks that can falsify those claims. Run applicable
parsing, typing, lint, schema, and package checks first, followed by focused
behavioral checks where the claim needs them. Use broader integration or live
checks only when needed and authorized. A prose-only correction may need no new
test suite. Reuse the repository's engineering and evaluation procedures rather
than creating a parallel runner.

For a decision-bearing operation, exercise the actual caller and decision branch.
Where a live effect is unsuitable, replace only the final effect with an inert
recorder while keeping the live validation and decision logic. Distinguish a
detached predicate check from evidence for an actual caller. Choose cases from
the supported contract: include a valid control and applicable malformed,
incomplete, wrong-type, or wrong-identity inputs. Keep each effect and its own
freshness check distinct. Admission retains its own schema, permission and
freshness rules; this procedure does not grant authority or replace them.

## Run and hand off

Run the selected checks against the bound candidate before requesting review.
Repair a failing required check or return the concrete blocker. Report unavailable
or unrun checks and the resulting limit rather than claiming a pass. When changes
invalidate the candidate or a check's dependencies, rerun the affected evidence;
retain unchanged evidence only when its dependencies remain unchanged.

Hand the reviewer the candidate identity, each command or check actually run,
its observed result, the exercised interface, and material limits. Separate a
synthetic recorder's result from live behavior. A mechanical pass supplies evidence
for review; it does not replace independent judgment, review, or adjudication.
