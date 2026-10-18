"""
WareBot AI — Benchmark API Router
Provides endpoints to trigger, monitor, and export comparative benchmarks
between WareBot Autonomous Utility AI and Nearest-Order Baseline.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional
import uuid
from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.simulation.benchmark import (
    BenchmarkJob,
    execute_benchmark_job_sync,
    generate_benchmark_csv,
)

logger = logging.getLogger("warebot.api.benchmark")

router = APIRouter(prefix="/api/benchmark", tags=["Benchmarking"])

# In-memory storage of benchmark jobs
_jobs: Dict[str, BenchmarkJob] = {}
_latest_job_id: Optional[str] = None
_benchmark_lock = asyncio.Lock()


class RunBenchmarkRequest(BaseModel):
    """Parameters to launch a comparative benchmark job."""
    runs: int = Field(default=10, ge=1, le=50, description="Number of independent seed runs")
    seeds: Optional[List[int]] = Field(default=None, description="Custom list of fixed seeds")
    max_ticks_per_run: int = Field(default=120, ge=30, le=500, description="Simulation ticks per run")


@router.post("/run", response_model=BenchmarkJob, summary="Start comparative benchmark")
async def start_benchmark(req: RunBenchmarkRequest = RunBenchmarkRequest()):
    """
    Launch a fair comparative benchmark evaluating WareBot Utility AI
    vs. Nearest-Order Baseline under identical conditions.
    Runs asynchronously in background worker to prevent blocking live simulation.
    """
    global _latest_job_id

    async with _benchmark_lock:
        # Check if an active benchmark is already executing
        if _latest_job_id and _latest_job_id in _jobs:
            current = _jobs[_latest_job_id]
            if current.status == "running":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Benchmark {current.job_id} is already in progress ({current.progress_pct}%). Please wait for completion.",
                )

        job_id = f"bench-{uuid.uuid4().hex[:8]}"

        # Derive reproducible seeds
        if req.seeds and len(req.seeds) > 0:
            seeds = req.seeds[:req.runs]
        else:
            seeds = [100 + (i * 101) for i in range(req.runs)]

        job = BenchmarkJob(
            job_id=job_id,
            status="queued",
            progress_pct=0.0,
            created_at=datetime.now(timezone.utc).isoformat(),
            runs_requested=len(seeds),
            max_ticks_per_run=req.max_ticks_per_run,
            seeds_used=seeds,
        )

        _jobs[job_id] = job
        _latest_job_id = job_id

    # Spawn non-blocking background worker
    asyncio.create_task(_run_benchmark_worker(job))
    return job


async def _run_benchmark_worker(job: BenchmarkJob):
    """Background worker executing benchmark without blocking main loop."""
    try:
        # Run CPU-bound benchmark in separate thread pool
        completed_job = await asyncio.to_thread(execute_benchmark_job_sync, job)
        _jobs[job.job_id] = completed_job
    except Exception as exc:
        logger.error(f"Benchmark job {job.job_id} failed: {exc}", exc_info=True)
        job.status = "failed"
        job.error_message = str(exc)
        _jobs[job.job_id] = job


@router.get("/active", response_model=Optional[BenchmarkJob], summary="Get latest or active benchmark")
async def get_active_benchmark():
    """Retrieve the most recent benchmark job and its current status."""
    if not _latest_job_id or _latest_job_id not in _jobs:
        return None
    return _jobs[_latest_job_id]


@router.get("/{benchmark_id}", response_model=BenchmarkJob, summary="Get benchmark status & summary")
async def get_benchmark(benchmark_id: str):
    """Retrieve benchmark status, progress, and strategy summaries."""
    if benchmark_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"Benchmark job '{benchmark_id}' not found.")
    return _jobs[benchmark_id]


@router.get("/{benchmark_id}/results", summary="Get detailed per-seed benchmark runs")
async def get_benchmark_results(benchmark_id: str):
    """Retrieve detailed individual run metrics for statistical auditing."""
    if benchmark_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"Benchmark job '{benchmark_id}' not found.")
    job = _jobs[benchmark_id]
    return {
        "job_id": job.job_id,
        "status": job.status,
        "runs": job.detailed_runs,
        "utility_summary": job.utility_summary,
        "baseline_summary": job.baseline_summary,
        "verdict": job.comparison_verdict,
    }


@router.get("/{benchmark_id}/export", summary="Export benchmark results as CSV")
async def export_benchmark_csv(benchmark_id: str):
    """Download RFC 4180 CSV spreadsheet containing full benchmark data."""
    if benchmark_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"Benchmark job '{benchmark_id}' not found.")
    job = _jobs[benchmark_id]
    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot export benchmark '{benchmark_id}': Job status is '{job.status}'.",
        )

    csv_data = generate_benchmark_csv(job)
    filename = f"warebot_benchmark_{job.job_id}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
