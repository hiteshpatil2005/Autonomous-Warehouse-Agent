const LEGEND_ITEMS = [
  { type: 'start',          bg: '#064e3b', border: '#10b981', label: 'Start Point [28, 1]', icon: '🏁' },
  { type: 'goal',           bg: '#78350f', border: '#f59e0b', label: 'Current Goal',        icon: '🎯' },
  { type: 'robot',          bg: '#0891b2', border: '#22d3ee', label: 'Robot AGV',           icon: '🤖' },
  { type: 'obstacle',       bg: '#7f1d1d', border: '#ef4444', label: 'Obstacle (Click)',   icon: '✕' },
  { type: 'path_planned',   bg: '#1e3a8a', border: '#3b82f6', label: 'A* Path Route',       icon: '•' },
  { type: 'shelf',          bg: '#1e1b4b', border: '#3730a3', label: 'Inventory Shelf',     icon: null },
  { type: 'packing',        bg: '#78350f', border: '#d97706', label: 'Packing [28, 14]',    icon: '📦' },
  { type: 'charging',       bg: '#14532d', border: '#22c55e', label: 'Charging [28, 27]',   icon: '⚡' },
];

export default function GridLegend({ hoveredCell }) {
  return (
    <div className="flex flex-col gap-1.5">
      {/* Cell type legend */}
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          {LEGEND_ITEMS.map(item => (
            <div key={item.type} className="flex items-center gap-1.5">
              <div
                className="w-3.5 h-3.5 rounded-sm border flex items-center justify-center text-[8px] font-bold shrink-0"
                style={{ background: item.bg, borderColor: item.border }}
              >
                {item.icon}
              </div>
              <span className="text-[10px] text-wh-muted">{item.label}</span>
            </div>
          ))}
        </div>

        {/* Hovered cell info */}
        {hoveredCell?.row != null && (
          <div className="text-[10px] text-cyan-300 font-mono bg-wh-card/80 px-2 py-0.5 rounded border border-wh-border/50">
            Selected Box: [{hoveredCell.row}, {hoveredCell.col}]
            {hoveredCell.type ? ` · ${hoveredCell.type}` : ''}
            {hoveredCell.shelfId ? ` · Shelf ${hoveredCell.shelfId}` : ''}
          </div>
        )}
      </div>
    </div>
  );
}
