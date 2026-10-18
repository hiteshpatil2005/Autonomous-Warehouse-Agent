import { useState } from 'react';
import { ShoppingCart, Plus } from 'lucide-react';
import OrderCard from './OrderCard';

const FILTERS = ['All', 'Pending', 'Active', 'Completed'];

const STATUS_MAP = {
  All:       null,
  Pending:   ['pending'],
  Active:    ['assigned', 'picking', 'returning', 'packing'],
  Completed: ['completed'],
};

export default function OrderQueue({ orders, currentOrder, onAddUrgent }) {
  const [filter, setFilter] = useState('All');

  const allowed = STATUS_MAP[filter];
  const visible = allowed
    ? orders.filter(o => allowed.includes(o.status))
    : orders;

  const counts = {
    pending:   orders.filter(o => o.status === 'pending').length,
    active:    orders.filter(o => ['assigned','picking','returning','packing'].includes(o.status)).length,
    completed: orders.filter(o => o.status === 'completed').length,
  };

  return (
    <div className="panel flex flex-col min-h-0">
      {/* Header */}
      <div className="panel-header">
        <ShoppingCart size={13} className="text-amber-400" />
        <span className="panel-title">Order Queue</span>
        <span className="ml-2 badge border border-amber-800 bg-amber-950 text-amber-300 text-[9px]">
          {counts.pending} pending
        </span>
        <button
          className="btn btn-warning ml-auto"
          onClick={onAddUrgent}
          aria-label="Add urgent order"
          title="Inject an urgent order into the queue"
        >
          <Plus size={12} />
          Urgent
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 px-2 pt-2 border-b border-wh-border pb-2">
        {FILTERS.map(f => (
          <button
            key={f}
            className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
              filter === f
                ? 'bg-wh-border text-white'
                : 'text-wh-muted hover:text-gray-300'
            }`}
            onClick={() => setFilter(f)}
          >
            {f}
            {f === 'Pending'   && counts.pending   > 0 && <span className="ml-1 text-amber-400">{counts.pending}</span>}
            {f === 'Active'    && counts.active    > 0 && <span className="ml-1 text-cyan-400">{counts.active}</span>}
            {f === 'Completed' && counts.completed > 0 && <span className="ml-1 text-green-400">{counts.completed}</span>}
          </button>
        ))}
      </div>

      {/* Order list */}
      <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-1.5">
        {visible.length === 0 ? (
          <div className="flex items-center justify-center h-20 text-wh-muted text-xs">
            No orders in this category
          </div>
        ) : (
          visible.map(order => (
            <OrderCard
              key={order.id}
              order={order}
              isActive={currentOrder?.id === order.id}
            />
          ))
        )}
      </div>

      {/* Footer counts */}
      <div className="px-3 py-1.5 border-t border-wh-border flex gap-4 text-[10px] text-wh-muted">
        <span>Total: <b className="text-gray-300">{orders.length}</b></span>
        <span>Active: <b className="text-cyan-400">{counts.active}</b></span>
        <span>Done: <b className="text-green-400">{counts.completed}</b></span>
      </div>
    </div>
  );
}
