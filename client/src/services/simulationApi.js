/**
 * simulationApi.js — REST API client for WareBot AI warehouse simulation.
 */

import { apiRequest } from './api';

export const simulationApi = {
  /**
   * Check backend readiness.
   */
  async getHealth() {
    return apiRequest('/health');
  },

  /**
   * Create a new simulation scenario with optional seed.
   */
  async createSimulation({ seed = null, random_layout = false } = {}) {
    return apiRequest('/api/simulation/create', {
      method: 'POST',
      body: JSON.stringify({ seed, random_layout }),
    });
  },

  /**
   * Fetch current full simulation state snapshot.
   */
  async getState() {
    return apiRequest('/api/simulation/state');
  },

  /**
   * Start autonomous execution.
   */
  async startSimulation() {
    return apiRequest('/api/simulation/start', { method: 'POST' });
  },

  /**
   * Pause execution loop without losing state.
   */
  async pauseSimulation() {
    return apiRequest('/api/simulation/pause', { method: 'POST' });
  },

  /**
   * Resume continuous execution.
   */
  async resumeSimulation() {
    return apiRequest('/api/simulation/resume', { method: 'POST' });
  },

  /**
   * Reset simulation state cleanly.
   */
  async resetSimulation() {
    return apiRequest('/api/simulation/reset', { method: 'POST' });
  },

  /**
   * Advance simulation by exact number of ticks while paused.
   */
  async stepSimulation(steps = 1) {
    return apiRequest('/api/simulation/step', {
      method: 'POST',
      body: JSON.stringify({ steps }),
    });
  },

  /**
   * Update execution speed multiplier (1 to 5).
   */
  async setSpeed(speed = 2) {
    return apiRequest('/api/simulation/speed', {
      method: 'POST',
      body: JSON.stringify({ speed }),
    });
  },

  /**
   * Place a temporary obstacle on the warehouse floor.
   */
  async addObstacle({ row = null, col = null, duration_ticks = 15 } = {}) {
    return apiRequest('/api/simulation/obstacles', {
      method: 'POST',
      body: JSON.stringify({ row, col, duration_ticks }),
    });
  },

  /**
   * Inject a high-urgency order.
   */
  async createUrgentOrder(shelfId = null) {
    return apiRequest('/api/simulation/orders/urgent', {
      method: 'POST',
      body: JSON.stringify({ shelf_id: shelfId }),
    });
  },

  /**
   * Replenish stock on a shelf.
   */
  async replenishInventory({ shelf_id = null, amount = 5 } = {}) {
    return apiRequest('/api/simulation/inventory/replenish', {
      method: 'POST',
      body: JSON.stringify({ shelf_id, amount }),
    });
  },

  /**
   * Fetch order list.
   */
  async getOrders() {
    return apiRequest('/api/simulation/orders');
  },

  /**
   * Fetch live metrics.
   */
  async getMetrics() {
    return apiRequest('/api/simulation/metrics');
  },

  /**
   * Fetch recent activity log events.
   */
  async getEvents() {
    return apiRequest('/api/simulation/events');
  },

  /**
   * Fetch latest AI decision explanation and candidate scores.
   */
  async getDecision() {
    return apiRequest('/api/simulation/decision');
  },

  // ── Benchmarking Endpoints (Part 4) ───────────────────────────────────────
  /**
   * Start a comparative benchmark job (Utility AI vs Nearest-Order baseline).
   */
  async runBenchmark({ runs = 10, seeds = null, max_ticks_per_run = 120 } = {}) {
    return apiRequest('/api/benchmark/run', {
      method: 'POST',
      body: JSON.stringify({ runs, seeds, max_ticks_per_run }),
    });
  },

  /**
   * Fetch active or most recent benchmark job.
   */
  async getActiveBenchmark() {
    return apiRequest('/api/benchmark/active');
  },

  /**
   * Fetch benchmark status and summaries by job ID.
   */
  async getBenchmark(jobId) {
    return apiRequest(`/api/benchmark/${jobId}`);
  },

  /**
   * Fetch detailed per-seed runs for a benchmark job.
   */
  async getBenchmarkResults(jobId) {
    return apiRequest(`/api/benchmark/${jobId}/results`);
  },

  /**
   * Get direct download URL for benchmark CSV export.
   */
  getBenchmarkExportUrl(jobId) {
    const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    return `${base}/api/benchmark/${jobId}/export`;
  },
};
