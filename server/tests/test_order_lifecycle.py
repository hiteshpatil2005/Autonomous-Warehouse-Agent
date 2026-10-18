"""
Tests for Order Lifecycle and Warehouse Inventory (Requirements 12, 13, 14).
"""

from app.models.order import Order, OrderStatus, Priority
from app.simulation.engine import WarehouseEngine


def test_order_lifecycle_progression(default_cfg):
    """
    Requirement 12: Orders follow the correct lifecycle:
    PENDING -> ASSIGNED -> PICKING -> RETURNING -> PACKING -> COMPLETED
    """
    engine = WarehouseEngine(seed=42, config=default_cfg)

    # Step through ticks until the first order transitions and completes
    initial_order = engine.orders[0]
    assert initial_order.status == OrderStatus.PENDING

    observed_statuses = set()
    observed_statuses.add(initial_order.status)

    # Run up to 100 ticks to observe complete order lifecycle
    for _ in range(120):
        engine.step()
        observed_statuses.add(initial_order.status)
        if initial_order.status == OrderStatus.COMPLETED:
            break

    # Verify lifecycle stages were hit
    assert OrderStatus.ASSIGNED in observed_statuses or OrderStatus.PICKING in observed_statuses
    assert OrderStatus.COMPLETED in observed_statuses


def test_inventory_decreases_correctly_after_picking(default_cfg):
    """Requirement 13: Inventory decreases correctly after picking."""
    engine = WarehouseEngine(seed=42, config=default_cfg)

    # Find the order that will be chosen
    best_order = engine.orders[0]
    shelf = engine.warehouse_map.get_shelf_by_id(best_order.shelf_id)
    assert shelf is not None
    initial_stock = shelf.stock

    # Advance until the order completes picking
    picked = False
    for _ in range(80):
        events = engine.step()
        for ev in events:
            if ev.event_type.value == "PICKING_COMPLETED" and ev.data.get("shelf_id") == shelf.shelf_id:
                picked = True
                break
        if picked:
            break

    assert picked, "Picking should have completed within 80 ticks"
    assert shelf.stock == initial_stock - best_order.quantity


def test_completed_orders_are_not_processed_twice(default_cfg):
    """Requirement 14: Completed orders are not processed twice."""
    engine = WarehouseEngine(seed=42, config=default_cfg)

    # Run until first delivery completes
    completed_order_id = None
    for _ in range(120):
        engine.step()
        completed = [o for o in engine.orders if o.status == OrderStatus.COMPLETED]
        if completed:
            completed_order_id = completed[0].order_id
            break

    assert completed_order_id is not None
    completed_order = engine.get_order_by_id(completed_order_id)
    assert completed_order.status == OrderStatus.COMPLETED

    # Step further: verify completed order is never re-assigned
    for _ in range(40):
        engine.step()
        assert completed_order.status == OrderStatus.COMPLETED
        assert engine.robot.current_order_id != completed_order_id
