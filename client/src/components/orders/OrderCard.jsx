import { memo } from 'react';

const PRIORITY_STYLE = {
  URGENT: { badge: 'bg-red-900 text-red-300 border-red-700',   dot: 'bg-red-400'    },
  HIGH:   { badge: 'bg-amber-900 text-amber-300 border-amber-700', dot: 'bg-amber-400' },
  MEDIUM: { badge: 'bg-blue-900 text-blue-300 border-blue-700', dot: 'bg-blue-400'   },
  LOW:    { badge: 'bg-gray-800 text-gray-400 border-gray-700', dot: 'bg-gray-500'   },
};

const STATUS_STYLE = {
  pending:   'text-gray-400',
  assigned:  'text-cyan-400',
  picking:   'text-amber-400',
  returning: 'text-indigo-400',
  packing:   'text-amber-300',
  completed: 'text-green-400',
};

const STATUS_LABEL = {
  pending:   '● Pending',
  assigned:  '◉ Assigned',
  picking:   '⟳ Picking',
  returning: '⟳ Returning',
  packing:   '⟳ Packing',
  completed: '✓ Completed',
};

const OrderCard = memo(function OrderCard({ order, isActive }) {
  const ps = PRIORITY_STYLE[order.priority] || PRIORITY_STYLE.LOW;
  const ss = STATUS_STYLE[order.status]     || STATUS_STYLE.pending;

  return (
    <div
      className={`rounded-md border p-2.5 transition-all ${
        isActive
          ? 'border-cyan-700 bg-cyan-950/30'
          : order.status === 'completed'
          ? 'border-wh-border bg-wh-card/40 opacity-60'
          : 'border-wh-border bg-wh-card'
      }`}
    >
      {/* Top row */}
      <div className="flex items-center gap-2 mb-1.5">
        <span className="font-mono text-[10px] text-wh-muted">{order.id}</span>
        <span className={`badge border text-[9px] ${ps.badge}`}>{order.priority}</span>
        {isActive && (
          <span className="badge border border-cyan-700 bg-cyan-950 text-cyan-300 text-[9px]">ACTIVE</span>
        )}
        <span className="ml-auto font-mono text-[10px]">
          <span className={ss}>{STATUS_LABEL[order.status] || order.status}</span>
        </span>
      </div>

      {/* Product info */}
      <div className="flex items-baseline gap-2">
        <span className="text-xs text-gray-200 font-medium truncate flex-1">{order.product}</span>
        <span className="text-[10px] text-wh-muted shrink-0">×{order.quantity}</span>
      </div>

      {/* Bottom row */}
      <div className="flex items-center gap-3 mt-1.5 text-[10px] text-wh-muted">
        <span>Shelf <span className="font-mono text-gray-300">{order.targetShelfId}</span></span>
        {order.deadline && (
          <span className="text-amber-500">⏱ {order.deadline}</span>
        )}
        {order.completedAt && (
          <span className="text-green-500 ml-auto">✓ {order.completedAt}</span>
        )}
      </div>
    </div>
  );
});

export default OrderCard;
