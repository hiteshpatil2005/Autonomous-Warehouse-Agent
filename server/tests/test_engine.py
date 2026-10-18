"""
Tests for Warehouse Engine and Metrics (Requirements 7, 19, 20).
"""

from httpx import ASGITransport, AsyncClient
import pytest

from app.core.config import SimulationConfig
from app.main import app
from app.models.order import OrderStatus
from app.services.serialization import serialize_simulation_state
from app.simulation.engine import WarehouseEngine


def test_robot_never_moves_into_shelf_or_obstacle(default_cfg):
    """Requirement 7: The robot never moves into a shelf or obstacle across execution."""
    engine = WarehouseEngine(seed=42, config=default_cfg)
    shelf_coords = {s.pos for s in engine.warehouse_map.shelves}

    # Run for 150 ticks
    for _ in range(150):
        engine.step()
        robot_pos = engine.robot.pos

        # Robot must never occupy any shelf coordinate
        assert robot_pos not in shelf_coords, f"Robot stepped into shelf cell: {robot_pos}"

        # Robot must never occupy an active obstacle coordinate
        assert not engine.warehouse_map.is_obstacle(
            robot_pos[0], robot_pos[1]
        ), f"Robot stepped into obstacle cell: {robot_pos}"


def test_metrics_and_event_history_update_correctly(default_cfg):
    """Requirement 19: Metrics and event history update correctly."""
    engine = WarehouseEngine(seed=42, config=default_cfg)

    # Initial state
    initial_metrics = engine.get_metrics_snapshot()
    assert initial_metrics["tick"] == 0
    assert initial_metrics["total_orders"] == 10
    assert initial_metrics["pending_orders"] == 10
    assert len(engine.event_history) >= 1  # SIMULATION_START

    # Run 60 ticks
    for _ in range(60):
        engine.step()

    updated_metrics = engine.get_metrics_snapshot()
    assert updated_metrics["tick"] == 60
    assert updated_metrics["distance_travelled"] > 0
    assert updated_metrics["movement_count"] > 0
    assert len(engine.event_history) > 1

    # Verify JSON serialization works without error
    serialized = serialize_simulation_state(engine)
    assert serialized["tick"] == 60
    assert "grid" in serialized
    assert "robot" in serialized
    assert "metrics" in serialized
    assert "decision_inspector" in serialized


def test_reset_does_not_retain_stale_state(default_cfg):
    """Requirement 20: Resetting or creating a new engine does not retain stale state."""
    engine = WarehouseEngine(seed=42, config=default_cfg)

    # Advance 80 ticks
    for _ in range(80):
        engine.step()

    assert engine.tick == 80
    assert engine.metrics["distance_travelled"] > 0

    # Reset
    engine.reset(new_seed=42)
    assert engine.tick == 0
    assert engine.elapsed_time_seconds == 0.0
    assert engine.robot.pos == default_cfg.robot_start_pos
    assert engine.robot.battery == default_cfg.initial_battery
    assert engine.metrics["distance_travelled"] == 0
    assert engine.metrics["movement_count"] == 0
    assert len(engine.orders) == 10
    assert all(o.status == OrderStatus.PENDING for o in engine.orders)


def test_manual_triggers(default_cfg):
    """Test manual trigger methods for urgent orders, obstacles, and replenishment."""
    engine = WarehouseEngine(seed=42, config=default_cfg)

    # Trigger urgent order
    order, ev = engine.trigger_urgent_order()
    assert order is not None
    assert order.priority.value == "URGENT"
    assert ev is not None

    # Trigger obstacle
    obs_ev = engine.trigger_obstacle()
    assert obs_ev is not None
    assert len(engine.warehouse_map.obstacles) >= 1

    # Trigger replenishment
    rep_ev = engine.trigger_replenish()
    assert rep_ev is not None


@pytest.mark.asyncio
async def test_fastapi_health_endpoint():
    """Verify that the FastAPI health endpoint is functional and returns status 'ok'."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "WareBot AI"
