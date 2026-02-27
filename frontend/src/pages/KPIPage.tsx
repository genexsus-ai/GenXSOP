import { useEffect, useState } from 'react'
import { Plus, TrendingUp, TrendingDown, Minus, BarChart3 } from 'lucide-react'
import { kpiService } from '@/services/kpiService'
import { Card } from '@/components/common/Card'
import { Button } from '@/components/common/Button'
import { Modal } from '@/components/common/Modal'
import { SkeletonCard } from '@/components/common/LoadingSpinner'
import { formatPercent, formatNumber, formatPeriod } from '@/utils/formatters'
import type { KPIMetric, CreateKPIRequest, KPICategory } from '@/types'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/store/authStore'
import { can } from '@/auth/permissions'

const CATEGORIES: KPICategory[] = ['demand', 'supply', 'inventory', 'financial', 'service']

const categoryColor: Record<KPICategory, string> = {
  demand: 'bg-blue-50 text-blue-700 border-blue-200',
  supply: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  inventory: 'bg-purple-50 text-purple-700 border-purple-200',
  financial: 'bg-amber-50 text-amber-700 border-amber-200',
  service: 'bg-indigo-50 text-indigo-700 border-indigo-200',
}

export function KPIPage() {
  const { user } = useAuthStore()
  const canManage = can(user?.role, 'kpi.manage')

  const [metrics, setMetrics] = useState<KPIMetric[]>([])
  const [loading, setLoading] = useState(true)
  const [activeCategory, setActiveCategory] = useState<string>('')
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<Partial<CreateKPIRequest>>({
    metric_category: 'demand',
  })

  const load = async () => {
    setLoading(true)
    try {
      const res = await kpiService.getMetrics({
        page_size: 100,
        category: activeCategory || undefined,
      })
      // Defensive: never allow metrics to become undefined (would crash render)
      setMetrics(Array.isArray(res.items) ? res.items : [])
    } catch (e) {
      console.error('Failed to load KPI metrics', e)
      toast.error('Failed to load KPI metrics')
      setMetrics([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [activeCategory])

  const handleCreate = async () => {
    if (!form.metric_name || !form.period || form.value === undefined) {
      toast.error('Please fill in all required fields')
      return
    }
    try {
      await kpiService.createMetric(form as CreateKPIRequest)
      toast.success('KPI metric recorded')
      setShowCreate(false)
      setForm({ metric_category: 'demand' })
      load()
    } catch {
      // handled
    }
  }

  const TrendIcon = ({ trend }: { trend?: string }) => {
    if (trend === 'improving') return <TrendingUp className="h-4 w-4 text-emerald-500" />
    if (trend === 'declining') return <TrendingDown className="h-4 w-4 text-red-500" />
    return <Minus className="h-4 w-4 text-gray-400" />
  }

  // Extra guard: if backend returns Decimal fields as strings, avoid crashing
  // formatting helpers (toFixed) in the UI.
  const asNumber = (v: unknown): number => {
    if (typeof v === 'number' && Number.isFinite(v)) return v
    if (typeof v === 'string' && v.trim() !== '') {
      const n = Number(v)
      if (Number.isFinite(n)) return n
    }
    return 0
  }

  const grouped = CATEGORIES.reduce((acc, cat) => {
    acc[cat] = metrics.filter((m) => m.metric_category === cat)
    return acc
  }, {} as Record<KPICategory, KPIMetric[]>)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">KPI Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">{metrics.length} metrics tracked</p>
        </div>
        {canManage && (
          <Button icon={<Plus />} onClick={() => setShowCreate(true)}>
            Record KPI
          </Button>
        )}
      </div>

      {/* Category filter */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => setActiveCategory('')}
          className={`px-3 py-1.5 text-xs rounded-full font-medium transition-colors ${
            activeCategory === '' ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          All
        </button>
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-3 py-1.5 text-xs rounded-full font-medium transition-colors capitalize ${
              activeCategory === cat ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => <SkeletonCard key={i} rows={3} />)}
        </div>
      ) : metrics.length === 0 ? (
        <Card>
          <div className="text-center py-16 text-gray-400">
            <BarChart3 className="h-10 w-10 mx-auto mb-3 opacity-40" />
            <p className="text-sm">No KPI metrics found. Start recording metrics.</p>
          </div>
        </Card>
      ) : (
        <div className="space-y-6">
          {(activeCategory ? [activeCategory as KPICategory] : CATEGORIES).map((cat) => {
            const catMetrics = grouped[cat]
            if (catMetrics.length === 0) return null
            return (
              <div key={cat}>
                <h2 className="text-sm font-semibold text-gray-700 capitalize mb-3">{cat} KPIs</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {catMetrics.map((metric) => {
                    const valueNum = asNumber(metric.value)
                    const targetNum = metric.target != null ? asNumber(metric.target) : undefined
                    const achievementPct = targetNum ? (valueNum / targetNum) * 100 : null
                    return (
                      <div key={metric.id} className="bg-white rounded-xl border border-gray-100 p-5">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                              {metric.metric_name.replace(/_/g, ' ')}
                            </p>
                            <p className="text-xs text-gray-400 mt-0.5">{formatPeriod(metric.period)}</p>
                          </div>
                          <span className={`text-xs px-2 py-0.5 rounded-full border font-medium capitalize ${categoryColor[metric.metric_category]}`}>
                            {metric.metric_category}
                          </span>
                        </div>

                        <div className="flex items-end justify-between mb-3">
                          <div>
                            <p className="text-2xl font-bold text-gray-900 tabular-nums">
                              {metric.unit === '%' ? formatPercent(valueNum) : formatNumber(valueNum)}
                              {metric.unit && metric.unit !== '%' && (
                                <span className="text-sm font-normal text-gray-500 ml-1">{metric.unit}</span>
                              )}
                            </p>
                            {targetNum != null && (
                              <p className="text-xs text-gray-500 mt-0.5">
                                Target: {metric.unit === '%' ? formatPercent(targetNum) : formatNumber(targetNum)}
                              </p>
                            )}
                          </div>
                          <div className="flex items-center gap-1">
                            <TrendIcon trend={metric.trend} />
                            {metric.variance_pct != null && (
                              <span className={`text-xs font-medium ${metric.variance_pct >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                                {metric.variance_pct >= 0 ? '+' : ''}{metric.variance_pct.toFixed(1)}%
                              </span>
                            )}
                          </div>
                        </div>

                        {achievementPct !== null && (
                          <div>
                            <div className="flex justify-between text-xs text-gray-400 mb-1">
                              <span>Achievement</span>
                              <span>{achievementPct.toFixed(0)}%</span>
                            </div>
                            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${achievementPct >= 100 ? 'bg-emerald-500' : achievementPct >= 80 ? 'bg-amber-500' : 'bg-red-500'}`}
                                style={{ width: `${Math.min(100, achievementPct)}%` }}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      )}

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Record KPI Metric"
        footer={
          <>
            <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={!canManage}>Record</Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Metric Name *</label>
            <input value={form.metric_name ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, metric_name: e.target.value }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., forecast_accuracy" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Category</label>
              <select value={form.metric_category ?? 'demand'}
                onChange={(e) => setForm((f) => ({ ...f, metric_category: e.target.value as KPICategory }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Period *</label>
              <input type="month" value={form.period?.slice(0, 7) ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, period: e.target.value + '-01' }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Value *</label>
              <input type="number" step="0.01" value={form.value ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, value: Number(e.target.value) }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Target</label>
              <input type="number" step="0.01" value={form.target ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, target: Number(e.target.value) }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Unit</label>
              <input value={form.unit ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, unit: e.target.value }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="%, units..." />
            </div>
          </div>
        </div>
      </Modal>
    </div>
  )
}
