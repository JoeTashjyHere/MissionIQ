"""Pursuit Automation Orchestrator contracts.

The orchestration core (run_steps) is pure over injected executors, so retry,
critical-abort, partial-failure, resume, and epistemic-honesty semantics are
verified here without a database.
"""
from __future__ import annotations

import pytest

from app.services.automation_service import (
    AutomationStepDef,
    build_step_plan,
    initial_step_results,
    run_steps,
)


def _executors(behaviors: dict[str, list[Exception | dict | None]]):
    """Build executors that pop scripted outcomes per call: an Exception is
    raised, anything else is returned."""

    def make(step_id: str):
        async def _exec():
            outcomes = behaviors.get(step_id)
            outcome = outcomes.pop(0) if outcomes else {"detail": "ok"}
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        return _exec

    return {step_id: make(step_id) for step_id in behaviors} | {
        s.step_id: make(s.step_id) for s in build_step_plan()
    }


# ── Step plan shape ─────────────────────────────────────────────────────────


def test_step_plan_covers_milestone_responsibilities_in_order():
    ids = [s.step_id for s in build_step_plan()]
    assert ids == [
        "pursuit_ready",
        "documents_ready",
        "market_intel",
        "customer_dna",
        "company_dna",
        "capability_match",
        "win_strategy",
        "executive_brief",
    ]


def test_dna_dependency_chain_preserved():
    """Customer DNA must run before every downstream intelligence module, and
    it is critical: nothing downstream may run on a missing DNA profile."""
    plan = build_step_plan()
    ids = [s.step_id for s in plan]
    dna = ids.index("customer_dna")
    for downstream in ("company_dna", "capability_match", "win_strategy", "executive_brief"):
        assert ids.index(downstream) > dna
    by_id = {s.step_id: s for s in plan}
    assert by_id["pursuit_ready"].critical
    assert by_id["customer_dna"].critical
    assert not by_id["market_intel"].critical


def test_initial_step_results_are_pending():
    results = initial_step_results()
    assert all(r["status"] == "pending" and r["attempts"] == 0 for r in results)
    assert len(results) == len(build_step_plan())


# ── Execution semantics ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_all_steps_succeed():
    results = initial_step_results()
    final = await run_steps(build_step_plan(), _executors({}), results)
    assert final == "succeeded"
    assert all(r["status"] == "succeeded" for r in results)
    assert all(r["attempts"] == 1 for r in results)


@pytest.mark.asyncio
async def test_transient_failure_is_retried_then_succeeds():
    results = initial_step_results()
    final = await run_steps(
        build_step_plan(),
        _executors({"win_strategy": [RuntimeError("transient"), {"detail": "ok"}]}),
        results,
    )
    assert final == "succeeded"
    win = next(r for r in results if r["step_id"] == "win_strategy")
    assert win["status"] == "succeeded"
    assert win["attempts"] == 2


@pytest.mark.asyncio
async def test_noncritical_failure_yields_partial_and_continues():
    results = initial_step_results()
    final = await run_steps(
        build_step_plan(),
        _executors({"market_intel": [RuntimeError("api down"), RuntimeError("api down")]}),
        results,
    )
    assert final == "partial"
    mi = next(r for r in results if r["step_id"] == "market_intel")
    assert mi["status"] == "failed"
    assert mi["attempts"] == 2
    assert "api down" in mi["error"]
    # Downstream modules still ran.
    brief = next(r for r in results if r["step_id"] == "executive_brief")
    assert brief["status"] == "succeeded"


@pytest.mark.asyncio
async def test_critical_customer_dna_failure_aborts_downstream():
    results = initial_step_results()
    boom = [RuntimeError("dna failed"), RuntimeError("dna failed")]
    final = await run_steps(
        build_step_plan(), _executors({"customer_dna": boom}), results
    )
    assert final == "failed"
    by_id = {r["step_id"]: r for r in results}
    assert by_id["customer_dna"]["status"] == "failed"
    for downstream in ("company_dna", "capability_match", "win_strategy", "executive_brief"):
        assert by_id[downstream]["status"] == "skipped"
    # Upstream steps were unaffected.
    assert by_id["pursuit_ready"]["status"] == "succeeded"


@pytest.mark.asyncio
async def test_resume_skips_succeeded_steps():
    """Retry semantics: a second pass over the same results only re-executes
    non-succeeded steps."""
    results = initial_step_results()
    await run_steps(
        build_step_plan(),
        _executors({"capability_match": [RuntimeError("x"), RuntimeError("x")]}),
        results,
    )
    # Simulate retry_run's reset of failed steps.
    for r in results:
        if r["status"] in ("failed", "skipped"):
            r["status"] = "pending"
            r["error"] = None

    calls: list[str] = []

    def tracking(step_id: str):
        async def _exec():
            calls.append(step_id)
            return {"detail": "ok"}

        return _exec

    executors = {s.step_id: tracking(s.step_id) for s in build_step_plan()}
    final = await run_steps(build_step_plan(), executors, results)
    assert final == "succeeded"
    assert calls == ["capability_match"]  # only the failed step re-ran


@pytest.mark.asyncio
async def test_insufficient_context_is_honest_success_not_failure():
    """A module that honestly reports insufficient_context completes the step:
    automation never fabricates inputs to force an output."""
    results = initial_step_results()
    final = await run_steps(
        build_step_plan(),
        _executors(
            {
                "customer_dna": [
                    {"ai_output_id": "abc", "detail": "capture.customer_dna → insufficient_context"}
                ]
            }
        ),
        results,
    )
    assert final == "succeeded"
    dna = next(r for r in results if r["step_id"] == "customer_dna")
    assert dna["status"] == "succeeded"
    assert "insufficient_context" in dna["detail"]


@pytest.mark.asyncio
async def test_on_update_hook_reports_progress():
    seen: list[str | None] = []

    async def hook(current: str | None) -> None:
        seen.append(current)

    results = initial_step_results()
    await run_steps(build_step_plan(), _executors({}), results, on_update=hook)
    # Two notifications per executed step (start + finish).
    assert len(seen) == 2 * len(build_step_plan())
    assert seen[0] == "pursuit_ready"


@pytest.mark.asyncio
async def test_workflow_expansion_is_a_list_entry():
    """Future workflow expansion: appending a step definition + executor is
    all that's required."""
    plan = build_step_plan() + [
        AutomationStepDef("gate_review", "Gate Review generated")
    ]
    results = initial_step_results(plan)
    final = await run_steps(plan, _executors({"gate_review": []}), results)
    assert final == "succeeded"
    assert results[-1]["step_id"] == "gate_review"
    assert results[-1]["status"] == "succeeded"
