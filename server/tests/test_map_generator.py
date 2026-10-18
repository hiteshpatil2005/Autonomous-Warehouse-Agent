"""
Tests for Warehouse Map Generator (Requirements 1, 2, 3, 4).
"""

from app.core.config import SimulationConfig
from app.simulation.map_generator import (
    generate_warehouse_map,
    validate_connectivity,
    validate_map_integrity,
)


def test_generated_map_contains_exactly_50_shelves():
    """Requirement 1: Generated maps contain exactly 50 shelves."""
    w_map = generate_warehouse_map(seed=123)
    assert len(w_map.shelves) == 50
    assert w_map.rows == 30
    assert w_map.cols == 30

    # Ensure all shelf IDs are distinct
    shelf_ids = {s.shelf_id for s in w_map.shelves}
    assert len(shelf_ids) == 50


def test_robot_and_stations_occupy_valid_distinct_cells():
    """Requirement 2: Robot and stations occupy valid, distinct cells with no shelf overlap."""
    w_map = generate_warehouse_map(seed=999)
    valid, errors = validate_map_integrity(w_map)
    assert valid, f"Map integrity validation failed: {errors}"

    stations = [w_map.robot_start, w_map.packing_station, w_map.charging_station]
    assert len(set(stations)) == 3, "Robot and stations must occupy distinct cells"

    # All stations must be within 30x30 bounds
    for r, c in stations:
        assert 0 <= r < 30
        assert 0 <= c < 30

    # No shelf may overlap any station
    shelf_coords = {s.pos for s in w_map.shelves}
    for st in stations:
        assert st not in shelf_coords, f"Station {st} overlaps a shelf"


def test_generated_maps_pass_connectivity_validation():
    """Requirement 3: Generated maps pass connectivity validation."""
    for test_seed in [42, 100, 2024, 777]:
        w_map = generate_warehouse_map(seed=test_seed)
        connected, reason = validate_connectivity(w_map)
        assert connected, f"Connectivity check failed for seed {test_seed}: {reason}"


def test_fixed_seeds_produce_reproducible_scenarios():
    """Requirement 4: Fixed seeds produce reproducible initial scenarios."""
    map_a = generate_warehouse_map(seed=555)
    map_b = generate_warehouse_map(seed=555)

    # Identical shelf positions and metadata
    assert len(map_a.shelves) == len(map_b.shelves)
    for s_a, s_b in zip(map_a.shelves, map_b.shelves):
        assert s_a.shelf_id == s_b.shelf_id
        assert s_a.pos == s_b.pos
        assert s_a.product_id == s_b.product_id
        assert s_a.stock == s_b.stock

    assert map_a.robot_start == map_b.robot_start
    assert map_a.packing_station == map_b.packing_station
    assert map_a.charging_station == map_b.charging_station
