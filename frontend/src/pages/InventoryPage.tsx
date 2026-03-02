import { useEffect, useState } from 'react'
import { Search, Filter, AlertTriangle, Package, Sparkles, ShieldAlert, Bot, Download, RotateCcw } from 'lucide-react'
import { inventoryService } from '@/services/inventoryService'
import { Card } from '@/components/common/Card'
import { StatusBadge } from '@/components/common/StatusBadge'
import { KPICard } from '@/components/common/KPICard'
import { SkeletonTable } from '@/components/common/LoadingSpinner'
import { Button } from '@/components/common/Button'
import { Modal } from '@/components/common/Modal'
import { formatNumber, formatCurrency } from '@/utils/formatters'
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  CartesianGrid,
  XAxis,
  YAxis,
  BarChart,
  ComposedChart,
  Bar,
  Line,
} from 'recharts'
import type {
  Inventory,
  InventoryException,
  InventoryPolicyRecommendation,
  InventoryRebalanceRecommendation,
  InventoryControlTowerSummary,
  InventoryDataQuality,
  InventoryEscalationItem,
  InventoryWorkingCapitalSummary,
  InventoryHealthSummary,
  InventoryAssessmentScorecard,
  InventoryServiceLevelAnalyticsResponse,
  InventoryServiceLevelMethod,
} from '@/types'
import { useAuthStore } from '@/store/authStore'
import { can } from '@/auth/permissions'
import toast from 'react-hot-toast'

const STATUSES = ['', 'normal', 'low', 'critical', 'excess']

export function InventoryPage() {
  const { user } = useAuthStore()
  const canUpdate = can(user?.role, 'inventory.update')

  const [items, setItems] = useState<Inventory[]>([])
  const [exceptions, setExceptions] = useState<InventoryException[]>([])
  const [recommendations, setRecommendations] = useState<InventoryPolicyRecommendation[]>([])
  const [rebalance, setRebalance] = useState<InventoryRebalanceRecommendation[]>([])
  const [controlTower, setControlTower] = useState<InventoryControlTowerSummary | null>(null)
  const [dataQuality, setDataQuality] = useState<InventoryDataQuality[]>([])
  const [escalations, setEscalations] = useState<InventoryEscalationItem[]>([])
  const [workingCapital, setWorkingCapital] = useState<InventoryWorkingCapitalSummary | null>(null)
  const [healthSummary, setHealthSummary] = useState<InventoryHealthSummary | null>(null)
  const [assessment, setAssessment] = useState<InventoryAssessmentScorecard | null>(null)
  const [serviceLevelAnalytics, setServiceLevelAnalytics] = useState<InventoryServiceLevelAnalyticsResponse | null>(null)
  const [serviceLevelMethod, setServiceLevelMethod] = useState<InventoryServiceLevelMethod>('analytical')
  const [targetServiceLevel, setTargetServiceLevel] = useState(0.95)
  const [serviceLevelLoading, setServiceLevelLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [optimizationLoading, setOptimizationLoading] = useState(false)
  const [recommendationLoading, setRecommendationLoading] = useState(false)
  const [autoApplyLoading, setAutoApplyLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')
  const [qualityTierFilter, setQualityTierFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all')
  const [recommendationStatusFilter, setRecommendationStatusFilter] = useState('pending')
  const [showOverride, setShowOverride] = useState(false)
  const [selectedInventory, setSelectedInventory] = useState<Inventory | null>(null)
  const [overrideForm, setOverrideForm] = useState({
    safety_stock: '',
    reorder_point: '',
    max_stock: '',
    reason: '',
  })
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
      const ex = await inventoryService.getExceptions()
      setExceptions(ex)
      const rec = await inventoryService.getRecommendations({ status: recommendationStatusFilter || undefined })
      setRecommendations(rec)
      const rb = await inventoryService.getRebalanceRecommendations({ min_transfer_qty: 1 })
      setRebalance(rb)
      const tower = await inventoryService.getControlTowerSummary()
      setControlTower(tower)
      const quality = await inventoryService.getDataQuality()
      setDataQuality(quality)
      const esc = await inventoryService.getEscalations()
      setEscalations(esc)
      const wc = await inventoryService.getWorkingCapitalSummary()
      setWorkingCapital(wc)
      const health = await inventoryService.getHealthSummary()
      setHealthSummary(health)
      const asmt = await inventoryService.getAssessmentScorecard()
      setAssessment(asmt)

      if (res.items.length > 0) {
        await loadServiceLevelAnalytics(res.items[0].id)
      } else {
        setServiceLevelAnalytics(null)
      }
    } catch {
      // handled
    } finally {
      setLoading(false)
    }
  }

  const loadServiceLevelAnalytics = async (inventoryId: number) => {
    setServiceLevelLoading(true)
    try {
      const data = await inventoryService.getServiceLevelAnalytics({
        inventory_id: inventoryId,
        target_service_level: targetServiceLevel,
        method: serviceLevelMethod,
        simulation_runs: serviceLevelMethod === 'monte_carlo' ? 2000 : undefined,
        bucket_count: 20,
      })
      setServiceLevelAnalytics(data)
    } finally {
      setServiceLevelLoading(false)
    }
  }

  const generateRecommendations = async () => {
    setRecommendationLoading(true)
    try {
      const generated = await inventoryService.generateRecommendations({
        min_confidence: 0.6,
        max_items: 100,
      })
      toast.success(`Generated ${generated.length} AI recommendations`)
      await load()
    } catch {
      // handled globally
    } finally {
      setRecommendationLoading(false)
    }
  }

  useEffect(() => { load() }, [page, statusFilter, recommendationStatusFilter])

  const runOptimization = async () => {
    setOptimizationLoading(true)
    try {
      const result = await inventoryService.runOptimization({
        service_level_target: 0.95,
        lead_time_days: 14,
        review_period_days: 7,
        moq_units: 10,
        lot_size_units: 5,
        capacity_max_units: 1500,
        lead_time_variability_days: 2,
      })
      toast.success(`Optimization completed. Updated ${result.updated_count} records`)
      await load()
    } catch {
      // handled globally
    } finally {
      setOptimizationLoading(false)
    }
  }

  const openOverride = (item: Inventory) => {
    setSelectedInventory(item)
    setOverrideForm({
      safety_stock: String(item.safety_stock ?? ''),
      reorder_point: String(item.reorder_point ?? ''),
      max_stock: item.max_stock != null ? String(item.max_stock) : '',
      reason: '',
    })
    setShowOverride(true)
  }

  const submitOverride = async () => {
    if (!selectedInventory) return
    if (!overrideForm.reason || overrideForm.reason.trim().length < 3) {
      toast.error('Please provide a valid reason (min 3 chars).')
      return
    }
    try {
      await inventoryService.overridePolicy(selectedInventory.id, {
        safety_stock: overrideForm.safety_stock ? Number(overrideForm.safety_stock) : undefined,
        reorder_point: overrideForm.reorder_point ? Number(overrideForm.reorder_point) : undefined,
        max_stock: overrideForm.max_stock ? Number(overrideForm.max_stock) : undefined,
        reason: overrideForm.reason,
      })
      toast.success('Policy override applied')
      setShowOverride(false)
      setSelectedInventory(null)
      await load()
    } catch {
      // handled globally
    }
  }

  const criticalCount = items.filter((i) => i.status === 'critical').length
  const lowCount = items.filter((i) => i.status === 'low').length
  const excessCount = items.filter((i) => i.status === 'excess').length
  const totalValue = items.reduce((sum, i) => sum + (i.valuation ?? 0), 0)

  const statusChartData = [
    { name: 'Normal', value: healthSummary?.normal_count ?? items.filter((i) => i.status === 'normal').length, color: '#10b981' },
    { name: 'Low', value: healthSummary?.low_count ?? lowCount, color: '#f59e0b' },
    { name: 'Critical', value: healthSummary?.critical_count ?? criticalCount, color: '#ef4444' },
    { name: 'Excess', value: healthSummary?.excess_count ?? excessCount, color: '#8b5cf6' },
  ]

  const qualityTierData = ['high', 'medium', 'low'].map((tier) => ({
    tier,
    count: dataQuality.filter((dq) => dq.quality_tier === tier).length,
  }))

  const filteredDataQuality = qualityTierFilter === 'all'
    ? dataQuality
    : dataQuality.filter((dq) => dq.quality_tier === qualityTierFilter)

  const recommendationFunnelData = controlTower
    ? [
        { stage: 'Pending', value: controlTower.pending_recommendations },
        { stage: 'Accepted', value: controlTower.accepted_recommendations },
        { stage: 'Applied', value: controlTower.applied_recommendations },
      ]
    : []

  const serviceLevelDistributionData = (serviceLevelAnalytics?.distribution || []).map((d) => ({
    bucket: d.bucket,
    probabilityPct: Number((d.probability * 100).toFixed(2)),
  }))

  const workingCapitalChartData = workingCapital
    ? [
        { metric: 'Inventory Value', value: workingCapital.total_inventory_value },
        { metric: 'Excess Value', value: workingCapital.excess_inventory_value },
        { metric: 'Low Exposure', value: workingCapital.low_stock_exposure_value },
        { metric: 'Annual Carry Cost', value: workingCapital.estimated_carrying_cost_annual },
      ]
    : []

  const exportInventoryCsv = () => {
    const escape = (value: string | number | undefined | null) => `"${String(value ?? '').replace(/"/g, '""')}"`
    const headers = ['Product', 'SKU', 'Location', 'On Hand', 'Allocated', 'In Transit', 'Safety Stock', 'ROP', 'Max Stock', 'Days of Supply', 'Status', 'Valuation']
    const rows = items.map((item) => [
      item.product?.name ?? `Product #${item.product_id}`,
      item.product?.sku ?? '',
      item.location,
      item.on_hand_qty,
      item.allocated_qty,
      item.in_transit_qty,
      item.safety_stock,
      item.reorder_point,
      item.max_stock ?? '',
      item.days_of_supply ?? '',
      item.status,
      item.valuation ?? '',
    ])

    const csv = [
      headers.map((h) => escape(h)).join(','),
      ...rows.map((row) => row.map((cell) => escape(cell as any)).join(',')),
    ].join('\n')

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `inventory-analytics-page-${page}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const resetAnalyticsDrilldowns = () => {
    setStatusFilter('')
    setQualityTierFilter('all')
    setRecommendationStatusFilter('pending')
    setPage(1)
  }

  const updateExceptionStatus = async (exceptionId: number, status: 'in_progress' | 'resolved') => {
    try {
      await inventoryService.updateException(exceptionId, { status })
      toast.success(`Exception marked ${status.replace('_', ' ')}`)
      await load()
    } catch {
      // handled globally
    }
  }

  const decideRecommendation = async (recommendationId: number, decision: 'accepted' | 'rejected') => {
    try {
      await inventoryService.decideRecommendation(recommendationId, {
        decision,
        apply_changes: decision === 'accepted',
      })
      toast.success(`Recommendation ${decision}`)
      await load()
    } catch {
      // handled globally
    }
  }

  const approveRecommendation = async (recommendationId: number) => {
    try {
      await inventoryService.approveRecommendation(recommendationId, { notes: 'Planner approved high-impact change' })
      toast.success('Recommendation approved')
      await load()
    } catch {
      // handled globally
    }
  }

  const applyApprovedRecommendation = async (recommendationId: number) => {
    try {
      await inventoryService.decideRecommendation(recommendationId, {
        decision: 'accepted',
        apply_changes: true,
        notes: 'Apply approved recommendation',
      })
      toast.success('Approved recommendation applied')
      await load()
    } catch {
      // handled globally
    }
  }

  const autoApplyRecommendations = async () => {
    setAutoApplyLoading(true)
    try {
      const res = await inventoryService.autoApplyRecommendations({
        min_confidence: 0.85,
        max_demand_pressure: 1.2,
        max_items: 100,
        dry_run: false,
      })
      toast.success(`Auto-applied ${res.applied_count} recommendations`)
      await load()
    } catch {
      // handled globally
    } finally {
      setAutoApplyLoading(false)
    }
  }

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

      {controlTower && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard title="Pending Recs" value={controlTower.pending_recommendations} icon={<Bot className="h-4 w-4" />} color="blue" />
          <KPICard title="Applied Recs" value={controlTower.applied_recommendations} icon={<Sparkles className="h-4 w-4" />} color="emerald" />
          <KPICard title="Acceptance Rate" value={`${controlTower.acceptance_rate_pct}%`} icon={<Package className="h-4 w-4" />} color="purple" />
          <KPICard title="Overdue Exceptions" value={controlTower.overdue_exceptions} icon={<AlertTriangle className="h-4 w-4" />} color="red"
            subtitle={`Backlog risk: ${controlTower.recommendation_backlog_risk}`} />
        </div>
      )}

      <Card title="Inventory Analytics" subtitle="Phase 1 visual insights for operations and finance decisions">
        <div className="flex items-center justify-end gap-2 mb-3">
          <Button size="sm" variant="outline" icon={<RotateCcw className="h-4 w-4" />} onClick={resetAnalyticsDrilldowns}>
            Reset Drilldowns
          </Button>
          <Button size="sm" variant="outline" icon={<Download className="h-4 w-4" />} onClick={exportInventoryCsv}>
            Export CSV
          </Button>
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <div className="border border-gray-100 rounded-lg p-3">
            <p className="text-sm font-medium text-gray-800 mb-2">Stock Status Distribution</p>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={statusChartData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={55}
                    outerRadius={85}
                    onClick={(entry: any) => {
                      const mapped = String(entry?.name || '').toLowerCase()
                      if (mapped) {
                        setStatusFilter(mapped)
                        setPage(1)
                      }
                    }}
                  >
                    {statusChartData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => formatNumber(Number(value ?? 0))} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="border border-gray-100 rounded-lg p-3">
            <p className="text-sm font-medium text-gray-800 mb-2">Working Capital Breakdown</p>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={workingCapitalChartData} margin={{ top: 8, right: 12, left: 4, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="metric" tick={{ fontSize: 11 }} />
                  <YAxis tickFormatter={(v) => `$${Math.round(Number(v) / 1000)}k`} width={56} />
                  <Tooltip formatter={(value) => formatCurrency(Number(value ?? 0))} />
                  <Bar dataKey="value" fill="#2563eb" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="border border-gray-100 rounded-lg p-3">
            <p className="text-sm font-medium text-gray-800 mb-2">Data Quality Distribution</p>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={qualityTierData} margin={{ top: 8, right: 12, left: 4, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="tier" />
                  <YAxis allowDecimals={false} width={40} />
                  <Tooltip formatter={(value) => formatNumber(Number(value ?? 0))} />
                  <Bar
                    dataKey="count"
                    radius={[6, 6, 0, 0]}
                    onClick={(payload: any) => {
                      const tier = String(payload?.tier || '').toLowerCase()
                      if (tier === 'high' || tier === 'medium' || tier === 'low') {
                        setQualityTierFilter(tier)
                      }
                    }}
                  >
                    {qualityTierData.map((entry) => (
                      <Cell
                        key={entry.tier}
                        fill={entry.tier === 'high' ? '#10b981' : entry.tier === 'medium' ? '#f59e0b' : '#ef4444'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="border border-gray-100 rounded-lg p-3">
            <p className="text-sm font-medium text-gray-800 mb-2">Recommendation Funnel</p>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={recommendationFunnelData} margin={{ top: 8, right: 12, left: 4, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="stage" />
                  <YAxis allowDecimals={false} width={40} />
                  <Tooltip formatter={(value) => formatNumber(Number(value ?? 0))} />
                  <Bar
                    dataKey="value"
                    fill="#7c3aed"
                    radius={[6, 6, 0, 0]}
                    onClick={(payload: any) => {
                      const stage = String(payload?.stage || '').toLowerCase()
                      if (stage) {
                        setRecommendationStatusFilter(stage)
                      }
                    }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </Card>

      <Card title="Service Level Under Uncertainty" subtitle="Probability-based CSL/fill-rate analytics from stock-demand distribution">
        <div className="flex flex-wrap items-end gap-2 mb-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Method</label>
            <select
              value={serviceLevelMethod}
              onChange={(e) => setServiceLevelMethod(e.target.value as InventoryServiceLevelMethod)}
              className="text-sm border border-gray-200 rounded-lg px-3 py-2"
            >
              <option value="analytical">Analytical</option>
              <option value="monte_carlo">Monte Carlo</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Target Service Level</label>
            <select
              value={String(targetServiceLevel)}
              onChange={(e) => setTargetServiceLevel(Number(e.target.value))}
              className="text-sm border border-gray-200 rounded-lg px-3 py-2"
            >
              <option value="0.9">90%</option>
              <option value="0.95">95%</option>
              <option value="0.97">97%</option>
              <option value="0.99">99%</option>
            </select>
          </div>
          <Button
            size="sm"
            loading={serviceLevelLoading}
            onClick={() => {
              const id = items[0]?.id
              if (!id) return
              void loadServiceLevelAnalytics(id)
            }}
          >
            Recalculate
          </Button>
        </div>

        {!serviceLevelAnalytics ? (
          <div className="text-sm text-gray-500">No inventory scope available for uncertainty analytics.</div>
        ) : (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              <KPICard title="Cycle SL" value={`${(serviceLevelAnalytics.cycle_service_level * 100).toFixed(1)}%`} icon={<Package className="h-4 w-4" />} color="emerald" />
              <KPICard title="Fill Rate" value={`${(serviceLevelAnalytics.fill_rate * 100).toFixed(1)}%`} icon={<Sparkles className="h-4 w-4" />} color="blue" />
              <KPICard title="Stockout Prob." value={`${(serviceLevelAnalytics.stockout_probability * 100).toFixed(1)}%`} icon={<AlertTriangle className="h-4 w-4" />} color="red" />
              <KPICard title="Recommended SS" value={formatNumber(serviceLevelAnalytics.recommended_safety_stock)} icon={<Bot className="h-4 w-4" />} color="purple" />
            </div>

            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={serviceLevelDistributionData} margin={{ top: 8, right: 12, left: 4, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="bucket" tick={{ fontSize: 10 }} interval={2} />
                  <YAxis tickFormatter={(v) => `${v}%`} width={44} />
                  <Tooltip formatter={(value) => `${Number(value).toFixed(2)}%`} />
                  <Bar dataKey="probabilityPct" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                  <Line
                    type="monotone"
                    dataKey="probabilityPct"
                    stroke="#1d4ed8"
                    strokeWidth={2}
                    dot={false}
                    name="Distribution Curve"
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </Card>

      <Card title="Data Quality Gate" subtitle="Phase 6 data quality scoring for recommendation readiness">
        {filteredDataQuality.length === 0 ? (
          <div className="text-sm text-gray-500">No data-quality records available.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {filteredDataQuality.slice(0, 6).map((dq) => (
              <div key={dq.inventory_id} className="border border-gray-100 rounded-lg p-3">
                <p className="text-xs text-gray-500">Inventory #{dq.inventory_id} · Product #{dq.product_id}</p>
                <p className="text-sm font-semibold text-gray-900 mt-1">{dq.location}</p>
                <p className={`text-xs mt-1 ${dq.quality_tier === 'high' ? 'text-emerald-600' : dq.quality_tier === 'medium' ? 'text-amber-600' : 'text-red-600'}`}>
                  Tier: {dq.quality_tier.toUpperCase()} · Overall: {(dq.overall_score * 100).toFixed(0)}%
                </p>
              </div>
            ))}
          </div>
        )}
      </Card>

      {workingCapital && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard title="Inventory Value" value={formatCurrency(workingCapital.total_inventory_value)} icon={<Package className="h-4 w-4" />} color="blue" />
          <KPICard title="Annual Carry Cost" value={formatCurrency(workingCapital.estimated_carrying_cost_annual)} icon={<Sparkles className="h-4 w-4" />} color="purple" />
          <KPICard title="Excess Value" value={formatCurrency(workingCapital.excess_inventory_value)} icon={<AlertTriangle className="h-4 w-4" />} color="amber" />
          <KPICard title="Health Index" value={`${workingCapital.inventory_health_index}%`} icon={<Bot className="h-4 w-4" />} color="emerald" />
        </div>
      )}

      <Card title="Control Tower Escalations" subtitle="Phase 7 SLA and severity-based exception escalation feed">
        {escalations.length === 0 ? (
          <div className="text-sm text-gray-500">No active escalations.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  {['Level', 'Exception', 'Product', 'Location', 'Status', 'Due Date', 'Reason'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {escalations.map((e) => (
                  <tr key={e.exception_id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3"><StatusBadge status={e.escalation_level === 'L2' ? 'critical' : 'warning'} size="sm" /></td>
                    <td className="px-4 py-3 text-gray-700">#{e.exception_id}</td>
                    <td className="px-4 py-3 text-gray-700">#{e.product_id}</td>
                    <td className="px-4 py-3 text-gray-700">{e.location}</td>
                    <td className="px-4 py-3"><StatusBadge status={e.status} size="sm" /></td>
                    <td className="px-4 py-3 text-gray-700">{e.due_date ?? '—'}</td>
                    <td className="px-4 py-3 text-gray-700">{e.escalation_reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {assessment && (
        <Card title="Optimization Assessment Scorecard" subtitle="Phase 8 executive maturity scorecard">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-gray-700">{assessment.maturity_level}</p>
            <p className="text-xs text-gray-500">Checks: {assessment.total_yes}/{assessment.total_checks}</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  {['Area', 'Score', 'RAG'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {assessment.areas.map((a) => (
                  <tr key={a.area} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-gray-700">{a.area}</td>
                    <td className="px-4 py-3 text-gray-700">{a.yes_count}/{a.total_count}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={a.rag === 'green' ? 'normal' : a.rag === 'amber' ? 'warning' : 'critical'} size="sm" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

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
            {canUpdate && (
              <>
                <Button
                  size="sm"
                  icon={<Sparkles className="h-4 w-4" />}
                  loading={optimizationLoading}
                  onClick={runOptimization}
                >
                  Run Optimization
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  icon={<Bot className="h-4 w-4" />}
                  loading={recommendationLoading}
                  onClick={generateRecommendations}
                >
                  Generate AI Recommendations
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  icon={<Sparkles className="h-4 w-4" />}
                  loading={autoApplyLoading}
                  onClick={autoApplyRecommendations}
                >
                  Auto-Apply (Guardrails)
                </Button>
              </>
            )}
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
                  {['Product', 'Location', 'On Hand', 'Allocated', 'In Transit', 'Safety Stock', 'ROP', 'Days of Supply', 'Status', 'Actions'].map((h) => (
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
                    <td className="px-4 py-3 tabular-nums text-gray-600">{formatNumber(item.reorder_point)}</td>
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
                    <td className="px-4 py-3">
                      {canUpdate ? (
                        <Button variant="outline" size="sm" onClick={() => openOverride(item)}>
                          Override
                        </Button>
                      ) : (
                        <span className="text-xs text-gray-400">—</span>
                      )}
                    </td>
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

      <Card title="Network Rebalance Recommendations" subtitle="Phase 4 multi-location transfer suggestions">
        {rebalance.length === 0 ? (
          <div className="text-sm text-gray-500">No rebalance opportunities detected.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  {['Product', 'From', 'To', 'Transfer Qty', 'Estimated Service Uplift'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {rebalance.map((r, idx) => (
                  <tr key={`${r.product_id}-${r.from_inventory_id}-${r.to_inventory_id}-${idx}`} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-gray-700">{r.product_name ?? `#${r.product_id}`}</td>
                    <td className="px-4 py-3 text-gray-700">{r.from_location}</td>
                    <td className="px-4 py-3 text-gray-700">{r.to_location}</td>
                    <td className="px-4 py-3 tabular-nums text-gray-700">{formatNumber(r.transfer_qty)}</td>
                    <td className="px-4 py-3 text-emerald-700 font-medium">+{r.estimated_service_uplift_pct.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Inventory Policy Exceptions" subtitle="System-generated stockout/excess risk alerts">
        {exceptions.length === 0 ? (
          <div className="text-sm text-gray-500">No open policy exceptions.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  {['Type', 'Severity', 'Product', 'Location', 'Status', 'Owner', 'Due Date', 'Recommended Action', 'Action'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {exceptions.map((ex, idx) => (
                  <tr key={`${ex.inventory_id}-${idx}`} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1">
                        <ShieldAlert className="h-3.5 w-3.5 text-amber-500" />
                        {ex.exception_type}
                      </span>
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={ex.severity} size="sm" /></td>
                    <td className="px-4 py-3 text-gray-700">#{ex.product_id}</td>
                    <td className="px-4 py-3 text-gray-700">{ex.location}</td>
                    <td className="px-4 py-3"><StatusBadge status={ex.status} size="sm" /></td>
                    <td className="px-4 py-3 text-gray-700">{ex.owner_user_id ? `#${ex.owner_user_id}` : '—'}</td>
                    <td className="px-4 py-3 text-gray-700">{ex.due_date ?? '—'}</td>
                    <td className="px-4 py-3 text-gray-700">{ex.recommended_action}</td>
                    <td className="px-4 py-3">
                      {canUpdate && ex.id ? (
                        <div className="flex gap-1">
                          {ex.status === 'open' && (
                            <Button variant="outline" size="sm" onClick={() => updateExceptionStatus(ex.id!, 'in_progress')}>
                              Start
                            </Button>
                          )}
                          {ex.status !== 'resolved' && (
                            <Button variant="outline" size="sm" onClick={() => updateExceptionStatus(ex.id!, 'resolved')}>
                              Resolve
                            </Button>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="AI Policy Recommendations" subtitle="Phase 3/6 queue with maker-checker approval support">
        {recommendations.length === 0 ? (
          <div className="text-sm text-gray-500">No pending recommendations. Generate recommendations to start review.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  {['Confidence', 'Product', 'Location', 'Safety Stock', 'ROP', 'Max Stock', 'Status', 'Rationale', 'Action'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {recommendations.map((rec) => (
                  <tr key={rec.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">{Math.round((rec.confidence_score || 0) * 100)}%</td>
                    <td className="px-4 py-3 text-gray-700">#{rec.product_id}</td>
                    <td className="px-4 py-3 text-gray-700">{rec.location}</td>
                    <td className="px-4 py-3 tabular-nums text-gray-700">{formatNumber(rec.recommended_safety_stock)}</td>
                    <td className="px-4 py-3 tabular-nums text-gray-700">{formatNumber(rec.recommended_reorder_point)}</td>
                    <td className="px-4 py-3 tabular-nums text-gray-700">{rec.recommended_max_stock != null ? formatNumber(rec.recommended_max_stock) : '—'}</td>
                    <td className="px-4 py-3"><StatusBadge status={rec.status} size="sm" /></td>
                    <td className="px-4 py-3 text-gray-700 max-w-sm">{rec.rationale}</td>
                    <td className="px-4 py-3">
                      {canUpdate ? (
                        <div className="flex gap-1">
                          {rec.status === 'pending' && (
                            <>
                              <Button variant="outline" size="sm" onClick={() => approveRecommendation(rec.id)}>
                                Approve
                              </Button>
                              <Button variant="outline" size="sm" onClick={() => decideRecommendation(rec.id, 'rejected')}>
                                Reject
                              </Button>
                            </>
                          )}
                          {rec.status === 'accepted' && (
                            <Button variant="outline" size="sm" onClick={() => applyApprovedRecommendation(rec.id)}>
                              Apply
                            </Button>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400">—</span>
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
        isOpen={showOverride}
        onClose={() => setShowOverride(false)}
        title="Inventory Policy Override"
        footer={
          <>
            <Button variant="outline" onClick={() => setShowOverride(false)}>Cancel</Button>
            <Button onClick={submitOverride}>Apply Override</Button>
          </>
        }
      >
        <div className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Safety Stock</label>
              <input
                type="number"
                value={overrideForm.safety_stock}
                onChange={(e) => setOverrideForm((f) => ({ ...f, safety_stock: e.target.value }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Reorder Point</label>
              <input
                type="number"
                value={overrideForm.reorder_point}
                onChange={(e) => setOverrideForm((f) => ({ ...f, reorder_point: e.target.value }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Max Stock</label>
              <input
                type="number"
                value={overrideForm.max_stock}
                onChange={(e) => setOverrideForm((f) => ({ ...f, max_stock: e.target.value }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Reason *</label>
            <textarea
              rows={3}
              value={overrideForm.reason}
              onChange={(e) => setOverrideForm((f) => ({ ...f, reason: e.target.value }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Document business reason for policy override"
            />
          </div>
        </div>
      </Modal>
    </div>
  )
}
