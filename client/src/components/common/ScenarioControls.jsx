import { AlertTriangle, Plus, RefreshCw, Bot } from 'lucide-react';

export default function ScenarioControls({ addObstacle, addUrgentOrder, replenishStock, newSimulation }) {
  return (
    <div className="panel flex items-center gap-2 px-3 py-2 shrink-0">
      <span className="panel-title mr-1">Scenarios</span>

      <button
        id="btn-add-obstacle"
        className="btn btn-danger"
        onClick={addObstacle}
        aria-label="Add a random obstacle to the warehouse floor"
        title="Place a random obstacle on a walkable floor cell"
      >
        <AlertTriangle size={13} />
        Add Obstacle
      </button>

      <button
        id="btn-add-urgent"
        className="btn btn-warning"
        onClick={addUrgentOrder}
        aria-label="Inject an urgent order"
        title="Add a new URGENT priority order to the queue"
      >
        <Plus size={13} />
        Urgent Order
      </button>

      <button
        id="btn-replenish"
        className="btn btn-ghost"
        onClick={replenishStock}
        aria-label="Replenish stock on a random shelf"
        title="Restock a random shelf with +10 units"
      >
        <RefreshCw size={13} />
        Replenish Stock
      </button>

      <button
        id="btn-new-sim"
        className="btn btn-ghost ml-auto"
        onClick={newSimulation}
        aria-label="Generate a new random simulation"
        title="Generate a new randomized warehouse map and order set"
      >
        <Bot size={13} />
        New Simulation
      </button>
    </div>
  );
}
