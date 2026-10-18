/**
 * Order generator for WareBot AI mock simulation.
 * Creates realistic orders referencing actual shelf positions.
 */

const PRIORITIES = ['LOW', 'MEDIUM', 'HIGH', 'URGENT'];

const PRIORITY_WEIGHT = [3, 4, 2, 1]; // LOW is most common

function mkRng(seed) {
  let s = (seed >>> 0) || 1;
  return () => {
    s = (Math.imul(1664525, s) + 1013904223) >>> 0;
    return s / 0x100000000;
  };
}

function weightedPriority(rng) {
  const total = PRIORITY_WEIGHT.reduce((a, b) => a + b, 0);
  let r = rng() * total;
  for (let i = 0; i < PRIORITIES.length; i++) {
    r -= PRIORITY_WEIGHT[i];
    if (r <= 0) return PRIORITIES[i];
  }
  return 'LOW';
}

let orderCounter = 1000;

/**
 * Generate initial 10 mock orders for the simulation.
 * @param {Array} shelves - from generateMap
 * @param {number} seed
 * @returns {Array<Order>}
 */
export function generateOrders(shelves, seed = 42) {
  if (!shelves || shelves.length === 0) return [];
  const rng = mkRng(seed + 9999);
  const orders = [];

  for (let i = 0; i < 10; i++) {
    const shelf = shelves[Math.floor(rng() * shelves.length)];
    const product = shelf.products[Math.floor(rng() * shelf.products.length)];
    const priority = weightedPriority(rng);
    const quantity = Math.floor(rng() * 4) + 1;
    const hasDeadline = rng() > 0.45;
    const deadlineMinutes = Math.floor(rng() * 90) + 15;

    orders.push({
      id: `ORD-${++orderCounter}`,
      product,
      quantity,
      priority,
      targetShelfId: shelf.id,
      targetShelfPos: { row: shelf.row, col: shelf.col },
      status: 'pending',   // pending | assigned | picking | packing | completed
      deadline: hasDeadline
        ? new Date(Date.now() + deadlineMinutes * 60_000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : null,
      createdAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      completedAt: null,
    });
  }

  // Sort by priority weight (URGENT first)
  const pw = { URGENT: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
  return orders.sort((a, b) => pw[a.priority] - pw[b.priority]);
}

/**
 * Create a single urgent order (used by the "Add Urgent Order" action).
 */
export function createUrgentOrder(shelves, existingOrders = []) {
  const rng = mkRng(Date.now() % 1_000_000);
  const shelf = shelves[Math.floor(rng() * shelves.length)];
  const product = shelf.products[0] || 'Emergency Part';

  const maxId = existingOrders.reduce((max, o) => {
    const n = parseInt(o.id.replace('ORD-', ''), 10);
    return isNaN(n) ? max : Math.max(max, n);
  }, orderCounter);
  orderCounter = Math.max(orderCounter, maxId);

  return {
    id: `ORD-${++orderCounter}`,
    product,
    quantity: 1,
    priority: 'URGENT',
    targetShelfId: shelf.id,
    targetShelfPos: { row: shelf.row, col: shelf.col },
    status: 'pending',
    deadline: new Date(Date.now() + 10 * 60_000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    createdAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    completedAt: null,
  };
}
