"""
WareBot AI — Simulation State Serialization Service
Transforms engine state models into JSON-safe dictionaries for headless inspection,
tests, and Part 3 WebSocket / REST APIs.
"""

from typing import Any, Dict
from app.simulation.engine import WarehouseEngine


def serialize_simulation_state(engine: WarehouseEngine) -> Dict[str, Any]:
    """
    Produce a complete, JSON-serializable snapshot of the simulation engine.
    Avoids returning non-serializable internal classes.
    """
    robot = engine.robot
    w_map = engine.warehouse_map

    # Format shelves
    shelves_data = [
        {
            "shelf_id": s.shelf_id,
            "row": s.row,
            "col": s.col,
            "product_id": s.product_id,
            "product_name": s.product_name,
            "stock": s.stock,
            "max_capacity": s.max_capacity,
        }
        for s in w_map.shelves
    ]

    # Format obstacles
    obstacles_data = []
    for key, expiry in w_map.obstacles.items():
        r, c = map(int, key.split(","))
        obstacles_data.append({"row": r, "col": c, "expiry_tick": expiry})

    # Format orders
    orders_data = [
        {
            "order_id": o.order_id,
            "product_id": o.product_id,
            "product_name": o.product_name,
            "quantity": o.quantity,
            "priority": o.priority.value,
            "shelf_id": o.shelf_id,
            "shelf_pos": list(o.shelf_pos),
            "created_tick": o.created_tick,
            "deadline_tick": o.deadline_tick,
            "status": o.status.value,
            "assigned_robot_id": o.assigned_robot_id,
            "assigned_tick": o.assigned_tick,
            "completed_tick": o.completed_tick,
            "completion_time_ticks": o.completion_time_ticks,
            "energy_consumed": round(o.energy_consumed, 1),
            "is_overdue": o.is_overdue(engine.tick),
        }
        for o in engine.orders
    ]

    # Format decision inspector
    decision_data = None
    if engine.last_decision:
        decision_data = {
            "selected_order_id": engine.last_decision.selected_order_id,
            "winning_score": engine.last_decision.winning_score,
            "explanation": engine.last_decision.explanation,
            "candidates_count": engine.last_decision.candidates_count,
            "feasible_count": engine.last_decision.feasible_count,
            "rejected_count": engine.last_decision.rejected_count,
            "rejections": engine.last_decision.rejections,
            "est_route_distance": engine.last_decision.est_route_distance,
            "est_energy_cost": round(engine.last_decision.est_energy_cost, 1),
            "battery_feasible": engine.last_decision.battery_feasible,
            "evaluations": [
                {
                    "order_id": e.order_id,
                    "product_name": e.product_name,
                    "priority": e.priority.value,
                    "shelf_id": e.shelf_id,
                    "is_feasible": e.is_feasible,
                    "rejection_reason": e.rejection_reason,
                    "urgency_score": e.urgency_score,
                    "deadline_score": e.deadline_score,
                    "proximity_shelf_score": e.proximity_shelf_score,
                    "proximity_packing_score": e.proximity_packing_score,
                    "inventory_score": e.inventory_score,
                    "route_risk_penalty": e.route_risk_penalty,
                    "total_utility": e.total_utility,
                    "est_distance": e.est_distance,
                    "est_energy_cost": round(e.est_energy_cost, 1),
                }
                for e in engine.last_decision.evaluations
            ],
        }

    # Format events (recent 50)
    events_data = [
        {
            "id": ev.id,
            "tick": ev.tick,
            "event_type": ev.event_type.value,
            "severity": ev.severity.value,
            "message": ev.message,
            "data": ev.data,
        }
        for ev in engine.event_history[-50:]
    ]

    return {
        "tick": engine.tick,
        "elapsed_time_seconds": engine.elapsed_time_seconds,
        "grid": {
            "rows": w_map.rows,
            "cols": w_map.cols,
            "shelves": shelves_data,
            "robot_start": list(w_map.robot_start),
            "packing_station": list(w_map.packing_station),
            "charging_station": list(w_map.charging_station),
            "obstacles": obstacles_data,
        },
        "robot": {
            "robot_id": robot.robot_id,
            "row": robot.row,
            "col": robot.col,
            "pos": [robot.row, robot.col],
            "state": robot.state.value,
            "battery": round(robot.battery, 1),
            "current_order_id": robot.current_order_id,
            "target_pos": list(robot.target_pos) if robot.target_pos else None,
            "target_type": robot.target_type,
            "planned_route": [list(p) for p in robot.planned_route],
            "traversed_path": [list(p) for p in robot.traversed_path[-30:]],
            "total_distance_travelled": robot.total_distance_travelled,
            "completed_movement_count": robot.completed_movement_count,
            "current_action": robot.current_action,
        },
        "orders": orders_data,
        "metrics": engine.get_metrics_snapshot(),
        "decision_inspector": decision_data,
        "events": events_data,
    }
