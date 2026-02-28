import { useEffect, useState } from 'react'
import { AlertTriangle, Brain, Check, Edit3, Eye, Play, TrendingUp, Target, Trash2, Upload } from 'lucide-react'
import { forecastService } from '@/services/forecastService'
import { demandService } from '@/services/demandService'
import { productService } from '@/services/productService'
import { Card } from '@/components/common/Card'
import { Button } from '@/components/common/Button'
import { KPICard } from '@/components/common/KPICard'
import { Modal } from '@/components/common/Modal'
import { SkeletonTable } from '@/components/common/LoadingSpinner'
import { StageTabs } from '@/components/forecasting/StageTabs'
import { formatPeriod, formatNumber, formatPercent } from '@/utils/formatters'
import type {
  Forecast,
  ForecastAccuracy,
  ForecastConsensus,
  ForecastDriftAlert,
  GenerateForecastRequest,
  ForecastModelType,
  Product,
  DemandPlan,
} from '@/types'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/store/authStore'
import { can } from '@/auth/permissions'
import {
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
  { value: 'ewma', label: 'EWMA' },
  { value: 'exp_smoothing', label: 'Exponential Smoothing' },
  { value: 'seasonal_naive', label: 'Seasonal Naive' },
  { value: 'arima', label: 'ARIMA' },
  { value: 'prophet', label: 'Prophet' },
]

const FORECAST_STAGES = [
  { key: 'stage1', label: '1. Historical' },
  { key: 'stage2', label: '2. Model Setup' },
  { key: 'stage4', label: '3. Forecast View' },
  { key: 'stage5', label: '4. Manage Results' },
] as const

type ForecastStageKey = typeof FORECAST_STAGES[number]['key']

export function ForecastingPage() {
  const { user } = useAuthStore()
  const canGenerate = can(user?.role, 'forecast.generate')
  const canApproveConsensus = can(user?.role, 'forecast.consensus.approve')

  const [forecasts, setForecasts] = useState<Forecast[]>([])
  const [accuracy, setAccuracy] = useState<ForecastAccuracy[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [showGenerate, setShowGenerate] = useState(false)
  const [driftAlerts, setDriftAlerts] = useState<ForecastDriftAlert[]>([])
  const [consensusRecords, setConsensusRecords] = useState<ForecastConsensus[]>([])
  const [showConsensusModal, setShowConsensusModal] = useState(false)
  const [savingConsensus, setSavingConsensus] = useState(false)
  const [consensusModalMode, setConsensusModalMode] = useState<'fresh' | 'edit'>('fresh')
  const [consensusForm, setConsensusForm] = useState({
    period: '',
    baseline_qty: 0,
    sales_override_qty: 0,
    marketing_uplift_qty: 0,
    finance_adjustment_qty: 0,
    constraint_cap_qty: '',
    status: 'draft' as ForecastConsensus['status'],
    notes: '',
  })
  const [latestGeneratedForecasts, setLatestGeneratedForecasts] = useState<Forecast[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [selectedProductId, setSelectedProductId] = useState<number | undefined>(undefined)
  const [lastGeneratedProductId, setLastGeneratedProductId] = useState<number | undefined>(undefined)
  const [lastGeneratedRunAuditId, setLastGeneratedRunAuditId] = useState<number | undefined>(undefined)
  const [selectedForecastRunAuditId, setSelectedForecastRunAuditId] = useState<number | undefined>(undefined)
  const [selectedForecastModelType, setSelectedForecastModelType] = useState<string | undefined>(undefined)
  const [historyRangeMonths, setHistoryRangeMonths] = useState(24)
  const [historyPlans, setHistoryPlans] = useState<DemandPlan[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [form, setForm] = useState<Partial<GenerateForecastRequest>>({
    model_type: 'prophet',
    horizon_months: 6,
  })
  const [activeStage, setActiveStage] = useState<ForecastStageKey>('stage1')

  const load = async () => {
    setLoading(true)
    try {
      const [fRes, aRes, cRes] = await Promise.allSettled([
        forecastService.getResults({ page_size: 50 }),
        forecastService.getAccuracy(),
        forecastService.getConsensus(),
      ])

      if (fRes.status === 'fulfilled') {
        setForecasts(fRes.value.items)
      }

      if (aRes.status === 'fulfilled') {
        setAccuracy(aRes.value)
      }

      if (cRes.status === 'fulfilled') {
        setConsensusRecords(cRes.value)
      }

      try {
        const drift = await forecastService.getDriftAlerts({ threshold_pct: 8, min_points: 6 })
        setDriftAlerts(drift)
      } catch {
        setDriftAlerts([])
      }
    } catch {
      // handled
    } finally {
      setLoading(false)
    }
  }

  const loadProducts = async () => {
    try {
      // Backend max page_size is 100
      const res = await productService.getProducts({ page_size: 100 })
      setProducts(res.items)
    } catch {
      setProducts([])
    }
  }

  useEffect(() => {
    load()
    loadProducts()
  }, [])

  const chartProductId = lastGeneratedProductId ?? selectedProductId ?? form.product_id ?? forecasts[0]?.product_id

  const fallbackRunAuditId = [...forecasts]
    .filter((f) => {
      const productMatch = !chartProductId || Number(f.product_id) === Number(chartProductId)
      const modelMatch = !selectedForecastModelType || f.model_type === selectedForecastModelType
      return productMatch && modelMatch && f.run_audit_id != null
    })
    .sort((a, b) => new Date(a.period).getTime() - new Date(b.period).getTime())
    .map((f) => f.run_audit_id)
    .filter((id): id is number => typeof id === 'number')
    .slice(-1)[0]

  const activeRunAuditId = lastGeneratedRunAuditId ?? selectedForecastRunAuditId ?? fallbackRunAuditId

  useEffect(() => {
    setForm((prev) => ({ ...prev, product_id: selectedProductId }))
  }, [selectedProductId])

  useEffect(() => {
    const loadHistoryPlans = async () => {
      if (!chartProductId) {
        setHistoryPlans([])
        return
      }

      setHistoryLoading(true)
      try {
        const periodTo = new Date()
        const periodFrom = new Date(periodTo.getFullYear(), periodTo.getMonth() - (historyRangeMonths - 1), 1)
        const history = await demandService.getPlans({
          page_size: 100,
          product_id: chartProductId,
          period_from: periodFrom.toISOString().slice(0, 10),
          period_to: periodTo.toISOString().slice(0, 10),
        })

        setHistoryPlans((history.items ?? []).sort((a, b) => new Date(a.period).getTime() - new Date(b.period).getTime()))
      } catch {
        setHistoryPlans([])
      } finally {
        setHistoryLoading(false)
      }
    }

    loadHistoryPlans()
  }, [chartProductId, historyRangeMonths])

  const handleGenerate = async () => {
    if (!form.product_id) {
      toast.error('Please enter a product ID')
      return
    }
    const generatedProductId = form.product_id
    setGenerating(true)
    try {
      const generated = await forecastService.generateForecast(form as GenerateForecastRequest)
      setLatestGeneratedForecasts(generated.forecasts ?? [])
      const runAuditId = generated.diagnostics?.run_audit_id
      setLastGeneratedRunAuditId(runAuditId)
      setSelectedForecastRunAuditId(runAuditId)

      const generatedForProduct = (generated.forecasts ?? [])
        .filter((f) => Number(f.product_id) === Number(generatedProductId))
        .sort((a, b) => new Date(a.period).getTime() - new Date(b.period).getTime())

      const firstForecastPoint = generatedForProduct.length > 0 ? generatedForProduct[0] : undefined
      if (firstForecastPoint?.period && runAuditId != null) {
        try {
          await forecastService.createConsensus({
            forecast_run_audit_id: runAuditId,
            product_id: generatedProductId,
            period: firstForecastPoint.period,
            baseline_qty: Number(firstForecastPoint.predicted_qty ?? 0),
            sales_override_qty: 0,
            marketing_uplift_qty: 0,
            finance_adjustment_qty: 0,
            constraint_cap_qty: null,
            status: 'draft',
            notes: 'Auto-created from latest forecast generation',
          })
          toast.success('Forecast generated and new consensus draft created')
        } catch {
          toast.success('Forecast generated successfully')
        }
      } else {
        toast.success('Forecast generated successfully')
      }

      setShowGenerate(false)
      setSelectedProductId(generatedProductId)
      setLastGeneratedProductId(generatedProductId)
      await load()
      setActiveStage('stage4')
    } catch {
      // handled
    } finally {
      setGenerating(false)
    }
  }

  const groupedForecasts = Array.from(
    forecasts.reduce((acc, f) => {
      const key = f.product_id
      if (!acc.has(key)) acc.set(key, [])
      acc.get(key)!.push(f)
      return acc
    }, new Map<number, Forecast[]>()),
  ).map(([product_id, items]) => {
    const sorted = [...items].sort((a, b) => new Date(a.period).getTime() - new Date(b.period).getTime())
    const sample = sorted[0]
    return {
      product_id,
      product_name: sample?.product?.name ?? `#${product_id}`,
      count: sorted.length,
      period_from: sorted[0]?.period,
      period_to: sorted[sorted.length - 1]?.period,
      latest_model: sorted[sorted.length - 1]?.model_type,
    }
  })
    .sort((a, b) => a.product_name.localeCompare(b.product_name))

  const groupedForecastModels = Array.from(
    forecasts.reduce((acc, f) => {
      const key = `${f.product_id}::${f.model_type}`
      if (!acc.has(key)) acc.set(key, [])
      acc.get(key)!.push(f)
      return acc
    }, new Map<string, Forecast[]>()),
  ).map(([key, items]) => {
    const [productIdRaw, modelType] = key.split('::')
    const productId = Number(productIdRaw)
    const sorted = [...items].sort((a, b) => new Date(a.period).getTime() - new Date(b.period).getTime())
    const sample = sorted[0]
    return {
      product_id: productId,
      model_type: modelType,
      product_name: sample?.product?.name ?? `#${productId}`,
      count: sorted.length,
      period_from: sorted[0]?.period,
      period_to: sorted[sorted.length - 1]?.period,
    }
  }).sort((a, b) => {
    const byProduct = a.product_name.localeCompare(b.product_name)
    if (byProduct !== 0) return byProduct
    return a.model_type.localeCompare(b.model_type)
  })

  const handleDeleteForecastGroup = async (productId: number, productName: string) => {
    if (!confirm(`Delete all forecast results for ${productName}? This action cannot be undone.`)) return
    try {
      const res = await forecastService.deleteResultsByProduct(productId)
      toast.success(
        `Deleted ${res.forecasts_deleted} forecast result(s) and ${res.consensus_deleted} consensus record(s) for ${productName}`,
      )
      await load()
    } catch {
      // handled
    }
  }

  const handleViewForecastResult = (productId: number, modelType: string) => {
    const viewRunAuditId = [...forecasts]
      .filter((f) => (
        Number(f.product_id) === Number(productId)
        && f.model_type === modelType
        && f.run_audit_id != null
      ))
      .sort((a, b) => new Date(a.period).getTime() - new Date(b.period).getTime())
      .map((f) => f.run_audit_id)
      .filter((id): id is number => typeof id === 'number')
      .slice(-1)[0]

    setSelectedProductId(productId)
    setLastGeneratedProductId(productId)
    setSelectedForecastRunAuditId(viewRunAuditId)
    setSelectedForecastModelType(modelType)
    setActiveStage('stage4')
  }

  const handlePromoteForecastResult = async (productId: number, modelType: string) => {
    if (!confirm(`Promote model ${modelType.replace(/_/g, ' ')} for product #${productId} to Demand Plan?`)) return
    try {
      const res = await forecastService.promoteForecastResults({
        product_id: productId,
        selected_model: modelType as ForecastModelType,
        horizon_months: form.horizon_months ?? 6,
      })
      toast.success(`Promoted ${res.records_promoted} period(s) to Demand Plan`)
    } catch {
      // handled
    }
  }

  const getSeedBaselineFromForecast = (productId: number, period: string): number => {
    const monthKey = period.slice(0, 7)
    const pointsForProduct = [...latestGeneratedForecasts, ...forecasts]
      .filter((f) => Number(f.product_id) === Number(productId))
      .sort((a, b) => new Date(a.period).getTime() - new Date(b.period).getTime())

    const exactMonthPoint = pointsForProduct.find((f) => f.period.slice(0, 7) === monthKey)
    if (exactMonthPoint?.predicted_qty != null) return Number(exactMonthPoint.predicted_qty)

    // Fallback to the nearest available future forecast point for the same product.
    const nextPoint = pointsForProduct.find((f) => new Date(f.period).getTime() >= new Date(period).getTime())
    if (nextPoint?.predicted_qty != null) return Number(nextPoint.predicted_qty)

    // Last fallback: latest available predicted quantity.
    const latestPoint = pointsForProduct.length > 0 ? pointsForProduct[pointsForProduct.length - 1] : null
    if (latestPoint?.predicted_qty != null) return Number(latestPoint.predicted_qty)

    return 0
  }

  const openConsensusModal = (mode: 'fresh' | 'edit' = 'fresh') => {
    const targetProductId = chartProductId ?? selectedProductId
    if (!targetProductId) {
      toast.error('Select a product first')
      return
    }

    setConsensusModalMode(mode)

    const hasFreshGeneratedForecast =
      mode === 'fresh'
      && Number(targetProductId) === Number(lastGeneratedProductId)
      && latestGeneratedForecasts.length > 0

    if (hasFreshGeneratedForecast) {
      const generatedForProduct = [...latestGeneratedForecasts]
        .filter((f) => Number(f.product_id) === Number(targetProductId))
        .sort((a, b) => new Date(a.period).getTime() - new Date(b.period).getTime())

      const basePoint = generatedForProduct.length > 0 ? generatedForProduct[0] : undefined
      const period = basePoint?.period ?? new Date().toISOString().slice(0, 10)
      const baseline = basePoint?.predicted_qty != null
        ? Number(basePoint.predicted_qty)
        : getSeedBaselineFromForecast(targetProductId, period)

      setConsensusForm({
        period,
        baseline_qty: baseline,
        sales_override_qty: 0,
        marketing_uplift_qty: 0,
        finance_adjustment_qty: 0,
        constraint_cap_qty: '',
        status: 'draft',
        notes: '',
      })
      setShowConsensusModal(true)
      return
    }

    const sortedExisting = [...selectedConsensus]
      .filter((c) => Number(c.product_id) === Number(targetProductId))
      .sort((a, b) => {
        const byPeriod = new Date(a.period).getTime() - new Date(b.period).getTime()
        if (byPeriod !== 0) return byPeriod
        return a.version - b.version
      })
    const existing = sortedExisting.length > 0 ? sortedExisting[sortedExisting.length - 1] : undefined
    const defaultPeriod = existing?.period ?? new Date().toISOString().slice(0, 10)
    const seededBaseline = existing?.baseline_qty ?? getSeedBaselineFromForecast(targetProductId, defaultPeriod)

    setConsensusForm({
      period: defaultPeriod,
      baseline_qty: seededBaseline,
      sales_override_qty: existing?.sales_override_qty ?? 0,
      marketing_uplift_qty: existing?.marketing_uplift_qty ?? 0,
      finance_adjustment_qty: existing?.finance_adjustment_qty ?? 0,
      constraint_cap_qty: existing?.constraint_cap_qty != null ? String(existing.constraint_cap_qty) : '',
      status: existing?.status ?? 'draft',
      notes: existing?.notes ?? '',
    })
    setShowConsensusModal(true)
  }

  const handleSaveConsensus = async () => {
    const targetProductId = chartProductId ?? selectedProductId
    if (!targetProductId) {
      toast.error('Select a product first')
      return
    }
    if (!consensusForm.period) {
      toast.error('Period is required')
      return
    }
    if (!activeRunAuditId) {
      toast.error('No forecast run selected for consensus')
      return
    }

    const samePeriodRows = [...consensusRecords]
      .filter((c) => (
        Number(c.product_id) === Number(targetProductId)
        && Number(c.forecast_run_audit_id) === Number(activeRunAuditId)
        && c.period === consensusForm.period
      ))
      .sort((a, b) => b.version - a.version)
    const samePeriodLatest = samePeriodRows.length > 0 ? samePeriodRows[0] : undefined

    setSavingConsensus(true)
    try {
      const payload = {
        baseline_qty: Number(consensusForm.baseline_qty || 0),
        sales_override_qty: Number(consensusForm.sales_override_qty || 0),
        marketing_uplift_qty: Number(consensusForm.marketing_uplift_qty || 0),
        finance_adjustment_qty: Number(consensusForm.finance_adjustment_qty || 0),
        constraint_cap_qty: consensusForm.constraint_cap_qty === '' ? null : Number(consensusForm.constraint_cap_qty),
        status: consensusForm.status,
        notes: consensusForm.notes || undefined,
      }

      if (consensusModalMode === 'edit' && samePeriodLatest) {
        await forecastService.updateConsensus(samePeriodLatest.id, payload)
        toast.success('Consensus updated')
      } else {
        await forecastService.createConsensus({
          forecast_run_audit_id: activeRunAuditId,
          product_id: targetProductId,
          period: consensusForm.period,
          ...payload,
        })
        toast.success('Consensus created')
      }
      setShowConsensusModal(false)
      await load()
    } catch {
      // handled by interceptors
    } finally {
      setSavingConsensus(false)
    }
  }

  const handleApproveConsensus = async () => {
    if (!latestConsensus) return
    setSavingConsensus(true)
    try {
      await forecastService.approveConsensus(latestConsensus.id, { notes: 'Approved from Forecasting UI' })
      toast.success('Consensus approved')
      await load()
    } catch {
      // handled by interceptors
    } finally {
      setSavingConsensus(false)
    }
  }

  const avgMape = accuracy.length > 0
    ? accuracy.reduce((s, a) => s + a.mape, 0) / accuracy.length
    : 0

  const draftPreConsensus = Math.max(
    0,
    Number(consensusForm.baseline_qty || 0)
      + Number(consensusForm.sales_override_qty || 0)
      + Number(consensusForm.marketing_uplift_qty || 0)
      + Number(consensusForm.finance_adjustment_qty || 0),
  )
  const draftCap = consensusForm.constraint_cap_qty === ''
    ? null
    : Number(consensusForm.constraint_cap_qty)
  const draftFinalConsensus = draftCap == null
    ? draftPreConsensus
    : Math.max(0, Math.min(draftPreConsensus, draftCap))

  const selectedConsensus = [...consensusRecords]
    .filter((c) => {
      const productMatch = !chartProductId || Number(c.product_id) === Number(chartProductId)
      if (!productMatch) return false
      if (!activeRunAuditId) return true
      return Number(c.forecast_run_audit_id) === Number(activeRunAuditId)
    })
    .sort((a, b) => {
      const byPeriod = new Date(a.period).getTime() - new Date(b.period).getTime()
      if (byPeriod !== 0) return byPeriod
      return a.version - b.version
    })

  const latestConsensus = selectedConsensus.length > 0
    ? selectedConsensus[selectedConsensus.length - 1]
    : null

  const selectedProductAccuracy = chartProductId
    ? accuracy.filter((a) => Number(a.product_id) === Number(chartProductId))
    : accuracy

  const bestModelByScore = selectedProductAccuracy.length > 0
    ? selectedProductAccuracy.reduce((best, current) => {
      const bestScore = best.mape + (best.wape * 0.25)
      const currentScore = current.mape + (current.wape * 0.25)
      return currentScore < bestScore ? current : best
    }, selectedProductAccuracy[0])
    : null

  const bestModelByScoreOverall = accuracy.length > 0
    ? accuracy.reduce((best, current) => {
      const bestScore = best.mape + (best.wape * 0.25)
      const currentScore = current.mape + (current.wape * 0.25)
      return currentScore < bestScore ? current : best
    }, accuracy[0])
    : null

  const bestModelDisplay = bestModelByScore ?? bestModelByScoreOverall

  const bestModel = accuracy.length > 0
    ? accuracy.reduce((best, a) => a.mape < best.mape ? a : best, accuracy[0])
    : null

  const historyChartData = historyPlans.map((p) => ({
    period: formatPeriod(p.period),
    actual_qty: p.actual_qty != null ? Number(p.actual_qty) : null,
  }))

  const historicalSeries = historyPlans.map((p) => ({
    period: p.period,
    // Historical line should represent true history only.
    // Keep this strictly to actuals to avoid plotting forecast/consensus as history points.
    historical_qty: p.actual_qty != null ? Number(p.actual_qty) : null,
  }))

  const forecastPoints = [...latestGeneratedForecasts, ...forecasts]
    .filter((f) => {
      const productMatch = !chartProductId || Number(f.product_id) === Number(chartProductId)
      const modelMatch = !selectedForecastModelType || f.model_type === selectedForecastModelType
      return productMatch && modelMatch
    })
    .sort((a, b) => new Date(a.period).getTime() - new Date(b.period).getTime())

  const latestConsensusPrediction = latestConsensus
    ? [...forecastPoints]
      .reverse()
      .find((p) => p.period.slice(0, 7) === latestConsensus.period.slice(0, 7) && p.predicted_qty != null)
    : undefined

  const latestConsensusVariance = (latestConsensus && latestConsensusPrediction?.predicted_qty != null)
    ? Number(latestConsensus.final_consensus_qty) - Number(latestConsensusPrediction.predicted_qty)
    : null

  const latestConsensusVariancePct = (latestConsensusVariance != null
    && latestConsensusPrediction?.predicted_qty != null
    && Number(latestConsensusPrediction.predicted_qty) !== 0)
    ? (latestConsensusVariance / Number(latestConsensusPrediction.predicted_qty)) * 100
    : null

  const latestConsensusDriverNet = latestConsensus
    ? Number(latestConsensus.sales_override_qty)
      + Number(latestConsensus.marketing_uplift_qty)
      + Number(latestConsensus.finance_adjustment_qty)
    : null

  const latestConsensusCapImpact = latestConsensus
    ? Number(latestConsensus.final_consensus_qty) - Number(latestConsensus.pre_consensus_qty)
    : null

  const dedupedForecastPoints = Array.from(
    forecastPoints.reduce((acc, point) => {
      const monthKey = point.period.slice(0, 7)
      if (!acc.has(monthKey)) acc.set(monthKey, point)
      return acc
    }, new Map<string, Forecast>()),
  ).map(([, v]) => v)

  const forecastPointRows = dedupedForecastPoints.slice(-12)

  const forecastModelUsed = dedupedForecastPoints.length > 0
    ? dedupedForecastPoints[dedupedForecastPoints.length - 1].model_type.replace(/_/g, ' ')
    : null

  const chartDataMap = new Map<string, {
    periodRaw: string
    historical_qty: number | null
    prediction_qty: number | null
    lower_bound: number | null
    upper_bound: number | null
    consensus_qty: number | null
  }>()

  historicalSeries.forEach((h) => {
    const key = h.period.slice(0, 7)
    const current = chartDataMap.get(key)
    chartDataMap.set(key, {
      periodRaw: current?.periodRaw ?? h.period,
      historical_qty: h.historical_qty,
      prediction_qty: current?.prediction_qty ?? null,
      lower_bound: current?.lower_bound ?? null,
      upper_bound: current?.upper_bound ?? null,
      consensus_qty: current?.consensus_qty ?? null,
    })
  })

  dedupedForecastPoints.forEach((f) => {
    const key = f.period.slice(0, 7)
    const current = chartDataMap.get(key)
    chartDataMap.set(key, {
      periodRaw: f.period,
      historical_qty: current?.historical_qty ?? null,
      prediction_qty: f.predicted_qty != null ? Number(f.predicted_qty) : null,
      lower_bound: f.lower_bound != null ? Number(f.lower_bound) : null,
      upper_bound: f.upper_bound != null ? Number(f.upper_bound) : null,
      consensus_qty: current?.consensus_qty ?? null,
    })
  })

  const consensusSeries = Array.from(
    selectedConsensus.reduce((acc, c) => {
      const monthKey = c.period.slice(0, 7)
      // Keep latest version for each period.
      if (!acc.has(monthKey) || c.version >= (acc.get(monthKey)?.version ?? 0)) {
        acc.set(monthKey, c)
      }
      return acc
    }, new Map<string, ForecastConsensus>()),
  ).map(([, v]) => v)

  consensusSeries.forEach((c) => {
    const key = c.period.slice(0, 7)
    const current = chartDataMap.get(key)
    chartDataMap.set(key, {
      periodRaw: current?.periodRaw ?? c.period,
      historical_qty: current?.historical_qty ?? null,
      prediction_qty: current?.prediction_qty ?? null,
      lower_bound: current?.lower_bound ?? null,
      upper_bound: current?.upper_bound ?? null,
      consensus_qty: c.final_consensus_qty != null ? Number(c.final_consensus_qty) : null,
    })
  })

  const chartData = Array.from(chartDataMap.values())
    .sort((a, b) => new Date(a.periodRaw).getTime() - new Date(b.periodRaw).getTime())
    .map((row) => ({
      period: formatPeriod(row.periodRaw),
      historical_qty: row.historical_qty,
      prediction_qty: row.prediction_qty,
      lower_bound: row.lower_bound,
      upper_bound: row.upper_bound,
      consensus_qty: row.consensus_qty,
    }))

  const accuracyChartData = [...accuracy]
    .sort((a, b) => a.mape - b.mape)
    .map((a) => ({
      model: a.model_type.replace(/_/g, ' '),
      mape: a.mape,
      wape: a.wape,
      hit_rate: a.hit_rate,
    }))

  const stageEnabled: Record<ForecastStageKey, boolean> = {
    stage1: true,
    stage2: Boolean(selectedProductId),
    stage4: forecasts.length > 0,
    stage5: true,
  }

  const stageStatus = (stage: ForecastStageKey): 'complete' | 'active' | 'locked' | 'ready' => {
    if (activeStage === stage) return 'active'
    if (!stageEnabled[stage]) return 'locked'
    if (stage === 'stage1' && selectedProductId) return 'complete'
    if (stage === 'stage2' && selectedProductId && form.model_type && form.horizon_months) return 'complete'
    if (stage === 'stage4' && forecasts.length > 0) return 'complete'
    if (stage === 'stage5') return 'ready'
    return 'ready'
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">AI Forecasting</h1>
          <p className="text-sm text-gray-500 mt-0.5">ML-powered demand forecasting</p>
        </div>
      </div>

      <StageTabs
        stages={FORECAST_STAGES}
        activeStage={activeStage}
        stageEnabled={stageEnabled}
        getStatus={stageStatus}
        onSelect={setActiveStage}
      />

      {activeStage === 'stage1' && (
      <Card title="Step 1 · Select Product & Review Historical Demand" subtitle="View actual demand before generating forecast">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Product</label>
            <select
              value={selectedProductId ?? ''}
              onChange={(e) => setSelectedProductId(e.target.value ? Number(e.target.value) : undefined)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a product</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">History Range</label>
            <select
              value={historyRangeMonths}
              onChange={(e) => setHistoryRangeMonths(Number(e.target.value))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={6}>Last 6 months</option>
              <option value={12}>Last 12 months</option>
              <option value={24}>Last 24 months</option>
            </select>
          </div>
        </div>

        {!selectedProductId ? (
          <p className="text-sm text-gray-500">Select a product to preview historical demand values.</p>
        ) : historyLoading ? (
          <SkeletonTable rows={5} cols={4} />
        ) : historyChartData.length === 0 ? (
          <p className="text-sm text-gray-500">No historical demand data found for this product and range.</p>
        ) : (
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={historyChartData} margin={{ top: 16, right: 24, left: 8, bottom: 12 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="period" tickMargin={8} />
                <YAxis width={56} />
                <Tooltip formatter={(v) => (typeof v === 'number' ? formatNumber(v) : '—')} />
                <Legend />
                <Line type="monotone" dataKey="actual_qty" name="Actual Qty" stroke="#16a34a" strokeWidth={2} dot={false} connectNulls={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>
      )}

      {activeStage === 'stage2' && (
      <Card title="Step 2 · Model Setup" subtitle="Configure model inputs for forecast generation">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
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
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Forecast Horizon (months)</label>
            <input type="number" min={1} max={24} value={form.horizon_months ?? 6}
              onChange={(e) => setForm((f) => ({ ...f, horizon_months: Number(e.target.value) }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button icon={<Play />} loading={generating} onClick={handleGenerate} disabled={!selectedProductId || !canGenerate}>
            Generate Forecast
          </Button>
        </div>
      </Card>
      )}

      {activeStage === 'stage4' && driftAlerts.length > 0 && (
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

      {activeStage === 'stage4' && (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard title="Avg MAPE" value={formatPercent(avgMape)} icon={<Target className="h-4 w-4" />} color="blue"
          subtitle="Mean Absolute % Error" />
        <KPICard title="Best Model (Score)" value={bestModelDisplay?.model_type?.replace(/_/g, ' ') ?? '—'}
          icon={<Brain className="h-4 w-4" />} color="emerald"
          subtitle={bestModelDisplay
            ? `Score: ${(bestModelDisplay.mape + (bestModelDisplay.wape * 0.25)).toFixed(2)} · Product #${bestModelDisplay.product_id}`
            : undefined} />
        <KPICard title="Forecasts Generated" value={forecasts.length}
          icon={<TrendingUp className="h-4 w-4" />} color="purple" />
        <KPICard title="Models Evaluated" value={accuracy.length}
          icon={<Brain className="h-4 w-4" />} color="indigo" />
      </div>
      )}

      {activeStage === 'stage4' && (
      <Card title="Consensus Quantity Snapshot" subtitle="Latest cross-functional agreed demand value">
        {!latestConsensus ? (
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-gray-500">No consensus records available for selected product.</p>
            <Button size="sm" variant="outline" icon={<Edit3 className="h-4 w-4" />} onClick={() => openConsensusModal('fresh')}>
              Create
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <div>
                <p className="text-xs text-gray-500">Period</p>
                <p className="text-sm font-medium text-gray-900">{formatPeriod(latestConsensus.period)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Final Consensus</p>
                <p className="text-sm font-semibold text-emerald-700">{formatNumber(latestConsensus.final_consensus_qty)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Pre-Consensus</p>
                <p className="text-sm text-gray-900">{formatNumber(latestConsensus.pre_consensus_qty)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Status</p>
                <p className="text-sm text-gray-900 capitalize">{latestConsensus.status}</p>
              </div>
            </div>
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
              <p className="text-xs font-medium text-amber-900 mb-1">Variance Explanation (Latest Period)</p>
              {latestConsensusPrediction?.predicted_qty == null ? (
                <p className="text-xs text-amber-800">
                  No matching forecast prediction found for this consensus period.
                </p>
              ) : (
                <div className="space-y-1 text-xs text-amber-900">
                  <p>
                    Consensus ({formatNumber(Number(latestConsensus.final_consensus_qty))})
                    {' '}− Prediction ({formatNumber(Number(latestConsensusPrediction.predicted_qty))})
                    {' '}= <span className="font-semibold">{latestConsensusVariance != null ? formatNumber(latestConsensusVariance) : '—'}</span>
                    {latestConsensusVariancePct != null ? ` (${formatPercent(latestConsensusVariancePct)})` : ''}
                  </p>
                  <p>
                    Driver breakdown:
                    {' '}Baseline {formatNumber(Number(latestConsensus.baseline_qty))}
                    {' '}+ Sales {formatNumber(Number(latestConsensus.sales_override_qty))}
                    {' '}+ Marketing {formatNumber(Number(latestConsensus.marketing_uplift_qty))}
                    {' '}+ Finance {formatNumber(Number(latestConsensus.finance_adjustment_qty))}
                    {' '}= Pre {formatNumber(Number(latestConsensus.pre_consensus_qty))}
                  </p>
                  <p>
                    Net overrides vs baseline: <span className="font-semibold">{latestConsensusDriverNet != null ? formatNumber(latestConsensusDriverNet) : '—'}</span>
                    {' '}· Cap impact: <span className="font-semibold">{latestConsensusCapImpact != null ? formatNumber(latestConsensusCapImpact) : '—'}</span>
                  </p>
                </div>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="outline" icon={<Edit3 className="h-4 w-4" />} onClick={() => openConsensusModal('fresh')}>
                New Version
              </Button>
              <Button
                size="sm"
                icon={<Check className="h-4 w-4" />}
                loading={savingConsensus}
                onClick={handleApproveConsensus}
                disabled={!canApproveConsensus || latestConsensus.status === 'approved' || latestConsensus.status === 'frozen'}
              >
                Approve
              </Button>
            </div>
            {!canApproveConsensus && (
              <p className="text-xs text-amber-700">
                Approve requires role: admin, executive, or sop_coordinator.
              </p>
            )}
            {(latestConsensus.status === 'approved' || latestConsensus.status === 'frozen') && (
              <p className="text-xs text-gray-500">
                This consensus is already {latestConsensus.status}.
              </p>
            )}
          </div>
        )}
      </Card>
      )}

      {activeStage === 'stage4' && (
      <Card title="Consensus History" subtitle="Latest consensus versions for selected product">
        {selectedConsensus.length === 0 ? (
          <p className="text-sm text-gray-500">No consensus history yet for selected product.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {['Period', 'Version', 'Pre-Consensus', 'Final Consensus', 'Status', 'Approved At'].map((h) => (
                    <th key={h} className="text-left pb-3 text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {[...selectedConsensus].reverse().slice(0, 10).map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="py-2.5 text-gray-900">{formatPeriod(c.period)}</td>
                    <td className="py-2.5 text-gray-700">v{c.version}</td>
                    <td className="py-2.5 text-gray-700">{formatNumber(c.pre_consensus_qty)}</td>
                    <td className="py-2.5 font-medium text-gray-900">{formatNumber(c.final_consensus_qty)}</td>
                    <td className="py-2.5">
                      <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full capitalize">{c.status}</span>
                    </td>
                    <td className="py-2.5 text-gray-600">{c.approved_at ? new Date(c.approved_at).toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      )}

      {activeStage === 'stage4' && (
      <Card title="Best Model Recommendation" subtitle="Composite score = MAPE + 0.25 × WAPE">
        {bestModelDisplay ? (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            <span className="font-semibold">Best model:</span> {bestModelDisplay.model_type.replace(/_/g, ' ')} ·
            {' '}Score {(bestModelDisplay.mape + (bestModelDisplay.wape * 0.25)).toFixed(2)} ·
            {' '}Product #{bestModelDisplay.product_id}
            {!bestModelByScore && bestModelByScoreOverall ? ' (using overall data fallback)' : ''}
          </div>
        ) : (
          <p className="text-sm text-gray-500">Accuracy appears after actual demand is recorded for forecasted months.</p>
        )}
      </Card>
      )}

      {activeStage === 'stage4' && selectedForecastModelType && (
      <Card title="Viewing Filter" subtitle="Filtered from Manage Forecast Results">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-gray-700">
            Showing forecast curve for model:{' '}
            <span className="font-semibold text-gray-900">{selectedForecastModelType.replace(/_/g, ' ')}</span>
          </p>
          <Button variant="outline" onClick={() => setSelectedForecastModelType(undefined)}>
            Show all models
          </Button>
        </div>
      </Card>
      )}

      {activeStage === 'stage4' && (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card
          title="Step 4 · Forecast Curve"
          subtitle={`Historical + prediction + consensus with confidence interval${forecastModelUsed ? ` · Model: ${forecastModelUsed}` : ''}`}
        >
          {bestModelDisplay && (
            <div className="mb-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
              <span className="font-semibold">Best Model (Score):</span>{' '}
              {bestModelDisplay.model_type.replace(/_/g, ' ')} · Score {(bestModelDisplay.mape + (bestModelDisplay.wape * 0.25)).toFixed(2)}
            </div>
          )}
          {chartData.length === 0 ? (
            <div className="text-center py-10 text-gray-400 text-sm">Select a product and generate forecast to visualize trend</div>
          ) : (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 16, right: 16, left: 0, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="period" tickMargin={8} />
                  <YAxis width={56} />
                  <Tooltip formatter={(v) => (typeof v === 'number' ? formatNumber(v) : '—')} />
                  <Legend />
                  <Line type="monotone" dataKey="upper_bound" stroke="#93c5fd" strokeWidth={1.5} strokeDasharray="4 4" dot={false} name="Confidence Upper" connectNulls={false} />
                  <Line type="monotone" dataKey="lower_bound" stroke="#93c5fd" strokeWidth={1.5} strokeDasharray="4 4" dot={false} name="Confidence Lower" connectNulls={false} />
                  <Line type="monotone" dataKey="historical_qty" stroke="#16a34a" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 4 }} name="Historical" connectNulls={false} />
                  <Line type="monotone" dataKey="prediction_qty" stroke="#2563eb" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 4 }} name="Prediction" connectNulls={false} />
                  <Line type="monotone" dataKey="consensus_qty" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 4 }} name="Consensus" connectNulls={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

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
      )}

      {activeStage === 'stage4' && (
      <Card title="Recent Forecast Results" subtitle="Latest generated records by product">
        {loading ? (
          <SkeletonTable rows={6} cols={4} />
        ) : forecasts.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <p className="text-sm">No forecast results available yet</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {['Product', 'Periods', 'Latest Model', 'Count'].map((h) => (
                    <th key={h} className="text-left pb-3 text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {groupedForecasts.slice(0, 10).map((g) => (
                  <tr key={`stage4-${g.product_id}`} className="hover:bg-gray-50">
                    <td className="py-2.5 font-medium text-gray-900 pr-3">{g.product_name}</td>
                    <td className="py-2.5 text-gray-600 pr-3">
                      {g.period_from && g.period_to
                        ? `${formatPeriod(g.period_from)} → ${formatPeriod(g.period_to)}`
                        : '—'}
                    </td>
                    <td className="py-2.5 pr-3">
                      <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
                        {g.latest_model?.replace(/_/g, ' ') ?? '—'}
                      </span>
                    </td>
                    <td className="py-2.5 tabular-nums pr-3">{g.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      )}

      {activeStage === 'stage4' && (
      <Card title="Forecast Point Details" subtitle="Historical and predicted points for selected/generated product">
        {forecastPointRows.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <p className="text-sm">No forecast points available for this product yet</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {['Period', 'Predicted', 'Lower', 'Upper'].map((h) => (
                    <th key={h} className="text-left pb-3 text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {forecastPointRows.map((p) => (
                  <tr key={`point-${p.id}`} className="hover:bg-gray-50">
                    <td className="py-2.5 text-gray-900">{formatPeriod(p.period)}</td>
                    <td className="py-2.5 text-gray-700">{formatNumber(Number(p.predicted_qty ?? 0))}</td>
                    <td className="py-2.5 text-gray-600">{p.lower_bound != null ? formatNumber(Number(p.lower_bound)) : '—'}</td>
                    <td className="py-2.5 text-gray-600">{p.upper_bound != null ? formatNumber(Number(p.upper_bound)) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      )}

      {activeStage === 'stage5' && (
      <Card title="Step 5 · Manage Forecast Results" subtitle="All executed models, ordered by product">
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
                  {['Product', 'Model', 'Periods', 'Count', 'Actions'].map((h) => (
                    <th key={h} className="text-left pb-3 text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {groupedForecastModels.slice(0, 50).map((g) => (
                  <tr key={`${g.product_id}-${g.model_type}`} className="hover:bg-gray-50">
                    <td className="py-2.5 font-medium text-gray-900 pr-3">{g.product_name}</td>
                    <td className="py-2.5 pr-3">
                      <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
                        {g.model_type?.replace(/_/g, ' ') ?? '—'}
                      </span>
                    </td>
                    <td className="py-2.5 text-gray-600 pr-3">
                      {g.period_from && g.period_to
                        ? `${formatPeriod(g.period_from)} → ${formatPeriod(g.period_to)}`
                        : '—'}
                    </td>
                    <td className="py-2.5 tabular-nums pr-3">{g.count}</td>
                    <td className="py-2.5">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleViewForecastResult(g.product_id, g.model_type)}
                          className="p-1.5 rounded text-gray-500 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                          title="View this forecast in Forecast View"
                        >
                          <Eye className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => handlePromoteForecastResult(g.product_id, g.model_type)}
                          className="p-1.5 rounded text-gray-500 hover:text-emerald-600 hover:bg-emerald-50 transition-colors"
                          title="Promote this forecast model to Demand Plan"
                          disabled={!canGenerate}
                        >
                          <Upload className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => handleDeleteForecastGroup(g.product_id, g.product_name)}
                          className="p-1.5 rounded text-gray-500 hover:text-red-600 hover:bg-red-50 transition-colors"
                          title="Delete all forecast results for this product"
                          disabled={!canGenerate}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      )}

      {(activeStage !== 'stage1' && !selectedProductId) && (
        <Card title="Stage Locked" subtitle="Select a product in Stage 1 first">
          <p className="text-sm text-gray-500">Please go to Stage 1 and select a product to continue.</p>
        </Card>
      )}

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

      <Modal
        isOpen={showConsensusModal}
        onClose={() => setShowConsensusModal(false)}
        title="Consensus Quantity"
        footer={
          <>
            <Button variant="outline" onClick={() => setShowConsensusModal(false)}>Cancel</Button>
            <Button loading={savingConsensus} onClick={handleSaveConsensus} disabled={!canGenerate}>Save</Button>
          </>
        }
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Period *</label>
            <input
              type="date"
              value={consensusForm.period}
              onChange={(e) => setConsensusForm((prev) => ({ ...prev, period: e.target.value }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Status</label>
            <select
              value={consensusForm.status}
              onChange={(e) => setConsensusForm((prev) => ({ ...prev, status: e.target.value as ForecastConsensus['status'] }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
            >
              <option value="draft">draft</option>
              <option value="proposed">proposed</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Baseline Qty</label>
            <input
              type="number"
              value={consensusForm.baseline_qty}
              onChange={(e) => setConsensusForm((prev) => ({ ...prev, baseline_qty: Number(e.target.value) }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Sales Override</label>
            <input
              type="number"
              value={consensusForm.sales_override_qty}
              onChange={(e) => setConsensusForm((prev) => ({ ...prev, sales_override_qty: Number(e.target.value) }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Marketing Uplift</label>
            <input
              type="number"
              value={consensusForm.marketing_uplift_qty}
              onChange={(e) => setConsensusForm((prev) => ({ ...prev, marketing_uplift_qty: Number(e.target.value) }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Finance Adjustment</label>
            <input
              type="number"
              value={consensusForm.finance_adjustment_qty}
              onChange={(e) => setConsensusForm((prev) => ({ ...prev, finance_adjustment_qty: Number(e.target.value) }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Constraint Cap (optional)</label>
            <input
              type="number"
              value={consensusForm.constraint_cap_qty}
              onChange={(e) => setConsensusForm((prev) => ({ ...prev, constraint_cap_qty: e.target.value }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
            />
          </div>
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Notes</label>
            <textarea
              rows={3}
              value={consensusForm.notes}
              onChange={(e) => setConsensusForm((prev) => ({ ...prev, notes: e.target.value }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
            />
          </div>
          <div className="md:col-span-2 rounded-lg border border-blue-100 bg-blue-50 px-3 py-2">
            <p className="text-xs font-medium text-blue-800 mb-1">Live Calculation Preview</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
              <p className="text-blue-900">
                Pre-Consensus: <span className="font-semibold">{formatNumber(draftPreConsensus)}</span>
              </p>
              <p className="text-blue-900">
                Final Consensus: <span className="font-semibold">{formatNumber(draftFinalConsensus)}</span>
              </p>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  )
}
