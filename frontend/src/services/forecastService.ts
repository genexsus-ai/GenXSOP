import api from './api'
import type {
  Forecast,
  GenerateForecastRequest,
  ForecastAccuracy,
  PaginatedResponse,
  GenerateForecastResponse,
  ForecastDiagnostics,
} from '@/types'

/**
 * Forecasting API normalization
 *
 * Backend endpoints in this repo currently return:
 * - POST /forecasting/generate -> { product_id, model_type, horizon, forecasts: [...] }
 * - GET  /forecasting/results  -> Forecast[] (array)
 * - GET  /forecasting/accuracy -> [{ model_type, avg_mape, sample_count }]
 *
 * But the React UI expects:
 * - generateForecast() -> Forecast[]
 * - getResults() -> PaginatedResponse<Forecast>
 * - getAccuracy() -> ForecastAccuracy[] (with mape/bias/rmse/mae/hit_rate/period_count)
 *
 * So we normalize responses here to keep the UI stable.
 */

type AccuracyResponseItem = {
  model_type: string
  avg_mape: number
  sample_count: number
}

export type GenerateForecastResult = {
  forecasts: Forecast[]
  diagnostics?: ForecastDiagnostics
}

function normalizeForecastsArray(items: Forecast[]): PaginatedResponse<Forecast> {
  return {
    items,
    total: items.length,
    page: 1,
    page_size: items.length,
    total_pages: 1,
  }
}

function normalizeAccuracy(items: AccuracyResponseItem[]): ForecastAccuracy[] {
  return items.map((i) => ({
    product_id: 0,
    model_type: i.model_type,
    mape: i.avg_mape,
    wape: 0,
    bias: 0,
    rmse: 0,
    mae: 0,
    hit_rate: 0,
    period_count: i.sample_count,
    sample_count: i.sample_count,
    avg_mape: i.avg_mape,
  }))
}

export const forecastService = {
  async generateForecast(data: GenerateForecastRequest): Promise<GenerateForecastResult> {
    const res = await api.post<GenerateForecastResponse>('/forecasting/generate', null, {
      params: {
        product_id: data.product_id,
        horizon: data.horizon_months ?? 6,
        model_type: data.model_type,
      },
    })

    const modelType = (res.data.model_type ?? data.model_type ?? 'moving_average') as Forecast['model_type']
    const forecasts = (res.data.forecasts ?? []).map((f, idx) => ({
      id: -1 * (idx + 1),
      product_id: res.data.product_id,
      model_type: (f.model_type ?? modelType) as Forecast['model_type'],
      period: f.period,
      predicted_qty: f.predicted_qty,
      lower_bound: f.lower_bound ?? undefined,
      upper_bound: f.upper_bound ?? undefined,
      confidence: f.confidence ?? undefined,
      mape: f.mape ?? undefined,
      rmse: undefined,
      model_version: undefined,
      training_date: undefined,
      created_at: new Date().toISOString(),
      product: undefined,
      selection_reason: res.data.diagnostics?.selection_reason,
      advisor_confidence: res.data.diagnostics?.advisor_confidence,
      advisor_enabled: res.data.diagnostics?.advisor_enabled,
      fallback_used: res.data.diagnostics?.fallback_used,
    }))

    return { forecasts, diagnostics: res.data.diagnostics }
  },

  async getResults(params?: { product_id?: number; model_type?: string; page?: number; page_size?: number }): Promise<PaginatedResponse<Forecast>> {
    // Backend currently returns Forecast[] (array). Normalize to PaginatedResponse.
    const res = await api.get<Forecast[] | PaginatedResponse<Forecast>>('/forecasting/results', { params })
    const data = res.data as any
    if (Array.isArray(data)) return normalizeForecastsArray(data)
    return data
  },

  async getResult(id: number): Promise<Forecast> {
    const res = await api.get<Forecast>(`/forecasting/results/${id}`)
    return res.data
  },

  async getModels() {
    const res = await api.get('/forecasting/models')
    return res.data
  },

  async getAccuracy(params?: { product_id?: number; model_type?: string }): Promise<ForecastAccuracy[]> {
    const res = await api.get<AccuracyResponseItem[] | ForecastAccuracy[]>('/forecasting/accuracy', { params })
    const data = res.data as any
    if (Array.isArray(data) && data.length > 0 && 'mape' in data[0]) {
      return data.map((row: any) => ({
        ...row,
        wape: row.wape ?? 0,
        sample_count: row.sample_count ?? row.period_count,
        avg_mape: row.avg_mape ?? row.mape,
      }))
    }
    return normalizeAccuracy((data as AccuracyResponseItem[]) ?? [])
  },

  async detectAnomalies(productId: number) {
    // backend expects query param `product_id`
    const res = await api.post('/forecasting/anomalies/detect', null, { params: { product_id: productId } })
    return res.data
  },

  async getAnomalies(params?: { product_id?: number }) {
    const res = await api.get('/forecasting/anomalies', { params })
    return res.data
  },
}
