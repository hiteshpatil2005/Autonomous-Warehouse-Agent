"""
Tests for Autonomous AI Decision Engine (Requirements 10, 11).
"""

from app.core.config import SimulationConfig
from app.models.order import Order, OrderStatus, Priority
from app.models.robot import Robot
from app.simulation.decision_engine import AutonomousDecisionEngine


def test_infeasible_orders_are_rejected(seeded_map, default_cfg):
    """Requirement 10: Infeasible orders are rejected (stock, reachability, battery)."""
    engine = AutonomousDecisionEngine(default_cfg)
    robot = Robot(row=28, col=1, battery=100.0)

    # 1. Reject if out of stock
    shelf_1 = seeded_map.shelves[0]
    shelf_1.stock = 0

    order_out_of_stock = Order(
        order_id="ORD-TEST-01",
        product_id=shelf_1.product_id,
        product_name=shelf_1.product_name,
        quantity=1,
        priority=Priority.HIGH,
        shelf_id=shelf_1.shelf_id,
        shelf_pos=shelf_1.pos,
        created_tick=0,
        status=OrderStatus.PENDING,
    )

    eval_out_of_stock = engine.evaluate_order(order_out_of_stock, robot, seeded_map, current_tick=1)
    assert not eval_out_of_stock.is_feasible
    assert "Insufficient stock" in (eval_out_of_stock.rejection_reason or "")

    # Restore stock
    shelf_1.stock = 10

    # 2. Reject if robot has insufficient battery
    low_bat_robot = Robot(row=28, col=1, battery=8.0)  # Min reserve is 15.0!
    order_normal = Order(
        order_id="ORD-TEST-02",
        product_id=shelf_1.product_id,
        product_name=shelf_1.product_name,
        quantity=1,
        priority=Priority.HIGH,
        shelf_id=shelf_1.shelf_id,
        shelf_pos=shelf_1.pos,
        created_tick=0,
        status=OrderStatus.PENDING,
    )
    eval_low_bat = engine.evaluate_order(order_normal, low_bat_robot, seeded_map, current_tick=1)
    assert not eval_low_bat.is_feasible
    assert "Insufficient battery" in (eval_low_bat.rejection_reason or "")

    # 3. Reject if destination shelf is completely blocked
    # Surround shelf_1 with impassable obstacles
    r, c = shelf_1.pos
    for adj in [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]:
        seeded_map.obstacles[f"{adj[0]},{adj[1]}"] = 999

    eval_blocked = engine.evaluate_order(order_normal, robot, seeded_map, current_tick=1)
    assert not eval_blocked.is_feasible
    assert "No passable route" in (eval_blocked.rejection_reason or "")

    # Clean up
    for adj in [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]:
        del seeded_map.obstacles[f"{adj[0]},{adj[1]}"]


def test_decision_engine_selects_highest_scoring_feasible_task(seeded_map, default_cfg):
    """Requirement 11: Decision engine selects highest-scoring feasible task."""
    decision_ai = AutonomousDecisionEngine(default_cfg)
    robot = Robot(row=28, col=1, battery=100.0)

    shelf_a = seeded_map.shelves[1]
    shelf_b = seeded_map.shelves[2]

    # Order A: Low priority, no deadline
    order_a = Order(
        order_id="ORD-LOW-01",
        product_id=shelf_a.product_id,
        product_name=shelf_a.product_name,
        quantity=1,
        priority=Priority.LOW,
        shelf_id=shelf_a.shelf_id,
        shelf_pos=shelf_a.pos,
        created_tick=0,
        deadline_tick=None,
        status=OrderStatus.PENDING,
    )

    # Order B: Urgent priority, tight deadline
    order_b = Order(
        order_id="ORD-URGENT-01",
        product_id=shelf_b.product_id,
        product_name=shelf_b.product_name,
        quantity=1,
        priority=Priority.URGENT,
        shelf_id=shelf_b.shelf_id,
        shelf_pos=shelf_b.pos,
        created_tick=0,
        deadline_tick=25,
        status=OrderStatus.PENDING,
    )

    result = decision_ai.select_best_order(
        robot=robot,
        orders=[order_a, order_b],
        warehouse_map=seeded_map,
        current_tick=1,
    )

    assert result.selected_order_id == "ORD-URGENT-01"
    assert result.winning_score > 0
    assert result.feasible_count == 2
    assert "Selected ORD-URGENT-01" in result.explanation
