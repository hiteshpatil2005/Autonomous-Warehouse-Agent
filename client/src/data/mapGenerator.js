/**
 * Warehouse map generator for WareBot AI.
 * Produces a 30×30 grid with exactly 50 shelf cells,
 * 1 robot start, 1 packing station, and 1 charging station.
 *
 * Coordinate system: [row, col], row 0 = top, col 0 = left.
 */

export const CELL_TYPES = {
  FLOOR:     'floor',
  SHELF:     'shelf',
  ROBOT:     'robot',
  PACKING:   'packing',
  CHARGING:  'charging',
  OBSTACLE:  'obstacle',
};

const GRID_ROWS = 30;
const GRID_COLS = 30;

// All products available across shelves
export const PRODUCTS = [
  'Widget Alpha',    'Gear Beta',       'Circuit Board C', 'Sensor Module D',
  'Actuator E',      'Power Unit F',    'Controller G',    'Motor Assembly H',
  'Valve Pack I',    'Cable Bundle J',  'Filter Kit K',    'Pump Module L',
  'Relay Board M',   'Switch Panel N',  'Drive Unit O',    'Encoder P',
  'Servo Q',         'Hydraulic R',     'Pneumatic S',     'Frame T',
  'Bearing Set U',   'Coolant Tank V',  'Fan Module W',    'Bracket X',
];

/** Seeded LCG random number generator → returns [0, 1) */
function mkRng(seed) {
  let s = (seed >>> 0) || 1;
  return () => {
    s = (Math.imul(1664525, s) + 1013904223) >>> 0;
    return s / 0x100000000;
  };
}

function shuffle(arr, rng) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/**
 * Generate a structured, navigation-friendly 30×30 warehouse map.
 *
 * Layout strategy:
 *   Shelf rows come from 5 bands: [2-4], [6-8], [10-12], [14-16], [18-20].
 *   One row is picked per band (seeded).
 *   Shelf columns: 10 positions from a pool of 18 valid cols (spaced ≥2 apart).
 *   Result: 5 × 10 = exactly 50 shelves.
 *   Rows 21-29 are kept clear for station access.
 *
 * @param {number} seed
 * @returns {{ grid, robotPos, packingPos, chargingPos, shelves }}
 */
export function generateMap(seed = 42) {
  const rng = mkRng(seed);

  // ── 1. Build empty floor grid ────────────────────────────────
  const grid = Array.from({ length: GRID_ROWS }, (_, r) =>
    Array.from({ length: GRID_COLS }, (_, c) => ({
      type: CELL_TYPES.FLOOR,
      row: r,
      col: c,
      shelfId: null,
    }))
  );

  // ── 2. Fixed station positions (always on clear rows 25-29) ──
  const robotPos   = { row: 28, col: 1  };
  const packingPos = { row: 28, col: 14 };
  const chargingPos= { row: 28, col: 27 };

  // ── 3. Select shelf rows (one per band) ──────────────────────
  const rowBands = [[2,3,4],[6,7,8],[10,11,12],[14,15,16],[18,19,20]];
  const shelfRows = rowBands.map(band => band[Math.floor(rng() * band.length)]);

  // ── 4. Select shelf columns (10 from pool, ≥2 gap between each) ──
  // Pool: every 2nd col in 2-28 range, giving 14 candidates;
  // shuffle and pick 10, then sort.
  const colPool = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28];
  const shelfCols = shuffle(colPool, rng).slice(0, 10).sort((a, b) => a - b);

  // ── 5. Place shelves ─────────────────────────────────────────
  const shelves = [];
  let idx = 0;

  for (const row of shelfRows) {
    for (const col of shelfCols) {
      const shelfId = `S-${String(idx + 1).padStart(2, '0')}`;
      // Assign 2-3 random products and random stock
      const products = shuffle(PRODUCTS, rng).slice(0, Math.floor(rng() * 2) + 2);
      const stock    = Math.floor(rng() * 18) + 4;

      grid[row][col] = { type: CELL_TYPES.SHELF, row, col, shelfId };
      shelves.push({ id: shelfId, row, col, products, stock });
      idx++;
    }
  }

  // ── 6. Set station cells ─────────────────────────────────────
  grid[robotPos.row][robotPos.col].type    = CELL_TYPES.ROBOT;
  grid[packingPos.row][packingPos.col].type= CELL_TYPES.PACKING;
  grid[chargingPos.row][chargingPos.col].type = CELL_TYPES.CHARGING;

  return { grid, robotPos, packingPos, chargingPos, shelves };
}

/** Validate a generated map: exactly 50 shelves, unique stations, no overlap. */
export function validateMap({ grid, robotPos, packingPos, chargingPos, shelves }) {
  const errors = [];
  if (shelves.length !== 50) errors.push(`Expected 50 shelves, got ${shelves.length}`);

  const keys = new Set();
  const add = (pos, label) => {
    const k = `${pos.row},${pos.col}`;
    if (keys.has(k)) errors.push(`Overlap at ${k} (${label})`);
    keys.add(k);
  };
  add(robotPos, 'robot');
  add(packingPos, 'packing');
  add(chargingPos, 'charging');

  return { valid: errors.length === 0, errors };
}
