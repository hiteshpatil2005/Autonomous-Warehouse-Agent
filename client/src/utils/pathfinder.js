/**
 * A* pathfinding for the 30×30 warehouse grid.
 * Coordinates: [row, col], 0-indexed, row 0 = top, col 0 = left.
 *
 * Returns an array of {row, col} from start to end (inclusive),
 * or null if no path exists.
 */

const GRID_ROWS = 30;
const GRID_COLS = 30;
const DIRS = [[-1, 0], [1, 0], [0, -1], [0, 1]];

function posKey(row, col) {
  return row * 100 + col; // Fast integer key for 30×30 grid
}

function heuristic(ar, ac, br, bc) {
  return Math.abs(ar - br) + Math.abs(ac - bc);
}

/**
 * Find a path through the grid avoiding shelves and obstacles.
 * @param {Array<Array<{type:string}>>} grid  - 30×30 base grid
 * @param {{row:number,col:number}} start
 * @param {{row:number,col:number}} end
 * @param {Array<{row:number,col:number}>} obstacles - dynamic obstacles
 * @returns {Array<{row:number,col:number}>|null}
 */
export function findPath(grid, start, end, obstacles = []) {
  if (!grid || !start || !end) return null;
  if (start.row === end.row && start.col === end.col) return [start];

  // Build obstacle set
  const blocked = new Set();
  for (const o of obstacles) blocked.add(posKey(o.row, o.col));

  const isWalkable = (r, c) => {
    if (r < 0 || r >= GRID_ROWS || c < 0 || c >= GRID_COLS) return false;
    if (blocked.has(posKey(r, c))) return false;
    const t = grid[r][c]?.type;
    // Shelves are impassable; everything else (floor, packing, charging, robot) is walkable
    return t !== 'shelf';
  };

  if (!isWalkable(end.row, end.col)) return null;

  // A* open set as a min-heap (simulated with array + linear scan for simplicity)
  // For 900 cells this is fast enough
  const open = new Map(); // key → node
  const closed = new Set();
  const g = new Map();

  const startKey = posKey(start.row, start.col);
  const startNode = {
    r: start.row, c: start.col,
    g: 0,
    f: heuristic(start.row, start.col, end.row, end.col),
    parent: null,
  };
  open.set(startKey, startNode);
  g.set(startKey, 0);

  while (open.size > 0) {
    // Pick node with lowest f
    let bestKey = null;
    let bestF = Infinity;
    for (const [k, node] of open) {
      if (node.f < bestF) { bestF = node.f; bestKey = k; }
    }
    const cur = open.get(bestKey);
    open.delete(bestKey);
    closed.add(bestKey);

    if (cur.r === end.row && cur.c === end.col) {
      // Reconstruct
      const path = [];
      let n = cur;
      while (n) { path.unshift({ row: n.r, col: n.c }); n = n.parent; }
      return path;
    }

    for (const [dr, dc] of DIRS) {
      const nr = cur.r + dr;
      const nc = cur.c + dc;
      const nk = posKey(nr, nc);
      if (!isWalkable(nr, nc) || closed.has(nk)) continue;

      const ng = cur.g + 1;
      if (!g.has(nk) || ng < g.get(nk)) {
        g.set(nk, ng);
        open.set(nk, {
          r: nr, c: nc,
          g: ng,
          f: ng + heuristic(nr, nc, end.row, end.col),
          parent: cur,
        });
      }
    }
  }
  return null;
}

/**
 * Find the nearest walkable cell adjacent to a target position.
 * Used to get the pickup cell next to a shelf.
 */
export function findAdjacentWalkable(grid, targetPos, obstacles = []) {
  const blocked = new Set(obstacles.map(o => posKey(o.row, o.col)));
  for (const [dr, dc] of DIRS) {
    const r = targetPos.row + dr;
    const c = targetPos.col + dc;
    if (r < 0 || r >= GRID_ROWS || c < 0 || c >= GRID_COLS) continue;
    if (blocked.has(posKey(r, c))) continue;
    const t = grid[r][c]?.type;
    if (t && t !== 'shelf') return { row: r, col: c };
  }
  return null;
}
