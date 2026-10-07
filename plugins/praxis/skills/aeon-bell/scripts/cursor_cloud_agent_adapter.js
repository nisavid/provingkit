(function () {
  "use strict";

  const HOST = "cursor-cloud-agent";
  const API_ORIGIN = "https://api.cursor.com";

  function plainObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function wellFormed(value) {
    for (let index = 0; index < value.length; index += 1) {
      const unit = value.charCodeAt(index);
      if (unit >= 0xd800 && unit <= 0xdbff) {
        const next = value.charCodeAt(index + 1);
        if (!(next >= 0xdc00 && next <= 0xdfff)) return false;
        index += 1;
      } else if (unit >= 0xdc00 && unit <= 0xdfff) return false;
    }
    return true;
  }

  function targetText(value) {
    return typeof value === "string" && value.length > 0 && value.length <= 512 &&
      wellFormed(value) && !/[\u0000-\u001f\u007f-\u009f]/u.test(value);
  }

  function pathIdentifier(value) {
    if (!targetText(value) || value.normalize("NFC") !== value ||
        value.normalize("NFKC") !== value || /[\\/]/u.test(value) ||
        /%(?:2f|5c)/iu.test(value)) return false;
    const dotDecoded = value.replaceAll(/%2e/giu, ".");
    return dotDecoded !== "." && dotDecoded !== "..";
  }

  function messageText(value) {
    return typeof value === "string" && value.length > 0 && value.length <= 16384 &&
      wellFormed(value) && !/[\u0000\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f]/u.test(value);
  }

  function unknownSend(status, reason) {
    const evidence = {response: reason};
    if (Number.isInteger(status)) evidence.http_status = status;
    return {
      kind: "completed",
      actual_result: {evidence},
      summary: {
        transport_status: "unknown",
        evidence_summary: "Cursor continuation admission is not authoritative",
      },
    };
  }

  function failedRead() {
    return {
      kind: "completed",
      actual_result: {
        disposition: "failed",
        reason: "Cursor task read is not authoritative",
      },
    };
  }

  function completedBody(response) {
    if (!plainObject(response) || response.kind !== "completed" ||
        !Number.isInteger(response.status) || response.status < 200 || response.status >= 300 ||
        typeof response.body !== "string") return null;
    try {
      const body = JSON.parse(response.body);
      return plainObject(body) ? body : null;
    } catch (_) {
      return null;
    }
  }

  function createCursorCloudAgentControls(options) {
    if (!plainObject(options) || typeof options.request !== "function") {
      throw new TypeError("an already-authenticated request control is required");
    }
    const request = options.request;

    async function taskRead(input) {
      if (!plainObject(input) || input.host !== HOST || !pathIdentifier(input.task_id) ||
          !targetText(input.episode)) return {kind: "not_started"};
      let agentResponse;
      try {
        agentResponse = await request({
          method: "GET",
          url: API_ORIGIN + "/v1/agents/" + encodeURIComponent(input.task_id),
        });
      } catch (_) {
        return failedRead();
      }
      if (plainObject(agentResponse) && agentResponse.kind === "not_started") {
        return {kind: "not_started"};
      }
      const agent = completedBody(agentResponse);
      if (agent === null || agent.id !== input.task_id ||
          !["ACTIVE", "IDLE", "ARCHIVED"].includes(agent.status) ||
          !pathIdentifier(agent.latestRunId)) return failedRead();

      let runResponse;
      try {
        runResponse = await request({
          method: "GET",
          url: API_ORIGIN + "/v1/agents/" + encodeURIComponent(input.task_id) +
            "/runs/" + encodeURIComponent(agent.latestRunId),
        });
      } catch (_) {
        return failedRead();
      }
      if (plainObject(runResponse) && runResponse.kind === "not_started") {
        return {kind: "not_started"};
      }
      const run = completedBody(runResponse);
      if (run === null || run.id !== agent.latestRunId || run.agentId !== input.task_id ||
          !["CREATING", "RUNNING", "FINISHED", "ERROR", "CANCELLED", "EXPIRED"].includes(run.status) ||
          typeof runResponse.observed_at !== "string") return failedRead();

      const taskStatus = agent.status === "ACTIVE"
        ? "running" : agent.status === "ARCHIVED" ? "archived" : "idle";
      return {
        kind: "completed",
        actual_result: {
          observed_at: runResponse.observed_at,
          agent_status: agent.status,
          latest_run_id: agent.latestRunId,
          run_status: run.status,
          final_reply_available: typeof run.result === "string",
        },
        summary: {
          task_status: taskStatus,
          episode_context: "Cursor agent and latest run observed; the public API proves no Aeon wait-episode relation",
          episode_matches: false,
        },
      };
    }

    async function send(input) {
      if (!plainObject(input) || input.host !== HOST || !pathIdentifier(input.task_id) ||
          !messageText(input.message)) {
        return {kind: "not_started"};
      }
      const requestInput = {
        method: "POST",
        url: API_ORIGIN + "/v1/agents/" + encodeURIComponent(input.task_id) + "/runs",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({prompt: {text: input.message}}),
      };
      let response;
      try {
        response = await request(requestInput);
      } catch (_) {
        return unknownSend(undefined, "request-outcome-lost");
      }
      if (plainObject(response) && response.kind === "not_started") return {kind: "not_started"};
      if (!plainObject(response) || response.kind !== "completed") {
        return unknownSend(undefined, "request-outcome-unknown");
      }
      if (response.status === 409 && response.error_code === "agent_busy") {
        return {
          kind: "completed",
          actual_result: {evidence: {http_status: 409, error_code: "agent_busy"}},
          summary: {
            transport_status: "not_sent",
            evidence_summary: "Cursor rejected the continuation because the Cloud Agent is busy",
          },
        };
      }
      let body;
      try {
        if (typeof response.body !== "string") throw new Error("body is not text");
        body = JSON.parse(response.body);
      } catch (_) {
        return unknownSend(response.status, "response-malformed");
      }
      const run = plainObject(body) && plainObject(body.run) ? body.run : null;
      if (Number.isInteger(response.status) && response.status >= 200 && response.status < 300 &&
          run !== null && pathIdentifier(run.id) && run.agentId === input.task_id &&
          run.status === "CREATING") {
        return {
          kind: "completed",
          actual_result: {evidence: {http_status: response.status, native_run_id: run.id}},
          summary: {
            transport_status: "accepted",
            evidence_summary: "Cursor returned a CREATING run bound to the requested Cloud Agent",
          },
        };
      }
      return unknownSend(response.status, "response-nonauthoritative");
    }

    return Object.freeze({taskRead, send});
  }

  return Object.freeze({HOST, API_ORIGIN, createCursorCloudAgentControls});
}())
