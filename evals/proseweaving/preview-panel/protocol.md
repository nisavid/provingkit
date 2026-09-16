# Run the Proseweaving preview comparison

This procedure gives the [panel execution task](https://github.com/nisavid/provingkit/issues/71) fixed inputs, grading, and evidence requirements for a with/without Proseweaving comparison. Load it before preparing a run, resuming an interrupted panel, or selecting README examples. Use the preview map's [orchestration contract](https://github.com/nisavid/provingkit/issues/66#issuecomment-5690388354) for ownership and acceptance.

## Entry conditions and scope

The execution owner needs the accepted protocol commit, the qualified preview's source commit and artifact receipts, and the Linux rollout receipt. Record these separately: the preparation source in [panel.json](panel.json) is neither the eventual candidate nor proof of installation. Use `capturing-agent-procedures` to record which reviewed procedure revision was consumed and return corrections to its owner.

Preparation may inspect requirements and model selectors and exercise this procedure with synthetic records. Only issue 71 may generate comparison outputs or publish examples. This is descriptive preview evidence, not a signed-release gate or a claim about models outside the recorded panel. It does not invoke the retained Versionkeeping four-condition release-evaluation gate.

The fixed input panel comprises all seven small cases in the existing corpus: stopping-point report, review reply, three inline comments, status update, release note with a missing decision, editing a finished draft, and explanation for a nontechnical reader. Their prompts, fixtures, and expectations remain at the source revision and digests in `panel.json`. Read [grading.md](grading.md) before any output exists. The [record contract](records.md) defines what must survive execution.

## 1. Freeze the run before generation

1. Resolve every model-panel entry against its recorded operator decision. [Availability](availability.md) is a dated observation, not permission to replace a model. An empty panel, unavailable model, unapproved substitution, or missing exact harness/model/effort identity blocks generation; return that question to the orchestrator. The four subjects and chosen native routes are recorded in `panel.json`; the linked recovered requirement authorizes the subject roster, while harness and effort are reproducible preparation choices. Worker-routing preferences choose preparation and grading workers, not models under test.
2. Compare every pinned source dependency in `panel.json` with the qualified candidate. Equal bytes may retain the prepared prompts and rubric while recording both commits. A changed prompt, fixture, skill, routed reference, delivery contract, or relevant requirement needs a reviewed protocol update before generation. Never silently move the preparation source to `main`.
3. Create a run manifest under the execution task's evidence directory. Record the final protocol commit and file digests, candidate and projection identities, rollout receipt, exact panel, harness versions, generation settings, evaluator identities, and source comparison. A model alias needs both the requested selector and returned model identity when exposed; otherwise disclose that the provider supplies no immutable model identity.
4. Declare two separate tracks. Writing: model/harness entry × seven cases × `disabled`/`enabled` × repetitions 1–3, using the `explicit-bundle` route: 42 writing coordinates per entry, 168 for the four subjects. Routing: the same entries × four fixed routing cases × two conditions × repetitions 1–3: 24 routing coordinates per entry, 96 total. Keep native-route capability gaps visible as blocked coordinates; never shrink either denominator after seeing output. The three repetitions describe variability, not statistical significance.
5. Shuffle execution order and opaque grading IDs with a recorded seed before the first request. Freeze the coordinate list, prompts, grading criteria, sample-selection rule, and serialized launch configuration. Give the orchestrator a digest and reviewable pointer to this pre-output manifest.

Completion: the frozen manifest has no unresolved policy choice, and every writing coordinate has a supported isolated route. Routing capability gaps may remain explicit while writing proceeds; a complete panel result still needs those gaps resolved or accepted by the orchestrator.

## 2. Prepare each fresh session

Keep the tested host configuration fixed. Use disposable, isolated client configurations and fresh conversations; do not edit global client configuration, reuse the leader's conversation, fork its context, resume a prior executor, or run inside the repository with ambient agent instructions. The execution owner establishes the launch recipe using the installed harness's help and the rollout evidence, records it before generation, and verifies it at each session boundary.

For both arms, inventory the effective system/developer instructions, personal/global/project instructions, memories, custom output styles, installed plugins, skill discovery paths, rules, hooks, and tool/MCP configuration that can affect the response. Retain a redacted, digest-bound inventory. Check for duplicated or superseded writing guidance, including the global Writing section, `writing-for-people`, legacy Tidesmith routes, `writing-clearly-and-concisely`, review-voice instructions, and native rules that preload equivalent guidance. Presence in a catalog alone is distinct from loaded content; record both.

The baseline contains the harness's recorded common instructions and the raw task only. The enabled arm differs only in the candidate Proseweaving surface and the declared invocation intervention. Neither arm receives the root task's AGENTS.md, personal voice policy, other Provingkit prose rules, corpus expectations, grading instructions, prior responses, or selected-example hints. If the harness cannot isolate or attest its effective context, report `isolation-unverified` and stop that route; an ordinary new chat is insufficient evidence.

Record separate session/request IDs, configuration digests, timestamps, candidate-bundle identity, and the observable activation trace for each attempt. Store account details only in local operational state; public evidence uses a redacted identity and no credentials or machine-local paths.

Completion: both arms have comparable, independently captured context inventories, and the disabled arm cannot discover or load candidate or superseded writing guidance.

## 3. Distinguish writing behavior from native routing

The writing track explicitly supplies the candidate skill and both routed references as the enabled `candidate_bundle`; the disabled bundle is empty. Raw prompt and fixture bytes are identical. Label these samples `explicit-bundle`: they show writing with the instructions supplied, not proof that a native client selected a skill. Record the normalized request and loaded bundle bytes as activation evidence. The writing executor has no tools, matching the pinned plugin delivery contract.

The separate routing track follows the repository's existing separation of semantic evaluation and observable routing in `evals/README.md`. It uses the four frozen prompts in `panel.json`: cold start, explicit invocation, automatic positive selection, and a nearby negative task. These are selection probes, not permission to carry out the underlying review or other work. Expose only the candidate Proseweaving discovery surface in enabled sessions and none in disabled sessions. Do not load the wider Kit to satisfy the negative case's other-skill expectation: this panel checks only whether `writing-for-people` is selected.

For each probe, use a fresh session with a common, frozen instruction to select any applicable skill and stop before carrying out the task. Permit only the native selection/loading facility and bounded reads of its immutable skill/reference files. Deny shell, other task tools, network tools, and writes. Record the exact discovery inventory, common probe instruction, native invocation syntax, events, loaded file identities, and actual model. The explicit probe may translate the source's `$writing-for-people` token into the qualified projection's verified native syntax; record those exact bytes before generation. Automatic probes contain no skill name or preload.

The enabled cold-start, explicit, and positive cases expect selection; the enabled negative expects no target selection. Every disabled probe expects no target selection. An absent native event with a complete trace is a selection miss or correct non-selection, depending on the case. A response merely claiming selection supplies no evidence. If the client has no observable native selection event or the session cannot restrict its capability as described, record `route-unsupported`; do not infer success from writing quality or a manually injected bundle.

Grade routing as pass/fail against these fixed expectations and retain every attempt. Do not grade or publish routing-probe prose as writing examples, and do not use its selected content to seed a writing session. The tool permission belongs solely to this discovery track; writing remains tool-free. Never label an `explicit-bundle` example automatic on the strength of a separate routing result.

Completion: the writing intervention is explicit and reproducible; all native routing coordinates are observed or carry a concrete capability gap. Report routing results and gaps separately from writing quality.

## 4. Deliver only writing inputs

The coordinator reads the pinned corpus and extracts the chosen case. For example, from the protocol checkout:

```python
import hashlib
import json
import subprocess
from pathlib import Path

panel = json.loads(Path("evals/proseweaving/preview-panel/panel.json").read_text())
source = panel["source_revision"]
def pinned(path):
    return subprocess.check_output(["git", "show", f"{source}:{path}"])

for entry in panel["source_files"]:
    assert hashlib.sha256(pinned(entry["path"])).hexdigest() == entry["sha256"]
corpus = json.loads(pinned(panel["corpus_path"]))
case_id = 7  # Choose the frozen coordinate; do not select by observed quality.
case = next(row for row in corpus["evals"] if row["id"] == case_id)
entry = next(row for row in panel["cases"] if row["id"] == case_id)
raw_input = {"prompt": case["prompt"],
             "fixture": pinned(entry["fixture_path"]).decode("utf-8")}
```

Pass only `prompt`, `fixture`, and the condition's actual `candidate_bundle` to the writing executor, as the pinned `evals/delivery.json` specifies. The enabled candidate bundle contains the skill and both routed references with their qualified-candidate bytes; the disabled bundle is empty. File digests and actual normalized request bytes prove that intervention. Keep manifest metadata, condition labels, corpus expected output, and rubric in coordinator/grader storage. A raw prompt/fixture extraction is not proof of native invocation or isolation. The fragment above only prepares input; it is not a model runner.

Start each executor with tools denied and the frozen generation settings. Retain its complete raw response and metadata even for refusal, truncation, empty output, transport failure, selection miss, or contamination. Do not repair its prose, ask it to improve a score, or append context mid-run.

Allow at most one new-session retry for a transport failure that returned no usable response, using the same frozen coordinate and inputs. Record both attempts and their relationship. Never retry a completed low-scoring, factually wrong, refused, or truncated response. An interrupted run resumes only missing coordinates after revalidating every frozen dependency; it does not reuse executor sessions.

Completion: every required coordinate has its full attempt record, or a named unresolved blocker. Freeze all raw outputs before grading starts.

## 5. Grade, adjudicate, and select

Give a fresh grader, distinct from every writing executor, the case prompt, fixture, pinned expectations, common rubric, and randomized responses identified only by opaque IDs. Keep model, condition, invocation, candidate bundle, and activation metadata hidden during scoring. The delivery contract's allowed grader fields do not require exposing every field; candidate behavior is judged against the fixed rubric. Choose the grader under current operator routing policy and freeze its identity before generation.

Apply `grading.md` to every response. Require evidence for each score and failure, and independently adjudicate all factuality failures, grader disagreements, and proposed examples before unblinding. Preserve the original grading and the reasons for any adjudicated change. Do not tune the rubric after observing outputs; a necessary rubric change starts a new, clearly identified panel with fresh executor outputs.

Unblind only after scoring is frozen. Report per model/harness/route: completion and validity counts, separately measured native selection outcomes, hard-failure counts, quality distributions, and paired enabled-minus-disabled deltas. Separate missing data from zeros and selection failures from writing quality. Apply the fixed sample-selection rule in `grading.md`; a lack of eligible examples is an acceptable observed result, not permission to cherry-pick or rewrite.

Completion: all coordinates are accounted for, every published sample meets the fixed rule, and all claims link to raw, graded, and activation evidence for the tested candidate. Issue 71 owns README edits and publication with the orchestrator's file/publication coordination.

## Changes and return

A changed candidate, effective context, model identity, harness version, configuration, prompt, fixture, rubric, or launch recipe invalidates affected comparisons. Do not mix those results into one frozen panel. Re-review the affected protocol branch, bind a new manifest, and rerun both arms and all three repetitions for affected coordinates; a shared dependency change affects all coordinates that use it. Retain superseded evidence with its original identity.

Return the protocol revision, final manifest, raw and graded evidence, selection record, limitations, and published example links through `handoff` to the orchestrator. The orchestrator accepts the result and closes issues. Feed procedure corrections back to this maintained directory; installed client state remains the rollout owner's responsibility.
