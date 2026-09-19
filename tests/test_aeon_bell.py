"""Behavioral tests for the Aeon Bell monitor/registry/conditional-dispatch engine."""

from __future__ import annotations

import concurrent.futures
import contextlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPOSITORY
    / "plugins"
    / "praxis"
    / "skills"
    / "aeon-bell"
    / "scripts"
    / "aeon_bell.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("aeon_bell", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


aeon_bell = load_module()

T0 = "2026-09-17T12:00:00+00:00"
QUOTA_GATE = {
    "kind": "quota_recovery",
    "account": "synthetic-account-a",
    "route": "cli",
    "bucket": "weekly",
    "policy_revision": "policy-1",
}


def run(*argv: str) -> tuple[int, Any, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = aeon_bell.main(list(argv))
    text = out.getvalue()
    payload = json.loads(text) if text.strip() else None
    return code, payload, err.getvalue()


class AeonBellCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = str(Path(self._tmp.name) / "store")

    def register(
        self,
        *,
        owner: str = "owner-a",
        host: str = "host-a",
        task_id: str = "task-1",
        episode: str = "episode-1",
        gate: dict[str, Any] | None = None,
        continuation: str = "Continue the bounded work.",
        now: str = T0,
        extra: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        code, payload, err = run(
            "register",
            "--store",
            self.store,
            "--owner",
            owner,
            "--host",
            host,
            "--task-id",
            task_id,
            "--episode",
            episode,
            "--gate-json",
            json.dumps(QUOTA_GATE if gate is None else gate),
            "--continuation",
            continuation,
            "--now",
            now,
            *extra,
        )
        self.assertEqual(code, 0, err)
        return payload


class RegistryCommands(AeonBellCase):
    def test_owner_can_register_and_inspect_exact_target_identity(self) -> None:
        registered = self.register()
        self.assertEqual(registered["status"], "waiting")
        code, inspected, err = run("inspect", "--store", self.store, "--now", T0)
        self.assertEqual(code, 0, err)
        [entry] = inspected["registrations"]
        self.assertEqual(entry["registration_id"], registered["registration_id"])
        self.assertEqual(entry["owner"], "owner-a")
        self.assertEqual(entry["host"], "host-a")
        self.assertEqual(entry["task_id"], "task-1")
        self.assertEqual(entry["episode"], "episode-1")
        self.assertEqual(entry["gate"], QUOTA_GATE)
        self.assertEqual(entry["status"], "waiting")
        self.assertEqual(inspected["unresolved_attempts"], [])

    def test_owner_can_update_pause_resume_and_remove(self) -> None:
        rid = self.register()["registration_id"]
        common = ("--store", self.store, "--registration-id", rid, "--owner", "owner-a")
        code, updated, err = run(
            "update", *common, "--continuation", "Revised continuation.", "--now", T0
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(updated["continuation"], "Revised continuation.")
        code, paused, err = run("pause", *common, "--now", T0)
        self.assertEqual(code, 0, err)
        self.assertEqual(paused["status"], "paused")
        code, resumed, err = run("resume", *common, "--now", T0)
        self.assertEqual(code, 0, err)
        self.assertEqual(resumed["status"], "waiting")
        code, removed, err = run("remove", *common, "--now", T0)
        self.assertEqual(code, 0, err)
        self.assertEqual(removed["status"], "removed")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        self.assertEqual(inspected["registrations"], [])

    def test_wrong_owner_cannot_update_pause_or_remove(self) -> None:
        rid = self.register()["registration_id"]
        for command, extra in (
            ("update", ("--continuation", "Hijacked.")),
            ("pause", ()),
            ("remove", ()),
        ):
            code, payload, err = run(
                command,
                "--store",
                self.store,
                "--registration-id",
                rid,
                "--owner",
                "owner-b",
                *extra,
                "--now",
                T0,
            )
            self.assertEqual(code, 2, command)
            self.assertIsNone(payload)
            self.assertIn("owner-mismatch", err)
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        [entry] = inspected["registrations"]
        self.assertEqual(entry["status"], "waiting")
        self.assertEqual(entry["continuation"], "Continue the bounded work.")

    def test_unknown_registration_and_duplicate_target_are_rejected(self) -> None:
        self.register()
        code, _, err = run(
            "register",
            "--store",
            self.store,
            "--owner",
            "owner-b",
            "--host",
            "host-a",
            "--task-id",
            "task-1",
            "--episode",
            "episode-9",
            "--gate-json",
            json.dumps(QUOTA_GATE),
            "--continuation",
            "Another.",
            "--now",
            T0,
        )
        self.assertEqual(code, 2)
        self.assertIn("duplicate-target", err)
        code, _, err = run(
            "pause",
            "--store",
            self.store,
            "--registration-id",
            "missing",
            "--owner",
            "owner-a",
            "--now",
            T0,
        )
        self.assertEqual(code, 2)
        self.assertIn("unknown-registration", err)


def cycle(store: str, now: str, **fields: Any) -> tuple[int, Any, str]:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
        json.dump(fields, handle)
        path = handle.name
    try:
        return run("cycle", "--store", store, "--input", path, "--now", now)
    finally:
        Path(path).unlink(missing_ok=True)


class CycleHelpers(AeonBellCase):
    def gate_key(self) -> str:
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        return inspected["registrations"][0]["gate_key"]

    def quota_observation(
        self,
        *,
        remaining: float,
        observed_at: str = T0,
        account: str = "synthetic-account-a",
        bucket: str = "weekly",
        reset_at: str | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        bucket_entry: dict[str, Any] = {"name": bucket, "remaining_percent": remaining}
        if reset_at is not None:
            bucket_entry["reset_at"] = reset_at
        return {
            "gate_key": self.gate_key(),
            "status": "ok",
            "observed_at": observed_at,
            "account": account,
            "route": "cli",
            "buckets": [bucket_entry],
            **extra,
        }

    @staticmethod
    def idle(
        task_id: str = "task-1", status: str = "idle", observed_at: str = T0
    ) -> dict:
        return {
            "host": "host-a",
            "task_id": task_id,
            "status": status,
            "observed_at": observed_at,
        }

    def assert_no_wake(self, result: Any, reason: str) -> None:
        self.assertEqual(result["wake_proposals"], [], reason)
        self.assertEqual([s["reason"] for s in result["skipped"]], [reason])

    def propose(
        self, now: str = T0, task_ids: tuple[str, ...] = ("task-1",)
    ) -> list[dict]:
        _, result, err = cycle(
            self.store,
            now,
            observations=[self.quota_observation(remaining=50, observed_at=now)],
            task_states=[self.idle(task_id=t, observed_at=now) for t in task_ids],
        )
        self.assertIsNotNone(result, err)
        return result["wake_proposals"]

    def report(self, attempt_id: str, outcome: str, now: str = T0, **evidence: Any):
        return run(
            "report",
            "--store",
            self.store,
            "--attempt-id",
            attempt_id,
            "--outcome",
            outcome,
            "--evidence-json",
            json.dumps(evidence),
            "--now",
            now,
        )


class MonitorCycle(CycleHelpers):
    def test_equivalent_gates_share_one_observation_request(self) -> None:
        self.register(task_id="task-1")
        self.register(task_id="task-2", gate=dict(QUOTA_GATE))
        other = dict(QUOTA_GATE, account="synthetic-account-b")
        self.register(task_id="task-3", gate=other)
        code, result, err = cycle(self.store, T0)
        self.assertEqual(code, 0, err)
        requests = result["observation_requests"]
        self.assertEqual(len(requests), 2)
        self.assertEqual([r["gate"] for r in requests], [QUOTA_GATE, other])
        self.assertEqual(result["wake_proposals"], [])
        shared = requests[0]
        self.assertEqual(sorted(shared["task_ids"]), ["task-1", "task-2"])

    def test_open_gate_and_idle_target_yield_one_exact_wake_proposal(self) -> None:
        rid = self.register()["registration_id"]
        code, result, err = cycle(
            self.store,
            T0,
            observations=[self.quota_observation(remaining=42)],
            task_states=[self.idle()],
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(result["observation_requests"], [])
        [proposal] = result["wake_proposals"]
        self.assertEqual(proposal["registration_id"], rid)
        self.assertEqual(
            (proposal["host"], proposal["task_id"], proposal["episode"]),
            ("host-a", "task-1", "episode-1"),
        )
        self.assertEqual(proposal["attempt_status"], "reserved")
        steps = {step["step"]: step for step in proposal["native_steps"]}
        self.assertEqual(
            steps["read"]["arguments"], {"host": "host-a", "task_id": "task-1"}
        )
        send = steps["send"]
        self.assertEqual(send["tool"], "send_follow_up")
        self.assertEqual(send["arguments"]["host"], "host-a")
        self.assertEqual(send["arguments"]["task_id"], "task-1")
        self.assertIn("Continue the bounded work.", send["arguments"]["message"])
        self.assertIn("episode-1", send["arguments"]["message"])
        self.assertIsNone(send["model_override"])
        self.assertIsNone(send["effort_override"])
        self.assertTrue(proposal["target_revalidation_required"])
        # The attempt is durable before any send happens.
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        [attempt] = inspected["unresolved_attempts"]
        self.assertEqual(attempt["attempt_id"], proposal["attempt_id"])
        self.assertEqual(attempt["status"], "reserved")
        self.assertEqual(inspected["registrations"][0]["status"], "reserved")

    def test_repeated_fresh_cycles_neither_recheck_nor_repropose(self) -> None:
        self.register()
        cycle(
            self.store,
            T0,
            observations=[self.quota_observation(remaining=42)],
            task_states=[self.idle()],
        )
        later = "2026-09-17T12:10:00+00:00"
        code, result, err = cycle(
            self.store, later, task_states=[self.idle(observed_at=later)]
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(result["observation_requests"], [])
        self.assertEqual(result["wake_proposals"], [])
        [skip] = result["skipped"]
        self.assertEqual(skip["reason"], "registration-reserved")
        # Once the observation ages past its freshness window, the gate is due again.
        expired = "2026-09-17T12:15:00+00:00"
        _, result, _ = cycle(self.store, expired)
        self.assertEqual(
            result["observation_requests"], []
        )  # reserved: nothing waiting
        rid = result["skipped"][0]["registration_id"]
        self.assertEqual(rid, result["unresolved_attempts"][0]["registration_id"])

    def test_closed_gate_without_estimate_is_requeried_sixty_minutes_after_its_anchor(
        self,
    ) -> None:
        self.register()
        # Tick 1 at 12:00: the plan cycle runs a few seconds in, the adapter stamps
        # its observation later still, and the result cycle ingests it.
        _, plan, _ = cycle(self.store, "2026-09-17T12:00:05+00:00")
        self.assertEqual([r["reason"] for r in plan["observation_requests"]], ["unobserved"])
        self.assertEqual(plan["schedule"]["reason"], "gate-due")
        self.assertEqual(plan["schedule"]["delay_minutes"], 0)
        closed = self.quota_observation(remaining=0, observed_at="2026-09-17T12:00:20+00:00")
        _, result, _ = cycle(
            self.store,
            "2026-09-17T12:00:25+00:00",
            observations=[closed],
            task_states=[self.idle(observed_at="2026-09-17T12:00:25+00:00")],
        )
        self.assertEqual(result["observation_requests"], [], "just observed: no request")
        self.assert_no_wake(result, "gate-closed")
        # No forecast and no reset hint: the next query is 60 minutes after the
        # observation's own timestamp, not after the cycle that ingested it.
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T13:00:20+00:00")
        self.assertEqual(result["schedule"]["delay_minutes"], 60)
        # A tick at the old fixed cadence finds nothing due, fresh or stale: a
        # stale closed observation waits for its planned query.
        for early in ("2026-09-17T12:15:05+00:00", "2026-09-17T12:30:00+00:00"):
            _, plan, _ = cycle(self.store, early)
            self.assertEqual(plan["observation_requests"], [], early)
            self.assertEqual(plan["schedule"]["next_check_at"], "2026-09-17T13:00:20+00:00")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", "2026-09-17T12:30:00+00:00")
        self.assertFalse(inspected["observations"][0]["fresh"], "freshness is unchanged")
        _, plan, _ = cycle(self.store, "2026-09-17T13:00:20+00:00")
        [request] = plan["observation_requests"]
        self.assertEqual(request["reason"], "stale")
        self.assertEqual(request["freshness_minutes"], 15)
        self.assertEqual(request["query_due_at"], "2026-09-17T13:00:20+00:00")
        # The refreshed observation, stamped seconds later, is not re-requested.
        opened = self.quota_observation(remaining=30, observed_at="2026-09-17T13:00:35+00:00")
        _, result, _ = cycle(
            self.store,
            "2026-09-17T13:00:40+00:00",
            observations=[opened],
            task_states=[self.idle(observed_at="2026-09-17T13:00:40+00:00")],
        )
        self.assertEqual(result["observation_requests"], [])
        self.assertEqual(len(result["wake_proposals"]), 1)

    def test_closed_missing_and_stale_evidence_do_not_wake(self) -> None:
        # The observations arrive in observed order: the engine keeps a
        # monotonic anchor per gate, so evidence older than what it holds is
        # superseded rather than applied (see ObservationOrdering).
        self.register()
        # A stale but open observation (older than the freshness window) never wakes.
        stale = "2026-09-17T11:40:00+00:00"
        code, result, _ = cycle(
            self.store,
            T0,
            observations=[self.quota_observation(remaining=50, observed_at=stale)],
            task_states=[self.idle()],
        )
        self.assertEqual(code, 0)
        self.assert_no_wake(result, "gate-observation-stale")
        self.assertEqual(len(result["observation_requests"]), 1)
        # A newer closed observation does not wake either.
        code, result, _ = cycle(
            self.store,
            T0,
            observations=[self.quota_observation(remaining=0)],
            task_states=[self.idle()],
        )
        self.assertEqual(code, 0)
        self.assert_no_wake(result, "gate-closed")
        # Fresh open gate but no task-state evidence: unknown stays closed.
        at = "2026-09-17T12:01:00+00:00"
        code, result, _ = cycle(
            self.store, at, observations=[self.quota_observation(remaining=50, observed_at=at)]
        )
        self.assertEqual(code, 0)
        self.assert_no_wake(result, "task-unknown")

    def test_reset_timestamps_credits_and_other_buckets_are_not_capacity(self) -> None:
        self.register()
        cases = (
            self.quota_observation(remaining=0, reset_at="2026-09-17T12:05:00+00:00"),
            self.quota_observation(remaining=0, credits={"balance": 999}),
            self.quota_observation(remaining=100, bucket="daily"),
            self.quota_observation(remaining=100, account="synthetic-account-b"),
            {
                "gate_key": self.gate_key(),
                "status": "ok",
                "observed_at": T0,
                "account": "synthetic-account-a",
                "route": "cli",
                "buckets": [],
            },
        )
        # Each case is a later observation of the same gate: the anchor is
        # monotonic, so an equal-time replay would be skipped, not evaluated.
        for minute, observation in enumerate(cases):
            at = f"2026-09-17T12:{minute:02d}:00+00:00"
            observation["observed_at"] = at
            code, result, err = cycle(
                self.store, at, observations=[observation], task_states=[self.idle(observed_at=at)]
            )
            self.assertEqual(code, 0, err)
            self.assertEqual(result["wake_proposals"], [])
            self.assertEqual(result["ingested_observations"][0]["result"], "closed")

    def test_non_idle_or_unknown_targets_stay_unawakened(self) -> None:
        self.register()
        for status in (
            "running",
            "completed",
            "archived",
            "canceled",
            "human_waiting",
            "unavailable",
            "unknown",
        ):
            code, result, err = cycle(
                self.store,
                T0,
                observations=[self.quota_observation(remaining=50)],
                task_states=[self.idle(status=status)],
            )
            self.assertEqual(code, 0, err)
            self.assert_no_wake(result, f"task-{status}")
        # A stale task-state observation is treated as unknown.
        _, result, _ = cycle(
            self.store,
            T0,
            observations=[self.quota_observation(remaining=50)],
            task_states=[self.idle(observed_at="2026-09-17T11:30:00+00:00")],
        )
        self.assert_no_wake(result, "task-state-stale")

    def test_paused_expired_and_removed_registrations_do_not_wake(self) -> None:
        rid = self.register(extra=("--expires-in-minutes", "60"))["registration_id"]
        run(
            "pause",
            "--store",
            self.store,
            "--registration-id",
            rid,
            "--owner",
            "owner-a",
            "--now",
            T0,
        )
        _, result, _ = cycle(
            self.store,
            T0,
            observations=[self.quota_observation(remaining=50)],
            task_states=[self.idle()],
        )
        self.assert_no_wake(result, "registration-paused")
        run(
            "resume",
            "--store",
            self.store,
            "--registration-id",
            rid,
            "--owner",
            "owner-a",
            "--now",
            T0,
        )
        late = "2026-09-17T13:00:00+00:00"
        _, result, _ = cycle(
            self.store,
            late,
            observations=[self.quota_observation(remaining=50, observed_at=late)],
            task_states=[self.idle(observed_at=late)],
        )
        self.assert_no_wake(result, "registration-expired")
        self.assertEqual(result["observation_requests"], [])
        _, inspected, _ = run("inspect", "--store", self.store, "--now", late)
        self.assertEqual(inspected["registrations"][0]["status"], "expired")
        self.assertIn("expired", inspected["registrations"][0]["next_action"])
        code, extended, err = run(
            "update",
            "--store",
            self.store,
            "--registration-id",
            rid,
            "--owner",
            "owner-a",
            "--expires-in-minutes",
            "120",
            "--now",
            late,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(extended["status"], "waiting")
        run(
            "remove",
            "--store",
            self.store,
            "--registration-id",
            rid,
            "--owner",
            "owner-a",
            "--now",
            late,
        )
        _, result, _ = cycle(
            self.store, late, task_states=[self.idle(observed_at=late)]
        )
        self.assertEqual(result["skipped"], [])
        self.assertEqual(result["wake_proposals"], [])

    def test_early_quota_reset_wakes_before_advertised_reset(self) -> None:
        self.register()
        advertised = "2026-09-20T00:00:00+00:00"
        _, result, _ = cycle(
            self.store,
            T0,
            observations=[self.quota_observation(remaining=0, reset_at=advertised)],
            task_states=[self.idle()],
        )
        self.assert_no_wake(result, "gate-closed")
        # The advertised reset is days away: the planned check is the 360-minute
        # ceiling, and a tick at the old fixed cadence requests nothing.
        self.assertEqual(result["schedule"]["gates"][0]["basis"], "reset-hint")
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T18:00:00+00:00")
        tick = "2026-09-17T12:15:00+00:00"
        _, result, _ = cycle(
            self.store, tick, task_states=[self.idle(observed_at=tick)]
        )
        self.assertEqual(result["observation_requests"], [])
        self.assert_no_wake(result, "gate-observation-stale")
        # An imported early recovery still admits before the planned check; the
        # reset timestamp alone never could.
        _, result, _ = cycle(
            self.store,
            tick,
            observations=[self.quota_observation(remaining=100, observed_at=tick)],
            task_states=[self.idle(observed_at=tick)],
        )
        [proposal] = result["wake_proposals"]
        self.assertEqual(proposal["gate_observation"]["result"], "open")


class DispatchBookkeeping(CycleHelpers):
    def test_accepted_dispatch_completes_episode_until_explicit_rearm(self) -> None:
        rid = self.register()["registration_id"]
        [proposal] = self.propose()
        code, reported, err = self.report(
            proposal["attempt_id"], "accepted", tool_response="follow-up queued"
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(reported["attempt"]["status"], "accepted")
        self.assertEqual(reported["registration"]["status"], "completed")
        self.assertEqual(reported["registration"]["completed_episodes"], ["episode-1"])
        self.assertEqual(reported["delivery_claim"], "accepted_by_native_send_tool")
        self.assertNotIn("delivered", reported["delivery_claim"])
        later = "2026-09-17T12:20:00+00:00"
        _, result, _ = cycle(
            self.store,
            later,
            observations=[self.quota_observation(remaining=50, observed_at=later)],
            task_states=[self.idle(observed_at=later)],
        )
        self.assert_no_wake(result, "registration-completed")
        self.assertEqual(result["observation_requests"], [])
        # Same episode cannot be rearmed; a new explicit episode can.
        common = ("--store", self.store, "--registration-id", rid, "--owner", "owner-a")
        code, _, err = run(
            "rearm",
            "--store",
            self.store,
            "--registration-id",
            rid,
            "--owner",
            "owner-b",
            "--episode",
            "episode-2",
            "--now",
            later,
        )
        self.assertEqual(code, 2)
        self.assertIn("owner-mismatch", err)
        code, _, err = run("rearm", *common, "--episode", "episode-1", "--now", later)
        self.assertEqual(code, 2)
        self.assertIn("episode-reused", err)
        code, rearmed, err = run(
            "rearm", *common, "--episode", "episode-2", "--now", later
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(rearmed["status"], "waiting")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", later)
        self.assertEqual(inspected["registrations"][0]["status"], "waiting")
        self.assertEqual(inspected["registrations"][0]["episode"], "episode-2")
        [proposal] = self.propose(now=later)
        self.assertEqual(proposal["episode"], "episode-2")

    def test_rearm_of_an_expired_registration_needs_an_explicit_new_expiry(self) -> None:
        rid = self.register(extra=("--expires-in-minutes", "60"))["registration_id"]
        [proposal] = self.propose()
        self.report(proposal["attempt_id"], "accepted")
        common = ("--store", self.store, "--registration-id", rid, "--owner", "owner-a")
        late = "2026-09-17T14:00:00+00:00"
        code, payload, err = run("rearm", *common, "--episode", "episode-2", "--now", late)
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("invalid-transition", err)
        self.assertIn("expires-in-minutes", err)
        _, inspected, _ = run("inspect", "--store", self.store, "--now", late)
        self.assertEqual(inspected["registrations"][0]["episode"], "episode-1")
        self.assertEqual(inspected["registrations"][0]["status"], "completed")
        code, rearmed, err = run(
            "rearm", *common, "--episode", "episode-2", "--expires-in-minutes", "60",
            "--now", late,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(rearmed["status"], "waiting")
        self.assertFalse(rearmed["expired"])
        self.assertEqual(rearmed["expires_at"], "2026-09-17T15:00:00+00:00")
        soon = "2026-09-17T14:05:00+00:00"
        [proposal] = self.propose(now=soon)
        self.assertEqual(proposal["episode"], "episode-2")
        # Rearming an unexpired registration may also renew its horizon explicitly.
        self.report(proposal["attempt_id"], "accepted", now=soon)
        code, renewed, err = run(
            "rearm", *common, "--episode", "episode-3", "--expires-in-minutes", "600",
            "--now", soon,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(renewed["expires_at"], "2026-09-18T00:05:00+00:00")

    def test_every_prior_episode_identity_is_rejected_on_rearm(self) -> None:
        rid = self.register()["registration_id"]
        [proposal] = self.propose()
        self.report(proposal["attempt_id"], "accepted")
        common = ("--store", self.store, "--registration-id", rid, "--owner", "owner-a")
        code, _, err = run("rearm", *common, "--episode", "episode-2", "--now", T0)
        self.assertEqual(code, 0, err)
        # episode-2 never dispatched; it is superseded by episode-3 without an attempt.
        code, _, err = run("rearm", *common, "--episode", "episode-3", "--now", T0)
        self.assertEqual(code, 0, err)
        for reused in ("episode-1", "episode-2", "episode-3"):
            code, payload, err = run("rearm", *common, "--episode", reused, "--now", T0)
            self.assertEqual(code, 2, reused)
            self.assertIsNone(payload)
            self.assertIn("episode-reused", err)
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        [entry] = inspected["registrations"]
        self.assertEqual(entry["episode"], "episode-3")
        self.assertEqual(entry["episodes"], ["episode-1", "episode-2", "episode-3"])
        code, _, err = run("rearm", *common, "--episode", "episode-4", "--now", T0)
        self.assertEqual(code, 0, err)

    def test_send_is_preceded_by_a_registry_recheck_and_a_target_read(self) -> None:
        rid = self.register()["registration_id"]
        [proposal] = self.propose()
        steps = proposal["native_steps"]
        self.assertEqual(
            [step["step"] for step in steps], ["recheck", "read", "send", "report"]
        )
        recheck = steps[0]
        self.assertEqual(recheck["command"], ["inspect"])
        self.assertEqual(
            recheck["require"],
            {
                "registration_id": rid,
                "status": "reserved",
                "attempt_id": proposal["attempt_id"],
                "episode": "episode-1",
                "expired": False,
            },
        )
        self.assertIn("not_sent", recheck["on_mismatch"])
        self.assertEqual(steps[1]["require"], {"status": "idle", "episode": "episode-1"})
        self.assertTrue(
            any(l.startswith("registry_recheck_is_not_atomic") for l in proposal["limitations"])
        )
        # The recheck is satisfied right after planning...
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        [entry] = inspected["registrations"]
        self.assertEqual(
            {k: entry[k] for k in recheck["require"]}, recheck["require"]
        )
        # ...and no longer once the owner rearms between planning and sending.
        run(
            "rearm", "--store", self.store, "--registration-id", rid, "--owner", "owner-a",
            "--episode", "episode-2", "--now", T0,
        )
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        [entry] = inspected["registrations"]
        self.assertNotEqual(
            {k: entry[k] for k in recheck["require"]}, recheck["require"]
        )
        code, _, err = self.report(proposal["attempt_id"], "not_sent")
        self.assertEqual(code, 2)
        self.assertIn("attempt-not-reserved", err)

    def test_dispatch_inputs_are_immutable_while_an_attempt_is_reserved(self) -> None:
        rid = self.register()["registration_id"]
        [proposal] = self.propose()
        common = ("--store", self.store, "--registration-id", rid, "--owner", "owner-a")
        recheck = proposal["native_steps"][0]["require"]
        revised_gate = json.dumps(dict(QUOTA_GATE, bucket="daily"))
        for label, extra in (
            ("continuation", ("--continuation", "Replaced continuation.")),
            ("gate", ("--gate-json", revised_gate)),
            ("gate with expiry", ("--gate-json", revised_gate, "--expires-in-minutes", "600")),
        ):
            with self.subTest(label=label):
                code, payload, err = run("update", *common, *extra, "--now", T0)
                self.assertEqual(code, 2)
                self.assertIsNone(payload)
                self.assertIn("invalid-transition", err)
        # Nothing was applied, so the planned message still describes the registry.
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        [entry] = inspected["registrations"]
        self.assertEqual(entry["gate"], QUOTA_GATE)
        self.assertEqual(entry["gate_key"], proposal["gate_key"])
        self.assertEqual(entry["continuation"], "Continue the bounded work.")
        self.assertEqual(entry["expires_at"], "2026-09-18T12:00:00+00:00")
        self.assertEqual({k: entry[k] for k in recheck}, recheck)
        # Expiry is registration state the recheck already covers; it may be renewed.
        code, renewed, err = run(
            "update", *common, "--expires-in-minutes", "600", "--now", T0
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(renewed["status"], "reserved")
        self.assertEqual(renewed["expires_at"], "2026-09-17T22:00:00+00:00")
        # Once the attempt is reported, the registration owns its inputs again.
        code, _, err = self.report(proposal["attempt_id"], "not_sent")
        self.assertEqual(code, 0, err)
        code, updated, err = run(
            "update", *common, "--continuation", "Replaced continuation.", "--now", T0
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(updated["status"], "waiting")
        self.assertEqual(updated["continuation"], "Replaced continuation.")

    def test_unknown_dispatch_requires_reconciliation_and_never_auto_retries(
        self,
    ) -> None:
        self.register()
        [proposal] = self.propose()
        code, reported, err = self.report(
            proposal["attempt_id"], "unknown", tool_response="timeout after send"
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(reported["registration"]["status"], "unresolved")
        for minute in (20, 35, 50):
            later = f"2026-09-17T12:{minute}:00+00:00"
            _, result, _ = cycle(
                self.store,
                later,
                observations=[self.quota_observation(remaining=50, observed_at=later)],
                task_states=[self.idle(observed_at=later)],
            )
            self.assert_no_wake(result, "registration-unresolved")
            [unresolved] = result["unresolved_attempts"]
            self.assertEqual(unresolved["status"], "unknown")
            self.assertIn("reconcile", unresolved["next_action"])
        # Reporting an already-reported attempt is rejected.
        code, _, err = self.report(proposal["attempt_id"], "accepted")
        self.assertEqual(code, 2)
        self.assertIn("attempt-not-reserved", err)
        code, reconciled, err = run(
            "reconcile",
            "--store",
            self.store,
            "--attempt-id",
            proposal["attempt_id"],
            "--resolution",
            "accepted",
            "--evidence-json",
            json.dumps({"target_transcript_shows_message": True}),
            "--now",
            "2026-09-17T13:00:00+00:00",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(reconciled["attempt"]["status"], "reconciled_accepted")
        self.assertEqual(reconciled["registration"]["status"], "completed")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        self.assertEqual(inspected["unresolved_attempts"], [])

    def test_abandoned_reserved_attempt_is_settled_only_by_reconcile_with_evidence(
        self,
    ) -> None:
        # The monitor lost its process after reserving two attempts. Nobody saw the
        # send, so each is settled from the target transcript, never re-reported.
        self.register(task_id="task-1")
        self.register(task_id="task-2")
        proposals = {p["task_id"]: p for p in self.propose(task_ids=("task-1", "task-2"))}
        later = "2026-09-17T13:00:00+00:00"

        def reconcile(attempt_id: str, resolution: str, **evidence: Any):
            return run(
                "reconcile", "--store", self.store, "--attempt-id", attempt_id,
                "--resolution", resolution, "--evidence-json", json.dumps(evidence),
                "--now", later,
            )

        code, payload, err = reconcile(proposals["task-1"]["attempt_id"], "accepted")
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("missing-evidence", err)
        code, accepted, err = reconcile(
            proposals["task-1"]["attempt_id"], "accepted", target_transcript_shows_message=True
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(accepted["attempt"]["status"], "reconciled_accepted")
        self.assertEqual(accepted["registration"]["status"], "completed")
        self.assertEqual(accepted["registration"]["completed_episodes"], ["episode-1"])
        self.assertEqual(accepted["delivery_claim"], "accepted_by_native_send_tool")
        code, not_sent, err = reconcile(
            proposals["task-2"]["attempt_id"], "not_sent", target_transcript_shows_message=False
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(not_sent["attempt"]["status"], "reconciled_not_sent")
        self.assertEqual(not_sent["registration"]["status"], "waiting")
        self.assertEqual(not_sent["delivery_claim"], "not_sent")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", later)
        self.assertEqual(inspected["unresolved_attempts"], [])
        self.assertEqual(inspected["attention"], [])
        # A reconciled attempt takes neither a report nor a second reconciliation.
        code, _, err = self.report(proposals["task-2"]["attempt_id"], "not_sent", now=later)
        self.assertEqual(code, 2)
        self.assertIn("attempt-not-reserved", err)
        code, _, err = reconcile(proposals["task-2"]["attempt_id"], "accepted", seen=True)
        self.assertEqual(code, 2)
        self.assertIn("attempt-not-unresolved", err)
        # task-2 waits again and gets a fresh second attempt for the same episode.
        [proposal] = self.propose(now=later, task_ids=("task-2",))
        self.assertEqual((proposal["task_id"], proposal["episode"]), ("task-2", "episode-1"))
        self.assertNotEqual(proposal["attempt_id"], proposals["task-2"]["attempt_id"])

    def test_rearm_supersedes_a_reserved_or_unknown_attempt_without_resending(
        self,
    ) -> None:
        reserved = self.register(task_id="task-1")["registration_id"]
        unknown = self.register(task_id="task-2")["registration_id"]
        proposals = {p["task_id"]: p for p in self.propose(task_ids=("task-1", "task-2"))}
        code, _, err = self.report(
            proposals["task-2"]["attempt_id"], "unknown", tool_response="timeout"
        )
        self.assertEqual(code, 0, err)
        for rid, task_id, superseded in (
            (reserved, "task-1", "superseded_reserved"),
            (unknown, "task-2", "superseded_unknown"),
        ):
            with self.subTest(task_id=task_id):
                attempt_id = proposals[task_id]["attempt_id"]
                code, rearmed, err = run(
                    "rearm", "--store", self.store, "--registration-id", rid, "--owner",
                    "owner-a", "--episode", "episode-2", "--now", T0,
                )
                self.assertEqual(code, 0, err)
                self.assertEqual(rearmed["status"], "waiting")
                self.assertEqual(rearmed["episode"], "episode-2")
                self.assertIsNone(rearmed["attempt_id"])
                self.assertIsNone(rearmed["unresolved_reason"])
                self.assertEqual(rearmed["attempt_count"], 0)
                # The old attempt is closed: no report, no reconciliation, and the
                # diagnostic names the superseded state it is in.
                code, _, err = self.report(attempt_id, "accepted")
                self.assertEqual(code, 2)
                self.assertIn("attempt-not-reserved", err)
                self.assertIn(superseded, err)
                code, _, err = run(
                    "reconcile", "--store", self.store, "--attempt-id", attempt_id,
                    "--resolution", "accepted", "--evidence-json", json.dumps({"seen": True}),
                    "--now", T0,
                )
                self.assertEqual(code, 2)
                self.assertIn("attempt-not-unresolved", err)
                self.assertIn(superseded, err)
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        self.assertEqual(inspected["unresolved_attempts"], [])
        self.assertEqual(inspected["attention"], [])
        # Each new episode dispatches with a fresh attempt, never the old message.
        fresh = self.propose(now="2026-09-17T12:20:00+00:00", task_ids=("task-1", "task-2"))
        self.assertEqual({p["episode"] for p in fresh}, {"episode-2"})
        self.assertTrue(
            {p["attempt_id"] for p in fresh}.isdisjoint(
                {p["attempt_id"] for p in proposals.values()}
            )
        )

    def test_reserved_registration_past_expiry_fails_recheck_and_rearms_only_with_new_expiry(
        self,
    ) -> None:
        rid = self.register(extra=("--expires-in-minutes", "30"))["registration_id"]
        [proposal] = self.propose()
        recheck = proposal["native_steps"][0]["require"]
        common = ("--store", self.store, "--registration-id", rid, "--owner", "owner-a")
        late = "2026-09-17T12:45:00+00:00"
        _, inspected, _ = run("inspect", "--store", self.store, "--now", late)
        [entry] = inspected["registrations"]
        self.assertEqual(entry["status"], "reserved")
        self.assertTrue(entry["expired"])
        # expired is the recheck's only expiry guard, and it now refuses the send.
        self.assertNotEqual({k: entry[k] for k in recheck}, recheck)
        [attention] = inspected["attention"]
        self.assertEqual(attention["status"], "reserved")
        self.assertEqual(attention["attempt_id"], proposal["attempt_id"])
        code, payload, err = run("rearm", *common, "--episode", "episode-2", "--now", late)
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("invalid-transition", err)
        _, inspected, _ = run("inspect", "--store", self.store, "--now", late)
        self.assertEqual(inspected["registrations"][0]["status"], "reserved")
        self.assertEqual(len(inspected["unresolved_attempts"]), 1)
        # An explicit new expiry starts a new wait and supersedes the abandoned attempt.
        code, rearmed, err = run(
            "rearm", *common, "--episode", "episode-2", "--expires-in-minutes", "60",
            "--now", late,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(rearmed["status"], "waiting")
        self.assertFalse(rearmed["expired"])
        self.assertEqual(rearmed["expires_at"], "2026-09-17T13:45:00+00:00")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", late)
        self.assertEqual(inspected["unresolved_attempts"], [])
        self.assertEqual(inspected["attention"], [])
        code, _, err = self.report(proposal["attempt_id"], "not_sent", now=late)
        self.assertEqual(code, 2)
        self.assertIn("attempt-not-reserved", err)

    def test_not_sent_returns_to_waiting_with_bounded_attempts(self) -> None:
        self.register()
        attempts = []
        for minute in (0, 15, 30):
            now = f"2026-09-17T12:{minute:02d}:00+00:00"
            [proposal] = self.propose(now=now)
            attempts.append(proposal["attempt_id"])
            code, reported, err = self.report(
                proposal["attempt_id"],
                "not_sent",
                now=now,
                tool_response="target was running",
            )
            self.assertEqual(code, 0, err)
            self.assertEqual(reported["attempt"]["status"], "not_sent")
        self.assertEqual(len(set(attempts)), 3)
        self.assertEqual(reported["registration"]["status"], "unresolved")
        self.assertEqual(reported["registration"]["unresolved_reason"], "attempt-limit")
        self.assertEqual(self.propose(now="2026-09-17T12:45:00+00:00"), [])

    def test_partial_dispatch_keeps_other_attempts_reserved_and_visible(self) -> None:
        self.register(task_id="task-1")
        self.register(task_id="task-2")
        proposals = self.propose(task_ids=("task-1", "task-2"))
        self.assertEqual([p["task_id"] for p in proposals], ["task-1", "task-2"])
        code, _, err = self.report(proposals[0]["attempt_id"], "accepted")
        self.assertEqual(code, 0, err)
        _, inspected, _ = run(
            "inspect", "--store", self.store, "--now", "2026-09-17T13:30:00+00:00"
        )
        [unresolved] = inspected["unresolved_attempts"]
        self.assertEqual(unresolved["attempt_id"], proposals[1]["attempt_id"])
        self.assertEqual(unresolved["task_id"], "task-2")
        self.assertEqual(unresolved["status"], "reserved")
        self.assertEqual(unresolved["age_minutes"], 90)
        self.assertIn("report", unresolved["next_action"])
        by_task = {r["task_id"]: r for r in inspected["registrations"]}
        self.assertEqual(by_task["task-1"]["status"], "completed")
        self.assertEqual(by_task["task-2"]["status"], "reserved")
        self.assertIn("report", by_task["task-2"]["next_action"])
        self.assertIn("rearm", by_task["task-1"]["next_action"])
        # A lost process never releases the reservation into a duplicate wake.
        self.assertEqual(
            self.propose(now="2026-09-17T14:00:00+00:00", task_ids=("task-2",)), []
        )

    def test_stuck_registrations_are_surfaced_when_nothing_is_waiting(self) -> None:
        # Three registrations end up reserved (monitor crashed before report),
        # unresolved (attempt limit), and expired; none is waiting any more.
        self.register(task_id="task-1")
        self.register(task_id="task-2")
        self.register(task_id="task-3", extra=("--expires-in-minutes", "30"))
        for minute in (0, 15, 30):
            now = f"2026-09-17T12:{minute:02d}:00+00:00"
            for proposal in self.propose(now=now, task_ids=("task-1", "task-2")):
                if proposal["task_id"] == "task-2":
                    self.report(proposal["attempt_id"], "not_sent", now=now)
        later = "2026-09-17T13:00:00+00:00"
        _, result, _ = cycle(self.store, later)
        self.assertEqual(result["wake_proposals"], [])
        code, inspected, err = run("inspect", "--store", self.store, "--now", later)
        self.assertEqual(code, 0, err)
        self.assertEqual(
            [r["status"] for r in inspected["registrations"]],
            ["reserved", "unresolved", "expired"],
        )
        attention = {a["task_id"]: a for a in inspected["attention"]}
        self.assertEqual(set(attention), {"task-1", "task-2", "task-3"})
        self.assertEqual(attention["task-1"]["status"], "reserved")
        self.assertIn("report attempt", attention["task-1"]["next_action"])
        self.assertEqual(attention["task-2"]["unresolved_reason"], "attempt-limit")
        self.assertIn("rearm", attention["task-2"]["next_action"])
        self.assertEqual(attention["task-3"]["status"], "expired")
        self.assertIn("expired", attention["task-3"]["next_action"])
        # Each entry names when it entered its state, so an unchanged entry can be
        # recognised across ticks and not re-reported as new.
        self.assertEqual(attention["task-1"]["since"], T0)
        self.assertEqual(attention["task-2"]["since"], "2026-09-17T12:30:00+00:00")
        self.assertEqual(attention["task-3"]["since"], "2026-09-17T12:30:00+00:00")
        self.assertEqual(result["attention"], inspected["attention"])
        # A tick later, nothing changed: the same entries with the same markers.
        _, again, _ = run(
            "inspect", "--store", self.store, "--now", "2026-09-17T13:15:00+00:00"
        )
        self.assertEqual(again["attention"], inspected["attention"])

    def test_expired_registration_since_is_its_expiry_before_and_after_a_cycle(
        self,
    ) -> None:
        # The same expiry must read as the same stuck work whether inspect sees
        # it before any cycle or after a cycle has persisted the expired status.
        self.register(extra=("--expires-in-minutes", "30"))
        expires_at = "2026-09-17T12:30:00+00:00"
        _, before, _ = run("inspect", "--store", self.store, "--now", "2026-09-17T12:45:00+00:00")
        [entry] = before["attention"]
        self.assertEqual((entry["status"], entry["since"]), ("expired", expires_at))
        _, result, _ = cycle(self.store, "2026-09-17T12:45:07+00:00")
        self.assertEqual(result["attention"], before["attention"])
        _, after, _ = run("inspect", "--store", self.store, "--now", "2026-09-17T13:00:00+00:00")
        self.assertEqual(after["registrations"][0]["status"], "expired")
        self.assertEqual(after["attention"], before["attention"])

    def test_reserved_next_action_routes_actors_without_send_knowledge_to_reconcile(
        self,
    ) -> None:
        # A restarted monitor or an owner finding a reservation has no send
        # knowledge; every guidance surface must send it to reconcile with
        # target-transcript evidence rather than to an evidence-free not_sent.
        rid = self.register()["registration_id"]
        [proposal] = self.propose()
        attempt_id = proposal["attempt_id"]
        later = "2026-09-17T13:00:00+00:00"
        _, inspected, _ = run("inspect", "--store", self.store, "--now", later)
        [registration] = inspected["registrations"]
        [attention] = inspected["attention"]
        [unresolved] = inspected["unresolved_attempts"]
        _, result, _ = cycle(self.store, later)
        for label, text in (
            ("registration", registration["next_action"]),
            ("attention", attention["next_action"]),
            ("unresolved", unresolved["next_action"]),
            ("cycle unresolved", result["unresolved_attempts"][0]["next_action"]),
        ):
            with self.subTest(surface=label):
                self.assertIn("holding this reservation", text)
                self.assertIn("reconciles it with target-transcript evidence", text)
                self.assertIn(f"reconcile --attempt-id {attempt_id}", text)
        # The owner's remove leaves the same distinction on the detached entry.
        run(
            "remove", "--store", self.store, "--registration-id", rid, "--owner",
            "owner-a", "--now", later,
        )
        _, inspected, _ = run("inspect", "--store", self.store, "--now", later)
        [detached] = inspected["attention"]
        self.assertEqual(detached["status"], "detached")
        self.assertIn("holding this reservation", detached["next_action"])
        self.assertIn("reconciles it with target-transcript evidence", detached["next_action"])
        self.assertIn(f"reconcile --attempt-id {attempt_id}", detached["next_action"])

    def test_owner_removal_during_a_reserved_attempt_is_preserved(self) -> None:
        rid = self.register()["registration_id"]
        [proposal] = self.propose()
        code, _, err = run(
            "remove",
            "--store",
            self.store,
            "--registration-id",
            rid,
            "--owner",
            "owner-a",
            "--now",
            T0,
        )
        self.assertEqual(code, 0, err)
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        self.assertEqual(inspected["registrations"], [])
        [unresolved] = inspected["unresolved_attempts"]
        self.assertEqual(unresolved["attempt_id"], proposal["attempt_id"])
        code, reported, err = self.report(proposal["attempt_id"], "not_sent")
        self.assertEqual(code, 0, err)
        self.assertEqual(reported["registration"]["status"], "removed")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        self.assertEqual(inspected["registrations"], [])
        self.assertEqual(inspected["unresolved_attempts"], [])
        _, result, _ = cycle(self.store, T0, task_states=[self.idle()])
        self.assertEqual(result["observation_requests"], [])
        self.assertEqual(result["wake_proposals"], [])

    def test_removed_registration_keeps_its_outstanding_attempt_in_attention(
        self,
    ) -> None:
        # The owner cancels while the monitor holds a reservation. The registry is
        # empty, but the attempt still needs a closeout, so the single attention
        # signal must carry it until the monitor closes it with evidence.
        rid = self.register()["registration_id"]
        [proposal] = self.propose()
        removed_at = "2026-09-17T12:05:00+00:00"
        code, _, err = run(
            "remove", "--store", self.store, "--registration-id", rid, "--owner",
            "owner-a", "--now", removed_at,
        )
        self.assertEqual(code, 0, err)
        later = "2026-09-17T12:20:00+00:00"
        code, inspected, err = run("inspect", "--store", self.store, "--now", later)
        self.assertEqual(code, 0, err)
        self.assertEqual(inspected["registrations"], [])
        [entry] = inspected["attention"]
        self.assertEqual(entry["registration_id"], rid)
        self.assertEqual((entry["host"], entry["task_id"]), ("host-a", "task-1"))
        self.assertEqual(entry["episode"], "episode-1")
        self.assertEqual(entry["status"], "detached")
        self.assertEqual(entry["attempt_id"], proposal["attempt_id"])
        self.assertEqual(entry["since"], removed_at)
        self.assertIn("not_sent", entry["next_action"])
        # The cycle view is the same signal, so a no-op check on attention alone sees it.
        _, result, _ = cycle(self.store, later)
        self.assertEqual(result["wake_proposals"], [])
        self.assertEqual(result["attention"], inspected["attention"])
        [unresolved] = result["unresolved_attempts"]
        self.assertEqual(unresolved["attempt_id"], entry["attempt_id"])
        # An unchanged entry keeps its marker across ticks.
        _, again, _ = run(
            "inspect", "--store", self.store, "--now", "2026-09-17T12:35:00+00:00"
        )
        self.assertEqual(again["attention"], inspected["attention"])
        # Explicit closeout with known not-sent evidence clears it everywhere.
        code, reported, err = self.report(
            proposal["attempt_id"], "not_sent", now=later, recheck="registration removed"
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(reported["delivery_claim"], "not_sent")
        self.assertEqual(reported["registration"]["status"], "removed")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", later)
        self.assertEqual(inspected["attention"], [])
        self.assertEqual(inspected["unresolved_attempts"], [])

    def test_removed_registration_with_an_unknown_attempt_stays_detached_until_reconciled(
        self,
    ) -> None:
        rid = self.register()["registration_id"]
        [proposal] = self.propose()
        code, _, err = self.report(proposal["attempt_id"], "unknown", tool_response="timeout")
        self.assertEqual(code, 0, err)
        removed_at = "2026-09-17T12:05:00+00:00"
        run(
            "remove", "--store", self.store, "--registration-id", rid, "--owner",
            "owner-a", "--now", removed_at,
        )
        _, inspected, _ = run("inspect", "--store", self.store, "--now", removed_at)
        [entry] = inspected["attention"]
        self.assertEqual(entry["status"], "detached")
        self.assertEqual(entry["attempt_id"], proposal["attempt_id"])
        self.assertEqual(entry["since"], removed_at)
        self.assertIn("reconcile", entry["next_action"])
        code, reconciled, err = run(
            "reconcile", "--store", self.store, "--attempt-id", proposal["attempt_id"],
            "--resolution", "accepted", "--evidence-json",
            json.dumps({"target_transcript_shows_message": True}), "--now", removed_at,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(reconciled["attempt"]["status"], "reconciled_accepted")
        self.assertEqual(reconciled["registration"]["status"], "removed")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", removed_at)
        self.assertEqual(inspected["attention"], [])
        self.assertEqual(inspected["unresolved_attempts"], [])

    def test_overlapping_monitor_runs_and_restart_do_not_duplicate(self) -> None:
        self.register()
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        cycle_input = Path(self._tmp.name) / "cycle.json"
        cycle_input.write_text(
            json.dumps({"task_states": [self.idle()]}), encoding="utf-8"
        )
        argv = [
            sys.executable,
            str(SCRIPT),
            "cycle",
            "--store",
            self.store,
            "--input",
            str(cycle_input),
            "--now",
            T0,
        ]
        # Overlap: several independent processes race on the same store.
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            runs = list(
                pool.map(
                    lambda _: subprocess.run(
                        argv, capture_output=True, text=True, check=False
                    ),
                    range(4),
                )
            )
        for completed in runs:
            self.assertEqual(completed.returncode, 0, completed.stderr)
        proposals = [json.loads(r.stdout)["wake_proposals"] for r in runs]
        self.assertEqual(sum(len(p) for p in proposals), 1)
        # Restart: a fresh process sees the reservation and does not re-propose.
        again = subprocess.run(argv, capture_output=True, text=True, check=False)
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(json.loads(again.stdout)["wake_proposals"], [])
        [unresolved] = json.loads(again.stdout)["unresolved_attempts"]
        self.assertEqual(unresolved["status"], "reserved")

    def test_gate_binding_change_invalidates_cached_observation(self) -> None:
        rid = self.register()["registration_id"]
        _, result, _ = cycle(
            self.store, T0, observations=[self.quota_observation(remaining=50)]
        )
        self.assertEqual(result["ingested_observations"][0]["result"], "open")
        revised = dict(QUOTA_GATE, policy_revision="policy-2")
        code, _, err = run(
            "update",
            "--store",
            self.store,
            "--registration-id",
            rid,
            "--owner",
            "owner-a",
            "--gate-json",
            json.dumps(revised),
            "--now",
            T0,
        )
        self.assertEqual(code, 0, err)
        _, result, _ = cycle(self.store, T0, task_states=[self.idle()])
        self.assert_no_wake(result, "gate-unobserved")
        [request] = result["observation_requests"]
        self.assertEqual(request["gate"], revised)
        # The old observation cannot be replayed against the new binding: a key no
        # registration uses is skipped, never stored, and never aborts the cycle.
        stale_key_observation = self.quota_observation(remaining=50)
        stale_key_observation["gate_key"] = result["skipped"][0]["registration_id"]
        code, result, err = cycle(self.store, T0, observations=[stale_key_observation])
        self.assertEqual(code, 0, err)
        [ingested] = result["ingested_observations"]
        self.assertFalse(ingested["accepted"])
        self.assertEqual(ingested["reason"], "gate-not-registered")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        self.assertNotIn(
            stale_key_observation["gate_key"],
            [o["gate_key"] for o in inspected["observations"]],
        )

    def test_owner_remove_or_gate_change_between_plan_and_result_skips_only_that_gate(
        self,
    ) -> None:
        # The tick's plan cycle lists two gates; while the adapter queries them the
        # owner removes one registration and changes the other's gate. The result
        # cycle must apply everything that still belongs to a registration.
        weekly = self.register(task_id="task-1")["registration_id"]
        daily = self.register(
            task_id="task-2", gate=dict(QUOTA_GATE, bucket="daily")
        )["registration_id"]
        _, plan, _ = cycle(self.store, "2026-09-17T12:00:05+00:00")
        keys = {r["gate"]["bucket"]: r["gate_key"] for r in plan["observation_requests"]}
        self.assertEqual(set(keys), {"weekly", "daily"})
        common = ("--store", self.store, "--owner", "owner-a", "--now", "2026-09-17T12:00:40+00:00")
        code, _, err = run("remove", *common, "--registration-id", weekly)
        self.assertEqual(code, 0, err)
        code, _, err = run(
            "update", *common, "--registration-id", daily,
            "--gate-json", json.dumps(dict(QUOTA_GATE, bucket="monthly")),
        )
        self.assertEqual(code, 0, err)
        at = "2026-09-17T12:00:45+00:00"
        observations = [
            dict(self.quota_observation(remaining=50, observed_at=at), gate_key=keys["weekly"]),
            dict(
                self.quota_observation(remaining=50, observed_at=at, bucket="daily"),
                gate_key=keys["daily"],
            ),
        ]
        code, result, err = cycle(
            self.store, at, observations=observations,
            task_states=[self.idle("task-1", observed_at=at), self.idle("task-2", observed_at=at)],
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(
            [(i["accepted"], i["reason"]) for i in result["ingested_observations"]],
            [(False, "gate-not-registered"), (False, "gate-not-registered")],
        )
        self.assertEqual(result["wake_proposals"], [])
        [skip] = result["skipped"]
        self.assertEqual((skip["registration_id"], skip["reason"]), (daily, "gate-unobserved"))
        [request] = result["observation_requests"]
        self.assertEqual(request["gate"]["bucket"], "monthly")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        self.assertEqual(inspected["observations"], [], "nothing unregistered is stored")
        # A gate that is still registered is applied in the same cycle.
        self.register(task_id="task-3")
        code, result, err = cycle(
            self.store, at,
            observations=[
                dict(self.quota_observation(remaining=50, observed_at=at), gate_key=keys["weekly"]),
            ],
            task_states=[self.idle("task-3", observed_at=at)],
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(result["ingested_observations"][0]["result"], "open")
        self.assertEqual([p["task_id"] for p in result["wake_proposals"]], ["task-3"])

    def test_quota_disappearance_after_observation_is_an_acknowledged_limitation(
        self,
    ) -> None:
        self.register()
        [proposal] = self.propose()
        [send] = [s for s in proposal["native_steps"] if s["step"] == "send"]
        message = send["arguments"]["message"]
        self.assertIn("revalidate", message)
        self.assertIn("remaining capacity", message)
        self.assertTrue(
            any(
                l.startswith("observation_is_a_snapshot")
                for l in proposal["limitations"]
            )
        )
        # Quota vanishes after the observation; the engine cannot see that and says so.
        code, reported, err = self.report(proposal["attempt_id"], "accepted")
        self.assertEqual(code, 0, err)
        self.assertEqual(reported["delivery_claim"], "accepted_by_native_send_tool")
        self.assertTrue(
            any(
                l.startswith("observation_is_a_snapshot")
                for l in reported["limitations"]
            )
        )
        _, result, _ = cycle(
            self.store,
            "2026-09-17T12:16:00+00:00",
            observations=[
                self.quota_observation(
                    remaining=0, observed_at="2026-09-17T12:16:00+00:00"
                )
            ],
        )
        self.assertEqual(result["ingested_observations"][0]["result"], "closed")
        self.assertEqual(result["wake_proposals"], [])

    def test_provider_failures_back_off_on_one_shared_schedule(self) -> None:
        week = ("--expires-in-minutes", str(7 * 24 * 60))
        self.register(task_id="task-1", extra=week)
        self.register(task_id="task-2", extra=week)
        key = self.gate_key()
        due_at = []
        now = T0
        for failure in range(8):
            _, result, err = cycle(
                self.store,
                now,
                observations=[
                    {
                        "gate_key": key,
                        "status": "error",
                        "observed_at": now,
                        "reason": "provider unavailable",
                    }
                ],
            )
            self.assertIsNotNone(result, err)
            self.assertEqual(result["observation_requests"], [], failure)
            _, inspected, _ = run("inspect", "--store", self.store, "--now", now)
            schedule = inspected["retry_schedule"][key]
            self.assertEqual(schedule["failures"], failure + 1)
            due_at.append(schedule["next_due_at"])
            just_before = aeon_bell.parse_time(
                schedule["next_due_at"], "t"
            ) - timedelta(seconds=1)
            _, result, _ = cycle(self.store, aeon_bell.format_time(just_before))
            self.assertEqual(result["observation_requests"], [])
            now = schedule["next_due_at"]
            _, result, _ = cycle(self.store, now)
            self.assertEqual(len(result["observation_requests"]), 1, "one shared retry")
        delays = [
            (
                aeon_bell.parse_time(due_at[i], "t")
                - aeon_bell.parse_time(due_at[i - 1], "t")
            ).total_seconds()
            / 60
            for i in range(1, len(due_at))
        ]
        self.assertEqual(delays[:5], [30, 60, 120, 240, 360])
        self.assertEqual(delays[5:], [360, 360])
        # A successful observation clears the schedule.
        _, _, _ = cycle(
            self.store,
            now,
            observations=[self.quota_observation(remaining=0, observed_at=now)],
        )
        _, inspected, _ = run("inspect", "--store", self.store, "--now", now)
        self.assertEqual(inspected["retry_schedule"], {})

    def test_imported_observation_retains_its_existing_expiry(self) -> None:
        self.register()
        imported = self.quota_observation(
            remaining=50,
            observed_at="2026-09-17T11:50:00+00:00",
            expires_at="2026-09-17T12:03:00+00:00",
        )
        _, result, _ = cycle(
            self.store, T0, observations=[imported], task_states=[self.idle()]
        )
        self.assertEqual(
            result["ingested_observations"][0]["expires_at"],
            "2026-09-17T12:03:00+00:00",
        )
        self.assertEqual(len(result["wake_proposals"]), 1)
        _, inspected, _ = run(
            "inspect", "--store", self.store, "--now", "2026-09-17T12:03:00+00:00"
        )
        [observation] = inspected["observations"]
        self.assertFalse(observation["fresh"])
        self.assertEqual(observation["source"], "import")
        # An import whose expiry has already passed is recorded stale and still
        # requested. It is observed after the stored 11:50 import (the anchor
        # is monotonic, so an equal-time import would preserve the stored one).
        self.register(task_id="task-2")
        expired = self.quota_observation(
            remaining=50,
            observed_at="2026-09-17T11:52:00+00:00",
            expires_at="2026-09-17T11:57:00+00:00",
        )
        _, result, _ = cycle(
            self.store, T0, observations=[expired], task_states=[self.idle("task-2")]
        )
        self.assertFalse(result["ingested_observations"][0]["fresh"])
        self.assertEqual(result["wake_proposals"], [])
        self.assertEqual(len(result["observation_requests"]), 1)


    def test_imported_observation_cannot_extend_freshness_past_the_window(self) -> None:
        self.register()
        # A closed import advertising a reset two days out cannot stretch its own
        # freshness: it is capped at observed_at + 15 minutes. The requery is the
        # planned check, a quarter of the wait bounded at 360 minutes.
        far = self.quota_observation(
            remaining=0,
            observed_at="2026-09-17T12:31:00+00:00",
            expires_at="2026-09-19T00:00:00+00:00",
            reset_at="2026-09-19T00:00:00+00:00",
        )
        _, result, err = cycle(
            self.store, "2026-09-17T12:31:10+00:00", observations=[far]
        )
        self.assertIsNotNone(result, err)
        [ingested] = result["ingested_observations"]
        self.assertEqual(ingested["expires_at"], "2026-09-17T12:46:00+00:00")
        self.assertTrue(ingested["fresh"])
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T18:31:00+00:00")
        _, result, _ = cycle(self.store, "2026-09-17T12:46:05+00:00")
        self.assertEqual(result["observation_requests"], [])
        _, inspected, _ = run("inspect", "--store", self.store, "--now", "2026-09-17T12:46:05+00:00")
        self.assertFalse(inspected["observations"][0]["fresh"])
        _, result, _ = cycle(self.store, "2026-09-17T18:31:00+00:00")
        self.assertEqual([r["reason"] for r in result["observation_requests"]], ["stale"])
        # An open import far in the future likewise stops proposing after the window.
        open_far = self.quota_observation(
            remaining=50,
            observed_at="2026-09-17T13:00:00+00:00",
            expires_at="2026-09-18T13:00:00+00:00",
        )
        _, result, _ = cycle(
            self.store, "2026-09-17T13:20:00+00:00", observations=[open_far]
        )
        self.assertFalse(result["ingested_observations"][0]["fresh"])
        self.assertEqual(result["wake_proposals"], [])


DAYBREAK_GATE = {
    "kind": "daybreak_status",
    "account": "synthetic-account-a",
    "route": "cli",
    "model": "synthetic-daybreak-model",
    "policy_revision": "policy-1",
}


class DaybreakStatusGate(CycleHelpers):
    def daybreak_observation(self, **overrides: Any) -> dict[str, Any]:
        observation = {
            "gate_key": self.gate_key(),
            "status": "ok",
            "observed_at": T0,
            "account": "synthetic-account-a",
            "route": "cli",
            "exposed_models": ["synthetic-daybreak-model", "other-model"],
            "capacity": "available",
        }
        observation.update(overrides)
        return observation

    def test_open_daybreak_status_wakes_owner_to_recheck_policy_not_to_work(
        self,
    ) -> None:
        self.register(gate=DAYBREAK_GATE)
        _, result, err = cycle(
            self.store,
            T0,
            observations=[self.daybreak_observation()],
            task_states=[self.idle()],
        )
        self.assertIsNotNone(result, err)
        [proposal] = result["wake_proposals"]
        [send] = [s for s in proposal["native_steps"] if s["step"] == "send"]
        message = send["arguments"]["message"]
        self.assertIn("Rolecasting policy", message)
        self.assertIn("harmless probe", message)
        self.assertIn("authorizes no work", message)
        self.assertEqual(
            proposal["gate_observation"]["reason"], "model-exposed-with-capacity"
        )

    def test_daybreak_status_closes_on_missing_model_account_or_capacity(self) -> None:
        self.register(gate=DAYBREAK_GATE)
        # Each case is a later observation of the same gate (monotonic anchor).
        for minute, (overrides, reason) in enumerate((
            ({"exposed_models": ["other-model"]}, "model-not-exposed"),
            ({"account": "synthetic-account-b"}, "binding-mismatch"),
            ({"capacity": "unknown"}, "capacity-unknown"),
            ({"capacity": "exhausted"}, "capacity-exhausted"),
        )):
            at = f"2026-09-17T12:{minute:02d}:00+00:00"
            _, result, err = cycle(
                self.store,
                at,
                observations=[self.daybreak_observation(observed_at=at, **overrides)],
                task_states=[self.idle(observed_at=at)],
            )
            self.assertIsNotNone(result, err)
            self.assertEqual(result["ingested_observations"][0]["reason"], reason)
            self.assert_no_wake(result, "gate-closed")

    def fresh_store(self) -> None:
        self.store = str(Path(self._tmp.name) / f"store-{len(os.listdir(self._tmp.name))}")

    def test_capacity_reset_hint_plans_the_requery_and_never_opens(self) -> None:
        # A daybreak gate closed on exhausted capacity carries the bucket's
        # reset as an optional hint. The plan uses it exactly as a quota
        # bucket's reset_at (a quarter of the way there, bounded 15 to 360);
        # the observation stays closed, and nothing opens when the hint passes.
        self.register(gate=DAYBREAK_GATE, extra=("--expires-in-minutes", "4320"))
        hinted = self.daybreak_observation(
            capacity="exhausted", reset_at="2026-09-17T14:00:00+00:00"
        )
        code, result, err = cycle(self.store, T0, observations=[hinted], task_states=[self.idle()])
        self.assertEqual(code, 0, err)
        [ingested] = result["ingested_observations"]
        self.assertEqual((ingested["result"], ingested["reason"]), ("closed", "capacity-exhausted"))
        self.assert_no_wake(result, "gate-closed")
        [gate] = result["schedule"]["gates"]
        self.assertEqual((gate["observation"], gate["anchor"]), ("closed", T0))
        self.assertEqual((gate["basis"], gate["estimate_at"]), ("reset-hint", "2026-09-17T14:00:00+00:00"))
        self.assertEqual((gate["cadence"], gate["interval_minutes"]), ("adaptive", 30))
        self.assertEqual(result["schedule"]["reason"], "gate-query")
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T12:30:00+00:00")
        self.assertEqual(result["schedule"]["delay_minutes"], 30)
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        [stored] = inspected["observations"]
        self.assertEqual(stored["evidence"]["reset_at"], "2026-09-17T14:00:00+00:00")
        self.assertEqual(stored["evidence"]["capacity"], "exhausted")
        self.assertEqual(stored["expires_at"], "2026-09-17T12:15:00+00:00", "freshness is unchanged")
        # Early reads request nothing; the planned check does; the passed hint
        # admits nothing on its own.
        _, early, _ = cycle(self.store, "2026-09-17T12:20:00+00:00", task_states=[self.idle(observed_at="2026-09-17T12:20:00+00:00")])
        self.assertEqual(early["observation_requests"], [])
        self.assert_no_wake(early, "gate-observation-stale")
        _, planned, _ = cycle(self.store, "2026-09-17T12:30:00+00:00")
        self.assertEqual([r["reason"] for r in planned["observation_requests"]], ["stale"])
        after = "2026-09-17T14:01:00+00:00"
        _, passed, _ = cycle(self.store, after, task_states=[self.idle(observed_at=after)])
        self.assert_no_wake(passed, "gate-observation-stale")
        # Without a hint, the same closure keeps the 60-minute unknown default.
        self.fresh_store()
        self.register(gate=DAYBREAK_GATE, extra=("--expires-in-minutes", "4320"))
        code, result, err = cycle(
            self.store, T0,
            observations=[self.daybreak_observation(capacity="exhausted")],
            task_states=[self.idle()],
        )
        self.assertEqual(code, 0, err)
        self.assert_no_wake(result, "gate-closed")
        [gate] = result["schedule"]["gates"]
        self.assertEqual((gate["basis"], gate["estimate_at"], gate["interval_minutes"]), ("no-estimate", None, 60))
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T13:00:00+00:00")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        self.assertIsNone(inspected["observations"][0]["evidence"]["reset_at"])

    def test_reset_hint_never_implies_exposure_and_yields_to_a_forecast(self) -> None:
        # A reset says nothing about whether a missing model will appear, so a
        # hint on a model-not-exposed or capacity-unknown closure is ignored;
        # an owner forecast still competes as the earliest applicable estimate.
        hint = "2026-09-17T14:00:00+00:00"
        for label, overrides, reason in (
            ("model absent, capacity exhausted", {"exposed_models": [], "capacity": "exhausted", "reset_at": hint}, "model-not-exposed"),
            ("model absent, capacity available", {"exposed_models": ["other-model"], "reset_at": hint}, "model-not-exposed"),
            ("capacity unknown", {"capacity": "unknown", "reset_at": hint}, "capacity-unknown"),
        ):
            with self.subTest(label=label):
                self.fresh_store()
                self.register(gate=DAYBREAK_GATE, extra=("--expires-in-minutes", "4320"))
                code, result, err = cycle(
                    self.store, T0,
                    observations=[self.daybreak_observation(**overrides)],
                    task_states=[self.idle()],
                )
                self.assertEqual(code, 0, err)
                self.assertEqual(result["ingested_observations"][0]["reason"], reason)
                self.assert_no_wake(result, "gate-closed")
                [gate] = result["schedule"]["gates"]
                self.assertEqual((gate["basis"], gate["estimate_at"]), ("no-estimate", None))
                self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T13:00:00+00:00")
        self.fresh_store()
        self.register(
            gate=DAYBREAK_GATE,
            extra=("--expires-in-minutes", "4320", "--expected-open-at", "2026-09-17T12:30:00+00:00"),
        )
        code, result, err = cycle(
            self.store, T0,
            observations=[self.daybreak_observation(capacity="exhausted", reset_at=hint)],
            task_states=[self.idle()],
        )
        self.assertEqual(code, 0, err)
        [gate] = result["schedule"]["gates"]
        self.assertEqual((gate["basis"], gate["estimate_at"]), ("forecast", "2026-09-17T12:30:00+00:00"))
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T12:15:00+00:00")
        # The open path is unchanged: exposure plus available capacity, and the
        # wake still routes the owner to policy revalidation and the probe.
        _, opened, _ = cycle(
            self.store, "2026-09-17T12:15:00+00:00",
            observations=[self.daybreak_observation(observed_at="2026-09-17T12:15:00+00:00")],
            task_states=[self.idle(observed_at="2026-09-17T12:15:00+00:00")],
        )
        [proposal] = opened["wake_proposals"]
        [send] = [s for s in proposal["native_steps"] if s["step"] == "send"]
        self.assertIn("harmless probe", send["arguments"]["message"])
        self.assertIn("Rolecasting policy", send["arguments"]["message"])

    def test_reset_hint_field_is_optional_validated_and_never_echoed(self) -> None:
        self.register(gate=DAYBREAK_GATE)
        secret = "SYNTHETIC-RESET-SECRET-3c7e"
        state_path = Path(self.store) / "state.json"
        before = state_path.read_bytes()
        for label, value, code_name in (
            ("not a time", secret, "invalid-time"),
            ("no offset", "2026-09-17T14:00:00", "invalid-time"),
            ("wrong type", 1789653600, "invalid-time"),
        ):
            with self.subTest(label=label):
                code, payload, err = cycle(
                    self.store, T0,
                    observations=[self.daybreak_observation(capacity="exhausted", reset_at=value)],
                    task_states=[self.idle()],
                )
                self.assertEqual(code, 2)
                self.assertIsNone(payload)
                self.assertIn(f"aeon bell: {code_name}:", err)
                self.assertNotIn(secret, err)
                self.assertNotIn("Traceback", err)
                self.assertEqual(state_path.read_bytes(), before, "nothing was stored")
        # A quota observation never carries the field at the top level.
        quota_store = str(Path(self._tmp.name) / "quota-store")
        self.store = quota_store
        self.register()
        code, payload, err = cycle(
            self.store, T0,
            observations=[self.quota_observation(remaining=0, reset_at="2026-09-17T14:00:00+00:00")],
        )
        self.assertEqual(code, 0, err)
        stray = self.quota_observation(remaining=0)
        stray["reset_at"] = "2026-09-17T14:00:00+00:00"
        code, payload, err = cycle(self.store, "2026-09-17T12:01:00+00:00", observations=[stray])
        self.assertEqual(code, 2)
        self.assertIn("invalid-observation", err)
        # Null reads as absent, and a stored observation written before the
        # field existed (no reset_at in its evidence) still reads and plans the
        # unknown default.
        self.fresh_store()
        self.register(gate=DAYBREAK_GATE)
        code, result, err = cycle(
            self.store, T0,
            observations=[self.daybreak_observation(capacity="exhausted", reset_at=None)],
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(result["schedule"]["gates"][0]["basis"], "no-estimate")
        state_path = Path(self.store) / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        for observation in state["observations"].values():
            observation["evidence"].pop("reset_at")
        state_path.write_text(json.dumps(state), encoding="utf-8")
        code, inspected, err = run("inspect", "--store", self.store, "--now", T0)
        self.assertEqual(code, 0, err)
        self.assertNotIn("reset_at", inspected["observations"][0]["evidence"])
        self.assertEqual(inspected["schedule"]["gates"][0]["basis"], "no-estimate")
        self.assertEqual(inspected["schedule"]["next_check_at"], "2026-09-17T13:00:00+00:00")


class ObservationOrdering(CycleHelpers):
    """The successful-observation anchor is monotonic per gate key and binding.

    Normal ticks stamp the tick's clock, so only the documented import path
    and replayed input can present evidence older than what the store holds.
    Such evidence must never move the anchor backward, clear newer failure
    state, or admit a target from a superseded open observation.
    """

    def skip_entry(self, reason: str) -> dict[str, Any]:
        return {"gate_key": self.gate_key(), "accepted": False, "result": None, "reason": reason}

    def stored(self, now: str) -> list[dict[str, Any]]:
        _, inspected, _ = run("inspect", "--store", self.store, "--now", now)
        return inspected["observations"]

    def test_older_open_import_never_replaces_a_newer_closed_observation(self) -> None:
        self.register(extra=("--expires-in-minutes", "4320"))
        anchor = "2026-09-17T12:10:00+00:00"
        _, result, err = cycle(
            self.store, "2026-09-17T12:10:05+00:00",
            observations=[self.quota_observation(remaining=0, observed_at=anchor, reset_at="2026-09-17T14:00:00+00:00")],
        )
        self.assertIsNotNone(result, err)
        # 110 minutes to the reset: a quarter is 27, so 12:37.
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T12:37:00+00:00")
        fingerprint = result["schedule"]["registry"]["fingerprint"]
        # Another source saw the bucket open five minutes before that. Its
        # evidence is superseded: it is skipped with a fixed reason, stores
        # nothing, leaves the anchor and the planned query where they were,
        # and admits nothing.
        older = self.quota_observation(
            remaining=50, observed_at="2026-09-17T12:05:00+00:00", expires_at="2026-09-17T12:20:00+00:00"
        )
        at = "2026-09-17T12:11:00+00:00"
        code, result, err = cycle(self.store, at, observations=[older], task_states=[self.idle(observed_at=at)])
        self.assertEqual(code, 0, err)
        self.assertEqual(result["ingested_observations"], [self.skip_entry("observation-superseded")])
        self.assert_no_wake(result, "gate-closed")
        self.assertEqual(result["observation_requests"], [])
        [gate] = result["schedule"]["gates"]
        self.assertEqual((gate["observation"], gate["anchor"]), ("closed", anchor))
        self.assertEqual(gate["query_due_at"], "2026-09-17T12:37:00+00:00")
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T12:37:00+00:00")
        self.assertEqual(result["schedule"]["registry"]["fingerprint"], fingerprint)
        [stored] = self.stored(at)
        self.assertEqual((stored["result"], stored["observed_at"], stored["source"]), ("closed", anchor, "cycle"))
        # Newer evidence moves the anchor forward and admits as before.
        newer = "2026-09-17T12:12:00+00:00"
        _, result, _ = cycle(
            self.store, newer,
            observations=[self.quota_observation(remaining=50, observed_at=newer)],
            task_states=[self.idle(observed_at=newer)],
        )
        self.assertEqual(result["ingested_observations"][0]["result"], "open")
        self.assertEqual(len(result["wake_proposals"]), 1)
        self.assertEqual(result["wake_proposals"][0]["gate_observation"]["observed_at"], newer)

    def test_equal_time_evidence_preserves_the_current_observation(self) -> None:
        self.register(extra=("--expires-in-minutes", "4320"))
        anchor = "2026-09-17T12:10:00+00:00"
        _, result, _ = cycle(self.store, anchor, observations=[self.quota_observation(remaining=0, observed_at=anchor)])
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T13:10:00+00:00")
        fingerprint = result["schedule"]["registry"]["fingerprint"]
        # Contradictory evidence stamped at the same second carries no ordering:
        # the stored closed observation stands and the open one admits nothing.
        later = "2026-09-17T12:11:00+00:00"
        code, result, err = cycle(
            self.store, later,
            observations=[self.quota_observation(remaining=50, observed_at=anchor)],
            task_states=[self.idle(observed_at=later)],
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(result["ingested_observations"], [self.skip_entry("observation-not-newer")])
        self.assert_no_wake(result, "gate-closed")
        [gate] = result["schedule"]["gates"]
        self.assertEqual((gate["anchor"], gate["query_due_at"]), (anchor, "2026-09-17T13:10:00+00:00"))
        self.assertEqual(result["schedule"]["registry"]["fingerprint"], fingerprint)
        # An identical replay is a no-op with the same reason.
        code, result, err = cycle(
            self.store, later, observations=[self.quota_observation(remaining=0, observed_at=anchor)]
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(result["ingested_observations"], [self.skip_entry("observation-not-newer")])
        self.assertEqual(result["schedule"]["registry"]["fingerprint"], fingerprint)
        [stored] = self.stored(later)
        self.assertEqual((stored["result"], stored["observed_at"]), ("closed", anchor))
        self.assertEqual(stored["evidence"]["remaining_percent"], 0.0)

    def test_superseded_evidence_never_clears_newer_failure_state(self) -> None:
        self.register(extra=("--expires-in-minutes", "4320"))
        key = self.gate_key()
        anchor = "2026-09-17T12:10:00+00:00"
        cycle(self.store, anchor, observations=[self.quota_observation(remaining=0, observed_at=anchor)])

        def error_at(observed_at: str, now: str | None = None) -> dict[str, Any]:
            code, result, err = cycle(
                self.store, now or observed_at,
                observations=[{"gate_key": key, "status": "error", "observed_at": observed_at, "reason": "error:codex-timeout"}],
            )
            self.assertEqual(code, 0, err)
            return result

        def retry_schedule(now: str) -> dict[str, Any]:
            _, inspected, _ = run("inspect", "--store", self.store, "--now", now)
            return inspected["retry_schedule"].get(key)

        failed = "2026-09-17T12:20:00+00:00"
        result = error_at(failed)
        self.assertEqual(result["ingested_observations"][0]["result"], "error")
        first = retry_schedule(failed)
        self.assertEqual((first["failures"], first["next_due_at"]), (1, "2026-09-17T12:35:00+00:00"))
        # An open observation older than the failure is superseded: it neither
        # admits nor clears the backoff, and the closed anchor stands.
        at = "2026-09-17T12:21:00+00:00"
        code, result, err = cycle(
            self.store, at,
            observations=[self.quota_observation(remaining=50, observed_at="2026-09-17T12:15:00+00:00")],
            task_states=[self.idle(observed_at=at)],
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(result["ingested_observations"], [self.skip_entry("observation-superseded")])
        self.assert_no_wake(result, "gate-closed")
        self.assertEqual(retry_schedule(at), first)
        self.assertEqual(result["schedule"]["gates"][0]["backoff_until"], "2026-09-17T12:35:00+00:00")
        # An error older than the failure, or a replay of the same failure,
        # advances nothing.
        result = error_at("2026-09-17T12:12:00+00:00", now="2026-09-17T12:22:00+00:00")
        self.assertEqual(result["ingested_observations"], [self.skip_entry("observation-superseded")])
        result = error_at(failed, now="2026-09-17T12:23:00+00:00")
        self.assertEqual(result["ingested_observations"], [self.skip_entry("observation-not-newer")])
        self.assertEqual(retry_schedule("2026-09-17T12:23:00+00:00"), first)
        [stored] = self.stored("2026-09-17T12:23:00+00:00")
        self.assertEqual((stored["result"], stored["observed_at"]), ("closed", anchor))
        # Newer evidence still advances and still clears as before.
        result = error_at("2026-09-17T12:30:00+00:00")
        self.assertEqual(result["ingested_observations"][0]["result"], "error")
        second = retry_schedule("2026-09-17T12:30:00+00:00")
        self.assertEqual((second["failures"], second["next_due_at"]), (2, "2026-09-17T13:00:00+00:00"))
        recovered = "2026-09-17T12:31:00+00:00"
        _, result, _ = cycle(self.store, recovered, observations=[self.quota_observation(remaining=0, observed_at=recovered)])
        self.assertEqual(result["ingested_observations"][0]["result"], "closed")
        self.assertIsNone(retry_schedule(recovered))
        self.assertEqual(result["schedule"]["gates"][0]["anchor"], recovered)

    def test_binding_change_is_a_distinct_comparison_domain(self) -> None:
        rid = self.register(extra=("--expires-in-minutes", "4320"))["registration_id"]
        original_key = self.gate_key()
        anchor = "2026-09-17T12:10:00+00:00"
        cycle(self.store, anchor, observations=[self.quota_observation(remaining=0, observed_at=anchor)])
        common = ("--store", self.store, "--registration-id", rid, "--owner", "owner-a")
        revised = dict(QUOTA_GATE, policy_revision="policy-2")
        code, _, err = run("update", *common, "--gate-json", json.dumps(revised), "--now", "2026-09-17T12:11:00+00:00")
        self.assertEqual(code, 0, err)
        revised_key = self.gate_key()
        self.assertNotEqual(revised_key, original_key)
        # Under the revised key nothing is stored yet, so an observation older
        # than the original key's anchor is that key's first evidence: it is
        # accepted on its own terms (the existing invalidation rules) and admits.
        older = "2026-09-17T12:05:00+00:00"
        at = "2026-09-17T12:11:30+00:00"
        code, result, err = cycle(
            self.store, at,
            observations=[self.quota_observation(remaining=50, observed_at=older)],
            task_states=[self.idle(observed_at=at)],
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(result["ingested_observations"][0]["result"], "open")
        [proposal] = result["wake_proposals"]
        self.assertEqual(proposal["gate_key"], revised_key)
        code, _, err = self.report(proposal["attempt_id"], "not_sent", now="2026-09-17T12:12:00+00:00")
        self.assertEqual(code, 0, err)
        # Back on the original gate, its own anchor still stands and is reused,
        # and the same older open evidence is still superseded there.
        code, _, err = run("update", *common, "--gate-json", json.dumps(QUOTA_GATE), "--now", "2026-09-17T12:13:00+00:00")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.gate_key(), original_key)
        at = "2026-09-17T12:13:00+00:00"
        _, result, _ = cycle(self.store, at, task_states=[self.idle(observed_at=at)])
        self.assertEqual(result["observation_requests"], [])
        self.assert_no_wake(result, "gate-closed")
        self.assertEqual(result["schedule"]["gates"][0]["anchor"], anchor)
        at = "2026-09-17T12:13:30+00:00"
        code, result, err = cycle(
            self.store, at,
            observations=[self.quota_observation(remaining=50, observed_at=older)],
            task_states=[self.idle(observed_at=at)],
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(result["ingested_observations"], [self.skip_entry("observation-superseded")])
        self.assert_no_wake(result, "gate-closed")
        by_key = {o["gate_key"]: o for o in self.stored(at)}
        self.assertEqual(set(by_key), {original_key, revised_key})
        self.assertEqual((by_key[original_key]["result"], by_key[original_key]["observed_at"]), ("closed", anchor))
        self.assertEqual((by_key[revised_key]["result"], by_key[revised_key]["observed_at"]), ("open", older))


class NotificationNotice(CycleHelpers):
    """The engine owns durable notification selection; the monitor relays text."""

    def gate_entry(self, key: str, outcome: str, kind: str = "quota_recovery") -> dict:
        reason = {
            "observed": "typed-observation",
            "unhandled": "binding-labels-differ",
            "held": "held:policy-revision-mismatch",
            "error": "error:codex-timeout",
        }[outcome]
        return {"gate_key": key, "kind": kind, "outcome": outcome, "reason": reason}

    def notice(
        self, now: str, gates: list[dict] | None = None, report: Any = None
    ) -> tuple[int, Any, str]:
        argv = ["notice", "--store", self.store, "--now", now]
        if gates is not None or report is not None:
            payload = {"adapter": "praxis-aeon-bell-codex-status", "gates": gates}
            if report is not None:
                payload = report
            path = Path(self._tmp.name) / "tick-report.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            argv += ["--adapter-report", str(path)]
        return run(*argv)

    def acknowledge(self, notice_id: str, now: str) -> tuple[int, Any, str]:
        return run(
            "acknowledge", "--store", self.store, "--notice-id", notice_id, "--now", now
        )

    def test_unchanged_configuration_gap_is_reported_once_then_cleared_then_new_again(
        self,
    ) -> None:
        rid = self.register()["registration_id"]
        key = self.gate_key()
        # Tick 1: no binding owns the gate's labels, so the adapter left it unhandled.
        code, first, err = self.notice("2026-09-17T12:00:10+00:00", [self.gate_entry(key, "unhandled")])
        self.assertEqual(code, 0, err)
        self.assertTrue(first["report"])
        self.assertFalse(first["replayed"])
        [entry] = first["new"]
        self.assertEqual(entry["family"], "unhandled")
        self.assertEqual(entry["gate_key"], key)
        self.assertEqual(entry["kind"], "quota_recovery")
        self.assertEqual((entry["account"], entry["route"]), ("synthetic-account-a", "cli"))
        self.assertEqual(entry["registration_ids"], [rid])
        self.assertEqual(first["cleared"], [])
        self.assertEqual(first["events"], [])
        self.assertEqual(first["markers_now"], [f"unhandled:{key}"])
        for needle in ("unhandled", "quota_recovery", "synthetic-account-a", "cli", rid, "2026-09-17T12:00:10+00:00"):
            self.assertIn(needle, first["text"])
        code, acked, err = self.acknowledge(first["notice_id"], "2026-09-17T12:00:11+00:00")
        self.assertEqual(code, 0, err)
        self.assertTrue(acked["acknowledged"])
        self.assertEqual(acked["baseline"]["markers"], [f"unhandled:{key}"])
        # Tick 2: the adapter says the same thing again; the engine requests the
        # gate again and skips the registration again. None of that is news.
        code, second, err = self.notice("2026-09-17T12:15:10+00:00", [self.gate_entry(key, "unhandled")])
        self.assertEqual(code, 0, err)
        self.assertFalse(second["report"])
        self.assertIsNone(second["text"])
        self.assertIsNone(second["notice_id"])
        # Tick 3: a binding with those labels was passed and the gate was observed.
        code, third, err = self.notice("2026-09-17T12:30:10+00:00", [self.gate_entry(key, "observed")])
        self.assertEqual(code, 0, err)
        self.assertTrue(third["report"])
        self.assertEqual(third["new"], [])
        [cleared] = third["cleared"]
        self.assertEqual((cleared["family"], cleared["gate_key"]), ("unhandled", key))
        self.assertEqual(third["markers_now"], [])
        self.assertIn("cleared", third["text"])
        self.assertNotEqual(third["notice_id"], first["notice_id"])
        code, _, err = self.acknowledge(third["notice_id"], "2026-09-17T12:30:11+00:00")
        self.assertEqual(code, 0, err)
        # Tick 4: the binding was withdrawn; the same key is new again.
        code, fourth, err = self.notice("2026-09-17T12:45:10+00:00", [self.gate_entry(key, "unhandled")])
        self.assertEqual(code, 0, err)
        self.assertTrue(fourth["report"])
        self.assertEqual([n["gate_key"] for n in fourth["new"]], [key])
        self.assertNotIn(fourth["notice_id"], {first["notice_id"], third["notice_id"]})

    def test_abandoned_reservation_is_standing_work_until_reconciled_then_an_event(
        self,
    ) -> None:
        rid = self.register()["registration_id"]
        [proposal] = self.propose()  # the monitor process dies after reserving
        key = self.gate_key()
        code, first, err = self.notice("2026-09-17T12:15:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertTrue(first["report"])
        [entry] = first["new"]
        self.assertEqual(entry["family"], "attention")
        self.assertEqual((entry["registration_id"], entry["status"]), (rid, "reserved"))
        self.assertEqual(entry["since"], T0)
        self.assertEqual(entry["attempt_id"], proposal["attempt_id"])
        self.assertIn("reconcile", entry["next_action"])
        self.assertIn("evidence", entry["next_action"])
        self.assertEqual(first["events"], [])
        for needle in ("reserved", rid, proposal["attempt_id"], "reconcile", "evidence"):
            self.assertIn(needle, first["text"])
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T12:15:11+00:00")
        self.assertEqual(code, 0, err)
        code, second, err = self.notice("2026-09-17T12:30:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertFalse(second["report"], "unchanged stuck work is not news")
        # The restarted monitor checks the target transcript and reconciles.
        code, reconciled, err = run(
            "reconcile", "--store", self.store, "--attempt-id", proposal["attempt_id"],
            "--resolution", "not_sent", "--evidence-json",
            json.dumps({"target_transcript_shows_message": False}),
            "--now", "2026-09-17T12:31:00+00:00",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(reconciled["registration"]["status"], "waiting")
        code, third, err = self.notice(
            "2026-09-17T12:45:10+00:00", [self.gate_entry(key, "observed")]
        )
        self.assertEqual(code, 0, err)
        self.assertTrue(third["report"])
        [event] = third["events"]
        self.assertEqual(event["attempt_id"], proposal["attempt_id"])
        self.assertEqual(event["status"], "reconciled_not_sent")
        self.assertEqual(event["delivery_claim"], "not_sent")
        self.assertEqual(event["resolved_at"], "2026-09-17T12:31:00+00:00")
        self.assertEqual(third["new"], [])
        self.assertEqual(third["cleared"], [], "an attention marker leaves silently")
        self.assertEqual(third["markers_now"], [])
        self.assertIn("reconciled_not_sent", third["text"])

    def test_detached_reservation_is_standing_work_with_evidence_based_recovery_guidance(
        self,
    ) -> None:
        rid = self.register()["registration_id"]
        [proposal] = self.propose()
        run(
            "remove", "--store", self.store, "--registration-id", rid, "--owner",
            "owner-a", "--now", "2026-09-17T12:05:00+00:00",
        )
        code, first, err = self.notice("2026-09-17T12:15:10+00:00")
        self.assertEqual(code, 0, err)
        [entry] = first["new"]
        self.assertEqual((entry["status"], entry["since"]), ("detached", "2026-09-17T12:05:00+00:00"))
        self.assertIn("reconcile", entry["next_action"])
        self.assertIn("evidence", entry["next_action"])
        self.assertIn("detached", first["text"])
        self.assertIn("reconcile", first["text"])
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T12:15:11+00:00")
        self.assertEqual(code, 0, err)
        code, reconciled, err = run(
            "reconcile", "--store", self.store, "--attempt-id", proposal["attempt_id"],
            "--resolution", "not_sent", "--evidence-json",
            json.dumps({"target_transcript_shows_message": False}),
            "--now", "2026-09-17T12:20:00+00:00",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(reconciled["registration"]["status"], "removed")
        code, second, err = self.notice("2026-09-17T12:30:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertEqual([e["status"] for e in second["events"]], ["reconciled_not_sent"])
        self.assertEqual(second["new"], [])
        self.assertEqual(second["markers_now"], [])

    def test_wake_in_one_tick_reports_the_event_alone_then_quiet(self) -> None:
        self.register()
        [proposal] = self.propose()
        key = self.gate_key()
        code, _, err = self.report(
            proposal["attempt_id"], "accepted", now="2026-09-17T12:00:30+00:00",
            tool_response="follow-up queued",
        )
        self.assertEqual(code, 0, err)
        code, first, err = self.notice(
            "2026-09-17T12:00:40+00:00", [self.gate_entry(key, "observed")]
        )
        self.assertEqual(code, 0, err)
        self.assertTrue(first["report"])
        [event] = first["events"]
        self.assertEqual(event["attempt_id"], proposal["attempt_id"])
        self.assertEqual(event["status"], "accepted")
        self.assertEqual(event["delivery_claim"], "accepted_by_native_send_tool")
        self.assertEqual(event["resolved_at"], "2026-09-17T12:00:30+00:00")
        self.assertEqual((first["new"], first["cleared"], first["markers_now"]), ([], [], []))
        self.assertIn("accepted_by_native_send_tool", first["text"])
        self.assertIn(proposal["attempt_id"], first["text"])
        self.assertNotIn("delivered", first["text"])
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T12:00:41+00:00")
        self.assertEqual(code, 0, err)
        code, second, err = self.notice("2026-09-17T12:15:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertFalse(second["report"], "a completed registration is not attention")

    def test_events_resolved_at_the_same_time_are_each_reported_once(self) -> None:
        self.register(task_id="task-1")
        self.register(task_id="task-2")
        proposals = self.propose(task_ids=("task-1", "task-2"))
        key = self.gate_key()
        for proposal in proposals:
            code, _, err = self.report(
                proposal["attempt_id"], "accepted", now="2026-09-17T12:00:30+00:00"
            )
            self.assertEqual(code, 0, err)
        code, first, err = self.notice(
            "2026-09-17T12:00:40+00:00", [self.gate_entry(key, "observed")]
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(
            {e["attempt_id"] for e in first["events"]},
            {p["attempt_id"] for p in proposals},
        )
        self.assertEqual({e["resolved_at"] for e in first["events"]}, {"2026-09-17T12:00:30+00:00"})
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T12:00:41+00:00")
        self.assertEqual(code, 0, err)
        code, second, err = self.notice("2026-09-17T12:15:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertFalse(second["report"])

    def test_events_survive_context_loss_and_a_long_delayed_restart(self) -> None:
        self.register()
        [proposal] = self.propose()
        code, _, err = self.report(
            proposal["attempt_id"], "unknown", now="2026-09-17T12:00:30+00:00",
            tool_response="timeout",
        )
        self.assertEqual(code, 0, err)
        # The monitor task is lost before it can run notice; days later a new
        # monitor task on the same store still learns of the resolution.
        code, first, err = self.notice("2026-09-20T15:00:00+00:00")
        self.assertEqual(code, 0, err)
        self.assertTrue(first["report"])
        [event] = first["events"]
        self.assertEqual((event["attempt_id"], event["status"]), (proposal["attempt_id"], "unknown"))
        self.assertEqual(event["delivery_claim"], "unknown_requires_reconciliation")
        self.assertIn("reconcile", event["next_action"])
        [entry] = first["new"]
        self.assertEqual((entry["status"], entry["unresolved_reason"]), ("unresolved", "delivery-unknown"))
        self.assertIn("2026-09-20T15:00:00+00:00", first["text"])
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-20T15:00:01+00:00")
        self.assertEqual(code, 0, err)
        code, second, err = self.notice("2026-09-20T15:15:00+00:00")
        self.assertEqual(code, 0, err)
        self.assertFalse(second["report"])

    def test_pending_notice_is_replayed_verbatim_until_acknowledged(self) -> None:
        self.register()
        key = self.gate_key()
        code, first, err = self.notice(
            "2026-09-17T12:00:10+00:00", [self.gate_entry(key, "unhandled")]
        )
        self.assertEqual(code, 0, err)
        self.assertTrue(first["report"])
        # The monitor relayed the text (or not) and crashed before acknowledging.
        # The next tick sees a different world, yet gets the identical notice.
        code, replay, err = self.notice(
            "2026-09-17T12:15:10+00:00", [self.gate_entry(key, "observed")]
        )
        self.assertEqual(code, 0, err)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["notice_id"], first["notice_id"])
        self.assertEqual(replay["text"], first["text"])
        self.assertEqual(replay["computed_at"], "2026-09-17T12:00:10+00:00")
        self.assertEqual(replay["new"], first["new"])
        code, _, err = self.acknowledge(replay["notice_id"], "2026-09-17T12:15:11+00:00")
        self.assertEqual(code, 0, err)
        # Only after acknowledgement does the current state get compared.
        code, third, err = self.notice(
            "2026-09-17T12:15:12+00:00", [self.gate_entry(key, "observed")]
        )
        self.assertEqual(code, 0, err)
        self.assertFalse(third["replayed"])
        self.assertEqual([c["gate_key"] for c in third["cleared"]], [key])
        code, _, err = self.acknowledge(third["notice_id"], "2026-09-17T12:15:13+00:00")
        self.assertEqual(code, 0, err)
        code, fourth, err = self.notice(
            "2026-09-17T12:30:10+00:00", [self.gate_entry(key, "observed")]
        )
        self.assertEqual(code, 0, err)
        self.assertFalse(fourth["report"])

    def test_registry_mutation_while_a_notice_is_pending_does_not_alter_it(self) -> None:
        rid = self.register()["registration_id"]
        [proposal] = self.propose()
        key = self.gate_key()
        code, first, err = self.notice("2026-09-17T12:15:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertEqual([n["status"] for n in first["new"]], ["reserved"])
        code, _, err = run(
            "rearm", "--store", self.store, "--registration-id", rid, "--owner",
            "owner-a", "--episode", "episode-2", "--now", "2026-09-17T12:16:00+00:00",
        )
        self.assertEqual(code, 0, err)
        code, replay, err = self.notice("2026-09-17T12:16:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertTrue(replay["replayed"])
        self.assertEqual((replay["notice_id"], replay["text"]), (first["notice_id"], first["text"]))
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T12:16:11+00:00")
        self.assertEqual(code, 0, err)
        # The reserved marker left when the owner rearmed; a superseded attempt
        # is the owner's own action, not an event.
        code, after, err = self.notice(
            "2026-09-17T12:16:20+00:00", [self.gate_entry(key, "observed")]
        )
        self.assertEqual(code, 0, err)
        self.assertFalse(after["report"])
        self.assertEqual(after["markers_now"], [])
        self.assertNotIn(proposal["attempt_id"], json.dumps(after["events"]))

    def test_stale_or_wrong_acknowledgement_is_refused_without_moving_the_baseline(
        self,
    ) -> None:
        self.register()
        key = self.gate_key()
        code, first, err = self.notice(
            "2026-09-17T12:00:10+00:00", [self.gate_entry(key, "unhandled")]
        )
        self.assertEqual(code, 0, err)
        code, payload, err = self.acknowledge("0" * 24, "2026-09-17T12:00:11+00:00")
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("unknown-notice", err)
        code, acked, err = self.acknowledge(first["notice_id"], "2026-09-17T12:00:12+00:00")
        self.assertEqual(code, 0, err)
        self.assertEqual(acked["baseline"]["sequence"], 1)
        # Acknowledging the same notice again is explicit and changes nothing.
        code, again, err = self.acknowledge(first["notice_id"], "2026-09-17T12:00:13+00:00")
        self.assertEqual(code, 0, err)
        self.assertFalse(again["acknowledged"])
        self.assertEqual(again["result"], "already-acknowledged")
        self.assertEqual(again["baseline"]["sequence"], 1)
        self.assertEqual(again["baseline"]["acknowledged_at"], "2026-09-17T12:00:12+00:00")
        # A quiet notice leaves nothing to acknowledge.
        code, quiet, err = self.notice(
            "2026-09-17T12:15:10+00:00", [self.gate_entry(key, "unhandled")]
        )
        self.assertEqual(code, 0, err)
        self.assertFalse(quiet["report"])
        code, _, err = self.acknowledge("f" * 24, "2026-09-17T12:15:11+00:00")
        self.assertEqual(code, 2)
        self.assertIn("unknown-notice", err)
        # A stale id never consumes a newer pending notice.
        code, second, err = self.notice(
            "2026-09-17T12:30:10+00:00", [self.gate_entry(key, "observed")]
        )
        self.assertEqual(code, 0, err)
        self.assertTrue(second["report"])
        code, stale, err = self.acknowledge(first["notice_id"], "2026-09-17T12:30:11+00:00")
        self.assertEqual(code, 0, err)
        self.assertEqual(stale["result"], "already-acknowledged")
        self.assertEqual(stale["pending_notice_id"], second["notice_id"])
        code, replay, err = self.notice("2026-09-17T12:30:12+00:00")
        self.assertEqual(code, 0, err)
        self.assertEqual((replay["replayed"], replay["notice_id"]), (True, second["notice_id"]))

    def test_held_and_error_results_are_standing_markers_not_repeated_events(
        self,
    ) -> None:
        self.register(extra=("--expires-in-minutes", str(7 * 24 * 60)))
        key = self.gate_key()

        def fail(now: str, reason: str) -> None:
            code, _, err = cycle(
                self.store, now,
                observations=[{"gate_key": key, "status": "error", "observed_at": now, "reason": reason}],
            )
            self.assertEqual(code, 0, err)

        fail(T0, "held:policy-revision-mismatch")
        code, first, err = self.notice("2026-09-17T12:00:10+00:00", [self.gate_entry(key, "held")])
        self.assertEqual(code, 0, err)
        [entry] = first["new"]
        self.assertEqual((entry["family"], entry["gate_key"]), ("failing", key))
        self.assertEqual(entry["reason"], "held:policy-revision-mismatch")
        self.assertEqual(entry["failures"], 1)
        self.assertEqual(entry["next_due_at"], "2026-09-17T12:15:00+00:00")
        self.assertIn("re-register", entry["next_action"])
        self.assertEqual(first["events"], [])
        self.assertIn("held:policy-revision-mismatch", first["text"])
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T12:00:11+00:00")
        self.assertEqual(code, 0, err)
        # Inside the backoff window the gate is not queried at all.
        code, backoff, err = self.notice("2026-09-17T12:10:00+00:00", [])
        self.assertEqual(code, 0, err)
        self.assertFalse(backoff["report"])
        # The requery holds for the same reason: the counter moved, the cause did not.
        fail("2026-09-17T12:15:00+00:00", "held:policy-revision-mismatch")
        code, same, err = self.notice("2026-09-17T12:15:10+00:00", [self.gate_entry(key, "held")])
        self.assertEqual(code, 0, err)
        self.assertFalse(same["report"])
        self.assertEqual(same["markers_now"], [f"failing:{key}:held:policy-revision-mismatch"])
        # A different cause is a new marker; the old one is reported cleared.
        fail("2026-09-17T12:45:00+00:00", "error:codex-timeout")
        code, changed, err = self.notice("2026-09-17T12:45:10+00:00", [self.gate_entry(key, "error")])
        self.assertEqual(code, 0, err)
        self.assertEqual([n["reason"] for n in changed["new"]], ["error:codex-timeout"])
        self.assertIn("backoff", changed["new"][0]["next_action"])
        self.assertEqual([c["reason"] for c in changed["cleared"]], ["held:policy-revision-mismatch"])
        code, _, err = self.acknowledge(changed["notice_id"], "2026-09-17T12:45:11+00:00")
        self.assertEqual(code, 0, err)
        # A successful observation clears the schedule, and the marker with it.
        at = "2026-09-17T14:45:00+00:00"
        code, _, err = cycle(
            self.store, at, observations=[self.quota_observation(remaining=0, observed_at=at)]
        )
        self.assertEqual(code, 0, err)
        code, cleared, err = self.notice("2026-09-17T14:45:10+00:00", [self.gate_entry(key, "observed")])
        self.assertEqual(code, 0, err)
        self.assertEqual([c["marker"] for c in cleared["cleared"]], [f"failing:{key}:error:codex-timeout"])
        self.assertEqual(cleared["markers_now"], [])

    def test_gap_knowledge_is_retained_when_the_gate_was_not_queried(self) -> None:
        self.register(task_id="task-1")
        other = self.register(task_id="task-2", gate=dict(QUOTA_GATE, bucket="daily"))
        key = self.gate_key()
        other_key = other["gate_key"]
        code, first, err = self.notice(
            "2026-09-17T12:00:10+00:00",
            [self.gate_entry(key, "unhandled"), self.gate_entry(other_key, "observed")],
        )
        self.assertEqual(code, 0, err)
        self.assertEqual([n["gate_key"] for n in first["new"]], [key])
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T12:00:11+00:00")
        self.assertEqual(code, 0, err)
        # A tick where observe never ran: no adapter report, nothing cleared.
        code, absent, err = self.notice("2026-09-17T12:15:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertFalse(absent["report"])
        self.assertEqual(absent["markers_now"], [f"unhandled:{key}"])
        self.assertEqual(absent["coverage"], {"adapter_report": False, "queried": [], "retained": [key]})
        # A tick where observe ran but this gate was not in the query set (fresh
        # cache or backoff): the other gate's result says nothing about it.
        code, unqueried, err = self.notice(
            "2026-09-17T12:30:10+00:00", [self.gate_entry(other_key, "observed")]
        )
        self.assertEqual(code, 0, err)
        self.assertFalse(unqueried["report"])
        self.assertEqual(unqueried["coverage"]["queried"], [other_key])
        self.assertEqual(unqueried["coverage"]["retained"], [key])
        # A covered observation of the gate itself clears the gap.
        code, cleared, err = self.notice(
            "2026-09-17T12:45:10+00:00", [self.gate_entry(key, "observed")]
        )
        self.assertEqual(code, 0, err)
        self.assertEqual([c["gate_key"] for c in cleared["cleared"]], [key])
        self.assertEqual(cleared["coverage"]["retained"], [])

    def test_empty_registry_is_quiet_and_clears_a_remembered_gap_once(self) -> None:
        code, empty, err = self.notice("2026-09-17T12:00:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertFalse(empty["report"])
        self.assertEqual(empty["markers_now"], [])
        rid = self.register()["registration_id"]
        key = self.gate_key()
        code, first, err = self.notice(
            "2026-09-17T12:15:10+00:00", [self.gate_entry(key, "unhandled")]
        )
        self.assertEqual(code, 0, err)
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T12:15:11+00:00")
        self.assertEqual(code, 0, err)
        # A pause, like a removal, means nothing waits on the gate any more.
        code, _, err = run(
            "pause", "--store", self.store, "--registration-id", rid, "--owner",
            "owner-a", "--now", "2026-09-17T12:20:00+00:00",
        )
        self.assertEqual(code, 0, err)
        code, cleared, err = self.notice("2026-09-17T12:30:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertTrue(cleared["report"])
        [entry] = cleared["cleared"]
        self.assertEqual((entry["gate_key"], entry["registration_ids"]), (key, []))
        self.assertEqual(cleared["markers_now"], [])
        code, _, err = self.acknowledge(cleared["notice_id"], "2026-09-17T12:30:11+00:00")
        self.assertEqual(code, 0, err)
        code, _, err = run(
            "remove", "--store", self.store, "--registration-id", rid, "--owner",
            "owner-a", "--now", "2026-09-17T12:35:00+00:00",
        )
        self.assertEqual(code, 0, err)
        code, quiet, err = self.notice("2026-09-17T12:45:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertFalse(quiet["report"])

    def test_expiry_is_reported_once_across_inspect_and_cycle(self) -> None:
        rid = self.register(extra=("--expires-in-minutes", "30"))["registration_id"]
        code, first, err = self.notice("2026-09-17T12:45:00+00:00")
        self.assertEqual(code, 0, err)
        [entry] = first["new"]
        self.assertEqual((entry["registration_id"], entry["status"]), (rid, "expired"))
        self.assertEqual(entry["since"], "2026-09-17T12:30:00+00:00")
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T12:45:01+00:00")
        self.assertEqual(code, 0, err)
        code, _, err = cycle(self.store, "2026-09-17T12:45:07+00:00")
        self.assertEqual(code, 0, err)
        code, second, err = self.notice("2026-09-17T12:45:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertFalse(second["report"])
        self.assertEqual(second["markers_now"], first["markers_now"])

    def test_malformed_adapter_report_is_refused_without_corrupting_state(self) -> None:
        self.register()
        key = self.gate_key()
        secret = "SYNTHETIC-SECRET-VALUE-4b2d"
        good = self.gate_entry(key, "unhandled")
        for label, report in (
            ("not an object", [good]),
            ("gates not a list", {"gates": "x"}),
            ("missing fields", {"gates": [{"gate_key": key}]}),
            ("extra field", {"gates": [dict(good, token=secret)]}),
            ("bad key", {"gates": [dict(good, gate_key=secret)]}),
            ("bad outcome", {"gates": [dict(good, outcome=secret)]}),
            ("duplicate key", {"gates": [good, good]}),
        ):
            with self.subTest(label=label):
                code, payload, err = self.notice("2026-09-17T12:00:10+00:00", report=report)
                self.assertEqual(code, 2)
                self.assertIsNone(payload)
                self.assertIn("invalid-adapter-report", err)
                self.assertNotIn(secret, err)
        code, _, err = run(
            "notice", "--store", self.store, "--now", "2026-09-17T12:00:10+00:00",
            "--adapter-report", str(Path(self._tmp.name) / "missing.json"),
        )
        self.assertEqual(code, 2)
        self.assertIn("invalid-adapter-report", err)
        # The artifact an observe exit 2 leaves behind: its redirected stdout is a
        # zero-byte file, which is not a report and must not read as one.
        state_path = Path(self.store) / "state.json"
        before = state_path.read_bytes()
        empty = Path(self._tmp.name) / "empty-report.json"
        empty.write_bytes(b"")
        code, payload, err = run(
            "notice", "--store", self.store, "--now", "2026-09-17T12:00:10+00:00",
            "--adapter-report", str(empty),
        )
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("invalid-adapter-report", err)
        self.assertEqual(state_path.read_bytes(), before)
        # Nothing was selected or stored: there is no pending notice to acknowledge.
        code, _, err = self.acknowledge("a" * 24, "2026-09-17T12:00:11+00:00")
        self.assertEqual(code, 2)
        self.assertIn("unknown-notice", err)
        code, first, err = self.notice("2026-09-17T12:00:12+00:00", [good])
        self.assertEqual(code, 0, err)
        self.assertEqual(first["sequence"], 0)
        self.assertTrue(first["report"])

    def test_notice_text_names_labels_ids_and_codes_but_no_target_or_observation_values(
        self,
    ) -> None:
        secrets_ = {
            "host": "host-secret-9",
            "task": "task-secret-7",
            "episode": "episode-secret-3",
            "continuation": "CONTINUATION-SECRET-TEXT",
            "tool": "TOOL-RESPONSE-SECRET",
        }
        rid = self.register(
            host=secrets_["host"], task_id=secrets_["task"], episode=secrets_["episode"],
            continuation=secrets_["continuation"],
        )["registration_id"]
        key = self.gate_key()
        _, result, err = cycle(
            self.store, T0,
            observations=[self.quota_observation(remaining=37.5)],
            task_states=[{"host": secrets_["host"], "task_id": secrets_["task"], "status": "idle", "observed_at": T0}],
        )
        [proposal] = result["wake_proposals"]
        code, _, err = self.report(
            proposal["attempt_id"], "unknown", now="2026-09-17T12:00:30+00:00",
            tool_response=secrets_["tool"],
        )
        self.assertEqual(code, 0, err)
        other = self.register(task_id="task-2", gate=dict(QUOTA_GATE, bucket="daily"))
        code, first, err = self.notice(
            "2026-09-17T12:00:40+00:00", [self.gate_entry(other["gate_key"], "unhandled")]
        )
        self.assertEqual(code, 0, err)
        text = first["text"]
        for needle in (
            "quota_recovery", "synthetic-account-a", "cli", rid, other["registration_id"],
            proposal["attempt_id"], "unknown_requires_reconciliation", "delivery-unknown",
            "reconcile", other["gate_key"],
        ):
            self.assertIn(needle, text)
        for value in (*secrets_.values(), "37.5", "remaining"):
            self.assertNotIn(value, text)
            self.assertNotIn(value, json.dumps(first), "nor anywhere in the notice")

    def test_legacy_store_without_notification_state_reports_history_once(self) -> None:
        # A store written before notification state existed: attempts resolved,
        # nothing ever acknowledged. The first notice reports that history once
        # rather than seeding it away; inspect never shows notification state.
        rid = self.register()["registration_id"]
        [proposal] = self.propose()
        code, _, err = self.report(proposal["attempt_id"], "accepted", now="2026-09-17T12:00:30+00:00")
        self.assertEqual(code, 0, err)
        _, inspected, _ = run("inspect", "--store", self.store, "--now", "2026-09-17T14:00:00+00:00")
        self.assertNotIn("notification", inspected)
        code, first, err = self.notice("2026-09-17T14:00:00+00:00")
        self.assertEqual(code, 0, err)
        self.assertEqual(first["sequence"], 0)
        self.assertIsNone(first["acknowledged_at"])
        self.assertEqual([e["status"] for e in first["events"]], ["accepted"])
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T14:00:01+00:00")
        self.assertEqual(code, 0, err)
        # Ordinary commands preserve the acknowledged state.
        code, _, err = run(
            "rearm", "--store", self.store, "--registration-id", rid, "--owner",
            "owner-a", "--episode", "episode-2", "--now", "2026-09-17T14:05:00+00:00",
        )
        self.assertEqual(code, 0, err)
        _, inspected, _ = run("inspect", "--store", self.store, "--now", "2026-09-17T14:05:00+00:00")
        self.assertNotIn("notification", inspected)
        code, second, err = self.notice("2026-09-17T14:15:00+00:00", [self.gate_entry(self.gate_key(), "observed")])
        self.assertEqual(code, 0, err)
        self.assertFalse(second["report"])
        self.assertEqual(second["sequence"], 1)
        # Malformed notification state is refused by notice and acknowledge only;
        # the registry stays readable and untouched.
        state_path = Path(self.store) / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["notification"] = {"baseline": "bogus"}
        state_path.write_text(json.dumps(state), encoding="utf-8")
        code, payload, err = self.notice("2026-09-17T14:30:00+00:00")
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("corrupt-store", err)
        code, _, err = self.acknowledge("b" * 24, "2026-09-17T14:30:00+00:00")
        self.assertEqual(code, 2)
        self.assertIn("corrupt-store", err)
        code, inspected, err = run("inspect", "--store", self.store, "--now", "2026-09-17T14:30:00+00:00")
        self.assertEqual(code, 0, err)
        self.assertEqual(inspected["registrations"][0]["episode"], "episode-2")

    def owner(self, command: str, rid: str, now: str, *extra: str) -> dict:
        code, payload, err = run(
            command, "--store", self.store, "--registration-id", rid, "--owner",
            "owner-a", *extra, "--now", now,
        )
        self.assertEqual(code, 0, err)
        return payload

    def test_expiry_renewal_while_reserved_keeps_the_same_stuck_work(self) -> None:
        rid = self.register()["registration_id"]
        [proposal] = self.propose()  # reserved at T0; the monitor died before reporting
        code, first, err = self.notice("2026-09-17T12:15:10+00:00")
        self.assertEqual(code, 0, err)
        [entry] = first["new"]
        self.assertEqual((entry["status"], entry["since"]), ("reserved", T0))
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T12:15:11+00:00")
        self.assertEqual(code, 0, err)
        # The one owner edit allowed while reserved: renew the expiry.
        updated = self.owner(
            "update", rid, "2026-09-17T12:20:00+00:00", "--expires-in-minutes", "600"
        )
        self.assertEqual((updated["status"], updated["attempt_id"]), ("reserved", proposal["attempt_id"]))
        code, second, err = self.notice("2026-09-17T12:30:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertFalse(second["report"], "the same reservation is not news")
        self.assertEqual(second["markers_now"], first["markers_now"])
        _, inspected, _ = run("inspect", "--store", self.store, "--now", "2026-09-17T12:30:10+00:00")
        [entry] = inspected["attention"]
        self.assertEqual((entry["status"], entry["since"]), ("reserved", T0))

    def test_owner_edits_of_an_unresolved_registration_keep_the_same_stuck_work(self) -> None:
        rid = self.register()["registration_id"]
        [proposal] = self.propose()
        code, _, err = self.report(
            proposal["attempt_id"], "unknown", now="2026-09-17T12:00:30+00:00", tool_response="timeout"
        )
        self.assertEqual(code, 0, err)
        code, first, err = self.notice("2026-09-17T12:15:10+00:00")
        self.assertEqual(code, 0, err)
        [entry] = first["new"]
        self.assertEqual(
            (entry["status"], entry["unresolved_reason"], entry["since"]),
            ("unresolved", "delivery-unknown", "2026-09-17T12:00:30+00:00"),
        )
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T12:15:11+00:00")
        self.assertEqual(code, 0, err)
        # Continuation and expiry edits are allowed while unresolved; neither is a transition.
        updated = self.owner(
            "update", rid, "2026-09-17T12:20:00+00:00",
            "--continuation", "Revised continuation.", "--expires-in-minutes", "2880",
        )
        self.assertEqual(updated["status"], "unresolved")
        code, second, err = self.notice("2026-09-17T12:30:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertFalse(second["report"], "the same unresolved attempt is not news")
        self.assertEqual(second["markers_now"], first["markers_now"])
        _, inspected, _ = run("inspect", "--store", self.store, "--now", "2026-09-17T12:30:10+00:00")
        [entry] = inspected["attention"]
        self.assertEqual((entry["status"], entry["since"]), ("unresolved", "2026-09-17T12:00:30+00:00"))

    def test_settling_an_unresolved_attempt_leaves_no_stale_unresolved_reason(self) -> None:
        # unresolved_reason belongs to the unresolved state: a registration that
        # reconcile moves back to waiting or on to completed describes its current
        # state, and a later expiry of that wait relays no reason from the past.
        waiting = self.register(task_id="task-1", extra=("--expires-in-minutes", "60"))["registration_id"]
        completed = self.register(task_id="task-2")["registration_id"]
        limited = self.register(task_id="task-3")["registration_id"]
        proposals = {p["task_id"]: p for p in self.propose(task_ids=("task-1", "task-2", "task-3"))}
        for task_id in ("task-1", "task-2"):
            code, reported, err = self.report(
                proposals[task_id]["attempt_id"], "unknown", now="2026-09-17T12:00:30+00:00", tool_response="timeout"
            )
            self.assertEqual(code, 0, err)
            self.assertEqual(
                (reported["registration"]["status"], reported["registration"]["unresolved_reason"]),
                ("unresolved", "delivery-unknown"),
            )
        code, _, err = self.report(proposals["task-3"]["attempt_id"], "not_sent", now="2026-09-17T12:00:30+00:00")
        self.assertEqual(code, 0, err)

        def reconcile(attempt_id: str, resolution: str, now: str):
            return run(
                "reconcile", "--store", self.store, "--attempt-id", attempt_id, "--resolution", resolution,
                "--evidence-json", json.dumps({"target_transcript_shows_message": resolution == "accepted"}),
                "--now", now,
            )

        code, settled, err = reconcile(proposals["task-1"]["attempt_id"], "not_sent", "2026-09-17T12:05:00+00:00")
        self.assertEqual(code, 0, err)
        registration = settled["registration"]
        self.assertEqual(
            (registration["status"], registration["unresolved_reason"], registration["attempt_id"]),
            ("waiting", None, None),
        )
        code, settled, err = reconcile(proposals["task-2"]["attempt_id"], "accepted", "2026-09-17T12:05:00+00:00")
        self.assertEqual(code, 0, err)
        self.assertEqual(
            (settled["registration"]["status"], settled["registration"]["unresolved_reason"]), ("completed", None)
        )
        _, inspected, _ = run("inspect", "--store", self.store, "--now", "2026-09-17T12:10:00+00:00")
        by_id = {r["registration_id"]: r for r in inspected["registrations"]}
        self.assertEqual((by_id[waiting]["status"], by_id[waiting]["unresolved_reason"]), ("waiting", None))
        self.assertEqual((by_id[completed]["status"], by_id[completed]["unresolved_reason"]), ("completed", None))
        self.assertEqual(inspected["attention"], [])
        # A third not_sent settled through reconcile from delivery-unknown is a new
        # unresolved state with its own reason, and remove leaves none behind.
        for minute, outcome in ((15, "not_sent"), (30, "unknown")):
            now = f"2026-09-17T12:{minute}:00+00:00"
            [proposal] = self.propose(now=now, task_ids=("task-3",))
            code, _, err = self.report(proposal["attempt_id"], outcome, now=now, tool_response="x")
            self.assertEqual(code, 0, err)
        code, settled, err = reconcile(proposal["attempt_id"], "not_sent", "2026-09-17T12:31:00+00:00")
        self.assertEqual(code, 0, err)
        self.assertEqual(
            (settled["registration"]["status"], settled["registration"]["unresolved_reason"]),
            ("unresolved", "attempt-limit"),
        )
        removed = self.owner("remove", limited, "2026-09-17T12:32:00+00:00")
        self.assertEqual((removed["status"], removed["unresolved_reason"]), ("removed", None))
        # The reconciled wait expires: the expired entry and its relayed line name no reason.
        late = "2026-09-17T13:15:00+00:00"
        _, inspected, _ = run("inspect", "--store", self.store, "--now", late)
        [entry] = inspected["attention"]
        self.assertEqual(
            (entry["registration_id"], entry["status"], entry["unresolved_reason"], entry["attempt_id"]),
            (waiting, "expired", None, None),
        )
        code, notice, err = self.notice(late)
        self.assertEqual(code, 0, err)
        [body] = [b for b in notice["new"] if b["family"] == "attention"]
        self.assertEqual((body["status"], body["unresolved_reason"]), ("expired", None))
        [line] = [l for l in notice["text"].splitlines() if l.startswith("new: registration")]
        self.assertIn(f"registration {waiting} expired since 2026-09-17T13:00:00+00:00", line)
        self.assertIn("attempt none; reason none;", line)
        self.assertNotIn("delivery-unknown", line)

    def test_gate_edit_of_an_attempt_limited_registration_keeps_the_same_stuck_work(
        self,
    ) -> None:
        rid = self.register()["registration_id"]
        for minute in (0, 15, 30):
            now = f"2026-09-17T12:{minute:02d}:00+00:00"
            [proposal] = self.propose(now=now)
            code, _, err = self.report(proposal["attempt_id"], "not_sent", now=now)
            self.assertEqual(code, 0, err)
        code, first, err = self.notice("2026-09-17T12:45:10+00:00")
        self.assertEqual(code, 0, err)
        [entry] = first["new"]
        self.assertEqual(
            (entry["status"], entry["unresolved_reason"], entry["since"]),
            ("unresolved", "attempt-limit", "2026-09-17T12:30:00+00:00"),
        )
        self.assertEqual([e["status"] for e in first["events"]], ["not_sent"] * 3)
        for event in first["events"]:
            self.assertIn("attempt limit", event["next_action"])
            self.assertNotIn("waits again", event["next_action"])
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T12:45:11+00:00")
        self.assertEqual(code, 0, err)
        updated = self.owner(
            "update", rid, "2026-09-17T12:50:00+00:00",
            "--gate-json", json.dumps(dict(QUOTA_GATE, policy_revision="policy-2")),
        )
        self.assertEqual(updated["status"], "unresolved")
        code, second, err = self.notice("2026-09-17T13:00:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertFalse(second["report"], "a gate edit is not a state transition")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", "2026-09-17T13:00:10+00:00")
        [entry] = inspected["attention"]
        self.assertEqual(entry["since"], "2026-09-17T12:30:00+00:00")

    def test_not_sent_event_next_action_follows_the_registration_current_state(self) -> None:
        # Removed while reserved: the holder reports not_sent and nothing waits.
        rid = self.register()["registration_id"]
        [proposal] = self.propose()
        self.owner("remove", rid, "2026-09-17T12:05:00+00:00")
        code, reported, err = self.report(
            proposal["attempt_id"], "not_sent", now="2026-09-17T12:06:00+00:00",
            recheck="registration removed",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(reported["registration"]["status"], "removed")
        code, first, err = self.notice("2026-09-17T12:15:10+00:00")
        self.assertEqual(code, 0, err)
        [event] = first["events"]
        self.assertEqual((event["attempt_id"], event["status"]), (proposal["attempt_id"], "not_sent"))
        self.assertIn("removed", event["next_action"])
        self.assertNotIn("waits again", event["next_action"])
        self.assertNotIn("rearm", event["next_action"])
        self.assertIn("removed", first["text"])
        self.assertEqual(first["new"], [])
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T12:15:11+00:00")
        self.assertEqual(code, 0, err)
        # Rearmed after a not_sent: the old episode's wait is over, a new one waits.
        other = self.register(task_id="task-2")["registration_id"]
        [proposal] = self.propose(now="2026-09-17T12:20:00+00:00", task_ids=("task-2",))
        code, _, err = self.report(proposal["attempt_id"], "not_sent", now="2026-09-17T12:20:30+00:00")
        self.assertEqual(code, 0, err)
        self.owner("rearm", other, "2026-09-17T12:21:00+00:00", "--episode", "episode-2")
        code, second, err = self.notice("2026-09-17T12:30:10+00:00")
        self.assertEqual(code, 0, err)
        [event] = second["events"]
        self.assertEqual(event["attempt_id"], proposal["attempt_id"])
        self.assertIn("rearmed", event["next_action"])
        self.assertNotIn("episode-2", json.dumps(second))
        self.assertNotIn("episode-1", json.dumps(second))

    def test_query_knowledge_learned_during_a_replay_tick_survives_acknowledgement(
        self,
    ) -> None:
        self.register(task_id="task-1")
        other = self.register(task_id="task-2", gate=dict(QUOTA_GATE, bucket="daily"))
        key = self.gate_key()
        other_key = other["gate_key"]
        code, first, err = self.notice(
            "2026-09-17T12:00:10+00:00",
            [self.gate_entry(key, "unhandled"), self.gate_entry(other_key, "observed")],
        )
        self.assertEqual(code, 0, err)
        self.assertEqual([n["gate_key"] for n in first["new"]], [key])
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T12:00:11+00:00")
        self.assertEqual(code, 0, err)
        code, second, err = self.notice(
            "2026-09-17T12:15:10+00:00",
            [self.gate_entry(key, "unhandled"), self.gate_entry(other_key, "unhandled")],
        )
        self.assertEqual(code, 0, err)
        self.assertEqual([n["gate_key"] for n in second["new"]], [other_key])
        # The monitor crashed before acknowledging. The next tick ran observe,
        # which now covers both gates, and gets the identical pending notice.
        code, replay, err = self.notice(
            "2026-09-17T12:30:10+00:00",
            [self.gate_entry(key, "observed"), self.gate_entry(other_key, "observed")],
        )
        self.assertEqual(code, 0, err)
        self.assertTrue(replay["replayed"])
        # The frozen notice is identical; the schedule is a live recommendation
        # computed at each read and is not part of the notice.
        strip = lambda payload: {k: v for k, v in payload.items() if k not in {"replayed", "schedule"}}
        self.assertEqual(json.dumps(strip(replay), sort_keys=True), json.dumps(strip(second), sort_keys=True))
        code, acked, err = self.acknowledge(replay["notice_id"], "2026-09-17T12:30:11+00:00")
        self.assertEqual(code, 0, err)
        self.assertEqual(acked["baseline"]["markers"], second["markers_now"], "exactly the frozen snapshot")
        # A later tick that does not query the first gate: the covered result
        # learned during the replay tick already cleared both gaps.
        code, fourth, err = self.notice(
            "2026-09-17T12:45:10+00:00", [self.gate_entry(other_key, "observed")]
        )
        self.assertEqual(code, 0, err)
        self.assertTrue(fourth["report"])
        self.assertEqual(sorted(c["marker"] for c in fourth["cleared"]), sorted([f"unhandled:{key}", f"unhandled:{other_key}"]))
        self.assertEqual(fourth["new"], [])
        self.assertEqual(fourth["markers_now"], [])
        self.assertEqual(fourth["coverage"], {"adapter_report": True, "queried": [other_key], "retained": []})
        code, _, err = self.acknowledge(fourth["notice_id"], "2026-09-17T12:45:11+00:00")
        self.assertEqual(code, 0, err)
        # No report at all afterwards: nothing is manufactured either way.
        code, fifth, err = self.notice("2026-09-17T13:00:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertFalse(fifth["report"])
        self.assertEqual(fifth["markers_now"], [])
        self.assertEqual(fifth["coverage"]["retained"], [])
        _, inspected, _ = run("inspect", "--store", self.store, "--now", "2026-09-17T13:00:10+00:00")
        self.assertNotIn("notification", inspected)

    def test_held_and_error_results_learned_during_a_replay_tick_end_the_gap(self) -> None:
        self.register(task_id="task-1", extra=("--expires-in-minutes", str(7 * 24 * 60)))
        other = self.register(task_id="task-2", gate=dict(QUOTA_GATE, bucket="daily"), extra=("--expires-in-minutes", str(7 * 24 * 60)))
        key = self.gate_key()
        other_key = other["gate_key"]
        code, first, err = self.notice(
            "2026-09-17T12:00:10+00:00",
            [self.gate_entry(key, "unhandled"), self.gate_entry(other_key, "unhandled")],
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(len(first["new"]), 2)
        # Not acknowledged. The next tick's adapter holds one gate and fails the
        # other; the cycle ingests those as error observations as usual.
        at = "2026-09-17T12:15:00+00:00"
        code, _, err = cycle(
            self.store, at,
            observations=[
                {"gate_key": key, "status": "error", "observed_at": at, "reason": "held:policy-revision-mismatch"},
                {"gate_key": other_key, "status": "error", "observed_at": at, "reason": "error:codex-timeout"},
            ],
        )
        self.assertEqual(code, 0, err)
        code, replay, err = self.notice(
            "2026-09-17T12:15:10+00:00",
            [self.gate_entry(key, "held"), self.gate_entry(other_key, "error")],
        )
        self.assertEqual(code, 0, err)
        self.assertEqual((replay["replayed"], replay["text"]), (True, first["text"]))
        code, _, err = self.acknowledge(replay["notice_id"], "2026-09-17T12:15:11+00:00")
        self.assertEqual(code, 0, err)
        # Inside the backoff window nothing is queried: the held and error
        # results still stand, so neither gate is a gap and a failure alongside.
        code, after, err = self.notice("2026-09-17T12:20:10+00:00", [])
        self.assertEqual(code, 0, err)
        self.assertEqual(
            sorted(c["marker"] for c in after["cleared"]),
            sorted([f"unhandled:{key}", f"unhandled:{other_key}"]),
        )
        self.assertEqual(
            after["markers_now"],
            sorted([f"failing:{key}:held:policy-revision-mismatch", f"failing:{other_key}:error:codex-timeout"]),
        )
        self.assertEqual(after["coverage"]["retained"], [])

    def test_owner_pause_while_a_notice_is_pending_retires_the_gap_without_inventing_one(
        self,
    ) -> None:
        rid = self.register(task_id="task-1")["registration_id"]
        other = self.register(task_id="task-2", gate=dict(QUOTA_GATE, bucket="daily"))
        key = self.gate_key()
        other_rid, other_key = other["registration_id"], other["gate_key"]
        code, first, err = self.notice(
            "2026-09-17T12:00:10+00:00",
            [self.gate_entry(key, "unhandled"), self.gate_entry(other_key, "unhandled")],
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(len(first["new"]), 2)
        self.owner("pause", other_rid, "2026-09-17T12:05:00+00:00")
        code, replay, err = self.notice("2026-09-17T12:15:10+00:00", [self.gate_entry(key, "observed")])
        self.assertEqual(code, 0, err)
        self.assertEqual((replay["replayed"], replay["text"]), (True, first["text"]))
        code, _, err = self.acknowledge(replay["notice_id"], "2026-09-17T12:15:11+00:00")
        self.assertEqual(code, 0, err)
        code, after, err = self.notice("2026-09-17T12:16:10+00:00")
        self.assertEqual(code, 0, err)
        cleared = {c["gate_key"]: c["registration_ids"] for c in after["cleared"]}
        self.assertEqual(cleared, {key: [rid], other_key: []}, "covered, and nothing waiting")
        self.assertEqual(after["markers_now"], [])
        code, _, err = self.acknowledge(after["notice_id"], "2026-09-17T12:16:11+00:00")
        self.assertEqual(code, 0, err)
        # Resuming does not resurrect the gap: nothing has queried the gate since.
        self.owner("resume", other_rid, "2026-09-17T12:20:00+00:00")
        code, quiet, err = self.notice("2026-09-17T12:30:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertFalse(quiet["report"])
        self.assertEqual(quiet["coverage"]["retained"], [])
        # Only a query says it is a gap again.
        code, again, err = self.notice("2026-09-17T12:45:10+00:00", [self.gate_entry(other_key, "unhandled")])
        self.assertEqual(code, 0, err)
        self.assertEqual([n["gate_key"] for n in again["new"]], [other_key])

    def test_malformed_report_or_knowledge_state_fails_without_mutation(self) -> None:
        self.register()
        key = self.gate_key()
        code, first, err = self.notice("2026-09-17T12:00:10+00:00", [self.gate_entry(key, "unhandled")])
        self.assertEqual(code, 0, err)
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T12:00:11+00:00")
        self.assertEqual(code, 0, err)
        state_path = Path(self.store) / "state.json"
        before = state_path.read_bytes()
        bad = dict(self.gate_entry(key, "observed"), outcome="SYNTHETIC-BAD-OUTCOME")
        code, payload, err = self.notice("2026-09-17T12:15:10+00:00", report={"gates": [bad]})
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("invalid-adapter-report", err)
        self.assertEqual(state_path.read_bytes(), before, "a refused report stores nothing")
        code, retained, err = self.notice("2026-09-17T12:15:20+00:00")
        self.assertEqual(code, 0, err)
        self.assertFalse(retained["report"])
        self.assertEqual(retained["coverage"]["retained"], [key], "the gap knowledge is intact")
        # Malformed private query knowledge is refused like any other malformed
        # notification state: notice and acknowledge fail, the registry stays readable.
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["notification"]["knowledge"] = {key: "SYNTHETIC-BAD-OUTCOME"}
        state_path.write_text(json.dumps(state), encoding="utf-8")
        malformed = state_path.read_bytes()
        code, payload, err = self.notice("2026-09-17T12:30:10+00:00", [self.gate_entry(key, "observed")])
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("corrupt-store", err)
        self.assertNotIn("SYNTHETIC-BAD-OUTCOME", err)
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T12:30:11+00:00")
        self.assertEqual(code, 2)
        self.assertIn("corrupt-store", err)
        self.assertEqual(state_path.read_bytes(), malformed)
        code, inspected, err = run("inspect", "--store", self.store, "--now", "2026-09-17T12:30:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertEqual(inspected["registrations"][0]["gate_key"], key)

    def test_store_without_query_knowledge_keeps_baseline_retention_then_learns(self) -> None:
        self.register(task_id="task-1")
        other = self.register(task_id="task-2", gate=dict(QUOTA_GATE, bucket="daily"))
        key = self.gate_key()
        other_key = other["gate_key"]
        code, first, err = self.notice(
            "2026-09-17T12:00:10+00:00",
            [self.gate_entry(key, "unhandled"), self.gate_entry(other_key, "observed")],
        )
        self.assertEqual(code, 0, err)
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T12:00:11+00:00")
        self.assertEqual(code, 0, err)
        # A store written before per-gate query knowledge existed holds only the
        # acknowledged markers; its retention must read the same as before.
        state_path = Path(self.store) / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["notification"].pop("knowledge", None)
        state_path.write_text(json.dumps(state), encoding="utf-8")
        code, absent, err = self.notice("2026-09-17T12:15:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertFalse(absent["report"])
        self.assertEqual(absent["coverage"], {"adapter_report": False, "queried": [], "retained": [key]})
        code, partial, err = self.notice("2026-09-17T12:30:10+00:00", [self.gate_entry(other_key, "observed")])
        self.assertEqual(code, 0, err)
        self.assertFalse(partial["report"])
        self.assertEqual(partial["coverage"]["retained"], [key])
        code, covered, err = self.notice("2026-09-17T12:45:10+00:00", [self.gate_entry(key, "observed")])
        self.assertEqual(code, 0, err)
        self.assertEqual([c["gate_key"] for c in covered["cleared"]], [key])
        code, _, err = self.acknowledge(covered["notice_id"], "2026-09-17T12:45:11+00:00")
        self.assertEqual(code, 0, err)
        code, later, err = self.notice("2026-09-17T13:00:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertFalse(later["report"])
        self.assertEqual(later["coverage"]["retained"], [])

    EDITED_GATE = dict(
        QUOTA_GATE, account="synthetic-account-b", route="other-route", policy_revision="policy-2"
    )

    def assert_original_labels(self, body: dict, text_line: str | None = None) -> None:
        self.assertEqual(
            (body["kind"], body["account"], body["route"]),
            ("quota_recovery", "synthetic-account-a", "cli"),
        )
        if text_line is not None:
            self.assertIn("quota_recovery synthetic-account-a/cli", text_line)
            self.assertNotIn("synthetic-account-b", text_line)
            self.assertNotIn("other-route", text_line)

    def test_not_sent_events_after_a_gate_edit_name_the_gate_the_attempts_were_made_against(
        self,
    ) -> None:
        # Three not_sent attempts exhaust the episode; the owner edits the gate
        # (allowed while unresolved) before a restarted monitor's first notice.
        # Each event is a fact about its attempt, so it names the gate that
        # attempt was reserved against, not the registration's current gate.
        rid = self.register()["registration_id"]
        attempts = []
        for minute in (0, 15, 30):
            now = f"2026-09-17T12:{minute:02d}:00+00:00"
            [proposal] = self.propose(now=now)
            attempts.append(proposal["attempt_id"])
            code, _, err = self.report(proposal["attempt_id"], "not_sent", now=now)
            self.assertEqual(code, 0, err)
        updated = self.owner(
            "update", rid, "2026-09-17T12:40:00+00:00", "--gate-json", json.dumps(self.EDITED_GATE)
        )
        self.assertEqual((updated["status"], updated["gate"]), ("unresolved", self.EDITED_GATE))
        code, first, err = self.notice("2026-09-17T12:45:10+00:00")
        self.assertEqual(code, 0, err)
        self.assertEqual([e["attempt_id"] for e in first["events"]], attempts)
        event_lines = [line for line in first["text"].splitlines() if line.startswith("event:")]
        self.assertEqual(len(event_lines), 3)
        for event, line in zip(first["events"], event_lines):
            self.assert_original_labels(event, line)

    def test_unknown_event_and_its_unresolved_attention_keep_the_attempt_gate_after_an_edit(
        self,
    ) -> None:
        # An unknown send leaves the registration unresolved (delivery-unknown);
        # the owner may edit the gate meanwhile. Both the event and the attention
        # line that names this attempt identify the gate it was reserved against.
        rid = self.register()["registration_id"]
        [proposal] = self.propose()
        code, _, err = self.report(
            proposal["attempt_id"], "unknown", now="2026-09-17T12:00:30+00:00", tool_response="timeout"
        )
        self.assertEqual(code, 0, err)
        updated = self.owner(
            "update", rid, "2026-09-17T12:05:00+00:00", "--gate-json", json.dumps(self.EDITED_GATE)
        )
        self.assertEqual((updated["status"], updated["attempt_id"]), ("unresolved", proposal["attempt_id"]))
        code, first, err = self.notice("2026-09-17T12:15:10+00:00")
        self.assertEqual(code, 0, err)
        [event] = first["events"]
        self.assertEqual((event["attempt_id"], event["status"]), (proposal["attempt_id"], "unknown"))
        [entry] = first["new"]
        self.assertEqual(
            (entry["family"], entry["status"], entry["unresolved_reason"], entry["attempt_id"]),
            ("attention", "unresolved", "delivery-unknown", proposal["attempt_id"]),
        )
        lines = first["text"].splitlines()
        [event_line] = [line for line in lines if line.startswith("event:")]
        [attention_line] = [line for line in lines if line.startswith("new:")]
        self.assert_original_labels(event, event_line)
        self.assert_original_labels(entry, attention_line)
        # The registration itself still reports the owner's current intent.
        _, inspected, _ = run("inspect", "--store", self.store, "--now", "2026-09-17T12:15:10+00:00")
        self.assertEqual(inspected["registrations"][0]["gate"], self.EDITED_GATE)

    def test_attempt_limited_attention_after_a_gate_edit_names_the_exhausting_attempt_gate(
        self,
    ) -> None:
        # The attempt-limit entry names no open attempt, but its `since` is the
        # episode's last not_sent resolution; the entry identifies that attempt's
        # gate, so the same stuck work keeps the same labels across a gate edit.
        rid = self.register()["registration_id"]
        for minute in (0, 15, 30):
            now = f"2026-09-17T12:{minute:02d}:00+00:00"
            [proposal] = self.propose(now=now)
            code, _, err = self.report(proposal["attempt_id"], "not_sent", now=now)
            self.assertEqual(code, 0, err)
        self.owner("update", rid, "2026-09-17T12:40:00+00:00", "--gate-json", json.dumps(self.EDITED_GATE))
        code, first, err = self.notice("2026-09-17T12:45:10+00:00")
        self.assertEqual(code, 0, err)
        [entry] = first["new"]
        self.assertEqual(
            (entry["status"], entry["unresolved_reason"], entry["attempt_id"], entry["since"]),
            ("unresolved", "attempt-limit", None, "2026-09-17T12:30:00+00:00"),
        )
        [attention_line] = [line for line in first["text"].splitlines() if line.startswith("new:")]
        self.assert_original_labels(entry, attention_line)

    def test_cleared_gap_resolved_through_an_attempt_names_that_attempt_gate(self) -> None:
        # A gate that was unhandled had an earlier not_sent attempt. After the
        # owner edits the gate, the cleared marker's key is found only through
        # that attempt, and its labels are the attempt's, not the edited gate's.
        rid = self.register()["registration_id"]
        key = self.gate_key()
        [proposal] = self.propose()
        code, _, err = self.report(proposal["attempt_id"], "not_sent", now="2026-09-17T12:00:30+00:00")
        self.assertEqual(code, 0, err)
        code, first, err = self.notice("2026-09-17T12:00:40+00:00", [self.gate_entry(key, "unhandled")])
        self.assertEqual(code, 0, err)
        self.assertEqual([n["family"] for n in first["new"]], ["unhandled"])
        code, _, err = self.acknowledge(first["notice_id"], "2026-09-17T12:00:41+00:00")
        self.assertEqual(code, 0, err)
        self.owner("update", rid, "2026-09-17T12:05:00+00:00", "--gate-json", json.dumps(self.EDITED_GATE))
        code, second, err = self.notice("2026-09-17T12:15:10+00:00")
        self.assertEqual(code, 0, err)
        [cleared] = second["cleared"]
        self.assertEqual((cleared["family"], cleared["gate_key"]), ("unhandled", key))
        [cleared_line] = [line for line in second["text"].splitlines() if line.startswith("cleared:")]
        self.assert_original_labels(cleared, cleared_line)
        self.assertEqual(second["new"], [], "the edited gate was not queried, so it is no gap")

    def strip_attempt_gates(self) -> None:
        """Rewrite the store as an engine before the attempt gate snapshot wrote it."""
        state_path = Path(self.store) / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        for attempt in state["attempts"].values():
            self.assertIn("gate", attempt)
            del attempt["gate"]
        state_path.write_text(json.dumps(state), encoding="utf-8")

    def test_legacy_attempt_labels_come_only_from_a_record_with_the_same_gate_key(self) -> None:
        # A store written before attempts carried their gate: the registration
        # still holds the same key, and an identical key is an identical gate,
        # so the labels are provable and read as before.
        self.register()
        [proposal] = self.propose()
        code, _, err = self.report(
            proposal["attempt_id"], "unknown", now="2026-09-17T12:00:30+00:00", tool_response="timeout"
        )
        self.assertEqual(code, 0, err)
        self.strip_attempt_gates()
        code, first, err = self.notice("2026-09-17T12:15:10+00:00")
        self.assertEqual(code, 0, err)
        [event] = first["events"]
        [entry] = first["new"]
        self.assert_original_labels(event)
        self.assert_original_labels(entry)
        self.assertIn("quota_recovery synthetic-account-a/cli", first["text"])

    def test_legacy_attempt_labels_are_unavailable_after_a_gate_edit_never_the_new_gate(
        self,
    ) -> None:
        # Same legacy store, but the owner edited the gate before the notice: no
        # record with the attempt's key remains, so the labels are explicitly
        # unavailable rather than borrowed from the registration's current gate.
        rid = self.register()["registration_id"]
        [proposal] = self.propose()
        code, _, err = self.report(
            proposal["attempt_id"], "unknown", now="2026-09-17T12:00:30+00:00", tool_response="timeout"
        )
        self.assertEqual(code, 0, err)
        self.strip_attempt_gates()
        self.owner("update", rid, "2026-09-17T12:05:00+00:00", "--gate-json", json.dumps(self.EDITED_GATE))
        code, first, err = self.notice("2026-09-17T12:15:10+00:00")
        self.assertEqual(code, 0, err)
        [event] = first["events"]
        [entry] = first["new"]
        for body in (event, entry):
            self.assertEqual((body["kind"], body["account"], body["route"]), (None, None, None))
        lines = first["text"].splitlines()
        [event_line] = [line for line in lines if line.startswith("event:")]
        [attention_line] = [line for line in lines if line.startswith("new:")]
        for line in (event_line, attention_line):
            self.assertIn("unknown unknown/unknown", line)
            self.assertNotIn("synthetic-account-b", line)
            self.assertNotIn("other-route", line)
        self.assertIn(proposal["attempt_id"], event_line)
        self.assertIn(rid, attention_line)

    def test_malformed_attempt_gate_snapshot_fails_notice_and_leaves_the_registry_readable(
        self,
    ) -> None:
        rid = self.register()["registration_id"]
        [proposal] = self.propose()
        code, _, err = self.report(
            proposal["attempt_id"], "unknown", now="2026-09-17T12:00:30+00:00", tool_response="timeout"
        )
        self.assertEqual(code, 0, err)
        state_path = Path(self.store) / "state.json"
        secret = "SYNTHETIC-SNAPSHOT-SECRET-4b1e"
        for bad_gate in (
            {"kind": "shell", "account": secret},          # not a gate at all
            dict(self.EDITED_GATE, account=secret),       # a gate, but not this attempt's key
        ):
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["attempts"][proposal["attempt_id"]]["gate"] = bad_gate
            state_path.write_text(json.dumps(state), encoding="utf-8")
            code, payload, err = self.notice("2026-09-17T12:15:10+00:00")
            self.assertEqual(code, 2)
            self.assertIsNone(payload)
            self.assertIn("corrupt-store", err)
            self.assertNotIn(secret, err)
            code, inspected, err = run("inspect", "--store", self.store, "--now", "2026-09-17T12:15:10+00:00")
            self.assertEqual(code, 0, err)
            [entry] = inspected["attention"]
            self.assertEqual((entry["registration_id"], entry["status"]), (rid, "unresolved"))
            self.assertIsNone(json.loads(state_path.read_text(encoding="utf-8")).get("notification"))


class WorkedSyntheticExample(CycleHelpers):
    """The engine-cli.md worked example, in order: plan, states, synthetic
    input, result, an honest report, then notice and a guarded
    acknowledgement."""

    def test_example_sequence_relays_one_event_and_no_false_stuck_work(self) -> None:
        gate = {
            "kind": "quota_recovery",
            "account": "acct-label",
            "route": "route-label",
            "bucket": "weekly",
            "policy_revision": "policy-2026-09+0123456789abcdef",
        }
        for task in ("t1", "t2", "t3"):
            self.register(
                owner="me", host="h1", task_id=task, episode=f"{task}-wait-1", gate=gate,
                continuation=f"Quota observed open; revalidate and resume {task}.",
            )
        code, plan, err = run("cycle", "--store", self.store, "--now", T0)
        self.assertEqual(code, 0, err)
        [request] = plan["observation_requests"]
        self.assertEqual(request["task_ids"], ["t1", "t2", "t3"])
        task_states = [
            {"host": "h1", "task_id": "t1", "status": "idle", "observed_at": T0},
            {"host": "h1", "task_id": "t2", "status": "running", "observed_at": T0},
            {"host": "h1", "task_id": "t3", "status": "completed", "observed_at": T0},
        ]
        observation = {
            "gate_key": request["gate_key"], "status": "ok", "observed_at": T0,
            "account": "acct-label", "route": "route-label",
            "buckets": [{"name": "weekly", "remaining_percent": 40}],
        }
        code, result, err = cycle(
            self.store, T0, observations=[observation], task_states=task_states
        )
        self.assertEqual(code, 0, err)
        [proposal] = result["wake_proposals"]
        self.assertEqual(proposal["task_id"], "t1")
        self.assertEqual(
            {(s["task_id"], s["reason"]) for s in result["skipped"]},
            {("t2", "task-running"), ("t3", "task-completed")},
        )
        # Report before notice: no send was made in the synthetic run, so the
        # truthful outcome is not_sent, and the reservation is no longer stuck work.
        code, reported, err = self.report(
            proposal["attempt_id"], "not_sent", now="2026-09-17T12:00:20+00:00",
            recheck="synthetic example: no native send was made",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual((reported["attempt"]["status"], reported["registration"]["status"]), ("not_sent", "waiting"))
        code, notice, err = run("notice", "--store", self.store, "--now", "2026-09-17T12:00:30+00:00")
        self.assertEqual(code, 0, err)
        self.assertTrue(notice["report"])
        self.assertEqual([e["status"] for e in notice["events"]], ["not_sent"])
        self.assertEqual(notice["new"], [], "the reported attempt is not stuck work")
        self.assertNotIn("reserved since", notice["text"])
        self.assertFalse(notice["coverage"]["adapter_report"], "observe did not run")
        notice_id = notice["notice_id"] if notice["report"] else ""
        self.assertEqual(len(notice_id), 24)
        code, acked, err = run(
            "acknowledge", "--store", self.store, "--notice-id", notice_id, "--now", "2026-09-17T12:00:31+00:00"
        )
        self.assertEqual(code, 0, err)
        self.assertTrue(acked["acknowledged"])
        # A quiet follow-up tick yields no id, so the guarded extraction is empty.
        code, quiet, err = run("notice", "--store", self.store, "--now", "2026-09-17T12:15:30+00:00")
        self.assertEqual(code, 0, err)
        self.assertFalse(quiet["report"])
        self.assertEqual(quiet["notice_id"] if quiet["report"] else "", "")


class OwnerCadenceMetadata(CycleHelpers):
    """Owner forecasts and effective intervals ride the registration, not the gate."""

    def owner(self, command: str, rid: str, now: str, *extra: str) -> tuple[int, Any, str]:
        return run(
            command, "--store", self.store, "--registration-id", rid, "--owner",
            "owner-a", *extra, "--now", now,
        )

    def test_forecast_and_interval_round_trip_outside_gate_identity(self) -> None:
        plain = self.register(task_id="task-1")
        hinted = self.register(
            task_id="task-2",
            extra=(
                "--expected-open-at", "2026-09-17T12:30:00+00:00",
                "--poll-interval-minutes", "5",
            ),
        )
        self.assertEqual(hinted["expected_open_at"], "2026-09-17T12:30:00+00:00")
        self.assertEqual(hinted["poll_interval_minutes"], 5)
        self.assertIsNone(plain["expected_open_at"])
        self.assertIsNone(plain["poll_interval_minutes"])
        # Same gate, same key: the metadata is outside gate identity.
        self.assertEqual(hinted["gate_key"], plain["gate_key"])
        self.assertEqual(hinted["gate"], QUOTA_GATE)
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        by_task = {r["task_id"]: r for r in inspected["registrations"]}
        self.assertEqual(by_task["task-2"]["expected_open_at"], "2026-09-17T12:30:00+00:00")
        self.assertEqual(by_task["task-2"]["poll_interval_minutes"], 5)
        self.assertIsNone(by_task["task-1"]["expected_open_at"])
        self.assertIsNone(by_task["task-1"]["poll_interval_minutes"])
        # Explicit sentinels on register mean null and adaptive.
        cleared = self.register(
            task_id="task-3",
            extra=("--expected-open-at", "unknown", "--poll-interval-minutes", "adaptive"),
        )
        self.assertIsNone(cleared["expected_open_at"])
        self.assertIsNone(cleared["poll_interval_minutes"])

    def test_invalid_forecast_or_interval_is_rejected_atomically(self) -> None:
        secret = "SYNTHETIC-FORECAST-SECRET-4b1d"
        base = (
            "register", "--store", self.store, "--owner", "owner-a", "--host", "host-a",
            "--task-id", "task-1", "--episode", "episode-1", "--gate-json",
            json.dumps(QUOTA_GATE), "--continuation", "Continue.", "--now", T0,
        )
        for label, code_name, extra in (
            ("past forecast", "invalid-forecast", ("--expected-open-at", "2026-09-17T11:59:00+00:00")),
            ("forecast at now", "invalid-forecast", ("--expected-open-at", T0)),
            ("forecast past the default expiry", "invalid-forecast", ("--expected-open-at", "2026-09-18T12:00:00+00:00")),
            ("forecast without offset", "invalid-forecast", ("--expected-open-at", "2026-09-17T13:00:00")),
            ("forecast that is not a time", "invalid-forecast", ("--expected-open-at", secret)),
            ("zero interval", "invalid-interval", ("--poll-interval-minutes", "0")),
            ("interval past a week", "invalid-interval", ("--poll-interval-minutes", "10081")),
            ("negative interval", "invalid-interval", ("--poll-interval-minutes", "-5")),
            ("interval that is not a number", "invalid-interval", ("--poll-interval-minutes", secret)),
        ):
            with self.subTest(label=label):
                code, payload, err = run(*base, *extra)
                self.assertEqual(code, 2)
                self.assertIsNone(payload)
                self.assertIn(f"aeon bell: {code_name}:", err)
                self.assertNotIn(secret, err)
                _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
                self.assertEqual(inspected["registrations"], [], "nothing was written")
        # The bounds are inclusive: 1 and 10080 minutes are accepted.
        code, _, err = run(*base, "--poll-interval-minutes", "10080")
        self.assertEqual(code, 0, err)
        # A forecast past the expiry is accepted only with the expiry renewed in
        # the same command; the expiry is never extended implicitly.
        rid = self.register(task_id="task-2", extra=("--expires-in-minutes", "60"))["registration_id"]
        code, payload, err = self.owner(
            "update", rid, T0, "--expected-open-at", "2026-09-17T14:00:00+00:00"
        )
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("invalid-forecast", err)
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        entry = {r["task_id"]: r for r in inspected["registrations"]}["task-2"]
        self.assertIsNone(entry["expected_open_at"])
        self.assertEqual(entry["expires_at"], "2026-09-17T13:00:00+00:00")
        code, updated, err = self.owner(
            "update", rid, T0, "--expected-open-at", "2026-09-17T14:00:00+00:00",
            "--expires-in-minutes", "180",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(updated["expected_open_at"], "2026-09-17T14:00:00+00:00")
        self.assertEqual(updated["expires_at"], "2026-09-17T15:00:00+00:00")
        # Sentinels clear; an update of only these fields is a change.
        code, cleared, err = self.owner(
            "update", rid, T0, "--expected-open-at", "unknown", "--poll-interval-minutes", "adaptive"
        )
        self.assertEqual(code, 0, err)
        self.assertIsNone(cleared["expected_open_at"])
        self.assertIsNone(cleared["poll_interval_minutes"])
        code, _, err = self.owner("update", rid, T0)
        self.assertEqual(code, 2)
        self.assertIn("nothing-to-update", err)
        # A stored forecast is allowed to pass; only a new one must be future.
        code, later, err = self.owner(
            "update", rid, T0, "--expected-open-at", "2026-09-17T12:30:00+00:00"
        )
        self.assertEqual(code, 0, err)
        code, renewed, err = self.owner(
            "update", rid, "2026-09-17T13:00:00+00:00", "--expires-in-minutes", "60"
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(renewed["expected_open_at"], "2026-09-17T12:30:00+00:00")

    def test_metadata_only_update_while_reserved_leaves_the_attempt_untouched(self) -> None:
        rid = self.register()["registration_id"]
        [proposal] = self.propose()
        recheck = proposal["native_steps"][0]["require"]
        code, updated, err = self.owner(
            "update", rid, T0, "--expected-open-at", "2026-09-17T13:00:00+00:00",
            "--poll-interval-minutes", "120",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(updated["status"], "reserved")
        self.assertEqual(updated["poll_interval_minutes"], 120)
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        [entry] = inspected["registrations"]
        self.assertEqual({k: entry[k] for k in recheck}, recheck)
        [attempt] = inspected["unresolved_attempts"]
        self.assertEqual(attempt["attempt_id"], proposal["attempt_id"])
        self.assertEqual(attempt["status"], "reserved")
        # Nothing about the metadata reaches the frozen attempt or its message.
        [send] = [s for s in proposal["native_steps"] if s["step"] == "send"]
        self.assertNotIn("2026-09-17T13:00:00", send["arguments"]["message"])
        code, reported, err = self.report(proposal["attempt_id"], "accepted")
        self.assertEqual(code, 0, err)
        self.assertEqual(reported["attempt"]["message_sha256"], proposal_digest(proposal))
        self.assertEqual(reported["registration"]["poll_interval_minutes"], 120)


    def test_rearm_clears_the_forecast_and_keeps_the_interval_unless_told_otherwise(
        self,
    ) -> None:
        rid = self.register(
            extra=(
                "--expected-open-at", "2026-09-17T13:00:00+00:00",
                "--poll-interval-minutes", "30",
            )
        )["registration_id"]
        [proposal] = self.propose()
        self.report(proposal["attempt_id"], "accepted")
        # A fresh episode is a fresh wait: the forecast belonged to the old one
        # and is cleared; the effective interval is a standing requirement.
        code, rearmed, err = self.owner("rearm", rid, T0, "--episode", "episode-2")
        self.assertEqual(code, 0, err)
        self.assertEqual(rearmed["episode"], "episode-2")
        self.assertIsNone(rearmed["expected_open_at"])
        self.assertEqual(rearmed["poll_interval_minutes"], 30)
        # Both may be supplied with the rearm; the forecast is validated against
        # the expiry the command leaves behind and never extends it implicitly.
        code, payload, err = self.owner(
            "rearm", rid, T0, "--episode", "episode-3",
            "--expected-open-at", "2026-09-19T12:00:00+00:00",
        )
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("invalid-forecast", err)
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        [entry] = inspected["registrations"]
        self.assertEqual(entry["episode"], "episode-2", "the failed rearm wrote nothing")
        self.assertEqual(entry["episodes"], ["episode-1", "episode-2"])
        code, rearmed, err = self.owner(
            "rearm", rid, T0, "--episode", "episode-3",
            "--expected-open-at", "2026-09-19T12:00:00+00:00",
            "--expires-in-minutes", "4320", "--poll-interval-minutes", "adaptive",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(rearmed["expected_open_at"], "2026-09-19T12:00:00+00:00")
        self.assertIsNone(rearmed["poll_interval_minutes"])
        self.assertEqual(rearmed["expires_at"], "2026-09-20T12:00:00+00:00")
        self.assertEqual(rearmed["episodes"], ["episode-1", "episode-2", "episode-3"])


class AdaptiveSchedule(CycleHelpers):
    """Planned checks come from the observation anchor and current owner metadata."""

    def fresh_store(self) -> None:
        self.store = str(Path(self._tmp.name) / f"store-{len(os.listdir(self._tmp.name))}")

    def closed_at(self, observed_at: str, reset_at: str | None = None, **states: Any):
        _, result, err = cycle(
            self.store,
            observed_at,
            observations=[
                self.quota_observation(remaining=0, observed_at=observed_at, reset_at=reset_at)
            ],
            **states,
        )
        self.assertIsNotNone(result, err)
        return result

    def test_default_interval_is_a_quarter_of_the_wait_bounded_15_to_360(self) -> None:
        cases = (
            ("30 minutes to opening", "2026-09-17T12:30:00+00:00", None, "2026-09-17T12:15:00+00:00", 15),
            ("5 hours to opening", "2026-09-17T17:00:00+00:00", None, "2026-09-17T13:15:00+00:00", 75),
            ("48 hours to opening", "2026-09-19T12:00:00+00:00", None, "2026-09-17T18:00:00+00:00", 360),
            ("no forecast", None, None, "2026-09-17T13:00:00+00:00", 60),
            ("reset hint only", None, "2026-09-17T12:30:00+00:00", "2026-09-17T12:15:00+00:00", 15),
        )
        for label, forecast, reset_at, next_check_at, delay in cases:
            with self.subTest(label=label):
                self.fresh_store()
                extra: tuple[str, ...] = ("--expires-in-minutes", "4320")
                if forecast is not None:
                    extra += ("--expected-open-at", forecast)
                self.register(extra=extra)
                result = self.closed_at(T0, reset_at=reset_at, task_states=[self.idle()])
                self.assert_no_wake(result, "gate-closed")
                schedule = result["schedule"]
                self.assertEqual(schedule["next_check_at"], next_check_at)
                self.assertEqual(schedule["delay_minutes"], delay)
                self.assertEqual(schedule["reason"], "gate-query")
                [gate] = schedule["gates"]
                self.assertEqual(gate["gate_key"], self.gate_key())
                self.assertFalse(gate["due"])
                self.assertEqual(gate["query_due_at"], next_check_at)
                self.assertEqual(gate["anchor"], T0)
                self.assertEqual(gate["cadence"], "adaptive")
                self.assertEqual(gate["interval_minutes"], delay)
                # The same store, read again by inspect, plans the same check.
                _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
                self.assertEqual(inspected["schedule"]["next_check_at"], next_check_at)

    def test_anchor_holds_across_early_reads_and_a_missed_forecast_stays_due(self) -> None:
        self.register(extra=("--expected-open-at", "2026-09-17T12:30:00+00:00"))
        result = self.closed_at(T0)
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T12:15:00+00:00")
        # Early reads neither request nor slide the planned check.
        for early in ("2026-09-17T12:05:00+00:00", "2026-09-17T12:10:00+00:00", "2026-09-17T12:14:59+00:00"):
            _, result, _ = cycle(self.store, early)
            self.assertEqual(result["observation_requests"], [], early)
            self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T12:15:00+00:00")
            self.assertFalse(result["schedule"]["gates"][0]["due"])
        # At the planned time the gate is due: one request, an immediate recommendation.
        _, result, _ = cycle(self.store, "2026-09-17T12:15:00+00:00")
        [request] = result["observation_requests"]
        self.assertEqual(request["reason"], "stale")
        self.assertNotIn("refresh_lead_minutes", request)
        self.assertEqual(result["schedule"]["reason"], "gate-due")
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T12:15:00+00:00")
        self.assertEqual(result["schedule"]["delay_minutes"], 0)
        # The forecast passes with no new observation: the check stays due, at
        # its anchored time, across repeated reads; nothing is postponed.
        for late in ("2026-09-17T12:31:00+00:00", "2026-09-17T13:40:00+00:00"):
            _, result, _ = cycle(self.store, late)
            self.assertEqual([r["reason"] for r in result["observation_requests"]], ["stale"])
            [gate] = result["schedule"]["gates"]
            self.assertTrue(gate["due"])
            self.assertEqual(gate["query_due_at"], "2026-09-17T12:15:00+00:00")
            self.assertEqual(gate["estimate_at"], "2026-09-17T12:30:00+00:00")
            self.assertEqual(result["schedule"]["next_check_at"], late)
            self.assertEqual(result["schedule"]["delay_minutes"], 0)
        # A new observation after the missed forecast anchors the unknown default.
        result = self.closed_at("2026-09-17T13:40:00+00:00")
        [gate] = result["schedule"]["gates"]
        self.assertEqual(gate["anchor"], "2026-09-17T13:40:00+00:00")
        self.assertEqual(gate["basis"], "no-estimate")
        self.assertIsNone(gate["estimate_at"])
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T14:40:00+00:00")
        self.assertEqual(result["schedule"]["delay_minutes"], 60)

    def test_each_observation_tightens_toward_a_future_forecast(self) -> None:
        self.register(extra=("--expected-open-at", "2026-09-17T13:00:00+00:00"))
        # 60 minutes out: a quarter is 15 minutes.
        result = self.closed_at(T0)
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T12:15:00+00:00")
        # Observed again 44 minutes out: a quarter is 11, floored at 15.
        result = self.closed_at("2026-09-17T12:16:00+00:00")
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T12:31:00+00:00")
        self.assertEqual(result["schedule"]["gates"][0]["interval_minutes"], 15)
        # The refreshed observation is fresh: no request until the planned time.
        _, result, _ = cycle(self.store, "2026-09-17T12:20:00+00:00")
        self.assertEqual(result["observation_requests"], [])
        _, result, _ = cycle(self.store, "2026-09-17T12:31:00+00:00")
        self.assertEqual([r["reason"] for r in result["observation_requests"]], ["stale"])

    def test_explicit_interval_controls_the_query_time_over_hints_and_freshness(self) -> None:
        # A 5-minute requirement queries again while the prior observation is
        # still fresh; freshness is a maximum usable age, not a minimum cadence.
        self.register(extra=("--poll-interval-minutes", "5"))
        result = self.closed_at(T0, task_states=[self.idle()])
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T12:05:00+00:00")
        self.assertEqual(result["schedule"]["delay_minutes"], 5)
        [gate] = result["schedule"]["gates"]
        self.assertEqual((gate["cadence"], gate["interval_minutes"]), ("explicit", 5))
        _, result, _ = cycle(self.store, "2026-09-17T12:04:00+00:00")
        self.assertEqual(result["observation_requests"], [])
        _, result, _ = cycle(self.store, "2026-09-17T12:05:00+00:00")
        [request] = result["observation_requests"]
        self.assertEqual((request["reason"], request["cadence"], request["interval_minutes"]), ("due", "explicit", 5))
        _, inspected, _ = run("inspect", "--store", self.store, "--now", "2026-09-17T12:05:00+00:00")
        self.assertTrue(inspected["observations"][0]["fresh"], "requested while still fresh")
        # A fresh open observation still admits on its own terms, unchanged.
        _, result, _ = cycle(
            self.store, "2026-09-17T12:05:00+00:00",
            observations=[self.quota_observation(remaining=50, observed_at="2026-09-17T12:05:00+00:00")],
            task_states=[self.idle(observed_at="2026-09-17T12:05:00+00:00")],
        )
        self.assertEqual(len(result["wake_proposals"]), 1)
        # A 120-minute requirement overrides a forecast that would tighten to 15
        # and lets the stale closed observation wait until its planned query.
        self.fresh_store()
        self.register(
            extra=("--poll-interval-minutes", "120", "--expected-open-at", "2026-09-17T12:30:00+00:00")
        )
        result = self.closed_at(T0)
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T14:00:00+00:00")
        self.assertEqual(result["schedule"]["delay_minutes"], 120)
        self.assertEqual(result["schedule"]["gates"][0]["estimate_at"], "2026-09-17T12:30:00+00:00")
        for early in ("2026-09-17T12:15:00+00:00", "2026-09-17T13:00:00+00:00", "2026-09-17T13:59:00+00:00"):
            _, result, _ = cycle(self.store, early, task_states=[self.idle(observed_at=early)])
            self.assertEqual(result["observation_requests"], [], early)
            self.assert_no_wake(result, "gate-observation-stale")
            self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T14:00:00+00:00")
        _, result, _ = cycle(self.store, "2026-09-17T14:00:00+00:00")
        self.assertEqual([r["reason"] for r in result["observation_requests"]], ["stale"])

    def test_shared_gate_honors_the_earliest_registration_demand(self) -> None:
        self.register(task_id="task-1", extra=("--poll-interval-minutes", "120"))
        self.register(task_id="task-2")  # adaptive, no forecast: 60 minutes
        result = self.closed_at(T0)
        [gate] = result["schedule"]["gates"]
        self.assertEqual(gate["task_ids"], ["task-1", "task-2"])
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T13:00:00+00:00")
        self.assertEqual((gate["cadence"], gate["interval_minutes"]), ("adaptive", 60))
        # A third registration's forecast tightens the shared adaptive default.
        self.register(task_id="task-3", extra=("--expected-open-at", "2026-09-17T12:30:00+00:00"))
        _, result, _ = cycle(self.store, T0)
        [gate] = result["schedule"]["gates"]
        self.assertEqual(gate["estimate_at"], "2026-09-17T12:30:00+00:00")
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T12:15:00+00:00")
        # A 5-minute explicit requirement on the same gate wins outright, and one
        # request covers every task on the key.
        self.register(task_id="task-4", extra=("--poll-interval-minutes", "5"))
        _, result, _ = cycle(self.store, T0)
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T12:05:00+00:00")
        _, result, _ = cycle(self.store, "2026-09-17T12:05:00+00:00")
        [request] = result["observation_requests"]
        self.assertEqual(request["task_ids"], ["task-1", "task-2", "task-3", "task-4"])
        self.assertEqual(request["reason"], "due")

    def test_open_gate_with_waiting_targets_is_requeried_at_fifteen_minutes(self) -> None:
        self.register()
        # Open, but the target is running: the next query is when this
        # observation can no longer admit.
        _, result, _ = cycle(
            self.store, T0,
            observations=[self.quota_observation(remaining=50)],
            task_states=[self.idle(status="running")],
        )
        self.assert_no_wake(result, "task-running")
        [gate] = result["schedule"]["gates"]
        self.assertEqual((gate["observation"], gate["basis"]), ("open", "open"))
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T12:15:00+00:00")
        self.assertEqual(result["schedule"]["delay_minutes"], 15)
        _, result, _ = cycle(self.store, "2026-09-17T12:10:00+00:00", task_states=[self.idle(observed_at="2026-09-17T12:10:00+00:00")])
        self.assertEqual(result["observation_requests"], [], "fresh open reuse: it admits")
        self.assertEqual(len(result["wake_proposals"]), 1)
        # A stale open observation is due for a query and never authorizes a wake.
        self.fresh_store()
        self.register()
        _, result, _ = cycle(
            self.store, T0,
            observations=[self.quota_observation(remaining=50, observed_at="2026-09-17T11:40:00+00:00")],
            task_states=[self.idle()],
        )
        self.assert_no_wake(result, "gate-observation-stale")
        self.assertEqual([r["reason"] for r in result["observation_requests"]], ["stale"])
        self.assertEqual(result["schedule"]["reason"], "gate-due")
        self.assertEqual(result["schedule"]["delay_minutes"], 0)

    def test_backoff_and_planned_query_use_the_later_bound(self) -> None:
        self.register(extra=("--expected-open-at", "2026-09-17T17:00:00+00:00"))
        key = self.gate_key()

        def error_at(now: str):
            _, result, err = cycle(
                self.store, now,
                observations=[{"gate_key": key, "status": "error", "observed_at": now, "reason": "error:codex-timeout"}],
            )
            self.assertIsNotNone(result, err)
            return result

        # Errors only: no anchor, so the backoff retry is the whole bound.
        result = error_at(T0)
        self.assertEqual(result["schedule"]["reason"], "backoff")
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T12:15:00+00:00")
        [gate] = result["schedule"]["gates"]
        self.assertEqual((gate["anchor"], gate["backoff_until"], gate["due"]), (None, "2026-09-17T12:15:00+00:00", False))
        _, result, _ = cycle(self.store, "2026-09-17T12:14:59+00:00")
        self.assertEqual(result["observation_requests"], [])
        _, result, _ = cycle(self.store, "2026-09-17T12:15:00+00:00")
        self.assertEqual([r["reason"] for r in result["observation_requests"]], ["unobserved"])
        # A success anchors the plan (285 minutes out: a quarter is 71, so
        # 13:26) and clears the backoff; a later error's 15-minute retry ends
        # before that plan, so the plan holds.
        result = self.closed_at("2026-09-17T12:15:00+00:00")
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T13:26:00+00:00")
        result = error_at("2026-09-17T12:30:00+00:00")
        self.assertEqual(result["schedule"]["reason"], "gate-query")
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T13:26:00+00:00")
        # A retry that ends after the plan is the later bound.
        result = error_at("2026-09-17T13:20:00+00:00")
        self.assertEqual(result["schedule"]["gates"][0]["backoff_until"], "2026-09-17T13:50:00+00:00")
        self.assertEqual(result["schedule"]["reason"], "backoff")
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T13:50:00+00:00")
        _, result, _ = cycle(self.store, "2026-09-17T13:30:00+00:00")
        self.assertEqual(result["observation_requests"], [], "inside the backoff window")
        _, result, _ = cycle(self.store, "2026-09-17T13:50:00+00:00")
        self.assertEqual([r["reason"] for r in result["observation_requests"]], ["stale"])

    def test_near_expiry_is_not_rounded_later_by_the_adaptive_floor(self) -> None:
        self.register(extra=("--expires-in-minutes", "20"))
        result = self.closed_at(T0)
        [gate] = result["schedule"]["gates"]
        self.assertEqual(gate["query_due_at"], "2026-09-17T13:00:00+00:00")
        self.assertEqual(result["schedule"]["reason"], "registration-expiry")
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T12:20:00+00:00")
        self.assertEqual(result["schedule"]["delay_minutes"], 20)
        # At expiry the registration is stuck work, and nothing waits any more.
        _, result, _ = cycle(self.store, "2026-09-17T12:20:00+00:00")
        self.assertEqual(result["observation_requests"], [])
        self.assertEqual([a["status"] for a in result["attention"]], ["expired"])
        self.assertEqual(result["schedule"]["gates"], [])

    def notice(self, now: str) -> dict[str, Any]:
        code, payload, err = run("notice", "--store", self.store, "--now", now)
        self.assertEqual(code, 0, err)
        return payload

    def test_recovery_liveness_and_restart_reconstruct_from_the_store(self) -> None:
        # An empty registry needs only a liveness check.
        empty = self.notice("2026-09-17T12:00:00+00:00")
        self.assertFalse(empty["report"])
        self.assertEqual(empty["schedule"]["reason"], "liveness")
        self.assertEqual(empty["schedule"]["next_check_at"], "2026-09-17T18:00:00+00:00")
        self.assertEqual(empty["schedule"]["delay_minutes"], 360)
        # A reservation the monitor has not reported is a 15-minute recovery,
        # immediately in the cycle that made it.
        self.register()
        [proposal] = self.propose()
        _, inspected, _ = run("inspect", "--store", self.store, "--now", "2026-09-17T12:01:00+00:00")
        self.assertEqual(inspected["schedule"]["reason"], "reservation-unrelayed")
        self.assertEqual(inspected["schedule"]["next_check_at"], "2026-09-17T12:16:00+00:00")
        self.assertEqual(inspected["schedule"]["registry"]["counts"]["reserved"], 1)
        # The monitor crashes; a new process reads the same recommendation.
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "inspect", "--store", self.store, "--now", "2026-09-17T12:01:00+00:00"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["schedule"], inspected["schedule"])
        # notice selects the stuck reservation; while it is pending, recovery
        # stays bounded at 15 minutes from the read.
        first = self.notice("2026-09-17T12:16:00+00:00")
        self.assertTrue(first["report"])
        self.assertEqual(first["schedule"]["reason"], "notice-pending")
        self.assertEqual(first["schedule"]["next_check_at"], "2026-09-17T12:31:00+00:00")
        replay = self.notice("2026-09-17T12:40:00+00:00")
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["schedule"]["next_check_at"], "2026-09-17T12:55:00+00:00")
        # Acknowledged, the reservation is attention-only: a liveness check.
        code, acked, err = run(
            "acknowledge", "--store", self.store, "--notice-id", first["notice_id"],
            "--now", "2026-09-17T12:41:00+00:00",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(acked["schedule"]["reason"], "liveness")
        self.assertEqual(acked["schedule"]["next_check_at"], "2026-09-17T18:41:00+00:00")
        self.assertEqual(acked["schedule"]["registry"]["attention"], 1)
        self.assertFalse(acked["schedule"]["registry"]["pending_notice"])
        quiet = self.notice("2026-09-17T12:42:00+00:00")
        self.assertFalse(quiet["report"])
        self.assertEqual(quiet["schedule"]["reason"], "liveness")

    def owner(self, command: str, rid: str, now: str, *extra: str) -> dict[str, Any]:
        code, payload, err = run(
            command, "--store", self.store, "--registration-id", rid, "--owner",
            "owner-a", *extra, "--now", now,
        )
        self.assertEqual(code, 0, err)
        return payload

    def test_owner_commands_carry_the_schedule_and_recompute_on_change(self) -> None:
        registered = self.register(extra=("--expires-in-minutes", "4320"))
        rid = registered["registration_id"]
        # Unobserved: the new registration is due now, so the owner's output
        # already says the heartbeat must come forward to now.
        self.assertEqual(registered["schedule"]["reason"], "gate-due")
        self.assertEqual(registered["schedule"]["delay_minutes"], 0)
        result = self.closed_at(T0)
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T13:00:00+00:00")
        fingerprint = result["schedule"]["registry"]["fingerprint"]
        _, inspected, _ = run("inspect", "--store", self.store, "--now", "2026-09-17T12:10:00+00:00")
        self.assertEqual(inspected["schedule"]["registry"]["fingerprint"], fingerprint, "same inputs, same digest")
        # An earlier forecast brings the planned check forward from the same
        # anchor (40 minutes out: a quarter is 10, floored at 15) and changes
        # the digest a fresh state check compares against.
        updated = self.owner("update", rid, "2026-09-17T12:10:00+00:00", "--expected-open-at", "2026-09-17T12:40:00+00:00")
        self.assertEqual(updated["schedule"]["next_check_at"], "2026-09-17T12:15:00+00:00")
        self.assertEqual(updated["schedule"]["delay_minutes"], 5)
        self.assertNotEqual(updated["schedule"]["registry"]["fingerprint"], fingerprint)
        # An explicit interval already elapsed since the anchor is due now.
        updated = self.owner("update", rid, "2026-09-17T12:10:00+00:00", "--poll-interval-minutes", "5")
        self.assertEqual(updated["schedule"]["reason"], "gate-due")
        self.assertEqual(updated["schedule"]["gates"][0]["query_due_at"], "2026-09-17T12:05:00+00:00")
        # Paused, nothing waits; resumed, the same anchor still makes it due.
        paused = self.owner("pause", rid, "2026-09-17T12:10:00+00:00")
        self.assertEqual(paused["schedule"]["reason"], "liveness")
        self.assertEqual(paused["schedule"]["next_check_at"], "2026-09-17T18:10:00+00:00")
        self.assertEqual(paused["schedule"]["gates"], [])
        resumed = self.owner("resume", rid, "2026-09-17T12:10:00+00:00")
        self.assertEqual(resumed["schedule"]["reason"], "gate-due")
        removed = self.owner("remove", rid, "2026-09-17T12:10:00+00:00")
        self.assertEqual(removed["schedule"]["reason"], "liveness")

    def test_malformed_stored_metadata_is_corrupt_store_and_legacy_records_read_adaptive(
        self,
    ) -> None:
        rid = self.register(
            extra=("--expected-open-at", "2026-09-17T13:00:00+00:00", "--poll-interval-minutes", "30")
        )["registration_id"]
        self.closed_at(T0)
        state_path = Path(self.store) / "state.json"
        good = state_path.read_bytes()
        secret = "SYNTHETIC-META-SECRET-2e9a"

        def mutate(change) -> bytes:
            state = json.loads(good.decode("utf-8"))
            change(state)
            state_path.write_text(json.dumps(state), encoding="utf-8")
            return state_path.read_bytes()

        cases = (
            ("forecast that is not a time", lambda s: s["registrations"][rid].update(expected_open_at=secret)),
            ("forecast without offset", lambda s: s["registrations"][rid].update(expected_open_at="2026-09-17T13:00:00")),
            ("interval that is not a number", lambda s: s["registrations"][rid].update(poll_interval_minutes=secret)),
            ("interval of zero", lambda s: s["registrations"][rid].update(poll_interval_minutes=0)),
            ("interval past a week", lambda s: s["registrations"][rid].update(poll_interval_minutes=10081)),
            ("boolean interval", lambda s: s["registrations"][rid].update(poll_interval_minutes=True)),
        )
        for label, change in cases:
            with self.subTest(label=label):
                malformed = mutate(change)
                for command in ("inspect", "cycle", "notice"):
                    code, payload, err = run(command, "--store", self.store, "--now", T0)
                    self.assertEqual(code, 2, command)
                    self.assertIsNone(payload)
                    self.assertIn("aeon bell: corrupt-store:", err)
                    self.assertNotIn(secret, err)
                    self.assertNotIn("Traceback", err)
                self.assertEqual(state_path.read_bytes(), malformed, "nothing is rewritten")
        # A record written before the fields existed reads as null and adaptive,
        # and schedules the unknown default from its anchor.
        mutate(
            lambda s: [
                s["registrations"][rid].pop("expected_open_at"),
                s["registrations"][rid].pop("poll_interval_minutes"),
            ]
        )
        code, inspected, err = run("inspect", "--store", self.store, "--now", T0)
        self.assertEqual(code, 0, err)
        [entry] = inspected["registrations"]
        self.assertIsNone(entry["expected_open_at"])
        self.assertIsNone(entry["poll_interval_minutes"])
        self.assertEqual(inspected["schedule"]["gates"][0]["cadence"], "adaptive")
        self.assertEqual(inspected["schedule"]["next_check_at"], "2026-09-17T13:00:00+00:00")

    def test_configuration_gap_defers_to_the_liveness_bound_but_is_still_requested(self) -> None:
        self.register()
        key = self.gate_key()
        _, plan, _ = cycle(self.store, "2026-09-17T12:00:05+00:00")
        self.assertEqual([r["reason"] for r in plan["observation_requests"]], ["unobserved"])
        self.assertEqual(plan["schedule"]["reason"], "gate-due")
        report = Path(self._tmp.name) / "tick-report.json"
        report.write_text(
            json.dumps(
                {
                    "adapter": "praxis-aeon-bell-codex-status",
                    "gates": [{"gate_key": key, "kind": "quota_recovery", "outcome": "unhandled", "reason": "binding-labels-differ"}],
                }
            ),
            encoding="utf-8",
        )
        code, notice, err = run(
            "notice", "--store", self.store, "--adapter-report", str(report), "--now", "2026-09-17T12:00:10+00:00"
        )
        self.assertEqual(code, 0, err)
        self.assertTrue(notice["report"])
        self.assertEqual(notice["schedule"]["reason"], "notice-pending")
        code, acked, err = run(
            "acknowledge", "--store", self.store, "--notice-id", notice["notice_id"], "--now", "2026-09-17T12:00:11+00:00"
        )
        self.assertEqual(code, 0, err)
        # No binding owns the gate: asking again sooner cannot help, so the next
        # check is the liveness bound rather than an immediate rerun.
        self.assertEqual(acked["schedule"]["reason"], "configuration-gap")
        self.assertEqual(acked["schedule"]["next_check_at"], "2026-09-17T18:00:11+00:00")
        [gate] = acked["schedule"]["gates"]
        self.assertTrue(gate["due"])
        self.assertTrue(gate["configuration_gap"])
        # Whenever a tick does run, the gate is requested again.
        _, plan, _ = cycle(self.store, "2026-09-17T12:30:00+00:00")
        self.assertEqual([r["reason"] for r in plan["observation_requests"]], ["unobserved"])
        # Once a binding observes it, the plan anchors normally.
        result = self.closed_at("2026-09-17T12:30:00+00:00")
        self.assertEqual(result["schedule"]["reason"], "gate-query")
        self.assertEqual(result["schedule"]["next_check_at"], "2026-09-17T13:30:00+00:00")


def proposal_digest(proposal: dict[str, Any]) -> str:
    [send] = [s for s in proposal["native_steps"] if s["step"] == "send"]
    return aeon_bell.hashlib.sha256(
        send["arguments"]["message"].encode("utf-8")
    ).hexdigest()


class Diagnostics(CycleHelpers):
    def test_store_is_private_by_default(self) -> None:
        self.register()
        self.assertEqual(stat.S_IMODE(os.stat(self.store).st_mode), 0o700)
        self.assertEqual(
            stat.S_IMODE(os.stat(Path(self.store) / "state.json").st_mode), 0o600
        )

    def test_corrupt_store_and_malformed_input_are_reported_without_echo(self) -> None:
        self.register()
        secret = "SYNTHETIC-SECRET-VALUE-9f3c"
        Path(self.store, "state.json").write_text(
            '{"registrations": ' + secret, encoding="utf-8"
        )
        code, payload, err = run("inspect", "--store", self.store, "--now", T0)
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("corrupt-store", err)
        self.assertNotIn(secret, err)
        Path(self.store, "state.json").unlink()
        self.register()
        bad_input = Path(self._tmp.name) / "bad.json"
        bad_input.write_text('{"observations": [' + secret, encoding="utf-8")
        code, payload, err = run(
            "cycle", "--store", self.store, "--input", str(bad_input), "--now", T0
        )
        self.assertEqual(code, 2)
        self.assertIn("invalid-input", err)
        self.assertNotIn(secret, err)
        # A typed observation carrying an unexpected field (such as a credential) is
        # rejected without echoing the value, and the observation is not stored.
        leaky = self.quota_observation(remaining=50, token=secret)
        code, payload, err = cycle(
            self.store, T0, observations=[leaky], task_states=[self.idle()]
        )
        self.assertEqual(code, 2)
        self.assertIn("invalid-observation", err)
        self.assertNotIn(secret, err)
        self.assertNotIn(
            secret, Path(self.store, "state.json").read_text(encoding="utf-8")
        )
        _, inspected, _ = run("inspect", "--store", self.store, "--now", T0)
        self.assertEqual(inspected["observations"], [])
        # Bad registration inputs are rejected at the seam.
        code, _, err = run(
            "register",
            "--store",
            self.store,
            "--owner",
            "owner-a",
            "--host",
            "host-a",
            "--task-id",
            "task-9",
            "--episode",
            "e",
            "--gate-json",
            '{"kind": "shell"}',
            "--continuation",
            "x",
            "--now",
            T0,
        )
        self.assertEqual(code, 2)
        self.assertIn("invalid-gate", err)

    def test_malformed_registry_records_fail_every_command_as_corrupt_store_without_echo(
        self,
    ) -> None:
        # One malformed record per store container. The engine indexes these
        # fields directly, so each is refused at the store's read boundary with
        # the documented code, no echo, no traceback, and nothing rewritten;
        # records written before the optional fields existed still read.
        rid = self.register(task_id="task-1")["registration_id"]
        other = self.register(task_id="task-2", gate=dict(QUOTA_GATE, bucket="daily"))
        key, other_key = self.gate_key(), other["gate_key"]
        at = "2026-09-17T12:00:05+00:00"
        code, result, err = cycle(
            self.store, at,
            observations=[
                self.quota_observation(remaining=50, observed_at=at),
                {"gate_key": other_key, "status": "error", "observed_at": at, "reason": "error:codex-timeout"},
            ],
            task_states=[self.idle(observed_at=at)],
        )
        self.assertEqual(code, 0, err)
        [proposal] = result["wake_proposals"]
        state_path = Path(self.store) / "state.json"
        good = state_path.read_bytes()
        secret = "SYNTHETIC-RECORD-SECRET-7a2c"

        def mutate(change) -> bytes:
            state = json.loads(good.decode("utf-8"))
            change(state)
            state_path.write_text(json.dumps(state), encoding="utf-8")
            return state_path.read_bytes()

        cases = (
            ("registration status", lambda s: s["registrations"][rid].update(status=secret)),
            ("registration field missing", lambda s: s["registrations"][rid].pop("expires_at")),
            ("observation field missing", lambda s: s["observations"][key].pop("binding_digest")),
            ("retry schedule reason missing", lambda s: s["retry_schedule"][other_key].pop("last_reason")),
            ("attempt status", lambda s: s["attempts"][proposal["attempt_id"]].update(status=secret)),
            ("attempt names no registration", lambda s: s["attempts"][proposal["attempt_id"]].update(registration_id=secret)),
        )
        later = "2026-09-17T12:15:00+00:00"
        for label, change in cases:
            with self.subTest(label=label):
                malformed = mutate(change)
                for command in ("inspect", "cycle", "notice"):
                    code, payload, err = run(command, "--store", self.store, "--now", later)
                    self.assertEqual(code, 2, command)
                    self.assertIsNone(payload)
                    self.assertIn("aeon bell: corrupt-store:", err)
                    self.assertNotIn(secret, err)
                    self.assertNotIn("Traceback", err)
                self.assertEqual(state_path.read_bytes(), malformed, "nothing is rewritten")
        # The same schedule shape driven through the CLI as a monitor tick runs it.
        mutate(lambda s: s["retry_schedule"][other_key].pop("last_reason"))
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "notice", "--store", self.store, "--now", later],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertEqual(completed.stdout, "")
        self.assertNotIn("Traceback", completed.stderr)
        self.assertIn("aeon bell: corrupt-store:", completed.stderr)

        def legacy(state: dict) -> None:
            for record in state["registrations"].values():
                for name in ("episodes", "attempt_count", "unresolved_reason"):
                    record.pop(name, None)
                if record.get("attempt_id") is None:
                    record.pop("attempt_id", None)
            for attempt in state["attempts"].values():
                for name in ("gate", "evidence", "reconciliation_evidence"):
                    attempt.pop(name, None)

        mutate(legacy)
        for command in ("inspect", "cycle", "notice"):
            code, payload, err = run(command, "--store", self.store, "--now", later)
            self.assertEqual(code, 0, (command, err))
        _, inspected, _ = run("inspect", "--store", self.store, "--now", later)
        self.assertEqual([r["status"] for r in inspected["registrations"]], ["reserved", "waiting"])
        [entry] = inspected["attention"]
        self.assertEqual((entry["status"], entry["attempt_id"]), ("reserved", proposal["attempt_id"]))


class DirectedTick(CycleHelpers):
    """The engine-directed tick: the engine issues every action with bound
    arguments and the monitor submits typed results; every case runs through
    the public tick commands with synthetic native results."""

    HEARTBEAT = "monitor-heartbeat-1"

    def tick_start(self, now: str | None, *extra: str) -> tuple[int, Any, str]:
        argv = ["tick", "start", "--store", self.store, *extra]
        if now is not None:
            argv += ["--now", now]
        return run(*argv)

    def start(self, now: str | None = T0, *extra: str, heartbeat: bool = True) -> dict:
        args = list(extra)
        if heartbeat:
            args += ["--heartbeat", self.HEARTBEAT]
        code, view, err = self.tick_start(now, *args)
        self.assertEqual(code, 0, err)
        return view

    def submit(
        self, view: dict, result: Any, now: str | None = None, **extra: Any
    ) -> tuple[int, Any, str]:
        pending = view["pending_action"]
        argv = [
            "tick", "submit", "--store", self.store,
            "--tick-id", view["tick"]["tick_id"],
            "--action-id", extra.pop("action_id", pending["action_id"] if pending else "none"),
            "--result-json", json.dumps(result),
        ]
        if now is not None:
            argv += ["--now", now]
        return run(*argv)

    def submit_ok(self, view: dict, result: Any, now: str | None = None) -> dict:
        code, next_view, err = self.submit(view, result, now)
        self.assertEqual(code, 0, err)
        return next_view

    def status(self, now: str | None = None) -> dict:
        argv = ["tick", "status", "--store", self.store]
        if now is not None:
            argv += ["--now", now]
        code, view, err = run(*argv)
        self.assertEqual(code, 0, err)
        return view

    def pending(self, view: dict, kind: str, purpose: str | None = None) -> dict:
        action = view["pending_action"]
        self.assertIsNotNone(action, "an action must be pending")
        self.assertEqual(action["kind"], kind, action)
        if purpose is not None:
            self.assertEqual(action["purpose"], purpose, action)
        return action

    def applied(self, action: dict, next_run_at: str | None = None) -> dict:
        return {
            "applied": True,
            "next_run_at": action["arguments"]["target_at"] if next_run_at is None else next_run_at,
        }

    @staticmethod
    def read(status: str, observed_at: str) -> dict:
        return {"status": status, "observed_at": observed_at}

    def test_cached_open_observation_wakes_through_the_directed_tick(self) -> None:
        # The previously missed case: a fresh open observation is cached, no
        # query is due, and the target is idle. The old recipe let a monitor
        # skip the result cycle here; the directed tick cannot.
        rid = self.register()["registration_id"]
        _, planned, err = cycle(
            self.store, T0,
            observations=[self.quota_observation(remaining=50)],
            task_states=[self.idle(status="running")],
        )
        self.assertIsNotNone(planned, err)
        self.assertEqual([s["reason"] for s in planned["skipped"]], ["task-running"])
        at = "2026-09-17T12:05:00+00:00"
        view = self.start(at)
        tick = view["tick"]
        self.assertEqual(tick["status"], "running")
        self.assertEqual(tick["time_mode"], "supplied")
        self.assertEqual(tick["heartbeat"], self.HEARTBEAT)
        self.assertEqual(tick["registration_order"], [rid])
        self.assertEqual(tick["phase"], "task_states")
        self.assertTrue(view["schedule"]["registry"]["tick_in_progress"])
        self.assertTrue(view["schedule"]["registry"]["tick_readable"])
        read = self.pending(view, "task_read", "task-state")
        self.assertEqual(
            {k: read["arguments"][k] for k in ("host", "task_id", "registration_id", "episode")},
            {"host": "host-a", "task_id": "task-1", "registration_id": rid, "episode": "episode-1"},
        )
        self.assertIsNone(read["arguments"]["attempt_id"])
        self.assertIsNone(read["require"])
        self.assertEqual(read["restart"], "resumable")
        self.assertEqual(read["failure_form"]["disposition"], "not_performed|failed|unavailable")
        # A second start is refused while this tick runs.
        code, _, err = self.tick_start(at, "--heartbeat", self.HEARTBEAT)
        self.assertEqual(code, 2)
        self.assertIn("tick-in-progress", err)
        view = self.submit_ok(view, self.read("idle", at), at)
        self.assertEqual(view["last_result"]["consequence"], "task-state-recorded")
        self.assertEqual(view["tick"]["actions"][0]["disposition"], "performed")
        self.assertEqual(view["tick"]["actions"][0]["recorded"], {"status": "idle"})
        # No query is due (fresh cached open observation): observe is not
        # issued, and the result cycle still runs: the pre-send read is bound
        # to the reservation the engine just made.
        self.assertFalse(view["tick"]["observe"]["issued"])
        self.assertEqual(view["tick"]["observe"]["not_issued_reason"], "no-request")
        self.assertEqual(view["tick"]["requested_gate_keys"], [])
        self.assertEqual(view["tick"]["phase"], "dispatch")
        pre = self.pending(view, "task_read", "pre-send")
        self.assertEqual(pre["require"], {"status": "idle", "episode": "episode-1"})
        attempt_id = pre["arguments"]["attempt_id"]
        self.assertRegex(attempt_id, r"^[0-9a-f]{24}$")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        self.assertEqual(inspected["registrations"][0]["status"], "reserved")
        self.assertEqual(inspected["registrations"][0]["attempt_id"], attempt_id)
        self.assertEqual([p["attempt_id"] for p in view["tick"]["proposals"]], [attempt_id])
        self.assertNotIn("message", view["tick"]["proposals"][0])
        view = self.submit_ok(view, self.read("idle", at), at)
        send = self.pending(view, "send", "wake")
        self.assertEqual(send["restart"], "abandon-only")
        args = send["arguments"]
        self.assertEqual(args["tool"], "send_follow_up")
        self.assertEqual((args["host"], args["task_id"], args["episode"]), ("host-a", "task-1", "episode-1"))
        self.assertEqual((args["attempt_id"], args["registration_id"]), (attempt_id, rid))
        self.assertIsNone(args["model_override"])
        self.assertIsNone(args["effort_override"])
        self.assertIn("Continue the bounded work.", args["message"])
        digest = aeon_bell.hashlib.sha256(args["message"].encode("utf-8")).hexdigest()
        self.assertEqual(args["message_sha256"], digest)
        self.assertEqual(inspected["unresolved_attempts"][0]["attempt_id"], attempt_id)
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        self.assertEqual(inspected["schedule"]["registry"]["tick_in_progress"], True)
        code, _, err = self.tick_start(at, "--heartbeat", self.HEARTBEAT)
        self.assertEqual(code, 2)
        self.assertIn("tick-in-progress", err)
        view = self.submit_ok(view, {"outcome": "accepted", "evidence": {"tool": "accepted"}}, at)
        self.assertEqual(view["last_result"]["consequence"], "attempt-accepted")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        self.assertEqual(inspected["registrations"][0]["status"], "completed")
        self.assertEqual(inspected["registrations"][0]["completed_episodes"], ["episode-1"])
        self.assertEqual(
            view["tick"]["dispatch"]["attempts"],
            [{"attempt_id": attempt_id, "registration_id": rid, "stage": "send", "result": "accepted"}],
        )
        # The notice carries the one accepted event and is emitted verbatim.
        emit = self.pending(view, "emit", "notice")
        self.assertEqual(emit["arguments"]["channel"], "notice")
        self.assertFalse(emit["arguments"]["replayed"])
        notice_id = emit["arguments"]["notice_id"]
        self.assertRegex(notice_id, r"^[0-9a-f]{24}$")
        self.assertIn(f"attempt {attempt_id}", emit["arguments"]["text"])
        self.assertIn("accepted_by_native_send_tool", emit["arguments"]["text"])
        self.assertNotIn("host-a", emit["arguments"]["text"])
        view = self.submit_ok(view, {"emitted": True}, at)
        self.assertEqual(view["last_result"]["consequence"], "notice-acknowledged")
        self.assertEqual(view["tick"]["notice"]["acknowledged"], True)
        # Scheduling: one heartbeat_set bound to the configured reference.
        heartbeat = self.pending(view, "heartbeat_set", "schedule")
        self.assertEqual(heartbeat["arguments"]["heartbeat"], self.HEARTBEAT)
        self.assertEqual(heartbeat["arguments"]["write_number"], 1)
        self.assertEqual(heartbeat["arguments"]["rule"], "schedule-as-printed")
        self.assertEqual(heartbeat["arguments"]["fingerprint"], view["schedule"]["registry"]["fingerprint"])
        self.assertEqual(heartbeat["arguments"]["target_at"], view["schedule"]["next_check_at"])
        self.assertEqual(heartbeat["restart"], "abandon-only")
        final = self.submit_ok(view, self.applied(heartbeat), at)
        self.assertIsNone(final["pending_action"])
        self.assertEqual(final["tick"]["status"], "complete")
        self.assertEqual(final["tick"]["phase"], "done")
        outcome = final["outcome_when_complete"]
        self.assertEqual(outcome["wakes"], [{"attempt_id": attempt_id, "registration_id": rid, "result": "accepted"}])
        self.assertEqual(outcome["notice"], {"notice_id": notice_id, "acknowledged": True, "replayed": False})
        self.assertEqual(outcome["heartbeat"]["result"], "applied")
        self.assertEqual(outcome["heartbeat"]["writes"], 1)
        self.assertTrue(outcome["printed_anything"])
        self.assertEqual(
            [a["disposition"] for a in final["tick"]["actions"]],
            ["performed"] * 5,
        )
        self.assertIn("results_are_caller_assertions", " ".join(final["limitations"]))
        # Afterwards nothing is pending and the summary is durable.
        after = self.status(at)
        self.assertIsNone(after["tick"])
        self.assertIsNone(after["pending_action"])
        self.assertEqual(after["last"]["tick_id"], final["tick"]["tick_id"])
        self.assertEqual(after["last"]["status"], "complete")
        self.assertFalse(after["schedule"]["registry"]["tick_in_progress"])
        _, quiet, _ = run("notice", "--store", self.store, "--now", at)
        self.assertFalse(quiet["report"], "the event was acknowledged by the tick")

    def complete_quietly(self, view: dict, at: str) -> dict:
        """Drive a tick that should issue no send and no notice to completion."""
        while view["pending_action"] is not None:
            action = view["pending_action"]
            if action["kind"] == "task_read":
                self.fail(f"unexpected task_read {action['purpose']}")
            self.assertNotEqual(action["kind"], "send", "no wake expected")
            self.assertNotEqual((action["kind"], action["purpose"]), ("emit", "notice"))
            if action["kind"] == "emit":
                view = self.submit_ok(view, {"emitted": True}, at)
            else:
                view = self.submit_ok(view, self.applied(action), at)
        return view

    def test_no_query_due_is_not_no_processing(self) -> None:
        # Same cached open observation, but the target is still running at the
        # task-state read: nothing is sent, the skip is recorded, and the
        # heartbeat is set as the schedule prints it (the open observation's
        # freshness end).
        rid = self.register()["registration_id"]
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        at = "2026-09-17T12:05:00+00:00"
        view = self.start(at)
        view = self.submit_ok(view, self.read("running", at), at)
        self.assertEqual(view["tick"]["observe"]["not_issued_reason"], "no-request")
        self.assertEqual(view["tick"]["dispatch"]["skipped"], [{"registration_id": rid, "reason": "task-running"}])
        self.assertEqual(view["tick"]["proposals"], [])
        heartbeat = self.pending(view, "heartbeat_set", "schedule")
        self.assertEqual(heartbeat["arguments"]["rule"], "schedule-as-printed")
        self.assertEqual(heartbeat["arguments"]["basis"]["schedule_reason"], "gate-query")
        self.assertEqual(heartbeat["arguments"]["target_at"], "2026-09-17T12:15:00+00:00")
        self.assertEqual(heartbeat["arguments"]["delay_minutes"], 10)
        final = self.submit_ok(view, self.applied(heartbeat), at)
        self.assertEqual(final["tick"]["status"], "complete")
        self.assertEqual([a["kind"] for a in final["tick"]["actions"]], ["task_read", "heartbeat_set"])
        outcome = final["outcome_when_complete"]
        self.assertEqual(outcome["wakes"], [])
        self.assertEqual(outcome["notice"]["notice_id"], None)
        self.assertFalse(outcome["printed_anything"])
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        self.assertEqual(inspected["registrations"][0]["status"], "waiting")
        self.assertEqual(inspected["registrations"][0]["attempt_count"], 0)

    def test_cached_closed_observation_and_empty_registry_are_quiet(self) -> None:
        # A fresh closed cached observation: no query, no wake, no notice, one
        # heartbeat_set at the planned query.
        self.register()
        cycle(self.store, T0, observations=[self.quota_observation(remaining=0)])
        at = "2026-09-17T12:05:00+00:00"
        view = self.start(at)
        view = self.submit_ok(view, self.read("idle", at), at)
        self.assertEqual(view["tick"]["observe"]["not_issued_reason"], "no-request")
        self.assertEqual([s["reason"] for s in view["tick"]["dispatch"]["skipped"]], ["gate-closed"])
        heartbeat = self.pending(view, "heartbeat_set")
        self.assertEqual(heartbeat["arguments"]["target_at"], "2026-09-17T13:00:00+00:00")
        final = self.complete_quietly(view, at)
        self.assertEqual(final["tick"]["status"], "complete")
        self.assertFalse(final["outcome_when_complete"]["printed_anything"])
        self.assertEqual(final["tick"]["diagnostics"], [])
        # An empty, not-yet-created registry: the tick issues only the
        # heartbeat (liveness) and creates the private store.
        empty = str(Path(self._tmp.name) / "empty-store")
        code, view, err = run(
            "tick", "start", "--store", empty, "--heartbeat", self.HEARTBEAT, "--now", at
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(stat.S_IMODE(os.stat(empty).st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(os.stat(Path(empty) / "state.json").st_mode), 0o600)
        self.assertEqual(view["tick"]["registration_order"], [])
        self.assertEqual(view["tick"]["observe"]["not_issued_reason"], "no-request")
        heartbeat = self.pending(view, "heartbeat_set", "schedule")
        self.assertEqual(heartbeat["arguments"]["rule"], "schedule-as-printed")
        self.assertEqual(heartbeat["arguments"]["basis"]["schedule_reason"], "liveness")
        self.assertEqual(heartbeat["arguments"]["delay_minutes"], 360)
        self.assertEqual([a["kind"] for a in view["tick"]["actions"]], ["heartbeat_set"])
        code, final, err = run(
            "tick", "submit", "--store", empty, "--tick-id", view["tick"]["tick_id"],
            "--action-id", heartbeat["action_id"],
            "--result-json", json.dumps(self.applied(heartbeat)), "--now", at,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(final["tick"]["status"], "complete")
        self.assertIsNone(final["pending_action"])
        self.assertFalse(final["outcome_when_complete"]["printed_anything"])
        self.assertEqual(final["outcome_when_complete"]["heartbeat"]["result"], "applied")
        self.assertFalse(os.path.exists(Path(empty) / "ticks"), "no artifacts without observe")

    def test_heartbeat_unconfigured_missing_control_and_off_target_are_reported(self) -> None:
        self.register()
        cycle(self.store, T0, observations=[self.quota_observation(remaining=0)])
        at = "2026-09-17T12:05:00+00:00"
        # No --heartbeat: no heartbeat_set is issued; the tick says so once in
        # its diagnostics and claims no coverage anywhere.
        view = self.start(at, heartbeat=False)
        self.assertIsNone(view["tick"]["heartbeat"])
        view = self.submit_ok(view, self.read("idle", at), at)
        emit = self.pending(view, "emit", "diagnostics")
        self.assertEqual(
            emit["arguments"]["text"],
            "aeon bell: heartbeat-unconfigured: no $HEARTBEAT is configured; next check "
            "2026-09-17T13:00:00+00:00 not applied",
        )
        self.assertEqual([a["kind"] for a in view["tick"]["actions"]], ["task_read", "emit"])
        final = self.submit_ok(view, {"emitted": True}, at)
        self.assertEqual(final["tick"]["status"], "complete")
        heartbeat = final["outcome_when_complete"]["heartbeat"]
        self.assertEqual((heartbeat["issued"], heartbeat["result"], heartbeat["writes"]), (False, "not-issued", 0))
        self.assertNotIn("coverage", json.dumps(final))
        # The control is missing: one write attempted, the failure recorded
        # verbatim, no second write, no invented cadence.
        view = self.start(at)
        view = self.submit_ok(view, self.read("idle", at), at)
        first = self.pending(view, "heartbeat_set")
        view = self.submit_ok(view, {"disposition": "unavailable", "reason": "cannot set next run"}, at)
        self.assertEqual(view["last_result"]["disposition"], "unavailable")
        self.assertEqual(view["last_result"]["consequence"], "heartbeat-control-failed")
        emit = self.pending(view, "emit", "diagnostics")
        self.assertEqual(
            emit["arguments"]["text"],
            "aeon bell: heartbeat-control: unavailable: cannot set next run",
        )
        final = self.submit_ok(view, {"emitted": True}, at)
        self.assertEqual([a["kind"] for a in final["tick"]["actions"]], ["task_read", "heartbeat_set", "emit"])
        heartbeat = final["outcome_when_complete"]["heartbeat"]
        self.assertEqual((heartbeat["writes"], heartbeat["result"], heartbeat["reason"]), (1, "unavailable", "cannot set next run"))
        self.assertIsNone(heartbeat["fingerprint_applied_from"])
        self.assertEqual(final["tick"]["heartbeat_writes"][0]["target_at"], first["arguments"]["target_at"])
        # Applied four minutes after the chosen target: recorded, reported, done.
        view = self.start(at)
        view = self.submit_ok(view, self.read("idle", at), at)
        action = self.pending(view, "heartbeat_set")
        view = self.submit_ok(view, self.applied(action, "2026-09-17T13:04:00+00:00"), at)
        self.assertEqual(view["last_result"]["disposition"], "performed")
        self.assertEqual(view["last_result"]["consequence"], "heartbeat-applied-off-target")
        emit = self.pending(view, "emit", "diagnostics")
        self.assertEqual(
            emit["arguments"]["text"],
            "aeon bell: heartbeat-off-target: applied run differs from the chosen target by 4 minute(s)",
        )
        final = self.submit_ok(view, {"emitted": True}, at)
        self.assertEqual(final["tick"]["status"], "complete")
        heartbeat = final["outcome_when_complete"]["heartbeat"]
        self.assertEqual((heartbeat["result"], heartbeat["writes"]), ("applied-off-target", 1))
        self.assertEqual(final["tick"]["heartbeat_writes"][0]["next_run_at"], "2026-09-17T13:04:00+00:00")

    def artifacts(self, view: dict) -> Path:
        return Path(self.store) / "ticks" / view["tick"]["tick_id"]

    def write_artifacts(
        self, view: dict, gates: list[dict], observations: list[dict]
    ) -> None:
        directory = self.artifacts(view)
        (directory / "report.json").write_text(
            json.dumps({"adapter": "praxis-aeon-bell-codex-status", "gates": gates}),
            encoding="utf-8",
        )
        (directory / "input.json").write_text(
            json.dumps({"observations": observations, "task_states": []}), encoding="utf-8"
        )

    def gate_entry(self, key: str, outcome: str, kind: str = "quota_recovery") -> dict:
        reason = {
            "observed": "typed-observation",
            "unhandled": "binding-labels-differ",
            "held": "held:policy-revision-mismatch",
            "error": "error:codex-timeout",
        }[outcome]
        return {"gate_key": key, "kind": kind, "outcome": outcome, "reason": reason}

    def test_observe_is_issued_with_exact_argv_and_engine_owned_artifacts(self) -> None:
        rid = self.register()["registration_id"]
        key = self.gate_key()
        cycle(self.store, T0, observations=[self.quota_observation(remaining=0)])
        at = "2026-09-17T13:05:00+00:00"  # past the 13:00 planned query: stale and due
        view = self.start(at, "--binding", "b.json")
        binding = os.path.abspath("b.json")
        self.assertEqual(view["tick"]["binding_paths"], [binding])
        view = self.submit_ok(view, self.read("running", at), at)
        self.assertEqual(view["tick"]["phase"], "observe")
        self.assertEqual(view["tick"]["requested_gate_keys"], [key])
        observe = self.pending(view, "observe", "query")
        self.assertEqual(observe["restart"], "resumable")
        directory = self.artifacts(view)
        adapter = str(SCRIPT.parent / "codex_status.py")
        self.assertEqual(
            observe["arguments"]["argv"],
            [
                "python3", adapter, "observe", "--binding", binding,
                "--requests", str(directory / "plan.json"),
                "--output", str(directory / "input.json"),
                "--report", str(directory / "report.json"),
                "--now", at,
            ],
        )
        self.assertIsNone(observe["arguments"]["cwd"])
        self.assertEqual(stat.S_IMODE(os.stat(directory).st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(os.stat(directory / "plan.json").st_mode), 0o600)
        plan = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(list(plan), ["observation_requests"])
        [request] = plan["observation_requests"]
        self.assertEqual((request["gate_key"], request["gate"], request["reason"]), (key, QUOTA_GATE, "stale"))
        self.assertTrue(view["tick"]["observe"]["issued"])
        self.assertEqual(view["tick"]["observe"]["unanswered_gate_keys"], [key])
        # The adapter (stood in for here) held the gate: the report and the
        # error observation are read from the engine's own directory.
        self.write_artifacts(
            view,
            [self.gate_entry(key, "held")],
            [{"gate_key": key, "status": "error", "observed_at": at, "reason": "held:policy-revision-mismatch"}],
        )
        view = self.submit_ok(view, {"exit_code": 0}, at)
        self.assertEqual(view["last_result"]["consequence"], "observation-ingested")
        observed = view["tick"]["observe"]
        self.assertEqual((observed["exit_code"], observed["answered_gate_keys"], observed["unanswered_gate_keys"]), (0, [key], []))
        self.assertTrue(observed["adapter_report_learned"])
        self.assertEqual(observed["adapter_report"], {key: "held"})
        self.assertIsNone(observed["artifacts_code"])
        self.assertEqual(view["tick"]["actions"][1]["recorded"], {"exit_code": 0, "answered_gate_keys": [key]})
        # The error stored no result: the stale closed observation still stands.
        self.assertEqual([s["reason"] for s in view["tick"]["dispatch"]["skipped"]], ["gate-observation-stale"])
        # The notice learned the query: the hold is a new failing marker.
        emit = self.pending(view, "emit", "notice")
        self.assertIn(f"new: failing gate quota_recovery synthetic-account-a/cli key {key} reason held:policy-revision-mismatch", emit["arguments"]["text"])
        view = self.submit_ok(view, {"emitted": True}, at)
        heartbeat = self.pending(view, "heartbeat_set")
        self.assertEqual(heartbeat["arguments"]["rule"], "schedule-as-printed")
        self.assertEqual(heartbeat["arguments"]["basis"]["schedule_reason"], "backoff")
        self.assertEqual(heartbeat["arguments"]["target_at"], "2026-09-17T13:20:00+00:00")
        final = self.submit_ok(view, self.applied(heartbeat), at)
        self.assertEqual(final["tick"]["status"], "complete")
        self.assertFalse(directory.exists(), "artifacts are removed after completion")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        self.assertEqual(inspected["retry_schedule"][key]["failures"], 1)
        # Next tick, after the backoff: the query answers open, the target is
        # idle, and the wake goes through the same bound path.
        later = "2026-09-17T13:20:00+00:00"
        view = self.start(later, "--binding", "b.json")
        view = self.submit_ok(view, self.read("idle", later), later)
        observe = self.pending(view, "observe", "query")
        directory = self.artifacts(view)
        self.assertNotEqual(directory, self.artifacts(final))
        self.write_artifacts(
            view,
            [self.gate_entry(key, "observed")],
            [self.quota_observation(remaining=30, observed_at=later)],
        )
        view = self.submit_ok(view, {"exit_code": 0}, later)
        self.assertEqual(view["tick"]["observe"]["answered_gate_keys"], [key])
        pre = self.pending(view, "task_read", "pre-send")
        view = self.submit_ok(view, self.read("idle", later), later)
        send = self.pending(view, "send", "wake")
        self.assertEqual(send["arguments"]["attempt_id"], pre["arguments"]["attempt_id"])
        self.assertIn("observed open at 2026-09-17T13:20:00+00:00", send["arguments"]["message"])
        view = self.submit_ok(view, {"outcome": "accepted"}, later)
        emit = self.pending(view, "emit", "notice")
        self.assertIn("cleared: failing gate", emit["arguments"]["text"])
        self.assertIn(f"attempt {pre['arguments']['attempt_id']} for registration {rid}", emit["arguments"]["text"])
        view = self.submit_ok(view, {"emitted": True}, later)
        heartbeat = self.pending(view, "heartbeat_set")
        final = self.submit_ok(view, self.applied(heartbeat), later)
        self.assertEqual(final["outcome_when_complete"]["wakes"][0]["result"], "accepted")
        self.assertFalse(directory.exists())
        self.assertFalse(os.path.exists("b.json"), "the engine never touches the binding path")

    def start_due_query(self, at: str, *extra: str, task: str = "idle") -> tuple[dict, str]:
        """A registration whose closed observation is past its planned query,
        driven to the pending observe action."""
        self.register()
        key = self.gate_key()
        cycle(self.store, T0, observations=[self.quota_observation(remaining=0)])
        view = self.start(at, "--binding", "b.json", *extra)
        view = self.submit_ok(view, self.read(task, at), at)
        return view, key

    def test_observe_failures_record_query_failed_and_bound_recovery(self) -> None:
        at = "2026-09-17T13:05:00+00:00"
        view, key = self.start_due_query(at)
        self.pending(view, "observe", "query")
        state_before = Path(self.store, "state.json").read_bytes()
        line = "codex status: invalid-binding: binding config must be private (mode 0600)"
        view = self.submit_ok(view, {"exit_code": 2, "stderr_line": line}, at)
        self.assertEqual(view["last_result"], {"action_id": view["tick"]["actions"][1]["action_id"], "disposition": "performed", "consequence": "query-failed"})
        observe = view["tick"]["observe"]
        self.assertEqual((observe["exit_code"], observe["failure_line"]), (2, line))
        self.assertEqual((observe["answered_gate_keys"], observe["unanswered_gate_keys"]), ([], [key]))
        self.assertFalse(observe["adapter_report_learned"])
        self.assertIsNone(observe["adapter_report"])
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        self.assertEqual(inspected["retry_schedule"], {}, "nothing ingested")
        self.assertEqual(inspected["observations"][0]["observed_at"], T0)
        self.assertTrue(inspected["schedule"]["gates"][0]["due"], "the gate stays due in the store")
        # No notice (nothing new); the heartbeat is bounded by recovery, not
        # rerun immediately.
        heartbeat = self.pending(view, "heartbeat_set")
        self.assertEqual(heartbeat["arguments"]["rule"], "failed-observation-recovery")
        self.assertEqual(heartbeat["arguments"]["target_at"], "2026-09-17T13:20:00+00:00")
        self.assertEqual(heartbeat["arguments"]["delay_minutes"], 15)
        basis = heartbeat["arguments"]["basis"]
        self.assertEqual(basis["unanswered_due_gate_keys"], [key])
        self.assertEqual(basis["recovery_bound_at"], "2026-09-17T13:20:00+00:00")
        self.assertEqual(basis["schedule_reason"], "gate-due")
        self.assertEqual(basis["earliest_waiting_expiry_at"], "2026-09-18T12:00:00+00:00")
        view = self.submit_ok(view, self.applied(heartbeat), at)
        emit = self.pending(view, "emit", "diagnostics")
        self.assertEqual(emit["arguments"]["text"], f"step observe: {line}")
        final = self.submit_ok(view, {"emitted": True}, at)
        self.assertEqual(final["tick"]["status"], "complete")
        self.assertEqual(final["outcome_when_complete"]["heartbeat"]["rule"], "failed-observation-recovery")
        # The failure form (the argv could not be run at all) is the same path
        # with its own diagnostic line.
        later = "2026-09-17T13:20:00+00:00"
        view = self.start(later, "--binding", "b.json")
        view = self.submit_ok(view, self.read("idle", later), later)
        self.pending(view, "observe")
        view = self.submit_ok(view, {"disposition": "not_performed", "reason": "python3 not on PATH"}, later)
        self.assertEqual(view["last_result"]["disposition"], "not_performed")
        self.assertEqual(view["last_result"]["consequence"], "query-failed")
        self.assertEqual(view["tick"]["observe"]["failure_line"], "python3 not on PATH")
        self.assertIsNone(view["tick"]["observe"]["exit_code"])
        heartbeat = self.pending(view, "heartbeat_set")
        self.assertEqual(heartbeat["arguments"]["rule"], "failed-observation-recovery")
        view = self.submit_ok(view, self.applied(heartbeat), later)
        emit = self.pending(view, "emit", "diagnostics")
        self.assertEqual(emit["arguments"]["text"], "aeon bell: observe-failed: not_performed: python3 not on PATH")
        self.submit_ok(view, {"emitted": True}, later)

    def test_observe_stderr_line_bound_is_the_untruncated_diagnostics_bound(self) -> None:
        # Coverage for review cycle 9, finding 1 (first-green after the bound
        # correction): the accepted exit-2 line bound is the diagnostics line
        # bound less the `step observe: ` relay prefix, so a line at the bound
        # is relayed untruncated and one past it is refused with nothing changed.
        bound = aeon_bell.STDERR_LINE_MAX_CHARS
        self.assertEqual(bound, aeon_bell.TICK_DIAGNOSTIC_MAX_CHARS - len("step observe: "))
        self.assertEqual(bound, 498)
        at = "2026-09-17T13:05:00+00:00"
        view, key = self.start_due_query(at)
        self.pending(view, "observe", "query")
        state_path = Path(self.store, "state.json")
        before = state_path.read_bytes()
        prefix = "codex status: invalid-binding: "
        longest = prefix + "x" * (bound - len(prefix))
        self.assertEqual(len(longest), bound)
        for label, line in (
            ("one past the bound", longest + "x"),
            ("non-printable", prefix + "tab\there"),
            ("not the adapter's line", "Traceback (most recent call last)"),
            ("empty message", prefix),
        ):
            with self.subTest(label=label):
                code, payload, err = self.submit(view, {"exit_code": 2, "stderr_line": line}, at)
                self.assertEqual(code, 2)
                self.assertIsNone(payload)
                self.assertIn("invalid-result", err)
                self.assertNotIn("xxxx", err, "the refused line is not echoed")
                self.assertEqual(state_path.read_bytes(), before, "nothing changed")
        view = self.submit_ok(view, {"exit_code": 2, "stderr_line": longest}, at)
        self.assertEqual(view["last_result"]["consequence"], "query-failed")
        self.assertEqual(view["tick"]["observe"]["failure_line"], longest)
        self.assertEqual(view["tick"]["observe"]["unanswered_gate_keys"], [key])
        heartbeat = self.pending(view, "heartbeat_set")
        self.assertEqual(heartbeat["arguments"]["rule"], "failed-observation-recovery")
        view = self.submit_ok(view, self.applied(heartbeat), at)
        emit = self.pending(view, "emit", "diagnostics")
        self.assertEqual(emit["arguments"]["text"], f"step observe: {longest}")
        self.assertEqual(len(emit["arguments"]["text"]), aeon_bell.TICK_DIAGNOSTIC_MAX_CHARS)
        final = self.submit_ok(view, {"emitted": True}, at)
        self.assertEqual(final["tick"]["status"], "complete")

    def test_observe_unusable_artifacts_roll_back(self) -> None:
        at = "2026-09-17T13:05:00+00:00"
        view, key = self.start_due_query(at)
        directory = self.artifacts(view)
        state_path = Path(self.store, "state.json")
        cases = [
            ("missing files", None, None, "artifact-io"),
            ("partial report", '{"adapter": "praxis-aeon-bell-codex-status", "gates": [{"gate_k', None, "invalid-adapter-report"),
            ("report is not an observe report", '{"gates": "none"}', None, "invalid-adapter-report"),
            ("partial input", "ok", '{"observations": [{"gate_key": "', "invalid-input"),
            ("input is not cycle input", "ok", '["not", "an", "object"]', "invalid-input"),
            (
                "one valid and one invalid observation",
                "ok",
                json.dumps({"observations": [
                    self.quota_observation(remaining=30, observed_at=at),
                    {"gate_key": key, "status": "ok", "observed_at": at, "account": "synthetic-account-a", "route": "cli", "buckets": [{"name": "weekly", "remaining_percent": 30}], "token": "SYNTHETIC-LEAK-0a1b"},
                ], "task_states": []}),
                "invalid-observation",
            ),
        ]
        for label, report, cycle_input, code in cases:
            with self.subTest(label=label):
                for name in ("report.json", "input.json"):
                    (directory / name).unlink(missing_ok=True)
                if report == "ok":
                    report = json.dumps({"adapter": "praxis-aeon-bell-codex-status", "gates": [self.gate_entry(key, "observed")]})
                if report is not None:
                    (directory / "report.json").write_text(report, encoding="utf-8")
                if cycle_input is not None:
                    (directory / "input.json").write_text(cycle_input, encoding="utf-8")
                before = state_path.read_bytes()
                code_, next_view, err = self.submit(view, {"exit_code": 0}, at)
                self.assertEqual(code_, 0, err)
                self.assertEqual(next_view["last_result"]["consequence"], "query-failed")
                observe = next_view["tick"]["observe"]
                self.assertEqual(observe["artifacts_code"], code)
                self.assertEqual((observe["answered_gate_keys"], observe["unanswered_gate_keys"]), ([], [key]))
                self.assertFalse(observe["adapter_report_learned"])
                self.assertIn(f"aeon bell: observe-artifacts: {code}: report.json or input.json unusable", next_view["tick"]["diagnostics"])
                self.assertNotIn("SYNTHETIC-LEAK", json.dumps(next_view))
                _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
                self.assertEqual(inspected["observations"][0]["observed_at"], T0, "nothing stored")
                self.assertEqual(inspected["retry_schedule"], {})
                self.assertNotIn("SYNTHETIC-LEAK", state_path.read_text(encoding="utf-8"))
                self.assertEqual(next_view["tick"]["phase"], "schedule" if next_view["pending_action"]["kind"] == "heartbeat_set" else next_view["tick"]["phase"])
                self.pending(next_view, "heartbeat_set")
                self.assertEqual(next_view["pending_action"]["arguments"]["rule"], "failed-observation-recovery")
                # Rewind for the next case by abandoning this tick and driving
                # a fresh one to the same pending observe.
                view = self.start(at, "--binding", "b.json", "--abandon", next_view["tick"]["tick_id"])
                view = self.submit_ok(view, self.read("idle", at), at)
                self.pending(view, "observe")
                directory = self.artifacts(view)
                self.assertNotEqual(before, b"", "state was written")

    def test_missing_binding_is_a_configuration_gap_reported_once_then_deferred_to_liveness(self) -> None:
        # Review cycle 9, finding 2: a wholly absent --binding is a
        # configuration gap. The first tick that finds it relays one durable
        # notice and defers to the liveness bound; it prints no per-tick
        # diagnostics line and does not rerun every 15 minutes. Nothing is
        # queried, so no observation, adapter report, or backoff appears.
        rid = self.register()["registration_id"]
        key = self.gate_key()
        at = "2026-09-17T12:05:00+00:00"  # never observed: due now
        view = self.start(at)
        view = self.submit_ok(view, self.read("idle", at), at)
        observe = view["tick"]["observe"]
        self.assertFalse(observe["issued"])
        self.assertEqual(observe["not_issued_reason"], "no-binding")
        self.assertEqual(observe["unanswered_gate_keys"], [key])
        self.assertEqual(view["tick"]["requested_gate_keys"], [key])
        self.assertFalse(observe["adapter_report_learned"], "no query, no adapter report")
        self.assertIsNone(observe["adapter_report"])
        self.assertFalse(os.path.exists(Path(self.store) / "ticks"))
        self.assertEqual([s["reason"] for s in view["tick"]["dispatch"]["skipped"]], ["gate-unobserved"])
        self.assertEqual(view["tick"]["diagnostics"], [], "no per-tick diagnostics line")
        # First sight: one notice names the gap as configuration knowledge.
        emit = self.pending(view, "emit", "notice")
        self.assertFalse(emit["arguments"]["replayed"])
        text = emit["arguments"]["text"]
        self.assertIn(
            f"new: no-binding gate quota_recovery synthetic-account-a/cli key {key}; "
            f"registrations {rid}; next: ",
            text,
        )
        self.assertIn("--binding", text)
        self.assertIn("bring the existing heartbeat forward", text)
        self.assertNotIn("unhandled", text)
        for needle in ("host-a", "task-1", "episode-1", "Continue the bounded work."):
            self.assertNotIn(needle, text)
        view = self.submit_ok(view, {"emitted": True}, at)
        self.assertEqual(view["last_result"]["consequence"], "notice-acknowledged")
        # Then the schedule defers to the liveness bound: no recovery cadence.
        heartbeat = self.pending(view, "heartbeat_set")
        args = heartbeat["arguments"]
        self.assertEqual(args["rule"], "schedule-as-printed")
        self.assertEqual(args["target_at"], "2026-09-17T18:05:00+00:00")
        self.assertEqual(args["delay_minutes"], 360)
        self.assertEqual(args["basis"]["schedule_reason"], "configuration-gap")
        self.assertEqual(args["basis"]["unanswered_due_gate_keys"], [])
        self.assertIsNone(args["basis"]["recovery_bound_at"])
        final = self.submit_ok(view, self.applied(heartbeat), at)
        self.assertEqual(final["tick"]["status"], "complete")
        self.assertEqual(final["tick"]["diagnostics"], [])
        self.assertTrue(final["outcome_when_complete"]["printed_anything"])
        self.assertEqual(final["outcome_when_complete"]["heartbeat"]["rule"], "schedule-as-printed")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        [gate] = inspected["schedule"]["gates"]
        self.assertTrue(gate["due"], "the gate is still requested at every tick that runs")
        self.assertTrue(gate["configuration_gap"])
        self.assertEqual(inspected["schedule"]["reason"], "configuration-gap")
        self.assertEqual(inspected["observations"], [], "no observation was fabricated")
        self.assertEqual(inspected["retry_schedule"], {}, "no backoff was fabricated")
        # The legacy notice reads the same durable knowledge: the gap is
        # retained as configuration knowledge, and nothing was queried.
        code, notice, err = run("notice", "--store", self.store, "--now", at)
        self.assertEqual(code, 0, err)
        self.assertFalse(notice["report"])
        self.assertEqual(notice["markers_now"], [f"no-binding:{key}"])
        self.assertEqual(notice["coverage"], {"adapter_report": False, "queried": [], "retained": [key]})

    def no_binding_first_tick(self, at: str) -> tuple[str, str]:
        """Register one wait and drive the first no-binding tick to completion:
        the gap is relayed once and the heartbeat targets the liveness bound."""
        rid = self.register()["registration_id"]
        key = self.gate_key()
        view = self.start(at)
        view = self.submit_ok(view, self.read("idle", at), at)
        self.pending(view, "emit", "notice")
        view = self.submit_ok(view, {"emitted": True}, at)
        heartbeat = self.pending(view, "heartbeat_set")
        self.assertEqual(heartbeat["arguments"]["basis"]["schedule_reason"], "configuration-gap")
        final = self.submit_ok(view, self.applied(heartbeat), at)
        self.assertEqual(final["tick"]["status"], "complete")
        return rid, key

    def test_missing_binding_repeated_tick_and_restart_stay_quiet(self) -> None:
        # Later identical ticks are quiet (no notice, no diagnostics, the same
        # liveness recommendation); a monitor that lost its context mid-relay
        # abandons and the new tick replays the same notice; a restarted
        # monitor with an empty context reads the same quiet state from the
        # store.
        rid = self.register()["registration_id"]
        key = self.gate_key()
        at = "2026-09-17T12:05:00+00:00"
        view = self.start(at)
        view = self.submit_ok(view, self.read("idle", at), at)
        lost = self.pending(view, "emit", "notice")
        self.assertEqual(lost["restart"], "abandon-only")
        # Context lost before the print was submitted: the notice stays
        # pending and a fresh start refuses until the tick is abandoned.
        again = "2026-09-17T12:06:00+00:00"
        code, _, err = self.tick_start(again, "--heartbeat", self.HEARTBEAT)
        self.assertEqual(code, 2)
        self.assertIn("tick-in-progress", err)
        view = self.start(again, "--abandon", view["tick"]["tick_id"])
        self.assertEqual(view["last"]["abandoned_pending"]["kind"], "emit")
        self.assertEqual(view["last"]["abandoned_pending"]["notice_id"], lost["arguments"]["notice_id"])
        view = self.submit_ok(view, self.read("idle", again), again)
        self.assertEqual(view["tick"]["observe"]["not_issued_reason"], "no-binding")
        replay = self.pending(view, "emit", "notice")
        self.assertTrue(replay["arguments"]["replayed"])
        self.assertEqual(replay["arguments"]["notice_id"], lost["arguments"]["notice_id"])
        self.assertEqual(replay["arguments"]["text"], lost["arguments"]["text"])
        view = self.submit_ok(view, {"emitted": True}, again)
        self.assertEqual(view["last_result"]["consequence"], "notice-acknowledged")
        heartbeat = self.pending(view, "heartbeat_set")
        self.assertEqual(heartbeat["arguments"]["basis"]["schedule_reason"], "configuration-gap")
        self.assertEqual(heartbeat["arguments"]["target_at"], "2026-09-17T18:06:00+00:00")
        final = self.submit_ok(view, self.applied(heartbeat), again)
        self.assertEqual(final["tick"]["status"], "complete")
        self.assertEqual(final["tick"]["diagnostics"], [])
        # The liveness run fires with the same missing binding: quiet.
        later = "2026-09-17T18:06:00+00:00"
        view = self.start(later)
        view = self.submit_ok(view, self.read("idle", later), later)
        observe = view["tick"]["observe"]
        self.assertEqual((observe["issued"], observe["not_issued_reason"]), (False, "no-binding"))
        self.assertEqual(view["tick"]["requested_gate_keys"], [key], "still requested at every tick")
        heartbeat = self.pending(view, "heartbeat_set")
        self.assertIsNone(view["tick"]["notice"]["notice_id"], "an unchanged gap is not news")
        self.assertEqual(heartbeat["arguments"]["rule"], "schedule-as-printed")
        self.assertEqual(heartbeat["arguments"]["basis"]["schedule_reason"], "configuration-gap")
        self.assertEqual(heartbeat["arguments"]["target_at"], "2026-09-18T00:06:00+00:00")
        self.assertEqual(heartbeat["arguments"]["delay_minutes"], 360)
        final = self.submit_ok(view, self.applied(heartbeat), later)
        self.assertEqual(final["tick"]["status"], "complete")
        self.assertEqual(final["tick"]["diagnostics"], [])
        self.assertFalse(final["outcome_when_complete"]["printed_anything"])
        self.assertIsNone(final["outcome_when_complete"]["notice"]["notice_id"])
        # A restarted monitor with an empty context: the baseline and the gap
        # knowledge are in the store, so the next tick is quiet as well.
        restart = "2026-09-18T00:06:00+00:00"
        view = self.start(restart)
        view = self.submit_ok(view, self.read("idle", restart), restart)
        heartbeat = self.pending(view, "heartbeat_set")
        self.assertEqual(heartbeat["arguments"]["basis"]["schedule_reason"], "configuration-gap")
        final = self.submit_ok(view, self.applied(heartbeat), restart)
        self.assertFalse(final["outcome_when_complete"]["printed_anything"])
        _, inspected, _ = run("inspect", "--store", self.store, "--now", restart)
        self.assertEqual(inspected["observations"], [])
        self.assertEqual([r["registration_id"] for r in inspected["registrations"]], [rid])

    def test_missing_binding_repair_that_is_observed_clears_the_gap_truthfully(self) -> None:
        rid, key = self.no_binding_first_tick("2026-09-17T12:05:00+00:00")
        # A binding is passed but its query exits 2: nothing was observed, so
        # nothing is cleared or fabricated. The gap stays retained knowledge
        # (quiet), the failure line is the tick's diagnostics, and the schedule
        # still defers to the liveness bound until a query answers the gate;
        # after fixing the binding the heartbeat is brought forward again.
        at = "2026-09-17T12:30:00+00:00"
        view = self.start(at, "--binding", "b.json")
        view = self.submit_ok(view, self.read("idle", at), at)
        self.pending(view, "observe", "query")
        self.assertTrue(view["tick"]["observe"]["issued"])
        line = "codex status: invalid-binding: binding config must be private (mode 0600)"
        view = self.submit_ok(view, {"exit_code": 2, "stderr_line": line}, at)
        self.assertEqual(view["last_result"]["consequence"], "query-failed")
        heartbeat = self.pending(view, "heartbeat_set")
        self.assertIsNone(view["tick"]["notice"]["notice_id"], "nothing learned, nothing cleared")
        self.assertEqual(heartbeat["arguments"]["basis"]["schedule_reason"], "configuration-gap")
        self.assertEqual(heartbeat["arguments"]["target_at"], "2026-09-17T18:30:00+00:00")
        view = self.submit_ok(view, self.applied(heartbeat), at)
        emit = self.pending(view, "emit", "diagnostics")
        self.assertEqual(emit["arguments"]["text"], f"step observe: {line}")
        view = self.submit_ok(view, {"emitted": True}, at)
        self.assertEqual(view["tick"]["status"], "complete")
        code, notice, err = run("notice", "--store", self.store, "--now", at)
        self.assertEqual(code, 0, err)
        self.assertEqual(notice["coverage"]["retained"], [key])
        # The repaired binding is passed and the brought-forward tick's query
        # answers the gate (closed): the gap is cleared once, from the actual
        # observation, and the gate's own plan takes over the schedule.
        at = "2026-09-17T12:45:00+00:00"
        view = self.start(at, "--binding", "b.json")
        view = self.submit_ok(view, self.read("idle", at), at)
        self.pending(view, "observe", "query")
        self.write_artifacts(
            view,
            [self.gate_entry(key, "observed")],
            [self.quota_observation(remaining=0, observed_at=at)],
        )
        view = self.submit_ok(view, {"exit_code": 0}, at)
        self.assertEqual(view["last_result"]["consequence"], "observation-ingested")
        self.assertEqual(view["tick"]["observe"]["answered_gate_keys"], [key])
        self.assertEqual(view["tick"]["observe"]["adapter_report"], {key: "observed"})
        emit = self.pending(view, "emit", "notice")
        text = emit["arguments"]["text"]
        self.assertIn(
            f"cleared: no-binding gate quota_recovery synthetic-account-a/cli key {key}; "
            f"registrations {rid}",
            text,
        )
        self.assertNotIn("new:", text)
        view = self.submit_ok(view, {"emitted": True}, at)
        heartbeat = self.pending(view, "heartbeat_set")
        args = heartbeat["arguments"]
        self.assertEqual(args["rule"], "schedule-as-printed")
        self.assertEqual(args["basis"]["schedule_reason"], "gate-query")
        self.assertEqual(args["target_at"], "2026-09-17T13:45:00+00:00", "no estimate: 60 minutes from the anchor")
        final = self.submit_ok(view, self.applied(heartbeat), at)
        self.assertEqual(final["tick"]["status"], "complete")
        self.assertEqual(final["tick"]["diagnostics"], [])
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        [gate] = inspected["schedule"]["gates"]
        self.assertFalse(gate["configuration_gap"])
        self.assertFalse(gate["due"])
        # The binding is withdrawn again at the next planned query: the same
        # gap reads as new again.
        at = "2026-09-17T13:45:00+00:00"
        view = self.start(at)
        view = self.submit_ok(view, self.read("idle", at), at)
        self.assertEqual(view["tick"]["observe"]["not_issued_reason"], "no-binding")
        emit = self.pending(view, "emit", "notice")
        self.assertIn(f"new: no-binding gate quota_recovery synthetic-account-a/cli key {key}", emit["arguments"]["text"])
        view = self.submit_ok(view, {"emitted": True}, at)
        heartbeat = self.pending(view, "heartbeat_set")
        self.assertEqual(heartbeat["arguments"]["basis"]["schedule_reason"], "configuration-gap")
        final = self.submit_ok(view, self.applied(heartbeat), at)
        self.assertEqual(final["tick"]["status"], "complete")
        # A binding that is passed but does not own the labels is a different
        # gap: the adapter's own unhandled answer clears no-binding and is
        # reported as new, in one notice.
        at = "2026-09-17T14:00:00+00:00"
        view = self.start(at, "--binding", "other.json")
        view = self.submit_ok(view, self.read("idle", at), at)
        self.pending(view, "observe", "query")
        self.write_artifacts(view, [self.gate_entry(key, "unhandled")], [])
        view = self.submit_ok(view, {"exit_code": 0}, at)
        self.assertEqual(view["tick"]["observe"]["adapter_report"], {key: "unhandled"})
        self.assertEqual(view["tick"]["observe"]["unanswered_gate_keys"], [key])
        emit = self.pending(view, "emit", "notice")
        text = emit["arguments"]["text"]
        self.assertIn(f"cleared: no-binding gate quota_recovery synthetic-account-a/cli key {key}", text)
        self.assertIn(f"new: unhandled gate quota_recovery synthetic-account-a/cli key {key}", text)
        view = self.submit_ok(view, {"emitted": True}, at)
        heartbeat = self.pending(view, "heartbeat_set")
        self.assertEqual(heartbeat["arguments"]["basis"]["schedule_reason"], "configuration-gap")
        final = self.submit_ok(view, self.applied(heartbeat), at)
        self.assertEqual(final["tick"]["status"], "complete")
        code, notice, err = run("notice", "--store", self.store, "--now", at)
        self.assertEqual(code, 0, err)
        self.assertEqual(notice["markers_now"], [f"unhandled:{key}"])

    def test_missing_binding_gap_respects_nearer_obligations_and_outranks_explicit_interval(self) -> None:
        # Gate A's registration expires in about two hours; with no binding the
        # heartbeat is bounded by that expiry, never pushed out to the
        # 360-minute liveness bound.
        at = "2026-09-17T12:05:00+00:00"
        a = self.register(task_id="task-1", extra=("--expires-in-minutes", "125"))
        key_a = a["gate_key"]
        view = self.start(at)
        view = self.submit_ok(view, self.read("idle", at), at)
        self.pending(view, "emit", "notice")
        view = self.submit_ok(view, {"emitted": True}, at)
        heartbeat = self.pending(view, "heartbeat_set")
        args = heartbeat["arguments"]
        self.assertEqual(args["rule"], "schedule-as-printed")
        self.assertEqual(args["basis"]["schedule_reason"], "registration-expiry")
        self.assertEqual(args["target_at"], "2026-09-17T14:05:00+00:00")
        self.assertEqual(args["basis"]["earliest_waiting_expiry_at"], "2026-09-17T14:05:00+00:00")
        final = self.submit_ok(view, self.applied(heartbeat), at)
        self.assertEqual(final["tick"]["status"], "complete")
        # Gate B (another bucket) has a fresh cached closed observation and an
        # explicit 30-minute interval: not due yet, its planned query is the
        # nearer independent obligation, and A's unchanged gap stays quiet.
        b = self.register(
            task_id="task-2",
            gate=dict(QUOTA_GATE, bucket="daily"),
            extra=("--poll-interval-minutes", "30"),
            now=at,
        )
        key_b = b["gate_key"]
        cycle(self.store, at, observations=[self.observation_for(key_b, "daily", 0, at)])
        later = "2026-09-17T12:10:00+00:00"
        view = self.start(later)
        view = self.submit_ok(view, self.read("idle", later), later)
        view = self.submit_ok(view, self.read("idle", later), later)
        self.assertEqual(view["tick"]["requested_gate_keys"], [key_a])
        heartbeat = self.pending(view, "heartbeat_set")
        args = heartbeat["arguments"]
        self.assertEqual(args["basis"]["schedule_reason"], "gate-query")
        self.assertEqual(args["target_at"], "2026-09-17T12:35:00+00:00")
        self.assertEqual(args["basis"]["earliest_non_due_check_at"], "2026-09-17T12:35:00+00:00")
        final = self.submit_ok(view, self.applied(heartbeat), later)
        self.assertEqual(final["tick"]["status"], "complete")
        self.assertFalse(final["outcome_when_complete"]["printed_anything"])
        # At B's explicit interval both gates are due and still no binding is
        # passed: B's gap is new (reported once), and the explicit interval
        # does not pull the next check before A's expiry or the liveness
        # bound; no 15-minute recovery cadence applies to an unissued query.
        due = "2026-09-17T12:35:00+00:00"
        view = self.start(due)
        view = self.submit_ok(view, self.read("idle", due), due)
        view = self.submit_ok(view, self.read("idle", due), due)
        self.assertEqual(sorted(view["tick"]["requested_gate_keys"]), sorted([key_a, key_b]))
        self.assertEqual(view["tick"]["observe"]["not_issued_reason"], "no-binding")
        emit = self.pending(view, "emit", "notice")
        text = emit["arguments"]["text"]
        self.assertIn(f"new: no-binding gate quota_recovery synthetic-account-a/cli key {key_b}", text)
        self.assertNotIn(key_a, text, "A's unchanged gap is not repeated")
        view = self.submit_ok(view, {"emitted": True}, due)
        heartbeat = self.pending(view, "heartbeat_set")
        args = heartbeat["arguments"]
        self.assertEqual(args["rule"], "schedule-as-printed")
        self.assertEqual(args["basis"]["schedule_reason"], "registration-expiry")
        self.assertEqual(args["target_at"], "2026-09-17T14:05:00+00:00")
        self.assertEqual(args["basis"]["unanswered_due_gate_keys"], [])
        self.assertIsNone(args["basis"]["recovery_bound_at"])
        final = self.submit_ok(view, self.applied(heartbeat), due)
        self.assertEqual(final["tick"]["status"], "complete")
        self.assertEqual(final["tick"]["diagnostics"], [])
        _, inspected, _ = run("inspect", "--store", self.store, "--now", due)
        gates = {g["gate_key"]: g for g in inspected["schedule"]["gates"]}
        self.assertEqual(gates[key_b]["cadence"], "explicit")
        self.assertTrue(gates[key_b]["due"])
        self.assertTrue(gates[key_b]["configuration_gap"])
        self.assertEqual(inspected["schedule"]["reason"], "registration-expiry")

    def two_gates(self, *extra_a: str) -> tuple[str, str]:
        a = self.register(task_id="task-1", extra=extra_a)
        b = self.register(task_id="task-2", gate=dict(QUOTA_GATE, bucket="daily"))
        return a["gate_key"], b["gate_key"]

    def observation_for(self, key: str, bucket: str, remaining: float, observed_at: str) -> dict:
        return {
            "gate_key": key, "status": "ok", "observed_at": observed_at,
            "account": "synthetic-account-a", "route": "cli",
            "buckets": [{"name": bucket, "remaining_percent": remaining}],
        }

    def test_partial_answers_across_two_gates(self) -> None:
        key_a, key_b = self.two_gates()
        at = "2026-09-17T12:05:00+00:00"
        view = self.start(at, "--binding", "b.json")
        view = self.submit_ok(view, self.read("idle", at), at)
        view = self.submit_ok(view, self.read("idle", at), at)
        self.assertEqual(view["tick"]["requested_gate_keys"], [key_a, key_b])
        self.pending(view, "observe")
        # The adapter reported both gates but carried only A's observation.
        self.write_artifacts(
            view,
            [self.gate_entry(key_a, "observed"), self.gate_entry(key_b, "error")],
            [self.observation_for(key_a, "weekly", 0, at)],
        )
        view = self.submit_ok(view, {"exit_code": 0}, at)
        observe = view["tick"]["observe"]
        self.assertEqual((observe["answered_gate_keys"], observe["unanswered_gate_keys"]), ([key_a], [key_b]))
        self.assertTrue(observe["adapter_report_learned"])
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        gates = {g["gate_key"]: g for g in inspected["schedule"]["gates"]}
        self.assertFalse(gates[key_a]["due"], "A is answered and planned")
        self.assertEqual(gates[key_a]["check_at"], "2026-09-17T13:05:00+00:00")
        self.assertTrue(gates[key_b]["due"], "B stays due")
        heartbeat = self.pending(view, "heartbeat_set")
        args = heartbeat["arguments"]
        self.assertEqual(args["rule"], "failed-observation-recovery")
        self.assertEqual(args["target_at"], "2026-09-17T12:20:00+00:00")
        self.assertEqual(args["basis"]["unanswered_due_gate_keys"], [key_b])
        self.assertEqual(args["basis"]["answered_due_gate_keys"], [])
        self.assertEqual(args["basis"]["earliest_non_due_check_at"], "2026-09-17T13:05:00+00:00")
        self.assertEqual(args["basis"]["recovery_bound_at"], "2026-09-17T12:20:00+00:00")
        final = self.complete_quietly(view, at)
        self.assertEqual(final["tick"]["status"], "complete")
        self.assertEqual(final["tick"]["diagnostics"], [], "a partial answer is not a diagnostic")

    def test_answered_still_due_gate_keeps_its_deadline_beside_an_unanswered_gate(self) -> None:
        # A's owner fixed a 1-minute explicit interval; B's query failed. A's
        # next deadline is its own cadence and is not pushed to the recovery
        # bound; B is retried at that run, never earlier on its own account.
        key_a, key_b = self.two_gates("--poll-interval-minutes", "1")
        at = "2026-09-17T12:05:00+00:00"
        view = self.start(at, "--binding", "b.json")
        view = self.submit_ok(view, self.read("running", at), at)
        view = self.submit_ok(view, self.read("running", at), at)
        self.pending(view, "observe")
        self.write_artifacts(
            view,
            [self.gate_entry(key_a, "observed"), self.gate_entry(key_b, "error")],
            [self.observation_for(key_a, "weekly", 40, at)],
        )
        later = "2026-09-17T12:07:00+00:00"  # A's 12:06 explicit deadline has passed
        view = self.submit_ok(view, {"exit_code": 0}, later)
        self.assertEqual(view["tick"]["observe"]["answered_gate_keys"], [key_a])
        heartbeat = self.pending(view, "heartbeat_set")
        args = heartbeat["arguments"]
        self.assertEqual(args["rule"], "schedule-as-printed")
        self.assertEqual((args["target_at"], args["delay_minutes"]), (later, 0))
        self.assertEqual(args["basis"]["schedule_reason"], "gate-due")
        self.assertEqual(args["basis"]["answered_due_gate_keys"], [key_a])
        self.assertEqual(args["basis"]["unanswered_due_gate_keys"], [key_b])
        self.assertIsNone(args["basis"]["recovery_bound_at"])
        final = self.complete_quietly(view, later)
        self.assertEqual(final["outcome_when_complete"]["heartbeat"]["rule"], "schedule-as-printed")
        # The same gate answered and due again with nothing unanswered is the
        # printed schedule too: the owner-configured cadence, not a recovery.
        view = self.start(later, "--binding", "b.json")
        view = self.submit_ok(view, self.read("running", later), later)
        view = self.submit_ok(view, self.read("running", later), later)
        self.write_artifacts(
            view,
            [self.gate_entry(key_a, "observed"), self.gate_entry(key_b, "observed")],
            [self.observation_for(key_a, "weekly", 40, later), self.observation_for(key_b, "daily", 0, later)],
        )
        latest = "2026-09-17T12:09:00+00:00"
        view = self.submit_ok(view, {"exit_code": 0}, latest)
        heartbeat = self.pending(view, "heartbeat_set")
        self.assertEqual(heartbeat["arguments"]["rule"], "schedule-as-printed")
        self.assertEqual(heartbeat["arguments"]["basis"]["answered_due_gate_keys"], [key_a])
        self.assertEqual(heartbeat["arguments"]["basis"]["unanswered_due_gate_keys"], [])
        self.assertEqual(heartbeat["arguments"]["delay_minutes"], 0)

    def test_fresh_owner_work_and_nearer_expiry_bound_the_heartbeat(self) -> None:
        # Observe fails for gate A while an owner registers gate B during the
        # tick: the fresh owner work wins with delay 0.
        rid = self.register(task_id="task-1")["registration_id"]
        key_a = self.gate_key()
        at = "2026-09-17T12:05:00+00:00"
        view = self.start(at, "--binding", "b.json")
        view = self.submit_ok(view, self.read("running", at), at)
        self.pending(view, "observe")
        b = self.register(task_id="task-2", gate=dict(QUOTA_GATE, bucket="daily"), now=at)
        line = "codex status: invalid-requests: requests file is unreadable"
        view = self.submit_ok(view, {"exit_code": 2, "stderr_line": line}, at)
        heartbeat = self.pending(view, "heartbeat_set")
        args = heartbeat["arguments"]
        self.assertEqual(args["rule"], "fresh-owner-work")
        self.assertEqual((args["target_at"], args["delay_minutes"]), (at, 0))
        self.assertEqual(args["basis"]["unrequested_due_gate_keys"], [b["gate_key"]])
        self.assertEqual(args["basis"]["unanswered_due_gate_keys"], [key_a])
        view = self.submit_ok(view, self.applied(heartbeat), at)
        self.submit_ok(view, {"emitted": True}, at)
        # A waiting registration expiring in five minutes bounds the recovery.
        _, _, _ = run("remove", "--store", self.store, "--registration-id", b["registration_id"], "--owner", "owner-a", "--now", at)
        _, _, _ = run("update", "--store", self.store, "--registration-id", rid, "--owner", "owner-a", "--expires-in-minutes", "5", "--now", at)
        view = self.start(at, "--binding", "b.json")
        view = self.submit_ok(view, self.read("running", at), at)
        view = self.submit_ok(view, {"exit_code": 2, "stderr_line": line}, at)
        heartbeat = self.pending(view, "heartbeat_set")
        self.assertEqual(heartbeat["arguments"]["rule"], "failed-observation-recovery")
        self.assertEqual(heartbeat["arguments"]["target_at"], "2026-09-17T12:10:00+00:00")
        self.assertEqual(heartbeat["arguments"]["basis"]["earliest_waiting_expiry_at"], "2026-09-17T12:10:00+00:00")
        self.assertEqual(heartbeat["arguments"]["delay_minutes"], 5)

    def test_fingerprint_recheck_writes_twice_then_reports(self) -> None:
        rid = self.register()["registration_id"]
        cycle(self.store, T0, observations=[self.quota_observation(remaining=0)])
        at = "2026-09-17T12:05:00+00:00"
        view = self.start(at)
        view = self.submit_ok(view, self.read("idle", at), at)
        first = self.pending(view, "heartbeat_set")
        self.assertEqual(first["arguments"]["write_number"], 1)
        # Owner work lands after write 1: the fingerprint moved, so exactly
        # one more write is chosen from the newest schedule.
        run("update", "--store", self.store, "--registration-id", rid, "--owner", "owner-a", "--expected-open-at", "2026-09-17T12:30:00+00:00", "--now", at)
        view = self.submit_ok(view, self.applied(first), at)
        self.assertEqual(view["last_result"]["consequence"], "heartbeat-applied")
        second = self.pending(view, "heartbeat_set")
        self.assertEqual(second["arguments"]["write_number"], 2)
        self.assertNotEqual(second["arguments"]["fingerprint"], first["arguments"]["fingerprint"])
        self.assertEqual(second["arguments"]["target_at"], "2026-09-17T12:15:00+00:00")
        # And again after write 2: the engine stops, reports, and leaves the
        # run from write 2 applied.
        run("update", "--store", self.store, "--registration-id", rid, "--owner", "owner-a", "--poll-interval-minutes", "120", "--now", at)
        view = self.submit_ok(view, self.applied(second), at)
        emit = self.pending(view, "emit", "diagnostics")
        self.assertEqual(
            emit["arguments"]["text"],
            "aeon bell: schedule-raced: the registry changed during scheduling; the run "
            f"left applied is from fingerprint {second['arguments']['fingerprint'][:12]}",
        )
        final = self.submit_ok(view, {"emitted": True}, at)
        self.assertEqual([a["kind"] for a in final["tick"]["actions"]], ["task_read", "heartbeat_set", "heartbeat_set", "emit"])
        heartbeat = final["outcome_when_complete"]["heartbeat"]
        self.assertEqual(heartbeat["writes"], 2)
        self.assertTrue(heartbeat["registry_changed_after_last_write"])
        self.assertEqual(heartbeat["fingerprint_applied_from"], second["arguments"]["fingerprint"])
        self.assertEqual(heartbeat["target_at"], "2026-09-17T12:15:00+00:00")

    def test_waiting_gate_knowledge_is_part_of_the_schedule_fingerprint(self) -> None:
        self.register()
        key = self.gate_key()
        at = "2026-09-17T12:05:00+00:00"
        view = self.start(at)
        view = self.submit_ok(view, self.read("idle", at), at)
        notice = self.pending(view, "emit", "notice")
        view = self.submit_ok(
            view,
            {"disposition": "unavailable", "reason": "notice channel unavailable"},
            at,
        )
        first = self.pending(view, "heartbeat_set")

        report = Path(self._tmp.name) / "knowledge-report.json"
        report.write_text(
            json.dumps(
                {
                    "adapter": "praxis-aeon-bell-codex-status",
                    "gates": [
                        {
                            "gate_key": key,
                            "kind": "quota_recovery",
                            "outcome": "observed",
                            "reason": "typed-observation",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        code, replay, err = run(
            "notice", "--store", self.store, "--adapter-report", str(report),
            "--now", at,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(replay["notice_id"], notice["arguments"]["notice_id"])

        view = self.submit_ok(view, self.applied(first), at)
        second = self.pending(view, "heartbeat_set")
        self.assertEqual(second["arguments"]["write_number"], 2)
        self.assertNotEqual(
            second["arguments"]["fingerprint"], first["arguments"]["fingerprint"]
        )

    def test_binding_and_shape_enforcement_leave_the_store_unchanged(self) -> None:
        self.register()
        cycle(self.store, T0, observations=[self.quota_observation(remaining=0)])
        at = "2026-09-17T12:05:00+00:00"
        done = self.complete_quietly(self.submit_ok(self.start(at), self.read("idle", at), at), at)
        view = self.start(at)
        read = self.pending(view, "task_read", "task-state")
        state_path = Path(self.store, "state.json")
        before = state_path.read_bytes()
        long_reason = "x" * 257

        def refused(code: str, *argv: str, result: Any = None, action_id: str | None = None, now: str | None = at) -> None:
            with self.subTest(code=code, argv=argv, result=result):
                args = [
                    "tick", "submit", "--store", self.store,
                    "--tick-id", view["tick"]["tick_id"],
                    "--action-id", read["action_id"] if action_id is None else action_id,
                    *argv,
                ]
                if result is not None:
                    args += ["--result-json", json.dumps(result)]
                if now is not None:
                    args += ["--now", now]
                exit_code, payload, err = run(*args)
                self.assertEqual(exit_code, 2, err)
                self.assertIsNone(payload)
                self.assertTrue(err.startswith(f"aeon bell: {code}: "), err)
                self.assertNotIn("Traceback", err)
                self.assertEqual(state_path.read_bytes(), before, "state.json is byte-identical")
                self.assertEqual(self.status(at)["pending_action"]["action_id"], read["action_id"])

        idle = self.read("idle", at)
        refused("unknown-tick", "--tick-id", "0" * 24, result=idle)
        refused("tick-not-running", "--tick-id", done["tick"]["tick_id"], result=idle)
        refused("action-not-pending", result=idle, action_id="0" * 12)
        refused("action-not-pending", result=idle, action_id=done["tick"]["actions"][0]["action_id"])
        refused("invalid-result", result={"status": "idle"})
        refused("invalid-result", result={"status": "idle", "observed_at": at, "extra": 1})
        refused("invalid-result", result={"status": "busy", "observed_at": at})
        refused("invalid-result", result={"status": "idle", "observed_at": "yesterday"})
        refused("invalid-result", result={"disposition": "failed", "reason": long_reason})
        refused("invalid-result", result={"disposition": "skipped", "reason": "no"})
        refused("invalid-result", result={"exit_code": 0})
        refused("invalid-result", result=["idle"])
        refused("invalid-result", "--result-json", "{not json")
        refused("invalid-result", "--result-file", str(Path(self._tmp.name) / "missing.json"))
        refused("stale-result", result=self.read("idle", "2026-09-17T12:03:00+00:00"))
        refused("stale-result", result=self.read("idle", "2026-09-17T12:07:00+00:00"))
        refused("tick-clock", result=idle, now="2026-09-17T12:04:59+00:00")
        refused("tick-clock", result=idle, now=None)
        refused("invalid-time", result=idle, now="noon")
        self.assertNotIn(long_reason, state_path.read_text(encoding="utf-8"))
        # An observe action refuses a stderr line that is not the adapter's.
        view = self.submit_ok(view, idle, at)
        final = self.complete_quietly(view, at)
        self.assertEqual(final["tick"]["status"], "complete")
        later = "2026-09-17T13:05:00+00:00"
        view = self.start(later, "--binding", "b.json")
        view = self.submit_ok(view, self.read("idle", later), later)
        read = self.pending(view, "observe")
        before = state_path.read_bytes()
        refused("invalid-result", result={"exit_code": 2, "stderr_line": "Traceback (most recent call last)"}, now=later)
        refused("invalid-result", result={"exit_code": 2}, now=later)
        refused("invalid-result", result={"exit_code": 0, "stderr_line": "codex status: x: y"}, now=later)
        refused("invalid-result", result={"exit_code": False}, now=later)
        refused("invalid-result", result={"exit_code": 1, "stderr_line": "codex status: invalid-binding: x"}, now=later)

    def test_result_file_and_old_task_read_and_clock_regression(self) -> None:
        from unittest import mock

        rid = self.register()["registration_id"]
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        at = "2026-09-17T12:05:00+00:00"
        view = self.start(at)
        read = self.pending(view, "task_read", "task-state")
        # --result-file carries the same JSON as --result-json would.
        result_file = Path(self._tmp.name) / "result.json"
        result_file.write_text(json.dumps(self.read("idle", at)), encoding="utf-8")
        # The read is submitted twenty minutes after issue, stamped at issue:
        # inside the window, so recorded, not refused. A fresh open
        # observation arrived meanwhile through a legacy import, so the
        # result cycle judges the target by the existing freshness rule.
        late = "2026-09-17T12:25:00+00:00"
        cycle(self.store, "2026-09-17T12:20:00+00:00", observations=[self.quota_observation(remaining=50, observed_at="2026-09-17T12:20:00+00:00")])
        code, view, err = run(
            "tick", "submit", "--store", self.store, "--tick-id", view["tick"]["tick_id"],
            "--action-id", read["action_id"], "--result-file", str(result_file), "--now", late,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(view["last_result"]["consequence"], "task-state-recorded")
        self.assertEqual(view["tick"]["dispatch"]["skipped"], [{"registration_id": rid, "reason": "task-state-stale"}])
        self.assertEqual(view["tick"]["last_now"], late)
        self.pending(view, "heartbeat_set")
        # Clock mode: the wall clock regresses between two submits; the
        # transition time is clamped to the tick's last time, once reported.
        clock = str(Path(self._tmp.name) / "clock-store")
        times = {"now": aeon_bell.parse_time("2026-09-17T14:00:00+00:00", "t")}
        with mock.patch.object(aeon_bell, "_now", lambda value: times["now"]):
            code, view, err = run("tick", "start", "--store", clock, "--heartbeat", self.HEARTBEAT)
            self.assertEqual(code, 0, err)
            self.assertEqual(view["tick"]["time_mode"], "clock")
            self.assertEqual(view["tick"]["last_now"], "2026-09-17T14:00:00+00:00")
            heartbeat = self.pending(view, "heartbeat_set")
            self.assertEqual(heartbeat["arguments"]["delay_minutes"], 360)
            # --now is refused in clock mode and leaves the action pending.
            code, _, err = run(
                "tick", "submit", "--store", clock, "--tick-id", view["tick"]["tick_id"],
                "--action-id", heartbeat["action_id"], "--result-json", json.dumps(self.applied(heartbeat)),
                "--now", "2026-09-17T14:01:00+00:00",
            )
            self.assertEqual(code, 2)
            self.assertIn("tick-clock", err)
            times["now"] = aeon_bell.parse_time("2026-09-17T13:58:00+00:00", "t")
            code, view, err = run(
                "tick", "submit", "--store", clock, "--tick-id", view["tick"]["tick_id"],
                "--action-id", heartbeat["action_id"], "--result-json", json.dumps({"disposition": "failed", "reason": "control timed out"}),
            )
            self.assertEqual(code, 0, err)
            self.assertEqual(view["tick"]["last_now"], "2026-09-17T14:00:00+00:00")
            self.assertEqual(view["tick"]["actions"][0]["submitted_at"], "2026-09-17T14:00:00+00:00")
            emit = self.pending(view, "emit", "diagnostics")
            self.assertEqual(
                emit["arguments"]["text"].split("\n"),
                [
                    "aeon bell: clock-regressed: transition time clamped to the tick's last time",
                    "aeon bell: heartbeat-control: failed: control timed out",
                ],
            )
            times["now"] = aeon_bell.parse_time("2026-09-17T13:57:00+00:00", "t")
            code, final, err = run(
                "tick", "submit", "--store", clock, "--tick-id", view["tick"]["tick_id"],
                "--action-id", emit["action_id"], "--result-json", json.dumps({"emitted": True}),
            )
            self.assertEqual(code, 0, err)
            self.assertEqual(final["tick"]["status"], "complete")
            self.assertEqual(final["tick"]["diagnostics"].count("aeon bell: clock-regressed: transition time clamped to the tick's last time"), 1)
            self.assertEqual(final["last"]["finished_at"], "2026-09-17T14:00:00+00:00")

    def attempt_record(self, attempt_id: str, now: str) -> dict:
        state = json.loads(Path(self.store, "state.json").read_text(encoding="utf-8"))
        return state["attempts"][attempt_id]

    def to_pre_send(self, at: str, task_ids: tuple[str, ...] = ("task-1",)) -> dict:
        view = self.start(at)
        for _ in task_ids:
            view = self.submit_ok(view, self.read("idle", at), at)
        self.pending(view, "task_read", "pre-send")
        return view

    def test_pre_send_read_not_idle_or_stale_reports_not_sent(self) -> None:
        rid = self.register()["registration_id"]
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        at = "2026-09-17T12:05:00+00:00"
        # Not idle at the pre-send read: no send, not_sent with the read as evidence.
        view = self.to_pre_send(at)
        attempt_id = view["pending_action"]["arguments"]["attempt_id"]
        view = self.submit_ok(view, self.read("running", at), at)
        self.assertEqual(view["last_result"]["consequence"], "attempt-not-sent")
        self.assertEqual(view["tick"]["dispatch"]["attempts"], [{"attempt_id": attempt_id, "registration_id": rid, "stage": "pre-send", "result": "not_sent"}])
        self.assertEqual(self.attempt_record(attempt_id, at)["evidence"], {"read": "running", "reason": None})
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        self.assertEqual((inspected["registrations"][0]["status"], inspected["registrations"][0]["attempt_count"]), ("waiting", 1))
        emit = self.pending(view, "emit", "notice")
        self.assertIn(f"attempt {attempt_id} for registration {rid} (quota_recovery synthetic-account-a/cli) not_sent", emit["arguments"]["text"])
        self.assertNotIn("send", [a["kind"] for a in view["tick"]["actions"]])
        view = self.submit_ok(view, {"emitted": True}, at)
        self.complete_quietly(view, at)
        # An idle read that is stale by the time it is submitted is recorded
        # and refused as a send: the existing 15-minute task-state rule holds.
        view = self.to_pre_send(at)
        attempt_id = view["pending_action"]["arguments"]["attempt_id"]
        late = "2026-09-17T12:21:00+00:00"
        view = self.submit_ok(view, self.read("idle", at), late)
        self.assertEqual(view["last_result"]["disposition"], "performed")
        self.assertEqual(view["last_result"]["consequence"], "attempt-not-sent")
        self.assertEqual(self.attempt_record(attempt_id, late)["evidence"], {"read": "idle", "reason": "task-state-stale"})
        self.assertEqual(view["tick"]["actions"][-2]["recorded"], {"status": "idle"})
        self.assertNotIn("send", [a["kind"] for a in view["tick"]["actions"]])
        view = self.submit_ok(view, {"emitted": True}, late)
        self.complete_quietly(view, late)
        # Gate evidence that aged past its freshness while the read was fresh
        # refuses the send on its own account.
        cycle(self.store, late, observations=[self.quota_observation(remaining=50, observed_at=late)])
        view = self.to_pre_send("2026-09-17T12:22:00+00:00")
        attempt_id = view["pending_action"]["arguments"]["attempt_id"]
        _, inspected, _ = run("inspect", "--store", self.store, "--now", late)
        self.assertEqual(inspected["unresolved_attempts"][0]["attempt_id"], attempt_id)
        read_at = "2026-09-17T12:33:00+00:00"  # the read stays fresh until 12:48
        submit_at = "2026-09-17T12:37:00+00:00"  # the 12:21 observation expired at 12:36
        view = self.submit_ok(view, self.read("idle", read_at), submit_at)
        self.assertEqual(view["last_result"]["consequence"], "attempt-not-sent")
        self.assertEqual(self.attempt_record(attempt_id, submit_at)["evidence"], {"read": "idle", "reason": "gate-observation-stale"})
        self.assertNotIn("send", [a["kind"] for a in view["tick"]["actions"]])
        _, inspected, _ = run("inspect", "--store", self.store, "--now", submit_at)
        self.assertEqual((inspected["registrations"][0]["status"], inspected["registrations"][0]["attempt_count"]), ("unresolved", 3))
        self.assertEqual(inspected["registrations"][0]["unresolved_reason"], "attempt-limit")

    def test_replaced_gate_observation_uses_the_reserved_observation_window(self) -> None:
        cases = (
            ("inside", "2026-09-17T12:10:00+00:00", None, True),
            ("outside", "2026-09-17T12:16:00+00:00", None, False),
            (
                "shorter replacement expiry",
                "2026-09-17T12:10:00+00:00",
                "2026-09-17T12:07:00+00:00",
                True,
            ),
        )
        for index, (label, submit_at, replacement_expiry, sends) in enumerate(cases):
            with self.subTest(label=label):
                self.store = str(Path(self._tmp.name) / f"replacement-{index}")
                self.register()
                cycle(
                    self.store,
                    T0,
                    observations=[self.quota_observation(remaining=50)],
                )
                view = self.to_pre_send("2026-09-17T12:05:00+00:00")
                attempt_id = view["pending_action"]["arguments"]["attempt_id"]
                replacement = self.quota_observation(
                    remaining=0,
                    observed_at="2026-09-17T12:06:00+00:00",
                )
                if replacement_expiry is not None:
                    replacement["expires_at"] = replacement_expiry
                code, _, err = cycle(
                    self.store,
                    "2026-09-17T12:06:00+00:00",
                    observations=[replacement],
                )
                self.assertEqual(code, 0, err)
                view = self.submit_ok(view, self.read("idle", submit_at), submit_at)
                if sends:
                    self.assertEqual(self.pending(view, "send")["arguments"]["attempt_id"], attempt_id)
                else:
                    self.assertNotIn("send", [action["kind"] for action in view["tick"]["actions"]])
                    self.assertEqual(
                        self.attempt_record(attempt_id, submit_at)["evidence"],
                        {"read": "idle", "reason": "gate-observation-stale"},
                    )

    def test_send_dispositions_map_truthfully_and_late_results_are_recorded(self) -> None:
        ids = {t: self.register(task_id=t)["registration_id"] for t in ("task-1", "task-2", "task-3")}
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        at = "2026-09-17T12:05:00+00:00"
        view = self.to_pre_send(at, ("task-1", "task-2", "task-3"))

        def send_for(view: dict, task_id: str, now: str, result: dict, consequence: str) -> tuple[dict, str]:
            pre = self.pending(view, "task_read", "pre-send")
            self.assertEqual(pre["arguments"]["task_id"], task_id)
            view = self.submit_ok(view, self.read("idle", now), now)
            send = self.pending(view, "send", "wake")
            self.assertEqual(send["arguments"]["task_id"], task_id)
            return view, send["arguments"]["attempt_id"]

        # not_performed: refused before any effect -> not_sent with the disposition as evidence.
        view, first = send_for(view, "task-1", at, {}, "")
        view = self.submit_ok(view, {"disposition": "not_performed", "reason": "tool refused: target archived"}, at)
        self.assertEqual(view["last_result"], {"action_id": view["tick"]["actions"][-2]["action_id"], "disposition": "not_performed", "consequence": "attempt-not-sent"})
        self.assertEqual(self.attempt_record(first, at), {**self.attempt_record(first, at), "status": "not_sent", "evidence": {"disposition": "not_performed", "reason": "tool refused: target archived"}})
        # failed: invoked with no interpretable answer -> unknown, never retried.
        view, second = send_for(view, "task-2", at, {}, "")
        view = self.submit_ok(view, {"disposition": "failed", "reason": "timeout after send"}, at)
        self.assertEqual(view["last_result"]["consequence"], "attempt-unknown")
        self.assertEqual(self.attempt_record(second, at)["status"], "unknown")
        self.assertEqual(self.attempt_record(second, at)["evidence"], {"disposition": "failed", "reason": "timeout after send"})
        # A known result of a send that already happened is recorded however late.
        view, third = send_for(view, "task-3", at, {}, "")
        late = "2026-09-17T13:00:00+00:00"
        view = self.submit_ok(view, {"outcome": "accepted", "evidence": {"tool_message_id": "synthetic-77"}}, late)
        self.assertEqual(view["last_result"]["consequence"], "attempt-accepted")
        self.assertEqual(self.attempt_record(third, late)["resolved_at"], late)
        self.assertEqual(view["tick"]["actions"][-2]["recorded"], {"outcome": "accepted", "attempt_id": third})
        _, inspected, _ = run("inspect", "--store", self.store, "--now", late)
        by_task = {r["task_id"]: r for r in inspected["registrations"]}
        self.assertEqual((by_task["task-1"]["status"], by_task["task-1"]["attempt_count"]), ("waiting", 1))
        self.assertEqual((by_task["task-2"]["status"], by_task["task-2"]["unresolved_reason"]), ("unresolved", "delivery-unknown"))
        self.assertEqual(by_task["task-3"]["status"], "completed")
        self.assertEqual(
            [w["result"] for w in view["tick"]["dispatch"]["attempts"]],
            ["not_sent", "unknown", "accepted"],
        )
        emit = self.pending(view, "emit", "notice")
        self.assertEqual(emit["arguments"]["text"].count("event: attempt"), 3)
        self.assertIn("unknown_requires_reconciliation", emit["arguments"]["text"])
        view = self.submit_ok(view, {"emitted": True}, late)
        final = self.complete_quietly(view, late)
        self.assertEqual([w["result"] for w in final["outcome_when_complete"]["wakes"]], ["not_sent", "unknown", "accepted"])
        # Second tick: unavailable -> not_sent (attempt 2); outcome unknown -> unknown.
        run("rearm", "--store", self.store, "--registration-id", ids["task-2"], "--owner", "owner-a", "--episode", "episode-2", "--now", late)
        cycle(self.store, late, observations=[self.quota_observation(remaining=50, observed_at=late)])
        next_at = "2026-09-17T13:01:00+00:00"
        view = self.to_pre_send(next_at, ("task-1", "task-2"))
        view, fourth = send_for(view, "task-1", next_at, {}, "")
        view = self.submit_ok(view, {"disposition": "unavailable", "reason": "no send-follow-up tool for this host"}, next_at)
        self.assertEqual(view["last_result"]["consequence"], "attempt-not-sent")
        view, fifth = send_for(view, "task-2", next_at, {}, "")
        self.assertEqual(self.status(next_at)["pending_action"]["arguments"]["episode"], "episode-2")
        view = self.submit_ok(view, {"outcome": "unknown", "evidence": {"tool": "ambiguous response"}}, next_at)
        self.assertEqual(view["last_result"]["consequence"], "attempt-unknown")
        view = self.submit_ok(view, {"emitted": True}, next_at)
        self.complete_quietly(view, next_at)
        # Third tick: a third not_sent exhausts the episode.
        third_at = "2026-09-17T13:05:00+00:00"
        view = self.to_pre_send(third_at)
        view, sixth = send_for(view, "task-1", third_at, {}, "")
        view = self.submit_ok(view, {"outcome": "not_sent", "evidence": {"tool": "refused"}}, third_at)
        _, inspected, _ = run("inspect", "--store", self.store, "--now", third_at)
        by_task = {r["task_id"]: r for r in inspected["registrations"]}
        self.assertEqual((by_task["task-1"]["status"], by_task["task-1"]["unresolved_reason"], by_task["task-1"]["attempt_count"]), ("unresolved", "attempt-limit", 3))
        self.assertEqual((by_task["task-2"]["status"], by_task["task-2"]["unresolved_reason"]), ("unresolved", "delivery-unknown"))
        emit = self.pending(view, "emit", "notice")
        self.assertIn("attempt limit reached", emit["arguments"]["text"])

    def test_owner_and_legacy_actions_during_a_tick_are_superseded_not_errors(self) -> None:
        ids = {t: self.register(task_id=t)["registration_id"] for t in ("task-1", "task-2")}
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        at = "2026-09-17T12:05:00+00:00"
        # Owner rearm while the send is pending: the submitted result is
        # recorded on a superseded attempt, no event, the tick continues.
        view = self.to_pre_send(at, ("task-1", "task-2"))
        view = self.submit_ok(view, self.read("idle", at), at)
        send = self.pending(view, "send", "wake")
        old = send["arguments"]["attempt_id"]
        code, _, err = run("rearm", "--store", self.store, "--registration-id", ids["task-1"], "--owner", "owner-a", "--episode", "episode-2", "--now", at)
        self.assertEqual(code, 0, err)
        # And the owner removes task-2 before its turn: caught at recheck.
        run("remove", "--store", self.store, "--registration-id", ids["task-2"], "--owner", "owner-a", "--now", at)
        second = view["tick"]["proposals"][1]["attempt_id"]
        view = self.submit_ok(view, {"outcome": "accepted"}, at)
        self.assertEqual(view["last_result"], {"action_id": send["action_id"], "disposition": "performed", "consequence": "attempt-superseded"})
        self.assertEqual(self.attempt_record(old, at)["status"], "superseded_reserved")
        self.assertEqual(
            view["tick"]["dispatch"]["attempts"],
            [
                {"attempt_id": old, "registration_id": ids["task-1"], "stage": "send", "result": "superseded"},
                {"attempt_id": second, "registration_id": ids["task-2"], "stage": "recheck", "result": "not_sent"},
            ],
        )
        self.assertEqual(self.attempt_record(second, at)["evidence"], {"recheck": "registration-removed"})
        emit = self.pending(view, "emit", "notice")
        self.assertNotIn(old, emit["arguments"]["text"], "a superseded attempt is not an event")
        self.assertIn(f"attempt {second}", emit["arguments"]["text"])
        # A legacy acknowledge of the tick's notice before the emit submit.
        code, acked, err = run("acknowledge", "--store", self.store, "--notice-id", emit["arguments"]["notice_id"], "--now", at)
        self.assertEqual(code, 0, err)
        view = self.submit_ok(view, {"emitted": True}, at)
        self.assertEqual(view["last_result"]["consequence"], "notice-acknowledged-elsewhere")
        self.assertEqual(view["tick"]["notice"]["consequence"], "notice-acknowledged-elsewhere")
        self.assertTrue(view["tick"]["notice"]["acknowledged"])
        final = self.complete_quietly(view, at)
        self.assertEqual(final["tick"]["status"], "complete")
        # A legacy report on the tick's attempt before the send submit.
        cycle(self.store, at, observations=[self.quota_observation(remaining=50, observed_at=at)])
        view = self.to_pre_send(at)
        view = self.submit_ok(view, self.read("idle", at), at)
        send = self.pending(view, "send", "wake")
        code, _, err = self.report(send["arguments"]["attempt_id"], "not_sent", at, recheck="legacy monitor refused")
        self.assertEqual(code, 0, err)
        view = self.submit_ok(view, {"outcome": "accepted"}, at)
        self.assertEqual(view["last_result"]["consequence"], "attempt-superseded")
        self.assertEqual(self.attempt_record(send["arguments"]["attempt_id"], at)["status"], "not_sent")
        self.assertEqual(view["tick"]["dispatch"]["attempts"][0]["result"], "superseded")
        view = self.submit_ok(view, {"emitted": True}, at)
        self.assertEqual(self.complete_quietly(view, at)["tick"]["status"], "complete")

    def test_emit_failure_keeps_the_notice_pending(self) -> None:
        rid = self.register()["registration_id"]
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        at = "2026-09-17T12:05:00+00:00"
        view = self.to_pre_send(at)
        view = self.submit_ok(view, self.read("idle", at), at)
        view = self.submit_ok(view, {"outcome": "accepted"}, at)
        emit = self.pending(view, "emit", "notice")
        notice_id = emit["arguments"]["notice_id"]
        view = self.submit_ok(view, {"disposition": "failed", "reason": "print channel closed"}, at)
        self.assertEqual(view["last_result"]["consequence"], "notice-still-pending")
        self.assertEqual(view["tick"]["notice"], {"notice_id": notice_id, "replayed": False, "emitted": False, "acknowledged": False, "consequence": "notice-still-pending"})
        heartbeat = self.pending(view, "heartbeat_set")
        self.assertEqual(heartbeat["arguments"]["rule"], "schedule-as-printed")
        self.assertEqual(heartbeat["arguments"]["basis"]["schedule_reason"], "notice-pending")
        self.assertEqual(heartbeat["arguments"]["target_at"], "2026-09-17T12:20:00+00:00")
        view = self.submit_ok(view, self.applied(heartbeat), at)
        diagnostics = self.pending(view, "emit", "diagnostics")
        self.assertEqual(diagnostics["arguments"]["text"], f"aeon bell: notice-unrelayed: {notice_id} stays pending")
        final = self.submit_ok(view, {"emitted": True}, at)
        self.assertEqual(final["outcome_when_complete"]["notice"], {"notice_id": notice_id, "acknowledged": False, "replayed": False})
        _, pending, _ = run("notice", "--store", self.store, "--now", at)
        self.assertEqual((pending["notice_id"], pending["replayed"]), (notice_id, True))

    def test_restart_with_pending_send_is_explicit_and_safe(self) -> None:
        rid = self.register()["registration_id"]
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        at = "2026-09-17T12:05:00+00:00"
        view = self.to_pre_send(at)
        view = self.submit_ok(view, self.read("idle", at), at)
        send = self.pending(view, "send", "wake")
        attempt_id = send["arguments"]["attempt_id"]
        old_tick = view["tick"]["tick_id"]
        # The monitor lost its context here. A fresh actor sees abandon-only
        # advice and cannot start a second tick without saying so.
        status = self.status(at)
        self.assertEqual(status["pending_action"]["restart"], "abandon-only")
        self.assertEqual(status["pending_action"]["action_id"], send["action_id"])
        self.assertEqual(status["tick"]["started_at"], at)
        code, _, err = self.tick_start(at, "--heartbeat", self.HEARTBEAT)
        self.assertEqual(code, 2)
        self.assertIn(f"tick-in-progress: tick {old_tick} is running", err)
        code, _, err = self.tick_start(at, "--heartbeat", self.HEARTBEAT, "--abandon", "0" * 24)
        self.assertEqual(code, 2)
        self.assertIn("tick-in-progress", err)
        view = self.start(at, "--abandon", old_tick)
        self.assertNotEqual(view["tick"]["tick_id"], old_tick)
        self.assertEqual(view["last"]["tick_id"], old_tick)
        self.assertEqual(view["last"]["status"], "abandoned")
        self.assertEqual(
            view["last"]["abandoned_pending"],
            {"action_id": send["action_id"], "kind": "send", "purpose": "wake", "attempt_id": attempt_id, "notice_id": None},
        )
        self.assertEqual([a["disposition"] for a in view["last"]["actions"]], ["performed", "performed", "pending"])
        # The attempt stays reserved with the existing reconcile guidance; the
        # new tick never re-proposes it and relays it as stuck work.
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        [entry] = inspected["attention"]
        self.assertEqual((entry["status"], entry["attempt_id"]), ("reserved", attempt_id))
        self.assertIn(f"reconcile --attempt-id {attempt_id}", entry["next_action"])
        self.assertEqual(view["tick"]["registration_order"], [], "a reserved registration is not read")
        self.assertEqual(view["tick"]["dispatch"]["skipped"], [{"registration_id": rid, "reason": "registration-reserved"}])
        emit = self.pending(view, "emit", "notice")
        self.assertIn(f"new: registration {rid} reserved since {at}", emit["arguments"]["text"])
        self.assertIn(f"attempt {attempt_id}", emit["arguments"]["text"])
        view = self.submit_ok(view, {"emitted": True}, at)
        final = self.complete_quietly(view, at)
        self.assertEqual(final["tick"]["status"], "complete")
        # Later, the actor who checked the transcript reconciles with evidence.
        code, reconciled, err = run(
            "reconcile", "--store", self.store, "--attempt-id", attempt_id, "--resolution", "accepted",
            "--evidence-json", json.dumps({"transcript": "wake message found in target"}), "--now", at,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(reconciled["registration"]["status"], "completed")
        # A second start with the abandoned id now names a tick that is not running.
        code, _, err = self.tick_start(at, "--heartbeat", self.HEARTBEAT, "--abandon", old_tick)
        self.assertEqual(code, 2)
        self.assertIn("tick-not-running", err)
        # The completed tick is now `last`, so the abandoned id is unknown: a
        # late submit for its send can never be applied.
        code, _, err = run("tick", "submit", "--store", self.store, "--tick-id", old_tick, "--action-id", send["action_id"], "--result-json", json.dumps({"outcome": "accepted"}), "--now", at)
        self.assertEqual(code, 2)
        self.assertIn("unknown-tick", err)
        code, _, err = run("tick", "submit", "--store", self.store, "--tick-id", final["tick"]["tick_id"], "--action-id", send["action_id"], "--result-json", json.dumps({"outcome": "accepted"}), "--now", at)
        self.assertEqual(code, 2)
        self.assertIn("tick-not-running", err)

    def test_restart_with_pending_read_is_resumable_and_pending_notice_replays(self) -> None:
        rid = self.register()["registration_id"]
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        at = "2026-09-17T12:05:00+00:00"
        view = self.start(at)
        # Context lost after the read was issued: status says resume, and the
        # submitted read proceeds exactly as if nothing had happened.
        status = self.status(at)
        self.assertEqual((status["pending_action"]["kind"], status["pending_action"]["restart"]), ("task_read", "resumable"))
        self.assertIsNone(status["last_result"])
        view = self.submit_ok(status, self.read("idle", at), at)
        pre = self.pending(view, "task_read", "pre-send")
        self.assertEqual(self.status(at)["pending_action"]["restart"], "resumable")
        self.assertEqual(self.status(at)["last_result"]["consequence"], "task-state-recorded")
        view = self.submit_ok(self.status(at), self.read("idle", at), at)
        view = self.submit_ok(view, {"outcome": "accepted"}, at)
        emit = self.pending(view, "emit", "notice")
        notice_id = emit["arguments"]["notice_id"]
        self.assertEqual(self.status(at)["pending_action"]["restart"], "abandon-only")
        # Abandon while the notice emit is pending: the next tick's emit
        # carries the same notice as a replay and acknowledges it once.
        old_tick = view["tick"]["tick_id"]
        view = self.start(at, "--abandon", old_tick)
        self.assertEqual(view["last"]["abandoned_pending"]["notice_id"], notice_id)
        self.assertEqual(view["last"]["abandoned_pending"]["kind"], "emit")
        replay = self.pending(view, "emit", "notice")
        self.assertEqual(replay["arguments"]["notice_id"], notice_id)
        self.assertTrue(replay["arguments"]["replayed"])
        self.assertEqual(replay["arguments"]["text"], emit["arguments"]["text"])
        view = self.submit_ok(view, {"emitted": True}, at)
        self.assertEqual(view["last_result"]["consequence"], "notice-acknowledged")
        final = self.complete_quietly(view, at)
        self.assertEqual(final["outcome_when_complete"]["notice"], {"notice_id": notice_id, "acknowledged": True, "replayed": True})
        _, quiet, _ = run("notice", "--store", self.store, "--now", at)
        self.assertFalse(quiet["report"])
        # An observe pending across a restart is resumable too: a stale
        # closed observation makes the next tick query.
        _, _, _ = run("rearm", "--store", self.store, "--registration-id", rid, "--owner", "owner-a", "--episode", "episode-2", "--now", at)
        cycle(self.store, at, observations=[self.quota_observation(remaining=0, observed_at=at)])
        later = "2026-09-17T13:10:00+00:00"
        view = self.start(later, "--binding", "b.json")
        view = self.submit_ok(view, self.read("idle", later), later)
        self.pending(view, "observe")
        status = self.status(later)
        self.assertEqual((status["pending_action"]["kind"], status["pending_action"]["restart"]), ("observe", "resumable"))
        self.assertTrue((self.artifacts(view) / "plan.json").exists(), "plan.json is kept for the resumed observe")
        self.assertEqual(status["pending_action"]["arguments"]["argv"], view["pending_action"]["arguments"]["argv"])

    def test_concurrent_tick_start_admits_one(self) -> None:
        self.register()
        argv = [sys.executable, str(SCRIPT), "tick", "start", "--store", self.store, "--heartbeat", self.HEARTBEAT, "--now", T0]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            runs = list(pool.map(lambda _: subprocess.run(argv, capture_output=True, text=True, check=False), range(4)))
        codes = sorted(r.returncode for r in runs)
        self.assertEqual(codes, [0, 2, 2, 2], [r.stderr for r in runs])
        for completed in runs:
            if completed.returncode == 2:
                self.assertIn("aeon bell: tick-in-progress:", completed.stderr)
                self.assertEqual(completed.stdout, "")
        [started] = [json.loads(r.stdout) for r in runs if r.returncode == 0]
        self.assertEqual(self.status(T0)["tick"]["tick_id"], started["tick"]["tick_id"])
        self.assertEqual(self.status(T0)["pending_action"]["action_id"], started["pending_action"]["action_id"])

    def test_ordered_task_reads_and_bounded_diagnostics(self) -> None:
        ids = [self.register(task_id=f"task-{n}", episode=f"episode-{n}")["registration_id"] for n in (1, 2, 3)]
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        at = "2026-09-17T12:05:00+00:00"
        view = self.start(at)
        self.assertEqual(view["tick"]["registration_order"], ids)
        for n, rid in enumerate(ids, start=1):
            read = self.pending(view, "task_read", "task-state")
            self.assertEqual((read["arguments"]["registration_id"], read["arguments"]["task_id"], read["arguments"]["episode"]), (rid, f"task-{n}", f"episode-{n}"))
            result = {"disposition": "not_performed", "reason": "task tool unavailable"} if n == 1 else self.read("idle", at)
            view = self.submit_ok(view, result, at)
        self.assertEqual([a["consequence"] for a in view["tick"]["actions"][:3]], ["no-task-state", "task-state-recorded", "task-state-recorded"])
        self.assertEqual(view["tick"]["diagnostics"], [f"aeon bell: task-read-failed: registration {ids[0]}: not_performed: task tool unavailable"])
        self.assertEqual(view["tick"]["dispatch"]["skipped"], [{"registration_id": ids[0], "reason": "task-unknown"}])
        self.assertEqual([p["registration_id"] for p in view["tick"]["proposals"]], ids[1:])
        self.assertEqual(self.pending(view, "task_read", "pre-send")["arguments"]["registration_id"], ids[1])
        old_tick = view["tick"]["tick_id"]
        # Many failed reads: the diagnostics collapse at 32 lines plus one
        # counting line, and the emit carries exactly that.
        many = str(Path(self._tmp.name) / "many-store")
        for n in range(1, 36):
            code, _, err = run(
                "register", "--store", many, "--owner", "owner-a", "--host", "host-a", "--task-id", f"task-{n}",
                "--episode", "e", "--gate-json", json.dumps(QUOTA_GATE), "--continuation", "Continue.", "--now", T0,
            )
            self.assertEqual(code, 0, err)
        _, inspected, _ = run("inspect", "--store", many, "--now", T0)
        key = inspected["registrations"][0]["gate_key"]
        code, _, err = cycle(many, T0, observations=[dict(self.quota_observation(remaining=0), gate_key=key)])
        self.assertEqual(code, 0, err)
        code, view, err = run("tick", "start", "--store", many, "--heartbeat", self.HEARTBEAT, "--now", at)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(view["tick"]["registration_order"]), 35)
        for _ in range(35):
            code, view, err = run(
                "tick", "submit", "--store", many, "--tick-id", view["tick"]["tick_id"],
                "--action-id", view["pending_action"]["action_id"],
                "--result-json", json.dumps({"disposition": "unavailable", "reason": "no task tool"}), "--now", at,
            )
            self.assertEqual(code, 0, err)
        lines = view["tick"]["diagnostics"]
        self.assertEqual(len(lines), 33)
        self.assertTrue(all(line.startswith("aeon bell: task-read-failed: registration ") for line in lines[:32]))
        self.assertEqual(lines[32], "aeon bell: diagnostics-truncated: 3 further line(s) omitted")
        heartbeat = self.pending(view, "heartbeat_set")
        code, view, err = run(
            "tick", "submit", "--store", many, "--tick-id", view["tick"]["tick_id"], "--action-id", heartbeat["action_id"],
            "--result-json", json.dumps(self.applied(heartbeat)), "--now", at,
        )
        self.assertEqual(code, 0, err)
        emit = self.pending(view, "emit", "diagnostics")
        self.assertEqual(emit["arguments"]["text"], "\n".join(lines))
        self.assertEqual(len(emit["arguments"]["text"].split("\n")), 33)

    def test_malformed_tick_state_is_refused_not_used(self) -> None:
        rid = self.register()["registration_id"]
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        at = "2026-09-17T12:05:00+00:00"
        view = self.to_pre_send(at)
        view = self.submit_ok(view, self.read("idle", at), at)
        send = self.pending(view, "send", "wake")
        tick_id = view["tick"]["tick_id"]
        artifacts = Path(self.store) / "ticks" / tick_id
        artifacts.mkdir(parents=True)
        (artifacts / "plan.json").write_text("{}", encoding="utf-8")
        state_path = Path(self.store, "state.json")
        good = state_path.read_bytes()
        secret = "SYNTHETIC-TICK-SECRET-4d2e"

        def mutate(change) -> bytes:
            state = json.loads(good.decode("utf-8"))
            change(state["tick"])
            state_path.write_text(json.dumps(state), encoding="utf-8")
            return state_path.read_bytes()

        def second_pending(tick: dict) -> None:
            tick["current"]["actions"].insert(0, dict(tick["current"]["actions"][-1], action_id="a" * 12))

        cases = (
            ("message digest mismatch", lambda t: t["current"]["proposals"][0].update(message="tampered " + secret)),
            ("unknown phase", lambda t: t["current"].update(phase=secret)),
            ("registration_order names no registration", lambda t: t["current"].update(registration_order=[secret])),
            ("two pending actions", second_pending),
            ("unknown key", lambda t: t["current"].update(extra=secret)),
            ("last summary malformed", lambda t: t.update(last={"tick_id": secret})),
            ("not an object", lambda t: t.update(current=[secret])),
        )
        for label, change in cases:
            with self.subTest(label=label):
                malformed = mutate(change)
                for argv in (
                    ["tick", "status"],
                    ["tick", "submit", "--tick-id", tick_id, "--action-id", send["action_id"], "--result-json", json.dumps({"outcome": "accepted"})],
                    ["tick", "start", "--heartbeat", self.HEARTBEAT],
                    ["tick", "start", "--heartbeat", self.HEARTBEAT, "--abandon", tick_id],
                ):
                    code, payload, err = run(*argv, "--store", self.store, "--now", at)
                    self.assertEqual(code, 2, argv)
                    self.assertIsNone(payload)
                    self.assertIn("aeon bell: corrupt-store:", err)
                    self.assertNotIn(secret, err)
                    self.assertNotIn("Traceback", err)
                self.assertEqual(state_path.read_bytes(), malformed, "nothing rewritten")
                self.assertTrue((artifacts / "plan.json").exists(), "no artifact removed")
                code, inspected, err = run("inspect", "--store", self.store, "--now", at)
                self.assertEqual(code, 0, err)
                self.assertFalse(inspected["schedule"]["registry"]["tick_readable"])
                self.assertEqual(inspected["registrations"][0]["status"], "reserved")
                code, _, err = run("notice", "--store", self.store, "--now", at)
                self.assertEqual(code, 0, err)
        # Repair: delete the key. Reservations are untouched; the next start
        # sweeps the orphaned artifact directory.
        state = json.loads(state_path.read_bytes().decode("utf-8"))
        del state["tick"]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        status = self.status(at)
        self.assertIsNone(status["tick"])
        self.assertIsNone(status["last"])
        self.assertTrue(status["schedule"]["registry"]["tick_readable"])
        view = self.start(at)
        self.assertNotEqual(view["tick"]["tick_id"], tick_id)
        self.assertFalse(artifacts.exists())
        self.assertEqual(view["tick"]["dispatch"]["skipped"], [{"registration_id": rid, "reason": "registration-reserved"}])

    def test_artifact_lifecycle_sweep_and_write_failure(self) -> None:
        # A 5-minute explicit interval keeps a query due at every tick below.
        self.register(extra=("--poll-interval-minutes", "5"))
        key = self.gate_key()
        cycle(self.store, T0, observations=[self.quota_observation(remaining=0)])
        at = "2026-09-17T13:05:00+00:00"
        ticks = Path(self.store) / "ticks"
        state_path = Path(self.store) / "state.json"
        view = self.start(at, "--binding", "b.json")
        self.assertFalse(ticks.exists(), "nothing before observe is issued")
        view = self.submit_ok(view, self.read("idle", at), at)
        self.pending(view, "observe")
        directory = self.artifacts(view)
        self.assertEqual(stat.S_IMODE(os.stat(ticks).st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(os.stat(directory).st_mode), 0o700)
        self.assertEqual(sorted(os.listdir(directory)), ["plan.json"])
        self.assertEqual(stat.S_IMODE(os.stat(state_path).st_mode), 0o600)
        self.write_artifacts(view, [self.gate_entry(key, "observed")], [self.quota_observation(remaining=0, observed_at=at)])
        view = self.submit_ok(view, {"exit_code": 0}, at)
        self.assertTrue(directory.exists(), "kept until the tick ends")
        final = self.complete_quietly(view, at)
        self.assertEqual(final["tick"]["status"], "complete")
        self.assertFalse(directory.exists())
        self.assertEqual(final["last"]["diagnostics_unemitted"], [])
        # Stale directories from lost ticks, a symlink named like one, a
        # directory with a foreign file, and an unrelated name at the next start.
        stale = ticks / ("b" * 24)
        stale.mkdir()
        (stale / "report.json").write_text("{}", encoding="utf-8")
        (stale / "input.json").write_text("{}", encoding="utf-8")
        foreign = ticks / ("c" * 24)
        foreign.mkdir()
        (foreign / "notes.txt").write_text("keep me", encoding="utf-8")
        outside = Path(self._tmp.name) / "outside"
        outside.mkdir()
        (outside / "plan.json").write_text("{}", encoding="utf-8")
        link = ticks / ("d" * 24)
        os.symlink(outside, link)
        (ticks / "README").write_text("unrelated", encoding="utf-8")
        later = "2026-09-17T13:20:00+00:00"
        view = self.start(later, "--binding", "b.json")
        self.assertFalse(stale.exists(), "a stale artifact directory is swept")
        self.assertTrue(foreign.exists() and (foreign / "notes.txt").exists(), "a foreign file is never removed")
        self.assertTrue(os.path.islink(link) and (outside / "plan.json").exists(), "a symlink is never followed")
        self.assertTrue((ticks / "README").exists())
        self.assertEqual(
            view["tick"]["diagnostics"],
            [
                f"aeon bell: artifact-io: ticks/{'c' * 24} could not be removed",
                f"aeon bell: artifact-io: ticks/{'d' * 24} could not be removed",
            ],
        )
        view = self.submit_ok(view, self.read("idle", later), later)
        running = self.artifacts(view)
        self.assertTrue((running / "plan.json").exists())
        old_tick = view["tick"]["tick_id"]
        # The running tick's own directory is never touched by another start;
        # abandoning it sweeps it.
        code, _, err = self.tick_start(later, "--heartbeat", self.HEARTBEAT)
        self.assertEqual(code, 2)
        self.assertTrue((running / "plan.json").exists())
        view = self.start(later, "--binding", "b.json", "--abandon", old_tick)
        self.assertFalse(running.exists())
        view = self.submit_ok(view, self.read("idle", later), later)
        self.pending(view, "observe")
        old_tick = view["tick"]["tick_id"]
        # Write failure: the artifact root cannot hold a directory. The sweep
        # reports that it could not list it, and observe is not issued.
        for name in os.listdir(ticks):
            path = ticks / name
            if os.path.islink(path) or path.is_file():
                path.unlink()
            else:
                for child in os.listdir(path):
                    (path / child).unlink()
                path.rmdir()
        ticks.rmdir()
        ticks.write_text("not a directory", encoding="utf-8")
        view = self.start(later, "--binding", "b.json", "--abandon", old_tick)
        self.assertEqual(view["tick"]["diagnostics"], ["aeon bell: artifact-io: ticks could not be listed"])
        view = self.submit_ok(view, self.read("idle", later), later)
        observe = view["tick"]["observe"]
        self.assertFalse(observe["issued"])
        self.assertEqual(observe["not_issued_reason"], "artifact-io")
        self.assertEqual(observe["unanswered_gate_keys"], [key])
        self.assertEqual(
            view["tick"]["diagnostics"],
            [
                "aeon bell: artifact-io: ticks could not be listed",
                "aeon bell: artifact-io: plan.json could not be written",
            ],
        )
        self.assertEqual(view["tick"]["phase"], "schedule")
        heartbeat = self.pending(view, "heartbeat_set")
        self.assertEqual(heartbeat["arguments"]["rule"], "failed-observation-recovery")
        view = self.submit_ok(view, self.applied(heartbeat), later)
        final = self.submit_ok(view, {"emitted": True}, later)
        self.assertEqual(final["tick"]["status"], "complete")
        self.assertEqual(ticks.read_text(encoding="utf-8"), "not a directory", "nothing outside the rule is touched")

    def test_legacy_commands_and_stores_stay_compatible(self) -> None:
        rid = self.register()["registration_id"]
        state_path = Path(self.store, "state.json")
        self.assertNotIn("tick", json.loads(state_path.read_text(encoding="utf-8")))
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        at = "2026-09-17T12:05:00+00:00"
        # A store without a tick key starts a tick; the legacy surface is
        # unchanged apart from the two additive registry fields.
        view = self.to_pre_send(at)
        registry = view["schedule"]["registry"]
        self.assertEqual(
            set(registry),
            {"counts", "attention", "pending_notice", "notification_readable", "fingerprint", "tick_in_progress", "tick_readable"},
        )
        view = self.submit_ok(view, self.read("idle", at), at)
        view = self.submit_ok(view, {"outcome": "accepted"}, at)
        view = self.submit_ok(view, {"emitted": True}, at)
        final = self.complete_quietly(view, at)
        self.assertEqual(final["tick"]["status"], "complete")
        self.assertIn("tick", json.loads(state_path.read_text(encoding="utf-8")))
        # Legacy commands run on the store carrying a completed tick.
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        self.assertEqual(set(inspected), {"registrations", "observations", "retry_schedule", "unresolved_attempts", "attention", "schedule", "limitations"})
        self.assertEqual((inspected["schedule"]["registry"]["tick_in_progress"], inspected["schedule"]["registry"]["tick_readable"]), (False, True))
        code, rearmed, err = run("rearm", "--store", self.store, "--registration-id", rid, "--owner", "owner-a", "--episode", "episode-2", "--now", at)
        self.assertEqual(code, 0, err)
        code, planned, err = cycle(self.store, at, observations=[self.quota_observation(remaining=50, observed_at=at)], task_states=[self.idle(observed_at=at)])
        self.assertEqual(code, 0, err)
        [proposal] = planned["wake_proposals"]
        self.assertEqual([s["step"] for s in proposal["native_steps"]], ["recheck", "read", "send", "report"])
        code, reported, err = self.report(proposal["attempt_id"], "not_sent", at, recheck="legacy monitor")
        self.assertEqual(code, 0, err)
        code, noticed, err = run("notice", "--store", self.store, "--now", at)
        self.assertEqual(code, 0, err)
        self.assertTrue(noticed["report"])
        code, acked, err = run("acknowledge", "--store", self.store, "--notice-id", noticed["notice_id"], "--now", at)
        self.assertEqual(code, 0, err)
        self.assertTrue(acked["acknowledged"])
        # And a tick starts again after the legacy tick, with the legacy
        # not_sent already acknowledged.
        view = self.start(at)
        self.assertEqual(view["tick"]["registration_order"], [rid])
        self.assertIsNone(view["last"]["abandoned_pending"])

    def test_tick_view_and_diagnostics_are_redacted(self) -> None:
        continuation = "Resume: SYNTHETIC-CONTINUATION-MARKER-6f1a."
        self.register(continuation=continuation)
        binding = Path(self._tmp.name) / "binding.json"
        binding.write_text('{"codex_home": "/SYNTHETIC-BINDING-SECRET-2c9d"}', encoding="utf-8")
        key = self.gate_key()
        cycle(self.store, T0, observations=[self.quota_observation(remaining=0)])
        at = "2026-09-17T13:05:00+00:00"
        views: list[dict] = []
        view = self.start(at, "--binding", str(binding))
        views.append(view)
        view = self.submit_ok(view, self.read("idle", at), at)
        views.append(view)
        self.pending(view, "observe")
        self.write_artifacts(
            view,
            [self.gate_entry(key, "observed")],
            [self.quota_observation(remaining=37.5, observed_at=at)],
        )
        view = self.submit_ok(view, {"exit_code": 0}, at)
        views.append(view)
        view = self.submit_ok(view, self.read("idle", at), at)
        send = self.pending(view, "send", "wake")
        self.assertIn("SYNTHETIC-CONTINUATION-MARKER-6f1a", send["arguments"]["message"])
        stripped = dict(view, pending_action=dict(send, arguments={}))
        views.append(stripped)
        views.append(dict(self.status(at), pending_action=dict(send, arguments={})))
        view = self.submit_ok(view, {"disposition": "not_performed", "reason": "send tool declined"}, at)
        views.append(view)
        view = self.submit_ok(view, {"emitted": True}, at)
        views.append(view)
        final = self.complete_quietly(view, at)
        views.append(final)
        views.append(self.status(at))
        for index, item in enumerate(views):
            text = json.dumps(item)
            with self.subTest(view=index):
                self.assertNotIn("SYNTHETIC-CONTINUATION-MARKER", text)
                self.assertNotIn("SYNTHETIC-BINDING-SECRET", text)
                self.assertNotIn("37.5", text)
                self.assertNotIn("remaining_percent", text)
        self.assertEqual(final["tick"]["diagnostics"], [])
        # Diagnostics lines carry engine codes, adapter lines, ids, times, and
        # counts only.
        again = "2026-09-17T13:20:00+00:00"
        run("rearm", "--store", self.store, "--registration-id", views[0]["tick"]["registration_order"][0], "--owner", "owner-a", "--episode", "episode-2", "--now", again)
        view = self.start(again, "--binding", str(binding))
        view = self.submit_ok(view, {"disposition": "unavailable", "reason": "no task tool"}, again)
        line = "codex status: invalid-binding: binding config must be private (mode 0600)"
        view = self.submit_ok(view, {"exit_code": 2, "stderr_line": line}, again)
        view = self.submit_ok(view, self.applied(view["pending_action"]), again)
        emit = self.pending(view, "emit", "diagnostics")
        lines = emit["arguments"]["text"].split("\n")
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("aeon bell: task-read-failed: registration "))
        self.assertEqual(lines[1], f"step observe: {line}")
        for needle in ("SYNTHETIC", "host-a", "task-1", "episode", "37.5", str(binding)):
            self.assertNotIn(needle, emit["arguments"]["text"])


class MonitorEntry(DirectedTick):
    """The public bound monitor entry owns store selection and sequencing."""

    def test_bound_entry_refuses_missing_registry_without_creating_it(self) -> None:
        binding = str(Path(self._tmp.name) / "binding.json")
        code, payload, err = run(
            "monitor", "bind", "--store", self.store,
            "--binding", binding, "--heartbeat", self.HEARTBEAT,
        )
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("registry-not-found", err)
        self.assertFalse(Path(self.store).exists())

        code, bound, err = run(
            "monitor", "bind", "--store", self.store, "--initialize-registry",
            "--binding", binding, "--heartbeat", self.HEARTBEAT,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(bound["status"], "bound")
        self.assertTrue(bound["store_created"])
        self.assertRegex(bound["registry_id"], r"^[0-9a-f]{32}$")
        self.assertEqual(bound["config_revision"], 1)
        self.assertTrue(bound["entry_ref"].startswith("ab1."))

        state_path = Path(self.store) / aeon_bell.STATE_NAME
        state_path.unlink()
        code, payload, err = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", T0,
        )
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("registry-not-found", err)
        self.assertFalse(state_path.exists())

    def test_copied_registry_and_stale_configuration_refuse_without_state_change(self) -> None:
        code, bound, err = run(
            "monitor", "bind", "--store", self.store, "--initialize-registry",
            "--heartbeat", self.HEARTBEAT,
        )
        self.assertEqual(code, 0, err)
        duplicate = Path(self._tmp.name) / "duplicate"
        duplicate.mkdir()
        copied_state = duplicate / aeon_bell.STATE_NAME
        copied_state.write_bytes(Path(self.store, aeon_bell.STATE_NAME).read_bytes())
        (duplicate / aeon_bell.LOCK_NAME).touch()
        wrong_ref = aeon_bell._reference(
            aeon_bell.ENTRY_REF_PREFIX,
            {
                "store": str(duplicate.resolve()),
                "registry_id": bound["registry_id"],
                "config_revision": bound["config_revision"],
            },
        )
        before = copied_state.read_bytes()
        code, payload, err = run(
            "monitor", "enter", "--entry-ref", wrong_ref, "--now", T0,
        )
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("registry-mismatch", err)
        self.assertEqual(copied_state.read_bytes(), before)

        code, revised, err = run(
            "monitor", "bind", "--store", self.store,
            "--registry-id", bound["registry_id"],
            "--binding", str(Path(self._tmp.name) / "new-binding.json"),
            "--heartbeat", self.HEARTBEAT,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(revised["config_revision"], 2)
        code, payload, err = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", T0,
        )
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("registry-mismatch", err)

    def bind_monitor(self) -> dict[str, Any]:
        code, bound, err = run(
            "monitor", "bind", "--store", self.store,
            "--binding", str(Path(self._tmp.name) / "binding.json"),
            "--heartbeat", self.HEARTBEAT,
        )
        self.assertEqual(code, 0, err)
        return bound

    def monitor_continue(self, response: dict[str, Any], result: Any, now: str) -> dict[str, Any]:
        code, next_response, err = run(
            "monitor", "continue",
            "--continuation", response["continuation"],
            "--result-json", json.dumps(result),
            "--now", now,
        )
        self.assertEqual(code, 0, err)
        return next_response

    def test_takeover_reissues_pending_pre_send_without_stranding_reservation(self) -> None:
        rid = self.register()["registration_id"]
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        bound = self.bind_monitor()
        at = "2026-09-17T12:05:00+00:00"
        later = "2026-09-17T12:07:00+00:00"

        code, first, err = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        self.assertEqual(code, 0, err)
        first = self.monitor_continue(first, self.read("idle", at), at)
        self.assertEqual(
            (first["action"]["kind"], first["action"]["purpose"]),
            ("task_read", "pre-send"),
        )
        old_continuation = first["continuation"]
        tick_id = aeon_bell._continuation_reference(old_continuation)["tick_id"]
        attempt_id = first["action"]["arguments"]["attempt_id"]

        code, takeover, err = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", later,
        )
        self.assertEqual(code, 0, err)
        self.assertGreater(takeover["generation"], first["generation"])
        self.assertNotEqual(takeover["continuation"], old_continuation)
        self.assertEqual(
            (takeover["action"]["kind"], takeover["action"]["purpose"]),
            ("task_read", "pre-send"),
        )
        self.assertEqual(takeover["action"]["arguments"]["attempt_id"], attempt_id)
        self.assertEqual(
            aeon_bell._continuation_reference(takeover["continuation"])["tick_id"],
            tick_id,
        )

        code, payload, err = run(
            "monitor", "continue", "--continuation", old_continuation,
            "--result-json", json.dumps(self.read("idle", later)), "--now", later,
        )
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("stale-invocation", err)

        takeover = self.monitor_continue(takeover, self.read("idle", later), later)
        self.assertEqual((takeover["action"]["kind"], takeover["action"]["purpose"]), ("send", "wake"))
        self.assertEqual(takeover["action"]["arguments"]["attempt_id"], attempt_id)
        send_continuation = takeover["continuation"]
        view = self.status(later)
        self.assertEqual(
            [action["kind"] for action in view["tick"]["actions"]].count("send"),
            1,
        )
        takeover = self.monitor_continue(takeover, {"outcome": "accepted"}, later)
        code, payload, err = run(
            "monitor", "continue", "--continuation", send_continuation,
            "--result-json", json.dumps({"outcome": "accepted"}), "--now", later,
        )
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("stale-result", err)
        view = self.status(later)
        self.assertEqual(
            [action["kind"] for action in view["tick"]["actions"]].count("send"),
            1,
        )
        _, inspected, _ = run("inspect", "--store", self.store, "--now", later)
        self.assertEqual(
            (inspected["registrations"][0]["registration_id"], inspected["registrations"][0]["status"]),
            (rid, "completed"),
        )

    def test_owner_remove_during_pre_send_takeover_is_not_overwritten(self) -> None:
        rid = self.register()["registration_id"]
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        bound = self.bind_monitor()
        at = "2026-09-17T12:05:00+00:00"
        _, response, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        response = self.monitor_continue(response, self.read("idle", at), at)
        attempt_id = response["action"]["arguments"]["attempt_id"]

        code, removed, err = run(
            "remove", "--store", self.store, "--registration-id", rid,
            "--owner", "owner-a", "--now", at,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(removed["status"], "removed")
        _, takeover, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        self.assertEqual(takeover["action"]["arguments"]["attempt_id"], attempt_id)
        takeover = self.monitor_continue(takeover, self.read("idle", at), at)
        self.assertNotEqual(takeover["action"]["kind"], "send")
        view = self.status(at)
        self.assertEqual(
            [action["kind"] for action in view["tick"]["actions"]].count("send"),
            0,
        )
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        self.assertEqual(inspected["registrations"], [])
        self.assertEqual(inspected["unresolved_attempts"], [])

    def test_owner_rearm_during_pre_send_takeover_preserves_new_episode(self) -> None:
        rid = self.register()["registration_id"]
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        bound = self.bind_monitor()
        at = "2026-09-17T12:05:00+00:00"
        _, response, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        response = self.monitor_continue(response, self.read("idle", at), at)
        attempt_id = response["action"]["arguments"]["attempt_id"]

        code, rearmed, err = run(
            "rearm", "--store", self.store, "--registration-id", rid,
            "--owner", "owner-a", "--episode", "episode-2", "--now", at,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual((rearmed["status"], rearmed["episode"]), ("waiting", "episode-2"))
        _, takeover, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        self.assertEqual(takeover["action"]["arguments"]["attempt_id"], attempt_id)
        takeover = self.monitor_continue(takeover, self.read("idle", at), at)
        self.assertNotEqual(takeover["action"]["kind"], "send")
        view = self.status(at)
        self.assertEqual(
            [action["kind"] for action in view["tick"]["actions"]].count("send"),
            0,
        )
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        [registration] = inspected["registrations"]
        self.assertEqual(
            (registration["status"], registration["episode"], registration["attempt_id"]),
            ("waiting", "episode-2", None),
        )

    def test_expiry_during_pre_send_takeover_reports_not_sent(self) -> None:
        rid = self.register(extra=("--expires-in-minutes", "6"))["registration_id"]
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        bound = self.bind_monitor()
        at = "2026-09-17T12:05:00+00:00"
        expired_at = "2026-09-17T12:07:00+00:00"
        _, response, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        response = self.monitor_continue(response, self.read("idle", at), at)
        attempt_id = response["action"]["arguments"]["attempt_id"]

        _, takeover, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", expired_at,
        )
        self.assertEqual(takeover["action"]["arguments"]["attempt_id"], attempt_id)
        takeover = self.monitor_continue(
            takeover, self.read("idle", expired_at), expired_at
        )
        self.assertNotEqual(takeover["action"]["kind"], "send")
        view = self.status(expired_at)
        self.assertEqual(
            [action["kind"] for action in view["tick"]["actions"]].count("send"),
            0,
        )
        _, inspected, _ = run("inspect", "--store", self.store, "--now", expired_at)
        [registration] = inspected["registrations"]
        self.assertEqual(
            (registration["registration_id"], registration["status"], registration["expired"]),
            (rid, "waiting", True),
        )
        self.assertEqual(inspected["unresolved_attempts"], [])

    def test_legacy_report_during_pre_send_takeover_is_not_overwritten(self) -> None:
        rid = self.register()["registration_id"]
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        bound = self.bind_monitor()
        at = "2026-09-17T12:05:00+00:00"
        _, response, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        response = self.monitor_continue(response, self.read("idle", at), at)
        attempt_id = response["action"]["arguments"]["attempt_id"]

        code, reported, err = self.report(
            attempt_id, "not_sent", at, recheck="legacy monitor"
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(reported["registration"]["status"], "waiting")
        _, takeover, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        self.assertEqual(takeover["action"]["arguments"]["attempt_id"], attempt_id)
        takeover = self.monitor_continue(takeover, self.read("idle", at), at)
        self.assertNotEqual(takeover["action"]["kind"], "send")
        view = self.status(at)
        self.assertEqual(
            [action["kind"] for action in view["tick"]["actions"]].count("send"),
            0,
        )
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        [registration] = inspected["registrations"]
        self.assertEqual(
            (registration["registration_id"], registration["status"]),
            (rid, "waiting"),
        )
        self.assertEqual(inspected["unresolved_attempts"], [])

    def test_takeover_reissues_observe_with_the_same_engine_owned_artifacts(self) -> None:
        self.register()
        key = self.gate_key()
        bound = self.bind_monitor()
        at = "2026-09-17T12:05:00+00:00"
        later = "2026-09-17T12:07:00+00:00"
        _, response, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        response = self.monitor_continue(response, self.read("idle", at), at)
        self.assertEqual(
            (response["action"]["kind"], response["action"]["purpose"]),
            ("observe", "query"),
        )
        old_continuation = response["continuation"]
        old_ref = aeon_bell._continuation_reference(old_continuation)
        argv = response["action"]["arguments"]["argv"]
        artifact_directory = Path(self.store) / "ticks" / old_ref["tick_id"]
        self.assertTrue((artifact_directory / "plan.json").is_file())

        _, takeover, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", later,
        )
        self.assertGreater(takeover["generation"], response["generation"])
        self.assertNotEqual(takeover["continuation"], old_continuation)
        self.assertEqual(
            aeon_bell._continuation_reference(takeover["continuation"])["tick_id"],
            old_ref["tick_id"],
        )
        self.assertEqual(
            (takeover["action"]["kind"], takeover["action"]["purpose"]),
            ("observe", "query"),
        )
        self.assertEqual(takeover["action"]["arguments"]["argv"], argv)
        self.assertTrue((artifact_directory / "plan.json").is_file())

        code, payload, err = run(
            "monitor", "continue", "--continuation", old_continuation,
            "--result-json", json.dumps({"exit_code": 0}), "--now", later,
        )
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("stale-invocation", err)

        view = self.status(later)
        self.write_artifacts(
            view,
            [self.gate_entry(key, "observed")],
            [self.quota_observation(remaining=50, observed_at=later)],
        )
        takeover = self.monitor_continue(takeover, {"exit_code": 0}, later)
        self.assertEqual(
            (takeover["action"]["kind"], takeover["action"]["purpose"]),
            ("task_read", "pre-send"),
        )
        self.assertEqual(
            aeon_bell._continuation_reference(takeover["continuation"])["tick_id"],
            old_ref["tick_id"],
        )

    def test_fresh_entry_over_pending_send_retains_reservation_and_never_replays(self) -> None:
        rid = self.register()["registration_id"]
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        bound = self.bind_monitor()
        at = "2026-09-17T12:05:00+00:00"

        code, response, err = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(response["action"]["kind"], "task_read")
        response = self.monitor_continue(response, self.read("idle", at), at)
        self.assertEqual(response["action"]["purpose"], "pre-send")
        response = self.monitor_continue(response, self.read("idle", at), at)
        self.assertEqual(response["action"]["kind"], "send")
        attempt_id = response["action"]["arguments"]["attempt_id"]

        code, takeover, err = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        self.assertEqual(code, 0, err)
        self.assertNotEqual(takeover["invocation_id"], response["invocation_id"])
        self.assertGreater(takeover["generation"], response["generation"])
        self.assertNotEqual(takeover["action"]["kind"], "send")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        [attention] = inspected["attention"]
        self.assertEqual(
            (attention["registration_id"], attention["attempt_id"], attention["status"]),
            (rid, attempt_id, "reserved"),
        )

    def test_superseded_send_accepts_one_truthful_late_result(self) -> None:
        self.register()
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        bound = self.bind_monitor()
        at = "2026-09-17T12:05:00+00:00"
        _, response, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        response = self.monitor_continue(response, self.read("idle", at), at)
        response = self.monitor_continue(response, self.read("idle", at), at)
        old_continuation = response["continuation"]
        run("monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at)

        code, stopped, err = run(
            "monitor", "continue", "--continuation", old_continuation,
            "--result-json", json.dumps({"outcome": "accepted"}), "--now", at,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(
            stopped,
            {
                "status": "stopped",
                "reason": "superseded-invocation",
                "late_result": "recorded",
            },
        )
        code, stopped, err = run(
            "monitor", "continue", "--continuation", old_continuation,
            "--result-json", json.dumps({"outcome": "accepted"}), "--now", at,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(stopped["late_result"], "already-settled")
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        self.assertEqual(inspected["registrations"][0]["status"], "completed")

    def test_monitor_status_is_redacted_and_never_resumes_work(self) -> None:
        self.register(task_id="SENSITIVE-TARGET", continuation="SENSITIVE-CONTINUATION")
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        bound = self.bind_monitor()
        at = "2026-09-17T12:05:00+00:00"
        _, response, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        code, initial_status, err = run(
            "monitor", "status", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        self.assertEqual(code, 0, err)
        self.assertNotIn("SENSITIVE-TARGET", json.dumps(initial_status))
        response = self.monitor_continue(response, self.read("idle", at), at)
        response = self.monitor_continue(response, self.read("idle", at), at)
        self.assertEqual(response["action"]["kind"], "send")

        code, status, err = run(
            "monitor", "status", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(status["active_invocation"]["pending"]["kind"], "send")
        self.assertEqual(
            status["active_invocation"]["pending"]["interruption_class"],
            "effect_may_have_happened",
        )
        text = json.dumps(status)
        for secret in (
            "SENSITIVE-CONTINUATION",
            response["continuation"],
            response["action"]["arguments"]["message"],
            response["action"]["arguments"]["task_id"],
            str(Path(self._tmp.name) / "binding.json"),
            self.HEARTBEAT,
        ):
            self.assertNotIn(secret, text)
        code, again, err = run(
            "monitor", "status", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(again, status)

    def test_safe_result_from_superseded_generation_is_rejected_and_continuations_are_single_use(self) -> None:
        self.register()
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        bound = self.bind_monitor()
        at = "2026-09-17T12:05:00+00:00"
        _, first, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        _, second, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        self.assertEqual(second["action"]["kind"], "task_read")
        code, payload, err = run(
            "monitor", "continue", "--continuation", first["continuation"],
            "--result-json", json.dumps(self.read("idle", at)), "--now", at,
        )
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("stale-invocation", err)

        next_response = self.monitor_continue(second, self.read("idle", at), at)
        code, payload, err = run(
            "monitor", "continue", "--continuation", second["continuation"],
            "--result-json", json.dumps(self.read("idle", at)), "--now", at,
        )
        self.assertEqual(code, 2)
        self.assertIsNone(payload)
        self.assertIn("stale-result", err)
        code, status, err = run(
            "monitor", "status", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(status["active_invocation"]["pending"]["purpose"], next_response["action"]["purpose"])

    def test_interrupted_diagnostics_are_replayed_by_the_new_generation(self) -> None:
        code, bound, err = run(
            "monitor", "bind", "--store", self.store, "--initialize-registry",
            "--heartbeat", self.HEARTBEAT,
        )
        self.assertEqual(code, 0, err)
        _, response, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", T0,
        )
        self.assertEqual(response["action"]["kind"], "heartbeat_set")
        response = self.monitor_continue(
            response,
            {"disposition": "failed", "reason": "heartbeat control timed out"},
            T0,
        )
        self.assertEqual((response["action"]["kind"], response["action"]["purpose"]), ("emit", "diagnostics"))
        expected = response["action"]["arguments"]["text"]

        _, takeover, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", T0,
        )
        self.assertEqual(takeover["action"]["kind"], "heartbeat_set")
        takeover = self.monitor_continue(
            takeover,
            {
                "applied": True,
                "next_run_at": takeover["action"]["arguments"]["target_at"],
            },
            T0,
        )
        self.assertEqual((takeover["action"]["kind"], takeover["action"]["purpose"]), ("emit", "diagnostics"))
        self.assertEqual(takeover["action"]["arguments"]["text"], expected)

    def test_notice_replays_and_heartbeat_recomputes_across_takeover(self) -> None:
        self.register()
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        bound = self.bind_monitor()
        at = "2026-09-17T12:05:00+00:00"
        _, response, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        response = self.monitor_continue(response, self.read("idle", at), at)
        response = self.monitor_continue(response, self.read("idle", at), at)
        response = self.monitor_continue(response, {"outcome": "accepted"}, at)
        self.assertEqual((response["action"]["kind"], response["action"]["purpose"]), ("emit", "notice"))
        notice_text = response["action"]["arguments"]["text"]
        _, takeover, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        self.assertEqual((takeover["action"]["kind"], takeover["action"]["purpose"]), ("emit", "notice"))
        self.assertTrue(takeover["action"]["arguments"]["replayed"])
        self.assertEqual(takeover["action"]["arguments"]["text"], notice_text)

        heartbeat_store = str(Path(self._tmp.name) / "heartbeat-store")
        code, heartbeat_bound, err = run(
            "monitor", "bind", "--store", heartbeat_store, "--initialize-registry",
            "--heartbeat", self.HEARTBEAT,
        )
        self.assertEqual(code, 0, err)
        _, first, _ = run(
            "monitor", "enter", "--entry-ref", heartbeat_bound["entry_ref"], "--now", at,
        )
        old_continuation = first["continuation"]
        _, second, _ = run(
            "monitor", "enter", "--entry-ref", heartbeat_bound["entry_ref"], "--now", at,
        )
        self.assertEqual((first["action"]["kind"], second["action"]["kind"]), ("heartbeat_set", "heartbeat_set"))
        self.assertNotEqual(first["continuation"], second["continuation"])
        code, stopped, err = run(
            "monitor", "continue", "--continuation", old_continuation,
            "--result-json", json.dumps(
                {"applied": True, "next_run_at": first["action"]["arguments"]["target_at"]}
            ),
            "--now", at,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(stopped["late_result"], "recorded")

    def test_overlapping_entries_fence_the_older_return_without_a_second_send(self) -> None:
        self.register()
        cycle(self.store, T0, observations=[self.quota_observation(remaining=50)])
        bound = self.bind_monitor()
        at = "2026-09-17T12:05:00+00:00"
        _, response, _ = run(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", at,
        )
        response = self.monitor_continue(response, self.read("idle", at), at)
        response = self.monitor_continue(response, self.read("idle", at), at)
        self.assertEqual(response["action"]["kind"], "send")

        argv = [
            sys.executable,
            str(SCRIPT),
            "monitor",
            "enter",
            "--entry-ref",
            bound["entry_ref"],
            "--now",
            at,
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            completed = list(
                pool.map(
                    lambda _: subprocess.run(
                        argv, capture_output=True, text=True, check=False
                    ),
                    range(2),
                )
            )
        self.assertEqual([item.returncode for item in completed], [0, 0])
        entries = [json.loads(item.stdout) for item in completed]
        self.assertNotIn("send", [entry["action"]["kind"] for entry in entries])
        older, newer = sorted(entries, key=lambda item: item["generation"])
        self.assertLess(older["generation"], newer["generation"])
        code, stopped, err = run(
            "monitor", "continue", "--continuation", older["continuation"],
            "--result-json", json.dumps({"emitted": True}), "--now", at,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(stopped["status"], "stopped")
        self.assertNotIn("continuation", stopped)
        _, inspected, _ = run("inspect", "--store", self.store, "--now", at)
        self.assertEqual(inspected["registrations"][0]["status"], "reserved")


if __name__ == "__main__":
    unittest.main()
