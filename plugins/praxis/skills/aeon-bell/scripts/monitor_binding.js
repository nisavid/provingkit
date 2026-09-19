(function () {
  "use strict";

  const ACTION_KINDS = Object.freeze(["task_read", "observe", "send", "emit", "heartbeat_set"]);
  const TASK_STATUSES = Object.freeze(["idle", "running", "completed", "archived", "canceled", "human_waiting", "unavailable", "unknown"]);
  const SEND_OUTCOMES = Object.freeze(["accepted", "not_sent", "unknown"]);
  const MAX_SUBMISSION_ATTEMPTS = 3;

  function plainObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function serializableCopy(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function deepFreeze(value) {
    if (value !== null && typeof value === "object" && !Object.isFrozen(value)) {
      Object.freeze(value);
      for (const item of Object.values(value)) deepFreeze(item);
    }
    return value;
  }

  function put(state, key, value) {
    state.put(key, serializableCopy(value));
  }

  function engineArgv(kind, run) {
    const argv = ["python3", "scripts/aeon_bell.py", "monitor", kind];
    if (kind === "enter") argv.push("--entry-ref", run.entry_ref);
    else argv.push("--continuation", run.continuation, "--result-json", run.result_json);
    if (run.logical_now !== null) argv.push("--now", run.logical_now);
    return argv;
  }

  function posixQuote(value) {
    if (typeof value !== "string") throw new TypeError("argv entries must be strings");
    return "'" + value.replaceAll("'", "'\\''") + "'";
  }

  function parseEngineReply(outcome) {
    if (!plainObject(outcome) || !["completed", "not_started", "unknown"].includes(outcome.kind)) {
      return {transport: "unknown", reason: "invalid-engine-transport-outcome"};
    }
    if (outcome.kind !== "completed") return {transport: outcome.kind};
    if (!Number.isInteger(outcome.exit_code)) return {transport: "unknown", reason: "engine-exit-is-not-authoritative"};
    if (outcome.exit_code !== 0) return {transport: "refused", reason: "engine-refused"};
    if (typeof outcome.stdout !== "string") return {transport: "unknown", reason: "engine-output-is-not-text"};
    let reply;
    try {
      const text = outcome.stdout.trim();
      if (!text) throw new Error("empty");
      reply = JSON.parse(text);
    } catch (_) {
      return {transport: "unknown", reason: "engine-reply-is-not-one-json-object"};
    }
    if (!plainObject(reply) || !["action_required", "complete", "stopped"].includes(reply.status)) {
      return {transport: "unknown", reason: "engine-reply-shape-is-invalid"};
    }
    if (reply.status === "action_required" && (
      typeof reply.registry_id !== "string" || typeof reply.invocation_id !== "string" ||
      !Number.isInteger(reply.generation) || typeof reply.continuation !== "string" ||
      !plainObject(reply.action) || !ACTION_KINDS.includes(reply.action.kind) ||
      typeof reply.action.purpose !== "string" || !plainObject(reply.action.arguments)
    )) return {transport: "unknown", reason: "engine-action-reply-shape-is-invalid"};
    return {transport: "completed", reply};
  }

  function newRun(entryRef, now) {
    return {
      phase: "ready_to_enter", entry_ref: serializableCopy(entryRef),
      logical_now: now === undefined ? null : serializableCopy(now),
      engine_request: null, engine_reply: null, registry_id: null,
      invocation_id: null, generation: null, continuation: null, action: null,
      action_binding_id: null, native_phase: null, native_actual_result: null,
      native_result_summary: null, decision_id: null, mapped_engine_result: null,
      result_json: null, submission_attempts: 0, terminal_reason: null,
    };
  }

  function validRun(value) {
    return plainObject(value) && typeof value.phase === "string" &&
      Object.prototype.hasOwnProperty.call(value, "entry_ref") &&
      Number.isInteger(value.submission_attempts);
  }

  function actorView(run, status, extra) {
    const view = {
      status, display_only: true,
      action_kind: run.action && run.action.kind,
      purpose: run.action && run.action.purpose,
      generation: run.generation,
      native_result_summary: run.native_result_summary,
      decision_id: run.decision_id,
      allowed_choices: null,
      reason: run.terminal_reason,
    };
    if (run.action && run.action.kind === "task_read") {
      view.expected_episode = run.action.arguments.episode;
      view.allowed_choices = TASK_STATUSES;
    }
    if (run.action && run.action.kind === "send") view.allowed_choices = SEND_OUTCOMES;
    return Object.assign(view, extra || {});
  }

  function publicResult(run, status, displayPolicy, extra) {
    const safe = actorView(run, status, extra);
    const transformed = displayPolicy ? displayPolicy(serializableCopy(safe)) : safe;
    return {status, view: serializableCopy(transformed)};
  }

  function actualValue(outcome) {
    if (Object.prototype.hasOwnProperty.call(outcome, "actual_result")) return outcome.actual_result;
    if (Object.prototype.hasOwnProperty.call(outcome, "result")) return outcome.result;
    return outcome;
  }

  function scalarEvidence(value) {
    if (!plainObject(value)) return {};
    const result = {};
    for (const [key, item] of Object.entries(value)) {
      if (item === null || ["string", "number", "boolean"].includes(typeof item)) result[key] = item;
    }
    return result;
  }

  function boundedSummary(kind, outcome) {
    if (!plainObject(outcome.summary)) return null;
    const allowed = kind === "task_read"
      ? ["task_status", "episode_context", "episode_matches"]
      : kind === "send" ? ["transport_status", "evidence_summary"] : [];
    const summary = {};
    for (const [key, value] of Object.entries(outcome.summary)) {
      if (!allowed.includes(key) || !["string", "number", "boolean"].includes(typeof value)) return null;
      if (typeof value === "string" && (value.length > 512 || /\p{C}/u.test(value))) return null;
      summary[key] = value;
    }
    if (Object.keys(summary).length === 0 || JSON.stringify(summary).length > 1024) return null;
    return summary;
  }

  function mechanicalResult(run, outcome) {
    const source = plainObject(actualValue(outcome)) ? actualValue(outcome) : outcome;
    if (Object.keys(source).length === 2 &&
        ["not_performed", "failed", "unavailable"].includes(source.disposition) &&
        typeof source.reason === "string" && source.reason.length > 0 &&
        source.reason.length <= 256 && !/\p{C}/u.test(source.reason)) {
      return {disposition: source.disposition, reason: source.reason};
    }
    if (run.action.kind === "observe") {
      if (source.exit_code === 0) return {exit_code: 0};
      if (source.exit_code === 2 && typeof source.stderr_line === "string") return {exit_code: 2, stderr_line: source.stderr_line};
      return null;
    }
    if (run.action.kind === "emit") return {emitted: true};
    if (run.action.kind === "heartbeat_set") {
      if (source.applied !== true || typeof source.next_run_at !== "string") return null;
      const result = {applied: true, next_run_at: source.next_run_at};
      if (Object.prototype.hasOwnProperty.call(source, "previous_next_run_at")) result.previous_next_run_at = source.previous_next_run_at;
      return result;
    }
    return null;
  }

  function classificationResult(run, classification) {
    if (!plainObject(classification) || Object.keys(classification).length !== 2 ||
        classification.decision_id !== run.decision_id || typeof classification.choice !== "string") return null;
    const native = run.native_actual_result;
    const source = plainObject(native) ? (plainObject(actualValue(native)) ? actualValue(native) : native) : {};
    if (run.action.kind === "task_read") {
      if (!TASK_STATUSES.includes(classification.choice)) return null;
      if (classification.choice === "idle" && (
        !plainObject(run.native_result_summary) ||
        run.native_result_summary.episode_matches !== true ||
        typeof run.native_result_summary.episode_context !== "string"
      )) return null;
      const observedAt = source.observed_at || source.read_at;
      if (typeof observedAt !== "string") return null;
      return {status: classification.choice, observed_at: observedAt};
    }
    if (run.action.kind === "send") {
      if (!SEND_OUTCOMES.includes(classification.choice)) return null;
      const evidence = scalarEvidence(source.evidence);
      return Object.keys(evidence).length ? {outcome: classification.choice, evidence} : {outcome: classification.choice};
    }
    return null;
  }

  function installReply(run, reply) {
    run.engine_reply = serializableCopy(reply);
    if (reply.status !== "action_required") return;
    run.registry_id = reply.registry_id;
    run.invocation_id = reply.invocation_id;
    run.generation = reply.generation;
    run.continuation = serializableCopy(reply.continuation);
    run.action = serializableCopy(reply.action);
    const prior = typeof run.action_binding_id === "string"
      ? Number(run.action_binding_id.slice(run.action_binding_id.lastIndexOf("-") + 1))
      : 0;
    const sequence = Number.isInteger(prior) && prior >= 0 ? prior + 1 : 1;
    run.action_binding_id = "binding-" + reply.generation + "-" + sequence;
    run.native_phase = "ready";
    run.native_actual_result = null;
    run.native_result_summary = null;
    run.decision_id = null;
    run.mapped_engine_result = null;
    run.result_json = null;
    run.submission_attempts = 0;
    run.phase = "native_ready";
  }

  function redactCompletedRun(run) {
    run.entry_ref = null;
    run.engine_request = null;
    run.engine_reply = null;
    run.continuation = null;
    run.action = null;
    run.action_binding_id = null;
    run.native_actual_result = null;
    run.mapped_engine_result = null;
    run.result_json = null;
    run.decision_id = null;
  }

  function createStructuredMonitorBinding(options) {
    if (!plainObject(options) || !plainObject(options.state) ||
        typeof options.state.get !== "function" || typeof options.state.put !== "function" ||
        typeof options.engineTransport !== "function" || !plainObject(options.nativeAdapters)) {
      throw new TypeError("structured state, engineTransport, and nativeAdapters are required");
    }
    const state = options.state;
    const engineTransport = options.engineTransport;
    const nativeAdapters = options.nativeAdapters;
    const displayPolicy = options.displayPolicy;

    async function submitEngine(runKey, run, kind) {
      const argv = engineArgv(kind, run);
      run.engine_request = {kind, argv: serializableCopy(argv)};
      run.phase = kind === "enter" ? "entering" : "submission_started";
      if (kind === "continue") run.submission_attempts += 1;
      put(state, runKey, run);
      let outcome;
      try {
        outcome = await engineTransport(deepFreeze(serializableCopy(argv)), {kind, attempt: run.submission_attempts});
      } catch (_) {
        outcome = {kind: "unknown"};
      }
      return parseEngineReply(outcome);
    }

    async function advance(input) {
      if (!plainObject(input) || typeof input.runKey !== "string" || typeof input.entryKey !== "string") {
        return {status: "unsupported", view: {status: "unsupported", display_only: true, reason: "invalid-binding-input"}};
      }
      let run = state.get(input.runKey);
      if (run === undefined || run === null) {
        const entry = state.get(input.entryKey);
        if (typeof entry !== "string" || !entry) return {status: "unsupported", view: {status: "unsupported", display_only: true, reason: "entry-channel-unavailable"}};
        run = newRun(entry, input.now);
        put(state, input.runKey, run);
      } else if (!validRun(run)) {
        return {status: "unsupported", view: {status: "unsupported", display_only: true, reason: "invalid-stored-run"}};
      } else run = serializableCopy(run);

      if (["complete", "stopped", "unresolved", "unsupported"].includes(run.phase)) return publicResult(run, run.phase, displayPolicy);
      if (run.phase === "entering" || run.phase === "native_started" || run.phase === "submission_started") {
        const prior = run.phase;
        run.phase = "unresolved";
        run.terminal_reason = prior === "entering" ? "enter-outcome-unknown" : prior === "native_started" ? "native-outcome-unknown" : "engine-transition-outcome-unknown";
        put(state, input.runKey, run);
        return publicResult(run, "unresolved", displayPolicy);
      }

      while (true) {
        if (run.phase === "ready_to_enter") {
          const parsed = await submitEngine(input.runKey, run, "enter");
          if (parsed.transport === "unknown") {
            run.phase = "unresolved"; run.terminal_reason = parsed.reason || "enter-outcome-unknown";
            put(state, input.runKey, run); return publicResult(run, "unresolved", displayPolicy);
          }
          if (parsed.transport === "not_started" || parsed.transport === "refused") {
            run.phase = "stopped"; run.terminal_reason = parsed.transport === "not_started" ? "engine-enter-not-started" : parsed.reason;
            put(state, input.runKey, run); return publicResult(run, "stopped", displayPolicy);
          }
          installReply(run, parsed.reply);
          put(state, input.runKey, run);
        }

        if (run.engine_reply.status === "complete") {
          run.phase = "complete"; run.terminal_reason = null;
          redactCompletedRun(run);
          put(state, input.runKey, run); return publicResult(run, "complete", displayPolicy);
        }
        if (run.engine_reply.status === "stopped") {
          run.phase = "stopped"; run.terminal_reason = "engine-stopped";
          put(state, input.runKey, run); return publicResult(run, "stopped", displayPolicy);
        }

        if (run.phase === "classification_pending") {
          const mapped = classificationResult(run, input.classification);
          if (mapped === null) return publicResult(run, "needs_classification", displayPolicy, {reason: "invalid-classification"});
          run.mapped_engine_result = serializableCopy(mapped);
          run.result_json = JSON.stringify(mapped);
          run.phase = "submission_ready";
          put(state, input.runKey, run);
        }

        if (run.phase === "native_ready") {
          const adapter = nativeAdapters[run.action.kind];
          if (!plainObject(adapter) || typeof adapter.invoke !== "function") {
            run.phase = "unsupported"; run.terminal_reason = "native-adapter-unavailable";
            put(state, input.runKey, run); return publicResult(run, "unsupported", displayPolicy);
          }
          run.phase = "native_started"; run.native_phase = "started";
          put(state, input.runKey, run);
          let nativeOutcome;
          try {
            nativeOutcome = await adapter.invoke({
              engine: deepFreeze({registry_id: run.registry_id, invocation_id: run.invocation_id, generation: run.generation}),
              action: deepFreeze(serializableCopy(run.action)),
            });
          } catch (_) {
            nativeOutcome = {kind: "unknown"};
          }
          if (!plainObject(nativeOutcome) || !["completed", "not_started", "unknown"].includes(nativeOutcome.kind)) nativeOutcome = {kind: "unknown"};
          if (nativeOutcome.kind === "unknown") {
            run.phase = "unresolved"; run.terminal_reason = "native-outcome-unknown";
            put(state, input.runKey, run); return publicResult(run, "unresolved", displayPolicy);
          }
          run.native_actual_result = serializableCopy(nativeOutcome);
          run.native_phase = "completed";
          const summary = nativeOutcome.kind === "completed" ? boundedSummary(run.action.kind, nativeOutcome) : null;
          run.native_result_summary = summary || (nativeOutcome.kind === "completed" ? "native call completed" : "native call positively did not start");
          put(state, input.runKey, run);
          if (nativeOutcome.kind === "not_started") {
            run.mapped_engine_result = {disposition: "not_performed", reason: "native transport did not start"};
            run.result_json = JSON.stringify(run.mapped_engine_result);
            run.phase = "submission_ready";
            put(state, input.runKey, run);
          } else {
            const mapped = mechanicalResult(run, nativeOutcome);
            if (mapped !== null) {
              run.mapped_engine_result = serializableCopy(mapped);
              run.result_json = JSON.stringify(mapped);
              run.phase = "submission_ready";
              put(state, input.runKey, run);
            } else if (run.action.kind === "task_read" || run.action.kind === "send") {
              if (summary === null) {
                run.phase = "unresolved"; run.terminal_reason = "native-summary-unavailable";
                put(state, input.runKey, run); return publicResult(run, "unresolved", displayPolicy);
              }
              run.decision_id = "decision-" + run.action_binding_id;
              run.phase = "classification_pending";
              put(state, input.runKey, run);
              return publicResult(run, "needs_classification", displayPolicy);
            } else {
              run.phase = "unresolved"; run.terminal_reason = "native-result-cannot-be-mapped";
              put(state, input.runKey, run); return publicResult(run, "unresolved", displayPolicy);
            }
          }
        }

        if (run.phase === "submission_retryable") run.phase = "submission_ready";
        if (run.phase === "submission_ready") {
          let parsed;
          let immediateAttempts = 0;
          while (immediateAttempts < MAX_SUBMISSION_ATTEMPTS) {
            immediateAttempts += 1;
            parsed = await submitEngine(input.runKey, run, "continue");
            if (parsed.transport !== "not_started") break;
            run.phase = "submission_ready";
            put(state, input.runKey, run);
          }
          if (parsed.transport === "not_started") {
            run.phase = "submission_retryable"; run.terminal_reason = "engine-continue-not-started";
            put(state, input.runKey, run); return publicResult(run, "stopped", displayPolicy);
          }
          if (parsed.transport === "unknown") {
            run.phase = "unresolved"; run.terminal_reason = parsed.reason || "engine-transition-outcome-unknown";
            put(state, input.runKey, run); return publicResult(run, "unresolved", displayPolicy);
          }
          if (parsed.transport === "refused") {
            run.phase = "stopped"; run.terminal_reason = parsed.reason;
            put(state, input.runKey, run); return publicResult(run, "stopped", displayPolicy);
          }
          installReply(run, parsed.reply);
          put(state, input.runKey, run);
          input = Object.assign({}, input, {classification: undefined});
        }
      }
    }
    return Object.freeze({advance});
  }

  function createExecCommandEngineTransport(options) {
    if (!plainObject(options) || typeof options.execCommand !== "function") throw new TypeError("execCommand is required");
    return async function (argv) {
      const cmd = argv.map(posixQuote).join(" ");
      let result;
      try {
        result = await options.execCommand({cmd, workdir: options.workdir});
      } catch (error) {
        if (error && error.not_started === true) return {kind: "not_started"};
        return {kind: "unknown"};
      }
      let output = plainObject(result) && typeof result.output === "string" ? result.output : "";
      const sessionId = plainObject(result) ? result.session_id : undefined;
      while (plainObject(result) && result.session_id !== undefined && result.exit_code === undefined) {
        if (typeof options.writeStdin !== "function") return {kind: "unknown"};
        try {
          if (result.session_id !== sessionId) return {kind: "unknown"};
          result = await options.writeStdin({session_id: sessionId, chars: ""});
          if (plainObject(result) && typeof result.output === "string") output += result.output;
        } catch (_) {
          return {kind: "unknown"};
        }
      }
      if (!plainObject(result) || !Number.isInteger(result.exit_code)) return {kind: "unknown"};
      return {kind: "completed", exit_code: result.exit_code, stdout: output, stderr: ""};
    };
  }

  function createNativeAdapters(controls) {
    if (!plainObject(controls)) throw new TypeError("native controls are required");
    const adapters = {};
    if (typeof controls.taskRead === "function") adapters.task_read = {invoke: ({action}) => controls.taskRead({host: action.arguments.host, task_id: action.arguments.task_id, episode: action.arguments.episode})};
    if (typeof controls.runArgv === "function") adapters.observe = {invoke: ({action}) => controls.runArgv({argv: action.arguments.argv, cwd: action.arguments.cwd})};
    if (typeof controls.send === "function") adapters.send = {invoke: ({action}) => controls.send({host: action.arguments.host, task_id: action.arguments.task_id, message: action.arguments.message})};
    if (typeof controls.emit === "function") adapters.emit = {invoke: ({action}) => controls.emit(action.arguments.text)};
    if (typeof controls.heartbeatSet === "function") adapters.heartbeat_set = {invoke: ({engine, action}) => controls.heartbeatSet({engine, action})};
    return Object.freeze(adapters);
  }

  return Object.freeze({createStructuredMonitorBinding, createExecCommandEngineTransport, createNativeAdapters});
}())
