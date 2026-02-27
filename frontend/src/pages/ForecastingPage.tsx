import { useEffect, useState } from 'react'
import { Brain, Play, TrendingUp, Target } from 'lucide-react'
import { forecastService } from '@/services/forecastService'
import { Card } from '@/components/common/Card'
import { Button } from '@/components/common/Button'
import { KPICard } from '@/components/common/KPICard'
import { Modal } from '@/components/common/Modal'
import { SkeletonTable } from '@/components/common/LoadingSpinner'
import { formatPeriod, formatNumber, formatPercent } from '@/utils/formatters'
import type { Forecast, ForecastAccuracy, GenerateForecastRequest } from '@/types'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/store/authStore'
import { can } from '@/auth/permissions'

const MODEL_TYPES = [
  { value: 'moving_average', label: 'Moving Average' },
  { value: 'exp_smoothing', label: 'Exponential Smoothing' },
  { value: 'arima', label: 'ARIMA' },
  { value: 'prophet', label: 'Prophet' },
  { value: 'ml_ensemble', label: 'ML Ensemble' },
]

export function ForecastingPage() {
  const { user } = useAuthStore()
  const canGenerate = can(user?.role, 'forecast.generate')

  const [forecasts, setForecasts] = useState<Forecast[]>([])
  const [accuracy, setAccuracy] = useState<ForecastAccuracy[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [showGenerate, setShowGenerate] = useState(false)
  const [form, setForm] = useState<Partial<GenerateForecastRequest>>({
    model_type: 'ml_ensemble',
    horizon_months: 6,
  })

  const load = async () => {
    setLoading(true)
    try {
      const [fRes, aRes] = await Promise.all([
        forecastService.getResults({ page_size: 50 }),
        forecastService.getAccuracy(),
      ])
      setForecasts(fRes.items)
      setAccuracy(aRes)
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
      await forecastService.generateForecast(form as GenerateForecastRequest)
      toast.success('Forecast generated successfully')
      setShowGenerate(false)
      load()
    } catch {
      // handled
    } finally {
      setGenerating(false)
    }
  }

  const avgMape = accuracy.length > 0
    ? accuracy.reduce((s, a) => s + a.mape, 0) / accuracy.length
    : 0

  const bestModel = accuracy.length > 0
    ? accuracy.reduce((best, a) => a.mape < best.mape ? a : best, accuracy[0])
    : null

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">AI Forecasting</h1>
          <p className="text-sm text-gray-500 mt-0.5">ML-powered demand forecasting</p>
        </div>
        {canGenerate && (
          <Button icon={<Play />} onClick={() => setShowGenerate(true)}>
            Generate Forecast
          </Button>
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

      {/* Generate Modal */}
      <Modal isOpen={showGenerate} onClose={() => setShowGenerate(false)} title="Generate Forecast"
        footer={
          <>
            <Button variant="outline" onClick={() => setShowGenerate(false)}>Cancel</Button>
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
            <select value={form.model_type ?? 'ml_ensemble'}
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
