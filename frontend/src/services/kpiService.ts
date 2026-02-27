import api from './api'
import type { KPIMetric, CreateKPIRequest, PaginatedResponse } from '@/types'

type KPIMetricsResponse = PaginatedResponse<KPIMetric> | KPIMetric[]

/**
 * Backend uses Decimal for numeric fields which may serialize as strings.
 * Normalize to numbers so UI formatting (toFixed, arithmetic) never crashes.
 */
function toNumber(v: unknown): number | undefined {
  if (v === null || v === undefined) return undefined
  if (typeof v === 'number') return Number.isFinite(v) ? v : undefined
  if (typeof v === 'string' && v.trim() !== '') {
    const n = Number(v)
    return Number.isFinite(n) ? n : undefined
  }
  return undefined
}

function normalizeMetric(raw: any): KPIMetric {
  // Keep all non-numeric fields as-is; coerce numeric fields.
  return {
    ...raw,
    value: toNumber(raw?.value) ?? 0,
    target: toNumber(raw?.target),
    previous_value: toNumber(raw?.previous_value),
    variance: toNumber(raw?.variance),
    variance_pct: toNumber(raw?.variance_pct),
  } as KPIMetric
}

function normalizePaginated(data: PaginatedResponse<any>): PaginatedResponse<KPIMetric> {
  return {
    ...data,
    items: Array.isArray((data as any).items) ? (data as any).items.map(normalizeMetric) : [],
  }
}

export const kpiService = {
  async getMetrics(params?: { page?: number; page_size?: number; category?: string; period?: string }): Promise<PaginatedResponse<KPIMetric>> {
    // Backend historically returned either a paginated object or a raw list.
    // Normalize here so pages can always rely on PaginatedResponse<T>.
    const res = await api.get<KPIMetricsResponse>('/kpi/metrics', { params })
    const data = res.data

    if (Array.isArray(data)) {
      return {
        items: data.map(normalizeMetric),
        total: data.length,
        page: params?.page ?? 1,
        page_size: params?.page_size ?? data.length,
        total_pages: 1,
      }
    }

    return normalizePaginated(data)
  },

  async getMetric(name: string): Promise<KPIMetric[]> {
    const res = await api.get<KPIMetric[]>(`/kpi/metrics/${name}`)
    return Array.isArray(res.data) ? (res.data as any[]).map(normalizeMetric) : []
  },

  async createMetric(data: CreateKPIRequest): Promise<KPIMetric> {
    const res = await api.post<KPIMetric>('/kpi/metrics', data)
    return normalizeMetric(res.data)
  },

  async getDashboard() {
    const res = await api.get('/kpi/dashboard')
    return res.data
  },

  async getTrends(params?: { category?: string; months?: number }) {
    const res = await api.get('/kpi/trends', { params })
    return res.data
  },

  async getAlerts() {
    const res = await api.get('/kpi/alerts')
    return res.data
  },

  async getSummary() {
    const res = await api.get('/kpi/summary')
    return res.data
  },
}
