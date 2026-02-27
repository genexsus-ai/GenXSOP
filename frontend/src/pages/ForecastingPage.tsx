import { useEffect, useState } from 'react'
import { AlertTriangle, Brain, Play, Sparkles, TrendingUp, Target } from 'lucide-react'
import { forecastService } from '@/services/forecastService'
import { Card } from '@/components/common/Card'
import { Button } from '@/components/common/Button'
import { KPICard } from '@/components/common/KPICard'
import { Modal } from '@/components/common/Modal'
import { SkeletonTable } from '@/components/common/LoadingSpinner'
import { formatPeriod, formatNumber, formatPercent } from '@/utils/formatters'
import type { Forecast, ForecastAccuracy, ForecastDiagnostics, ForecastDriftAlert, GenerateForecastRequest } from '@/types'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/store/authStore'
import { can } from '@/auth/permissions'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const MODEL_TYPES = [
  { value: 'moving_average', label: 'Moving Average' },
  { value: 'exp_smoothing', label: 'Exponential Smoothing' },
  { value: 'prophet', label: 'Prophet' },
]

export function ForecastingPage() {
  const { user } = useAuthStore()
  const canGenerate = can(user?.role, 'forecast.generate')

  const [forecasts, setForecasts] = useState<Forecast[]>([])
  const [accuracy, setAccuracy] = useState<ForecastAccuracy[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [recommending, setRecommending] = useState(false)
  const [showGenerate, setShowGenerate] = useState(false)
  const [diagnostics, setDiagnostics] = useState<ForecastDiagnostics | null>(null)
  const [driftAlerts, setDriftAlerts] = useState<ForecastDriftAlert[]>([])
  const [form, setForm] = useState<Partial<GenerateForecastRequest>>({
    model_type: 'prophet',
    horizon_months: 6,
  })

  const load = async () => {
    setLoading(true)
    try {
      const [fRes, aRes] = await Promise.all([
        forecastService.getResults({ page_size: 50 }),
        forecastService.getAccuracy(),
      ])
      const drift = await forecastService.getDriftAlerts({ threshold_pct: 8, min_points: 6 })
      setForecasts(fRes.items)
      setAccuracy(aRes)
      setDriftAlerts(drift)
    } catch {
      // handled
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleGenerate = async () => {
    if (!form.product_id) {
      toast.error('Please enter a product ID')
      return
    }
    setGenerating(true)
    try {
      const result = await forecastService.generateForecast(form as GenerateForecastRequest)
      setDiagnostics(result.diagnostics ?? null)
      toast.success('Forecast generated successfully')
      setShowGenerate(false)
      load()
    } catch {
      // handled
    } finally {
      setGenerating(false)
    }
  }

  const handleRecommend = async () => {
    if (!form.product_id) {
      toast.error('Please enter a product ID')
      setShowGenerate(true)
      return
    }

    setRecommending(true)
    try {
      const result = await forecastService.getRecommendation({
        product_id: form.product_id,
        model_type: form.model_type,
      })
      setDiagnostics(result.diagnostics ?? null)
      toast.success('Recommendation received')
    } catch {
      // handled
    } finally {
      setRecommending(false)
    }
  }

  const avgMape = accuracy.length > 0
    ? accuracy.reduce((s, a) => s + a.mape, 0) / accuracy.length
    : 0

  const bestModel = accuracy.length > 0
    ? accuracy.reduce((best, a) => a.mape < best.mape ? a : best, accuracy[0])
    : null

  const chartData = [...forecasts]
    .sort((a, b) => new Date(a.period).getTime() - new Date(b.period).getTime())
    .map((f) => ({
      period: formatPeriod(f.period),
      predicted_qty: f.predicted_qty,
      lower_bound: f.lower_bound ?? f.predicted_qty,
      upper_bound: f.upper_bound ?? f.predicted_qty,
      mape: f.mape ?? null,
    }))

  const accuracyChartData = [...accuracy]
    .sort((a, b) => a.mape - b.mape)
    .map((a) => ({
      model: a.model_type.replace(/_/g, ' '),
      mape: a.mape,
      wape: a.wape,
      hit_rate: a.hit_rate,
    }))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">AI Forecasting</h1>
          <p className="text-sm text-gray-500 mt-0.5">ML-powered demand forecasting</p>
        </div>
        {canGenerate && (
          <div className="flex items-center gap-2">
            <Button variant="outline" icon={<Sparkles />} loading={recommending} onClick={handleRecommend}>
              Get Recommendation
            </Button>
            <Button icon={<Play />} onClick={() => setShowGenerate(true)}>
              Generate Forecast
            </Button>
          </div>
        )}
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard title="Avg MAPE" value={formatPercent(avgMape)} icon={<Target className="h-4 w-4" />} color="blue"
          subtitle="Mean Absolute % Error" />
        <KPICard title="Best Model" value={bestModel?.model_type?.replace(/_/g, ' ') ?? '—'}
          icon={<Brain className="h-4 w-4" />} color="emerald"
          subtitle={bestModel ? `MAPE: ${formatPercent(bestModel.mape)}` : undefined} />
        <KPICard title="Forecasts Generated" value={forecasts.length}
          icon={<TrendingUp className="h-4 w-4" />} color="purple" />
        <KPICard title="Models Evaluated" value={accuracy.length}
          icon={<Brain className="h-4 w-4" />} color="indigo" />
      </div>

      {diagnostics && (
        <Card title="AI Advisor Decision" subtitle="GenXAI model recommendation diagnostics">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Selected Model</p>
              <p className="font-semibold text-gray-900">{diagnostics.selected_model?.replace(/_/g, ' ') ?? '—'}</p>
            </div>
            <div>
              <p className="text-gray-500">Advisor Confidence</p>
              <p className="font-semibold text-gray-900">{formatPercent((diagnostics.advisor_confidence ?? 0) * 100, 0)}</p>
            </div>
            <div className="md:col-span-2">
              <p className="text-gray-500">Reason</p>
              <p className="text-gray-800">{diagnostics.selection_reason ?? 'No recommendation details.'}</p>
            </div>
          </div>
        </Card>
      )}

      {driftAlerts.length > 0 && (
        <Card title="Forecast Drift Alerts" subtitle="Month-over-month accuracy degradation detected">
          <div className="space-y-2">
            {driftAlerts.slice(0, 5).map((a, idx) => (
              <div key={`${a.product_id}-${a.model_type}-${idx}`} className="flex items-center justify-between p-3 rounded-lg border border-amber-200 bg-amber-50">
                <div className="flex items-center gap-2 min-w-0">
                  <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
                  <p className="text-sm text-amber-900 truncate">
                    Product #{a.product_id} · {a.model_type.replace(/_/g, ' ')} degraded by {formatPercent(a.degradation_pct)}
                  </p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full ${a.severity === 'high' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
                  {a.severity}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Forecast Results */}
        <Card title="Recent Forecasts" subtitle={`${forecasts.length} results`}>
          {loading ? (
            <SkeletonTable rows={6} cols={4} />
          ) : forecasts.length === 0 ? (
            <div className="text-center py-10 text-gray-400">
              <Brain className="h-8 w-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm">No forecasts yet. Generate your first forecast.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100">
                    {['Product', 'Period', 'Model', 'Predicted Qty', 'MAPE'].map((h) => (
                      <th key={h} className="text-left pb-3 text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {forecasts.slice(0, 10).map((f) => (
                    <tr key={f.id} className="hover:bg-gray-50">
                      <td className="py-2.5 font-medium text-gray-900 pr-3">
                        {f.product?.name ?? `#${f.product_id}`}
                      </td>
                      <td className="py-2.5 text-gray-600 pr-3">{formatPeriod(f.period)}</td>
                      <td className="py-2.5 pr-3">
                        <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
                          {f.model_type.replace(/_/g, ' ')}
                        </span>
                        {f.fallback_used ? (
                          <span className="ml-2 text-[10px] bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full" title={f.selection_reason ?? 'Advisor fallback used'}>
                            fallback
                          </span>
                        ) : null}
                      </td>
                      <td className="py-2.5 tabular-nums pr-3">{formatNumber(f.predicted_qty)}</td>
                      <td className="py-2.5 tabular-nums">
                        {f.mape != null ? (
                          <span className={f.mape < 10 ? 'text-emerald-600' : f.mape < 20 ? 'text-amber-600' : 'text-red-500'}>
                            {formatPercent(f.mape)}
                          </span>
                        ) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Model Accuracy */}
        <Card title="Model Accuracy Comparison">
          {accuracy.length === 0 ? (
            <div className="text-center py-10 text-gray-400">
              <p className="text-sm">No accuracy data available</p>
            </div>
          ) : (
            <div className="space-y-3">
              {accuracy.map((a) => (
                <div key={`${a.product_id}-${a.model_type}`} className="flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-gray-700">
                        {a.model_type.replace(/_/g, ' ')}
                      </span>
                      <span className="text-xs text-gray-500">MAPE: {formatPercent(a.mape)}</span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${a.mape < 10 ? 'bg-emerald-500' : a.mape < 20 ? 'bg-amber-500' : 'bg-red-500'}`}
                        style={{ width: `${Math.min(100, 100 - a.mape)}%` }}
                      />
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500">Bias</p>
                    <p className={`text-xs font-medium ${a.bias > 0 ? 'text-red-500' : 'text-emerald-600'}`}>
                      {a.bias > 0 ? '+' : ''}{a.bias.toFixed(1)}%
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="Forecast Curve" subtitle="Prediction with confidence interval">
          {chartData.length === 0 ? (
            <div className="text-center py-10 text-gray-400 text-sm">Generate forecast to visualize trend</div>
          ) : (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 16, right: 16, left: 0, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="period" tickMargin={8} />
                  <YAxis width={56} />
                  <Tooltip formatter={(v: number) => formatNumber(v)} />
                  <Legend />
                  <Area type="monotone" dataKey="upper_bound" stroke="none" fill="#93c5fd" fillOpacity={0.25} name="Upper Bound" />
                  <Area type="monotone" dataKey="lower_bound" stroke="none" fill="#ffffff" fillOpacity={1} name="Lower Bound Mask" />
                  <Line type="monotone" dataKey="predicted_qty" stroke="#2563eb" strokeWidth={2} dot={false} name="Predicted Qty" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card title="Error & Model Quality" subtitle="Cross-model accuracy overview">
          {accuracyChartData.length === 0 ? (
            <div className="text-center py-10 text-gray-400 text-sm">No accuracy metrics available yet</div>
          ) : (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={accuracyChartData} margin={{ top: 16, right: 16, left: 0, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="model" tickMargin={8} />
                  <YAxis width={56} />
                  <Tooltip formatter={(v: number) => formatPercent(v)} />
                  <Legend />
                  <Line type="monotone" dataKey="mape" stroke="#ef4444" strokeWidth={2} name="MAPE" />
                  <Line type="monotone" dataKey="wape" stroke="#f59e0b" strokeWidth={2} name="WAPE" />
                  <Line type="monotone" dataKey="hit_rate" stroke="#10b981" strokeWidth={2} name="Hit Rate" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>

      {/* Generate Modal */}
      <Modal isOpen={showGenerate} onClose={() => setShowGenerate(false)} title="Generate Forecast"
        footer={
          <>
            <Button variant="outline" onClick={() => setShowGenerate(false)}>Cancel</Button>
            <Button variant="outline" loading={recommending} onClick={handleRecommend} icon={<Sparkles />} disabled={!canGenerate}>
              Get Recommendation
            </Button>
            <Button loading={generating} onClick={handleGenerate} icon={<Brain />} disabled={!canGenerate}>
              Generate
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Product ID *</label>
            <input type="number" value={form.product_id ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, product_id: Number(e.target.value) }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter product ID" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Model Type</label>
            <select value={form.model_type ?? 'prophet'}
              onChange={(e) => setForm((f) => ({ ...f, model_type: e.target.value as GenerateForecastRequest['model_type'] }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
              {MODEL_TYPES.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">
              Forecast Horizon (months): {form.horizon_months}
            </label>
            <input type="range" min={1} max={24} value={form.horizon_months ?? 6}
              onChange={(e) => setForm((f) => ({ ...f, horizon_months: Number(e.target.value) }))}
              className="w-full" />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>1 month</span><span>24 months</span>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  )
}
