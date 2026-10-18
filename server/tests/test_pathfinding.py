"""
Tests for A* Pathfinding Engine (Requirements 5, 6, 17).
"""

from app.simulation.map_generator import generate_warehouse_map
from app.simulation.pathfinding import (
    find_path,
    find_path_to_adjacent,
    is_route_valid,
    manhattan_distance,
    recalculate_route,
)


def test_astar_returns_valid_paths_around_shelves(seeded_map):
    """Requirement 5: A* returns valid paths around shelves without diagonal moves."""
    start = seeded_map.robot_start
    target = seeded_map.packing_station

    path = find_path(seeded_map, start, target)
    assert path is not None
    assert path[0] == start
    assert path[-1] == target

    shelf_positions = {s.pos for s in seeded_map.shelves}

    # Verify each step is orthogonal (Manhattan step == 1) and never steps on a shelf
    for i in range(len(path) - 1):
        step_a = path[i]
        step_b = path[i + 1]
        dist = manhattan_distance(step_a, step_b)
        assert dist == 1, f"Diagonal or non-unit movement detected between {step_a} and {step_b}"
        assert step_a not in shelf_positions, f"Path passed through shelf at {step_a}"
        assert step_b not in shelf_positions, f"Path passed through shelf at {step_b}"


def test_astar_detects_unreachable_destinations(seeded_map):
    """Requirement 6: A* detects unreachable destinations."""
    start = seeded_map.robot_start

    # Destination on a shelf itself is impassable
    shelf_pos = seeded_map.shelves[0].pos
    assert find_path(seeded_map, start, shelf_pos) is None

    # Destination surrounded completely by obstacles is unreachable
    isolated_target = (10, 10)
    # Block all 4 neighbors of (10, 10)
    surroundings = [(9, 10), (11, 10), (10, 9), (10, 11)]
    for r, c in surroundings:
        seeded_map.obstacles[f"{r},{c}"] = 999

    unreachable_path = find_path(seeded_map, start, isolated_target)
    assert unreachable_path is None

    # Clean up obstacles
    for r, c in surroundings:
        del seeded_map.obstacles[f"{r},{c}"]


def test_route_recalculation_after_route_invalidation(seeded_map):
    """Requirement 17: Route recalculation occurs after route invalidation."""
    start = (20, 10)
    target = (20, 18)

    original_path = find_path(seeded_map, start, target)
    assert original_path is not None
    assert is_route_valid(seeded_map, original_path)

    # Invalidate route by placing an obstacle on an intermediate waypoint
    block_node = original_path[len(original_path) // 2]
    seeded_map.obstacles[f"{block_node[0]},{block_node[1]}"] = 100

    # Original route must now fail validation
    assert not is_route_valid(seeded_map, original_path)

    # Recalculate route
    new_path = recalculate_route(seeded_map, start, target, is_shelf_target=False)
    assert new_path is not None
    assert block_node not in new_path, "Recalculated route must bypass the newly placed obstacle"
    assert is_route_valid(seeded_map, new_path)

    # Clean up
    del seeded_map.obstacles[f"{block_node[0]},{block_node[1]}"]
