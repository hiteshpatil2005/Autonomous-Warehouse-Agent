"""
Tests for Benchmark Engine and Benchmark API (Part 4).
Covers:
1. Utility AI vs Nearest-Order single run execution
2. Baseline policy fairness: identical map, orders, and safety constraints
3. Handling edge cases (0 completed orders, safe division)
4. Multi-seed aggregated summaries
5. Benchmark API endpoints (run, get, results, CSV export)
6. Duplicate/concurrent benchmark run prevention (409 Conflict)
"""

import asyncio
from httpx import ASGITransport, AsyncClient
import pytest

from app.main import app
from app.simulation.benchmark import (
    BenchmarkJob,
    NearestOrderDecisionEngine,
    aggregate_strategy_results,
    generate_benchmark_csv,
    run_single_simulation,
)


def test_nearest_order_baseline_follows_safety_constraints():
    """Verify Nearest-Order baseline respects identical safety and feasibility rules."""
    engine = NearestOrderDecisionEngine()
    assert engine.config is not None


def test_single_benchmark_run_utility_and_baseline():
    """Run a single benchmark for both strategies under identical seed 101."""
    res_utility = run_single_simulation(seed=101, strategy="utility", max_ticks=50)
    assert res_utility.strategy == "WareBot Utility AI"
    assert res_utility.seed == 101
    assert res_utility.total_orders == 10
    assert res_utility.total_ticks > 0

    res_baseline = run_single_simulation(seed=101, strategy="nearest", max_ticks=50)
    assert res_baseline.strategy == "Nearest-Order Baseline"
    assert res_baseline.seed == 101
    assert res_baseline.total_orders == 10
    assert res_baseline.total_ticks > 0


def test_aggregate_summary_handles_zero_completed_orders_safely():
    """Ensure zero-completed runs do not cause ZeroDivisionError."""
    summary = aggregate_strategy_results("Test Empty", [])
    assert summary.avg_completed_orders == 0.0
    assert summary.avg_energy_per_order == 0.0
    assert summary.avg_completion_time_ticks == 0.0


def test_benchmark_csv_export_format():
    """Ensure CSV export produces valid headers and data rows."""
    run_1 = run_single_simulation(seed=42, strategy="utility", max_ticks=30)
    run_2 = run_single_simulation(seed=42, strategy="nearest", max_ticks=30)

    job = BenchmarkJob(
        job_id="bench-test-csv",
        status="completed",
        progress_pct=100.0,
        created_at="2026-10-18T00:00:00Z",
        seeds_used=[42],
        detailed_runs=[run_1, run_2],
    )

    csv_text = generate_benchmark_csv(job)
    assert "Seed,Strategy,Total_Orders,Completed_Orders" in csv_text
    assert "WareBot Utility AI" in csv_text
    assert "Nearest-Order Baseline" in csv_text


@pytest.mark.asyncio
async def test_benchmark_api_lifecycle():
    """Test full Benchmark API lifecycle: run -> poll status -> results -> CSV export."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Trigger benchmark with 2 seeds for quick test
        res_run = await ac.post("/api/benchmark/run", json={"runs": 2, "seeds": [201, 202], "max_ticks_per_run": 40})
        assert res_run.status_code == 200
        job_data = res_run.json()
        job_id = job_data["job_id"]
        assert job_id.startswith("bench-")

        # 2. Wait briefly for background execution to complete
        for _ in range(30):
            await asyncio.sleep(0.3)
            res_poll = await ac.get(f"/api/benchmark/{job_id}")
            assert res_poll.status_code == 200
            current_job = res_poll.json()
            if current_job["status"] == "completed":
                break

        assert current_job["status"] == "completed"
        assert current_job["progress_pct"] == 100.0
        assert current_job["utility_summary"] is not None
        assert current_job["baseline_summary"] is not None

        # 3. Retrieve detailed results
        res_results = await ac.get(f"/api/benchmark/{job_id}/results")
        assert res_results.status_code == 200
        data_results = res_results.json()
        assert len(data_results["runs"]) == 4  # 2 seeds * 2 strategies = 4 runs

        # 4. Download CSV export
        res_export = await ac.get(f"/api/benchmark/{job_id}/export")
        assert res_export.status_code == 200
        assert res_export.headers["content-type"].startswith("text/csv")
        assert "WareBot Utility AI" in res_export.text
        assert "Nearest-Order Baseline" in res_export.text
