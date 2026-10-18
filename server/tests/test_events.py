"""
Tests for Dynamic Event Engine (Requirements 16, 18).
"""

from app.core.config import SimulationConfig
from app.simulation.engine import WarehouseEngine
from app.simulation.event_engine import EventEngine


def test_temporary_obstacles_expire_correctly(seeded_map, default_cfg):
    """Requirement 16: Temporary obstacles expire correctly."""
    event_eng = EventEngine(default_cfg, seed=123)

    # Place an obstacle expiring at tick 10
    seeded_map.obstacles["15,15"] = 10
    assert "15,15" in seeded_map.obstacles

    # Tick 5: Obstacle should remain
    event_eng.process_tick(current_tick=5, warehouse_map=seeded_map, robot=None, orders=[])
    assert "15,15" in seeded_map.obstacles

    # Tick 10: Obstacle expires
    events = event_eng.process_tick(current_tick=10, warehouse_map=seeded_map, robot=None, orders=[])
    assert "15,15" not in seeded_map.obstacles
    assert any(ev.event_type.value == "OBSTACLE_EXPIRED" for ev in events)


def test_event_generation_reproducible_with_fixed_seed(default_cfg):
    """Requirement 18: Event generation is reproducible with a fixed seed."""
    engine_1 = WarehouseEngine(seed=777, config=default_cfg)
    engine_2 = WarehouseEngine(seed=777, config=default_cfg)

    # Run both engines for 50 ticks
    events_1_types = []
    events_2_types = []

    for _ in range(50):
        evs_1 = engine_1.step()
        evs_2 = engine_2.step()
        events_1_types.append([e.event_type.value for e in evs_1])
        events_2_types.append([e.event_type.value for e in evs_2])

    assert events_1_types == events_2_types
    assert engine_1.robot.pos == engine_2.robot.pos
    assert engine_1.robot.battery == engine_2.robot.battery
