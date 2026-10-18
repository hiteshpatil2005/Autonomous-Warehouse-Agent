"""
WareBot AI — Performance Benchmark Engine
Compares the WareBot Autonomous Utility AI Agent against the Nearest-Order-First Baseline.
Ensures rigorous experimental fairness under identical warehouse maps, inventory,
battery limits, pathfinding, and safety constraints.
"""

import asyncio
from datetime import datetime, timezone
import io
import csv
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.config import SimulationConfig, default_config
from app.models.order import Order, OrderStatus
from app.models.robot import Robot
from app.models.warehouse import WarehouseMap
from app.simulation.decision_engine import (
    AutonomousDecisionEngine,
    CandidateEvaluation,
    DecisionResult,
)
from app.simulation.engine import WarehouseEngine

logger = logging.getLogger("warebot.benchmark")


class NearestOrderDecisionEngine(AutonomousDecisionEngine):
    """
    Baseline decision policy: Selects the nearest feasible pending order.
    Enforces identical hard safety constraints (stock check, A* reachability,
    battery feasibility) as the utility engine to guarantee experimental fairness.
    """

    def select_best_order(
        self,
        robot: Robot,
        orders: List[Order],
        warehouse_map: WarehouseMap,
        current_tick: int,
    ) -> DecisionResult:
        pending_orders = [o for o in orders if o.status == OrderStatus.PENDING]
        evaluations: List[CandidateEvaluation] = []
        rejections: Dict[str, str] = {}

        for order in pending_orders:
            evaluation = self.evaluate_order(order, robot, warehouse_map, current_tick)
            evaluations.append(evaluation)
            if not evaluation.is_feasible:
                rejections[order.order_id] = evaluation.rejection_reason or "Safety constraint violation"

        feasible_evals = [e for e in evaluations if e.is_feasible]

        if not feasible_evals:
            return DecisionResult(
                selected_order_id=None,
                selected_order=None,
                winning_score=0.0,
                explanation="Baseline (Nearest-Order): No feasible orders available.",
                candidates_count=len(pending_orders),
                feasible_count=0,
                rejected_count=len(rejections),
                evaluations=evaluations,
                rejections=rejections,
                battery_feasible=not (robot.battery < self.config.critical_battery_threshold),
            )

        # Baseline greedy rule: Sort ascending by distance to shelf
        feasible_evals.sort(key=lambda x: (x.est_distance, x.order_id))
        winner = feasible_evals[0]
        selected_order = next((o for o in pending_orders if o.order_id == winner.order_id), None)

        explanation = (
            f"Baseline Selection: {winner.order_id} ({winner.product_name}) chosen as nearest order "
            f"({winner.est_distance} steps). Priority and deadline urgency ignored."
        )

        return DecisionResult(
            selected_order_id=winner.order_id,
            selected_order=selected_order,
            winning_score=float(winner.est_distance),
            explanation=explanation,
            candidates_count=len(pending_orders),
            feasible_count=len(feasible_evals),
            rejected_count=len(rejections),
            evaluations=evaluations,
            rejections=rejections,
            est_route_distance=winner.est_distance,
            est_energy_cost=winner.est_energy_cost,
            battery_feasible=True,
        )


class BenchmarkRunResult(BaseModel):
    """Metrics from a single simulation run under a specific seed and policy."""
    seed: int
    strategy: str
    total_orders: int
    completed_orders: int
    completion_rate_pct: float
    average_completion_time_ticks: float
    total_ticks: int
    distance_travelled: int
    energy_consumed: float
    energy_per_completed_order: float
    deadline_success_rate_pct: float
    route_replanning_count: int
    blocked_movement_attempts: int
    infeasible_rejections: int


class BenchmarkStrategySummary(BaseModel):
    """Aggregated multi-run benchmark results for one strategy."""
    strategy_name: str
    runs_count: int
    avg_completed_orders: float
    avg_completion_rate_pct: float
    avg_completion_time_ticks: float
    avg_distance_travelled: float
    avg_energy_consumed: float
    avg_energy_per_order: float
    avg_deadline_success_rate_pct: float
    total_replans: int
    total_blocked_attempts: int
    total_infeasible_rejections: int


class BenchmarkJob(BaseModel):
    """Job container representing a full comparative benchmark execution."""
    job_id: str
    status: str = "queued"  # "queued" | "running" | "completed" | "failed"
    progress_pct: float = 0.0
    created_at: str
    completed_at: Optional[str] = None
    runs_requested: int = 10
    max_ticks_per_run: int = 120
    seeds_used: List[int] = Field(default_factory=list)
    utility_summary: Optional[BenchmarkStrategySummary] = None
    baseline_summary: Optional[BenchmarkStrategySummary] = None
    detailed_runs: List[BenchmarkRunResult] = Field(default_factory=list)
    comparison_verdict: Optional[str] = None
    error_message: Optional[str] = None


def run_single_simulation(
    seed: int,
    strategy: str,
    max_ticks: int = 120,
    config: Optional[SimulationConfig] = None,
) -> BenchmarkRunResult:
    """
    Execute one complete deterministic simulation run for a given strategy and seed.
    Controlled event-free environment ensures identical baseline conditions.
    """
    cfg = config or default_config
    # Temporarily set event probabilities to 0 during baseline run to guarantee identical scenario conditions
    clean_cfg = cfg.model_copy(
        update={
            "order_arrival_prob": 0.0,
            "urgent_order_prob": 0.0,
            "obstacle_prob": 0.0,
            "replenish_prob": 0.0,
        }
    )

    engine = WarehouseEngine(seed=seed, config=clean_cfg)

    # Configure decision strategy
    if strategy == "nearest":
        engine.decision_engine = NearestOrderDecisionEngine(clean_cfg)
    else:
        engine.decision_engine = AutonomousDecisionEngine(clean_cfg)

    # Step engine until completion or max_ticks reached
    infeasible_rejections = 0
    for _ in range(max_ticks):
        engine.step()
        if engine.last_decision:
            infeasible_rejections += engine.last_decision.rejected_count

        # Early exit if all initial orders completed
        pending = [o for o in engine.orders if o.status != OrderStatus.COMPLETED]
        if not pending and engine.robot.state.value == "IDLE":
            break

    # Compute metrics safely
    completed_orders = [o for o in engine.orders if o.status == OrderStatus.COMPLETED and o.completion_time_ticks]
    completed_count = len(completed_orders)
    total_orders = len(engine.orders)
    completion_rate = round((completed_count / total_orders) * 100.0, 1) if total_orders > 0 else 0.0

    avg_completion_time = (
        round(sum(o.completion_time_ticks for o in completed_orders) / completed_count, 1)
        if completed_count > 0
        else 0.0
    )

    total_dist = engine.metrics["distance_travelled"]
    total_energy = round(sum(o.energy_consumed for o in engine.orders), 1)
    energy_per_order = round(total_energy / completed_count, 1) if completed_count > 0 else 0.0

    on_time_count = sum(
        1
        for o in completed_orders
        if o.deadline_tick is None or (o.completed_tick and o.completed_tick <= o.deadline_tick)
    )
    deadline_rate = round((on_time_count / completed_count) * 100.0, 1) if completed_count > 0 else 100.0

    return BenchmarkRunResult(
        seed=seed,
        strategy="WareBot Utility AI" if strategy == "utility" else "Nearest-Order Baseline",
        total_orders=total_orders,
        completed_orders=completed_count,
        completion_rate_pct=completion_rate,
        average_completion_time_ticks=avg_completion_time,
        total_ticks=engine.tick,
        distance_travelled=total_dist,
        energy_consumed=total_energy,
        energy_per_completed_order=energy_per_order,
        deadline_success_rate_pct=deadline_rate,
        route_replanning_count=engine.metrics["route_replanning_count"],
        blocked_movement_attempts=engine.metrics["blocked_movement_attempts"],
        infeasible_rejections=infeasible_rejections,
    )


def aggregate_strategy_results(strategy_name: str, runs: List[BenchmarkRunResult]) -> BenchmarkStrategySummary:
    """Compute aggregate statistical averages across runs."""
    count = len(runs)
    if count == 0:
        return BenchmarkStrategySummary(
            strategy_name=strategy_name,
            runs_count=0,
            avg_completed_orders=0.0,
            avg_completion_rate_pct=0.0,
            avg_completion_time_ticks=0.0,
            avg_distance_travelled=0.0,
            avg_energy_consumed=0.0,
            avg_energy_per_order=0.0,
            avg_deadline_success_rate_pct=0.0,
            total_replans=0,
            total_blocked_attempts=0,
            total_infeasible_rejections=0,
        )

    return BenchmarkStrategySummary(
        strategy_name=strategy_name,
        runs_count=count,
        avg_completed_orders=round(sum(r.completed_orders for r in runs) / count, 2),
        avg_completion_rate_pct=round(sum(r.completion_rate_pct for r in runs) / count, 1),
        avg_completion_time_ticks=round(sum(r.average_completion_time_ticks for r in runs) / count, 1),
        avg_distance_travelled=round(sum(r.distance_travelled for r in runs) / count, 1),
        avg_energy_consumed=round(sum(r.energy_consumed for r in runs) / count, 1),
        avg_energy_per_order=round(sum(r.energy_per_completed_order for r in runs) / count, 1),
        avg_deadline_success_rate_pct=round(sum(r.deadline_success_rate_pct for r in runs) / count, 1),
        total_replans=sum(r.route_replanning_count for r in runs),
        total_blocked_attempts=sum(r.blocked_movement_attempts for r in runs),
        total_infeasible_rejections=sum(r.infeasible_rejections for r in runs),
    )


def execute_benchmark_job_sync(job: BenchmarkJob) -> BenchmarkJob:
    """Synchronous worker executing the full benchmark suite across requested seeds."""
    logger.info(f"Starting benchmark job {job.job_id} ({len(job.seeds_used)} seeds)...")
    job.status = "running"

    total_runs = len(job.seeds_used) * 2
    completed_runs = 0

    utility_results: List[BenchmarkRunResult] = []
    baseline_results: List[BenchmarkRunResult] = []

    for seed in job.seeds_used:
        # 1. Run WareBot Autonomous Utility AI
        res_utility = run_single_simulation(seed=seed, strategy="utility", max_ticks=job.max_ticks_per_run)
        utility_results.append(res_utility)
        job.detailed_runs.append(res_utility)
        completed_runs += 1
        job.progress_pct = round((completed_runs / total_runs) * 100.0, 1)

        # 2. Run Nearest-Order Baseline
        res_baseline = run_single_simulation(seed=seed, strategy="nearest", max_ticks=job.max_ticks_per_run)
        baseline_results.append(res_baseline)
        job.detailed_runs.append(res_baseline)
        completed_runs += 1
        job.progress_pct = round((completed_runs / total_runs) * 100.0, 1)

    job.utility_summary = aggregate_strategy_results("WareBot Utility AI", utility_results)
    job.baseline_summary = aggregate_strategy_results("Nearest-Order Baseline", baseline_results)

    # Calculate comparative verdict
    u_rate = job.utility_summary.avg_deadline_success_rate_pct
    b_rate = job.baseline_summary.avg_deadline_success_rate_pct
    u_time = job.utility_summary.avg_completion_time_ticks
    b_time = job.baseline_summary.avg_completion_time_ticks

    verdict_parts = []
    if u_rate >= b_rate:
        verdict_parts.append(f"WareBot Utility AI achieved superior deadline compliance ({u_rate}% vs {b_rate}%).")
    else:
        verdict_parts.append(f"Baseline achieved higher deadline compliance ({b_rate}% vs {u_rate}%).")

    if u_time <= b_time:
        verdict_parts.append(f"Utility AI completed orders faster on average ({u_time} ticks vs {b_time} ticks).")
    else:
        verdict_parts.append(f"Baseline completed orders in {b_time} ticks vs {u_time} ticks for Utility AI.")

    job.comparison_verdict = " ".join(verdict_parts)
    job.status = "completed"
    job.progress_pct = 100.0
    job.completed_at = datetime.now(timezone.utc).isoformat()
    logger.info(f"Benchmark job {job.job_id} finished successfully.")
    return job


def generate_benchmark_csv(job: BenchmarkJob) -> str:
    """Generate RFC 4180 compliant CSV string from benchmark results."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Seed",
        "Strategy",
        "Total_Orders",
        "Completed_Orders",
        "Completion_Rate_Pct",
        "Avg_Completion_Time_Ticks",
        "Total_Ticks",
        "Distance_Travelled",
        "Energy_Consumed",
        "Energy_Per_Order",
        "Deadline_Success_Rate_Pct",
        "Route_Replans",
        "Blocked_Attempts",
    ])

    for r in job.detailed_runs:
        writer.writerow([
            r.seed,
            r.strategy,
            r.total_orders,
            r.completed_orders,
            r.completion_rate_pct,
            r.average_completion_time_ticks,
            r.total_ticks,
            r.distance_travelled,
            r.energy_consumed,
            r.energy_per_completed_order,
            r.deadline_success_rate_pct,
            r.route_replanning_count,
            r.blocked_movement_attempts,
        ])

    return output.getvalue()
