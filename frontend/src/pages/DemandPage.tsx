import { useEffect, useState } from 'react'
import { Plus, Search, Filter, CheckCircle, XCircle, Send, Download, Trash2 } from 'lucide-react'
import { demandService, type DemandFilters } from '@/services/demandService'
import { productService } from '@/services/productService'
import { Card } from '@/components/common/Card'
import { Button } from '@/components/common/Button'
import { StatusBadge } from '@/components/common/StatusBadge'
import { Modal } from '@/components/common/Modal'
import { SkeletonTable } from '@/components/common/LoadingSpinner'
import { formatPeriod, formatNumber } from '@/utils/formatters'
import type { DemandPlan, CreateDemandPlanRequest, Product } from '@/types'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/store/authStore'
import { can } from '@/auth/permissions'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

const STATUSES = ['', 'draft', 'submitted', 'approved', 'rejected', 'locked']

export function DemandPage() {
  const { user } = useAuthStore()
  const canWrite = can(user?.role, 'demand.plan.write')
  const canApprove = can(user?.role, 'demand.plan.approve')

  const [plans, setPlans] = useState<DemandPlan[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState<DemandFilters>({ page: 1, page_size: 20 })
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [actionLoading, setActionLoading] = useState<number | null>(null)
  const [products, setProducts] = useState<Product[]>([])
  const [historyProductId, setHistoryProductId] = useState<number | undefined>(undefined)
  const [historyRangeMonths, setHistoryRangeMonths] = useState(24)
  const [historyPlans, setHistoryPlans] = useState<DemandPlan[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyOnlyActuals, setHistoryOnlyActuals] = useState(false)

  const [form, setForm] = useState<Partial<CreateDemandPlanRequest>>({
    forecast_qty: 0,
    region: 'Global',
    channel: 'Direct',
  })

  const load = async () => {
    setLoading(true)
    try {
      const res = await demandService.getPlans(filters)
      setPlans(res.items)
      setTotal(res.total)
    } catch {
      // handled
    } finally {
      setLoading(false)
    }
  }

  const loadProducts = async () => {
    try {
      // Backend enforces page_size <= 100. Pull all pages so selector is complete.
      const first = await productService.getProducts({ page: 1, page_size: 100 })
      let all = [...first.items]

      for (let page = 2; page <= first.total_pages; page += 1) {
        const next = await productService.getProducts({ page, page_size: 100 })
        all = all.concat(next.items)
      }

      // Keep active/new products first while still allowing historical discontinued products.
      all.sort((a, b) => {
        const rank = (status?: string) => (status === 'active' ? 0 : status === 'new' ? 1 : 2)
        return rank(a.status) - rank(b.status)
      })

      setProducts(all)
    } catch {
      // handled
    }
  }

  const loadHistory = async () => {
    if (!historyProductId) {
      setHistoryPlans([])
      return
    }

    setHistoryLoading(true)
    try {
      const now = new Date()
      const periodTo = new Date(now.getFullYear(), now.getMonth(), 1)
      const periodFrom = new Date(now.getFullYear(), now.getMonth() - (historyRangeMonths - 1), 1)

      const first = await demandService.getPlans({
        page: 1,
        page_size: 100,
        product_id: historyProductId,
        period_from: periodFrom.toISOString().slice(0, 10),
        period_to: periodTo.toISOString().slice(0, 10),
      })

      let all = [...first.items]
      for (let page = 2; page <= first.total_pages; page += 1) {
        const next = await demandService.getPlans({
          page,
          page_size: 100,
          product_id: historyProductId,
          period_from: periodFrom.toISOString().slice(0, 10),
          period_to: periodTo.toISOString().slice(0, 10),
        })
        all = all.concat(next.items)
      }

      const sorted = [...all].sort(
        (a, b) => new Date(a.period).getTime() - new Date(b.period).getTime(),
      )
      setHistoryPlans(sorted)
    } catch {
      // handled
    } finally {
      setHistoryLoading(false)
    }
  }

  useEffect(() => { load() }, [filters])
  useEffect(() => { loadProducts() }, [])
  useEffect(() => { loadHistory() }, [historyProductId, historyRangeMonths])

  const filteredHistoryPlans = historyOnlyActuals
    ? historyPlans.filter((p) => p.actual_qty != null)
    : historyPlans

  const historyChartData = filteredHistoryPlans.map((p) => ({
    period: formatPeriod(p.period),
    forecast_qty: p.forecast_qty,
    actual_qty: p.actual_qty ?? null,
    consensus_qty: p.consensus_qty ?? null,
  }))

  const exportHistoryCsv = () => {
    if (!filteredHistoryPlans.length) return

    const headers = ['period', 'forecast_qty', 'actual_qty', 'consensus_qty', 'region', 'channel', 'status']
    const escapeCsv = (value: string | number | null | undefined) => {
      if (value == null) return ''
      const str = String(value)
      return /[",\n]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str
    }

    const rows = filteredHistoryPlans.map((p) => [
      p.period,
      p.forecast_qty,
      p.actual_qty ?? '',
      p.consensus_qty ?? '',
      p.region,
      p.channel,
      p.status,
    ])

    const csvContent = [headers, ...rows]
      .map((row) => row.map((cell) => escapeCsv(cell)).join(','))
      .join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `demand_history_product_${historyProductId}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const handleAction = async (id: number, action: 'submit' | 'approve' | 'reject') => {
    setActionLoading(id)
    try {
      if (action === 'submit') await demandService.submitPlan(id)
      else if (action === 'approve') await demandService.approvePlan(id)
      else await demandService.rejectPlan(id)
      toast.success(`Plan ${action}ed successfully`)
      load()
    } catch {
      // handled
    } finally {
      setActionLoading(null)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this demand plan?')) return
    setActionLoading(id)
    try {
      await demandService.deletePlan(id)
      toast.success('Demand plan deleted')
      load()
    } catch {
      // handled
    } finally {
      setActionLoading(null)
    }
  }

  const handleCreate = async () => {
    if (!form.product_id || !form.period || !form.forecast_qty) {
      toast.error('Please fill in all required fields')
      return
    }
    try {
      await demandService.createPlan(form as CreateDemandPlanRequest)
      toast.success('Demand plan created')
      setShowCreate(false)
      setForm({ forecast_qty: 0, region: 'Global', channel: 'Direct' })
      load()
    } catch {
      // handled
    }
  }

  return (
    <div className="space-y-6 pt-2">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Demand Planning</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} plans total</p>
        </div>
        {canWrite && (
          <Button icon={<Plus />} onClick={() => setShowCreate(true)}>
            New Plan
          </Button>
        )}
      </div>

      {/* Filters */}
      <Card>
        <div className="space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[240px]">
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Historical View Product</label>
              <select
                value={historyProductId ?? ''}
                onChange={(e) => setHistoryProductId(e.target.value ? Number(e.target.value) : undefined)}
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select product...</option>
                {products.map((product) => (
                  <option key={product.id} value={product.id}>
                    #{product.id} — {product.sku} — {product.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Range</label>
              <select
                value={historyRangeMonths}
                onChange={(e) => setHistoryRangeMonths(Number(e.target.value))}
                className="text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={12}>Last 12 months</option>
                <option value={24}>Last 24 months</option>
                <option value={36}>Last 36 months</option>
              </select>
            </div>

            <label className="inline-flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={historyOnlyActuals}
                onChange={(e) => setHistoryOnlyActuals(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              Only periods with actuals
            </label>

            <Button
              variant="outline"
              size="sm"
              icon={<Download className="h-4 w-4" />}
              onClick={exportHistoryCsv}
              disabled={!filteredHistoryPlans.length}
            >
              Export CSV
            </Button>
          </div>

          {!historyProductId ? (
            <p className="text-sm text-gray-500">Select a product to view its historical demand trend.</p>
          ) : historyLoading ? (
            <SkeletonTable rows={6} cols={4} />
          ) : filteredHistoryPlans.length === 0 ? (
            <p className="text-sm text-gray-500">No historical data found for the selected product and range.</p>
          ) : (
            <>
              <p className="text-xs text-gray-500">Selected Product ID: <span className="font-medium text-gray-700">{historyProductId}</span></p>
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={historyChartData}
                    margin={{ top: 16, right: 24, left: 8, bottom: 12 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="period" minTickGap={16} tickMargin={8} />
                    <YAxis width={56} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="actual_qty" name="Actual Qty" stroke="#16a34a" strokeWidth={2} dot={false} connectNulls={false} />
                    <Line type="monotone" dataKey="forecast_qty" name="Forecast Qty" stroke="#2563eb" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="consensus_qty" name="Consensus Qty" stroke="#f59e0b" strokeWidth={2} dot={false} connectNulls={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="overflow-x-auto border border-gray-100 rounded-lg">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50">
                      {['Period', 'Forecast Qty', 'Actual Qty', 'Consensus Qty'].map((h) => (
                        <th key={h} className="text-left px-4 py-2.5 text-xs font-medium text-gray-500 uppercase tracking-wide">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {filteredHistoryPlans.map((plan) => (
                      <tr key={plan.id}>
                        <td className="px-4 py-2.5 text-gray-700">{formatPeriod(plan.period)}</td>
                        <td className="px-4 py-2.5 text-gray-900 tabular-nums">{formatNumber(plan.forecast_qty)}</td>
                        <td className="px-4 py-2.5 text-gray-900 tabular-nums">{plan.actual_qty != null ? formatNumber(plan.actual_qty) : '—'}</td>
                        <td className="px-4 py-2.5 text-gray-900 tabular-nums">{plan.consensus_qty != null ? formatNumber(plan.consensus_qty) : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </Card>

      <Card padding={false}>
        <div className="flex items-center gap-3 p-4">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search plans..."
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-400" />
            <select
              value={filters.status ?? ''}
              onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value || undefined, page: 1 }))}
              className="text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>{s ? s.charAt(0).toUpperCase() + s.slice(1) : 'All Statuses'}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Table */}
        {loading ? (
          <div className="p-4"><SkeletonTable rows={8} cols={8} /></div>
        ) : plans.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <p className="text-sm">No demand plans found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  {['Product', 'Period', 'Region', 'Forecast Qty', 'Actual Qty', 'Consensus Qty', 'Status', 'Actions'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {plans.map((plan) => (
                  <tr key={plan.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">
                      <p>{plan.product?.name ?? `Product #${plan.product_id}`}</p>
                      <p className="text-xs text-gray-400">ID: {plan.product_id}</p>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{formatPeriod(plan.period)}</td>
                    <td className="px-4 py-3 text-gray-600">{plan.region}</td>
                    <td className="px-4 py-3 text-gray-900 tabular-nums">{formatNumber(plan.forecast_qty)}</td>
                    <td className="px-4 py-3 text-gray-900 tabular-nums">
                      {plan.actual_qty != null ? formatNumber(plan.actual_qty) : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-900 tabular-nums">
                      {plan.consensus_qty != null ? formatNumber(plan.consensus_qty) : '—'}
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={plan.status} size="sm" /></td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        {canWrite && plan.status === 'draft' && (
                          <button
                            onClick={() => handleAction(plan.id, 'submit')}
                            disabled={actionLoading === plan.id}
                            className="p-1.5 rounded text-blue-600 hover:bg-blue-50 transition-colors"
                            title="Submit"
                          >
                            <Send className="h-3.5 w-3.5" />
                          </button>
                        )}
                        {canApprove && plan.status === 'submitted' && (
                          <>
                            <button
                              onClick={() => handleAction(plan.id, 'approve')}
                              disabled={actionLoading === plan.id}
                              className="p-1.5 rounded text-emerald-600 hover:bg-emerald-50 transition-colors"
                              title="Approve"
                            >
                              <CheckCircle className="h-3.5 w-3.5" />
                            </button>
                            <button
                              onClick={() => handleAction(plan.id, 'reject')}
                              disabled={actionLoading === plan.id}
                              className="p-1.5 rounded text-red-500 hover:bg-red-50 transition-colors"
                              title="Reject"
                            >
                              <XCircle className="h-3.5 w-3.5" />
                            </button>
                          </>
                        )}
                        {canWrite && plan.status !== 'approved' && plan.status !== 'locked' && (
                          <button
                            onClick={() => handleDelete(plan.id)}
                            disabled={actionLoading === plan.id}
                            className="p-1.5 rounded text-gray-500 hover:text-red-600 hover:bg-red-50 transition-colors"
                            title="Delete"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {total > (filters.page_size ?? 20) && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
            <p className="text-xs text-gray-500">
              Showing {((filters.page ?? 1) - 1) * (filters.page_size ?? 20) + 1}–{Math.min((filters.page ?? 1) * (filters.page_size ?? 20), total)} of {total}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline" size="sm"
                disabled={(filters.page ?? 1) <= 1}
                onClick={() => setFilters((f) => ({ ...f, page: (f.page ?? 1) - 1 }))}
              >
                Previous
              </Button>
              <Button
                variant="outline" size="sm"
                disabled={(filters.page ?? 1) * (filters.page_size ?? 20) >= total}
                onClick={() => setFilters((f) => ({ ...f, page: (f.page ?? 1) + 1 }))}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Create Modal */}
      <Modal
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        title="Create Demand Plan"
        footer={
          <>
            <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={!canWrite}>Create Plan</Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Product ID *</label>
            <input
              type="number"
              value={form.product_id ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, product_id: Number(e.target.value) }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter product ID"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Period *</label>
            <input
              type="month"
              value={form.period ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, period: e.target.value + '-01' }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Region</label>
              <input
                value={form.region ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, region: e.target.value }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Channel</label>
              <input
                value={form.channel ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, channel: e.target.value }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Forecast Quantity *</label>
            <input
              type="number"
              value={form.forecast_qty ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, forecast_qty: Number(e.target.value) }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Notes</label>
            <textarea
              value={form.notes ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              rows={3}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>
        </div>
      </Modal>
    </div>
  )
}
