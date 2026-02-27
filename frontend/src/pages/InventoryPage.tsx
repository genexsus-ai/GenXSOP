import { useEffect, useState } from 'react'
import { Search, Filter, AlertTriangle, Package } from 'lucide-react'
import { inventoryService } from '@/services/inventoryService'
import { Card } from '@/components/common/Card'
import { StatusBadge } from '@/components/common/StatusBadge'
import { KPICard } from '@/components/common/KPICard'
import { SkeletonTable } from '@/components/common/LoadingSpinner'
import { formatNumber, formatCurrency } from '@/utils/formatters'
import type { Inventory } from '@/types'

const STATUSES = ['', 'normal', 'low', 'critical', 'excess']

export function InventoryPage() {
  const [items, setItems] = useState<Inventory[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const pageSize = 20

  const load = async () => {
    setLoading(true)
    try {
      const res = await inventoryService.getInventory({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
      })
      setItems(res.items)
      setTotal(res.total)
    } catch {
      // handled
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [page, statusFilter])

  const criticalCount = items.filter((i) => i.status === 'critical').length
  const lowCount = items.filter((i) => i.status === 'low').length
  const excessCount = items.filter((i) => i.status === 'excess').length
  const totalValue = items.reduce((sum, i) => sum + (i.valuation ?? 0), 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Inventory Management</h1>
        <p className="text-sm text-gray-500 mt-0.5">{total} SKUs tracked</p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard title="Total Value" value={formatCurrency(totalValue)} icon={<Package className="h-4 w-4" />} color="blue" />
        <KPICard title="Critical Stock" value={criticalCount} icon={<AlertTriangle className="h-4 w-4" />} color="red"
          subtitle="Immediate action needed" />
        <KPICard title="Low Stock" value={lowCount} icon={<AlertTriangle className="h-4 w-4" />} color="amber"
          subtitle="Below reorder point" />
        <KPICard title="Excess Stock" value={excessCount} icon={<Package className="h-4 w-4" />} color="purple"
          subtitle="Above max stock level" />
      </div>

      <Card padding={false}>
        <div className="flex items-center gap-3 p-4">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              placeholder="Search inventory..."
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
              className="text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>{s ? s.charAt(0).toUpperCase() + s.slice(1) : 'All Statuses'}</option>
              ))}
            </select>
          </div>
        </div>

        {loading ? (
          <div className="p-4"><SkeletonTable rows={8} cols={8} /></div>
        ) : items.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <Package className="h-10 w-10 mx-auto mb-3 opacity-40" />
            <p className="text-sm">No inventory records found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  {['Product', 'Location', 'On Hand', 'Allocated', 'In Transit', 'Safety Stock', 'Days of Supply', 'Status'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {item.product?.name ?? `Product #${item.product_id}`}
                      {item.product?.sku && (
                        <span className="block text-xs text-gray-400">{item.product.sku}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{item.location}</td>
                    <td className="px-4 py-3 tabular-nums font-medium">{formatNumber(item.on_hand_qty)}</td>
                    <td className="px-4 py-3 tabular-nums text-gray-600">{formatNumber(item.allocated_qty)}</td>
                    <td className="px-4 py-3 tabular-nums text-gray-600">{formatNumber(item.in_transit_qty)}</td>
                    <td className="px-4 py-3 tabular-nums text-gray-600">{formatNumber(item.safety_stock)}</td>
                    <td className="px-4 py-3 tabular-nums">
                      {(() => {
                        // Defensive: backend decimals may arrive as strings; avoid crashing the page.
                        const raw: any = (item as any).days_of_supply
                        const n = typeof raw === 'number' ? raw : typeof raw === 'string' ? Number(raw) : undefined

                        if (n === undefined || Number.isNaN(n)) return '—'

                        return (
                          <span className={n < 7 ? 'text-red-600 font-medium' : n < 14 ? 'text-amber-600' : 'text-gray-900'}>
                            {n.toFixed(0)}d
                          </span>
                        )
                      })()}
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={item.status} size="sm" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {total > pageSize && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
            <p className="text-xs text-gray-500">
              Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total}
            </p>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="px-3 py-1.5 text-xs border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50"
              >
                Previous
              </button>
              <button
                disabled={page * pageSize >= total}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1.5 text-xs border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
