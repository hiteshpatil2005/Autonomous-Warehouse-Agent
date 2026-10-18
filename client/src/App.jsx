import { useState, useCallback } from 'react';
import { useSimulation } from './hooks/useSimulation';
import DashboardHeader from './components/layout/DashboardHeader';
import WarehouseGrid from './components/warehouse/WarehouseGrid';
import AgentSidebar from './components/dashboard/AgentSidebar';
import BenchmarkDashboard from './components/analytics/BenchmarkDashboard';

/**
 * App — Streamlined WareBot AI Simulation Dashboard.
 *
 * Designed with a clean, focused, simple user interface:
 * - Top header with primary simulation controls (Play, Resume, Pause, Stop/Reset, Step, + Add Obstacle)
 * - Maximized warehouse floor grid with large, prominent boxes
 * - Accurate obstacle placement directly on clicked boxes
 * - Clearly defined Starting Point [28, 1] and Current Goal beacon
 * - Dedicated Agent Mission & Real-Time Activity Log in the sidebar
 */
export default function App() {
  const [activeTab, setActiveTab] = useState('simulation');
  const [isObstacleMode, setIsObstacleMode] = useState(false);

  const sim = useSimulation();
  const { state } = sim;

  const toggleObstacleMode = useCallback(() => {
    setIsObstacleMode(prev => !prev);
  }, []);

  const handleCellClick = useCallback((row, col) => {
    sim.addObstacle(row, col);
  }, [sim]);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-wh-bg text-gray-200">
      {/* ── Top Header with Controls ─────────────────────────── */}
      <DashboardHeader
        simStatus={state.simStatus}
        tick={state.tick}
        speed={state.speed}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        connectionStatus={sim.connectionStatus}
        onNewSimulation={sim.newSimulation}
        onSetSpeed={sim.setSpeed}
        onRetry={sim.retryConnection}
        onStart={sim.start}
        onPause={sim.pause}
        onResume={sim.resume}
        onReset={sim.reset}
        onStep={sim.step}
        isObstacleMode={isObstacleMode}
        onToggleObstacleMode={toggleObstacleMode}
      />

      {/* ── Main View Container ──────────────────────────────── */}
      {activeTab === 'benchmark' ? (
        <BenchmarkDashboard />
      ) : (
        <main className="flex-1 flex gap-2.5 p-2.5 overflow-hidden min-h-0 bg-wh-bg">
          {/* Left: Maximized Warehouse Simulation Area */}
          <section className="flex-1 flex flex-col min-w-0 min-h-0 h-full">
            <WarehouseGrid
              state={state}
              onCellClick={handleCellClick}
              isObstacleMode={isObstacleMode}
            />
          </section>

          {/* Right: Focused Agent Status, Goal/Start & Activity Log Sidebar */}
          <AgentSidebar
            state={state}
            isObstacleMode={isObstacleMode}
            onToggleObstacleMode={toggleObstacleMode}
          />
        </main>
      )}
    </div>
  );
}
