// Passive qualification: execute original bookkeeping and context preparation only.
import { readFileSync } from "node:fs";
import { recordEvent, readSession, readTranscript, buildObservation, workDiff } from "./integration/dist/src/supervise.js";

const input = JSON.parse(readFileSync(0, "utf8"));
const before = readSession(input.session_id);
if (input.hook_event_name === "PostToolUse") {
  const text = value => value === undefined || value === null ? "" : typeof value === "string" ? value : JSON.stringify(value);
  const after = recordEvent(input.session_id, input.cwd, {
    tool: String(input.tool_name ?? ""), input: text(input.tool_input), result: text(input.tool_response),
  });
  const transcript = input.transcript_path ? readTranscript(input.transcript_path) : { job: "", output: "" };
  const eligible = after.count % 10 === 0 && Boolean(transcript.job);
  console.log(JSON.stringify({ before, after, cadence_eligible: eligible,
    current_observation: eligible ? buildObservation({ job: transcript.job, events: after.events }) : null,
    assessment: "omitted_for_passive_qualification" }));
} else if (input.hook_event_name === "Stop") {
  const transcript = input.transcript_path ? readTranscript(input.transcript_path) : { job: "", output: "" };
  const diff = input.stop_hook_active === true ? undefined : workDiff(input.cwd, before.base, before.untracked);
  console.log(JSON.stringify({ before, after: readSession(input.session_id),
    stop_hook_active: input.stop_hook_active === true,
    current_observation: diff?.trim() && transcript.job ? buildObservation({ job: transcript.job, diff, output: transcript.output }) : null,
    assessment: "omitted_for_passive_qualification" }));
} else {
  throw new Error("unsupported qualification hook");
}
