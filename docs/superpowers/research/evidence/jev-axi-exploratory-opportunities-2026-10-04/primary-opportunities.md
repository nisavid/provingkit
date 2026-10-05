# Lifecycle-hook research opportunities

Primary sources support exploring narrower completion checks, evidence-aware supervision, and discovery on demand. They do not establish that Jev earns any particular assignment. A successful ordinary task can still reveal a cheaper design or a useful new purpose; it supplies neither benefit qualification nor grounds to end exploration.

Research date: **2026-10-04**. All three frozen input files matched their recorded SHA-256 digests; the worktree HEAD matched `0d342774f78d730e084eec2144ec5fc7cef598c6`. I read the `research` and `firecrawl` skills. Firecrawl and tool-search capabilities were unavailable in this worker, so I used read-only web search and retrieval with public queries. I made no writes, uploads, external mutations, model or hook calls, tests, or experiments.

## 1. Distinguish completion from yielding before evaluating Stop

**Source finding.** Claude Code’s current reference describes Stop as finishing a response, separately documents task completion, and provides background-task and scheduled-wakeup information to distinguish completion from waiting. It also warns that the transcript may lack the final response at Stop time on some versions. This makes event interpretation and input construction substantive design questions. [Claude Code hooks reference](https://code.claude.com/docs/en/hooks#stop) (undated living documentation; accessed 2026-10-04).

**Proposal.** Construct a small, explicit input describing the current requirement revision, final response, work still in flight, and whether the agent is claiming completion, handing off, or requesting a decision. Use deterministic native state where available; reserve semantic judgment for ambiguous response meaning. A supported task-completion event may be a better placement than Stop.

**Expected benefit.** Fewer irrelevant completeness assessments and fewer interruptions of legitimate pauses.

**Cheap first observation.** Annotate retained Stop records with their actual conversational purpose and available native state. Check what information the integration discarded or never received.

**Unknowns and transfer limits.** These are current Claude Code documentation facts, not installed-version or Codex behavior. Reliable response classification remains unqualified; absence of background work does not establish completion.

## 2. Check the evidence attached to a completion claim

**Source finding.** Anthropic’s public teaching repository records evidence-file reads and gates writes to a results file. Its implementation explicitly permits any recorded evidence read to unlock any result row; it does not establish that evidence supports the particular criterion. The repository identifies itself as an unmaintained event demonstration. [Harness primitives](https://github.com/anthropics/cwc-long-running-agents), [evidence-read gate](https://github.com/anthropics/cwc-long-running-agents/blob/main/claude-code-config/.claude/hooks/verify-gate.sh) (2026 copyright; publication date unspecified; accessed 2026-10-04).

**Proposal.** Explore criterion-specific records connecting a current requirement, a claimed result, and the observed verification. Deterministic checks can establish record presence and revision agreement. Jev might judge a narrowly framed mismatch between the claim and supplied evidence, rather than infer the entire job’s completeness from a diff.

**Expected benefit.** Earlier correction of unsupported completion claims, with reusable context for Stop and Git checks.

**Cheap first observation.** For retained completion claims, identify the evidence actually cited and whether it concerns the same requirement and candidate revision.

**Unknowns and transfer limits.** Reading a file is not verification. Many useful tasks have no structured results file. Creating and maintaining records may cost more than the check saves; the teaching example provides no comparative utility evidence.

## 3. Make review cadence depend on the purpose and workload

**Source finding.** Anthropic reports that a tuned evaluator interacting with applications caught concrete specification gaps. With Opus 4.6, the author removed sprint decomposition and moved evaluation from every sprint to the end of the run. Evaluation became overhead for work the generator handled reliably, while still helping with harder work. The report also describes evaluator leniency and incomplete testing. [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps) (2026-03-24).

**Proposal.** Separate three possible jobs: cheap progress bookkeeping, semantic review when relevant evidence changes, and independent verification of a completed deliverable. Explore triggering review on changed requirements, changed verification, or a completion claim instead of every fixed number of tool calls. A typed Jev assessment could route a bounded question; it cannot substitute for a reviewer that must operate the application.

**Expected benefit.** Avoid recurring assessments of unchanged evidence while preserving review where its consumer can act.

**Cheap first observation.** Classify retained supervision calls by whether new decision-relevant evidence appeared since the preceding call and whether any delivered finding changed work.

**Unknowns and transfer limits.** The engineering report is workload-specific, not a population estimate or evidence for Jev thresholds. More selective cadence could miss early drift. Model upgrades require renewed comparison, not inherited retention or removal.

## 4. Replace recurring discovery prose with a small capability map

**Source finding.** Anthropic describes deferred tool discovery and keeping frequently used tools immediately available. Its internal evaluations report improvements with large tool libraries, but the article explicitly identifies additional search latency and weaker value for small libraries. It also separates discovery problems from parameter-use problems. [Introducing advanced tool use](https://www.anthropic.com/engineering/advanced-tool-use) (2025-11-24).

**Proposal.** SessionStart could expose a compact map of available capabilities and where to obtain current readiness or usage details. Resolve detailed instructions when needed. For recurring parameter errors, supply a short usage example at discovery time rather than another global reminder or semantic classifier.

**Expected benefit.** Less irrelevant startup context and faster access to the right capability.

**Cheap first observation.** Compare actual startup information with the capabilities subsequently used, including discovery calls, wrong selections, and repeated readiness checks.

**Unknowns and transfer limits.** Native discovery may already provide this benefit. Tool metadata availability and indexing differ by harness. Jev is unnecessary when deterministic lookup resolves the question; readiness needs current evidence rather than a cached assertion.

## 5. Share references broadly; prepare judgment context narrowly

**Source finding.** Anthropic recommends lightweight references and loading information as needed, while acknowledging exploration latency and missed-information risks. It describes hybrid approaches rather than a universal preference for retrieval over injection. [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (2025-09-29).

**Proposal.** Maintain shared references to requirements, changes, verification, and unresolved decisions. Prepare a question-specific context package only when an assessment has a consumer. Reuse unchanged preparation across applicable hooks, but invalidate it when requirements, revisions, or verification dependencies change. Missing necessary input should produce an explicit unsupported result.

**Expected benefit.** Less duplicate context construction and fewer judgments based on irrelevant or incomplete material.

**Cheap first observation.** Inspect retained inputs for duplicated bytes, omitted amendments, stale baselines, and unused assessments. Identify which consumer needed each field.

**Unknowns and transfer limits.** References save tokens only if retrieval and maintenance costs remain acceptable. Shared caches can propagate stale evidence. Better input construction does not qualify Jev’s judgment or establish whole-workflow savings.

## 6. Give diagnostics a repair consumer

**Source finding.** OpenAI reports using a short repository entrypoint, deeper versioned documentation, mechanical checks, and actionable lint feedback. Agent difficulties feed improvements to tools and documentation. The article explicitly says its autonomous workflow depends on substantial repository-specific structure and tooling. [Harness engineering](https://openai.com/index/harness-engineering/) (2026-02-11).

**Proposal.** Explore supervision as a source of bounded environment-repair suggestions: for example, repeated failed discovery could identify a missing capability pointer, while repeated verification confusion could identify unclear project instructions. Batch such observations for an authorized maintainer rather than repeatedly steering the active agent.

**Expected benefit.** Fix a recurring cause once instead of paying for repeated classification and intervention.

**Cheap first observation.** Select one retained recurring difficulty, identify its maintainer and concrete possible repair, and check whether existing diagnostics preserve the necessary facts.

**Unknowns and transfer limits.** A log without a consumer earns no assignment. Similar failures may have different causes. Repository repair, publication, and rollout require their own authority; this research supplies none.

## Comparison boundary

These hypotheses vary purpose, placement, context, and implementation independently. Each eventual comparison needs ordinary harness behavior, omission, and a viable deterministic or on-demand alternative. Any Jev replacement must remove observed model work; any addition must produce a useful native effect. Evidence preparation, duplicate review, recovery, maintenance, and operator effort belong in the cost account.

The next decision is which hypotheses deserve a frozen observation contract. Their supported inputs and useful effects remain unqualified.