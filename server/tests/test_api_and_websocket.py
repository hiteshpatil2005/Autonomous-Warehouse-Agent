"""
Integration and Unit Tests for FastAPI REST Endpoints and WebSocket Stream (Part 3).
Covers:
1. Health endpoint
2. Create simulation and retrieve state
3. Start, pause, resume behavior
4. Single-step behavior
5. Reset during execution
6. Duplicate Start and Resume requests
7. Invalid obstacle requests
8. Urgent-order creation
9. Inventory replenishment
10. State serialization
11. WebSocket initial snapshot
12. WebSocket state updates after a simulation tick
13. Disconnected WebSocket client handling
14. Concurrent command safety
"""

import asyncio
import pytest
from starlette.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.simulation_manager import sim_manager


@pytest.fixture(autouse=True)
def reset_manager():
    """Ensure simulation manager starts idle with standard seed before each test."""
    asyncio.run(sim_manager.reset(new_seed=42))
    yield
    asyncio.run(sim_manager.pause())


@pytest.mark.asyncio
async def test_1_health_endpoint():
    """Test 1: Health endpoint responds with 200 OK and ready status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["service"] == "WareBot AI"


@pytest.mark.asyncio
async def test_2_create_simulation_and_get_state():
    """Test 2: Create simulation and retrieve state."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create simulation with fixed seed
        res_create = await ac.post("/api/simulation/create", json={"seed": 101, "random_layout": False})
        assert res_create.status_code == 200
        data_create = res_create.json()
        assert data_create["tick"] == 0
        assert len(data_create["grid"]["shelves"]) == 50

        # Retrieve state
        res_state = await ac.get("/api/simulation/state")
        assert res_state.status_code == 200
        data_state = res_state.json()
        assert data_state["simulation_id"] == data_create["simulation_id"]
        assert data_state["robot"]["battery"] == 100.0


@pytest.mark.asyncio
async def test_3_start_pause_resume_behavior():
    """Test 3: Start, pause, and resume execution behavior."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Start
        res_start = await ac.post("/api/simulation/start")
        assert res_start.status_code == 200
        assert res_start.json()["status"] == "running"
        assert sim_manager.status == "running"

        # Pause
        res_pause = await ac.post("/api/simulation/pause")
        assert res_pause.status_code == 200
        assert res_pause.json()["status"] == "paused"
        assert sim_manager.status == "paused"

        # Resume
        res_resume = await ac.post("/api/simulation/resume")
        assert res_resume.status_code == 200
        assert res_resume.json()["status"] == "running"
        assert sim_manager.status == "running"

        # Clean up
        await ac.post("/api/simulation/pause")


@pytest.mark.asyncio
async def test_4_single_step_behavior():
    """Test 4: Single-step advances exactly one simulation tick."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        initial_tick = sim_manager.engine.tick

        res_step = await ac.post("/api/simulation/step", json={"steps": 1})
        assert res_step.status_code == 200
        data_step = res_step.json()
        assert data_step["tick"] == initial_tick + 1

        # Advance 3 ticks
        res_step3 = await ac.post("/api/simulation/step", json={"steps": 3})
        assert res_step3.status_code == 200
        assert res_step3.json()["tick"] == initial_tick + 4


@pytest.mark.asyncio
async def test_5_reset_during_execution():
    """Test 5: Reset during execution stops loop and clears metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Start execution
        await ac.post("/api/simulation/start")
        await asyncio.sleep(0.3)  # Allow a tick or two to run

        # Reset
        res_reset = await ac.post("/api/simulation/reset")
        assert res_reset.status_code == 200
        data_reset = res_reset.json()

        assert sim_manager.status == "idle"
        assert data_reset["tick"] == 0
        assert data_reset["metrics"]["movement_count"] == 0
        assert data_reset["robot"]["pos"] == [28, 1]


@pytest.mark.asyncio
async def test_6_duplicate_start_and_resume_requests():
    """Test 6: Duplicate Start and Resume requests do not spawn extra loops."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # First start
        res1 = await ac.post("/api/simulation/start")
        assert res1.status_code == 200
        task1 = sim_manager._background_task

        # Duplicate start
        res2 = await ac.post("/api/simulation/start")
        assert res2.status_code == 200
        # Background task should remain the identical single task
        assert sim_manager._background_task is task1

        # Duplicate resume
        res3 = await ac.post("/api/simulation/resume")
        assert res3.status_code == 200
        assert sim_manager._background_task is task1

        # Clean up
        await ac.post("/api/simulation/pause")


@pytest.mark.asyncio
async def test_7_invalid_obstacle_requests():
    """Test 7: Obstacle requests on shelf, stations, or robot are rejected with 400 Bad Request."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Reject obstacle on robot position (28, 1)
        res_robot = await ac.post("/api/simulation/obstacles", json={"row": 28, "col": 1})
        assert res_robot.status_code == 400
        assert "Cannot place obstacle on station or robot cell" in res_robot.json()["detail"]

        # 2. Reject obstacle on packing station (28, 14)
        res_packing = await ac.post("/api/simulation/obstacles", json={"row": 28, "col": 14})
        assert res_packing.status_code == 400

        # 3. Reject obstacle on a shelf (row 4, col 3 is SH-01)
        shelf = sim_manager.engine.warehouse_map.shelves[0]
        res_shelf = await ac.post("/api/simulation/obstacles", json={"row": shelf.row, "col": shelf.col})
        assert res_shelf.status_code == 400
        assert "Cannot place obstacle on shelf" in res_shelf.json()["detail"]

        # 4. Valid obstacle on free floor cell succeeds
        res_valid = await ac.post("/api/simulation/obstacles", json={"row": 15, "col": 15, "duration_ticks": 10})
        assert res_valid.status_code == 200
        assert "15,15" in sim_manager.engine.warehouse_map.obstacles


@pytest.mark.asyncio
async def test_8_urgent_order_creation():
    """Test 8: Urgent-order creation via REST API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        initial_order_count = len(sim_manager.engine.orders)

        res = await ac.post("/api/simulation/orders/urgent")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert len(sim_manager.engine.orders) == initial_order_count + 1

        newest_order = sim_manager.engine.orders[-1]
        assert newest_order.priority.value == "URGENT"


@pytest.mark.asyncio
async def test_9_inventory_replenishment():
    """Test 9: Inventory replenishment via REST API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        shelf = sim_manager.engine.warehouse_map.shelves[0]
        shelf.stock = 5

        res = await ac.post("/api/simulation/inventory/replenish", json={"shelf_id": shelf.shelf_id, "amount": 7})
        assert res.status_code == 200
        assert shelf.stock == 12


@pytest.mark.asyncio
async def test_10_state_serialization():
    """Test 10: State serialization contains all necessary structures."""
    state = sim_manager.get_full_state()
    assert "tick" in state
    assert "grid" in state
    assert "robot" in state
    assert "orders" in state
    assert "metrics" in state
    assert "events" in state
    assert "decision_inspector" in state

    assert state["grid"]["rows"] == 30
    assert state["grid"]["cols"] == 30
    assert len(state["grid"]["shelves"]) == 50
    assert state["robot"]["battery"] >= 0.0


def test_11_websocket_initial_snapshot():
    """Test 11: WebSocket receives initial state snapshot immediately upon connection."""
    client = TestClient(app)
    with client.websocket_connect("/api/simulation/stream") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "simulation_state"
        assert "data" in msg
        snapshot = msg["data"]
        assert snapshot["tick"] == 0
        assert snapshot["robot"]["battery"] == 100.0


def test_12_websocket_state_updates_after_tick():
    """Test 12: WebSocket broadcasts state update when simulation step occurs."""
    client = TestClient(app)
    with client.websocket_connect("/api/simulation/stream") as ws:
        # Initial snapshot
        msg1 = ws.receive_json()
        assert msg1["type"] == "simulation_state"

        # Advance step via REST
        res = client.post("/api/simulation/step", json={"steps": 1})
        assert res.status_code == 200

        # WebSocket should receive the broadcasted update
        msg2 = ws.receive_json()
        assert msg2["type"] == "simulation_state"
        assert msg2["data"]["tick"] == 1


def test_13_disconnected_websocket_handling():
    """Test 13: Disconnected WebSocket clients do not crash broadcasting or the engine."""
    client = TestClient(app)
    with client.websocket_connect("/api/simulation/stream") as ws:
        _ = ws.receive_json()  # Consume initial snapshot
        ws.close()

    # Step engine and broadcast — manager must handle missing/closed socket safely
    res = client.post("/api/simulation/step", json={"steps": 1})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_14_concurrent_command_safety():
    """Test 14: Concurrent commands do not corrupt state."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Fire multiple concurrent requests
        reqs = [
            ac.post("/api/simulation/step", json={"steps": 1}),
            ac.post("/api/simulation/orders/urgent"),
            ac.post("/api/simulation/step", json={"steps": 1}),
            ac.post("/api/simulation/inventory/replenish", json={"amount": 3}),
        ]
        results = await asyncio.gather(*reqs)
        for r in results:
            assert r.status_code in (200, 400)

        # Simulation state remains coherent
        state = sim_manager.get_full_state()
        assert state["tick"] >= 2
        assert len(state["orders"]) >= 10
