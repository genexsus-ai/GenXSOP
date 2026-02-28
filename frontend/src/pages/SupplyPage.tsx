import { useEffect, useState } from 'react'
import { Plus, Search, Filter, CheckCircle, XCircle, Send } from 'lucide-react'
import { supplyService, type SupplyFilters } from '@/services/supplyService'
import { productService } from '@/services/productService'
import { Card } from '@/components/common/Card'
import { Button } from '@/components/common/Button'
import { StatusBadge } from '@/components/common/StatusBadge'
import { Modal } from '@/components/common/Modal'
import { SkeletonTable } from '@/components/common/LoadingSpinner'
import { formatPeriod, formatNumber } from '@/utils/formatters'
import type { SupplyPlan, CreateSupplyPlanRequest, Product, SupplyGapAnalysisItem } from '@/types'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/store/authStore'
import { can } from '@/auth/permissions'

const STATUSES = ['', 'draft', 'submitted', 'approved', 'rejected', 'locked']

export function SupplyPage() {
  const { user } = useAuthStore()
  const canWrite = can(user?.role, 'supply.plan.write')
  const canApprove = can(user?.role, 'supply.plan.approve')

  const [plans, setPlans] = useState<SupplyPlan[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState<SupplyFilters>({ page: 1, page_size: 20 })
  const [showCreate, setShowCreate] = useState(false)
  const [actionLoading, setActionLoading] = useState<number | null>(null)
  const [products, setProducts] = useState<Product[]>([])
  const [gapAnalysis, setGapAnalysis] = useState<SupplyGapAnalysisItem[]>([])
  const [gapLoading, setGapLoading] = useState(false)
  const [gapProductId, setGapProductId] = useState<number | undefined>(undefined)
  const [gapPeriod, setGapPeriod] = useState<string>('')
  const [gapActionContext, setGapActionContext] = useState<{
    existingPlanId?: number
    recommendedIncreaseQty: number
  } | null>(null)
  const [form, setForm] = useState<Partial<CreateSupplyPlanRequest>>({ location: 'Main Warehouse' })

  const load = async () => {
    setLoading(true)
    try {
      const res = await supplyService.getPlans(filters)
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
      const first = await productService.getProducts({ page: 1, page_size: 100 })
      let all = [...first.items]
      for (let page = 2; page <= first.total_pages; page += 1) {
        const next = await productService.getProducts({ page, page_size: 100 })
        all = all.concat(next.items)
      }
      setProducts(all)
    } catch {
      // handled
    }
  }

  const loadGapAnalysis = async () => {
    setGapLoading(true)
    try {
      const period = gapPeriod ? `${gapPeriod}-01` : undefined
      const data = await supplyService.getGapAnalysis({
        period,
        product_id: gapProductId,
      })
      setGapAnalysis(data)
    } catch {
      // handled
      setGapAnalysis([])
    } finally {
      setGapLoading(false)
    }
  }

  useEffect(() => { load() }, [filters])
  useEffect(() => { loadProducts() }, [])
  useEffect(() => {
    if (!gapPeriod && plans.length > 0) {
      setGapPeriod(plans[0].period.slice(0, 7))
    }
  }, [plans, gapPeriod])
  useEffect(() => { loadGapAnalysis() }, [gapProductId, gapPeriod])

  const handleAction = async (id: number, action: 'submit' | 'approve' | 'reject') => {
    setActionLoading(id)
    try {
      if (action === 'submit') await supplyService.submitPlan(id)
      else if (action === 'approve') await supplyService.approvePlan(id)
      else await supplyService.rejectPlan(id)
      toast.success(`Plan ${action}ed successfully`)
      load()
    } catch {
      // handled
    } finally {
      setActionLoading(null)
    }
  }

  const handleCreate = async () => {
    if (!form.product_id || !form.period) {
      toast.error('Please fill in all required fields')
      return
    }
    try {
      if (gapActionContext?.existingPlanId) {
        await supplyService.updatePlan(gapActionContext.existingPlanId, form)
        toast.success('Supply plan updated to close gap')
      } else {
        await supplyService.createPlan(form as CreateSupplyPlanRequest)
        toast.success('Supply plan created')
      }
      setShowCreate(false)
      setGapActionContext(null)
      setForm({ location: 'Main Warehouse' })
      load()
      loadGapAnalysis()
    } catch {
      // handled
    }
  }

  const closeModal = () => {
    setShowCreate(false)
    setGapActionContext(null)
  }

  const handleCloseGap = (item: SupplyGapAnalysisItem) => {
    const normalizedPeriod = item.period.slice(0, 10)
    const existingPlan = plans.find(
      (plan) => plan.product_id === item.product_id && plan.period.slice(0, 10) === normalizedPeriod,
    )

    const currentPlanned = Number(existingPlan?.planned_prod_qty ?? item.planned_supply_qty ?? 0)
    const requiredIncrease = item.gap < 0 ? Math.abs(Number(item.gap)) : 0
    const targetPlanned = currentPlanned + requiredIncrease

    setForm({
      product_id: item.product_id,
      period: normalizedPeriod,
      location: existingPlan?.location ?? 'Main Warehouse',
      supplier_name: existingPlan?.supplier_name,
      capacity_max: existingPlan?.capacity_max,
      planned_prod_qty: Number(targetPlanned.toFixed(2)),
    })
    setGapActionContext({
      existingPlanId: existingPlan?.id,
      recommendedIncreaseQty: Number(requiredIncrease.toFixed(2)),
    })
    setShowCreate(true)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Supply Planning</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} plans total</p>
        </div>
        {canWrite && (
          <Button
            icon={<Plus />}
            onClick={() => {
              setGapActionContext(null)
              setShowCreate(true)
            }}
          >
            New Plan
          </Button>
        )}
      </div>

      <Card padding={false}>
        <div className="flex items-center gap-3 p-4">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
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

        {loading ? (
          <div className="p-4"><SkeletonTable rows={8} cols={7} /></div>
        ) : plans.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <p className="text-sm">No supply plans found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  {['Product', 'Period', 'Location', 'Planned Qty', 'Capacity Max', 'Supplier', 'Status', 'Actions'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {plans.map((plan) => (
                  <tr key={plan.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {plan.product?.name ?? `Product #${plan.product_id}`}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{formatPeriod(plan.period)}</td>
                    <td className="px-4 py-3 text-gray-600">{plan.location}</td>
                    <td className="px-4 py-3 tabular-nums">{plan.planned_prod_qty != null ? formatNumber(plan.planned_prod_qty) : '—'}</td>
                    <td className="px-4 py-3 tabular-nums">{plan.capacity_max != null ? formatNumber(plan.capacity_max) : '—'}</td>
                    <td className="px-4 py-3 text-gray-600">{plan.supplier_name ?? '—'}</td>
                    <td className="px-4 py-3"><StatusBadge status={plan.status} size="sm" /></td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        {canWrite && plan.status === 'draft' && (
                          <button onClick={() => handleAction(plan.id, 'submit')} disabled={actionLoading === plan.id}
                            className="p-1.5 rounded text-blue-600 hover:bg-blue-50 transition-colors" title="Submit">
                            <Send className="h-3.5 w-3.5" />
                          </button>
                        )}
                        {canApprove && plan.status === 'submitted' && (
                          <>
                            <button onClick={() => handleAction(plan.id, 'approve')} disabled={actionLoading === plan.id}
                              className="p-1.5 rounded text-emerald-600 hover:bg-emerald-50 transition-colors" title="Approve">
                              <CheckCircle className="h-3.5 w-3.5" />
                            </button>
                            <button onClick={() => handleAction(plan.id, 'reject')} disabled={actionLoading === plan.id}
                              className="p-1.5 rounded text-red-500 hover:bg-red-50 transition-colors" title="Reject">
                              <XCircle className="h-3.5 w-3.5" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {total > (filters.page_size ?? 20) && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
            <p className="text-xs text-gray-500">
              Showing {((filters.page ?? 1) - 1) * (filters.page_size ?? 20) + 1}–{Math.min((filters.page ?? 1) * (filters.page_size ?? 20), total)} of {total}
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={(filters.page ?? 1) <= 1}
                onClick={() => setFilters((f) => ({ ...f, page: (f.page ?? 1) - 1 }))}>Previous</Button>
              <Button variant="outline" size="sm" disabled={(filters.page ?? 1) * (filters.page_size ?? 20) >= total}
                onClick={() => setFilters((f) => ({ ...f, page: (f.page ?? 1) + 1 }))}>Next</Button>
            </div>
          </div>
        )}
      </Card>

      <Card
        title="Supply Gap Analysis"
        subtitle="Planned supply + available inventory against demand"
        actions={
          <div className="flex items-end gap-2">
            <div>
              <label className="block text-[11px] font-medium text-gray-600 mb-1">Period</label>
              <input
                type="month"
                value={gapPeriod}
                onChange={(e) => setGapPeriod(e.target.value)}
                className="px-2.5 py-1.5 text-xs border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-gray-600 mb-1">Product</label>
              <select
                value={gapProductId ?? ''}
                onChange={(e) => setGapProductId(e.target.value ? Number(e.target.value) : undefined)}
                className="px-2.5 py-1.5 text-xs border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 max-w-[260px]"
              >
                <option value="">All Products</option>
                {products.map((product) => (
                  <option key={product.id} value={product.id}>
                    #{product.id} — {product.sku} — {product.name}
                  </option>
                ))}
              </select>
            </div>
            <Button variant="outline" size="sm" onClick={loadGapAnalysis}>
              Refresh
            </Button>
          </div>
        }
      >
        {gapLoading ? (
          <SkeletonTable rows={6} cols={10} />
        ) : gapAnalysis.length === 0 ? (
          <div className="space-y-1">
            <p className="text-sm text-gray-500">No gap analysis data found for the selected filters.</p>
            <p className="text-xs text-gray-400">
              This usually means there are no demand plans for
              {gapPeriod ? ` ${gapPeriod}-01` : ' the selected period'}.
              Try Period: <span className="font-medium">2026-01</span>, Product: <span className="font-medium">All Products</span>, then click Refresh.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto border border-gray-100 rounded-lg">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  {[
                    'Product',
                    'Period',
                    'Demand',
                    'Planned Supply',
                    'Inventory Available',
                    'Effective Supply',
                    'Additional Prod Required',
                    'Gap',
                    'Gap %',
                    'Status',
                    'Action',
                  ].map((h) => (
                    <th key={h} className="text-left px-4 py-2.5 text-xs font-medium text-gray-500 uppercase tracking-wide">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {gapAnalysis.map((item) => (
                  <tr key={`${item.product_id}-${item.period}`}>
                    <td className="px-4 py-2.5 text-gray-800">
                      <p className="font-medium">{item.product_name}</p>
                      <p className="text-xs text-gray-500">{item.sku}</p>
                    </td>
                    <td className="px-4 py-2.5 text-gray-700">{formatPeriod(item.period)}</td>
                    <td className="px-4 py-2.5 tabular-nums">{formatNumber(item.demand_qty)}</td>
                    <td className="px-4 py-2.5 tabular-nums">{formatNumber(item.planned_supply_qty)}</td>
                    <td className="px-4 py-2.5 tabular-nums">{formatNumber(item.inventory_available_qty)}</td>
                    <td className="px-4 py-2.5 tabular-nums font-medium text-gray-900">{formatNumber(item.effective_supply_qty)}</td>
                    <td className="px-4 py-2.5 tabular-nums">{formatNumber(item.additional_prod_required_qty)}</td>
                    <td className={`px-4 py-2.5 tabular-nums font-medium ${item.gap < 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                      {formatNumber(item.gap)}
                    </td>
                    <td className={`px-4 py-2.5 tabular-nums ${item.gap_pct < 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                      {item.gap_pct.toFixed(1)}%
                    </td>
                    <td className="px-4 py-2.5"><StatusBadge status={item.status} size="sm" /></td>
                    <td className="px-4 py-2.5">
                      {canWrite ? (
                        <Button variant="outline" size="sm" onClick={() => handleCloseGap(item)}>
                          {item.gap < 0
                            ? (plans.some((plan) => plan.product_id === item.product_id && plan.period.slice(0, 10) === item.period.slice(0, 10))
                              ? 'Adjust Plan'
                              : 'Close Gap')
                            : 'Adjust Plan'}
                        </Button>
                      ) : (
                        <span className="text-xs text-gray-400">No edit permission</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal
        isOpen={showCreate}
        onClose={closeModal}
        title={gapActionContext ? 'Close Gap — Supply Plan Adjustment' : 'Create Supply Plan'}
        footer={
          <>
            <Button variant="outline" onClick={closeModal}>Cancel</Button>
            <Button onClick={handleCreate} disabled={!canWrite}>
              {gapActionContext?.existingPlanId ? 'Update Plan' : 'Create Plan'}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {gapActionContext && (
            <div className="rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-700">
              Recommended planned production increase: <span className="font-semibold">{formatNumber(gapActionContext.recommendedIncreaseQty)}</span>
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Product ID *</label>
            <input type="number" value={form.product_id ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, product_id: Number(e.target.value) }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter product ID" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Period *</label>
            <input type="month" value={form.period?.slice(0, 7) ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, period: e.target.value + '-01' }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Location</label>
              <input value={form.location ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, location: e.target.value }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Supplier</label>
              <input value={form.supplier_name ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, supplier_name: e.target.value }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Planned Qty</label>
              <input type="number" value={form.planned_prod_qty ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, planned_prod_qty: Number(e.target.value) }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Capacity Max</label>
              <input type="number" value={form.capacity_max ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, capacity_max: Number(e.target.value) }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
        </div>
      </Modal>
    </div>
  )
}
