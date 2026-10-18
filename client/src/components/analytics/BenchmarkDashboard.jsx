/**
 * BenchmarkDashboard.jsx — Performance Benchmark & Comparative Analytics
 * Compares WareBot Autonomous Utility AI against Nearest-Order Baseline under
 * strictly identical warehouse maps, inventory, battery, and safety constraints.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid
} from 'recharts';
import {
  Trophy, Play, Download, RefreshCw, CheckCircle, Clock, Zap, Target, Route, ShieldAlert, FileSpreadsheet
} from 'lucide-react';
import { simulationApi } from '../../services/simulationApi';

export default function BenchmarkDashboard() {
  const [runs, setRuns] = useState(10);
  const [maxTicks, setMaxTicks] = useState(120);
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const pollTimerRef = useRef(null);

  // ── Poll Active Benchmark Status ──────────────────────────────────────────
  const pollJobStatus = useCallback(async (jobId) => {
    try {
      const current = await simulationApi.getBenchmark(jobId);
      setJob(current);

      if (current.status === 'completed' || current.status === 'failed') {
        clearInterval(pollTimerRef.current);
        setLoading(false);
      }
    } catch (err) {
      console.error('[Benchmark] Poll error:', err);
      clearInterval(pollTimerRef.current);
      setLoading(false);
    }
  }, []);

  // ── Fetch Existing Benchmark on Mount ─────────────────────────────────────
  useEffect(() => {
    async function loadActive() {
      try {
        const active = await simulationApi.getActiveBenchmark();
        if (active) {
          setJob(active);
          if (active.status === 'running' || active.status === 'queued') {
            setLoading(true);
            pollTimerRef.current = setInterval(() => pollJobStatus(active.job_id), 1000);
          }
        }
      } catch (err) {
        console.warn('[Benchmark] Unable to load active benchmark:', err);
      }
    }
    loadActive();

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [pollJobStatus]);

  // ── Launch Benchmark Execution ───────────────────────────────────────────
  const handleRunBenchmark = async () => {
    setLoading(true);
    setError(null);
    try {
      const newJob = await simulationApi.runBenchmark({
        runs: Number(runs),
        max_ticks_per_run: Number(maxTicks),
      });
      setJob(newJob);

      // Start polling
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      pollTimerRef.current = setInterval(() => pollJobStatus(newJob.job_id), 1000);
    } catch (err) {
      setError(err.message || 'Failed to start benchmark job.');
      setLoading(false);
    }
  };

  const uSummary = job?.utility_summary;
  const bSummary = job?.baseline_summary;

  // ── Prepare Recharts Data ────────────────────────────────────────────────
  const rateChartData = uSummary && bSummary ? [
    {
      metric: 'Completion Rate (%)',
      'WareBot Utility AI': uSummary.avg_completion_rate_pct,
      'Nearest-Order Baseline': bSummary.avg_completion_rate_pct,
    },
    {
      metric: 'Deadline Success (%)',
      'WareBot Utility AI': uSummary.avg_deadline_success_rate_pct,
      'Nearest-Order Baseline': bSummary.avg_deadline_success_rate_pct,
    },
  ] : [];

  const efficiencyChartData = uSummary && bSummary ? [
    {
      metric: 'Avg Completion (Ticks)',
      'WareBot Utility AI': uSummary.avg_completion_time_ticks,
      'Nearest-Order Baseline': bSummary.avg_completion_time_ticks,
    },
    {
      metric: 'Energy per Order (Units)',
      'WareBot Utility AI': uSummary.avg_energy_per_order,
      'Nearest-Order Baseline': bSummary.avg_energy_per_order,
    },
    {
      metric: 'Distance per Run (Cells)',
      'WareBot Utility AI': Math.round(uSummary.avg_distance_travelled / 5), // scaled for display
      'Nearest-Order Baseline': Math.round(bSummary.avg_distance_travelled / 5),
    },
  ] : [];

  return (
    <div className="flex-1 flex flex-col gap-3 p-3 overflow-y-auto min-h-0 bg-wh-bg text-gray-200">
      {/* ── Top Bar: Config & Controls ────────────────────────────────────── */}
      <div className="panel flex items-center gap-3 px-4 py-3 shrink-0">
        <div className="flex items-center gap-2">
          <Trophy size={18} className="text-amber-400" />
          <div>
            <div className="text-sm font-bold text-white leading-tight">AI Strategy Benchmark</div>
            <div className="text-[10px] text-wh-muted font-mono">Controlled multi-seed experimental evaluation</div>
          </div>
        </div>

        <div className="h-6 w-px bg-wh-border mx-2" />

        {/* Runs selector */}
        <div className="flex items-center gap-1.5 text-xs text-wh-muted">
          <span>Runs:</span>
          <select
            value={runs}
            onChange={e => setRuns(Number(e.target.value))}
            disabled={loading}
            className="bg-wh-card border border-wh-border text-xs rounded px-2 py-1 text-gray-200"
          >
            <option value={5}>5 Seeds (Fast)</option>
            <option value={10}>10 Seeds (Standard)</option>
            <option value={20}>20 Seeds (Comprehensive)</option>
          </select>
        </div>

        {/* Max Ticks */}
        <div className="flex items-center gap-1.5 text-xs text-wh-muted">
          <span>Ticks:</span>
          <select
            value={maxTicks}
            onChange={e => setMaxTicks(Number(e.target.value))}
            disabled={loading}
            className="bg-wh-card border border-wh-border text-xs rounded px-2 py-1 text-gray-200"
          >
            <option value={80}>80 Ticks</option>
            <option value={120}>120 Ticks (Default)</option>
            <option value={160}>160 Ticks</option>
          </select>
        </div>

        {/* Start Button */}
        <button
          onClick={handleRunBenchmark}
          disabled={loading}
          className="btn btn-primary ml-2 px-3 py-1.5"
        >
          {loading ? (
            <>
              <RefreshCw size={13} className="animate-spin" />
              Running... ({job?.progress_pct?.toFixed(0)}%)
            </>
          ) : (
            <>
              <Play size={13} />
              Run Benchmark
            </>
          )}
        </button>

        {/* Export CSV Button */}
        {job?.status === 'completed' && (
          <a
            href={simulationApi.getBenchmarkExportUrl(job.job_id)}
            download
            className="btn btn-ghost border border-wh-border px-3 py-1.5 ml-auto flex items-center gap-1.5 text-xs"
          >
            <FileSpreadsheet size={13} className="text-emerald-400" />
            Export CSV
          </a>
        )}
      </div>

      {/* Progress Bar when Running */}
      {loading && job && (
        <div className="panel p-3 flex flex-col gap-1.5 shrink-0">
          <div className="flex justify-between text-xs text-wh-muted">
            <span>Executing benchmark across {job.runs_requested} seed scenarios...</span>
            <span className="font-mono text-cyan-300">{job.progress_pct?.toFixed(0)}%</span>
          </div>
          <div className="w-full bg-wh-border rounded-full h-2 overflow-hidden">
            <div
              className="bg-cyan-500 h-full rounded-full transition-all duration-300"
              style={{ width: `${job.progress_pct}%` }}
            />
          </div>
        </div>
      )}

      {/* Error alert */}
      {error && (
        <div className="p-3 bg-red-950/60 border border-red-800 rounded-lg text-xs text-red-200 flex items-center gap-2">
          <ShieldAlert size={16} className="text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ── Verdict Banner ────────────────────────────────────────────────── */}
      {job?.comparison_verdict && (
        <div className="panel p-3 bg-gradient-to-r from-cyan-950/40 to-indigo-950/40 border border-cyan-800/60 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-cyan-900/60 border border-cyan-600 flex items-center justify-center shrink-0">
            <CheckCircle size={18} className="text-cyan-400" />
          </div>
          <div className="text-xs">
            <div className="font-bold text-white mb-0.5">Benchmark Findings ({job.runs_requested} Scenarios)</div>
            <div className="text-gray-300">{job.comparison_verdict}</div>
          </div>
        </div>
      )}

      {/* ── Summary KPI Cards ─────────────────────────────────────────────── */}
      {uSummary && bSummary ? (
        <>
          <div className="grid grid-cols-4 gap-3 shrink-0">
            {/* KPI 1: Completion Rate */}
            <div className="panel p-3 flex flex-col gap-1">
              <div className="text-[10px] uppercase font-mono text-wh-muted">Order Completion Rate</div>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-xl font-bold font-mono text-cyan-400">{uSummary.avg_completion_rate_pct}%</span>
                <span className="text-xs text-wh-muted">vs</span>
                <span className="text-sm font-mono text-gray-400">{bSummary.avg_completion_rate_pct}%</span>
              </div>
              <div className="text-[10px] text-wh-muted mt-1">
                Utility AI: {uSummary.avg_completed_orders} orders/run
              </div>
            </div>

            {/* KPI 2: Deadline Success */}
            <div className="panel p-3 flex flex-col gap-1">
              <div className="text-[10px] uppercase font-mono text-wh-muted">Deadline Compliance</div>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-xl font-bold font-mono text-emerald-400">{uSummary.avg_deadline_success_rate_pct}%</span>
                <span className="text-xs text-wh-muted">vs</span>
                <span className="text-sm font-mono text-gray-400">{bSummary.avg_deadline_success_rate_pct}%</span>
              </div>
              <div className="text-[10px] text-emerald-300/80 mt-1">
                {uSummary.avg_deadline_success_rate_pct >= bSummary.avg_deadline_success_rate_pct ? '+ Higher punctuality' : 'Baseline faster'}
              </div>
            </div>

            {/* KPI 3: Avg Completion Time */}
            <div className="panel p-3 flex flex-col gap-1">
              <div className="text-[10px] uppercase font-mono text-wh-muted">Avg Completion Time</div>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-xl font-bold font-mono text-amber-400">{uSummary.avg_completion_time_ticks}</span>
                <span className="text-xs text-wh-muted">vs</span>
                <span className="text-sm font-mono text-gray-400">{bSummary.avg_completion_time_ticks}</span>
                <span className="text-xs text-wh-muted">ticks</span>
              </div>
              <div className="text-[10px] text-wh-muted mt-1">Duration per fulfilled item</div>
            </div>

            {/* KPI 4: Energy per Order */}
            <div className="panel p-3 flex flex-col gap-1">
              <div className="text-[10px] uppercase font-mono text-wh-muted">Energy per Order</div>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-xl font-bold font-mono text-purple-400">{uSummary.avg_energy_per_order}</span>
                <span className="text-xs text-wh-muted">vs</span>
                <span className="text-sm font-mono text-gray-400">{bSummary.avg_energy_per_order}</span>
                <span className="text-xs text-wh-muted">units</span>
              </div>
              <div className="text-[10px] text-wh-muted mt-1">Battery consumption efficiency</div>
            </div>
          </div>

          {/* ── Visual Comparison Charts (Recharts) ─────────────────────────── */}
          <div className="grid grid-cols-2 gap-3 shrink-0 h-64">
            {/* Chart 1: Success & Deadlines */}
            <div className="panel p-3 flex flex-col min-h-0">
              <div className="text-xs font-bold text-gray-300 mb-2">Success Rates & Deadline Compliance (%)</div>
              <div className="flex-1 min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={rateChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                    <XAxis dataKey="metric" stroke="#64748b" tick={{ fontSize: 11 }} />
                    <YAxis domain={[0, 100]} stroke="#64748b" tick={{ fontSize: 11 }} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }} />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />
                    <Bar dataKey="WareBot Utility AI" fill="#06b6d4" radius={[3, 3, 0, 0]} />
                    <Bar dataKey="Nearest-Order Baseline" fill="#64748b" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 2: Operational Efficiency */}
            <div className="panel p-3 flex flex-col min-h-0">
              <div className="text-xs font-bold text-gray-300 mb-2">Operational Efficiency Metrics</div>
              <div className="flex-1 min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={efficiencyChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                    <XAxis dataKey="metric" stroke="#64748b" tick={{ fontSize: 10 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }} />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />
                    <Bar dataKey="WareBot Utility AI" fill="#10b981" radius={[3, 3, 0, 0]} />
                    <Bar dataKey="Nearest-Order Baseline" fill="#f59e0b" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* ── Detailed Runs Table ────────────────────────────────────────── */}
          <div className="panel flex flex-col flex-1 min-h-0">
            <div className="panel-header border-b border-wh-border">
              <span className="panel-title">Per-Scenario Detailed Results ({job.detailed_runs?.length} runs)</span>
            </div>
            <div className="overflow-x-auto overflow-y-auto flex-1">
              <table className="w-full text-left text-xs">
                <thead className="bg-wh-card/60 text-[10px] text-wh-muted uppercase font-mono sticky top-0 border-b border-wh-border">
                  <tr>
                    <th className="p-2">Seed</th>
                    <th className="p-2">Strategy</th>
                    <th className="p-2">Completed</th>
                    <th className="p-2">Rate</th>
                    <th className="p-2">Avg Time</th>
                    <th className="p-2">Distance</th>
                    <th className="p-2">Energy</th>
                    <th className="p-2">Deadline %</th>
                    <th className="p-2">Replans</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-wh-border/40 font-mono text-[11px]">
                  {(job.detailed_runs || []).map((r, i) => (
                    <tr key={i} className={r.strategy.includes('Utility') ? 'bg-cyan-950/10' : ''}>
                      <td className="p-2 text-wh-muted">{r.seed}</td>
                      <td className="p-2 font-medium">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] border ${
                          r.strategy.includes('Utility')
                            ? 'bg-cyan-950 text-cyan-300 border-cyan-800'
                            : 'bg-gray-800 text-gray-400 border-gray-700'
                        }`}>
                          {r.strategy}
                        </span>
                      </td>
                      <td className="p-2 text-white">{r.completed_orders} / {r.total_orders}</td>
                      <td className="p-2 text-gray-300">{r.completion_rate_pct}%</td>
                      <td className="p-2 text-amber-300">{r.average_completion_time_ticks}t</td>
                      <td className="p-2 text-gray-300">{r.distance_travelled}</td>
                      <td className="p-2 text-purple-300">{r.energy_consumed}</td>
                      <td className="p-2 text-emerald-300">{r.deadline_success_rate_pct}%</td>
                      <td className="p-2 text-wh-muted">{r.route_replanning_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        /* Empty State */
        <div className="panel flex-1 flex flex-col items-center justify-center p-8 text-center text-wh-muted">
          <Trophy size={40} className="text-wh-border mb-3" />
          <div className="text-base font-semibold text-white mb-1">No Benchmark Results Yet</div>
          <p className="text-xs max-w-md mb-4 text-gray-400">
            Compare the multi-factor autonomous utility agent against a greedy nearest-order baseline across identical seeded warehouse layouts and orders.
          </p>
          <button
            onClick={handleRunBenchmark}
            disabled={loading}
            className="btn btn-primary px-4 py-2"
          >
            <Play size={14} /> Start 10-Seed Comparative Benchmark
          </button>
        </div>
      )}
    </div>
  );
}
