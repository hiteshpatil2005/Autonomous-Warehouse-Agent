"""
WareBot AI — A* Pathfinding Engine
Strict 4-directional grid navigation with Manhattan heuristic.
"""

import heapq
from typing import Dict, List, Optional, Set, Tuple

from app.models.warehouse import WarehouseMap


def manhattan_distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """Manhattan distance heuristic h(n) = |r1 - r2| + |c1 - c2|."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def find_path(
    warehouse_map: WarehouseMap,
    start: Tuple[int, int],
    target: Tuple[int, int],
) -> Optional[List[Tuple[int, int]]]:
    """
    A* search algorithm for 4-directional grid navigation.
    Returns list of coordinates from start to target (inclusive),
    or None if target is unreachable or invalid.
    """
    if start == target:
        return [start]

    # Boundary and walkability sanity checks
    if not warehouse_map.is_in_bounds(start[0], start[1]):
        return None
    if not warehouse_map.is_in_bounds(target[0], target[1]):
        return None
    if not warehouse_map.is_walkable(target[0], target[1]):
        # Target itself is impassable (e.g. shelf or obstacle)
        return None

    # Priority queue item: (f_score, g_score, (row, col))
    open_set: List[Tuple[int, int, Tuple[int, int]]] = []
    heapq.heappush(open_set, (manhattan_distance(start, target), 0, start))

    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    g_score: Dict[Tuple[int, int], int] = {start: 0}
    closed_set: Set[Tuple[int, int]] = set()

    # Orthogonal step directions: Up, Down, Left, Right (no diagonals)
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    while open_set:
        _, current_g, current = heapq.heappop(open_set)

        if current == target:
            # Reconstruct path from start to target
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        if current in closed_set:
            continue
        closed_set.add(current)

        for dr, dc in directions:
            neighbor = (current[0] + dr, current[1] + dc)
            nr, nc = neighbor

            # Neighbor must be walkable floor (or target destination)
            if not warehouse_map.is_walkable(nr, nc):
                continue

            tentative_g = current_g + 1

            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f = tentative_g + manhattan_distance(neighbor, target)
                heapq.heappush(open_set, (f, tentative_g, neighbor))

    return None


def find_path_to_adjacent(
    warehouse_map: WarehouseMap,
    start: Tuple[int, int],
    target_pos: Tuple[int, int],
) -> Optional[List[Tuple[int, int]]]:
    """
    Find shortest A* path to any walkable orthogonal cell adjacent to target_pos.
    Used for navigating to shelves which themselves cannot be walked on.
    """
    adjacents = warehouse_map.get_adjacent_walkable(target_pos)
    if not adjacents:
        return None

    best_path: Optional[List[Tuple[int, int]]] = None
    best_cost = float("inf")

    # If start is already adjacent to target, return path containing just start
    if start in adjacents:
        return [start]

    for candidate in adjacents:
        path = find_path(warehouse_map, start, candidate)
        if path and len(path) < best_cost:
            best_cost = len(path)
            best_path = path

    return best_path


def is_route_valid(
    warehouse_map: WarehouseMap,
    route: List[Tuple[int, int]],
    from_index: int = 0,
) -> bool:
    """
    Verify if remaining cells in planned route are still unblocked and within bounds.
    """
    if not route or from_index >= len(route):
        return False

    for i in range(from_index, len(route)):
        r, c = route[i]
        if not warehouse_map.is_walkable(r, c):
            return False

    return True


def recalculate_route(
    warehouse_map: WarehouseMap,
    current_pos: Tuple[int, int],
    target_pos: Tuple[int, int],
    is_shelf_target: bool = False,
) -> Optional[List[Tuple[int, int]]]:
    """Recalculate route upon detecting a blocked path."""
    if is_shelf_target:
        return find_path_to_adjacent(warehouse_map, current_pos, target_pos)
    return find_path(warehouse_map, current_pos, target_pos)
