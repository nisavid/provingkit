(function () {
  "use strict";

  function plainObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function failure(disposition, reason) {
    return {kind: "completed", actual_result: {disposition, reason}};
  }

  function supportedTimestamp(value) {
    if (typeof value !== "string") return null;
    const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?(Z|[+-]\d{2}:\d{2})$/.exec(value);
    if (match === null) return null;
    const year = Number(match[1]);
    const month = Number(match[2]);
    const day = Number(match[3]);
    const hour = Number(match[4]);
    const minute = Number(match[5]);
    const second = Number(match[6]);
    const millisecond = Number((match[7] || "").padEnd(3, "0"));
    if (year === 0 || month < 1 || month > 12 || day < 1 || day > 31 ||
        hour > 23 || minute > 59 || second > 59) return null;

    const wall = new Date(0);
    wall.setUTCFullYear(year, month - 1, day);
    wall.setUTCHours(hour, minute, second, millisecond);
    if (wall.getUTCFullYear() !== year || wall.getUTCMonth() !== month - 1 ||
        wall.getUTCDate() !== day || wall.getUTCHours() !== hour ||
        wall.getUTCMinutes() !== minute || wall.getUTCSeconds() !== second ||
        wall.getUTCMilliseconds() !== millisecond) return null;

    let offsetMinutes = 0;
    if (match[8] !== "Z") {
      if (match[8] === "-00:00") return null;
      const offsetHour = Number(match[8].slice(1, 3));
      const offsetMinute = Number(match[8].slice(4, 6));
      if (offsetHour > 14 || offsetMinute > 59 || (offsetHour === 14 && offsetMinute !== 0)) return null;
      offsetMinutes = (offsetHour * 60 + offsetMinute) * (match[8][0] === "+" ? 1 : -1);
    }
    const instant = new Date(wall.getTime() - offsetMinutes * 60000);
    if (!Number.isFinite(instant.getTime())) return null;
    const utcYear = instant.getUTCFullYear();
    if (utcYear < 1 || utcYear > 9999) return null;
    const utc = instant.toISOString();
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(utc)) return null;
    return utc.replace(/\.000Z$/, "Z");
  }

  function completedResponse(outcome) {
    if (!plainObject(outcome) || outcome.kind !== "completed" ||
        !Number.isInteger(outcome.status)) return null;
    return outcome;
  }

  function successStatus(status) {
    return status >= 200 && status <= 299;
  }

  function parseDocument(response) {
    if (typeof response.json !== "string") return null;
    let value;
    try {
      value = JSON.parse(response.json);
    } catch (_) {
      return null;
    }
    return plainObject(value) ? value : null;
  }

  function oneOffRoutine(document, triggerId) {
    const cronInactive =
      Object.prototype.hasOwnProperty.call(document, "cron_expression") &&
      (document.cron_expression === null || document.cron_expression === "");
    return document.id === triggerId &&
      supportedTimestamp(document.run_once_at) !== null &&
      cronInactive;
  }

  function createClaudeRoutineControls(options) {
    if (!plainObject(options) || typeof options.remoteTrigger !== "function" ||
        typeof options.triggerId !== "string" || !options.triggerId ||
        options.triggerId !== options.triggerId.trim() || /\p{C}/u.test(options.triggerId)) {
      throw new TypeError("remoteTrigger and an explicit triggerId are required");
    }
    const remoteTrigger = options.remoteTrigger;
    const triggerId = options.triggerId;

    async function call(request) {
      let outcome;
      try {
        outcome = await remoteTrigger(request);
      } catch (_) {
        return {kind: "unknown"};
      }
      if (!plainObject(outcome) || !["completed", "not_started", "unknown"].includes(outcome.kind)) {
        return {kind: "unknown"};
      }
      return outcome.kind === "completed" ? outcome : {kind: outcome.kind};
    }

    async function heartbeatSet({action}) {
      if (!plainObject(action) || action.kind !== "heartbeat_set" ||
          action.purpose !== "schedule" || !plainObject(action.arguments)) {
        return failure("not_performed", "unsupported-heartbeat-action");
      }
      if (action.arguments.heartbeat !== triggerId) {
        return failure("not_performed", "heartbeat-id-mismatch");
      }
      const target = supportedTimestamp(action.arguments.target_at);
      if (target === null) return failure("not_performed", "invalid-heartbeat-target");

      const preflightOutcome = await call({action: "get", trigger_id: triggerId});
      if (preflightOutcome.kind !== "completed") return preflightOutcome;
      const preflightResponse = completedResponse(preflightOutcome);
      if (preflightResponse === null || !successStatus(preflightResponse.status)) {
        return failure("not_performed", "native-preflight-failed");
      }
      const preflight = parseDocument(preflightResponse);
      if (preflight === null) return failure("not_performed", "native-preflight-invalid");
      if (!oneOffRoutine(preflight, triggerId)) {
        return failure("not_performed", "native-routine-unsupported");
      }

      const updateOutcome = await call({
        action: "update",
        trigger_id: triggerId,
        body: {run_once_at: target, enabled: true},
      });
      if (updateOutcome.kind !== "completed") return updateOutcome;
      const updateResponse = completedResponse(updateOutcome);
      if (updateResponse === null) return {kind: "unknown"};
      if (!successStatus(updateResponse.status)) {
        return failure("failed", "native-update-failed");
      }
      if (parseDocument(updateResponse) === null) return {kind: "unknown"};

      const readbackOutcome = await call({action: "get", trigger_id: triggerId});
      if (readbackOutcome.kind !== "completed") return {kind: "unknown"};
      const readbackResponse = completedResponse(readbackOutcome);
      if (readbackResponse === null || !successStatus(readbackResponse.status)) {
        return {kind: "unknown"};
      }
      const readback = parseDocument(readbackResponse);
      if (readback === null || readback.id !== triggerId) {
        return {kind: "unknown"};
      }
      if (readback.enabled !== true) return {kind: "unknown"};
      const observedNextRun = supportedTimestamp(readback.next_run_at);
      if (observedNextRun === null) return {kind: "unknown"};
      return {kind: "completed", actual_result: {applied: true, next_run_at: readback.next_run_at}};
    }

    return Object.freeze({heartbeatSet});
  }

  return Object.freeze({createClaudeRoutineControls});
}())
