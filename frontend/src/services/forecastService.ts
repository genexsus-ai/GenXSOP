import api from './api'
import type { Forecast, GenerateForecastRequest, ForecastAccuracy, PaginatedResponse } from '@/types'

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

type GenerateForecastResponse = {
  product_id: number
  model_type?: string | null
  horizon: number
  forecasts: Array<{
    period: string
    predicted_qty: number
    lower_bound?: number | null
    upper_bound?: number | null
    confidence?: number | null
    mape?: number | null
  }>
}

type AccuracyResponseItem = {
  model_type: string
  avg_mape: number
  sample_count: number
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
  // Forecasting page expects mape as a % number and bias fields etc.
  // Backend currently only provides avg_mape + sample_count, so fill the rest with 0.
  return items.map((i) => ({
    product_id: 0,
    model_type: i.model_type,
    mape: i.avg_mape,
    bias: 0,
    rmse: 0,
    mae: 0,
    hit_rate: 0,
    period_count: i.sample_count,
  }))
}

export const forecastService = {
  async generateForecast(data: GenerateForecastRequest): Promise<Forecast[]> {
    // backend expects query params (product_id, horizon, model_type), not JSON body
    const res = await api.post<GenerateForecastResponse>('/forecasting/generate', null, {
      params: {
        product_id: data.product_id,
        horizon: data.horizon_months ?? 6,
        model_type: data.model_type,
      },
    })

    // Transform backend response into Forecast[] used in UI
    const modelType = (res.data.model_type ?? data.model_type ?? 'ml_ensemble') as Forecast['model_type']
    return (res.data.forecasts ?? []).map((f, idx) => ({
      id: -1 * (idx + 1),
      product_id: res.data.product_id,
      model_type: modelType,
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
    }))
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
    // If backend already matches frontend shape, pass through.
    if (Array.isArray(data) && data.length > 0 && 'mape' in data[0]) return data
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
